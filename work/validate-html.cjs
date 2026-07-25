const fs = require("fs");

for (const file of ["outputs/index.html", "outputs/jinggangshan-miniapp-prototype.html"]) {
  const html = fs.readFileSync(file, "utf8");
  const scripts = [...html.matchAll(/<script(?:[^>]*)>([\s\S]*?)<\/script>/g)].map(match => match[1]);
  scripts.forEach(script => new Function(script));
  if (!html.includes('data-screen="sticker-custom"')) throw new Error(`${file}: missing custom sticker screen`);
  if (!html.includes("getJgsStickerEndpoint")) throw new Error(`${file}: missing sticker endpoint resolver`);
  console.log(`${file}: ${scripts.length} inline scripts OK`);
}
