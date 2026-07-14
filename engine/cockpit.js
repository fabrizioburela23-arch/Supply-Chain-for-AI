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

  // idioma para los textos de la Cabina (regla bilingüe)
  function ckLang() {
    try { return (window.LANG || localStorage.getItem('eco_lang') || 'es'); } catch (e) { return 'es'; }
  }
  function L(es, en) { return ckLang() === 'en' ? en : es; }

  // Extrae empresas SEMILLA mencionadas en un texto de escenario (para la
  // simulación por agentes): busca labels/tickers de NODES dentro del texto.
  function extractSeeds(text) {
    var out = [], seen = {};
    var norm = (window.KhipuResolve && window.KhipuResolve.norm)
      ? window.KhipuResolve.norm
      : function (x) { return String(x == null ? '' : x).toLowerCase(); };
    var nt = ' ' + norm(text) + ' ';
    (window.NODES || []).forEach(function (n) {
      if (out.length >= 8 || seen[n.id]) return;
      var lab = norm(n.label || '');
      if (lab && lab.length >= 3 && nt.indexOf(lab) >= 0) { seen[n.id] = 1; out.push(n.id); return; }
      if (n.mkt) {
        var tk = String(n.mkt).toLowerCase();
        if (tk.length >= 2 && nt.indexOf(' ' + tk + ' ') >= 0) { seen[n.id] = 1; out.push(n.id); }
      }
    });
    return out;
  }

  // ── textos bilingües del stage BRÓKER (Etapa M) ──
  var TRB = {
    broker:      { es: 'Bróker', en: 'Broker' },
    account:     { es: 'Cuenta', en: 'Account' },
    paperBadge:  { es: '🧪 SIMULADO (papel)', en: '🧪 SIMULATED (paper)' },
    realBadge:   { es: '🔴 DINERO REAL', en: '🔴 REAL MONEY' },
    equity:      { es: 'Valor total', en: 'Equity' },
    cash:        { es: 'Efectivo', en: 'Cash' },
    buyingPower: { es: 'Poder de compra', en: 'Buying power' },
    positions:   { es: 'Posiciones', en: 'Positions' },
    noPositions: { es: 'Sin posiciones abiertas', en: 'No open positions' },
    orders:      { es: 'Últimas órdenes', en: 'Recent orders' },
    noOrders:    { es: 'Sin órdenes recientes', en: 'No recent orders' },
    refresh:     { es: '↻ Actualizar', en: '↻ Refresh' },
    confirmTitle:{ es: 'Confirmar orden', en: 'Confirm order' },
    confirm:     { es: '✓ Confirmar', en: '✓ Confirm' },
    cancel:      { es: '✕ Cancelar', en: '✕ Cancel' },
    buy:         { es: 'COMPRAR', en: 'BUY' },
    sell:        { es: 'VENDER', en: 'SELL' },
    units:       { es: 'unidades', en: 'units' },
    sending:     { es: 'Enviando orden…', en: 'Sending order…' },
    sent:        { es: '✓ Orden enviada', en: '✓ Order sent' },
    dedup:       { es: '(ya se había enviado — no se duplicó)', en: '(already sent — not duplicated)' },
    canceled:    { es: 'Orden cancelada — no se envió nada.', en: 'Order canceled — nothing was sent.' },
    loading:     { es: 'Cargando cuenta del bróker…', en: 'Loading broker account…' },
    connectErr:  { es: 'No pude conectar con el bróker.', en: 'Could not reach the broker.' },
    amountRange: { es: 'El monto debe estar entre $1 y $100,000 por orden.', en: 'The amount must be between $1 and $100,000 per order.' },
    marketOrder: { es: 'Orden de mercado — se ejecuta al precio actual.', en: 'Market order — executes at the current price.' },
    resolving:   { es: 'Preparando la orden…', en: 'Preparing the order…' },
  };
  function tb(k) { var e = TRB[k]; if (!e) return k; return ckLang() === 'en' ? e.en : e.es; }

  // resuelve empresa desde id/ticker/nombre — resolutor robusto compartido
  // (engine/resolve.js: alias de voz, sin acentos, fuzzy); búsqueda débil de fallback
  function resolveNode(q) {
    if (window.KhipuResolve) { var r = window.KhipuResolve.find(q); if (r && r.node) return r.node; }
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
/* barra de chat de Bixby: AHORA ABAJO (pedido de Fabrizio: "ponla abajo") */
#bcp-barwrap{flex-shrink:0;padding:12px 22px 16px;border-top:1px solid rgba(122,158,255,.12);
  display:flex;justify-content:center;background:linear-gradient(0deg,rgba(5,7,14,.6),transparent)}
#bcp-bar{display:flex;align-items:center;gap:9px;width:100%;max-width:900px}
#bcp-input{flex:1;background:rgba(11,18,34,.8);border:1px solid rgba(122,158,255,.22);border-radius:12px;
  color:#E8EDFB;font-size:14px;padding:12px 15px;outline:none;font-family:inherit;transition:border-color .15s,box-shadow .15s}
#bcp-input:focus{border-color:rgba(0,224,255,.55);box-shadow:0 0 0 3px rgba(0,224,255,.1)}
#bcp-input::placeholder{color:#5b6580}
.bcp-iconbtn{width:44px;height:44px;flex-shrink:0;border-radius:12px;border:1px solid rgba(122,158,255,.22);
  background:rgba(11,18,34,.8);color:#E8EDFB;cursor:pointer;font-size:17px;display:flex;align-items:center;justify-content:center;
  transition:all .14s}
