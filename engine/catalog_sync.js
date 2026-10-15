/* ============================================================================
   engine/catalog_sync.js — EXPANSION_5K E3.1 (lote L, 2026-10-15): el catálogo del navegador se COMPLETA con lo
   que solo está en Postgres.

   El navegador arma NODES/LINKS con el catálogo estático (nodes/*.js + nodes/merge_graph.js). Una empresa que solo
   existe en la base (las importadas con el importador, IncorporarEmpresa) no salía en el mapa, la búsqueda (📍,
   KhipuResolve) ni las listas. Al arrancar, este módulo pide GET /api/hot/catalog (la diferencia entre el grafo de
   los LECTORES del servidor —el mismo que usan el MCP, el chat y el NRS— y el catálogo estático) y la AÑADE:

     · nodos nuevos → NODES / NODE_BY_ID (un id que el navegador ya tiene NUNCA se repite ni se pisa);
     · vínculos nuevos → LINKS (clave origen→destino·tipo, como el merge; extremos por window._canonId);
     · alias de fusiones de la base → NODE_BY_ID / NODE_ID_ALIAS (solo claves que no existían);
     · nombres legales / alternativos → LEGAL_NAMES (la búsqueda los encuentra; nunca pisa uno existente);
     · el mapa: elementos SVG con la MISMA forma que los del catálogo (app_main.js) dentro de las selecciones
       vivas, la simulación d3 re-inicializada y UN re-asentado corto (_resizeNodesByCap → _ensureMapSettled):
       la física se adelanta sin dibujar y nunca se llama sim.alpha().restart() fuera del arrastre.

   TAMAÑO DEL NODO = su capitalización (pedido de Fabrizio): computeNodeRadius tal cual — capitalización EN VIVO
   (KhipuLiveCaps, que el servidor ya calcula para toda empresa del grafo con símbolo) o la valuación VERIFICADA de
   una privada (última ronda cerrada con fuente). Sin dato: el tamaño fijo de "sin dato" de computeNodeRadius y el
   aviso «Sin capitalización» en la tarjeta flotante. Nunca al azar ni por grado.

   Los textos largos (rol, qué suministra, foso, crecimiento) y el texto de cada vínculo nuevo NO viajan al arrancar:
   se piden al abrir la ficha (renderDetail) con GET /api/hot/catalog/detail?ids=.

   Sin base de datos (o con error / sin red) la diferencia es vacía: no se toca nada. Se carga JUSTO después de
   nodes/merge_graph.js (empieza a pedir temprano) y aplica cuando todos los scripts corrieron (DOMContentLoaded).
   API: window.KhipuCatalogSync = { status(), ready, ensureDetail(id), isDbNode(id), capStatus(id) }.
   ============================================================================ */
