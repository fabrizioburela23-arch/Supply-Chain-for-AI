// src/lib/khipu.js — puerto puro del lenguaje de comandos KHIPU
// (engine/khipu_lang.js). Gramática: <ENTIDAD> <FUNCIÓN> [ARGS].
//
// Diferencias con el clásico (deliberadas, ver MIGRATION.md):
// - Sin `window.*`, sin `fetch`, sin `localStorage`: este módulo SOLO parsea.
//   Los comandos que en el clásico disparaban red (FA, THESIS, PORT VAR,
//   GRAPH DIFF, ALERT LIST/CREATE) aquí devuelven un descriptor con `cmd` y
//   los campos necesarios para que el LLAMADOR ejecute la llamada vía
//   `src/api/client.js`.
// - La resolución de entidades (ticker/id → nodo) se inyecta con el parámetro
//   opcional `resolve`. Sin él, el símbolo crudo (en MAYÚSCULAS) se usa como
//   id/label/símbolo de mercado.
// - Se conservan las MISMAS formas de acción `{ type, arg }` que produce el
//   original: second_brain, navigate, tkg_object, stress, xray, compare,
//   livesim, insights, switch_tab.
//
// Gramática soportada (igual que el clásico):
//   NVDA DES · NVDA GP 1Y · NVDA SUP · NVDA CLI · NVDA RISK · NVDA SIM ·
//   NVDA NEWS · NVDA FA · NVDA XRAY · NVDA THESIS [texto]
//   PORT VAR · PORT PL
//   GRAPH ASOF <YYYY-MM-DD> · GRAPH DIFF <Nd>
//   ALERT <TICKER> PX|NRS > <valor> · ALERT REGION <región> NEWS · ALERT LIST
//   COMPARE <A> <B> · SHOCK <TICKER> [severidad] · INSIGHTS · MATRIX

/**
 * Nodo mínimo que puede devolver el resolutor inyectado.
 * @typedef {Object} KhipuNode
 * @property {string} id      Id canónico del nodo (p.ej. "nvidia").
 * @property {string} [label] Nombre visible (p.ej. "NVIDIA").
 * @property {string} [mkt]   Ticker de mercado (p.ej. "NVDA").
 */

/**
 * Resolutor de entidades: token del usuario → nodo conocido o null.
 * @callback KhipuResolve
 * @param {string} token
 * @returns {KhipuNode|null|undefined}
 */

/**
 * Acción para la UI — misma forma `{type, arg}` que el clásico.
 * `type` ∈ second_brain | navigate | tkg_object | stress | xray | compare |
 * livesim | insights | switch_tab.
 * @typedef {Object} KhipuAction
 * @property {string} type
 * @property {*} [arg]
 */

/**
 * Resultado del parser. Siempre trae `cmd`; el resto depende del comando:
 *
 * - DES:    { cmd:'DES', id, label, answer, actions:[{type:'second_brain',arg:id}] }
 * - GP:     { cmd:'GP', id, label, range, answer, actions:[{type:'navigate',arg:id}] }
 * - SUP/CLI/RISK/NEWS: { cmd, id, label, answer, actions:[{type:'tkg_object',arg:id}] }
 * - SIM:    { cmd:'SIM', id, label, answer, actions:[{type:'stress',arg:id}] }
 * - XRAY:   { cmd:'XRAY', id, label, answer, actions:[{type:'xray',arg:id}] }
 * - FA:     { cmd:'FA', id, label, symbol, actions:[{type:'second_brain',arg:id}] }
 *           (el llamador consulta GET /api/fundamentals/<symbol>)
 * - THESIS: { cmd:'THESIS', id, label, text, actions:[{type:'tkg_object',arg:id}] }
 *           (con `text` el llamador hace POST /api/ontology/actions/CrearTesis;
 *            sin texto trae `answer` y solo abre la ficha)
 * - PORT:   { cmd:'PORT', sub:'VAR'|'PL'|null, answer?, actions:[] }
 *           (sub null → answer de uso; el cálculo lo hace el llamador)
 * - GRAPH:  { cmd:'GRAPH', sub:'ASOF', date, answer?, actions:[] } ·
 *           { cmd:'GRAPH', sub:'DIFF', days, actions:[{type:'switch_tab',arg:'tkg'}] } ·
 *           { cmd:'GRAPH', sub:null, answer, actions:[] }
 * - ALERT:  { cmd:'ALERT', sub:'LIST', actions:[] } ·
 *           { cmd:'ALERT', sub:'REGION', rule:{metric:'news_region',region}, actions:[] } ·
 *           { cmd:'ALERT', sub:'CREATE', rule:{entity,metric:'price'|'nrs',op,value}, actions:[] } ·
 *           { cmd:'ALERT', sub:null, answer, actions:[] } (uso)
 * - COMPARE:{ cmd:'COMPARE', a, b, answer, actions:[{type:'compare',arg:{a,b}}] }
 * - SHOCK:  { cmd:'SHOCK', id, label, sev, answer, actions:[{type:'livesim',arg:{id,sev}}] }
 * - INSIGHTS / MATRIX: { cmd, answer, actions:[{type:'insights'}] }
 *
 * @typedef {Object} KhipuResult
 * @property {string} cmd
 * @property {string} [answer]
 * @property {KhipuAction[]} [actions]
 */

