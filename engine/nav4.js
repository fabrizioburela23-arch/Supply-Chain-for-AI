/* ============================================================================
   engine/nav4.js — NAVEGACIÓN DE 4 PESTAÑAS (simplificación pedida por Fabrizio)
   Las 10 pestañas se agrupan bajo 4 primarias:
     🗺️ Mapa  → map · geo · space · tkg · simulation
     📈 Mercado → market
     💡 Insights → analysis · canvas · terminal
     ❓ Guía   → guia
   NO toca switchTab ni los paneles: los sub-modos siguen siendo botones .tab
   con data-tab (los cablea el código existente). Este módulo solo pinta la
   barra primaria + muestra la fila de sub-modos del grupo activo. La fila
   secundaria se oculta cuando el grupo tiene un solo modo (Mercado, Guía).
   ============================================================================ */
(function () {
  'use strict';

  // 2026-07-11 (Fabrizio): la pestaña se llama TERMINAL y abre la terminal
  // por defecto ("no me parece que la terminal esté en insights").
  var GROUP_DEFAULT = { mapa: 'map', mercado: 'market', insights: 'terminal', guia: 'guia' };
  var TAB_GROUP = {};   // se llena leyendo data-group del DOM

  function ensureStyles() {
    if (document.getElementById('nav4-styles')) return;
    var css = ''
      + '#nav4{display:flex;flex-direction:column;gap:0;padding:0;border-bottom:1px solid var(--line,rgba(122,158,255,.12))}'
      + '.ptabs{display:flex;gap:4px;padding:7px 12px 0}'
      + '.ptab{display:flex;align-items:center;gap:7px;padding:8px 16px;border:none;background:none;cursor:pointer;'
      + 'font-family:Inter,system-ui,sans-serif;font-size:13.5px;font-weight:600;color:var(--ink-3,#8791AC);'
      + 'border-radius:9px 9px 0 0;transition:color .12s,background .12s;position:relative}'
      + '.ptab:hover{color:var(--ink,#E8EDFB)}'
      + '.ptab.active{color:#00E0FF}'
      + '.ptab.active::after{content:"";position:absolute;left:12px;right:12px;bottom:-1px;height:2px;background:#00E0FF;border-radius:2px;box-shadow:0 0 8px rgba(0,224,255,.5)}'
      + '.stabs{display:flex;gap:2px;padding:4px 12px 6px;flex-wrap:wrap;align-items:center}'
      + '.stabs.hide{display:none}'
      + '.stabs .tab{padding:5px 12px;font-size:12px;border-radius:7px;border:1px solid transparent;background:none;'
      + 'cursor:pointer;color:var(--ink-3,#8791AC);font-family:inherit;transition:all .12s;display:none}'
      + '.stabs .tab:hover{color:var(--ink,#E8EDFB);background:rgba(122,158,255,.06)}'
      + '.stabs .tab.active{color:#00E0FF;background:rgba(0,224,255,.1);border-color:rgba(0,224,255,.3)}'
      + '.stabs.g-mapa .tab[data-group="mapa"],'
      + '.stabs.g-mercado .tab[data-group="mercado"],'
      + '.stabs.g-insights .tab[data-group="insights"],'
      + '.stabs.g-guia .tab[data-group="guia"]{display:inline-flex;align-items:center;gap:5px}'
      /* fluidez: fundido sutil al cambiar de pestaña (solo opacity — no
         transform: main contiene SVG/fixed y un transform lo rompería) */
      + '@keyframes panelIn{from{opacity:.4}to{opacity:1}}'
      + '.panel-in{animation:panelIn .16s ease}'
      + '@media(prefers-reduced-motion:reduce){.panel-in{animation:none}}'
      /* la sub-pestaña 🪐 3D destaca (entrada principal al universo) */
      + '#tab-3d{border:1px solid rgba(142,90,255,.35)!important;background:rgba(142,90,255,.07)}'
      + '#tab-3d:hover{border-color:rgba(142,90,255,.7)!important;color:#cabeff!important}'
      + '#tab-3d.active{color:#cabeff!important;background:rgba(142,90,255,.18)!important;border-color:#8e5aff!important;box-shadow:0 0 10px rgba(142,90,255,.35)}';
    var st = document.createElement('style'); st.id = 'nav4-styles'; st.textContent = css;
    document.head.appendChild(st);
  }

  function groupOf(tab) { return TAB_GROUP[tab] || 'mapa'; }

  // panel visible de cada tab — para el fundido de fluidez
  var PANEL_OF = { map: 'main', market: '#market', analysis: '#analysis-panel',
    geo: '#geo-panel', simulation: '#simulation-panel', space: '#space-panel',
    terminal: '#terminal-panel', canvas: '#canvas-panel', tkg: '#tkg-panel', guia: '#guia-panel' };

  function syncTo(tab) {
    var grp = groupOf(tab);
    document.querySelectorAll('.ptab').forEach(function (b) { b.classList.toggle('active', b.dataset.group === grp); });
    var stabs = document.getElementById('stabs');
    if (stabs) {
      ['mapa', 'mercado', 'insights', 'guia'].forEach(function (g) { stabs.classList.toggle('g-' + g, g === grp); });
      // ocultar la fila secundaria si el grupo tiene un solo modo
      var count = stabs.querySelectorAll('.tab[data-group="' + grp + '"]').length;
      stabs.classList.toggle('hide', count <= 1);
    }
    // fluidez: fundido sutil del panel que entra (re-disparable)
    try {
      var el = document.querySelector(PANEL_OF[tab] || 'x');
      if (el) { el.classList.remove('panel-in'); void el.offsetWidth; el.classList.add('panel-in'); }
    } catch (e) {}
  }

  function mount() {
    var nav = document.getElementById('nav4'); if (!nav) return;
    ensureStyles();
    // mapear cada tab → grupo desde el DOM
    document.querySelectorAll('.stabs .tab').forEach(function (b) { TAB_GROUP[b.dataset.tab] = b.dataset.group; });
    // primarias: al hacer clic, ir al modo por defecto del grupo (o al último usado)
    var lastOf = {};
    document.querySelectorAll('.ptab').forEach(function (p) {
      p.onclick = function () {
        var g = p.dataset.group;
        var target = lastOf[g] || GROUP_DEFAULT[g];
        if (typeof window.switchTab === 'function') window.switchTab(target);
      };
    });
    // recordar el último sub-modo usado por grupo
    document.querySelectorAll('.stabs .tab').forEach(function (b) {
      b.addEventListener('click', function () { lastOf[b.dataset.group] = b.dataset.tab; });
    });
    // envolver switchTab para sincronizar la barra (incluye llamadas programáticas)
    if (window.switchTab && !window._nav4Wrapped) {
      var orig = window.switchTab;
      window.switchTab = function (tab) { var r = orig.apply(this, arguments); try { syncTo(tab); } catch (e) {} return r; };
      window._nav4Wrapped = true;
    }
    syncTo(window.activeTab || 'map');
  }

  // esperar a que switchTab exista (se define en el bloque grande de app.html)
  function wait() {
    if (document.getElementById('nav4') && typeof window.switchTab === 'function') { mount(); return; }
    setTimeout(wait, 120);
  }
  if (document.readyState !== 'loading') wait();
  else document.addEventListener('DOMContentLoaded', wait);
})();