(function () {
  'use strict';
  if (window.KhipuCatalogSync) return;
  var W = window;
  var API = '/api/hot/catalog';
  var DETAIL_API = '/api/hot/catalog/detail';
  var MAX_PAGES = 40;

  var ST = { phase: 'fetching', generation: null, graph_version: null, source: null, fallback: null, pages: 0,
             total_nodes: 0, total_links: 0, added_nodes: 0, added_links: 0, aliases: 0, names: 0, valuations: 0,
             skipped: { existing_node: 0, existing_link: 0, missing_endpoint: 0, self_loop: 0 },
             map: null, fetch_ms: null, apply_ms: null, data_ms: null, map_ms: null, resize_ms: null, error: null };
  var T0 = (W.performance && performance.now) ? performance.now() : Date.now();
  var DB_IDS = new Set();      // empresas añadidas desde la base
  var TOUCH = new Set();       // ids tocados por un vínculo añadido (su texto llega con la ficha)
  var LINK_BY_KEY = {};        // clave → vínculo añadido (para ponerle su texto)
  var DONE = {};               // id → true: textos y vínculos ya pedidos
  var INFLIGHT = {};           // id → promesa

  function now() { return (W.performance && performance.now) ? performance.now() : Date.now(); }
  function en() {
    try { return (W.LANG || localStorage.getItem('eco_lang') || 'es') === 'en'; } catch (e) { return false; }
  }
  function L(es, eng) { return en() ? eng : es; }
  function lid(v) { return (v && typeof v === 'object') ? v.id : v; }
  function key(s, t, type) { return s + '→' + t + '·' + (type || 'supply'); }
  function delay(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  function hash(s) { var h = 0; s = String(s); for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return h >>> 0; }

  function getJSON(url) {
    return fetch(url, { credentials: 'same-origin', headers: { Accept: 'application/json' } }).then(function (r) {
      var ct = (r.headers && r.headers.get('content-type')) || '';
      if (ct.indexOf('json') < 0) return { status: r.status, body: null };
      return r.json().then(function (b) { return { status: r.status, body: b }; },
                           function () { return { status: r.status, body: null }; });
    });
  }

  // ── 1. pedir todas las páginas de UNA generación (409 = cambió entre páginas → de nuevo, una vez) ──────────────
  function fetchAll(attempt) {
    var pages = [], gen = null;
    function page(off) {
      var u = API + '?offset=' + off + (gen ? '&gen=' + encodeURIComponent(gen) : '');
      return getJSON(u).then(function (res) {
        var b = res.body || {};
        if (res.status === 409 && attempt < 2) return fetchAll(attempt + 1);
        if (res.status === 503 && b.code === 'view_warming' && attempt < 4) {
          return delay(3000).then(function () { return fetchAll(attempt + 1); });
        }
        if (res.status !== 200 || !b.data) throw new Error('HTTP ' + res.status + (b.code ? ' ' + b.code : ''));
        var d = b.data;
        if (!gen) gen = d.generation;
        pages.push(d);
        if (d.next_offset != null && pages.length < MAX_PAGES) return page(d.next_offset);
        return pages;
      });
    }
    return page(0);
  }

  // ── 2. añadir a NODES / NODE_BY_ID / LINKS (solo lo que falta) ────────────────────────────────────────────────
  function rowsOf(fields, rows) {
    var out = [];
    (rows || []).forEach(function (r) {
      var o = {};
      for (var i = 0; i < fields.length; i++) o[fields[i]] = r[i];
      out.push(o);
    });
    return out;
  }
  // Nombre del país en el idioma activo: ISO-2 → window.KhipuCountries (engine/geo_coords.js); si no, el texto.
  function countryText(iso2, k) {
    try { if (W.KhipuCountries && (iso2 || k)) return W.KhipuCountries.label(iso2 || k, en() ? 'en' : 'es') || k || ''; } catch (e) {}
    return k || '';
  }
  function fmtB(v) { v = +v; return v >= 100 ? String(Math.round(v)) : String(Math.round(v * 10) / 10); }

  function mkNode(o) {
    var n = { id: o.id, label: o.label || o.id, ticker: typeof o.ticker === 'string' ? o.ticker : '',
              mkt: o.mkt || null, preipo: !!o.preipo,
              // el NRS (_nrsTerms) solo mira 🔴/🟡 del crecimiento: la señal llega ya; el texto, con la ficha
              growth: o.gflag === 'r' ? '🔴' : (o.gflag === 'y' ? '🟡' : ''),
              role: '', supplies: '', moat: '', from_db: true };
    if (o.cat) n.cat = o.cat;
    if (o.sector) n.sector = o.sector;
    if (o.country) n.country = o.country;
    if (o.country_iso2) n.country_iso2 = o.country_iso2;
    if (o.margin != null && isFinite(+o.margin)) n.margin = +o.margin;
    if (o.status) n.listing = { status: o.status, source: 'ontology' };
    n.loc = countryText(o.country_iso2, o.country);
    return n;
  }

  function applyData(pages) {
    var NB = W.NODE_BY_ID, NODES_ = W.NODES, LINKS_ = W.LINKS;
    if (!NB || !Array.isArray(NODES_) || !Array.isArray(LINKS_)) { ST.phase = 'no_graph'; return null; }
    var first = pages[0];
    ST.generation = first.generation; ST.graph_version = first.graph_version; ST.source = first.source;
    ST.fallback = first.fallback; ST.pages = pages.length;
    ST.total_nodes = first.total_nodes || 0; ST.total_links = first.total_links || 0;
    var addN = [], addL = [];
    var META = W.NODE_META || null, LN = W.LEGAL_NAMES || null;
    var IDA = (typeof NODE_ID_ALIAS !== 'undefined' && NODE_ID_ALIAS) ? NODE_ID_ALIAS : (W.NODE_ID_ALIAS || null);
    pages.forEach(function (d) {
      rowsOf(d.node_fields, d.nodes).forEach(function (o) {
        if (!o.id || NB[o.id]) { ST.skipped.existing_node++; return; }
        var n = mkNode(o);
        NODES_.push(n);
        NB[n.id] = n;
        DB_IDS.add(n.id);
        addN.push(n);
      });
      Object.keys(d.valuations || {}).forEach(function (id) {
        var v = d.valuations[id];
        if (!META || !DB_IDS.has(id) || !v || !(+v.usd_b > 0)) return;
        var m = META[id] || (META[id] = {});
        if (+m.mktcap_b > 0) return;              // la capitalización en vivo ya llegó: manda
        m.mktcap_b = +v.usd_b;
        m.mktcap_verified = { as_of: v.as_of, label: '$' + fmtB(v.usd_b) + 'B (' + v.as_of + ')',
                              source_url: v.source_url, round: v.round || null, confidence: v.confidence };
        ST.valuations++;
      });
      Object.keys(d.names || {}).forEach(function (nm) {
        if (!LN || Object.prototype.hasOwnProperty.call(LN, nm) || !NB[d.names[nm]]) return;
        LN[nm] = d.names[nm];
        ST.names++;
      });
    });
    var aliases = first.aliases || {};
    Object.keys(aliases).forEach(function (a) {
      var c = NB[aliases[a]];
      if (!c || NB[a]) return;
      NB[a] = c;
      if (IDA && !Object.prototype.hasOwnProperty.call(IDA, a)) IDA[a] = c.id;
      ST.aliases++;
    });
    var have = new Set();
    LINKS_.forEach(function (l) { have.add(key(lid(l.source), lid(l.target), l.type)); });
    var canon = typeof W._canonId === 'function' ? W._canonId : function (x) { return (NB[x] && NB[x].id) || x; };
    pages.forEach(function (d) {
      rowsOf(d.link_fields, d.links).forEach(function (o) {
        var sN = NB[canon(o.source)], tN = NB[canon(o.target)];
        if (!sN || !tN) { ST.skipped.missing_endpoint++; return; }
        if (sN.id === tN.id) { ST.skipped.self_loop++; return; }
        var k = key(sN.id, tN.id, o.type);
        if (have.has(k)) { ST.skipped.existing_link++; return; }
        have.add(k);
        var l = { source: sN.id, target: tN.id, w: (+o.w > 0 ? +o.w : 2), rel: '', type: o.type || 'supply',
                  conf: (o.conf != null && isFinite(+o.conf)) ? +o.conf : 1, verified: o.verified !== false, from_db: true };
        if (o.since) l.since = o.since;
        LINKS_.push(l);
        LINK_BY_KEY[k] = l;
        TOUCH.add(sN.id); TOUCH.add(tN.id);
        addL.push(l);
      });
    });
    ST.added_nodes = addN.length; ST.added_links = addL.length;
    return { nodes: addN, links: addL };
  }

  // ── 3. el mapa: elementos con la forma de app_main.js dentro de las selecciones vivas + UN re-asentado ────────
  function haveMap() {
    try {
      return typeof nodeSel !== 'undefined' && typeof linkSel !== 'undefined' && typeof sim !== 'undefined' &&
             !!W.d3 && !!W._mapLayers;
    } catch (e) { return false; }
  }
  function capMark(event, d) {
    var m = (W.NODE_META || {})[d.id];
    if (m && +m.mktcap_b > 0) return;
    var el = document.getElementById('hover-tooltip');
    if (!el || el.style.display === 'none' || el.querySelector('.kh-nocap')) return;
    var div = document.createElement('div');
    div.className = 'kh-nocap';
    div.style.cssText = 'font-size:10px;color:var(--ink-3);margin-top:4px';
    div.textContent = L('⚪ Sin capitalización · tamaño por defecto (sin dato)', '⚪ No market cap · default size (no data)');
    el.appendChild(div);
  }
  // Posición inicial (determinista, nunca al azar): junto a sus vecinos del catálogo (d3 ya les dio posición,
  // asentada o la inicial) o, sin vecinos, en el ancla de su categoría. Sin tamaño de mapa todavía: d3 la pone.
  function placeNew(added) {
    var nb = {};
    added.links.forEach(function (l) {
      (nb[l.source] = nb[l.source] || []).push(l.target);
      (nb[l.target] = nb[l.target] || []).push(l.source);
    });
    var NB = W.NODE_BY_ID, w = 0, h = 0;
    try { var ms = W._mapState(); w = ms.W; h = ms.H; } catch (e) {}
    added.nodes.forEach(function (n) {
      var xs = 0, ys = 0, k = 0;
      (nb[n.id] || []).forEach(function (o) {
        var m = NB[o];
        if (m && !DB_IDS.has(m.id) && isFinite(m.x) && isFinite(m.y)) { xs += m.x; ys += m.y; k++; }
      });
      var hh = hash(n.id), ang = (hh % 360) * Math.PI / 180, rad = 24 + (hh % 29);
      if (k) { n.x = xs / k + Math.cos(ang) * rad; n.y = ys / k + Math.sin(ang) * rad; }
      else if (w > 0 && h > 0) {
        var C = (typeof CATS !== 'undefined' && CATS) ? (CATS[n.cat] || CATS.aisoft) : null;
        n.x = (C && isFinite(C.x) ? C.x : 0.5) * w + Math.cos(ang) * rad;
        n.y = h / 2 + Math.sin(ang) * rad * 2;
      }
      if (isFinite(n.x)) { n.vx = 0; n.vy = 0; }
    });
  }
  function mapAppend(added) {
    if (!haveMap()) return 'no_map';
    var d3 = W.d3, layers = W._mapLayers;
    var ng = nodeSel._groups && nodeSel._groups[0], lg = linkSel._groups && linkSel._groups[0];
    if (!Array.isArray(ng) || !Array.isArray(lg)) return 'd3_internals';
    var laid = false;
    try { laid = !!(W._mapState && W._mapState().laid); } catch (e) {}
    placeNew(added);
    // vínculos (debajo de los nodos: su propia capa)
    var ls = d3.select(layers.linkLayer.node()).selectAll(null).data(added.links).enter().append('line')
      .attr('stroke-width', function (d) { return Math.max(.6, d.w * .45); })
      .style('stroke', function (d) { return getLinkColor(d.type); }).style('stroke-opacity', .22).attr('fill', 'none');
    ls.each(function () { lg.push(this); });
    // nodos: la MISMA estructura que app_main.js (anillo, núcleo, riesgo, marca IPO, etiqueta)
    var ns = d3.select(layers.nodeLayer.node()).selectAll(null).data(added.nodes).enter().append('g')
      .attr('class', 'kh-db-node').style('cursor', 'pointer');
    var R = function (d) { return computeNodeRadius(d.id); };
    var MT = W.NODE_META || {};
    ns.append('circle').attr('class', 'n-ring').attr('r', function (d) { return R(d) + 4; }).attr('fill', 'none')
      .style('stroke', function (d) { return ringStroke(d); })
      .attr('stroke-width', function (d) { return (d.preipo || d.port) ? 2.2 : 0; })
      .attr('stroke-dasharray', function (d) { return d.preipo ? '2 2.5' : d.port === 'C1+C2' ? '4 2.5' : 'none'; });
    ns.append('circle').attr('class', 'n-core').attr('r', R).attr('fill', function (d) { return nodeFill(d); })
      .attr('fill-opacity', .9).style('stroke', 'var(--surface)').attr('stroke-width', 1.5).style('transition', 'r .12s');
    ns.filter(function (d) { var r = (MT[d.id] || {}).risk; return r === 'critical' || r === 'high'; }).append('circle')
      .attr('class', function (d) { return 'risk-ring' + (MT[d.id].risk === 'critical' ? ' risk-ring-critical' : ''); })
      .attr('r', function (d) { return R(d) + 8; }).attr('fill', 'none')
      .style('stroke', function (d) { return MT[d.id].risk === 'critical' ? 'var(--danger)' : 'var(--gold)'; })
      .attr('stroke-width', 1.5).attr('stroke-dasharray', '4 3').attr('opacity', .7);
    ns.filter(function (d) { return d.preipo; }).append('text').attr('class', 'preipo-mark').text('IPO')
      .attr('text-anchor', 'middle').attr('dy', 3).style('font-size', '7px').style('font-weight', '700')
      .style('letter-spacing', '.02em').style('fill', 'var(--surface)').style('pointer-events', 'none');
    ns.filter(function (d) { return d.risk; }).append('text').attr('class', 'risk-mark').text('⚠')
      .attr('text-anchor', 'middle').attr('dy', function (d) { return -(R(d) + 8); })
      .style('font-size', '11px').style('pointer-events', 'none');
    ns.append('text').attr('class', function (d) { return 'node-label' + (d.big ? ' big' : ''); })
      .text(function (d) { return d.label.length > 15 ? d.label.slice(0, 14) + '…' : d.label; })
      .attr('text-anchor', 'middle').attr('dy', function (d) { return R(d) + 13; }).style('fill', 'var(--ink)')
      .classed('lbl-off', function (d) { return !(W._lblOn ? W._lblOn(d) : false); });
    // los MISMOS manejadores que los nodos del catálogo (clic → ficha, alt+clic → colapso, tarjeta flotante,
    // arrastre): se copian del primer nodo; si d3 cambiara su forma interna, al menos el clic abre la ficha
    var tpl = ng[0], on = tpl && tpl.__on;
    if (on && on.length) {
      on.forEach(function (o) { ns.on(o.name ? o.type + '.' + o.name : o.type, o.value, o.options); });
      ns.style('touch-action', 'none').style('-webkit-tap-highlight-color', 'rgba(0,0,0,0)');
    } else {
      ns.on('click', function (e, d) { e.stopPropagation(); if (typeof selectNode === 'function') selectNode(d.id); });
    }
    // al pasar el ratón ≥ 200 ms se piden ya los textos: al hacer clic la ficha sale completa de una vez
    var hoverT = null;
    ns.on('mouseover.khcatalog', function (e, d) {
      capMark(e, d);
      clearTimeout(hoverT);
      hoverT = setTimeout(function () { ensureDetail(d.id); }, 200);
    }).on('mouseout.khcatalog', function () { clearTimeout(hoverT); });
    ns.each(function () { ng.push(this); });
    // la simulación ve los nodos/vínculos nuevos (re-inicializa fuerzas; d3 no arranca su reloj por esto)
    try { sim.nodes(W.NODES); var lf = sim.force('link'); if (lf) lf.links(W.LINKS); } catch (e) { return 'sim:' + e.message; }
    if (laid && typeof _paintGraph === 'function') { try { _paintGraph(); } catch (e) {} }
    try { if (typeof refreshStyles === 'function') refreshStyles(); } catch (e) {}
    // radios por capitalización + etiquetas + UN re-asentado corto (o al mostrarse el mapa si está tapado), en la
    // tarea SIGUIENTE: el navegador respira entre las dos mitades (~0,1 s cada una con 400 empresas). Los datos y la
    // simulación ya quedaron coherentes arriba, en la MISMA tarea (un tick con NODES más largo que sim.nodes() daría NaN).
    setTimeout(function () {
      var t = now();
      try { if (typeof W._resizeNodesByCap === 'function') W._resizeNodesByCap(); } catch (e) {}
      ST.resize_ms = Math.round((now() - t) * 10) / 10;
    }, 0);
    return 'ok';
  }

  // Contadores de la cabecera (Empresas / Conexiones / Etapas / Pre-IPO): mismos cálculos que app_main.js al arrancar.
  // También la banda de categorías (renderBand: cuántas empresas por etapa), la caché de filtros y los grados de
  // flujo de la ficha (_deg, memo de app_main.js): sin esto la banda decía «Equipamiento 25» con 51 en el mapa.
  // `let`/`function` de nivel superior de los scripts clásicos son compartidos: se tocan sin editar app_main.js.
  function refreshCounters() {
    var N = W.NODES || [], set = function (id, v) { var el = document.getElementById(id); if (el) el.textContent = v; };
    set('m-companies', N.length);
    set('m-links', (W.LINKS || []).length);
    set('m-stages', new Set(N.map(function (n) { return n.cat; })).size);
    set('m-preipo', N.filter(function (n) { return n.preipo; }).length);
    try { if (typeof invalidateFilterCache === 'function') invalidateFilterCache(); } catch (e) {}
    try { if (typeof _deg !== 'undefined') _deg = null; } catch (e) {}
    try { if (typeof renderBand === 'function') renderBand(); } catch (e) {}
  }

  // ── 4. textos al abrir la ficha ────────────────────────────────────────────────────────────────────────────
  var TEXT_KEYS = ['role', 'role_en', 'supplies', 'supplies_en', 'moat', 'moat_en', 'growth', 'growth_en', 'desc',
                   'desc_en', 'capex_2026', 'capex_2026_en', 'backlog_status', 'backlog_status_en', 'legal_name', 'website'];
  function applyDetail(d) {
    var NB = W.NODE_BY_ID || {}, META = W.NODE_META || null;
    Object.keys(d.nodes || {}).forEach(function (id) {
      var n = NB[id], x = d.nodes[id];
      if (!n || !DB_IDS.has(n.id) || !x) return;
      TEXT_KEYS.forEach(function (k) { if (x[k] != null && x[k] !== '') n[k] = x[k]; });
      if (x.hq_city) {
        var ct = countryText(n.country_iso2, n.country);
        n.loc = x.hq_city + (ct ? ', ' + ct : '');
      }
      if (x.listing) n.listing = Object.assign({}, n.listing || {}, x.listing);
      if (META) {
        var m = META[n.id] || (META[n.id] = {});
        if (x.founded && m.founded == null) m.founded = x.founded;
        if (x.employees && m.employees == null) m.employees = x.employees;
        if (x.geo_risk && m.geo_risk == null) m.geo_risk = en() && x.geo_risk_en ? x.geo_risk_en : x.geo_risk;
      }
    });
    (d.rels || []).forEach(function (r) {
      var l = LINK_BY_KEY[key(r[0], r[1], r[2])];
      if (l && !l.rel && r[3]) l.rel = r[3];
    });
  }
  function ensureDetail(id) {
    var NB = W.NODE_BY_ID || {};
    var c = NB[id] ? NB[id].id : id;
    if (DONE[c] || !(DB_IDS.has(c) || TOUCH.has(c))) return Promise.resolve(false);
    if (INFLIGHT[c]) return INFLIGHT[c];
    INFLIGHT[c] = getJSON(DETAIL_API + '?ids=' + encodeURIComponent(c)).then(function (res) {
      delete INFLIGHT[c];
      if (res.status !== 200 || !res.body || !res.body.data) return false;
      applyDetail(res.body.data);
      DONE[c] = true;
      try {
        if (typeof selected !== 'undefined' && selected === c && typeof W.renderDetail === 'function') W.renderDetail(c);
      } catch (e) {}
      return true;
    }, function () { delete INFLIGHT[c]; return false; });
    return INFLIGHT[c];
  }
  function hookDetail() {
    var orig = W.renderDetail;
    if (typeof orig !== 'function' || orig.__khCatalog) return;
    var wrapped = function (id) {
      var r = orig.apply(this, arguments);
      try { ensureDetail(id); } catch (e) {}
      return r;
    };
    wrapped.__khCatalog = true;
    W.renderDetail = wrapped;
  }

  // ── 5. orden: pedir YA, aplicar cuando todo cargó (y nunca a mitad de un arrastre) ─────────────────────────────
  var _resolveReady;
  var ready = new Promise(function (r) { _resolveReady = r; });
  var fetched = fetchAll(0).then(function (p) { ST.fetch_ms = Math.round(now() - T0); return p; },
                                  function (e) { ST.error = String((e && e.message) || e).slice(0, 160); ST.phase = 'error'; return null; });
  function dragging() { try { return typeof _liveTick !== 'undefined' && _liveTick; } catch (e) { return false; } }
  function apply(pages, tries) {
    if (dragging() && tries < 20) { setTimeout(function () { apply(pages, tries + 1); }, 400); return; }
    var t1 = now();
    try {
      var added = applyData(pages);
      ST.data_ms = Math.round((now() - t1) * 10) / 10;
      if (added && (added.nodes.length || added.links.length)) {
        var t2 = now();
        ST.map = mapAppend(added);
        ST.map_ms = Math.round((now() - t2) * 10) / 10;
        try { if (typeof W._invalidateNRS === 'function') W._invalidateNRS(); } catch (e) {}
        try { refreshCounters(); } catch (e) {}
        // la animación de conteo de la cabecera (animateMetrics → countUp, ~1,2 s) lee su meta UNA vez y la escribe
        // en cada cuadro: si el catálogo llegó a mitad de ella, terminaba en «937». Se vuelve a escribir después.
        setTimeout(function () { try { refreshCounters(); } catch (e) {} }, 1300);
        setTimeout(function () { try { refreshCounters(); } catch (e) {} }, 2600);
        hookDetail();
        // los fundamentales en vivo que llegaron ANTES no encontraron a las empresas nuevas: se vuelven a aplicar
        try { if (W.KhipuLiveFund && W.KhipuLiveFund.status && W.KhipuLiveFund.status()) W.KhipuLiveFund.load(); } catch (e) {}
        try { W.dispatchEvent(new CustomEvent('khipu:catalogsync', { detail: status() })); } catch (e) {}
      }
      ST.phase = added ? 'done' : ST.phase;
    } catch (e) {
      ST.phase = 'error'; ST.error = String((e && e.message) || e).slice(0, 160);
      try { console.warn('catalog_sync:', e); } catch (e2) {}
    }
    ST.apply_ms = Math.round((now() - t1) * 10) / 10;
    _resolveReady(status());
  }
  function start() {
    fetched.then(function (pages) {
      if (!pages || !pages.length) { if (ST.phase === 'fetching') ST.phase = 'empty'; _resolveReady(status()); return; }
      var any = pages.some(function (d) { return (d.nodes && d.nodes.length) || (d.links && d.links.length); });
      if (!any) {
        var d0 = pages[0];
        ST.phase = 'empty'; ST.generation = d0.generation; ST.graph_version = d0.graph_version; ST.source = d0.source;
        ST.fallback = d0.fallback; ST.pages = pages.length;
        _resolveReady(status());
        return;
      }
      apply(pages, 0);
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else setTimeout(start, 0);

  function status() { return JSON.parse(JSON.stringify(ST)); }
  W.KhipuCatalogSync = {
    status: status,
    ready: ready,
    ensureDetail: ensureDetail,
    isDbNode: function (id) { var n = (W.NODE_BY_ID || {})[id]; return !!(n && DB_IDS.has(n.id)); },
    // 'live' (capitalización en vivo) · 'verified' (valuación verificada de una privada) · 'catalog' · 'none'
    capStatus: function (id) {
      var n = (W.NODE_BY_ID || {})[id], m = n ? (W.NODE_META || {})[n.id] : null;
      if (!m || !(+m.mktcap_b > 0)) return 'none';
      return m.mktcap_live ? 'live' : (m.mktcap_verified ? 'verified' : 'catalog');
    },
  };
})();
