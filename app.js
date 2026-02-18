let raw = [];
let sortKey = 'score';
let sortDir = -1;

function fmt(n, d=2){
  if (n === null || n === undefined || Number.isNaN(n)) return '';
  return Number(n).toFixed(d);
}

function render(){
  const q = document.getElementById('search').value.trim().toLowerCase();
  const sec = document.getElementById('sector').value;
  const onlyPass = document.getElementById('onlyPass').checked;

  let rows = raw.slice();

  if (q){
    rows = rows.filter(r =>
      (r.ticker||'').toLowerCase().includes(q) ||
      (r.company||'').toLowerCase().includes(q)
    );
  }
  if (sec && sec !== 'ALL'){
    rows = rows.filter(r => r.sector === sec);
  }
  if (onlyPass){
    rows = rows.filter(r => r.pass === true);
  }

  rows.sort((a,b) => {
    const va = a[sortKey], vb = b[sortKey];
    if (va === vb) return 0;
    if (va === null || va === undefined) return 1;
    if (vb === null || vb === undefined) return -1;
    return (va > vb ? 1 : -1) * sortDir;
  });

  const tb = document.querySelector('#tbl tbody');
  tb.innerHTML = rows.map(r => `
    <tr>
      <td><span class="badge good">${fmt(r.score,0)}</span></td>
      <td><b>${r.ticker}</b></td>
      <td>${r.company||''}</td>
      <td>${r.sector||''}</td>
      <td>${fmt(r.price)}</td>
      <td>${fmt(r.rsi)}</td>
      <td>${fmt(r.ma50)}</td>
      <td class="${r.p_vs_ma50>=0?'good':'bad'}">${fmt(r.p_vs_ma50)}%</td>
      <td class="${r.ret3m>=0?'good':'bad'}">${fmt(r.ret3m)}%</td>
      <td class="${(r.relvol||0)>=1.2?'good':'bad'}">${fmt(r.relvol)}</td>
    </tr>
  `).join('');
}

async function load(){
  const res = await fetch('./data/sp500_momentum.json', {cache:'no-store'});
  const payload = await res.json();
  document.getElementById('lastUpdate').textContent = 'Actualización: ' + (payload.updated_at || '—');
  raw = payload.rows || [];

  const sectors = Array.from(new Set(raw.map(r => r.sector).filter(Boolean))).sort();
  const sel = document.getElementById('sector');
  sel.innerHTML = ['<option value="ALL">Todos los sectores</option>']
    .concat(sectors.map(s => `<option value="${s}">${s}</option>`)).join('');

  render();
}

document.addEventListener('click', (e) => {
  const th = e.target.closest('th[data-sort]');
  if (!th) return;
  const key = th.getAttribute('data-sort');
  if (sortKey === key) sortDir *= -1;
  else { sortKey = key; sortDir = -1; }
  render();
});

['search','sector','onlyPass'].forEach(id => {
  document.addEventListener('input', (e) => { if (e.target && e.target.id === id) render(); });
  document.addEventListener('change', (e) => { if (e.target && e.target.id === id) render(); });
});

document.getElementById('refreshBtn').addEventListener('click', load);
load().catch(() => document.getElementById('lastUpdate').textContent = 'Error al cargar datos.');
