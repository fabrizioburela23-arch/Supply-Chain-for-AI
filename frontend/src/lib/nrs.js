/**
 * NRS — Node Risk Score (0-100).
 *
 * Port fiel de `computeNRS` / `computeNRSBreakdown` de `app.html`
 * (~líneas 2253-2313 del clásico). Funciones PURAS: lo que el clásico
 * leía de globals (`NODE_BY_ID`, `window.LINKS` para el grado) entra
 * ahora por parámetros (`node`, `ctx`).
 *
 * BUG CONOCIDO Y REPRODUCIDO A PROPÓSITO (paridad > corrección, ver
 * CLAUDE.md): el término de margen `(1 - min(1, margin/0.4)) * 20` NO
 * está acotado por arriba — con margen negativo (empresas pre-revenue)
 * el término supera 20 (p.ej. margin = -0.5 → 45) e infla el score.
 * El TOTAL sí se acota a [0,100] al final, igual que en el clásico.
 * La réplica server (`ontology/agents.py:_compute_server_nrs`) sí acota
 * ese término a [0,20]; la divergencia está documentada — no "arreglar"
 * aquí sin decidirlo explícitamente.
 *
 * Términos de la fórmula (idénticos al clásico):
 *   geo           0-30  riesgo país (GEO_RISK; desconocido → 15)
 *   chain         0-25  min(25, grado * 2.5)
 *   market        0-20* margen como proxy de volatilidad (*sin tope superior real)
 *   fundamental   0-15  min(15, penalidad pre-IPO 10 + growth 🔴5/🟡2)
 *   concentration 0-10  Taiwan/China → 10, resto → 4
 */

/**
 * Riesgo geopolítico por país (0-30). Única copia — el clásico la
 * duplicaba inline en computeNRS y computeNRSBreakdown.
 * @type {Readonly<Record<string, number>>}
 */
export const GEO_RISK = Object.freeze({
  China: 28,
  Taiwan: 25,
  Korea: 15,
  Japan: 12,
  EEUU: 8,
  Europa: 10,
  Israel: 18,
});

/** Riesgo geo por defecto cuando el país no está en GEO_RISK. */
const GEO_DEFAULT = 15;

/**
 * @typedef {Object} NrsNode Campos del nodo que lee la fórmula.
 * @property {string} [country]  País ('China', 'Taiwan', 'EEUU', …).
 * @property {number} [margin]   Margen operativo como fracción (0.25 = 25%).
 *                               Ausente → 0.15. Negativo → infla el término
 *                               de margen (bug reproducido, ver arriba).
 * @property {boolean} [preipo]  true si la empresa es pre-IPO (+10 fundamental).
 * @property {string}  [growth]  Texto de crecimiento; se buscan los emojis
 *                               '🔴' (+5) o '🟡' (+2).
 */

/**
 * @typedef {Object} NrsCtx Contexto que el clásico sacaba de globals.
 * @property {number} [degree] Grado del nodo en LINKS (número de aristas
 *                             incidentes). El clásico lo precalculaba de
 *                             `window.LINKS`; aquí lo aporta el llamador
 *                             (ver {@link buildDegreeMap}). Ausente → 0.
 */

/**
 * Precalcula el grado de cada nodo a partir de los links (equivalente a
 * `_buildNrsDegree` del clásico). Acepta endpoints string o objeto
 * `{id}` (LINKS post-merge trae objetos).
 * @param {Array<{source: string|{id:string}, target: string|{id:string}}>} links
 * @returns {Map<string, number>} nodeId → grado
 */
export function buildDegreeMap(links) {
  const m = new Map();
  for (const l of links || []) {
    const s = typeof l.source === 'object' && l.source !== null ? l.source.id : l.source;
    const t = typeof l.target === 'object' && l.target !== null ? l.target.id : l.target;
    m.set(s, (m.get(s) || 0) + 1);
    if (t !== s) m.set(t, (m.get(t) || 0) + 1);
  }
  return m;
}

/**
 * Términos crudos de la fórmula — compartidos por computeNRS y
 * computeNRSBreakdown para que nunca vuelvan a divergir.
 * @param {NrsNode} node
 * @param {NrsCtx} [ctx]
 */
