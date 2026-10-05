/* engine/worldmonitor.js — WORLD MONITOR geopolítico (pestaña 🌐 Geopolítica).

   Pedido de Fabrizio (2026-09-30): "hay el mundo 3D y el mapa de eventos pero el
   mapa de eventos es muy grande y no da mucha info; quiero que sea como un world
   monitor, impresionante, incorporado al 3D y que solo haya uno".
   → UNA sola vista: globo 3D (engine/globe.js, look 'monitor') con:
     · eventos EN VIVO (GDELT conflicto/protestas/comercio, USGS sismos, NASA
       EONET eventos naturales) como puntos pulsantes por severidad,
     · estrechos/canales con score vivo (anillos) + inestabilidad por país,
     · TU grafo: empresas por NRS, arcos de suministro con flujo, tu cartera,
     · REFERENCIA (no en vivo): rutas marítimas, cables submarinos, fabs.
   HUD: ticker de titulares, capas con estado por fuente, panel de inteligencia
   (qué/dónde/cuándo/fuente + empresas del grafo expuestas + X-Ray + simular),
   filtro 24h/7d, leyenda y "Situación global". En móvil los paneles son hojas
   inferiores. Degrada con gracia: sin servidor, el globo + empresas siguen y el
   estado dice qué fuente cayó.

   API: window.KhipuWorld = { mount(container), open(), focus(lat, lon), unmount() }
   Datos: /api/world/events · /api/world/brief · /api/world/reference ·
          /api/world/exposure · /api/matrix/status · POST /api/matrix/impact.
   Todo bilingüe (window.LANG). Cada métrica con su "?" (engine/explain.js). */