const FUNCS = new Set(['DES', 'GP', 'SUP', 'CLI', 'RISK', 'SIM', 'NEWS', 'FA', 'THESIS', 'XRAY']);
const KEYWORDS = new Set(['PORT', 'GRAPH', 'ALERT', 'COMPARE', 'SHOCK', 'INSIGHTS', 'MATRIX']);

/**
 * Resuelve un token a una entidad. Con `resolve` inyectado delega en él (y
 * devuelve null si no hay match — el texto sigue a la IA como lenguaje
 * natural, igual que el clásico). Sin `resolve`, acepta el símbolo crudo en
 * MAYÚSCULAS como id/label/ticker.
 * @param {string} token
 * @param {KhipuResolve} [resolve]
 * @returns {{id:string,label:string,mkt:string|null}|null}
 */
function resolveEntity(token, resolve) {
  if (!token) return null;
  if (typeof resolve === 'function') {
    const n = resolve(token);
    if (!n || !n.id) return null;
    return { id: n.id, label: n.label || n.id, mkt: n.mkt || null };
  }
  const sym = token.toUpperCase();
  return { id: sym, label: sym, mkt: sym };
}

/**
 * Intenta interpretar `text` como comando KHIPU.
 * Devuelve null si NO es un comando (para que el llamador lo mande a la IA).
 * @param {string} text  Texto crudo del usuario.
 * @param {KhipuResolve} [resolve]  Resolutor opcional ticker/id → nodo.
 * @returns {KhipuResult|null}
 */
export function tryParse(text, resolve) {
  const raw = (text || '').trim();
  if (!raw) return null;
  const parts = raw.split(/\s+/);
  const first = parts[0].toUpperCase();

  if (KEYWORDS.has(first)) {
    // INSIGHTS / MATRIX son comandos de una sola palabra; el resto exige args.
    if (parts.length < 2 && first !== 'INSIGHTS' && first !== 'MATRIX') return null;
    return handleKeyword(first, parts.slice(1), resolve);
  }

  if (parts.length < 2) return null;
  const fn = (parts[1] || '').toUpperCase();
  if (!FUNCS.has(fn)) return null;
  const entity = resolveEntity(parts[0], resolve);
  if (!entity) return null; // no es ticker/id conocido → lenguaje natural
  return handleEntityFunc(entity, fn, parts.slice(2));
}

/**
 * Comandos <ENTIDAD> <FUNCIÓN> [args].
 * @param {{id:string,label:string,mkt:string|null}} entity
 * @param {string} fn
 * @param {string[]} args
 * @returns {KhipuResult|null}
 */
