const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({
    executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    headless: true
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("file:///C:/Users/Ken/Documents/Codex/2026-07-06/ui/outputs/proposals/jinggangshan-lbs-quiz-options.html");

  const mapDemo = page.locator('[data-demo="map"]');
  await mapDemo.locator("[data-arrive]").click();
  await mapDemo.locator("[data-answer]").first().click();
  await mapDemo.locator("[data-answer][data-correct]").click();

  const deepDemo = page.locator('[data-demo="deep"]');
  await deepDemo.locator("[data-answer][data-correct]").click();

  const teamDemo = page.locator('[data-demo="team"]');
  await teamDemo.locator("[data-arrive]").click();
  await teamDemo.locator("[data-answer][data-correct]").click();

  const state = {
    mapPoints: await mapDemo.locator("[data-points]").textContent(),
    mapState: await mapDemo.locator("[data-state]").textContent(),
    deepPoints: await deepDemo.locator("[data-points]").textContent(),
    report: await deepDemo.locator("[data-report-comment]").textContent(),
    teamPoints: await teamDemo.locator("[data-points]").textContent(),
    teamProgress: await teamDemo.locator("[data-progress-text]").textContent(),
    stampClass: await teamDemo.locator("[data-team-stamp]").getAttribute("class"),
    errors
  };

  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: "work/lbs-quiz-options-desktop.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("file:///C:/Users/Ken/Documents/Codex/2026-07-06/ui/outputs/proposals/jinggangshan-lbs-quiz-options.html");
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: "work/lbs-quiz-options-mobile.png", fullPage: true });
  console.log(JSON.stringify(state));
  await browser.close();
})();
