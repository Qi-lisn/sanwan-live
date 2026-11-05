// 直播播放器：读 script.md，逐句播放并更新字幕
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const SCRIPT = path.join(ROOT, 'live', 'script.md');
const OUT = path.join(ROOT, 'out');

// 解析：## 段落 -> 段落间停顿；- 行 -> 台词
function parse(md) {
  const segs = [];
  let cur = null;
  for (const raw of md.split('\n')) {
    const line = raw.trim();
    if (line.startsWith('## ')) {
      cur = { title: line.slice(3), lines: [] };
      segs.push(cur);
    } else if (line.startsWith('- ') && cur) {
      cur.lines.push(line.slice(2).trim());
    }
  }
  return segs;
}

(async () => {
  const segs = parse(fs.readFileSync(SCRIPT, 'utf8'));
  const total = segs.reduce((n, s) => n + s.lines.length, 0);
  console.log('segments:', segs.length, 'lines:', total);

  const ctx = await chromium.launchPersistentContext(path.join(ROOT, '.live-profile'), {
    channel: 'chrome',
    headless: false,
    viewport: { width: 1080, height: 1920 },
    args: [
      '--app=http://127.0.0.1:8765/',
      '--window-size=1080,1920',
      '--window-position=0,0',
      '--no-first-run',
      '--no-default-browser-check',
      '--autoplay-policy=no-user-gesture-required',
    ],
  });
  const page = ctx.pages()[0] || (await ctx.newPage());
  if (!page.url().includes('8765')) await page.goto('http://127.0.0.1:8765/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);

  const stopFile = path.join(OUT, 'STOP_LIVE');
  fs.existsSync(stopFile) && fs.unlinkSync(stopFile);

  const LIMIT = parseInt(process.env.LIMIT || '0', 10);
  let played = 0;
  for (const seg of segs) {
    console.log('---', seg.title);
    for (const line of seg.lines) {
      if (LIMIT && played >= LIMIT) { console.log('limit reached'); await ctx.close(); return; }
      if (fs.existsSync(stopFile)) { console.log('stopped by flag'); await ctx.close(); return; }
      const ok = await page.evaluate(t => window.speak(t), line);
      await page.waitForTimeout(700 + Math.random() * 500);
      if (!ok) console.log('speak failed:', line);
      played++;
    }
    await page.waitForTimeout(2500); // 段落之间
  }
  console.log('script finished');
  await page.waitForTimeout(3000);
  await ctx.close();
})();
