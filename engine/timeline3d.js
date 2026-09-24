/* ============================================================================
   engine/timeline3d.js — El Grafo Temporal en 3D, donde la PROFUNDIDAD ES EL
   TIEMPO.

   Por qué este 3D y no otro: para analizar un grafo, el 3D suele ser PEOR que
   un buen 2D — los nodos se tapan, cuesta navegar y es difícil juzgar
   distancias. Solo gana cuando el tercer eje representa una variable real.
   Aquí Z = cuándo empezó cada relación, así que la cadena de suministro deja
   de ser un mapa que cambia y pasa a ser un sólido que se atraviesa: se ven
   las sanciones cortando enlaces y las relaciones nuevas brotando por delante.

   Es barato por construcción: solo entran los hechos CON fecha real (86) y las
   empresas que participan en ellos (71) — no las 949 del mapa. Y se dibuja
   BAJO DEMANDA, no en un bucle continuo: quieto no consume nada, que es lo que
   permite tenerlo en un teléfono.

   Empresas en un anillo, relaciones como cuerdas que lo cruzan a la
   profundidad de su fecha: un diagrama de cuerdas extruido en el tiempo.
   ============================================================================ */
(function () {
  'use strict';

  const R = 130;          // radio del anillo de empresas
  const DEPTH = 420;      // largo del eje temporal
  let S = null;           // estado de la escena

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }
  function L(es, en) {
    let l = window.LANG;
    if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = null; } }
    return l === 'en' ? en : es;
  }
  function nm(id) {
    const n = window.NODE_BY_ID && window.NODE_BY_ID[id];
    return (n && n.label) || id;
  }
  function relColor(rel) {
    try { if (typeof window.getLinkColorHex === 'function') return window.getLinkColorHex(rel); } catch (e) {}
    return '#4E8B1E';
  }

  /* Hechos con fecha y dos extremos: son los únicos que pueden situarse en el
     eje temporal. Un hecho sin fecha no pertenece a esta vista — mostrarlo en
     "hoy" sería inventarle una. */
  function factsWithTime() {
    const raw = window.TEMPORAL_SEED_FACTS || [];
    const out = [];
    for (const f of raw) {
      if (f.object_type !== 'node') continue;
      const a = f.subject, b = f.object;
      const t = Date.parse(f.valid_from || '');
      if (!a || !b || a === b || isNaN(t)) continue;
      out.push({ a, b, t, rel: f.rel || 'supply', until: Date.parse(f.valid_until || '') || null,
                 headline: (f.meta && f.meta.headline) || f.predicate || '' });
    }
    return out.sort((x, y) => x.t - y.t);
  }

  function buildScene(canvas, facts) {
    const THREE = window.THREE;
    const ents = [...new Set(facts.flatMap(f => [f.a, f.b]))];
    const minT = Math.min(...facts.map(f => f.t));
    const maxT = Math.max(...facts.map(f => f.t));
    const span = Math.max(1, maxT - minT);
    const zOf = t => -DEPTH / 2 + ((t - minT) / span) * DEPTH;

    // posición angular estable por entidad (mismo orden ⇒ misma posición)
    const pos = {};
    ents.forEach((id, i) => {
      const ang = (i / ents.length) * Math.PI * 2;
      pos[id] = { x: Math.cos(ang) * R, y: Math.sin(ang) * R };
    });

    const scene = new THREE.Scene();
    const w = canvas.clientWidth || 600, h = canvas.clientHeight || 420;
    const camera = new THREE.PerspectiveCamera(50, w / h, 1, 4000);
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(w, h, false);

    const world = new THREE.Group();
    scene.add(world);

    // columnas: cada empresa es una línea vertical a lo largo de TODO el tiempo,
    // para poder seguirla de punta a punta
    const colPts = [];
    ents.forEach(id => {
      const p = pos[id];
      colPts.push(new THREE.Vector3(p.x, p.y, -DEPTH / 2), new THREE.Vector3(p.x, p.y, DEPTH / 2));
    });
    world.add(new THREE.LineSegments(
      new THREE.BufferGeometry().setFromPoints(colPts),
      new THREE.LineBasicMaterial({ color: 0x8a857a, transparent: true, opacity: 0.16 })));

    // anillos de año: la escala temporal, visible sin texto 3D
    const ringPts = [];
    const y0 = new Date(minT).getUTCFullYear(), y1 = new Date(maxT).getUTCFullYear();
    const years = [];
    for (let y = y0; y <= y1; y++) {
      const t = Date.UTC(y, 0, 1);
      if (t < minT || t > maxT) continue;
      years.push(y);
      const z = zOf(t);
      for (let i = 0; i < 48; i++) {
        const a1 = (i / 48) * Math.PI * 2, a2 = ((i + 1) / 48) * Math.PI * 2;
        ringPts.push(new THREE.Vector3(Math.cos(a1) * R * 1.08, Math.sin(a1) * R * 1.08, z),
                     new THREE.Vector3(Math.cos(a2) * R * 1.08, Math.sin(a2) * R * 1.08, z));
      }
    }
    world.add(new THREE.LineSegments(
      new THREE.BufferGeometry().setFromPoints(ringPts),
      new THREE.LineBasicMaterial({ color: 0x9b4fe8, transparent: true, opacity: 0.1 })));

    // las relaciones: una cuerda que cruza el anillo a la profundidad de su fecha.
    // Agrupadas por color para no crear 86 materiales.
    const porColor = {};
    facts.forEach(f => {
      const c = relColor(f.rel);
      (porColor[c] = porColor[c] || []).push(f);
    });
    Object.entries(porColor).forEach(([color, fs]) => {
      const pts = [];
      fs.forEach(f => {
        const pa = pos[f.a], pb = pos[f.b], z = zOf(f.t);
        // arco suave hacia el centro: evita que las cuerdas se solapen en línea recta
        const mid = new THREE.Vector3((pa.x + pb.x) * 0.25, (pa.y + pb.y) * 0.25, z);
        const A = new THREE.Vector3(pa.x, pa.y, z), B = new THREE.Vector3(pb.x, pb.y, z);
        const SEG = 10;
        for (let i = 0; i < SEG; i++) {
          const t1 = i / SEG, t2 = (i + 1) / SEG;
          const q = (p, t) => new THREE.Vector3(
            (1 - t) * (1 - t) * A.x + 2 * (1 - t) * t * mid.x + t * t * B.x,
            (1 - t) * (1 - t) * A.y + 2 * (1 - t) * t * mid.y + t * t * B.y, z);
          pts.push(q(null, t1), q(null, t2));
        }
      });
      world.add(new THREE.LineSegments(
        new THREE.BufferGeometry().setFromPoints(pts),
        new THREE.LineBasicMaterial({ color: new THREE.Color(color), transparent: true, opacity: 0.55 })));
    });

    camera.position.set(0, -R * 2.6, DEPTH * 0.95);
    camera.lookAt(0, 0, 0);

    return { THREE, scene, camera, renderer, world, canvas, ents, years,
             minT, maxT, rotX: -0.45, rotY: 0, zoom: 1 };
  }

  function draw() {
    if (!S) return;
    S.world.rotation.x = S.rotX;
    S.world.rotation.y = S.rotY;
    S.camera.position.set(0, -R * 2.6 / S.zoom, DEPTH * 0.95 / S.zoom);
    S.camera.lookAt(0, 0, 0);
    S.renderer.render(S.scene, S.camera);
  }

  /* Controles mínimos. Se dibuja SOLO al interactuar: sin bucle continuo la
     vista quieta no gasta batería ni CPU. */
  function bindControls(canvas) {
    let dragging = false, lx = 0, ly = 0;
    const start = (x, y) => { dragging = true; lx = x; ly = y; };
    const move = (x, y) => {
      if (!dragging) return;
      S.rotY += (x - lx) * 0.006;
      S.rotX += (y - ly) * 0.006;
      S.rotX = Math.max(-1.4, Math.min(1.4, S.rotX));
      lx = x; ly = y;
      draw();
    };
    const end = () => { dragging = false; };

    canvas.addEventListener('mousedown', e => start(e.clientX, e.clientY));
    window.addEventListener('mousemove', e => move(e.clientX, e.clientY));
    window.addEventListener('mouseup', end);
    canvas.addEventListener('touchstart', e => { if (e.touches[0]) start(e.touches[0].clientX, e.touches[0].clientY); }, { passive: true });
    canvas.addEventListener('touchmove', e => { if (e.touches[0]) { move(e.touches[0].clientX, e.touches[0].clientY); } }, { passive: true });
    canvas.addEventListener('touchend', end, { passive: true });
    canvas.addEventListener('wheel', e => {
      e.preventDefault();
      S.zoom = Math.max(0.5, Math.min(3, S.zoom * (e.deltaY < 0 ? 1.12 : 0.89)));
      draw();
    }, { passive: false });
  }

  window.KhipuTimeline3D = {
    /* Devuelve true si logró montar la escena. No lanza: si no hay WebGL o no
       hay hechos fechados, se dice en texto y la pestaña sigue usable. */
    init(containerId) {
      const cont = document.getElementById(containerId);
      if (!cont) return false;

      const facts = factsWithTime();
      if (!facts.length) {
        cont.innerHTML = `<div style="padding:26px;color:var(--ink-3);font-size:13px">${
          L('No hay hechos con fecha real para situar en el tiempo.',
            'No dated facts available to place on the time axis.')}</div>`;
        return false;
      }
      if (!window.THREE) {
        cont.innerHTML = `<div style="padding:26px;color:var(--ink-3);font-size:13px">${
          L('Esta vista necesita WebGL y no está disponible en este navegador. El resto del Grafo Temporal funciona igual.',
            'This view needs WebGL, unavailable in this browser. The rest of the Temporal Graph works fine.')}</div>`;
        return false;
      }

      const ents = new Set(facts.flatMap(f => [f.a, f.b]));
      const y0 = new Date(Math.min(...facts.map(f => f.t))).getUTCFullYear();
      const y1 = new Date(Math.max(...facts.map(f => f.t))).getUTCFullYear();

      cont.innerHTML = `
        <div style="font-size:11.5px;color:var(--ink-3);margin-bottom:8px;line-height:1.5">
          ${L('La <b>profundidad es el tiempo</b>: al fondo ' + y0 + ', al frente ' + y1 +
              '. Cada empresa es una columna; cada relación, una cuerda a la altura del año en que empezó.',
              'Depth <b>is time</b>: ' + y0 + ' at the back, ' + y1 + ' at the front. ' +
              'Each company is a column; each relation, a chord at the year it began.')}
          <span style="color:var(--ink-3)"> · ${ents.size} ${L('empresas', 'companies')} · ${facts.length} ${L('relaciones fechadas', 'dated relations')}</span>
        </div>
        <canvas id="tkg3d-canvas" style="width:100%;height:440px;display:block;border:1px solid var(--line);border-radius:10px;background:var(--surface-2);touch-action:none;cursor:grab"></canvas>
        <div style="font-size:10.5px;color:var(--ink-3);margin-top:6px">
          ${L('Arrastra para girar · rueda o pellizca para acercar',
              'Drag to rotate · wheel or pinch to zoom')}
        </div>`;

      const canvas = document.getElementById('tkg3d-canvas');
      try {
        S = buildScene(canvas, facts);
        bindControls(canvas);
        draw();
        return true;
      } catch (e) {
        cont.innerHTML = `<div style="padding:26px;color:var(--ink-3);font-size:13px">${
          L('No se pudo iniciar la vista 3D: ', 'Could not start the 3D view: ')}${esc(e.message || e)}</div>`;
        S = null;
        return false;
      }
    },

    resize() {
      if (!S || !S.canvas) return;
      const w = S.canvas.clientWidth || 600, h = S.canvas.clientHeight || 440;
      S.camera.aspect = w / h;
      S.camera.updateProjectionMatrix();
      S.renderer.setSize(w, h, false);
      draw();
    },

    dispose() {
      if (!S) return;
      try { S.renderer.dispose(); } catch (e) {}
      S = null;
    },
  };
})();
