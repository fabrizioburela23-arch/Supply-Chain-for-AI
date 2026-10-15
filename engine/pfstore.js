/* ============================================================================
   engine/pfstore.js — UN SOLO LUGAR DONDE SE GUARDAN TUS POSICIONES

   Pedido de Fabrizio (2026-10-15): «que solo haya uno donde guardar, no 3».
   Antes había tres listas: «Mis posiciones» de Mercado (localStorage 'eco_pos'),
   las carteras de práctica ('kh_portfolios') y la cuenta del bróker. La cuenta
   del bróker sigue aparte (es la cuenta REAL, con órdenes). Lo que guardas tú
   vive SOLO aquí: 'kh_portfolios' (lista de carteras) + 'kh_pf_active' (cuál
   está activa).

   · MKT.pos ya no es una lista propia: es la VISTA {nodeId:{sh,bp}} de la cartera
     ACTIVA. Leer MKT.pos = leer la cartera activa; escribir (Mercado, panel de
     trading sin bróker) = `savePos()` → `applyView(MKT.pos)` → se guarda en la
     cartera activa. Así Mercado, la Terminal, el reporte de riesgo, el chat y la
     pestaña Carteras muestran LO MISMO.
   · Anotar una posición desde Mercado es «la tengo, a este precio»: no gasta la
     caja de la cartera; sube el capital inicial en lo que costó (y quitarla lo
     baja), así el P&L de Carteras sigue siendo valor − costo.
   · Migración (una vez, bandera 'kh_pos_migrated'; nunca pierde datos): si
     'eco_pos' tiene posiciones, pasan a una cartera «Mi cartera» (id fijo
     'pf_main': repetir no duplica) que queda ACTIVA, para que Mercado y el chat
     sigan mostrando lo mismo que antes. Si 'eco_pos' ya es idéntico a una cartera
     guardada (otro dispositivo ya migró y sincronizó), solo se activa esa. Si
     'eco_pos' está vacío no se crea nada.
   · 'eco_pos' queda como COPIA ESCRITA de la cartera activa (compatibilidad con
     /api/user-state y lectores viejos del servidor); después de migrar NUNCA se
     vuelve a leer como fuente.
   · Cada cambio: MKT.pos se actualiza al instante y se avisa con el evento
     'khipu:portfolio' (Mercado, la barra de saldo y Carteras se repintan).
   - Lo que llega de OTRO dispositivo (engine/sync.js -> `fromServer`) nunca se pierde (revisión 2026-10-15 b):
     a) un 'eco_pos' que no es la copia de ninguna cartera conocida (lo escribió una pestaña con el código viejo, o
        es de un dueño que todavía no migró, p. ej. al vincular un teléfono nuevo) se ADOPTA: se suma a «Mi cartera»
        (la que nació de 'eco_pos') o, si no existe, crea una. Las copias ya vistas ('kh_pos_seen', solo local) no
        se adoptan: así una copia que llega atrasada no duplica nada.
     b) si la «Mi cartera» que migró ESTE navegador choca por id con la que subió otro (contenido distinto: p. ej.
        un cambio hecho sin conexión), tras la bajada vuelve con otro id y queda activa.

   window.KhipuPfStore = { list, save, activeId, setActive, active, view, viewOf,
     applyView, migrate, refresh, afterSync, name, others, adopt, fromServer, … }
   ============================================================================ */
