// engine/geo_coords.js — Coordenadas geográficas para los globos 3D (Khipu Finance)
// Los nodos NO traen lat/long: solo `country` (EEUU, Japon, "Estados Unidos
// (HQ Denver, CO)"…) y `loc`. Este módulo resuelve cada nodo a {lat,lng} de
// forma DETERMINISTA, y dice con qué PRECISIÓN lo hizo (regla del proyecto:
// no aparentar exactitud que no tenemos):
//   1) 'hq'      → sede o sitio principal curado a mano (empresas clave),
//   2) 'city'    → ciudad mencionada en el texto del país/loc ("Denver", "Pekín"),
//   3) 'hub'     → EE.UU. sin ciudad: hub tecnológico asignado por hash (APROX.),
//   4) 'country' → centro económico del país + jitter determinista (APROX.),
//   5) 'unknown' → país no reconocido → hub global (Singapur). NO es su ubicación.
// Lo usan engine/globe.js y engine/worldmonitor.js. El server tiene una réplica
// EXACTA en core/world.py (exposición de la cadena a eventos) — tests/test_world.py
// compara ambas implementaciones sobre los 949 nodos: si editas una tabla aquí,
// edítala también allá. Al final vive `window.KhipuCountries` (ISO-2 ↔ clave ↔ nombre
// ES/EN, gemela de core/countries.py; tabla GENERADA, ver abajo).

