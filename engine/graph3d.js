// engine/graph3d.js — Motor de visualización 3D Three.js para Khipu Finance
// Renderiza los 450+ nodos como esferas en el espacio, con tamaño por market cap,
// links de colores, raycast para hover/click, y highlight de stress-test en 3D.
//
// Depende de variables globales de app.html:
//   NODES, LINKS, NODE_BY_ID, CATS, MKT, lid, computeNodeRadius, computeNRS
// Y de helpers definidos al final de este archivo (getCatColorHex, getLinkColorHex...)

class KhipuGraph3D {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.canvas = document.getElementById('graph-canvas');
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(
      60, (this.canvas?.clientWidth || 1) / (this.canvas?.clientHeight || 1), 0.1, 10000
    );
    this.renderer = new THREE.WebGLRenderer({ canvas: this.canvas, antialias: true, alpha: true });
    this.nodeMeshes = new Map();   // id → THREE.Mesh
    this.linkLines = [];
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();
    this.selected = null;
    this.hovered = null;
    this.clock = new THREE.Clock();
    this.active = false;
    this._mouseMoved = false;
    this._prevMouse = { x: 0, y: 0 };
    this._spherical = new THREE.Spherical(600, Math.PI / 3, Math.PI / 4);
    // Group that holds all nodes + links — rotates as one brain
    this._graphGroup = new THREE.Group();
    this._target = new THREE.Vector3(0, 0, 0); // orbit/pan center
  }

  init() {
    // Canvas may have 0×0 if still display:none — use parent dimensions as fallback
    const w = this.canvas.clientWidth || this.container?.clientWidth || window.innerWidth;
    const h = this.canvas.clientHeight || this.container?.clientHeight || window.innerHeight;
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(w, h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.shadowMap.enabled = false;

    // Luces
    this.scene.add(new THREE.AmbientLight(0x223366, 0.7));
    const p1 = new THREE.PointLight(0x52B1FF, 1.5, 1400);
    p1.position.set(300, 300, 300);
    this.scene.add(p1);
    const p2 = new THREE.PointLight(0x3DE0C8, 1.0, 900);
    p2.position.set(-300, -150, 150);
    this.scene.add(p2);

    this.scene.add(this._graphGroup);
    this._addGrid();
    this._addStarfield();
    this._setupPointerControls();

    window.addEventListener('resize', () => this._onResize());
    this.canvas.addEventListener('mousemove', e => this._onMouseMove(e));
    this.canvas.addEventListener('click', e => this._onClick(e));
    this.canvas.addEventListener('wheel', e => this._onWheel(e), { passive: true });

    this.camera.position.setFromSpherical(this._spherical);
    this.camera.lookAt(0, 0, 0);

    this.active = true;
    this._animate();

    const svg = document.getElementById('graph');
    if (svg) svg.style.display = 'none';
  }

  loadData(nodes, links) {
    this.nodeMeshes.forEach(m => this._graphGroup.remove(m));
    this.linkLines.forEach(l => this._graphGroup.remove(l));
    this.nodeMeshes.clear();
    this.linkLines = [];

    nodes.forEach(n => {
      const mesh = this._createNodeMesh(n);
      this.nodeMeshes.set(n.id, mesh);
      this._graphGroup.add(mesh);
    });

    this._initForce3D(nodes, links);
  }

  _createNodeMesh(node) {
    const radius = (typeof computeNodeRadius === 'function' ? computeNodeRadius(node.id) : 0) || (node.big ? 16 : 9);
    const color = new THREE.Color(getCatColorHex(node.cat));

    const geo = node.big
      ? new THREE.IcosahedronGeometry(radius, 2)
      : new THREE.SphereGeometry(radius, 10, 8);

    const mat = new THREE.MeshPhongMaterial({
      color, emissive: color, emissiveIntensity: 0.25,
      transparent: true, opacity: 0.9, shininess: 80,
    });

    const mesh = new THREE.Mesh(geo, mat);
    mesh.userData = { nodeId: node.id, node, baseRadius: radius };

    // Anillo portfolio
    if (node.port) {
      const rc = node.port.includes('C1+C2') ? 0xA78BFF
        : node.port === 'C1' ? 0xD9A520 : 0x52B1FF;
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(radius + 3, 0.5, 8, 48),
        new THREE.MeshBasicMaterial({ color: rc, transparent: true, opacity: 0.9 })
      );
      mesh.add(ring);
    }

    // Anillo pre-IPO
    if (node.preipo) {
      const ring = new THREE.Mesh(
        new THREE.TorusGeometry(radius + 4, 0.35, 6, 32),
        new THREE.MeshBasicMaterial({ color: 0xC99BFF, transparent: true, opacity: 0.7 })
      );
      ring.rotation.x = Math.PI / 3;
      mesh.add(ring);
    }

    const label = this._makeLabel(node.label, color);
    label.position.y = radius + 6;
    mesh.add(label);

    return mesh;
  }

  _makeLabel(text, color) {
    const cv = document.createElement('canvas');
    cv.width = 256; cv.height = 56;
    const ctx = cv.getContext('2d');
    ctx.fillStyle = `#${new THREE.Color(color).getHexString()}`;
    ctx.font = '500 18px "Archivo", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const short = text.length > 15 ? text.slice(0, 14) + '…' : text;
    ctx.fillText(short, 128, 28);
    const tex = new THREE.CanvasTexture(cv);
    const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 0.85 });
    const sprite = new THREE.Sprite(mat);
    sprite.scale.set(28, 7, 1);
    return sprite;
  }

  _createLinkLine(link, nodes) {
    // O(1) lookup via NODE_BY_ID instead of O(n) find
    const nbi = (typeof NODE_BY_ID !== 'undefined') ? NODE_BY_ID : null;
    const src = nbi ? nbi[lid(link.source)] : nodes.find(n => n.id === lid(link.source));
    const dst = nbi ? nbi[lid(link.target)] : nodes.find(n => n.id === lid(link.target));
    if (!src || !dst) return null;

    const color = getLinkColorHex(link.type || 'supply');
    const geo = new THREE.BufferGeometry();
    const pos = new Float32Array(6);
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));

    const mat = new THREE.LineBasicMaterial({
      color: new THREE.Color(color), transparent: true,
      opacity: 0.28 + (link.w || 1) * 0.06,
    });

    const line = new THREE.Line(geo, mat);
    line.userData = { link, src, dst };
    return line;
  }

  _initForce3D(nodes, links) {
    links.forEach(l => {
      const line = this._createLinkLine(l, nodes);
      if (line) { this.linkLines.push(line); this._graphGroup.add(line); }
    });

    // Always use Fibonacci spherical layout for true 3D depth.
    // D3's force sim only produces 2D (x,y) positions for the SVG graph
    // and would flatten the 3D view to a plane.
    this._staticLayout(nodes);
  }

  _staticLayout(nodes) {
    // Category-cluster layout: each category gets a center on a large sphere,
    // nodes scatter within their cluster — gives genuine 3D brain-like depth.
    const catMap = {};
    nodes.forEach(n => { const c = n.cat || 'fabless'; (catMap[c] = catMap[c] || []).push(n); });
    const cats = Object.keys(catMap);
    const CLUSTER_R = 300;  // radius of cluster-center sphere
    const SCATTER   = 85;   // scatter radius within each cluster

    // Cluster centers: Fibonacci on outer sphere
    const centers = {};
    cats.forEach((cat, i) => {
      const phi   = Math.acos(-1 + (2 * i) / cats.length);
      const theta = Math.sqrt(cats.length * Math.PI) * phi;
      centers[cat] = {
        x: CLUSTER_R * Math.cos(theta) * Math.sin(phi),
        y: CLUSTER_R * Math.sin(theta) * Math.sin(phi),
        z: CLUSTER_R * Math.cos(phi),
      };
    });

    // Fast deterministic hash for consistent positions across reloads
    const hash = s => { let h = 5381; for (let i = 0; i < s.length; i++) h = (h * 33 ^ s.charCodeAt(i)) >>> 0; return h; };

    nodes.forEach(n => {
      const c  = centers[n.cat || 'fabless'] || { x: 0, y: 0, z: 0 };
      const hx = hash(n.id);
      const hy = hash(n.id + '__y');
      const hz = hash(n.id + '__z');
      n.x = c.x + ((hx & 0xFFFF) / 0xFFFF - 0.5) * 2 * SCATTER;
      n.y = c.y + ((hy & 0xFFFF) / 0xFFFF - 0.5) * 2 * SCATTER;
      n.z = c.z + ((hz & 0xFFFF) / 0xFFFF - 0.5) * 2 * SCATTER;
      const mesh = this.nodeMeshes.get(n.id);
      if (mesh) mesh.position.set(n.x, n.y, n.z);
    });
    this._updateLinkPositions();
  }

  _onSimTick(nodes) {
    nodes.forEach(n => {
      if (n.vz == null) n.vz = 0;
      const fz = -n.z * 0.005;
      n.vz = (n.vz + fz) * 0.85;
      n.z = (n.z || 0) + n.vz;
    });

    nodes.forEach(n => {
      const mesh = this.nodeMeshes.get(n.id);
      if (mesh) mesh.position.set(n.x || 0, n.y || 0, n.z || 0);
    });

    this._updateLinkPositions();
  }

  _updateLinkPositions() {
    this.linkLines.forEach(line => {
      const { src, dst } = line.userData;
      const pos = line.geometry.attributes.position.array;
      pos[0] = src.x || 0; pos[1] = src.y || 0; pos[2] = src.z || 0;
      pos[3] = dst.x || 0; pos[4] = dst.y || 0; pos[5] = dst.z || 0;
      line.geometry.attributes.position.needsUpdate = true;
    });
  }

  _applySpherical() {
    this.camera.position.setFromSpherical(this._spherical).add(this._target);
    this.camera.lookAt(this._target);
  }

  _resetView() {
    this._spherical = new THREE.Spherical(600, Math.PI / 3, Math.PI / 4);
    this._target.set(0, 0, 0);
    this._applySpherical();
  }

  _animate() {
    if (!this.active) return;
    requestAnimationFrame(() => this._animate());
    const t = this.clock.getElapsedTime();

    if (this.selected) {
      const mesh = this.nodeMeshes.get(this.selected);
      if (mesh) mesh.scale.setScalar(1 + 0.08 * Math.sin(t * 3));
    }

    // Auto-rotation: advance camera theta (not group rotation) so user orbit
    // stays continuous — no jump when the user grabs then releases the graph.
    if (!this._dragging) {
      let speed = 0.0006;
      const energy = (typeof window !== 'undefined' && window.__bixbyEnergy) || 0;
      if (energy > 0) {
        speed += energy * 0.006;
        window.__bixbyEnergy = energy * 0.94;
        this._graphGroup.scale.setScalar(1 + energy * 0.04);
      } else if (this._graphGroup.scale.x !== 1) {
        this._graphGroup.scale.setScalar(1);
      }
      this._spherical.theta += speed;
      this._applySpherical();
    }

    this.renderer.render(this.scene, this.camera);
  }

  selectNode(id) {
    if (this.selected) {
      const prev = this.nodeMeshes.get(this.selected);
      if (prev) { prev.material.emissiveIntensity = 0.25; prev.scale.setScalar(1); }
    }
    this.selected = id;
    const mesh = this.nodeMeshes.get(id);
    if (mesh) {
      mesh.material.emissiveIntensity = 1.0;
      this._flyTo(mesh.position.clone());
    }
  }

  morphNodeSize(nodeId) {
    const mesh = this.nodeMeshes.get(nodeId);
    if (!mesh) return;
    const targetR = (typeof computeNodeRadius === 'function' ? computeNodeRadius(nodeId) : 0) || mesh.userData.baseRadius;
    const currentR = mesh.userData.baseRadius || 9;
    if (Math.abs(targetR - currentR) < 0.5) return;

    mesh.userData.baseRadius = targetR;
    const newGeo = new THREE.SphereGeometry(targetR, 16, 12);
    mesh.geometry.dispose();
    mesh.geometry = newGeo;

    const perfColor = getDailyPerformanceHex(nodeId);
    if (perfColor) {
      mesh.material.emissive.setHex(perfColor);
      mesh.material.emissiveIntensity = 0.8;
      setTimeout(() => {
        mesh.material.emissive.copy(mesh.material.color);
        mesh.material.emissiveIntensity = 0.25;
      }, 2000);
    }
  }

  highlightStress(failedId, affectedSet) {
    this.nodeMeshes.forEach((mesh, id) => {
      if (id === failedId) {
        mesh.material.color.setHex(0xFF2222);
        mesh.material.emissive.setHex(0xFF0000);
        mesh.material.emissiveIntensity = 2.0;
        mesh.scale.setScalar(1.3);
      } else if (affectedSet.has(id)) {
        mesh.material.opacity = 0.85;
        mesh.material.emissiveIntensity = 0.5;
      } else {
        mesh.material.opacity = 0.12;
      }
    });
    this.linkLines.forEach(line => {
      const sl = lid(line.userData.link.source);
      const tl = lid(line.userData.link.target);
      if (sl === failedId || tl === failedId) {
        line.material.color.setHex(0xFF2222);
        line.material.opacity = 0.9;
      }
    });
  }

  resetHighlight() {
    this.nodeMeshes.forEach((mesh, id) => {
      const n = NODE_BY_ID[id];
      if (n) {
        const c = new THREE.Color(getCatColorHex(n.cat));
        mesh.material.color.copy(c);
        mesh.material.emissive.copy(c);
        mesh.material.emissiveIntensity = 0.25;
        mesh.material.opacity = 0.9;
        mesh.scale.setScalar(1);
      }
    });
    this.linkLines.forEach(line => {
      const c = new THREE.Color(getLinkColorHex(line.userData.link.type || 'supply'));
      line.material.color.copy(c);
      line.material.opacity = 0.2;
    });
  }

  _flyTo(targetPos, duration = 1100) {
    const startCam    = this.camera.position.clone();
    const startTarget = this._target.clone();
    // Approach from current direction at a comfortable distance
    const dir = startCam.clone().sub(startTarget).normalize();
    const dist = Math.min(this._spherical.radius * 0.45, 280);
    const endCam = targetPos.clone().add(dir.multiplyScalar(dist));
    const t0 = performance.now();
    const fly = () => {
      const p    = Math.min(1, (performance.now() - t0) / duration);
      const ease = 1 - Math.pow(1 - p, 3); // cubic ease-out
      this.camera.position.lerpVectors(startCam, endCam, ease);
      this._target.lerpVectors(startTarget, targetPos, ease);
      this.camera.lookAt(this._target);
      if (p < 1) {
        requestAnimationFrame(fly);
      } else {
        // Sync spherical so subsequent orbit works from new position
        const diff = this.camera.position.clone().sub(this._target);
        this._spherical.setFromVector3(diff);
      }
    };
    fly();
  }

  _setupPointerControls() {
    // ── Mouse ──────────────────────────────────────────────────────────────────
    this.canvas.addEventListener('mousedown', e => {
      this._mouseMoved = false;
      this._dragging   = true;
      this._isPan      = e.button === 2 || e.shiftKey;
      this._prevMouse  = { x: e.clientX, y: e.clientY };
      clearTimeout(this._rotResumeTimer);
      // Prevent text selection while dragging
      e.preventDefault();
    });

    this.canvas.addEventListener('mousemove', e => {
      if (!e.buttons) return;
      const dx = e.clientX - this._prevMouse.x;
      const dy = e.clientY - this._prevMouse.y;
      if (Math.abs(dx) + Math.abs(dy) > 2) {
        this._mouseMoved = true;
        if (this._isPan) {
          // Shift+drag / right-drag: pan the orbit centre
          const panSpeed = this._spherical.radius * 0.00065;
          const right = new THREE.Vector3()
            .crossVectors(
              this.camera.getWorldDirection(new THREE.Vector3()),
              new THREE.Vector3(0, 1, 0)
            ).normalize();
          this._target.addScaledVector(right, -dx * panSpeed);
          this._target.y += dy * panSpeed;
        } else {
          // Left-drag: orbit
          this._spherical.theta -= dx * 0.005;
          this._spherical.phi = Math.max(0.08, Math.min(Math.PI - 0.08,
            this._spherical.phi + dy * 0.005));
        }
        this._prevMouse = { x: e.clientX, y: e.clientY };
        this._applySpherical();
      }
    });

    this.canvas.addEventListener('mouseup', () => {
      // Resume auto-rotation 2.5 s after last interaction
      clearTimeout(this._rotResumeTimer);
      this._rotResumeTimer = setTimeout(() => { this._dragging = false; }, 2500);
    });

    // Right-click: pan mode, suppress context menu
    this.canvas.addEventListener('contextmenu', e => e.preventDefault());

    // Double-click: reset view
    this.canvas.addEventListener('dblclick', () => this._resetView());

    // ── Touch ──────────────────────────────────────────────────────────────────
    const touch = (fn) => this.canvas.addEventListener(fn.name.replace('_on', '').toLowerCase()
      .replace('touch', 'touch'), fn, { passive: false });

    this.canvas.addEventListener('touchstart', e => {
      e.preventDefault();
      this._dragging = true;
      clearTimeout(this._rotResumeTimer);
      if (e.touches.length === 1) {
        this._prevMouse = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      } else if (e.touches.length === 2) {
        this._pinchDist = Math.hypot(
          e.touches[1].clientX - e.touches[0].clientX,
          e.touches[1].clientY - e.touches[0].clientY
        );
        // Mid-point for pan reference
        this._prevMouse = {
          x: (e.touches[0].clientX + e.touches[1].clientX) / 2,
          y: (e.touches[0].clientY + e.touches[1].clientY) / 2,
        };
      }
    }, { passive: false });

    this.canvas.addEventListener('touchmove', e => {
      e.preventDefault();
      if (e.touches.length === 1) {
        const dx = e.touches[0].clientX - this._prevMouse.x;
        const dy = e.touches[0].clientY - this._prevMouse.y;
        this._spherical.theta -= dx * 0.007;
        this._spherical.phi = Math.max(0.08, Math.min(Math.PI - 0.08,
          this._spherical.phi + dy * 0.007));
        this._prevMouse = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        this._applySpherical();
      } else if (e.touches.length === 2) {
        const dist = Math.hypot(
          e.touches[1].clientX - e.touches[0].clientX,
          e.touches[1].clientY - e.touches[0].clientY
        );
        if (this._pinchDist) {
          this._spherical.radius = Math.max(80, Math.min(2200,
            this._spherical.radius + (this._pinchDist - dist) * 1.8));
          this._applySpherical();
        }
        this._pinchDist = dist;
      }
    }, { passive: false });

    this.canvas.addEventListener('touchend', e => {
      e.preventDefault();
      if (e.touches.length === 0) {
        clearTimeout(this._rotResumeTimer);
        this._rotResumeTimer = setTimeout(() => { this._dragging = false; }, 2500);
      }
    }, { passive: false });

    // ── Keyboard ───────────────────────────────────────────────────────────────
    window.addEventListener('keydown', e => {
      if (!this.active) return;
      // Only when nothing else has focus (not a text input)
      const tag = document.activeElement?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      const spd = 0.06;
      let moved = false;
      if (e.key === 'ArrowLeft')       { this._spherical.theta -= spd; moved = true; }
      if (e.key === 'ArrowRight')      { this._spherical.theta += spd; moved = true; }
      if (e.key === 'ArrowUp')         { this._spherical.phi = Math.max(0.08, this._spherical.phi - spd); moved = true; }
      if (e.key === 'ArrowDown')       { this._spherical.phi = Math.min(Math.PI - 0.08, this._spherical.phi + spd); moved = true; }
      if (e.key === '+' || e.key === '=') { this._spherical.radius = Math.max(80, this._spherical.radius - 55); moved = true; }
      if (e.key === '-')               { this._spherical.radius = Math.min(2200, this._spherical.radius + 55); moved = true; }
      if (e.key === 'r' || e.key === 'R') { this._resetView(); moved = true; }
      if (moved) {
        this._dragging = true;
        clearTimeout(this._rotResumeTimer);
        this._rotResumeTimer = setTimeout(() => { this._dragging = false; }, 2500);
        this._applySpherical();
        e.preventDefault();
      }
    });

    // Show nav hint on first activation
    this._showNavHint();
  }

  _showNavHint() {
    if (this._hintShown) return;
    this._hintShown = true;
    const hint = document.createElement('div');
    hint.style.cssText = [
      'position:absolute', 'bottom:70px', 'left:50%', 'transform:translateX(-50%)',
      'background:rgba(0,0,0,.7)', 'color:#ccc', 'font-size:11px',
      'padding:6px 14px', 'border-radius:20px', 'pointer-events:none',
      'z-index:50', 'white-space:nowrap', 'transition:opacity .5s',
      'font-family:"JetBrains Mono",monospace',
    ].join(';');
    hint.textContent = 'Arrastra · Scroll/pinch para zoom · Shift+drag para desplazar · R resetear';
    this.canvas.parentElement?.appendChild(hint);
    setTimeout(() => { hint.style.opacity = '0'; }, 3500);
    setTimeout(() => hint.remove(), 4100);
  }

  _onWheel(e) {
    this._spherical.radius = Math.max(80, Math.min(2200, this._spherical.radius + e.deltaY * 0.6));
    this._applySpherical();
  }

  _onMouseMove(e) {
    if (e.buttons) return; // skip raycasting while dragging
    const rect = this.canvas.getBoundingClientRect();
    this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.mouse, this.camera);
    const meshes = [...this.nodeMeshes.values()];
    const hits = this.raycaster.intersectObjects(meshes, false);
    const newHover = hits.length > 0 ? hits[0].object.userData.nodeId : null;
    if (newHover !== this.hovered) {
      this.hovered = newHover;
      this.canvas.style.cursor = newHover ? 'pointer' : 'grab';
    }
  }

  _onClick(e) {
    if (this._mouseMoved) return;
    if (this.hovered && typeof window.jumpTo === 'function') {
      window.jumpTo(this.hovered);
      this.selectNode(this.hovered);
    }
  }

  _addGrid() {
    const grid = new THREE.GridHelper(2400, 60, 0x1A2030, 0x1A2030);
    grid.material.opacity = 0.2;
    grid.material.transparent = true;
    grid.position.y = -240;
    this.scene.add(grid);
  }

  _addStarfield() {
    const geo = new THREE.BufferGeometry();
    const pos = new Float32Array(3000);
    for (let i = 0; i < 3000; i++) pos[i] = (Math.random() - 0.5) * 4000;
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    this.scene.add(new THREE.Points(geo,
      new THREE.PointsMaterial({ color: 0x334466, size: 0.8 })
    ));
  }

  _onResize() {
    if (!this.canvas.clientWidth) return;
    const w = this.canvas.clientWidth, h = this.canvas.clientHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  }

  pause() { this.active = false; }

  resume() {
    if (!this.active) {
      this.active = true;
      this._animate();
    }
  }

  // ── Live coloring by market performance ──────────────────────────────────────
  updateLiveColors(quotesMap) {
    // quotesMap = { ticker: { close, prev, live, pct } }
    if (!this.nodeMeshes || !this.nodeMeshes.size) return;
    this.nodeMeshes.forEach((mesh, id) => {
      const node = (typeof NODE_BY_ID !== 'undefined') ? NODE_BY_ID[id] : null;
      if (!node || !node.mkt) return;
      const q = quotesMap[node.mkt];
      if (!q) return;
      const pct = q.pct != null ? q.pct : ((q.live - q.prev) / q.prev * 100);
      if (isNaN(pct)) return;
      // color: red(-5%) -> grey(0) -> green(+5%)
      let color;
      if (pct > 3)       color = 0x00ff88;
      else if (pct > 1)  color = 0x44cc77;
      else if (pct > 0)  color = 0x229966;
      else if (pct > -1) color = 0xcc4444;
      else if (pct > -3) color = 0xff4444;
      else               color = 0xff2222;
      if (mesh.material) {
        mesh.material.color.setHex(color);
        mesh.material.emissive.setHex(color);
        mesh.material.emissiveIntensity = 0.35;
      }
      // pulse ring if > 2% move
      if (Math.abs(pct) > 2) {
        mesh.children.forEach(child => {
          if (child.isMesh && child.geometry && child.geometry.type === 'TorusGeometry') {
            child.material.color.setHex(pct > 0 ? 0x00ff88 : 0xff2222);
            child.material.opacity = 0.8;
          }
        });
      }
    });
  }

  destroy() {
    this.active = false;
    const svg = document.getElementById('graph');
    if (svg) svg.style.display = '';
  }
}

