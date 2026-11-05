const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel:'chrome', headless:true });
  const p = await b.newPage({ viewport:{width:1080,height:1920} });
  await p.goto('http://127.0.0.1:8765/stage_port.html?v=80', { waitUntil:'networkidle' });
  await p.waitForTimeout(600);
  await p.screenshot({ path:'out/v3_idle.png' });
  await p.evaluate(() => { window.setCaption('末班车的时候 车厢是空的'); document.getElementById('mouth').style.opacity=1; });
  await p.waitForTimeout(200);
  await p.screenshot({ path:'out/v3_talk.png' });
  await b.close();
})();
