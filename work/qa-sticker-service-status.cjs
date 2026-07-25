const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({
    executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    headless: true
  });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("http://127.0.0.1:8787/");
  await page.locator('[data-go="ip"]').first().click();
  await page.locator('[data-go="sticker-custom"]').click();
  await page.locator('#customStickerAudit.blocked').waitFor({ timeout: 10000 });
  const state = {
    audit: await page.locator('#customStickerAuditText').textContent(),
    generateDisabled: await page.locator('#customStickerGenerate').isDisabled(),
    resultVisible: await page.locator('#customStickerResult').isVisible(),
    errors
  };
  console.log(JSON.stringify(state));
  await browser.close();
})();
