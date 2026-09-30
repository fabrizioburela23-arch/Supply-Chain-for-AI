/* engine/spacemonitor.js — SPACE MONITOR (pestaña 🚀 Espacio).

   Pedido de Fabrizio (2026-09-30): "haz lo mismo que el World Monitor para
   Espacio; los lanzamientos que sean DINÁMICOS, no una lista".
   → UNA sola vista inmersiva: globo 3D (engine/globe.js, look 'monitor') con
     · plataformas de lanzamiento REALES (coordenadas de Launch Library 2) que
       brillan; las de lanzamiento inminente laten,
     · los próximos lanzamientos como ARCOS DE ASCENSO animados desde su
       plataforma hacia la órbita (trayectoria ESQUEMÁTICA, dicho en su "?"),
       el próximo resaltado en oro con su plano orbital,
     · lanzamientos recientes (30 d) con éxito/fallo,
     · satélites reales por constelación (CelesTrak, SGP4 en vivo) con
       telemetría al hacer clic,
     · empresas espaciales de TU grafo (color = NRS).
   HUD: cuenta regresiva en vivo (T-02:14:33) + ticker de próximos, capas con
   estado por fuente (vivo / en caché / caída / referencia), panel "Situación
   espacial" (próximo lanzamiento, conteos por semana/mes y proveedor, órbita,
   empresas del grafo con capitalización en vivo, exposición del grafo) y una
   LÍNEA DE TIEMPO horizontal que se puede arrastrar (scrub) o pulsar: enfoca la
   plataforma en el globo y abre la ficha (cohete, proveedor, misión, órbita,
   ventana, estado, webcast, empresas del grafo con NRS + X-Ray).
   En móvil los paneles son hojas inferiores. Degrada con gracia: sin servidor
   o sin Launch Library el globo y los satélites siguen y el estado dice qué cayó.

   API: window.KhipuSpace = { mount(container), unmount(), focusLaunch(id), open() }
   Datos: /api/space2/launches · /api/space2/summary (core/space.py) · /api/space/tle.
   Todo bilingüe (window.LANG). Cada métrica con su "?" (engine/explain.js). */
