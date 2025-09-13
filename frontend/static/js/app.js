function setActive(id){
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-'+id).classList.add('active');
  document.getElementById('panel-'+id).classList.add('active');
}

async function loadPeg(){
  const res = await fetch('/peg');
  const data = await res.json();
  const rows = data.data;
  const tb = document.querySelector('#peg-table tbody');
  tb.innerHTML='';
  rows.sort((a,b)=> a.symbol.localeCompare(b.symbol) || a.venue.localeCompare(b.venue));
  // compute spreads per symbol between venues
  const bySymbol = {};
  for(const r of rows){
    bySymbol[r.symbol] = bySymbol[r.symbol] || {};
    bySymbol[r.symbol][r.venue] = r.price;
  }
  function spreadBps(symbol, venue){
    const venues = bySymbol[symbol] || {};
    const others = Object.entries(venues).filter(([v,_]) => v !== venue).map(([_,p])=>p);
    if(!others.length) return 0;
    const avg = others.reduce((a,b)=>a+b,0)/others.length;
    if(avg === 0) return 0;
    return ((bySymbol[symbol][venue]-avg)/avg)*10000;
  }
  for(const r of rows){
    const tr = document.createElement('tr');
    const ts = new Date(r.timestamp).toLocaleTimeString();
    const sBps = spreadBps(r.symbol, r.venue);
    const sClass = Math.abs(sBps) > 20 ? 'alert' : '';
    const sparkId = `spark-${r.symbol}-${r.venue}`.replace(/[^a-zA-Z0-9_-]/g,'');
    tr.innerHTML = `<td>${r.symbol}</td><td>${r.venue}</td><td>${r.price.toFixed(6)}</td><td class="${sClass}">${sBps.toFixed(1)}</td><td><div id="${sparkId}" class="spark"></div></td><td class="small">${ts}</td>`;
    tb.appendChild(tr);
    drawSpark(r.symbol, r.venue, sparkId);
  }
}

async function loadSlippage(){
  const res = await fetch('/slippage');
  const data = await res.json();
  const rows = data.summary;
  const tb = document.querySelector('#slip-table tbody');
  tb.innerHTML='';
  for(const d of rows){
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>$${d.size.toLocaleString()}</td><td>$${d.out_amount.toLocaleString()}</td><td>${d.execution_price.toFixed(6)}</td><td>${d.slippage_bps.toFixed(2)}</td>`;
    tb.appendChild(tr);
  }
  const sizes = rows.map(r=> r.size/1e6);
  const slp = rows.map(r=> r.slippage_bps);
  Plotly.newPlot('slip-chart', [{x: sizes, y: slp, mode: 'lines+markers', line: {color:'#7aa2ff'}}], {paper_bgcolor:'#131826', plot_bgcolor:'#131826', xaxis:{title:'Trade Size (MM)'}, yaxis:{title:'Slippage (bps)'}, margin:{t:20,l:50,r:20,b:50}});
}

async function loadYield(){
  const res = await fetch('/yield');
  const data = await res.json();
  const anchors = data.anchors;
  const tb = document.querySelector('#yield-anchors tbody');
  tb.innerHTML='';
  for(const [name, v] of Object.entries(anchors)){
    const tr = document.createElement('tr');
    const terms = v.days.map((d,i)=> `${d}d: ${v.rates[i].toFixed(2)}%`).join(' · ');
    tr.innerHTML = `<td>${name}</td><td>${terms}</td>`;
    tb.appendChild(tr);
  }
  const days = data.curve.days;
  const rates = data.curve.rates;
  Plotly.newPlot('yield-chart', [{x: days, y: rates, mode: 'lines+markers', line:{color:'#40c9a2'}}], {paper_bgcolor:'#131826', plot_bgcolor:'#131826', xaxis:{title:'Days'}, yaxis:{title:'APY %'}, margin:{t:20,l:50,r:20,b:50}});
  const delta = typeof data.delta_bps === 'number' ? data.delta_bps : 0;
  const el = document.getElementById('yield-delta');
  if(el){
    const sign = delta >= 0 ? '+' : '';
    el.textContent = `CeFi vs DeFi spread: ${sign}${delta.toFixed(1)} bps`;
  }
}

async function refreshPegLoop(){
  while(true){
    try { await loadPeg(); } catch(e) { console.error(e); }
    await new Promise(r=> setTimeout(r, 3000));
  }
}

window.addEventListener('DOMContentLoaded', async ()=>{
  setActive('peg');
  await loadPeg();
  await loadSlippage();
  await loadYield();
  refreshPegLoop();
  setupReplay();
  loadHeatmap();
});

async function drawSpark(symbol, venue, elId){
  try{
    const res = await fetch(`/peg_history?symbol=${encodeURIComponent(symbol)}&limit=60`);
    const data = await res.json();
    const points = (((data||{}).data||{})[symbol]||{})[venue]||[];
    if(!points.length) return;
    const x = points.map(p=> new Date(p.t));
    const y = points.map(p=> p.p);
    Plotly.newPlot(elId, [{x, y, mode:'lines', line:{color:'#9aa4bf'} }], {paper_bgcolor:'#131826', plot_bgcolor:'#131826', margin:{t:2,l:20,r:10,b:18}, xaxis:{visible:false}, yaxis:{visible:false}});
  }catch(e){ console.error(e); }
}

function setupReplay(){
  const btn = document.getElementById('btn-replay');
  if(!btn) return;
  btn.addEventListener('click', async ()=>{
    try{
      const res = await fetch('/replay/usdc_2023');
      const data = await res.json();
      // Render into signals card as two mini charts
      const wrap = document.getElementById('signals');
      if(!wrap) return;
      const series = data.data.USDC;
      wrap.innerHTML = '';
      for(const [venue, pts] of Object.entries(series)){
        const div = document.createElement('div');
        div.className = 'card-mini';
        const id = `replay-${venue}`;
        div.innerHTML = `<div class="muted">${venue} replay</div><div id="${id}" style="height:120px;"></div>`;
        wrap.appendChild(div);
        const x = pts.map(p=> new Date(p.t));
        const y = pts.map(p=> p.p);
        Plotly.newPlot(id, [{x, y, mode:'lines', line:{color:'#f39c12'}}], {paper_bgcolor:'#131826', plot_bgcolor:'#131826', margin:{t:10,l:40,r:20,b:24}, xaxis:{title:'t', tickfont:{size:10}}, yaxis:{title:'$'} });
      }
    }catch(e){ console.error(e); }
  });
}

async function loadHeatmap(){
  try{
    const res = await fetch('/slippage_grid');
    const data = await res.json();
    const x = data.x_sizes_mm;
    const y = data.y_depth_multipliers;
    const z = data.z_slippage_bps;
    Plotly.newPlot('slip-heatmap', [{z, x, y, type:'heatmap', colorscale:'RdYlGn_r'}], {paper_bgcolor:'#131826', plot_bgcolor:'#131826', xaxis:{title:'Trade Size (MM)'}, yaxis:{title:'Depth x'}, margin:{t:20,l:50,r:20,b:50}});
  }catch(e){ console.error(e); }
}


