/* engine/governance.js — 🩺 Sistema → Gobernanza (INFRA_OPERATIVA paso 12; pieza mínima del paso 25).
   Muestra el RELEASE vigente (reglas y números versionados), «Ratificar (PIN)» si el de arranque aún no lo está, y
   cada versión DISPONIBLE de un artefacto con «¿Qué cambia?» (contrafactual del servidor, sin tocar el motor vivo:
   GET /api/governance/preview) y «Activar (PIN)» (POST /api/governance/activate). Deshacer = activar la anterior.
   TODO por window._tradeFetch (PIN) y window.KhipuToast.confirm (nunca window.confirm). Textos ES/EN.
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
      '.kgv-root .kgv-prev{margin-top:8px;font-size:12.5px;line-height:1.55}';
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
    render();
  }

  function previewHTML(p) {
    if (!p) return '';
    if (p.loading) return '<div class="kgv-prev kgv-mut">⏳ ' + esc(L('Calculando qué cambia (todas las simulaciones de caída)…', 'Computing what changes (every collapse simulation)…')) + '</div>';
    if (p.error) return '<div class="kgv-prev kgv-warn">❌ ' + esc(p.error) + '</div>';
    var d = p.data, k = d.kernel, h = '<div class="kgv-prev">' + esc(en() ? d.summary_en : d.summary_es);
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

  function render() {
    if (!_box) return;
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
          esc(L('¿Qué cambia?', 'What changes?')) + '</button>' +
          (db ? '<button class="kgv-btn pri" data-act="activate" data-k="' + esc(key) + '"' + (_busy ? ' disabled' : '') + '>' +
            esc(back ? L('Volver a esta versión (PIN)', 'Go back to this version (PIN)') : L('Activar (PIN)', 'Activate (PIN)')) + '</button>' : '') +
          '</div>' + previewHTML(_prev[key]) + '</div>';
      });
      if (!db) h += '<div class="kgv-mut kgv-warn">' + esc(L('Sin base de datos no se puede activar nada: rige la propuesta del repositorio.', 'Without a database nothing can be activated: the repository proposal rules.')) + '</div>';
    }
    if (_msg) h += '<div class="kgv-mut" style="margin-top:8px">' + _msg + '</div>';
    h += '</div></div>';
    _box.innerHTML = h;
    Array.prototype.forEach.call(_box.querySelectorAll('button[data-act]'), function (b) {
      b.addEventListener('click', function () {
        var act = b.getAttribute('data-act'), k = b.getAttribute('data-k');
        if (act === 'ratify') ratify();
        else if (act === 'preview') preview(k);
        else if (act === 'activate') activate(k);
      });
    });
  }

  function split(k) { var i = k.lastIndexOf('@'); return { artifact: k.slice(0, i), semver: k.slice(i + 1) }; }

  async function preview(k) {
    var a = split(k);
    _prev[k] = { loading: true }; render();
    try {
      var r = await fetch(BASE + '/api/governance/preview?artifact=' + encodeURIComponent(a.artifact) + '&semver=' + encodeURIComponent(a.semver),
        { headers: { Accept: 'application/json' } });
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

  async function activate(k) {
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
      note: L('Entra en vigor YA para toda la app y queda registrado con tu PIN. Para deshacer, vuelve a activar la versión anterior.',
              'It takes effect NOW for the whole app and is recorded with your PIN. To undo, activate the previous version again.'),
      warnHtml: major ? esc(L('Cambio mayor: por ahora solo tú lo apruebas (una segunda persona llegará más adelante).',
                              'Major change: for now only you approve it (a second person will come later).')) : '',
      confirmLabel: L('Activar', 'Activate'),
    }) : false;   // sin engine/toast.js no hay confirmación posible → no se activa
    if (!ok) return;
    _busy = true; _msg = '⏳ ' + esc(L('Activando…', 'Activating…')); render();
    var res = await post('/api/governance/activate', { artifact: a.artifact, semver: a.semver });
    _busy = false;
    if (res.ok) {
      _msg = '✅ ' + esc(L('Activado: ', 'Activated: ')) + esc(a.artifact + ' ' + a.semver) + ' · release <code>' + esc(String(res.d.release_hash || '').slice(0, 8)) + '</code>';
      _prev = {};
      try { if (window.KhipuHot && window.KhipuHot.flush) window.KhipuHot.flush(); } catch (e) { /* las vistas se renuevan solas */ }
      if (window.KhipuToast && window.KhipuToast.show) window.KhipuToast.show({ kind: 'ok', title: L('Versión activada', 'Version activated'), body: a.artifact + ' ' + a.semver });
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
