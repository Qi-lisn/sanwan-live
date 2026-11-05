const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel:'chrome', headless:true });
  const p = await b.newPage({ viewport:{width:1080,height:1920}, deviceScaleFactor:1 });
  await p.goto('http://127.0.0.1:8765/', { waitUntil:'networkidle' });
  await p.waitForTimeout(1200);
  await p.screenshot({ path:'out/live_stage.png' });
  await p.evaluate(() => window.setCaption('晚上好呀，我是三万'));
  await p.waitForTimeout(400);
  await p.screenshot({ path:'out/live_stage_caption.png' });
  await b.close();
})();
