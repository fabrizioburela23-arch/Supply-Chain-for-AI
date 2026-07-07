/* ============================================================================
   engine/statematrix.js — MOTOR DE ESTADOS REACTIVO (client-side, 60 fps)
   El "sistema nervioso" de Khipus: cada empresa tiene un VECTOR DE ESTADO
   (signos vitales); las MATRICES DE ACOPLAMIENTO (una por tipo de relación)
   son su entorno; un KERNEL reactivo re-adapta los valores cuando algo cambia.

   Diseño (2026-07, con Fabrizio):
   - PROPAGAN por la red: salud, riesgo, momentum.
   - DERIVAN por nodo (baratos): valoración, crecimiento, señal, potencial.
   - Corre en el navegador con adjacency lists dispersas (99,4% ceros → se
     saltan) → una simulación completa ≈ 50.000 operaciones ≈ microsegundos.
   - Hiperaristas (factores externos) suben la fragilidad de sus miembros.

   Núcleo PURO (KhipuStateCore) testeable en Node sin DOM; glue de navegador
   (window.KhipuState) que lo alimenta desde window.NODES/LINKS/computeNRS.
   Mismos pesos de criticidad que matrix/engine.py (fab≈supply > invest).
   ============================================================================ */
(function () {
  'use strict';

  // Criticidad de cada tipo de relación en la transmisión de daño (idéntico a
  // matrix/engine.py DEFAULT_REL_WEIGHTS — el cliente y el server coinciden).
  var REL_W = {
    supply: 1.0, fab: 1.0, cloud: 0.9, license: 0.8, ppa: 0.7,
    deploy: 0.4, partner: 0.3, owns: 0.6, invest: 0.25,
  };
  var clamp01 = function (v) { return v < 0 ? 0 : v > 1 ? 1 : v; };

  // ── NÚCLEO PURO ────────────────────────────────────────────────────────────
  // opts: { nodes:[{id,...}], links:[{source,target,w,type}], baselineFn(node)->state }
  function KhipuStateCore(opts) {
    var nodes = opts.nodes, links = opts.links;
    var idx = {}, ids = [];
    nodes.forEach(function (n, i) { idx[n.id] = i; ids.push(n.id); });
    var N = ids.length;

    // Dependencia entrante normalizada por TIPO (columna j suma 1 dentro del
    // tipo), combinada por criticidad → transmisión T[j] = lista de {i, w}.
    // Un proveedor ÚNICO en su tipo transmite ~todo; 1 de N, poco.
    var incoming = [];       // incoming[j] = [{i, w}]
    for (var k = 0; k < N; k++) incoming.push([]);
    var byType = {};         // type -> [{i,j,w}]
    links.forEach(function (l) {
      var s = (typeof l.source === 'object' && l.source) ? l.source.id : l.source;
      var t = (typeof l.target === 'object' && l.target) ? l.target.id : l.target;
      var i = idx[s], j = idx[t];
      if (i == null || j == null || i === j) return;
      var type = l.type || 'supply';
      (byType[type] = byType[type] || []).push({ i: i, j: j, w: l.w || 2, type: type });
    });
    Object.keys(byType).forEach(function (type) {
      var edges = byType[type];
      var colSum = new Float64Array(N);
      edges.forEach(function (e) { colSum[e.j] += e.w; });
      var crit = REL_W[type] != null ? REL_W[type] : 0.5;
      edges.forEach(function (e) {
        var norm = e.w / (colSum[e.j] || 1) * crit;
        incoming[e.j].push({ i: e.i, w: norm });
      });
    });

    // estado base por nodo (vector de signos vitales)
    var base = nodes.map(function (n) { return opts.baselineFn(n); });

    this.idx = idx; this.ids = ids; this.N = N;
    this.incoming = incoming; this.base = base; this.nodes = nodes;
  }

  // Propaga un shock. shocks: {id: {salud?, riesgo?...}} valores IMPUESTOS.
  // factors: [{members:{id:coef}, severity}] → fragilidad. Devuelve
  // {state: Map(id->vector), impact: Map(id->0..100)} tras `iters` iteraciones.
  KhipuStateCore.prototype.simulate = function (shocks, factors, iters, damping) {
    iters = iters || 8; damping = damping == null ? 0.6 : damping;
    var N = this.N, incoming = this.incoming, base = this.base, ids = this.ids, idx = this.idx;

    // fragilidad por hiperaristas
    var frag = new Float64Array(N); for (var f = 0; f < N; f++) frag[f] = 1;
    (factors || []).forEach(function (fac) {
      var sev = (fac.severity || 5) / 5;
      Object.keys(fac.members || {}).forEach(function (id) {
        if (idx[id] != null) frag[idx[id]] += (fac.members[id] || 0) * sev;
      });
    });

    // "daño" a la salud propagado (0 = intacto, 1 = colapso total)
    var dmg = new Float64Array(N);
    var forced = {};
    Object.keys(shocks || {}).forEach(function (id) {
      if (idx[id] != null) { var d = 1 - clamp01(shocks[id].salud != null ? shocks[id].salud : 0); dmg[idx[id]] = d; forced[idx[id]] = d; }
    });

    var cur = dmg.slice();
    for (var it = 0; it < iters; it++) {
      var nxt = new Float64Array(N);
      for (var j = 0; j < N; j++) {
        if (forced[j] != null) { nxt[j] = forced[j]; continue; }
        var acc = 0, inc = incoming[j];
        for (var e = 0; e < inc.length; e++) acc += inc[e].w * cur[inc[e].i];
        nxt[j] = clamp01(damping * acc * frag[j]);
      }
      cur = nxt;
    }

    // materializar vectores de estado finales
    var state = new Map(), impact = new Map();
    for (var n = 0; n < N; n++) {
      var b = base[n], d2 = cur[n];
      if (d2 <= 0.001 && forced[n] == null) { state.set(ids[n], b); continue; }
      var salud = clamp01(b.salud - d2);
      var riesgo = clamp01(b.riesgo + d2 * 0.7);
      var momentum = clamp01(b.momentum - d2 * 0.8);
      var st = {
        salud: salud, riesgo: riesgo, momentum: momentum,
        valor: b.valor, crecim: b.crecim,
      };
      st.senal = _senal(st);              // -1..1 (venta..compra)
      st.potencial = _potencial(st);      // -1..1 (bajista..alcista)
      state.set(ids[n], st);
      impact.set(ids[n], Math.round(d2 * 100));
    }
    return { state: state, impact: impact };
  };

  // señales derivadas (baratas, por nodo)
  function _senal(s) {
    // compra si: sana, barata, con momentum y crecimiento, bajo riesgo
    var v = 0.30 * (s.momentum - 0.5) + 0.25 * (0.5 - (s.valor - 0.5))
          + 0.20 * (s.crecim - 0.5) + 0.15 * (s.salud - 0.5) - 0.25 * (s.riesgo - 0.5);
    return Math.max(-1, Math.min(1, v * 2));
  }
  function _potencial(s) {
    return Math.max(-1, Math.min(1, (s.crecim - 0.5) * 1.4 + (0.5 - s.riesgo) * 0.8 + (s.momentum - 0.5) * 0.6));
  }

  // ── GLUE DE NAVEGADOR ──────────────────────────────────────────────────────
  function browserBaseline(n) {
    var nrs = (typeof window.computeNRS === 'function') ? window.computeNRS(n.id) : 50;
    var mkt = n.mkt && window.MKT && window.MKT.quotes ? window.MKT.quotes[n.mkt] : null;
    var pct = mkt && mkt.prev ? (mkt.close - mkt.prev) / mkt.prev : 0;
    var g = (n.growth || '').toLowerCase();
    var crecim = g.indexOf('🟢') >= 0 ? 0.8 : g.indexOf('🟡') >= 0 ? 0.5 : g.indexOf('🔴') >= 0 ? 0.25 : 0.5;
    var margin = n.margin != null ? n.margin : 0.15;
    return {
      salud: 1.0,
      riesgo: clamp01(nrs / 100),
      momentum: clamp01(0.5 + pct * 4),          // ±12,5% → 0..1
      valor: clamp01(1 - Math.min(1, margin / 0.5)),  // margen alto = "barata" en calidad
      crecim: crecim,
    };
  }

  var _core = null;
  if (typeof window !== 'undefined')
  window.KhipuState = {
    // (re)construye el motor desde el grafo cargado
    build: function () {
      if (!window.NODES || !window.LINKS) return null;
      _core = new KhipuStateCore({
        nodes: window.NODES, links: window.LINKS, baselineFn: browserBaseline,
      });
      return _core;
    },
    core: function () { return _core || this.build(); },
    baseline: function (id) { var c = this.core(); var i = c && c.idx[id]; return (i != null) ? c.base[i] : null; },
    // simula: shocks={id:{salud}}, factors=[{members,severity}]
    simulate: function (shocks, factors, iters, damping) {
      var c = this.core(); if (!c) return { state: new Map(), impact: new Map() };
      return c.simulate(shocks, factors, iters, damping);
    },
    REL_W: REL_W,
  };

  // exportar el núcleo para tests headless (Node)
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { KhipuStateCore: KhipuStateCore };
  }
})();
