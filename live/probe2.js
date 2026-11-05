const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel:'chrome', headless:true });
  const p = await b.newPage({ viewport:{width:1920,height:1080} });
  p.on('console', m => { if (m.type()==='error') console.log('CERR', m.text().slice(0,100)); });
  await p.goto('http://127.0.0.1:8765/stage_land.html?v=33', { waitUntil:'networkidle' });
  for (let i=0;i<10;i++){
    await p.waitForTimeout(1000);
    const r = await p.evaluate(async () => {
      const s = await (await fetch('/caption')).json();
      return { serverSeq: s.seq, serverText: s.text, cap: document.getElementById('caption').textContent,
               cls: document.getElementById('caption').className };
    });
    console.log(JSON.stringify(r));
  }
  await b.close();
})();
