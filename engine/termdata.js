/* ============================================================================
   engine/termdata.js — PANEL DE DATOS de la Terminal (feedback de Fabrizio:
   "te pedí que la terminal tuviera muchas más tablas" + "para muchas decía
   upstream 402 pero no sale nada, necesito ver la info de todos").
   Columna derecha colapsable que se llena SOLA al abrir cualquier empresa
   (hook en _termLoadCell) con tablas reales:
     1. FICHA        — sector, país, fundada, empleados, ingresos, cap, NRS…
     2. PERFIL       — descripción y riesgo geográfico (LOCAL, para TODAS las
                       empresas: nunca queda vacío aunque no haya API)
     3. VALUACIÓN    — P/E, EV/EBITDA, precio objetivo y ratings de analistas
     4. FUNDAMENTALES— serie anual: crec. ingresos, margen bruto/FCF, ROE, D/E
     5. CADENA       — top proveedores y clientes con peso de criticidad
   Fuentes: catálogo local + /api/fundamentals (caché 24h) + /api/findossier.
   Regla: si una API no trae dato (plan sin cobertura / 402 / privada) NUNCA se
   deja la celda vacía ni se muestra el error crudo — se cae al dato local y a
   un mensaje claro y BILINGÜE (ES/EN, window.LANG / localStorage eco_lang).
   ============================================================================ */
