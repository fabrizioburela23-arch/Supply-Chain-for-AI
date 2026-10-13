/* ============================================================================
   engine/maptime.js — EL TIEMPO DENTRO DEL MAPA PRINCIPAL (2026-09-25)
   Fabrizio: "el grafo temporal y el normal deberían ser uno; el temporal no
   da mucho por sí solo". Antes el tiempo vivía en una pestaña aparte con su
   propio grafo pequeño. Ahora el MISMO mapa de 949 nodos tiene:

     ⏱ línea de tiempo  → la cadena tal como era en una fecha. UNA regla, la
                          del SERVIDOR (DT-M3, batch I3): con base de datos,
                          lo vigente lo dice /api/ontology/graph?as_of=
                          (+ known_at = "tal como se conocía en κ"); sin base
                          (503) o sin conexión, la MISMA regla con la que la
                          migración carga el catálogo, rotulada: un vínculo
                          del catálogo cuenta "desde que se rastrea" (2000-01-01,
                          GENESIS) y una empresa existe si tiene algún vínculo
                          vigente. Antes se apagaban por fundación y por la
                          fecha del par: otra regla que daba otro grafo.
     ⚡ capa Eventos     → los hechos fechados (sanciones, inversiones,
                          fábricas, competencia…) dibujados como líneas
                          punteadas entre las dos empresas, visibles solo
                          dentro de su ventana de validez. Si el otro extremo
                          es un CONCEPTO (EUV, Ley CHIPS, China, galio…) o un
                          atributo, el hecho se ancla como anillo punteado
                          alrededor de la empresa. Apagada por defecto.
     ☰ Hechos / ⬗ 3D    → la lista de hechos y la vista 3D temporal siguen
                          existiendo, pero como VISTAS que se abren desde aquí.

   Honestidad del dato: un vínculo sin fecha conocida NO se inventa una; cuenta
   "desde que se rastrea" (2000) y la barra dice SIEMPRE de dónde sale la foto
   (base del servidor o regla del catálogo). Solo se dibujan
   eventos cuyos DOS extremos están en el mapa (los demás siguen en ☰ Hechos).

   Coste: nada se calcula hasta abrir ⏱. El filtro por fecha se aplica dentro
   de _refreshStylesCore (una pasada de estilos, sin tocar la física), y el
   slider se agrupa a 1 repintado por fotograma.
   API: window.KhipuMapTime {open, close, toggle, setDate, relabel, active,
        nodeOk(id), linkOk(link)} · window.__tkgShow(vista)
   ============================================================================ */
