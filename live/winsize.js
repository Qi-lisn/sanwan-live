const { chromium } = require('playwright-core');
const path = require('path');
(async () => {
  const ctx = await chromium.launchPersistentContext(path.join(__dirname,'..','.live-profile'), {
    channel:'chrome', headless:false, viewport:{width:1080,height:1920},
    args:['--app=http://127.0.0.1:8765/','--window-size=1080,1920','--window-position=0,0'],
  });
  const p = ctx.pages()[0] || await ctx.newPage();
  await p.waitForTimeout(1200);
  console.log(JSON.stringify(await p.evaluate(() => ({iw:innerWidth, ih:innerHeight, ow:outerWidth, oh:outerHeight, dpr:devicePixelRatio}))));
  await ctx.close();
})();
