/* engine/audit.js — 🩺 Sistema → 📋 Registro → ⚖ Auditoría (INFRA_OPERATIVA paso 24, §5.6).
   Lista las decisiones recientes del LIBRO (filtros: tipo, quién, fecha) y por cada una:
     «¿Por qué?»  → GET /api/ledger/why/<id>: entradas, versiones de las reglas, evidencia, puertas y resultado, en
                    lenguaje simple ES/EN (los textos los arma el servidor: core/replay.why);
     «Repetir»    → POST /api/ledger/replay/<id>: la repite con lo que el sistema sabía ENTONCES y muestra el veredicto
                    (idéntica / distinta / no repetible y por qué). Sin PIN: el resumen (sin valores de clientes); con
                    el PIN guardado (o «Ver detalle con PIN»): campo a campo.
   Sin diálogos nativos del navegador (el PIN lo pide window._tradeFetch con su diálogo oculto de KhipuToast). Textos ES/EN.
   API: window.KhipuAudit.mount(containerId)
*/
(function () {
  'use strict';
  var BASE = (typeof window.BASE !== 'undefined') ? window.BASE : '';
  function en() { var l = window.LANG; if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = 'es'; } } return l === 'en'; }
  function L(es, e) { return en() ? e : es; }
  function T(o) { return o ? (en() ? (o.en || o.es) : (o.es || o.en)) : ''; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function chip(k) { return window.explainChip ? window.explainChip(k) : ''; }

  var WHO = { human: ['Personas', 'People'], agent: ['Agentes de IA', 'AI agents'], system: ['Tareas del sistema', 'System tasks'],
              external_ai: ['IA externas (MCP)', 'External AIs (MCP)'] };
  var VERD = { identical: ['✓ Idéntica', '✓ Identical', 'ok'], differs: ['≠ Distinta', '≠ Different', 'bad'],
               not_replayable: ['— No repetible', '— Not replayable', 'mut'] };

  var _box = null, _st = { items: [], kinds: [], sample: null, redacted: true, err: '', loading: false, limit: 20 };
  var _f = { kind: '', who: '', day: '' }, _open = {}, _busy = {};

  function ensureStyles() {
    if (document.getElementById('kau-styles')) return;
    var st = document.createElement('style'); st.id = 'kau-styles';
    st.textContent =
      '.kau-root{color:var(--os-ink,#F2F2F5);font-family:var(--os-font,\'Nunito\',system-ui,sans-serif);min-width:0}' +
      '.kau-root .kau-card{border-radius:var(--os-r,18px);padding:14px 16px;margin:6px 0 12px;background:var(--os-surface,#17181F);' +
        'box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35));min-width:0;box-sizing:border-box}' +
      '.kau-root .kau-hd{display:flex;align-items:center;gap:6px;margin-bottom:4px;flex-wrap:wrap}' +
      '.kau-root .kau-hd b{font-size:14px;font-weight:800}' +
      '.kau-root .kau-mut{font-size:12px;color:var(--os-ink-2,#A6A8B5);line-height:1.5;overflow-wrap:anywhere}' +
      '.kau-root .kau-filters{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0 4px}' +
      '.kau-root select,.kau-root input{box-sizing:border-box;max-width:100%;font:inherit;font-size:12.5px;min-width:0;' +
        'color:var(--os-ink,#F2F2F5);background:var(--os-surface-2,#1F2029);border:1px solid var(--os-line,rgba(255,255,255,.12));border-radius:10px;padding:5px 8px;height:32px}' +
      '.kau-root select{flex:1 1 150px}.kau-root input[type=date]{flex:1 1 130px}' +
      '.kau-root .kau-btn{appearance:none;border:0;cursor:pointer;height:30px;padding:0 12px;border-radius:999px;font-size:12px;font-weight:700;' +
        'background:var(--os-surface-2,#1F2029);color:var(--os-ink,#F2F2F5);white-space:nowrap}' +
      '.kau-root .kau-btn.pri{background:var(--os-btn,#F2F2F5);color:var(--os-btn-ink,#111216)}' +
      '.kau-root .kau-btn[disabled]{opacity:.45;cursor:default}' +
      '.kau-root .kau-btn:focus-visible,.kau-root select:focus-visible,.kau-root input:focus-visible{outline:2px solid var(--os-accent,#4C8DF6);outline-offset:2px}' +
      '.kau-root .kau-row{padding:9px 0;border-top:1px solid var(--os-line,rgba(255,255,255,.07));min-width:0}' +
      '.kau-root .kau-rh{display:flex;gap:6px;align-items:baseline;flex-wrap:wrap;min-width:0}' +
      '.kau-root .kau-k{font-size:13px;font-weight:800;overflow-wrap:anywhere;min-width:0}' +
      '.kau-root .kau-tag{font-size:10.5px;font-weight:800;border-radius:999px;padding:1px 8px;background:var(--os-surface-2,#1F2029)}' +
      '.kau-root .kau-tag.ok{color:var(--os-ok-ink,#7BD88F)}.kau-root .kau-tag.bad{color:var(--os-bad-ink,#FF8A8A)}' +
      '.kau-root .kau-tag.warn{color:var(--os-warn-ink,#F2C46D)}.kau-root .kau-tag.mut{color:var(--os-ink-2,#A6A8B5)}' +
      '.kau-root .kau-acts{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}' +
      '.kau-root .kau-out{margin-top:8px;padding:10px 12px;border-radius:12px;background:var(--os-surface-2,#1F2029);font-size:12.5px;line-height:1.55;overflow-wrap:anywhere}' +
      '.kau-root .kau-out ul{margin:6px 0 0;padding-left:18px}.kau-root .kau-out li{margin:2px 0}' +
      '.kau-root .kau-ok{color:var(--os-ok-ink,#7BD88F)}.kau-root .kau-bad{color:var(--os-bad-ink,#FF8A8A)}' +
      '.kau-root code{font-size:11.5px;overflow-wrap:anywhere}' +
      '.kau-root .kau-empty{font-size:12.5px;color:var(--os-ink-2,#A6A8B5);padding:10px 0}';
    document.head.appendChild(st);
  }

  function pinHeaders() {
    var h = { Accept: 'application/json' };
    try { var p = window._tradePinStored && window._tradePinStored(); if (p) h['X-Trade-Pin'] = p; } catch (e) {}
    return h;
  }
  async function getJSON(url, opts, withPinPrompt) {
    var r;
    if (withPinPrompt && window._tradeFetch) r = await window._tradeFetch(url, opts || {}, true);
    else r = await fetch(url, Object.assign({ headers: pinHeaders() }, opts || {}));
    var d = await r.json().catch(function () { return null; });
    if (!r.ok || !d) {
      var m = d && (en() ? (d.error_en || d.error) : (d.error || d.error_en));
      throw new Error(m || ('HTTP ' + r.status));
    }
    return d;
  }

  function qs() {
    var p = ['limit=' + _st.limit];
    if (_f.kind) p.push('kind=' + encodeURIComponent(_f.kind));
    if (_f.who) p.push('principal_kind=' + encodeURIComponent(_f.who));
    if (_f.day) {
      var d0 = new Date(_f.day + 'T00:00:00Z');
      if (!isNaN(d0)) {
        var d1 = new Date(d0.getTime() + 86400000);
        p.push('since=' + encodeURIComponent(d0.toISOString()), 'until=' + encodeURIComponent(d1.toISOString()));
      }
    }
    return p.join('&');
  }

  async function load() {
    _st.loading = true; _st.err = ''; render();
    try {
      var d = await getJSON(BASE + '/api/ledger/audit?' + qs());
      _st.items = d.decisions || []; _st.kinds = d.kinds || _st.kinds; _st.sample = d.sample || null;
      _st.redacted = !!d.redacted;
    } catch (e) {
      _st.items = []; _st.err = String(e && e.message || e);
    }
    _st.loading = false; render();
  }

  function fmtWhen(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    if (isNaN(d)) return esc(iso);
    try { return d.toLocaleString(en() ? 'en-US' : 'es-PE', { dateStyle: 'medium', timeStyle: 'short' }); } catch (e) { return d.toISOString(); }
  }

  function sampleLine() {
    var s = _st.sample && _st.sample.last;
    if (!s) return L('Muestra nocturna: todavía no corrió (cada noche se repiten al azar 50 decisiones y todas las de dinero).',
                     'Nightly sample: it has not run yet (every night 50 random decisions and all money ones are replayed).');
    var c = s.counts || {};
    var bad = +(c.differs || 0) > 0;
    return '<span class="' + (bad ? 'kau-bad' : '') + '">' + esc(L('Muestra nocturna', 'Nightly sample')) + ' (' + fmtWhen(s.at) + '): ' +
      esc(s.sampled || 0) + ' ' + esc(L('repetidas', 'replayed')) + ' — ' + esc(c.identical || 0) + ' ' + esc(L('idénticas', 'identical')) +
      ', ' + esc(c.differs || 0) + ' ' + esc(L('distintas', 'different')) + ', ' + esc(c.not_replayable || 0) + ' ' +
      esc(L('no repetibles', 'not replayable')) + '</span>';
  }

  // decisiones que la muestra nocturna marcó DISTINTAS: arriba, con su «Repetir» (el 🩺 manda aquí)
  function differsHTML() {
    var l = (_st.sample && _st.sample.differs_list) || [];
    if (!l.length) return '';
    return '<div class="kau-out" style="margin-top:8px"><b class="kau-bad">' + esc(L('Distintas en la última muestra', 'Different in the last sample')) + '</b>' +
      l.map(function (x) {
        var o = _open[x.decision_id] || {};
        return '<div class="kau-row" data-id="' + esc(x.decision_id) + '"><div class="kau-rh"><span class="kau-k">' + esc(x.kind) + '</span>' +
          '<code>' + esc(String(x.decision_id).slice(0, 8)) + '</code></div>' +
          ((x.paths || []).length ? '<div class="kau-mut">' + esc(L('Campos: ', 'Fields: ')) + x.paths.slice(0, 4).map(function (p) { return '<code>' + esc(p) + '</code>'; }).join(', ') + '</div>' : '') +
          '<div class="kau-acts"><button class="kau-btn pri" data-a="replay" data-id="' + esc(x.decision_id) + '">' + esc(L('Repetir', 'Replay')) + '</button></div>' +
          (o.repErr ? '<div class="kau-out kau-bad">❌ ' + esc(o.repErr) + '</div>' : '') +
          (o.rep ? '<div class="kau-out">' + replayHTML(o.rep) + '</div>' : '') + '</div>';
      }).join('') + '</div>';
  }

  function filtersHTML() {
    var ko = '<option value="">' + esc(L('Todos los tipos', 'All kinds')) + '</option>' +
      (_st.kinds || []).map(function (k) {
        return '<option value="' + esc(k.kind) + '"' + (k.kind === _f.kind ? ' selected' : '') + '>' + esc(en() ? k.en : k.es) +
          (k.replayable ? ' ⟳' : '') + '</option>';
      }).join('');
    var wo = '<option value="">' + esc(L('Cualquiera', 'Anyone')) + '</option>' +
      Object.keys(WHO).map(function (k) { return '<option value="' + k + '"' + (k === _f.who ? ' selected' : '') + '>' + esc(L(WHO[k][0], WHO[k][1])) + '</option>'; }).join('');
    return '<div class="kau-filters">' +
      '<select data-f="kind" aria-label="' + esc(L('Tipo de decisión', 'Decision kind')) + '">' + ko + '</select>' +
      '<select data-f="who" aria-label="' + esc(L('Quién decidió', 'Who decided')) + '">' + wo + '</select>' +
      '<input type="date" data-f="day" value="' + esc(_f.day) + '" aria-label="' + esc(L('Fecha (UTC)', 'Date (UTC)')) + '" title="' + esc(L('Fecha (UTC)', 'Date (UTC)')) + '">' +
      '<button class="kau-btn" data-a="reload">↻ ' + esc(L('Actualizar', 'Refresh')) + '</button></div>';
  }

  function whyHTML(w) {
    var lines = en() ? w.lines_en : w.lines_es;
    var h = '<b>' + esc(L('¿Por qué?', 'Why?')) + '</b>' + chip('audit_why') + '<ul>' +
      (lines || []).map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>';
    if (w.violations && w.violations.length) {
      h += '<div class="kau-mut">' + esc(L('Reglas que avisaron: ', 'Rules that warned: ')) +
        w.violations.slice(0, 6).map(function (v) { return '<code>' + esc(String(v.rule || '').replace('khr:', '')) + '</code>'; }).join(', ') + '</div>';
    }
    if (w.redacted) h += '<div class="kau-mut">' + esc(L('Resumen sin datos personales ni de clientes; con tu PIN se ve el detalle.',
      'Summary without personal or client data; with your PIN you see the detail.')) + '</div>';
    return h;
  }

  function stepIcon(ok) { return ok === true ? '<span class="kau-ok">✓</span>' : ok === false ? '<span class="kau-bad">✗</span>' : '<span class="kau-mut">·</span>'; }

  function replayHTML(r) {
    var v = VERD[r.verdict] || [r.verdict, r.verdict, 'mut'];
    var h = '<div class="kau-rh"><b>' + esc(L('Repetición', 'Replay')) + '</b>' + chip('audit_replay') +
      '<span class="kau-tag ' + v[2] + '">' + esc(L(v[0], v[1])) + '</span>' + chip('audit_verdict') +
      (r.fidelity === 'approximate' ? '<span class="kau-tag warn">' + esc(L('aproximada', 'approximate')) + '</span>' + chip('audit_approx') : '') + '</div>' +
      '<div style="margin-top:6px">' + esc(T(r.explanation)) + '</div>';
    if (r.fidelity === 'approximate' && r.approximations_text && r.approximations_text.length) {
      h += '<div class="kau-mut">' + esc(L('Por qué es aproximada: ', 'Why it is approximate: ')) +
        r.approximations_text.slice(0, 6).map(function (a) { return esc(T(a)); }).join('; ') + '</div>';
    }
    h += '<ul>';
    (r.steps || []).forEach(function (s) {
      var extra = '';
      var diffs = s.diffs || [];
      if (diffs.length) {
        extra = '<div class="kau-mut">' + diffs.slice(0, 6).map(function (d) {
          return '<code>' + esc(d.path) + '</code>: ' + esc(L('registrado', 'recorded')) + ' <code>' + esc(JSON.stringify(d.recorded)) +
            '</code> → ' + esc(L('repetido', 'replayed')) + ' <code>' + esc(JSON.stringify(d.replayed)) + '</code>';
        }).join('<br>') + '</div>';
      } else if (s.diff_paths && s.diff_paths.length) {
        extra = '<div class="kau-mut">' + esc(L('Campos distintos: ', 'Different fields: ')) + s.diff_paths.slice(0, 6).map(function (p) { return '<code>' + esc(p) + '</code>'; }).join(', ') + '</div>';
      } else if (s.name === 'seal' && s.pending) {
        extra = ' <span class="kau-mut">(' + esc(L('se sella en menos de un minuto', 'sealed within a minute')) + ')</span>';
      }
      h += '<li>' + stepIcon(s.ok) + ' ' + esc(T(s.label) || s.name) + extra + '</li>';
    });
    h += '</ul>';
    if (r.world) {
      h += '<div class="kau-mut">' + esc(L('Mundo de entonces: versión del grafo ', 'World of then: graph version ')) + esc(r.world.graph_version) +
        ' · release <code>' + esc(r.world.release) + '</code>' + (r.cost_ms != null ? ' · ' + esc(r.cost_ms) + ' ms' : '') + '</div>';
    }
    if (r.redacted) {
      h += '<div class="kau-acts"><button class="kau-btn" data-a="replay-pin" data-id="' + esc(r.decision_id) + '">🔓 ' +
        esc(L('Ver detalle con PIN', 'See detail with PIN')) + '</button></div>';
    }
    return h;
  }

  function rowHTML(it) {
    var o = _open[it.id] || {};
    var who = WHO[it.principal_kind] ? L(WHO[it.principal_kind][0], WHO[it.principal_kind][1]) : it.principal_kind;
    var vo = it.verdict_outcome;
    var meta = esc(who) + (it.principal_id ? ' (<code>' + esc(it.principal_id) + '</code>)' : '') + ' · ' + esc(it.channel || '') +
      ' · ' + esc(L('grafo v', 'graph v')) + esc(it.graph_version == null ? '—' : it.graph_version) + ' · ' + esc(L('reglas', 'rules')) +
      ' <code>' + esc(it.release) + '</code>';
    var out = '';
    if (o.whyErr || o.repErr) out += '<div class="kau-out kau-bad">❌ ' + esc(o.whyErr || o.repErr) + '</div>';
    if (o.why) out += '<div class="kau-out">' + whyHTML(o.why) + '</div>';
    if (o.rep) out += '<div class="kau-out">' + replayHTML(o.rep) + '</div>';
    return '<div class="kau-row" data-id="' + esc(it.id) + '"><div class="kau-rh"><span class="kau-k">' + esc(T(it.kind_label) || it.kind) + '</span>' +
      '<span class="kau-tag">' + esc(T(it.status_label) || it.status) + '</span>' +
      (vo && vo !== 'pass' ? '<span class="kau-tag ' + (vo === 'block' ? 'bad' : 'warn') + '">' + esc(vo === 'block' ? L('bloqueada', 'blocked') : L('con avisos', 'with warnings')) + '</span>' : '') +
      (it.replayable ? '<span class="kau-tag ok" title="' + esc(L('Tiene un cálculo que se puede repetir', 'It has a computation that can be replayed')) + '">⟳ ' + esc(L('repetible', 'replayable')) + '</span>' : '') +
      '</div><div class="kau-mut">' + fmtWhen(it.recorded_at) + ' · ' + meta + '</div>' +
      '<div class="kau-acts"><button class="kau-btn" data-a="why" data-id="' + esc(it.id) + '"' + (_busy[it.id + 'w'] ? ' disabled' : '') + '>' + esc(L('¿Por qué?', 'Why?')) + '</button>' +
      '<button class="kau-btn pri" data-a="replay" data-id="' + esc(it.id) + '"' + (_busy[it.id + 'r'] ? ' disabled' : '') + '>' +
      esc(_busy[it.id + 'r'] ? L('Repitiendo…', 'Replaying…') : L('Repetir', 'Replay')) + '</button></div>' + out + '</div>';
  }

  function render() {
    if (!_box) return;
    ensureStyles();
    var list;
    if (_st.loading && !_st.items.length) list = '<div class="kau-empty">' + esc(L('Cargando el libro…', 'Loading the ledger…')) + '</div>';
    else if (_st.err) list = '<div class="kau-empty kau-bad">❌ ' + esc(_st.err) + '</div>';
    else if (!_st.items.length) list = '<div class="kau-empty">' + esc(L('No hay decisiones con esos filtros.', 'No decisions with those filters.')) + '</div>';
    else list = _st.items.map(rowHTML).join('');
    var more = (_st.items.length >= _st.limit && _st.limit < 200)
      ? '<div class="kau-acts"><button class="kau-btn" data-a="more">' + esc(L('Ver más', 'Show more')) + '</button></div>' : '';
    _box.innerHTML = '<div class="kau-root"><div class="kau-card" id="kau-card">' +
      '<div class="kau-hd"><b>⚖ ' + esc(L('Auditoría — decisiones del libro', 'Audit — ledger decisions')) + '</b>' + chip('audit_replay') + '</div>' +
      '<div class="kau-mut">' + esc(L('Cada acción del sistema deja una ficha que nadie puede borrar. Elige una para ver por qué se tomó o para repetirla con lo que el sistema sabía en ese momento.',
        'Every action of the system leaves a record nobody can erase. Pick one to see why it was taken or to replay it with what the system knew at that moment.')) + '</div>' +
      '<div class="kau-mut" style="margin-top:6px">' + sampleLine() + '</div>' + differsHTML() +
      filtersHTML() + (_st.redacted ? '<div class="kau-mut">' + esc(L('Vista sin PIN: no se muestran quiénes son las personas ni los datos de clientes.', 'View without PIN: people identities and client data are not shown.')) + '</div>' : '') +
      '<div class="kau-list">' + list + '</div>' + more + '</div></div>';
  }

  async function doWhy(id) {
    var o = _open[id] = _open[id] || {};
    if (o.why) { delete o.why; render(); return; }
    _busy[id + 'w'] = true; o.whyErr = ''; render();
    try { o.why = await getJSON(BASE + '/api/ledger/why/' + encodeURIComponent(id)); }
    catch (e) { o.whyErr = String(e && e.message || e); }
    _busy[id + 'w'] = false; render();
  }

  async function doReplay(id, withPin) {
    var o = _open[id] = _open[id] || {};
    _busy[id + 'r'] = true; o.repErr = ''; render();
    try {
      o.rep = await getJSON(BASE + '/api/ledger/replay/' + encodeURIComponent(id),
        { method: 'POST', headers: Object.assign(pinHeaders(), { 'Content-Type': 'application/json' }), body: '{"mode":"audit"}' }, !!withPin);
    } catch (e) { o.repErr = String(e && e.message || e); }
    _busy[id + 'r'] = false; render();
  }

  function onClick(ev) {
    var b = ev.target.closest && ev.target.closest('[data-a]');
    if (!b || !_box.contains(b)) return;
    var a = b.getAttribute('data-a'), id = b.getAttribute('data-id');
    if (a === 'reload') load();
    else if (a === 'more') { _st.limit = Math.min(200, _st.limit + 30); load(); }
    else if (a === 'why' && id) doWhy(id);
    else if (a === 'replay' && id) doReplay(id, false);
    else if (a === 'replay-pin' && id) doReplay(id, true);
  }
  function onChange(ev) {
    var t = ev.target, f = t && t.getAttribute && t.getAttribute('data-f');
    if (!f) return;
    _f[f] = t.value || '';
    _st.limit = 20;
    load();
  }

  function mount(id) {
    var el = document.getElementById(id);
    if (!el) return;
    if (_box !== el) {
      _box = el;
      el.addEventListener('click', onClick);
      el.addEventListener('change', onChange);
    }
    load();
  }

  window.KhipuAudit = { mount: mount, render: render, _state: function () { return { st: _st, f: _f, open: _open }; } };
})();
