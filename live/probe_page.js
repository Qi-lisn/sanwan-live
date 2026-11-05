const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel:'chrome', headless:true });
  const p = await b.newPage({ viewport:{width:1920,height:1080} });
  p.on('console', m => console.log('CONSOLE', m.text().slice(0,120)));
  p.on('pageerror', e => console.log('ERR', e.message));
  await p.goto('http://127.0.0.1:8765/stage_land.html?v=32', { waitUntil:'networkidle' });
  await p.waitForTimeout(1000);
  console.log('fetch:', await p.evaluate(async () => { const r = await fetch('/caption'); return [r.status, (await r.text()).slice(0,80)]; }));
  console.log('setCaption test:', await p.evaluate(() => { window.setCaption('测试一下'); return document.getElementById('caption').textContent; }));
  await p.waitForTimeout(1500);
  console.log('after loop:', await p.evaluate(() => document.getElementById('caption').textContent));
  await b.close();
})();
