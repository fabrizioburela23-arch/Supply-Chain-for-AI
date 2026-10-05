/* ============================================================================
   engine/localcharts.js — CANVAS: ROUTER DE INTENCIÓN + GRÁFICOS SIN IA
   (Etapa G 2026-07-11 · Etapa I 2026-07-12 · ROUTER 2026-10-02)

   Feedback de Fabrizio (2026-10): "las respuestas que no usan IA no están muy
   bien … que haya un criterio de qué tipo de gráfico mostrar y que se integre
   a la IA cuando la consulta no pueda ser respondida de forma precisa".

   ANTES: ~13 regex sueltos; el primero que encontraba una palabra clave
   respondía aunque ignorara el resto de la pregunta ("margen de Nvidia" →
   top márgenes de TODO el grafo; "relación riesgo y margen" → lista de
   márgenes; "P/E de Nvidia vs AMD" → comparación genérica sin P/E).

   AHORA — 3 pasos:
   1) parse(q) → { intent, entities, metrics, timeframe, groupBy, country,
      chart, unknown[], weak[] }. Cada palabra de la consulta debe quedar
      "entendida" (empresa resuelta con KhipuResolve EXACTO, métrica,
      agrupación, país, periodo, verbo o palabra vacía). Lo que sobra = unknown.
   2) confidence 0-1 + reason. Solo se responde LOCAL si ≥ 0.75: todas las
      empresas resueltas exacto, la métrica existe en nuestros datos y la
      intención es una que sabemos dibujar. Si no → IA con `hints` (la
      intención/entidades/métricas viajan en el body de /api/canvas/generate).
   3) Si la IA no está disponible → honest(q, err): tarjeta bilingüe "no puedo
      responder esto con precisión sin IA" + la respuesta parcial CORRECTA más
      cercana (nunca un gráfico por defecto sin relación).

   CRITERIO DE TIPO DE GRÁFICO (el MISMO en server.py → core/canvas_spec.py):
   ┌──────────────────────────────┬──────────────────────────────────────────┐
   │ intención                    │ gráfico                                  │
   ├──────────────────────────────┼──────────────────────────────────────────┤
   │ compare (2-6 ítems, 1 métr.) │ bar (barras ordenadas, color por empresa)│
   │ compare (2-6 ítems, n métr.) │ grouped (barras agrupadas) · radar si se │
   │                              │ pide · table si >6 ítems                 │
   │ trend (tiempo)               │ line · bar si son montos anuales que     │
   │                              │ pueden ser negativos (capex, FCF, crec.%)│
   │ rank (top N / por grupo)     │ bar horizontal ordenada                  │
   │ composition (parte del todo) │ donut si ≤6 porciones · treemap si más   │
   │ distribution                 │ histogram                                │
   │ relationship (2 métricas)    │ scatter                                  │
   │ single_metric (1 número)     │ kpi                                      │
   │ profile (ficha 1 empresa)    │ kpi (varias tarjetas)                    │
   │ cross (país × sector)        │ heatmap                                  │
   │ detalle multi-atributo       │ table                                    │
   └──────────────────────────────┴──────────────────────────────────────────┘

   NUNCA inventar datos: solo NODES / NODE_META / computeNRS / LINKS /
   MKT (cliente) y /api/candles · /api/findossier · /api/crypto (servidor).

   API pública (NO romper): window.KhipuLocalCharts.try(query) → spec|null
   (solo si la confianza es alta) · .tryAsync(query) → Promise<spec|null> ·
   .clearCache() · .prefetch(). NUEVO: .route(q) · .decide(q) · .hints(q) ·
   .honest(q, errMsg) → Promise<spec notice>.
   ============================================================================ */
