/* ============================================================================
   engine/layers.js — SISTEMA DE CAPAS DEL MAPA (petición día 1 de Fabrizio)
   El mapa deja de ser "todo o nada": enciendes/apagas información como capas.
   Cada capa = un grupo de elementos SVG que ya existen (conexiones, etiquetas,
   anillos de riesgo, marcas, países). Alternar = una regla CSS (instantáneo,
   sin re-render). Piel NEXUS. Botón "◱ Capas" arriba a la izquierda del mapa.
   La preferencia se recuerda en localStorage.
   ============================================================================ */
(function () {
  'use strict';

  // capa: {id, label, css (selector→display cuando OFF), on por defecto}
  var LAYERS = [
    { id: 'links',   label: 'Conexiones',        sel: '#graph line',            def: true },
    { id: 'labels',  label: 'Nombres de empresa', sel: '#graph .node-label',    def: true },
    { id: 'risk',    label: 'Anillos de riesgo',  sel: '#graph .risk-ring',     def: true },
    { id: 'marks',   label: 'Marcas ⚠ / IPO',     sel: '#graph .risk-mark, #graph .preipo-mark', def: true },
    { id: 'regions', label: 'Etiquetas de país',  sel: '#graph .region-label',  def: true },
  ];

  var state = {};
  try { state = JSON.parse(localStorage.getItem('khipu_layers') || '{}'); } catch (e) { state = {}; }
  function isOn(id) { var v = state[id]; return v == null ? LAYERS.find(function (l) { return l.id === id; }).def : !!v; }

  function ensureStyles() {
    if (document.getElementById('layers-styles')) return;
    var css = ''
      + '#lay-btn{position:absolute;left:12px;top:12px;z-index:20;display:flex;align-items:center;gap:6px;'
      + 'padding:7px 12px;border-radius:9px;cursor:pointer;font-family:Inter,system-ui,sans-serif;font-size:12px;font-weight:600;'
      + 'background:rgba(15,21,34,.85);border:1px solid rgba(122,158,255,.3);color:#c8d0e0;backdrop-filter:blur(6px)}'
      + '#lay-btn:hover{border-color:#00E0FF;color:#00E0FF}'
      + '#lay-btn.on{border-color:#00E0FF;color:#00E0FF}'
      + '#lay-panel{position:absolute;left:12px;top:52px;z-index:21;width:224px;display:none;flex-direction:column;gap:3px;'
      + 'padding:12px 13px;border-radius:12px;background:radial-gradient(320px 200px at 60% -10%,#0d1424,#06090F);'
      + 'border:1px solid rgba(122,158,255,.2);box-shadow:0 16px 44px rgba(0,0,0,.5);color:#E8EDFB;font-family:Inter,system-ui,sans-serif}'
      + '#lay-panel.show{display:flex}'
      + '#lay-panel h4{margin:0 0 8px;font-size:10.5px;letter-spacing:.15em;text-transform:uppercase;color:#7C87A3;font-weight:600;display:flex;justify-content:space-between;align-items:center}'
      + '#lay-panel .lx{cursor:pointer;color:#7C87A3;font-size:14px;line-height:1}'
      + '.lay-row{display:flex;align-items:center;gap:9px;padding:5px 6px;border-radius:7px;cursor:pointer;font-size:12px;color:#9BA6C4;transition:background .1s}'
      + '.lay-row:hover{background:rgba(122,158,255,.06)}'
      + '.lay-row.on{color:#E8EDFB}'
      + '.lay-sw{width:26px;height:15px;border-radius:9px;border:1px solid rgba(122,158,255,.25);position:relative;flex:none;background:rgba(21,28,45,.9);transition:background .15s,border-color .15s}'
      + '.lay-row.on .lay-sw{background:rgba(0,224,255,.28);border-color:#00E0FF}'
      + '.lay-sw::after{content:"";position:absolute;top:1px;left:2px;width:11px;height:11px;border-radius:50%;background:#7C87A3;transition:left .15s,background .15s}'
      + '.lay-row.on .lay-sw::after{left:auto;right:2px;background:#00E0FF}'
      + '#lay-note{font-size:10px;color:#5c657f;margin-top:7px;line-height:1.4}';
    var st = document.createElement('style'); st.id = 'layers-styles'; st.textContent = css;
    document.head.appendChild(st);
  }

  // aplica el estado de una capa vía una hoja de estilo dedicada (rápido)
  function apply() {
    var sheet = document.getElementById('layers-rules');
    if (!sheet) { sheet = document.createElement('style'); sheet.id = 'layers-rules'; document.head.appendChild(sheet); }
    var rules = LAYERS.filter(function (l) { return !isOn(l.id); })
      .map(function (l) { return l.sel + '{display:none !important}'; }).join('\n');
    sheet.textContent = rules;
    document.querySelectorAll('.lay-row').forEach(function (r) { r.classList.toggle('on', isOn(r.dataset.id)); });
  }

  function toggleLayer(id) {
    state[id] = !isOn(id);
    try { localStorage.setItem('khipu_layers', JSON.stringify(state)); } catch (e) {}
    apply();
  }

  function togglePanel() {
    var btn = document.getElementById('lay-btn'), panel = document.getElementById('lay-panel');
    var open = !panel.classList.contains('show');
    panel.classList.toggle('show', open);
    btn.classList.toggle('on', open);
  }

  function mount() {
    var wrap = document.querySelector('.graph-wrap');
    if (!wrap || document.getElementById('lay-btn')) return;
    ensureStyles();
    var btn = document.createElement('div');
    btn.id = 'lay-btn'; btn.innerHTML = '<span>◱</span> Capas';
    btn.title = 'Capas del mapa — enciende y apaga información';
    btn.onclick = togglePanel;
    var panel = document.createElement('div');
    panel.id = 'lay-panel';
    panel.innerHTML = '<h4>Capas del mapa <span class="lx">✕</span></h4>' +
      LAYERS.map(function (l) {
        return '<div class="lay-row" data-id="' + l.id + '"><span class="lay-sw"></span>' + l.label + '</div>';
      }).join('') +
      '<div id="lay-note">El color de los nodos se controla en la leyenda (sector ⇄ detalle).</div>';
    wrap.appendChild(btn); wrap.appendChild(panel);
    panel.querySelector('.lx').onclick = togglePanel;
    panel.querySelectorAll('.lay-row').forEach(function (r) {
      r.onclick = function () { toggleLayer(r.dataset.id); };
    });
    apply();
  }

  window._layersApply = apply;   // re-aplicar tras un re-render del grafo
  if (document.querySelector('.graph-wrap')) mount();
  else document.addEventListener('DOMContentLoaded', mount);
  setTimeout(mount, 1500);
})();
