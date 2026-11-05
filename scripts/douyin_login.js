// 打开创作者中心，等待用户扫码登录（登录态存进 profile）
const { chromium } = require('playwright-core');
const path = require('path');

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
  }).catch(() => {});

  const deadline = Date.now() + 10 * 60 * 1000;
  let tick = 0;
  while (Date.now() < deadline) {
    await page.waitForTimeout(4000);
    tick++;
    const url = page.url();
    const text = await page.evaluate(() => document.body.innerText.slice(0, 200)).catch(() => '');
    const loggedIn = !text.includes('扫码登录') && (text.includes('发布作品') || text.includes('作品描述') || url.includes('/content/post'));
    if (tick % 5 === 0) {
      await page.screenshot({ path: path.join(OUT, 'dy_login.png') }).catch(() => {});
    }
    if (loggedIn) {
      console.log('LOGIN_OK', url);
      await page.screenshot({ path: path.join(OUT, 'dy_loggedin.png') }).catch(() => {});
      await page.waitForTimeout(2000);
      await ctx.close();
      return;
    }
  }
  console.log('LOGIN_TIMEOUT');
  await ctx.close();
})();
