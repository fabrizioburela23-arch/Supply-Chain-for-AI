/* ============================================================================
   engine/desktop.js — ESCRITORIO KHIPU (K1, 2026-10-04)

   Visión de Fabrizio: "la vista general sea como el interfaz de Khipu; poco a
   poco será el ÚNICO interfaz. Todo lo que se genere o abra, como una ventana
   que se puede mover y cambiar de tamaño. Punto medio entre ChatGPT y
   Windows 11: ajustar la información que se muestra sin dejar de ser un
   chatbot."

   Qué hace: convierte el escenario de la Cabina (#bcp-stage, engine/cockpit.js)
   en un ESCRITORIO. Cada escena (grafo, terminal, X-Ray, simulación, comité…)
   se abre como una VENTANA con barra de título (– ▢ ✕), se arrastra, se
   redimensiona por los 8 bordes, se pega a mitades/cuartos (snap estilo
   Windows 11, con fantasma de previsualización), se maximiza con doble clic,
   y abajo hay una BARRA DE TAREAS con lo abierto. El chat de Khipu sigue
   siempre presente (dock + barra de abajo de la Cabina). En el teléfono las
   ventanas son HOJAS a pantalla completa (sin arrastre) y la barra de tareas
   son chips para cambiar entre ellas. Tablet (dedo, ≥761 px): controles
   grandes y el selector de acomodo se abre tocando ▢.

   La Cabina es quien PINTA el contenido: registra `configure({render,title,
   icon,onClose,beforeRender,onFocus,onModeChange,resume,adoptKinds,
   resumeKinds,multiKinds})`; este módulo solo gestiona las ventanas. Una sola
   puerta: BixbyCockpit.stage(kind,arg) → KhipuDesk.open(). Geometría recordada
   por tipo en localStorage kh_desk_geom; modo ON/OFF en kh_desk_mode (OFF =
   Cabina clásica de una sola pantalla, por si algo falla).

   Lecciones de la revisión adversarial (2026-10-04, no repetir):
   · NUNCA reemitir 'resize' desde el propio escuchador de 'resize' (bucle a
     5 Hz que seguía con la Cabina cerrada): los 'resize' sintéticos
     (isTrusted=false) son PARA los motores (mapa/globos/terminal), no para
     el escritorio; el escritorio se re-adapta con un ResizeObserver.
   · NUNCA medir ni recortar geometría con el escenario oculto (0×0 →
     encogía todas las ventanas a 320×220 al cerrar la Cabina).
   · Clases de botones (kd-b-*) ≠ estados de ventana (kd-min/kd-max/kd-hide).
   · pointercancel NO es "soltar": revierte.

   window.KhipuDesk = { configure, enabled, setEnabled, active, mount, unmount,
     wall, open, close, closeKind, closeAll, focus, focused, has, get, list,
     minimize, maximize, restore, snap, tile, cascade, suspend, resume,
     isMobile, relabel }
   ============================================================================ */
