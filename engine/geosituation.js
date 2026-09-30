// engine/geosituation.js — (RETIRADO 2026-09-30) Sala de Situación 2D.
// El mapa 2D de eventos ("muy grande y da poca info", feedback de Fabrizio) se
// FUSIONÓ en el World Monitor 3D (engine/worldmonitor.js): chokepoints con score
// vivo + "Simular cierre" (POST /api/matrix/impact), inestabilidad por país,
// fabs críticas, arcos de suministro y empresas viven ahora en el globo, con
// eventos en vivo encima. Este archivo queda como alias fino para que ningún
// llamador viejo (ni la caché del service worker) rompa: NO recrear el mapa 2D.
(function () {
  'use strict';
  window.GeoSituation = {
    init: function () { if (window.KhipuWorld) window.KhipuWorld.mount(); },
    get state() { return window.KhipuWorld ? window.KhipuWorld.state : null; },
  };
})();
