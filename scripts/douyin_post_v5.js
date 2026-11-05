// 抖音发布 v2：上传 -> 文案 -> 自主声明 -> 封面 -> 等旗标 -> 发布
const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');

const ROOT = path.join(__dirname, '..');
const PROFILE = path.join(ROOT, '.douyin-profile');
const OUT = path.join(ROOT, 'out');
const VIDEO = path.join(OUT, 'sanzhong_intro.mp4');
const COVER = path.join(OUT, 'frame_1.0.png');
const FLAG = path.join(OUT, 'PUBLISH_NOW');
const DESC = '初次见面，我是三万🐟 一个刚来到人类世界的 AI 少女，想在人类世界月入三万。 #AI #AI少女 #虚拟人 #电子宠物';

const shot = async (page, name) => {
  await page.screenshot({ path: path.join(OUT, name + '.png') }).catch(() => {});
  console.log('shot', name);
};

async function clickText(page, re, timeout = 4000) {
  const el = page.getByText(re).first();
  if (await el.count().catch(() => 0)) {
    await el.click({ timeout }).catch(() => {});
    await page.waitForTimeout(600);
    return true;
  }
  return false;
}

(async () => {
  const ctx = await chromium.launchPersistentContext(PROFILE, {
    channel: 'chrome', headless: false,
    viewport: { width: 1440, height: 960 },
    args: ['--no-first-run', '--no-default-browser-check', '--lang=zh-CN'],
  });
  const page = ctx.pages()[0] || (await ctx.newPage());

  await page.goto('https://creator.douyin.com/creator-micro/content/upload',
    { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(3500);

  for (const t of ['我知道了', '跳过', '下一步']) {
    await clickText(page, new RegExp('^' + t + '$'));
  }
  await page.keyboard.press('Escape').catch(() => {});

  await page.locator('input[type=file]').first().setInputFiles(VIDEO);
  await page.waitForTimeout(14000);
  await clickText(page, /^我知道了$/);
  await page.keyboard.press('Escape').catch(() => {});
  await shot(page, 'v2_1');

  const ed = page.locator('[contenteditable="true"]').first();
  await ed.click({ timeout: 6000 }).catch(() => {});
  await page.keyboard.insertText(DESC);
  await page.waitForTimeout(1200);
  await page.keyboard.press('Escape');
  await page.locator('text=基础信息').first().click({ timeout: 3000 }).catch(() => {});
  await page.waitForTimeout(800);
  await shot(page, 'v2_2');

  const decl = page.getByText('请选择自主声明').first();
  if (await decl.count().catch(() => 0)) {
    await decl.click({ timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(1500);
    await shot(page, 'v2_decl');
    const opts = await page.locator('[role="option"], li').allInnerTexts().catch(() => []);
    const label = page.locator('label.semi-radio').filter({ hasText: '内容由AI生成' }).first();
    console.log('decl label count:', await label.count());
    await label.click({ force: true }).catch(e => console.log('pick err', e.message));
    await page.waitForTimeout(800);
    await shot(page, 'v3_decl_picked');
    const ok = page.getByRole('button', { name: '确定' }).first();
    await ok.click({ timeout: 5000 }).catch(e => console.log('ok err', e.message));
    await page.waitForTimeout(1200);
    await page.keyboard.press('Escape').catch(() => {});
  } else {
    console.log('no decl field');
  }
  await shot(page, 'v2_3');

  await shot(page, 'v3_4');

  console.log('WAITING_FLAG');
  const deadline = Date.now() + 8 * 60 * 1000;
  while (Date.now() < deadline && !fs.existsSync(FLAG)) await page.waitForTimeout(2000);
  if (!fs.existsSync(FLAG)) { console.log('NO_FLAG'); await ctx.close(); return; }

  await shot(page, 'v2_before_publish');
  const btn = page.getByRole('button', { name: /^发布$/ }).first();
  console.log('publish btn:', await btn.count());
  await btn.click({ timeout: 8000 }).catch(e => console.log('publish click err', e.message));
  await page.waitForTimeout(6000);
  await shot(page, 'v5_after_click');
  const hasVerify = await page.getByText('接收短信验证码').count().catch(() => 0);
  console.log('VERIFY_MODAL', hasVerify);
  if (hasVerify) {
    console.log('WAITING_HUMAN_VERIFY');
    const until = Date.now() + 5 * 60 * 1000;
    while (Date.now() < until) {
      await page.waitForTimeout(5000);
      const txt = await page.evaluate(() => document.body.innerText).catch(() => '');
      if (!txt.includes('接收短信验证码')) break;
    }
    await shot(page, 'v5_after_verify');
  }
  await page.waitForSelector('text=发布成功', { timeout: 15000 }).catch(() => console.log('no success text'));
  await shot(page, 'v2_after_publish');
  console.log('URL_AFTER', page.url());
  await page.waitForTimeout(3000);
  await ctx.close();
})();
