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

  // ── Estado en bolsa VERIFICADO (nodes/listing_status.js) ────────────────
  // El catálogo se escribió en una fecha y envejece: SpaceX figuraba como
  // "privada" meses después de salir a bolsa (SPCX, jun-2026). Esta capa
  // pisa SOLO lo que se verificó con fuente, y deja el rastro en n.listing
  // {status, note_es, note_en, source_url, as_of…} para que la UI lo muestre.
  // Ticker "de relleno" en privadas (FIGURE, GROQ, PERPLEXITY…): no es un
  // símbolo de bolsa, y con él la app las trataba como cotizadas (Dossier de
  // cotizada vacío, pedía precios que no existen). Una pre-IPO sin estado
  // verificado "public" NO cotiza: mkt = null (el texto de n.ticker se queda).
  NODES.forEach(function (n) {
    if (n && n.preipo && n.mkt) n.mkt = null;
  });

  const LS = env.LISTING_STATUS;
  if (LS && LS.entries) {
    Object.keys(LS.entries).forEach(function (id) {
      const n = NODE_BY_ID[resolveId(id)];
      const e = LS.entries[id];
      if (!n || !e) return;
      n.listing = Object.assign({ as_of: LS.as_of }, e);
      // El texto de crecimiento se escribió cuando era privada ("⭐ PRE-IPO
      // ~$350B…") y la ficha lo muestra tal cual: sin esto la empresa seguía
      // DICIENDO pre-IPO aunque la marca ya estuviera apagada.
      const PRE = /⭐?\s*PRE-?IPO[^;·]*[;·]?\s*/i;
      const hadPre = PRE.test(n.growth || '') || PRE.test(n.growth_en || '');
      if (e.status === 'public' && e.ticker) {
        n.mkt = e.ticker;
        n.ticker = e.ticker + (e.exchange ? ' · ' + e.exchange : '');
        n.preipo = false;
        if (hadPre) {
          const since = e.listed_since ? ' ' + e.listed_since : '';
          const rest = (n.growth || '').replace(PRE, '').trim();
          const restEn = (n.growth_en || n.growth || '').replace(PRE, '').trim();
          n.growth = '🟢 En bolsa (' + e.ticker + ')' + (since ? ' desde' + since : '') + (rest ? ' · ' + rest : '');
          n.growth_en = '🟢 Listed (' + e.ticker + ')' + (since ? ' since' + since : '') + (restEn ? ' · ' + restEn : '');
        }
      } else if (e.status === 'acquired' || e.status === 'merged' || e.status === 'subsidiary') {
        // ya no cotiza por sí misma; la exposición bursátil es la del dueño
        n.mkt = null;
        n.preipo = false;
        n.ticker = (e.parent || '') + (e.parent_ticker ? ' (' + e.parent_ticker + ')' : '');
        if (hadPre && e.note_es) { n.growth = '🔄 ' + e.note_es; n.growth_en = '🔄 ' + (e.note_en || e.note_es); }
      } else if (e.status === 'defunct') {
        n.mkt = null;
        n.preipo = false;
      }
    });
  }

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
