/* 为现有 DSH /control.html 增加外卖控制区。原有动作/弹幕/点歌控制不改。 */
(() => {
  const layout = document.querySelector('.layout');
  if (!layout || document.querySelector('#cityDeliveryPanel')) return;
  const panel = document.createElement('section');
  panel.className = 'card';
  panel.id = 'cityDeliveryPanel';
  panel.innerHTML = `<h2>🛵 大肥鱼 · 外卖城市</h2>
    <p class="muted">沿用当前服务的 /delivery 状态。舞台页不会独立派单或计费。</p>
    <div id="cityDeliveryState" class="muted">正在读取配送状态…</div>
    <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:12px">
      <button data-dest="">📦 派随机单</button>
      <button data-dest="community">🏘 送小区</button>
      <button data-dest="shop">🏪 送便利店</button>
      <button data-dest="school">🎒 送学校</button>
      <button data-dest="hospital">🏥 送医院</button>
      <button data-dest="mall">🏬 送商场</button>
    </div>
    <div style="display:flex;gap:8px;align-items:center;margin-top:9px">
      <button id="cityReset" class="warn">↺ 重置外卖记录</button>
      <a href="/stage_map.html" target="_blank" rel="noreferrer">打开 2.5D 外卖舞台</a>
    </div>
    <p id="cityDeliveryFeedback" class="muted" style="font-size:13px"></p>`;
  layout.appendChild(panel);
  const state = panel.querySelector('#cityDeliveryState'), feedback = panel.querySelector('#cityDeliveryFeedback');
  async function post(path) {
    const r = await fetch(path, {method:'POST',headers: {'Content-Type':'application/json'},body:'{}'});
    if (!r.ok) throw Error('HTTP '+r.status);
    return r.json();
  }
  panel.querySelectorAll('button[data-dest]').forEach(btn=>btn.addEventListener('click',async()=>{
    try {
      const place = btn.dataset.dest;
      const resp = await post('/delivery/new' + (place?'?place='+encodeURIComponent(place):''));
      feedback.textContent = resp.queued ? '已安排下一单：'+resp.order.place_name : '已派单：'+resp.order.good+' → '+resp.order.place_name;
      await refresh();
    } catch(e) {feedback.textContent='派单失败：'+e.message}
  }));
  panel.querySelector('#cityReset').addEventListener('click',async()=>{
    if(!confirm('确定清空当前外卖订单与模拟收益吗？'))return;
    try{await post('/delivery/reset');feedback.textContent='外卖模拟记录已重置';await refresh()}
    catch(e){feedback.textContent='重置失败：'+e.message}
  });
  async function refresh(){
    try {
      const r = await fetch('/delivery',{cache:'no-store'});
      if(!r.ok) throw Error('HTTP '+r.status);
      const d = await r.json();
      state.textContent = (d.order?`${d.order.good} → ${d.order.place_name} · `:'等单中 · ')+
        `当前 ${d.status} · 已完成 ${d.delivered} 单 · 游戏收益 ¥${Number(d.earned).toFixed(1)} · 超时 ${d.late} 单`;
    } catch(e){state.textContent='配送接口暂不可用：'+e.message}
  }
  refresh(); setInterval(refresh,1500);
})();
