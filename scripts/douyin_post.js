// 抖音发布：上传 -> 填文案 -> 等确认旗标 -> 点发布
const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');

const ROOT = path.join(__dirname, '..');
const PROFILE = path.join(ROOT, '.douyin-profile');
const OUT = path.join(ROOT, 'out');
const VIDEO = path.join(OUT, 'sanzhong_intro.mp4');
const FLAG = path.join(OUT, 'PUBLISH_NOW');
const DESC = '初次见面，我是三万🐟 一个刚来到人类世界的 AI 少女，想在人类世界月入三万。 #AI #AI少女 #虚拟人 #电子宠物';

const shot = async (page, name) => {
  await page.screenshot({ path: path.join(OUT, name + '.png') }).catch(() => {});
  console.log('shot', name);
};

(async () => {
  const ctx = await chromium.launchPersistentContext(PROFILE, {
    channel: 'chrome',
    headless: false,
    viewport: { width: 1440, height: 960 },
    args: ['--no-first-run', '--no-default-browser-check', '--lang=zh-CN'],
  });
  const page = ctx.pages()[0] || (await ctx.newPage());
  page.on('console', m => { if (m.type() === 'error') console.log('PAGE_ERR', m.text().slice(0, 120)); });

  await page.goto('https://creator.douyin.com/creator-micro/content/upload', {
    waitUntil: 'domcontentloaded', timeout: 60000,
  });
  await page.waitForTimeout(4000);
  await shot(page, 'post_0');

  // 关掉引导弹窗
  for (const t of ['跳过', '下一步', '我知道了']) {
    const el = page.getByText(t, { exact: true }).first();
    if (await el.count().catch(() => 0)) {
      await el.click({ timeout: 3000 }).catch(() => {});
      await page.waitForTimeout(800);
    }
  }

  // 上传
  const input = page.locator('input[type=file]').first();
  console.log('file inputs:', await page.locator('input[type=file]').count());
  await input.setInputFiles(VIDEO).catch(e => console.log('setInputFiles err', e.message));
  await page.waitForTimeout(12000);
  await shot(page, 'post_1');

  // 文案
  const ed = page.locator('[contenteditable="true"]').first();
  if (await ed.count().catch(() => 0)) {
    await ed.click({ timeout: 5000 }).catch(() => {});
    await page.keyboard.insertText(DESC);
    await page.waitForTimeout(1500);
  } else {
    console.log('no contenteditable found');
  }
  await shot(page, 'post_2');

  // 等旗标，最长 8 分钟
  console.log('WAITING_FLAG');
  const deadline = Date.now() + 8 * 60 * 1000;
  while (Date.now() < deadline && !fs.existsSync(FLAG)) {
    await page.waitForTimeout(2000);
  }
  if (!fs.existsSync(FLAG)) {
    console.log('NO_FLAG_TIMEOUT');
    await ctx.close();
    return;
  }

  await shot(page, 'post_3');
  const btn = page.getByRole('button', { name: /^发布$/ }).first();
  console.log('publish button count:', await btn.count());
  await btn.click({ timeout: 8000 }).catch(e => console.log('click err', e.message));
  await page.waitForTimeout(8000);
  await shot(page, 'post_4');
  console.log('URL_AFTER', page.url());
  await page.waitForTimeout(3000);
  await ctx.close();
})();
