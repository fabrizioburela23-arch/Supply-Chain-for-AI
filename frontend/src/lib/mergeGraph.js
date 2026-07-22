/**
 * Merge del grafo + resolución de alias.
 *
 * Port fiel de `buildKhipusGraph` (`nodes/merge_graph.js`) y de la tabla
 * `NODE_ID_ALIAS` (`nodes/nodes_seed.js` ~línea 2476), como función PURA:
 * nada de `window.*`, no muta las entradas, devuelve arrays nuevos.
 *
 * Semántica reproducida del clásico:
 * - Un id alias es un DUPLICADO: el nodo canónico ABSORBE los campos
 *   faltantes del alias (solo rellena `null`/`undefined`/`''`; los campos
 *   del canónico siempre ganan) y los links del alias se redirigen.
 * - `rawLinks` acepta arrays `[s, t, w, rel, type]` Y objetos
 *   `{s, t, w, rel, type}` (los de links_expand.js llegan como objetos).
 * - Filtrado: se descartan self-links (tras resolver alias), pesos no
 *   positivos y links cuyos extremos no existen en el catálogo.
 * - Dedupe de links por clave (source, target, type): gana el mayor peso
 *   y la descripción (`rel`) más larga.
 * - Resultado `links`: objetos `{source, target, w, rel, type}`.
 *
 * MEJORA sobre el original (mismo RESULTADO, mejor costo): el clásico usaba
 * `NODES.indexOf(n)` + `NODES.splice(...)` dentro del bucle de absorción —
 * O(n²) sobre el catálogo. Aquí todo va con `Map` (id canónico → nodo
 * fusionado, clave de link → link ganador): O(n + m).
 *
 * Divergencias deliberadas (solo en casos patológicos, documentadas):
 * - Si un nodo tiene id alias pero su canónico NO existe en el catálogo, el
 *   clásico lo dejaba registrado bajo el id alias (y sus links se perdían);
 *   aquí el nodo adopta el id canónico, así sus links sí resuelven. En los
 *   datos reales todo alias tiene canónico, así que no hay diferencia.
 * - Dos nodos con el MISMO id se fusionan (el primero es la base); el
 *   clásico dejaba ambos en el array y el mapa apuntaba al último.
 */

/** Máximo de saltos al seguir cadenas de alias (igual que el clásico). */
const MAX_ALIAS_HOPS = 5;

/**
 * Resuelve un id siguiendo la tabla de alias (hasta {@link MAX_ALIAS_HOPS}
 * saltos, por si hay cadenas alias → alias → canónico).
 *
 * @param {string} id Id posiblemente alias.
 * @param {Record<string, string>} aliases Tabla alias → id canónico.
 * @returns {string} Id canónico.
 */
export function resolveAlias(id, aliases) {
  let cur = id;
  let hops = 0;
  while (aliases[cur] !== undefined && hops++ < MAX_ALIAS_HOPS) cur = aliases[cur];
  return cur;
}

/**
 * @typedef {Object} GraphNode
 * @property {string} id Id canónico del nodo.
 * // ...resto de campos del catálogo (label, cat, country, …) se preservan.
 */

/**
 * @typedef {Object} GraphLink
 * @property {string} source Id canónico del proveedor (source PROVEE a target).
 * @property {string} target Id canónico del cliente.
 * @property {number} w Peso (default 2).
 * @property {string} rel Descripción de la relación (default '').
 * @property {string} type Tipo de relación (default 'supply').
 */

/**
 * Un link crudo: array `[s, t, w?, rel?, type?]` u objeto
 * `{s, t, w?, rel?, type?}`.
 * @typedef {Array<*>|{s: string, t: string, w?: number, rel?: string, type?: string}} RawLink
 */

/**
 * Rellena en `base` los campos que le faltan (`null`/`undefined`/`''`)
 * tomándolos de `extra`. Nunca toca `id` ni pisa valores existentes.
 * Muta `base` (que siempre es una copia interna nuestra, no una entrada).
 *
 * @param {Record<string, *>} base Nodo que absorbe.
 * @param {Record<string, *>} extra Nodo absorbido.
 */