.bcp-iconbtn:hover{border-color:rgba(0,224,255,.5);color:#00E0FF}
#bcp-mic.on{background:rgba(214,59,59,.85);border-color:#d63b3b;color:#fff;box-shadow:0 0 18px rgba(214,59,59,.45);animation:bcpPulse 1.1s ease-in-out infinite}
#bcp-close{margin-left:auto}
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
/* simulación por agentes (MiroFish) — impactos por empresa con motivo */
.bcp-agrow{border-bottom:1px solid rgba(122,158,255,.08);padding:9px 0;cursor:pointer}
.bcp-agrow:hover .nm{color:#00E0FF}
.bcp-agrow-top{display:flex;align-items:center;gap:9px}
.bcp-agrow .nm{flex:1;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bcp-agrow .bar{width:120px;height:6px;border-radius:3px;overflow:hidden;flex:none}
.bcp-agrow .bar i{display:block;height:100%}
.bcp-agrow .pv{font-family:'JetBrains Mono',monospace;font-size:12px;width:52px;text-align:right;flex:none}
.bcp-agwhy{font-size:11.5px;color:#8b95b0;margin-top:4px;line-height:1.45}
.bcp-agent{border:1px solid rgba(122,158,255,.18);border-radius:12px;padding:8px 12px;min-width:0;max-width:260px}
.bcp-agent .an{font-size:12.5px;font-weight:700;color:#E8EDFB;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bcp-agent .at{font-size:10px;text-transform:uppercase;letter-spacing:.08em}
.bcp-agent .as{font-size:11.5px;color:#9BA6C4;margin-top:3px;line-height:1.4}
/* investigación profunda estructurada (sector · competidores · geopolítica · tesis) */
.bcp-rs-sec{margin-bottom:16px}
.bcp-rs-txt{font-size:13.5px;line-height:1.6;color:#D5DCF0}
.bcp-rs-list{margin:6px 0 0;padding-left:18px;font-size:13px;line-height:1.6;color:#C6CEE6}
.bcp-rs-list li{margin-bottom:4px}
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
    var en0 = ckLang() === 'en';
    ov.innerHTML =
      '<div id="bcp-top">' +
        '<div id="bcp-orb-wrap"><canvas id="bcp-orb-canvas" width="64" height="64"></canvas></div>' +
        '<div id="bcp-idwrap"><div id="bcp-word">BIXBY</div>' +
          '<div id="bcp-state"><span class="dot"></span><span class="txt">' + (en0 ? 'Ready' : 'Listo') + '</span></div></div>' +
        '<button class="bcp-iconbtn" id="bcp-close" title="' + (en0 ? 'Close (Esc)' : 'Cerrar (Esc)') + '">✕</button>' +
      '</div>' +
      // Barra de BOTONES (pedido de Fabrizio): todo lo que Bixby puede
      // mostrar, a un clic — el grafo y la terminal viven DENTRO del escenario.
      '<div id="bcp-actions">' +
        '<button class="bcp-act" data-act="graph">🗺️ ' + (en0 ? 'Graph' : 'Grafo') + '</button>' +
        '<button class="bcp-act" data-act="terminal">🖥️ ' + (en0 ? 'Terminal' : 'Terminal') + '</button>' +
        '<button class="bcp-act" data-act="xray">🔬 X-Ray</button>' +
        '<button class="bcp-act" data-act="sim">◉ ' + (en0 ? 'Simulate' : 'Simular') + '</button>' +
        '<button class="bcp-act" data-act="compare">⇄ ' + (en0 ? 'Compare' : 'Comparar') + '</button>' +
        '<button class="bcp-act" data-act="insights">💡 ' + (en0 ? 'Opportunities' : 'Oportunidades') + '</button>' +
        '<button class="bcp-act" data-act="deep">🧠 ' + (en0 ? 'Research' : 'Investigar') + '</button>' +
        '<button class="bcp-act" data-act="canvas">✦ ' + (en0 ? 'Chart' : 'Gráfico') + '</button>' +
        '<button class="bcp-act" data-act="broker">💼 ' + tb('broker') + '</button>' +
        '<button class="bcp-act" data-act="crypto">💠 ' + (en0 ? 'Crypto' : 'Cripto') + '</button>' +
      '</div>' +
      // Pulso proactivo del portafolio (pedido de Fabrizio: que Bixby "mande" el
      // informe). Oculto por defecto; se llena al abrir SOLO si el PIN ya está
      // en caché (no molesta a quien no usa el bróker). Clic → informe completo.
      '<div id="bcp-pulse" style="display:none"></div>' +
      '<div id="bcp-stage"></div>' +
      // Barra de chat ABAJO (Fabrizio: "pon la barra de chat de Bixby abajo").
      '<div id="bcp-barwrap"><div id="bcp-bar">' +
        '<input id="bcp-input" type="text" autocomplete="off" spellcheck="false" ' +
          'placeholder="' + (en0
            ? 'Ask Bixby anything…  “break down Nvidia”  ·  “what if TSMC falls?”'
            : 'Pídele algo a Bixby…  «desármame Nvidia»  ·  «¿qué pasa si cae TSMC?»') + '">' +
        '<button class="bcp-iconbtn" id="bcp-send" title="' + (en0 ? 'Send' : 'Enviar') + '">➤</button>' +
        '<button class="bcp-iconbtn" id="bcp-mic" title="' + (en0 ? 'Talk to Bixby' : 'Hablar con Bixby') + '">🎙</button>' +
      '</div></div>';
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
        if (act === 'broker') return stage('broker');
        if (act === 'crypto') return stage('crypto');
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

    mountCockpitOrb();
    return ov;
  }

  // ── Orbe de voz de Bixby (engine/orb.js) dentro de la Cabina ──
  // Reemplaza el orbe estático del header: respira en reposo y reacciona a la
  // voz (cian = usuario, violeta = Bixby). voice.js lo alimenta con setUserLevel
  // / setBixbyLevel. Si orb.js no cargó, cae al orbe pequeño (registerBixbyOrb).
  function mountCockpitOrb() {
    var wrap = document.getElementById('bcp-orb-wrap');
    if (!wrap) return;
    if (window.BixbyOrb && window.BixbyOrb.mount) {
      try {
        var old = document.getElementById('bcp-orb-canvas');
        if (old) old.style.display = 'none';
        window.BixbyOrb.mount(wrap);
        window.BixbyOrb.start();
        return;
      } catch (e) { /* cae al fallback */ }
    }
    if (window.registerBixbyOrb) window.registerBixbyOrb('bcp-orb-canvas', 64);
  }
  function stopCockpitOrb() {
    if (window.BixbyOrb && window.BixbyOrb.stop) { try { window.BixbyOrb.stop(); } catch (e) {} }
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
    markActive(['graph', 'terminal', 'insights', 'canvas', 'deep', 'broker', 'crypto'].indexOf(kind) >= 0 ? kind : null);
    if (kind === 'broker') return stageBroker(s, arg);
    if (kind === 'crypto') return stageCrypto(s, arg);
    if (kind === 'xray') return stageXRay(s, arg);
    if (kind === 'compare') return stageCompare(s, arg);
    if (kind === 'agentsim') return stageAgentSim(s, arg);
    if (kind === 'research') return stageResearch(s, arg);
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

  // ── CRIPTO, dentro de la Cabina. Arregla el bug (pedir cripto por voz cerraba
  //    la Cabina y callaba a Bixby) y cumple la visión: TODO vive en Bixby. Adopta
  //    #crypto-panel igual que el grafo/terminal (mismo panel vivo, se devuelve al
  //    salir). ──
  function stageCrypto(s, arg) {
    var en = ckLang() === 'en';
    s.innerHTML = backBar(en ? 'Crypto' : 'Cripto') + '<div class="bcp-embed" id="bcp-embed-crypto" style="overflow:auto"></div>';
    var pane = document.getElementById('crypto-panel');
    if (!pane || !adoptInto(s.querySelector('#bcp-embed-crypto'), pane, 'block')) {
      s.innerHTML += '<div class="bcp-loading">' + (en ? 'Could not mount crypto' : 'No se pudo montar cripto') + '</div>';
      return;
    }
    try { pane.style.minHeight = '100%'; } catch (e) {}
    try { if (window.KhipuCrypto) window.KhipuCrypto.init(true); } catch (e) {}
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
    return '<div class="bcp-stagehd"><span class="bcp-back" onclick="window.BixbyCockpit.stage(\'empty\')">← ' + (ckLang() === 'en' ? 'Home' : 'Inicio') + '</span>' +
      (label ? '<span style="color:#7C87A3;font-size:12px">' + esc(label) + '</span>' : '') + '</div>';
  }

  function stageEmpty(s) {
    var en = ckLang() === 'en';
    var chips = en ? [
      ['break down ', 'Nvidia', 'Full X-Ray'],
      ['simulate that ', 'China bans HBM exports', 'Agent simulation'],
      ['what if ', 'TSMC falls', 'Shock on the map'],
      ['compare ', 'Nvidia and AMD', 'Two companies'],
      ['show me ', 'opportunities', 'Where to invest'],
      ['research ', 'Nvidia', 'Deep research'],
      ['chart: ', 'margins of NVIDIA, TSMC and ASML', 'Data canvas'],
      ['', 'my account', tb('broker')],
      ['', 'blank canvas', 'Start from scratch'],
    ] : [
      ['desármame ', 'Nvidia', 'Radiografía completa'],
      ['simula que ', 'China prohíbe exportar HBM', 'Sim por agentes'],
      ['¿qué pasa si cae ', 'TSMC?', 'Shock en el mapa'],
      ['compara ', 'Nvidia y AMD', 'Dos empresas'],
      ['muéstrame ', 'oportunidades', 'Dónde invertir'],
      ['investiga ', 'Nvidia', 'Investigación profunda'],
      ['gráfico: ', 'márgenes de NVIDIA, TSMC y ASML', 'Lienzo de datos'],
      ['', 'mi cuenta', tb('broker')],
      ['', 'lienzo en blanco', 'Empezar de cero'],
    ];
    var h2 = en ? "I'm Bixby. Ask me anything." : 'Soy Bixby. Pregúntame lo que sea.';
    var pp = en
      ? 'I can break down any company, simulate what happens if something falls, compare, and chart your data.'
      : 'Puedo desarmar cualquier empresa, simular qué pasa si algo cae, comparar, y dibujarte los datos.';
    s.innerHTML = '<div id="bcp-empty"><h2>' + esc(h2) + '</h2>' +
      '<p>' + esc(pp) + '</p>' +
      '<div class="bcp-chips">' + chips.map(function (c) {
        return '<span class="bcp-chip" data-q="' + esc(c[0] + c[1]) + '"><span class="k">' + esc(c[2]) + '</span>' + esc(c[0] + c[1]) + '</span>';
      }).join('') + '</div></div>';
    s.querySelectorAll('.bcp-chip').forEach(function (el) {
      el.addEventListener('click', function () { ask(el.getAttribute('data-q')); });
    });
  }

  // ── "no encontré esa empresa": mensaje bilingüe + sugerencias clicables ──
  function stageNotFound(s, query) {
    var nf = window.KhipuResolve ? window.KhipuResolve.notFound(query) : null;
    var en = ckLang() === 'en';
    var title = en ? ('I couldn\'t find "' + query + '"') : ('No encontré «' + query + '»');
    var sugg = (nf && nf.suggestions) || [];
    s.innerHTML = backBar(en ? 'Not found' : 'No encontrada') +
      '<div id="bcp-empty"><h2>' + esc(title) + '</h2>' +
      '<p>' + (sugg.length ? (en ? 'Did you mean one of these?' : '¿Quisiste decir alguna de estas?')
        : (en ? 'Try the ticker (e.g. NVDA) or the full name.' : 'Prueba con el ticker (ej. NVDA) o el nombre completo.')) + '</p>' +
      (sugg.length ? '<div class="bcp-chips">' + sugg.map(function (n) {
        return '<span class="bcp-chip" data-id="' + esc(n.id) + '"><span class="k">' + esc(n.mkt || n.id) + '</span>' + esc(n.label) + '</span>';
      }).join('') + '</div>' : '') + '</div>';
    s.querySelectorAll('.bcp-chip').forEach(function (el) {
      el.addEventListener('click', function () { stage('xray', el.getAttribute('data-id')); });
    });
  }

  function stageXRay(s, id) {
    var n = resolveNode(id); if (!n) { stageNotFound(s, id); return; }
    if (!window.buildXRayHTML) { s.innerHTML = '<div class="bcp-loading">X-Ray no disponible</div>'; return; }
    s.innerHTML = backBar('Radiografía') +
      '<div class="bcp-inner"><div id="bcp-xray" class="xray-scope xr-full">' + window.buildXRayHTML(n.id, { full: true }) + '</div></div>';
    var root = s.querySelector('#bcp-xray');
    if (window.wireXRay) window.wireXRay(root, n.id);
  }

  /* ══ COMPARAR FUNDAMENTALES (dossier lado a lado) — pedido de Fabrizio: "el
     dossier es súper importante". Trae /api/findossier de ambas y alinea las
     cifras clave del último año; resalta en verde quién gana cada fila. ══ */
  function _latest(arr) { if (!Array.isArray(arr)) return null; for (var i = arr.length - 1; i >= 0; i--) { if (arr[i] != null) return arr[i]; } return null; }
  var FUND_ROWS = [
    { key: 'revenue', es: 'Ingresos (últ. año)', en: 'Revenue (latest)', kind: 'usd', better: 'high' },
    { key: 'revenue_growth', es: 'Crecimiento de ingresos', en: 'Revenue growth', kind: 'growth', better: 'high' },
    { key: 'gross_margin', es: 'Margen bruto', en: 'Gross margin', kind: 'pct', better: 'high' },
    { key: 'fcf_margin', es: 'Margen de flujo libre', en: 'FCF margin', kind: 'pct', better: 'high' },
    { key: 'fcf_growth', es: 'Crecimiento del flujo libre', en: 'FCF growth', kind: 'growth', better: 'high' },
    { key: 'roe', es: 'Retorno sobre capital (ROE)', en: 'Return on equity', kind: 'pct', better: 'high' },
    { key: 'de_ratio', es: 'Deuda / Capital', en: 'Debt / Equity', kind: 'ratio', better: 'low' },
    { key: 'ev_to_sales', es: 'Valuación EV / Ventas', en: 'EV / Sales', kind: 'ratiox', better: 'low' },
    { key: 'dilution', es: 'Dilución anual', en: 'Annual dilution', kind: 'growth', better: 'low' },
  ];
  function _fundVal(kind, v) {
    if (v == null) return '—';
    if (kind === 'usd') { var a = Math.abs(v); return (v < 0 ? '-' : '') + (a >= 1e9 ? '$' + (a / 1e9).toFixed(1) + 'B' : a >= 1e6 ? '$' + (a / 1e6).toFixed(0) + 'M' : '$' + Math.round(a)); }
    if (kind === 'growth') return (v >= 0 ? '+' : '') + (+v).toFixed(1) + '%';
    if (kind === 'pct') return (+v).toFixed(1) + '%';
    if (kind === 'ratiox') return (+v).toFixed(1) + 'x';
    return (+v).toFixed(2);
  }
  function buildFundTable(da, db, aLabel, bLabel, en) {
    var rows = FUND_ROWS.map(function (r) {
      var va = _latest(da[r.key]), vb = _latest(db[r.key]), win = 0;
      if (va != null && vb != null && va !== vb) win = (r.better === 'high') ? (va > vb ? 1 : 2) : (va < vb ? 1 : 2);
      var cell = function (v, isWin) {
        return '<td style="padding:8px 12px;text-align:right;font-family:\'JetBrains Mono\',monospace;font-size:13px;' +
          (isWin ? 'color:' + UP + ';font-weight:750;background:' + UP + '14' : 'color:#C3CBE0') + '">' + _fundVal(r.kind, v) + '</td>';
      };
      return '<tr style="border-top:1px solid rgba(255,255,255,.06)">' +
        '<td style="padding:8px 12px;font-size:12.5px;color:#8791AC">' + (en ? r.en : r.es) + '</td>' +
        cell(va, win === 1) + cell(vb, win === 2) + '</tr>';
    }).join('');
    return '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;min-width:420px">' +
      '<thead><tr>' +
        '<th style="text-align:left;padding:8px 12px;font-size:11px;color:#5b6580;text-transform:uppercase;letter-spacing:.06em">' + (en ? 'Metric' : 'Métrica') + '</th>' +
        '<th style="text-align:right;padding:8px 12px;font-size:13px;color:#00E0FF">' + esc(aLabel) + '</th>' +
        '<th style="text-align:right;padding:8px 12px;font-size:13px;color:#8E5AFF">' + esc(bLabel) + '</th>' +
      '</tr></thead><tbody>' + rows + '</tbody></table></div>';
  }
  function stageCompareFund(aNode, bNode) {
    var en = ckLang() === 'en';
    var box = document.getElementById('bcp-cmp-fund');
    if (!box) return;
    var ta = aNode.mkt, tb2 = bNode.mkt;
    if (!ta || !tb2) { box.innerHTML = '<div style="color:#FFB300;padding:14px;font-size:13px">' + (en ? 'One of these is private (no public fundamentals).' : 'Una de estas es privada (sin fundamentales públicos).') + '</div>'; return; }
    box.innerHTML = '<div class="bcp-loading">' + (en ? 'Loading fundamentals…' : 'Cargando fundamentales…') + '</div>';
    Promise.all([
      fetch((window.BASE || '') + '/api/findossier/' + encodeURIComponent(ta)).then(function (r) { return r.json(); }).catch(function () { return { available: false }; }),
      fetch((window.BASE || '') + '/api/findossier/' + encodeURIComponent(tb2)).then(function (r) { return r.json(); }).catch(function () { return { available: false }; }),
    ]).then(function (res) {
      box = document.getElementById('bcp-cmp-fund'); if (!box) return;
      var da = res[0] || {}, db = res[1] || {};
      if (!da.available && !db.available) { box.innerHTML = '<div style="color:#FFB300;padding:14px;font-size:13px">' + (en ? 'No fundamentals available for these two.' : 'Sin fundamentales disponibles para estas dos.') + '</div>'; return; }
      box.innerHTML = buildFundTable(da.available ? da : {}, db.available ? db : {}, aNode.label, bNode.label, en) +
        '<div style="margin-top:10px;font-size:10.5px;color:#5b6580">' + (en ? 'Latest available fiscal year · source FMP/Alpha Vantage · green = better in that row · not financial advice.' : 'Último año fiscal disponible · fuente FMP/Alpha Vantage · verde = mejor en esa fila · no es asesoría financiera.') + '</div>';
    });
  }

  function stageCompare(s, arg) {
    arg = arg || {};
    var en = ckLang() === 'en';
    var a = resolveNode(arg.a), b = arg.b ? resolveNode(arg.b) : null;
    if (!a) { stageNotFound(s, arg.a || ''); return; }
    if (arg.b && !b) { stageNotFound(s, arg.b); return; }
    if (!b) b = pickRival(a);   // si solo dieron una, comparamos vs su rival natural
    if (!b) { stageXRay(s, a.id); return; }
    var tabBtn = function (mode, on, label) {
      return '<button class="bcp-back cmp-tab" data-cmp="' + mode + '" style="' +
        (on ? 'border-color:#00E0FF;color:#00E0FF' : '') + '">' + label + '</button>';
    };
    s.innerHTML = backBar('Comparar') +
      '<div class="bcp-inner">' +
        '<div style="display:flex;gap:8px;margin-bottom:14px">' +
          tabBtn('profile', true, '🔬 ' + (en ? 'Profile' : 'Perfil')) +
          tabBtn('fund', false, '📊 ' + (en ? 'Fundamentals' : 'Fundamentales')) +
        '</div>' +
        '<div id="bcp-cmp-profile"><div class="bcp-cmp">' +
          '<div class="xray-scope" id="bcp-cmpA">' + window.buildXRayHTML(a.id, { full: false }) + '</div>' +
          '<div class="xray-scope" id="bcp-cmpB">' + window.buildXRayHTML(b.id, { full: false }) + '</div>' +
        '</div></div>' +
        '<div id="bcp-cmp-fund" style="display:none"></div>' +
      '</div>';
    if (window.wireXRay) { window.wireXRay(s.querySelector('#bcp-cmpA'), a.id); window.wireXRay(s.querySelector('#bcp-cmpB'), b.id); }
    var loadedFund = false;
    s.querySelectorAll('.cmp-tab').forEach(function (btn) {
      btn.addEventListener('click', function () {
        s.querySelectorAll('.cmp-tab').forEach(function (x) { x.style.borderColor = ''; x.style.color = ''; });
        btn.style.borderColor = '#00E0FF'; btn.style.color = '#00E0FF';
        var mode = btn.getAttribute('data-cmp');
        var pf = document.getElementById('bcp-cmp-profile'), fd = document.getElementById('bcp-cmp-fund');
        if (mode === 'fund') { if (pf) pf.style.display = 'none'; if (fd) fd.style.display = 'block'; if (!loadedFund) { loadedFund = true; stageCompareFund(a, b); } }
        else { if (pf) pf.style.display = ''; if (fd) fd.style.display = 'none'; }
      });
    });
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
    var n = resolveNode(arg.id); if (!n) { stageNotFound(s, arg.id || ''); return; }
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

  /* ══ STAGE BRÓKER (Etapa M) — cuenta Alpaca + posiciones + órdenes +
     tarjeta de CONFIRMACIÓN de compra/venta. Reglas innegociables:
     badge 🧪 SIMULADO / 🔴 DINERO REAL siempre visible; NINGUNA orden se
     envía sin clic en Confirmar (o confirmación verbal vía voice.js).
     Reusa los helpers compartidos de voice.js: window._resolveTradeSymbol,
     window._tradeAccountInfo y window._executeTradeOrder — NO duplicar. ══ */
  var _bkAcct = null;         // última cuenta cargada (para el badge)
  var _pendingOrder = null;   // orden esperando el clic en Confirmar

  function badgeHTML(paper) {
    if (paper === true) return '<span style="font-size:10px;font-weight:800;letter-spacing:.08em;padding:3px 10px;border-radius:999px;background:rgba(255,179,0,.14);color:#FFB300;border:1px solid rgba(255,179,0,.4)">' + tb('paperBadge') + '</span>';
    if (paper === false) return '<span style="font-size:10px;font-weight:800;letter-spacing:.08em;padding:3px 10px;border-radius:999px;background:rgba(255,45,70,.16);color:#FF2D46;border:1px solid rgba(255,45,70,.55)">' + tb('realBadge') + '</span>';
    return '';
  }
  function paintConfirmBadge() {
    var el = document.getElementById('bcp-bk-cbadge');
    if (el && _bkAcct) el.innerHTML = badgeHTML(typeof _bkAcct.paper === 'boolean' ? _bkAcct.paper : null);
  }
  function fmtUsd(v) { return '$' + (Number(v) || 0).toLocaleString('en-US', { maximumFractionDigits: 2 }); }

  /* ══ INFORME DE PORTAFOLIO (pedido de Fabrizio: que Bixby "mande" informes de
     cómo va el portafolio). Rendimiento + mejor/peor + concentración por sector
     + comentario CAUTO de Bixby (Sonnet 5, sin órdenes de compra/venta). Todo
     sobre la cuenta de PAPEL. Reusa NODES/catLabel y los helpers de trade. ══ */
  function _sectorOf(p) {
    var en = ckLang() === 'en';
    var symbol = (p && p.symbol != null) ? p.symbol : p;   // acepta el objeto posición o un string
    var ac = (p && p.asset_class) || '';
    var sym = String(symbol || '').toUpperCase();
    if (!sym) return en ? 'Other' : 'Otro';
    // cripto: por asset_class de Alpaca, por par con barra ("BTC/USD"), o por sufijo
    // USD/USDT/USDC ("BTCUSD" — así lo devuelve /v2/positions, SIN barra → antes caía
    // a "Otro" y Bixby decía "~100% en Otro" en carteras cripto).
    if (ac === 'crypto' || sym.indexOf('/') >= 0 || /^[A-Z0-9]{2,10}(USD|USDT|USDC)$/.test(sym))
      return en ? 'Crypto' : 'Cripto';
    var n = (window.NODES || []).find(function (x) { return x.mkt && String(x.mkt).toUpperCase() === sym; });
    if (n) return (typeof window.catLabel === 'function') ? window.catLabel(n.cat) : (n.cat || (en ? 'Other' : 'Otro'));
    return en ? 'Other' : 'Otro';
  }

  function _computePortfolio(acct, positions) {
    positions = Array.isArray(positions) ? positions : [];
    var totalMV = 0, pnl = 0, cost = 0, best = null, worst = null, bySec = {};
    positions.forEach(function (p) {
      var mv = +p.market_val || 0, up = +p.unrealized || 0, cb = +p.cost_basis || 0, pct = +p.unrealized_pct || 0;
      totalMV += mv; pnl += up; cost += cb;
      if (!best || pct > (+best.unrealized_pct || 0)) best = p;
      if (!worst || pct < (+worst.unrealized_pct || 0)) worst = p;
      var sec = _sectorOf(p);
      bySec[sec] = (bySec[sec] || 0) + mv;
    });
    var denom = totalMV > 0 ? totalMV : 1;
    var sectors = Object.keys(bySec).map(function (k) { return { sector: k, mv: bySec[k], pct: bySec[k] / denom * 100 }; })
      .sort(function (a, b) { return b.mv - a.mv; });
    return {
      // |cost| en el denominador: una posición corta tiene cost_basis negativo;
      // con `cost > 0` daba 0.00% junto a un P&L en $ ≠ 0 (incoherente).
      totalMV: totalMV, pnl: pnl, pnlPct: Math.abs(cost) > 1e-9 ? (pnl / Math.abs(cost) * 100) : 0,
      best: best, worst: worst, sectors: sectors, n: positions.length,
      equity: (+(acct && acct.equity)) || totalMV,
      paper: (acct && typeof acct.paper === 'boolean') ? acct.paper : null,
    };
  }
  window._computePortfolioSummary = _computePortfolio;   // reuso desde voice.js (informe hablado)

  var SEC_COLORS = ['#00E0FF', '#8E5AFF', '#FFB300', '#22D3A6', '#FF6B9D', '#5B8DEF', '#7C87A3'];
  function renderPortfolioReport(acct, positions) {
    var box = document.getElementById('bcp-bk-report');
    if (!box) return;
    var en = ckLang() === 'en';
    var m = _computePortfolio(acct, positions);
    if (!m.n) { box.innerHTML = ''; return; }   // sin posiciones → sin informe
    var plCol = m.pnl >= 0 ? UP : DOWN, plSign = m.pnl >= 0 ? '+' : '';
    var bars = m.sectors.slice(0, 5).map(function (s, i) {
      var c = SEC_COLORS[i % SEC_COLORS.length];
      return '<div style="margin-bottom:7px">' +
        '<div style="display:flex;justify-content:space-between;font-size:11.5px;margin-bottom:3px">' +
          '<span style="color:#C3CBE0">' + esc(s.sector) + '</span>' +
          '<span style="color:#7C87A3;font-family:\'JetBrains Mono\',monospace">' + s.pct.toFixed(0) + '%</span></div>' +
        '<div style="height:7px;border-radius:5px;background:rgba(255,255,255,.06);overflow:hidden">' +
          '<div style="height:100%;width:' + Math.max(2, s.pct).toFixed(1) + '%;background:' + c + ';border-radius:5px"></div></div></div>';
    }).join('');
    var chip = function (p, label, col) {
      if (!p) return '';
      var pct = +p.unrealized_pct || 0;
      return '<div style="flex:1;min-width:120px;padding:9px 12px;border:1px solid ' + col + '33;border-radius:10px;background:' + col + '0c">' +
        '<div style="font-size:10.5px;color:#7C87A3;text-transform:uppercase;letter-spacing:.07em;margin-bottom:2px">' + label + '</div>' +
        '<div style="font-size:14px;font-weight:750;font-family:\'JetBrains Mono\',monospace">' + esc(p.symbol || '—') +
          ' <span style="color:' + col + '">' + (pct >= 0 ? '+' : '') + pct.toFixed(1) + '%</span></div></div>';
    };
    box.innerHTML =
      '<div style="margin-top:16px;padding:16px 18px;border:1px solid rgba(122,158,255,.18);border-radius:14px;background:rgba(12,18,32,.5)">' +
        '<div style="display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:14px">' +
          '<span style="font-size:14px;font-weight:750">📊 ' + (en ? 'Portfolio report' : 'Informe de portafolio') + '</span>' +
          '<span style="margin-left:auto;font-size:12px;color:#7C87A3">' + (en ? 'Total return' : 'Rendimiento total') + '</span>' +
          '<span style="font-size:20px;font-weight:800;color:' + plCol + ';font-family:\'JetBrains Mono\',monospace">' +
            plSign + m.pnlPct.toFixed(2) + '%</span>' +
          '<span style="font-size:13px;color:' + plCol + '">(' + plSign + fmtUsd(Math.abs(m.pnl)) + ')</span></div>' +
        (m.best || m.worst ? '<div style="display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap">' +
          chip(m.best, en ? 'Best' : 'Mejor', UP) + (m.best !== m.worst ? chip(m.worst, en ? 'Worst' : 'Peor', DOWN) : '') + '</div>' : '') +
        '<div style="font-size:11px;color:#7C87A3;text-transform:uppercase;letter-spacing:.07em;margin-bottom:8px">' +
          (en ? 'Concentration by sector' : 'Concentración por sector') + '</div>' + bars +
        '<div id="bcp-bk-aicomment" style="margin-top:14px;padding:12px 14px;border-radius:10px;background:rgba(0,224,255,.05);border:1px solid rgba(0,224,255,.16);font-size:12.5px;line-height:1.5;color:#C3CBE0">' +
          '<span style="color:#7C87A3">💬 ' + (en ? 'Bixby is looking at your portfolio…' : 'Bixby está mirando tu portafolio…') + '</span></div></div>';
    _fetchPortfolioComment(m);
  }

  async function _fetchPortfolioComment(m) {
    var el = document.getElementById('bcp-bk-aicomment');
    if (!el) return;
    var en = ckLang() === 'en';
    var payload = {
      lang: en ? 'en' : 'es', equity: Math.round(m.equity || m.totalMV || 0),
      pnl_pct: +m.pnlPct.toFixed(2), positions_count: m.n, paper: m.paper,
      sectors: m.sectors.slice(0, 5).map(function (s) { return { sector: s.sector, pct: +s.pct.toFixed(1) }; }),
      best: m.best ? { symbol: m.best.symbol, pnl_pct: +(+m.best.unrealized_pct || 0).toFixed(2) } : null,
      worst: m.worst ? { symbol: m.worst.symbol, pnl_pct: +(+m.worst.unrealized_pct || 0).toFixed(2) } : null,
    };
    try {
      var r = await fetch((window.BASE || '') + '/api/portfolio/comment', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      });
      var d = await r.json();
      el = document.getElementById('bcp-bk-aicomment');
      if (!el) return;
      el.innerHTML = (d && d.comment)
        ? '<span style="color:#00E0FF;font-weight:700">💬 Bixby:</span> ' + esc(d.comment)
        : '<span style="color:#7C87A3">💬 ' + (en ? 'No comment available.' : 'Sin comentario disponible.') + '</span>';
    } catch (e) {
      el = document.getElementById('bcp-bk-aicomment');
      if (el) el.innerHTML = '<span style="color:#7C87A3">💬 ' + (en ? "Could not load Bixby's comment." : 'No pude cargar el comentario de Bixby.') + '</span>';
    }
  }

  // Pulso proactivo: al abrir la Cabina, si el PIN ya está guardado, Bixby "manda"
  // un resumen de una línea (valor + rendimiento). Silencioso si no hay PIN — no
  // molesta a quien no usa el bróker ni dispara el prompt del PIN.
  async function _portfolioPulse() {
    var el = document.getElementById('bcp-pulse');
    if (!el) return;
    var hasPin = false;
    try { hasPin = !!localStorage.getItem('khipu_trade_pin'); } catch (e) {}
    if (!hasPin || !window._tradeFetch || !window._tradeAccountInfo) { el.style.display = 'none'; return; }
    var en = ckLang() === 'en';
    try {
      var acct = await window._tradeAccountInfo(false, false);   // NO interactivo: nunca pide el PIN
      if (!acct || acct.error) { el.style.display = 'none'; return; }
      var positions = [];
      try {
        var rp = await window._tradeFetch('/api/trade/positions/detail', {}, false);
        var dp = await rp.json();
        if (Array.isArray(dp)) positions = dp;
      } catch (e2) {}
      var m = _computePortfolio(acct, positions);
      var plCol = m.pnl >= 0 ? UP : DOWN, sign = m.pnl >= 0 ? '+' : '';
      var pf = (en ? 'Your paper portfolio' : 'Tu portafolio simulado') + ': ' + fmtUsd(m.equity);
      var line = m.n
        ? pf + ' · <span style="color:' + plCol + '">' + sign + m.pnlPct.toFixed(1) + '%</span> · ' +
          m.n + ' ' + (en ? (m.n === 1 ? 'position' : 'positions') : (m.n === 1 ? 'posición' : 'posiciones'))
        : pf + ' · ' + (en ? 'no open positions' : 'sin posiciones');
      el.innerHTML =
        '<div style="max-width:980px;margin:0 auto 4px;padding:8px 14px;display:flex;align-items:center;gap:10px;' +
          'border:1px solid rgba(0,224,255,.18);border-radius:12px;background:rgba(0,224,255,.05);cursor:pointer;font-size:12.5px" ' +
          'onclick="window.BixbyCockpit&&window.BixbyCockpit.stage(\'broker\')">' +
          '<span>💼</span><span style="color:#C3CBE0">' + line + '</span>' +
          '<span style="margin-left:auto;color:#00E0FF;font-weight:600;white-space:nowrap">' + (en ? 'See report →' : 'Ver informe →') + '</span></div>';
      el.style.display = 'block';
    } catch (e) { el.style.display = 'none'; }
  }

  function stageBroker(s, arg) {
    arg = arg || {};
    var en = ckLang() === 'en';
    s.innerHTML = backBar(tb('broker')) +
      '<div class="bcp-inner" style="max-width:980px">' +
        '<div id="bcp-bk-confirm"></div>' +
        '<div id="bcp-bk-acct"><div class="bcp-loading">' + tb('loading') + '</div></div>' +
        '<div id="bcp-bk-report"></div>' +
        '<div class="bcp-two" style="margin-top:18px">' +
          '<div><div class="bcp-lh">' + tb('positions') + '</div><div id="bcp-bk-pos"><div class="bcp-loading">…</div></div></div>' +
          '<div><div class="bcp-lh">' + tb('orders') + '</div><div id="bcp-bk-ord"><div class="bcp-loading">…</div></div></div>' +
        '</div>' +
      '</div>';
    var box = s.querySelector('#bcp-bk-confirm');
    if (arg.confirm) renderTradeConfirm(arg.confirm);
    else if (arg.resolving) box.innerHTML = '<div class="bcp-loading" style="text-align:left;padding:6px 0 16px">' + tb('resolving') + '</div>';
    else if (arg.badAmount || arg.needAmount || arg.error) {
      var msg = arg.badAmount ? tb('amountRange')
        : arg.needAmount ? (en
          ? 'How much? E.g. "buy $100 of ' + (arg.needAmount.label || 'Bitcoin') + '".'
          : '¿Por cuánto? Ej.: «compra 100 dólares de ' + (arg.needAmount.label || 'Bitcoin') + '».')
        : String(arg.error || '');
      box.innerHTML = '<div style="color:#FFB300;font-size:13px;padding:6px 0 16px">' + esc(msg) + '</div>';
    }
    // no-interactivo: si falta el PIN, loadBroker pinta el formulario inline
    // (jamás el prompt() del navegador al solo ABRIR el escenario)
    loadBroker(false, false);
  }

  // tarjeta de confirmación — SOLO el clic en Confirmar envía la orden
  function renderTradeConfirm(o) {
    var box = document.getElementById('bcp-bk-confirm');
    if (!box || !o || !o.symbol) return;
    _pendingOrder = o;
    var side = o.side === 'sell' ? 'sell' : 'buy';
    var col = side === 'buy' ? UP : DOWN;
    var amount = o.notional != null ? fmtUsd(o.notional) : ((+o.qty || 0) + ' ' + tb('units'));
    box.innerHTML =
      '<div style="border:1px solid ' + col + '55;border-radius:14px;background:' + col + '0d;padding:16px 18px;margin-bottom:16px">' +
        '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px">' +
          '<span style="font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#7C87A3;font-weight:700">' + tb('confirmTitle') + '</span>' +
          '<span id="bcp-bk-cbadge"></span></div>' +
        '<div style="font-size:19px;font-weight:750;margin-bottom:4px"><span style="color:' + col + '">' + tb(side) + '</span> ' +
          esc(amount) + ' · ' + esc(o.label || o.symbol) +
          ' <span style="color:#7C87A3;font-family:\'JetBrains Mono\',monospace;font-size:13px">(' + esc(o.symbol) + ')</span></div>' +
        '<div style="font-size:11.5px;color:#7C87A3;margin-bottom:14px">' + tb('marketOrder') + '</div>' +
        '<div style="display:flex;gap:10px">' +
          '<button id="bcp-bk-ok" class="bcp-back" style="border-color:' + col + '66;color:' + col + ';font-weight:700">' + tb('confirm') + '</button>' +
          '<button id="bcp-bk-no" class="bcp-back">' + tb('cancel') + '</button>' +
        '</div><div id="bcp-bk-cstatus" style="margin-top:10px;font-size:12.5px"></div></div>';
    paintConfirmBadge();   // pinta 🧪/🔴 en cuanto la cuenta esté cargada
    box.querySelector('#bcp-bk-ok').addEventListener('click', confirmPendingOrder);
    box.querySelector('#bcp-bk-no').addEventListener('click', function () {
      _pendingOrder = null;
      box.innerHTML = '<div style="color:#7C87A3;font-size:12.5px;padding:6px 0 16px">' + tb('canceled') + '</div>';
      setTimeout(function () { var b = document.getElementById('bcp-bk-confirm'); if (b && !_pendingOrder) b.innerHTML = ''; }, 3000);
    });
  }

  async function confirmPendingOrder() {
    var o = _pendingOrder;
    if (!o) return;
    var ok = document.getElementById('bcp-bk-ok'), no = document.getElementById('bcp-bk-no');
    var stEl = document.getElementById('bcp-bk-cstatus');
    if (ok) ok.disabled = true;
    if (no) no.disabled = true;
    if (stEl) { stEl.style.color = '#7C87A3'; stEl.textContent = tb('sending'); }
    var r = window._executeTradeOrder ? await window._executeTradeOrder(o)
      : { ok: false, error: 'trading no disponible' };
    stEl = document.getElementById('bcp-bk-cstatus');   // pudo cambiar de escena
    if (r.ok) {
      _pendingOrder = null;
      if (stEl) {
        stEl.style.color = UP;
        stEl.textContent = tb('sent') + ' — ' + ((r.data && r.data.status) || 'accepted') + (r.dedup ? ' ' + tb('dedup') : '');
      }
      setTimeout(function () { loadBroker(false, true); }, 1200);
    } else {
      if (stEl) { stEl.style.color = DOWN; stEl.textContent = '⚠ ' + (r.error || 'error'); }
      ok = document.getElementById('bcp-bk-ok'); no = document.getElementById('bcp-bk-no');
      if (ok) ok.disabled = false;   // permitir reintentar o cancelar
      if (no) no.disabled = false;
    }
  }

  async function loadBroker(interactive, force) {
    var acctEl = document.getElementById('bcp-bk-acct');
    if (!acctEl) return;
    if (!window._tradeFetch || !window._tradeAccountInfo) {
      acctEl.innerHTML = '<div class="bcp-loading" style="color:#FF4D6A">⚠ ' + tb('connectErr') + '</div>';
      return;
    }
    var acct = await window._tradeAccountInfo(interactive !== false, !!force);
    acctEl = document.getElementById('bcp-bk-acct');
    if (!acctEl) return;   // salieron de la escena mientras cargaba
    if (!acct || acct.error) {
      var en2 = ckLang() === 'en';
      if (acct && acct.status === 401) {
        // falta el PIN (o es incorrecto): formulario inline — nunca prompt()
        // del navegador (bloqueado en móvil/PWA y feo en escritorio).
        acctEl.innerHTML =
          '<div style="padding:16px;border:1px solid rgba(0,224,255,.25);border-radius:12px;background:rgba(0,224,255,.05)">' +
            '<div style="font-size:13.5px;font-weight:700;margin-bottom:6px">🔒 ' + (en2 ? 'Trading PIN' : 'PIN de trading') + '</div>' +
            '<div style="font-size:12px;color:#7C87A3;margin-bottom:10px">' +
              (en2 ? 'Enter the PIN you set as TRADE_PIN in Railway. Asked only once per device.'
                   : 'Ingresa el PIN que configuraste como TRADE_PIN en Railway. Se pide una sola vez por dispositivo.') + '</div>' +
            '<div style="display:flex;gap:8px"><input id="bcp-bk-pin" type="password" inputmode="numeric" autocomplete="off" ' +
              'style="flex:1;max-width:200px;padding:8px 12px;border-radius:8px;border:1px solid rgba(122,158,255,.3);background:rgba(8,14,26,.8);color:#E8EDFB;font-size:14px" ' +
              'placeholder="' + (en2 ? 'PIN' : 'PIN') + '">' +
            '<button id="bcp-bk-pin-ok" class="bcp-back" style="border-color:rgba(0,224,255,.45);color:#00E0FF;font-weight:700">' +
              (en2 ? 'Unlock' : 'Entrar') + '</button></div></div>';
        var pinBtn = acctEl.querySelector('#bcp-bk-pin-ok');
        var pinInp = acctEl.querySelector('#bcp-bk-pin');
        var submitPin = function () {
          var v = (pinInp.value || '').trim();
          if (!v) return;
          try { localStorage.setItem('khipu_trade_pin', v); } catch (e) {}
          loadBroker(false, true);
        };
        pinBtn.addEventListener('click', submitPin);
        pinInp.addEventListener('keydown', function (ev) { if (ev.key === 'Enter') submitPin(); });
        pinInp.focus();
      } else {
        // 403 sin TRADE_PIN → mostrar el mensaje del server TAL CUAL (ya en español)
        acctEl.innerHTML = '<div style="color:#FF4D6A;font-size:13px;padding:14px;border:1px solid rgba(255,77,106,.3);border-radius:12px;background:rgba(255,77,106,.06)">⚠ ' +
          esc((acct && acct.error) || tb('connectErr')) + '</div>';
      }
      var pe0 = document.getElementById('bcp-bk-pos'); if (pe0) pe0.innerHTML = '<div class="bcp-loading">—</div>';
      var oe0 = document.getElementById('bcp-bk-ord'); if (oe0) oe0.innerHTML = '<div class="bcp-loading">—</div>';
      return;
    }
    _bkAcct = acct;
    paintConfirmBadge();
    var paper = (typeof acct.paper === 'boolean') ? acct.paper : null;
    acctEl.innerHTML =
      '<div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap">' +
        '<span style="font-size:15px;font-weight:750">💼 ' + tb('account') + '</span>' + badgeHTML(paper) +
        '<button class="bcp-back" style="margin-left:auto" id="bcp-bk-refresh">' + tb('refresh') + '</button></div>' +
      '<div class="bcp-grid3">' +
        '<div class="bcp-stat"><b style="color:' + NEON + '">' + fmtUsd(acct.equity) + '</b><span>' + tb('equity') + '</span></div>' +
        '<div class="bcp-stat"><b>' + fmtUsd(acct.cash) + '</b><span>' + tb('cash') + '</span></div>' +
        '<div class="bcp-stat"><b>' + fmtUsd(acct.buying_power) + '</b><span>' + tb('buyingPower') + '</span></div>' +
      '</div>';
    acctEl.querySelector('#bcp-bk-refresh').addEventListener('click', function () { loadBroker(true, true); });

    // posiciones (símbolo · cantidad · valor · P&L% coloreado)
    try {
      var rp = await window._tradeFetch('/api/trade/positions/detail', {}, false);
      var dp = await rp.json();
      var posEl = document.getElementById('bcp-bk-pos');
      if (posEl) {
        if (!Array.isArray(dp) || !dp.length) {
          posEl.innerHTML = '<div class="bcp-loading" style="padding:12px">' + tb('noPositions') + '</div>';
        } else {
          posEl.innerHTML = dp.map(function (p) {
            var pl = +p.unrealized_pct || 0;
            var col = pl >= 0 ? UP : DOWN;
            return '<div class="bcp-row" style="cursor:default">' +
              '<span class="nm" style="font-family:\'JetBrains Mono\',monospace;font-weight:700">' + esc(p.symbol || '') + '</span>' +
              '<span class="pv" style="width:auto;color:#9BA6C4">' + (+p.qty || 0).toLocaleString('en-US', { maximumFractionDigits: 4 }) + '</span>' +
              '<span class="pv" style="width:84px">' + fmtUsd(p.market_val) + '</span>' +
              '<span class="pv" style="color:' + col + '">' + (pl >= 0 ? '+' : '') + pl.toFixed(2) + '%</span></div>';
          }).join('');
        }
      }
      try { renderPortfolioReport(acct, dp); } catch (eR) {}   // informe (rendimiento + concentración + comentario)
    } catch (e) { var pe = document.getElementById('bcp-bk-pos'); if (pe) pe.innerHTML = '<div class="bcp-loading">—</div>'; }

    // últimas órdenes (si /api/trade/history responde)
    try {
      var ro = await window._tradeFetch('/api/trade/history', {}, false);
      var od = await ro.json();
      var ordEl = document.getElementById('bcp-bk-ord');
      if (ordEl) {
        if (!Array.isArray(od) || !od.length) {
          ordEl.innerHTML = '<div class="bcp-loading" style="padding:12px">' + tb('noOrders') + '</div>';
        } else {
          ordEl.innerHTML = od.slice(0, 10).map(function (o) {
            var col = o.side === 'buy' ? UP : DOWN;
            var when = '';
            try { when = new Date(o.created_at).toLocaleString(ckLang() === 'en' ? 'en' : 'es', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }); } catch (e2) {}
            var amt = o.notional ? fmtUsd(o.notional) : (((+o.qty || +o.filled_qty || 0) || '') + '×');
            return '<div class="bcp-row" style="cursor:default">' +
              '<span class="pv" style="width:auto;color:#5b6580">' + esc(when) + '</span>' +
              '<span style="color:' + col + ';font-weight:700;font-size:11px;min-width:44px">' + esc((o.side || '').toUpperCase()) + '</span>' +
              '<span class="nm" style="font-family:\'JetBrains Mono\',monospace">' + esc(o.symbol || '') + '</span>' +
              '<span class="pv" style="width:auto">' + esc(String(amt)) + '</span>' +
              '<span class="pv" style="width:auto;color:#9BA6C4">' + esc(o.status || '') + '</span></div>';
          }).join('');
        }
      }
    } catch (e) { var oe = document.getElementById('bcp-bk-ord'); if (oe) oe.innerHTML = '<div class="bcp-loading">—</div>'; }
  }

  // ── comandos de compra/venta en TEXTO (compartido con command_center.js) ──
  // "compra 100 dólares de bitcoin" · "compra $50 de eth" · "vende 20 de solana"
  // · "buy $100 of bitcoin" · "compra bitcoin por 100 dólares".
  // Números sueltos se interpretan como MONTO EN DÓLARES (notional).
  // Devuelve {side, amountUsd|null, assetText} o null si no es un comando.
  window._parseTradeCommand = function (text) {
    var s = String(text || '').trim();
    if (!s) return null;
    var low = s.toLowerCase();
    var m = low.match(/^(c[oó]mprame|compra(?:r|me)?|buy|v[eé]ndeme|vende(?:r|me)?|sell)\s+(.+)$/);
    if (!m) return null;
    var side = /^(v|s)/.test(m[1]) ? 'sell' : 'buy';
    var rest = m[2].replace(/[?!.]+$/, '').trim();
    // "$100 de bitcoin" · "100 dólares de bitcoin" · "100 de eth" · "100 usd de eth"
    var am = rest.match(/^\$?\s*([\d][\d.,]*)\s*(?:d[oó]lares|dollars|usd|\$)?\s+(?:de|del|of|en)\s+(.+)$/);
    if (!am) {
      // "bitcoin por 100 dólares" · "bitcoin for $100"
      var am2 = rest.match(/^(.+?)\s+(?:por|for)\s+\$?\s*([\d][\d.,]*)\s*(?:d[oó]lares|dollars|usd|\$)?$/);
      if (am2) am = [am2[0], am2[2], am2[1]];
    }
    if (!am) {
      // sin monto ("compra bitcoin") → la Cabina pedirá el monto
      return { side: side, amountUsd: null, assetText: rest };
    }
    var rawNum = am[1].replace(/,(?=\d{3}\b)/g, '').replace(',', '.');
    var amount = parseFloat(rawNum);
    if (!isFinite(amount) || amount <= 0) return null;
    var asset = (am[2] || '').trim();
    if (!asset) return null;
    return { side: side, amountUsd: amount, assetText: asset };
  };

  // Comando de compra/venta → Cabina en el stage broker con la tarjeta de
  // confirmación. Lo llama ask() y también command_center.js (texto fuera de
  // la Cabina). parsed = resultado de window._parseTradeCommand.
  window._openBrokerConfirm = async function (parsed) {
    if (!parsed) return false;
    openCockpit({ kind: 'broker', arg: { resolving: true } });
    if (!window._resolveTradeSymbol) return true;
    var arg;
    try {
      var res = await window._resolveTradeSymbol(parsed.assetText);
      if (!res.ok) arg = { error: res.error };
      else if (parsed.amountUsd == null) arg = { needAmount: res };
      else if (!(parsed.amountUsd >= 1 && parsed.amountUsd <= 100000)) arg = { badAmount: true };
      else arg = { confirm: { symbol: res.symbol, side: parsed.side, notional: parsed.amountUsd, label: res.label, kind: res.kind } };
    } catch (e) { arg = { error: String((e && e.message) || e) }; }
    stage('broker', arg);
    return true;
  };

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
    // 2º: patrones locales con datos del servidor (precio histórico, ~300ms)
    if (window.KhipuLocalCharts && window.KhipuLocalCharts.tryAsync) {
      var localA = await window.KhipuLocalCharts.tryAsync(query);
      if (localA && window._cvRenderCard) { window._cvRenderCard(cardId, query, localA, 'local ⚡ sin IA'); return; }
    }
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

  /* ══ SIMULACIÓN POR AGENTES (MiroFish desde la terminal de Bixby) ══
     Varios agentes analistas (empresa / gobierno / geopolítica) debaten un
     escenario y proyectan impactos REALISTAS. Server: POST /api/sim/agents
     {scenario, seeds, lang} → {narrative, impacts:[{id,label,pct,rationale}],
     agents:[{name,type,stance}], rounds?}. Un solo fetch: el stage y el helper
     público (voice.js) comparten la MISMA promesa. ══ */
  function fetchAgentSim(scenario, seeds, lang) {
    var body = { scenario: scenario, seeds: seeds || [], lang: lang || ckLang() };
    try {
      return fetch((window.BASE || '') + '/api/sim/agents', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      }).then(function (r) { return r.json().catch(function () { return { ok: false, error: L('Respuesta inválida del servidor', 'Invalid server response') }; }); })
        .catch(function (e) { return { ok: false, error: String((e && e.message) || e) }; });
    } catch (e) { return Promise.resolve({ ok: false, error: String((e && e.message) || e) }); }
  }

  function agentTypeColor(type) {
    var t = String(type || '').toLowerCase();
    if (/gob|gover|state|estad|regul|polic|central bank|banco central/.test(t)) return VIOLET;
    if (/geo|pol[ií]t|macro|milit|defens|nation/.test(t)) return '#FFB300';
    return NEON; // empresa / mercado / industria
  }

  function renderAgentSim(d, en) {
    var agents = Array.isArray(d.agents) ? d.agents : [];
    var impacts = Array.isArray(d.impacts) ? d.impacts : [];
    var agentsHTML = agents.length
      ? '<div class="bcp-lh">' + (en ? 'Agents in the debate' : 'Agentes en el debate') + '</div>' +
        '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px">' +
        agents.map(function (a) {
          var col = agentTypeColor(a.type);
          return '<div class="bcp-agent" style="border-color:' + col + '55;background:' + col + '0d">' +
            '<div class="an">' + esc(a.name || '') + '</div>' +
            (a.type ? '<div class="at" style="color:' + col + '">' + esc(a.type) + '</div>' : '') +
            (a.stance ? '<div class="as">' + esc(a.stance) + '</div>' : '') +
          '</div>';
        }).join('') + '</div>'
      : '';
    var narrHTML = d.narrative
      ? '<div style="border:1px solid rgba(122,158,255,.16);border-radius:14px;background:rgba(11,18,34,.55);' +
        'padding:16px 18px;font-size:14px;line-height:1.6;color:#E8EDFB;white-space:pre-wrap;margin-bottom:18px">' +
        esc(d.narrative) + '</div>'
      : '';
    var impactsHTML = impacts.length ? impacts.map(function (x) {
      var pct = (typeof x.pct === 'number') ? x.pct : (parseFloat(x.pct) || 0);
      var col = pct >= 0 ? UP : DOWN;
      var w = Math.min(100, Math.abs(pct));
      var id = x.id || '';
      return '<div class="bcp-agrow"' + (id ? ' data-id="' + esc(id) + '"' : ' style="cursor:default"') + '>' +
        '<div class="bcp-agrow-top">' +
          '<span class="bcp-dot" style="background:' + col + ';color:' + col + '"></span>' +
          '<span class="nm">' + esc(x.label || id) + '</span>' +
          '<span class="bar" style="background:' + col + '22"><i style="width:' + w + '%;background:' + col + '"></i></span>' +
          '<span class="pv" style="color:' + col + '">' + (pct >= 0 ? '+' : '') + Math.round(pct) + '%</span>' +
        '</div>' +
        (x.rationale ? '<div class="bcp-agwhy">' + esc(x.rationale) + '</div>' : '') +
      '</div>';
    }).join('') : '<div class="bcp-loading">' + (en ? 'No quantified impacts.' : 'Sin impactos cuantificados.') + '</div>';
    // sello del modelo que razonó (transparencia: Sonnet 5 vs respaldo sin IA)
    var mdl = d.model ? String(d.model) : '';
    var mLabel = /sonnet-5/i.test(mdl) ? 'Claude Sonnet 5'
      : /haiku/i.test(mdl) ? 'Claude Haiku'
      : /claude/i.test(mdl) ? mdl
      : /gemini/i.test(mdl) ? 'Google Gemini'
      : /nvidia|llama/i.test(mdl) ? 'NVIDIA' : '';
    var modelHTML = mLabel
      ? '<div style="display:inline-flex;align-items:center;gap:6px;margin-bottom:14px;padding:3px 10px;border-radius:999px;' +
        'border:1px solid ' + NEON + '44;background:' + NEON + '11;font-size:10.5px;color:' + NEON + '">✦ ' +
        (en ? 'Reasoned by ' : 'Razonado por ') + esc(mLabel) + '</div>'
      : (d.model === '' && mdl === '' ? '' : '');
    return modelHTML + agentsHTML + narrHTML +
      '<div class="bcp-lh">' + (en ? 'Projected impact by company' : 'Impacto proyectado por empresa') + '</div>' + impactsHTML;
  }

  function stageAgentSim(s, arg) {
    arg = arg || {};
    var en = ckLang() === 'en';
    var scen = arg.scenario || '';
    var title = en ? 'Agent simulation' : 'Simulación por agentes';
    s.innerHTML = backBar(title) +
      '<div class="bcp-inner" style="max-width:1040px">' +
        '<div class="bcp-simhd"><span class="big">🧪 ' + esc(scen || title) + '</span>' +
          '<span class="kind" style="background:' + NEON + '22;color:' + NEON + '">MiroFish</span>' +
          '<span style="color:#7C87A3;font-size:12px">' + (en ? 'analysts debating…' : 'analistas debatiendo…') + '</span></div>' +
        '<div id="bcp-ag-body"></div>' +
      '</div>';
    // espera LARGA (Sonnet 5, ~10-30s): progreso por pasos, no un vacío
    var _ld = window.KhipuLoading && window.KhipuLoading.staged('bcp-ag-body', {
      title: en ? 'Multi-agent simulation' : 'Simulación por agentes',
      accent: NEON,
      steps: en
        ? ['Assembling the agents (companies + government + geopolitics)', 'Round 1: the analysts debate the scenario', 'Round 2: the shock propagates through the chain', 'Estimating realistic impacts per company', 'Writing the consensus']
        : ['Reuniendo a los agentes (empresas + gobierno + geopolítica)', 'Ronda 1: los analistas debaten el escenario', 'Ronda 2: el golpe se propaga por la cadena', 'Estimando impactos realistas por empresa', 'Redactando el consenso'],
    });
    var p = arg.promise || fetchAgentSim(scen, arg.seeds || [], ckLang());
    p.then(function (d) {
      if (_ld) _ld.stop();
      var body = document.getElementById('bcp-ag-body');
      if (!body) return;   // salieron de la escena
      if (!d || d.ok === false) {
        body.innerHTML = '<div class="bcp-loading" style="color:#FF4D6A">⚠ ' + esc((d && d.error) || (en ? 'Simulation failed' : 'La simulación falló')) + '</div>';
        return;
      }
      body.innerHTML = renderAgentSim(d, en);
      body.querySelectorAll('.bcp-agrow[data-id]').forEach(function (el) {
        el.addEventListener('click', function () { stage('xray', el.getAttribute('data-id')); });
      });
    });
  }

  // Helper público (lo llama voice.js): abre la Cabina en la sim por agentes y
  // devuelve la promesa del resultado para que Bixby narre el consenso.
  window._runAgentSim = function (scenario, seeds, lang) {
    ensureShell();
    var p = fetchAgentSim(scenario, seeds || [], lang);
    openCockpit({ kind: 'agentsim', arg: { scenario: scenario, seeds: seeds || [], promise: p } });
    return p || Promise.resolve({ ok: false, error: 'no fetch' });
  };

  /* ══ INVESTIGACIÓN PROFUNDA (más allá del nodo) ══
     Server: POST /api/research/deep {id, lang} → {thesis, sector, competitors,
     geopolitics, chokepoints, risks, watch, disclaimer}. ══ */
  function fetchResearch(id, lang) {
    var body = { id: id, lang: lang || ckLang() };
    try {
      return fetch((window.BASE || '') + '/api/research/deep', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      }).then(function (r) { return r.json().catch(function () { return { ok: false, error: L('Respuesta inválida del servidor', 'Invalid server response') }; }); })
        .catch(function (e) { return { ok: false, error: String((e && e.message) || e) }; });
    } catch (e) { return Promise.resolve({ ok: false, error: String((e && e.message) || e) }); }
  }

  function renderResearch(d, en) {
    function block(title, txt) {
      if (!txt) return '';
      return '<div class="bcp-rs-sec"><div class="bcp-lh">' + esc(title) + '</div><div class="bcp-rs-txt">' + esc(txt) + '</div></div>';
    }
    function listBlock(title, arr, color) {
      if (!Array.isArray(arr) || !arr.length) return '';
      return '<div class="bcp-rs-sec"><div class="bcp-lh"' + (color ? ' style="color:' + color + '"' : '') + '>' + esc(title) + '</div><ul class="bcp-rs-list">' +
        arr.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul></div>';
    }
    var comp = Array.isArray(d.competitors) ? d.competitors : [];
    var compHTML = comp.length
      ? '<div class="bcp-rs-sec"><div class="bcp-lh">' + (en ? 'Direct competitors' : 'Competidores directos') + '</div>' +
        '<div class="bcp-chips" style="justify-content:flex-start">' +
        comp.map(function (c) { return '<span class="bcp-chip" data-q="' + esc(c) + '">' + esc(c) + '</span>'; }).join('') + '</div></div>'
      : '';
    var thesisHTML = d.thesis
      ? '<div style="border:1px solid rgba(0,224,255,.25);border-radius:14px;background:rgba(0,224,255,.05);padding:16px 18px;margin-bottom:16px">' +
        '<div class="bcp-lh" style="color:' + NEON + '">' + (en ? 'Investment thesis' : 'Tesis de inversión') + '</div>' +
        '<div class="bcp-rs-txt" style="font-size:14.5px">' + esc(d.thesis) + '</div></div>'
      : '';
    return thesisHTML +
      block(en ? 'Sector' : 'Sector', d.sector) +
      compHTML +
      block(en ? 'Geopolitics' : 'Geopolítica', d.geopolitics) +
      listBlock(en ? 'Supply-chain chokepoints' : 'Cuellos de botella de la cadena', d.chokepoints, DOWN) +
      listBlock(en ? 'Risks' : 'Riesgos', d.risks, DOWN) +
      listBlock(en ? 'What to watch' : 'Qué vigilar', d.watch, NEON) +
      (d.disclaimer ? '<div style="margin-top:14px;font-size:11px;color:#5b6580;font-style:italic">' + esc(d.disclaimer) + '</div>' : '');
  }

  function stageResearch(s, arg) {
    arg = arg || {};
    var en = ckLang() === 'en';
    var n = arg.id ? resolveNode(arg.id) : null;
    var label = (n && n.label) || arg.label || arg.id || '';
    s.innerHTML = backBar(en ? 'Deep research' : 'Investigación profunda') +
      '<div class="bcp-inner" style="max-width:900px">' +
        '<div class="bcp-simhd"><span class="big">🧠 ' + esc(label) + '</span>' +
          '<span style="color:#7C87A3;font-size:12px">' + (en ? 'sector · competitors · geopolitics · thesis' : 'sector · competidores · geopolítica · tesis') + '</span></div>' +
        '<div id="bcp-rs-body"></div>' +
      '</div>';
    var _ld = window.KhipuLoading && window.KhipuLoading.staged('bcp-rs-body', {
      title: en ? 'Deep research' : 'Investigación profunda',
      accent: '#8e5aff',
      steps: en
        ? ['Mapping the sector landscape', 'Identifying direct competitors', 'Assessing geopolitical exposure', 'Finding supply-chain chokepoints', 'Writing the investment thesis']
        : ['Mapeando el panorama del sector', 'Identificando competidores directos', 'Evaluando la exposición geopolítica', 'Buscando cuellos de botella de la cadena', 'Redactando la tesis de inversión'],
    });
    var p = arg.promise || fetchResearch(arg.id, ckLang());
    p.then(function (d) {
      if (_ld) _ld.stop();
      var body = document.getElementById('bcp-rs-body');
      if (!body) return;
      if (!d || d.ok === false) {
        body.innerHTML = '<div class="bcp-loading" style="color:#FF4D6A">⚠ ' + esc((d && d.error) || (en ? 'Research failed' : 'La investigación falló')) + '</div>';
        return;
      }
      body.innerHTML = renderResearch(d, en);
      body.querySelectorAll('.bcp-chip[data-q]').forEach(function (el) {
        el.addEventListener('click', function () { var rn = resolveNode(el.getAttribute('data-q')); if (rn) stage('xray', rn.id); });
      });
    });
  }

  // Helper público (voice.js): abre la investigación profunda en la Cabina y
  // devuelve la promesa del informe para que Bixby narre la tesis.
  // OJO: NO usar el nombre window._openResearch — app.html ya lo usa para el
  // panel "📄 SEC" (10-K de EDGAR). Aquí es la investigación PROFUNDA de la Cabina.
  window._openDeepResearch = function (id, lang) {
    ensureShell();
    var p = fetchResearch(id, lang);
    openCockpit({ kind: 'research', arg: { id: id, promise: p } });
    return p || Promise.resolve({ ok: false, error: 'no fetch' });
  };

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

    // 1.5) BRÓKER (Etapa M): "compra 100 dólares de bitcoin" · "vende 20 de eth"
    //      → tarjeta de confirmación; "mi cuenta" / "broker" / "portafolio" → cuenta
    var tcmd = window._parseTradeCommand ? window._parseTradeCommand(text) : null;
    if (tcmd) {
      if (window._openBrokerConfirm) window._openBrokerConfirm(tcmd);
      else stage('broker');
      return;
    }
    if (/^(mi\s+|la\s+|my\s+)?(cuenta|br[oó]ker|broker|account)\s*$/.test(low) ||
        /^(mi\s+|my\s+)?(portafolio|portfolio|posiciones|positions)(\s+del?\s+(br[oó]ker|broker|alpaca))?\s*$/.test(low)) {
      stage('broker'); return;
    }

    // 2) lienzo en blanco / gráfico
    if (/^(l[ií]enzo|canvas)\b/.test(low) || /lienzo en blanco/.test(low)) { stage('canvas'); return; }
    if (/^(gr[aá]fico|gr[aá]fica|graf|chart|dibuja|tabla|visualiza)\b[:\s]/.test(low) || low.indexOf('gráfico:') >= 0) {
      stage('canvas', text.replace(/^(gr[aá]fico|gr[aá]fica|graf|chart|dibuja|tabla|visualiza)\s*:?\s*/i, '')); return;
    }

    // 2.5) investigación profunda. Si nombra una EMPRESA → informe estructurado
    //      (sector/competidores/geopolítica/tesis, /api/research/deep). Si es una
    //      pregunta abierta → el bucle multi-paso (Capa 4, /api/deep/analyze).
    var invM = low.match(/(?:investiga(?:ci[oó]n)?(?:\s+(?:de|sobre|a))?|research|reporte\s+de|informe\s+de|tesis\s+(?:de|sobre))\s+(.+)/);
    if (invM) {
      var invT = invM[1].replace(/\?+$/, '').trim();
      var invN = resolveNode(invT);
      if (invN) { stage('research', { id: invN.id }); return; }
      stage('deep', text); return;   // pregunta abierta → multi-paso
    }
    if (/investiga|a fondo|an[aá]lisis profundo|profundiza|\bdeep\b/.test(low)) {
      stage('deep', text); return;
    }

    // 2.55) dossier financiero (ingresos, dilución, FCF, márgenes, ROE…)
    // vía _surface: con la Cabina abierta lo sube POR ENCIMA (z), no atrás
    var dosM = low.match(/(?:dossier|fundamentales|financieros)\s+(?:de\s+)?(.+)/);
    if (dosM && window.openFinCard) {
      var dn = resolveNode(dosM[1].replace(/\?+$/, '').trim());
      if (dn) {
        if (window._surface) { window._surface('dossier', dn.mkt || dn.id); return; }
        window.openFinCard(dn.mkt || dn.id); return;
      }
      stageNotFound(document.getElementById('bcp-stage'), dosM[1].replace(/\?+$/, '').trim()); return;
    }

    // 2.6) el grafo o la terminal, DENTRO de la pantalla de Bixby
    if (/universo|\b3d\b/.test(low)) { close(); if (window._go3D) { window._go3D(); return; } }
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

    // 4.5) SIMULACIÓN POR AGENTES (MiroFish): escenarios abiertos en lenguaje
    //      natural — "simula que China prohíbe HBM", "qué pasaría si cae Taiwán".
    //      El "qué pasa si cae X" simple (present) sigue yendo al sim local rápido.
    var agM = low.match(/^(?:simulate|simula(?:r|me|ci[oó]n)?|run\s+a\s+simulation(?:\s+of)?)\b\s*(?:that|the scenario|un escenario|el escenario|que|del?|:)?\s*(.+)$/)
           || low.match(/^(?:qu[eé]\s+pasar[ií]a|what\s+would\s+happen(?:\s+if)?|what\s+if)\s+(?:si\s+|if\s+)?(.+)$/);
    if (agM) {
      var scen = agM[1].replace(/\?+$/, '').trim();
      if (scen) { stage('agentsim', { scenario: scen, seeds: extractSeeds(scen) }); return; }
    }

    // 5) simular / caída — si el nombre no resuelve, decirlo CON sugerencias
    var sim = low.match(/(?:qu[eé] pasa si cae|si cae|cae|colaps|corte de|corta[nr]?|sanci[oó]n(?:a[nr]?)?|prohib|auge de|boom de|demanda de|simula[nr]?|shock)\s+(.+)/);
    if (sim) {
      var kind = /auge|boom|demanda/.test(low) ? 'demand' : /sanci|prohib/.test(low) ? 'sanction' : /precio/.test(low) ? 'price' : 'collapse';
      var target = sim[1].replace(/\?+$/, '').trim();
      var nn = resolveNode(target);
      if (nn) { stage('sim', { id: nn.id, kind: kind }); return; }
      stageNotFound(document.getElementById('bcp-stage'), target); return;
    }

    // 6) desármame / radiografía / x-ray → X-Ray; el nombre es claramente una
    //    empresa: si no resuelve, mensaje con sugerencias (no "no existe")
    var xrStrong = low.match(/(?:des[aá]rma(?:me)?|radiograf[ií]a|x-?ray|destripa(?:me)?)\s+(?:la\s+empresa\s+|a\s+)?(.+)/);
    if (xrStrong) {
      var nxs = resolveNode(xrStrong[1].replace(/\?+$/, '').trim());
      if (nxs) { stage('xray', nxs.id); return; }
      stageNotFound(document.getElementById('bcp-stage'), xrStrong[1].replace(/\?+$/, '').trim()); return;
    }
    // verbos genéricos (analiza/abre/muéstrame): si no resuelven, seguimos al fallback
    var xr = low.match(/(?:anal[ií]za|abre|mu[eé]strame)\s+(?:la\s+empresa\s+|a\s+)?(.+)/);
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
    mountCockpitOrb();
    if (initial && initial.kind) stage(initial.kind, initial.arg);
    else if (!document.getElementById('bcp-stage').children.length) stage('empty');
    setTimeout(function () { var i = document.getElementById('bcp-input'); if (i) i.focus(); }, 60);
    try { _portfolioPulse(); } catch (e) {}   // pulso proactivo del portafolio (silencioso sin PIN)
  }
  function close() {
    restoreAdopted();   // devolver grafo/terminal a su sitio original
    stopCockpitOrb();
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
