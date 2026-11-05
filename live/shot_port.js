const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel:'chrome', headless:true });
  const p = await b.newPage({ viewport:{width:1080,height:1920} });
  await p.goto('http://127.0.0.1:8765/stage_port.html?v=50', { waitUntil:'networkidle' });
  await p.waitForTimeout(3000);
  await p.screenshot({ path:'out/live_port2.png' });
  await b.close();
})();
