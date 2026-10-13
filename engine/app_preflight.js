
(function(){
'use strict';

/* ── Preflight debounce wiring ── */
let _pfTimer = null;
let _pfCurrentText = '';

function _simWirePreflight() {
  const ta = document.getElementById('sim-custom-text');
  if (!ta || ta._pfWired) return;
  ta._pfWired = true;
  ta.addEventListener('input', () => {
    clearTimeout(_pfTimer);
    const text = ta.value.trim();
    if (text.length < 10) { _hidePreflight(); return; }
    _pfTimer = setTimeout(() => _runPreflight(text), 750);
  });
}

function _hidePreflight() {
  const card = document.getElementById('sim-preflight-card');
  if (card) card.style.display = 'none';
}

/* ── Core preflight analysis (client-side BFS) ── */
async function _runPreflight(text) {
  const card = document.getElementById('sim-preflight-card');
  const body = document.getElementById('sim-pf-body');
  const nodesEl = document.getElementById('sim-pf-nodes');
  const insightEl = document.getElementById('sim-pf-insight');
  if (!card) return;
  card.style.display = 'block';
  body.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--ink-3);padding:10px;font-size:12px">Analizando escenario…</div>';
  nodesEl.innerHTML = '';
  insightEl.style.display = 'none';

  // 1. Find nodes mentioned in text
  const textLower = text.toLowerCase();
  const mentioned = (window.NODES || []).filter(n => {
    if (textLower.includes(n.label.toLowerCase())) return true;
    if (n.id && textLower.includes(n.id.toLowerCase())) return true;
    if (n.mkt && textLower.includes(n.mkt.toLowerCase())) return true;
    return false;
  });

  // 2. BFS cascade up to 3 hops
  const linkMap = {};
  (window.LINKS || []).forEach(l => {
    const s = typeof l.source === 'object' ? l.source.id : l.source;
    const t = typeof l.target === 'object' ? l.target.id : l.target;
    (linkMap[s] = linkMap[s] || []).push(t);
    (linkMap[t] = linkMap[t] || []).push(s);
  });
  const affected = new Set(mentioned.map(n => n.id));
  let frontier = mentioned.map(n => n.id);
  for (let hop = 0; hop < 3; hop++) {
    const next = [];
    frontier.forEach(id => {
      (linkMap[id] || []).forEach(nb => { if (!affected.has(nb)) { affected.add(nb); next.push(nb); } });
    });
    frontier = next;
    if (!frontier.length) break;
  }
  const affectedNodes = [...affected].map(id => (window.NODE_BY_ID||{})[id]).filter(Boolean);

  // 3. Compute metrics
  const cats = {};
  affectedNodes.forEach(n => cats[n.cat] = (cats[n.cat]||0)+1);
  const topCats = Object.entries(cats).sort((a,b)=>b[1]-a[1]).slice(0,4);
  const portfolioExposed = affectedNodes.filter(n => (window.MKT?.pos||{})[n.id]?.sh > 0);
  const nrsScores = affectedNodes.map(n => typeof computeNRS === 'function' ? computeNRS(n.id) : 50);
  const avgNRS = nrsScores.length ? Math.round(nrsScores.reduce((a,b)=>a+b,0)/nrsScores.length) : 50;
  const contextTokens = Math.ceil(text.length / 4) + affectedNodes.length * 12;
  const totalTokens = Math.round(contextTokens * 2.2);
  const costUsd = totalTokens * 0.00000025;

  // 4. Render stats
  const nrsColor = avgNRS < 40 ? '#f87171' : avgNRS < 65 ? '#f59e0b' : '#34d399';
  body.innerHTML = [
    { label: 'Nodos afectados', value: affectedNodes.length, sub: `${mentioned.length} directos · ${affectedNodes.length-mentioned.length} cascada`, color: '#60a5fa' },
    { label: 'NRS promedio', value: avgNRS, sub: 'Resiliencia de nodos afectados', color: nrsColor },
    { label: 'Posiciones expuestas', value: portfolioExposed.length, sub: portfolioExposed.length ? portfolioExposed.map(n=>n.label).slice(0,2).join(', ')+'…' : 'Sin posiciones abiertas', color: portfolioExposed.length ? '#f59e0b' : 'var(--ink-3)' },
    { label: 'Tokens estimados', value: totalTokens >= 1000 ? (totalTokens/1000).toFixed(1)+'K' : totalTokens, sub: `~$${costUsd < 0.01 ? costUsd.toFixed(4) : costUsd.toFixed(2)} USD`, color: 'var(--ink-2)' },
    { label: 'Tiempo estimado', value: affectedNodes.length > 80 ? '2-4 min' : '1-2 min', sub: 'con los motores internos', color: 'var(--ink-2)' },
    { label: 'Categorías', value: topCats.length, sub: topCats.map(([c,n])=>`${c.replace(/_/g,' ')} (${n})`).slice(0,2).join(' · '), color: '#a78bfa' },
  ].map(m => `<div style="padding:10px;background:var(--surface-2);border-radius:8px">
    <div style="font-size:10px;color:var(--ink-3);margin-bottom:4px;text-transform:uppercase;letter-spacing:.05em">${m.label}</div>
    <div style="font-size:20px;font-weight:800;color:${m.color}">${m.value}</div>
    <div style="font-size:10px;color:var(--ink-3);margin-top:2px;line-height:1.3">${m.sub}</div>
  </div>`).join('');

  // 5. Top affected node chips
  const topNodes = affectedNodes
    .sort((a,b) => (typeof computeNRS==='function' ? computeNRS(a.id) - computeNRS(b.id) : 0))
    .slice(0, 12);
  nodesEl.innerHTML = `<div style="width:100%;font-size:10px;color:var(--ink-3);margin-bottom:4px;text-transform:uppercase;letter-spacing:.06em">Nodos más expuestos</div>` +
    topNodes.map(n => {
      const nrs = typeof computeNRS==='function' ? computeNRS(n.id) : 50;
      const col = nrs < 35 ? '#f87171' : nrs < 60 ? '#f59e0b' : '#34d399';
      return `<span onclick="switchTab('map');setTimeout(()=>jumpTo('${n.id}'),80)"
        style="font-size:11px;padding:3px 9px;background:var(--surface-2);border:1px solid var(--line);
        border-radius:12px;cursor:pointer;color:var(--ink-2);border-left:3px solid ${col}"
        title="NRS: ${nrs}">${n.label}</span>`;
    }).join('');

  // 6. Optional AI insight (async, non-blocking)
  _fetchPreflightInsight(text, affectedNodes.length, avgNRS, topCats);
}

async function _fetchPreflightInsight(text, nodeCount, avgNRS, topCats) {
  const insightEl = document.getElementById('sim-pf-insight');
  if (!insightEl) return;

  try {
    const catStr = topCats.map(([c,n])=>`${c}(${n})`).join(', ');
    const prompt = `Semiconductor/AI/space supply chain scenario:\n"${text.slice(0,300)}"\n\nGraph impact: ${nodeCount} nodes affected, avg NRS resilience ${avgNRS}/100, categories: ${catStr}.\n\nIn 2 sentences: what is the primary risk vector and which node category is most exposed?`;
    const r = await fetch('/api/ai/analyze', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ system: 'You are a supply chain risk analyst. Reply in exactly 2 sentences.', prompt, max_tokens: 120 })
    });
    const d = await r.json();
    if (d.result) {
      insightEl.style.display = 'block';
      insightEl.textContent = '💡 ' + d.result;
    }
  } catch {}
}

/* ── Wire preflight when sim tab activates ── */
const _origInitSimTab = window.initSimTab;
window.initSimTab = function() {
  _origInitSimTab && _origInitSimTab();
  setTimeout(_simWirePreflight, 100);
};

// Also wire immediately if sim tab was already inited
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(_simWirePreflight, 1500);
});

})();
