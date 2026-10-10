/* engine/reconcile.js — G3 (misión de reparación 2026-10-04)
   🩺 Diagnóstico → "Grafo: base vs catálogo".
   Muestra el dry-run de ontology/reconcile.py (GET /api/ontology/reconcile/plan),
   abre la lista completa (HTML) y, con el PIN de operador, aplica las categorías
   marcadas o deshace la última corrida. TODO por eventos: nada se borra.
   API: window.KhipuReconcile.mount(containerId)
*/
(function () {
  'use strict';
  var BASE = (typeof window.BASE !== 'undefined') ? window.BASE : '';
  function en() { return (window.LANG || localStorage.getItem('eco_lang') || 'es') === 'en'; }
  function L(es, e) { return en() ? e : es; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

  var CATS = [
    ['alias', 'Empresas duplicadas', 'Duplicate companies', true],
    ['duplicates', 'Vínculos repetidos', 'Repeated links', true],
    ['direction', 'Direcciones al revés', 'Reversed directions', false],
    ['variants', 'Mismo vínculo, otro peso', 'Same link, other weight', false],
    ['missing', 'Faltan en la base', 'Missing in the database', false],
    ['extra', 'Sobran en la base', 'Extra in the database', false],
  ];

  if (window.explainRegister) {
    window.explainRegister('reconcile', {
      es: { t: '¿Qué es "Grafo: base vs catálogo"?',
        b: 'Khipus guarda el mapa de proveedores en dos sitios: el <b>catálogo</b> (lo que ves en el mapa y lo que leen las IAs ' +
           'conectadas) y la <b>base de datos</b> (lo que usan el simulador de shocks, el riesgo NRS del servidor y el Grafo ' +
           'Temporal). En julio se limpió el catálogo (empresas repetidas, vínculos dobles, flechas al revés) pero la base ' +
           'conservó la versión vieja. Esta revisión compara ambos y propone arreglos.<br><br>' +
           '<b>Nada se borra</b>: cada arreglo es un registro nuevo con tu nombre, y cada aplicación se puede <b>deshacer</b>. ' +
           'Lo "seguro" (duplicados) se puede aplicar ya; las <b>direcciones</b> y lo demás conviene revisarlos en la lista ' +
           'completa antes de marcarlos.' },
      en: { t: 'What is "Graph: database vs catalog"?',
        b: 'Khipus keeps the supplier map in two places: the <b>catalog</b> (what you see on the map and what connected AIs ' +
           'read) and the <b>database</b> (what the shock simulator, the server NRS risk and the Temporal Graph use). In July ' +
           'the catalog was cleaned (repeated companies, double links, reversed arrows) but the database kept the old ' +
           'version. This review compares both and proposes fixes.<br><br>' +
           '<b>Nothing is deleted</b>: every fix is a new record with your name, and every run can be <b>undone</b>. The ' +
           '"safe" part (duplicates) can be applied now; <b>directions</b> and the rest are best checked in the full list ' +
           'before ticking them.' } });
  }

  var _plan = null, _box = null, _busy = false;

  // ── Khipus OS (2026-10-10): la caja vive en 🩺 Sistema (fuera de #bcp-ov) y lleva .kos-themed → tokens --os-*
  // de engine/cockpit.js (claro = body sin .dark, oscuro = body.dark). Solo tokens; el valor tras la coma es el
  // respaldo oscuro. Tarjeta sin bordes, botones píldora, aviso «revisar antes» con texto AA (--os-warn-ink).
  function ensureStyles() {
    if (document.getElementById('krc-styles')) return;
    var st = document.createElement('style'); st.id = 'krc-styles';
    st.textContent =
      '.krc-root{color:var(--os-ink,#F2F2F5);font-family:var(--os-font,\'Nunito\',\'Geist\',system-ui,-apple-system,\'Segoe UI\',sans-serif);' +
        '-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale}' +
      '.krc-root *{box-sizing:border-box}.krc-root button{font-family:inherit}' +
      '.krc-root .krc-card{border-radius:var(--os-r,18px);padding:14px 16px;margin:6px 0 12px;background:var(--os-surface,#17181F);' +
        'box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35));min-width:0}' +
      '.krc-root .krc-hd{display:flex;align-items:center;gap:8px;margin-bottom:4px}' +
      '.krc-root .krc-hd b{font-size:14px;font-weight:800;letter-spacing:-.005em;flex:1;min-width:0}' +
      '.krc-root .krc-ic{width:28px;height:28px;flex:none;border-radius:9px;display:inline-flex;align-items:center;justify-content:center;font-size:14px;' +
        'background:var(--os-surface-2,#1F2029);background:color-mix(in srgb,var(--os-accent,#4C8DF6) 13%,transparent)}' +
      '.krc-root .krc-in{padding-left:36px}' +
      '.krc-root .krc-mut{font-size:12px;color:var(--os-ink-2,#A6A8B5);line-height:1.5;margin-bottom:6px;overflow-wrap:anywhere}' +
      '.krc-root code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:11.5px;padding:1px 6px;border-radius:6px;background:var(--os-surface-2,#1F2029);color:var(--os-ink,#F2F2F5)}' +
      '.krc-root .krc-row{display:flex;align-items:center;gap:8px;padding:5px 0;font-size:12.5px;cursor:pointer;border-bottom:1px solid var(--os-line,rgba(255,255,255,.07))}' +
      '.krc-root .krc-row:last-child{border-bottom:0}' +
      '.krc-root .krc-row.off{color:var(--os-ink-2,#A6A8B5);cursor:default}' +
      '.krc-root .krc-row input{width:16px;height:16px;margin:0;accent-color:var(--os-accent,#4C8DF6);flex:none}' +
      '.krc-root .krc-row .krc-n{font-variant-numeric:tabular-nums;font-weight:800;min-width:28px;text-align:right}' +
      '.krc-root .krc-chk{display:inline-flex;align-items:center;font-size:10.5px;font-weight:700;border-radius:999px;padding:1px 8px;margin-left:4px;white-space:nowrap;' +
        'color:var(--os-warn-ink,#F2C46D);background:var(--os-surface-2,#1F2029);background:color-mix(in srgb,var(--os-warn,#F2C46D) 16%,transparent)}' +
      '.krc-root .krc-acts{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}' +
      '.krc-root .krc-btn{appearance:none;-webkit-appearance:none;border:0;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:6px;height:34px;' +
        'padding:0 14px;border-radius:999px;background:var(--os-surface-2,#1F2029);color:var(--os-ink,#F2F2F5);font-size:12.5px;font-weight:700;white-space:nowrap;' +
        'text-decoration:none;transition:opacity .15s,background-color .15s,transform .1s}' +
      '.krc-root .krc-btn:hover:not([disabled]){background:var(--os-surface-3,#2A2B36)}.krc-root .krc-btn:active{transform:scale(.98)}' +
      '.krc-root .krc-btn.pri{background:var(--os-btn,#F2F2F5);color:var(--os-btn-ink,#111216)}.krc-root .krc-btn.pri:hover:not([disabled]){opacity:.88;background:var(--os-btn,#F2F2F5)}' +
      '.krc-root .krc-btn[disabled]{opacity:.45;cursor:default;transform:none}' +
      '.krc-root .krc-btn.krc-icon{width:34px;padding:0;font-size:14px}' +
      '.krc-root .krc-btn:focus-visible,.krc-root input:focus-visible{outline:2px solid var(--os-accent,#4C8DF6);outline-offset:2px}' +
      '.krc-root .krc-msg{font-size:12.5px;margin-top:10px;line-height:1.5;overflow-wrap:anywhere}' +
      // el «?» de explain.js trae cian fijo: aquí toma el acento del tema (legible en claro)
      '.krc-root span[onclick*="explainMetric"]{color:var(--os-accent,#4C8DF6)!important;border-color:color-mix(in srgb,var(--os-accent,#4C8DF6) 45%,transparent)!important}' +
      '@media(prefers-reduced-motion:reduce){.krc-root .krc-btn{transition:none}}' +
      '@media(max-width:480px){.krc-root .krc-in{padding-left:0}}';
    document.head.appendChild(st);
  }

  function card(inner) {
    return '<div class="krc-card">' + inner + '</div>';
  }

  function head() {
    return '<div class="krc-hd"><span class="krc-ic" aria-hidden="true">🧹</span>' +
      '<b>' + L('Grafo: base vs catálogo', 'Graph: database vs catalog') + '</b>' +
      (window.explainChip ? window.explainChip('reconcile') : '') + '</div>';
  }

  function render(msg) {
    if (!_box) return;
    ensureStyles();
    // tokens --os-* de Khipus OS (claro/oscuro) aunque 🩺 Sistema viva fuera de #bcp-ov
    if (_box.classList) { _box.classList.add('kos-themed'); _box.classList.add('krc-root'); }
    if (!_plan) {
      _box.innerHTML = card(head() + '<div class="krc-mut krc-in">' + (msg || L('Cargando…', 'Loading…')) + '</div>');
      return;
    }
    var s = _plan.summary || {}, total = 0;
    var rows = CATS.map(function (c) {
      var n = s[c[0]] || 0; total += n;
      return '<label class="krc-row' + (n ? '' : ' off') + '">' +
        '<input type="checkbox" data-cat="' + c[0] + '"' + (c[3] && n ? ' checked' : '') + (n ? '' : ' disabled') + '>' +
        '<span style="flex:1;min-width:0">' + esc(en() ? c[2] : c[1]) + (c[3] ? '' : ' <span class="krc-chk">' +
        L('revisar antes', 'check first') + '</span>') + '</span><span class="krc-n">' + n + '</span></label>';
    }).join('');
    var runs = (_plan.runs || []).filter(function (r) { return !r.rollback; });
    var undone = {}; (_plan.runs || []).forEach(function (r) { if (r.rollback) undone[r.run_id] = 1; });
    var last = runs.filter(function (r) { return !undone[r.run_id]; })[0];
    var lang = en() ? 'en' : 'es';
    _box.innerHTML = card(head() +
      '<div class="krc-mut krc-in">' +
      (total ? L('Diferencias encontradas: ', 'Differences found: ') + '<b>' + total + '</b> · ' : L('Sin diferencias. ✅ ', 'No differences. ✅ ')) +
      L('base', 'database') + ' <code>' + esc(_plan.db || '?') + '</code> · ' + esc((_plan.as_of || '').slice(0, 16).replace('T', ' ')) + ' UTC</div>' +
      '<div class="krc-in">' + rows + '</div>' +
      '<div class="krc-acts krc-in">' +
      '<a class="krc-btn" target="_blank" rel="noopener" href="' + BASE + '/api/ontology/reconcile/plan?format=html&lang=' + lang + '">📄 ' + L('Ver lista completa', 'See full list') + '</a>' +
      '<button type="button" class="krc-btn pri" data-act="apply"' + (total ? '' : ' disabled') + '>✓ ' + L('Aplicar lo marcado', 'Apply ticked') + '</button>' +
      '<button type="button" class="krc-btn krc-icon" data-act="refresh" title="' + esc(L('Recalcular', 'Recompute')) + '" aria-label="' + esc(L('Recalcular', 'Recompute')) + '">↻</button>' +
      (last ? '<button type="button" class="krc-btn" data-act="undo" data-run="' + esc(last.run_id) + '">↶ ' + L('Deshacer ', 'Undo ') + esc(last.run_id) + '</button>' : '') +
      '</div>' + (msg ? '<div class="krc-msg krc-in" role="status">' + msg + '</div>' : ''));
    _box.querySelectorAll('[data-act]').forEach(function (b) {
      b.onclick = function () {
        var a = b.getAttribute('data-act');
        if (a === 'refresh') load(true);
        else if (a === 'apply') apply();
        else if (a === 'undo') undo(b.getAttribute('data-run'));
      };
    });
  }

  async function load(fresh) {
    _plan = null; render();
    try {
      var r = await fetch(BASE + '/api/ontology/reconcile/plan?summary=1' + (fresh ? '&fresh=1' : ''));
      var d = await r.json().catch(function () { return {}; });
      if (r.status === 503 && d.code === 'no_snapshot') { render(L('Falta el catálogo (data/grafo_v0.json) en el servidor.', 'The catalog (data/grafo_v0.json) is missing on the server.')); return; }
      if (r.status === 503 && d.code === 'busy') { render(L('El plan se está calculando; reintenta en unos segundos.', 'The plan is being computed; retry in a few seconds.')); return; }
      if (r.status === 503) { render(L('Sin base de datos (DATABASE_URL): nada que comparar.', 'No database (DATABASE_URL): nothing to compare.')); return; }
      if (!r.ok) { render(esc(errMsg(d, r.status))); return; }
      _plan = d; render();
    } catch (e) { render(esc(String(e && e.message || e))); }
  }

  function errMsg(d, status) {
    d = d || {};
    return (en() ? (d.error_en || d.error) : (d.error_es || d.error || d.error_en)) || ('HTTP ' + status);
  }

  // G5: antes de aplicar, se vuelve a pedir el plan (con PIN, recalculado) y se
  // compara con lo que la persona está viendo; el servidor además exige `expect`.
  async function freshCounts() {
    var f = window._tradeFetch || fetch;
    var r = await f(BASE + '/api/ontology/reconcile/plan?summary=1&fresh=1', {}, true);
    var d = await r.json().catch(function () { return {}; });
    if (!r.ok) throw new Error(errMsg(d, r.status));
    return d;
  }

  function actor() {
    try {
      var a = localStorage.getItem('khipu_actor');
      if (!a) { a = (window.prompt(L('¿Cómo te identificamos?', 'Who are you?')) || '').trim(); if (a) localStorage.setItem('khipu_actor', a); }
      return a || '';
    } catch (e) { return ''; }
  }

  async function post(url, body) {
    var f = window._tradeFetch || fetch;
    var r = await f(BASE + url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), timeout: 120000 }, true);
    var d = await r.json().catch(function () { return {}; });
    return { ok: r.ok, status: r.status, d: d };
  }

  async function apply() {
    if (_busy || !_plan) return;
    var cats = Array.prototype.map.call(_box.querySelectorAll('input[data-cat]:checked'), function (i) { return i.getAttribute('data-cat'); });
    if (!cats.length) { render(L('Marca al menos una categoría.', 'Tick at least one category.')); return; }
    var latest;
    try { latest = await freshCounts(); } catch (e) { render('❌ ' + esc(String(e && e.message || e))); return; }
    var changed = cats.filter(function (c) { return ((latest.summary || {})[c] || 0) !== ((_plan.summary || {})[c] || 0); });
    if (changed.length) {
      _plan = latest; render('⚠ ' + L('La lista cambió desde que la miraste. Revísala de nuevo antes de aplicar.',
                                       'The list changed since you looked at it. Review it again before applying.'));
      return;
    }
    var names = CATS.filter(function (c) { return cats.indexOf(c[0]) >= 0; })
      .map(function (c) { return (en() ? c[2] : c[1]) + ' (' + ((_plan.summary || {})[c[0]] || 0) + ')'; }).join(' · ');
    var risky = cats.some(function (c) { return ['direction', 'variants', 'missing', 'extra'].indexOf(c) >= 0; });
    var ok = window.KhipuToast && window.KhipuToast.confirm ? await window.KhipuToast.confirm({
      title: L('¿Aplicar estas correcciones al grafo?', 'Apply these fixes to the graph?'),
      subtitle: names,
      note: L('Se registran como eventos nuevos con tu nombre. Nada se borra y se puede deshacer.',
              'They are recorded as new events under your name. Nothing is deleted and it can be undone.'),
      warnHtml: risky ? esc(L('Incluye categorías para revisar: confirma que viste la lista completa.',
                              'Includes categories to check: confirm you saw the full list.')) : '',
      requireCheck: L('Hice una copia de seguridad de la base (Railway → Postgres → Backups).',
                      'I made a database backup (Railway → Postgres → Backups).'),
      confirmLabel: L('Aplicar', 'Apply'),
    }) : window.confirm(names);
    if (!ok) return;
    var who = actor(); if (!who) return;
    _busy = true; render('⏳ ' + L('Aplicando…', 'Applying…'));
    try {
      var expect = {}; cats.forEach(function (c) { expect[c] = (_plan.summary || {})[c] || 0; });
      var res = await post('/api/ontology/reconcile/apply', { actor: who, confirm_db: _plan.db, include: cats, expect: expect });
      _busy = false;
      if (!res.ok) {
        await load(true);
        var extra = res.d && res.d.run_id ? ' · ' + L('código para deshacer: ', 'undo code: ') + '<code>' + esc(res.d.run_id) + '</code>' : '';
        render('❌ ' + esc(errMsg(res.d, res.status)) + extra); return;
      }
      await load(true);
      render('✅ ' + L('Aplicado. Código para deshacer: ', 'Applied. Undo code: ') + '<code>' + esc(res.d.run_id) + '</code>');
    } catch (e) { _busy = false; await load(true); render('❌ ' + esc(String(e && e.message || e))); }
  }

  async function undo(runId) {
    if (_busy || !_plan || !runId) return;
    var ok = window.KhipuToast && window.KhipuToast.confirm ? await window.KhipuToast.confirm({
      title: L('¿Deshacer la corrida ', 'Undo run ') + runId + '?',
      note: L('Se revierte con eventos nuevos; la historia queda.', 'It is reverted with new events; the history stays.'),
      confirmLabel: L('Deshacer', 'Undo'),
    }) : window.confirm(runId);
    if (!ok) return;
    var who = actor(); if (!who) return;
    _busy = true; render('⏳ ' + L('Deshaciendo…', 'Undoing…'));
    try {
      var res = await post('/api/ontology/reconcile/rollback', { actor: who, confirm_db: _plan.db, run_id: runId });
      _busy = false;
      await load(true);
      render(res.ok ? '✅ ' + L('Deshecho.', 'Undone.') : '❌ ' + esc(errMsg(res.d, res.status)));
    } catch (e) { _busy = false; await load(true); render('❌ ' + esc(String(e && e.message || e))); }
  }

  window.KhipuReconcile = {
    mount: function (id) {
      _box = document.getElementById(id);
      if (!_box) return;
      if (!_busy) load(false);      // G5: siempre el plan actual (antes se reusaba uno viejo en memoria)
    },
    reload: function () { return load(true); },
  };
})();
