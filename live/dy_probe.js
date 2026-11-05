const { chromium } = require('playwright-core');
const path = require('path');
(async () => {
  const b = await chromium.launch({ channel:'chrome', headless:true, args:['--mute-audio','--autoplay-policy=no-user-gesture-required'] });
  const p = await b.newPage({ viewport:{width:1280,height:900} });
  await p.goto('https://live.douyin.com/7703933670848138019', { waitUntil:'domcontentloaded', timeout:60000 }).catch(e=>console.log('goto', e.message));
  await p.waitForTimeout(10000);
  console.log('URL', p.url());
  console.log('TITLE', await p.title());
  const info = await p.evaluate(() => {
    const out = { chatLike: [], textSample: document.body.innerText.slice(0, 500) };
    const all = document.querySelectorAll('div,span');
    let n = 0;
    for (const el of all) {
      const cls = (el.className && el.className.toString) ? el.className.toString() : '';
      if (/chat/i.test(cls) && el.children.length < 30) {
        out.chatLike.push({ cls: cls.slice(0,80), text: (el.innerText||'').slice(0,120) });
        if (++n > 10) break;
      }
    }
    return out;
  });
  console.log(JSON.stringify(info, null, 1).slice(0, 2500));
  await p.screenshot({ path: path.join(__dirname,'..','out','dy_live_probe.png') });
  await b.close();
})();
