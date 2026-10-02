/* ============================================================================
   engine/pfreports.js — 📄 REPORTES · 📰 NOTICIAS · 💬 PREGÚNTALE A TU CARTERA
   (secciones de Comité → 💼 Mi cartera; las monta engine/pfcommittee.js)

   Pedido (2026-10-02): "reportes mensuales, diarios o a pedido, en base a tus
   carteras en relación con tu posición inicial, con gráficos… como un NotebookLM
   pero que el contexto sea tu cartera… noticias en vivo relevantes a tu cartera,
   no las mismas emergencias viejas".
   Server: core/portfolio_reports_api.py. Dueño = llave aleatoria del navegador
   (localStorage 'kh_owner_key', cabecera X-Khipu-Owner).
   window.KhipuPortfolioExtras.render(el, section, ctx)
     section: 'reports' | 'news' | 'ask'
     ctx: { source: {key, label, positions, cash, start, startDate}, profile, analysis }
   ============================================================================ */
(function () {
  'use strict';
  function isEn() { var l = window.LANG; if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = null; } } return l === 'en'; }
  function L(es, en) { return isEn() ? en : es; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function usd(v) { v = Number(v); if (!isFinite(v)) return '—'; return (v < 0 ? '−$' : '$') + Math.abs(v).toLocaleString('en-US', { maximumFractionDigits: 0 }); }
  function sgn(v, d) { v = Number(v); if (!isFinite(v)) return '—'; return (v >= 0 ? '+' : '') + v.toFixed(d == null ? 1 : d); }
  function col(v) { return Number(v) >= 0 ? '#2BE38B' : '#FF4D6A'; }
  function day(iso) { var d = new Date(iso); return isNaN(d) ? (iso || '') : d.toLocaleDateString(isEn() ? 'en' : 'es', { day: '2-digit', month: 'short', year: 'numeric' }); }
  function actor() { var a = null; try { a = localStorage.getItem('khipu_actor'); } catch (e) {} return (a && a.trim()) || 'usuario'; }
  function owner() {
    var k = null;
    try { k = localStorage.getItem('kh_owner_key'); } catch (e) {}
    if (!k || k.length < 16) {
      var a = new Uint8Array(16); (window.crypto || {}).getRandomValues ? window.crypto.getRandomValues(a) : a.forEach(function (_, i) { a[i] = Math.random() * 256; });
      k = Array.prototype.map.call(a, function (b) { return ('0' + b.toString(16)).slice(-2); }).join('');
      try { localStorage.setItem('kh_owner_key', k); } catch (e) {}
    }
    return k;
  }
  function api(url, opts) {
    opts = opts || {};
    opts.headers = Object.assign({ 'Content-Type': 'application/json', 'X-Khipu-Owner': owner(), 'X-Khipu-Actor': actor() }, opts.headers || {});
    return fetch((window.BASE || '') + url, opts).then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { j._status = r.status; return j; }); });
  }
  function errOf(d) { return (isEn() ? (d.error_en || d.error) : d.error) || L('Algo falló.', 'Something failed.'); }
  function card(inner) { return '<div class="cm-cell">' + inner + '</div>'; }
  function md(t) {   // markdown mínimo y seguro (negrita, listas, saltos)
    return esc(t).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/^- (.*)$/gm, '• $1').replace(/\n/g, '<br>');
  }

  var S = { reports: null, viewing: null, period: 'month', busy: false, err: null, news: null, newsDays: 7,
    chat: [], asking: false, watches: null };
  var INV_SCHED = { autopilot: 'monthly', informed: 'weekly', active: 'daily' };

  // ── gráficos SVG (sin librerías) ──────────────────────────────────────────
  function lineChart(curve) {
    if (!curve || curve.length < 2) return '';
    var W = 640, H = 200, P = 34;
    var vals = [];
    curve.forEach(function (c) { if (c.idx != null) vals.push(c.idx); if (c.spy_idx != null) vals.push(c.spy_idx); });
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals); if (hi - lo < 1) { hi += 0.5; lo -= 0.5; }
    var x = function (i) { return P + i * (W - P - 8) / (curve.length - 1); };
    var y = function (v) { return 8 + (hi - v) * (H - 8 - 22) / (hi - lo); };
    var path = function (k) { var d = ''; curve.forEach(function (c, i) { if (c[k] == null) return; d += (d ? 'L' : 'M') + x(i).toFixed(1) + ',' + y(c[k]).toFixed(1); }); return d; };
    var last = curve[curve.length - 1];
    return '<svg viewBox="0 0 ' + W + ' ' + H + '" style="width:100%;height:auto;display:block" role="img" aria-label="' + esc(L('Valor de tu cartera vs S&P 500', 'Your portfolio vs S&P 500')) + '">' +
      [lo, (lo + hi) / 2, hi].map(function (v) { return '<line x1="' + P + '" x2="' + (W - 8) + '" y1="' + y(v) + '" y2="' + y(v) + '" stroke="#24304a" stroke-dasharray="3 4"/><text x="2" y="' + (y(v) + 4) + '" fill="#7C87A3" font-size="10">' + v.toFixed(0) + '</text>'; }).join('') +
      '<line x1="' + P + '" x2="' + (W - 8) + '" y1="' + y(100) + '" y2="' + y(100) + '" stroke="#5f6b8a"/>' +
      '<path d="' + path('spy_idx') + '" fill="none" stroke="#9BA6C4" stroke-width="1.6" stroke-dasharray="5 4"/>' +
      '<path d="' + path('idx') + '" fill="none" stroke="#00E0FF" stroke-width="2.4"/>' +
      '<text x="' + P + '" y="' + (H - 4) + '" fill="#7C87A3" font-size="10">' + esc(day(curve[0].d)) + '</text>' +
      '<text x="' + (W - 8) + '" y="' + (H - 4) + '" fill="#7C87A3" font-size="10" text-anchor="end">' + esc(day(last.d)) + '</text>' +
      '</svg><div class="cm-note" style="font-size:11px;display:flex;gap:14px;flex-wrap:wrap"><span><b style="color:#00E0FF">━</b> ' + esc(L('tu cartera', 'your portfolio')) + ' (' + sgn(last.idx - 100) + '%)</span>' +
      (last.spy_idx != null ? '<span><b style="color:#9BA6C4">┅</b> S&amp;P 500 (' + sgn(last.spy_idx - 100) + '%)</span>' : '') + '<span>' + esc(L('base 100 = inicio del periodo', 'base 100 = start of period')) + '</span></div>';
  }
  function bars(rows, key, fmt) {
    if (!rows || !rows.length) return '';
    var mx = Math.max.apply(null, rows.map(function (r) { return Math.abs(r[key]) || 0; }).concat([1e-9]));
    return rows.map(function (r) {
      var v = r[key], w = Math.abs(v) / mx * 50;
      return '<div style="display:grid;grid-template-columns:minmax(0,120px) minmax(0,1fr) 78px;gap:8px;align-items:center;font-size:12px;margin:4px 0">' +
        '<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + esc(r.label) + '</span>' +
        '<span style="position:relative;height:10px"><b style="position:absolute;left:50%;top:-2px;bottom:-2px;width:1px;background:#5f6b8a"></b>' +
        '<i style="position:absolute;top:0;bottom:0;border-radius:4px;background:' + col(v) + ';' + (v >= 0 ? 'left:50%' : 'right:50%') + ';width:' + w + '%"></i></span>' +
        '<span style="text-align:right;color:' + col(v) + ';font-variant-numeric:tabular-nums">' + fmt(v) + '</span></div>';
    }).join('');
  }
  function newsList(items) {
    if (!items || !items.length) return '<div class="cm-note">' + esc(L('Sin noticias recientes sobre tus posiciones en esta ventana.', 'No recent news about your holdings in this window.')) + '</div>';
    return items.map(function (n) {
      var c = n.freshness === 'new' ? '#2BE38B' : n.freshness === 'recent' ? '#5FC6E8' : '#7C87A3';
      var href = window.safeUrl ? window.safeUrl(n.url) : n.url;
      return '<div style="padding:8px 0;border-bottom:1px solid rgba(122,158,255,.08)">' +
        '<div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;font-size:11px;margin-bottom:2px">' +
          '<span style="color:' + c + ';font-weight:700">' + esc(n.label || '') + '</span><span style="color:#7C87A3">' + esc(day(n.published_at)) + (n.outlet ? ' · ' + esc(n.outlet) : '') + '</span>' +
          (n.holdings || []).map(function (h) { return '<span class="cm-pill" style="padding:0 7px">' + esc(h) + '</span>'; }).join('') + '</div>' +
        '<a href="' + esc(href) + '" target="_blank" rel="noopener" style="font-size:13px;color:#E8EDFB;font-weight:600;text-decoration:none">' + esc(n.title) + '</a>' +
        (n.summary ? '<div class="cm-note" style="margin-top:2px">' + esc(n.summary) + '</div>' : '') + '</div>';
    }).join('');
  }

  // ── 📄 reportes ──────────────────────────────────────────────────────────
  function reportView(r) {
    var p = r.performance || {}, s = r.summary || {}, adv = r.advisor || {};
    return '<div id="pfr-print">' + card('<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><b style="font-size:14px">📄 ' + esc(r.title || L('Reporte de tu cartera', 'Your portfolio report')) + '</b>' +
        '<span style="margin-left:auto;display:flex;gap:6px"><button class="cm-btn ghost" id="pfr-print-btn" style="padding:4px 10px;font-size:11.5px">🖨 ' + esc(L('Imprimir / PDF', 'Print / PDF')) + '</button>' +
        '<button class="cm-btn ghost" id="pfr-back" style="padding:4px 10px;font-size:11.5px">← ' + esc(L('Volver', 'Back')) + '</button></span></div>' +
        '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:10px">' +
          '<span class="cm-pill">💰 ' + usd(p.value_now_usd) + '</span>' +
          '<span class="cm-pill" style="color:' + col(p.period_change_pct) + '">' + esc(L('en el periodo ', 'over the period ')) + sgn(p.period_change_pct) + '% (' + usd(p.period_change_usd) + ')</span>' +
          (p.spy_period_pct != null ? '<span class="cm-pill">S&amp;P 500 ' + sgn(p.spy_period_pct) + '%' + (p.vs_spy_pts != null ? ' · ' + esc(L('tú ', 'you ')) + sgn(p.vs_spy_pts) + esc(L(' pts', ' pts')) : '') + '</span>' : '') +
          (p.initial_usd ? '<span class="cm-pill" style="color:' + col(p.since_start_pct) + '">' + esc(L('desde tu posición inicial ', 'since your starting position ')) + usd(p.initial_usd) + ' → ' + sgn(p.since_start_pct) + '%</span>' : '') +
          (p.period_max_drawdown_pct != null ? '<span class="cm-pill">📉 ' + esc(L('peor caída del periodo ', 'worst drop in the period ')) + Number(p.period_max_drawdown_pct).toFixed(1) + '%</span>' : '') +
        '</div>' +
        (s.text ? '<div style="margin-top:10px;font-size:13px;line-height:1.6;color:#E8EDFB">' + md(s.text) + (s.ai ? ' <span class="cm-pill" style="color:#B48CFF">🧠 IA</span>' : '') + '</div>' : '')) +
      card('<div class="cm-t">📈 ' + esc(L('Tu cartera vs el mercado', 'Your portfolio vs the market')) + '</div>' + lineChart(r.curve) + '<div class="cm-note" style="font-size:10.5px">' + esc(r.assumption || '') + '</div>') +
      '<div class="cm-grid"><div style="min-width:0">' +
        card('<div class="cm-t">🧮 ' + esc(L('Quién sumó y quién restó', 'Who added and who subtracted')) + '</div>' + bars(r.contributions || [], 'contrib_usd', usd)) +
        card('<div class="cm-t">↕ ' + esc(L('Cambio de cada posición en el periodo', 'Change of each position in the period')) + '</div>' + bars(r.contributions || [], 'change_pct', function (v) { return sgn(v) + '%'; })) +
      '</div><div style="min-width:0">' +
        (adv.actions && adv.actions.length ? card('<div class="cm-t">✅ ' + esc(L('Qué revisar', 'What to review')) + '</div>' + adv.actions.slice(0, 5).map(function (a) {
          return '<div class="cm-note" style="margin:5px 0"><b>' + esc(a.id) + '</b> · ' + esc(isEn() ? a.why_en : a.why_es) + '</div>'; }).join('') +
          (adv.disclaimer ? '<div class="cm-note" style="font-size:10.5px;color:#FFB300">🤖 ' + esc(adv.disclaimer) + '</div>' : '')) : '') +
        card('<div class="cm-t">📰 ' + esc(L('Noticias del periodo', 'News of the period')) + '</div>' + newsList(r.news || [])) +
      '</div></div>' +
      '<div class="cm-note" style="font-size:10.5px">' + esc(L('Fuente: ', 'Source: ') + (r.source || '') + ' · ' + L('generado ', 'generated ') + day(r.generated_at || r.created_at)) + '</div></div>';
  }

  function reportsHtml(ctx) {
    if (S.viewing) return reportView(S.viewing);
    var prof = ctx.profile || {}, sched = currentSchedule(ctx);
    var PER = [['day', 'Hoy', 'Today'], ['week', 'Semana', 'Week'], ['month', 'Mes', 'Month'], ['quarter', 'Trimestre', 'Quarter'], ['since_start', 'Desde el inicio', 'Since start']];
    var SCH = [['off', 'Apagado', 'Off'], ['daily', 'Diario', 'Daily'], ['weekly', 'Semanal', 'Weekly'], ['monthly', 'Mensual', 'Monthly']];
    return card('<div class="cm-t">📄 ' + esc(L('Reporte de tu cartera', 'Your portfolio report')) + '</div>' +
        '<div class="cm-note" style="margin-bottom:8px">' + esc(L('Cómo te fue frente a tu posición inicial y al S&P 500, quién sumó y quién restó, noticias con fecha y qué revisar. Con gráficos.', 'How you did vs your starting position and the S&P 500, who added and who subtracted, dated news and what to review. With charts.')) + '</div>' +
        '<div class="cm-form" style="margin-bottom:6px"><select id="pfr-period">' + PER.map(function (o) { return '<option value="' + o[0] + '"' + (S.period === o[0] ? ' selected' : '') + '>' + esc(L(o[1], o[2])) + '</option>'; }).join('') + '</select>' +
          '<button class="cm-btn" id="pfr-gen"' + (S.busy ? ' disabled' : '') + '>' + esc(S.busy ? L('Generando… (10-40 s)', 'Generating… (10-40 s)') : L('📄 Generar reporte ahora', '📄 Generate report now')) + '</button></div>' +
        '<div class="cm-form" style="margin:0"><span class="cm-note">🗓 ' + esc(L('Reportes automáticos de esta cartera:', 'Automatic reports for this portfolio:')) + '</span>' +
          '<select id="pfr-sched">' + SCH.map(function (o) { return '<option value="' + o[0] + '"' + (sched === o[0] ? ' selected' : '') + '>' + esc(L(o[1], o[2])) + '</option>'; }).join('') + '</select>' +
          (prof.involvement && !hasWatch(ctx) ? '<span class="cm-note" style="font-size:11px">' + esc(L('sugerido para tu nivel de involucramiento: ', 'suggested for your involvement level: ')) +
            esc(L({ daily: 'diario', weekly: 'semanal', monthly: 'mensual' }[suggestedSchedule(ctx)], suggestedSchedule(ctx))) + '</span>' : '') + '</div>' +
        (S.err ? '<div class="cm-note" style="color:#FFB300;margin-top:6px">' + esc(S.err) + '</div>' : '')) +
      card('<div class="cm-t">🗂 ' + esc(L('Tus reportes', 'Your reports')) + '</div>' +
        (S.reports == null ? '<div class="cm-note"><span class="cm-spin">◌</span></div>' : S.reports.length ? S.reports.map(function (r) {
          return '<div class="cm-hist" data-rid="' + esc(r.id) + '" style="display:flex;gap:8px;align-items:center">' + (r.read ? '' : '<b style="color:#00E0FF">●</b>') +
            '<span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + esc(r.title) + '</span>' +
            (r.change_pct != null ? '<span style="color:' + col(r.change_pct) + '">' + sgn(r.change_pct) + '%</span>' : '') + '</div>';
        }).join('') : '<div class="cm-note">' + esc(L('Todavía no hay reportes. Genera el primero arriba.', 'No reports yet. Generate the first one above.')) + '</div>'));
  }
  function hasWatch(ctx) { return (S.watches || []).some(function (w) { return w.source_key === ctx.source.key; }); }
  function currentSchedule(ctx) {
    var w = (S.watches || []).filter(function (x) { return x.source_key === ctx.source.key; })[0];
    if (w) return w.schedule;
    return 'off';
  }
  function suggestedSchedule(ctx) { return INV_SCHED[(ctx.profile || {}).involvement] || 'weekly'; }

  // ── 💬 pregúntale ───────────────────────────────────────────────────────
  function askHtml() {
    var sug = isEn() ? ['Why did my portfolio move this week?', 'Which position gives me the most risk?', 'What would you change to have fewer scares?', 'Explain my last report as if I were 12']
      : ['¿Por qué se movió mi cartera esta semana?', '¿Qué posición me da más riesgo?', '¿Qué cambiarías para tener menos sustos?', 'Explícame mi último reporte como si tuviera 12 años'];
    return card('<div class="cm-t">💬 ' + esc(L('Pregúntale a tu cartera', 'Ask your portfolio')) + '</div>' +
      '<div class="cm-note" style="margin-bottom:8px">' + esc(L('Khipu responde usando TU cartera y tu último reporte como contexto, más datos en vivo. Es análisis de IA, no asesoría personalizada.', 'Khipu answers using YOUR portfolio and your latest report as context, plus live data. It is AI analysis, not personalized advice.')) + '</div>' +
      '<div id="pfa-log" style="max-height:420px;overflow-y:auto">' + S.chat.map(function (m) {
        return '<div style="margin:8px 0;display:flex;' + (m.role === 'user' ? 'justify-content:flex-end' : '') + '"><div style="max-width:88%;padding:8px 12px;border-radius:12px;font-size:13px;line-height:1.55;' +
          (m.role === 'user' ? 'background:rgba(0,224,255,.12);color:#E8EDFB' : 'background:rgba(21,28,45,.8);color:#D5DCF0;border:1px solid rgba(122,158,255,.14)') + '">' + md(m.content) +
          (m.sources && m.sources.length ? '<div class="cm-note" style="font-size:10.5px;margin-top:4px">' + esc(L('Fuentes: ', 'Sources: ') + m.sources.map(function (s) { return s.label || s.name || s; }).join(' · ')) + '</div>' : '') + '</div></div>';
      }).join('') + (S.asking ? '<div class="cm-note"><span class="cm-spin">◌</span> ' + esc(L('Khipu está pensando con tu cartera…', 'Khipu is thinking with your portfolio…')) + '</div>' : '') + '</div>' +
      (S.chat.length ? '' : '<div style="display:flex;gap:6px;flex-wrap:wrap;margin:6px 0">' + sug.map(function (q) { return '<button class="cm-tab" data-sug="' + esc(q) + '">' + esc(q) + '</button>'; }).join('') + '</div>') +
      '<div class="cm-form" style="margin:8px 0 0"><input id="pfa-q" placeholder="' + esc(L('Pregunta lo que sea sobre tu cartera…', 'Ask anything about your portfolio…')) + '"><button class="cm-btn" id="pfa-send"' + (S.asking ? ' disabled' : '') + '>➤</button></div>');
  }

  // ── montaje ──────────────────────────────────────────────────────────────
  var CUR = { el: null, section: null, ctx: null };
  function paint() {
    var el = CUR.el; if (!el) return;
    var ctx = CUR.ctx;
    if (CUR.section === 'news') {
      el.innerHTML = card('<div class="cm-t">📰 ' + esc(L('Noticias de tu cartera', 'Your portfolio news')) + '</div>' +
        '<div class="cm-form" style="margin-bottom:4px"><span class="cm-note">' + esc(L('Ventana:', 'Window:')) + '</span>' + [1, 3, 7, 30].map(function (d) {
          return '<button class="cm-tab' + (S.newsDays === d ? ' on' : '') + '" data-nd="' + d + '">' + d + L(d === 1 ? ' día' : ' días', d === 1 ? ' day' : ' days') + '</button>'; }).join('') + '</div>' +
        '<div class="cm-note" style="font-size:11px;margin-bottom:6px">' + esc(L('Solo noticias con fecha dentro de la ventana, sin repetir. 🆕 = de hoy.', 'Only dated news within the window, no repeats. 🆕 = today.')) + '</div>' +
        (S.news == null ? '<div class="cm-note"><span class="cm-spin">◌</span> ' + esc(L('Buscando noticias…', 'Fetching news…')) + '</div>' : newsList(S.news.items)));
    } else if (CUR.section === 'ask') {
      el.innerHTML = askHtml();
      var lg = document.getElementById('pfa-log'); if (lg) lg.scrollTop = lg.scrollHeight;
    } else {
      el.innerHTML = reportsHtml(ctx);
    }
    wire();
  }
  function wire() {
    var el = CUR.el, ctx = CUR.ctx;
    el.querySelectorAll('[data-nd]').forEach(function (b) { b.onclick = function () { S.newsDays = +b.getAttribute('data-nd'); loadNews(); }; });
    var g = document.getElementById('pfr-gen'); if (g) g.onclick = generate;
    var pp = document.getElementById('pfr-period'); if (pp) pp.onchange = function () { S.period = pp.value; };
    var sc = document.getElementById('pfr-sched'); if (sc) sc.onchange = function () { saveWatch(sc.value); };
    el.querySelectorAll('[data-rid]').forEach(function (x) { x.onclick = function () { openReport(x.getAttribute('data-rid')); }; });
    var bk = document.getElementById('pfr-back'); if (bk) bk.onclick = function () { S.viewing = null; loadReports(); };
    var pr = document.getElementById('pfr-print-btn'); if (pr) pr.onclick = printReport;
    el.querySelectorAll('[data-sug]').forEach(function (b) { b.onclick = function () { ask(b.getAttribute('data-sug')); }; });
    var sd = document.getElementById('pfa-send'), qi = document.getElementById('pfa-q');
    if (sd && qi) { sd.onclick = function () { ask(qi.value); }; qi.onkeydown = function (e) { if (e.key === 'Enter') ask(qi.value); }; }
  }
  function body(ctx) {
    return { positions: ctx.source.positions, cash_usd: ctx.source.cash || 0, start_value: ctx.source.start || null,
      start_date: ctx.source.startDate || null, profile: Object.assign({ lang: isEn() ? 'en' : 'es' }, ctx.profile || {}),
      lang: isEn() ? 'en' : 'es', actor: actor(), name: ctx.source.label };
  }
  function generate() {
    var ctx = CUR.ctx; if (!ctx || !ctx.source) return;
    S.busy = true; S.err = null; paint();
    api('/api/portfolio-report/generate', { method: 'POST', body: JSON.stringify(Object.assign(body(ctx), { period: S.period })) }).then(function (d) {
      S.busy = false;
      if (!d.ok) { S.err = errOf(d); paint(); return; }
      S.viewing = d; paint(); loadReports(true);
    }).catch(function () { S.busy = false; S.err = L('Sin conexión con el servidor.', 'No connection to the server.'); paint(); });
  }
  function saveWatch(sched) {
    var ctx = CUR.ctx;
    api('/api/portfolio-report/watch', { method: 'POST', body: JSON.stringify(Object.assign(body(ctx), { schedule: sched, source_key: ctx.source.key })) }).then(function (d) {
      if (d.ok) { S.err = null; loadWatches(); if (window.KhipuToast) window.KhipuToast.show({ kind: 'info', title: L('Reportes automáticos', 'Automatic reports'), body: sched === 'off' ? L('Apagados.', 'Turned off.') : L('Programados: ', 'Scheduled: ') + sched }); }
      else { S.err = errOf(d); paint(); }
    });
  }
  function loadReports(silent) {
    api('/api/portfolio-report/list').then(function (d) { S.reports = d.reports || []; if (!silent || CUR.section === 'reports') paint(); });
  }
  function loadWatches() { api('/api/portfolio-report/watches').then(function (d) { S.watches = d.watches || []; paint(); }); }
  function openReport(id) { api('/api/portfolio-report/' + encodeURIComponent(id)).then(function (d) { if (d.performance) { S.viewing = d; paint(); } }); }
  function loadNews() {
    var ctx = CUR.ctx; S.news = null; paint();
    var weights = {};
    ((ctx.analysis && ctx.analysis.positions) || []).forEach(function (p) { weights[p.symbol] = p.weight_pct; });
    api('/api/news/portfolio', { method: 'POST', body: JSON.stringify({ days: S.newsDays, lang: isEn() ? 'en' : 'es',
      holdings: ctx.source.positions.map(function (p) { return { id: p.id, label: p.label, symbol: p.symbol, weight_pct: weights[p.symbol] }; }) }) })
      .then(function (d) { S.news = d; paint(); }).catch(function () { S.news = { items: [] }; paint(); });
  }
  function ask(q) {
    q = String(q || '').trim(); if (!q || S.asking) return;
    var ctx = CUR.ctx;
    S.chat.push({ role: 'user', content: q }); S.asking = true; paint();
    var last = (S.reports || [])[0];
    api('/api/portfolio-report/ask', { method: 'POST', body: JSON.stringify({ question: q, lang: isEn() ? 'en' : 'es', actor: actor(),
      positions: ctx.source.positions, report_id: (S.viewing && S.viewing.id) || (last && last.id) || null,
      notes: ctx.analysis ? notesFrom(ctx.analysis) : '',
      history: S.chat.slice(0, -1).slice(-8).map(function (m) { return { role: m.role, content: m.content }; }) }) }).then(function (d) {
      S.asking = false;
      S.chat.push({ role: 'assistant', content: d.answer || errOf(d), sources: d.sources || [] });
      paint();
    }).catch(function () { S.asking = false; S.chat.push({ role: 'assistant', content: L('Sin conexión con el servidor.', 'No connection to the server.') }); paint(); });
  }
  function notesFrom(a) {
    var k = a.kpis || {}, lines = ['Diagnóstico del comité de cartera: salud ' + (a.health || {}).score + '/100 (' + (a.health || {}).verdict + '); valor ' + k.value_usd +
      ' USD; volatilidad anual ' + k.vol_ann_pct + ' %; peor caída ' + k.max_drawdown_pct + ' %; perfil ' + ((a.profile || {}).label || '') + '.'];
    (a.positions || []).forEach(function (p) { lines.push(p.label + ' (' + p.symbol + '): peso ' + p.weight_pct + ' %, aporta ' + p.risk_contrib_pct + ' % del riesgo, convicción ' + (p.conviction == null ? 'sin investigar' : p.conviction) + '.'); });
    (a.actions || []).slice(0, 5).forEach(function (x) { lines.push('Acción ' + x.id + ': ' + x.why_es); });
    return lines.join('\n').slice(0, 3000);
  }
  function printReport() {
    var el = document.getElementById('pfr-print'); if (!el) return;
    var w = window.open('', '_blank'); if (!w) return;
    w.document.write('<!doctype html><html><head><meta charset="utf-8"><title>' + esc((S.viewing && S.viewing.title) || 'Reporte') + '</title>' +
      '<style>body{font-family:Inter,system-ui,sans-serif;background:#fff;color:#111;padding:24px}.cm-cell{border:1px solid #ddd;border-radius:10px;padding:12px;margin-bottom:12px}' +
      '.cm-pill{display:inline-block;border:1px solid #ccc;border-radius:999px;padding:2px 8px;margin:2px;font-size:12px}.cm-note{color:#444;font-size:12px}.cm-t{font-weight:700;font-size:12px;text-transform:uppercase;margin-bottom:6px}' +
      '.cm-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}button{display:none}a{color:#0645ad}</style></head><body>' + el.innerHTML + '</body></html>');
    w.document.close(); setTimeout(function () { try { w.print(); } catch (e) {} }, 300);
  }

  // aviso al abrir la app: reportes automáticos nuevos (solo si ya hay una llave de dueño)
  setTimeout(function () {
    var k = null; try { k = localStorage.getItem('kh_owner_key'); } catch (e) {}
    if (!k) return;
    api('/api/portfolio-report/list').then(function (d) {
      var n = d.unread || 0; if (!n) return;
      var msg = L('Tienes ' + n + ' reporte(s) nuevo(s) de tu cartera. Ábrelos en Comité → 💼 Mi cartera → 📄 Reportes.',
        'You have ' + n + ' new portfolio report(s). Open them in Committee → 💼 My portfolio → 📄 Reports.');
      if (window.KhipuToast && window.KhipuToast.show) window.KhipuToast.show({ kind: 'info', title: L('📄 Reportes nuevos', '📄 New reports'), body: msg, timeout: 12000,
        onClick: function () { if (window.KhipuCommittee && window.KhipuCommittee.openTab) window.KhipuCommittee.openTab('portfolio'); } });
    }).catch(function () {});
  }, 9000);

  window.KhipuPortfolioExtras = {
    render: function (el, section, ctx) {
      var changed = !CUR.ctx || !ctx || CUR.ctx.source.key !== ctx.source.key;
      CUR.el = el; CUR.section = section; CUR.ctx = ctx;
      if (changed) { S.news = null; S.chat = []; S.viewing = null; }
      paint();
      if (section === 'reports') { if (S.reports == null || changed) loadReports(); if (S.watches == null || changed) loadWatches(); }
      if (section === 'news' && (S.news == null || changed)) loadNews();
    },
    suggestedSchedule: suggestedSchedule,
    syncWatch: function (ctx) {   // mantiene al día las posiciones de una cartera con reportes automáticos
      if (!(S.watches || []).some(function (w) { return w.source_key === ctx.source.key && w.schedule !== 'off'; })) return;
      var w = S.watches.filter(function (x) { return x.source_key === ctx.source.key; })[0];
      api('/api/portfolio-report/watch', { method: 'POST', body: JSON.stringify(Object.assign(body(ctx), { schedule: w.schedule, source_key: ctx.source.key })) });
    },
    unread: function () { return api('/api/portfolio-report/list').then(function (d) { return d.unread || 0; }).catch(function () { return 0; }); },
  };
})();
