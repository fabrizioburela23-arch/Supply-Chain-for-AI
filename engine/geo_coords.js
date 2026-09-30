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
// edítala también allá.

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
  function countryKey(raw) {
    if (!raw) return null;
    if (Object.prototype.hasOwnProperty.call(COUNTRY, raw)) return raw;
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

  window.GeoCoords = { geoCoord, latLngToVec3, haversineKm, countryKey, COUNTRY, ALIAS, US_HUBS, HQ, CITY };
})();
