const { chromium } = require('playwright-core');
const path = require('path');
const ROOT = path.join(__dirname, '..');
(async () => {
  const ctx = await chromium.launchPersistentContext(path.join(ROOT, '.douyin-profile'), {
    channel: 'chrome', headless: false, viewport: { width: 1440, height: 960 },
  });
  const page = ctx.pages()[0] || await ctx.newPage();
  await page.goto('https://creator.douyin.com/creator-micro/content/manage', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(8000);
  await page.screenshot({ path: path.join(ROOT, 'out', 'check_manage.png') });
  const txt = await page.evaluate(() => document.body.innerText.slice(0, 600)).catch(() => '');
  console.log('TEXT:', txt.replace(/\s+/g, ' ').slice(0, 400));
  await ctx.close();
})();
