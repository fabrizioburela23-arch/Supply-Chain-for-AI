/* ============================================================================
   engine/cockpit.js — CABINA DE BIXBY · el modo pantalla completa
   Bixby deja de ser un botón: SE VUELVE la pantalla.
   - Arriba: el orbe/logo de Bixby + estado (escuchando / pensando / listo) +
     una barra para pedirle cosas por texto o por voz (🎙).
   - Abajo: un ESCENARIO grande (un lienzo) donde Bixby te muestra lo que pidas:
       · la radiografía completa de una empresa (X-Ray a pantalla completa)
       · una simulación de shock (a quién arrastra / quién gana)
       · dos empresas comparadas lado a lado
       · un gráfico / tabla generado por IA (Canvas)  ·  o un lienzo en blanco
   Voz y texto van al MISMO escenario: cuando Bixby (por voz) abre un X-Ray,
   xray.js detecta que la cabina está abierta y lo pinta aquí, no en el cajón.

   Depende de (todos ya cargados antes que este archivo):
     window.buildXRayHTML / wireXRay (xray.js) · KhipuState (statematrix.js) ·
     registerBixbyOrb (app.html) · BixbyVoice (voice.js) · KHIPU (khipu_lang.js)
   ============================================================================ */
(function () {
  'use strict';

  var NEON = '#00E0FF', VIOLET = '#8e5aff', UP = '#2BE38B', DOWN = '#FF4D6A';
  var open = false;

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  // resuelve empresa desde id/ticker/nombre (reusa el de voice.js si está)
  function resolveNode(q) {
    if (window.BixbyVoice && window.BixbyVoice._resolveNode) { var n = window.BixbyVoice._resolveNode(q); if (n) return n; }
    if (q == null || typeof NODES === 'undefined') return null;
    var s = String(q).trim(); if (!s) return null; var lc = s.toLowerCase();
    return NODES.find(function (n) { return n.id === s || n.mkt === s; })
      || NODES.find(function (n) { return (n.id || '').toLowerCase() === lc || (n.mkt || '').toLowerCase() === lc; })
      || NODES.find(function (n) { return (n.label || '').toLowerCase() === lc; })
      || NODES.find(function (n) { return (n.label || '').toLowerCase().indexOf(lc) >= 0; }) || null;
  }

  // ── estilos ──
  function ensureStyles() {
    if (document.getElementById('bcp-styles')) return;
    var css = `
#bcp-ov{position:fixed;inset:0;z-index:7000;display:none;flex-direction:column;
  background:radial-gradient(1200px 700px at 50% -10%,#0B1424 0%,#05070E 55%,#04060B 100%);
  color:#E8EDFB;font-family:'Inter',system-ui,sans-serif;animation:bcpFade .22s ease}
#bcp-ov.show{display:flex}
@keyframes bcpFade{from{opacity:0}to{opacity:1}}
#bcp-top{display:flex;align-items:center;gap:16px;padding:16px 22px 12px;border-bottom:1px solid rgba(122,158,255,.12);flex-shrink:0}
#bcp-orb-wrap{position:relative;width:64px;height:64px;flex-shrink:0;filter:drop-shadow(0 0 22px rgba(80,60,255,.35))}
#bcp-orb-canvas{display:block;border-radius:50%}
#bcp-idwrap{display:flex;flex-direction:column;gap:3px;min-width:0}
#bcp-word{font-size:16px;font-weight:800;letter-spacing:.16em;background:linear-gradient(90deg,#00E0FF,#8e5aff);
  -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
#bcp-state{font-size:9.5px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#7C87A3;display:flex;align-items:center;gap:6px}
#bcp-state .dot{width:7px;height:7px;border-radius:50%;background:#7C87A3;box-shadow:0 0 8px currentColor}
#bcp-state.live .dot{background:#00E0FF;color:#00E0FF;animation:bcpPulse 1.2s ease-in-out infinite}
#bcp-state.think .dot{background:#FFB300;color:#FFB300;animation:bcpPulse .7s ease-in-out infinite}
@keyframes bcpPulse{0%,100%{opacity:1}50%{opacity:.3}}
#bcp-bar{flex:1;display:flex;align-items:center;gap:9px;max-width:720px;margin:0 auto}
#bcp-input{flex:1;background:rgba(11,18,34,.8);border:1px solid rgba(122,158,255,.22);border-radius:12px;
  color:#E8EDFB;font-size:14px;padding:12px 15px;outline:none;font-family:inherit;transition:border-color .15s,box-shadow .15s}
#bcp-input:focus{border-color:rgba(0,224,255,.55);box-shadow:0 0 0 3px rgba(0,224,255,.1)}
#bcp-input::placeholder{color:#5b6580}
.bcp-iconbtn{width:44px;height:44px;flex-shrink:0;border-radius:12px;border:1px solid rgba(122,158,255,.22);
  background:rgba(11,18,34,.8);color:#E8EDFB;cursor:pointer;font-size:17px;display:flex;align-items:center;justify-content:center;
  transition:all .14s}
.bcp-iconbtn:hover{border-color:rgba(0,224,255,.5);color:#00E0FF}
#bcp-mic.on{background:rgba(214,59,59,.85);border-color:#d63b3b;color:#fff;box-shadow:0 0 18px rgba(214,59,59,.45);animation:bcpPulse 1.1s ease-in-out infinite}
#bcp-close{margin-left:6px}
#bcp-actions{display:flex;gap:7px;flex-wrap:wrap;padding:9px 22px 0;flex-shrink:0}
.bcp-act{font-size:11.5px;padding:6px 13px;border-radius:9px;cursor:pointer;color:#9BA6C4;
  background:rgba(11,18,34,.6);border:1px solid rgba(122,158,255,.16);transition:all .13s;
  font-family:inherit;display:inline-flex;align-items:center;gap:6px}
.bcp-act:hover{color:#E8EDFB;border-color:rgba(0,224,255,.45);transform:translateY(-1px)}
.bcp-act.on{color:#00E0FF;border-color:rgba(0,224,255,.5);background:rgba(0,224,255,.08)}
#bcp-stage{flex:1;overflow-y:auto;padding:22px;position:relative}
@keyframes bcpStageIn{from{opacity:.35;transform:translateY(4px)}to{opacity:1;transform:none}}
#bcp-stage>*{animation:bcpStageIn .16s ease}
@media(prefers-reduced-motion:reduce){#bcp-stage>*{animation:none}}
.bcp-embed{height:calc(100vh - 250px);min-height:420px;display:flex;flex-direction:column;
  border:1px solid rgba(122,158,255,.18);border-radius:14px;overflow:hidden;background:#04060B;position:relative}
/* estado vacío / lienzo */
#bcp-empty{max-width:820px;margin:4vh auto 0;text-align:center}
#bcp-empty h2{font-size:26px;font-weight:750;margin:0 0 8px;background:linear-gradient(90deg,#E8EDFB,#9BA6C4);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
#bcp-empty p{color:#7C87A3;font-size:14px;margin:0 0 26px}
.bcp-chips{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;max-width:680px;margin:0 auto}
.bcp-chip{font-size:13px;padding:10px 16px;border-radius:12px;cursor:pointer;color:#E8EDFB;
  background:rgba(11,18,34,.7);border:1px solid rgba(122,158,255,.18);transition:all .14s}
.bcp-chip:hover{border-color:rgba(0,224,255,.5);transform:translateY(-2px);box-shadow:0 6px 20px rgba(0,0,0,.35)}
.bcp-chip .k{color:#00E0FF;font-weight:700;margin-right:7px}
.bcp-stagehd{display:flex;align-items:center;gap:10px;margin:0 auto 14px;max-width:1200px}
.bcp-back{font-size:12px;color:#9BA6C4;cursor:pointer;border:1px solid rgba(122,158,255,.2);
  border-radius:9px;padding:6px 12px;background:rgba(11,18,34,.6);transition:all .14s}
.bcp-back:hover{border-color:rgba(0,224,255,.45);color:#E8EDFB}
.bcp-inner{max-width:1200px;margin:0 auto}
.bcp-cmp{display:flex;gap:18px;align-items:flex-start;flex-wrap:wrap}
.bcp-cmp > div{flex:1;min-width:320px;border:1px solid rgba(122,158,255,.14);border-radius:16px;
  background:rgba(11,18,34,.5);overflow:hidden}
/* dossier de simulación */
.bcp-simhd{display:flex;align-items:baseline;gap:12px;margin-bottom:16px;flex-wrap:wrap}
.bcp-simhd .big{font-size:22px;font-weight:700}
.bcp-simhd .kind{font-size:11px;text-transform:uppercase;letter-spacing:.1em;padding:4px 11px;border-radius:999px}
.bcp-grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:20px}
.bcp-stat{border:1px solid rgba(122,158,255,.14);border-radius:12px;padding:14px;background:rgba(11,18,34,.5)}
.bcp-stat b{display:block;font-family:'JetBrains Mono',monospace;font-size:24px;font-weight:700}
.bcp-stat span{font-size:10px;color:#7C87A3;text-transform:uppercase;letter-spacing:.06em}
.bcp-two{display:grid;grid-template-columns:1fr 1fr;gap:20px}
@media(max-width:760px){.bcp-two{grid-template-columns:1fr}}
.bcp-lh{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:#7C87A3;font-weight:600;margin:0 0 10px}
.bcp-row{display:flex;align-items:center;gap:9px;font-size:12.5px;padding:5px 0;cursor:pointer}
.bcp-row:hover .nm{color:#00E0FF}
.bcp-row .nm{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bcp-row .bar{width:90px;height:5px;border-radius:3px;overflow:hidden;flex:none}
.bcp-row .bar i{display:block;height:100%}
.bcp-row .pv{font-family:'JetBrains Mono',monospace;font-size:11px;width:42px;text-align:right;flex:none}
.bcp-dot{width:8px;height:8px;border-radius:50%;flex:none;box-shadow:0 0 6px currentColor}
.bcp-canvaswrap{max-width:900px;margin:0 auto}
.bcp-canvasbar{display:flex;gap:9px;margin-bottom:16px}
.bcp-loading{color:#7C87A3;font-size:13px;font-style:italic;text-align:center;padding:40px}
`;
    var st = document.createElement('style'); st.id = 'bcp-styles'; st.textContent = css;
    document.head.appendChild(st);
  }

  // ── shell (una vez) ──
  function ensureShell() {
    ensureStyles();
    if (window.xrayEnsureStyles) window.xrayEnsureStyles();
    var ov = document.getElementById('bcp-ov');
    if (ov) return ov;
    ov = document.createElement('div');
    ov.id = 'bcp-ov';
    ov.innerHTML =
      '<div id="bcp-top">' +
        '<div id="bcp-orb-wrap"><canvas id="bcp-orb-canvas" width="64" height="64"></canvas></div>' +
        '<div id="bcp-idwrap"><div id="bcp-word">BIXBY</div>' +
          '<div id="bcp-state"><span class="dot"></span><span class="txt">Listo</span></div></div>' +
        '<div id="bcp-bar">' +
          '<input id="bcp-input" type="text" autocomplete="off" spellcheck="false" ' +
            'placeholder="Pídele algo a Bixby…  «desármame Nvidia»  ·  «¿qué pasa si cae TSMC?»">' +
          '<button class="bcp-iconbtn" id="bcp-send" title="Enviar">➤</button>' +
          '<button class="bcp-iconbtn" id="bcp-mic" title="Hablar con Bixby">🎙</button>' +
        '</div>' +
        '<button class="bcp-iconbtn" id="bcp-close" title="Cerrar (Esc)">✕</button>' +
      '</div>' +
      // Barra de BOTONES (pedido de Fabrizio): todo lo que Bixby puede
      // mostrar, a un clic — el grafo y la terminal viven DENTRO del escenario.
      '<div id="bcp-actions">' +
        '<button class="bcp-act" data-act="graph">🗺️ Grafo</button>' +
        '<button class="bcp-act" data-act="terminal">🖥️ Terminal</button>' +
        '<button class="bcp-act" data-act="xray">🔬 X-Ray</button>' +
        '<button class="bcp-act" data-act="sim">◉ Simular</button>' +
        '<button class="bcp-act" data-act="compare">⇄ Comparar</button>' +
        '<button class="bcp-act" data-act="insights">💡 Oportunidades</button>' +
        '<button class="bcp-act" data-act="deep">🧠 Investigar</button>' +
        '<button class="bcp-act" data-act="canvas">✦ Gráfico</button>' +
      '</div>' +
      '<div id="bcp-stage"></div>';
    document.body.appendChild(ov);

    ov.querySelectorAll('.bcp-act').forEach(function (b) {
      b.addEventListener('click', function () {
        var act = b.getAttribute('data-act');
        var input = document.getElementById('bcp-input');
        // acciones directas
        if (act === 'graph') return stage('graph');
        if (act === 'terminal') return stage('terminal');
        if (act === 'insights') return stage('insights');
        if (act === 'canvas') return stage('canvas');
        // acciones que necesitan una empresa → prellenar la barra (enseña la sintaxis)
        var sel = (window._liveSelectedNode && window._liveSelectedNode()) || null;
        var name = sel && window.NODE_BY_ID && window.NODE_BY_ID[sel] ? window.NODE_BY_ID[sel].label : '';
        if (act === 'xray') { if (name) return stage('xray', sel); input.value = 'desármame '; }
        if (act === 'sim') { if (name) return stage('sim', { id: sel, kind: 'collapse' }); input.value = '¿qué pasa si cae '; }
        if (act === 'compare') { input.value = 'compara ' + (name ? name + ' y ' : ''); }
        if (act === 'deep') { input.value = 'investiga '; }
        input.focus();
      });
    });

    var input = ov.querySelector('#bcp-input');
    ov.querySelector('#bcp-send').addEventListener('click', function () { submit(); });
    input.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); submit(); } });
    ov.querySelector('#bcp-mic').addEventListener('click', toggleMic);
    ov.querySelector('#bcp-close').addEventListener('click', close);
    function submit() { var v = (input.value || '').trim(); if (!v) return; input.value = ''; ask(v); }

    if (window.registerBixbyOrb) window.registerBixbyOrb('bcp-orb-canvas', 64);
    return ov;
  }

  // ── estado del orbe / badge (lo llama voice.js también) ──
  function setState(mode, text) {
    var el = document.getElementById('bcp-state');
    if (!el) return;
    el.className = mode === 'live' ? 'live' : mode === 'think' ? 'think' : '';
    var t = el.querySelector('.txt'); if (t && text) t.textContent = text;
    if (window.setBixbyThinking) window.setBixbyThinking(mode === 'think');
  }

  // ── micrófono / voz ──
  function toggleMic() {
    var btn = document.getElementById('bcp-mic');
    if (!window.BixbyVoice) { setState('', 'Voz no disponible'); return; }
    var on = window.BixbyVoice.isConnected;
    if (on) { window.BixbyVoice.stop && window.BixbyVoice.stop(); if (btn) btn.classList.remove('on'); setState('', 'Listo'); }
    else { window.BixbyVoice.toggle && window.BixbyVoice.toggle(); if (btn) btn.classList.add('on'); setState('live', 'Escuchando'); }
  }

  // ── ADOPCIÓN de paneles reales: el grafo y la terminal se MUEVEN al
  // escenario de la Cabina (con un placeholder para devolverlos intactos al
  // salir). Así Bixby los muestra EN SU PANTALLA, no te lleva a otra pestaña.
  var _adopted = [];

  function restoreAdopted() {
    var hadGraph = false;
    while (_adopted.length) {
      var a = _adopted.pop();
      try {
        if (a.el.tagName === 'MAIN') hadGraph = true;
        a.el.style.display = a.prevDisplay;
        if (a.ph.parentNode) a.ph.parentNode.replaceChild(a.el, a.ph);
      } catch (e) {}
    }
    try { window.dispatchEvent(new Event('resize')); } catch (e) {}
    // anti-glitch (feedback real): el grafo volvía clavado/zoomeado en una
    // empresa — al devolverlo, re-encuadramos la vista completa
    if (hadGraph) {
      setTimeout(function () {
        try { if (typeof fitToView === 'function') fitToView(); } catch (e) {}
      }, 150);
    }
  }

  function adoptInto(container, el, displayMode) {
    if (!el || !el.parentNode) return false;
    var ph = document.createComment('bcp-placeholder');
    _adopted.push({ el: el, ph: ph, prevDisplay: el.style.display });
    el.parentNode.replaceChild(ph, el);
    container.appendChild(el);
    el.style.display = displayMode || 'flex';
    setTimeout(function () { try { window.dispatchEvent(new Event('resize')); } catch (e) {} }, 60);
    return true;
  }

  function markActive(act) {
    document.querySelectorAll('.bcp-act').forEach(function (b) {
      b.classList.toggle('on', b.getAttribute('data-act') === act);
    });
  }

  // ══ ESCENARIO ══
  function stage(kind, arg) {
    ensureShell();
    var s = document.getElementById('bcp-stage');
    if (!s) return;
    restoreAdopted();   // devolver cualquier panel adoptado antes de cambiar de escena
    markActive(kind === 'graph' || kind === 'terminal' || kind === 'insights' || kind === 'canvas' || kind === 'deep' ? kind : null);
    if (kind === 'xray') return stageXRay(s, arg);
    if (kind === 'compare') return stageCompare(s, arg);
    if (kind === 'sim') return stageSim(s, arg);
    if (kind === 'insights') return stageInsights(s);
    if (kind === 'canvas') return stageCanvas(s, arg);
    if (kind === 'deep') return stageDeep(s, arg);
    if (kind === 'graph') return stageGraph(s, arg);
    if (kind === 'terminal') return stageTerminal(s, arg);
    return stageEmpty(s);
  }

  // ── el GRAFO en vivo, dentro de la Cabina ──
  function stageGraph(s, focusId) {
    s.innerHTML = backBar('Grafo en vivo') + '<div class="bcp-embed" id="bcp-embed-graph"></div>';
    var main = document.querySelector('main');
    if (!adoptInto(s.querySelector('#bcp-embed-graph'), main, 'flex')) {
      s.innerHTML += '<div class="bcp-loading">No se pudo montar el grafo</div>';
      return;
    }
    // re-encuadrar al tamaño del escenario (si no, entra con el zoom que traía)
    setTimeout(function () {
      try { if (typeof fitToView === 'function' && !focusId) fitToView(); } catch (e) {}
    }, 180);
    if (focusId) {
      var n = resolveNode(focusId);
      if (n) setTimeout(function () { try { if (typeof jumpTo === 'function') jumpTo(n.id); } catch (e) {} }, 220);
    }
  }

  // ── la TERMINAL Bloomberg, dentro de la Cabina ──
  function stageTerminal(s, arg) {
    arg = arg || {};
    s.innerHTML = backBar('Terminal') + '<div class="bcp-embed" id="bcp-embed-term"></div>';
    var term = document.getElementById('terminal-panel');
    if (!adoptInto(s.querySelector('#bcp-embed-term'), term, 'flex')) {
      s.innerHTML += '<div class="bcp-loading">No se pudo montar la terminal</div>';
      return;
    }
    try { if (typeof window.initTerminalTab === 'function') window.initTerminalTab(); } catch (e) {}
    var tk = arg.ticker || arg;
    if (tk && typeof tk === 'string') {
      setTimeout(function () { try { if (window._termOpenTicker) window._termOpenTicker(tk); } catch (e) {} }, 250);
    }
  }

  function backBar(label) {
    return '<div class="bcp-stagehd"><span class="bcp-back" onclick="window.BixbyCockpit.stage(\'empty\')">← Inicio</span>' +
      (label ? '<span style="color:#7C87A3;font-size:12px">' + esc(label) + '</span>' : '') + '</div>';
  }

  function stageEmpty(s) {
    var chips = [
      ['desármame ', 'Nvidia', 'Radiografía completa'],
      ['¿qué pasa si cae ', 'TSMC?', 'Simular un shock'],
      ['compara ', 'Nvidia y AMD', 'Dos empresas'],
      ['muéstrame ', 'oportunidades', 'Dónde invertir'],
      ['gráfico: ', 'márgenes de NVIDIA, TSMC y ASML', 'Lienzo de datos'],
      ['investiga ', 'la energía nuclear para datacenters', 'Investigación profunda'],
      ['', 'lienzo en blanco', 'Empezar de cero'],
    ];
    s.innerHTML = '<div id="bcp-empty"><h2>Soy Bixby. Pregúntame lo que sea.</h2>' +
      '<p>Puedo desarmar cualquier empresa, simular qué pasa si algo cae, comparar, y dibujarte los datos.</p>' +
      '<div class="bcp-chips">' + chips.map(function (c) {
        return '<span class="bcp-chip" data-q="' + esc(c[0] + c[1]) + '"><span class="k">' + esc(c[2]) + '</span>' + esc(c[0] + c[1]) + '</span>';
      }).join('') + '</div></div>';
    s.querySelectorAll('.bcp-chip').forEach(function (el) {
      el.addEventListener('click', function () { ask(el.getAttribute('data-q')); });
    });
  }

  function stageXRay(s, id) {
    var n = resolveNode(id); if (!n) { stageEmpty(s); return; }
    if (!window.buildXRayHTML) { s.innerHTML = '<div class="bcp-loading">X-Ray no disponible</div>'; return; }
    s.innerHTML = backBar('Radiografía') +
      '<div class="bcp-inner"><div id="bcp-xray" class="xray-scope xr-full">' + window.buildXRayHTML(n.id, { full: true }) + '</div></div>';
    var root = s.querySelector('#bcp-xray');
    if (window.wireXRay) window.wireXRay(root, n.id);
  }

  function stageCompare(s, arg) {
    arg = arg || {};
    var a = resolveNode(arg.a), b = arg.b ? resolveNode(arg.b) : null;
    if (!a) { stageEmpty(s); return; }
    if (!b) b = pickRival(a);   // si solo dieron una, comparamos vs su rival natural
    if (!b) { stageXRay(s, a.id); return; }
    s.innerHTML = backBar('Comparar') +
      '<div class="bcp-inner"><div class="bcp-cmp">' +
        '<div class="xray-scope" id="bcp-cmpA">' + window.buildXRayHTML(a.id, { full: false }) + '</div>' +
        '<div class="xray-scope" id="bcp-cmpB">' + window.buildXRayHTML(b.id, { full: false }) + '</div>' +
      '</div></div>';
    if (window.wireXRay) { window.wireXRay(s.querySelector('#bcp-cmpA'), a.id); window.wireXRay(s.querySelector('#bcp-cmpB'), b.id); }
  }

  // rival natural: misma categoría, mayor mkt cap, distinta empresa
  function pickRival(a) {
    var meta = window.NODE_META || {};
    var best = null, bestCap = -1;
    (window.NODES || []).forEach(function (x) {
      if (x.id === a.id || x.cat !== a.cat) return;
      var cap = Number((meta[x.id] || {}).mktcap_b) || 0;
      if (cap > bestCap) { bestCap = cap; best = x; }
    });
    return best;
  }

  function sectorColor(cat) { var S = window.SECTORS9 || {}, M = window.CAT_TO_SECTOR || {}; var s = S[M[cat] || 'cloud_ia']; return s ? s.color : NEON; }

  function stageSim(s, arg) {
    arg = arg || {};
    var n = resolveNode(arg.id); if (!n) { stageEmpty(s); return; }
    var kind = ['collapse', 'demand', 'price', 'sanction'].indexOf(arg.kind) >= 0 ? arg.kind : 'collapse';
    var dir = kind === 'demand' ? 'up' : 'down';
    var kindLabel = { collapse: 'Corte / caída', demand: 'Auge de demanda', price: 'Shock de precio', sanction: 'Sanción' }[kind];
    var tint = dir === 'up' ? UP : DOWN;
    if (!window.KhipuState || !window.KhipuState.simulate) { s.innerHTML = backBar() + '<div class="bcp-loading">Motor de simulación no disponible</div>'; return; }
    var shock = {}; shock[n.id] = (kind === 'demand') ? { salud: 100 } : { salud: 0 };
    var r = window.KhipuState.simulate(shock, [], 8, 0.6, false, { direction: dir, kind: kind });
    var impacts = {}; if (r && r.impact) r.impact.forEach(function (v, k) { if (k !== n.id && v > 0) impacts[k] = v; });
    var arr = Object.keys(impacts).map(function (k) { return { id: k, v: impacts[k] }; }).sort(function (a, b) { return b.v - a.v; });

    // desglose por sector
    var secAgg = {};
    arr.forEach(function (x) { var nd = window.NODE_BY_ID[x.id]; if (!nd) return; var sc = (window.CAT_TO_SECTOR || {})[nd.cat] || 'cloud_ia'; (secAgg[sc] = secAgg[sc] || { sum: 0, n: 0 }); secAgg[sc].sum += x.v; secAgg[sc].n++; });
    var secRows = Object.keys(secAgg).map(function (k) { return { k: k, avg: secAgg[k].sum / secAgg[k].n, n: secAgg[k].n }; })
      .sort(function (a, b) { return b.avg - a.avg; }).slice(0, 8);
    var SLAB = window.SECTORS9 || {};

    // ganadores
    var winners = window.xrayComputeWinners ? window.xrayComputeWinners(n.id, (function () { var o = {}; o[n.id] = 100; arr.forEach(function (x) { o[x.id] = x.v; }); return o; })()) : [];

    var victimRows = arr.slice(0, 12).map(function (x) {
      var nd = window.NODE_BY_ID[x.id]; if (!nd) return '';
      return '<div class="bcp-row" onclick="window.BixbyCockpit.stage(\'xray\',\'' + esc(x.id) + '\')">' +
        '<span class="bcp-dot" style="background:' + sectorColor(nd.cat) + ';color:' + sectorColor(nd.cat) + '"></span>' +
        '<span class="nm">' + esc(nd.label) + '</span>' +
        '<span class="bar" style="background:rgba(255,77,106,.15)"><i style="width:' + Math.round(x.v) + '%;background:' + tint + '"></i></span>' +
        '<span class="pv" style="color:' + tint + '">' + Math.round(x.v) + '%</span></div>';
    }).join('') || '<div class="bcp-loading" style="padding:16px">Sin propagación significativa</div>';

    var winRows = winners.length ? winners.map(function (w) {
      var nd = window.NODE_BY_ID[w.id]; if (!nd) return '';
      return '<div class="bcp-row" onclick="window.BixbyCockpit.stage(\'xray\',\'' + esc(w.id) + '\')">' +
        '<span class="bcp-dot" style="background:' + UP + ';color:' + UP + '"></span>' +
        '<span class="nm">' + esc(nd.label) + '</span>' +
        '<span class="bar" style="background:rgba(43,227,139,.15)"><i style="width:' + (w.up * 2) + '%;background:' + UP + '"></i></span>' +
        '<span class="pv" style="color:' + UP + '">+' + w.up + '%</span></div>';
    }).join('') : '<div class="bcp-loading" style="padding:10px">—</div>';

    var secRowsHTML = secRows.map(function (x) {
      var lab = (SLAB[x.k] || {}).label || x.k, cc = (SLAB[x.k] || {}).color || NEON;
      return '<div class="bcp-row"><span class="bcp-dot" style="background:' + cc + ';color:' + cc + '"></span>' +
        '<span class="nm">' + esc(lab) + ' <span style="color:#5b6580">(' + x.n + ')</span></span>' +
        '<span class="bar" style="background:rgba(122,158,255,.12)"><i style="width:' + Math.round(x.avg) + '%;background:' + cc + '"></i></span>' +
        '<span class="pv">' + Math.round(x.avg) + '%</span></div>';
    }).join('');

    s.innerHTML = backBar('Simulación') +
      '<div class="bcp-inner">' +
        '<div class="bcp-simhd"><span class="big">' + esc(n.label) + '</span>' +
          '<span class="kind" style="background:' + tint + '22;color:' + tint + '">' + esc(kindLabel) + '</span>' +
          '<span style="color:#7C87A3;font-size:12px">' + arr.length + ' empresas movidas</span>' +
          '<button class="bcp-back" style="margin-left:auto" onclick="window._cockpitMapSim(\'' + esc(n.id) + '\',\'' + kind + '\')">⚡ Ver en el mapa</button></div>' +
        '<div class="bcp-grid3">' +
          '<div class="bcp-stat"><b style="color:' + tint + '">' + arr.length + '</b><span>empresas afectadas</span></div>' +
          '<div class="bcp-stat"><b style="color:' + tint + '">' + (arr[0] ? Math.round(arr[0].v) + '%' : '—') + '</b><span>golpe máximo</span></div>' +
          '<div class="bcp-stat"><b style="color:' + UP + '">' + winners.length + '</b><span>ganadores</span></div>' +
        '</div>' +
        '<div class="bcp-two">' +
          '<div><div class="bcp-lh" style="color:' + tint + '">' + (dir === 'up' ? 'Quién se beneficia ↑' : 'Quién sufre ↓') + '</div>' + victimRows + '</div>' +
          '<div><div class="bcp-lh" style="color:' + UP + '">Quién gana ↑ (rivales)</div>' + winRows +
            '<div class="bcp-lh" style="margin-top:18px">Por sector</div>' + secRowsHTML + '</div>' +
        '</div>' +
      '</div>';
  }

  function stageInsights(s) {
    var comp = (typeof window.computeNRS === 'function');
    var risk = [], opps = [];
    if (comp) {
      var scored = (window.NODES || []).map(function (n) {
        var nrs = window.computeNRS(n.id);
        var g = (n.growth || '').toLowerCase();
        var growth = g.indexOf('🟢') >= 0 ? 2 : g.indexOf('🟡') >= 0 ? 1 : 0;
        var margin = n.margin != null ? n.margin : 0;
        return { id: n.id, nrs: nrs, growth: growth, margin: margin, score: growth * 22 + Math.min(30, margin * 60) + (50 - nrs) * 0.5 };
      });
      risk = scored.slice().sort(function (a, b) { return b.nrs - a.nrs; }).slice(0, 10);
      opps = scored.filter(function (x) { return x.nrs < 55 && x.growth >= 1 && x.margin > 0.15; }).sort(function (a, b) { return b.score - a.score; }).slice(0, 10);
    }
    function row(x, color, val) {
      var nd = window.NODE_BY_ID[x.id]; if (!nd) return '';
      return '<div class="bcp-row" onclick="window.BixbyCockpit.stage(\'xray\',\'' + esc(x.id) + '\')">' +
        '<span class="bcp-dot" style="background:' + sectorColor(nd.cat) + ';color:' + sectorColor(nd.cat) + '"></span>' +
        '<span class="nm">' + esc(nd.label) + '</span>' +
        '<span class="pv" style="color:' + color + '">' + val(x) + '</span></div>';
    }
    s.innerHTML = backBar('Insights') +
      '<div class="bcp-inner"><div class="bcp-two">' +
        '<div><div class="bcp-lh" style="color:' + DOWN + '">Mayor riesgo (NRS)</div>' +
          (risk.map(function (x) { return row(x, DOWN, function (y) { return y.nrs; }); }).join('') || '<div class="bcp-loading">—</div>') + '</div>' +
        '<div><div class="bcp-lh" style="color:' + UP + '">Oportunidades (resilientes)</div>' +
          (opps.map(function (x) { return row(x, UP, function (y) { return 'NRS ' + y.nrs; }); }).join('') || '<div class="bcp-loading">Sin oportunidades claras ahora</div>') + '</div>' +
      '</div></div>';
  }

  // ── Investigación profunda (Capa 4): planear→reunir→simular→sintetizar ──
  var _deepTimer = null;

  function stageDeep(s, question) {
    if (_deepTimer) { clearInterval(_deepTimer); _deepTimer = null; }
    question = (question || '').trim();
    s.innerHTML = backBar('Investigación profunda') +
      '<div class="bcp-inner" style="max-width:820px">' +
        '<div class="bcp-simhd"><span class="big">🧠 ' + esc(question || 'Análisis profundo') + '</span></div>' +
        '<div id="bcp-deep-steps" style="display:flex;flex-direction:column;gap:7px;margin-bottom:18px"></div>' +
        '<div id="bcp-deep-result"></div>' +
      '</div>';
    if (!question) return;
    setState('think', 'Investigando');

    fetch((window.BASE || '') + '/api/deep/analyze', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: question }),
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (d.error) { renderDeepError(d.error); return; }
      _deepTimer = setInterval(pollDeep, 2500);
      pollDeep();
    }).catch(function () { renderDeepError('No se pudo conectar con el servidor'); });

    function renderDeepError(msg) {
      var el = document.getElementById('bcp-deep-result');
      if (el) el.innerHTML = '<div class="bcp-loading" style="color:#FF4D6A">⚠ ' + esc(msg) + '</div>';
      setState('', 'Listo');
    }

    function pollDeep() {
      fetch((window.BASE || '') + '/api/deep/status').then(function (r) { return r.json(); }).then(function (d) {
        var stepsEl = document.getElementById('bcp-deep-steps');
        if (!stepsEl) { clearInterval(_deepTimer); _deepTimer = null; return; }  // salieron de la escena
        stepsEl.innerHTML = (d.steps || []).map(function (st, i) {
          var last = i === d.steps.length - 1 && d.running;
          return '<div style="display:flex;gap:9px;align-items:baseline;font-size:12.5px;color:#9BA6C4">' +
            '<span style="color:' + (last ? '#FFB300' : '#2BE38B') + '">' + (last ? '◌' : '✓') + '</span>' +
            '<span><b style="color:#E8EDFB">' + esc(st.paso) + '</b> — ' + esc(st.detalle || '') + '</span></div>';
        }).join('');
        if (!d.running && d.result) {
          clearInterval(_deepTimer); _deepTimer = null;
          setState('', 'Listo');
          var el = document.getElementById('bcp-deep-result');
          if (!el) return;
          if (d.result.error) { renderDeepError(d.result.error); return; }
          var simHTML = d.result.sim ?
            '<div class="bcp-grid3" style="margin:14px 0">' +
              '<div class="bcp-stat"><b style="color:#FF4D6A">' + d.result.sim.afectadas + '</b><span>afectadas si cae ' + esc(d.result.sim.shock) + '</span></div>' +
              '<div class="bcp-stat"><b style="color:#E8EDFB;font-size:14px">' + esc((d.result.focos || []).join(', ').slice(0, 40) || '—') + '</b><span>foco</span></div>' +
              '<div class="bcp-stat"><b style="color:#E8EDFB;font-size:13px">' + esc(d.result.model || '') + '</b><span>modelo</span></div>' +
            '</div>' : '';
          el.innerHTML = simHTML +
            '<div style="border:1px solid rgba(122,158,255,.16);border-radius:14px;background:rgba(11,18,34,.55);' +
              'padding:18px 20px;font-size:14px;line-height:1.65;color:#E8EDFB;white-space:pre-wrap">' +
              esc(d.result.answer || '') + '</div>';
        }
      }).catch(function () {});
    }
  }

  // ── Canvas / lienzo (gráfico o tabla por IA) ──
  function stageCanvas(s, query) {
    s.innerHTML = backBar('Lienzo') +
      '<div class="bcp-inner bcp-canvaswrap">' +
        '<div class="bcp-canvasbar">' +
          '<input id="bcp-cv-q" class="" type="text" autocomplete="off" placeholder="Describe el gráfico o la tabla…  «top 10 por riesgo NRS»" ' +
            'style="flex:1;background:rgba(11,18,34,.8);border:1px solid rgba(122,158,255,.22);border-radius:12px;color:#E8EDFB;font-size:14px;padding:12px 15px;outline:none">' +
          '<button class="bcp-iconbtn" id="bcp-cv-go" style="width:auto;padding:0 16px">✦ Generar</button>' +
        '</div>' +
        '<div id="bcp-cv-cards"></div>' +
      '</div>';
    var q = s.querySelector('#bcp-cv-q');
    function go() { var v = (q.value || '').trim(); if (v) cockpitCanvas(v); }
    s.querySelector('#bcp-cv-go').addEventListener('click', go);
    q.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); go(); } });
    if (query) { q.value = query; cockpitCanvas(query); } else { q.focus(); }
  }

  async function cockpitCanvas(query) {
    var cards = document.getElementById('bcp-cv-cards');
    if (!cards) return;
    var cardId = 'bcpcv-' + (query.length + query.charCodeAt(0) + cards.children.length);
    cards.insertAdjacentHTML('afterbegin',
      '<div id="' + cardId + '" class="cv-card"><div class="cv-card-hdr"><div><div class="cv-card-title">' + esc(query) +
      '</div><div class="cv-card-sub">Generando…</div></div></div>' +
      '<div style="height:180px;display:flex;align-items:center;justify-content:center"><div class="cv-spinner"></div></div></div>');
    // 1º: generador LOCAL determinista (0 ms, 0 errores) — la IA solo para lo exótico
    var local = window.KhipuLocalCharts && window.KhipuLocalCharts.try(query);
    if (local && window._cvRenderCard) { window._cvRenderCard(cardId, query, local, 'local ⚡ instantáneo'); return; }
    try {
      var nodeCtx = (window.NODES || []).slice(0, 600).map(function (n) {
        var o = { id: n.id, label: n.label, cat: n.cat };
        if (n.mkt) o.mkt = n.mkt; if (n.margin != null) o.margin = n.margin; if (n.growth != null) o.growth = n.growth;
        if (n.country) o.country = n.country;
        if (typeof computeNRS === 'function') { var sc = computeNRS(n.id); if (sc != null) o.nrs = sc; }
        return o;
      });
      var quotesCtx = {};
      var mq = (window.MKT || {}).quotes || {};
      Object.keys(mq).forEach(function (t) { if (mq[t]) quotesCtx[t] = { close: mq[t].close, prev: mq[t].prev }; });
      var live = null;
      if (window.canvasEnrichData) { try { var en = await window.canvasEnrichData(query); live = (en && en.live) || null; } catch (e) {} }
      var r = await fetch('/api/canvas/generate', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query, context: { nodes: nodeCtx, quotes: quotesCtx, live: live } })
      });
      var ct = r.headers.get('content-type') || '';
      if (ct.indexOf('application/json') < 0) throw new Error('El servidor está ocupado. Reintenta en ~1 min.');
      var d = await r.json();
      if (d.error) throw new Error(d.error);
      if (window._cvRenderCard) window._cvRenderCard(cardId, query, d.spec, d.model);
    } catch (e) {
      var card = document.getElementById(cardId);
      if (card) card.innerHTML = '<div class="cv-card-hdr"><div class="cv-card-title">' + esc(query) + '</div></div>' +
        '<div style="padding:20px;text-align:center;color:#f87171;font-size:13px">⚠ ' + esc(e.message) + '</div>';
    }
  }

  // ══ ENRUTADOR de lo que pides (texto) ══
  function ask(text) {
    text = (text || '').trim(); if (!text) return;
    ensureShell();

    // 1) ¿es un comando KHIPU? (rápido, sin IA)
    if (window.KHIPU && window.KHIPU.tryParse) {
      try {
        var act = window.KHIPU.tryParse(text);
        if (act && dispatchAction(act)) return;
      } catch (e) {}
    }

    var low = text.toLowerCase();

    // 2) lienzo en blanco / gráfico
    if (/^(l[ií]enzo|canvas)\b/.test(low) || /lienzo en blanco/.test(low)) { stage('canvas'); return; }
    if (/^(gr[aá]fico|gr[aá]fica|graf|chart|dibuja|tabla|visualiza)\b[:\s]/.test(low) || low.indexOf('gráfico:') >= 0) {
      stage('canvas', text.replace(/^(gr[aá]fico|gr[aá]fica|graf|chart|dibuja|tabla|visualiza)\s*:?\s*/i, '')); return;
    }

    // 2.5) investigación profunda (Capa 4): planear→reunir→simular→sintetizar
    if (/investiga|a fondo|an[aá]lisis profundo|profundiza|\bdeep\b|tesis (de|sobre)/.test(low)) {
      stage('deep', text); return;
    }

    // 2.55) dossier financiero (ingresos, dilución, FCF, márgenes, ROE…)
    var dosM = low.match(/(?:dossier|fundamentales|financieros)\s+(?:de\s+)?(.+)/);
    if (dosM && window.openFinCard) {
      var dn = resolveNode(dosM[1].replace(/\?+$/, '').trim());
      if (dn) { window.openFinCard(dn.mkt || dn.id); return; }
    }

    // 2.6) el grafo o la terminal, DENTRO de la pantalla de Bixby
    if (/^(mu[eé]strame |ver |abre |abrir )?(el )?(grafo|mapa)\b/.test(low)) { stage('graph'); return; }
    var termM = low.match(/^(mu[eé]strame |ver |abre |abrir )?(la )?terminal(?:\s+(?:de|con)\s+(.+))?/);
    if (termM) {
      var tn = termM[3] ? resolveNode(termM[3].replace(/\?+$/, '').trim()) : null;
      stage('terminal', tn ? { ticker: tn.mkt || tn.id } : {}); return;
    }

    // 3) oportunidades / insights
    if (/oportunidad|insight|d[oó]nde inv|qu[eé] compr/.test(low)) { stage('insights'); return; }

    // 4) comparar A y B
    var cmp = low.match(/compar[ao]?r?\s+(.+?)\s+(?:y|vs|versus|con|contra)\s+(.+)/);
    if (cmp) { stage('compare', { a: cmp[1], b: cmp[2] }); return; }

    // 5) simular / caída
    var sim = low.match(/(?:qu[eé] pasa si cae|si cae|cae|colaps|corte de|corta[nr]?|sanci[oó]n(?:a[nr]?)?|prohib|auge de|boom de|demanda de|simula[nr]?|shock)\s+(.+)/);
    if (sim) {
      var kind = /auge|boom|demanda/.test(low) ? 'demand' : /sanci|prohib/.test(low) ? 'sanction' : /precio/.test(low) ? 'price' : 'collapse';
      var target = sim[1].replace(/\?+$/, '').trim();
      var nn = resolveNode(target);
      if (nn) { stage('sim', { id: nn.id, kind: kind }); return; }
    }

    // 6) desármame / radiografía / x-ray / analiza  → X-Ray
    var xr = low.match(/(?:des[aá]rma(?:me)?|radiograf[ií]a|x-?ray|destripa(?:me)?|anal[ií]za|abre|mu[eé]strame)\s+(?:la\s+empresa\s+|a\s+)?(.+)/);
    if (xr) { var nx = resolveNode(xr[1].replace(/\?+$/, '').trim()); if (nx) { stage('xray', nx.id); return; } }

    // 7) ¿el texto ES una empresa? → X-Ray directo
    var nDirect = resolveNode(text);
    if (nDirect && text.length <= 40) { stage('xray', nDirect.id); return; }

    // 8) fallback: intentar dibujarlo como datos
    stage('canvas', text);
  }

  // convierte una acción del parser KHIPU en escena
  function dispatchAction(act) {
    if (!act || !act.type) return false;
    if (act.type === 'xray' && act.arg) { stage('xray', act.arg); return true; }
    if (act.type === 'compare' && act.arg) { stage('compare', { a: act.arg.a, b: act.arg.b }); return true; }
    if (act.type === 'insights') { stage('insights'); return true; }
    if (act.type === 'livesim' && act.arg) { stage('sim', { id: act.arg.id || act.arg, kind: act.arg.kind || 'collapse' }); return true; }
    return false;
  }

  // "ver en el mapa" desde una simulación del escenario
  window._cockpitMapSim = function (id, kind) {
    close();
    var n = resolveNode(id); if (!n) return;
    var dir = kind === 'demand' ? 'up' : 'down';
    try {
      var shock = {}; shock[n.id] = (kind === 'demand') ? { salud: 100 } : { salud: 0 };
      var r = window.KhipuState.simulate(shock, [], 8, 0.6, false, { direction: dir, kind: kind });
      if (typeof switchTab === 'function') switchTab('map');
      if (typeof jumpTo === 'function') jumpTo(n.id);
      if (window._liveRecolorByImpact) window._liveRecolorByImpact(r.impact, dir);
    } catch (e) {}
  };

  // ══ abrir / cerrar ══
  function openCockpit(initial) {
    ensureShell();
    var ov = document.getElementById('bcp-ov');
    ov.classList.add('show');
    open = true;
    if (window.registerBixbyOrb) window.registerBixbyOrb('bcp-orb-canvas', 64);
    if (initial && initial.kind) stage(initial.kind, initial.arg);
    else if (!document.getElementById('bcp-stage').children.length) stage('empty');
    setTimeout(function () { var i = document.getElementById('bcp-input'); if (i) i.focus(); }, 60);
  }
  function close() {
    restoreAdopted();   // devolver grafo/terminal a su sitio original
    var ov = document.getElementById('bcp-ov');
    if (ov) ov.classList.remove('show');
    open = false;
    var btn = document.getElementById('bcp-mic');
    if (btn && btn.classList.contains('on') && window.BixbyVoice && window.BixbyVoice.stop) { window.BixbyVoice.stop(); btn.classList.remove('on'); }
  }

  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && open) close(); });

  window.BixbyCockpit = {
    open: openCockpit,
    close: close,
    isOpen: function () { return open; },
    stage: stage,
    ask: ask,
    setState: setState,
  };
})();