// ── Helpers de color ─────────────────────────────────────────────────────────
// getCatColorHex: devuelve el color CSS de la categoría (reutiliza catColor de app.html)
function getCatColorHex(cat) {
  if (typeof catColor === 'function') {
    try { const v = catColor(cat); if (v) return v; } catch {}
  }
  const meta = (typeof CATS !== 'undefined' && CATS[cat]) || (typeof CATS_NEW !== 'undefined' && CATS_NEW[cat]) || {};
  const val = getComputedStyle(document.documentElement)
    .getPropertyValue(meta.cssVar || '--c-fabless').trim();
  return val || '#52B1FF';
}

function getLinkColorHex(type) {
  const LINK_HEX = {
    supply:   '#4E8B1E', fab:      '#0F8C5F', license:  '#6B5DD3',
    cloud:    '#0A6CA8', invest:   '#B8880D', deploy:   '#0E7A6E',
    partner:  '#8A857A', customer: '#C25E12', owns:     '#7C3AED',
  };
  return LINK_HEX[type] || '#4E8B1E';
}

function getDailyPerformanceHex(nodeId) {
  const n = NODE_BY_ID[nodeId];
  if (!n || !n.mkt || typeof MKT === 'undefined') return null;
  const q = MKT.quotes[n.mkt];
  if (!q || q.close == null || q.prev == null) return null;
  const chg = (q.close - q.prev) / q.prev;
  if (chg > 0.03) return 0x00FF66;
  if (chg < -0.03) return 0xFF3333;
  return null;
}

window.KhipuGraph3D = KhipuGraph3D;

// Expose live-color updater — wired up when 3D graph is instantiated
// (See initKhipuCore in app.html which sets window.khipuGraph3D)
Object.defineProperty(window, '_graph3d_updateLiveColors', {
  get() {
    const g = window.khipuGraph3D;
    return g ? (q) => g.updateLiveColors(q) : null;
  },
  configurable: true,
});
