// engine/globe.js — MOTOR GLOBO UNIFICADO (Track A, Fase 1 del prompt 2026-08).
// Fusión de engine/geoglobe.js + engine/planetarium.js: el boilerplate Three.js
// (escena/cámara/luces/starfield/drag/zoom táctil/resize/animate/Tierra con
// texturas /vendor) estaba duplicado casi línea a línea en dos WebGL contexts.
// Ahora se escribe UNA vez; las diferencias son CAPAS: 'companies' (empresas
// por NRS + arcos + chokepoints + etiquetas) y 'satellites' (constelaciones
// SGP4 en vivo). Compatibilidad: window.KhipuGeoGlobe y window.Planetarium
// quedan como alias finos. Los dos archivos originales se borraron en Track A
// Fase 2: este es el único motor.
//
// 2026-09-30 · WORLD MONITOR (engine/worldmonitor.js): primitivas de capa
// genéricas y BATCHEADAS (un draw call por capa) — puntos de evento pulsantes
// por severidad (shader), arcos/rutas con "flujo" animado, rutas de gran
// círculo, anillos de chokepoint, rombos de fabs, bordes de países (TopoJSON),
// retícula, picking/hover unificado, focusOn(lat,lon) animado, pausa cuando el
// canvas no se ve (IntersectionObserver + document.hidden) y dispose() completo.
// Look 'monitor': Tierra oscura (earth-dark) + bordes + halo Fresnel.
//
// 2026-09-30 · SPACE MONITOR (engine/spacemonitor.js), extensiones OPCIONALES
// (sin opts todo se comporta igual que antes): init opts.fitR/opts.view,
// setFlowLines opts.colors/normalized/reverse (arcos de ascenso con un cometa
// por arco), ascentPath()/orbitPath() (trayectorias esquemáticas desde una
// plataforma real), loadSatellites(data, {monitor, altScale, pick}) (discos
// brillantes, altitud comprimida por encima de LEO, picking genérico de
// satélites vía onPick) y setSatVisible(nombre, v) por constelación.
(function () {
  'use strict';
  const THREE = window.THREE;
  if (!THREE) { console.warn('[Globe] THREE no disponible'); return; }

  const R = 100;
  const EARTH_KM = 6371;
  const KM = R / EARTH_KM;
  const TEX = ((typeof BASE !== 'undefined' && BASE) ? BASE : '') + '/vendor/';

  const latLng = (lat, lng, r) =>
    (window.GeoCoords ? window.GeoCoords.latLngToVec3(lat, lng, r)
      : (() => { const p = (90 - lat) * Math.PI / 180, t = (lng + 180) * Math.PI / 180;
        return { x: -r * Math.sin(p) * Math.cos(t), y: r * Math.cos(p), z: r * Math.sin(p) * Math.sin(t) }; })());
  const lv = (lat, lng, r) => { const v = latLng(lat, lng, r); return new THREE.Vector3(v.x, v.y, v.z); };
  // NRS: 0 = muy seguro · 100 = muy frágil (engine/explain.js): verde <35 · ámbar 35-60 · rojo >60
  const nrsColor = (n) => n > 60 ? 0xf87171 : n >= 35 ? 0xf59e0b : 0x34d399;
  // hex → [r,g,b] 0-1 SIN gestión de color (los shaders propios escriben tal cual)
  const rgb = (hex) => {
    if (typeof hex === 'string') hex = parseInt(hex.replace('#', ''), 16);
    return [((hex >> 16) & 255) / 255, ((hex >> 8) & 255) / 255, (hex & 255) / 255];
  };

  // Chokepoints decorativos del modo 'companies' clásico (el World Monitor
  // usa los de /api/world/events con score vivo).
  const CHOKEPOINTS = [
    { name: 'Estrecho de Taiwán', lat: 24.5, lon: 120.8, risk: 'crítico' },
    { name: 'Estrecho de Malaca', lat: 2.7, lon: 101.4, risk: 'alto' },
    { name: 'Estrecho de Ormuz', lat: 26.6, lon: 56.3, risk: 'alto' },
    { name: 'Canal de Suez', lat: 30.0, lon: 32.35, risk: 'medio' },
    { name: 'Canal de Panamá', lat: 9.1, lon: -79.7, risk: 'medio' },
  ];

  // ── shaders (GLSL compatible con three r128 y posteriores) ────────────────
  // uShape: 0 disco con núcleo+anillo · 1 rombo · 2 halo suave · 3 solo anillo
  const PT_VS = `
    attribute vec3 aColor; attribute float aSize; attribute float aPhase; attribute float aPulse;
    uniform float uTime; uniform float uPx; uniform float uWave;
    varying vec3 vColor; varying float vA;
    void main(){
      vColor = aColor;
      vec4 mv = modelViewMatrix * vec4(position, 1.0);
      float s = aSize;
      vA = 1.0;
      if (uWave > 0.5) {
        float k = fract(uTime * 0.45 + aPhase);
        s = aSize * (1.0 + 2.6 * k) * aPulse;
        vA = (1.0 - k) * aPulse;
      } else {
        s = aSize * (1.0 + 0.12 * sin(uTime * 2.2 + aPhase * 6.2831));
      }
      gl_PointSize = max(0.0, s * uPx * (300.0 / -mv.z));
      gl_Position = projectionMatrix * mv;
    }`;
  const PT_FS = `
    uniform float uOpacity; uniform float uShape; uniform float uWave;
    varying vec3 vColor; varying float vA;
    void main(){
      vec2 p = gl_PointCoord - 0.5;
      float d = length(p);
      float a;
      if (uWave > 0.5) {
        if (d > 0.5) discard;
        a = smoothstep(0.5, 0.44, d) * smoothstep(0.30, 0.42, d) * vA;
      } else if (uShape > 0.5 && uShape < 1.5) {
        float m = abs(p.x) + abs(p.y);
        if (m > 0.5) discard;
        a = smoothstep(0.5, 0.40, m);
      } else if (uShape > 1.5 && uShape < 2.5) {
        if (d > 0.5) discard;
        a = pow(1.0 - d * 2.0, 1.6) * 0.85;
      } else if (uShape > 2.5) {
        if (d > 0.5) discard;
        a = smoothstep(0.5, 0.42, d) * smoothstep(0.28, 0.38, d);
      } else {
        if (d > 0.5) discard;
        float core = smoothstep(0.24, 0.14, d);
        float ring = smoothstep(0.5, 0.42, d) * smoothstep(0.30, 0.38, d);
        float glow = (1.0 - smoothstep(0.0, 0.5, d)) * 0.35;
        a = max(max(core, ring * 0.9), glow);
      }
      gl_FragColor = vec4(vColor, a * uOpacity);
    }`;
  const FLOW_VS = `
    attribute vec3 aColor; attribute float aT;
    varying vec3 vColor; varying float vT;
    void main(){ vColor = aColor; vT = aT; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;
  const FLOW_FS = `
    uniform float uTime; uniform float uOpacity; uniform float uSpeed; uniform float uDash; uniform float uFlow;
    varying vec3 vColor; varying float vT;
    void main(){
      float g = 0.0;
      if (uFlow > 0.5) {
        float f = fract(vT * uDash - uTime * uSpeed);
        g = smoothstep(0.0, 0.08, f) * (1.0 - smoothstep(0.08, 0.34, f));
      }
      gl_FragColor = vec4(vColor * (0.85 + 0.9 * g), clamp(uOpacity * (0.45 + 1.6 * g), 0.0, 1.0));
    }`;
  const GLOW_VS = `
    varying vec3 vN;
    void main(){ vN = normalize(normalMatrix * normal); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;
  const GLOW_FS = `
    uniform vec3 uColor; uniform float uPow; uniform float uK;
    varying vec3 vN;
    void main(){ float i = pow(max(0.0, uK - dot(vN, vec3(0.0, 0.0, 1.0))), uPow); gl_FragColor = vec4(uColor, i); }`;

  class KhipuGlobe {
    constructor(canvasId, opts) {
      opts = opts || {};
      this.canvasId = canvasId;
      this.modes = (opts.layers || ['companies']);
      this.look = opts.look || 'classic';
      this._mon = this.look === 'monitor';
      this._sat = this.modes.includes('satellites');
      this._raf = null; this._drag = false; this._moved = false;
      this._last = { x: 0, y: 0 };
      this._rot = this._sat ? { x: 0.2, y: 0 } : { x: 0.15, y: -1.2 };
      this._dist = this._sat ? 320 : (this._mon ? 290 : 300);
      this._zoomLim = this._sat ? [150, 900] : (this._mon ? [125, 700] : [140, 800]);
      this.nodePos = []; this.nodeRef = [];
      this.layers = []; this._lastProp = 0; this._filter = null;
      this.constellations = [];
      this.gl = {};                 // capas genéricas: id → {obj, pick, items, kind}
      this.autoRotate = true;
      this.onPick = null; this.onHover = null;
      this._t0 = performance.now();
      this._handlers = [];
      this._fitR = opts.fitR || 1.12;          // radio (en R) que debe caber en pantalla (look monitor)
      this._view0 = opts.view || null;          // {lat, lon} vista inicial (look monitor)
    }

    init() {
      const canvas = document.getElementById(this.canvasId);
      if (!canvas) { console.warn('[Globe] canvas no encontrado:', this.canvasId); return this; }
      if (this._inited) { this._resize(); return this; }
      this._inited = true;
      this.canvas = canvas;
      const w = canvas.clientWidth || 900, h = canvas.clientHeight || (this._sat ? 480 : 560);

      this.scene = new THREE.Scene();
      this.camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 4000);
      this.camera.position.set(0, 0, this._dist);
      this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
      const small = Math.min(w, h) < 520;
      this._lowPower = small;
      this._px = Math.min(window.devicePixelRatio || 1, small ? 1.5 : 2);
      this.renderer.setPixelRatio(this._px);
      this.renderer.setSize(w, h, false);
      if (this._mon) {
        // encuadre: el globo entero cabe también en móvil (vertical); vista inicial
        // Europa–Oriente Medio–Asia (donde se concentra la cadena de IA)
        this._fitDist = this._fit(w, h);
        this._dist = this._fitDist;
        this._zoomLim = [125, Math.max(700, Math.round(this._fitDist * 1.4))];
        this._rot = { x: 22 * Math.PI / 180, y: Math.PI / 2 - (75 + 180) * Math.PI / 180 };
        if (this._view0) {
          this._rot = { x: Math.max(-1.3, Math.min(1.3, this._view0.lat * Math.PI / 180)),
            y: Math.PI / 2 - (this._view0.lon + 180) * Math.PI / 180 };
        }
      }

      this.world = new THREE.Group();
      this.scene.add(this.world);

      // Tierra (texturas /vendor con fallback al azul sólido / azul noche)
      const mat = this._mon
        ? new THREE.MeshPhongMaterial({ color: 0x0b1d33, emissive: 0x06101d, shininess: 6 })
        : new THREE.MeshPhongMaterial({ color: 0x3a6bb0, emissive: 0x21406b, shininess: this._sat ? 16 : 18 });
      this.earth = new THREE.Mesh(new THREE.SphereGeometry(R, 64, 64), mat);
      this.world.add(this.earth);
      const loader = new THREE.TextureLoader(); loader.setCrossOrigin('anonymous');
      this._textures = [];
      if (this._mon) {
        loader.load(TEX + 'earth-dark.jpg',
          t => { this._textures.push(t); mat.map = t; mat.color.set(0xb8c7dd); mat.emissive.set(0x0a1626); mat.needsUpdate = true; this._dirty = true; },
          undefined, () => {});
      } else {
        loader.load(TEX + 'earth-blue-marble.jpg',
          t => { this._textures.push(t); mat.map = t; mat.emissiveMap = t; mat.color.set(0xffffff); mat.emissive.set(0x9aa6b8); mat.needsUpdate = true; },
          undefined, () => {});
        loader.load(TEX + 'earth-topology.png',
          t => { this._textures.push(t); mat.bumpMap = t; mat.bumpScale = this._sat ? 1.2 : 1.4; mat.needsUpdate = true; }, undefined, () => {});
      }

      // Halo(s)
      if (this._mon) {
        const glow = new THREE.Mesh(new THREE.SphereGeometry(R * 1.13, 48, 48), new THREE.ShaderMaterial({
          vertexShader: GLOW_VS, fragmentShader: GLOW_FS, side: THREE.BackSide, transparent: true,
          depthWrite: false, blending: THREE.AdditiveBlending,
          uniforms: { uColor: { value: new THREE.Vector3(0.12, 0.55, 1.0) }, uPow: { value: 3.2 }, uK: { value: 0.72 } } }));
        this.scene.add(glow);   // en la escena (no rota con la Tierra)
        this.world.add(new THREE.Mesh(new THREE.SphereGeometry(R * 1.012, 48, 48),
          new THREE.MeshBasicMaterial({ color: 0x1b5fa8, transparent: true, opacity: 0.07, depthWrite: false })));
      } else if (this._sat) {
        this.world.add(new THREE.Mesh(new THREE.SphereGeometry(R * 1.025, 48, 48),
          new THREE.MeshBasicMaterial({ color: 0x4a90e2, transparent: true, opacity: 0.12, side: THREE.BackSide })));
      } else {
        this.world.add(new THREE.Mesh(new THREE.SphereGeometry(R * 1.04, 48, 48),
          new THREE.MeshBasicMaterial({ color: 0x5aa0e6, transparent: true, opacity: 0.28, side: THREE.BackSide })));
        this.world.add(new THREE.Mesh(new THREE.SphereGeometry(R * 1.12, 48, 48),
          new THREE.MeshBasicMaterial({ color: 0x3a78c8, transparent: true, opacity: 0.10, side: THREE.BackSide })));
      }

      this.scene.add(new THREE.AmbientLight(0xffffff, this._mon ? 1.05 : (this._sat ? 1.15 : 1.25)));
      const sun = new THREE.DirectionalLight(0xffffff, this._mon ? 0.35 : (this._sat ? 0.7 : 0.55));
      sun.position.set(-1, this._sat ? 0.4 : 0.5, 1).multiplyScalar(this._sat ? 500 : 400);
      this.scene.add(sun);
      this.scene.add(this._stars());

      this.raycaster = new THREE.Raycaster();
      this.raycaster.params.Points.threshold = this._sat ? 2.2 : 2.6;
      this._bind(); this._resize();
      this._on(window, 'resize', () => this._resize());
      if (window.ResizeObserver && canvas.parentElement) {
        this._ro = new ResizeObserver(() => { this._resize(); this._wake(); });
        this._ro.observe(canvas.parentElement);
      }
      if (window.IntersectionObserver) {
        this._io = new IntersectionObserver(es => { if (es.some(e => e.isIntersecting)) this._wake(); });
        this._io.observe(canvas);
      }
      this._on(document, 'visibilitychange', () => { if (!document.hidden) this._wake(); });
      this._animate();
      return this;
    }

    _fit(w, h) {
      const vh = 22.5 * Math.PI / 180, hh = Math.atan(Math.tan(vh) * (w / Math.max(1, h)));
      return Math.max(260, Math.min(900, R * (this._fitR || 1.12) / Math.sin(Math.min(vh, hh))));
    }

    _discTex() {
      if (this._disc) return this._disc;
      const c = document.createElement('canvas'); c.width = c.height = 64;
      const g = c.getContext('2d'), gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
      gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.55, 'rgba(255,255,255,1)');
      gr.addColorStop(0.78, 'rgba(255,255,255,.3)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
      g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
      this._disc = new THREE.CanvasTexture(c);
      (this._textures = this._textures || []).push(this._disc);
      return this._disc;
    }

    _on(target, ev, fn, opts) { target.addEventListener(ev, fn, opts); this._handlers.push([target, ev, fn, opts]); }

    _stars() {
      const n = this._sat ? 1800 : 1200, p = new Float32Array(n * 3);
      for (let i = 0; i < n; i++) {
        const u = Math.random() * 2 - 1, th = Math.random() * Math.PI * 2,
          r = (this._sat ? 1500 : 1400) + Math.random() * (this._sat ? 800 : 700), s = Math.sqrt(1 - u * u);
        p[i * 3] = r * s * Math.cos(th); p[i * 3 + 1] = r * u; p[i * 3 + 2] = r * s * Math.sin(th);
      }
      const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(p, 3));
      return new THREE.Points(g, new THREE.PointsMaterial({
        color: this._sat ? 0xaaccff : 0x88aadd, size: this._sat ? 2 : 1.6,
        sizeAttenuation: false, transparent: true, opacity: this._mon ? 0.45 : (this._sat ? 0.7 : 0.6) }));
    }

    // ── CAPA EMPRESAS (ex geoglobe.loadData) ────────────────────────────────
    // opts.monitor: puntos más discretos (el protagonista son los eventos),
    // arcos con flujo animado en UN solo draw call, sin chokepoints decorativos.
    loadCompanies(opts) {
      opts = opts || {};
      const NODES = window.NODES || [], LINKS = window.LINKS || [], GC = window.GeoCoords;
      if (!GC) { console.warn('[Globe] GeoCoords no disponible'); return; }
      this.nodePos = []; this.nodeRef = [];
      const pos = [], col = [], idMap = {};
      NODES.forEach(n => {
        const g = GC.geoCoord(n);
        const v = lv(g.lat, g.lng, R * 1.006);
        idMap[n.id] = v;
        this.nodePos.push(v); this.nodeRef.push(n);
        pos.push(v.x, v.y, v.z);
        const nrs = typeof computeNRS === 'function' ? computeNRS(n.id) : 50;
        const c = new THREE.Color(nrsColor(nrs));
        col.push(c.r, c.g, c.b);
      });
      const ng = new THREE.BufferGeometry();
      ng.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
      ng.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
      this.nodePoints = new THREE.Points(ng, new THREE.PointsMaterial(opts.monitor
        ? { size: 2.5, sizeAttenuation: true, vertexColors: true, transparent: true, opacity: 0.85, depthWrite: false,
          map: this._discTex(), alphaTest: 0.04 }
        : { size: 3.4, sizeAttenuation: true, vertexColors: true, transparent: true, opacity: 0.95, depthWrite: false }));
      this.world.add(this.nodePoints);
      this._nodeIdMap = idMap;

      const lid = v => (typeof v === 'object' && v !== null) ? v.id : v;
      const top = [...LINKS].sort((a, b) => (b.w || 0) - (a.w || 0)).slice(0, opts.monitor ? 260 : 200);
      if (opts.monitor) {
        const segs = [];
        top.forEach(l => {
          const a = idMap[lid(l.source)], b = idMap[lid(l.target)];
          if (!a || !b || a.distanceTo(b) < 1) return;
          const mid = a.clone().add(b).multiplyScalar(0.5).normalize().multiplyScalar(R * (1.12 + a.distanceTo(b) / (R * 5)));
          segs.push(new THREE.QuadraticBezierCurve3(a, mid, b).getPoints(24));
        });
        this.setFlowLines('arcs', segs, { color: 0x4a9bff, opacity: 0.2, speed: 0.22, dash: 1 / 60 });
        this.arcs = this.gl.arcs && this.gl.arcs.obj;
        return;
      }
      const arcs = new THREE.Group();
      top.forEach(l => {
        const a = idMap[lid(l.source)], b = idMap[lid(l.target)];
        if (!a || !b) return;
        const mid = a.clone().add(b).multiplyScalar(0.5).normalize().multiplyScalar(R * (1.18 + a.distanceTo(b) / (R * 6)));
        const g = new THREE.BufferGeometry().setFromPoints(new THREE.QuadraticBezierCurve3(a, mid, b).getPoints(22));
        arcs.add(new THREE.Line(g, new THREE.LineBasicMaterial({ color: 0x4a9bff, transparent: true, opacity: 0.22 })));
      });
      this.world.add(arcs); this.arcs = arcs;

      const chk = new THREE.Group();
      CHOKEPOINTS.forEach(cp => {
        const v = lv(cp.lat, cp.lon, R * 1.02);
        const c2 = cp.risk === 'crítico' ? 0xff3b3b : cp.risk === 'alto' ? 0xff8c1a : 0xffd23b;
        const m = new THREE.Mesh(new THREE.SphereGeometry(2.2, 16, 16), new THREE.MeshBasicMaterial({ color: c2 }));
        m.position.copy(v); m.userData.cp = cp; chk.add(m);
        const ring = new THREE.Mesh(new THREE.RingGeometry(3, 4.2, 24),
          new THREE.MeshBasicMaterial({ color: c2, transparent: true, opacity: 0.5, side: THREE.DoubleSide }));
        ring.position.copy(v); ring.lookAt(0, 0, 0); chk.add(ring);
      });
      this.world.add(chk); this.chokepoints = chk;

      const REGIONS = [['EE.UU.', 39, -98], ['China', 33, 110], ['Taiwán', 24, 121], ['Japón', 37, 139],
        ['Corea', 37, 127], ['Europa', 50, 9], ['India', 22, 79], ['Israel', 31, 35]];
      const grp = new THREE.Group();
      REGIONS.forEach(([name, lat, lng]) => {
        const s = this._textSprite(name); s.position.copy(lv(lat, lng, R * 1.13)); grp.add(s);
      });
      this.world.add(grp); this.labels = grp;
    }

    // Re-colorea las empresas (p.ej. tras _invalidateNRS) sin reconstruir.
    recolorCompanies() {
      if (!this.nodePoints) return;
      const c = this.nodePoints.geometry.attributes.color, tmp = new THREE.Color();
      this.nodeRef.forEach((n, i) => {
        tmp.set(nrsColor(typeof computeNRS === 'function' ? computeNRS(n.id) : 50));
        c.setXYZ(i, tmp.r, tmp.g, tmp.b);
      });
      c.needsUpdate = true;
    }

    _textSprite(text, opts) {
      opts = opts || {};
      const font = (opts.weight || 'bold') + ' ' + (opts.px || 30) + 'px Inter, system-ui, sans-serif';
      const c = document.createElement('canvas');
      let ctx = c.getContext('2d');
      ctx.font = font;
      // ancho según el texto (antes 256 px fijos → nombres largos salían cortados)
      c.width = Math.max(256, Math.ceil(ctx.measureText(text).width + 28)); c.height = 64;
      ctx = c.getContext('2d');
      ctx.font = font;
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.lineWidth = 5; ctx.strokeStyle = 'rgba(2,8,20,.85)'; ctx.strokeText(text, c.width / 2, 34);
      ctx.fillStyle = opts.color || '#eaf2ff'; ctx.fillText(text, c.width / 2, 34);
      const spr = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false }));
      const h = (opts.w || 26) / 4;
      spr.scale.set(h * c.width / 64, h, 1);
      return spr;
    }

    // ── PRIMITIVAS GENÉRICAS (World Monitor) ───────────────────────────────
    _drop(id) {
      const L = this.gl[id];
      if (!L) return;
      (L.objs || [L.obj]).forEach(o => {
        if (!o) return;
        (o.parent || this.world).remove(o);
        o.traverse && o.traverse(ch => {
          if (ch.geometry) ch.geometry.dispose();
          if (ch.material) { if (ch.material.map) ch.material.map.dispose(); ch.material.dispose(); }
        });
      });
      delete this.gl[id];
    }

    // Puntos pulsantes (1 draw call + 1 para la onda). items: [{lat,lon,color,size,pulse?,alt?}]
    setPoints(id, items, opts) {
      opts = opts || {};
      this._drop(id);
      const n = items.length;
      if (!n) { this.gl[id] = { obj: null, items: [], kind: 'points', visible: true }; return; }
      const pos = new Float32Array(n * 3), col = new Float32Array(n * 3), size = new Float32Array(n),
        phase = new Float32Array(n), pulse = new Float32Array(n);
      const vecs = [];
      items.forEach((it, i) => {
        const v = lv(it.lat, it.lon, R * (1 + (it.alt != null ? it.alt : (opts.alt != null ? opts.alt : 0.012))));
        vecs.push(v);
        pos[i * 3] = v.x; pos[i * 3 + 1] = v.y; pos[i * 3 + 2] = v.z;
        const c = rgb(it.color != null ? it.color : (opts.color != null ? opts.color : 0xffffff));
        col[i * 3] = c[0]; col[i * 3 + 1] = c[1]; col[i * 3 + 2] = c[2];
        size[i] = it.size || opts.size || 6;
        phase[i] = ((i * 0.6180339) % 1);
        pulse[i] = it.pulse ? 1 : 0;
      });
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      g.setAttribute('aColor', new THREE.BufferAttribute(col, 3));
      g.setAttribute('aSize', new THREE.BufferAttribute(size, 1));
      g.setAttribute('aPhase', new THREE.BufferAttribute(phase, 1));
      g.setAttribute('aPulse', new THREE.BufferAttribute(pulse, 1));
      const mk = (wave) => new THREE.ShaderMaterial({
        vertexShader: PT_VS, fragmentShader: PT_FS, transparent: true, depthWrite: false,
        blending: opts.additive === false ? THREE.NormalBlending : THREE.AdditiveBlending,
        uniforms: { uTime: { value: 0 }, uPx: { value: this._px || 1 }, uWave: { value: wave ? 1 : 0 },
          uOpacity: { value: opts.opacity != null ? opts.opacity : 0.95 }, uShape: { value: opts.shape || 0 } } });
      const pts = new THREE.Points(g, mk(false));
      pts.renderOrder = opts.renderOrder || 5;
      this.world.add(pts);
      const objs = [pts];
      if (items.some(it => it.pulse)) {
        const wave = new THREE.Points(g, mk(true));
        wave.renderOrder = (opts.renderOrder || 5) - 1;
        this.world.add(wave); objs.push(wave);
      }
      this.gl[id] = { obj: pts, objs, items, vecs, kind: 'points', visible: true, pickable: opts.pickable !== false,
        hitPx: opts.hitPx || 9 };
    }

    // Líneas con "flujo" animado: segs = [[Vector3…], …] o [[[lat,lon]…]…] (gc=true)
    // opts.colors[si] = color por línea · opts.normalized: aT va 0→1 en cada
    // línea (con dash 1 = UN cometa por línea) · opts.reverse: cabeza del cometa
    // al frente (sentido de avance = del primer punto al último).
    setFlowLines(id, segs, opts) {
      opts = opts || {};
      this._drop(id);
      const P = [], C = [], T = [];
      const c0 = rgb(opts.color != null ? opts.color : 0x4a9bff);
      segs.forEach((pts, si) => {
        const c = opts.colors && opts.colors[si] != null ? rgb(opts.colors[si]) : c0;
        let total = 0;
        if (opts.normalized) for (let i = 1; i < pts.length; i++) total += pts[i - 1].distanceTo(pts[i]);
        const off = opts.normalized ? ((si * 0.37) % 1) : 0;
        let acc = opts.normalized ? 0 : (si * 37) % 97;           // desfase por línea: los cometas no van sincronizados
        for (let i = 1; i < pts.length; i++) {
          const a = pts[i - 1], b = pts[i];
          const d = a.distanceTo(b);
          P.push(a.x, a.y, a.z, b.x, b.y, b.z);
          C.push(c[0], c[1], c[2], c[0], c[1], c[2]);
          if (opts.normalized) {
            const t0 = total ? acc / total : 0, t1 = total ? (acc + d) / total : 1;
            if (opts.reverse) T.push(1 - t0 + off, 1 - t1 + off); else T.push(t0 + off, t1 + off);
          } else T.push(acc, acc + d);
          acc += d;
        }
      });
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
      g.setAttribute('aColor', new THREE.Float32BufferAttribute(C, 3));
      g.setAttribute('aT', new THREE.Float32BufferAttribute(T, 1));
      const m = new THREE.ShaderMaterial({ vertexShader: FLOW_VS, fragmentShader: FLOW_FS, transparent: true,
        depthWrite: false, blending: THREE.AdditiveBlending,
        uniforms: { uTime: { value: 0 }, uOpacity: { value: opts.opacity != null ? opts.opacity : 0.5 },
          uSpeed: { value: (opts.speed != null ? opts.speed : 0.25) * (opts.reverse ? -1 : 1) }, uDash: { value: opts.dash || (1 / 50) },
          uFlow: { value: opts.flow === false ? 0 : 1 } } });
      const ls = new THREE.LineSegments(g, m);
      ls.renderOrder = opts.renderOrder || 3;
      this.world.add(ls);
      this.gl[id] = { obj: ls, kind: 'lines', visible: true, pickable: false };
    }

    // Rutas de gran círculo entre waypoints [lat,lon] (rutas marítimas, cables).
    greatCircle(path, alt, stepDeg) {
      const out = [], r = R * (1 + (alt || 0.004)), step = (stepDeg || 2) * Math.PI / 180;
      for (let i = 1; i < path.length; i++) {
        const a = lv(path[i - 1][0], path[i - 1][1], 1), b = lv(path[i][0], path[i][1], 1);
        const ang = a.angleTo(b), n = Math.max(1, Math.ceil(ang / step));
        for (let k = (i === 1 ? 0 : 1); k <= n; k++) {
          const t = k / n;
          // slerp
          const s = Math.sin(ang);
          const v = s < 1e-6 ? a.clone() : a.clone().multiplyScalar(Math.sin((1 - t) * ang) / s)
            .add(b.clone().multiplyScalar(Math.sin(t * ang) / s));
          out.push(v.normalize().multiplyScalar(r));
        }
      }
      return out;
    }
    // Trayectoria de ascenso ESQUEMÁTICA desde una plataforma: sigue el gran
    // círculo con rumbo headingDeg durante downrangeDeg grados mientras sube
    // hasta altFrac (fracción de R). No es la trayectoria real del vehículo.
    _tangents(lat, lon) {
      const p = lv(lat, lon, 1).normalize();
      const n = lv(Math.min(89.99, lat + 0.01), lon, 1).normalize().sub(p).normalize();
      const e = new THREE.Vector3().crossVectors(n, p).normalize();
      // e = norte × radial → apunta al este en el sistema de latLng (se verifica con un punto al este)
      const east = lv(lat, lon + 0.01, 1).normalize().sub(p);
      if (east.dot(e) < 0) e.negate();
      return { p, n, e };
    }
    ascentPath(lat, lon, headingDeg, downrangeDeg, altFrac, steps) {
      const { p, n, e } = this._tangents(lat, lon);
      const h = headingDeg * Math.PI / 180, dr = downrangeDeg * Math.PI / 180, k = steps || 48;
      const dir = n.clone().multiplyScalar(Math.cos(h)).add(e.clone().multiplyScalar(Math.sin(h)));
      const out = [];
      for (let i = 0; i <= k; i++) {
        const t = i / k;
        const th = dr * Math.pow(t, 1.5);
        const alt = 0.008 + altFrac * Math.pow(Math.sin(t * Math.PI / 2), 0.75);
        out.push(p.clone().multiplyScalar(Math.cos(th)).add(dir.clone().multiplyScalar(Math.sin(th))).multiplyScalar(R * (1 + alt)));
      }
      return out;
    }
    // Círculo orbital (plano del gran círculo que pasa por la plataforma con ese rumbo).
    orbitPath(lat, lon, headingDeg, altFrac, steps) {
      const { p, n, e } = this._tangents(lat, lon);
      const h = headingDeg * Math.PI / 180, k = steps || 160;
      const dir = n.clone().multiplyScalar(Math.cos(h)).add(e.clone().multiplyScalar(Math.sin(h)));
      const out = [];
      for (let i = 0; i <= k; i++) {
        const th = 2 * Math.PI * i / k;
        out.push(p.clone().multiplyScalar(Math.cos(th)).add(dir.clone().multiplyScalar(Math.sin(th))).multiplyScalar(R * (1 + altFrac)));
      }
      return out;
    }
    setPaths(id, paths, opts) {
      opts = opts || {};
      this.setFlowLines(id, paths.map(p => this.greatCircle(p, opts.alt, opts.step)), opts);
    }

    // Anillos pulsantes (chokepoints): items [{lat,lon,color,scale?}]
    setRings(id, items, opts) {
      opts = opts || {};
      this._drop(id);
      const grp = new THREE.Group(), cores = [];
      items.forEach((it, i) => {
        const v = lv(it.lat, it.lon, R * 1.014);
        const c = new THREE.Color(it.color);
        const sc = it.scale || 1;
        const core = new THREE.Mesh(new THREE.SphereGeometry(1.25 * sc, 12, 12),
          new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: 0.95, depthWrite: false }));
        core.position.copy(v); core.userData.idx = i; grp.add(core); cores.push(core);
        [0, 1].forEach(k => {
          const ring = new THREE.Mesh(new THREE.RingGeometry(2.2 * sc, 2.9 * sc, 40),
            new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: 0.6, side: THREE.DoubleSide, depthWrite: false }));
          ring.position.copy(v); ring.lookAt(0, 0, 0);
          ring.userData.ph = (i * 0.37 + k * 0.5) % 1; ring.userData.pulse = true;
          grp.add(ring);
        });
      });
      grp.renderOrder = 6;
      this.world.add(grp);
      this.gl[id] = { obj: grp, items, cores, vecs: items.map(it => lv(it.lat, it.lon, R * 1.014)),
        kind: 'rings', visible: true, pickable: opts.pickable !== false, hitPx: 13 };
    }

    // Etiquetas (sprites) — pocas: nombres de chokepoints/regiones.
    setLabels(id, items, opts) {
      opts = opts || {};
      this._drop(id);
      const grp = new THREE.Group();
      items.forEach(it => {
        const s = this._textSprite(it.text, { color: it.color || opts.color, px: opts.px || 26, w: opts.w || 22, weight: '600' });
        s.position.copy(lv(it.lat, it.lon, R * (1 + (opts.alt || 0.07))));
        grp.add(s);
      });
      this.world.add(grp);
      this.gl[id] = { obj: grp, kind: 'labels', visible: true, pickable: false };
    }

    // Bordes de países (TopoJSON world-atlas): TODOS los arcos en un LineSegments.
    setBorders(topo, opts) {
      opts = opts || {};
      this._drop('borders');
      if (!topo || !topo.arcs) return;
      const tr = topo.transform, sx = tr ? tr.scale[0] : 1, sy = tr ? tr.scale[1] : 1,
        tx = tr ? tr.translate[0] : 0, ty = tr ? tr.translate[1] : 0;
      const P = [], r = R * 1.0025;
      topo.arcs.forEach(arc => {
        let x = 0, y = 0, prev = null;
        arc.forEach(p => {
          if (tr) { x += p[0]; y += p[1]; } else { x = p[0]; y = p[1]; }
          const lon = x * sx + tx, lat = y * sy + ty;
          const v = lv(lat, lon, r);
          if (prev && Math.abs(prev.lon - lon) < 180) P.push(prev.v.x, prev.v.y, prev.v.z, v.x, v.y, v.z);
          prev = { v, lon };
        });
      });
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
      const ls = new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: opts.color || 0x3b82c4,
        transparent: true, opacity: opts.opacity != null ? opts.opacity : 0.55, depthWrite: false }));
      ls.renderOrder = 2;
      this.world.add(ls);
      this.gl.borders = { obj: ls, kind: 'lines', visible: true, pickable: false };
    }

    setGraticule(stepDeg, opts) {
      opts = opts || {};
      this._drop('graticule');
      const P = [], r = R * 1.0015, st = stepDeg || 30;
      for (let lat = -90 + st; lat < 90; lat += st) {
        for (let lon = -180; lon < 180; lon += 3) {
          const a = lv(lat, lon, r), b = lv(lat, lon + 3, r); P.push(a.x, a.y, a.z, b.x, b.y, b.z);
        }
      }
      for (let lon = -180; lon < 180; lon += st) {
        for (let lat = -88; lat < 88; lat += 3) {
          const a = lv(lat, lon, r), b = lv(Math.min(88, lat + 3), lon, r); P.push(a.x, a.y, a.z, b.x, b.y, b.z);
        }
      }
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
      const ls = new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: opts.color || 0x2a4d7a,
        transparent: true, opacity: opts.opacity != null ? opts.opacity : 0.16, depthWrite: false }));
      this.world.add(ls);
      this.gl.graticule = { obj: ls, kind: 'lines', visible: true, pickable: false };
    }

    setLayerVisible(id, v) {
      if (id === 'companies') { if (this.nodePoints) this.nodePoints.visible = !!v; this._companiesVisible = !!v; return; }
      const L = this.gl[id];
      if (!L) return;
      L.visible = !!v;
      (L.objs || [L.obj]).forEach(o => { if (o) o.visible = !!v; });
    }

    // Gira el globo para traer (lat,lon) al frente, con animación.
    focusOn(lat, lon, opts) {
      opts = opts || {};
      const ry0 = Math.PI / 2 - (lon + 180) * Math.PI / 180;
      const rx = Math.max(-1.3, Math.min(1.3, lat * Math.PI / 180));
      const k = Math.round((this._rot.y - ry0) / (2 * Math.PI));
      const ry = ry0 + 2 * Math.PI * k;
      const dist = opts.dist != null ? Math.max(this._zoomLim[0], Math.min(this._zoomLim[1], opts.dist)) : this._dist;
      this._tween = { t0: performance.now(), dur: opts.duration || 900,
        from: { x: this._rot.x, y: this._rot.y, d: this._dist }, to: { x: rx, y: ry, d: dist } };
      this.autoRotate = false;
      this._wake();
    }
    resetView() {
      this._tween = { t0: performance.now(), dur: 900, from: { x: this._rot.x, y: this._rot.y, d: this._dist },
        to: { x: 0.35, y: this._rot.y, d: this._mon ? (this._fitDist || 290) : 300 } };
      this.autoRotate = true;
      this._wake();
    }

    // ── CAPA SATÉLITES (ex planetarium.loadConstellations) ─────────────────
    // opts (opcional): monitor → discos brillantes aditivos · altScale(km)→km
    // mostrado (p.ej. comprimir MEO/GEO para que quepan) · pick → los satélites
    // entran al picking genérico (onPick/onHover) como layer 'satellites'.
    loadSatellites(data, opts) {
      opts = opts || {};
      this._satOpts = opts;
      this._satPick = !!opts.pick;
      this.constellations = data.constellations || [];
      this.meta = data;
      const byC = {};
      (data.sats || []).forEach(s => { (byC[s.c] = byC[s.c] || []).push(s); });
      this.layers.forEach(l => this.world.remove(l.points));
      this.layers = [];
      this.constellations.forEach((c, idx) => {
        const list = byC[idx] || [];
        if (!list.length) return;
        const satrecs = list.map(s => {
          let rec = null;
          if (window.satellite) { try { rec = window.satellite.twoline2satrec(s.l1, s.l2); } catch (e) { rec = null; } }
          return { rec, name: s.n, raw: s };
        });
        const positions = new Float32Array(satrecs.length * 3);
        const g = new THREE.BufferGeometry();
        g.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        const station = c.name === 'Estaciones (ISS/CSS)';
        const pts = new THREE.Points(g, new THREE.PointsMaterial(opts.monitor
          ? { color: new THREE.Color(c.color || '#9bd1ff'), size: station ? 5.5 : (opts.size || 2.1),
            sizeAttenuation: true, transparent: true, opacity: 0.95, depthWrite: false,
            map: this._discTex(), alphaTest: 0.03, blending: THREE.AdditiveBlending }
          : { color: new THREE.Color(c.color || '#9bd1ff'), size: station ? 6 : 2.4,
            sizeAttenuation: true, transparent: true, opacity: 0.95 }));
        pts.userData.layerIdx = this.layers.length;
        this.world.add(pts);
        this.layers.push({ name: c.name, color: c.color, node: c.node, count: c.count,
          points: pts, satrecs, positions, geom: g, visible: true, idx });
      });
      this._lastProp = 0;
      this._propagate(true);
    }

    _propagate(force) {
      const now = Date.now();
      if (!force && now - this._lastProp < 1200) return;
      this._lastProp = now;
      const date = new Date();
      let gmst = 0;
      if (window.satellite) { try { gmst = window.satellite.gstime(date); } catch (e) {} }
      this.layers.forEach(layer => {
        const p = layer.positions, recs = layer.satrecs;
        for (let i = 0; i < recs.length; i++) {
          let v = null;
          if (recs[i].rec && window.satellite) {
            try {
              const pv = window.satellite.propagate(recs[i].rec, date);
              if (pv && pv.position) {
                const geo = window.satellite.eciToGeodetic(pv.position, gmst);
                const lat = geo.latitude * 180 / Math.PI, lon = geo.longitude * 180 / Math.PI, altKm = geo.height;
                recs[i].tel = { lat, lon, altKm,
                  vel: pv.velocity ? Math.sqrt(pv.velocity.x ** 2 + pv.velocity.y ** 2 + pv.velocity.z ** 2) : 0 };
                v = latLng(lat, lon, R + (this._satOpts && this._satOpts.altScale ? this._satOpts.altScale(altKm) : altKm) * KM);
              }
            } catch (e) { v = null; }
          }
          if (!v) {
            const seed = (i * 97 + layer.name.length * 13);
            const lat = ((seed * 1.7) % 160) - 80;
            const lon = ((seed * 3.3 + now / 2000) % 360) - 180;
            v = latLng(lat, lon, R + 35);
            recs[i].tel = { lat, lon, altKm: 550, vel: 7.5 };
          }
          p[i * 3] = v.x; p[i * 3 + 1] = v.y; p[i * 3 + 2] = v.z;
        }
        layer.geom.attributes.position.needsUpdate = true;
        layer.geom.computeBoundingSphere();
      });
    }

    setFilter(name) {
      this._filter = name;
      this.layers.forEach(l => { l.points.visible = !name || l.name === name; });
    }
    // Visibilidad por constelación (nombre o índice en data.constellations).
    setSatVisible(name, v) {
      this.layers.forEach(l => { if (l.name === name || l.idx === name) { l.points.visible = !!v; l.visible = !!v; } });
      this._wake();
    }

    // ── interacción compartida (mouse + táctil, feedback tablet) ───────────
    _bind() {
      const c = this.canvas, lim = this._zoomLim;
      const rotBy = (dx, dy) => {
        const k = 0.005 * Math.min(1.4, Math.max(0.45, this._dist / 300));   // más fino con zoom
        this._rot.y += dx * k; this._rot.x = Math.max(-1.3, Math.min(1.3, this._rot.x + dy * k));
        this._tween = null;
        this._wake();
      };
      this._on(c, 'mousedown', e => { this._drag = true; this._moved = false; this._last = { x: e.clientX, y: e.clientY }; });
      this._on(window, 'mouseup', () => { this._drag = false; });
      this._on(window, 'mousemove', e => {
        if (!this._drag) return;
        const dx = e.clientX - this._last.x, dy = e.clientY - this._last.y;
        if (Math.abs(dx) + Math.abs(dy) > 3) { this._moved = true; this.autoRotate = false; }
        rotBy(dx, dy);
        this._last = { x: e.clientX, y: e.clientY };
      });
      this._on(c, 'mousemove', e => {
        if (this._drag || !this.onHover) return;
        this._hoverEv = { clientX: e.clientX, clientY: e.clientY };
        if (this._hoverPending) return;
        this._hoverPending = true;
        setTimeout(() => {
          this._hoverPending = false;
          const ev = this._hoverEv; if (!ev || !this.onHover) return;
          const hit = this._pickGeneric(ev);
          c.style.cursor = hit ? 'pointer' : 'grab';
          this.onHover(hit, ev.clientX, ev.clientY);
        }, 45);
      });
      this._on(c, 'mouseleave', () => { this._hoverEv = null; if (this.onHover) this.onHover(null); });
      this._on(c, 'wheel', e => { e.preventDefault(); this._tween = null; this._dist = Math.max(lim[0], Math.min(lim[1], this._dist + e.deltaY * 0.4)); this._wake(); }, { passive: false });
      this._on(c, 'click', e => { if (!this._moved) this._pick(e); });
      let _pinch = 0;
      this._on(c, 'touchstart', e => {
        if (e.touches.length === 1) { this._drag = true; this._moved = false; this._last = { x: e.touches[0].clientX, y: e.touches[0].clientY }; }
        else if (e.touches.length === 2) { this._drag = false; _pinch = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY); }
      }, { passive: false });
      this._on(c, 'touchmove', e => {
        e.preventDefault();
        if (e.touches.length === 2 && _pinch) {
          const d = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
          this._dist = Math.max(lim[0], Math.min(lim[1], this._dist + (_pinch - d) * 0.9)); _pinch = d;
          this._tween = null; this._wake();
        } else if (this._drag && e.touches.length === 1) {
          const dx = e.touches[0].clientX - this._last.x, dy = e.touches[0].clientY - this._last.y;
          if (Math.abs(dx) + Math.abs(dy) > 3) { this._moved = true; this.autoRotate = false; }
          rotBy(dx, dy);
          this._last = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        }
      }, { passive: false });
      this._on(c, 'touchend', e => {
        if (this._drag && !this._moved && e.changedTouches.length) this._pick(e.changedTouches[0]);
        this._drag = false; _pinch = 0;
      });
    }

    zoomBy(f) {
      const lim = this._zoomLim;
      this._tween = { t0: performance.now(), dur: 350, from: { x: this._rot.x, y: this._rot.y, d: this._dist },
        to: { x: this._rot.x, y: this._rot.y, d: Math.max(lim[0], Math.min(lim[1], this._dist * f)) } };
      this._wake();
    }

    // Picking genérico en coordenadas de pantalla (px): el objeto visible más
    // cercano al cursor dentro de su radio de toque, SOLO del hemisferio frontal.
    _pickGeneric(e) {
      if (!this.canvas || !this.world) return null;
      const rect = this.canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      this.world.updateMatrixWorld();
      const mw = this.world.matrixWorld, cam = this.camera, limZ = (R * R) / this._dist;
      const tmp = new THREE.Vector3();
      let best = null;
      const test = (layerId, vec, idx, hitPx, kind) => {
        tmp.copy(vec).applyMatrix4(mw);
        if (tmp.z < limZ * 0.98) return;                  // cara oculta del globo
        tmp.project(cam);
        const sx = (tmp.x + 1) / 2 * rect.width, sy = (1 - tmp.y) / 2 * rect.height;
        const d = Math.hypot(sx - mx, sy - my);
        if (d <= hitPx && (!best || d < best.d)) best = { d, layer: layerId, index: idx, kind };
      };
      Object.keys(this.gl).forEach(id => {
        const L = this.gl[id];
        if (!L.visible || !L.pickable || !L.vecs) return;
        L.vecs.forEach((v, i) => test(id, v, i, L.hitPx || 9, L.kind));
      });
      if (this.nodePoints && this.nodePoints.visible !== false && this._companiesVisible !== false) {
        this.nodePos.forEach((v, i) => test('companies', v, i, 6, 'company'));
      }
      // satélites (solo si loadSatellites(…, {pick:true})): ocultos si la
      // Tierra los tapa (detrás del disco visto desde la cámara)
      if (this._satPick && this.layers.length) {
        const R2 = R * R, hit = 7;
        this.layers.forEach((layer, li) => {
          if (!layer.points.visible) return;
          const p = layer.positions;
          for (let i = 0; i < layer.satrecs.length; i++) {
            tmp.set(p[i * 3], p[i * 3 + 1], p[i * 3 + 2]).applyMatrix4(mw);
            if (tmp.z < 0 && tmp.x * tmp.x + tmp.y * tmp.y < R2) continue;
            tmp.project(cam);
            const sx = (tmp.x + 1) / 2 * rect.width, sy = (1 - tmp.y) / 2 * rect.height;
            const d = Math.hypot(sx - mx, sy - my);
            if (d <= hit && (!best || d < best.d)) best = { d, layer: 'satellites', index: i, li, kind: 'satellite' };
          }
        });
      }
      if (!best) return null;
      if (best.layer === 'companies') return { layer: 'companies', index: best.index, data: this.nodeRef[best.index] };
      if (best.layer === 'satellites') {
        const layer = this.layers[best.li], rec = layer.satrecs[best.index], tel = rec.tel || {};
        return { layer: 'satellites', index: best.index, data: { name: rec.name, constellation: layer.name,
          node: layer.node, color: layer.color, lat: tel.lat, lon: tel.lon, altKm: tel.altKm, vel: tel.vel,
          modeled: !rec.rec } };
      }
      const L = this.gl[best.layer];
      return { layer: best.layer, index: best.index, data: L.items ? L.items[best.index] : null };
    }

    _pick(e) {
      if (this.onPick) { this.onPick(this._pickGeneric(e)); return; }
      const rect = this.canvas.getBoundingClientRect();
      const m = new THREE.Vector2(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
      this.raycaster.setFromCamera(m, this.camera);
      // capa empresas → mismo CustomEvent de siempre
      if (this.nodePoints) {
        const hits = this.raycaster.intersectObject(this.nodePoints);
        if (hits.length) {
          const node = this.nodeRef[hits[0].index];
          if (node) {
            const g = window.GeoCoords.geoCoord(node);
            const nrs = typeof computeNRS === 'function' ? computeNRS(node.id) : 50;
            window.dispatchEvent(new CustomEvent('khipu-geo-selected', { detail: {
              id: node.id, label: node.label, ticker: node.ticker || node.mkt || '',
              region: g.region || g.label || node.country, nrs } }));
            return;
          }
        }
      }
      // capa satélites → mismo CustomEvent de siempre (renderSatCard intacto)
      if (this.layers.length) {
        let best = null;
        this.layers.forEach(layer => {
          if (!layer.points.visible) return;
          const hits = this.raycaster.intersectObject(layer.points);
          if (hits.length) {
            const h = hits[0];
            if (!best || h.distanceToRay < best.h.distanceToRay) best = { h, layer };
          }
        });
        if (!best) return;
        const rec = best.layer.satrecs[best.h.index];
        const tel = rec.tel || {};
        window.dispatchEvent(new CustomEvent('khipu-sat-selected', { detail: {
          name: rec.name, constellation: best.layer.name, node: best.layer.node,
          lat: tel.lat, lon: tel.lon, altKm: tel.altKm, vel: tel.vel, color: best.layer.color } }));
      }
    }

    _resize() {
      if (!this.canvas || !this.renderer) return;
      const w = this.canvas.clientWidth, h = this.canvas.clientHeight;
      if (!w || !h) return;                 // oculto: no deformar la cámara
      if (w === this._w && h === this._h) return;
      this._w = w; this._h = h;
      this.camera.aspect = w / h;
      this._applyShift();
      this.renderer.setSize(w, h, false);
    }

    // Desplaza el encuadre verticalmente (fracción de la altura): en móvil, con
    // una hoja inferior abierta, el globo sube para no quedar tapado.
    setViewShift(frac) {
      this._shiftY = frac || 0;
      this._applyShift();
      this._wake();
    }
    _applyShift() {
      if (!this.camera) return;
      const w = this._w || (this.canvas && this.canvas.clientWidth) || 1, h = this._h || (this.canvas && this.canvas.clientHeight) || 1;
      if (this._shiftY) this.camera.setViewOffset(w, h, 0, Math.round(this._shiftY * h), w, h);
      else if (this.camera.view && this.camera.view.enabled) this.camera.clearViewOffset();
      this.camera.updateProjectionMatrix();
    }

    _visible() {
      const c = this.canvas;
      return !!(c && c.isConnected && !document.hidden && c.offsetParent !== null && c.clientWidth > 0);
    }
    _wake() {
      if (this._disposed || !this._inited) return;
      if (this._raf == null && !this._paused) this._animate();
    }
    pause() { this._paused = true; if (this._raf != null) cancelAnimationFrame(this._raf); this._raf = null; }
    resume() { this._paused = false; this._resize(); this._wake(); }

    _animate() {
      if (this._disposed || this._paused) { this._raf = null; return; }
      if (!this._visible()) { this._raf = null; return; }   // dormir: IntersectionObserver/visibilitychange lo despiertan
      this._raf = requestAnimationFrame(() => this._animate());
      const now = performance.now();
      if (this._lowPower && this._lastFrame && now - this._lastFrame < 30) return;   // ~30 fps en móvil
      this._lastFrame = now;
      if (this._tween) {
        const tw = this._tween, k = Math.min(1, (now - tw.t0) / tw.dur);
        const e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
        this._rot.x = tw.from.x + (tw.to.x - tw.from.x) * e;
        this._rot.y = tw.from.y + (tw.to.y - tw.from.y) * e;
        this._dist = tw.from.d + (tw.to.d - tw.from.d) * e;
        if (k >= 1) this._tween = null;
      } else if (!this._drag && this.autoRotate) {
        this._rot.y += this._mon ? 0.0006 : 0.0004;
      }
      this.world.rotation.y = this._rot.y; this.world.rotation.x = this._rot.x;
      this.camera.position.set(0, 0, this._dist); this.camera.lookAt(0, 0, 0);
      if (this._sat && this.layers.length) this._propagate();
      const t = (now - this._t0) / 1000;
      Object.keys(this.gl).forEach(id => {
        const L = this.gl[id];
        if (!L.visible) return;
        (L.objs || [L.obj]).forEach(o => {
          if (o && o.material && o.material.uniforms && o.material.uniforms.uTime) o.material.uniforms.uTime.value = t;
        });
        if (L.kind === 'rings' && L.obj) {
          L.obj.children.forEach(ch => {
            if (!ch.userData.pulse) return;
            const f = (t * 0.5 + ch.userData.ph) % 1;
            const s = 1 + 1.4 * f;
            ch.scale.set(s, s, s);
            ch.material.opacity = 0.75 * (1 - f);
          });
        }
      });
      this.renderer.render(this.scene, this.camera);
    }

    dispose() {
      this._disposed = true;
      if (this._raf != null) cancelAnimationFrame(this._raf);
      this._raf = null;
      this._handlers.forEach(([t, ev, fn, o]) => { try { t.removeEventListener(ev, fn, o); } catch (e) {} });
      this._handlers = [];
      try { this._ro && this._ro.disconnect(); } catch (e) {}
      try { this._io && this._io.disconnect(); } catch (e) {}
      try {
        this.scene && this.scene.traverse(o => {
          if (o.geometry) o.geometry.dispose();
          if (o.material) {
            (Array.isArray(o.material) ? o.material : [o.material]).forEach(m => { if (m.map) m.map.dispose(); m.dispose(); });
          }
        });
        (this._textures || []).forEach(t => t.dispose());
      } catch (e) {}
      try { this.renderer.dispose(); if (this.renderer.forceContextLoss) this.renderer.forceContextLoss(); } catch (e) {}
      this.gl = {};
    }
  }

  // ── Alias de compatibilidad (burn-in): new KhipuGeoGlobe(...).init().loadData()
  //    y new Planetarium(...).init() + loadConstellations(data) sin cambios. ──
  class KhipuGeoGlobe extends KhipuGlobe {
    constructor(canvasId) { super(canvasId, { layers: ['companies'] }); }
    loadData() { return this.loadCompanies(); }
  }
  class Planetarium extends KhipuGlobe {
    constructor(canvasId) { super(canvasId, { layers: ['satellites'] }); }
    loadConstellations(data) { return this.loadSatellites(data); }
  }

  window.KhipuGlobe = KhipuGlobe;
  window.KhipuGeoGlobe = KhipuGeoGlobe;
  window.Planetarium = Planetarium;
})();
