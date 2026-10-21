/* ============================================================================
   engine/simreport.js — INFORME DE ESCENARIO (2026-10-21, «que parezca un producto»)
   Pinta la salida de POST /api/sim/agents (core/sim_agents + core/sim_report) como un informe completo:
     titular · cifras clave · resumen ejecutivo · TU CARTERA · ganadoras/perdedoras · por sector · por país ·
     tabla completa (ticker, sector, país, canal, %, capitalización y precio en vivo, valor en juego, camino) ·
     cómo se desarrolla · lo que dicen los agentes · qué vigilar · metodología y fuentes · aviso.
   Botones: 🖨 PDF (ventana de impresión clara) y 📋 copiar el resumen. Cifras SOLO del servidor (sin dato «—»).
   window.KhipuSimReport.render(d, en) → HTML · .bind(root, d, en, onCompany) → engancha clics y botones.
   ============================================================================ */
(function () {
  'use strict';
  if (window.KhipuSimReport) return;

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function nf(v, d, en) { return Number(v).toLocaleString(en ? 'en-US' : 'es-PE', { maximumFractionDigits: d == null ? 1 : d, minimumFractionDigits: 0 }); }
  function pct(v, en) { if (v == null || !isFinite(v)) return '—'; return (v > 0 ? '+' : v < 0 ? '−' : '') + nf(Math.abs(v), 1, en) + (en ? '%' : ' %'); }
  function bil(b, en) {           // miles de millones de USD → «$4,2 T» / «$350 B» / «$820 M»
    if (b == null || !isFinite(b)) return '—';
    var a = Math.abs(b), s = b < 0 ? '−' : '';
    if (a >= 1000) return s + '$' + nf(a / 1000, 2, en) + ' T';
    if (a >= 1) return s + '$' + nf(a, 1, en) + ' B';
    return s + '$' + nf(a * 1000, 0, en) + ' M';
  }
  function usd(v, en) { if (v == null || !isFinite(v)) return '—'; return (v < 0 ? '−' : '') + '$' + nf(Math.abs(v), 0, en); }
  function when(iso, en) { if (!iso) return '—'; try { return new Date(iso).toLocaleString(en ? 'en-US' : 'es-PE', { dateStyle: 'medium', timeStyle: 'short' }); } catch (e) { return iso; } }
  var CHAN = { direct: ['Golpe directo', 'Direct hit', 'bad'], substitute: ['Podría ganar cuota', 'Could gain share', 'good'],
    customer: ['Cliente: pierde suministro', 'Customer: loses supply', 'warn'], supplier: ['Proveedor: cambian sus pedidos', 'Supplier: orders change', 'ai'],
    second_order: ['Segundo orden', 'Second order', 'muted'] };

  var CSS = '.ksr{font-size:13.5px;line-height:1.5;color:var(--os-ink,#F2F2F5)}' +
    '.ksr *{box-sizing:border-box}.ksr h3{margin:22px 0 8px;font-size:15px;font-weight:800;letter-spacing:-.01em}' +
    '.ksr .card{background:var(--os-surface,#17181F);border-radius:16px;padding:14px 16px;box-shadow:0 1px 2px rgba(0,0,0,.25)}' +
    '.ksr .top{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:6px}' +
    '.ksr .tag{font-size:11px;font-weight:800;letter-spacing:.06em;padding:3px 9px;border-radius:999px;background:var(--os-surface-2,#24252F);color:var(--os-ink-2,#A6A8B5)}' +
    '.ksr .tag.sim{color:var(--os-warn-ink,#F2C46D)}.ksr .sp{flex:1}' +
    '.ksr .btn{font:inherit;font-size:12px;font-weight:700;border:0;border-radius:999px;padding:6px 12px;cursor:pointer;background:var(--os-surface-2,#24252F);color:var(--os-ink,#F2F2F5)}' +
    '.ksr .btn:focus-visible{outline:2px solid var(--os-accent,#4C8DF6);outline-offset:2px}' +
    '.ksr .hl{font-size:19px;font-weight:800;line-height:1.35;letter-spacing:-.015em;margin:4px 0 2px}' +
    '.ksr .meta{font-size:12px;color:var(--os-ink-2,#A6A8B5)}' +
    '.ksr .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:14px}' +
    '.ksr .kpi{background:var(--os-surface,#17181F);border-radius:14px;padding:11px 13px}' +
    '.ksr .kpi .l{font-size:11.5px;color:var(--os-ink-2,#A6A8B5);font-weight:700}' +
    '.ksr .kpi .v{font-size:20px;font-weight:800;margin-top:2px;font-variant-numeric:tabular-nums}' +
    '.ksr .kpi .s{font-size:11.5px;color:var(--os-ink-2,#A6A8B5);margin-top:1px}' +
    '.ksr .bad{color:var(--os-bad-ink,#F47C7C)}.ksr .good{color:var(--os-good-ink,#2fbf5b)}.ksr .warn{color:var(--os-warn-ink,#F2C46D)}.ksr .ai{color:var(--os-ai,#B48CFF)}.ksr .muted{color:var(--os-ink-2,#A6A8B5)}' +
    '.ksr .two{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}' +
    '.ksr .bar{display:grid;grid-template-columns:minmax(90px,38%) 1fr 64px;gap:8px;align-items:center;padding:3px 0;font-size:13px}' +
    '.ksr .bar .n{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.ksr .bar .t{height:8px;border-radius:5px;background:var(--os-surface-2,#24252F);overflow:hidden}' +
    '.ksr .bar .t i{display:block;height:100%;border-radius:5px}.ksr .bar .p{text-align:right;font-weight:800;font-variant-numeric:tabular-nums}' +
    '.ksr .tw{overflow-x:auto;-webkit-overflow-scrolling:touch}' +
    '.ksr table{width:100%;border-collapse:collapse;font-size:12.5px;min-width:640px}' +
    '.ksr th{text-align:left;font-size:11px;font-weight:800;color:var(--os-ink-2,#A6A8B5);padding:6px 8px;border-bottom:1px solid var(--os-surface-2,#24252F);white-space:nowrap}' +
    '.ksr td{padding:7px 8px;border-bottom:1px solid var(--os-surface-2,#24252F);vertical-align:top}' +
    '.ksr td.num,.ksr th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}' +
    '.ksr tr[data-id]{cursor:pointer}.ksr tr[data-id]:hover td{background:var(--os-surface-2,#24252F)}' +
    '.ksr .path{font-size:11.5px;color:var(--os-ink-2,#A6A8B5)}' +
    '.ksr ul{margin:0;padding-left:18px}.ksr li{margin:3px 0}' +
    '.ksr .q{border-left:3px solid var(--os-accent,#4C8DF6);padding:4px 10px;margin:6px 0;font-size:13px}' +
    '.ksr details summary{cursor:pointer;font-weight:800;margin:20px 0 6px;font-size:14px}' +
    '.ksr .note{font-size:12px;color:var(--os-ink-2,#A6A8B5);margin-top:6px}' +
    '.ksr .warnbox{border:1px dashed var(--os-warn,#F2C46D);border-radius:12px;padding:9px 12px;font-size:12px;color:var(--os-warn-ink,#F2C46D);margin-top:16px}' +
    '.ksr dl{display:grid;grid-template-columns:max-content 1fr;gap:4px 14px;margin:0;font-size:12.5px}.ksr dt{color:var(--os-ink-2,#A6A8B5)}.ksr dd{margin:0}';

  function bars(list, en, kind) {
    if (!list.length) return '<div class="meta">' + (en ? 'None clear' : 'Ninguna clara') + '</div>';
    var max = Math.max.apply(null, list.map(function (x) { return Math.abs(x.pct) || 0; })) || 1;
    var col = kind === 'good' ? 'var(--os-good,#2fbf5b)' : 'var(--os-bad,#f06565)';
    return list.map(function (x) {
      return '<div class="bar"><span class="n" title="' + esc(x.label) + '">' + esc(x.label) + '</span>' +
        '<span class="t"><i style="width:' + Math.max(4, Math.abs(x.pct) / max * 100) + '%;background:' + col + '"></i></span>' +
        '<span class="p ' + kind + '">' + pct(x.pct, en) + '</span></div>';
    }).join('');
  }

  function render(d, en) {
    var R = d.report || {}, K = R.kpis || {}, M = R.method || {}, rows = R.rows || (d.impacts || []);
    var lose = rows.filter(function (r) { return r.pct < 0; }).sort(function (a, b) { return a.pct - b.pct; }).slice(0, 8);
    var win = rows.filter(function (r) { return r.pct > 0; }).sort(function (a, b) { return b.pct - a.pct; }).slice(0, 8);
    var h = '<div class="ksr"><style>' + CSS + '</style>';
    h += '<div class="top"><span class="tag sim">🧪 ' + (en ? 'SIMULATION · HYPOTHETICAL SCENARIO' : 'SIMULACIÓN · ESCENARIO HIPOTÉTICO') + '</span>' +
      '<span class="meta">' + esc(when(M.generated_at, en)) + '</span><span class="sp"></span>' +
      '<button type="button" class="btn" data-ksr="copy">📋 ' + (en ? 'Copy summary' : 'Copiar resumen') + '</button>' +
      '<button type="button" class="btn" data-ksr="print">🖨 PDF</button></div>';
    if (R.headline) h += '<div class="hl">' + esc(R.headline) + '</div>';
    var sub = [d.theme ? (en ? 'At stake: ' : 'En juego: ') + d.theme : '', d.actor ? (en ? 'Who acts: ' : 'Quién actúa: ') + d.actor : ''].filter(Boolean).join(' · ');
    if (sub) h += '<div class="meta">' + esc(sub) + '</div>';

    // cifras clave
    function kpi(l, v, s, cls) { return '<div class="kpi"><div class="l">' + esc(l) + '</div><div class="v ' + (cls || '') + '">' + v + '</div>' + (s ? '<div class="s">' + esc(s) + '</div>' : '') + '</div>'; }
    if (K.n_companies != null) {
      h += '<div class="kpis">' +
        kpi(en ? 'Companies hit' : 'Empresas golpeadas', esc(K.n_hit), K.avg_hit_pct != null ? (en ? 'average ' : 'promedio ') + pct(K.avg_hit_pct, en) : '', 'bad') +
        kpi(en ? 'Could benefit' : 'Podrían ganar', esc(K.n_benefit), '', 'good') +
        kpi(en ? 'Sectors · countries' : 'Sectores · países', esc(K.n_sectors) + ' · ' + esc(K.n_countries), '') +
        kpi(en ? 'Market cap exposed' : 'Capitalización expuesta', bil(K.mcap_hit_b, en), (en ? 'of the companies hit' : 'de las golpeadas') + (K.n_with_mcap < K.n_companies ? ' · ' + K.n_with_mcap + '/' + K.n_companies + (en ? ' with live data' : ' con dato en vivo') : '')) +
        kpi(en ? 'Value at stake' : 'Valor en juego', bil(K.value_loss_b, en), (en ? 'cap × estimated %' : 'capitalización × % estimado'), 'bad') +
        (K.worst ? kpi(en ? 'Hardest hit' : 'Golpe más fuerte', pct(K.worst.pct, en), K.worst.label, 'bad') : '') +
        '</div>';
    }

    // resumen ejecutivo
    h += '<h3>' + (en ? 'Executive summary' : 'Resumen ejecutivo') + '</h3><div class="card">' +
      (d.mechanism ? '<p style="margin:0 0 8px">💡 ' + esc(d.mechanism) + '</p>' : '') +
      (d.narrative ? '<p style="margin:0;white-space:pre-wrap">' + esc(d.narrative) + '</p>' : '') + '</div>';

    // tu cartera
    var P = R.portfolio || {};
    h += '<h3>💼 ' + (en ? 'Your portfolio in this scenario' : 'Tu cartera en este escenario') + '</h3><div class="card">';
    if (P.status === 'ok') {
      h += '<div class="kpis" style="margin-top:0">' +
        kpi(en ? 'Estimated effect' : 'Efecto estimado', usd(P.est_usd, en), pct(P.est_pct, en) + (en ? ' of ' : ' de ') + usd(P.total_usd, en), P.est_usd < 0 ? 'bad' : 'good') +
        kpi(en ? 'Positions affected' : 'Posiciones afectadas', esc(P.positions.length), (P.n_untouched ? P.n_untouched + (en ? ' not affected' : ' sin efecto') : '')) + '</div>' +
        '<div class="tw" style="margin-top:10px"><table><thead><tr><th>' + (en ? 'Position' : 'Posición') + '</th><th class="num">' + (en ? 'Amount' : 'Monto') + '</th><th class="num">' + (en ? 'Est. %' : '% est.') + '</th><th class="num">' + (en ? 'Est. effect' : 'Efecto est.') + '</th><th>' + (en ? 'How it reaches you' : 'Cómo te llega') + '</th></tr></thead><tbody>' +
        P.positions.map(function (x) {
          var c = CHAN[x.channel];
          return '<tr data-id="' + esc(x.id) + '"><td><b>' + esc(x.label) + '</b> <span class="meta">' + esc(x.symbol || '') + '</span></td><td class="num">' + usd(x.usd, en) + '</td>' +
            '<td class="num ' + (x.pct < 0 ? 'bad' : 'good') + '">' + pct(x.pct, en) + '</td><td class="num ' + (x.est_usd < 0 ? 'bad' : 'good') + '">' + usd(x.est_usd, en) + '</td>' +
            '<td>' + (c ? '<span class="' + c[2] + '">' + esc(en ? c[1] : c[0]) + '</span>' : '') + (x.path && x.path.indexOf('→') >= 0 ? '<div class="path">' + esc(x.path) + '</div>' : '') + '</td></tr>';
        }).join('') + '</tbody></table></div><div class="note">' + esc(P.note || '') + '</div>';
    } else if (P.status === 'untouched') {
      h += '<div>✅ ' + (en ? 'None of your ' + P.n_untouched + ' positions appears in this scenario.' : 'Ninguna de tus ' + P.n_untouched + ' posiciones aparece en este escenario.') + '</div>';
    } else {
      h += '<div class="meta">' + (en ? 'Add positions in Portfolios to see what this scenario would mean for your money.' : 'Agrega posiciones en Carteras para ver qué significaría este escenario para tu dinero.') + '</div>';
    }
    h += '</div>';

    // ganadoras y perdedoras
    h += '<h3>' + (en ? 'Who loses and who could gain' : 'Quién pierde y quién podría ganar') + '</h3><div class="two">' +
      '<div class="card"><div class="meta bad" style="font-weight:800;margin-bottom:6px">▼ ' + (en ? 'Most hit' : 'Más perjudicadas') + '</div>' + bars(lose, en, 'bad') + '</div>' +
      '<div class="card"><div class="meta good" style="font-weight:800;margin-bottom:6px">▲ ' + (en ? 'Possible winners' : 'Posibles ganadoras') + '</div>' + bars(win, en, 'good') + '</div></div>';

    // por sector / por país
    var S = R.by_sector || [], C = R.by_country || [];
    if (S.length) {
      h += '<h3>' + (en ? 'By sector' : 'Por sector') + '</h3><div class="card tw"><table style="min-width:420px"><thead><tr><th>' + (en ? 'Sector' : 'Sector') + '</th><th class="num">' + (en ? 'Companies' : 'Empresas') + '</th><th class="num">▼ / ▲</th><th class="num">' + (en ? 'Avg %' : '% medio') + '</th><th class="num">' + (en ? 'Value at stake' : 'Valor en juego') + '</th></tr></thead><tbody>' +
        S.map(function (x) { return '<tr><td>' + esc(x.label) + '</td><td class="num">' + x.n + '</td><td class="num">' + x.n_hit + ' / ' + x.n_benefit + '</td><td class="num ' + (x.avg_pct < 0 ? 'bad' : 'good') + '">' + pct(x.avg_pct, en) + '</td><td class="num">' + bil(x.value_b || null, en) + '</td></tr>'; }).join('') +
        '</tbody></table></div>';
    }
    if (C.length) {
      h += '<h3>' + (en ? 'By country' : 'Por país') + '</h3><div class="card">' + C.map(function (x) {
        return '<span class="tag" style="display:inline-block;margin:3px 4px 3px 0;font-size:12px">' + esc(x.label) + ' · ' + x.n + ' · <span class="' + (x.avg_pct < 0 ? 'bad' : 'good') + '">' + pct(x.avg_pct, en) + '</span></span>';
      }).join('') + '</div>';
    }

    // tabla completa
    h += '<h3>' + (en ? 'Every company, and how the shock reaches it' : 'Todas las empresas y cómo les llega el golpe') + ' <span class="meta">(' + rows.length + ')</span></h3>' +
      '<div class="card tw"><table><thead><tr><th>' + (en ? 'Company' : 'Empresa') + '</th><th>' + (en ? 'Sector · country' : 'Sector · país') + '</th><th>' + (en ? 'Channel' : 'Canal') + '</th><th class="num">' + (en ? 'Est. %' : '% est.') + '</th><th class="num">' + (en ? 'Market cap' : 'Capitalización') + '</th><th class="num">' + (en ? 'Value at stake' : 'Valor en juego') + '</th><th class="num">' + (en ? 'Today' : 'Hoy') + '</th></tr></thead><tbody>' +
      rows.map(function (r) {
        var c = CHAN[r.channel];
        return '<tr data-id="' + esc(r.id) + '"><td><b>' + esc(r.label) + '</b> <span class="meta">' + esc(r.ticker || '') + '</span>' +
          (r.path && r.path.indexOf('→') >= 0 ? '<div class="path">' + esc(r.path) + '</div>' : (r.rationale ? '<div class="path">' + esc(r.rationale) + '</div>' : '')) + '</td>' +
          '<td>' + esc([r.sector_label, r.country_label].filter(Boolean).join(' · ') || '—') + '</td>' +
          '<td>' + (c ? '<span class="' + c[2] + '">' + esc(en ? c[1] : c[0]) + '</span>' : '—') + '</td>' +
          '<td class="num ' + (r.pct < 0 ? 'bad' : 'good') + '"><b>' + pct(r.pct, en) + '</b></td>' +
          '<td class="num">' + bil(r.mcap_b, en) + '</td><td class="num">' + bil(r.value_at_stake_b, en) + '</td>' +
          '<td class="num">' + (r.change_pct != null ? '<span class="' + (r.change_pct < 0 ? 'bad' : 'good') + '">' + pct(r.change_pct, en) + '</span>' : '—') + '</td></tr>';
      }).join('') + '</tbody></table><div class="note">' + (en ? 'Tap a company to open its X-Ray. "Today" = real move of the day (live), not the scenario.' : 'Toca una empresa para abrir su X-Ray. «Hoy» = movimiento real del día (en vivo), no el escenario.') + '</div></div>';

    // desarrollo, agentes, vigilar
    var rounds = Array.isArray(d.rounds) ? d.rounds : [];
    if (rounds.length) {
      h += '<h3>' + (en ? 'How it unfolds' : 'Cómo se desarrolla') + '</h3><div class="card">' + rounds.map(function (x) {
        return '<div style="margin:4px 0"><b>' + (en ? 'Phase ' : 'Fase ') + esc(x.round) + '.</b> ' + (x.events || []).map(esc).join(' · ') + '</div>';
      }).join('') + '</div>';
    }
    var watch = Array.isArray(d.watch) ? d.watch : [];
    if (watch.length) h += '<h3>👁 ' + (en ? 'What to watch (signals the scenario is happening)' : 'Qué vigilar (señales de que el escenario ocurre)') + '</h3><div class="card"><ul>' + watch.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul></div>';
    var quotes = Array.isArray(d.quotes) ? d.quotes : [], agents = Array.isArray(d.agents) ? d.agents : [];
    if (quotes.length || agents.length) {
      h += '<details><summary>' + (en ? 'The debate: what each actor says (' : 'El debate: qué dice cada actor (') + agents.length + ')</summary><div class="card">' +
        quotes.map(function (x) { return '<div class="q"><b>' + esc(x.agent) + ':</b> «' + esc(x.quote) + '»</div>'; }).join('') +
        (agents.length ? '<div class="meta" style="margin-top:8px">' + agents.map(function (a) { return esc(a.name) + (a.stance ? ' — ' + esc(a.stance) : ''); }).join(' · ') + '</div>' : '') + '</div></details>';
    }

    // metodología
    h += '<details><summary>' + (en ? 'Method and sources' : 'Metodología y fuentes') + '</summary><div class="card"><dl>' +
      '<dt>' + (en ? 'Who sets the %' : 'Quién pone los %') + '</dt><dd>' + esc(M.pct_source_text || '—') + '</dd>' +
      '<dt>' + (en ? 'AI model' : 'Modelo de IA') + '</dt><dd>' + esc(M.model || (en ? 'none (structural estimate)' : 'ninguno (estimación estructural)')) + '</dd>' +
      '<dt>' + (en ? 'Chain engine' : 'Motor de la cadena') + '</dt><dd>' + esc(M.kernel_semver ? 'kernel.params ' + M.kernel_semver : '—') + '</dd>' +
      '<dt>' + (en ? 'Debate' : 'Debate') + '</dt><dd>' + esc((M.agents || 0) + (en ? ' actors · ' : ' actores · ') + (M.rounds || 0) + (en ? ' rounds' : ' rondas')) + '</dd>' +
      '<dt>' + (en ? 'Live prices' : 'Precios en vivo') + '</dt><dd>' + esc(M.caps_source ? M.caps_source + ' · ' + when(M.caps_as_of, en) : (en ? 'not available now' : 'no disponibles ahora')) + '</dd>' +
      '<dt>' + (en ? 'Graph' : 'Grafo') + '</dt><dd>' + esc(M.graph || '—') + '</dd></dl></div></details>';
    h += '<div class="warnbox">⚠ ' + esc(M.limits || (en ? 'Hypothetical scenario: not a forecast nor a recommendation.' : 'Escenario hipotético: no es un pronóstico ni una recomendación.')) + '</div>';
    return h + '</div>';
  }

  function summaryText(d, en) {
    var R = d.report || {}, P = R.portfolio || {}, lines = [];
    lines.push((en ? 'Scenario: ' : 'Escenario: ') + (d.scenario || d.theme || ''));
    if (R.headline) lines.push(R.headline);
    if (d.narrative) lines.push(d.narrative);
    if (P.status === 'ok') lines.push((en ? 'My portfolio: ' : 'Mi cartera: ') + usd(P.est_usd, en) + ' (' + pct(P.est_pct, en) + ')');
    (R.rows || []).slice(0, 10).forEach(function (r) { lines.push('· ' + r.label + (r.ticker ? ' (' + r.ticker + ')' : '') + ': ' + pct(r.pct, en)); });
    lines.push((R.method || {}).limits || '');
    return lines.filter(Boolean).join('\n');
  }

  function printIt(d, en) {
    var w = window.open('', '_blank');
    if (!w) return;
    var light = '--os-ink:#16171D;--os-ink-2:#555866;--os-surface:#F4F5F8;--os-surface-2:#E3E5EC;--os-bad:#d64545;--os-bad-ink:#B42318;--os-good:#16a34a;--os-good-ink:#15803D;--os-warn:#b7791f;--os-warn-ink:#8A5A00;--os-ai:#6D28D9;--os-accent:#2563EB';
    w.document.write('<!doctype html><html><head><meta charset="utf-8"><title>Khipus — ' + esc(d.scenario || (en ? 'Scenario report' : 'Informe de escenario')) + '</title>' +
      '<style>body{font-family:Inter,system-ui,sans-serif;margin:28px;background:#fff;' + light + '}.btn{display:none!important}details{display:block}details>summary{list-style:none}' +
      '@media print{body{margin:12mm}.card,.kpi{break-inside:avoid}}</style></head><body>' +
      '<div style="font-weight:800;font-size:13px;letter-spacing:.08em;color:#555866">KHIPUS FINANCE INTELLIGENCE</div>' +
      '<h1 style="margin:4px 0 10px;font-size:22px">' + esc(d.scenario || '') + '</h1>' + render(d, en) + '</body></html>');
    w.document.close();
    w.document.querySelectorAll('details').forEach(function (x) { x.open = true; });
    setTimeout(function () { try { w.focus(); w.print(); } catch (e) {} }, 300);
  }

  function bind(root, d, en, onCompany) {
    if (!root) return;
    root.querySelectorAll('tr[data-id]').forEach(function (tr) {
      tr.addEventListener('click', function () { if (onCompany) onCompany(tr.getAttribute('data-id')); });
    });
    root.querySelectorAll('[data-ksr]').forEach(function (b) {
      b.addEventListener('click', function () {
        var a = b.getAttribute('data-ksr');
        if (a === 'print') printIt(d, en);
        else if (a === 'copy') {
          var t = summaryText(d, en);
          try { navigator.clipboard.writeText(t).then(function () { b.textContent = '✓ ' + (en ? 'Copied' : 'Copiado'); }); } catch (e) {}
        }
      });
    });
  }

  window.KhipuSimReport = { render: render, bind: bind, summaryText: summaryText };
})();
