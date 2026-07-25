"""Jinggangshan prototype backend: agent, profile, points, and settings APIs."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import base64
import json
import mimetypes
import os
import threading
import uuid
from copy import deepcopy
from urllib.parse import unquote, urlparse


APP_ROOT = Path(__file__).parent.resolve()
LOCAL_ENV_FILE = APP_ROOT / ".env.local"
if LOCAL_ENV_FILE.exists():
    for raw_line in LOCAL_ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

PORT = int(os.environ.get("PORT", "8787"))
HOST = os.environ.get("HOST", "127.0.0.1")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-5")
API_KEY = os.environ.get("OPENAI_API_KEY", "")
KNOWLEDGE_FILE = APP_ROOT / "assets" / "jinggangshan-knowledge-base.json"
USER_DATA_DIR = Path(os.environ.get("JGS_USER_DATA_DIR", str(APP_ROOT / "assets" / "users")))
KNOWLEDGE = json.loads(KNOWLEDGE_FILE.read_text(encoding="utf-8"))
USER_DATA_LOCK = threading.Lock()
STICKER_TEMPLATE_DIR = APP_ROOT / "assets" / "stickers" / "red-soldier"


def refresh_api_key():
    global API_KEY
    if API_KEY:
        return API_KEY
    if LOCAL_ENV_FILE.exists():
        for raw_line in LOCAL_ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line.startswith("OPENAI_API_KEY="):
                candidate = line.split("=", 1)[1].strip().strip('"').strip("'")
                if candidate and "replace_with" not in candidate:
                    API_KEY = candidate
                    break
    return API_KEY

DEFAULT_USER_DATA = {
    "profile": {
        "nickname": "研学同学",
        "realName": "",
        "organization": "",
        "role": "学生",
        "phone": "",
        "bio": "",
        "avatar": ""
    },
    "points": {
        "balance": 1280,
        "lastCheckin": "",
        "history": [
            {"title": "完成三湾改编知识问答", "date": "今天 09:20", "amount": 30},
            {"title": "发布研学短视频", "date": "昨天 18:45", "amount": 80},
            {"title": "黄洋界路线打卡", "date": "7月13日", "amount": 50},
            {"title": "兑换官方表情包", "date": "7月12日", "amount": -100}
        ]
    },
    "settings": {
        "notifications": True,
        "location": True,
        "autoplay": False,
        "analytics": False
    },
    "referral": {"code": "JGS-1927", "count": 3}
}

SYSTEM_PROMPT = """
你是“井冈山智能体”，面向井冈山宣传小程序用户。
回答井冈山革命历史、旧址和景区、研学路线、采访提纲、短视频素材等问题。
优先使用随请求提供的本地知识库；遇到未覆盖或实时问题时使用联网搜索，优先采用井冈山革命博物馆、政府网站和中国共产党新闻网等可信来源。
不得编造史实、人物、开放时间、交通或票务信息。实时信息须提示以官方当日公告为准。
如请求带有路线偏好或位置，只将其用于当前回答，不在回答中复述精确坐标，也不保存位置。
""".strip()


def relevant_knowledge(question):
    normalized = question.lower()
    scored = []
    for entry in KNOWLEDGE["entries"]:
        score = sum(len(keyword) for keyword in entry["keywords"] if keyword.lower() in normalized)
        if score:
            scored.append((score, entry))
    return [entry for _, entry in sorted(scored, key=lambda item: item[0], reverse=True)[:3]]


def route_context(context):
    if not isinstance(context, dict):
        return ""
    start = str(context.get("start", "")).strip()[:120]
    duration = str(context.get("duration", "")).strip()[:30]
    interest = str(context.get("interest", "")).strip()[:50]
    location = context.get("location") if isinstance(context.get("location"), dict) else {}
    latitude = location.get("latitude")
    longitude = location.get("longitude")
    position = ""
    if isinstance(latitude, (int, float)) and isinstance(longitude, (int, float)):
        position = f"已获用户本次定位授权，概略坐标：{latitude:.4f}, {longitude:.4f}。"
    details = "；".join(item for item in [f"出发地：{start}" if start else "", f"可用时间：{duration}" if duration else "", f"主题偏好：{interest}" if interest else "", position] if item)
    return f"\n\n路线规划上下文（仅本次请求使用）：{details}" if details else ""


def ask_openai(question, context=None):
    api_key = refresh_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    facts = relevant_knowledge(question)
    reference_context = "\n\n".join(
        f"{index}. {entry['title']}: {entry['answer']}\n来源：{entry['sourceName']} {entry['sourceUrl']}"
        for index, entry in enumerate(facts, start=1)
    ) or "本地知识库暂无直接命中，请进行可信来源联网检索。"
    body = json.dumps({
        "model": MODEL,
        "tools": [{"type": "web_search"}],
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"用户问题：{question}{route_context(context)}\n\n可用本地知识库：\n{reference_context}"}
        ]
    }).encode("utf-8")
    request = Request(
        "https://api.openai.com/v1/responses",
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST"
    )
    with urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    return {
        "answer": data.get("output_text") or "暂时没有生成回答，请换个问法再试。",
        "sources": [{"name": entry["sourceName"], "url": entry["sourceUrl"]} for entry in facts]
    }


def user_data_file(user_id):
    safe_id = "".join(character for character in user_id if character.isalnum() or character in "-_")[:80]
    return USER_DATA_DIR / f"{safe_id or 'jgs-local-user'}.json"


def load_user_data(user_id):
    data_file = user_data_file(user_id)
    if not data_file.exists():
        return deepcopy(DEFAULT_USER_DATA)
    try:
        stored = json.loads(data_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return deepcopy(DEFAULT_USER_DATA)
    data = deepcopy(DEFAULT_USER_DATA)
    for section in data:
        if isinstance(stored.get(section), dict):
            data[section].update(stored[section])
    return data


def save_user_data(user_id, data):
    data_file = user_data_file(user_id)
    data_file.parent.mkdir(parents=True, exist_ok=True)
    temporary = data_file.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(data_file)


def clean_profile(payload):
    allowed = {
        "nickname": 16,
        "realName": 16,
        "organization": 30,
        "role": 12,
        "phone": 11,
        "bio": 120,
        "avatar": 400_000
    }
    result = {}
    for key, limit in allowed.items():
        if key in payload and isinstance(payload[key], str):
            result[key] = payload[key].strip()[:limit]
    if result.get("phone") and (len(result["phone"]) != 11 or not result["phone"].isdigit()):
        raise ValueError("Invalid phone number")
    return result


def clean_settings(payload):
    keys = ("notifications", "location", "autoplay", "analytics")
    return {key: bool(payload[key]) for key in keys if key in payload}


class StickerServiceError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def decode_data_image(value, max_bytes=10_000_000):
    if not isinstance(value, str) or not value.startswith("data:image/") or ";base64," not in value:
        raise StickerServiceError(400, "请上传有效的 JPG、PNG 或 WEBP 人像")
    header, encoded = value.split(",", 1)
    mime = header[5:].split(";", 1)[0].lower()
    extensions = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    if mime not in extensions:
        raise StickerServiceError(400, "仅支持 JPG、PNG 或 WEBP 图片")
    try:
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as error:
        raise StickerServiceError(400, "图片数据无法读取") from error
    if not content or len(content) > max_bytes:
        raise StickerServiceError(400, "图片大小不能超过 10MB")
    signatures = {
        "image/jpeg": content.startswith(b"\xff\xd8\xff"),
        "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    }
    if not signatures[mime]:
        raise StickerServiceError(400, "图片格式与文件内容不一致")
    return content, mime, extensions[mime]


def openai_json(path, payload, timeout=60):
    api_key = refresh_api_key()
    if not api_key:
        raise StickerServiceError(503, "AI 图片服务尚未配置，请联系管理员")
    request = Request(
        f"https://api.openai.com/v1/{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        if error.code in (401, 403):
            raise StickerServiceError(503, "AI 图片服务配置无效，请联系管理员") from error
        raise StickerServiceError(502, "AI 图片服务暂时不可用，请稍后重试") from error


def moderate_portrait(portrait_data_url):
    result = openai_json("moderations", {
        "model": "omni-moderation-latest",
        "input": [
            {"type": "text", "text": "用户提交本人或已获授权的人像，用于制作井冈山红军主题卡通表情。"},
            {"type": "image_url", "image_url": {"url": portrait_data_url}}
        ]
    })
    if any(item.get("flagged") for item in result.get("results", [])):
        raise StickerServiceError(422, "照片未通过安全审核，请更换合规人像")


def multipart_body(fields, files):
    boundary = f"----JgsSticker{uuid.uuid4().hex}"
    chunks = []
    for name, value in fields.items():
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
            str(value).encode("utf-8"),
            b"\r\n"
        ])
    for name, filename, mime, content in files:
        chunks.extend([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode(),
            f"Content-Type: {mime}\r\n\r\n".encode(),
            content,
            b"\r\n"
        ])
    chunks.append(f"--{boundary}--\r\n".encode())
    return boundary, b"".join(chunks)


def sticker_prompt(style, template_label):
    style_notes = {
        "natural": "Keep facial proportions especially faithful and use restrained cartoon simplification.",
        "balanced": "Balance recognizable facial features with the friendly rounded cartoon style of the template.",
        "lively": "Use a lively, slightly exaggerated cartoon expression while keeping the person recognizable."
    }
    return f"""
