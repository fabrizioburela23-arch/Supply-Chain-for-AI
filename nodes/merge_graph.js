/* ============================================================================
   nodes/merge_graph.js — EL merge del catálogo (única implementación)
   Usado por app.html (navegador) Y por scripts/export_graph_v0.js (Node vm).
   Antes esta lógica existía 3 veces (app.html inline, exportador por líneas
   hardcodeadas y script de migración) y divergía en silencio.

   Reglas (Etapa 2, 2026-07):
   - NODE_ID_ALIAS es la tabla canónica de entidades: un id alias es un
     duplicado; el canónico ABSORBE sus campos faltantes, sus links se
     redirigen y NODE_BY_ID conserva la clave alias → nodo canónico.
   - Links canónicos: source PROVEE a target. Dedupe por (s,t,type):
     mayor peso + descripción más larga.
   ============================================================================ */

function buildKhipusGraph(env) {
  const NODES = env.NODES;               // array seed — se MUTA en sitio
  const NODE_BY_ID = env.NODE_BY_ID;     // mapa pre-poblado con el seed
  const ALIAS = env.NODE_ID_ALIAS || {};
  const RAW = env.RAW_LINKS || [];
  const expansions = env.expansions || [];
  const warn = env.warn || function () {};

  function resolveId(id) {
    let cur = id, hops = 0;
    while (ALIAS[cur] !== undefined && hops++ < 5) cur = ALIAS[cur];
    return cur;
  }

  function absorbNode(n) {
    const cid = resolveId(n.id);
    const existing = NODE_BY_ID[cid];
    if (existing) {
      if (existing !== n) {
        for (const k in n) {
          if (k === 'id') continue;
          if (existing[k] == null || existing[k] === '') existing[k] = n[k];
        }
        if (n.id !== cid) NODE_BY_ID[n.id] = existing;  // alias → nodo canónico
      }
      return;
    }
    n.id = cid;
    NODE_BY_ID[cid] = n;
    if (NODES.indexOf(n) === -1) NODES.push(n);
  }

  // el seed también pasa por resolución (por si contiene ids alias)
  NODES.slice().forEach(function (n) {
    const cid = resolveId(n.id);
    if (cid !== n.id && NODE_BY_ID[cid]) {
      const idx = NODES.indexOf(n);
      if (idx >= 0) NODES.splice(idx, 1);
      absorbNode(n);
    } else { NODE_BY_ID[n.id] = n; }
  });
  expansions.forEach(function (arr) { if (arr) arr.forEach(absorbNode); });

  // links de expansión → RAW (acepta [s,t,w,rel,type] y {s,t,w,rel,type})
  (env.linkArrays || []).forEach(function (arr) {
    if (!arr) return;
    arr.forEach(function (l) {
      if (Array.isArray(l)) RAW.push([l[0], l[1], l[2] || 2, l[3] || '', l[4] || 'supply']);
      else RAW.push([l.s, l.t, l.w || 2, l.rel || '', l.type || 'supply']);
    });
  });

  // tubería final: resolver alias → filtrar → dedupe (s,t,type)
  const seen = new Map();
  RAW.forEach(function (row) {
    const s = resolveId(row[0]), t = resolveId(row[1]);
    const w = row[2], rel = row[3] || '', type = row[4] || 'supply';
    if (s === t || !(w > 0)) return;
    if (!NODE_BY_ID[s] || !NODE_BY_ID[t]) { warn('Link descartado por id inexistente: ' + row[0] + ' → ' + row[1]); return; }
    const sid = NODE_BY_ID[s].id, tid = NODE_BY_ID[t].id;
    if (sid === tid) return;
    const key = sid + '→' + tid + '·' + type;
    const prev = seen.get(key);
    if (prev) {
      if ((w || 2) > prev.w) prev.w = w || 2;
      if (rel.length > (prev.rel || '').length) prev.rel = rel;
    } else {
      seen.set(key, { source: sid, target: tid, w: w || 2, rel: rel, type: type });
    }
  });

  return { LINKS: Array.from(seen.values()), resolveId: resolveId };
}

if (typeof window !== 'undefined') window.buildKhipusGraph = buildKhipusGraph;
if (typeof module !== 'undefined' && module.exports) module.exports = { buildKhipusGraph };
