/* ============================================================================
   engine/maptime.js — EL TIEMPO DENTRO DEL MAPA PRINCIPAL (2026-09-25)
   Fabrizio: "el grafo temporal y el normal deberían ser uno; el temporal no
   da mucho por sí solo". Antes el tiempo vivía en una pestaña aparte con su
   propio grafo pequeño. Ahora el MISMO mapa de 949 nodos tiene:

     ⏱ línea de tiempo  → la cadena tal como era en una fecha: las empresas
                          aún no fundadas y los vínculos que aún no existían
                          se apagan (fundación = NODE_META.founded; inicio de
                          un vínculo = el hecho fechado más antiguo del par).
     ⚡ capa Eventos     → los hechos fechados (sanciones, inversiones,
                          fábricas, competencia…) dibujados como líneas
                          punteadas entre las dos empresas, visibles solo
                          dentro de su ventana de validez. Apagada por defecto.
     ☰ Hechos / ⬗ 3D    → la lista de hechos y la vista 3D temporal siguen
                          existiendo, pero como VISTAS que se abren desde aquí.

   Honestidad del dato: un vínculo sin fecha conocida NO se inventa una; se
   considera presente siempre que sus dos empresas existan. Solo se dibujan
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
    try { if (typeof window.getLinkColorHex === 'function') return window.getLinkColorHex(rel); } catch (e) {}
    return '#8e5aff';
  }

  const S = {
    active: false,     // ⏱ abierto → el filtro por fecha se aplica
    events: false,     // ⚡ capa de eventos visible
    dateMs: Date.now(),
    maxMs: Date.now(),
    built: false,
    founded: {},       // id → ms de fundación
    pairFrom: {},      // 'a|b' (ordenado) → ms del hecho más antiguo del par
    facts: [],         // hechos dibujables en el mapa
    layer: null,       // <g> de eventos
    sel: null,         // selección d3 de líneas de eventos
    play: null,
    raf: 0,
  };

  function pairKey(a, b) { return a < b ? a + '|' + b : b + '|' + a; }

  function build() {
    if (S.built) return;
    S.built = true;
    const meta = window.NODE_META || {};
    Object.keys(window.NODE_BY_ID || {}).forEach(k => {
      const id = canon(k);
      if (!id || S.founded[id] != null) return;
      const y = parseInt(String((meta[id] && meta[id].founded) || ''), 10);
      if (y > 1000 && y < 2100) S.founded[id] = Date.UTC(y, 0, 1);
    });
    const seen = new Set();
    (window.TEMPORAL_SEED_FACTS || []).forEach(f => {
      if (!f || f.object_type !== 'node') return;
      const a = canon(f.subject), b = canon(f.object);
      const from = Date.parse(f.valid_from || '');
      if (!a || !b || a === b || isNaN(from)) return;
      const until = Date.parse(f.valid_until || '');
      const k = pairKey(a, b);
      if (S.pairFrom[k] == null || from < S.pairFrom[k]) S.pairFrom[k] = from;
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
  function nodeOk(id) {
    if (!S.active) return true;
    const f = S.founded[id];
    return f == null || f <= S.dateMs;
  }
  function linkOk(l) {
    if (!S.active) return true;
    const s = lid(l.source), t = lid(l.target);
    if (!nodeOk(s) || !nodeOk(t)) return false;
    const from = S.pairFrom[pairKey(s, t)];
    return from == null || from <= S.dateMs;
  }
  function factOn(f) {
    return f.from <= S.dateMs && (f.until == null || S.dateMs <= f.until);
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
    paint();
  }
  function paint() {
    if (!S.sel) return;
    const N = window.NODE_BY_ID || {};
    S.sel.attr('x1', d => (N[d.a] || {}).x || 0).attr('y1', d => (N[d.a] || {}).y || 0)
         .attr('x2', d => (N[d.b] || {}).x || 0).attr('y2', d => (N[d.b] || {}).y || 0);
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
        L('Hechos con fecha (sanciones, inversiones, fábricas…) como líneas punteadas',
          'Dated facts (sanctions, investments, fabs…) as dashed lines'));
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
    const evN = S.facts.filter(factOn).length;
    const c = document.getElementById('mt-count');
    if (c) c.textContent = L(
      `En ${fmt(S.dateMs)}: ${nOk} de ${ids.size} empresas ya existían y ${lOk} vínculos. ` +
      `${evN} eventos vigentes${S.events ? '' : ' (actívalos con ⚡)'}. Lo apagado aún no existía.`,
      `In ${fmt(S.dateMs)}: ${nOk} of ${ids.size} companies already existed, with ${lOk} links. ` +
      `${evN} active events${S.events ? '' : ' (turn on with ⚡)'}. Dimmed = did not exist yet.`);
  }

  function schedule() {
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
    S.active = true;
    const bar = document.getElementById('mt-bar'); if (bar) bar.classList.add('on');
    const btn = document.getElementById('mt-btn'); if (btn) btn.classList.add('on');
    schedule();
  }
  function close() {
    stopPlay();
    S.active = false; S.events = false; S.dateMs = S.maxMs;
    const bar = document.getElementById('mt-bar'); if (bar) bar.classList.remove('on');
    const btn = document.getElementById('mt-btn'); if (btn) btn.classList.remove('on');
    schedule();
  }
  function toggle() { if (S.active) close(); else open(); }

  // Para KHIPU "GRAPH ASOF <fecha>": mueve el MAPA a esa fecha.
  function setDate(v) {
    const ms = typeof v === 'number' ? v : Date.parse(v);
    if (ms == null || isNaN(ms)) return false;
    if (typeof window.switchTab === 'function') window.switchTab('map');
    open();
    stopPlay();
    S.dateMs = Math.max(MIN_MS, Math.min(S.maxMs, ms));
    schedule();
    return true;
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
    open, close, toggle, setDate, relabel, paint, nodeOk, linkOk,
    get active() { return S.active; },
    get events() { return S.events; },
    get dateMs() { return S.dateMs; },
  };
  window._mapTimePaint = paint;

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mountButton);
  else mountButton();
})();