(function () {
  'use strict';

  var S = {
    root: null, globe: null, win: '24h', events: null, eventsErr: null, brief: null, ref: null,
    refErr: null, systemic: null, items: {}, sel: null, expCache: {}, timers: [], pendingPolls: 0,
    loading: false, narrow: false, sheet: null, collapsed: { left: false, right: false },
    vis: { conflict: true, unrest: true, trade: true, quakes: true, natural: true, chokepoints: true,
      shipping: true, policy: true, disasters: true, advisories: true, outages: true,
      instability: true, companies: true, arcs: true, portfolio: true, lanes: true, cables: false, fabs: true },
    sim: null, lastLoad: 0, quotes: null, quotesErr: null, quotesTs: 0, lists: {},
  };

  var LAYERS = [
    // 2026-10-05: fuentes OFICIALES (core/world_feeds.py) — "más info, pero fiable"
    { id: 'shipping', g: 'official', c: '#5B8CFF', i: '⛴', es: 'Tráfico por estrechos (FMI)', en: 'Strait traffic (IMF)', ses: 'Buques', sen: 'Ships' },
    { id: 'policy', g: 'official', c: '#A3E635', i: '📜', es: 'Reglas de chips y sanciones (EE.UU.)', en: 'Chip rules & sanctions (US)', ses: 'Reglas', sen: 'Rules' },
    { id: 'disasters', g: 'official', c: '#E879F9', i: '🚨', es: 'Alertas de desastres (ONU/UE)', en: 'Disaster alerts (UN/EU)', ses: 'Alertas', sen: 'Alerts' },
    { id: 'advisories', g: 'official', c: '#F97316', i: '🛂', es: 'Riesgo país oficial (EE.UU.)', en: 'Official country risk (US)', ses: 'Riesgo país', sen: 'Country risk' },
    { id: 'outages', g: 'official', c: '#22D3EE', i: '🛜', es: 'Cortes de internet', en: 'Internet outages', ses: 'Internet', sen: 'Internet' },
    { id: 'conflict', g: 'live', c: '#FF3B5C', i: '⚔', es: 'Conflicto armado', en: 'Armed conflict', ses: 'Conflicto', sen: 'Conflict' },
    { id: 'unrest', g: 'live', c: '#FF8A3D', i: '📢', es: 'Protestas', en: 'Protests / unrest', ses: 'Protestas', sen: 'Unrest' },
    { id: 'trade', g: 'live', c: '#FFD23F', i: '⚖', es: 'Comercio / sanciones', en: 'Trade / sanctions', ses: 'Comercio', sen: 'Trade' },
    { id: 'quakes', g: 'live', c: '#B983FF', i: '◎', es: 'Sismos M4.5+', en: 'Earthquakes M4.5+', ses: 'Sismos', sen: 'Quakes' },
    { id: 'natural', g: 'live', c: '#2BD9C7', i: '🌀', es: 'Eventos naturales', en: 'Natural events', ses: 'Naturales', sen: 'Natural' },
    { id: 'chokepoints', g: 'struct', c: '#FFB300', i: '⚓', es: 'Estrechos y canales', en: 'Straits & canals', ses: 'Estrechos', sen: 'Straits' },
    { id: 'instability', g: 'struct', c: '#FF6B8B', i: '🌡', es: 'Inestabilidad país', en: 'Country instability', ses: 'Países', sen: 'Countries' },
    { id: 'companies', g: 'graph', c: '#34d399', i: '🏢', es: 'Empresas (color = NRS)', en: 'Companies (color = NRS)' },
    { id: 'arcs', g: 'graph', c: '#4A9BFF', i: '🔗', es: 'Arcos de suministro', en: 'Supply arcs' },
    { id: 'portfolio', g: 'graph', c: '#FFFFFF', i: '💼', es: 'Mi cartera', en: 'My portfolio' },
    { id: 'lanes', g: 'ref', c: '#38BDF8', i: '🚢', es: 'Rutas marítimas', en: 'Shipping lanes' },
    { id: 'cables', g: 'ref', c: '#A78BFA', i: '〰', es: 'Cables submarinos', en: 'Undersea cables' },
    { id: 'fabs', g: 'ref', c: '#00E0FF', i: '🏭', es: 'Fabs críticas', en: 'Critical fabs' },
  ];
  var LBY = {}; LAYERS.forEach(function (l) { LBY[l.id] = l; });
  var OFFICIAL = ['shipping', 'policy', 'disasters', 'advisories', 'outages'];
  var LIVE = ['conflict', 'unrest', 'trade', 'quakes', 'natural'].concat(OFFICIAL);
  var SERVER_LAYERS = LIVE.concat(['chokepoints', 'instability']);
  var NAT_ICON = { wildfires: '🔥', severeStorms: '🌀', volcanoes: '🌋', floods: '🌊', earthquakes: '◎',
    drought: '☀', landslides: '⛰', seaLakeIce: '🧊', snow: '❄', tempExtremes: '🌡', dustHaze: '🌫', manmade: '⚠' };
  // Estrechos: coordenadas reales (core/geosit.py). Solo se usan si el servidor
  // no responde — sin score (no se inventa).
  var FALLBACK_CHOKE = [
    ['taiwan_strait', 'Estrecho de Taiwán', 'Taiwan Strait', 24.6, 119.8], ['luzon_strait', 'Estrecho de Luzón', 'Luzon Strait', 20.6, 121.0],
    ['kerch', 'Estrecho de Kerch', 'Kerch Strait', 45.3, 36.5], ['hormuz', 'Estrecho de Ormuz', 'Strait of Hormuz', 26.6, 56.5],
    ['malacca', 'Estrecho de Malaca', 'Strait of Malacca', 2.5, 101.0], ['bab_el_mandeb', 'Bab el-Mandeb', 'Bab el-Mandeb', 12.6, 43.3],
    ['suez', 'Canal de Suez', 'Suez Canal', 30.5, 32.35], ['panama', 'Canal de Panamá', 'Panama Canal', 9.1, -79.7],
    ['bosphorus', 'Bósforo', 'Bosphorus', 41.1, 29.05],
  ];
  var REGIONS = [
    { id: 'usa', es: 'EE.UU.', en: 'United States', lat: 38, lon: -97, keys: ['EEUU'] },
    { id: 'taiwan', es: 'Taiwán', en: 'Taiwan', lat: 23.8, lon: 121, keys: ['Taiwan'] },
    { id: 'china', es: 'China', en: 'China', lat: 32, lon: 112, keys: ['China', 'HongKong'] },
    { id: 'japan', es: 'Japón', en: 'Japan', lat: 36, lon: 138, keys: ['Japon', 'Japan'] },
    { id: 'korea', es: 'Corea del Sur', en: 'South Korea', lat: 36.5, lon: 127.8, keys: ['Corea'] },
    { id: 'europe', es: 'Europa', en: 'Europe', lat: 50, lon: 9, keys: ['Alemania', 'Francia', 'PaisesBajos', 'ReinoUnido', 'Europa', 'RestoEuropa', 'Irlanda', 'Suiza', 'Suecia', 'Finlandia', 'Noruega', 'Dinamarca', 'Italia', 'Espana', 'Belgica', 'Luxemburgo', 'Polonia', 'Lituania', 'Austria', 'Portugal', 'Grecia', 'Chequia', 'Hungria', 'Rumania', 'Ucrania'] },
    { id: 'mideast', es: 'Oriente Medio', en: 'Middle East', lat: 27, lon: 45, keys: ['Israel', 'EAU', 'Catar', 'Kuwait', 'ArabiaSaudita', 'Iran', 'Turquia', 'Egipto', 'Azerbaiyan'] },
    { id: 'row', es: 'Resto del mundo', en: 'Rest of world', lat: 0, lon: 60, keys: null },
  ];
  // Materias primas vía ETF PROXY (no precio spot): GLD/USO siguen la materia
  // prima; COPX/URA/LIT/REMX son ETFs de mineras del sector (explicado en "?").
  var COMMOD = [['USO', 'Petróleo (WTI)', 'Oil (WTI)'], ['GLD', 'Oro', 'Gold'], ['COPX', 'Cobre', 'Copper'],
    ['URA', 'Uranio', 'Uranium'], ['LIT', 'Litio', 'Lithium'], ['REMX', 'Tierras raras', 'Rare earths']];
  var BIG = { EEUU: 1, China: 1, Rusia: 1, Canada: 1, Australia: 1, Brasil: 1, India: 1, Europa: 1, RestoMundo: 1,
    RestoEuropa: 1, Kazajistan: 1, Argentina: 1, Mexico: 1, Indonesia: 1, Argelia: 1, ArabiaSaudita: 1, Iran: 1 };

  /* ── utilidades ─────────────────────────────────────────────────────── */
  function en() { try { return (window.LANG || localStorage.getItem('eco_lang') || 'es') === 'en'; } catch (e) { return false; } }
  function L(es, e) { return en() ? e : es; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function chip(k) { return window.explainChip ? window.explainChip(k) : ''; }
  function base() { return (typeof window.BASE !== 'undefined' && window.BASE) || ''; }
  function lsGet(k, d) { try { var v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } }
  function lsSet(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  function sevColor(s) { return s >= 75 ? '#FF4D6A' : s >= 55 ? '#FFB300' : s >= 35 ? '#EAD24B' : '#2BE38B'; }
  function nrsColor(n) { return n > 60 ? '#f87171' : n >= 35 ? '#f59e0b' : '#34d399'; }
  function nrsOf(id) { try { return typeof window.computeNRS === 'function' ? window.computeNRS(id) : null; } catch (e) { return null; } }
  function title(it) { return (en() ? (it.title_en || it.title) : (it.title_es || it.title)) || it.place || '?'; }
  function hav(a1, o1, a2, o2) {
    if (window.GeoCoords && window.GeoCoords.haversineKm) return window.GeoCoords.haversineKm(a1, o1, a2, o2);
    var r = Math.PI / 180, dA = (a2 - a1) * r, dO = (o2 - o1) * r;
    var x = Math.sin(dA / 2) * Math.sin(dA / 2) + Math.cos(a1 * r) * Math.cos(a2 * r) * Math.sin(dO / 2) * Math.sin(dO / 2);
    return 2 * 6371.0088 * Math.asin(Math.min(1, Math.sqrt(x)));
  }
  function ago(ts) {
    if (!ts) return '';
    var s = Math.max(0, Date.now() / 1000 - ts);
    if (s < 90) return L('ahora', 'now');
    if (s < 3600) return L('hace ' + Math.round(s / 60) + ' min', Math.round(s / 60) + ' min ago');
    if (s < 86400) return L('hace ' + Math.round(s / 3600) + ' h', Math.round(s / 3600) + ' h ago');
    return L('hace ' + Math.round(s / 86400) + ' d', Math.round(s / 86400) + ' d ago');
  }
  function utc(ts) {
    if (!ts) return '';
    try { return new Date(ts * 1000).toISOString().replace('T', ' ').slice(0, 16) + ' UTC'; } catch (e) { return ''; }
  }
  function getJSON(url, opts) {
    return fetch(base() + url, opts || {}).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!r.ok) {
          var e = new Error((j && (en() ? j.error_en : j.error_es)) || (j && j.error) || ('HTTP ' + r.status));
          e.status = r.status; throw e;
        }
        return j;
      });
    });
  }
  // textos del servidor en el idioma de la UI (el server manda error_es/error_en, source_es/source_en…)
  function errText(s) { return (s && (en() ? s.error_en : s.error_es)) || (s && s.error) || '?'; }
  function srcText(it) { return (en() ? it.source_en : it.source_es) || it.source || '—'; }
  function provText(s) { return (s && (en() ? s.provider_en : s.provider_es)) || (s && s.provider) || ''; }
  function fmtIso(iso) { return iso ? String(iso).replace('T', ' ').slice(0, 16) + ' UTC' : '?'; }
  // solo http(s) en un href (un feed alterado no puede colar javascript:/data:)
  function safeUrl(u) { return typeof u === 'string' && /^https?:\/\//i.test(u.trim()) ? u.trim() : null; }
  function staleTag(it) { return it && it.stale ? '⚠ ' + L('datos de ' + fmtIso(it.as_of) + ' · fuente caída', 'data from ' + fmtIso(it.as_of) + ' · source down') : ''; }
  function itemRadius(it) {   // misma regla que core/world.py:item_radius_km
    if (it.layer === 'quakes') { var m = +it.mag || 4.5; return Math.min(800, Math.round(60 * Math.pow(2, m - 4.5))); }
    if (it.layer === 'natural') return { wildfires: 150, severeStorms: 500, volcanoes: 200, floods: 300 }[it.category] || 250;
    var r = { conflict: 300, unrest: 250, trade: 300, chokepoints: 600, instability: 0, shipping: 600, policy: 0, disasters: 400, advisories: 0, outages: 0 }[it.layer];
    return r != null ? r : 300;
  }
  function held() {
    var pos = (window.MKT && window.MKT.pos) || {};
    return Object.keys(pos).filter(function (id) { return window.NODE_BY_ID && window.NODE_BY_ID[id]; });
  }

  /* ── explicaciones "?" (registradas en tiempo de ejecución) ──────────── */
  var _xpl = false;
  function registerExplain() {
    if (_xpl || !window.explainRegister) return;
    _xpl = true;
    var R = window.explainRegister;
    R('wm_official', {
      es: { t: 'Fuentes oficiales', b: 'Datos publicados por organismos oficiales, no por la prensa:<ul style="margin:8px 0;padding-left:18px;line-height:1.7"><li><b>FMI PortWatch</b>: cuántos buques cruzan cada día cada estrecho o canal, medido por satélite (AIS). Llega con unos días de retraso.</li><li><b>Diario oficial de EE.UU. (Federal Register)</b>: las reglas del <b>BIS</b> (exportación de chips, «Entity List») y de la <b>OFAC</b> (sanciones), tal como se publican.</li><li><b>GDACS</b> (ONU + Comisión Europea): alertas de desastre NARANJA y ROJA.</li><li><b>Departamento de Estado de EE.UU.</b>: países con aviso de viaje nivel 3 («reconsiderar») y 4 («no viajar»).</li><li><b>Cloudflare Radar</b>: cortes de internet por país (necesita una clave gratuita).</li></ul>Cada dato trae fecha y enlace al original. Si una fuente cae, la capa lo dice; nunca rellenamos con datos inventados.' },
      en: { t: 'Official sources', b: 'Data published by official bodies, not by the press:<ul style="margin:8px 0;padding-left:18px;line-height:1.7"><li><b>IMF PortWatch</b>: how many ships cross each strait or canal every day, measured by satellite (AIS). It arrives a few days late.</li><li><b>US Federal Register</b>: <b>BIS</b> rules (chip exports, the "Entity List") and <b>OFAC</b> rules (sanctions), as published.</li><li><b>GDACS</b> (UN + European Commission): ORANGE and RED disaster alerts.</li><li><b>US State Department</b>: countries with a level 3 ("reconsider") or 4 ("do not travel") travel advisory.</li><li><b>Cloudflare Radar</b>: internet outages by country (needs a free key).</li></ul>Every item carries its date and a link to the original. If a source is down, the layer says so; we never fill in made-up data.' } });
    R('wm_gpr', {
      es: { t: 'Índice de riesgo geopolítico (GPR)', b: 'Índice académico de Caldara e Iacoviello (economistas de la Reserva Federal), muy usado por bancos centrales. Cuenta cada día qué parte de las noticias de 10 grandes diarios habla de guerras, amenazas militares, terrorismo o tensiones nucleares. <b>100 = el promedio 1985-2019</b>; por encima de 150-200 hay mucha tensión percibida. Mide el riesgo que <b>percibe la prensa</b>, no víctimas ni probabilidades. «Suben en la prensa» = países cuyo índice mensual está muy por encima de su último año.' },
      en: { t: 'Geopolitical risk index (GPR)', b: 'Academic index by Caldara and Iacoviello (Federal Reserve economists), widely used by central banks. Every day it counts what share of the news in 10 major newspapers is about wars, military threats, terrorism or nuclear tensions. <b>100 = the 1985-2019 average</b>; above 150-200 means high perceived tension. It measures risk <b>perceived by the press</b>, not casualties or probabilities. "Rising in the press" = countries whose monthly index is well above their last year.' } });
    R('wm_shipping', {
      es: { t: 'Tráfico por los estrechos', b: 'Comparamos los buques por día de la <b>última semana</b> con el promedio de los <b>90 días anteriores</b>. Una caída fuerte (por ejemplo −40 %) suele significar desvíos, bloqueos o un conflicto: encarece fletes y retrasa entregas de las empresas que dependen de esa ruta. La severidad sale de la caída (−25 % ≈ 40, −50 % ≈ 80); las subidas no suman alarma.' },
      en: { t: 'Traffic through the straits', b: 'We compare ships per day over the <b>last week</b> with the average of the <b>previous 90 days</b>. A sharp drop (e.g. −40%) usually means diversions, blockades or conflict: freight gets pricier and deliveries slower for companies that depend on that route. Severity comes from the drop (−25% ≈ 40, −50% ≈ 80); increases add no alarm.' } });
    R('wm_policy', {
      es: { t: 'Reglas de chips y sanciones', b: 'Documentos oficiales de los últimos 30 días del <b>BIS</b> (controles de exportación: chips avanzados, IA, «Entity List») y de la <b>OFAC</b> (sanciones). Marcamos las empresas de tu grafo que el documento <b>nombra</b> y el país objetivo. El número es una <b>estimación por palabras clave</b> (Entity List, chips, IA, si es una regla y no un aviso…), no una opinión: abre el documento antes de decidir.' },
      en: { t: 'Chip rules & sanctions', b: 'Official documents from the last 30 days by <b>BIS</b> (export controls: advanced chips, AI, the "Entity List") and <b>OFAC</b> (sanctions). We flag the graph companies the document <b>names</b> and the target country. The number is a <b>keyword estimate</b> (Entity List, chips, AI, a rule rather than a notice…), not an opinion: open the document before deciding.' } });
    R('wm_severity', {
      es: { t: '¿Qué es la severidad de un evento?', b: 'Un número de <b>0 a 100</b> que ordena los eventos por gravedad. Cada fuente se mide distinto y lo decimos tal cual:<ul style="margin:8px 0;padding-left:18px;line-height:1.7"><li><b>Sismos (USGS)</b>: según la magnitud (M4.5≈13, M6.5≈63, M7.5≈88) + la alerta oficial PAGER de USGS y avisos de tsunami.</li><li><b>Eventos GDELT</b> (conflicto, protestas, sanciones): según cuántos artículos y fuentes cubren ese lugar (10 artículos ≈ 63, 25 ≈ 80) — mide <b>atención mediática</b>, no víctimas. Solo conflictos con actores armados (militares, rebeldes, insurgentes).</li><li><b>Eventos naturales (NASA EONET)</b>: <b>estimada</b> por tipo (volcán 55, tormenta 45, incendio 30…) + viento o área cuando EONET la publica. Se muestran los que NASA actualizó dentro de la ventana (24h / 7d).</li><li><b>Tráfico marítimo (FMI)</b>: según la caída de buques/día (7 d vs 90 d).</li><li><b>Reglas y sanciones (EE.UU.)</b>: <b>estimada</b> por palabras clave (Entity List, chips, IA) y empresas nombradas.</li><li><b>Alertas GDACS</b>: roja 85, naranja 60 (nivel oficial).</li><li><b>Riesgo país (EE.UU.)</b>: nivel 4 «no viajar» = 85, nivel 3 = 65 (Departamento de Estado).</li><li><b>Cortes de internet</b>: nacional en curso 80, regional 55; terminados, menos.</li><li><b>Estrechos y países</b>: el score de la Sala de Situación (base curada + noticias + factores activos).</li></ul>El tamaño del punto en el globo es la severidad; los ≥ 60 laten.' },
      en: { t: 'What is an event\'s severity?', b: 'A number from <b>0 to 100</b> that ranks events by seriousness. Each source is measured differently and we say so:<ul style="margin:8px 0;padding-left:18px;line-height:1.7"><li><b>Earthquakes (USGS)</b>: by magnitude (M4.5≈13, M6.5≈63, M7.5≈88) + USGS\'s official PAGER alert and tsunami flags.</li><li><b>GDELT events</b> (conflict, protests, sanctions): by how many articles and sources cover that place (10 articles ≈ 63, 25 ≈ 80) — it measures <b>media attention</b>, not casualties. Conflict only with armed actors (military, rebels, insurgents).</li><li><b>Natural events (NASA EONET)</b>: <b>estimated</b> by type (volcano 55, storm 45, wildfire 30…) + wind or area when EONET publishes it. Shown if NASA updated them within the window (24h / 7d).</li><li><b>Shipping traffic (IMF)</b>: by the drop in ships/day (7d vs 90d).</li><li><b>Rules & sanctions (US)</b>: <b>estimated</b> from keywords (Entity List, chips, AI) and named companies.</li><li><b>GDACS alerts</b>: red 85, orange 60 (official level).</li><li><b>Country risk (US)</b>: level 4 "do not travel" = 85, level 3 = 65 (State Department).</li><li><b>Internet outages</b>: nationwide ongoing 80, regional 55; ended ones, less.</li><li><b>Straits and countries</b>: the Situation Room score (curated base + news + active factors).</li></ul>Dot size on the globe is severity; ≥ 60 pulses.' } });
    R('wm_relevance', {
      es: { t: '¿Qué es la relevancia?', b: 'Cuánto te debería importar un evento <b>como inversionista de esta cadena</b>: <b>55% severidad</b> del evento + <b>45% exposición</b> de tu grafo (empresas y fabs cerca, país). Un sismo fuerte en medio del océano importa menos que uno moderado junto a las fábricas de TSMC.<ul style="margin:8px 0;padding-left:18px;line-height:1.7"><li>La <b>inestabilidad por país</b> es un índice de todo un país, no un evento: cuenta con exposición 0 en el orden (si no, EE.UU. o Japón, con muchas empresas, saldrían siempre arriba aunque estén estables).</li><li>Al menos <b>la mitad de la lista</b> se reserva a eventos en vivo (si los hay), para que los estrechos y países — que cambian poco — no tapen lo nuevo.</li></ul>Es un cálculo fijo, sin IA.' },
      en: { t: 'What is relevance?', b: 'How much an event should matter to you <b>as an investor in this chain</b>: <b>55% event severity</b> + <b>45% exposure</b> of your graph (companies and fabs nearby, country). A strong quake in the middle of the ocean matters less than a moderate one next to TSMC\'s fabs.<ul style="margin:8px 0;padding-left:18px;line-height:1.7"><li><b>Country instability</b> is an index for a whole country, not an event: it ranks with exposure 0 (otherwise the US or Japan, with many companies, would always be on top even when stable).</li><li>At least <b>half of the list</b> is reserved for live events (when there are any), so straits and countries — which change slowly — do not hide what is new.</li></ul>A fixed formula, no AI.' } });
    R('wm_exposure', {
      es: { t: '¿Qué es la exposición de la cadena?', b: 'Qué empresas de tu grafo podrían verse afectadas por un evento:<ul style="margin:8px 0;padding-left:18px;line-height:1.7"><li><b>Cerca</b>: su sede conocida (curada o ciudad del catálogo) está dentro del radio del evento.</li><li><b>Mismo país</b>: están registradas en ese país pero no sabemos su ubicación exacta (solo en países compactos: un sismo en California no expone a todo EE.UU.).</li><li><b>Fabs críticas</b> cercanas (fábricas de chips, EUV, HBM).</li></ul>El índice (0-100) pondera cercanía, fabs y país (el aporte de "mismo país" tiene tope: un conteo de todo el país no reemplaza a la cercanía). Para la <b>inestabilidad por país</b> el número es otro: <b>% de tu grafo</b> registrado en ese país. Es <b>proximidad</b>, no daño confirmado.' },
      en: { t: 'What is supply-chain exposure?', b: 'Which companies in your graph could be affected by an event:<ul style="margin:8px 0;padding-left:18px;line-height:1.7"><li><b>Near</b>: their known HQ (curated or catalog city) is within the event radius.</li><li><b>Same country</b>: registered in that country but exact location unknown (compact countries only: a California quake does not expose all of the US).</li><li>Nearby <b>critical fabs</b> (chip plants, EUV, HBM).</li></ul>The index (0-100) weighs proximity, fabs and country (the "same country" part is capped: a whole-country count does not replace proximity). For <b>country instability</b> the number is different: the <b>% of your graph</b> registered in that country. It is <b>proximity</b>, not confirmed damage.' } });
    R('wm_choke_score', {
      es: { t: '¿Qué es el score de un estrecho?', b: 'Riesgo 0-100 de un paso marítimo clave (Taiwán, Ormuz, Suez…): <b>base estructural curada</b> (qué tan crítico es para la cadena) + <b>actividad de noticias</b> de los últimos 7 días (GDELT) + <b>factores sistémicos activos</b> de tu grafo que lo mencionan. No hay datos de tráfico de barcos (AIS): no se inventan.<br><br><b>Simular cierre</b> propaga el shock por el grafo real con el motor de matrices: análisis, no predicción.' },
      en: { t: 'What is a strait\'s score?', b: 'Risk 0-100 of a key sea passage (Taiwan, Hormuz, Suez…): <b>curated structural base</b> (how critical it is to the chain) + <b>news activity</b> over the last 7 days (GDELT) + <b>active systemic factors</b> in your graph that mention it. There is no ship-traffic (AIS) data: nothing is made up.<br><br><b>Simulate closure</b> propagates the shock through the real graph with the matrix engine: analysis, not prediction.' } });
    R('wm_instability', {
      es: { t: '¿Qué es la inestabilidad por país?', b: 'Índice 0-100 por país: <b>base estructural curada</b> (guerra, sanciones, tensión militar) + <b>noticias</b> de 7 días (GDELT) + <b>factores activos</b> del grafo. Al abrirlo verás las empresas de tu grafo registradas en ese país.' },
      en: { t: 'What is country instability?', b: 'A 0-100 index per country: <b>curated structural base</b> (war, sanctions, military tension) + 7-day <b>news</b> (GDELT) + active graph <b>factors</b>. Opening it lists the companies in your graph registered in that country.' } });
    R('wm_systemic', {
      es: { t: '¿Qué es el nivel sistémico?', b: 'Qué tan cerca está la red de suministro de que un golpe <b>se auto-sostenga</b> (efecto dominó). Se calcula con el motor de matrices: amortiguación × radio espectral ρ(T).<br><br><b>&lt; 0,75</b> estable · <b>0,75-0,9</b> tenso · <b>0,9-1</b> crítico · <b>≥ 1</b> supercrítico (los shocks no se apagan solos). Necesita la base de datos de la ontología.' },
      en: { t: 'What is the systemic level?', b: 'How close the supply network is to a shock <b>sustaining itself</b> (domino effect). Computed by the matrix engine: damping × spectral radius ρ(T).<br><br><b>&lt; 0.75</b> stable · <b>0.75-0.9</b> strained · <b>0.9-1</b> critical · <b>≥ 1</b> supercritical (shocks do not die out). Needs the ontology database.' } });
    R('wm_etf_proxy', {
      es: { t: '¿Qué es "materias primas vía ETF proxy"?', b: 'No mostramos el precio spot de la materia prima (no tenemos esa fuente en vivo): mostramos <b>fondos cotizados (ETFs)</b> que la siguen, con su precio en USD y su variación del día.<ul style="margin:8px 0;padding-left:18px;line-height:1.7"><li><b>USO</b> (petróleo WTI, futuros) y <b>GLD</b> (oro físico) siguen a la materia prima.</li><li><b>COPX</b> (cobre), <b>URA</b> (uranio), <b>LIT</b> (litio) y <b>REMX</b> (tierras raras) invierten en <b>empresas mineras</b> del sector: se mueven con él, pero no son el precio del metal.</li></ul>Sirven para ver rápido si un evento (Ormuz, sanciones…) ya mueve los mercados.' },
      en: { t: 'What is "commodities via ETF proxy"?', b: 'We do not show the commodity\'s spot price (we have no live source for it): we show <b>exchange-traded funds (ETFs)</b> that track it, with their USD price and daily change.<ul style="margin:8px 0;padding-left:18px;line-height:1.7"><li><b>USO</b> (WTI oil, futures) and <b>GLD</b> (physical gold) track the commodity.</li><li><b>COPX</b> (copper), <b>URA</b> (uranium), <b>LIT</b> (lithium) and <b>REMX</b> (rare earths) hold <b>mining companies</b> in that sector: they move with it, but are not the metal price.</li></ul>They let you quickly see whether an event (Hormuz, sanctions…) is already moving markets.' } });
    R('wm_reference', {
      es: { t: '¿Por qué "referencia (no en vivo)"?', b: 'Las <b>rutas marítimas</b> y los <b>cables submarinos</b> se dibujan de forma esquemática entre puntos reales conocidos (puertos, estrechos, estaciones de aterrizaje). Sirven para ver qué pasa cerca de ellos, pero <b>no</b> muestran barcos ni el estado de los cables en tiempo real. Las <b>fabs críticas</b> son sitios curados a nivel ciudad.' },
      en: { t: 'Why "reference (not live)"?', b: '<b>Shipping lanes</b> and <b>undersea cables</b> are drawn schematically between known real points (ports, straits, landing stations). They help you see what happens near them, but they do <b>not</b> show live ships or cable status. <b>Critical fabs</b> are curated city-level sites.' } });
  }

  /* ── estilos (inyectados) ───────────────────────────────────────────── */
  function ensureStyles() {
    if (document.getElementById('wm-css')) return;
    var st = document.createElement('style'); st.id = 'wm-css';
    st.textContent = [
      '.wm{position:relative;width:100%;height:100%;min-height:520px;overflow:hidden;color:#E8EDFB;font-family:Inter,system-ui,sans-serif;background:radial-gradient(120% 90% at 50% 45%,#0a1628 0%,#050a14 55%,#02040a 100%)}',
      '.wm *{box-sizing:border-box}',
      '.wm-canvas{position:absolute;inset:0;width:100%;height:100%;display:block;cursor:grab;touch-action:none;outline:none}',
      '.wm-canvas:active{cursor:grabbing}',
      '.wm-top{position:absolute;left:0;right:0;top:0;height:38px;z-index:6;display:flex;align-items:center;gap:10px;padding:0 12px;background:linear-gradient(180deg,rgba(3,7,15,.95),rgba(3,7,15,.72));border-bottom:1px solid rgba(0,224,255,.14);backdrop-filter:blur(6px)}',
      '.wm-brand{display:flex;align-items:center;gap:8px;flex:0 0 auto;font-size:11.5px;font-weight:800;letter-spacing:.12em;white-space:nowrap}',
      '.wm-live{font-size:9px;font-weight:800;letter-spacing:.12em;color:#2BE38B;border:1px solid rgba(43,227,139,.45);border-radius:999px;padding:2px 8px;display:inline-flex;align-items:center;gap:5px}',
      '.wm-live.off{color:#FF8FA3;border-color:rgba(255,77,106,.45)}',
      '.wm-live::before{content:"";width:6px;height:6px;border-radius:50%;background:currentColor;box-shadow:0 0 8px currentColor;animation:wmBlink 1.6s ease-in-out infinite}',
      '@keyframes wmBlink{0%,100%{opacity:1}50%{opacity:.25}}',
      '.wm-ticker{flex:1;min-width:0;overflow:hidden;position:relative;height:100%;display:flex;align-items:center;-webkit-mask-image:linear-gradient(90deg,transparent,#000 4%,#000 96%,transparent);mask-image:linear-gradient(90deg,transparent,#000 4%,#000 96%,transparent)}',
      '.wm-track{display:inline-flex;gap:28px;white-space:nowrap;animation:wmScroll 90s linear infinite;padding-right:28px}',
      '.wm-ticker:hover .wm-track{animation-play-state:paused}',
      '@keyframes wmScroll{from{transform:translateX(0)}to{transform:translateX(-50%)}}',
      '.wm-tk{font-size:11.5px;color:#C7D0EA;cursor:pointer;display:inline-flex;align-items:center;gap:6px}',
      '.wm-tk:hover{color:#fff}',
      '.wm-tk i{width:7px;height:7px;border-radius:50%;display:inline-block;flex:0 0 7px}',
      '.wm-tk b{font-size:9.5px;letter-spacing:.08em;font-weight:800}',
      '.wm-tk .ta{color:#6F7B98;font-size:10.5px}',
      '.wm-clock{flex:0 0 auto;font-family:"JetBrains Mono",ui-monospace,monospace;font-size:10.5px;color:#7C87A3}',
      '.wm-panel{position:absolute;z-index:5;background:rgba(5,10,20,.86);border:1px solid rgba(122,158,255,.18);border-radius:13px;backdrop-filter:blur(10px);box-shadow:0 10px 40px rgba(0,0,0,.45);overflow:hidden;display:flex;flex-direction:column}',
      '.wm-left{left:10px;top:48px;width:252px;max-height:calc(100% - 104px)}',
      '.wm-right{right:10px;top:48px;width:352px;max-height:calc(100% - 104px)}',
      '.wm-panel.hid{display:none}',
      '.wm-ph{display:flex;align-items:center;gap:8px;padding:9px 12px;border-bottom:1px solid rgba(122,158,255,.12);font-size:10px;font-weight:800;letter-spacing:.12em;color:#9BA6C4;text-transform:uppercase;flex:0 0 auto}',
      '.wm-ph .x{margin-left:auto;cursor:pointer;color:#7C87A3;font-size:14px;line-height:1;padding:2px 6px;border-radius:6px}',
      '.wm-ph .x:hover{background:rgba(122,158,255,.12);color:#fff}',
      '.wm-pb{overflow-y:auto;overflow-x:hidden;padding:8px 12px 12px;flex:1 1 auto;min-height:0}',
      '.wm-pb::-webkit-scrollbar{width:6px}.wm-pb::-webkit-scrollbar-thumb{background:rgba(122,158,255,.2);border-radius:3px}',
      '.wm-g{font-size:9px;font-weight:800;letter-spacing:.14em;color:#5E6884;margin:10px 0 4px;text-transform:uppercase;display:flex;align-items:center;gap:4px}',
      '.wm-g:first-child{margin-top:2px}',
      '.wm-lay{display:flex;align-items:center;gap:7px;padding:4px 2px;font-size:12px;color:#C7D0EA;cursor:pointer;user-select:none;border-radius:7px}',
      '.wm-lay:hover{background:rgba(122,158,255,.07)}',
      '.wm-lay.off{opacity:.45}',
      '.wm-lay .dot{width:9px;height:9px;border-radius:50%;flex:0 0 9px;box-shadow:0 0 6px currentColor}',
      '.wm-lay .nm{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
      '.wm-lay .ct{font-family:"JetBrains Mono",ui-monospace,monospace;font-size:10.5px;color:#9BA6C4}',
      '.wm-st{font-size:9px;font-weight:700;border-radius:999px;padding:1px 6px;white-space:nowrap}',
      '.wm-st.ok{color:#2BE38B;background:rgba(43,227,139,.1)}.wm-st.err{color:#FF8FA3;background:rgba(255,77,106,.12)}',
      '.wm-st.pend{color:#FFD27A;background:rgba(255,179,0,.1)}.wm-st.ref{color:#9BA6C4;background:rgba(122,158,255,.1)}',
      '.wm-note{font-size:10px;color:#6F7B98;line-height:1.45;margin-top:8px}',
      '.wm-bottom{position:absolute;z-index:5;left:50%;transform:translateX(-50%);bottom:10px;display:flex;align-items:center;gap:8px;flex-wrap:wrap;justify-content:center;max-width:calc(100% - 650px);min-width:300px}',
      '.wm-seg{display:inline-flex;background:rgba(5,10,20,.88);border:1px solid rgba(122,158,255,.22);border-radius:999px;padding:2px}',
      '.wm-seg button{background:none;border:0;color:#9BA6C4;font:700 11px Inter,system-ui,sans-serif;padding:5px 12px;border-radius:999px;cursor:pointer}',
      '.wm-seg button.on{background:rgba(0,224,255,.16);color:#00E0FF}',
      '.wm-btn{background:rgba(5,10,20,.88);border:1px solid rgba(122,158,255,.22);color:#C7D0EA;border-radius:999px;font:600 11px Inter,system-ui,sans-serif;padding:5px 11px;cursor:pointer;white-space:nowrap}',
      '.wm-btn:hover{border-color:rgba(0,224,255,.5);color:#fff}',
      '.wm-legend{display:flex;align-items:center;gap:9px;flex-wrap:wrap;background:rgba(5,10,20,.8);border:1px solid rgba(122,158,255,.16);border-radius:10px;padding:5px 10px;font-size:10px;color:#9BA6C4}',
      '.wm-legend i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:4px;vertical-align:-1px}',
      '.wm-reopen{position:absolute;z-index:5;top:48px;background:rgba(5,10,20,.88);border:1px solid rgba(122,158,255,.25);color:#C7D0EA;border-radius:10px;padding:6px 10px;font:700 11px Inter,system-ui,sans-serif;cursor:pointer}',
      '.wm-tip{position:absolute;z-index:8;pointer-events:none;background:rgba(4,8,16,.96);border:1px solid rgba(0,224,255,.35);border-radius:9px;padding:7px 10px;font-size:11.5px;color:#E8EDFB;max-width:260px;display:none;line-height:1.4;box-shadow:0 8px 24px rgba(0,0,0,.5)}',
      '.wm-tip .m{color:#8B96B5;font-size:10.5px}',
      '.wm-kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:4px 0 10px}',
      '.wm-kpi{border:1px solid rgba(122,158,255,.12);border-radius:9px;padding:6px 7px;background:rgba(10,18,34,.55);cursor:pointer;min-width:0}',
      '.wm-kpi:hover{border-color:rgba(0,224,255,.35)}',
      '.wm-kpi .k{font-size:9px;color:#7C87A3;font-weight:700;letter-spacing:.04em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '.wm-kpi .v{font-family:"JetBrains Mono",ui-monospace,monospace;font-size:16px;font-weight:800;margin-top:1px}',
      '.wm-sec{margin-top:12px}',
      '.wm-sh{font-size:10px;font-weight:800;letter-spacing:.1em;color:#7C87A3;text-transform:uppercase;margin-bottom:6px;display:flex;align-items:center;gap:4px}',
      '.wm-sh .r{margin-left:auto;text-transform:none;letter-spacing:0;font-weight:600;color:#5E6884;font-size:9.5px}',
      '.wm-row{display:flex;gap:8px;align-items:flex-start;padding:7px 4px;border-bottom:1px solid rgba(122,158,255,.07);cursor:pointer;border-radius:6px}',
      '.wm-row:hover{background:rgba(122,158,255,.06)}',
      '.wm-row:last-child{border-bottom:0}',
      '.wm-rel{flex:0 0 30px;height:22px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-family:"JetBrains Mono",ui-monospace,monospace;font-size:11px;font-weight:800;color:#04060B}',
      '.wm-rt{flex:1;min-width:0}',
      '.wm-rt .t{font-size:12px;color:#E8EDFB;line-height:1.35;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}',
      '.wm-rt .m{font-size:10px;color:#7C87A3;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '.wm-gauge{display:flex;align-items:center;gap:12px;border:1px solid rgba(122,158,255,.14);border-radius:10px;padding:8px 10px;background:rgba(10,18,34,.5)}',
      '.wm-gauge .n{font-family:"JetBrains Mono",ui-monospace,monospace;font-size:22px;font-weight:800}',
      '.wm-gauge .d{font-size:10.5px;color:#9BA6C4;line-height:1.4}',
      '.wm-tag{display:inline-flex;align-items:center;gap:5px;font-size:9.5px;font-weight:800;letter-spacing:.08em;padding:2px 8px;border-radius:999px;border:1px solid}',
      '.wm-h1{font-size:15px;font-weight:750;line-height:1.3;margin:8px 0 4px;color:#fff;word-wrap:break-word}',
      '.wm-meta{font-size:11px;color:#8B96B5;line-height:1.5}',
      '.wm-bar{height:6px;border-radius:4px;background:rgba(122,158,255,.12);overflow:hidden;flex:1}',
      '.wm-bar i{display:block;height:100%}',
      '.wm-kv{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px}',
      '.wm-kv>div{border:1px solid rgba(122,158,255,.1);border-radius:8px;padding:5px 8px;background:rgba(10,18,34,.45);min-width:0}',
      '.wm-kv .k{font-size:9px;color:#7C87A3;text-transform:uppercase;letter-spacing:.06em}',
      '.wm-kv .v{font-size:12.5px;color:#E8EDFB;font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '.wm-co{display:flex;align-items:center;gap:7px;padding:5px 2px;border-bottom:1px solid rgba(122,158,255,.06);font-size:11.5px}',
      '.wm-co .nm{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#E8EDFB}',
      '.wm-co .ds{font-family:"JetBrains Mono",ui-monospace,monospace;font-size:10px;color:#7C87A3}',
      '.wm-co .nr{font-family:"JetBrains Mono",ui-monospace,monospace;font-size:11px;font-weight:800;width:24px;text-align:right}',
      '.wm-mini{font:700 10px Inter,system-ui,sans-serif;padding:3px 8px;border-radius:999px;cursor:pointer;color:#00E0FF;background:rgba(0,224,255,.08);border:1px solid rgba(0,224,255,.35);white-space:nowrap}',
      '.wm-mini:hover{background:rgba(0,224,255,.18)}',
      '.wm-act{display:block;width:100%;margin-top:10px;padding:8px;border-radius:9px;cursor:pointer;font:700 12px Inter,system-ui,sans-serif;color:#04060B;background:linear-gradient(90deg,#00E0FF,#7A9EFF);border:0}',
      '.wm-act.ghost{background:rgba(0,224,255,.08);color:#00E0FF;border:1px solid rgba(0,224,255,.4)}',
      '.wm-simres{margin-top:8px;border:1px solid rgba(255,77,106,.3);border-radius:9px;padding:8px 10px;background:rgba(255,77,106,.06)}',
      '.wm-vrow{display:flex;align-items:center;gap:7px;font-size:11px;color:#C7D0EA;padding:2px 0}',
      '.wm-vrow .n{flex:0 0 112px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
      '.wm-vrow .vb{flex:1;height:4px;border-radius:3px;background:rgba(122,158,255,.1);overflow:hidden}',
      '.wm-vrow .vb i{display:block;height:100%;background:linear-gradient(90deg,#FF4D6A,#FFB300)}',
      '.wm-vrow .p{font-family:"JetBrains Mono",ui-monospace,monospace;font-size:10.5px;width:36px;text-align:right;color:#FF8FA3}',
      '.wm-link{color:#7AB8FF;text-decoration:none;font-size:11.5px;line-height:1.4;display:block;padding:3px 0}',
      '.wm-link:hover{text-decoration:underline}',
      '.wm-back{cursor:pointer;color:#00E0FF;font-size:11px;font-weight:700;letter-spacing:0;text-transform:none}',
      '.wm-load{color:#7C87A3;font-size:12px;font-style:italic;padding:14px 4px;text-align:center}',
      '.wm-chips{display:flex;flex-wrap:wrap;gap:6px}',
      '.wm-mbar{display:none}',
      '.wm-empty{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#9bd1ff;font-size:13px;text-align:center;padding:24px}',
      /* ── modo angosto (móvil / Cabina estrecha): hojas inferiores ── */
      '.wm.nr .wm-panel{left:0;right:0;top:auto;bottom:0;width:auto;max-height:64%;border-radius:16px 16px 0 0;transform:translateY(105%);transition:transform .25s ease;display:flex}',
      '.wm.nr .wm-panel.open{transform:translateY(0)}',
      '.wm.nr .wm-panel.hid{display:flex}',
      '.wm.nr .wm-bottom,.wm.nr .wm-reopen{display:none}',
      '.wm.nr .wm-mbar{display:flex;position:absolute;z-index:4;left:8px;right:8px;bottom:8px;gap:6px;justify-content:space-between;align-items:center}',
      '.wm.nr .wm-mbar .wm-btn{flex:1;text-align:center;padding:8px 6px;font-size:11.5px}',
      '.wm.nr .wm-clock{display:none}',
      '.wm.nr .wm-brand .wm-bt{display:none}',
      '.wm.nr .wm-ph .grab{display:block;position:absolute;left:50%;top:4px;width:38px;height:4px;border-radius:3px;background:rgba(122,158,255,.3);transform:translateX(-50%)}',
      '.wm-ph .grab{display:none}',
      '.wm-ph{position:relative}',
    ].join('\n');
    document.head.appendChild(st);
  }

  /* ── armazón DOM ────────────────────────────────────────────────────── */
  function shell() {
    return '<div class="wm" id="wm">' +
      '<canvas class="wm-canvas" id="wm-canvas" tabindex="0" aria-label="' + esc(L('Globo del World Monitor', 'World Monitor globe')) + '"></canvas>' +
      '<div class="wm-top"><div class="wm-brand"><span class="wm-live" id="wm-live">' + esc(L('EN VIVO', 'LIVE')) + '</span><span class="wm-bt">WORLD MONITOR</span></div>' +
      '<div class="wm-ticker" id="wm-ticker"><div class="wm-track" id="wm-track"></div></div><span class="wm-clock" id="wm-clock"></span></div>' +
      '<aside class="wm-panel wm-left" id="wm-left"></aside>' +
      '<aside class="wm-panel wm-right" id="wm-right"></aside>' +
      '<button class="wm-reopen" id="wm-reopen-l" style="left:10px;display:none" data-act="reopen" data-side="left">☰ ' + esc(L('Capas', 'Layers')) + '</button>' +
      '<button class="wm-reopen" id="wm-reopen-r" style="right:10px;display:none" data-act="reopen" data-side="right">◉ Intel</button>' +
      '<div class="wm-bottom" id="wm-bottom"></div>' +
      '<div class="wm-mbar" id="wm-mbar"></div>' +
      '<div class="wm-tip" id="wm-tip"></div>' +
      '</div>';
  }

  function $(id) { return document.getElementById(id); }

  /* ── panel de capas ─────────────────────────────────────────────────── */
  function statusPill(id) {
    var l = LBY[id];
    if (l.g === 'ref') {
      if (S.refErr) return '<span class="wm-st err" title="' + esc(S.refErr) + '">⚠</span>';
      return '<span class="wm-st ref">' + esc(L('ref', 'ref')) + '</span>';
    }
    if (l.g === 'graph') return '';
    if (S.eventsErr && !S.events) return '<span class="wm-st err" title="' + esc(S.eventsErr) + '">' + esc(L('sin servidor', 'no server')) + '</span>';
    var s = S.events && S.events.sources && S.events.sources[id];
    if (!s) return '<span class="wm-st pend">…</span>';
    if (s.error_code === 'refreshing') return '<span class="wm-st pend" title="' + esc(errText(s)) + '">' + esc(L('actualizando', 'refreshing')) + '</span>';
    if (s.pending) return '<span class="wm-st pend">' + esc(L('cargando', 'loading')) + '</span>';
    if (s.error_code === 'busy' && !s.stale) return '<span class="wm-st pend" title="' + esc(errText(s)) + '">' + esc(L('en cola', 'queued')) + '</span>';
    if (!s.ok && s.stale) return '<span class="wm-st pend" title="' + esc(errText(s) + ' · ' + L('datos de ', 'data from ') + fmtIso(s.as_of)) + '">' + esc(L('en caché', 'cached')) + '</span>';
    // W1: fuente en pausa (404/403 repetidos) → "en pausa" con el próximo intento; no es un fallo pasajero
    if (!s.ok && s.error_code === 'needs_key') return '<span class="wm-st pend" title="' + esc(errText(s)) + '">🔑 ' + esc(L('falta clave', 'needs key')) + '</span>';
    if (!s.ok && s.error_code === 'source_unavailable') return '<span class="wm-st err" title="' + esc(errText(s) + (s.retry_at ? ' · ' + L('próximo intento ', 'next try ') + fmtIso(s.retry_at) : '')) + '">' + esc(L('en pausa', 'paused')) + '</span>';
    if (!s.ok) return '<span class="wm-st err" title="' + esc(errText(s)) + '">' + esc(L('caída', 'down')) + '</span>';
    // W1: capas CURADAS (juicio humano revisado en curated_as_of) — no se presentan como "en vivo"
    if (s.static) {
      var li = (s.live_inputs || []);
      return '<span class="wm-st ' + (li.length ? 'ok' : 'ref') + '" title="' + esc(provText(s) + ' · ' + L('base revisada ', 'base reviewed ') + (s.curated_as_of || '?') +
        (li.length ? ' · ' + L('+ en vivo: ', '+ live: ') + li.join(', ') : '') + (s.news_live === false ? ' · ' + L('noticias GDELT en pausa', 'GDELT news paused') : '')) + '">' +
        esc(li.length ? L('curado + vivo', 'curated + live') : L('curado', 'curated')) + '</span>';
    }
    // GDELT eventos (15 min): se carga por tandas → dice cuántas horas de la ventana hay
    if (s.coverage_hours != null && s.window_hours && s.coverage_hours < s.window_hours)
      return '<span class="wm-st ok" title="' + esc(provText(s) + ' · ' + L('cargadas ' + s.coverage_hours + ' h de ' + s.window_hours + ' h; se completa solo', 'loaded ' + s.coverage_hours + ' h of ' + s.window_hours + ' h; filling in automatically')) + '">' +
        esc(L('vivo · ' + s.coverage_hours + ' h', 'live · ' + s.coverage_hours + ' h')) + '</span>';
    return '<span class="wm-st ok" title="' + esc(provText(s) + (s.as_of ? ' · ' + s.as_of : '')) + '">' + esc(L('vivo', 'live')) + '</span>';
  }
  function layerCount(id) {
    if (id === 'companies') return (window.NODES || []).length;
    if (id === 'arcs') return Math.min(260, (window.LINKS || []).length);
    if (id === 'portfolio') return held().length;
    if (id === 'lanes') return S.ref ? S.ref.lanes.length : 0;
    if (id === 'cables') return S.ref ? S.ref.cables.length : 0;
    if (id === 'fabs') return S.ref ? S.ref.fabs.length : 0;
    var s = S.events && S.events.sources && S.events.sources[id];
    if (id === 'chokepoints' && (!s || !s.count)) return FALLBACK_CHOKE.length;
    return s ? s.count : 0;
  }
  function renderLayers() {
    var el = $('wm-left'); if (!el) return;
    var groups = [['official', L('Fuentes oficiales · en vivo', 'Official sources · live')], ['live', L('En vivo', 'Live')], ['struct', L('Estructural · curado + noticias', 'Structural · curated + news')],
      ['graph', L('Tu grafo', 'Your graph')], ['ref', L('Referencia · no en vivo', 'Reference · not live')]];
    var h = '<div class="wm-ph"><span class="grab"></span>☰ ' + esc(L('Capas', 'Layers')) + '<span class="x" data-act="collapse" data-side="left" title="' + esc(L('Ocultar', 'Hide')) + '">—</span></div><div class="wm-pb">';
    groups.forEach(function (g) {
      h += '<div class="wm-g">' + esc(g[1]) + (g[0] === 'ref' ? chip('wm_reference') : g[0] === 'struct' ? chip('wm_choke_score') : g[0] === 'official' ? chip('wm_official') : '') + '</div>';
      LAYERS.filter(function (l) { return l.g === g[0]; }).forEach(function (l) {
        var on = !!S.vis[l.id];
        h += '<div class="wm-lay' + (on ? '' : ' off') + '" data-act="toggle" data-layer="' + l.id + '" role="checkbox" aria-checked="' + on + '">' +
          '<span class="dot" style="background:' + l.c + ';color:' + l.c + '"></span><span class="nm">' + esc(l.i + ' ' + L(l.es, l.en)) + '</span>' +
          '<span class="ct">' + layerCount(l.id) + '</span>' + statusPill(l.id) + '</div>';
      });
    });
    h += '<div class="wm-note">' + esc(L('Fuentes: FMI PortWatch (tránsito diario de buques por satélite), diario oficial de EE.UU. (reglas del BIS y la OFAC, últimos 30 días), GDACS (alertas naranja/roja de la ONU y la UE), Departamento de Estado (riesgo país nivel 3-4), Cloudflare Radar (cortes de internet, con clave), GDELT 2.0 (eventos de conflicto, protestas y sanciones codificados de la prensa cada 15 min: señal de prensa), USGS (sismos), NASA EONET (eventos naturales), Sala de Situación Khipu. El filtro 24h/7d aplica a sismos, eventos naturales y alertas GDACS; el tráfico marítimo es diario (con unos días de retraso) y las reglas cubren 30 días. Las capas de referencia no son en vivo.',
      'Sources: IMF PortWatch (daily satellite ship transits), US Federal Register (BIS and OFAC rules, last 30 days), GDACS (UN/EU orange/red alerts), State Department (level 3-4 country risk), Cloudflare Radar (internet outages, needs a key), GDELT 2.0 (conflict, protest and sanctions events coded from the press every 15 min: press signal), USGS (earthquakes), NASA EONET (natural events), Khipu Situation Room. The 24h/7d filter applies to earthquakes, natural events and GDACS alerts; shipping traffic is daily (a few days behind) and rules cover 30 days. Reference layers are not live.')) + '</div>';
    var errs = SERVER_LAYERS.filter(function (id) { var s = S.events && S.events.sources && S.events.sources[id]; return s && !s.ok && !s.pending && s.error_code !== 'busy'; });
    if (errs.length) {
      h += '<div class="wm-note" style="color:#FF8FA3">⚠ ' + esc(L('Fuentes caídas ahora: ', 'Sources down right now: ')) +
        errs.map(function (id) {
          var s = S.events.sources[id];
          var extra = s.stale ? ' · ' + L('se muestran datos de ', 'showing data from ') + fmtIso(s.as_of) + ' (⚠)' : s.expired_dropped ? ' · ' + L('datos demasiado viejos descartados', 'too-old data discarded') : '';
          return esc(L(LBY[id].es, LBY[id].en) + ' (' + errText(s) + extra + ')');
        }).join(' · ') + '</div>';
    }
    h += '</div>';
    el.innerHTML = h;
  }

  /* ── barra inferior / móvil ─────────────────────────────────────────── */
  function renderBottom() {
    var seg = '<div class="wm-seg" role="group">' + ['24h', '7d'].map(function (w) {
      return '<button data-act="win" data-win="' + w + '" class="' + (S.win === w ? 'on' : '') + '">' + w + '</button>';
    }).join('') + '</div>';
    var b = $('wm-bottom');
    if (b) {
      b.innerHTML = seg +
        '<div class="wm-legend"><span><i style="background:#FF3B5C"></i>' + esc(L('conflicto', 'conflict')) + '</span><span><i style="background:#FF8A3D"></i>' + esc(L('protestas', 'unrest')) +
        '</span><span><i style="background:#FFD23F"></i>' + esc(L('comercio', 'trade')) + '</span><span><i style="background:#B983FF"></i>' + esc(L('sismos', 'quakes')) +
        '</span><span><i style="background:#2BD9C7"></i>' + esc(L('naturales', 'natural')) + '</span><span><i style="background:#5B8CFF"></i>' + esc(L('buques', 'ships')) +
        '</span><span><i style="background:#A3E635"></i>' + esc(L('reglas', 'rules')) + '</span><span><i style="background:#E879F9"></i>' + esc(L('alertas', 'alerts')) + '</span><span style="opacity:.8">' + esc(L('tamaño = severidad', 'size = severity')) + chip('wm_severity') + '</span></div>' +
        '<button class="wm-btn" data-act="zoom" data-f="0.8" title="Zoom +">＋</button><button class="wm-btn" data-act="zoom" data-f="1.25" title="Zoom −">－</button>' +
        '<button class="wm-btn" data-act="reset">⟲ ' + esc(L('Vista', 'View')) + '</button>';
    }
    var m = $('wm-mbar');
    if (m) {
      m.innerHTML = '<button class="wm-btn" data-act="sheet" data-side="left">☰ ' + esc(L('Capas', 'Layers')) + '</button>' + seg +
        '<button class="wm-btn" data-act="sheet" data-side="right">◉ Intel</button>';
    }
  }

  /* ── ticker de titulares ────────────────────────────────────────────── */
  function renderTicker() {
    var tr = $('wm-track'), live = $('wm-live'); if (!tr) return;
    var srcs = (S.events && S.events.sources) || {};
    var anyOk = LIVE.some(function (id) { return srcs[id] && srcs[id].ok; });
    var anyPend = LIVE.some(function (id) { return srcs[id] && srcs[id].pending; });
    if (live) {
      live.className = 'wm-live' + (anyOk || anyPend ? '' : ' off');
      live.textContent = anyOk ? L('EN VIVO', 'LIVE') : anyPend ? L('CONECTANDO', 'CONNECTING') : L('SIN FUENTES', 'NO FEEDS');
    }
    var items = S.events ? S.events.items.filter(function (i) { return LIVE.indexOf(i.layer) >= 0 && S.vis[i.layer]; }) : [];
    items = items.slice().sort(function (a, b) { return (b.severity || 0) - (a.severity || 0); }).slice(0, 22);
    var h;
    if (!items.length) {
      var allDown = S.events && LIVE.every(function (id) { return srcs[id] && !srcs[id].ok && !srcs[id].pending; });
      h = '<span class="wm-tk" style="cursor:default">' + esc(S.loading && !S.events ? L('Conectando con las fuentes en vivo…', 'Connecting to live sources…')
        : S.eventsErr && !S.events ? L('Servidor no disponible: se muestran tu grafo y las capas de referencia.', 'Server unavailable: showing your graph and reference layers.')
          : allDown ? L('Las fuentes en vivo (GDELT, USGS, NASA EONET) no responden ahora. Se muestran estrechos, países, tu grafo y las capas de referencia.',
            'Live sources (GDELT, USGS, NASA EONET) are not responding right now. Showing straits, countries, your graph and reference layers.')
            : anyPend ? L('Cargando fuentes en vivo…', 'Loading live sources…')
              : L('Sin eventos en vivo en esta ventana.', 'No live events in this window.')) + '</span>';
      tr.style.animation = 'none'; tr.style.paddingLeft = '0';
    } else {
      h = items.map(function (it) {
        var l = LBY[it.layer];
        return '<span class="wm-tk" data-act="sel" data-id="' + esc(it.id) + '"><i style="background:' + l.c + ';box-shadow:0 0 6px ' + l.c + '"></i><b style="color:' + l.c + '">' +
          esc(L(l.ses, l.sen).toUpperCase()) + '</b>' + esc(String(title(it)).slice(0, 110)) +
          (it.place && it.place !== title(it) ? ' · ' + esc(String(it.place).slice(0, 40)) : '') + '<span class="ta"' + (it.stale ? ' style="color:#FFB300"' : '') + '>' + esc(it.stale ? staleTag(it) : it.time_kind === 'window' ? S.win : ago(it.ts)) + '</span></span>';
      }).join('');
      h = h + h;                       // duplicado → bucle sin salto
      tr.style.animation = ''; tr.style.paddingLeft = '';
      tr.style.animationDuration = Math.max(40, items.length * 8) + 's';
    }
    tr.innerHTML = h;
  }
  function tickClock() {
    var c = $('wm-clock'); if (!c) return;
    c.textContent = new Date().toISOString().slice(11, 16) + ' UTC';
  }

  /* ── panel derecho: Situación global ────────────────────────────────── */
  function systemicHTML() {
    var sy = S.systemic;
    if (!sy || sy.spectral_radius == null) {
      return '<div class="wm-gauge"><div class="d">🧮 ' + esc(L('Nivel sistémico', 'Systemic level')) + chip('wm_systemic') + '<br>' +
        esc(L('No disponible ahora (el motor de matrices necesita la base de datos).', 'Not available right now (the matrix engine needs the database).')) + '</div></div>';
    }
    var dr = sy.damping_rho != null ? sy.damping_rho : 0.6 * sy.spectral_radius;
    var lvl = dr >= 1 ? [L('SUPERCRÍTICO', 'SUPERCRITICAL'), '#FF4D6A'] : dr >= 0.9 ? [L('CRÍTICO', 'CRITICAL'), '#FF7A45']
      : dr >= 0.75 ? [L('TENSO', 'STRAINED'), '#FFB300'] : [L('ESTABLE', 'STABLE'), '#2BE38B'];
    var nf = (sy.active_factors || []).length;
    return '<div class="wm-gauge"><div class="n" style="color:' + lvl[1] + '">' + dr.toFixed(2) + '</div><div class="d"><b style="color:' + lvl[1] + '">' + lvl[0] + '</b> · ' +
      esc(L('nivel sistémico de la red', 'network systemic level')) + chip('wm_systemic') + (nf ? '<br>⚡ ' + nf + ' ' + esc(L('factor(es) activo(s)', 'active factor(s)')) : '') + '</div></div>';
  }
  // 🌍 índice de riesgo geopolítico global (Caldara-Iacoviello, Fed): valor diario, tendencia y países que suben
  function gprHTML() {
    if (!S.gpr && !S.gprLoading) {
      S.gprLoading = true;
      getJSON('/api/world/gpr').then(function (d) { S.gpr = d; }).catch(function () { S.gpr = { ok: false }; })
        .then(function () { S.gprLoading = false; if (!S.sel) renderSituation(); });
    }
    var g = S.gpr;
    if (!g) return '';
    if (!g.ok || !g.daily) return '<div class="wm-meta" style="margin-top:8px;color:#7C87A3">🌍 ' + esc(L('Índice de riesgo geopolítico: ', 'Geopolitical risk index: ') + ((en() ? g.error_en : g.error_es) || L('no disponible', 'unavailable'))) + '</div>';
    var d = g.daily, v = d.value, up = d.avg30 && v > d.avg30 * 1.1, down = d.avg30 && v < d.avg30 * 0.9;
    var col = v >= 200 ? '#FF4D6A' : v >= 140 ? '#FFB300' : '#2BE38B';
    var hist = (d.history || []).slice(-90), path = '';
    if (hist.length > 1) {
      var vals = hist.map(function (h) { return h.value; }), lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals) || 1;
      path = hist.map(function (h, i) { return (i ? 'L' : 'M') + (i * 160 / (hist.length - 1)).toFixed(1) + ',' + (30 - (h.value - lo) / Math.max(1, hi - lo) * 28).toFixed(1); }).join('');
    }
    var cs = ((g.monthly || {}).countries || []).filter(function (c) { return (c.vs_12m || 0) >= 1.3; }).slice(0, 3);
    return '<div class="wm-gauge" style="margin-top:8px"><div class="n" style="color:' + col + '">' + Math.round(v) + '</div><div class="d"><b style="color:' + col + '">' +
      esc(L('Riesgo geopolítico global', 'Global geopolitical risk')) + '</b>' + chip('wm_gpr') + '<br>' +
      esc((up ? '▲ ' : down ? '▼ ' : '≈ ') + L('vs promedio 30 d (', 'vs 30-day avg (') + Math.round(d.avg30) + ')' + (d.percentile_1y != null ? ' · ' + L('más alto que el ', 'higher than ') + d.percentile_1y + L(' % del último año', '% of the last year') : '') + ' · ' + d.date) +
      (path ? '<br><svg viewBox="0 0 160 32" width="160" height="32" style="margin-top:4px"><path d="' + path + '" fill="none" stroke="' + col + '" stroke-width="1.5"/></svg>' : '') +
      (cs.length ? '<br>' + esc(L('Suben en la prensa: ', 'Rising in the press: ') + cs.map(function (c) { return c.name_es + ' ×' + c.vs_12m; }).join(' · ')) : '') +
      '</div></div>';
  }
  function kpisHTML() {
    var h = '<div class="wm-kpis">';
    LIVE.concat(['chokepoints']).forEach(function (id) {
      var l = LBY[id], s = S.events && S.events.sources && S.events.sources[id];
      var v = s ? (s.pending ? '…' : s.count) : (S.eventsErr ? '—' : '…');
      h += '<div class="wm-kpi" data-act="top" data-layer="' + id + '" title="' + esc(L(l.es, l.en) + ' · ' + L('ir al más severo', 'go to the most severe')) + '"><div class="k">' + esc(l.i + ' ' + L(l.ses, l.sen)) + '</div><div class="v" style="color:' + l.c + '">' + v + '</div></div>';
    });
    return h + '</div>';
  }
  function briefHTML() {
    var h = '<div class="wm-sec"><div class="wm-sh">⚡ ' + esc(L('Lo más relevante ahora', 'Most relevant now')) + chip('wm_relevance') +
      '<span class="r">' + esc(S.win) + '</span></div>';
    if (!S.brief) return h + '<div class="wm-load">' + esc(S.eventsErr ? L('No disponible (servidor sin respuesta).', 'Not available (server not responding).') : L('Calculando exposición…', 'Computing exposure…')) + '</div></div>';
    var items = (S.brief.items || []).slice(0, 9);
    if (!items.length) return h + '<div class="wm-load">' + esc(L('Sin eventos con datos en esta ventana.', 'No events with data in this window.')) + '</div></div>';
    items.forEach(function (it) {
      S.items[it.id] = S.items[it.id] || it;
      var l = LBY[it.layer] || LBY.conflict, ex = it.exposure || {};
      var ic = it.layer === 'natural' ? (NAT_ICON[it.category] || l.i) : l.i;
      h += '<div class="wm-row" data-act="sel" data-id="' + esc(it.id) + '"><div class="wm-rel" style="background:' + sevColor(it.relevance) + '" title="' + esc(L('relevancia', 'relevance')) + '">' + it.relevance + '</div>' +
        '<div class="wm-rt"><div class="t">' + esc(ic + ' ' + title(it)) + '</div><div class="m">' +
        '<span style="color:' + l.c + '">' + esc(L(l.es, l.en)) + '</span> · ' + esc(L('sev.', 'sev.')) + ' ' + (it.severity || 0) +
        (ex.count ? ' · 🏢 ' + ex.count : '') + (ex.fabs && ex.fabs.length ? ' · 🏭 ' + ex.fabs.length : '') +
        (it.stale ? ' · <span style="color:#FFB300">⚠ ' + esc(L('datos de ' + fmtIso(it.as_of) + ' (fuente caída)', 'data from ' + fmtIso(it.as_of) + ' (source down)')) + '</span>'
          : it.time_kind === 'window' || it.time_kind === 'current' ? '' : ' · ' + esc(ago(it.ts))) + '</div></div></div>';
    });
    return h + '</div>';
  }
  function portfolioHTML() {
    var ids = held();
    if (!ids.length || !S.events || !window.GeoCoords) return '';
    var NB = window.NODE_BY_ID || {}, hits = [];
    var ev = S.events.items.filter(function (i) { return LIVE.indexOf(i.layer) >= 0 || i.layer === 'chokepoints'; });
    ids.forEach(function (id) {
      var g = window.GeoCoords.geoCoord(NB[id]);
      var best = null;
      ev.forEach(function (it) {
        var near = false;
        if (g.precision === 'hq' || g.precision === 'city') near = hav(g.lat, g.lng, it.lat, it.lon) <= itemRadius(it);
        if (!near && it.country_key && it.country_key === g.country && !BIG[g.country]) near = true;
        if ((it.layer === 'chokepoints' || it.layer === 'shipping' || it.layer === 'policy') && (it.affected || []).indexOf(id) >= 0) near = true;
        if (near && (!best || (it.severity || 0) > (best.severity || 0))) best = it;
      });
      if (best) hits.push({ id: id, it: best });
    });
    var h = '<div class="wm-sec"><div class="wm-sh">💼 ' + esc(L('Tu cartera frente a los eventos', 'Your portfolio vs events')) + chip('wm_exposure') + '</div>';
    if (!hits.length) return h + '<div class="wm-meta">' + esc(L('Ninguna de tus ' + ids.length + ' posiciones tiene eventos activos cerca en esta ventana.', 'None of your ' + ids.length + ' positions has active events nearby in this window.')) + '</div></div>';
    hits.sort(function (a, b) { return (b.it.severity || 0) - (a.it.severity || 0); });
    h += '<div class="wm-meta" style="margin-bottom:4px">' + esc(L(hits.length + ' de ' + ids.length + ' posiciones con eventos cerca:', hits.length + ' of ' + ids.length + ' positions with events nearby:')) + '</div>';
    hits.slice(0, 4).forEach(function (x) {
      var n = NB[x.id], l = LBY[x.it.layer];
      h += '<div class="wm-row" data-act="sel" data-id="' + esc(x.it.id) + '"><div class="wm-rt"><div class="t">💼 ' + esc(n.label) + ' ← <span style="color:' + l.c + '">' + esc(title(x.it)).slice(0, 80) + '</span></div>' +
        '<div class="m">' + esc(L(l.es, l.en)) + ' · ' + esc(L('sev.', 'sev.')) + ' ' + (x.it.severity || 0) + '</div></div></div>';
    });
    return h + '</div>';
  }
  function regionsHTML() {
    var NODES = window.NODES || [], GC = window.GeoCoords;
    if (!NODES.length || !GC) return '';
    var pos = (window.MKT && window.MKT.pos) || {};
    var ck0 = NODES.length + ':' + Object.keys(pos).length;
    var agg = S._reg && S._reg.k === ck0 ? S._reg.agg : null;
    if (!agg) {
    agg = {};
    REGIONS.forEach(function (r) { agg[r.id] = { n: 0, s: 0, p: 0 }; });
    NODES.forEach(function (n) {
      var ck = GC.geoCoord(n).country, rid = 'row';
      for (var i = 0; i < REGIONS.length; i++) { if (REGIONS[i].keys && REGIONS[i].keys.indexOf(ck) >= 0) { rid = REGIONS[i].id; break; } }
      var a = agg[rid]; a.n++; var v = nrsOf(n.id); a.s += (v == null ? 0 : v); if (pos[n.id]) a.p++;
    });
    S._reg = { k: ck0, agg: agg };
    }
    var h = '<div class="wm-sec"><div class="wm-sh">🗺 ' + esc(L('Tu grafo por región', 'Your graph by region')) + chip('nrs') + '<span class="r">' + esc(L('empresas · NRS medio', 'companies · avg NRS')) + '</span></div>';
    REGIONS.map(function (r) { return { r: r, a: agg[r.id] }; }).filter(function (x) { return x.a.n; })
      .sort(function (x, y) { return y.a.n - x.a.n; }).forEach(function (x) {
        var avg = Math.round(x.a.s / x.a.n);
        h += '<div class="wm-co" style="cursor:pointer" data-act="focus" data-lat="' + x.r.lat + '" data-lon="' + x.r.lon + '"><span class="nm">' + esc(L(x.r.es, x.r.en)) + (x.a.p ? ' <span style="color:#fff" title="' + esc(L('posiciones en tu cartera', 'positions in your portfolio')) + '">💼' + x.a.p + '</span>' : '') +
          '</span><span class="ds">' + x.a.n + '</span><span class="nr" style="color:' + nrsColor(avg) + '">' + avg + '</span></div>';
      });
    return h + '</div>';
  }
  /* listas completas de estrechos y países (score + clic = seleccionar) */
  function layerItems(layer) {
    var its = (S.events ? S.events.items : []).filter(function (i) { return i.layer === layer; });
    if (!its.length && layer === 'chokepoints') its = Object.keys(S.items).map(function (k) { return S.items[k]; }).filter(function (i) { return i.layer === layer; });
    return its.slice().sort(function (a, b) { return (b.severity == null ? -1 : b.severity) - (a.severity == null ? -1 : a.severity); });
  }
  function rankedHTML(layer) {
    var l = LBY[layer], its = layerItems(layer);
    if (!its.length) return '';
    var open = !!S.lists[layer], shown = open ? its : its.slice(0, 3);
    var h = '<div class="wm-sec"><div class="wm-sh">' + esc(l.i + ' ' + L(l.es, l.en)) + chip(layer === 'chokepoints' ? 'wm_choke_score' : 'wm_instability') +
      '<span class="r">' + esc(L('score 0-100', 'score 0-100')) + '</span></div>';
    shown.forEach(function (it) {
      var sv = it.severity, news = it.news && it.news.count != null ? '📰 ' + it.news.count + ' ' + L('art. 7d', 'art. 7d') : L('noticias: aún sin datos', 'news: no data yet');
      if (it.live_shipping && it.live_shipping.change_pct != null) news += ' · ⛴ ' + (it.live_shipping.change_pct > 0 ? '+' : '') + Math.round(it.live_shipping.change_pct) + ' % ' + L('buques', 'ships');
      if (it.advisory_level) news += ' · 🛂 ' + L('nivel ', 'level ') + it.advisory_level;
      if (it.live_events && it.live_events.count) news += ' · ⚔ ' + it.live_events.count + ' ' + L('eventos 24h', 'events 24h');
      h += '<div class="wm-row" data-act="sel" data-id="' + esc(it.id) + '"><div class="wm-rel" style="background:' + (sv == null ? '#7C87A3' : sevColor(sv)) + '">' + (sv == null ? '—' : sv) + '</div>' +
        '<div class="wm-rt"><div class="t">' + esc(title(it)) + '</div><div class="m">' + esc(sv == null ? L('sin score (servidor no disponible)', 'no score (server unavailable)')
          : L('base', 'base') + ' ' + (it.base != null ? it.base : '—') + ' · ' + news + (it.factors && it.factors.length ? ' · ⚡ ' + it.factors.length : '')) + '</div></div></div>';
    });
    if (its.length > 3) {
      h += '<button class="wm-mini" data-act="list" data-layer="' + layer + '" style="margin-top:6px">' +
        esc(open ? L('ver menos', 'show less') : L('ver los ' + its.length, 'show all ' + its.length)) + '</button>';
    }
    return h + '</div>';
  }
  // ⛴ tránsito diario por estrechos (FMI PortWatch): caída/subida 7 d vs 90 d previos
  function shippingHTML() {
    var its = layerItems('shipping'), s = S.events && S.events.sources && S.events.sources.shipping;
    if (!its.length) return s && !s.ok && !s.pending ? '<div class="wm-sec"><div class="wm-sh">⛴ ' + esc(L('Tráfico por los estrechos', 'Traffic through the straits')) + '</div><div class="wm-meta" style="color:#FF8FA3">⚠ ' + esc(errText(s)) + '</div></div>' : '';
    var open = !!S.lists.shipping;
    var sorted = its.slice().sort(function (a, b) { return (a.change_pct || 0) - (b.change_pct || 0); });
    var shown = open ? sorted : sorted.slice(0, 5);
    var h = '<div class="wm-sec"><div class="wm-sh">⛴ ' + esc(L('Tráfico por los estrechos', 'Traffic through the straits')) + chip('wm_shipping') +
      '<span class="r">' + esc(L('7 d vs 90 d · FMI', '7d vs 90d · IMF')) + '</span></div>';
    shown.forEach(function (it) {
      var c = it.change_pct, col = c <= -25 ? '#FF4D6A' : c <= -10 ? '#FFB300' : c >= 10 ? '#2BE38B' : '#9BA6C4';
      h += '<div class="wm-row" data-act="sel" data-id="' + esc(it.id) + '"><div class="wm-rel" style="background:' + col + '">' + (c > 0 ? '+' : '') + Math.round(c) + '%</div>' +
        '<div class="wm-rt"><div class="t">' + esc(L(it.title_es, it.title_en).split(':')[0]) + (it.data_caveat ? ' ⚠' : '') + '</div><div class="m">' +
        esc(L('≈ ' + it.transits_7d_avg + ' buques/día (antes ' + it.transits_base_avg + ') · datos al ', '≈ ' + it.transits_7d_avg + ' ships/day (was ' + it.transits_base_avg + ') · data as of ') + String(it.time || '').slice(0, 10)) + '</div></div></div>';
    });
    if (its.length > 5) h += '<button class="wm-mini" data-act="list" data-layer="shipping" style="margin-top:6px">' + esc(open ? L('ver menos', 'show less') : L('ver los ' + its.length, 'show all ' + its.length)) + '</button>';
    return h + '</div>';
  }
  // 📜 reglas del BIS (exportación de chips) y de la OFAC (sanciones): lista COMPLETA de 30 días
  function policyHTML() {
    if (!S.policy && !S.policyLoading) { S.policyLoading = true; getJSON('/api/world/policy?limit=40').then(function (d) { S.policy = d; }).catch(function () { S.policy = { items: [], error: true }; })
      .then(function () { S.policyLoading = false; if (!S.sel) renderSituation(); }); }
    var h = '<div class="wm-sec"><div class="wm-sh">📜 ' + esc(L('Reglas de chips y sanciones de EE.UU.', 'US chip rules & sanctions')) + chip('wm_policy') + '<span class="r">' + esc(L('30 días · oficial', '30 days · official')) + '</span></div>';
    if (!S.policy) return h + '<div class="wm-load">' + esc(L('Cargando el diario oficial…', 'Loading the official register…')) + '</div></div>';
    var st = S.policy.status || {};
    if (S.policy.error || (st.ok === false && !(S.policy.items || []).length)) return h + '<div class="wm-meta" style="color:#FF8FA3">⚠ ' + esc(st.error_es ? errText(st) : L('El diario oficial no respondió.', 'The official register did not respond.')) + '</div></div>';
    var its = (S.policy.items || []).slice().sort(function (a, b) { return (b.severity || 0) - (a.severity || 0) || (b.ts || 0) - (a.ts || 0); });
    if (!its.length) return h + '<div class="wm-meta">' + esc(L('Sin reglas nuevas del BIS ni de la OFAC en 30 días.', 'No new BIS or OFAC rules in 30 days.')) + '</div></div>';
    var open = !!S.lists.policy, shown = open ? its : its.slice(0, 4), mine = held();
    shown.forEach(function (it) {
      var hit = (it.affected || []).filter(function (id) { return mine.indexOf(id) >= 0; });
      var u = safeUrl(it.url);
      h += '<div class="wm-row"' + (it.lat != null ? ' data-act="sel" data-id="' + esc(it.id) + '"' : '') + '><div class="wm-rel" style="background:' + sevColor(it.severity || 0) + '" title="' + esc(L('importancia estimada', 'estimated importance')) + '">' + (it.severity || 0) + '</div>' +
        '<div class="wm-rt"><div class="t">' + esc(it.agency + ' · ' + it.title) + '</div><div class="m">' + esc(String(it.time || '').slice(0, 10) + ' · ' + L(it.kind_es, it.kind_en)) +
        ((it.countries || []).length ? ' · 🌐 ' + esc(it.countries.slice(0, 3).join(', ')) : '') +
        ((it.companies || []).length ? ' · 🏢 ' + esc(it.companies.slice(0, 4).map(function (c) { return c.label; }).join(', ')) : '') +
        (hit.length ? ' · <b style="color:#FFB300">💼 ' + esc(L('en tu cartera', 'in your portfolio')) + '</b>' : '') +
        (u ? ' · <a class="wm-link" style="display:inline" href="' + esc(u) + '" target="_blank" rel="noopener noreferrer">' + esc(L('documento ↗', 'document ↗')) + '</a>' : '') + '</div></div></div>';
    });
    if (its.length > 4) h += '<button class="wm-mini" data-act="list" data-layer="policy" style="margin-top:6px">' + esc(open ? L('ver menos', 'show less') : L('ver los ' + its.length, 'show all ' + its.length)) + '</button>';
    return h + '</div>';
  }
  function commoditiesHTML() {
    var h = '<div class="wm-sec"><div class="wm-sh">⛏ ' + esc(L('Materias primas', 'Commodities')) + chip('wm_etf_proxy') + '<span class="r">' + esc(L('vía ETF proxy · USD', 'via ETF proxy · USD')) + '</span></div>';
    var q = S.quotes || {};
    var boxes = COMMOD.map(function (c) {
      var d = q[c[0]];
      if (!d || (d.live == null && d.close == null)) return '';
      var px = d.live != null ? d.live : d.close;
      var pct = d.pct != null ? d.pct : (d.prev ? (px - d.prev) / d.prev * 100 : null);
      var col = pct == null ? '#9BA6C4' : pct >= 0 ? '#2BE38B' : '#FF4D6A';
      return '<div class="wm-kpi" style="cursor:default" title="' + esc(c[0] + ' · ' + L('precio del ETF, no spot', 'ETF price, not spot')) + '"><div class="k">' + esc(L(c[1], c[2])) + ' · ' + c[0] + '</div>' +
        '<div class="v" style="font-size:13px;color:#E8EDFB">$' + Number(px).toFixed(2) + '</div>' +
        '<div style="font-family:JetBrains Mono,monospace;font-size:10.5px;font-weight:700;color:' + col + '">' + (pct == null ? '—' : (pct >= 0 ? '+' : '') + Number(pct).toFixed(1) + '%') + '</div></div>';
    }).join('');
    if (!boxes) {
      return h + '<div class="wm-meta">' + esc(!S.quotesTs || (!S.quotes && !S.quotesErr) ? L('Cargando cotizaciones…', 'Loading quotes…')
        : L('Cotizaciones no disponibles ahora (proveedor de mercado sin respuesta).', 'Quotes not available right now (market data provider not responding).')) + '</div></div>';
    }
    return h + '<div class="wm-kpis" style="margin-bottom:0">' + boxes + '</div></div>';
  }
  function loadQuotes(force) {
    if (!force && S.quotesTs && Date.now() - S.quotesTs < 300000) return;
    S.quotesTs = Date.now();
    getJSON('/api/quotes/live', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tickers: COMMOD.map(function (c) { return c[0]; }) }) })
      .then(function (d) { S.quotes = d && d.quotes ? d.quotes : (d || {}); S.quotesErr = null; })
      .catch(function (e) { S.quotesErr = e.message || 'error'; })
      .then(function () { if (!S.sel && S.root) renderSituation(); });
  }
  function scenariosHTML() {
    if (!window.nexusCore || typeof window.nexusCore.runPreset !== 'function') return '';
    var sc = [['taiwan_conflict', L('⚔ Conflicto Taiwán', '⚔ Taiwan conflict')], ['china_chip_ban_total', L('🚫 Veto total de chips a China', '🚫 Total China chip ban')],
      ['hbm_shortage_2027', L('💾 Escasez HBM 2027', '💾 HBM shortage 2027')]];
    return '<div class="wm-sec"><div class="wm-sh">🧪 ' + esc(L('Escenarios what-if (simulación)', 'What-if scenarios (simulation)')) + '</div><div class="wm-chips">' +
      sc.map(function (s) { return '<button class="wm-mini" data-act="scen" data-preset="' + s[0] + '">' + esc(s[1]) + '</button>'; }).join('') + '</div></div>';
  }
  function renderSituation() {
    var el = $('wm-right'); if (!el) return;
    var asOf = S.events && S.events.as_of ? S.events.as_of.replace('T', ' ').slice(0, 16) + ' UTC' : '';
    el.innerHTML = '<div class="wm-ph"><span class="grab"></span>🌐 ' + esc(L('Situación global', 'Global situation')) +
      '<span style="margin-left:auto;font-weight:600;letter-spacing:0;text-transform:none;color:#5E6884;font-size:9.5px">' + esc(asOf) + '</span>' +
      '<span class="x" data-act="reload" title="' + esc(L('Actualizar', 'Refresh')) + '" style="margin-left:4px">⟳</span><span class="x" data-act="collapse" data-side="right" title="' + esc(L('Ocultar', 'Hide')) + '" style="margin-left:0">—</span></div>' +
      '<div class="wm-pb">' + systemicHTML() + gprHTML() + '<div style="height:8px"></div>' + kpisHTML() + briefHTML() + portfolioHTML() +
      shippingHTML() + policyHTML() + rankedHTML('chokepoints') + rankedHTML('instability') + commoditiesHTML() + regionsHTML() + scenariosHTML() +
      '<div class="wm-note">' + esc(L('Análisis informativo con datos públicos. No es asesoría financiera.', 'Informational analysis from public data. Not financial advice.')) + '</div></div>';
  }

  /* ── panel derecho: detalle del elemento seleccionado ───────────────── */
  function detailHead(tag, color) {
    return '<div class="wm-ph"><span class="grab"></span><span class="wm-back" data-act="back">← ' + esc(L('Situación global', 'Global situation')) + '</span>' +
      '<span class="x" data-act="collapse" data-side="right" title="' + esc(L('Ocultar', 'Hide')) + '">—</span></div><div class="wm-pb">' +
      '<span class="wm-tag" style="color:' + color + ';border-color:' + color + '66;background:' + color + '14">' + esc(tag) + '</span>';
  }
  function sevRow(sev, key) {
    if (sev == null) {
      return '<div class="wm-meta" style="margin-top:10px;color:#FFD27A">' + esc(L('Score no disponible: el servidor no respondió. Se muestra solo la ubicación (referencia).',
        'Score not available: the server did not respond. Only the location is shown (reference).')) + '</div>';
    }
    return '<div style="display:flex;align-items:center;gap:8px;margin-top:10px"><span class="wm-meta" style="flex:0 0 auto">' + esc(L('Severidad', 'Severity')) + chip(key || 'wm_severity') + '</span>' +
      '<div class="wm-bar"><i style="width:' + Math.max(3, Math.min(100, sev || 0)) + '%;background:' + sevColor(sev || 0) + '"></i></div>' +
      '<b style="font-family:JetBrains Mono,monospace;color:' + sevColor(sev || 0) + '">' + (sev || 0) + '</b></div>';
  }
  function coRow(c, extra) {
    var nrs = nrsOf(c.id); if (nrs == null) nrs = c.nrs;
    var mine = ((window.MKT && window.MKT.pos) || {})[c.id] ? ' 💼' : '';
    var approx = c.precision === 'hq' || c.precision === 'city' ? '' : ' ≈';
    return '<div class="wm-co"><span class="nm" title="' + esc(c.label + (c.place ? ' · ' + c.place : '')) + '">' + esc(c.label) + mine + '</span>' +
      (c.distance_km != null ? '<span class="ds">' + c.distance_km + ' km' + approx + '</span>' : (extra ? '<span class="ds">' + esc(extra) + '</span>' : '')) +
      '<span class="nr" style="color:' + nrsColor(nrs == null ? 50 : nrs) + '" title="NRS">' + (nrs == null ? '—' : nrs) + '</span>' +
      '<button class="wm-mini" data-act="xray" data-id="' + esc(c.id) + '" title="X-Ray">🔬</button></div>';
  }
  function exposureHTML(it, ex) {
    var h = '<div class="wm-sec"><div class="wm-sh">🏢 ' + esc(L('Exposición de tu cadena', 'Your supply-chain exposure')) + chip('wm_exposure') + '</div>';
    if (!ex) return h + '<div class="wm-load">' + esc(L('Buscando empresas cercanas…', 'Looking for nearby companies…')) + '</div></div>';
    if (ex.error) return h + '<div class="wm-meta" style="color:#FF8FA3">' + esc(L('No se pudo calcular: ', 'Could not compute: ') + ex.error) + '</div></div>';
    var share = ex.index_kind === 'share';
    h += '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px"><span class="wm-meta">' + esc(share ? L('% de tu grafo en el país', '% of your graph in the country') : L('Índice', 'Index')) + '</span><div class="wm-bar"><i style="width:' + Math.max(2, ex.index) + '%;background:' + sevColor(ex.index) + '"></i></div><b style="font-family:JetBrains Mono,monospace;color:' + sevColor(ex.index) + '">' + (share ? ex.share_pct + '%' : ex.index) + '</b></div>';
    var affIds = {};
    var aff = (it.layer === 'chokepoints' ? (it.affected || []) : []).map(function (id) {
      var n = (window.NODE_BY_ID || {})[id]; if (n) affIds[id] = 1; return n ? { id: id, label: n.label, precision: 'hq' } : null;
    }).filter(Boolean);
    if (aff.length) {
      h += '<div class="wm-g">' + esc(L('Dependientes directos (curado)', 'Direct dependents (curated)')) + '</div>';
      aff.forEach(function (c) { h += coRow(c, L('dep.', 'dep.')); });
    }
    var nearCos = (ex.companies || []).filter(function (c) { return !affIds[c.id]; });
    if (nearCos.length) {
      h += '<div class="wm-g">' + esc(L('Sede o sitio principal a ≤ ' + ex.radius_km + ' km', 'HQ or main site within ' + ex.radius_km + ' km')) + ' · ' + ex.near_count + '</div>';
      nearCos.slice(0, 8).forEach(function (c) { h += coRow(c); });
    }
    if (ex.fabs && ex.fabs.length) {
      h += '<div class="wm-g">🏭 ' + esc(L('Fabs críticas cerca', 'Critical fabs nearby')) + '</div>';
      ex.fabs.slice(0, 5).forEach(function (f) {
        h += '<div class="wm-co"><span class="nm">' + esc(f.site) + '</span><span class="ds">' + f.distance_km + ' km</span>' +
          (f.company_known ? '<button class="wm-mini" data-act="xray" data-id="' + esc(f.company) + '">🔬</button>' : '') + '</div>';
      });
    }
    if (ex.same_country && ex.same_country.length) {
      h += '<div class="wm-g">' + esc(L('Registradas en el país (ubicación aprox.)', 'Registered in the country (approx. location)')) + ' · ' + ex.country_count + '</div>';
      ex.same_country.slice(0, S.moreCountry ? ex.same_country.length : 6).forEach(function (c) { h += coRow(c, '≈'); });
      if (!S.moreCountry && ex.same_country.length > 6) h += '<button class="wm-mini" data-act="more" style="margin-top:6px">+ ' + (ex.same_country.length - 6) + ' ' + esc(L('más', 'more')) + '</button>';
      if (S.moreCountry && ex.country_count > ex.same_country.length) h += '<div class="wm-meta" style="margin-top:4px">' + esc(L('Mostrando las ' + ex.same_country.length + ' más conectadas de ' + ex.country_count + '.', 'Showing the ' + ex.same_country.length + ' most connected of ' + ex.country_count + '.')) + '</div>';
    }
    if (!aff.length && !ex.count) h += '<div class="wm-meta">' + esc(L('Ninguna empresa de tu grafo con sede conocida cerca. El evento puede igual afectar precios de energía o fletes.', 'No company in your graph with a known HQ nearby. The event may still move energy or freight prices.')) + '</div>';
    var shock = simShock(it, ex);
    if (shock.length) {
      h += '<button class="wm-act ghost" data-act="sim">◉ ' + esc(it.layer === 'chokepoints' ? L('Simular cierre', 'Simulate closure') : L('Simular impacto en la cadena', 'Simulate supply-chain impact')) + '</button>' +
        '<div class="wm-meta" style="margin-top:4px">' + esc(it.layer === 'chokepoints' ? L('¿Y si este paso se cierra? Propaga el shock desde sus ' + shock.length + ' dependientes por el grafo real.', 'What if this passage closes? Propagates the shock from its ' + shock.length + ' dependents through the real graph.')
        : L('¿Y si estas ' + shock.length + ' empresas se detienen? Magnitud = severidad del evento. Es un what-if, no una predicción.', 'What if these ' + shock.length + ' companies stop? Magnitude = event severity. A what-if, not a prediction.')) + '</div>';
    }
    h += '<div id="wm-simout"></div>';
    return h + '</div>';
  }
  function simShock(it, ex) {
    var ids = [];
    if (it.layer === 'chokepoints' || ((it.layer === 'shipping' || it.layer === 'policy') && (it.affected || []).length)) ids = (it.affected || []).slice();
    else if (ex && !ex.error) ids = (ex.companies || []).map(function (c) { return c.id; });
    var NB = window.NODE_BY_ID || {};
    return ids.filter(function (id, i) { return NB[id] && ids.indexOf(id) === i; }).slice(0, 8);
  }
  function eventDetailHTML(it) {
    var l = LBY[it.layer] || LBY.conflict;
    var ic = it.layer === 'natural' ? (NAT_ICON[it.category] || l.i) : l.i;
    var h = detailHead(ic + ' ' + L(l.es, l.en).toUpperCase(), l.c);
    h += '<div class="wm-h1">' + esc(title(it)) + '</div>';
    var when = it.stale ? (it.time_kind === 'window'
        ? L('⚠ Datos de ' + fmtIso(it.as_of) + ': la fuente no responde ahora. Cubren las ' + S.win + ' previas a esa hora, NO las últimas ' + S.win + '.', '⚠ Data from ' + fmtIso(it.as_of) + ': the source is not responding. It covers the ' + S.win + ' before that time, NOT the last ' + S.win + '.')
        : L('⚠ Datos de ' + fmtIso(it.as_of) + ' (fuente caída). ', '⚠ Data from ' + fmtIso(it.as_of) + ' (source down). ') + (it.ts ? ago(it.ts) + ' · ' + utc(it.ts) : ''))
      : it.time_kind === 'window' ? L('Cobertura en las últimas ' + S.win + ' (GDELT agrega por ventana, sin hora exacta)', 'Coverage over the last ' + S.win + ' (GDELT aggregates by window, no exact time)')
      : it.time_kind === 'current' ? L('Valor actual', 'Current value')
      : it.time_kind === 'published' ? L('Publicado el ', 'Published on ') + String(it.time || '').slice(0, 10)
        : it.time_kind === 'last_update' ? L('Última actualización: ', 'Last update: ') + ago(it.ts) + ' · ' + utc(it.ts) : ago(it.ts) + ' · ' + utc(it.ts);
    var place = (it.layer === 'chokepoints' || it.layer === 'instability') ? (it.lat.toFixed(1) + '°, ' + it.lon.toFixed(1) + '°')
      : (it.place && it.place !== title(it) ? it.place : (it.lat.toFixed(2) + ', ' + it.lon.toFixed(2)));
    h += '<div class="wm-meta">📍 ' + esc(place) + '<br>' + (it.stale ? '<span style="color:#FFB300">' + esc(when) + '</span>' : '🕒 ' + esc(when)) + '</div>';
    h += sevRow(it.severity, it.layer === 'chokepoints' ? 'wm_choke_score' : it.layer === 'instability' ? 'wm_instability' : 'wm_severity');
    var kv = [];
    if (it.layer === 'quakes') {
      kv.push([L('Magnitud', 'Magnitude'), 'M' + (it.mag != null ? (+it.mag).toFixed(1) : '?')]);
      kv.push([L('Profundidad', 'Depth'), it.depth_km != null ? it.depth_km + ' km' : '—']);
      kv.push([L('Alerta PAGER', 'PAGER alert'), it.alert ? String(it.alert).toUpperCase() : L('ninguna', 'none')]);
      kv.push(['Tsunami', it.tsunami ? L('aviso', 'flag') : L('no', 'no')]);
    } else if (it.layer === 'natural') {
      kv.push([L('Tipo', 'Type'), it.category_title || it.category || '—']);
      kv.push([L('Magnitud', 'Magnitude'), it.magnitude != null ? it.magnitude + ' ' + (it.magnitude_unit || '') : '—']);
    } else if (it.layer === 'shipping') {
      var ld = it.last_day || {};
      kv.push([L('Cambio 7 d vs 90 d', 'Change 7d vs 90d'), (it.change_pct > 0 ? '+' : '') + it.change_pct + ' %']);
      kv.push([L('Buques/día (7 d)', 'Ships/day (7d)'), it.transits_7d_avg + ' (' + L('antes ', 'was ') + it.transits_base_avg + ')']);
      kv.push([L('Último día', 'Last day'), (ld.date || '—') + ' · ' + (ld.total != null ? ld.total : '—')]);
      kv.push([L('Petroleros / contenedores', 'Tankers / containers'), (ld.tanker != null ? ld.tanker : '—') + ' / ' + (ld.container != null ? ld.container : '—')]);
    } else if (it.layer === 'policy') {
      kv.push([L('Organismo', 'Agency'), it.agency + ' · ' + L(it.kind_es, it.kind_en)]);
      kv.push([L('Tipo', 'Type'), it.doc_type || '—']);
      kv.push([L('Publicado', 'Published'), String(it.time || '').slice(0, 10)]);
      kv.push([L('Empresas del grafo nombradas', 'Graph companies named'), (it.companies || []).length]);
    } else if (it.layer === 'advisories') {
      kv.push([L('Nivel oficial', 'Official level'), it.level + ' / 4']);
      kv.push([L('Qué significa', 'What it means'), it.level >= 4 ? L('No viajar', 'Do not travel') : L('Reconsiderar el viaje', 'Reconsider travel')]);
      kv.push([L('Actualizado', 'Updated'), String(it.time || '').slice(0, 10) || '—']);
    } else if (it.layer === 'outages') {
      kv.push([L('Estado', 'Status'), it.ongoing ? L('en curso', 'ongoing') : L('terminado', 'ended')]);
      kv.push([L('Alcance', 'Scope'), it.scope || '—']);
      kv.push([L('Causa', 'Cause'), it.cause || '—']);
      if ((it.networks || []).length) kv.push([L('Redes', 'Networks'), it.networks.join(', ')]);
    } else if (it.layer === 'disasters') {
      kv.push([L('Alerta oficial', 'Official alert'), String(it.alert || '').toUpperCase()]);
      kv.push([L('Tipo', 'Type'), it.event_type || '—']);
      if (it.severity_text) kv.push([L('Medida', 'Measure'), it.severity_text]);
    } else if (it.press_signal) {
      kv.push([L('Artículos', 'Articles'), it.count != null ? it.count : '—']);
      kv.push([L('Eventos codificados', 'Coded events'), it.events != null ? it.events : '—']);
      kv.push([L('Fuentes (suma)', 'Sources (sum)'), it.sources_n != null ? it.sources_n : '—']);
      kv.push([L('Precisión', 'Precision'), it.precision === 'country' ? L('país (aprox.)', 'country (approx.)') : L('ciudad', 'city')]);
    } else if (LIVE.indexOf(it.layer) >= 0) {
      kv.push([L('Artículos', 'Articles'), it.count != null ? it.count : '—']);
      kv.push([L('Ventana', 'Window'), S.win]);
    } else if (it.layer === 'chokepoints' || it.layer === 'instability') {
      kv.push([L('Base curada', 'Curated base'), it.base != null ? it.base : '—']);
      if (it.live_shipping) kv.push([L('Buques/día en vivo (FMI)', 'Live ships/day (IMF)'), (it.live_shipping.transits_7d_avg != null ? it.live_shipping.transits_7d_avg : '—') +
        ' (' + (it.live_shipping.change_pct > 0 ? '+' : '') + it.live_shipping.change_pct + ' % ' + L('vs 90 d', 'vs 90d') + ')']);
      if (it.advisory_level) kv.push([L('Aviso oficial EE.UU.', 'Official US advisory'), L('nivel ', 'level ') + it.advisory_level + ' / 4']);
      if (it.live_events && it.live_events.count) kv.push([L('Eventos en vivo (24 h)', 'Live events (24h)'), it.live_events.count + ' · ' + (it.live_events.top || '')]);
      kv.push([L('Noticias 7d', 'News 7d'), it.news && it.news.count != null ? it.news.count + ' art.' + (it.news.tone != null ? ' · ' + L('tono', 'tone') + ' ' + it.news.tone : '') : L('sin datos aún', 'no data yet')]);
    }
    if (kv.length) h += '<div class="wm-kv">' + kv.map(function (x) { return '<div><div class="k">' + esc(x[0]) + '</div><div class="v">' + esc(x[1]) + '</div></div>'; }).join('') + '</div>';
    if (it.press_signal) h += '<div class="wm-meta" style="margin-top:8px;color:#9BA6C4">📰 ' + esc(L('Señal de prensa: GDELT codifica automáticamente miles de noticias cada 15 min. Solo mostramos eventos con ≥ 2 fuentes o ≥ 5 artículos; abre las notas para confirmar.', 'Press signal: GDELT automatically codes thousands of news stories every 15 min. We only show events with ≥ 2 sources or ≥ 5 articles; open the stories to confirm.')) + '</div>';
    if (it.layer === 'shipping' && it.data_caveat) h += '<div class="wm-meta" style="margin-top:8px;color:#FFB300">⚠ ' + esc(L('Cero buques registrados: puede ser un cierre real, buques con el transpondedor (AIS) apagado o un hueco en los datos del FMI. Confírmalo con noticias antes de decidir.', 'Zero ships recorded: it may be a real closure, ships with their (AIS) transponder off, or a gap in the IMF data. Confirm with news before deciding.')) + '</div>';
    if (it.layer === 'policy' && it.abstract) h += '<div class="wm-meta" style="margin-top:8px;color:#C7D0EA">' + esc(it.abstract) + '</div>';
    if (it.layer === 'policy' && (it.companies || []).length) h += '<div class="wm-meta" style="margin-top:6px">🏢 ' + esc(L('Nombra a: ', 'Names: ') + it.companies.map(function (c) { return c.label; }).join(', ')) + '</div>';
    if (it.layer === 'policy') h += '<div class="wm-meta" style="margin-top:6px;color:#7C87A3">' + esc(L('La importancia es una ESTIMACIÓN por palabras clave (Entity List, chips, IA…); lee el documento oficial antes de decidir.', 'Importance is a KEYWORD ESTIMATE (Entity List, chips, AI…); read the official document before deciding.')) + '</div>';
    if (it.factors && it.factors.length) h += '<div class="wm-meta" style="margin-top:8px;color:#FFD27A">⚡ ' + esc(L('Factores activos del grafo: ', 'Active graph factors: ') + it.factors.join(' · ')) + '</div>';
    var why = en() ? it.why_en : it.why_es;
    if (why) h += '<div class="wm-meta" style="margin-top:8px;color:#C7D0EA">' + esc(why) + '</div>';
    if (it.articles && it.articles.length) {
      h += '<div class="wm-sec"><div class="wm-sh">📰 ' + esc(L('Artículos', 'Articles')) + '</div>' + it.articles.map(function (a) {
        var u = safeUrl(a.url);
        return u ? '<a class="wm-link" href="' + esc(u) + '" target="_blank" rel="noopener noreferrer">↗ ' + esc(a.title || u) + '</a>' : '';
      }).join('') + '</div>';
    }
    var ou = safeUrl(it.url);
    h += '<div class="wm-meta" style="margin-top:8px">' + esc(L('Fuente: ', 'Source: ') + srcText(it)) +
      (ou && !(it.articles && it.articles.length) ? ' · <a class="wm-link" style="display:inline" href="' + esc(ou) + '" target="_blank" rel="noopener noreferrer">' + esc(L('ver original ↗', 'view original ↗')) + '</a>' : '') + '</div>';
    h += exposureHTML(it, S.expCache[it.id]);
    return h + '</div>';
  }
  function companyDetailHTML(n) {
    var g = window.GeoCoords ? window.GeoCoords.geoCoord(n) : { precision: 'unknown' };
    var nrs = nrsOf(n.id);
    var prec = { hq: L('sede / sitio principal (curado)', 'HQ / main site (curated)'), city: L('ciudad de la sede', 'HQ city'), hub: L('aprox. (hub regional)', 'approx. (regional hub)'),
      country: L('aprox. (centro del país)', 'approx. (country center)'), unknown: L('desconocida', 'unknown') }[g.precision] || '—';
    var h = detailHead('🏢 ' + L('EMPRESA DEL GRAFO', 'GRAPH COMPANY'), '#34d399');
    h += '<div class="wm-h1">' + esc(n.label) + (((window.MKT && window.MKT.pos) || {})[n.id] ? ' 💼' : '') + '</div>';
    h += '<div class="wm-meta">' + esc((n.mkt || n.ticker || '') + (n.cat ? ' · ' + n.cat : '')) + '<br>📍 ' + esc((g.label || '') + ' — ' + prec) + '</div>';
    h += '<div style="display:flex;align-items:center;gap:8px;margin-top:10px"><span class="wm-meta">NRS' + chip('nrs') + '</span><div class="wm-bar"><i style="width:' + Math.max(3, nrs || 0) + '%;background:' + nrsColor(nrs || 0) + '"></i></div><b style="font-family:JetBrains Mono,monospace;color:' + nrsColor(nrs || 0) + '">' + (nrs == null ? '—' : nrs) + '</b></div>';
    h += '<div style="display:flex;gap:6px;margin-top:10px"><button class="wm-act" style="margin:0" data-act="xray" data-id="' + esc(n.id) + '">🔬 X-Ray</button>' +
      '<button class="wm-act ghost" style="margin:0" data-act="map" data-id="' + esc(n.id) + '">🗺 ' + esc(L('Ver en el mapa', 'View on map')) + '</button></div>';
    h += nearbyEventsHTML(g, 800);
    return h + '</div>';
  }
  function nearbyEventsHTML(g, km) {
    var h = '<div class="wm-sec"><div class="wm-sh">⚡ ' + esc(L('Eventos a ≤ ' + km + ' km', 'Events within ' + km + ' km')) + '</div>';
    if (!(g.precision === 'hq' || g.precision === 'city' || g.precision === 'site')) {
      return h + '<div class="wm-meta">' + esc(L('Ubicación aproximada: no calculamos eventos cercanos para no dar falsas alarmas.', 'Approximate location: we do not compute nearby events to avoid false alarms.')) + '</div></div>';
    }
    var ev = (S.events ? S.events.items : []).filter(function (it) { return LIVE.indexOf(it.layer) >= 0 || it.layer === 'chokepoints'; })
      .map(function (it) { return { it: it, d: hav(g.lat, g.lng, it.lat, it.lon) }; })
      .filter(function (x) { return x.d <= km; }).sort(function (a, b) { return (b.it.severity || 0) - (a.it.severity || 0); }).slice(0, 8);
    if (!ev.length) return h + '<div class="wm-meta">' + esc(L('Nada activo cerca en esta ventana.', 'Nothing active nearby in this window.')) + '</div></div>';
    ev.forEach(function (x) {
      var l = LBY[x.it.layer];
      h += '<div class="wm-row" data-act="sel" data-id="' + esc(x.it.id) + '"><div class="wm-rel" style="background:' + sevColor(x.it.severity || 0) + '">' + (x.it.severity || 0) + '</div><div class="wm-rt"><div class="t">' + esc(title(x.it)) + '</div><div class="m"><span style="color:' + l.c + '">' + esc(L(l.es, l.en)) + '</span> · ' + Math.round(x.d) + ' km</div></div></div>';
    });
    return h + '</div>';
  }
  function fabDetailHTML(f) {
    var kind = { fab: L('Fab (fundición/lógica)', 'Fab (foundry/logic)'), hbm: L('Memoria HBM', 'HBM memory'), nand: 'NAND', euv: L('Litografía EUV', 'EUV lithography'), packaging: L('Empaquetado avanzado', 'Advanced packaging') }[f.kind] || f.kind;
    var h = detailHead('🏭 ' + L('FAB CRÍTICA · REFERENCIA', 'CRITICAL FAB · REFERENCE'), '#00E0FF');
    h += '<div class="wm-h1">' + esc(f.site) + '</div><div class="wm-meta">' + esc(kind + (f.c && !en() ? ' · ' + f.c : '')) + '<br>' + esc(L('Sitio curado a nivel ciudad (no en vivo).', 'Curated city-level site (not live).')) + chip('wm_reference') + '</div>';
    if (f.company_known) h += '<button class="wm-act" data-act="xray" data-id="' + esc(f.company) + '">🔬 X-Ray · ' + esc(((window.NODE_BY_ID || {})[f.company] || {}).label || f.company) + '</button>';
    h += nearbyEventsHTML({ lat: f.lat, lng: f.lon, precision: 'site' }, 800);
    return h + '</div>';
  }
  function renderDetail() {
    var el = $('wm-right'); if (!el || !S.sel) return;
    var s = S.sel;
    el.innerHTML = s.kind === 'company' ? companyDetailHTML(s.data) : s.kind === 'fab' ? fabDetailHTML(s.data) : eventDetailHTML(s.data);
    if (S.sim && S.sim.id === (s.data && s.data.id)) renderSim();
  }
  function renderRight() { if (S.sel) renderDetail(); else renderSituation(); }

  /* ── selección ──────────────────────────────────────────────────────── */
  function select(kind, data, opts) {
    opts = opts || {};
    if (!data) return;
    S.sel = { kind: kind, data: data }; S.moreCountry = false;
    if (S.sim && S.sim.id !== data.id) S.sim = null;
    var lat = kind === 'company' ? window.GeoCoords.geoCoord(data).lat : data.lat;
    var lon = kind === 'company' ? window.GeoCoords.geoCoord(data).lng : data.lon;
    if (S.globe) {
      S.globe.setPoints('sel', [{ lat: lat, lon: lon, color: '#00E0FF', size: 20, pulse: true }], { shape: 3, pickable: false, renderOrder: 9 });
      if (opts.focus !== false) S.globe.focusOn(lat, lon, { dist: opts.zoom ? Math.round((S.globe._fitDist || 290) * (S.narrow ? 0.8 : 0.72)) : undefined });
    }
    // siempre la exposición COMPLETA (limit 25 + dependientes curados): la del
    // brief es una vista previa (5 empresas) y no debe decidir qué se ve o simula
    if (kind === 'event' && !S.expCache[data.id]) loadExposure(data);
    S.collapsed.right = false; applyCollapse();
    if (S.narrow) openSheet('right');
    renderDetail();
  }
  function selectById(id, opts) {
    var it = S.items[id];
    if (!it) return;
    select('event', it, opts);
  }
  function back() {
    S.sel = null; S.sim = null;
    if (S.globe) S.globe._drop('sel');
    renderSituation();
  }
  function loadExposure(it) {
    var aff = (it.layer === 'chokepoints' || it.layer === 'shipping' || it.layer === 'policy') ? (it.affected || []).slice(0, 20) : [];
    var q = '/api/world/exposure?lat=' + encodeURIComponent(it.lat) + '&lon=' + encodeURIComponent(it.lon) +
      '&radius_km=' + itemRadius(it) + (it.country_key ? '&country=' + encodeURIComponent(it.country_key) : '') + '&limit=25' +
      (aff.length ? '&affected=' + encodeURIComponent(aff.join(',')) : '');
    getJSON(q).then(function (d) { S.expCache[it.id] = d; })
      .catch(function (e) { S.expCache[it.id] = { error: e.message || 'error' }; })
      .then(function () { if (S.sel && S.sel.data && S.sel.data.id === it.id) renderDetail(); });
  }
  function runSim() {
    var s = S.sel; if (!s || s.kind !== 'event') return;
    var it = s.data, shock = simShock(it, S.expCache[it.id]);
    if (!shock.length) return;
    var mag = it.layer === 'chokepoints' ? 1.0 : Math.max(0.2, Math.min(1, (it.severity || 0) / 100));
    S.sim = { id: it.id, loading: true, shock: shock };
    renderSim();
    getJSON('/api/matrix/impact', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shock: shock, magnitude: mag }) })
      .then(function (res) { if (S.sim && S.sim.id === it.id) { S.sim.loading = false; S.sim.res = res; S.sim.mag = mag; renderSim(); } })
      .catch(function (e) {
        if (!(S.sim && S.sim.id === it.id)) return;
        S.sim.loading = false;
        S.sim.err = e.status === 503 ? L('El motor de matrices necesita la base de datos (DATABASE_URL).', 'The matrix engine needs the database (DATABASE_URL).')
          : /ning[uú]n id/i.test(e.message || '') ? L('Estas empresas aún no están en la ontología de la base de datos (¿falta migrar el grafo?).', 'These companies are not in the ontology database yet (graph not migrated?).')
            : (e.message || 'error');
        renderSim();
      });
  }
  function renderSim() {
    var out = $('wm-simout'); if (!out || !S.sim) return;
    if (S.sim.loading) { out.innerHTML = '<div class="wm-load">' + esc(L('Propagando el shock por la cadena…', 'Propagating the shock through the chain…')) + '</div>'; return; }
    if (S.sim.err) { out.innerHTML = '<div class="wm-meta" style="color:#FF8FA3;margin-top:6px">' + esc(S.sim.err) + '</div>'; return; }
    var res = S.sim.res || {}, shocked = {};
    S.sim.shock.forEach(function (id) { shocked[id] = 1; });
    var NB = window.NODE_BY_ID || {};
    var victims = Object.keys(res.impacts || {}).filter(function (id) { return !shocked[id]; })
      .map(function (id) { return [id, res.impacts[id]]; }).sort(function (a, b) { return b[1] - a[1]; }).slice(0, 8);
    out.innerHTML = '<div class="wm-simres"><div class="wm-meta" style="color:#FF8FA3;font-weight:700;margin-bottom:5px">◉ ' + esc(L('Simulación', 'Simulation')) + ' · ' +
      (res.affected != null ? res.affected : victims.length) + ' ' + esc(L('empresas alcanzadas', 'companies reached')) + '</div>' +
      victims.map(function (v) {
        return '<div class="wm-vrow" style="cursor:pointer" data-act="xray" data-id="' + esc(v[0]) + '"><span class="n">' + esc((NB[v[0]] || {}).label || v[0]) + '</span><span class="vb"><i style="width:' + Math.min(100, v[1]) + '%"></i></span><span class="p">' + Math.round(v[1]) + '%</span></div>';
      }).join('') +
      '<div class="wm-note">' + esc(L('Motor de matrices sobre el grafo real (mismo kernel que la pestaña Simulación). Análisis, no asesoría ni predicción.', 'Matrix engine over the real graph (same kernel as the Simulation tab). Analysis, not advice or prediction.')) + '</div></div>';
  }

  /* ── dibujo en el globo ─────────────────────────────────────────────── */
  function fallbackChokes() {
    return FALLBACK_CHOKE.map(function (c) {
      return { id: 'chokepoints:' + c[0], layer: 'chokepoints', lat: c[3], lon: c[4], title: c[1], title_es: c[1], title_en: c[2], severity: null,
        source: 'reference (server unavailable: no score)', source_es: 'referencia (servidor no disponible: sin score)',
        source_en: 'reference (server unavailable: no score)', time_kind: 'current', affected: [] };
    });
  }
  // Índice id → ítem para ticker/KPIs/listas/brief. SIN depender del globo
  // (sin Three.js los paneles siguen abriendo el detalle).
  function indexItems() {
    var items = S.events ? S.events.items : [];
    S.items = {};
    items.forEach(function (it) { S.items[it.id] = it; });
    if (!items.some(function (it) { return it.layer === 'chokepoints'; })) fallbackChokes().forEach(function (it) { S.items[it.id] = it; });
    ((S.brief && S.brief.items) || []).forEach(function (it) { if (!S.items[it.id]) S.items[it.id] = it; });
  }
  function drawServerLayers() {
    var G = S.globe; if (!G) return;
    var items = S.events ? S.events.items : [];
    LIVE.forEach(function (id) {
      var l = LBY[id];
      var list = items.filter(function (it) { return it.layer === id; });
      G.setPoints(id, list.map(function (it) {
        var s = it.severity || 0;
        return { lat: it.lat, lon: it.lon, color: l.c, size: 3.6 + s / 100 * 9.5, pulse: s >= 60 };
      }), { hitPx: 11, renderOrder: 6 });
      G.gl[id].items = list;
      G.setLayerVisible(id, S.vis[id]);
    });
    var ck = items.filter(function (it) { return it.layer === 'chokepoints'; });
    if (!ck.length) ck = fallbackChokes().map(function (it) { return S.items[it.id] || it; });
    G.setRings('chokepoints', ck.map(function (it) {
      return { lat: it.lat, lon: it.lon, color: it.severity == null ? '#7C87A3' : sevColor(it.severity), scale: 0.8 + (it.severity || 30) / 100 * 0.7 };
    }));
    G.gl.chokepoints.items = ck;
    G.setLabels('choke_labels', ck.slice().sort(function (a, b) { return (b.severity || 0) - (a.severity || 0); }).slice(0, 5).map(function (it) {
      return { lat: it.lat + 2.2, lon: it.lon, text: title(it), color: it.severity == null ? '#9BA6C4' : sevColor(it.severity) };
    }), { px: 26, w: 22 });
    G.setLayerVisible('chokepoints', S.vis.chokepoints); G.setLayerVisible('choke_labels', S.vis.chokepoints);
    var ins = items.filter(function (it) { return it.layer === 'instability'; });
    G.setPoints('instability', ins.map(function (it) {
      var s = it.severity || 0;
      return { lat: it.lat, lon: it.lon, color: sevColor(s), size: 12 + s / 100 * 22, alt: 0.004 };
    }), { shape: 2, hitPx: 16, opacity: 0.55, renderOrder: 4 });
    G.gl.instability.items = ins;
    G.setLayerVisible('instability', S.vis.instability);
  }
  function drawRef() {
    var G = S.globe; if (!G || !S.ref) return;
    G.setPaths('lanes', S.ref.lanes.map(function (x) { return x.path; }), { color: 0x38BDF8, opacity: 0.34, speed: 0.4, dash: 1 / 30, alt: 0.0035 });
    G.setPaths('cables', S.ref.cables.map(function (x) { return x.path; }), { color: 0xA78BFA, opacity: 0.4, speed: 0.12, dash: 1 / 45, alt: 0.002, step: 1.5 });
    G.setPoints('landings', S.ref.landings.map(function (x) { return { lat: x.lat, lon: x.lon, color: '#A78BFA', size: 4.5 }; }), { shape: 3, pickable: false, opacity: 0.8 });
    var fabCol = { euv: '#8E5AFF', hbm: '#FFB300', nand: '#7AE2FF', packaging: '#5EEAD4' };
    G.setPoints('fabs', S.ref.fabs.map(function (f) { return { lat: f.lat, lon: f.lon, color: fabCol[f.kind] || '#00E0FF', size: 6.5, alt: 0.006 }; }),
      { shape: 1, hitPx: 9, additive: false, renderOrder: 7 });
    G.gl.fabs.items = S.ref.fabs;
    G.setLayerVisible('lanes', S.vis.lanes); G.setLayerVisible('cables', S.vis.cables); G.setLayerVisible('landings', S.vis.cables); G.setLayerVisible('fabs', S.vis.fabs);
  }
  function drawPortfolio() {
    var G = S.globe; if (!G || !window.GeoCoords) return;
    var NB = window.NODE_BY_ID || {};
    G.setPoints('portfolio', held().map(function (id) {
      var g = window.GeoCoords.geoCoord(NB[id]); return { lat: g.lat, lon: g.lng, color: '#FFFFFF', size: 8.5 };
    }), { shape: 3, pickable: false, opacity: 0.9, renderOrder: 8 });
    G.setLayerVisible('portfolio', S.vis.portfolio);
  }
  function applyVis() {
    var G = S.globe; if (!G) return;
    Object.keys(S.vis).forEach(function (id) { G.setLayerVisible(id, S.vis[id]); });
    G.setLayerVisible('choke_labels', S.vis.chokepoints);
    G.setLayerVisible('landings', S.vis.cables);
  }

  /* ── carga de datos ─────────────────────────────────────────────────── */
  function load(force) {
    if (S.loading && !force) return;
    S.loading = true; S.lastLoad = Date.now();
    renderTicker();
    var win = S.win;
    getJSON('/api/world/events?window=' + win).then(function (d) {
      if (win !== S.win) return;
      S.events = d; S.eventsErr = null;
    }).catch(function (e) {
      S.eventsErr = e.message || 'error';
      if (!S.events) S.events = null;
    }).then(function () {
      S.loading = false;
      indexItems(); drawServerLayers(); renderLayers(); renderTicker();
      if (!S.sel) renderSituation(); else renderDetail();
      var pending = S.events && SERVER_LAYERS.some(function (id) { var s = S.events.sources[id]; return s && s.pending; });
      if (pending && S.pendingPolls < 6) { S.pendingPolls++; later(function () { load(); }, 12000); } else if (!pending) S.pendingPolls = 0;
      loadBrief();
    });
    getJSON('/api/matrix/status').then(function (d) { if (d && d.available) S.systemic = d; }).catch(function () { S.systemic = null; })
      .then(function () { if (!S.sel) renderSituation(); });
    loadQuotes(force);
  }
  function loadBrief() {
    var win = S.win;
    getJSON('/api/world/brief?window=' + win + '&n=9').then(function (d) {
      if (win !== S.win) return;
      S.brief = d;
      // la exposición del brief es VISTA PREVIA: no se copia a expCache
      (d.items || []).forEach(function (it) { if (!S.items[it.id]) S.items[it.id] = it; });
    }).catch(function () { S.brief = null; }).then(function () { if (!S.sel) renderSituation(); });
  }
  function loadStatic() {
    if (S.ref) drawRef();            // re-montaje: el globo es nuevo, las capas de referencia no
    else {
      getJSON('/api/world/reference').then(function (d) { S.ref = d; S.refErr = null; drawRef(); })
        .catch(function (e) { S.refErr = e.message || 'error'; }).then(renderLayers);
    }
    if (S.globe && !S.globe.gl.borders) {
      fetch(base() + '/vendor/world-110m.json').then(function (r) { if (!r.ok) throw new Error('topo'); return r.json(); })
        .then(function (tp) { if (S.globe) S.globe.setBorders(tp, { color: 0x3b82c4, opacity: 0.5 }); }).catch(function () {});
    }
  }
  function later(fn, ms) { var t = setTimeout(fn, ms); S.timers.push(t); return t; }

  /* ── colapsar / hojas móviles ───────────────────────────────────────── */
  function applyCollapse() {
    var l = $('wm-left'), r = $('wm-right'), rl = $('wm-reopen-l'), rr = $('wm-reopen-r');
    if (!l || !r) return;
    if (S.narrow) { l.classList.remove('hid'); r.classList.remove('hid'); return; }
    l.classList.toggle('hid', S.collapsed.left); r.classList.toggle('hid', S.collapsed.right);
    if (rl) rl.style.display = S.collapsed.left ? '' : 'none';
    if (rr) rr.style.display = S.collapsed.right ? '' : 'none';
  }
  function openSheet(side) {
    S.sheet = side;
    var l = $('wm-left'), r = $('wm-right');
    if (l) l.classList.toggle('open', side === 'left');
    if (r) r.classList.toggle('open', side === 'right');
    // con la hoja abierta el globo sube (si no, lo seleccionado queda tapado)
    if (S.globe && S.globe.setViewShift) S.globe.setViewShift(S.narrow && side ? 0.3 : 0);
  }
  function checkNarrow() {
    var w = S.root ? S.root.clientWidth : 0;
    if (!w) return;
    var nr = w < 760;
    if (nr !== S.narrow) {
      S.narrow = nr;
      var wm = $('wm'); if (wm) wm.classList.toggle('nr', nr);
      if (!nr) openSheet(null);
      applyCollapse();
    }
  }

  /* ── eventos de UI (delegación) ─────────────────────────────────────── */
  function onClick(e) {
    var a = e.target.closest('[data-act]');
    if (!a || !S.root || !S.root.contains(a)) return;
    var act = a.getAttribute('data-act');
    if (act === 'toggle') {
      var id = a.getAttribute('data-layer');
      S.vis[id] = !S.vis[id]; lsSet('kh_wm_layers', S.vis);
      applyVis(); renderLayers(); renderTicker();
    } else if (act === 'win') {
      var w = a.getAttribute('data-win');
      if (w !== S.win) { S.win = w; lsSet('kh_wm_window', w); S.brief = null; S.expCache = {}; renderBottom(); back(); load(true); }
    } else if (act === 'sel') {
      selectById(a.getAttribute('data-id'), { zoom: true });
    } else if (act === 'back') { back(); }
    else if (act === 'xray') {
      var xid = a.getAttribute('data-id');
      if (typeof window._surface === 'function' && window._surface('xray', xid)) return;
      if (window.openXRay) window.openXRay(xid);
    } else if (act === 'map') {
      var mid = a.getAttribute('data-id');
      if (typeof window._surface === 'function') window._surface('graph', mid);
      else if (window.goMap) window.goMap(mid);
    } else if (act === 'sim') { runSim(); }
    else if (act === 'more') { S.moreCountry = true; renderDetail(); }
    else if (act === 'list') { var ly = a.getAttribute('data-layer'); S.lists[ly] = !S.lists[ly]; lsSet('kh_wm_lists', S.lists); renderSituation(); }
    else if (act === 'focus') { if (S.globe) S.globe.focusOn(+a.getAttribute('data-lat'), +a.getAttribute('data-lon'), { dist: Math.round((S.globe._fitDist || 290) * 0.85) }); }
    else if (act === 'top') {
      var lay = a.getAttribute('data-layer');
      var its = (S.events ? S.events.items : []).filter(function (i) { return i.layer === lay; });
      if (its.length) { if (!S.vis[lay]) { S.vis[lay] = true; applyVis(); renderLayers(); } select('event', its[0], { zoom: true }); }
    } else if (act === 'scen') {
      try { window.nexusCore.runPreset(a.getAttribute('data-preset')); } catch (err) {}
      if (typeof window.toast === 'function') window.toast(L('Simulación de escenario en marcha (what-if).', 'Scenario simulation running (what-if).'));
    } else if (act === 'collapse') {
      var side = a.getAttribute('data-side');
      if (S.narrow) openSheet(null); else { S.collapsed[side] = true; applyCollapse(); }
    } else if (act === 'reopen') { S.collapsed[a.getAttribute('data-side')] = false; applyCollapse(); }
    else if (act === 'sheet') { var sd = a.getAttribute('data-side'); openSheet(S.sheet === sd ? null : sd); }
    else if (act === 'zoom') { if (S.globe) S.globe.zoomBy(+a.getAttribute('data-f')); }
    else if (act === 'reset') { if (S.globe) S.globe.resetView(); }
    else if (act === 'reload') { load(true); }
  }

  function onGlobePick(hit) {
    if (!hit || !hit.data) return;
    if (hit.layer === 'companies') return select('company', hit.data, { focus: false });
    if (hit.layer === 'fabs') return select('fab', hit.data, { focus: false });
    select('event', hit.data, { focus: false });
  }
  function onGlobeHover(hit, x, y) {
    var tip = $('wm-tip'); if (!tip || !S.root) return;
    if (!hit || !hit.data) { tip.style.display = 'none'; return; }
    var d = hit.data, h;
    if (hit.layer === 'companies') {
      var nrs = nrsOf(d.id);
      h = '<b>🏢 ' + esc(d.label) + '</b><div class="m">NRS <b style="color:' + nrsColor(nrs || 0) + '">' + (nrs == null ? '—' : nrs) + '</b> · ' + esc(L('clic = detalle', 'click = details')) + '</div>';
    } else if (hit.layer === 'fabs') {
      h = '<b>🏭 ' + esc(d.site) + '</b><div class="m">' + esc((d.c && !en() ? d.c + ' · ' : '') + L('referencia', 'reference')) + '</div>';
    } else {
      var l = LBY[d.layer] || LBY.conflict;
      h = '<b>' + esc((d.layer === 'natural' ? (NAT_ICON[d.category] || l.i) : l.i) + ' ' + String(title(d)).slice(0, 90)) + '</b><div class="m"><span style="color:' + l.c + '">' + esc(L(l.es, l.en)) + '</span>' +
        (d.severity != null ? ' · ' + esc(L('sev.', 'sev.')) + ' ' + d.severity : '') + (d.stale ? ' · <span style="color:#FFB300">' + esc(staleTag(d)) + '</span>' : d.time_kind === 'exact' || d.time_kind === 'last_update' ? ' · ' + esc(ago(d.ts)) : '') + '</div>';
    }
    var r = S.root.getBoundingClientRect();
    tip.innerHTML = h; tip.style.display = 'block';
    var tx = Math.min(x - r.left + 14, r.width - 270), ty = Math.min(y - r.top + 12, r.height - 70);
    tip.style.left = Math.max(6, tx) + 'px'; tip.style.top = Math.max(44, ty) + 'px';
  }

  /* ── montaje ────────────────────────────────────────────────────────── */
  function initGlobe() {
    if (!window.THREE || !window.KhipuGlobe || !window.GeoCoords) {
      var w = $('wm');
      if (w) w.insertAdjacentHTML('beforeend', '<div class="wm-empty">' + esc(L('El globo 3D necesita Three.js (revisa tu conexión). Los paneles siguen funcionando.', 'The 3D globe needs Three.js (check your connection). The panels still work.')) + '</div>');
      return;
    }
    try {
      var G = new window.KhipuGlobe('wm-canvas', { layers: ['companies'], look: 'monitor' });
      G.init();
      G.setGraticule(30, { opacity: 0.12 });
      G.loadCompanies({ monitor: true });
      G.onPick = onGlobePick;
      G.onHover = onGlobeHover;
      S.globe = G;
      drawPortfolio();
      applyVis();
      window._wmGlobe = G;
    } catch (e) { console.warn('[WorldMonitor] globo:', e); }
  }

  function mount(container) {
    container = container || $('wm-root');
    if (!container) return;
    ensureStyles(); registerExplain();
    // La Cabina adopta #geo-panel y le deja min-height:100%; al volver a la
    // pestaña eso lo estira más que la pantalla (el globo quedaba cortado).
    var pane = $('geo-panel');
    if (pane && !(pane.closest && pane.closest('.bcp-embed'))) pane.style.minHeight = '';
    if (S.root && S.root === container && $('wm')) {
      // ya montado: re-etiquetar (idioma/tema), redimensionar y refrescar si toca
      renderLayers(); renderBottom(); renderTicker(); renderRight(); checkNarrow();
      var tp = $('wm-tip'); if (tp) tp.style.display = 'none';
      if (S.globe) { S.globe.resume(); if (S.globe.recolorCompanies) S.globe.recolorCompanies(); drawPortfolio(); drawServerLayers(); }
      if (Date.now() - S.lastLoad > 180000) load();
      return;
    }
    if (S.root) unmount();
    S.root = container;
    S.vis = Object.assign({}, S.vis, lsGet('kh_wm_layers', {}));
    var w = lsGet('kh_wm_window', '24h'); S.win = (w === '7d') ? '7d' : '24h';
    var ls = lsGet('kh_wm_lists', {}); S.lists = ls && typeof ls === 'object' ? ls : {};
    container.innerHTML = shell();
    renderLayers(); renderBottom(); renderTicker(); renderSituation(); tickClock();
    container.addEventListener('click', onClick);
    S._onClick = onClick;
    if (window.ResizeObserver) { S._ro = new ResizeObserver(checkNarrow); S._ro.observe(container); }
    checkNarrow();
    initGlobe();
    loadStatic();
    load(true);
    S.timers.push(setInterval(tickClock, 30000));
    S.timers.push(setInterval(function () {
      if (document.hidden || !S.root || !S.root.offsetParent) return;
      load();
    }, 180000));
  }

  function unmount() {
    S.timers.forEach(function (t) { clearTimeout(t); clearInterval(t); });
    S.timers = [];
    try { if (S._ro) S._ro.disconnect(); } catch (e) {}
    if (S.root && S._onClick) S.root.removeEventListener('click', S._onClick);
    if (S.globe) { try { S.globe.dispose(); } catch (e) {} }
    S.globe = null; window._wmGlobe = null;
    if (S.root) S.root.innerHTML = '';
    S.root = null; S.sel = null; S.sim = null; S.narrow = false; S.sheet = null;
  }

  function open() {
    if (typeof window._surface === 'function') window._surface('tab', 'geo');
    else if (typeof window.switchTab === 'function') window.switchTab('geo');
    setTimeout(function () { mount(); }, 60);
  }

  function focus(lat, lon) {
    open();
    var tries = 0;
    (function go() {
      if (S.globe) { S.globe.focusOn(+lat, +lon, { dist: Math.round((S.globe._fitDist || 290) * 0.78) }); return; }
      if (++tries < 20) setTimeout(go, 150);
    })();
  }

  window.KhipuWorld = { mount: mount, open: open, focus: focus, unmount: unmount, state: S, select: selectById };
})();