(function () {
  'use strict';

  // ── Centros representativos por país/región (lat, lng) ────────────────────
  // No son centroides geográficos puros: apuntan a la zona tecnológica/económica
  // relevante para que las empresas caigan donde el espectador las espera.
  const COUNTRY = {
    EEUU:        [37.77, -122.42],  // default → Bay Area (se reparte por hubs, ver US_HUBS)
    Japon:       [35.68, 139.69],   // Tokio
    Japan:       [35.68, 139.69],
    China:       [31.23, 121.47],   // Shanghái
    Taiwan:      [24.80, 120.97],   // Hsinchu (TSMC)
    Corea:       [37.57, 126.98],   // Seúl
    Alemania:    [51.05, 13.74],    // Dresde (Silicon Saxony)
    Francia:     [45.18, 5.72],     // Grenoble (microelectrónica)
    PaisesBajos: [51.41, 5.42],     // Veldhoven (ASML)
    ReinoUnido:  [51.51, -0.13],    // Londres
    Israel:      [32.08, 34.78],    // Tel Aviv
    India:       [12.97, 77.59],    // Bangalore
    Australia:   [-33.87, 151.21],  // Sídney
    Europa:      [50.11, 8.68],     // Frankfurt (centroide Europa occidental)
    RestoEuropa: [52.52, 13.40],    // Berlín
    RestoMundo:  [1.35, 103.82],    // Singapur (hub global)
    // ampliación multicapa (2026-08: energía, materiales, macro, logística…)
    Canada:      [45.50, -73.57],   // Montreal
    Finlandia:   [60.17, 24.94],    // Helsinki
    Noruega:     [59.91, 10.75],    // Oslo
    Chile:       [-33.45, -70.67],  // Santiago
    Rusia:       [55.76, 37.62],    // Moscú
    EAU:         [25.20, 55.27],    // Dubái
    Singapur:    [1.29, 103.85],
    HongKong:    [22.32, 114.17],
    Suiza:       [47.37, 8.54],     // Zúrich
    Dinamarca:   [55.68, 12.57],    // Copenhague
    Brasil:      [-23.55, -46.63],  // São Paulo
    Catar:       [25.29, 51.53],    // Doha
    Sudafrica:   [-26.20, 28.05],   // Johannesburgo
    Panama:      [8.98, -79.52],
    Irlanda:     [53.35, -6.26],    // Dublín
    Italia:      [45.46, 9.19],     // Milán
    Kazajistan:  [51.17, 71.45],    // Astaná
    Tailandia:   [13.76, 100.50],   // Bangkok
    Lituania:    [54.69, 25.28],    // Vilna
    Malasia:     [3.14, 101.69],    // Kuala Lumpur
    Argelia:     [36.75, 3.06],     // Argel
    Polonia:     [52.23, 21.01],    // Varsovia
    Indonesia:   [-6.21, 106.85],   // Yakarta
    Kuwait:      [29.38, 47.99],
    Espana:      [40.42, -3.70],    // Madrid
    Uganda:      [0.35, 32.58],     // Kampala
    Mexico:      [19.43, -99.13],   // CDMX
    Suecia:      [59.33, 18.07],    // Estocolmo
    Egipto:      [30.04, 31.24],    // El Cairo
    Belgica:     [50.85, 4.35],     // Bruselas
    Luxemburgo:  [49.61, 6.13],
    Ucrania:     [50.45, 30.52],    // Kiev
    Azerbaiyan:  [40.41, 49.87],    // Bakú
    Iran:        [35.69, 51.39],    // Teherán
    Argentina:   [-34.60, -58.38],
    NuevaZelanda:[-36.85, 174.76],  // Auckland
    ArabiaSaudita:[24.71, 46.68],   // Riad
    Turquia:     [41.01, 28.98],    // Estambul
    Vietnam:     [21.03, 105.85],   // Hanói
    Filipinas:   [14.60, 120.98],   // Manila
    Pakistan:    [24.86, 67.01],    // Karachi
    Nigeria:     [6.52, 3.38],      // Lagos
    Kenia:       [-1.29, 36.82],    // Nairobi
    Colombia:    [4.71, -74.07],    // Bogotá
    Peru:        [-12.05, -77.04],  // Lima
    Austria:     [48.21, 16.37],    // Viena
    Portugal:    [38.72, -9.14],    // Lisboa
    Grecia:      [37.98, 23.73],    // Atenas
    Chequia:     [50.08, 14.44],    // Praga
    Hungria:     [47.50, 19.04],    // Budapest
    Rumania:     [44.43, 26.10],    // Bucarest
  };

  // Texto normalizado (minúsculas, sin acentos ni puntuación) → clave de COUNTRY.
  const ALIAS = {
    'eeuu': 'EEUU', 'ee uu': 'EEUU', 'estados unidos': 'EEUU', 'united states': 'EEUU',
    'united states of america': 'EEUU', 'usa': 'EEUU', 'us': 'EEUU', 'u s': 'EEUU', 'u s a': 'EEUU',
    'japon': 'Japon', 'japan': 'Japon',
    'china': 'China', 'prc': 'China',
    'taiwan': 'Taiwan',
    'corea': 'Corea', 'corea del sur': 'Corea', 'south korea': 'Corea', 'korea': 'Corea', 'republic of korea': 'Corea',
    'alemania': 'Alemania', 'germany': 'Alemania',
    'francia': 'Francia', 'france': 'Francia',
    'paisesbajos': 'PaisesBajos', 'paises bajos': 'PaisesBajos', 'netherlands': 'PaisesBajos',
    'the netherlands': 'PaisesBajos', 'holanda': 'PaisesBajos',
    'reinounido': 'ReinoUnido', 'reino unido': 'ReinoUnido', 'united kingdom': 'ReinoUnido', 'uk': 'ReinoUnido',
    'gran bretana': 'ReinoUnido', 'great britain': 'ReinoUnido', 'england': 'ReinoUnido', 'inglaterra': 'ReinoUnido',
    'israel': 'Israel', 'india': 'India', 'australia': 'Australia',
    'europa': 'Europa', 'europe': 'Europa', 'eurozone': 'Europa', 'union europea': 'Europa', 'eu': 'Europa',
    'restoeuropa': 'RestoEuropa', 'restomundo': 'RestoMundo',
    'canada': 'Canada', 'finlandia': 'Finlandia', 'finland': 'Finlandia', 'noruega': 'Noruega', 'norway': 'Noruega',
    'chile': 'Chile', 'rusia': 'Rusia', 'russia': 'Rusia', 'russian federation': 'Rusia',
    'emiratos arabes unidos': 'EAU', 'united arab emirates': 'EAU', 'uae': 'EAU', 'eau': 'EAU', 'emiratos': 'EAU',
    'singapur': 'Singapur', 'singapore': 'Singapur', 'hong kong': 'HongKong',
    'suiza': 'Suiza', 'switzerland': 'Suiza', 'dinamarca': 'Dinamarca', 'denmark': 'Dinamarca',
    'brasil': 'Brasil', 'brazil': 'Brasil', 'catar': 'Catar', 'qatar': 'Catar',
    'sudafrica': 'Sudafrica', 'south africa': 'Sudafrica', 'panama': 'Panama',
    'irlanda': 'Irlanda', 'ireland': 'Irlanda', 'italia': 'Italia', 'italy': 'Italia',
    'kazajistan': 'Kazajistan', 'kazakhstan': 'Kazajistan', 'tailandia': 'Tailandia', 'thailand': 'Tailandia',
    'lituania': 'Lituania', 'lithuania': 'Lituania', 'malasia': 'Malasia', 'malaysia': 'Malasia',
    'argelia': 'Argelia', 'algeria': 'Argelia', 'polonia': 'Polonia', 'poland': 'Polonia',
    'indonesia': 'Indonesia', 'kuwait': 'Kuwait', 'espana': 'Espana', 'spain': 'Espana',
    'uganda': 'Uganda', 'mexico': 'Mexico', 'suecia': 'Suecia', 'sweden': 'Suecia',
    'egipto': 'Egipto', 'egypt': 'Egipto', 'belgica': 'Belgica', 'belgium': 'Belgica',
    'luxemburgo': 'Luxemburgo', 'luxembourg': 'Luxemburgo', 'ucrania': 'Ucrania', 'ukraine': 'Ucrania',
    'azerbaiyan': 'Azerbaiyan', 'azerbaijan': 'Azerbaiyan', 'iran': 'Iran', 'argentina': 'Argentina',
    'nueva zelanda': 'NuevaZelanda', 'new zealand': 'NuevaZelanda', 'nz': 'NuevaZelanda',
    'arabia saudita': 'ArabiaSaudita', 'saudi arabia': 'ArabiaSaudita',
    'turquia': 'Turquia', 'turkey': 'Turquia', 'turkiye': 'Turquia', 'vietnam': 'Vietnam', 'viet nam': 'Vietnam',
    'filipinas': 'Filipinas', 'philippines': 'Filipinas', 'pakistan': 'Pakistan', 'nigeria': 'Nigeria',
    'kenia': 'Kenia', 'kenya': 'Kenia', 'colombia': 'Colombia', 'peru': 'Peru', 'austria': 'Austria',
    'portugal': 'Portugal', 'grecia': 'Grecia', 'greece': 'Grecia', 'chequia': 'Chequia',
    'czech republic': 'Chequia', 'czechia': 'Chequia', 'hungria': 'Hungria', 'hungary': 'Hungria',
    'rumania': 'Rumania', 'romania': 'Rumania',
  };

  // Ciudades que aparecen en el texto de país/loc del catálogo → sede real a
  // nivel ciudad (lat, lng, etiqueta, clave de país).
  const CITY = {
    'denver': [39.74, -104.99, 'Denver', 'EEUU'],
    'dallas': [32.78, -96.80, 'Dallas', 'EEUU'],
    'san francisco': [37.77, -122.42, 'San Francisco', 'EEUU'],
    'nueva york': [40.71, -74.01, 'Nueva York', 'EEUU'],
    'new york': [40.71, -74.01, 'New York', 'EEUU'],
    'atlanta': [33.75, -84.39, 'Atlanta', 'EEUU'],
    'omaha': [41.26, -95.93, 'Omaha', 'EEUU'],
    'las vegas': [36.17, -115.14, 'Las Vegas', 'EEUU'],
    'boulder': [40.01, -105.27, 'Boulder', 'EEUU'],
    'herndon': [38.97, -77.39, 'Herndon', 'EEUU'],
    'kansas city': [39.10, -94.58, 'Kansas City', 'EEUU'],
    'chicago': [41.88, -87.63, 'Chicago', 'EEUU'],
    'minneapolis': [44.98, -93.27, 'Minneapolis', 'EEUU'],
    'portland': [45.52, -122.68, 'Portland', 'EEUU'],
    'redwood city': [37.49, -122.24, 'Redwood City', 'EEUU'],
    'fort worth': [32.76, -97.33, 'Fort Worth', 'EEUU'],
    'jacksonville': [30.33, -81.66, 'Jacksonville', 'EEUU'],
    'palm beach gardens': [26.82, -80.14, 'Palm Beach Gardens', 'EEUU'],
    'reston': [38.96, -77.36, 'Reston', 'EEUU'],
    'greeley': [40.42, -104.71, 'Greeley', 'EEUU'],
    'ypsilanti': [42.24, -83.61, 'Ypsilanti', 'EEUU'],
    'carrollton': [32.95, -96.89, 'Carrollton', 'EEUU'],
    'milwaukee': [43.04, -87.91, 'Milwaukee', 'EEUU'],
    'toronto': [43.65, -79.38, 'Toronto', 'Canada'],
    'montreal': [45.50, -73.57, 'Montreal', 'Canada'],
    'calgary': [51.05, -114.07, 'Calgary', 'Canada'],
    'sidney': [-33.87, 151.21, 'Sídney', 'Australia'],
    'sydney': [-33.87, 151.21, 'Sydney', 'Australia'],
    'canberra': [-35.28, 149.13, 'Canberra', 'Australia'],
    'dubai': [25.20, 55.27, 'Dubái', 'EAU'],
    'abu dhabi': [24.45, 54.38, 'Abu Dabi', 'EAU'],
    'basel': [47.56, 7.59, 'Basilea', 'Suiza'],
    'schindellegi': [47.17, 8.71, 'Schindellegi', 'Suiza'],
    'frankfurt': [50.11, 8.68, 'Fráncfort', 'Alemania'],
    'hamburgo': [53.55, 9.99, 'Hamburgo', 'Alemania'],
    'hamburg': [53.55, 9.99, 'Hamburg', 'Alemania'],
    'leipzig': [51.34, 12.37, 'Leipzig', 'Alemania'],
    'londres': [51.51, -0.13, 'Londres', 'ReinoUnido'],
    'london': [51.51, -0.13, 'London', 'ReinoUnido'],
    'kent': [51.28, 0.52, 'Kent', 'ReinoUnido'],
    'kingston upon thames': [51.41, -0.30, 'Kingston upon Thames', 'ReinoUnido'],
    'la haya': [52.08, 4.30, 'La Haya', 'PaisesBajos'],
    'shenzhen': [22.54, 114.06, 'Shenzhen', 'China'],
    'shanghai': [31.23, 121.47, 'Shanghái', 'China'],
    'pekin': [39.90, 116.40, 'Pekín', 'China'],
    'beijing': [39.90, 116.40, 'Beijing', 'China'],
    'hefei': [31.82, 117.23, 'Hefei', 'China'],
    'tianjin': [39.34, 117.36, 'Tianjín', 'China'],
    'hong kong': [22.32, 114.17, 'Hong Kong', 'HongKong'],
    'singapur': [1.29, 103.85, 'Singapur', 'Singapur'],
    'singapore': [1.29, 103.85, 'Singapore', 'Singapur'],
    'baku': [40.41, 49.87, 'Bakú', 'Azerbaiyan'],
    'ulyanovsk': [54.32, 48.40, 'Uliánovsk', 'Rusia'],
    'moscu': [55.76, 37.62, 'Moscú', 'Rusia'],
    'reggio emilia': [44.70, 10.63, 'Reggio Emilia', 'Italia'],
    'kista': [59.40, 17.95, 'Kista', 'Suecia'],
    'estocolmo': [59.33, 18.07, 'Estocolmo', 'Suecia'],
    'swords': [53.46, -6.22, 'Swords', 'Irlanda'],
    'cork': [51.90, -8.47, 'Cork', 'Irlanda'],
  };
  // más largas primero: "kansas city" antes que un hipotético "kansas"
  const CITY_KEYS = Object.keys(CITY).sort((a, b) => b.length - a.length);

  // ── Hubs regionales de EE.UU. — para repartir las empresas US sin ciudad ───
  const US_HUBS = [
    [37.39, -122.08, 'Silicon Valley'],   // Bay Area
    [47.61, -122.33, 'Seattle'],
    [30.27, -97.74,  'Austin'],
    [40.71, -74.01,  'New York'],
    [42.36, -71.06,  'Boston'],
    [33.45, -112.07, 'Phoenix'],          // TSMC AZ, Intel
    [32.78, -96.80,  'Dallas'],
    [34.05, -118.24, 'Los Angeles'],      // SpaceX / Hawthorne cercano
    [45.52, -122.68, 'Portland'],         // Intel Hillsboro
  ];

  // ── HQ reales de empresas clave (precisión para la demo) ───────────────────
  const HQ = {
    Nvidia:        [37.37, -121.96],  // Santa Clara
    AMD:           [37.40, -121.98],  // Santa Clara
    Intel:         [45.53, -122.93],  // Hillsboro (sitio principal: fabs D1X/R&D; sede legal en Santa Clara)
    Apple:         [37.33, -122.03],  // Cupertino
    Microsoft:     [47.64, -122.13],  // Redmond
    Alphabet:      [37.42, -122.08],  // Mountain View
    Google:        [37.42, -122.08],
    Meta:          [37.48, -122.15],  // Menlo Park
    Amazon:        [47.62, -122.34],  // Seattle
    Oracle:        [30.55, -97.69],   // Austin
    Dell:          [30.30, -97.69],   // Round Rock
    Broadcom:      [37.41, -121.97],  // Palo Alto / San Jose
    Qualcomm:      [32.90, -117.20],  // San Diego
    OpenAI:        [37.77, -122.42],  // San Francisco
    Anthropic:     [37.77, -122.42],  // San Francisco
    Micron:        [43.61, -116.21],  // Boise
    Marvell:       [37.41, -121.97],
    SpaceX:        [33.92, -118.33],  // Hawthorne
    RocketLab:     [33.83, -118.15],  // Long Beach, CA (sede; lanza desde Mahia, NZ)
    AST_SpaceMobile:[31.99, -102.08], // Midland, TX
    Anduril:       [33.65, -117.74],  // Costa Mesa
    ShieldAI:      [32.90, -117.20],  // San Diego
    Kratos_Defense:[32.90, -117.20],  // San Diego
    Iridium:       [38.93, -77.18],   // McLean, Virginia

    // Asia
    TSMC:          [24.77, 120.99],   // Hsinchu
    Samsung:       [37.27, 127.05],   // Hwaseong / Suwon
    SKHynix:       [37.21, 127.10],   // Icheon
    SMIC:          [31.21, 121.59],   // Shanghai
    HiSilicon:     [22.58, 114.06],   // Shenzhen
    Huawei:        [22.65, 114.06],   // Shenzhen (Dongguan)
    Cambricon:     [39.98, 116.31],   // Beijing
    Foxconn:       [25.01, 121.46],   // New Taipei (Tucheng)
    TokyoOhka:     [35.53, 139.70],   // Kawasaki
    SonySemi:      [35.63, 139.74],   // Tokyo

    // Europa
    ASML:          [51.41, 5.42],     // Veldhoven
    ASM:           [52.34, 4.86],     // Almere
    Infineon:      [48.21, 11.62],    // Munich
    STMicro:       [45.78, 4.88],     // Geneva/Grenoble axis
    Zeiss:         [48.45, 9.95],     // Oberkochen
    Trumpf:        [48.80, 9.06],     // Ditzingen
    Nokia:         [60.21, 24.81],    // Espoo
    Ericsson:      [59.40, 17.95],    // Stockholm

    // Israel
    QuantumMachines:[32.08, 34.78],   // Tel Aviv

    // capa energía/materiales/macro (catálogo con país 'RestoMundo' sin loc)
    SaudiAramco:   [26.29, 50.11],    // Dhahran
    Petrobras:     [-22.91, -43.17],  // Río de Janeiro
    QatarEnergy:   [25.29, 51.53],    // Doha
    Trafigura:     [1.28, 103.85],    // Singapur
    Vale:          [-22.91, -43.17],  // Río de Janeiro
    GrupoMexico:   [19.43, -99.13],   // Ciudad de México
    Cemex:         [25.65, -100.40],  // San Pedro Garza García (Monterrey)
    PIF_SaudiArabia:[24.71, 46.68],   // Riad
    Temasek:       [1.28, 103.85],    // Singapur
    GIC_Singapore: [1.28, 103.85],    // Singapur
    QIA:           [25.29, 51.53],    // Doha
    Qatar_Airways_Cargo:[25.26, 51.61], // Doha (Hamad)
  };

  // ── Hash determinista (sin Math.random, estable entre cargas) ──────────────
  function hash(str) {
    let h = 2166136261;
    for (let i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return (h >>> 0);
  }

  function jitter(seed, amp) {
    // dos valores pseudo-aleatorios estables en [-amp, amp]
    const a = ((seed % 1000) / 1000) * 2 - 1;
    const b = (((seed >> 10) % 1000) / 1000) * 2 - 1;
    return [a * amp, b * amp];
  }

  function norm(s) {
    return String(s == null ? '' : s).normalize('NFD').replace(/[̀-ͯ]/g, '')
      .toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  }

  // Texto libre de país ("Estados Unidos (HQ Denver, CO)", "Japón") → clave.
  // Desde 2026-10-14 también un ISO-2 guardado por el importador ('US' → 'EEUU', 'JP' → 'Japon'): solo dos
  // MAYÚSCULAS y solo si su clave existe en COUNTRY (igual que core/world.country_key).
  function countryKey(raw) {
    if (!raw) return null;
    if (Object.prototype.hasOwnProperty.call(COUNTRY, raw)) return raw;
    const t = String(raw).trim();
    if (KC_ISO_RX.test(t) && KC_TABLE[t] && Object.prototype.hasOwnProperty.call(COUNTRY, KC_TABLE[t].key)) {
      return KC_TABLE[t].key;
    }
    const n = norm(raw);
    if (ALIAS[n]) return ALIAS[n];
    const first = norm(String(raw).split(/[\/(,;—–]/)[0]);
    if (first && ALIAS[first]) return ALIAS[first];
    return null;
  }

  // Primera ciudad conocida mencionada en el texto (por posición).
  function cityHint(raw) {
    const s = ' ' + norm(raw) + ' ';
    if (s.length <= 2) return null;
    let best = null, bi = Infinity;
    for (const k of CITY_KEYS) {
      const i = s.indexOf(' ' + k + ' ');
      if (i >= 0 && i < bi) { bi = i; best = k; }
    }
    return best;
  }

  // 'RestoMundo'/'RestoEuropa' son etiquetas genéricas: si el loc dice el país
  // concreto ("Canadá", "Finlandia"), manda el loc.
  const GENERIC = { RestoMundo: 1, RestoEuropa: 1 };
  function normCountry(node) {
    const k = countryKey(node && node.country);
    if (k && !GENERIC[k]) return k;
    const k2 = countryKey(node && node.loc);
    if (k2 && !(k && GENERIC[k2])) return k2;
    return k || k2 || 'RestoMundo';
  }

  // ── API principal: resuelve un nodo (o id+meta) a {lat,lng} ────────────────
  function geoCoord(node) {
    if (!node) return { lat: 0, lng: 0, label: '?', precision: 'unknown', precise: false };
    const id = node.id || node.label || '';

    // 1) HQ real curado
    if (Object.prototype.hasOwnProperty.call(HQ, id)) {
      return { lat: HQ[id][0], lng: HQ[id][1], label: node.loc || id, precise: true, precision: 'hq',
        country: normCountry(node) };
    }

    // 2) ciudad mencionada en país/loc
    const ck = cityHint((node.country || '') + ' | ' + (node.loc || ''));
    if (ck) {
      const c = CITY[ck];
      const [dj, dk] = jitter(hash(id + 'c'), 0.08);
      return { lat: c[0] + dj, lng: c[1] + dk, label: c[2], region: c[2], precise: true, precision: 'city',
        country: c[3] };
    }

    const country = normCountry(node);

    // 3) EE.UU.: repartir por hubs regionales (aproximado)
    if (country === 'EEUU') {
      const hub = US_HUBS[hash(id) % US_HUBS.length];
      const [dj, dk] = jitter(hash(id + 'us'), 1.1);
      return { lat: hub[0] + dj, lng: hub[1] + dk, label: hub[2], region: hub[2], precise: false,
        precision: 'hub', country: country };
    }

    // 4) centro del país + jitter (aproximado); 5) desconocido → hub global
    const base = COUNTRY[country] || COUNTRY.RestoMundo;
    const [dj, dk] = jitter(hash(id), country === 'China' || country === 'Europa' ? 2.2 : 1.1);
    const known = country !== 'RestoMundo';
    return { lat: base[0] + dj, lng: base[1] + dk, label: node.loc || country, region: country, precise: false,
      precision: known ? 'country' : 'unknown', country: country };
  }

  // Convierte lat/lng a vector 3D sobre una esfera de radio r (Three.js).
  function latLngToVec3(lat, lng, r) {
    const phi = (90 - lat) * Math.PI / 180;
    const theta = (lng + 180) * Math.PI / 180;
    return {
      x: -r * Math.sin(phi) * Math.cos(theta),
      y: r * Math.cos(phi),
      z: r * Math.sin(phi) * Math.sin(theta),
    };
  }

  // Distancia de gran círculo en km (haversine).
  function haversineKm(lat1, lng1, lat2, lng2) {
    const R = 6371.0088, rad = Math.PI / 180;
    const dLat = (lat2 - lat1) * rad, dLng = (lng2 - lng1) * rad;
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLng / 2) ** 2;
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(a)));
  }

  // ── KhipuCountries: ISO-2 ↔ clave del catálogo ↔ nombre ES/EN ↔ ¿Europa? ─────────────────────────────────
  // Gemela EXACTA de core/countries.py (iso2_of / region_of / catalog_key_of / label / is_europe). La tabla de
  // abajo se GENERA con `python scripts/build_country_review.py --js` (tests/test_countries.py exige paridad):
  // no la edites a mano. Cada fila: [iso2, nombre EN, nombre ES, clave del catálogo de hoy ('' = ninguna), ¿Europa?].
  // BEGIN KhipuCountries TABLE (generado)
  const KC_DATA = {"regions":{"Europa":{"en":"Europe","es":"Europa"},"RestoEuropa":{"en":"Rest of Europe",
    "es":"Resto de Europa"},"RestoMundo":{"en":"Rest of World","es":"Resto del mundo"}},"extra":{"aland":"AX",
    "america":"US","aotearoa":"NZ","bahrein":"BH","bangladesh":"BD","belarus":"BY","bielorusia":"BY",
    "bolivia plurinational state of":"BO","bosnia":"BA","britain":"GB","brunei darussalam":"BN","burma":"MM",
    "cabo verde":"CV","cape verde":"CV","china continental":"CN","chinese taipei":"TW","congo brazzaville":"CG",
    "congo kinshasa":"CD","corea sur":"KR","cote d ivoire":"CI","curacao":"CW","czech":"CZ","dprk":"KP","drc":"CD",
    "east timor":"TL","eau":"AE","ee uu de america":"US","emiratos":"AE","emiratos arabes":"AE","escocia":"GB",
    "eslovaquia":"SK","estados unidos de america":"US","falklands":"FK","faroes":"FO","gales":"GB","gran bretana":"GB",
    "hk":"HK","holland":"NL","holy see":"VA","hong kong china":"HK","hong kong sar":"HK","hongkong":"HK",
    "iran islamic republic of":"IR","irlanda del norte":"GB","islas virgenes":"VI","ivory coast":"CI","kazajstan":"KZ",
    "kazakstan":"KZ","kingdom of saudi arabia":"SA","kirguizistan":"KG","korea democratic people s republic of":"KP",
    "korea republic of":"KR","korea south":"KR","ksa":"SA","kyrgyz republic":"KG","lao":"LA",
    "lao people s democratic republic":"LA","libyan arab jamahiriya":"LY","macao china":"MO","macau":"MO",
    "macedonia":"MK","mainland china":"CN","malvinas":"FK","micronesia federated states of":"FM",
    "moldova republic of":"MD","new caledonia":"NC","northern ireland":"GB","nueva zelandia":"NZ",
    "palestinian territories":"PS","palestinian territory":"PS","people s republic of china":"CN","persia":"IR",
    "pitcairn":"PN","rd congo":"CD","rdc":"CD","reino de arabia saudita":"SA","republic of china":"TW",
    "republica checa":"CZ","republica de moldova":"MD","republica popular china":"CN","reunion":"RE","roc":"TW",
    "rok":"KR","russian federation":"RU","sahara occidental":"EH","saint helena ascension and tristan da cunha":"SH",
    "saint martin french part":"MF","santa sede":"VA","sao tome and principe":"ST","scotland":"GB",
    "sint maarten dutch part":"SX","slovak republic":"SK","st helena":"SH","st kitts and nevis":"KN","st lucia":"LC",
    "st vincent and the grenadines":"VC","suazilandia":"SZ","swaziland":"SZ","syrian arab republic":"SY",
    "tadjikistan":"TJ","taiwan province of china":"TW","tanzania united republic of":"TZ","timor este":"TL",
    "trinidad":"TT","turkiye":"TR","u k":"GB","u s a":"US","uae":"AE","united states virgin islands":"VI",
    "us virgin islands":"VI","uzbekistan":"UZ","vatican":"VA","vaticano":"VA","venezuela bolivarian republic of":"VE",
    "viet nam":"VN","virgin islands british":"VG","virgin islands u s":"VI","wales":"GB","zimbabue":"ZW",
    "zimbabwe":"ZW"},"rows":[["AD","Andorra","Andorra","",1],["AE","United Arab Emirates","Emiratos Árabes Unidos","EAU",
    0],["AF","Afghanistan","Afganistán","",0],["AG","Antigua and Barbuda","Antigua y Barbuda","",0],["AI","Anguilla",
    "Anguila","",0],["AL","Albania","Albania","",1],["AM","Armenia","Armenia","",0],["AO","Angola","Angola","",0],["AQ",
    "Antarctica","Antártida","",0],["AR","Argentina","Argentina","Argentina",0],["AS","American Samoa","Samoa Americana",
    "",0],["AT","Austria","Austria","Austria",1],["AU","Australia","Australia","Australia",0],["AW","Aruba","Aruba","",0],
    ["AX","Åland Islands","Islas Åland","",1],["AZ","Azerbaijan","Azerbaiyán","Azerbaiyan",0],["BA",
    "Bosnia and Herzegovina","Bosnia y Herzegovina","",1],["BB","Barbados","Barbados","",0],["BD","Bangladesh",
    "Bangladés","",0],["BE","Belgium","Bélgica","Belgica",1],["BF","Burkina Faso","Burkina Faso","",0],["BG","Bulgaria",
    "Bulgaria","",1],["BH","Bahrain","Baréin","",0],["BI","Burundi","Burundi","",0],["BJ","Benin","Benín","",0],["BL",
    "Saint Barthélemy","San Bartolomé","",0],["BM","Bermuda","Bermudas","",0],["BN","Brunei","Brunéi","",0],["BO",
    "Bolivia","Bolivia","",0],["BQ","Bonaire, Sint Eustatius and Saba","Bonaire, San Eustaquio y Saba","",0],["BR",
    "Brazil","Brasil","Brasil",0],["BS","Bahamas","Bahamas","",0],["BT","Bhutan","Bután","",0],["BV","Bouvet Island",
    "Isla Bouvet","",0],["BW","Botswana","Botsuana","",0],["BY","Belarus","Bielorrusia","",1],["BZ","Belize","Belice","",
    0],["CA","Canada","Canadá","Canada",0],["CC","Cocos (Keeling) Islands","Islas Cocos","",0],["CD",
    "Democratic Republic of the Congo","República Democrática del Congo","",0],["CF","Central African Republic",
    "República Centroafricana","",0],["CG","Republic of the Congo","República del Congo","",0],["CH","Switzerland",
    "Suiza","Suiza",1],["CI","Côte d'Ivoire","Costa de Marfil","",0],["CK","Cook Islands","Islas Cook","",0],["CL",
    "Chile","Chile","Chile",0],["CM","Cameroon","Camerún","",0],["CN","China","China","China",0],["CO","Colombia",
    "Colombia","Colombia",0],["CR","Costa Rica","Costa Rica","",0],["CU","Cuba","Cuba","",0],["CV","Cape Verde",
    "Cabo Verde","",0],["CW","Curaçao","Curazao","",0],["CX","Christmas Island","Isla de Navidad","",0],["CY","Cyprus",
    "Chipre","",1],["CZ","Czechia","Chequia","Chequia",1],["DE","Germany","Alemania","Alemania",1],["DJ","Djibouti",
    "Yibuti","",0],["DK","Denmark","Dinamarca","Dinamarca",1],["DM","Dominica","Dominica","",0],["DO",
    "Dominican Republic","República Dominicana","",0],["DZ","Algeria","Argelia","Argelia",0],["EC","Ecuador","Ecuador","",
    0],["EE","Estonia","Estonia","",1],["EG","Egypt","Egipto","Egipto",0],["EH","Western Sahara","Sáhara Occidental","",
    0],["ER","Eritrea","Eritrea","",0],["ES","Spain","España","Espana",1],["ET","Ethiopia","Etiopía","",0],["FI",
    "Finland","Finlandia","Finlandia",1],["FJ","Fiji","Fiyi","",0],["FK","Falkland Islands","Islas Malvinas","",0],["FM",
    "Micronesia","Micronesia","",0],["FO","Faroe Islands","Islas Feroe","",1],["FR","France","Francia","Francia",1],["GA",
    "Gabon","Gabón","",0],["GB","United Kingdom","Reino Unido","ReinoUnido",1],["GD","Grenada","Granada","",0],["GE",
    "Georgia","Georgia","",0],["GF","French Guiana","Guayana Francesa","",0],["GG","Guernsey","Guernsey","",1],["GH",
    "Ghana","Ghana","",0],["GI","Gibraltar","Gibraltar","",1],["GL","Greenland","Groenlandia","",0],["GM","Gambia",
    "Gambia","",0],["GN","Guinea","Guinea","",0],["GP","Guadeloupe","Guadalupe","",0],["GQ","Equatorial Guinea",
    "Guinea Ecuatorial","",0],["GR","Greece","Grecia","Grecia",1],["GS","South Georgia and the South Sandwich Islands",
    "Islas Georgias del Sur y Sandwich del Sur","",0],["GT","Guatemala","Guatemala","",0],["GU","Guam","Guam","",0],["GW",
    "Guinea-Bissau","Guinea-Bisáu","",0],["GY","Guyana","Guyana","",0],["HK","Hong Kong","Hong Kong","HongKong",0],["HM",
    "Heard Island and McDonald Islands","Islas Heard y McDonald","",0],["HN","Honduras","Honduras","",0],["HR","Croatia",
    "Croacia","",1],["HT","Haiti","Haití","",0],["HU","Hungary","Hungría","Hungria",1],["ID","Indonesia","Indonesia",
    "Indonesia",0],["IE","Ireland","Irlanda","Irlanda",1],["IL","Israel","Israel","Israel",0],["IM","Isle of Man",
    "Isla de Man","",1],["IN","India","India","India",0],["IO","British Indian Ocean Territory",
    "Territorio Británico del Océano Índico","",0],["IQ","Iraq","Irak","",0],["IR","Iran","Irán","Iran",0],["IS",
    "Iceland","Islandia","",1],["IT","Italy","Italia","Italia",1],["JE","Jersey","Jersey","",1],["JM","Jamaica","Jamaica",
    "",0],["JO","Jordan","Jordania","",0],["JP","Japan","Japón","Japon",0],["KE","Kenya","Kenia","Kenia",0],["KG",
    "Kyrgyzstan","Kirguistán","",0],["KH","Cambodia","Camboya","",0],["KI","Kiribati","Kiribati","",0],["KM","Comoros",
    "Comoras","",0],["KN","Saint Kitts and Nevis","San Cristóbal y Nieves","",0],["KP","North Korea","Corea del Norte","",
    0],["KR","South Korea","Corea del Sur","Corea",0],["KW","Kuwait","Kuwait","Kuwait",0],["KY","Cayman Islands",
    "Islas Caimán","",0],["KZ","Kazakhstan","Kazajistán","Kazajistan",0],["LA","Laos","Laos","",0],["LB","Lebanon",
    "Líbano","",0],["LC","Saint Lucia","Santa Lucía","",0],["LI","Liechtenstein","Liechtenstein","",1],["LK","Sri Lanka",
    "Sri Lanka","",0],["LR","Liberia","Liberia","",0],["LS","Lesotho","Lesoto","",0],["LT","Lithuania","Lituania",
    "Lituania",1],["LU","Luxembourg","Luxemburgo","Luxemburgo",1],["LV","Latvia","Letonia","",1],["LY","Libya","Libia","",
    0],["MA","Morocco","Marruecos","",0],["MC","Monaco","Mónaco","",1],["MD","Moldova","Moldavia","",1],["ME",
    "Montenegro","Montenegro","",1],["MF","Saint Martin","San Martín","",0],["MG","Madagascar","Madagascar","",0],["MH",
    "Marshall Islands","Islas Marshall","",0],["MK","North Macedonia","Macedonia del Norte","",1],["ML","Mali","Malí","",
    0],["MM","Myanmar","Birmania","",0],["MN","Mongolia","Mongolia","",0],["MO","Macao","Macao","",0],["MP",
    "Northern Mariana Islands","Islas Marianas del Norte","",0],["MQ","Martinique","Martinica","",0],["MR","Mauritania",
    "Mauritania","",0],["MS","Montserrat","Montserrat","",0],["MT","Malta","Malta","",1],["MU","Mauritius","Mauricio","",
    0],["MV","Maldives","Maldivas","",0],["MW","Malawi","Malaui","",0],["MX","Mexico","México","Mexico",0],["MY",
    "Malaysia","Malasia","Malasia",0],["MZ","Mozambique","Mozambique","",0],["NA","Namibia","Namibia","",0],["NC",
    "New Caledonia","Nueva Caledonia","",0],["NE","Niger","Níger","",0],["NF","Norfolk Island","Isla Norfolk","",0],["NG",
    "Nigeria","Nigeria","Nigeria",0],["NI","Nicaragua","Nicaragua","",0],["NL","Netherlands","Países Bajos","PaisesBajos",
    1],["NO","Norway","Noruega","Noruega",1],["NP","Nepal","Nepal","",0],["NR","Nauru","Nauru","",0],["NU","Niue","Niue",
    "",0],["NZ","New Zealand","Nueva Zelanda","NuevaZelanda",0],["OM","Oman","Omán","",0],["PA","Panama","Panamá",
    "Panama",0],["PE","Peru","Perú","Peru",0],["PF","French Polynesia","Polinesia Francesa","",0],["PG",
    "Papua New Guinea","Papúa Nueva Guinea","",0],["PH","Philippines","Filipinas","Filipinas",0],["PK","Pakistan",
    "Pakistán","Pakistan",0],["PL","Poland","Polonia","Polonia",1],["PM","Saint Pierre and Miquelon",
    "San Pedro y Miquelón","",0],["PN","Pitcairn Islands","Islas Pitcairn","",0],["PR","Puerto Rico","Puerto Rico","",0],
    ["PS","Palestine","Palestina","",0],["PT","Portugal","Portugal","Portugal",1],["PW","Palau","Palaos","",0],["PY",
    "Paraguay","Paraguay","",0],["QA","Qatar","Catar","Catar",0],["RE","Réunion","Reunión","",0],["RO","Romania",
    "Rumania","Rumania",1],["RS","Serbia","Serbia","",1],["RU","Russia","Rusia","Rusia",0],["RW","Rwanda","Ruanda","",0],
    ["SA","Saudi Arabia","Arabia Saudita","ArabiaSaudita",0],["SB","Solomon Islands","Islas Salomón","",0],["SC",
    "Seychelles","Seychelles","",0],["SD","Sudan","Sudán","",0],["SE","Sweden","Suecia","Suecia",1],["SG","Singapore",
    "Singapur","Singapur",0],["SH","Saint Helena","Santa Elena","",0],["SI","Slovenia","Eslovenia","",1],["SJ",
    "Svalbard and Jan Mayen","Svalbard y Jan Mayen","",1],["SK","Slovakia","Eslovaquia","",1],["SL","Sierra Leone",
    "Sierra Leona","",0],["SM","San Marino","San Marino","",1],["SN","Senegal","Senegal","",0],["SO","Somalia","Somalia",
    "",0],["SR","Suriname","Surinam","",0],["SS","South Sudan","Sudán del Sur","",0],["ST","São Tomé and Príncipe",
    "Santo Tomé y Príncipe","",0],["SV","El Salvador","El Salvador","",0],["SX","Sint Maarten","Sint Maarten","",0],["SY",
    "Syria","Siria","",0],["SZ","Eswatini","Esuatini","",0],["TC","Turks and Caicos Islands","Islas Turcas y Caicos","",
    0],["TD","Chad","Chad","",0],["TF","French Southern Territories","Territorios Australes Franceses","",0],["TG","Togo",
    "Togo","",0],["TH","Thailand","Tailandia","Tailandia",0],["TJ","Tajikistan","Tayikistán","",0],["TK","Tokelau",
    "Tokelau","",0],["TL","Timor-Leste","Timor Oriental","",0],["TM","Turkmenistan","Turkmenistán","",0],["TN","Tunisia",
    "Túnez","",0],["TO","Tonga","Tonga","",0],["TR","Turkey","Turquía","Turquia",0],["TT","Trinidad and Tobago",
    "Trinidad y Tobago","",0],["TV","Tuvalu","Tuvalu","",0],["TW","Taiwan","Taiwán","Taiwan",0],["TZ","Tanzania",
    "Tanzania","",0],["UA","Ukraine","Ucrania","Ucrania",1],["UG","Uganda","Uganda","Uganda",0],["UM",
    "United States Minor Outlying Islands","Islas Ultramarinas Menores de Estados Unidos","",0],["US","United States",
    "Estados Unidos","EEUU",0],["UY","Uruguay","Uruguay","",0],["UZ","Uzbekistan","Uzbekistán","",0],["VA","Vatican City",
    "Ciudad del Vaticano","",1],["VC","Saint Vincent and the Grenadines","San Vicente y las Granadinas","",0],["VE",
    "Venezuela","Venezuela","",0],["VG","British Virgin Islands","Islas Vírgenes Británicas","",0],["VI",
    "U.S. Virgin Islands","Islas Vírgenes de los Estados Unidos","",0],["VN","Vietnam","Vietnam","Vietnam",0],["VU",
    "Vanuatu","Vanuatu","",0],["WF","Wallis and Futuna","Wallis y Futuna","",0],["WS","Samoa","Samoa","",0],["XK",
    "Kosovo","Kosovo","",1],["YE","Yemen","Yemen","",0],["YT","Mayotte","Mayotte","",0],["ZA","South Africa","Sudáfrica",
    "Sudafrica",0],["ZM","Zambia","Zambia","",0],["ZW","Zimbabwe","Zimbabue","",0]]};
  // END KhipuCountries TABLE
  const KC_TABLE = {}, KC_KEY_TO_ISO = {}, KC_EUROPE = {};
  KC_DATA.rows.forEach(r => {
    KC_TABLE[r[0]] = { key: r[3] || r[1], es: r[2], en: r[1], eu: !!r[4] };
    if (r[3]) KC_KEY_TO_ISO[r[3]] = r[0];
    if (r[4]) KC_EUROPE[r[0]] = 1;
  });
  const KC_REGIONS = { Europa: 1, RestoEuropa: 1, RestoMundo: 1 };
  const KC_ISO_RX = /^[A-Z]{2}$/;
  let KC_NAME_INDEX = null;
  const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);

  function kcNameIndex() {
    if (!KC_NAME_INDEX) {
      const idx = {};
      KC_DATA.rows.forEach(r => {
        const en = norm(r[1]), es = norm(r[2]);
        if (!has(idx, en)) idx[en] = r[0];
        if (!has(idx, es)) idx[es] = r[0];
      });
      Object.keys(KC_DATA.extra).forEach(k => { idx[k] = KC_DATA.extra[k]; });
      KC_NAME_INDEX = idx;
    }
    return KC_NAME_INDEX;
  }

  // ¿Es un ISO-2 conocido? Solo dos MAYÚSCULAS ('CA' sí, 'ca' no).
  function isIso2(text) {
    const t = String(text == null ? '' : text).trim();
    return KC_ISO_RX.test(t) && has(KC_TABLE, t);
  }

  // Cualquier grafía del país (136 del catálogo, ISO-2, nombre EN/ES) → ISO-2; regiones y desconocidos → null.
  function iso2Of(text) {
    if (text == null) return null;
    const t = String(text).trim();
    if (!t) return null;
    if (isIso2(t)) return t;
    const k = countryKey(t);
    if (k && has(KC_KEY_TO_ISO, k)) return KC_KEY_TO_ISO[k];
    if (k && KC_REGIONS[k]) return null;
    if (k === 'Japan') return 'JP';
    const idx = kcNameIndex();
    const n = norm(t);
    if (has(idx, n)) return idx[n];
    const first = norm(t.split(/[\/(,;—–]/)[0]);
    return has(idx, first) ? idx[first] : null;
  }

  // 'Europa' | 'RestoEuropa' | 'RestoMundo' cuando el texto NO nombra un país real; si no, null.
  function regionOf(text) {
    if (text == null) return null;
    const t = String(text).trim();
    if (!t) return null;
    if (KC_REGIONS[t]) return t;
    const k = countryKey(t);
    return k && KC_REGIONS[k] ? k : null;
  }

  // ISO-2 → clave del catálogo de hoy ('GB' → 'ReinoUnido'); sin clave → nombre EN; desconocido → el mismo texto.
  function catalogKeyOf(iso2) {
    const t = String(iso2 == null ? '' : iso2).trim().toUpperCase();
    return has(KC_TABLE, t) ? KC_TABLE[t].key : (iso2 == null ? '' : iso2);
  }

  // Nombre legible (ISO-2, región o clave del catálogo): label('US','es') → 'Estados Unidos'.
  function countryLabel(code, lang) {
    const lg = String(lang || '').toLowerCase().indexOf('en') === 0 ? 'en' : 'es';
    const t = String(code == null ? '' : code).trim();
    if (!t) return '';
    if (has(KC_DATA.regions, t)) return KC_DATA.regions[t][lg];
    let row = KC_ISO_RX.test(t.toUpperCase()) && has(KC_TABLE, t.toUpperCase()) ? KC_TABLE[t.toUpperCase()] : null;
    if (!row && has(KC_KEY_TO_ISO, t)) row = KC_TABLE[KC_KEY_TO_ISO[t]];
    return row ? row[lg] : t;
  }

  // ¿Europa? (ISO-2, clave o texto; 'Europa'/'RestoEuropa' también).
  function isEurope(text) {
    const iso = iso2Of(text);
    if (iso) return !!KC_EUROPE[iso];
    const r = regionOf(text);
    return r === 'Europa' || r === 'RestoEuropa';
  }

  // Grupo para contar/filtrar por país en el navegador: la clave del catálogo si se reconoce, si no el texto tal cual.
  function countryGroup(raw) {
    const k = countryKey(raw);
    return k || (raw == null ? null : String(raw)) || null;
  }

  // ISO-2 de un nodo: country (o loc cuando country es una región), como core/countries.iso2_of_props.
  function countryIso2(node) {
    if (!node) return null;
    for (const k of ['hq_country', 'country_iso2']) {
      const v = node[k];
      if (v && isIso2(String(v).trim())) return String(v).trim();
    }
    const c = node.country || node.pais;
    const iso = iso2Of(c);
    if (iso) return iso;
    if (!c || regionOf(c)) return iso2Of(node.loc);
    return null;
  }

  window.KhipuCountries = {
    TABLE: KC_TABLE, KEY_TO_ISO: KC_KEY_TO_ISO, EUROPE: KC_EUROPE, EXTRA_ALIAS: KC_DATA.extra,
    iso2Of, regionOf, catalogKeyOf, label: countryLabel, isEurope, isIso2, countryIso2, countryGroup,
  };
  window.GeoCoords = { geoCoord, latLngToVec3, haversineKm, countryKey, countryIso2, countryGroup,
    COUNTRY, ALIAS, US_HUBS, HQ, CITY };
})();