(function () {
  'use strict';

  var PAL = ['#60a5fa', '#34d399', '#f59e0b', '#f87171', '#a78bfa', '#38bdf8', '#fb923c', '#4ade80'];
  var RED = '#f87171', AMB = '#f59e0b', GRN = '#34d399', BLU = '#60a5fa';
  var ACCEPT = 0.75;   // umbral de confianza para responder sin IA

  /* ── i18n local (regla bilingüe ES/EN — window.LANG / localStorage eco_lang) ── */
  var I18 = {
    es: {
      gen: 'Generando con IA…', genHint: 'suele tardar unos segundos · quedará en caché',
      mRev: 'Ingresos', mMgn: 'Margen', mNrs: 'Riesgo NRS', mEmp: 'Empleados', mCap: 'Capitalización',
      mFnd: 'Año de fundación', mCnt: 'Empresas', mSup: 'Proveedores', mCli: 'Clientes', mPrice: 'Precio',
      riskOf: 'Riesgo de', riskBd: 'de qué se compone el NRS', lowerBetter: 'más alto = más riesgo',
      cryT: 'Top {n} cripto por capitalización', cryS: 'Miles de millones USD · verde = subió en 24 h',
      cryHT: '{l} — precio, {p}', cryHCap: 'El historial gratuito llega a 12 meses (pediste {p}).', srcCryH: 'Fuente: CoinGecko (precio diario en USD)',
      topBy: 'Top {n} por {m}', botBy: '{n} con menor {m}', oldest: 'Las {n} más antiguas', newest: 'Las {n} más recientes',
      bySector: '{m} por sector', byCountry: '{m} por país', avgOf: 'promedio', sumOf: 'suma', cntOf: 'conteo',
      cmpS1: 'Valores reales del catálogo · ordenado de mayor a menor',
      cmpSn: 'Cada bloque es una métrica con sus valores reales · NRS: más alto = más riesgo',
      radarT: 'Perfil comparado', radarS: '0-100 relativo entre las comparadas · más grande = mejor (Seguridad = 100 − NRS)',
      axRev: 'Ingresos', axMgn: 'Margen', axSafe: 'Seguridad', axEmp: 'Empleados', axCap: 'Cap.',
      colCompany: 'Empresa', colTicker: 'Ticker', colNrs: 'NRS riesgo', colMgn: 'Margen %',
      colCap: 'Cap $B', colCountry: 'País', colFounded: 'Fundada', colRev: 'Ingresos $B',
      colQty: 'Cantidad', colPrice: 'Precio', colValue: 'Valor',
      provOf: 'Proveedores de', cliOf: 'Clientes de', pcS: '{k} de {n} · peso de criticidad del vínculo (1-5)',
      scT: '{y} vs {x}', scS: '{n} empresas con ambos datos · cada punto es una empresa',
      histT: 'Distribución: {m}', histS: '{n} empresas con dato · cuántas caen en cada rango',
      tmCapT: 'Capitalización por sector', tmRevT: 'Ingresos por sector', tmCntT: 'Empresas por sector', tmEmpT: 'Empleados por sector',
      tmS: 'Peso de cada parte en el total · {n} empresas con dato', ctryCompT: 'Empresas por país',
      heatT: 'Riesgo NRS promedio: país × sector', heatS: 'Países con más empresas · celda vacía = sin empresas',
      portT: 'Mi cartera', portS: 'posiciones · peso según precio en vivo', portEmpty: 'Todavía no tienes posiciones guardadas.',
      portEmptyHint: 'Agrega posiciones en Mercado → Mi cartera y vuelve a pedir el gráfico.',
      lineT: '{l} — precio, {p}', lineS: '{a} en el periodo · {d0} → {d1}', relT: 'Precio relativo (base 100), {p}',
      relS: '100 = precio al inicio del periodo · compara el rendimiento, no el precio',
      kpiRank: 'puesto #{r} de {n} con dato', kpiSect: 'promedio de su sector: {v}', kpiNone: 'sin dato en el catálogo',
      profT: '{l} — ficha rápida', profS: 'Datos del catálogo · NRS calculado en vivo',
      todayT: '{l} — precio actual', todayS: 'vs cierre anterior',
      fundSrc: 'estados anuales', exclOut: '{n} valor(es) atípico(s) del catálogo excluido(s)',
      srcCat: 'Fuente: datos EN VIVO (Yahoo/Finnhub: capitalización, margen, ingresos, empleados) donde ya llegaron; si no, catálogo Khipus', srcNrs: 'NRS calculado en vivo sobre el grafo',
      srcLinks: 'Fuente: vínculos del grafo de suministro', srcPx: 'Fuente: precios de mercado en vivo',
      srcFund: 'Fuente: estados financieros anuales ({s})', srcCry: 'Fuente: mercado cripto en vivo',
      srcPort: 'Fuente: tu cartera (este navegador) · precios en vivo',
      noAiT: 'No puedo responder esto con precisión sin IA',
      noAiPartial: 'Lo más cercano que sí puedo mostrar con datos reales:',
      noAiNone: 'No hay una respuesta parcial confiable con los datos locales.',
      aiDown: 'La IA no está disponible ahora',
      noProv: 'no hay ningún proveedor de IA configurado en el servidor', rateLim: 'se alcanzó el límite de consultas; prueba en unos minutos',
      rsReason: 'La pregunta pide explicar o proyectar («por qué», «qué pasaría si»): eso requiere IA.',
      rsMetric: 'No tengo «{m}» en los datos de la app sin IA.',
      rsUnknown: 'No entendí con precisión: «{w}».',
      rsWeak: 'No estoy seguro de qué empresa es «{w}». ¿Quisiste decir {s}?',
      rsMissing: 'Faltan empresas reconocibles para comparar.',
      rsNoData: 'El catálogo no tiene datos suficientes para esto.',
      rsHistory: 'No guardo el historial de «{m}» en el tiempo.',
      rsVague: 'La pregunta es demasiado abierta para un gráfico preciso sin IA.',
      tryLike: 'Prueba, por ejemplo: «{e}».',
      cntUnit: 'empresas',
    },
    en: {
      gen: 'Generating with AI…', genHint: 'usually takes a few seconds · will be cached',
      mRev: 'Revenue', mMgn: 'Margin', mNrs: 'NRS risk', mEmp: 'Employees', mCap: 'Market cap',
      mFnd: 'Year founded', mCnt: 'Companies', mSup: 'Suppliers', mCli: 'Customers', mPrice: 'Price',
      riskOf: 'Risk of', riskBd: 'what the NRS is made of', lowerBetter: 'higher = riskier',
      cryT: 'Top {n} crypto by market cap', cryS: 'USD billions · green = up in 24h',
      cryHT: '{l} — price, {p}', cryHCap: 'Free history goes back 12 months (you asked for {p}).', srcCryH: 'Source: CoinGecko (daily price in USD)',
      topBy: 'Top {n} by {m}', botBy: '{n} with the lowest {m}', oldest: 'The {n} oldest', newest: 'The {n} newest',
      bySector: '{m} by sector', byCountry: '{m} by country', avgOf: 'average', sumOf: 'total', cntOf: 'count',
      cmpS1: 'Real catalog values · sorted high to low',
      cmpSn: 'Each block is one metric with its real values · NRS: higher = riskier',
      radarT: 'Compared profile', radarS: '0-100 relative among compared · bigger = better (Safety = 100 − NRS)',
      axRev: 'Revenue', axMgn: 'Margin', axSafe: 'Safety', axEmp: 'Employees', axCap: 'Cap.',
      colCompany: 'Company', colTicker: 'Ticker', colNrs: 'NRS risk', colMgn: 'Margin %',
      colCap: 'Cap $B', colCountry: 'Country', colFounded: 'Founded', colRev: 'Revenue $B',
      colQty: 'Qty', colPrice: 'Price', colValue: 'Value',
      provOf: 'Suppliers of', cliOf: 'Customers of', pcS: '{k} of {n} · link criticality weight (1-5)',
      scT: '{y} vs {x}', scS: '{n} companies with both values · each dot is a company',
      histT: 'Distribution: {m}', histS: '{n} companies with data · how many fall in each range',
      tmCapT: 'Market cap by sector', tmRevT: 'Revenue by sector', tmCntT: 'Companies by sector', tmEmpT: 'Employees by sector',
      tmS: 'Each part\'s share of the total · {n} companies with data', ctryCompT: 'Companies by country',
      heatT: 'Average NRS risk: country × sector', heatS: 'Countries with most companies · empty cell = no companies',
      portT: 'My portfolio', portS: 'positions · weight by live price', portEmpty: 'You have no saved positions yet.',
      portEmptyHint: 'Add positions in Market → My portfolio and ask for the chart again.',
      lineT: '{l} — price, {p}', lineS: '{a} over the period · {d0} → {d1}', relT: 'Relative price (base 100), {p}',
      relS: '100 = price at the start of the period · compares performance, not price',
      kpiRank: 'rank #{r} of {n} with data', kpiSect: 'sector average: {v}', kpiNone: 'no data in the catalog',
      profT: '{l} — quick profile', profS: 'Catalog data · NRS computed live',
      todayT: '{l} — current price', todayS: 'vs previous close',
      fundSrc: 'annual statements', exclOut: '{n} catalog outlier(s) excluded',
      srcCat: 'Source: LIVE data (Yahoo/Finnhub: market cap, margin, revenue, employees) where available; otherwise the Khipus catalog', srcNrs: 'NRS computed live on the graph',
      srcLinks: 'Source: supply-graph links', srcPx: 'Source: live market prices',
      srcFund: 'Source: annual financial statements ({s})', srcCry: 'Source: live crypto market',
      srcPort: 'Source: your portfolio (this browser) · live prices',
      noAiT: 'I can\'t answer this precisely without AI',
      noAiPartial: 'The closest thing I can show with real data:',
      noAiNone: 'There is no reliable partial answer with local data.',
      aiDown: 'AI is not available right now',
      noProv: 'no AI provider is configured on the server', rateLim: 'the request limit was reached; try again in a few minutes',
      rsReason: 'The question asks to explain or project ("why", "what if"): that needs AI.',
      rsMetric: 'I don\'t have "{m}" in the app\'s non-AI data.',
      rsUnknown: 'I didn\'t precisely understand: "{w}".',
      rsWeak: 'I\'m not sure which company "{w}" is. Did you mean {s}?',
      rsMissing: 'Not enough recognizable companies to compare.',
      rsNoData: 'The catalog doesn\'t have enough data for this.',
      rsHistory: 'I don\'t keep the history of "{m}" over time.',
      rsVague: 'The question is too open-ended for a precise chart without AI.',
      tryLike: 'Try, for example: "{e}".',
      cntUnit: 'companies',
    },
  };
  function L() {
    try { return String(window.LANG || localStorage.getItem('eco_lang') || 'es').slice(0, 2) === 'en' ? 'en' : 'es'; }
    catch (e) { return 'es'; }
  }
  function TT(k, vars) {
    var d = I18[L()] || I18.es;
    var s = d[k] != null ? d[k] : (I18.es[k] != null ? I18.es[k] : k);
    if (vars) Object.keys(vars).forEach(function (v) { s = s.split('{' + v + '}').join(vars[v]); });
    return s;
  }
  var TERM_EN = { 'Geopolítica': 'Geopolitics', 'Cadena': 'Supply chain', 'Margen': 'Margin',
                  'Fundamental': 'Fundamentals', 'Concentración': 'Concentration' };

  /* ── accesos a datos (SOLO lo que el cliente ya tiene) ─────────────────── */
  function nrs(id) { try { var v = (typeof computeNRS === 'function') ? computeNRS(id) : null; return (v != null && isFinite(v)) ? v : null; } catch (e) { return null; } }
  function meta(id) { return (window.NODE_META || {})[id] || {}; }
  function cap(id) { var c = Number(meta(id).mktcap_b); return isFinite(c) && c > 0 ? c : null; }
  // ingresos ($B) de NODE_META.revenue_2025 ("~$21.5B", "$390M"). Solo USD.
  function revB(id) {
    // 2026-10-05: ingresos REALES de los últimos 12 meses si ya llegaron (KhipuLiveFund); si no, el catálogo
    var lv = Number(meta(id).revenue_ttm_usd_b);
    if (isFinite(lv) && lv > 0) return lv;
    var s = String(meta(id).revenue_2025 || '');
    if (!s || /[€¥£]/.test(s)) return null;
    var m = s.match(/\$\s?([\d.,]+)\s?([TBM])/i);
    if (!m) return null;
    var v = parseFloat(m[1].replace(/,/g, ''));
    if (!isFinite(v) || v <= 0) return null;
    var u = m[2].toUpperCase();
    return u === 'T' ? v * 1000 : u === 'M' ? v / 1000 : v;
  }
  // margen del catálogo en %. Valores ≥ 95 % o < −300 % son errores de carga
  // del catálogo (p.ej. 1 = 100 % en una trader de materias primas) → fuera.
  function mgnRaw(n) { return n && n.margin != null && isFinite(n.margin) ? n.margin * 100 : null; }
  function mgn(n) { var v = mgnRaw(n); return v != null && v < 95 && v > -300 ? v : null; }
  function emp(id) { var e = Number(meta(id).employees); return isFinite(e) && e > 0 ? e : null; }
  function fnd(id) { var f = Number(meta(id).founded); return isFinite(f) && f > 1500 && f < 2100 ? f : null; }
  function sectorOf(n) { return (window.CAT_TO_SECTOR || {})[n.cat] || 'cloud_ia'; }
  function sectorLabel(k) { var s = (window.SECTORS9 || {})[k] || {}; return (L() === 'en' ? (s.en || s.label) : s.label) || k; }
  function sectorColor(k) { return ((window.SECTORS9 || {})[k] || {}).color || BLU; }
  function lid(v) { return (typeof v === 'object' && v) ? v.id : v; }
  function nodes() { return window.NODES || []; }
  function byId(id) { return (window.NODE_BY_ID || {})[id] || null; }
  function r1(v) { return Math.round(v * 10) / 10; }

  // ── país canónico: el catálogo mezcla "EEUU", "Estados Unidos (HQ…)", "United States"…
  function norm(s) {
    try { if (window.KhipuResolve && window.KhipuResolve.norm) return window.KhipuResolve.norm(s); } catch (e) {}
    s = String(s == null ? '' : s).toLowerCase();
    try { s = s.normalize('NFD').replace(new RegExp('[\\u0300-\\u036f]', 'g'), ''); } catch (e) {}
    return s.replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim();
  }
  var COUNTRY_CANON = {
    'eeuu': 'EEUU', 'ee uu': 'EEUU', 'estados unidos': 'EEUU', 'united states': 'EEUU', 'usa': 'EEUU', 'us': 'EEUU',
    'china': 'China', 'hong kong': 'Hong Kong', 'taiwan': 'Taiwán', 'japon': 'Japón', 'japan': 'Japón',
    'corea': 'Corea del Sur', 'corea del sur': 'Corea del Sur', 'south korea': 'Corea del Sur', 'korea': 'Corea del Sur',
    'reino unido': 'Reino Unido', 'reinounido': 'Reino Unido', 'united kingdom': 'Reino Unido', 'uk': 'Reino Unido',
    'alemania': 'Alemania', 'germany': 'Alemania', 'francia': 'Francia', 'france': 'Francia',
    'paises bajos': 'Países Bajos', 'paisesbajos': 'Países Bajos', 'netherlands': 'Países Bajos',
    'canada': 'Canadá', 'rusia': 'Rusia', 'russia': 'Rusia', 'suiza': 'Suiza', 'switzerland': 'Suiza',
    'emiratos arabes unidos': 'Emiratos Árabes', 'united arab emirates': 'Emiratos Árabes',
    'sudafrica': 'Sudáfrica', 'south africa': 'Sudáfrica', 'europa': 'Europa', 'restoeuropa': 'Europa', 'eurozone': 'Europa',
    'restomundo': 'Resto del mundo', 'india': 'India', 'israel': 'Israel', 'australia': 'Australia',
    'singapur': 'Singapur', 'singapore': 'Singapur', 'brasil': 'Brasil', 'brazil': 'Brasil', 'italia': 'Italia',
    'espana': 'España', 'spain': 'España', 'irlanda': 'Irlanda', 'suecia': 'Suecia', 'dinamarca': 'Dinamarca',
    'malaysia': 'Malasia', 'malasia': 'Malasia', 'indonesia': 'Indonesia', 'poland': 'Polonia', 'polonia': 'Polonia',
  };
  var EUROPE = { 'Europa': 1, 'Alemania': 1, 'Francia': 1, 'Países Bajos': 1, 'Reino Unido': 1, 'Suiza': 1, 'Italia': 1,
                 'España': 1, 'Irlanda': 1, 'Suecia': 1, 'Dinamarca': 1, 'Polonia': 1, 'Bélgica': 1, 'Finlandia': 1,
                 'Luxemburgo': 1, 'Lituania': 1 };
  function canonCountry(raw) {
    var s = String(raw || '').split(/[(\/—;,]| - /)[0];
    var k = norm(s);
    if (!k) return '—';
    if (COUNTRY_CANON[k]) return COUNTRY_CANON[k];
    return s.trim().replace(/^\w/, function (c) { return c.toUpperCase(); });
  }
  function inCountry(n, want) {
    if (!want) return true;
    var c = canonCountry(n.country);
    return want === 'Europa' ? !!EUROPE[c] : c === want;
  }
  var COUNTRY_EN = { 'EEUU': 'USA', 'Taiwán': 'Taiwan', 'Japón': 'Japan', 'Corea del Sur': 'South Korea', 'Reino Unido': 'UK',
    'Alemania': 'Germany', 'Francia': 'France', 'Países Bajos': 'Netherlands', 'Canadá': 'Canada', 'Rusia': 'Russia',
    'Suiza': 'Switzerland', 'Emiratos Árabes': 'UAE', 'Sudáfrica': 'South Africa', 'Europa': 'Europe',
    'Resto del mundo': 'Rest of world', 'Singapur': 'Singapore', 'Brasil': 'Brazil', 'Italia': 'Italy', 'España': 'Spain',
    'Irlanda': 'Ireland', 'Suecia': 'Sweden', 'Dinamarca': 'Denmark', 'Malasia': 'Malaysia', 'Polonia': 'Poland' };
  function countryLabel(c) { return L() === 'en' ? (COUNTRY_EN[c] || c) : c; }

  /* ══════════════════════════ 1) PARSER ══════════════════════════════════ */

  // métricas: clave → {re (sobre texto normalizado), src, es, en, unit}
  //  src: 'cat' (catálogo cliente) · 'graph' (vínculos) · 'px' (velas) ·
  //       'fund' (estados anuales) · 'none' (no la tenemos sin IA)
  var METRICS = [
    // fundamentales en el tiempo (específicos ANTES que los amplios)
    { k: 'revenue_growth', re: /crecimiento (?:de (?:los |las )?)?(?:ingresos|ventas)|revenue growth|sales growth/, src: 'fund', es: 'Crecimiento de ingresos', en: 'Revenue growth', unit: '%', fbar: true },
    { k: 'capex', re: /\bcapex\b|gasto(?:s)? (?:de|en) capital|inversion(?:es)? (?:de|en) capital|capital expenditures?/, src: 'fund', es: 'Capex (inversión)', en: 'Capex', unit: '$B', bn: true, fbar: true },
    { k: 'fcf', re: /flujo(?: de caja)?(?: libre)?|\bfcf\b|caja libre|free cash(?: flow)?|cash flow/, src: 'fund', es: 'Flujo de caja libre', en: 'Free cash flow', unit: '$B', bn: true, fbar: true },
    { k: 'roe', re: /\broe\b|retorno (?:sobre (?:el )?)?(?:patrimonio|capital)|return on equity/, src: 'fund', es: 'ROE', en: 'Return on equity', unit: '%' },
    { k: 'gross_margin', re: /margen(?:es)? brutos?|gross margins?/, src: 'fund', es: 'Margen bruto', en: 'Gross margin', unit: '%' },
    { k: 'de_ratio', re: /deuda (?:sobre |\/ ?)?(?:capital|patrimonio)|debt (?:to )?equity|apalancamiento|leverage/, src: 'fund', es: 'Deuda / Capital', en: 'Debt / Equity', unit: 'x' },
    { k: 'ev_to_sales', re: /\bev (?:sobre |\/ ?|to )?(?:ventas|sales)\b/, src: 'fund', es: 'EV / Ventas', en: 'EV / Sales', unit: 'x' },
    // NO disponibles sin IA (se reconocen para no confundirlos con otra cosa)
    { k: 'pe', re: /\bp ?e\b|\bper\b|price to earnings|precio ?(?:\/|sobre)? ?beneficio|multiplo(?:s)?(?: de valuacion)?|\bpe ratio\b/, src: 'none', es: 'P/E (precio/beneficio)', en: 'P/E' },
    { k: 'eps', re: /\beps\b|beneficio por accion|earnings per share|\bbpa\b/, src: 'none', es: 'BPA / EPS', en: 'EPS' },
    { k: 'dividend', re: /dividend\w*/, src: 'none', es: 'Dividendos', en: 'Dividends' },
    { k: 'debt', re: /\bdeudas?\b|\bdebt\b|endeudamiento/, src: 'none', es: 'Deuda', en: 'Debt' },
    { k: 'market_share', re: /cuota de mercado|market share|participacion de mercado/, src: 'none', es: 'Cuota de mercado', en: 'Market share' },
    { k: 'volume', re: /\bvolumen\b|\bvolume\b/, src: 'none', es: 'Volumen', en: 'Volume' },
    { k: 'ebitda', re: /\bebitda\b|\bebit\b/, src: 'none', es: 'EBITDA', en: 'EBITDA' },
    { k: 'volatility', re: /volatilidad|volatility|\bbeta\b/, src: 'none', es: 'Volatilidad / beta', en: 'Volatility / beta' },
    { k: 'valuation', re: /valuacion(?:es)?|valoracion(?:es)?|valuations?/, src: 'none', es: 'Valuación', en: 'Valuation' },
    { k: 'profit', re: /\bganancias?\b|beneficio(?:s)? neto|net income|utilidad(?:es)?|\bprofits?\b|earnings/, src: 'none', es: 'Beneficio neto', en: 'Net income' },
    { k: 'growth', re: /\bcrecimiento\b|\bgrowth\b|\bcrece(?:n)?\b/, src: 'none', es: 'Crecimiento', en: 'Growth' },
    // catálogo cliente
    { k: 'nrs', re: /\briesgos?\b|\bnrs\b|\brisk(?:s|iest|y)?\b|fragil\w*|peligros\w*|riesgos[ao]s?|vulnerab\w*|segur[ao]s|safest/, src: 'cat', es: 'Riesgo NRS', en: 'NRS risk', unit: 'NRS' },
    { k: 'margin', re: /\bmargen(?:es)?\b|\bmargins?\b|rentabilidad|profitab\w*/, src: 'cat', es: 'Margen', en: 'Margin', unit: '%' },
    { k: 'mktcap', re: /market ?cap\w*|capitalizacion(?:es)?|valor de mercado|market value|(?:mas|mayores|largest|biggest) (?:grandes?|empresas|companies)|mas grandes|largest|biggest/, src: 'cat', es: 'Capitalización', en: 'Market cap', unit: '$B' },
    { k: 'revenue', re: /\bingresos?\b|\brevenues?\b|\bventas\b|\bsales\b|facturacion|factura/, src: 'cat', es: 'Ingresos', en: 'Revenue', unit: '$B' },
    { k: 'employees', re: /emplead\w*|employees|plantilla|headcount|trabajadores|workers/, src: 'cat', es: 'Empleados', en: 'Employees', unit: '' },
    { k: 'founded', re: /fundad\w*|fundacion|founded|antigu\w*|oldest|mas viejas|newest|mas recientes|mas jovenes/, src: 'cat', es: 'Año de fundación', en: 'Year founded', unit: 'year' },
    { k: 'suppliers', re: /proveedor\w*|suppliers?|abastece\w*/, src: 'graph', es: 'Proveedores', en: 'Suppliers', unit: 'w' },
    { k: 'customers', re: /\bclientes?\b|customers?|compradores|buyers/, src: 'graph', es: 'Clientes', en: 'Customers', unit: 'w' },
    { k: 'price', re: /\bprecios?\b|cotiza\w*|\bprice\b|\bstock\b|\bshares?\b|\bacci(?:o|ó)n(?:es)?\b|velas|candles|\bcuanto vale\b|how much is/, src: 'px', es: 'Precio', en: 'Price', unit: '$' },
  ];
  var MET_BY = {}; METRICS.forEach(function (m) { MET_BY[m.k] = m; });
  function metLabel(k) { var m = MET_BY[k]; return m ? (L() === 'en' ? m.en : m.es) : k; }
  // sustantivo para títulos ("Top 10 por riesgo (NRS)")
  var NOUN = { nrs: ['riesgo (NRS)', 'risk (NRS)'], margin: ['margen', 'margin'], mktcap: ['capitalización', 'market cap'],
               revenue: ['ingresos', 'revenue'], employees: ['empleados', 'employees'], founded: ['antigüedad', 'age'] };
  function metNoun(k) { var n = NOUN[k]; return n ? n[L() === 'en' ? 1 : 0] : metLabel(k).toLowerCase(); }

  var RE = {
    explain: /\bpor ?que\b|\bwhy\b|que pasaria|what (?:would|if|happens)|\bwhat if\b|\bsi (?:china|eeuu|taiwan|\w+) (?:invade|ataca|cae|sube|baja|bloquea|prohibe)|\bexplica\w*|\bexplain\w*|\bimpacto\b|\bimpact\b|\bdeberia\b|\bshould i\b|\bconviene\b|\brecomienda\w*|\brecommend\w*|predic\w*|pronostic\w*|\bforecast\w*|va a (?:subir|bajar)|will (?:it )?(?:rise|fall|go)|\bcausa\w*|\bcause\w*|\bsubio\b|\bbajo\b|\bcayo\b|\bgano\b|\bperdio\b|\bescenario\b|\bscenario\b|\bsimula\w*/,
    distribution: /distribuci\w*|histograma|histogram|distribution|como se reparten los valores/,
    relation: /\brelacion\b|correlaci\w*|relationship|correlat\w*|\bscatter\b|dispersion|tiene que ver/,
    composition: /composicion|\breparto\b|participacion|\bpeso(?:s)?\b|\bshare of\b|\bsplit\b|\bmix\b|desglos\w*|breakdown|\bde que se compone\b|made of|\bpie\b|\btorta\b|\btarta\b|\bdona\b|\bdonut\b|\btreemap\b|cuanto pesa/,
    trend: /evoluci\w*|historic\w*|historial|tendencia|\btrend\w*|over time|a lo largo|en el tiempo|trayectoria|\bserie\b|ultimos?|ultimas?|\blast\b|\bpast\b|\bdesde\b|\bsince\b|\bytd\b|\bpor ano\b|\bper year\b|\banual(?:es)?\b|\bannual\b|year over year|\bha cambiado\b|\bchanged\b/,
    compare: /compar\w*|\bversus\b|\bvs\b|frente a|\bcontra\b|cual (?:tiene|es) (?:mas|mayor|menor|mejor|peor)|which (?:has|is) (?:more|higher|lower|bigger|better|worse)|\bdiferencia\w*|\bdifference\b/,
    rank: /\btop\b|ranking|\brank\w*|\bmayor(?:es)?\b|\bmenor(?:es)?\b|\bmas\b|\bmenos\b|highest|lowest|largest|biggest|smallest|\bbest\b|\bworst\b|\bmejor(?:es)?\b|\bpeor(?:es)?\b|lider\w*|leaders?|\bprincipales\b|\bmain\b|\bmost\b|\bleast\b/,
    asc: /\bmenor(?:es)?\b|\bmenos\b|lowest|smallest|\bleast\b|mas segur\w*|safest|mas recientes|mas jovenes|newest|\bpeor(?:es)? margen|\bbottom\b/,
    today: /\bhoy\b|\btoday\b|\bahora\b|\bnow\b|\bactual\b|\bcurrent\b|en este momento|right now|cuanto vale|how much is/,
    portfolio: /\bcartera\b|portafolio|portfolio|mis posiciones|my positions|mis acciones|my holdings/,
    crypto: /\bcriptos?\b|\bcryptos?\b|criptomonedas?|cryptocurrenc\w*|\bbitcoin\b|\bbtc\b|\bethereum\b/,
    bySector: /por sector(?:es)?|by sectors?|per sector|\bsectores\b|\bsectors\b|por categorias?|by categor\w*|\bcategorias\b|categories/,
    byCountry: /por pais(?:es)?|by countr\w*|per country|\bpaises\b|\bcountries\b|por region(?:es)?|by region/,
  };
  // pedido explícito de tipo de gráfico
  var CHART_WORDS = [
    ['radar', /\bradar\b|\barana\b|tela de arana|perfil comparad\w*|spider/],
    ['treemap', /\btreemap\b|mapa de (?:sectores|capital|arbol)/],
    ['heatmap', /\bheatmap\b|mapa de calor|heat map/],
    ['scatter', /\bscatter\b|dispersion|\bpuntos\b/],
    ['histogram', /histograma|histogram/],
    ['donut', /\bpie\b|\btorta\b|\btarta\b|\bdona\b|\bdonut\b|circular/],
    ['table', /\btabla\b|\btable\b/],
    ['line', /\blinea\b|\bline chart\b|\bline\b/],
    ['bar', /\bbarras?\b|\bbars?\b/],
    ['kpi', /\bkpi\b|\btarjeta\b/],
  ];
  // país / región como FILTRO ("empresas chinas", "japanese companies")
  var COUNTRY_WORDS = [
    ['China', /\bchin(?:a|as|os?|ese)\b/], ['Taiwán', /\btaiwan(?:es|esas?|ese)?\b/],
    ['Japón', /\bjapon(?:es|esas?)?\b|\bjapan(?:ese)?\b/], ['Corea del Sur', /\bcorea(?:nas?)?(?: del sur)?\b|\b(?:south )?korea(?:n)?\b/],
    ['EEUU', /\beeuu\b|\bee uu\b|estados unidos|estadounidenses?|norteamerican\w*|\bamerican(?:as|os)?\b|\busa\b|united states|\bus companies\b/],
    ['Alemania', /\bale?mania\b|\balemanas?\b|\bgerman(?:y)?\b/], ['Francia', /\bfrancia\b|\bfrancesas?\b|\bfrance\b|\bfrench\b/],
    ['Europa', /\beuropa\b|\beuropeas?\b|\beurope(?:an)?\b/], ['India', /\bindia\b|\bindias\b|\bindian\b/],
    ['Israel', /\bisrael(?:ies|i)?\b/], ['Reino Unido', /reino unido|\bbritanicas?\b|\buk\b|\bbritish\b|united kingdom/],
    ['Canadá', /\bcanada\b|\bcanadienses?\b|\bcanadian\b/], ['Australia', /\baustralia(?:nas?|n)?\b/],
    ['Rusia', /\brusia\b|\brusas?\b|\brussia(?:n)?\b/], ['Países Bajos', /paises bajos|\bholanda\b|\bneerlandesas?\b|netherlands|\bdutch\b/],
  ];
  // SECTOR como filtro ("top 5 semiconductores por margen", "empresas de defensa") — 2026-10-05
  var SECTOR_WORDS = [
    [['fabricacion', 'diseno', 'equipos'], /\bsemiconductor(?:es|s)?\b|\bchips?\b|\bchipmakers?\b|\bsemis\b/],
    [['espacio'], /\bespacial(?:es)?\b|\bspace\b|\bdel espacio\b/], [['defensa'], /\bdefensa\b|\bdefen[cs]e\b/],
    [['energia'], /\benergia\b|\benerg(?:y|etic\w*)\b|\bnuclear(?:es)?\b|\butilities\b/],
    [['robotica'], /\brobotica\b|\brobotics?\b|\brobots?\b/],
  ];
  // MATERIAS PRIMAS e ÍNDICES (precio histórico vía /api/candles; futuros de Yahoo) — 2026-10-05
  var COMMODITIES = [
    ['GC=F', 'Oro', 'Gold', /\boro\b|\bgold\b/], ['CL=F', 'Petróleo WTI', 'WTI crude oil', /\bpetroleo\b|\bcrudo\b|\bcrude\b|\boil\b|\bwti\b/],
    ['BZ=F', 'Petróleo Brent', 'Brent crude', /\bbrent\b/], ['HG=F', 'Cobre', 'Copper', /\bcobre\b|\bcopper\b/],
    ['NG=F', 'Gas natural', 'Natural gas', /gas natural|natural gas/], ['SI=F', 'Plata (metal)', 'Silver', /\bsilver\b|plata metal|precio de la plata/],
    ['URA', 'Uranio (ETF URA)', 'Uranium (URA ETF)', /\buranio\b|\buranium\b/],
    ['^GSPC', 'S&P 500', 'S&P 500', /s ?& ?p ?500|\bsp ?500\b|\bs y p 500\b/], ['^IXIC', 'Nasdaq Composite', 'Nasdaq Composite', /\bnasdaq\b/],
    ['^SOX', 'Índice de semiconductores (SOX)', 'Semiconductor index (SOX)', /\bsox\b|indice de semiconductores|semiconductor index/],
  ];
  // timeframe ("90 días", "5 años", "último año", "1y")
  var TF_UNITS = [
    [/^(?:d|dia|dias|day|days)$/, 1], [/^(?:w|sem|semana|semanas|week|weeks)$/, 7],
    [/^(?:m|mes|meses|month|months|mo)$/, 30], [/^(?:a|ano|anos|y|yr|yrs|year|years)$/, 365],
    [/^(?:trimestre|trimestres|quarter|quarters|q)$/, 91],
  ];
  // palabras que NO aportan significado (se descartan sin bajar la confianza)
  var STOP = ('de del la el los las lo un una unos unas y e o u a al en con por para que q cual cuales cuanto cuanta cuantos ' +
    'cuantas es son fue sea esta estan este estos ha han hay mi mis su sus tu tus se me te le les nos entre sobre segun como ' +
    'muy the of and or an in on for to by with is are was what which how much many my our your their its it this that these ' +
    'those also vs versus contra frente across among all todas todos toda todo cada each per sus ellas ellos quien quienes who ' +
    'tiene tienen has have tengo tenemos hace hacen do does can could would please favor porfa gracias thanks ' +
    'grafico grafica graficos graficas graficar graficame chart charts plot plots dibuja dibujame dibujar draw muestra muestrame ' +
    'mostrar mostrame mostra ensename ensena ver veamos dame dime quiero quisiera necesito podrias puedes puede show give display ' +
    'see visualiza visualizar visualizacion genera generar generame hazme haz crea crear create make build arma armame ' +
    'informacion info datos dato numeros cifras data compara comparar comparame comparacion comparativa compare comparison ' +
    'empresa empresas compania companias companies company firmas firms negocios corporaciones catalogo grafo khipus khipu ' +
    'mayor mayores menor menores mas menos highest lowest largest biggest smallest best worst mejor mejores peor peores top ' +
    'ranking rank lider lideres leaders leader principales principal main most least primeras primeros first grandes grande ' +
    'pequenas small alto alta altos altas bajo baja bajos bajas high low big bigger higher lower more less ordenadas sorted ' +
    'por sector sectores sectors categoria categorias category categories pais paises country countries region regiones ' +
    'hoy today ahora now actual actuales current dia dias day days semana semanas week weeks mes meses month months ano anos ' +
    'year years trimestre trimestres quarter quarters ultimo ultimos ultima ultimas last past desde since historico historica ' +
    'historicos historial history evolucion tendencia trend trends tiempo time largo over ytd anual anuales annual serie series ' +
    'momento right periodo period ' +
    'barras barra bars bar linea line radar arana tela treemap mapa calor heatmap heat map scatter dispersion puntos tabla table ' +
    'pie torta tarta dona donut circular histograma histogram kpi tarjeta ' +
    'distribucion distribution reparto composicion participacion peso pesos share split mix desglose breakdown compone made ' +
    'relacion correlacion relationship correlation diferencia difference perfil profile ficha resumen overview summary ' +
    'cuantas cuanto vale valen cotizan cotiza valor precio precios evoluciona cambio cambiado changed ' +
    'mis my mi cartera portafolio portfolio posiciones positions holdings tenencias ' +
    'score puntaje puntuacion indice index metrica metric valores values ' +
    'red network cadena suministro supply chain ia ai ' +
    'promedio promedios media medio average avg mean desglosado desglosada desglosa desglosar componentes components ' +
    'sector semiconductor semiconductores semiconductors chips chip chipmakers').split(/\s+/);
  var STOPSET = {}; STOP.forEach(function (w) { if (w) STOPSET[w] = 1; });

  // resolución EXACTA (score ≥ 82 en KhipuResolve = id/ticker/label/alias exacto)
  function resolveExact(text) {
    try {
      if (window.KhipuResolve && typeof window.KhipuResolve.find === 'function') {
        var r = window.KhipuResolve.find(text);
        if (r && r.node && r.score >= 82) return { node: byId(r.node.id) || r.node, score: r.score };
        return null;
      }
    } catch (e) {}
    // respaldo sin KhipuResolve: id / ticker / label exactos
    var k = norm(text);
    if (!k) return null;
    var hit = nodes().find(function (n) { return norm(n.id) === k || norm(n.mkt) === k || norm(n.label) === k; });
    return hit ? { node: hit, score: 90 } : null;
  }
  function resolveWeak(text) {
    try {
      if (window.KhipuResolve && typeof window.KhipuResolve.find === 'function') {
        var r = window.KhipuResolve.find(text);
        if (r && r.node && r.score >= 55) return { node: byId(r.node.id) || r.node, score: r.score, sugg: (r.suggestions || []).map(function (n) { return n.label; }) };
      }
    } catch (e) {}
    return null;
  }

  function parse(query) {
    var raw = String(query || '');
    var t = ' ' + norm(raw.replace(/\bp\s*\/\s*e\b/ig, ' pe ')) + ' ';
    var P = { query: raw, text: t.trim(), intent: 'other', entities: [], weak: [], metrics: [], unknown: [],
              timeframe: null, groupBy: [], country: null, chart: null, topN: null, asc: false,
              explain: false, portfolio: false, crypto: false, today: false };
    var work = t;   // texto donde se van "consumiendo" las partes entendidas
    function eat(re) { work = work.replace(new RegExp(re.source, 'g'), ' § '); }

    P.explain = RE.explain.test(t);
    P.portfolio = RE.portfolio.test(t);
    P.crypto = RE.crypto.test(t);
    P.today = RE.today.test(t);
    P.asc = RE.asc.test(t);
    if (P.crypto) eat(RE.crypto);
    if (P.explain) eat(RE.explain);

    // métricas (en orden de aparición en la consulta)
    var found = [];
    METRICS.forEach(function (m) {
      var mm = work.match(m.re);
      if (mm) {
        // "margen bruto" no debe contar también como "margen"; "crecimiento de ingresos" no como "ingresos"
        found.push({ k: m.k, at: work.indexOf(mm[0]) });
        eat(m.re);
      }
    });
    found.sort(function (a, b) { return a.at - b.at; });
    P.metrics = found.map(function (f) { return f.k; });

    if (RE.bySector.test(t)) { P.groupBy.push('sector'); eat(RE.bySector); }
    if (RE.byCountry.test(t)) { P.groupBy.push('country'); eat(RE.byCountry); }
    for (var ci = 0; ci < COUNTRY_WORDS.length; ci++) {
      if (COUNTRY_WORDS[ci][1].test(work)) { P.country = COUNTRY_WORDS[ci][0]; eat(COUNTRY_WORDS[ci][1]); break; }
    }
    for (var sw = 0; sw < SECTOR_WORDS.length; sw++) {
      if (SECTOR_WORDS[sw][1].test(work)) { P.sectors = SECTOR_WORDS[sw][0]; eat(SECTOR_WORDS[sw][1]); break; }
    }
    for (var cm = 0; cm < COMMODITIES.length; cm++) {
      if (COMMODITIES[cm][3].test(work)) { P.commodity = { sym: COMMODITIES[cm][0], es: COMMODITIES[cm][1], en: COMMODITIES[cm][2] }; eat(COMMODITIES[cm][3]); break; }
    }
    for (var ch = 0; ch < CHART_WORDS.length; ch++) {
      if (CHART_WORDS[ch][1].test(t)) { P.chart = CHART_WORDS[ch][0]; break; }
    }
    // periodo
    var tf = work.match(/\b(\d{1,4})\s*(d|dias?|days?|w|sem|semanas?|weeks?|m|mes|meses|months?|mo|a|anos?|y|yrs?|years?|trimestres?|quarters?|q)\b/);
    if (tf) {
      var unit = 0;
      TF_UNITS.forEach(function (u) { if (!unit && u[0].test(tf[2])) unit = u[1]; });
      if (unit) { P.timeframe = { days: Math.min(36500, parseInt(tf[1], 10) * unit), label: tf[0].trim() }; work = work.replace(tf[0], ' § '); }
    }
    if (!P.timeframe) {
      if (/(?:ultimo|last|past|este|this) (?:ano|year)|ano pasado|12 meses|\bytd\b/.test(t)) P.timeframe = { days: 365, label: '1y' };
      else if (/(?:ultimo|last|past|este|this) mes|month/.test(t) && /ultimo|last|past|este|this/.test(t)) P.timeframe = { days: 30, label: '1m' };
      else if (/(?:ultima|last|past|esta|this) semana|week/.test(t) && /ultima|last|past|esta|this/.test(t)) P.timeframe = { days: 7, label: '1w' };
    }
    // top N
    var tn = work.match(/\btop\s*(\d{1,2})\b/) || work.match(/\b(\d{1,2})\s+(?:empresas|companias|companies|mayores|menores|primeras|primeros|mas|largest|biggest|principales)\b/) ||
             work.match(/\b(?:las|los|the|top)\s+(\d{1,2})\b/);
    if (tn) { P.topN = Math.max(3, Math.min(25, parseInt(tn[1], 10))); work = work.replace(tn[0], ' § '); }

    // ── empresas: n-gramas (4→1) sobre lo que queda, solo coincidencia EXACTA ──
    var origTokens = {};   // token normalizado → apareció en MAYÚSCULAS (ticker tecleado)
    raw.split(/[^A-Za-z0-9]+/).forEach(function (w) { if (w) origTokens[w.toLowerCase()] = origTokens[w.toLowerCase()] || (w.length >= 2 && w === w.toUpperCase() && /[A-Z]/.test(w)); });
    var segs = work.split('§').map(function (s) { return s.trim().split(' ').filter(Boolean); });
    var seen = {};
    segs.forEach(function (toks) {
      var used = toks.map(function () { return false; });
      for (var size = Math.min(4, toks.length); size >= 1; size--) {
        for (var i = 0; i + size <= toks.length; i++) {
          var span = toks.slice(i, i + size);
          if (used.slice(i, i + size).some(Boolean)) continue;
          if (STOPSET[span[0]] || STOPSET[span[span.length - 1]]) continue;   // "de nvidia" → no
          if (size === 1) {
            var w = span[0];
            if (/^\d+$/.test(w)) continue;
            if (w.length <= 2 && !origTokens[w]) continue;                   // "on", "ai"… solo si se tecleó en MAYÚSCULAS
          }
          var hit = resolveExact(span.join(' '));
          if (hit && hit.node && !seen[hit.node.id]) {
            seen[hit.node.id] = 1;
            P.entities.push({ id: hit.node.id, label: hit.node.label, mkt: hit.node.mkt || null, score: hit.score, at: t.indexOf(' ' + span[0]) });
            for (var u = i; u < i + size; u++) used[u] = true;
          } else if (hit && hit.node) { for (var u2 = i; u2 < i + size; u2++) used[u2] = true; }
        }
      }
      // lo que sobra: palabra vacía → se ignora; lo demás → desconocido (o empresa dudosa)
      toks.forEach(function (w, j) {
        if (used[j] || STOPSET[w] || /^\d+$/.test(w) || w.length <= 1) return;
        if (w.length >= 4) {
          var wk = resolveWeak(w);
          if (wk && wk.node && !seen[wk.node.id] && wk.score >= 60) {
            P.weak.push({ word: w, id: wk.node.id, label: wk.node.label, score: wk.score, sugg: wk.sugg });
            return;
          }
        }
        P.unknown.push(w);
      });
    });
    P.entities.sort(function (a, b) { return a.at - b.at; });

    P.intent = deriveIntent(P, t);
    return P;
  }

  function isFund(k) { return MET_BY[k] && MET_BY[k].src === 'fund'; }
  function deriveIntent(P, t) {
    var nE = P.entities.length, ms = P.metrics;
    if (P.explain) return 'explain';
    if (P.commodity && !nE) return 'trend';
    if (P.crypto) {
      // una moneda concreta con tiempo o "precio" → su historial; lo demás → ranking
      var coinQ = cryptoCoinIn(P.query) || cryptoCoinIn(t);
      return (coinQ && (P.timeframe || RE.trend.test(t) || ms.indexOf('price') >= 0)) ? 'trend' : 'rank';
    }
    if (P.chart === 'heatmap' || (P.groupBy.length >= 2)) return 'cross';
    if (P.chart === 'histogram' || RE.distribution.test(t)) return 'distribution';
    if (P.chart === 'scatter' || RE.relation.test(t) ||
        (ms.length >= 2 && nE < 2 && !P.groupBy.length && !ms.some(isFund) && ms.indexOf('price') < 0 &&
         ms.indexOf('suppliers') < 0 && ms.indexOf('customers') < 0)) return 'relationship';
    if (P.portfolio) return 'composition';
    if (RE.composition.test(t) || P.chart === 'treemap' || P.chart === 'donut' ||
        (P.groupBy.length && ms.length && /^(mktcap|revenue|employees)$/.test(ms[0]) && !RE.rank.test(t))) return 'composition';
    if (ms.indexOf('suppliers') >= 0 || ms.indexOf('customers') >= 0) return 'rank';
    var timeWords = RE.trend.test(t) || (P.timeframe && !P.today);
    if (timeWords || (ms.indexOf('price') >= 0 && !P.today) || (ms.length && ms.every(isFund))) return 'trend';
    if (nE >= 2 || (RE.compare.test(t) && nE >= 1)) return 'compare';
    if (nE === 1) return ms.length ? 'single_metric' : 'profile';
    if (P.groupBy.length || ms.length || RE.rank.test(t) || P.country) return 'rank';
    return 'other';
  }

  /* ═════════════════ 2) CONFIANZA (¿se puede responder sin IA?) ═══════════ */
  function score(P) {
    var conf = 1, reasons = [];
    function hit(v, r) { conf = Math.min(conf, v); reasons.push(r); }
    if (P.intent === 'explain') hit(0.1, 'needs_reasoning');
    if (P.intent === 'other') hit(0.3, 'vague');
    var none = P.metrics.filter(function (k) { return MET_BY[k].src === 'none'; });
    if (none.length) hit(0.2, 'metric_unavailable');
    if (P.unknown.length) hit(Math.max(0.2, 0.7 - 0.15 * (P.unknown.length - 1)), 'unknown_words');
    if (P.weak.length) hit(0.4, 'weak_entity');
    // "compara X con su principal proveedor": la 2ª empresa es una REFERENCIA
    // que no sabemos resolver sin IA
    if ((P.intent === 'compare' || (RE.compare.test(' ' + P.text + ' ') && /^(rank|single_metric|profile)$/.test(P.intent) && P.entities.length === 1)) && P.entities.length < 2 && !P.groupBy.length) hit(0.3, 'missing_entities');
    if (P.intent === 'trend') {
      var noHist = P.metrics.filter(function (k) { return /^(nrs|mktcap|employees|founded|suppliers|customers)$/.test(k); });
      if (noHist.length) hit(0.25, 'no_history');
      if (!P.entities.length && !P.crypto && !P.commodity) hit(0.3, 'missing_entities');
      if (P.entities.length > 4) hit(0.5, 'too_many');
    }
    if (P.intent === 'single_metric' || P.intent === 'profile' || P.intent === 'compare') {
      if (P.metrics.length > 3) hit(0.6, 'too_many');
    }
    return { confidence: Math.round(conf * 100) / 100, reasons: reasons, reason: reasons[0] || 'ok' };
  }

  // tipo de gráfico sugerido por la intención (mismo criterio que el server)
  function chartFor(P) {
    if (P.chart) return P.chart;
    var nE = P.entities.length, nM = P.metrics.length;
    switch (P.intent) {
      case 'compare': return nE > 6 ? 'table' : (nM === 1 ? 'bar' : 'grouped');
      case 'trend': return (nM === 1 && MET_BY[P.metrics[0]] && MET_BY[P.metrics[0]].fbar && nE <= 1) ? 'bar' : 'line';
      case 'rank': return 'bar';
      case 'composition': return 'treemap';
      case 'distribution': return 'histogram';
      case 'relationship': return 'scatter';
      case 'single_metric': return P.metrics[0] === 'nrs' ? 'bar' : 'kpi';
      case 'profile': return 'kpi';
      case 'cross': return 'heatmap';
      default: return 'bar';
    }
  }

  function route(query) {
    var P = parse(query);
    var s = score(P);
    P.confidence = s.confidence; P.reason = s.reason; P.reasons = s.reasons;
    P.suggested = chartFor(P);
    P.local = s.confidence >= ACCEPT;
    return P;
  }

  function hintsOf(P) {
    return {
      v: 2, intent: P.intent, chart: P.suggested,
      entities: P.entities.concat(P.weak).slice(0, 12).map(function (e) { return { id: e.id, label: e.label, mkt: e.mkt || (byId(e.id) || {}).mkt || null }; }),
      metrics: P.metrics.slice(0, 6), timeframe_days: P.timeframe ? P.timeframe.days : null,
      group_by: P.groupBy.slice(0, 2), country: P.country, top_n: P.topN,
      unknown: P.unknown.slice(0, 8), reason: P.reason, confidence: P.confidence,
    };
  }

  /* ═════════════════ 3) CONSTRUCTORES DE SPEC (datos reales) ══════════════ */
  function spec(type, title, subtitle, data, config, source, note) {
    return { type: type, title: title, subtitle: subtitle || '', data: data, config: config || {},
             source: source || TT('srcCat'), engine: 'local', note: note || '' };
  }
  function nrsColor(v) { return v >= 70 ? RED : v >= 40 ? AMB : GRN; }

  // valor de una métrica de catálogo para un nodo
  function getM(k, n) {
    switch (k) {
      case 'nrs': return nrs(n.id);
      case 'margin': return mgn(n);
      case 'mktcap': return cap(n.id);
      case 'revenue': return revB(n.id);
      case 'employees': return emp(n.id);
      case 'founded': return fnd(n.id);
      default: return null;
    }
  }
  function unitOf(k) { return (MET_BY[k] || {}).unit || ''; }
  function srcOf(k) { return k === 'nrs' ? TT('srcCat') + ' · ' + TT('srcNrs') : TT('srcCat'); }
  function pool(P) {
    var ns = nodes();
    if (P.country) ns = ns.filter(function (n) { return inCountry(n, P.country); });
    if (P.sectors && P.sectors.length) ns = ns.filter(function (n) { return P.sectors.indexOf(sectorOf(n)) >= 0; });
    return ns;
  }
  function withCountry(title, P) {
    if (P.sectors && P.sectors.length) title += ' — ' + P.sectors.map(sectorLabel).join(' / ');
    return P.country ? title + ' — ' + countryLabel(P.country) : title;
  }

  // ── rank: top N por métrica (o por grupo) ──
  function buildRank(P) {
    var k = P.metrics[0] || (P.groupBy.length ? 'count' : null);
    if (P.metrics.indexOf('suppliers') >= 0 || P.metrics.indexOf('customers') >= 0) return buildLinks(P);
    if (!k) return null;
    if (P.groupBy.length) return buildGroup(P, k);
    if (P.entities.length >= 2) return buildCompare(P);
    if (P.entities.length === 1) return null;
    if (MET_BY[k] && MET_BY[k].src !== 'cat') return null;
    var asc = P.asc || (k === 'founded' && !/newest|recientes|jovenes/.test(P.text));
    if (k === 'founded') asc = !/newest|recientes|jovenes/.test(P.text);
    var n = P.topN || 10;
    var rows = pool(P).map(function (nd) { return [nd, getM(k, nd)]; }).filter(function (r) { return r[1] != null; });
    if (rows.length < 2) return null;
    var excl = k === 'margin' ? pool(P).filter(function (nd) { return mgnRaw(nd) != null && mgn(nd) == null; }).length : 0;
    rows.sort(function (a, b) { return asc ? a[1] - b[1] : b[1] - a[1]; });
    rows = rows.slice(0, n);
    var title = k === 'founded' ? TT(asc ? 'oldest' : 'newest', { n: rows.length })
      : TT(asc ? 'botBy' : 'topBy', { n: rows.length, m: metNoun(k) });
    return spec('bar', withCountry(title, P),
      (k === 'nrs' ? TT('lowerBetter') + ' · ' : '') + (L() === 'en' ? 'of ' : 'de ') + pool(P).filter(function (nd) { return getM(k, nd) != null; }).length + ' ' + TT('cntUnit') + (L() === 'en' ? ' with data' : ' con dato'),
      rows.map(function (r, i) { return { label: r[0].label, value: k === 'margin' ? r1(r[1]) : (k === 'nrs' ? Math.round(r[1]) : r[1]), color: k === 'nrs' ? nrsColor(r[1]) : sectorColor(sectorOf(r[0])) }; }),
      { unit: unitOf(k), sort: asc ? 'asc' : 'desc' }, srcOf(k), excl ? TT('exclOut', { n: excl }) : '');
  }

  // ── por sector / país: promedio (riesgo, margen) · suma (cap, ingresos, empleados) · conteo ──
  function groupAgg(P, k, dim) {
    var agg = {};
    pool(P).forEach(function (n) {
      var g = dim === 'sector' ? sectorOf(n) : canonCountry(n.country);
      var a = agg[g] = agg[g] || { n: 0, sum: 0, have: 0 };
      a.n++;
      if (k !== 'count') { var v = getM(k, n); if (v != null) { a.sum += v; a.have++; } }
    });
    var mode = k === 'count' ? 'count' : (/^(nrs|margin|founded)$/.test(k) ? 'avg' : 'sum');
    var rows = Object.keys(agg).map(function (g) {
      var a = agg[g];
      var v = mode === 'count' ? a.n : mode === 'avg' ? (a.have ? a.sum / a.have : null) : (a.have ? a.sum : null);
      return { g: g, v: v, n: a.n, have: a.have };
    }).filter(function (r) { return r.v != null && (mode !== 'avg' || r.have >= 2); });
    return { rows: rows, mode: mode };
  }
  function buildGroup(P, k) {
    var dim = P.groupBy[0];
    var G = groupAgg(P, k, dim);
    if (G.rows.length < 2) return null;
    G.rows.sort(function (a, b) { return b.v - a.v; });
    var rows = G.rows.slice(0, dim === 'country' ? (P.topN || 12) : 20);
    var mLab = k === 'count' ? TT('mCnt') : metLabel(k);
    var modeLab = TT(G.mode === 'avg' ? 'avgOf' : G.mode === 'sum' ? 'sumOf' : 'cntOf');
    return spec('bar', withCountry(TT(dim === 'sector' ? 'bySector' : 'byCountry', { m: mLab }), P),
      modeLab + ' · ' + G.rows.reduce(function (s, r) { return s + (G.mode === 'count' ? r.n : r.have); }, 0) + ' ' + TT('cntUnit') +
        (dim === 'country' && G.rows.length > rows.length ? ' · top ' + rows.length : ''),
      rows.map(function (r) {
        return { label: dim === 'sector' ? sectorLabel(r.g) : countryLabel(r.g),
                 value: G.mode === 'avg' ? r1(r.v) : Math.round(r.v * 10) / 10,
                 color: dim === 'sector' ? sectorColor(r.g) : (k === 'nrs' ? nrsColor(r.v) : BLU) };
      }), { unit: k === 'count' ? '' : unitOf(k) }, srcOf(k));
  }

  // ── composición: parte de un todo → donut (≤6) / treemap ──
  function buildComposition(P) {
    if (P.portfolio) return buildPortfolio(P);
    var k = P.metrics[0];
    if (P.entities.length === 1 && (!k || k === 'nrs')) return buildNrsBreakdown(P.entities[0]);
    if (P.entities.length >= 2 && k && MET_BY[k].src === 'cat') {
      // "peso de la capitalización entre Nvidia, AMD e Intel"
      var items = P.entities.map(function (e) { var n = byId(e.id); return n ? [n, getM(k, n)] : null; }).filter(function (r) { return r && r[1] != null && r[1] > 0; });
      if (items.length < 2 || !/^(mktcap|revenue|employees)$/.test(k)) return null;
      return spec(items.length <= 6 ? 'donut' : 'treemap', metLabel(k) + ': ' + items.map(function (r) { return r[0].label; }).join(' · '),
        L() === 'en' ? 'Share of the combined total' : 'Participación en el total combinado',
        items.map(function (r, i) { return { label: r[0].label, value: r1(r[1]), color: PAL[i % PAL.length] }; }), { unit: unitOf(k) }, srcOf(k));
    }
    var dim = P.groupBy[0] || 'sector';
    var kk = k && /^(mktcap|revenue|employees)$/.test(k) ? k : (k ? null : 'count');
    if (!kk) return null;
    var G = groupAgg(P, kk, dim);
    if (G.rows.length < 2) return null;
    G.rows.sort(function (a, b) { return b.v - a.v; });
    var rows = G.rows, other = 0;
    if (rows.length > 12) { other = rows.slice(11).reduce(function (s, r) { return s + r.v; }, 0); rows = rows.slice(0, 11); }
    var data = rows.map(function (r, i) {
      return { label: dim === 'sector' ? sectorLabel(r.g) : countryLabel(r.g), value: Math.round(r.v * 10) / 10,
               color: dim === 'sector' ? sectorColor(r.g) : PAL[i % PAL.length] };
    });
    if (other > 0) data.push({ label: L() === 'en' ? 'Others' : 'Otros', value: Math.round(other * 10) / 10, color: '#64748b' });
    var title = dim === 'country' ? TT('ctryCompT') : TT({ mktcap: 'tmCapT', revenue: 'tmRevT', employees: 'tmEmpT', count: 'tmCntT' }[kk]);
    var nHave = G.rows.reduce(function (s, r) { return s + (kk === 'count' ? r.n : r.have); }, 0);
    return spec(data.length <= 6 && P.chart !== 'treemap' ? 'donut' : 'treemap', withCountry(title, P),
      TT('tmS', { n: nHave }), data, { unit: kk === 'count' ? '' : unitOf(kk) }, srcOf(kk));
  }

  function buildNrsBreakdown(e) {
    if (typeof window.computeNRSBreakdown !== 'function') return null;
    var bd = null;
    try { bd = window.computeNRSBreakdown(e.id); } catch (er) {}
    if (!bd || !bd.terms || !bd.terms.length) return null;
    var en = L() === 'en';
    return spec('bar', TT('riskOf') + ' ' + e.label + ': NRS ' + Math.round(bd.total) + '/100',
      TT('riskBd') + ' · ' + TT('lowerBetter'),
      bd.terms.map(function (tm) {
        var k = en ? (TERM_EN[tm.key] || tm.key) : tm.key;
        return { label: k + ' (máx ' + tm.max + ')' + (tm.detail ? ' — ' + tm.detail : ''), value: r1(tm.val), color: tm.hot ? RED : BLU, max: tm.max };
      }), { unit: '', sort: 'none' }, TT('srcCat') + ' · ' + TT('srcNrs'));
  }

  // ── comparación de 2-6 empresas ──
  var CMP_DEFAULT = ['revenue', 'margin', 'mktcap', 'nrs', 'employees'];
  function buildCompare(P) {
    var comps = P.entities.map(function (e) { return byId(e.id); }).filter(Boolean);
    if (comps.length < 2) return null;
    var mets = P.metrics.filter(function (k) { return MET_BY[k] && MET_BY[k].src === 'cat'; });
    if (P.metrics.length && !mets.length) return null;     // pidió una métrica que no es de catálogo (la resuelve async/IA)
    var names = comps.map(function (n) { return n.label; });
    if (P.chart === 'radar' || (!mets.length && P.chart === 'radar')) { var rs = radarSpec(comps.slice(0, 5)); if (rs) return rs; }
    if (comps.length > 6 || P.chart === 'table') return compareTable(comps);
    if (mets.length === 1) {
      var k = mets[0];
      var rows = comps.map(function (n, i) { return { n: n, v: getM(k, n), c: PAL[i % PAL.length] }; });
      var have = rows.filter(function (r) { return r.v != null; });
      if (have.length < 2) return null;
      var miss = rows.filter(function (r) { return r.v == null; }).map(function (r) { return r.n.label; });
      have.sort(function (a, b) { return P.asc ? a.v - b.v : b.v - a.v; });
      return spec('bar', metLabel(k) + ': ' + names.join(' vs '),
        (k === 'nrs' ? TT('lowerBetter') + ' · ' : '') + TT('cmpS1'),
        have.map(function (r) { return { label: r.n.label, value: k === 'margin' ? r1(r.v) : (k === 'nrs' ? Math.round(r.v) : r.v), color: k === 'nrs' ? nrsColor(r.v) : r.c }; }),
        { unit: unitOf(k), sort: 'none' }, srcOf(k), miss.length ? (L() === 'en' ? 'No data for: ' : 'Sin dato para: ') + miss.join(', ') : '');
    }
    var use = mets.length ? mets : CMP_DEFAULT;
    var groups = [];
    use.forEach(function (k) {
      var vals = comps.map(function (n) { var v = getM(k, n); return v == null ? null : (k === 'margin' ? r1(v) : k === 'nrs' ? Math.round(v) : v); });
      if (vals.filter(function (v) { return v != null; }).length < 2) return;
      groups.push({ label: metLabel(k), values: vals, unit: unitOf(k), lowerBetter: k === 'nrs' });
    });
    if (!groups.length) return null;
    if (groups.length === 1 && use.length > 1 && !mets.length) return compareTable(comps);
    return spec('grouped', names.join(' vs '), TT('cmpSn'), groups,
      { series_labels: names, colors: comps.map(function (_, i) { return PAL[i % PAL.length]; }) },
      TT('srcCat') + (use.indexOf('nrs') >= 0 ? ' · ' + TT('srcNrs') : ''));
  }
  function compareTable(comps) {
    var cC = TT('colCompany'), cT = TT('colTicker'), cN = TT('colNrs'), cM = TT('colMgn'), cP = TT('colCap'), cR = TT('colRev'), cY = TT('colCountry');
    return spec('table', comps.map(function (n) { return n.label; }).slice(0, 6).join(' · ') + (comps.length > 6 ? '…' : ''), '',
      comps.slice(0, 15).map(function (n) {
        var o = {}; var nv = nrs(n.id), mv = mgn(n);
        o[cC] = n.label; o[cT] = n.mkt || '—'; o[cN] = nv != null ? Math.round(nv) : '—';
        o[cM] = mv != null ? Math.round(mv) : '—'; o[cP] = cap(n.id) || '—'; o[cR] = revB(n.id) != null ? r1(revB(n.id)) : '—';
        o[cY] = countryLabel(canonCountry(n.country));
        return o;
      }), { columns: [cC, cT, cN, cM, cP, cR, cY] }, TT('srcCat') + ' · ' + TT('srcNrs'));
  }
  function radarSpec(comps) {
    var get = {
      axRev: function (n) { return revB(n.id); },
      axMgn: function (n) { var v = mgn(n); return v != null ? Math.max(0, v) : null; },
      axSafe: function (n) { var v = nrs(n.id); return v != null ? Math.max(0, 100 - v) : null; },
      axEmp: function (n) { return emp(n.id); },
      axCap: function (n) { return cap(n.id); },
    };
    var order = ['axRev', 'axMgn', 'axSafe', 'axEmp', 'axCap'], maxBy = {};
    order.forEach(function (mk) {
      var vals = comps.map(function (n) { return get[mk](n); }).filter(function (v) { return v != null && isFinite(v) && v > 0; });
      maxBy[mk] = vals.length >= 2 ? Math.max.apply(null, vals) : 0;
    });
    var axes = order.filter(function (mk) { return maxBy[mk] > 0; });
    if (axes.length < 3) return null;
    return spec('radar', TT('radarT') + ': ' + comps.map(function (n) { return n.label; }).join(' · '), TT('radarS'),
      comps.map(function (n) {
        return { label: n.label, values: axes.map(function (mk) { var v = get[mk](n); return v == null || !isFinite(v) ? 0 : Math.round(Math.max(0, v) / maxBy[mk] * 100); }) };
      }), { axes: axes.map(function (mk) { return TT(mk); }) }, TT('srcCat') + ' · ' + TT('srcNrs'));
  }

  // ── 1 empresa + 1 métrica → KPI (con contexto: puesto y promedio del sector) ──
  function buildSingle(P) {
    var e = P.entities[0], n = byId(e.id), k = P.metrics[0];
    if (!n || !k) return null;
    if (k === 'nrs') return buildNrsBreakdown(e);
    if (k === 'suppliers' || k === 'customers') return buildLinks(P);
    if (MET_BY[k].src !== 'cat') return null;
    var v = getM(k, n);
    if (v == null) return null;
    var all = nodes().map(function (x) { return getM(k, x); }).filter(function (x) { return x != null; });
    var asc = k === 'founded';
    var rank = all.filter(function (x) { return asc ? x < v : x > v; }).length + 1;
    var sec = sectorOf(n), sv = nodes().filter(function (x) { return sectorOf(x) === sec; }).map(function (x) { return getM(k, x); }).filter(function (x) { return x != null; });
    var savg = sv.length >= 2 ? sv.reduce(function (s, x) { return s + x; }, 0) / sv.length : null;
    var subs = [TT('kpiRank', { r: rank, n: all.length })];
    if (savg != null && k !== 'founded') subs.push(TT('kpiSect', { v: fmtPlain(savg, unitOf(k)) }) + ' (' + sectorLabel(sec) + ')');
    return spec('kpi', n.label + (n.mkt ? ' (' + n.mkt + ')' : '') + ' — ' + metLabel(k), '',
      [{ label: metLabel(k), value: k === 'margin' ? r1(v) : v, unit: unitOf(k), sub: subs.join(' · ') }], {}, srcOf(k));
  }
  function fmtPlain(v, unit) {
    if (unit === '$B') return v >= 1000 ? '$' + (v / 1000).toFixed(2) + 'T' : '$' + (v >= 100 ? Math.round(v) : v.toFixed(1)) + 'B';
    if (unit === '%') return r1(v) + '%';
    if (unit === 'NRS') return String(Math.round(v));
    if (unit === 'year') return String(Math.round(v));
    return v >= 1e6 ? r1(v / 1e6) + 'M' : v >= 1e3 ? r1(v / 1e3) + 'k' : String(r1(v));
  }

  // ── ficha rápida de 1 empresa → KPIs ──
  function buildProfile(P) {
    var n = byId(P.entities[0].id);
    if (!n) return null;
    var tiles = [];
    var c = cap(n.id), rv = revB(n.id), mg = mgn(n), nv = nrs(n.id), em = emp(n.id), fd = fnd(n.id);
    if (c != null) tiles.push({ label: TT('mCap'), value: c, unit: '$B' });
    if (rv != null) tiles.push({ label: TT('mRev') + ' 2025', value: r1(rv), unit: '$B' });
    if (mg != null) tiles.push({ label: TT('mMgn'), value: r1(mg), unit: '%' });
    if (nv != null) tiles.push({ label: TT('mNrs'), value: Math.round(nv), unit: 'NRS', sub: TT('lowerBetter'), color: nrsColor(nv) });
    if (em != null) tiles.push({ label: TT('mEmp'), value: em, unit: '' });
    if (fd != null) tiles.push({ label: TT('mFnd'), value: fd, unit: 'year' });
    if (tiles.length < 2) return null;
    return spec('kpi', TT('profT', { l: n.label + (n.mkt ? ' (' + n.mkt + ')' : '') }),
      sectorLabel(sectorOf(n)) + ' · ' + countryLabel(canonCountry(n.country)), tiles, {}, TT('srcCat') + ' · ' + TT('srcNrs'));
  }

  // ── proveedores / clientes de X (vínculos del grafo) ──
  function buildLinks(P) {
    if (!window.LINKS || P.entities.length !== 1) return null;
    var anchor = byId(P.entities[0].id);
    if (!anchor) return null;
    var wantProv = P.metrics.indexOf('suppliers') >= 0 && (P.metrics.indexOf('customers') < 0 || P.metrics.indexOf('suppliers') < P.metrics.indexOf('customers'));
    var rows = [];
    window.LINKS.forEach(function (l) {
      var s = lid(l.source), t = lid(l.target);
      if (wantProv && t === anchor.id && byId(s)) rows.push([byId(s), l.w || 1]);
      if (!wantProv && s === anchor.id && byId(t)) rows.push([byId(t), l.w || 1]);
    });
    if (P.country) rows = rows.filter(function (r) { return inCountry(r[0], P.country); });
    if (!rows.length) return null;
    rows.sort(function (a, b) { return b[1] - a[1] || (cap(b[0].id) || 0) - (cap(a[0].id) || 0); });
    var shown = rows.slice(0, P.topN || 14);
    return spec('bar', withCountry((wantProv ? TT('provOf') : TT('cliOf')) + ' ' + anchor.label, P),
      TT('pcS', { k: shown.length, n: rows.length }),
      shown.map(function (r) { return { label: r[0].label, value: r[1], color: sectorColor(sectorOf(r[0])) }; }),
      { unit: 'w', max: 5 }, TT('srcLinks'));
  }

  // ── relación entre 2 métricas → scatter ──
  function buildScatter(P) {
    var cand = P.metrics.filter(function (k) { return MET_BY[k].src === 'cat' && k !== 'founded'; });
    if (P.metrics.some(function (k) { return MET_BY[k].src !== 'cat'; })) return null;
    if (cand.length === 1) cand = cand[0] === 'nrs' ? ['nrs', 'margin'] : [cand[0], 'nrs'];
    if (cand.length < 2) cand = ['nrs', 'margin'];
    var ky = cand[0], kx = cand[1];
    var base = P.entities.length >= 3 ? P.entities.map(function (e) { return byId(e.id); }).filter(Boolean) : pool(P);
    var pts = base.map(function (n) { return { n: n, x: getM(kx, n), y: getM(ky, n) }; })
      .filter(function (p) { return p.x != null && p.y != null; });
    if (pts.length < 5 && !(P.entities.length >= 3 && pts.length >= 3)) return null;
    // las 40 más grandes (cap o ingresos) para que el gráfico se lea
    pts.sort(function (a, b) { return ((cap(b.n.id) || revB(b.n.id) || 0) - (cap(a.n.id) || revB(a.n.id) || 0)); });
    var total = pts.length;
    pts = pts.slice(0, 40);
    return spec('scatter', withCountry(TT('scT', { y: metLabel(ky), x: metLabel(kx) }), P),
      TT('scS', { n: total }) + (total > 40 ? ' · top 40' : ''),
      pts.map(function (p) { return { label: p.n.label, x: kx === 'margin' ? r1(p.x) : Math.round(p.x * 10) / 10, y: ky === 'margin' ? r1(p.y) : Math.round(p.y * 10) / 10, color: sectorColor(sectorOf(p.n)) }; }),
      { x_label: metLabel(kx) + (unitOf(kx) && unitOf(kx) !== 'NRS' ? ' (' + unitOf(kx) + ')' : ''),
        y_label: metLabel(ky) + (unitOf(ky) && unitOf(ky) !== 'NRS' ? ' (' + unitOf(ky) + ')' : ''), x_unit: unitOf(kx), y_unit: unitOf(ky) },
      TT('srcCat') + (kx === 'nrs' || ky === 'nrs' ? ' · ' + TT('srcNrs') : ''));
  }

  // ── distribución → histograma ──
  function buildHistogram(P) {
    var k = P.metrics[0] || 'nrs';
    if (!MET_BY[k] || MET_BY[k].src !== 'cat') return null;
    var vals = pool(P).map(function (n) { return getM(k, n); }).filter(function (v) { return v != null; });
    if (vals.length < 8) return null;
    var bins;
    if (k === 'nrs') bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100.0001];
    else if (k === 'margin') bins = [-300, -50, -20, 0, 10, 20, 30, 40, 50, 60, 95];
    else if (k === 'founded') bins = [1500, 1900, 1950, 1970, 1980, 1990, 2000, 2010, 2015, 2020, 2100];
    else if (k === 'mktcap' || k === 'revenue') bins = [0, 1, 10, 50, 100, 500, 1000, 1e9];
    else bins = [0, 100, 1000, 10000, 50000, 100000, 500000, 1e9];
    var lab = function (a, b) {
      var u = unitOf(k);
      var f = function (v) { return u === '$B' ? fmtPlain(v, '$B') : u === '%' ? Math.round(v) + '%' : u === 'year' ? String(v) : fmtPlain(v, ''); };
      var mn = function (x) { return String(x).replace(/^-/, '−'); };
      if (b >= 1e8) return '≥ ' + mn(f(a));
      if (a <= -300) return '< ' + mn(f(b));
      if (k === 'founded' && a === 1500) return '< ' + b;
      return mn(f(a)).replace(/%$/, '') + ' … ' + mn(f(k === 'nrs' && b > 100 ? 100 : b));
    };
    var data = [];
    for (var i = 0; i < bins.length - 1; i++) {
      var a = bins[i], b = bins[i + 1];
      var c = vals.filter(function (v) { return v >= a && v < b; }).length;
      data.push({ label: lab(a, b), value: c, color: k === 'nrs' ? nrsColor((a + Math.min(b, 100)) / 2) : BLU });
    }
    while (data.length && data[0].value === 0) data.shift();
    while (data.length && data[data.length - 1].value === 0) data.pop();
    var excl = k === 'margin' ? pool(P).filter(function (nd) { return mgnRaw(nd) != null && mgn(nd) == null; }).length : 0;
    return spec('histogram', withCountry(TT('histT', { m: metLabel(k) }), P), TT('histS', { n: vals.length }),
      data, { x_label: metLabel(k), unit: TT('cntUnit') }, srcOf(k), excl ? TT('exclOut', { n: excl }) : '');
  }

  // ── país × sector → heatmap de NRS promedio ──
  function buildCross(P) {
    var k = P.metrics[0] && MET_BY[P.metrics[0]].src === 'cat' ? P.metrics[0] : (P.metrics.length ? null : 'nrs');
    if (!k || k === 'founded') return null;
    var cnt = {};
    nodes().forEach(function (n) { var c = canonCountry(n.country); cnt[c] = (cnt[c] || 0) + 1; });
    var countries = Object.keys(cnt).filter(function (c) { return c !== '—'; }).sort(function (a, b) { return cnt[b] - cnt[a]; }).slice(0, 8);
    var cells = {}, secSeen = {};
    nodes().forEach(function (n) {
      var c = canonCountry(n.country);
      if (countries.indexOf(c) < 0) return;
      var v = getM(k, n); if (v == null) return;
      var s = sectorOf(n); secSeen[s] = (secSeen[s] || 0) + 1;
      var key = c + '||' + s; var a = cells[key] = cells[key] || { sum: 0, n: 0 }; a.sum += v; a.n++;
    });
    var secs = Object.keys(secSeen).sort(function (a, b) { return secSeen[b] - secSeen[a]; }).slice(0, 9);
    var data = [];
    Object.keys(cells).forEach(function (key) {
      var p = key.split('||'); if (secs.indexOf(p[1]) < 0) return;
      var a = cells[key];
      data.push({ row: countryLabel(p[0]), col: sectorLabel(p[1]), value: /^(nrs|margin)$/.test(k) ? Math.round(a.sum / a.n) : Math.round(a.sum) });
    });
    if (data.length < 4) return null;
    return spec('heatmap', k === 'nrs' ? TT('heatT') : metLabel(k) + ': ' + (L() === 'en' ? 'country × sector' : 'país × sector'), TT('heatS'), data,
      { rows: countries.map(countryLabel), cols: secs.map(sectorLabel), unit: unitOf(k) === 'NRS' ? '' : unitOf(k), higher_is_worse: k === 'nrs' }, srcOf(k));
  }

  // ── mi cartera → donut/treemap por valor (precio en vivo) o tabla ──
  function buildPortfolio(P) {
    var pos = (window.MKT || {}).pos || {};
    var keys = Object.keys(pos);
    if (!keys.length) {
      return spec('notice', TT('portT'), '', [], { message: TT('portEmpty') + ' ' + TT('portEmptyHint'), tone: 'info' }, TT('srcPort'));
    }
    var rows = keys.map(function (k) {
      var n = byId(k) || nodes().find(function (x) { return x.mkt === k; });
      var tk = (n && n.mkt) || k;
      var q = ((window.MKT || {}).quotes || {})[tk] || {};
      var qty = typeof pos[k] === 'object' ? (pos[k].sh || pos[k].qty || pos[k].shares || 0) : pos[k];
      return { label: (n && n.label) || k, tk: tk, qty: Number(qty) || 0, px: q.close != null ? Number(q.close) : null };
    });
    var priced = rows.filter(function (r) { return r.px != null && r.qty > 0; });
    if (priced.length >= 2 && priced.length === rows.length) {
      priced.sort(function (a, b) { return b.px * b.qty - a.px * a.qty; });
      var data = priced.map(function (r, i) { return { label: r.label + ' (' + r.tk + ')', value: Math.round(r.px * r.qty), color: PAL[i % PAL.length] }; });
      return spec(data.length <= 6 ? 'donut' : 'treemap', TT('portT'), rows.length + ' ' + TT('portS'), data, { unit: '$' }, TT('srcPort'));
    }
    var pC = TT('colCompany'), pT = TT('colTicker'), pQ = TT('colQty'), pP = TT('colPrice'), pV = TT('colValue');
    return spec('table', TT('portT'), rows.length + ' ' + TT('portS'), rows.map(function (r) {
      var o = {}; o[pC] = r.label; o[pT] = r.tk; o[pQ] = r.qty;
      o[pP] = r.px != null ? '$' + r.px.toFixed(2) : '—';
      o[pV] = r.px != null && r.qty ? '$' + Math.round(r.px * r.qty).toLocaleString() : '—';
      return o;
    }), { columns: [pC, pT, pQ, pP, pV] }, TT('srcPort'));
  }

  // ── precio "hoy" de 1 empresa → KPI con MKT.quotes ──
  function buildToday(P) {
    var n = byId(P.entities[0].id);
    if (!n || !n.mkt) return null;
    var q = ((window.MKT || {}).quotes || {})[n.mkt];
    if (!q || q.close == null) return null;
    var tiles = [{ label: TT('mPrice'), value: Number(q.close), unit: '$' }];
    if (q.prev) {
      var ch = (q.close / q.prev - 1) * 100;
      tiles[0].sub = (ch >= 0 ? '▲ +' : '▼ ') + ch.toFixed(2) + '% ' + TT('todayS');
      tiles[0].color = ch >= 0 ? GRN : RED;
    }
    return spec('kpi', TT('todayT', { l: n.label + ' (' + n.mkt + ')' }), '', tiles, {}, TT('srcPx'));
  }

  // ── sincrónico: dispatcher por intención ──
  function buildSync(P) {
    switch (P.intent) {
      case 'rank': return P.crypto ? null : buildRank(P);
      case 'compare': return buildCompare(P);
      case 'composition': return buildComposition(P);
      case 'distribution': return buildHistogram(P);
      case 'relationship': return buildScatter(P);
      case 'cross': return buildCross(P);
      case 'single_metric':
        if (P.metrics[0] === 'price') return P.today ? buildToday(P) : null;
        return buildSingle(P);
      case 'profile': return buildProfile(P);
      default: return null;
    }
  }

  /* ══ CACHÉ EN MEMORIA: velas y cripto (para tryAsync + prefetch) ══════════ */
  var _candles = {};                    // key → {t, data} | {t:0, p:Promise}
  var CANDLE_TTL = 5 * 60 * 1000;
  function _rangeFor(days) {
    if (!days) return null;
    if (days <= 5) return '5d'; if (days <= 31) return '1mo'; if (days <= 93) return '3mo';
    if (days <= 186) return '6mo'; if (days <= 366) return '1y'; if (days <= 731) return '2y';
    if (days <= 1830) return '5y'; return 'max';
  }
  function _getCandles(mkt, range) {
    var key = mkt + (range ? '|' + range : '');
    var c = _candles[key];
    if (c && c.data && Date.now() - c.t < CANDLE_TTL) return Promise.resolve(c.data);
    if (c && c.p) return c.p;
    var qs = range ? '?range=' + range + (/^(2y|5y|max)$/.test(range) ? '&interval=1wk' : '') : '';
    var p = fetch((window.BASE || '') + '/api/candles/' + encodeURIComponent(mkt) + qs)
      .then(function (r) { return r.json(); })
      .then(function (d) { _candles[key] = { t: Date.now(), data: d }; return d; })
      .catch(function () { delete _candles[key]; return null; });
    _candles[key] = { t: 0, p: p };
    return p;
  }
  var _crypto = { t: 0, data: null, p: null };
  function _getCrypto() {
    if (_crypto.data && Date.now() - _crypto.t < 120000) return Promise.resolve(_crypto.data);
    if (_crypto.p) return _crypto.p;
    _crypto.p = fetch((window.BASE || '') + '/api/crypto/markets?per_page=25')
      .then(function (r) { return r.json(); })
      .then(function (d) { _crypto = { t: Date.now(), data: d, p: null }; return d; })
      .catch(function () { _crypto.p = null; return null; });
    return _crypto.p;
  }
  var _fund = {};
  function _getFund(mkt) {
    var c = _fund[mkt];
    if (c && (c.data || c.p)) return c.p || Promise.resolve(c.data);
    var p = fetch((window.BASE || '') + '/api/findossier/' + encodeURIComponent(mkt))
      .then(function (r) { return r.json(); })
      .then(function (d) { _fund[mkt] = { data: d }; return d; })
      .catch(function () { delete _fund[mkt]; return null; });
    _fund[mkt] = { p: p };
    return p;
  }
  function _d(ts) {
    try { return new Date(ts * 1000).toLocaleDateString(L() === 'en' ? 'en-US' : 'es-ES', { day: 'numeric', month: 'short', year: '2-digit' }); } catch (e) { return ''; }
  }
  function periodLabel(days, nPts) {
    var en = L() === 'en';
    if (!days) return en ? '~3 months' : '~3 meses';
    if (days <= 31) return days + (en ? ' days' : ' días');
    if (days < 365) return Math.round(days / 30) + (en ? ' months' : ' meses');
    var y = Math.round(days / 365);
    return y + (en ? (y === 1 ? ' year' : ' years') : (y === 1 ? ' año' : ' años'));
  }

  function buildPriceAsync(P) {
    var ents = P.entities.map(function (e) { return byId(e.id); }).filter(function (n) { return n && n.mkt; }).slice(0, 4);
    if (!ents.length || ents.length !== P.entities.length) return Promise.resolve(null);
    var days = P.timeframe ? P.timeframe.days : null, range = _rangeFor(days);
    return Promise.all(ents.map(function (n) { return _getCandles(n.mkt, range); })).then(function (all) {
      var ok = all.every(function (c) { return c && c.s === 'ok' && c.c && c.c.length >= 5; });
      if (!ok) return null;
      var plab = periodLabel(days);
      if (ents.length === 1) {
        var c = all[0], n = ents[0];
        var vals = c.c.map(function (v) { return Math.round(v * 100) / 100; });
        var up = vals[vals.length - 1] >= vals[0];
        var pct = ((vals[vals.length - 1] / vals[0] - 1) * 100).toFixed(1);
        return spec('line', TT('lineT', { l: n.label + ' (' + n.mkt + ')', p: plab }),
          TT('lineS', { a: (up ? '▲ +' : '▼ ') + pct + '%', d0: _d((c.t || [])[0]), d1: _d((c.t || [])[c.t.length - 1]) }),
          [{ label: n.mkt, values: vals, color: up ? GRN : RED }],
          { series_labels: [n.mkt], labels: (c.t || []).map(_d), unit: '$' }, TT('srcPx'));
      }
      // varias: base 100 sobre la longitud común
      var len = Math.min.apply(null, all.map(function (c) { return c.c.length; }));
      var series = all.map(function (c, i) {
        var arr = c.c.slice(c.c.length - len), b0 = arr[0];
        return { label: ents[i].mkt, values: arr.map(function (v) { return Math.round(v / b0 * 1000) / 10; }), color: PAL[i % PAL.length] };
      });
      var t0 = all[0].t ? all[0].t.slice(all[0].t.length - len) : [];
      return spec('line', TT('relT', { p: plab }), TT('relS'), series,
        { series_labels: ents.map(function (n) { return n.label + ' (' + n.mkt + ')'; }), labels: t0.map(_d), unit: '' }, TT('srcPx'));
    });
  }

  function buildFundAsync(P) {
    var k = P.metrics.filter(isFund)[0] || (P.metrics[0] === 'revenue' ? 'revenue' : P.metrics[0] === 'margin' ? 'gross_margin' : null);
    if (!k) return Promise.resolve(null);
    var FKEY = { revenue: { key: 'revenue', bn: true, unit: '$B', es: 'Ingresos', en: 'Revenue' } };
    var m = FKEY[k] ? FKEY[k] : { key: k, bn: !!MET_BY[k].bn, unit: MET_BY[k].unit, es: MET_BY[k].es, en: MET_BY[k].en, fbar: MET_BY[k].fbar };
    var ents = P.entities.map(function (e) { return byId(e.id); }).filter(function (n) { return n && n.mkt; }).slice(0, 4);
    if (!ents.length || ents.length !== P.entities.length) return Promise.resolve(null);
    var flab = L() === 'en' ? m.en : m.es;
    return Promise.all(ents.map(function (n) { return _getFund(n.mkt); })).then(function (all) {
      if (!all.every(function (d) { return d && d.available && Array.isArray(d.years); })) return null;
      var SM = { fmp: 'FMP', yahoo: 'Yahoo Finance', alphavantage: 'Alpha Vantage' };
      var srcs = all.map(function (d) { return SM[d.source] || d.source || '—'; }).filter(function (s, i, a) { return a.indexOf(s) === i; }).join(', ');
      var years = {};
      all.forEach(function (d) { d.years.forEach(function (y, i) { if ((d[m.key] || [])[i] != null) years[y] = 1; }); });
      var ys = Object.keys(years).sort();
      if (P.timeframe && P.timeframe.days >= 365) ys = ys.slice(-Math.max(2, Math.round(P.timeframe.days / 365)));
      if (ys.length < 2) return null;
      var conv = function (v) { return v == null ? null : (m.bn ? Math.round(v / 1e9 * 10) / 10 : Math.round(v * 10) / 10); };
      var series = all.map(function (d, i) {
        return { label: ents[i].mkt, color: PAL[i % PAL.length], values: ys.map(function (y) { var ix = d.years.map(String).indexOf(String(y)); return ix >= 0 ? conv((d[m.key] || [])[ix]) : null; }) };
      });
      var note = (k === 'gross_margin' && P.metrics[0] === 'margin') ? (L() === 'en' ? 'Gross margin from annual statements (the catalog margin has no history)' : 'Margen bruto de los estados anuales (el margen del catálogo no tiene historial)') : '';
      if (ents.length === 1) {
        var vals = series[0].values, first = vals.find(function (v) { return v != null; }), last = vals[vals.length - 1];
        var up = last != null && first != null && last >= first;
        var sub = (up ? '▲ ' : '▼ ') + ys[0] + '→' + ys[ys.length - 1];
        if (m.fbar) {
          return spec('bar', ents[0].label + ' — ' + flab, sub,
            ys.map(function (y, i) { return { label: String(y), value: vals[i], color: vals[i] != null && vals[i] < 0 ? RED : GRN }; }).filter(function (d) { return d.value != null; }),
            { unit: m.unit, sort: 'none', time: true }, TT('srcFund', { s: srcs }), note);
        }
        return spec('line', ents[0].label + ' — ' + flab, sub, [{ label: flab, values: vals, color: up ? GRN : RED }],
          { series_labels: [flab], labels: ys.map(String), unit: m.unit }, TT('srcFund', { s: srcs }), note);
      }
      return spec('line', flab + ': ' + ents.map(function (n) { return n.label; }).join(' vs '), ys[0] + '→' + ys[ys.length - 1], series,
        { series_labels: ents.map(function (n) { return n.label; }), labels: ys.map(String), unit: m.unit }, TT('srcFund', { s: srcs }), note);
    }).catch(function () { return null; });
  }

  var CRYPTO_ALIAS = { bitcoin: 'bitcoin', btc: 'bitcoin', ethereum: 'ethereum', eth: 'ethereum', ether: 'ethereum', solana: 'solana', sol: 'solana',
    xrp: 'ripple', ripple: 'ripple', bnb: 'binancecoin', cardano: 'cardano', ada: 'cardano', dogecoin: 'dogecoin', doge: 'dogecoin',
    tether: 'tether', usdt: 'tether', usdc: 'usd-coin', tron: 'tron', trx: 'tron', avalanche: 'avalanche-2', avax: 'avalanche-2',
    polkadot: 'polkadot', dot: 'polkadot', chainlink: 'chainlink', link: 'chainlink', litecoin: 'litecoin', ltc: 'litecoin', monero: 'monero', xmr: 'monero' };
  function cryptoCoinIn(text) {
    var words = (text || '').toLowerCase().split(/[^a-z0-9]+/);
    for (var i = 0; i < words.length; i++) { if (CRYPTO_ALIAS[words[i]]) return CRYPTO_ALIAS[words[i]]; }
    return null;
  }
  // "precio de bitcoin de los últimos 5 años" → LÍNEA con el historial (no un ranking)
  function buildCryptoHistoryAsync(P) {
    var coin = cryptoCoinIn(P.text) || cryptoCoinIn(P.query);
    var pick = coin ? Promise.resolve(coin) : _getCrypto().then(function (d) {
      var lc = (P.text || '').toLowerCase();
      var a = ((d && d.assets) || []).filter(function (x) { return x && x.id && (lc.indexOf(String(x.name || '').toLowerCase()) >= 0 || new RegExp('\\b' + String(x.symbol || '').toLowerCase() + '\\b').test(lc)); })[0];
      return a ? a.id : null;
    });
    return pick.then(function (cid) {
      if (!cid) return null;
      var asked = P.timeframe ? P.timeframe.days : 365, days = Math.min(365, asked || 365);
      return fetch((window.BASE || '') + '/api/crypto/' + encodeURIComponent(cid) + '/history?days=' + days)
        .then(function (r) { return r.json(); })
        .then(function (d) {
          var pr = (d && d.prices) || [];
          if (pr.length < 5) return null;
          var vals = pr.map(function (x) { return Math.round(+x[1] * 100) / 100; });
          var labs = pr.map(function (x) { return _d(+x[0] / 1000); });
          var up = vals[vals.length - 1] >= vals[0];
          var pct = ((vals[vals.length - 1] / vals[0] - 1) * 100).toFixed(1);
          var name = cid.charAt(0).toUpperCase() + cid.slice(1).replace(/-\d+$/, '');
          var note = asked > 365 ? TT('cryHCap', { p: periodLabel(asked) }) : '';
          return spec('line', TT('cryHT', { l: name, p: periodLabel(days) }),
            TT('lineS', { a: (up ? '▲ +' : '▼ ') + pct + '%', d0: labs[0], d1: labs[labs.length - 1] }),
            [{ label: name, values: vals, color: up ? GRN : RED }],
            { series_labels: [name], labels: labs, unit: '$' }, TT('srcCryH'), note);
        }).catch(function () { return null; });
    });
  }

  function buildCryptoAsync(P) {
    return _getCrypto().then(function (d) {
      var assets = (d && d.assets) || [];
      var n = P.topN || 10;
      var rows = assets.filter(function (a) { return a && a.market_cap > 0; })
        .sort(function (a, b) { return b.market_cap - a.market_cap; }).slice(0, n);
      if (rows.length < 2) return null;
      return spec('bar', TT('cryT', { n: rows.length }), TT('cryS'), rows.map(function (a) {
        var up = (a.change_24h_pct || 0) >= 0;
        return { label: (a.rank ? a.rank + '. ' : '') + (a.name || a.id) + ' (' + String(a.symbol || '').toUpperCase() + ')',
                 value: Math.round(a.market_cap / 1e9 * 10) / 10, color: up ? GRN : RED };
      }), { unit: '$B' }, TT('srcCry'));
    });
  }

  function buildCommodityAsync(P) {
    var c = P.commodity, days = P.timeframe ? P.timeframe.days : 365, range = _rangeFor(days);
    return _getCandles(c.sym, range).then(function (d) {
      if (!(d && d.s === 'ok' && d.c && d.c.length >= 5)) return null;
      var vals = d.c.map(function (v) { return Math.round(v * 100) / 100; });
      var up = vals[vals.length - 1] >= vals[0], pct = ((vals[vals.length - 1] / vals[0] - 1) * 100).toFixed(1);
      var name = L() === 'en' ? c.en : c.es;
      return spec('line', TT('lineT', { l: name + ' (' + c.sym + ')', p: periodLabel(days) }),
        TT('lineS', { a: (up ? '▲ +' : '▼ ') + pct + '%', d0: _d((d.t || [])[0]), d1: _d((d.t || [])[d.t.length - 1]) }),
        [{ label: c.sym, values: vals, color: up ? GRN : RED }],
        { series_labels: [name], labels: (d.t || []).map(_d), unit: /^\^/.test(c.sym) ? '' : '$' }, TT('srcPx'));
    });
  }
  function buildAsync(P) {
    if (P.commodity && !P.entities.length) return buildCommodityAsync(P);
    // una cripto concreta + tiempo/precio → su historial (antes caía al ranking "Top 10 cripto")
    if (P.crypto && (cryptoCoinIn(P.text) || cryptoCoinIn(P.query)) && (P.intent === 'trend' || P.timeframe || P.metrics.indexOf('price') >= 0 || P.intent === 'single_metric')) {
      return buildCryptoHistoryAsync(P).then(function (sp) { return sp || buildCryptoAsync(P); });
    }
    if (P.crypto && (P.intent === 'rank' || P.intent === 'other' || P.intent === 'composition')) return buildCryptoAsync(P);
    if (P.intent === 'trend' || (P.intent === 'single_metric' && P.metrics.some(isFund)) ||
        (P.intent === 'compare' && P.metrics.length && P.metrics.every(function (k) { return isFund(k) || k === 'price'; }))) {
      if (P.metrics.indexOf('price') >= 0 || !P.metrics.length) return buildPriceAsync(P);
      return buildFundAsync(P);
    }
    if (P.intent === 'single_metric' && P.metrics[0] === 'price') return buildPriceAsync(P);
    return Promise.resolve(null);
  }

  /* ══ decide(q): el flujo completo (local confiable → IA con hints) ═══════ */
  function decide(query) {
    var P = route(query);
    var hints = hintsOf(P);
    if (!P.local) return Promise.resolve({ via: 'ai', route: P, hints: hints, confidence: P.confidence, reason: P.reason });
    var s = null;
    try { s = buildSync(P); } catch (e) { s = null; }
    if (s) return Promise.resolve({ via: 'local', spec: s, route: P, hints: hints, confidence: P.confidence, reason: 'ok' });
    var p;
    try { p = buildAsync(P); } catch (e) { p = Promise.resolve(null); }
    return p.then(function (sa) {
      if (sa) return { via: 'local-async', spec: sa, route: P, hints: hints, confidence: P.confidence, reason: 'ok' };
      hints.reason = 'no_local_data';
      return { via: 'ai', route: P, hints: hints, confidence: P.confidence, reason: 'no_local_data' };
    }, function () { return { via: 'ai', route: P, hints: hints, confidence: P.confidence, reason: 'no_local_data' }; });
  }

  /* ══ honest(q, err): "no puedo con precisión sin IA" + parcial correcta ═══ */
  var EXAMPLES = { es: ['compara márgenes de Nvidia y AMD', 'precio de TSMC 6 meses', 'riesgo por sector', 'top 10 por capitalización', 'relación entre riesgo y margen'],
                   en: ['compare margins of Nvidia and AMD', 'TSMC price 6 months', 'risk by sector', 'top 10 by market cap', 'risk vs margin'] };
  function reasonText(P) {
    var lines = [];
    (P.reasons || [P.reason]).forEach(function (r) {
      if (r === 'needs_reasoning') lines.push(TT('rsReason'));
      else if (r === 'metric_unavailable') lines.push(TT('rsMetric', { m: P.metrics.filter(function (k) { return MET_BY[k].src === 'none'; }).map(metLabel).join(', ') }));
      else if (r === 'unknown_words') lines.push(TT('rsUnknown', { w: P.unknown.join(' ') }));
      else if (r === 'weak_entity') P.weak.forEach(function (w) { lines.push(TT('rsWeak', { w: w.word, s: [w.label].concat(w.sugg || []).slice(0, 3).join(' / ') })); });
      else if (r === 'missing_entities') lines.push(TT('rsMissing'));
      else if (r === 'no_history') lines.push(TT('rsHistory', { m: P.metrics.filter(function (k) { return /^(nrs|mktcap|employees|founded|suppliers|customers)$/.test(k); }).map(metLabel).join(', ') }));
      else if (r === 'vague') lines.push(TT('rsVague'));
      else if (r === 'no_local_data') lines.push(TT('rsNoData'));
    });
    var seen = {};
    return lines.filter(function (l) { if (seen[l]) return false; seen[l] = 1; return true; });
  }
  // la respuesta parcial: lo que SÍ entendimos, con datos reales y sin fingir
  function partialFor(P) {
    var Q = JSON.parse(JSON.stringify(P));
    Q.metrics = P.metrics.filter(function (k) { return MET_BY[k].src !== 'none'; });
    // empresas dudosas → usamos la mejor coincidencia SOLO como parcial
    if (!Q.entities.length && P.weak.length) Q.entities = P.weak.map(function (w) { return { id: w.id, label: w.label }; });
    var en = Q.entities.length;
    var tries = [];
    if (P.metrics.some(function (k) { return k === 'debt'; }) && en) tries.push(function () { var R = JSON.parse(JSON.stringify(Q)); R.metrics = ['de_ratio']; R.intent = 'trend'; return buildFundAsync(R); });
    if (en >= 2) tries.push(function () { var R = JSON.parse(JSON.stringify(Q)); R.intent = 'compare'; R.metrics = R.metrics.filter(function (k) { return MET_BY[k].src === 'cat'; }); return buildCompare(R); });
    if (en === 1) {
      if (Q.metrics.indexOf('price') >= 0 || P.explain) tries.push(function () { var R = JSON.parse(JSON.stringify(Q)); R.intent = 'trend'; R.metrics = ['price']; return buildPriceAsync(R); });
      var cm = Q.metrics.filter(function (k) { return MET_BY[k].src === 'cat'; });
      if (cm.length) tries.push(function () { var R = JSON.parse(JSON.stringify(Q)); R.intent = 'single_metric'; R.metrics = cm; return buildSingle(R); });
      tries.push(function () { var R = JSON.parse(JSON.stringify(Q)); R.intent = 'profile'; return buildProfile(R); });
    }
    if (!en && Q.metrics.some(function (k) { return MET_BY[k].src === 'cat'; })) {
      tries.push(function () { var R = JSON.parse(JSON.stringify(Q)); R.metrics = Q.metrics.filter(function (k) { return MET_BY[k].src === 'cat'; }); R.intent = R.groupBy.length ? 'rank' : (R.metrics.length >= 2 ? 'relationship' : 'rank'); return R.intent === 'relationship' ? buildScatter(R) : buildRank(R); });
    }
    if (!en && P.country && !Q.metrics.length) tries.push(function () { var R = JSON.parse(JSON.stringify(Q)); R.metrics = ['nrs']; R.intent = 'rank'; return buildRank(R); });
    var i = 0;
    function next() {
      if (i >= tries.length) return Promise.resolve(null);
      var f = tries[i++], r;
      try { r = f(); } catch (e) { r = null; }
      return Promise.resolve(r).then(function (s) { return s || next(); }, next);
    }
    return next();
  }
  function honest(query, errMsg) {
    var P = route(query);
    if (P.local) { P.reasons = ['no_local_data']; P.reason = 'no_local_data'; }
    var lines = reasonText(P);
    if (errMsg) {
      var em = String(errMsg);
      if (/no ai provider|sin keys|ningún proveedor|no provider/i.test(em)) em = TT('noProv');
      else if (/429|rate|límite|limit/i.test(em)) em = TT('rateLim');
      lines.push(TT('aiDown') + ' (' + em.slice(0, 140) + ').');
    }
    var ex = EXAMPLES[L()] || EXAMPLES.es;
    return partialFor(P).then(function (part) {
      if (part) part.partial = true;
      if (!part) lines.push(TT('tryLike', { e: ex[Math.floor(Math.random() * ex.length)] }));
      return { type: 'notice', title: TT('noAiT'), subtitle: '', data: [], engine: 'local',
               config: { message: lines.join(' '), tone: 'warn', partial_label: part ? TT('noAiPartial') : TT('noAiNone') },
               partial: part || null, source: part ? part.source : '' };
    }).catch(function () {
      return { type: 'notice', title: TT('noAiT'), subtitle: '', data: [], engine: 'local', config: { message: lines.join(' '), tone: 'warn' }, partial: null };
    });
  }

  // ── compat: try/tryAsync (devuelven spec SOLO si la confianza es alta) ──
  function trySpec(query) {
    var P = route(query);
    if (!P.local) return null;
    return buildSync(P);
  }
  function tryAsync(query) {
    var P = route(query);
    if (!P.local) return Promise.resolve(null);
    var s0 = null;
    try { s0 = buildSync(P); } catch (e) { s0 = null; }
    if (s0) return Promise.resolve(s0);
    return buildAsync(P);
  }

  /* ══ 2) ESQUELETO "Generando con IA…" (bilingüe, instantáneo) ═════════════ */
  var _cssDone = false;
  function _injectCSS() {
    if (_cssDone || !document.head) return;
    _cssDone = true;
    var st = document.createElement('style');
    st.id = 'khlc-css';
    st.textContent =
      '.khlc-skel{display:flex;flex-direction:column;gap:7px;width:72%;max-width:340px}' +
      '.khlc-skel-bar{height:9px;border-radius:5px;' +
        'background:linear-gradient(90deg,rgba(122,158,255,.10),rgba(122,158,255,.30),rgba(122,158,255,.10));' +
        'background-size:200% 100%;animation:khlcShimmer 1.2s linear infinite}' +
      '@keyframes khlcShimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}';
    document.head.appendChild(st);
  }

  function _skelHTML(h) {
    return '<div style="height:' + h + 'px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:11px">' +
      '<div class="cv-spinner"></div>' +
      '<div style="font-size:12px;color:#8fa6d4;font-weight:600">✦ ' + TT('gen') + '</div>' +
      '<div style="font-size:10px;color:#5b6b8f">' + TT('genHint') + '</div>' +
      '<div class="khlc-skel">' +
        '<div class="khlc-skel-bar" style="width:92%"></div>' +
        '<div class="khlc-skel-bar" style="width:64%"></div>' +
        '<div class="khlc-skel-bar" style="width:78%"></div>' +
      '</div></div>';
  }

  // localiza los cards pendientes (Canvas / Cabina / Khipu inline) y pinta el
  // esqueleto EN EL MISMO contenedor donde aparecerá el gráfico.
  function _showAISkeleton() {
    try {
      _injectCSS();
      var cards = document.querySelectorAll('.cv-card:not([data-khlc])');
      for (var i = 0; i < cards.length; i++) {
        var card = cards[i];
        var spin = card.querySelector('.cv-spinner');
        if (spin && spin.parentElement && spin.parentElement !== card) {
          // Canvas (app.html) y Cabina (cockpit.js): reemplazar el bloque del spinner
          card.setAttribute('data-khlc', '1');
          spin.parentElement.outerHTML = _skelHTML(180);
        } else if (!spin && card.id && card.id.indexOf('bcc-cv-') === 0 && !card.querySelector('.cv-card-hdr')) {
          // Khipu inline (command_center.js): holder sin header todavía
          card.setAttribute('data-khlc', '1');
          card.innerHTML = _skelHTML(130);
        }
      }
    } catch (e) {}
  }

  /* ══ 3) CACHÉ CLIENTE de respuestas del Canvas IA (localStorage, LRU) ═════ */
  var CK = 'kh_chartcache', CACHE_TTL = 60 * 60 * 1000, CACHE_MAX = 30;

  function _normKey(q) {
    var s = String(q || '').toLowerCase();
    try { s = s.normalize('NFD').replace(new RegExp('[\\u0300-\\u036f]', 'g'), ''); } catch (e) {}
    return s.replace(/[¿?¡!.,;:'"«»()]+/g, ' ').replace(/\s+/g, ' ').trim();
  }
  function _cacheLoad() {
    // v2 (router 2026-10-02): las respuestas viejas de la IA no pasaron por la
    // validación de tipo de gráfico → se descartan.
    try { var d = JSON.parse(localStorage.getItem(CK) || 'null'); if (d && d.v === 2 && d.items && d.items.length !== undefined) return d; } catch (e) {}
    return { v: 2, items: [] };
  }
  function _cacheSave(d) { try { localStorage.setItem(CK, JSON.stringify(d)); } catch (e) { try { localStorage.removeItem(CK); } catch (e2) {} } }
  function _cacheGet(key) {
    var d = _cacheLoad(), now = Date.now(), hit = null, dirty = false;
    var keep = [];
    for (var i = 0; i < d.items.length; i++) {
      var it = d.items[i];
      if (now - (it.t || 0) >= CACHE_TTL) { dirty = true; continue; }   // TTL 1 h
      if (it.k === key) { hit = it; it.last = now; dirty = true; }
      keep.push(it);
    }
    d.items = keep;
    if (dirty) _cacheSave(d);
    return hit;
  }
  function _cachePut(key, spec, model) {
    if (!key || !spec) return;
    var d = _cacheLoad(), now = Date.now();
    d.items = d.items.filter(function (x) { return x.k !== key && now - (x.t || 0) < CACHE_TTL; });
    d.items.push({ k: key, t: now, last: now, spec: spec, model: model || '' });
    while (d.items.length > CACHE_MAX) {                                // LRU: fuera el menos usado
      var oldest = 0;
      for (var i = 1; i < d.items.length; i++) if ((d.items[i].last || 0) < (d.items[oldest].last || 0)) oldest = i;
      d.items.splice(oldest, 1);
    }
    _cacheSave(d);
  }
  function clearCache() {
    try { localStorage.removeItem(CK); } catch (e) {}
    _candles = {};
    _fund = {};
    _crypto = { t: 0, data: null, p: null };
    return true;
  }

  // Interceptor de fetch SOLO para POST /api/canvas/generate: sirve del caché
  // (instantáneo) o pinta el esqueleto y guarda la respuesta. Cubre Canvas,
  // Cabina y Khipu sin tocar sus archivos. Passthrough para todo lo demás.
  function _wrapFetch() {
    if (window.__khlcFetchWrapped || typeof window.fetch !== 'function') return;
    window.__khlcFetchWrapped = true;
    var _orig = window.fetch;
    window.fetch = function (input, init) {
      try {
        var url = (typeof input === 'string') ? input : ((input && input.url) || '');
        var method = String((init && init.method) || (input && input.method) || 'GET').toUpperCase();
        if (method === 'POST' && /\/api\/canvas\/generate(?:\?|$)/.test(url) &&
            init && typeof init.body === 'string' && typeof Response === 'function') {
          var body = null;
          try { body = JSON.parse(init.body); } catch (e) {}
          // ROUTER: la intención/entidades/métricas parseadas viajan como
          // `hints` (la IA elige el gráfico con el MISMO criterio y el server
          // valida el tipo) y se añaden los datos de ficha que la IA necesita
          // para no inventar (cap, ingresos, empleados, fundación). Cubre
          // Canvas, Cabina y Khipu sin tocar sus archivos.
          if (body && body.query) {
            try {
              if (!body.hints) body.hints = hintsOf(route(body.query));
              _enrichCtx(body);
              init = Object.assign({}, init, { body: JSON.stringify(body) });
            } catch (e) {}
          }
          var key = body && body.query ? _normKey(body.query) : '';
          if (key) {
            var hit = _cacheGet(key);
            if (hit && hit.spec) {
              return Promise.resolve(new Response(
                JSON.stringify({ spec: hit.spec, model: '⚡ ' + (hit.model || 'cache'), cached: true }),
                { status: 200, headers: { 'Content-Type': 'application/json' } }));
            }
            _showAISkeleton();   // va a la IA: feedback inmediato en el card
            return _orig.call(this, input, init).then(function (r) {
              try {
                if (r && r.ok && (r.headers.get('content-type') || '').indexOf('application/json') >= 0) {
                  r.clone().json().then(function (d) {
                    if (d && d.spec && !d.error) _cachePut(key, d.spec, d.model);
                  }).catch(function () {});
                }
              } catch (e) {}
              return r;
            });
          }
        }
      } catch (e) {}
      return _orig.call(this, input, init);
    };
  }
  // datos de ficha de las empresas que viajan en el contexto (solo los que
  // EXISTEN en NODE_META; nada se rellena) — y las empresas de los hints
  // siempre presentes aunque el caller haya recortado la lista.
  function _enrichCtx(body) {
    var ctx = body.context = body.context || {};
    var list = Array.isArray(ctx.nodes) ? ctx.nodes : (ctx.nodes = []);
    var have = {};
    list.forEach(function (o) { if (o && o.id) have[o.id] = o; });
    ((body.hints || {}).entities || []).forEach(function (e) {
      if (e && e.id && !have[e.id] && byId(e.id)) {
        var n = byId(e.id), o = { id: n.id, label: n.label, cat: n.cat };
        if (n.mkt) o.mkt = n.mkt;
        if (n.margin != null) o.margin = n.margin;
        if (n.country) o.country = n.country;
        var v = nrs(n.id); if (v != null) o.nrs = v;
        list.push(o); have[o.id] = o;
      }
    });
    list.forEach(function (o) {
      if (!o || !o.id) return;
      var c = cap(o.id), r = revB(o.id), e2 = emp(o.id), f = fnd(o.id);
      if (c != null && o.mktcap_b == null) o.mktcap_b = c;
      if (r != null && o.revenue_b == null) o.revenue_b = Math.round(r * 10) / 10;
      if (e2 != null && o.employees == null) o.employees = e2;
      if (f != null && o.founded == null) o.founded = f;
      if (o.country) o.country = canonCountry(o.country);
      if (o.margin != null && (o.margin * 100 >= 95 || o.margin * 100 <= -300)) delete o.margin;   // atípico del catálogo
    });
  }
  _wrapFetch();

  /* ══ 4) PREFETCH de velas al abrir Canvas / Cabina (máx. 4, silencioso) ═══ */
  var _lastPrefetch = 0;
  function prefetch() {
    try {
      if (Date.now() - _lastPrefetch < 120000) return;   // throttle 2 min
      _lastPrefetch = Date.now();
      var tickers = [];
      var byId = window.NODE_BY_ID || {};
      // nodo enfocado primero
      var sel = window._selectedNode && byId[window._selectedNode];
      if (sel && sel.mkt) tickers.push(sel.mkt);
      // portafolio del usuario (MKT.pos, claves = ids de nodo)
      var pos = (window.MKT || {}).pos || {};
      Object.keys(pos).forEach(function (id) {
        var n = byId[id];
        var mkt = (n && n.mkt) || null;
        if (mkt && tickers.indexOf(mkt) < 0) tickers.push(mkt);
      });
      tickers = tickers.filter(function (t) {
        var c = _candles[t];
        return !(c && (c.p || (c.data && Date.now() - c.t < CANDLE_TTL)));
      }).slice(0, 4);
      tickers.forEach(function (t) { _getCandles(t).catch(function () {}); });
    } catch (e) {}
  }

  // enganches perezosos: switchTab('canvas') y BixbyCockpit.open se definen
  // DESPUÉS de este archivo → reintentar hasta poder envolverlos.
  var _hooked = { tab: false, cabin: false }, _hookTries = 0;
  function _installHooks() {
    try {
      if (!_hooked.tab && typeof window.switchTab === 'function') {
        var st = window.switchTab;
        window.switchTab = function (tab) {
          if (tab === 'canvas') { try { prefetch(); } catch (e) {} }
          return st.apply(this, arguments);
        };
        _hooked.tab = true;
      }
      if (!_hooked.cabin && window.BixbyCockpit && typeof window.BixbyCockpit.open === 'function') {
        var op = window.BixbyCockpit.open;
        window.BixbyCockpit.open = function () {
          try { prefetch(); } catch (e) {}
          return op.apply(this, arguments);
        };
        _hooked.cabin = true;
      }
    } catch (e) {}
    if ((!_hooked.tab || !_hooked.cabin) && _hookTries++ < 40) setTimeout(_installHooks, 1500);
  }
  _installHooks();

  window.KhipuLocalCharts = {
    try: function (query) {
      try { return trySpec(query); } catch (e) { return null; }
    },
    // NUEVO (router 2026-10-02)
    route: function (query) { try { return route(query); } catch (e) { return { intent: 'other', entities: [], metrics: [], confidence: 0, reason: 'error', local: false }; } },
    hints: function (query) { try { return hintsOf(route(query)); } catch (e) { return null; } },
    decide: function (query) {
      var p;
      try { p = decide(query); } catch (e) { p = Promise.resolve({ via: 'ai', reason: 'error' }); }
      return p.then(function (d) { if (d && d.via === 'ai') _showAISkeleton(); return d; });
    },
    honest: function (query, errMsg) { try { return honest(query, errMsg); } catch (e) { return Promise.resolve(null); } },
    ACCEPT: ACCEPT,
    // patrones que necesitan datos del servidor (velas/cripto) — sin IA.
    // Si tampoco matchean → el pedido va a la IA: pintamos el esqueleto YA.
    tryAsync: function (query) {
      var p;
      try { p = tryAsync(query); } catch (e) { p = Promise.resolve(null); }
      return p.then(
        function (spec) { if (!spec) _showAISkeleton(); return spec; },
        function () { _showAISkeleton(); return null; });
    },
    clearCache: clearCache,
    prefetch: prefetch,
  };
})();
