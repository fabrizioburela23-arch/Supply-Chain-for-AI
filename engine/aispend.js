/* ============================================================================
   engine/aispend.js — 💰 GASTO DE IA (🩺 Sistema → pestaña "Gasto IA")

   Pedido (2026-10-02): "saber el saldo del API… controlar el gasto, y de dónde
   está gastando en cada caso porque hay más de una IA conectada".
   Lee GET /api/ai/usage (core/ai_usage.py) y muestra: hoy / semana / mes vs
   límites, por proveedor (Claude, Gemini, NVIDIA), por modelo, por función de
   la app, por persona/cliente, por día y las últimas llamadas. Los límites se
   editan con el PIN (POST /api/ai/usage/limits vía window._tradeFetch).
   Si hay ANTHROPIC_ADMIN_KEY, muestra además lo FACTURADO por Anthropic.
   window.KhipuSpend.render(elId)
   ============================================================================ */
(function () {
  'use strict';
  function isEn() { var l = window.LANG; if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = null; } } return l === 'en'; }
  function L(es, en) { return isEn() ? en : es; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function usd(v) {
    v = Number(v) || 0;
    if (v === 0) return '$0';
    if (v < 0.01) return '<$0.01';
    return '$' + v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  function tok(n) { n = Number(n) || 0; return n >= 1e6 ? (n / 1e6).toFixed(1) + 'M' : n >= 1e3 ? Math.round(n / 1e3) + 'k' : String(n); }
  function actor() { var a = null; try { a = localStorage.getItem('khipu_actor'); } catch (e) {} return (a && a.trim()) || 'operador'; }
  // Colores de MARCA de cada proveedor: solo para puntos y barras (rellenos), nunca para texto
  // (el verde de NVIDIA o el rosa de Jev no llegan a 4.5:1 sobre blanco): el nombre va en --os-ink.
  var PROV = { claude: ['Claude (Anthropic)', '#D97757'], gemini: ['Gemini (Google)', '#4C8DF6'], nvidia: ['NVIDIA', '#76B900'], typesafe: ['Jev (TypeSafe)', '#E551BA'] };
  // Colores SEMÁNTICOS de Khipus OS (tokens; el valor tras la coma = respaldo oscuro). Rellenos vivos → --os-good/bad/warn;
  // TEXTO → --os-*-ink (contraste AA en claro y oscuro).
  var C = { good: 'var(--os-good,#2fbf5b)', bad: 'var(--os-bad,#f06565)', warn: 'var(--os-warn,#F2C46D)', accent: 'var(--os-accent,#4C8DF6)',
    ai: 'var(--os-ai,#B48CFF)', goodInk: 'var(--os-good-ink,#2fbf5b)', badInk: 'var(--os-bad-ink,#F47C7C)', warnInk: 'var(--os-warn-ink,#F2C46D)' };

  var S = { el: null, days: 30, data: null, editing: false, msg: null };

  function dot(col) { return '<i class="sp-dot" style="background:' + col + '"></i>'; }
  function bar(frac, col) {
    var w = Math.max(0, Math.min(100, Math.round((frac || 0) * 100)));
    return '<div class="sp-track"><i style="width:' + w + '%;background:' + col + '"></i></div>';
  }
  function meter(label, spent, limit, hint) {
    var frac = limit ? spent / limit : 0, col = frac >= 1 ? C.bad : frac >= 0.8 ? C.warn : C.good;
    return '<div class="sp-meter">' +
      '<div class="sp-lab">' + esc(label) + '</div>' +
      '<div class="sp-big">' + usd(spent) + '</div>' +
      (limit ? '<div class="sp-mut">' + L('de ', 'of ') + usd(limit) + ' · ' + Math.round(frac * 100) + '%</div>' + bar(frac, col)
        : '<div class="sp-mut">' + esc(hint || L('sin límite', 'no limit')) + '</div>') + '</div>';
  }
  function table(title, rows, labelFn, total) {
    if (!rows || !rows.length) return '';
    var max = Math.max.apply(null, rows.map(function (r) { return r.cost_usd; }).concat([0.000001]));
    return '<div class="sp-card"><div class="sp-h">' + esc(title) + '</div>' +
      rows.slice(0, 12).map(function (r) {
        var lab = labelFn(r), col = lab[1] || C.accent;
        return '<div class="sp-row">' +
          '<div class="sp-rl"><span class="sp-name">' + lab[0] + '</span>' +
          '<span class="sp-val"><b>' + usd(r.cost_usd) + '</b> <span class="sp-mut">· ' + r.calls + L(' llamadas', ' calls') + ' · ' + tok(r.tokens_in) + '↓ ' + tok(r.tokens_out) + '↑</span></span></div>' +
          bar(r.cost_usd / max, col) + '</div>';
      }).join('') + '</div>';
  }
  function days(rows) {
    if (!rows || !rows.length) return '';
    var max = Math.max.apply(null, rows.map(function (r) { return r.cost_usd; }).concat([0.000001]));
    return '<div class="sp-card"><div class="sp-h">' + L('Gasto por día', 'Spend per day') + '</div>' +
      '<div class="sp-days">' + rows.map(function (r) {
        return '<div title="' + esc(r.key + ' · ' + usd(r.cost_usd) + ' · ' + r.calls) + '" style="height:' + Math.max(2, Math.round(r.cost_usd / max * 70)) + 'px"></div>';
      }).join('') + '</div><div class="sp-axis"><span>' + esc(rows[0].key) + '</span><span>' + esc(rows[rows.length - 1].key) + '</span></div></div>';
  }
  function recent(rows) {
    if (!rows || !rows.length) return '';
    return '<details class="sp-card sp-recent"><summary>' + L('Últimas llamadas', 'Latest calls') + ' (' + rows.length + ')</summary>' +
      rows.map(function (r) {
        var p = PROV[r.provider] || [r.provider, 'var(--os-ink-3,#6E7080)'];
        var t = new Date(r.at);
        return '<div class="sp-call">' +
          '<span class="sp-mut">' + (isNaN(t) ? '' : t.toLocaleTimeString(isEn() ? 'en' : 'es', { hour: '2-digit', minute: '2-digit' })) + '</span>' +
          '<b>' + dot(p[1]) + esc(p[0]) + '</b><span>' + esc(r.model) + '</span><span>· ' + esc(r.feature_label || r.feature) + '</span><span>· ' + esc(r.who) + '</span>' +
          '<span class="sp-amt">' + usd(r.cost_usd) + (r.estimated ? ' ≈' : '') + '</span></div>';
      }).join('') + '</details>';
  }
  function limitsForm(d) {
    var lm = d.limits || {}, pf = lm.per_feature_daily_usd || {};
    var feats = (d.by_feature || []).map(function (f) { return f; });
    var inp = function (id, v, ph) { return '<input id="' + id + '" class="sp-in" type="number" min="0" step="0.5" value="' + esc(v == null ? '' : v) + '" placeholder="' + esc(ph || '') + '">'; };
    var row = function (lab, html) { return '<div class="sp-frow"><span>' + lab + '</span>' + html + '</div>'; };
    var provs = ['claude', 'gemini', 'nvidia', 'typesafe'];
    return '<div class="sp-card sp-form">' +
      row(L('Límite diario total (USD)', 'Total daily limit (USD)'), inp('sp-daily', lm.daily_usd)) +
      row(L('Límite mensual total (USD)', 'Total monthly limit (USD)'), inp('sp-month', lm.monthly_usd)) +
      row(L('Límite diario por persona/cliente (0 = sin límite)', 'Daily limit per person/client (0 = none)'), inp('sp-who', lm.per_who_daily_usd)) +
      '<div class="sp-mut sp-fh">' + L('Límite diario por función (vacío = sin límite):', 'Daily limit per feature (empty = none):') + '</div>' +
      feats.map(function (f) { return row(esc(f.label || f.key), inp('sp-f-' + f.key, pf[f.key], '—')); }).join('') +
      '<div class="sp-mut sp-fh">' + L('Proveedores activos:', 'Active providers:') + '</div>' +
      '<div class="sp-provs">' + provs.map(function (p) { return '<label class="sp-chk"><input type="checkbox" id="sp-p-' + p + '"' + ((lm.blocked_providers || []).indexOf(p) < 0 ? ' checked' : '') + '> ' + dot(PROV[p][1]) + esc(PROV[p][0]) + '</label>'; }).join('') + '</div>' +
      '<div class="sp-actions"><button type="button" class="sp-btn" id="sp-save">🔒 ' + L('Guardar límites (PIN)', 'Save limits (PIN)') + '</button>' +
      '<button type="button" class="sp-btn ghost" id="sp-cancel">' + L('Cancelar', 'Cancel') + '</button></div></div>';
  }

  function paint() {
    var el = S.el; if (!el) return;
    ensureStyles();
    // tokens --os-* de Khipus OS (claro/oscuro) aunque 🩺 Sistema viva fuera de #bcp-ov
    if (el.classList) { el.classList.add('kos-themed'); el.classList.add('sp-root'); }
    var d = S.data;
    if (!d) { el.innerHTML = '<div class="sp-empty"><span class="sp-spin" aria-hidden="true"></span>' + L('Cargando gasto…', 'Loading spend…') + '</div>'; return; }
    if (d._err) { el.innerHTML = '<div class="sp-msg warn">' + esc(d._err) + '</div>'; return; }
    var t = d.totals || {}, lm = d.limits || {}, ab = d.anthropic_billed || {};
    var provLabel = function (r) { var p = PROV[r.key] || [r.key, C.accent]; return ['<b>' + dot(p[1]) + esc(p[0]) + '</b>', p[1]]; };
    el.innerHTML =
      '<p class="sp-sub">' + L('Cuánto gastas en IA, en qué proveedor, en qué parte de la app y quién lo pidió. Al llegar a un límite, la app <b>deja de llamar a la IA</b> (no cobra) y lo avisa.',
        'How much you spend on AI, on which provider, in which part of the app and who asked. When a limit is reached the app <b>stops calling the AI</b> (no charge) and says so.') + '</p>' +
      (S.msg ? '<div class="sp-msg ' + (S.msg.bad ? 'warn' : 'ok') + '" role="status">' + esc(S.msg.text) + '</div>' : '') +
      '<div class="sp-meters">' + meter(L('Hoy', 'Today'), t.today, lm.daily_usd) + meter(L('Este mes', 'This month'), t.month, lm.monthly_usd) +
        meter(L('Últimos 7 días', 'Last 7 days'), t.week, 0, (t.calls_today || 0) + L(' llamadas hoy', ' calls today')) + '</div>' +
      '<div class="sp-billed">' +
        (ab.available ? '🧾 <b>' + L('Facturado por Anthropic este mes: ', 'Billed by Anthropic this month: ') + usd(ab.month_usd) + '</b> <span class="sp-mut">(' + L('dato real de su reporte de costos', 'real figure from their cost report') + ')</span>'
          : '🧾 ' + L('Saldo restante: ningún proveedor lo publica por API. Míralo en ', 'Remaining balance: no provider exposes it via API. Check it at ') +
            '<a href="https://console.anthropic.com/settings/billing" target="_blank" rel="noopener">console.anthropic.com → Billing</a>, ' +
            '<a href="https://aistudio.google.com/" target="_blank" rel="noopener">Google AI Studio</a> ' + L('y', 'and') + ' <a href="https://build.nvidia.com/" target="_blank" rel="noopener">build.nvidia.com</a>. ' +
            '<span class="sp-mut">' + L('Para ver aquí lo facturado REAL por Anthropic, agrega en Railway la variable ANTHROPIC_ADMIN_KEY (llave Admin, solo cuentas de organización).', 'To see Anthropic\'s REAL billed amount here, add the ANTHROPIC_ADMIN_KEY variable on Railway (Admin key, organization accounts only).') + '</span>') + '</div>' +
      '<div class="sp-bar">' +
        '<div class="sp-seg" role="group" aria-label="' + esc(L('Periodo', 'Period')) + '">' +
        [7, 30, 90].map(function (n) { return '<button type="button" data-days="' + n + '"' + (S.days === n ? ' class="on" aria-pressed="true"' : ' aria-pressed="false"') + '>' + n + L(' días', ' days') + '</button>'; }).join('') + '</div>' +
        '<button type="button" class="sp-btn ghost" id="sp-edit" style="margin-left:auto"' + (S.editing ? ' aria-expanded="true"' : ' aria-expanded="false"') + '>⚙ ' + L('Límites', 'Limits') + '</button>' +
        '<button type="button" class="sp-btn ghost sp-icon" id="sp-refresh" title="' + esc(L('Actualizar', 'Refresh')) + '" aria-label="' + esc(L('Actualizar', 'Refresh')) + '">↻</button></div>' +
      (S.editing ? limitsForm(d) : '') +
      table(L('Por proveedor de IA', 'By AI provider'), d.by_provider, provLabel) +
      table(L('En qué parte de la app', 'In which part of the app'), d.by_feature, function (r) { return [esc(r.label || r.key), C.ai]; }) +
      table(L('Quién lo pidió (persona / cliente)', 'Who asked (person / client)'), d.by_who, function (r) { return [esc(r.key), C.accent]; }) +
      table(L('Por modelo', 'By model'), d.by_model, function (r) { return [esc(r.key), C.warn]; }) +
      jevCard() +
      days(d.by_day) + recent(d.recent) +
      '<div class="sp-note">' + esc(isEn() ? d.note_en : d.note_es) +
        (d.source === 'memory' ? ' ' + L('Sin base de datos: el historial se pierde al reiniciar el servidor.', 'No database: history is lost when the server restarts.') : '') + '</div>';
    el.querySelectorAll('[data-days]').forEach(function (b) { b.onclick = function () { S.days = +b.getAttribute('data-days'); load(); }; });
    var r = document.getElementById('sp-refresh'); if (r) r.onclick = load;
    var e = document.getElementById('sp-edit'); if (e) e.onclick = function () { S.editing = !S.editing; S.msg = null; paint(); };
    var c = document.getElementById('sp-cancel'); if (c) c.onclick = function () { S.editing = false; paint(); };
    var sv = document.getElementById('sp-save'); if (sv) sv.onclick = save;
  }

  // 🧭 JEV (core/decide.py): modelo de DECISIÓN en modo sombra — acuerdo con el sistema por función
  function jevCard() {
    var j = S.jev;
    var h = '<div class="sp-card sp-jev"><div class="sp-jh"><b>🧭 Jev (TypeSafe) — ' + L('decisiones', 'decisions') + '</b> ';
    if (!j) h += '<span class="sp-mut">' + L('cargando…', 'loading…') + '</span></div>';
    else if (!j.available) h += '</div><div class="sp-mut">' + L('No conectado. Para activarlo, agrega en Railway la variable TYPESAFE_API_KEY. Arranca en modo sombra: decide, pero no manda.', 'Not connected. To enable it, add the TYPESAFE_API_KEY variable on Railway. It starts in shadow mode: it decides but does not act.') + '</div>';
    else {
      h += '<span class="sp-pill ai">' + (j.shadow ? L('MODO SOMBRA', 'SHADOW MODE') : L('ACTIVO', 'ACTIVE')) + '</span></div>' +
        '<div class="sp-mut" style="margin:4px 0 6px">' + esc(isEn() ? j.note_en : j.note_es) + '</div>';
      if (j._pin) h += '<div class="sp-warn">' + L('Pon tu PIN de operador (🔒 Límites) para ver el acuerdo por función.', 'Enter your operator PIN (🔒 Limits) to see agreement per feature.') + '</div>';
      else if (!(j.features || []).length) h += '<div class="sp-mut">' + L('Aún sin decisiones registradas: pregúntale algo a Khipu y vuelve.', 'No decisions recorded yet: ask Khipu something and come back.') + '</div>';
      else h += (j.features || []).map(function (f) {
        var lab = { chat_gate: L('Portero del chat', 'Chat gatekeeper') }[f.feature] || f.feature;
        return '<div class="sp-jrow"><span style="flex:1">' + esc(lab) + '</span>' +
          '<span class="sp-num">' + (f.agree_pct == null ? '—' : f.agree_pct + '%') + '</span>' +
          '<span class="sp-mut">' + f.n + ' ' + L('comparaciones', 'comparisons') + '</span>' +
          '<span class="sp-pill' + (f.control ? ' good' : '') + '">' + (f.control ? L('manda', 'in control') : L('sombra', 'shadow')) + '</span></div>';
      }).join('');
    }
    return h + '</div>';
  }
  function loadJev() {
    var base = (window.BASE || '');
    fetch(base + '/api/decide/status').then(function (r) { return r.json(); }).then(function (st) {
      if (!st.available) { S.jev = st; paint(); return; }
      var p = typeof window._tradeFetch === 'function' ? window._tradeFetch(base + '/api/decide/shadow?days=' + S.days, {}, false) : fetch(base + '/api/decide/shadow?days=' + S.days);
      return p.then(function (r) { return r.json().then(function (j) { if (!r.ok) j = { available: true, shadow: st.shadow, _pin: true, note_es: '', note_en: '' }; S.jev = j; paint(); }); });
    }).catch(function () { S.jev = { available: false }; paint(); });
  }

  function num(id) { var x = document.getElementById(id); if (!x || x.value === '') return null; var v = parseFloat(x.value); return isNaN(v) ? null : v; }
  function save() {
    var d = S.data || {}, pf = {};
    (d.by_feature || []).forEach(function (f) { var v = num('sp-f-' + f.key); if (v != null && v > 0) pf[f.key] = v; });
    var blocked = ['claude', 'gemini', 'nvidia', 'typesafe'].filter(function (p) { var x = document.getElementById('sp-p-' + p); return x && !x.checked; });
    var limits = { per_feature_daily_usd: pf, blocked_providers: blocked };
    var dv = num('sp-daily'), mv = num('sp-month'), wv = num('sp-who');
    if (dv != null) limits.daily_usd = dv;
    if (mv != null) limits.monthly_usd = mv;
    if (wv != null) limits.per_who_daily_usd = wv;
    var opts = { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ actor: actor(), limits: limits }) };
    var p = typeof window._tradeFetch === 'function' ? window._tradeFetch((window.BASE || '') + '/api/ai/usage/limits', opts, true)
      : fetch((window.BASE || '') + '/api/ai/usage/limits', opts);
    p.then(function (r) { return r.json().then(function (j) { j._status = r.status; return j; }); }).then(function (j) {
      if (j._status === 200 && j.ok) { S.editing = false; S.msg = { text: L('Límites guardados.', 'Limits saved.') }; load(); }
      else { S.msg = { bad: true, text: (isEn() ? (j.error_en || j.error) : j.error) || (j._status === 401 ? L('PIN incorrecto.', 'Wrong PIN.') : L('No se pudo guardar.', 'Could not save.')) }; paint(); }
    }).catch(function () { S.msg = { bad: true, text: L('Sin conexión con el servidor.', 'No connection to the server.') }; paint(); });
  }

  function load() {
    S.data = S.data || null; paint();
    fetch((window.BASE || '') + '/api/ai/usage?days=' + S.days + '&lang=' + (isEn() ? 'en' : 'es')).then(function (r) {
      return r.json().then(function (j) { if (!r.ok) j._err = (isEn() ? (j.error_en || j.error) : j.error) || ('HTTP ' + r.status); return j; });
    }).then(function (j) { S.data = j; paint(); loadJev(); })
      .catch(function () { S.data = { _err: L('Sin conexión con el servidor.', 'No connection to the server.') }; paint(); });
  }

  // ── estilos: Khipus OS (2026-10-10). El contenedor lleva .kos-themed → tokens --os-* de engine/cockpit.js
  // (claro = body sin .dark, oscuro = body.dark). Solo tokens; el valor tras la coma = respaldo oscuro.
  // Tarjetas sin bordes, botones píldora, periodo = control segmentado, textos semánticos AA.
  function ensureStyles() {
    if (document.getElementById('sp-styles')) return;
    var st = document.createElement('style'); st.id = 'sp-styles';
    st.textContent =
      '.sp-root{color:var(--os-ink,#F2F2F5);font-family:var(--os-font,\'Nunito\',\'Geist\',system-ui,-apple-system,\'Segoe UI\',sans-serif);font-size:13px;line-height:1.5;' +
        '-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale}' +
      '.sp-root *{box-sizing:border-box}.sp-root button,.sp-root input{font-family:inherit}' +
      '.sp-root .sp-sub{font-size:12.5px;color:var(--os-ink-2,#A6A8B5);line-height:1.55;margin:0 0 14px}' +
      '.sp-root .sp-mut{color:var(--os-ink-2,#A6A8B5);font-size:11.5px}' +
      '.sp-root .sp-meters{display:flex;gap:10px;flex-wrap:wrap}' +
      '.sp-root .sp-meter{flex:1 1 140px;min-width:0;border-radius:var(--os-r-sm,12px);padding:12px 14px;background:var(--os-surface,#17181F);' +
        'box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35))}' +
      '.sp-root .sp-lab{font-size:11px;font-weight:700;color:var(--os-ink-2,#A6A8B5);text-transform:uppercase;letter-spacing:.06em}' +
      '.sp-root .sp-big{font-size:21px;font-weight:800;letter-spacing:-.02em;margin-top:2px;font-variant-numeric:tabular-nums}' +
      '.sp-root .sp-track{height:7px;border-radius:999px;background:var(--os-surface-3,#2A2B36);overflow:hidden;margin-top:5px}' +
      '.sp-root .sp-track i{display:block;height:100%;border-radius:999px}' +
      '.sp-root .sp-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:1px;flex:none}' +
      '.sp-root .sp-billed{margin-top:12px;font-size:12px;border-radius:var(--os-r-sm,12px);padding:10px 12px;line-height:1.55;background:var(--os-surface,#17181F);' +
        'box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35));overflow-wrap:anywhere}' +
      '.sp-root .sp-billed a{color:var(--os-accent,#4C8DF6);text-decoration:none;border-bottom:1px dotted currentColor}.sp-root .sp-billed a:hover{text-decoration:none;border-bottom-style:solid}' +
      '.sp-root .sp-bar{display:flex;gap:8px;align-items:center;margin-top:12px;flex-wrap:wrap}' +
      '.sp-root .sp-seg{display:inline-flex;gap:2px;padding:3px;border-radius:18px;background:var(--os-surface-3,#2A2B36);max-width:100%}' +
      '.sp-root .sp-seg button{appearance:none;-webkit-appearance:none;border:0;cursor:pointer;min-height:30px;padding:0 12px;border-radius:999px;background:none;' +
        'color:var(--os-ink-2,#A6A8B5);font-size:12.5px;font-weight:700;white-space:nowrap;transition:background-color .15s,color .15s,box-shadow .15s}' +
      '.sp-root .sp-seg button:hover{color:var(--os-ink,#F2F2F5)}' +
      '.sp-root .sp-seg button.on{background:var(--os-surface,#17181F);color:var(--os-ink,#F2F2F5);box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35))}' +
      '.sp-root .sp-btn{appearance:none;-webkit-appearance:none;border:0;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:6px;height:36px;padding:0 16px;' +
        'border-radius:999px;background:var(--os-btn,#F2F2F5);color:var(--os-btn-ink,#111216);font-size:12.5px;font-weight:700;white-space:nowrap;transition:opacity .15s,background-color .15s,transform .1s}' +
      '.sp-root .sp-btn:hover{opacity:.88}.sp-root .sp-btn:active{transform:scale(.98)}' +
      '.sp-root .sp-btn.ghost{background:var(--os-surface-2,#1F2029);color:var(--os-ink,#F2F2F5);font-weight:600}' +
      '.sp-root .sp-btn.ghost:hover{background:var(--os-surface-3,#2A2B36);opacity:1}' +
      '.sp-root .sp-btn.sp-icon{width:36px;padding:0;font-size:15px}' +
      '.sp-root button:focus-visible,.sp-root input:focus-visible,.sp-root summary:focus-visible,.sp-root a:focus-visible{outline:2px solid var(--os-accent,#4C8DF6);outline-offset:2px}' +
      '.sp-root .sp-card{margin-top:14px;border-radius:var(--os-r,18px);padding:12px 14px;background:var(--os-surface,#17181F);' +
        'box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35));min-width:0}' +
      '.sp-root .sp-h{font-size:11px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--os-ink-2,#A6A8B5);margin-bottom:6px}' +
      '.sp-root .sp-row{padding:6px 0;border-bottom:1px solid var(--os-line,rgba(255,255,255,.07))}.sp-root .sp-row:last-child{border-bottom:0}' +
      '.sp-root .sp-rl{display:flex;justify-content:space-between;gap:8px;font-size:12.5px}' +
      '.sp-root .sp-name{overflow-wrap:anywhere;min-width:0}.sp-root .sp-name b{font-weight:700}' +
      '.sp-root .sp-val{white-space:nowrap;font-variant-numeric:tabular-nums}' +
      '.sp-root .sp-days{display:flex;align-items:flex-end;gap:2px;height:70px}' +
      '.sp-root .sp-days>div{flex:1;min-width:3px;background:var(--os-accent,#4C8DF6);opacity:.85;border-radius:3px 3px 0 0}' +
      '.sp-root .sp-axis{display:flex;justify-content:space-between;font-size:10.5px;color:var(--os-ink-2,#A6A8B5);margin-top:3px;font-variant-numeric:tabular-nums}' +
      '.sp-root .sp-recent summary{cursor:pointer;font-size:12.5px;font-weight:700;color:var(--os-ink,#F2F2F5);border-radius:6px}' +
      '.sp-root .sp-call{font-size:11.5px;padding:5px 0;border-bottom:1px solid var(--os-line,rgba(255,255,255,.07));display:flex;gap:6px;flex-wrap:wrap;align-items:center}' +
      '.sp-root .sp-call:last-child{border-bottom:0}.sp-root .sp-call b{font-weight:700;display:inline-flex;align-items:center}' +
      '.sp-root .sp-amt{margin-left:auto;font-variant-numeric:tabular-nums;font-weight:700}' +
      '.sp-root .sp-form .sp-frow{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:5px 0;font-size:12.5px}' +
      '.sp-root .sp-form .sp-fh{margin:10px 0 2px}' +
      '.sp-root .sp-in{width:96px;height:34px;padding:0 10px;border:0;border-radius:10px;background:var(--os-surface-2,#1F2029);color:var(--os-ink,#F2F2F5);' +
        'font-size:12.5px;outline:none;font-variant-numeric:tabular-nums;transition:box-shadow .15s;flex:none}' +
      '.sp-root .sp-in::placeholder{color:var(--os-ink-2,#A6A8B5)}' +
      '.sp-root .sp-in:focus{box-shadow:inset 0 0 0 1.5px var(--os-accent,#4C8DF6),0 0 0 3px var(--kos-accent-soft,rgba(76,141,246,.16))}' +
      '.sp-root .sp-provs{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:4px}' +
      '.sp-root .sp-chk{display:inline-flex;gap:6px;align-items:center;font-size:12.5px;cursor:pointer}' +
      '.sp-root .sp-chk input{width:16px;height:16px;accent-color:var(--os-accent,#4C8DF6);margin:0}' +
      '.sp-root .sp-actions{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}' +
      '.sp-root .sp-jh{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.sp-root .sp-jh b{color:var(--os-ai,#B48CFF);font-weight:800}' +
      '.sp-root .sp-jev{font-size:12.5px;line-height:1.5}' +
      '.sp-root .sp-jrow{display:flex;gap:8px;align-items:center;padding:4px 0}' +
      '.sp-root .sp-num{font-variant-numeric:tabular-nums;font-weight:700}' +
      '.sp-root .sp-pill{display:inline-flex;align-items:center;font-size:10.5px;font-weight:800;letter-spacing:.04em;border-radius:999px;padding:2px 9px;white-space:nowrap;' +
        'background:var(--os-surface-2,#1F2029);color:var(--os-ink-2,#A6A8B5)}' +
      '.sp-root .sp-pill.ai{color:var(--os-ai,#B48CFF);background:color-mix(in srgb,var(--os-ai,#B48CFF) 13%,transparent)}' +
      '.sp-root .sp-pill.good{color:var(--os-good-ink,#2fbf5b);background:color-mix(in srgb,var(--os-good,#2fbf5b) 13%,transparent)}' +
      '.sp-root .sp-warn{color:var(--os-warn-ink,#F2C46D)}' +
      '.sp-root .sp-msg{margin-bottom:12px;font-size:12.5px;font-weight:600;border-radius:var(--os-r-sm,12px);padding:9px 12px;line-height:1.5}' +
      '.sp-root .sp-msg.ok{color:var(--os-good-ink,#2fbf5b);background:var(--os-surface-2,#1F2029);background:color-mix(in srgb,var(--os-good,#2fbf5b) 12%,transparent)}' +
      '.sp-root .sp-msg.warn{color:var(--os-warn-ink,#F2C46D);background:var(--os-surface-2,#1F2029);background:color-mix(in srgb,var(--os-warn,#F2C46D) 14%,transparent)}' +
      '.sp-root .sp-note{margin-top:14px;font-size:11.5px;color:var(--os-ink-2,#A6A8B5);line-height:1.55}' +
      '.sp-root .sp-empty{padding:30px;text-align:center;color:var(--os-ink-2,#A6A8B5);font-size:13px}' +
      '.sp-root .sp-spin{display:block;width:22px;height:22px;margin:0 auto 10px;border-radius:50%;border:2.5px solid var(--os-surface-3,#2A2B36);' +
        'border-top-color:var(--os-accent,#4C8DF6);animation:spSpin .7s linear infinite}' +
      '@keyframes spSpin{to{transform:rotate(360deg)}}' +
      '@media(prefers-reduced-motion:reduce){.sp-root .sp-spin{animation:none}.sp-root .sp-btn,.sp-root .sp-seg button{transition:none}}' +
      '@media(max-width:480px){.sp-root .sp-bar>.sp-seg{flex:1 1 100%;justify-content:space-between}.sp-root .sp-seg button{flex:1}' +
        '.sp-root .sp-rl{flex-wrap:wrap;gap:2px 8px}.sp-root .sp-val{white-space:normal;flex-basis:100%}}';
    document.head.appendChild(st);
  }

  window.KhipuSpend = { render: function (elId) { S.el = document.getElementById(elId); load(); } };
})();