function handleEntityFunc(entity, fn, args) {
  const { id, label } = entity;
  switch (fn) {
    case 'DES':
      return { cmd: 'DES', id, label, answer: `Abriendo ficha de ${label}.`, actions: [{ type: 'second_brain', arg: id }] };
    case 'GP':
      return {
        cmd: 'GP', id, label, range: args[0] || null,
        answer: `Gráfico de ${label}${args[0] ? ' (' + args[0] + ')' : ''}.`,
        actions: [{ type: 'navigate', arg: id }],
      };
    case 'SUP':
      return { cmd: 'SUP', id, label, answer: `${label} — proveedores en ◈ Grafo Temporal.`, actions: [{ type: 'tkg_object', arg: id }] };
    case 'CLI':
      return { cmd: 'CLI', id, label, answer: `${label} — clientes en ◈ Grafo Temporal.`, actions: [{ type: 'tkg_object', arg: id }] };
    case 'RISK':
      return { cmd: 'RISK', id, label, answer: `${label} — riesgo NRS en ◈ Grafo Temporal.`, actions: [{ type: 'tkg_object', arg: id }] };
    case 'NEWS':
      return { cmd: 'NEWS', id, label, answer: `${label} — noticias (abre 📰 en su ficha).`, actions: [{ type: 'tkg_object', arg: id }] };
    case 'SIM':
      return { cmd: 'SIM', id, label, answer: `Simulando la caída de ${label}.`, actions: [{ type: 'stress', arg: id }] };
    case 'XRAY':
      return { cmd: 'XRAY', id, label, answer: `Desarmando a ${label} — riesgo, hilos e impacto.`, actions: [{ type: 'xray', arg: id }] };
    case 'FA':
      // El llamador consulta GET /api/fundamentals/<symbol> vía api/client.js.
      return { cmd: 'FA', id, label, symbol: entity.mkt || id, actions: [{ type: 'second_brain', arg: id }] };
    case 'THESIS': {
      const texto = args.join(' ');
      if (!texto) {
        return { cmd: 'THESIS', id, label, text: null, answer: `${label} — abriendo su ficha (tesis registradas).`, actions: [{ type: 'tkg_object', arg: id }] };
      }
      // El llamador hace POST /api/ontology/actions/CrearTesis con este texto.
      return { cmd: 'THESIS', id, label, text: texto, actions: [{ type: 'tkg_object', arg: id }] };
    }
    default:
      return null;
  }
}

/**
 * Comandos que arrancan con palabra clave (PORT, GRAPH, ALERT, …).
 * @param {string} kw
 * @param {string[]} args
 * @param {KhipuResolve} [resolve]
 * @returns {KhipuResult|null}
 */
function handleKeyword(kw, args, resolve) {
  if (kw === 'PORT') return handlePort(args);
  if (kw === 'GRAPH') return handleGraph(args);
  if (kw === 'ALERT') return handleAlert(args, resolve);
  if (kw === 'COMPARE') return handleCompare(args, resolve);
  if (kw === 'SHOCK') return handleShock(args, resolve);
  if (kw === 'INSIGHTS') return { cmd: 'INSIGHTS', answer: 'Abriendo insights automáticos de la red.', actions: [{ type: 'insights' }] };
  if (kw === 'MATRIX') return { cmd: 'MATRIX', answer: 'Abriendo las 9 matrices de relación.', actions: [{ type: 'insights' }] };
  return null;
}

/**
 * PORT VAR · PORT PL. El cálculo (VaR vía POST /api/portfolio-risk, P&L con
 * cotizaciones en caché) lo ejecuta el llamador; aquí solo se clasifica.
 * @param {string[]} args
 * @returns {KhipuResult}
 */
function handlePort(args) {
  const sub = (args[0] || '').toUpperCase();
  if (sub === 'VAR' || sub === 'PL') return { cmd: 'PORT', sub, actions: [] };
  return { cmd: 'PORT', sub: null, answer: 'Comandos de PORT: VAR, PL.', actions: [] };
}

/**
 * GRAPH ASOF <YYYY-MM-DD> · GRAPH DIFF <Nd>.
 * ASOF: el llamador mueve la línea de tiempo del Grafo Temporal a `date`.
 * DIFF: el llamador consulta GET /api/ontology/graph/diff para `days` días.
 * @param {string[]} args
 * @returns {KhipuResult}
 */