(function () {
  'use strict';

  var S = {
    root: null, globe: null, up: null, prev: null, upSrc: null, prevSrc: null, upErr: null, prevErr: null,
    summary: null, sumErr: null, tle: null, tleErr: null, sel: null, timers: [], narrow: false, sheet: null,
    collapsed: { left: false, right: false }, lastLoad: 0, loading: false, tlMode: 'upcoming', provWin: 'week',
    vis: { upcoming: true, recent: true, pads: true, orbit: true, companies: true, shells: false },
    satVis: {}, byId: {}, nextId: null, moreCos: false, pendingFocus: null, scrub: null,
  };

  var ALT_KNEE = 2000;     // km: por encima, la altitud se comprime ×0.22 (explicado en "?")
  function altScale(km) { km = +km || 0; return km <= ALT_KNEE ? km : ALT_KNEE + (km - ALT_KNEE) * 0.22; }
  var EARTH_KM = 6371;

  var LAYERS = [
    { id: 'upcoming', g: 'launch', c: '#FFD166', i: '🚀', es: 'Próximos (arcos de ascenso)', en: 'Upcoming (ascent arcs)' },
    { id: 'recent', g: 'launch', c: '#2BE38B', i: '✓', es: 'Recientes · 30 días', en: 'Recent · 30 days' },
    { id: 'pads', g: 'launch', c: '#00E0FF', i: '⬢', es: 'Plataformas de lanzamiento', en: 'Launch pads' },
    { id: 'orbit', g: 'launch', c: '#FFD166', i: '◯', es: 'Plano orbital del seleccionado', en: 'Selected orbital plane' },
    { id: 'companies', g: 'graph', c: '#34d399', i: '🏢', es: 'Empresas espaciales (color = NRS)', en: 'Space companies (color = NRS)' },
    { id: 'shells', g: 'ref', c: '#7C87A3', i: '◎', es: 'Capas orbitales LEO/MEO/GEO', en: 'Orbital shells LEO/MEO/GEO' },
  ];
  var LBY = {}; LAYERS.forEach(function (l) { LBY[l.id] = l; });
  var ST_C = { go: '#2BE38B', tbc: '#FFB300', tbd: '#7AA7FF', hold: '#FF4D6A', inflight: '#00E0FF',
    success: '#2BE38B', failure: '#FF4D6A', partial: '#FFB300', other: '#9BA6C4' };
  var ST_L = {
    go: ['Confirmado (Go)', 'Go for launch'], tbc: ['Por confirmar (TBC)', 'To be confirmed (TBC)'],
    tbd: ['Fecha no confirmada (TBD)', 'Date not confirmed (TBD)'], hold: ['En espera (Hold)', 'On hold'],
    inflight: ['En vuelo', 'In flight'], success: ['Éxito', 'Success'], failure: ['Fallo', 'Failure'],
    partial: ['Fallo parcial', 'Partial failure'], other: ['Otro', 'Other'] };
  var PREC = { Second: ['segundo', 'second'], Minute: ['minuto', 'minute'], Hour: ['hora', 'hour'],
    Morning: ['mañana', 'morning'], Afternoon: ['tarde', 'afternoon'], Day: ['día', 'day'], Week: ['semana', 'week'],
    Month: ['mes', 'month'], Year: ['año', 'year'] };
  var ROLE = { provider: ['Proveedor del lanzamiento', 'Launch provider'], customer: ['Cliente / agencia de la misión', 'Mission customer / agency'],
    payload: ['Dueño de la carga (por nombre de misión)', 'Payload owner (by mission name)'], manufacturer: ['Fabricante del cohete', 'Rocket manufacturer'] };
  var PALETTE = ['#7AA7FF', '#FF8A3D', '#B983FF', '#2BD9C7', '#FF6B8B', '#FFD23F', '#5EEAD4', '#A3E635', '#F472B6', '#60A5FA'];

  /* ── utilidades ─────────────────────────────────────────────────────── */
  function en() { try { return (window.LANG || localStorage.getItem('eco_lang') || 'es') === 'en'; } catch (e) { return false; } }
  function L(es, e) { return en() ? e : es; }
  function LL(pair) { return pair ? (en() ? pair[1] : pair[0]) : ''; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function chip(k) { return window.explainChip ? window.explainChip(k) : ''; }
  function base() { return (typeof window.BASE !== 'undefined' && window.BASE) || ''; }
  function lsGet(k, d) { try { var v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } }
  function lsSet(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  function nrsColor(n) { return n > 60 ? '#f87171' : n >= 35 ? '#f59e0b' : '#34d399'; }
  function nrsOf(id, fb) { try { if (typeof window.computeNRS === 'function' && window.NODE_BY_ID && window.NODE_BY_ID[id]) return window.computeNRS(id); } catch (e) {} return fb == null ? null : fb; }
  function safeUrl(u) { return typeof u === 'string' && /^https?:\/\//i.test(u.trim()) ? u.trim() : null; }
  function $(id) { return document.getElementById(id); }
  function errText(s) { return (s && (en() ? s.error_en : s.error_es)) || (s && s.error) || '?'; }
  function fmtIso(iso) { return iso ? String(iso).replace('T', ' ').slice(0, 16) + ' UTC' : '?'; }
  function hashC(s) { var h = 0; s = String(s || ''); for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return PALETTE[Math.abs(h) % PALETTE.length]; }
  function getJSON(url, opts) {
    return fetch(base() + url, opts || {}).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!r.ok) { var e = new Error((j && (en() ? j.error_en : j.error_es)) || (j && j.error) || ('HTTP ' + r.status)); e.status = r.status; throw e; }
        return j;
      });
    });
  }
  function fmtDate(ts, withTime) {
    if (!ts) return '?';
    try {
      var o = { day: 'numeric', month: 'short', timeZone: 'UTC' };
      if (withTime) { o.hour = '2-digit'; o.minute = '2-digit'; o.hour12 = false; }
      return new Date(ts * 1000).toLocaleString(en() ? 'en-US' : 'es-ES', o) + (withTime ? ' UTC' : '');
    } catch (e) { return fmtIso(new Date(ts * 1000).toISOString()); }
  }
  function pad2(n) { return (n < 10 ? '0' : '') + n; }
  // Cuenta regresiva honesta: segundos solo si LL2 da precisión de segundo/minuto;
  // si la fecha es aproximada (hora/día/mes…) se dice "NET <fecha> · ±<precisión>".
  function countdown(l, now) {
    if (!l || !l.net_ts) return { t: L('fecha por definir', 'date TBD'), exact: false };
    now = now || Date.now() / 1000;
    var d = l.net_ts - now, p = l.net_precision, k = l.status && l.status.kind;
    var coarse = p && !/^(Second|Minute|Hour)$/.test(p);
    if (coarse) {
      var pk = Object.keys(PREC).filter(function (x) { return p.indexOf(x) === 0; })[0];
      return { t: 'NET ' + fmtDate(l.net_ts) + ' · ±' + (pk ? LL(PREC[pk]) : p), exact: false };
    }
    var sign = d >= 0 ? 'T-' : 'T+', a = Math.abs(d);
    var dd = Math.floor(a / 86400), hh = Math.floor(a % 86400 / 3600), mm = Math.floor(a % 3600 / 60), ss = Math.floor(a % 60);
    var t = p === 'Hour' ? sign + (dd ? dd + 'd ' : '') + pad2(hh) + 'h ' + pad2(mm) + 'm'
      : sign + (dd ? dd + 'd ' : '') + pad2(hh) + ':' + pad2(mm) + ':' + pad2(ss);
    return { t: (k === 'tbd' || k === 'tbc' || p === 'Hour' ? '≈ ' : '') + t, exact: p !== 'Hour' && k !== 'tbd' };
  }
  function isSpaceNode(n) {
    if (!n) return false;
    var sec = typeof window.sectorOf === 'function' ? window.sectorOf(n.cat) : n.sector;
    return sec === 'espacio' || n.cat === 'space_launch' || n.cat === 'satellite' || n.cat === 'earth_obs';
  }
  function spaceNodes() { return (window.NODES || []).filter(isSpaceNode); }
  function provName(l) { return (l.provider && l.provider.name) || '?'; }
  function provShort(l) { var p = l.provider || {}; return p.abbrev && p.abbrev.length <= 8 ? p.abbrev : (p.name || '?'); }
  function rocketName(l) { return (l.rocket && (l.rocket.name || l.rocket.full_name)) || '?'; }
  function missionName(l) { return (l.mission && l.mission.name) || (String(l.name || '').split('|').slice(-1)[0] || '').trim() || '?'; }
  function orbitAbbr(l) { var o = l.mission && l.mission.orbit; return o ? (o.abbrev || o.name || '') : ''; }
  function padLoc(l) { var p = l.pad || {}; return String(p.location || p.name || '').split(',')[0]; }
  function hasLL(l) { return l && l.pad && l.pad.lat != null && l.pad.lon != null; }
  function stTag(l) {
    var k = (l.status && l.status.kind) || 'other', c = ST_C[k] || ST_C.other;
    return '<span class="sm-tag" style="color:' + c + ';border-color:' + c + '66;background:' + c + '14">' + esc(LL(ST_L[k] || ST_L.other)) + '</span>';
  }
  function xray(id) {
    if (typeof window._surface === 'function' && window._surface('xray', id)) return;
    if (window.openXRay) return window.openXRay(id);
    goMap(id);
  }
  function goMap(id) {
    if (typeof window._surface === 'function' && window._surface('graph', id)) return;
    if (typeof window.switchTab === 'function') window.switchTab('map');
    setTimeout(function () { if (window.jumpTo) window.jumpTo(id); }, 90);
  }
  function mcap(id) {
    var m = (window.NODE_META || {})[id] || {};
    return m.mktcap_b != null && isFinite(+m.mktcap_b) ? { v: +m.mktcap_b, live: !!m.mktcap_live, as_of: m.mktcap_live && m.mktcap_live.as_of } : null;
  }
  function fmtCap(b) { return b >= 1000 ? '$' + (b / 1000).toFixed(2) + 'T' : b >= 10 ? '$' + Math.round(b) + 'B' : '$' + b.toFixed(1) + 'B'; }
  function dayChg(n) {
    var q = n && n.mkt && window.MKT && window.MKT.quotes && window.MKT.quotes[n.mkt];
    if (!q) return null;
    var px = q.live != null ? q.live : q.close;
    return px != null && q.prev ? (px - q.prev) / q.prev * 100 : null;
  }

  /* ── geometría de ascenso (ESQUEMÁTICA: rumbo por tipo de órbita) ────── */
  function orbitClass(l) {
    var a = String(orbitAbbr(l) || '').toUpperCase(), n = String((l.mission && l.mission.orbit && l.mission.orbit.name) || '').toLowerCase();
    if (/SSO|PO\b|POLAR/.test(a) || /sun-sync|polar/.test(n)) return 'sso';
    if (/ISS|CSS/.test(a)) return 'iss';
    if (/GTO|GEO|GSO|SSGTO/.test(a) || /geo/.test(n)) return 'geo';
    if (/MEO|NAV/.test(a) || /medium/.test(n)) return 'meo';
    if (/LO$|TLI|HEO|HELIO|L1|L2|MARS|LUNAR|ESCAPE|ELLIPT/.test(a) || /lunar|helio|mars|escape|lagrange/.test(n)) return 'deep';
    if (/SUB/.test(a) || /suborb/.test(n)) return 'sub';
    return 'leo';
  }
  var OC = { leo: { inc: 53, alt: 0.09, dr: 22 }, iss: { inc: 51.6, alt: 0.07, dr: 22 }, sso: { inc: 97.5, alt: 0.1, dr: 26 },
    meo: { inc: 55, alt: 0.3, dr: 36 }, geo: { inc: 0, alt: 0.36, dr: 42 }, deep: { inc: 0, alt: 0.55, dr: 64 }, sub: { inc: 0, alt: 0.035, dr: 4 } };
  function heading(l) {
    var oc = orbitClass(l), lat = l.pad.lat, cfg = OC[oc];
    if (oc === 'sub') return 90;
    var inc = Math.max(Math.abs(lat) + 0.3, cfg.inc || 0);
    var s = Math.cos(inc * Math.PI / 180) / Math.cos(lat * Math.PI / 180);
    s = Math.max(-1, Math.min(1, s));
    var az = Math.asin(s) * 180 / Math.PI;       // rama ascendente (hacia el norte/este)
    if (oc === 'sso') return lat > 45 ? (360 + az) % 360 : 180 - az;   // polares: al sur desde latitudes medias
    if (lat < 0) return 180 - az;                                      // hemisferio sur: rama sur-este
    return az;
  }

  /* ── explicaciones "?" ─────────────────────────────────────────────── */
  var _xpl = false;
  function registerExplain() {
    if (_xpl || !window.explainRegister) return;
    _xpl = true;
    var R = window.explainRegister;
    R('sm_countdown', {
      es: { t: '¿Qué es la cuenta regresiva (T-)?', b: '<b>T-</b> es el tiempo que falta para el lanzamiento según la fecha <b>NET</b> ("no antes de") que publica Launch Library 2. <b>T+</b> es el tiempo desde esa hora.<ul style="margin:8px 0;padding-left:18px;line-height:1.7"><li>Solo mostramos segundos si la fuente da la hora con precisión de minuto o segundo.</li><li>Si la fecha es aproximada (día, mes…) mostramos <b>NET fecha · ±precisión</b>, sin inventar una hora.</li><li><b>≈</b> = la fecha aún no está confirmada (TBD/TBC).</li></ul>Los lanzamientos se retrasan a menudo por clima o problemas técnicos.' },
      en: { t: 'What is the countdown (T-)?', b: '<b>T-</b> is the time left until launch based on the <b>NET</b> ("no earlier than") date published by Launch Library 2. <b>T+</b> is the time since then.<ul style="margin:8px 0;padding-left:18px;line-height:1.7"><li>We only show seconds when the source gives the time to the minute or second.</li><li>If the date is approximate (day, month…) we show <b>NET date · ±precision</b>, without making up a time.</li><li><b>≈</b> = the date is not confirmed yet (TBD/TBC).</li></ul>Launches often slip because of weather or technical issues.' } });
    R('sm_arcs', {
      es: { t: '¿Qué son los arcos de ascenso?', b: 'Cada arco sale de las <b>coordenadas reales de la plataforma</b> (Launch Library 2) y sube hacia la órbita de la misión. La <b>trayectoria es esquemática</b>: el rumbo se estima por el tipo de órbita (p.ej. polar/SSO hacia el sur, órbita geoestacionaria hacia el este) y la latitud de la plataforma. No es la trayectoria real del cohete.<br><br>El arco dorado es el <b>próximo</b> (o el que seleccionaste) y el círculo dorado su <b>plano orbital</b> aproximado. Si la fuente no da coordenadas de la plataforma, el lanzamiento no se dibuja en el globo (sí aparece en la línea de tiempo).' },
      en: { t: 'What are the ascent arcs?', b: 'Each arc starts at the <b>real pad coordinates</b> (Launch Library 2) and climbs toward the mission orbit. The <b>trajectory is schematic</b>: the heading is estimated from the orbit type (e.g. polar/SSO to the south, geostationary to the east) and the pad latitude. It is not the rocket\'s real trajectory.<br><br>The golden arc is the <b>next</b> launch (or the one you selected) and the golden circle its approximate <b>orbital plane</b>. If the source gives no pad coordinates, the launch is not drawn on the globe (it still shows on the timeline).' } });
    R('sm_graph_match', {
      es: { t: '¿Cómo se vinculan los lanzamientos con tu grafo?', b: 'El servidor busca en tu grafo (el mismo resolvedor de nombres que usa toda la app):<ul style="margin:8px 0;padding-left:18px;line-height:1.7"><li><b>Proveedor</b> del lanzamiento (p.ej. SpaceX, Rocket Lab).</li><li><b>Clientes / agencias</b> de la misión que publica la fuente.</li><li><b>Dueño de la carga por nombre de misión</b>: una lista corta y curada (Starlink → SpaceX, Kuiper → Amazon, OneWeb → Eutelsat, BlueBird → AST SpaceMobile…).</li><li><b>Fabricante</b> del cohete, si es distinto.</li></ul>Agencias públicas (NASA, ESA, CASC…) no son empresas del grafo y no aparecen. El NRS es el riesgo de red de cada empresa (0 = seguro, 100 = frágil).' },
      en: { t: 'How are launches linked to your graph?', b: 'The server searches your graph (the same name resolver used across the app):<ul style="margin:8px 0;padding-left:18px;line-height:1.7"><li>The launch <b>provider</b> (e.g. SpaceX, Rocket Lab).</li><li>Mission <b>customers / agencies</b> published by the source.</li><li><b>Payload owner by mission name</b>: a short curated list (Starlink → SpaceX, Kuiper → Amazon, OneWeb → Eutelsat, BlueBird → AST SpaceMobile…).</li><li>The rocket <b>manufacturer</b>, if different.</li></ul>Public agencies (NASA, ESA, CASC…) are not graph companies and do not appear. NRS is each company\'s network risk (0 = safe, 100 = fragile).' } });
    R('sm_altitude', {
      es: { t: '¿Por qué la altitud está comprimida?', b: 'Los satélites de <b>órbita baja (LEO, hasta 2.000 km)</b> — Starlink, OneWeb, Planet, la ISS — se dibujan a <b>escala real</b> sobre la Tierra. Los de <b>órbita media y alta</b> (GPS ~20.200 km, geoestacionarios ~35.786 km) se acercan: por encima de 2.000 km la altitud se <b>comprime ×0,22</b> para que quepan en pantalla. Las posiciones (latitud/longitud) sí son reales, calculadas con SGP4 a partir de los datos de CelesTrak.' },
      en: { t: 'Why is altitude compressed?', b: '<b>Low Earth orbit (LEO, up to 2,000 km)</b> satellites — Starlink, OneWeb, Planet, the ISS — are drawn at <b>true scale</b> above the Earth. <b>Medium and high orbit</b> ones (GPS ~20,200 km, geostationary ~35,786 km) are pulled in: above 2,000 km the altitude is <b>compressed ×0.22</b> so they fit on screen. Positions (latitude/longitude) are real, computed with SGP4 from CelesTrak data.' } });
    R('sm_exposure', {
      es: { t: '¿Qué es la exposición del grafo al espacio?', b: 'Cuántas empresas de tu grafo <b>fuera del sector espacial</b> tienen relaciones de suministro con empresas espaciales (proveen a, o reciben de), según los enlaces del grafo. El peso <b>w</b> de cada relación mide su importancia. Sirve para ver quién sufriría si, por ejemplo, un fallo de lanzamiento retrasa una constelación. Es <b>estructura del grafo</b>, no un pronóstico.' },
      en: { t: 'What is the graph\'s space exposure?', b: 'How many companies in your graph <b>outside the space sector</b> have supply relationships with space companies (supply to, or buy from), according to the graph links. Each link\'s weight <b>w</b> measures its importance. It shows who would be hit if, say, a launch failure delays a constellation. It is <b>graph structure</b>, not a forecast.' } });
    R('sm_ll2', {
      es: { t: '¿De dónde salen los lanzamientos?', b: 'De <b>Launch Library 2</b> (The Space Devs), una base pública y gratuita de lanzamientos de todo el mundo. Su plan gratuito permite pocas consultas por hora, así que el servidor guarda los datos 15 min (próximos) y 30 min (recientes). Si la fuente no responde o nos limita, se muestran los últimos datos buenos con su hora (<b>en caché</b>), nunca datos inventados.<br><br>Los <b>conteos por semana/mes</b> se calculan sobre los lanzamientos descargados (hasta 60 próximos y 40 recientes); si no alcanzan a cubrir el periodo se marca con <b>≥</b>.' },
      en: { t: 'Where do launches come from?', b: 'From <b>Launch Library 2</b> (The Space Devs), a free public database of launches worldwide. Its free plan allows few requests per hour, so the server keeps data for 15 min (upcoming) and 30 min (recent). If the source is down or rate-limits us, the last good data is shown with its time (<b>cached</b>), never made-up data.<br><br><b>Weekly/monthly counts</b> are computed over the downloaded launches (up to 60 upcoming and 40 recent); if they do not cover the whole period it is marked with <b>≥</b>.' } });
  }

  /* ── estilos ────────────────────────────────────────────────────────── */
  function ensureStyles() {
    if (document.getElementById('sm-css')) return;
    var st = document.createElement('style'); st.id = 'sm-css';
    st.textContent = [
      '.sm{position:relative;width:100%;height:100%;min-height:520px;overflow:hidden;color:#E8EDFB;font-family:Inter,system-ui,sans-serif;background:radial-gradient(120% 90% at 50% 40%,#0c1430 0%,#060a1a 55%,#020309 100%)}',
      '.sm *{box-sizing:border-box}',
      '.sm-canvas{position:absolute;inset:0;width:100%;height:100%;display:block;cursor:grab;touch-action:none;outline:none}',
      '.sm-canvas:active{cursor:grabbing}',
      '.sm-top{position:absolute;left:0;right:0;top:0;height:40px;z-index:6;display:flex;align-items:center;gap:10px;padding:0 12px;background:linear-gradient(180deg,rgba(3,5,14,.96),rgba(3,5,14,.74));border-bottom:1px solid rgba(255,209,102,.16);backdrop-filter:blur(6px)}',
      '.sm-brand{display:flex;align-items:center;gap:8px;flex:0 0 auto;font-size:11.5px;font-weight:800;letter-spacing:.12em;white-space:nowrap}',
      '.sm-live{font-size:9px;font-weight:800;letter-spacing:.12em;color:#2BE38B;border:1px solid rgba(43,227,139,.45);border-radius:999px;padding:2px 8px;display:inline-flex;align-items:center;gap:5px}',
      '.sm-live.off{color:#FF8FA3;border-color:rgba(255,77,106,.45)}.sm-live.pend{color:#FFD27A;border-color:rgba(255,179,0,.45)}',
      '.sm-live::before{content:"";width:6px;height:6px;border-radius:50%;background:currentColor;box-shadow:0 0 8px currentColor;animation:smBlink 1.6s ease-in-out infinite}',
      '@keyframes smBlink{0%,100%{opacity:1}50%{opacity:.25}}',
      '.sm-next{flex:0 1 auto;min-width:0;display:flex;align-items:center;gap:8px;padding:3px 10px 3px 8px;border-radius:9px;background:rgba(255,209,102,.07);border:1px solid rgba(255,209,102,.28);cursor:pointer;white-space:nowrap;overflow:hidden}',
      '.sm-next:hover{background:rgba(255,209,102,.13)}',
      '.sm-next .lb{font-size:9px;font-weight:800;letter-spacing:.12em;color:#FFD166}',
      '.sm-next .nm{font-size:11.5px;color:#E8EDFB;overflow:hidden;text-overflow:ellipsis;min-width:0;max-width:260px}',
      '.sm-cdx{font-family:"JetBrains Mono",ui-monospace,monospace;font-size:15px;font-weight:800;color:#FFD166;text-shadow:0 0 12px rgba(255,209,102,.45);letter-spacing:.02em}',
      '.sm-ticker{flex:1;min-width:0;overflow:hidden;position:relative;height:100%;display:flex;align-items:center;-webkit-mask-image:linear-gradient(90deg,transparent,#000 4%,#000 96%,transparent);mask-image:linear-gradient(90deg,transparent,#000 4%,#000 96%,transparent)}',
      '.sm-track{display:inline-flex;gap:28px;white-space:nowrap;animation:smScroll 90s linear infinite;padding-right:28px}',
      '.sm-ticker:hover .sm-track{animation-play-state:paused}',
      '@keyframes smScroll{from{transform:translateX(0)}to{transform:translateX(-50%)}}',
      '.sm-tk{font-size:11.5px;color:#C7D0EA;cursor:pointer;display:inline-flex;align-items:center;gap:6px}',
      '.sm-tk:hover{color:#fff}.sm-tk i{width:7px;height:7px;border-radius:50%;display:inline-block;flex:0 0 7px}',
      '.sm-tk .ta{color:#6F7B98;font-size:10.5px;font-family:"JetBrains Mono",ui-monospace,monospace}',
      '.sm-clock{flex:0 0 auto;font-family:"JetBrains Mono",ui-monospace,monospace;font-size:10.5px;color:#7C87A3}',
      '.sm-panel{position:absolute;z-index:5;background:rgba(5,8,20,.86);border:1px solid rgba(140,160,255,.18);border-radius:13px;backdrop-filter:blur(10px);box-shadow:0 10px 40px rgba(0,0,0,.45);overflow:hidden;display:flex;flex-direction:column}',
      '.sm-left{left:10px;top:50px;width:256px;max-height:calc(100% - 196px)}',
      '.sm-right{right:10px;top:50px;width:356px;bottom:10px}',
      '.sm-panel.hid{display:none}',
      '.sm-ph{position:relative;display:flex;align-items:center;gap:8px;padding:9px 12px;border-bottom:1px solid rgba(140,160,255,.12);font-size:10px;font-weight:800;letter-spacing:.12em;color:#9BA6C4;text-transform:uppercase;flex:0 0 auto}',
      '.sm-ph .x{margin-left:auto;cursor:pointer;color:#7C87A3;font-size:14px;line-height:1;padding:2px 6px;border-radius:6px}',
      '.sm-ph .x:hover{background:rgba(140,160,255,.12);color:#fff}',
      '.sm-ph .grab{display:none}',
      '.sm-pb{overflow-y:auto;overflow-x:hidden;padding:8px 12px 12px;flex:1 1 auto;min-height:0}',
      '.sm-pb::-webkit-scrollbar{width:6px}.sm-pb::-webkit-scrollbar-thumb{background:rgba(140,160,255,.2);border-radius:3px}',
      '.sm-g{font-size:9px;font-weight:800;letter-spacing:.14em;color:#5E6884;margin:10px 0 4px;text-transform:uppercase;display:flex;align-items:center;gap:4px}',
      '.sm-g:first-child{margin-top:2px}',
      '.sm-lay{display:flex;align-items:center;gap:7px;padding:4px 2px;font-size:12px;color:#C7D0EA;cursor:pointer;user-select:none;border-radius:7px}',
      '.sm-lay:hover{background:rgba(140,160,255,.07)}.sm-lay.off{opacity:.42}',
      '.sm-lay .dot{width:9px;height:9px;border-radius:50%;flex:0 0 9px;box-shadow:0 0 6px currentColor}',
      '.sm-lay .nm{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
      '.sm-lay .ct{font-family:"JetBrains Mono",ui-monospace,monospace;font-size:10.5px;color:#9BA6C4}',
      '.sm-st{font-size:9px;font-weight:700;border-radius:999px;padding:1px 6px;white-space:nowrap}',
      '.sm-st.ok{color:#2BE38B;background:rgba(43,227,139,.1)}.sm-st.err{color:#FF8FA3;background:rgba(255,77,106,.12)}',
      '.sm-st.pend{color:#FFD27A;background:rgba(255,179,0,.1)}.sm-st.ref{color:#9BA6C4;background:rgba(140,160,255,.1)}',
      '.sm-note{font-size:10px;color:#6F7B98;line-height:1.45;margin-top:8px}',
      '.sm-btn{background:rgba(5,8,20,.88);border:1px solid rgba(140,160,255,.22);color:#C7D0EA;border-radius:999px;font:600 11px Inter,system-ui,sans-serif;padding:5px 11px;cursor:pointer;white-space:nowrap}',
      '.sm-btn:hover{border-color:rgba(255,209,102,.5);color:#fff}',
      '.sm-seg{display:inline-flex;background:rgba(5,8,20,.88);border:1px solid rgba(140,160,255,.22);border-radius:999px;padding:2px}',
      '.sm-seg button{background:none;border:0;color:#9BA6C4;font:700 11px Inter,system-ui,sans-serif;padding:4px 11px;border-radius:999px;cursor:pointer;white-space:nowrap}',
      '.sm-seg button.on{background:rgba(255,209,102,.16);color:#FFD166}',
      '.sm-reopen{position:absolute;z-index:5;top:50px;background:rgba(5,8,20,.88);border:1px solid rgba(140,160,255,.25);color:#C7D0EA;border-radius:10px;padding:6px 10px;font:700 11px Inter,system-ui,sans-serif;cursor:pointer}',
      '.sm-tip{position:absolute;z-index:8;pointer-events:none;background:rgba(4,6,16,.96);border:1px solid rgba(255,209,102,.35);border-radius:9px;padding:7px 10px;font-size:11.5px;color:#E8EDFB;max-width:270px;display:none;line-height:1.4;box-shadow:0 8px 24px rgba(0,0,0,.5)}',
      '.sm-tip .m{color:#8B96B5;font-size:10.5px}',
      /* línea de tiempo */
      '.sm-tl{position:absolute;z-index:5;left:276px;right:376px;bottom:10px;height:136px;background:rgba(5,8,20,.86);border:1px solid rgba(140,160,255,.18);border-radius:13px;backdrop-filter:blur(10px);box-shadow:0 10px 40px rgba(0,0,0,.45);display:flex;flex-direction:column;overflow:hidden}',
      '.sm-tlh{display:flex;align-items:center;gap:8px;padding:6px 10px 4px;flex:0 0 auto;min-width:0}',
      '.sm-tlh .ttl{font-size:10px;font-weight:800;letter-spacing:.12em;color:#9BA6C4;text-transform:uppercase;white-space:nowrap}',
      '.sm-tlh .sc{font-size:10px;color:#6F7B98;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;flex:1}',
      '.sm-tlh .nv{display:flex;gap:4px;flex:0 0 auto}',
      '.sm-tlh .nv button{background:rgba(140,160,255,.08);border:1px solid rgba(140,160,255,.2);color:#C7D0EA;border-radius:7px;font:700 11px Inter,system-ui,sans-serif;padding:3px 8px;cursor:pointer}',
      '.sm-tlh .nv button:hover{border-color:rgba(255,209,102,.5);color:#fff}',
      '.sm-tlw{position:relative;flex:1 1 auto;min-height:0;overflow-x:auto;overflow-y:hidden;scrollbar-width:thin}',
      '.sm-tlw::-webkit-scrollbar{height:5px}.sm-tlw::-webkit-scrollbar-thumb{background:rgba(140,160,255,.22);border-radius:3px}',
      '.sm-tlt{position:relative;height:100%;min-width:100%;cursor:crosshair;touch-action:pan-x;user-select:none}',
      '.sm-ax{position:absolute;left:0;right:0;bottom:18px;height:1px;background:linear-gradient(90deg,rgba(140,160,255,.1),rgba(140,160,255,.35),rgba(140,160,255,.1))}',
      '.sm-tick{position:absolute;bottom:4px;font-size:9px;color:#5E6884;font-family:"JetBrains Mono",ui-monospace,monospace;transform:translateX(-50%);white-space:nowrap;pointer-events:none}',
      '.sm-tick::before{content:"";position:absolute;left:50%;bottom:13px;width:1px;height:5px;background:rgba(140,160,255,.35)}',
      '.sm-now{position:absolute;top:2px;bottom:18px;width:0;border-left:1px dashed rgba(255,209,102,.6);pointer-events:none}',
      '.sm-now span{position:absolute;top:0;left:3px;font-size:8.5px;font-weight:800;letter-spacing:.1em;color:#FFD166}',
      '.sm-cur{position:absolute;top:0;bottom:18px;width:0;border-left:1px solid rgba(0,224,255,.8);pointer-events:none;display:none;box-shadow:0 0 8px rgba(0,224,255,.6)}',
      '.sm-cur span{position:absolute;bottom:2px;left:4px;font-size:9px;color:#00E0FF;font-family:"JetBrains Mono",ui-monospace,monospace;white-space:nowrap;background:rgba(2,4,12,.85);padding:1px 4px;border-radius:4px}',
      '.sm-mk{position:absolute;display:flex;align-items:center;gap:5px;height:22px;padding:0 8px 0 4px;border-radius:999px;background:rgba(12,18,40,.92);border:1px solid rgba(140,160,255,.22);font-size:10.5px;color:#C7D0EA;white-space:nowrap;cursor:pointer;transform:translateX(-9px);transition:border-color .12s,background .12s;max-width:170px}',
      '.sm-mk:hover,.sm-mk.hot{border-color:#00E0FF;color:#fff;background:rgba(0,224,255,.12);z-index:3}',
      '.sm-mk.sel{border-color:#FFD166;color:#fff;background:rgba(255,209,102,.16);box-shadow:0 0 12px rgba(255,209,102,.35);z-index:4}',
      '.sm-mk i{width:10px;height:10px;border-radius:50%;flex:0 0 10px;box-shadow:0 0 6px currentColor}',
      '.sm-mk b{font-weight:700;overflow:hidden;text-overflow:ellipsis}',
      '.sm-mk .g{font-size:9px;color:#34d399}',
      '.sm-stem{position:absolute;width:1px;bottom:18px;background:rgba(140,160,255,.25);pointer-events:none}',
      '.sm-empty{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#9BA6C4;font-size:12px;text-align:center;padding:10px}',
      /* panel derecho */
      '.sm-hero{border:1px solid rgba(255,209,102,.3);border-radius:12px;padding:10px 12px;background:linear-gradient(135deg,rgba(255,209,102,.08),rgba(0,224,255,.04));cursor:pointer}',
      '.sm-hero:hover{border-color:rgba(255,209,102,.6)}',
      '.sm-hero .k{font-size:9px;font-weight:800;letter-spacing:.14em;color:#FFD166;display:flex;align-items:center;gap:4px}',
      '.sm-hero .n{font-size:14px;font-weight:750;color:#fff;margin:4px 0 2px;line-height:1.3}',
      '.sm-hero .m{font-size:11px;color:#8B96B5;line-height:1.45}',
      '.sm-hero .sm-cdx{font-size:22px;display:block;margin:6px 0 2px}',
      '.sm-kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:10px 0}',
      '.sm-kpi{border:1px solid rgba(140,160,255,.12);border-radius:9px;padding:6px 7px;background:rgba(10,16,36,.55);min-width:0}',
      '.sm-kpi .k{font-size:9px;color:#7C87A3;font-weight:700;letter-spacing:.04em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '.sm-kpi .v{font-family:"JetBrains Mono",ui-monospace,monospace;font-size:16px;font-weight:800;margin-top:1px;white-space:nowrap}',
      '.sm-kpi .s{font-size:9.5px;color:#6F7B98;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '.sm-sec{margin-top:12px}',
      '.sm-sh{font-size:10px;font-weight:800;letter-spacing:.1em;color:#7C87A3;text-transform:uppercase;margin-bottom:6px;display:flex;align-items:center;gap:4px}',
      '.sm-sh .r{margin-left:auto;text-transform:none;letter-spacing:0;font-weight:600;color:#5E6884;font-size:9.5px}',
      '.sm-bar{display:flex;align-items:center;gap:7px;font-size:11px;color:#C7D0EA;padding:3px 0}',
      '.sm-bar .n{flex:0 0 120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
      '.sm-bar .b{flex:1;height:6px;border-radius:4px;background:rgba(140,160,255,.1);overflow:hidden}',
      '.sm-bar .b i{display:block;height:100%;border-radius:4px}',
      '.sm-bar .c{font-family:"JetBrains Mono",ui-monospace,monospace;font-size:10.5px;width:34px;text-align:right;color:#E8EDFB}',
      '.sm-co{display:flex;align-items:center;gap:7px;padding:5px 2px;border-bottom:1px solid rgba(140,160,255,.06);font-size:11.5px}',
      '.sm-co .nm{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#E8EDFB;cursor:pointer}',
      '.sm-co .ds{font-family:"JetBrains Mono",ui-monospace,monospace;font-size:10px;color:#7C87A3;white-space:nowrap}',
      '.sm-co .nr{font-family:"JetBrains Mono",ui-monospace,monospace;font-size:11px;font-weight:800;width:24px;text-align:right}',
      '.sm-co .rl{font-size:9.5px;color:#8B96B5;display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '.sm-mini{font:700 10px Inter,system-ui,sans-serif;padding:3px 8px;border-radius:999px;cursor:pointer;color:#00E0FF;background:rgba(0,224,255,.08);border:1px solid rgba(0,224,255,.35);white-space:nowrap}',
      '.sm-mini:hover{background:rgba(0,224,255,.18)}',
      '.sm-tag{display:inline-flex;align-items:center;gap:5px;font-size:9.5px;font-weight:800;letter-spacing:.06em;padding:2px 8px;border-radius:999px;border:1px solid}',
      '.sm-h1{font-size:15px;font-weight:750;line-height:1.3;margin:8px 0 4px;color:#fff;word-wrap:break-word}',
      '.sm-meta{font-size:11px;color:#8B96B5;line-height:1.5;word-wrap:break-word}',
      '.sm-kv{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px}',
      '.sm-kv>div{border:1px solid rgba(140,160,255,.1);border-radius:8px;padding:5px 8px;background:rgba(10,16,36,.45);min-width:0}',
      '.sm-kv .k{font-size:9px;color:#7C87A3;text-transform:uppercase;letter-spacing:.06em}',
      '.sm-kv .v{font-size:12.5px;color:#E8EDFB;font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-family:inherit}',
      '.sm-kv .v.mono{font-family:"JetBrains Mono",ui-monospace,monospace;color:#9bd1ff}',
      '.sm-act{display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:8px 10px;border-radius:9px;cursor:pointer;font:700 12px Inter,system-ui,sans-serif;color:#04060B;background:linear-gradient(90deg,#FFD166,#FF8A3D);border:0;text-decoration:none;flex:1}',
      '.sm-act.ghost{background:rgba(0,224,255,.08);color:#00E0FF;border:1px solid rgba(0,224,255,.4)}',
      '.sm-act.live{background:linear-gradient(90deg,#FF4D6A,#FF8A3D);color:#fff}',
      '.sm-acts{display:flex;gap:6px;margin-top:10px;flex-wrap:wrap}',
      '.sm-link{color:#7AB8FF;text-decoration:none;font-size:11.5px;line-height:1.4;display:block;padding:3px 0;word-break:break-word}',
      '.sm-link:hover{text-decoration:underline}',
      '.sm-back{cursor:pointer;color:#FFD166;font-size:11px;font-weight:700;letter-spacing:0;text-transform:none}',
      '.sm-load{color:#7C87A3;font-size:12px;font-style:italic;padding:14px 4px;text-align:center}',
      '.sm-row{display:flex;gap:8px;align-items:center;padding:6px 4px;border-bottom:1px solid rgba(140,160,255,.07);cursor:pointer;border-radius:6px}',
      '.sm-row:hover{background:rgba(140,160,255,.06)}.sm-row:last-child{border-bottom:0}',
      '.sm-row .d{flex:0 0 52px;font-family:"JetBrains Mono",ui-monospace,monospace;font-size:10px;color:#9BA6C4;line-height:1.3}',
      '.sm-row .t{flex:1;min-width:0;font-size:11.5px;color:#E8EDFB;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
      '.sm-row .t small{display:block;color:#7C87A3;font-size:10px}',
      '.sm-img{width:100%;max-height:140px;object-fit:cover;border-radius:10px;margin-top:8px;border:1px solid rgba(140,160,255,.15);background:#0a1024}',
      '.sm-mbar{display:none}',
      '.sm-glnote{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#9bd1ff;font-size:13px;text-align:center;padding:24px;pointer-events:none}',
      /* modo angosto (móvil / Cabina estrecha) */
      '.sm.nr .sm-panel{left:0;right:0;top:auto;bottom:0;width:auto;max-height:66%;border-radius:16px 16px 0 0;transform:translateY(105%);transition:transform .25s ease;display:flex;z-index:7}',
      '.sm.nr .sm-panel.open{transform:translateY(0)}',
      '.sm.nr .sm-panel.hid{display:flex}',
      '.sm.nr .sm-reopen{display:none}',
      '.sm.nr .sm-ticker,.sm.nr .sm-clock,.sm.nr .sm-brand .bt{display:none}',
      '.sm.nr .sm-next{flex:1}',
      '.sm.nr .sm-next .nm{max-width:none}',
      '.sm.nr .sm-cdx{font-size:13px}',
      '.sm.nr .sm-tl{left:8px;right:8px;bottom:50px;height:118px}',
      '.sm.nr .sm-mbar{display:flex;position:absolute;z-index:4;left:8px;right:8px;bottom:8px;gap:6px;justify-content:space-between;align-items:center}',
      '.sm.nr .sm-mbar .sm-btn{flex:1;text-align:center;padding:8px 6px;font-size:11.5px}',
      '.sm.nr .sm-ph .grab{display:block;position:absolute;left:50%;top:4px;width:38px;height:4px;border-radius:3px;background:rgba(140,160,255,.3);transform:translateX(-50%)}',
      '.sm.nr .sm-tlh .sc{display:none}',
    ].join('\n');
    document.head.appendChild(st);
  }

  function shell() {
    return '<div class="sm" id="sm">' +
      '<canvas class="sm-canvas" id="sm-canvas" tabindex="0" aria-label="' + esc(L('Globo del Space Monitor', 'Space Monitor globe')) + '"></canvas>' +
      '<div class="sm-top"><div class="sm-brand"><span class="sm-live pend" id="sm-live">…</span><span class="bt">SPACE MONITOR</span></div>' +
      '<div class="sm-next" id="sm-next" data-act="next"></div>' +
      '<div class="sm-ticker" id="sm-ticker"><div class="sm-track" id="sm-track"></div></div><span class="sm-clock" id="sm-clock"></span></div>' +
      '<aside class="sm-panel sm-left" id="sm-left"></aside>' +
      '<aside class="sm-panel sm-right" id="sm-right"></aside>' +
      '<button class="sm-reopen" id="sm-reopen-l" style="left:10px;display:none" data-act="reopen" data-side="left">☰ ' + esc(L('Capas', 'Layers')) + '</button>' +
      '<button class="sm-reopen" id="sm-reopen-r" style="right:10px;display:none" data-act="reopen" data-side="right">◉ ' + esc(L('Situación', 'Situation')) + '</button>' +
      '<div class="sm-tl" id="sm-tl"></div>' +
      '<div class="sm-mbar" id="sm-mbar"></div>' +
      '<div class="sm-tip" id="sm-tip"></div>' +
      '</div>';
  }

  /* ── datos derivados ───────────────────────────────────────────────── */
  function indexLaunches() {
    S.byId = {};
    (S.up || []).forEach(function (l) { l._w = 'upcoming'; S.byId[l.id] = l; });
    (S.prev || []).forEach(function (l) { l._w = 'previous'; S.byId[l.id] = l; });
  }
  function nextLaunch() {
    var now = Date.now() / 1000;
    var list = (S.up || []).filter(function (l) { return l.net_ts && ['success', 'failure', 'partial'].indexOf(l.status && l.status.kind) < 0; })
      .sort(function (a, b) { return a.net_ts - b.net_ts; });
    for (var i = 0; i < list.length; i++) {
      if (list[i].net_ts >= now - 3600 || (list[i].status && list[i].status.kind === 'inflight')) return list[i];
    }
    return null;
  }
  function recentList() {
    var now = Date.now() / 1000;
    return (S.prev || []).filter(function (l) { return l.net_ts && l.net_ts >= now - 30 * 86400; });
  }
  function padsAgg() {
    var map = {}, now = Date.now() / 1000;
    function add(l, kind) {
      if (!hasLL(l)) return;
      var k = l.pad.name + '|' + l.pad.lat.toFixed(3) + '|' + l.pad.lon.toFixed(3);
      var a = map[k] || (map[k] = { key: k, name: l.pad.name, location: l.pad.location, cc: l.pad.country_code, lat: l.pad.lat, lon: l.pad.lon, up: [], rec: [] });
      a[kind].push(l);
    }
    (S.up || []).forEach(function (l) { add(l, 'up'); });
    recentList().forEach(function (l) { add(l, 'rec'); });
    return Object.keys(map).map(function (k) {
      var a = map[k];
      a.up.sort(function (x, y) { return (x.net_ts || 0) - (y.net_ts || 0); });
      a.rec.sort(function (x, y) { return (y.net_ts || 0) - (x.net_ts || 0); });
      a.soon = a.up.some(function (l) { return l.net_ts && l.net_ts - now < 48 * 3600 && l.net_ts > now - 3600; });
      a.week = a.up.some(function (l) { return l.net_ts && l.net_ts - now < 7 * 86400; });
      return a;
    });
  }
  function graphLinks() {
    var LINKS = window.LINKS || [], NB = window.NODE_BY_ID || {};
    var lid = function (v) { return (typeof v === 'object' && v !== null) ? v.id : v; };
    var ext = {}, n = 0;
    LINKS.forEach(function (l) {
      var s = lid(l.source), t = lid(l.target), sn = NB[s], tn = NB[t];
      if (!sn || !tn) return;
      var ss = isSpaceNode(sn), ts = isSpaceNode(tn);
      if (ss === ts) return;
      n++;
      var other = ss ? t : s, sp = ss ? s : t, dir = ss ? 'buys' : 'supplies';   // dir desde la óptica de la empresa externa
      var e = ext[other] || (ext[other] = { id: other, w: 0, supplies: 0, buys: 0, with: {} });
      e.w += +l.w || 0; e[dir]++; e.with[sp] = 1;
    });
    var list = Object.keys(ext).map(function (k) { return ext[k]; }).sort(function (a, b) { return b.w - a.w; });
    return { links: n, companies: list.length, top: list };
  }

  /* ── panel de capas ────────────────────────────────────────────────── */
  function srcPill(src, err) {
    if (err && !src) return '<span class="sm-st err" title="' + esc(err) + '">' + esc(L('sin servidor', 'no server')) + '</span>';
    if (!src) return '<span class="sm-st pend">…</span>';
    if (src.pending) return '<span class="sm-st pend">' + esc(L('cargando', 'loading')) + '</span>';
    if (src.error_code === 'refreshing') return '<span class="sm-st pend">' + esc(L('actualizando', 'refreshing')) + '</span>';
    if (!src.ok && src.stale) return '<span class="sm-st pend" title="' + esc(errText(src) + ' · ' + L('datos de ', 'data from ') + fmtIso(src.as_of)) + '">' + esc(L('en caché', 'cached')) + '</span>';
    if (!src.ok) return '<span class="sm-st err" title="' + esc(errText(src)) + '">' + esc(L('caída', 'down')) + '</span>';
    return '<span class="sm-st ok" title="' + esc((src.provider || '') + (src.as_of ? ' · ' + fmtIso(src.as_of) : '')) + '">' + esc(L('vivo', 'live')) + '</span>';
  }
  function layerCount(id) {
    if (id === 'upcoming') return (S.up || []).length;
    if (id === 'recent') return recentList().length;
    if (id === 'pads') return padsAgg().length;
    if (id === 'orbit') return (S.sel && S.sel.kind === 'launch') || nextLaunch() ? 1 : 0;
    if (id === 'companies') return spaceNodes().length;
    if (id === 'shells') return 3;
    return '';
  }
  function layerPill(id) {
    if (id === 'upcoming' || id === 'orbit') return srcPill(S.upSrc, S.upErr);
    if (id === 'recent') return srcPill(S.prevSrc, S.prevErr);
    if (id === 'pads') return srcPill(S.upSrc, S.upErr);
    if (id === 'shells') return '<span class="sm-st ref">ref</span>';
    return '';
  }
  function renderLayers() {
    var el = $('sm-left'); if (!el) return;
    var h = '<div class="sm-ph"><span class="grab"></span>☰ ' + esc(L('Capas', 'Layers')) + '<span class="x" data-act="collapse" data-side="left" title="' + esc(L('Ocultar', 'Hide')) + '">—</span></div><div class="sm-pb">';
    h += '<div class="sm-g">' + esc(L('Lanzamientos · Launch Library 2', 'Launches · Launch Library 2')) + chip('sm_ll2') + '</div>';
    LAYERS.filter(function (l) { return l.g === 'launch'; }).forEach(function (l) { h += layRow(l.id, l.c, l.i + ' ' + L(l.es, l.en), layerCount(l.id), layerPill(l.id), !!S.vis[l.id]); });
    h += '<div class="sm-g">' + esc(L('Constelaciones · CelesTrak', 'Constellations · CelesTrak')) + chip('sm_altitude') + '</div>';
    var t = S.tle;
    if (!t) {
      h += '<div class="sm-note" style="margin-top:2px">' + esc(S.tleErr ? L('Satélites no disponibles: ', 'Satellites unavailable: ') + S.tleErr : L('Cargando satélites reales…', 'Loading real satellites…')) + '</div>';
    } else {
      var fb = t.source === 'fallback';
      (t.constellations || []).forEach(function (c) {
        var pill = fb ? '<span class="sm-st ref" title="' + esc(L('CelesTrak no responde: órbitas de referencia, NO en vivo', 'CelesTrak unreachable: reference orbits, NOT live')) + '">ref</span>'
          : c.error ? '<span class="sm-st err" title="' + esc(c.error) + '">' + esc(L('caída', 'down')) + '</span>'
            : '<span class="sm-st ok" title="CelesTrak">' + esc(L('vivo', 'live')) + '</span>';
        var on = S.satVis[c.name] !== false;
        h += '<div class="sm-lay' + (on && (c.rendered || 0) ? '' : ' off') + '" data-act="sat" data-name="' + esc(c.name) + '" role="checkbox" aria-checked="' + on + '">' +
          '<span class="dot" style="background:' + esc(c.color) + ';color:' + esc(c.color) + '"></span><span class="nm">' + esc(c.name === 'Estaciones (ISS/CSS)' ? L('Estaciones (ISS/CSS)', 'Stations (ISS/CSS)') : c.name) + '</span>' +
          '<span class="ct">' + (c.count ? Number(c.count).toLocaleString(en() ? 'en-US' : 'es-ES') : '—') + '</span>' + pill + '</div>';
      });
      h += '<div class="sm-note" style="margin-top:4px">' + esc(fb ? L('⚠ CelesTrak no responde: conteos y órbitas de REFERENCIA, no en vivo.', '⚠ CelesTrak unreachable: REFERENCE counts and orbits, not live.')
        : L('Conteo = satélites reales del grupo; se dibuja una muestra (' + (t.rendered || 0) + ').', 'Count = real satellites in the group; a sample is drawn (' + (t.rendered || 0) + ').')) +
        (window.satellite ? '' : ' ' + esc(L('Sin SGP4 en este navegador: posiciones modeladas.', 'No SGP4 in this browser: modeled positions.'))) + '</div>';
    }
    h += '<div class="sm-g">' + esc(L('Tu grafo', 'Your graph')) + '</div>';
    h += layRow('companies', LBY.companies.c, LBY.companies.i + ' ' + L(LBY.companies.es, LBY.companies.en), layerCount('companies'), '', !!S.vis.companies);
    h += '<div class="sm-g">' + esc(L('Referencia · no en vivo', 'Reference · not live')) + '</div>';
    h += layRow('shells', LBY.shells.c, LBY.shells.i + ' ' + L(LBY.shells.es, LBY.shells.en), 3, layerPill('shells'), !!S.vis.shells);
    var errs = [];
    if (S.upSrc && !S.upSrc.ok && !S.upSrc.pending) errs.push(L('Próximos', 'Upcoming') + ' (' + errText(S.upSrc) + (S.upSrc.stale ? ' · ' + L('datos de ', 'data from ') + fmtIso(S.upSrc.as_of) : '') + ')');
    if (S.prevSrc && !S.prevSrc.ok && !S.prevSrc.pending) errs.push(L('Recientes', 'Recent') + ' (' + errText(S.prevSrc) + (S.prevSrc.stale ? ' · ' + L('datos de ', 'data from ') + fmtIso(S.prevSrc.as_of) : '') + ')');
    if (S.upErr && !S.upSrc) errs.push(L('Servidor', 'Server') + ' (' + S.upErr + ')');
    if (errs.length) h += '<div class="sm-note" style="color:#FF8FA3">⚠ ' + esc(L('Fuentes con problemas: ', 'Sources with issues: ') + errs.join(' · ')) + '</div>';
    h += '<div class="sm-note">' + esc(L('Arcos = trayectoria esquemática desde la plataforma real.', 'Arcs = schematic trajectory from the real pad.')) + chip('sm_arcs') + '</div>';
    h += '</div>';
    el.innerHTML = h;
  }
  function layRow(id, c, name, ct, pill, on) {
    return '<div class="sm-lay' + (on ? '' : ' off') + '" data-act="toggle" data-layer="' + id + '" role="checkbox" aria-checked="' + on + '">' +
      '<span class="dot" style="background:' + c + ';color:' + c + '"></span><span class="nm">' + esc(name) + '</span><span class="ct">' + ct + '</span>' + (pill || '') + '</div>';
  }

  /* ── barra superior ────────────────────────────────────────────────── */
  function renderTop() {
    var live = $('sm-live'), nx = $('sm-next'), tr = $('sm-track');
    var ok = S.upSrc && (S.upSrc.ok || S.upSrc.stale), pend = !S.upSrc && !S.upErr;
    if (live) {
      live.className = 'sm-live' + (S.upSrc && S.upSrc.ok ? '' : ok || pend ? ' pend' : ' off');
      live.textContent = S.upSrc && S.upSrc.ok ? L('EN VIVO', 'LIVE') : S.upSrc && S.upSrc.stale ? L('EN CACHÉ', 'CACHED') : pend ? L('CONECTANDO', 'CONNECTING') : L('SIN FUENTE', 'NO FEED');
    }
    var n = nextLaunch();
    S.nextId = n ? n.id : null;
    if (nx) {
      nx.style.display = '';
      nx.innerHTML = n ? '<span class="lb">' + esc(L('PRÓXIMO', 'NEXT')) + '</span><span class="sm-cdx sm-cd" data-id="' + esc(n.id) + '">' + esc(countdown(n).t) + '</span>' +
        '<span class="nm">' + esc(rocketName(n) + ' · ' + missionName(n)) + '</span>'
        : '<span class="lb">' + esc(L('PRÓXIMO', 'NEXT')) + '</span><span class="nm">' + esc(pend ? L('cargando…', 'loading…') : L('sin datos de lanzamientos', 'no launch data')) + '</span>';
    }
    if (!tr) return;
    var list = (S.up || []).filter(function (l) { return l.net_ts && l.net_ts > Date.now() / 1000 - 3600; }).slice(0, 14);
    if (!list.length) { tr.innerHTML = ''; return; }
    var h = list.map(function (l) {
      var c = ST_C[(l.status && l.status.kind) || 'other'];
      return '<span class="sm-tk" data-act="launch" data-id="' + esc(l.id) + '"><i style="background:' + c + ';box-shadow:0 0 6px ' + c + '"></i><b style="color:#fff">' + esc(rocketName(l)) + '</b>' +
        esc(missionName(l)) + (padLoc(l) ? ' · ' + esc(padLoc(l)) : '') + '<span class="ta">' + esc(fmtDate(l.net_ts, true)) + '</span></span>';
    }).join('');
    tr.innerHTML = h + h;
    tr.style.animationDuration = Math.max(40, list.length * 7) + 's';
  }
  function tick() {
    if (!S.root) return;
    var now = Date.now() / 1000;
    var els = S.root.querySelectorAll('.sm-cd[data-id]');
    for (var i = 0; i < els.length; i++) {
      var l = S.byId[els[i].getAttribute('data-id')];
      if (l) els[i].textContent = countdown(l, now).t;
    }
    // el próximo ya despegó hace > 1 h → pasar al siguiente
    var n = S.nextId && S.byId[S.nextId];
    if (n && n.net_ts && now - n.net_ts > 3600 && !(n.status && n.status.kind === 'inflight')) { renderTop(); drawLaunches(); }
    var c = $('sm-clock'); if (c) c.textContent = new Date().toISOString().slice(11, 19) + ' UTC';
  }

  /* ── línea de tiempo ───────────────────────────────────────────────── */
  function tlList() {
    var now = Date.now() / 1000;
    if (S.tlMode === 'upcoming') return (S.up || []).filter(function (l) { return l.net_ts && l.net_ts >= now - 3600 && l.net_ts <= now + 30 * 86400; }).sort(function (a, b) { return a.net_ts - b.net_ts; });
    return recentList().slice().sort(function (a, b) { return a.net_ts - b.net_ts; });
  }
  function tlDomain(list) {
    var now = Date.now() / 1000, t0, t1;
    if (S.tlMode === 'upcoming') {
      var last = list.length ? list[list.length - 1].net_ts : now;
      t0 = now - 3 * 3600; t1 = Math.max(now + 7 * 86400, Math.min(now + 30 * 86400, last + 12 * 3600));
    } else {
      var first = list.length ? list[0].net_ts : now;
      t1 = now + 3 * 3600; t0 = Math.min(now - 7 * 86400, Math.max(now - 30 * 86400, first - 12 * 3600));
    }
    return [t0, t1];
  }
  function renderTimeline() {
    var el = $('sm-tl'); if (!el) return;
    var list = tlList(), dom = tlDomain(list), days = (dom[1] - dom[0]) / 86400;
    var seg = '<div class="sm-seg" role="group">' + [['upcoming', L('Próximos', 'Upcoming')], ['previous', L('Recientes', 'Recent')]].map(function (m) {
      return '<button data-act="tlmode" data-mode="' + m[0] + '" class="' + (S.tlMode === m[0] ? 'on' : '') + '">' + esc(m[1]) + '</button>';
    }).join('') + '</div>';
    var src = S.tlMode === 'upcoming' ? S.upSrc : S.prevSrc;
    var scope = list.length + ' ' + L('lanzamientos', 'launches') + ' · ' + Math.round(days) + ' ' + L('días', 'days') +
      (src && src.stale ? ' · ⚠ ' + L('datos de ', 'data from ') + fmtIso(src.as_of) : '') + ' · ' + L('arrastra para explorar', 'drag to scrub');
    var h = '<div class="sm-tlh"><span class="ttl">⏱ ' + esc(L('Línea de tiempo', 'Timeline')) + '</span>' + seg + '<span class="sc">' + esc(scope) + '</span>' +
      '<span class="nv"><button data-act="step" data-d="-1" title="' + esc(L('Anterior', 'Previous')) + '">◀</button><button data-act="step" data-d="1" title="' + esc(L('Siguiente', 'Next')) + '">▶</button>' +
      '<button data-act="zoom" data-f="0.8" title="Zoom +">＋</button><button data-act="zoom" data-f="1.25" title="Zoom −">－</button><button data-act="reset" title="' + esc(L('Vista', 'View')) + '">⟲</button></span></div>';
    h += '<div class="sm-tlw" id="sm-tlw"><div class="sm-tlt" id="sm-tlt" tabindex="0" aria-label="' + esc(L('Línea de tiempo de lanzamientos', 'Launch timeline')) + '"></div></div>';
    el.innerHTML = h;
    layoutTimeline();
  }
  function layoutTimeline() {
    var w = $('sm-tlw'), t = $('sm-tlt'); if (!w || !t) return;
    var list = tlList(), dom = tlDomain(list), days = (dom[1] - dom[0]) / 86400;
    var W = Math.max(w.clientWidth || 300, Math.round(days * (S.narrow ? 64 : 34)));
    t.style.width = W + 'px';
    S.tl = { list: list, dom: dom, W: W };
    var x = function (ts) { return 14 + (ts - dom[0]) / (dom[1] - dom[0]) * (W - 28); };
    var h = '<div class="sm-ax"></div>';
    // marcas por día (cada 1, 2 o 7 días según densidad)
    var pxDay = (W - 28) / days, step = pxDay > 44 ? 1 : pxDay > 22 ? 2 : 7;
    var d0 = new Date(dom[0] * 1000); d0.setUTCHours(0, 0, 0, 0);
    for (var ts = d0.getTime() / 1000 + 86400, k = 0; ts < dom[1]; ts += 86400, k++) {
      if (k % step) continue;
      h += '<span class="sm-tick" style="left:' + x(ts).toFixed(1) + 'px">' + esc(fmtDate(ts)) + '</span>';
    }
    var now = Date.now() / 1000;
    h += '<div class="sm-now" style="left:' + x(now).toFixed(1) + 'px"><span>' + esc(L('AHORA', 'NOW')) + '</span></div>';
    var lanes = S.narrow ? 2 : 3, last = [], gap = S.narrow ? 118 : 132;
    for (var i = 0; i < lanes; i++) last.push(-1e9);
    var selId = S.sel && S.sel.kind === 'launch' ? S.sel.data.id : null;
    list.forEach(function (l, idx) {
      var px = x(l.net_ts), lane = -1;
      for (var j = 0; j < lanes; j++) { if (px - last[j] >= gap) { lane = j; break; } }
      if (lane < 0) { lane = 0; for (var q = 1; q < lanes; q++) if (last[q] < last[lane]) lane = q; }
      last[lane] = px;
      var top = 4 + lane * 25, c = S.tlMode === 'previous' ? ST_C[(l.status && l.status.kind) || 'other'] : hashC(provName(l));
      var g = (l.graph || []).length;
      h += '<div class="sm-stem" style="left:' + px.toFixed(1) + 'px;top:' + (top + 22) + 'px"></div>' +
        '<div class="sm-mk' + (l.id === selId ? ' sel' : '') + '" data-act="launch" data-id="' + esc(l.id) + '" data-i="' + idx + '" style="left:' + px.toFixed(1) + 'px;top:' + top + 'px" title="' + esc(provName(l) + ' · ' + rocketName(l) + ' · ' + missionName(l) + ' · ' + fmtDate(l.net_ts, true)) + '">' +
        '<i style="background:' + c + ';color:' + c + '"></i><b>' + esc(rocketName(l)) + '</b>' + (g ? '<span class="g" title="' + esc(L('empresas de tu grafo', 'companies in your graph')) + '">◆' + g + '</span>' : '') + '</div>';
    });
    h += '<div class="sm-cur" id="sm-cur"><span></span></div>';
    if (!list.length) {
      var src = S.tlMode === 'upcoming' ? S.upSrc : S.prevSrc, err = S.tlMode === 'upcoming' ? S.upErr : S.prevErr;
      h += '<div class="sm-empty">' + esc(!src && !err ? L('Cargando lanzamientos…', 'Loading launches…')
        : err && !src ? L('Servidor no disponible: no hay datos de lanzamientos (no se inventan).', 'Server unavailable: no launch data (nothing is made up).')
          : src && !src.ok && !src.stale ? L('Launch Library 2 no responde ahora: ', 'Launch Library 2 is not responding right now: ') + errText(src)
            : L('Sin lanzamientos en este periodo.', 'No launches in this period.')) + '</div>';
    }
    t.innerHTML = h;
    // desplaza para ver la selección / "ahora"
    var focusX = selId && S.byId[selId] && S.byId[selId].net_ts ? x(S.byId[selId].net_ts) : x(now);
    if (W > w.clientWidth) w.scrollLeft = Math.max(0, focusX - w.clientWidth * (S.tlMode === 'upcoming' && !selId ? 0.1 : 0.5));
  }
  function tlPick(clientX) {
    var t = $('sm-tlt'); if (!t || !S.tl || !S.tl.list.length) return null;
    var r = t.getBoundingClientRect(), px = clientX - r.left, dom = S.tl.dom, W = S.tl.W;
    var ts = dom[0] + (px - 14) / (W - 28) * (dom[1] - dom[0]);
    var best = null;
    S.tl.list.forEach(function (l) { var d = Math.abs(l.net_ts - ts); if (!best || d < best.d) best = { d: d, l: l }; });
    var cur = $('sm-cur');
    if (cur) {
      cur.style.display = 'block'; cur.style.left = Math.max(0, Math.min(W, px)) + 'px';
      cur.firstChild.textContent = fmtDate(ts, true);
    }
    var mks = t.querySelectorAll('.sm-mk.hot'); for (var i = 0; i < mks.length; i++) mks[i].classList.remove('hot');
    if (best) { var m = t.querySelector('.sm-mk[data-id="' + cssEsc(best.l.id) + '"]'); if (m) m.classList.add('hot'); }
    return best ? best.l : null;
  }
  function cssEsc(s) { return window.CSS && CSS.escape ? CSS.escape(s) : String(s).replace(/"/g, '\\"'); }
  function bindTimeline() {
    var root = S.root;
    var down = function (e) {
      var t = $('sm-tlt'); if (!t || !t.contains(e.target) || e.target.closest('.sm-mk')) return;
      if (e.pointerType === 'touch') return;          // en táctil: el dedo desplaza la franja; tocar un chip selecciona
      S.scrub = { last: 0 };
      try { t.setPointerCapture(e.pointerId); } catch (err) {}
      var l = tlPick(e.clientX); if (l) previewFocus(l);
      e.preventDefault();
    };
    var move = function (e) {
      if (!S.scrub) return;
      var l = tlPick(e.clientX);
      if (l && Date.now() - S.scrub.last > 220) { S.scrub.last = Date.now(); previewFocus(l); }
    };
    var up = function (e) {
      if (!S.scrub) return;
      var l = tlPick(e.clientX); S.scrub = null;
      var cur = $('sm-cur'); if (cur) cur.style.display = 'none';
      if (l) selectLaunch(l, { focus: true });
    };
    root.addEventListener('pointerdown', down);
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
    var key = function (e) {
      if (!S.root || !document.activeElement || document.activeElement.id !== 'sm-tlt') return;
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { step(e.key === 'ArrowRight' ? 1 : -1); e.preventDefault(); }
    };
    window.addEventListener('keydown', key);
    S._tlh = [['pointerdown', down, root], ['pointermove', move, window], ['pointerup', up, window], ['keydown', key, window]];
  }
  function previewFocus(l) {
    if (S.globe && hasLL(l)) S.globe.focusOn(l.pad.lat, l.pad.lon, { duration: 500 });
  }
  function step(d) {
    var list = S.tl ? S.tl.list : tlList(); if (!list.length) return;
    var cur = S.sel && S.sel.kind === 'launch' ? list.indexOf(S.sel.data) : -1;
    var i = cur < 0 ? (d > 0 ? 0 : list.length - 1) : Math.max(0, Math.min(list.length - 1, cur + d));
    if (cur < 0 && S.tlMode === 'upcoming' && S.nextId) { var ni = list.indexOf(S.byId[S.nextId]); if (ni >= 0) i = ni; }
    selectLaunch(list[i], { focus: true });
  }

  /* ── panel derecho: Situación espacial ─────────────────────────────── */
  function heroHTML() {
    var n = nextLaunch();
    if (!n) {
      return '<div class="sm-hero" style="cursor:default"><div class="k">🚀 ' + esc(L('PRÓXIMO LANZAMIENTO', 'NEXT LAUNCH')) + '</div><div class="m" style="margin-top:6px">' +
        esc(!S.upSrc && !S.upErr ? L('Cargando…', 'Loading…') : S.upErr && !S.upSrc ? L('Servidor no disponible.', 'Server unavailable.') : S.upSrc && !S.upSrc.ok && !S.upSrc.stale ? L('Launch Library 2 no responde: ', 'Launch Library 2 not responding: ') + errText(S.upSrc) : L('Sin lanzamientos próximos en los datos.', 'No upcoming launches in the data.')) + '</div></div>';
    }
    var g = (n.graph || []).map(function (x) { return x.label; }).slice(0, 3).join(' · ');
    return '<div class="sm-hero" data-act="launch" data-id="' + esc(n.id) + '"><div class="k">🚀 ' + esc(L('PRÓXIMO LANZAMIENTO', 'NEXT LAUNCH')) + chip('sm_countdown') + '<span style="margin-left:auto">' + stTag(n) + '</span></div>' +
      '<span class="sm-cdx sm-cd" data-id="' + esc(n.id) + '">' + esc(countdown(n).t) + '</span>' +
      '<div class="n">' + esc(missionName(n)) + '</div>' +
      '<div class="m">' + esc(provName(n) + ' · ' + rocketName(n)) + (orbitAbbr(n) ? ' · ' + esc(L('órbita ', 'orbit ') + orbitAbbr(n)) : '') + '<br>📍 ' + esc((n.pad && (n.pad.location || n.pad.name)) || '?') + '<br>🕒 ' + esc(fmtDate(n.net_ts, true)) +
      (g ? '<br><span style="color:#34d399">◆ ' + esc(g) + '</span>' : '') + '</div></div>';
  }
  function kpisHTML() {
    var sm = S.summary && S.summary.counts, t = S.tle, fb = t && t.source === 'fallback';
    var oc = S.summary && S.summary.outcomes_30d;
    var succ = oc ? oc.success + oc.failure + oc.partial : 0;
    var rate = succ ? Math.round(oc.success / succ * 100) : null;
    var ge = (!sm && S.sumErr) ? '—' : '…';
    var k = [
      [L('Próx. 7 días', 'Next 7 days'), sm ? (sm.upcoming_7d_truncated ? '≥' : '') + sm.upcoming_7d : ge, '#FFD166', L('lanzamientos', 'launches')],
      [L('Próx. 30 días', 'Next 30 days'), sm ? (sm.upcoming_30d_truncated ? '≥' : '') + sm.upcoming_30d : ge, '#FF8A3D', L('lanzamientos', 'launches')],
      [L('Últimos 30 d', 'Last 30 d'), sm ? (sm.previous_30d_truncated ? '≥' : '') + sm.previous_30d : ge, '#2BE38B', rate != null ? rate + '% ' + L('éxito', 'success') : ''],
      [L('Satélites', 'Satellites'), t ? (fb ? '—' : Number(t.total_real || 0).toLocaleString(en() ? 'en-US' : 'es-ES')) : '…', '#9bd1ff', fb ? L('fuente caída', 'source down') : 'CelesTrak'],
      [L('Constelac.', 'Constell.'), t ? (fb ? '—' : (t.constellations || []).filter(function (c) { return c.count > 0; }).length) : '…', '#B983FF', L('rastreadas', 'tracked')],
      [L('Plataformas', 'Pads'), S.up ? padsAgg().filter(function (p) { return p.up.length; }).length : '…', '#00E0FF', L('con próximos', 'with upcoming')],
    ];
    return '<div class="sm-kpis">' + k.map(function (x) {
      return '<div class="sm-kpi"><div class="k">' + esc(x[0]) + '</div><div class="v" style="color:' + x[2] + '">' + esc(x[1]) + '</div><div class="s">' + esc(x[3]) + '</div></div>';
    }).join('') + '</div>';
  }
  function providersHTML() {
    var h = '<div class="sm-sec"><div class="sm-sh">🏭 ' + esc(L('Lanzamientos por proveedor', 'Launches by provider')) + chip('sm_ll2') +
      '<span class="r"><span class="sm-seg" style="padding:1px">' + [['week', L('7 d', '7 d')], ['month', L('30 d', '30 d')], ['past_month', L('últ. 30 d', 'last 30 d')]].map(function (w) {
        return '<button data-act="provwin" data-w="' + w[0] + '" class="' + (S.provWin === w[0] ? 'on' : '') + '" style="padding:2px 8px;font-size:10px">' + esc(w[1]) + '</button>';
      }).join('') + '</span></span></div>';
    var bp = S.summary && S.summary.by_provider && S.summary.by_provider[S.provWin];
    if (!bp) return h + '<div class="sm-meta">' + esc(S.sumErr ? L('No disponible (servidor sin respuesta).', 'Not available (server not responding).') : L('Calculando…', 'Computing…')) + '</div></div>';
    if (!bp.length) return h + '<div class="sm-meta">' + esc(L('Sin lanzamientos en este periodo.', 'No launches in this period.')) + '</div></div>';
    var max = bp[0].count || 1;
    bp.slice(0, 8).forEach(function (p) {
      var c = hashC(p.name);
      h += '<div class="sm-bar"' + (p.graph_id ? ' style="cursor:pointer" data-act="co" data-id="' + esc(p.graph_id) + '"' : '') + '><span class="n" title="' + esc(p.name) + '">' + (p.graph_id ? '◆ ' : '') + esc(p.abbrev && p.abbrev.length <= 10 ? p.abbrev : p.name) + '</span>' +
        '<span class="b"><i style="width:' + Math.max(4, p.count / max * 100) + '%;background:' + c + '"></i></span><span class="c">' + p.count + '</span></div>';
    });
    if (bp.length > 8) h += '<div class="sm-note" style="margin-top:2px">+' + (bp.length - 8) + ' ' + esc(L('proveedores más', 'more providers')) + '</div>';
    return h + '<div class="sm-note" style="margin-top:4px">◆ = ' + esc(L('empresa de tu grafo', 'company in your graph')) + '</div></div>';
  }
  function constellationsHTML() {
    var t = S.tle; if (!t) return '';
    var cs = (t.constellations || []).filter(function (c) { return c.count > 0; }).sort(function (a, b) { return b.count - a.count; });
    if (!cs.length) return '';
    var fb = t.source === 'fallback', max = cs[0].count;
    var h = '<div class="sm-sec"><div class="sm-sh">🛰 ' + esc(L('Constelaciones en órbita', 'Constellations in orbit')) + chip('sm_altitude') + '<span class="r">' + esc(fb ? L('referencia · no en vivo', 'reference · not live') : 'CelesTrak') + '</span></div>';
    cs.slice(0, 8).forEach(function (c) {
      var nm = c.name === 'Estaciones (ISS/CSS)' ? L('Estaciones', 'Stations') : c.name;
      h += '<div class="sm-bar" style="cursor:pointer" data-act="solo" data-name="' + esc(c.name) + '" title="' + esc(L('Mostrar solo esta constelación', 'Show only this constellation')) + '"><span class="n">' + esc(nm) + '</span>' +
        '<span class="b"><i style="width:' + Math.max(3, Math.sqrt(c.count / max) * 100) + '%;background:' + esc(c.color) + '"></i></span><span class="c" style="width:44px">' + Number(c.count).toLocaleString(en() ? 'en-US' : 'es-ES') + '</span></div>';
    });
    return h + '<div class="sm-note" style="margin-top:2px">' + esc(L('Barra en escala raíz (Starlink es mucho mayor). Clic = ver solo esa.', 'Bar in square-root scale (Starlink is far larger). Click = show only that one.')) + '</div></div>';
  }
  function companiesHTML() {
    var NS = spaceNodes();
    if (!NS.length) return '';
    var rows = NS.map(function (n) { var m = mcap(n.id); return { n: n, m: m, nrs: nrsOf(n.id) }; })
      .sort(function (a, b) { return (b.m ? b.m.v : -1) - (a.m ? a.m.v : -1); });
    var anyLive = rows.some(function (r) { return r.m && r.m.live; });
    var h = '<div class="sm-sec"><div class="sm-sh">🏢 ' + esc(L('Empresas espaciales de tu grafo', 'Space companies in your graph')) + chip('nrs') +
      '<span class="r">' + esc(anyLive ? L('cap. en vivo · NRS', 'live cap · NRS') : L('cap. catálogo · NRS', 'catalog cap · NRS')) + '</span></div>';
    rows.slice(0, S.moreCos ? rows.length : 8).forEach(function (r) {
      var chg = dayChg(r.n), n = r.n;
      h += '<div class="sm-co"><span class="nm" data-act="co" data-id="' + esc(n.id) + '" title="' + esc(n.label) + '">' + esc(n.label) +
        '<span class="rl">' + esc((n.mkt || L('privada', 'private')) + (chg != null ? ' · ' : '')) + (chg != null ? '<b style="color:' + (chg >= 0 ? '#2BE38B' : '#FF4D6A') + '">' + (chg >= 0 ? '+' : '') + chg.toFixed(1) + '%</b>' : '') + '</span></span>' +
        '<span class="ds" title="' + esc(r.m ? (r.m.live ? L('capitalización en vivo', 'live market cap') + (r.m.as_of ? ' · ' + r.m.as_of : '') : L('capitalización / valuación del catálogo (no en vivo)', 'catalog market cap / valuation (not live)')) : '') + '">' +
        (r.m ? (r.m.live ? '<span style="color:#2BE38B">●</span> ' : '') + esc(fmtCap(r.m.v)) : '—') + '</span>' +
        '<span class="nr" style="color:' + nrsColor(r.nrs == null ? 50 : r.nrs) + '" title="NRS">' + (r.nrs == null ? '—' : r.nrs) + '</span>' +
        '<button class="sm-mini" data-act="xray" data-id="' + esc(n.id) + '" title="X-Ray">🔬</button></div>';
    });
    if (rows.length > 8) h += '<button class="sm-mini" data-act="morecos" style="margin-top:6px">' + esc(S.moreCos ? L('ver menos', 'show less') : L('ver las ' + rows.length, 'show all ' + rows.length)) + '</button>';
    return h + '</div>';
  }
  function exposureHTML() {
    var gl = graphLinks(), NB = window.NODE_BY_ID || {};
    var h = '<div class="sm-sec"><div class="sm-sh">🔗 ' + esc(L('Exposición de tu grafo al espacio', 'Your graph\'s space exposure')) + chip('sm_exposure') + '</div>';
    var sg = S.summary && S.summary.graph;
    if (sg) h += '<div class="sm-meta" style="margin-bottom:6px">' + esc(L(sg.launches_with_graph + ' de ' + sg.upcoming_total + ' próximos lanzamientos involucran empresas de tu grafo.', sg.launches_with_graph + ' of ' + sg.upcoming_total + ' upcoming launches involve companies in your graph.')) + chip('sm_graph_match') + '</div>';
    if (!gl.links) return h + '<div class="sm-meta">' + esc(L('Sin relaciones entre el sector espacial y el resto del grafo.', 'No links between the space sector and the rest of the graph.')) + '</div></div>';
    h += '<div class="sm-meta" style="margin-bottom:4px">' + esc(L(gl.companies + ' empresas de otros sectores, ' + gl.links + ' relaciones. Las más expuestas:', gl.companies + ' companies from other sectors, ' + gl.links + ' links. Most exposed:')) + '</div>';
    gl.top.slice(0, 6).forEach(function (e) {
      var n = NB[e.id]; if (!n) return;
      var nrs = nrsOf(e.id), wth = Object.keys(e.with).slice(0, 2).map(function (id) { return (NB[id] || {}).label || id; }).join(', ');
      var rel = e.supplies && e.buys ? L('provee y compra', 'supplies & buys') : e.supplies ? L('provee a', 'supplies') : L('compra a', 'buys from');
      h += '<div class="sm-co"><span class="nm" data-act="co" data-id="' + esc(e.id) + '">' + esc(n.label) + '<span class="rl">' + esc(rel + ' ' + wth + (Object.keys(e.with).length > 2 ? '…' : '')) + '</span></span>' +
        '<span class="ds">w ' + e.w.toFixed(1) + '</span><span class="nr" style="color:' + nrsColor(nrs == null ? 50 : nrs) + '">' + (nrs == null ? '—' : nrs) + '</span>' +
        '<button class="sm-mini" data-act="xray" data-id="' + esc(e.id) + '" title="X-Ray">🔬</button></div>';
    });
    return h + '</div>';
  }
  function upcomingListHTML() {
    var list = (S.up || []).filter(function (l) { return l.net_ts && l.net_ts > Date.now() / 1000 - 3600; }).slice(0, 6);
    if (!list.length) return '';
    var h = '<div class="sm-sec"><div class="sm-sh">📅 ' + esc(L('Siguientes', 'Coming up')) + '</div>';
    list.forEach(function (l) {
      h += '<div class="sm-row" data-act="launch" data-id="' + esc(l.id) + '"><span class="d">' + esc(fmtDate(l.net_ts)) + '<br>' + esc(new Date(l.net_ts * 1000).toISOString().slice(11, 16)) + '</span>' +
        '<span class="t">' + esc(rocketName(l) + ' · ' + missionName(l)) + '<small>' + esc(provName(l) + (padLoc(l) ? ' · ' + padLoc(l) : '')) + ((l.graph || []).length ? ' · ◆ ' + l.graph.length : '') + '</small></span>' + stTag(l) + '</div>';
    });
    return h + '</div>';
  }
  function renderSituation() {
    var el = $('sm-right'); if (!el) return;
    var asOf = S.upSrc && S.upSrc.as_of ? fmtIso(S.upSrc.as_of) : '';
    el.innerHTML = '<div class="sm-ph"><span class="grab"></span>🛰 ' + esc(L('Situación espacial', 'Space situation')) +
      '<span style="margin-left:auto;font-weight:600;letter-spacing:0;text-transform:none;color:#5E6884;font-size:9.5px">' + esc(asOf) + '</span>' +
      '<span class="x" data-act="reload" title="' + esc(L('Actualizar', 'Refresh')) + '" style="margin-left:4px">⟳</span><span class="x" data-act="collapse" data-side="right" title="' + esc(L('Ocultar', 'Hide')) + '" style="margin-left:0">—</span></div>' +
      '<div class="sm-pb">' + heroHTML() + kpisHTML() + providersHTML() + upcomingListHTML() + constellationsHTML() + companiesHTML() + exposureHTML() +
      '<div class="sm-note">' + esc(L('Fuentes: Launch Library 2 (The Space Devs), CelesTrak, tu grafo Khipus. Análisis informativo; no es asesoría financiera.', 'Sources: Launch Library 2 (The Space Devs), CelesTrak, your Khipus graph. Informational analysis; not financial advice.')) + '</div></div>';
  }

  /* ── panel derecho: detalle ────────────────────────────────────────── */
  function detailHead(tag, color) {
    return '<div class="sm-ph"><span class="grab"></span><span class="sm-back" data-act="back">← ' + esc(L('Situación espacial', 'Space situation')) + '</span>' +
      '<span class="x" data-act="collapse" data-side="right" title="' + esc(L('Ocultar', 'Hide')) + '">—</span></div><div class="sm-pb">' +
      (tag ? '<span class="sm-tag" style="color:' + color + ';border-color:' + color + '66;background:' + color + '14">' + esc(tag) + '</span>' : '');
  }
  function coRow(g) {
    var nrs = nrsOf(g.id, g.nrs), m = mcap(g.id);
    return '<div class="sm-co"><span class="nm" data-act="co" data-id="' + esc(g.id) + '">' + esc(g.label) +
      '<span class="rl">' + esc(LL(ROLE[g.role]) + (g.method === 'mission_keyword' && g.matched ? ' · "' + g.matched + '"' : '')) + '</span></span>' +
      (m ? '<span class="ds">' + (m.live ? '<span style="color:#2BE38B">●</span> ' : '') + esc(fmtCap(m.v)) + '</span>' : (g.ticker ? '<span class="ds">' + esc(g.ticker) + '</span>' : '')) +
      '<span class="nr" style="color:' + nrsColor(nrs == null ? 50 : nrs) + '" title="NRS">' + (nrs == null ? '—' : nrs) + '</span>' +
      '<button class="sm-mini" data-act="xray" data-id="' + esc(g.id) + '" title="X-Ray">🔬</button>' +
      '<button class="sm-mini" data-act="map" data-id="' + esc(g.id) + '" title="' + esc(L('Ver en el mapa', 'View on map')) + '">🗺</button></div>';
  }
  function launchDetailHTML(l) {
    var past = l._w === 'previous', k = (l.status && l.status.kind) || 'other';
    var h = detailHead((past ? '✓ ' + L('LANZAMIENTO RECIENTE', 'RECENT LAUNCH') : '🚀 ' + L('PRÓXIMO LANZAMIENTO', 'UPCOMING LAUNCH')), past ? ST_C[k] : '#FFD166');
    h += ' ' + stTag(l);
    if (l.webcast_live) h += ' <span class="sm-tag" style="color:#FF4D6A;border-color:#FF4D6A66;background:#FF4D6A14">● ' + esc(L('WEBCAST EN VIVO', 'LIVE WEBCAST')) + '</span>';
    h += '<div class="sm-h1">' + esc(missionName(l)) + '</div>';
    h += '<div class="sm-meta">' + esc(provName(l)) + ((l.provider && l.provider.type) ? ' · ' + esc(l.provider.type) : '') + '<br>🚀 ' + esc((l.rocket && (l.rocket.full_name || l.rocket.name)) || '?') + '</div>';
    if (!past) h += '<div style="margin-top:8px"><span class="sm-cdx sm-cd" style="font-size:24px" data-id="' + esc(l.id) + '">' + esc(countdown(l).t) + '</span>' + chip('sm_countdown') + '</div>';
    var p = l.pad || {};
    h += '<div class="sm-meta" style="margin-top:6px">📍 ' + esc((p.name || '?') + (p.location ? ' — ' + p.location : '')) +
      (hasLL(l) ? ' <span style="font-family:JetBrains Mono,monospace;color:#6F7B98">(' + p.lat.toFixed(2) + '°, ' + p.lon.toFixed(2) + '°)</span>' : '<br><span style="color:#FFD27A">' + esc(L('La fuente no da coordenadas: no se dibuja en el globo.', 'The source gives no coordinates: not drawn on the globe.')) + '</span>') + '</div>';
    var kv = [
      [L('Fecha (NET)', 'Date (NET)'), fmtDate(l.net_ts, true), true],
      [L('Ventana', 'Window'), l.window_start ? (fmtIso(l.window_start).slice(11, 16) + '–' + (l.window_end ? fmtIso(l.window_end).slice(11, 16) : '?') + ' UTC') : '—', true],
      [L('Órbita', 'Orbit'), (l.mission && l.mission.orbit && (l.mission.orbit.name || l.mission.orbit.abbrev)) || '—'],
      [L('Tipo de misión', 'Mission type'), (l.mission && l.mission.type) || '—'],
      [L('Precisión', 'Precision'), l.net_precision ? (function () { var pk = Object.keys(PREC).filter(function (x) { return l.net_precision.indexOf(x) === 0; })[0]; return pk ? LL(PREC[pk]) : l.net_precision; })() : '—'],
      [L('Prob. clima OK', 'Weather go prob.'), l.probability != null && l.probability >= 0 ? l.probability + '%' : '—', true],
    ];
    h += '<div class="sm-kv">' + kv.map(function (x) { return '<div><div class="k">' + esc(x[0]) + '</div><div class="v' + (x[2] ? ' mono' : '') + '" title="' + esc(x[1]) + '">' + esc(x[1]) + '</div></div>'; }).join('') + '</div>';
    if (l.status && l.status.description) h += '<div class="sm-meta" style="margin-top:8px">' + esc(l.status.description) + '</div>';
    if (l.holdreason) h += '<div class="sm-meta" style="margin-top:6px;color:#FFD27A">⏸ ' + esc(l.holdreason) + '</div>';
    if (l.failreason) h += '<div class="sm-meta" style="margin-top:6px;color:#FF8FA3">✕ ' + esc(l.failreason) + '</div>';
    var acts = '';
    (l.vid_urls || []).slice(0, 2).forEach(function (v, i) {
      var u = safeUrl(v.url); if (!u) return;
      acts += '<a class="sm-act' + (l.webcast_live && i === 0 ? ' live' : '') + '" href="' + esc(u) + '" target="_blank" rel="noopener noreferrer">▶ ' + esc(i === 0 ? L('Ver webcast', 'Watch webcast') : (v.source || L('Otro stream', 'Other stream'))) + '</a>';
    });
    if (hasLL(l)) acts += '<button class="sm-act ghost" data-act="focuspad" data-id="' + esc(l.id) + '">🌍 ' + esc(L('Enfocar plataforma', 'Focus pad')) + '</button>';
    if (acts) h += '<div class="sm-acts">' + acts + '</div>';
    if (!(l.vid_urls || []).length) h += '<div class="sm-note">' + esc(L('La fuente aún no publica enlace de webcast para este lanzamiento.', 'The source has not published a webcast link for this launch yet.')) + '</div>';
    if (l.mission && l.mission.description) h += '<div class="sm-sec"><div class="sm-sh">🎯 ' + esc(L('Misión', 'Mission')) + '</div><div class="sm-meta" style="color:#C7D0EA">' + esc(l.mission.description) + '</div></div>';
    h += '<div class="sm-sec"><div class="sm-sh">◆ ' + esc(L('Empresas de tu grafo', 'Companies in your graph')) + chip('sm_graph_match') + '</div>';
    if ((l.graph || []).length) l.graph.forEach(function (g) { h += coRow(g); });
    else h += '<div class="sm-meta">' + esc(L('Ninguna empresa del grafo identificada (proveedor/cliente/carga). Agencias públicas y empresas fuera del grafo no aparecen.', 'No graph company identified (provider/customer/payload). Public agencies and companies outside the graph do not appear.')) + '</div>';
    h += '</div>';
    var ag = (l.mission && l.mission.agencies) || [];
    if (ag.length) h += '<div class="sm-meta" style="margin-top:6px">' + esc(L('Agencias/clientes según la fuente: ', 'Agencies/customers per the source: ') + ag.map(function (a) { return a.name; }).join(' · ')) + '</div>';
    var img = safeUrl(l.image);
    if (img) h += '<img class="sm-img" loading="lazy" referrerpolicy="no-referrer" alt="" src="' + esc(img) + '" onerror="this.remove()">';
    (l.info_urls || []).slice(0, 2).forEach(function (u) { var s = safeUrl(u.url); if (s) h += '<a class="sm-link" href="' + esc(s) + '" target="_blank" rel="noopener noreferrer">↗ ' + esc(u.title || s) + '</a>'; });
    h += '<div class="sm-note">' + esc(L('Fuente: Launch Library 2 (The Space Devs)', 'Source: Launch Library 2 (The Space Devs)')) + (S[past ? 'prevSrc' : 'upSrc'] && S[past ? 'prevSrc' : 'upSrc'].stale ? ' · ⚠ ' + esc(L('datos de ', 'data from ') + fmtIso(S[past ? 'prevSrc' : 'upSrc'].as_of)) : '') + '</div>';
    return h + '</div>';
  }
  function padDetailHTML(a) {
    var h = detailHead('⬢ ' + L('PLATAFORMA DE LANZAMIENTO', 'LAUNCH PAD'), '#00E0FF');
    h += '<div class="sm-h1">' + esc(a.name || '?') + '</div><div class="sm-meta">📍 ' + esc(a.location || '') + ' <span style="font-family:JetBrains Mono,monospace;color:#6F7B98">(' + a.lat.toFixed(2) + '°, ' + a.lon.toFixed(2) + '°)</span></div>';
    h += '<div class="sm-sec"><div class="sm-sh">🚀 ' + esc(L('Próximos desde aquí', 'Upcoming from here')) + '<span class="r">' + a.up.length + '</span></div>';
    if (!a.up.length) h += '<div class="sm-meta">' + esc(L('Ninguno en los datos cargados.', 'None in the loaded data.')) + '</div>';
    a.up.slice(0, 8).forEach(function (l) {
      h += '<div class="sm-row" data-act="launch" data-id="' + esc(l.id) + '"><span class="d">' + esc(fmtDate(l.net_ts)) + '</span><span class="t">' + esc(rocketName(l) + ' · ' + missionName(l)) + '<small class="sm-cd" data-id="' + esc(l.id) + '">' + esc(countdown(l).t) + '</small></span>' + stTag(l) + '</div>';
    });
    h += '</div><div class="sm-sec"><div class="sm-sh">✓ ' + esc(L('Recientes (30 d)', 'Recent (30 d)')) + '<span class="r">' + a.rec.length + '</span></div>';
    if (!a.rec.length) h += '<div class="sm-meta">' + esc(L('Ninguno en los últimos 30 días (según los datos cargados).', 'None in the last 30 days (per the loaded data).')) + '</div>';
    a.rec.slice(0, 6).forEach(function (l) {
      h += '<div class="sm-row" data-act="launch" data-id="' + esc(l.id) + '"><span class="d">' + esc(fmtDate(l.net_ts)) + '</span><span class="t">' + esc(rocketName(l) + ' · ' + missionName(l)) + '<small>' + esc(provName(l)) + '</small></span>' + stTag(l) + '</div>';
    });
    return h + '</div></div>';
  }
  function satDetailHTML(d) {
    var h = detailHead('🛰 ' + L('SATÉLITE · TELEMETRÍA', 'SATELLITE · TELEMETRY'), d.color || '#9bd1ff');
    h += '<div class="sm-h1">' + esc(d.name || L('Satélite', 'Satellite')) + '</div><div class="sm-meta"><span style="color:' + esc(d.color || '#9bd1ff') + '">●</span> ' + esc(d.constellation === 'Estaciones (ISS/CSS)' ? L('Estaciones (ISS/CSS)', 'Stations (ISS/CSS)') : d.constellation || '') + '</div>';
    h += '<div class="sm-kv" id="sm-tel">' + telHTML(d) + '</div>';
    h += '<div class="sm-note">' + esc(d.modeled ? L('⚠ Posición MODELADA (sin SGP4 o datos de referencia): no es la posición real.', '⚠ MODELED position (no SGP4 or reference data): not the real position.')
      : S.tle && S.tle.source === 'fallback' ? L('⚠ Órbita de referencia (CelesTrak no responde): no es la posición real.', '⚠ Reference orbit (CelesTrak unreachable): not the real position.')
        : L('Posición calculada en tu navegador con SGP4 a partir de los elementos orbitales de CelesTrak; se actualiza cada ~1 s.', 'Position computed in your browser with SGP4 from CelesTrak orbital elements; updates every ~1 s.')) + chip('sm_altitude') + '</div>';
    var node = d.node && (window.NODE_BY_ID || {})[d.node];
    if (node) h += '<div class="sm-sec"><div class="sm-sh">◆ ' + esc(L('Operador en tu grafo', 'Operator in your graph')) + '</div>' + coRow({ id: node.id, label: node.label, role: 'payload', method: 'constellation' }).replace(esc(LL(ROLE.payload)), esc(L('Operador de la constelación', 'Constellation operator'))) + '</div>';
    return h + '</div>';
  }
  function telHTML(d) {
    var c = function (k, v) { return '<div><div class="k">' + esc(k) + '</div><div class="v mono">' + esc(v) + '</div></div>'; };
    return c(L('Altitud', 'Altitude'), d.altKm != null ? Math.round(d.altKm).toLocaleString(en() ? 'en-US' : 'es-ES') + ' km' : '—') + c(L('Velocidad', 'Speed'), d.vel != null ? d.vel.toFixed(2) + ' km/s' : '—') +
      c(L('Latitud', 'Latitude'), d.lat != null ? d.lat.toFixed(2) + '°' : '—') + c(L('Longitud', 'Longitude'), d.lon != null ? d.lon.toFixed(2) + '°' : '—');
  }
  function companyDetailHTML(n) {
    var nrs = nrsOf(n.id), m = mcap(n.id), chg = dayChg(n);
    var h = detailHead('🏢 ' + L('EMPRESA DEL GRAFO', 'GRAPH COMPANY'), '#34d399');
    h += '<div class="sm-h1">' + esc(n.label) + '</div><div class="sm-meta">' + esc((n.mkt || L('privada', 'private')) + (n.cat ? ' · ' + n.cat : '')) + '</div>';
    h += '<div class="sm-kv"><div><div class="k">NRS</div><div class="v mono" style="color:' + nrsColor(nrs == null ? 50 : nrs) + '">' + (nrs == null ? '—' : nrs) + '</div></div>' +
      '<div><div class="k">' + esc(L('Capitalización', 'Market cap')) + '</div><div class="v mono">' + (m ? (m.live ? '<span style="color:#2BE38B">●</span> ' : '') + esc(fmtCap(m.v)) : '—') + '</div></div>' +
      (chg != null ? '<div><div class="k">' + esc(L('Día', 'Day')) + '</div><div class="v mono" style="color:' + (chg >= 0 ? '#2BE38B' : '#FF4D6A') + '">' + (chg >= 0 ? '+' : '') + chg.toFixed(2) + '%</div></div>' : '') + '</div>';
    if (m && !m.live) h += '<div class="sm-note">' + esc(L('Capitalización/valuación del catálogo (no en vivo).', 'Catalog market cap/valuation (not live).')) + '</div>';
    h += '<div class="sm-acts"><button class="sm-act" data-act="xray" data-id="' + esc(n.id) + '">🔬 X-Ray</button><button class="sm-act ghost" data-act="map" data-id="' + esc(n.id) + '">🗺 ' + esc(L('Ver en el mapa', 'View on map')) + '</button></div>';
    var mine = Object.keys(S.byId).map(function (k) { return S.byId[k]; }).filter(function (l) { return (l.graph || []).some(function (g) { return g.id === n.id; }); })
      .sort(function (a, b) { return (a.net_ts || 0) - (b.net_ts || 0); });
    h += '<div class="sm-sec"><div class="sm-sh">🚀 ' + esc(L('Lanzamientos donde participa', 'Launches it is involved in')) + chip('sm_graph_match') + '<span class="r">' + mine.length + '</span></div>';
    if (!mine.length) h += '<div class="sm-meta">' + esc(L('Ninguno en los datos cargados.', 'None in the loaded data.')) + '</div>';
    mine.slice(0, 10).forEach(function (l) {
      var g = (l.graph || []).filter(function (x) { return x.id === n.id; })[0];
      h += '<div class="sm-row" data-act="launch" data-id="' + esc(l.id) + '"><span class="d">' + esc(fmtDate(l.net_ts)) + '</span><span class="t">' + esc(rocketName(l) + ' · ' + missionName(l)) + '<small>' + esc(g ? LL(ROLE[g.role]) : '') + '</small></span>' + stTag(l) + '</div>';
    });
    return h + '</div></div>';
  }
  function renderDetail() {
    var el = $('sm-right'); if (!el || !S.sel) return;
    var s = S.sel;
    el.innerHTML = s.kind === 'launch' ? launchDetailHTML(s.data) : s.kind === 'pad' ? padDetailHTML(s.data) : s.kind === 'sat' ? satDetailHTML(s.data) : companyDetailHTML(s.data);
  }
  function renderRight() { if (S.sel) renderDetail(); else renderSituation(); }

  /* ── selección ─────────────────────────────────────────────────────── */
  function openRight() {
    S.collapsed.right = false; applyCollapse();
    if (S.narrow) openSheet('right');
  }
  function selectLaunch(l, opts) {
    opts = opts || {};
    if (!l) return;
    S.sel = { kind: 'launch', data: l };
    if (l._w === 'previous' && S.tlMode !== 'previous') { S.tlMode = 'previous'; renderTimeline(); }
    else if (l._w === 'upcoming' && S.tlMode !== 'upcoming') { S.tlMode = 'upcoming'; renderTimeline(); }
    else markTimeline();
    drawLaunches();
    if (S.globe && hasLL(l) && opts.focus !== false) S.globe.focusOn(l.pad.lat, l.pad.lon, { dist: Math.round((S.globe._fitDist || 300) * (S.narrow ? 0.9 : 0.78)) });
    openRight();
    renderDetail();
  }
  function markTimeline() {
    var t = $('sm-tlt'); if (!t) return;
    var sel = S.sel && S.sel.kind === 'launch' ? S.sel.data.id : null;
    var ms = t.querySelectorAll('.sm-mk');
    for (var i = 0; i < ms.length; i++) {
      var on = ms[i].getAttribute('data-id') === sel;
      ms[i].classList.toggle('sel', on);
      if (on) { var w = $('sm-tlw'); if (w && (ms[i].offsetLeft < w.scrollLeft || ms[i].offsetLeft > w.scrollLeft + w.clientWidth - 60)) w.scrollLeft = Math.max(0, ms[i].offsetLeft - w.clientWidth / 2); }
    }
  }
  function select(kind, data, opts) {
    opts = opts || {};
    if (!data) return;
    if (kind === 'launch') return selectLaunch(data, opts);
    S.sel = { kind: kind, data: data };
    if (S.globe) {
      if (kind === 'pad') S.globe.focusOn(data.lat, data.lon, { dist: Math.round((S.globe._fitDist || 300) * 0.8) });
      else if (kind === 'company' && window.GeoCoords && opts.focus !== false) { var g = window.GeoCoords.geoCoord(data); S.globe.focusOn(g.lat, g.lng); }
    }
    if (kind !== 'sat' && S.globe) S.globe._drop('satsel');
    markTimeline(); drawLaunches();
    openRight();
    renderDetail();
  }
  function back() {
    S.sel = null;
    if (S.globe) S.globe._drop('satsel');
    markTimeline(); drawLaunches();
    renderSituation();
  }
  function refreshSat() {
    if (!S.sel || S.sel.kind !== 'sat' || !S.globe) return;
    var d = S.sel.data, G = S.globe, layer = G.layers[d._li], rec = layer && layer.satrecs[d._i];
    if (!rec || !rec.tel) return;
    d.lat = rec.tel.lat; d.lon = rec.tel.lon; d.altKm = rec.tel.altKm; d.vel = rec.tel.vel;
    var el = $('sm-tel'); if (el) el.innerHTML = telHTML(d);
    G.setPoints('satsel', [{ lat: d.lat, lon: d.lon, color: '#FFFFFF', size: 14, pulse: true, alt: altScale(d.altKm) / EARTH_KM }], { shape: 3, pickable: false, renderOrder: 9 });
  }

  /* ── dibujo en el globo ────────────────────────────────────────────── */
  function drawLaunches() {
    var G = S.globe; if (!G) return;
    var now = Date.now() / 1000;
    var sel = S.sel && S.sel.kind === 'launch' ? S.sel.data : null;
    var focus = sel || nextLaunch();
    var up = (S.up || []).filter(function (l) { return hasLL(l) && l.net_ts && l.net_ts >= now - 3600 && ['success', 'failure', 'partial'].indexOf(l.status.kind) < 0; })
      .sort(function (a, b) { return a.net_ts - b.net_ts; }).slice(0, 16);
    var others = up.filter(function (l) { return l !== focus; });
    G.setFlowLines('arcs', others.map(function (l) { var c = OC[orbitClass(l)]; return G.ascentPath(l.pad.lat, l.pad.lon, heading(l), c.dr, c.alt); }),
      { colors: others.map(function (l) { return ST_C[l.status.kind] || ST_C.other; }), normalized: true, reverse: true, dash: 1, speed: 0.22, opacity: 0.5 });
    if (focus && hasLL(focus)) {
      var c = OC[orbitClass(focus)], hd = heading(focus);
      G.setFlowLines('arc_focus', [G.ascentPath(focus.pad.lat, focus.pad.lon, hd, c.dr, c.alt, 64)], { color: 0xFFD166, normalized: true, reverse: true, dash: 1, speed: 0.4, opacity: 0.95, renderOrder: 5 });
      G.setFlowLines('orbit', [G.orbitPath(focus.pad.lat, focus.pad.lon, hd, c.alt)], { color: 0xFFD166, dash: 1 / 40, speed: 0.15, opacity: 0.32 });
      G.setRings('focus_ring', [{ lat: focus.pad.lat, lon: focus.pad.lon, color: '#FFD166', scale: 1.15 }], { pickable: false });
      var e = G.ascentPath(focus.pad.lat, focus.pad.lon, hd, c.dr, c.alt);
      var tip = e[e.length - 1].clone().normalize();
      var tlat = Math.asin(tip.y) * 180 / Math.PI;
      // punto de inserción (fin del arco) — convierte el vector a lat/lon con la inversa de latLng
      var tlon = Math.atan2(tip.z, -tip.x) * 180 / Math.PI - 180; if (tlon < -180) tlon += 360;
      G.setPoints('arc_tip', [{ lat: tlat, lon: tlon, color: '#FFD166', size: 9, pulse: true, alt: c.alt + 0.008 }], { pickable: false, renderOrder: 8 });
    } else { G._drop('arc_focus'); G._drop('orbit'); G._drop('focus_ring'); G._drop('arc_tip'); }
    // plataformas: halo + núcleo (laten las de lanzamiento en < 48 h)
    var pads = padsAgg();
    G.setPoints('pads_glow', pads.map(function (a) { return { lat: a.lat, lon: a.lon, color: a.up.length ? (a.week ? '#00E0FF' : '#4A7BFF') : '#5E6884', size: a.up.length ? 16 + Math.min(12, a.up.length * 2.2) : 10 }; }),
      { shape: 2, pickable: false, opacity: 0.5, renderOrder: 4, alt: 0.004 });
    G.setPoints('pads', pads.map(function (a) { return { lat: a.lat, lon: a.lon, color: a.up.length ? (a.week ? '#9EF6FF' : '#8FB0FF') : '#9BA6C4', size: a.up.length ? 5.5 : 4, pulse: a.soon }; }),
      { hitPx: 11, renderOrder: 7, alt: 0.006 });
    G.gl.pads.items = pads;
    var lab = pads.filter(function (a) { return a.up.length; }).sort(function (a, b) { return b.up.length - a.up.length; }).slice(0, S.narrow ? 4 : 7);
    G.setLabels('pad_labels', lab.map(function (a) { return { lat: a.lat + 3.2, lon: a.lon, text: String(a.location || a.name || '').split(',')[0] + ' · ' + a.up.length, color: '#9EF6FF' }; }), { px: 24, w: 20, alt: 0.03 });
    var rec = recentList().filter(hasLL);
    G.setPoints('recent', rec.map(function (l) { return { lat: l.pad.lat, lon: l.pad.lon, color: ST_C[l.status.kind] || ST_C.other, size: 11 }; }), { shape: 3, pickable: false, opacity: 0.8, renderOrder: 6, alt: 0.008 });
    applyVis();
  }
  function drawCompanies() {
    var G = S.globe; if (!G || !window.GeoCoords) return;
    var NS = spaceNodes();
    G.setPoints('companies', NS.map(function (n) { var g = window.GeoCoords.geoCoord(n); var v = nrsOf(n.id); return { lat: g.lat, lon: g.lng, color: nrsColor(v == null ? 50 : v), size: 6 }; }),
      { shape: 1, hitPx: 9, additive: false, renderOrder: 7 });
    G.gl.companies.items = NS;
    G.setLayerVisible('companies', S.vis.companies);
  }
  function drawShells() {
    var G = S.globe; if (!G) return;
    var sh = [[550, 'LEO · 550 km'], [20200, 'MEO · 20.200 km'], [35786, 'GEO · 35.786 km']];
    G.setFlowLines('shells', sh.map(function (s) { return G.orbitPath(0, -30, 90, altScale(s[0]) / EARTH_KM, 200); }), { color: 0x7C87A3, flow: false, opacity: 0.28 });
    G.setLabels('shell_labels', sh.map(function (s) { return { lat: 1.5, lon: -30, text: en() ? s[1].replace('.', ',') : s[1], color: '#9BA6C4' }; }), { px: 22, w: 18, alt: 0 });
    // setLabels coloca a una altura fija: se recolocan a la altura de cada capa
    var L2 = G.gl.shell_labels;
    if (L2 && L2.obj) L2.obj.children.forEach(function (spr, i) { spr.position.normalize().multiplyScalar(100 * (1 + altScale(sh[i][0]) / EARTH_KM) + 4); });
    G.setLayerVisible('shells', S.vis.shells); G.setLayerVisible('shell_labels', S.vis.shells);
  }
  function applyVis() {
    var G = S.globe; if (!G) return;
    ['arcs', 'arc_focus', 'arc_tip'].forEach(function (id) { G.setLayerVisible(id, S.vis.upcoming); });
    G.setLayerVisible('recent', S.vis.recent);
    ['pads', 'pads_glow', 'pad_labels', 'focus_ring'].forEach(function (id) { G.setLayerVisible(id, S.vis.pads); });
    G.setLayerVisible('orbit', S.vis.orbit);
    G.setLayerVisible('companies', S.vis.companies);
    G.setLayerVisible('shells', S.vis.shells); G.setLayerVisible('shell_labels', S.vis.shells);
    (G.layers || []).forEach(function (l) { G.setSatVisible(l.name, S.satVis[l.name] !== false); });
  }

  /* ── carga de datos ────────────────────────────────────────────────── */
  function load(force) {
    if (S.loading && !force) return;
    S.loading = true; S.lastLoad = Date.now();
    var a = getJSON('/api/space2/launches?window=upcoming&limit=60').then(function (d) { S.up = d.launches || []; S.upSrc = d.source || null; S.upErr = null; })
      .catch(function (e) { S.upErr = e.message || 'error'; });
    var b = getJSON('/api/space2/launches?window=previous&limit=40').then(function (d) { S.prev = d.launches || []; S.prevSrc = d.source || null; S.prevErr = null; })
      .catch(function (e) { S.prevErr = e.message || 'error'; });
    Promise.all([a, b]).then(function () {
      S.loading = false;
      indexLaunches();
      if (S.sel && S.sel.kind === 'launch' && S.byId[S.sel.data.id]) S.sel.data = S.byId[S.sel.data.id];
      drawLaunches(); renderLayers(); renderTop(); renderTimeline(); renderRight();
      if (S.pendingFocus) { var id = S.pendingFocus; S.pendingFocus = null; focusLaunch(id); }
      else if (!S.sel && S.globe && !S._focused) { var n = nextLaunch(); if (n && hasLL(n)) { S._focused = true; S.globe.focusOn(n.pad.lat, n.pad.lon, { duration: 1400 }); } }
      var pend = (S.upSrc && (S.upSrc.pending || S.upSrc.error_code === 'refreshing')) || (S.prevSrc && (S.prevSrc.pending || S.prevSrc.error_code === 'refreshing'));
      if (pend && (S._polls = (S._polls || 0) + 1) < 5) later(function () { load(); }, 12000);
      return getJSON('/api/space2/summary').then(function (d) { S.summary = d; S.sumErr = null; }).catch(function (e) { S.sumErr = e.message || 'error'; })
        .then(function () { if (!S.sel) renderSituation(); });
    });
  }
  function loadTLE() {
    if (S.tle) { if (S.globe && !S.globe.layers.length) { S.globe.loadSatellites(S.tle, { monitor: true, altScale: altScale, pick: true }); applyVis(); } return; }
    getJSON('/api/space/tle').then(function (d) {
      if (!d || !Array.isArray(d.constellations)) throw new Error(L('respuesta inesperada', 'unexpected response'));
      S.tle = d; S.tleErr = null;
      if (S.globe) { S.globe.loadSatellites(d, { monitor: true, altScale: altScale, pick: true }); applyVis(); }
    }).catch(function (e) { S.tleErr = e.message || 'error'; })
      .then(function () { renderLayers(); if (!S.sel) renderSituation(); });
  }
  function later(fn, ms) { var t = setTimeout(fn, ms); S.timers.push(t); return t; }

  /* ── colapsar / hojas ──────────────────────────────────────────────── */
  function applyCollapse() {
    var l = $('sm-left'), r = $('sm-right'), rl = $('sm-reopen-l'), rr = $('sm-reopen-r'), tl = $('sm-tl');
    if (!l || !r) return;
    if (S.narrow) { l.classList.remove('hid'); r.classList.remove('hid'); if (tl) { tl.style.left = ''; tl.style.right = ''; } return; }
    l.classList.toggle('hid', S.collapsed.left); r.classList.toggle('hid', S.collapsed.right);
    if (rl) rl.style.display = S.collapsed.left ? '' : 'none';
    if (rr) rr.style.display = S.collapsed.right ? '' : 'none';
    if (tl) { tl.style.left = S.collapsed.left ? '10px' : ''; tl.style.right = S.collapsed.right ? '10px' : ''; }
    later(layoutTimeline, 30);
  }
  function openSheet(side) {
    S.sheet = side;
    var l = $('sm-left'), r = $('sm-right');
    if (l) l.classList.toggle('open', side === 'left');
    if (r) r.classList.toggle('open', side === 'right');
    if (S.globe && S.globe.setViewShift) S.globe.setViewShift(S.narrow && side ? 0.3 : 0);
  }
  function checkNarrow() {
    var w = S.root ? S.root.clientWidth : 0;
    if (!w) return;
    var nr = w < 760;
    if (nr !== S.narrow) {
      S.narrow = nr;
      var sm = $('sm'); if (sm) sm.classList.toggle('nr', nr);
      if (!nr) openSheet(null);
      applyCollapse(); renderMbar();
      if (S.globe) drawLaunches();
    }
    layoutTimeline();
  }
  function renderMbar() {
    var m = $('sm-mbar'); if (!m) return;
    m.innerHTML = '<button class="sm-btn" data-act="sheet" data-side="left">☰ ' + esc(L('Capas', 'Layers')) + '</button>' +
      '<button class="sm-btn" data-act="zoom" data-f="0.8">＋</button><button class="sm-btn" data-act="zoom" data-f="1.25">－</button>' +
      '<button class="sm-btn" data-act="sheet" data-side="right">◉ ' + esc(L('Situación', 'Situation')) + '</button>';
  }

  /* ── eventos de UI ─────────────────────────────────────────────────── */
  function onClick(e) {
    var a = e.target.closest('[data-act]');
    if (!a || !S.root || !S.root.contains(a)) return;
    var act = a.getAttribute('data-act');
    if (act === 'toggle') {
      var id = a.getAttribute('data-layer'); S.vis[id] = !S.vis[id]; lsSet('kh_sm_layers', S.vis); applyVis(); renderLayers();
    } else if (act === 'sat') {
      var nm = a.getAttribute('data-name'); S.satVis[nm] = S.satVis[nm] === false; lsSet('kh_sm_sats', S.satVis); applyVis(); renderLayers();
    } else if (act === 'solo') {
      var only = a.getAttribute('data-name'), all = ((S.tle && S.tle.constellations) || []).map(function (c) { return c.name; });
      var already = all.every(function (n) { return (S.satVis[n] !== false) === (n === only); });
      all.forEach(function (n) { S.satVis[n] = already ? true : n === only; });
      lsSet('kh_sm_sats', S.satVis); applyVis(); renderLayers();
    } else if (act === 'launch') {
      var l = S.byId[a.getAttribute('data-id')]; if (l) selectLaunch(l, { focus: true });
    } else if (act === 'next') {
      var n = S.nextId && S.byId[S.nextId]; if (n) selectLaunch(n, { focus: true });
    } else if (act === 'focuspad') {
      var fl = S.byId[a.getAttribute('data-id')]; if (fl && hasLL(fl) && S.globe) { S.globe.focusOn(fl.pad.lat, fl.pad.lon, { dist: Math.round((S.globe._fitDist || 300) * 0.6) }); if (S.narrow) openSheet(null); }
    } else if (act === 'co') {
      var cn = (window.NODE_BY_ID || {})[a.getAttribute('data-id')]; if (cn) select('company', cn);
    } else if (act === 'xray') { xray(a.getAttribute('data-id')); }
    else if (act === 'map') { goMap(a.getAttribute('data-id')); }
    else if (act === 'back') { back(); }
    else if (act === 'tlmode') { var md = a.getAttribute('data-mode'); if (md !== S.tlMode) { S.tlMode = md; renderTimeline(); } }
    else if (act === 'step') { step(+a.getAttribute('data-d')); }
    else if (act === 'provwin') { S.provWin = a.getAttribute('data-w'); renderSituation(); }
    else if (act === 'morecos') { S.moreCos = !S.moreCos; renderSituation(); }
    else if (act === 'collapse') { var sd = a.getAttribute('data-side'); if (S.narrow) openSheet(null); else { S.collapsed[sd] = true; applyCollapse(); } }
    else if (act === 'reopen') { S.collapsed[a.getAttribute('data-side')] = false; applyCollapse(); }
    else if (act === 'sheet') { var sside = a.getAttribute('data-side'); openSheet(S.sheet === sside ? null : sside); }
    else if (act === 'zoom') { if (S.globe) S.globe.zoomBy(+a.getAttribute('data-f')); }
    else if (act === 'reset') { if (S.globe) S.globe.resetView(); }
    else if (act === 'reload') { load(true); }
  }
  function onGlobePick(hit) {
    if (!hit || !hit.data) return;
    if (hit.layer === 'pads') return select('pad', hit.data);
    if (hit.layer === 'companies') return select('company', hit.data, { focus: false });
    if (hit.layer === 'satellites') {
      var d = hit.data, G = S.globe;
      for (var li = 0; li < G.layers.length; li++) if (G.layers[li].name === d.constellation) { d._li = li; break; }
      d._i = hit.index;
      select('sat', d);
      refreshSat();
    }
  }
  function onGlobeHover(hit, x, y) {
    var tip = $('sm-tip'); if (!tip || !S.root) return;
    if (!hit || !hit.data) { tip.style.display = 'none'; return; }
    var d = hit.data, h;
    if (hit.layer === 'pads') {
      var n = d.up[0];
      h = '<b>⬢ ' + esc(d.name) + '</b><div class="m">' + esc(d.location || '') + '<br>' + esc(L(d.up.length + ' próximos · ' + d.rec.length + ' recientes', d.up.length + ' upcoming · ' + d.rec.length + ' recent')) +
        (n ? '<br>🚀 ' + esc(rocketName(n) + ' · ' + countdown(n).t) : '') + '</div>';
    } else if (hit.layer === 'companies') {
      var v = nrsOf(d.id);
      h = '<b>🏢 ' + esc(d.label) + '</b><div class="m">NRS <b style="color:' + nrsColor(v == null ? 50 : v) + '">' + (v == null ? '—' : v) + '</b> · ' + esc(L('clic = detalle', 'click = details')) + '</div>';
    } else if (hit.layer === 'satellites') {
      h = '<b>🛰 ' + esc(d.name) + '</b><div class="m"><span style="color:' + esc(d.color) + '">●</span> ' + esc(d.constellation) + (d.altKm != null ? ' · ' + Math.round(d.altKm) + ' km' : '') + '</div>';
    } else return;
    var r = S.root.getBoundingClientRect();
    tip.innerHTML = h; tip.style.display = 'block';
    tip.style.left = Math.max(6, Math.min(x - r.left + 14, r.width - 280)) + 'px';
    tip.style.top = Math.max(46, Math.min(y - r.top + 12, r.height - 90)) + 'px';
  }

  /* ── montaje ───────────────────────────────────────────────────────── */
  function initGlobe() {
    if (!window.THREE || !window.KhipuGlobe || !window.GeoCoords) {
      var w = $('sm');
      if (w) w.insertAdjacentHTML('beforeend', '<div class="sm-glnote">' + esc(L('El globo 3D necesita Three.js (revisa tu conexión). Los paneles y la línea de tiempo siguen funcionando.', 'The 3D globe needs Three.js (check your connection). The panels and timeline still work.')) + '</div>');
      return;
    }
    try {
      var G = new window.KhipuGlobe('sm-canvas', { layers: ['satellites'], look: 'monitor', fitR: 1.3, view: { lat: 24, lon: -70 } });
      G.init();
      G.setGraticule(30, { opacity: 0.1, color: 0x3a4d8a });
      G.onPick = onGlobePick;
      G.onHover = onGlobeHover;
      S.globe = G; window._smGlobe = G;
      drawShells(); drawCompanies();
      if (S.up || S.prev) drawLaunches();
      fetch(base() + '/vendor/world-110m.json').then(function (r) { if (!r.ok) throw new Error('topo'); return r.json(); })
        .then(function (tp) { if (S.globe === G) G.setBorders(tp, { color: 0x3b5fc4, opacity: 0.4 }); }).catch(function () {});
    } catch (e) { console.warn('[SpaceMonitor] globo:', e); }
  }

  function relabel() {
    var br = document.querySelector('#sm .sm-brand .bt');
    var rl = $('sm-reopen-l'), rr = $('sm-reopen-r');
    if (rl) rl.textContent = '☰ ' + L('Capas', 'Layers');
    if (rr) rr.textContent = '◉ ' + L('Situación', 'Situation');
    renderLayers(); renderTop(); renderTimeline(); renderRight(); renderMbar();
    if (S.globe) drawShells();
    return br;
  }

  function mount(container) {
    container = container || $('sp-root');
    if (!container) return;
    ensureStyles(); registerExplain();
    var pane = $('space-panel');
    if (pane && !(pane.closest && pane.closest('.bcp-embed'))) pane.style.minHeight = '';
    if (S.root && S.root === container && $('sm')) {
      renderLayers(); renderTop(); renderTimeline(); renderRight(); renderMbar(); checkNarrow();
      var tp = $('sm-tip'); if (tp) tp.style.display = 'none';
      if (S.globe) { S.globe.resume(); drawCompanies(); drawShells(); drawLaunches(); }
      if (Date.now() - S.lastLoad > 600000) load();
      return;
    }
    if (S.root) unmount();
    S.root = container;
    S.vis = Object.assign({}, S.vis, lsGet('kh_sm_layers', {}));
    var sv = lsGet('kh_sm_sats', {}); S.satVis = sv && typeof sv === 'object' ? sv : {};
    container.innerHTML = shell();
    renderLayers(); renderTop(); renderSituation(); renderMbar(); renderTimeline(); tick();
    container.addEventListener('click', onClick);
    S._onClick = onClick;
    bindTimeline();
    if (window.ResizeObserver) { S._ro = new ResizeObserver(checkNarrow); S._ro.observe(container); }
    // cambio de idioma: app.html fija <html lang> → re-etiquetar (regla bilingüe)
    if (window.MutationObserver) {
      S._mo = new MutationObserver(function () { if (S.root) relabel(); });
      S._mo.observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
    }
    checkNarrow();
    initGlobe();
    loadTLE();
    load(true);
    S.timers.push(setInterval(function () {
      if (document.hidden || !S.root || !S.root.offsetParent) return;
      tick();
      if (S.sel && S.sel.kind === 'sat') refreshSat();
    }, 1000));
    S.timers.push(setInterval(function () {
      if (document.hidden || !S.root || !S.root.offsetParent) return;
      renderTop(); load();
    }, 600000));
  }

  function unmount() {
    S.timers.forEach(function (t) { clearTimeout(t); clearInterval(t); });
    S.timers = [];
    try { if (S._ro) S._ro.disconnect(); } catch (e) {}
    try { if (S._mo) S._mo.disconnect(); } catch (e) {}
    (S._tlh || []).forEach(function (x) { try { x[2].removeEventListener(x[0], x[1]); } catch (e) {} });
    S._tlh = null;
    if (S.root && S._onClick) S.root.removeEventListener('click', S._onClick);
    if (S.globe) { try { S.globe.dispose(); } catch (e) {} }
    S.globe = null; window._smGlobe = null;
    if (S.root) S.root.innerHTML = '';
    S.root = null; S.sel = null; S.narrow = false; S.sheet = null; S._focused = false; S.scrub = null;
  }

  function open() {
    if (typeof window._surface === 'function') window._surface('tab', 'space');
    else if (typeof window.switchTab === 'function') window.switchTab('space');
    setTimeout(function () { mount(); }, 60);
  }

  function focusLaunch(id) {
    if (!S.root) { S.pendingFocus = id; open(); return; }
    var l = S.byId[id];
    if (!l) { S.pendingFocus = id; if (!S.loading) load(); return; }
    selectLaunch(l, { focus: true });
  }

  window.KhipuSpace = { mount: mount, unmount: unmount, focusLaunch: focusLaunch, open: open, state: S };
})();
