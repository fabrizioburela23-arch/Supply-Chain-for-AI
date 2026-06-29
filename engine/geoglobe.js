// engine/geoglobe.js — Globo geopolítico 3D (Khipu Finance)
// Empresas ubicadas por región real (GeoCoords), arcos de cadena de suministro
// great-circle, chokepoints reales y coloreado por riesgo NRS.
// Three.js (global) + GeoCoords + NODES/NODE_BY_ID/LINKS/computeNRS.
// Expone window.KhipuGeoGlobe. Dispara 'khipu-geo-selected' al clic en empresa.

(function () {
  'use strict';
  const THREE = window.THREE;
  if (!THREE) { console.warn('[GeoGlobe] THREE no disponible'); return; }

  const R = 100;
  const TEX = 'https://unpkg.com/three-globe/example/img/';

  // Chokepoints reales del comercio (lat, lon, riesgo)
  const CHOKEPOINTS = [
    { name: 'Estrecho de Taiwán', lat: 24.5, lon: 120.8, risk: 'crítico' },
    { name: 'Estrecho de Malaca', lat: 2.7, lon: 101.4, risk: 'alto' },
    { name: 'Estrecho de Ormuz', lat: 26.6, lon: 56.3, risk: 'alto' },
    { name: 'Canal de Suez', lat: 30.0, lon: 32.35, risk: 'medio' },
    { name: 'Canal de Panamá', lat: 9.1, lon: -79.7, risk: 'medio' },
  ];

  const lv = (lat, lng, r) => {
    const v = window.GeoCoords.latLngToVec3(lat, lng, r);
    return new THREE.Vector3(v.x, v.y, v.z);
  };
  const nrsColor = (n) => n < 40 ? 0xf87171 : n < 60 ? 0xf59e0b : 0x34d399;

  class KhipuGeoGlobe {
    constructor(canvasId) {
      this.canvasId = canvasId;
      this._raf = null; this._drag = false; this._moved = false;
      this._last = { x: 0, y: 0 }; this._rot = { x: 0.15, y: -1.2 }; this._dist = 300;
      this.nodePos = []; this.nodeRef = [];
    }

    init() {
      const canvas = document.getElementById(this.canvasId);
      if (!canvas) return;
      if (this._inited) { this._resize(); return this; }
      this._inited = true;
      this.canvas = canvas;
      const w = canvas.clientWidth || 900, h = canvas.clientHeight || 560;

      this.scene = new THREE.Scene();
      this.camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 4000);
      this.camera.position.set(0, 0, this._dist);
      this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      this.renderer.setSize(w, h, false);

      this.world = new THREE.Group();
      this.scene.add(this.world);

      // Tierra
      const mat = new THREE.MeshPhongMaterial({ color: 0x3a6bb0, emissive: 0x21406b, shininess: 18 });
      this.earth = new THREE.Mesh(new THREE.SphereGeometry(R, 64, 64), mat);
      this.world.add(this.earth);
      const loader = new THREE.TextureLoader(); loader.setCrossOrigin('anonymous');
      // Blue Marble (color real) como principal; emissiveMap → se auto-ilumina y no queda negra
      loader.load(TEX + 'earth-blue-marble.jpg',
        t => { mat.map = t; mat.emissiveMap = t; mat.color.set(0xffffff); mat.emissive.set(0x9aa6b8); mat.needsUpdate = true; },
        undefined, () => {});
      loader.load(TEX + 'earth-topology.png',
        t => { mat.bumpMap = t; mat.bumpScale = 1.4; mat.needsUpdate = true; }, undefined, () => {});

      const halo = new THREE.Mesh(new THREE.SphereGeometry(R * 1.04, 48, 48),
        new THREE.MeshBasicMaterial({ color: 0x5aa0e6, transparent: true, opacity: 0.28, side: THREE.BackSide }));
      this.world.add(halo);
      const glow = new THREE.Mesh(new THREE.SphereGeometry(R * 1.12, 48, 48),
        new THREE.MeshBasicMaterial({ color: 0x3a78c8, transparent: true, opacity: 0.10, side: THREE.BackSide }));
      this.world.add(glow);

      this.scene.add(new THREE.AmbientLight(0xffffff, 1.25));
      const d = new THREE.DirectionalLight(0xffffff, 0.55); d.position.set(-1, 0.5, 1).multiplyScalar(400);
      this.scene.add(d);
      this.scene.add(this._stars());

      this.raycaster = new THREE.Raycaster(); this.raycaster.params.Points.threshold = 2.6;
      this._bind(); this._resize();
      window.addEventListener('resize', this._resizeBound = () => this._resize());
      this._animate();
      return this;
    }

    _stars() {
      const n = 1200, p = new Float32Array(n * 3);
      for (let i = 0; i < n; i++) {
        const u = Math.random() * 2 - 1, th = Math.random() * Math.PI * 2, r = 1400 + Math.random() * 700, s = Math.sqrt(1 - u * u);
        p[i * 3] = r * s * Math.cos(th); p[i * 3 + 1] = r * u; p[i * 3 + 2] = r * s * Math.sin(th);
      }
      const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(p, 3));
      return new THREE.Points(g, new THREE.PointsMaterial({ color: 0x88aadd, size: 1.6, sizeAttenuation: false, transparent: true, opacity: 0.6 }));
    }

    loadData() {
      const NODES = window.NODES || [], LINKS = window.LINKS || [], GC = window.GeoCoords;
      if (!GC) { console.warn('[GeoGlobe] GeoCoords no disponible'); return; }

      // ── Empresas como puntos coloreados por NRS ───────────────────────────
      const pos = [], col = [], idMap = {};
      NODES.forEach(n => {
        const g = GC.geoCoord(n);
        const v = lv(g.lat, g.lng, R * 1.006);
        idMap[n.id] = v;
        this.nodePos.push(v); this.nodeRef.push(n);
        pos.push(v.x, v.y, v.z);
        const nrs = typeof computeNRS === 'function' ? computeNRS(n.id) : 55;
        const c = new THREE.Color(nrsColor(nrs));
        col.push(c.r, c.g, c.b);
      });
      const ng = new THREE.BufferGeometry();
      ng.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
      ng.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
      this.nodePoints = new THREE.Points(ng, new THREE.PointsMaterial({
        size: 3.4, sizeAttenuation: true, vertexColors: true, transparent: true, opacity: 0.95 }));
      this.world.add(this.nodePoints);

      // ── Arcos de cadena de suministro (great-circle) ──────────────────────
      const arcs = new THREE.Group();
      const lid = v => (typeof v === 'object' && v !== null) ? v.id : v;
      const links = [...LINKS].sort((a, b) => (b.w || 0) - (a.w || 0)).slice(0, 200);
      links.forEach(l => {
        const a = idMap[lid(l.source)], b = idMap[lid(l.target)];
        if (!a || !b) return;
        const mid = a.clone().add(b).multiplyScalar(0.5).normalize().multiplyScalar(R * (1.18 + a.distanceTo(b) / (R * 6)));
        const curve = new THREE.QuadraticBezierCurve3(a, mid, b);
        const pts = curve.getPoints(22);
        const g = new THREE.BufferGeometry().setFromPoints(pts);
        const line = new THREE.Line(g, new THREE.LineBasicMaterial({ color: 0x4a9bff, transparent: true, opacity: 0.22 }));
        arcs.add(line);
      });
      this.world.add(arcs); this.arcs = arcs;

      // ── Chokepoints ───────────────────────────────────────────────────────
      const chk = new THREE.Group();
      CHOKEPOINTS.forEach(cp => {
        const v = lv(cp.lat, cp.lon, R * 1.02);
        const col2 = cp.risk === 'crítico' ? 0xff3b3b : cp.risk === 'alto' ? 0xff8c1a : 0xffd23b;
        const m = new THREE.Mesh(new THREE.SphereGeometry(2.2, 16, 16),
          new THREE.MeshBasicMaterial({ color: col2 }));
        m.position.copy(v); m.userData.cp = cp; chk.add(m);
        const ring = new THREE.Mesh(new THREE.RingGeometry(3, 4.2, 24),
          new THREE.MeshBasicMaterial({ color: col2, transparent: true, opacity: 0.5, side: THREE.DoubleSide }));
        ring.position.copy(v); ring.lookAt(0, 0, 0); chk.add(ring);
      });
      this.world.add(chk); this.chokepoints = chk;

      this._addRegionLabels();
    }

    _addRegionLabels() {
      const REGIONS = [
        ['EE.UU.', 39, -98], ['China', 33, 110], ['Taiwán', 24, 121],
        ['Japón', 37, 139], ['Corea', 37, 127], ['Europa', 50, 9],
        ['India', 22, 79], ['Israel', 31, 35],
      ];
      const grp = new THREE.Group();
      REGIONS.forEach(([name, lat, lng]) => {
        const s = this._textSprite(name);
        const v = lv(lat, lng, R * 1.13);
        s.position.copy(v);
        grp.add(s);
      });
      this.world.add(grp); this.labels = grp;
    }

    _textSprite(text) {
      const c = document.createElement('canvas'); c.width = 256; c.height = 64;
      const ctx = c.getContext('2d');
      ctx.font = 'bold 30px Inter, system-ui, sans-serif';
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.lineWidth = 5; ctx.strokeStyle = 'rgba(2,8,20,.85)'; ctx.strokeText(text, 128, 34);
      ctx.fillStyle = '#eaf2ff'; ctx.fillText(text, 128, 34);
      const tex = new THREE.CanvasTexture(c);
      const spr = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false }));
      spr.scale.set(26, 6.5, 1);
      return spr;
    }

    _bind() {
      const c = this.canvas;
      c.addEventListener('mousedown', e => { this._drag = true; this._moved = false; this._last = { x: e.clientX, y: e.clientY }; });
      window.addEventListener('mouseup', () => { this._drag = false; });
      window.addEventListener('mousemove', e => {
        if (!this._drag) return;
        const dx = e.clientX - this._last.x, dy = e.clientY - this._last.y;
        if (Math.abs(dx) + Math.abs(dy) > 3) this._moved = true;
        this._rot.y += dx * 0.005; this._rot.x = Math.max(-1.3, Math.min(1.3, this._rot.x + dy * 0.005));
        this._last = { x: e.clientX, y: e.clientY };
      });
      c.addEventListener('wheel', e => { e.preventDefault(); this._dist = Math.max(140, Math.min(800, this._dist + e.deltaY * 0.4)); }, { passive: false });
      c.addEventListener('click', e => { if (!this._moved) this._pick(e); });
    }

    _pick(e) {
      if (!this.nodePoints) return;
      const rect = this.canvas.getBoundingClientRect();
      const m = new THREE.Vector2(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
      this.raycaster.setFromCamera(m, this.camera);
      const hits = this.raycaster.intersectObject(this.nodePoints);
      if (!hits.length) return;
      const node = this.nodeRef[hits[0].index];
      if (!node) return;
      const g = window.GeoCoords.geoCoord(node);
      const nrs = typeof computeNRS === 'function' ? computeNRS(node.id) : 55;
      window.dispatchEvent(new CustomEvent('khipu-geo-selected', { detail: {
        id: node.id, label: node.label, ticker: node.ticker || node.mkt || '',
        region: g.region || g.label || node.country, nrs,
      } }));
    }

    _resize() {
      if (!this.canvas) return;
      const w = this.canvas.clientWidth || 900, h = this.canvas.clientHeight || 560;
      this.camera.aspect = w / h; this.camera.updateProjectionMatrix();
      this.renderer.setSize(w, h, false);
    }

    _animate() {
      this._raf = requestAnimationFrame(() => this._animate());
      if (!this._drag) this._rot.y += 0.0004;
      this.world.rotation.y = this._rot.y; this.world.rotation.x = this._rot.x;
      this.camera.position.set(0, 0, this._dist); this.camera.lookAt(0, 0, 0);
      this.renderer.render(this.scene, this.camera);
    }

    dispose() {
      if (this._raf) cancelAnimationFrame(this._raf);
      if (this._resizeBound) window.removeEventListener('resize', this._resizeBound);
      try { this.renderer.dispose(); } catch (e) {}
    }
  }

  window.KhipuGeoGlobe = KhipuGeoGlobe;
})();