(function () {
  'use strict';

  var CUR = null;   // ticker actual

  /* ── i18n local (regla bilingüe ES/EN) ─────────────────────────────────── */
  var I18 = {
    es: {
      title: 'Datos', reopen: 'Datos',
      close: 'Ocultar panel de datos', show: 'Mostrar el panel de datos',
      ph: 'Abre una empresa de la lista y aquí aparecen sus tablas: ficha, perfil, valuación, analistas, fundamentales anuales y su cadena.',
      ficha: 'Ficha', sector: 'Sector', country: 'País', founded: 'Fundada',
      employees: 'Empleados', revenue: 'Ingresos', mktcap: 'Cap. de mercado',
      preipo: 'Pre-IPO', margin: 'Margen', nrsRisk: 'Riesgo NRS',
      links: 'Vínculos', prov: 'prov', clients: 'clientes',
      profile: 'Perfil', geoRisk: 'Riesgo geográfico',
      valuation: 'Valuación & Analistas', loading: 'Cargando…',
      pe: 'P/E (12m)', peTip: 'Precio ÷ ganancias: cuántos años de utilidades cuesta la acción hoy.',
      evebitda: 'EV/EBITDA', evTip: 'Valor de la empresa ÷ ganancia operativa: múltiplo de valuación menos sensible a deuda e impuestos.',
      target: 'Precio objetivo', upside: 'Potencial',
      analysts: 'Analistas', buy: 'compra', hold: 'mantiene', sell: 'vende',
      noMarket: 'Sin datos de mercado en el plan actual — arriba tienes la ficha y el perfil de la empresa.',
      fundamentals: 'Fundamentales anuales', fundSrc: 'fuente: estados financieros',
      noFin: 'Sin estados financieros (empresa privada o sin cobertura en el plan actual).',
      revg: 'Ingr. %', gm: 'M. bruto %', fcf: 'M. FCF %', roe: 'ROE %', de: 'Deuda/Cap',
      dossier: 'Ver dossier financiero completo',
      chain: 'Cadena de suministro', weight: 'peso 1-5', noChain: 'Sin vínculos mapeados.',
      noConn: 'Proveedor no disponible ahora — mostrando el dato local.',
      sup1: 'Proveedor (le vende a esta empresa)', cli1: 'Cliente (le compra a esta empresa)',
    },
    en: {
      title: 'Data', reopen: 'Data',
      close: 'Hide data panel', show: 'Show the data panel',
      ph: 'Open a company from the list and its tables appear here: snapshot, profile, valuation, analysts, annual fundamentals and its chain.',
      ficha: 'Snapshot', sector: 'Sector', country: 'Country', founded: 'Founded',
      employees: 'Employees', revenue: 'Revenue', mktcap: 'Market cap',
      preipo: 'Pre-IPO', margin: 'Margin', nrsRisk: 'NRS risk',
      links: 'Links', prov: 'sup', clients: 'customers',
      profile: 'Profile', geoRisk: 'Geographic risk',
      valuation: 'Valuation & Analysts', loading: 'Loading…',
      pe: 'P/E (TTM)', peTip: 'Price ÷ earnings: how many years of profit the share costs today.',
      evebitda: 'EV/EBITDA', evTip: 'Enterprise value ÷ operating earnings: a valuation multiple less sensitive to debt and taxes.',
      target: 'Price target', upside: 'Upside',
      analysts: 'Analysts', buy: 'buy', hold: 'hold', sell: 'sell',
      noMarket: 'No market data in the current plan — the snapshot and profile above cover this company.',
      fundamentals: 'Annual fundamentals', fundSrc: 'source: financial statements',
      noFin: 'No financial statements (private company or not covered in the current plan).',
      revg: 'Rev. %', gm: 'Gross m. %', fcf: 'FCF m. %', roe: 'ROE %', de: 'Debt/Eq',
      dossier: 'Open the full financial dossier',
      chain: 'Supply chain', weight: 'weight 1-5', noChain: 'No links mapped.',
      noConn: 'Provider unavailable right now — showing local data.',
      sup1: 'Supplier (sells to this company)', cli1: 'Customer (buys from this company)',
    },
  };
  function L() {
    try { return String(window.LANG || localStorage.getItem('eco_lang') || 'es').slice(0, 2) === 'en' ? 'en' : 'es'; }
    catch (e) { return 'es'; }
  }
  function T(k) { var d = I18[L()] || I18.es; return d[k] != null ? d[k] : (I18.es[k] != null ? I18.es[k] : k); }

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function lid(v) { return (typeof v === 'object' && v !== null) ? v.id : v; }
  function fmt(v, suf) { return (v == null || v === '' || Number.isNaN(v)) ? '—' : v + (suf || ''); }

  function ensureStyles() {
    if (document.getElementById('td-styles')) return;
    // Tokens --kt-* de la Terminal (app.html, bloque «TERMINAL rediseño
    // 2026-10-02») → mismo aspecto en tema oscuro/claro y dentro de la Cabina.
    var css = `
#term-data{width:320px;flex:0 0 320px;min-height:0;border-left:1px solid var(--kt-line,rgba(255,255,255,.07));
  background:var(--kt-panel,#10131A);color:var(--kt-ink,#E7E9EF);display:flex;flex-direction:column;overflow:hidden;
  font-family:var(--kt-sans,'Geist','Inter',sans-serif)}
#term-data.closed{display:none}
#td-head{display:flex;align-items:center;gap:8px;min-height:48px;padding:8px 10px 8px 14px;border-bottom:1px solid var(--kt-line,rgba(255,255,255,.07));flex-shrink:0}
#td-title{flex:1;min-width:0;font-size:13.5px;font-weight:650;color:var(--kt-ink,#fff);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#td-title small{display:block;font-size:10.5px;font-weight:650;letter-spacing:.08em;text-transform:uppercase;color:var(--kt-ink-3,#6E7586);margin-bottom:1px}
#td-close{width:30px;height:30px;flex-shrink:0;border-radius:8px;border:1px solid var(--kt-line-2,rgba(255,255,255,.13));background:transparent;
  color:var(--kt-ink-2,#A3A9B8);cursor:pointer;font-size:16px;line-height:1}
#td-close:hover{color:var(--kt-ink,#fff);background:var(--kt-hover,rgba(255,255,255,.04))}
#td-body{flex:1;overflow-y:auto;padding:12px 14px 28px;overscroll-behavior:contain}
.td-sec{margin-bottom:20px}
.td-h{font-size:10.5px;font-weight:650;letter-spacing:.08em;text-transform:uppercase;color:var(--kt-ink-3,#6E7586);margin:0 0 6px;
  padding-bottom:6px;border-bottom:1px solid var(--kt-line,rgba(255,255,255,.07));display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.td-h .u{font-size:10.5px;color:var(--kt-ink-3,#6E7586);letter-spacing:0;text-transform:none;font-weight:500}
.td-kv{display:flex;justify-content:space-between;align-items:baseline;gap:12px;font-size:12.5px;padding:6px 0;border-bottom:1px solid var(--kt-line,rgba(255,255,255,.05))}
.td-kv .k{color:var(--kt-ink-2,#A3A9B8);display:inline-flex;align-items:center;gap:4px}
.td-kv .v{color:var(--kt-ink,#E7E9EF);font-family:var(--kt-mono,'JetBrains Mono',monospace);font-variant-numeric:tabular-nums;font-size:12px;text-align:right}
.td-desc{font-size:12.5px;line-height:1.6;color:var(--kt-ink-2,#A3A9B8)}
.td-geo{font-size:12px;line-height:1.55;color:var(--kt-ink-2,#A3A9B8);margin-top:8px;padding:8px 10px;border-radius:8px;
  background:color-mix(in srgb,var(--kt-warn,#F0A92E) 8%,transparent);border:1px solid color-mix(in srgb,var(--kt-warn,#F0A92E) 25%,transparent)}
.td-geo b{color:var(--kt-warn,#F0A92E);font-weight:650}
.td-tbl{width:100%;border-collapse:collapse;font-size:11.5px;font-family:var(--kt-mono,'JetBrains Mono',monospace);font-variant-numeric:tabular-nums}
.td-tbl th{color:var(--kt-ink-3,#6E7586);font-weight:600;text-align:right;padding:5px 4px;border-bottom:1px solid var(--kt-line-2,rgba(255,255,255,.12));font-size:10.5px}
.td-tbl th:first-child{text-align:left}
.td-tbl td{color:var(--kt-ink,#E7E9EF);text-align:right;padding:5px 4px;border-bottom:1px solid var(--kt-line,rgba(255,255,255,.05))}
.td-tbl td:first-child{text-align:left;color:var(--kt-ink-2,#A3A9B8);font-family:var(--kt-sans,'Geist',sans-serif)}
.td-chain{display:flex;align-items:center;gap:8px;font-size:12.5px;padding:6px 2px;cursor:pointer;border-radius:6px}
.td-chain:hover{background:var(--kt-hover,rgba(255,255,255,.04))}
.td-chain:hover .n{color:var(--kt-ink,#fff)}
.td-chain .n{flex:1;color:var(--kt-ink-2,#A3A9B8);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.td-chain .w{font-family:var(--kt-mono,'JetBrains Mono',monospace);font-size:11px;color:var(--kt-ink-3,#6E7586)}
.td-chain .a{font-family:var(--kt-mono,'JetBrains Mono',monospace);font-size:12px;width:12px;text-align:center}
.td-empty{font-size:12px;color:var(--kt-ink-3,#6E7586);padding:6px 0;line-height:1.55}
.td-rating{display:flex;gap:2px;margin-top:8px;height:6px;border-radius:4px;overflow:hidden}
.td-rating span{height:100%}
.td-btn{width:100%;margin-top:10px;padding:8px;border-radius:8px;border:1px solid var(--kt-line-2,rgba(255,255,255,.13));background:transparent;
  color:var(--kt-ink,#E7E9EF);font:600 12.5px var(--kt-sans,'Geist',sans-serif);cursor:pointer}
.td-btn:hover{background:var(--kt-hover,rgba(255,255,255,.04))}
#td-reopen svg{width:15px;height:15px}
/* pantallas medianas: el panel de datos es un CAJÓN sobre los gráficos */
@media(max-width:1180px){
  #term-data{position:absolute;top:0;right:0;bottom:0;width:min(360px,100%);z-index:12;box-shadow:var(--kt-shadow,0 18px 50px rgba(0,0,0,.55))}
}
@media(max-width:560px){ #term-data{width:100%;border-left:0} }
`;
    var st = document.createElement('style'); st.id = 'td-styles'; st.textContent = css;
    document.head.appendChild(st);
  }

  var ICO = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>';
  var LAST_ID = null;
  function setOpen(open) {
    var panel = document.getElementById('term-data'), btn = document.getElementById('td-reopen');
    if (panel) panel.classList.toggle('closed', !open);
    if (btn) btn.setAttribute('aria-pressed', open ? 'true' : 'false');
    try { localStorage.setItem('kh_termdata', open ? '1' : '0'); } catch (e) {}
  }
  function paintChrome() {
    var btn = document.getElementById('td-reopen');
    if (btn) { btn.innerHTML = ICO + '<span>' + esc(T('reopen')) + '</span>'; btn.title = T('show'); }
    var cl = document.getElementById('td-close');
    if (cl) { cl.title = T('close'); cl.setAttribute('aria-label', T('close')); }
  }

  function mount() {
    ensureStyles();
    if (document.getElementById('term-data')) return true;
    var grid = document.getElementById('term-grid');
    if (!grid || !grid.parentNode) return false;
    // 3ª COLUMNA de la Terminal (fila #term-shell). Antes se colgaba DENTRO de
    // la columna de gráficos y, al llenarse, aplastaba la grilla a 0 px.
    var shell = document.getElementById('term-shell') || grid.parentNode.parentNode || grid.parentNode;
    var panel = document.createElement('aside');
    panel.id = 'term-data';
    panel.innerHTML =
      '<div id="td-head"><span id="td-title"><small>' + esc(T('title')) + '</small>—</span>' +
        '<button type="button" id="td-close" title="' + esc(T('close')) + '" aria-label="' + esc(T('close')) + '">×</button></div>' +
      '<div id="td-body"><div class="td-empty">' + esc(T('ph')) + '</div></div>';
    shell.appendChild(panel);

    // interruptor 📋 Datos en la barra de la Terminal (siempre visible)
    var reopen = document.createElement('button');
    reopen.id = 'td-reopen'; reopen.type = 'button'; reopen.className = 'kt-btn';
    var slot = document.getElementById('term-tb-actions');
    if (slot) slot.appendChild(reopen);
    else { reopen.style.cssText = 'position:absolute;right:10px;top:10px;z-index:8'; grid.parentNode.style.position = 'relative'; grid.parentNode.appendChild(reopen); }
    paintChrome();

    document.getElementById('td-close').onclick = function () { setOpen(false); };
    reopen.onclick = function () { setOpen(document.getElementById('term-data').classList.contains('closed')); };
    var saved = null;
    try { saved = localStorage.getItem('kh_termdata'); } catch (e) {}
    if (saved == null) saved = window.innerWidth < 1180 ? '0' : '1';   // pantallas medianas/teléfono: cerrado por defecto
    setOpen(saved !== '0');
    return true;
  }
  // cambio de idioma: re-pinta los textos y la ficha abierta
  function relabel() {
    if (!document.getElementById('term-data')) return;
    paintChrome();
    if (LAST_ID && CUR) load(LAST_ID, CUR);
    else { var b = document.getElementById('td-body'); if (b) b.innerHTML = '<div class="td-empty">' + esc(T('ph')) + '</div>';
      var tt = document.getElementById('td-title'); if (tt) tt.innerHTML = '<small>' + esc(T('title')) + '</small>—'; }
  }

  // k = etiqueta de confianza (proviene de T(), sin HTML de usuario) → NO se
  // escapa, así el chip "?" (window.explainChip) se renderiza de verdad.
  // v = valor ya formateado (HTML permitido). tip = tooltip opcional.
  function kv(k, v, tip) {
    return '<div class="td-kv"' + (tip ? ' title="' + esc(tip) + '"' : '') +
      '><span class="k">' + k + '</span><span class="v">' + v + '</span></div>';
  }

  function load(nodeId, ticker) {
    if (!mount()) return;
    CUR = ticker; LAST_ID = nodeId;
    var n = (window.NODE_BY_ID || {})[nodeId] || (window.NODES || []).find(function (x) { return x.mkt === ticker; });
    if (!n) return;
    var m = (window.NODE_META || {})[n.id] || {};
    var nrs = null;
    try { if (typeof computeNRS === 'function') nrs = computeNRS(n.id); } catch (e) {}
    var nrsCol = nrs == null ? 'var(--kt-ink-3,#7C87A3)' : nrs >= 60 ? 'var(--kt-down,#FF4D6A)' : nrs >= 35 ? 'var(--kt-warn,#FFB300)' : 'var(--kt-up,#2BE38B)';

    document.getElementById('td-title').innerHTML = '<small>' + esc(T('title')) + ' · ' + esc(ticker) + '</small>' + esc(n.label);
    var body = document.getElementById('td-body');

    // ── 1. FICHA (instantánea, datos locales) ──
    var cadena = chainOf(n.id);
    var nrsChip = window.explainChip ? window.explainChip('nrs') : '';
    var wChip = window.explainChip ? window.explainChip('w') : '';

    // ── 2. PERFIL (local: descripción + riesgo geográfico) — nunca vacío ──
    var descTxt = m.desc || m.description || '';
    var geoTxt = m.geo_risk || m.geoRisk || '';
    var perfilHTML = (descTxt || geoTxt)
      ? '<div class="td-sec"><div class="td-h">' + esc(T('profile')) + '</div>' +
          (descTxt ? '<div class="td-desc">' + esc(descTxt) + '</div>' : '') +
          (geoTxt ? '<div class="td-geo"><b>' + esc(T('geoRisk')) + ':</b> ' + esc(geoTxt) + '</div>' : '') +
        '</div>'
      : '';

    body.innerHTML =
      '<div class="td-sec"><div class="td-h">' + esc(T('ficha')) + '</div>' +
        kv(esc(T('sector')), esc(window.sectorName ? window.sectorName(n.cat, true) : n.cat)) +
        kv(esc(T('country')), esc(n.country || '—')) +
        kv(esc(T('founded')), fmt(m.founded)) +
        kv(esc(T('employees')), m.employees ? Number(m.employees).toLocaleString() : '—') +
        kv(esc(T('revenue')), esc(m.revenue_2025 || '—')) +
        kv(esc(T('mktcap')), m.mktcap_b ? '$' + esc(String(m.mktcap_b)) + 'B' + (window.liveCapDot ? window.liveCapDot(m) : '') : (n.preipo ? T('preipo') : '—')) +
        kv(esc(T('margin')), n.margin != null ? Math.round(n.margin * 100) + '%' : '—') +
        kv(esc(T('nrsRisk')) + nrsChip,
           '<b style="color:' + nrsCol + '">' + fmt(nrs) + '</b>/100') +
        kv(esc(T('links')), cadena.up.length + ' ' + esc(T('prov')) + ' · ' + cadena.down.length + ' ' + esc(T('clients'))) +
      '</div>' +
      perfilHTML +
      '<div class="td-sec" id="td-val"><div class="td-h">' + esc(T('valuation')) + '</div><div class="td-empty">' + esc(T('loading')) + '</div></div>' +
      '<div class="td-sec" id="td-fund"><div class="td-h">' + esc(T('fundamentals')) + ' <span class="u">' + esc(T('fundSrc')) + '</span></div><div class="td-empty">' + esc(T('loading')) + '</div></div>' +
      '<div class="td-sec"><div class="td-h">' + esc(T('chain')) + ' <span class="u">' + esc(T('weight')) + '</span>' +
        wChip + '</div>' + chainHTML(cadena) + '</div>';

    // ── 3. VALUACIÓN & ANALISTAS (API, caché 24h) ──
    fetch((window.BASE || '') + '/api/fundamentals/' + encodeURIComponent(ticker))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var el = document.getElementById('td-val');
        if (!el || CUR !== ticker) return;
        d = d || {};
        var met = (d.metrics && d.metrics[0]) || {};
        var pt = (d.priceTarget && d.priceTarget[0]) || {};
        var rt = (d.ratings && d.ratings[0]) || {};
        var target = pt.targetConsensus || pt.priceTargetAverage || pt.targetMedian || null;
        var q = ((window.MKT || {}).quotes || {})[ticker] || {};
        var upside = (target && q.close) ? Math.round((target / q.close - 1) * 100) : null;
        var b = (rt.analystRatingsStrongBuy || 0) + (rt.analystRatingsBuy || 0);
        var h = rt.analystRatingsHold || 0;
        var s = (rt.analystRatingsSell || 0) + (rt.analystRatingsStrongSell || 0);
        var tot = b + h + s;
        var hasAny = met.peRatio != null || met.enterpriseValueOverEBITDA != null || target != null || tot > 0;
        var html =
          kv(esc(T('pe')), fmt(met.peRatio), T('peTip')) +
          kv(esc(T('evebitda')), fmt(met.enterpriseValueOverEBITDA), T('evTip')) +
          kv(esc(T('target')), target ? '$' + Number(target).toFixed(2) : '—') +
          kv(esc(T('upside')), upside != null ? '<b style="color:' + (upside >= 0 ? 'var(--kt-up,#2BE38B)' : 'var(--kt-down,#FF4D6A)') + '">' + (upside >= 0 ? '+' : '') + upside + '%</b>' : '—');
        if (tot > 0) {
          html += kv(esc(T('analysts')), b + ' ' + esc(T('buy')) + ' · ' + h + ' ' + esc(T('hold')) + ' · ' + s + ' ' + esc(T('sell'))) +
            '<div class="td-rating">' +
              '<span style="width:' + (b / tot * 100) + '%;background:var(--kt-up,#2BE38B)"></span>' +
              '<span style="width:' + (h / tot * 100) + '%;background:var(--kt-warn,#FFB300)"></span>' +
              '<span style="width:' + (s / tot * 100) + '%;background:var(--kt-down,#FF4D6A)"></span>' +
            '</div>';
        }
        // Fallback 402/plan sin cobertura: en vez de dejar la celda vacía o
        // mostrar el error crudo, se explica en lenguaje claro y bilingüe (la
        // ficha y el perfil de arriba ya cubren a esta empresa).
        el.innerHTML = '<div class="td-h">' + esc(T('valuation')) + '</div>' +
          (hasAny ? html : '<div class="td-empty">' + esc(T('noMarket')) + '</div>');
      }).catch(function () {
        var el = document.getElementById('td-val');
        if (!el || CUR !== ticker) return;
        var em = el.querySelector('.td-empty');
        if (em) em.textContent = T('noConn');
      });

    // ── 4. FUNDAMENTALES ANUALES (API findossier, caché 24h) ──
    fetch((window.BASE || '') + '/api/findossier/' + encodeURIComponent(ticker))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var el = document.getElementById('td-fund');
        if (!el || CUR !== ticker) return;
        d = d || {};
        // {available:false, reason:'…upstream 402…'} → nunca mostramos el
        // `reason` crudo, solo un mensaje claro y bilingüe.
        if (!d.available || !(d.years || []).length) {
          var em = el.querySelector('.td-empty');
          if (em) em.textContent = T('noFin');
          else el.innerHTML = '<div class="td-h">' + esc(T('fundamentals')) + '</div><div class="td-empty">' + esc(T('noFin')) + '</div>';
          return;
        }
        var rows = [
          [T('revg'), d.revenue_growth], [T('gm'), d.gross_margin],
          [T('fcf'), d.fcf_margin], [T('roe'), d.roe], [T('de'), d.de_ratio],
        ];
        var years = d.years.slice(-5);
        var off = d.years.length - years.length;
        el.innerHTML = '<div class="td-h">' + esc(T('fundamentals')) + ' <span class="u">' + esc(years[0]) + '–' + esc(years[years.length - 1]) + '</span></div>' +
          '<table class="td-tbl"><tr><th></th>' + years.map(function (y) { return '<th>' + esc(String(y).slice(2)) + '</th>'; }).join('') + '</tr>' +
          rows.map(function (r) {
            return '<tr><td>' + esc(r[0]) + '</td>' + years.map(function (_, i) {
              var v = (r[1] || [])[off + i];
              return '<td>' + (v == null ? '—' : v) + '</td>';
            }).join('') + '</tr>';
          }).join('') + '</table>' +
          '<button type="button" class="td-btn" onclick="window.openFinCard&&window.openFinCard(\'' + esc(ticker) + '\')">' + esc(T('dossier')) + '</button>';
      }).catch(function () {
        var el = document.getElementById('td-fund');
        if (!el || CUR !== ticker) return;
        var em = el.querySelector('.td-empty');
        if (em) em.textContent = T('noConn');
      });
  }

  function chainOf(id) {
    var up = [], down = [];
    (window.LINKS || []).forEach(function (l) {
      var s = lid(l.source), t = lid(l.target);
      if (t === id && window.NODE_BY_ID[s]) up.push({ n: window.NODE_BY_ID[s], w: l.w || 1 });
      if (s === id && window.NODE_BY_ID[t]) down.push({ n: window.NODE_BY_ID[t], w: l.w || 1 });
    });
    up.sort(function (a, b) { return b.w - a.w; });
    down.sort(function (a, b) { return b.w - a.w; });
    return { up: up, down: down };
  }

  function chainHTML(c) {
    var row = function (x, arrow) {
      return '<div class="td-chain" onclick="' + (x.n.mkt ? 'window._termOpenTicker(\'' + esc(x.n.mkt) + '\')' : 'window.openXRay&&window.openXRay(\'' + esc(x.n.id) + '\')') + '">' +
        '<span class="a" style="color:' + (arrow === '←' ? 'var(--kt-ink-2,#A3A9B8)' : 'var(--kt-accent,#8B8CF6)') + '" title="' + esc(arrow === '←' ? T('sup1') : T('cli1')) + '">' + arrow + '</span>' +
        '<span class="n">' + esc(x.n.label) + '</span><span class="w">w' + x.w + '</span></div>';
    };
    var html = '';
    if (c.up.length) html += c.up.slice(0, 5).map(function (x) { return row(x, '←'); }).join('');
    if (c.down.length) html += c.down.slice(0, 5).map(function (x) { return row(x, '→'); }).join('');
    return html || '<div class="td-empty">' + esc(T('noChain')) + '</div>';
  }

  window.TermData = { load: load, mount: mount, relabel: relabel, open: function () { if (mount()) setOpen(true); } };
})();
