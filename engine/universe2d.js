// engine/universe2d.js — Universo 2D: respaldo TOTAL del mapa 3D sin WebGL.
//
// Renderer del "universo" en CanvasRenderingContext2D puro (cero three.js,
// cero WebGL): SIEMPRE funciona, incluso con la aceleración de gráficos
// apagada o GPU bloqueada. Mismo layout SEMÁNTICO que engine/graph3d.js:
//   X = etapa de la cadena de valor (CATS[cat].x)
//   Y = riesgo NRS (frágil abajo ↔ resiliente arriba)
//   Z = región geográfica → en 2D es PARALLAX (3 capas de profundidad)
//
// API pública (window.KhipuUniverse2D):
//   init(canvasId) · loadData(nodes, links) · destroy() · pause() · resume()
//   · focus(nodeId)
//
// Globals opcionales que usa si existen (todo con fallback):
//   computeNRS, computeNodeRadius, getCatColorHex, CATS, NODE_BY_ID,
//   window.jumpTo, window._diag, window.LANG / localStorage.eco_lang
//
// NO toca app.html ni graph3d.js: el orquestador decide cuándo invocarlo
// (fallo de WebGL, _selfCheck en negro, etc.).

(function () {
  'use strict';

  /* ── i18n local (regla bilingüe ES/EN — window.LANG / localStorage eco_lang) ── */
  function _lang() {
    try {
      return String(window.LANG || localStorage.getItem('eco_lang') || 'es').slice(0, 2) === 'en' ? 'en' : 'es';
    } catch (e) { return 'es'; }
  }
  const I18N = {
    badge:     { es: '🪐 Modo compatible — universo 2D', en: '🪐 Compatible mode — 2D universe' },
    suppliers: { es: 'prov.',    en: 'suppliers' },
    clients:   { es: 'clientes', en: 'clients' },
    hint:      { es: 'Arrastra · Rueda/pellizco = zoom · Clic = cadena · Doble clic = ficha',
                 en: 'Drag · Wheel/pinch = zoom · Click = chain · Double-click = card' },
  };
  const t = k => (I18N[k] ? I18N[k][_lang()] : k);

  /* ── Constantes de layout (mismos ejes que graph3d._staticLayout) ── */
  const SPAN_X = 360, SPAN_Y = 220;
  const REGION_Z = {
    Taiwan: -3, 'Taiwán': -3, China: -2.3, Corea: -1.5, Korea: -1.5,
    Japon: -0.7, Japan: -0.7, India: 0.2, RestoMundo: 0.9, Israel: 1.3,
    EEUU: 2.1, Canada: 2.5, Europa: 3, Alemania: 3, Francia: 3,
    PaisesBajos: 3, ReinoUnido: 3, RestoEuropa: 3,
  };
  // 3 capas de profundidad: [escala de tamaño, alpha, factor de parallax]
  const LAYERS = [
    { scale: 0.72, alpha: 0.55, par: 0.85 },   // lejana (Asia)
    { scale: 1.00, alpha: 0.80, par: 1.00 },   // media
    { scale: 1.30, alpha: 1.00, par: 1.15 },   // cercana (Occidente)
  ];
  const CHAIN_UP   = '#2BE38B';   // proveedores (verde)
  const CHAIN_DOWN = '#FFB300';   // clientes (naranja)
  // Fallback de colores por categoría si getCatColorHex aún no cargó
  const CAT_FALLBACK = {
    fabless: '#52B1FF', foundry: '#3DE0C8', memoria: '#8e5aff',
    equipos: '#FFB300', materiales: '#9BB8D4', cloud: '#4FC3F7',
    ia: '#B383FF', energia: '#FFD666', espacio: '#7EE8FA',
    defensa: '#FF7A90', nuclear: '#7CFFB2', software: '#6FD6A8',
  };
  const PALETTE10 = ['#52B1FF', '#8e5aff', '#3DE0C8', '#FFB300', '#4FC3F7',
                     '#B383FF', '#7EE8FA', '#FF7A90', '#7CFFB2', '#FFD666'];
  const LINK_HEX = {
    supply: '#4E8B1E', fab: '#0F8C5F', license: '#6B5DD3', cloud: '#0A6CA8',
    invest: '#B8880D', deploy: '#0E7A6E', partner: '#8A857A',
    customer: '#C25E12', owns: '#7C3AED',
  };

  /* ── Estado interno ── */
  const U = {
    inited: false, active: false, raf: 0,
    canvas: null, ctx: null, ownCanvas: false, baseCanvas: null,
    w: 0, h: 0, dpr: 1,
    cam: { x: 0, y: 0 }, camTo: null,           // camTo = animación de focus
    zoom: 0.85, zoomTo: 0.85,
    nodes: [], links: [], idToIdx: new Map(),
    // arrays paralelos precalculados (posición mundo, capa, radio, color…)
    wx: null, wy: null, layer: null, baseR: null, color: null, nrs: null,
    degUp: null, degDown: null,
    sx: null, sy: null, sr: null,                // posiciones de pantalla del frame
    order: [], top40: new Set(), labelCache: [],
    buckets: [],                                  // links agrupados por color/peso
    selected: null, chainSet: null, chainUp: null, chainDown: null, chainLinks: [],
    hovered: -1,
    bg: null, sprites: new Map(),
    drag: false, moved: false, prev: { x: 0, y: 0 }, pinch: 0,
    frameEMA: 16, lite: false, elapsed: 0, lastTs: 0,
    badge: null, tip: null, tipPinned: false, hint: null,
    ro: null, sizeWatch: false, diagSent: false, failCount: 0,
    handlers: [],                                 // [(target, tipo, fn, opts)]
  };

  /* ── Helpers ── */
  const lid = v => (typeof v === 'object' && v !== null) ? v.id : v;
  function _rng(seed) {
    let s = seed >>> 0;
    return function () { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
  }
  function _hash(str) {
    let h = 5381;
    for (let i = 0; i < str.length; i++) h = (h * 33 ^ str.charCodeAt(i)) >>> 0;
    return h;
  }
  const _jit = (seed, amp) => ((_hash(seed) & 0xFFFF) / 0xFFFF - 0.5) * 2 * amp;
  function _hexToRgba(hex, a) {
    const m = /^#?([0-9a-f]{6})/i.exec(String(hex || '').trim());
    if (!m) return 'rgba(82,177,255,' + a + ')';
    const v = parseInt(m[1], 16);
    return 'rgba(' + ((v >> 16) & 255) + ',' + ((v >> 8) & 255) + ',' + (v & 255) + ',' + a + ')';
  }
  function _catColor(cat) {
    try {
      if (typeof window.getCatColorHex === 'function') {
        const v = window.getCatColorHex(cat);
        if (v && /^#/.test(v)) return v;
      }
    } catch (e) {}
    if (cat && CAT_FALLBACK[cat]) return CAT_FALLBACK[cat];
    return PALETTE10[_hash(String(cat || '?')) % PALETTE10.length];
  }
  function _nrsOf(id) {
    try { if (typeof window.computeNRS === 'function') return window.computeNRS(id); } catch (e) {}
    return 50;
  }
  function _radiusOf(id, degree, big) {
    try {
      if (typeof window.computeNodeRadius === 'function') {
        const r = window.computeNodeRadius(id);
        if (r > 0) return r;
      }
    } catch (e) {}
    return Math.min(22, (big ? 11 : 5) + Math.sqrt(degree || 1) * 2);
  }
  function _listen(target, type, fn, opts) {
    target.addEventListener(type, fn, opts);
    U.handlers.push([target, type, fn, opts]);
  }

  /* ── Sprites de nodo: disco con glow pre-renderizado (drawImage es barato;
        shadowBlur por nodo/frame NO lo es). Un sprite por color. ── */
  function _sprite(hex) {
    let sp = U.sprites.get(hex);
    if (sp) return sp;
    const S = 64, half = S / 2;
    const cv = document.createElement('canvas');
    cv.width = cv.height = S;
    const c = cv.getContext('2d');
    const g = c.createRadialGradient(half, half, 0, half, half, half);
    g.addColorStop(0.00, 'rgba(255,255,255,0.95)');       // núcleo caliente
    g.addColorStop(0.22, _hexToRgba(hex, 0.95));          // disco sólido
    g.addColorStop(0.50, _hexToRgba(hex, 0.90));          //   (borde del disco)
    g.addColorStop(0.62, _hexToRgba(hex, 0.28));          // glow
    g.addColorStop(1.00, _hexToRgba(hex, 0));
    c.fillStyle = g;
    c.fillRect(0, 0, S, S);
    U.sprites.set(hex, sp = cv);
    return sp;
  }

  /* ── Fondo "espacio": ~200 estrellas estáticas + nebulosas — se pinta UNA
        vez a un canvas oculto y se blitea cada frame. ── */
  function _buildBackground() {
    const w = Math.max(2, U.w), h = Math.max(2, U.h);
    const bg = U.bg || (U.bg = document.createElement('canvas'));
    bg.width = w; bg.height = h;
    const c = bg.getContext('2d');
    // cielo base con leve gradiente vertical
    const sky = c.createLinearGradient(0, 0, 0, h);
    sky.addColorStop(0, '#04060d');
    sky.addColorStop(0.55, '#060a14');
    sky.addColorStop(1, '#04070f');
    c.fillStyle = sky;
    c.fillRect(0, 0, w, h);
    // nebulosas: colores de la app (azul / violeta / teal)
    [[0.20, 0.28, 0.52, '#8e5aff', 0.10],
     [0.80, 0.22, 0.46, '#52B1FF', 0.10],
     [0.55, 0.82, 0.55, '#3DE0C8', 0.06]].forEach(([nx, ny, nr, hex, a]) => {
      const r = nr * Math.min(w, h) * 1.35;
      const g = c.createRadialGradient(nx * w, ny * h, 0, nx * w, ny * h, r);
      g.addColorStop(0, _hexToRgba(hex, a));
      g.addColorStop(0.5, _hexToRgba(hex, a * 0.45));
      g.addColorStop(1, _hexToRgba(hex, 0));
      c.fillStyle = g;
      c.fillRect(0, 0, w, h);
    });
    // resplandor central sutil (el "sol" Khipus)
    const core = c.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, Math.min(w, h) * 0.5);
    core.addColorStop(0, 'rgba(26,106,154,0.16)');
    core.addColorStop(1, 'rgba(26,106,154,0)');
    c.fillStyle = core;
    c.fillRect(0, 0, w, h);
    // ~200 estrellas estáticas (RNG con semilla: mismo cielo siempre)
    const rnd = _rng(1337);
    for (let i = 0; i < 205; i++) {
      const x = rnd() * w, y = rnd() * h;
      const big = rnd() > 0.86;
      c.globalAlpha = 0.22 + rnd() * 0.55;
      c.fillStyle = big ? '#cfe6ff' : '#8FA8C8';
      c.beginPath();
      c.arc(x, y, big ? 1.4 : 0.7, 0, 6.2832);
      c.fill();
    }
    c.globalAlpha = 1;
  }

  /* ── Tamaño / DPR ── */
  function _ensureSized() {
    const cv = U.canvas;
    if (!cv) return false;
    const w = cv.clientWidth || (cv.parentElement && cv.parentElement.clientWidth) || 0;
    const h = cv.clientHeight || (cv.parentElement && cv.parentElement.clientHeight) || 0;
    if (!w || !h) return false;
    const dpr = Math.min(window.devicePixelRatio || 1, U.lite ? 1 : 2);
    if (U.w !== w || U.h !== h || U.dpr !== dpr) {
      U.w = w; U.h = h; U.dpr = dpr;
      cv.width = Math.round(w * dpr);
      cv.height = Math.round(h * dpr);
      _buildBackground();
    }
    return true;
  }
  // Vigilante anti "canvas 0×0" (display:none / carrera de layout): reintenta
  // dimensionar cada frame hasta lograrlo (máx ~20 s) — mismo patrón que 3D.
  function _startSizeWatch() {
    if (U.sizeWatch) return;
    U.sizeWatch = true;
    let tries = 0;
    const tick = () => {
      if (!U.inited) { U.sizeWatch = false; return; }
      if (_ensureSized() || tries++ > 1200) { U.sizeWatch = false; return; }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  /* ── DOM auxiliar: aviso bilingüe + tooltip ── */
  function _ensureBadge() {
    if (U.badge && U.badge.isConnected) { U.badge.textContent = t('badge'); return; }
    const el = document.createElement('div');
    el.id = 'universe2d-badge';
    el.style.cssText = 'position:absolute;left:12px;bottom:12px;z-index:8;pointer-events:none;' +
      'font:10px "JetBrains Mono",monospace;color:#7a9cc4;background:rgba(8,12,22,.72);' +
      'border:1px solid rgba(80,130,200,.25);border-radius:12px;padding:4px 10px;' +
      'backdrop-filter:blur(4px);white-space:nowrap';
    el.textContent = t('badge');
    (U.canvas.parentElement || document.body).appendChild(el);
    U.badge = el;
  }
  function _showHint() {
    if (U.hint) return;
    const el = document.createElement('div');
    el.style.cssText = 'position:absolute;bottom:70px;left:50%;transform:translateX(-50%);' +
      'background:rgba(0,0,0,.7);color:#ccc;font-size:11px;padding:6px 14px;border-radius:20px;' +
      'pointer-events:none;z-index:50;white-space:nowrap;transition:opacity .5s;' +
      'font-family:"JetBrains Mono",monospace';
    el.textContent = t('hint');
    (U.canvas.parentElement || document.body).appendChild(el);
    U.hint = el;
    setTimeout(() => { if (U.hint) U.hint.style.opacity = '0'; }, 4000);
    setTimeout(() => { if (U.hint) { U.hint.remove(); U.hint = null; } }, 4600);
  }
  function _ensureTip() {
    if (U.tip && U.tip.isConnected) return U.tip;
    const el = document.createElement('div');
    el.id = 'universe2d-tooltip';
    el.style.cssText = 'position:fixed;display:none;z-index:999;pointer-events:none;' +
      'max-width:230px;background:rgba(10,14,24,.94);border:1px solid rgba(80,130,200,.35);' +
      'border-radius:9px;padding:9px 11px;font-family:"Archivo",sans-serif;' +
      'box-shadow:0 6px 22px rgba(0,0,0,.5)';
    document.body.appendChild(el);
    U.tip = el;
    return el;
  }
  function _showTip(i, cx, cy) {
    const tip = _ensureTip();
    const n = U.nodes[i];
    if (!n) { tip.style.display = 'none'; return; }
    const nrs = U.nrs[i];
    const nrsColor = nrs < 30 ? '#22c55e' : nrs < 60 ? '#f59e0b' : '#ef4444';
    tip.innerHTML =
      '<div style="font-size:12px;font-weight:700;color:#e8edf5;line-height:1.3">' + (n.label || n.id) + '</div>' +
      (n.ticker ? '<div style="font-size:10px;color:#5b8ab8;font-family:\'JetBrains Mono\',monospace;margin-top:2px">' + n.ticker + '</div>' : '') +
      '<div style="display:flex;gap:12px;font-size:10px;color:#7a9cc4;margin-top:6px;align-items:center">' +
        '<span>NRS <strong style="color:' + nrsColor + '">' + nrs + '</strong></span>' +
        '<span style="color:' + CHAIN_UP + '">⬆ ' + U.degUp[i] + ' ' + t('suppliers') + '</span>' +
        '<span style="color:' + CHAIN_DOWN + '">⬇ ' + U.degDown[i] + ' ' + t('clients') + '</span>' +
      '</div>';
    const vw = window.innerWidth, vh = window.innerHeight;
    let tx = cx + 16, ty = cy - 30;
    if (tx + 240 > vw - 8) tx = cx - 250;
    if (ty + 90 > vh - 8) ty = vh - 98;
    if (ty < 8) ty = 8;
    tip.style.left = tx + 'px';
    tip.style.top = ty + 'px';
    tip.style.display = 'block';
  }
  function _hideTip(force) {
    if (U.tipPinned && !force) return;
    if (U.tip) U.tip.style.display = 'none';
    if (force) U.tipPinned = false;
  }

  /* ── Carga de datos: precalcula TODO (posiciones mundo, capa, radio, color,
        etiquetas medidas una vez, buckets de links) — cero trabajo por frame. ── */
  function loadData(nodes, links) {
    U.nodes = Array.isArray(nodes) ? nodes : [];
    U.links = Array.isArray(links) ? links : [];
    const N = U.nodes.length;
    U.idToIdx = new Map();
    U.wx = new Float32Array(N); U.wy = new Float32Array(N);
    U.layer = new Uint8Array(N); U.baseR = new Float32Array(N);
    U.sx = new Float32Array(N); U.sy = new Float32Array(N); U.sr = new Float32Array(N);
    U.color = new Array(N); U.nrs = new Int16Array(N);
    U.degUp = new Int16Array(N); U.degDown = new Int16Array(N);
    U.nodes.forEach((n, i) => U.idToIdx.set(n.id, i));

    // grados (para radio fallback + tooltip)
    U.links.forEach(l => {
      const si = U.idToIdx.get(lid(l.source)), ti = U.idToIdx.get(lid(l.target));
      if (si != null) U.degDown[si]++;   // source PROVEE a target → source tiene cliente
      if (ti != null) U.degUp[ti]++;     // target recibe → tiene proveedor
    });

    const CATS_REF = window.CATS || {};
    U.nodes.forEach((n, i) => {
      const cat = CATS_REF[n.cat];
      const catX = (cat && cat.x != null) ? cat.x : 0.5;
      const nrs = _nrsOf(n.id);
      U.nrs[i] = nrs;
      // X = cadena de valor · Y = riesgo (frágil ABAJO — canvas crece hacia abajo)
      U.wx[i] = (catX - 0.5) * 2 * SPAN_X + _jit(n.id + 'x', 26);
      U.wy[i] = (nrs / 100 - 0.5) * 2 * SPAN_Y + _jit(n.id + 'y', 18);
      // Z (región) → capa de parallax: Asia lejos, Occidente cerca
      const zk = REGION_Z[n.country] != null ? REGION_Z[n.country]
               : REGION_Z[n.region] != null ? REGION_Z[n.region] : 0;
      U.layer[i] = zk < -1 ? 0 : zk > 1 ? 2 : 1;
      U.baseR[i] = _radiusOf(n.id, U.degUp[i] + U.degDown[i], n.big) * 0.62;
      U.color[i] = _catColor(n.cat);
      _sprite(U.color[i]);   // precalienta la caché de sprites
    });

    // orden de dibujo: capa lejana primero (los cercanos tapan a los lejanos)
    U.order = Array.from({ length: N }, (_, i) => i)
      .sort((a, b) => (U.layer[a] - U.layer[b]) || (U.baseR[a] - U.baseR[b]));

    // top ~40 por tamaño: los únicos con etiqueta permanente (LOD)
    U.top40 = new Set(
      Array.from({ length: N }, (_, i) => i)
        .sort((a, b) => U.baseR[b] - U.baseR[a]).slice(0, 40)
    );

    // etiquetas: texto corto + ancho MEDIDO UNA VEZ (jamás measureText por frame)
    const mctx = (U.ctx || document.createElement('canvas').getContext('2d'));
    mctx.font = '500 11px "Archivo", sans-serif';
    U.labelCache = U.nodes.map(n => {
      const s = String(n.label || n.id);
      const short = s.length > 16 ? s.slice(0, 15) + '…' : s;
      return { text: short, w: mctx.measureText(short).width };
    });

    // links → buckets por (color de tipo × peso fuerte/débil): pocas pasadas
    // de stroke por frame en vez de 1.600 cambios de estilo.
    const bmap = new Map();
    U.links.forEach(l => {
      const si = U.idToIdx.get(lid(l.source)), ti = U.idToIdx.get(lid(l.target));
      if (si == null || ti == null || si === ti) return;
      const hex = LINK_HEX[l.type || 'supply'] || '#4E8B1E';
      const strong = (l.w || 1) >= 3;
      const key = hex + (strong ? 'S' : 'W');
      let b = bmap.get(key);
      if (!b) bmap.set(key, b = { hex, alpha: strong ? 0.16 : 0.09, pairs: [] });
      b.pairs.push(si, ti);
    });
    U.buckets = [...bmap.values()];

    _clearChain();
    _sendDiag();
  }

  /* ── Beacon de diagnóstico: universe2d corrió en este equipo ── */
  function _sendDiag() {
    if (U.diagSent || !U.inited || !U.nodes.length) return;
    U.diagSent = true;
    try { if (window._diag) window._diag('universe2d_on', { nodes: U.nodes.length }); } catch (e) {}
  }

  /* ── Cadena resaltada (clic en nodo) ── */
  function _highlightChain(i) {
    const id = U.nodes[i] && U.nodes[i].id;
    if (!id) return;
    const up = new Set(), down = new Set();
    U.chainLinks = [];
    U.links.forEach(l => {
      const s = lid(l.source), tt = lid(l.target);
      if (tt === id && U.idToIdx.has(s)) {
        up.add(U.idToIdx.get(s));
        U.chainLinks.push([U.idToIdx.get(s), i, CHAIN_UP]);
      }
      if (s === id && U.idToIdx.has(tt)) {
        down.add(U.idToIdx.get(tt));
        U.chainLinks.push([i, U.idToIdx.get(tt), CHAIN_DOWN]);
      }
    });
    U.selected = i;
    U.chainUp = up; U.chainDown = down;
    U.chainSet = new Set([i, ...up, ...down]);
  }
  function _clearChain() {
    U.selected = null;
    U.chainSet = null; U.chainUp = null; U.chainDown = null;
    U.chainLinks = [];
  }

  /* ── Picking: nodo bajo el cursor (barrido lineal, 555 nodos = trivial) ── */
  function _pick(mx, my) {
    let best = -1, bestD = 1e9;
    for (let i = 0; i < U.nodes.length; i++) {
      const dx = U.sx[i] - mx, dy = U.sy[i] - my;
      const d = dx * dx + dy * dy;
      const hit = Math.max(U.sr[i] + 4, 9);
      if (d < hit * hit && d < bestD) { bestD = d; best = i; }
    }
    return best;
  }

  /* ── Frame ── */
  function _frame(ts) {
    if (!U.active) return;
    // redraw() invoca _frame de forma sincrónica para UN repintado: en ese caso
    // NO reprogramar rAF (crearía loops paralelos). El loop normal sí lo hace.
    if (!U.inRedraw) U.raf = requestAnimationFrame(_frame);
    if (!U.ctx) return;
    if (!_ensureSized()) { _startSizeWatch(); return; }

    const dt = Math.min(((ts - (U.lastTs || ts)) || 16) / 1000, 0.1);
    U.lastTs = ts;
    U.elapsed += dt;
    // monitor de rendimiento: si el equipo no llega a ~22 fps → modo ligero
    U.frameEMA = U.frameEMA * 0.95 + dt * 1000 * 0.05;
    U.lite = U.frameEMA > 45;

    // easing de cámara/zoom (y animación de focus)
    if (U.camTo) {
      U.cam.x += (U.camTo.x - U.cam.x) * 0.10;
      U.cam.y += (U.camTo.y - U.cam.y) * 0.10;
      if (Math.abs(U.camTo.x - U.cam.x) + Math.abs(U.camTo.y - U.cam.y) < 0.5) U.camTo = null;
    }
    U.zoom += (U.zoomTo - U.zoom) * 0.16;

    const ctx = U.ctx, w = U.w, h = U.h;
    ctx.setTransform(U.dpr, 0, 0, U.dpr, 0, 0);

    try {
      // 1) fondo cacheado (estrellas + nebulosas)
      if (U.bg) ctx.drawImage(U.bg, 0, 0, w, h);
      else { ctx.fillStyle = '#05070e'; ctx.fillRect(0, 0, w, h); }

      const cx = w / 2, cy = h / 2, zoom = U.zoom;
      const tGlobal = U.elapsed;

      // 2) posiciones de pantalla por capa (parallax + deriva lenta)
      const zScale = Math.pow(zoom, 0.85);
      const drift = U.lite ? [[0, 0], [0, 0], [0, 0]] : LAYERS.map((L, li) => [
        Math.cos(tGlobal * 0.045 + li * 2.1) * (5 + li * 4),
        Math.sin(tGlobal * 0.038 + li * 1.7) * (4 + li * 3),
      ]);
      for (let i = 0; i < U.nodes.length; i++) {
        const L = LAYERS[U.layer[i]], d = drift[U.layer[i]];
        const k = zoom * L.par;
        U.sx[i] = cx + (U.wx[i] + d[0] - U.cam.x) * k;
        U.sy[i] = cy + (U.wy[i] + d[1] - U.cam.y) * k;
        U.sr[i] = Math.max(1.6, Math.min(40, U.baseR[i] * zScale * L.scale));
      }

      // 3) links base: curvas bezier sutiles, batched por bucket
      const dimmed = !!U.chainSet;
      ctx.lineWidth = 1;
      ctx.lineCap = 'round';
      for (let b = 0; b < U.buckets.length; b++) {
        const bk = U.buckets[b];
        ctx.strokeStyle = bk.hex;
        ctx.globalAlpha = dimmed ? 0.03 : bk.alpha;
        ctx.beginPath();
        const P = bk.pairs;
        for (let p = 0; p < P.length; p += 2) {
          const a = P[p], z = P[p + 1];
          const x1 = U.sx[a], y1 = U.sy[a], x2 = U.sx[z], y2 = U.sy[z];
          // culling barato: fuera de pantalla por ambos extremos → no dibujar
          if ((x1 < -60 && x2 < -60) || (x1 > w + 60 && x2 > w + 60) ||
              (y1 < -60 && y2 < -60) || (y1 > h + 60 && y2 > h + 60)) continue;
          ctx.moveTo(x1, y1);
          if (U.lite) { ctx.lineTo(x2, y2); continue; }
          const dx = x2 - x1, dy = y2 - y1;
          const lift = (Math.abs(dx) + Math.abs(dy)) * 0.09;
          ctx.quadraticCurveTo((x1 + x2) / 2, (y1 + y2) / 2 - lift, x2, y2);
        }
        ctx.stroke();
      }

      // 3b) cadena resaltada encima (decenas de curvas, no miles)
      if (U.chainLinks.length) {
        ctx.lineWidth = 1.5;
        for (let ci = 0; ci < U.chainLinks.length; ci++) {
          const [a, z, col] = U.chainLinks[ci];
          const x1 = U.sx[a], y1 = U.sy[a], x2 = U.sx[z], y2 = U.sy[z];
          ctx.strokeStyle = col;
          ctx.globalAlpha = 0.6;
          ctx.beginPath();
          ctx.moveTo(x1, y1);
          const lift = (Math.abs(x2 - x1) + Math.abs(y2 - y1)) * 0.09;
          ctx.quadraticCurveTo((x1 + x2) / 2, (y1 + y2) / 2 - lift, x2, y2);
          ctx.stroke();
        }
        ctx.lineWidth = 1;
      }

      // 4) nodos: sprites con glow pre-renderizados, capa lejana → cercana
      for (let oi = 0; oi < U.order.length; oi++) {
        const i = U.order[oi];
        const x = U.sx[i], y = U.sy[i], r = U.sr[i];
        if (x < -50 || x > w + 50 || y < -50 || y > h + 50) continue;
        let hex = U.color[i];
        let alpha = LAYERS[U.layer[i]].alpha;
        if (U.chainSet) {
          if (i === U.selected)          { alpha = 1; }
          else if (U.chainUp.has(i))     { hex = CHAIN_UP; alpha = 1; }
          else if (U.chainDown.has(i))   { hex = CHAIN_DOWN; alpha = 1; }
          else                           { alpha = 0.10; }
        } else if (i === U.hovered) {
          alpha = 1;
        }
        ctx.globalAlpha = alpha;
        const S = r * 4;   // el sprite incluye el glow (disco sólido ≈ r)
        ctx.drawImage(_sprite(hex), x - S / 2, y - S / 2, S, S);
      }

      // 5) anillo del seleccionado (pulso)
      if (U.selected != null) {
        const i = U.selected;
        const pr = U.sr[i] + 5 + Math.sin(tGlobal * 3) * 1.5;
        ctx.globalAlpha = 0.9;
        ctx.strokeStyle = '#00E0FF';
        ctx.lineWidth = 1.4;
        ctx.beginPath();
        ctx.arc(U.sx[i], U.sy[i], pr, 0, 6.2832);
        ctx.stroke();
        ctx.lineWidth = 1;
      }

      // 6) etiquetas — LOD: top ~40 + cadena + hover (medidas cacheadas)
      if (zoom > 0.5) {
        ctx.font = '500 11px "Archivo", sans-serif';
        ctx.textAlign = 'center';
        let drawn = 0;
        const zoomIn = zoom > 1.35;
        const maxLabels = U.lite ? 45 : 120;
        for (let oi = U.order.length - 1; oi >= 0 && drawn < maxLabels; oi--) {
          const i = U.order[oi];
          const inChain = U.chainSet && U.chainSet.has(i);
          const want = inChain || i === U.hovered || i === U.selected ||
            (!U.chainSet && (U.top40.has(i) || (zoomIn && U.sr[i] >= 8)));
          if (!want) continue;
          const x = U.sx[i], y = U.sy[i];
          if (x < 10 || x > w - 10 || y < 14 || y > h - 6) continue;
          const lc = U.labelCache[i];
          const ly = y - U.sr[i] - 6;
          ctx.globalAlpha = (U.chainSet && !inChain && i !== U.hovered) ? 0.15 : 0.9;
          ctx.fillStyle = 'rgba(4,7,14,0.85)';           // sombra dura (legibilidad)
          ctx.fillText(lc.text, x + 1, ly + 1);
          ctx.fillStyle = U.color[i];
          ctx.fillText(lc.text, x, ly);
          drawn++;
        }
      }

      ctx.globalAlpha = 1;
      U.failCount = 0;
    } catch (e) {
      // dibujo inmortal: si algo revienta, no morir en bucle infinito
      U.failCount++;
      if (U.failCount > 30) {
        pause();
        try { if (window._diag) window._diag('universe2d_fail', { err: String(e && e.message || e).slice(0, 120) }); } catch (e2) {}
      }
    }
  }

  /* ── Interacción ── */
  function _clientXY(e) {
    const rect = U.canvas.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }
  function _zoomAt(mx, my, factor) {
    const z0 = U.zoomTo;
    const z1 = Math.max(0.3, Math.min(4.5, z0 * factor));
    // el punto del mundo bajo el cursor (capa media) queda fijo
    U.cam.x += (mx - U.w / 2) * (1 / z0 - 1 / z1);
    U.cam.y += (my - U.h / 2) * (1 / z0 - 1 / z1);
    U.camTo = null;
    U.zoomTo = z1;
  }
  function _bindEvents() {
    const cv = U.canvas;
    _listen(cv, 'mousedown', e => {
      U.drag = true; U.moved = false;
      U.prev = { x: e.clientX, y: e.clientY };
      U.camTo = null;
      e.preventDefault();
    });
    _listen(window, 'mousemove', e => {
      if (U.drag) {
        const dx = e.clientX - U.prev.x, dy = e.clientY - U.prev.y;
        if (Math.abs(dx) + Math.abs(dy) > 2) U.moved = true;
        U.cam.x -= dx / U.zoom;
        U.cam.y -= dy / U.zoom;
        U.prev = { x: e.clientX, y: e.clientY };
        _hideTip(true);
        return;
      }
      if (e.target !== cv) return;
      const m = _clientXY(e);
      const hit = _pick(m.x, m.y);
      if (hit !== U.hovered) {
        U.hovered = hit;
        cv.style.cursor = hit >= 0 ? 'pointer' : 'grab';
      }
      if (hit >= 0 && !U.tipPinned) _showTip(hit, e.clientX, e.clientY);
      else if (hit < 0) _hideTip(false);
    });
    _listen(window, 'mouseup', e => {
      if (!U.drag) return;
      U.drag = false;
      if (U.moved || e.target !== cv) return;
      // clic limpio: resaltar cadena + tooltip anclado / clic al vacío = limpiar
      const m = _clientXY(e);
      const hit = _pick(m.x, m.y);
      if (hit >= 0) {
        _highlightChain(hit);
        U.tipPinned = true;
        _showTip(hit, e.clientX, e.clientY);
      } else {
        _clearChain();
        _hideTip(true);
      }
    });
    _listen(cv, 'dblclick', e => {
      const m = _clientXY(e);
      const hit = _pick(m.x, m.y);
      if (hit >= 0 && typeof window.jumpTo === 'function') {
        try { window.jumpTo(U.nodes[hit].id); } catch (e2) {}
      }
      e.preventDefault();
    });
    _listen(cv, 'wheel', e => {
      const m = _clientXY(e);
      _zoomAt(m.x, m.y, Math.exp(-e.deltaY * 0.0012));
      _hideTip(true);
    }, { passive: true });
    _listen(cv, 'contextmenu', e => e.preventDefault());

    // táctil: 1 dedo = pan · 2 dedos = pellizco (zoom)
    _listen(cv, 'touchstart', e => {
      e.preventDefault();
      U.camTo = null;
      if (e.touches.length === 1) {
        U.drag = true; U.moved = false;
        U.prev = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      } else if (e.touches.length === 2) {
        U.drag = false;
        U.pinch = Math.hypot(e.touches[1].clientX - e.touches[0].clientX,
                             e.touches[1].clientY - e.touches[0].clientY);
      }
    }, { passive: false });
    _listen(cv, 'touchmove', e => {
      e.preventDefault();
      if (e.touches.length === 1 && U.drag) {
        const dx = e.touches[0].clientX - U.prev.x, dy = e.touches[0].clientY - U.prev.y;
        if (Math.abs(dx) + Math.abs(dy) > 3) U.moved = true;
        U.cam.x -= dx / U.zoom;
        U.cam.y -= dy / U.zoom;
        U.prev = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      } else if (e.touches.length === 2) {
        const d = Math.hypot(e.touches[1].clientX - e.touches[0].clientX,
                             e.touches[1].clientY - e.touches[0].clientY);
        if (U.pinch) {
          const rect = cv.getBoundingClientRect();
          const mx = (e.touches[0].clientX + e.touches[1].clientX) / 2 - rect.left;
          const my = (e.touches[0].clientY + e.touches[1].clientY) / 2 - rect.top;
          _zoomAt(mx, my, d / U.pinch);
        }
        U.pinch = d;
      }
    }, { passive: false });
    _listen(cv, 'touchend', e => {
      e.preventDefault();
      if (e.touches.length === 0) {
        if (U.drag && !U.moved && e.changedTouches.length === 1) {
          const rect = cv.getBoundingClientRect();
          const hit = _pick(e.changedTouches[0].clientX - rect.left,
                            e.changedTouches[0].clientY - rect.top);
          if (hit >= 0) {
            _highlightChain(hit);
            U.tipPinned = true;
            _showTip(hit, e.changedTouches[0].clientX, e.changedTouches[0].clientY);
          } else { _clearChain(); _hideTip(true); }
        }
        U.drag = false;
        U.pinch = 0;
      }
    }, { passive: false });

    // rAF con pausa cuando la pestaña está oculta (regla del repo)
    _listen(document, 'visibilitychange', () => {
      if (document.hidden) {
        if (U.raf) { cancelAnimationFrame(U.raf); U.raf = 0; }
      } else if (U.active && !U.raf) {
        U.lastTs = 0;
        U.raf = requestAnimationFrame(_frame);
      }
    });
    _listen(window, 'resize', () => { if (!_ensureSized()) _startSizeWatch(); });
  }

  /* ── API pública ── */
  function init(canvasId) {
    const base = document.getElementById(canvasId || 'graph-canvas');
    if (!base) return false;
    if (U.inited && U.canvas) { resume(); return true; }

    // Un canvas solo admite UN tipo de contexto: si el 3D ya reclamó WebGL en
    // este canvas, getContext('2d') devuelve null → creamos un gemelo 2D
    // encima (mismo padre, mismos estilos) y dibujamos ahí.
    let ctx = null;
    try { ctx = base.getContext('2d'); } catch (e) {}
    if (ctx) {
      U.canvas = base;
      U.ownCanvas = false;
    } else {
      let twin = document.getElementById((canvasId || 'graph-canvas') + '-2d');
      if (!twin) {
        twin = document.createElement('canvas');
        twin.id = (canvasId || 'graph-canvas') + '-2d';
        twin.style.cssText = base.style.cssText ||
          'position:absolute;inset:0;width:100%;height:100%;z-index:5;';
        if (base.parentElement) base.parentElement.insertBefore(twin, base.nextSibling);
        else document.body.appendChild(twin);
      }
      twin.style.display = 'block';
      try { ctx = twin.getContext('2d'); } catch (e) {}
      if (!ctx) return false;   // ni así: este navegador no puede dibujar nada
      U.canvas = twin;
      U.ownCanvas = true;
    }
    U.baseCanvas = base;
    U.ctx = U.canvas.getContext('2d');
    U.inited = true;
    U.active = true;
    U.failCount = 0;

    if (!_ensureSized()) _startSizeWatch();
    try {
      if (typeof ResizeObserver !== 'undefined' && !U.ro) {
        U.ro = new ResizeObserver(() => { if (!_ensureSized()) _startSizeWatch(); });
        U.ro.observe(U.canvas);
        if (U.canvas.parentElement) U.ro.observe(U.canvas.parentElement);
      }
    } catch (e) {}

    _bindEvents();
    _ensureBadge();
    _showHint();
    U.canvas.style.cursor = 'grab';

    if (U.raf) cancelAnimationFrame(U.raf);
    U.lastTs = 0;
    U.raf = requestAnimationFrame(_frame);

    _sendDiag();
    return true;
  }

  function pause() {
    U.active = false;
    if (U.raf) { cancelAnimationFrame(U.raf); U.raf = 0; }
    _hideTip(true);
  }

  function resume() {
    if (!U.inited) return;
    if (!U.active) {
      U.active = true;
      U.lastTs = 0;
      if (!U.raf) U.raf = requestAnimationFrame(_frame);
    }
    _ensureBadge();   // refresca el idioma del aviso si LANG cambió
    if (!_ensureSized()) _startSizeWatch();
  }

  function focus(nodeId) {
    const i = U.idToIdx.get(nodeId);
    if (i == null) return false;
    _highlightChain(i);
    U.camTo = { x: U.wx[i], y: U.wy[i] };
    U.zoomTo = Math.max(U.zoomTo, 1.6);
    _hideTip(true);
    return true;
  }

  function destroy() {
    pause();
    U.handlers.forEach(([tg, ty, fn, op]) => { try { tg.removeEventListener(ty, fn, op); } catch (e) {} });
    U.handlers = [];
    try { if (U.ro) { U.ro.disconnect(); U.ro = null; } } catch (e) {}
    try { if (U.badge) { U.badge.remove(); U.badge = null; } } catch (e) {}
    try { if (U.tip) { U.tip.remove(); U.tip = null; } } catch (e) {}
    try { if (U.hint) { U.hint.remove(); U.hint = null; } } catch (e) {}
    try {
      if (U.ctx) { U.ctx.setTransform(1, 0, 0, 1, 0, 0); U.ctx.clearRect(0, 0, U.canvas.width, U.canvas.height); }
      if (U.ownCanvas && U.canvas) U.canvas.style.display = 'none';   // el gemelo se oculta, no se borra (re-init barato)
    } catch (e) {}
    U.inited = false;
    U.canvas = null; U.ctx = null; U.baseCanvas = null;
    U.hovered = -1;
    _clearChain();
  }

  // Pinta UN frame de forma sincrónica (repintado tras resize/visibility sin
  // esperar a rAF; también permite verificar el dibujo en entornos donde rAF
  // está estrangulado, p.ej. un panel de preview con document.hidden).
  function redraw() {
    if (!U.inited || !U.ctx) return false;
    U.inRedraw = true;
    try { _frame((typeof performance !== 'undefined' && performance.now) ? performance.now() : 0); return true; }
    catch (e) { return false; }
    finally { U.inRedraw = false; }
  }

  window.KhipuUniverse2D = {
    init, loadData, destroy, pause, resume, focus, redraw,
    isActive: () => !!(U.inited && U.active),
  };
})();
