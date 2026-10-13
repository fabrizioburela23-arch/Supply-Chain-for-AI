/* engine/governance.js — 🩺 Sistema → Gobernanza (INFRA_OPERATIVA paso 12; pieza mínima del paso 25).
   Muestra el RELEASE vigente (reglas y números versionados), «Ratificar (PIN)» si el de arranque aún no lo está, y
   cada versión DISPONIBLE de un artefacto con «¿Qué cambia?» (contrafactual del servidor, sin tocar el motor vivo:
   GET /api/governance/preview) y «Activar (PIN)» (POST /api/governance/activate). Deshacer = activar la anterior.
   TODO por window._tradeFetch (PIN) y window.KhipuToast.confirm (nunca window.confirm). Textos ES/EN.
   Paso 25 (flujo completo, core/governance_flow.py): «¿Qué cambia para mí?» con TUS posiciones (eco_pos; sin ellas, las
   10 empresas más críticas), «Proponer cambio» (formulario de números con su mínimo y máximo: governance/tunables.json),
   «Regresión» (contrafactual sobre el libro real, en segundo plano), «Activar ahora» o «Programar» (effective_from;
   «Cancelar» antes de que empiece), «Deshacer» el último cambio y el historial (GET /api/governance/history).
   API: window.KhipuGovernance.mount(containerId)
*/
(function () {
  'use strict';
  var BASE = (typeof window.BASE !== 'undefined') ? window.BASE : '';
  function en() { var l = window.LANG; if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = 'es'; } } return l === 'en'; }
  function L(es, e) { return en() ? e : es; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function chip(k) { return window.explainChip ? window.explainChip(k) : ''; }

  var _box = null, _st = null, _busy = false, _msg = '', _prev = {};
  var _hist = null, _val = {}, _sched = {}, _form = { aid: null, vals: {}, problems: null }, _polls = {};
  var _open = {}, _pendingRender = false;

  function ensureStyles() {
    if (document.getElementById('kgv-styles')) return;
    var st = document.createElement('style'); st.id = 'kgv-styles';
    st.textContent =
      '.kgv-root{color:var(--os-ink,#F2F2F5);font-family:var(--os-font,\'Nunito\',system-ui,sans-serif)}' +
      '.kgv-root .kgv-card{border-radius:var(--os-r,18px);padding:14px 16px;margin:6px 0 12px;background:var(--os-surface,#17181F);' +
        'box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35));min-width:0}' +
      '.kgv-root .kgv-hd{display:flex;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap}' +
      '.kgv-root .kgv-hd b{font-size:14px;font-weight:800;flex:1;min-width:0}' +
      '.kgv-root .kgv-mut{font-size:12px;color:var(--os-ink-2,#A6A8B5);line-height:1.5;overflow-wrap:anywhere}' +
      '.kgv-root .kgv-row{padding:8px 0;border-top:1px solid var(--os-line,rgba(255,255,255,.07))}' +
      '.kgv-root .kgv-acts{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}' +
      '.kgv-root .kgv-btn{appearance:none;border:0;cursor:pointer;height:32px;padding:0 13px;border-radius:999px;font-size:12.5px;font-weight:700;' +
        'background:var(--os-surface-2,#1F2029);color:var(--os-ink,#F2F2F5)}' +
      '.kgv-root .kgv-btn.pri{background:var(--os-btn,#F2F2F5);color:var(--os-btn-ink,#111216)}' +
      '.kgv-root .kgv-btn[disabled]{opacity:.45;cursor:default}' +
      '.kgv-root .kgv-btn:focus-visible{outline:2px solid var(--os-accent,#4C8DF6);outline-offset:2px}' +
      '.kgv-root .kgv-tag{font-size:10.5px;font-weight:800;border-radius:999px;padding:1px 8px;background:var(--os-surface-2,#1F2029)}' +
      '.kgv-root .kgv-warn{color:var(--os-warn-ink,#F2C46D)}' +
      '.kgv-root table{width:100%;border-collapse:collapse;font-size:12px;margin-top:6px}' +
      '.kgv-root td,.kgv-root th{padding:3px 4px;text-align:left;border-bottom:1px solid var(--os-line,rgba(255,255,255,.07))}' +
      '.kgv-root td.n,.kgv-root th.n{text-align:right;font-variant-numeric:tabular-nums}' +
      '.kgv-root .kgv-prev{margin-top:8px;font-size:12.5px;line-height:1.55}' +
      '.kgv-root .kgv-sec{margin-top:12px;padding-top:10px;border-top:1px solid var(--os-line,rgba(255,255,255,.07))}' +
      '.kgv-root .kgv-sec > summary{cursor:pointer;font-size:13px;font-weight:800;list-style:revert}' +
      '.kgv-root .kgv-h{font-size:13px;font-weight:800;margin:0 0 4px}' +
      '.kgv-root .kgv-field{display:grid;grid-template-columns:minmax(0,1fr) 112px;gap:6px 10px;align-items:center;padding:5px 0}' +
      '.kgv-root .kgv-field label{font-size:12.5px;min-width:0;overflow-wrap:anywhere}' +
      '.kgv-root input,.kgv-root select,.kgv-root textarea{box-sizing:border-box;max-width:100%;font:inherit;font-size:12.5px;' +
        'color:var(--os-ink,#F2F2F5);background:var(--os-surface-2,#1F2029);border:1px solid var(--os-line,rgba(255,255,255,.12));border-radius:10px;padding:5px 8px}' +
      '.kgv-root input[type=number]{width:112px}' +
      '.kgv-root textarea{width:100%;min-height:40px;resize:vertical}' +
      '.kgv-root .kgv-list{margin:6px 0 0;padding-left:18px;font-size:12.5px;line-height:1.55}' +
      '.kgv-root .kgv-ok{color:var(--os-ok-ink,#7BD88F)}';
    document.head.appendChild(st);
  }

  function errMsg(d, status) {
    d = d || {};
    return (en() ? (d.error_en || d.error) : (d.error || d.error_en)) || ('HTTP ' + status);
  }

  async function load() {
    try {
      var r = await fetch(BASE + '/api/governance/status', { headers: { Accept: 'application/json' } });
      var d = await r.json().catch(function () { return null; });
      if (!r.ok || !d) throw new Error(errMsg(d, r.status));
      _st = d;
    } catch (e) {
      _st = null;
      _msg = '❌ ' + esc(String(e && e.message || e));
    }
    try {
      var rh = await fetch(BASE + '/api/governance/history', { headers: { Accept: 'application/json' } });
      var dh = await rh.json().catch(function () { return null; });
      _hist = (rh.ok && dh) ? dh : null;
    } catch (e) { _hist = null; }
    render();
    loadValidations();
  }

  function previewHTML(p) {
    if (!p) return '';
    if (p.loading) return '<div class="kgv-prev kgv-mut">⏳ ' + esc(L('Calculando qué cambia (todas las simulaciones de caída)…', 'Computing what changes (every collapse simulation)…')) + '</div>';
    if (p.error) return '<div class="kgv-prev kgv-warn">❌ ' + esc(p.error) + '</div>';
    var d = p.data, k = d.kernel, h = '<div class="kgv-prev">' + forMeHTML(d.for_me) + esc(en() ? d.summary_en : d.summary_es);
    if (k) {
      h += '<table><tr><th>' + esc(L('Si cae…', 'If it fails…')) + '</th><th class="n">' + esc(L('afectadas hoy', 'hit today')) +
        '</th><th class="n">' + esc(L('con la nueva', 'with new')) + '</th><th class="n">' + esc(L('golpe total', 'total hit')) + chip('choke_sum') + '</th></tr>';
      (k.reference || []).forEach(function (x) {
        h += '<tr><td>' + esc(x.label) + '</td><td class="n">' + esc(x.reach_before) + '</td><td class="n">' + esc(x.reach_after) +
          '</td><td class="n">' + esc(x.sum_before) + ' → ' + esc(x.sum_after) + '</td></tr>';
      });
      h += '</table><div class="kgv-mut" style="margin-top:6px">' +
        esc(L('Cuellos de botella (nuevo orden): ', 'Chokepoints (new order): ')) +
        esc((k.chokepoints_after || []).slice(0, 6).map(function (x) { return x.label; }).join(' · ')) + '</div>';
    }
    return h + '</div>';
  }

  function typing() {
    var a = document.activeElement;
    return !!(a && _box && _box.contains(a) && /^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName));
  }

  function render() {
    if (!_box) return;
    if (typing()) { _pendingRender = true; return; }   // no borrar lo que la persona está escribiendo
    _pendingRender = false;
    ensureStyles();
    var s = _st;
    var h = '<div class="kgv-root kos-themed"><div class="kgv-card">';
    h += '<div class="kgv-hd"><span aria-hidden="true">⚖</span><b>' + esc(L('Gobernanza: reglas y motor versionados', 'Governance: versioned rules and engine')) + chip('gov_release') + '</b></div>';
    if (!s) {
      h += '<div class="kgv-mut">' + (_msg || esc(L('Cargando…', 'Loading…'))) + '</div></div></div>';
      _box.innerHTML = h;
      return;
    }
    var db = s.source === 'db';
    var kp = (s.artifacts || {})['kernel.params'] || {};
    h += '<div class="kgv-mut">' + esc(en() ? (s.explain || {}).en : (s.explain || {}).es) + '</div>';
    h += '<div class="kgv-mut">' + esc(L('Motor de contagio vigente: ', 'Contagion engine in force: ')) + '<b>kernel.params ' + esc(kp.semver || '?') + '</b>' +
      (kp.semver === '2.0.0' ? chip('kernel_v2') : '') + ' · release <code>' + esc(String(s.release_hash || '').slice(0, 8)) + '</code></div>';
    if (s.needs_ratification) {
      h += '<div class="kgv-acts"><button class="kgv-btn pri" data-act="ratify"' + (_busy ? ' disabled' : '') + '>' +
        esc(L('Ratificar (PIN)', 'Ratify (PIN)')) + '</button></div>';
    }
    var props = (s.proposals || []).filter(function (p) { return p.id === 'kernel.params' || p.newer; });
    if (props.length) {
      props.forEach(function (p) {
        var key = p.id + '@' + p.semver;
        var back = !p.newer;
        h += '<div class="kgv-row"><div class="kgv-hd"><b>' + esc(p.id) + ' ' + esc(p.semver) + '</b>' +
          '<span class="kgv-tag">' + esc(back ? L('versión anterior', 'previous version') : (p.change_kind === 'major' ? L('cambio mayor', 'major change') : p.change_kind)) + '</span>' +
          (p.id === 'kernel.params' && p.semver === '2.0.0' ? chip('kernel_v2') : '') + '</div>' +
          '<div class="kgv-mut">' + esc(en() ? (p.summary_en || p.changelog_en) : (p.summary_es || p.changelog_es)) + '</div>' +
          '<div class="kgv-acts"><button class="kgv-btn" data-act="preview" data-k="' + esc(key) + '"' + (_busy ? ' disabled' : '') + '>' +
          esc(L('¿Qué cambia para mí?', 'What changes for me?')) + '</button>' +
          (db ? '<button class="kgv-btn" data-act="validate" data-k="' + esc(key) + '"' + (_busy ? ' disabled' : '') + '>' +
            esc(L('Regresión (PIN)', 'Regression (PIN)')) + '</button>' : '') +
          (db ? '<button class="kgv-btn pri" data-act="activate" data-k="' + esc(key) + '"' + (_busy ? ' disabled' : '') + '>' +
            esc(back ? L('Volver a esta versión (PIN)', 'Go back to this version (PIN)') : L('Activar (PIN)', 'Activate (PIN)')) + '</button>' : '') +
          (db && !back ? '<button class="kgv-btn" data-act="sched" data-k="' + esc(key) + '"' + (_busy ? ' disabled' : '') + '>' +
            esc(L('Programar…', 'Schedule…')) + '</button>' : '') +
          '</div>' + schedHTML(key) + validationHTML(key) + previewHTML(_prev[key]) + '</div>';
      });
      if (!db) h += '<div class="kgv-mut kgv-warn">' + esc(L('Sin base de datos no se puede activar nada: rige la propuesta del repositorio.', 'Without a database nothing can be activated: the repository proposal rules.')) + '</div>';
    }
    h += flowHTML(db);
    if (_msg) h += '<div class="kgv-mut" style="margin-top:8px">' + _msg + '</div>';
    h += '</div></div>';
    _box.innerHTML = h;
    Array.prototype.forEach.call(_box.querySelectorAll('button[data-act]'), function (b) {
      b.addEventListener('click', function () {
        var act = b.getAttribute('data-act'), k = b.getAttribute('data-k');
        if (act === 'ratify') ratify();
        else if (act === 'preview') preview(k);
        else if (act === 'activate') activate(k);
        else if (act === 'validate') validate(k);
        else if (act === 'sched') { _sched[k] = !_sched[k]; render(); }
        else if (act === 'sched-go') schedule(k);
        else if (act === 'cancel') cancelSched(k);
        else if (act === 'undo') undo();
        else if (act === 'propose') propose();
      });
    });
    Array.prototype.forEach.call(_box.querySelectorAll('details[data-gov-sec]'), function (d) {
      d.addEventListener('toggle', function () { _open[d.getAttribute('data-gov-sec')] = d.open; });
    });
    if (!_box.__kgvBlur) {
      _box.__kgvBlur = true;
      _box.addEventListener('focusout', function () { setTimeout(function () { if (_pendingRender && !typing()) render(); }, 0); });
    }
    var sel = _box.querySelector('select[data-gov-aid]');
    if (sel) sel.addEventListener('change', function () { _form.aid = sel.value; _form.vals = {}; _form.problems = null; sel.blur(); render(); });
    Array.prototype.forEach.call(_box.querySelectorAll('input[data-gov-path]'), function (inp) {
      inp.addEventListener('input', function () { _form.vals[inp.getAttribute('data-gov-path')] = inp.value; });
    });
    Array.prototype.forEach.call(_box.querySelectorAll('input[data-gov-when]'), function (inp) {
      inp.addEventListener('input', function () { _sched['when:' + inp.getAttribute('data-gov-when')] = inp.value; });
    });
    Array.prototype.forEach.call(_box.querySelectorAll('textarea[data-gov-note]'), function (ta) {
      ta.addEventListener('input', function () { _form[ta.getAttribute('data-gov-note')] = ta.value; });
    });
  }

  function split(k) { var i = k.lastIndexOf('@'); return { artifact: k.slice(0, i), semver: k.slice(i + 1) }; }

  async function preview(k) {
    var a = split(k);
    _prev[k] = { loading: true }; render();
    try {
      var ids = myIds();
      var r = await fetch(BASE + '/api/governance/preview?artifact=' + encodeURIComponent(a.artifact) + '&semver=' + encodeURIComponent(a.semver) +
        (ids.length ? '&ids=' + encodeURIComponent(ids.join(',')) : ''), { headers: { Accept: 'application/json' } });
      var d = await r.json().catch(function () { return null; });
      if (!r.ok || !d) throw new Error(errMsg(d, r.status));
      _prev[k] = { data: d };
    } catch (e) { _prev[k] = { error: String(e && e.message || e) }; }
    render();
    return _prev[k];
  }

  async function post(url, body) {
    var f = window._tradeFetch || fetch;
    var r = await f(BASE + url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}), timeout: 60000 }, true);
    var d = await r.json().catch(function () { return {}; });
    return { ok: r.ok, status: r.status, d: d };
  }

  async function ratify() {
    if (_busy) return;
    var ok = window.KhipuToast && window.KhipuToast.confirm ? await window.KhipuToast.confirm({
      title: L('¿Ratificar el release vigente?', 'Ratify the release in force?'),
      note: L('Confirmas que las reglas y números vigentes son los aprobados. No cambia ningún número; queda registrado con tu PIN.',
              'You confirm that the rules and numbers in force are the approved ones. No number changes; it is recorded with your PIN.'),
      confirmLabel: L('Ratificar', 'Ratify'),
    }) : false;
    if (!ok) return;
    _busy = true; _msg = '⏳ ' + esc(L('Ratificando…', 'Ratifying…')); render();
    var res = await post('/api/governance/ratify', {});
    _busy = false;
    _msg = res.ok ? '✅ ' + esc(L('Ratificado.', 'Ratified.')) : '❌ ' + esc(errMsg(res.d, res.status));
    await load();
  }

  async function activate(k, when) {
    if (_busy) return;
    var a = split(k);
    var p = (_prev[k] && _prev[k].data) ? _prev[k] : await preview(k);
    var d = p && p.data;
    // el aviso de "cambio mayor" SOLO para una versión NUEVA y mayor (no al volver a una anterior ni en una menor)
    var prop = ((_st && _st.proposals) || []).filter(function (x) { return x.id === a.artifact && x.semver === a.semver; })[0] || {};
    var major = !!prop.newer && (prop.four_eyes === 'unavailable' || prop.change_kind === 'major');
    var ok = window.KhipuToast && window.KhipuToast.confirm ? await window.KhipuToast.confirm({
      title: L('¿Activar ', 'Activate ') + a.artifact + ' ' + a.semver + '?',
      subtitle: d ? (en() ? d.summary_en : d.summary_es) : '',
      note: when ? L('Entra en vigor el ' + fmtWhen(when) + ' para toda la app (puedes cancelarlo antes). Queda registrado con tu PIN.',
                     'It takes effect on ' + fmtWhen(when) + ' for the whole app (you can cancel it before). It is recorded with your PIN.') :
            a.artifact === 'policy.broker_risk' ? L('Los límites del corretaje cambian después del cierre de Nueva York (puedes cancelarlo antes). Queda registrado con tu PIN.',
                     'Brokerage limits change after the New York close (you can cancel it before). It is recorded with your PIN.') :
            L('Entra en vigor YA para toda la app y queda registrado con tu PIN. Para deshacer, vuelve a activar la versión anterior.',
              'It takes effect NOW for the whole app and is recorded with your PIN. To undo, activate the previous version again.'),
      warnHtml: major ? esc(L('Cambio mayor: por ahora solo tú lo apruebas (una segunda persona llegará más adelante).',
                              'Major change: for now only you approve it (a second person will come later).')) : '',
      confirmLabel: L('Activar', 'Activate'),
    }) : false;   // sin engine/toast.js no hay confirmación posible → no se activa
    if (!ok) return;
    _busy = true; _msg = '⏳ ' + esc(L('Activando…', 'Activating…')); render();
    var body = { artifact: a.artifact, semver: a.semver };
    if (when) body.effective_from = when; else if (a.artifact !== 'policy.broker_risk') body.effective_from = 'now';
    var res = await post('/api/governance/activate', body);
    _busy = false;
    if (res.ok && res.d.scheduled) {
      _msg = '🗓 ' + esc(L('Programado para ', 'Scheduled for ')) + esc(fmtWhen(res.d.effective_from)) + ' · ' + esc(a.artifact + ' ' + a.semver);
      _sched[k] = false;
    } else if (res.ok) {
      _msg = '✅ ' + esc(L('Activado: ', 'Activated: ')) + esc(a.artifact + ' ' + a.semver) + ' · release <code>' + esc(String(res.d.release_hash || '').slice(0, 8)) + '</code>';
      _prev = {};
      try { if (window.KhipuHot && window.KhipuHot.flush) window.KhipuHot.flush(); } catch (e) { /* las vistas se renuevan solas */ }
      if (window.KhipuToast && window.KhipuToast.show) window.KhipuToast.show({ kind: 'ok', title: L('Versión activada', 'Version activated'), body: a.artifact + ' ' + a.semver });
    } else if (res.status === 409 && res.d && res.d.code === 'regression_required') {
      // un cambio MAYOR nuevo necesita su regresión antes: la lanzamos y avisamos (sin error en rojo)
      _msg = '⏳ ' + esc(L('Primero calculo qué cambiaría (regresión). Cuando termine, pulsa «Activar» otra vez.',
                           'First I compute what would change (regression). When it finishes, press «Activate» again.'));
      await load();
      validate(k);
      return;
    } else {
      _msg = '❌ ' + esc(errMsg(res.d, res.status));
    }
    await load();
  }

  // ── paso 25: flujo completo ─────────────────────────────────────────────────────────────────────────────────
  function myIds() {
    try {
      var pos = JSON.parse(localStorage.getItem('eco_pos') || '{}') || {};
      return Object.keys(pos).filter(function (k) { return pos[k]; }).slice(0, 25);
    } catch (e) { return []; }
  }

  function fmtWhen(iso) {
    try { return new Date(iso).toLocaleString(en() ? 'en-US' : 'es-PE', { dateStyle: 'medium', timeStyle: 'short' }); } catch (e) { return String(iso || ''); }
  }

  function forMeHTML(fm) {
    if (!fm) return '';
    var lines = (en() ? fm.lines_en : fm.lines_es) || [];
    if (!lines.length) return '';
    var who = fm.basis === 'positions' ? L('Para tus posiciones:', 'For your positions:') :
      fm.basis === 'top10' ? L('Para las 10 empresas más críticas (no tienes posiciones guardadas):', 'For the 10 most critical companies (you have no saved positions):') :
      L('Los números que cambian:', 'The numbers that change:');
    return '<div class="kgv-h">' + esc(L('¿Qué cambia para mí?', 'What changes for me?')) + chip('gov_for_me') + '</div>' +
      '<div class="kgv-mut">' + esc(who) + '</div><ul class="kgv-list">' +
      lines.slice(0, 8).map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>';
  }

  function validationHTML(k) {
    var v = _val[k];
    if (!v) return '';
    if (v.loading || v.state === 'running') return '<div class="kgv-prev kgv-mut">⏳ ' + esc(L('Regresión en curso: recalculando decisiones reales, simulaciones y NRS con esta versión…', 'Regression running: recomputing real decisions, simulations and NRS with this version…')) + '</div>';
    if (v.error || v.state === 'error') return '<div class="kgv-prev kgv-warn">❌ ' + esc(v.error || '') + '</div>';
    var rep = v.report || {};
    var h = '<div class="kgv-prev"><div class="kgv-h">' + esc(L('Regresión contrafactual', 'Counterfactual regression')) + chip('gov_regression') + '</div>' +
      '<div class="kgv-mut">' + esc(en() ? (v.summary_en || '') : (v.summary_es || '')) + '</div>';
    var led = rep.ledger || {}, rows = [];
    if (rep.shocks) rows.push([L('Simulaciones de caída', 'Collapse simulations'), rep.shocks.shocks_changed, rep.shocks.shocks]);
    if (led.whatif) rows.push([L('Qué-pasaría-si reales (30 días)', 'Real what-ifs (30 days)'), led.whatif.changed, led.whatif.replayed]);
    if (led.committee) rows.push([L('Memos del comité', 'Committee memos'), led.committee.changed, led.committee.replayed]);
    if (led.orders) rows.push([L('Órdenes (controles de monto)', 'Orders (amount checks)'), led.orders.changed, led.orders.replayed]);
    if (rep.nrs) rows.push(['NRS', rep.nrs.changed, rep.nrs.companies]);
    if (rep.shapes) rows.push([L('Reglas nuevas en sombra', 'New rules in shadow'), rep.shapes.with_diff, rep.shapes.evaluations]);
    if (rows.length) {
      h += '<table><tr><th>' + esc(L('Qué se recalculó', 'What was recomputed')) + '</th><th class="n">' + esc(L('cambian', 'change')) + '</th><th class="n">' + esc(L('de', 'of')) + '</th></tr>' +
        rows.map(function (r) { return '<tr><td>' + esc(r[0]) + '</td><td class="n">' + esc(r[1]) + '</td><td class="n">' + esc(r[2]) + '</td></tr>'; }).join('') + '</table>';
    }
    if (rep.semver_warning) h += '<div class="kgv-mut kgv-warn">' + esc(en() ? rep.semver_warning.en : rep.semver_warning.es) + '</div>';
    h += forMeHTML(rep.for_me);
    return h + '</div>';
  }

  function schedHTML(k) {
    if (!_sched[k]) return '';
    var v = _sched['when:' + k] || '';
    return '<div class="kgv-prev"><div class="kgv-h">' + esc(L('Programar la activación', 'Schedule the activation')) + chip('gov_schedule') + '</div>' +
      '<div class="kgv-acts"><input type="datetime-local" data-gov-when="' + esc(k) + '" value="' + esc(v) + '" aria-label="' + esc(L('Fecha y hora', 'Date and time')) + '">' +
      '<button class="kgv-btn pri" data-act="sched-go" data-k="' + esc(k) + '"' + (_busy ? ' disabled' : '') + '>' + esc(L('Programar (PIN)', 'Schedule (PIN)')) + '</button></div>' +
      '<div class="kgv-mut">' + esc(L('Hora de tu equipo. Hasta que llegue, nada cambia y puedes cancelarlo.', 'Your device time. Until then nothing changes and you can cancel it.')) + '</div></div>';
  }

  var KIND_ES = { 'governance.propose': 'Propuesta', 'governance.validate': 'Regresión', 'governance.activate': 'Activación', 'governance.ratify': 'Ratificación' };
  var KIND_EN = { 'governance.propose': 'Proposal', 'governance.validate': 'Regression', 'governance.activate': 'Activation', 'governance.ratify': 'Ratification' };

  function histLine(d) {
    var sub = d.subject || {}, what = KIND_ES[d.kind] ? (en() ? KIND_EN[d.kind] : KIND_ES[d.kind]) : d.kind;
    if (d.kind === 'governance.activate') {
      if (sub.cancels) what = L('Programación cancelada', 'Schedule cancelled');
      else if (sub.applies) what = L('Aplicada por el reloj', 'Applied by the clock');
      else if (sub.scheduled) what = L('Activación programada', 'Scheduled activation');
      else if (sub.bootstrap) what = L('Arranque (valores de hoy)', 'Bootstrap (today\'s values)');
      else if (sub.reactivation) what = L('Vuelta a una versión anterior', 'Back to a previous version');
    }
    var ch = sub.changes ? (Array.isArray(sub.changes) ? sub.changes.map(function (c) { return c.path + ' ' + c.from + '→' + c.to; }).join(', ') :
      Object.keys(sub.changes).map(function (a) { return a + ' ' + sub.changes[a].from + '→' + sub.changes[a].to; }).join(', ')) : '';
    var art = sub.artifact ? sub.artifact + (sub.semver ? ' ' + sub.semver : '') : '';
    return '<li><b>' + esc(what) + '</b> · ' + esc(fmtWhen(d.recorded_at)) + ' · ' + esc(d.principal_id || '') +
      (art ? ' · ' + esc(art) : '') + (ch ? ' · ' + esc(ch) : '') + (sub.four_eyes === 'unavailable' ? ' · ' + esc(L('un solo aprobador', 'single approver')) : '') + '</li>';
  }

  function formHTML() {
    var pr = (_hist && _hist.proposable) || {};
    var ids = Object.keys(pr).filter(function (a) { return pr[a] && pr[a].fields && pr[a].fields.length; });
    if (!ids.length) return '';
    if (!_form.aid || ids.indexOf(_form.aid) < 0) _form.aid = ids[0];
    var f = pr[_form.aid];
    var NAMES = { 'kernel.params': L('Motor de contagio', 'Contagion engine'), 'policy.committee': L('Comité de inversión', 'Investment committee'),
      'policy.broker_risk': L('Límites del corretaje', 'Brokerage limits'), 'policy.decide': L('Decisiones de Jev', 'Jev decisions'),
      'policy.auto_apply': L('Aplicación automática de agentes', 'Agent auto-apply') };
    var h = '<details class="kgv-sec"' + (_open.form ? ' open' : '') + ' data-gov-sec="form"><summary>' + esc(L('Proponer cambio', 'Propose a change')) + '</summary>' +
      '<div class="kgv-mut" style="margin:6px 0">' + esc(L('Cambia uno o más números. No entra en vigor: queda como propuesta, Khipus corre la regresión y tú decides si activarla.',
        'Change one or more numbers. It does not take effect: it stays as a proposal, Khipus runs the regression and you decide whether to activate it.')) + chip('gov_propose') + '</div>' +
      '<div class="kgv-acts"><select data-gov-aid aria-label="' + esc(L('Qué reglas', 'Which rules')) + '">' +
      ids.map(function (a) { return '<option value="' + esc(a) + '"' + (a === _form.aid ? ' selected' : '') + '>' + esc((NAMES[a] || a) + ' · ' + a + ' ' + pr[a].semver) + '</option>'; }).join('') +
      '</select></div>';
    f.fields.forEach(function (x) {
      var v = _form.vals[x.path] != null ? _form.vals[x.path] : x.value;
      h += '<div class="kgv-field"><label for="kgv-f-' + esc(x.path) + '" title="' + esc(en() ? x.help_en : x.help_es) + '">' + esc(en() ? x.label_en : x.label_es) +
        ' <span class="kgv-mut">(' + esc(L('hoy', 'today')) + ' ' + esc(x.value) + ' · ' + esc(x.min) + '–' + esc(x.max) + ')</span></label>' +
        '<input type="number" id="kgv-f-' + esc(x.path) + '" data-gov-path="' + esc(x.path) + '" value="' + esc(v) + '" min="' + esc(x.min) + '" max="' + esc(x.max) + '" step="' + esc(x.step || 'any') + '"></div>';
    });
    h += '<textarea data-gov-note="note" placeholder="' + esc(L('Por qué (opcional)', 'Why (optional)')) + '">' + esc(_form.note || '') + '</textarea>';
    if (_form.problems) h += '<ul class="kgv-list kgv-warn">' + _form.problems.map(function (p) { return '<li>' + esc(en() ? p.en : p.es) + '</li>'; }).join('') + '</ul>';
    h += '<div class="kgv-acts"><button class="kgv-btn pri" data-act="propose"' + (_busy || !(_hist && _hist.db) ? ' disabled' : '') + '>' + esc(L('Proponer (PIN)', 'Propose (PIN)')) + '</button></div>';
    if (_hist && !_hist.db) h += '<div class="kgv-mut kgv-warn">' + esc(L('Sin base de datos no se puede proponer.', 'Without a database nothing can be proposed.')) + '</div>';
    return h + '</details>';
  }

  function flowHTML(db) {
    var h = '';
    var sc = (_hist && _hist.scheduled) || [];
    if (sc.length) {
      h += '<div class="kgv-sec"><div class="kgv-h">🗓 ' + esc(L('Cambios programados', 'Scheduled changes')) + chip('gov_schedule') + '</div>';
      sc.forEach(function (p) {
        var ch = Object.keys(p.changes || {}).map(function (a) { return a + ' ' + p.changes[a].from + ' → ' + p.changes[a].to; }).join(', ');
        h += '<div class="kgv-row"><div class="kgv-mut">' + esc(L('Entra en vigor: ', 'Takes effect: ')) + '<b>' + esc(fmtWhen(p.effective_from)) + '</b> · ' + esc(ch) + '</div>' +
          '<div class="kgv-acts"><button class="kgv-btn" data-act="cancel" data-k="' + esc(p.decision_id) + '"' + (_busy ? ' disabled' : '') + '>' + esc(L('Cancelar (PIN)', 'Cancel (PIN)')) + '</button></div></div>';
      });
      h += '</div>';
    }
    if (_hist && _hist.undo) {
      var u = _hist.undo;
      var uch = Object.keys(u.changes || {}).map(function (a) { return a + ' ' + u.changes[a].to + ' → ' + u.changes[a].from; }).join(', ');
      h += '<div class="kgv-sec"><div class="kgv-mut">' + esc(L('Último cambio activado. Deshacerlo vuelve al release anterior: ', 'Last activated change. Undoing it goes back to the previous release: ')) + esc(uch) + '</div>' +
        '<div class="kgv-acts"><button class="kgv-btn" data-act="undo"' + (_busy ? ' disabled' : '') + '>' + esc(L('Deshacer (PIN)', 'Undo (PIN)')) + '</button></div></div>';
    }
    h += formHTML();
    var ds = (_hist && _hist.decisions) || [];
    if (ds.length) {
      h += '<details class="kgv-sec"' + (_open.hist ? ' open' : '') + ' data-gov-sec="hist"><summary>' + esc(L('Historial (nunca se borra)', 'History (never deleted)')) + '</summary><ul class="kgv-list">' +
        ds.slice(0, 12).map(histLine).join('') + '</ul></details>';
    }
    return h;
  }

  async function loadValidations() {
    var props = ((_st && _st.proposals) || []).filter(function (p) { return p.origin === 'app' && p.newer; });
    for (var i = 0; i < props.length; i++) {
      var k = props[i].id + '@' + props[i].semver;
      if (_val[k]) continue;
      try {
        var r = await fetch(BASE + '/api/governance/validation?artifact=' + encodeURIComponent(props[i].id) + '&semver=' + encodeURIComponent(props[i].semver), { headers: { Accept: 'application/json' } });
        var d = await r.json().catch(function () { return null; });
        if (r.ok && d && d.validation) { _val[k] = d.validation; if (d.validation.state === 'running') pollValidation(k); }
      } catch (e) { /* sin regresión todavía */ }
    }
    render();
  }

  function pollValidation(k) {
    if (_polls[k]) return;
    var a = split(k), n = 0;
    _polls[k] = setInterval(async function () {
      n++;
      try {
        var r = await fetch(BASE + '/api/governance/validation?artifact=' + encodeURIComponent(a.artifact) + '&semver=' + encodeURIComponent(a.semver), { headers: { Accept: 'application/json' } });
        var d = await r.json().catch(function () { return null; });
        if (r.ok && d && d.validation) _val[k] = d.validation;
      } catch (e) { /* reintenta */ }
      if ((_val[k] && _val[k].state !== 'running') || n > 80) { clearInterval(_polls[k]); delete _polls[k]; }
      render();
    }, 1500);
  }

  async function validate(k) {
    if (_busy) return;
    var a = split(k);
    _val[k] = { loading: true }; render();
    var res = await post('/api/governance/validate', { artifact: a.artifact, semver: a.semver, ids: myIds() });
    if (!res.ok) { _val[k] = { error: errMsg(res.d, res.status) }; render(); return; }
    _val[k] = res.d.job || { state: 'running' };
    pollValidation(k);
    render();
  }

  async function schedule(k) {
    var raw = _sched['when:' + k];
    var t = raw ? new Date(raw) : null;
    if (!t || isNaN(t.getTime()) || t.getTime() <= Date.now()) {
      _msg = '❌ ' + esc(L('Elige una fecha y hora futuras.', 'Pick a future date and time.')); render(); return;
    }
    await activate(k, t.toISOString());
  }

  async function cancelSched(id) {
    if (_busy) return;
    var ok = window.KhipuToast && window.KhipuToast.confirm ? await window.KhipuToast.confirm({
      title: L('¿Cancelar el cambio programado?', 'Cancel the scheduled change?'),
      note: L('No entrará en vigor. Queda registrado con tu PIN (nada se borra).', 'It will not take effect. It is recorded with your PIN (nothing is deleted).'),
      confirmLabel: L('Cancelar el cambio', 'Cancel the change'), cancelLabel: L('Volver', 'Back'),
    }) : false;
    if (!ok) return;
    _busy = true; render();
    var res = await post('/api/governance/cancel', { decision_id: id });
    _busy = false;
    _msg = res.ok ? '✅ ' + esc(L('Cambio programado cancelado.', 'Scheduled change cancelled.')) : '❌ ' + esc(errMsg(res.d, res.status));
    await load();
  }

  async function undo() {
    if (_busy || !_hist || !_hist.undo) return;
    var u = _hist.undo;
    var ok = window.KhipuToast && window.KhipuToast.confirm ? await window.KhipuToast.confirm({
      title: L('¿Deshacer el último cambio?', 'Undo the last change?'),
      subtitle: L('Vuelve al release ', 'Goes back to release ') + (u.to_semver || '') + ' (' + String(u.to_release || '').slice(0, 8) + ')',
      note: L('Entra en vigor YA y queda registrado con tu PIN. Nada se borra: puedes volver a activarlo.', 'It takes effect NOW and is recorded with your PIN. Nothing is deleted: you can activate it again.'),
      confirmLabel: L('Deshacer', 'Undo'),
    }) : false;
    if (!ok) return;
    _busy = true; render();
    var res = await post('/api/governance/activate', { release_hash: u.to_release, effective_from: 'now' });
    _busy = false;
    _msg = res.ok ? '✅ ' + esc(L('Cambio deshecho.', 'Change undone.')) : '❌ ' + esc(errMsg(res.d, res.status));
    if (res.ok) { _prev = {}; try { if (window.KhipuHot && window.KhipuHot.flush) window.KhipuHot.flush(); } catch (e) { /* solas */ } }
    await load();
  }

  async function propose() {
    if (_busy || !_hist) return;
    var f = (_hist.proposable || {})[_form.aid];
    if (!f) return;
    var changes = {};
    f.fields.forEach(function (x) {
      var v = _form.vals[x.path];
      if (v == null || v === '') return;
      var n = Number(String(v).replace(',', '.'));
      if (!isNaN(n) && n !== Number(x.value)) changes[x.path] = n;
    });
    if (!Object.keys(changes).length) { _form.problems = [{ es: 'No cambiaste ningún número.', en: 'You did not change any number.' }]; render(); return; }
    var ok = window.KhipuToast && window.KhipuToast.confirm ? await window.KhipuToast.confirm({
      title: L('¿Proponer este cambio?', 'Propose this change?'),
      subtitle: Object.keys(changes).map(function (p) { return p + ' → ' + changes[p]; }).join(' · '),
      note: L('NO entra en vigor: queda como propuesta con tu PIN y Khipus calcula qué cambiaría. Activarla es otro paso.',
              'It does NOT take effect: it stays as a proposal with your PIN and Khipus computes what would change. Activating it is another step.'),
      confirmLabel: L('Proponer', 'Propose'),
    }) : false;
    if (!ok) return;
    _busy = true; _form.problems = null; _open.form = true; render();
    var res = await post('/api/governance/propose', { artifact: _form.aid, changes: changes, note: _form.note || '', ids: myIds() });
    _busy = false;
    if (res.ok) {
      var k = res.d.artifact + '@' + res.d.semver;
      _msg = '✅ ' + esc(L('Propuesta registrada: ', 'Proposal recorded: ')) + esc(res.d.artifact + ' ' + res.d.semver) + ' · ' + esc(L('regresión en curso…', 'regression running…'));
      _form.vals = {}; _form.note = '';
      _val[k] = res.d.validation || { state: 'running' };
      pollValidation(k);
    } else if (res.d && res.d.problems) {
      _form.problems = res.d.problems;
    } else {
      _msg = '❌ ' + esc(errMsg(res.d, res.status));
    }
    await load();
  }

  window.KhipuGovernance = {
    mount: function (id) {
      _box = document.getElementById(id);
      if (!_box) return;
      _msg = '';
      render();
      if (!_busy) load();
    },
    reload: function () { return load(); },
  };
})();
