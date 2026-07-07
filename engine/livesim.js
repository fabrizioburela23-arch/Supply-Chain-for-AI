/* ============================================================================
   engine/livesim.js — SIMULACIÓN EN VIVO (deslizador → el mapa reacciona)
   El payoff del motor de estados (engine/statematrix.js): eliges una empresa
   (o un escenario), arrastras la severidad, y los 407 nodos cambian de color
   y tamaño en TIEMPO REAL (~7ms por simulación → 60 fps, sin servidor).
   Piel NEXUS. Botón "◉ En vivo" en el mapa.
   ============================================================================ */
(function () {
  'use strict';

  // Escenarios: cada uno define el/los nodo(s) FUENTE del shock.
  var SCENARIOS = [
    { id: 'taiwan',  label: 'Conflicto en Taiwán',    shock: ['TSMC'] },
    { id: 'hbm',     label: 'Escasez de memoria HBM',  shock: ['SKHynix', 'Micron', 'Samsung'] },
    { id: 'euv',     label: 'Sanción a equipos EUV',   shock: ['ASML'] },
    { id: 'cloud',   label: 'Caída de un hyperscaler', shock: ['Amazon'] },
    { id: 'chipban', label: 'Veto total de chips a China', shock: ['Nvidia', 'AMD'] },
  ];

  var active = false, shockIds = ['TSMC'], severity = 100, factors = [], raf = 0;

  function ensureStyles() {
    if (document.getElementById('livesim-styles')) return;
    var css = ''
      + '#ls-btn{position:absolute;left:12px;bottom:52px;z-index:20;display:flex;align-items:center;gap:6px;'
      + 'padding:7px 13px;border-radius:9px;cursor:pointer;font-family:Inter,system-ui,sans-serif;font-size:12px;font-weight:600;'
      + 'background:rgba(15,21,34,.85);border:1px solid rgba(0,224,255,.35);color:#00E0FF;backdrop-filter:blur(6px)}'
      + '#ls-btn:hover{border-color:#00E0FF;box-shadow:0 0 12px rgba(0,224,255,.3)}'
      + '#ls-btn.on{background:#00E0FF;color:#03141C}'
      + '#ls-panel{position:absolute;left:12px;bottom:96px;z-index:21;width:290px;display:none;flex-direction:column;gap:11px;'
      + 'padding:15px 16px;border-radius:13px;background:radial-gradient(400px 240px at 60% -10%,#0d1424,#06090F);'
      + 'border:1px solid rgba(122,158,255,.2);box-shadow:0 18px 50px rgba(0,0,0,.5);color:#E8EDFB;font-family:Inter,system-ui,sans-serif}'
      + '#ls-panel.show{display:flex}'
      + '#ls-panel h4{margin:0;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#7C87A3;font-weight:600;display:flex;justify-content:space-between;align-items:center}'
      + '#ls-panel .lsx{cursor:pointer;color:#7C87A3;font-size:15px;line-height:1}'
      + '#ls-scn{display:flex;flex-wrap:wrap;gap:5px}'
      + '.ls-chip{font-size:11px;padding:4px 9px;border-radius:20px;cursor:pointer;border:1px solid rgba(122,158,255,.2);'
      + 'background:rgba(21,28,45,.6);color:#c8d0e0;transition:all .12s}'
      + '.ls-chip:hover{border-color:rgba(0,224,255,.5)}.ls-chip.on{background:rgba(0,224,255,.15);border-color:#00E0FF;color:#00E0FF}'
      + '#ls-panel .lsrow{font-size:11px;color:#9BA6C4;display:flex;justify-content:space-between;align-items:center;font-family:"JetBrains Mono",monospace}'
      + '#ls-sev{width:100%;accent-color:#00E0FF;cursor:pointer}'
      + '#ls-read{font-size:11.5px;line-height:1.5;color:#E8EDFB}'
      + '#ls-read b{color:#FF4D6A}'
      + '#ls-top{display:flex;flex-direction:column;gap:3px;max-height:130px;overflow-y:auto}'
      + '.ls-victim{display:flex;align-items:center;gap:7px;font-size:11px;cursor:pointer}'
      + '.ls-victim:hover span:nth-child(2){color:#00E0FF}'
      + '.ls-victim .b{flex:1;height:4px;border-radius:3px;background:rgba(255,77,106,.15);overflow:hidden}'
      + '.ls-victim .b i{display:block;height:100%;background:#FF4D6A}'
      + '.ls-victim .p{font-family:"JetBrains Mono",monospace;font-size:9.5px;color:#FF4D6A;width:34px;text-align:right}';
    var st = document.createElement('style'); st.id = 'livesim-styles'; st.textContent = css;
    document.head.appendChild(st);
  }

  function nm(id) { var n = window.NODE_BY_ID && window.NODE_BY_ID[id]; return n ? n.label : id; }

  function run() {
    if (!window.KhipuState) return;
    var shocks = {};
    shockIds.forEach(function (id) { shocks[id] = { salud: 1 - severity / 100 }; });
    var r = window.KhipuState.simulate(shocks, factors, 8, 0.6);
    if (window._liveRecolorByImpact) window._liveRecolorByImpact(r.impact);
    // readout
    var arr = [];
    r.impact.forEach(function (v, id) { if (shockIds.indexOf(id) < 0) arr.push({ id: id, v: v }); });
    arr.sort(function (a, b) { return b.v - a.v; });
    var read = document.getElementById('ls-read');
    if (read) read.innerHTML = 'Fuente: <b style="color:#00E0FF">' + shockIds.map(nm).join(', ') +
      '</b> al ' + severity + '% · <b>' + arr.length + '</b> empresas afectadas.';
    var top = document.getElementById('ls-top');
    if (top) top.innerHTML = arr.slice(0, 8).map(function (x) {
      return '<div class="ls-victim" onclick="window.jumpTo&&window.jumpTo(\'' + x.id + '\')">' +
        '<span style="width:6px;height:6px;border-radius:50%;background:#FF4D6A;flex:none"></span>' +
        '<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + nm(x.id) + '</span>' +
        '<span class="b"><i style="width:' + Math.round(x.v) + '%"></i></span>' +
        '<span class="p">' + Math.round(x.v) + '%</span></div>';
    }).join('');
  }

  // rAF cuando la pestaña pinta; setTimeout de respaldo cuando está oculta
  // (rAF se congela en pestañas de fondo — mismo patrón que engine/voice.js).
  function schedule() {
    if (raf) { cancelAnimationFrame(raf); clearTimeout(raf); }
    raf = (typeof document !== 'undefined' && document.hidden)
      ? setTimeout(run, 16) : requestAnimationFrame(run);
  }

  function setScenario(scn) {
    shockIds = scn.shock.filter(function (id) { return window.NODE_BY_ID && window.NODE_BY_ID[id]; });
    if (!shockIds.length) shockIds = ['TSMC'];
    document.querySelectorAll('#ls-scn .ls-chip').forEach(function (c) { c.classList.toggle('on', c.dataset.id === scn.id); });
    schedule();
  }

  function toggle() {
    active = !active;
    var btn = document.getElementById('ls-btn'), panel = document.getElementById('ls-panel');
    btn.classList.toggle('on', active);
    panel.classList.toggle('show', active);
    btn.innerHTML = active ? '<span>◉</span> En vivo · ON' : '<span>◉</span> En vivo';
    if (active) {
      window.KhipuState && window.KhipuState.build();
      // si hay un nodo seleccionado, úsalo como fuente
      var sel = window._liveSelectedNode && window._liveSelectedNode();
      if (sel) { shockIds = [sel]; document.querySelectorAll('#ls-scn .ls-chip').forEach(function (c) { c.classList.remove('on'); }); }
      schedule();
    } else {
      if (window._liveResetColors) window._liveResetColors();
    }
  }

  function mount() {
    var wrap = document.querySelector('.graph-wrap');
    if (!wrap || document.getElementById('ls-btn')) return;
    ensureStyles();
    var btn = document.createElement('div');
    btn.id = 'ls-btn'; btn.innerHTML = '<span>◉</span> En vivo';
    btn.title = 'Simulación en vivo — arrastra la severidad y ve reaccionar la red';
    btn.onclick = toggle;
    var panel = document.createElement('div');
    panel.id = 'ls-panel';
    panel.innerHTML = ''
      + '<h4>Simulación en vivo <span class="lsx" onclick="window._lsToggle()">✕</span></h4>'
      + '<div id="ls-scn">' + SCENARIOS.map(function (s) {
          return '<span class="ls-chip" data-id="' + s.id + '">' + s.label + '</span>';
        }).join('') + '</div>'
      + '<div class="lsrow"><span>Severidad</span><span id="ls-sevv">100%</span></div>'
      + '<input type="range" id="ls-sev" min="0" max="100" value="100">'
      + '<div id="ls-read">Elige un escenario o selecciona una empresa en el mapa.</div>'
      + '<div id="ls-top"></div>';
    wrap.appendChild(btn); wrap.appendChild(panel);
    panel.querySelectorAll('#ls-scn .ls-chip').forEach(function (c) {
      c.onclick = function () { var scn = SCENARIOS.find(function (s) { return s.id === c.dataset.id; }); if (scn) setScenario(scn); };
    });
    var sev = panel.querySelector('#ls-sev');
    sev.oninput = function () { severity = +sev.value; document.getElementById('ls-sevv').textContent = severity + '%'; schedule(); };
  }

  window._lsToggle = toggle;
  // montar cuando el mapa exista
  if (document.querySelector('.graph-wrap')) mount();
  else document.addEventListener('DOMContentLoaded', mount);
  setTimeout(mount, 1500);  // red de seguridad si el DOM del mapa llega tarde
})();
