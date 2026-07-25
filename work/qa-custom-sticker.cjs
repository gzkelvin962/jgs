const { chromium } = require("playwright");
const fs = require("fs");

(async () => {
  const browser = await chromium.launch({
    executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    headless: true
  });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  const generated = fs.readFileSync("outputs/assets/stickers/custom/red-soldier-custom-steady.png").toString("base64");
  await page.route("http://127.0.0.1:8787/api/health", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ ok: true, openaiConfigured: true, imageModel: "gpt-image-2" })
  }));
  await page.route("http://127.0.0.1:8787/api/jinggangshan-sticker/customize", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ image: `data:image/png;base64,${generated}`, model: "gpt-image-2" })
  }));
  await page.goto("file:///C:/Users/Ken/Documents/Codex/2026-07-06/ui/outputs/jinggangshan-miniapp-prototype.html");

  await page.locator('[data-go="ip"]').first().click();
  await page.locator('[data-go="sticker-custom"]').click();
  await page.locator('#customStickerFile').setInputFiles("C:\\Users\\Ken\\Documents\\Codex\\2026-07-06\\ui\\outputs\\jinggangshan-hero.png");
  await page.locator('[data-custom-template="red-soldier-08"]').click();
  await page.locator('[data-custom-style="natural"]').click();
  await page.locator('#customStickerConsent').check();
  const enabledBeforeGenerate = await page.locator('#customStickerGenerate').isEnabled();
  await page.locator('#customStickerGenerate').click();
  await page.locator('#customStickerResult.show').waitFor({ timeout: 15000 });

  const state = await page.evaluate(() => ({
    activeScreen: document.querySelector('.screen.active')?.dataset.screen,
    selectedTemplate: document.querySelector('.custom-sticker-template.selected')?.dataset.customTemplate,
    selectedStyle: document.querySelector('[data-custom-style].selected')?.dataset.customStyle,
    audit: document.querySelector('#customStickerAuditText')?.textContent,
    resultNote: document.querySelector('#customStickerResultNote')?.textContent,
    resultSource: document.querySelector('#customStickerResultImage')?.src.slice(0, 22),
    downloadSource: document.querySelector('#customStickerDownload')?.getAttribute('href')?.slice(0, 22)
  }));
  await page.screenshot({ path: "work/custom-sticker-qa.png", fullPage: true });
  console.log(JSON.stringify({ enabledBeforeGenerate, state, errors }));
  await browser.close();
})();
