const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel:'chrome', headless:true });
  const p = await b.newPage({ viewport:{width:1920,height:1080} });
  await p.goto('http://127.0.0.1:8765/stage_land.html?v=40', { waitUntil:'networkidle' });
  await p.waitForTimeout(1200);
  await p.evaluate(() => window.setCaption('周报写了三行 全是在等'));
  await p.waitForTimeout(400);
  await p.screenshot({ path:'out/live_caption.png' });
  await b.close();
})();
