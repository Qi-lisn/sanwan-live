const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel:'chrome', headless:true });
  const p = await b.newPage({ viewport:{width:1920,height:1080} });
  await p.goto('http://127.0.0.1:8765/stage_wide.html?v=1', { waitUntil:'networkidle' });
  await p.waitForTimeout(1500);
  await p.evaluate(() => window.setCaption('末班车的时候 车厢是空的'));
  await p.waitForTimeout(300);
  await p.screenshot({ path:'out/wide.png' });
  await b.close();
})();