Create one square messaging sticker. Image 1 is a standardized cartoon head that has already been normalized to a consistent face size. Image 2 is the official red-soldier cartoon template named '{template_label}'. It controls the pose, red-star cap, historical costume, hands, props, composition, background, white sticker outline, expression intent, and Chinese wording.

Redraw only the facial identity of the character in Image 2 using Image 1. Match the exact face position, head angle, expression, scale, lighting, line weight, and hat occlusion of the original template. The new face must occupy exactly the same facial area as the template face; do not place Image 1 as a floating layer, badge, oval photo, or pasted object. {style_notes.get(style, style_notes['balanced'])} Keep the template's pose, clothing, hat, hair occlusion, hands, props, background, outline, crop, and existing Chinese text unchanged. Do not add text, watermarks, signatures, extra people, or new symbols. Do not infer or state identity and do not imitate a public figure.
""".strip()


def normalized_cartoon_prompt(style):
    style_notes = {
        "natural": "Use restrained cartoon simplification and prioritize accurate facial proportions.",
        "balanced": "Use a friendly rounded cartoon style while keeping the person clearly recognizable.",
        "lively": "Use a lively, slightly exaggerated cartoon treatment while preserving identity traits."
    }
    return f"""
Transform the supplied portrait into one standardized cartoon identity reference. Preserve the visible face shape, hairstyle and hairline, eyebrows, eye shape, nose, mouth, facial proportions, and non-sensitive distinguishing features without identifying the person. {style_notes.get(style, style_notes['balanced'])}

