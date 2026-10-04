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
   - Confianza por link (G4c, misión de reparación 2026-10-04): cada link
     sale con `conf` (0-1) y `verified`. Si la fila del catálogo trae un 6.º
     elemento objeto {conf, verified, since} se respeta; si no, se deriva del
     texto `rel`: "no verificado" / "no revisado" / "posible(mente)" /
     "sin confirmar" → conf 0.3, verified false (22+ links decían eso y
     pesaban igual que los verificados en NRS y matrices). La MISMA regex
     vive en mcp_server/tools.py (_link_trust) como respaldo para snapshots
     viejos sin estos campos.
   ============================================================================ */

var UNVERIFIED_RX = /no verificad|no revisad|\bposible(mente)?|sin confirmar/i;
var UNVERIFIED_QUALIFIER_RX = /(%|porcentaje|cifra|monto|participaci[oó]n)[^.;]{0,30}?no verificad[oa]s?|posibles? duplicad[oa]s?/gi;
var UNVERIFIED_CONF = 0.3;

// → {conf, verified, explicit}. `meta` = 6.º elemento de la fila (opcional).
function linkTrust(rel, meta) {
  if (meta && typeof meta === 'object' && (meta.conf != null || meta.verified != null)) {
    var conf = meta.conf != null ? +meta.conf : NaN;
    conf = isFinite(conf) ? Math.max(0, Math.min(1, conf)) : null;
    var ver = meta.verified;
    if (ver == null) ver = (conf == null || conf >= 1);
    if (conf == null) conf = ver ? 1 : UNVERIFIED_CONF;
    return { conf: conf, verified: !!ver, explicit: true };
  }
  var unv = UNVERIFIED_RX.test(String(rel || '').replace(UNVERIFIED_QUALIFIER_RX, ' '));
  return { conf: unv ? UNVERIFIED_CONF : 1, verified: !unv, explicit: false };
}

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
    const orig = n.id;
    n.id = cid;
    NODE_BY_ID[cid] = n;
    // G1c: el id viejo (alias) también debe llevar al nodo canónico, aunque el
    // alias se haya cargado ANTES que el canónico (antes quedaba sin mapear:
    // jumpTo('AWS') o un hecho con el id viejo no encontraban la empresa).
    if (orig !== cid) NODE_BY_ID[orig] = n;
    if (NODES.indexOf(n) === -1) NODES.push(n);
  }

  // el seed también pasa por resolución (por si contiene ids alias)
  NODES.slice().forEach(function (n) {
    const cid = resolveId(n.id);
    if (cid !== n.id && NODE_BY_ID[cid] && NODE_BY_ID[cid] !== n) {
      const idx = NODES.indexOf(n);
      if (idx >= 0) NODES.splice(idx, 1);
      absorbNode(n);
    } else if (cid !== n.id) {
      // G1c: alias en el seed SIN canónico cargado todavía → pasa a ser el
      // canónico (si no, el canónico de una expansión entraba como 2º nodo)
      const orig = n.id; n.id = cid; NODE_BY_ID[cid] = n; NODE_BY_ID[orig] = n;
    } else { NODE_BY_ID[n.id] = n; }
  });
  expansions.forEach(function (arr) { if (arr) arr.forEach(absorbNode); });
  // G1c: TODO id alias lleva a su nodo canónico (también los alias que nunca
  // fueron un nodo propio, p. ej. 'AWS' → Amazon, usados en links y hechos).
  // Quien enumere NODE_BY_ID para listar nodos debe filtrar NODE_BY_ID[k].id === k.
  Object.keys(ALIAS).forEach(function (a) {
    const c = NODE_BY_ID[resolveId(a)];
    if (c && !NODE_BY_ID[a]) NODE_BY_ID[a] = c;
  });

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

  // Valuación verificada de privadas: el texto del ticker ("Pre-IPO ~$39B")
  // lo leen la ficha y las carteras (precio estimado) — que no circule la vieja.
  const PV = env.PRIVATE_VALUATIONS;
  if (PV && PV.entries) {
    Object.keys(PV.entries).forEach(function (id) {
      const n = NODE_BY_ID[resolveId(id)], e = PV.entries[id];
      if (!n || !e || !e.label || !n.preipo) return;
      if (/\$\s?[\d.,]+\s*[BT]/i.test(n.ticker || '')) n.ticker = String(n.ticker).replace(/~?\$\s?[\d.,]+\s*[BT]/i, '~' + e.label.split(' ')[0]);
      else if (!n.ticker || /privad|pre-?ipo/i.test(n.ticker)) n.ticker = 'Pre-IPO ~' + e.label.split(' ')[0];
    });
  }

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

  // links de expansión → RAW (acepta [s,t,w,rel,type,{conf,verified,since}?]
  // y {s,t,w,rel,type,conf?,verified?,since?})
  (env.linkArrays || []).forEach(function (arr) {
    if (!arr) return;
    arr.forEach(function (l) {
      if (Array.isArray(l)) RAW.push([l[0], l[1], l[2] || 2, l[3] || '', l[4] || 'supply', l[5]]);
      else {
        var meta = (l.conf != null || l.verified != null || l.since) ? { conf: l.conf, verified: l.verified, since: l.since } : undefined;
        RAW.push([l.s, l.t, l.w || 2, l.rel || '', l.type || 'supply', meta]);
      }
    });
  });

  // tubería final: resolver alias → filtrar → dedupe (s,t,type) → confianza
  const seen = new Map();
  const explicit = new Set();   // claves cuya confianza vino declarada (no derivada del texto)
  RAW.forEach(function (row) {
    const s = resolveId(row[0]), t = resolveId(row[1]);
    const w = row[2], rel = row[3] || '', type = row[4] || 'supply';
    const meta = (row[5] && typeof row[5] === 'object') ? row[5] : null;
    if (s === t || !(w > 0)) return;
    if (!NODE_BY_ID[s] || !NODE_BY_ID[t]) { warn('Link descartado por id inexistente: ' + row[0] + ' → ' + row[1]); return; }
    const sid = NODE_BY_ID[s].id, tid = NODE_BY_ID[t].id;
    if (sid === tid) return;
    const key = sid + '→' + tid + '·' + type;
    const prev = seen.get(key);
    const tr = linkTrust(rel, meta);
    if (prev) {
      if ((w || 2) > prev.w) prev.w = w || 2;
      if (rel.length > (prev.rel || '').length) prev.rel = rel;
      if (tr.explicit) { prev.conf = tr.conf; prev.verified = tr.verified; explicit.add(key); }
      else if (!explicit.has(key)) { const t2 = linkTrust(prev.rel); prev.conf = t2.conf; prev.verified = t2.verified; }
      if (meta && meta.since && !prev.since) prev.since = meta.since;
    } else {
      const o = { source: sid, target: tid, w: w || 2, rel: rel, type: type, conf: tr.conf, verified: tr.verified };
      if (meta && meta.since) o.since = meta.since;
      if (tr.explicit) explicit.add(key);
      seen.set(key, o);
    }
  });

  return { LINKS: Array.from(seen.values()), resolveId: resolveId };
}

if (typeof window !== 'undefined') { window.buildKhipusGraph = buildKhipusGraph; window.linkTrust = linkTrust; }
if (typeof module !== 'undefined' && module.exports) module.exports = { buildKhipusGraph, linkTrust, UNVERIFIED_RX, UNVERIFIED_QUALIFIER_RX, UNVERIFIED_CONF };
