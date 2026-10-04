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

  function card(inner) {
    return '<div style="border:1px solid var(--line);border-left:3px solid #00a3ff;border-radius:8px;padding:12px 14px;' +
      'margin:4px 0 10px;background:var(--surface-2,rgba(255,255,255,.02))">' + inner + '</div>';
  }

  function head() {
    return '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px"><span style="font-size:14px">🧹</span>' +
      '<b style="font-size:13.5px;flex:1">' + L('Grafo: base vs catálogo', 'Graph: database vs catalog') + '</b>' +
      (window.explainChip ? window.explainChip('reconcile') : '') + '</div>';
  }

  function render(msg) {
    if (!_box) return;
    if (!_plan) {
      _box.innerHTML = card(head() + '<div style="font-size:12px;color:var(--ink-3);padding-left:22px">' + (msg || L('Cargando…', 'Loading…')) + '</div>');
      return;
    }
    var s = _plan.summary || {}, total = 0;
    var rows = CATS.map(function (c) {
      var n = s[c[0]] || 0; total += n;
      return '<label style="display:flex;align-items:center;gap:8px;padding:3px 0;font-size:12.5px' + (n ? '' : ';opacity:.55') + '">' +
        '<input type="checkbox" data-cat="' + c[0] + '"' + (c[3] && n ? ' checked' : '') + (n ? '' : ' disabled') + '>' +
        '<span style="flex:1">' + esc(en() ? c[2] : c[1]) + (c[3] ? '' : ' <span style="color:#e6a23c;font-size:10.5px">' +
        L('· revisar antes', '· check first') + '</span>') + '</span><b style="font-family:\'JetBrains Mono\',monospace">' + n + '</b></label>';
    }).join('');
    var runs = (_plan.runs || []).filter(function (r) { return !r.rollback; });
    var undone = {}; (_plan.runs || []).forEach(function (r) { if (r.rollback) undone[r.run_id] = 1; });
    var last = runs.filter(function (r) { return !undone[r.run_id]; })[0];
    var lang = en() ? 'en' : 'es';
    _box.innerHTML = card(head() +
      '<div style="font-size:11.5px;color:var(--ink-3);padding-left:22px;margin-bottom:6px">' +
      (total ? L('Diferencias encontradas: ', 'Differences found: ') + '<b>' + total + '</b> · ' : L('Sin diferencias. ✅ ', 'No differences. ✅ ')) +
      L('base', 'database') + ' <code>' + esc(_plan.db || '?') + '</code> · ' + esc((_plan.as_of || '').slice(0, 16).replace('T', ' ')) + ' UTC</div>' +
      '<div style="padding-left:22px">' + rows + '</div>' +
      '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;padding-left:22px">' +
      '<a class="key-btn" style="text-decoration:none" target="_blank" rel="noopener" href="' + BASE + '/api/ontology/reconcile/plan?format=html&lang=' + lang + '">📄 ' + L('Ver lista completa', 'See full list') + '</a>' +
      '<button class="key-btn" data-act="apply"' + (total ? '' : ' disabled') + '>✓ ' + L('Aplicar lo marcado', 'Apply ticked') + '</button>' +
      '<button class="key-btn" data-act="refresh">↻</button>' +
      (last ? '<button class="key-btn" data-act="undo" data-run="' + esc(last.run_id) + '">↶ ' + L('Deshacer ', 'Undo ') + esc(last.run_id) + '</button>' : '') +
      '</div>' + (msg ? '<div style="font-size:12px;margin-top:8px;padding-left:22px">' + msg + '</div>' : ''));
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
