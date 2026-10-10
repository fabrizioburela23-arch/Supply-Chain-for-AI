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

   🤖 Asistente de carteras (pestaña interna 'Asistente'): preguntas y
   propuestas vía /api/portfolio-ai/* (core/portfolio_ai.py). "Crear esta
   cartera" guarda una cartera SIMULADA más con origin:{kind:'ai_proposal'}.

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
  // Khipus OS (2026-10-10): colores SEMÁNTICOS = tokens --os-* (claro/oscuro los pone body.dark).
  // Son colores de TEXTO con contraste AA (good-ink/bad-ink/ink-2); el valor tras la coma es el
  // respaldo oscuro por si los tokens aún no existen. Nada de colores fijos fuera de var().
  var UP = 'var(--os-good-ink,#2fbf5b)', DOWN = 'var(--os-bad-ink,#F47C7C)', MUTE = 'var(--os-ink-2,#A6A8B5)';
  function plColor(v) { return v == null || !isFinite(v) ? MUTE : v >= 0 ? UP : DOWN; }
  // el asistente de carteras es un AGENTE → su mascota de Khipus OS (KhipuMascot.of('portfolio') = Comité)
  var PF_AGENT = 'portfolio';
  function mascot(seat, size, state, fallback) {
    try {
      var M = window.KhipuMascot;
      if (M && M.svg) return M.svg((M.of && M.of(seat)) || seat, size || 18, state ? { state: state } : {});
    } catch (e) {}
    return fallback == null ? '' : fallback;
  }

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
  // Si el navegador no deja guardar (almacenamiento lleno / modo privado) se AVISA:
  // antes fallaba en silencio y la cartera "desaparecía" al recargar (2026-10-05).
  function saveAll(list) {
    try { localStorage.setItem(LS_KEY, JSON.stringify(list)); return true; }
    catch (e) {
      try {   // libera cachés desechables y reintenta una vez
        Object.keys(localStorage).forEach(function (k) { if (/^ai_analysis2_|^kh_chartcache$|^eco_quotes$/.test(k)) localStorage.removeItem(k); });
        localStorage.setItem(LS_KEY, JSON.stringify(list)); return true;
      } catch (e2) {
        var msg = T('⚠ No se pudo guardar la cartera en este navegador (almacenamiento lleno o modo privado).',
                    '⚠ Could not save the portfolio in this browser (storage full or private mode).');
        if (window.KhipuToast && window.KhipuToast.show) window.KhipuToast.show({ kind: 'error', title: msg }); else toast(msg);
        return false;
      }
    }
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
    return NaN;   // sin valuación conocida → 'no disponible' (antes: $10 inventado)
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
    // detalle para el aviso pop-up (cifras = las de esta operación simulada)
    return { ok: true, msg: T('Compra simulada ejecutada', 'Simulated buy executed'),
      side: 'buy', label: n.label, ticker: n.mkt || '', shares: shares, price: pr.price, amount: cost, pfName: pf.name };
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
    return { ok: true, msg: T('Venta simulada por ' + money(proceeds), 'Simulated sell for ' + money(proceeds)),
      side: 'sell', label: (n && n.label) || nodeId, ticker: (n && n.mkt) || '', shares: qty, price: price, amount: proceeds, pfName: pf.name };
  }

  /* ── avisos: pop-up de engine/toast.js si existe; si no, el toast global ─ */
  function toast(msg) {
    try { if (window.KhipuToast) { window.KhipuToast.show({ kind: 'info', title: msg }); return; } } catch (e) {}
    try { if (typeof window.toast === 'function') { window.toast(msg); return; } } catch (e) {}
  }
  // compra/venta en la cartera SIMULADA: insignia 🧪 SIMULADO + qué, cuánto y a qué precio
  function tradeToast(side, res) {
    var KT = window.KhipuToast;
    if (!res || !KT) { if (res) toast(res.msg); return; }
    try {
      if (!res.ok) {
        KT.show({ kind: 'error', mode: 'sim', body: res.msg,
          title: side === 'sell' ? T('La venta simulada no se hizo', 'The simulated sell did not go through')
            : T('La compra simulada no se hizo', 'The simulated buy did not go through') });
        return;
      }
      var mono = function (x) { return '<span class="kht-num">' + esc(x) + '</span>'; };
      KT.show({ kind: res.side === 'sell' ? 'sell' : 'buy', mode: 'sim',
        title: res.side === 'sell' ? T('Venta simulada ejecutada', 'Simulated sell executed') : T('Compra simulada ejecutada', 'Simulated buy executed'),
        html: mono(fmtShares(res.shares)) + ' ' + esc(T('acciones de', 'shares of')) + ' <b>' + esc(res.label) + '</b>' +
          (res.ticker ? ' ' + mono('(' + res.ticker + ')') : '') + ' @ ' + mono(money(res.price)) +
          ' · ' + esc(T('total ', 'total ')) + mono(money(res.amount)) +
          (res.pfName ? '<br>' + esc(T('Cartera: ', 'Portfolio: ')) + esc(res.pfName) : '') });
    } catch (e) { toast(res.msg); }
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
     RENDER — piel de Khipus OS (2026-10-10): tarjetas sin bordes, botones
     píldora, tokens --os-* en claro y oscuro, foco visible, y un diseño que se
     adapta al ANCHO DE LA VENTANA (container queries: los flancos del OS miden
     ~400 px; ahí la tabla de posiciones se vuelve una lista de tarjetas).
     ══════════════════════════════════════════════════════════════════════ */
  function badge() {
    return '<span class="kpf-badge">🧪 ' + T('SIMULADO', 'SIMULATED') + '</span>';
  }

  function envError(kind) {
    var msg = kind === 'nodes'
      ? T('El catálogo de empresas aún no cargó. Espera un momento y vuelve a abrir esta pestaña.',
          'The company catalog has not loaded yet. Wait a moment and reopen this tab.')
      : T('No se pudo iniciar el módulo de carteras.', 'Could not start the portfolios module.');
    return '<div class="kpf-env">⏳ ' + esc(msg) + '</div>';
  }

  // barra superior: título + badge + selector de cartera + acciones
  function topBar(list, pf) {
    var opts = list.map(function (p) {
      return '<option value="' + esc(p.id) + '"' + (pf && p.id === pf.id ? ' selected' : '') + '>' + esc(p.name) + '</option>';
    }).join('');
    var selector = list.length
      ? '<select id="kpf-select" class="kpf-in kpf-sel" aria-label="' + T('Cartera activa', 'Active portfolio') + '">' + opts + '</select>'
      : '';
    var actions = list.length
      ? '<button id="kpf-rename" class="kpf-btn kpf-ghost kpf-ico" title="' + T('Renombrar', 'Rename') + '" aria-label="' + T('Renombrar', 'Rename') + '">✎</button>' +
        '<button id="kpf-delete" class="kpf-btn kpf-ghost kpf-ico" title="' + T('Borrar', 'Delete') + '" aria-label="' + T('Borrar', 'Delete') + '">🗑</button>'
      : '';
    return '<div class="kpf-top">' +
      '<div class="kpf-title"><span class="kpf-h">💼 ' + T('Carteras', 'Portfolios') + '</span>' + badge() + '</div>' +
      '<div class="kpf-actions">' + selector + actions +
      '<button id="kpf-new" class="kpf-btn kpf-primary">＋ ' + T('Nueva', 'New') + '</button>' +
      '<button id="kpf-refresh" class="kpf-btn kpf-ghost kpf-ico" title="' + T('Actualizar precios', 'Refresh prices') + '" aria-label="' + T('Actualizar precios', 'Refresh prices') + '">↻</button>' +
      '<button id="kpf-risk" class="kpf-btn kpf-ghost" title="VaR · CVaR · Vega">📉 ' + T('Riesgo', 'Risk') + '</button>' +
      '</div></div>';
  }

  function createForm() {
    return '<div class="kpf-card kpf-newcard">' +
      '<div class="kpf-ct">＋ ' + T('Nueva cartera simulada', 'New simulated portfolio') + '</div>' +
      '<div class="kpf-row kpf-form">' +
        '<label class="kpf-lbl kpf-grow">' + T('Nombre', 'Name') +
          '<input id="kpf-nn" class="kpf-in" type="text" placeholder="' + T('Mi tesis IA', 'My AI thesis') + '"></label>' +
        '<label class="kpf-lbl kpf-cash">' + T('Dinero virtual (USD)', 'Virtual money (USD)') +
          '<input id="kpf-nc" class="kpf-in" type="number" min="1" step="1000" value="' + DEFAULT_CASH + '"></label>' +
        '<div class="kpf-row">' +
          '<button id="kpf-create" class="kpf-btn kpf-primary">' + T('Crear', 'Create') + '</button>' +
          '<button id="kpf-cancel" class="kpf-btn kpf-ghost">' + T('Cancelar', 'Cancel') + '</button>' +
        '</div>' +
      '</div></div>';
  }

  function emptyState() {
    return '<div class="kpf-card kpf-empty">' +
      '<div class="kpf-empty-ic" aria-hidden="true">🧪</div>' +
      '<div class="kpf-empty-t">' + T('Crea tu primera cartera simulada', 'Create your first simulated portfolio') + '</div>' +
      '<div class="kpf-empty-b">' +
        T('Invierte dinero virtual en cualquiera de las ' + nodes().length + ' empresas del grafo y prueba tu tesis sin arriesgar nada real.',
          'Invest virtual money in any of the ' + nodes().length + ' companies in the graph and test your thesis risking nothing real.') + '</div>' +
      '<div class="kpf-row kpf-center">' +
      '<button id="kpf-new2" class="kpf-btn kpf-primary kpf-big">＋ ' + T('Nueva cartera', 'New portfolio') + '</button>' +
      '<button class="kpf-btn kpf-ghost kpf-big kpf-tab-ai">' + mascot(PF_AGENT, 22, null, '🤖') + ' ' +
        T('Que la IA me proponga una', 'Let the AI propose one') + '</button></div></div>';
  }

  // fila de resumen (tarjetas)
  function summary(pf) {
    var s = pfStats(pf);
    var best = null, worst = null;
    (pf.positions || []).forEach(function (p) {
      var m = posMarket(p);
      if (best == null || m.plPct > best.plPct) best = { node: m.node, plPct: m.plPct };
      if (worst == null || m.plPct < worst.plPct) worst = { node: m.node, plPct: m.plPct };
    });
    var tile = function (label, value, color, sub) {
      return '<div class="kpf-stat"><div class="kpf-sl">' + esc(label) + '</div>' +
        '<div class="kpf-sv"' + (color ? ' style="color:' + color + '"' : '') + '>' + value + '</div>' +
        (sub ? '<div class="kpf-ss">' + sub + '</div>' : '') + '</div>';
    };
    var bw = '';
    if (best && worst && (pf.positions || []).length) {
      bw = '<div class="kpf-stat"><div class="kpf-sl">' + T('Mejor / Peor', 'Best / Worst') + '</div>' +
        '<div class="kpf-bwr"><span>▲ ' + esc(best.node ? best.node.label : '—') + '</span>' +
          '<b style="color:' + plColor(best.plPct) + '">' + pct(best.plPct) + '</b></div>' +
        '<div class="kpf-bwr"><span>▼ ' + esc(worst.node ? worst.node.label : '—') + '</span>' +
          '<b style="color:' + plColor(worst.plPct) + '">' + pct(worst.plPct) + '</b></div></div>';
    }
    return '<div class="kpf-sum">' +
      tile(T('Valor total', 'Total value'), money(s.total), null,
           T('caja', 'cash') + ' ' + money(pf.cash)) +
      tile(T('Invertido', 'Invested'), money(s.invested), null,
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
        results = '<div class="kpf-noresult">' +
          T('Sin resultados para «' + esc(_search) + '»', 'No results for «' + esc(_search) + '»') + '</div>';
      } else {
        results = found.map(function (n) {
          var pr = priceOf(n);
          var priceTxt = pr.unavailable
            ? '<span class="kpf-mute">' + T('precio n/d', 'no price') + '</span>'
            : money(pr.price) + (pr.estimated ? ' <span class="kpf-est">' + T('est.', 'est.') + '</span>' : '');
          var open = _buyFor === n.id;
          var row = '<div class="kpf-res">' +
            '<div class="kpf-res-n">' +
              '<div class="kpf-nm">' + esc(n.label) + '</div>' +
              '<div class="kpf-tk">' + esc(n.mkt || (pr.estimated ? T('privada · valor estimado', 'private · estimated value') : (n.ticker || ''))) + '</div>' +
            '</div>' +
            '<div class="kpf-res-p">' + priceTxt + '</div>' +
            '<button class="kpf-btn ' + (open ? 'kpf-ghost' : 'kpf-primary') + ' kpf-buyopen" data-id="' + esc(n.id) + '"' + (pr.unavailable ? ' disabled' : '') + '>' +
              (open ? T('Cerrar', 'Close') : T('Comprar', 'Buy')) + '</button>' +
            '</div>';
          if (open && !pr.unavailable) row += buyForm(n, pr);
          return row;
        }).join('');
      }
    }
    return '<div class="kpf-card kpf-add">' +
      '<div class="kpf-sbar"><span class="kpf-sic" aria-hidden="true">🔎</span>' +
        '<input id="kpf-search" class="kpf-in" type="text" value="' + esc(_search) + '" ' +
          'placeholder="' + T('Añadir empresa (nombre o ticker)…', 'Add company (name or ticker)…') + '" ' +
          'aria-label="' + T('Añadir empresa', 'Add company') + '" autocomplete="off">' +
        (_search ? '<button id="kpf-search-clear" class="kpf-btn kpf-ghost kpf-ico" title="' + T('Limpiar', 'Clear') + '" aria-label="' + T('Limpiar', 'Clear') + '">✕</button>' : '') +
      '</div>' + (results ? '<div class="kpf-results">' + results + '</div>' : '') + '</div>';
  }

  function buyForm(n, pr) {
    return '<div class="kpf-buyform">' +
      '<div class="kpf-row kpf-form">' +
        '<label class="kpf-lbl kpf-grow">' + T('Monto (USD)', 'Amount (USD)') +
          '<input class="kpf-in kpf-buy-usd" data-id="' + esc(n.id) + '" type="number" min="1" step="100" placeholder="1000"></label>' +
        '<span class="kpf-or">' + T('o', 'or') + '</span>' +
        '<label class="kpf-lbl kpf-grow">' + T('Acciones', 'Shares') +
          '<input class="kpf-in kpf-buy-sh" data-id="' + esc(n.id) + '" type="number" min="0" step="0.01" placeholder="10"></label>' +
        '<button class="kpf-btn kpf-primary kpf-buy-go" data-id="' + esc(n.id) + '">' + T('Comprar', 'Buy') + '</button>' +
      '</div>' +
      '<div class="kpf-note">' +
        T('Precio', 'Price') + ' ' + money(pr.price) +
        (pr.estimated ? ' · <span class="kpf-est">' + T('privada (valor estimado)', 'private (estimated value)') + '</span>' : '') +
      '</div></div>';
  }

  // tabla de posiciones (en una ventana angosta cada fila se vuelve una tarjeta: ver @container kpf)
  function positionsTable(pf) {
    var poss = pf.positions || [];
    if (!poss.length) {
      return '<div class="kpf-card kpf-nopos">' +
        T('Aún no tienes posiciones. Usa el buscador de arriba para comprar tu primera empresa.',
          'No positions yet. Use the search above to buy your first company.') + '</div>';
    }
    var lSh = T('Acciones', 'Shares'), lBuy = T('P. compra', 'Buy price'), lNow = T('P. actual', 'Now'), lVal = T('Valor', 'Value');
    var rows = poss.map(function (p) {
      var m = posMarket(p);
      var n = m.node;
      var estTag = m.priceInfo.estimated
        ? ' <span class="kpf-est">🔒 ' + T('est.', 'est.') + '</span>' : '';
      return '<tr>' +
        '<td class="kpf-c-co"><div class="kpf-nm">' + esc(n ? n.label : p.nodeId) + estTag + '</div>' +
          '<div class="kpf-tk">' + esc(n && n.mkt ? n.mkt : (n && n.ticker || '')) + '</div></td>' +
        '<td class="kpf-c-num" data-l="' + lSh + '">' + fmtShares(p.shares) + '</td>' +
        '<td class="kpf-c-num kpf-mute" data-l="' + lBuy + '">' + money(p.avgPrice) + '</td>' +
        '<td class="kpf-c-num" data-l="' + lNow + '">' + money(m.price) + '</td>' +
        '<td class="kpf-c-num" data-l="' + lVal + '">' + money(m.value) + '</td>' +
        '<td class="kpf-c-num kpf-c-pl" style="color:' + plColor(m.plPct) + '">' + pct(m.plPct) + '</td>' +
        '<td class="kpf-c-act">' +
          '<input class="kpf-in kpf-sell-sh" data-id="' + esc(p.nodeId) + '" type="number" min="0" step="0.01" ' +
            'placeholder="' + fmtShares(p.shares) + '" aria-label="' + T('Acciones a vender', 'Shares to sell') + '">' +
          '<button class="kpf-btn kpf-sell kpf-sell-go" data-id="' + esc(p.nodeId) + '">' + T('Vender', 'Sell') + '</button>' +
        '</td></tr>';
    }).join('');
    var th = function (txt, right) {
      return '<th' + (right ? ' class="kpf-r"' : '') + '>' + txt + '</th>';
    };
    return '<div class="kpf-tw">' +
      '<table class="kpf-pos">' +
      '<thead><tr>' +
        th(T('Empresa', 'Company')) + th(lSh, 1) + th(lBuy, 1) +
        th(lNow, 1) + th(lVal, 1) + th('P&L', 1) + th(T('Acción', 'Action'), 1) +
      '</tr></thead><tbody>' + rows + '</tbody></table></div>';
  }
  function fmtShares(v) {
    if (!isFinite(v)) return '0';
    if (v >= 1000) return v.toLocaleString('en-US', { maximumFractionDigits: 0 });
    if (v >= 1) return v.toLocaleString('en-US', { maximumFractionDigits: 2 });
    return v.toLocaleString('en-US', { maximumFractionDigits: 4 });
  }

  // El contenedor (p. ej. #portfolios-panel) toma el tema de Khipus OS: dentro de una ventana del OS
  // hereda los tokens de #bcp-ov; fuera (pestaña clásica) se marca .kos-themed para tenerlos igual.
  function hostTheme() {
    var inOS = false;
    try { inOS = !!(_container.closest && _container.closest('#bcp-ov')); } catch (e) {}
    try {
      _container.classList.add('kpf-host');
      _container.classList.toggle('kos-themed', !inOS);
      _container.classList.toggle('kpf-page', !inOS);
    } catch (e) {}
  }

  function render() {
    if (!_container) return;
    ensureCss();
    hostTheme();
    // entorno mínimo
    if (!nodes().length) { _container.innerHTML = '<div class="kpf-root"><div class="kpf-wrap">' + envError('nodes') + '</div></div>'; wireEnv(); return; }

    var list = loadAll();
    var pf = activePortfolio(list);
    if (pf) setActiveId(pf.id);

    var html = '<div class="kpf-root"><div class="kpf-wrap">' + viewTabs();

    if (_view === 'ai') {
      _container.innerHTML = html + aiView() + '</div></div>';
      wireTabs();
      wireAI();
      return;
    }
    html += topBar(list, pf) + (_creating ? createForm() : '');

    if (!pf) {
      html += emptyState();
    } else {
      html += summary(pf) + addSection(pf) +
        '<div class="kpf-sec">' + T('Posiciones', 'Positions') + '</div>' +
        positionsTable(pf) +
        '<div class="kpf-foot">🧪 ' +
          T('Cartera 100% simulada con dinero virtual. No es una recomendación de inversión ni una orden real. Las privadas usan un valor estimado del grafo.',
            '100% simulated portfolio with virtual money. Not investment advice or a real order. Private companies use an estimated value from the graph.') +
        '</div>';
    }
    html += '</div></div>';
    _container.innerHTML = html;
    wireTabs();
    wire(pf);
  }

  function wireTabs() {
    $all('.kpf-tab').forEach(function (b) {
      b.onclick = function () { if (_view === 'ai') readFormSafe(); setView(b.getAttribute('data-view')); render(); };
    });
  }

  /* ══════════════════════════════════════════════════════════════════════
     🤖 ASISTENTE DE CARTERAS (pedido: "que puedas responder preguntas y que
     te proponga carteras con AI"). Server: core/portfolio_ai.py
       POST /api/portfolio-ai/ask      → {answer, sources, answer_source}
       POST /api/portfolio-ai/propose  → {portfolios:[…], excluded, disclaimer}
       GET  /api/portfolio-ai/themes   → chips de temas (sectores del grafo)
     La construcción es DETERMINISTA (datos reales); la IA solo redacta. Crear
     una propuesta = cartera SIMULADA local (kh_portfolios). Nunca órdenes.
     ══════════════════════════════════════════════════════════════════════ */
  var LS_VIEW = 'kh_pf_view';
  var _view = (function () { try { return localStorage.getItem(LS_VIEW) === 'ai' ? 'ai' : 'pf'; } catch (e) { return 'pf'; } })();
  var _aiMode = 'propose';          // 'propose' | 'ask'
  var _chat = [];                   // [{role:'user'|'assistant', text, sources, src, error}]
  var _asking = false;
  var _askDraft = '';
  var _useMyPf = true;
  var _form = { goal: 'equilibrio', horizon: '1-3', risk: 'medio', amount: 10000, themes: [], exclude: '' };
  var _themes = null;               // [{key,label,count}] del server
  var _themesLang = '';
  var _proposing = false;
  var _proposal = null;             // respuesta de /propose
  var _propError = '';
  var _created = {};                // id de propuesta → id de cartera creada

  var THEME_FALLBACK = [
    ['semis', 'Semiconductores', 'Semiconductors'], ['cloud_ia', 'Cloud & IA', 'Cloud & AI'],
    ['infra', 'Infra física', 'Physical Infra'], ['energia', 'Energía & Nuclear', 'Energy & Nuclear'],
    ['espacio', 'Espacio', 'Space'], ['defensa', 'Defensa', 'Defense'], ['robotica', 'Robótica', 'Robotics'],
    ['materiales', 'Materiales', 'Materials'], ['logistica', 'Logística', 'Logistics'],
    ['inmobiliario', 'Inmobiliario', 'Real Estate'], ['macro_credito', 'Macro & Crédito', 'Macro & Credit']
  ];

  function setView(v) { _view = v; try { localStorage.setItem(LS_VIEW, v); } catch (e) {} }

  function registerExplainAI() {
    if (!window.explainRegister || registerExplainAI.done) return;
    registerExplainAI.done = true;
    window.explainRegister('pf_diversif', {
      es: { t: '¿Qué es el ratio de diversificación?', b: 'Compara el riesgo de cada empresa por separado con el riesgo de la cartera entera.<br><br><b>1,0</b> = no ganas nada al mezclar (todas se mueven igual). <b>1,5</b> o más = la mezcla reduce bastante los sustos porque las empresas no caen todas a la vez.<br><br>Se calcula con 1 año de precios reales.' },
      en: { t: 'What is the diversification ratio?', b: 'It compares the risk of each company on its own with the risk of the whole portfolio.<br><br><b>1.0</b> = mixing gains nothing (they all move together). <b>1.5</b> or more = the mix clearly reduces scares because the companies do not all fall at once.<br><br>Computed from 1 year of real prices.' }
    });
    window.explainRegister('pf_sizing', {
      es: { t: '¿Cómo se deciden los pesos?', b: '<b>Inversa de la volatilidad</b>: las acciones más tranquilas reciben más dinero y las más nerviosas, menos.<br><br><b>Paridad de riesgo</b>: se ajustan los pesos para que cada empresa aporte un riesgo parecido a la cartera.<br><br>En ambos casos se respetan <b>topes</b> por empresa, sector y país según el riesgo que elegiste, para no depender de una sola apuesta. Todo con 1 año de precios reales.' },
      en: { t: 'How are the weights decided?', b: '<b>Inverse volatility</b>: calmer stocks get more money and jumpier ones less.<br><br><b>Risk parity</b>: weights are tuned so each company contributes a similar amount of risk.<br><br>Both respect <b>caps</b> per company, sector and country based on the risk you chose, so you do not depend on a single bet. All from 1 year of real prices.' }
    });
  }

  function apiPost(url, body) {
    var ctl = window.AbortController ? new AbortController() : null;
    var to = ctl ? setTimeout(function () { ctl.abort(); }, 90000) : null;
    return fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(body), signal: ctl ? ctl.signal : undefined })
      .then(function (r) {
        if (to) clearTimeout(to);
        return r.json().catch(function () { return {}; }).then(function (d) { d = d || {}; d._status = r.status; return d; });
      }, function (e) {
        if (to) clearTimeout(to);
        throw e;
      });
  }
  function errText(d, e) {
    if (d && (d.error || d.error_en)) return lang() === 'en' ? (d.error_en || d.error) : (d.error || d.error_en);
    if (e && e.name === 'AbortError') return T('Tardó demasiado. Inténtalo de nuevo.', 'It took too long. Please try again.');
    return T('No se pudo conectar con el servidor.', 'Could not reach the server.');
  }

  function loadThemes() {
    if (_themes && _themesLang === lang()) return;
    _themesLang = lang();
    fetch('/api/portfolio-ai/themes?lang=' + lang()).then(function (r) { return r.json(); }).then(function (d) {
      if (d && Array.isArray(d.themes) && d.themes.length) { _themes = d.themes; if (_view === 'ai') render(); }
    }).catch(function () {});
  }
  function themeList() {
    if (_themes && _themesLang === lang()) return _themes;
    return THEME_FALLBACK.map(function (t) { return { key: t[0], label: lang() === 'en' ? t[2] : t[1] }; });
  }

  // cartera activa → posiciones para /ask
  function pfForAsk() {
    var pf = activePortfolio();
    if (!pf || !(pf.positions || []).length) return null;
    return { name: pf.name, positions: pf.positions.slice(0, 30).map(function (p) {
      var n = nodeById(p.nodeId) || {};
      return { node_id: p.nodeId, symbol: n.mkt || '', label: n.label || p.nodeId, shares: p.shares };
    }) };
  }

  function viewTabs() {
    var tab = function (id, icon, es, en) {
      var on = _view === id;
      return '<button class="kpf-tab' + (on ? ' on' : '') + '" data-view="' + id + '" aria-pressed="' + (on ? 'true' : 'false') + '">' +
        icon + '<span>' + T(es, en) + '</span></button>';
    };
    return '<div class="kpf-tabs" role="group" aria-label="' + T('Vista', 'View') + '">' + tab('pf', '💼', 'Mis carteras', 'My portfolios') +
      tab('ai', mascot(PF_AGENT, 20, null, '🤖'), 'Asistente de carteras', 'Portfolio assistant') + '</div>';
  }

  function aiView() {
    registerExplainAI();
    loadThemes();
    var mode = function (id, txt) {
      var on = _aiMode === id;
      return '<button class="kpf-mode' + (on ? ' on' : '') + '" data-mode="' + id + '" aria-pressed="' + (on ? 'true' : 'false') + '">' + txt + '</button>';
    };
    return '<div class="kpf-intro">' + mascot(PF_AGENT, 34, (_asking || _proposing) ? 'think' : null, '') + '<div>' +
        T('Te ayudo a armar carteras con datos reales de Khipus: el grafo de la cadena de suministro, precios de 1 año y el riesgo de cada empresa. Es educativo: nada se ejecuta.',
          'I help you build portfolios with real Khipus data: the supply-chain graph, 1 year of prices and each company\'s risk. It is educational: nothing is executed.') +
      '</div></div>' +
      '<div class="kpf-modes" role="group" aria-label="' + T('Qué quieres hacer', 'What do you want to do') + '">' +
        mode('propose', '✨ ' + T('Proponme una cartera', 'Propose a portfolio')) +
        mode('ask', '💬 ' + T('Hazme una pregunta', 'Ask me a question')) + '</div>' +
      (_aiMode === 'ask' ? askView() : proposeView());
  }

  /* ── 💬 preguntas ─────────────────────────────────────────────────────── */
  // respuesta del asistente = burbuja con su mascota al lado (como el chat de Khipus OS)
  function botMsg(inner, extra, state) {
    return '<div class="kpf-botrow"><span class="kpf-bav">' + mascot(PF_AGENT, 28, state, '') + '</span>' +
      '<div class="kpf-msg kpf-bot' + (extra || '') + '">' + inner + '</div></div>';
  }
  function askView() {
    var pf = pfForAsk();
    var sugg = [T('¿Qué es diversificar?', 'What does diversifying mean?'),
                T('¿Nvidia y AMD se mueven juntas?', 'Do Nvidia and AMD move together?'),
                T('Quiero algo menos riesgoso', 'I want something less risky')];
    if (pf) sugg.push(T('¿Qué riesgo tiene mi cartera?', 'How risky is my portfolio?'));
    var msgs = _chat.map(function (m) {
      if (m.role === 'user') return '<div class="kpf-msg kpf-me">' + esc(m.text) + '</div>';
      var src = (m.sources || []).map(function (s) { return '<span class="kpf-src">' + esc(s.label) + '</span>'; }).join('');
      var tag = m.error ? '' : (m.src === 'ai'
        ? '<span class="kpf-src kpf-src-ai">' + T('IA', 'AI') + '</span>'
        : '<span class="kpf-src kpf-src-auto">' + T('sin IA', 'no AI') + '</span>');
      return botMsg(esc(m.text).replace(/\n/g, '<br>') +
        (m.error ? '' : '<div class="kpf-srcs">' + tag + src + '</div>'), m.error ? ' kpf-err' : '');
    }).join('');
    if (_asking) msgs += botMsg(T('Pensando con los datos de Khipus…', 'Thinking with Khipus data…'), ' kpf-thinking', 'think');
    if (!msgs) msgs = '<div class="kpf-note kpf-chat-empty">' +
      T('Pregunta lo que quieras sobre carteras, empresas del grafo, diversificación o riesgo. Ejemplos:', 'Ask anything about portfolios, graph companies, diversification or risk. Examples:') + '</div>';
    return '<div class="kpf-card">' +
      '<div id="kpf-chat" class="kpf-chat" aria-live="polite">' + msgs + '</div>' +
      '<div class="kpf-chips kpf-suggs">' + sugg.map(function (s) {
        return '<button class="kpf-chip kpf-sugg" data-q="' + esc(s) + '"' + (_asking ? ' disabled' : '') + '>' + esc(s) + '</button>';
      }).join('') + '</div>' +
      (pf ? '<label class="kpf-check">' +
        '<input id="kpf-usepf" type="checkbox"' + (_useMyPf ? ' checked' : '') + '>' +
        T('Usar mi cartera «' + esc(pf.name) + '» para responder', 'Use my portfolio «' + esc(pf.name) + '» to answer') + '</label>' : '') +
      '<div class="kpf-askrow">' +
        '<input id="kpf-ask" type="text" maxlength="800" value="' + esc(_askDraft) + '" placeholder="' +
          T('Escribe tu pregunta…', 'Type your question…') + '" aria-label="' + T('Tu pregunta', 'Your question') + '" class="kpf-input kpf-in" autocomplete="off">' +
        '<button id="kpf-ask-go" class="kpf-btn kpf-primary kpf-big"' + (_asking ? ' disabled' : '') + '>' + T('Preguntar', 'Ask') + '</button>' +
      '</div>' +
      '<div class="kpf-foot">ℹ️ ' +
        T('Respuestas educativas con datos de Khipus. No es asesoría personalizada ni promete rendimientos.',
          'Educational answers with Khipus data. Not personalized advice and no promise of returns.') + '</div>' +
      '</div>';
  }

  function sendAsk(q) {
    q = String(q || '').trim();
    if (!q || _asking) return;
    var history = _chat.filter(function (m) { return !m.error; }).slice(-6).map(function (m) { return { role: m.role, text: m.text }; });
    _chat.push({ role: 'user', text: q });
    _asking = true; _askDraft = '';
    render();
    var body = { question: q, lang: lang(), history: history };
    var pf = _useMyPf ? pfForAsk() : null;
    if (pf) body.portfolio = pf;
    apiPost('/api/portfolio-ai/ask', body).then(function (d) {
      if (d._status >= 400 || !d.answer) _chat.push({ role: 'assistant', text: errText(d), error: true });
      else _chat.push({ role: 'assistant', text: d.answer, sources: d.sources, src: d.answer_source });
    }, function (e) {
      _chat.push({ role: 'assistant', text: errText(null, e), error: true });
    }).then(function () {
      _asking = false; render();
      var c = $('#kpf-chat'); if (c) c.scrollTop = c.scrollHeight;
    });
  }

  /* ── ✨ propuesta ─────────────────────────────────────────────────────── */
  function optGroup(name, value, opts) {
    return '<div class="kpf-opts">' + opts.map(function (o) {
      var on = value === o[0];
      return '<button class="kpf-opt' + (on ? ' on' : '') + '" data-f="' + name + '" data-v="' + o[0] + '" aria-pressed="' + (on ? 'true' : 'false') + '">' +
        '<b>' + o[1] + '</b>' + (o[2] ? '<span>' + o[2] + '</span>' : '') + '</button>';
    }).join('') + '</div>';
  }
  function fieldLabel(n, txt) {
    return '<div class="kpf-flabel"><span class="kpf-num">' + n + '</span>' + txt + '</div>';
  }

  function proposeView() {
    var f = _form;
    var html = '<div class="kpf-card">' +
      fieldLabel(1, T('¿Qué buscas?', 'What are you looking for?')) +
      optGroup('goal', f.goal, [
        ['crecimiento', '🌱 ' + T('Crecimiento', 'Growth'), T('Que crezca más, aceptando sustos', 'Grow more, accepting scares')],
        ['equilibrio', '⚖️ ' + T('Equilibrio', 'Balanced'), T('Un punto medio', 'A middle ground')],
        ['defensivo', '🛡 ' + T('Defensivo', 'Defensive'), T('Proteger antes que ganar', 'Protect before gaining')]]) +
      fieldLabel(2, T('¿Por cuánto tiempo?', 'For how long?')) +
      optGroup('horizon', f.horizon, [['lt1', T('Menos de 1 año', 'Under 1 year')], ['1-3', T('1 a 3 años', '1 to 3 years')],
                                      ['3+', T('Más de 3 años', 'Over 3 years')]]) +
      fieldLabel(3, T('¿Cuánto riesgo toleras?', 'How much risk can you take?')) +
      optGroup('risk', f.risk, [['bajo', '🟢 ' + T('Bajo', 'Low'), T('Más empresas, topes estrictos', 'More names, strict caps')],
                                ['medio', '🟡 ' + T('Medio', 'Medium')],
                                ['alto', '🔴 ' + T('Alto', 'High'), T('Menos empresas, más concentración', 'Fewer names, more concentration')]]) +
      fieldLabel(4, T('¿Cuánto dinero (virtual)?', 'How much (virtual) money?')) +
      '<div class="kpf-amt"><span class="kpf-mute">$</span>' +
        '<input id="kpf-amt" type="number" min="100" max="10000000" step="1000" value="' + esc(f.amount) + '" class="kpf-input kpf-in" aria-label="' + T('Monto en dólares', 'Amount in dollars') + '">' +
        '<span class="kpf-mute kpf-small">USD</span></div>' +
      fieldLabel(5, T('Temas (opcional)', 'Themes (optional)') + ' <span class="kpf-flsub">' +
        T('— sin elegir = todos', '— none = all') + '</span>') +
      '<div class="kpf-chips">' + themeList().map(function (t) {
        var on = f.themes.indexOf(t.key) >= 0;
        return '<button class="kpf-chip kpf-theme' + (on ? ' on' : '') + '" data-k="' + esc(t.key) + '" aria-pressed="' + (on ? 'true' : 'false') + '">' + (on ? '✓ ' : '') + esc(t.label) +
          (t.count ? ' <span class="kpf-cnt">' + t.count + '</span>' : '') + '</button>';
      }).join('') + '</div>' +
      fieldLabel(6, T('Excluir (opcional)', 'Exclude (optional)')) +
      '<input id="kpf-excl" type="text" maxlength="400" value="' + esc(f.exclude) + '" class="kpf-input kpf-in kpf-full kpf-mb" placeholder="' +
        T('ej.: China, Tesla, energía', 'e.g.: China, Tesla, energy') + '" aria-label="' + T('Excluir', 'Exclude') + '">' +
      '<button id="kpf-prop-go" class="kpf-btn kpf-primary kpf-big kpf-full"' + (_proposing ? ' disabled' : '') + '>' +
        (_proposing ? mascot(PF_AGENT, 22, 'think', '⏳') + ' ' + T('Calculando con 1 año de precios reales…', 'Computing with 1 year of real prices…')
                    : '✨ ' + T('Proponme carteras', 'Propose portfolios')) + '</button>' +
      (_proposing ? '<div class="kpf-note kpf-tc">' +
        T('Puede tardar unos 20-40 segundos.', 'It may take about 20-40 seconds.') + '</div>' : '') +
      '</div>';
    if (_propError) html += '<div class="kpf-card kpf-err kpf-mt">⚠️ ' + esc(_propError) + excludedBlock(_proposal) + '</div>';
    if (_proposal && _proposal.portfolios && _proposal.portfolios.length) html += proposalResults(_proposal);
    return html;
  }

  function reasonOf(e) { return lang() === 'en' ? (e.reason_en || e.reason) : e.reason; }
  function excludedBlock(d) {
    var ex = (d && d.excluded) || [];
    if (!ex.length) return '';
    return '<details class="kpf-details"><summary>' +
      T('Qué quedó fuera y por qué', 'What was left out and why') + ' (' + ex.length + ')</summary>' +
      '<ul>' + ex.slice(0, 40).map(function (e) {
        return '<li>' + esc(e.label) + (e.symbol ? ' (' + esc(e.symbol) + ')' : '') + ' — ' + esc(reasonOf(e)) + '</li>';
      }).join('') + '</ul></details>';
  }

  function metricTile(label, value, key, sub) {
    var chip = (key && window.explainChip) ? window.explainChip(key) : '';
    return '<div class="kpf-tile"><div class="kpf-tl">' + label + chip + '</div><div class="kpf-tv">' + value + '</div>' +
      (sub ? '<div class="kpf-ts">' + sub + '</div>' : '') + '</div>';
  }

  function proposalResults(d) {
    var en = lang() === 'en';
    var disc = en ? (d.disclaimer_en || d.disclaimer) : (d.disclaimer_es || d.disclaimer);
    var html = '<div class="kpf-disc">⚠️ ' + esc(disc) + '</div>';
    d.portfolios.forEach(function (pf, i) {
      var m = pf.metrics || {};
      var name = en ? (pf.name_en || pf.name) : (pf.name_es || pf.name);
      var method = pf.method === 'risk_parity' ? T('paridad de riesgo', 'risk parity') : T('inversa de la volatilidad', 'inverse volatility');
      var risks = (en ? pf.risks_en : pf.risks_es) || pf.risks || [];
      var rows = (pf.positions || []).map(function (p) {
        var w = (p.weight * 100);
        return '<tr><td><div class="kpf-nm">' + esc(p.label) + '</div>' +
            '<div class="kpf-tk">' + esc(p.symbol) + ' · ' + esc(p.sector_label || p.sector) + ' · ' + esc(p.country) + '</div></td>' +
          '<td class="kpf-wcell"><div class="kpf-wrow"><div class="kpf-wbar"><i style="width:' + Math.min(100, w / 0.25).toFixed(1) + '%"></i></div>' +
            '<b>' + w.toFixed(1) + '%</b></div></td>' +
          '<td class="kpf-r">' + money0(p.usd) + '</td>' +
          '<td class="kpf-hide-sm kpf-r kpf-mute">' + money(p.price) + '</td>' +
          '<td class="kpf-hide-sm kpf-r kpf-mute">' + (p.vol_ann_pct != null ? p.vol_ann_pct.toFixed(0) + '%' : '—') + '</td></tr>';
      }).join('');
      var srcTag = pf.rationale_source === 'ai'
        ? '<span class="kpf-src kpf-src-ai">' + T('redactado por IA', 'written by AI') + '</span>'
        : '<span class="kpf-src kpf-src-auto">' + T('sin IA — texto automático', 'no AI — automatic text') + '</span>';
      var created = _created[pf.id];
      html += '<div class="kpf-card kpf-prop kpf-mt">' +
        '<div class="kpf-prop-h">' +
          '<div class="kpf-prop-n">' + (i + 1) + '. ' + esc(name) + '</div>' +
          '<span class="kpf-src">' + esc(method) + (window.explainChip ? window.explainChip('pf_sizing') : '') + '</span>' +
        '</div>' +
        '<div class="kpf-tiles">' +
          metricTile(T('Volatilidad anual', 'Annual volatility'), (m.vol_ann_pct != null ? m.vol_ann_pct.toFixed(1) + '%' : '—'), 'vol_ann') +
          metricTile(T('Mal día (VaR 95%)', 'Bad day (VaR 95%)'), money0(m.var95_1d_usd), 'var', T('pérdida en 1 día, 1 de cada 20', '1-day loss, 1 in 20')) +
          metricTile(T('Peor caída (1 año)', 'Worst drop (1 year)'), (m.max_drawdown_pct != null ? m.max_drawdown_pct.toFixed(1) + '%' : '—'), 'drawdown') +
          metricTile(T('Diversificación', 'Diversification'), (m.diversification_ratio != null ? m.diversification_ratio.toFixed(2) : '—'), 'pf_diversif',
            m.n_names + ' ' + T('empresas', 'companies') + ' · ' + m.n_sectors + ' ' + T('sectores', 'sectors') + ' · ' + m.n_countries + ' ' + T('países', 'countries')) +
        '</div>' +
        '<div class="kpf-tw2"><table class="kpf-ptable"><thead><tr>' +
          '<th>' + T('Empresa', 'Company') + '</th><th>' + T('Peso', 'Weight') + '</th><th class="kpf-r">USD</th>' +
          '<th class="kpf-hide-sm kpf-r">' + T('Precio', 'Price') + '</th><th class="kpf-hide-sm kpf-r">' + T('Vol.', 'Vol.') + '</th>' +
        '</tr></thead><tbody>' + rows + '</tbody></table></div>' +
        '<div class="kpf-ct kpf-ct-sm">💡 ' + T('Por qué esta cartera', 'Why this portfolio') + ' ' + srcTag + '</div>' +
        '<div class="kpf-p">' + esc(pf.rationale || '').replace(/\n/g, '<br>') + '</div>' +
        '<div class="kpf-ct kpf-ct-sm">⚠️ ' + T('Riesgos principales', 'Main risks') + '</div>' +
        '<ul class="kpf-list">' +
          risks.map(function (r) { return '<li>' + esc(r) + '</li>'; }).join('') + '</ul>' +
        ((pf.notes || []).length ? '<div class="kpf-warnnote">' + pf.notes.map(function (n) { return esc(en ? n.en : n.es); }).join('<br>') + '</div>' : '') +
        '<div class="kpf-note kpf-mb">' +
          T('Precios de cierre del ', 'Closing prices as of ') + esc(m.as_of || '') + ' · ' + T('historia desde ', 'history since ') + esc(m.from || '') +
          ' (' + (m.days || 0) + ' ' + T('días', 'days') + ') · Yahoo Finance</div>' +
        '<div class="kpf-row">' +
          (created
            ? '<button class="kpf-btn kpf-ghost kpf-big kpf-goto" data-pf="' + esc(created) + '">✓ ' + T('Creada — ver en Mis carteras', 'Created — see in My portfolios') + '</button>' +
              (window.KhipuRisk ? '<button class="kpf-btn kpf-ghost kpf-big kpf-riskgo" data-pf="' + esc(created) + '">📉 ' + T('Analizar riesgo', 'Analyze risk') + '</button>' : '')
            : '<button class="kpf-btn kpf-primary kpf-big kpf-create" data-i="' + i + '">➕ ' + T('Crear esta cartera (simulada)', 'Create this portfolio (simulated)') + '</button>') +
        '</div></div>';
    });
    html += '<div class="kpf-card kpf-mt">' +
      '<div class="kpf-note kpf-nomt">' +
        T('Cómo se armó: empresas cotizadas del grafo filtradas por tus temas, ordenadas por riesgo (NRS), tamaño, papel en la cadena de suministro y la postura de los agentes de investigación; con topes por empresa/sector/país según tu riesgo y pesos calculados con 1 año de precios reales.',
          'How it was built: listed companies from the graph filtered by your themes, ranked by risk (NRS), size, role in the supply chain and the research agents\' stance; with caps per company/sector/country based on your risk and weights computed from 1 year of real prices.') +
        (window.explainChip ? window.explainChip('nrs') : '') + '</div>' + excludedBlock(d) + '</div>';
    return html;
  }

  function readForm() {
    var a = num(($('#kpf-amt') || {}).value);
    if (isFinite(a)) _form.amount = a;
    var ex = $('#kpf-excl');
    if (ex) _form.exclude = ex.value;
  }

  function sendPropose() {
    readForm();
    if (!isFinite(_form.amount) || _form.amount < 100 || _form.amount > 10000000) {
      _propError = T('El monto debe estar entre $100 y $10.000.000.', 'The amount must be between $100 and $10,000,000.');
      _proposal = null; render(); return;
    }
    _proposing = true; _propError = ''; _proposal = null; _created = {};
    render();
    apiPost('/api/portfolio-ai/propose', {
      goal: _form.goal, horizon: _form.horizon, risk: _form.risk, amount_usd: _form.amount,
      themes: _form.themes, exclude: _form.exclude, lang: lang()
    }).then(function (d) {
      if (d._status >= 400 || !d.portfolios || !d.portfolios.length) { _propError = errText(d); _proposal = d; }
      else _proposal = d;
    }, function (e) { _propError = errText(null, e); }).then(function () {
      _proposing = false; render();
      var first = $('.kpf-disc'); if (first && first.scrollIntoView) try { first.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch (e) {}
    });
  }

  // "Crear esta cartera": cartera SIMULADA local; acciones = monto / precio actual.
  // Precio: el mismo que usa Carteras (MKT.quotes, USD) y, si no está cargado,
  // el cierre real que devolvió el server. Nunca se envía ninguna orden.
  function createFromProposal(idx) {
    var pfp = _proposal && _proposal.portfolios && _proposal.portfolios[idx];
    if (!pfp) return;
    var amount = (pfp.metrics && pfp.metrics.amount_usd) || _form.amount;
    var list = loadAll();
    var name = '🤖 ' + (lang() === 'en' ? (pfp.name_en || pfp.name) : (pfp.name_es || pfp.name));
    var pf = { id: uid(), name: name, cash: amount, startCash: amount, positions: [], createdAt: Date.now(),
               origin: { kind: 'ai_proposal', method: pfp.method, as_of: _proposal.as_of } };
    var skipped = [];
    (pfp.positions || []).forEach(function (p) {
      var n = nodeById(p.node_id);
      var pr = priceOf(n);
      var price = (!pr.unavailable && isFinite(pr.price) && pr.price > 0) ? pr.price : p.price;
      if (!n || !isFinite(price) || price <= 0 || !(p.usd > 0) || p.usd > pf.cash + 1e-6) { skipped.push(p.label); return; }
      pf.positions.push({ nodeId: p.node_id, shares: p.usd / price, avgPrice: price, ts: Date.now() });
      pf.cash -= p.usd;
    });
    if (pf.cash < 0.005) pf.cash = 0;
    list.push(pf); saveAll(list); setActiveId(pf.id);
    _created[pfp.id] = pf.id;
    toast(T('Cartera simulada creada: ', 'Simulated portfolio created: ') + name +
          (skipped.length ? T(' (sin precio: ', ' (no price: ') + skipped.join(', ') + ')' : ''));
    setView('pf'); _search = ''; _buyFor = null;
    render();
  }

  /* ── estilos (una sola vez en <head>) — SOLO tokens de Khipus OS ─────────
     Dentro de una ventana del OS: fondo = --os-surface y tarjetas = --os-surface-2
     (como las ventanas nativas). En la pestaña clásica (.kpf-page): fondo =
     --os-bg y tarjetas = --os-surface con sombra (como el comité). */
  var CSS_PF = '' +
    '.kpf-host{background:var(--os-surface,#17181F)!important;color:var(--os-ink,#F2F2F5)}' +
    '.kpf-host.kpf-page{background:var(--os-bg,#0E0F14)!important}' +
    '.kpf-root{container:kpf/inline-size;color:var(--os-ink,#F2F2F5);font-family:var(--os-font,\'Nunito\',\'Geist\',system-ui,-apple-system,\'Segoe UI\',sans-serif);' +
      'font-size:14px;line-height:1.5;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;' +
      '--kpf-card:var(--os-surface-2,#1F2029);--kpf-field:var(--os-surface,#17181F);--kpf-hover:var(--os-surface-3,#2A2B36);--kpf-seg:var(--os-surface-2,#1F2029);--kpf-cshadow:none}' +
    '.kpf-page .kpf-root{--kpf-card:var(--os-surface,#17181F);--kpf-field:var(--os-surface-2,#1F2029);--kpf-seg:var(--os-surface-3,#2A2B36);' +
      '--kpf-cshadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35))}' +
    '.kpf-wrap{max-width:1000px;margin:0 auto;padding:16px 16px 48px;box-sizing:border-box}' +
    '.kpf-root *{box-sizing:border-box}' +
    '.kpf-root button,.kpf-root input,.kpf-root select{font-family:inherit}' +
    // «?» de explainChip: trae un cian fijo en línea (1,3-1,6:1 sobre fondo claro) → acento del tema
    '.kpf-root span[onclick*="explainMetric"]{color:var(--os-accent,#4C8DF6)!important;border-color:color-mix(in srgb,var(--os-accent,#4C8DF6) 45%,transparent)!important}' +
    // foco de teclado VISIBLE (WCAG 2.4.7)
    '.kpf-root button:focus-visible,.kpf-root select:focus-visible,.kpf-root summary:focus-visible,.kpf-root input[type=checkbox]:focus-visible{outline:2px solid var(--os-accent,#4C8DF6);outline-offset:2px}' +
    // botones = píldoras
    '.kpf-btn{appearance:none;-webkit-appearance:none;border:0;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:6px;' +
      'height:36px;padding:0 15px;border-radius:999px;font-size:13px;font-weight:700;letter-spacing:-.005em;white-space:nowrap;line-height:1;' +
      'transition:background-color .15s,opacity .15s,transform .1s}' +
    '.kpf-btn:active{transform:scale(.98)}' +
    '.kpf-btn:disabled{opacity:.45;cursor:not-allowed;transform:none}' +
    '.kpf-primary{background:var(--os-btn,#F2F2F5);color:var(--os-btn-ink,#111216)}' +
    '.kpf-primary:hover:not(:disabled){opacity:.88}' +
    '.kpf-ghost{background:var(--kpf-card);color:var(--os-ink,#F2F2F5);font-weight:600;box-shadow:var(--kpf-cshadow)}' +
    '.kpf-card .kpf-ghost{background:var(--kpf-field);box-shadow:none}' +
    '.kpf-ghost:hover:not(:disabled){background:var(--kpf-hover)}' +
    '.kpf-ico{width:36px;padding:0;font-size:14px}' +
    '.kpf-sell{color:var(--os-bad-ink,#F47C7C);background:var(--os-surface-2,#1F2029);background:color-mix(in srgb,var(--os-bad,#f06565) 13%,transparent)}' +
    '.kpf-sell:hover:not(:disabled){background:color-mix(in srgb,var(--os-bad,#f06565) 20%,transparent)}' +
    '.kpf-big{height:44px;padding:0 20px;font-size:14px}' +
    '.kpf-full{width:100%}.kpf-mt{margin-top:14px}.kpf-mb{margin-bottom:16px}.kpf-tc{text-align:center}.kpf-nomt{margin-top:0}' +
    // campos: sin borde, fondo suave, anillo de foco
    '.kpf-in{height:40px;border:0;border-radius:var(--os-r-sm,12px);padding:0 12px;font-size:14px;color:var(--os-ink,#F2F2F5);background:var(--kpf-field);' +
      'box-shadow:inset 0 0 0 1px var(--os-line,rgba(255,255,255,.07));outline:none;min-width:0;max-width:100%;transition:box-shadow .15s}' +
    '.kpf-in::placeholder{color:var(--os-ink-2,#A6A8B5);opacity:.85}' +
    '.kpf-in:focus{box-shadow:inset 0 0 0 1.5px var(--os-accent,#4C8DF6),0 0 0 3px var(--kos-accent-soft,rgba(76,141,246,.16))}' +
    'select.kpf-in{cursor:pointer;padding-right:8px}' +
    'input[type=number].kpf-in{font-variant-numeric:tabular-nums}' +
    '.kpf-top .kpf-in{background:var(--kpf-card)}' +
    // barra superior
    '.kpf-top{display:flex;flex-wrap:wrap;align-items:center;gap:10px 12px;margin-bottom:16px}' +
    '.kpf-title{display:flex;align-items:center;gap:10px;flex:1 1 auto;min-width:0}' +
    '.kpf-h{font-size:18px;font-weight:800;letter-spacing:-.015em;color:var(--os-ink,#F2F2F5);white-space:nowrap}' +
    '.kpf-actions{display:flex;flex-wrap:wrap;align-items:center;gap:8px}' +
    '.kpf-sel{height:36px;max-width:220px;font-size:13px;font-weight:700}' +
    '.kpf-badge{display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:800;letter-spacing:.04em;padding:4px 10px;border-radius:999px;white-space:nowrap;' +
      'color:var(--os-warn-ink,#F2C46D);background:var(--os-surface-2,#1F2029);background:color-mix(in srgb,var(--os-warn,#F2C46D) 18%,transparent)}' +
    // tarjetas: superficie, radio 18, sin bordes
    '.kpf-card{background:var(--kpf-card);border-radius:var(--os-r,18px);box-shadow:var(--kpf-cshadow);padding:16px;min-width:0}' +
    '.kpf-ct{display:flex;align-items:center;flex-wrap:wrap;gap:8px;font-size:14px;font-weight:800;color:var(--os-ink,#F2F2F5);margin-bottom:12px}' +
    '.kpf-ct-sm{font-size:13px;margin-bottom:6px}' +
    '.kpf-row{display:flex;flex-wrap:wrap;gap:10px;align-items:center}' +
    '.kpf-form{align-items:flex-end}' +
    '.kpf-center{justify-content:center}' +
    '.kpf-lbl{display:flex;flex-direction:column;gap:6px;font-size:12px;font-weight:600;color:var(--os-ink-2,#A6A8B5)}' +
    '.kpf-lbl .kpf-in{width:100%}' +
    '.kpf-grow{flex:1 1 150px;min-width:0}.kpf-cash{flex:0 1 180px;min-width:130px}' +
    '.kpf-newcard{margin-bottom:16px}' +
    '.kpf-env{padding:40px 20px;text-align:center;color:var(--os-ink-2,#A6A8B5);font-size:13.5px;line-height:1.6}' +
    '.kpf-empty{text-align:center;padding:34px 20px}' +
    '.kpf-empty-ic{font-size:34px;margin-bottom:10px}' +
    '.kpf-empty-t{font-size:16px;font-weight:800;color:var(--os-ink,#F2F2F5);margin-bottom:6px}' +
    '.kpf-empty-b{font-size:13.5px;color:var(--os-ink-2,#A6A8B5);line-height:1.6;max-width:460px;margin:0 auto 18px}' +
    // resumen
    '.kpf-sum{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:16px}' +
    '.kpf-stat{background:var(--kpf-card);border-radius:var(--os-r,18px);box-shadow:var(--kpf-cshadow);padding:13px 15px;min-width:0}' +
    '.kpf-sl{font-size:12px;font-weight:700;color:var(--os-ink-2,#A6A8B5);margin-bottom:5px}' +
    '.kpf-sv{font-size:21px;font-weight:800;letter-spacing:-.02em;color:var(--os-ink,#F2F2F5);font-variant-numeric:tabular-nums;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.kpf-ss{font-size:12px;color:var(--os-ink-2,#A6A8B5);margin-top:3px;font-variant-numeric:tabular-nums}' +
    '.kpf-bwr{display:flex;justify-content:space-between;align-items:baseline;gap:8px;font-size:13px;color:var(--os-ink,#F2F2F5);margin-top:4px}' +
    '.kpf-bwr span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
    '.kpf-bwr b{font-variant-numeric:tabular-nums;white-space:nowrap}' +
    // buscador + resultados + compra
    '.kpf-add{padding:0;margin-bottom:16px;overflow:hidden}' +
    '.kpf-sbar{display:flex;align-items:center;gap:8px;padding:7px 8px 7px 14px;border-radius:var(--os-r,18px)}' +
    '.kpf-sbar:focus-within{box-shadow:inset 0 0 0 2px var(--os-accent,#4C8DF6)}' +
    '.kpf-sbar .kpf-in{flex:1;background:transparent;box-shadow:none;height:38px;padding:0 4px}' +
    '.kpf-sic{font-size:15px}' +
    '.kpf-results{border-top:1px solid var(--os-line,rgba(255,255,255,.07))}' +
    '.kpf-res{display:flex;align-items:center;gap:10px;padding:10px 14px;border-bottom:1px solid var(--os-line,rgba(255,255,255,.07))}' +
    '.kpf-results>.kpf-res:last-child{border-bottom:0}' +
    '.kpf-res-n{flex:1;min-width:0}' +
    '.kpf-nm{font-size:13.5px;font-weight:700;color:var(--os-ink,#F2F2F5);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.kpf-tk{font-size:11.5px;color:var(--os-ink-2,#A6A8B5);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.kpf-res-p{font-size:13px;font-weight:700;text-align:right;min-width:72px;font-variant-numeric:tabular-nums;color:var(--os-ink,#F2F2F5)}' +
    '.kpf-est{color:var(--os-warn-ink,#F2C46D);font-size:10.5px;font-weight:700}' +
    '.kpf-mute{color:var(--os-ink-2,#A6A8B5)}.kpf-small{font-size:12px}' +
    '.kpf-noresult{padding:12px 14px;color:var(--os-ink-2,#A6A8B5);font-size:13px}' +
    '.kpf-buyform{padding:12px 14px 14px;border-bottom:1px solid var(--os-line,rgba(255,255,255,.07));' +
      'background:var(--kpf-field);background:color-mix(in srgb,var(--os-accent,#4C8DF6) 7%,var(--kpf-card))}' +
    '.kpf-results>.kpf-buyform:last-child{border-bottom:0}' +
    '.kpf-or{color:var(--os-ink-2,#A6A8B5);font-size:12px;padding-bottom:12px}' +
    '.kpf-note{font-size:12px;color:var(--os-ink-2,#A6A8B5);line-height:1.55;margin-top:8px}' +
    // posiciones
    '.kpf-sec{font-size:13.5px;font-weight:800;color:var(--os-ink,#F2F2F5);margin:4px 2px 10px}' +
    '.kpf-tw{overflow-x:auto;background:var(--kpf-card);border-radius:var(--os-r,18px);box-shadow:var(--kpf-cshadow)}' +
    '.kpf-pos{width:100%;border-collapse:collapse;min-width:640px}' +
    '.kpf-pos th{padding:11px 10px 9px;font-size:11.5px;font-weight:700;color:var(--os-ink-2,#A6A8B5);text-align:left;white-space:nowrap;border-bottom:1px solid var(--os-line,rgba(255,255,255,.07))}' +
    '.kpf-pos th:first-child,.kpf-pos td:first-child{padding-left:16px}.kpf-pos th:last-child,.kpf-pos td:last-child{padding-right:14px}' +
    '.kpf-r,.kpf-pos th.kpf-r,.kpf-pos td.kpf-c-num{text-align:right}' +
    '.kpf-pos td{padding:10px;border-bottom:1px solid var(--os-line,rgba(255,255,255,.07));font-size:13px;color:var(--os-ink,#F2F2F5);font-variant-numeric:tabular-nums;vertical-align:middle}' +
    '.kpf-pos td.kpf-mute{color:var(--os-ink-2,#A6A8B5)}' +
    '.kpf-pos tbody tr:last-child td{border-bottom:0}' +
    '.kpf-c-co{max-width:220px}' +
    '.kpf-c-pl{font-weight:800}' +
    '.kpf-c-act{white-space:nowrap;text-align:right}' +
    '.kpf-c-act .kpf-sell-sh{width:78px;height:34px;font-size:12.5px;text-align:right;padding:0 8px}' +
    '.kpf-c-act .kpf-sell{margin-left:6px;height:34px}' +
    '.kpf-nopos{text-align:center;color:var(--os-ink-2,#A6A8B5);font-size:13.5px;padding:28px 18px}' +
    '.kpf-foot{font-size:12px;color:var(--os-ink-2,#A6A8B5);margin-top:14px;line-height:1.6}' +
    // pestañas = control segmentado (como .osw-seg)
    '.kpf-tabs{display:flex;gap:2px;padding:3px;border-radius:999px;background:var(--kpf-seg);margin-bottom:16px}' +
    '.kpf-tab{flex:1 1 0;min-width:0;appearance:none;-webkit-appearance:none;border:0;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:7px;' +
      'min-height:38px;padding:3px 12px;border-radius:999px;background:none;color:var(--os-ink-2,#A6A8B5);font-size:13.5px;font-weight:700;line-height:1.2;text-align:center;' +
      'transition:background-color .15s,color .15s,box-shadow .15s}' +
    '.kpf-tab:hover{color:var(--os-ink,#F2F2F5)}' +
    '.kpf-tab.on{background:var(--os-surface,#17181F);color:var(--os-ink,#F2F2F5);box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35))}' +
    // asistente
    '.kpf-intro{display:flex;gap:12px;align-items:flex-start;margin-bottom:14px;font-size:13.5px;color:var(--os-ink-2,#A6A8B5);line-height:1.6}' +
    '.kpf-intro>.km{margin-top:2px}' +
    '.kpf-modes{display:flex;gap:8px;margin-bottom:14px}' +
    '.kpf-mode{flex:1 1 0;min-width:0;appearance:none;-webkit-appearance:none;border:0;cursor:pointer;min-height:46px;padding:8px 12px;border-radius:var(--os-r-sm,12px);' +
      'background:var(--kpf-card);box-shadow:var(--kpf-cshadow);color:var(--os-ink,#F2F2F5);font-size:14px;font-weight:700;line-height:1.25;transition:background-color .15s,color .15s}' +
    '.kpf-mode:hover{background:var(--kpf-hover)}' +
    '.kpf-mode.on{background:var(--os-btn,#F2F2F5);color:var(--os-btn-ink,#111216)}' +
    '.kpf-err{color:var(--os-bad-ink,#F47C7C)!important;background:var(--os-surface-2,#1F2029);background:color-mix(in srgb,var(--os-bad,#f06565) 11%,var(--kpf-card))!important}' +
    '.kpf-flabel{display:flex;align-items:center;flex-wrap:wrap;gap:8px;font-size:14px;font-weight:800;color:var(--os-ink,#F2F2F5);margin-bottom:8px}' +
    '.kpf-num{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:50%;font-size:11.5px;font-weight:800;' +
      'background:var(--os-btn,#F2F2F5);color:var(--os-btn-ink,#111216)}' +
    '.kpf-flsub{font-weight:500;color:var(--os-ink-2,#A6A8B5);font-size:12px}' +
    '.kpf-opts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-bottom:16px}' +
    '.kpf-opt{appearance:none;-webkit-appearance:none;border:0;cursor:pointer;text-align:left;padding:11px 12px;border-radius:var(--os-r-sm,12px);background:var(--kpf-field);' +
      'color:var(--os-ink,#F2F2F5);display:flex;flex-direction:column;justify-content:center;gap:3px;min-height:48px;box-shadow:inset 0 0 0 1px var(--os-line,rgba(255,255,255,.07));transition:box-shadow .15s,background-color .15s}' +
    '.kpf-opt b{font-size:13.5px;font-weight:700}.kpf-opt span{font-size:11.5px;color:var(--os-ink-2,#A6A8B5);font-weight:500;line-height:1.35}' +
    '.kpf-opt:hover{box-shadow:inset 0 0 0 1px var(--os-ink-3,#6E7080)}' +
    '.kpf-opt.on{box-shadow:inset 0 0 0 2px var(--os-accent,#4C8DF6);background:var(--kpf-field);background:color-mix(in srgb,var(--os-accent,#4C8DF6) 9%,var(--kpf-field))}' +
    '.kpf-chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px}' +
    '.kpf-suggs{margin:12px 0 10px}' +
    '.kpf-chip{appearance:none;-webkit-appearance:none;border:0;cursor:pointer;font-size:12.5px;font-weight:600;padding:0 12px;min-height:34px;border-radius:999px;' +
      'background:var(--kpf-field);color:var(--os-ink,#F2F2F5);box-shadow:inset 0 0 0 1px var(--os-line,rgba(255,255,255,.07));transition:box-shadow .15s,background-color .15s}' +
    '.kpf-chip:hover:not(:disabled){box-shadow:inset 0 0 0 1px var(--os-ink-3,#6E7080)}' +
    '.kpf-chip.on{background:var(--os-btn,#F2F2F5);color:var(--os-btn-ink,#111216);box-shadow:none}' +
    '.kpf-chip:disabled{opacity:.5;cursor:not-allowed}' +
    '.kpf-cnt{opacity:.72;font-variant-numeric:tabular-nums}' +
    '.kpf-amt{display:flex;align-items:center;gap:8px;margin-bottom:16px}' +
    '.kpf-amt .kpf-in{max-width:200px;font-size:15px;font-weight:700}' +
    '.kpf-check{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--os-ink,#F2F2F5);margin-bottom:10px;cursor:pointer}' +
    '.kpf-check input{width:17px;height:17px;accent-color:var(--os-accent,#4C8DF6);flex:0 0 auto}' +
    // chat del asistente
    '.kpf-chat{max-height:420px;overflow-y:auto;overscroll-behavior:contain;display:flex;flex-direction:column;gap:10px}' +
    '.kpf-chat-empty{margin:2px 2px 0}' +
    '.kpf-msg{max-width:88%;padding:10px 14px;font-size:13.5px;line-height:1.6;overflow-wrap:anywhere}' +
    '.kpf-me{align-self:flex-end;border-radius:18px 18px 6px 18px;color:var(--os-ink,#F2F2F5);background:var(--kpf-field);background:color-mix(in srgb,var(--os-accent,#4C8DF6) 16%,var(--kpf-card))}' +
    '.kpf-botrow{display:flex;gap:8px;align-items:flex-start;align-self:flex-start;max-width:94%}' +
    '.kpf-bav{flex:0 0 28px;width:28px;height:28px;line-height:0;margin-top:2px}' +
    '.kpf-botrow .kpf-msg{max-width:none;min-width:0}' +
    '.kpf-bot{border-radius:6px 18px 18px 18px;background:var(--kpf-field);color:var(--os-ink,#F2F2F5)}' +
    '.kpf-thinking{color:var(--os-ink-2,#A6A8B5)}' +
    '.kpf-srcs{margin-top:8px;display:flex;flex-wrap:wrap;gap:5px}' +
    '.kpf-src{display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:600;padding:3px 9px;border-radius:999px;' +
      'background:var(--os-surface-3,#2A2B36);color:var(--os-ink-2,#A6A8B5);white-space:nowrap}' +
    '.kpf-src-ai{color:var(--os-ai,#B48CFF);background:var(--os-surface-3,#2A2B36);background:color-mix(in srgb,var(--os-ai,#B48CFF) 14%,transparent)}' +
    '.kpf-src-auto{color:var(--os-warn-ink,#F2C46D);background:var(--os-surface-3,#2A2B36);background:color-mix(in srgb,var(--os-warn,#F2C46D) 16%,transparent)}' +
    '.kpf-askrow{display:flex;gap:8px}.kpf-askrow .kpf-in{flex:1;height:44px}' +
    // propuestas
    '.kpf-disc{margin-top:14px;padding:11px 14px;border-radius:var(--os-r-sm,12px);font-size:12.5px;line-height:1.55;' +
      'color:var(--os-warn-ink,#F2C46D);background:var(--os-surface-2,#1F2029);background:color-mix(in srgb,var(--os-warn,#F2C46D) 13%,transparent)}' +
    '.kpf-prop-h{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-bottom:12px}' +
    '.kpf-prop-n{font-size:16px;font-weight:800;letter-spacing:-.01em;color:var(--os-ink,#F2F2F5)}' +
    '.kpf-tiles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}' +
    '.kpf-tile{background:var(--kpf-field);border-radius:var(--os-r-sm,12px);padding:10px 12px;min-width:0}' +
    '.kpf-tl{font-size:11.5px;font-weight:700;color:var(--os-ink-2,#A6A8B5);margin-bottom:4px}' +
    '.kpf-tv{font-size:18px;font-weight:800;color:var(--os-ink,#F2F2F5);font-variant-numeric:tabular-nums}' +
    '.kpf-ts{font-size:11px;color:var(--os-ink-2,#A6A8B5);margin-top:2px}' +
    '.kpf-tw2{overflow-x:auto;margin:12px 0}' +
    '.kpf-ptable{width:100%;border-collapse:collapse;font-size:12.5px}' +
    '.kpf-ptable th{font-size:11.5px;color:var(--os-ink-2,#A6A8B5);font-weight:700;text-align:left;padding:6px;white-space:nowrap}' +
    '.kpf-ptable th.kpf-r,.kpf-ptable td.kpf-r{text-align:right}' +
    '.kpf-ptable td{padding:7px 6px;border-top:1px solid var(--os-line,rgba(255,255,255,.07));color:var(--os-ink,#F2F2F5);font-variant-numeric:tabular-nums}' +
    '.kpf-ptable td.kpf-mute{color:var(--os-ink-2,#A6A8B5)}' +
    '.kpf-wcell{min-width:96px}' +
    '.kpf-wrow{display:flex;align-items:center;gap:6px}' +
    '.kpf-wbar{flex:1;height:6px;border-radius:999px;background:var(--os-surface-3,#2A2B36);overflow:hidden}' +
    '.kpf-wbar i{display:block;height:100%;border-radius:999px;background:var(--os-accent,#4C8DF6)}' +
    '.kpf-wrow b{font-variant-numeric:tabular-nums;color:var(--os-ink,#F2F2F5)}' +
    '.kpf-p{font-size:13px;color:var(--os-ink,#F2F2F5);line-height:1.65;margin-bottom:12px}' +
    '.kpf-list{margin:0 0 12px;padding-left:18px;font-size:13px;color:var(--os-ink,#F2F2F5);line-height:1.6}' +
    '.kpf-warnnote{font-size:12px;font-weight:600;color:var(--os-warn-ink,#F2C46D);margin-bottom:10px}' +
    '.kpf-details{margin-top:10px;font-size:12px;color:var(--os-ink-2,#A6A8B5)}' +
    '.kpf-details summary{cursor:pointer;font-weight:600;border-radius:6px}' +
    '.kpf-details ul{margin:8px 0 0;padding-left:18px;line-height:1.6}' +
    // ventana ANGOSTA (flancos del OS ~400 px) o móvil: una columna; la tabla de posiciones pasa a tarjetas
    '@container kpf (max-width:600px){' +
      '.kpf-wrap{padding:14px 12px 40px}' +
      '.kpf-actions{width:100%}.kpf-sel{flex:1 1 100%;max-width:none}' +
      '.kpf-opts{grid-template-columns:1fr}.kpf-tiles{grid-template-columns:repeat(2,minmax(0,1fr))}' +
      '.kpf-hide-sm{display:none}' +
      '.kpf-tab{font-size:12.5px;padding:3px 6px;gap:5px}.kpf-mode{font-size:13px;padding:8px}' +
      '.kpf-msg{max-width:96%}.kpf-botrow{max-width:100%}' +
      '.kpf-cash{flex:1 1 150px}' +
      '.kpf-tw{overflow:visible}' +
      '.kpf-pos,.kpf-pos tbody{display:block;min-width:0;width:100%}' +
      '.kpf-pos thead{display:none}' +
      '.kpf-pos tr{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));grid-template-areas:"co co co pl" "sh bp nw vl" "ac ac ac ac";' +
        'gap:8px 10px;padding:12px 14px;border-bottom:1px solid var(--os-line,rgba(255,255,255,.07))}' +
      '.kpf-pos tbody tr:last-child{border-bottom:0}' +
      '.kpf-pos td,.kpf-pos td:first-child,.kpf-pos td:last-child{padding:0;border:0;text-align:left;min-width:0}' +
      '.kpf-pos td.kpf-c-co{grid-area:co;max-width:none}' +
      '.kpf-pos td:nth-child(2){grid-area:sh}.kpf-pos td:nth-child(3){grid-area:bp}.kpf-pos td:nth-child(4){grid-area:nw}.kpf-pos td:nth-child(5){grid-area:vl}' +
      '.kpf-pos td.kpf-c-num.kpf-c-pl{grid-area:pl;text-align:right;font-size:15px;align-self:center}' +
      '.kpf-pos td.kpf-c-num{font-size:12.5px;text-align:left;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
      '.kpf-pos td[data-l]:before{content:attr(data-l);display:block;font-size:10.5px;font-weight:700;color:var(--os-ink-2,#A6A8B5);margin-bottom:1px;overflow:hidden;text-overflow:ellipsis}' +
      '.kpf-pos td.kpf-c-act{grid-area:ac;display:flex;gap:8px;justify-content:flex-end}' +
      '.kpf-pos td.kpf-c-act .kpf-sell-sh{flex:1 1 auto;width:auto;max-width:180px}' +
      '.kpf-pos td.kpf-c-act .kpf-sell{margin-left:0}' +
    '}' +
    // celular (~390 px): cifras sin recortar → posiciones en 2 columnas y números del resumen algo menores
    '@container kpf (max-width:400px){.kpf-sv{font-size:18px}.kpf-sum{gap:8px}.kpf-stat{padding:12px 13px}' +
      '.kpf-pos tr{grid-template-columns:repeat(2,minmax(0,1fr));grid-template-areas:"co pl" "sh bp" "nw vl" "ac ac";gap:8px 12px}}' +
    '@container kpf (max-width:380px){.kpf-modes{flex-direction:column}.kpf-askrow{flex-wrap:wrap}.kpf-askrow .kpf-btn{width:100%}}' +
    // sin container queries (navegadores viejos): al menos el móvil por ancho de pantalla
    '@media (max-width:560px){.kpf-opts{grid-template-columns:1fr}.kpf-tiles{grid-template-columns:repeat(2,minmax(0,1fr))}.kpf-hide-sm{display:none}.kpf-msg{max-width:96%}}' +
    '@media (prefers-reduced-motion:reduce){.kpf-btn,.kpf-tab,.kpf-mode,.kpf-opt,.kpf-chip,.kpf-in{transition:none}.kpf-btn:active{transform:none}}';
  function ensureCss() {
    if (document.getElementById('kpf-css')) return;
    var st = document.createElement('style'); st.id = 'kpf-css'; st.textContent = CSS_PF;
    (document.head || document.documentElement).appendChild(st);
  }

  function wireAI() {
    $all('.kpf-mode').forEach(function (b) {
      b.onclick = function () { readFormSafe(); _aiMode = b.getAttribute('data-mode'); render(); };
    });
    $all('.kpf-opt').forEach(function (b) {
      b.onclick = function () { readForm(); _form[b.getAttribute('data-f')] = b.getAttribute('data-v'); render(); };
    });
    $all('.kpf-theme').forEach(function (b) {
      b.onclick = function () {
        readForm();
        var k = b.getAttribute('data-k'), i = _form.themes.indexOf(k);
        if (i >= 0) _form.themes.splice(i, 1); else _form.themes.push(k);
        render();
      };
    });
    var el;
    if ((el = $('#kpf-prop-go'))) el.onclick = sendPropose;
    $all('.kpf-create').forEach(function (b) { b.onclick = function () { createFromProposal(+b.getAttribute('data-i')); }; });
    $all('.kpf-goto').forEach(function (b) { b.onclick = function () { setActiveId(b.getAttribute('data-pf')); setView('pf'); render(); }; });
    $all('.kpf-riskgo').forEach(function (b) {
      b.onclick = function () { if (window.KhipuRisk) window.KhipuRisk.open({ tab: 'var', source: 'pf:' + b.getAttribute('data-pf'), autorun: true }); };
    });
    // chat
    var askEl = $('#kpf-ask');
    if (askEl) {
      askEl.oninput = function () { _askDraft = askEl.value; };
      askEl.onkeydown = function (e) { if (e.key === 'Enter') { e.preventDefault(); sendAsk(askEl.value); } };
    }
    if ((el = $('#kpf-ask-go'))) el.onclick = function () { sendAsk(($('#kpf-ask') || {}).value); };
    $all('.kpf-sugg').forEach(function (b) { b.onclick = function () { sendAsk(b.getAttribute('data-q')); }; });
    if ((el = $('#kpf-usepf'))) el.onchange = function () { _useMyPf = !!el.checked; };
    var c = $('#kpf-chat'); if (c) c.scrollTop = c.scrollHeight;
  }
  function readFormSafe() { try { readForm(); } catch (e) {} }

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
    $all('.kpf-tab-ai').forEach(function (b) { b.onclick = function () { setView('ai'); _aiMode = 'propose'; render(); }; });
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
    if ((el = $('#kpf-risk'))) el.onclick = function () {
      var a = activeId(); if (window.KhipuRisk) window.KhipuRisk.open({ tab: 'var', source: a ? 'pf:' + a : 'market', autorun: true });
    };
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
        tradeToast('buy', res);
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
        tradeToast('sell', res);
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
    // utilidades por si otro módulo (Khipu, KHIPU) las necesita
    _list: loadAll,
    _buy: buy,           // los usa el comité de cartera (engine/pfcommittee.js) para aplicar consejos en SIMULACIÓN
    _sell: sell,
    _stats: pfStats,
    _priceOf: priceOf
  };
})();
