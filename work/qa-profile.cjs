const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({
    executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    headless: true
  });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("file:///C:/Users/Ken/Documents/Codex/2026-07-06/ui/outputs/jinggangshan-miniapp-prototype.html");

  await page.locator('[data-nav="profile"]').click();
  await page.locator('[data-go="profile-info"]').click();
  await page.locator("#profileNickname").fill("验证同学");
  await page.locator("#profileForm button[type=submit]").click();
  await page.locator('[data-screen="profile-info"] [data-go="profile"]').click();
  const savedName = await page.locator("#profileDisplayName").textContent();

  await page.locator('[data-go="profile-points"]').click();
  const beforePoints = Number(await page.locator("#pointsBalance").textContent());
  await page.locator("#pointsCheckin").click();
  const afterPoints = Number(await page.locator("#pointsBalance").textContent());
  await page.locator('[data-screen="profile-points"] [data-go="profile"]').click();

  await page.locator('[data-go="profile-cache"]').click();
  await page.locator("#clearSelectedCache").click();
  const confirmVisible = await page.locator("#profileConfirmLayer").isVisible();
  await page.locator("#profileConfirmCancel").click();
  await page.locator('[data-screen="profile-cache"] [data-go="profile"]').click();

  await page.locator('[data-go="profile-settings"]').click();
  await page.locator('[data-setting="autoplay"]').evaluate(input => input.click());
  const settingStored = await page.evaluate(() => JSON.parse(localStorage.getItem("JGS_SETTINGS_V1")).autoplay);
  await page.screenshot({ path: "work/profile-settings-qa.png", fullPage: true });

  console.log(JSON.stringify({ savedName, beforePoints, afterPoints, confirmVisible, settingStored, errors }));
  await browser.close();
})();
