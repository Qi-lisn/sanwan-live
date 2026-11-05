const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel:'chrome', headless:true });
  const p = await b.newPage({ viewport:{width:1920,height:1080} });
  await p.goto('http://127.0.0.1:8765/stage_land.html?v=32', { waitUntil:'networkidle' });
  for (let i=0;i<12;i++){
    await p.waitForTimeout(1000);
    console.log(i, JSON.stringify(await p.evaluate(() => document.getElementById('caption').textContent)));
  }
  await p.screenshot({ path:'out/direct_check.png' });
  await b.close();
})();
