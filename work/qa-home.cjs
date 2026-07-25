const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({
    executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    headless: true
  });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("file:///C:/Users/Ken/Documents/Codex/2026-07-06/ui/outputs/index.html");
  const cards = await page.locator(".ip-guide > .guide-step").evaluateAll(elements => elements.map(element => {
    const box = element.getBoundingClientRect();
    return { width: Math.round(box.width), height: Math.round(box.height), columns: getComputedStyle(element).gridTemplateColumns };
  }));
  await page.locator(".ip-guide").screenshot({ path: "work/home-guide-restored-qa.png" });
  console.log(JSON.stringify({ cards, errors }));
  await browser.close();
})();
