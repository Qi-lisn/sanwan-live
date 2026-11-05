const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');
const ROOT = path.join(__dirname, '..');
const PROFILE = path.join(ROOT, '.douyin-profile');
const OUT = path.join(ROOT, 'out');
const VIDEO = path.join(OUT, 'douyin_today.mp4');
const DESC = '今天我主人在给我做新衣服呢，你看漂亮吗。\n他说过两天我就可以跳舞了，你们期待吗。\n#AI #虚拟人 #AI少女 #夜班电台';

(async () => {
  const ctx = await chromium.launchPersistentContext(PROFILE, {
    channel: 'chrome', headless: false,
    viewport: { width: 1440, height: 960 },
    args: ['--no-first-run', '--no-default-browser-check', '--lang=zh-CN'],
  });
  const page = ctx.pages()[0] || (await ctx.newPage());
  page.on('console', m => { if (m.type() === 'error') console.log('CONSOLE_ERR', m.text().slice(0,120)); });

  await page.goto('https://creator.douyin.com/creator-micro/content/upload', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(3000);
  await page.setInputFiles('input[type=file]', VIDEO);
  console.log('file set');
  await page.waitForTimeout(6000);

  // 填文案
  const editor = page.locator('div[contenteditable=true], textarea').first();
  if (await editor.count()) {
    await editor.click();
    await page.keyboard.type(DESC, { delay: 8 });
    console.log('desc typed');
  }
  await page.waitForTimeout(2000);

  // 等快速检测跑完（最多 150s）
  for (let i = 0; i < 50; i++) {
    const t = await page.evaluate(() => document.body.innerText);
    const m = t.match(/检测中(\d+)%/);
    if (!m) { console.log('detect done'); break; }
    if (i % 6 === 0) console.log('detect', m[1] + '%');
    await page.waitForTimeout(3000);
  }
  await page.screenshot({ path: path.join(OUT, 'post2_ready.png') });

  const btn = page.getByRole('button', { name: /^发布$/ }).first();
  console.log('publish btn count', await btn.count());
  await btn.click({ timeout: 10000 }).catch(e => console.log('click err', e.message));
  await page.waitForTimeout(6000);
  await page.screenshot({ path: path.join(OUT, 'post2_after_click.png') });
  console.log('URL', page.url());

  const txt = await page.evaluate(() => document.body.innerText).catch(() => '');
  console.log('has 发布成功:', txt.includes('发布成功'));
  console.log('has 短信:', txt.includes('接收短信验证码'));
  await page.waitForTimeout(4000);
  await page.screenshot({ path: path.join(OUT, 'post2_final.png') });
  await ctx.close();
})();