(function () {
  'use strict';
  var W = typeof window !== 'undefined' ? window : globalThis;
  var KEY = 'kh_portfolios', ACTIVE = 'kh_pf_active', MIRROR = 'eco_pos', FLAG = 'kh_pos_migrated', MAIN_ID = 'pf_main';
  var DEFAULT_CASH = 100000;
  var SEEN = 'kh_pos_seen', SEEN_MAX = 40;
  var _sig = null, _evT = null, _migratedNow = false, _migratedPf = null, _seen = null;

  function store() {
    try { return W.localStorage || (typeof localStorage !== 'undefined' ? localStorage : null); } catch (e) { return null; }
  }
  function get(k) { var s = store(); try { return s ? s.getItem(k) : null; } catch (e) { return null; } }
  function put(k, v) { var s = store(); if (!s) throw new Error('no_storage'); s.setItem(k, v); }   // puede lanzar (lleno)
  function lang() {
    try { return W.LANG || get('eco_lang') || 'es'; } catch (e) { return 'es'; }
  }
  function T(es, en) { return lang() === 'en' ? en : es; }
  function num(v) { var n = Number(v); return isFinite(n) ? n : NaN; }
  function near(a, b) { return Math.abs(a - b) <= 1e-9 * Math.max(1, Math.abs(a), Math.abs(b)); }

  /* ── lectura ──────────────────────────────────────────────────────────── */
  function list() {
    try {
      var raw = get(KEY);
      var arr = raw ? JSON.parse(raw) : [];
      if (!Array.isArray(arr)) arr = [];
      return arr.filter(function (p) { return p && p.id; }).map(function (p) {
        p.positions = Array.isArray(p.positions) ? p.positions : [];
        p.cash = isFinite(p.cash) ? p.cash : 0;
        p.startCash = isFinite(p.startCash) ? p.startCash : (p.cash || DEFAULT_CASH);
        return p;
      });
    } catch (e) { return []; }
  }
  function activeId() { return get(ACTIVE) || ''; }
  function active(lst) {
    lst = lst || list();
    if (!lst.length) return null;
    var id = activeId(), found = null;
    lst.forEach(function (p) { if (!found && p.id === id) found = p; });
    return found || lst[0];
  }
  // {nodeId: {sh, bp}} de una cartera (una fila repetida de la misma empresa se suma: acciones y precio promedio)
  function viewOf(pf) {
    var out = {};
    ((pf && pf.positions) || []).forEach(function (p) {
      if (!p || !p.nodeId) return;
      var sh = num(p.shares), bp = num(p.avgPrice);
      if (!(sh > 0)) return;
      if (!(bp >= 0)) bp = 0;
      var c = out[p.nodeId];
      if (c) { var t = c.sh + sh; c.bp = t > 0 ? (c.sh * c.bp + sh * bp) / t : 0; c.sh = t; }
      else out[p.nodeId] = { sh: sh, bp: bp };
    });
    return out;
  }
  function view() { return viewOf(active()); }
  function sameView(a, b) {
    var ka = Object.keys(a), kb = Object.keys(b);
    if (ka.length !== kb.length) return false;
    for (var i = 0; i < ka.length; i++) {
      var x = a[ka[i]], y = b[ka[i]];
      if (!y || Math.abs(x.sh - y.sh) > 1e-6 * Math.max(1, x.sh) || Math.abs(x.bp - y.bp) > 1e-6 * Math.max(1, x.bp)) return false;
    }
    return true;
  }
  // huella de una vista (ordenada; 6 cifras significativas) → para recordar las copias que este navegador ya vio
  function sigOf(v) {
    return Object.keys(v).sort().map(function (k) { return k + ':' + (+v[k].sh).toPrecision(6) + '@' + (+v[k].bp).toPrecision(6); }).join('|');
  }
  function seenSet() {
    if (_seen) return _seen;
    try { _seen = JSON.parse(get(SEEN) || '[]'); } catch (e) { _seen = []; }
    if (!Array.isArray(_seen)) _seen = [];
    return _seen;
  }
  function remember(views) {
    var s = seenSet(), add = false;
    views.forEach(function (v) {
      if (!Object.keys(v).length) return;
      var k = sigOf(v), i = s.indexOf(k);
      if (i >= 0 && i === s.length - 1) return;
      if (i >= 0) s.splice(i, 1);
      s.push(k); add = true;
    });
    if (!add) return;
    while (s.length > SEEN_MAX) s.shift();
    try { put(SEEN, JSON.stringify(s)); } catch (e) {}
  }
  // ¿la vista `big` ya tiene CADA posición de `small` con las mismas acciones y precio? (entonces nada se perdería)
  function covers(big, small) {
    var ks = Object.keys(small);
    for (var i = 0; i < ks.length; i++) {
      var x = small[ks[i]], y = big[ks[i]];
      if (!y || Math.abs(x.sh - y.sh) > 1e-6 * Math.max(1, x.sh) || Math.abs(x.bp - y.bp) > 1e-6 * Math.max(1, x.bp)) return false;
    }
    return true;
  }
  function name() { var pf = active(); return pf ? String(pf.name || '') : ''; }
  function others() {
    var lst = list(), pf = active(lst);
    return lst.filter(function (p) { return !pf || p.id !== pf.id; }).map(function (p) { return String(p.name || p.id); });
  }

  /* ── aviso a la app (MKT.pos al instante; el evento, agrupado) ─────────── */
  function notify() {
    if (_evT) return;
    _evT = setTimeout(function () {
      _evT = null;
      try {
        var pf = active();
        W.dispatchEvent(new W.CustomEvent('khipu:portfolio', { detail: { id: pf ? pf.id : '', name: pf ? pf.name : '' } }));
      } catch (e) {}
    }, 0);
  }
  // recalcula la vista, la pone en MKT.pos y escribe la COPIA en 'eco_pos' (solo si cambió)
  function refresh() {
    var lst = list(), v = viewOf(active(lst));
    try { remember(lst.map(viewOf)); } catch (e) {}
    try { if (W.MKT && typeof W.MKT === 'object') W.MKT.pos = v; } catch (e) {}
    if (get(FLAG)) {
      var m = JSON.stringify(v);
      if (get(MIRROR) !== m) { try { put(MIRROR, m); } catch (e) {} }
    }
    var sig = activeId() + '|' + (get(KEY) || '');
    if (sig !== _sig) { _sig = sig; notify(); }
    return v;
  }

  /* ── escritura ────────────────────────────────────────────────────────── */
  // Si el navegador no deja guardar (almacenamiento lleno / modo privado) se AVISA:
  // antes fallaba en silencio y la cartera "desaparecía" al recargar (2026-10-05).
  function save(lst) {
    var txt = JSON.stringify(lst || []);
    try { put(KEY, txt); }
    catch (e) {
      try {   // libera cachés desechables y reintenta una vez
        var s = store();
        Object.keys(s).forEach(function (k) { if (/^ai_analysis2_|^kh_chartcache$|^eco_quotes$/.test(k)) s.removeItem(k); });
        put(KEY, txt);
      } catch (e2) {
        var msg = T('⚠ No se pudo guardar la cartera en este navegador (almacenamiento lleno o modo privado).',
                    '⚠ Could not save the portfolio in this browser (storage full or private mode).');
        try {
          if (W.KhipuToast && W.KhipuToast.show) W.KhipuToast.show({ kind: 'error', title: msg });
          else if (typeof W.toast === 'function') W.toast(msg);
        } catch (e3) {}
        return false;
      }
    }
    refresh();
    return true;
  }
  function setActive(id) {
    id = String(id || '');
    if (id !== activeId()) { try { put(ACTIVE, id); } catch (e) {} }
    refresh();
  }
  function newMain(lst) {
    var ids = {}; lst.forEach(function (p) { ids[p.id] = 1; });
    var id = ids[MAIN_ID] ? MAIN_ID + '_' + Date.now().toString(36) : MAIN_ID;
    return { id: id, name: T('Mi cartera', 'My portfolio'), cash: 0, startCash: 0, positions: [], createdAt: Date.now(),
             origin: { kind: 'positions' } };
  }
  // Lo que Mercado (o el panel de trading sin bróker) dejó en MKT.pos → la cartera ACTIVA.
  // Sin cartera y con algo que guardar → se crea «Mi cartera».
  function applyView(map) {
    map = map || {};
    var want = {};
    Object.keys(map).forEach(function (id) {
      var p = map[id];
      if (!id || !p || typeof p !== 'object') return;
      var sh = num(p.sh != null ? p.sh : p.shares), bp = num(p.bp != null ? p.bp : p.avgPrice);
      if (sh > 0) want[id] = { sh: sh, bp: bp >= 0 ? bp : 0 };
    });
    var lst = list(), pf = active(lst), now = Date.now(), changed = false;
    if (!pf) {
      if (!Object.keys(want).length) { refresh(); return true; }
      pf = newMain(lst); lst.push(pf);
      try { put(ACTIVE, pf.id); } catch (e) {}
      changed = true;
    }
    var cur = viewOf(pf);
    Object.keys(cur).forEach(function (id) {          // quitadas
      if (want[id]) return;
      pf.startCash = Math.max(0, pf.startCash - cur[id].sh * cur[id].bp);
      pf.positions = pf.positions.filter(function (q) { return !q || q.nodeId !== id; });
      changed = true;
    });
    Object.keys(want).forEach(function (id) {         // nuevas o cambiadas
      var c = cur[id], w = want[id];
      if (c && near(c.sh, w.sh) && near(c.bp, w.bp)) return;
      pf.startCash = Math.max(0, pf.startCash + w.sh * w.bp - (c ? c.sh * c.bp : 0));
      var at = -1;
      pf.positions = pf.positions.filter(function (q, i) {
        if (!q || q.nodeId !== id) return true;
        if (at < 0) { at = i; return true; }
        return false;                                  // filas repetidas de la misma empresa → una sola
      });
      if (at >= 0) { var row = pf.positions[at]; row.shares = w.sh; row.avgPrice = w.bp; row.ts = now; }
      else pf.positions.push({ nodeId: id, shares: w.sh, avgPrice: w.bp, ts: now });
      changed = true;
    });
    if (!changed) { refresh(); return true; }
    return save(lst);
  }

  /* ── migración única de 'eco_pos' («Mis posiciones») ──────────────────── */
  // {nodeId:{sh,bp}} (formato de 'eco_pos') → filas de cartera + su costo
  function rowsOf(pos, now) {
    var rows = [], cost = 0;
    if (pos && typeof pos === 'object' && !Array.isArray(pos)) {
      Object.keys(pos).forEach(function (id) {
        var p = pos[id];
        if (!id || !p || typeof p !== 'object') return;
        var sh = num(p.sh), bp = num(p.bp);
        if (!(sh > 0)) return;
        if (!(bp >= 0)) bp = 0;
        rows.push({ nodeId: id, shares: sh, avgPrice: bp, ts: now });
        cost += sh * bp;
      });
    }
    return { rows: rows, cost: cost };
  }
  function migrate() {
    if (get(FLAG)) return { already: true };
    var pos = {};
    try { pos = JSON.parse(get(MIRROR) || '{}') || {}; } catch (e) { pos = {}; }
    var now = Date.now(), rc = rowsOf(pos, now), rows = rc.rows, cost = rc.cost;
    var res = { created: false, id: null };
    if (rows.length) {
      var lst = list(), mine = viewOf({ positions: rows }), same = null;
      lst.forEach(function (pf) { if (!same && sameView(viewOf(pf), mine)) same = pf; });
      try {
        if (same) res.id = same.id;                    // ya estaba guardada (otro dispositivo ya migró)
        else {
          var pf = newMain(lst);
          pf.startCash = cost; pf.positions = rows; pf.createdAt = now; pf.origin = { kind: 'eco_pos', migrated_at: new Date(now).toISOString() };
          lst.push(pf);
          put(KEY, JSON.stringify(lst));
          res.created = true; res.id = pf.id; _migratedNow = true;
          _migratedPf = JSON.parse(JSON.stringify(pf));   // por si la primera bajada la pisa (mismo id, otro contenido)
        }
        put(ACTIVE, res.id);
      } catch (e) {
        return { error: true };                        // sin espacio: 'eco_pos' sigue intacto y se reintenta la próxima vez
      }
    }
    try { put(FLAG, new Date(now).toISOString()); } catch (e) {}
    return res;
  }

  // ¿La «Mi cartera» que migró este navegador desapareció al mezclar con el servidor (otra con el MISMO id y otro
  // contenido ganó)? → vuelve con un id nuevo y queda activa (lo que Mercado mostraba antes sigue a la vista).
  function rescueMigrated() {
    if (!_migratedPf) return false;
    var lst = list(), mine = viewOf(_migratedPf), hit = null;
    lst.forEach(function (pf) { if (!hit && covers(viewOf(pf), mine)) hit = pf; });
    if (hit) return false;                             // ya está todo guardado (igual o con más cosas): nada que rescatar
    var pf = JSON.parse(JSON.stringify(_migratedPf)), ids = {};
    lst.forEach(function (p) { ids[p.id] = 1; });
    if (ids[pf.id]) pf.id = MAIN_ID + '_' + Date.now().toString(36) + Math.floor(Math.random() * 1296).toString(36);
    pf.createdAt = Date.now();                         // más nueva que la versión del servidor → sync.js la conserva y la sube
    lst.push(pf);
    try { put(ACTIVE, pf.id); } catch (e) {}
    _migratedPf = pf;
    return save(lst);
  }

  // 'eco_pos' que llegó del servidor y NO es la copia de ninguna cartera conocida → sus posiciones se guardan en
  // «Mi cartera» (se suman: una empresa que ya estaba toma las acciones y el precio que llegaron) o en una nueva.
  function adopt(map) {
    var now = Date.now(), rc = rowsOf(map, now);
    if (!rc.rows.length) return { noop: true };
    var lst = list(), mine = viewOf({ positions: rc.rows });
    for (var i = 0; i < lst.length; i++) if (covers(viewOf(lst[i]), mine)) return { noop: true, id: lst[i].id };
    if (seenSet().indexOf(sigOf(mine)) >= 0) return { noop: true, seen: true };   // copia que este navegador ya conocía
    var tgt = null;
    // «Mi cartera» = la que nació de 'eco_pos' (o de anotar en Mercado sin carteras): id 'pf_main' primero
    lst.forEach(function (p) { if (!tgt && p.id === MAIN_ID) tgt = p; });
    lst.forEach(function (p) { if (!tgt && p.origin && (p.origin.kind === 'eco_pos' || p.origin.kind === 'positions')) tgt = p; });
    var res = { adopted: rc.rows.length, created: false, id: null };
    if (tgt) {
      var cur = viewOf(tgt);
      rc.rows.forEach(function (r) {
        var c = cur[r.nodeId];
        if (c && near(c.sh, r.shares) && near(c.bp, r.avgPrice)) return;
        tgt.startCash = Math.max(0, tgt.startCash + r.shares * r.avgPrice - (c ? c.sh * c.bp : 0));
        tgt.positions = tgt.positions.filter(function (q) { return !q || q.nodeId !== r.nodeId; });
        tgt.positions.push(r);
      });
      res.id = tgt.id;
    } else {
      var pf = newMain(lst), had = lst.length;
      pf.startCash = rc.cost; pf.positions = rc.rows; pf.createdAt = now;
      pf.origin = { kind: 'eco_pos', adopted_at: new Date(now).toISOString() };
      lst.push(pf);
      res.created = true; res.id = pf.id;
      if (!had) { try { put(ACTIVE, pf.id); } catch (e) {} }   // sin carteras: la nueva es la activa
    }
    remember([mine]);
    if (!save(lst)) return { error: true };
    return res;
  }

  // engine/sync.js aplicó valores del servidor (keys = claves que cambiaron; eco = 'eco_pos' tal como llegó):
  // primero se rescata/adopta lo que de otro modo se perdería y RECIÉN después se reescribe la copia 'eco_pos'.
  function fromServer(keys, eco) {
    keys = keys || [];
    try { rescueMigrated(); } catch (e) {}
    if (keys.indexOf(MIRROR) >= 0) {
      var m = eco;
      if (typeof m === 'string') { try { m = JSON.parse(m); } catch (e) { m = null; } }
      try { adopt(m); } catch (e) {}
    }
    return refresh();
  }

  // engine/sync.js, tras su primera bajada del servidor: si esta carga creó «Mi cartera», se vuelve a guardar la
  // lista (ya mezclada con la del servidor) para que suba; antes de sync.js nada marcaba la escritura como nueva.
  function afterSync() {
    var rescued = false;
    try { rescued = rescueMigrated(); } catch (e) {}
    _migratedPf = null;
    if (_migratedNow) {
      _migratedNow = false;
      var lst = list();
      if (lst.length && !rescued) { save(lst); return; }
    }
    refresh();
  }

  try {
    W.addEventListener('storage', function (e) {      // otra pestaña cambió las carteras o la activa
      if (!e || e.key === KEY || e.key === ACTIVE || e.key === null) refresh();
    });
  } catch (e) {}

  W.KhipuPfStore = {
    KEY: KEY, ACTIVE: ACTIVE, MIRROR: MIRROR, FLAG: FLAG, MAIN_ID: MAIN_ID, DEFAULT_CASH: DEFAULT_CASH,
    list: list, save: save, activeId: activeId, setActive: setActive, active: active, view: view, viewOf: viewOf,
    applyView: applyView, migrate: migrate, refresh: refresh, reload: refresh, afterSync: afterSync, name: name, others: others,
    adopt: adopt, fromServer: fromServer
  };
  migrate();
  refresh();
})();
