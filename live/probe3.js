const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel:'chrome', headless:true });
  const p = await b.newPage({ viewport:{width:1920,height:1080} });
  p.on('console', m => console.log('C:', m.text().slice(0,80)));
  p.on('pageerror', e => console.log('ERR', e.message));
  await p.goto('http://127.0.0.1:8765/stage_land.html?v=34', { waitUntil:'networkidle' });
  await p.waitForTimeout(6000);
  console.log('cap=', JSON.stringify(await p.evaluate(() => document.getElementById('caption').textContent)));
  await b.close();
})();
