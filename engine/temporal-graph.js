// engine/temporal-graph.js — Grafo de Conocimiento Temporal (Khipus AI Finance)
// Reemplaza la vista 3D. Cada hecho tiene ventana de validez (valid_from →
// valid_until). Un timeline deslizable/reproducible muestra cómo las relaciones
// aparecen, están vigentes o expiran a lo largo del tiempo. Funciona 100%
// client-side (deriva de TEMPORAL_SEED_FACTS + LINKS + PREIPO_INTEL); el backend
// Graphiti/Neo4j es un upgrade opcional. Expone window.initTKGTab.

(function () {
  'use strict';

  let _built = false, _facts = [], _sim = null, _svg = null, _root = null;
  let _linkSel = null, _nodeSel = null, _labelSel = null;
  let _minMs = 0, _maxMs = 0, _dateMs = 0, _playTimer = null, _tab = 'viz';
  let _search = '';

  const COL = { vigente: '#4ade80', expirado: '#6b7280', futuro: '#3a3a5e', node: '#a78bfa' };

  const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const catColor = cat => { try { return (typeof getCatColorHex === 'function' && getCatColorHex(cat)) || COL.node; } catch (e) { return COL.node; } };

  function toMs(s) {
    if (!s) return null;
    const p = String(s).trim();
    if (/^\d{4}$/.test(p)) return Date.parse(p + '-01-01');
    if (/^\d{4}-\d{2}$/.test(p)) return Date.parse(p + '-01');
    const t = Date.parse(p);
    return isNaN(t) ? null : t;
  }
  const fmtDate = ms => { const d = new Date(ms); return d.toLocaleDateString('es', { year: 'numeric', month: 'short' }); };

  // ── Derivar todos los hechos temporales ─────────────────────────────────────
  function deriveFacts() {
    const NB = window.NODE_BY_ID || {};
    const out = [];
    const push = f => {
      f._from = toMs(f.valid_from);
      f._until = f.valid_until ? toMs(f.valid_until) : null;
      f._isEdge = f.object_type === 'node' && !!NB[f.subject] && !!NB[f.object];
      out.push(f);
    };

    // 1) Hechos curados
    (window.TEMPORAL_SEED_FACTS || []).forEach(f => push({ ...f }));

    // 2) Rondas de financiación (PREIPO_INTEL) → hechos con fecha
    const PI = window.PREIPO_INTEL || {};
    Object.entries(PI).forEach(([id, intel]) => {
      (intel.rounds || []).forEach((r, i) => {
        push({
          id: `tf_fund_${id}_${i}`, subject: id, predicate: `${r.round || 'ronda'} · ${r.amount || ''}`,
          object: r.lead || '', object_type: (NB[r.lead] ? 'node' : 'literal'),
          valid_from: r.date || '2024', valid_until: null, source: 'preipo', confidence: 0.85,
          group: `g_fund_${id}`, meta: { headline: `${(NB[id] && NB[id].label) || id}: ${r.round || ''} ${r.amount || ''}`, impact: 5 },
        });
      });
    });

    // 3) Cadena de suministro (LINKS más fuertes) → aristas
    const links = [...(window.LINKS || [])].sort((a, b) => (b.w || 0) - (a.w || 0)).slice(0, 34);
    const lid = v => (typeof v === 'object' && v !== null) ? v.id : v;
    links.forEach((l, i) => {
      const s = lid(l.source), t = lid(l.target);
      if (!NB[s] || !NB[t]) return;
      if (out.some(f => f._isEdge && f.subject === s && f.object === t)) return; // no duplicar con curados
      push({
        id: `tf_link_${i}`, subject: s, predicate: l.rel || l.type || 'abastece a', object: t, object_type: 'node',
        valid_from: '2022-01-01', valid_until: null, source: 'link', confidence: 0.7,
        group: 'g_supply', meta: { headline: `${(NB[s] && NB[s].label) || s} → ${(NB[t] && NB[t].label) || t}`, impact: Math.min(9, (l.w || 2) + 2) },
      });
    });
    return out;
  }

  function status(f, ms) {
    if (f._from && f._from > ms) return 'futuro';
    if (f._until && f._until <= ms) return 'expirado';
    return 'vigente';
  }
  function matchesSearch(f) {
    if (!_search) return true;
    const q = _search.toLowerCase();
    return ((f.subject || '') + ' ' + (f.object || '') + ' ' + (f.predicate || '') + ' ' + ((f.meta && f.meta.headline) || '')).toLowerCase().includes(q);
  }

  // ── UI ──────────────────────────────────────────────────────────────────────
  window.initTKGTab = function () {
    const panel = document.getElementById('tkg-panel');
    if (!panel) return;
    if (_built) { _resize(); return; }
    if (typeof d3 === 'undefined') { panel.innerHTML = '<div style="padding:40px;text-align:center;color:var(--ink-3)">D3 no disponible (revisa conexión).</div>'; return; }
    _built = true;
    _facts = deriveFacts();
    const froms = _facts.map(f => f._from).filter(Boolean);
    _minMs = froms.length ? Math.min(...froms) : Date.parse('2019-01-01');
    _maxMs = Date.parse('2026-12-31');
    _dateMs = _maxMs;

    panel.innerHTML = `
      <div style="max-width:1200px;margin:0 auto;padding:22px 24px 40px">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:6px">
          <h2 style="font-family:'Fraunces',serif;font-size:24px;font-weight:700;margin:0">◈ Grafo de Conocimiento Temporal</h2>
          <span id="tkg-store" style="font-size:10px;padding:3px 9px;border-radius:20px;background:var(--surface-2);border:1px solid var(--line);color:var(--ink-3)">memoria: nativa</span>
        </div>
        <p style="font-size:12.5px;color:var(--ink-3);margin:0 0 14px">Cada hecho tiene una <b>ventana de validez</b>. Mueve la línea de tiempo (o dale ▶) para ver cómo las relaciones aparecen, están vigentes o expiran.</p>

        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px">
          <input id="tkg-search" placeholder="Buscar (empresa, relación, evento)…" style="flex:1;min-width:200px;padding:8px 12px;border:1px solid var(--line);border-radius:8px;background:var(--surface-2);color:var(--ink);font-size:13px">
          <div class="seg" id="tkg-tabseg">
            <button data-t="viz" class="active">◈ Grafo</button>
            <button data-t="facts">☰ Hechos</button>
          </div>
        </div>

        <div style="display:flex;gap:10px;align-items:center;margin-bottom:12px;background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:10px 14px">
          <button id="tkg-play" title="Reproducir el tiempo" style="flex-shrink:0;width:34px;height:34px;border-radius:50%;border:1px solid var(--violet);background:none;color:var(--violet);cursor:pointer;font-size:13px">▶</button>
          <input id="tkg-time" type="range" min="${_minMs}" max="${_maxMs}" value="${_dateMs}" step="2592000000" style="flex:1;accent-color:var(--violet)">
          <span id="tkg-datelbl" style="flex-shrink:0;min-width:96px;text-align:right;font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:700;color:var(--ink-1)"></span>
        </div>

        <div id="tkg-viz">
          <div style="position:relative;border:1px solid var(--line);border-radius:12px;overflow:hidden;background:radial-gradient(120% 120% at 50% 0%, rgba(124,58,237,.06), transparent 60%),var(--bg)">
            <svg id="tkg-svg" style="width:100%;height:520px;display:block;cursor:grab"></svg>
            <div style="position:absolute;bottom:10px;left:14px;display:flex;gap:14px;font-size:10px;color:var(--ink-3)">
              <span><span style="display:inline-block;width:16px;height:3px;background:${COL.vigente};vertical-align:middle;border-radius:2px"></span> vigente</span>
              <span><span style="display:inline-block;width:16px;height:0;border-top:2px dashed ${COL.expirado};vertical-align:middle"></span> expirado</span>
              <span style="color:var(--ink-3)">clic en nodo → verlo en el mapa</span>
            </div>
          </div>
        </div>
        <div id="tkg-facts" style="display:none"></div>
      </div>`;

    // wire
    panel.querySelector('#tkg-search').addEventListener('input', e => { _search = e.target.value; _refresh(); });
    panel.querySelectorAll('#tkg-tabseg button').forEach(b => b.addEventListener('click', () => {
      panel.querySelectorAll('#tkg-tabseg button').forEach(x => x.classList.remove('active'));
      b.classList.add('active'); _tab = b.dataset.t;
      panel.querySelector('#tkg-viz').style.display = _tab === 'viz' ? 'block' : 'none';
      panel.querySelector('#tkg-facts').style.display = _tab === 'facts' ? 'block' : 'none';
      if (_tab === 'viz') { _resize(); _refresh(); } else _renderFacts();
    }));
    const slider = panel.querySelector('#tkg-time');
    slider.addEventListener('input', e => { _dateMs = +e.target.value; _stopPlay(); _refresh(); });
    panel.querySelector('#tkg-play').addEventListener('click', _togglePlay);

    _buildGraph();
    _refresh();
    _checkBackendStore();
  };

  function _buildGraph() {
    const svgEl = document.getElementById('tkg-svg'); if (!svgEl) return;
    const w = svgEl.clientWidth || 900, h = 520;
    const edges = _facts.filter(f => f._isEdge);
    const ids = new Set(); edges.forEach(e => { ids.add(e.subject); ids.add(e.object); });
    const NB = window.NODE_BY_ID || {};
    const nodes = [...ids].map(id => ({ id, label: (NB[id] && NB[id].label) || id, cat: NB[id] && NB[id].cat }));
    const links = edges.map(e => ({ ...e, source: e.subject, target: e.object }));

    _svg = d3.select(svgEl); _svg.selectAll('*').remove();
    _root = _svg.append('g');
    _svg.call(d3.zoom().scaleExtent([0.3, 3]).on('zoom', ev => _root.attr('transform', ev.transform)));

    _linkSel = _root.append('g').selectAll('line').data(links).join('line')
      .attr('stroke-width', 1.6).attr('stroke-linecap', 'round');
    _nodeSel = _root.append('g').selectAll('circle').data(nodes).join('circle')
      .attr('r', 7).attr('fill', d => catColor(d.cat)).attr('stroke', '#0a0a14').attr('stroke-width', 1.5)
      .style('cursor', 'pointer')
      .on('click', (ev, d) => { if (typeof switchTab === 'function') switchTab('map'); if (typeof jumpTo === 'function') setTimeout(() => jumpTo(d.id), 90); })
      .call(d3.drag()
        .on('start', (ev, d) => { if (!ev.active) _sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on('drag', (ev, d) => { d.fx = ev.x; d.fy = ev.y; })
        .on('end', (ev, d) => { if (!ev.active) _sim.alphaTarget(0); d.fx = null; d.fy = null; }));
    _nodeSel.append('title').text(d => d.label);
    _labelSel = _root.append('g').selectAll('text').data(nodes).join('text')
      .text(d => d.label.length > 16 ? d.label.slice(0, 15) + '…' : d.label)
      .attr('font-size', '10px').attr('fill', 'var(--ink-2)').attr('text-anchor', 'middle').attr('dy', -11)
      .style('pointer-events', 'none');

    _sim = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(95))
      .force('charge', d3.forceManyBody().strength(-260))
      .force('center', d3.forceCenter(w / 2, h / 2))
      .force('collide', d3.forceCollide(24))
      .on('tick', () => {
        _linkSel.attr('x1', d => d.source.x).attr('y1', d => d.source.y).attr('x2', d => d.target.x).attr('y2', d => d.target.y);
        _nodeSel.attr('cx', d => d.x).attr('cy', d => d.y);
        _labelSel.attr('x', d => d.x).attr('y', d => d.y);
      });
  }

  function _refresh() {
    _updateDateLabel();
    if (_linkSel) {
      _linkSel
        .attr('stroke', d => { const st = status(d, _dateMs); return st === 'vigente' ? COL.vigente : st === 'expirado' ? COL.expirado : COL.futuro; })
        .attr('stroke-opacity', d => { const st = status(d, _dateMs); const m = matchesSearch(d); if (!m) return 0.05; return st === 'vigente' ? 0.85 : st === 'expirado' ? 0.35 : 0.1; })
        .attr('stroke-dasharray', d => status(d, _dateMs) === 'vigente' ? null : '4,4');
    }
    if (_nodeSel) {
      _nodeSel.attr('opacity', d => {
        const rel = _facts.some(f => f._isEdge && (f.subject === d.id || f.object === d.id) && matchesSearch(f));
        return rel ? 1 : 0.15;
      });
    }
    if (_tab === 'facts') _renderFacts();
  }

  function _renderFacts() {
    const el = document.getElementById('tkg-facts'); if (!el) return;
    const rows = _facts.filter(matchesSearch).map(f => ({ f, st: status(f, _dateMs) }))
      .sort((a, b) => (b.f._from || 0) - (a.f._from || 0));
    const NB = window.NODE_BY_ID || {};
    const lbl = id => (NB[id] && NB[id].label) || id;
    const badge = st => {
      const c = st === 'vigente' ? COL.vigente : st === 'expirado' ? COL.expirado : '#8a7de0';
      const t = st === 'vigente' ? 'VIGENTE' : st === 'expirado' ? 'EXPIRADO' : 'FUTURO';
      return `<span style="font-size:9px;font-weight:800;color:${c};background:${c}22;border:1px solid ${c}55;padding:2px 7px;border-radius:10px">${t}</span>`;
    };
    el.innerHTML = rows.length ? rows.map(({ f, st }) => `
      <div style="border-bottom:1px solid var(--line);padding:11px 2px;display:flex;gap:10px;align-items:flex-start">
        <div style="flex-shrink:0;margin-top:2px">${badge(st)}</div>
        <div style="flex:1;min-width:0">
          <div style="font-size:13px;color:var(--ink-1);line-height:1.4">
            <b>${esc(lbl(f.subject))}</b> <span style="color:var(--ink-3)">${esc(f.predicate)}</span> ${f.object_type === 'node' ? '<b>' + esc(lbl(f.object)) + '</b>' : '<span style="color:var(--ink-2)">' + esc(f.object) + '</span>'}
          </div>
          <div style="font-size:10.5px;color:var(--ink-3);margin-top:3px;font-family:'JetBrains Mono',monospace">
            ${f.valid_from ? fmtDate(f._from) : '—'} → ${f._until ? fmtDate(f._until) : 'hoy'} · ${esc(f.source)} · conf ${(f.confidence != null ? Math.round(f.confidence * 100) : '—')}%
          </div>
        </div>
      </div>`).join('') : '<div style="padding:30px;text-align:center;color:var(--ink-3);font-size:13px">Sin hechos que coincidan.</div>';
  }

  function _updateDateLabel() { const el = document.getElementById('tkg-datelbl'); if (el) el.textContent = fmtDate(_dateMs); const s = document.getElementById('tkg-time'); if (s && +s.value !== _dateMs) s.value = _dateMs; }

  function _togglePlay() { if (_playTimer) _stopPlay(); else _startPlay(); }
  function _startPlay() {
    const btn = document.getElementById('tkg-play'); if (btn) btn.textContent = '❚❚';
    if (_dateMs >= _maxMs) _dateMs = _minMs;
    _playTimer = setInterval(() => {
      _dateMs = Math.min(_maxMs, _dateMs + 2592000000 * 2); // +2 meses por tick
      _refresh();
      if (_dateMs >= _maxMs) _stopPlay();
    }, 260);
  }
  function _stopPlay() { if (_playTimer) { clearInterval(_playTimer); _playTimer = null; } const btn = document.getElementById('tkg-play'); if (btn) btn.textContent = '▶'; }

  function _resize() { if (_sim && _svg) { const svgEl = document.getElementById('tkg-svg'); if (svgEl) { const w = svgEl.clientWidth || 900; _sim.force('center', d3.forceCenter(w / 2, 260)); _sim.alpha(0.3).restart(); } } }

  // Si el backend expone el grafo (Graphiti/Neo4j), lo indicamos en el badge.
  function _checkBackendStore() {
    try {
      const base = (typeof BASE !== 'undefined') ? BASE : '';
      fetch(`${base}/api/grafo/estado`).then(r => r.ok ? r.json() : null).then(d => {
        if (d && d.store) { const el = document.getElementById('tkg-store'); if (el) el.textContent = 'memoria: ' + d.store + (d.neo4j_connected ? ' 🟢' : ''); }
      }).catch(() => {});
    } catch (e) {}
  }
})();
