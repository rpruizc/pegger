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
  for(const r of rows){
    const tr = document.createElement('tr');
    const ts = new Date(r.timestamp).toLocaleTimeString();
    tr.innerHTML = `<td>${r.symbol}</td><td>${r.venue}</td><td>${r.price.toFixed(6)}</td><td class="small">${ts}</td>`;
    tb.appendChild(tr);
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
});


