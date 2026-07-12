/* ============================================================================
   engine/crypto.js — Pestaña ₿ Cripto (Fase 1 módulo de datos + Expediente).
   - Datos VIVOS: /api/crypto/* (server → core/providers/coingecko.py).
   - Capa ESTÁTICA: window.CRYPTO_INTEL + window.CRYPTO_CATS
     (nodes/crypto_intel*.js, expediente jul-2026, refrescar cada 3-6 meses).
   Vistas (elección de Fabrizio 2026-07-12, maqueta "Burbujas vivas"):
     🫧 Burbujas — canvas con física suave: tamaño = market cap, color = 24h%,
        anillo rojo punteado = ⚠ del expediente. Tap = tarjeta con "Ver ficha".
     ☰ Lista — top 100 con filtros por tesis del expediente (badges 📋/⚠).
     Detalle — gráfico 90d + Expediente Khipus de 6 bloques + banner ⚠.
   Bilingüe ES/EN (regla del proyecto).
   ============================================================================ */
(function () {
  'use strict';

  var LOADED_AT = 0;      // timestamp del último fetch de la lista
  var ASSETS = [];        // CryptoAsset[] vivos (top 100)
  var CHART = null;       // instancia Chart.js de la vista detalle
  var VIEW = null;        // 'bubbles' | 'list' (persistido)
  var FILTER = null;      // null | catKey
  var BUB = null;         // estado del canvas de burbujas {ctx, items, raf…}

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
    try { VIEW = localStorage.getItem('kh_cryptoview') || 'bubbles'; } catch (e) { VIEW = 'bubbles'; }
    if (VIEW !== 'list' && VIEW !== 'bubbles') VIEW = 'bubbles';   // migra 'map' viejo
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
  function pctCol(p) {
    if (p == null || Math.abs(p) < 0.05) return '#5C6784';
    var t = Math.min(Math.abs(p) / 6, 1);
    return p > 0
      ? 'rgb(' + Math.round(43 - 20 * t) + ',227,' + Math.round(139 - 60 * t) + ')'
      : 'rgb(255,' + Math.round(77 + 40 * (1 - t)) + ',' + Math.round(106 + 40 * (1 - t)) + ')';
  }
  function esc(s) { return String(s == null ? '' : s).replace(/[<>&"]/g, function (c) { return { '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c]; }); }

  function panel() { return document.getElementById('crypto-panel'); }
  function filtered() {
    if (!FILTER) return ASSETS;
    return ASSETS.filter(function (a) { var it = intelOf(a); return it && (it.tags || [it.cat]).indexOf(FILTER) >= 0; });
  }

  // ── cabecera común (título + conmutador de vista + refresh) ──
  function headerHTML() {
    var v = view();
    var seg = function (id, txt, on) {
      return '<button onclick="window.KhipuCrypto.setView(\'' + id + '\')" style="padding:5px 13px;border-radius:7px;cursor:pointer;font-size:12px;font-weight:600;' +
        'border:1px solid ' + (on ? 'rgba(0,224,255,.45)' : 'transparent') + ';background:' + (on ? 'rgba(0,224,255,.12)' : 'none') + ';color:' + (on ? '#00E0FF' : '#7C87A3') + '">' + txt + '</button>';
    };
    return '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:4px">' +
      '<h2 style="margin:0;font-size:19px">' + T('cr_title', '₿ Cripto') + '</h2>' +
      '<div style="display:flex;gap:2px;background:rgba(21,28,45,.6);border-radius:9px;padding:2px">' +
        seg('bubbles', '🫧 ' + T('cr_view_bub', 'Burbujas'), v === 'bubbles') + seg('list', '☰ ' + T('cr_view_list', 'Lista'), v === 'list') + '</div>' +
      '<button onclick="window.KhipuCrypto.refresh()" title="Refresh" style="margin-left:auto;padding:5px 12px;border-radius:7px;border:1px solid rgba(0,224,255,.3);background:rgba(0,224,255,.08);color:#00E0FF;cursor:pointer;font-size:12px">⟳</button></div>' +
      '<div style="color:#7C87A3;font-size:12px;margin-bottom:10px">' + T('cr_sub', 'Datos en vivo de CoinGecko · clic en una moneda para ver su detalle') + '</div>';
  }

  // chips de categoría (filtran ambas vistas) + blurb educativo al filtrar
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
    var blurb = '';
    if (FILTER) {
      var ci = catInfo(FILTER);
      if (ci) blurb = '<div style="margin:8px 0 0;padding:8px 13px;border-radius:9px;background:rgba(0,224,255,.06);border:1px solid rgba(0,224,255,.18);color:#9AB8D8;font-size:12px;line-height:1.5">' +
        ci.icon + ' ' + esc(lang() === 'en' ? (ci.ben || '') : (ci.bes || '')) + '</div>';
    }
    return '<div style="display:flex;gap:6px;flex-wrap:wrap">' + h + '</div>' + blurb;
  }

  function badges(a) {
    var it = intelOf(a); var h = '';
    if (it) h += '<span title="' + T('cr_dossier', 'Expediente') + '" style="font-size:10px">📋</span>';
    if (it && it.warn) h += '<span title="' + esc(lang() === 'en' ? it.warn.en : it.warn.es) + '" style="font-size:10px">⚠️</span>';
    return h;
  }

  function baseCSS() {
    return '<style>#crypto-panel td{padding:8px 6px;border-bottom:1px solid rgba(122,158,255,.08)}' +
      '#crypto-panel tbody tr:hover{background:rgba(0,224,255,.05)}' +
      '@media(max-width:760px){#crypto-panel .cr-hide-m{display:none}}</style>';
  }

  // ── vista LISTA ──
  function renderList() {
    stopBubbles();
    var p = panel(); if (!p) return;
    var list = filtered();
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
        '<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:12.5px">' +
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

  // ── vista BURBUJAS (elección de Fabrizio — estilo CryptoBubbles) ──
  function stopBubbles() {
    if (BUB && BUB.raf) cancelAnimationFrame(BUB.raf);
    BUB = null;
  }
  function renderBubbles() {
    stopBubbles();
    var p = panel(); if (!p) return;
    p.innerHTML =
      '<div style="max-width:1100px;margin:0 auto;padding:20px 16px 40px;display:flex;flex-direction:column;height:calc(100% - 10px);box-sizing:border-box">' +
        headerHTML() + chipsHTML() +
        '<div id="cr-bub-stage" style="position:relative;flex:1;min-height:340px;margin-top:12px;border:1px solid rgba(122,158,255,.14);' +
          'border-radius:14px;background:radial-gradient(700px 380px at 50% -80px,#0B1428 0%,#05070E 60%);overflow:hidden">' +
          '<canvas id="cr-bub" style="display:block;width:100%;height:100%;cursor:pointer;touch-action:none"></canvas>' +
          '<div id="cr-bub-tip" style="position:absolute;display:none;z-index:5;background:rgba(8,14,26,.97);border:1px solid rgba(0,224,255,.35);' +
            'border-radius:10px;padding:10px 13px;font-size:12px;box-shadow:0 8px 30px rgba(0,0,0,.5);max-width:230px"></div>' +
          '<div style="position:absolute;left:12px;bottom:9px;font-size:10px;color:#5C6784;pointer-events:none">' +
            T('cr_bub_hint', 'tamaño = capitalización · color = 24h · toca una burbuja') + '</div>' +
        '</div>' +
        '<div style="margin-top:10px;color:#5C6784;font-size:10.5px">' + T('cr_disclaimer', 'Contexto informativo, no es asesoría de inversión. Capa de análisis: jul 2026 · precios en vivo de CoinGecko.') + '</div>' +
      '</div>';
    initBubbles();
  }

  function initBubbles() {
    var cv = document.getElementById('cr-bub');
    var tip = document.getElementById('cr-bub-tip');
    var stage = document.getElementById('cr-bub-stage');
    if (!cv || !ASSETS.length) return;
    var ctx = cv.getContext('2d');
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    function fit() {
      var r = stage.getBoundingClientRect();
      cv.width = Math.max(1, r.width * dpr); cv.height = Math.max(1, r.height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    fit();
    var list = filtered().slice(0, 100);
    if (!list.length) return;
    var W = function () { return cv.clientWidth || 300; }, H = function () { return cv.clientHeight || 300; };
    var maxM = Math.sqrt(list[0].market_cap || 1);
    var small = W() < 520;
    var items = list.map(function (a) {
      var rel = Math.sqrt(Math.max(a.market_cap || 1, 1)) / maxM;
      var r = (small ? 9 : 12) + rel * (small ? 34 : 56);
      return { a: a, it: intelOf(a), r: r,
        x: r + Math.random() * Math.max(20, W() - 2 * r), y: r + Math.random() * Math.max(20, H() - 2 * r),
        vx: (Math.random() - .5) * .35, vy: (Math.random() - .5) * .35 };
    });
    var reduce = false;
    try { reduce = matchMedia('(prefers-reduced-motion:reduce)').matches; } catch (e) {}
    var drag = null;
    function step() {
      var w = W(), h = H();
      for (var i = 0; i < items.length; i++) {
        var b = items[i]; if (b === drag) continue;
        b.x += b.vx; b.y += b.vy; b.vx *= .995; b.vy *= .995;
        if (b.x < b.r) { b.x = b.r; b.vx = Math.abs(b.vx); } if (b.x > w - b.r) { b.x = w - b.r; b.vx = -Math.abs(b.vx); }
        if (b.y < b.r) { b.y = b.r; b.vy = Math.abs(b.vy); } if (b.y > h - b.r) { b.y = h - b.r; b.vy = -Math.abs(b.vy); }
      }
      for (var i2 = 0; i2 < items.length; i2++) for (var j = i2 + 1; j < items.length; j++) {
        var A = items[i2], B = items[j];
        var dx = B.x - A.x, dy = B.y - A.y, d = Math.sqrt(dx * dx + dy * dy) || 1, min = A.r + B.r + 1.5;
        if (d < min) {
          var f = (min - d) / d * .5, fx = dx * f, fy = dy * f;
          A.x -= fx * .5; A.y -= fy * .5; B.x += fx * .5; B.y += fy * .5;
          A.vx -= fx * .02; A.vy -= fy * .02; B.vx += fx * .02; B.vy += fy * .02;
        }
      }
    }
    function draw() {
      var w = W(), h = H(); ctx.clearRect(0, 0, w, h);
      for (var i = 0; i < items.length; i++) {
        var b = items[i], a = b.a, col = pctCol(a.change_24h_pct);
        ctx.save();
        ctx.shadowColor = col; ctx.shadowBlur = Math.min(24, Math.abs(a.change_24h_pct || 0) * 4 + 5);
        var g = ctx.createRadialGradient(b.x - b.r * .3, b.y - b.r * .35, b.r * .1, b.x, b.y, b.r);
        g.addColorStop(0, 'rgba(20,30,52,.95)'); g.addColorStop(1, 'rgba(8,12,24,.92)');
        ctx.beginPath(); ctx.arc(b.x, b.y, b.r, 0, 7); ctx.fillStyle = g; ctx.fill();
        ctx.lineWidth = 2; ctx.strokeStyle = col; ctx.stroke();
        ctx.restore();
        if (b.it && b.it.warn) {   // anillo rojo punteado del expediente
          ctx.save(); ctx.strokeStyle = '#FF4D6A'; ctx.lineWidth = 1.2; ctx.setLineDash([4, 4]);
          ctx.beginPath(); ctx.arc(b.x, b.y, b.r + 3.5, 0, 7); ctx.stroke(); ctx.restore();
        }
        ctx.fillStyle = '#E8EDFB'; ctx.textAlign = 'center';
        ctx.font = '700 ' + Math.max(8, b.r * .38) + 'px ui-monospace,Consolas,monospace';
        ctx.fillText(a.symbol || '', b.x, b.y + 1);
        if (b.r > 22) {
          ctx.fillStyle = col; ctx.font = '600 ' + Math.max(8, b.r * .25) + 'px ui-monospace,monospace';
          var pc = a.change_24h_pct;
          ctx.fillText(pc != null ? (pc > 0 ? '+' : '') + pc.toFixed(1) + '%' : '', b.x, b.y + b.r * .44);
        }
      }
    }
    function loop() {
      if (!BUB || BUB.cv !== cv) return;                 // vista cambiada
      if (!document.hidden && cv.offsetParent !== null) { // solo si visible
        if (!reduce) step();
        draw();
      }
      BUB.raf = requestAnimationFrame(loop);
    }
    BUB = { cv: cv, raf: 0 };
    loop();
    var onResize = function () { fit(); };
    window.addEventListener('resize', onResize);

    function pick(x, y) {
      for (var i = items.length - 1; i >= 0; i--) {
        var b = items[i];
        if (Math.sqrt((b.x - x) * (b.x - x) + (b.y - y) * (b.y - y)) <= b.r + 2) return b;
      }
      return null;
    }
    function showTip(b, x, y) {
      var a = b.a, col = pctCol(a.change_24h_pct);
      tip.innerHTML = '<b style="font-size:13px">' + esc(a.name) + '</b> <span style="color:#7C87A3">' + esc(a.symbol) + '</span><br>' +
        '<span style="font-weight:700">' + fmtPrice(a.price) + '</span> · <span style="color:' + col + ';font-weight:600">' +
        (a.change_24h_pct != null ? (a.change_24h_pct > 0 ? '+' : '') + a.change_24h_pct.toFixed(2) + '%' : '—') + '</span>' +
        '<span style="color:#7C87A3"> · ' + fmtBig(a.market_cap) + '</span>' +
        (b.it && b.it.warn ? '<div style="color:#FF8FA3;font-size:11px;margin-top:3px">' + esc(lang() === 'en' ? b.it.warn.en : b.it.warn.es) + '</div>' : '') +
        '<button onclick="window.KhipuCrypto.openDetail(\'' + esc(a.id) + '\')" style="margin-top:7px;width:100%;padding:5px 0;border-radius:7px;' +
          'border:1px solid rgba(0,224,255,.4);background:rgba(0,224,255,.1);color:#00E0FF;cursor:pointer;font-size:11.5px;font-weight:600">📋 ' +
          T('cr_open_card', 'Ver ficha completa') + '</button>';
      tip.style.display = 'block';
      var r = stage.getBoundingClientRect();
      tip.style.left = Math.min(x + 14, Math.max(6, r.width - 240)) + 'px';
      tip.style.top = Math.max(6, Math.min(y - 40, r.height - 130)) + 'px';
      clearTimeout(tip._t); tip._t = setTimeout(function () { tip.style.display = 'none'; }, 5000);
    }
    cv.addEventListener('pointerdown', function (e) {
      var r = cv.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
      var b = pick(x, y);
      if (b) { drag = b; try { cv.setPointerCapture(e.pointerId); } catch (err) {} showTip(b, x, y); }
      else tip.style.display = 'none';
    });
    cv.addEventListener('pointermove', function (e) {
      if (!drag) return;
      var r = cv.getBoundingClientRect();
      drag.x = e.clientX - r.left; drag.y = e.clientY - r.top; drag.vx = 0; drag.vy = 0;
    });
    cv.addEventListener('pointerup', function () { drag = null; });
  }

  function renderCurrent() { if (view() === 'bubbles') renderBubbles(); else renderList(); }

  function renderMsg(html) {
    stopBubbles();
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
    stopBubbles();
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
          if (!ASSETS.length) renderMsg(T('cr_err', 'No se pudo cargar el mercado cripto. Reintenta en unos segundos.'));
        });
    },
    refresh: function () { LOADED_AT = 0; ASSETS = []; window.KhipuCrypto.init(); },
    back: function () { window.KhipuCrypto.init(true); },
    setView: function (v) {
      VIEW = v === 'list' ? 'list' : 'bubbles';
      try { localStorage.setItem('kh_cryptoview', VIEW); } catch (e) {}
      renderCurrent();
    },
    setFilter: function (k) { FILTER = k || null; renderCurrent(); },
    stop: stopBubbles,
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
