/* engine/genui.js — RESPUESTAS VISUALES del chat (kblocks/1). Contrato, API (window.KhipuGenUI) y reglas:
   docs/CHAT_UI_GENERATIVA.md §7. Dibuja bloques; NUNCA calcula cifras (cada número trae src + as_of; sin dato «—»
   con su motivo). DOM seguro (innerHTML solo con KhipuChat.md()), 17 tipos cerrados, acciones solo abrir/sugerir
   (ningún botón de dinero), movimiento solo transform/opacity y «reducir movimiento» lo apaga, tokens --os-*,
   bilingüe (S.es/S.en). genui_charts.js y genui_shapes.js se cargan PEREZOSOS desde aquí (loadExtras). */
(function (root) {
  'use strict';
  var W = root;
  var V = 'kblocks/1', FLAG = 'kh_genui';
  var TYPES = ['text', 'metric.tiles', 'chart.line', 'chart.bar', 'chart.candles', 'ranking', 'table', 'company.card',
    'graph.mini', 'impact.cascade', 'timeline', 'geo.mini', 'callout', 'image', 'comparison', 'actions', 'sources'];
  var REG = {};
  var MAX_BLOCKS = 14;
  var CHARTY = { 'chart.line': 1, 'chart.bar': 1, 'chart.candles': 1, 'ranking': 1, 'comparison': 1, 'impact.cascade': 1, 'graph.mini': 1, 'geo.mini': 1 };
  var BARE = { text: 1, actions: 1, sources: 1 };
  var ACTION_KINDS = { open_window: 1, open_dossier: 1, open_xray: 1, open_map: 1, open_world: 1, open_research: 1,
    open_committee: 1, prefill_chat: 1, set_range: 1, set_view: 1, pin: 1 };
  var WINDOWS = { glance: 1, supplychain: 1, conviction: 1, agents: 1, xray: 1, compare: 1, canvas: 1, sim: 1, geo: 1, genui: 1 };
  var IMG_RX = /^\/(static\/genui\/[a-z0-9_-]{1,60}\.(svg|png|webp)|api\/genui\/img\/[a-f0-9]{16,64})$/;
  var ID_RX = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$/;   // ids del catálogo (p. ej. 'Nvidia'); el esquema pide minúsculas: ver informe F2
  var EXPLAIN_RX = /^[a-z][a-z0-9_.-]{0,40}$/;

  function lang() {
    try { return (W.LANG || (W.localStorage && W.localStorage.getItem('eco_lang')) || 'es') === 'en' ? 'en' : 'es'; }
    catch (e) { return 'es'; }
  }
  // textos PROPIOS (bilingües); los del servidor llegan como I18n {es,en}
  var S = {
    es: { pin: 'Fijar como ventana', pinned: 'Fijado como ventana', more: 'Más opciones', table: 'Ver como tabla', chart: 'Ver como gráfico',
      where: '¿De dónde sale?', ask: 'Preguntar sobre esto', csv: 'Descargar CSV', refresh: 'Actualizar', retry: 'Reintentar',
      tool: 'Herramienta', call: 'Llamada', fact: 'Dato', args: 'Consulta', asof: 'Hora del dato', gen: 'Generación', gv: 'Versión del grafo',
      why: 'Ver la decisión en el registro', type: 'Bloque', nodata: 'sin dato en vivo', live: 'en vivo', staleOf: 'datos de ', loading: 'Cargando…',
      err: 'No se pudo cargar este bloque.', soon: 'Cambiar esto todavía no está disponible.', ready: 'Respuesta lista', answering: 'Khipu está respondiendo…',
      opinion: 'opinión de Khipu', pros: 'Fortalezas', cons: 'Riesgos', sources: 'Fuentes', since: 'desde que se rastrea', seeAll: 'Ver todo',
      less: 'Ver menos', company: 'Empresa', value: 'Valor', metric: 'Métrica', date: 'Fecha', source: 'Fuente', title: 'Título', change: 'Cambio',
      hop: 'Salto', companies: 'empresas', suppliers: 'Proveedores', customers: 'Clientes', peers: 'Parecidas', dossier: 'Dossier', xray: 'X-Ray',
      unknown: 'Este bloque necesita una versión más nueva de Khipus. En texto:', about: 'Sobre ', item: 'Tipo', text: 'Texto', aboutBlock: 'Bloque',
      privVal: 'Valuación privada verificada', structure: 'Estructura', price: 'Precio', mcap: 'Capitalización', nrs: 'NRS', chg: 'Cambio hoy',
      marketClosed: 'mercado cerrado', open: 'Abrir', ext: 'abre otra pestaña', chartN: ['gráfico', 'gráficos'], tableN: ['tabla', 'tablas'],
      cardN: ['ficha', 'fichas'], figN: ['grupo de cifras', 'grupos de cifras'], otherN: ['bloque', 'bloques'], noUrl: 'sin enlace',
      ago: 'hace ', and: ' y ' },
    en: { pin: 'Pin as a window', pinned: 'Pinned as a window', more: 'More options', table: 'View as table', chart: 'View as chart',
      where: 'Where is this from?', ask: 'Ask about this', csv: 'Download CSV', refresh: 'Refresh', retry: 'Retry',
      tool: 'Tool', call: 'Call', fact: 'Fact', args: 'Query', asof: 'Data time', gen: 'Generation', gv: 'Graph version',
      why: 'See the decision in the log', type: 'Block', nodata: 'no live data', live: 'live', staleOf: 'data from ', loading: 'Loading…',
      err: 'This block could not be loaded.', soon: 'Changing this is not available yet.', ready: 'Answer ready', answering: 'Khipu is answering…',
      opinion: "Khipu's opinion", pros: 'Strengths', cons: 'Risks', sources: 'Sources', since: 'since tracked', seeAll: 'See all',
      less: 'See less', company: 'Company', value: 'Value', metric: 'Metric', date: 'Date', source: 'Source', title: 'Title', change: 'Change',
      hop: 'Hop', companies: 'companies', suppliers: 'Suppliers', customers: 'Customers', peers: 'Similar', dossier: 'Dossier', xray: 'X-Ray',
      unknown: 'This block needs a newer version of Khipus. As text:', about: 'About ', item: 'Kind', text: 'Text', aboutBlock: 'Block',
      privVal: 'Verified private valuation', structure: 'Structure', price: 'Price', mcap: 'Market cap', nrs: 'NRS', chg: 'Change today',
      marketClosed: 'market closed', open: 'Open', ext: 'opens a new tab', chartN: ['chart', 'charts'], tableN: ['table', 'tables'],
      cardN: ['card', 'cards'], figN: ['figure group', 'figure groups'], otherN: ['block', 'blocks'], noUrl: 'no link',
      ago: '', and: ' and ' }
  };
  function t(k) { var d = S[lang()]; return d[k] != null ? d[k] : S.es[k]; }
  // I18n {es,en} o texto plano (nombres propios no se traducen)
  function T(o) {
    if (o == null) return '';
    if (typeof o === 'string' || typeof o === 'number') return String(o);
    if (typeof o === 'object') return String(o[lang()] || o.es || o.en || '');
    return '';
  }
  function reducedPref() {
    try { return !!(W.matchMedia && W.matchMedia('(prefers-reduced-motion: reduce)').matches); } catch (e) { return false; }
  }

  /* ══ formato de cifras (modelo de vista PURO: se prueba en node) ══ */
  var INT_OK = { pct: 1, pp: 1, pts: 1, x: 1, index: 1, none: 1, ratio: 1, years: 1, CCY: 1 };
  var DEF_P = { USD: 2, USD_B: 1, USD_T: 2, CCY: 2, pct: 1, pp: 1, pts: 1, x: 1, nrs: 0, count: 0, index: 1, score: 0, ratio: 2, days: 0, years: 1, none: 2 };
  function nf(v, p) {
    try { return new Intl.NumberFormat(lang() === 'en' ? 'en-US' : 'es-ES', { minimumFractionDigits: p, maximumFractionDigits: p }).format(v); }
    catch (e) { return Number(v).toFixed(p); }
  }
  /* parts(v, unit, {precision, currency, sign}) → {pre, num, suf, text} — el número llega CRUDO del servidor;
     aquí solo se le da formato (unidad, decimales, separadores es/en). Nunca se recalcula. */
  function parts(v, unit, o) {
    o = o || {};
    if (v == null || typeof v !== 'number' || !isFinite(v)) return { pre: '', num: '—', suf: '', text: '—', na: true };
    var u = unit || 'none', p = o.precision != null ? o.precision : (DEF_P[u] != null ? DEF_P[u] : 2), en = lang() === 'en';
    if (u === 'USD' && Math.abs(v) >= 1e3 && o.precision == null) p = 0;
    // enteros sin decimales de relleno (50 %, 40×, índice 100), salvo precios en USD
    if (o.precision == null && Number.isInteger(v) && INT_OK[u]) p = 0;
    var sign = v < 0 ? '−' : (o.sign && v > 0 ? '+' : '');
    var num = nf(Math.abs(v), p), pre = '', suf = '';
    switch (u) {
      case 'USD': pre = '$'; break;
      case 'USD_B': pre = '$'; suf = ' B'; break;
      case 'USD_T': pre = '$'; suf = ' T'; break;
      case 'CCY': suf = ' ' + String(o.currency || ''); break;
      case 'pct': suf = en ? '%' : ' %'; break;
      case 'pp': suf = ' pp'; break;
      case 'pts': suf = ' pts'; break;
      case 'x': suf = '×'; break;
      case 'nrs': suf = '/100'; break;
      case 'days': suf = en ? ' days' : ' días'; break;
      case 'years': suf = en ? ' years' : ' años'; break;
    }
    return { pre: sign + pre, num: num, suf: suf, text: sign + pre + num + suf };
  }
  function fmt(v, unit, o) { return parts(v, unit, o).text; }
  function fmtFig(f, o) { f = f || {}; return parts(f.v, f.unit, { precision: f.precision, currency: f.currency, sign: o && o.sign }).text; }
  // "hace 3 min" / "14:32" / "12 oct" — la hora de un dato (as_of), nunca inventada
  function when(iso) {
    if (!iso) return '';
    try { if (W.KhipuChat && W.KhipuChat.relTime) return W.KhipuChat.relTime(iso); } catch (e) {}
    var s = String(iso), m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
    return m ? m[3] + '/' + m[2] + '/' + m[1] : s.slice(0, 16);
  }
  function isOld(iso, hours) {
    var ts = Date.parse(/^\d{4}-\d{2}-\d{2}$/.test(String(iso)) ? iso + 'T12:00:00' : String(iso));
    return isFinite(ts) && Date.now() - ts > hours * 3600e3;
  }
  // vista de una cifra: lo que el usuario ve + la procedencia que va en el tooltip / aria-label
  function vmFigure(f) {
    f = f || {};
    var p = parts(f.v, f.unit, { precision: f.precision, currency: f.currency });
    return { text: p.text, pre: p.pre, num: p.num, suf: p.suf, na: !!p.na,
      reason: p.na ? (T(f.missing_reason) || t('nodata')) : '', src: String(f.src || ''), as_of: f.as_of || '',
      stale: !!f.stale, live: !!f.live, fact: f.fact || '', explain: (f.explain && EXPLAIN_RX.test(f.explain)) ? f.explain : '' };
  }

  /* ══ DOM seguro ══ */
  var NS = 'http://www.w3.org/2000/svg';
  function h(tag, cls, text) {
    var el = W.document.createElement(tag);
    if (cls) el.className = cls;
    if (text != null && text !== '') el.textContent = String(text);
    return el;
  }
  function sv(tag, attrs, cls) {
    var el = W.document.createElementNS(NS, tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { if (attrs[k] != null) el.setAttribute(k, String(attrs[k])); });
    if (cls) el.setAttribute('class', cls);
    return el;
  }
  function add(p) { for (var i = 1; i < arguments.length; i++) { var c = arguments[i]; if (c) p.appendChild(typeof c === 'string' ? W.document.createTextNode(c) : c); } return p; }
  function tip(el, a, b) { if (el) { el.setAttribute('data-kg-tip', String(a || '').slice(0, 300)); if (b) el.setAttribute('data-kg-tip2', String(b).slice(0, 300)); } return el; }
  function btn(cls, label, fn, aria) {
    var b = h('button', cls, label); b.type = 'button';
    if (aria) b.setAttribute('aria-label', aria);
    if (fn) b.addEventListener('click', function (e) { e.stopPropagation(); fn(e); });
    return b;
  }
  // íconos de la cabecera (trazos CONSTANTES del módulo)
  var ICON = { pin: 'M9 4h6l-1 5 3 3H7l3-3zM12 15v5', more: 'M5 12h.01M12 12h.01M19 12h.01', ext: 'M14 4h6v6M20 4l-9 9M18 14v5H5V6h5' };
  function icon(name) {
    var s = sv('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2.2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true' });
    s.appendChild(sv('path', { d: ICON[name] }));
    return s;
  }
  // enlaces: la MISMA regla que window.safeUrl (solo http/https); setAttribute no necesita el escapado HTML
  function href(u) {
    var s = String(u == null ? '' : u).trim();
    if (!/^https?:\/\//i.test(s)) return null;
    if (typeof W.safeUrl === 'function') {
      var r = W.safeUrl(s);
      if (!r || r === '#') return null;
      return String(r).replace(/&(amp|quot|#39|lt|gt);/g, function (m, k) { return { amp: '&', quot: '"', '#39': "'", lt: '<', gt: '>' }[k]; });
    }
    try { var p = new URL(s); return (p.protocol === 'http:' || p.protocol === 'https:') ? p.href : null; } catch (e) { return null; }
  }
  // markdown ligero de khipu_chat.js (ESCAPA el HTML antes de dar formato); sin él, texto plano
  function mdInto(el, text) {
    var K = W.KhipuChat;
    if (K && typeof K.md === 'function') { el.innerHTML = K.md(text); return true; }
    String(text || '').split(/\n{2,}/).forEach(function (p) { if (p.trim()) el.appendChild(h('p', null, p)); });
    return false;
  }

  /* ══ estilos (tokens --os-* de Khipus OS; --os-dur-* = movimiento) ══ */
  var CSS = '' +
    '.kg-root{--kg-a:var(--os-accent);--kg-b:#E06640;--kg-d1:var(--os-dur-1);--kg-d2:var(--os-dur-2);--kg-d3:var(--os-dur-3);' +
      '--kg-e:var(--os-ease-out,cubic-bezier(.2,0,0,1));--kg-a-soft:color-mix(in srgb,var(--kg-a) 42%,var(--os-surface));display:flex;flex-direction:column;gap:12px;min-width:0;color:var(--os-ink)}' +
    'body:not(.dark) .kg-root,body:not(.dark) .kg-win{--kg-b:#E8623A}' +
    '.kg-root *{box-sizing:border-box}.kg-n{font-variant-numeric:tabular-nums}' +
    '.kg-sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}' +
    '.kg-in{animation:kgIn var(--kg-d2) var(--kg-e) both}' +
    '@keyframes kgIn{from{opacity:0;transform:translateY(6px) scale(.985)}to{opacity:1;transform:none}}' +
    '.kg-text p{margin:0 0 9px}.kg-text p:last-child{margin-bottom:0}.kg-text ul,.kg-text ol{margin:4px 0 9px;padding-left:20px}' +
    '.kg-mk-entity{border-bottom:1px dotted var(--kg-a);cursor:pointer}.kg-mk-entity:hover{color:var(--kg-a)}' +
    '.kg-mk-fact{font-size:10.5px;font-weight:700;color:var(--os-ink-2);vertical-align:super;cursor:pointer;margin-left:1px}' +
    '.kg-mk-unverified{text-decoration:underline wavy var(--os-warn);text-underline-offset:3px}' +
    '.kg-b{position:relative;background:var(--os-surface);border:1px solid var(--os-line);border-radius:16px;padding:12px 14px;min-width:0}' +
    '.kg-hd{display:flex;align-items:center;gap:8px;margin-bottom:10px;min-height:28px;min-width:0}' +
    '.kg-ti{font-weight:700;font-size:13.5px;letter-spacing:-.005em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}' +
    '.kg-sub{font-size:12px;color:var(--os-ink-2);font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}' +
    '.kg-sp{flex:1}' +
    '.kg-stale{font-size:10.5px;font-weight:700;color:var(--os-warn-ink);background:color-mix(in srgb,var(--os-warn) 18%,transparent);border-radius:6px;padding:2px 6px;white-space:nowrap}' +
    '.kg-ic{width:30px;height:30px;flex-shrink:0;border-radius:50%;border:0;background:transparent;color:var(--os-ink-2);cursor:pointer;display:inline-flex;align-items:center;justify-content:center;transition:background var(--kg-d1),color var(--kg-d1)}' +
    '.kg-ic:hover{background:var(--os-surface-2);color:var(--os-ink)}.kg-ic.on{color:var(--kg-a)}.kg-ic svg{width:16px;height:16px}' +
    '.kg-ic:focus-visible,.kg-act:focus-visible,.kg-chip:focus-visible,.kg-q:focus-visible,.kg-seg button:focus-visible,.kg-pop button:focus-visible{outline:none;box-shadow:0 0 0 3px var(--kos-accent-soft)}' +
    '.kg-ft{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:10px}' +
    '.kg-src{font-size:11.5px;color:var(--os-ink-2);background:var(--os-surface-2);border-radius:999px;padding:3px 9px;white-space:nowrap;max-width:100%;overflow:hidden;text-overflow:ellipsis}' +
    '.kg-src b{color:var(--os-ink-2);font-weight:700;margin-right:3px}.kg-src.hi{box-shadow:0 0 0 2px var(--kg-a)}' +
    '.kg-act{font-size:12.5px;font-weight:600;padding:7px 12px;border-radius:999px;border:0;cursor:pointer;background:var(--os-surface-3);color:var(--os-ink);font-family:inherit;transition:background var(--kg-d1),transform var(--kg-d1)}' +
    '.kg-act:hover{background:var(--os-surface-2);box-shadow:0 0 0 1px var(--os-line)}.kg-act:active{transform:scale(.97)}' +
    '.kg-ft .kg-act{margin-left:auto}.kg-ft .kg-act~.kg-act{margin-left:0}' +
    '.kg-acts{display:flex;flex-wrap:wrap;gap:6px}' +
    '.kg-chip{border:0;background:var(--os-surface-2);color:var(--os-ink);font-size:12.5px;line-height:1.3;padding:7px 12px;border-radius:999px;cursor:pointer;text-align:left;font-family:inherit;transition:background var(--kg-d1),transform var(--kg-d1)}' +
    '.kg-chip:hover{background:var(--os-surface-3);transform:translateY(-1px)}' +
    '.kg-q{width:17px;height:17px;border-radius:50%;border:0;background:var(--os-surface-3);color:var(--os-ink-2);font-size:10.5px;font-weight:800;cursor:help;display:inline-flex;align-items:center;justify-content:center;padding:0;flex-shrink:0;font-family:inherit}' +
    '.kg-q:hover{background:var(--kg-a);color:#fff}' +
    /* cifras */
    '.kg-tiles{display:grid;grid-template-columns:repeat(var(--kg-cols,4),minmax(0,1fr));gap:8px}' +
    '.kg-tile{background:var(--os-surface-2);border-radius:14px;padding:11px 12px 10px;min-width:0;display:flex;flex-direction:column}' +
    '.kg-tile .l{font-size:12px;color:var(--os-ink-2);font-weight:600;display:flex;align-items:center;gap:5px;white-space:nowrap;overflow:hidden}' +
    '.kg-tile .l span{overflow:hidden;text-overflow:ellipsis}' +
    '.kg-big{font-size:24px;font-weight:800;letter-spacing:-.02em;margin:3px 0 4px;line-height:1.15;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.kg-big small{font-size:13px;font-weight:700;color:var(--os-ink-2);margin-left:2px}.kg-big.na{color:var(--os-ink-2)}' +
    '.kg-d{font-size:11.5px;color:var(--os-ink-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.kg-up{color:var(--os-good-ink)}.kg-dn{color:var(--os-bad-ink)}' +
    '.kg-tile .kg-src{align-self:flex-start;margin-top:6px}.kg-tile .kg-spk{margin-top:4px}' +
    '.kg-live{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--os-good);margin-left:4px;vertical-align:middle}' +
    '.kg-spk{width:100%;height:30px;display:block;overflow:visible}.kg-spk path{fill:none;stroke:var(--kg-a);stroke-width:2;vector-effect:non-scaling-stroke;stroke-linejoin:round;stroke-linecap:round}' +
    /* ficha */
    '.kg-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:8px}' +
    '.kg-cc{background:var(--os-surface-2);border-radius:14px;padding:12px;display:flex;flex-direction:column;gap:8px;min-width:0;transition:transform var(--kg-d1),box-shadow var(--kg-d1)}' +
    '.kg-cc:hover{transform:translateY(-2px);box-shadow:var(--os-shadow,0 8px 24px rgba(0,0,0,.3))}' +
    '.kg-cc-top{display:flex;align-items:center;gap:9px;min-width:0}' +
    '.kg-cc-lg{width:34px;height:34px;font-size:12.5px;border-radius:10px;background:var(--os-surface);display:flex;align-items:center;justify-content:center;font-weight:800;color:var(--kg-a);flex-shrink:0}' +
    '.kg-cc-n{font-weight:700;font-size:13.5px;line-height:1.2;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
    '.kg-cc-r{font-size:12px;color:var(--os-ink-2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
    '.kg-cc-f{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12px;color:var(--os-ink-2)}.kg-cc-f b{color:var(--os-ink);font-weight:750;margin-left:4px}' +
    '.kg-cc-l{font-size:12px;color:var(--os-ink-2);line-height:1.5}.kg-cc-l b{font-weight:700;color:var(--os-ink-2);margin-right:4px}' +
    '.kg-cc-b{display:flex;gap:6px;flex-wrap:wrap}' +
    /* avisos */
    '.kg-cp{display:grid;grid-template-columns:1fr 1fr;gap:8px}' +
    '.kg-cpc{border-radius:14px;padding:11px 12px;background:var(--os-surface-2);min-width:0}' +
    '.kg-cph{font-size:12.5px;font-weight:800;display:flex;align-items:center;gap:7px;margin-bottom:6px}' +
    '.kg-cpc.good .kg-cph{color:var(--os-good-ink)}.kg-cpc.warn .kg-cph{color:var(--os-warn-ink)}' +
    '.kg-cpi{display:flex;gap:8px;font-size:13px;line-height:1.45;padding:4px 0}' +
    '.kg-cpi .ic{flex-shrink:0;width:18px;height:18px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:800;margin-top:1px}' +
    '.good .ic{background:color-mix(in srgb,var(--os-good) 20%,transparent);color:var(--os-good-ink)}' +
    '.warn .ic{background:color-mix(in srgb,var(--os-warn) 22%,transparent);color:var(--os-warn-ink)}' +
    '.kg-cpi sup{color:var(--os-ink-2);font-size:10.5px;font-weight:700;margin-left:3px}' +
    '.kg-op{font-size:10.5px;font-weight:700;color:var(--os-ai);background:color-mix(in srgb,var(--os-ai) 14%,transparent);border-radius:6px;padding:2px 6px;white-space:nowrap}' +
    '.kg-box{display:flex;gap:10px;align-items:flex-start;border-radius:14px;padding:11px 13px;font-size:13px;line-height:1.5;background:var(--os-surface-2)}' +
    '.kg-box.warning{background:color-mix(in srgb,var(--os-warn) 13%,var(--os-surface));color:var(--os-ink)}' +
    '.kg-box.info{background:color-mix(in srgb,var(--kg-a) 11%,var(--os-surface))}' +
    '.kg-box.unavailable{color:var(--os-ink-2)}.kg-box ul{margin:0;padding-left:18px}' +
    '.kg-disc{font-size:12px;color:var(--os-ink-2);display:flex;gap:6px;align-items:center}' +
    /* tabla */
    '.kg-tbw{overflow-x:auto;max-width:100%}' +
    '.kg-tb{width:100%;border-collapse:collapse;font-size:13px}' +
    '.kg-tb th{font-size:11.5px;color:var(--os-ink-2);font-weight:700;text-align:left;padding:6px 8px;border-bottom:1px solid var(--os-line);white-space:nowrap}' +
    '.kg-tb th button{all:unset;cursor:pointer}.kg-tb th.end,.kg-tb td.end{text-align:right}' +
    '.kg-tb td{padding:8px;border-bottom:1px solid var(--os-line);vertical-align:middle}' +
    '.kg-tb tr:last-child td{border-bottom:0}.kg-tb tbody tr{transition:background var(--kg-d1)}.kg-tb tbody tr:hover{background:var(--os-surface-2)}' +
    '.kg-tb td,.kg-tb th{overflow-wrap:normal;word-break:normal;hyphens:auto}.kg-tb .m{font-weight:600}' +
    '.kg-badge{font-size:11px;font-weight:700;background:var(--os-surface-2);border-radius:6px;padding:2px 7px}' +
    '.kg-ent{cursor:pointer;font-weight:600}.kg-ent:hover{color:var(--kg-a)}' +
    /* línea de tiempo */
    '.kg-tl{display:flex;flex-direction:column;gap:2px;position:relative}' +
    '.kg-tli{display:grid;grid-template-columns:86px minmax(0,1fr);gap:10px;padding:6px 4px;border-radius:10px}' +
    '.kg-tli:hover{background:var(--os-surface-2)}' +
    '.kg-tld{font-size:11.5px;color:var(--os-ink-2);font-weight:600;padding-top:1px}' +
    '.kg-tlt{font-size:13px;line-height:1.4;min-width:0}.kg-tlt a{color:var(--os-ink);text-decoration:none}.kg-tlt a:hover{text-decoration:underline}' +
    '.kg-tlm{font-size:11.5px;color:var(--os-ink-2);margin-top:2px;display:flex;gap:8px;flex-wrap:wrap}' +
    /* fuentes */
    '.kg-srcs{font-size:12px;line-height:1.7;color:var(--os-ink-2);display:flex;flex-wrap:wrap;gap:4px 12px}' +
    '.kg-srcs a{color:var(--os-ink-2);text-decoration:underline;text-decoration-color:var(--os-line);text-underline-offset:2px}' +
    '.kg-srcs .kg-si{border-radius:6px;padding:0 3px}.kg-srcs .kg-si.hi{background:color-mix(in srgb,var(--kg-a) 18%,transparent)}' +
    '.kg-unk{font-size:13px;color:var(--os-ink-2)}.kg-unk b{display:block;font-size:11.5px;color:var(--os-ink-2);margin-bottom:3px}' +
    /* esqueleto con la forma real + error */
    '.kg-sk{display:flex;flex-direction:column;gap:10px}.kg-sk .lab{font-size:11.5px;color:var(--os-ink-2);font-weight:600}' +
    '.kg-sk i{display:block;border-radius:8px;background:linear-gradient(90deg,var(--os-surface-2) 0%,var(--os-surface-3) 40%,var(--os-surface-2) 80%);background-size:300% 100%;animation:kgShim 1.2s ease-in-out 4}' +
    '@keyframes kgShim{from{background-position:100% 0}to{background-position:-100% 0}}' +
    '.kg-err{font-size:13px;color:var(--os-bad-ink);display:flex;gap:10px;align-items:center;flex-wrap:wrap}' +
    /* tooltip, menú, hoja */
    '#kg-tip{position:fixed;z-index:12000;pointer-events:none;background:var(--os-btn);color:var(--os-btn-ink);font-size:12px;font-weight:600;line-height:1.4;padding:7px 10px;border-radius:10px;max-width:280px;opacity:0;transition:opacity 120ms;box-shadow:var(--kos-shadow-lg,0 10px 30px rgba(0,0,0,.4))}' +
    '#kg-tip.on{opacity:1}#kg-tip .t2{display:block;font-weight:500;opacity:.75;font-size:11.5px}' +
    '.kg-pop{position:fixed;z-index:11900;background:var(--os-surface);color:var(--os-ink);border:1px solid var(--os-line);border-radius:14px;box-shadow:var(--kos-shadow-lg,0 10px 30px rgba(0,0,0,.4));padding:6px;min-width:210px;max-width:320px;font-size:13px;line-height:1.5}' +
    '.kg-pop button{display:flex;width:100%;gap:9px;align-items:center;border:0;background:transparent;color:inherit;padding:8px 10px;border-radius:9px;font-size:13px;cursor:pointer;text-align:left;font-family:inherit}' +
    '.kg-pop button:hover{background:var(--os-surface-2)}.kg-pop h4{margin:4px 8px 4px;font-size:13px}' +
    '.kg-kv{display:grid;grid-template-columns:auto 1fr;gap:3px 10px;font-size:12px;margin:4px 8px 6px}.kg-kv>span:nth-child(odd){color:var(--os-ink-2)}' +
    '.kg-kv code{font-family:ui-monospace,"JetBrains Mono",monospace;font-size:11.5px;overflow-wrap:anywhere}.kg-pop a{color:var(--kg-a);margin:0 8px 6px;display:inline-block}' +
    '.kg-scrim{position:fixed;inset:0;background:var(--kos-scrim);z-index:11000}' +
    '.kg-sheet{position:fixed;left:0;right:0;bottom:0;z-index:11001;background:var(--os-surface);color:var(--os-ink);border-radius:20px 20px 0 0;max-height:82vh;overflow:auto;padding:6px 12px 16px;animation:kgUp var(--kg-d3) var(--kg-e)}' +
    '.kg-sheet .grab{width:40px;height:5px;border-radius:5px;background:var(--os-surface-3);margin:6px auto 8px}' +
    '@keyframes kgUp{from{transform:translateY(100%)}to{transform:none}}' +
    '.kg-win .kg-b{border:0;padding:0;background:transparent}' +
    /* compacto (< 520 px) */
    '.kg-compact .kg-tiles{--kg-cols:2!important}.kg-compact .kg-cp{grid-template-columns:1fr}.kg-compact .kg-big{font-size:21px}' +
    '.kg-compact .kg-d,.kg-compact .kg-tile .l,.kg-compact .kg-tile .l span{white-space:normal}.kg-compact .kg-hd>.kg-sub{display:none}.kg-compact .kg-b{padding:11px}' +
    '.kg-compact .kg-tli{grid-template-columns:70px minmax(0,1fr)}' +
    '.kg-compact .kg-cards{grid-template-columns:1fr}.kg-compact .kg-cc{flex-direction:row;flex-wrap:wrap;align-items:center}.kg-compact .kg-cc>*{flex-basis:100%}' +
    '.kg-compact .kg-cc>.kg-cc-top{flex:1 1 55%}.kg-compact .kg-cc>.kg-spk{flex:1 1 30%;width:30%}' +
    '.kg-compact .kg-tb td,.kg-compact .kg-tb th{padding:7px 4px}' +
    /* reducir movimiento: TODO aparece de golpe */
    '.kg-rm,.kg-rm *{animation:none!important;transition:none!important}' +
    '@media(prefers-reduced-motion:reduce){.kg-root,.kg-root *,.kg-win,.kg-win *,.kg-sheet,#kg-tip,.kg-pop{animation:none!important;transition:none!important}}';

  function ensureStyles() {
    var d = W.document;
    if (!d || !d.head || d.getElementById('kg-styles')) return;
    var st = d.createElement('style'); st.id = 'kg-styles'; st.textContent = CSS;
    d.head.appendChild(st);
  }

  /* ══ tooltip compartido ([data-kg-tip]) ══ */
  var _tip = null, _tipWired = false;
  function wireTip() {
    if (_tipWired || !W.document || !W.document.addEventListener) return;
    _tipWired = true;
    W.document.addEventListener('pointermove', function (e) {
      var el = e.target && e.target.closest && e.target.closest('[data-kg-tip]');
      if (!el) { if (_tip) _tip.classList.remove('on'); return; }
      if (!_tip) { _tip = h('div', 'kos-themed'); _tip.id = 'kg-tip'; _tip.setAttribute('role', 'tooltip'); W.document.body.appendChild(_tip); }
      _tip.textContent = el.getAttribute('data-kg-tip') || '';
      var b = el.getAttribute('data-kg-tip2'); if (b) _tip.appendChild(h('span', 't2', b));
      _tip.classList.add('on');
      var r = _tip.getBoundingClientRect(), x = e.clientX + 14, y = e.clientY - r.height - 12;
      if (x + r.width > W.innerWidth - 8) x = e.clientX - r.width - 14;
      if (y < 8) y = e.clientY + 18;
      _tip.style.left = Math.max(8, x) + 'px'; _tip.style.top = y + 'px';
    }, { passive: true });
    W.document.addEventListener('scroll', function () { if (_tip) _tip.classList.remove('on'); }, true);
  }

  /* ══ popover (menú ⋯, ¿de dónde sale?) ══ */
  var _pop = null, _popAnchor = null;
  // cerrar devuelve el foco al botón que abrió el menú (Esc o tras elegir), salvo que el foco ya esté en otra parte
  function closePop(keepFocus) {
    var had = _pop, a = _popAnchor;
    if (_pop && _pop.parentNode) _pop.parentNode.removeChild(_pop);
    _pop = null; _popAnchor = null;
    if (had && !keepFocus && a && a.isConnected !== false && a.focus) {
      var ae = W.document.activeElement;
      if (!ae || ae === W.document.body || had.contains(ae)) try { a.focus({ preventScroll: true }); } catch (e) {}
    }
  }
  /* asMenu = lista de acciones (role=menu + menuitem + flechas); si no, un diálogo no modal (¿de dónde sale?) */
  function openPop(anchor, kids, label, asMenu) {
    closePop(true);
    var p = h('div', 'kg-pop kos-themed'); p.setAttribute('role', asMenu ? 'menu' : 'dialog');
    if (label) p.setAttribute('aria-label', label);
    kids.forEach(function (k) {
      if (!k) return;
      if (asMenu && k.tagName === 'BUTTON') { k.setAttribute('role', 'menuitem'); k.setAttribute('tabindex', '-1'); }
      p.appendChild(k);
    });
    if (asMenu) p.addEventListener('keydown', function (e) {
      var its = [].slice.call(p.querySelectorAll('[role=menuitem]')); if (!its.length) return;
      var i = its.indexOf(W.document.activeElement), n = -1;
      if (e.key === 'ArrowDown') n = (i + 1) % its.length;
      else if (e.key === 'ArrowUp') n = (i - 1 + its.length) % its.length;
      else if (e.key === 'Home') n = 0;
      else if (e.key === 'End') n = its.length - 1;
      else if (e.key === 'Tab') { closePop(); return; }
      if (n < 0) return;
      e.preventDefault(); try { its[n].focus({ preventScroll: true }); } catch (x) {}
    });
    W.document.body.appendChild(p);
    var a = anchor.getBoundingClientRect(), r = p.getBoundingClientRect();
    p.style.left = Math.max(8, Math.min(W.innerWidth - r.width - 8, a.right - r.width)) + 'px';
    p.style.top = (a.bottom + r.height + 8 > W.innerHeight ? Math.max(8, a.top - r.height - 6) : a.bottom + 6) + 'px';
    _pop = p; _popAnchor = anchor;
    var f = p.querySelector('button,a');
    if (!f) { p.setAttribute('tabindex', '-1'); f = p; }
    try { f.focus({ preventScroll: true }); } catch (e) {}
    return p;
  }
  var _popWired = false;
  function wirePop() {
    if (_popWired || !W.document || !W.document.addEventListener) return;
    _popWired = true;
    W.document.addEventListener('pointerdown', function (e) { if (_pop && !_pop.contains(e.target) && !(e.target.closest && e.target.closest('.kg-ic'))) closePop(true); });
    W.document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && _pop) { closePop(); } });
  }

  /* ══ "?" explicable (engine/explain.js) ══ */
  function qBtn(key) {
    if (!key || !EXPLAIN_RX.test(key) || typeof W.explainMetric !== 'function') return null;
    var b = btn('kg-q', '?', function () { W.explainMetric(key); }, lang() === 'en' ? 'What is this?' : '¿Qué es esto?');
    return b;
  }
  function registerExplains() {
    if (typeof W.explainRegister !== 'function') return;
    var X = {
      genui_na: { es: { t: 'Sin dato en vivo', b: 'Cuando no hay una fuente confiable en este momento, Khipu muestra «—» y el motivo, en vez de inventar un número.' },
        en: { t: 'No live data', b: 'When there is no reliable source right now, Khipu shows “—” and the reason instead of inventing a number.' } },
      genui_hops: { es: { t: 'Saltos del choque', b: 'Salto 1 = los clientes directos de la empresa que cae. Salto 2 = los clientes de esos clientes. Y así. Las cifras salen del motor de choques del servidor (el mismo de toda la app).' },
        en: { t: 'Shock hops', b: 'Hop 1 = the direct customers of the company that fails. Hop 2 = their customers. And so on. The figures come from the server shock engine (the same one used across the app).' } },
      genui_pf: { es: { t: 'Golpe a tu cartera', b: 'Estimación del motor de choques sobre TUS posiciones, con su banda de error. No es una predicción del precio. Si la calibración es débil, Khipu no da cifra.' },
        en: { t: 'Hit to your portfolio', b: 'Shock-engine estimate on YOUR positions, with its error band. It is not a price forecast. If the calibration is weak, Khipu gives no figure.' } },
      genui_index: { es: { t: 'Índice (inicio = 100)', b: 'Pone todo en la misma escala: el primer día vale 100 y el resto se compara con él. Sirve para comparar formas, no precios.' },
        en: { t: 'Index (start = 100)', b: 'Puts everything on one scale: the first day is 100 and the rest compare to it. Good for comparing shapes, not prices.' } }
    };
    Object.keys(X).forEach(function (k) { try { W.explainRegister(k, X[k]); } catch (e) {} });
  }

  /* ══ contexto de pintado ══ */
  function mkCtx(opts, env) {
    opts = opts || {};
    var facts = {};
    ((env && env.blocks) || []).forEach(function (b) {
      if (b && b.type === 'sources' && b.data && Array.isArray(b.data.items)) b.data.items.forEach(function (it) { if (it && it.id) facts[it.id] = it; });
    });
    return { lang: lang(), compact: !!opts.compact, reduced: opts.reduced != null ? !!opts.reduced : reducedPref(), facts: facts,
      onAction: opts.onAction || null, reqId: opts.reqId || (env && env._req) || '', pinned: !!opts.pinned, root: null };
  }

  /* ══ procedencia: chips de fuente al pie del bloque ══ */
  function srcChip(id, ctx, fallbackLabel, asOf) {
    var f = ctx.facts[id] || null;
    var lab = (f && f.label) || fallbackLabel || '';
    var at = (f && f.as_of) || asOf || '';
    var c = h('span', 'kg-src');
    if (id) c.appendChild(h('b', null, id));
    c.appendChild(W.document.createTextNode(lab + (at ? ' · ' + when(at) : '')));
    if (id) c.setAttribute('data-kg-fact', id);
    tip(c, (id ? id + ' · ' : '') + lab, at ? t('asof') + ': ' + at : '');
    return c;
  }
  function blockAsOf(b) {
    var d = b.data || {};
    if (d.as_of) return d.as_of;
    var v = d.values || d.metric || (d.series && d.series[0] && d.series[0].values) || (d.series && d.series.values);
    if (v && v.as_of) return v.as_of;
    if (d.items && d.items[0] && d.items[0].value && d.items[0].value.as_of) return d.items[0].value.as_of;
    if (d.price && d.price.as_of) return d.price.as_of;
    return '';
  }
  function figChip(fig, ctx) {   // procedencia de UNA cifra (tile)
    var vm = vmFigure(fig);
    if (!vm.src && !vm.fact) return null;
    return srcChip(vm.fact, ctx, vm.src, vm.as_of);
  }

  /* ══ acciones (solo abrir o sugerir) ══ */
  function surface(kind, arg) { try { return W._surface ? W._surface(kind, arg) : false; } catch (e) { return false; } }
  function stage(kind, arg) {
    var ck = W.BixbyCockpit;
    try { if (ck && typeof ck.stage === 'function' && (!ck.isOpen || ck.isOpen())) return ck.stage(kind, arg); } catch (e) {}
    return null;
  }
  function chatRun(a) { try { if (W.KhipuChat && W.KhipuChat.runAction) return W.KhipuChat.runAction(a); } catch (e) {} return false; }
  function chatInput() {
    var d = W.document;
    return d.getElementById('bcp-input') || d.getElementById('bcc-input') || null;
  }
  function prefill(text) {
    var i = chatInput(); if (!i) return false;
    i.value = String(text || '').slice(0, 300);
    try { i.focus({ preventScroll: true }); i.setSelectionRange(i.value.length, i.value.length); } catch (e) {}
    return true;
  }
  function entId(e) { return e && typeof e.id === 'string' && ID_RX.test(e.id) ? e.id : null; }
  function openWindow(win, a, block) {
    var id = entId(a.entity) || entId(block && block.entity) || '';
    if (win === 'genui') return pin(block, null);
    if (win === 'xray') return id ? (stage('xray', id) || chatRun({ type: 'open_xray', arg: id })) : false;
    if (win === 'sim') return id ? (stage('sim', { id: id, kind: 'collapse' }) || surface('stress', id)) : false;
    if (win === 'compare') {
      var es = (block && block.data && block.data.entities) || [];
      var a0 = entId(es[0]) || id, b0 = entId(es[1]);
      return a0 && b0 ? (stage('compare', { a: a0, b: b0 }) || surface('compare', { a: a0, b: b0 })) : false;
    }
    if (win === 'geo') {
      var r = stage('geo');
      if (a.lat != null && W.KhipuWorld && W.KhipuWorld.focus) setTimeout(function () { try { W.KhipuWorld.focus(a.lat, a.lon); } catch (e) {} }, 900);
      return r || surface('tab', 'geo');
    }
    if (win === 'canvas') return stage('canvas', a.text || '') || surface('canvas', a.text || '');
    if (win === 'agents') return stage('agents');
    if (id && W.KhipuOSWin && W.KhipuOSWin.open && W.KhipuOSWin.open(win, { id: id })) return true;
    return id ? stage(win, { id: id }) : false;
  }
  function runAction(a, block, ctx) {
    if (!a || !ACTION_KINDS[a.kind]) return false;
    if (ctx && typeof ctx.onAction === 'function') { try { if (ctx.onAction(a, block) === true) return true; } catch (e) {} }
    var id = entId(a.entity);
    switch (a.kind) {
      case 'open_window': return WINDOWS[a.window] ? openWindow(a.window, a, block) : false;
      case 'open_dossier': if (!id) return false; { var n = (W.NODE_BY_ID || {})[id]; return surface('dossier', (n && n.mkt) || id) || chatRun({ type: 'dossier', arg: id }); }
      case 'open_xray': return id ? chatRun({ type: 'open_xray', arg: id }) : false;
      case 'open_map': return id ? chatRun({ type: 'navigate', arg: id }) : false;
      case 'open_world': return (typeof a.lat === 'number' && typeof a.lon === 'number') ? chatRun({ type: 'open_world', arg: { lat: a.lat, lon: a.lon } }) : false;
      case 'open_research': if (id && W.KhipuResearch && W.KhipuResearch.open) { W.KhipuResearch.open(id); return true; } return false;
      case 'open_committee': if (id && W.KhipuCommittee && W.KhipuCommittee.open) { W.KhipuCommittee.open(id); return true; } return false;
      case 'prefill_chat': return prefill(a.text);
      case 'pin': return pin(block, ctx && ctx._el ? ctx._el : null);
      case 'set_view': return !!(ctx && ctx._setView && ctx._setView(a.view));
      case 'set_range': return refine(block, { range: a.range }, ctx);
    }
    return false;
  }
  function actBtn(a, block, ctx, cls) {
    if (!a || !ACTION_KINDS[a.kind] || (a.kind === 'open_window' && !WINDOWS[a.window])) return null;
    return btn(cls || 'kg-act', T(a.label), function () { runAction(a, block, ctx); });
  }
  // refinar un bloque SIN IA (POST /api/genui/block, fase F4). Si el servidor aún no lo tiene, se dice.
  function refine(block, opts, ctx) {
    if (!block || !block.prov || typeof fetch !== 'function') return false;
    var base = (typeof W.BASE === 'string' ? W.BASE : '');
    fetch(base + '/api/genui/block', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: block.type, tool: block.prov.name, args: block.prov.args || '', opts: opts || {}, lang: lang(), entity: block.entity || null }) })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (nb) {
        var b2 = nb && (nb.block || nb);
        if (!b2 || b2.type !== block.type || !ctx || !ctx._el) throw new Error('no');
        replaceBlock(ctx._el, b2, ctx);
      }).catch(function () { notify(t('soon')); });
    return true;
  }
  function notify(msg) {
    try { if (W.KhipuToast && W.KhipuToast.show) { W.KhipuToast.show({ kind: 'info', title: msg }); return; } } catch (e) {}
    announce(msg);
  }

  /* ══ anuncio accesible (role=status oculto) ══ */
  var _st = null;
  function announce(msg) {
    var d = W.document; if (!d || !d.body) return;
    if (!_st) { _st = h('div', 'kg-sr'); _st.id = 'kg-status'; _st.setAttribute('role', 'status'); _st.setAttribute('aria-live', 'polite'); d.body.appendChild(_st); }
    _st.textContent = '';
    setTimeout(function () { if (_st) _st.textContent = msg; }, 30);
  }
  function summary(blocks) {
    var c = { chart: 0, table: 0, card: 0, fig: 0, other: 0 };
    (blocks || []).forEach(function (b) {
      if (!b || BARE[b.type] || b.state === 'planned') return;
      if (CHARTY[b.type]) c.chart++; else if (b.type === 'table') c.table++; else if (b.type === 'company.card') c.card++;
      else if (b.type === 'metric.tiles') c.fig++; else c.other++;
    });
    var parts0 = [];
    [['chart', 'chartN'], ['table', 'tableN'], ['card', 'cardN'], ['fig', 'figN'], ['other', 'otherN']].forEach(function (k) {
      var n = c[k[0]]; if (n) parts0.push(n + ' ' + t(k[1])[n === 1 ? 0 : 1]);
    });
    return t('ready') + (parts0.length ? ': ' + parts0.join(', ') : '');
  }

  /* ══ la envoltura de un bloque: cabecera, cuerpo, pie con fuentes, ⋯, 📌 ══ */
  function isPinnable(b) { return b.pinnable !== false && !BARE[b.type] && b.type !== 'callout' && b.type !== 'image'; }
  function header(b, ctx, wrap) {
    var hd = h('div', 'kg-hd');
    hd.appendChild(h('span', 'kg-ti', T(b.title) || ''));
    if (b.subtitle) hd.appendChild(h('span', 'kg-sub', T(b.subtitle)));
    var asOf = blockAsOf(b);
    if (b.state === 'stale') hd.appendChild(tip(h('span', 'kg-stale', t('staleOf') + when(asOf)), t('asof') + ': ' + asOf));
    hd.appendChild(h('span', 'kg-sp'));
    if (b.state === 'ready' || b.state === 'stale') {
      if (!ctx.pinned && isPinnable(b)) {
        var pb = btn('kg-ic', null, function () { pin(b, wrap, pb); }, t('pin'));
        pb.appendChild(icon('pin')); tip(pb, t('pin')); hd.appendChild(pb);
      }
      if (b.type !== 'callout' || b.prov) {
        var mb = btn('kg-ic', null, function () { menu(mb, b, wrap, ctx); }, t('more'));
        mb.setAttribute('aria-haspopup', 'menu'); mb.appendChild(icon('more')); hd.appendChild(mb);
      }
    }
    return hd;
  }
  function footer(b, ctx) {
    var ft = h('div', 'kg-ft'), n = 0, asOf = blockAsOf(b);
    var perFig = b.type === 'metric.tiles' && ((b.data || {}).items || []).every(function (it) { return it.value && (it.value.fact || it.value.src); });
    if (!perFig) (Array.isArray(b.sources) ? b.sources : []).slice(0, 8).forEach(function (id) { ft.appendChild(srcChip(id, ctx, '', asOf)); n++; });
    if (!n && !perFig && b.prov && b.prov.name) { ft.appendChild(srcChip(b.prov.fact || '', ctx, b.prov.name, asOf)); n++; }
    (Array.isArray(b.actions) ? b.actions : []).slice(0, 2).forEach(function (a) { var x = actBtn(a, b, ctx); if (x) { ft.appendChild(x); n++; } });
    return n ? ft : null;
  }
  function menu(anchor, b, wrap, ctx) {
    var items = [], allowed = Array.isArray(b.menu) && b.menu.length ? b.menu : ['table', 'where_from', 'ask'];
    var reg = REG[b.type] || {};
    var asTable = wrap && wrap.classList.contains('kg-astable');
    if (allowed.indexOf('table') >= 0 && toTable(b)) items.push(btn(null, '⧉  ' + (asTable ? t('chart') : t('table')), function () { closePop(); toggleTable(wrap, b, ctx); }));
    if (allowed.indexOf('where_from') >= 0 && b.prov) items.push(btn(null, 'ⓘ  ' + t('where'), function () { closePop(); whereFrom(anchor, b); }));
    if (allowed.indexOf('ask') >= 0) items.push(btn(null, '↳  ' + t('ask'), function () {
      closePop(); prefill(t('about') + (T(b.title) || t('aboutBlock')) + ': ');
      _ref = { id: b.id, prov: b.prov || null, ts: Date.now() };
    }));
    if (allowed.indexOf('csv') >= 0 && toTable(b)) items.push(btn(null, '⇩  ' + t('csv'), function () { closePop(); csv(b); }));
    if (allowed.indexOf('refresh') >= 0 && b.prov) items.push(btn(null, '⟳  ' + t('refresh'), function () { closePop(); refine(b, {}, ctx); }));
    if (!reg && !items.length) return;
    if (items.length) openPop(anchor, items, t('more'), true);
  }
  function whereFrom(anchor, b) {
    var p = b.prov || {}, kv = h('div', 'kg-kv');
    var row = function (k, v, code) { if (v == null || v === '') return; kv.appendChild(h('span', null, k)); kv.appendChild(h(code ? 'code' : 'span', null, String(v))); };
    row(t('tool'), p.name, true);
    if (p.call != null) row(t('call'), '#' + p.call, true);
    row(t('fact'), p.fact || '', true);
    row(t('args'), p.args || '');
    var at = blockAsOf(b); row(t('asof'), at ? at + ' (' + when(at) + ')' : '');
    row(t('gen'), p.generation != null ? p.generation : '');
    row(t('gv'), p.graph_version != null ? p.graph_version : '');
    row(t('type'), V + ' · ' + b.type, true);
    var kids = [h('h4', null, t('where')), kv];
    if (p.decision_id && /^[A-Za-z0-9_-]{4,64}$/.test(p.decision_id)) {
      var a = h('a', null, t('why')); a.setAttribute('href', '/api/ledger/why/' + encodeURIComponent(p.decision_id));
      a.setAttribute('target', '_blank'); a.setAttribute('rel', 'noopener noreferrer'); kids.push(a);
    }
    openPop(anchor, kids, t('where'));
  }
  function toggleTable(wrap, b, ctx) {
    if (!wrap) return;
    var bd = wrap.querySelector('.kg-bd'); if (!bd) return;
    var on = !wrap.classList.contains('kg-astable');
    wrap.classList.toggle('kg-astable', on);
    bd.textContent = '';
    if (on) bd.appendChild(tableEl(toTable(b)));
    else {
      // volver al gráfico: cada renderizador esconde sus marcas hasta go(); sin llamarlo la línea, las barras y
      // los conteos quedaban vacíos ('…')
      var c2 = Object.assign({}, ctx, { reduced: true }), r = renderBody(bd, b, c2);
      if (r && typeof r.go === 'function') try { r.go(true); } catch (e) {}
    }
  }
  function csv(b) {
    var tb = toTable(b); if (!tb) return;
    var q = function (v) { v = String(v == null ? '' : v); return /[",\n;]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };
    var txt = [tb.columns.map(q).join(',')].concat(tb.rows.map(function (r) { return r.map(q).join(','); })).join('\n');
    try {
      var url = URL.createObjectURL(new Blob(['\ufeff' + txt], { type: 'text/csv;charset=utf-8' }));
      var a = h('a'); a.setAttribute('href', url); a.setAttribute('download', 'khipu_' + String(b.id || 'bloque') + '.csv');
      W.document.body.appendChild(a); a.click();
      setTimeout(function () { try { URL.revokeObjectURL(url); a.parentNode.removeChild(a); } catch (e) {} }, 400);
    } catch (e) {}
  }
  function tableEl(tb) {
    var w = h('div', 'kg-tbw'), tbl = h('table', 'kg-tb'), th = h('thead'), tr = h('tr'), body = h('tbody');
    (tb.columns || []).forEach(function (c) { var x = h('th', null, c); x.setAttribute('scope', 'col'); tr.appendChild(x); });
    th.appendChild(tr); tbl.appendChild(th);
    (tb.rows || []).forEach(function (r) { var row = h('tr'); r.forEach(function (c) { row.appendChild(h('td', null, c)); }); body.appendChild(row); });
    tbl.appendChild(body); w.appendChild(tbl);
    return w;
  }

  /* ══ esqueleto con la forma real + altura reservada ══ */
  var SK = { 'metric.tiles': [[100, 74]], 'chart.line': [[34, 22], [100, 150]], 'chart.bar': [[90, 14], [70, 14], [55, 14], [40, 14]],
    'chart.candles': [[100, 170]], ranking: [[96, 14], [78, 14], [62, 14], [48, 14], [34, 14]], table: [[100, 16], [100, 16], [100, 16], [100, 16]],
    'company.card': [[60, 34], [100, 30], [70, 28]], 'graph.mini': [[100, 200]], 'impact.cascade': [[100, 70], [100, 18], [100, 18], [100, 18]],
    timeline: [[100, 30], [100, 30], [100, 30]], 'geo.mini': [[100, 180]], callout: [[100, 90]], image: [[100, 70]], comparison: [[100, 16], [100, 16], [100, 16], [100, 16]] };
  function skeleton(b) {
    var reg = REG[b.type] || {};
    if (reg.skeleton) { try { var x = reg.skeleton(b); if (x) return x; } catch (e) {} }
    var sk = h('div', 'kg-sk'); sk.setAttribute('aria-hidden', 'true');
    sk.appendChild(h('div', 'lab', '◌ ' + t('loading') + (b.prov && b.prov.name ? ' · ' + b.prov.name : '')));
    (SK[b.type] || [[100, 60]]).forEach(function (d) { var i = h('i'); i.style.width = d[0] + '%'; i.style.height = d[1] + 'px'; sk.appendChild(i); });
    return sk;
  }
  function height(b, width) {
    var reg = REG[b.type] || {};
    if (reg.height) { try { return reg.height(b, width); } catch (e) {} }
    return 44 + (SK[b.type] || [[100, 60]]).reduce(function (s, d) { return s + d[1] + 10; }, 0);
  }

  /* ══ pintado ══ */
  function renderBody(bd, b, ctx) {
    var reg = REG[b.type];
    var out = null;
    try { out = reg.render(bd, b, ctx) || null; }
    catch (e) {
      try { console.warn('[KhipuGenUI] ' + b.type + ':', e); } catch (x) {}
      bd.textContent = ''; bd.appendChild(h('div', 'kg-unk', T(b.alt) || t('err')));
    }
    return out;
  }
  function unknownBlock(b) {
    var u = h('div', 'kg-unk'); u.appendChild(h('b', null, t('unknown'))); u.appendChild(W.document.createTextNode(T(b.alt) || String(b.type || '')));
    return u;
  }
  /* buildBlock(b, ctx) → {el, go} — el bloque completo según su estado (planned | ready | error | stale) */
  function buildBlock(b, ctx) {
    if (!b || typeof b !== 'object' || typeof b.type !== 'string') return null;
    var reg = REG[b.type];
    if (!reg) { var u = unknownBlock(b); u.setAttribute('data-kg-id', String(b.id || '')); return { el: u, go: null }; }
    var bare = BARE[b.type] || (b.type === 'callout' && b.data && b.data.variant === 'disclaimer');
    var wrap = h(bare ? 'div' : 'section', bare ? 'kg-bare kg-t-' + b.type.replace('.', '-') : 'kg-b kg-t-' + b.type.replace('.', '-'));
    wrap.setAttribute('data-kg-id', String(b.id || ''));
    wrap.setAttribute('data-kg-type', b.type);
    wrap._kgBlock = b;
    var c = Object.assign({}, ctx, { _el: wrap });
    if (b.state === 'planned') {
      wrap.setAttribute('aria-busy', 'true');
      if (!bare && b.title) wrap.appendChild(header(b, c, wrap));
      var sk = skeleton(b); wrap.appendChild(sk);
      return { el: wrap, go: null };
    }
    if (b.state === 'error') {
      if (!bare) wrap.appendChild(header(b, c, wrap));
      var er = h('div', 'kg-err'); er.setAttribute('role', 'alert');
      er.appendChild(h('span', null, '⚠ ' + (T(b.error) || t('err'))));
      if (b.prov && Array.isArray(b.menu) && b.menu.indexOf('refresh') >= 0) er.appendChild(btn('kg-act', '⟳ ' + t('retry'), function () { refine(b, {}, c); }));
      wrap.appendChild(er);
      return { el: wrap, go: null };
    }
    if (!b.data || typeof b.data !== 'object') { var u2 = unknownBlock(b); return { el: u2, go: null }; }
    if (!bare) {
      wrap.setAttribute('aria-label', T(b.title) || b.type);
      if (b.title || b.subtitle) wrap.appendChild(header(b, c, wrap));
    }
    var bd = h('div', 'kg-bd'); wrap.appendChild(bd);
    var made = renderBody(bd, b, c);
    if (!bare) { var ft = footer(b, c); if (ft) wrap.appendChild(ft); }
    return { el: wrap, go: made && typeof made.go === 'function' ? made.go : null };
  }
  function replaceBlock(oldEl, b, ctx) {
    var x = buildBlock(b, Object.assign({}, ctx, { reduced: true }));
    if (!x || !oldEl.parentNode) return null;
    oldEl.parentNode.replaceChild(x.el, oldEl);
    if (x.go) x.go(true);
    return x.el;
  }

  // varias fichas seguidas (company.card) se dibujan en UNA fila, como "Las 3 primeras" del prototipo
  function groupCards(blocks) {
    var out = [], run = [];
    var flush = function () { if (run.length >= 2) out.push({ cards: run }); else run.forEach(function (b) { out.push(b); }); run = []; };
    blocks.forEach(function (b) {
      if (b && b.type === 'company.card' && (b.state === 'ready' || b.state === 'stale')) run.push(b);
      else { flush(); out.push(b); }
    });
    flush();
    return out;
  }
  function cardRow(list, ctx) {
    var wrap = h('section', 'kg-b kg-t-cards'), g = h('div', 'kg-cards');
    var first = list[0];
    wrap.setAttribute('data-kg-id', String(first.id || ''));
    wrap.setAttribute('data-kg-type', 'company.card');
    var hd = h('div', 'kg-hd');
    hd.appendChild(h('span', 'kg-ti', list.map(function (b) { return T(b.title) || (b.data.company && b.data.company.label) || ''; }).join(' · ')));
    hd.appendChild(h('span', 'kg-sp'));
    wrap.appendChild(hd);
    var gos = [];
    list.forEach(function (b, i) {
      var cell = h('div'); cell.setAttribute('data-kg-id', String(b.id || '')); cell.setAttribute('data-kg-type', 'company.card');
      var r = renderBody(cell, b, Object.assign({}, ctx, { _el: cell, _inRow: true, _i: i }));
      while (cell.firstChild) g.appendChild(cell.firstChild);
      if (r && r.go) gos.push(r.go);
    });
    wrap.appendChild(g);
    var ft = h('div', 'kg-ft'), seen = {};
    list.forEach(function (b) { (b.sources || []).forEach(function (id) { if (!seen[id]) { seen[id] = 1; ft.appendChild(srcChip(id, ctx, '', blockAsOf(b))); } }); });
    if (ft.firstChild) wrap.appendChild(ft);
    return { el: wrap, go: function (inst) { gos.forEach(function (f) { f(inst); }); } };
  }

  /* validación otra vez en el cliente (lo mínimo: versión, catálogo, topes) */
  function validEnv(env) {
    return !!(env && typeof env === 'object' && env.v === V && Array.isArray(env.blocks));
  }
  function textOf(env) { return (env.blocks || []).some(function (b) { return b && b.type === 'text'; }); }

  /* renderAnswer(host, env, opts) — pinta el sobre completo dentro de host (se vacía) */
  function renderAnswer(host, env, opts) {
    if (!host || !validEnv(env)) return null;
    opts = opts || {};
    // gráficos aún no cargados: se pinta lo que ya se sabe pintar y, al llegar los archivos, el MISMO sobre de nuevo
    if (needsExtras(env)) {
      loadExtras().then(function (ok) {
        var r = host.querySelector && host.querySelector('.kg-root');
        if (ok && r && r._kgEnv === env) renderAnswer(host, env, Object.assign({}, opts, { silent: true }));
      });
    }
    ensureStyles(); wireTip(); wirePop(); registerExplains(); watchLang();
    var ctx = mkCtx(opts, env);
    host.textContent = '';
    var rootEl = h('div', 'kg-root kos-themed');
    rootEl.setAttribute('aria-busy', 'true');
    if (ctx.reduced) rootEl.classList.add('kg-rm');
    try { var w0 = host.clientWidth || 0; if (opts.compact != null ? opts.compact : (w0 > 0 && w0 < 520)) { ctx.compact = true; rootEl.classList.add('kg-compact'); } } catch (e) {}
    rootEl._kgEnv = env; rootEl._kgOpts = opts;
    ctx.root = rootEl;
    host.appendChild(rootEl);
    var blocks = env.blocks.slice(0, MAX_BLOCKS);
    if (!textOf(env) && opts.answer) blocks.unshift({ id: 'kg-answer', type: 'text', state: 'ready', data: { md: String(opts.answer), lang: env.lang || lang() } });
    var built = [];
    groupCards(blocks).forEach(function (b) {
      var x = b && b.cards ? cardRow(b.cards, ctx) : buildBlock(b, ctx);
      if (!x) return;
      rootEl.appendChild(x.el); built.push(x);
    });
    // entrada escalonada (55–90 ms, máx. 6) y luego el dibujo de cada gráfico; reducir movimiento = todo ya
    var vis = 0;
    built.forEach(function (x) {
      if (ctx.reduced) { if (x.go) x.go(true); return; }
      var i = Math.min(vis++, 5), delay = i * 70;
      x.el.classList.add('kg-in'); x.el.style.animationDelay = delay + 'ms';
      if (x.go) setTimeout(function () { try { x.go(false); } catch (e) {} }, delay + 140);
    });
    rootEl.setAttribute('aria-busy', 'false');
    if (!opts.silent) announce(summary(blocks));
    watchSize(rootEl, host);
    return rootEl;
  }
  /* update(host, partial) — bloques nuevos por seq: reemplaza el del mismo id (esqueleto → listo) o lo añade */
  function update(host, part) {
    if (!host || !validEnv(part)) return null;
    ensureStyles(); wireTip(); wirePop();
    var rootEl = host.querySelector('.kg-root');
    if (!rootEl) return renderAnswer(host, part, { silent: true });
    var since = rootEl._kgSeq || 0, ctx = mkCtx(rootEl._kgOpts || {}, part);
    ctx.root = rootEl; ctx.compact = rootEl.classList.contains('kg-compact');
    part.blocks.slice(0, MAX_BLOCKS).forEach(function (b) {
      if (!b || (b.seq != null && b.seq <= since)) return;
      var old = null, kids = rootEl.querySelectorAll('[data-kg-id]');
      for (var i = 0; i < kids.length; i++) if (kids[i].getAttribute('data-kg-id') === String(b.id)) { old = kids[i]; break; }
      var x = buildBlock(b, Object.assign({}, ctx, { reduced: true }));
      if (!x) return;
      if (old && old.parentNode === rootEl) rootEl.replaceChild(x.el, old); else rootEl.appendChild(x.el);
      if (x.go) x.go(true);
    });
    if (typeof part.seq === 'number') rootEl._kgSeq = Math.max(since, part.seq);
    return rootEl;
  }
  /* renderBlock(el, block, opts) — un bloque suelto (ventana 📌, historial) */
  function renderBlock(el, block, opts) {
    if (!el || !block) return null;
    opts = opts || {};
    ensureStyles(); wireTip(); wirePop(); registerExplains();
    var ctx = mkCtx(opts, null);
    if (opts.facts) ctx.facts = opts.facts;
    el.textContent = '';
    var rootEl = h('div', 'kg-root kos-themed' + (opts.pinned ? ' kg-win' : '') + (opts.compact ? ' kg-compact' : ''));
    if (opts.compact) ctx.compact = true;
    if (ctx.reduced) rootEl.classList.add('kg-rm');
    ctx.root = rootEl;
    rootEl._kgFacts = ctx.facts;            // relang() repinta con las MISMAS fuentes (si no, el chip pierde su nombre)
    el.appendChild(rootEl);
    var x = buildBlock(block, ctx);
    if (!x) return null;
    rootEl.appendChild(x.el);
    if (x.go) x.go(ctx.reduced || !!opts.instant);
    return rootEl;
  }

  /* ══ compacto por ancho (ResizeObserver, < 520 px) + idioma ══ */
  function rerender(rootEl) {
    var host = rootEl.parentNode, env = rootEl._kgEnv;
    if (!host || !env) return;
    var o = Object.assign({}, rootEl._kgOpts || {}, { reduced: true, silent: true });
    delete o.compact;
    renderAnswer(host, env, o);
  }
  function watchSize(rootEl, host) {
    if (typeof W.ResizeObserver !== 'function' || (rootEl._kgOpts && rootEl._kgOpts.compact != null)) return;
    var last = rootEl.classList.contains('kg-compact'), tm = null;
    var ro = new W.ResizeObserver(function () {
      var w = host.clientWidth || 0; if (!w) return;
      var c = w < 520;
      if (c === last) return;
      last = c;
      clearTimeout(tm); tm = setTimeout(function () { ro.disconnect(); if (rootEl.isConnected !== false) rerender(rootEl); }, 120);
    });
    try { ro.observe(host); } catch (e) {}
  }
  var _langObs = null, _lastLang = null;
  function relang() {
    var cur = lang(); if (cur === _lastLang) return; _lastLang = cur;
    closePop();
    var roots = W.document.querySelectorAll('.kg-root');
    for (var i = 0; i < roots.length; i++) {
      var r = roots[i];
      if (r._kgEnv) rerender(r);
      else { var b = r.querySelector('[data-kg-id]'); if (b && b._kgBlock && r.parentNode) renderBlock(r.parentNode, b._kgBlock, { compact: r.classList.contains('kg-compact'), pinned: r.classList.contains('kg-win'), reduced: true, facts: r._kgFacts || null }); }
    }
  }
  function watchLang() {
    if (_lastLang == null) _lastLang = lang();
    if (_langObs || typeof W.MutationObserver !== 'function' || !W.document.documentElement) return;
    _langObs = new W.MutationObserver(function () { relang(); });
    try { _langObs.observe(W.document.documentElement, { attributes: true, attributeFilter: ['lang'] }); } catch (e) {}
  }

  /* ══ 📌 fijar: el MISMO JSON se vuelve ventana (FLIP desde el bloque) ══ */
  var NATIVE = { 'company.card': function (b) { var id = entId(b.data && b.data.company); return id ? ['glance', { id: id }] : null; },
    'graph.mini': function (b) { var id = entId(b.data && b.data.center); return id ? ['supplychain', { id: id }] : null; },
    'impact.cascade': function (b) { var id = entId(b.data && b.data.origin); return id ? ['sim', { id: id, kind: 'collapse' }] : null; },
    comparison: function (b) { var e = (b.data && b.data.entities) || []; return entId(e[0]) && entId(e[1]) ? ['compare', { a: e[0].id, b: e[1].id }] : null; } };
  function hasKind(k) {
    try {
      if (W.KhipuOSWin && W.KhipuOSWin.kinds && W.KhipuOSWin.kinds[k]) return true;
      var ck = W.BixbyCockpit; if (ck && typeof ck.hasKind === 'function') return !!ck.hasKind(k);
    } catch (e) {}
    return k === 'sim' || k === 'compare';
  }
  function flip(fromRect, toEl, reduced) {
    if (!fromRect || !toEl || reduced || typeof toEl.animate !== 'function') return;
    var to = toEl.getBoundingClientRect(); if (!to.width || !to.height) return;
    try {
      toEl.animate([{ transformOrigin: '0 0', transform: 'translate(' + (fromRect.left - to.left) + 'px,' + (fromRect.top - to.top) + 'px) scale(' +
        Math.max(.2, fromRect.width / to.width) + ',' + Math.max(.2, fromRect.height / to.height) + ')', opacity: .55 },
      { transformOrigin: '0 0', transform: 'none', opacity: 1 }], { duration: 380, easing: 'cubic-bezier(.2,0,0,1)' });
    } catch (e) {}
  }
  function pin(block, fromEl, pinBtn) {
    if (!block) return false;
    var rect = null; try { rect = fromEl && fromEl.getBoundingClientRect ? fromEl.getBoundingClientRect() : null; } catch (e) {}
    var reduced = reducedPref() || !!(fromEl && fromEl.closest && fromEl.closest('.kg-rm'));
    var ck = W.BixbyCockpit, nat = NATIVE[block.type] && NATIVE[block.type](block);
    var rootEl = fromEl && fromEl.closest ? fromEl.closest('.kg-root') : null;
    var req = (rootEl && rootEl._kgOpts && rootEl._kgOpts.reqId) || 'kg';
    var wid = null;
    if (ck && typeof ck.stage === 'function') {
      if (ck.isOpen && !ck.isOpen() && ck.open) { try { ck.open(); } catch (e) {} }
      try {
        if (nat && hasKind(nat[0])) wid = ck.stage(nat[0], nat[1]);
        else wid = ck.stage('genui', { id: String(req).slice(0, 40) + ':' + String(block.id || 'b'), block: block,
          facts: rootEl ? mkCtx({}, rootEl._kgEnv).facts : null });
      } catch (e) { wid = null; }
    }
    if (wid == null) { sheet(block, rootEl); }
    else {
      var win = null; try { win = W.document.querySelector('.kd-win[data-id="' + String(wid).replace(/["\\]/g, '') + '"]'); } catch (e) {}
      if (win) flip(rect, win, reduced);
    }
    if (pinBtn) { pinBtn.classList.add('on'); pinBtn.setAttribute('aria-pressed', 'true'); tip(pinBtn, t('pinned')); }
    return true;
  }
  // sin Khipus OS: hoja inferior propia (móvil / vista clásica)
  function sheet(block, rootEl) {
    var d = W.document, scrim = h('div', 'kg-scrim'), sh = h('div', 'kg-sheet kos-themed');
    sh.setAttribute('role', 'dialog'); sh.setAttribute('aria-label', T(block.title) || t('pinned'));
    sh.appendChild(h('div', 'grab'));
    var hd = h('div', 'kg-hd'); hd.appendChild(h('span', 'kg-ti', '📌 ' + (T(block.title) || ''))); hd.appendChild(h('span', 'kg-sp'));
    var close = function () { if (sh.parentNode) sh.parentNode.removeChild(sh); if (scrim.parentNode) scrim.parentNode.removeChild(scrim); d.removeEventListener('keydown', onKey); };
    var onKey = function (e) { if (e.key === 'Escape') close(); };
    hd.appendChild(btn('kg-ic', '✕', close, lang() === 'en' ? 'Close' : 'Cerrar'));
    sh.appendChild(hd);
    var body = h('div'); sh.appendChild(body);
    scrim.addEventListener('click', close); d.addEventListener('keydown', onKey);
    d.body.appendChild(scrim); d.body.appendChild(sh);
    renderBlock(body, block, { compact: true, pinned: true, instant: true, facts: rootEl ? mkCtx({}, rootEl._kgEnv).facts : null });
  }
  // la ventana 📌 'genui' (cola de arranque de Khipus OS: sirve antes o después de cockpit.js)
  (W.__kosKindQueue = W.__kosKindQueue || []).push(['genui', {
    icon: '📌', es: 'Bloque', en: 'Block', multi: true,
    title: function (arg) { var x = arg && arg.block && arg.block.title; return x ? T(x) : ''; },
    render: function (body, arg) { if (arg && arg.block) renderBlock(body, arg.block, { compact: true, pinned: true, facts: arg.facts || null }); }
  }]);

  /* ══ vista accesible / CSV (PURA) ══ */
  function toTable(b) {
    if (!b || !b.data || (b.state !== 'ready' && b.state !== 'stale')) return null;
    var reg = REG[b.type];
    if (reg && reg.toTable) { try { return reg.toTable(b); } catch (e) { return null; } }
    return null;
  }

  /* ══ registro ══ */
  function register(type, spec) {
    if (TYPES.indexOf(type) < 0 || !spec || typeof spec.render !== 'function') return false;
    REG[type] = spec; return true;
  }
  function catalog() { return TYPES.filter(function (k) { return !!REG[k]; }); }
  function enabled() { try { return W.localStorage.getItem(FLAG) === '1'; } catch (e) { return false; } }
  function setEnabled(on) {
    try { if (on) W.localStorage.setItem(FLAG, '1'); else W.localStorage.removeItem(FLAG); } catch (e) {}
    var en = enabled(); if (en) loadExtras();
    return en;
  }
  /* ══ carga PEREZOSA de gráficos y formas (§8: ≤ 90 KB al abrir la app): genui_charts.js y genui_shapes.js solo se
     descargan y se interpretan con la bandera encendida (o al llegar el primer sobre). Mismo origen y la misma
     ?v= que genui.js (CSP: script-src 'self'); en orden (async=false) porque se registran en este archivo. ══ */
  var EXTRAS = ['genui_charts.js', 'genui_shapes.js'], _extras = null;
  var _selfSrc = (function () { try { var c = W.document && W.document.currentScript; return c && c.src ? String(c.src) : ''; } catch (e) { return ''; } })();
  function extrasReady() { return !!(REG['chart.line'] && REG['geo.mini']); }
  function loadExtras() {
    if (extrasReady()) return Promise.resolve(true);
    if (_extras) return _extras;
    var d = W.document;
    if (!d || !d.createElement || !(d.head || d.body)) return Promise.resolve(false);
    var m = /^(.*\/)genui\.js(\?[^#]*)?/.exec(_selfSrc), base = m ? m[1] : 'engine/', q = m && m[2] ? m[2] : '';
    _extras = new Promise(function (res) {
      var left = EXTRAS.length, done = function () { if (--left <= 0) { if (!extrasReady()) _extras = null; res(extrasReady()); } };
      EXTRAS.forEach(function (f) {
        var sc = d.createElement('script'); sc.src = base + f + q; sc.async = false;
        sc.onload = done; sc.onerror = done;
        (d.head || d.body).appendChild(sc);
      });
    });
    return _extras;
  }
  function needsExtras(env) {
    return !extrasReady() && ((env && env.blocks) || []).some(function (b) { return b && typeof b.type === 'string' && TYPES.indexOf(b.type) >= 0 && !REG[b.type]; });
  }
  var _ref = null;
  // "Preguntar sobre esto": la próxima pregunta lleva context.ref_block (10 min, una vez)
  function takeRef() { var r = _ref; _ref = null; return r && Date.now() - r.ts < 600000 ? { id: r.id, prov: r.prov } : null; }

  /* ══ RENDERIZADORES BÁSICOS (los gráficos están en genui_charts.js; formas/mapa en genui_shapes.js) ══ */
  // spark compartido (tiles, ficha): solo dibuja los puntos que llegaron; huecos = null
  function spark(series, ctx) {
    var pts = (series && Array.isArray(series.points)) ? series.points : [];
    var vals = pts.map(function (p) { return Array.isArray(p) && typeof p[1] === 'number' && isFinite(p[1]) ? p[1] : null; });
    var ok = vals.filter(function (v) { return v != null; });
    if (ok.length < 2) return null;
    var mn = Math.min.apply(null, ok), mx = Math.max.apply(null, ok), n = vals.length, Wd = 200, Hd = 30, d = '', on = false;
    vals.forEach(function (v, i) {
      if (v == null) { on = false; return; }
      d += (on ? 'L' : 'M') + (i * Wd / Math.max(1, n - 1)).toFixed(1) + ' ' + (Hd - 3 - (v - mn) / (mx - mn || 1) * (Hd - 6)).toFixed(1) + ' ';
      on = true;
    });
    var s = sv('svg', { viewBox: '0 0 ' + Wd + ' ' + Hd, preserveAspectRatio: 'none', 'aria-hidden': 'true' }, 'kg-spk');
    var p = sv('path', { d: d.trim(), pathLength: '1', 'stroke-dasharray': '1', 'stroke-dashoffset': '1' });
    s.appendChild(p);
    s._kgDraw = function (inst) { draw(p, inst, 650); };
    return s;
  }
  // dibujo de una línea (stroke-dashoffset 1 → 0); reducir movimiento = ya dibujada
  function draw(p, inst, dur) {
    if (!p) return;
    if (inst || typeof p.animate !== 'function') { p.setAttribute('stroke-dashoffset', '0'); return; }
    try {
      var an = p.animate([{ strokeDashoffset: 1 }, { strokeDashoffset: 0 }], { duration: dur || 600, easing: 'cubic-bezier(.4,0,.2,1)', fill: 'forwards' });
      an.onfinish = function () { p.setAttribute('stroke-dashoffset', '0'); try { an.cancel(); } catch (e) {} };
    } catch (e) { p.setAttribute('stroke-dashoffset', '0'); }
  }
  // cuenta hacia arriba SOLO para conteos y puntajes (nunca precios, capitalización ni P&L); el valor final ya
  // está en aria-label desde el primer fotograma
  var COUNTABLE = { count: 1, score: 1 };
  function countUp(el, v, unit, o, inst) {
    var final = fmt(v, unit, o);
    el.setAttribute('aria-label', final);
    if (inst || !COUNTABLE[unit] || typeof v !== 'number' || !(v > 0) || typeof W.requestAnimationFrame !== 'function') { el.textContent = final; return; }
    var t0 = null, dur = 600, k10 = Math.pow(10, (o && o.precision) || 0);
    var step = function (now) {
      if (t0 == null) t0 = now;
      var k = Math.min(1, (now - t0) / dur);
      var cur = Math.round(v * (1 - Math.pow(1 - k, 3)) * k10) / k10;
      // nunca un «0» provisional (§7.4, §14.2): mientras el conteo redondeado sea 0 se queda «…»
      el.textContent = k >= 1 ? final : (cur > 0 ? fmt(cur, unit, o) : '…');
      if (k < 1) W.requestAnimationFrame(step);
    };
    el.textContent = '…';
    W.requestAnimationFrame(step);
  }
  function bigFig(f, ctx) {
    var vm = vmFigure(f), el = h('div', 'kg-big kg-n' + (vm.na ? ' na' : ''));
    if (vm.na) { el.textContent = '—'; el.setAttribute('aria-label', t('nodata')); return { el: el, go: null }; }
    // una cifra que cuenta hacia arriba empieza en «…» (no en el valor final para luego saltar a 0); con
    // movimiento reducido se escribe ya la final
    var counts = COUNTABLE[f.unit] && !(ctx && ctx.reduced) && typeof f.v === 'number' && f.v > 0;
    var num = h('span', null, counts ? '…' : vm.pre + vm.num); el.appendChild(num);
    if (vm.suf.trim()) el.appendChild(h('small', null, vm.suf.trim()));
    el.setAttribute('aria-label', vm.text);
    tip(el, vm.text, (vm.src ? vm.src : '') + (vm.as_of ? ' · ' + when(vm.as_of) : ''));
    // conteos y puntajes cuentan hacia arriba (no llevan sufijo); precios, %, capitalización y P&L aparecen tal cual
    var o = { precision: f.precision, currency: f.currency };
    return { el: el, go: COUNTABLE[f.unit] ? function (inst) { countUp(num, f.v, f.unit, o, inst); } : null };
  }
  function deltaEl(f) {
    var vm = vmFigure(f); if (vm.na) return null;
    var up = f.v > 0, dn = f.v < 0;
    var el = h('div', 'kg-d kg-n' + (up ? ' kg-up' : dn ? ' kg-dn' : ''), (up ? '▲ ' : dn ? '▼ ' : '') + parts(f.v, f.unit, { precision: f.precision, sign: true }).text);
    tip(el, vm.src, vm.as_of ? t('asof') + ': ' + vm.as_of : '');
    return el;
  }

  // UN ayudante para todo lo que se puede «abrir» con el teclado: role, tabindex, clic y Enter/Espacio
  function linkify(el, fn, role) {
    if (!el || typeof fn !== 'function') return el;
    if (role !== null) el.setAttribute('role', role || 'link');
    el.setAttribute('tabindex', '0');
    el.addEventListener('click', fn);
    el.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') { e.preventDefault(); fn(e); }
    });
    return el;
  }
  // 1) texto (markdown-lite + marcas deterministas del servidor)
  register('text', {
    render: function (el, b, ctx) {
      var d = b.data || {}, md = String(d.md || '').slice(0, 4000);
      var marks = (Array.isArray(d.marks) ? d.marks : []).filter(function (m) {
        return m && typeof m.s === 'number' && typeof m.e === 'number' && m.e > m.s && (m.kind === 'entity' || m.kind === 'fact' || m.kind === 'unverified');
      }).slice(0, 60).sort(function (a, b2) { return b2.s - a.s; });
      // las marcas usan posiciones en UNIDADES UTF-16 (las de String.prototype.slice; el servidor convierte cuando
      // hay emojis fuera del plano básico): se insertan marcadores privados de la posición más alta a la más baja
      var used = [], low = function (k) { var c = md.charCodeAt(k); return c >= 0xDC00 && c <= 0xDFFF; };
      marks.forEach(function (m, i) {
        if (m.s < 0 || m.e > md.length) return;
        if (low(m.s) || (m.e < md.length && low(m.e))) return;          // nunca partir un par sustituto
        if (used.some(function (u) { return !(m.e <= u.s || m.s >= u.e); })) return;
        used.push(m);
        md = md.slice(0, m.s) + '\uE000' + String.fromCharCode(0xE100 + i) + '\uE001' + md.slice(m.s, m.e) + '\uE002' + md.slice(m.e);
      });
      var box = h('div', 'kg-text kc-body');
      el.appendChild(box);
      mdInto(box, md);
      // marcadores → chips (DOM seguro: se recorren los nodos de texto)
      if (used.length) wireMarks(box, marks, ctx);
      return null;
    },
    toTable: function (b) { return { columns: [t('text')], rows: [[String((b.data || {}).md || '')]] }; }
  });
  function wireMarks(box, marks, ctx) {
    var tw = W.document.createTreeWalker(box, 4, null), nodes = [], n;
    while ((n = tw.nextNode())) if (/[\uE000-\uE002]/.test(n.nodeValue)) nodes.push(n);
    var stack = [];
    nodes.forEach(function (node) {
      var s = node.nodeValue, frag = W.document.createDocumentFragment(), buf = '', target = frag;
      var flush = function () { if (buf) { target.appendChild(W.document.createTextNode(buf)); buf = ''; } };
      for (var i = 0; i < s.length; i++) {
        var c = s.charAt(i);
        if (c === '\uE000') {
          flush();
          var mi = s.charCodeAt(i + 1) - 0xE100; i += 2;
          var m = marks[mi] || {}, sp = h('span', 'kg-mk kg-mk-' + (m.kind || 'x'));
          markWire(sp, m, ctx);
          target.appendChild(sp); stack.push(target); target = sp;
        } else if (c === '\uE002') { flush(); target = stack.pop() || frag; }
        else if (c === '\uE001') { /* nada */ } else buf += c;
      }
      flush();
      node.parentNode.replaceChild(frag, node);
    });
  }
  function markWire(sp, m, ctx) {
    if (m.kind === 'entity' && m.ref && ID_RX.test(m.ref)) {
      linkify(sp, function () { runAction({ kind: 'open_dossier', entity: { id: m.ref, label: m.ref } }, null, ctx); });
    } else if (m.kind === 'fact' && m.ref && /^F\d{1,3}$/.test(m.ref)) {
      linkify(sp, function () { highlightFact(ctx.root, m.ref); }, 'button');
    } else if (m.kind === 'unverified') {
      tip(sp, lang() === 'en' ? '⚠ figure not verified against the data' : '⚠ cifra no verificada con los datos');
    }
  }
  function highlightFact(rootEl, id) {
    if (!rootEl) return;
    var els = rootEl.querySelectorAll('[data-kg-fact]');
    for (var i = 0; i < els.length; i++) {
      var on = els[i].getAttribute('data-kg-fact') === id;
      els[i].classList.toggle('hi', on);
      if (on && els[i].scrollIntoView) try { els[i].scrollIntoView({ block: 'nearest', behavior: reducedPref() ? 'auto' : 'smooth' }); } catch (e) {}
    }
  }

  // 2) cifras grandes con delta ▲▼, mini-sparkline, «?» y su fuente
  register('metric.tiles', {
    render: function (el, b, ctx) {
      var items = ((b.data || {}).items || []).slice(0, 6), g = h('div', 'kg-tiles'), gos = [];
      g.style.setProperty('--kg-cols', String(Math.min(4, Math.max(1, items.length))));
      items.forEach(function (it) {
        var f = it.value || {}, vm = vmFigure(f), tl = h('div', 'kg-tile');
        var lb = h('div', 'l'); lb.appendChild(h('span', null, T(it.label)));
        var q = qBtn(vm.explain || (vm.na ? 'genui_na' : '')); if (q) lb.appendChild(q);
        if (vm.live) lb.appendChild(tip(h('span', 'kg-live'), t('live')));
        tl.appendChild(lb);
        var bf = bigFig(f, ctx); tl.appendChild(bf.el); if (bf.go) gos.push(bf.go);
        var dl = it.delta ? deltaEl(it.delta) : null;
        if (dl) tl.appendChild(dl);
        else if (vm.na) tl.appendChild(h('div', 'kg-d', vm.reason));
        if (it.sub) tl.appendChild(h('div', 'kg-d', T(it.sub)));
        if (it.spark) { var sp = spark(it.spark, ctx); if (sp) { tl.appendChild(sp); gos.push(sp._kgDraw); } }
        var ch = figChip(f, ctx); if (ch) tl.appendChild(ch);
        g.appendChild(tl);
      });
      el.appendChild(g);
      return { go: function (inst) { gos.forEach(function (fn) { fn(inst); }); } };
    },
    toTable: function (b) {
      return { columns: [t('metric'), t('value'), t('change'), t('source'), t('asof')], rows: ((b.data || {}).items || []).map(function (it) {
        var f = it.value || {}, vm = vmFigure(f);
        return [T(it.label), vm.na ? '— (' + vm.reason + ')' : vm.text, it.delta ? fmtFig(it.delta, { sign: true }) : '', vm.src, vm.as_of || ''];
      }) };
    },
    height: function (b, w) { var n = ((b.data || {}).items || []).length; return 70 + (w < 520 && n > 2 ? 2 : 1) * 110; }
  });

  // 8) ficha de empresa
  function linkLine(label, list) {
    if (!Array.isArray(list) || !list.length) return null;
    var p = h('div', 'kg-cc-l'); p.appendChild(h('b', null, label));
    p.appendChild(W.document.createTextNode(list.slice(0, 5).map(function (x) { return (x.entity && x.entity.label) || ''; }).filter(Boolean).join(' · ')));
    return p;
  }
  register('company.card', {
    render: function (el, b, ctx) {
      var d = b.data || {}, co = d.company || {}, cc = h('div', 'kg-cc'), gos = [];
      var top = h('div', 'kg-cc-top');
      top.appendChild(h('div', 'kg-cc-lg', String(co.label || '?').split(/\s+/).filter(Boolean).slice(0, 2).map(function (w) { return w.charAt(0); }).join('').toUpperCase()));
      var nm = h('div'); nm.style.minWidth = '0';
      nm.appendChild(h('div', 'kg-cc-n', co.label || ''));
      var role = [co.symbol, d.market_state === 'closed' ? t('marketClosed') : d.market_state].filter(Boolean).join(' · ');
      if (d.structure) role = T(d.structure) + (role ? ' · ' + role : '');
      if (role) nm.appendChild(h('div', 'kg-cc-r', role));
      top.appendChild(nm); cc.appendChild(top);
      var fl = h('div', 'kg-cc-f kg-n');
      [['price', t('price')], ['change', t('chg')], ['market_cap', t('mcap')], ['nrs', t('nrs')]].forEach(function (k) {
        var f = d[k[0]]; if (!f) return;
        var vm = vmFigure(f), sp = h('span', null, k[1]);
        var v = h('b', vm.na ? null : (k[0] === 'change' ? (f.v > 0 ? 'kg-up' : f.v < 0 ? 'kg-dn' : null) : null),
          vm.na ? '—' : (k[0] === 'change' ? parts(f.v, f.unit, { precision: f.precision, sign: true }).text : vm.text));
        tip(v, vm.na ? vm.reason : vm.text, (vm.src || '') + (vm.as_of ? ' · ' + when(vm.as_of) : ''));
        sp.appendChild(v); fl.appendChild(sp);
      });
      if (fl.firstChild) cc.appendChild(fl);
      if (d.private_valuation && d.private_valuation.value) {
        var pv = vmFigure(d.private_valuation.value), pl = h('div', 'kg-cc-l');
        pl.appendChild(h('b', null, t('privVal'))); pl.appendChild(W.document.createTextNode(pv.text + (d.private_valuation.round ? ' · ' + d.private_valuation.round : '')));
        tip(pl, pv.src, pv.as_of); cc.appendChild(pl);
      }
      if (d.spark) { var s = spark(d.spark, ctx); if (s) { cc.appendChild(s); gos.push(s._kgDraw); } }
      var ls = linkLine(t('suppliers'), d.top_suppliers); if (ls) cc.appendChild(ls);
      var lc = linkLine(t('customers'), d.top_customers); if (lc) cc.appendChild(lc);
      var id = entId(co);
      if (id) {
        var bb = h('div', 'kg-cc-b');
        bb.appendChild(actBtn({ kind: 'open_dossier', entity: co, label: { es: '📊 ' + S.es.dossier, en: '📊 ' + S.en.dossier } }, b, ctx));
        bb.appendChild(actBtn({ kind: 'open_xray', entity: co, label: { es: '🔬 ' + S.es.xray, en: '🔬 ' + S.en.xray } }, b, ctx));
        cc.appendChild(bb);
      }
      el.appendChild(ctx._inRow ? cc : (function () { var g = h('div', 'kg-cards'); g.appendChild(cc); return g; })());
      return { go: function (inst) { gos.forEach(function (fn) { fn(inst); }); } };
    },
    toTable: function (b) {
      var d = b.data || {}, rows = [[t('company'), (d.company || {}).label || '']];
      [['price', t('price')], ['change', t('chg')], ['market_cap', t('mcap')], ['nrs', t('nrs')]].forEach(function (k) {
        if (d[k[0]]) { var vm = vmFigure(d[k[0]]); rows.push([k[1], vm.na ? '— (' + vm.reason + ')' : vm.text]); }
      });
      (d.top_suppliers || []).forEach(function (x) { rows.push([t('suppliers'), (x.entity || {}).label || '']); });
      (d.top_customers || []).forEach(function (x) { rows.push([t('customers'), (x.entity || {}).label || '']); });
      return { columns: [t('metric'), t('value')], rows: rows };
    }
  });

  // 13) avisos: pros/contras (tool = investigación; model = «opinión de Khipu»), aviso, info, sin dato, descargo
  function calloutItems(list, kind) {
    var col = h('div');
    (list || []).slice(0, 5).forEach(function (x) {
      var r = h('div', 'kg-cpi'); r.appendChild(h('span', 'ic', kind === 'good' ? '✓' : '!'));
      var tx = h('span', null, String(x.text || ''));
      (x.facts || []).slice(0, 4).forEach(function (f) { if (/^F\d{1,3}$/.test(f)) tx.appendChild(h('sup', null, '[' + f + ']')); });
      r.appendChild(tx); col.appendChild(r);
    });
    return col;
  }
  register('callout', {
    render: function (el, b, ctx) {
      var d = b.data || {}, v = d.variant;
      if (v === 'pros_cons') {
        var g = h('div', 'kg-cp');
        [['good', '▲', t('pros'), d.pros], ['warn', '▼', t('cons'), d.cons]].forEach(function (c) {
          var box = h('div', 'kg-cpc ' + c[0]), hd = h('div', 'kg-cph'); hd.appendChild(h('span', null, c[1])); hd.appendChild(h('span', null, c[2]));
          box.appendChild(hd); box.appendChild(calloutItems(c[3], c[0])); g.appendChild(box);
        });
        if (d.origin === 'model') { var op = h('div', 'kg-ft'); op.appendChild(h('span', 'kg-op', '✦ ' + t('opinion'))); el.appendChild(g); el.appendChild(op); return null; }
        el.appendChild(g); return null;
      }
      if (v === 'disclaimer') { var dc = h('div', 'kg-disc'); dc.appendChild(h('span', null, 'ⓘ')); dc.appendChild(h('span', null, T(d.text))); el.appendChild(dc); return null; }
      var bx = h('div', 'kg-box ' + (v === 'warning' || v === 'info' || v === 'unavailable' ? v : 'info'));
      bx.setAttribute('role', v === 'warning' ? 'alert' : 'note');
      bx.appendChild(h('span', null, v === 'warning' ? '⚠' : v === 'unavailable' ? '—' : 'ⓘ'));
      var tx = h('div');
      if (d.text) tx.appendChild(h('div', null, T(d.text)));
      if (Array.isArray(d.items) && d.items.length) { var ul = h('ul'); d.items.slice(0, 5).forEach(function (x) { ul.appendChild(h('li', null, String(x.text || ''))); }); tx.appendChild(ul); }
      bx.appendChild(tx);
      if (d.origin === 'model') bx.appendChild(h('span', 'kg-op', '✦ ' + t('opinion')));
      el.appendChild(bx);
      return null;
    },
    toTable: function (b) {
      var d = b.data || {}, rows = [];
      (d.pros || []).forEach(function (x) { rows.push([t('pros'), x.text]); });
      (d.cons || []).forEach(function (x) { rows.push([t('cons'), x.text]); });
      (d.items || []).forEach(function (x) { rows.push([d.variant, x.text]); });
      if (d.text) rows.push([d.variant, T(d.text)]);
      return { columns: [t('item'), t('text')], rows: rows };
    }
  });

  // 16) fila final de botones (≤ 4; solo abrir o sugerir)
  register('actions', {
    render: function (el, b, ctx) {
      var row = h('div', 'kg-acts');
      ((b.data || {}).items || []).slice(0, 4).forEach(function (a) {
        var x = actBtn(a, b, ctx, 'kg-chip'); if (x) row.appendChild(x);
      });
      el.appendChild(row);
      return null;
    }
  });

  // 17) fuentes [F#] con su hora; siempre al final
  register('sources', {
    render: function (el, b, ctx) {
      var box = h('div', 'kg-srcs'); box.setAttribute('aria-label', t('sources'));
      box.appendChild(h('span', null, t('sources') + ':'));
      ((b.data || {}).items || []).slice(0, 12).forEach(function (it) {
        var s = h('span', 'kg-si');
        if (it.id) { s.setAttribute('data-kg-fact', it.id); s.appendChild(h('b', null, it.id + ' ')); }
        var u = href(it.url);
        if (u) { var a = h('a', null, it.label || u); a.setAttribute('href', u); a.setAttribute('target', '_blank'); a.setAttribute('rel', 'noopener noreferrer'); s.appendChild(a); }
        else s.appendChild(W.document.createTextNode(it.label || ''));
        if (it.as_of) s.appendChild(W.document.createTextNode(' · ' + when(it.as_of)));
        tip(s, (it.tool ? it.tool + ' · ' : '') + (it.label || ''), t('asof') + ': ' + (it.as_of || '') + (it.published ? ' · ' + it.published : ''));
        box.appendChild(s);
      });
      el.appendChild(box);
      return null;
    },
    toTable: function (b) {
      return { columns: ['F#', t('source'), t('asof'), 'URL'], rows: ((b.data || {}).items || []).map(function (it) { return [it.id || '', it.label || '', it.as_of || '', it.url || '']; }) };
    }
  });

  // 7) tabla: texto, entidad, número (con su unidad), fecha, insignia; ordenar por columna; 8 en línea + «Ver todo»
  function cellText(c, v) {
    if (v == null) return '—';
    if (c.kind === 'number') return typeof v === 'number' ? fmt(v, (c.values || {}).unit, { currency: (c.values || {}).currency }) : '—';
    if (c.kind === 'entity') return (v && v.label) || String(v);
    if (c.kind === 'date') return typeof v === 'string' ? when(v) : '';
    if (typeof v === 'object') return T(v);
    return String(v);
  }
  register('table', {
    render: function (el, b, ctx) {
      var d = b.data || {}, cols = (d.columns || []).slice(0, 8), rows = (d.rows || []).slice(0, 50);
      var inl = Math.max(1, Math.min(8, d.inline_rows || 8)), all = false, sortK = null, dir = 1;
      var wrap = h('div', 'kg-tbw'), tbl = h('table', 'kg-tb'), thead = h('thead'), tr = h('tr'), tbody = h('tbody');
      cols.forEach(function (c) {
        var th = h('th', c.kind === 'number' || c.align === 'end' ? 'end' : null); th.setAttribute('scope', 'col');
        var sb = btn(null, T(c.label), function () { dir = sortK === c.key ? -dir : 1; sortK = c.key; paint(); });
        th.appendChild(sb);
        if (c.kind === 'number' && c.values && c.values.explain) { var q = qBtn(c.values.explain); if (q) th.appendChild(q); }
        tr.appendChild(th);
      });
      thead.appendChild(tr); tbl.appendChild(thead); tbl.appendChild(tbody); wrap.appendChild(tbl); el.appendChild(wrap);
      var more = null;
      function paint() {
        var list = rows.slice();
        if (sortK) {
          var c0 = cols.filter(function (c) { return c.key === sortK; })[0] || {};
          list.sort(function (a, z) {
            var x = a[sortK], y = z[sortK];
            if (c0.kind === 'number') return ((x == null ? -Infinity : x) - (y == null ? -Infinity : y)) * dir;
            return cellText(c0, x).localeCompare(cellText(c0, y)) * dir;
          });
          Array.prototype.forEach.call(thead.querySelectorAll('th'), function (th, i) { th.setAttribute('aria-sort', cols[i].key === sortK ? (dir > 0 ? 'ascending' : 'descending') : 'none'); });
        }
        tbody.textContent = '';
        (all ? list : list.slice(0, inl)).forEach(function (r) {
          var row = h('tr');
          cols.forEach(function (c, i) {
            var v = r[c.key], td = h('td', (c.kind === 'number' || c.align === 'end' ? 'end ' : '') + (i === 0 ? 'm' : ''));
            if (c.kind === 'entity' && v && entId(v)) {
              var e = linkify(h('span', 'kg-ent', v.label || v.id), function () { runAction({ kind: 'open_dossier', entity: v }, b, ctx); });
              td.appendChild(e);
            } else if (c.kind === 'badge' && v != null) td.appendChild(h('span', 'kg-badge', cellText(c, v)));
            else { td.textContent = cellText(c, v); if (c.kind === 'number') td.classList.add('kg-n'); }
            if (c.kind === 'number' && c.values) tip(td, cellText(c, v), (c.values.src || '') + ' · ' + when(c.values.as_of));
            row.appendChild(td);
          });
          tbody.appendChild(row);
        });
        if (rows.length > inl) {
          if (!more) { more = btn('kg-act', '', function () { all = !all; paint(); }); more.style.marginTop = '8px'; el.appendChild(more); }
          more.textContent = all ? t('less') : t('seeAll') + ' (' + rows.length + ')';
        }
      }
      paint();
      return null;
    },
    toTable: function (b) {
      var d = b.data || {}, cols = (d.columns || []).slice(0, 8);
      return { columns: cols.map(function (c) { return T(c.label); }), rows: (d.rows || []).map(function (r) { return cols.map(function (c) { return cellText(c, r[c.key]); }); }) };
    }
  });

  // 11) línea de tiempo (date_known:false = «desde que se rastrea»); enlaces con safeUrl
  var TL_IC = { news: '📰', event: '⚡', filing: '📄', earnings: '💵', link: '🔗', launch: '🚀', decision: '⚖' };
  register('timeline', {
    render: function (el, b, ctx) {
      var list = h('div', 'kg-tl');
      ((b.data || {}).items || []).slice(0, 20).forEach(function (it) {
        var r = h('div', 'kg-tli');
        r.appendChild(h('div', 'kg-tld kg-n', it.date_known === false ? t('since') : when(it.date)));
        var tx = h('div', 'kg-tlt'), u = href(it.url);
        var ttl = (TL_IC[it.kind] || '•') + ' ' + T(it.title);
        if (u) { var a = h('a', null, ttl); a.setAttribute('href', u); a.setAttribute('target', '_blank'); a.setAttribute('rel', 'noopener noreferrer'); tip(a, T(it.title), t('ext')); tx.appendChild(a); }
        else tx.appendChild(h('span', null, ttl));
        var m = h('div', 'kg-tlm'); m.appendChild(h('span', null, it.src || ''));
        if (it.fact) m.appendChild(h('span', null, it.fact));
        if (it.entity && entId(it.entity)) {
          m.appendChild(linkify(h('span', 'kg-ent', it.entity.label), function () { runAction({ kind: 'open_dossier', entity: it.entity }, b, ctx); }));
        }
        if (typeof it.lat === 'number' && typeof it.lon === 'number') {
          var g = linkify(h('span', 'kg-ent', '🌐'), function () { runAction({ kind: 'open_world', lat: it.lat, lon: it.lon }, b, ctx); });
          g.setAttribute('aria-label', lang() === 'en' ? 'Open in World Monitor' : 'Abrir en World Monitor');
          tip(g, lang() === 'en' ? 'Open in World Monitor' : 'Abrir en World Monitor'); m.appendChild(g);
        }
        tx.appendChild(m); r.appendChild(tx); list.appendChild(r);
      });
      el.appendChild(list);
      return null;
    },
    toTable: function (b) {
      return { columns: [t('date'), t('title'), t('source'), 'URL'], rows: ((b.data || {}).items || []).map(function (it) {
        return [it.date_known === false ? t('since') : String(it.date || ''), T(it.title), it.src || '', it.url || ''];
      }) };
    }
  });

  W.KhipuGenUI = {
    V: V, TYPES: TYPES.slice(),
    enabled: enabled, setEnabled: setEnabled, loadExtras: loadExtras, extrasReady: extrasReady, renderAnswer: renderAnswer, update: update, renderBlock: renderBlock,
    register: register, toTable: toTable, pin: pin, catalog: catalog, relang: relang, takeRef: takeRef, ensureStyles: ensureStyles,
    // piezas compartidas con genui_charts.js / genui_shapes.js (y las pruebas en node)
    _u: { h: h, sv: sv, add: add, tip: tip, btn: btn, linkify: linkify, T: T, t: t, S: S, lang: lang, fmt: fmt, parts: parts, vmFigure: vmFigure, when: when,
      isOld: isOld, spark: spark, draw: draw, countUp: countUp, runAction: runAction, actBtn: actBtn, entId: entId, href: href, qBtn: qBtn,
      skeleton: skeleton, height: height, summary: summary, validEnv: validEnv, IMG_RX: IMG_RX, ACTION_KINDS: ACTION_KINDS, WINDOWS: WINDOWS },
    _vm: { figure: vmFigure, fmt: fmt, parts: parts, summary: summary }
  };
  // con la bandera ya encendida, los gráficos se piden al arrancar (llegan mucho antes que la primera respuesta)
  if (enabled()) { try { setTimeout(loadExtras, 0); } catch (e) {} }
})(typeof window !== 'undefined' ? window : globalThis);
