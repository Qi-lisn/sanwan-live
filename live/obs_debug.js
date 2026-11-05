const OBSWebSocket = require('obs-websocket-js').default;
const obs = new OBSWebSocket();
(async () => {
  await obs.connect('ws://127.0.0.1:4455', process.env.OBS_PASSWORD || '');
  console.log('scenes', (await obs.call('GetSceneList')).scenes.map(s=>s.sceneName));
  console.log('inputs', (await obs.call('GetInputList')).inputs.map(i=>i.inputName));
  try {
    const items = await obs.call('GetSceneItemList', { sceneName: '三万直播' });
    console.log('items', JSON.stringify(items.sceneItems.map(i=>({id:i.sceneItemId,name:i.sourceName,enabled:i.sceneItemEnabled}))));
  } catch(e) { console.log('items err', e.message); }
  await obs.disconnect();
})().catch(e => console.error('ERR', e.message));
