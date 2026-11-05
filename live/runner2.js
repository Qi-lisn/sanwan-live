// 动态直播：从语料库随机组句，不背稿
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const OUT = path.join(ROOT, 'out');
const INJECT = path.join(ROOT, 'live', 'inject.txt');
const STOP = path.join(OUT, 'STOP_LIVE');
const CONTENT = JSON.parse(fs.readFileSync(path.join(ROOT, 'live', 'content.json'), 'utf8'));

const rnd = (a) => a[Math.floor(Math.random() * a.length)];

function makeEngine(content) {
  const recent = [];
  const recentTopics = [];
  const push = (line) => { recent.push(line); if (recent.length > 70) recent.shift(); };
  const fresh = (pool, n = 40) => {
    const used = new Set(recent.slice(-n));
    const avail = pool.filter(x => !used.has(x));
    return avail.length ? avail : pool;
  };
  return {
    nextTopic() {
      const pool = content.topics.filter(t => !recentTopics.includes(t.id));
      const t = rnd(pool.length ? pool : content.topics);
      recentTopics.push(t.id); if (recentTopics.length > 3) recentTopics.shift();
      return t;
    },
    nextAtom(topic) {
      const line = rnd(fresh(topic.atoms));
      push(line);
      return line;
    },
    reaction() { const l = rnd(content.reactions); push(l); return l; },
  };
}

(async () => {
  const engine = makeEngine(CONTENT);
  const ctx = await chromium.launchPersistentContext(path.join(ROOT, '.live-profile'), {
    channel: 'chrome', headless: false,
    viewport: { width: 1080, height: 1920 },
    args: ['--app=http://127.0.0.1:8765/', '--window-size=1080,1920',
           '--window-position=0,0', '--autoplay-policy=no-user-gesture-required'],
  });
  const page = ctx.pages()[0] || (await ctx.newPage());
  if (!page.url().includes('8765')) await page.goto('http://127.0.0.1:8765/');
  await page.waitForTimeout(1200);

  const LIMIT = parseInt(process.env.LIMIT || '0', 10);
  let n = 0;
  if (fs.existsSync(STOP)) fs.unlinkSync(STOP);

  const say = async (line) => {
    const ok = await page.evaluate(t => window.speak(t), line);
    if (!ok) console.log('fail:', line);
    await page.waitForTimeout(600 + Math.random() * 600);
    n++;
  };

  while (!fs.existsSync(STOP)) {
    if (LIMIT && n >= LIMIT) break;

    // 手动插话优先
    if (fs.existsSync(INJECT)) {
      const lines = fs.readFileSync(INJECT, 'utf8').split('\n').map(s => s.trim()).filter(Boolean);
      fs.unlinkSync(INJECT);
      for (const l of lines) { if (LIMIT && n >= LIMIT) break; await say(l); }
      continue;
    }

    const topic = engine.nextTopic();
    console.log('##', topic.title);
    if (Math.random() < 0.5) await say(rnd(topic.intro));
    const k = 3 + Math.floor(Math.random() * 4);
    for (let i = 0; i < k; i++) {
      if (LIMIT && n >= LIMIT) break;
      if (Math.random() < 0.15) await say(engine.reaction());
      await say(engine.nextAtom(topic));
    }
    await page.waitForTimeout(1500 + Math.random() * 1500);
  }
  console.log('lines spoken:', n);
  await page.waitForTimeout(2000);
  await ctx.close();
})();
