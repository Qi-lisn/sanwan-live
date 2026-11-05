const { chromium } = require('playwright-core');
const path = require('path');
(async () => {
  const ctx = await chromium.launchPersistentContext(path.join(__dirname,'..','.dy-viewer'), {
    channel:'chrome', headless:false, viewport:{width:430,height:932},
    userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    args:['--mute-audio','--no-first-run'],
  });
  const p = ctx.pages()[0] || await ctx.newPage();
  await p.goto('https://webcast.amemv.com/douyin/webcast/reflow/7703933670848138019', { waitUntil:'domcontentloaded', timeout:60000 }).catch(e=>console.log('goto', e.message));
  await p.waitForTimeout(12000);
  console.log('URL', p.url());
  console.log('TITLE', await p.title());
  console.log('TEXT', (await p.evaluate(()=>document.body.innerText)).replace(/\s+/g,' ').slice(0,250));
  await p.screenshot({ path: path.join(__dirname,'..','out','dy_live_probe3.png') });
  await ctx.close();
})();
