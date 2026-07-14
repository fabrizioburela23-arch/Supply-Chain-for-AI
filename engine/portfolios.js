/* ============================================================================
   engine/portfolios.js — 🧪 CARTERAS SIMULADAS (paper trading local)

   Pedido de Fabrizio: "quita las carteras de mediano y largo plazo; que se
   puedan CREAR carteras donde pones tus empresas y sea como paper trading
   donde inviertes y pruebas". Decisión: carteras SIMULADAS 100% LOCALES —
   NO dependen de Alpaca ni de ningún broker, así es imposible que fallen en
   la demo. Todo vive en localStorage 'kh_portfolios'.

   API pública:  window.KhipuPortfolios.mount(container)
     - Renderiza la UI completa DENTRO de `container`. Idempotente (se puede
       llamar en cada apertura de pestaña; recalcula precios al montar).
     - Bilingüe ES/EN (window.LANG || localStorage 'eco_lang').

   Persistencia (localStorage 'kh_portfolios'): lista de carteras, cada una:
     { id, name, cash, startCash,
       positions:[{ nodeId, shares, avgPrice, ts }], createdAt }
   La cartera activa se recuerda en localStorage 'kh_pf_active'.

   Precios:
     - Pública con ticker (n.mkt): MKT.quotes[ticker].close (precio vivo/caché).
     - Privada/pre-IPO sin ticker: valor ESTIMADO del nodo (NODE_META.mktcap_b,
       PREIPO_INTEL.valuation o el texto de n.ticker). Se marca "valor estimado"
       y su P&L queda plano — sirve para armar la tesis, no para especular.

   Degrada con elegancia si MKT o NODES no están cargados (mensaje claro, sin
   crash). Sin dependencias externas salvo window.NODES / window.MKT.
   ============================================================================ */
