// 抖音创作者中心自动化：探测登录态
const { chromium } = require('playwright-core');
const path = require('path');
const os = require('os');

const PROFILE = path.join(__dirname, '..', '.douyin-profile');
const OUT = path.join(__dirname, '..', 'out');

(async () => {
  const ctx = await chromium.launchPersistentContext(PROFILE, {
    channel: 'chrome',
    headless: false,
    viewport: { width: 1440, height: 960 },
    args: ['--no-first-run', '--no-default-browser-check', '--lang=zh-CN'],
  });
  const page = ctx.pages()[0] || (await ctx.newPage());
  await page.goto('https://creator.douyin.com/creator-micro/content/upload', {
    waitUntil: 'domcontentloaded', timeout: 60000,
  }).catch(e => console.log('goto error', e.message));

  await page.waitForTimeout(5000);
  console.log('URL:', page.url());
  console.log('TITLE:', await page.title());
  await page.screenshot({ path: path.join(OUT, 'dy_state.png') });

  const body = await page.evaluate(() => document.body.innerText.slice(0, 400)).catch(() => '');
  console.log('TEXT:', body.replace(/\s+/g, ' ').slice(0, 300));

  await page.waitForTimeout(3000);
  await ctx.close();
})();
