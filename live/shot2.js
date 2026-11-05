const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel:'chrome', headless:true });
  const p = await b.newPage({ viewport:{width:1920,height:1080} });
  await p.goto('http://127.0.0.1:8765/stage_land.html?v=20', { waitUntil:'networkidle' });
  await p.waitForTimeout(3500);
  await p.screenshot({ path:'out/live_v2.png' });
  await b.close();
})();
