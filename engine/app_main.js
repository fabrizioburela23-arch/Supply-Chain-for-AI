
// Global error reporter — shows uncaught JS errors on screen (no devtools needed)
window.addEventListener('error', function(ev){
  var msg = (ev.message||'unknown error') + '\n' + (ev.filename||'') + ':' + (ev.lineno||'');
  if (ev.error && ev.error.stack) msg += '\n' + ev.error.stack.split('\n').slice(0,5).join('\n');
  var d = document.getElementById('_khipu_err_overlay');
  if (!d) {
    d = document.createElement('div'); d.id = '_khipu_err_overlay';
    d.style.cssText = 'position:fixed;bottom:0;left:0;right:0;z-index:99999;background:#1a0505;border-top:2px solid #ef4444;color:#fca5a5;padding:14px 20px;font-family:monospace;font-size:12px;white-space:pre-wrap;max-height:40vh;overflow-y:auto';
    document.body.appendChild(d);
  }
  d.textContent += '❌ ' + msg + '\n---\n';
});

// Solo-Railway (decisión 2026-07-03): la app SIEMPRE corre servida por server.py.
// El antiguo modo standalone (doble clic en app.html, API keys en el navegador)
// se eliminó — las keys viven únicamente en el servidor (.env / Railway).
// La variable se conserva porque engine/*.js la consulta (window.SERVER_MODE).
var SERVER_MODE = true;
var BASE = location.origin;
// Nombres de marca centralizados (el asistente "Khipu" es PROVISIONAL hasta
// que Fabrizio elija el definitivo — usar estas vars en código NUEVO; el
// texto ya existente se renombra con sed protegido, ver CLAUDE.md §Nombres).
window.APP_NAME = 'Khipus Finance Intelligence';
window.ASSISTANT_NAME = 'Khipu';
document.documentElement.classList.add('server-mode');
// ═══════════════════════════════════════════════════════════════
// Khipu Finance v1 · Cadena de Valor Global · 450+ empresas · 35 categorías
// Construido: 2026-06-12
// Nodos: 132+ | Links: 530+ | Tipos de relación: 7 | Pestañas: 4
// Mejoras M1-M10 implementadas
// ═══════════════════════════════════════════════════════════════
/* ============================================================================
   DEL SILICIO A LA IA — Cadena de valor global 2026
   Semiconductores · Computación cuántica · Conectividad · Infraestructura IA
   Datos compilados de fuentes públicas y estimaciones de analistas (jun. 2026)
   ============================================================================ */

// (movido a nodes/nodes_seed.js) — const CATS

// Nuevas categorías para nodos expandidos
// (movido a nodes/nodes_seed.js) — const CATS_NEW
Object.assign(CATS, CATS_NEW);
window.CATS = CATS;  // expuesto para el layout semántico del grafo 3D

/* Países para la vista geopolítica: cluster propio + color propio */
// (movido a nodes/nodes_seed.js) — const COUNTRIES
function countryColor(k){
  const co=COUNTRIES[k]||COUNTRIES.RestoMundo;
  return document.body.classList.contains('dark')?co.cd:co.c;
}

function catColor(cat){
  if (!CATS[cat]) return '#888';
  return getComputedStyle(document.documentElement).getPropertyValue(CATS[cat].cssVar).trim() || '#888';
}

// ── Macro-sectores NEXUS (Etapa 4): 40 categorías → 9 colores vivos ──────────
// SECTORS9 y CAT_TO_SECTOR viven en nodes/nodes_seed.js; se exponen para el
// X-Ray, el globo y el resto de motores.
window.SECTORS9 = (typeof SECTORS9 !== 'undefined') ? SECTORS9 : {};
window.CAT_TO_SECTOR = (typeof CAT_TO_SECTOR !== 'undefined') ? CAT_TO_SECTOR : {};
/* Nombre VISIBLE de un macro-sector en el idioma activo (cada entrada de
   SECTORS9 ya trae `en`; los módulos mostraban siempre `label` en español).
   Acepta la clave de sector ('macro_credito') o, con byCat=true, una categoría. */
window.sectorName = function(key, byCat){
  var k = byCat ? ((window.CAT_TO_SECTOR || {})[key] || 'cloud_ia') : key;
  var s = (window.SECTORS9 || {})[k];
  if(!s) return key || '';
  return (typeof LANG !== 'undefined' && LANG === 'en' && s.en) ? s.en : s.label;
};
function sectorColorFor(cat){
  var s = window.SECTORS9[(window.CAT_TO_SECTOR[cat]) || 'cloud_ia'];
  return s ? s.color : '#00E0FF';
}
function sectorLabelFor(cat){
  var s = window.SECTORS9[(window.CAT_TO_SECTOR[cat]) || 'cloud_ia'];
  return s ? (LANG==='en' ? s.en : s.label) : 'Cloud & IA';
}
/* Track A Fase 0 — reubicadas desde engine/graph3d.js. Desde la Fase 2 estas
   son las ÚNICAS definiciones del repo: la copia duplicada de graph3d.js se
   borró (pisaba esta en silencio al cargar). Las usan el Grafo Temporal,
   universe2d, secondbrain e hypergraph, y cargan siempre — también cuando
   graph3d.js no se carga (camino sin WebGL). */
function getCatColorHex(cat) {
  if (typeof catColor === 'function') {
    try { const v = catColor(cat); if (v) return v; } catch (e) {}
  }
  const meta = (typeof CATS !== 'undefined' && CATS[cat]) || (typeof CATS_NEW !== 'undefined' && CATS_NEW[cat]) || {};
  const val = getComputedStyle(document.documentElement)
    .getPropertyValue(meta.cssVar || '--c-fabless').trim();
  return val || '#52B1FF';
}
function getLinkColorHex(type) {
  const LINK_HEX = {
    supply:   '#4E8B1E', fab:      '#0F8C5F', license:  '#6B5DD3',
    cloud:    '#0A6CA8', invest:   '#B8880D', deploy:   '#0E7A6E',
    partner:  '#8A857A', customer: '#C25E12', owns:     '#7C3AED',
  };
  return LINK_HEX[type] || '#4E8B1E';
}
// Por defecto el mapa colorea por MACRO-SECTOR (9 colores limpios); el detalle
// de las 40 categorías se recupera con el toggle de la leyenda.
let colorMode = localStorage.getItem('eco_colormode') || 'sector';

/* ---- i18n base ---- */
let LANG = localStorage.getItem('eco_lang')||'es';
// window.LANG = idioma VIVO: un `let` global NO crea propiedad en window y
// muchos módulos (engine/*, avisos de trading, franja "servidor caído") leen
// window.LANG → antes era siempre undefined y salían en español.
try { Object.defineProperty(window, 'LANG', { get(){ return LANG; }, configurable: true }); } catch(e) {}
if(localStorage.getItem('eco_theme')!=='light') document.body.classList.add('dark'); /* v8.1: terminal dark por defecto */
const catLabel = k => CATS[k] ? (LANG==='en' ? CATS[k].en : CATS[k].label) : (k||'?');
const countryLabel = k => (COUNTRIES[k]||COUNTRIES.RestoMundo)[LANG==='en'?'en':'es'];
const nf = (d,f) => (LANG==='en' && d[f+'_en']) ? d[f+'_en'] : d[f];

/* Schema por nodo:
   { id, label, ticker, cat, port, role, supplies, moat, loc, region, growth,
     margin (fracción estricta sobre el precio de venta final, ej 0.45 = 45%),
     capex_2026, backlog_status, preipo?, risk?, big? } */


// (movido a nodes/nodes_seed.js) — const NODES


/* Links: [source (proveedor), target (cliente), peso 1-6, descripción de la relación] */
// (movido a nodes/nodes_seed.js) — const RAW_LINKS


// NODE_BY_ID is populated here from NODES_CORE, then expanded after
// NODES_EXPAND / NODES_EXPAND2 / NODES_SPACEX merges (see below ~line 4026)
const NODE_BY_ID = Object.fromEntries(NODES.map(n=>[n.id,n]));

// Shares outstanding en billones (para computar market cap en vivo)
// (movido a nodes/nodes_seed.js) — const SHARES_OUTSTANDING_B

function computeNodeRadius(nodeId) {
  const n = NODE_BY_ID ? NODE_BY_ID[nodeId] : null;
  if (!n) return 9;

  // Market cap base estimado
  const MKT_CAP_EST = {
    'SpaceX': 350, 'Anthropic': 61, 'OpenAI': 300, 'xAI': 40,
    'Anduril': 28, 'ScaleAI': 13.8, 'ElevenLabs': 3.3, 'AlphaSense': 4,
    'Cohere': 2.2, 'ShieldAI': 2.7, 'BlueOrigin': 15, 'ICEYE': 0.5,
  };

  // 2026-10-06 (pedido de Fabrizio: "los nodos del tamaño correcto de su market cap en vivo"):
  // NODE_META.mktcap_b = capitalización EN VIVO (KhipuLiveCaps, cada 15 min, las ~570 cotizadas),
  // valuación VERIFICADA (privadas, applyVerifiedValuations) o, mientras llega, la del catálogo.
  // La tabla fija queda como último recurso. Las etiquetas visibles NO dependen de esto: ver _lblOn.
  const _m = (window.NODE_META || {})[nodeId];
  let cap_B = (_m && _m.mktcap_b > 0) ? +_m.mktcap_b : (MKT_CAP_EST[nodeId] || 0.5);

  // Si hay precio en vivo y shares conocidos → calcular market cap real
  // window.MKT bypasses TDZ (const MKT declared later at line ~5539)
  if (window.MKT && n.mkt) {
    const q = window.MKT.quotes ? window.MKT.quotes[n.mkt] : null;
    const shares = SHARES_OUTSTANDING_B[n.mkt];
    if (q && q.close && shares) {
      cap_B = q.close * shares;
    }
  }

  // Escala logarítmica
  const logCap = Math.log10(Math.max(0.05, cap_B));
  const normalized = Math.min(1, Math.max(0, (logCap + 1.3) / 4.8));

  const MIN_R = n.preipo ? 4 : (n.big ? 12 : 5);
  const MAX_R = n.big ? 28 : 22;
  return Math.round(MIN_R + normalized * (MAX_R - MIN_R));
}

// ── NRS memoizado ────────────────────────────────────────────────────────────
// computeNRS se llama cientos de veces por render (análisis, voz, stress). El
// grado (degree) se sacaba filtrando TODO window.LINKS en cada llamada → O(L)
// por nodo → O(N·L) por pantalla. Precalculamos el grado una vez y cacheamos el
// score por nodo. Llama window._invalidateNRS() si LINKS cambia.
let _nrsDegree = null;                 // Map nodeId -> grado ESTRUCTURAL en LINKS
const _nrsCache = new Map();           // nodeId -> score 0-100
// G4d (misión de reparación 2026-10-04): el grado del NRS es ESTRUCTURAL —
// cuenta pares distintos source→target unidos por una relación de FLUJO
// (suministro, fabricación, nube, licencia, energía, propiedad, despliegue).
// Socios (`partner`) e inversores (`invest`) NO son proveedores ni clientes,
// y un mismo par con dos tipos (supply+fab) o duplicado cuenta UNA vez.
// Antes se contaba toda fila de LINKS (753 partner + 192 invest + 48 pares
// repetidos) y el término "cadena" (hasta 25 pts) salía inflado: los NRS
// visibles BAJAN para empresas con muchos socios/accionistas. Misma regla que
// ontology/agents.py server_flow_degree y ontology.vocabulary.flow_degree;
// la lista refleja vocabulary.json (relation_types.*.flow = true).
const NRS_FLOW_TYPES = { supply: 1, fab: 1, cloud: 1, license: 1, ppa: 1, owns: 1, deploy: 1 };
window.NRS_FLOW_TYPES = NRS_FLOW_TYPES;   // proveedores/clientes de cualquier módulo = solo FLUJO (G4a)
function _buildNrsDegree() {
  const m = new Map();
  const pairs = new Set();
  const L = window.LINKS || [];
  for (const l of L) {
    if (!NRS_FLOW_TYPES[l.type || 'supply']) continue;
    const s = lid(l.source), t = lid(l.target);
    if (s === t) continue;
    const k = s + '\u2192' + t;
    if (pairs.has(k)) continue;
    pairs.add(k);
    m.set(s, (m.get(s) || 0) + 1);
    m.set(t, (m.get(t) || 0) + 1);
  }
  return m;
}
window._buildNrsDegree = _buildNrsDegree;
function _invalidateNRS() { _nrsCache.clear(); _nrsDegree = null; }
window._invalidateNRS = _invalidateNRS;

// Revisión G1c (2026-10-04): NODE_BY_ID[alias] lleva al nodo canónico; quien
// luego busca grado/vínculos por id debe usar el id CANÓNICO (n.id).
function _canonId(id){ const n = (typeof NODE_BY_ID !== 'undefined' && NODE_BY_ID) ? NODE_BY_ID[id] : null; return (n && n.id) || id; }
window._canonId = _canonId;
// Los 5 términos del NRS, calculados en UN solo sitio (limpieza 2026-10-11: antes computeNRS y
// computeNRSBreakdown re-escribían la fórmula cada una). MISMA fórmula que core/world.py client_nrs
// — servidor (ontology/agents.py), MCP y carteras delegan ahí; tests/test_cleanup_nrs_parity.py
// compara las dos implementaciones sobre TODO el catálogo.
const _NRS_GEO = { 'China': 28, 'Taiwan': 25, 'Korea': 15, 'Japan': 12, 'EEUU': 8, 'Europa': 10, 'Israel': 18 };
function _nrsTerms(nodeId, n) {
  // Geo risk (0-30): país escrito de cualquier forma ("Japón", "Corea", "Estados Unidos"…) → clave de la tabla
  const ck = _nrsCountry(n.country);
  const geo = _NRS_GEO[ck] ?? 15;
  // Chain risk (0-25): grado ESTRUCTURAL (precalculado 1 vez)
  if (_nrsDegree === null && window.LINKS) _nrsDegree = _buildNrsDegree();
  const degree = _nrsDegree ? (_nrsDegree.get(nodeId) || 0) : 0;
  const chain = Math.min(25, degree * 2.5);
  // Market risk (0-20): volatility proxy from margin
  // acotado a [0,20] (2026-10-05): sin esto una empresa sin ganancias (OpenAI) llegaba a NRS 100
  const margin = n.margin != null ? n.margin : 0.15;
  const market = Math.max(0, Math.min(20, Math.round((1 - Math.min(1, margin / 0.4)) * 20)));
  // Fundamental risk (0-15): preipo penalty + growth signal
  const growth_str = (n.growth || '').toLowerCase();
  const fundamental = Math.min(15, (n.preipo ? 10 : 0) + (growth_str.includes('🔴') ? 5 : (growth_str.includes('🟡') ? 2 : 0)));
  // Concentration risk (0-10): single-country dependency
  const concentration = (ck === 'Taiwan' || ck === 'China') ? 10 : 4;
  const total = Math.min(100, Math.max(0, Math.round(geo + chain + market + fundamental + concentration)));
  return { geo, degree, chain, market, fundamental, concentration, total };
}
function computeNRS(nodeId) {
  nodeId = _canonId(nodeId);   /* revisión G1c: un id viejo (alias) usa el grado del canónico */
  const hit = _nrsCache.get(nodeId);
  if (hit !== undefined) return hit;
  const n = NODE_BY_ID ? NODE_BY_ID[nodeId] : null;
  if (!n) return 50;
  const val = _nrsTerms(nodeId, n).total;
  if (window.LINKS) _nrsCache.set(nodeId, val);  // cachear solo cuando el grafo ya cargó
  return val;
}

// Descomposición término a término del NRS — la usa el X-Ray para mostrar
// "por qué N": misma fórmula que computeNRS, devuelta desglosada.
var _NRS_GEO_ALIAS = { 'china':'China', 'taiwan':'Taiwan', 'korea':'Korea', 'corea':'Korea', 'corea del sur':'Korea',
  'south korea':'Korea', 'japan':'Japan', 'japon':'Japan', 'eeuu':'EEUU', 'ee uu':'EEUU', 'estados unidos':'EEUU', 'usa':'EEUU',
  'united states':'EEUU', 'us':'EEUU', 'europa':'Europa', 'europe':'Europa', 'israel':'Israel' };
function _nrsCountry(c){
  const norm = x => String(x == null ? '' : x).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
  return _NRS_GEO_ALIAS[norm(c)] || _NRS_GEO_ALIAS[norm(String(c || '').split(/[\/(,;]/)[0])] || null;
}
function computeNRSBreakdown(nodeId) {
  nodeId = _canonId(nodeId);
  const n = NODE_BY_ID ? NODE_BY_ID[nodeId] : null;
  if (!n) return null;
  const _en = (typeof LANG !== 'undefined' && LANG === 'en');   /* regla bilingüe: los términos se MUESTRAN */
  const T = _nrsTerms(nodeId, n);
  return {
    total: T.total,
    terms: [
      { key: _en ? 'Geopolitics' : 'Geopolítica', val: T.geo, max: 30, hot: T.geo >= 20, detail: n.country || '—' },
      { key: _en ? 'Supply chain' : 'Cadena', val: Math.round(T.chain), max: 25, hot: T.chain >= 20, detail: (_en ? 'degree ' : 'grado ') + T.degree },
      { key: _en ? 'Margin' : 'Margen', val: T.market, max: 20, hot: T.market >= 14, detail: n.margin != null ? Math.round(n.margin * 100) + '%' : (_en ? 'n/a' : 's/d') },
      { key: 'Fundamental', val: T.fundamental, max: 15, hot: T.fundamental >= 10, detail: n.preipo ? 'pre-IPO' : (_en ? 'public' : 'pública') },
      { key: _en ? 'Concentration' : 'Concentración', val: T.concentration, max: 10, hot: T.concentration >= 10, detail: n.country || '—' },
    ],
  };
}
window.computeNRSBreakdown = computeNRSBreakdown;
window.computeNRS = computeNRS;

// (movido a nodes/nodes_seed.js) — const NODE_META
window.NODE_META = NODE_META;  // el X-Ray lee mktcap/founded/geo_risk

/* ── Valuación VERIFICADA de privadas = la ÚNICA que circula (2026-10-05) ───
   La auditoría encontró Anthropic con TRES valuaciones en la misma ficha ($965B verificada,
   "$350B (2025)" del PREIPO_INTEL y "$60B" del catálogo) — y la de $60B entraba en el valor
   de las carteras. Aquí, una sola vez al cargar: NODE_META.mktcap_b, PREIPO_INTEL.valuation
   e INVEST_PATH toman la de nodes/private_valuations.js (con fecha y fuente). Las cotizadas
   las sigue pisando la capitalización EN VIVO (KhipuLiveCaps). */
function applyVerifiedValuations(){
  const PV = window.PRIVATE_VALUATIONS;
  const NB = window.NODE_BY_ID || NODE_BY_ID;
  if(!PV || !PV.entries) return;
  Object.keys(PV.entries).forEach(function(k){
    const e = PV.entries[k], n = NB[k];
    if(!n || !e || !(+e.valuation_usd_b > 0)) return;
    if(n.listing && n.listing.status === 'public') return;          // cotizada: manda el precio en vivo
    const m = NODE_META[n.id] = NODE_META[n.id] || {};
    if(m.mktcap_b != null && m.mktcap_catalog == null) m.mktcap_catalog = m.mktcap_b;
    m.mktcap_b = +e.valuation_usd_b;
    m.mktcap_verified = {as_of: e.as_of, label: e.label, source_url: e.source_url, round: e.round || null};
    const pi = (window.PREIPO_INTEL || {})[n.id];
    if(pi){ if(pi.valuation && pi.valuation_catalog == null) pi.valuation_catalog = pi.valuation; pi.valuation = e.label; pi.valuation_verified = true; }
    const ip = INVEST_PATH[n.id];
    if(ip && ip.note) ip.note = ip.note.replace(/Valoraci[oó]n\s*~?\$\s?[\d.,]+\s*[BT]?\s*(\(\d{4}\))?/i, function(){ return 'Valuación verificada ' + e.label; });
  });
  // empresas que YA cotizan: la nota vieja ("IPO realizada en Nasdaq 2024") se reemplaza por la verificada
  Object.keys(INVEST_PATH).forEach(function(k){
    const n = NB[k], ip = INVEST_PATH[k];
    if(n && n.listing && /^(public|merged|acquired)$/.test(n.listing.status) && ip && (n.listing.note_es || n.listing.note)) ip.note = n.listing.note_es || n.listing.note;
  });
  // fusionadas (xAI → SpaceX/SPCX): no circula una valuación propia vieja; se dice dónde está ahora
  Object.keys(NB).forEach(function(k){
    const n = NB[k];
    if(!n || n.id !== k || !n.listing || n.listing.status !== 'merged') return;
    const m = NODE_META[n.id];
    if(m && m.mktcap_b != null){ if(m.mktcap_catalog == null) m.mktcap_catalog = m.mktcap_b; m.mktcap_b = null; }
    const pi = (window.PREIPO_INTEL || {})[n.id];
    if(pi){ if(pi.valuation_catalog == null) pi.valuation_catalog = pi.valuation; pi.valuation = n.listing.note_es || ('→ ' + (n.listing.parent || '')); }
  });
}
window.applyVerifiedValuations = applyVerifiedValuations;
applyVerifiedValuations();
// las expansiones del catálogo se suman después: se vuelve a aplicar cuando TODO el catálogo cargó
document.addEventListener('DOMContentLoaded', applyVerifiedValuations);

const LINK_TYPE_COLORS = {
  supply:   {light:'#4E8B1E', dark:'#9BCF5E'},
  fab:      {light:'#0F8C5F', dark:'#43C896'},
  license:  {light:'#6B5DD3', dark:'#A99EEC'},
  cloud:    {light:'#0A6CA8', dark:'#4FA8E0'},
  invest:   {light:'#B8880D', dark:'#D9A520'},
  deploy:   {light:'#0E7A6E', dark:'#40B8A8'},
  partner:  {light:'#8A857A', dark:'#B5B0A4'},
  customer: {light:'#C25E12', dark:'#EF8B40'},
  owns:     {light:'#7C3AED', dark:'#A855F7'},
};

function getLinkColor(type) {
  const theme = document.body.classList.contains('dark') ? 'dark' : 'light';
  return (LINK_TYPE_COLORS[type] || LINK_TYPE_COLORS.supply)[theme];
}

// ── Merge del catálogo: UNA sola implementación en nodes/merge_graph.js ─────
// (resolución de entidades + absorción + redirección de links + dedupe).
// La usa también scripts/export_graph_v0.js — no duplicar lógica aquí.
const _mergeResult = buildKhipusGraph({
  NODES, NODE_BY_ID, NODE_ID_ALIAS, RAW_LINKS,
  LISTING_STATUS: window.LISTING_STATUS || null,   /* estado en bolsa verificado */
  PRIVATE_VALUATIONS: window.PRIVATE_VALUATIONS || null,   /* valuación verificada de privadas */
  expansions: [typeof NODES_EXPAND !== 'undefined' ? NODES_EXPAND : null,
               typeof NODES_EXPAND2 !== 'undefined' ? NODES_EXPAND2 : null,
               typeof NODES_SPACEX !== 'undefined' ? NODES_SPACEX : null,
               typeof NODES_EXPAND3 !== 'undefined' ? NODES_EXPAND3 : null,
               typeof NODES_NUCLEAR !== 'undefined' ? NODES_NUCLEAR : null,
               typeof NODES_EXPAND4 !== 'undefined' ? NODES_EXPAND4 : null,
               typeof NODES_EXPAND5 !== 'undefined' ? NODES_EXPAND5 : null,
               typeof NODES_CHINA !== 'undefined' ? NODES_CHINA : null,
               typeof NODES_MULTICAPA !== 'undefined' ? NODES_MULTICAPA : null],
  linkArrays: [typeof LINKS_EXPAND !== 'undefined' ? LINKS_EXPAND : null,
               typeof LINKS_SPACEX !== 'undefined' ? LINKS_SPACEX : null,
               typeof LINKS_CONNECT !== 'undefined' ? LINKS_CONNECT : null,
               typeof LINKS_NUCLEAR !== 'undefined' ? LINKS_NUCLEAR : null,
               typeof LINKS_EXPAND4 !== 'undefined' ? LINKS_EXPAND4 : null,
               typeof LINKS_EXPAND5 !== 'undefined' ? LINKS_EXPAND5 : null,
               typeof LINKS_CHINA !== 'undefined' ? LINKS_CHINA : null,
               typeof LINKS_MULTICAPA !== 'undefined' ? LINKS_MULTICAPA : null],
  warn: m => console.warn(m),
});
const _resolveId = _mergeResult.resolveId;
window.NODES = NODES;
// Exponer NODE_BY_ID al scope global: muchos módulos (grafo temporal, etc.) leen
// window.NODE_BY_ID. Sin esto quedaba undefined → el Grafo Temporal veía 0 aristas.
window.NODE_BY_ID = NODE_BY_ID;
// Los links de expansión y la tubería final viven en buildKhipusGraph (nodes/merge_graph.js).
var LINKS = _mergeResult.LINKS;
window.LINKS = LINKS;

const lid = v => (typeof v==='object' && v!==null) ? v.id : v;

/* ===================== D3 force graph ===================== */
const svg = d3.select('#graph');
let W=0,H=0;
const root = svg.append('g');
const regionLayer = root.append('g');
const linkLayer = root.append('g');
const nodeLayer = root.append('g');
// Las etiquetas de país van POR ENCIMA de los nodos para que se lean (sin bloquear clics)
regionLayer.raise().style('pointer-events','none');
// engine/maptime.js inserta su capa ⚡ Eventos entre enlaces y nodos
window._mapLayers = { root, linkLayer, nodeLayer };

// la transición del zoom puede dar NaN si el svg se colapsa a 0×0 a mitad de camino (ventana minimizada/oculta):
// ese fotograma se ignora en vez de escribir translate(NaN,NaN) (decenas de errores en la consola)
const zoom = d3.zoom().scaleExtent([.3,3.5]).on('zoom',e=>{const t=e.transform; if(isFinite(t.x)&&isFinite(t.y)&&isFinite(t.k)) root.attr('transform',t);});
svg.call(zoom);
svg.on('dblclick.zoom',null);

let selected=null, hovered=null, activePF=null, activeCat=null, activeCountry=null, searchTerm='', activeLinkType='';
let viewMode='flow', stressId=null, stressAffected=new Set();
/* v7 · M4: estado del pathfinder */
let pathfinderMode=false, pathSrc=null, pathDst=null, pathActive=false;
let pathNodes=new Set(), pathLinkKeys=new Set();
function isPathLink(l){ return pathLinkKeys.has(lid(l.source)+'>'+lid(l.target)); }

// Loading progress — helper used throughout scripts[1]
const _loaderBar = document.getElementById('loader-bar');
const _loaderText = document.getElementById('loader-text');
function _ldrSet(pct, text) {
  if (_loaderBar) _loaderBar.style.width = pct + '%';
  if (_loaderText && text) _loaderText.textContent = text;
}
_ldrSet(25, `Procesando ${NODES.length} nodos · ${LINKS.length} conexiones…`);

// SAFETY: Hard fallback registered HERE (before any potentially-crashing code)
// so that even if D3 setup throws, the loader will dismiss after 6s.
(function(){
  const _ldr = document.getElementById('khipu-loader');
  if (!_ldr) return;
  window._khipuLoaderDismiss = function(){
    if (!_ldr.parentNode) return;
    _ldr.style.transition = 'opacity .5s';
    _ldr.style.opacity = '0';
    setTimeout(function(){ if (_ldr.parentNode) _ldr.parentNode.removeChild(_ldr); }, 550);
  };
  window._khipuLoaderFallback = setTimeout(function(){
    if (document.getElementById('khipu-loader')) {
      if (_loaderText) _loaderText.textContent = 'Listo (' + NODES.length + ' nodos)';
      window._khipuLoaderDismiss();
    }
  }, 6000);
})();
_ldrSet(40, `Iniciando simulación de fuerzas (${NODES.length} nodos)…`);
// With 450+ nodes, reduce charge and increase decay for smoother convergence
const _nodeCount = NODES.length;
const _chargeStr = _nodeCount > 300 ? -180 : _nodeCount > 150 ? -220 : -280;
const _alphaDecay = _nodeCount > 300 ? 0.04 : 0.02;
const sim = d3.forceSimulation(NODES)
  .force('link', d3.forceLink(LINKS).id(d=>d.id).distance(d=>60+d.w*4).strength(.3))
  .force('charge', d3.forceManyBody().strength(_chargeStr).distanceMax(400))
  .force('collide', d3.forceCollide(d=>computeNodeRadius(d.id)+10))
  .alphaDecay(_alphaDecay).velocityDecay(.38);
/* VELOCIDAD (Khipus OS, 2026-10-06): d3 arranca su reloj interno al crear la simulación y
   calculaba ticks (~11 ms c/u con 949 nodos) mientras se cargaban los scripts, aunque Khipus OS
   tapara el mapa. Con el OS (lo normal) se detiene YA y la física se adelanta solo cuando el mapa
   se ve (_ensureMapSettled, más abajo). En "Vista clásica" el mapa ES la pantalla de arranque:
   se conserva el calentamiento de d3 detrás del splash, igual que antes (medido: es lo más rápido
   para ver el mapa listo en un móvil lento). El arrastre la reactiva en vivo como siempre. */
const _mapClassicBoot = (function(){ try { return sessionStorage.getItem('kh_os_classic') === '1'; } catch(e){ return false; } })();
if(!_mapClassicBoot) sim.stop();

function setForces(){
  if(viewMode==='geo'){
    sim.force('x', d3.forceX(d=>(COUNTRIES[d.country]||COUNTRIES.RestoMundo).x*W).strength(.55))
       .force('y', d3.forceY(d=>(COUNTRIES[d.country]||COUNTRIES.RestoMundo).y*H).strength(.55));
  } else {
    sim.force('x', d3.forceX(d=>(CATS[d.cat]||CATS.aisoft).x*W).strength(.5))
       .force('y', d3.forceY(H/2).strength(.07));
  }
}

function nodeFill(d){
  if(viewMode==='geo') return countryColor(d.country);
  return colorMode==='sector' ? sectorColorFor(d.cat) : catColor(d.cat);
}
function recolorNodes(){ nodeSel.select('.n-core').attr('fill',d=>nodeFill(d)); }

// ── Hooks de simulación VIVA (engine/livesim.js) ────────────────────────────
// Recolorea los nodos por impacto 0-100 (color base → rojo), sin re-render.
function _mixHex(a,b,t){
  a=a.replace('#',''); b=b.replace('#','');
  if(a.length===3) a=a.replace(/./g,'$&$&'); if(b.length===3) b=b.replace(/./g,'$&$&');
  const ar=parseInt(a.slice(0,2),16),ag=parseInt(a.slice(2,4),16),ab=parseInt(a.slice(4,6),16);
  const br=parseInt(b.slice(0,2),16),bg=parseInt(b.slice(2,4),16),bb=parseInt(b.slice(4,6),16);
  const m=(x,y)=>Math.round(x+(y-x)*t).toString(16).padStart(2,'0');
  return '#'+m(ar,br)+m(ag,bg)+m(ab,bb);
}
window._liveRecolorByImpact = function(impactMap, dir){
  const tint = dir==='up' ? '#2BE38B' : '#FF4D6A';   // auge=verde, daño=rojo
  nodeSel.select('.n-core').attr('fill', d=>{
    const imp = impactMap ? (impactMap.get(d.id)||0) : 0;
    return imp<=0 ? nodeFill(d) : _mixHex(nodeFill(d),tint,Math.min(1,imp/100));
  }).attr('r', d=>{
    const imp = impactMap ? (impactMap.get(d.id)||0) : 0;
    return computeNodeRadius(d.id) * (1 + Math.min(0.5, imp/200));  // crecen los afectados
  });
};
window._liveResetColors = function(){
  recolorNodes();
  nodeSel.select('.n-core').attr('r',d=>computeNodeRadius(d.id));
  linkSel.style('stroke',l=>getLinkColor(l.type)).style('stroke-opacity',.22)
    .style('stroke-width',l=>Math.max(0.6,(l.w||2)*0.45));
};
window._liveSelectedNode = function(){ return selected; };
// Tiñe las CONEXIONES que transmiten el daño (ambos extremos golpeados)
window._liveTintLinks = function(impactMap, dir){
  const tint = dir==='up' ? '#2BE38B' : '#FF4D6A';
  linkSel
    .style('stroke', l=>{
      const si=impactMap.get(lid(l.source))||0, ti=impactMap.get(lid(l.target))||0;
      const f=Math.min(si,ti)/100;
      return f>0.03 ? _mixHex('#3a4664',tint,Math.min(1,f*1.6)) : getLinkColor(l.type);
    })
    .style('stroke-opacity', l=>{
      const f=Math.min(impactMap.get(lid(l.source))||0, impactMap.get(lid(l.target))||0)/100;
      return f>0.03 ? 0.25+f*0.65 : 0.10;
    })
    .style('stroke-width', l=>{
      const f=Math.min(impactMap.get(lid(l.source))||0, impactMap.get(lid(l.target))||0)/100;
      const base=Math.max(0.6,(l.w||2)*0.45);
      return f>0.03 ? base+f*2.4 : base;
    });
};

/* Etiquetas de país (vista geopolítica) */
const regionLabels = regionLayer.selectAll('text')
  .data(Object.keys(COUNTRIES)).join('text')
  .attr('class','region-label')
  .attr('text-anchor','middle')
  .style('opacity',0);

function positionRegionLabels(){
  regionLabels
    .text(k=>countryLabel(k))
    .style('fill',k=>countryColor(k))
    .attr('x',k=>COUNTRIES[k].x*W)
    .attr('y',k=>COUNTRIES[k].y*H-62);
}

/* ── VELOCIDAD (Khipus OS, 2026-10-06): el mapa NO se calcula mientras está tapado ──────────
   Antes, el arranque y CADA evento 'resize' (las ventanas del escritorio lo disparan al abrirse,
   moverse o adoptar un panel) asentaban la física aunque Khipus OS tapara el mapa: ~1,4 s de CPU
   antes de que el chat apareciera (más de 7 s en un móvil lento) y ~0,7 s más por cada ventana.
   Ahora resize() solo PIDE; _ensureMapSettled() asienta cuando el mapa se ve de verdad (pestaña
   Mapa, ventana "Grafo", al cerrar el OS) o cuando alguien necesita posiciones (jumpTo/fitToView),
   y no hace nada si el tamaño no cambió. Mientras nunca se asentó, la capa del grafo queda oculta
   (vacío honesto en vez de 949 nodos amontonados en una esquina).                              */
let _mapLaidOnce = false;   // hubo un asentado con tamaño real (las posiciones ya significan algo)
let _mapReheat = false;     // cambió algo que pide re-separar nodos (radios por capitalización en vivo)
let _mapFitPending = false; // alguien pidió encuadrar antes del primer asentado
let _mapFlyPending = null;  // {id, yFrac}: jumpTo antes del primer asentado → se vuela al mostrarse
root.style('visibility','hidden');
// ¿Khipus OS se abrirá al arrancar? Siempre, salvo "Vista clásica" en esta sesión (kh_os_classic).
let _mapOsExpected = !_mapClassicBoot;
let _mapCkSeen = 0, _mapCkOpened = false;
function _mapCkOpen(){
  const ck = window.BixbyCockpit;
  return !!(ck && typeof ck.isOpen === 'function' && ck.isOpen());
}
// Mientras el arranque aún no decidió (el OS va a abrirse pero todavía no lo hizo) el mapa cuenta
// como tapado. Se rinde: (a) si el arranque se rindió (window.__khOsGaveUp: la Cabina nunca cargó);
// (b) si el splash #boot ya no está (lo quitó el arranque o el respaldo fijo de 3 s) y pasó un respiro
// de 600 ms — con o SIN Cabina cargada: sin splash, el mapa es lo que se ve (antes, si cockpit.js no
// cargaba, el mapa quedaba en blanco de ~3 s a 12 s); (c) a los 12 s, como último tope.
// Si la Cabina llega tarde y se abre, el asentado por porciones se pausa solo (_mapCovered()).
function _mapBootWaiting(){
  if (!_mapOsExpected || _mapCkOpened) return false;
  if (_mapCkOpen()) { _mapCkOpened = true; return false; }
  const now = performance.now();
  if (now > 12000 || window.__khOsGaveUp) { _mapOsExpected = false; return false; }
  const b = document.getElementById('boot');
  if (!b || b.classList.contains('gone')) {
    if (!_mapCkSeen) _mapCkSeen = now;
    if (now - _mapCkSeen > 600) { _mapOsExpected = false; return false; }
  }
  return true;
}
// Tapado = pestaña del navegador oculta, arranque hacia el OS, o Khipus OS abierto SIN el mapa
// dentro de una de sus ventanas (adoptado en #bcp-ov).
function _mapCovered(){
  if (document.hidden) return true;
  if (_mapBootWaiting()) return true;
  if (_mapCkOpen()) {
    const ov = document.getElementById('bcp-ov');
    if (!(ov && ov.contains(svg.node()))) return true;
  }
  return false;
}
// Aviso mientras se ordena por primera vez (bilingüe; texto SVG fuera de la capa oculta).
let _mapHintEl = null, _mapHintKey = '';
function _mapHint(on){
  try{
    if(!on){ if(_mapHintEl){ _mapHintEl.remove(); _mapHintEl = null; _mapHintKey = ''; } return; }
    const en = (window.LANG || 'es') === 'en';
    const key = (en ? 'en' : 'es') + W + 'x' + H;
    if(_mapHintEl && key === _mapHintKey) return;          /* sin cambios: no tocar el SVG (evita re-maquetarlo) */
    _mapHintKey = key;
    if(!_mapHintEl) _mapHintEl = svg.append('text').attr('class','kh-map-hint').attr('text-anchor','middle')
      .style('fill','var(--ink-3)').style('font-size','12.5px').style('letter-spacing','.02em').style('pointer-events','none');
    _mapHintEl.attr('x', W/2).attr('y', H/2)
      .text(en ? `Arranging the map of ${NODES.length} companies…` : `Ordenando el mapa de ${NODES.length} empresas…`);
  }catch(e){}
}
// Primera vez que las posiciones valen (lo llama settleGraph): mostrar la capa y hacer la cámara pendiente.
function _mapLaidNow(){
  _mapReheat = false;
  if(_mapLaidOnce) return;
  _mapLaidOnce = true; _mapSettleJob = 0; _mapSettlePaused = false;
  root.style('visibility', null);
  _mapHint(false);
  const fly = _mapFlyPending; _mapFlyPending = null;
  const fit = _mapFitPending; _mapFitPending = false;
  if(fly && fly.id===selected && NODE_BY_ID[fly.id]) flyToNode(NODE_BY_ID[fly.id], fly.yFrac, 450);
  else if(fit) fitToView(450);
  setTimeout(_mapPosSave, 0);   /* recordar ya (aunque cierre enseguida); los asentados siguientes la refrescan */
}
/* MEMORIA DEL MAPA (por dispositivo): el primer orden desde cero cuesta ~80 ticks (~0,9 s; ~4 s en un
   móvil lento). Se guarda la disposición ya asentada (x relativo al ancho, y relativo al centro) y la
   próxima vez se parte de ella con un asentado corto. Se invalida sola si cambia el conjunto de
   empresas (firma de ids) o el ancho cambia demasiado. Solo vista "Flujo de Valor". Bonus: cada
   empresa aparece donde el usuario la vio la última vez. Son posiciones de dibujo, no datos. */
const MAP_POS_KEY = 'kh_map_pos_v1';
let _mapSeeded = false;
function _mapSig(){
  let h = 0;
  for(const n of NODES){ const s = String(n.id); for(let i=0;i<s.length;i++) h = (h*31 + s.charCodeAt(i)) | 0; }
  return NODES.length + ':' + h;
}
function _mapPosSave(){
  if(viewMode !== 'flow' || !(W>0) || !(H>0)) return;
  try {
    const p = {};
    for(const n of NODES){
      if(!isFinite(n.x) || !isFinite(n.y)) return;
      p[n.id] = [Math.round(n.x / W * 1e4) / 1e4, Math.round((n.y - H/2) * 10) / 10];
    }
    localStorage.setItem(MAP_POS_KEY, JSON.stringify({ v:1, sig:_mapSig(), W:Math.round(W), at:Date.now(), p:p }));
  } catch(e){}
}
let _mapPosSaveT = null;
function _mapPosSaveSoon(){ clearTimeout(_mapPosSaveT); _mapPosSaveT = setTimeout(_mapPosSave, 1200); }   /* tras cada asentado, ya quieto */
function _mapPosSeed(){
  if(viewMode !== 'flow' || !(W>0) || !(H>0)) return false;
  try {
    const c = JSON.parse(localStorage.getItem(MAP_POS_KEY) || 'null');
    if(!c || c.v !== 1 || c.sig !== _mapSig() || !c.p || !(c.W > 0)) return false;
    const ratio = W / c.W;
    if(ratio < .6 || ratio > 1.7) return false;   /* otro tamaño de pantalla: mejor ordenar de cero */
    for(const n of NODES){ const q = c.p[n.id]; if(!q || !isFinite(q[0]) || !isFinite(q[1])) return false; }
    for(const n of NODES){ const q = c.p[n.id]; n.x = q[0] * W; n.y = q[1] + H/2; n.vx = 0; n.vy = 0; }
    return true;
  } catch(e){ return false; }
}
// PRIMER asentado POR PORCIONES (≤ ~80 ms cada una; nunca una tarea larga): la ventana del mapa se abre
// fluida y se puede seguir usando la app (en un móvil eran ~4 s de pantalla congelada). Sin pintar
// hasta el final (regla "Mapa principal"); se pausa si el mapa vuelve a taparse y sigue al mostrarse.
let _mapSettleJob = 0, _mapSettleSeq = 0, _mapSettlePaused = false, _mapSettleStep = null;
/* Receta del PRIMER asentado (desde la posición inicial de d3). Medido con 937 nodos: solapes 3 y
   separación media 30 px (el arranque de antes: 4-13 solapes, 29-30 px) con 80 ticks (~0,9 s de CPU).
   Desde la memoria del mapa basta un asentado corto (solo acomoda radios/tamaño nuevos). */
const MAP_FIRST_ALPHA = .25, MAP_FIRST_TICKS = 80, MAP_SEED_ALPHA = .08, MAP_SEED_TICKS = 30;
function _mapFirstRecipe(){
  _mapSeeded = _mapPosSeed();
  return _mapSeeded ? [MAP_SEED_ALPHA, MAP_SEED_TICKS] : [MAP_FIRST_ALPHA, MAP_FIRST_TICKS];
}
/* Siguiente porción. Medido: setTimeout(0) es lo mejor; scheduler.postTask('user-blocking') encadenaba
   porciones sin dejar pintar (tareas de hasta 3,7 s en un móvil lento) — no usarlo aquí. */
function _mapPost(fn){ setTimeout(fn, 0); }
function _mapFirstSettleAsync(){
  const job = _mapSettleJob = ++_mapSettleSeq;
  _mapSettlePaused = false;
  const [alpha0, MAX_TICKS] = _mapFirstRecipe();
  try { sim.stop(); sim.alpha(alpha0); } catch(e){}
  _mapHint(true);
  let ticks = 0;
  const step = () => {
    if(job !== _mapSettleJob || _mapLaidOnce) return;      /* otro asentado (síncrono) ya lo resolvió */
    if(_mapCovered()){ _mapSettlePaused = true; return; }   /* tapado otra vez: seguir cuando se vea */
    _mapHint(true);                                         /* idioma/tamaño al día (un solo texto) */
    const t0 = performance.now();
    let minA = .001;
    try {
      minA = sim.alphaMin();
      while(ticks < MAX_TICKS && sim.alpha() > minA && performance.now() - t0 < 80){ sim.tick(); ticks++; }
    } catch(e){ ticks = MAX_TICKS; }
    if(ticks < MAX_TICKS && sim.alpha() > minA){ _mapPost(step); return; }
    try { sim.stop(); } catch(e){}
    _mapSettleJob = 0;
    _paintGraph();
    if(W>0 && H>0){ _mapLaidNow(); _mapPosSaveSoon(); }
  };
  _mapSettleStep = step;
  _mapPost(step);
}
function _ensureMapSettled(force){
  let r;
  try { r = svg.node().getBoundingClientRect(); } catch(e){ return false; }
  if(!r.width||!r.height) return false;   /* oculto (ventana minimizada / pestaña cerrada): no re-centrar en 0×0 */
  if(!force && _mapCovered()) return false;
  if(_liveTick) return _mapLaidOnce;       /* arrastrando: la física ya corre en vivo */
  const sized = (r.width!==W || r.height!==H);
  if(_mapLaidOnce && !sized && !_mapReheat) return true;   /* nada cambió: cero trabajo */
  if(sized){ W=r.width; H=r.height; setForces(); positionRegionLabels(); }
  if(!_mapLaidOnce){
    /* De una vez (síncrono) si quien llama necesita posiciones YA, o si el mapa es la pantalla de
       arranque (vista clásica) y el splash todavía lo tapa: así aparece listo al desvanecerse. */
    const bootEl = document.getElementById('boot');
    if(force || (bootEl && !bootEl.classList.contains('gone'))){
      _mapSettleJob = 0;
      if(_mapClassicBoot && !force) settleGraph(.15, 60);   /* ya calentado por d3 (vista clásica): lo de siempre */
      else { const rc = _mapFirstRecipe(); settleGraph(rc[0], rc[1]); }
      return _mapLaidOnce;
    }
    if(_mapSettleJob){
      if(sized) _mapHint(true);
      if(_mapSettlePaused && _mapSettleStep){ _mapSettlePaused = false; _mapPost(_mapSettleStep); }
    } else _mapFirstSettleAsync();
    return false;
  }
  if(sized) settleGraph(.15, 60);  /* Reasentado LIGERO: girar el móvil, barra del navegador, ventana nueva */
  else settleGraph(.12, 60);       /* radios nuevos (capitalización en vivo): solo separar solapes */
  return true;
}
window._ensureMapSettled = _ensureMapSettled;
window._mapState = function(){
  return { laid:_mapLaidOnce, reheat:_mapReheat, covered:_mapCovered(), bootWaiting:_mapBootWaiting(),
           osExpected:_mapOsExpected, settling:!!_mapSettleJob, paused:_mapSettlePaused, seeded:_mapSeeded,
           W:W, H:H, hidden: root.style('visibility')==='hidden' };
};
function resize(){ _ensureMapSettled(false); }

const linkSel = linkLayer.selectAll('line').data(LINKS).join('line')
  .attr('stroke-width',d=>Math.max(.6,d.w*.45))
  .style('stroke',d=>getLinkColor(d.type)).style('stroke-opacity',.22).attr('fill','none');

const nodeSel = nodeLayer.selectAll('g').data(NODES).join('g')
  .style('cursor','pointer')
  .on('click',(e,d)=>{
    e.stopPropagation();
    if(pathfinderMode){ pathClick(d.id); return; } /* v7 · M4 */
    if(e.altKey){ activateStress(d.id); return; }
    selectNode(d.id);
  })
  .on('mouseenter',(e,d)=>{ hovered=d.id; if(!selected&&!stressId){growCore(d,true);refreshStyles();} })
  .on('mouseleave',(e,d)=>{ hovered=null; if(!selected&&!stressId){growCore(d,false);refreshStyles();} });

// ETIQUETAS: solo las ~LBL_MAX empresas más grandes (+ las "big") muestran su nombre. Antes era
// "radio ≥ 13", pero con la capitalización en vivo cientos de nodos pasan ese radio y el mapa se
// llenaría de texto (y de trabajo de pintado). El umbral se recalcula al llegar las caps.
const LBL_MAX = 90;
let _lblMinR = 13;
function _recalcLblMin(){
  try{
    const rs = NODES.map(n=>computeNodeRadius(n.id)).sort((a,b)=>b-a);
    _lblMinR = Math.max(13, rs[Math.min(rs.length-1, LBL_MAX-1)] || 13);
  }catch(e){ _lblMinR = 13; }
}
function _lblOn(d){ return !!d.big || computeNodeRadius(d.id) >= _lblMinR; }
window._lblOn = _lblOn;
function growCore(d,on){
  nodeSel.filter(n=>n.id===d.id).select('.n-core')
    .attr('r',on?computeNodeRadius(d.id)+3:computeNodeRadius(d.id));
  nodeSel.filter(n=>n.id===d.id).select('.node-label')
    .classed('lbl-off', !on && !_lblOn(d));
}

function ringStroke(d){
  return d.preipo?'var(--preipo)':d.port==='C1+C2'?'var(--violet)':d.port==='C1'?'var(--gold)':d.port==='C2'?'var(--blue)':'transparent';
}

nodeSel.append('circle')
  .attr('class','n-ring')
  .attr('r',d=>computeNodeRadius(d.id)+4)
  .attr('fill','none')
  .style('stroke',d=>ringStroke(d))
  .attr('stroke-width',d=>(d.preipo||d.port)?2.2:0)
  .attr('stroke-dasharray',d=>d.preipo?'2 2.5':d.port==='C1+C2'?'4 2.5':'none');

nodeSel.append('circle')
  .attr('class','n-core')
  .attr('r',d=>computeNodeRadius(d.id))
  .attr('fill',d=>nodeFill(d))
  .attr('fill-opacity',.9)
  .style('stroke','var(--surface)').attr('stroke-width',1.5)
  .style('transition','r .12s');

/* v7 · M2: anillo de riesgo geopolítico (critical/high) */
nodeSel.filter(d=>{ const r=NODE_META[d.id]?.risk; return r==='critical'||r==='high'; })
  .append('circle')
  .attr('class',d=>'risk-ring'+(NODE_META[d.id].risk==='critical'?' risk-ring-critical':''))
  .attr('r',d=>computeNodeRadius(d.id)+8)
  .attr('fill','none')
  .style('stroke',d=>NODE_META[d.id].risk==='critical'?'var(--danger)':'var(--gold)')
  .attr('stroke-width',1.5)
  .attr('stroke-dasharray','4 3')
  .attr('opacity',.7);

nodeSel.filter(d=>d.preipo).append('text')
  .attr('class','preipo-mark')
  .text('IPO')
  .attr('text-anchor','middle').attr('dy',3)
  .style('font-size','7px').style('font-weight','700').style('letter-spacing','.02em')
  .style('fill','var(--surface)').style('pointer-events','none');

nodeSel.filter(d=>d.risk).append('text')
  .attr('class','risk-mark')
  .text('⚠')
  .attr('text-anchor','middle').attr('dy',d=>-(computeNodeRadius(d.id)+8))
  .style('font-size','11px').style('pointer-events','none');

nodeSel.append('text')
  .attr('class',d=>'node-label'+(d.big?' big':''))
  .text(d=>d.label.length>15?d.label.slice(0,14)+'…':d.label)
  .attr('text-anchor','middle')
  .attr('dy',d=>computeNodeRadius(d.id)+13)
  .style('fill','var(--ink)')
  /* VELOCIDAD (2026-10-03, medido): las etiquetas de nodos chicos ANTES quedaban
     con opacity:0 — invisibles pero el navegador igual las maquetaba y pintaba
     (~800 textos con halo en cada zoom/pan). display:none las saca del render. */
  .classed('lbl-off', d => !_lblOn(d));

// Capitalización EN VIVO → re-dimensiona los nodos (sin re-maquetar todo el mapa): radios,
// anillos, marcas y etiquetas; la física solo separa los que ahora se solapan (settle corto).
let _capResizeT = null;
function _resizeNodesByCap(){
  _recalcLblMin();
  nodeSel.select('.n-core').attr('r',d=>computeNodeRadius(d.id)+(d.id===selected?3:0));
  nodeSel.select('.n-ring').attr('r',d=>computeNodeRadius(d.id)+4);
  nodeSel.select('.risk-ring').attr('r',d=>computeNodeRadius(d.id)+8);
  nodeSel.select('.risk-mark').attr('dy',d=>-(computeNodeRadius(d.id)+8));
  nodeSel.select('.node-label').attr('dy',d=>computeNodeRadius(d.id)+13).classed('lbl-off', d=>!_lblOn(d) && d.id!==selected && d.id!==hovered);
  try{ sim.force('collide').radius(d=>computeNodeRadius(d.id)+10); }catch(e){}
  if(_liveTick) return;
  // Khipus OS: si el mapa está tapado, la separación de solapes espera a que se vea (no 60 ticks a ciegas).
  _mapReheat = true;
  _ensureMapSettled(false);
}
window._resizeNodesByCap = _resizeNodesByCap;
window.addEventListener('khipu:livecaps', ()=>{ clearTimeout(_capResizeT); _capResizeT = setTimeout(_resizeNodesByCap, 400); });
_recalcLblMin();
nodeSel.select('.node-label').classed('lbl-off', d => !_lblOn(d));

nodeSel.call(d3.drag()
  .on('start',(e,d)=>{if(!e.active){_liveTick=true;sim.alphaTarget(.2).restart();}d.fx=d.x;d.fy=d.y;})
  .on('drag',(e,d)=>{d.fx=e.x;d.fy=e.y;})
  .on('end',(e,d)=>{if(!e.active){sim.alphaTarget(0);_liveTick=false;settleGraph(.08,40);}d.fx=null;d.fy=null;}));

/* ── Rendimiento del mapa: la física se calcula SIN dibujar ────────────────
   Antes cada tick escribía ~11.000 atributos al DOM (2.526 enlaces × 4 +
   949 nodos), y la simulación tarda ~150 ticks en asentarse → ~1,6 millones
   de escrituras cada vez que arrancaba: al cargar, al filtrar y al arrastrar.
   En un teléfono eso es lo que se sentía lento.

   Ahora la simulación se adelanta en memoria (sim.tick() NO dispara el evento
   'tick' en d3, justo para esto) y se pinta UNA vez con las posiciones ya
   finales. Excepción: mientras arrastras SÍ se pinta en vivo, porque ahí el
   movimiento es la respuesta a tu dedo. Mismo resultado visual, sin el baile
   inicial.                                                                  */
function _paintGraph(){
  linkSel.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y)
         .attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
  nodeSel.attr('transform',d=>`translate(${d.x},${d.y})`);
  if(window._mapTimePaint) window._mapTimePaint();   /* capa ⚡ Eventos */
}
let _liveTick = false;   // solo true mientras se arrastra un nodo
sim.on('tick',()=>{ if(_liveTick) _paintGraph(); });

function settleGraph(alpha=.4, maxTicks=200){
  try{
    sim.stop();
    sim.alpha(alpha);
    const minA = sim.alphaMin();
    for(let i=0;i<maxTicks && sim.alpha()>minA;i++) sim.tick();
    sim.stop();
  }catch(e){ /* si algo falla, al menos pintamos lo que haya */ }
  _paintGraph();
  if(W>0 && H>0){ _mapLaidNow(); _mapPosSaveSoon(); }   /* posiciones reales → mostrar la capa y recordarlas */
}
window.settleGraph = settleGraph;

svg.on('click',()=>{ if(stressId||pathfinderMode) return; deselect(); });

/* ===================== v7 · M7: tooltip enriquecido ===================== */
const tooltipEl=document.getElementById('hover-tooltip');
function positionTooltip(event){
  const tw=tooltipEl.offsetWidth, th=tooltipEl.offsetHeight;
  const mx=event.clientX, my=event.clientY;
  tooltipEl.style.left=(mx+16+tw>window.innerWidth ? mx-tw-12 : mx+16)+'px';
  tooltipEl.style.top =(my+8+th>window.innerHeight ? my-th-8 : my+8)+'px';
}
nodeSel.on('mouseover.tooltip',(event,d)=>{
  if(pathfinderMode) return;
  const meta=NODE_META[d.id]||{};
  const out=LINKS.filter(l=>lid(l.source)===d.id).length;
  const inp=LINKS.filter(l=>lid(l.target)===d.id).length;
  const riskColor=meta.risk==='critical'?'var(--danger)':meta.risk==='high'?'var(--gold)':'var(--ink-3)';
  tooltipEl.style.display='block';
  tooltipEl.innerHTML=`
    <div style="display:flex;align-items:center;gap:7px;margin-bottom:6px">
      <span style="width:10px;height:10px;border-radius:50%;background:${catColor(d.cat)};flex-shrink:0"></span>
      <strong>${esc(d.label)}</strong>
      <span style="font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--ink-3)">${esc((d.ticker||'').split(' · ')[0])}</span>
    </div>
    ${(meta.revenue_ttm_usd_b!=null||meta.revenue_2025)?(function(){
      // 2026-10-05: ingresos de los últimos 12 meses EN VIVO (KhipuLiveFund) antes que la cifra 2025 del catálogo
      const rv=meta.revenue_ttm_usd_b, liv=rv!=null&&isFinite(+rv);
      const rt=liv?('$'+(+rv>=1000?(+rv/1000).toFixed(2)+'T':(+rv>=10?Math.round(+rv):(+rv).toFixed(1))+'B')+' <span style="color:#22c55e" title="'+(LANG==='en'?'live · last 12 months':'en vivo · últimos 12 meses')+'">●</span>'):esc(meta.revenue_2025);
      const em=meta.employees?meta.employees.toLocaleString()+(meta.employees_live?' <span style="color:#22c55e">●</span>':''):'—';
      return `<div style="font-size:11px;color:var(--ink-2)">💰 ${rt} &nbsp;·&nbsp; 👥 ${em}</div>`;})():''}
    <div style="font-size:11px;color:var(--ink-3);margin-top:4px">↑ ${inp} ${t('tt_sup')} &nbsp;·&nbsp; ↓ ${out} ${t('tt_cli')}</div>
    ${meta.risk&&meta.risk!=='low'?`<div style="font-size:10px;color:${riskColor};margin-top:4px;font-weight:600;text-transform:uppercase">⚠ ${t('tt_risk')}: ${esc(meta.risk)}</div>`:''}
    ${(function(){try{const nrs=computeNRS(d.id);const nc=nrs<30?'#22c55e':nrs<60?'#f59e0b':'#ef4444';return `<div style="font-size:10px;margin-top:4px;display:flex;align-items:center;gap:5px"><span style="color:var(--ink-3)">NRS</span><span style="font-weight:700;color:${nc}">${nrs}</span><span style="color:var(--ink-3)">/100</span></div>`;}catch(e){return '';}})()}
  `;
  positionTooltip(event);
});
nodeSel.on('mousemove.tooltip',positionTooltip);
nodeSel.on('mouseout.tooltip',()=>{ tooltipEl.style.display='none'; });
nodeSel.on('mousedown.tooltip',()=>{ tooltipEl.style.display='none'; });

/* ===================== v7 · M4: pathfinder (ruta más corta) ===================== */
function bfsPath(srcId,dstId){
  const visited={[srcId]:null};
  const queue=[srcId];
  while(queue.length){
    const curr=queue.shift();
    if(curr===dstId){
      const path=[];
      let node=dstId;
      while(node!==null){ path.unshift(node); node=visited[node]; }
      return path;
    }
    LINKS.forEach(l=>{
      if(lid(l.source)!==curr) return;
      const tg=lid(l.target);
      if(!(tg in visited)){ visited[tg]=curr; queue.push(tg); }
    });
  }
  return null;
}
function setPathText(html){
  document.getElementById('path-text').innerHTML=html;
  document.getElementById('path-banner').classList.add('show');
}
function clearPath(silent){
  pathActive=false; pathSrc=null; pathDst=null; pathfinderMode=false;
  pathNodes=new Set(); pathLinkKeys=new Set();
  document.getElementById('graph').classList.remove('pathfinder-mode');
  document.getElementById('pathfinder-btn').classList.remove('pf-active');
  document.getElementById('path-banner').classList.remove('show');
  nodeSel.select('.n-core').style('stroke','var(--surface)').attr('stroke-width',1.5);
  linkSel.attr('stroke-width',d=>Math.max(.6,d.w*.45));
  if(!silent) refreshStyles();
}
function pathClick(id){
  if(!pathSrc){
    pathSrc=id;
    nodeSel.select('.n-core')
      .style('stroke',d=>d.id===id?'#0F8C5F':'var(--surface)')
      .attr('stroke-width',d=>d.id===id?3:1.5);
    setPathText(t('pf_pick_dst')+' · <b>'+esc(NODE_BY_ID[id].label)+'</b> →');
    return;
  }
  if(id===pathSrc) return;
  pathDst=id;
  const path=bfsPath(pathSrc,pathDst);
  pathfinderMode=false;
  document.getElementById('graph').classList.remove('pathfinder-mode');
  if(!path){
    setPathText('⚠ '+t('pf_nopath').replace('{a}','<b>'+esc(NODE_BY_ID[pathSrc].label)+'</b>').replace('{b}','<b>'+esc(NODE_BY_ID[pathDst].label)+'</b>'));
    pathSrc=null; pathDst=null;
    document.getElementById('pathfinder-btn').classList.remove('pf-active');
    nodeSel.select('.n-core').style('stroke','var(--surface)').attr('stroke-width',1.5);
    return;
  }
  pathActive=true;
  pathNodes=new Set(path);
  pathLinkKeys=new Set();
  for(let i=0;i<path.length-1;i++) pathLinkKeys.add(path[i]+'>'+path[i+1]);
  setPathText('<span class="pb-route">'+path.map(p=>esc(NODE_BY_ID[p].label)).join(' → ')+'</span> <b>('+(path.length-1)+' '+t('pf_hops')+')</b>');
  refreshStyles();
}
document.getElementById('pathfinder-btn').onclick=()=>{
  if(pathfinderMode||pathActive){ clearPath(); return; }
  if(stressId) clearStress();
  if(selected) deselect();
  pathfinderMode=true; pathSrc=null; pathDst=null; pathActive=false;
  document.getElementById('graph').classList.add('pathfinder-mode');
  document.getElementById('pathfinder-btn').classList.add('pf-active');
  setPathText(t('pf_pick_src'));
};
document.getElementById('path-clear').onclick=()=>clearPath();

/* ===================== Estilos unificados (stress > selección > filtros) ===================== */
function neighborsOf(id){
  const ids=new Set([id]);
  LINKS.forEach(l=>{
    const s=lid(l.source), t=lid(l.target);
    if(s===id||t===id){ids.add(s);ids.add(t);}
  });
  return ids;
}

function passesFilters(d){
  if(!d) return false;
  let vis=true;
  if(activePF) vis = inPortfolio(d, activePF);
  if(activeCat) vis = vis && d.cat===activeCat;
  if(activeCountry) vis = vis && d.country===activeCountry;
  if(searchTerm) vis = vis && (d.label+' '+d.ticker+' '+d.id).toLowerCase().includes(searchTerm);
  return vis;
}

/* v7 · M10: cache de filtros — se recalcula solo cuando cambia un filtro */
let _filterCache=null;
function invalidateFilterCache(){ _filterCache=null; }
function buildFilterCache(){
  if(_filterCache) return _filterCache;
  _filterCache=new Map();
  NODES.forEach(n=>_filterCache.set(n.id,passesFilters(n)));
  return _filterCache;
}

/* v7 · M2: los anillos de riesgo solo se muestran sin filtros/selección activos */
function updateRiskRings(){
  const show = !activeCat && !activePF && !activeCountry && !searchTerm && !stressId && !selected && !pathActive;
  nodeSel.selectAll('.risk-ring').style('display', show?null:'none');
}

function refreshStyles(){ _refreshStylesCore(); updateRiskRings(); }
window.refreshStyles = refreshStyles;

function _refreshStylesCore(){
  if(pathActive){
    nodeSel.classed('node-collapsed',false);
    nodeSel.select('.n-core').classed('failed',false);
    nodeSel.select('.n-ring').classed('failed-ring',false);
    nodeSel.style('opacity', d=>pathNodes.has(d.id)?1:.08);
    nodeSel.select('.n-core')
      .style('stroke',d=>pathNodes.has(d.id)?'var(--gold)':'var(--surface)')
      .attr('stroke-width',d=>pathNodes.has(d.id)?3:1.5);
    linkSel
      .style('stroke', l=>isPathLink(l)?'var(--gold)':getLinkColor(l.type))
      .style('stroke-opacity', l=>isPathLink(l)?.95:.04)
      .attr('stroke-width', l=>isPathLink(l)?3.5:Math.max(.6,l.w*.45));
    return;
  }
  if(stressId){
    /* gris "colapsada" SOLO para las muy golpeadas (≥ STRESS_DEAD_PCT); las demás afectadas se atenúan según su %
       (antes una empresa al 1 % se veía igual de muerta que Nvidia al 100 %) */
    const sp=id=>stressPct.get(id)||0;
    nodeSel.classed('node-collapsed', d=>d.id!==stressId && sp(d.id)>=STRESS_DEAD_PCT)
      .style('opacity', d=> d.id===stressId?1 : sp(d.id)>=STRESS_DEAD_PCT? .1
        : stressAffected.has(d.id)? Math.max(.3, .92-sp(d.id)/STRESS_DEAD_PCT*.6) : .92);
    nodeSel.select('.n-core').classed('failed', d=>d.id===stressId);
    nodeSel.select('.n-ring').classed('failed-ring', d=>d.id===stressId);
    linkSel
      .style('stroke', l=> lid(l.source)===stressId ? 'var(--danger)' : 'var(--line-2)')
      .style('stroke-opacity', l=>{
        const s=lid(l.source), t=lid(l.target);
        if(s===stressId) return .7;
        if(stressAffected.has(s)||stressAffected.has(t)) return .04;
        return .28;
      });
    return;
  }
  nodeSel.classed('node-collapsed', false);
  nodeSel.select('.n-core').classed('failed', false);
  nodeSel.select('.n-ring').classed('failed-ring', false);

  /* ⏱ tiempo en el mapa (engine/maptime.js): lo que aún no existía en la fecha se apaga */
  const tm = (window.KhipuMapTime && window.KhipuMapTime.active) ? window.KhipuMapTime : null;
  const focus = selected || hovered;
  if(focus && NODE_BY_ID[focus]){
    const nb=neighborsOf(focus);
    nodeSel.style('opacity', n=> tm && !tm.nodeOk(n.id) ? .05 : nb.has(n.id)?1:.13);
    linkSel
      .style('stroke', l=>(lid(l.source)===focus||lid(l.target)===focus)?nodeFill(NODE_BY_ID[focus]):getLinkColor(l.type))
      .style('stroke-opacity', l=> tm && !tm.linkOk(l) ? .015 : (lid(l.source)===focus||lid(l.target)===focus)?.85:.05);
    return;
  }
  const anyFilter = activePF||activeCat||activeCountry||searchTerm;
  let baseOp = viewMode==='geo' ? .14 : .35;
  const cache = buildFilterCache(); /* v7 · M10 */
  if(tm && tm.events) baseOp = .1;   /* con ⚡ Eventos, los vínculos normales ceden protagonismo */
  nodeSel.style('opacity', d=> tm && !tm.nodeOk(d.id) ? .05 : cache.get(d.id)?1:.12);
  linkSel.style('stroke',l=>getLinkColor(l.type))
    .style('stroke-opacity', l=>{
      if(tm && !tm.linkOk(l)) return .015;
      const ltOk = !activeLinkType || l.type===activeLinkType;
      if(!ltOk) return .04;
      if(!anyFilter) return baseOp;
      return (cache.get(lid(l.source))&&cache.get(lid(l.target)))?.45:.05;
    });
}

function selectNode(id){
  if(!NODE_BY_ID[id]) return;
  id = _canonId(id);   /* revisión G1c: alias → canónico (si no, el panel salía sin proveedores ni clientes) */
  if(pathActive||pathfinderMode) clearPath(true); /* v7 · M4 */
  selected=id; window._selectedNode=id; /* contexto para el Command Center */
  nodeSel.select('.n-core').attr('r',d=>d.id===id?computeNodeRadius(d.id)+3:computeNodeRadius(d.id));
  refreshStyles();
  renderDetail(id);
}

function deselect(){
  selected=null; hovered=null; window._selectedNode=null;
  nodeSel.select('.n-core').attr('r',d=>computeNodeRadius(d.id));
  refreshStyles();
  document.getElementById('detail').style.display='none';
  document.getElementById('panel-empty').style.display='block';
  if(window.V8feed) window.V8feed.load();   /* 📡 refresca como mucho 1/min */
}

/* ===================== Stress-Test (Simulador de Colapso) ===================== */
/* Paso 13 INFRA_OPERATIVA (2026-10-13): el banner de colapso usa el motor ÚNICO del servidor
   (/api/hot/impact vía engine/hotclient.js, window.KhipuHot) — el MISMO número que el X-Ray, la Cabina,
   la voz y los Insights. Aquí había una cascada binaria propia (umbral 50 % / peso crítico 5) que daba
   otra cifra (PROP-03): se borró. Afectadas = las que reciben ≥1 % del golpe (reach_1 del servidor). */
let stressSeq=0, stressRes=null, stressPct=new Map();
const STRESS_DEAD_PCT=40;   /* % del golpe desde el que el mapa pinta la empresa como colapsada */

/* Texto del banner — distingue el caso resiliente (0 afectadas) y dice de qué versión del grafo sale */
function stressText(d){
  const r=stressRes;
  if(!r) return t('st_wait').replace('{n}',`<b>${esc(d.label)}</b>`);
  if(!r.ok) return t('st_err').replace('{n}',`<b>${esc(d.label)}</b>`).replace('{e}',esc(r.error||''));
  const stamp=(window.KhipuHot&&window.KhipuHot.stampHTML)?' '+window.KhipuHot.stampHTML(r.view):'';
  const c=r.reach_1;
  if(c===0) return t('st_msg_safe').replace('{n}',`<b>${esc(d.label)}</b>`)+stamp;
  const pct=Math.round(c/Math.max(1,NODES.length-1)*100);
  return t('st_msg').replace('{n}',`<b>${esc(d.label)}</b>`).replace('{c}',`<b>${c}</b>`).replace('{p}',pct)+stamp;
}

function activateStress(id){
  const d=NODE_BY_ID[id]; if(!d) return;
  stressId=id;
  selected=id; window._selectedNode=id;
  stressAffected=new Set(); stressRes=null; stressPct=new Map();
  const seq=++stressSeq;
  nodeSel.select('.n-core').attr('r',n=>n.id===id?computeNodeRadius(n.id)+3:computeNodeRadius(n.id));
  document.getElementById('stress-text').innerHTML=stressText(d);
  document.getElementById('stress-banner').classList.add('show');
  refreshStyles();
  renderDetail(id);
  if(typeof onStressMobile==='function') onStressMobile();
  const p=window.KhipuHot?window.KhipuHot.simulate({targets:[id],kind:'collapse',severity:100})
    :Promise.resolve({ok:false,error:LANG==='en'?'Impact engine unavailable.':'Motor de impacto no disponible.'});
  return p.then(r=>{
    if(seq!==stressSeq||stressId!==id) return r;   /* llegó tarde: ya se simula otra empresa */
    stressRes=r;
    stressAffected=new Set(r.ok?r.victims.filter(v=>v.pct>=1).map(v=>v.id):[]);
    stressPct=new Map(r.ok?r.victims.filter(v=>v.pct>=1).map(v=>[v.id,v.pct]):[]);
    document.getElementById('stress-text').innerHTML=stressText(d);
    refreshStyles();
    return r;
  });
}

function clearStress(){
  stressId=null; stressAffected=new Set(); stressRes=null; stressPct=new Map(); stressSeq++;
  document.getElementById('stress-banner').classList.remove('show');
  refreshStyles();
  if(selected) renderDetail(selected);
}

/* v7: chips de tipo de vínculo — construidos dinámicamente (faltaban en el markup v6) */
function ltLabel(tp){ return t('lt_'+(tp||'all')); }
const ltChipsEl=document.getElementById('lt-chips');
const LT_ORDER=['','supply','fab','license','cloud','invest','deploy','partner'];
function buildLtChips(){
  ltChipsEl.innerHTML='';
  LT_ORDER.forEach(tp=>{
    const b=document.createElement('button');
    b.className='chip lt-chip'+(activeLinkType===tp?' active':'');
    b.dataset.lt=tp;
    b.innerHTML=(tp?`<span class="dot" style="background:${getLinkColor(tp)}"></span>`:'')+`<span class="lt-txt">${ltLabel(tp)}</span>`;
    b.onclick=()=>{
      activeLinkType=(activeLinkType===tp&&tp!=='')?'':tp;
      document.querySelectorAll('.lt-chip').forEach(x=>x.classList.toggle('active',x.dataset.lt===activeLinkType));
      refreshStyles();
    };
    ltChipsEl.appendChild(b);
  });
}

document.getElementById('stress-restore').onclick=clearStress;

window.addEventListener('keydown',e=>{
  if(e.key!=='Escape') return;
  if(suggEl.classList.contains('show')){ closeSugg(); return; }
  if(pathfinderMode||pathActive){ clearPath(); return; } /* v7 · M4 */
  if(stressId){ clearStress(); return; }
  if(selected) deselect();
});

/* ===================== Cámara ===================== */
/* Khipus OS: la cámara necesita posiciones reales. Si el mapa nunca se asentó (estuvo tapado),
   se asienta ahora si se ve; si sigue tapado, el encuadre/vuelo queda pendiente y se hace al mostrarse. */
function fitToView(dur=500){
  _ensureMapSettled(false);
  if(!_mapLaidOnce){ _mapFitPending = true; return; }
  if(!W||!H) return;
  const xs=NODES.map(n=>n.x).filter(v=>v!=null), ys=NODES.map(n=>n.y).filter(v=>v!=null);
  if(!xs.length) return;
  const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
  const pad=50, gw=(maxX-minX)||1, gh=(maxY-minY)||1;
  const scale=Math.min((W-pad*2)/gw,(H-pad*2)/gh,1.5);
  const tx=W/2-scale*(minX+maxX)/2, ty=H/2-scale*(minY+maxY)/2;
  svg.transition().duration(dur).call(zoom.transform, d3.zoomIdentity.translate(tx,ty).scale(scale));
}

function flyToNode(d,yFrac=0.5,dur=650){
  if(!d) return;
  _ensureMapSettled(false);
  if(!_mapLaidOnce){ _mapFlyPending = { id:d.id, yFrac:yFrac }; return; }
  if(d.x==null) return;
  const t=d3.zoomTransform(svg.node());
  const k=Math.max(Math.min(t.k,1.6),1.05);
  const tx=W/2-k*d.x, ty=H*yFrac-k*d.y;
  svg.transition().duration(dur).ease(d3.easeCubicInOut)
     .call(zoom.transform, d3.zoomIdentity.translate(tx,ty).scale(k));
}

window.jumpTo=function(id){
  const d=NODE_BY_ID[id]; if(!d) return;
  flyToNode(d, isMobile()?0.22:0.5);
  selectNode(id);
};

/* ===================== Panel de detalle ===================== */
function pfLabel(p){return p==='C1+C2'?t('pf_both'):p==='C1'?t('pf_c1'):p==='C2'?t('pf_c2'):'';}
function pfClass(p){return p==='C1+C2'?'both':p==='C1'?'c1':p==='C2'?'c2':'';}
const esc=s=>String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
window.esc = esc;
const isPreipoTicker=t=>/pre-ipo/i.test(t||'');

function fmtMargin(m){
  if(m==null) return {v:'—', neg:false, sub:t('m_pre')};
  const pct=Math.round(m*100);
  return {v:pct+'%', neg:m<0, sub:m<0?t('m_burn'):t('m_op')};
}

/* v7 · M3: vecinos a profundidad 2 (cadena de suministro visual) */
function getDepth2(id,direction){
  const direct = direction==='up'
    ? LINKS.filter(l=>lid(l.target)===id).map(l=>lid(l.source))
    : LINKS.filter(l=>lid(l.source)===id).map(l=>lid(l.target));
  const uniqDirect=[...new Set(direct)];
  const depth2=new Set();
  uniqDirect.slice(0,4).forEach(nid=>{
    const d2 = direction==='up'
      ? LINKS.filter(l=>lid(l.target)===nid).map(l=>lid(l.source))
      : LINKS.filter(l=>lid(l.source)===nid).map(l=>lid(l.target));
    d2.slice(0,2).forEach(x=>{ if(x!==id && !uniqDirect.includes(x)) depth2.add(x); });
  });
  return { direct: uniqDirect.slice(0,4), depth2: [...depth2].slice(0,3) };
}

function renderDetail(id){
  id = _canonId(id);
  const d=NODE_BY_ID[id];
  const col=catColor(d.cat);
  const upstream=[], downstream=[];
  LINKS.forEach(l=>{
    const s=lid(l.source), t=lid(l.target);
    if(t===id) upstream.push({node:NODE_BY_ID[s],rel:l.rel,type:l.type});
    if(s===id) downstream.push({node:NODE_BY_ID[t],rel:l.rel,type:l.type});
  });

  const TYPE_LABELS = {supply:'Suministro',fab:'Fab',license:'Licencia IP',cloud:'Cloud',invest:'Inversión',deploy:'Deploy',partner:'Partner'};
  const connHTML=(arr,dir)=>{
    if(!arr.length) return '';
    const title = dir==='up'
      ? `<span class="arrow" style="color:${col}">↓</span> ${t('d_up')} <span class="cnt">${arr.length}</span>`
      : `<span class="arrow" style="color:${col}">↑</span> ${t('d_down')} <span class="cnt">${arr.length}</span>`;
    const items=arr.map(({node,rel,type})=>{
      const tag = node.preipo?`<span class="pf-tag ipo">${isPreipoTicker(node.ticker)?'PRE-IPO':'PRIVADA'}</span>`
        : node.port?`<span class="pf-tag ${pfClass(node.port)}">${node.port}</span>`:'';
      return `<div class="conn-item" onclick="jumpTo('${node.id}')">
        <span class="cdot" style="background:${catColor(node.cat)}"></span>
        <div class="ctext">
          <div class="cname">${esc(node.label)} <span class="ctk">${esc(node.ticker.split(' · ')[0])}</span> ${tag}</div>
          <div class="crel"><span class="ctype-dot" style="background:${getLinkColor(type||'supply')}"></span>${esc(rel)}</div>
        </div>
      </div>`;
    }).join('');
    return `<div class="conn-group"><div class="conn-h">${title}</div>${items}</div>`;
  };

  const pf = d.port ? `<span class="badge badge-pf ${pfClass(d.port)}">★ ${pfLabel(d.port)}</span>` : '';
  // Carteras simuladas propias (reemplazan C1/C2 mediano/largo — pedido de Fabrizio)
  const pfBtns = `<div style="display:flex;gap:6px;margin:8px 0 2px;align-items:center;flex-wrap:wrap">
    <button onclick="window.addToPortfolio&&window.addToPortfolio('${d.id}')" title="${LANG==='en'?'Add to one of your simulated portfolios':'Añadir a una de tus carteras simuladas'}" style="font-size:11px;padding:5px 13px;border-radius:20px;cursor:pointer;font-weight:700;border:1px solid #3DE0C8;background:transparent;color:#3DE0C8;transition:all .12s">💼 ${LANG==='en'?'Add to portfolio':'Añadir a cartera'}</button></div>`;
  const preipoBadge = d.preipo
    ? `<span class="badge badge-preipo">◌ ${isPreipoTicker(d.ticker)?t('b_preipo'):t('b_priv')}</span>` : '';
  const riskBadge = d.risk ? `<span class="badge badge-risk">⚠ ${t('b_risk')}</span>` : '';
  const m=fmtMargin(d.margin);


  // NODE_META extra data
  const meta = NODE_META[id] || {};
  /* la rejilla sale también para toda empresa que COTIZA aunque no tenga
     ficha extendida (Mizuho no tenía `founded` → ni siquiera había dónde
     mostrar su capitalización en vivo) */
  const _en = LANG==='en';
  const metaHTML = (meta.founded || d.mkt) ? `
    <div class="meta-grid">
      <div class="meta-item"><div class="meta-l">${_en?'Founded':'Fundada'}</div><div class="meta-v">${meta.founded||'—'}</div></div>
      <div class="meta-item"><div class="meta-l">${_en?'Employees':'Empleados'}</div><div class="meta-v" id="d-emp" data-live="employees">${meta.employees?esc(isFinite(+meta.employees)?(+meta.employees).toLocaleString(_en?'en-US':'es-ES'):meta.employees):'—'}</div></div>
      <div class="meta-item"><div class="meta-l" id="d-rev-l" data-live-label="revenue">${_en?'Revenue 2025':'Ingresos 2025'}</div><div class="meta-v" id="d-rev" data-live="revenue">${esc(meta.revenue_2025||'—')}</div></div>
      <div class="meta-item"><div class="meta-l">Mkt Cap</div><div class="meta-v" id="d-mcap" data-live="mcap">${meta.mktcap_b?(isFinite(+meta.mktcap_b)?'$'+meta.mktcap_b+'B'+(window.liveCapDot?window.liveCapDot(meta):''):esc(meta.mktcap_b)):(d.mkt?'—':(LANG==='en'?'Private':'Privada'))}</div></div>
    </div>
    ${meta.geo_risk?`<div class="geo-risk-box"><span class="geo-icon">🌐</span>${esc(meta.geo_risk)}</div>`:''}
    ${meta.key_clients&&meta.key_clients.length?`<div class="key-clients-box"><div class="kc-l">${_en?'Key clients':'Clientes clave'}</div><div class="kc-tags">${meta.key_clients.map(c=>`<span class="kc-tag">${esc(c)}</span>`).join('')}</div></div>`:''}
  ` : '';

  // Connection type breakdown
  const upByType = {}, downByType = {};
  upstream.forEach(({node,rel,type})=>{
    const tp = type||'supply';
    if(!upByType[tp]) upByType[tp]=[];
    upByType[tp].push({node,rel,type:tp});
  });
  downstream.forEach(({node,rel,type})=>{
    const tp = type||'supply';
    if(!downByType[tp]) downByType[tp]=[];
    downByType[tp].push({node,rel,type:tp});
  });

  /* v7 · M3: posición en la cadena (profundidad 2) */
  const up2=getDepth2(id,'up'), down2=getDepth2(id,'down');
  const chainPill=(nid,cls)=>{ const n=NODE_BY_ID[nid]; return n?`<button class="chain-pill ${cls}" onclick="jumpTo('${n.id}')" title="${esc(n.label)}">${esc(n.label)}</button>`:''; };
  const chainCol=(ids,cls)=>`<div class="chain-col">${ids.map(i=>chainPill(i,cls)).join('')}</div>`;
  const chainArrow='<div class="chain-arrow">→</div>';
  const chainParts=[];
  if(up2.depth2.length) chainParts.push(chainCol(up2.depth2,'chain-d2'),chainArrow);
  if(up2.direct.length) chainParts.push(chainCol(up2.direct,''),chainArrow);
  chainParts.push(`<div class="chain-col"><span class="chain-pill chain-self">● ${esc(d.label)}</span></div>`);
  if(down2.direct.length) chainParts.push(chainArrow,chainCol(down2.direct,''));
  if(down2.depth2.length) chainParts.push(chainArrow,chainCol(down2.depth2,'chain-d2'));
  const chainHTML=(up2.direct.length||down2.direct.length)
    ? `<div class="d-section"><h3>${t('d_chain')}</h3><div class="chain-row">${chainParts.join('')}</div></div>` : '';

  document.getElementById('detail').innerHTML=`
    <div class="d-cat-bar" style="background:${col}"></div>
    <div class="d-head">
      <div style="flex:1;min-width:0">
        <div class="d-name">${esc(d.label)}</div>
        <div class="d-ticker mono">${esc(d.ticker)}</div>
      </div>
      <button onclick="window.openXRay&&window.openXRay('${id}')"
        title="X-Ray — desarmar la empresa: riesgo, hilos, onda de impacto"
        style="flex-shrink:0;padding:5px 10px;border:1px solid #00E0FF;border-radius:6px;background:none;color:#00E0FF;font-size:11px;font-weight:700;cursor:pointer;white-space:nowrap">🔬 X-Ray</button>
    </div>
    <div style="display:flex;align-items:center;gap:8px;margin:6px 0 2px;padding:7px 11px;border-radius:9px;background:${col}1a;border:1px solid ${col}55">
      <span style="width:10px;height:10px;border-radius:50%;background:${col};display:inline-block;flex-shrink:0;box-shadow:0 0 8px ${col}"></span>
      <div style="min-width:0">
        <div style="font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3)">${LANG==='en'?'Sector · category':'Sector · categoría'}</div>
        <div style="font-size:13px;font-weight:700;color:${col}">${esc(sectorLabelFor(d.cat))} <span style="color:var(--ink-3);font-weight:500">· ${catLabel(d.cat)}</span></div>
      </div>
    </div>
    <div class="d-badges">
      ${pf}
      ${preipoBadge}
      ${riskBadge}
      <span class="badge badge-loc">📍 ${esc(d.loc)}</span>
    </div>
    ${pfBtns}
    ${d.preipo ? renderPreipoPanel(d) : ''}
    <div class="fin-grid">
      <div class="fin-card">
        <div class="fl">${t('d_margin')}</div>
        <div class="fv${m.neg?' neg':''}" data-live="margin">${m.v}</div>
        <div class="fs" data-live-sub="margin">${d.margin_live ? (_en?'operating · last 12 mo · live':'operativo · últ. 12 meses · en vivo') : m.sub + ' · ' + (_en?'catalog':'catálogo')}</div>
      </div>
      <div class="fin-card">
        <div class="fl">${t('d_capex')}</div>
        <div class="fv" style="font-size:14px">${esc(nf(d,'capex_2026'))||'—'}</div>
        <div class="fs">${_en?'catalog · est.':'catálogo · estimado'}</div>
      </div>
      <div class="fin-card">
        <div class="fl">${t('d_backlog')}</div>
        <div class="fv" style="font-size:12.5px;line-height:1.35">${esc(nf(d,'backlog_status'))||'—'}</div>
        <div class="fs">${_en?'catalog':'catálogo'}</div>
      </div>
    </div>
    <div class="growth-box">
      <div class="gl" data-live-label="growth">${t('d_growth')}</div>
      <div class="gv" data-live="growth">${esc(nf(d,'growth'))}</div>
      <div class="fs" data-live-sub="growth" style="font-size:10px;color:var(--ink-3);margin-top:4px">${_en?'catalog projection (curated)':'proyección del catálogo (curada)'}</div>
    </div>
    ${d.mkt && !isPreipoTicker(d.ticker) ? `
    <div class="d-section" id="stock-chart-section-${id}">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
        <h3 style="margin:0">Precio histórico (90d)</h3>
        <div style="display:flex;gap:4px">
          <button id="chart-line-${id}" onclick="setChartMode('${id}','line')" style="padding:2px 9px;font-size:10px;border:1px solid var(--violet);border-radius:4px;background:var(--violet);color:#fff;cursor:pointer;transition:.15s">Línea</button>
          <button id="chart-candle-${id}" onclick="setChartMode('${id}','candle')" style="padding:2px 9px;font-size:10px;border:1px solid var(--line);border-radius:4px;background:none;color:var(--ink-3);cursor:pointer;transition:.15s">Velas</button>
        </div>
      </div>
      <canvas id="stock-canvas-${id}" style="width:100%;height:110px;border-radius:6px;display:block"></canvas>
      <div id="stock-info-${id}" style="display:flex;justify-content:space-between;margin-top:5px;font-size:10px;font-family:'JetBrains Mono',monospace;color:var(--ink-3)"></div>
    </div>` : ''}
    <div class="d-section">
      <h3>${t('d_role')}</h3>
      <p>${esc(nf(d,'role'))}</p>
    </div>
    <div class="d-section">
      <h3>${t('d_supplies')}</h3>
      <p>${esc(nf(d,'supplies'))}</p>
    </div>
    <div class="d-section">
      <h3>${t('d_moat')}</h3>
      <p>${esc(nf(d,'moat'))}</p>
    </div>
    ${chainHTML}
    <div class="d-section">
      <h3>${t('d_conn')}</h3>
      ${metaHTML}${connHTML(upstream,'up')}
      ${connHTML(downstream,'down')}
      ${(!upstream.length&&!downstream.length)?`<p style="font-size:12px;color:var(--ink-3)">${t('d_noconn')}</p>`:''}
    </div>
    ${(()=>{
      const ip=typeof INVEST_PATH!=='undefined'?INVEST_PATH[id]:null;
      // Direct ticker
      if(d.mkt && !isPreipoTicker(d.mkt)){
        const hasProxy = ip && ip.parent && ip.ticker === d.mkt;
        const parentNote = hasProxy ? `<div style="font-size:10px;color:#7a9cc4;margin-top:4px">Vía ${ip.parent} · ${ip.note}</div>` : '';
        return `<div style="padding:0 16px 10px">
          <button onclick="openTradeModal(${esc(JSON.stringify(String(id)))},${esc(JSON.stringify(String(d.mkt)))},${esc(JSON.stringify(String(d.label)))})" style="width:100%;padding:8px 12px;border:1.5px solid #22c55e;border-radius:6px;background:none;color:#22c55e;font-size:12px;font-weight:600;cursor:pointer;transition:.15s" onmouseover="this.style.background='rgba(34,197,94,.12)'" onmouseout="this.style.background='none'">💹 Operar ${d.mkt} ${hasProxy?'('+ip.parent+')':''}</button>
          ${parentNote}
        </div>`;
      }
      // No direct ticker but has invest path
      if(ip){
        if(ip.ticker){
          return `<div style="padding:0 16px 10px">
            <div style="font-size:10px;color:#f59e0b;margin-bottom:6px;font-weight:600">⚡ Inversión indirecta disponible</div>
            <button onclick="openTradeModal(${esc(JSON.stringify(String(id)))},${esc(JSON.stringify(String(ip.ticker)))},${esc(JSON.stringify(String(d.label)))})" style="width:100%;padding:8px 12px;border:1.5px solid #f59e0b;border-radius:6px;background:none;color:#f59e0b;font-size:12px;font-weight:600;cursor:pointer;transition:.15s" onmouseover="this.style.background='rgba(245,158,11,.1)'" onmouseout="this.style.background='none'">📊 Operar vía ${ip.parent} (${ip.ticker})</button>
            <div style="font-size:10px;color:#7a9cc4;margin-top:5px;line-height:1.4">${ip.note}</div>
          </div>`;
        }
        if(ip.etf){
          return `<div style="padding:0 16px 10px">
            <div style="font-size:10px;color:#7a9cc4;margin-bottom:6px;font-weight:600">📡 Exposición vía ETF</div>
            <button onclick="openTradeModal(${esc(JSON.stringify(String(id)))},${esc(JSON.stringify(String(ip.etf)))},${esc(JSON.stringify(String(d.label)))})" style="width:100%;padding:8px 12px;border:1.5px solid #7a9cc4;border-radius:6px;background:none;color:#7a9cc4;font-size:12px;font-weight:600;cursor:pointer;transition:.15s" onmouseover="this.style.background='rgba(122,156,196,.1)'" onmouseout="this.style.background='none'">📊 ${ip.etfName} (${ip.etf})</button>
            <div style="font-size:10px;color:#5b8ab8;margin-top:5px;line-height:1.4">${ip.note}</div>
          </div>`;
        }
        return `<div style="padding:0 16px 10px;font-size:10.5px;color:var(--ink-3);line-height:1.5;background:rgba(20,25,38,.4);border-radius:6px;border:1px solid var(--line)">
          <div style="font-weight:600;color:var(--ink-2);margin-bottom:3px">Empresa privada / Pre-IPO</div>
          ${ip.note}
        </div>`;
      }
      // Pre-IPO without path
      if(d.preipo) return `<div style="padding:0 16px 10px;font-size:10.5px;color:var(--ink-3)">Empresa privada · No cotiza en bolsa actualmente</div>`;
      return '';
    })()}
    ${stressId===id
      ? `<button class="stress-btn" onclick="clearStressBtn()">⟲ ${t('d_restore')}</button>`
      : `<button class="stress-btn" onclick="stressBtn('${d.id}')">💥 ${t('d_collapse')} ${esc(d.label)}</button>`}
  `;
  document.getElementById('detail').style.display='block';
  document.getElementById('panel-empty').style.display='none';
  document.getElementById('panel').scrollTop=0;
  if (d.mkt && !isPreipoTicker(d.ticker)) {
    requestAnimationFrame(() => loadStockChart(id, d.mkt));
  }
}
window.stressBtn=function(id){ activateStress(id); };
window.clearStressBtn=function(){ clearStress(); };

/* ===================== Stock Chart ===================== */
const _stockCache = {};   // ticker → candle data
const _chartModes = {};   // nodeId → 'line' | 'candle'

function setChartMode(nodeId, mode) {
  _chartModes[nodeId] = mode;
  const node = NODE_BY_ID[nodeId];
  if (node && _stockCache[node.mkt]) drawStockChart(nodeId, _stockCache[node.mkt], mode);
  const btn = (id, on) => {
    const b = document.getElementById(id);
    if (!b) return;
    b.style.background = on ? 'var(--violet)' : 'none';
    b.style.color = on ? '#fff' : 'var(--ink-3)';
    b.style.borderColor = on ? 'var(--violet)' : 'var(--line)';
  };
  btn(`chart-line-${nodeId}`,   mode === 'line');
  btn(`chart-candle-${nodeId}`, mode === 'candle');
}
window.setChartMode = setChartMode;

async function loadStockChart(nodeId, ticker) {
  _chartModes[nodeId] = _chartModes[nodeId] || 'line';
  const canvas = document.getElementById(`stock-canvas-${nodeId}`);
  if (!canvas) return;

  if (_stockCache[ticker]) {
    drawStockChart(nodeId, _stockCache[ticker], _chartModes[nodeId]);
    return;
  }

  const W = canvas.offsetWidth || 260, H = 110;
  canvas.width = W; canvas.height = H;
  const ctx = canvas.getContext('2d');
  const isDark = document.documentElement.classList.contains('dark');
  ctx.fillStyle = isDark ? '#26241D' : '#EFEBE1';
  ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = isDark ? '#827D72' : '#8A857A';
  ctx.font = '11px Archivo,sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('Cargando ' + ticker + '…', W / 2, H / 2);

  try {
    const r = await fetch(`/api/candles/${encodeURIComponent(ticker)}`);
    const data = await r.json();
    if (!r.ok || data.s !== 'ok' || !data.c || !data.c.length) throw new Error('no_data');
    _stockCache[ticker] = data;
    drawStockChart(nodeId, data, _chartModes[nodeId]);
    const info = document.getElementById(`stock-info-${nodeId}`);
    if (info) {
      const last = data.c[data.c.length - 1];
      const prev = data.c[data.c.length - 2] || last;
      const chg = ((last - prev) / prev * 100).toFixed(2);
      const color = chg >= 0 ? '#22c55e' : '#ef4444';
      info.innerHTML = `<span>Último: <b>$${last.toFixed(2)}</b></span><span style="color:${color}">${chg >= 0 ? '+' : ''}${chg}%</span><span>${data.c.length}d de datos</span>`;
    }
  } catch(e) {
    const c2 = document.getElementById(`stock-canvas-${nodeId}`);
    if (!c2) return;
    const ctx2 = c2.getContext('2d');
    const isDk = document.documentElement.classList.contains('dark');
    ctx2.fillStyle = isDk ? '#26241D' : '#EFEBE1';
    ctx2.fillRect(0, 0, c2.width, c2.height);
    ctx2.fillStyle = isDk ? '#827D72' : '#8A857A';
    ctx2.font = '11px Archivo,sans-serif';
    ctx2.textAlign = 'center';
    ctx2.fillText('Sin datos históricos', c2.width / 2, c2.height / 2);
  }
}
window.loadStockChart = loadStockChart;

function drawStockChart(nodeId, data, mode) {
  const canvas = document.getElementById(`stock-canvas-${nodeId}`);
  if (!canvas) return;
  const dpr = window.devicePixelRatio || 1;
  const W = canvas.offsetWidth || 260;
  const H = canvas.offsetHeight || 110;
  canvas.width = W * dpr; canvas.height = H * dpr;
  canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  const { o: opens, c: closes, h: highs, l: lows, t: times } = data;
  const n = closes.length;
  if (!n) return;
  const pad = { t: 6, r: 6, b: 18, l: 40 };
  const cW = W - pad.l - pad.r, cH = H - pad.t - pad.b;
  const prices = mode === 'candle' ? [...highs, ...lows] : closes;
  const minP = Math.min(...prices), maxP = Math.max(...prices);
  const rng = maxP - minP || 1;
  const xS = i => pad.l + (i / (n - 1)) * cW;
  const yS = p => pad.t + cH - ((p - minP) / rng) * cH;
  const isDark = document.documentElement.classList.contains('dark');

  ctx.fillStyle = isDark ? '#26241D' : '#EFEBE1';
  ctx.fillRect(0, 0, W, H);

  // Grid
  ctx.strokeStyle = isDark ? '#322F27' : '#DDD8CC';
  ctx.lineWidth = 0.5;
  for (let i = 0; i <= 3; i++) {
    const y = pad.t + (cH / 3) * i;
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
  }
  // Y labels
  ctx.fillStyle = isDark ? '#827D72' : '#8A857A';
  ctx.font = '8px JetBrains Mono,monospace';
  ctx.textAlign = 'right';
  for (let i = 0; i <= 3; i++) {
    const p = minP + (rng / 3) * (3 - i);
    ctx.fillText('$' + p.toFixed(0), pad.l - 3, pad.t + (cH / 3) * i + 3);
  }

  if (mode === 'line') {
    const isUp = closes[n - 1] >= closes[0];
    const lc = isUp ? '#22c55e' : '#ef4444';
    const grad = ctx.createLinearGradient(0, pad.t, 0, H - pad.b);
    grad.addColorStop(0, isUp ? 'rgba(34,197,94,.22)' : 'rgba(239,68,68,.22)');
    grad.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.beginPath();
    closes.forEach((c, i) => i === 0 ? ctx.moveTo(xS(i), yS(c)) : ctx.lineTo(xS(i), yS(c)));
    ctx.lineTo(xS(n - 1), H - pad.b); ctx.lineTo(xS(0), H - pad.b); ctx.closePath();
    ctx.fillStyle = grad; ctx.fill();
    ctx.beginPath();
    closes.forEach((c, i) => i === 0 ? ctx.moveTo(xS(i), yS(c)) : ctx.lineTo(xS(i), yS(c)));
    ctx.strokeStyle = lc; ctx.lineWidth = 1.5; ctx.stroke();
  } else {
    const bW = Math.max(1, (cW / n) * 0.6);
    for (let i = 0; i < n; i++) {
      const x = xS(i);
      const up = closes[i] >= opens[i];
      ctx.strokeStyle = ctx.fillStyle = up ? '#22c55e' : '#ef4444';
      ctx.lineWidth = 0.8;
      ctx.beginPath(); ctx.moveTo(x, yS(highs[i])); ctx.lineTo(x, yS(lows[i])); ctx.stroke();
      const top = yS(Math.max(opens[i], closes[i]));
      ctx.fillRect(x - bW / 2, top, bW, Math.max(1, yS(Math.min(opens[i], closes[i])) - top));
    }
  }
  // X date labels
  if (times && times.length) {
    ctx.fillStyle = isDark ? '#827D72' : '#8A857A';
    ctx.font = '8px JetBrains Mono,monospace';
    ctx.textAlign = 'center';
    [0, Math.floor(n / 3), Math.floor((2 * n) / 3), n - 1].forEach(i => {
      if (i >= n) return;
      const d = new Date(times[i] * 1000);
      ctx.fillText(`${d.getMonth() + 1}/${d.getDate()}`, xS(i), H - pad.b + 11);
    });
  }
}

/* openTradeModal is defined at bottom of file in the Trade Panel block */

/* ================== Simulación — contexto del grafo ================== */
function _injectGraphContext() {
  const cl = (cat) => typeof catLabel === 'function' ? catLabel(cat) : cat;

  // 1. Category breakdown
  const cats = {};
  NODES.forEach(n => { cats[n.cat] = (cats[n.cat] || 0) + 1; });
  const catSummary = Object.entries(cats).sort((a, b) => b[1] - a[1])
    .map(([c, n]) => `${cl(c)}: ${n}`).join(' | ');

  // 2. All nodes (compact CSV): Label [TICKER] | Category
  const allNodes = NODES.map(n =>
    `${n.label}${n.mkt ? ' [' + n.mkt + ']' : ''} | ${cl(n.cat)}`
  ).join('\n');

  // 3. Top 40 by NRS risk score
  let nrsLines = '';
  if (typeof computeNRS === 'function') {
    try {
      const scored = NODES.map(n => ({ n, nrs: computeNRS(n.id) }))
        .sort((a, b) => b.nrs - a.nrs).slice(0, 40);
      nrsLines = 'TOP 40 POR RIESGO (NRS 0-100):\n' +
        scored.map(({ n, nrs }) =>
          `  ${n.label}${n.mkt ? ' [' + n.mkt + ']' : ''}: NRS=${nrs} | ${cl(n.cat)}`
        ).join('\n');
    } catch {}
  }

  // 4. Top 60 links by weight
  const linkLines = 'CONEXIONES PRINCIPALES:\n' +
    (LINKS || []).sort((a, b) => (b.w || 1) - (a.w || 1)).slice(0, 60)
      .map(l => {
        const src = NODE_BY_ID[lid(l.source)]?.label || lid(l.source);
        const tgt = NODE_BY_ID[lid(l.target)]?.label || lid(l.target);
        return `  ${src} → ${tgt} [${l.type || l.rel || 'supply'}]`;
      }).join('\n');

  // 5. Live market prices
  const priceLines = Object.entries(MKT.quotes || {}).filter(([, q]) => q.close)
    .slice(0, 100).map(([t, q]) => {
      const chg = q.prev ? ((q.close - q.prev) / q.prev * 100).toFixed(1) : '?';
      return `  ${t}: $${q.close.toFixed(2)} (${chg}%)`;
    });
  const priceSec = priceLines.length ? 'PRECIOS DE MERCADO:\n' + priceLines.join('\n') : '';

  // 6. Portfolio if any
  const posList = Object.entries(MKT.pos || {});
  const portSec = posList.length ? 'PORTFOLIO ACTUAL:\n' + posList.map(([id, p]) => {
    const n = NODE_BY_ID[id];
    const q = n?.mkt ? MKT.quotes[n.mkt] : null;
    const nrs = typeof computeNRS === 'function' ? computeNRS(id) : '?';
    const pnl = q?.close ? ((q.close - p.bp) * p.sh).toFixed(0) : '?';
    return `  ${n?.label || id} [${n?.mkt || ''}]: ${p.sh}acc × $${p.bp} → $${q?.close?.toFixed(2) || '?'} | P&L:$${pnl} | NRS:${nrs}`;
  }).join('\n') : '';

  const parts = [
    `═══ KHIPU FINANCE — BASE DE DATOS COMPLETA ═══`,
    `Fecha: ${new Date().toLocaleString('es-ES')}`,
    `Red: ${NODES.length} empresas · ${(LINKS || []).length} conexiones de supply chain`,
    ``,
    `SECTORES: ${catSummary}`,
    ``,
    `DIRECTORIO COMPLETO (${NODES.length} empresas):`,
    allNodes,
    ``,
    nrsLines,
    ``,
    linkLines,
    priceSec ? `\n${priceSec}` : '',
    portSec ? `\n${portSec}` : '',
  ].filter(x => x !== '');

  const ctx = parts.join('\n');
  const el = document.getElementById('sim-context-text');
  if (el) {
    el.value = ctx;
    el.style.height = '140px';
    const kb = Math.round(ctx.length / 1024);
    if (typeof toast === 'function') toast(`📊 ${NODES.length} empresas · ${(LINKS||[]).length} conexiones · ${priceLines.length} precios · ${kb}KB`);
  }
}
window._injectGraphContext = _injectGraphContext;

/* ===================== Selector de vista ===================== */
function applyView(mode){
  viewMode=mode;
  if(mode!=='geo') activeCountry=null;
  invalidateFilterCache(); /* v7 · M10 */
  document.querySelectorAll('#view-seg button').forEach(b=>b.classList.toggle('active',b.dataset.view===mode));
  setForces();
  positionRegionLabels();
  regionLabels.transition().duration(450).style('opacity',mode==='geo'?0.92:0);
  recolorNodes();
  renderLegend();
  renderBand();
  refreshStyles();
  settleGraph(.75, 220);
}
document.querySelectorAll('#view-seg button').forEach(b=>{
  b.onclick=()=>applyView(b.dataset.view);
});

/* ===================== Búsqueda predictiva ===================== */
const searchInput=document.getElementById('search');
const suggEl=document.getElementById('sugg');
let suggIdx=-1, suggIds=[];

function closeSugg(){ suggEl.classList.remove('show'); suggEl.innerHTML=''; suggIdx=-1; suggIds=[]; }

function renderSugg(q){
  if(!q){ closeSugg(); return; }
  const ql=q.toLowerCase();
  const starts=[], incl=[];
  NODES.forEach(n=>{
    const hay=(n.label+' '+n.ticker+' '+n.id).toLowerCase();
    if(n.label.toLowerCase().startsWith(ql)||n.ticker.toLowerCase().startsWith(ql)) starts.push(n);
    else if(hay.includes(ql)) incl.push(n);
  });
  const list=[...starts,...incl].slice(0,8);
  if(!list.length){ closeSugg(); return; }
  suggIds=list.map(n=>n.id);
  suggEl.innerHTML=list.map((n,i)=>`
    <div class="sugg-item${i===suggIdx?' active':''}" data-id="${n.id}">
      <span class="sd" style="background:${catColor(n.cat)}"></span>
      <span class="sn">${esc(n.label)}</span>
      <span class="st">${esc(n.ticker.split(' · ')[0])}</span>
      <span class="sc">${catLabel(n.cat)}</span>
    </div>`).join('');
  suggEl.classList.add('show');
  suggEl.querySelectorAll('.sugg-item').forEach(el=>{
    el.onmousedown=e=>{ e.preventDefault(); pickSugg(el.dataset.id); };
  });
}

function pickSugg(id){
  searchTerm=''; searchInput.value='';
  /* 2026-10-05: sin esto el filtro guardado seguía con el texto buscado ("nvid") y, al deseleccionar,
     el mapa dejaba encendida SOLO esa empresa hasta recargar la página. */
  invalidateFilterCache();
  closeSugg();
  if(typeof closeToolbar==='function') closeToolbar();
  jumpTo(id);
}

searchInput.addEventListener('input',e=>{
  searchTerm=e.target.value.toLowerCase().trim();
  suggIdx=-1;
  invalidateFilterCache(); /* v7 · M10 */
  renderSugg(e.target.value.trim());
  if(!selected&&!stressId) refreshStyles();
});
searchInput.addEventListener('keydown',e=>{
  if(!suggIds.length) return;
  if(e.key==='ArrowDown'){ e.preventDefault(); suggIdx=Math.min(suggIdx+1,suggIds.length-1); renderSugg(searchInput.value.trim()); }
  else if(e.key==='ArrowUp'){ e.preventDefault(); suggIdx=Math.max(suggIdx-1,0); renderSugg(searchInput.value.trim()); }
  else if(e.key==='Enter'){ e.preventDefault(); pickSugg(suggIds[suggIdx>=0?suggIdx:0]); }
});
searchInput.addEventListener('blur',()=>setTimeout(closeSugg,150));

/* ===================== Chips de filtro ===================== */
const catChips=document.getElementById('cat-chips');
Object.entries(CATS).forEach(([key,c])=>{
  const b=document.createElement('button');
  b.className='chip';b.dataset.cat=key;
  b.innerHTML=`<span class="dot" style="background:${catColor(key)}"></span><span class="chip-txt">${catLabel(key)}</span>`;
  b.onclick=()=>{
    if(activeCat===key){activeCat=null;b.classList.remove('active');}
    else{catChips.querySelectorAll('.chip').forEach(x=>x.classList.remove('active'));activeCat=key;b.classList.add('active');}
    invalidateFilterCache(); /* v7 · M10 */
    if(!selected&&!stressId) refreshStyles();
  };
  catChips.appendChild(b);
});

document.querySelectorAll('.pf-chip').forEach(b=>{
  b.onclick=()=>{
    const pf=b.dataset.pf;
    if(activePF===pf){activePF=null;b.classList.remove('active');}
    else{document.querySelectorAll('.pf-chip').forEach(x=>x.classList.remove('active'));activePF=pf;b.classList.add('active');}
    invalidateFilterCache(); /* v7 · M10 */
    if(!selected&&!stressId) refreshStyles();
  };
});

/* ===================== Pills de inicio, leyenda, métricas ===================== */
const startPills=document.getElementById('start-pills');
['TSMC','Nvidia','ASML','SK Hynix','OpenAI','Anthropic','Oracle','Bluefors','Figure AI'].forEach(name=>{
  const node=NODES.find(n=>n.label.startsWith(name));
  if(!node) return;
  const b=document.createElement('button');
  b.textContent=name;
  b.onclick=()=>jumpTo(node.id);
  startPills.appendChild(b);
});

const legend=document.getElementById('legend');
function renderLegend(){
  if(viewMode==='geo'){
    legend.innerHTML=`<div class="lt">${t('lg_countries')}</div>`+
      Object.keys(COUNTRIES).map(k=>`<div class="legend-row"><span class="ld" style="background:${countryColor(k)}"></span>${countryLabel(k)}</div>`).join('');
  } else if(colorMode==='sector'){
    // 9 macro-sectores + toggle a las 40 categorías (el detalle no se pierde)
    legend.innerHTML=`<div class="lt" style="display:flex;justify-content:space-between;align-items:center">`+
      `<span>${LANG==='en'?'Sectors':'Sectores'}</span>`+
      `<span onclick="_toggleColorMode()" style="cursor:pointer;color:#00E0FF;font-size:8.5px;letter-spacing:.06em" title="Ver las 40 categorías">▸ ${LANG==='en'?'detail':'detalle'}</span></div>`+
      Object.keys(window.SECTORS9).map(k=>{
        const s=window.SECTORS9[k];
        return `<div class="legend-row"><span class="ld" style="background:${s.color};box-shadow:0 0 6px ${s.color}"></span>${LANG==='en'?s.en:s.label}</div>`;
      }).join('');
  } else {
    legend.innerHTML=`<div class="lt" style="display:flex;justify-content:space-between;align-items:center">`+
      `<span>${t('lg_stages')}</span>`+
      `<span onclick="_toggleColorMode()" style="cursor:pointer;color:#00E0FF;font-size:8.5px;letter-spacing:.06em" title="Agrupar en 9 sectores">◂ ${LANG==='en'?'sectors':'sectores'}</span></div>`+
      Object.keys(CATS).map(k=>`<div class="legend-row"><span class="ld" style="background:${catColor(k)}"></span>${catLabel(k)}</div>`).join('');
  }
}
window._toggleColorMode=function(){
  colorMode = colorMode==='sector' ? 'cat' : 'sector';
  localStorage.setItem('eco_colormode', colorMode);
  recolorNodes();
  renderLegend();
  if(typeof renderBand==='function') renderBand();
  if(selected) renderDetail(selected);
};
/* renderLegend() se invoca desde applyLang() en el init de la app */

document.getElementById('m-companies').textContent=NODES.length;
document.getElementById('m-links').textContent=LINKS.length;
document.getElementById('m-stages').textContent=new Set(NODES.map(n=>n.cat)).size;
document.getElementById('m-preipo').textContent=NODES.filter(n=>n.preipo).length;

/* ===================== Header: tema y reset ===================== */
document.getElementById('theme-toggle').onclick=()=>{
  document.body.classList.toggle('dark');
  localStorage.setItem('eco_theme', document.body.classList.contains('dark')?'dark':'light');
  recolorNodes();
  positionRegionLabels();
  catChips.querySelectorAll('.chip').forEach(ch=>{
    const dot=ch.querySelector('.dot'); if(dot) dot.style.background=catColor(ch.dataset.cat);
  });
  renderLegend();
  renderBand();
  buildLtChips(); /* v7: los puntos de color de los chips dependen del tema */
  if(activeTab==='geo') renderGeoPanel();           /* v7: colores del mapa geo */
  if(activeTab==='analysis') renderAnalysis();      /* v7: colores de las barras M9 */
  if(selected) renderDetail(selected);
  if(suggEl.classList.contains('show')) renderSugg(searchInput.value.trim());
  refreshStyles();
};

document.getElementById('reset-btn').onclick=()=>{
  activePF=null;activeCat=null;activeCountry=null;searchTerm='';activeLinkType='';
  searchInput.value='';
  invalidateFilterCache(); /* v7 · M10 */
  clearPath(true);         /* v7 · M4 */
  renderBand();
  closeSugg();
  document.querySelectorAll('.chip').forEach(c=>c.classList.remove('active'));
  document.querySelectorAll('.lt-chip').forEach(b=>b.classList.toggle('active',b.dataset.lt===''));
  clearStress();
  deselect();
  applyView('flow');
  svg.transition().duration(500).call(zoom.transform,d3.zoomIdentity);
};

document.getElementById('zoom-in').onclick=()=>svg.transition().duration(250).call(zoom.scaleBy,1.4);
document.getElementById('zoom-out').onclick=()=>svg.transition().duration(250).call(zoom.scaleBy,1/1.4);
document.getElementById('zoom-fit').onclick=()=>fitToView();

/* ===================== Interacciones móviles ===================== */
const isMobile=()=>window.matchMedia('(max-width:820px)').matches;
const toolbarEl=document.getElementById('toolbar');
const backdropEl=document.getElementById('backdrop');
const panelEl=document.getElementById('panel');
const mobileHint=document.getElementById('mobile-hint');

function openToolbar(focusSearch){
  toolbarEl.classList.add('open'); backdropEl.classList.add('show');
  if(focusSearch) setTimeout(()=>searchInput.focus(),220);
}
function closeToolbar(){
  if(!isMobile()) return;
  toolbarEl.classList.remove('open');
  if(!panelEl.classList.contains('open')) backdropEl.classList.remove('show');
}
function openSheet(){
  panelEl.classList.add('open'); backdropEl.classList.add('show');
  if(mobileHint) mobileHint.style.display='none';
}
function closeSheet(){
  panelEl.classList.remove('open');
  if(!toolbarEl.classList.contains('open')) backdropEl.classList.remove('show');
  if(mobileHint && isMobile()) mobileHint.style.display='';
}
document.getElementById('m-filter-btn').onclick=()=>openToolbar(false);
document.getElementById('m-search-btn').onclick=()=>openToolbar(true);
document.getElementById('m-toolbar-close').onclick=closeToolbar;
document.getElementById('sheet-close').onclick=()=>deselect();
backdropEl.onclick=()=>{ closeToolbar(); if(panelEl.classList.contains('open')) deselect(); };

(function(){
  const handle=document.getElementById('sheet-handle');
  let y0=null;
  const start=e=>{ y0=(e.touches?e.touches[0].clientY:e.clientY); };
  const move=e=>{ if(y0==null) return; const y=(e.touches?e.touches[0].clientY:e.clientY); if(y-y0>60){ y0=null; deselect(); } };
  const end=()=>{ y0=null; };
  handle.addEventListener('touchstart',start,{passive:true});
  handle.addEventListener('touchmove',move,{passive:true});
  handle.addEventListener('touchend',end);
})();

const _selectNode=selectNode;
selectNode=function(id){
  _selectNode(id);
  if(isMobile()){ closeToolbar(); openSheet(); flyToNode(NODE_BY_ID[id],0.22); }
};
const _deselect=deselect;
deselect=function(){
  _deselect();
  closeSheet();
};
function onStressMobile(){ if(isMobile()){ closeToolbar(); openSheet(); } }

setTimeout(()=>{ if(isMobile()) fitToView(650); },1900);

/* ===================== Init ===================== */
// Amortiguado a propósito: en el móvil este evento se dispara en ráfaga al
// ocultarse/mostrarse la barra del navegador durante el scroll, y ahora cada
// resize reasienta la física (trabajo síncrono). Sin esto, el arreglo de
// rendimiento se convertiría en un problema de rendimiento.
let _resizeT = null;
window.addEventListener('resize', () => {
  clearTimeout(_resizeT);
  _resizeT = setTimeout(resize, 150);
});
setTimeout(resize,60);
/* Khipus OS (2026-10-06): señales de "el mapa se volvió visible" además del 'resize' de la ventana.
   - ResizeObserver del <svg>: al adoptarlo una ventana del escritorio, al devolverlo a su pestaña,
     al restaurar una ventana minimizada o al cambiar de pestaña (0×0 → tamaño real).
   - visibilitychange: la pestaña del navegador estaba en segundo plano al arrancar.
   - pointerenter: red de seguridad si algo lo mostró sin avisar (nunca dejarlo vacío).
   - Vigía del arranque: si se esperaba Khipus OS y no se abrió (falló o vista clásica), asentar.
   Todos llaman a _ensureMapSettled(): idempotente y gratis si nada cambió. */
(function(){
  const el = svg.node();
  if (window.ResizeObserver) {
    let roT = null;
    try {
      new ResizeObserver(() => {
        /* Solo hasta el PRIMER asentado. Después, cada forma real de mostrar el mapa ya avisa
           (switchTab, 'resize' del escritorio/Cabina, visibilitychange) y los corrimientos de
           maquetación del arranque (el svg pasa por 29 px → 0 → 349 px) NO deben re-asentar:
           medido, era un asentado extra de ~0,85 s justo al desvanecerse el splash. */
        if (!_mapLaidOnce) { clearTimeout(roT); roT = setTimeout(resize, 0); }
      }).observe(el);
    } catch(e){}
  }
  document.addEventListener('visibilitychange', () => { if (!document.hidden) setTimeout(resize, 0); });
  el.addEventListener('pointerenter', () => { if (!_mapLaidOnce) resize(); });
  let n = 0;
  const iv = setInterval(() => {
    n++;
    if (_mapLaidOnce || _mapCkOpened || n > 70) { clearInterval(iv); return; }
    if (!_mapBootWaiting()) { clearInterval(iv); resize(); }
  }, 200);
})();


/* ===================== i18n ===================== */
const I18N = {
es: {
  sub:'Cadena de valor global 2026 · 450+ empresas · 900+ conexiones · 35 categorías',
  hg_title:'Hipergrafos Temporales', hg_add:'+ Evento', hg_hide:'Ocultar',
  tab_map:'Mapa de la Cadena', tab_market:'Mercado en Vivo', tab_portfolios:'Carteras', tab_committee:'Comité', tab_clients:'Clientes',
  tab_analysis:'Análisis de Red', tab_geo:'Geopolítica',
  tab_sim:'Simulación', tab_space:'Espacio',
  an_history_h:'Historial de lecturas',
  an_history_sub:'— cómo fue cambiando la red (una entrada por cambio real, no por visita)',
  sim_sub:'Motores internos · agentes con IA + matrices deterministas · Escenarios geopolíticos y de mercado sobre la cadena de valor global',
  sim_preset_btn:'Preset', sim_run:'▶ Ejecutar Simulación', sim_placeholder:'Describe el escenario...',
  space_launches:'Próximos Lanzamientos', space_companies:'Empresas Espaciales en Khipu', space_consts:'Constelaciones rastreadas', space_sats:'Satélites rastreados', space_nodes:'Nodos espaciales en Khipu',
  f_link:'Vínculo',
  lt_all:'Todos', lt_supply:'Suministro', lt_fab:'Fabricación', lt_license:'Licencia IP',
  lt_cloud:'Cloud/SaaS', lt_invest:'Inversión', lt_deploy:'Despliegue', lt_partner:'Partnership',
  pf_btn:'Trazar ruta', pf_clear:'Limpiar ruta',
  pf_pick_src:'Pathfinder: haz clic en el nodo de ORIGEN', pf_pick_dst:'Ahora haz clic en el nodo DESTINO',
  pf_nopath:'Sin ruta dirigida de {a} a {b}', pf_hops:'saltos',
  d_chain:'Posición en la cadena',
  tt_sup:'proveedores', tt_cli:'clientes', tt_risk:'riesgo geo',
  an_sub:'{n} empresas · {l} conexiones · 7 tipos de relación · grafo dirigido',
  geo_title:'Geopolítica del Ecosistema',
  geo_sub:'Mapa esquemático por regiones · tamaño = capitalización de mercado · borde = riesgo geopolítico · clic = ver en el mapa',
  geo_rank:'Top 8 · Riesgo sistémico por país',
  geo_note:'Score = Σ (grado de entrada × riesgo) de las empresas del país. Riesgo: critical=4 · high=3 · medium=2 · low=1.',
  geo_th_country:'País', geo_th_co:'Empresas',
  ml_co:'Empresas', ml_ln:'Conexiones', ml_st:'Etapas', ml_ipo:'Pre-IPO',
  f_view:'Vista', f_port:'Cartera', f_stage:'Etapa',
  v_flow:'⇢ Flujo de Valor', v_geo:'◉ Geopolítica',
  pf1:'Corto plazo', pf2:'Mediano plazo',
  search_ph:'Buscar empresa o ticker…',
  hint:'<span>Clic → detalle</span><span>·</span><span><b>Alt+Clic → simular colapso</b></span><span>·</span><span>Scroll → zoom</span>',
  mhint:'👆 Toca una empresa para ver su detalle', mtb_head:'Buscar y filtrar',
  st_msg:'Colapso simulado: {n} — {c} empresas afectadas aguas abajo (≥1 % del golpe; {p}% de la cadena)',
  st_msg_safe:'Colapso simulado: {n} — la cadena lo absorbe: ninguna empresa recibe ≥1 % del golpe',
  st_wait:'Colapso simulado: {n} — calculando con el motor del servidor…',
  st_err:'Colapso simulado: {n} — {e}',
  st_restore:'⟲ Restaurar cadena',
  lg_stages:'Etapas de la cadena', lg_countries:'Países',
  pf_both:'Cartera 1 + Cartera 2', pf_c1:'Cartera 1 (corto plazo)', pf_c2:'Cartera 2 (mediano plazo)',
  b_preipo:'PRE-IPO — aún privada', b_priv:'No cotiza — privada / subsidiaria', b_risk:'Riesgo regulatorio severo',
  m_pre:'Pre-ingresos / no significativo', m_burn:'Quema caja (margen negativo)', m_op:'Margen operativo est. FY2026',
  d_margin:'Margen s/ ventas', d_capex:'CAPEX 2026e', d_backlog:'Backlog', d_growth:'Proyección de crecimiento 2026–2027',
  d_role:'Rol estratégico', d_supplies:'Componentes suministrados', d_moat:'Foso competitivo (Moat)',
  d_conn:'Interconexiones en la cadena', d_up:'Proveedores (Aguas Arriba)', d_down:'Clientes (Aguas Abajo)',
  d_noconn:'Sin conexiones directas mapeadas.', d_restore:'Restaurar la cadena', d_collapse:'Simular colapso de',
  em_title:'Explora la cadena de valor 2026',
  em_p1:'Cada nodo es una empresa real, desde la <strong>criogenia cuántica</strong> finlandesa hasta los <strong>laboratorios de IA frontera</strong>. Las líneas muestran <strong>quién suministra a quién</strong>.',
  em_p2:'El anillo dorado/azul marca la cartera. El anillo <strong>morado punteado</strong> marca empresas <strong>privadas o pre-IPO</strong> que aún no cotizan.',
  em_p3:'<strong>💥 Stress-Test:</strong> Alt+Clic sobre cualquier empresa (o el botón rojo de su ficha) simula su colapso y el efecto dominó aguas abajo.',
  em_start:'Empieza por los nodos centrales',
  disc:'Análisis informativo: precios y fundamentales en vivo donde dice ● / «en vivo»; lo rotulado «catálogo» son estimaciones curadas (revisión jun. 2026). Toda métrica de rentabilidad es margen sobre ventas. No constituye asesoría financiera.',
  mk_value:'Valor de posiciones', mk_pnl:'P&L total', mk_day:'Variación del día', mk_status:'Datos',
  mk_fpos:'Posiciones', mk_fall:'Todas', mk_refresh:'Actualizar precios', mk_risk:'Reporte de riesgo', mk_key:'API key',
  mk_save:'Guardar', mk_clear:'Borrar',
  mk_keyhint:'Se guarda solo en este navegador (localStorage), nunca en el archivo.',
  mk_foot:'Precios EN VIVO (Finnhub y Yahoo, todas las bolsas; el punto verde dice la fuente y la hora). Marketstack solo como respaldo de cierre. Las empresas privadas no cotizan: muestran su última valuación verificada (✓ fecha).',
  mk_nokey:'Sin API key', mk_keysaved:'Key guardada', mk_updated:'Actualizado', mk_never:'Sin datos aún',
  mk_loading:'Consultando…', mk_err:'Error', mk_cached:'caché local',
  th_co:'Empresa', th_price:'Precio', th_chg:'Día %', th_sh:'Acciones', th_bp:'P. compra', th_val:'Valor', th_pnl:'P&L %', th_act:'',
  mk_add:'+ Posición', mk_edit:'✎', mk_npos:'—',
  nrs_top10:'⚡ NRS Top 10 — Mayor Riesgo',
  cr_title:'₿ Cripto — Top por capitalización', cr_sub:'Datos en vivo de CoinGecko · clic en una moneda para ver su detalle',
  cr_th_coin:'Moneda', cr_th_price:'Precio', cr_th_24h:'24h %', cr_th_7d:'7d %', cr_th_mcap:'Market cap', cr_th_vol:'Volumen 24h',
  cr_loading:'Cargando mercado cripto…', cr_err:'No se pudo cargar el mercado cripto. Reintenta en unos segundos.',
  cr_back:'← Volver a la lista', cr_supply:'En circulación', cr_maxsupply:'Suministro máximo', cr_ath:'Máximo histórico', cr_atl:'Mínimo histórico', cr_rank:'Ranking',
  cr_view_map:'Mapa', cr_view_list:'Lista', cr_view_bub:'Burbujas', cr_all:'Todas', cr_empty:'Ninguna moneda del top 100 en esta categoría.',
  cr_bub_hint:'tamaño = capitalización · color = 24h · toca una burbuja', cr_open_card:'Ver ficha completa',
  cr_dossier:'Expediente', cr_dossier_t:'Expediente Khipu',
  cr_b_what:'¿Qué es?', cr_b_mech:'Cómo funciona', cr_b_tok:'Tokenomics', cr_b_cats:'Catalizadores', cr_b_risks:'Riesgos', cr_b_pos:'Posicionamiento',
  cr_disclaimer:'Contexto informativo, no es asesoría de inversión. Capa de análisis: jul 2026 · precios en vivo de CoinGecko.',
},
en: {
  sub:'Global value chain 2026 · 450+ companies · 900+ links · 35 categories',
  hg_title:'Temporal hypergraphs', hg_add:'+ Event', hg_hide:'Hide',
  tab_map:'Chain Map', tab_market:'Live Market', tab_portfolios:'Portfolios', tab_committee:'Committee', tab_clients:'Clients',
  tab_analysis:'Network Analysis', tab_geo:'Geopolitics',
  tab_sim:'Simulation', tab_space:'Space Economy',
  an_history_h:'Reading history',
  an_history_sub:'— how the network kept changing (one entry per real change, not per visit)',
  sim_sub:'Internal engines · AI agents + deterministic matrices · Geopolitical and market scenarios across the global value chain',
  sim_preset_btn:'Preset', sim_run:'▶ Run Simulation', sim_placeholder:'Describe the scenario...',
  space_launches:'Upcoming Launches', space_companies:'Space Companies in Khipu', space_consts:'Tracked constellations', space_sats:'Tracked satellites', space_nodes:'Space nodes in Khipu',
  f_link:'Link type',
  lt_all:'All', lt_supply:'Supply', lt_fab:'Fabrication', lt_license:'IP License',
  lt_cloud:'Cloud/SaaS', lt_invest:'Investment', lt_deploy:'Deployment', lt_partner:'Partnership',
  pf_btn:'Trace route', pf_clear:'Clear route',
  pf_pick_src:'Pathfinder: click the SOURCE node', pf_pick_dst:'Now click the TARGET node',
  pf_nopath:'No directed path from {a} to {b}', pf_hops:'hops',
  d_chain:'Position in the chain',
  tt_sup:'suppliers', tt_cli:'customers', tt_risk:'geo risk',
  an_sub:'{n} companies · {l} links · 7 relation types · directed graph',
  geo_title:'Ecosystem Geopolitics',
  geo_sub:'Schematic region map · size = market cap · border = geopolitical risk · click = view on map',
  geo_rank:'Top 8 · Systemic risk by country',
  geo_note:'Score = Σ (in-degree × risk) of the country\'s companies. Risk: critical=4 · high=3 · medium=2 · low=1.',
  geo_th_country:'Country', geo_th_co:'Companies',
  ml_co:'Companies', ml_ln:'Links', ml_st:'Stages', ml_ipo:'Pre-IPO',
  f_view:'View', f_port:'Portfolio', f_stage:'Stage',
  v_flow:'⇢ Value Flow', v_geo:'◉ Geopolitical',
  pf1:'Short term', pf2:'Medium term',
  search_ph:'Search company or ticker…',
  hint:'<span>Click → details</span><span>·</span><span><b>Alt+Click → simulate collapse</b></span><span>·</span><span>Scroll → zoom</span>',
  mhint:'👆 Tap a company to see its details', mtb_head:'Search & filter',
  st_msg:'Simulated collapse: {n} — {c} companies affected downstream (≥1% of the hit; {p}% of the chain)',
  st_msg_safe:'Simulated collapse: {n} — the chain absorbs it: no company receives ≥1% of the hit',
  st_wait:'Simulated collapse: {n} — computing with the server engine…',
  st_err:'Simulated collapse: {n} — {e}',
  st_restore:'⟲ Restore chain',
  lg_stages:'Chain stages', lg_countries:'Countries',
  pf_both:'Portfolio 1 + Portfolio 2', pf_c1:'Portfolio 1 (short term)', pf_c2:'Portfolio 2 (medium term)',
  b_preipo:'PRE-IPO — still private', b_priv:'Not listed — private / subsidiary', b_risk:'Severe regulatory risk',
  m_pre:'Pre-revenue / not meaningful', m_burn:'Cash burn (negative margin)', m_op:'Est. operating margin FY2026',
  d_margin:'Margin on sales', d_capex:'CAPEX 2026e', d_backlog:'Backlog', d_growth:'Growth outlook 2026–2027',
  d_role:'Strategic role', d_supplies:'Supplied components', d_moat:'Competitive moat',
  d_conn:'Chain interconnections', d_up:'Suppliers (Upstream)', d_down:'Customers (Downstream)',
  d_noconn:'No direct connections mapped.', d_restore:'Restore the chain', d_collapse:'Simulate collapse of',
  em_title:'Explore the 2026 value chain',
  em_p1:'Every node is a real company, from Finnish <strong>quantum cryogenics</strong> to <strong>frontier AI labs</strong>. Lines show <strong>who supplies whom</strong>.',
  em_p2:'The gold/blue ring marks the portfolio. The dashed <strong>purple ring</strong> marks <strong>private or pre-IPO</strong> companies.',
  em_p3:'<strong>💥 Stress-Test:</strong> Alt+Click any company (or the red button on its card) to simulate its collapse and the downstream domino effect.',
  em_start:'Start with the central nodes',
  disc:'Informational analysis: live prices and fundamentals where marked ● / «live»; items labelled «catalog» are curated estimates (Jun 2026 review). All profitability metrics are margin on sales. Not financial advice.',
  mk_value:'Positions value', mk_pnl:'Total P&L', mk_day:'Day change', mk_status:'Data',
  mk_fpos:'Positions', mk_fall:'All', mk_refresh:'Refresh prices', mk_risk:'Risk report', mk_key:'API key',
  mk_save:'Save', mk_clear:'Clear',
  mk_keyhint:'Stored only in this browser (localStorage), never inside the file.',
  mk_foot:'LIVE prices (Finnhub and Yahoo, all exchanges; the green dot shows the source and time). Marketstack only as an end-of-day fallback. Private companies do not trade: they show their last verified valuation (✓ date).',
  mk_nokey:'No API key', mk_keysaved:'Key saved', mk_updated:'Updated', mk_never:'No data yet',
  mk_loading:'Fetching…', mk_err:'Error', mk_cached:'local cache',
  th_co:'Company', th_price:'Price', th_chg:'Day %', th_sh:'Shares', th_bp:'Buy price', th_val:'Value', th_pnl:'P&L %', th_act:'',
  mk_add:'+ Position', mk_edit:'✎', mk_npos:'—',
  nrs_top10:'⚡ NRS Top 10 — Highest Risk',
  cr_title:'₿ Crypto — Top by market cap', cr_sub:'Live data from CoinGecko · click a coin to see its detail',
  cr_th_coin:'Coin', cr_th_price:'Price', cr_th_24h:'24h %', cr_th_7d:'7d %', cr_th_mcap:'Market cap', cr_th_vol:'24h volume',
  cr_loading:'Loading crypto market…', cr_err:'Could not load the crypto market. Retry in a few seconds.',
  cr_back:'← Back to list', cr_supply:'Circulating supply', cr_maxsupply:'Max supply', cr_ath:'All-time high', cr_atl:'All-time low', cr_rank:'Rank',
  cr_view_map:'Map', cr_view_list:'List', cr_view_bub:'Bubbles', cr_all:'All', cr_empty:'No top-100 coin in this category.',
  cr_bub_hint:'size = market cap · color = 24h · tap a bubble', cr_open_card:'Open full card',
  cr_dossier:'Dossier', cr_dossier_t:'Khipu Dossier',
  cr_b_what:'What is it?', cr_b_mech:'How it works', cr_b_tok:'Tokenomics', cr_b_cats:'Catalysts', cr_b_risks:'Risks', cr_b_pos:'Positioning',
  cr_disclaimer:'Informational context, not investment advice. Analysis layer: Jul 2026 · live prices from CoinGecko.',
},
};
function t(k){ return (I18N[LANG]&&I18N[LANG][k])||I18N.es[k]||k; }

function applyLang(){
  document.documentElement.lang=LANG;
  document.getElementById('lang-toggle').textContent = LANG==='es'?'EN':'ES';
  document.querySelectorAll('[data-i18n]').forEach(el=>{ el.innerHTML=t(el.dataset.i18n); });
  (function(){
    const _nCats = new Set((window.NODES||[]).map(n=>n.cat)).size;
    const _nN = (window.NODES||[]).length, _nL = (window.LINKS||[]).length;
    const _pre = LANG==='en' ? 'Global value chain 2026' : 'Cadena de valor global 2026';
    const _u = LANG==='en'
      ? `${_nN} companies · ${_nL} links · ${_nCats} categories`
      : `${_nN} empresas · ${_nL} conexiones · ${_nCats} categorías`;
    const el=document.querySelector('.brand .sub');
    if(el) el.textContent = `${_pre} · ${_u}`;
  })();
  const mls=document.querySelectorAll('.metric .l');
  ['ml_co','ml_ln','ml_st','ml_ipo'].forEach((k,i)=>{ if(mls[i]) mls[i].textContent=t(k); });
  const fls=document.querySelectorAll('.filter-label');
  ['f_view','f_port','f_stage'].forEach((k,i)=>{ if(fls[i]) fls[i].textContent=t(k); });
  const vf=document.querySelector('#view-seg [data-view="flow"]'); if(vf) vf.textContent=t('v_flow');
  const vg=document.querySelector('#view-seg [data-view="geo"]'); if(vg) vg.textContent=t('v_geo');
  const p1=document.querySelector('.pf-chip.c1'); if(p1) p1.textContent=t('pf1');
  const p2=document.querySelector('.pf-chip.c2'); if(p2) p2.textContent=t('pf2');
  searchInput.placeholder=t('search_ph');
  document.querySelector('.graph-hint').innerHTML=t('hint');
  const mh=document.getElementById('mobile-hint'); if(mh) mh.textContent=t('mhint');
  const th=document.querySelector('.toolbar-mobile-head span'); if(th) th.textContent=t('mtb_head');
  document.getElementById('stress-restore').textContent=t('st_restore');
  /* v7: textos de las features nuevas */
  const ltl=document.getElementById('lt-label'); if(ltl) ltl.textContent=t('f_link');
  const pfb=document.getElementById('pf-btn-txt'); if(pfb) pfb.textContent=t('pf_btn');
  if(window.KhipuMapTime) window.KhipuMapTime.relabel();
  const pcl=document.getElementById('path-clear'); if(pcl) pcl.textContent='✕ '+t('pf_clear');
  buildLtChips();
  const gt=document.getElementById('geo-title'); if(gt) gt.textContent=t('geo_title');
  const gs=document.getElementById('geo-sub'); if(gs) gs.textContent=t('geo_sub');
  const gr=document.getElementById('geo-rank-title'); if(gr) gr.textContent=t('geo_rank');
  const gn=document.getElementById('geo-rank-note'); if(gn) gn.textContent=t('geo_note');
  const gtc=document.getElementById('geo-th-country'); if(gtc) gtc.textContent=t('geo_th_country');
  const gco=document.getElementById('geo-th-co'); if(gco) gco.textContent=t('geo_th_co');
  if(activeTab==='geo') renderGeoPanel();
  if(activeTab==='analysis') renderAnalysis();
  if(window._dossierRelabel) window._dossierRelabel();   /* Dossier de Análisis: bilingüe */
  if(activeTab==='guia' && window.initGuiaTab) window.initGuiaTab();   /* la Guía es bilingüe */
  /* pestañas primarias (nav4) y subtítulo del botón Khipu: también bilingües */
  { const _en=LANG==='en', PT={mapa:_en?'Map':'Mapa', mercado:_en?'Market':'Mercado', insights:'Terminal', guia:_en?'Guide':'Guía'};
    document.querySelectorAll('.ptab[data-group]').forEach(b=>{ const sp=b.querySelector('span'); if(sp&&PT[b.dataset.group]) sp.textContent=PT[b.dataset.group]; });
    const bs=document.getElementById('bixby-btn-sub'); if(bs) bs.textContent=_en?'ask me ⌘K':'pregúntame ⌘K'; }
  const pe=document.getElementById('panel-empty');
  pe.querySelector('h2').innerHTML=t('em_title');
  const ps=pe.querySelectorAll('p');
  ['em_p1','em_p2','em_p3'].forEach((k,i)=>{ if(ps[i]) ps[i].innerHTML=t(k); });
  pe.querySelector('.start-hint .t').textContent=t('em_start');
  document.querySelector('footer .disc').textContent=t('disc');
  catChips.querySelectorAll('.chip').forEach(ch=>{
    const tx=ch.querySelector('.chip-txt'); if(tx) tx.textContent=catLabel(ch.dataset.cat);
  });
  positionRegionLabels();
  renderLegend();
  renderBand();
  if(selected) renderDetail(selected);
  if(stressId){
    document.getElementById('stress-text').innerHTML=stressText(NODE_BY_ID[stressId]);
  }
  renderMarket();
  // i18n: simulation + space tab dynamic strings
  const simRunBtn=document.getElementById('sim-run-btn'); if(simRunBtn) simRunBtn.textContent=t('sim_run');
  const simTxt=document.getElementById('sim-custom-text'); if(simTxt) simTxt.placeholder=t('sim_placeholder');
  // data-i18n-placeholder support
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el=>{ el.placeholder=t(el.dataset.i18nPlaceholder); });
}
document.getElementById('lang-toggle').onclick=()=>{
  LANG = LANG==='es'?'en':'es';
  localStorage.setItem('eco_lang',LANG);
  closeSugg();
  applyLang();
};

/* ===================== Banda superior (etapas / países) ===================== */
const bandEl=document.getElementById('band');
function renderBand(){
  if(viewMode==='geo'){
    const counts={};
    NODES.forEach(n=>{ const k=COUNTRIES[n.country]?n.country:'RestoMundo'; counts[k]=(counts[k]||0)+1; });
    bandEl.innerHTML=Object.keys(COUNTRIES).map(k=>`
      <button class="band-item${activeCountry===k?' active':''}" data-country="${k}">
        <span class="bd" style="background:${countryColor(k)}"></span>${countryLabel(k)} <span class="bc">${counts[k]||0}</span>
      </button>`).join('');
    bandEl.querySelectorAll('.band-item').forEach(b=>{
      b.onclick=()=>{
        activeCountry = activeCountry===b.dataset.country ? null : b.dataset.country;
        invalidateFilterCache(); /* v7 · M10 */
        renderBand();
        if(!selected&&!stressId) refreshStyles();
      };
    });
  } else {
    const counts={};
    NODES.forEach(n=>{ counts[n.cat]=(counts[n.cat]||0)+1; });
    bandEl.innerHTML=Object.keys(CATS).map(k=>`
      <button class="band-item${activeCat===k?' active':''}" data-cat="${k}">
        <span class="bd" style="background:${catColor(k)}"></span>${catLabel(k)} <span class="bc">${counts[k]||0}</span>
      </button>`).join('');
    bandEl.querySelectorAll('.band-item').forEach(b=>{
      b.onclick=()=>{
        const k=b.dataset.cat;
        activeCat = activeCat===k ? null : k;
        catChips.querySelectorAll('.chip').forEach(x=>x.classList.toggle('active',x.dataset.cat===activeCat));
        invalidateFilterCache(); /* v7 · M10 */
        renderBand();
        if(!selected&&!stressId) refreshStyles();
      };
    });
  }
}

/* ===================== Pestañas (v7: 4 pestañas) ===================== */
let activeTab='map';
function switchTab(tab){
  activeTab=tab;
  document.querySelectorAll('.tabs .tab').forEach(b=>b.classList.toggle('active',b.dataset.tab===tab));
  const isMap=tab==='map', isAnalysis=tab==='analysis', isGeo=tab==='geo';
  const isSim=tab==='simulation', isSpace=tab==='space', isTerm=tab==='terminal';
  const isCanvas=tab==='canvas', isTkg=tab==='tkg', isGuia=tab==='guia';
  document.querySelector('main').style.display = isMap?'flex':'none';
  document.getElementById('toolbar').style.display = isMap?'flex':'none';
  document.getElementById('market').style.display = tab==='market'?'block':'none';
  const anEl=document.getElementById('analysis-panel');
  if(anEl) anEl.style.display = isAnalysis?'block':'none';
  if(isAnalysis && window._dossierRedrawIfNeeded) setTimeout(window._dossierRedrawIfNeeded, 0);   /* Dossier: redibujo pendiente */
  const geoEl=document.getElementById('geo-panel');
  if(geoEl) geoEl.style.display = isGeo?'block':'none';
  const simEl=document.getElementById('simulation-panel');
  if(simEl) simEl.style.display = isSim?'block':'none';
  const spaceEl=document.getElementById('space-panel');
  if(spaceEl) spaceEl.style.display = isSpace?'block':'none';
  const termEl=document.getElementById('terminal-panel');
  if(termEl) termEl.style.display = isTerm?'flex':'none';
  const cvEl=document.getElementById('canvas-panel');
  if(cvEl) cvEl.style.display = isCanvas?'flex':'none';
  const tkgEl=document.getElementById('tkg-panel');
  if(tkgEl) tkgEl.style.display = isTkg?'block':'none';
  const guiaEl=document.getElementById('guia-panel');
  if(guiaEl) guiaEl.style.display = isGuia?'block':'none';
  const isCrypto=tab==='crypto';
  const cryEl=document.getElementById('crypto-panel');
  if(cryEl) cryEl.style.display = isCrypto?'block':'none';
  const isPf=tab==='portfolios';
  const pfEl=document.getElementById('portfolios-panel');
  if(pfEl) pfEl.style.display = isPf?'block':'none';
  // Animate
  const _tabEls = [
    isMap && document.querySelector('main'),
    tab==='market' && document.getElementById('market'),
    isAnalysis && anEl, isGeo && geoEl, isSim && simEl, isSpace && spaceEl,
    isTerm && termEl, isCanvas && cvEl, isTkg && tkgEl, isGuia && guiaEl,
    isCrypto && cryEl, isPf && pfEl,
  ].filter(Boolean);
  _tabEls.forEach(el => {
    el.classList.remove('tab-anim-in');
    void el.offsetWidth;
    el.classList.add('tab-anim-in');
    setTimeout(() => el.classList.remove('tab-anim-in'), 220);
  });
  if(isMap){ resize(); }
  else if(isAnalysis){ renderAnalysis(); }
  else if(isGeo){ renderGeoPanel(); }
  else if(isSim){ initSimTab(); }
  else if(isSpace){ initSpaceTab(); }
  else if(isTerm){ initTerminalTab(); }
  else if(isCanvas){ initCanvasTab(); }
  else if(isTkg){ if(typeof initTKGTab==='function') initTKGTab(); }
  else if(isGuia){ if(typeof initGuiaTab==='function') initGuiaTab(); }
  else if(isCrypto){ if(window.KhipuCrypto) window.KhipuCrypto.init(); }
  else if(isPf){ if(window.KhipuPortfolios) window.KhipuPortfolios.mount('portfolios-panel'); }
  else {
    renderMarket();
    if(!MKT.ts){ fetchQuotes(); }
  }
}

// Desde la ficha de una empresa → llevar a Carteras con la empresa lista para añadir.
window.addToPortfolio = function(nodeId){
  switchTab('portfolios');
  const n = (window.NODE_BY_ID||{})[nodeId];
  if (typeof toast==='function' && n) toast((LANG==='en'?'Search "':'Busca «')+ (n.label||nodeId) +(LANG==='en'?'" here to add it to a portfolio.':'» aquí para añadirla a una cartera.'));
};

/* ===================== v7 · M6: betweenness centrality real (Brandes) ===================== */
let _bcCache=null;
function computeBetweenness(nodes,links){
  const ids=nodes.map(n=>n.id);
  const adj={};
  ids.forEach(id=>adj[id]=[]);
  links.forEach(l=>{ adj[lid(l.source)]?.push(lid(l.target)); });
  const BC=Object.fromEntries(ids.map(id=>[id,0]));
  ids.forEach(s=>{
    const stack=[], pred={}, sigma={}, dist={}, delta={};
    ids.forEach(w=>{ pred[w]=[]; sigma[w]=0; dist[w]=-1; delta[w]=0; });
    sigma[s]=1; dist[s]=0;
    const Q=[s];
    while(Q.length){
      const v=Q.shift(); stack.push(v);
      adj[v].forEach(w=>{
        if(dist[w]<0){ dist[w]=dist[v]+1; Q.push(w); }
        if(dist[w]===dist[v]+1){ sigma[w]+=sigma[v]; pred[w].push(v); }
      });
    }
    while(stack.length){
      const w=stack.pop();
      pred[w].forEach(v=>{ delta[v]+=(sigma[v]/sigma[w])*(1+delta[w]); });
      if(w!==s) BC[w]+=delta[w];
    }
  });
  const maxBC=Math.max(...Object.values(BC))||1;
  Object.keys(BC).forEach(k=>BC[k]/=maxBC);
  return BC;
}
function getBetweenness(){ if(!_bcCache) _bcCache=computeBetweenness(NODES,LINKS); return _bcCache; }

function renderAnalysis(){
  const outDeg={}, inDeg={};
  NODES.forEach(n=>{outDeg[n.id]=0;inDeg[n.id]=0;});
  LINKS.forEach(l=>{
    const s=lid(l.source), t=lid(l.target);
    outDeg[s]=(outDeg[s]||0)+1;
    inDeg[t]=(inDeg[t]||0)+1;
  });
  const anSub=document.getElementById('an-subtitle');
  if(anSub) anSub.textContent=t('an_sub').replace('{n}',NODES.length).replace('{l}',LINKS.length);
  if(typeof window.renderKhipuInsights==='function') window.renderKhipuInsights();  // llena #an-insights
  if(typeof window.renderInsightsHistory==='function') window.renderInsightsHistory();  // llena #an-history
  if(typeof window.renderMatrixView==='function') window.renderMatrixView();        // llena #an-matrix (las 9 matrices)
  document.getElementById('an-nodes').textContent=NODES.length;
  document.getElementById('an-links').textContent=LINKS.length;
  document.getElementById('an-density').textContent=((LINKS.length/(NODES.length*(NODES.length-1)))*100).toFixed(2)+'%';
  document.getElementById('an-preipo').textContent=NODES.filter(n=>n.preipo).length;
  document.getElementById('an-risk').textContent=Object.values(NODE_META).filter(m=>m.risk==='critical'||m.risk==='high').length;

  const sortedOut=[...NODES].sort((a,b)=>(outDeg[b.id]||0)-(outDeg[a.id]||0)).slice(0,10);
  document.getElementById('an-top-out').innerHTML=sortedOut.map(n=>`
    <tr onclick="jumpTo('${n.id}');switchTab('map')" style="cursor:pointer">
      <td style="font-weight:600">${esc(n.label)}</td>
      <td style="font-size:11px;color:var(--ink-3);text-align:right">${catLabel(n.cat)}</td>
      <td style="text-align:right">${outDeg[n.id]||0}</td>
      <td style="text-align:right;color:var(--ink-3)">${inDeg[n.id]||0}</td>
    </tr>`).join('');

  const sortedIn=[...NODES].sort((a,b)=>(inDeg[b.id]||0)-(inDeg[a.id]||0)).slice(0,10);
  document.getElementById('an-top-in').innerHTML=sortedIn.map(n=>`
    <tr onclick="jumpTo('${n.id}');switchTab('map')" style="cursor:pointer">
      <td style="font-weight:600">${esc(n.label)}</td>
      <td style="font-size:11px;color:var(--ink-3);text-align:right">${catLabel(n.cat)}</td>
      <td style="text-align:right;color:var(--c-cloud)">${inDeg[n.id]||0}</td>
      <td style="text-align:right;color:var(--ink-3)">${outDeg[n.id]||0}</td>
    </tr>`).join('');

  const riskNodes=NODES.filter(n=>NODE_META[n.id]&&(NODE_META[n.id].risk==='critical'||NODE_META[n.id].risk==='high'));
  document.getElementById('an-geo-risk').innerHTML=riskNodes.map(n=>{
    const m=NODE_META[n.id];
    const riskColor=m.risk==='critical'?'var(--danger)':'var(--gold)';
    return `<tr onclick="jumpTo('${n.id}');switchTab('map')" style="cursor:pointer">
      <td style="font-weight:600">${esc(n.label)}</td>
      <td style="color:var(--ink-3);font-size:11px">${esc(n.country||n.loc||'—')}</td>
      <td style="color:${riskColor};font-weight:700;text-transform:uppercase;font-size:11px">${m.risk}</td>
    </tr>`;
  }).join('');

  /* v7 · M9: distribución por tipo como gráfico de barras SVG */
  const typeCounts={};
  LINKS.forEach(l=>{const tp=l.type||'supply';typeCounts[tp]=(typeCounts[tp]||0)+1;});
  const typeOrder=['supply','fab','license','cloud','invest','deploy','partner'];
  const maxCnt=Math.max(...typeOrder.map(tp=>typeCounts[tp]||0))||1;
  const barH=28, gap=8, svgW=500;
  const svgHTML='<svg width="100%" viewBox="0 0 '+svgW+' '+((barH+gap)*typeOrder.length)+'" style="margin-top:8px">'+
    typeOrder.map((tp,i)=>{
      const cnt=typeCounts[tp]||0;
      const pct=((cnt/LINKS.length)*100).toFixed(1);
      const bw=Math.max(2,Math.round((cnt/maxCnt)*(svgW-200)));
      const clr=getLinkColor(tp);
      const y=i*(barH+gap);
      return `<text x="0" y="${y+barH*.7}" font-size="12" fill="var(--ink-2)" font-family="Archivo,sans-serif">${ltLabel(tp)}</text>
        <rect x="130" y="${y+2}" width="${bw}" height="${barH-4}" rx="4" fill="${clr}" opacity=".85"/>
        <text x="${130+bw+8}" y="${y+barH*.7}" font-size="11" fill="var(--ink-3)" font-family="JetBrains Mono,monospace">${cnt} (${pct}%)</text>`;
    }).join('')+'</svg>';
  document.getElementById('an-link-types-viz').innerHTML=svgHTML;

  /* v7 · M6: betweenness real (Brandes), cacheada */
  const BC=getBetweenness();
  const topBC=[...NODES].sort((a,b)=>(BC[b.id]||0)-(BC[a.id]||0)).slice(0,8);
  const betInterp=LANG==='en'
    ? ['Most critical node','Essential intermediary','Essential intermediary','Major hub','Major hub','Major hub','Relevant node','Relevant node']
    : ['Nodo más crítico','Intermediario esencial','Intermediario esencial','Hub importante','Hub importante','Hub importante','Nodo relevante','Nodo relevante'];
  document.getElementById('an-betweenness').innerHTML=topBC.map((n,i)=>{
    const score=BC[n.id]||0;
    const w=Math.max(4,Math.round(score*110));
    return `<tr onclick="jumpTo('${n.id}');switchTab('map')" style="cursor:pointer">
      <td style="font-weight:600">${esc(n.label)}</td>
      <td style="font-size:11px;color:var(--ink-3)">${catLabel(n.cat)}</td>
      <td><div style="display:flex;align-items:center;gap:8px;justify-content:flex-end">
        <div style="background:${catColor(n.cat)};height:6px;border-radius:3px;width:${w}px;min-width:4px"></div>
        <span style="font-family:'JetBrains Mono',monospace;font-size:11px">${score.toFixed(3)}</span>
      </div></td>
      <td style="font-size:11px;color:var(--ink-3)">${betInterp[i]||betInterp[betInterp.length-1]}</td>
    </tr>`;
  }).join('');

  const isolated=NODES.filter(n=>(outDeg[n.id]||0)===0);
  document.getElementById('an-isolated').innerHTML=isolated.length===0
    ? '<span style="color:#4E8B1E">✓ Todos los nodos tienen al menos una conexión de salida</span>'
    : isolated.map(n=>`<span style="margin:2px;padding:3px 9px;background:var(--surface-2);border-radius:12px;font-size:12px;cursor:pointer;display:inline-block" onclick="jumpTo('${n.id}');switchTab('map')">${esc(n.label)}</span>`).join('');
}

/* ===================== v7 · M5: pestaña Geopolítica ===================== */
const GEO_REGION_OF={EEUU:'usa',ReinoUnido:'europe',PaisesBajos:'europe',Alemania:'europe',Francia:'europe',RestoEuropa:'europe',Japon:'japan',Corea:'korea',Taiwan:'taiwan',China:'china',RestoMundo:'row'};
const GEO_REGIONS={
  usa:   {es:'EE.UU.',          en:'USA',           tint:'#2E6FB7'},
  europe:{es:'Europa',          en:'Europe',        tint:'#5F6B52'},
  china: {es:'China',           en:'China',         tint:'#C8392F'},
  taiwan:{es:'Taiwán',          en:'Taiwan',        tint:'#18A05A'},
  japan: {es:'Japón',           en:'Japan',         tint:'#C2185B'},
  korea: {es:'Corea del Sur',   en:'South Korea',   tint:'#6B5DD3'},
  row:   {es:'Resto del mundo', en:'Rest of World', tint:'#8A857A'},
};
function renderGeoPanel(){
  /* Pestaña Geopolítica = WORLD MONITOR (engine/worldmonitor.js). mount() es
     idempotente: la 1ª vez arma el globo y carga los datos; después re-etiqueta
     (idioma/tema), redimensiona y reanuda el render. Lo llaman switchTab('geo'),
     la Cabina (ADOPT_TABS.geo) y los cambios de idioma/tema. */
  const root=document.getElementById('wm-root');
  if(root && window.KhipuWorld) window.KhipuWorld.mount(root);
}

// Cablea cada sub-pestaña a switchTab por su data-tab. EXCEPCIÓN: los botones
// con su propio onclick y SIN data-tab (p.ej. 🪐 tab-3d → _go3D) — este bucle
// los pisaba con switchTab(undefined) y por eso "el 3D no daba" (bug raíz
// 2026-07-13). Solo cablea los que declaran data-tab.
document.querySelectorAll('.tabs .tab').forEach(b=>{ if(b.dataset.tab) b.onclick=()=>switchTab(b.dataset.tab); });

/* ===================== Mercado en vivo (Marketstack v2) ===================== */
var MKT = {
  quotes: (function(){
    // R9: entradas viejas con live:true (booleano) de versiones anteriores alimentaban
    // aritmética ((true − prev)/prev ≈ −99 %): se sanean al cargar
    let q = {}; try{ q = JSON.parse(localStorage.getItem('eco_quotes')||'{}') || {}; }catch(e){ q = {}; }
    Object.keys(q).forEach(k=>{ const v = q[k]; if(v && typeof v === 'object' && v.live != null && typeof v.live !== 'number') delete v.live; });
    return q;
  })(),
  ts: Number(localStorage.getItem('eco_quotes_ts'))||null,
  pos: JSON.parse(localStorage.getItem('eco_pos')||'{}'),
  filter:'all', editing:null, loading:false,
};
const fmtN=(v,dec=2)=> v==null||isNaN(v) ? '—' : Number(v).toLocaleString('en-US',{minimumFractionDigits:dec,maximumFractionDigits:dec});
const fmtPct=v=> v==null||isNaN(v) ? '—' : (v>=0?'+':'')+ (v*100).toFixed(2)+'%';
function savePos(){ localStorage.setItem('eco_pos',JSON.stringify(MKT.pos)); }
function quoteOf(n){ return n.mkt ? MKT.quotes[n.mkt] : null; }
/* ── CONTRATO de MKT.quotes[ticker] (2026-10-04) ─────────────────────────────
   {close, prev, pct?, live?:<precio NUMÉRICO o ausente>, src:'finnhub'|'yahoo'|
    'marketstack', via?:'live_caps', as_of:<ISO>, currency?, converted?}
   `live` NUNCA es booleano (antes LivePrices escribía live:true y
   parseFloat(q.live) daba NaN → "—" en la Terminal y precio 0 al operar).
   Precio a mostrar: SIEMPRE window.quotePx(q). "En vivo": quoteIsLive(q). */
window.quotePx = q => { if(!q) return 0; const v = typeof q.live==='number' ? q.live : q.close; return Number(v)||0; };
window.quoteAge = q => { if(!q||!q.as_of) return null; const t=Date.parse(q.as_of); return isNaN(t)?null:Math.max(0,Math.round((Date.now()-t)/1000)); };
window.quoteIsLive = q => { if(!q||!(quotePx(q)>0)||!q.src||q.src==='marketstack') return false; const a=quoteAge(q); return a==null || a<15*60; };
window.quoteSrcName = src => ({finnhub:'Finnhub', yahoo:'Yahoo', marketstack:'Marketstack (EOD)', live:'Finnhub/Yahoo'})[src] || (src||'');
window.quoteAgoText = sec => { const en=(LANG==='en'); if(sec==null) return '';
  if(sec<60) return en?`${sec}s ago`:`hace ${sec} s`;
  if(sec<3600){ const m=Math.round(sec/60); return en?`${m} min ago`:`hace ${m} min`; }
  if(sec<86400){ const h=Math.round(sec/3600); return en?`${h} h ago`:`hace ${h} h`; }
  const d=Math.round(sec/86400); return en?`${d} d ago`:`hace ${d} d`; };
// bolsa a partir del sufijo Yahoo del ticker (ADANIPORTS.NS → NSE, 4401.T → TSE…)
window.quoteExchange = tk => { const m=String(tk||'').match(/\.([A-Z]+)$/); const sfx=m?m[1]:'';
  const EX={NS:'NSE',BO:'BSE',T:'TSE',HK:'HKEX',SS:'SSE',SZ:'SZSE',KS:'KRX',KQ:'KOSDAQ',TW:'TWSE',TWO:'TPEx',L:'LSE',DE:'XETRA',F:'FRA',
    PA:'Euronext',AS:'Euronext',BR:'Euronext',IR:'Euronext',MI:'Borsa Italiana',MC:'BME',SW:'SIX',ST:'OMX',CO:'OMX',HE:'OMX',OL:'Oslo',
    TO:'TSX',V:'TSXV',AX:'ASX',SA:'B3',MX:'BMV',JO:'JSE',TA:'TASE',SI:'SGX',KL:'Bursa',BK:'SET',JK:'IDX',VI:'Wiener Börse'};
  return EX[sfx] || sfx || (LANG==='en'?'US':'EE.UU.'); };
/* Chip de fuente + antigüedad del precio: ● verde <2 min · ámbar <1 h · gris EOD/viejo.
   Sin precio: punto apagado con "Sin precio en vivo para esta bolsa (NSE)". */
window.quoteSrcChip = (q, tk) => {
  if(!(quotePx(q)>0)){
    if(!tk) return '';
    const tip = (LANG==='en' ? 'No live price for this exchange' : 'Sin precio en vivo para esta bolsa') + ' (' + quoteExchange(tk) + ')';
    return `<span class="q-src none" title="${esc(tip)}">●</span>`;
  }
  const age = quoteAge(q);
  const eod = q.src==='marketstack' || (age!=null && age>=3600);
  const cls = eod ? 'eod' : (age!=null && age<120 ? 'fresh' : 'warm');
  const when = q.src==='marketstack' ? (LANG==='en'?'close (EOD)':'cierre (EOD)') : quoteAgoText(age);
  const tip = (quoteSrcName(q.src) || (LANG==='en'?'cached':'caché')) + (when ? ' · ' + when : '');
  return `<span class="q-src ${cls}" title="${esc(tip)}">●</span>`;
};

/* ── Panel de empresa privada (pre-IPO) — Fase 4 ──────────────────────────── */
function renderPreipoPanel(d){
  const intel = (window.PREIPO_INTEL||{})[d.id] || {};
  const val = intel.valuation || (/[$~]\d|\bB\b|valuation/i.test(d.ticker||'') ? d.ticker : (d.ticker||'—'));
  const raised = intel.total_raised || '—';
  const ipo = intel.ipo_timeline || (d.growth||'').replace(/^[^A-Za-z0-9$]+/,'') || '—';
  const invChip = name => {
    const n = NODE_BY_ID[name];
    return n ? `<button class="pp-inv pp-inv-link" onclick="jumpTo('${n.id}')" title="Ver ${esc(n.label)}">${esc(n.label)}</button>`
             : `<span class="pp-inv">${esc(name)}</span>`;
  };
  const investors = (intel.investors||[]).map(invChip).join('');
  const rounds = (intel.rounds||[]).map(r=>`<div class="pp-round"><span class="pp-amt">${esc(r.amount||'')}</span><span class="pp-rnd">${esc(r.round||'')}</span><span class="pp-date">${esc(r.date||'')}</span>${r.lead?`<span class="pp-lead">${esc(r.lead)}</span>`:''}</div>`).join('');
  const milestones = (intel.milestones||[]).map(m=>`<div class="pp-ms"><span class="pp-ms-date">${esc(m.date||'')}</span><span>${esc(m.event)}</span></div>`).join('');
  return `<div class="preipo-panel">
    <div class="pp-head">🔒 ${LANG==='en'?'PRIVATE COMPANY':'EMPRESA PRIVADA'}</div>
    <div class="pp-kpis">
      <div class="pp-kpi"><div class="pp-kl">${LANG==='en'?'Valuation':'Valoración'}</div><div class="pp-kv" style="font-size:13px">${esc(val)}</div></div>
      <div class="pp-kpi"><div class="pp-kl">${LANG==='en'?'Total raised':'Levantado'}</div><div class="pp-kv">${esc(raised)}</div></div>
      <div class="pp-kpi"><div class="pp-kl">IPO</div><div class="pp-kv" style="font-size:11px">${esc(ipo)}</div></div>
    </div>
    ${investors?`<div class="pp-sec"><div class="pp-sl">${LANG==='en'?'Key investors':'Inversores clave'}</div><div class="pp-invs">${investors}</div></div>`:''}
    ${rounds?`<div class="pp-sec"><div class="pp-sl">${LANG==='en'?'Funding rounds':'Rondas de financiación'}</div>${rounds}</div>`:''}
    ${milestones?`<div class="pp-sec"><div class="pp-sl">${LANG==='en'?'Recent milestones':'Hitos recientes'}</div>${milestones}</div>`:''}
  </div>`;
}

/* ── Carteras editables: capa de usuario sobre el `port` estático ──────────── */
var USER_PORTFOLIOS = JSON.parse(localStorage.getItem('eco_user_pf')||'{}');
['C1','C2'].forEach(k=>{ if(!USER_PORTFOLIOS[k]) USER_PORTFOLIOS[k]={add:[],rm:[]}; });
function inPortfolio(n, pf){
  if(!n||!pf) return false;
  const u=USER_PORTFOLIOS[pf]||{add:[],rm:[]};
  if(u.rm && u.rm.indexOf(n.id)>=0) return false;        // removida por el usuario
  if((n.port||'').includes(pf)) return true;             // estática
  return !!(u.add && u.add.indexOf(n.id)>=0);            // añadida por el usuario
}

function setStatus(msg){ document.getElementById('mk-status').textContent=msg; }

function _persistQuotes(){
  try{ localStorage.setItem('eco_quotes',JSON.stringify(MKT.quotes)); localStorage.setItem('eco_quotes_ts',String(MKT.ts||Date.now())); }catch(e){}
}
/* ── CARGADOR POR LOTES de precios EN VIVO (2026-10-04) ──────────────────────
   569 tickers → POST /api/quotes/live en lotes de 100 (2 en paralelo). El
   server (core/quotes.fetch_quotes_live) va Finnhub→Yahoo para TODO ticker,
   en paralelo, con caché de 15 s. Antes solo se pedían los primeros 100 y la
   Terminal mostraba "–" para el resto (ADANIPORTS.NS, 4401.T…). Reemplaza al
   viejo LivePrices.seed() (~1.090 req/min a /api/quote → 429 silenciosos).
   Es el ÚNICO camino: fetchQuotes, el Live Data Manager y el poll de
   LivePrices pasan por aquí. Nunca pisa una cotización MÁS NUEVA. */
const LIVE_BATCH = 100;
function _mergeLiveQuote(tk, q){
  if(!q || typeof q!=='object') return false;
  const px = (typeof q.live==='number' && q.live>0) ? q.live : (Number(q.close)>0 ? Number(q.close) : 0);
  if(!(px>0)) return false;
  const cur = MKT.quotes[tk];
  // Solo una cotización DIRECTA más nueva (p.ej. un trade del WebSocket de hace
  // 2 s) bloquea el merge; el relleno de live_caps (via) nunca manda sobre el lote.
  if(cur && quotePx(cur)>0 && cur.src && cur.src!=='marketstack' && cur.via!=='live_caps' && cur.as_of && q.as_of){
    const a=Date.parse(cur.as_of), b=Date.parse(q.as_of);
    if(!isNaN(a) && !isNaN(b) && a>b) return false;
  }
  MKT.quotes[tk] = Object.assign({}, cur||{}, {
    close: px, live: px,
    prev: (q.prev!=null && isFinite(+q.prev)) ? +q.prev : (cur && cur.prev!=null ? cur.prev : null),
    pct: (q.pct!=null && isFinite(+q.pct)) ? +q.pct : null,
    src: q.provider || q.src || 'live', as_of: q.as_of || new Date().toISOString(),
    currency: q.currency || 'USD', converted: !!q.converted, market_state: q.market_state || null,
  });
  delete MKT.quotes[tk].via;
  return true;
}
function _afterQuotesMerged(){
  _persistQuotes();
  try{ if(typeof window._termRefreshPrices==='function') window._termRefreshPrices(); }catch(e){}
  try{ if(typeof activeTab!=='undefined' && activeTab==='market' && typeof renderMarket==='function') renderMarket(); }catch(e){}
  try{ if(window.KhipuLive && typeof window.KhipuLive.tick==='function') window.KhipuLive.tick(); }catch(e){}
  try{ const up=window._graph3d_updateLiveColors; if(up) up(MKT.quotes); }catch(e){}
  try{ if(typeof LivePrices!=='undefined' && LivePrices.updateSummary) LivePrices.updateSummary(); }catch(e){}
  try{ window.dispatchEvent(new CustomEvent('khipu:quotes', {detail: MKT.liveMeta||null})); }catch(e){}
}
window.loadLiveQuotes = function(opts){
  opts = opts || {};
  if(window._liveLoading) return window._liveLoading;          // ya en curso: no duplicar
  const full = !opts.tickers;
  const all = opts.tickers || [...new Set(NODES.filter(n=>n.mkt).map(n=>n.mkt))];
  const run = (async()=>{
    const batches=[]; for(let i=0;i<all.length;i+=LIVE_BATCH) batches.push(all.slice(i,i+LIVE_BATCH));
    let got=0, failed=0, quota=false; const srcs={};
    const one = async b => {
      try{
        const r = await fetch(BASE+'/api/quotes/live',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tickers:b})});
        if(!r.ok){ failed++; return; }
        const j = await r.json(); const map = (j && j.quotes) ? j.quotes : (j||{});
        if(j && j.finnhub_quota) quota=true;
        Object.keys(map).forEach(tk=>{ const q=map[tk]; if(_mergeLiveQuote(tk,q)){ got++; const k=q.provider||'live'; srcs[k]=(srcs[k]||0)+1; } });
      }catch(e){ failed++; }
    };
    for(let i=0;i<batches.length;i+=2){
      await Promise.all(batches.slice(i,i+2).map(one));
      if(got && i+2<batches.length) _afterQuotesMerged();          // pintar progresivamente
    }
    if(got){ MKT.ts=Date.now(); MKT.src='live'; }
    if(full || !MKT.liveMeta) MKT.liveMeta={got, failed, batches:batches.length, finnhub_quota:quota, sources:srcs, at:Date.now(), done:true};
    else if(quota) MKT.liveMeta.finnhub_quota=true;
    _afterQuotesMerged();
    // ⚠ de tickers sin precio en NINGUNA fuente (espera a que _liveLoading se libere)
    if(full && got && typeof validateTickers==='function') setTimeout(()=>{ try{ validateTickers(); }catch(e){} }, 50);
    return {got, failed, batches:batches.length, finnhub_quota:quota};
  })();
  window._liveLoading = run.catch(()=>({got:0, failed:1, batches:0})).finally(()=>{ window._liveLoading=null; });
  return window._liveLoading;
};

function _processMktData(j){
  if(j.error) throw new Error(j.error.message||j.error.code||'API error');
  const q={};
  (j.data||[]).forEach(row=>{
    const s=(row.symbol||'').toUpperCase(); if(!s||row.close==null) return;
    if(!q[s]) q[s]={close:row.close, date:(row.date||'').slice(0,10)};
    else if(q[s].prev==null) q[s].prev=row.close;
  });
  // Alias: 'MDB.XNGS' → 'MDB' (sufijo MIC de Marketstack → ticker del catálogo).
  // SOLO tickers de EE.UU. (sin punto): Marketstack entrega las otras bolsas en
  // moneda local y pintarla con "$" sería mentir; esas vienen de Yahoo en USD.
  const _knownMkt = new Set((typeof NODES!=='undefined'?NODES:[]).filter(n=>n.mkt&&!n.mkt.includes('.')).map(n=>n.mkt));
  Object.keys(q).forEach(sym=>{
    if(sym.includes('.')){
      const base=sym.split('.')[0];
      if(_knownMkt.has(base)&&!q[base]) q[base]=q[sym];
    }
  });
  if(!Object.keys(q).length) throw new Error('Sin datos / no data');
  // MERGE, nunca reemplazo: un cierre EOD jamás pisa una cotización en vivo
  // más nueva (se compara as_of). Antes `MKT.quotes=q` borraba Finnhub/Yahoo.
  let n=0;
  Object.keys(q).forEach(sym=>{
    if(!_knownMkt.has(sym)) return;
    const row=q[sym]; const asOf=row.date ? row.date+'T21:00:00Z' : null;
    const cur=MKT.quotes[sym];
    if(cur && quotePx(cur)>0 && cur.src && cur.src!=='marketstack'){
      const curT=Date.parse(cur.as_of||''), newT=Date.parse(asOf||'');
      if(isNaN(curT) || isNaN(newT) || curT>=newT) return;       // lo vivo manda
    }
    const prev=(row.prev!=null)?row.prev:(cur&&cur.prev!=null?cur.prev:null);
    MKT.quotes[sym]=Object.assign({}, cur||{}, {close:row.close, prev, pct:(prev?(row.close-prev)/prev*100:null),
      src:'marketstack', as_of:asOf, date:row.date});
    delete MKT.quotes[sym].live; delete MKT.quotes[sym].via;
    n++;
  });
  if(n){
    if(!MKT.ts) MKT.ts=Date.now();
    _persistQuotes();
    if (typeof window._termRefreshPrices === 'function') window._termRefreshPrices();
  }
  return n;
}
async function fetchQuotes(){
  if(MKT.loading) return;
  MKT.loading=true;
  const btn=document.getElementById('mk-refresh'); if(btn) btn.disabled=true;
  setStatus(t('mk_loading'));
  let ok=false;
  try{
    // 1) EN VIVO primero (Finnhub→Yahoo, todas las bolsas, por lotes)
    const r = await window.loadLiveQuotes();
    ok = !!(r && r.got);
    // 2) Marketstack = respaldo EOD OPCIONAL: solo con clave, solo para los
    //    tickers de EE.UU. que quedaron sin precio, y nunca pisa lo vivo.
    const gaps = NODES.some(n=>n.mkt && !n.mkt.includes('.') && !(quotePx(MKT.quotes[n.mkt])>0));
    // `Keys` vive dentro del IIFE de V8 (más abajo): aquí se lee por window.V8 — antes daba ReferenceError y la
    // ventana de Mercado mostraba «Error al obtener precios: Keys is not defined» aunque los precios ya habían llegado.
    const _mkKeys = window.V8 && window.V8.Keys;
    if(_mkKeys && _mkKeys.has('marketstack') && gaps){
      try{
        const syms=[...new Set(NODES.filter(n=>n.mkt&&!n.mkt.includes('.')&&!(quotePx(MKT.quotes[n.mkt])>0)).map(n=>n.mkt))];
        const rr=await fetch(BASE+'/api/marketstack?symbols='+encodeURIComponent(syms.join(',')));
        const j=await rr.json();
        if(!j.error && _processMktData(j)>0) ok=true;
      }catch(e){ /* respaldo opcional: silencio */ }
    }
    if(!ok) setStatus(LANG==='en' ? '⚠ No prices from Finnhub or Yahoo — open 🩺' : '⚠ Sin precios de Finnhub ni de Yahoo — abre 🩺');
  }catch(e){
    setStatus('⚠ '+(LANG==='en'?'Error fetching prices: ':'Error al obtener precios: ')+String(e.message).slice(0,60));
  }
  MKT.loading=false; if(btn) btn.disabled=false;
  renderMarket(!ok);
  validateTickers();
}
document.getElementById('mk-refresh').onclick=fetchQuotes;

/* ── Ticker validation: flag nodes with mkt but no quote ── */
async function validateTickers(){
  // Espera al lote en vivo: el ⚠ solo se marca si el ticker falta en
  // /api/quotes/live Y en live_caps (antes se marcaba apenas Marketstack callaba).
  try{ if(window._liveLoading) await window._liveLoading; }catch(e){}
  const anyPrice = Object.keys(MKT.quotes||{}).some(k=>quotePx(MKT.quotes[k])>0);
  if(!anyPrice) return;                 // fallo GLOBAL de fuentes: no es culpa del ticker
  const meta = window.NODE_META || {};
  const hasCapPx = n => { const l=(meta[n.id]||{}).mktcap_live; return !!(l && l.price!=null && isFinite(+l.price) && +l.price>0); };
  const missing=NODES.filter(n=>n.mkt&&!n.preipo&&!(quotePx(MKT.quotes[n.mkt])>0)&&!hasCapPx(n));
  if(!window._tickerWarnings) window._tickerWarnings=new Set();
  // ya tienen precio → quitar el ⚠ viejo
  NODES.forEach(n=>{ if(n.mkt && window._tickerWarnings.has(n.id) && quotePx(MKT.quotes[n.mkt])>0){ window._tickerWarnings.delete(n.id);
    document.querySelectorAll(`[data-ticker="${CSS.escape(n.mkt)}"] .tk-warn`).forEach(x=>x.remove()); } });
  if(!missing.length) return;
  const warnTip = LANG==='en' ? 'No price from Finnhub, Yahoo or the market-cap batch · the ticker may have changed'
                              : 'Sin precio en Finnhub, Yahoo ni el lote de capitalización · el ticker puede haber cambiado';
  missing.forEach(n=>{
    window._tickerWarnings.add(n.id);
    document.querySelectorAll(`[data-ticker="${CSS.escape(n.mkt)}"]`).forEach(row=>{
      if(!row.querySelector('.tk-warn')){
        const td=row.querySelector('td');
        if(td) td.insertAdjacentHTML('beforeend',' <span class="tk-warn" title="'+esc(warnTip)+'" style="color:#f59e0b;font-size:10px;cursor:help">⚠</span>');
      }
    });
  });
  try{
    const r=await fetch(BASE+'/api/ipo_calendar');
    const data=await r.json();
    const ipos=data.ipoCalendar||[];
    const preIpoNodes=NODES.filter(n=>n.preipo);
    const matches=[];
    ipos.forEach(ipo=>{
      const name=(ipo.name||'').toLowerCase();
      preIpoNodes.forEach(n=>{
        const l=n.label.toLowerCase();
        if(name.includes(l.split(' ')[0])||l.includes((ipo.name||'').split(' ')[0].toLowerCase()))
          matches.push({node:n,ipo});
      });
    });
    if(matches.length) _showEventsAlert(matches.map(m=>
      `📋 <strong>${m.node.label}</strong> — IPO detectada: <span style="color:#22c55e;font-weight:700">${m.ipo.symbol||'?'}</span> · ${m.ipo.date||''} · $${m.ipo.price||'?'}/sh`
    ));
  }catch(e){/* silent */}
}
function _showEventsAlert(items){
  if(!items.length) return;
  const old=document.getElementById('events-alert-bar'); if(old) old.remove();
  const bar=document.createElement('div');
  bar.id='events-alert-bar';
  bar.style.cssText='position:fixed;bottom:48px;left:50%;transform:translateX(-50%);z-index:800;background:rgba(8,15,28,.96);border:1px solid rgba(34,197,94,.35);border-radius:10px;padding:10px 16px;min-width:360px;max-width:560px;box-shadow:0 4px 20px rgba(0,0,0,.6);backdrop-filter:blur(8px);font-size:11px;animation:fadeUp .3s ease';
  bar.innerHTML='<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px"><span style="font-weight:700;color:#22c55e;font-size:12px">🔔 Eventos Corporativos Detectados</span><button onclick="this.parentElement.parentElement.remove()" style="background:none;border:none;color:#7a9cc4;font-size:16px;cursor:pointer;line-height:1">×</button></div>'
    +items.map(i=>`<div style="margin-bottom:5px;line-height:1.4;color:#c8daf0">${i}</div>`).join('')
    +`<div style="margin-top:8px;font-size:10px;color:#5b8ab8">Fuente: Finnhub IPO Calendar · ${new Date().toLocaleDateString()}</div>`;
  document.body.appendChild(bar);
  setTimeout(()=>{if(bar.parentNode)bar.remove();},30000);
}
async function loadCorporateEvents(){
  const panel=document.getElementById('mk-events-panel'); if(!panel) return;
  if(panel.style.display!=='none'){panel.style.display='none';return;}
  panel.style.display='block';
  panel.innerHTML='<div style="color:#7a9cc4">Cargando eventos…</div>';
  try{
    const r=await fetch(BASE+'/api/ipo_calendar');
    const data=await r.json();
    const ipos=(data.ipoCalendar||[]).slice(0,18);
    const now=new Date();
    if(!ipos.length){panel.innerHTML='<div style="color:#7a9cc4">No se encontraron IPOs en el rango consultado.</div>';return;}
    panel.innerHTML=
      `<div style="font-weight:700;color:#e8edf5;margin-bottom:8px;font-size:12px">📋 IPOs Recientes / Próximas — Finnhub Calendar</div>`
      +`<div style="display:grid;gap:5px">`
      +ipos.map(e=>{
        const d=new Date(e.date||'');
        const isPast=d<now;
        const matched=NODES.find(n=>{
          const l=n.label.toLowerCase(), nm=(e.name||'').toLowerCase();
          return nm.includes(l.split(' ')[0])||l.includes((e.name||'').split(' ')[0].toLowerCase());
        });
        return `<div style="display:flex;align-items:center;gap:10px;padding:5px 8px;border-radius:5px;background:${matched?'rgba(34,197,94,.08)':'rgba(255,255,255,.03)'};border:1px solid ${matched?'rgba(34,197,94,.2)':'rgba(60,80,120,.15)'}">`
          +`<span style="font-family:monospace;color:${matched?'#22c55e':'#5b8ab8'};font-size:11px;font-weight:700;min-width:60px">${e.symbol||'—'}</span>`
          +`<span style="color:#c8daf0;flex:1">${e.name||''}</span>`
          +(e.price?`<span style="color:#f59e0b;font-size:10px">$${e.price}/sh</span>`:'')
          +`<span style="font-size:10px;color:${isPast?'#5b8ab8':'#22c55e'}">${isPast?'✓':'→'} ${isNaN(d)?'':d.toLocaleDateString()}</span>`
          +(matched?`<span onclick="jumpTo('${matched.id}')" style="cursor:pointer;color:#7ab2e8;font-size:10px;text-decoration:underline;flex-shrink:0">ver nodo</span>`:'')
          +`</div>`;
      }).join('')
      +`</div><div style="margin-top:8px;font-size:10px;color:#5b8ab8">Fuente: Finnhub · ${new Date().toLocaleString()}</div>`;
  }catch(e){panel.innerHTML=`<div style="color:#ef4444">Error: ${e.message}</div>`;}
}

/* Filtro de tabla */
document.querySelectorAll('#mkt-filter button').forEach(b=>{
  b.onclick=()=>{
    MKT.filter=b.dataset.f;
    document.querySelectorAll('#mkt-filter button').forEach(x=>x.classList.toggle('active',x===b));
    renderMarket();
  };
});

// Logo domains por node id (Clearbit Logo API)
// (movido a nodes/nodes_seed.js) — const LOGO_DOMAIN
/* ── Rutas de inversión para empresas privadas / adquiridas ── */
// (movido a nodes/nodes_seed.js) — const INVEST_PATH

function marketRows(){
  let list=NODES.filter(n=>n.mkt||MKT.pos[n.id]);
  if(MKT.filter==='pos') list=list.filter(n=>MKT.pos[n.id]);
  else if(MKT.filter==='C1'||MKT.filter==='C2') list=list.filter(n=>inPortfolio(n, MKT.filter));
  return list.sort((a,b)=>{
    const pa=MKT.pos[a.id]?0:1, pb=MKT.pos[b.id]?0:1;
    return pa-pb || a.label.localeCompare(b.label);
  });
}

function renderMarket(keepStatus){
  if(activeTab!=='market') return;
  const rows=marketRows();
  let totVal=0, totCost=0, totDay=0, anyPos=false;
  rows.forEach(n=>{
    const p=MKT.pos[n.id], q=quoteOf(n);
    if(p&&q&&q.close!=null){
      anyPos=true;
      totVal+=p.sh*q.close; totCost+=p.sh*p.bp;
      if(q.prev!=null) totDay+=p.sh*(q.close-q.prev);
    }
  });
  const elV=document.getElementById('mk-value'), elP=document.getElementById('mk-pnl'), elD=document.getElementById('mk-day');
  elV.textContent = anyPos ? '$'+fmtN(totVal) : '—';
  const pnl=totVal-totCost;
  elP.textContent = anyPos ? (pnl>=0?'+$':'-$')+fmtN(Math.abs(pnl))+' ('+fmtPct(totCost?pnl/totCost:null)+')' : '—';
  elP.className='mv '+(anyPos?(pnl>=0?'up':'down'):'');
  elD.textContent = anyPos ? (totDay>=0?'+$':'-$')+fmtN(Math.abs(totDay)) : '—';
  elD.className='mv '+(anyPos?(totDay>=0?'up':'down'):'');
  if(!keepStatus){
    setStatus(MKT.ts ? t('mk_updated')+' '+new Date(MKT.ts).toLocaleString(LANG==='en'?'en-US':'es-ES',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}) : t('mk_never'));
  }
  document.getElementById('mk-ts').textContent = MKT.ts ? '('+t('mk_cached')+')' : '';

  const tbl=document.getElementById('mk-table');
  tbl.innerHTML=`<thead><tr>
    <th>${t('th_co')}</th><th>${t('th_price')}</th><th>${t('th_chg')}</th>
    <th>${t('th_sh')}</th><th>${t('th_bp')}</th><th>${t('th_val')}</th><th>${t('th_pnl')}</th><th title="NEXUS Risk Score 0-100" onclick="window.explainMetric&&window.explainMetric('nrs')" style="cursor:help">NRS ?</th><th></th>
  </tr></thead><tbody>`+rows.map(n=>{
    const q=quoteOf(n), p=MKT.pos[n.id];
    const chg=(q&&q.prev!=null&&q.close!=null)?(q.close-q.prev)/q.prev:null;
    const val=(p&&q&&q.close!=null)?p.sh*q.close:null;
    const pnlP=(p&&q&&q.close!=null&&p.bp)?(q.close-p.bp)/p.bp:null;
    const nrs=(function(){try{const v=computeNRS(n.id);const c=v<30?'#22c55e':v<60?'#f59e0b':'#ef4444';return `<span style="font-weight:700;color:${c}">${v}</span>`;}catch(e){return '<span class="td-dim">—</span>';}})();
    if(MKT.editing===n.id){
      return `<tr><td onclick="goMap('${n.id}')" style="display:flex;align-items:center;gap:6px">${LOGO_DOMAIN[n.id]?`<img src="https://logo.clearbit.com/${LOGO_DOMAIN[n.id]}?size=32" style="width:20px;height:20px;border-radius:4px;object-fit:contain;flex-shrink:0;background:#fff" onerror="this.style.display='none'" loading="lazy">`:'<span style="width:20px;flex-shrink:0"></span>'}<span>${esc(n.label)} <span class="tk">${esc(n.mkt||'')}</span></span></td>
        <td>${q?'$'+fmtN(q.close):'—'}</td>
        <td colspan="5"><div class="pos-edit">
          <input id="pe-sh" type="number" min="0" step="any" placeholder="${t('th_sh')}" value="${p?p.sh:''}">
          <input id="pe-bp" type="number" min="0" step="any" placeholder="${t('th_bp')}" value="${p?p.bp:''}">
          <button class="pos-btn" onclick="posSave('${n.id}')">✓</button>
          <button class="pos-btn" onclick="posDel('${n.id}')">🗑</button>
          <button class="pos-btn" onclick="posCancel()">✕</button>
        </div></td><td>${nrs}</td><td></td></tr>`;
    }
    return `<tr data-ticker="${esc(n.mkt||'')}"${quoteIsLive(q)?' data-live="1"':''}>
      <td onclick="goMap('${n.id}')" style="display:flex;align-items:center;gap:6px">${LOGO_DOMAIN[n.id]?`<img src="https://logo.clearbit.com/${LOGO_DOMAIN[n.id]}?size=32" style="width:20px;height:20px;border-radius:4px;object-fit:contain;flex-shrink:0;background:#fff" onerror="this.style.display='none'" loading="lazy">`:'<span style="width:20px;flex-shrink:0"></span>'}<span>${esc(n.label)} <span class="tk">${esc(n.mkt||t('mk_npos'))}</span></span>${(window._tickerWarnings&&window._tickerWarnings.has(n.id)&&!(quotePx(q)>0))?' <span class="tk-warn" title="'+esc(LANG==='en'?'No price from Finnhub, Yahoo or the market-cap batch · the ticker may have changed':'Sin precio en Finnhub, Yahoo ni el lote de capitalización · el ticker puede haber cambiado')+'" style="color:#f59e0b;font-size:10px;cursor:help">⚠</span>':''}</td>
      <td class="mk-c-price">${q&&q.close!=null?'$'+fmtN(q.close):'<span class="td-dim">—</span>'}${quoteSrcChip(q, n.mkt)}</td>
      <td class="mk-c-chg ${chg==null?'td-dim':chg>=0?'td-up':'td-down'}">${fmtPct(chg)}</td>
      <td>${p?fmtN(p.sh,0):'<span class="td-dim">—</span>'}</td>
      <td>${p?'$'+fmtN(p.bp):'<span class="td-dim">—</span>'}</td>
      <td class="mk-c-val">${val!=null?'$'+fmtN(val):'<span class="td-dim">—</span>'}</td>
      <td class="mk-c-pnl ${pnlP==null?'td-dim':pnlP>=0?'td-up':'td-down'}">${fmtPct(pnlP)}</td>
      <td>${nrs}</td>
      <td><button class="pos-btn" onclick="posEdit('${n.id}')">${p?t('mk_edit'):t('mk_add')}</button></td>
    </tr>`;
  }).join('')+'</tbody>';
  if(typeof V8!=='undefined' && V8.market) V8.market.afterRender();
  if(typeof renderNrsTop10==='function') renderNrsTop10();
  if(typeof initGdelt==='function') initGdelt();
}
window.posEdit=id=>{ MKT.editing=id; renderMarket(true); };
window.posCancel=()=>{ MKT.editing=null; renderMarket(true); };
window.posSave=id=>{
  const sh=parseFloat(document.getElementById('pe-sh').value), bp=parseFloat(document.getElementById('pe-bp').value);
  if(sh>0&&bp>0){ MKT.pos[id]={sh,bp}; savePos(); }
  MKT.editing=null; renderMarket(true);
};
window.posDel=id=>{ delete MKT.pos[id]; savePos(); MKT.editing=null; renderMarket(true); };
window.goMap=id=>{ switchTab('map'); setTimeout(()=>jumpTo(id),80); };

/* ===================== Init v7 ===================== */
_ldrSet(82, 'Renderizando interfaz…');
try { renderBand(); } catch(e) { console.error('[khipu] renderBand:', e); }
_ldrSet(90, 'Aplicando idioma y temas…');
try { applyLang(); } catch(e) { console.error('[khipu] applyLang:', e); }
// Cancel fallback timer and dismiss now
if (typeof window._khipuLoaderFallback !== 'undefined') clearTimeout(window._khipuLoaderFallback);
if (typeof window._khipuLoaderDismiss === 'function') {
  if (_loaderBar) _loaderBar.style.width = '100%';
  if (_loaderText) _loaderText.textContent = `${NODES.length} nodos · ${LINKS.length} conexiones · listo`;
  setTimeout(window._khipuLoaderDismiss, 200);
}

/* ═══════════════════════════════════════════════════════════════════════════
   v8 · CAPA DE PRODUCTO — datos en vivo, IA, fundamentales, portfolio, alertas
   Se apoya en todo lo de v7 (NODES, NODE_BY_ID, LINKS, t, esc, MKT, renderDetail…)
   sin modificar su lógica protegida (grafo, stress-test, pathfinder, filtros, i18n).
   ═══════════════════════════════════════════════════════════════════════════ */
var V8 = {};   /* var (hoisted) para que el guard de renderMarket sea seguro en init */
(function(){
'use strict';

/* ---------- §A · i18n v8 (se mezcla en el I18N existente) ---------- */
Object.assign(I18N.es, {
  offline:'Sin conexión',
  mk_export:'Exportar',
  set_title:'⚙ Configuración',
  set_sub:'Tus API keys se guardan solo en este navegador (localStorage), nunca en el archivo ni en ningún servidor.',
  set_sub_server:'Modo servidor: las API keys viven en el .env del servidor. Aquí solo ajustas preferencias.',
  set_keys:'🔑 API Keys', set_prefs:'⚙ Preferencias', set_data:'🗑 Datos',
  pref_live:'Precios en tiempo real (WebSocket)',
  pref_notif:'Notificaciones del sistema para alertas',
  pref_aicache:'Guardar análisis de IA en caché (24h)',
  d_news:'Noticias', d_earn:'Próximo earnings', d_fund:'Fundamentales', d_ai:'Análisis IA',
  d_alerts:'Alertas de precio', d_pos:'Mi posición',
  d_history:'Historia · de dónde sale cada dato', hist_empty:'Sin historia registrada todavía.',
  d_research:'🔬 Investigación IA · agentes con evidencia',
  feed_h:'Lo último en el grafo', feed_ago:'hace', feed_now:'ahora', feed_quiet:'Sin novedades en las últimas 2 semanas.',
  hist_facts:'hechos', hist_src:'con fuente', hist_saved:'noticias nuevas guardadas',
  hist_primary:'fuente primaria', hist_press:'prensa', hist_weak:'fuente débil',
  v8_needkey:'Configura tu API key en ⚙ para activar esta sección.',
  v8_nolist:'Sin listado en EE.UU. — datos de mercado no disponibles.',
  ai_btn:'✨ Analizar con IA', ai_loading:'Analizando con IA…',
  ai_digest_btn:'📰 Resumir noticias', ai_digest_loading:'Resumiendo…',
  news_24:'24h', news_7:'7 días', news_30:'30 días',
  earn_next:'Próximo earnings', earn_in:'en {d} días', earn_eps:'EPS est',
  earn_beat:'✓ Beat', earn_miss:'✗ Miss',
  fund_pe:'P/E', fund_ev:'EV/EBITDA', fund_pt:'Precio objetivo', fund_ins:'Consenso de analistas',
  fund_sector:'sector', fund_analysts:'{n} analistas', fund_insiders90:'últimos 90d',
  ins_buy:'COMPRA', ins_sell:'VENTA', ins_title:'Insiders (últimos 90 días)',
  al_add:'+ Nueva alerta', al_above:'sobre', al_below:'bajo', al_active:'Activa', al_fired:'Disparada',
  al_banner:'🔔 ALERTA: {t} {dir} ${p} → precio actual ${cur}',
  al_go:'Ver empresa', al_dismiss:'Descartar',
  pos_shares:'Acciones', pos_value:'Valor', pos_pnl:'P&L',
  stress_ai:'✨ Analizar impacto con IA', stress_ai_loading:'Evaluando impacto…',
  dh_finnhub:'Finnhub', dh_yahoo:'Yahoo', dh_fmp:'FMP', dh_ai:'IA', dh_mkt:'Marketstack (EOD)', dh_offline:'Offline',
  dh_live:'LIVE', dh_cache:'caché', dh_ready:'listo', dh_off:'sin clave', dh_no:'no', dh_yes:'sí',
  dh_key:'clave presente', dh_batch:'en lotes', dh_quota:'cuota agotada',
  test:'Probar', test_ok:'✓ válida', test_err:'✗ error', test_ing:'probando…', test_empty:'sin clave',
  clear_quotes:'Borrar caché de precios', clear_ai:'Borrar análisis IA', clear_cache:'Vaciar caché de datos',
  ai_verdict:'Salud del negocio', ai_conf:'confianza', ai_bull:'CASO ALCISTA', ai_bear:'RIESGO PRINCIPAL',
  ai_metric:'Métrica clave', ai_horizon:'Horizonte', ai_cats:'Catalizadores', ai_similar:'Similar a',
  ai_disclaim:'Generado por IA a partir de datos públicos. Evalúa la salud del negocio: no es una recomendación de compra, venta ni mantener, ni asesoría financiera.',
});
Object.assign(I18N.en, {
  offline:'Offline',
  mk_export:'Export',
  set_title:'⚙ Settings',
  set_sub:'Your API keys are stored only in this browser (localStorage) — never in the file or on any server.',
  set_sub_server:'Server mode: API keys live in the server .env. Here you only adjust preferences.',
  set_keys:'🔑 API Keys', set_prefs:'⚙ Preferences', set_data:'🗑 Data',
  pref_live:'Real-time prices (WebSocket)',
  pref_notif:'System notifications for alerts',
  pref_aicache:'Cache AI analysis (24h)',
  d_news:'News', d_earn:'Next earnings', d_fund:'Fundamentals', d_ai:'AI analysis',
  d_alerts:'Price alerts', d_pos:'My position',
  d_history:'History · where each fact comes from', hist_empty:'No recorded history yet.',
  d_research:'🔬 AI research · agents with evidence',
  feed_h:'Latest in the graph', feed_ago:'ago', feed_now:'now', feed_quiet:'Nothing new in the last 2 weeks.',
  hist_facts:'facts', hist_src:'with source', hist_saved:'new news items saved',
  hist_primary:'primary source', hist_press:'press', hist_weak:'weak source',
  v8_needkey:'Add your API key in ⚙ to enable this section.',
  v8_nolist:'No US listing — market data unavailable.',
  ai_btn:'✨ Analyze with AI', ai_loading:'Analyzing with AI…',
  ai_digest_btn:'📰 Summarize news', ai_digest_loading:'Summarizing…',
  news_24:'24h', news_7:'7 days', news_30:'30 days',
  earn_next:'Next earnings', earn_in:'in {d} days', earn_eps:'EPS est',
  earn_beat:'✓ Beat', earn_miss:'✗ Miss',
  fund_pe:'P/E', fund_ev:'EV/EBITDA', fund_pt:'Price target', fund_ins:'Analyst consensus',
  fund_sector:'sector', fund_analysts:'{n} analysts', fund_insiders90:'last 90d',
  ins_buy:'BUY', ins_sell:'SELL', ins_title:'Insiders (last 90 days)',
  al_add:'+ New alert', al_above:'above', al_below:'below', al_active:'Active', al_fired:'Fired',
  al_banner:'🔔 ALERT: {t} {dir} ${p} → current price ${cur}',
  al_go:'View company', al_dismiss:'Dismiss',
  pos_shares:'Shares', pos_value:'Value', pos_pnl:'P&L',
  stress_ai:'✨ Analyze impact with AI', stress_ai_loading:'Assessing impact…',
  dh_finnhub:'Finnhub', dh_yahoo:'Yahoo', dh_fmp:'FMP', dh_ai:'AI', dh_mkt:'Marketstack (EOD)', dh_offline:'Offline',
  dh_live:'LIVE', dh_cache:'cache', dh_ready:'ready', dh_off:'no key', dh_no:'no', dh_yes:'yes',
  dh_key:'key present', dh_batch:'batched', dh_quota:'quota exhausted',
  test:'Test', test_ok:'✓ valid', test_err:'✗ error', test_ing:'testing…', test_empty:'no key',
  clear_quotes:'Clear price cache', clear_ai:'Clear AI analysis', clear_cache:'Clear data cache',
  ai_verdict:'Business health', ai_conf:'confidence', ai_bull:'BULL CASE', ai_bear:'KEY RISK',
  ai_metric:'Key metric', ai_horizon:'Horizon', ai_cats:'Catalysts', ai_similar:'Similar to',
  ai_disclaim:'AI-generated from public data. It assesses business health: not a buy, sell or hold recommendation, nor financial advice.',
});

/* ---------- §B · Modo de operación + claves ---------- */
// SERVER_MODE y BASE ya declarados al inicio del script (var global)
const health = { server:SERVER_MODE, finnhub:false, fmp:false, claude:false, marketstack:false };

// Las API keys viven SOLO en el servidor (.env/Railway). El navegador únicamente
// conoce el estado de salud que reporta /api/health.
const Keys = {
  has(svc){ return !!health[svc]; }
};

/* ---------- §C · Caché IndexedDB (TTL) ---------- */
const idb = {
  _db:null,
  open(){ return new Promise((res,rej)=>{
    if(this._db) return res(this._db);
    let r; try{ r=indexedDB.open('eco_v8_cache',1); }catch(e){ return rej(e); }
    r.onupgradeneeded=()=>{ if(!r.result.objectStoreNames.contains('cache')) r.result.createObjectStore('cache',{keyPath:'k'}); };
    r.onsuccess=()=>{ this._db=r.result; res(this._db); };
    r.onerror=()=>rej(r.error);
  }); },
  async get(k){ try{ const db=await this.open(); return await new Promise(res=>{
    const tx=db.transaction('cache').objectStore('cache').get(k);
    tx.onsuccess=()=>{ const v=tx.result; if(!v||Date.now()>v.exp) return res(null); res(v.data); };
    tx.onerror=()=>res(null);
  }); }catch(e){ return null; } },
  async set(k,data,ttl){ try{ const db=await this.open(); db.transaction('cache','readwrite').objectStore('cache').put({k,data,exp:Date.now()+ttl}); }catch(e){} },
  async clear(){ try{ const db=await this.open(); db.transaction('cache','readwrite').objectStore('cache').clear(); }catch(e){} }
};

/* ---------- §D · DataLayer (proxy servidor ⇄ API directa + caché) ---------- */
const today = () => new Date().toISOString().slice(0,10);
const daysAgo = n => new Date(Date.now()-n*864e5).toISOString().slice(0,10);

const DataLayer = {
  serverMode: true,   // compat: siempre servida por server.py (solo-Railway)
  // Límite de 6 s: initV8 la espera antes de registrar el service worker y
  // de pasar la UI a inglés — un server colgado no puede congelar el arranque.
  async health(){
    const ac = (typeof AbortController!=='undefined') ? new AbortController() : null;
    const t = ac ? setTimeout(()=>ac.abort(), 6000) : null;
    try{ const r=await fetch(BASE+'/api/health',{cache:'no-store', signal: ac ? ac.signal : undefined}); const j=await khJSON(r);
      if(j && !j.offline) Object.assign(health,j); }catch(e){}
    finally{ if(t) clearTimeout(t); }
    return health;
  },
  // JSON o error claro: HTTP ≠ 2xx → Error('HTTP n — mensaje del server') con
  // .status/.offline; 200 que no es JSON (HTML de un proxy caído, shell viejo)
  // → error bilingüe offline (khJSON) en vez de "Unexpected token '<'".
  async _json(url, opts){
    const r=await fetch(url,opts);
    if(!r.ok){
      let j=null; try{ j=await r.clone().json(); }catch(e){}
      const m = j ? ((window.LANG==='en') ? (j.error_en||j.error) : (j.error||j.error_en)) : '';
      const err=new Error('HTTP '+r.status+(m?' — '+m:''));
      err.status=r.status; if(j && j.offline) err.offline=true;
      throw err;
    }
    return khJSON(r);
  },

  async quote(ticker){ // {c, pc}
    return this._json(BASE+'/api/quote/'+encodeURIComponent(ticker));
  },
  async news(ticker){
    return DataLayer._cached('news_'+ticker, 1800000, ()=>
      this._json(BASE+'/api/news/'+encodeURIComponent(ticker)));
  },
  async earnings(ticker){
    return DataLayer._cached('earn_'+ticker, 3600000, ()=>
      this._json(BASE+'/api/earnings/'+encodeURIComponent(ticker)));
  },
  async fundamentals(ticker){
    return DataLayer._cached('fund3_'+ticker, 86400000, ()=>
      this._json(BASE+'/api/fundamentals/'+encodeURIComponent(ticker)));
  },
  async insiders(ticker){
    return DataLayer._cached('ins_'+ticker, 86400000, ()=>
      this._json(BASE+'/api/insiders/'+encodeURIComponent(ticker)));
  },
  async aiComplete(system, prompt, maxTokens, tier){ // → texto; tier 'deep' = Sonnet
    maxTokens = maxTokens||900;
    const body={system,prompt,max_tokens:maxTokens};
    if(tier) body.tier=tier;
    const j=await this._json(BASE+'/api/ai/analyze',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(body)});
    if(j.error) throw new Error(j.error);
    return j.result;
  },
  async wsToken(){
    // Two-step exchange: get a short-lived session token, then exchange for the real key
    const sess=await this._json(BASE+'/api/ws-token');
    if(!sess.session_token) return null;
    const j=await fetch(BASE+'/api/ws-key',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_token:sess.session_token})}).then(r=>r.json());
    return j.token||null;
  },
  async _cached(key, ttl, fetcher){
    const c=await idb.get(key); if(c!=null) return c;
    const d=await fetcher(); if(d!=null) idb.set(key,d,ttl); return d;
  }
};
V8.DataLayer = DataLayer;
window.DataLayer = DataLayer;   // el X-Ray (engine/xray.js) lo busca en window para el precio en vivo

/* ---------- helpers ---------- */
const $ = id => document.getElementById(id);
const usTickers = () => [...new Set(NODES.filter(n=>n.mkt).map(n=>n.mkt))];
const nodeByTicker = {}; NODES.forEach(n=>{ if(n.mkt) nodeByTicker[n.mkt]=n; });
function relTime(sec){ const d=Date.now()/1000-sec; if(d<3600) return Math.max(1,Math.round(d/60))+'m';
  if(d<86400) return Math.round(d/3600)+'h'; return Math.round(d/86400)+'d'; }
function tr(k,vars){ let s=t(k); if(vars) for(const v in vars) s=s.replace('{'+v+'}',vars[v]); return s; }

/* ════════════════ §E · PANEL DE CONFIGURACIÓN (Feature 11) ════════════════ */
// Las API keys se configuran SOLO en Railway (.env del server) — aquí quedan
// las preferencias del usuario y el estado de salud de los servicios.
const Settings = {
  open(){ $('settings-overlay').classList.add('show'); $('settings-panel').classList.add('show'); this.render(); },
  close(){ $('settings-overlay').classList.remove('show'); $('settings-panel').classList.remove('show'); },
  render(){
    $('set-title').textContent=t('set_title');
    $('set-sub').textContent=t('set_sub_server');
    $('set-keys-h').textContent=t('set_keys'); $('set-prefs-h').textContent=t('set_prefs'); $('set-data-h').textContent=t('set_data');
    $('pref-live-l').textContent=t('pref_live'); $('pref-notif-l').textContent=t('pref_notif'); $('pref-aicache-l').textContent=t('pref_aicache');
    $('data-clear-quotes').textContent=t('clear_quotes'); $('data-clear-ai').textContent=t('clear_ai'); $('data-clear-cache').textContent=t('clear_cache');
    $('settings-keys').innerHTML='<div class="v8-need-key">'+(LANG==='en'
      ?'Keys are configured on the server (Railway → Variables). Health below.'
      :'Las claves se configuran en el servidor (Railway → Variables). Estado abajo.')+'</div>';
    const P=prefs();
    $('pref-live').checked=P.live; $('pref-notif').checked=P.notif; $('pref-aicache').checked=P.aicache;
  }
};
V8.openSettings = ()=>Settings.open();

function prefs(){
  return Object.assign({live:true, notif:false, aicache:true}, JSON.parse(localStorage.getItem('eco_prefs')||'{}'));
}
function savePrefs(p){ localStorage.setItem('eco_prefs', JSON.stringify(p)); }

/* listeners settings */
$('settings-btn').onclick=()=>Settings.open();
$('settings-close').onclick=()=>Settings.close();
$('settings-overlay').onclick=()=>Settings.close();

/* ── Estado del Sistema — diagnóstico en vivo ──────────────────────────── */
// KHIPUS OS (2026-10-10): cada servicio es una tarjeta OS = punto de estado + título + detalle + «Qué hacer»,
// con texto AA por nivel (ok = --os-good-ink · aviso = --os-warn-ink · falla = --os-bad-ink; CSS .ksys-*).
// Bilingüe: si el servidor manda detail_en / fixes[{es,en}] / fix_en (la voz ya lo hace) se usan en inglés;
// si no, se muestra el texto del servidor tal cual. Las pistas « → …» que el servidor pega al final del
// detalle (_ai_error_hint / _db_error_hint) pasan al bloque «Qué hacer».
const _sysEN = () => (window.LANG||'')==='en';
const _sysL = (es, en) => _sysEN() ? en : es;
const DIAG_META = {
  // IA: el PAPEL de cada proveedor (1.º / respaldo, en el nivel rápido y en el profundo) se calcula con la
  // ruta REAL del servidor (d.routing, core/ai.ai_route_state) en _diagAiRole — limpieza 2026-10-11: antes
  // decía fijo "Claude = IA principal" aunque el chat rápido empiece por Gemini
  claude:     { icon:'✦',  name:'Claude (Anthropic)',  why:'IA de Anthropic', why_en:'Anthropic AI', ai:true },
  gemini:     { icon:'◆',  name:'Google Gemini',        why:'IA de Google', why_en:'Google AI', ai:true },
  nvidia:     { icon:'▲',  name:'NVIDIA NIM',           why:'IA del catálogo de NVIDIA (créditos de desarrollador)', why_en:'NVIDIA catalog AI (developer credits)', ai:true },
  elevenlabs: { icon:'🎙', name:'Khipu / ElevenLabs',  why:'Voz conversacional — preguntar por voz', why_en:'Conversational voice — ask by voice' },
  finnhub:    { icon:'📈', name:'Finnhub',             why:'Precios en vivo (EE.UU.) · WebSocket · primero en la cascada', why_en:'Live prices (US) · WebSocket · first in the cascade' },
  yahoo:      { icon:'🌐', name:'Yahoo Finance',       why:'Precios de TODAS las bolsas (sin clave) · respaldo de EE.UU. · capitalización', why_en:'Prices for ALL exchanges (no key) · US backup · market cap' },
  fmp:        { icon:'📑', name:'FMP',                 why:'Estados financieros · perfil · precio objetivo (plan con cobertura limitada)', why_en:'Financial statements · profile · price target (limited-coverage plan)' },
  grafo:      { icon:'◈',  name:'Grafo Temporal', name_en:'Temporal Graph', why:'Memoria temporal (nativa · en Postgres)', why_en:'Temporal memory (native · in Postgres)' },
  ontologia:  { icon:'🗄️', name:'Ontología (Postgres)', name_en:'Ontology (Postgres)', why:'Fuente única de verdad · eventos bitemporales', why_en:'Single source of truth · bitemporal events' },
  gobernanza: { icon:'⚖', name:'Gobernanza', name_en:'Governance', why:'Reglas y motor versionados · se activan con tu PIN', why_en:'Versioned rules and engine · activated with your PIN',
    explain:[['gov_gates_7d','Puertas','Gates'],['gov_guard','Guardia','Guard'],['gov_retention','Retención','Retention']] },
  market_extra:{icon:'🗂', name:'Fuentes de respaldo', name_en:'Backup sources', why:'FMP · MarketStack · AlphaVantage', why_en:'FMP · MarketStack · AlphaVantage' },
  genui:      { icon:'✦', name:'Respuestas visuales', name_en:'Visual answers', why:'Gráficos y cifras dentro del chat · cada cifra con su fuente (sin IA, sin red)', why_en:'Charts and figures inside the chat · every figure with its source (no AI, no network)' },
  investigacion:{icon:'🔬', name:'Investigación IA', name_en:'AI research', why:'Proveedores en pausa · cola · presupuesto diario · reloj del servidor (R6)', why_en:'Paused providers · queue · daily budget · server clock (R6)' },
};
const DIAG_LEVEL_TXT = {
  ok:   {es:'OPERATIVO',      en:'OPERATIONAL'},
  warn: {es:'CON AVISOS',     en:'WARNINGS'},
  bad:  {es:'FALLA',          en:'FAILING'},
  off:  {es:'NO CONFIGURADO', en:'NOT SET UP'},
};
// nivel: ok · warn (responde, pero con avisos: chequeos «warn» de la voz, cuota de Finnhub, IA en pausa) · bad · off
function _diagLevel(s){
  s = s || {};
  if(s.ok){
    const warn = (Array.isArray(s.checks) && s.checks.some(c=>c && c.level==='warn'))
      || !!s.quota || !!(s.circuit && s.circuit.open);
    return warn ? 'warn' : 'ok';
  }
  return s.configured ? 'bad' : 'off';
}
// textos de la tarjeta en el idioma de la app → {detail, fixes[]}
function _diagTexts(s, level){
  s = s || {};
  const en = _sysEN();
  let detail = String((en && s.detail_en) ? s.detail_en : (s.detail || s.detail_en || ''));
  let fixes = [];
  if(Array.isArray(s.fixes)) fixes = s.fixes.map(f=>{
    if(!f) return '';
    if(typeof f === 'string') return f;
    return String((en ? (f.en || f.es) : (f.es || f.en)) || '');
  }).filter(Boolean);
  if(!fixes.length){
    const flat = en ? (s.fix_en || s.fix_es || s.fix) : (s.fix_es || s.fix || s.fix_en);
    if(flat) fixes = [String(flat)];
  }
  if(fixes.length){
    // el detalle de la voz ya trae «— QUÉ HACER: 1) …» / «— WHAT TO DO: 1) …»: se quita para no repetirlo
    detail = detail.replace(/\s*—\s*(QUÉ HACER|WHAT TO DO)\s*:[\s\S]*$/i, '').trim();
  } else if(level !== 'ok'){
    const i = _diagHintAt(detail);
    if(i > 0 && detail.slice(i + 3).trim()){ fixes = [detail.slice(i + 3).trim()]; detail = detail.slice(0, i).trim(); }
  }
  return {detail, fixes};
}
// dónde empieza la pista « → …» que el servidor PEGA al final del detalle (_ai_error_hint/_db_error_hint): la
// primera flecha FUERA de paréntesis/corchetes. Una ruta de menú como «(Deployments → Restart)» o «(+ New → Database)»
// no es la pista; un detalle con viñetas «•» (la voz) ya trae sus arreglos aparte → -1 (no se parte).
function _diagHintAt(detail){
  const s = String(detail || '');
  if(s.indexOf('•') >= 0) return -1;
  let depth = 0;
  for(let i = 0; i < s.length; i++){
    const c = s[i];
    if(c === '(' || c === '[') depth++;
    else if((c === ')' || c === ']') && depth > 0) depth--;
    else if(depth === 0 && c === ' ' && s.startsWith(' → ', i)) return i;
  }
  return -1;
}
// «Khipu (voz) tiene problemas: • A • B» → encabezado + lista
function _diagDetailHTML(detail){
  const parts = String(detail||'').split(/\s*•\s+/).map(x=>x.trim());
  const head = parts.shift() || '';
  const items = parts.filter(Boolean);
  return esc(head) + (items.length ? '<ul>' + items.map(x=>'<li>' + esc(x) + '</li>').join('') + '</ul>' : '');
}
// papel REAL de un proveedor de IA según la ruta del servidor: "Rápido: 1.º · Profundo: respaldo 2"
function _diagAiRole(key, routing){
  if(!routing) return '';
  const en = _sysEN();
  const pos = (lst) => { const i = (lst || []).indexOf(key); return i < 0 ? null : i; };
  const txt = (i) => i === 0 ? (en ? '1st' : '1.º') : (en ? 'backup ' + i : 'respaldo ' + i);
  const f = pos(routing.fast), d = pos(routing.deep), out = [];
  if(f != null) out.push((en ? 'Fast (chat): ' : 'Rápido (chat): ') + txt(f));
  if(d != null) out.push((en ? 'Deep (research): ' : 'Profundo (investigación): ') + txt(d));
  const md = (routing.models || {})[key] || (key === 'claude' ? [(routing.models || {}).fast, (routing.models || {}).deep].filter(Boolean).join(' / ') : '');
  return out.join(' · ') + (md ? ' · ' + md : '');
}
function _diagCard(key, s, routing){
  s = s || {};
  const m = DIAG_META[key] || {icon:'•', name:key, why:''};
  const en = _sysEN();
  const lv = _diagLevel(s);
  const tx = _diagTexts(s, lv);
  const name = (en && m.name_en) || m.name;
  const role = m.ai ? _diagAiRole(key, routing) : '';
  const why = ((en && m.why_en) || m.why || '') + (role ? ' — ' + role : '');
  const lat = (s.latency_ms!=null) ? `<span class="ksys-lat">${esc(s.latency_ms)} ms</span>` : '';
  const fix = tx.fixes.length ? `<div class="ksys-fix"><span class="ksys-fix-h">${esc(_sysL('Qué hacer', 'What to do'))}</span>${
    tx.fixes.length > 1 ? '<ol>' + tx.fixes.map(f=>'<li>' + esc(f) + '</li>').join('') + '</ol>' : esc(tx.fixes[0])}</div>` : '';
  return `<div class="ksys-card ksys-lv-${lv}" data-diag="${esc(key)}" data-level="${lv}">
    <div class="ksys-ch">
      <span class="ksys-ic" aria-hidden="true">${esc(m.icon)}<span class="ksys-dot"></span></span>
      <b class="ksys-name">${esc(name)}</b>
      <span class="ksys-st">${esc(DIAG_LEVEL_TXT[lv][en ? 'en' : 'es'])}</span>
      ${lat}
    </div>
    ${why ? `<div class="ksys-why">${esc(why)}</div>` : ''}
    ${(m.explain && window.explainChip) ? `<div class="ksys-why">${m.explain.map(x=>esc(en ? x[2] : x[1]) + window.explainChip(x[0])).join(' · ')}</div>` : ''}
    ${tx.detail ? `<div class="ksys-detail">${_diagDetailHTML(tx.detail)}</div>` : ''}
    ${fix}
  </div>`;
}
function _sysEmpty(es, en){ return `<div class="ksys-empty">${esc(_sysL(es, en))}</div>`; }
function _sysErrCard(title, msg, hint){
  return `<div class="ksys-card ksys-lv-bad" role="alert">
    <div class="ksys-ch"><span class="ksys-ic" aria-hidden="true">⚠<span class="ksys-dot"></span></span><b class="ksys-name ksys-bad-ink">${esc(title)}</b></div>
    ${msg ? `<div class="ksys-detail">${esc(msg)}</div>` : ''}
    ${hint ? `<div class="ksys-fix"><span class="ksys-fix-h">${esc(_sysL('Qué hacer', 'What to do'))}</span>${esc(hint)}</div>` : ''}
  </div>`;
}
window.openDiagnostics = async function(fresh){
  const body = $('diag-body'), sum = $('diag-summary');
  if(fresh) body.innerHTML = _sysEmpty('Re-probando servicios en vivo…', 'Re-testing services live…');
  sum.textContent = '';
  try{
    const base = (typeof BASE!=='undefined') ? BASE : '';
    const r = await fetch(`${base}/api/diagnostics${fresh?'?fresh=1':''}`);
    if(!r.ok) throw new Error('HTTP '+r.status);
    const d = await r.json();
    const order = ['claude','gemini','nvidia','investigacion','elevenlabs','finnhub','yahoo','fmp','grafo','ontologia','gobernanza','genui','market_extra'];
    body.innerHTML = order.filter(k=>d.services&&d.services[k]).map(k=>_diagCard(k, d.services[k], d.routing)).join('');
    const ok = d.summary?.ok ?? 0, tot = d.summary?.total ?? 0;
    const lv = ok===tot ? 'ok' : (ok===0 ? 'bad' : 'warn');
    sum.innerHTML = `<b class="ksys-sumb ksys-lv-${lv}">${esc(ok)}/${esc(tot)} ${esc(_sysL('operativos', 'operational'))}</b> · ${esc(_sysL('ruta de la IA', 'AI route'))}: <code>${esc((d.routing && (_sysEN() ? d.routing.hint_en : d.routing.hint_es)) || '?')}</code>${d.cached ? ' · ' + esc(_sysL('caché', 'cached')) : ''}`;
    if(window.KhipuReconcile && d.services && d.services.ontologia && d.services.ontologia.configured) window.KhipuReconcile.mount('recon-box');
    if(window.KhipuGovernance) window.KhipuGovernance.mount('gov-box');
    if(window.KhipuPriceHistory) window.KhipuPriceHistory.mount('prices-box');
  }catch(e){
    body.innerHTML = _sysErrCard(_sysL('No se pudo obtener el diagnóstico', 'Could not load the diagnostics'), String(e.message||e),
      _sysL('El diagnóstico en vivo necesita el servidor de Khipus (backend Flask). Si acabas de desplegar, espera un minuto y pulsa ↻ Re-probar.',
            'The live diagnostics need the Khipus server (Flask backend). If you just deployed, wait a minute and press ↻ Re-test.'));
  }
};

/* ── Registro de Acciones (Fase 2 — ontología) ──────────────────────────── */
function _registroActionMeta(a){
  const M = {
    CrearTesis:{icon:'📋',label:'Tesis',en:'Thesis'}, MarcarRiesgo:{icon:'⚠',label:'Riesgo marcado',en:'Risk flagged'},
    RegistrarDecision:{icon:'🗳',label:'Decisión',en:'Decision'}, AnotarObjeto:{icon:'✎',label:'Anotación',en:'Note'},
    ProponerVinculo:{icon:'🔗',label:'Vínculo propuesto',en:'Link proposed'}, ConfirmarVinculo:{icon:'✓',label:'Vínculo confirmado',en:'Link confirmed'},
    RechazarVinculo:{icon:'✗',label:'Vínculo rechazado',en:'Link rejected'}, AjustarPosicion:{icon:'📊',label:'Posición ajustada',en:'Position adjusted'},
    CorregirDato:{icon:'✒',label:'Dato corregido',en:'Data corrected'},
  };
  const m = M[a];
  if(!m) return {icon:'•', label:a||_sysL('Acción', 'Action')};
  return {icon:m.icon, label:_sysEN() ? m.en : m.label};
}
function _registroCard(a){
  const m = _registroActionMeta(a.action);
  const p = a.payload||{};
  const detail = p.rationale || p.razon || p.decision || p.texto || (p.campo ? `${p.campo}: ${p.valor_anterior} → ${p.valor_nuevo}` : '') || '';
  const objId = a.object_id || a.target_id || '';
  const objLabel = (window.NODE_BY_ID && window.NODE_BY_ID[objId] && window.NODE_BY_ID[objId].label) || objId;
  const when = a.recorded_at ? new Date(a.recorded_at).toLocaleString(_sysEN()?'en':'es',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}) : '';
  return `<div class="ksys-card">
    <div class="ksys-ch">
      <span class="ksys-ic acc" aria-hidden="true">${esc(m.icon)}</span>
      <b class="ksys-name">${esc(m.label)}${objLabel?' · '+esc(objLabel):''}</b>
      <span class="ksys-when">${esc(when)}</span>
    </div>
    <div class="ksys-why">${esc(_sysL('por', 'by'))} <b>${esc(a.actor||'')}</b></div>
    ${detail?`<div class="ksys-detail">${esc(String(detail).slice(0,240))}</div>`:''}
  </div>`;
}
window.openRegistro = async function(fresh){
  const body = $('registro-body');
  if(fresh) body.innerHTML = _sysEmpty('Actualizando…', 'Refreshing…');
  try{
    const base = (typeof BASE!=='undefined') ? BASE : '';
    const actor = ($('registro-filter-actor').value||'').trim();
    const qs = actor ? `?actor=${encodeURIComponent(actor)}&limit=100` : '?limit=100';
    const r = await fetch(`${base}/api/ontology/actions${qs}`);
    if(!r.ok){
      if(r.status===503){ body.innerHTML = _sysEmpty('La ontología no está configurada en este servidor (falta Postgres). El Registro se activa solo cuando existe.',
        'The ontology is not set up on this server (Postgres is missing). The Log turns on only when it exists.'); return; }
      throw new Error('HTTP '+r.status);
    }
    const d = await r.json();
    if(!d.actions || !d.actions.length){
      body.innerHTML = _sysEmpty('Sin acciones registradas todavía. Abre una empresa en ◈ Grafo Temporal → ＋ Acción para crear la primera tesis o anotación.',
        'No actions recorded yet. Open a company in ◈ Temporal Graph → ＋ Action to create the first thesis or note.');
      return;
    }
    body.innerHTML = d.actions.map(_registroCard).join('');
  }catch(e){
    body.innerHTML = _sysErrCard(_sysL('No se pudo cargar el registro', 'Could not load the log'), String(e.message||e), '');
  }
};
(function(){ const f=$('registro-filter-actor'); if(f) f.addEventListener('keydown', e=>{ if(e.key==='Enter') window.openRegistro(true); }); })();

/* ── Propuestas de Agentes (Fase 3 — ontología) ─────────────────────────── */
const AGENT_META = {
  centinela_nrs:{icon:'🛰',label:'Centinela NRS',en:'NRS Sentinel'}, lector_gdelt:{icon:'📰',label:'Lector GDELT',en:'GDELT Reader'},
  guardian_cartera:{icon:'💼',label:'Guardián de Cartera',en:'Portfolio Guardian'}, cartografo:{icon:'🗺',label:'Cartógrafo',en:'Cartographer'},
  radar_empresas:{icon:'📡',label:'Radar de Empresas',en:'Company Radar'}, tejedor_hiperaristas:{icon:'🕸',label:'Tejedor de Hiperaristas',en:'Hyperedge Weaver'},
  investigador_autonomo:{icon:'🌐',label:'Investigador Autónomo',en:'Autonomous Researcher'},
};
const PROPOSAL_FIELD_LABELS = {
  nivel:'Nivel NRS', razon:'Razón', stance:'Postura', confidence:'Confianza', rationale:'Razonamiento',
  decision:'Decisión', texto:'Nota', ticker:'Ticker', delta:'Delta (unidades)', tipo:'Tipo de vínculo',
};
const PROPOSAL_FIELD_LABELS_EN = {
  nivel:'NRS level', razon:'Reason', stance:'Stance', confidence:'Confidence', rationale:'Rationale',
  decision:'Decision', texto:'Note', ticker:'Ticker', delta:'Delta (units)', tipo:'Link type',
};
// quién firma una acción de la ontología: EL helper único (engine/toast.js khipuActor; pide el nombre una vez,
// bilingüe). Devuelve una promesa.
function _getActorGlobal(){
  return window.khipuActor ? window.khipuActor({ask:true}) : Promise.resolve('usuario');
}
function _propuestaCard(p){
  const en = _sysEN();
  const m0 = AGENT_META[p.agent];
  const m = m0 ? {icon:m0.icon, label:(en && m0.en) || m0.label} : {icon:'🤖', label:p.agent||''};
  const objLabel = (window.NODE_BY_ID && window.NODE_BY_ID[p.object_id] && window.NODE_BY_ID[p.object_id].label) || p.object_id || '';
  const conf = p.confidence!=null ? Math.round(p.confidence*100)+'%' : '—';
  // Track C: 'fuentes' y 'datos_no_verificados' del Investigador se muestran
  // bonitos (links + lista), no como JSON editable; 'autor_tipo' se omite.
  const fields = Object.keys(p.payload||{}).filter(k=>(!['company_id','object_id','ticker','fuentes','datos_no_verificados','autor_tipo'].includes(k)) || k==='ticker');
  const fuentes = Array.isArray(p.payload&&p.payload.fuentes) ? p.payload.fuentes : [];
  const fuentesHtml = fuentes.length ? `<div class="ksys-src">
      <span class="ksys-flab">📎 ${esc(_sysL('Fuentes citadas', 'Cited sources'))} (${fuentes.length})</span>
      ${fuentes.slice(0,8).map(f=>`<a href="${safeUrl(f.url)}" target="_blank" rel="noopener noreferrer">↗ ${esc(f.titulo||f.publicador||f.url||'')}</a>`).join('')}
    </div>` : '';
  const noVerif = Array.isArray(p.payload&&p.payload.datos_no_verificados) ? p.payload.datos_no_verificados : [];
  const noVerifHtml = noVerif.length ? `<div class="ksys-why ksys-warn-ink ksys-unv">⚠ ${esc(_sysL('Sin verificar', 'Unverified'))}: ${esc(noVerif.slice(0,4).join(' · '))}</div>` : '';
  const fieldsHtml = fields.map(k=>{
    const v = p.payload[k];
    const label = (en ? PROPOSAL_FIELD_LABELS_EN[k] : PROPOSAL_FIELD_LABELS[k]) || k;
    const isLong = typeof v === 'string' && v.length > 40;
    return `<label class="ksys-fl"><span class="ksys-flab">${esc(label)}</span>${isLong
        ? `<textarea data-k="${esc(k)}" class="prop-field ksys-field" rows="2">${esc(String(v))}</textarea>`
        : `<input data-k="${esc(k)}" class="prop-field ksys-field" value="${esc(String(v))}">`}</label>`;
  }).join('');
  return `<div class="prop-card ksys-card" data-id="${esc(p.id)}" data-action-type="${esc(p.action_type)}">
    <div class="ksys-ch">
      <span class="ksys-ic ai" aria-hidden="true">${esc(m.icon)}</span>
      <b class="ksys-name">${esc(m.label)}${objLabel?' · '+esc(objLabel):''}</b>
      <span class="ksys-when">conf. ${esc(conf)}</span>
    </div>
    ${p.explanation?`<div class="ksys-detail">${esc(p.explanation)}</div>`:''}
    ${fuentesHtml}${noVerifHtml}
    ${fieldsHtml?`<div class="ksys-fields">${fieldsHtml}</div>`:''}
    <div class="ksys-acts">
      <button type="button" class="prop-approve key-btn ksys-pri">✓ ${esc(_sysL('Aprobar', 'Approve'))}</button>
      <button type="button" class="prop-reject key-btn">✗ ${esc(_sysL('Rechazar', 'Reject'))}</button>
      <span class="prop-status" aria-live="polite"></span>
    </div>
  </div>`;
}
/* Track C — Investigador Autónomo: investigación web puntual bajo demanda.
   Corre en el server en segundo plano (20-60s); aquí se sondea el estado y al
   terminar se refresca la lista (la tesis aparece como propuesta a aprobar). */
window.lanzarInvestigacion = async function(){
  const q = ($('investigar-q')&&$('investigar-q').value||'').trim();
  const st = $('investigar-status');
  if(!q){ if(st) st.textContent = _sysL('Escribe qué investigar.', 'Type what to research.'); return; }
  const base = (typeof BASE!=='undefined') ? BASE : '';
  const actor = window.khipuActor ? window.khipuActor() : 'usuario';
  // Escritura de la ontología → PIN de operador (X-Trade-Pin) vía _tradeFetch.
  // El primer envío puede pedir el PIN; los sondeos NUNCA (interactive=false).
  const post = async(interactive)=>{
    try{
      const r = await window._tradeFetch(`${base}/api/ontology/agents/investigar`,{
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({query:q, actor})}, interactive);
      return {ok:r.ok, code:r.status, data:await r.json().catch(()=>null)};
    }catch(e){ return {ok:false, code:0, data:{error:'Error de red', error_en:'Network error'}}; }
  };
  if(st) st.textContent = _sysL('🌐 Investigando en la web… (20-60s)', '🌐 Researching the web… (20-60s)');
  let res = await post(true);
  if(!res.ok){
    if(st) st.textContent = window._tradeErrText(res.data, res.code);
    return;
  }
  let tries = 0;
  const poll = async()=>{
    tries++;
    const r = await post(false);                 // re-POST = consulta estado (throttle server)
    const d = r.data||{};
    if(d.running && tries < 24){ setTimeout(poll, 5000); return; }
    const last = d.last||{};
    if(st) st.textContent = last.status==='ok'
      ? (_sysEN() ? `✓ Proposal created (${last.action_type}) — review it below and approve or reject it.`
                  : `✓ Propuesta creada (${last.action_type}) — revísala abajo y apruébala o recházala.`)
      : (last.status==='sin_resultado' ? (last.hint||_sysL('Sin resultados.', 'No results.')) : (last.error||_sysL('Terminó.', 'Finished.')));
    if(last.status==='ok') window.openPropuestas(true);
  };
  setTimeout(poll, 6000);
};

window.openPropuestas = async function(fresh){
  const body = $('propuestas-body');
  if(fresh) body.innerHTML = _sysEmpty('Actualizando…', 'Refreshing…');
  try{
    const base = (typeof BASE!=='undefined') ? BASE : '';
    const r = await fetch(`${base}/api/ontology/agents/proposals?status=pending`);
    if(!r.ok){
      if(r.status===503){ body.innerHTML = _sysEmpty('La ontología no está configurada en este servidor (falta Postgres).',
        'The ontology is not set up on this server (Postgres is missing).'); return; }
      throw new Error('HTTP '+r.status);
    }
    const d = await r.json();
    $('propuestas-summary').textContent = _sysEN() ? `${d.count} pending` : `${d.count} pendiente${d.count===1?'':'s'}`;
    if(!d.proposals || !d.proposals.length){
      body.innerHTML = _sysEmpty('Sin propuestas pendientes. Dale a «🔍 Revisar ahora» para que los agentes analicen la ontología.',
        'No pending proposals. Press «🔍 Review now» so the agents analyze the ontology.');
      return;
    }
    body.innerHTML = d.proposals.map(_propuestaCard).join('');
    body.querySelectorAll('.prop-card').forEach(card=>{
      const id = card.dataset.id;
      card.querySelector('.prop-approve').onclick = () => _resolveProposal(card, id, 'approve');
      card.querySelector('.prop-reject').onclick = () => _resolveProposal(card, id, 'reject');
    });
  }catch(e){
    body.innerHTML = _sysErrCard(_sysL('No se pudo cargar', 'Could not load'), String(e.message||e), '');
  }
};
async function _resolveProposal(card, id, verb){
  const status = card.querySelector('.prop-status');
  const actor = await _getActorGlobal();
  status.textContent = verb==='approve' ? _sysL('aprobando…', 'approving…') : _sysL('rechazando…', 'rejecting…'); status.style.color='var(--os-ink-2,#A6A8B5)';
  const base = (typeof BASE!=='undefined') ? BASE : '';
  const body = { actor };
  if(verb==='approve'){
    const edits = {};
    card.querySelectorAll('.prop-field').forEach(el=>{
      const k = el.dataset.k;
      const raw = el.value;
      edits[k] = (k==='confidence' || k==='nivel' || k==='delta') && raw!=='' && !isNaN(raw) ? parseFloat(raw) : raw;
    });
    body.edits = edits;
  }
  // Aprobar/rechazar = escritura de la ontología → PIN de operador.
  window._tradeFetch(`${base}/api/ontology/agents/proposals/${encodeURIComponent(id)}/${verb}`, {
    method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body),
  }, true).then(r=>r.json().catch(()=>null).then(d=>({ok:r.ok,d,code:r.status}))).then(({ok,d,code})=>{
    if(ok){ status.textContent = verb==='approve' ? '✓ ' + _sysL('aprobado', 'approved') : '✗ ' + _sysL('rechazado', 'rejected'); status.style.color = verb==='approve' ? 'var(--os-good-ink,#2fbf5b)' : 'var(--os-ink-2,#A6A8B5)';
      setTimeout(()=>{ card.style.opacity='0.4'; card.style.pointerEvents='none'; }, 300);
    } else { status.textContent = '⚠ '+window._tradeErrText(d, code); status.style.color='var(--os-bad-ink,#F47C7C)'; }
  }).catch(()=>{ status.textContent='⚠ '+((window.LANG==='en')?'network error':'error de red'); status.style.color='var(--os-bad-ink,#F47C7C)'; });
}
window.runAgentes = function(){
  const summary = $('propuestas-summary');
  summary.textContent = _sysL('revisando…', 'reviewing…');
  const base = (typeof BASE!=='undefined') ? BASE : '';
  // Correr agentes = escritura de la ontología → PIN de operador.
  window._tradeFetch(`${base}/api/ontology/agents/run`, { method:'POST', headers:{'Content-Type':'application/json'}, body:'{}' }, true)
    .then(r=>r.json().catch(()=>null).then(d=>({d, code:r.status}))).then(({d, code})=>{
      if(d && d.status==='ok'){
        const total = Object.values(d.summary||{}).reduce((s,a)=>s+(a.proposals||0),0);
        summary.textContent = _sysEN() ? `${total} new proposal${total===1?'':'s'}` : `${total} propuesta${total===1?'':'s'} nueva${total===1?'':'s'}`;
        window.openPropuestas(true);
      } else { summary.textContent = '⚠ ' + window._tradeErrText(d, code); }
    }).catch(()=>{ summary.textContent = '⚠ ' + ((window.LANG==='en')?'network error':'error de red'); });
};
window.closePropuestas = function(){ window.closeSistema && window.closeSistema(); };

/* ── ⚙ Sistema: overlay unificado (Diagnóstico / Registro / Propuestas) ──── */
let _sistemaTab = 'diag';
// Textos ES/EN del armazón (Khipus OS 2026-10-10): los elementos llevan data-ksys-t (texto) · data-ksys-h (HTML
// FIJO de esta tabla, nunca datos) · data-ksys-ph (placeholder) · data-ksys-al (aria-label). Se aplican al abrir
// y al cambiar de pestaña, así el botón de idioma se respeta sin re-pintar nada más.
const SYS_I18N = {
  es:{ panel_al:'Sistema', close:'Cerrar',
       tab_diag:'🩺 Diagnóstico', tab_registro:'📋 Registro', tab_propuestas:'🔔 Propuestas', tab_gasto:'💰 Gasto IA',
       t_diag:'🩺 Estado del Sistema', t_registro:'📋 Registro de Acciones', t_propuestas:'🔔 Propuestas de Agentes', t_gasto:'💰 Gasto de IA',
       diag_sub:'Prueba <b>en vivo</b> cada API key y servicio del servidor — no solo si existen, sino si <b>de verdad responden</b>. Las keys nunca se muestran.',
       retest:'↻ Re-probar', diag_loading:'Cargando diagnóstico…',
       reg_sub:'Tesis, decisiones, anotaciones y correcciones — quién hizo qué, cuándo y por qué. Se registran desde la ficha de cada empresa en <b>◈ Grafo Temporal</b>.',
       reg_filter:'Filtrar por autor…', refresh:'↻ Actualizar', reg_loading:'Cargando registro…',
       prop_sub:'7 agentes vigilan la ontología (riesgo NRS, noticias, tu cartera, consistencia del grafo, radar de empresas, hiperaristas e investigación web) y <b>proponen</b> — nada se ejecuta sin que tú apruebes.',
       prop_run:'🔍 Revisar ahora', inv_ph:'Investiga en la web… (ej. «¿CXMT amenaza a Micron?»)', inv_al:'Investiga en la web',
       inv_go:'🌐 Investigar', prop_loading:'Cargando propuestas…' },
  en:{ panel_al:'System', close:'Close',
       tab_diag:'🩺 Diagnostics', tab_registro:'📋 Log', tab_propuestas:'🔔 Proposals', tab_gasto:'💰 AI spend',
       t_diag:'🩺 System status', t_registro:'📋 Action log', t_propuestas:'🔔 Agent proposals', t_gasto:'💰 AI spend',
       diag_sub:'Tests every API key and server service <b>live</b> — not just whether they exist, but whether they <b>really respond</b>. Keys are never shown.',
       retest:'↻ Re-test', diag_loading:'Loading diagnostics…',
       reg_sub:'Theses, decisions, notes and corrections — who did what, when and why. They are recorded from each company\'s card in <b>◈ Temporal Graph</b>.',
       reg_filter:'Filter by author…', refresh:'↻ Refresh', reg_loading:'Loading log…',
       prop_sub:'7 agents watch the ontology (NRS risk, news, your portfolio, graph consistency, company radar, hyperedges and web research) and <b>propose</b> — nothing runs until you approve it.',
       prop_run:'🔍 Review now', inv_ph:'Research the web… (e.g. “Is CXMT a threat to Micron?”)', inv_al:'Research the web',
       inv_go:'🌐 Research', prop_loading:'Loading proposals…' },
};
function _sistemaApplyLang(){
  const D = SYS_I18N[_sysEN() ? 'en' : 'es'];
  const root = $('sistema-panel'); if(!root) return D;
  const each = (attr, fn) => {
    if(root.hasAttribute(attr)) fn(root, root.getAttribute(attr));
    root.querySelectorAll('['+attr+']').forEach(el=>fn(el, el.getAttribute(attr)));
  };
  each('data-ksys-t',  (el,k)=>{ if(D[k]!=null) el.textContent = D[k]; });
  each('data-ksys-h',  (el,k)=>{ if(D[k]!=null) el.innerHTML = D[k]; });       // solo cadenas fijas de SYS_I18N
  each('data-ksys-ph', (el,k)=>{ if(D[k]!=null) el.placeholder = D[k]; });
  each('data-ksys-al', (el,k)=>{ if(D[k]!=null) el.setAttribute('aria-label', D[k]); });
  // la entrada 🤖 Conectar IAs (engine/mcpconnect.js) se re-rotula en el idioma actual (idempotente)
  try{ if(window.KhipuMCP && window.KhipuMCP.installEntry) window.KhipuMCP.installEntry(); }catch(e){}
  return D;
}
function _switchSistemaTab(t){
  const toAudit = t === 'auditoria';               // paso 24: ⚖ Auditoría vive DENTRO de 📋 Registro (sin pestaña nueva)
  if(toAudit) t = 'registro';
  _sistemaTab = t;
  document.querySelectorAll('#sistema-tabseg button').forEach(b=>{
    const on = b.dataset.t===t;
    b.classList.toggle('active', on);
    b.setAttribute('aria-selected', on ? 'true' : 'false');
  });
  $('sistema-diag').style.display = t==='diag' ? 'block' : 'none';
  $('sistema-registro').style.display = t==='registro' ? 'block' : 'none';
  $('sistema-propuestas').style.display = t==='propuestas' ? 'block' : 'none';
  $('sistema-gasto').style.display = t==='gasto' ? 'block' : 'none';
  const D = _sistemaApplyLang();
  if(D['t_'+t]) $('sistema-title').textContent = D['t_'+t];
  if(t==='gasto') { if(window.KhipuSpend) window.KhipuSpend.render('sistema-gasto'); }
  else if(t==='diag') window.openDiagnostics();
  else if(t==='registro'){
    window.openRegistro();
    if(window.KhipuAudit) window.KhipuAudit.mount('audit-box');
    if(toAudit){ const ab=$('audit-box'); if(ab && ab.scrollIntoView) ab.scrollIntoView({block:'start'}); }
  }
  else if(t==='propuestas') window.openPropuestas();
}
window.openSistema = function(tab){
  $('sistema-overlay').classList.add('show');
  $('sistema-panel').classList.add('show');
  _switchSistemaTab(tab || _sistemaTab);
};
window.closeSistema = function(){
  $('sistema-overlay').classList.remove('show');
  $('sistema-panel').classList.remove('show');
};
document.querySelectorAll('#sistema-tabseg button').forEach(b=>b.addEventListener('click', ()=>_switchSistemaTab(b.dataset.t)));
$('pref-live').onchange=e=>{ const p=prefs(); p.live=e.target.checked; savePrefs(p); LivePrices.restart(); DataHealth.render(); };
$('pref-notif').onchange=e=>{ const p=prefs(); p.notif=e.target.checked; savePrefs(p);
  if(e.target.checked && 'Notification' in window && Notification.permission==='default') Notification.requestPermission(); };
$('pref-aicache').onchange=e=>{ const p=prefs(); p.aicache=e.target.checked; savePrefs(p); };
$('data-clear-quotes').onclick=()=>{ localStorage.removeItem('eco_quotes'); localStorage.removeItem('eco_quotes_ts');
  MKT.quotes={}; MKT.ts=null; MKT.liveMeta=null; if(activeTab==='market') renderMarket(); toast(LANG==='en'?'Price cache cleared':'Caché de precios borrada'); };
$('data-clear-ai').onclick=()=>{ Object.keys(localStorage).filter(k=>k.startsWith('ai_analysis')).forEach(k=>localStorage.removeItem(k));
  toast(LANG==='en'?'AI analysis cleared':'Análisis IA borrados'); if(selected) renderDetail(selected); };
$('data-clear-cache').onclick=()=>{ idb.clear(); toast(LANG==='en'?'Data cache cleared':'Caché de datos vaciada'); };

// Khipu API key generation
document.getElementById('kfi-gen-btn').addEventListener('click', async () => {
  const tier = document.getElementById('kfi-tier').value;
  const result = document.getElementById('kfi-result');
  try {
    const resp = await fetch('/v1/auth/key', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({user_id: 'browser_'+Date.now(), tier}) });
    const data = await resp.json();
    if (data.api_key) {
      localStorage.setItem('khipu_api_key', data.api_key);
      result.style.display = 'block';
      result.innerHTML = `<span style="color:var(--ink-2)">✓ Clave ${tier} generada y guardada</span><br><span style="color:var(--ink-3)">${data.api_key.substring(0,24)}…</span>`;
    } else { result.style.display='block'; result.textContent='Error: '+(data.error||'desconocido'); }
  } catch(e) { result.style.display='block'; result.textContent='Error: '+e.message; }
});

/* ════════════════ §F · PRECIOS EN VIVO (Feature 1) + portfolio (Feature 7) ════════════════ */
const LivePrices = {
  ws:null, connected:false, poll:null, subs:[],
  async restart(){ this.stop(); this.start(); },
  stop(){ try{ this.ws&&this.ws.close(); }catch(e){} this.ws=null; if(this.poll) clearInterval(this.poll); this.poll=null;
    this.connected=false; this.setPill(false); },
  async start(){
    if(!prefs().live || !Keys.has('finnhub')){ this.setPill(false); DataHealth.render(); return; }
    // (2026-10-04) seed() ELIMINADO: lanzaba ~1.090 req/min a /api/quote (límite
    // 120/min → 429 silenciosos y quemaba la cuota de Finnhub). Los precios de
    // TODO el catálogo llegan por lotes vía window.loadLiveQuotes().
    try{ await this.connectWS(); }catch(e){ this.startPoll(); }
  },
  // Solo tickers de EE.UU. (sin punto: el WebSocket de Finnhub no cubre otras
  // bolsas) y máximo 45 (plan gratuito ≈ 50 símbolos).
  wsTickers(){ return usTickers().filter(s=>!s.includes('.')).slice(0,45); },
  async connectWS(){
    const token=await DataLayer.wsToken(); if(!token) throw new Error('no token');
    const ws=new WebSocket('wss://ws.finnhub.io?token='+token); this.ws=ws;
    this.subs=this.wsTickers();
    ws.onopen=()=>{ this.connected=true; this.setPill(true); DataHealth.render();
      this.subs.forEach(s=>ws.send(JSON.stringify({type:'subscribe',symbol:s})));
      if(this.poll){ clearInterval(this.poll); this.poll=null; } /* el resto llega por lotes */ };
    ws.onmessage=e=>{ let d; try{ d=JSON.parse(e.data); }catch(_){ return; }
      if(d.type==='trade' && d.data) d.data.forEach(tr=>this.onTrade(tr.s, tr.p)); };
    ws.onerror=()=>{};
    ws.onclose=()=>{ this.connected=false; this.setPill(false); DataHealth.render(); if(prefs().live && Keys.has('finnhub')) this.startPoll(); };
  },
  startPoll(){
    // Sin WebSocket: UN lote por minuto con los ≤45 tickers de EE.UU. (antes:
    // 30 llamadas sueltas a /api/quote por minuto). Pasa por el mismo cargador.
    if(this.poll) clearInterval(this.poll);
    this.poll=setInterval(()=>{
      if(document.hidden) return;
      const list=this.subs.length?this.subs:this.wsTickers();
      if(list.length && window.loadLiveQuotes) window.loadLiveQuotes({tickers:list});
    }, 60000);
  },
  onTrade(ticker, price, pc){
    price=Number(price); if(!(price>0)) return;
    const q=MKT.quotes[ticker]||{}; const prevShown=q.close;
    // contrato: live = precio NUMÉRICO (nunca true/false), src + as_of dicen "en vivo"
    q.close=price; q.live=price; q.src='finnhub'; q.as_of=new Date().toISOString(); delete q.via;
    if(pc!=null) q.prev=pc; if(q.prev==null) q.prev=price;
    q.pct = q.prev ? (price-q.prev)/q.prev*100 : null;
    MKT.quotes[ticker]=q;
    this.updateCell(ticker, prevShown);
    this.updateSummary();
    Alerts.check(ticker, price);
  },
  updateCell(ticker, prevShown){
    if(activeTab!=='market' || MKT.editing) return;
    const row=document.querySelector('#mk-table tr[data-ticker="'+CSS.escape(ticker)+'"]'); if(!row) return;
    const n=nodeByTicker[ticker]; if(!n) return;
    const q=MKT.quotes[ticker], p=MKT.pos[n.id];
    const chg=(q.prev!=null&&q.close!=null)?(q.close-q.prev)/q.prev:null;
    const val=(p&&q.close!=null)?p.sh*q.close:null;
    const pnlP=(p&&q.close!=null&&p.bp)?(q.close-p.bp)/p.bp:null;
    const cP=row.querySelector('.mk-c-price'), cC=row.querySelector('.mk-c-chg'),
          cV=row.querySelector('.mk-c-val'), cN=row.querySelector('.mk-c-pnl');
    if(cP) cP.innerHTML='$'+fmtN(q.close)+quoteSrcChip(q, ticker);
    if(cC){ cC.className='mk-c-chg '+(chg==null?'td-dim':chg>=0?'td-up':'td-down'); cC.innerHTML=fmtPct(chg); }
    if(cV) cV.innerHTML = val!=null?'$'+fmtN(val):'<span class="td-dim">—</span>';
    if(cN){ cN.className='mk-c-pnl '+(pnlP==null?'td-dim':pnlP>=0?'td-up':'td-down'); cN.innerHTML=fmtPct(pnlP); }
    if(prevShown!=null && q.close!==prevShown){
      const dir=q.close>prevShown?'flash-up':'flash-down';
      row.classList.remove('flash-up','flash-down'); void row.offsetWidth; row.classList.add(dir);
    }
  },
  updateSummary(){
    let totVal=0,totCost=0,totDay=0,any=false;
    marketRows().forEach(n=>{ const p=MKT.pos[n.id], q=quoteOf(n);
      if(p&&q&&q.close!=null){ any=true; totVal+=p.sh*q.close; totCost+=p.sh*p.bp; if(q.prev!=null) totDay+=p.sh*(q.close-q.prev); } });
    const elV=$('mk-value'),elP=$('mk-pnl'),elD=$('mk-day'); if(!elV) return;
    elV.textContent=any?'$'+fmtN(totVal):'—';
    const pnl=totVal-totCost;
    elP.textContent=any?(pnl>=0?'+$':'-$')+fmtN(Math.abs(pnl))+' ('+fmtPct(totCost?pnl/totCost:null)+')':'—';
    elP.className='mv '+(any?(pnl>=0?'up':'down'):'');
    elD.textContent=any?(totDay>=0?'+$':'-$')+fmtN(Math.abs(totDay)):'—';
    elD.className='mv '+(any?(totDay>=0?'up':'down'):'');
  },
  setPill(on){ const el=$('live-pill'); if(el) el.classList.toggle('on',!!on); }
};
V8.market = { afterRender(){ LivePrices.setPill(LivePrices.connected); } };

/* Export all nodes CSV */
document.getElementById('export-btn')?.addEventListener('click', () => {
  const rows = [['ID','Empresa','Ticker','Categoría','País','Precio','Cambio%','NRS','Acciones','P.Compra','Valor','P&L%']];
  (window.NODES || []).forEach(n => {
    const q = n.mkt ? (MKT.quotes[n.mkt] || {}) : {};
    const p = MKT.pos[n.id];
    const chg = (q.close && q.prev) ? ((q.close-q.prev)/q.prev*100).toFixed(2) : '';
    const nrs = (typeof computeNRS==='function') ? computeNRS(n.id) : '';
    const val = (p && q.close) ? (p.sh * q.close).toFixed(2) : '';
    const pnl = (p && q.close && p.bp) ? (((q.close-p.bp)/p.bp)*100).toFixed(2) : '';
    rows.push([n.id, n.label, n.mkt||'', n.cat, n.country||'', q.close||'', chg, nrs, p?p.sh:'', p?p.bp:'', val, pnl]);
  });
  const csv = rows.map(r => r.map(v => '"'+String(v).replace(/"/g,'""')+'"').join(',')).join('\n');
  const a = document.createElement('a');
  a.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv);
  a.download = 'khipu-finance-' + new Date().toISOString().slice(0,10) + '.csv';
  a.click();
  if (typeof toast === 'function') toast('CSV exportado · ' + (window.NODES||[]).length + ' empresas');
});

/* Export CSV (Feature 7) */
$('mk-export').onclick=()=>{
  const rows=[['ticker','empresa','acciones','precio_compra','precio_actual','pnl_usd','pnl_pct','valor']];
  NODES.forEach(n=>{ const p=MKT.pos[n.id]; if(!p) return; const q=quoteOf(n); const cur=q&&q.close!=null?q.close:'';
    const val=cur!==''?p.sh*cur:''; const pnl=cur!==''?(cur-p.bp)*p.sh:''; const pct=cur!==''&&p.bp?((cur/p.bp-1)*100).toFixed(2):'';
    rows.push([n.mkt||'', '"'+(n.label||'').replace(/"/g,'""')+'"', p.sh, p.bp, cur, (pnl===''?'':pnl.toFixed(2)), pct, (val===''?'':val.toFixed(2))]); });
  if(rows.length===1){ toast(LANG==='en'?'No positions to export':'Sin posiciones que exportar'); return; }
  const csv=rows.map(r=>r.join(',')).join('\n');
  const blob=new Blob([csv],{type:'text/csv;charset=utf-8'}); const url=URL.createObjectURL(blob);
  const a=document.createElement('a'); a.href=url; a.download='portfolio.csv'; a.click(); setTimeout(()=>URL.revokeObjectURL(url),2000);
};

/* ════════════════ §G · ENRIQUECER PANEL DETALLE ════════════════ */
const _renderDetail = renderDetail;
renderDetail = function(id){
  _renderDetail(id);
  try{ V8detail.enrich(id); }catch(e){ console.warn('v8 enrich',e); }
};

const V8detail = {
  token:0, fundCache:{}, newsCache:{}, newsRange:{},
  /* Phase 1 · M6 en el sitio correcto: la historia de la entidad con la
     FUENTE de cada hecho, en el panel que se abre desde el mapa principal.
     (Primero se puso solo en la ficha del Grafo Temporal — una pantalla que
     casi no se usa — y desde el mapa "todo se veía como antes".)
     Además, la primera vez por sesión ingiere noticias de esa empresa al
     grafo, para que la historia crezca sola con fuentes citables. */
  _histIngested:new Set(),
  loadHistory(id,my){
    const el=$('v8-history'); if(!el) return;
    const lang=(LANG==='en')?'en':'es';
    fetch(`${BASE}/api/ontology/objects/${encodeURIComponent(id)}/timeline?limit=8&lang=${lang}`)
      .then(r=>r.ok?r.json():null).then(d=>{
        if(my!==this.token) return;
        if(!d||!Array.isArray(d.timeline)||!d.timeline.length){
          el.innerHTML=`<div class="v8-loading" style="font-style:normal">${t('hist_empty')}</div>`;
        } else {
          const nsrc=d.timeline.filter(e=>e.source&&e.source.url).length;
          const dot=tr=>{const n=+tr||0;const c=n>=3?'#43C896':n===2?'#E0B25C':'#8A857A';
            const lb=n>=3?t('hist_primary'):n===2?t('hist_press'):t('hist_weak');
            return `<span title="${esc(lb)}" style="display:inline-block;width:6px;height:6px;border-radius:50%;background:${c};margin-right:4px;vertical-align:middle"></span>`;};
          const when=iso=>{if(!iso)return'';const x=new Date(iso);return isNaN(x)?'':x.toLocaleDateString(lang,{day:'2-digit',month:'short',year:'numeric'});};
          el.innerHTML=`<div style="font-size:10.5px;color:var(--ink-3);margin-bottom:4px">${d.timeline.length} ${t('hist_facts')} · ${nsrc} ${t('hist_src')}</div>`+
            d.timeline.map(e=>{
              const src=e.source&&e.source.url?e.source:null;
              const host=src?(src.publisher||src.url).replace(/^https?:\/\//,'').split('/')[0]:'';
              return `<div style="padding:5px 0;border-bottom:1px solid var(--line);line-height:1.4">
                <div style="display:flex;gap:6px;align-items:baseline">
                  <span style="font-size:11.5px;color:var(--ink-2);flex:1">${e.kind==='news'?'📰 ':''}${esc(e.title||'')}</span>
                  <span style="font-size:10px;color:var(--ink-3);white-space:nowrap">${e.valid_from_known===false?esc(lang==='en'?'since tracked':'desde que se rastrea'):esc(when(e.at))}</span></div>
                ${src?`<a href="${safeUrl(src.url)}" target="_blank" rel="noopener noreferrer" style="font-size:10.5px;color:var(--ink-3);text-decoration:none">${dot(src.trust)}${esc(host)} ↗</a>`:''}
              </div>`;}).join('');
        }
        this.ingestOnce(id,my);
      }).catch(()=>{ el.innerHTML=''; });
  },
  ingestOnce(id,my){
    if(this._histIngested.has(id)) return;
    this._histIngested.add(id);
    let actor='ingesta_ui'; try{ actor=localStorage.getItem('khipu_actor')||actor; }catch(e){}
    fetch(`${BASE}/api/ontology/ingest/news`,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({entity_id:id,actor,limit:8})})
      .then(r=>r.ok?r.json():null).then(res=>{
        if(res&&res.new&&my===this.token) this.loadHistory(id,my);
      }).catch(()=>{});
  },
  enrich(id){
    const d=NODE_BY_ID[id]; if(!d) return;
    window.fillLiveMeta($('detail'), d);   // empleados / capitalización / ingresos EN VIVO
    const tk=d.mkt; const my=++this.token;
    const host=document.createElement('div'); host.id='v8-detail-host';
    // posición / P&L
    host.innerHTML = this.positionHTML(d) + (tk?(
      `<div class="v8-sec" id="v8-earn"></div>
       <div class="v8-sec"><div class="v8-sec-h">${t('d_fund')}</div><div id="v8-fund"><div class="v8-loading">…</div></div></div>
       <div class="v8-sec"><div class="v8-sec-h">${t('d_news')}<div class="v8-chips" id="v8-news-range">
          <span class="v8-mini-chip" data-r="1">${t('news_24')}</span>
          <span class="v8-mini-chip active" data-r="7">${t('news_7')}</span>
          <span class="v8-mini-chip" data-r="30">${t('news_30')}</span></div></div>
          <div id="v8-news-digest"></div><div id="v8-news"><div class="v8-loading">…</div></div></div>
       <div class="v8-sec"><div class="v8-sec-h">${t('d_ai')}</div><button class="ai-btn" id="v8-ai-btn">${t('ai_btn')}</button><div id="v8-ai"></div></div>
       <div class="v8-sec"><div class="v8-sec-h">${t('d_alerts')}</div><div id="v8-alerts"></div></div>`
    ) : `<div class="v8-sec"><div class="v8-need-key">${t('v8_nolist')}</div></div>`)
      + `<div class="v8-sec"><div class="v8-sec-h">${t('d_research')}</div><div id="v8-research"><div class="v8-loading">…</div></div></div>`
      + `<div class="v8-sec"><div class="v8-sec-h">${t('d_history')}</div><div id="v8-history"><div class="v8-loading">…</div></div></div>`;
    const detail=$('detail'); const stressBtn=detail.querySelector('.stress-btn');
    if(stressBtn) detail.insertBefore(host, stressBtn); else detail.appendChild(host);
    // wire collapsible sections
    host.querySelectorAll('.v8-sec').forEach(sec => {
      sec.classList.add('v8-collapsible');
      const h = sec.querySelector('.v8-sec-h');
      if(h) h.addEventListener('click', () => sec.classList.toggle('collapsed'));
    });

    this.loadHistory(id,my);
    if(window.KhipuResearch) window.KhipuResearch.renderInline($('v8-research'), id);   /* Phase 2: investigación IA */
    if(!tk) return;
    this.loadEarnings(id,tk,my);
    this.loadFundamentals(id,tk,my);
    this.newsRange[id]=this.newsRange[id]||7;
    this.loadNews(id,tk,my);
    Alerts.renderInDetail(id, tk);
    // chips de rango de noticias
    const rc=$('v8-news-range'); if(rc) rc.querySelectorAll('.v8-mini-chip').forEach(c=>{
      c.classList.toggle('active', +c.dataset.r===this.newsRange[id]);
      c.onclick=()=>{ this.newsRange[id]=+c.dataset.r; rc.querySelectorAll('.v8-mini-chip').forEach(x=>x.classList.toggle('active',x===c)); this.loadNews(id,tk,this.token); };
    });
    // botón IA
    const aib=$('v8-ai-btn'); if(aib) aib.onclick=()=>this.runAI(id);
    this.showCachedAI(id);
  },
  positionHTML(d){
    const p=MKT.pos[d.id]; if(!p) return '';
    const q=MKT.quotes[d.mkt]; const cur=q&&q.close!=null?q.close:null;
    const val=cur!=null?p.sh*cur:null, cost=p.sh*p.bp, pnl=val!=null?val-cost:null, pct=val!=null&&cost?pnl/cost:null;
    return `<div class="v8-sec"><div class="v8-sec-h">${t('d_pos')}</div><div class="pos-box">
      <div class="pb-row"><span>${t('pos_shares')}</span><span class="pv">${fmtN(p.sh,0)} @ $${fmtN(p.bp)}</span></div>
      <div class="pb-row"><span>${t('pos_value')}</span><span class="pv">${val!=null?'$'+fmtN(val):'—'}</span></div>
      <div class="pb-row"><span>${t('pos_pnl')}</span><span class="pv ${pnl==null?'':pnl>=0?'up':'down'}">${pnl!=null?(pnl>=0?'+$':'-$')+fmtN(Math.abs(pnl))+' ('+fmtPct(pct)+')':'—'}</span></div>
    </div></div>`;
  },
  async loadEarnings(id,tk,my){
    const el=$('v8-earn'); if(!el) return;
    if(!Keys.has('finnhub')){ el.innerHTML=this.needKey(); return; }
    el.innerHTML=`<div class="v8-sec-h">${t('d_earn')}</div><div class="v8-loading">…</div>`;
    try{
      const data=await DataLayer.earnings(tk); if(my!==this.token) return;
      const cal=(data&&data.earningsCalendar)||[]; const now=Date.now();
      const future=cal.filter(e=>new Date(e.date).getTime()>=now-864e5).sort((a,b)=>new Date(a.date)-new Date(b.date));
      const past=cal.filter(e=>new Date(e.date).getTime()<now).sort((a,b)=>new Date(b.date)-new Date(a.date));
      const next=future[0], last=past[0];
      if(!next && !last){ el.innerHTML=`<div class="v8-sec-h">${t('d_earn')}</div><div class="v8-loading">—</div>`; return; }
      let tag='';
      if(last && last.epsActual!=null && last.epsEstimate!=null){
        const beat=last.epsActual>=last.epsEstimate; const diff=last.epsEstimate?((last.epsActual-last.epsEstimate)/Math.abs(last.epsEstimate)*100):0;
        tag=`<span class="eb-tag ${beat?'beat':'miss'}">${beat?t('earn_beat'):t('earn_miss')} ${(diff>=0?'+':'')+diff.toFixed(0)}%</span>`;
      }
      let nextHtml='';
      if(next){ const days=Math.round((new Date(next.date).getTime()-now)/864e5);
        nextHtml=`📅 <span class="eb-date">${next.date}</span> ${tr('earn_in',{d:Math.max(0,days)})}`+
          (next.epsEstimate!=null?` · ${t('earn_eps')}: $${next.epsEstimate}`:'');
        if(days>=0 && days<=7) V8earnings.applyCorona(id);
      }
      el.innerHTML=`<div class="v8-sec-h">${t('d_earn')}</div><div class="earnings-badge">${nextHtml||'—'} ${tag}</div>`;
    }catch(e){ if(my===this.token) el.innerHTML=`<div class="v8-sec-h">${t('d_earn')}</div><div class="v8-loading">—</div>`; }
  },
  async loadFundamentals(id,tk,my){
    const el=$('v8-fund'); if(!el) return;
    if(!Keys.has('fmp')){ el.innerHTML=this.needKey(); return; }
    try{
      const f=await DataLayer.fundamentals(tk); if(my!==this.token) return;
      this.fundCache[id]=f;
      const m=(f.metrics&&f.metrics[0])||{};
      const pe=m.peRatio!=null?(+m.peRatio).toFixed(1)+'x':'—';
      const ev=m.enterpriseValueOverEBITDA!=null?(+m.enterpriseValueOverEBITDA).toFixed(1)+'x':'—';
      const pt=(f.priceTarget&&f.priceTarget[0])||{};
      const q=MKT.quotes[tk]; const cur=q&&q.close!=null?q.close:null;
      let ptStr='—', ptUp='';
      if(pt.targetConsensus!=null){ ptStr='$'+(+pt.targetConsensus).toFixed(0);
        if(cur){ const up=(pt.targetConsensus/cur-1)*100; ptStr+=` ${up>=0?'↑':'↓'}${Math.abs(up).toFixed(0)}%`; ptUp=up>=0?'up':'down'; } }
      // rating de analistas → consenso simple
      const r=(f.ratings&&f.ratings[0])||{};
      // Es lo que OPINAN analistas externos (FMP), no Khipus. Sin calificaciones
      // → '—' (antes mostraba "Mantener" que nadie había dado).
      const buys=(r.analystRatingsbuy||r.analystRatingsBuy||0)+(r.analystRatingsStrongBuy||0);
      const sells=(r.analystRatingsSell||0)+(r.analystRatingsStrongSell||0);
      const holds=(r.analystRatingsHold||0);
      const tot=buys+sells+holds;
      const rate = !tot ? '—' : (LANG==='en'
        ? `<span title="External analysts' ratings (FMP), not Khipus'">${buys} buy · ${holds} hold · ${sells} sell</span>`
        : `<span title="Calificaciones de analistas externos (FMP), no de Khipus">${buys} compra · ${holds} mant. · ${sells} venta</span>`);
      el.innerHTML=`<div class="fund-grid">
        <div class="fund-card"><div class="fl">${t('fund_pe')}</div><div class="fv">${pe}</div></div>
        <div class="fund-card"><div class="fl">${t('fund_ev')}</div><div class="fv">${ev}</div></div>
        <div class="fund-card"><div class="fl">${t('fund_pt')}</div><div class="fv ${ptUp}" style="font-size:15px">${ptStr}</div><div class="fs">${pt.numberOfAnalysts?tr('fund_analysts',{n:pt.numberOfAnalysts}):''}</div></div>
        <div class="fund-card"><div class="fl">${t('fund_ins')}</div><div class="fv" style="font-size:14px">${rate}</div></div>
      </div>`;
      this.loadInsiders(id,tk,my,el);
    }catch(e){ if(my===this.token) el.innerHTML=`<div class="v8-loading">—</div>`; }
  },
  async loadInsiders(id,tk,my,fundEl){
    try{
      const ins=await DataLayer.insiders(tk); if(my!==this.token) return;
      if(!ins||!ins.length) return;
      const rows=ins.slice(0,5).map(x=>{
        const buy=/P-|Buy|Purchase/i.test(x.transactionType||x.acquisitionOrDisposition||'')|| (x.acquisitionOrDisposition==='A');
        const val=(x.securitiesTransacted&&x.price)?x.securitiesTransacted*x.price:null;
        return `<div class="insider-row"><span class="ir-name">${esc((x.reportingName||x.typeOfOwner||'—'))}</span>
          <span class="ir-act ${buy?'buy':'sell'}">${buy?t('ins_buy'):t('ins_sell')}</span>
          <span class="ir-val">${val!=null?(buy?'+':'-')+'$'+fmtN(Math.abs(val)/1e6,1)+'M':''}</span></div>`;
      }).join('');
      fundEl.insertAdjacentHTML('beforeend', `<div style="margin-top:10px"><div class="kc-l" style="margin-bottom:6px">${t('ins_title')}</div>${rows}</div>`);
    }catch(e){}
  },
  async loadNews(id,tk,my){
    const el=$('v8-news'); if(!el) return;
    if(!Keys.has('finnhub')){ el.innerHTML=this.needKey(); return; }
    el.innerHTML='<div class="v8-loading">…</div>';
    try{
      let arr=await DataLayer.news(tk); if(my!==this.token) return;
      this.newsCache[id]=arr||[];
      const range=this.newsRange[id]||7; const cut=Date.now()/1000-range*86400;
      let list=(arr||[]).filter(n=>n.datetime>=cut);
      if(!list.length) list=(arr||[]).slice(0,6);
      if(!list.length){ el.innerHTML=`<div class="v8-loading">${LANG==='en'?'No recent news.':'Sin noticias recientes.'}</div>`; return; }
      el.innerHTML=list.slice(0,8).map(n=>{
        const s=sentiment(n.headline);
        return `<a class="news-item" href="${safeUrl(n.url)}" target="_blank" rel="noopener noreferrer">
          <div class="news-top"><span class="news-src">${esc(n.source||'')}</span><span>${relTime(n.datetime)}</span>
            <span class="news-sent ${s.cls}">${s.icon}</span></div>
          <div class="news-title">${esc(n.headline)}</div></a>`;
      }).join('');
      // botón resumen IA si hay clave de Claude
      const dg=$('v8-news-digest');
      if(dg && Keys.has('claude')) dg.innerHTML=`<button class="ai-btn" style="margin:0 0 10px" id="v8-digest-btn">${t('ai_digest_btn')}</button>`;
      const db=$('v8-digest-btn'); if(db) db.onclick=()=>this.runDigest(id);
    }catch(e){ if(my===this.token) el.innerHTML=`<div class="v8-loading">—</div>`; }
  },
  needKey(){ return `<div class="v8-need-key">${t('v8_needkey')} <a onclick="V8.openSettings()">⚙</a></div>`; },

  /* ----- Feature 5: análisis con IA ----- */
  showCachedAI(id){
    if(!prefs().aicache) return; const d=NODE_BY_ID[id]; if(!d.mkt) return;
    const raw=localStorage.getItem('ai_analysis2_'+d.mkt+'_'+today());
    if(raw){ try{ this.renderAI(id, JSON.parse(raw), true); }catch(e){} }
  },
  async runAI(id){
    const btn=$('v8-ai-btn'); const out=$('v8-ai'); if(!out) return;
    if(!Keys.has('claude')){ out.innerHTML=this.needKey(); return; }
    if(btn){ btn.disabled=true; btn.textContent=t('ai_loading'); }
    const d=NODE_BY_ID[id], meta=NODE_META[id]||{}, q=MKT.quotes[d.mkt]||{};
    const fund=(this.fundCache[id]&&this.fundCache[id].metrics&&this.fundCache[id].metrics[0])||{};
    const pt=(this.fundCache[id]&&this.fundCache[id].priceTarget&&this.fundCache[id].priceTarget[0])||{};
    const news=(this.newsCache[id]||[]).slice(0,3).map(n=>'- '+n.headline+' ('+(n.source||'')+')').join('\n')||'—';
    const system=`Eres un analista de investigación senior especializado en el ecosistema de semiconductores e inteligencia artificial. Evalúas la SALUD DEL NEGOCIO para inversores informados de largo plazo. NUNCA recomiendes comprar, vender ni mantener, ni des precios objetivo propios. Sé preciso y directo, destaca lo que realmente importa. Responde SIEMPRE en ${LANG==='en'?'English':'español'}.`;
    const live=meta.mktcap_live?`capitalización EN VIVO $${meta.mktcap_b}B`:'capitalización en vivo N/D';
    const prompt=`Evalúa la salud del negocio de esta empresa.
Empresa: ${nf(d,'label')||d.label} (${d.ticker})
Categoría en la cadena: ${catLabel(d.cat)}
País: ${d.loc}
Rol: ${nf(d,'role')}
Moat: ${nf(d,'moat')}
Datos de mercado (en vivo): precio ${q.close!=null?'$'+q.close:'N/D'}, ${live}, P/E ${fund.peRatio!=null?(+fund.peRatio).toFixed(1):'N/D'}, EV/EBITDA ${fund.enterpriseValueOverEBITDA!=null?(+fund.enterpriseValueOverEBITDA).toFixed(1):'N/D'}, precio objetivo consenso de analistas externos ${pt.targetConsensus!=null?'$'+pt.targetConsensus:'N/D'}.
Datos del CATÁLOGO Khipus (curados a mano, pueden estar desactualizados — no los presentes como actuales): margen ${d.margin!=null?(d.margin*100).toFixed(0)+'%':'N/D'}, crecimiento ${nf(d,'growth')}, CAPEX 2026 ${nf(d,'capex_2026')}, riesgo geopolítico ${meta.geo_risk||'N/D'}.
Noticias recientes:
${news}
Idioma de respuesta: ${LANG==='en'?'English':'español'}.
Devuelve SOLO un objeto JSON válido (sin texto alrededor, sin markdown) con este formato exacto:
{"verdict":"SÓLIDA|POSITIVA|NEUTRAL|DÉBIL|ALTO RIESGO (salud del negocio; en inglés: STRONG|POSITIVE|NEUTRAL|WEAK|HIGH RISK)","confidence":1-5,"headline":"tesis central en una línea (max 80 chars)","bull_case":"caso alcista en 2-3 oraciones","bear_case":"riesgo principal en 2-3 oraciones","key_metric":"métrica clave a vigilar","time_horizon":"horizonte (ej 18-36 meses)","catalysts":["c1","c2","c3"],"comparable":"empresa comparable conocida"}`;
    try{
      const txt=await DataLayer.aiComplete(system, prompt, 1400, 'deep');
      const obj=extractJSON(txt);
      if(!obj) throw new Error('respuesta no parseable');
      if(prefs().aicache && d.mkt) localStorage.setItem('ai_analysis2_'+d.mkt+'_'+today(), JSON.stringify(obj));
      this.renderAI(id, obj, false);
    }catch(e){
      if($('v8-ai')) $('v8-ai').innerHTML=`<div class="ai-err">${esc(String(e.message||e))}</div>`;
    }finally{ if(btn){ btn.disabled=false; btn.textContent=t('ai_btn'); } }
    DataHealth.render();
  },
  renderAI(id, a, cached){
    const out=$('v8-ai'); if(!out) return;
    const vkey=(a.verdict||'').toLowerCase();
    const vcls = /riesgo|risk/.test(vkey)?'riesgo':/sólida|solida|strong/.test(vkey)?'fuerte':/positiva|positive/.test(vkey)?'buy':/neutral/.test(vkey)?'hold':/débil|debil|weak/.test(vkey)?'sell':'riesgo';
    const conf=Math.max(0,Math.min(5,+a.confidence||0));
    const dots=Array.from({length:5},(_,i)=>`<span class="${i<conf?'on':''}"></span>`).join('');
    const cats=(a.catalysts||[]).map(c=>`<li>${esc(c)}</li>`).join('');
    out.innerHTML=`<div class="ai-card"><div class="ai-card-head">✨ ${t('d_ai')}<span class="ai-ts">${cached?(LANG==='en'?'cached':'caché'):''}</span></div>
      <div class="ai-card-body">
        <div class="ai-verdict ${vcls}"><span style="font-size:10px;color:var(--ink-3);margin-right:4px">${t('ai_verdict')}:</span><span class="av-label">${esc(a.verdict||'')}</span><span class="av-conf">${dots}</span><span style="font-size:11px;color:var(--ink-3)">${conf}/5 ${t('ai_conf')}</span></div>
        ${a.headline?`<div class="ai-headline">${esc(a.headline)}</div>`:''}
        ${a.bull_case?`<div class="ai-case bull"><div class="acl">🟢 ${t('ai_bull')}</div><p>${esc(a.bull_case)}</p></div>`:''}
        ${a.bear_case?`<div class="ai-case bear"><div class="acl">🔴 ${t('ai_bear')}</div><p>${esc(a.bear_case)}</p></div>`:''}
        <div class="ai-meta">${a.key_metric?`<span class="am">📊 <b>${t('ai_metric')}:</b> ${esc(a.key_metric)}</span>`:''}${a.time_horizon?`<span class="am">⏱ <b>${t('ai_horizon')}:</b> ${esc(a.time_horizon)}</span>`:''}${a.comparable?`<span class="am"><b>${t('ai_similar')}:</b> ${esc(a.comparable)}</span>`:''}</div>
        ${cats?`<div class="ai-cats"><div class="acl">🚀 ${t('ai_cats')}</div><ul>${cats}</ul></div>`:''}
        <div class="ai-disclaim">${t('ai_disclaim')}</div>
      </div></div>`;
  },
  /* ----- Feature 6: resumen de noticias con IA ----- */
  async runDigest(id){
    const dg=$('v8-news-digest'); const btn=$('v8-digest-btn'); if(!dg) return;
    const news=(this.newsCache[id]||[]).slice(0,8);
    if(!news.length || !Keys.has('claude')) return;
    if(btn){ btn.disabled=true; btn.textContent=t('ai_digest_loading'); }
    const d=NODE_BY_ID[id];
    const list=news.map(n=>'- '+n.headline+(n.summary?(': '+n.summary.slice(0,160)):'')).join('\n');
    const prompt=`Tienes estas noticias de ${d.label} de los últimos días:\n${list}\n\nEn máximo 3 oraciones dime: (1) qué pasa que importa para un inversor a largo plazo, (2) si cambia la tesis de inversión o es ruido de corto plazo. Responde en ${LANG==='en'?'English':'español'}, sin preámbulo, directo.`;
    try{
      const txt=await DataLayer.aiComplete(LANG==='en'?'You are a concise investment news analyst.':'Eres un analista conciso de noticias de inversión.', prompt, 320);
      dg.innerHTML=`<div class="ai-digest"><b>📰 ${LANG==='en'?'AI digest':'Resumen IA'}:</b> ${esc(txt.trim())}</div>`;
    }catch(e){ if(btn){ btn.disabled=false; btn.textContent=t('ai_digest_btn'); } }
  }
};

window.V8detail = V8detail;

/* ── KhipuLive: perfil EN VIVO de una empresa cotizada (2026-09-28) ─────────
   window.KhipuLive.profile(ticker) → Promise<perfil|null> sobre
   /api/company/live/<ticker> (Yahoo quoteSummary → Finnhub → Yahoo chart; el
   servidor cachea 90 s). Aquí, caché de 60 s en memoria POR PROMESA: la ficha
   del mapa, el X-Ray y la capitalización piden lo mismo a la vez → 1 request.
   El perfil trae `available`; sin dato → los llamadores dejan el catálogo.
   OJO: engine/live.js (cargado DESPUÉS) hace `window.KhipuLive = {tick, cycle}`
   — por eso KhipuLive es una propiedad con setter que FUSIONA lo asignado en
   este mismo objeto en vez de reemplazarlo (no se pierde profile()). */
(function(){
  const TTL = 60000, _c = {};
  const SRC = { yahoo:'Yahoo Finance', yahoo_chart:'Yahoo Finance', finnhub:'Finnhub' };
  const en = () => (typeof LANG!=='undefined' && LANG==='en');
  const api = {
    profile(ticker){
      const tk = String(ticker==null?'':ticker).trim();
      if(!tk) return Promise.resolve(null);
      const k = tk.toUpperCase(), hit = _c[k];
      if(hit && Date.now()-hit.t < TTL) return hit.p;
      const p = fetch(BASE+'/api/company/live/'+encodeURIComponent(tk))
        .then(r => r.ok ? r.json() : null)
        .then(j => { if(!j || typeof j!=='object'){ delete _c[k]; return null; } return j; })
        .catch(() => { delete _c[k]; return null; });   // fallo de red → reintenta la próxima vez
      _c[k] = { t: Date.now(), p };
      return p;
    },
    /* "en vivo · Yahoo Finance · 14:32:05" (bilingüe) — para el title de cada dato */
    stamp(p){
      if(!p) return '';
      const src = SRC[p.source] || p.source || '—';
      const t = p.as_of ? new Date(p.as_of) : null;
      const hh = (t && !isNaN(t)) ? t.toLocaleTimeString(en()?'en-US':'es-ES',{hour:'2-digit',minute:'2-digit',second:'2-digit'}) : '';
      return (en()?'live':'en vivo')+' · '+src+(hh?' · '+hh:'');
    },
    fmtUsdB(b){   // miles de millones USD → $1.23T / $45B / $3.4B / $560M
      b = +b; if(!isFinite(b) || b<=0) return '—';
      return b>=1000 ? '$'+(b/1000).toFixed(2)+'T' : b>=10 ? '$'+Math.round(b)+'B' : b>=1 ? '$'+b.toFixed(1)+'B' : '$'+Math.round(b*1000)+'M';
    },
    fmtEmp(v, compact){
      v = Math.round(+v); if(!isFinite(v) || v<=0) return '—';
      if(compact) return v>=1000 ? Math.round(v/1000)+'K' : String(v);
      return v.toLocaleString(en()?'en-US':'es-ES');
    },
    sourceName(p){ return p ? (SRC[p.source] || p.source || '') : ''; },
    clear(){ Object.keys(_c).forEach(k => delete _c[k]); }
  };
  const prev = window.KhipuLive;
  try {
    Object.defineProperty(window, 'KhipuLive', {
      configurable: true, enumerable: true,
      get(){ return api; },
      set(v){ if(v && typeof v==='object' && v!==api) Object.keys(v).forEach(k => { if(!(k in api)) api[k]=v[k]; }); }
    });
  } catch(e){ window.KhipuLive = api; }
  if(prev && typeof prev==='object') window.KhipuLive = prev;   // fusiona lo que ya hubiera
})();

/* marca un dato como EN VIVO: texto + title "en vivo · fuente · hora" + punto verde */
function _paintLive(el, txt, p){
  if(!el || !el.isConnected || txt==null || txt==='—') return false;
  el.textContent = txt;
  el.title = window.KhipuLive.stamp(p);
  el.classList.add('is-live');
  return true;
}

/* El "en vivo · fuente · hora" vive en el title, que en el teléfono NO se ve
   (no hay hover). Tocar (o hacer clic en) un dato con punto verde abre un
   globito con esa misma línea + qué significa el punto. Delegado en document:
   sirve para la ficha del mapa, el X-Ray (cajón y Cabina) y lo que venga. */
document.addEventListener('click', e=>{
  const el = e.target && e.target.closest ? e.target.closest('.is-live') : null;
  if(!el || !el.title) return;
  let tip = document.getElementById('live-tip');
  if(!tip){
    tip = document.createElement('div'); tip.id = 'live-tip';
    tip.setAttribute('role','status'); tip.setAttribute('aria-live','polite');
    document.body.appendChild(tip);
  }
  tip.textContent = '● ' + el.title;
  const sm = document.createElement('small');
  sm.textContent = LANG==='en'
    ? 'The green dot marks a figure fetched live from the source (not from the catalog).'
    : 'El punto verde marca un dato consultado en vivo a la fuente (no del catálogo).';
  tip.appendChild(sm);
  const r = el.getBoundingClientRect(), vw = window.innerWidth, vh = window.innerHeight;
  const w = tip.offsetWidth, h = tip.offsetHeight;
  tip.style.left = Math.max(8, Math.min(r.left, vw - w - 8)) + 'px';
  tip.style.top = (r.bottom + 6 + h > vh - 8 ? Math.max(8, r.top - h - 6) : r.bottom + 6) + 'px';
  tip.classList.add('show');
  clearTimeout(tip._t); tip._t = setTimeout(()=>tip.classList.remove('show'), 4000);
});

/* Capitalización EN VIVO. 1º el perfil en vivo (KhipuLive: Yahoo/Finnhub, en
   USD); si no hay, /api/fundamentals (Finnhub en EE.UU., FMP + tipo de cambio
   en el resto) — este solo cuando el catálogo no la trae, como antes. La usan
   la ficha del mapa y el X-Ray. Sin dato → queda el valor del catálogo o "—". */
window.fillLiveMcap = function(el, n){
  if(!el || !n || !n.mkt) return;
  const meta=(window.NODE_META||{})[n.id]||{};
  const viaFundamentals = ()=>{
    if(meta.mktcap_b || !el.isConnected) return;
    DataLayer.fundamentals(n.mkt).then(f=>{
      const b=f&&f.marketCapB; if(!b||!el.isConnected) return;
      el.textContent = window.KhipuLive.fmtUsdB(b);
      el.title = (LANG==='en'?'Live market cap · ':'Capitalización en vivo · ')+(f.marketCapSource||'');
    }).catch(()=>{});
  };
  window.KhipuLive.profile(n.mkt).then(p=>{
    const b = p && p.available && p.market_cap_usd_b;
    if(b && _paintLive(el, window.KhipuLive.fmtUsdB(b), p)) return;
    viaFundamentals();
  }).catch(viaFundamentals);
};

/* Empleados / Mkt Cap / Ingresos EN VIVO dentro de `root` (ficha del mapa,
   X-Ray, Cabina). Busca [data-live="employees|mcap|revenue"] y, para ingresos,
   cambia la etiqueta [data-live-label="revenue"] a "Ingresos (últ. 12 m)" (el catálogo
   dice 2025; el dato vivo son los últimos 12 meses — no mezclar). Sin perfil
   en vivo, todo queda con el catálogo como hoy. data-live-fmt="k" → 48K. */
window.fillLiveMeta = function(root, n){
  if(!root || !n || !n.mkt) return;
  const mc = root.querySelector('[data-live="mcap"]');
  if(mc) window.fillLiveMcap(mc, n);
  // Las celdas se capturan AHORA, antes de la consulta: `root` (#detail, el
  // cajón #xray) sigue en la página aunque ya muestre OTRA empresa (se le
  // cambia el innerHTML). Así, si la respuesta de A llega tarde, sus celdas
  // ya no están conectadas y _paintLive la descarta — nunca pinta los datos
  // de A en la ficha de B.
  const emp = root.querySelector('[data-live="employees"]');
  const rev = root.querySelector('[data-live="revenue"]');
  const lab = root.querySelector('[data-live-label="revenue"]');
  const mg = root.querySelector('[data-live="margin"]'), mgs = root.querySelector('[data-live-sub="margin"]');
  const gr = root.querySelector('[data-live="growth"]'), grs = root.querySelector('[data-live-sub="growth"]'), grl = root.querySelector('[data-live-label="growth"]');
  if(!emp && !rev && !mg && !gr) return;
  window.KhipuLive.profile(n.mkt).then(p=>{
    if(!p || !p.available) return;
    const L = window.KhipuLive;
    if(emp && p.employees) _paintLive(emp, L.fmtEmp(p.employees, emp.dataset.liveFmt==='k'), p);
    if(rev && p.revenue_ttm_usd_b && _paintLive(rev, L.fmtUsdB(p.revenue_ttm_usd_b), p)){
      // "últimos 12 meses" en palabras (no la sigla TTM), igual que el Dossier
      if(lab && lab.isConnected){
        lab.textContent = LANG==='en' ? 'Revenue (last 12 mo)' : 'Ingresos (últ. 12 m)';
        lab.title = LANG==='en'
          ? 'Sales over the last 12 months (the sum of the latest 4 quarters), live. The catalog figure was for year 2025.'
          : 'Ventas de los últimos 12 meses (suma de los 4 trimestres más recientes), en vivo. El dato del catálogo era del año 2025.';
      }
    }
    // margen y crecimiento REALES (2026-10-05: antes era el número curado del catálogo, sin fecha)
    const om = p.operating_margin != null ? +p.operating_margin : null;
    if(mg && om != null && isFinite(om) && _paintLive(mg, (om >= 0 ? '' : '−') + Math.abs(om).toFixed(1) + '%', p)){
      mg.classList.toggle('neg', om < 0);
      if(mgs && mgs.isConnected) mgs.textContent = LANG==='en' ? 'operating · last 12 mo · live' : 'operativo · últ. 12 meses · en vivo';
    }
    const gq = p.revenue_growth_q != null ? +p.revenue_growth_q : null;
    if(gr && gq != null && isFinite(gq)){
      const cat = gr.textContent;
      if(_paintLive(gr, (gq >= 0 ? '+' : '−') + Math.abs(gq).toFixed(0) + (LANG==='en' ? '% sales (last quarter vs a year ago)' : ' % ventas (últ. trimestre vs hace un año)'), p)){
        if(grl && grl.isConnected) grl.textContent = LANG==='en' ? 'Real growth · live' : 'Crecimiento real · en vivo';
        if(grs && grs.isConnected) grs.textContent = (LANG==='en' ? 'Catalog projection: ' : 'Proyección del catálogo: ') + cat;
      }
    }
  }).catch(()=>{});
};

/* CAPITALIZACIÓN EN VIVO DE TODO EL GRAFO (pedido: "que todo esté en vivo").
   /api/market/live_caps trae en lote ~580 cotizadas (Yahoo, caché 15 min en el
   server). Pisa NODE_META[id].mktcap_b (el comparador, la simulación en vivo,
   el portafolio, la terminal, la Cabina y los gráficos lo leen de ahí) y guarda
   el valor del catálogo en mktcap_catalog. mktcap_live = {as_of, source}.
   Emite 'khipu:livecaps'. Sin red → queda el catálogo, como antes. */
window.KhipuLiveCaps = (function(){
  let tries = 0, timer = null, last = null;
  function apply(d){
    const meta = window.NODE_META || {};
    let n = 0, nq = 0;
    Object.keys(d.caps || {}).forEach(id=>{
      const c = d.caps[id]; if(!c) return;
      const hasCap = c.mcap_b != null && isFinite(+c.mcap_b);
      // precio EN USD: `price_usd` (convertido en el server) o `price` solo si ya es USD.
      // `price` de otra moneda NUNCA se pinta con "$".
      const pxUsd = (c.price_usd != null && isFinite(+c.price_usd)) ? +c.price_usd
                  : ((c.price != null && isFinite(+c.price) && (!c.currency || c.currency === 'USD')) ? +c.price : null);
      if(!hasCap && pxUsd == null) return;              // condición relajada: cap O precio
      const m = meta[id] || (meta[id] = {});
      if(hasCap){
        if(m.mktcap_catalog === undefined) m.mktcap_catalog = (m.mktcap_b === undefined ? null : m.mktcap_b);
        const v = +c.mcap_b;
        m.mktcap_b = v >= 100 ? Math.round(v) : Math.round(v*10)/10;
        n++;
      }
      m.mktcap_live = Object.assign({}, m.mktcap_live || {}, {as_of: d.as_of, source: d.source || 'yahoo', price: c.price, price_usd: pxUsd, currency: c.currency});
      // (2026-10-04) también alimenta MKT.quotes cuando NO hay una cotización más
      // fresca (<15 min): la Terminal/Mercado muestran precio aunque el lote en
      // vivo no haya cubierto el ticker. Fuente honesta: Yahoo (lote de 15 min).
      const sym = c.symbol;
      if(sym && pxUsd != null && pxUsd > 0 && window.MKT && MKT.quotes){
        const cur = MKT.quotes[sym];
        // R9 (misión de reparación): el lote de capitalizaciones SOLO rellena tickers sin
        // cotización directa (o con una de live_caps/Marketstack). Nunca pisa una fila de
        // Finnhub/Yahoo aunque sea del cierre de ayer: fuera de la sesión (noches, fines
        // de semana) pisaba todo el catálogo y lo sellaba con la hora del lote ("en vivo
        // · hace 1 min" para un cierre de ayer).
        const direct = !!(cur && quotePx(cur)>0 && cur.src && cur.src!=='marketstack' && cur.via!=='live_caps');
        if(!direct){
          const pct = (c.change_pct != null && isFinite(+c.change_pct)) ? +c.change_pct : null;
          const prev = (pct != null && pct > -100) ? pxUsd/(1+pct/100) : (cur && cur.prev != null ? cur.prev : null);
          // hora REAL del precio (regularMarketTime) si el lote la trae; si no, la del lote
          const asOf = (c.price_ts > 0) ? new Date(c.price_ts*1000).toISOString() : (d.as_of || new Date().toISOString());
          MKT.quotes[sym] = Object.assign({}, cur||{}, {close: pxUsd, live: pxUsd, prev, pct, src:'yahoo', via:'live_caps',
            as_of: asOf, market_state: c.market_state || null, currency: c.currency || 'USD', converted: !!(c.currency && c.currency !== 'USD')});
          nq++;
        }
      }
    });
    last = {n, nq, as_of: d.as_of};
    if(nq){
      if(!MKT.ts) MKT.ts = Date.now();
      try{ _persistQuotes(); }catch(e){}
      try{ if(typeof window._termRefreshPrices === 'function') window._termRefreshPrices(); }catch(e){}
      try{ if(typeof activeTab !== 'undefined' && activeTab === 'market' && typeof renderMarket === 'function') renderMarket(true); }catch(e){}
    }
    try { window.dispatchEvent(new CustomEvent('khipu:livecaps', {detail: last})); } catch(e){}
    return n;
  }
  function load(){
    if(document.hidden) return;
    fetch('/api/market/live_caps').then(r=>r.ok ? r.json() : null).then(d=>{
      if(!d) return;
      if(d.caps && Object.keys(d.caps).length) apply(d);
      if((d.warming || d.refreshing) && tries++ < 6) { clearTimeout(timer); timer = setTimeout(load, 20000); }
    }).catch(()=>{});
  }
  setTimeout(load, 1500);
  setInterval(()=>{ tries = 0; load(); }, 15*60*1000);
  document.addEventListener('visibilitychange', ()=>{ if(!document.hidden && last && last.as_of && Date.now() - Date.parse(last.as_of) > 15*60*1000){ tries = 0; load(); } });
  return {load, apply, status: ()=>last};
})();

/* FUNDAMENTALES EN VIVO DE TODO EL GRAFO (2026-10-05, pedido: "en vivo siempre lo que varía; fijo solo
   lo que no cambia, como la fundación"). /api/market/live_fundamentals (core/live_fundamentals: tandas en
   segundo plano, cada empresa ≥ 1×/día) trae margen operativo, crecimiento del último trimestre, ingresos
   12 m y empleados REALES. Se aplican al catálogo entero → NRS, rankings, comparador, gráficos, Insights y
   simulación usan el dato real. Lo del catálogo queda en *_catalog; cada dato vivo lleva {source, as_of}. */
window.KhipuLiveFund = (function(){
  let last = null, tries = 0, timer = null;
  function apply(d){
    const meta = window.NODE_META || {}, NB = window.NODE_BY_ID || {};
    let n = 0;
    Object.keys(d.fund || {}).forEach(id=>{
      const f = d.fund[id], node = NB[id];
      if(!node || node.id !== id || !f) return;
      const live = {source: f.source || 'yahoo', as_of: f.as_of};
      if(f.operating_margin != null && isFinite(+f.operating_margin)){
        if(node.margin_catalog === undefined) node.margin_catalog = node.margin;
        node.margin = +f.operating_margin / 100;
        node.margin_live = live;
      }
      if(f.revenue_growth_q != null && isFinite(+f.revenue_growth_q)) node.growth_live = Object.assign({pct: +f.revenue_growth_q}, live);
      const m = meta[id] = meta[id] || {};
      if(f.employees){ if(m.employees_catalog === undefined) m.employees_catalog = m.employees; m.employees = +f.employees; m.employees_live = live; }
      if(f.revenue_ttm_usd_b != null && isFinite(+f.revenue_ttm_usd_b)){
        if(m.revenue_catalog === undefined) m.revenue_catalog = m.revenue_2025;
        m.revenue_ttm_usd_b = +f.revenue_ttm_usd_b; m.revenue_live = live;
      }
      n++;
    });
    last = {n: n, at: d.last_run};
    if(n){
      try{ if(window._invalidateNRS) window._invalidateNRS(); }catch(e){}
      try{ if(typeof refreshStyles === 'function') refreshStyles(); }catch(e){}
      try{ window.dispatchEvent(new CustomEvent('khipu:livefund', {detail: last})); }catch(e){}
    }
    return n;
  }
  function load(){
    if(document.hidden) return;
    fetch('/api/market/live_fundamentals').then(r=>r.ok ? r.json() : null).then(d=>{
      if(!d) return;
      const k = apply(d);
      // el servidor llena el grafo por tandas tras cada arranque: se vuelve a pedir hasta tenerlo
      if((!k || (d.n && d.n < 400)) && tries++ < 12){ clearTimeout(timer); timer = setTimeout(load, 5*60*1000); }
    }).catch(()=>{});
  }
  setTimeout(load, 2500);
  setInterval(()=>{ tries = 0; load(); }, 60*60*1000);
  return {load, apply, status: ()=>last};
})();
/* Punto verde "en vivo" para una capitalización pintada desde NODE_META. */
window.liveCapDot = function(meta){
  const l = meta && meta.mktcap_live;
  if(!l && meta && meta.mktcap_verified){
    // privada: valuación VERIFICADA (última ronda cerrada, con fecha y fuente)
    const v = meta.mktcap_verified;
    const tipv = (LANG==='en' ? 'Verified valuation · last closed round ' : 'Valuación verificada · última ronda cerrada ') + (v.as_of||'') + (v.round ? ' · ' + v.round : '');
    return ' <span style="color:#7ecbff;font-size:9px;font-weight:600;vertical-align:middle" title="'+tipv.replace(/"/g,'&quot;')+'">✓ '+esc(v.as_of||'')+'</span>';
  }
  if(!l){
    // valor del CATÁLOGO (curado a mano, puede estar desactualizado): rotularlo
    if(!meta || meta.mktcap_b == null || !isFinite(+meta.mktcap_b)) return '';
    const tipc = LANG==='en' ? 'Catalog figure (curated, may be outdated) — no live data right now' : 'Dato del catálogo (curado, puede estar desactualizado) — sin dato en vivo ahora';
    return ' <span style="color:var(--ink-3);font-size:9px;font-weight:400;vertical-align:middle" title="'+tipc+'">'+(LANG==='en'?'cat.':'cat.')+'</span>';
  }
  const t = l.as_of ? new Date(l.as_of).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) : '';
  const tip = (LANG==='en' ? 'Live · ' : 'En vivo · ') + (l.source||'yahoo') + (t ? ' · ' + t : '');
  return ' <b style="color:#2BE38B;font-size:9px;vertical-align:middle" title="'+tip+'">●</b>';
};

/* ── 📡 Lo último en el grafo (Phase 1 · M6: feed GLOBAL) ──────────────────
   La Historia de arriba es POR EMPRESA; esto es el grafo ENTERO: noticias,
   relaciones nuevas o terminadas, tesis y acciones, lo más nuevo primero (por
   cuándo lo supimos). Vive en el panel derecho del mapa cuando no hay empresa
   elegida — donde Fabrizio ya mira. Sin ontología (sin DATABASE_URL) se oculta. */
const V8feed = {
  _t:0,
  load(force){
    const box=$('feed-box'), el=$('feed-list'); if(!box||!el) return;
    const lang=(LANG==='en')?'en':'es';
    if(!force && Date.now()-this._t<60000) return;
    // 2026-10-06: al arrancar llegaban DOS cargas forzadas casi juntas (1,5 s + applyLang) → una sola
    if(force && this._lang===lang && Date.now()-this._t<5000) return;
    this._t=Date.now(); this._lang=lang;
    fetch(`${BASE}/api/ontology/feed?limit=8&lang=${lang}`)
      .then(r=>r.ok?r.json():null).then(d=>{
        if(!d||!Array.isArray(d.feed)){ box.style.display='none'; return; }
        box.style.display='block';
        $('feed-h').textContent='📡 '+t('feed_h');
        if(!d.feed.length){
          /* nada nuevo en la ventana de frescura: se dice claro, no se reciclan noticias viejas */
          const la=Date.parse(d.last_at||''); const dd=isNaN(la)?null:Math.round((Date.now()-la)/86400000);
          el.innerHTML=`<div style="padding:6px 0;font-size:12px;color:var(--ink-3);line-height:1.45">${esc(t('feed_quiet'))}${dd!=null?' '+esc(lang==='en'?`Last entry ${dd} days ago.`:`Lo último entró hace ${dd} días.`):''}</div>`;
          return;
        }
        const ico={NewsItem:'📰',LinkCreated:'🔗',LinkRemoved:'✂',ActionExecuted:'✎',ObjectUpdated:'↻',ObjectCreated:'＋'};
        const ago=iso=>{ const x=Date.parse(iso||''); if(isNaN(x)) return '';
          const m=Math.max(0,(Date.now()-x)/60000);
          const v=m<1?t('feed_now'):m<60?Math.round(m)+' min':m<1440?Math.round(m/60)+' h':Math.round(m/1440)+' d';
          return m<1?v:(lang==='en'?v+' '+t('feed_ago'):t('feed_ago')+' '+v); };
        el.innerHTML=d.feed.map(e=>{
          const sub=e.subject||null;
          const onMap=sub&&NODE_BY_ID[sub.id];
          const subj=sub?(onMap
            ? `<span onclick="jumpTo('${esc(sub.id)}')" style="color:var(--ink);font-weight:600;cursor:pointer;border-bottom:1px dotted var(--ink-3)">${esc(sub.label)}</span>`
            : `<span style="color:var(--ink-2);font-weight:600">${esc(sub.label)}</span>`):'';
          const src=e.source&&e.source.url?e.source:null;
          const host=src?(src.publisher||src.url).replace(/^https?:\/\//,'').split('/')[0]:'';
          return `<div style="padding:6px 0;border-bottom:1px solid var(--line);line-height:1.4;font-size:12px">
            <div style="display:flex;gap:6px;align-items:baseline">
              <span style="flex-shrink:0">${ico[e.event_type]||'•'}</span>
              <span style="flex:1;color:var(--ink-2)">${subj}${subj?' · ':''}${esc(e.title||'')}</span>
              <span style="font-size:10px;color:var(--ink-3);white-space:nowrap">${esc(ago(e.recorded_at))}</span></div>
            ${src?`<a href="${safeUrl(src.url)}" target="_blank" rel="noopener noreferrer" style="font-size:10.5px;color:var(--ink-3);text-decoration:none;margin-left:20px">${esc(host)} ↗</a>`:''}
          </div>`;}).join('');
      }).catch(()=>{ box.style.display='none'; });
  },
};
window.V8feed = V8feed;
setTimeout(()=>V8feed.load(true), 1500);

/* sentimiento por palabras clave */
function sentiment(headline){
  const h=(headline||'').toLowerCase();
  const pos=/(beat|record|surge|soar|jump|gain|rise|grow|strong|win|up |raise|outperform|upgrade|profit|bullish|rally|高|récord|sube|gana|crece)/;
  const neg=/(miss|fall|drop|plunge|cut|loss|weak|down |decline|sue|fine|ban|probe|warn|downgrade|bearish|slump|baja|cae|pierde|riesgo|sanción)/;
  if(pos.test(h) && !neg.test(h)) return {cls:'pos',icon:'🟢 +'};
  if(neg.test(h) && !pos.test(h)) return {cls:'neg',icon:'🔴 −'};
  return {cls:'neu',icon:'⚪'};
}
function extractJSON(txt){
  if(!txt) return null;
  let s=txt.trim().replace(/^```[a-z]*\s*/i,'').replace(/```$/,'').trim();
  const a=s.indexOf('{'), b=s.lastIndexOf('}'); if(a<0||b<0) return null;
  try{ return JSON.parse(s.slice(a,b+1)); }catch(e){ return null; }
}

/* ════════════════ §H · ALERTAS DE PRECIO (Feature 8) ════════════════ */
const Alerts = {
  list(){ return JSON.parse(localStorage.getItem('eco_alerts')||'[]'); },
  save(a){ localStorage.setItem('eco_alerts', JSON.stringify(a)); },
  add(ticker,type,price){ const a=this.list(); a.push({ticker,type,price:+price,triggered:false,createdAt:Date.now()}); this.save(a); },
  remove(i){ const a=this.list(); a.splice(i,1); this.save(a); },
  check(ticker, price){
    const a=this.list(); let changed=false;
    a.forEach(al=>{ if(al.ticker!==ticker || al.triggered) return;
      const hit=(al.type==='above'&&price>=al.price)||(al.type==='below'&&price<=al.price);
      if(hit){ al.triggered=true; changed=true; this.fire(al, price); } });
    if(changed){ this.save(a); if(selected && NODE_BY_ID[selected] && NODE_BY_ID[selected].mkt===ticker) this.renderInDetail(selected, ticker); }
  },
  fire(al, price){
    const n=nodeByTicker[al.ticker]; const label=n?n.label:al.ticker;
    const dir=al.type==='above'?(LANG==='en'?'rose above':'superó'):(LANG==='en'?'fell below':'bajó de');
    const txt=tr('al_banner',{t:label, dir, p:al.price, cur:fmtN(price)});
    const b=$('alert-banner'); $('alert-banner-text').innerHTML=txt; b.classList.add('show');
    $('alert-banner-go').onclick=()=>{ b.classList.remove('show'); if(n){ switchTab('map'); jumpTo(n.id); } };
    $('alert-banner-dismiss').onclick=()=>b.classList.remove('show');
    setTimeout(()=>b.classList.remove('show'), 12000);
    if(prefs().notif && 'Notification' in window && Notification.permission==='granted'){
      try{ new Notification('🔔 '+label, {body:txt.replace(/<[^>]+>/g,'')}); }catch(e){}
    }
  },
  renderInDetail(id, tk){
    const el=$('v8-alerts'); if(!el) return;
    const all=this.list();
    const mine=all.map((a,i)=>({a,i})).filter(x=>x.a.ticker===tk);
    const rows=mine.map(({a,i})=>`<div class="alert-row">
      <span class="ar-txt"><b>${esc(tk)}</b> ${a.type==='above'?t('al_above'):t('al_below')} <b>$${fmtN(a.price)}</b></span>
      <span class="ar-state ${a.triggered?'fired':'active'}">${a.triggered?t('al_fired'):t('al_active')}</span>
      <button class="ar-del" data-i="${i}">✕</button></div>`).join('');
    el.innerHTML=`<div class="alert-add">
        <select id="v8-al-type"><option value="above">${t('al_above')}</option><option value="below">${t('al_below')}</option></select>
        <input id="v8-al-price" type="number" step="any" placeholder="$">
        <button class="key-btn" id="v8-al-add">${t('al_add')}</button>
      </div>${rows}`;
    $('v8-al-add').onclick=()=>{ const pr=parseFloat($('v8-al-price').value); if(!(pr>0)) return;
      this.add(tk, $('v8-al-type').value, pr); this.renderInDetail(id,tk); };
    el.querySelectorAll('.ar-del').forEach(btn=>btn.onclick=()=>{ this.remove(+btn.dataset.i); this.renderInDetail(id,tk); });
  }
};

/* ── Alertas de la Ontología (Fase 4) — persistentes en Postgres, creadas por
   el lenguaje KHIPU ("ALERT NVDA PX > 150", "ALERT REGION taiwan NEWS").
   Viven en el servidor, sobreviven a cambiar de dispositivo, y soportan NRS +
   noticias por región. Se limitan a notificar UNA VEZ por sesión de navegador
   por alerta (evita spam si la condición sigue vigente en cada sondeo). ──── */
const OntologyAlerts = {
  _notified: new Set(),
  async check() {
    if (!(prefs().notif)) return;
    let actor; try { actor = localStorage.getItem('khipu_actor'); } catch (e) { actor = null; }
    if (!actor) return; // sin identidad aún no ha creado ninguna alerta
    try {
      const base = (typeof BASE !== 'undefined') ? BASE : '';
      const r = await fetch(`${base}/api/ontology/alerts/check?owner=${encodeURIComponent(actor)}`);
      if (!r.ok) return; // 503 = ontología no configurada; silencioso, no es un error del usuario
      const d = await r.json();
      (d.fired || []).forEach(f => {
        if (this._notified.has(f.id)) return;
        this._notified.add(f.id);
        this._notify(f);
      });
    } catch (e) {}
  },
  _notify(f) {
    const msg = f.detail || JSON.stringify(f.rule);
    if (typeof toast === 'function') toast('🔔 ' + msg);
    if ('Notification' in window && Notification.permission === 'granted') {
      try { new Notification('Khipus Finance Intelligence · Alerta', { body: msg, icon: '/icon.svg' }); } catch (e) {}
    }
  },
  start() { setTimeout(() => this.check(), 8000); setInterval(() => this.check(), 120000); },
};
window.OntologyAlerts = OntologyAlerts;
if (document.readyState === 'complete' || document.readyState === 'interactive') OntologyAlerts.start();
else window.addEventListener('DOMContentLoaded', () => OntologyAlerts.start());

/* ════════════════ §I · CORONA DE EARNINGS PRÓXIMOS (Feature 3) ════════════════ */
const V8earnings = {
  applyCorona(id){
    try{
      const g=nodeSel.filter(d=>d.id===id);
      if(g.empty() || !g.select('.earnings-corona').empty()) return;
      g.append('circle').attr('class','earnings-corona')
        .attr('r', d=>computeNodeRadius(d.id)+11).lower(); // detrás del core
    }catch(e){}
  }
};

/* ════════════════ §J · ANÁLISIS DE IMPACTO IA TRAS STRESS-TEST (Feature 9) ════════════════ */
const _activateStress = activateStress;
activateStress = function(id){
  const p=_activateStress(id);
  try{
    const bar=$('stress-banner'); if(bar && !$('stress-ai-btn') && Keys.has('claude')){
      const btn=document.createElement('button'); btn.id='stress-ai-btn'; btn.textContent=t('stress_ai');
      btn.onclick=()=>StressAI.run(stressId); bar.appendChild(btn);   /* la empresa simulada AHORA (el botón se reusa) */
    }
  }catch(e){}
  return p;
};
const StressAI = {
  async run(id){
    const d=NODE_BY_ID[id]; if(!d) return;
    /* Sin el resultado del motor del servidor (todavía calculando, sin conexión, 503/429…) NO se llama a la IA:
       antes el prompt decía "afectadas (0): ninguna" y la IA escribía un análisis tranquilizador inventado. */
    const r=stressRes;
    if(!(r && r.ok && stressId===id)){
      const msg = !r ? (LANG==='en'?'The server engine is still computing this collapse; try again in a moment.'
                                   :'El motor del servidor todavía está calculando este colapso; prueba en un momento.')
                     : (LANG==='en'?'There is no engine result to analyze: ':'No hay resultado del motor para analizar: ')+(r.error||'');
      showAIFloat(`<div class="ai-card-body"><div class="ai-err">${esc(msg)}</div></div>`);
      return;
    }
    const btn=$('stress-ai-btn'); if(btn){ btn.disabled=true; btn.textContent=t('stress_ai_loading'); }
    const vic=(r.victims||[]).filter(v=>v.pct>=1).sort((a,b)=>b.pct-a.pct);
    const aff=vic.slice(0,40).map(v=>{ const n=NODE_BY_ID[v.id]; return (n?(n.label+' ('+catLabel(n.cat)+')'):v.id)+' '+Math.round(v.pct)+'%'; }).join(', ');
    const posAff=vic.filter(v=>MKT.pos[v.id]).map(v=>(NODE_BY_ID[v.id]?NODE_BY_ID[v.id].label:v.id)+' '+Math.round(v.pct)+'%');
    const prompt=`El usuario simuló el colapso de ${d.label} en la cadena de valor global de semiconductores e IA.
Empresas afectadas aguas abajo según el motor de impacto del servidor (${vic.length}; % = parte del golpe que recibe cada una): ${aff||'ninguna'}.
${posAff.length?('El inversor tiene posiciones en: '+posAff.join(', ')+'.'):'El inversor no tiene posiciones afectadas.'}
¿Qué significaría este colapso para: (1) la cadena de producción de chips (impacto en meses), (2) las empresas de IA más perjudicadas, (3) el portafolio del inversor? Responde en ${LANG==='en'?'English':'español'}, máximo 200 palabras, lenguaje de inversor, no técnico.`;
    try{
      const txt=await DataLayer.aiComplete(LANG==='en'?'You are a supply-chain risk analyst for investors.':'Eres un analista de riesgo de cadena de suministro para inversores.', prompt, 600);
      showAIFloat(`<div class="ai-card-head">✨ ${d.label} — ${LANG==='en'?'impact':'impacto'}</div><div class="ai-card-body" style="white-space:pre-wrap;font-size:13px;line-height:1.55;color:var(--ink-2)">${esc(txt.trim())}<div class="ai-disclaim">${t('ai_disclaim')}</div></div>`);
    }catch(e){ showAIFloat(`<div class="ai-card-body"><div class="ai-err">${esc(String(e.message||e))}</div></div>`); }
    finally{ if($('stress-ai-btn')){ $('stress-ai-btn').disabled=false; $('stress-ai-btn').textContent=t('stress_ai'); } }
  }
};
function showAIFloat(html){
  let ov=$('ai-float'); if(!ov){ ov=document.createElement('div'); ov.id='ai-float';
    ov.style.cssText='position:fixed;inset:0;z-index:130;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.42)';
    ov.onclick=e=>{ if(e.target===ov) ov.remove(); };
    document.body.appendChild(ov); }
  ov.innerHTML=`<div class="ai-card" style="max-width:440px;width:92%;max-height:80vh;overflow-y:auto;background:var(--surface)">
    <div style="display:flex;justify-content:flex-end;padding:6px 8px 0"><button class="icon-btn" onclick="document.getElementById('ai-float').remove()">✕</button></div>
    ${html}</div>`;
}

/* ════════════════ §K · BARRA DATA-HEALTH (Feature 12) ════════════════ */
const DataHealth = {
  render(){
    const el=$('data-health'); if(!el) return;
    const items=[];
    const lm = (typeof MKT!=='undefined' && MKT.liveMeta) || null;
    const srcN = k => (lm && lm.sources && lm.sources[k]) || 0;
    // Finnhub: LIVE (WebSocket) · lotes (precios llegaron por /api/quotes/live) · cuota (429) · caché
    const fh = !Keys.has('finnhub')?['off',t('dh_off')] : LivePrices.connected?['ok',t('dh_live')]
             : (lm && lm.finnhub_quota)?['warn',t('dh_quota')] : srcN('finnhub')?['ok',t('dh_batch')] : ['warn',t('dh_cache')];
    items.push(['dh_finnhub',fh]);
    // Yahoo no necesita clave: cubre TODAS las bolsas y es el respaldo de EE.UU.
    items.push(['dh_yahoo', srcN('yahoo')?['ok',t('dh_batch')] : (lm && lm.done)?['warn',t('dh_cache')] : ['warn',t('dh_ready')]]);
    // FMP: solo "clave presente" — la prueba REAL vive en 🩺 (/api/diagnostics → fmp)
    items.push(['dh_fmp', !Keys.has('fmp')?['off',t('dh_off')]:['ok',t('dh_key')]]);
    items.push(['dh_ai', !Keys.has('claude')?['off',t('dh_off')]:['ok',t('dh_ready')]]);
    items.push(['dh_mkt', !Keys.has('marketstack')?['off',t('dh_off')] : ['ok',t('dh_key')]]);
    items.push(['dh_offline', navigator.onLine?['ok',t('dh_no')]:['err',t('dh_yes')]]);
    el.innerHTML=items.map(([k,[cls,txt]])=>`<span class="dh-item"><span class="dh-dot ${cls}"></span>${t(k)}: ${txt}</span>`).join('');
  }
};

/* ════════════════ §L · PWA + OFFLINE (Feature 10) ════════════════ */
function setupPWA(){
  // manifest (solo sirve sobre http; en file:// el 404 es inofensivo)
  if(!document.querySelector('link[rel="manifest"]')){
    const l=document.createElement('link'); l.rel='manifest'; l.href=(BASE||'')+'/manifest.webmanifest'; document.head.appendChild(l);
  }
  if('serviceWorker' in navigator && /^https?:$/.test(location.protocol)){
    navigator.serviceWorker.register('/sw.js').catch(()=>{});
    // Auto-actualización: cuando un SW nuevo toma control (versión nueva
    // desplegada), recargamos UNA vez para que el usuario vea lo último sin
    // tener que abrir incógnito ni Ctrl+Shift+R. Guardas anti-bucle:
    // solo si ya había un controller (no en la primera instalación).
    // Aviso de versión nueva — clicable, nunca interrumpe. Lo disparan:
    // (a) el Service Worker al activarse una versión nueva, y
    // (b) el chequeo periódico de live.js (para navegadores que cachean de
    //     más y NUNCA disparan el SW — causa real de "sigo viendo lo viejo").
    // Actualización SIEMPRE INVISIBLE (pedido explícito: "no quiero eso de
    // nuevas versiones — cuando lo abres ya deberías abrir la última"):
    // jamás un aviso, jamás recargar en la cara del usuario. Cuando se detecta
    // versión nueva: recarga silenciosa si la página es recién abierta (<10s)
    // o si la pestaña está oculta; si está en pleno uso, se recarga en el
    // momento en que el usuario minimiza o cambia de pestaña. El nombre
    // _showUpdatePill se conserva por compatibilidad (lo llama live.js).
    window._showUpdatePill = function () {
      if (window._updPending) return;
      const last = +(sessionStorage.getItem('kh_upd_ts') || 0);
      if (Date.now() - last < 60000) return;   // anti-bucle: máx 1/min
      window._updPending = true;
      const doReload = () => {
        sessionStorage.setItem('kh_upd_ts', String(Date.now()));
        const done = () => location.reload();
        try {
          Promise.all([
            window.caches ? caches.keys().then(ks => Promise.all(ks.map(k => caches.delete(k)))) : null,
            navigator.serviceWorker ? navigator.serviceWorker.getRegistrations().then(rs => Promise.all(rs.map(r => r.update()))) : null,
          ]).then(done, done);
          setTimeout(done, 1500);   // pase lo que pase, recarga
        } catch (e) { done(); }
      };
      if (performance.now() < 10000 || document.hidden) { doReload(); return; }
      document.addEventListener('visibilitychange', function onHide() {
        if (document.hidden) { document.removeEventListener('visibilitychange', onHide); doReload(); }
      });
    };

    // Actualización de versión SIN molestar (feedback real: "se reinicia a
    // cada rato" — el auto-reload interrumpía al usuario en cada deploy):
    // - página recién abierta (<10s): recarga silenciosa (no interrumpe nada)
    // - en medio del uso: un avisito clicable; el usuario decide cuándo
    // - anti-bucle: máx. 1 recarga automática por minuto (sessionStorage)
    const hadController = !!navigator.serviceWorker.controller;
    let _swHandled = false;
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (!hadController || _swHandled) return;
      _swHandled = true;
      const last = +(sessionStorage.getItem('kh_upd_ts') || 0);
      if (performance.now() < 10000 && Date.now() - last > 60000) {
        sessionStorage.setItem('kh_upd_ts', String(Date.now()));
        location.reload();
        return;
      }
      window._showUpdatePill();
    });
  }
  const upd=()=>{ const on=navigator.onLine; $('offline-badge').classList.toggle('show',!on); DataHealth.render(); };
  window.addEventListener('online',upd); window.addEventListener('offline',upd); upd();
}

/* ---------- toast minimal ---------- */
let toastT=null;
function toast(msg){
  let el=$('v8-toast'); if(!el){ el=document.createElement('div'); el.id='v8-toast';
    el.style.cssText='position:fixed;bottom:22px;left:50%;transform:translateX(-50%);z-index:140;background:var(--ink);color:var(--bg);font-size:12.5px;font-weight:500;padding:9px 16px;border-radius:20px;box-shadow:var(--shadow);opacity:0;transition:opacity .2s;pointer-events:none';
    document.body.appendChild(el); }
  el.textContent=msg; el.style.opacity='1'; clearTimeout(toastT); toastT=setTimeout(()=>el.style.opacity='0',2200);
}

/* ════════════════ §M · i18n estático v8 + wrap de applyLang ════════════════ */
function applyLangV8(){
  if(window.V8feed) V8feed.load(true);
  const ob=$('offline-badge'); if(ob){ const sp=ob.querySelector('[data-i18n="offline"]'); if(sp) sp.textContent=t('offline'); }
  const ex=$('mk-export'); if(ex){ const sp=ex.querySelector('[data-i18n="mk_export"]'); if(sp) sp.textContent=t('mk_export'); }
  if($('settings-panel').classList.contains('show')) Settings.render();
  DataHealth.render();
}
/* 🩺 Sistema abierto al cambiar ES/EN: se re-rotula y re-pinta la pestaña actual en el idioma nuevo (antes quedaba
   en el viejo hasta cerrarlo). Va aparte de applyLangV8 para que un fallo allí no lo salte. */
function _sistemaRelabel(){
  const sp=$('sistema-panel');
  if(sp && sp.classList.contains('show')) _switchSistemaTab(_sistemaTab);
}
const _applyLang = applyLang;
applyLang = function(){ _applyLang(); try{ applyLangV8(); }catch(e){} try{ _sistemaRelabel(); }catch(e){} };

/* ════════════════ INIT v8 ════════════════ */
/* Hooks públicos (depuración / power-users): V8.Alerts, V8.LivePrices, V8.Settings… */
V8.Alerts=Alerts; V8.LivePrices=LivePrices; V8.Settings=Settings; V8.DataHealth=DataHealth;
V8.Keys=Keys; V8.health=health; V8.prefs=prefs;
(async function initV8(){
  try{ await DataLayer.health(); }catch(e){}
  setupPWA();
  DataHealth.render();
  applyLangV8();
  // arranca precios en vivo (si hay clave + pref activa)
  LivePrices.start();
  // reevalúa alertas con lo que haya cacheado al cargar
  Object.entries(MKT.quotes||{}).forEach(([tk,q])=>{ if(q&&q.close!=null) Alerts.check(tk,q.close); });
  console.log('%cv8 listo','color:#9B4FE8;font-weight:700','· servido por Railway',
    '· salud:', {finnhub:Keys.has('finnhub'),fmp:Keys.has('fmp'),claude:Keys.has('claude'),marketstack:Keys.has('marketstack')});
})();

})();

/* ═══════════════════════════════════════════════════════════════════════════
   v8.1 · CAPA VISUAL — boot splash, contadores animados, grafo vivo (glow+flow),
   mini-gráfico de flujo en la ficha. No toca lógica; solo decora.
   ═══════════════════════════════════════════════════════════════════════════ */
(function(){
'use strict';
const $=id=>document.getElementById(id);

/* ---- Boot splash: secuencia de log y fade-out ---- */
(function boot(){
  const el=$('boot'); if(!el) return;
  const log=$('boot-log');
  const nodeCount = (typeof NODES !== 'undefined') ? NODES.length : '…';
  const linkCount = (typeof LINKS !== 'undefined') ? LINKS.length : '…';
  const lines=[`› grafo · ${nodeCount} nodos · ${linkCount} conexiones`,
    '› cargando capa de mercado en vivo…','› motor de análisis IA listo','› ✓ terminal operativo'];
  const footerEl = document.getElementById('footer-nodecount');
  if (footerEl) {
    // versión visible: clave para diagnosticar "sigo viendo lo viejo"
    const vm2 = (document.querySelector('script[src*="?v="]')?.src.match(/[?&]v=(\d+)/) || [])[1];
    footerEl.textContent = `Khipus Finance Intelligence · ${nodeCount} nodos · NRS · Khipu AI` + (vm2 ? ` · v${vm2}` : '');
    window._appVersion = vm2 || null;
  }
  let i=0; const iv=setInterval(()=>{ i++; if(log&&lines[i]) log.textContent=lines[i]; if(i>=lines.length-1) clearInterval(iv); }, 300);

  // Fade del splash de arranque — COORDINADO con la Cabina para que NO se vea el
  // mapa pelado en medio (pedido de Fabrizio: "se queda en el panel principal
  // antes de pasar a Khipu y se ve feo"). Idempotente.
  const fadeBoot = () => {
    if (el && !el.classList.contains('gone')) {
      el.classList.add('gone');
      setTimeout(() => { try { el.remove(); } catch (e) {} }, 700);
    }
  };

  // KHIPUS OS (2026-10-06): la app SIEMPRE arranca en Khipus OS (la Cabina evolucionada),
  // en cada carga — antes era una sola vez por sesión y al recargar se veía el mapa viejo.
  // Única excepción: el usuario eligió "Vista clásica" en esta sesión (sessionStorage
  // kh_os_classic='1', lo borra el propio OS al volver a abrirse). Si algo falla, el mapa
  // aparece con el fade normal (fallback de ~9 s).
  try {
    let classic = false;
    try { classic = sessionStorage.getItem('kh_os_classic') === '1'; } catch (e) {}
    if (classic) {
      setTimeout(fadeBoot, 1350);   // eligió la vista clásica en esta sesión → mapa normal
    } else {
      let tries = 0;
      const tryLand = () => {
        tries++;
        if (window.BixbyCockpit && typeof window.BixbyCockpit.open === 'function'
            && typeof NODES !== 'undefined' && NODES.length) {
          try { sessionStorage.setItem('kh_bixby_landed', '1'); } catch (e) {}   // compat: ya no decide nada
          try { window.BixbyCockpit.open(); } catch (e) {}
          // la Cabina (z-index 7000) ya tapa el mapa → RECIÉN AHÍ quitamos el
          // splash. Sin flash del mapa. Un respiro para su transición de entrada.
          setTimeout(fadeBoot, 450);
          return;
        }
        if (tries < 90) setTimeout(tryLand, 100);   // poll rápido, hasta ~9s
        // fallback: mostrar el mapa si la Cabina nunca cargó — y avisarle al mapa que deje de
        // esperarla (_mapBootWaiting) para que se ordene enseguida en vez de quedar en blanco
        else { window.__khOsGaveUp = true; fadeBoot(); }
      };
      // 2026-10-06: con el mapa ya liberado (no se calcula tapado), la espera fija de 850 ms era lo que más
      // demoraba la entrada al OS; el poll de 100 ms entra apenas cockpit.js y los nodos están listos
      setTimeout(tryLand, 60);
    }
  } catch (e) { window.__khOsGaveUp = true; setTimeout(fadeBoot, 1350); }
})();

/* ---- Contadores animados ---- */
function countUp(el, dur){
  if(!el) return; const target=parseFloat((el.textContent||'').replace(/[^\d.\-]/g,'')); if(isNaN(target)) return;
  const suffix=(el.textContent.match(/[%]+$/)||[''])[0]; const dec=(el.textContent.split('.')[1]||'').replace(/[^\d]/g,'').length;
  const t0=performance.now();
  function step(now){ const p=Math.min(1,(now-t0)/dur); const e=1-Math.pow(1-p,3);
    el.textContent=(target*e).toFixed(dec)+suffix; if(p<1) requestAnimationFrame(step); else el.textContent=target.toFixed(dec)+suffix; }
  requestAnimationFrame(step);
}
function animateMetrics(){ ['m-companies','m-links','m-stages','m-preipo'].forEach((id,i)=>{ const el=$(id);
  if(el && /^\d/.test(el.textContent)) setTimeout(()=>countUp(el,900), 200+i*70); }); }
setTimeout(animateMetrics, 1450);
/* re-anima las stats de Análisis al abrir la pestaña */
if(typeof renderAnalysis==='function'){ const _ra=renderAnalysis; renderAnalysis=function(){ _ra.apply(this,arguments);
  ['an-nodes','an-links','an-density','an-preipo','an-risk'].forEach((id,i)=>setTimeout(()=>countUp($(id),700),i*60)); }; }

/* ---- Grafo vivo: glow en nodo focal + flujo en enlaces vecinos ---- */
function applyGlow(){
  try{
    const lock = (typeof stressId!=='undefined'&&stressId) || (typeof pathActive!=='undefined'&&pathActive);
    const focus = lock ? null : ((typeof selected!=='undefined'&&selected) || (typeof hovered!=='undefined'&&hovered) || null);
    nodeSel.classed('node-glow', d=> focus ? d.id===focus : false);
    linkSel.classed('flowing', l=> focus ? (lid(l.source)===focus||lid(l.target)===focus) : false);
  }catch(e){}
}
if(typeof refreshStyles==='function'){ const _rs=refreshStyles; refreshStyles=function(){ _rs.apply(this,arguments); applyGlow(); }; }

/* ---- Mini-gráfico de flujo in/out en la ficha ---- */
let _deg=null;
function degrees(){ if(_deg) return _deg; _deg={in:{},out:{}}; LINKS.forEach(l=>{ const s=lid(l.source),t=lid(l.target);
  _deg.out[s]=(_deg.out[s]||0)+1; _deg.in[t]=(_deg.in[t]||0)+1; }); return _deg; }
function vizDetail(id){
  try{
    const d=NODE_BY_ID[id]; if(!d) return; const deg=degrees(); const ins=deg.in[id]||0, outs=deg.out[id]||0, tot=ins+outs;
    if(!tot) return;
    const badges=document.querySelector('#detail .d-badges'); if(!badges || document.getElementById('flow-viz')) return;
    const html=`<div class="flow-viz" id="flow-viz" title="${LANG==='en'?'inbound vs outbound links':'enlaces de entrada vs salida'}">
      <span style="color:var(--blue)">↑${ins}</span>
      <div class="flow-bar"><span class="fin" style="width:0"></span><span class="fout" style="width:0"></span></div>
      <span style="color:var(--up)">↓${outs}</span></div>`;
    badges.insertAdjacentHTML('afterend', html);
    requestAnimationFrame(()=>{ const fv=document.getElementById('flow-viz'); if(!fv) return;
      fv.querySelector('.fin').style.width=(ins/tot*100)+'%'; fv.querySelector('.fout').style.width=(outs/tot*100)+'%'; });
  }catch(e){}
}
if(typeof renderDetail==='function'){ const _rd=renderDetail; renderDetail=function(id){ _rd.apply(this,arguments); vizDetail(id); }; }

})();
// ═══════════════════════════════════════════════════════════════
// Fin capa v8 / v8.1
// ═══════════════════════════════════════════════════════════════
