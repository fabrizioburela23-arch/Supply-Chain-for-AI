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
  var PROV = { claude: ['Claude (Anthropic)', '#D97757'], gemini: ['Gemini (Google)', '#4C8DF6'], nvidia: ['NVIDIA', '#76B900'] };

  var S = { el: null, days: 30, data: null, editing: false, msg: null };

  function bar(frac, col) {
    var w = Math.max(0, Math.min(100, Math.round((frac || 0) * 100)));
    return '<div style="height:7px;border-radius:4px;background:var(--surface-2,#1a2234);overflow:hidden;margin-top:4px"><i style="display:block;height:100%;width:' + w + '%;background:' + col + '"></i></div>';
  }
  function meter(label, spent, limit, hint) {
    var frac = limit ? spent / limit : 0, col = frac >= 1 ? '#FF4D6A' : frac >= 0.8 ? '#FFB300' : '#2BE38B';
    return '<div style="flex:1 1 140px;min-width:0;border:1px solid var(--line,#24304a);border-radius:10px;padding:10px 12px">' +
      '<div style="font-size:11px;color:var(--ink-3,#8791AC);text-transform:uppercase;letter-spacing:.06em">' + esc(label) + '</div>' +
      '<div style="font-size:20px;font-weight:800;margin-top:2px">' + usd(spent) + '</div>' +
      (limit ? '<div style="font-size:11px;color:var(--ink-3,#8791AC)">' + L('de ', 'of ') + usd(limit) + ' · ' + Math.round(frac * 100) + '%</div>' + bar(frac, col)
        : '<div style="font-size:11px;color:var(--ink-3,#8791AC)">' + esc(hint || L('sin límite', 'no limit')) + '</div>') + '</div>';
  }
  function table(title, rows, labelFn, total) {
    if (!rows || !rows.length) return '';
    var max = Math.max.apply(null, rows.map(function (r) { return r.cost_usd; }).concat([0.000001]));
    return '<div style="margin-top:16px"><div style="font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3,#8791AC);margin-bottom:6px">' + esc(title) + '</div>' +
      rows.slice(0, 12).map(function (r) {
        var lab = labelFn(r), col = lab[1] || '#00E0FF';
        return '<div style="padding:5px 0;border-bottom:1px solid var(--line,#1c2538)">' +
          '<div style="display:flex;justify-content:space-between;gap:8px;font-size:12.5px"><span style="overflow-wrap:anywhere">' + lab[0] + '</span>' +
          '<span style="white-space:nowrap"><b>' + usd(r.cost_usd) + '</b> <span style="color:var(--ink-3,#8791AC);font-size:11px">· ' + r.calls + L(' llamadas', ' calls') + ' · ' + tok(r.tokens_in) + '↓ ' + tok(r.tokens_out) + '↑</span></span></div>' +
          bar(r.cost_usd / max, col) + '</div>';
      }).join('') + '</div>';
  }
  function days(rows) {
    if (!rows || !rows.length) return '';
    var max = Math.max.apply(null, rows.map(function (r) { return r.cost_usd; }).concat([0.000001]));
    return '<div style="margin-top:16px"><div style="font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3,#8791AC);margin-bottom:6px">' + L('Gasto por día', 'Spend per day') + '</div>' +
      '<div style="display:flex;align-items:flex-end;gap:2px;height:70px">' + rows.map(function (r) {
        return '<div title="' + esc(r.key + ' · ' + usd(r.cost_usd) + ' · ' + r.calls) + '" style="flex:1;min-width:3px;background:#00E0FF;opacity:.8;border-radius:2px 2px 0 0;height:' + Math.max(2, Math.round(r.cost_usd / max * 70)) + 'px"></div>';
      }).join('') + '</div><div style="display:flex;justify-content:space-between;font-size:10px;color:var(--ink-3,#8791AC)"><span>' + esc(rows[0].key) + '</span><span>' + esc(rows[rows.length - 1].key) + '</span></div></div>';
  }
  function recent(rows) {
    if (!rows || !rows.length) return '';
    return '<details style="margin-top:16px"><summary style="cursor:pointer;font-size:12px;color:var(--ink-2,#c8d0e0)">' + L('Últimas llamadas', 'Latest calls') + ' (' + rows.length + ')</summary>' +
      rows.map(function (r) {
        var p = PROV[r.provider] || [r.provider, '#999'];
        var t = new Date(r.at);
        return '<div style="font-size:11.5px;padding:4px 0;border-bottom:1px solid var(--line,#1c2538);display:flex;gap:6px;flex-wrap:wrap">' +
          '<span style="color:var(--ink-3,#8791AC)">' + (isNaN(t) ? '' : t.toLocaleTimeString(isEn() ? 'en' : 'es', { hour: '2-digit', minute: '2-digit' })) + '</span>' +
          '<b style="color:' + p[1] + '">' + esc(p[0]) + '</b><span>' + esc(r.model) + '</span><span>· ' + esc(r.feature_label || r.feature) + '</span><span>· ' + esc(r.who) + '</span>' +
          '<span style="margin-left:auto">' + usd(r.cost_usd) + (r.estimated ? ' ≈' : '') + '</span></div>';
      }).join('') + '</details>';
  }
  function limitsForm(d) {
    var lm = d.limits || {}, pf = lm.per_feature_daily_usd || {};
    var feats = (d.by_feature || []).map(function (f) { return f; });
    var inp = function (id, v, ph) { return '<input id="' + id + '" type="number" min="0" step="0.5" value="' + esc(v == null ? '' : v) + '" placeholder="' + esc(ph || '') + '" style="width:90px;padding:5px 7px;border-radius:7px;border:1px solid var(--line,#24304a);background:var(--surface-2,#111827);color:var(--ink,#E8EDFB);font-size:12.5px">'; };
    var row = function (lab, html) { return '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;padding:5px 0;font-size:12.5px"><span>' + lab + '</span>' + html + '</div>'; };
    var provs = ['claude', 'gemini', 'nvidia'];
    return '<div style="margin-top:12px;border:1px solid var(--line,#24304a);border-radius:10px;padding:10px 12px">' +
      row(L('Límite diario total (USD)', 'Total daily limit (USD)'), inp('sp-daily', lm.daily_usd)) +
      row(L('Límite mensual total (USD)', 'Total monthly limit (USD)'), inp('sp-month', lm.monthly_usd)) +
      row(L('Límite diario por persona/cliente (0 = sin límite)', 'Daily limit per person/client (0 = none)'), inp('sp-who', lm.per_who_daily_usd)) +
      '<div style="font-size:11px;color:var(--ink-3,#8791AC);margin:8px 0 2px">' + L('Límite diario por función (vacío = sin límite):', 'Daily limit per feature (empty = none):') + '</div>' +
      feats.map(function (f) { return row(esc(f.label || f.key), inp('sp-f-' + f.key, pf[f.key], '—')); }).join('') +
      '<div style="font-size:11px;color:var(--ink-3,#8791AC);margin:8px 0 2px">' + L('Proveedores activos:', 'Active providers:') + '</div>' +
      provs.map(function (p) { return '<label style="display:inline-flex;gap:5px;align-items:center;margin-right:12px;font-size:12.5px"><input type="checkbox" id="sp-p-' + p + '"' + ((lm.blocked_providers || []).indexOf(p) < 0 ? ' checked' : '') + '> ' + esc(PROV[p][0]) + '</label>'; }).join('') +
      '<div style="display:flex;gap:8px;margin-top:10px"><button class="key-btn" id="sp-save">🔒 ' + L('Guardar límites (PIN)', 'Save limits (PIN)') + '</button>' +
      '<button class="key-btn" id="sp-cancel">' + L('Cancelar', 'Cancel') + '</button></div></div>';
  }

  function paint() {
    var el = S.el; if (!el) return;
    var d = S.data;
    if (!d) { el.innerHTML = '<div style="padding:30px;text-align:center;color:var(--ink-3);font-size:13px">' + L('Cargando gasto…', 'Loading spend…') + '</div>'; return; }
    if (d._err) { el.innerHTML = '<div style="padding:16px;color:#FFB300;font-size:13px">' + esc(d._err) + '</div>'; return; }
    var t = d.totals || {}, lm = d.limits || {}, ab = d.anthropic_billed || {};
    var provLabel = function (r) { var p = PROV[r.key] || [r.key, '#00E0FF']; return ['<b style="color:' + p[1] + '">' + esc(p[0]) + '</b>', p[1]]; };
    el.innerHTML =
      '<p class="settings-sub">' + L('Cuánto gastas en IA, en qué proveedor, en qué parte de la app y quién lo pidió. Al llegar a un límite, la app <b>deja de llamar a la IA</b> (no cobra) y lo avisa.',
        'How much you spend on AI, on which provider, in which part of the app and who asked. When a limit is reached the app <b>stops calling the AI</b> (no charge) and says so.') + '</p>' +
      (S.msg ? '<div style="margin-bottom:10px;font-size:12.5px;color:' + (S.msg.bad ? '#FFB300' : '#2BE38B') + '">' + esc(S.msg.text) + '</div>' : '') +
      '<div style="display:flex;gap:8px;flex-wrap:wrap">' + meter(L('Hoy', 'Today'), t.today, lm.daily_usd) + meter(L('Este mes', 'This month'), t.month, lm.monthly_usd) +
        meter(L('Últimos 7 días', 'Last 7 days'), t.week, 0, (t.calls_today || 0) + L(' llamadas hoy', ' calls today')) + '</div>' +
      '<div class="sp-billed" style="margin-top:10px;font-size:12px;border:1px dashed var(--line,#24304a);border-radius:9px;padding:8px 10px;line-height:1.5">' +
        (ab.available ? '🧾 <b>' + L('Facturado por Anthropic este mes: ', 'Billed by Anthropic this month: ') + usd(ab.month_usd) + '</b> <span style="color:var(--ink-3,#8791AC)">(' + L('dato real de su reporte de costos', 'real figure from their cost report') + ')</span>'
          : '🧾 ' + L('Saldo restante: ningún proveedor lo publica por API. Míralo en ', 'Remaining balance: no provider exposes it via API. Check it at ') +
            '<a href="https://console.anthropic.com/settings/billing" target="_blank" rel="noopener">console.anthropic.com → Billing</a>, ' +
            '<a href="https://aistudio.google.com/" target="_blank" rel="noopener">Google AI Studio</a> ' + L('y', 'and') + ' <a href="https://build.nvidia.com/" target="_blank" rel="noopener">build.nvidia.com</a>. ' +
            '<span style="color:var(--ink-3,#8791AC)">' + L('Para ver aquí lo facturado REAL por Anthropic, agrega en Railway la variable ANTHROPIC_ADMIN_KEY (llave Admin, solo cuentas de organización).', 'To see Anthropic\'s REAL billed amount here, add the ANTHROPIC_ADMIN_KEY variable on Railway (Admin key, organization accounts only).') + '</span>') + '</div>' +
      '<div style="display:flex;gap:8px;align-items:center;margin-top:10px;flex-wrap:wrap">' +
        [7, 30, 90].map(function (n) { return '<button class="key-btn" data-days="' + n + '" style="flex:0 0 auto' + (S.days === n ? ';border-color:#00E0FF;color:#00E0FF' : '') + '">' + n + L(' días', ' days') + '</button>'; }).join('') +
        '<button class="key-btn" id="sp-edit" style="flex:0 0 auto;margin-left:auto">⚙ ' + L('Límites', 'Limits') + '</button>' +
        '<button class="key-btn" id="sp-refresh" style="flex:0 0 auto">↻</button></div>' +
      (S.editing ? limitsForm(d) : '') +
      table(L('Por proveedor de IA', 'By AI provider'), d.by_provider, provLabel) +
      table(L('En qué parte de la app', 'In which part of the app'), d.by_feature, function (r) { return [esc(r.label || r.key), '#B48CFF']; }) +
      table(L('Quién lo pidió (persona / cliente)', 'Who asked (person / client)'), d.by_who, function (r) { return [esc(r.key), '#5FC6E8']; }) +
      table(L('Por modelo', 'By model'), d.by_model, function (r) { return [esc(r.key), '#FFB300']; }) +
      days(d.by_day) + recent(d.recent) +
      '<div style="margin-top:12px;font-size:11px;color:var(--ink-3,#8791AC);line-height:1.5">' + esc(isEn() ? d.note_en : d.note_es) +
        (d.source === 'memory' ? ' ' + L('Sin base de datos: el historial se pierde al reiniciar el servidor.', 'No database: history is lost when the server restarts.') : '') + '</div>';
    el.querySelectorAll('[data-days]').forEach(function (b) { b.onclick = function () { S.days = +b.getAttribute('data-days'); load(); }; });
    var r = document.getElementById('sp-refresh'); if (r) r.onclick = load;
    var e = document.getElementById('sp-edit'); if (e) e.onclick = function () { S.editing = !S.editing; S.msg = null; paint(); };
    var c = document.getElementById('sp-cancel'); if (c) c.onclick = function () { S.editing = false; paint(); };
    var sv = document.getElementById('sp-save'); if (sv) sv.onclick = save;
  }

  function num(id) { var x = document.getElementById(id); if (!x || x.value === '') return null; var v = parseFloat(x.value); return isNaN(v) ? null : v; }
  function save() {
    var d = S.data || {}, pf = {};
    (d.by_feature || []).forEach(function (f) { var v = num('sp-f-' + f.key); if (v != null && v > 0) pf[f.key] = v; });
    var blocked = ['claude', 'gemini', 'nvidia'].filter(function (p) { var x = document.getElementById('sp-p-' + p); return x && !x.checked; });
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
    }).then(function (j) { S.data = j; paint(); })
      .catch(function () { S.data = { _err: L('Sin conexión con el servidor.', 'No connection to the server.') }; paint(); });
  }

  (function () {
    if (document.getElementById('sp-styles')) return;
    var st = document.createElement('style'); st.id = 'sp-styles';
    st.textContent = '.sp-billed a{color:#5FC6E8;text-decoration:none;border-bottom:1px dotted #5FC6E8}.sp-billed a:hover{color:#00E0FF}';
    document.head.appendChild(st);
  })();

  window.KhipuSpend = { render: function (elId) { S.el = document.getElementById(elId); load(); } };
})();
