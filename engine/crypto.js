/* ============================================================================
   engine/crypto.js — Pestaña ₿ Cripto (Fase 1 del módulo de datos, 2026-07-12).
   Consume /api/crypto/* (server → core/providers/coingecko.py, esquema
   unificado CryptoAsset). Bilingüe vía t()/I18N (claves cr_*) — regla ES/EN.
   Vista lista (top 100 por market cap) + vista detalle con gráfico de precio
   (Chart.js ya cargado en /vendor/chart.umd.min.js).
   ============================================================================ */
(function () {
  'use strict';

  var LOADED_AT = 0;      // timestamp del último fetch de la lista
  var ASSETS = [];        // CryptoAsset[]
  var CHART = null;       // instancia Chart.js de la vista detalle

  function T(k, fb) {
    try { if (typeof window.t === 'function') { var v = window.t(k); if (v && v !== k) return v; } } catch (e) {}
    return fb;
  }
  function lang() {
    try { return window.LANG || localStorage.getItem('eco_lang') || 'es'; } catch (e) { return 'es'; }
  }

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

  // ── vista lista ──
  function renderList() {
    var p = panel(); if (!p) return;
    var rows = ASSETS.map(function (a) {
      return '<tr onclick="window.KhipuCrypto.openDetail(\'' + esc(a.id) + '\')" style="cursor:pointer">' +
        '<td style="color:#7C87A3;text-align:right;padding-right:10px">' + (a.rank || '—') + '</td>' +
        '<td><div style="display:flex;align-items:center;gap:8px">' +
          (a.image ? '<img src="' + esc(a.image) + '" width="20" height="20" style="border-radius:50%" loading="lazy">' : '') +
          '<b>' + esc(a.name) + '</b><span style="color:#7C87A3;font-size:11px">' + esc(a.symbol) + '</span></div></td>' +
        '<td style="text-align:right;font-variant-numeric:tabular-nums">' + fmtPrice(a.price) + '</td>' +
        '<td style="text-align:right">' + fmtPct(a.change_24h_pct) + '</td>' +
        '<td style="text-align:right" class="cr-hide-m">' + fmtPct(a.change_7d_pct) + '</td>' +
        '<td style="text-align:right" class="cr-hide-m">' + fmtBig(a.market_cap) + '</td>' +
        '<td style="text-align:right" class="cr-hide-m">' + fmtBig(a.volume_24h) + '</td></tr>';
    }).join('');
    p.innerHTML =
      '<div style="max-width:1100px;margin:0 auto;padding:20px 16px 60px">' +
        '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:4px">' +
          '<h2 style="margin:0;font-size:19px">' + T('cr_title', '₿ Cripto — Top por capitalización') + '</h2>' +
          '<button onclick="window.KhipuCrypto.refresh()" style="margin-left:auto;padding:5px 12px;border-radius:7px;border:1px solid rgba(0,224,255,.3);background:rgba(0,224,255,.08);color:#00E0FF;cursor:pointer;font-size:12px">⟳</button></div>' +
        '<div style="color:#7C87A3;font-size:12px;margin-bottom:14px">' + T('cr_sub', 'Datos en vivo de CoinGecko · clic en una moneda para ver su detalle') + '</div>' +
        '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12.5px">' +
          '<thead><tr style="color:#7C87A3;font-size:10.5px;text-transform:uppercase;letter-spacing:.05em">' +
            '<th style="text-align:right;padding:6px 10px 6px 0">#</th>' +
            '<th style="text-align:left;padding:6px 0">' + T('cr_th_coin', 'Moneda') + '</th>' +
            '<th style="text-align:right">' + T('cr_th_price', 'Precio') + '</th>' +
            '<th style="text-align:right">' + T('cr_th_24h', '24h %') + '</th>' +
            '<th style="text-align:right" class="cr-hide-m">' + T('cr_th_7d', '7d %') + '</th>' +
            '<th style="text-align:right" class="cr-hide-m">' + T('cr_th_mcap', 'Market cap') + '</th>' +
            '<th style="text-align:right" class="cr-hide-m">' + T('cr_th_vol', 'Volumen 24h') + '</th></tr></thead>' +
          '<tbody id="cr-tbody">' + rows + '</tbody></table></div></div>' +
      '<style>#crypto-panel td{padding:8px 6px;border-bottom:1px solid rgba(122,158,255,.08)}' +
      '#crypto-panel tbody tr:hover{background:rgba(0,224,255,.05)}' +
      '@media(max-width:760px){#crypto-panel .cr-hide-m{display:none}}</style>';
  }

  function renderMsg(html) {
    var p = panel(); if (!p) return;
    p.innerHTML = '<div style="padding:60px 20px;text-align:center;color:#7C87A3;font-size:13px">' + html + '</div>';
  }

  // ── vista detalle ──
  function renderDetail(a) {
    var p = panel(); if (!p) return;
    var kv = function (k, v) {
      return '<div style="display:flex;justify-content:space-between;gap:12px;padding:7px 0;border-bottom:1px solid rgba(122,158,255,.08);font-size:12.5px">' +
        '<span style="color:#7C87A3">' + k + '</span><span style="font-weight:600">' + v + '</span></div>';
    };
    var athDate = a.ath_date ? new Date(a.ath_date).toLocaleDateString(lang() === 'en' ? 'en-US' : 'es-PE') : '';
    p.innerHTML =
      '<div style="max-width:900px;margin:0 auto;padding:20px 16px 60px">' +
        '<button onclick="window.KhipuCrypto.init(true)" style="margin-bottom:14px;padding:5px 12px;border-radius:7px;border:1px solid rgba(122,158,255,.25);background:none;color:#8791AC;cursor:pointer;font-size:12px">' + T('cr_back', '← Volver a la lista') + '</button>' +
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px">' +
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
        (a.description ? '<p style="margin-top:18px;font-size:13px;line-height:1.65;color:#C9D4EC">' + esc(a.description) + '</p>' : '') +
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
      if (ASSETS.length && (fresh || force === true)) { renderList(); if (fresh && force !== true) return; }
      if (!ASSETS.length) renderMsg(T('cr_loading', 'Cargando mercado cripto…'));
      fetch('/api/crypto/markets?per_page=100')
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d || !d.assets) throw new Error(d && d.error || 'sin datos');
          ASSETS = d.assets; LOADED_AT = Date.now(); renderList();
        })
        .catch(function () { if (!ASSETS.length) renderMsg(T('cr_err', 'No se pudo cargar el mercado cripto. Reintenta en unos segundos.')); });
    },
    refresh: function () { LOADED_AT = 0; ASSETS = []; window.KhipuCrypto.init(); },
    openDetail: function (id) {
      renderMsg(T('cr_loading', 'Cargando mercado cripto…'));
      fetch('/api/crypto/' + encodeURIComponent(id))
        .then(function (r) { return r.json(); })
        .then(function (a) {
          if (!a || a.error) throw new Error(a && a.error || 'sin datos');
          renderDetail(a);
        })
        .catch(function () { renderMsg(T('cr_err', 'No se pudo cargar el mercado cripto. Reintenta en unos segundos.')); });
    },
  };
})();
