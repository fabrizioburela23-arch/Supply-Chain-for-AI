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
   son chips para cambiar entre ellas.

   La Cabina es quien PINTA el contenido: registra `configure({render,title,
   onClose,beforeRender,onFocus,adoptKinds})`; este módulo solo gestiona las
   ventanas. Una sola puerta: BixbyCockpit.stage(kind,arg) → KhipuDesk.open().
   Geometría recordada por tipo en localStorage kh_desk_geom; modo ON/OFF en
   kh_desk_mode (OFF = Cabina clásica de una sola pantalla, por si algo falla).

   window.KhipuDesk = { configure, enabled, setEnabled, active, mount, unmount,
     wall, open, close, closeAll, focus, has, get, list, minimize, maximize,
     restore, tile, cascade, suspend, resume, isMobile, relabel }
   ============================================================================ */
(function () {
  'use strict';

  var MOBILE_MAX = 760;        // ≤ → hojas a pantalla completa (mismo corte que la Cabina)
  var BAR_H = 40;              // alto de la barra de tareas
  var MIN_W = 320, MIN_H = 220;
  var SNAP_PX = 14;            // distancia al borde del escritorio que activa el snap
  var LS_GEOM = 'kh_desk_geom', LS_MODE = 'kh_desk_mode';

  function lang() {
    var l = window.LANG;
    if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = null; } }
    return l === 'en' ? 'en' : 'es';
  }
  function L(es, en) { return lang() === 'en' ? en : es; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function ls(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

  // ── textos de la interfaz (regla bilingüe) ──
  var T = {
    min: ['Minimizar', 'Minimize'], max: ['Maximizar', 'Maximize'], restore: ['Restaurar', 'Restore'],
    close: ['Cerrar', 'Close'], snapTip: ['Acomodar en pantalla', 'Snap layouts'],
    tile: ['▦ Mosaico', '▦ Tile'], cascade: ['⧉ Cascada', '⧉ Cascade'],
    minAll: ['▁ Minimizar todo', '▁ Minimize all'], closeAll: ['✕ Cerrar todo', '✕ Close all'],
    classic: ['▭ Una sola pantalla (modo clásico)', '▭ Single screen (classic mode)'],
    menuTip: ['Ventanas', 'Windows'],
    hint: ['Todo lo que abras aparece aquí como ventana: muévela, cámbiale el tamaño o pégala a un borde.',
           'Everything you open shows up here as a window: move it, resize it or snap it to an edge.'],
    hintMobile: ['Lo que abras aparece aquí; cambia entre pantallas con estos botones.',
                 'What you open shows up here; switch between screens with these buttons.'],
    back: ['‹ Volver', '‹ Back'],
    zones: { left: ['Mitad izquierda', 'Left half'], right: ['Mitad derecha', 'Right half'],
             tl: ['Cuarto superior izquierdo', 'Top-left quarter'], tr: ['Cuarto superior derecho', 'Top-right quarter'],
             bl: ['Cuarto inferior izquierdo', 'Bottom-left quarter'], br: ['Cuarto inferior derecho', 'Bottom-right quarter'],
             max: ['Pantalla completa', 'Full screen'] },
  };
  function t(k) { var v = T[k]; return v ? (lang() === 'en' ? v[1] : v[0]) : k; }

  // ── estado ──
  var hooks = { render: null, title: null, onClose: null, beforeRender: null, onFocus: null, adoptKinds: [] };
  var stageEl = null, wallEl = null, winsEl = null, barEl = null, ghostEl = null, menuEl = null, layoutsEl = null;
  var wins = [];            // [{id, kind, arg, key, el, body, x,y,w,h, max, min, snap, prev, needsRender}]
  var zTop = 10, seq = 0, focused = null, resizeT = null;

  function enabled() { return ls(LS_MODE) !== 'off'; }
  function isMobile() { return (window.innerWidth || 1024) <= MOBILE_MAX; }
  function active() { return !!(stageEl && stageEl.classList.contains('kd-desk') && stageEl.contains(winsEl)); }

  // ── estilos ──
  function ensureStyles() {
    if (document.getElementById('kd-styles')) return;
    var css = '' +
'#bcp-stage.kd-desk{padding:0!important;overflow:hidden!important;position:relative}' +
'#bcp-stage.kd-desk>*{animation:none}' +
'#kd-wall{position:absolute;left:0;right:0;top:0;bottom:' + BAR_H + 'px;overflow-y:auto;padding:22px;scrollbar-width:thin}' +
'#kd-wins{position:absolute;left:0;right:0;top:0;bottom:' + BAR_H + 'px;pointer-events:none;overflow:hidden}' +
'.kd-win{position:absolute;pointer-events:auto;display:flex;flex-direction:column;min-width:' + MIN_W + 'px;min-height:' + MIN_H + 'px;' +
  'border:1px solid rgba(122,158,255,.22);border-radius:14px;background:rgba(7,11,20,.96);' +
  'box-shadow:0 18px 50px rgba(0,0,0,.55),0 0 0 1px rgba(0,0,0,.4);overflow:hidden;animation:kdIn .16s ease;' +
  'transition:box-shadow .15s,border-color .15s}' +
'@keyframes kdIn{from{opacity:0;transform:scale(.985)}to{opacity:1;transform:none}}' +
'@media(prefers-reduced-motion:reduce){.kd-win{animation:none}}' +
'.kd-win.kd-focus{border-color:rgba(0,224,255,.55);box-shadow:0 22px 60px rgba(0,0,0,.65),0 0 0 1px rgba(0,224,255,.18)}' +
'.kd-win.kd-min{display:none}' +
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
'#kd-bar{position:absolute;left:0;right:0;bottom:0;height:' + BAR_H + 'px;display:flex;align-items:center;gap:6px;padding:0 10px;' +
  'background:rgba(6,10,19,.92);border-top:1px solid rgba(122,158,255,.16);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);z-index:9100;overflow:hidden}' +
'#kd-bar .kd-tasks{flex:1;min-width:0;display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;align-items:center;height:100%}' +
'#kd-bar .kd-tasks::-webkit-scrollbar{display:none}' +
'.kd-task{flex:none;max-width:200px;height:28px;padding:0 11px;border-radius:9px;border:1px solid rgba(122,158,255,.18);background:rgba(11,18,34,.7);' +
  'color:#9BA6C4;font-size:12px;cursor:pointer;display:inline-flex;align-items:center;gap:6px;font-family:inherit;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;transition:all .13s}' +
'.kd-task:hover{color:#E8EDFB;border-color:rgba(0,224,255,.45)}' +
'.kd-task.on{color:#00E0FF;border-color:rgba(0,224,255,.55);background:rgba(0,224,255,.09)}' +
'.kd-task.dim{opacity:.55}' +
'.kd-task .tx{overflow:hidden;text-overflow:ellipsis}' +
'.kd-hint{flex:1;min-width:0;font-size:11.5px;color:#5E6884;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding-left:4px}' +
'#kd-menu-btn{flex:none;width:32px;height:28px;border-radius:9px;border:1px solid rgba(122,158,255,.22);background:rgba(11,18,34,.7);color:#9BA6C4;cursor:pointer;font-size:15px;font-family:inherit;display:inline-flex;align-items:center;justify-content:center}' +
'#kd-menu-btn:hover,#kd-menu-btn.on{color:#00E0FF;border-color:rgba(0,224,255,.5)}' +
'#kd-menu{position:absolute;left:10px;bottom:' + (BAR_H + 6) + 'px;display:none;flex-direction:column;gap:2px;padding:6px;min-width:230px;z-index:9200;' +
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
        if (layoutsEl.classList.contains('show') && !layoutsEl.contains(e.target)) hideLayouts();
      });
    }
    layoutsEl.addEventListener('mouseleave', function () { hideLayouts(); });
    // re-adaptar al cambiar el tamaño (giro del teléfono, ventana del navegador)
    window.removeEventListener('resize', onResize);
    window.addEventListener('resize', onResize);
    applyMode();
    renderBar();
    // ventanas existentes (vuelta del modo clásico)
    wins.forEach(function (w) { winsEl.appendChild(w.el); });
  }

  function unmount() {
    if (!stageEl) return;
    closeAll();
    window.removeEventListener('resize', onResize);
    stageEl.classList.remove('kd-desk', 'kd-mobile');
    stageEl.innerHTML = '';
    wallEl = winsEl = barEl = ghostEl = menuEl = layoutsEl = null;
  }

  function applyMode() {
    if (!stageEl) return;
    var m = isMobile();
    stageEl.classList.toggle('kd-mobile', m);
    if (!m) wins.forEach(function (w) { w.el.style.visibility = ''; if (!w.max) place(w); });
    else wins.forEach(function (w) { w.el.style.visibility = (focused && w.id !== focused) ? 'hidden' : ''; });
  }
  function onResize() {
    if (!active()) return;
    clearTimeout(resizeT);
    resizeT = setTimeout(function () { applyMode(); renderBar(); fireResize(); }, 120);
  }
  // los motores (mapa, globos, terminal) miden su contenedor al evento resize;
  // solo se dispara cuando cambia una ventana que aloja uno (adoptKinds), no por un X-Ray
  var fireT = null;
  function fireResize(w) {
    if (w && hooks.adoptKinds.indexOf(w.kind) < 0) return;
    clearTimeout(fireT);
    fireT = setTimeout(function () { try { window.dispatchEvent(new Event('resize')); } catch (e) {} }, 80);
  }

  function deskSize() {
    var r = winsEl ? winsEl.getBoundingClientRect() : { width: 1000, height: 600 };
    return { W: Math.max(300, Math.round(r.width)), H: Math.max(200, Math.round(r.height)) };
  }

  // ── geometría recordada por tipo ──
  function geomStore() { try { return JSON.parse(ls(LS_GEOM) || '{}') || {}; } catch (e) { return {}; } }
  function saveGeom(w) {
    if (isMobile()) return;
    var g = geomStore();
    g[w.kind] = { x: w.x, y: w.y, w: w.w, h: w.h, max: !!w.max, snap: w.snap || null };
    lsSet(LS_GEOM, JSON.stringify(g));
  }
  function defaultGeom(kind, n) {
    var d = deskSize();
    var saved = geomStore()[kind];
    var w, h, x, y;
    if (saved && saved.w >= MIN_W && saved.h >= MIN_H) {
      w = Math.min(saved.w, d.W); h = Math.min(saved.h, d.H);
      x = clamp(saved.x, 0, Math.max(0, d.W - 60)); y = clamp(saved.y, 0, Math.max(0, d.H - 40));
      return { x: x, y: y, w: w, h: h, max: !!saved.max, snap: saved.snap || null };
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
    // nunca se pierde una ventana: siempre quedan ≥ 80 px de barra de título a la vista
    w.w = clamp(w.w, MIN_W, Math.max(MIN_W, d.W)); w.h = clamp(w.h, MIN_H, Math.max(MIN_H, d.H));
    w.x = clamp(w.x, -(w.w - 80), Math.max(0, d.W - 80));
    w.y = clamp(w.y, 0, Math.max(0, d.H - 36));
    w.el.style.left = w.x + 'px'; w.el.style.top = w.y + 'px';
    w.el.style.width = w.w + 'px'; w.el.style.height = w.h + 'px';
    w.el.classList.toggle('kd-max', !!w.max);
    var mb = w.el.querySelector('.kd-b-max');
    if (mb) { mb.textContent = w.max ? '❐' : '▢'; mb.title = w.max ? t('restore') : t('max'); }
  }

  // ── ventanas ──
  function keyFor(kind, arg) {
    var multi = hooks.multiKinds && hooks.multiKinds.indexOf(kind) >= 0;
    if (!multi) return kind;
    var a = arg;
    if (a && typeof a === 'object') a = a.id || a.a || a.scenario || JSON.stringify(a);
    return kind + ':' + String(a == null ? '' : a).toLowerCase();
  }
  function get(id) { for (var i = 0; i < wins.length; i++) if (wins[i].id === id || wins[i].key === id) return wins[i]; return null; }
  function has(kind) { return wins.some(function (w) { return w.kind === kind; }); }
  function list() { return wins.map(function (w) { return { id: w.id, kind: w.kind, key: w.key, min: !!w.min, max: !!w.max, focused: focused === w.id }; }); }

  function titleFor(w) {
    var s = '';
    try { s = hooks.title ? hooks.title(w.kind, w.arg) : ''; } catch (e) { s = ''; }
    return s || w.kind;
  }
  function iconFor(w) {
    try { return (hooks.icon && hooks.icon(w.kind)) || '▫'; } catch (e) { return '▫'; }
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
          max: !!(g.max || opts.max), min: false, snap: g.snap, prev: null, needsRender: false };
    var el = document.createElement('div');
    el.className = 'kd-win'; el.setAttribute('data-id', w.id); el.setAttribute('data-kind', kind);
    el.innerHTML =
      '<div class="kd-ttl"><span class="kd-ico"></span><span class="kd-name"></span>' +
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
    place(w);
    render(w);
    focus(w.id);
    renderBar();
    return w.id;
  }

  function relabelWin(w) {
    w.el.querySelector('.kd-ico').textContent = iconFor(w);
    w.el.querySelector('.kd-name').textContent = titleFor(w);
    var b = w.el.querySelector('.kd-b-min'); b.title = t('min'); b.setAttribute('aria-label', t('min'));
    b = w.el.querySelector('.kd-b-max'); b.title = w.max ? t('restore') : t('max'); b.setAttribute('aria-label', b.title);
    b = w.el.querySelector('.kd-b-x'); b.title = t('close'); b.setAttribute('aria-label', t('close'));
    b.textContent = isMobile() ? t('back') : '✕';
  }
  function relabel() {
    wins.forEach(relabelWin);
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

  function focus(id) {
    var w = get(id); if (!w) return;
    if (w.min) { w.min = false; w.el.classList.remove('kd-min'); }
    if (focused !== w.id) {
      if (zTop > 4000) {   // renormalizar (los z de fantasma/barra/menús empiezan en 9000)
        wins.slice().sort(function (a, b) { return (+a.el.style.zIndex || 0) - (+b.el.style.zIndex || 0); })
          .forEach(function (o, i) { o.el.style.zIndex = 10 + i; });
        zTop = 10 + wins.length;
      }
      zTop++;
      w.el.style.zIndex = zTop;
      wins.forEach(function (o) { o.el.classList.toggle('kd-focus', o === w); });
      focused = w.id;
      if (isMobile()) wins.forEach(function (o) { if (o !== w) { o.el.style.visibility = 'hidden'; } else o.el.style.visibility = ''; });
    }
    try { if (hooks.onFocus) hooks.onFocus(w.kind, w.id); } catch (e) {}
    renderBar();
  }
  function topVisible() {
    var best = null;
    wins.forEach(function (w) { if (!w.min && (!best || (+w.el.style.zIndex || 0) > (+best.el.style.zIndex || 0))) best = w; });
    return best;
  }

  function close(id) {
    var w = get(id); if (!w) return false;
    wins = wins.filter(function (o) { return o !== w; });        // primero sale de la lista (has() ya dice que no)
    try { if (hooks.onClose) hooks.onClose(w.kind, w.id); } catch (e) {}   // la Cabina devuelve lo adoptado
    if (w.el && w.el.parentNode) w.el.parentNode.removeChild(w.el);
    if (focused === w.id) { focused = null; var nx = topVisible(); if (nx) focus(nx.id); else { try { if (hooks.onFocus) hooks.onFocus(null, null); } catch (e) {} } }
    if (isMobile()) wins.forEach(function (o) { o.el.style.visibility = (focused && o.id !== focused) ? 'hidden' : ''; });
    renderBar();
    return true;
  }
  function closeKind(kind) { wins.slice().forEach(function (w) { if (w.kind === kind) close(w.id); }); }
  function closeAll() { wins.slice().forEach(function (w) { close(w.id); }); }

  function minimize(id) {
    var w = get(id); if (!w) return;
    w.min = true; w.el.classList.add('kd-min');
    if (focused === w.id) { focused = null; var nx = topVisible(); if (nx) focus(nx.id); else { try { if (hooks.onFocus) hooks.onFocus(null, null); } catch (e) {} } }
    renderBar();
  }
  function maximize(id, on) {
    var w = get(id); if (!w) return;
    if (on == null) on = !w.max;
    if (on && !w.max) { w.prev = { x: w.x, y: w.y, w: w.w, h: w.h }; }
    if (!on && w.prev) { w.x = w.prev.x; w.y = w.prev.y; w.w = w.prev.w; w.h = w.prev.h; }
    w.max = on; w.snap = null;
    place(w); saveGeom(w); fireResize(w);
  }
  function restore(id) { var w = get(id); if (!w) return; if (w.max) maximize(id, false); focus(id); }

  // zonas de snap (estilo Windows 11)
  function zoneRect(zone) {
    var d = deskSize(), hw = Math.round(d.W / 2), hh = Math.round(d.H / 2);
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
    var d = deskSize();
    var l = px <= SNAP_PX, r = px >= d.W - SNAP_PX, tp = py <= SNAP_PX, b = py >= d.H - SNAP_PX;
    if (tp && !l && !r) return 'max';
    if (l && tp) return 'tl'; if (r && tp) return 'tr'; if (l && b) return 'bl'; if (r && b) return 'br';
    if (l) return 'left'; if (r) return 'right';
    return null;
  }
  function showGhost(zone) {
    if (!zone) { ghostEl.style.display = 'none'; return; }
    var r = zoneRect(zone);
    ghostEl.style.display = 'block';
    ghostEl.style.left = r.x + 'px'; ghostEl.style.top = r.y + 'px'; ghostEl.style.width = r.w + 'px'; ghostEl.style.height = r.h + 'px';
  }

  // selector de acomodo (aparece al pasar por ▢, como en Windows 11)
  var layoutsFor = null, layT = null;
  function showLayouts(w, btn) {
    if (isMobile()) return;
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
      b.addEventListener('click', function (e) { e.stopPropagation(); snapTo(layoutsFor, b.getAttribute('data-z')); hideLayouts(); });
    });
    var sr = stageEl.getBoundingClientRect(), br = btn.getBoundingClientRect();
    layoutsEl.classList.add('show');
    var lw = layoutsEl.offsetWidth || 190;
    layoutsEl.style.left = clamp(br.left - sr.left + br.width / 2 - lw / 2, 6, sr.width - lw - 6) + 'px';
    layoutsEl.style.top = (br.bottom - sr.top + 4) + 'px';
  }
  function hideLayouts() { clearTimeout(layT); layoutsEl.classList.remove('show'); layoutsFor = null; }

  // ── interacción: arrastrar, redimensionar, botones ──
  function wireWin(w) {
    var el = w.el, ttl = el.querySelector('.kd-ttl');
    el.addEventListener('pointerdown', function () { if (focused !== w.id) focus(w.id); }, true);
    el.querySelector('.kd-b-min').addEventListener('click', function (e) { e.stopPropagation(); minimize(w.id); });
    var mb = el.querySelector('.kd-b-max');
    mb.addEventListener('click', function (e) { e.stopPropagation(); hideLayouts(); maximize(w.id); });
    mb.addEventListener('mouseenter', function () { clearTimeout(layT); layT = setTimeout(function () { showLayouts(w, mb); }, 350); });
    mb.addEventListener('mouseleave', function () { clearTimeout(layT); layT = setTimeout(function () { if (!layoutsEl.matches(':hover')) hideLayouts(); }, 250); });
    el.querySelector('.kd-b-x').addEventListener('click', function (e) { e.stopPropagation(); close(w.id); });
    ttl.addEventListener('dblclick', function (e) { if (e.target.closest('.kd-b') || isMobile()) return; maximize(w.id); });

    // arrastre por la barra de título
    ttl.addEventListener('pointerdown', function (e) {
      if (e.button !== 0 || e.target.closest('.kd-b') || isMobile()) return;
      e.preventDefault();
      var sr = winsEl.getBoundingClientRect();
      var startX = e.clientX, startY = e.clientY, moved = false;
      var ox = w.x, oy = w.y;
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
          var pw = w.prev || { w: Math.round(deskSize().W * 0.64), h: Math.round(deskSize().H * 0.74) };
          var fx = (ev.clientX - sr.left) / Math.max(1, w.el.offsetWidth);   // posición relativa del cursor en la barra
          w.max = false; w.snap = null; w.w = pw.w; w.h = pw.h;
          ox = Math.round(ev.clientX - sr.left - fx * pw.w); oy = Math.round(ev.clientY - sr.top - 18);
          startX = ev.clientX; startY = ev.clientY; dx = 0; dy = 0;
          el.classList.remove('kd-max');
        }
        w.x = ox + dx; w.y = oy + dy;
        place(w);
        showGhost(zoneAt(ev.clientX - sr.left, ev.clientY - sr.top));
      }
      function up(ev) {
        ttl.removeEventListener('pointermove', mv); ttl.removeEventListener('pointerup', up); ttl.removeEventListener('pointercancel', up);
        try { ttl.releasePointerCapture(pid); } catch (err) {}
        el.classList.remove('kd-drag');
        if (!moved) return;
        var z = zoneAt(ev.clientX - sr.left, ev.clientY - sr.top);
        showGhost(null);
        if (z) snapTo(w.id, z); else { w.snap = null; saveGeom(w); fireResize(w); }
      }
      ttl.addEventListener('pointermove', mv); ttl.addEventListener('pointerup', up); ttl.addEventListener('pointercancel', up);
    });

    // redimensión por bordes y esquinas
    el.querySelectorAll('.kd-rs').forEach(function (h) {
      h.addEventListener('pointerdown', function (e) {
        if (e.button !== 0 || isMobile() || w.max) return;
        e.preventDefault(); e.stopPropagation();
        var d = h.getAttribute('data-d'), sx = e.clientX, sy = e.clientY;
        var o = { x: w.x, y: w.y, w: w.w, h: w.h }, pid = e.pointerId;
        try { h.setPointerCapture(pid); } catch (err) {}
        function mv(ev) {
          var dx = ev.clientX - sx, dy = ev.clientY - sy;
          var nx = o.x, ny = o.y, nw = o.w, nh = o.h;
          if (d.indexOf('e') >= 0) nw = o.w + dx;
          if (d.indexOf('s') >= 0) nh = o.h + dy;
          if (d.indexOf('w') >= 0) { nw = o.w - dx; nx = o.x + dx; if (nw < MIN_W) { nx -= (MIN_W - nw); nw = MIN_W; } }
          if (d.indexOf('n') >= 0) { nh = o.h - dy; ny = o.y + dy; if (nh < MIN_H) { ny -= (MIN_H - nh); nh = MIN_H; } }
          w.x = nx; w.y = Math.max(0, ny); w.w = Math.max(MIN_W, nw); w.h = Math.max(MIN_H, nh); w.snap = null;
          place(w);
        }
        function up() {
          h.removeEventListener('pointermove', mv); h.removeEventListener('pointerup', up); h.removeEventListener('pointercancel', up);
          try { h.releasePointerCapture(pid); } catch (err) {}
          saveGeom(w); fireResize(w);
        }
        h.addEventListener('pointermove', mv); h.addEventListener('pointerup', up); h.addEventListener('pointercancel', up);
      });
    });
  }

  // ── barra de tareas y menú ──
  function renderBar() {
    if (!barEl) return;
    var tasks = barEl.querySelector('.kd-tasks');
    var mb = barEl.querySelector('#kd-menu-btn');
    mb.title = t('menuTip'); mb.setAttribute('aria-label', t('menuTip'));
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
        : [['tile', tile], ['cascade', cascade], ['minAll', function () { wins.slice().forEach(function (w) { minimize(w.id); }); }], ['closeAll', closeAll], ['sep'], ['classic', toClassic]];
      menuEl.innerHTML = items.map(function (it) { return it[0] === 'sep' ? '<div class="sep"></div>' : '<button type="button" data-k="' + it[0] + '">' + esc(t(it[0])) + '</button>'; }).join('');
      menuEl.querySelectorAll('button').forEach(function (b) {
        var it = items.filter(function (x) { return x[0] === b.getAttribute('data-k'); })[0];
        b.addEventListener('click', function (e) { e.stopPropagation(); toggleMenu(false); if (it && it[1]) it[1](); });
      });
    }
    menuEl.classList.toggle('show', on);
    barEl.querySelector('#kd-menu-btn').classList.toggle('on', on);
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
    var d = deskSize(), cols = Math.ceil(Math.sqrt(n)), rows = Math.ceil(n / cols);
    var cw = Math.floor(d.W / cols), ch = Math.floor(d.H / rows);
    vs.forEach(function (w, i) {
      w.max = false; w.snap = 'grid';
      w.x = (i % cols) * cw; w.y = Math.floor(i / cols) * ch; w.w = Math.max(MIN_W, cw); w.h = Math.max(MIN_H, ch);
      place(w);
    });
    fireResize();
  }
  function cascade() {
    if (isMobile()) return;
    var vs = visibleWins(), d = deskSize();
    vs.forEach(function (w, i) {
      w.max = false; w.snap = null;
      w.w = clamp(Math.round(d.W * 0.64), MIN_W, d.W); w.h = clamp(Math.round(d.H * 0.74), MIN_H, d.H);
      w.x = Math.min(30 * i, Math.max(0, d.W - w.w)); w.y = Math.min(30 * i, Math.max(0, d.H - w.h));
      place(w);
      zTop++; w.el.style.zIndex = zTop;
    });
    if (vs.length) focus(vs[vs.length - 1].id);
    fireResize();
  }

  // ── la Cabina se cierra/abre: los paneles adoptados vuelven a su sitio y se re-adoptan ──
  function suspend() {
    wins.forEach(function (w) { if (hooks.adoptKinds.indexOf(w.kind) >= 0) w.needsRender = true; });
  }
  function resume() {
    if (!active()) return;
    applyMode();
    wins.forEach(function (w) { if (w.needsRender) { w.body.innerHTML = ''; render(w); } });
    relabel();
  }

  function setEnabled(on) {
    lsSet(LS_MODE, on ? 'on' : 'off');
    if (!on && active()) unmount();
    try { if (hooks.onModeChange) hooks.onModeChange(!!on); } catch (e) {}
  }

  function configure(h) {
    Object.keys(h || {}).forEach(function (k) { hooks[k] = h[k]; });
    hooks.adoptKinds = hooks.adoptKinds || [];
  }

  window.KhipuDesk = {
    configure: configure, enabled: enabled, setEnabled: setEnabled, active: active,
    mount: mount, unmount: unmount, wall: function () { return wallEl; },
    open: open, close: close, closeKind: closeKind, closeAll: closeAll, focus: focus, has: has, get: get, list: list,
    minimize: minimize, maximize: maximize, restore: restore, snap: snapTo, tile: tile, cascade: cascade,
    suspend: suspend, resume: resume, isMobile: isMobile, relabel: relabel,
    focused: function () { return focused; },
  };
})();
