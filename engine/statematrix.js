/* ============================================================================
   engine/statematrix.js — ESTADO VISUAL de la simulación (solo animación; SIN matemática de contagio)
   Paso 13 de INFRA_OPERATIVA (2026-10-13): el navegador ya NO propaga choques. Aquí había un segundo
   motor (máximo por "eslabón más débil", 8 iteraciones, sin umbral ni tope de fragilidad) que daba otros
   números que el servidor para la misma caída (PROP-01/02/12, G5-03). Ahora TODA cifra de impacto la da
   el kernel único del servidor por /api/hot/* (engine/hotclient.js, window.KhipuHot). Este archivo
   solo convierte ese resultado en ESTADO VISUAL:
     · frames(res)   la "película" de la cascada por SALTO (el `hop` que manda el servidor), para animar el mapa
     · baseline(id)  signos vitales de presentación (riesgo = NRS, momentum = precio del día) que usa el Comparador
     · idsInSector / idsInCountry   ayudantes de selección de objetivos (livesim)
   Una prueba estática (tests/test_no_client_engine.py) exige que aquí no vuelva un bucle de propagación.
   ============================================================================ */
(function () {
  'use strict';
  var clamp01 = function (v) { return v < 0 ? 0 : v > 1 ? 1 : v; };

  // Película por salto: frame k = semillas + víctimas con hop ≤ k (valores del SERVIDOR, sin recalcular).
  // res = KhipuHot.simulate(...) → {targets, severity, victims:[{id,pct,hop}], impact: Map}
  function frames(res) {
    if (!res || !res.ok) return [];
    var seeds = res.targets || [], sev = res.severity == null ? 100 : res.severity;
    var victims = (res.victims || []).slice();
    var maxHop = 0;
    victims.forEach(function (v) { if ((v.hop || 0) > maxHop) maxHop = v.hop || 0; });
    var out = [];
    for (var k = 0; k <= maxHop; k++) {
      var f = new Map();
      seeds.forEach(function (id) { f.set(id, sev); });
      victims.forEach(function (v) { if ((v.hop || 0) <= k && !f.has(v.id)) f.set(v.id, v.pct); });
      out.push(f);
    }
    if (!out.length) { var f0 = new Map(); seeds.forEach(function (id) { f0.set(id, sev); }); out.push(f0); }
    return out;
  }

  // signos vitales de PRESENTACIÓN (no propagan nada): el Comparador los dibuja como barras
  function browserBaseline(n) {
    var nrs = (typeof window.computeNRS === 'function') ? window.computeNRS(n.id) : 50;
    var mkt = n.mkt && window.MKT && window.MKT.quotes ? window.MKT.quotes[n.mkt] : null;
    var px = mkt ? (typeof window.quotePx === 'function' ? window.quotePx(mkt) : mkt.close) : null;
    var pct = mkt && mkt.prev && px ? (px - mkt.prev) / mkt.prev : 0;
    var g = (n.growth || '').toLowerCase();
    var crecim = g.indexOf('🟢') >= 0 ? 0.8 : g.indexOf('🟡') >= 0 ? 0.5 : g.indexOf('🔴') >= 0 ? 0.25 : 0.5;
    var margin = n.margin != null ? n.margin : 0.15;
    return {
      salud: 1.0,
      riesgo: clamp01(nrs / 100),
      momentum: clamp01(0.5 + pct * 4),               // ±12,5 % → 0..1
      valor: clamp01(1 - Math.min(1, margin / 0.5)),  // margen alto = "barata" en calidad
      crecim: crecim,
    };
  }

  if (typeof window !== 'undefined')
  window.KhipuState = {
    frames: frames,
    baseline: function (id) {
      var n = window.NODE_BY_ID ? window.NODE_BY_ID[id] : null;
      return n ? browserBaseline(n) : null;
    },
    idsInSector: function (sec) {
      return (window.NODES || []).filter(function (n) {
        return ((window.CAT_TO_SECTOR || {})[n.cat] || 'cloud_ia') === sec;
      }).map(function (n) { return n.id; });
    },
    idsInCountry: function (country) {
      return (window.NODES || []).filter(function (n) { return n.country === country; }).map(function (n) { return n.id; });
    },
  };

  // exportar para tests headless (Node)
  if (typeof module !== 'undefined' && module.exports) module.exports = { frames: frames };
})();