function _terms(node, ctx) {
  const degree = (ctx && Number.isFinite(ctx.degree)) ? ctx.degree : 0;

  // Geo (0-30): riesgo país
  const geo = GEO_RISK[node.country] ?? GEO_DEFAULT;

  // Cadena (0-25): grado como proxy de centralidad
  const chain = Math.min(25, degree * 2.5);

  // Mercado ("0-20"): proxy de volatilidad desde el margen.
  // SIN tope superior — margen negativo lo dispara (bug reproducido).
  const margin = node.margin != null ? node.margin : 0.15;
  const market = Math.round((1 - Math.min(1, margin / 0.4)) * 20);

  // Fundamental (0-15): penalidad pre-IPO + señal de crecimiento
  const growthStr = (node.growth || '').toLowerCase();
  const growthPen = growthStr.includes('🔴') ? 5 : (growthStr.includes('🟡') ? 2 : 0);
  const fundamental = Math.min(15, (node.preipo ? 10 : 0) + growthPen);

  // Concentración (0-10): dependencia de un solo país
  const concentration = (node.country === 'Taiwan' || node.country === 'China') ? 10 : 4;

  return { geo, chain, market, fundamental, concentration, degree };
}

/**
 * Node Risk Score 0-100. Devuelve SIEMPRE un NUMBER (nunca objeto) —
 * regla del clásico (CLAUDE.md). Nodo ausente → 50 (paridad con el
 * clásico cuando NODE_BY_ID no tenía el id).
 * @param {NrsNode|null|undefined} node Nodo (antes se resolvía vía NODE_BY_ID).
 * @param {NrsCtx} [ctx] Contexto: `{ degree }` del nodo en LINKS.
 * @returns {number} Score entero acotado a [0,100].
 */
export function computeNRS(node, ctx) {
  if (!node) return 50;
  const t = _terms(node, ctx);
  const nrs = Math.round(t.geo + t.chain + t.market + t.fundamental + t.concentration);
  return Math.min(100, Math.max(0, nrs));
}

/**
 * @typedef {Object} NrsTerm
 * @property {string} key    Nombre del término (en español, lo muestra el X-Ray).
 * @property {number} val    Valor del término (chain redondeado, como el clásico).
 * @property {number} max    Máximo nominal del término.
 * @property {boolean} hot   true si el término está "caliente" (umbral del clásico).
 * @property {string} detail Detalle legible (país, grado, % margen, …).
 */

/**
 * Descomposición término a término del NRS — misma fórmula que
 * {@link computeNRS}, devuelta desglosada (la usa el X-Ray para
 * mostrar "por qué N"). Nodo ausente → null (paridad con el clásico).
 *
 * Nota de paridad: `total` usa `chain` SIN redondear y luego redondea la
 * suma; `terms[1].val` muestra `chain` redondeado — por eso la suma de
 * los `val` mostrados puede diferir del `total` en ±1 (igual que el
 * clásico). `total` siempre coincide con `computeNRS(node, ctx)`.
 * @param {NrsNode|null|undefined} node
 * @param {NrsCtx} [ctx]
 * @returns {{total: number, terms: NrsTerm[]}|null}
 */
export function computeNRSBreakdown(node, ctx) {
  if (!node) return null;
  const t = _terms(node, ctx);
  return {
    total: Math.min(100, Math.max(0, Math.round(t.geo + t.chain + t.market + t.fundamental + t.concentration))),
    terms: [
      { key: 'Geopolítica', val: t.geo, max: 30, hot: t.geo >= 20, detail: node.country || '—' },
      { key: 'Cadena', val: Math.round(t.chain), max: 25, hot: t.chain >= 20, detail: 'grado ' + t.degree },
      { key: 'Margen', val: t.market, max: 20, hot: t.market >= 14, detail: node.margin != null ? Math.round(node.margin * 100) + '%' : 's/d' },
      { key: 'Fundamental', val: t.fundamental, max: 15, hot: t.fundamental >= 10, detail: node.preipo ? 'pre-IPO' : 'pública' },
      { key: 'Concentración', val: t.concentration, max: 10, hot: t.concentration >= 10, detail: node.country || '—' },
    ],
  };
}
