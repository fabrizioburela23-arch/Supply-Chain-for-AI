/* engine/riskreport.js — REPORTE DE RIESGO DE CARTERA: VaR + Vega (Kappa).

   window.KhipuRisk.open({ tab: 'var'|'vega', source?: 'market'|<id de cartera> })

   Pestaña VaR: posiciones de "Mi portafolio" (Mercado, MKT.pos) o de una de
   las Carteras simuladas (KhipuPortfolios) o escritas a mano ("NVDA:10, AMD 5").
   Server: POST /api/portfolio/risk_report (precios diarios REALES de 1 año).

   Pestaña Vega: opciones que el usuario registra (localStorage 'kh_options',
   hipotéticas o reales — NO se ejecutan órdenes). Server: POST
   /api/portfolio/vega_report (Black-Scholes con volatilidad implícita EN VIVO).

   Todo bilingüe (window.LANG). Cada métrica con su "?" (engine/explain.js).
   Nada se inventa: lo que no tiene datos se excluye y se dice por qué. */
(function () {
  'use strict';
  var LS_OPT = 'kh_options';
  var S = { tab: 'var', source: 'market', manual: '', rep: null, vrep: null, busy: false, chart: null };

  function en() { return (window.LANG || '') === 'en'; }
  function L(es, e) { return en() ? e : es; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function chip(k) { return window.explainChip ? window.explainChip(k) : ''; }
  function usd(v) {
    if (v == null || !isFinite(v)) return '—';
    var a = Math.abs(v), s = v < 0 ? '−' : '';
    return s + '$' + (a >= 1e6 ? (a / 1e6).toFixed(2) + 'M' : a >= 1e4 ? Math.round(a).toLocaleString() : a.toFixed(2));
  }
  function pct(v, d) { return v == null || !isFinite(v) ? '—' : (+v).toFixed(d == null ? 2 : d) + '%'; }
  function base() { return (typeof window.BASE !== 'undefined' && window.BASE) || ''; }

  /* ── fuentes de posiciones ───────────────────────────────────────────── */
  function sources() {
    var out = [{ id: 'market', name: L('Mi portafolio (Mercado)', 'My portfolio (Market)') }];
    try {
      var list = window.KhipuPortfolios && window.KhipuPortfolios._list ? window.KhipuPortfolios._list() : [];
      (list || []).forEach(function (p) { out.push({ id: 'pf:' + p.id, name: '🧪 ' + (p.name || p.id) }); });
    } catch (e) {}
    out.push({ id: 'manual', name: L('Escribir tickers a mano', 'Type tickers by hand') });
    return out;
  }
  function positionsFrom(src) {
    var NB = window.NODE_BY_ID || {}, out = [], skipped = [];
    if (src === 'market') {
      var pos = (window.MKT && window.MKT.pos) || {};
      Object.keys(pos).forEach(function (id) {
        var n = NB[id], p = pos[id];
        if (n && n.mkt && (p.sh || p.shares)) out.push({ symbol: n.mkt, shares: +(p.sh || p.shares), label: n.label });
        else skipped.push((n && n.label) || id);
      });
    } else if (src.indexOf('pf:') === 0) {
      var id = src.slice(3), list = (window.KhipuPortfolios && window.KhipuPortfolios._list()) || [];
      var pf = list.filter(function (x) { return x.id === id; })[0];
      ((pf && pf.positions) || []).forEach(function (p) {
        var n = NB[p.nodeId];
        if (n && n.mkt && p.shares > 0) out.push({ symbol: n.mkt, shares: +p.shares, label: n.label });
        else skipped.push((n && n.label) || p.nodeId);
      });
    } else {
      String(S.manual || '').split(/[,;\n]+/).forEach(function (tok) {
        var m = tok.trim().match(/^([A-Za-z0-9.^-]{1,15})\s*[: ]\s*([\d.]+)$/);
        if (m) out.push({ symbol: m[1].toUpperCase(), shares: +m[2], label: m[1].toUpperCase() });
        else if (tok.trim()) skipped.push(tok.trim());
      });
    }
    return { positions: out, skipped: skipped };
  }

  /* ── opciones guardadas ──────────────────────────────────────────────── */
  function loadOpts() { try { return JSON.parse(localStorage.getItem(LS_OPT) || '[]') || []; } catch (e) { return []; } }
  function saveOpts(a) { try { localStorage.setItem(LS_OPT, JSON.stringify(a)); } catch (e) {} }

  /* ── estructura ──────────────────────────────────────────────────────── */
  function css() {
    if (document.getElementById('krr-css')) return;
    var st = document.createElement('style'); st.id = 'krr-css';
    st.textContent =
      '#krr-ov{position:fixed;inset:0;z-index:7800;display:none;align-items:flex-start;justify-content:center;background:rgba(3,6,12,.74);backdrop-filter:blur(4px);overflow-y:auto;font-family:Inter,system-ui,sans-serif}' +
      '#krr-ov.show{display:flex}' +
      '#krr{width:min(1100px,96vw);margin:3vh 0;border-radius:16px;background:radial-gradient(900px 500px at 50% -10%,#0B1222 0%,#06090F 60%);border:1px solid rgba(122,158,255,.22);box-shadow:0 24px 70px rgba(0,0,0,.6);padding:18px 20px;color:#E8EDFB}' +
      '#krr .hd{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px}#krr .hd h2{margin:0;font-size:19px;flex:1;min-width:200px}' +
      '#krr .x{width:32px;height:32px;border-radius:8px;border:1px solid rgba(122,158,255,.25);background:rgba(21,28,45,.7);color:#9BA6C4;cursor:pointer}' +
      '#krr .tabs{display:flex;gap:6px;margin-bottom:12px}#krr .tab{padding:7px 14px;border-radius:9px;border:1px solid rgba(122,158,255,.22);background:rgba(21,28,45,.6);color:#9BA6C4;cursor:pointer;font-size:13px}#krr .tab.on{background:rgba(0,224,255,.12);border-color:#00E0FF;color:#00E0FF}' +
      '#krr .row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px}#krr select,#krr input,#krr textarea{background:#0B1222;border:1px solid rgba(122,158,255,.25);color:#E8EDFB;border-radius:8px;padding:7px 9px;font-size:13px;font-family:inherit}' +
      '#krr .btn{padding:8px 14px;border-radius:9px;border:1px solid #00E0FF;background:rgba(0,224,255,.12);color:#00E0FF;cursor:pointer;font-weight:650;font-size:13px}#krr .btn:disabled{opacity:.5;cursor:default}#krr .btn.gh{border-color:rgba(122,158,255,.3);background:transparent;color:#9BA6C4}' +
      '#krr .note{font-size:11.5px;color:#9BA6C4;line-height:1.55}#krr .warn{padding:8px 12px;border:1px dashed #f59e0b;border-radius:9px;background:rgba(245,158,11,.08);color:#fbbf24;font-size:12px;line-height:1.5;margin:8px 0}' +
      '#krr .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin:10px 0}#krr .card{border:1px solid rgba(122,158,255,.16);border-radius:11px;background:rgba(11,18,34,.6);padding:10px 12px}#krr .card .l{font-size:10.5px;color:#7C87A3;text-transform:uppercase;letter-spacing:.05em}#krr .card .v{font-size:19px;font-weight:750;margin-top:3px}#krr .card .s{font-size:11px;color:#9BA6C4;margin-top:2px}' +
      '#krr .sec{margin-top:14px}#krr .sec h3{font-size:13px;margin:0 0 8px;color:#C9D4EC;text-transform:uppercase;letter-spacing:.05em}' +
      '#krr table{width:100%;border-collapse:collapse;font-size:12.5px}#krr th,#krr td{padding:6px 8px;border-bottom:1px solid rgba(122,158,255,.1);text-align:right}#krr th:first-child,#krr td:first-child{text-align:left}#krr th{color:#7C87A3;font-weight:600;font-size:11px}' +
      '#krr .bar{height:7px;border-radius:4px;background:rgba(122,158,255,.12);position:relative;min-width:60px}#krr .bar i{position:absolute;left:0;top:0;bottom:0;border-radius:4px}' +
      '#krr .grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:760px){#krr .grid2{grid-template-columns:1fr}#krr{padding:14px 12px}#krr .card .v{font-size:16px}}' +
      '#krr .hm td{text-align:center;font-size:11px;color:#06090F;font-weight:650}#krr .scroll{overflow-x:auto}';
    document.head.appendChild(st);
  }
  function shell() {
    css();
    var ov = document.getElementById('krr-ov');
    if (!ov) {
      ov = document.createElement('div'); ov.id = 'krr-ov';
      ov.innerHTML = '<div id="krr"></div>';
      ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
      document.body.appendChild(ov);
    }
    return ov;
  }
  function close() { var ov = document.getElementById('krr-ov'); if (ov) ov.classList.remove('show'); }

  function header() {
    return '<div class="hd"><h2>📉 ' + esc(L('Reporte de riesgo de cartera', 'Portfolio risk report')) + '</h2>' +
      '<button class="btn gh" data-act="print">🖨 ' + esc(L('Imprimir / PDF', 'Print / PDF')) + '</button>' +
      '<button class="x" data-act="close">✕</button></div>' +
      '<div class="tabs"><button class="tab' + (S.tab === 'var' ? ' on' : '') + '" data-tab="var">📉 ' + esc(L('Riesgo (VaR)', 'Risk (VaR)')) + '</button>' +
      '<button class="tab' + (S.tab === 'vega' ? ' on' : '') + '" data-tab="vega">🌪 Vega / Kappa (' + esc(L('opciones', 'options')) + ')</button></div>';
  }

  function render() {
    var box = document.getElementById('krr'); if (!box) return;
    box.innerHTML = header() + (S.tab === 'var' ? viewVar() : viewVega());
    wire(box);
    if (S.tab === 'var' && S.rep && S.rep.ok) drawHist();
  }

  /* ── VaR ─────────────────────────────────────────────────────────────── */
  function viewVar() {
    var src = sources().map(function (x) { return '<option value="' + esc(x.id) + '"' + (x.id === S.source ? ' selected' : '') + '>' + esc(x.name) + '</option>'; }).join('');
    var h = '<div class="note" style="margin-bottom:8px">' + esc(L(
      'Mide cuánto se mueve tu cartera y cuánto podrías perder en un día malo, con precios diarios REALES del último año. Es una estimación estadística del pasado, no una predicción.',
      'Measures how much your portfolio moves and how much you could lose on a bad day, using REAL daily prices from the last year. It is a statistical estimate from the past, not a forecast.')) + '</div>' +
      '<div class="row"><select id="krr-src">' + src + '</select>' +
      (S.source === 'manual' ? '<input id="krr-man" style="flex:1;min-width:220px" placeholder="' + esc(L('Ej: NVDA:10, AMD:20, TSM:5', 'E.g. NVDA:10, AMD:20, TSM:5')) + '" value="' + esc(S.manual) + '">' : '') +
      '<button class="btn" data-act="run"' + (S.busy ? ' disabled' : '') + '>' + esc(S.busy ? L('Calculando…', 'Computing…') : L('Calcular reporte', 'Run report')) + '</button></div>';
    var r = S.rep;
    if (!r) return h;
    if (!r.ok) return h + '<div class="warn">' + esc(r.error || L('No se pudo calcular', 'Could not compute')) + '</div>' + excluded(r);
    var v95 = r.var95, v99 = r.var99;
    h += '<div class="note">' + esc(L('Datos: ', 'Data: ')) + esc(r.source) + ' · ' + esc(r.from) + ' → ' + esc(r.as_of) + ' (' + r.days + ' ' + esc(L('días', 'days')) + ')</div>';
    h += '<div class="cards">' +
      card(L('Valor de la cartera', 'Portfolio value'), usd(r.portfolio_value_usd), L('a precio de cierre', 'at closing price')) +
      card(L('Volatilidad anual', 'Annual volatility') + chip('vol_ann'), pct(r.vol_ann_pct, 1), L('diaria ', 'daily ') + pct(r.vol_daily_pct)) +
      card('VaR 95% · 1 ' + L('día', 'day') + chip('var'), usd(v95.hist_1d_usd), pct(v95.hist_1d_pct) + ' · ' + L('paramétrico ', 'parametric ') + usd(v95.param_1d_usd) + chip('var_method')) +
      card('CVaR 95% · 1 ' + L('día', 'day') + chip('cvar'), usd(v95.cvar_1d_usd), pct(v95.cvar_1d_pct)) +
      card('VaR 99% · 1 ' + L('día', 'day'), usd(v99.hist_1d_usd), pct(v99.hist_1d_pct) + ' · CVaR ' + usd(v99.cvar_1d_usd)) +
      card('VaR 95% · ' + r.horizon_days + ' ' + L('días', 'days'), usd(v95.hist_nd_usd), pct(v95.hist_nd_pct) + ' (√' + r.horizon_days + ')') +
      card(L('Máxima caída', 'Max drawdown') + chip('drawdown'), pct(r.max_drawdown_pct, 1), r.max_drawdown_date ? L('fondo el ', 'trough on ') + r.max_drawdown_date : '') +
      card(L('Beta vs S&P 500', 'Beta vs S&P 500') + chip('beta'), r.beta_spy == null ? '—' : r.beta_spy.toFixed(2), r.corr_spy == null ? '' : L('correlación ', 'correlation ') + r.corr_spy.toFixed(2)) +
      card('Sharpe' + chip('sharpe'), r.sharpe == null ? '—' : r.sharpe.toFixed(2), L('retorno anual ', 'annual return ') + pct(r.return_ann_pct, 1)) +
      card(L('Diversificación', 'Diversification') + chip('correlation'), r.diversification_ratio == null ? '—' : r.diversification_ratio.toFixed(2) + '×', L('1 = sin beneficio', '1 = no benefit')) +
      '</div>';
    var bt = r.backtest95;
    h += '<div class="note">' + chip('backtest') + ' ' + esc(L(
      'En el último año la pérdida real superó el VaR 95% en ' + bt.breaches + ' de ' + bt.days + ' días (lo esperado es ~' + bt.expected + ').',
      'Over the last year the real loss exceeded the 95% VaR on ' + bt.breaches + ' of ' + bt.days + ' days (about ' + bt.expected + ' expected).')) +
      (bt.breaches > bt.expected * 1.5 ? ' <b style="color:#FFB300">' + esc(L('El VaR estaría subestimando el riesgo.', 'VaR would be underestimating risk.')) + '</b>' : '') + '</div>';
    h += '<div class="grid2"><div class="sec"><h3>' + esc(L('Distribución de retornos diarios', 'Daily return distribution')) + '</h3>' +
      '<div style="height:220px"><canvas id="krr-hist"></canvas></div><div class="note">' + esc(L('En rojo: días peores que el VaR 95%.', 'In red: days worse than the 95% VaR.')) + '</div></div>' +
      '<div class="sec"><h3>' + esc(L('Peores días reales', 'Worst real days')) + '</h3><table><tr><th>' + esc(L('Fecha', 'Date')) + '</th><th>%</th><th>USD</th></tr>' +
      r.worst_days.map(function (d) { return '<tr><td>' + esc(d.date) + '</td><td style="color:#FF4D6A">' + pct(d.pct) + '</td><td>' + usd(d.usd) + '</td></tr>'; }).join('') + '</table></div></div>';
    var lab = r.labels || {};
    h += '<div class="sec"><h3>' + esc(L('¿Quién pone el riesgo?', 'Who brings the risk?')) + chip('risk_contrib') + '</h3><div class="scroll"><table><tr><th>' + esc(L('Posición', 'Position')) + '</th><th>' + esc(L('Valor', 'Value')) + '</th><th>' + esc(L('Peso', 'Weight')) + '</th><th>' + esc(L('Aporte al riesgo', 'Risk share')) + '</th><th></th><th>' + esc(L('Vol. anual', 'Ann. vol')) + '</th></tr>' +
      r.positions.map(function (p) {
        var hot = p.risk_contrib_pct > p.weight_pct * 1.3;
        return '<tr><td>' + esc(lab[p.symbol] || p.symbol) + ' <span style="color:#7C87A3">' + esc(p.symbol) + '</span></td><td>' + usd(p.value_usd) + '</td><td>' + pct(p.weight_pct, 1) + '</td><td style="color:' + (hot ? '#FFB300' : '#E8EDFB') + '">' + pct(p.risk_contrib_pct, 1) + '</td>' +
          '<td style="width:22%"><div class="bar"><i style="width:' + Math.max(0, Math.min(100, p.risk_contrib_pct)) + '%;background:' + (hot ? '#FFB300' : '#00E0FF') + '"></i></div></td><td>' + pct(p.vol_ann_pct, 1) + '</td></tr>';
      }).join('') + '</table></div><div class="note">' + esc(L('En ámbar: aporta mucho más riesgo que su peso en dinero.', 'Amber: brings far more risk than its money weight.')) + '</div></div>';
    h += heatmap(r);
    h += excluded(r);
    h += '<div class="note" style="margin-top:12px">' + esc(L(
      'Nota: una cartera solo de acciones tiene Vega 0. La Vega mide la sensibilidad de OPCIONES a la volatilidad — está en la otra pestaña.',
      'Note: a stock-only portfolio has zero Vega. Vega measures OPTIONS sensitivity to volatility — see the other tab.')) + '</div>';
    return h;
  }
  function card(l, v, s) { return '<div class="card"><div class="l">' + l + '</div><div class="v">' + v + '</div>' + (s ? '<div class="s">' + s + '</div>' : '') + '</div>'; }
  function excluded(r) {
    var ex = (r && r.excluded) || [], sk = S._skipped || [];
    if (!ex.length && !sk.length) return '';
    return '<div class="warn">' + esc(L('Excluidas del cálculo: ', 'Excluded from the calculation: ')) +
      ex.map(function (e) { return esc((e.label || e.symbol) + ' (' + e.reason + ')'); }).concat(sk.map(function (x) { return esc(x + ' (' + L('no cotiza o sin cantidad', 'not listed or no quantity') + ')'); })).join(' · ') + '</div>';
  }
  function heatmap(r) {
    var c = r.correlation; if (!c || c.symbols.length < 2) return '';
    var col = function (v) {
      if (v == null) return '#333';
      var t = Math.max(-1, Math.min(1, v));
      return t >= 0 ? 'rgba(255,77,106,' + (0.15 + 0.85 * t) + ')' : 'rgba(43,227,139,' + (0.15 + 0.85 * -t) + ')';
    };
    return '<div class="sec"><h3>' + esc(L('Correlaciones', 'Correlations')) + chip('correlation') + '</h3><div class="scroll"><table class="hm"><tr><th></th>' +
      c.symbols.map(function (s) { return '<th>' + esc(s) + '</th>'; }).join('') + '</tr>' +
      c.matrix.map(function (row, i) {
        return '<tr><th style="text-align:left">' + esc(c.symbols[i]) + '</th>' + row.map(function (v) { return '<td style="background:' + col(v) + '">' + (v == null ? '—' : v.toFixed(2)) + '</td>'; }).join('') + '</tr>';
      }).join('') + '</table></div><div class="note">' + esc(L('Rojo = se mueven juntas (no diversifican); verde = en sentido contrario (cubren).', 'Red = move together (no diversification); green = opposite (hedge).')) + '</div></div>';
  }
  function drawHist() {
    var r = S.rep, cv = document.getElementById('krr-hist');
    if (!cv || !window.Chart || !r.histogram) return;
    if (S.chart) { try { S.chart.destroy(); } catch (e) {} }
    var ed = r.histogram.edges_pct, cnt = r.histogram.counts, cut = -r.var95.hist_1d_pct;
    var labels = cnt.map(function (_, i) { return ((ed[i] + ed[i + 1]) / 2).toFixed(1) + '%'; });
    var colors = cnt.map(function (_, i) { return ed[i + 1] <= cut ? '#FF4D6A' : '#00E0FF'; });
    S.chart = new window.Chart(cv.getContext('2d'), {
      type: 'bar', data: { labels: labels, datasets: [{ data: cnt, backgroundColor: colors, borderWidth: 0 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } },
        scales: { x: { ticks: { color: '#7C87A3', maxTicksLimit: 8, font: { size: 10 } }, grid: { display: false } },
                  y: { ticks: { color: '#7C87A3', font: { size: 10 } }, grid: { color: 'rgba(122,158,255,.08)' } } } },
    });
  }
  function runVar() {
    if (S.busy) return;
    var got = positionsFrom(S.source);
    S._skipped = got.skipped;
    if (!got.positions.length) {
      S.rep = { ok: false, error: L('No hay posiciones con ticker y cantidad en esa cartera. Agrega acciones en Mercado o en una Cartera simulada, o escribe tickers a mano.',
        'No positions with ticker and quantity in that portfolio. Add stocks in Market or a Simulated portfolio, or type tickers by hand.') };
      return render();
    }
    S.busy = true; render();
    fetch(base() + '/api/portfolio/risk_report', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ positions: got.positions, horizon_days: 10 }) })
      .then(function (r) { return r.json().catch(function () { return { ok: false, error: 'HTTP ' + r.status }; }); })
      .then(function (d) { S.rep = d; })
      .catch(function () { S.rep = { ok: false, error: L('Sin conexión con el servidor', 'No connection to the server') }; })
      .then(function () { S.busy = false; render(); });
  }

  /* ── Vega ────────────────────────────────────────────────────────────── */
  function viewVega() {
    var opts = loadOpts();
    var h = '<div class="note" style="margin-bottom:8px">' + chip('vega') + ' ' + esc(L(
      'La Vega (en algunos bancos, Kappa) mide cuánto cambia el valor de tus OPCIONES si la volatilidad del mercado sube o baja 1 punto. Registra aquí tus opciones (reales o hipotéticas): no se ejecuta ninguna orden. Se valoran con Black-Scholes usando la volatilidad implícita EN VIVO de cada contrato.',
      'Vega (at some banks, Kappa) measures how much the value of your OPTIONS changes if market volatility rises or falls by 1 point. Register your options here (real or hypothetical): no order is placed. They are valued with Black-Scholes using each contract\'s LIVE implied volatility.')) + '</div>';
    h += '<div class="row"><input id="kv-sym" placeholder="' + esc(L('Ticker (ej. NVDA)', 'Ticker (e.g. NVDA)')) + '" style="width:120px" value="' + esc(S.vsym || '') + '">' +
      '<button class="btn gh" data-act="chain">' + esc(L('Buscar vencimientos', 'Find expiries')) + '</button>' +
      '<select id="kv-kind"><option value="call">Call</option><option value="put">Put</option></select>' +
      '<select id="kv-exp">' + ((S.chain && S.chain.expirations) || []).map(function (e) { return '<option' + (e === S.vexp ? ' selected' : '') + '>' + esc(e) + '</option>'; }).join('') + '</select>' +
      '<select id="kv-k">' + ((S.chain && S.chain.strikes) || []).map(function (k) { return '<option' + (k === S.vk ? ' selected' : '') + '>' + k + '</option>'; }).join('') + '</select>' +
      '<input id="kv-n" type="number" step="1" value="1" style="width:80px" title="' + esc(L('Contratos (negativo = vendida)', 'Contracts (negative = short)')) + '">' +
      '<button class="btn" data-act="addopt">＋ ' + esc(L('Agregar', 'Add')) + '</button></div>';
    if (S.chain && S.chain.spot) h += '<div class="note">' + esc(S.chain.symbol) + ': ' + esc(L('precio en vivo ', 'live price ')) + '$' + (+S.chain.spot).toFixed(2) + (S.chain.available ? '' : ' · ' + esc(L('sin cadena de opciones publicada', 'no options chain published'))) + '</div>';
    if (S.chainErr) h += '<div class="warn">' + esc(S.chainErr) + '</div>';
    h += '<div class="note">' + esc(L('1 contrato = 100 acciones. Contratos negativos = opción vendida (Vega negativa).', '1 contract = 100 shares. Negative contracts = sold option (negative Vega).')) + '</div>';
    if (opts.length) {
      h += '<div class="sec"><h3>' + esc(L('Tus opciones', 'Your options')) + '</h3><div class="scroll"><table><tr><th>' + esc(L('Contrato', 'Contract')) + '</th><th>' + esc(L('Contratos', 'Contracts')) + '</th><th></th></tr>' +
        opts.map(function (o, i) { return '<tr><td>' + esc(o.symbol + ' ' + o.kind.toUpperCase() + ' ' + o.strike + ' · ' + o.expiry) + '</td><td>' + esc(o.contracts) + '</td><td><button class="btn gh" data-del="' + i + '">✕</button></td></tr>'; }).join('') +
        '</table></div><div class="row" style="margin-top:8px"><button class="btn" data-act="runvega"' + (S.busy ? ' disabled' : '') + '>' + esc(S.busy ? L('Calculando…', 'Computing…') : L('Calcular reporte Vega', 'Run Vega report')) + '</button></div></div>';
    } else {
      h += '<div class="note" style="margin-top:10px">' + esc(L('Aún no registraste opciones. Tu cartera de acciones, por sí sola, tiene Vega 0.', 'No options registered yet. Your stock portfolio alone has zero Vega.')) + '</div>';
    }
    var r = S.vrep;
    if (!r) return h;
    if (!r.ok) return h + '<div class="warn">' + esc(r.error || '') + (r.excluded && r.excluded.length ? ' · ' + r.excluded.map(function (e) { return esc(e.symbol + ': ' + e.reason); }).join(' · ') : '') + '</div>';
    var t = r.totals;
    h += '<div class="cards">' +
      card('Vega' + chip('vega'), usd(t.vega_usd), L('por +1 punto de volatilidad', 'per +1 volatility point')) +
      card(L('Valor de las opciones', 'Options value'), usd(t.value_usd), L('según el modelo', 'per the model')) +
      card('Delta' + chip('delta'), (t.delta_shares >= 0 ? '+' : '') + t.delta_shares.toFixed(0) + ' ' + L('acc.', 'sh.'), L('equivalente en acciones', 'share equivalent')) +
      card('Theta' + chip('theta'), usd(t.theta_usd_day), L('por día que pasa', 'per day that passes')) +
      card('Gamma' + chip('gamma'), t.gamma.toFixed(2), L('cambio de Delta por $1', 'Delta change per $1')) +
      '</div>';
    h += '<div class="sec"><h3>' + esc(L('Si la volatilidad cambia…', 'If volatility changes…')) + '</h3><table><tr><th>' + esc(L('Cambio de volatilidad', 'Volatility change')) + '</th><th>' + esc(L('Ganancia / pérdida', 'Gain / loss')) + '</th></tr>' +
      r.vol_scenarios.map(function (s) { return '<tr><td>' + (s.shock_pts > 0 ? '+' : '') + s.shock_pts + ' ' + esc(L('puntos', 'points')) + '</td><td style="color:' + (s.pnl_usd >= 0 ? '#2BE38B' : '#FF4D6A') + '">' + usd(s.pnl_usd) + '</td></tr>'; }).join('') +
      '</table><div class="note">' + esc(L('Revaluación completa con el modelo (no solo Vega × cambio). Todo lo demás constante.', 'Full model revaluation (not just Vega × change). Everything else held constant.')) + '</div></div>';
    h += '<div class="sec"><h3>' + esc(L('Detalle por opción', 'Detail per option')) + '</h3><div class="scroll"><table><tr><th>' + esc(L('Contrato', 'Contract')) + '</th><th>' + esc(L('Días', 'Days')) + '</th><th>' + esc(L('Precio acción', 'Stock price')) + '</th><th>IV' + chip('iv') + '</th><th>' + esc(L('Modelo', 'Model')) + '</th><th>' + esc(L('Mercado (medio)', 'Market (mid)')) + '</th><th>Vega' + chip('vega') + '</th><th>Delta' + chip('delta') + '</th><th>Gamma' + chip('gamma') + '</th><th>Theta' + chip('theta') + '/' + esc(L('día', 'day')) + '</th></tr>' +
      r.positions.map(function (p) {
        return '<tr><td>' + esc(p.symbol + ' ' + p.kind.toUpperCase() + ' ' + p.strike + ' · ' + p.expiry + ' ×' + p.contracts) + '</td><td>' + p.days + '</td><td>$' + p.spot + '</td><td title="' + esc(p.iv_source) + '">' + pct(p.iv_pct, 1) + (p.iv_source.indexOf('hist') === 0 ? '*' : '') + '</td><td>$' + p.model_price.toFixed(2) + '</td><td>' + (p.market_mid == null ? '—' : '$' + p.market_mid.toFixed(2)) + '</td><td>' + usd(p.vega_usd) + '</td><td>' + p.delta_shares.toFixed(0) + '</td><td>' + p.gamma.toFixed(2) + '</td><td>' + usd(p.theta_usd_day) + '</td></tr>';
      }).join('') + '</table></div><div class="note">* ' + esc(L('volatilidad histórica de 1 año (el contrato no publica implícita).', '1-year historical volatility (the contract publishes no implied).')) +
      ' · ' + esc(r.model) + ' · ' + esc(L('tasa libre de riesgo ', 'risk-free rate ')) + r.rate.value_pct + '% (' + esc(r.rate.source) + ')</div></div>';
    h += greeksByUnderlying(r);
    if (r.excluded && r.excluded.length) h += '<div class="warn">' + esc(L('No valoradas: ', 'Not valued: ')) + r.excluded.map(function (e) { return esc(e.symbol + ' (' + e.reason + ')'); }).join(' · ') + '</div>';
    return h;
  }
  // Griegas por empresa: las ACCIONES de "Mi portafolio" aportan Delta = nº de
  // acciones (Gamma, Theta y Vega 0); las opciones, lo que dice el modelo.
  function greeksByUnderlying(r) {
    var NB = window.NODE_BY_ID || {}, pos = (window.MKT && window.MKT.pos) || {}, sh = {};
    Object.keys(pos).forEach(function (id) { var n = NB[id]; if (n && n.mkt) sh[n.mkt] = (sh[n.mkt] || 0) + (+(pos[id].sh || pos[id].shares) || 0); });
    var g = {};
    r.positions.forEach(function (p) {
      var x = g[p.symbol] || (g[p.symbol] = { d: 0, gm: 0, v: 0, t: 0 });
      x.d += p.delta_shares; x.gm += p.gamma; x.v += p.vega_usd; x.t += p.theta_usd_day;
    });
    var syms = Object.keys(g); if (!syms.length) return '';
    return '<div class="sec"><h3>' + esc(L('Griegas por empresa (acciones + opciones)', 'Greeks by company (stocks + options)')) + '</h3><div class="scroll"><table><tr><th>' + esc(L('Empresa', 'Company')) +
      '</th><th>' + esc(L('Acciones', 'Shares')) + '</th><th>Delta' + chip('delta') + '</th><th>Gamma' + chip('gamma') + '</th><th>Theta' + chip('theta') + '</th><th>Vega' + chip('vega') + '</th></tr>' +
      syms.map(function (k) {
        var x = g[k], s0 = sh[k] || 0;
        return '<tr><td>' + esc(k) + '</td><td>' + s0 + '</td><td>' + (s0 + x.d).toFixed(0) + '</td><td>' + x.gm.toFixed(2) + '</td><td>' + usd(x.t) + '</td><td>' + usd(x.v) + '</td></tr>';
      }).join('') + '</table></div><div class="note">' + esc(L('Delta total = tus acciones (de "Mi portafolio") + la Delta de tus opciones. Las acciones no tienen Gamma, Theta ni Vega.',
        'Total Delta = your shares (from "My portfolio") + your options\' Delta. Shares have no Gamma, Theta or Vega.')) + '</div></div>';
  }
  function loadChain(sym, exp) {
    S.vsym = sym; S.chainErr = null;
    fetch(base() + '/api/options/chain/' + encodeURIComponent(sym) + (exp ? '?expiry=' + encodeURIComponent(exp) : ''))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        S.chain = d;
        if (!d || !d.available) S.chainErr = L('No encontré opciones listadas para ' + sym + '.', 'No listed options found for ' + sym + '.');
        else if (!exp && d.expirations && d.expirations.length) { S.vexp = d.expirations[0]; return loadChain(sym, S.vexp); }
        render();
      }).catch(function () { S.chainErr = L('Sin conexión con el servidor', 'No connection to the server'); render(); });
  }
  function runVega() {
    var opts = loadOpts(); if (!opts.length || S.busy) return;
    S.busy = true; render();
    fetch(base() + '/api/portfolio/vega_report', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ options: opts }) })
      .then(function (r) { return r.json().catch(function () { return { ok: false, error: 'HTTP ' + r.status }; }); })
      .then(function (d) { S.vrep = d; })
      .catch(function () { S.vrep = { ok: false, error: L('Sin conexión con el servidor', 'No connection to the server') }; })
      .then(function () { S.busy = false; render(); });
  }

  /* ── eventos ─────────────────────────────────────────────────────────── */
  function wire(box) {
    box.querySelectorAll('[data-tab]').forEach(function (b) { b.onclick = function () { S.tab = b.getAttribute('data-tab'); render(); }; });
    box.querySelectorAll('[data-act]').forEach(function (b) {
      b.onclick = function () {
        var a = b.getAttribute('data-act');
        if (a === 'close') close();
        else if (a === 'print') printReport();
        else if (a === 'run') { var m = document.getElementById('krr-man'); if (m) S.manual = m.value; runVar(); }
        else if (a === 'chain') { var s = (document.getElementById('kv-sym').value || '').trim().toUpperCase(); if (s) loadChain(s); }
        else if (a === 'addopt') {
          var sym = (document.getElementById('kv-sym').value || '').trim().toUpperCase();
          var exp = document.getElementById('kv-exp').value, k = parseFloat(document.getElementById('kv-k').value);
          var n = parseFloat(document.getElementById('kv-n').value), kind = document.getElementById('kv-kind').value;
          if (!sym || !exp || !isFinite(k) || !isFinite(n) || n === 0) { S.chainErr = L('Elige ticker, vencimiento, strike y contratos (≠ 0).', 'Pick ticker, expiry, strike and contracts (≠ 0).'); return render(); }
          var o = loadOpts(); o.push({ symbol: sym, kind: kind, strike: k, expiry: exp, contracts: n }); saveOpts(o); S.vrep = null; render();
        } else if (a === 'runvega') runVega();
      };
    });
    box.querySelectorAll('[data-del]').forEach(function (b) { b.onclick = function () { var o = loadOpts(); o.splice(+b.getAttribute('data-del'), 1); saveOpts(o); S.vrep = null; render(); }; });
    var src = document.getElementById('krr-src'); if (src) src.onchange = function () { S.source = src.value; S.rep = null; render(); };
    var ex = document.getElementById('kv-exp'); if (ex) ex.onchange = function () { S.vexp = ex.value; if (S.vsym) loadChain(S.vsym, ex.value); };
    var kk = document.getElementById('kv-k'); if (kk) kk.onchange = function () { S.vk = parseFloat(kk.value); };
  }
  function printReport() {
    var box = document.getElementById('krr'); if (!box) return;
    var img = '';
    try { var cv = document.getElementById('krr-hist'); if (cv) img = cv.toDataURL('image/png'); } catch (e) {}
    var html = box.innerHTML.replace(/<canvas id="krr-hist"><\/canvas>/, img ? '<img src="' + img + '" style="max-width:100%">' : '');
    var w = window.open('', '_blank'); if (!w) return;
    w.document.write('<!doctype html><meta charset="utf-8"><title>' + esc(L('Reporte de riesgo — Khipus', 'Risk report — Khipus')) + '</title>' +
      '<style>body{font-family:Inter,system-ui,sans-serif;color:#111;padding:20px}button,select,input,.tabs{display:none!important}table{width:100%;border-collapse:collapse;font-size:12px}th,td{border-bottom:1px solid #ddd;padding:4px 6px;text-align:right}th:first-child,td:first-child{text-align:left}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.card{border:1px solid #ccc;border-radius:8px;padding:8px}.card .l{font-size:10px;color:#555;text-transform:uppercase}.card .v{font-size:17px;font-weight:700}.note{font-size:11px;color:#444}.warn{font-size:11px;color:#8a5a00;border:1px dashed #c90;padding:6px;margin:6px 0}.bar{height:6px;background:#eee;position:relative}.bar i{position:absolute;left:0;top:0;bottom:0;background:#0aa}</style>' +
      '<body>' + html + '<p class="note">Khipus Finance AI · ' + new Date().toLocaleString() + '</p></body>');
    w.document.close(); setTimeout(function () { try { w.print(); } catch (e) {} }, 400);
  }

  window.KhipuRisk = {
    open: function (o) {
      o = o || {};
      if (o.tab) S.tab = o.tab;
      if (o.source) S.source = o.source;
      shell().classList.add('show');
      render();
      if (o.autorun && S.tab === 'var') runVar();
    },
    close: close,
  };
})();
