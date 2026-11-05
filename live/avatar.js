/* 三万舞台动作适配：轮询 /action_state，按动作切换 CSS 微动或透明 WebM。 */
(() => {
  const wrap = document.getElementById('heroWrap');
  if (!wrap) return;

  const style = document.createElement('style');
  style.textContent = `
    #heroWrap.sanwan-wave #heroBob {animation:sanwanWave .45s ease-in-out 5 alternate!important}
    #heroWrap.sanwan-happy #heroBob {animation:sanwanHappy .35s ease-in-out 5 alternate!important}
    #heroWrap.sanwan-shy #heroBob {animation:sanwanShy 1s ease-in-out 2!important}
    #heroWrap.sanwan-nod #heroBob {animation:sanwanNod .35s ease-in-out 4!important}
    #heroWrap.sanwan-laugh #heroBob {animation:sanwanLaugh .3s ease-in-out 6 alternate!important}
    #heroWrap.sanwan-demo-dance #heroBob {animation:sanwanDance .6s ease-in-out 12 alternate!important}
    @keyframes sanwanWave {to{transform:rotate(3deg) translateX(8px)}}
    @keyframes sanwanHappy {to{transform:translateY(-12px) scale(1.02)}}
    @keyframes sanwanShy {to{transform:rotate(-2deg) translateY(5px)}}
    @keyframes sanwanNod {to{transform:translateY(6px) rotate(-1deg)}}
    @keyframes sanwanLaugh {to{transform:translateY(-10px) scale(1.015)}}
    @keyframes sanwanDance {to{transform:rotate(5deg) translateY(-14px) scale(1.02)}}
    #sanwanDanceVideo{position:absolute;left:50%;bottom:0;transform:translateX(-50%);
      height:100%;width:auto;max-width:none;object-fit:contain;display:none;z-index:3;pointer-events:none}
  `;
  document.head.appendChild(style);

  const video = document.createElement('video');
  video.id = 'sanwanDanceVideo';
  video.muted = true;
  video.playsInline = true;
  video.preload = 'auto';
  video.src = 'motions/dance_cute.webm';
  wrap.appendChild(video);

  let lastSeq = -1;
  let timeoutId = null;
  let videoOk = true;          // 素材缺失/解码失败后置 false，后续直接走 CSS 示意
  let videoDuration = 8;       // 默认值，拿到 metadata 后覆盖

  function showHero() {
    const bob = document.getElementById('heroBob');
    if (bob) bob.style.visibility = '';
  }

  function reset() {
    clearTimeout(timeoutId);
    timeoutId = null;
    wrap.classList.remove('sanwan-wave', 'sanwan-happy', 'sanwan-shy', 'sanwan-nod', 'sanwan-laugh', 'sanwan-demo-dance');
    try { video.pause(); } catch (_) {}
    video.style.display = 'none';
    showHero();
  }

  function demoDance(duration) {
    reset();
    wrap.classList.add('sanwan-demo-dance');
    timeoutId = setTimeout(reset, Math.max(1000, duration * 1000));
  }

  function playDance(duration) {
    reset();
    const bob = document.getElementById('heroBob');
    const h = (bob && bob.offsetHeight) || 900;
    video.style.height = h + 'px';
    video.style.display = 'block';
    if (bob) bob.style.visibility = 'hidden';
    try { video.currentTime = 0; } catch (_) {}
    const p = video.play();
    if (p && p.catch) {
      p.catch(() => { videoOk = false; demoDance(duration); });
    }
    // 以视频真实时长为准，动作时长作为兜底
    timeoutId = setTimeout(reset, Math.max(duration, videoDuration) * 1000 + 400);
  }

  video.addEventListener('loadedmetadata', () => {
    if (isFinite(video.duration) && video.duration > 0) videoDuration = video.duration;
  });
  video.addEventListener('ended', reset);
  video.addEventListener('error', () => {
    videoOk = false;
    if (video.style.display === 'block') demoDance(videoDuration);
  });

  function perform(e) {
    if (e.name === 'idle') { reset(); return; }
    if (e.name === 'dance_cute') {
      if (videoOk) playDance(e.duration || 8);
      else demoDance(e.duration || 8);
      return;
    }
    reset();
    wrap.classList.add('sanwan-' + e.name);
    timeoutId = setTimeout(reset, Math.max(100, (e.duration || 2) * 1000));
  }

  async function poll() {
    try {
      const r = await fetch('/action_state', { cache: 'no-store' });
      if (r.ok) {
        const d = await r.json();
        if (lastSeq === -1) lastSeq = d.seq;      // 刷新页面不重放旧动作
        if (d.seq > lastSeq && d.recent && d.recent.length) {
          lastSeq = d.seq;
          perform(d.recent[d.recent.length - 1]);
        }
        if (d.paused) reset();
      }
    } catch (_) { /* 后端不可用时保持原状 */ }
    setTimeout(poll, 250);
  }
  poll();
})();
