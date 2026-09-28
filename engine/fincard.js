/* ============================================================================
   engine/fincard.js — DOSSIER FINANCIERO de una empresa (Etapa G, 2026-07-11)
   Estilo investingvisuals que pidió Fabrizio: una tarjeta con small-multiples
   de indicadores reales — crecimiento de ingresos, dilución, free cash flow,
   acción, valuación EV/Ventas, deuda/capital, márgenes y ROE.

   window.openFinCard(idOrTicker) — overlay NEXUS con 8 mini-gráficos Chart.js.
   Datos: /api/fundamentals/<t> (FMP anual, caché 24h) + /api/candles/<t>.
   Sin FMP_KEY muestra un aviso claro (no un error feo).
   ============================================================================ */
(function () {
  'use strict';

  var NEON = '#00E0FF', DOWN = '#FF4D6A', UP = '#2BE38B', INK = '#9BA6C4';
  var charts = [];

  // bilingüe (regla del proyecto): idioma activo = window.LANG → eco_lang
  function isEn() { var l = window.LANG; if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = null; } } return l === 'en'; }
  function L(es, en) { return isEn() ? en : es; }

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  function ensureStyles() {
    if (document.getElementById('fincard-styles')) return;
    var css = `
#fc-ov{position:fixed;inset:0;z-index:6500;display:none;align-items:center;justify-content:center;
  background:rgba(3,6,12,.7);backdrop-filter:blur(4px);font-family:'Inter',system-ui,sans-serif}
#fc-ov.show{display:flex}
#fc{width:min(1060px,96vw);max-height:92vh;overflow-y:auto;border-radius:18px;color:#E8EDFB;
  background:radial-gradient(1000px 500px at 50% -10%,#0B1222 0%,#06090F 60%);
  border:1px solid rgba(122,158,255,.2);box-shadow:0 30px 80px rgba(0,0,0,.6);padding:22px 24px}
#fc .fc-hd{display:flex;align-items:baseline;gap:12px;margin-bottom:4px;flex-wrap:wrap}
#fc .fc-name{font-size:22px;font-weight:750}
#fc .fc-tk{font-family:'JetBrains Mono',monospace;font-size:12px;color:#7C87A3}
#fc .fc-close{margin-left:auto;width:32px;height:32px;border-radius:9px;cursor:pointer;
  border:1px solid rgba(122,158,255,.2);background:rgba(21,28,45,.7);color:#7C87A3;font-size:16px}
#fc .fc-close:hover{color:#E8EDFB}
#fc .fc-sub{font-size:11px;color:#5b6580;margin-bottom:16px}
#fc .fc-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
#fc .fc-cell{border:1px solid rgba(122,158,255,.14);border-radius:13px;background:rgba(11,18,34,.55);padding:13px 14px}
#fc .fc-t{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#9BA6C4;
  display:flex;align-items:center;gap:7px;margin-bottom:2px}
#fc .fc-d{font-size:9.5px;color:#5b6580;margin-bottom:8px}
#fc .fc-cv{position:relative;height:130px}
#fc .fc-note{padding:36px 10px;text-align:center;color:#7C87A3;font-size:12.5px}
#fc .fc-foot{margin-top:14px;font-size:9.5px;color:#5b6580;display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px}
`;
    var st = document.createElement('style'); st.id = 'fincard-styles'; st.textContent = css;
    document.head.appendChild(st);
  }

  function ensureShell() {
    ensureStyles();
    var ov = document.getElementById('fc-ov');
    if (ov) return ov;
    ov = document.createElement('div');
    ov.id = 'fc-ov';
    ov.innerHTML = '<div id="fc"></div>';
    ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
    document.body.appendChild(ov);
    return ov;
  }

  function close() {
    var ov = document.getElementById('fc-ov');
    if (ov) ov.classList.remove('show');
    charts.forEach(function (c) { try { c.destroy(); } catch (e) {} });
    charts = [];
  }

  function baseOpts(unit) {
    return {
      responsive: true, maintainAspectRatio: false, animation: { duration: 350 },
      plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
      scales: {
        x: { grid: { color: 'rgba(122,158,255,.07)' }, ticks: { color: INK, font: { size: 9 } } },
        y: { grid: { color: 'rgba(122,158,255,.07)' },
             ticks: { color: INK, font: { size: 9 },
                      callback: function (v) { return v + (unit || ''); } } },
      },
    };
  }

  function cell(title, desc, id) {
    return '<div class="fc-cell"><div class="fc-t">' + title + '</div>' +
      '<div class="fc-d">' + desc + '</div><div class="fc-cv"><canvas id="' + id + '"></canvas></div></div>';
  }

  function lineChart(id, years, values, unit, colorPos) {
    var el = document.getElementById(id); if (!el || typeof Chart === 'undefined') return;
    charts.push(new Chart(el, {
      type: 'line',
      data: { labels: years, datasets: [{
        data: values, borderColor: colorPos || NEON, borderWidth: 2, pointRadius: 2.5,
        pointBackgroundColor: colorPos || NEON, tension: .35, spanGaps: true,
        fill: true, backgroundColor: 'rgba(0,224,255,.06)',
      }] },
      options: baseOpts(unit),
    }));
  }

  function barChart(id, years, values, unit, colorFn) {
    var el = document.getElementById(id); if (!el || typeof Chart === 'undefined') return;
    charts.push(new Chart(el, {
      type: 'bar',
      data: { labels: years, datasets: [{
        data: values, borderWidth: 0, borderRadius: 3,
        backgroundColor: values.map(function (v) { return colorFn ? colorFn(v) : NEON; }),
      }] },
      options: baseOpts(unit),
    }));
  }

  function posneg(v) { return v == null ? INK : v >= 0 ? UP : DOWN; }
  function posnegInv(v) { return v == null ? INK : v <= 0 ? UP : DOWN; }   // dilución: menos es mejor

  // dossier de empresa PRIVADA/pre-IPO: ficha + valuación + rondas + hitos
  // (feedback: "no todas las empresas tienen toda la info — que esté de todas")
  function renderPrivate(n) {
    var ov = ensureShell();
    var fc = document.getElementById('fc');
    var m = (window.NODE_META || {})[n.id] || {};
    var pi = (window.PREIPO_INTEL || {})[n.id] || {};
    var kv = function (k, v) {
      return v ? '<div style="display:flex;justify-content:space-between;gap:12px;font-size:12.5px;padding:6px 0;border-bottom:1px solid rgba(122,158,255,.08)">' +
        '<span style="color:#7C87A3">' + esc(k) + '</span><span style="color:#E8EDFB;text-align:right">' + esc(v) + '</span></div>' : '';
    };
    var rounds = (pi.rounds || []).map(function (r) {
      return '<div style="display:flex;gap:10px;font-size:11.5px;padding:5px 0;border-bottom:1px solid rgba(122,158,255,.06)">' +
        '<span style="color:#00E0FF;font-family:monospace;flex:0 0 52px">' + esc(r.date || '') + '</span>' +
        '<span style="color:#E8EDFB;flex:1">' + esc(r.round || '') + '</span>' +
        '<span style="color:#2BE38B;font-family:monospace">' + esc(r.amount || '') + '</span></div>';
    }).join('');
    var miles = (pi.milestones || []).map(function (h) {
      return '<div style="font-size:11.5px;padding:4px 0;color:#9BA6C4"><span style="color:#00E0FF;font-family:monospace">' + esc(h.date || '') + '</span> · ' + esc(h.event || '') + '</div>';
    }).join('');
    fc.innerHTML =
      '<div class="fc-hd"><span class="fc-name">🔒 ' + esc(n.label) + '</span>' +
        '<span class="fc-tk">' + L('empresa privada · dossier pre-IPO', 'private company · pre-IPO dossier') + '</span>' +
        '<button class="fc-close" onclick="window._finCardClose()" title="' + L('Cerrar', 'Close') + '">✕</button></div>' +
      '<div class="fc-sub">' + L('Sin estados financieros públicos — esto es lo que sabemos del catálogo e inteligencia pre-IPO', 'No public financial statements — this is what we know from the catalog and pre-IPO intelligence') + '</div>' +
      '<div class="fc-grid">' +
        '<div class="fc-cell"><div class="fc-t">🏢 ' + L('Ficha', 'Profile') + '</div>' +
          kv(L('País', 'Country'), n.country) + kv(L('Fundada', 'Founded'), m.founded) +
          kv(L('Empleados', 'Employees'), m.employees ? Number(m.employees).toLocaleString() : null) +
          kv(L('Ingresos', 'Revenue'), m.revenue_2025) + kv(L('Riesgo geopolítico', 'Geopolitical risk'), m.geo_risk) + '</div>' +
        '<div class="fc-cell"><div class="fc-t">💎 ' + L('Valuación', 'Valuation') + '</div>' +
          kv(L('Valuación', 'Valuation'), pi.valuation) + kv(L('Capital levantado', 'Capital raised'), pi.total_raised) +
          kv(L('IPO estimada', 'Expected IPO'), pi.ipo_timeline) +
          kv(L('Inversores', 'Investors'), (pi.investors || []).slice(0, 4).join(', ') || null) +
          (!pi.valuation ? '<div class="fc-note" style="padding:14px 4px">' + L('Sin inteligencia pre-IPO registrada para esta empresa.', 'No pre-IPO intelligence on record for this company.') + '</div>' : '') + '</div>' +
        (rounds ? '<div class="fc-cell"><div class="fc-t">💸 ' + L('Rondas', 'Funding rounds') + '</div>' + rounds + '</div>' : '') +
        (miles ? '<div class="fc-cell"><div class="fc-t">🏁 ' + L('Hitos', 'Milestones') + '</div>' + miles + '</div>' : '') +
        ((m.desc || n.role) ? '<div class="fc-cell" style="grid-column:1/-1"><div class="fc-t">📖 ' + L('Qué hace', 'What it does') + '</div>' +
          '<div style="font-size:12.5px;line-height:1.6;color:#C9D4EC;padding:4px 0">' + esc(m.desc || n.role) + '</div>' +
          (n.moat ? '<div style="font-size:11.5px;line-height:1.55;color:#8FA0C0;padding:6px 0 0"><b style="color:#9BA6C4">Moat:</b> ' + esc(n.moat) + '</div>' : '') + '</div>' : '') +
      '</div>' +
      '<div class="fc-foot"><span>Khipus Finance AI · ' + L('análisis, no asesoría financiera', 'analysis, not financial advice') + '</span><span>' + L('fuente: catálogo + inteligencia pre-IPO', 'source: catalog + pre-IPO intelligence') + '</span></div>';
    ov.classList.add('show');
  }

  window.openFinCard = function (idOrTicker) {
    var n = (window.BixbyVoice && window.BixbyVoice._resolveNode) ? window.BixbyVoice._resolveNode(idOrTicker) : null;
    var ticker = (n && n.mkt) || String(idOrTicker || '').toUpperCase();
    var label = (n && n.label) || ticker;
    if (n && !n.mkt) { renderPrivate(n); return; }   // privada → dossier pre-IPO
    if (!ticker) { if (typeof toast === 'function') toast(L('No encuentro esa empresa', "I can't find that company")); return; }

    var ov = ensureShell();
    var fc = document.getElementById('fc');
    charts.forEach(function (c) { try { c.destroy(); } catch (e) {} }); charts = [];
    fc.innerHTML =
      '<div class="fc-hd"><span class="fc-name">📊 ' + esc(label) + '</span>' +
        '<span class="fc-tk">' + esc(ticker) + ' · ' + L('dossier financiero', 'financial dossier') + '</span>' +
        '<button class="fc-close" onclick="window._finCardClose()" title="' + L('Cerrar', 'Close') + '">✕</button></div>' +
      '<div class="fc-sub">' + L('Estados financieros anuales · fuente FMP · los años sin dato se omiten', 'Annual financial statements · source FMP · years without data are skipped') + '</div>' +
      '<div class="fc-note">' + L('Cargando fundamentales…', 'Loading fundamentals…') + '</div>';
    ov.classList.add('show');

    fetch((window.BASE || '') + '/api/findossier/' + encodeURIComponent(ticker))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d || !d.available) {
          fc.querySelector('.fc-note').textContent = (d && d.reason === 'FMP_KEY no configurada')
            ? L('Para el dossier completo añade FMP_KEY en Railway (financialmodelingprep.com — plan gratis).', 'For the full dossier add FMP_KEY in Railway (financialmodelingprep.com — free plan).')
            : L('Sin estados financieros para ', 'No financial statements for ') + ticker + (d && d.reason ? ' — ' + d.reason : '') + '.';
          return;
        }
        var Y = d.years || [];
        var has = function (a) { return Array.isArray(a) && a.some(function (v) { return v != null; }); };
        var revB = (d.revenue || []).map(function (v) { return v != null ? Math.round(v / 1e8) / 10 : null; });
        var fcfB = (d.fcf || []).map(function (v) { return v != null ? Math.round(v / 1e8) / 10 : null; });

        // GARANTÍA "nunca una celda vacía" (feedback real): cada indicador
        // tiene un plan B con datos reales; si ni eso, una nota clara.
        var CELLS = [
          has(d.revenue_growth)
            ? { t: L('💵 Crecimiento de ingresos', '💵 Revenue growth'), d: L('variación anual, %', 'year-over-year change, %'), r: function (id) { lineChart(id, Y, d.revenue_growth, '%'); } }
            : { t: L('💵 Ingresos', '💵 Revenue'), d: L('miles de millones USD por año', 'USD billions per year'), r: has(revB) ? function (id) { barChart(id, Y, revB, '$B'); } : null },
          has(d.dilution)
            ? { t: L('🩸 Dilución', '🩸 Dilution'), d: L('cambio de acciones en circulación, % (menos es mejor)', 'change in shares outstanding, % (lower is better)'), r: function (id) { barChart(id, Y, d.dilution, '%', posnegInv); } }
            : { t: L('🩸 Acciones en circulación', '🩸 Shares outstanding'), d: L('miles de millones de acciones', 'billions of shares'), r: has(d.shares) ? function (id) { lineChart(id, Y, d.shares, 'B'); } : null },
          has(d.fcf_growth)
            ? { t: '💰 Free cash flow', d: L('crecimiento anual, %', 'annual growth, %'), r: function (id) { lineChart(id, Y, d.fcf_growth, '%'); } }
            : { t: '💰 Free cash flow', d: L('miles de millones USD por año', 'USD billions per year'), r: has(fcfB) ? function (id) { barChart(id, Y, fcfB, '$B', posneg); } : null },
          { t: L('📈 Acción', '📈 Stock'), d: L('últimos ~90 días', 'last ~90 days'), r: 'candles' },
          has(d.ev_to_sales)
            ? { t: L('🏷️ Valuación', '🏷️ Valuation'), d: L('EV / Ventas', 'EV / Sales'), r: function (id) { lineChart(id, Y, d.ev_to_sales, 'x'); } }
            : { t: L('🏷️ Margen bruto anual', '🏷️ Annual gross margin'), d: L('evolución del margen bruto, %', 'gross margin trend, %'), r: has(d.gross_margin) ? function (id) { lineChart(id, Y, d.gross_margin, '%'); } : null },
          { t: L('🏦 Balance', '🏦 Balance sheet'), d: L('deuda / capital (menos es mejor)', 'debt / equity (lower is better)'), r: has(d.de_ratio) ? function (id) { barChart(id, Y, d.de_ratio, '', function (v) { return v == null ? INK : v > 1 ? DOWN : NEON; }); } : null },
          { t: L('🧮 Márgenes', '🧮 Margins'), d: L('bruto vs FCF, último año, %', 'gross vs FCF, latest year, %'), r: 'margins' },
          { t: '♻️ Return on equity', d: L('ROE anual, %', 'annual ROE, %'), r: has(d.roe) ? function (id) { barChart(id, Y, d.roe, '%', posneg); } : null },
        ];

        fc.querySelector('.fc-note').outerHTML =
          '<div class="fc-grid">' +
            CELLS.map(function (c, i) { return cell(c.t, c.d, 'fc-c' + i); }).join('') +
          '</div>' +
          '<div class="fc-foot"><span>Khipus Finance AI · ' + L('análisis, no asesoría financiera', 'analysis, not financial advice') + '</span>' +
          '<span>' + L('fuente: estados financieros + mercado en vivo', 'source: financial statements + live market') + '</span></div>';

        CELLS.forEach(function (c, i) {
          var id = 'fc-c' + i;
          if (typeof c.r === 'function') { c.r(id); return; }
          if (c.r === 'margins') {
            var gm = null, fm = null;
            for (var k = Y.length - 1; k >= 0; k--) {
              if (gm == null && d.gross_margin[k] != null) gm = d.gross_margin[k];
              if (fm == null && d.fcf_margin[k] != null) fm = d.fcf_margin[k];
            }
            if (gm != null || fm != null) {
              barChart(id, [L('Margen bruto', 'Gross margin'), L('Margen FCF', 'FCF margin')], [gm, fm], '%', function (v) { return v == null ? INK : v >= 0 ? NEON : DOWN; });
              return;
            }
            c.r = null;
          }
          if (c.r == null) {
            var el = document.getElementById(id);
            if (el) el.parentNode.innerHTML = '<div class="fc-t">' + c.t + '</div>' +
              '<div class="fc-note" style="padding:26px 8px">' + L('El proveedor no publica este dato para esta empresa.', 'The provider does not publish this data for this company.') + '</div>';
          }
        });
        // precio ~90d (celda 4 = fc-c3); si no hay velas → nota clara
        fetch((window.BASE || '') + '/api/candles/' + encodeURIComponent(ticker))
          .then(function (r) { return r.json(); })
          .then(function (c) {
            if (!c || c.s !== 'ok' || !c.c || !c.c.length) {
              var el = document.getElementById('fc-c3');
              if (el) el.parentNode.innerHTML = '<div class="fc-t">' + L('📈 Acción', '📈 Stock') + '</div>' +
                '<div class="fc-note" style="padding:26px 8px">' + L('Sin datos de mercado para este ticker.', 'No market data for this ticker.') + '</div>';
              return;
            }
            var labels = (c.t || []).map(function (ts) { var dt = new Date(ts * 1000); return (dt.getMonth() + 1) + '/' + dt.getDate(); });
            var up = c.c[c.c.length - 1] >= c.c[0];
            lineChart('fc-c3', labels, c.c, '', up ? UP : DOWN);
          }).catch(function () {});
      })
      .catch(function () {
        var nEl = fc.querySelector('.fc-note');
        if (nEl) nEl.textContent = L('No se pudo cargar el dossier — reintenta en un momento.', 'Could not load the dossier — try again in a moment.');
      });
  };

  window._finCardClose = close;
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
})();
