const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel:'chrome', headless:true });
  const p = await b.newPage({ viewport:{width:1920,height:1080} });
  await p.goto('http://127.0.0.1:8765/stage_land.html', { waitUntil:'networkidle' });
  await p.waitForTimeout(600);
  await p.evaluate(() => window.setCaption('晚上好呀，我是三万'));
  await p.waitForTimeout(400);
  await p.screenshot({ path:'out/live_land.png' });
  await b.close();
})();