function absorbInto(base, extra) {
  for (const k in extra) {
    if (k === 'id') continue;
    if (base[k] == null || base[k] === '') base[k] = extra[k];
  }
}

/**
 * Fusiona el catálogo de nodos y los links crudos resolviendo alias.
 * Función pura: no muta `nodes`, `rawLinks` ni `aliases`.
 *
 * @param {Object} input
 * @param {ReadonlyArray<Record<string, *>>} input.nodes Catálogo seed
 *   (cada nodo con `id`; puede traer duplicados e ids alias).
 * @param {ReadonlyArray<RawLink>} [input.rawLinks] Links crudos, mezcla de
 *   arrays `[s,t,w,rel,type]` y objetos `{s,t,w,rel,type}`.
 * @param {Record<string, string>} [input.aliases] Tabla `NODE_ID_ALIAS`
 *   (alias → id canónico).
 * @param {(msg: string) => void} [input.warn] Callback opcional para links
 *   descartados por extremo inexistente (el clásico hacía `warn(...)`).
 * @returns {{nodes: GraphNode[], links: GraphLink[]}} Grafo fusionado:
 *   nodos deduplicados con campos absorbidos y links
 *   `{source, target, w, rel, type}` deduplicados por (s, t, type).
 */
export function mergeGraph({ nodes, rawLinks = [], aliases = {}, warn }) {
  const notify = warn || (() => {});

  // ── Nodos: dedupe + absorción, O(n) con Map ────────────────────────────
  /** @type {Map<string, Record<string, *>>} id canónico → nodo fusionado */
  const byId = new Map();
  /** @type {Set<string>} ids cuyo nodo almacenado ES el canónico real
   *  (venía con id === canónico, sus campos deben ganar). */
  const trueCanonical = new Set();

  for (const n of nodes) {
    const cid = resolveAlias(n.id, aliases);
    const existing = byId.get(cid);
    if (!existing) {
      byId.set(cid, { ...n, id: cid });
      if (n.id === cid) trueCanonical.add(cid);
      continue;
    }
    if (n.id === cid && !trueCanonical.has(cid)) {
      // Llega el canónico real y lo almacenado era un alias: los campos del
      // canónico ganan; el alias solo rellena huecos. Se reemplaza el valor
      // en el Map (conserva la posición de primera aparición).
      const merged = { ...n };
      absorbInto(merged, existing);
      byId.set(cid, merged);
      trueCanonical.add(cid);
    } else {
      absorbInto(existing, n);
    }
  }

  // ── Links: normalizar → resolver alias → filtrar → dedupe (s,t,type) ──
  /** @type {Map<string, GraphLink>} clave "s→t·type" → link ganador */
  const seen = new Map();

  for (const raw of rawLinks) {
    let s0, t0, w, rel, type;
    if (Array.isArray(raw)) {
      s0 = raw[0]; t0 = raw[1];
      w = raw[2] == null ? 2 : raw[2];
      rel = raw[3] || '';
      type = raw[4] || 'supply';
    } else {
      s0 = raw.s; t0 = raw.t;
      w = raw.w == null ? 2 : raw.w;
      rel = raw.rel || '';
      type = raw.type || 'supply';
    }

    const s = resolveAlias(s0, aliases);
    const t = resolveAlias(t0, aliases);
    if (s === t || !(w > 0)) continue;
    if (!byId.has(s) || !byId.has(t)) {
      notify('Link descartado por id inexistente: ' + s0 + ' → ' + t0);
      continue;
    }

    const key = s + '→' + t + '·' + type;
    const prev = seen.get(key);
    if (prev) {
      if (w > prev.w) prev.w = w;
      if (rel.length > prev.rel.length) prev.rel = rel;
    } else {
      seen.set(key, { source: s, target: t, w, rel, type });
    }
  }

  return { nodes: Array.from(byId.values()), links: Array.from(seen.values()) };
}
