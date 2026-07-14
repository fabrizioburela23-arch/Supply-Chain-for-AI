// engine/planetarium.js — Planeta 3D con satélites reales (Khipu Finance)
// Three.js (r128 global) + satellite.js (SGP4) sobre su PROPIO canvas/renderer.
// Datos: /api/space/tle (CelesTrak). Posiciones propagadas en vivo.
// Expone window.Planetarium. Depende de window.THREE, window.GeoCoords.
// satellite.js (window.satellite) es opcional: sin él, usa órbitas sintéticas.

(function () {
  'use strict';
  const THREE = window.THREE;
  if (!THREE) { console.warn('[Planetarium] THREE no disponible'); return; }

  const R = 100;                 // radio del globo en unidades de mundo
  const EARTH_KM = 6371;
  const KM = R / EARTH_KM;       // escala km → mundo
  // Texturas servidas desde el propio servidor (/vendor) para no depender de CDNs
  const TEX = ((typeof BASE !== 'undefined' && BASE) ? BASE : '') + '/vendor/';

  const latLng = (lat, lng, r) =>
    (window.GeoCoords ? window.GeoCoords.latLngToVec3(lat, lng, r)
      : (() => { const p = (90 - lat) * Math.PI / 180, t = (lng + 180) * Math.PI / 180;
        return { x: -r * Math.sin(p) * Math.cos(t), y: r * Math.cos(p), z: r * Math.sin(p) * Math.sin(t) }; })());

  class Planetarium {
    constructor(canvasId) {
      this.canvasId = canvasId;
      this.constellations = [];
      this.layers = [];          // {name,color,points,satrecs,positions,visible,node}
      this._raf = null;
      this._drag = false;
      this._last = { x: 0, y: 0 };
      this._rot = { x: 0.2, y: 0 };
      this._dist = 320;
      this._lastProp = 0;
      this._filter = null;
    }

    init() {
      const canvas = document.getElementById(this.canvasId);
      if (!canvas) { console.warn('[Planetarium] canvas no encontrado:', this.canvasId); return; }
      this.canvas = canvas;
      const w = canvas.clientWidth || 900, h = canvas.clientHeight || 480;

      this.scene = new THREE.Scene();
      this.camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 4000);
      this.camera.position.set(0, 0, this._dist);

      this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      this.renderer.setSize(w, h, false);

      this.world = new THREE.Group();      // todo lo que rota junto (tierra + satélites)
      this.scene.add(this.world);

      // ── Tierra ──────────────────────────────────────────────────────────
      const geo = new THREE.SphereGeometry(R, 64, 64);
      const mat = new THREE.MeshPhongMaterial({ color: 0x3a6bb0, emissive: 0x21406b, shininess: 16 });
      this.earth = new THREE.Mesh(geo, mat);
      this.world.add(this.earth);

      const loader = new THREE.TextureLoader();
      loader.setCrossOrigin('anonymous');
      loader.load(TEX + 'earth-blue-marble.jpg',
        (t) => { mat.map = t; mat.emissiveMap = t; mat.color.set(0xffffff); mat.emissive.set(0x9aa6b8); mat.needsUpdate = true; },
        undefined, () => {/* fallback: queda el azul sólido */ });
      loader.load(TEX + 'earth-topology.png',
        (t) => { mat.bumpMap = t; mat.bumpScale = 1.2; mat.needsUpdate = true; }, undefined, () => {});

      // Halo atmosférico
      const halo = new THREE.Mesh(
        new THREE.SphereGeometry(R * 1.025, 48, 48),
        new THREE.MeshBasicMaterial({ color: 0x4a90e2, transparent: true, opacity: 0.12, side: THREE.BackSide }));
      this.world.add(halo);

      // ── Estrellas ───────────────────────────────────────────────────────
      this.scene.add(this._starfield());

      // ── Luces ───────────────────────────────────────────────────────────
      this.scene.add(new THREE.AmbientLight(0xffffff, 1.15));
      const sun = new THREE.DirectionalLight(0xffffff, 0.7);
      sun.position.set(-1, 0.4, 1).multiplyScalar(500);
      this.scene.add(sun);

      // ── Interacción ─────────────────────────────────────────────────────
      this.raycaster = new THREE.Raycaster();
      this.raycaster.params.Points.threshold = 2.2;
      this._bind();
      this._resize();
      window.addEventListener('resize', this._resizeBound = () => this._resize());

      this._animate();
      return this;
    }

    _starfield() {
      const n = 1800, pos = new Float32Array(n * 3);
      for (let i = 0; i < n; i++) {
        // distribución estable (sin Math.random crítico; aquí da igual)
        const u = Math.random() * 2 - 1, th = Math.random() * Math.PI * 2;
        const r = 1500 + Math.random() * 800, s = Math.sqrt(1 - u * u);
        pos[i * 3] = r * s * Math.cos(th); pos[i * 3 + 1] = r * u; pos[i * 3 + 2] = r * s * Math.sin(th);
      }
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      return new THREE.Points(g, new THREE.PointsMaterial({ color: 0xaaccff, size: 2, sizeAttenuation: false, transparent: true, opacity: 0.7 }));
    }

    // ── Carga de constelaciones desde /api/space/tle ──────────────────────
    loadConstellations(data) {
      this.constellations = data.constellations || [];
      this.meta = data;
      const sats = data.sats || [];
      // agrupar sats por índice de constelación
      const byC = {};
      sats.forEach(s => { (byC[s.c] = byC[s.c] || []).push(s); });

      this.layers.forEach(l => this.world.remove(l.points));
      this.layers = [];

      this.constellations.forEach((c, idx) => {
        const list = byC[idx] || [];
        if (!list.length) return;
        const satrecs = [];
        list.forEach(s => {
          let rec = null;
          if (window.satellite) {
            try { rec = window.satellite.twoline2satrec(s.l1, s.l2); } catch (e) { rec = null; }
          }
          satrecs.push({ rec, name: s.n, raw: s });
        });
        const positions = new Float32Array(satrecs.length * 3);
        const g = new THREE.BufferGeometry();
        g.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        const col = new THREE.Color(c.color || '#9bd1ff');
        const pts = new THREE.Points(g, new THREE.PointsMaterial({
          color: col, size: c.name === 'Estaciones (ISS/CSS)' ? 6 : 2.4,
          sizeAttenuation: true, transparent: true, opacity: 0.95,
        }));
        pts.userData.layerIdx = this.layers.length;
        this.world.add(pts);
        this.layers.push({ name: c.name, color: c.color, node: c.node, count: c.count,
          points: pts, satrecs, positions, geom: g, visible: true });
      });
      this._lastProp = 0;
      this._propagate(true);
    }

    // ── Propagación SGP4 (throttle ~1.2s) ─────────────────────────────────
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
                const lat = geo.latitude * 180 / Math.PI;
                const lon = geo.longitude * 180 / Math.PI;
                const altKm = geo.height;
                recs[i].tel = { lat, lon, altKm,
                  vel: pv.velocity ? Math.sqrt(pv.velocity.x ** 2 + pv.velocity.y ** 2 + pv.velocity.z ** 2) : 0 };
                v = latLng(lat, lon, R + altKm * KM);
              }
            } catch (e) { v = null; }
          }
          if (!v) {
            // órbita sintética estable si no hay satellite.js
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

    // ── Interacción mouse ─────────────────────────────────────────────────
    _bind() {
      const c = this.canvas;
      c.addEventListener('mousedown', e => { this._drag = true; this._last = { x: e.clientX, y: e.clientY }; this._moved = false; });
      window.addEventListener('mouseup', () => { this._drag = false; });
      window.addEventListener('mousemove', e => {
        if (!this._drag) return;
        const dx = e.clientX - this._last.x, dy = e.clientY - this._last.y;
        if (Math.abs(dx) + Math.abs(dy) > 3) this._moved = true;
        this._rot.y += dx * 0.005; this._rot.x += dy * 0.005;
        this._rot.x = Math.max(-1.3, Math.min(1.3, this._rot.x));
        this._last = { x: e.clientX, y: e.clientY };
      });
      c.addEventListener('wheel', e => {
        e.preventDefault();
        this._dist = Math.max(150, Math.min(900, this._dist + e.deltaY * 0.4));
      }, { passive: false });
      c.addEventListener('click', e => { if (!this._moved) this._pick(e); });
      // TÁCTIL (tablet, feedback Fabrizio): 1 dedo rota · 2 dedos pellizco→zoom · tap→selecciona.
      let _pinch = 0;
      c.addEventListener('touchstart', e => {
        if (e.touches.length === 1) { this._drag = true; this._moved = false; this._last = { x: e.touches[0].clientX, y: e.touches[0].clientY }; }
        else if (e.touches.length === 2) { this._drag = false; _pinch = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY); }
      }, { passive: false });
      c.addEventListener('touchmove', e => {
        e.preventDefault();
        if (e.touches.length === 2 && _pinch) {
          const d = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
          this._dist = Math.max(150, Math.min(900, this._dist + (_pinch - d) * 0.9)); _pinch = d;
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
      const mouse = new THREE.Vector2(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        -((e.clientY - rect.top) / rect.height) * 2 + 1);
      this.raycaster.setFromCamera(mouse, this.camera);
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
      const idx = best.h.index;
      const rec = best.layer.satrecs[idx];
      const tel = rec.tel || {};
      window.dispatchEvent(new CustomEvent('khipu-sat-selected', { detail: {
        name: rec.name, constellation: best.layer.name, node: best.layer.node,
        lat: tel.lat, lon: tel.lon, altKm: tel.altKm, vel: tel.vel, color: best.layer.color,
      } }));
    }

    _resize() {
      if (!this.canvas) return;
      const w = this.canvas.clientWidth || 900, h = this.canvas.clientHeight || 480;
      this.camera.aspect = w / h; this.camera.updateProjectionMatrix();
      this.renderer.setSize(w, h, false);
    }

    _animate() {
      this._raf = requestAnimationFrame(() => this._animate());
      // rotación suave automática + control manual
      if (!this._drag) this._rot.y += 0.0006;
      this.world.rotation.y = this._rot.y;
      this.world.rotation.x = this._rot.x;
      const d = this._dist;
      this.camera.position.set(0, 0, d);
      this.camera.lookAt(0, 0, 0);
      this._propagate(false);
      this.renderer.render(this.scene, this.camera);
    }

    dispose() {
      if (this._raf) cancelAnimationFrame(this._raf);
      if (this._resizeBound) window.removeEventListener('resize', this._resizeBound);
      try { this.renderer.dispose(); } catch (e) {}
    }
  }

  window.Planetarium = Planetarium;
})();
