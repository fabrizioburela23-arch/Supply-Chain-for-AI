/* ============================================================================
   engine/live.js — MODO EN VIVO (Etapa D, 2026-07)
   La app se mantiene relevante SOLA:
   1) Latido de insights: cuando llegan precios nuevos, invalida el NRS y
      re-dibuja los insights si la pestaña Análisis está visible.
   2) Ciclo de agentes: cada 10 min dispara POST /api/ontology/agents/cycle —
      los 5 agentes del servidor (incl. 📡 RadarEmpresas) corren y las
      propuestas seguras se aplican solas (auditadas, reversibles).
      Sin DATABASE_URL el endpoint responde 503 y esto calla — patrón opcional.
   3) Indicador ● EN VIVO en el pie + toast cuando el radar aplica cambios.
   ============================================================================ */
(function () {
  'use strict';

  var TICK_MS = 90 * 1000;        // latido de insights (barato, 100% cliente)
  var CYCLE_MS = 10 * 60 * 1000;  // ciclo de agentes del servidor
  var lastSig = '';

  function quotesSig() {
    try {
      var q = (window.MKT || {}).quotes || {};
      var keys = Object.keys(q);
      var s = keys.length + ':';
      for (var i = 0; i < keys.length; i += 7) {
        var v = q[keys[i]];
        if (v && v.close != null) s += v.close + ',';
      }
      return s;
    } catch (e) { return ''; }
  }

  function pulse() {
    var d = document.getElementById('live-dot');
    if (!d) return;
    d.style.opacity = '1';
    setTimeout(function () { d.style.opacity = '.35'; }, 700);
  }

  function tick() {
    if (document.hidden) return;
    var sig = quotesSig();
    if (!sig || sig === lastSig) return;
    lastSig = sig;
    if (window._invalidateNRS) window._invalidateNRS();
    var panel = document.getElementById('analysis-panel');
    if (panel && panel.offsetParent !== null && window.renderKhipuInsights) {
      try { window.renderKhipuInsights(); } catch (e) {}
    }
    pulse();
  }

  var lastSeenRun = 0;   // no re-notificar la misma corrida dos veces

  function cycle() {
    if (document.hidden) return;
    // el server corre el ciclo en background; esta llamada arranca una corrida
    // si toca y devuelve el resultado de la ÚLTIMA corrida terminada
    fetch((window.BASE || '') + '/api/ontology/agents/cycle', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ actor: 'live' }),
    }).then(function (r) { return r.ok ? r.json() : null; }).then(function (d) {
      if (!d || d.status !== 'ok') return;
      var last = d.last;
      if (!last || last.status !== 'ok' || !d.last_at || d.last_at <= lastSeenRun) { pulse(); return; }
      lastSeenRun = d.last_at;
      var applied = (last.auto_applied || []).length;
      if (applied > 0) {
        if (typeof toast === 'function') {
          var first = last.auto_applied[0];
          toast('📡 Radar: ' + applied + ' cambio(s) al grafo — ' + (first.explanation || first.action));
        }
        var b = document.getElementById('live-badge');
        if (b) { b.textContent = '📡 +' + applied; b.style.display = 'inline'; }
      }
      (last.alerts_fired || []).forEach(function (a) {
        if (typeof toast === 'function') toast('🔔 Alerta: ' + (a.detail || JSON.stringify(a.rule)));
      });
      pulse();
    }).catch(function () {});
  }

  function mountBadge() {
    if (document.getElementById('live-dot')) return;
    var foot = document.getElementById('footer-nodecount');
    if (!foot || !foot.parentNode) return;
    var wrap = document.createElement('span');
    wrap.style.cssText = 'display:inline-flex;align-items:center;gap:5px;margin-left:10px;white-space:nowrap';
    wrap.innerHTML =
      '<span id="live-dot" title="Modo en vivo: insights y radar automáticos" ' +
        'style="width:7px;height:7px;border-radius:50%;background:#2BE38B;box-shadow:0 0 6px #2BE38B;opacity:.35;transition:opacity .3s"></span>' +
      '<span style="font-size:9px;letter-spacing:.08em;color:#7C87A3">EN VIVO</span>' +
      '<span id="live-badge" style="display:none;font-size:9px;color:#2BE38B"></span>';
    foot.parentNode.insertBefore(wrap, foot.nextSibling);
  }

  setInterval(tick, TICK_MS);
  setInterval(cycle, CYCLE_MS);
  setTimeout(cycle, 25 * 1000);   // primer ciclo a los 25s de abrir la app
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mountBadge);
  else mountBadge();

  window.KhipuLive = { tick: tick, cycle: cycle };
})();
