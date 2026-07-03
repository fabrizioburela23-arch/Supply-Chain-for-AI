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
  // Etapa 2/3: filtros por tipo, color de arista, y motor de microsimulación
  let _hiddenTypes = new Set();       // tipos de objeto ocultos por el usuario
  let _edgeColorMode = 'time';        // 'time' (validez) | 'rel' (tipo de relación)
  let _simMode = false;               // clic en nodo = disparar shock
  let _shock = null;                  // { origin, affected:Set, byType:{} } o null
  let _nodeType = {};                 // id -> tipo (Company/Tech/…)
  let _impactAdj = {};                // id -> [ {to, fact} ] : si id cae, 'to' se afecta
  let _impactRev = {};                // id -> [ {to, fact} ] : id depende de 'to' (upstream)
  let _allNodeIds = [];               // ids presentes en el grafo
  let _searchNodes = new Set(), _searchAll = true;
  let _objOpen = null;                // id del objeto abierto en la ficha lateral
  const lidOf = v => (v && typeof v === 'object') ? v.id : v;

  const COL = { vigente: '#4ade80', expirado: '#6b7280', futuro: '#3a3a5e', node: '#a78bfa' };

  const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const catColor = cat => { try { return (typeof getCatColorHex === 'function' && getCatColorHex(cat)) || COL.node; } catch (e) { return COL.node; } };

  // Resuelve una entidad desde el catálogo de empresas (NODE_BY_ID) o desde la
  // ontología (ONTOLOGY._byId). Devuelve {id,label,type,cat} o null.
  function resolveEntity(id) {
    const NB = window.NODE_BY_ID || {};
    if (NB[id]) return { id, label: NB[id].label || id, type: 'Company', cat: NB[id].cat };
    const O = (window.ONTOLOGY && window.ONTOLOGY._byId) || {};
    if (O[id]) return { id, label: O[id].label || id, type: O[id].type, cat: null };
    return null;
  }
  // Color de un nodo según su tipo (empresa → color de categoría; objeto → color del tipo).
  function entityColor(n) {
    if (!n || n.type === 'Company' || !n.type) return catColor(n && n.cat);
    const t = window.ONTOLOGY && window.ONTOLOGY.types && window.ONTOLOGY.types[n.type];
    return (t && t.color) || COL.node;
  }

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
      // arista válida si AMBOS extremos resuelven (empresa u objeto de ontología)
      f._isEdge = f.object_type === 'node' && !!resolveEntity(f.subject) && !!resolveEntity(f.object);
      out.push(f);
    };

    // 1) Hechos curados — cada uno en su propio try para que uno malo no rompa todo
    try {
      (window.TEMPORAL_SEED_FACTS || []).forEach(f => { try { push({ ...f }); } catch (e) {} });
    } catch (e) {}

    // 2) Rondas de financiación (PREIPO_INTEL) → hechos con fecha
    try {
      const PI = window.PREIPO_INTEL || {};
      Object.entries(PI).forEach(([id, intel]) => {
        const rounds = (intel && Array.isArray(intel.rounds)) ? intel.rounds : [];
        rounds.forEach((r, i) => {
          if (!r) return;
          try {
            push({
              id: `tf_fund_${id}_${i}`, subject: id, predicate: `${r.round || 'ronda'} · ${r.amount || ''}`,
              object: r.lead || '', object_type: (NB[r.lead] ? 'node' : 'literal'),
              valid_from: r.date || '2024', valid_until: null, source: 'preipo', confidence: 0.85,
              group: `g_fund_${id}`, meta: { headline: `${(NB[id] && NB[id].label) || id}: ${r.round || ''} ${r.amount || ''}`, impact: 5 },
            });
          } catch (e) {}
        });
      });
    } catch (e) {}

    // 3) Cadena de suministro (LINKS más fuertes) → aristas
    try {
      const lid = v => (v && typeof v === 'object') ? v.id : v;
      const links = [...(window.LINKS || [])].sort((a, b) => ((b && b.w) || 0) - ((a && a.w) || 0)).slice(0, 34);
      links.forEach((l, i) => {
        if (!l) return;
        try {
          const s = lid(l.source), t = lid(l.target);
          if (!NB[s] || !NB[t]) return;
          if (out.some(f => f._isEdge && f.subject === s && f.object === t)) return; // no duplicar con curados
          push({
            id: `tf_link_${i}`, subject: s, predicate: l.rel || l.type || 'abastece a', object: t, object_type: 'node',
            valid_from: '2022-01-01', valid_until: null, source: 'link', confidence: 0.7,
            group: 'g_supply', meta: { headline: `${(NB[s] && NB[s].label) || s} → ${(NB[t] && NB[t].label) || t}`, impact: Math.min(9, (l.w || 2) + 2) },
          });
        } catch (e) {}
      });
    } catch (e) {}
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
    try {
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
          <span id="tkg-ontology-badge" style="display:none;font-size:10px;padding:3px 9px;border-radius:20px;background:var(--surface-2);border:1px solid var(--violet);color:var(--violet)"></span>
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

        <div id="tkg-typelegend" style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px"></div>

        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:10px">
          <div class="seg" id="tkg-edgemode">
            <button data-m="time" class="active">⏱ color por tiempo</button>
            <button data-m="rel">🔗 color por relación</button>
          </div>
          <button id="tkg-adv-toggle" style="font-size:12px;padding:6px 12px;border-radius:8px;border:1px solid var(--line);background:var(--surface-2);color:var(--ink-2);cursor:pointer;margin-left:auto">🔬 Análisis avanzado ▾</button>
        </div>

        <div id="tkg-advanced-row" style="display:none;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:10px;padding:10px;background:var(--surface-2);border:1px solid var(--line);border-radius:10px">
          <button id="tkg-simbtn" style="font-size:12px;padding:6px 12px;border-radius:8px;border:1px solid var(--violet);background:none;color:var(--violet);cursor:pointer">⚡ Modo simulación</button>
          <button id="tkg-chokepoints" style="font-size:12px;padding:6px 12px;border-radius:8px;border:1px solid var(--line);background:var(--bg);color:var(--ink-2);cursor:pointer">🏛 Chokepoints</button>
          <button id="tkg-exposure" style="font-size:12px;padding:6px 12px;border-radius:8px;border:1px solid var(--line);background:var(--bg);color:var(--ink-2);cursor:pointer">🎯 Mi exposición</button>
          <button id="tkg-reset" style="font-size:12px;padding:6px 12px;border-radius:8px;border:1px solid var(--line);background:var(--bg);color:var(--ink-2);cursor:pointer;display:none">↺ Reiniciar</button>
          <span id="tkg-simhint" style="font-size:11px;color:var(--ink-3)"></span>
        </div>

        <div id="tkg-insights" style="display:none;margin-bottom:10px"></div>
        <div id="tkg-impact" style="display:none;margin-bottom:10px"></div>

        <div id="tkg-viz">
          <div style="position:relative;border:1px solid var(--line);border-radius:12px;overflow:hidden;background:radial-gradient(120% 120% at 50% 0%, rgba(124,58,237,.06), transparent 60%),var(--bg)">
            <svg id="tkg-svg" style="width:100%;height:520px;display:block;cursor:grab"></svg>
            <div style="position:absolute;bottom:10px;left:14px;display:flex;gap:14px;font-size:10px;color:var(--ink-3)">
              <span><span style="display:inline-block;width:16px;height:3px;background:${COL.vigente};vertical-align:middle;border-radius:2px"></span> vigente</span>
              <span><span style="display:inline-block;width:16px;height:0;border-top:2px dashed ${COL.expirado};vertical-align:middle"></span> expirado</span>
              <span style="color:var(--ink-3)">clic en nodo → ficha del objeto</span>
            </div>
            <div id="tkg-objpanel" style="position:absolute;top:0;right:0;width:min(370px,90%);height:100%;background:rgba(9,11,20,.98);border-left:1px solid var(--line);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);overflow-y:auto;transform:translateX(101%);transition:transform .22s cubic-bezier(.2,.8,.2,1);z-index:6"></div>
          </div>
        </div>
        <div id="tkg-facts" style="display:none"></div>
      </div>`;

    // wire
    panel.querySelector('#tkg-search').addEventListener('input', e => { _search = e.target.value; _applySearch(); _refresh(); });
    panel.querySelectorAll('#tkg-tabseg button').forEach(b => b.addEventListener('click', () => {
      panel.querySelectorAll('#tkg-tabseg button').forEach(x => x.classList.remove('active'));
      b.classList.add('active'); _tab = b.dataset.t;
      panel.querySelector('#tkg-viz').style.display = _tab === 'viz' ? 'block' : 'none';
      panel.querySelector('#tkg-facts').style.display = _tab === 'facts' ? 'block' : 'none';
      if (_tab === 'viz') { _resize(); _refresh(); } else _renderFacts();
    }));
    const slider = panel.querySelector('#tkg-time');
    // throttle con rAF: arrastrar el slider dispara muchos 'input'; coalescemos a 1 por frame
    let _sliderRAF = 0;
    slider.addEventListener('input', e => {
      _dateMs = +e.target.value; _stopPlay();
      if (_sliderRAF) return;
      _sliderRAF = requestAnimationFrame(() => { _sliderRAF = 0; _refresh(); });
    });
    panel.querySelector('#tkg-play').addEventListener('click', _togglePlay);

    // Etapa 2: color de arista por tiempo vs por tipo de relación
    panel.querySelectorAll('#tkg-edgemode button').forEach(b => b.addEventListener('click', () => {
      panel.querySelectorAll('#tkg-edgemode button').forEach(x => x.classList.remove('active'));
      b.classList.add('active'); _edgeColorMode = b.dataset.m; _refresh();
    }));
    // Etapa 3: modo simulación (clic en nodo = shock) y reinicio
    panel.querySelector('#tkg-simbtn').addEventListener('click', () => _toggleSimMode());
    panel.querySelector('#tkg-reset').addEventListener('click', () => _clearShock());
    // Lote 2 (insights de inversión)
    panel.querySelector('#tkg-chokepoints').addEventListener('click', () => _runChokepoints());
    panel.querySelector('#tkg-exposure').addEventListener('click', () => _runExposure());

    // Simplicidad por defecto: las herramientas avanzadas (simulación, chokepoints,
    // exposición) empiezan ocultas — un clic las revela para quien las quiera.
    panel.querySelector('#tkg-adv-toggle').addEventListener('click', () => {
      const row = panel.querySelector('#tkg-advanced-row');
      const btn = panel.querySelector('#tkg-adv-toggle');
      const show = row.style.display === 'none';
      row.style.display = show ? 'flex' : 'none';
      btn.textContent = show ? '🔬 Análisis avanzado ▴' : '🔬 Análisis avanzado ▾';
      btn.style.color = show ? 'var(--violet)' : 'var(--ink-2)';
      btn.style.borderColor = show ? 'var(--violet)' : 'var(--line)';
    });

    // El dibujo del grafo en su propio try: si el SVG falla, la UI (título,
    // línea de tiempo, lista de Hechos) sigue viva.
    _renderTypeLegend();
    try { _buildGraph(); _applySearch(); _refresh(); }
    catch (e) {
      try { console.error('[TKG] buildGraph', e); } catch (_) {}
      try {
        const viz = document.getElementById('tkg-viz');
        if (viz) viz.innerHTML = '<div style="padding:24px;color:#f87171;font-family:monospace;'
          + 'font-size:12px;white-space:pre-wrap;line-height:1.5">Grafo: error al dibujar →\n'
          + esc((e && e.message) || String(e)) + '\n\n' + esc((e && e.stack ? e.stack.slice(0, 400) : '')) + '</div>';
      } catch (_) {}
    }
    _checkBackendStore();
    // precargar precios en vivo para las fichas de objeto (A: datos vivos)
    if (window.SERVER_MODE && window.MKT && !window.MKT.ts && typeof window.fetchQuotes === 'function') {
      try { window.fetchQuotes(); } catch (e) {}
    }
    } catch (err) {
      _built = false;  // permitir reintento al volver a la pestaña
      const msg = (err && err.message) ? err.message : String(err);
      const stack = (err && err.stack) ? err.stack.slice(0, 500) : '';
      panel.innerHTML = '<div style="max-width:900px;margin:0 auto;padding:30px 24px;color:#f87171;'
        + 'font-family:monospace;font-size:12.5px;white-space:pre-wrap;line-height:1.5">'
        + '◈ Grafo Temporal — no pudo iniciar:\n\n' + esc(msg) + '\n\n' + esc(stack) + '</div>';
      try { console.error('[TKG] init error', err); } catch (e) {}
    }
  };

  // Leyenda de tipos de objeto (empresa, tecnología, política, país, energía…).
  function _renderTypeLegend() {
    const el = document.getElementById('tkg-typelegend'); if (!el) return;
    const types = (window.ONTOLOGY && window.ONTOLOGY.types) || { Company: { label: 'Empresa', color: COL.node, icon: '🏢' } };
    el.innerHTML = Object.keys(types).map(k => {
      const t = types[k];
      const off = _hiddenTypes.has(k);
      return `<span data-type="${k}" title="Clic para mostrar/ocultar este tipo"
        style="display:inline-flex;align-items:center;gap:5px;font-size:10.5px;cursor:pointer;user-select:none;
        color:${off ? 'var(--ink-3)' : 'var(--ink-2)'};background:var(--surface-2);border:1px solid var(--line);
        border-radius:20px;padding:3px 9px;opacity:${off ? 0.45 : 1};${off ? 'text-decoration:line-through' : ''}">
        <span style="width:9px;height:9px;border-radius:50%;background:${t.color};flex-shrink:0"></span>${t.icon || ''} ${esc(t.label)}</span>`;
    }).join('');
    el.querySelectorAll('[data-type]').forEach(chip => chip.addEventListener('click', () => {
      const k = chip.dataset.type;
      if (_hiddenTypes.has(k)) _hiddenTypes.delete(k); else _hiddenTypes.add(k);
      _renderTypeLegend(); _applyFilters();
    }));
  }

  function _svgW(svgEl) {
    return (svgEl && svgEl.clientWidth) ||
           (svgEl && svgEl.parentElement && svgEl.parentElement.clientWidth) ||
           (typeof window !== 'undefined' && Math.min(window.innerWidth - 60, 1150)) || 960;
  }

  function _buildGraph() {
    const svgEl = document.getElementById('tkg-svg'); if (!svgEl) return;
    const w = _svgW(svgEl), h = 520;
    const edges = _facts.filter(f => f._isEdge);
    const ids = new Set(); edges.forEach(e => { ids.add(e.subject); ids.add(e.object); });
    const NB = window.NODE_BY_ID || {};
    const nodes = [...ids].map(id => {
      const e = resolveEntity(id);
      return { id, label: (e && e.label) || id, type: (e && e.type) || 'Company', cat: e && e.cat };
    });
    const links = edges.map(e => ({ ...e, source: e.subject, target: e.object }));

    // Índices para filtros y microsimulación
    _nodeType = {}; nodes.forEach(n => { _nodeType[n.id] = n.type; });
    _impactAdj = {}; _impactRev = {};
    edges.forEach(f => {
      const ie = _impactEdges(f); if (!ie) return;
      (_impactAdj[ie[0]] = _impactAdj[ie[0]] || []).push({ to: ie[1], fact: f });   // si ie[0] cae → ie[1] afectado
      (_impactRev[ie[1]] = _impactRev[ie[1]] || []).push({ to: ie[0], fact: f });    // ie[1] depende de ie[0]
    });
    _allNodeIds = nodes.map(n => n.id);

    // Diagnóstico visible: cuántos hechos/aristas/nodos hay realmente.
    const dbg = document.getElementById('tkg-store');
    if (dbg) dbg.title = `hechos:${_facts.length} · aristas:${edges.length} · nodos:${nodes.length} · NODE_BY_ID:${Object.keys(NB).length}`;
    if (!nodes.length) {
      _svg = d3.select(svgEl); _svg.selectAll('*').remove();
      _svg.append('text').attr('x', 24).attr('y', 44).attr('fill', '#f87171').attr('font-size', '13px')
        .text(`Sin relaciones para dibujar — hechos:${_facts.length} aristas:${edges.length} (NODE_BY_ID:${Object.keys(NB).length}).`);
      return;
    }

    _svg = d3.select(svgEl); _svg.selectAll('*').remove();
    _root = _svg.append('g');
    _svg.call(d3.zoom().scaleExtent([0.3, 3]).on('zoom', ev => _root.attr('transform', ev.transform)));

    _linkSel = _root.append('g').selectAll('line').data(links).join('line')
      .attr('stroke-width', 1.6).attr('stroke-linecap', 'round');
    _nodeSel = _root.append('g').selectAll('circle').data(nodes).join('circle')
      .attr('r', d => d.type && d.type !== 'Company' ? 9 : 7)   // objetos de ontología un poco más grandes
      .attr('fill', d => entityColor(d)).attr('stroke', '#0a0a14').attr('stroke-width', 1.5)
      .style('cursor', 'pointer')
      .on('click', (ev, d) => {
        if (_simMode) { _runShock(d.id); return; }   // modo simulación: dispara shock
        _openObject(d.id);                            // explorar: abre la ficha del objeto
      })
      .call(d3.drag()
        .on('start', (ev, d) => { if (!ev.active) _sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on('drag', (ev, d) => { d.fx = ev.x; d.fy = ev.y; })
        .on('end', (ev, d) => { if (!ev.active) _sim.alphaTarget(0); d.fx = null; d.fy = null; }));
    _nodeSel.append('title').text(d => d.label);
    _labelSel = _root.append('g').selectAll('text').data(nodes).join('text')
      .text(d => d.label.length > 16 ? d.label.slice(0, 15) + '…' : d.label)
      .attr('font-size', '10px').attr('fill', '#9fb0d0').attr('text-anchor', 'middle').attr('dy', -11)
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

    // El panel puede estar recién mostrado (clientWidth=0 en el primer build):
    // re-centra cuando el layout ya midió el ancho real, y encuadra los nodos
    // (fit-to-view) cuando la simulación ya los posicionó, por si quedaron fuera.
    if (typeof requestAnimationFrame === 'function') requestAnimationFrame(_resize);
    setTimeout(_resize, 350);
    setTimeout(_fitView, 1100);
    setTimeout(_fitView, 2200);
  }

  // Encuadra todos los nodos dentro del SVG (por si el force los dejó fuera de vista).
  function _fitView() {
    if (!_svg || !_nodeSel || !_root) return;
    const svgEl = document.getElementById('tkg-svg'); if (!svgEl) return;
    const w = _svgW(svgEl), h = svgEl.clientHeight || 520;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity, n = 0;
    _nodeSel.each(d => {
      if (d == null || d.x == null || d.y == null || !isFinite(d.x) || !isFinite(d.y)) return;
      n++; minX = Math.min(minX, d.x); minY = Math.min(minY, d.y);
      maxX = Math.max(maxX, d.x); maxY = Math.max(maxY, d.y);
    });
    if (!n || !isFinite(minX)) return;
    const gw = Math.max(1, maxX - minX), gh = Math.max(1, maxY - minY);
    const pad = 60;
    const scale = Math.max(0.3, Math.min(2.2, Math.min((w - pad) / gw, (h - pad) / gh)));
    const tx = w / 2 - scale * (minX + maxX) / 2;
    const ty = h / 2 - scale * (minY + maxY) / 2;
    _root.attr('transform', `translate(${tx},${ty}) scale(${scale})`);
  }

  // _applySearch: SOLO al cambiar la búsqueda. Precalcula el conjunto de nodos
  // relevantes y el match por arista, luego repinta.
  function _applySearch() {
    _searchAll = !_search;
    _searchNodes = new Set();
    if (!_searchAll) _facts.forEach(f => { if (f._isEdge && matchesSearch(f)) { _searchNodes.add(f.subject); _searchNodes.add(f.object); } });
    if (_linkSel) _linkSel.each(function (d) { d._match = matchesSearch(d); });
    _refresh();
  }

  // Filtros por tipo → simplemente repintar (la lógica vive en _refresh).
  function _applyFilters() { _refresh(); }

  const _typeHidden = id => _hiddenTypes.has(_nodeType[id] || 'Company');

  function _edgeStroke(d) {
    if (_shock) {
      const a = _shock.affected.has(lidOf(d.source)), b = _shock.affected.has(lidOf(d.target));
      return (a && b) ? '#ef4444' : '#3a3a5e';
    }
    if (_edgeColorMode === 'rel') {
      const r = window.ONTOLOGY && window.ONTOLOGY.rels && window.ONTOLOGY.rels[d.rel];
      return (r && r.color) || '#6b7280';
    }
    const st = status(d, _dateMs);
    return st === 'vigente' ? COL.vigente : st === 'expirado' ? COL.expirado : COL.futuro;
  }
  function _edgeOpacity(d) {
    if (_shock) {
      const a = _shock.affected.has(lidOf(d.source)), b = _shock.affected.has(lidOf(d.target));
      return (a && b) ? 0.9 : 0.05;
    }
    const st = status(d, _dateMs);
    if (d._match === false) return 0.05;
    return st === 'vigente' ? 0.8 : st === 'expirado' ? 0.32 : 0.1;
  }

  // _refresh: repinta nodos y aristas según tiempo, búsqueda, filtros y shock.
  function _refresh() {
    _updateDateLabel();
    if (_nodeSel) {
      _nodeSel
        .attr('display', d => _typeHidden(d.id) ? 'none' : null)
        .attr('fill', d => (_shock && d.id === _shock.origin) ? '#ef4444' : entityColor(d))
        .attr('stroke', d => (_shock && _shock.affected.has(d.id)) ? '#ef4444' : '#0a0a14')
        .attr('stroke-width', d => (_shock && _shock.affected.has(d.id)) ? 2.5 : 1.5)
        .attr('opacity', d => {
          if (_typeHidden(d.id)) return 0;
          if (_shock) return _shock.affected.has(d.id) ? 1 : 0.12;
          if (!_searchAll && !_searchNodes.has(d.id)) return 0.15;
          return 1;
        });
    }
    if (_labelSel) {
      _labelSel
        .attr('display', d => _typeHidden(d.id) ? 'none' : null)
        .attr('opacity', d => {
          if (_shock) return _shock.affected.has(d.id) ? 1 : 0.1;
          if (!_searchAll && !_searchNodes.has(d.id)) return 0.2;
          return 0.9;
        });
    }
    if (_linkSel) {
      _linkSel
        .attr('display', d => (_typeHidden(lidOf(d.source)) || _typeHidden(lidOf(d.target))) ? 'none' : null)
        .attr('stroke', _edgeStroke)
        .attr('stroke-opacity', _edgeOpacity)
        .attr('stroke-dasharray', d => status(d, _dateMs) === 'vigente' ? null : '4,4');
    }
    if (_tab === 'facts') _renderFacts();
  }

  // ── Microsimulación: shock que se propaga por dependencias vigentes ──────────
  // Dirección de impacto de una arista: "si FROM cae/actúa, TO se ve afectado".
  function _impactEdges(f) {
    const rel = f.rel;
    if (rel === 'usa' || rel === 'depende') return [f.object, f.subject]; // el sujeto depende del objeto
    if (rel === 'compite' || rel === 'domina') return null;               // no es dependencia dura
    return [f.subject, f.object]; // fabrica/abastece/controla/energiza/alberga/sanciona/restringe/ (o sin rel)
  }

  function _runShock(originId) {
    if (!_impactAdj) return;
    const affected = new Set([originId]);
    const order = [{ id: originId, depth: 0 }];
    let frontier = [originId], depth = 0;
    while (frontier.length && depth < 6) {
      depth++;
      const next = [];
      frontier.forEach(id => {
        (_impactAdj[id] || []).forEach(({ to, fact }) => {
          if (status(fact, _dateMs) !== 'vigente') return;   // solo relaciones vigentes en la fecha
          if (_typeHidden(to)) return;
          if (!affected.has(to)) { affected.add(to); next.push(to); order.push({ id: to, depth }); }
        });
      });
      frontier = next;
    }
    const byType = {};
    affected.forEach(id => { const t = _nodeType[id] || 'Company'; byType[t] = (byType[t] || 0) + 1; });
    _shock = { origin: originId, affected, byType, order, port: _portfolioAtRisk(affected) };
    _refresh();
    _renderImpact();
  }

  // ── Portafolio (B): valor por posición desde MKT.pos + MKT.quotes ────────────
  function _portfolio() {
    const pos = (window.MKT && window.MKT.pos) || {};
    const NB = window.NODE_BY_ID || {};
    const out = [];
    Object.keys(pos).forEach(id => {
      const p = pos[id] || {}; const n = NB[id];
      const q = (n && n.mkt && window.MKT.quotes) ? window.MKT.quotes[n.mkt] : null;
      const price = q && q.close != null ? q.close : (p.bp || null);
      const sh = p.sh || p.shares || 0;
      const val = (price != null && sh) ? price * sh : 0;
      out.push({ id, label: (n && n.label) || id, value: val });
    });
    const total = out.reduce((s, x) => s + x.value, 0);
    return { holdings: out, total };
  }
  function _portfolioAtRisk(affected) {
    const pf = _portfolio();
    if (!pf.total) return null;
    const hit = pf.holdings.filter(h => affected.has(h.id) && h.value > 0);
    const atRisk = hit.reduce((s, x) => s + x.value, 0);
    return { atRisk, total: pf.total, pct: pf.total ? (atRisk / pf.total * 100) : 0, hit };
  }
  const _money = v => v >= 1e9 ? '$' + (v / 1e9).toFixed(1) + 'B' : v >= 1e6 ? '$' + (v / 1e6).toFixed(1) + 'M' : v >= 1e3 ? '$' + (v / 1e3).toFixed(1) + 'K' : '$' + Math.round(v);

  // Exposición: para cada posición, sube por sus dependencias (upstream) y agrega.
  function _runExposure() {
    const el = document.getElementById('tkg-insights'); if (!el) return;
    const pf = _portfolio();
    if (!pf.holdings.length) {
      el.style.display = 'block';
      el.innerHTML = `<div style="border:1px solid var(--line);background:var(--surface-2);border-radius:12px;padding:12px 14px;font-size:12.5px;color:var(--ink-2)">No tienes posiciones. Agrega empresas a tu portafolio (pestaña <b>Mercado</b>) y vuelve para ver a qué riesgos ocultos estás expuesto.</div>`;
      return;
    }
    const NB = window.NODE_BY_ID || {};
    const expCount = {};   // dep id -> nº de posiciones expuestas
    const expVal = {};     // dep id -> valor expuesto
    const ctryVal = {};    // país -> valor
    pf.holdings.forEach(h => {
      // BFS upstream desde la posición
      const seen = new Set([h.id]); let fr = [h.id], depth = 0;
      while (fr.length && depth < 6) {
        depth++; const nx = [];
        fr.forEach(id => (_impactRev[id] || []).forEach(({ to, fact }) => {
          if (status(fact, _dateMs) !== 'vigente') return;
          if (!seen.has(to)) { seen.add(to); nx.push(to); }
        }));
        fr = nx;
      }
      seen.forEach(dep => {
        if (dep === h.id) return;
        expCount[dep] = (expCount[dep] || 0) + 1;
        expVal[dep] = (expVal[dep] || 0) + h.value;
      });
      // exposición geográfica por país del holding y de sus dependencias-empresa
      [h.id, ...seen].forEach(x => { const c = NB[x] && NB[x].country; if (c) ctryVal[c] = (ctryVal[c] || 0) + h.value / (seen.size || 1); });
    });
    const topDeps = Object.keys(expCount).map(id => ({ id, n: expCount[id], val: expVal[id], e: resolveEntity(id) || { label: id } }))
      .sort((a, b) => b.val - a.val || b.n - a.n).slice(0, 10);
    const topCtry = Object.keys(ctryVal).map(c => ({ c, val: ctryVal[c] })).sort((a, b) => b.val - a.val).slice(0, 5);
    const chip = (label, sub, color) => `<span style="display:inline-flex;flex-direction:column;gap:1px;background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:5px 9px;margin:0 5px 5px 0">
        <span style="font-size:11.5px;color:var(--ink-1);font-weight:600">${esc(label)}</span><span style="font-size:10px;color:${color || 'var(--ink-3)'}">${esc(sub)}</span></span>`;
    el.style.display = 'block';
    el.innerHTML = `<div style="border:1px solid rgba(67,200,150,.35);background:rgba(67,200,150,.06);border-radius:12px;padding:12px 14px">
      <div style="font-size:13.5px;font-weight:700;color:var(--ink-1);margin-bottom:2px">🎯 Exposición de tu portafolio <span style="font-size:11px;color:var(--ink-3);font-weight:400">· ${_money(pf.total)} en ${pf.holdings.length} posiciones · ${fmtDate(_dateMs)}</span></div>
      <div style="font-size:11px;color:var(--ink-3);margin:8px 0 3px">Depende (oculto) de:</div>
      <div>${topDeps.map(d => chip(d.e.label, `${_money(d.val)} · ${d.n} posición${d.n > 1 ? 'es' : ''}`, '#43C896')).join('') || '<span style="font-size:12px;color:var(--ink-3)">sin dependencias mapeadas</span>'}</div>
      <div style="font-size:11px;color:var(--ink-3);margin:8px 0 3px">Exposición geográfica:</div>
      <div>${topCtry.map(c => chip(c.c, _money(c.val), '#E0B25C')).join('') || '—'}</div>
    </div>`;
  }

  // Chokepoints: para cada nodo, tamaño de su cascada de impacto (centralidad).
  function _runChokepoints() {
    const el = document.getElementById('tkg-insights'); if (!el) return;
    const casSize = id => {
      const seen = new Set([id]); let fr = [id], depth = 0;
      while (fr.length && depth < 6) {
        depth++; const nx = [];
        fr.forEach(x => (_impactAdj[x] || []).forEach(({ to, fact }) => {
          if (status(fact, _dateMs) !== 'vigente') return;
          if (!seen.has(to)) { seen.add(to); nx.push(to); }
        }));
        fr = nx;
      }
      return seen.size - 1;
    };
    const ranked = _allNodeIds.map(id => ({ id, e: resolveEntity(id) || { label: id }, n: casSize(id) }))
      .filter(x => x.n > 0).sort((a, b) => b.n - a.n).slice(0, 12);
    const types = (window.ONTOLOGY && window.ONTOLOGY.types) || {};
    el.style.display = 'block';
    el.innerHTML = `<div style="border:1px solid rgba(251,146,60,.35);background:rgba(251,146,60,.06);border-radius:12px;padding:12px 14px">
      <div style="font-size:13.5px;font-weight:700;color:var(--ink-1);margin-bottom:6px">🏛 Chokepoints sistémicos <span style="font-size:11px;color:var(--ink-3);font-weight:400">· quién arrastra a más si cae (${fmtDate(_dateMs)})</span></div>
      <div style="display:flex;flex-direction:column;gap:3px">${ranked.map((x, i) => {
        const tm = types[_nodeType[x.id] || 'Company'] || { color: COL.node };
        return `<div style="display:flex;align-items:center;gap:8px;cursor:pointer" onclick="window.__tkgOpenObj&&window.__tkgOpenObj('${x.id}')">
          <span style="font-size:11px;color:var(--ink-3);width:18px">${i + 1}.</span>
          <span style="width:8px;height:8px;border-radius:50%;background:${tm.color};flex-shrink:0"></span>
          <span style="flex:1;font-size:12px;color:var(--ink-1)">${esc(x.e.label)}</span>
          <span style="flex-shrink:0;font-size:11px;color:#fb923c;font-weight:700">${x.n} afectados</span>
          <span style="flex-shrink:0;width:${Math.min(120, x.n * 9)}px;height:5px;background:#fb923c55;border-radius:3px"></span>
        </div>`;
      }).join('')}</div>
      <div style="font-size:10.5px;color:var(--ink-3);margin-top:6px">Clic en cualquiera para su ficha. Tip: mueve la fecha y recalcula — los chokepoints cambian con el tiempo.</div>
    </div>`;
  }

  function _clearShock() { _shock = null; _renderImpact(); _refresh(); }

  function _toggleSimMode() {
    _simMode = !_simMode;
    const btn = document.getElementById('tkg-simbtn');
    const hint = document.getElementById('tkg-simhint');
    if (btn) { btn.style.background = _simMode ? 'var(--violet)' : 'none'; btn.style.color = _simMode ? '#fff' : 'var(--violet)'; }
    if (hint) hint.textContent = _simMode ? '⚡ clic en cualquier nodo para simular su caída (según la fecha actual)' : '';
    if (_nodeSel) _nodeSel.style('cursor', _simMode ? 'crosshair' : 'pointer');
  }

  function _renderImpact() {
    const el = document.getElementById('tkg-impact');
    const reset = document.getElementById('tkg-reset');
    if (!el) return;
    if (!_shock) { el.style.display = 'none'; el.innerHTML = ''; if (reset) reset.style.display = 'none'; return; }
    const originLabel = (resolveEntity(_shock.origin) || {}).label || _shock.origin;
    const total = _shock.affected.size - 1;
    const types = (window.ONTOLOGY && window.ONTOLOGY.types) || {};
    const chips = Object.keys(_shock.byType).map(t => {
      const meta = types[t] || { label: t, color: COL.node };
      return `<span style="font-size:11px;color:${meta.color};background:${meta.color}18;border:1px solid ${meta.color}44;border-radius:12px;padding:2px 8px">${esc(meta.label)}: ${_shock.byType[t]}</span>`;
    }).join(' ');
    const list = _shock.order.filter(o => o.id !== _shock.origin).slice(0, 18)
      .map(o => { const e = resolveEntity(o.id) || {}; return `<span title="ola ${o.depth}" style="font-size:11px;color:var(--ink-2);background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:2px 7px">${esc(e.label || o.id)}</span>`; }).join(' ');
    const extra = _shock.order.length > 19 ? ` <span style="font-size:11px;color:var(--ink-3)">+${_shock.order.length - 19} más</span>` : '';
    el.style.display = 'block';
    if (reset) reset.style.display = 'inline-block';
    const port = _shock.port;
    const portHtml = port
      ? `<div style="font-size:12.5px;margin:2px 0 8px;padding:7px 10px;border-radius:8px;background:${port.pct >= 30 ? 'rgba(255,107,92,.12)' : 'rgba(224,178,92,.1)'};border:1px solid ${port.pct >= 30 ? '#FF6B5C55' : '#E0B25C55'}">
           💼 Tu portafolio en riesgo: <b style="color:${port.pct >= 30 ? '#FF6B5C' : '#E0B25C'}">${_money(port.atRisk)} (${port.pct.toFixed(0)}%)</b>
           ${port.hit.length ? ` · ${port.hit.slice(0, 6).map(h => esc(h.label)).join(', ')}` : ''}</div>`
      : '';
    el.innerHTML = `<div style="border:1px solid #ef444455;background:#ef44440d;border-radius:12px;padding:12px 14px">
      <div style="font-size:13.5px;color:var(--ink-1);font-weight:700;margin-bottom:6px">⚡ Shock: <span style="color:#ef4444">${esc(originLabel)}</span> cae en ${fmtDate(_dateMs)}</div>
      <div style="font-size:12px;color:var(--ink-2);margin-bottom:8px"><b>${total}</b> entidades afectadas en cascada · ${chips}</div>
      ${portHtml}
      <div style="display:flex;flex-wrap:wrap;gap:5px">${list}${extra}</div>
    </div>`;
  }

  function _renderFacts() {
    const el = document.getElementById('tkg-facts'); if (!el) return;
    const rows = _facts.filter(matchesSearch).map(f => ({ f, st: status(f, _dateMs) }))
      .sort((a, b) => (b.f._from || 0) - (a.f._from || 0));
    const lbl = id => { const e = resolveEntity(id); return (e && e.label) || id; };
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

  // ── Ficha de objeto (ontología "clic") con datos VIVOS + IA + noticias ──────
  function _base() { return (typeof BASE !== 'undefined') ? BASE : ''; }
  function _liveQuote(mkt) {
    if (!mkt || !window.MKT || !window.MKT.quotes) return null;
    const q = window.MKT.quotes[mkt]; if (!q || q.close == null) return null;
    const pct = (q.prev ? ((q.close - q.prev) / q.prev * 100) : null);
    return { close: q.close, prev: q.prev, pct };
  }
  function _relFactsOf(id) {
    return _facts.filter(f => f._isEdge && (f.subject === id || f.object === id));
  }

  function _closeObject() {
    const p = document.getElementById('tkg-objpanel');
    if (p) p.style.transform = 'translateX(101%)';
    _objOpen = null;
  }

  function _openObject(id) {
    const p = document.getElementById('tkg-objpanel'); if (!p) return;
    _objOpen = id;
    const e = resolveEntity(id) || { id, label: id, type: 'Company' };
    const NB = window.NODE_BY_ID || {};
    const node = NB[id];
    const isCompany = e.type === 'Company';
    const mkt = node && node.mkt;
    const q = _liveQuote(mkt);
    const nrs = (isCompany && typeof window.computeNRS === 'function') ? window.computeNRS(id) : null;
    const types = (window.ONTOLOGY && window.ONTOLOGY.types) || {};
    const tmeta = types[e.type] || { label: e.type, color: COL.node, icon: '' };

    // upstream / downstream (empresas)
    let up = [], down = [];
    if (isCompany && window.LINKS) {
      window.LINKS.forEach(l => {
        const s = lidOf(l.source), t = lidOf(l.target);
        if (t === id && NB[s]) up.push({ id: s, label: (NB[s].label || s), rel: l.rel || l.type });
        if (s === id && NB[t]) down.push({ id: t, label: (NB[t].label || t), rel: l.rel || l.type });
      });
    }
    up = up.slice(0, 8); down = down.slice(0, 8);
    const rounds = (window.PREIPO_INTEL && window.PREIPO_INTEL[id] && window.PREIPO_INTEL[id].rounds) || [];

    // Linaje (Fase 5): de dónde sale el dato y qué tan viejo es.
    const _ageStr = ms => {
      const s = Math.max(0, Math.round((Date.now() - ms) / 1000));
      if (s < 60) return `hace ${s}s`;
      if (s < 3600) return `hace ${Math.round(s / 60)}min`;
      return `hace ${Math.round(s / 3600)}h`;
    };
    const priceLineage = (window.MKT && window.MKT.ts) ? `Finnhub/FMP · ${_ageStr(window.MKT.ts)}` : '';
    const priceHtml = q
      ? `<div style="display:flex;align-items:baseline;gap:8px;margin:2px 0 2px">
           <span style="font-size:22px;font-weight:800;font-family:'JetBrains Mono',monospace;color:var(--ink-1)">$${q.close.toFixed(2)}</span>
           ${q.pct != null ? `<span style="font-size:13px;font-weight:700;color:${q.pct >= 0 ? '#43C896' : '#FF6B5C'}">${q.pct >= 0 ? '▲' : '▼'} ${Math.abs(q.pct).toFixed(2)}%</span>` : ''}
           <span class="live-pill on" style="margin-left:auto" title="${esc(priceLineage)}"><span class="live-dot"></span>LIVE</span>
         </div>${priceLineage ? `<div style="font-size:10px;color:var(--ink-3);margin-bottom:8px">ⓘ ${esc(priceLineage)}</div>` : '<div style="margin-bottom:8px"></div>'}`
      : (isCompany ? `<div style="font-size:12px;color:var(--preipo);margin:2px 0 8px">${node && node.preipo ? '◆ Pre-IPO / privada' : (mkt ? 'sin cotización en vivo' : 'no cotiza')}${node && node.ticker ? ' · ' + esc(node.ticker) : ''}</div>` : '');

    const nrsHtml = nrs != null
      ? `<div style="margin:6px 0 4px">
           <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--ink-3)"><span>Riesgo NRS</span><span style="color:${nrs >= 70 ? '#FF6B5C' : nrs >= 40 ? '#E0B25C' : '#43C896'};font-weight:700">${nrs}/100</span></div>
           <div style="height:6px;background:var(--surface-2);border-radius:4px;overflow:hidden;margin-top:3px"><div style="height:100%;width:${nrs}%;background:${nrs >= 70 ? '#FF6B5C' : nrs >= 40 ? '#E0B25C' : '#43C896'}"></div></div>
           <div id="tkg-obj-nrs-lineage" style="font-size:10px;color:var(--ink-3);margin-top:3px">ⓘ calculado (geo + cadena + margen + concentración)</div>
         </div>` : '';

    const chipRow = (arr, dir) => arr.length ? `<div style="margin-top:4px;display:flex;flex-wrap:wrap;gap:4px">${arr.map(x => `<span title="${esc(x.rel || '')}" onclick="window.__tkgOpenObj&&window.__tkgOpenObj('${x.id}')" style="cursor:pointer;font-size:10.5px;color:var(--ink-2);background:var(--surface-2);border:1px solid var(--line);border-radius:9px;padding:2px 7px">${dir}${esc(x.label)}</span>`).join('')}</div>` : '<div style="font-size:11px;color:var(--ink-3);margin-top:3px">—</div>';

    const rels = _relFactsOf(id).slice(0, 8);
    const relHtml = !isCompany && rels.length ? `<div style="margin-top:10px"><div style="font-size:11px;color:var(--ink-3);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">Relaciones</div>${rels.map(f => { const other = f.subject === id ? f.object : f.subject; const oe = resolveEntity(other) || {}; return `<div style="font-size:11.5px;color:var(--ink-2);padding:2px 0">${esc((f.meta && f.meta.headline) || (f.subject === id ? f.predicate + ' → ' + (oe.label || other) : (oe.label || other) + ' ' + f.predicate))}</div>`; }).join('')}</div>` : '';

    p.innerHTML = `
      <div style="padding:16px 16px 24px">
        <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:4px">
          <div style="flex:1">
            <div style="font-size:10px;color:${tmeta.color};font-weight:700;letter-spacing:.5px;text-transform:uppercase">${tmeta.icon || ''} ${esc(tmeta.label)}</div>
            <div style="font-size:17px;font-weight:800;color:var(--ink-1);line-height:1.2">${esc(e.label)}</div>
          </div>
          <button id="tkg-obj-close" style="flex-shrink:0;background:none;border:none;color:var(--ink-3);font-size:18px;cursor:pointer;line-height:1">✕</button>
        </div>
        ${priceHtml}${nrsHtml}
        ${isCompany && node ? `<div style="font-size:11px;color:var(--ink-3);margin-bottom:8px">${[node.country, (typeof window.catLabel === 'function' ? window.catLabel(node.cat) : node.cat)].filter(Boolean).map(esc).join(' · ')}</div>` : ''}
        ${isCompany && node && (node.role || node.role_en) ? `<div style="font-size:12px;color:var(--ink-2);line-height:1.45;margin-bottom:10px">${esc((node.role || node.role_en || '').slice(0, 220))}</div>` : ''}
        <div style="display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 12px">
          <button id="tkg-obj-shock" style="font-size:11.5px;padding:6px 10px;border-radius:8px;border:1px solid #ef444488;background:#ef44441a;color:#ff8a8a;cursor:pointer">⚡ Simular caída</button>
          ${isCompany ? `<button id="tkg-obj-map" style="font-size:11.5px;padding:6px 10px;border-radius:8px;border:1px solid var(--line);background:var(--surface-2);color:var(--ink-2);cursor:pointer">🗺 Ver en mapa</button>` : ''}
          <button id="tkg-obj-ai" style="font-size:11.5px;padding:6px 10px;border-radius:8px;border:1px solid var(--violet);background:none;color:var(--violet);cursor:pointer">🧠 Bixby analiza</button>
          ${isCompany ? `<button id="tkg-obj-news" style="font-size:11.5px;padding:6px 10px;border-radius:8px;border:1px solid var(--line);background:var(--surface-2);color:var(--ink-2);cursor:pointer">📰 Noticias</button>` : ''}
          <button id="tkg-obj-action" style="font-size:11.5px;padding:6px 10px;border-radius:8px;border:1px solid #43C89688;background:rgba(67,200,150,.10);color:#43C896;cursor:pointer">＋ Acción</button>
        </div>
        <div id="tkg-obj-action-form" style="display:none;margin:0 0 12px;padding:12px;border:1px solid var(--line);border-radius:10px;background:var(--surface-2)"></div>
        <div id="tkg-obj-action-log" style="margin:0 0 4px"></div>
        ${isCompany ? `
          <div style="font-size:11px;color:var(--ink-3);text-transform:uppercase;letter-spacing:.5px">Depende de (upstream)</div>${chipRow(up, '↑ ')}
          <div style="font-size:11px;color:var(--ink-3);text-transform:uppercase;letter-spacing:.5px;margin-top:8px">Le abastece a (downstream)</div>${chipRow(down, '↓ ')}` : ''}
        ${rounds.length ? `<div style="font-size:11px;color:var(--ink-3);text-transform:uppercase;letter-spacing:.5px;margin-top:10px">Rondas</div>${rounds.slice(0, 5).map(r => `<div style="font-size:11.5px;color:var(--ink-2);padding:2px 0">${esc((r.round || '') + ' · ' + (r.amount || '') + ' · ' + (r.date || '') + (r.lead ? ' · ' + r.lead : ''))}</div>`).join('')}` : ''}
        ${relHtml}
        <div id="tkg-obj-ai-out" style="margin-top:12px"></div>
        <div id="tkg-obj-news-out" style="margin-top:10px"></div>
      </div>`;
    p.style.transform = 'translateX(0)';
    p.scrollTop = 0;

    p.querySelector('#tkg-obj-close').onclick = _closeObject;
    const bShock = p.querySelector('#tkg-obj-shock'); if (bShock) bShock.onclick = () => { _runShock(id); };
    const bMap = p.querySelector('#tkg-obj-map'); if (bMap) bMap.onclick = () => { if (typeof switchTab === 'function') switchTab('map'); if (typeof jumpTo === 'function') setTimeout(() => jumpTo(id), 90); };
    const bAi = p.querySelector('#tkg-obj-ai'); if (bAi) bAi.onclick = () => _objAnalyze(id, e.label, mkt);
    const bNews = p.querySelector('#tkg-obj-news'); if (bNews) bNews.onclick = () => _objNews(id, e.label, mkt);
    const bAction = p.querySelector('#tkg-obj-action'); if (bAction) bAction.onclick = () => _toggleActionForm(id, isCompany, e.label);
    _renderActionLog(id);
    if (isCompany) _loadNrsLineage(id);
  }

  // Linaje del NRS (Fase 5): si la ontología tiene un nrs_override (fijado vía
  // la Acción MarcarRiesgo), lo mostramos con quién y por qué en vez del texto
  // genérico "calculado". Consulta aparte para no bloquear el render inicial.
  function _loadNrsLineage(id) {
    const el = document.getElementById('tkg-obj-nrs-lineage'); if (!el) return;
    fetch(`${_base()}/api/ontology/objects/${encodeURIComponent(id)}`)
      .then(r => r.ok ? r.json() : null).then(d => {
        const props = d && d.properties; if (!props || props.nrs_override == null) return;
        const who = props.nrs_override_by ? ' por ' + props.nrs_override_by : '';
        const why = props.nrs_override_reason ? ' — ' + props.nrs_override_reason : '';
        el.textContent = `ⓘ fijado manualmente${who}${why}`;
      }).catch(() => {});
  }

  // ── Acciones (Fase 2): escritura humana auditada — CrearTesis, Anotar,
  // MarcarRiesgo, RegistrarDecision. Cada una pide actor (se recuerda en este
  // navegador) y queda en el Registro con quién/cuándo/por qué.
  function _getActor() {
    try {
      let a = localStorage.getItem('khipu_actor');
      if (!a) { a = (window.prompt('¿Cómo te identificamos en el Registro de Acciones? (tu nombre)') || '').trim(); if (a) localStorage.setItem('khipu_actor', a); }
      return a || 'anónimo';
    } catch (e) { return 'anónimo'; }
  }

  const ACTION_FIELDS = {
    CrearTesis: [
      { k: 'stance', label: 'Postura', type: 'select', options: [['long', 'Alcista (long)'], ['short', 'Bajista (short)'], ['watch', 'Vigilar'], ['avoid', 'Evitar']] },
      { k: 'confidence', label: 'Confianza (0-1)', type: 'number', step: '0.05', min: 0, max: 1, value: 0.7 },
      { k: 'rationale', label: 'Razonamiento', type: 'textarea' },
    ],
    MarcarRiesgo: [
      { k: 'nivel', label: 'Nivel NRS (0-100)', type: 'number', min: 0, max: 100, value: 50 },
      { k: 'razon', label: 'Razón', type: 'textarea' },
    ],
    RegistrarDecision: [
      { k: 'decision', label: 'Decisión', type: 'textarea' },
    ],
    AnotarObjeto: [
      { k: 'texto', label: 'Nota', type: 'textarea' },
    ],
  };

  function _toggleActionForm(id, isCompany, label) {
    const form = document.getElementById('tkg-obj-action-form'); if (!form) return;
    const open = form.style.display !== 'none';
    if (open) { form.style.display = 'none'; return; }
    const types = isCompany ? ['CrearTesis', 'MarcarRiesgo', 'RegistrarDecision', 'AnotarObjeto'] : ['AnotarObjeto'];
    const typeLabels = { CrearTesis: '📋 Crear tesis', MarcarRiesgo: '⚠ Marcar riesgo', RegistrarDecision: '🗳 Registrar decisión', AnotarObjeto: '✎ Anotar' };
    form.innerHTML = `
      <select id="tkg-act-type" style="width:100%;margin-bottom:8px;padding:6px 8px;border-radius:6px;border:1px solid var(--line);background:var(--bg);color:var(--ink-1);font-size:12px">
        ${types.map(t => `<option value="${t}">${typeLabels[t]}</option>`).join('')}
      </select>
      <div id="tkg-act-fields"></div>
      <div style="display:flex;gap:8px;align-items:center;margin-top:8px">
        <button id="tkg-act-submit" style="font-size:12px;padding:6px 12px;border-radius:7px;border:none;background:#43C896;color:#04241a;font-weight:700;cursor:pointer">Guardar</button>
        <span id="tkg-act-status" style="font-size:11.5px;color:var(--ink-3)"></span>
      </div>`;
    form.style.display = 'block';
    const sel = form.querySelector('#tkg-act-type');
    const renderFields = () => {
      const fields = ACTION_FIELDS[sel.value] || [];
      form.querySelector('#tkg-act-fields').innerHTML = fields.map(f => {
        const base = `id="tkg-f-${f.k}" style="width:100%;margin-bottom:6px;padding:6px 8px;border-radius:6px;border:1px solid var(--line);background:var(--bg);color:var(--ink-1);font-size:12px"`;
        if (f.type === 'select') return `<label style="font-size:10.5px;color:var(--ink-3)">${f.label}</label><select ${base}>${f.options.map(([v, l]) => `<option value="${v}">${l}</option>`).join('')}</select>`;
        if (f.type === 'textarea') return `<label style="font-size:10.5px;color:var(--ink-3)">${f.label}</label><textarea ${base} rows="2"></textarea>`;
        return `<label style="font-size:10.5px;color:var(--ink-3)">${f.label}</label><input ${base} type="number" step="${f.step || '1'}" min="${f.min}" max="${f.max}" value="${f.value != null ? f.value : ''}">`;
      }).join('');
    };
    sel.addEventListener('change', renderFields);
    renderFields();
    form.querySelector('#tkg-act-submit').onclick = () => _submitAction(id, sel.value, form);
  }

  function _submitAction(id, actionType, form) {
    const status = form.querySelector('#tkg-act-status');
    const fields = ACTION_FIELDS[actionType] || [];
    const body = { actor: _getActor() };
    if (actionType === 'CrearTesis') body.company_id = id;
    if (actionType === 'MarcarRiesgo') body.company_id = id;
    if (actionType === 'RegistrarDecision') body.company_id = id;
    if (actionType === 'AnotarObjeto') body.object_id = id;
    fields.forEach(f => {
      const el = form.querySelector(`#tkg-f-${f.k}`);
      if (!el) return;
      body[f.k] = f.type === 'number' ? parseFloat(el.value) : el.value;
    });
    status.textContent = 'guardando…'; status.style.color = 'var(--ink-3)';
    const base = _base();
    fetch(`${base}/api/ontology/actions/${actionType}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }).then(r => r.json().then(d => ({ ok: r.ok, d }))).then(({ ok, d }) => {
      if (ok) {
        status.textContent = '✓ guardado'; status.style.color = '#43C896';
        form.style.display = 'none';
        _renderActionLog(id);
      } else {
        status.textContent = '⚠ ' + (d.error || 'error'); status.style.color = '#f87171';
      }
    }).catch(() => { status.textContent = '⚠ error de red'; status.style.color = '#f87171'; });
  }

  function _renderActionLog(id) {
    const el = document.getElementById('tkg-obj-action-log'); if (!el) return;
    const base = _base();
    fetch(`${base}/api/ontology/actions?object_id=${encodeURIComponent(id)}&limit=6`)
      .then(r => r.ok ? r.json() : null).then(d => {
        if (!d || !d.actions || !d.actions.length) { el.innerHTML = ''; return; }
        el.innerHTML = `<div style="font-size:11px;color:var(--ink-3);text-transform:uppercase;letter-spacing:.5px;margin:8px 0 4px">Registro</div>` +
          d.actions.map(a => {
            const when = a.recorded_at ? new Date(a.recorded_at).toLocaleDateString('es', { day: '2-digit', month: 'short' }) : '';
            const p = a.payload || {};
            const detail = p.rationale || p.razon || p.decision || p.texto || '';
            return `<div style="font-size:11.5px;color:var(--ink-2);padding:3px 0;line-height:1.4">
              <b style="color:#43C896">${esc(a.action || '')}</b> · ${esc(a.actor || '')} · <span style="color:var(--ink-3)">${when}</span>
              ${detail ? '<br><span style="color:var(--ink-3)">' + esc(String(detail).slice(0, 140)) + '</span>' : ''}
            </div>`;
          }).join('');
      }).catch(() => { el.innerHTML = ''; });
  }

  function _objAnalyze(id, label, mkt) {
    const out = document.getElementById('tkg-obj-ai-out'); if (!out) return;
    out.innerHTML = '<div style="font-size:12px;color:var(--ink-3)">🧠 Bixby analizando…</div>';
    const e = resolveEntity(id) || {};
    const NB = window.NODE_BY_ID || {};
    const n = NB[id] || {};
    const q = _liveQuote(mkt);
    const ctx = { label, type: e.type, ticker: mkt || null, country: n.country || null,
      price: q ? q.close : null, change_pct: q && q.pct != null ? +q.pct.toFixed(2) : null,
      nrs: typeof window.computeNRS === 'function' ? window.computeNRS(id) : null,
      role: (n.role || '').slice(0, 300) };
    const sys = 'Eres Bixby, analista senior de inversión en la cadena de deep-tech (semiconductores, IA, espacio, nuclear). Responde en español, conciso y accionable, SIN markdown.';
    const prompt = `Da un análisis de inversión de "${label}" en 4-6 frases: su rol en la cadena, 1-2 riesgos clave, 1 catalizador, y qué vigilar. Usa los datos si ayudan.\nDATOS: ${JSON.stringify(ctx)}`;
    fetch(`${_base()}/api/ai/analyze`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ system: sys, prompt, max_tokens: 420 }) })
      .then(r => r.ok ? r.json() : null).then(d => {
        if (d && d.result) out.innerHTML = `<div style="border:1px solid rgba(124,58,237,.35);background:rgba(124,58,237,.08);border-radius:10px;padding:11px 12px;font-size:12.5px;line-height:1.5;color:var(--ink-1)"><b style="color:var(--violet)">🧠 Bixby</b> <span style="font-size:10px;color:var(--ink-3)">${esc(d.model || '')}</span><br>${esc(d.result)}</div>`;
        else out.innerHTML = `<div style="font-size:12px;color:#f87171">${esc((d && d.error) || 'No pude analizar ahora.')}</div>`;
      }).catch(() => { out.innerHTML = '<div style="font-size:12px;color:#f87171">Error de red al analizar.</div>'; });
  }

  function _objNews(id, label, mkt) {
    const out = document.getElementById('tkg-obj-news-out'); if (!out) return;
    out.innerHTML = '<div style="font-size:12px;color:var(--ink-3)">📰 buscando noticias…</div>';
    const url = mkt ? `${_base()}/api/news/${encodeURIComponent(mkt)}` : `${_base()}/api/news/gdelt/${encodeURIComponent(label)}`;
    fetch(url).then(r => r.ok ? r.json() : null).then(d => {
      const arr = Array.isArray(d) ? d : (d && Array.isArray(d.articles) ? d.articles : []);
      if (!arr.length) { out.innerHTML = '<div style="font-size:12px;color:var(--ink-3)">Sin noticias recientes.</div>'; return; }
      out.innerHTML = `<div style="font-size:11px;color:var(--ink-3);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">Noticias</div>` +
        arr.slice(0, 6).map(a => {
          const h = a.headline || a.title || ''; const src = a.source || ''; const u = a.url || a.link || '#';
          const sent = a.sentiment;
          const dot = sent != null ? `<span style="color:${sent > 0 ? '#43C896' : sent < 0 ? '#FF6B5C' : 'var(--ink-3)'}">●</span> ` : '';
          return `<a href="${esc(u)}" target="_blank" rel="noopener" style="display:block;font-size:11.5px;color:var(--ink-2);text-decoration:none;padding:5px 0;border-bottom:1px solid var(--line);line-height:1.35">${dot}${esc(h)}${src ? ` <span style="color:var(--ink-3)">· ${esc(src)}</span>` : ''}</a>`;
        }).join('');
    }).catch(() => { out.innerHTML = '<div style="font-size:12px;color:#f87171">Error al cargar noticias.</div>'; });
  }
  // permitir navegar entre objetos desde los chips upstream/downstream
  window.__tkgOpenObj = function (id) { try { _openObject(id); } catch (e) {} };
  // Fase 4 (lenguaje KHIPU): mover la línea de tiempo a una fecha desde afuera
  // (ej. "GRAPH ASOF 2020-01-01"). Si el panel aún no se construyó, lo hace primero.
  window.__tkgSetDate = function (msOrDateStr) {
    try {
      if (!_built && typeof window.initTKGTab === 'function') window.initTKGTab();
      const ms = typeof msOrDateStr === 'number' ? msOrDateStr : toMs(msOrDateStr);
      if (ms == null || isNaN(ms)) return false;
      _dateMs = Math.max(_minMs || ms, Math.min(_maxMs || ms, ms));
      _stopPlay(); _refresh();
      return true;
    } catch (e) { return false; }
  };

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

  function _resize() {
    if (!_sim || !_svg) return;
    const svgEl = document.getElementById('tkg-svg'); if (!svgEl) return;
    const w = _svgW(svgEl);
    const h = svgEl.clientHeight || 520;
    _sim.force('center', d3.forceCenter(w / 2, h / 2));
    _sim.alpha(0.4).restart();
  }

  // Si el backend expone el grafo (Neo4j), lo indicamos en el badge y, la
  // primera vez que detectamos Neo4j conectado, sembramos los hechos derivados.
  function _checkBackendStore() {
    try {
      const base = (typeof BASE !== 'undefined') ? BASE : '';
      fetch(`${base}/api/grafo/estado`).then(r => r.ok ? r.json() : null).then(d => {
        if (!d || !d.store) return;
        const el = document.getElementById('tkg-store');
        if (el) {
          if (d.store === 'neo4j' && d.neo4j_connected) {
            el.textContent = 'memoria: neo4j 🟢';
          } else if (d.store === 'neo4j') {
            el.textContent = 'neo4j ⚠ sin conexión';
            el.title = d.error || 'No conecta con Neo4j';
          } else {
            el.textContent = 'memoria: nativa';
            if (d.hint) el.title = d.hint;
          }
        }
        if (d.store === 'neo4j' && d.neo4j_connected) _seedBackend(base);
      }).catch(() => {});
    } catch (e) {}
    _checkOntologyStatus();
  }

  // Fase 1 del roadmap de ontología: /api/ontology/graph?as_of= es la fuente
  // de verdad bitemporal en Postgres (si está configurada). Por ahora la
  // consultamos como VERIFICACIÓN cruzada (no reemplaza window.NODE_BY_ID/
  // LINKS, de los que dependen 7 pestañas más de la app) — un swap completo
  // del catálogo es un cambio de mayor riesgo que se hace en su propia sesión
  // con regresión de toda la app, no el mismo día de una demo en vivo.
  function _checkOntologyStatus() {
    try {
      const base = (typeof BASE !== 'undefined') ? BASE : '';
      fetch(`${base}/api/ontology/status`).then(r => r.ok ? r.json() : null).then(d => {
        if (!d) return;
        const el = document.getElementById('tkg-ontology-badge');
        if (!el) return;
        if (d.configured && d.ok) {
          el.style.display = 'inline-flex';
          el.textContent = `◈ ontología: ${d.objects} objetos · ${d.links} vínculos · ${d.events} eventos`;
          el.title = 'Postgres (fuente única de verdad, Fase 1) — GET /api/ontology/graph?as_of=';
        } else {
          el.style.display = 'none';
        }
      }).catch(() => {});
    } catch (e) {}
  }

  function _seedBackend(base) {
    // solo una vez por navegador (el MERGE del server igual es idempotente)
    try { if (localStorage.getItem('tkg_seeded_neo4j_v2') === '1') return; } catch (e) {}
    const NB = window.NODE_BY_ID || {};
    const payload = (_facts || []).map(f => ({
      id: f.id, subject: f.subject, subject_label: (NB[f.subject] && NB[f.subject].label) || f.subject,
      predicate: f.predicate, object: f.object, object_type: f.object_type,
      object_label: (NB[f.object] && NB[f.object].label) || f.object,
      valid_from: f.valid_from || null, valid_until: f.valid_until || null,
      source: f.source, confidence: f.confidence, group: f.group, meta: f.meta || {},
    }));
    if (!payload.length) return;
    fetch(`${base}/api/grafo/seed`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ facts: payload }),
    }).then(r => r.ok ? r.json() : null).then(res => {
      if (res && res.status === 'ok') {
        try { localStorage.setItem('tkg_seeded_neo4j_v2', '1'); } catch (e) {}
        const el = document.getElementById('tkg-store');
        if (el) el.textContent = 'memoria: neo4j 🟢 (' + res.persisted + ' hechos)';
      }
    }).catch(() => {});
  }
})();
