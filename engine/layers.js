/* ============================================================================
   engine/layers.js — SISTEMA DE CAPAS DEL MAPA (petición día 1 de Fabrizio)
   El mapa deja de ser "todo o nada": enciendes/apagas información como capas.
   Cada capa = un grupo de elementos SVG que ya existen (conexiones, etiquetas,
   anillos de riesgo, marcas, países). Alternar = una regla CSS (instantáneo,
   sin re-render). Botón "◱ Capas" arriba a la izquierda del mapa.
   La preferencia se recuerda en localStorage.
   KHIPUS OS (2026-10-11): botón y panel llevan .kos-themed → tokens --os-* de
   engine/cockpit.js (claro = body sin .dark, oscuro = body.dark); el valor tras
   la coma de cada var() es el respaldo (la piel NEXUS vieja). Textos ES/EN y
   re-etiquetado al cambiar de idioma (regla bilingüe).
   ============================================================================ */
(function () {
  'use strict';

  // bilingüe (regla del proyecto): idioma activo = window.LANG (getter de app.html) → eco_lang
  function L(es, en) {
    var l = window.LANG;
    if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = null; } }
    return l === 'en' ? en : es;
  }

  // capa: {id, label ES/EN, css (selector→display cuando OFF), on por defecto}
  var LAYERS = [
    { id: 'links',   label: 'Conexiones',         en: 'Links',          sel: '#graph line',            def: true },
    { id: 'labels',  label: 'Nombres de empresa', en: 'Company names',  sel: '#graph .node-label',    def: true },
    { id: 'risk',    label: 'Anillos de riesgo',  en: 'Risk rings',     sel: '#graph .risk-ring',     def: true },
    { id: 'marks',   label: 'Marcas ⚠ / IPO',     en: '⚠ / IPO marks',  sel: '#graph .risk-mark, #graph .preipo-mark', def: true },
    { id: 'regions', label: 'Etiquetas de país',  en: 'Country labels', sel: '#graph .region-label',  def: true },
  ];
  function lbl(l) { return L(l.label, l.en); }

  var state = {};
  try { state = JSON.parse(localStorage.getItem('khipu_layers') || '{}'); } catch (e) { state = {}; }
  function isOn(id) { var v = state[id]; return v == null ? LAYERS.find(function (l) { return l.id === id; }).def : !!v; }

  function ensureStyles() {
    if (document.getElementById('layers-styles')) return;
    var css = ''
      + '#lay-btn{position:absolute;left:12px;top:12px;z-index:20;display:flex;align-items:center;gap:6px;'
      + 'padding:7px 12px;border-radius:9px;cursor:pointer;font-family:var(--os-font,Inter,system-ui,sans-serif);font-size:12px;font-weight:600;'
      + 'background:var(--os-surface,rgba(15,21,34,.85));border:1px solid var(--os-line,rgba(122,158,255,.3));color:var(--os-ink-2,#c8d0e0);'
      + 'box-shadow:var(--os-shadow,none);backdrop-filter:blur(6px)}'
      + '#lay-btn:hover{border-color:var(--os-accent,#00E0FF);color:var(--os-accent,#00E0FF)}'
      + '#lay-btn.on{border-color:var(--os-accent,#00E0FF);color:var(--os-accent,#00E0FF)}'
      + '#lay-panel{position:absolute;left:12px;top:52px;z-index:21;width:224px;display:none;flex-direction:column;gap:3px;'
      + 'padding:12px 13px;border-radius:12px;background:var(--os-surface,radial-gradient(320px 200px at 60% -10%,#0d1424,#06090F));'
      + 'border:1px solid var(--os-line,rgba(122,158,255,.2));box-shadow:var(--kos-shadow-lg,0 16px 44px rgba(0,0,0,.5));color:var(--os-ink,#E8EDFB);'
      + 'font-family:var(--os-font,Inter,system-ui,sans-serif)}'
      + '#lay-panel.show{display:flex}'
      + '#lay-panel h4{margin:0 0 8px;font-size:10.5px;letter-spacing:.15em;text-transform:uppercase;color:var(--os-ink-2,#7C87A3);font-weight:600;display:flex;justify-content:space-between;align-items:center}'
      + '#lay-panel .lx{cursor:pointer;color:var(--os-ink-2,#7C87A3);font-size:14px;line-height:1}'
      + '.lay-row{display:flex;align-items:center;gap:9px;padding:5px 6px;border-radius:7px;cursor:pointer;font-size:12px;color:var(--os-ink-2,#9BA6C4);transition:background .1s}'
      + '.lay-row:hover{background:var(--os-surface-2,rgba(122,158,255,.06))}'
      + '.lay-row.on{color:var(--os-ink,#E8EDFB)}'
      + '.lay-sw{width:26px;height:15px;border-radius:9px;border:1px solid var(--os-line,rgba(122,158,255,.25));position:relative;flex:none;background:var(--os-surface-3,rgba(21,28,45,.9));transition:background .15s,border-color .15s}'
      + '.lay-row.on .lay-sw{background:var(--kos-accent-soft,rgba(0,224,255,.28));border-color:var(--os-accent,#00E0FF)}'
      + '.lay-sw::after{content:"";position:absolute;top:1px;left:2px;width:11px;height:11px;border-radius:50%;background:var(--os-ink-3,#7C87A3);transition:left .15s,background .15s}'
      + '.lay-row.on .lay-sw::after{left:auto;right:2px;background:var(--os-accent,#00E0FF)}'
      + '#lay-note{font-size:10px;color:var(--os-ink-2,#5c657f);margin-top:7px;line-height:1.4}';
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

  // textos visibles ES/EN (se re-aplican al cambiar de idioma)
  function relabel() {
    var btn = document.getElementById('lay-btn'), panel = document.getElementById('lay-panel');
    if (btn) { btn.innerHTML = '<span>◱</span> ' + L('Capas', 'Layers'); btn.title = L('Capas del mapa — enciende y apaga información', 'Map layers — switch information on and off'); }
    if (!panel) return;
    var h = panel.querySelector('.lay-h'); if (h) h.textContent = L('Capas del mapa', 'Map layers');
    panel.querySelectorAll('.lay-row').forEach(function (r) {
      var l = LAYERS.find(function (y) { return y.id === r.dataset.id; }), t = r.querySelector('.lay-lb');
      if (l && t) t.textContent = lbl(l);
    });
    var n = document.getElementById('lay-note');
    if (n) n.textContent = L('El color de los nodos se controla en la leyenda (sector ⇄ detalle).', 'Node colour is set in the legend (sector ⇄ detail).');
  }

  function mount() {
    var wrap = document.querySelector('.graph-wrap');
    if (!wrap || document.getElementById('lay-btn')) return;
    ensureStyles();
    var btn = document.createElement('div');
    btn.id = 'lay-btn'; btn.className = 'kos-themed';   // tokens --os-* de Khipus OS (claro/oscuro)
    btn.onclick = togglePanel;
    var panel = document.createElement('div');
    panel.id = 'lay-panel'; panel.className = 'kos-themed';
    panel.innerHTML = '<h4><span class="lay-h"></span> <span class="lx">✕</span></h4>' +
      LAYERS.map(function (l) {
        return '<div class="lay-row" data-id="' + l.id + '"><span class="lay-sw"></span><span class="lay-lb"></span></div>';
      }).join('') +
      '<div id="lay-note"></div>';
    wrap.appendChild(btn); wrap.appendChild(panel);
    relabel();
    panel.querySelector('.lx').onclick = togglePanel;
    panel.querySelectorAll('.lay-row').forEach(function (r) {
      r.onclick = function () { toggleLayer(r.dataset.id); };
    });
    apply();
  }

  window._layersApply = apply;   // re-aplicar tras un re-render del grafo
  // idioma: applyLang() (app.html) fija <html lang>; también 'khipu:lang' y cambios de otra pestaña
  try { new MutationObserver(relabel).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] }); } catch (e) {}
  window.addEventListener('khipu:lang', relabel);
  window.addEventListener('storage', function (e) { if (e && e.key === 'eco_lang') relabel(); });
  if (document.querySelector('.graph-wrap')) mount();
  else document.addEventListener('DOMContentLoaded', mount);
  setTimeout(mount, 1500);
})();
