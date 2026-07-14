// engine/orb.js — BixbyOrb: el orbe de voz de Bixby.
//
// Un blob orgánico que FLOTA (bobbing suave), respira en reposo y se deforma /
// pulsa con la energía de la voz: cuando habla el USUARIO reacciona hacia el
// cian/teal, cuando habla BIXBY reacciona hacia el violeta. Canvas con alpha
// (clearRect cada frame) — SIN caja ni fondo. 60fps, liviano, DPR-aware.
//
// API pública (window.BixbyOrb):
//   mount(container?)          → monta un <canvas> transparente dentro de
//                                `container`. Si no se pasa contenedor, crea uno
//                                fixed flotante (abajo-derecha). Idempotente:
//                                re-montar en el mismo contenedor no duplica.
//   start()                    → arranca la animación (rAF; se auto-pausa con
//                                document.hidden y reanuda al volver a ser visible).
//   stop()                     → detiene la animación (deja el último frame).
//   setUserLevel(v)            → 0..1, energía de la voz del USUARIO (cian).
//   setBixbyLevel(v)           → 0..1, energía de la voz de BIXBY (violeta).
//   destroy()                  → detiene, quita listeners y remueve el canvas
//                                (y el contenedor flotante si lo creó él).
//   isMounted()/isRunning()    → estado.
//
// Notas de integración:
//   • El agente BIXBY (voice.js) llama setUserLevel/setBixbyLevel con el nivel
//     RMS del micrófono y del audio de reproducción respectivamente. Si nadie
//     actualiza, los niveles decaen solos y el orbe vuelve a "idle" (respira).
//   • No depende de ningún global de la app; funciona aislado. Bilingüe solo en
//     el aria-label (no dibuja texto).
//
// NO toca app.html ni sw.js: el orquestador monta el orbe en la Cabina.

