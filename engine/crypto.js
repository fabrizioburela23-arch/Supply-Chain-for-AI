/* ============================================================================
   engine/crypto.js — Pestaña ₿ Cripto (Fase 1 módulo de datos + Expediente).
   - Datos VIVOS: /api/crypto/* (server → core/providers/coingecko.py).
   - Capa ESTÁTICA: window.CRYPTO_INTEL + window.CRYPTO_CATS
     (nodes/crypto_intel*.js, expediente jul-2026, refrescar cada 3-6 meses).
   Tres vistas: 🗺 Mapa (categorías explicadas — para ENTENDER el mercado),
   ☰ Lista (top 100 con filtros por tesis), y Detalle (gráfico 90d + ficha
   del expediente con advertencias ⚠). Bilingüe ES/EN (regla del proyecto).
   ============================================================================ */
(function () {
  'use strict';

  var LOADED_AT = 0;      // timestamp del último fetch de la lista
  var ASSETS = [];        // CryptoAsset[] vivos (top 100)
  var CHART = null;       // instancia Chart.js de la vista detalle
  var VIEW = null;        // 'map' | 'list' (persistido)
  var FILTER = null;      // null | catKey

  var CAT_ORDER = ['store', 'l1', 'stable', 'payments', 'defi', 'perps', 'exchange', 'rwa', 'ai', 'privacy', 'meme'];

  function T(k, fb) {
    try { if (typeof window.t === 'function') { var v = window.t(k); if (v && v !== k) return v; } } catch (e) {}
    return fb;
  }
  function lang() {
    try { return window.LANG || localStorage.getItem('eco_lang') || 'es'; } catch (e) { return 'es'; }
  }
  function view() {
    if (VIEW) return VIEW;
    try { VIEW = localStorage.getItem('kh_cryptoview') || 'map'; } catch (e) { VIEW = 'map'; }
    return VIEW;
  }
  function intelOf(a) {
    var I = window.CRYPTO_INTEL || {};
    if (a.id && I[a.id]) return I[a.id];
    var sym = (a.symbol || '').toUpperCase();
    for (var k in I) { if (I[k].ticker === sym) return I[k]; }
    return null;
  }
  function catInfo(key) { return (window.CRYPTO_CATS || {})[key] || null; }
  function catLabel(key) { var c = catInfo(key); return c ? (lang() === 'en' ? c.en : c.es) : key; }

  // ── formato ──
  function fmtPrice(v) {
    if (v == null) return '—';
    if (v >= 1000) return '$' + v.toLocaleString(undefined, { maximumFractionDigits: 0 });
    if (v >= 1) return '$' + v.toLocaleString(undefined, { maximumFractionDigits: 2 });
    return '$' + v.toLocaleString(undefined, { maximumFractionDigits: 6 });
  }
  function fmtBig(v) {
    if (v == null) return '—';
    if (v >= 1e12) return '$' + (v / 1e12).toFixed(2) + 'T';
    if (v >= 1e9) return '$' + (v / 1e9).toFixed(1) + 'B';
    if (v >= 1e6) return '$' + (v / 1e6).toFixed(1) + 'M';
    return '$' + Math.round(v).toLocaleString();
  }
  function fmtPct(v) {
    if (v == null) return '<span style="color:#7C87A3">—</span>';
    var c = v >= 0 ? '#2BE38B' : '#FF4D6A';
    return '<span style="color:' + c + ';font-weight:600">' + (v >= 0 ? '+' : '') + v.toFixed(2) + '%</span>';
  }
  function fmtSupply(v, sym) {
    if (v == null) return '—';
    var n = v >= 1e9 ? (v / 1e9).toFixed(2) + 'B' : v >= 1e6 ? (v / 1e6).toFixed(1) + 'M' : Math.round(v).toLocaleString();
    return n + (sym ? ' ' + sym : '');
  }
  function esc(s) { return String(s == null ? '' : s).replace(/[<>&"]/g, function (c) { return { '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c]; }); }

  function panel() { return document.getElementById('crypto-panel'); }

  // ── cabecera común (título + conmutador de vista + refresh) ──
  function headerHTML() {
    var isMap = view() === 'map';
    var seg = function (id, txt, on) {
      return '<button onclick="window.KhipuCrypto.setView(\'' + id + '\')" style="padding:5px 13px;border-radius:7px;cursor:pointer;font-size:12px;font-weight:600;' +
        'border:1px solid ' + (on ? 'rgba(0,224,255,.45)' : 'transparent') + ';background:' + (on ? 'rgba(0,224,255,.12)' : 'none') + ';color:' + (on ? '#00E0FF' : '#7C87A3') + '">' + txt + '</button>';
    };
    return '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:4px">' +
      '<h2 style="margin:0;font-size:19px">' + T('cr_title', '₿ Cripto') + '</h2>' +
      '<div style="display:flex;gap:2px;background:rgba(21,28,45,.6);border-radius:9px;padding:2px">' +
        seg('map', '🗺 ' + T('cr_view_map', 'Mapa'), isMap) + seg('list', '☰ ' + T('cr_view_list', 'Lista'), !isMap) + '</div>' +
      '<button onclick="window.KhipuCrypto.refresh()" title="Refresh" style="margin-left:auto;padding:5px 12px;border-radius:7px;border:1px solid rgba(0,224,255,.3);background:rgba(0,224,255,.08);color:#00E0FF;cursor:pointer;font-size:12px">⟳</button></div>' +
      '<div style="color:#7C87A3;font-size:12px;margin-bottom:12px">' + T('cr_sub', 'Datos en vivo de CoinGecko · clic en una moneda para ver su detalle') + '</div>';
  }

  // chips de categoría (filtro en vista lista)
  function chipsHTML() {
    if (!window.CRYPTO_CATS) return '';
    var mk = function (key, txt, on) {
      return '<button onclick="window.KhipuCrypto.setFilter(' + (key ? '\'' + key + '\'' : 'null') + ')" style="padding:4px 11px;border-radius:999px;cursor:pointer;font-size:11px;font-weight:600;white-space:nowrap;' +
        'border:1px solid ' + (on ? 'rgba(0,224,255,.5)' : 'rgba(122,158,255,.18)') + ';background:' + (on ? 'rgba(0,224,255,.12)' : 'rgba(21,28,45,.5)') + ';color:' + (on ? '#00E0FF' : '#9AA6C4') + '">' + txt + '</button>';
    };
    var h = mk(null, T('cr_all', 'Todas'), !FILTER);
    CAT_ORDER.forEach(function (k) {
      var c = catInfo(k); if (!c) return;
      h += mk(k, c.icon + ' ' + catLabel(k), FILTER === k);
    });
    return '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px">' + h + '</div>';
  }

  function badges(a) {
    var it = intelOf(a); var h = '';
    if (it) h += '<span title="' + T('cr_dossier', 'Expediente') + '" style="font-size:10px">📋</span>';
    if (it && it.warn) h += '<span title="' + esc(lang() === 'en' ? it.warn.en : it.warn.es) + '" style="font-size:10px">⚠️</span>';
    return h;
  }

  // ── vista LISTA ──
  function renderList() {
    var p = panel(); if (!p) return;
    var list = ASSETS;
    if (FILTER) list = ASSETS.filter(function (a) { var it = intelOf(a); return it && (it.tags || [it.cat]).indexOf(FILTER) >= 0; });
    var rows = list.map(function (a) {
      return '<tr onclick="window.KhipuCrypto.openDetail(\'' + esc(a.id) + '\')" style="cursor:pointer">' +
        '<td style="color:#7C87A3;text-align:right;padding-right:10px">' + (a.rank || '—') + '</td>' +
        '<td><div style="display:flex;align-items:center;gap:8px">' +
          (a.image ? '<img src="' + esc(a.image) + '" width="20" height="20" style="border-radius:50%" loading="lazy">' : '') +
          '<b>' + esc(a.name) + '</b><span style="color:#7C87A3;font-size:11px">' + esc(a.symbol) + '</span>' + badges(a) + '</div></td>' +
        '<td style="text-align:right;font-variant-numeric:tabular-nums">' + fmtPrice(a.price) + '</td>' +
        '<td style="text-align:right">' + fmtPct(a.change_24h_pct) + '</td>' +
        '<td style="text-align:right" class="cr-hide-m">' + fmtPct(a.change_7d_pct) + '</td>' +
        '<td style="text-align:right" class="cr-hide-m">' + fmtBig(a.market_cap) + '</td>' +
        '<td style="text-align:right" class="cr-hide-m">' + fmtBig(a.volume_24h) + '</td></tr>';
    }).join('');
    p.innerHTML =
      '<div style="max-width:1100px;margin:0 auto;padding:20px 16px 60px">' + headerHTML() + chipsHTML() +
        '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12.5px">' +
          '<thead><tr style="color:#7C87A3;font-size:10.5px;text-transform:uppercase;letter-spacing:.05em">' +
            '<th style="text-align:right;padding:6px 10px 6px 0">#</th>' +
            '<th style="text-align:left;padding:6px 0">' + T('cr_th_coin', 'Moneda') + '</th>' +
            '<th style="text-align:right">' + T('cr_th_price', 'Precio') + '</th>' +
            '<th style="text-align:right">' + T('cr_th_24h', '24h %') + '</th>' +
            '<th style="text-align:right" class="cr-hide-m">' + T('cr_th_7d', '7d %') + '</th>' +
            '<th style="text-align:right" class="cr-hide-m">' + T('cr_th_mcap', 'Market cap') + '</th>' +
            '<th style="text-align:right" class="cr-hide-m">' + T('cr_th_vol', 'Volumen 24h') + '</th></tr></thead>' +
          '<tbody>' + rows + '</tbody></table>' +
          (list.length ? '' : '<div style="padding:40px;text-align:center;color:#7C87A3;font-size:13px">' + T('cr_empty', 'Ninguna moneda del top 100 en esta categoría.') + '</div>') +
        '</div></div>' + baseCSS();
  }

  // ── vista MAPA (categorías explicadas — el "entender el mercado") ──
  function renderMap() {
    var p = panel(); if (!p) return;
    var I = window.CRYPTO_INTEL || {};
    var bySym = {}; ASSETS.forEach(function (a) { bySym[(a.symbol || '').toUpperCase()] = a; if (a.id) bySym['#' + a.id] = a; });
    var cards = CAT_ORDER.map(function (key) {
      var c = catInfo(key); if (!c) return '';
      var members = [];
      for (var id in I) {
        var it = I[id];
        if ((it.tags || [it.cat]).indexOf(key) < 0) continue;
        members.push({ id: id, it: it, live: bySym['#' + id] || bySym[it.ticker] || null });
      }
      if (!members.length) return '';
      members.sort(function (a, b) { return (a.it.rank || 999) - (b.it.rank || 999); });
      var chips = members.map(function (m) {
        var pct = m.live ? m.live.change_24h_pct : null;
        var col = pct == null ? '#7C87A3' : pct >= 0 ? '#2BE38B' : '#FF4D6A';
        return '<button onclick="window.KhipuCrypto.openDetail(\'' + esc(m.id) + '\')" style="display:inline-flex;align-items:center;gap:5px;padding:5px 10px;margin:0 6px 6px 0;' +
          'border-radius:8px;border:1px solid rgba(122,158,255,.16);background:rgba(13,19,33,.7);cursor:pointer;font-size:11.5px;color:#E8EDFB">' +
          '<b>' + esc(m.it.ticker) + '</b>' +
          (pct != null ? '<span style="color:' + col + ';font-weight:600">' + (pct >= 0 ? '+' : '') + pct.toFixed(1) + '%</span>' : '') +
          (m.it.warn ? '<span title="' + esc(lang() === 'en' ? m.it.warn.en : m.it.warn.es) + '">⚠️</span>' : '') + '</button>';
      }).join('');
      return '<div style="border:1px solid rgba(122,158,255,.14);border-radius:14px;padding:16px 16px 10px;background:linear-gradient(180deg,rgba(13,19,35,.85),rgba(8,12,22,.85))">' +
        '<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:4px"><span style="font-size:17px">' + c.icon + '</span>' +
          '<b style="font-size:14px">' + esc(catLabel(key)) + '</b>' +
          '<span style="margin-left:auto;color:#7C87A3;font-size:10.5px">' + members.length + '</span></div>' +
        '<div style="color:#9AA6C4;font-size:11.5px;line-height:1.5;margin-bottom:10px">' + esc(lang() === 'en' ? (c.ben || '') : (c.bes || '')) + '</div>' +
        '<div>' + chips + '</div></div>';
    }).join('');
    p.innerHTML =
      '<div style="max-width:1100px;margin:0 auto;padding:20px 16px 60px">' + headerHTML() +
        (cards ? '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px">' + cards + '</div>' +
          '<div style="margin-top:16px;color:#5C6784;font-size:10.5px;line-height:1.5">' + T('cr_disclaimer', 'Contexto informativo, no es asesoría de inversión. Capa de análisis: jul 2026 · precios en vivo de CoinGecko.') + '</div>'
        : '<div style="padding:50px;text-align:center;color:#7C87A3;font-size:13px">' + T('cr_loading', 'Cargando mercado cripto…') + '</div>') +
      '</div>' + baseCSS();
  }

  function baseCSS() {
    return '<style>#crypto-panel td{padding:8px 6px;border-bottom:1px solid rgba(122,158,255,.08)}' +
      '#crypto-panel tbody tr:hover{background:rgba(0,224,255,.05)}' +
      '@media(max-width:760px){#crypto-panel .cr-hide-m{display:none}}</style>';
  }

  function renderCurrent() { if (view() === 'map') renderMap(); else renderList(); }

  function renderMsg(html) {
    var p = panel(); if (!p) return;
    p.innerHTML = '<div style="padding:60px 20px;text-align:center;color:#7C87A3;font-size:13px">' + html + '</div>';
  }

  // ── bloque Expediente de la vista detalle ──
  function intelHTML(it) {
    if (!it) return '';
    var L = lang() === 'en' ? it.en : it.es;
    if (!L) return '';
    var BLOCKS = [
      ['what', '💡', T('cr_b_what', '¿Qué es?'), '#52B1FF'],
      ['mech', '⚙️', T('cr_b_mech', 'Cómo funciona'), '#8e5aff'],
      ['tok', '🪙', T('cr_b_tok', 'Tokenomics'), '#3DE0C8'],
      ['cats', '🚀', T('cr_b_cats', 'Catalizadores'), '#2BE38B'],
      ['risks', '⚠️', T('cr_b_risks', 'Riesgos'), '#FF4D6A'],
      ['pos', '🎯', T('cr_b_pos', 'Posicionamiento'), '#FFB300'],
    ];
    var blocks = BLOCKS.map(function (b) {
      var txt = L[b[0]]; if (!txt) return '';
      return '<div style="border-left:3px solid ' + b[3] + ';padding:8px 12px;margin-bottom:10px;background:rgba(13,19,33,.55);border-radius:0 9px 9px 0">' +
        '<div style="font-size:11px;font-weight:700;color:' + b[3] + ';margin-bottom:3px">' + b[1] + ' ' + b[2] + '</div>' +
        '<div style="font-size:12.5px;line-height:1.6;color:#C9D4EC">' + esc(txt) + '</div></div>';
    }).join('');
    var cat = catInfo(it.cat);
    var warn = it.warn ? '<div style="margin:10px 0;padding:9px 13px;border-radius:9px;border:1px solid rgba(255,77,106,.4);background:rgba(255,77,106,.09);color:#FF8FA3;font-size:12px;font-weight:600">' +
      esc(lang() === 'en' ? it.warn.en : it.warn.es) + '</div>' : '';
    return '<div style="margin-top:22px">' +
      '<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap">' +
        '<h3 style="margin:0;font-size:15px">📋 ' + T('cr_dossier_t', 'Expediente Khipus') + '</h3>' +
        (cat ? '<span style="padding:3px 10px;border-radius:999px;border:1px solid rgba(0,224,255,.3);background:rgba(0,224,255,.07);color:#00E0FF;font-size:10.5px;font-weight:600">' + cat.icon + ' ' + esc(catLabel(it.cat)) + '</span>' : '') +
      '</div>' + warn + blocks +
      '<div style="color:#5C6784;font-size:10.5px;line-height:1.5">' + T('cr_disclaimer', 'Contexto informativo, no es asesoría de inversión. Capa de análisis: jul 2026 · precios en vivo de CoinGecko.') + '</div></div>';
  }

  // ── vista DETALLE ──
  function renderDetail(a) {
    var p = panel(); if (!p) return;
    var it = intelOf(a);
    var kv = function (k, v) {
      return '<div style="display:flex;justify-content:space-between;gap:12px;padding:7px 0;border-bottom:1px solid rgba(122,158,255,.08);font-size:12.5px">' +
        '<span style="color:#7C87A3">' + k + '</span><span style="font-weight:600">' + v + '</span></div>';
    };
    var athDate = a.ath_date ? new Date(a.ath_date).toLocaleDateString(lang() === 'en' ? 'en-US' : 'es-PE') : '';
    p.innerHTML =
      '<div style="max-width:900px;margin:0 auto;padding:20px 16px 60px">' +
        '<button onclick="window.KhipuCrypto.back()" style="margin-bottom:14px;padding:5px 12px;border-radius:7px;border:1px solid rgba(122,158,255,.25);background:none;color:#8791AC;cursor:pointer;font-size:12px">' + T('cr_back', '← Volver') + '</button>' +
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;flex-wrap:wrap">' +
          (a.image ? '<img src="' + esc(a.image) + '" width="34" height="34" style="border-radius:50%">' : '') +
          '<h2 style="margin:0;font-size:21px">' + esc(a.name) + ' <span style="color:#7C87A3;font-size:14px">' + esc(a.symbol) + '</span></h2>' +
          '<span style="margin-left:auto;font-size:22px;font-weight:800">' + fmtPrice(a.price) + '</span>' + fmtPct(a.change_24h_pct) + '</div>' +
        '<div style="height:280px;margin:16px 0"><canvas id="cr-chart"></canvas></div>' +
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:0 32px">' +
          kv(T('cr_rank', 'Ranking'), '#' + (a.rank || '—')) +
          kv(T('cr_th_mcap', 'Market cap'), fmtBig(a.market_cap)) +
          kv(T('cr_th_vol', 'Volumen 24h'), fmtBig(a.volume_24h)) +
          kv(T('cr_supply', 'En circulación'), fmtSupply(a.circulating_supply, a.symbol)) +
          kv(T('cr_maxsupply', 'Suministro máximo'), a.max_supply ? fmtSupply(a.max_supply, a.symbol) : '∞') +
          kv(T('cr_ath', 'Máximo histórico'), fmtPrice(a.ath) + (athDate ? ' <span style="color:#7C87A3;font-weight:400">(' + athDate + ')</span>' : '')) +
          kv(T('cr_atl', 'Mínimo histórico'), fmtPrice(a.atl)) +
        '</div>' +
        intelHTML(it) +
        (a.description ? '<p style="margin-top:18px;font-size:13px;line-height:1.65;color:#8b96b5">' + esc(a.description) + '</p>' : '') +
      '</div>';
    // gráfico de precio 90 días
    fetch('/api/crypto/' + encodeURIComponent(a.id) + '/history?days=90')
      .then(function (r) { return r.json(); })
      .then(function (h) {
        var prices = (h && h.prices) || [];
        if (!prices.length || typeof Chart === 'undefined') return;
        var el = document.getElementById('cr-chart'); if (!el) return;
        if (CHART) { try { CHART.destroy(); } catch (e) {} }
        var up = prices[prices.length - 1][1] >= prices[0][1];
        var col = up ? '#2BE38B' : '#FF4D6A';
        CHART = new Chart(el.getContext('2d'), {
          type: 'line',
          data: { labels: prices.map(function (x) { return new Date(x[0]).toLocaleDateString(lang() === 'en' ? 'en-US' : 'es-PE', { month: 'short', day: 'numeric' }); }),
            datasets: [{ data: prices.map(function (x) { return x[1]; }), borderColor: col, borderWidth: 2, pointRadius: 0, fill: true,
              backgroundColor: (up ? 'rgba(43,227,139,.08)' : 'rgba(255,77,106,.08)'), tension: 0.25 }] },
          options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } },
            interaction: { intersect: false, mode: 'index' },
            scales: { x: { ticks: { color: '#7C87A3', maxTicksLimit: 8, font: { size: 10 } }, grid: { display: false } },
              y: { ticks: { color: '#7C87A3', font: { size: 10 } }, grid: { color: 'rgba(122,158,255,.07)' } } } }
        });
      }).catch(function () {});
  }

  // ── API pública ──
  window.KhipuCrypto = {
    init: function (force) {
      var fresh = Date.now() - LOADED_AT < 120000;
      if (ASSETS.length && (fresh || force === true)) { renderCurrent(); if (fresh && force !== true) return; }
      if (!ASSETS.length) renderMsg(T('cr_loading', 'Cargando mercado cripto…'));
      fetch('/api/crypto/markets?per_page=100')
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d || !d.assets) throw new Error(d && d.error || 'sin datos');
          ASSETS = d.assets; LOADED_AT = Date.now(); renderCurrent();
        })
        .catch(function () {
          // sin red/API: la vista mapa aún sirve con la capa estática
          if (!ASSETS.length && view() === 'map' && window.CRYPTO_INTEL) renderMap();
          else if (!ASSETS.length) renderMsg(T('cr_err', 'No se pudo cargar el mercado cripto. Reintenta en unos segundos.'));
        });
    },
    refresh: function () { LOADED_AT = 0; ASSETS = []; window.KhipuCrypto.init(); },
    back: function () { window.KhipuCrypto.init(true); },
    setView: function (v) {
      VIEW = v === 'list' ? 'list' : 'map';
      try { localStorage.setItem('kh_cryptoview', VIEW); } catch (e) {}
      renderCurrent();
    },
    setFilter: function (k) { FILTER = k || null; if (view() !== 'list') { VIEW = 'list'; } renderList(); },
    openDetail: function (id) {
      renderMsg(T('cr_loading', 'Cargando mercado cripto…'));
      fetch('/api/crypto/' + encodeURIComponent(id))
        .then(function (r) { return r.json(); })
        .then(function (a) {
          if (!a || a.error) throw new Error(a && a.error || 'sin datos');
          renderDetail(a);
        })
        .catch(function () {
          // sin dato vivo: mostrar al menos el expediente estático
          var it = (window.CRYPTO_INTEL || {})[id];
          if (it) renderDetail({ id: id, name: it.name, symbol: it.ticker, rank: it.rank });
          else renderMsg(T('cr_err', 'No se pudo cargar el mercado cripto. Reintenta en unos segundos.'));
        });
    },
  };
})();
