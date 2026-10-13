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
     KhipuHot.card(id, {structure}) / cardCached GET  /api/hot/card/<id>     (tarjeta V3: NRS, flujo, estructura)
     KhipuHot.nrs(ids)                           GET  /api/hot/nrs?ids=      (vector NRS, LA fórmula del servidor)
     KhipuHot.scenario(body)                     POST /api/hot/scenario      (varias fuentes; factores 'active')
     KhipuHot.simulate({targets, kind, severity}) → la forma única que usan las pantallas (ver abajo)
     KhipuHot.stamp(view) / stampHTML(view)       "g18 · base · hace 3 s" (generación y edad, discreto)
     KhipuHot.rivals(shockIds, impact, max)       rivales del mismo rubro poco golpeados (SIN % inventado)
     KhipuHot.pnlLine(el, {targets, severity, kind}) "Tu cartera: −X ± Y USD" con el κ calibrado del SERVIDOR
                                                  (POST /api/hot/scenario_pnl); solo con posiciones; débil → sin cifra

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
  // ── paso 14: tarjeta V3 (NRS + 5 términos, proveedores/clientes en pares distintos de FLUJO, estructura) ──
  function cardPath(id, structure) {
    return '/api/hot/card/' + encodeURIComponent(String(id || '').slice(0, 120)) + '?lang=' + (isEn() ? 'en' : 'es') +
      (structure === false ? '&structure=0' : '');
  }
  function card(id, opts) {
    opts = opts || {};
    var path = cardPath(id, opts.structure);
    return request('GET', path, null, 'card:' + path);
  }
  // la tarjeta ya descargada (cualquier idioma/variante) de la generación vigente, o null — para código síncrono
  function cardCached(id) {
    var pre = 'card:/api/hot/card/' + encodeURIComponent(String(id || '').slice(0, 120)) + '?';
    var best = null;
    _cache.forEach(function (e, k) {
      if (k.indexOf(pre) === 0 && e && e.res && e.res.ok && e.gen === _gen && (!best || e.at > best.at)) best = e;
    });
    return best ? best.res.data : null;
  }
  function nrs(ids) {
    ids = (ids || []).filter(function (x) { return x != null && String(x).length; }).map(String).slice(0, 1000);
    var path = '/api/hot/nrs' + (ids.length ? '?ids=' + encodeURIComponent(ids.join(',')) : '');
    return request('GET', path, null, 'nrs:' + path);
  }
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

  // ── escenario → DINERO (batch I3, L2-13): UNA línea discreta "Tu cartera: −X ± Y USD", SOLO con posiciones ──
  // La cifra la calcula el SERVIDOR (POST /api/hot/scenario_pnl: el mismo kernel + κ calibrado de kernel.calibration);
  // aquí solo se valora cada posición (acciones × precio en USD que ya muestra la app). Si la calibración es débil,
  // falta o es de otro motor, el servidor lo dice y la línea lo dice: NUNCA un número calculado en el navegador.
  var PNL_POS_CAP = 100;
  function myPositions() {
    var pos = null;
    try { pos = (W.MKT && W.MKT.pos) || JSON.parse((W.localStorage && W.localStorage.getItem('eco_pos')) || '{}'); } catch (e) { pos = null; }
    var NB = W.NODE_BY_ID || {}, Q = (W.MKT && W.MKT.quotes) || {};
    var out = [], noPrice = 0;
    Object.keys(pos || {}).forEach(function (id) {
      var p = pos[id], sh = p ? Number(p.sh) : 0;
      if (!(sh > 0)) return;
      var n = NB[id], t = n && n.mkt ? String(n.mkt) : '';
      var q = t ? Q[t] : null;
      var px = q ? (typeof W.quotePx === 'function' ? W.quotePx(q) : Number(q.close)) : 0;
      if (!(px > 0)) { noPrice++; return; }
      out.push({ id: (n && n.id) || id, symbol: t, usd: Math.round(sh * px * 100) / 100 });
    });
    return { positions: out.slice(0, PNL_POS_CAP), no_price: noPrice, total: out.length + noPrice };
  }
  function scenarioPnl(opts) {
    opts = opts || {};
    var targets = (Array.isArray(opts.targets) ? opts.targets : (opts.id != null ? [opts.id] : [])).map(String).slice(0, 200);
    var sev = clampSev(opts.severity == null ? 100 : opts.severity);
    var mine = opts.positions ? { positions: opts.positions, no_price: 0 } : myPositions();
    if (!targets.length) return Promise.resolve(err('no_targets', 'Elige al menos una empresa.', 'Pick at least one company.'));
    if (!mine.positions.length) return Promise.resolve({ ok: true, data: { pnl: { status: 'no_positions' } }, no_price: mine.no_price });
    var body = { shocks: targets.map(function (id) { return { id: id, magnitude: sev / 100 }; }), positions: mine.positions,
      factors: 'active', record: opts.record !== false };
    // sin caché propia: el resultado depende de TUS posiciones y sus precios (cambian); no es una vista del grafo
    return request('POST', '/api/hot/scenario_pnl', body, null).then(function (res) {
      if (res && res.ok) res.no_price = mine.no_price;
      return res;
    });
  }
  function fmtUsd(v) {
    var n = Math.abs(Number(v) || 0), en = isEn();
    var s = n >= 1e6 ? (n / 1e6).toLocaleString(en ? 'en-US' : 'es-PE', { maximumFractionDigits: 1 }) + (en ? 'M' : ' M')
      : Math.round(n).toLocaleString(en ? 'en-US' : 'es-PE');
    return s + ' USD';
  }
  function registerPnlExplain() {
    if (typeof W.explainRegister !== 'function') return;
    W.explainRegister('scenario_pnl', {
      es: { t: '¿Cómo se pasa de "golpe" a dólares?',
        b: 'El motor dice qué parte del suministro pierde cada empresa (el %). Para pasarlo a <b>dinero</b> hace falta un factor ' +
           '<b>κ</b>: cuánto cae de verdad el precio de una empresa por cada punto de golpe.<br><br>' +
           'κ se mide con <b>episodios reales</b> (propuestos: escasez de chips 2021, controles de exportación 2022, terremoto de Taiwán 2024): ' +
           'se compara la caída de cada empresa frente al mercado con el golpe que el motor le da. El resultado es <b>−κ × golpe × lo que tienes</b>, ' +
           'con una banda <b>±</b> (90 %) que suma la duda sobre κ y el ruido de cada acción.<br><br>' +
           'Si esa medición es <b>débil</b> (pocos datos, el golpe no explica las caídas), Khipus <b>no da una cifra</b> y lo dice. Hoy es así: ' +
           'con los datos disponibles el golpe del motor no predice las caídas de precio. <b>No es un pronóstico</b> ni una recomendación.' },
      en: { t: 'How does a "hit" become dollars?',
        b: 'The engine says what share of supply each company loses (the %). Turning it into <b>money</b> needs a factor <b>κ</b>: how much a ' +
           'company\'s price really falls per point of hit.<br><br>' +
           'κ is measured on <b>real episodes</b> (proposed: 2021 chip shortage, 2022 export controls, 2024 Taiwan earthquake): each company\'s ' +
           'fall versus the market is compared with the hit the engine gives it. The result is <b>−κ × hit × what you hold</b>, with a <b>±</b> band ' +
           '(90%) that adds the doubt about κ and each stock\'s noise.<br><br>' +
           'If that measurement is <b>weak</b> (little data, the hit does not explain the falls), Khipus <b>gives no figure</b> and says so. That is the ' +
           'case today: with the available data the engine\'s hit does not predict price falls. <b>Not a forecast</b> or a recommendation.' } });
  }
  function pnlLineHTML(res) {
    if (!res || !res.ok) return '';
    var p = (res.data && res.data.pnl) || {};
    if (p.status === 'no_positions') return '';
    var chip = (registerPnlExplain(), typeof W.explainChip === 'function') ? W.explainChip('scenario_pnl') : '';
    var head = '<b>' + L('Tu cartera: ', 'Your portfolio: ') + '</b>';
    var cal = p.calibration || {};
    if (p.status === 'ok') {
      var nEp = cal.n_episodes || 0;
      var sign = p.pnl_usd < 0 ? '−' : (p.pnl_usd > 0 ? '+' : '');
      var txt = sign + fmtUsd(p.pnl_usd).replace(' USD', '') + ' ± ' + fmtUsd(p.band_usd) +
        ' <span style="opacity:.72">(' + L('estimación con ' + nEp + ' episodios', 'estimate from ' + nEp + ' episodes') + ')</span>';
      if (p.extrapolated) txt += ' <span style="opacity:.72">· ' + L('fuera del rango medido', 'beyond the measured range') + '</span>';
      // revisión lote I: posiciones sin precio en USD (aún sin cotización, privadas) o que el servidor no ubicó en el
      // grafo NO están en la cifra → se dice cuántas (nunca una cartera parcial rotulada como «Tu cartera» a secas)
      var left = (Number(res.no_price) || 0) + ((p.unmapped && p.unmapped.length) || 0);
      if (left > 0) txt += ' <span style="opacity:.72">· ' + L('sin valorar: ' + left + (left === 1 ? ' posición' : ' posiciones'),
        'not valued: ' + left + (left === 1 ? ' position' : ' positions')) + '</span>';
      return head + txt + chip;
    }
    var why = p.status === 'weak' ? L('sin cifra en dinero: la calibración con episodios reales es débil', 'no money figure: the calibration on real episodes is weak')
      : p.status === 'kernel_mismatch' ? L('sin cifra en dinero: la calibración es de otra versión del motor', 'no money figure: the calibration is for another engine version')
        : L('sin cifra en dinero: todavía no está calibrado', 'no money figure: not calibrated yet');
    return head + '<span style="opacity:.8">' + why + '</span>' + chip;
  }
  // pinta la línea en `el` (o la oculta) SIN bloquear a quien llama: la simulación ya se mostró
  function pnlLine(el, opts) {
    if (!el) return Promise.resolve(null);
    opts = opts || {};
    var spec = KINDS[opts.kind] || KINDS.collapse;
    if (spec.direction !== 'down') { el.innerHTML = ''; el.style.display = 'none'; return Promise.resolve(null); }
    var mine = myPositions();
    var tok = {}; el._pnlTok = tok;
    // posiciones sin cotización todavía (p. ej. al arrancar): se repinta UNA vez cuando llegan los precios
    if (mine.no_price > 0 && typeof W.addEventListener === 'function') {
      var again = function () {
        W.removeEventListener('khipu:quotes', again);
        if (el._pnlTok === tok && el.isConnected !== false) pnlLine(el, Object.assign({}, opts, { record: false }));
      };
      W.addEventListener('khipu:quotes', again);
    }
    if (!mine.positions.length) { el.innerHTML = ''; el.style.display = 'none'; return Promise.resolve(null); }
    return scenarioPnl({ targets: opts.targets, severity: opts.severity, record: opts.record }).then(function (res) {
      if (el._pnlTok !== tok) return res;
      var h = pnlLineHTML(res);
      el.innerHTML = h;
      el.style.display = h ? '' : 'none';
      return res;
    });
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
    card: card, cardCached: cardCached, nrs: nrs,
    simulate: simulate, rivals: rivals, stamp: stamp, stampHTML: stampHTML,
    scenarioPnl: scenarioPnl, pnlLine: pnlLine, pnlLineHTML: pnlLineHTML, myPositions: myPositions,
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
