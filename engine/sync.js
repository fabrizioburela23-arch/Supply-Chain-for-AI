/* ============================================================================
   engine/sync.js — SINCRONIZACIÓN ENTRE DISPOSITIVOS (carteras, perfil, posiciones)

   Pedido implícito (2026-10-03): lo que armas en la PC (carteras simuladas, tu
   perfil de inversionista, tus posiciones de Mercado) también en el teléfono, y
   que los reportes automáticos usen tu cartera de HOY.
   · Claves: kh_portfolios, kh_pf_active, kh_investor_profile, eco_pos.
   · Servidor: GET/PUT /api/user-state (core/portfolio_reports_api.py), por dueño
     = llave aleatoria del navegador (localStorage kh_owner_key → X-Khipu-Owner).
   · Último que escribe gana (marca de tiempo por clave en kh_sync_meta).
   · Vincular otro dispositivo: el código (la llave) se copia y se pega allá.
   window.KhipuSync = { code(), link(code), pull(force) }
   ============================================================================ */
(function () {
  'use strict';
  var KEYS = ['kh_portfolios', 'kh_pf_active', 'kh_investor_profile', 'eco_pos'];
  var META = 'kh_sync_meta';
  var applying = false, timers = {}, available = true;

  function ls(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function meta() { try { return JSON.parse(ls(META) || '{}') || {}; } catch (e) { return {}; } }
  function setMeta(m) { applying = true; lsSet(META, JSON.stringify(m)); applying = false; }
  function owner() {
    var k = ls('kh_owner_key');
    if (!k || k.length < 16) {
      var a = new Uint8Array(16);
      if (window.crypto && window.crypto.getRandomValues) window.crypto.getRandomValues(a); else for (var i = 0; i < 16; i++) a[i] = Math.random() * 256;
      k = Array.prototype.map.call(a, function (b) { return ('0' + b.toString(16)).slice(-2); }).join('');
      lsSet('kh_owner_key', k);
    }
    return k;
  }
  function api(method, body) {
    return fetch((window.BASE || '') + '/api/user-state', { method: method,
      headers: { 'Content-Type': 'application/json', 'X-Khipu-Owner': owner() }, body: body ? JSON.stringify(body) : undefined })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { j._status = r.status; return j; }); });
  }
  function parse(raw) { try { return raw == null ? null : JSON.parse(raw); } catch (e) { return raw; } }

  function push(key) {
    if (!available) return;
    var m = meta(), ts = m[key] || new Date().toISOString();
    api('PUT', { key: key, value: parse(ls(key)), updated_at: ts }).then(function (d) {
      if (d._status === 409 && d.updated_at) apply(key, d.value, d.updated_at);   // otro dispositivo escribió después
    }).catch(function () {});
  }
  // cada escritura local de una clave sincronizada → se sube (con 1.5 s de espera)
  var orig = Storage.prototype.setItem;
  Storage.prototype.setItem = function (k, v) {
    orig.call(this, k, v);
    try {
      if (!applying && this === window.localStorage && KEYS.indexOf(k) >= 0) {
        var m = meta(); m[k] = new Date().toISOString(); setMeta(m);
        clearTimeout(timers[k]); timers[k] = setTimeout(function () { push(k); }, 1500);
      }
    } catch (e) {}
  };

  function apply(key, value, ts) {
    applying = true;
    try {
      if (value === null || value === undefined) localStorage.removeItem(key);
      else localStorage.setItem(key, typeof value === 'string' && key === 'kh_pf_active' ? value : JSON.stringify(value));
    } catch (e) {}
    applying = false;
    var m = meta(); m[key] = ts; setMeta(m);
  }
  function refreshUI(keys) {
    try {
      if (keys.indexOf('eco_pos') >= 0 && window.MKT) { window.MKT.pos = JSON.parse(ls('eco_pos') || '{}'); if (typeof window.renderMarket === 'function') window.renderMarket(); }
    } catch (e) {}
    try { if ((keys.indexOf('kh_portfolios') >= 0 || keys.indexOf('kh_pf_active') >= 0) && window.KhipuPortfolios && window.KhipuPortfolios.refresh) window.KhipuPortfolios.refresh(); } catch (e) {}
  }

  function pull(serverWins) {
    return api('GET').then(function (d) {
      if (d.available === false || d._status >= 400) { available = d._status !== 401 && d.available !== false; return 0; }
      var st = d.state || {}, m = meta(), changed = [];
      KEYS.forEach(function (k) {
        var srv = st[k], localTs = m[k];
        if (srv && (serverWins || !localTs || srv.updated_at > localTs || ls(k) == null)) {
          if (JSON.stringify(parse(ls(k))) !== JSON.stringify(srv.value)) changed.push(k);
          apply(k, srv.value, srv.updated_at);
        } else if (ls(k) != null && (!srv || (localTs && localTs > srv.updated_at))) {
          if (!localTs) { m[k] = new Date().toISOString(); setMeta(m); }
          push(k);
        }
      });
      if (changed.length) refreshUI(changed);
      return changed.length;
    }).catch(function () { return 0; });
  }

  function code() { return owner().replace(/(.{4})/g, '$1-').replace(/-$/, '').toUpperCase(); }
  function link(c) {
    var k = String(c || '').toLowerCase().replace(/[^0-9a-f]/g, '');
    if (k.length < 16) return Promise.resolve({ ok: false });
    lsSet('kh_owner_key', k);
    setMeta({});
    return pull(true).then(function (n) { return { ok: true, changed: n }; });
  }

  window.KhipuSync = { code: code, link: link, pull: pull, keys: KEYS };
  setTimeout(function () { owner(); pull(false); }, 2500);
  setInterval(function () { if (!document.hidden) pull(false); }, 120000);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) pull(false); });
})();
