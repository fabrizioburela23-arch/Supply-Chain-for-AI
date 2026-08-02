// engine/globe.js — MOTOR GLOBO UNIFICADO (Track A, Fase 1 del prompt 2026-08).
// Fusión de engine/geoglobe.js + engine/planetarium.js: el boilerplate Three.js
// (escena/cámara/luces/starfield/drag/zoom táctil/resize/animate/Tierra con
// texturas /vendor) estaba duplicado casi línea a línea en dos WebGL contexts.
// Ahora se escribe UNA vez; las diferencias son CAPAS: 'companies' (empresas
// por NRS + arcos + chokepoints + etiquetas) y 'satellites' (constelaciones
// SGP4 en vivo). Compatibilidad: window.KhipuGeoGlobe y window.Planetarium
// quedan como alias finos — los llamadores de app.html no cambian (burn-in;
// geoglobe.js/planetarium.js quedan en el repo sin cargarse hasta la limpieza).
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
  const nrsColor = (n) => n < 40 ? 0xf87171 : n < 60 ? 0xf59e0b : 0x34d399;

  // Chokepoints del globo (la Sala de Situación 2D tiene los suyos con score
  // vivo; estos son los marcadores 3D decorativos del globo, como siempre).
  const CHOKEPOINTS = [
    { name: 'Estrecho de Taiwán', lat: 24.5, lon: 120.8, risk: 'crítico' },
    { name: 'Estrecho de Malaca', lat: 2.7, lon: 101.4, risk: 'alto' },
    { name: 'Estrecho de Ormuz', lat: 26.6, lon: 56.3, risk: 'alto' },
    { name: 'Canal de Suez', lat: 30.0, lon: 32.35, risk: 'medio' },
    { name: 'Canal de Panamá', lat: 9.1, lon: -79.7, risk: 'medio' },
  ];

  class KhipuGlobe {
    constructor(canvasId, opts) {
      this.canvasId = canvasId;
      this.modes = ((opts && opts.layers) || ['companies']);
      this._sat = this.modes.includes('satellites');
      this._raf = null; this._drag = false; this._moved = false;
      this._last = { x: 0, y: 0 };
      this._rot = this._sat ? { x: 0.2, y: 0 } : { x: 0.15, y: -1.2 };
      this._dist = this._sat ? 320 : 300;
      this._zoomLim = this._sat ? [150, 900] : [140, 800];
      this.nodePos = []; this.nodeRef = [];
      this.layers = []; this._lastProp = 0; this._filter = null;
      this.constellations = [];
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
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      this.renderer.setSize(w, h, false);

      this.world = new THREE.Group();
      this.scene.add(this.world);

      // Tierra (texturas /vendor con fallback al azul sólido)
      const mat = new THREE.MeshPhongMaterial({ color: 0x3a6bb0, emissive: 0x21406b, shininess: this._sat ? 16 : 18 });
      this.earth = new THREE.Mesh(new THREE.SphereGeometry(R, 64, 64), mat);
      this.world.add(this.earth);
      const loader = new THREE.TextureLoader(); loader.setCrossOrigin('anonymous');
      loader.load(TEX + 'earth-blue-marble.jpg',
        t => { mat.map = t; mat.emissiveMap = t; mat.color.set(0xffffff); mat.emissive.set(0x9aa6b8); mat.needsUpdate = true; },
        undefined, () => {});
      loader.load(TEX + 'earth-topology.png',
        t => { mat.bumpMap = t; mat.bumpScale = this._sat ? 1.2 : 1.4; mat.needsUpdate = true; }, undefined, () => {});

      // Halo(s) — el modo empresas lleva doble halo (look original de geoglobe)
      if (this._sat) {
        this.world.add(new THREE.Mesh(new THREE.SphereGeometry(R * 1.025, 48, 48),
          new THREE.MeshBasicMaterial({ color: 0x4a90e2, transparent: true, opacity: 0.12, side: THREE.BackSide })));
      } else {
        this.world.add(new THREE.Mesh(new THREE.SphereGeometry(R * 1.04, 48, 48),
          new THREE.MeshBasicMaterial({ color: 0x5aa0e6, transparent: true, opacity: 0.28, side: THREE.BackSide })));
        this.world.add(new THREE.Mesh(new THREE.SphereGeometry(R * 1.12, 48, 48),
          new THREE.MeshBasicMaterial({ color: 0x3a78c8, transparent: true, opacity: 0.10, side: THREE.BackSide })));
      }

      this.scene.add(new THREE.AmbientLight(0xffffff, this._sat ? 1.15 : 1.25));
      const sun = new THREE.DirectionalLight(0xffffff, this._sat ? 0.7 : 0.55);
      sun.position.set(-1, this._sat ? 0.4 : 0.5, 1).multiplyScalar(this._sat ? 500 : 400);
      this.scene.add(sun);
      this.scene.add(this._stars());

      this.raycaster = new THREE.Raycaster();
      this.raycaster.params.Points.threshold = this._sat ? 2.2 : 2.6;
      this._bind(); this._resize();
      window.addEventListener('resize', this._resizeBound = () => this._resize());
      this._animate();
      return this;
    }

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
        sizeAttenuation: false, transparent: true, opacity: this._sat ? 0.7 : 0.6 }));
    }

    // ── CAPA EMPRESAS (ex geoglobe.loadData) ────────────────────────────────
    loadCompanies() {
      const NODES = window.NODES || [], LINKS = window.LINKS || [], GC = window.GeoCoords;
      if (!GC) { console.warn('[Globe] GeoCoords no disponible'); return; }
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

      const arcs = new THREE.Group();
      const lid = v => (typeof v === 'object' && v !== null) ? v.id : v;
      [...LINKS].sort((a, b) => (b.w || 0) - (a.w || 0)).slice(0, 200).forEach(l => {
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

    _textSprite(text) {
      const c = document.createElement('canvas'); c.width = 256; c.height = 64;
      const ctx = c.getContext('2d');
      ctx.font = 'bold 30px Inter, system-ui, sans-serif';
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.lineWidth = 5; ctx.strokeStyle = 'rgba(2,8,20,.85)'; ctx.strokeText(text, 128, 34);
      ctx.fillStyle = '#eaf2ff'; ctx.fillText(text, 128, 34);
      const spr = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false }));
      spr.scale.set(26, 6.5, 1);
      return spr;
    }

    // ── CAPA SATÉLITES (ex planetarium.loadConstellations) ─────────────────
    loadSatellites(data) {
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
        const pts = new THREE.Points(g, new THREE.PointsMaterial({
          color: new THREE.Color(c.color || '#9bd1ff'),
          size: c.name === 'Estaciones (ISS/CSS)' ? 6 : 2.4,
          sizeAttenuation: true, transparent: true, opacity: 0.95 }));
        pts.userData.layerIdx = this.layers.length;
        this.world.add(pts);
        this.layers.push({ name: c.name, color: c.color, node: c.node, count: c.count,
          points: pts, satrecs, positions, geom: g, visible: true });
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
                v = latLng(lat, lon, R + altKm * KM);
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

    // ── interacción compartida (mouse + táctil, feedback tablet) ───────────
    _bind() {
      const c = this.canvas, lim = this._zoomLim;
      c.addEventListener('mousedown', e => { this._drag = true; this._moved = false; this._last = { x: e.clientX, y: e.clientY }; });
      window.addEventListener('mouseup', () => { this._drag = false; });
      window.addEventListener('mousemove', e => {
        if (!this._drag) return;
        const dx = e.clientX - this._last.x, dy = e.clientY - this._last.y;
        if (Math.abs(dx) + Math.abs(dy) > 3) this._moved = true;
        this._rot.y += dx * 0.005; this._rot.x = Math.max(-1.3, Math.min(1.3, this._rot.x + dy * 0.005));
        this._last = { x: e.clientX, y: e.clientY };
      });
      c.addEventListener('wheel', e => { e.preventDefault(); this._dist = Math.max(lim[0], Math.min(lim[1], this._dist + e.deltaY * 0.4)); }, { passive: false });
      c.addEventListener('click', e => { if (!this._moved) this._pick(e); });
      let _pinch = 0;
      c.addEventListener('touchstart', e => {
        if (e.touches.length === 1) { this._drag = true; this._moved = false; this._last = { x: e.touches[0].clientX, y: e.touches[0].clientY }; }
        else if (e.touches.length === 2) { this._drag = false; _pinch = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY); }
      }, { passive: false });
      c.addEventListener('touchmove', e => {
        e.preventDefault();
        if (e.touches.length === 2 && _pinch) {
          const d = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
          this._dist = Math.max(lim[0], Math.min(lim[1], this._dist + (_pinch - d) * 0.9)); _pinch = d;
        } else if (this._drag && e.touches.length === 1) {
          const dx = e.touches[0].clientX - this._last.x, dy = e.touches[0].clientY - this._last.y;
          if (Math.abs(dx) + Math.abs(dy) > 3) this._moved = true;
          this._rot.y += dx * 0.005; this._rot.x = Math.max(-1.3, Math.min(1.3, this._rot.x + dy * 0.005));
          this._last = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        }
      }, { passive: false });
      c.addEventListener('touchend', e => {
        if (this._drag && !this._moved && e.changedTouches.length) this._pick(e.changedTouches[0]);
        this._drag = false; _pinch = 0;
      });
    }

    _pick(e) {
      const rect = this.canvas.getBoundingClientRect();
      const m = new THREE.Vector2(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
      this.raycaster.setFromCamera(m, this.camera);
      // capa empresas → mismo CustomEvent de siempre (renderGeoInfoCard intacto)
      if (this.nodePoints) {
        const hits = this.raycaster.intersectObject(this.nodePoints);
        if (hits.length) {
          const node = this.nodeRef[hits[0].index];
          if (node) {
            const g = window.GeoCoords.geoCoord(node);
            const nrs = typeof computeNRS === 'function' ? computeNRS(node.id) : 55;
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
      if (!this.canvas) return;
      const w = this.canvas.clientWidth || 900, h = this.canvas.clientHeight || (this._sat ? 480 : 560);
      this.camera.aspect = w / h; this.camera.updateProjectionMatrix();
      this.renderer.setSize(w, h, false);
    }

    _animate() {
      this._raf = requestAnimationFrame(() => this._animate());
      if (!this._drag) this._rot.y += 0.0004;
      this.world.rotation.y = this._rot.y; this.world.rotation.x = this._rot.x;
      this.camera.position.set(0, 0, this._dist); this.camera.lookAt(0, 0, 0);
      if (this._sat && this.layers.length) this._propagate();
      this.renderer.render(this.scene, this.camera);
    }

    dispose() {
      if (this._raf) cancelAnimationFrame(this._raf);
      if (this._resizeBound) window.removeEventListener('resize', this._resizeBound);
      try { this.renderer.dispose(); } catch (e) {}
    }
  }

  // ── Alias de compatibilidad (burn-in): los llamadores de app.html siguen
  //    usando new KhipuGeoGlobe(...).init().loadData() y
  //    new Planetarium(...).init() + loadConstellations(data) sin cambios. ──
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
