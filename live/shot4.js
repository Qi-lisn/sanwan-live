const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel:'chrome', headless:true });
  const p = await b.newPage({ viewport:{width:1920,height:1080} });
  p.on('pageerror', e => console.log('PAGEERROR', e.message));
  await p.goto('http://127.0.0.1:8765/stage_land.html?v=32', { waitUntil:'networkidle' });
  await p.waitForTimeout(6000);
  const st = await p.evaluate(() => ({cap: document.getElementById('caption').textContent,
                                      on: document.getElementById('caption').className,
                                      hud: document.getElementById('hud').textContent}));
  console.log(JSON.stringify(st));
  await p.screenshot({ path:'out/direct_check.png' });
  await b.close();
})();