(function () {
  'use strict';

  var LS_KEY = 'kh_portfolios';
  var LS_ACTIVE = 'kh_pf_active';
  var DEFAULT_CASH = 100000;

  // estado de UI (no persistido)
  var _container = null;   // nodo DOM donde vivimos
  var _buyFor = null;      // nodeId con el formulario de compra abierto
  var _search = '';        // texto del buscador
  var _creating = false;   // formulario "nueva cartera" abierto

  /* ── i18n ─────────────────────────────────────────────────────────────── */
  function lang() {
    try { return window.LANG || localStorage.getItem('eco_lang') || 'es'; }
    catch (e) { return 'es'; }
  }
  function T(es, en) { return lang() === 'en' ? en : es; }

  /* ── util ─────────────────────────────────────────────────────────────── */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[<>&"']/g, function (c) {
      return { '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function uid() {
    return 'pf_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
  }
  function num(v) { var n = parseFloat(v); return isFinite(n) ? n : NaN; }
  function money(v) {
    if (v == null || !isFinite(v)) return '—';
    return '$' + Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  function money0(v) {
    if (v == null || !isFinite(v)) return '—';
    return '$' + Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 });
  }
  function pct(v) {
    if (v == null || !isFinite(v)) return '—';
    return (v >= 0 ? '+' : '') + v.toFixed(2) + '%';
  }
  var UP = '#2BE38B', DOWN = '#FF6B85', MUTE = '#7C87A3', INK = '#E8EDFB', CY = '#00E0FF';
  function plColor(v) { return v == null || !isFinite(v) ? MUTE : v >= 0 ? UP : DOWN; }

  /* ── persistencia ─────────────────────────────────────────────────────── */
  function loadAll() {
    try {
      var raw = localStorage.getItem(LS_KEY);
      var list = raw ? JSON.parse(raw) : [];
      if (!Array.isArray(list)) list = [];
      // saneo defensivo
      return list.filter(function (p) { return p && p.id; }).map(function (p) {
        p.positions = Array.isArray(p.positions) ? p.positions : [];
        p.cash = isFinite(p.cash) ? p.cash : 0;
        p.startCash = isFinite(p.startCash) ? p.startCash : (p.cash || DEFAULT_CASH);
        return p;
      });
    } catch (e) { return []; }
  }
  function saveAll(list) {
    try { localStorage.setItem(LS_KEY, JSON.stringify(list)); } catch (e) {}
  }
  function activeId() {
    try { return localStorage.getItem(LS_ACTIVE) || ''; } catch (e) { return ''; }
  }
  function setActiveId(id) {
    try { localStorage.setItem(LS_ACTIVE, id || ''); } catch (e) {}
  }
  function activePortfolio(list) {
    list = list || loadAll();
    if (!list.length) return null;
    var id = activeId();
    var found = null;
    list.forEach(function (p) { if (p.id === id) found = p; });
    return found || list[0];
  }

  /* ── catálogo / resolución de empresas ────────────────────────────────── */
  function nodes() { return window.NODES || []; }
  function nodeById(id) {
    if (window.NODE_BY_ID && window.NODE_BY_ID[id]) return window.NODE_BY_ID[id];
    var found = null;
    nodes().forEach(function (n) { if (n && n.id === id) found = n; });
    return found;
  }

  // hasta `limit` empresas que casan con el texto. Usa KhipuResolve si existe;
  // siempre completa con un filtro simple por id/label/ticker.
  function searchNodes(q, limit) {
    limit = limit || 8;
    var out = [], seen = {};
    var push = function (n) { if (n && n.id && !seen[n.id]) { seen[n.id] = 1; out.push(n); } };
    var raw = String(q || '').trim();
    if (!raw) return [];

    // 1) el resolutor robusto (aliases, fuzzy) si está disponible
    try {
      if (window.KhipuResolve && typeof window.KhipuResolve.find === 'function') {
        var r = window.KhipuResolve.find(raw);
        if (r && r.node) push(r.node);
        (r && r.suggestions || []).forEach(push);
      }
    } catch (e) {}

    // 2) filtro directo por texto (substring en id / label / ticker / mkt)
    var nq = raw.toLowerCase();
    var arr = nodes();
    for (var i = 0; i < arr.length && out.length < limit; i++) {
      var n = arr[i]; if (!n || !n.id) continue;
      var hay = (n.id + ' ' + (n.label || '') + ' ' + (n.ticker || '') + ' ' + (n.mkt || '')).toLowerCase();
      if (hay.indexOf(nq) >= 0) push(n);
    }
    return out.slice(0, limit);
  }

  /* ── precios (públicas vivas / privadas estimadas) ────────────────────── */
  function quotes() {
    return (window.MKT && window.MKT.quotes) ? window.MKT.quotes : {};
  }
  // parsea "$400B (2025)", "~$7B", "$2T", "$500M" → valor en MILES DE MILLONES
  function valuationToB(str) {
    if (str == null) return NaN;
    var m = String(str).replace(/,/g, '').match(/([\d.]+)\s*(t|b|m)\b/i);
    if (!m) {
      var m2 = String(str).match(/([\d.]+)/);
      return m2 ? parseFloat(m2[1]) : NaN;
    }
    var v = parseFloat(m[1]); if (!isFinite(v)) return NaN;
    var u = m[2].toLowerCase();
    return u === 't' ? v * 1000 : u === 'm' ? v / 1000 : v;
  }
  // valor estimado (precio sintético estable) para una privada/pre-IPO
  function estimatedPrice(n) {
    if (!n) return NaN;
    var meta = (window.NODE_META || {})[n.id] || {};
    if (typeof meta.mktcap_b === 'number' && meta.mktcap_b > 0) return meta.mktcap_b;
    var pi = (window.PREIPO_INTEL || {})[n.id] || {};
    var b = valuationToB(pi.valuation);
    if (isFinite(b) && b > 0) return b;
    if (typeof n.mktcap === 'number' && n.mktcap > 0) return n.mktcap;
    b = valuationToB(n.ticker);           // "Pre-IPO ~$7B"
    if (isFinite(b) && b > 0) return b;
    b = valuationToB(meta.mktcap_b);       // por si viene como texto "div. IBM"
    if (isFinite(b) && b > 0) return b;
    return 10;                             // último recurso: precio simbólico
  }
  // { price, estimated, live, unavailable }
  function priceOf(n) {
    if (!n) return { price: NaN, estimated: false, live: false, unavailable: true };
    if (n.mkt) {
      var q = quotes()[n.mkt];
      if (q && isFinite(q.close) && q.close > 0) {
        return { price: q.close, estimated: false, live: !!q.live, unavailable: false };
      }
      // pública pero sin cotización cargada aún
      return { price: NaN, estimated: false, live: false, unavailable: true };
    }
    var est = estimatedPrice(n);
    return { price: est, estimated: true, live: false, unavailable: !isFinite(est) };
  }

  /* ── cálculos de cartera ──────────────────────────────────────────────── */
  function posMarket(pos) {
    var n = nodeById(pos.nodeId);
    var pr = priceOf(n);
    var cur = pr.unavailable ? pos.avgPrice : pr.price;   // sin precio → usa el de compra (P&L 0)
    var value = cur * pos.shares;
    var cost = pos.avgPrice * pos.shares;
    var pl = value - cost;
    var plPct = cost > 0 ? (pl / cost) * 100 : 0;
    return { node: n, price: cur, priceInfo: pr, value: value, cost: cost, pl: pl, plPct: plPct };
  }
  function pfStats(pf) {
    var invested = 0, value = 0;
    (pf.positions || []).forEach(function (p) {
      var m = posMarket(p); invested += m.cost; value += m.value;
    });
    var total = pf.cash + value;                       // valor total = caja + posiciones
    var pl = total - pf.startCash;                     // P&L vs. capital inicial
    var plPct = pf.startCash > 0 ? (pl / pf.startCash) * 100 : 0;
    return { invested: invested, positionsValue: value, total: total, pl: pl, plPct: plPct };
  }

  /* ── mutaciones ───────────────────────────────────────────────────────── */
  function createPortfolio(name, cash) {
    var list = loadAll();
    var c = isFinite(cash) && cash > 0 ? cash : DEFAULT_CASH;
    var pf = {
      id: uid(),
      name: (name && String(name).trim()) || (T('Cartera', 'Portfolio') + ' ' + (list.length + 1)),
      cash: c, startCash: c, positions: [], createdAt: Date.now()
    };
    list.push(pf); saveAll(list); setActiveId(pf.id);
    return pf;
  }
  function deletePortfolio(id) {
    var list = loadAll().filter(function (p) { return p.id !== id; });
    saveAll(list);
    if (activeId() === id) setActiveId(list.length ? list[0].id : '');
  }
  function renamePortfolio(id, name) {
    var list = loadAll();
    list.forEach(function (p) { if (p.id === id) p.name = String(name || '').trim() || p.name; });
    saveAll(list);
  }
  // compra por MONTO (usd) o por ACCIONES (shares). Devuelve {ok,msg}.
  function buy(pfId, nodeId, opts) {
    var list = loadAll(), pf = null;
    list.forEach(function (p) { if (p.id === pfId) pf = p; });
    if (!pf) return { ok: false, msg: T('Cartera no encontrada', 'Portfolio not found') };
    var n = nodeById(nodeId);
    if (!n) return { ok: false, msg: T('Empresa no encontrada', 'Company not found') };
    var pr = priceOf(n);
    if (pr.unavailable || !isFinite(pr.price) || pr.price <= 0)
      return { ok: false, msg: T('Precio no disponible — pulsa Actualizar', 'Price unavailable — press Refresh') };

    var shares;
    if (opts && isFinite(opts.usd) && opts.usd > 0) shares = opts.usd / pr.price;
    else if (opts && isFinite(opts.shares) && opts.shares > 0) shares = opts.shares;
    else return { ok: false, msg: T('Indica un monto o nº de acciones', 'Enter an amount or number of shares') };

    var cost = shares * pr.price;
    if (cost > pf.cash + 1e-6)
      return { ok: false, msg: T('Saldo insuficiente (caja ' + money(pf.cash) + ')', 'Not enough cash (' + money(pf.cash) + ')') };

    var existing = null;
    pf.positions.forEach(function (p) { if (p.nodeId === nodeId) existing = p; });
    if (existing) {
      var totShares = existing.shares + shares;
      existing.avgPrice = (existing.avgPrice * existing.shares + cost) / totShares;
      existing.shares = totShares;
      existing.ts = Date.now();
    } else {
      pf.positions.push({ nodeId: nodeId, shares: shares, avgPrice: pr.price, ts: Date.now() });
    }
    pf.cash -= cost;
    saveAll(list);
    return { ok: true, msg: T('Compra simulada ejecutada', 'Simulated buy executed') };
  }
  // vende `shares` (o todo si no se indica). Devuelve {ok,msg}.
  function sell(pfId, nodeId, sharesToSell) {
    var list = loadAll(), pf = null;
    list.forEach(function (p) { if (p.id === pfId) pf = p; });
    if (!pf) return { ok: false, msg: T('Cartera no encontrada', 'Portfolio not found') };
    var pos = null, idx = -1;
    pf.positions.forEach(function (p, i) { if (p.nodeId === nodeId) { pos = p; idx = i; } });
    if (!pos) return { ok: false, msg: T('No tienes esa posición', 'You do not hold that position') };
    var n = nodeById(nodeId);
    var pr = priceOf(n);
    var price = (pr.unavailable || !isFinite(pr.price)) ? pos.avgPrice : pr.price;
    var qty = isFinite(sharesToSell) && sharesToSell > 0 ? Math.min(sharesToSell, pos.shares) : pos.shares;
    var proceeds = qty * price;
    pf.cash += proceeds;
    pos.shares -= qty;
    if (pos.shares <= 1e-9) pf.positions.splice(idx, 1);
    saveAll(list);
    return { ok: true, msg: T('Venta simulada por ' + money(proceeds), 'Simulated sell for ' + money(proceeds)) };
  }

  /* ── toast local (usa el global si existe) ────────────────────────────── */
  function toast(msg) {
    try { if (typeof window.toast === 'function') { window.toast(msg); return; } } catch (e) {}
  }

  /* ── refresco de precios (públicas) ───────────────────────────────────── */
  function refreshPrices() {
    var done = false;
    try {
      if (typeof window.fetchQuotes === 'function') {
        var r = window.fetchQuotes();
        done = true;
        if (r && typeof r.then === 'function') r.then(function () { render(); }).catch(function () {});
      }
    } catch (e) {}
    // re-render inmediato con lo que haya en caché
    render();
    if (done) setTimeout(render, 1500);
  }

  /* ══════════════════════════════════════════════════════════════════════
     RENDER
     ══════════════════════════════════════════════════════════════════════ */
  function badge() {
    return '<span style="display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:700;' +
      'color:#FFB300;background:rgba(255,179,0,.10);border:1px solid rgba(255,179,0,.35);' +
      'padding:3px 9px;border-radius:20px;letter-spacing:.3px">🧪 ' + T('SIMULADO', 'SIMULATED') + '</span>';
  }

  function envError(kind) {
    var msg = kind === 'nodes'
      ? T('El catálogo de empresas aún no cargó. Espera un momento y vuelve a abrir esta pestaña.',
          'The company catalog has not loaded yet. Wait a moment and reopen this tab.')
      : T('No se pudo iniciar el módulo de carteras.', 'Could not start the portfolios module.');
    return '<div style="padding:40px 20px;text-align:center;color:' + MUTE + ';font-size:13.5px;line-height:1.6">' +
      '⏳ ' + esc(msg) + '</div>';
  }

  // barra superior: título + badge + selector de cartera + acciones
  function topBar(list, pf) {
    var opts = list.map(function (p) {
      return '<option value="' + esc(p.id) + '"' + (pf && p.id === pf.id ? ' selected' : '') + '>' + esc(p.name) + '</option>';
    }).join('');
    var selector = list.length
      ? '<select id="kpf-select" style="background:#0E1426;color:' + INK + ';border:1px solid rgba(122,158,255,.22);' +
        'border-radius:9px;padding:8px 11px;font-size:13px;font-weight:600;max-width:210px">' + opts + '</select>'
      : '';
    var actions = list.length
      ? '<button id="kpf-rename" class="kpf-btn kpf-ghost" title="' + T('Renombrar', 'Rename') + '">✎</button>' +
        '<button id="kpf-delete" class="kpf-btn kpf-ghost" title="' + T('Borrar', 'Delete') + '">🗑</button>'
      : '';
    return '<div style="display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-bottom:16px">' +
      '<div style="font-size:17px;font-weight:800;color:' + INK + ';letter-spacing:.2px">💼 ' +
        T('Carteras', 'Portfolios') + '</div>' + badge() +
      '<div style="flex:1"></div>' + selector + actions +
      '<button id="kpf-new" class="kpf-btn kpf-primary">＋ ' + T('Nueva', 'New') + '</button>' +
      '<button id="kpf-refresh" class="kpf-btn kpf-ghost" title="' + T('Actualizar precios', 'Refresh prices') + '">↻</button>' +
      '</div>';
  }

  function createForm() {
    return '<div style="border:1px solid rgba(0,224,255,.25);background:rgba(0,224,255,.04);border-radius:12px;padding:16px;margin-bottom:16px">' +
      '<div style="font-size:14px;font-weight:700;color:' + INK + ';margin-bottom:12px">＋ ' +
        T('Nueva cartera simulada', 'New simulated portfolio') + '</div>' +
      '<div style="display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end">' +
        '<label style="flex:1;min-width:160px;font-size:12px;color:' + MUTE + '">' + T('Nombre', 'Name') +
          '<input id="kpf-nn" type="text" placeholder="' + T('Mi tesis IA', 'My AI thesis') + '" ' +
          'style="width:100%;margin-top:5px;background:#0E1426;color:' + INK + ';border:1px solid rgba(122,158,255,.22);border-radius:8px;padding:9px 11px;font-size:13px"></label>' +
        '<label style="width:170px;font-size:12px;color:' + MUTE + '">' + T('Dinero virtual (USD)', 'Virtual money (USD)') +
          '<input id="kpf-nc" type="number" min="1" step="1000" value="' + DEFAULT_CASH + '" ' +
          'style="width:100%;margin-top:5px;background:#0E1426;color:' + INK + ';border:1px solid rgba(122,158,255,.22);border-radius:8px;padding:9px 11px;font-size:13px"></label>' +
        '<button id="kpf-create" class="kpf-btn kpf-primary">' + T('Crear', 'Create') + '</button>' +
        '<button id="kpf-cancel" class="kpf-btn kpf-ghost">' + T('Cancelar', 'Cancel') + '</button>' +
      '</div></div>';
  }

  function emptyState() {
    return '<div style="border:1px dashed rgba(122,158,255,.25);border-radius:14px;padding:44px 24px;text-align:center">' +
      '<div style="font-size:34px;margin-bottom:10px">🧪</div>' +
      '<div style="font-size:15px;font-weight:700;color:' + INK + ';margin-bottom:6px">' +
        T('Crea tu primera cartera simulada', 'Create your first simulated portfolio') + '</div>' +
      '<div style="font-size:13px;color:' + MUTE + ';line-height:1.6;max-width:460px;margin:0 auto 18px">' +
        T('Invierte dinero virtual en cualquiera de las ' + nodes().length + ' empresas del grafo y prueba tu tesis sin arriesgar nada real.',
          'Invest virtual money in any of the ' + nodes().length + ' companies in the graph and test your thesis risking nothing real.') + '</div>' +
      '<button id="kpf-new2" class="kpf-btn kpf-primary" style="font-size:14px;padding:11px 20px">＋ ' +
        T('Nueva cartera', 'New portfolio') + '</button></div>';
  }

  // fila de resumen (4 tarjetas)
  function summary(pf) {
    var s = pfStats(pf);
    var best = null, worst = null;
    (pf.positions || []).forEach(function (p) {
      var m = posMarket(p);
      if (best == null || m.plPct > best.plPct) best = { node: m.node, plPct: m.plPct };
      if (worst == null || m.plPct < worst.plPct) worst = { node: m.node, plPct: m.plPct };
    });
    var tile = function (label, value, color, sub) {
      return '<div style="flex:1;min-width:140px;background:rgba(20,26,44,.55);border:1px solid rgba(122,158,255,.12);' +
        'border-radius:12px;padding:13px 15px">' +
        '<div style="font-size:11px;color:' + MUTE + ';text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">' + esc(label) + '</div>' +
        '<div style="font-size:20px;font-weight:800;color:' + (color || INK) + '">' + value + '</div>' +
        (sub ? '<div style="font-size:11.5px;color:' + MUTE + ';margin-top:3px">' + sub + '</div>' : '') +
        '</div>';
    };
    var bw = '';
    if (best && worst && (pf.positions || []).length) {
      bw = '<div style="flex:1;min-width:160px;background:rgba(20,26,44,.55);border:1px solid rgba(122,158,255,.12);border-radius:12px;padding:13px 15px">' +
        '<div style="font-size:11px;color:' + MUTE + ';text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">' + T('Mejor / Peor', 'Best / Worst') + '</div>' +
        '<div style="font-size:12.5px;color:' + INK + '">▲ ' + esc(best.node ? best.node.label : '—') +
          ' <b style="color:' + UP + '">' + pct(best.plPct) + '</b></div>' +
        '<div style="font-size:12.5px;color:' + INK + ';margin-top:2px">▼ ' + esc(worst.node ? worst.node.label : '—') +
          ' <b style="color:' + DOWN + '">' + pct(worst.plPct) + '</b></div></div>';
    }
    return '<div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:16px">' +
      tile(T('Valor total', 'Total value'), money(s.total), INK,
           T('caja', 'cash') + ' ' + money(pf.cash)) +
      tile(T('Invertido', 'Invested'), money(s.invested), INK,
           T('inicial', 'start') + ' ' + money0(pf.startCash)) +
      tile('P&L', money(s.pl), plColor(s.pl), pct(s.plPct)) +
      bw + '</div>';
  }

  // buscador + resultados + formulario de compra
  function addSection(pf) {
    var results = '';
    if (_search) {
      var found = searchNodes(_search, 8);
      if (!found.length) {
        results = '<div style="padding:12px;color:' + MUTE + ';font-size:12.5px">' +
          T('Sin resultados para «' + esc(_search) + '»', 'No results for «' + esc(_search) + '»') + '</div>';
      } else {
        results = found.map(function (n) {
          var pr = priceOf(n);
          var priceTxt = pr.unavailable
            ? '<span style="color:' + MUTE + '">' + T('precio n/d', 'no price') + '</span>'
            : money(pr.price) + (pr.estimated ? ' <span style="color:#FFB300;font-size:10.5px">' + T('est.', 'est.') + '</span>' : '');
          var open = _buyFor === n.id;
          var row = '<div style="display:flex;align-items:center;gap:10px;padding:9px 11px;border-bottom:1px solid rgba(122,158,255,.08)">' +
            '<div style="flex:1;min-width:0">' +
              '<div style="font-size:13px;color:' + INK + ';font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + esc(n.label) + '</div>' +
              '<div style="font-size:11px;color:' + MUTE + '">' + esc(n.mkt || (pr.estimated ? T('privada · valor estimado', 'private · estimated value') : (n.ticker || ''))) + '</div>' +
            '</div>' +
            '<div style="font-size:13px;color:' + INK + ';font-weight:600;text-align:right;min-width:72px">' + priceTxt + '</div>' +
            '<button class="kpf-btn kpf-primary kpf-buyopen" data-id="' + esc(n.id) + '" ' + (pr.unavailable ? 'disabled style="opacity:.5"' : '') + '>' +
              (open ? T('Cerrar', 'Close') : T('Comprar', 'Buy')) + '</button>' +
            '</div>';
          if (open && !pr.unavailable) row += buyForm(n, pr);
          return row;
        }).join('');
      }
    }
    return '<div style="border:1px solid rgba(122,158,255,.14);border-radius:12px;margin-bottom:16px;overflow:hidden">' +
      '<div style="display:flex;align-items:center;gap:8px;padding:11px 13px;background:rgba(20,26,44,.4)">' +
        '<span style="font-size:15px">🔎</span>' +
        '<input id="kpf-search" type="text" value="' + esc(_search) + '" ' +
          'placeholder="' + T('Añadir empresa (nombre o ticker)…', 'Add company (name or ticker)…') + '" ' +
          'style="flex:1;background:transparent;color:' + INK + ';border:none;outline:none;font-size:13.5px" autocomplete="off">' +
        (_search ? '<button id="kpf-search-clear" class="kpf-btn kpf-ghost" style="padding:5px 9px">✕</button>' : '') +
      '</div>' + results + '</div>';
  }

  function buyForm(n, pr) {
    return '<div style="padding:12px 13px;background:rgba(0,224,255,.04);border-top:1px solid rgba(0,224,255,.15)">' +
      '<div style="display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end">' +
        '<label style="flex:1;min-width:120px;font-size:11.5px;color:' + MUTE + '">' + T('Monto (USD)', 'Amount (USD)') +
          '<input class="kpf-buy-usd" data-id="' + esc(n.id) + '" type="number" min="1" step="100" placeholder="1000" ' +
          'style="width:100%;margin-top:4px;background:#0E1426;color:' + INK + ';border:1px solid rgba(122,158,255,.22);border-radius:8px;padding:8px 10px;font-size:13px"></label>' +
        '<span style="color:' + MUTE + ';font-size:11px;padding-bottom:9px">' + T('o', 'or') + '</span>' +
        '<label style="flex:1;min-width:120px;font-size:11.5px;color:' + MUTE + '">' + T('Acciones', 'Shares') +
          '<input class="kpf-buy-sh" data-id="' + esc(n.id) + '" type="number" min="0" step="0.01" placeholder="10" ' +
          'style="width:100%;margin-top:4px;background:#0E1426;color:' + INK + ';border:1px solid rgba(122,158,255,.22);border-radius:8px;padding:8px 10px;font-size:13px"></label>' +
        '<button class="kpf-btn kpf-primary kpf-buy-go" data-id="' + esc(n.id) + '">' + T('Comprar', 'Buy') + '</button>' +
      '</div>' +
      '<div style="font-size:11px;color:' + MUTE + ';margin-top:8px">' +
        T('Precio', 'Price') + ' ' + money(pr.price) +
        (pr.estimated ? ' · <span style="color:#FFB300">' + T('privada (valor estimado)', 'private (estimated value)') + '</span>' : '') +
      '</div></div>';
  }

  // tabla de posiciones
  function positionsTable(pf) {
    var poss = pf.positions || [];
    if (!poss.length) {
      return '<div style="padding:30px 20px;text-align:center;color:' + MUTE + ';font-size:13px;border:1px solid rgba(122,158,255,.12);border-radius:12px">' +
        T('Aún no tienes posiciones. Usa el buscador de arriba para comprar tu primera empresa.',
          'No positions yet. Use the search above to buy your first company.') + '</div>';
    }
    var rows = poss.map(function (p) {
      var m = posMarket(p);
      var n = m.node;
      var estTag = m.priceInfo.estimated
        ? ' <span style="color:#FFB300;font-size:10px">🔒 ' + T('est.', 'est.') + '</span>' : '';
      return '<tr style="border-bottom:1px solid rgba(122,158,255,.08)">' +
        '<td style="padding:10px 8px"><div style="font-size:13px;color:' + INK + ';font-weight:600">' + esc(n ? n.label : p.nodeId) + estTag + '</div>' +
          '<div style="font-size:10.5px;color:' + MUTE + '">' + esc(n && n.mkt ? n.mkt : (n && n.ticker || '')) + '</div></td>' +
        '<td style="padding:10px 8px;text-align:right;font-size:12.5px;color:' + INK + ';font-variant-numeric:tabular-nums">' + fmtShares(p.shares) + '</td>' +
        '<td style="padding:10px 8px;text-align:right;font-size:12.5px;color:' + MUTE + ';font-variant-numeric:tabular-nums">' + money(p.avgPrice) + '</td>' +
        '<td style="padding:10px 8px;text-align:right;font-size:12.5px;color:' + INK + ';font-variant-numeric:tabular-nums">' + money(m.price) + '</td>' +
        '<td style="padding:10px 8px;text-align:right;font-size:12.5px;color:' + INK + ';font-variant-numeric:tabular-nums">' + money(m.value) + '</td>' +
        '<td style="padding:10px 8px;text-align:right;font-size:12.5px;font-weight:700;color:' + plColor(m.plPct) + ';font-variant-numeric:tabular-nums">' + pct(m.plPct) + '</td>' +
        '<td style="padding:10px 8px;text-align:right;white-space:nowrap">' +
          '<input class="kpf-sell-sh" data-id="' + esc(p.nodeId) + '" type="number" min="0" step="0.01" ' +
            'placeholder="' + fmtShares(p.shares) + '" style="width:66px;background:#0E1426;color:' + INK + ';border:1px solid rgba(122,158,255,.22);border-radius:7px;padding:6px 7px;font-size:12px;text-align:right">' +
          '<button class="kpf-btn kpf-sell kpf-sell-go" data-id="' + esc(p.nodeId) + '" style="margin-left:5px">' + T('Vender', 'Sell') + '</button>' +
        '</td></tr>';
    }).join('');
    var th = function (txt, right) {
      return '<th style="padding:8px;text-align:' + (right ? 'right' : 'left') + ';font-size:10.5px;color:' + MUTE + ';text-transform:uppercase;letter-spacing:.5px;font-weight:600">' + txt + '</th>';
    };
    return '<div style="overflow-x:auto;border:1px solid rgba(122,158,255,.12);border-radius:12px">' +
      '<table style="width:100%;border-collapse:collapse;min-width:640px">' +
      '<thead><tr style="background:rgba(20,26,44,.5)">' +
        th(T('Empresa', 'Company')) + th(T('Acciones', 'Shares'), 1) + th(T('P. compra', 'Buy price'), 1) +
        th(T('P. actual', 'Now'), 1) + th(T('Valor', 'Value'), 1) + th('P&L', 1) + th(T('Acción', 'Action'), 1) +
      '</tr></thead><tbody>' + rows + '</tbody></table></div>';
  }
  function fmtShares(v) {
    if (!isFinite(v)) return '0';
    if (v >= 1000) return v.toLocaleString('en-US', { maximumFractionDigits: 0 });
    if (v >= 1) return v.toLocaleString('en-US', { maximumFractionDigits: 2 });
    return v.toLocaleString('en-US', { maximumFractionDigits: 4 });
  }

  function styleTag() {
    return '<style>' +
      '.kpf-btn{cursor:pointer;border-radius:8px;font-size:12.5px;font-weight:600;padding:8px 13px;border:1px solid transparent;transition:filter .12s,background .12s;font-family:inherit}' +
      '.kpf-btn:hover{filter:brightness(1.12)}' +
      '.kpf-primary{background:linear-gradient(135deg,#00E0FF,#4A7BFF);color:#04121C}' +
      '.kpf-ghost{background:rgba(122,158,255,.08);color:#C9D4EC;border-color:rgba(122,158,255,.20)}' +
      '.kpf-sell{background:rgba(255,107,133,.12);color:#FF9DB0;border-color:rgba(255,107,133,.3)}' +
      '.kpf-btn:disabled{cursor:not-allowed}' +
      '</style>';
  }

  function render() {
    if (!_container) return;
    // entorno mínimo
    if (!nodes().length) { _container.innerHTML = styleTag() + envError('nodes'); wireEnv(); return; }

    var list = loadAll();
    var pf = activePortfolio(list);
    if (pf) setActiveId(pf.id);

    var html = styleTag() +
      '<div style="max-width:1000px;margin:0 auto;padding:20px 18px 60px">' +
      topBar(list, pf) +
      (_creating ? createForm() : '');

    if (!pf) {
      html += emptyState();
    } else {
      html += summary(pf) + addSection(pf) +
        '<div style="font-size:12.5px;color:' + MUTE + ';margin:0 0 8px;font-weight:600;text-transform:uppercase;letter-spacing:.5px">' +
          T('Posiciones', 'Positions') + '</div>' +
        positionsTable(pf) +
        '<div style="font-size:11px;color:' + MUTE + ';margin-top:14px;line-height:1.6">🧪 ' +
          T('Cartera 100% simulada con dinero virtual. No es una recomendación de inversión ni una orden real. Las privadas usan un valor estimado del grafo.',
            '100% simulated portfolio with virtual money. Not investment advice or a real order. Private companies use an estimated value from the graph.') +
        '</div>';
    }
    html += '</div>';
    _container.innerHTML = html;
    wire(pf);
  }

  /* ── wiring de eventos (tras cada render) ─────────────────────────────── */
  function $(sel) { return _container ? _container.querySelector(sel) : null; }
  function $all(sel) { return _container ? Array.prototype.slice.call(_container.querySelectorAll(sel)) : []; }

  function wireEnv() {
    // nada interactivo en el estado de error; el próximo mount reintenta
  }

  function wire(pf) {
    var el;
    // nueva cartera
    ['kpf-new', 'kpf-new2'].forEach(function (id) {
      var b = $('#' + id);
      if (b) b.onclick = function () { _creating = true; render(); };
    });
    if ((el = $('#kpf-cancel'))) el.onclick = function () { _creating = false; render(); };
    if ((el = $('#kpf-create'))) el.onclick = function () {
      var name = ($('#kpf-nn') || {}).value;
      var cash = num(($('#kpf-nc') || {}).value);
      createPortfolio(name, cash);
      _creating = false; _search = ''; _buyFor = null;
      render();
      toast(T('Cartera creada', 'Portfolio created'));
    };

    // selector / renombrar / borrar / refrescar
    var selEl = $('#kpf-select');
    if (selEl) selEl.onchange = function () { setActiveId(selEl.value); _buyFor = null; render(); };
    if ((el = $('#kpf-refresh'))) el.onclick = function () { refreshPrices(); };
    if ((el = $('#kpf-rename')) && pf) el.onclick = function () {
      var nn = window.prompt(T('Nuevo nombre de la cartera:', 'New portfolio name:'), pf.name);
      if (nn != null) { renamePortfolio(pf.id, nn); render(); }
    };
    if ((el = $('#kpf-delete')) && pf) el.onclick = function () {
      if (window.confirm(T('¿Borrar la cartera «' + pf.name + '»? Esto no se puede deshacer.',
                           'Delete portfolio «' + pf.name + '»? This cannot be undone.'))) {
        deletePortfolio(pf.id); _buyFor = null; _search = ''; render();
        toast(T('Cartera borrada', 'Portfolio deleted'));
      }
    };

    // buscador
    var searchEl = $('#kpf-search');
    if (searchEl) {
      searchEl.oninput = function () {
        _search = searchEl.value;
        // re-render con foco preservado
        var pos = searchEl.selectionStart;
        render();
        var ne = $('#kpf-search');
        if (ne) { ne.focus(); try { ne.setSelectionRange(pos, pos); } catch (e) {} }
      };
    }
    if ((el = $('#kpf-search-clear'))) el.onclick = function () { _search = ''; _buyFor = null; render(); };

    // abrir/cerrar formulario de compra
    $all('.kpf-buyopen').forEach(function (b) {
      if (b.disabled) return;
      b.onclick = function () { var id = b.getAttribute('data-id'); _buyFor = (_buyFor === id) ? null : id; render(); };
    });
    // ejecutar compra
    $all('.kpf-buy-go').forEach(function (b) {
      b.onclick = function () {
        if (!pf) return;
        var id = b.getAttribute('data-id');
        var usd = num((_container.querySelector('.kpf-buy-usd[data-id="' + cssEsc(id) + '"]') || {}).value);
        var sh = num((_container.querySelector('.kpf-buy-sh[data-id="' + cssEsc(id) + '"]') || {}).value);
        var opts = isFinite(usd) && usd > 0 ? { usd: usd } : { shares: sh };
        var res = buy(pf.id, id, opts);
        toast(res.msg);
        if (res.ok) { _buyFor = null; }
        render();
      };
    });
    // vender
    $all('.kpf-sell-go').forEach(function (b) {
      b.onclick = function () {
        if (!pf) return;
        var id = b.getAttribute('data-id');
        var sh = num((_container.querySelector('.kpf-sell-sh[data-id="' + cssEsc(id) + '"]') || {}).value);
        var res = sell(pf.id, id, isFinite(sh) && sh > 0 ? sh : undefined);
        toast(res.msg);
        render();
      };
    });
  }

  // escape mínimo para selectores por atributo (los ids del grafo son [A-Za-z0-9_])
  function cssEsc(s) { return String(s).replace(/["\\]/g, '\\$&'); }

  /* ── API pública ──────────────────────────────────────────────────────── */
  window.KhipuPortfolios = {
    mount: function (container) {
      if (typeof container === 'string') container = document.getElementById(container);
      if (!container) return;
      _container = container;
      render();
    },
    refresh: function () { render(); },
    // utilidades por si otro módulo (Bixby, KHIPU) las necesita
    _list: loadAll,
    _stats: pfStats,
    _priceOf: priceOf
  };
})();
