/* ============================================================================
   engine/hotclient.js — EL cliente de las vistas rápidas del servidor (window.KhipuHot)
   INFRA_OPERATIVA §4.6-§4.7 (paso 13, 2026-10-13): en el navegador NO queda ningún motor de contagio.
   Toda cifra de impacto que se ve (X-Ray, Cabina, simulación en vivo, voz, Insights, brief, Second Brain,
   banner de colapso del mapa, sala de guerra) sale de UN solo kernel: matrix.engine.propagate en el servidor,
   servido por /api/hot/* (Postgres si hay DATABASE_URL; si no, el snapshot data/grafo_v0.json con el MISMO
   código — `view.source` lo dice). Así la misma caída da el mismo número en todas las pantallas.

     KhipuHot.impact(id, {severity, top})        GET  /api/hot/impact/<id>   (colapso precalculado o choque parcial)
     KhipuHot.chokepoints({by, limit})           GET  /api/hot/chokepoints   (ranking por Σ impacto o por conteo)
     KhipuHot.factors()                          GET  /api/hot/factors       (factores sistémicos activos)
     KhipuHot.scenario(body)                     POST /api/hot/scenario      (varias fuentes; factores 'active')
     KhipuHot.simulate({targets, kind, severity}) → la forma única que usan las pantallas (ver abajo)
     KhipuHot.stamp(view) / stampHTML(view)       "g18 · base · hace 3 s" (generación y edad, discreto)
     KhipuHot.rivals(shockIds, impact, max)       rivales del mismo rubro poco golpeados (SIN % inventado)

   Caché pequeña por generación: cada respuesta trae `view.generation` (+ ETag y X-Khipu-Graph-Version); si
   cambia, se olvida todo lo guardado. Las lecturas GET se revalidan con If-None-Match (304) tras 60 s.
   Errores SIEMPRE bilingües y honestos: sin conexión → "no se puede calcular sin conexión" (nunca un número
   distinto calculado aquí); vistas calentando → "se están preparando"; un tipo de golpe que el servidor aún
   no calcula (auge de demanda hacia proveedores, `direction:'up'`) → se dice, sin cifras.
   ============================================================================ */
