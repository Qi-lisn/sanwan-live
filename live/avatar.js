/* Visual-only avatar adapter. Polls the local controller, never calls an LLM. */
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
    #sanwanDanceVideo {position:absolute;inset:0;width:100%;height:100%;object-fit:contain;display:none;z-index:3}
  `;
  document.head.appendChild(style);
  const video = document.createElement('video');
  video.id = 'sanwanDanceVideo';
  video.muted = true;
  video.playsInline = true;
  video.preload = 'auto';
  // Transparent WebM file must be supplied separately; fallback does NOT provide real limb animation.
  video.src = 'motions/dance_cute.webm';
  wrap.appendChild(video);
  let lastSeq = -1, timeoutId = null;
  function reset() {
    clearTimeout(timeoutId);
    wrap.classList.remove('sanwan-wave','sanwan-happy','sanwan-shy','sanwan-nod','sanwan-laugh','sanwan-demo-dance');
    video.pause(); video.style.display = 'none';
    const bob = document.getElementById('heroBob');
    if (bob) bob.style.visibility = '';
  }
  function perform(e) {
    reset();
    if (e.name === 'idle') return;
    const duration = Math.max(100, (e.duration || 2) * 1000);
    if (e.name === 'dance_cute') {
      video.currentTime = 0;
      const bob = document.getElementById('heroBob');
      // Size video before hiding the in-flow image; otherwise the wrapper collapses.
      if (bob) video.style.height = bob.offsetHeight + 'px';
      video.style.display = 'block';
      if (bob) bob.style.visibility = 'hidden';
      video.play().catch(() => {
        if (bob) bob.style.visibility = '';
        video.style.display = 'none';
        wrap.classList.add('sanwan-demo-dance');
      });
    } else wrap.classList.add('sanwan-' + e.name);
    timeoutId = setTimeout(reset, duration);
  }
  video.addEventListener('error', () => {
    if (video.style.display === 'block') {
      video.style.display='none';
      const bob = document.getElementById('heroBob');
      if (bob) bob.style.visibility = '';
      wrap.classList.add('sanwan-demo-dance');
    }
  });
  async function poll() {
    try {
      const r = await fetch('/action_state', {cache:'no-store'});
      if (r.ok) {
        const d = await r.json();
        if (lastSeq === -1) lastSeq = d.seq; // Don't replay old action after page refresh.
        if (d.seq > lastSeq && d.recent?.length) {
          const event = d.recent[d.recent.length - 1];
          lastSeq = d.seq;
          perform(event);
        }
        if (d.paused && video.style.display === 'block') reset();
      }
    } catch (_) { /* Retain normal stage when backend unavailable. */ }
    setTimeout(poll, 250);
  }
  poll();
})();
