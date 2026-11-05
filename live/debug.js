const { chromium } = require('playwright-core');
(async () => {
  const b = await chromium.launch({ channel:'chrome', headless:true });
  const p = await b.newPage({ viewport:{width:1080,height:1920} });
  p.on('console', m => console.log('CONSOLE', m.type(), m.text()));
  p.on('pageerror', e => console.log('PAGEERROR', e.message));
  await p.goto('http://127.0.0.1:8765/', { waitUntil:'networkidle' });
  await p.waitForTimeout(1000);
  console.log('typeof setCaption', await p.evaluate(() => typeof window.setCaption));
  console.log('scripts', await p.evaluate(() => document.scripts.length));
  await b.close();
})();
