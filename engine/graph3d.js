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

    // Niebla exponencial MUY sutil, adaptativa al zoom (_animate la ajusta):
    // da profundidad sin BORRAR los nodos lejanos (feedback real: "no se
    // muestran todos los nodos, se borran si lo mueves").
    this.scene.fog = new THREE.FogExp2(0x05070e, 0.00022);

    this.scene.add(this._graphGroup);
    this._addGrid();
    this._addStarfield();
    this._setupPointerControls();

    window.addEventListener('resize', () => this._onResize());
    // El resize de ventana NO se dispara cuando un contenedor pasa de oculto
    // a visible — ResizeObserver sí. Cubre el caso "canvas nace 0×0".
    try {
      if (typeof ResizeObserver !== 'undefined') {
        this._ro = new ResizeObserver(() => this._onResize());
        this._ro.observe(this.canvas);
        if (this.canvas.parentElement) this._ro.observe(this.canvas.parentElement);
      }
    } catch (e) {}
    if (!this._ensureSized()) this._startSizeWatch();
    this.canvas.addEventListener('mousemove', e => this._onMouseMove(e));
    this.canvas.addEventListener('click', e => this._onClick(e));
    this.canvas.addEventListener('wheel', e => this._onWheel(e), { passive: true });

    this.camera.position.setFromSpherical(this._spherical);
    this.camera.lookAt(0, 0, 0);

    this.active = true;
    this._animate();

    // auto-chequeo visual: si a los 2s la pantalla sigue negra (pestaña
    // visible), degradar automáticamente — jamás dejar al usuario sin nada
    setTimeout(() => this._selfCheck(0), 2000);

    const svg = document.getElementById('graph');
    if (svg) svg.style.display = 'none';
  }

  loadData(nodes, links) {
    this.nodeMeshes.forEach(m => this._graphGroup.remove(m));
    this.nodeMeshes.clear();
    this.linkLines = [];   // legado: las aristas viven en _linkMerged (1 geometría)
    if (this._linkMerged) { this._graphGroup.remove(this._linkMerged); this._linkMerged = null; }
    if (this._flowPoints) { this._graphGroup.remove(this._flowPoints); this._flowPoints = null; }
    if (this._hlGroup) { this._graphGroup.remove(this._hlGroup); this._hlGroup = null; }
    if (this._haloPoints) { this._graphGroup.remove(this._haloPoints); this._haloPoints = null; }

    nodes.forEach(n => {
      const mesh = this._createNodeMesh(n);
      this.nodeMeshes.set(n.id, mesh);
      this._graphGroup.add(mesh);
    });

    this._initForce3D(nodes, links);
    this._buildHaloPoints();
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

    // Halo: ya NO es un sprite por nodo (555 draw calls + 555 escrituras de
    // opacity por frame). Ahora TODOS los halos viven en UNA nube de puntos
    // con shader (ver _buildHaloPoints) — el pulso lo calcula la GPU.
    mesh.userData.haloColor = color.clone();
    mesh.userData.pulsePhase = (node.id.charCodeAt(0) || 0) * 0.7; // desfase por nodo
    let nrs = 50;
    try { if (typeof computeNRS === 'function') nrs = computeNRS(node.id); } catch (e) {}
    mesh.userData.pulseSpeed = 0.8 + (nrs / 100) * 1.6;   // los frágiles laten más rápido

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
    mesh.userData.labelSprite = label;   // el LOD de etiquetas lo enciende/apaga

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

  // ── Aristas: UNA sola geometría fusionada (antes 1.623 draw calls, ahora 1).
  // Cada arista es una bezier de 10 segmentos como LineSegments con color por
  // vértice (el peso modula el brillo). El resaltado de cadena usa líneas
  // dedicadas encima (solo ~decenas), no toca la base.
  _buildLinkRecords(links, nodes) {
    const nbi = (typeof NODE_BY_ID !== 'undefined') ? NODE_BY_ID : null;
    this._linkRecs = [];
    links.forEach(link => {
      const src = nbi ? nbi[lid(link.source)] : nodes.find(n => n.id === lid(link.source));
      const dst = nbi ? nbi[lid(link.target)] : nodes.find(n => n.id === lid(link.target));
      if (!src || !dst) return;
      const hex = parseInt(getLinkColorHex(link.type || 'supply').replace('#', ''), 16) || 0x4e8b1e;
      this._linkRecs.push({ link, src, dst, hex, w: link.w || 1 });
    });
  }

  // textura compartida del halo (una sola para los 555 nodos)
  static _haloTexture() {
    if (KhipuGraph3D._haloTex) return KhipuGraph3D._haloTex;
    const cv = document.createElement('canvas');
    cv.width = cv.height = 64;
    const ctx = cv.getContext('2d');
    const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    g.addColorStop(0, 'rgba(255,255,255,0.85)');
    g.addColorStop(0.35, 'rgba(255,255,255,0.28)');
    g.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 64, 64);
    KhipuGraph3D._haloTex = new THREE.CanvasTexture(cv);
    return KhipuGraph3D._haloTex;
  }

  _initForce3D(nodes, links) {
    this._buildLinkRecords(links, nodes);

    // Always use Fibonacci spherical layout for true 3D depth.
    // D3's force sim only produces 2D (x,y) positions for the SVG graph
    // and would flatten the 3D view to a plane.
    this._staticLayout(nodes);
  }

  _staticLayout(nodes) {
    // Layout SEMÁNTICO: cada eje significa algo real.
    //  X = posición en la cadena de valor (upstream proveedor → downstream cliente)
    //  Y = riesgo NRS (frágil abajo ↔ resiliente arriba)
    //  Z = región geográfica (Asia ↔ Occidente)
    const SPAN_X = 360, SPAN_Y = 220, SPAN_Z = 320;
    const CATS_REF = (typeof CATS !== 'undefined' && CATS) ? CATS : (window.CATS || {});
    const REGION_Z = {
      Taiwan: -3, 'Taiwán': -3, China: -2.3, Corea: -1.5, Japon: -0.7, Japan: -0.7,
      India: 0.2, RestoMundo: 0.9, Israel: 1.3, EEUU: 2.1, Canada: 2.5,
      Europa: 3, Alemania: 3, Francia: 3, PaisesBajos: 3, ReinoUnido: 3, RestoEuropa: 3,
    };
    const hash = s => { let h = 5381; for (let i = 0; i < s.length; i++) h = (h * 33 ^ s.charCodeAt(i)) >>> 0; return h; };
    const jit = (seed, amp) => ((hash(seed) & 0xFFFF) / 0xFFFF - 0.5) * 2 * amp;

    nodes.forEach(n => {
      const cat = CATS_REF[n.cat];
      const catX = (cat && cat.x != null) ? cat.x : 0.5;
      let nrs = 50;
      try { if (typeof computeNRS === 'function') nrs = computeNRS(n.id); } catch (e) {}
      const zk = (REGION_Z[n.country] != null) ? REGION_Z[n.country] : 0;
      n.x = (catX - 0.5) * 2 * SPAN_X + jit(n.id + 'x', 26);
      n.y = (nrs / 100 - 0.5) * 2 * SPAN_Y + jit(n.id + 'y', 18);
      n.z = (zk / 3) * SPAN_Z + jit(n.id + 'z', 30);
      const mesh = this.nodeMeshes.get(n.id);
      if (mesh) mesh.position.set(n.x, n.y, n.z);
    });
    this._updateLinkPositions();
    // Los ejes/medidores los provee el Scatter de inversión (khipuScatter),
    // que se auto-activa al entrar a 3D. No añadimos aquí otra capa de ejes.
  }

  _updateLinkPositions() {
    // Reconstruye LA geometría fusionada de todas las aristas (bezier
    // cuadrática muestreada: punto de control = punto medio elevado).
    const SEGS = 10;
    const recs = this._linkRecs || [];
    const nSeg = recs.length * SEGS;               // segmentos totales
    const pos = new Float32Array(nSeg * 2 * 3);    // 2 vértices por segmento
    const col = new Float32Array(nSeg * 2 * 3);
    const c = new THREE.Color();
    let o = 0;
    const px = new Float32Array(SEGS + 1), py = new Float32Array(SEGS + 1), pz = new Float32Array(SEGS + 1);
    recs.forEach(rec => {
      const ax = rec.src.x || 0, ay = rec.src.y || 0, az = rec.src.z || 0;
      const bx = rec.dst.x || 0, by = rec.dst.y || 0, bz = rec.dst.z || 0;
      const dxx = bx - ax, dyy = by - ay, dzz = bz - az;
      const lift = Math.sqrt(dxx * dxx + dyy * dyy + dzz * dzz) * 0.14;
      const cx = (ax + bx) / 2, cy = (ay + by) / 2 + lift, cz = (az + bz) / 2;
      for (let i = 0; i <= SEGS; i++) {
        const t = i / SEGS, mt = 1 - t;
        px[i] = mt * mt * ax + 2 * mt * t * cx + t * t * bx;
        py[i] = mt * mt * ay + 2 * mt * t * cy + t * t * by;
        pz[i] = mt * mt * az + 2 * mt * t * cz + t * t * bz;
      }
      // el peso modula el BRILLO del color (LineBasicMaterial no tiene alpha
      // por vértice): w1 tenue → w5 vivo
      c.setHex(rec.hex).multiplyScalar(0.45 + Math.min(rec.w, 5) * 0.13);
      for (let i = 0; i < SEGS; i++) {
        pos[o] = px[i];     pos[o + 1] = py[i];     pos[o + 2] = pz[i];
        pos[o + 3] = px[i + 1]; pos[o + 4] = py[i + 1]; pos[o + 5] = pz[i + 1];
        col[o] = c.r; col[o + 1] = c.g; col[o + 2] = c.b;
        col[o + 3] = c.r; col[o + 4] = c.g; col[o + 5] = c.b;
        o += 6;
      }
    });
    if (this._linkMerged) this._graphGroup.remove(this._linkMerged);
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
    this._linkMerged = new THREE.LineSegments(geo, new THREE.LineBasicMaterial({
      vertexColors: true, transparent: true, opacity: 0.55, depthWrite: false,
    }));
    this._linkMerged.frustumCulled = false;   // el grafo entero, SIEMPRE visible
    this._graphGroup.add(this._linkMerged);
    this._buildFlowParticles();
  }

  // Partículas de FLUJO: UNA nube de puntos (antes 260 sprites = 260 draw
  // calls; ahora 1). Viajan por las aristas fuertes (w>=3).
  _buildFlowParticles() {
    if (this._flowPoints) this._graphGroup.remove(this._flowPoints);
    const strong = (this._linkRecs || []).filter(r => r.w >= 3).slice(0, 300);
    this._flowState = strong.map(rec => ({ rec, t: Math.random(), speed: 0.15 + Math.random() * 0.2 }));
    const n = this._flowState.length;
    const pos = new Float32Array(n * 3);
    const col = new Float32Array(n * 3);
    const c = new THREE.Color();
    this._flowState.forEach((f, i) => {
      c.setHex(f.rec.hex);
      col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b;
    });
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
    this._flowPoints = new THREE.Points(geo, new THREE.PointsMaterial({
      map: KhipuGraph3D._haloTexture(), vertexColors: true, size: 6,
      transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending,
      depthWrite: false, sizeAttenuation: true,
    }));
    this._flowPoints.frustumCulled = false;   // los puntos se mueven cada frame
    this._graphGroup.add(this._flowPoints);
  }

  // ── Halos GPU: UNA nube de puntos con shader (antes 555 sprites = 555
  // draw calls + 555 escrituras de opacity por frame en CPU). El pulso, el
  // hover y el tamaño en pantalla los calcula el vertex shader. ──
  _buildHaloPoints() {
    if (this._haloPoints) this._graphGroup.remove(this._haloPoints);
    const meshes = [...this.nodeMeshes.values()];
    const n = meshes.length;
    const pos = new Float32Array(n * 3);
    const col = new Float32Array(n * 3);
    const size = new Float32Array(n);
    const phase = new Float32Array(n);
    const speed = new Float32Array(n);
    const alpha = new Float32Array(n).fill(1);
    const index = new Float32Array(n);
    this._haloIndex = new Map();
    meshes.forEach((m, i) => {
      this._haloIndex.set(m.userData.nodeId, i);
      const c = m.userData.haloColor || new THREE.Color(0x00e0ff);
      col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b;
      size[i] = (m.userData.baseRadius || 9) * 3.4;
      phase[i] = m.userData.pulsePhase || 0;
      speed[i] = m.userData.pulseSpeed || 1;
      index[i] = i;
      pos[i * 3] = m.position.x; pos[i * 3 + 1] = m.position.y; pos[i * 3 + 2] = m.position.z;
    });
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('aColor', new THREE.BufferAttribute(col, 3));
    geo.setAttribute('aSize', new THREE.BufferAttribute(size, 1));
    geo.setAttribute('aPhase', new THREE.BufferAttribute(phase, 1));
    geo.setAttribute('aSpeed', new THREE.BufferAttribute(speed, 1));
    geo.setAttribute('aAlpha', new THREE.BufferAttribute(alpha, 1));
    geo.setAttribute('aIndex', new THREE.BufferAttribute(index, 1));
    this._haloMat = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uTex: { value: KhipuGraph3D._haloTexture() },
        uHover: { value: -1 },
        uScale: { value: (this.canvas.clientHeight || 800) * 0.9 },
      },
      vertexShader: [
        'attribute vec3 aColor;',
        'attribute float aSize; attribute float aPhase; attribute float aSpeed;',
        'attribute float aAlpha; attribute float aIndex;',
        'uniform float uTime; uniform float uHover; uniform float uScale;',
        'varying vec3 vColor; varying float vAlpha;',
        'void main(){',
        '  vColor = aColor;',
        '  float pulse = 0.40 + 0.22 * sin(uTime * aSpeed + aPhase);',
        '  float isHover = step(abs(aIndex - uHover), 0.5);',
        '  vAlpha = min(aAlpha * (pulse + isHover * 0.5), 0.95);',
        '  vec4 mv = modelViewMatrix * vec4(position, 1.0);',
        '  gl_PointSize = min(aSize * (1.0 + isHover * 0.35) * (uScale / -mv.z), 220.0);',
        '  gl_Position = projectionMatrix * mv;',
        '}',
      ].join('\n'),
      fragmentShader: [
        'uniform sampler2D uTex;',
        'varying vec3 vColor; varying float vAlpha;',
        'void main(){',
        '  vec4 t = texture2D(uTex, gl_PointCoord);',
        '  gl_FragColor = vec4(vColor * t.rgb * vAlpha, t.a * vAlpha);',
        '}',
      ].join('\n'),
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    });
    this._haloPoints = new THREE.Points(geo, this._haloMat);
    this._haloPoints.frustumCulled = false;
    this._graphGroup.add(this._haloPoints);
  }

  // ── AUTO-REPARACIÓN (feedback real "no se ve nada"): si el shader de halos
  // no compila en la GPU del usuario (móviles/integradas), caemos a un
  // PointsMaterial estándar; si aun así el render falla, modo ultra-seguro. ──
  _haloFallback() {
    if (!this._haloPoints) return;
    try {
      const geo = this._haloPoints.geometry;
      this._graphGroup.remove(this._haloPoints);
      geo.setAttribute('color', geo.getAttribute('aColor'));   // PointsMaterial usa 'color'
      this._haloPoints = new THREE.Points(geo, new THREE.PointsMaterial({
        map: KhipuGraph3D._haloTexture(), vertexColors: true, size: 24,
        transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending,
        depthWrite: false, sizeAttenuation: true,
      }));
      this._haloPoints.frustumCulled = false;
      this._haloMat = null;   // _animate deja de tocar uniforms
      this._graphGroup.add(this._haloPoints);
    } catch (e) {
      this._haloPoints = null;
      this._haloMat = null;
    }
  }

  _ultraSafeMode(reason) {
    // lo mínimo que SIEMPRE se ve: esferas + aristas. Fuera shaders/extras.
    try { if (this._haloPoints) { this._graphGroup.remove(this._haloPoints); this._haloPoints = null; this._haloMat = null; } } catch (e) {}
    try { if (this._flowPoints) { this._flowPoints.visible = false; } } catch (e) {}
    try { this.scene.fog = null; } catch (e) {}
    this._notify('3D en modo compatible' + (reason ? ' — ' + String(reason).slice(0, 70) : ''));
  }

  _notify(msg) {
    if (this._notified) return;
    this._notified = true;
    try { if (typeof toast === 'function') toast('🪐 ' + msg); } catch (e) {}
  }

  // Auto-chequeo visual: 2s tras arrancar, renderiza y LEE píxeles. Si todo
  // está negro en una pestaña visible → degradar automáticamente y avisar.
  _selfCheck(attempt) {
    if (!this.active) return;
    if (typeof document !== 'undefined' && document.hidden) {
      // pestaña oculta: reintentar luego, no abandonar el chequeo
      setTimeout(() => this._selfCheck(attempt), 3000);
      return;
    }
    try {
      this.renderer.render(this.scene, this.camera);   // frame fresco en este mismo tick
      const gl = this.renderer.getContext();
      const w = gl.drawingBufferWidth, h = gl.drawingBufferHeight;
      if (!w || !h) {
        // CANVAS 0×0 — la causa silenciosa de "pantalla negra": el motor corre
        // dentro de una caja sin tamaño. Avisar al diagnóstico y recuperar.
        if (window._diag) {
          window._diag('3d_zero_size', {
            cw: this.canvas.clientWidth, ch: this.canvas.clientHeight,
            winW: window.innerWidth, winH: window.innerHeight, attempt: attempt || 0,
          });
        }
        this._startSizeWatch();
        if ((attempt || 0) < 4) setTimeout(() => this._selfCheck((attempt || 0) + 1), 1500);
        return;
      }
      let lit = 0;
      const p = new Uint8Array(4);
      for (let i = 0; i < 60; i++) {
        gl.readPixels(Math.floor(w * (0.15 + 0.012 * i)), Math.floor(h * (0.3 + 0.006 * i)),
          1, 1, gl.RGBA, gl.UNSIGNED_BYTE, p);
        if (p[0] + p[1] + p[2] > 20) lit++;
      }
      let gpu = '';
      try {
        const dbg = gl.getExtension('WEBGL_debug_renderer_info');
        if (dbg) gpu = String(gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL)).slice(0, 60);
      } catch (e) {}
      // beacon de diagnóstico: qué GPU y cuántos píxeles se ven realmente
      if (window._diag) window._diag('3d_selfcheck', { lit: lit + '/60', attempt: attempt || 0, gpu });
      if (lit > 0) return;   // se ve — todo bien
      // PANTALLA NEGRA: degradar por pasos
      if ((attempt || 0) === 0 && this._haloMat) {
        this._haloFallback();
        setTimeout(() => this._selfCheck(1), 1500);
      } else {
        this._ultraSafeMode(gpu);
        // último recurso: re-encuadrar por si la cámara quedó fuera
        this._resetView();
      }
    } catch (e) {}
  }

  // atenúa/restaura el halo de UN nodo (lo usan el scatter y el resaltado)
  setHaloDim(nodeId, dim) {
    if (!this._haloPoints || !this._haloIndex) return;
    const i = this._haloIndex.get(nodeId);
    if (i == null) return;
    const a = this._haloPoints.geometry.attributes.aAlpha;
    a.array[i] = dim ? 0.06 : 1;
    a.needsUpdate = true;
  }

  setAllHalos(alphaValue) {
    if (!this._haloPoints) return;
    const a = this._haloPoints.geometry.attributes.aAlpha;
    a.array.fill(alphaValue);
    a.needsUpdate = true;
  }

  // posición sobre la curva de una arista (mismo bezier que la geometría)
  _pointOnRec(rec, t, out) {
    const ax = rec.src.x || 0, ay = rec.src.y || 0, az = rec.src.z || 0;
    const bx = rec.dst.x || 0, by = rec.dst.y || 0, bz = rec.dst.z || 0;
    const dx = bx - ax, dy = by - ay, dz = bz - az;
    const lift = Math.sqrt(dx * dx + dy * dy + dz * dz) * 0.14;
    const cx = (ax + bx) / 2, cy = (ay + by) / 2 + lift, cz = (az + bz) / 2;
    const mt = 1 - t;
    out.set(
      mt * mt * ax + 2 * mt * t * cx + t * t * bx,
      mt * mt * ay + 2 * mt * t * cy + t * t * by,
      mt * mt * az + 2 * mt * t * cz + t * t * bz
    );
    return out;
  }

  _applySpherical() {
    this.camera.position.setFromSpherical(this._spherical).add(this._target);
    this.camera.lookAt(this._target);
  }

  _resetView() {
    this._spherical = new THREE.Spherical(600, Math.PI / 3, Math.PI / 4);
    this._radiusTarget = 600;
    this._velTheta = 0; this._velPhi = 0;
    this._target.set(0, 0, 0);
    this._applySpherical();
  }

  _animate() {
    if (!this.active) return;
    requestAnimationFrame(() => this._animate());
    // OJO: getElapsedTime() consume getDelta() internamente en three.js — usar
    // SOLO getDelta() y acumular nosotros, o dt sería siempre ~0.
    const dt = Math.min(this.clock.getDelta(), 0.1);
    this._elapsed = (this._elapsed || 0) + dt;
    const t = this._elapsed;

    // Monitor de rendimiento: media móvil del frame; si cae de ~20fps
    // bajamos pixel ratio y apagamos partículas (modo ligero). Los HALOS
    // NUNCA se apagan: son el brillo de los nodos y esconderlos parecía
    // "borrar" empresas al mover la cámara (feedback real).
    this._frameEMA = (this._frameEMA || 16) * 0.95 + dt * 1000 * 0.05;
    const lite = this._frameEMA > 50;
    if (lite !== this._liteMode) {
      this._liteMode = lite;
      if (this._flowPoints) this._flowPoints.visible = !lite;
      this.renderer.setPixelRatio(lite ? 1 : Math.min(window.devicePixelRatio, 2));
      this._onResize();
    }

    // Niebla ADAPTATIVA: siempre sutil respecto al zoom actual — da
    // profundidad pero jamás borra el lado lejano del grafo.
    if (this.scene.fog) {
      const d = 0.26 / Math.max(this._spherical.radius, 200);
      this.scene.fog.density = Math.max(0.00010, Math.min(0.00035, d));
    }

    // Zoom SUAVE: la rueda fija un objetivo y el radio se acerca con easing
    if (this._radiusTarget != null && Math.abs(this._radiusTarget - this._spherical.radius) > 0.4) {
      this._spherical.radius += (this._radiusTarget - this._spherical.radius) * 0.16;
      this._applySpherical();
    }

    // INERCIA de órbita: al soltar el arrastre, el giro continúa y decae
    if (!this._buttonsDown && (Math.abs(this._velTheta || 0) > 0.00035 || Math.abs(this._velPhi || 0) > 0.00035)) {
      this._spherical.theta += this._velTheta;
      this._spherical.phi = Math.max(0.08, Math.min(Math.PI - 0.08, this._spherical.phi + this._velPhi));
      this._velTheta *= 0.93;
      this._velPhi *= 0.93;
      this._applySpherical();
    }

    if (this.selected) {
      const mesh = this.nodeMeshes.get(this.selected);
      if (mesh) {
        mesh.scale.setScalar(1 + 0.08 * Math.sin(t * 3));
        // anillo de selección: orbita el nodo elegido
        if (this._selRing) {
          this._selRing.position.copy(mesh.position);
          this._selRing.rotation.y = t * 0.9;
          this._selRing.rotation.x = Math.PI / 3 + Math.sin(t * 0.7) * 0.2;
        }
      }
    }

    // Halos GPU: solo actualizamos uniforms + sincronizamos posiciones con
    // los meshes (así siguen a los nodos aunque el scatter o el hipergrafo
    // los muevan). El pulso y el hover los calcula el shader — CPU casi cero.
    if (this._haloPoints) {
      // uniforms solo si el shader sigue vivo (el fallback compatible los quita)
      if (this._haloMat) {
        this._haloMat.uniforms.uTime.value = t;
        const hi = this.hovered != null && this._haloIndex ? this._haloIndex.get(this.hovered) : null;
        this._haloMat.uniforms.uHover.value = hi != null ? hi : -1;
      }
      const hp = this._haloPoints.geometry.attributes.position.array;
      let hj = 0;
      this.nodeMeshes.forEach(m => {
        hp[hj] = m.position.x; hp[hj + 1] = m.position.y; hp[hj + 2] = m.position.z;
        hj += 3;
      });
      this._haloPoints.geometry.attributes.position.needsUpdate = true;
    }
    if (!this._liteMode) {
      // partículas: UNA nube — solo actualizamos el buffer de posiciones
      if (this._flowPoints && this._flowState) {
        const v = this._flowV || (this._flowV = new THREE.Vector3());
        const arr = this._flowPoints.geometry.attributes.position.array;
        for (let i = 0; i < this._flowState.length; i++) {
          const f = this._flowState[i];
          f.t += f.speed * dt;
          if (f.t > 1) f.t -= 1;
          this._pointOnRec(f.rec, f.t, v);
          arr[i * 3] = v.x; arr[i * 3 + 1] = v.y; arr[i * 3 + 2] = v.z;
        }
        this._flowPoints.geometry.attributes.position.needsUpdate = true;
      }
    }

    // LOD de ETIQUETAS (cada ~8 frames): GENEROSO — el usuario quiere ver
    // todo. Las etiquetas nunca "desaparecen" de golpe: se DESVANECEN por
    // distancia; solo las muy lejanas en zoom muy cercano se apagan.
    this._lodTick = (this._lodTick || 0) + 1;
    if (this._lodTick % 8 === 0) {
      const camPos = this.camera.position;
      const near = Math.max(750, this._spherical.radius * 1.15);
      this.nodeMeshes.forEach(m => {
        const lbl = m.userData.labelSprite;
        if (!lbl) return;
        const important = m.userData.nodeId === this.selected
          || m.userData.nodeId === this.hovered
          || (this._chainSet && this._chainSet.has(m.userData.nodeId))
          || m.userData.baseRadius >= 12;
        const dist = m.position.distanceTo(camPos);
        lbl.visible = important || dist < near;
        // fundido suave por distancia (nada de "pop")
        lbl.material.opacity = important ? 0.95
          : Math.max(0.3, Math.min(0.85, 1.15 - dist / near));
      });
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
      // respiración cinemática: la cámara oscila apenas el radio — vida sutil
      this._spherical.radius += Math.sin(t * 0.4) * 0.05;
      this._applySpherical();
    }

    // render INMORTAL: si algo revienta en la GPU del usuario, degradamos por
    // pasos en vez de morir en negro y en silencio ("no se ve nada" real)
    try {
      this.renderer.render(this.scene, this.camera);
      this._renderFails = 0;
    } catch (e) {
      this._renderFails = (this._renderFails || 0) + 1;
      if (this._renderFails === 2 && this._haloMat) {
        this._haloFallback();
      } else if (this._renderFails === 5) {
        this._ultraSafeMode(e.message || e);
      }
    }
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
      // anillo de selección orbitando el nodo (se crea una vez)
      if (!this._selRing) {
        this._selRing = new THREE.Mesh(
          new THREE.TorusGeometry(1, 0.05, 8, 48),
          new THREE.MeshBasicMaterial({ color: 0x00E0FF, transparent: true, opacity: 0.85,
                                        blending: THREE.AdditiveBlending, depthWrite: false })
        );
        this._graphGroup.add(this._selRing);
      }
      const r = (mesh.userData.baseRadius || 10) + 6;
      this._selRing.scale.setScalar(r);
      this._selRing.visible = true;
      this._flyTo(mesh.position.clone());
    } else if (this._selRing) {
      this._selRing.visible = false;
    }
  }

  _highlightChain(nodeId) {
    if (!nodeId || typeof LINKS === 'undefined') return;
    const upstream = new Set(), downstream = new Set();
    LINKS.forEach(l => {
      const s = typeof lid === 'function' ? lid(l.source) : (l.source && l.source.id ? l.source.id : l.source);
      const t = typeof lid === 'function' ? lid(l.target) : (l.target && l.target.id ? l.target.id : l.target);
      if (t === nodeId) upstream.add(s);
      if (s === nodeId) downstream.add(t);
    });

    this.nodeMeshes.forEach((mesh, id) => {
      if (id === nodeId) {
        mesh.material.emissiveIntensity = 1.2;
        mesh.material.opacity = 1;
      } else if (upstream.has(id)) {
        mesh.material.color.setHex(0x22c55e);
        mesh.material.emissive.setHex(0x22c55e);
        mesh.material.emissiveIntensity = 0.9;
        mesh.material.opacity = 1;
      } else if (downstream.has(id)) {
        mesh.material.color.setHex(0xf97316);
        mesh.material.emissive.setHex(0xf97316);
        mesh.material.emissiveIntensity = 0.9;
        mesh.material.opacity = 1;
      } else {
        mesh.material.opacity = 0.09;
        mesh.material.emissiveIntensity = 0.03;
      }
    });

    // Aristas: la base fusionada se atenúa a casi nada y la CADENA se dibuja
    // encima con líneas dedicadas (decenas, no miles) — verde entra, naranja sale.
    if (this._linkMerged) this._linkMerged.material.opacity = 0.05;
    if (this._hlGroup) this._graphGroup.remove(this._hlGroup);
    this._hlGroup = new THREE.Group();
    const SEGS = 10;
    (this._linkRecs || []).forEach(rec => {
      const s = rec.src.id, t = rec.dst.id;
      if (s !== nodeId && t !== nodeId) return;
      const color = s === nodeId ? 0xf97316 : 0x22c55e;   // provee→naranja, recibe←verde
      const geo = new THREE.BufferGeometry();
      const pos = new Float32Array((SEGS + 1) * 3);
      const v = new THREE.Vector3();
      for (let i = 0; i <= SEGS; i++) {
        this._pointOnRec(rec, i / SEGS, v);
        pos[i * 3] = v.x; pos[i * 3 + 1] = v.y; pos[i * 3 + 2] = v.z;
      }
      geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      this._hlGroup.add(new THREE.Line(geo, new THREE.LineBasicMaterial({
        color, transparent: true, opacity: 0.95,
      })));
    });
    this._graphGroup.add(this._hlGroup);
    this._chainSet = new Set([nodeId, ...upstream, ...downstream]);  // etiquetas LOD
    // halos: se apagan los ajenos a la cadena — foco total
    this.setAllHalos(0.06);
    this._chainSet.forEach(id => this.setHaloDim(id, false));
    this._chainHighlighted = nodeId;
  }

  _clearChainHighlight() {
    if (!this._chainHighlighted) return;
    this.nodeMeshes.forEach((mesh, id) => {
      const node = typeof NODE_BY_ID !== 'undefined' ? NODE_BY_ID[id] : null;
      if (node) {
        const raw = getCatColorHex(node.cat);
        const hex = parseInt(raw.replace('#', ''), 16) || 0x4488cc;
        mesh.material.color.setHex(hex);
        mesh.material.emissive.setHex(hex);
      }
      mesh.material.opacity = 1;
      mesh.material.emissiveIntensity = 0.25;
    });
    if (this._linkMerged) this._linkMerged.material.opacity = 0.55;
    if (this._hlGroup) { this._graphGroup.remove(this._hlGroup); this._hlGroup = null; }
    this.setAllHalos(1);
    this._chainSet = null;
    this._chainHighlighted = null;
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
        this._radiusTarget = this._spherical.radius;   // el zoom suave parte de aquí
      }
    };
    fly();
  }

  _setupPointerControls() {
    // ── Mouse ──────────────────────────────────────────────────────────────────
    this.canvas.addEventListener('mousedown', e => {
      this._mouseMoved = false;
      this._dragging   = true;
      this._buttonsDown = true;
      this._velTheta = 0; this._velPhi = 0;   // la inercia arranca de cero
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
          // Left-drag: orbit (y memoriza la velocidad para la INERCIA al soltar)
          this._spherical.theta -= dx * 0.005;
          this._spherical.phi = Math.max(0.08, Math.min(Math.PI - 0.08,
            this._spherical.phi + dy * 0.005));
          this._velTheta = -dx * 0.005 * 0.5;
          this._velPhi = dy * 0.005 * 0.5;
        }
        this._prevMouse = { x: e.clientX, y: e.clientY };
        this._applySpherical();
      }
    });

    this.canvas.addEventListener('mouseup', () => {
      this._buttonsDown = false;   // desde aquí actúa la inercia
      // Resume auto-rotation 2.5 s after last interaction
      clearTimeout(this._rotResumeTimer);
      this._rotResumeTimer = setTimeout(() => { this._dragging = false; }, 2500);
    });

    // Right-click: pan mode, suppress context menu
    this.canvas.addEventListener('contextmenu', e => e.preventDefault());

    // Double-click: reset view
    this.canvas.addEventListener('dblclick', () => this._resetView());

    // ── Touch ──────────────────────────────────────────────────────────────────
    this.canvas.addEventListener('touchstart', e => {
      e.preventDefault();
      this._dragging = true;
      this._buttonsDown = true;
      this._velTheta = 0; this._velPhi = 0;
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
        this._velTheta = -dx * 0.007 * 0.5;
        this._velPhi = dy * 0.007 * 0.5;
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
          this._radiusTarget = this._spherical.radius;
          this._applySpherical();
        }
        this._pinchDist = dist;
      }
    }, { passive: false });

    this.canvas.addEventListener('touchend', e => {
      e.preventDefault();
      if (e.touches.length === 0) {
        this._buttonsDown = false;   // desde aquí actúa la inercia
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
      if (e.key === '+' || e.key === '=') { this._spherical.radius = Math.max(80, this._spherical.radius - 55); this._radiusTarget = this._spherical.radius; moved = true; }
      if (e.key === '-')               { this._spherical.radius = Math.min(2200, this._spherical.radius + 55); this._radiusTarget = this._spherical.radius; moved = true; }
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
    // zoom SUAVE: fija el objetivo; _animate acerca el radio con easing
    const base = this._radiusTarget != null ? this._radiusTarget : this._spherical.radius;
    this._radiusTarget = Math.max(80, Math.min(2200, base + e.deltaY * 0.8));
  }

  _onMouseMove(e) {
    if (e.buttons) return;
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

    // ── Tooltip ────────────────────────────────────────────────────────────────
    const tip = document.getElementById('g3d-tooltip');
    if (!tip) return;
    if (!newHover) { tip.style.display = 'none'; return; }
    const n = (typeof NODE_BY_ID !== 'undefined') ? NODE_BY_ID[newHover] : null;
    if (!n) { tip.style.display = 'none'; return; }

    const q = (typeof MKT !== 'undefined' && n.mkt) ? MKT.quotes[n.mkt] : null;
    const price = q && q.close != null ? '$' + Number(q.close).toFixed(2) : null;
    const chg = (q && q.close != null && q.prev != null) ? ((q.close - q.prev) / q.prev * 100) : null;
    const chgColor = chg == null ? '' : chg >= 0 ? '#22c55e' : '#ef4444';
    let nrs = null;
    try { if (typeof computeNRS === 'function') nrs = computeNRS(newHover); } catch(e){}
    const nrsColor = nrs == null ? '#7a9cc4' : nrs < 30 ? '#22c55e' : nrs < 60 ? '#f59e0b' : '#ef4444';

    let upstream = 0, downstream = 0;
    if (typeof LINKS !== 'undefined') {
      LINKS.forEach(l => {
        const s = typeof lid === 'function' ? lid(l.source) : (l.source && l.source.id ? l.source.id : l.source);
        const t = typeof lid === 'function' ? lid(l.target) : (l.target && l.target.id ? l.target.id : l.target);
        if (t === newHover) upstream++;
        if (s === newHover) downstream++;
      });
    }

    const catMeta = (typeof CATS !== 'undefined' && n.cat && CATS[n.cat]) || {};
    const catLabel = catMeta.label || n.cat || '';
    tip.innerHTML =
      `<div style="font-size:12px;font-weight:700;color:#e8edf5;margin-bottom:4px;line-height:1.3">${n.label}</div>` +
      (n.ticker ? `<div style="font-size:10px;color:#5b8ab8;margin-bottom:8px;font-family:'JetBrains Mono',monospace">${n.ticker}</div>` : '') +
      `<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">` +
        (price ? `<span style="font-size:13px;font-weight:700;color:#d1e8ff">${price}</span>` : '') +
        (chg != null ? `<span style="font-size:11px;color:${chgColor};font-weight:600">${chg>=0?'+':''}${chg.toFixed(2)}%</span>` : '') +
        `<span style="margin-left:auto;font-size:10px;color:#7a9cc4">NRS <strong style="color:${nrsColor}">${nrs != null ? nrs : '—'}</strong></span>` +
      `</div>` +
      `<div style="display:flex;gap:12px;font-size:10px;color:#5b8ab8;border-top:1px solid rgba(80,120,180,.2);padding-top:7px;margin-top:2px">` +
        `<span style="color:#22c55e">⬆ ${upstream} prov.</span>` +
        `<span style="color:#f97316">⬇ ${downstream} clientes</span>` +
        (catLabel ? `<span style="margin-left:auto;color:#7a9cc4">${catLabel}</span>` : '') +
      `</div>` +
      (n.growth ? `<div style="font-size:10px;color:#9ab;margin-top:6px;line-height:1.3">${n.growth}</div>` : '') +
      (n.mkt && window._tickerWarnings && window._tickerWarnings.has(newHover) ?
        `<div style="font-size:10px;color:#f59e0b;margin-top:5px;border-top:1px solid rgba(80,120,180,.2);padding-top:5px">⚠ Sin datos de mercado · ticker puede haber cambiado</div>` : '');

    // Position tooltip (avoid going off screen)
    const tw = 220, th = 110;
    const vw = window.innerWidth, vh = window.innerHeight;
    let tx = e.clientX + 18, ty = e.clientY - 40;
    if (tx + tw > vw - 10) tx = e.clientX - tw - 10;
    if (ty + th > vh - 10) ty = vh - th - 10;
    if (ty < 10) ty = 10;
    tip.style.left = tx + 'px';
    tip.style.top = ty + 'px';
    tip.style.display = 'block';
  }

  _onClick(e) {
    if (this._mouseMoved) return;
    if (this.hovered) {
      if (typeof window.jumpTo === 'function') window.jumpTo(this.hovered);
      this.selectNode(this.hovered);
      this._highlightChain(this.hovered);
    } else {
      this._clearChainHighlight();
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
    // ── ATMÓSFERA "otro planeta": doble campo de estrellas + nebulosas +
    // resplandor central. Todo aditivo y estático — costo casi nulo. ──
    // capa lejana: polvo estelar tenue
    const g1 = new THREE.BufferGeometry();
    const p1 = new Float32Array(3600);
    for (let i = 0; i < 3600; i++) p1[i] = (Math.random() - 0.5) * 4200;
    g1.setAttribute('position', new THREE.BufferAttribute(p1, 3));
    this.scene.add(new THREE.Points(g1, new THREE.PointsMaterial({ color: 0x2c3c5e, size: 0.8 })));
    // capa cercana: estrellas cian brillantes, pocas
    const g2 = new THREE.BufferGeometry();
    const p2 = new Float32Array(900);
    for (let i = 0; i < 900; i++) p2[i] = (Math.random() - 0.5) * 2800;
    g2.setAttribute('position', new THREE.BufferAttribute(p2, 3));
    this.scene.add(new THREE.Points(g2, new THREE.PointsMaterial({
      color: 0x6fd6ff, size: 1.6, transparent: true, opacity: 0.75,
      blending: THREE.AdditiveBlending, depthWrite: false,
    })));
    // nebulosas: manchas de color enormes y lejanas (violeta / cian / magenta)
    const nebulaTex = KhipuGraph3D._haloTexture();
    [[0x5a2da8, -1600, 500, -1500, 2600, 0.10],
     [0x0e5a80, 1500, -300, -1700, 2200, 0.12],
     [0x8a2d6e, 300, 900, 1600, 1900, 0.08],
     [0x1a3a8a, -900, -800, 1400, 2400, 0.09]].forEach(([hex, x, y, z, s, op]) => {
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({
        map: nebulaTex, color: hex, transparent: true, opacity: op,
        blending: THREE.AdditiveBlending, depthWrite: false,
      }));
      sp.position.set(x, y, z);
      sp.scale.set(s, s, 1);
      sp.renderOrder = -2;
      this.scene.add(sp);
    });
    // resplandor central: el "sol" del universo Khipus detrás del grafo
    const core = new THREE.Sprite(new THREE.SpriteMaterial({
      map: nebulaTex, color: 0x1a6a9a, transparent: true, opacity: 0.30,
      blending: THREE.AdditiveBlending, depthWrite: false,
    }));
    core.scale.set(560, 560, 1);
    core.renderOrder = -1;
    this.scene.add(core);
  }

  _onResize() {
    // OJO: nunca retornar en silencio con tamaño 0 — ese era el hueco de la
    // "pantalla negra": canvas nace 0×0 (pestaña oculta / carrera de layout)
    // y nada volvía a dimensionarlo. Ahora reintenta hasta tener tamaño real.
    if (!this._ensureSized()) this._startSizeWatch();
  }

  // Dimensiona el renderer al tamaño REAL del canvas. true si quedó > 0.
  _ensureSized() {
    const w = this.canvas.clientWidth, h = this.canvas.clientHeight;
    if (!w || !h) return false;
    const gl = this.renderer.getContext();
    if (gl.drawingBufferWidth !== Math.round(w * this.renderer.getPixelRatio()) ||
        gl.drawingBufferHeight !== Math.round(h * this.renderer.getPixelRatio())) {
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(w, h);
    }
    return gl.drawingBufferWidth > 0 && gl.drawingBufferHeight > 0;
  }

  // Vigilante: reintenta dimensionar cada frame hasta lograrlo (máx ~20s).
  _startSizeWatch() {
    if (this._sizeWatchOn) return;
    this._sizeWatchOn = true;
    let tries = 0;
    const tick = () => {
      if (this._ensureSized() || tries++ > 1200 || !this.renderer) {
        this._sizeWatchOn = false;
        return;
      }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  pause() { this.active = false; }

  resume() {
    if (!this.active) {
      this.active = true;
      this._animate();
      setTimeout(() => this._selfCheck(0), 2000);   // re-chequeo visual al volver
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
