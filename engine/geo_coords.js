// engine/geo_coords.js — Coordenadas geográficas para los globos 3D (Khipu Finance)
// Los nodos NO traen lat/long: solo `country` (EEUU, Japon, Taiwan…) y `loc`.
// Este módulo resuelve cada nodo a {lat,lng} de forma DETERMINISTA:
//   1) HQ real para las empresas clave (demo precisa),
//   2) hubs regionales reales dentro de países grandes (EE.UU. no se vuelve un borrón),
//   3) centroide de país + jitter determinista para el resto.
// Lo usan engine/space3d.js y engine/geoglobe.js.

(function () {
  'use strict';

  // ── Centroides representativos por país/región (lat, lng) ──────────────────
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
  };

  // Fallbacks por `loc` cuando el `country` es genérico o falta.
  const LOC = {
    'EE.UU.': 'EEUU', 'Japón': 'Japon', 'China': 'China', 'Taiwán': 'Taiwan',
    'Alemania': 'Alemania', 'Francia': 'Francia', 'Países Bajos': 'PaisesBajos',
    'Israel': 'Israel', 'Corea del Sur': 'Corea', 'Reino Unido': 'ReinoUnido',
    'India': 'India', 'Australia': 'Australia', 'Europa': 'Europa',
    'Canadá':   [45.50, -73.57],    // Montreal
    'Finlandia':[60.17, 24.94],     // Helsinki
    'Noruega':  [59.91, 10.75],     // Oslo
    'Chile':    [-33.45, -70.67],   // Santiago
  };

  // ── Hubs regionales de EE.UU. — para repartir las 385 empresas US ──────────
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
    Intel:         [45.53, -122.93],  // Hillsboro / Santa Clara
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
    RocketLab:     [-37.79, 175.49],  // Mahia (NZ) / Long Beach HQ
    AST_SpaceMobile:[31.86, -97.10],  // Midland, TX
    Anduril:       [33.65, -117.74],  // Costa Mesa
    ShieldAI:      [32.90, -117.20],  // San Diego
    Kratos_Defense:[32.90, -117.20],  // San Diego
    Iridium:       [22.0,  -90.0],    // McLean VA → use approx; will override below

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
  };
  HQ.Iridium = [38.93, -77.18];       // McLean, Virginia (corrige el aprox de arriba)

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

  function normCountry(node) {
    let c = node && node.country;
    if (c && COUNTRY[c]) return c;
    // intenta por loc
    const loc = node && node.loc;
    if (loc && LOC[loc]) {
      const v = LOC[loc];
      return (typeof v === 'string') ? v : '_LOC_';
    }
    // primer token del loc ("Taiwán (+ Arizona…)" → "Taiwán")
    if (loc) {
      const first = loc.split(/[\/(,]/)[0].trim();
      if (LOC[first]) { const v = LOC[first]; return (typeof v === 'string') ? v : '_LOC_'; }
    }
    return 'RestoMundo';
  }

  // ── API principal: resuelve un nodo (o id+meta) a {lat,lng} ────────────────
  function geoCoord(node) {
    if (!node) return { lat: 0, lng: 0, label: '?' };
    const id = node.id || node.label || '';

    // 1) HQ real
    if (HQ[id]) return { lat: HQ[id][0], lng: HQ[id][1], label: node.loc || id, precise: true };

    // 2) loc con coordenada directa (Canadá, Finlandia…)
    const loc = node.loc;
    if (loc && Array.isArray(LOC[loc])) {
      const [la, lo] = LOC[loc];
      const [dj, dk] = jitter(hash(id), 0.6);
      return { lat: la + dj, lng: lo + dk, label: loc };
    }

    const country = normCountry(node);

    // 3) EE.UU.: repartir por hubs regionales
    if (country === 'EEUU') {
      const hub = US_HUBS[hash(id) % US_HUBS.length];
      const [dj, dk] = jitter(hash(id + 'us'), 1.1);
      return { lat: hub[0] + dj, lng: hub[1] + dk, label: hub[2], region: hub[2] };
    }

    // 4) centroide de país + jitter
    const base = COUNTRY[country] || COUNTRY.RestoMundo;
    const [dj, dk] = jitter(hash(id), country === 'China' || country === 'Europa' ? 2.2 : 1.1);
    return { lat: base[0] + dj, lng: base[1] + dk, label: loc || country, region: country };
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

  window.GeoCoords = { geoCoord, latLngToVec3, COUNTRY, US_HUBS, HQ };
})();
