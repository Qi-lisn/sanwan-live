const OBSWebSocket = require('obs-websocket-js').default;
const obs = new OBSWebSocket();
const PASS = process.env.OBS_PASSWORD || '请设置 OBS_PASSWORD';
(async () => {
  await obs.connect('ws://127.0.0.1:4455', PASS);
  await obs.call('SetVideoSettings', { baseWidth:1080, baseHeight:1920, outputWidth:1080, outputHeight:1920, fpsNumerator:30, fpsDenominator:1 });
  const items = await obs.call('GetSceneItemList', { sceneName: '三万直播' });
  const it = items.sceneItems[0];
  console.log('item', it.sceneItemId, it.sourceName);
  await obs.call('SetSceneItemTransform', {
    sceneName:'三万直播', sceneItemId: it.sceneItemId,
    sceneItemTransform:{ positionX:0, positionY:0, scaleX:1, scaleY:1, alignment:5, boundsType:'OBS_BOUNDS_NONE' },
  });
  await obs.call('SetCurrentProgramScene', { sceneName:'三万直播' });
  const vc = await obs.call('GetVirtualCamStatus').catch(e=>({outputActive:false,err:e.message}));
  console.log('vcam before', JSON.stringify(vc));
  if (!vc.outputActive) await obs.call('StartVirtualCam').catch(e=>console.log('vcam err', e.message));
  console.log('vcam after', JSON.stringify(await obs.call('GetVirtualCamStatus').catch(e=>({err:e.message}))));
  await obs.disconnect();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