(function () {
  'use strict';

  var MOBILE_MAX = 760;        // ≤ → hojas a pantalla completa (mismo corte que la Cabina)
  var MIN_W = 320, MIN_H = 220;
  var SNAP_PX = 14;            // distancia al borde del escritorio que activa el snap
  var FALLBACK = { W: 1000, H: 600 };   // solo para dibujar cuando aún no hay medida; NUNCA para recortar
  var LS_GEOM = 'kh_desk_geom', LS_MODE = 'kh_desk_mode', LS_TIP = 'kh_desk_tip', LS_AUTO = 'kh_desk_auto', LS_PINS = 'kh_desk_pins';
  var MAX_CENTER = 3;          // ventanas sueltas visibles a la vez en el centro; el resto espera en la barra
  var SIDE_FRAC = 0.32;        // ancho de una columna lateral (ventanas fijadas)

  function lang() {
    var l = window.LANG;
    if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = null; } }
    return l === 'en' ? 'en' : 'es';
  }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function ls(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function num(v, d) { v = +v; return isFinite(v) ? v : d; }
  function coarse() { try { return !!(window.matchMedia && window.matchMedia('(pointer:coarse)').matches); } catch (e) { return false; } }
  function barH() { return coarse() ? 48 : 40; }

  // ── textos de la interfaz (regla bilingüe) ──
  var T = {
    min: ['Minimizar', 'Minimize'], max: ['Maximizar', 'Maximize'], restore: ['Restaurar', 'Restore'],
    close: ['Cerrar', 'Close'], snapTip: ['Acomodar en pantalla', 'Snap layouts'],
    tile: ['▦ Mosaico', '▦ Tile'], cascade: ['⧉ Cascada', '⧉ Cascade'],
    minAll: ['▁ Minimizar todo', '▁ Minimize all'], closeAll: ['✕ Cerrar todo', '✕ Close all'],
    classic: ['▭ Una sola pantalla (modo clásico)', '▭ Single screen (classic mode)'],
    menuTip: ['Ventanas: mosaico, cascada, cerrar todo…', 'Windows: tile, cascade, close all…'],
    hint: ['Todo lo que abras aparece aquí como ventana: muévela, cámbiale el tamaño o pégala a un borde.',
           'Everything you open shows up here as a window: move it, resize it or snap it to an edge.'],
    hintMobile: ['Lo que abras aparece aquí; cambia entre pantallas con estos botones.',
                 'What you open shows up here; switch between screens with the buttons.'],
    back: ['‹ Volver', '‹ Back'],
    pin: ['Fijar a un costado (seguir viéndola mientras escribes)', 'Pin to a side (keep seeing it while you type)'],
    unpin: ['Soltar del costado', 'Unpin from the side'],
    auto: ['✓ Ordenar automáticamente', '✓ Arrange automatically'], autoOff: ['○ Ordenar automáticamente', '○ Arrange automatically'],
    arrange: ['▦ Ordenar ahora', '▦ Arrange now'],
    tipTitle: ['Tu primera ventana', 'Your first window'],
    tip: ['Arrástrala por la barra de título. Llévala a un borde para pegarla a media pantalla, doble clic para agrandarla, y ▢ para elegir dónde acomodarla.',
          'Drag it by its title bar. Move it to an edge to snap it to half the screen, double-click to enlarge it, and ▢ to choose where to place it.'],
    zones: { left: ['Mitad izquierda', 'Left half'], right: ['Mitad derecha', 'Right half'],
             tl: ['Cuarto superior izquierdo', 'Top-left quarter'], tr: ['Cuarto superior derecho', 'Top-right quarter'],
             bl: ['Cuarto inferior izquierdo', 'Bottom-left quarter'], br: ['Cuarto inferior derecho', 'Bottom-right quarter'],
             max: ['Pantalla completa', 'Full screen'] },
  };
  function t(k) { var v = T[k]; return v ? (lang() === 'en' ? v[1] : v[0]) : k; }

  // ── estado ──
  var hooks = { render: null, title: null, icon: null, onClose: null, beforeRender: null, onFocus: null, onModeChange: null,
                resume: null, adoptKinds: [], resumeKinds: [], multiKinds: [] };
  var stageEl = null, wallEl = null, winsEl = null, barEl = null, ghostEl = null, menuEl = null, layoutsEl = null;
  var wins = [];            // [{id, kind, arg, key, el, body, x,y,w,h, max, min, snap, prev, needsRender}]
  var zTop = 10, seq = 0, focused = null;
  var resizeT = null, fireT = null, layT = null, ro = null, wasMobile = null, lastSz = null;

  function enabled() { return ls(LS_MODE) !== 'off'; }
  function isMobile() { return (window.innerWidth || 1024) <= MOBILE_MAX; }
  function active() { return !!(stageEl && stageEl.classList.contains('kd-desk') && winsEl && stageEl.contains(winsEl)); }
  function visible() { return !!(winsEl && winsEl.offsetWidth && winsEl.offsetHeight); }   // la Cabina está abierta y con layout

  // ── estilos ──
  function ensureStyles() {
    if (document.getElementById('kd-styles')) return;
    var css = '' +
'#bcp-stage.kd-desk{padding:0!important;overflow:hidden!important;position:relative;--kd-bar:40px}' +
'#bcp-stage.kd-desk>*{animation:none}' +
'#kd-wall{position:absolute;left:0;right:0;top:0;bottom:var(--kd-bar);overflow-y:auto;padding:22px;scrollbar-width:thin}' +
'#kd-wins{position:absolute;left:0;right:0;top:0;bottom:var(--kd-bar);pointer-events:none;overflow:hidden}' +
'.kd-win{position:absolute;pointer-events:auto;display:flex;flex-direction:column;min-width:' + MIN_W + 'px;min-height:' + MIN_H + 'px;' +
  'border:1px solid rgba(122,158,255,.22);border-radius:14px;background:#070B14;' +
  'box-shadow:0 18px 50px rgba(0,0,0,.55),0 0 0 1px rgba(0,0,0,.4);overflow:hidden;animation:kdIn .16s ease;' +
  'transition:box-shadow .15s,border-color .15s}' +
'@keyframes kdIn{from{opacity:0;transform:scale(.985)}to{opacity:1;transform:none}}' +
'@media(prefers-reduced-motion:reduce){.kd-win{animation:none}}' +
'.kd-win.kd-focus{border-color:rgba(0,224,255,.55);box-shadow:0 22px 60px rgba(0,0,0,.65),0 0 0 1px rgba(0,224,255,.18)}' +
'.kd-win.kd-min,.kd-win.kd-hide{display:none}' +
'.kd-win.kd-max{left:0!important;top:0!important;width:100%!important;height:100%!important;border-radius:0;border-left:0;border-right:0;border-top:0}' +
'.kd-win.kd-drag{transition:none;opacity:.92}' +
'.kd-ttl{display:flex;align-items:center;gap:8px;height:36px;padding:0 6px 0 12px;flex-shrink:0;cursor:grab;user-select:none;-webkit-user-select:none;touch-action:none;' +
  'background:linear-gradient(180deg,rgba(14,21,38,.95),rgba(9,14,26,.95));border-bottom:1px solid rgba(122,158,255,.14);font-size:12.5px;color:#C7D0EA}' +
'.kd-win.kd-focus .kd-ttl{color:#E8EDFB}' +
'.kd-ttl:active{cursor:grabbing}' +
'.kd-ico{font-size:14px;flex:none}' +
'.kd-name{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:650;letter-spacing:.01em}' +
'.kd-b{width:30px;height:26px;border-radius:7px;border:0;background:transparent;color:#9BA6C4;cursor:pointer;font-size:12px;' +
  'display:inline-flex;align-items:center;justify-content:center;font-family:inherit;flex:none;touch-action:manipulation}' +
'.kd-b:hover{background:rgba(122,158,255,.14);color:#E8EDFB}' +
'.kd-b.kd-b-x:hover{background:rgba(255,77,106,.22);color:#FF8FA3}' +
'.kd-b.kd-b-pin{font-size:13px}.kd-win.kd-pinned .kd-b-pin{color:#00E0FF;background:rgba(0,224,255,.12)}' +
'.kd-win.kd-pinned{border-color:rgba(0,224,255,.3)}.kd-win.kd-pinned .kd-ttl{cursor:default}' +
'#bcp-stage.kd-mobile .kd-b-pin{display:none}' +
'.kd-body{flex:1;min-height:0;overflow:auto;padding:16px 18px;display:flex;flex-direction:column;scrollbar-width:thin;scrollbar-color:rgba(122,158,255,.35) transparent}' +
'.kd-body>*{flex-shrink:0}' +
'.kd-body>.bcp-stagehd{display:none}' +            // en una ventana el "← Inicio" sobra: hay ✕
'.kd-body .xray-scope .xr-close{display:none}' +    // el ✕ propio del X-Ray (cierra su overlay) sobra dentro de una ventana
'.kd-body>.bcp-embed{flex:1 1 auto;height:auto!important;min-height:0!important}' +
'.kd-body>.bcp-inner{width:100%}' +
'.kd-body.kd-embedbody{padding:0}' +
'.kd-body.kd-embedbody>.bcp-embed{border:0;border-radius:0}' +
'.kd-rs{position:absolute;z-index:3;touch-action:none}' +
'.kd-rs.n{left:8px;right:8px;top:-3px;height:7px;cursor:ns-resize}.kd-rs.s{left:8px;right:8px;bottom:-3px;height:7px;cursor:ns-resize}' +
'.kd-rs.e{top:8px;bottom:8px;right:-3px;width:7px;cursor:ew-resize}.kd-rs.w{top:8px;bottom:8px;left:-3px;width:7px;cursor:ew-resize}' +
'.kd-rs.ne{right:-4px;top:-4px;width:14px;height:14px;cursor:nesw-resize}.kd-rs.sw{left:-4px;bottom:-4px;width:14px;height:14px;cursor:nesw-resize}' +
'.kd-rs.nw{left:-4px;top:-4px;width:14px;height:14px;cursor:nwse-resize}.kd-rs.se{right:-4px;bottom:-4px;width:14px;height:14px;cursor:nwse-resize}' +
'.kd-win.kd-max .kd-rs{display:none}' +
'#kd-ghost{position:absolute;display:none;pointer-events:none;border:1.5px solid rgba(0,224,255,.55);border-radius:14px;' +
  'background:rgba(0,224,255,.08);backdrop-filter:blur(2px);z-index:9000;transition:left .08s,top .08s,width .08s,height .08s}' +
'#kd-bar{position:absolute;left:0;right:0;bottom:0;height:var(--kd-bar);display:flex;align-items:center;gap:6px;padding:0 10px;' +
  'background:rgba(6,10,19,.92);border-top:1px solid rgba(122,158,255,.16);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);z-index:9100;overflow:hidden}' +
'#kd-bar .kd-tasks{flex:1;min-width:0;display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;align-items:center;height:100%}' +
'#kd-bar .kd-tasks::-webkit-scrollbar{display:none}' +
'.kd-task{flex:none;max-width:200px;height:28px;padding:0 11px;border-radius:9px;border:1px solid rgba(122,158,255,.18);background:rgba(11,18,34,.7);' +
  'color:#9BA6C4;font-size:12px;cursor:pointer;display:inline-flex;align-items:center;gap:6px;font-family:inherit;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;transition:all .13s}' +
'.kd-task:hover{color:#E8EDFB;border-color:rgba(0,224,255,.45)}' +
'.kd-task.on{color:#00E0FF;border-color:rgba(0,224,255,.55);background:rgba(0,224,255,.09)}' +
'.kd-task.dim{opacity:.55}' +
'.kd-task .tx{overflow:hidden;text-overflow:ellipsis}' +
'.kd-hint{flex:1;min-width:0;font-size:11.5px;color:#8791AC;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding-left:4px}' +
'#kd-menu-btn{flex:none;width:32px;height:28px;border-radius:9px;border:1px solid rgba(122,158,255,.22);background:rgba(11,18,34,.7);color:#9BA6C4;cursor:pointer;font-size:15px;font-family:inherit;display:inline-flex;align-items:center;justify-content:center}' +
'#kd-menu-btn:hover,#kd-menu-btn.on{color:#00E0FF;border-color:rgba(0,224,255,.5)}' +
'#kd-menu{position:absolute;left:10px;bottom:calc(var(--kd-bar) + 6px);display:none;flex-direction:column;gap:2px;padding:6px;min-width:230px;z-index:9200;' +
  'border:1px solid rgba(122,158,255,.25);border-radius:12px;background:rgba(8,12,22,.97);box-shadow:0 14px 40px rgba(0,0,0,.6)}' +
'#kd-menu.show{display:flex}' +
'#kd-menu button{text-align:left;border:0;background:transparent;color:#C7D0EA;font-size:12.5px;padding:8px 10px;border-radius:8px;cursor:pointer;font-family:inherit}' +
'#kd-menu button:hover{background:rgba(122,158,255,.14);color:#fff}' +
'#kd-menu .sep{height:1px;background:rgba(122,158,255,.14);margin:4px 2px}' +
'#kd-layouts{position:absolute;display:none;z-index:9300;padding:8px;gap:6px;grid-template-columns:repeat(3,56px);' +
  'border:1px solid rgba(122,158,255,.25);border-radius:12px;background:rgba(8,12,22,.97);box-shadow:0 14px 40px rgba(0,0,0,.6)}' +
'#kd-layouts.show{display:grid}' +
'.kd-lay{width:56px;height:38px;border-radius:7px;border:1px solid rgba(122,158,255,.25);background:rgba(11,18,34,.8);cursor:pointer;position:relative;padding:0}' +
'.kd-lay:hover{border-color:rgba(0,224,255,.6)}' +
'.kd-lay i{position:absolute;background:rgba(0,224,255,.35);border-radius:3px}' +
'.kd-lay:hover i{background:rgba(0,224,255,.7)}' +
// tablet / pantalla táctil con ventanas (≥761 px): controles para el dedo
'@media(pointer:coarse){' +
  '.kd-ttl{height:44px}.kd-b{width:40px;height:36px;font-size:14px}' +
  '.kd-rs.n,.kd-rs.s{height:16px}.kd-rs.e,.kd-rs.w{width:16px}' +
  '.kd-rs.n{top:-6px}.kd-rs.s{bottom:-6px}.kd-rs.e{right:-6px}.kd-rs.w{left:-6px}' +
  '.kd-rs.ne,.kd-rs.nw,.kd-rs.se,.kd-rs.sw{width:26px;height:26px}' +
  '.kd-task{height:36px}#kd-menu-btn{width:40px;height:36px}' +
  '.kd-lay{width:64px;height:46px}#kd-layouts{grid-template-columns:repeat(3,64px)}' +
  '#kd-menu button{padding:11px 12px}' +
'}' +
// móvil: hojas a pantalla completa, sin arrastre ni redimensión
'#bcp-stage.kd-mobile #kd-wall{padding:14px 12px}' +
'#bcp-stage.kd-mobile .kd-win{left:0!important;top:0!important;width:100%!important;height:100%!important;border-radius:0;border:0;animation:kdSheet .18s ease}' +
'@keyframes kdSheet{from{transform:translateY(12px);opacity:0}to{transform:none;opacity:1}}' +
'#bcp-stage.kd-mobile .kd-rs,#bcp-stage.kd-mobile .kd-b-min,#bcp-stage.kd-mobile .kd-b-max{display:none}' +
'#bcp-stage.kd-mobile .kd-ttl{cursor:default}' +
'#bcp-stage.kd-mobile .kd-body{padding:12px}' +
'#bcp-stage.kd-mobile .kd-b.kd-b-x{width:auto;padding:0 10px;font-size:12px}' +
'#bcp-stage.kd-mobile #kd-menu{min-width:200px}' +
'';
    var st = document.createElement('style'); st.id = 'kd-styles'; st.textContent = css;
    document.head.appendChild(st);
  }

  // ── montaje del escritorio sobre el escenario de la Cabina ──
  function mount(stage) {
    ensureStyles();
    stageEl = stage;
    if (active()) { applyMode(); return; }
    stage.innerHTML = '';
    stage.classList.add('kd-desk');
    stage.style.setProperty('--kd-bar', barH() + 'px');
    wallEl = document.createElement('div'); wallEl.id = 'kd-wall';
    winsEl = document.createElement('div'); winsEl.id = 'kd-wins';
    ghostEl = document.createElement('div'); ghostEl.id = 'kd-ghost';
    barEl = document.createElement('div'); barEl.id = 'kd-bar';
    barEl.innerHTML = '<button type="button" id="kd-menu-btn">⊞</button><div class="kd-tasks"></div>';
    menuEl = document.createElement('div'); menuEl.id = 'kd-menu';
    layoutsEl = document.createElement('div'); layoutsEl.id = 'kd-layouts';
    stage.appendChild(wallEl); stage.appendChild(winsEl); stage.appendChild(ghostEl);
    stage.appendChild(barEl); stage.appendChild(menuEl); stage.appendChild(layoutsEl);
    barEl.querySelector('#kd-menu-btn').addEventListener('click', function (e) { e.stopPropagation(); toggleMenu(); });
    // clic fuera cierra menú y selector de acomodo (se registra UNA vez por escenario:
    // el escritorio puede desmontarse y volver a montarse —modo clásico y vuelta—)
    if (!stage._kdWired) {
      stage._kdWired = true;
      stage.addEventListener('pointerdown', function (e) {
        if (!active()) return;
        if (menuEl.classList.contains('show') && !menuEl.contains(e.target) && e.target.id !== 'kd-menu-btn') toggleMenu(false);
        if (layoutsEl.classList.contains('show') && !layoutsEl.contains(e.target) && !(e.target.closest && e.target.closest('.kd-b-max'))) hideLayouts();
      });
    }
    layoutsEl.addEventListener('mouseleave', function () { hideLayouts(); });
    // re-adaptar al cambiar el tamaño: del navegador (giro del teléfono) y del propio
    // escenario (aparece/desaparece el dock del chat). Los 'resize' SINTÉTICOS
    // (fireResize, adoptInto/restoreAdopted de la Cabina) se ignoran: son para los motores.
    window.removeEventListener('resize', onResize);
    window.addEventListener('resize', onResize);
    if (ro) { try { ro.disconnect(); } catch (e) {} ro = null; }
    if (window.ResizeObserver) { try { ro = new ResizeObserver(function () { onResize(); }); ro.observe(winsEl); } catch (e) { ro = null; } }
    wasMobile = isMobile();
    barSig = null;
    applyMode();
    renderBar();
    // ventanas existentes (vuelta del modo clásico)
    wins.forEach(function (w) { winsEl.appendChild(w.el); });
  }

  function unmount() {
    if (!stageEl) return;
    closeAll();
    toggleMenu(false); hideLayouts();
    clearTimeout(resizeT); clearTimeout(fireT); clearTimeout(layT);
    window.removeEventListener('resize', onResize);
    if (ro) { try { ro.disconnect(); } catch (e) {} ro = null; }
    stageEl.classList.remove('kd-desk', 'kd-mobile');
    stageEl.style.removeProperty('--kd-bar');
    stageEl.innerHTML = '';
    wallEl = winsEl = barEl = ghostEl = menuEl = layoutsEl = null;
    lastSz = null; barSig = null;
  }

  function applyMode() {
    if (!stageEl) return;
    var m = isMobile();
    stageEl.classList.toggle('kd-mobile', m);
    stageEl.style.setProperty('--kd-bar', barH() + 'px');
    if (!visible()) return;               // Cabina cerrada: no hay medida válida, no se toca nada
    if (m) { showOnly(focused); return; }
    showOnly(null);
    if (autoOn() && wins.some(function (w) { return !w.min; })) { arrange(); return; }
    wins.forEach(function (w) {
      if (w.max) return;
      if (w.snap && w.snap !== 'grid') { var r = zoneRect(w.snap); if (r) { w.x = r.x; w.y = r.y; w.w = r.w; w.h = r.h; } }
      place(w);
    });
  }
  function onResize(e) {
    if (!active()) return;
    if (e && e.isTrusted === false) return;   // 'resize' emitido por fireResize/la Cabina: es para los motores, no para nosotros
    if (!visible()) return;
    clearTimeout(resizeT);
    resizeT = setTimeout(function () {
      if (!active() || !visible()) return;
      var d = deskSize(), changed = !lastSz || !d || d.W !== lastSz.W || d.H !== lastSz.H;
      lastSz = d;
      var nowMobile = isMobile();
      applyMode();
      if (wasMobile !== nowMobile) { wasMobile = nowMobile; relabel(); } else if (changed) renderBar();
      // los motores alojados (mapa/globos/terminal) deben re-medir si cambió el área real
      if (changed && wins.some(function (w) { return !w.min && hooks.adoptKinds.indexOf(w.kind) >= 0; })) fireResize();
    }, 120);
  }
  // los motores (mapa, globos, terminal) miden su contenedor al evento resize;
  // solo se dispara cuando cambia una ventana que aloja uno (adoptKinds), no por un X-Ray
  function fireResize(w) {
    if (w && hooks.adoptKinds.indexOf(w.kind) < 0) return;
    clearTimeout(fireT);
    fireT = setTimeout(function () { try { window.dispatchEvent(new Event('resize')); } catch (e) {} }, 80);
  }

  // medida del escritorio; null si está oculto (Cabina cerrada / sin layout)
  function deskSize() {
    if (!winsEl) return null;
    var r = winsEl.getBoundingClientRect();
    if (!r.width || !r.height) return null;
    return { W: Math.max(300, Math.round(r.width)), H: Math.max(200, Math.round(r.height)) };
  }
  function drawSize() { return deskSize() || FALLBACK; }

  // ── geometría recordada por tipo ──
  function geomStore() {
    try { var g = JSON.parse(ls(LS_GEOM) || '{}'); return (g && typeof g === 'object' && !Array.isArray(g)) ? g : {}; } catch (e) { return {}; }
  }
  function saveGeom(w) {
    if (isMobile() || !deskSize()) return;
    var g = geomStore();
    g[w.kind] = { x: w.x, y: w.y, w: w.w, h: w.h, max: !!w.max, snap: w.snap || null };
    lsSet(LS_GEOM, JSON.stringify(g));
  }
  function defaultGeom(kind, n) {
    var d = drawSize();
    var saved = geomStore()[kind];
    var w, h, x, y;
    if (saved && typeof saved === 'object' && num(saved.w, 0) >= MIN_W && num(saved.h, 0) >= MIN_H) {
      w = Math.min(num(saved.w, MIN_W), d.W); h = Math.min(num(saved.h, MIN_H), d.H);
      x = clamp(num(saved.x, 0), 0, Math.max(0, d.W - 60)); y = clamp(num(saved.y, 0), 0, Math.max(0, d.H - 40));
      var snap = (typeof saved.snap === 'string' && T.zones[saved.snap]) ? saved.snap : null;
      return { x: x, y: y, w: w, h: h, max: !!saved.max, snap: snap };
    }
    w = clamp(Math.round(d.W * 0.64), MIN_W, Math.max(MIN_W, d.W - 24));
    h = clamp(Math.round(d.H * 0.74), MIN_H, Math.max(MIN_H, d.H - 24));
    var off = 28 * (n % 7);
    x = clamp(Math.round((d.W - w) / 2) + off - 60, 0, Math.max(0, d.W - w));
    y = clamp(14 + off, 0, Math.max(0, d.H - h));
    return { x: x, y: y, w: w, h: h, max: d.W < 900, snap: null };
  }
  function place(w) {
    if (!w.el) return;
    var d = deskSize();
    if (d) {   // nunca se recorta contra un escenario oculto; siempre quedan ≥ 80 px de barra de título a la vista
      w.w = clamp(num(w.w, MIN_W), MIN_W, Math.max(MIN_W, d.W)); w.h = clamp(num(w.h, MIN_H), MIN_H, Math.max(MIN_H, d.H));
      w.x = clamp(num(w.x, 0), -(w.w - 80), Math.max(0, d.W - 80));
      w.y = clamp(num(w.y, 0), 0, Math.max(0, d.H - 36));
    }
    w.el.style.left = w.x + 'px'; w.el.style.top = w.y + 'px';
    w.el.style.width = w.w + 'px'; w.el.style.height = w.h + 'px';
    w.el.classList.toggle('kd-max', !!w.max);
    var mb = w.el.querySelector('.kd-b-max');
    if (mb) { mb.textContent = w.max ? '❐' : '▢'; mb.title = w.max ? t('restore') : t('max'); }
  }

  // ── ventanas ──
  function keyFor(kind, arg) {
    var multi = hooks.multiKinds.indexOf(kind) >= 0;
    if (!multi) return kind;
    var a = arg;
    if (a && typeof a === 'object') {
      a = a.id || a.a || a.scenario || a.ticker || '';
      if (typeof a === 'object') a = '';
    }
    return kind + ':' + String(a == null ? '' : a).toLowerCase();
  }
  function get(id) { for (var i = 0; i < wins.length; i++) if (wins[i].id === id || wins[i].key === id) return wins[i]; return null; }
  function has(kind) { return wins.some(function (w) { return w.kind === kind; }); }
  function list() { return wins.map(function (w) { return { id: w.id, kind: w.kind, key: w.key, min: !!w.min, max: !!w.max, focused: focused === w.id }; }); }

  function titleFor(w) {
    var s = '';
    try { s = hooks.title ? hooks.title(w.kind, w.arg) : ''; } catch (e) { s = ''; }
    return String(s || w.kind);
  }
  function iconFor(w) {
    try { return String((hooks.icon && hooks.icon(w.kind)) || '▫'); } catch (e) { return '▫'; }
  }

  function open(kind, arg, opts) {
    opts = opts || {};
    if (!active() || !hooks.render) return null;
    if (opts.solo) wins.slice().forEach(function (o) { if (o.kind !== kind) close(o.id); });
    var key = keyFor(kind, arg);
    var w = get(key);
    if (w) {
      // ya existe: con argumento nuevo se re-pinta; si no, solo al frente
      if (arg != null) rerender(w, arg);
      if (w.min) { w.min = false; w.el.classList.remove('kd-min'); }
      if (opts.max && !isMobile()) maximize(w.id, true);
      focus(w.id);
      renderBar();
      return w.id;
    }
    var g = defaultGeom(kind, wins.length);
    w = { id: 'kd' + (++seq), kind: kind, arg: arg, key: key, x: g.x, y: g.y, w: g.w, h: g.h,
          max: !!(g.max || opts.max), min: false, snap: g.snap, prev: null, needsRender: false,
          pinned: (pinStore()[kind] === 'left' || pinStore()[kind] === 'right') ? pinStore()[kind] : null };
    var el = document.createElement('div');
    el.className = 'kd-win'; el.setAttribute('data-id', w.id); el.setAttribute('data-kind', kind);
    el.setAttribute('role', 'dialog');
    el.innerHTML =
      '<div class="kd-ttl"><span class="kd-ico"></span><span class="kd-name"></span>' +
        '<button type="button" class="kd-b kd-b-pin">📌</button>' +
        '<button type="button" class="kd-b kd-b-min">–</button>' +
        '<button type="button" class="kd-b kd-b-max">▢</button>' +
        '<button type="button" class="kd-b kd-b-x">✕</button></div>' +
      '<div class="kd-body"></div>' +
      ['n', 's', 'e', 'w', 'ne', 'nw', 'se', 'sw'].map(function (d) { return '<div class="kd-rs ' + d + '" data-d="' + d + '"></div>'; }).join('');
    w.el = el; w.body = el.querySelector('.kd-body');
    wins.push(w);
    winsEl.appendChild(el);
    relabelWin(w);
    wireWin(w);
    if (w.snap && !w.max) { var zr = zoneRect(w.snap); if (zr) { w.x = zr.x; w.y = zr.y; w.w = zr.w; w.h = zr.h; } }
    place(w);
    render(w);
    focus(w.id);
    if (autoOn() && !opts.max) arrange(); else renderBar();
    firstTip();
    return w.id;
  }

  // ── ORDEN AUTOMÁTICO + FIJAR A UN COSTADO (pedido 2026-10-04: "que no se vea saturado") ──
  // Ventanas FIJADAS (📌) viven en una columna lateral (izq./der.) apiladas y siguen
  // a la vista mientras escribes; las sueltas se reparten en el centro (máximo
  // MAX_CENTER: las más antiguas pasan a la barra de tareas). Se re-ordena al
  // abrir, cerrar, minimizar o fijar. Arrastrar o redimensionar una ventana es
  // manual y se respeta hasta el siguiente cambio.
  function autoOn() { return ls(LS_AUTO) !== 'off'; }
  function setAuto(on) { lsSet(LS_AUTO, on ? 'on' : 'off'); if (on) arrange(); }
  function pinStore() { try { var g = JSON.parse(ls(LS_PINS) || '{}'); return (g && typeof g === 'object') ? g : {}; } catch (e) { return {}; } }
  function pin(id, side) {
    var w = get(id); if (!w) return;
    if (side === undefined) side = w.pinned ? null : (wins.some(function (o) { return o !== w && o.pinned === 'right'; }) && !wins.some(function (o) { return o !== w && o.pinned === 'left'; }) ? 'left' : 'right');
    w.pinned = side || null; w.max = false; w.snap = null; w.min = false; w.manual = false; w.el.classList.remove('kd-min');
    var ps = pinStore(); if (side) ps[w.kind] = side; else delete ps[w.kind]; lsSet(LS_PINS, JSON.stringify(ps));
    relabelWin(w);
    arrange(true);
    focus(w.id);
  }
  function setRect(w, r) {
    w.max = false; w.snap = null;
    w.x = r.x; w.y = r.y; w.w = Math.max(MIN_W, r.w); w.h = Math.max(MIN_H, r.h);
    place(w);
  }
  function arrange(force) {
    if (isMobile() || !visible()) { renderBar(); return; }
    if (!force && !autoOn()) { renderBar(); return; }
    var d = deskSize(); if (!d) return;
    if (force) wins.forEach(function (w) { w.manual = false; });   // "Ordenar ahora" / fijar: vuelve a mandar el orden
    var L = wins.filter(function (w) { return w.pinned === 'left'; }), R = wins.filter(function (w) { return w.pinned === 'right'; });
    // una ventana que el usuario movió o redimensionó a mano se respeta (w.manual) hasta "Ordenar ahora"
    var C = wins.filter(function (w) { return !w.pinned && !w.min && !w.manual; });
    // demasiadas sueltas: las más antiguas (menor z) esperan en la barra
    C.sort(function (a, b) { return (+a.el.style.zIndex || 0) - (+b.el.style.zIndex || 0); });
    while (C.length > MAX_CENTER) { var old = C.shift(); old.min = true; old.el.classList.add('kd-min'); }
    var colW = Math.max(MIN_W, Math.round(d.W * SIDE_FRAC));
    if (L.length && R.length && d.W - 2 * colW < MIN_W) colW = Math.max(MIN_W, Math.floor(d.W / 3));
    var x0 = L.length ? colW : 0, x1 = R.length ? d.W - colW : d.W;
    function column(list, x) {
      var h = Math.floor(d.H / list.length);
      list.forEach(function (w, i) { setRect(w, { x: x, y: i * h, w: colW, h: i === list.length - 1 ? d.H - i * h : h }); });
    }
    if (L.length) column(L, 0);
    if (R.length) column(R, x1);
    var cw = x1 - x0, hw = Math.round(cw / 2), hh = Math.round(d.H / 2);
    var n = C.length;
    if (n === 1) setRect(C[0], { x: x0, y: 0, w: cw, h: d.H });
    else if (n === 2) {
      if (cw >= 2 * MIN_W) { setRect(C[0], { x: x0, y: 0, w: hw, h: d.H }); setRect(C[1], { x: x0 + hw, y: 0, w: cw - hw, h: d.H }); }
      else { setRect(C[0], { x: x0, y: 0, w: cw, h: hh }); setRect(C[1], { x: x0, y: hh, w: cw, h: d.H - hh }); }
    } else if (n >= 3) {
      if (cw >= 2 * MIN_W) {
        setRect(C[n - 1], { x: x0, y: 0, w: hw, h: d.H });   // la más reciente, grande a la izquierda
        setRect(C[n - 3], { x: x0 + hw, y: 0, w: cw - hw, h: hh }); setRect(C[n - 2], { x: x0 + hw, y: hh, w: cw - hw, h: d.H - hh });
      } else {
        var th = Math.floor(d.H / n);
        C.forEach(function (w, i) { setRect(w, { x: x0, y: i * th, w: cw, h: i === n - 1 ? d.H - i * th : th }); });
      }
    }
    if (wins.some(function (w) { return !w.min && hooks.adoptKinds.indexOf(w.kind) >= 0; })) fireResize();
    renderBar();
  }

  // la primera vez: cómo se usan las ventanas (una sola vez, solo con ratón/tablet)
  function firstTip() {
    if (isMobile() || ls(LS_TIP) || wins.length !== 1) return;
    lsSet(LS_TIP, '1');
    try {
      if (window.KhipuToast && window.KhipuToast.show) window.KhipuToast.show({ kind: 'info', title: '🪟 ' + t('tipTitle'), body: t('tip') });
    } catch (e) {}
  }

  function relabelWin(w) {
    w.el.querySelector('.kd-ico').textContent = iconFor(w);
    var ttl = titleFor(w);
    w.el.querySelector('.kd-name').textContent = ttl;
    w.el.setAttribute('aria-label', ttl);
    var b = w.el.querySelector('.kd-b-min'); b.title = t('min'); b.setAttribute('aria-label', t('min'));
    b = w.el.querySelector('.kd-b-max'); b.title = w.max ? t('restore') : t('max'); b.setAttribute('aria-label', b.title);
    b = w.el.querySelector('.kd-b-x'); b.title = t('close'); b.setAttribute('aria-label', t('close'));
    b.textContent = isMobile() ? t('back') : '✕';
    b = w.el.querySelector('.kd-b-pin'); b.title = w.pinned ? t('unpin') : t('pin'); b.setAttribute('aria-label', b.title);
    w.el.classList.toggle('kd-pinned', !!w.pinned);
  }
  function relabel() {
    wins.forEach(relabelWin);
    barSig = null;
    renderBar();
  }

  function render(w) {
    try { hooks.render(w.body, w.kind, w.arg, w.id); } catch (e) {
      w.body.innerHTML = '<div class="bcp-loading" style="color:#FF4D6A">⚠ ' + esc((e && e.message) || e) + '</div>';
    }
    w.needsRender = false;
    // escenas que adoptan un panel completo (grafo, terminal, globos…) van sin márgenes
    var emb = w.body.querySelector(':scope > .bcp-embed');
    w.body.classList.toggle('kd-embedbody', !!emb);
    fireResize(w);
  }
  function rerender(w, arg) {
    try { if (hooks.beforeRender) hooks.beforeRender(w.kind, w.id); } catch (e) {}
    w.arg = arg;
    w.body.innerHTML = '';
    relabelWin(w);
    render(w);
  }

  // móvil: solo la hoja enfocada existe para el layout (display:none → los motores
  // WebGL/burbujas/timers se duermen solos; visibility:hidden no los dormía)
  function showOnly(id) {
    wins.forEach(function (o) { o.el.classList.toggle('kd-hide', !!id && o.id !== id); });
  }

  function focus(id) {
    var w = get(id); if (!w) return;
    if (w.min) { w.min = false; w.el.classList.remove('kd-min'); }
    var changed = focused !== w.id;
    if (changed) {
      if (zTop > 4000) {   // renormalizar (los z de fantasma/barra/menús empiezan en 9000)
        wins.slice().sort(function (a, b) { return (+a.el.style.zIndex || 0) - (+b.el.style.zIndex || 0); })
          .forEach(function (o, i) { o.el.style.zIndex = 10 + i; });
        zTop = 10 + wins.length;
      }
      zTop++;
      w.el.style.zIndex = zTop;
      wins.forEach(function (o) { o.el.classList.toggle('kd-focus', o === w); });
      focused = w.id;
    }
    if (isMobile()) { showOnly(w.id); if (changed) fireResize(w); }   // la hoja pudo girar mientras estaba oculta
    try { if (hooks.onFocus) hooks.onFocus(w.kind, w.id); } catch (e) {}
    renderBar();
  }
  function topVisible() {
    var best = null;
    wins.forEach(function (w) { if (!w.min && (!best || (+w.el.style.zIndex || 0) > (+best.el.style.zIndex || 0))) best = w; });
    return best;
  }
  function refocusAfter() {
    focused = null;
    var nx = topVisible();
    if (nx) focus(nx.id);
    else { if (isMobile()) showOnly(null); try { if (hooks.onFocus) hooks.onFocus(null, null); } catch (e) {} }
  }

  function close(id) {
    var w = get(id); if (!w) return false;
    wins = wins.filter(function (o) { return o !== w; });        // primero sale de la lista (has() ya dice que no)
    try { if (hooks.onClose) hooks.onClose(w.kind, w.id); } catch (e) {}   // la Cabina devuelve lo adoptado
    if (w.el && w.el.parentNode) w.el.parentNode.removeChild(w.el);
    if (layoutsFor === w.id) hideLayouts();
    if (focused === w.id) refocusAfter();
    if (autoOn()) arrange(); else renderBar();
    return true;
  }
  function closeKind(kind) { wins.slice().forEach(function (w) { if (w.kind === kind) close(w.id); }); }
  function closeAll() { wins.slice().forEach(function (w) { close(w.id); }); }

  function minimize(id) {
    var w = get(id); if (!w) return;
    w.min = true; w.el.classList.add('kd-min');
    if (layoutsFor === w.id) hideLayouts();
    if (focused === w.id) refocusAfter();
    if (autoOn()) arrange(); else renderBar();
  }
  function maximize(id, on) {
    var w = get(id); if (!w) return;
    if (on == null) on = !w.max;
    if (on && w.pinned) { w.pinned = null; relabelWin(w); }
    if (on && !w.max) { w.prev = { x: w.x, y: w.y, w: w.w, h: w.h }; }
    if (!on && w.prev) { w.x = w.prev.x; w.y = w.prev.y; w.w = w.prev.w; w.h = w.prev.h; }
    w.max = on; w.snap = null;
    place(w); saveGeom(w); fireResize(w);
  }
  function restore(id) { var w = get(id); if (!w) return; if (w.max) maximize(id, false); focus(id); }

  // zonas de snap (estilo Windows 11)
  function zoneRect(zone) {
    var d = drawSize(), hw = Math.round(d.W / 2), hh = Math.round(d.H / 2);
    switch (zone) {
      case 'left': return { x: 0, y: 0, w: hw, h: d.H };
      case 'right': return { x: hw, y: 0, w: d.W - hw, h: d.H };
      case 'tl': return { x: 0, y: 0, w: hw, h: hh };
      case 'tr': return { x: hw, y: 0, w: d.W - hw, h: hh };
      case 'bl': return { x: 0, y: hh, w: hw, h: d.H - hh };
      case 'br': return { x: hw, y: hh, w: d.W - hw, h: d.H - hh };
      case 'max': return { x: 0, y: 0, w: d.W, h: d.H };
    }
    return null;
  }
  function snapTo(id, zone) {
    var w = get(id); if (!w) return;
    if (zone === 'max') { maximize(id, true); return; }
    var r = zoneRect(zone); if (!r) return;
    if (!w.snap && !w.max) w.prev = { x: w.x, y: w.y, w: w.w, h: w.h };
    w.max = false; w.snap = zone;
    w.x = r.x; w.y = r.y; w.w = Math.max(MIN_W, r.w); w.h = Math.max(MIN_H, r.h);
    place(w); saveGeom(w); fireResize(w);
  }
  function zoneAt(px, py) {
    var d = drawSize();
    var l = px <= SNAP_PX, r = px >= d.W - SNAP_PX, tp = py <= SNAP_PX, b = py >= d.H - SNAP_PX;
    if (tp && !l && !r) return 'max';
    if (l && tp) return 'tl'; if (r && tp) return 'tr'; if (l && b) return 'bl'; if (r && b) return 'br';
    if (l) return 'left'; if (r) return 'right';
    return null;
  }
  function showGhost(zone) {
    if (!ghostEl) return;
    if (!zone) { ghostEl.style.display = 'none'; return; }
    var r = zoneRect(zone);
    ghostEl.style.display = 'block';
    ghostEl.style.left = r.x + 'px'; ghostEl.style.top = r.y + 'px'; ghostEl.style.width = r.w + 'px'; ghostEl.style.height = r.h + 'px';
  }

  // selector de acomodo (aparece al pasar por ▢ con el ratón; con el dedo, al tocar ▢)
  var layoutsFor = null;
  function showLayouts(w, btn) {
    if (isMobile() || !layoutsEl) return;
    layoutsFor = w.id;
    var zones = ['left', 'right', 'max', 'tl', 'tr', 'bl', 'br'];
    var shape = { left: [[0, 0, 50, 100]], right: [[50, 0, 50, 100]], max: [[0, 0, 100, 100]],
                  tl: [[0, 0, 50, 50]], tr: [[50, 0, 50, 50]], bl: [[0, 50, 50, 50]], br: [[50, 50, 50, 50]] };
    layoutsEl.innerHTML = zones.map(function (z) {
      var rects = shape[z].map(function (q) { return '<i style="left:' + (q[0] + 6) + '%;top:' + (q[1] + 8) + '%;width:' + (q[2] - 12) + '%;height:' + (q[3] - 16) + '%"></i>'; }).join('');
      var tt = T.zones[z]; tt = lang() === 'en' ? tt[1] : tt[0];
      return '<button type="button" class="kd-lay" data-z="' + z + '" title="' + esc(tt) + '" aria-label="' + esc(tt) + '">' + rects + '</button>';
    }).join('');
    layoutsEl.querySelectorAll('.kd-lay').forEach(function (b) {
      b.addEventListener('click', function (e) { e.stopPropagation(); var id = layoutsFor; hideLayouts(); if (id) snapTo(id, b.getAttribute('data-z')); });
    });
    var sr = stageEl.getBoundingClientRect(), br = btn.getBoundingClientRect();
    layoutsEl.classList.add('show');
    var lw = layoutsEl.offsetWidth || 190;
    layoutsEl.style.left = clamp(br.left - sr.left + br.width / 2 - lw / 2, 6, sr.width - lw - 6) + 'px';
    layoutsEl.style.top = (br.bottom - sr.top + 4) + 'px';
  }
  function hideLayouts() { clearTimeout(layT); if (layoutsEl) layoutsEl.classList.remove('show'); layoutsFor = null; }

  // ── interacción: arrastrar, redimensionar, botones ──
  function wireWin(w) {
    var el = w.el, ttl = el.querySelector('.kd-ttl');
    el.addEventListener('pointerdown', function () { if (focused !== w.id) focus(w.id); }, true);
    el.querySelector('.kd-b-min').addEventListener('click', function (e) { e.stopPropagation(); minimize(w.id); });
    el.querySelector('.kd-b-pin').addEventListener('click', function (e) { e.stopPropagation(); hideLayouts(); pin(w.id); });
    var mb = el.querySelector('.kd-b-max');
    mb.addEventListener('click', function (e) {
      e.stopPropagation();
      if (coarse() && !isMobile()) {   // tablet: no hay hover → tocar ▢ abre el selector (incluye "Pantalla completa")
        if (layoutsEl.classList.contains('show') && layoutsFor === w.id) hideLayouts(); else showLayouts(w, mb);
        return;
      }
      hideLayouts(); maximize(w.id);
    });
    mb.addEventListener('mouseenter', function () { if (coarse()) return; clearTimeout(layT); layT = setTimeout(function () { showLayouts(w, mb); }, 350); });
    mb.addEventListener('mouseleave', function () { clearTimeout(layT); layT = setTimeout(function () { if (layoutsEl && !layoutsEl.matches(':hover')) hideLayouts(); }, 250); });
    el.querySelector('.kd-b-x').addEventListener('click', function (e) { e.stopPropagation(); close(w.id); });
    ttl.addEventListener('dblclick', function (e) { if (e.target.closest('.kd-b') || isMobile()) return; maximize(w.id); });

    // arrastre por la barra de título
    ttl.addEventListener('pointerdown', function (e) {
      if (e.button !== 0 || e.target.closest('.kd-b') || isMobile() || w.pinned) return;
      e.preventDefault();
      var sr = winsEl.getBoundingClientRect();
      var startX = e.clientX, startY = e.clientY, moved = false;
      var ox = w.x, oy = w.y;
      var before = { x: w.x, y: w.y, w: w.w, h: w.h, max: w.max, snap: w.snap };   // para revertir si el gesto se cancela
      // una ventana maximizada o pegada se "despega" al arrastrarla (como en Windows)
      var pinned = w.max || w.snap;
      var pid = e.pointerId;
      try { ttl.setPointerCapture(pid); } catch (err) {}
      function mv(ev) {
        var dx = ev.clientX - startX, dy = ev.clientY - startY;
        if (!moved && Math.abs(dx) + Math.abs(dy) < 4) return;
        if (!moved) { moved = true; el.classList.add('kd-drag'); }
        if (pinned) {
          pinned = false;
          var ds = drawSize();
          var pw = w.prev || { w: Math.round(ds.W * 0.64), h: Math.round(ds.H * 0.74) };
          // posición relativa del cursor DENTRO de la barra (0..1): la ventana se encoge bajo el cursor
          var fx = clamp((ev.clientX - sr.left - w.x) / Math.max(1, w.el.offsetWidth), 0, 1);
          w.max = false; w.snap = null; w.w = pw.w; w.h = pw.h;
          ox = Math.round(ev.clientX - sr.left - fx * pw.w); oy = Math.round(ev.clientY - sr.top - 18);
          startX = ev.clientX; startY = ev.clientY; dx = 0; dy = 0;
          el.classList.remove('kd-max');
        }
        w.x = ox + dx; w.y = oy + dy;
        place(w);
        showGhost(zoneAt(ev.clientX - sr.left, ev.clientY - sr.top));
      }
      function done() {
        ttl.removeEventListener('pointermove', mv); ttl.removeEventListener('pointerup', up); ttl.removeEventListener('pointercancel', cancel);
        try { ttl.releasePointerCapture(pid); } catch (err) {}
        el.classList.remove('kd-drag');
        showGhost(null);
      }
      function up(ev) {
        done();
        if (!moved) return;
        var z = zoneAt(ev.clientX - sr.left, ev.clientY - sr.top);
        w.manual = true;   // la movió a mano: el orden automático ya no la toca
        if (z) snapTo(w.id, z); else { w.snap = null; saveGeom(w); fireResize(w); }
      }
      function cancel() {   // el sistema tomó el gesto (scroll, palma, cambio de app): se revierte, no se "suelta"
        done();
        if (!moved) return;
        w.x = before.x; w.y = before.y; w.w = before.w; w.h = before.h; w.max = before.max; w.snap = before.snap;
        place(w);
      }
      ttl.addEventListener('pointermove', mv); ttl.addEventListener('pointerup', up); ttl.addEventListener('pointercancel', cancel);
    });

    // redimensión por bordes y esquinas
    el.querySelectorAll('.kd-rs').forEach(function (h) {
      h.addEventListener('pointerdown', function (e) {
        if (e.button !== 0 || isMobile() || w.max || w.pinned) return;
        e.preventDefault(); e.stopPropagation();
        var d = h.getAttribute('data-d'), sx = e.clientX, sy = e.clientY;
        var o = { x: w.x, y: w.y, w: w.w, h: w.h, snap: w.snap }, pid = e.pointerId;
        try { h.setPointerCapture(pid); } catch (err) {}
        function mv(ev) {
          var dx = ev.clientX - sx, dy = ev.clientY - sy;
          var nx = o.x, ny = o.y, nw = o.w, nh = o.h;
          if (d.indexOf('e') >= 0) nw = o.w + dx;
          if (d.indexOf('s') >= 0) nh = o.h + dy;
          if (d.indexOf('w') >= 0) { nw = o.w - dx; nx = o.x + dx; if (nw < MIN_W) { nx -= (MIN_W - nw); nw = MIN_W; } }
          if (d.indexOf('n') >= 0) {
            var dyc = Math.max(dy, -o.y);          // el borde superior no pasa del escritorio (y el inferior no se mueve)
            nh = o.h - dyc; ny = o.y + dyc;
            if (nh < MIN_H) { ny -= (MIN_H - nh); nh = MIN_H; }
          }
          w.x = nx; w.y = ny; w.w = Math.max(MIN_W, nw); w.h = Math.max(MIN_H, nh); w.snap = null;
          place(w);
        }
        function done() {
          h.removeEventListener('pointermove', mv); h.removeEventListener('pointerup', up); h.removeEventListener('pointercancel', cancel);
          try { h.releasePointerCapture(pid); } catch (err) {}
        }
        function up() { done(); w.manual = true; saveGeom(w); fireResize(w); }
        function cancel() { done(); w.x = o.x; w.y = o.y; w.w = o.w; w.h = o.h; w.snap = o.snap; place(w); }
        h.addEventListener('pointermove', mv); h.addEventListener('pointerup', up); h.addEventListener('pointercancel', cancel);
      });
    });
  }

  // Esc: primero cierra el menú ⊞ / el selector de acomodo; si no hay nada abierto,
  // sigue su camino (la Cabina se cierra con Esc). Este módulo carga antes que cockpit.js.
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape' || !active()) return;
    var open = (menuEl && menuEl.classList.contains('show')) || (layoutsEl && layoutsEl.classList.contains('show'));
    if (!open) return;
    toggleMenu(false); hideLayouts();
    e.stopImmediatePropagation(); e.preventDefault();
  }, true);

  // ── barra de tareas y menú ──
  var barSig = null;
  function renderBar() {
    if (!barEl) return;
    var tasks = barEl.querySelector('.kd-tasks');
    var mb = barEl.querySelector('#kd-menu-btn');
    mb.title = t('menuTip'); mb.setAttribute('aria-label', t('menuTip'));
    var sig = lang() + '|' + (isMobile() ? 'm' : 'd') + '|' + wins.map(function (w) { return w.id + ':' + titleFor(w) + ':' + (w.min ? 1 : 0) + ':' + (focused === w.id ? 1 : 0); }).join(';');
    if (sig === barSig) return;   // no reconstruir botones si nada cambió (los clics no se pierden)
    barSig = sig;
    if (!wins.length) { tasks.innerHTML = '<span class="kd-hint">' + esc(isMobile() ? t('hintMobile') : t('hint')) + '</span>'; return; }
    tasks.innerHTML = wins.map(function (w) {
      return '<button type="button" class="kd-task' + (focused === w.id && !w.min ? ' on' : '') + (w.min ? ' dim' : '') + '" data-id="' + w.id + '" title="' + esc(titleFor(w)) + '">' +
        '<span>' + esc(iconFor(w)) + '</span><span class="tx">' + esc(titleFor(w)) + '</span></button>';
    }).join('');
    tasks.querySelectorAll('.kd-task').forEach(function (b) {
      b.addEventListener('click', function () {
        var w = get(b.getAttribute('data-id')); if (!w) return;
        if (w.min || focused !== w.id) focus(w.id);
        else if (!isMobile()) minimize(w.id);
      });
    });
  }
  function toggleMenu(on) {
    if (!menuEl) return;
    if (on == null) on = !menuEl.classList.contains('show');
    if (on) {
      var items = isMobile() ? [['closeAll', closeAll], ['classic', toClassic]]
        : [[autoOn() ? 'auto' : 'autoOff', function () { setAuto(!autoOn()); }], ['arrange', function () { arrange(true); }], ['tile', tile], ['cascade', cascade], ['minAll', function () { wins.slice().forEach(function (w) { minimize(w.id); }); }], ['closeAll', closeAll], ['sep'], ['classic', toClassic]];
      menuEl.innerHTML = items.map(function (it) { return it[0] === 'sep' ? '<div class="sep"></div>' : '<button type="button" data-k="' + it[0] + '">' + esc(t(it[0])) + '</button>'; }).join('');
      menuEl.querySelectorAll('button').forEach(function (b) {
        var it = items.filter(function (x) { return x[0] === b.getAttribute('data-k'); })[0];
        b.addEventListener('click', function (e) { e.stopPropagation(); toggleMenu(false); if (it && it[1]) it[1](); });
      });
    }
    menuEl.classList.toggle('show', on);
    if (barEl) barEl.querySelector('#kd-menu-btn').classList.toggle('on', on);
  }
  function toClassic() { setEnabled(false); }

  function visibleWins() { return wins.filter(function (w) { return !w.min; }); }
  function tile() {
    if (isMobile()) return;
    var vs = visibleWins(); if (!vs.length) return;
    var n = vs.length;
    if (n === 1) { maximize(vs[0].id, true); return; }
    var layouts = { 2: ['left', 'right'], 3: ['left', 'tr', 'br'], 4: ['tl', 'tr', 'bl', 'br'] };
    if (layouts[n]) { vs.forEach(function (w, i) { snapTo(w.id, layouts[n][i]); }); return; }
    var d = drawSize(), cols = Math.ceil(Math.sqrt(n)), rows = Math.ceil(n / cols);
    var cw = Math.floor(d.W / cols), ch = Math.floor(d.H / rows);
    vs.forEach(function (w, i) {
      w.max = false; w.snap = 'grid';
      w.x = (i % cols) * cw; w.y = Math.floor(i / cols) * ch; w.w = Math.max(MIN_W, cw); w.h = Math.max(MIN_H, ch);
      place(w);
    });
    if (vs.some(function (w) { return hooks.adoptKinds.indexOf(w.kind) >= 0; })) fireResize();
  }
  function cascade() {
    if (isMobile()) return;
    var vs = visibleWins(), d = drawSize();
    vs.forEach(function (w, i) {
      w.max = false; w.snap = null;
      w.w = clamp(Math.round(d.W * 0.64), MIN_W, d.W); w.h = clamp(Math.round(d.H * 0.74), MIN_H, d.H);
      w.x = Math.min(30 * i, Math.max(0, d.W - w.w)); w.y = Math.min(30 * i, Math.max(0, d.H - w.h));
      place(w);
      zTop++; w.el.style.zIndex = zTop;
    });
    if (vs.length) focus(vs[vs.length - 1].id);
    if (vs.some(function (w) { return hooks.adoptKinds.indexOf(w.kind) >= 0; })) fireResize();
  }

  // ── la Cabina se cierra/abre: los paneles adoptados vuelven a su sitio y se re-adoptan ──
  function suspend() {
    toggleMenu(false); hideLayouts();
    wins.forEach(function (w) {
      if (hooks.adoptKinds.indexOf(w.kind) >= 0 || hooks.resumeKinds.indexOf(w.kind) >= 0) w.needsRender = true;
    });
  }
  function resume() {
    if (!active()) return;
    wasMobile = isMobile();
    applyMode();
    lastSz = deskSize();
    wins.forEach(function (w) {
      if (!w.needsRender) return;
      var done = false;
      // la Cabina puede devolver el MISMO panel a su ventana sin re-inicializarlo (terminal con sus gráficos, mapa con su zoom)
      try { if (hooks.resume) done = !!hooks.resume(w.kind, w.id, w.body); } catch (e) { done = false; }
      if (done) { w.needsRender = false; fireResize(w); }
      else { w.body.innerHTML = ''; render(w); }
    });
    relabel();
    if (autoOn()) arrange();
  }

  function setEnabled(on) {
    lsSet(LS_MODE, on ? 'on' : 'off');
    if (!on && active()) unmount();
    try { if (hooks.onModeChange) hooks.onModeChange(!!on); } catch (e) {}
  }

  function configure(h) {
    Object.keys(h || {}).forEach(function (k) { hooks[k] = h[k]; });
    hooks.adoptKinds = hooks.adoptKinds || [];
    hooks.resumeKinds = hooks.resumeKinds || [];
    hooks.multiKinds = hooks.multiKinds || [];
  }

  window.KhipuDesk = {
    configure: configure, enabled: enabled, setEnabled: setEnabled, active: active,
    mount: mount, unmount: unmount, wall: function () { return wallEl; },
    open: open, close: close, closeKind: closeKind, closeAll: closeAll, focus: focus, has: has, get: get, list: list,
    minimize: minimize, maximize: maximize, restore: restore, snap: snapTo, tile: tile, cascade: cascade,
    arrange: arrange, pin: pin, autoOn: autoOn, setAuto: setAuto,
    suspend: suspend, resume: resume, isMobile: isMobile, relabel: relabel,
    focused: function () { return focused; },
  };
})();
