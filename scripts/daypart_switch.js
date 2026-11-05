// 时段联动：按 /daypart 切换 OBS 场景源，并在换档/开播前发系统通知
const OBS = require('obs-websocket-js').default;
const { execFile } = require('child_process');
const BASE = 'http://127.0.0.1:8765';
const SCENE = '三万直播';
const STAGE = '舞台', MAP = '地图';

const notify = (title, text) => execFile('osascript', ['-e',
  `display notification "${text}" with title "${title}" sound name "Ping"`], () => {});

async function getDaypart() {
  const r = await fetch(`${BASE}/daypart`, { cache: 'no-store' });
  return r.json();
}

async function ensureSource(obs) {
  const inputs = (await obs.call('GetInputList')).inputs.map(i => i.inputName);
  if (!inputs.includes(MAP)) {
    await obs.call('CreateInput', {
      sceneName: SCENE, inputName: MAP, inputKind: 'browser_source',
      inputSettings: { url: `${BASE}/stage_map.html`, width: 1920, height: 1080 },
      sceneItemEnabled: false,
    });
    console.log('created source', MAP);
  }
}

async function setVisible(obs, name, on) {
  const items = (await obs.call('GetSceneItemList', { sceneName: SCENE })).sceneItems;
  const it = items.find(i => i.sourceName === name);
  if (it && it.sceneItemEnabled !== on) {
    await obs.call('SetSceneItemEnabled', { sceneName: SCENE, sceneItemId: it.sceneItemId, sceneItemEnabled: on });
    console.log(name, on ? 'on' : 'off');
  }
}

(async () => {
  const obs = new OBS();
  await obs.connect('ws://127.0.0.1:4455', process.env.OBS_PASSWORD || 'wQkKeHnsCz9owvFz');
  await ensureSource(obs);
  let last = null;
  while (true) {
    try {
      const d = await getDaypart();
      const mapMode = !!d.map || require('fs').existsSync('/tmp/map_override');
      await setVisible(obs, STAGE, !mapMode);
      await setVisible(obs, MAP, mapMode);
      if (d.id !== last) {
        if (last !== null) notify('三万换班了', `${d.name} · ${d.intro}`);
        last = d.id;
      }
      const mins = Math.round(d.seconds_left / 60);
      const now = new Date();
      const hh = now.getHours(), mm = now.getMinutes();
      // 开播提醒：每天 05:55 / 11:55 / 19:55
      if ((hh === 5 || hh === 11 || hh === 19) && mm === 55) {
        notify('该开播了', `下一档 ${d.next}，点一下直播伴侣`);
      }
    } catch (e) {
      console.log('loop err', e.message);
    }
    await new Promise(r => setTimeout(r, 20000));
  }
})();
