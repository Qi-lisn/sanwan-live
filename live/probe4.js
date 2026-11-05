const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel:'chrome', headless:true });
  const p = await b.newPage({ viewport:{width:1920,height:1080} });
  p.on('console', m => console.log('C:', m.text().slice(0,90)));
  await p.goto('http://127.0.0.1:8765/stage_land.html?v=35', { waitUntil:'networkidle' });
  await p.waitForTimeout(1500);
  console.log(await p.evaluate(() => ({t: typeof captionLoop, seq: typeof lastSeq, ls: window.lastSeq, cap: document.getElementById('caption').textContent})));
  await p.evaluate(() => captionLoop());
  await p.waitForTimeout(800);
  console.log('after manual call:', await p.evaluate(() => document.getElementById('caption').textContent));
  await b.close();
})();