(function () {
  'use strict';

  /* ── i18n mínimo (solo aria-label; regla bilingüe ES/EN) ── */
  function _lang() {
    try {
      return String(window.LANG || localStorage.getItem('eco_lang') || 'es').slice(0, 2) === 'en' ? 'en' : 'es';
    } catch (e) { return 'es'; }
  }

  /* ── Paleta de la app ── */
  //  violeta (Bixby) · cian + teal (usuario)
  const C_VIOLET = [0x8e, 0x5a, 0xff]; // #8e5aff
  const C_CYAN   = [0x00, 0xe0, 0xff]; // #00E0FF
  const C_TEAL   = [0x3d, 0xe0, 0xc8]; // #3DE0C8

  function _clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }
  function _lerp(a, b, t) { return a + (b - a) * t; }
  function _mix(c1, c2, t) {
    return [
      Math.round(_lerp(c1[0], c2[0], t)),
      Math.round(_lerp(c1[1], c2[1], t)),
      Math.round(_lerp(c1[2], c2[2], t)),
    ];
  }
  function _rgba(c, a) { return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + a + ')'; }

  /* ── Estado del módulo ── */
  const S = {
    container: null,     // contenedor donde vive el canvas
    ownsContainer: false,// true si BixbyOrb creó el contenedor flotante
    canvas: null,
    ctx: null,
    dpr: 1,
    cssW: 0, cssH: 0,
    ro: null,            // ResizeObserver
    raf: 0,
    running: false,
    t0: 0,
    lastFrame: 0,

    // Niveles objetivo (los fija la voz) y suavizados (los que se dibujan).
    userTarget: 0, bixbyTarget: 0,
    userLevel: 0, bixbyLevel: 0,

    // Blend cromático suavizado: 0 = usuario (cian/teal) · 1 = Bixby (violeta).
    blend: 0.5,

    // Semillas de ruido para que el contorno no sea un círculo rígido.
    seed: [Math.random() * 6.28, Math.random() * 6.28, Math.random() * 6.28, Math.random() * 6.28],

    onVis: null,
    particles: null,     // partículas orbitando ("de otro planeta")
  };

  const TWO_PI = Math.PI * 2;
  const POINTS = 96;     // resolución del contorno

  /* ── Montaje ── */
  function mount(container) {
    // Idempotente: si ya está montado en el mismo contenedor, no dupliques.
    if (S.canvas && S.container === (container || S.container) && document.body.contains(S.canvas)) {
      return S.canvas;
    }
    // Si estaba montado en otro sitio, limpia primero.
    if (S.canvas) _teardownCanvas();

    let host = container;
    S.ownsContainer = false;
    if (!host) {
      host = document.createElement('div');
      host.id = 'bixby-orb-float';
      host.style.cssText = [
        'position:fixed', 'right:20px', 'bottom:20px',
        'width:140px', 'height:140px',
        'pointer-events:none', 'z-index:9999',
        'background:transparent',
      ].join(';');
      document.body.appendChild(host);
      S.ownsContainer = true;
    }
    S.container = host;

    const cv = document.createElement('canvas');
    cv.className = 'bixby-orb-canvas';
    cv.setAttribute('role', 'img');
    cv.setAttribute('aria-label', _lang() === 'en' ? 'Bixby voice orb' : 'Orbe de voz de Bixby');
    // Sin fondo: el canvas es transparente y no capta clics por defecto.
    cv.style.cssText = 'display:block;width:100%;height:100%;background:transparent;pointer-events:none';
    host.appendChild(cv);

    S.canvas = cv;
    S.ctx = cv.getContext('2d');

    _resize();
    // Observa cambios de tamaño del contenedor para mantener nitidez (DPR).
    try {
      S.ro = new ResizeObserver(function () { _resize(); });
      S.ro.observe(host);
    } catch (e) { /* ResizeObserver puede no existir en entornos viejos */ }

    // Pausa/reanuda con la visibilidad de la pestaña (rAF se congela oculto).
    if (!S.onVis) {
      S.onVis = function () {
        if (document.hidden) {
          if (S.raf) { cancelAnimationFrame(S.raf); S.raf = 0; }
        } else if (S.running && !S.raf) {
          S.lastFrame = 0;
          S.raf = requestAnimationFrame(_frame);
        }
      };
      document.addEventListener('visibilitychange', S.onVis);
    }

    // Dibuja un frame estático de inmediato (para que se vea aunque no arranque).
    _draw((typeof performance !== 'undefined' && performance.now) ? performance.now() : 0, 0);
    return cv;
  }

  function _resize() {
    if (!S.canvas || !S.ctx) return;
    const rect = S.container.getBoundingClientRect();
    let w = rect.width, h = rect.height;
    // Fallback si el contenedor aún no tiene tamaño (display:none, etc.).
    if (!w || !h) { w = S.cssW || 140; h = S.cssH || 140; }
    S.cssW = w; S.cssH = h;
    S.dpr = Math.min(window.devicePixelRatio || 1, 2.5); // cap para no reventar fill-rate
    S.canvas.width = Math.max(1, Math.round(w * S.dpr));
    S.canvas.height = Math.max(1, Math.round(h * S.dpr));
    S.ctx.setTransform(S.dpr, 0, 0, S.dpr, 0, 0);

    // Partículas orbitando: se generan una vez, se reescalan con el tamaño.
    if (!S.particles) {
      S.particles = [];
      const n = 5;
      for (let i = 0; i < n; i++) {
        S.particles.push({
          ang: Math.random() * TWO_PI,
          spd: 0.15 + Math.random() * 0.35,   // rad/s
          rad: 0.9 + Math.random() * 0.5,     // factor sobre el radio base
          size: 1 + Math.random() * 1.6,
          ph: Math.random() * TWO_PI,
        });
      }
    }
  }

  /* ── Ciclo de animación ── */
  function start() {
    if (!S.canvas) mount();       // auto-monta si aún no
    if (S.running) return;
    S.running = true;
    S.t0 = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
    S.lastFrame = 0;
    if (!document.hidden && !S.raf) S.raf = requestAnimationFrame(_frame);
  }

  function stop() {
    S.running = false;
    if (S.raf) { cancelAnimationFrame(S.raf); S.raf = 0; }
  }

  function _frame(now) {
    S.raf = 0;
    if (!S.running) return;
    const t = (now - S.t0) / 1000;             // segundos desde start
    let dt = S.lastFrame ? (now - S.lastFrame) / 1000 : 0.016;
    if (dt > 0.1) dt = 0.1;                     // clamp tras pausas largas
    S.lastFrame = now;

    _step(dt);
    _draw(now, t);

    if (S.running && !document.hidden) S.raf = requestAnimationFrame(_frame);
  }

  // Suaviza niveles y hace decaer los objetivos (para volver a idle si la voz
  // deja de actualizar). La voz llama setUserLevel/setBixbyLevel muy seguido
  // mientras hay audio, así que el objetivo se mantiene alto durante el habla.
  function _step(dt) {
    // Decaimiento del objetivo (~ vuelve a 0 en ~0.4s sin updates).
    const decay = Math.pow(0.02, dt);          // por-frame equiv. a e^{...}
    S.userTarget *= decay;
    S.bixbyTarget *= decay;
    if (S.userTarget < 0.001) S.userTarget = 0;
    if (S.bixbyTarget < 0.001) S.bixbyTarget = 0;

    // Suavizado hacia el objetivo (attack rápido, release medio).
    const kUp = 1 - Math.pow(0.001, dt);       // sube rápido
    const kDn = 1 - Math.pow(0.05, dt);        // baja más suave
    S.userLevel += (S.userTarget - S.userLevel) * (S.userTarget > S.userLevel ? kUp : kDn);
    S.bixbyLevel += (S.bixbyTarget - S.bixbyLevel) * (S.bixbyTarget > S.bixbyLevel ? kUp : kDn);

    // Blend cromático objetivo según quién domina.
    const sum = S.userLevel + S.bixbyLevel;
    let blendTarget = 0.5;                      // en reposo, mezcla equilibrada
    if (sum > 0.02) blendTarget = S.bixbyLevel / sum; // 0 usuario ↔ 1 bixby
    const kB = 1 - Math.pow(0.02, dt);
    S.blend += (blendTarget - S.blend) * kB;
  }

  function _draw(now, t) {
    const ctx = S.ctx;
    if (!ctx) return;
    const W = S.cssW, H = S.cssH;
    ctx.clearRect(0, 0, W, H);                  // transparente cada frame

    const cx = W / 2;
    const energy = _clamp(Math.max(S.userLevel, S.bixbyLevel), 0, 1);

    // Bobbing: flota arriba/abajo (más marcado en reposo, contenido al hablar).
    const bobAmp = H * 0.045 * (1 - 0.4 * energy);
    const cy = H / 2 + Math.sin(t * 1.1) * bobAmp + Math.sin(t * 0.37 + 1.3) * bobAmp * 0.4;

    // Radio base + respiración lenta (idle) + empuje por energía.
    const baseR = Math.min(W, H) * 0.30;
    const breathe = 1 + 0.05 * Math.sin(t * 1.6) + 0.03 * Math.sin(t * 0.9 + 2.0);
    const R = baseR * breathe * (1 + 0.28 * energy);

    // Color según blend (usuario cian/teal ↔ bixby violeta).
    const userCol = _mix(C_CYAN, C_TEAL, 0.35 + 0.25 * Math.sin(t * 0.6)); // matiz vivo
    const col = _mix(userCol, C_VIOLET, _clamp(S.blend, 0, 1));
    // Centro "caliente": mezcla hacia blanco con la energía.
    const core = _mix(col, [255, 255, 255], 0.35 + 0.4 * energy);

    // Amplitud de deformación del contorno (más al hablar → "vibra").
    const wob = 0.10 + 0.22 * energy;

    // Puntos del contorno (radio modulado por senoidales de distinta frecuencia).
    const pts = new Array(POINTS);
    for (let i = 0; i < POINTS; i++) {
      const a = (i / POINTS) * TWO_PI;
      const m =
          0.55 * Math.sin(a * 3 + t * 0.9 + S.seed[0]) +
          0.30 * Math.sin(a * 5 - t * 1.3 + S.seed[1]) +
          0.20 * Math.sin(a * 2 + t * 0.5 + S.seed[2]) +
          0.14 * Math.sin(a * 7 + t * 1.9 + S.seed[3]);
      const rr = R * (1 + wob * m * 0.5);
      pts[i] = [cx + Math.cos(a) * rr, cy + Math.sin(a) * rr, rr];
    }

    // ── Capa de glow externo (radial, suave, sin blur costoso) ──
    const glowR = R * 2.2;
    const gg = ctx.createRadialGradient(cx, cy, R * 0.2, cx, cy, glowR);
    gg.addColorStop(0, _rgba(col, 0.28 + 0.25 * energy));
    gg.addColorStop(0.45, _rgba(col, 0.10));
    gg.addColorStop(1, _rgba(col, 0));
    ctx.beginPath();
    ctx.arc(cx, cy, glowR, 0, TWO_PI);
    ctx.fillStyle = gg;
    ctx.fill();

    // ── Cuerpo del blob (contorno orgánico con curvas suaves) ──
    ctx.save();
    ctx.beginPath();
    _blobPath(ctx, pts);
    // Gradiente interno: núcleo brillante desplazado (da volumen "planetario").
    const g = ctx.createRadialGradient(
      cx - R * 0.28, cy - R * 0.30, R * 0.08,
      cx, cy, R * 1.08
    );
    g.addColorStop(0, _rgba(core, 0.98));
    g.addColorStop(0.35, _rgba(col, 0.92));
    g.addColorStop(0.75, _rgba(_mix(col, C_VIOLET, 0.2), 0.85));
    g.addColorStop(1, _rgba(_mix(col, [10, 6, 30], 0.55), 0.72));
    ctx.fillStyle = g;
    // Halo suave alrededor del cuerpo.
    ctx.shadowColor = _rgba(col, 0.55);
    ctx.shadowBlur = Math.max(6, R * (0.35 + 0.5 * energy));
    ctx.fill();
    ctx.restore();

    // ── Brillo especular (highlight) ──
    ctx.save();
    ctx.beginPath();
    _blobPath(ctx, pts);
    ctx.clip();
    const hx = cx - R * 0.30, hy = cy - R * 0.34;
    const hg = ctx.createRadialGradient(hx, hy, 0, hx, hy, R * 0.9);
    hg.addColorStop(0, _rgba([255, 255, 255], 0.45 + 0.2 * energy));
    hg.addColorStop(0.4, _rgba([255, 255, 255], 0.08));
    hg.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = hg;
    ctx.fillRect(cx - R * 1.2, cy - R * 1.2, R * 2.4, R * 2.4);
    ctx.restore();

    // ── Partículas orbitando (toque "de otro planeta") ──
    if (S.particles) {
      ctx.save();
      ctx.globalCompositeOperation = 'lighter';
      for (let i = 0; i < S.particles.length; i++) {
        const p = S.particles[i];
        p.ang += p.spd * 0.016;                // avance suave (indep. de dt fino)
        const orbit = R * (1.15 + 0.15 * Math.sin(t * 0.8 + p.ph)) * p.rad;
        const px = cx + Math.cos(p.ang) * orbit;
        const py = cy + Math.sin(p.ang) * orbit * 0.72; // leve elipse
        const twinkle = 0.4 + 0.6 * (0.5 + 0.5 * Math.sin(t * 2 + p.ph));
        const pr = p.size * (0.8 + 0.6 * energy);
        const pg = ctx.createRadialGradient(px, py, 0, px, py, pr * 3);
        pg.addColorStop(0, _rgba([255, 255, 255], 0.9 * twinkle));
        pg.addColorStop(0.4, _rgba(col, 0.5 * twinkle));
        pg.addColorStop(1, _rgba(col, 0));
        ctx.beginPath();
        ctx.arc(px, py, pr * 3, 0, TWO_PI);
        ctx.fillStyle = pg;
        ctx.fill();
      }
      ctx.restore();
    }
  }

  // Traza un contorno cerrado y suave a partir de puntos, usando curvas
  // cuadráticas entre los puntos medios (técnica clásica de "blob").
  function _blobPath(ctx, pts) {
    const n = pts.length;
    let mx = (pts[n - 1][0] + pts[0][0]) / 2;
    let my = (pts[n - 1][1] + pts[0][1]) / 2;
    ctx.moveTo(mx, my);
    for (let i = 0; i < n; i++) {
      const cur = pts[i];
      const nxt = pts[(i + 1) % n];
      const ex = (cur[0] + nxt[0]) / 2;
      const ey = (cur[1] + nxt[1]) / 2;
      ctx.quadraticCurveTo(cur[0], cur[1], ex, ey);
    }
    ctx.closePath();
  }

  /* ── Niveles de voz (los fija el agente BIXBY) ── */
  function setUserLevel(v) {
    const x = _clamp(+v || 0, 0, 1);
    if (x > S.userTarget) S.userTarget = x;    // toma el pico (attack inmediato)
    else S.userTarget = x;                      // permite bajar si la voz baja
  }
  function setBixbyLevel(v) {
    const x = _clamp(+v || 0, 0, 1);
    if (x > S.bixbyTarget) S.bixbyTarget = x;
    else S.bixbyTarget = x;
  }

  /* ── Limpieza ── */
  function _teardownCanvas() {
    if (S.ro) { try { S.ro.disconnect(); } catch (e) {} S.ro = null; }
    if (S.canvas && S.canvas.parentNode) S.canvas.parentNode.removeChild(S.canvas);
    if (S.ownsContainer && S.container && S.container.parentNode) {
      S.container.parentNode.removeChild(S.container);
    }
    S.canvas = null; S.ctx = null; S.container = null; S.ownsContainer = false;
  }

  function destroy() {
    stop();
    if (S.onVis) { document.removeEventListener('visibilitychange', S.onVis); S.onVis = null; }
    _teardownCanvas();
    S.userTarget = S.bixbyTarget = S.userLevel = S.bixbyLevel = 0;
    S.blend = 0.5;
    S.particles = null;
  }

  /* ── API pública ── */
  window.BixbyOrb = {
    mount, start, stop, setUserLevel, setBixbyLevel, destroy,
    isMounted: function () { return !!(S.canvas && document.body.contains(S.canvas)); },
    isRunning: function () { return !!S.running; },
  };
})();
