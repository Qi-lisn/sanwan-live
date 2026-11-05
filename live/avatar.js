/* 三万舞台动作适配：轮询 /action_state，按动作切换透明 WebM 或 CSS 微动。 */
(() => {
  const wrap = document.getElementById('heroWrap');
  if (!wrap) return;

  // 动作 -> 透明视频素材（存在即用视频，缺失/解码失败回退 CSS）
  const VIDEO_MAP = {
    dance_cute: 'motions/dance_cute.webm',
    wave: 'motions/wave.webm',
  };

  const style = document.createElement('style');
  style.textContent = `
    #heroWrap.sanwan-happy #heroBob {animation:sanwanHappy .35s ease-in-out 5 alternate!important}
    #heroWrap.sanwan-shy #heroBob {animation:sanwanShy 1s ease-in-out 2!important}
    #heroWrap.sanwan-nod #heroBob {animation:sanwanNod .35s ease-in-out 4!important}
    #heroWrap.sanwan-laugh #heroBob {animation:sanwanLaugh .3s ease-in-out 6 alternate!important}
    #heroWrap.sanwan-demo-wave #heroBob {animation:sanwanWave .45s ease-in-out 5 alternate!important}
    #heroWrap.sanwan-demo-dance #heroBob {animation:sanwanDance .6s ease-in-out 12 alternate!important}
    @keyframes sanwanWave {to{transform:rotate(3deg) translateX(8px)}}
    @keyframes sanwanHappy {to{transform:translateY(-12px) scale(1.02)}}
    @keyframes sanwanShy {to{transform:rotate(-2deg) translateY(5px)}}
    @keyframes sanwanNod {to{transform:translateY(6px) rotate(-1deg)}}
    @keyframes sanwanLaugh {to{transform:translateY(-10px) scale(1.015)}}
    @keyframes sanwanDance {to{transform:rotate(5deg) translateY(-14px) scale(1.02)}}
    #heroBob{transition:opacity .12s linear}
    .sanwan-clip{position:absolute;left:50%;bottom:0;transform:translateX(-50%);
      width:100%;height:auto;max-width:none;display:none;opacity:0;z-index:3;
      pointer-events:none;transition:opacity .12s linear}
  `;
  document.head.appendChild(style);

  const clips = {};       // name -> <video>
  const clipOk = {};      // name -> 是否可播放
  const clipDur = {};     // name -> 真实时长
  let lastSeq = -1;
  let timeoutId = null;
  let current = null;     // 当前播放的 clip 名

  function showHero() {
    const bob = document.getElementById('heroBob');
    if (bob) { bob.style.visibility = ''; bob.style.opacity = ''; }
  }

  function hideHero() {
    const bob = document.getElementById('heroBob');
    if (bob) bob.style.opacity = '0';
  }

  function getClip(name) {
    if (clips[name]) return clips[name];
    const v = document.createElement('video');
    v.className = 'sanwan-clip';
    v.dataset.name = name;
    v.muted = true;
    v.playsInline = true;
    v.preload = 'auto';
    v.src = VIDEO_MAP[name];
    v.addEventListener('loadedmetadata', () => {
      if (isFinite(v.duration) && v.duration > 0) clipDur[name] = v.duration;
    });
    v.addEventListener('error', () => {
      clipOk[name] = false;
      if (current === name) { v.style.display = 'none'; showHero(); }
    });
    v.addEventListener('ended', () => { if (current === name) reset(); });
    wrap.appendChild(v);
    clips[name] = v;
    return v;
  }

  function reset() {
    clearTimeout(timeoutId);
    timeoutId = null;
    Object.keys(clips).forEach(n => {
      const v = clips[n];
      try { v.pause(); } catch (_) {}
      v.style.display = 'none';
      v.style.opacity = '0';
    });
    current = null;
    wrap.classList.remove('sanwan-happy', 'sanwan-shy', 'sanwan-nod', 'sanwan-laugh',
                          'sanwan-demo-wave', 'sanwan-demo-dance');
    showHero();
  }

  function demo(name, duration) {
    reset();
    wrap.classList.add('sanwan-demo-' + (name === 'dance_cute' ? 'dance' : 'wave'));
    timeoutId = setTimeout(reset, Math.max(1000, duration * 1000));
  }

  function playClip(name, duration) {
    reset();
    const v = getClip(name);
    v.style.display = 'block';
    requestAnimationFrame(() => { v.style.opacity = '1'; });
    hideHero();
    current = name;
    try { v.currentTime = 0; } catch (_) {}
    const p = v.play();
    if (p && p.catch) p.catch(() => { clipOk[name] = false; demo(name, duration); });
    timeoutId = setTimeout(reset, Math.max(duration || 0, clipDur[name] || duration || 0) * 1000 + 400);
  }

  function perform(e) {
    if (e.name === 'idle') { reset(); return; }
    if (VIDEO_MAP[e.name]) {
      if (clipOk[e.name] === false) demo(e.name, e.duration || 2);
      else playClip(e.name, e.duration);
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
        if (lastSeq === -1) lastSeq = d.seq;
        if (d.seq > lastSeq && d.recent && d.recent.length) {
          lastSeq = d.seq;
          perform(d.recent[d.recent.length - 1]);
        }
        if (d.paused) reset();
      }
    } catch (_) { /* 后端不可用保持原状 */ }
    setTimeout(poll, 250);
  }
  poll();
})();