Output only one clean front-facing cartoon head with a small amount of neck on a flat light-blue square canvas. Normalize the head so it is centered, upright, symmetrical in placement, and occupies about 68 percent of the canvas height and 62 percent of the canvas width, regardless of the original photo crop. Use smooth solid color regions, clean dark outlines, soft shading, and a coherent illustrated finish. Remove the original background, clothing, accessories outside the face, and photographic texture. Do not add a hat, uniform, text, symbols, watermark, shoulders, hands, or a second person. Do not paste or preserve a photorealistic face.
""".strip()


def openai_image_edit(files, prompt, background=None):
    api_key = refresh_api_key()
    if not api_key:
        raise StickerServiceError(503, "AI 图片服务尚未配置，请联系管理员")
    fields = {
        "model": "gpt-image-2",
        "prompt": prompt,
        "size": "1024x1024",
        "quality": "medium",
        "output_format": "png",
        "n": "1"
    }
    if background:
        fields["background"] = background
    boundary, body = multipart_body(fields, files)
    request = Request(
        "https://api.openai.com/v1/images/edits",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body))
        },
        method="POST"
    )
    try:
        with urlopen(request, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        if error.code in (401, 403):
            raise StickerServiceError(503, "AI 图片服务配置无效，请联系管理员") from error
        raise StickerServiceError(502, "AI 图片生成失败，请稍后重试或更换照片") from error
    images = data.get("data") or []
    encoded = images[0].get("b64_json") if images else ""
    if not encoded:
        raise StickerServiceError(502, "AI 图片生成结果为空，请重试")
    return encoded


def customize_sticker(payload):
    if payload.get("consent") is not True:
        raise StickerServiceError(400, "请先确认人像使用授权")
    portrait_data_url = payload.get("portrait")
    portrait, portrait_mime, portrait_ext = decode_data_image(portrait_data_url)
    template_id = str(payload.get("templateId", ""))
    if not template_id.startswith("red-soldier-"):
        raise StickerServiceError(400, "请选择有效的官方表情模板")
    try:
        template_number = int(template_id.rsplit("-", 1)[1])
    except ValueError as error:
        raise StickerServiceError(400, "请选择有效的官方表情模板") from error
    if not 1 <= template_number <= 12:
        raise StickerServiceError(400, "请选择有效的官方表情模板")
    template_path = STICKER_TEMPLATE_DIR / f"{template_number:02d}.png"
    if not template_path.exists():
        raise StickerServiceError(500, "官方表情模板缺失")

    style = str(payload.get("style", "balanced"))
    template_label = str(payload.get("templateLabel", "红军表情"))[:20]
    moderate_portrait(portrait_data_url)

    normalized_head_base64 = openai_image_edit(
        [
            ("image[]", f"portrait.{portrait_ext}", portrait_mime, portrait)
        ],
        normalized_cartoon_prompt(style)
    )
    try:
        normalized_head = base64.b64decode(normalized_head_base64, validate=True)
    except ValueError as error:
        raise StickerServiceError(502, "标准卡通头像生成结果无法读取") from error

    encoded = openai_image_edit(
        [
            ("image[]", "normalized-cartoon-head.png", "image/png", normalized_head),
            ("image[]", "official-template.png", "image/png", template_path.read_bytes())
        ],
        sticker_prompt(style, template_label)
    )
    return {
        "image": f"data:image/png;base64,{encoded}",
        "audit": {"status": "passed"},
        "model": "gpt-image-2",
        "pipeline": ["moderation", "normalized_cartoon_head", "template_integration"],
        "stored": False
    }


class AgentHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-JGS-User-ID")
        super().end_headers()

    def send_json(self, status, payload):
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_static(self, request_path):
        relative = "index.html" if request_path in ("", "/") else unquote(request_path).lstrip("/")
        candidate = (APP_ROOT / relative).resolve()
        allowed_suffixes = {".html", ".png", ".jpg", ".jpeg", ".webp", ".json", ".zip"}
        if APP_ROOT not in candidate.parents or candidate.suffix.lower() not in allowed_suffixes or not candidate.is_file():
            self.send_json(404, {"error": "File not found"})
            return
        content = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8" if content_type.startswith("text/") else content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store" if candidate.suffix.lower() == ".html" else "public, max-age=3600")
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        self.send_json(204, {})

    def read_payload(self, max_bytes=1_000_000):
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length > max_bytes:
            raise ValueError("Request body too large")
        return json.loads(self.rfile.read(content_length) or b"{}")

    def user_id(self):
        return self.headers.get("X-JGS-User-ID", "jgs-local-user")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            self.send_json(200, {
                "ok": True,
                "openaiConfigured": bool(refresh_api_key()),
                "imageModel": "gpt-image-2",
                "stickerEndpoint": "/api/jinggangshan-sticker/customize"
            })
            return
        sections = {
            "/api/jinggangshan-user/profile": "profile",
            "/api/jinggangshan-user/points": "points",
            "/api/jinggangshan-user/settings": "settings",
            "/api/jinggangshan-user/referral": "referral"
        }
        section = sections.get(path)
        if not section:
            if path.startswith("/api/"):
                self.send_json(404, {"error": "Unknown endpoint"})
            else:
                self.send_static(path)
            return
        data = load_user_data(self.user_id())
        self.send_json(200, {section: data[section]})

    def do_PUT(self):
        path = urlparse(self.path).path
        try:
            payload = self.read_payload()
            with USER_DATA_LOCK:
                user_id = self.user_id()
                data = load_user_data(user_id)
                if path == "/api/jinggangshan-user/profile":
                    data["profile"].update(clean_profile(payload))
                    section = "profile"
                elif path == "/api/jinggangshan-user/settings":
                    data["settings"].update(clean_settings(payload))
                    section = "settings"
                else:
                    self.send_json(404, {"error": "Unknown endpoint"})
                    return
                save_user_data(user_id, data)
            self.send_json(200, {section: data[section]})
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self.send_json(400, {"error": str(error)})
        except OSError as error:
            self.send_json(500, {"error": str(error)})

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            payload = self.read_payload(16_000_000 if path == "/api/jinggangshan-sticker/customize" else 1_000_000)
            if path == "/api/jinggangshan-sticker/customize":
                self.send_json(200, customize_sticker(payload))
                return
            if path == "/api/jinggangshan-agent":
                question = payload.get("question") or payload.get("message")
                if not isinstance(question, str) or not question.strip():
                    raise ValueError("Missing question")
                self.send_json(200, ask_openai(question.strip(), payload.get("context")))
                return
            if path == "/api/jinggangshan-user/points/checkin":
                checkin_date = str(payload.get("date", "")).strip()[:20]
                if not checkin_date:
                    raise ValueError("Missing check-in date")
                with USER_DATA_LOCK:
                    user_id = self.user_id()
                    data = load_user_data(user_id)
                    points = data["points"]
                    if points.get("lastCheckin") != checkin_date:
                        points["lastCheckin"] = checkin_date
                        points["balance"] = int(points.get("balance", 0)) + 20
                        points.setdefault("history", []).insert(0, {
                            "title": "每日研学签到",
                            "date": "刚刚",
                            "amount": 20
                        })
                        points["history"] = points["history"][:50]
                        save_user_data(user_id, data)
                self.send_json(200, {"points": data["points"]})
                return
            self.send_json(404, {"error": "Unknown endpoint"})
        except StickerServiceError as error:
            self.send_json(error.status, {"error": error.message, "message": error.message})
        except HTTPError as error:
            self.send_json(error.code, {"error": error.read().decode("utf-8", "replace")})
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self.send_json(400, {"error": str(error)})
        except Exception as error:
            self.send_json(500, {"error": str(error)})

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path != "/api/jinggangshan-user/profile":
            self.send_json(404, {"error": "Unknown endpoint"})
            return
        try:
            with USER_DATA_LOCK:
                save_user_data(self.user_id(), deepcopy(DEFAULT_USER_DATA))
            self.send_json(204, {})
        except OSError as error:
            self.send_json(500, {"error": str(error)})

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    print(f"Jinggangshan agent API: http://127.0.0.1:{PORT}/api/jinggangshan-agent")
    print(f"Jinggangshan user API: http://127.0.0.1:{PORT}/api/jinggangshan-user/profile")
    print(f"Jinggangshan sticker API: http://127.0.0.1:{PORT}/api/jinggangshan-sticker/customize")
    print(f"Jinggangshan miniapp: http://{HOST}:{PORT}/")
    print("OpenAI image service: ready" if API_KEY else "OpenAI image service: missing OPENAI_API_KEY")
    ThreadingHTTPServer((HOST, PORT), AgentHandler).serve_forever()