(function () {
  'use strict';
  var W = (typeof window !== 'undefined') ? window : globalThis;

  function isEn() {
    var l = W.LANG;
    if (!l) { try { l = W.localStorage && W.localStorage.getItem('eco_lang'); } catch (e) { l = null; } }
    return l === 'en';
  }
  function L(es, en) { return isEn() ? en : es; }
  function base() { return (typeof W.BASE === 'string' && W.BASE) ? W.BASE : ''; }

  var TTL_MS = 60000;          // tras 60 s una lectura GET se revalida (ETag → 304, sin cuerpo)
  var MAX_ENTRIES = 80;        // caché pequeña: ~80 respuestas (impactos de las empresas que se miran)
  var IMPACT_TOP = 500;        // = TOP_CAP del servidor: todas las víctimas para pintar el mapa y sumar
  var UP_RETRY_MS = 300000;    // si el servidor dijo que 'up' no está, no se le vuelve a preguntar en 5 min
  var FETCH_TIMEOUT_MS = 8000; // una petición colgada no deja a la pantalla (ni a la voz, 10 s) esperando para siempre

  var _cache = new Map();      // clave → {etag, at, gen, res}
  var _inflight = new Map();   // clave → Promise (dos pantallas que piden lo mismo a la vez = UNA petición)
  var _gen = null;             // generación vista por última vez
  var _gv = null;              // X-Khipu-Graph-Version vista por última vez
  var _lastView = null;
  var _upUnsupportedAt = 0;
  var _stats = { requests: 0, hits: 0, revalidated: 0, flushes: 0, errors: 0 };

  // ── tipos de golpe → cómo los calcula el servidor (mapa EXPLÍCITO; nada se adivina) ──
  var KINDS = {
    collapse: { direction: 'down', mapped: false },
    sanction: { direction: 'down', mapped: true,
      note_es: 'Una sanción se calcula como un corte de suministro con el mismo motor de contagio.',
      note_en: 'A sanction is computed as a supply cut with the same contagion engine.' },
    price:    { direction: 'down', mapped: true,
      note_es: 'Un shock de precio se propaga con el mismo motor de contagio: la cifra es la intensidad transmitida (0-100), no un % de precio.',
      note_en: 'A price shock propagates with the same contagion engine: the figure is the transmitted intensity (0-100), not a % price move.' },
    demand:   { direction: 'up', mapped: false },
  };

  function err(code, es, en, extra) {
    var o = { ok: false, code: code, error: L(es, en), error_es: es, error_en: en };
    if (extra) for (var k in extra) if (Object.prototype.hasOwnProperty.call(extra, k)) o[k] = extra[k];
    _stats.errors++;
    return o;
  }
  function offlineErr() {
    return err('offline',
      'No se puede calcular sin conexión: el impacto lo calcula el servidor con un solo motor (no hay otro número en tu navegador).',
      "Can't compute offline: impact is computed by the server with one single engine (there is no other number in your browser).",
      { offline: true });
  }
  function timeoutErr() {
    return err('timeout',
      'El servidor tardó demasiado en calcular el impacto; reintenta en unos segundos (no mostramos otro número).',
      'The server took too long to compute the impact; retry in a few seconds (we do not show another number).',
      { timeout: true });
  }
  function timer() {
    var st = (typeof W.setTimeout === 'function') ? W.setTimeout : (typeof setTimeout === 'function' ? setTimeout : null);
    var ct = (typeof W.clearTimeout === 'function') ? W.clearTimeout : (typeof clearTimeout === 'function' ? clearTimeout : null);
    return st ? { set: function (fn, ms) { return st(fn, ms); }, clear: function (h) { if (ct) ct(h); } } : null;
  }
  function unsupportedUp() {
    return err('unsupported_direction',
      'El auge de demanda hacia los proveedores todavía no lo calcula el motor único del servidor. No mostramos cifras inventadas: por ahora simula un corte, una sanción o un shock de precio.',
      'Demand booms flowing up to suppliers are not computed by the server engine yet. We do not show made-up figures: for now simulate a cut, a sanction or a price shock.',
      { unsupported: true });
  }

  function flush(reason) {
    _cache.clear();
    _stats.flushes++;
    _stats.last_flush = reason || '';
  }
  // nueva generación (o nueva versión del grafo) → todo lo guardado era de otra foto del grafo
  function noteView(view) {
    if (!view) return;
    // edad VIVA: age_ms es la del momento de la respuesta; el sello suma lo que pasó desde que llegó (antes
    // quedaba congelada en "hace 8 s" toda la sesión, incluso tras cada 304)
    try { view._recv_at = Date.now(); view._age0 = view.age_ms; } catch (e) {}
    _lastView = view;
    if (view.generation && _gen && view.generation !== _gen) flush('generation');
    if (view.generation) _gen = view.generation;
  }
  function noteVersion(v) {
    if (v == null || v === '') return;
    v = String(v);
    if (_gv !== null && v !== _gv) flush('graph_version');
    _gv = v;
  }

  function put(key, entry) {
    if (_cache.size >= MAX_ENTRIES) { var first = _cache.keys().next(); if (!first.done) _cache.delete(first.value); }
    _cache.set(key, entry);
  }
  function hdr(r, name) { try { return r.headers && r.headers.get ? r.headers.get(name) : null; } catch (e) { return null; } }

  function request(method, path, body, key) {
    var now = Date.now();
    var hit = key ? _cache.get(key) : null;
    if (hit && hit.gen === _gen && now - hit.at < TTL_MS) { _stats.hits++; return Promise.resolve(hit.res); }
    if (key && _inflight.has(key)) return _inflight.get(key);
    if (W.navigator && W.navigator.onLine === false) return Promise.resolve(offlineErr());
    if (typeof W.fetch !== 'function') return Promise.resolve(offlineErr());
    var headers = { 'Accept': 'application/json' };
    if (body != null) headers['Content-Type'] = 'application/json';
    if (hit && hit.etag && method === 'GET') headers['If-None-Match'] = hit.etag;
    _stats.requests++;
    var ctl = null;
    try { ctl = (typeof W.AbortController === 'function') ? new W.AbortController() : null; } catch (e) { ctl = null; }
    var init = { method: method, headers: headers, body: body != null ? JSON.stringify(body) : undefined };
    if (ctl) init.signal = ctl.signal;
    var fp = W.fetch(base() + path, init)
      .then(function (r) {
        noteVersion(hdr(r, 'X-Khipu-Graph-Version'));
        if (r.status === 304 && hit) {
          _stats.revalidated++;
          hit.at = Date.now();
          if (key) _cache.set(key, hit);
          return hit.res;
        }
        return Promise.resolve(r.json ? r.json() : null).catch(function () { return null; }).then(function (d) {
          if (!r.ok || !d || typeof d !== 'object') {
            if (d && d.offline) return offlineErr();
            if (r.status === 503 && d && d.code === 'view_warming')
              return err('view_warming', 'Las vistas rápidas se están preparando (arranque del servidor); reintenta en unos segundos.',
                'Fast views are warming up (server startup); retry in a few seconds.', { retry_after: d.retry_after || 3 });
            if (r.status === 400 && d && d.param === 'direction') return unsupportedUp();
            if (r.status === 404 && d && d.code === 'unknown_id')
              return err('unknown_id', 'El servidor no conoce esa empresa.', 'The server does not know that company.');
            if (r.status === 429)
              return err('rate_limited', 'Demasiadas simulaciones seguidas; espera unos segundos.', 'Too many simulations in a row; wait a few seconds.');
            if (!d) return err('bad_response', 'El servidor respondió algo que no es JSON.', 'The server returned something that is not JSON.', { status: r.status });
            return err(d.code || ('http_' + r.status), d.error || ('Error ' + r.status), d.error_en || d.error || ('Error ' + r.status), { status: r.status });
          }
          var res = { ok: true, data: d.data, view: d.view || null };
          noteView(res.view);
          if (key) put(key, { etag: hdr(r, 'ETag'), at: Date.now(), gen: _gen, res: res });
          return res;
        });
      })
      .catch(function () { return offlineErr(); });
    // tope de FETCH_TIMEOUT_MS: aborta la petición y responde un error honesto; el _inflight se libera siempre
    var tm = timer(), h = null, p = fp;
    if (tm) {
      var timed = false;
      p = Promise.race([fp, new Promise(function (res) {
        h = tm.set(function () { timed = true; try { if (ctl) ctl.abort(); } catch (e) {} res(null); }, FETCH_TIMEOUT_MS);
      })]).then(function (v) {
        tm.clear(h);
        return timed ? timeoutErr() : v;
      });
    }
    if (key) {
      _inflight.set(key, p);
      var done = function () { _inflight.delete(key); };
      p.then(done, done);
    }
    return p;
  }

  function clampSev(v) {
    var n = Number(v);
    if (!isFinite(n)) return 100;
    return Math.max(0, Math.min(100, Math.round(n)));
  }

  // ── lecturas crudas ──
  function impact(id, opts) {
    opts = opts || {};
    var sev = clampSev(opts.severity == null ? 100 : opts.severity);
    var top = Math.max(1, Math.min(IMPACT_TOP, Math.round(Number(opts.top) || IMPACT_TOP)));
    var q = '?top=' + top + (sev < 100 ? '&severity=' + sev + '&kind=shock' : '');
    var path = '/api/hot/impact/' + encodeURIComponent(String(id || '').slice(0, 120)) + q;
    return request('GET', path, null, 'impact:' + path);
  }
  function chokepoints(opts) {
    opts = opts || {};
    var by = opts.by === 'count' ? 'count' : 'sum';
    var limit = Math.max(1, Math.min(200, Math.round(Number(opts.limit) || 25)));
    var path = '/api/hot/chokepoints?by=' + by + '&limit=' + limit;
    return request('GET', path, null, 'choke:' + path);
  }
  function factors() { return request('GET', '/api/hot/factors', null, 'factors'); }
  function status() { return request('GET', '/api/hot/status', null, null); }
  function scenario(body) {
    body = body || {};
    if (String(body.direction || 'down') === 'up' && Date.now() - _upUnsupportedAt < UP_RETRY_MS) return Promise.resolve(unsupportedUp());
    var payload = { shocks: body.shocks || [], factors: body.factors || 'active', direction: body.direction || 'down',
      top: body.top || IMPACT_TOP };
    return request('POST', '/api/hot/scenario', payload, 'scn:' + JSON.stringify(payload)).then(function (res) {
      if (!res.ok && res.code === 'unsupported_direction') _upUnsupportedAt = Date.now();
      return res;
    });
  }

  // ── la forma ÚNICA que usan las pantallas ──
  // opts: {targets:[ids] | id, kind: collapse|sanction|price|demand, severity: 0-100}
  // → {ok, kind, direction, mapped, note, severity, targets, impact: Map(id → % 0-100, incluidas las
  //    semillas), victims:[{id,label,pct,hop}], affected, reach_1, reach_10, sum_impact, by_hop, view}
  function simulate(opts) {
    opts = opts || {};
    var targets = Array.isArray(opts.targets) ? opts.targets.slice() : (opts.id != null ? [opts.id] : []);
    targets = targets.filter(function (x) { return x != null && String(x).length; }).map(String);
    var kind = KINDS[opts.kind] ? opts.kind : 'collapse';
    var spec = KINDS[kind];
    var sev = clampSev(opts.severity == null ? 100 : opts.severity);
    if (!targets.length) return Promise.resolve(err('no_targets', 'Elige al menos una empresa.', 'Pick at least one company.'));
    var p;
    if (spec.direction === 'down' && targets.length === 1) p = impact(targets[0], { severity: sev });
    else p = scenario({ shocks: targets.slice(0, 200).map(function (id) { return { id: id, magnitude: sev / 100 }; }),
      factors: 'active', direction: spec.direction });
    return p.then(function (res) {
      if (!res.ok) { res.kind = kind; res.direction = spec.direction; return res; }
      var d = res.data || {};
      var seeds = (d.shocks || (d.id ? [{ id: d.id, magnitude: sev / 100 }] : [])).map(function (s) { return s.id; });
      var m = new Map();
      seeds.forEach(function (id) { m.set(id, sev); });
      (d.victims || []).forEach(function (v) { if (!m.has(v.id)) m.set(v.id, v.pct); });
      return {
        ok: true, kind: kind, direction: spec.direction, mapped: !!spec.mapped,
        note: spec.mapped ? L(spec.note_es, spec.note_en) : '',
        severity: sev, targets: seeds, impact: m, victims: (d.victims || []).slice(),
        affected: d.affected || 0, reach_1: d.reach_1 || 0, reach_10: d.reach_10 || 0,
        sum_impact: d.sum_impact || 0, by_hop: d.by_hop || {}, view: res.view || null,
        unknown_ids: d.unknown_ids || [],
      };
    });
  }

  // rivales del mismo rubro que el servidor marca poco golpeados (< 15 %) frente a empresas muy golpeadas
  // (≥ 40 %): quién PODRÍA captar la demanda huérfana. Solo filtra cifras del servidor; NO inventa un % de
  // ganancia (antes: "+min(45, gains×14) %"). Orden: cuántas caídas hay en su rubro y su capitalización.
  function rivals(shockIds, impactMap, max) {
    var NB = W.NODE_BY_ID || {}, META = W.NODE_META || {};
    var get = function (id) { return impactMap && impactMap.get ? (impactMap.get(id) || 0) : ((impactMap || {})[id] || 0); };
    var ids = impactMap && impactMap.forEach ? [] : Object.keys(impactMap || {});
    if (impactMap && impactMap.forEach && impactMap.get) impactMap.forEach(function (v, k) { ids.push(k); });
    var seeds = {}; (shockIds || []).forEach(function (s) { seeds[s] = 1; });
    var damagedByCat = {};
    ids.forEach(function (id) {
      if (get(id) < 40) return;
      var n = NB[id]; if (!n || !n.cat) return;
      damagedByCat[n.cat] = (damagedByCat[n.cat] || 0) + 1;
    });
    var out = [];
    (W.NODES || []).forEach(function (n) {
      if (!n || !n.id || seeds[n.id]) return;
      var dmg = damagedByCat[n.cat]; if (!dmg) return;
      var hit = get(n.id); if (hit >= 15) return;
      out.push({ id: n.id, hit: Math.round(hit * 10) / 10, cat_damaged: dmg, cap: Number((META[n.id] || {}).mktcap_b) || 0 });
    });
    out.sort(function (a, b) { return (b.cat_damaged - a.cat_damaged) || (b.cap - a.cap) || (a.id < b.id ? -1 : 1); });
    return out.slice(0, max || 4);
  }

  // ── sello de versión (discreto): generación y edad ──
  function ago(ms) {
    if (ms == null || !isFinite(ms)) return '';
    var s = Math.max(0, Math.round(ms / 1000));
    if (s < 60) return L('hace ' + s + ' s', s + ' s ago');
    var m = Math.round(s / 60);
    if (m < 60) return L('hace ' + m + ' min', m + ' min ago');
    return L('hace ' + Math.round(m / 60) + ' h', Math.round(m / 60) + ' h ago');
  }
  function stamp(view) {
    view = view || _lastView;
    if (!view || !view.generation) return '';
    var src = view.source === 'pg' ? L('base', 'database') : view.source === 'snapshot' ? L('catálogo', 'catalog') : String(view.source || '');
    var parts = ['g' + (view.graph_version != null ? view.graph_version : '?'), src];
    var age = (view._recv_at && view._age0 != null && isFinite(view._age0)) ? view._age0 + (Date.now() - view._recv_at) : view.age_ms;
    var a = ago(age); if (a) parts.push(a);
    if (view.stale) parts.push(L('desactualizada', 'stale'));
    return parts.join(' · ');
  }
  function escAttr(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function stampHTML(view) {
    view = view || _lastView;
    var s = stamp(view);
    if (!s) return '';
    var title = L('Motor único del servidor · generación ', 'Single server engine · generation ') + view.generation +
      (view.built_at ? ' · ' + view.built_at : '') + ' · ' + (view.method || 'propagate@1');
    return '<span class="kh-hot-stamp" title="' + escAttr(title) + '" style="font-size:10.5px;opacity:.62;font-family:\'JetBrains Mono\',monospace;white-space:nowrap">' +
      escAttr(s) + '</span>';
  }

  var api = {
    impact: impact, chokepoints: chokepoints, factors: factors, scenario: scenario, status: status,
    simulate: simulate, rivals: rivals, stamp: stamp, stampHTML: stampHTML,
    kinds: function () { return Object.keys(KINDS); },
    kindSpec: function (k) { var s = KINDS[k]; return s ? { direction: s.direction, mapped: !!s.mapped, note: s.mapped ? L(s.note_es, s.note_en) : '' } : null; },
    lastView: function () { return _lastView; },
    generation: function () { return _gen; },
    flush: function () { flush('manual'); _upUnsupportedAt = 0; },
    stats: function () { var o = {}; for (var k in _stats) o[k] = _stats[k]; o.entries = _cache.size; o.generation = _gen; o.graph_version = _gv; return o; },
    TTL_MS: TTL_MS, IMPACT_TOP: IMPACT_TOP, FETCH_TIMEOUT_MS: FETCH_TIMEOUT_MS,
  };
  W.KhipuHot = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