function handleGraph(args) {
  const sub = (args[0] || '').toUpperCase();
  if (sub === 'ASOF') {
    const date = args[1] || null;
    if (!date) return { cmd: 'GRAPH', sub: 'ASOF', date: null, answer: 'Uso: GRAPH ASOF <YYYY-MM-DD>', actions: [] };
    return { cmd: 'GRAPH', sub: 'ASOF', date, actions: [] };
  }
  if (sub === 'DIFF') {
    const nStr = (args[1] || '30D').toUpperCase().replace('D', '');
    const days = parseInt(nStr, 10) || 30;
    return { cmd: 'GRAPH', sub: 'DIFF', days, actions: [{ type: 'switch_tab', arg: 'tkg' }] };
  }
  return { cmd: 'GRAPH', sub: null, answer: 'Comandos de GRAPH: ASOF <fecha>, DIFF <Nd>.', actions: [] };
}

const ALERT_USAGE = 'Uso: ALERT <TICKER> PX|NRS > <valor>  ·  ALERT LIST  ·  ALERT REGION <región> NEWS';

/**
 * ALERT LIST · ALERT REGION <región> NEWS · ALERT <TICKER> PX|NRS > <valor>.
 * LIST/REGION/CREATE los ejecuta el llamador contra /api/ontology/alerts;
 * las `rule` conservan la MISMA forma que el clásico
 * ({metric:'news_region',region} / {entity,metric:'price'|'nrs',op,value}).
 * @param {string[]} args
 * @param {KhipuResolve} [resolve]
 * @returns {KhipuResult}
 */
function handleAlert(args, resolve) {
  const sub = (args[0] || '').toUpperCase();
  if (sub === 'LIST') return { cmd: 'ALERT', sub: 'LIST', actions: [] };
  if (sub === 'REGION') {
    const region = args[1];
    const kind = (args[2] || '').toUpperCase();
    if (!region || kind !== 'NEWS') return { cmd: 'ALERT', sub: null, answer: 'Uso: ALERT REGION <región> NEWS', actions: [] };
    return { cmd: 'ALERT', sub: 'REGION', rule: { metric: 'news_region', region }, actions: [] };
  }
  const entity = resolveEntity(args[0] || '', resolve);
  const metricTok = (args[1] || '').toUpperCase();
  const op = args[2];
  const value = parseFloat(args[3]);
  if (!entity || !['PX', 'NRS'].includes(metricTok) || !op || isNaN(value)) {
    return { cmd: 'ALERT', sub: null, answer: ALERT_USAGE, actions: [] };
  }
  return {
    cmd: 'ALERT', sub: 'CREATE',
    rule: { entity: entity.id, metric: metricTok === 'PX' ? 'price' : 'nrs', op, value },
    actions: [],
  };
}

/**
 * COMPARE <A> <B> — comparación de dos entidades conocidas.
 * @param {string[]} args
 * @param {KhipuResolve} [resolve]
 * @returns {KhipuResult}
 */
function handleCompare(args, resolve) {
  const a = resolveEntity(args[0] || '', resolve);
  const b = resolveEntity(args[1] || '', resolve);
  if (!a || !b) {
    return { cmd: 'COMPARE', a: null, b: null, answer: 'Uso: COMPARE <A> <B> — dos tickers o ids conocidos.', actions: [] };
  }
  return {
    cmd: 'COMPARE', a: a.id, b: b.id,
    answer: `Comparando ${a.label} vs ${b.label}.`,
    actions: [{ type: 'compare', arg: { a: a.id, b: b.id } }],
  };
}

/**
 * SHOCK <TICKER> [severidad] — simulación en vivo de la caída de un nodo.
 * Severidad por defecto 100, igual que el clásico.
 * @param {string[]} args
 * @param {KhipuResolve} [resolve]
 * @returns {KhipuResult}
 */
function handleShock(args, resolve) {
  const e = resolveEntity(args[0] || '', resolve);
  if (!e) {
    return { cmd: 'SHOCK', id: null, answer: 'Uso: SHOCK <TICKER> [severidad] — simula su caída en vivo en el mapa.', actions: [] };
  }
  const sev = parseInt(args[1], 10);
  return {
    cmd: 'SHOCK', id: e.id, label: e.label, sev: isNaN(sev) ? 100 : sev,
    answer: `Simulando en vivo la caída de ${e.label}.`,
    actions: [{ type: 'livesim', arg: { id: e.id, sev: isNaN(sev) ? 100 : sev } }],
  };
}