(function () {
  'use strict';

  const DAY = 86400000;
  const MIN_MS = Date.UTC(1970, 0, 1);   // antes de 1970 casi no hay cadena de IA que ver
  const STEP = 30 * DAY;

  function isEn() {
    let l = window.LANG;
    if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = null; } }
    return l === 'en';
  }
  function L(es, en) { return isEn() ? en : es; }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  function lid(v) { return (v && typeof v === 'object') ? v.id : v; }
  function canon(id) {
    const n = window.NODE_BY_ID && window.NODE_BY_ID[id];
    return n ? n.id : null;
  }
  function fmt(ms) {
    const d = new Date(ms);
    const m = d.getUTCMonth();
    const es = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
    const en = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return (isEn() ? en : es)[m] + ' ' + d.getUTCFullYear();
  }
  function relColor(rel) {
    // primero los verbos de la ontología (sanciona, restringe, alberga…),
    // que getLinkColorHex no conoce
    const o = window.ONTOLOGY && window.ONTOLOGY.rels && window.ONTOLOGY.rels[rel];
    if (o && o.color) return o.color;
    try { if (typeof window.getLinkColorHex === 'function') return window.getLinkColorHex(rel); } catch (e) {}
    return '#8e5aff';
  }

  const GENESIS_MS = Date.UTC(2000, 0, 1);   // = ontology.service.GENESIS_SENTINEL ("desde que se rastrea")
  const ASOF_DEBOUNCE_MS = 250;
  const ASOF_FAIL_BASE_MS = 2000;     // tras un fallo, la MISMA foto se reintenta a los 2 s, 4 s, 8 s… (tope 60 s)
  const ASOF_FAIL_MAX_MS = 60000;
  const ASOF_CACHE_MAX = 36;

  const S = {
    active: false,     // ⏱ abierto → el filtro por fecha se aplica
    events: false,     // ⚡ capa de eventos visible
    dateMs: Date.now(),
    maxMs: Date.now(),
    built: false,
    linked: null,      // Set de empresas con algún vínculo del catálogo (regla de respaldo)
    knownAt: null,     // κ opcional (ISO o versión del grafo): "tal como se conocía entonces"
    mode: 'catalog',   // 'db' (servidor) | 'catalog' (sin base / sin conexión: regla de respaldo)
    srv: null,         // {key, pairs:Set('a>b'), nodes:Set} de la última respuesta del servidor
    cache: new Map(),  // 'YYYY-MM-DD|κ' → {pairs, nodes, counts}
    inflight: null, timer: 0, noDb: false, err: null,
    fails: new Map(),  // 'YYYY-MM-DD|κ' → {n, until}: una foto que falló NO se vuelve a pedir hasta su espera
    facts: [],         // hechos empresa↔empresa → línea punteada
    marks: [],         // hechos empresa↔concepto (EUV, Ley CHIPS, China…) → anillo en la empresa
    msel: null,
    layer: null,       // <g> de eventos
    sel: null,         // selección d3 de líneas de eventos
    play: null,
    raf: 0,
  };

  function build() {
    if (S.built) return;
    S.built = true;
    S.linked = new Set();
    (window.LINKS || []).forEach(l => {
      const a = canon(lid(l.source)), b = canon(lid(l.target));
      if (a) S.linked.add(a);
      if (b) S.linked.add(b);
    });
    const seen = new Set();
    const concepts = {};
    ((window.ONTOLOGY && window.ONTOLOGY.objects) || []).forEach(o => { concepts[o.id] = o.label; });
    const stack = {};
    (window.TEMPORAL_SEED_FACTS || []).forEach(f => {
      if (!f) return;
      const from = Date.parse(f.valid_from || '');
      if (isNaN(from)) return;
      const until = Date.parse(f.valid_until || '');
      const a = canon(f.subject), b = f.object_type === 'node' ? canon(f.object) : null;
      // Un solo extremo en el mapa (el otro es un concepto o un atributo):
      // el hecho se ancla como anillo alrededor de esa empresa.
      if (!!a !== !!b || (a && f.object_type !== 'node')) {
        const node = a || b;
        const other = a ? f.object : f.subject;
        if (!node) return;
        const i = stack[node] = (stack[node] || 0) + 1;
        S.marks.push({
          id: f.id, node, other: concepts[other] || other, from, until: isNaN(until) ? null : until,
          rel: f.rel || 'restringe', impact: (f.meta && f.meta.impact) || 5, ring: i - 1,
          headline: (f.meta && f.meta.headline) || f.predicate || '',
        });
        return;
      }
      if (!a || !b || a === b) return;
      const dedupe = a + '>' + b + '>' + (f.rel || '') + '>' + from;
      if (seen.has(dedupe)) return;
      seen.add(dedupe);
      S.facts.push({
        id: f.id, a, b, from, until: isNaN(until) ? null : until,
        rel: f.rel || 'supply', impact: (f.meta && f.meta.impact) || 5,
        headline: (f.meta && f.meta.headline) || f.predicate || '',
      });
    });
    S.facts.sort((x, y) => x.from - y.from);
  }

  /* ── predicados que usa _refreshStylesCore (app.html) ─────────────────── */
  // Con datos del servidor: lo que /api/ontology/graph?as_of= dice vigente. Sin base: la regla de respaldo
  // (catalogNodeOk/catalogLinkOk), que es la MISMA con la que scripts/migrate_v0_to_ontology.py carga el catálogo.
  function nodeOk(id) {
    if (!S.active) return true;
    if (S.mode === 'db' && S.srv) return S.srv.nodes.has(canon(id) || id);
    return catalogNodeOk(id);
  }
  function linkOk(l) {
    if (!S.active) return true;
    const s = canon(lid(l.source)) || lid(l.source), t = canon(lid(l.target)) || lid(l.target);
    if (S.mode === 'db' && S.srv) return S.srv.pairs.has(s + '>' + t) || S.srv.pairs.has(t + '>' + s);
    return catalogLinkOk(s, t);
  }
  // regla de respaldo (sin base): vínculo del catálogo vigente desde GENESIS; empresa = extremo de algo vigente
  function catalogLinkOk(s, t) {
    return S.dateMs >= GENESIS_MS || datedPairOn(s, t);
  }
  function catalogNodeOk(id) {
    const c = canon(id) || id;
    if (S.dateMs >= GENESIS_MS && S.linked && S.linked.has(c)) return true;
    return S.facts.some(f => factOn(f) && (f.a === c || f.b === c));
  }
  function datedPairOn(s, t) {
    return S.facts.some(f => factOn(f) && ((f.a === s && f.b === t) || (f.a === t && f.b === s)));
  }
  function factOn(f) {
    return f.from <= S.dateMs && (f.until == null || S.dateMs < f.until);
  }

  /* ── el viaje en el tiempo del SERVIDOR (DT-M3) ───────────────────────── */
  function isoDay(ms) { return new Date(ms).toISOString().slice(0, 10); }
  function asofKey() { return isoDay(S.dateMs) + '|' + (S.knownAt || ''); }
  function base() { return (typeof window.BASE === 'string' && window.BASE) ? window.BASE : ''; }
  function asofUrl(day) {
    return base() + '/api/ontology/graph?as_of=' + encodeURIComponent(day) +
      (S.knownAt ? '&known_at=' + encodeURIComponent(S.knownAt) : '');
  }
  function digest(d) {
    const pairs = new Set(), nodes = new Set();
    (d.links || []).forEach(l => {
      const a = canon(l.source) || l.source, b = canon(l.target) || l.target;
      if (!a || !b) return;
      pairs.add(a + '>' + b);
      nodes.add(a); nodes.add(b);
    });
    (d.nodes || []).forEach(n => { if (n && n.id) nodes.add(canon(n.id) || n.id); });
    return { pairs, nodes, counts: d.counts || null, as_of: d.as_of || null };
  }
  function useEntry(key, e) {
    S.srv = Object.assign({ key }, e);
    S.mode = 'db';
    S.err = null;
  }
  // pide la foto de la fecha (con espera corta y UNA petición en vuelo); mientras llega se ve la anterior
  function want() {
    if (!S.active || S.noDb) return;
    const key = asofKey();
    if (S.srv && S.srv.key === key) return;
    const hit = S.cache.get(key);
    if (hit) { useEntry(key, hit); return; }
    const f = S.fails.get(key);              // revisión lote I: una foto que falló espera (antes: 4 pedidos/s sin fin)
    if (f && Date.now() < f.until) return;
    // ▶ reproduciendo: el deslizador se mueve cada 160 ms < espera de 250 ms → la espera nunca vencía y se veía la
    // foto de la fecha inicial. Durante la reproducción: UN pedido en vuelo, siempre por la fecha más nueva.
    if (S.play) { if (!S.timer) fetchAsof(); return; }
    if (S.timer) clearTimeout(S.timer);
    S.timer = setTimeout(() => { S.timer = 0; fetchAsof(); }, ASOF_DEBOUNCE_MS);
  }
  function failed(key) {
    const prev = S.fails.get(key);
    const n = prev ? prev.n + 1 : 1;
    S.fails.set(key, { n, until: Date.now() + Math.min(ASOF_FAIL_MAX_MS, ASOF_FAIL_BASE_MS * Math.pow(2, n - 1)) });
    if (S.fails.size > ASOF_CACHE_MAX) S.fails.delete(S.fails.keys().next().value);
  }
  function fetchAsof() {
    if (!S.active || S.noDb || S.inflight || typeof fetch !== 'function') return;
    const key = asofKey(), day = key.split('|')[0];
    S.inflight = key;
    fetch(asofUrl(day), { headers: { Accept: 'application/json' } }).then(r => {
      return r.json().catch(() => null).then(d => {
        if (r.status === 503 && !(d && d.offline)) { S.noDb = true; return null; }   // sin base: regla de respaldo
        if (r.status === 503) { S.err = L('sin conexión', 'offline'); failed(key); return null; }   // 503 del SW
        if (!r.ok || !d) {
          S.err = (isEn() ? (d && (d.error_en || d.error)) : (d && d.error)) || ('HTTP ' + r.status);
          failed(key);
          return null;
        }
        return d;
      });
    }).then(d => {
      S.inflight = null;
      if (d && Array.isArray(d.links)) {
        const e = digest(d);
        S.cache.set(key, e);
        S.fails.delete(key);
        if (S.cache.size > ASOF_CACHE_MAX) S.cache.delete(S.cache.keys().next().value);
        if (key === asofKey()) useEntry(key, e);
      }
      if (S.noDb) { S.mode = 'catalog'; S.srv = null; }
      schedule();
      if (key !== asofKey()) want();       // el deslizador se movió mientras tanto
    }).catch(() => {
      S.inflight = null;                    // sin conexión: la regla de respaldo, rotulada
      S.mode = 'catalog'; S.srv = null;
      S.err = L('sin conexión', 'offline');
      failed(key);
      schedule();
    });
  }

  /* ── capa de eventos ──────────────────────────────────────────────────── */
  function ensureLayer() {
    if (S.layer || !window._mapLayers) return;
    const ml = window._mapLayers;
    const nodeEl = ml.nodeLayer.node();
    S.layer = ml.root.insert('g', () => nodeEl).attr('class', 'mt-events');
    S.sel = S.layer.selectAll('line').data(S.facts).join('line')
      .attr('stroke', d => relColor(d.rel))
      .attr('stroke-width', d => 2 + d.impact * 0.25)
      .attr('stroke-dasharray', '6 4')
      .attr('stroke-linecap', 'round')
      .style('pointer-events', 'visibleStroke')
      .style('cursor', 'pointer')
      .on('click', (e, d) => {
        e.stopPropagation();
        const go = window.jumpTo || window.selectNode;
        if (typeof go === 'function') go(d.a);
      });
    S.sel.append('title');
    S.msel = S.layer.selectAll('circle').data(S.marks).join('circle')
      .attr('fill', 'none')
      .attr('stroke', d => relColor(d.rel))
      .attr('stroke-width', 2)
      .attr('stroke-dasharray', '3 3')
      .style('pointer-events', 'visibleStroke')
      .style('cursor', 'pointer')
      .on('click', (e, d) => {
        e.stopPropagation();
        const go = window.jumpTo || window.selectNode;
        if (typeof go === 'function') go(d.node);
      });
    S.msel.append('title');
    paint();
  }
  function paint() {
    if (!S.sel) return;
    const N = window.NODE_BY_ID || {};
    S.sel.attr('x1', d => (N[d.a] || {}).x || 0).attr('y1', d => (N[d.a] || {}).y || 0)
         .attr('x2', d => (N[d.b] || {}).x || 0).attr('y2', d => (N[d.b] || {}).y || 0);
    if (S.msel) {
      const rad = id => { try { return window.computeNodeRadius(id); } catch (e) { return 8; } };
      S.msel.attr('cx', d => (N[d.node] || {}).x || 0).attr('cy', d => (N[d.node] || {}).y || 0)
        .attr('r', d => rad(d.node) + 5 + d.ring * 4);
    }
  }
  function styleEvents() {
    if (!S.sel) return;
    const show = S.events;
    S.layer.style('display', show ? null : 'none');
    if (!show) return;
    const recent = 2 * 365 * DAY;   // lo reciente respecto a la fecha brilla más
    S.sel.style('display', d => factOn(d) ? null : 'none')
      .style('stroke-opacity', d => (S.dateMs - d.from) < recent ? 0.95 : 0.5);
    const N = window.NODE_BY_ID || {};
    S.sel.select('title').text(d =>
      fmt(d.from) + (d.until ? ' → ' + fmt(d.until) : '') + ' · ' +
      ((N[d.a] || {}).label || d.a) + ' ↔ ' + ((N[d.b] || {}).label || d.b) + '\n' + d.headline);
    if (S.msel) {
      S.msel.style('display', d => factOn(d) ? null : 'none')
        .style('stroke-opacity', d => (S.dateMs - d.from) < recent ? 0.95 : 0.45);
      S.msel.select('title').text(d =>
        fmt(d.from) + (d.until ? ' → ' + fmt(d.until) : '') + ' · ' +
        ((N[d.node] || {}).label || d.node) + ' · ' + d.other + '\n' + d.headline);
    }
  }

  /* ── barra de tiempo ──────────────────────────────────────────────────── */
  function ensureBar() {
    if (document.getElementById('mt-bar')) return;
    const wrap = document.querySelector('.graph-wrap');
    if (!wrap) return;
    const st = document.createElement('style');
    st.textContent = ''
      + '#mt-bar{position:absolute;left:50%;transform:translateX(-50%);bottom:14px;z-index:6;display:none;'
      + 'align-items:center;gap:8px;flex-wrap:wrap;width:min(760px,calc(100% - 32px));padding:9px 12px;'
      + 'background:rgba(12,14,24,.92);border:1px solid rgba(142,90,255,.45);border-radius:12px;'
      + 'backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);box-shadow:0 8px 26px rgba(0,0,0,.35)}'
      + '#mt-bar.on{display:flex}'
      + '#mt-bar button{font:600 12px Inter,system-ui,sans-serif;padding:5px 10px;border-radius:8px;cursor:pointer;'
      + 'border:1px solid rgba(255,255,255,.14);background:none;color:#d6daf0;white-space:nowrap}'
      + '#mt-bar button.on{border-color:#8e5aff;color:#cabeff;background:rgba(142,90,255,.18)}'
      + '#mt-play{width:32px;height:32px;border-radius:50%!important;padding:0!important;border-color:#8e5aff!important;color:#cabeff!important}'
      + '#mt-range{flex:1;min-width:140px;accent-color:#8e5aff}'
      + '#mt-date{font:700 13px "JetBrains Mono",monospace;color:#fff;min-width:74px;text-align:right}'
      + '#mt-count{flex-basis:100%;font-size:11px;color:#9aa1bd;line-height:1.35}'
      + '#mt-btn.on{border-color:#8e5aff!important;color:#cabeff!important;background:rgba(142,90,255,.25)!important}'
      + '@media(max-width:640px){#mt-bar{bottom:8px;gap:6px;padding:8px}#mt-range{flex-basis:100%;order:5}}';
    document.head.appendChild(st);
    const bar = document.createElement('div');
    bar.id = 'mt-bar';
    bar.innerHTML =
      '<button id="mt-play">▶</button>' +
      `<input id="mt-range" type="range" min="${MIN_MS}" max="${S.maxMs}" step="${STEP}" value="${S.dateMs}">` +
      '<span id="mt-date"></span>' +
      '<button id="mt-ev"></button><button id="mt-facts"></button><button id="mt-3d"></button>' +
      '<button id="mt-close">✕</button>' +
      '<div id="mt-count"></div>';
    wrap.appendChild(bar);
    bar.addEventListener('click', e => e.stopPropagation());
    const range = bar.querySelector('#mt-range');
    range.addEventListener('input', () => { stopPlay(); S.dateMs = +range.value; schedule(); });
    bar.querySelector('#mt-play').onclick = togglePlay;
    bar.querySelector('#mt-ev').onclick = () => { S.events = !S.events; ensureLayer(); schedule(); };
    bar.querySelector('#mt-facts').onclick = () => window.__tkgShow('facts');
    bar.querySelector('#mt-3d').onclick = () => window.__tkgShow('t3d');
    bar.querySelector('#mt-close').onclick = close;
    relabel();
  }

  function relabel() {
    const btn = document.getElementById('mt-btn');
    if (btn) btn.title = L('⏱ Tiempo: ver la cadena como era en una fecha + eventos con fecha',
                           '⏱ Time: see the chain as it was on a date + dated events');
    const set = (id, txt, tip) => { const el = document.getElementById(id); if (el) { el.textContent = txt; if (tip) el.title = tip; } };
    set('mt-ev', '⚡ ' + L('Eventos', 'Events'),
        L('Hechos con fecha: línea punteada = entre dos empresas; anillo punteado = una empresa y un tema (EUV, Ley CHIPS, China…)',
          'Dated facts: dashed line = between two companies; dashed ring = a company and a topic (EUV, CHIPS Act, China…)'));
    set('mt-facts', '☰ ' + L('Hechos', 'Facts'), L('Lista completa de hechos con fecha', 'Full list of dated facts'));
    set('mt-3d', '⬗ 3D', L('Vista 3D: la profundidad es el tiempo', '3D view: depth is time'));
    set('mt-close', '✕', L('Volver a hoy', 'Back to today'));
    set('mt-play', S.play ? '❚❚' : '▶', L('Reproducir la historia', 'Play the history'));
    if (S.active) update();
  }

  function update() {
    const d = document.getElementById('mt-date');
    if (d) d.textContent = fmt(S.dateMs);
    const r = document.getElementById('mt-range');
    if (r && +r.value !== S.dateMs) r.value = S.dateMs;
    const ev = document.getElementById('mt-ev');
    if (ev) ev.classList.toggle('on', S.events);
    // cuentas: qué existía en esa fecha (texto simple, explica lo que se ve)
    const ids = new Set(Object.keys(window.NODE_BY_ID || {}).map(canon).filter(Boolean));
    let nOk = 0; ids.forEach(id => { if (nodeOk(id)) nOk++; });
    let lOk = 0; (window.LINKS || []).forEach(l => { if (linkOk(l)) lOk++; });
    const evN = S.facts.filter(factOn).length + S.marks.filter(factOn).length;
    const c = document.getElementById('mt-count');
    if (c) c.textContent = L(
      `En ${fmt(S.dateMs)}: ${nOk} de ${ids.size} empresas y ${lOk} vínculos vigentes. ` +
      `${evN} eventos${S.events ? '' : ' (actívalos con ⚡)'}. Lo apagado no estaba vigente. `,
      `In ${fmt(S.dateMs)}: ${nOk} of ${ids.size} companies and ${lOk} links in force. ` +
      `${evN} events${S.events ? '' : ' (turn on with ⚡)'}. Dimmed = not in force. `) + sourceNote();
  }

  // de dónde sale la foto (siempre dicho): la base del servidor o la regla de respaldo del catálogo
  function sourceNote() {
    const pre = S.dateMs < GENESIS_MS
      ? L(' Antes de 2000 solo cuentan los hechos con fecha: los vínculos sin fecha se rastrean desde 2000.',
          ' Before 2000 only dated facts count: undated links are tracked from 2000.') : '';
    if (S.mode === 'db' && S.srv) {
      const stale = S.srv.key !== asofKey() ? L(' (actualizando…)', ' (updating…)') : '';
      return L('Fuente: base de datos (viaje en el tiempo del servidor', 'Source: database (server time travel') +
        (S.knownAt ? L(', tal como se conocía en ', ', as known at ') + S.knownAt : '') + ')' + stale + '.' + pre;
    }
    return L('Fuente: regla del catálogo (', 'Source: catalog rule (') +
      (S.noDb ? L('sin base de datos', 'no database') : (S.err || L('esperando al servidor', 'waiting for the server'))) +
      L('): la misma con la que se carga la base.', '): the same one used to load the database.') + pre;
  }

  function schedule() {
    want();
    if (S.raf) return;
    S.raf = requestAnimationFrame(() => {
      S.raf = 0;
      if (typeof window.refreshStyles === 'function') window.refreshStyles();
      styleEvents();
      update();
    });
  }

  function togglePlay() { if (S.play) stopPlay(); else startPlay(); }
  function startPlay() {
    if (S.dateMs >= S.maxMs) S.dateMs = Date.UTC(1995, 0, 1);
    S.play = setInterval(() => {
      S.dateMs = Math.min(S.maxMs, S.dateMs + 4 * STEP);
      schedule();
      if (S.dateMs >= S.maxMs) stopPlay();
    }, 160);
    relabel();
  }
  function stopPlay() {
    if (!S.play) return;
    clearInterval(S.play); S.play = null;
    relabel();
  }

  function open() {
    build(); ensureBar();
    if (!S.active) { S.noDb = false; S.fails.clear(); }   // al ABRIR: la base pudo volver (un 503 no es para siempre)
    S.active = true;
    const bar = document.getElementById('mt-bar'); if (bar) bar.classList.add('on');
    // el aviso "toca una empresa" del teléfono tapaba la barra
    const mh = document.getElementById('mobile-hint'); if (mh) mh.style.display = 'none';
    const btn = document.getElementById('mt-btn'); if (btn) btn.classList.add('on');
    schedule();
  }
  function close() {
    stopPlay();
    if (S.timer) { clearTimeout(S.timer); S.timer = 0; }
    S.active = false; S.events = false; S.dateMs = S.maxMs; S.knownAt = null;
    const bar = document.getElementById('mt-bar'); if (bar) bar.classList.remove('on');
    const btn = document.getElementById('mt-btn'); if (btn) btn.classList.remove('on');
    schedule();
  }
  function toggle() { if (S.active) close(); else open(); }

  // Para KHIPU "GRAPH ASOF <fecha>": mueve el MAPA a esa fecha. opts.known_at (opcional, con base): la foto de esa
  // fecha TAL COMO SE CONOCÍA en κ (ISO o versión del grafo) — G(t, κ) del servidor, paso 23.
  function setDate(v, opts) {
    const ms = typeof v === 'number' ? v : Date.parse(v);
    if (ms == null || isNaN(ms)) return false;
    if (typeof window.switchTab === 'function') window.switchTab('map');
    open();
    stopPlay();
    if (opts && Object.prototype.hasOwnProperty.call(opts, 'known_at')) setKnownAt(opts.known_at);
    S.dateMs = Math.max(MIN_MS, Math.min(S.maxMs, ms));
    schedule();
    return true;
  }
  function setKnownAt(k) {
    S.knownAt = (k == null || k === '') ? null : String(k).slice(0, 40);
    S.srv = null;
    if (!S.noDb) S.mode = 'catalog';
    schedule();
  }

  // Vistas del antiguo Grafo Temporal (lista de hechos / 3D / grafo), ahora
  // abiertas desde la barra de tiempo del mapa.
  window.__tkgShow = function (view) {
    if (typeof window.switchTab === 'function') window.switchTab('tkg');
    if (typeof window.initTKGTab === 'function') window.initTKGTab();
    setTimeout(() => {
      const b = document.querySelector('#tkg-tabseg button[data-t="' + (view || 'viz') + '"]');
      if (b) b.click();
      if (typeof window.__tkgSetDate === 'function' && S.active) window.__tkgSetDate(S.dateMs);
    }, 60);
  };

  function mountButton() {
    // Junto a + − ⤢ 🪐: los controles del mapa siempre visibles (la barra de
    // filtros, en pantallas chicas, queda tapada o plegada).
    const zc = document.querySelector('.graph-wrap .zoom-ctrl');
    if (!zc || document.getElementById('mt-btn')) return;
    const btn = document.createElement('button');
    btn.id = 'mt-btn'; btn.style.fontSize = '13px';
    btn.textContent = '⏱';
    btn.onclick = toggle;
    zc.appendChild(btn);
    relabel();
  }

  window.KhipuMapTime = {
    open, close, toggle, setDate, setKnownAt, relabel, paint, nodeOk, linkOk, togglePlay,
    get playing() { return !!S.play; },
    get active() { return S.active; },
    get source() { return S.mode === 'db' && S.srv ? 'db' : 'catalog'; },
    get knownAt() { return S.knownAt; },
    get events() { return S.events; },
    get dateMs() { return S.dateMs; },
  };
  window._mapTimePaint = paint;

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mountButton);
  else mountButton();
})();
