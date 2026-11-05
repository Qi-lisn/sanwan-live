const { chromium } = require('playwright-core');
const path = require('path');
const ROOT = path.join(__dirname, '..');
const PROFILE = path.join(ROOT, '.douyin-profile');
const OUT = path.join(ROOT, 'out');
const VIDEO = path.join(OUT, 'douyin_today_v2.mp4');
const DESC = '今天我主人在给我做新衣服呢，你看漂亮吗。\n他说过两天我就可以跳舞了，你们期待吗。\n#AI #虚拟人 #AI少女 #夜班电台';

(async () => {
  const ctx = await chromium.launchPersistentContext(PROFILE, {
    channel: 'chrome', headless: false, viewport: { width: 1440, height: 960 },
    args: ['--no-first-run', '--no-default-browser-check', '--lang=zh-CN'],
  });
  const page = ctx.pages()[0] || (await ctx.newPage());
  await page.goto('https://creator.douyin.com/creator-micro/content/upload', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(2500);
  await page.setInputFiles('input[type=file]', VIDEO);
  console.log('uploading...');

  // 等上传完成：出现文案输入框且不再显示"上传中"
  let ready = false;
  for (let i = 0; i < 60; i++) {
    const t = await page.evaluate(() => document.body.innerText);
    if (t.includes('上传中') || t.includes('上传失败')) { await page.waitForTimeout(3000); continue; }
    if (t.includes('作品描述') || t.includes('添加作品描述') || t.includes('发布')) { ready = true; break; }
    await page.waitForTimeout(3000);
  }
  console.log('upload ready:', ready);
  await page.waitForTimeout(3000);

  const editor = page.locator('div[contenteditable=true]').first();
  if (await editor.count()) {
    await editor.click();
    await page.keyboard.type(DESC, { delay: 5 });
    console.log('desc ok');
  } else {
    console.log('no editor');
  }
  await page.waitForTimeout(2000);

  // 等快速检测
  for (let i = 0; i < 40; i++) {
    const t = await page.evaluate(() => document.body.innerText);
    const m = t.match(/检测中(\d+)%/);
    if (!m) break;
    if (i % 5 === 0) console.log('detect', m[1] + '%');
    await page.waitForTimeout(3000);
  }
  await page.screenshot({ path: path.join(OUT, 'post3_ready.png') });

  const btn = page.getByRole('button', { name: /^发布$/ }).first();
  console.log('btn count', await btn.count());
  await btn.click({ timeout: 10000 }).catch(e => console.log('click err', e.message));
  await page.waitForTimeout(8000);
  await page.screenshot({ path: path.join(OUT, 'post3_after.png') });
  const t2 = await page.evaluate(() => document.body.innerText).catch(() => '');
  console.log('success text:', t2.includes('发布成功'), '| sms:', t2.includes('接收短信验证码'), '| url:', page.url());
  await page.waitForTimeout(5000);
  await ctx.close();
})();
