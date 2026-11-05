const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel:'chrome', headless:true });
  const p = await b.newPage({ viewport:{width:1080,height:1920} });
  await p.goto('http://127.0.0.1:8765/stage_port.html?v=60', { waitUntil:'networkidle' });
  await p.waitForTimeout(1200);
  await p.evaluate(() => window.setCaption('末班车的时候 车厢是空的 你坐在那儿'));
  await p.waitForTimeout(300);
  await p.screenshot({ path:'out/live_port3.png' });
  await b.close();
})();
