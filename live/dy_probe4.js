const { chromium } = require('playwright-core');
const path = require('path');
(async () => {
  const ctx = await chromium.launchPersistentContext(path.join(__dirname,'..','.douyin-profile'), {
    channel:'chrome', headless:false, viewport:{width:1280,height:900},
    args:['--mute-audio','--no-first-run'],
  });
  const p = ctx.pages()[0] || await ctx.newPage();
  await p.goto('https://live.douyin.com/7703933670848138019', { waitUntil:'domcontentloaded', timeout:60000 }).catch(e=>console.log('goto', e.message));
  await p.waitForTimeout(12000);
  console.log('URL', p.url());
  console.log('TEXT', (await p.evaluate(()=>document.body.innerText)).replace(/\s+/g,' ').slice(0,300));
  await p.screenshot({ path: path.join(__dirname,'..','out','dy_live_probe4.png') });
  await ctx.close();
})();
