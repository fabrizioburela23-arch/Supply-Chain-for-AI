/* ============================================================================
   engine/termdata.js — PANEL DE DATOS de la Terminal (feedback de Fabrizio:
   "te pedí que la terminal tuviera muchas más tablas").
   Columna derecha colapsable que se llena SOLA al abrir cualquier empresa
   (hook en _termLoadCell) con 4 tablas reales:
     1. FICHA        — sector, país, fundada, empleados, ingresos, cap, NRS…
     2. VALUACIÓN    — P/E, EV/EBITDA, precio objetivo y ratings de analistas
     3. FUNDAMENTALES— serie anual: crec. ingresos, margen bruto/FCF, ROE, D/E
     4. CADENA       — top proveedores y clientes con peso de criticidad
   Fuentes: catálogo local + /api/fundamentals (caché 24h) + /api/findossier.
   ============================================================================ */
(function () {
  'use strict';

  var CUR = null;   // ticker actual

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function lid(v) { return (typeof v === 'object' && v !== null) ? v.id : v; }
  function fmt(v, suf) { return (v == null || v === '' || Number.isNaN(v)) ? '—' : v + (suf || ''); }

  function ensureStyles() {
    if (document.getElementById('td-styles')) return;
    var css = `
#term-data{width:308px;min-width:308px;border-left:1px solid rgba(255,255,255,.07);background:rgba(4,6,10,.97);
  display:flex;flex-direction:column;overflow:hidden;font-family:'Geist','Inter',sans-serif}
#term-data.closed{display:none}
#td-head{display:flex;align-items:center;gap:8px;padding:10px 12px;border-bottom:1px solid rgba(255,255,255,.07);flex-shrink:0}
#td-title{font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:700;color:#fff;flex:1;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#td-close{width:22px;height:22px;border-radius:3px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.05);
  color:rgba(255,255,255,.5);cursor:pointer;font-size:11px;line-height:1}
#td-body{flex:1;overflow-y:auto;padding:10px 12px 30px}
#td-body::-webkit-scrollbar{width:5px}
#td-body::-webkit-scrollbar-thumb{background:rgba(255,255,255,.12);border-radius:3px}
.td-sec{margin-bottom:16px}
.td-h{font-size:9.5px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#5b8ab8;margin:0 0 7px;
  display:flex;justify-content:space-between;align-items:baseline}
.td-h .u{font-size:8.5px;color:rgba(255,255,255,.25);letter-spacing:.04em;text-transform:none}
.td-kv{display:flex;justify-content:space-between;gap:10px;font-size:11.5px;padding:4px 0;border-bottom:1px solid rgba(255,255,255,.04)}
.td-kv .k{color:rgba(255,255,255,.45)}
.td-kv .v{color:#e8edf5;font-family:'JetBrains Mono',monospace;font-size:11px;text-align:right}
.td-tbl{width:100%;border-collapse:collapse;font-size:10px;font-family:'JetBrains Mono',monospace}
.td-tbl th{color:#5b8ab8;font-weight:600;text-align:right;padding:3px 4px;border-bottom:1px solid rgba(255,255,255,.1);font-size:9px}
.td-tbl th:first-child{text-align:left}
.td-tbl td{color:#cfe0ee;text-align:right;padding:3px 4px;border-bottom:1px solid rgba(255,255,255,.04)}
.td-tbl td:first-child{text-align:left;color:rgba(255,255,255,.5)}
.td-chain{display:flex;align-items:center;gap:7px;font-size:11px;padding:3.5px 0;cursor:pointer}
.td-chain:hover .n{color:#00E0FF}
.td-chain .n{flex:1;color:#cfe0ee;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.td-chain .w{font-family:'JetBrains Mono',monospace;font-size:9.5px;color:#5b8ab8}
.td-empty{font-size:11px;color:rgba(255,255,255,.3);font-style:italic;padding:6px 0}
.td-rating{display:flex;gap:3px;margin-top:6px;height:8px;border-radius:4px;overflow:hidden}
.td-rating span{height:100%}
#td-reopen{position:absolute;right:10px;top:10px;z-index:8;padding:6px 12px;border-radius:8px;cursor:pointer;
  border:1px solid rgba(0,224,255,.35);background:rgba(8,14,24,.9);color:#00E0FF;font-size:11px;font-weight:700;display:none}
/* MÓVIL: el panel de datos pasa a overlay de pantalla completa, la lista de
   empresas se angosta y el grid usa una sola columna (auditoría 375px) */
@media(max-width:760px){
  #term-data{position:absolute;inset:0;width:100%;min-width:0;z-index:12}
  #term-sidebar{width:150px!important;min-width:150px!important}
  #term-grid{grid-template-columns:1fr!important}
}
`;
    var st = document.createElement('style'); st.id = 'td-styles'; st.textContent = css;
    document.head.appendChild(st);
  }

  function mount() {
    ensureStyles();
    if (document.getElementById('term-data')) return true;
    var grid = document.getElementById('term-grid');
    if (!grid || !grid.parentNode) return false;
    var panel = document.createElement('div');
    panel.id = 'term-data';
    panel.innerHTML =
      '<div id="td-head"><span id="td-title">📋 Datos</span>' +
        '<button id="td-close" title="Ocultar panel de datos">✕</button></div>' +
      '<div id="td-body"><div class="td-empty">Abre una empresa de la lista y aquí aparecen sus tablas: ficha, valuación, analistas, fundamentales anuales y su cadena.</div></div>';
    grid.parentNode.appendChild(panel);

    var reopen = document.createElement('button');
    reopen.id = 'td-reopen';
    reopen.textContent = '📋 Datos';
    reopen.title = 'Mostrar el panel de datos';
    grid.parentNode.style.position = 'relative';
    grid.parentNode.appendChild(reopen);

    var setOpen = function (open) {
      panel.classList.toggle('closed', !open);
      reopen.style.display = open ? 'none' : 'block';
      try { localStorage.setItem('kh_termdata', open ? '1' : '0'); } catch (e) {}
    };
    document.getElementById('td-close').onclick = function () { setOpen(false); };
    reopen.onclick = function () { setOpen(true); };
    var saved = null;
    try { saved = localStorage.getItem('kh_termdata'); } catch (e) {}
    if (saved == null) saved = window.innerWidth < 760 ? '0' : '1';   // móvil: cerrado por defecto
    setOpen(saved !== '0');
    return true;
  }

  function kv(k, v) { return '<div class="td-kv"><span class="k">' + esc(k) + '</span><span class="v">' + v + '</span></div>'; }

  function load(nodeId, ticker) {
    if (!mount()) return;
    CUR = ticker;
    var n = (window.NODE_BY_ID || {})[nodeId] || (window.NODES || []).find(function (x) { return x.mkt === ticker; });
    if (!n) return;
    var m = (window.NODE_META || {})[n.id] || {};
    var nrs = null;
    try { if (typeof computeNRS === 'function') nrs = computeNRS(n.id); } catch (e) {}
    var nrsCol = nrs == null ? '#7C87A3' : nrs >= 60 ? '#FF4D6A' : nrs >= 35 ? '#FFB300' : '#2BE38B';

    document.getElementById('td-title').textContent = '📋 ' + n.label;
    var body = document.getElementById('td-body');

    // ── 1. FICHA (instantánea, datos locales) ──
    var cadena = chainOf(n.id);
    body.innerHTML =
      '<div class="td-sec"><div class="td-h">Ficha</div>' +
        kv('Sector', esc((window.SECTORS9 && window.SECTORS9[(window.CAT_TO_SECTOR || {})[n.cat]] || {}).label || n.cat)) +
        kv('País', esc(n.country || '—')) +
        kv('Fundada', fmt(m.founded)) +
        kv('Empleados', m.employees ? Number(m.employees).toLocaleString() : '—') +
        kv('Ingresos', esc(m.revenue_2025 || '—')) +
        kv('Market cap', m.mktcap_b ? '$' + m.mktcap_b + 'B' : (n.preipo ? 'Pre-IPO' : '—')) +
        kv('Margen', n.margin != null ? Math.round(n.margin * 100) + '%' : '—') +
        kv('Riesgo NRS' + (window.explainChip ? window.explainChip('nrs') : ''),
           '<b style="color:' + nrsCol + '">' + fmt(nrs) + '</b>/100') +
        kv('Vínculos', cadena.up.length + ' prov · ' + cadena.down.length + ' clientes') +
      '</div>' +
      '<div class="td-sec" id="td-val"><div class="td-h">Valuación & Analistas</div><div class="td-empty">Cargando…</div></div>' +
      '<div class="td-sec" id="td-fund"><div class="td-h">Fundamentales anuales <span class="u">fuente: estados financieros</span></div><div class="td-empty">Cargando…</div></div>' +
      '<div class="td-sec"><div class="td-h">Cadena de suministro <span class="u">peso 1-5</span>' +
        (window.explainChip ? window.explainChip('w') : '') + '</div>' + chainHTML(cadena) + '</div>';

    // ── 2. VALUACIÓN & ANALISTAS (API, caché 24h) ──
    fetch((window.BASE || '') + '/api/fundamentals/' + encodeURIComponent(ticker))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var el = document.getElementById('td-val');
        if (!el || CUR !== ticker) return;
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
        var html =
          kv('P/E (TTM)', fmt(met.peRatio)) +
          kv('EV/EBITDA', fmt(met.enterpriseValueOverEBITDA)) +
          kv('Precio objetivo', target ? '$' + Number(target).toFixed(2) : '—') +
          kv('Upside', upside != null ? '<b style="color:' + (upside >= 0 ? '#2BE38B' : '#FF4D6A') + '">' + (upside >= 0 ? '+' : '') + upside + '%</b>' : '—');
        if (tot > 0) {
          html += kv('Analistas', b + ' compra · ' + h + ' mantiene · ' + s + ' vende') +
            '<div class="td-rating">' +
              '<span style="width:' + (b / tot * 100) + '%;background:#2BE38B"></span>' +
              '<span style="width:' + (h / tot * 100) + '%;background:#FFB300"></span>' +
              '<span style="width:' + (s / tot * 100) + '%;background:#FF4D6A"></span>' +
            '</div>';
        }
        el.innerHTML = '<div class="td-h">Valuación & Analistas</div>' +
          (html.indexOf('—') === -1 || met.peRatio != null || target ? html : '<div class="td-empty">Sin datos de mercado para este ticker.</div>');
      }).catch(function () {
        var el = document.getElementById('td-val');
        if (el && CUR === ticker) el.querySelector('.td-empty').textContent = 'Sin conexión con el proveedor.';
      });

    // ── 3. FUNDAMENTALES ANUALES (API findossier, caché 24h) ──
    fetch((window.BASE || '') + '/api/findossier/' + encodeURIComponent(ticker))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var el = document.getElementById('td-fund');
        if (!el || CUR !== ticker) return;
        if (!d.available || !(d.years || []).length) {
          el.querySelector('.td-empty').textContent = 'Sin estados financieros (empresa privada o sin cobertura).';
          return;
        }
        var rows = [
          ['Ingr. %', d.revenue_growth], ['M. bruto %', d.gross_margin],
          ['M. FCF %', d.fcf_margin], ['ROE %', d.roe], ['Deuda/Cap', d.de_ratio],
        ];
        var years = d.years.slice(-5);
        var off = d.years.length - years.length;
        el.innerHTML = '<div class="td-h">Fundamentales anuales <span class="u">' + esc(years[0]) + '–' + esc(years[years.length - 1]) + '</span></div>' +
          '<table class="td-tbl"><tr><th></th>' + years.map(function (y) { return '<th>' + esc(String(y).slice(2)) + '</th>'; }).join('') + '</tr>' +
          rows.map(function (r) {
            return '<tr><td>' + esc(r[0]) + '</td>' + years.map(function (_, i) {
              var v = (r[1] || [])[off + i];
              return '<td>' + (v == null ? '—' : v) + '</td>';
            }).join('') + '</tr>';
          }).join('') + '</table>' +
          '<div style="margin-top:7px"><button onclick="window.openFinCard&&window.openFinCard(\'' + esc(ticker) + '\')" ' +
            'style="width:100%;padding:5px;border-radius:4px;border:1px solid rgba(0,224,255,.3);background:rgba(0,224,255,.07);' +
            'color:#00E0FF;font-size:10px;font-weight:700;cursor:pointer;letter-spacing:.05em">📊 VER DOSSIER GRÁFICO</button></div>';
      }).catch(function () {
        var el = document.getElementById('td-fund');
        if (el && CUR === ticker) el.querySelector('.td-empty').textContent = 'Sin conexión con el proveedor.';
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
      var tk = x.n.mkt || x.n.id;
      return '<div class="td-chain" onclick="' + (x.n.mkt ? 'window._termOpenTicker(\'' + esc(x.n.mkt) + '\')' : 'window.openXRay&&window.openXRay(\'' + esc(x.n.id) + '\')') + '">' +
        '<span style="color:' + (arrow === '←' ? '#2BE38B' : '#f97316') + ';font-family:monospace">' + arrow + '</span>' +
        '<span class="n">' + esc(x.n.label) + '</span><span class="w">w' + x.w + '</span></div>';
    };
    var html = '';
    if (c.up.length) html += c.up.slice(0, 5).map(function (x) { return row(x, '←'); }).join('');
    if (c.down.length) html += c.down.slice(0, 5).map(function (x) { return row(x, '→'); }).join('');
    return html || '<div class="td-empty">Sin vínculos mapeados.</div>';
  }

  window.TermData = { load: load, mount: mount };
})();
