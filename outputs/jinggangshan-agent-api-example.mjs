import http from "node:http";
import { readFile } from "node:fs/promises";

const PORT = Number(process.env.PORT || 8787);
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const MODEL = process.env.OPENAI_MODEL || "gpt-5";
const knowledgeBase = JSON.parse(
  await readFile(new URL("./assets/jinggangshan-knowledge-base.json", import.meta.url), "utf8")
);

const systemPrompt = `
你是“井冈山智能体”，面向井冈山宣传小程序用户。
回答范围：井冈山革命历史、旧址和景区、研学路线、采访提纲、短视频素材、IP应用、AI活化说明。
要求：中文回答，简洁可靠。优先使用随请求提供的本地知识库；遇到知识库未覆盖、用户明确询问“最新/今天/现在”的问题时，使用联网搜索，并优先采用井冈山革命博物馆、政府网站和中国共产党新闻网等可信来源。若提供位置或路线偏好，只用于当前回答，不保存位置，也不复述精确坐标。
不得编造史实、人物、开放时间、交通或票务信息。对实时信息明确提示以官方当日公告为准；回答历史问题时尽量指出资料来源名称。
`;

function sendJson(res, status, data) {
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization"
  });
  res.end(JSON.stringify(data));
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", chunk => {
      body += chunk;
      if (body.length > 1_000_000) {
        req.destroy();
        reject(new Error("request body too large"));
      }
    });
    req.on("end", () => resolve(body));
    req.on("error", reject);
  });
}

function relevantKnowledge(question) {
  const normalized = question.toLowerCase();
  return knowledgeBase.entries
    .map(entry => ({
      entry,
      score: entry.keywords.reduce((sum, keyword) => sum + (normalized.includes(keyword.toLowerCase()) ? keyword.length : 0), 0)
    }))
    .filter(item => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 3)
    .map(item => item.entry);
}

function routeContext(context) {
  if (!context || typeof context !== "object") return "";
  const start = String(context.start || "").trim().slice(0, 120);
  const duration = String(context.duration || "").trim().slice(0, 30);
  const interest = String(context.interest || "").trim().slice(0, 50);
  const location = context.location && typeof context.location === "object" ? context.location : {};
  const latitude = Number(location.latitude);
  const longitude = Number(location.longitude);
  const parts = [
    start && `出发地：${start}`,
    duration && `可用时间：${duration}`,
    interest && `主题偏好：${interest}`,
    Number.isFinite(latitude) && Number.isFinite(longitude) && `已获用户本次定位授权，概略坐标：${latitude.toFixed(4)}, ${longitude.toFixed(4)}`
  ].filter(Boolean);
  return parts.length ? `\n\n路线规划上下文（仅本次请求使用）：${parts.join("；")}` : "";
}

async function askOpenAI(question, context) {
  if (!OPENAI_API_KEY) {
    throw new Error("OPENAI_API_KEY is not set");
  }

  const facts = relevantKnowledge(question);
  const referenceContext = facts.length
    ? facts.map((entry, index) => `${index + 1}. ${entry.title}: ${entry.answer}\n来源：${entry.sourceName} ${entry.sourceUrl}`).join("\n\n")
    : "本地知识库暂无直接命中，请进行可信来源联网检索。";

  const response = await fetch("https://api.openai.com/v1/responses", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${OPENAI_API_KEY}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      model: MODEL,
      tools: [{ type: "web_search" }],
      input: [
        { role: "system", content: systemPrompt },
        {
          role: "user",
          content: `用户问题：${question}${routeContext(context)}\n\n可用本地知识库：\n${referenceContext}`
        }
      ]
    })
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`OpenAI API error ${response.status}: ${detail}`);
  }

  const data = await response.json();
  return {
    answer: data.output_text || "暂时没有生成回答，请换个问法再试。",
    sources: facts.map(entry => ({ name: entry.sourceName, url: entry.sourceUrl }))
  };
}

const server = http.createServer(async (req, res) => {
  if (req.method === "OPTIONS") {
    sendJson(res, 204, {});
    return;
  }

  if (req.method !== "POST" || req.url !== "/api/jinggangshan-agent") {
    sendJson(res, 404, { error: "Use POST /api/jinggangshan-agent" });
    return;
  }

  try {
    const raw = await readBody(req);
    const { question, context } = JSON.parse(raw || "{}");
    if (!question || typeof question !== "string") {
      sendJson(res, 400, { error: "Missing question" });
      return;
    }

    const result = await askOpenAI(question, context);
    sendJson(res, 200, result);
  } catch (error) {
    sendJson(res, 500, { error: error.message });
  }
});

server.listen(PORT, () => {
  console.log(`Jinggangshan agent API running at http://localhost:${PORT}/api/jinggangshan-agent`);
  console.log("Set OPENAI_API_KEY before starting this server.");
});
