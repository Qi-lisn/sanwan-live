const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel:'chrome', headless:true });
  const p = await b.newPage({ viewport:{width:1080,height:1920} });
  await p.goto('http://127.0.0.1:8765/stage_port.html?v=70', { waitUntil:'networkidle' });
  await p.waitForTimeout(800);
  await p.evaluate(() => { document.getElementById('blink').style.opacity = 1; });
  await p.waitForTimeout(200);
  await p.screenshot({ path:'out/live_blink.png' });
  await b.close();
})();
