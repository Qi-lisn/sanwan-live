const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel:'chrome', headless:true });
  const p = await b.newPage({ viewport:{width:1080,height:1920} });
  await p.goto('http://127.0.0.1:8765/stage_port.html?v=81', { waitUntil:'networkidle' });
  await p.waitForTimeout(600);
  await p.evaluate(() => window.setCaption('末班车的时候 车厢是空的'));
  for (let i=0;i<6;i++){ await p.waitForTimeout(55); await p.screenshot({path:`out/talk_${i}.png`, clip:{x:380,y:140,width:420,height:260}}); }
  await b.close();
})();
