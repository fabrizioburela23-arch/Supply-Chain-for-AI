/* ============================================================================
   engine/cockpit.js — CABINA DE BIXBY · el modo pantalla completa
   Khipu deja de ser un botón: SE VUELVE la pantalla.
   - Arriba: el orbe/logo de Khipu + estado (escuchando / pensando / listo) +
     una barra para pedirle cosas por texto o por voz (🎙).
   - Abajo: un ESCENARIO grande (un lienzo) donde Khipu te muestra lo que pidas:
       · la radiografía completa de una empresa (X-Ray a pantalla completa)
       · una simulación de shock (a quién arrastra / quién gana)
       · dos empresas comparadas lado a lado
       · un gráfico / tabla generado por IA (Canvas)  ·  o un lienzo en blanco
   Voz y texto van al MISMO escenario: cuando Khipu (por voz) abre un X-Ray,
   xray.js detecta que la cabina está abierta y lo pinta aquí, no en el cajón.

   Depende de (todos ya cargados antes que este archivo):
     window.buildXRayHTML / wireXRay (xray.js) · KhipuState (statematrix.js) ·
     registerBixbyOrb (app.html) · BixbyVoice (voice.js) · KHIPU (khipu_lang.js)
   ============================================================================ */
(function () {
  'use strict';

  var NEON = '#00E0FF', VIOLET = '#8e5aff', UP = '#2BE38B', DOWN = '#FF4D6A';
  var open = false;

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

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
      // palabra COMPLETA: antes "XPO" entraba por estar dentro de "eXPOrtar"
      if (lab && lab.length >= 3 && new RegExp('(^|[^a-z0-9])' + lab.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '([^a-z0-9]|$)').test(nt)) { seen[n.id] = 1; out.push(n.id); return; }
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
    brokerDup:   { es: 'Esa orden ya había llegado al bróker — no se envió dos veces. Si quieres OTRA igual, vuelve a enviarla.',
                   en: 'That order had already reached the broker — it was not sent twice. If you want ANOTHER identical one, send it again.' },
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
/* ══ KHIPUS OS (2026-10-06) — tokens de diseño, definidos UNA vez sobre #bcp-ov.
   Claro = el look del video (body sin .dark); oscuro = predeterminado de la app (body.dark).
   La Cabina clásica (kh_desk_mode=off, red de seguridad) usa SIEMPRE los oscuros: sus escenas
   viejas tienen colores fijos oscuros. Ventanas, barra y paleta leen solo estas variables →
   cambiar de tema es CSS puro (sin re-inyectar nada). ══ */
body:not(.dark) #bcp-ov,body:not(.dark) .kos-themed{
  --os-bg:#EDEDF5;--os-surface:#FFFFFF;--os-surface-2:#F2F2F7;--os-surface-3:#E7E7EF;
  --os-ink:#111216;--os-ink-2:#5B5E6B;--os-ink-3:#8D90A0;--os-line:rgba(17,18,22,.08);
  --os-shadow:0 1px 2px rgba(17,18,40,.04), 0 8px 28px rgba(17,18,40,.06);
  --os-accent:#2F6BEA;--os-pos:#2F6BEA;--os-neg:#E8623A;--os-mute:#C9CAD6;--os-good:#0ca30c;--os-bad:#d03b3b;
  --os-btn:#111216;--os-btn-ink:#FFFFFF;
  --kos-shadow-lg:0 2px 6px rgba(17,18,40,.06), 0 18px 48px rgba(17,18,40,.14);
  --kos-scrim:rgba(24,26,44,.22);--kos-accent-soft:rgba(47,107,234,.12);
  color-scheme:light}
body.dark #bcp-ov,body.dark .kos-themed,body #bcp-ov.kos-classic,#bcp-ov .kd-legacy-dark{
  --os-bg:#0E0F14;--os-surface:#17181F;--os-surface-2:#1F2029;--os-surface-3:#2A2B36;
  --os-ink:#F2F2F5;--os-ink-2:#A6A8B5;--os-ink-3:#6E7080;--os-line:rgba(255,255,255,.07);
  --os-shadow:0 1px 2px rgba(0,0,0,.4), 0 10px 30px rgba(0,0,0,.35);
  --os-accent:#4C8DF6;--os-pos:#4C8DF6;--os-neg:#F07A52;--os-mute:#3A3C4A;--os-good:#2fbf5b;--os-bad:#f06565;
  --os-btn:#F2F2F5;--os-btn-ink:#111216;
  --kos-shadow-lg:0 2px 8px rgba(0,0,0,.45), 0 22px 56px rgba(0,0,0,.55);
  --kos-scrim:rgba(0,0,0,.5);--kos-accent-soft:rgba(76,141,246,.16);
  color-scheme:dark}
/* colores SEMÁNTICOS de TEXTO con contraste AA (los --os-good/--os-bad vivos quedan para rellenos, barras y anillos):
   mismos valores que el comité (engine/committee.js --cm-good/--cm-bad/--cm-warn/--cm-ai) */
body:not(.dark) #bcp-ov,body:not(.dark) .kos-themed{--os-good-ink:#066B06;--os-bad-ink:#A82424;--os-warn:#B7791F;--os-warn-ink:#7F5200;--os-ai:#6236C9}
body.dark #bcp-ov,body.dark .kos-themed,body #bcp-ov.kos-classic,#bcp-ov .kd-legacy-dark{--os-good-ink:#2fbf5b;--os-bad-ink:#F47C7C;--os-warn:#F2C46D;--os-warn-ink:#F2C46D;--os-ai:#B48CFF}
/* .kos-themed: cualquier overlay FUERA de #bcp-ov (Dossier, Investigación, Clientes…) toma los mismos tokens */
.kos-themed{--os-r:18px;--os-r-sm:12px;--os-font:'Nunito', 'Geist', system-ui, -apple-system, 'Segoe UI', sans-serif;--km-ring:var(--os-surface)}
#bcp-ov{--os-r:18px;--os-r-sm:12px;--os-font:'Nunito', 'Geist', system-ui, -apple-system, 'Segoe UI', sans-serif;
  position:fixed;inset:0;z-index:7000;display:none;flex-direction:column;
  background:var(--os-bg);color:var(--os-ink);font-family:var(--os-font);
  -webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;--km-ring:var(--os-surface);animation:bcpFade .22s ease}
#bcp-ov.show{display:flex}
#bcp-ov button{font-family:inherit}
@keyframes bcpFade{from{opacity:0}to{opacity:1}}
@keyframes kosPop{from{opacity:0;transform:translateY(-4px) scale(.985)}to{opacity:1;transform:none}}
@media(prefers-reduced-motion:reduce){#bcp-ov,.kos-pop,.kos-pal-box{animation:none!important}}
/* ── BARRA SUPERIOR (mínima, como el video) ── */
#bcp-top{display:flex;align-items:center;gap:8px;margin:14px 16px 0;padding:0 10px 0 14px;height:60px;flex-shrink:0;
  background:var(--os-surface);border-radius:var(--os-r);box-shadow:var(--os-shadow);position:relative;z-index:30}
.kos-brand{display:flex;align-items:center;gap:10px;flex-shrink:0;min-width:0;padding-right:4px}
#bcp-orb-wrap{position:relative;width:30px;height:30px;flex-shrink:0;display:flex;align-items:center;justify-content:center}
#bcp-orb-wrap canvas{width:30px!important;height:30px!important;border-radius:50%}
.kos-orbf{display:block;width:28px;height:28px;border-radius:50%;background:radial-gradient(circle at 32% 28%,#ffd0e0 0,rgba(255,208,224,0) 38%),linear-gradient(135deg,#f07fa0,#7a4ce8 55%,#ff8746)}
#bcp-idwrap{display:flex;align-items:center;gap:8px;min-width:0}
#bcp-word{font-size:17px;font-weight:800;letter-spacing:-.01em;color:var(--os-ink);white-space:nowrap}
#bcp-word .sub{font-weight:600;color:var(--os-ink-2);margin-left:5px;letter-spacing:0}
@media(max-width:1280px){#bcp-word .sub{display:none}}
#bcp-state{display:none;align-items:center;gap:6px;font-size:11.5px;font-weight:600;color:var(--os-ink-2);
  background:var(--os-surface-2);border-radius:999px;padding:3px 9px 3px 8px;white-space:nowrap}
#bcp-state.live,#bcp-state.think{display:inline-flex}
#bcp-state .dot{width:7px;height:7px;border-radius:50%;background:var(--os-ink-3)}
#bcp-state.live .dot{background:var(--os-bad);animation:bcpPulse 1.2s ease-in-out infinite}
#bcp-state.think .dot{background:var(--os-accent);animation:bcpPulse .8s ease-in-out infinite}
@keyframes bcpPulse{0%,100%{opacity:1}50%{opacity:.3}}
.kos-mid{flex:1;display:flex;align-items:center;justify-content:center;gap:4px;min-width:0}
.kos-search{flex:0 1 460px;min-width:0;height:40px;display:flex;align-items:center;gap:10px;padding:0 16px 0 7px;border-radius:999px;
  background:var(--os-surface-2);border:0;color:var(--os-ink-3);font-size:14px;cursor:text;text-align:left;transition:background .15s,box-shadow .15s}
.kos-search:hover{background:var(--os-surface-3)}
.kos-search:focus-visible{outline:none;box-shadow:0 0 0 3px var(--kos-accent-soft)}
.kos-search .tx{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.kos-kbd{flex-shrink:0;font-size:11.5px;font-weight:600;color:var(--os-ink-2);background:var(--os-surface);border-radius:999px;
  padding:4px 9px;box-shadow:0 0 0 1px var(--os-line);font-variant-numeric:tabular-nums;letter-spacing:.02em}
.kos-btn{height:40px;padding:0 14px;border-radius:999px;border:0;background:transparent;color:var(--os-ink-2);font-size:14px;font-weight:500;
  cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:6px;white-space:nowrap;flex-shrink:0;transition:background .15s,color .15s}
.kos-btn:hover,.kos-btn.on{background:var(--os-surface-2);color:var(--os-ink)}
.kos-btn:focus-visible,.kos-bal:focus-visible,.kos-av:focus-visible{outline:none;box-shadow:0 0 0 3px var(--kos-accent-soft)}
.kos-more-btn svg,#kos-theme svg{width:14px;height:14px;flex-shrink:0}
/* Tools: el botón principal de la barra (todas las pantallas) */
.kos-btn.kos-more-btn{margin-left:6px;padding:0 16px 0 13px;font-weight:700;color:#fff;letter-spacing:.01em;background:linear-gradient(135deg,#7a4ce8,#f07fa0);box-shadow:0 6px 18px -8px rgba(122,76,232,.7)}
.kos-btn.kos-more-btn:hover,.kos-btn.kos-more-btn.on{color:#fff;background:linear-gradient(135deg,#6a3be0,#ec6d92);transform:translateY(-1px)}
.kos-more-btn .ti{width:15px;height:15px;flex-shrink:0}
#kos-theme svg{width:17px;height:17px}
.kos-round{width:40px;padding:0;font-size:13px;font-weight:600;letter-spacing:.02em}
.kos-right{display:flex;align-items:center;gap:2px;flex-shrink:0}
.kos-agbtn{padding:0 8px}
.kos-bal{display:flex;flex-direction:column;align-items:flex-end;justify-content:center;gap:1px;line-height:1.15;height:46px;padding:0 12px;
  border:0;background:transparent;border-radius:14px;cursor:pointer;color:var(--os-ink);flex-shrink:0;transition:background .15s}
.kos-bal:hover{background:var(--os-surface-2)}
.kos-bal .l{font-size:11.5px;color:var(--os-ink-2);font-weight:500;white-space:nowrap;display:flex;align-items:center;gap:5px}
.kos-bal .v{font-size:15px;font-weight:650;color:var(--os-ink);font-variant-numeric:tabular-nums;letter-spacing:-.01em;white-space:nowrap}
.kos-bal .v.sm{font-size:13px;font-weight:600;color:var(--os-accent)}
.kos-badge{font-size:10px;font-weight:700;letter-spacing:.04em;border-radius:999px;padding:1px 7px}
.kos-badge.paper{background:var(--os-surface-2);color:var(--os-ink-2)}
.kos-badge.real{background:#d03b3b;color:#fff}
.kos-av{width:40px;height:40px;border-radius:50%;border:0;background:var(--os-surface-2);color:var(--os-ink);font-weight:650;font-size:13.5px;
  letter-spacing:.03em;cursor:pointer;flex-shrink:0;margin-left:4px;transition:background .15s}
.kos-av:hover,.kos-av.on{background:var(--os-surface-3)}
#bcp-close{display:none}
/* pila de mascotas: solapamiento fijo (el % de margen de mascot.js depende del ancho del contenedor) */
#bcp-ov .km-stack{display:inline-flex;align-items:center}
#bcp-ov .km-stack .km{margin-left:-7px}
#bcp-ov .km-stack .km:first-child{margin-left:0}
/* la fila de chips de la Cabina vieja ya no existe a la vista: todo se abre desde el chat, ⌘K o "Más" */
#bcp-actions{display:none!important}
/* ── menús (Más ▾ y el de tus iniciales) ── */
.kos-pop{position:absolute;z-index:9400;background:var(--os-surface);color:var(--os-ink);border-radius:16px;border:1px solid var(--os-line);
  box-shadow:var(--kos-shadow-lg);padding:8px;animation:kosPop .14s ease;max-height:calc(100vh - 100px);overflow-y:auto}
.kos-more{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:2px 6px;width:min(900px,calc(100vw - 32px))}
.kos-more .grp{display:flex;flex-direction:column;gap:1px;min-width:0}
.kos-ph{font-size:11.5px;font-weight:600;color:var(--os-ink-3);padding:8px 10px 4px;letter-spacing:.01em}
.kos-mi{display:flex;align-items:center;gap:10px;width:100%;text-align:left;border:0;background:transparent;color:var(--os-ink);
  font-size:13.5px;padding:8px 10px;border-radius:10px;cursor:pointer;min-width:0}
.kos-mi:hover,.kos-mi:focus-visible{background:var(--os-surface-2);outline:none}
.kos-mi .ic{width:20px;text-align:center;flex-shrink:0;font-size:14px}
.kos-mi .tx{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.kos-mi .hint{margin-left:auto;color:var(--os-ink-3);font-size:12px;white-space:nowrap}
.kos-sep{height:1px;background:var(--os-line);margin:6px 4px}
.kos-me{width:260px}
.kos-mehd{display:flex;align-items:center;gap:10px;padding:8px 10px 10px}
.kos-mehd .nm{font-weight:650;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.kos-mehd .sb{font-size:12px;color:var(--os-ink-3)}
.kos-mehd input{width:100%;box-sizing:border-box;border:1px solid var(--os-line);background:var(--os-surface-2);color:var(--os-ink);
  border-radius:10px;padding:7px 10px;font:inherit;font-size:13.5px;outline:none}
.kos-seg{display:flex;background:var(--os-surface-2);border-radius:11px;padding:3px;gap:2px;margin:2px 6px 6px}
.kos-seg button{flex:1;border:0;background:transparent;border-radius:8px;padding:7px 10px;font-size:13px;color:var(--os-ink-2);cursor:pointer}
.kos-seg button.on{background:var(--os-surface);color:var(--os-ink);box-shadow:0 1px 2px rgba(0,0,0,.12);font-weight:600}
.kos-segl{font-size:11.5px;color:var(--os-ink-3);padding:6px 12px 0}
.kos-mob{display:none}
/* ── PALETA ⌘K ── */
#kos-pal{position:absolute;inset:0;z-index:9600;display:none;align-items:flex-start;justify-content:center;padding-top:11vh;
  background:var(--kos-scrim);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px)}
#kos-pal.show{display:flex;animation:bcpFade .12s ease}
.kos-pal-box{width:min(640px,calc(100vw - 24px));max-height:min(580px,78vh);display:flex;flex-direction:column;background:var(--os-surface);
  color:var(--os-ink);border-radius:20px;box-shadow:var(--kos-shadow-lg);border:1px solid var(--os-line);overflow:hidden;animation:kosPop .16s ease}
.kos-pal-in{display:flex;align-items:center;gap:12px;padding:16px 18px;border-bottom:1px solid var(--os-line)}
.kos-pal-in svg{width:18px;height:18px;color:var(--os-ink-3);flex-shrink:0}
.kos-pal-in input{flex:1;min-width:0;border:0;outline:0;background:transparent;color:var(--os-ink);font:inherit;font-size:17px}
.kos-pal-in input::placeholder{color:var(--os-ink-3)}
.kos-pal-list{overflow-y:auto;padding:6px 8px 8px;scrollbar-width:thin}
.kos-pal-sec{font-size:11.5px;font-weight:600;color:var(--os-ink-3);padding:10px 10px 4px}
.kos-pi{display:flex;align-items:center;gap:12px;padding:8px 10px;border-radius:12px;cursor:pointer;color:var(--os-ink);font-size:14px;min-width:0}
.kos-pi.on{background:var(--os-surface-2)}
.kos-pi .ic{width:30px;height:30px;border-radius:9px;display:flex;align-items:center;justify-content:center;background:var(--os-surface-2);
  font-size:14px;flex-shrink:0;color:var(--os-ink-2);font-weight:650}
.kos-pi.on .ic{background:var(--os-surface)}
.kos-pi .ic i{width:10px;height:10px;border-radius:50%;display:block}
.kos-pi .tx{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.kos-pi .sub{color:var(--os-ink-3);font-size:12.5px;margin-left:6px}
.kos-pi .go{color:var(--os-ink-3);font-size:12px;white-space:nowrap;opacity:0}
.kos-pi.on .go{opacity:1}
.kos-pal-empty{padding:22px 14px;color:var(--os-ink-3);font-size:13.5px;text-align:center}
.kos-pal-foot{display:flex;gap:16px;padding:9px 16px;border-top:1px solid var(--os-line);font-size:12px;color:var(--os-ink-3);flex-wrap:wrap}
.kos-pal-foot b{font-weight:600;color:var(--os-ink-2)}
/* ── COLUMNA CENTRAL DEL CHAT (desktop.js #kd-center, ≥ 1100 px) ── */
.kos-chat{position:absolute;inset:0;display:flex;flex-direction:column;background:var(--os-surface);border-radius:var(--os-r);
  box-shadow:var(--os-shadow);overflow:hidden;color:var(--os-ink);container-type:inline-size}
/* columna angosta (≈ 1100 px de ventana): la pila de mascotas ya está en la barra superior */
@container (max-width:500px){.kos-stackbtn{display:none}}
.kos-chathd{display:flex;align-items:center;gap:12px;padding:16px 16px 10px 18px;flex-shrink:0}
.kos-chathd .who{min-width:0}
.kos-chathd .nm{font-size:16px;font-weight:650;letter-spacing:-.01em;line-height:1.2}
.kos-chathd .sb{font-size:12.5px;color:var(--os-ink-2);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.kos-chathd .sp{flex:1}
.kos-ib{width:34px;height:34px;border-radius:50%;border:0;background:transparent;color:var(--os-ink-3);cursor:pointer;display:inline-flex;
  align-items:center;justify-content:center;flex-shrink:0;transition:background .15s,color .15s}
.kos-ib:hover{background:var(--os-surface-2);color:var(--os-ink)}
.kos-ib svg{width:17px;height:17px}
.kos-stackbtn{border:0;background:transparent;padding:5px 6px;border-radius:999px;cursor:pointer;display:inline-flex;flex-shrink:0}
.kos-stackbtn:hover{background:var(--os-surface-2)}
.kos-chatbody{flex:1;min-height:0;overflow-y:auto;padding:2px 18px 10px;scrollbar-width:thin;scrollbar-color:var(--os-surface-3) transparent;overscroll-behavior:contain}
.kos-chatbody .kc-thread{max-width:none}
.kos-has-msgs #kos-empty{display:none}
#kd-center #bcp-barwrap{padding:8px 14px 14px;background:transparent;border:0}
#kd-center #bcp-bar{max-width:none}
/* estado vacío del chat (sin mensajes): Khipu grande, una frase, sugerencias, lo vivo de hoy */
#kos-empty{display:flex;flex-direction:column;align-items:center;text-align:center;padding:5vh 6px 10px;max-width:520px;margin:0 auto}
.kos-hero{margin:0 0 14px;line-height:0;filter:drop-shadow(0 10px 22px rgba(194,58,140,.22))}
.kos-empty-h{font-size:34px;font-weight:800;letter-spacing:-.02em;margin:0;color:var(--os-ink);line-height:1.1}
.kos-empty-h .sub{display:block;font-size:17px;font-weight:600;letter-spacing:.01em;color:var(--os-ink-2);margin-top:6px}
.kos-empty-p{font-size:15px;color:var(--os-ink-2);margin:8px 0 22px;line-height:1.5}
.kos-sugg{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin:0 0 20px}
.kos-chip{border:0;background:var(--os-surface-2);color:var(--os-ink);font-size:13.5px;line-height:1.3;padding:9px 14px;border-radius:999px;
  cursor:pointer;text-align:left;transition:background .14s,transform .14s}
.kos-chip:hover{background:var(--os-surface-3);transform:translateY(-1px)}
.kos-chip:focus-visible{outline:none;box-shadow:0 0 0 3px var(--kos-accent-soft)}
#kos-empty .bcp-live{font-size:13px;line-height:1.55;color:var(--os-ink-2);margin:0 0 6px;max-width:56ch}
.kos-agrow{display:flex;gap:6px;justify-content:center;flex-wrap:wrap;margin:16px 0 0}
.kos-ag{display:flex;flex-direction:column;align-items:center;gap:6px;border:0;background:transparent;cursor:pointer;color:var(--os-ink-2);
  font-size:12px;padding:8px 8px 6px;border-radius:14px;min-width:64px;transition:background .14s,color .14s}
.kos-ag:hover{background:var(--os-surface-2);color:var(--os-ink)}
.kos-ag.off{opacity:.45}
/* ── barra de entrada del chat (en la columna central o, < 1100 px, abajo) ── */
#bcp-barwrap{flex-shrink:0;padding:10px 16px 14px;display:flex;justify-content:center;background:var(--os-bg);position:relative;z-index:60}
#bcp-bar{display:flex;align-items:center;gap:4px;width:100%;max-width:900px;background:var(--os-surface-2);border-radius:999px;
  padding:5px 5px 5px 18px;border:1px solid transparent;transition:border-color .15s,box-shadow .15s,background .15s}
#bcp-bar:focus-within{background:var(--os-surface);border-color:var(--os-line);box-shadow:0 0 0 4px var(--kos-accent-soft)}
#bcp-input{flex:1;min-width:0;background:transparent;border:0;color:var(--os-ink);font-size:15px;padding:10px 4px;outline:none;font-family:inherit}
#bcp-input::placeholder{color:var(--os-ink-3)}
/* INVOCAR: el agente invocado entra a la conversación (la firma de Khipus) */
#kos-inv{display:inline-flex;align-items:center;gap:6px;flex-shrink:0;height:34px;padding:0 6px 0 4px;margin-left:-12px;border-radius:999px;background:var(--os-surface);box-shadow:0 0 0 1px var(--os-line);font-size:13px;font-weight:700;color:var(--os-ink);white-space:nowrap}
#kos-inv[hidden]{display:none}
#kos-inv .x{border:0;background:transparent;color:var(--os-ink-3);cursor:pointer;font-size:13px;width:22px;height:22px;border-radius:50%;padding:0}
#kos-inv .x:hover{background:var(--os-surface-2);color:var(--os-ink)}
#kos-inv.pop{animation:kosInv .55s cubic-bezier(.2,1.4,.4,1)}
@keyframes kosInv{0%{transform:scale(.4) translateY(6px);opacity:0}60%{transform:scale(1.08)}100%{transform:none;opacity:1}}
.kos-ag.inv{background:var(--os-surface-2);color:var(--os-ink);box-shadow:0 0 0 2px var(--kos-accent-soft)}
.kos-ag .iv{font-size:10px;font-weight:800;color:var(--os-accent,#7a4ce8);text-transform:uppercase;letter-spacing:.07em;opacity:0;transition:opacity .15s;height:12px}
.kos-ag:hover .iv,.kos-ag:focus-visible .iv,.kos-ag.inv .iv{opacity:1}
@media(hover:none){.kos-ag .iv{display:none}}
@media(prefers-reduced-motion:reduce){#kos-inv.pop{animation:none}}
.bcp-iconbtn{width:40px;height:40px;flex-shrink:0;border-radius:50%;border:0;background:transparent;color:var(--os-ink-2);cursor:pointer;
  font-size:16px;display:flex;align-items:center;justify-content:center;transition:background .14s,color .14s,transform .14s}
.bcp-iconbtn:hover{background:var(--os-surface-3);color:var(--os-ink)}
.bcp-iconbtn svg{width:18px;height:18px}
#bcp-send{width:42px;height:42px;color:#fff;background:radial-gradient(circle at 30% 25%,rgba(255,255,255,.45) 0,rgba(255,255,255,0) 40%),
  linear-gradient(135deg,#f07fa0 0%,#c23a8c 40%,#7a4ce8 70%,#ff8746 100%);box-shadow:0 4px 14px rgba(194,58,140,.32)}
#bcp-send:hover{transform:scale(1.04);color:#fff;background:radial-gradient(circle at 30% 25%,rgba(255,255,255,.55) 0,rgba(255,255,255,0) 40%),
  linear-gradient(135deg,#f07fa0 0%,#c23a8c 40%,#7a4ce8 70%,#ff8746 100%)}
#bcp-mic.on{background:var(--os-bad);color:#fff;animation:bcpPulse 1.1s ease-in-out infinite}
/* escenario */
#bcp-stage{flex:1;overflow-y:auto;padding:22px;position:relative;scrollbar-width:thin}
@keyframes bcpStageIn{from{opacity:.35;transform:translateY(4px)}to{opacity:1;transform:none}}
#bcp-stage>*{animation:bcpStageIn .16s ease}
@media(prefers-reduced-motion:reduce){#bcp-stage>*{animation:none}}
.bcp-embed{height:calc(100vh - 250px);min-height:420px;display:flex;flex-direction:column;
  border:1px solid var(--os-line);border-radius:14px;overflow:hidden;background:var(--os-surface);position:relative}
/* GRAFO en una ventana ANGOSTA (flancos del OS: 300-760 px). La ficha de app.html (.panel) mide 380 px FIJOS y
   no encoge: el mapa se quedaba con 0-36 px (vacío, sin asentar). Ahí la ficha sale de la fila: el mapa usa
   todo el ancho y la ficha aparece como hoja inferior SOLO con una empresa elegida (#detail visible); ✕ o un
   clic en el fondo del mapa la cierran (deselect). Fuera de ventanas o con ventana ancha, nada cambia; el
   celular (≤ 820 px) conserva su hoja propia de app.html. */
@media(min-width:821px){#bcp-stage.kd-desk:not(.kd-mobile) .kd-body>#bcp-embed-graph{container:kosmap/inline-size}}
@container kosmap (max-width:760px){
  #bcp-embed-graph>main>.panel{position:absolute;left:0;right:0;bottom:0;top:auto;width:auto;min-width:0;height:45%;max-height:none;
    transform:none;z-index:30;border-left:0;border-top:1px solid var(--os-line);border-radius:14px 14px 0 0;box-shadow:0 -10px 30px rgba(0,0,0,.28)}
  #bcp-embed-graph>main>.panel:has(>#detail[style*="none"]){display:none}
  #bcp-embed-graph>main>.panel>.detail{padding-top:34px}
  #bcp-embed-graph>main>.panel>.sheet-close{display:flex;position:absolute;top:6px;right:8px;width:28px;height:28px;z-index:3;border-radius:50%;font-size:13px}
  /* como en el celular: la leyenda y la ayuda tapaban un tercio del mapa (la franja de sectores de arriba queda) */
  #bcp-embed-graph>main>.graph-wrap>.legend,#bcp-embed-graph>main>.graph-wrap>.graph-hint{display:none}
}
/* inicio en el "muro" (pantallas medianas sin chat al centro) */
#bcp-empty{max-width:760px;margin:5vh auto 0;padding:0 8px;text-align:left}
.bcp-hello{font-family:var(--os-font);font-weight:700;font-size:clamp(28px,4vw,38px);line-height:1.12;letter-spacing:-.025em;color:var(--os-ink);margin:0 0 12px}
.bcp-hello span{color:var(--os-ink-3)}
.bcp-lead{color:var(--os-ink-2);font-size:15px;line-height:1.55;margin:0 0 22px;max-width:60ch}
.bcp-live{font-size:13.5px;line-height:1.55;color:var(--os-ink-2);margin:0 0 8px;max-width:70ch}
.bcp-live:empty{display:none}
.bcp-live .new{color:var(--os-accent);font-weight:650}.bcp-live .old{color:var(--os-ink-3)}.bcp-live .dim{color:var(--os-ink-3)}
.bcp-live a,.bcp-foot a{color:var(--os-accent);text-decoration:none;margin-left:6px;font-weight:550}
.bcp-live a:hover,.bcp-foot a:hover{text-decoration:underline}
.bcp-cols{display:grid;grid-template-columns:1fr 1fr;gap:28px 40px;margin:30px 0 0}
@media(max-width:620px){.bcp-cols{grid-template-columns:1fr;gap:22px}}
.bcp-cols h3{font-size:12.5px;font-weight:600;color:var(--os-ink-3);margin:0 0 10px;letter-spacing:.01em}
.bcp-cols ul{list-style:none;margin:0;padding:0}
.bcp-cols li{margin:0 0 9px}
.bcp-cols a{color:var(--os-ink);font-size:14.5px;line-height:1.4;text-decoration:none;border-bottom:1px solid var(--os-line);padding-bottom:1px;transition:border-color .12s,color .12s}
.bcp-cols a:hover,.bcp-cols a:focus-visible{color:var(--os-accent);border-bottom-color:var(--os-accent);outline:none}
.bcp-foot{margin:28px 0 0;font-size:13px;color:var(--os-ink-3)}
/* ── teléfono / pantallas medianas ── */
@media(max-width:1099px){.kos-search{flex-basis:340px}.kos-bal .lt{display:none}.kos-bal{flex-direction:row;align-items:center;gap:6px}}
@media(max-width:900px){.kos-agbtn,#kos-lang{display:none}.kos-btn.kos-more-btn .tx{display:none}.kos-btn.kos-more-btn{width:40px;padding:0}.kos-mob{display:block}}
@media(max-width:760px){
  #bcp-top{margin:8px 8px 0;height:54px;padding:0 6px 0 10px;gap:6px;border-radius:16px}
  #bcp-word{font-size:16px}
  .kos-mid{justify-content:flex-start}
  .kos-search{height:38px;flex:1 1 auto;padding:0 12px}
  .kos-search .kos-kbd{display:none}
  .kos-bal,#kos-theme{display:none}
  .kos-av{width:38px;height:38px;margin-left:0}
  .kos-more{grid-template-columns:1fr 1fr;width:calc(100vw - 16px)}
  #bcp-barwrap{padding:8px 8px 10px}
  #bcp-bar{padding-left:14px}
  #kos-pal{padding-top:8px}
  .kos-pal-box{max-height:calc(100vh - 16px)}
}
@media(max-width:420px){#bcp-word{display:none}.kos-more{grid-template-columns:1fr}}
.bcp-pick-h{font-size:18px;font-weight:650;margin:6px 0 4px;color:#E8EDFB}
.bcp-pick-p{color:#8E9AB8;font-size:13px;margin:0 0 16px}
.bcp-pick-f{position:relative;margin:0 0 12px}
.bcp-pick-f input{width:100%;box-sizing:border-box;background:rgba(11,18,34,.8);border:1px solid rgba(122,158,255,.25);border-radius:10px;color:#E8EDFB;font-size:15px;padding:11px 14px;outline:none;font-family:inherit}
.bcp-pick-f input:focus{border-color:rgba(0,224,255,.55)}
.bcp-pick-sug{display:flex;flex-direction:column;gap:4px;margin-top:6px}
.bcp-pick-it{text-align:left;border:1px solid rgba(122,158,255,.16);background:rgba(11,18,34,.6);color:#E8EDFB;border-radius:9px;padding:9px 12px;cursor:pointer;font-size:13.5px;font-family:inherit}
.bcp-pick-it span{color:#8E9AB8;font-size:12px;margin-left:6px}
.bcp-pick-it:hover{border-color:rgba(0,224,255,.5)}
.bcp-pick-go{margin-top:6px}
.bcp-foot a{margin-left:0}
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
/* icono de carga animado en TODOS los estados de carga (pedido de Fabrizio: toda
   carga debe tener icono con animación). ::before → spinner centrado sobre el texto. */
.bcp-loading::before{content:"";display:block;width:26px;height:26px;margin:0 auto 12px;border-radius:50%;
  border:2.5px solid rgba(122,158,255,.18);border-top-color:#00E0FF;animation:bcpSpin .7s linear infinite}
@keyframes bcpSpin{to{transform:rotate(360deg)}}
/* ── Insights del HIPERGRAFO (simulación en vivo narrada) ── */
.bcp-hyper{margin:0 0 22px}
.bcp-hyper-hd{display:flex;align-items:center;gap:9px;margin:0 0 12px}
.bcp-hyper-hd .t{font-size:13px;font-weight:750;color:#E8EDFB;letter-spacing:.01em}
.bcp-hyper-hd .live{font-size:9.5px;font-weight:800;letter-spacing:.1em;color:#00E0FF;
  border:1px solid rgba(0,224,255,.4);border-radius:999px;padding:2px 8px;display:inline-flex;align-items:center;gap:5px}
.bcp-hyper-hd .live::before{content:"";width:6px;height:6px;border-radius:50%;background:#00E0FF;
  box-shadow:0 0 8px #00E0FF;animation:bcpPulse 1.6s ease-in-out infinite}
@keyframes bcpPulse{0%,100%{opacity:1}50%{opacity:.25}}
.bcp-facts{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 14px}
.bcp-fact{font-size:11px;padding:5px 11px;border-radius:999px;color:#FFD27A;cursor:default;
  background:rgba(255,179,0,.09);border:1px solid rgba(255,179,0,.32);display:inline-flex;align-items:center;gap:6px}
.bcp-fact b{color:#FFE7B0;font-weight:700}
.bcp-icards{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:0 0 14px}
@media(max-width:760px){.bcp-icards{grid-template-columns:1fr}}
.bcp-icard{border:1px solid rgba(122,158,255,.16);border-left-width:3px;border-radius:12px;
  padding:12px 14px;background:rgba(11,18,34,.5)}
.bcp-icard .ih{display:flex;align-items:center;gap:8px;margin:0 0 5px}
.bcp-icard .ic{font-size:14px}
.bcp-icard .it{font-size:12.5px;font-weight:700;color:#E8EDFB}
.bcp-icard .id{font-size:12px;color:#AEB8D4;line-height:1.5}
.bcp-icard.k-riesgo{border-left-color:#FF4D6A}
.bcp-icard.k-oportunidad{border-left-color:#2BE38B}
.bcp-icard.k-estructura{border-left-color:#00E0FF}
.bcp-casc{border:1px solid rgba(122,158,255,.12);border-radius:12px;padding:11px 14px;background:rgba(4,6,11,.4)}
.bcp-casc .ch{font-size:10.5px;text-transform:uppercase;letter-spacing:.1em;color:#7C87A3;font-weight:600;margin:0 0 9px}
.bcp-cascrow{display:flex;align-items:center;gap:9px;font-size:12px;padding:3px 0;cursor:pointer}
.bcp-cascrow:hover .nm{color:#00E0FF}
.bcp-cascrow .nm{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#C7D0EA}
.bcp-cascrow .bar{width:120px;height:5px;border-radius:3px;background:rgba(122,158,255,.1);overflow:hidden;flex:none}
.bcp-cascrow .bar i{display:block;height:100%;background:linear-gradient(90deg,#FF4D6A,#FFB300)}
.bcp-cascrow .pv{font-family:'JetBrains Mono',monospace;font-size:11px;width:44px;text-align:right;flex:none;color:#FF8FA3}
.bcp-hyper-foot{font-size:10.5px;color:#5E6884;margin:9px 2px 0}
/* ── MODO DEMOSTRACIÓN — Khipu maneja la app y va narrando ── */
#bcp-demo{position:absolute;left:0;right:0;bottom:74px;z-index:12;padding:0 22px;
  pointer-events:none;animation:bcpDemoIn .3s ease}
@keyframes bcpDemoIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.bcp-demobox{pointer-events:auto;max-width:1200px;margin:0 auto;display:flex;align-items:center;gap:14px;
  padding:13px 18px;border-radius:16px;border:1px solid rgba(0,224,255,.32);
  background:rgba(6,11,22,.93);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
  box-shadow:0 10px 40px rgba(0,0,0,.55),0 0 0 1px rgba(0,224,255,.06)}
.bcp-demoav{width:34px;height:34px;border-radius:50%;flex:none;position:relative;
  background:radial-gradient(circle at 35% 32%,#7ef0ff,#00E0FF 45%,#0b6fa8);
  box-shadow:0 0 16px rgba(0,224,255,.65)}
.bcp-demoav::after{content:"";position:absolute;inset:-5px;border-radius:50%;
  border:1.5px solid rgba(0,224,255,.35);animation:bcpDemoPing 1.8s ease-out infinite}
@keyframes bcpDemoPing{0%{transform:scale(.85);opacity:.9}100%{transform:scale(1.25);opacity:0}}
.bcp-demotxtwrap{flex:1;min-width:0}
.bcp-demolabel{font-size:9.5px;font-weight:800;letter-spacing:.12em;color:#00E0FF;margin:0 0 3px}
.bcp-demotxt{font-size:13.5px;line-height:1.45;color:#E8EDFB}
.bcp-demotxt .cur{display:inline-block;width:7px;color:#00E0FF;animation:bcpBlink .8s steps(1) infinite}
@keyframes bcpBlink{50%{opacity:0}}
.bcp-democtl{display:flex;align-items:center;gap:7px;flex:none}
.bcp-demobtn{width:32px;height:32px;border-radius:9px;cursor:pointer;font-size:13px;
  display:inline-flex;align-items:center;justify-content:center;color:#9BA6C4;
  background:rgba(11,18,34,.7);border:1px solid rgba(122,158,255,.2);transition:all .13s;font-family:inherit}
.bcp-demobtn:hover{color:#E8EDFB;border-color:rgba(0,224,255,.5)}
.bcp-demodots{display:flex;gap:4px;align-items:center;margin-right:4px}
.bcp-demodot{width:6px;height:6px;border-radius:50%;background:rgba(122,158,255,.25);transition:all .2s}
.bcp-demodot.on{background:#00E0FF;box-shadow:0 0 7px #00E0FF}
.bcp-demodot.done{background:rgba(0,224,255,.45)}
@media(max-width:700px){.bcp-demodots{display:none}.bcp-demotxt{font-size:12.5px}#bcp-demo{padding:0 12px}}
/* simulación por agentes (motor interno) — impactos por empresa con motivo */
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
/* CHAT de Khipu (2026-09-30): el hilo vive a pantalla completa en la escena
   'chat'; cuando una acción cambia la escena (X-Ray, mapa, gráfico…) el hilo
   baja a este DOCK sobre la barra → la respuesta NUNCA desaparece.
   Khipus OS (≥ 1100 px): el hilo y la barra viven en la columna central (#kd-center)
   y este dock queda oculto; < 1100 px sigue siendo el dock de abajo. */
/* z-index: por encima de la hoja inferior del mapa en el celular (.panel, z 50) */
#bcp-chatdock{position:relative;z-index:60}
#bcp-ov.kos-centered #bcp-chatdock{display:none!important}
/* ESCRITORIO (engine/desktop.js): chrome compacto para que las ventanas tengan alto;
   el dock del chat cede espacio pero sigue SIEMPRE presente (cabecera + barra de entrada) */
#bcp-ov.desk #bcp-chatdock{max-height:24vh}
@media(max-height:820px){#bcp-ov.desk #bcp-chatdock{max-height:20vh}#bcp-ov.desk:not(.kos-centered) #bcp-barwrap{padding:6px 16px 10px}}
#bcp-chatdock{flex-shrink:0;display:none;flex-direction:column;margin:8px 16px 0;border-radius:var(--os-r);
  background:var(--os-surface);box-shadow:var(--os-shadow);max-height:34vh;min-height:0;overflow:hidden}
#bcp-chatdock.show{display:flex}
#bcp-chatdock.min .bd{display:none}
#bcp-chatdock .hd{display:flex;align-items:center;gap:8px;padding:8px 14px 6px 18px;font-size:12.5px;font-weight:600;color:var(--os-ink-2);flex-shrink:0}
#bcp-chatdock .hd .sp{flex:1}
#bcp-chatdock .hd .ttl{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#bcp-chatdock .hd button{background:transparent;border:0;color:var(--os-ink-2);border-radius:999px;
  padding:5px 11px;font-size:12px;cursor:pointer;font-family:inherit;white-space:nowrap;flex-shrink:0}
#bcp-chatdock .hd button:hover{background:var(--os-surface-2);color:var(--os-ink)}
#bcp-chatdock .bd{overflow-y:auto;padding:2px 18px 12px;min-height:0;scrollbar-width:thin}
.bcp-chatwrap{max-width:900px;margin:0 auto}
.bcp-chattools{display:flex;justify-content:flex-end;gap:8px;max-width:860px;margin:0 auto 10px}
.bcp-chattools button{background:transparent;border:1px solid var(--os-line);color:var(--os-ink-2);border-radius:999px;
  padding:5px 12px;font-size:12px;cursor:pointer;font-family:inherit}
@media(max-width:700px){#bcp-chatdock{max-height:40vh;margin:6px 8px 0}#bcp-chatdock .hd,#bcp-chatdock .bd{padding-left:12px;padding-right:12px}}
`;
    var st = document.createElement('style'); st.id = 'bcp-styles'; st.textContent = css;
    document.head.appendChild(st);
  }

  // Botones de la fila de chips de la Cabina vieja: [data-act, icono, es, en]. La fila ya
  // no se ve en Khipus OS (#bcp-actions oculta, se conserva el nodo); queda como registro.
  function actChips() {
    return [
      ['broker',     '💼', 'Invertir',      'Invest'],
      ['scalp',      '⚡', 'Scalping',      'Scalping'],
      ['crypto',     '💠', 'Cripto',        'Crypto'],
      ['graph',      '🗺️', 'Grafo',         'Graph'],
      ['terminal',   '🖥️', 'Terminal',      'Terminal'],
      ['market',     '📈', 'Mercado',       'Market'],
      ['xray',       '🔬', 'X-Ray',         'X-Ray'],
      ['sim',        '◉',  'Simular',       'Simulate'],
      ['compare',    '⇄',  'Comparar',      'Compare'],
      ['insights',   '💡', 'Oportunidades', 'Opportunities'],
      ['deep',       '🧠', 'Investigar',    'Research'],
      ['canvas',     '✦',  'Gráfico',       'Chart'],
      ['simulation', '🔮', 'Escenarios',    'Scenarios'],
      ['geo',        '🌐', 'Geo',           'Geo'],
      ['space',      '🚀', 'Espacio',       'Space'],
    ];
  }

  /* ══ KHIPUS OS (2026-10-06): utilidades de la cáscara ══ */
  var SVG = {
    tools: '<svg class="ti" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><rect x="1.5" y="1.5" width="5.5" height="5.5" rx="1.8"/><rect x="9" y="1.5" width="5.5" height="5.5" rx="1.8"/><rect x="1.5" y="9" width="5.5" height="5.5" rx="1.8"/><rect x="9" y="9" width="5.5" height="5.5" rx="2.75"/></svg>',
    chev: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 6l4 4 4-4"/></svg>',
    mic: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></svg>',
    send: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5M6 11l6-6 6 6"/></svg>',
    search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>',
    compose: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20h8"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4z"/></svg>',
    moon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg>',
    sun: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
  };
  function _fold(s) { return String(s == null ? '' : s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').trim(); }
  function _isMac() { try { return /Mac|iPhone|iPad|iPod/.test(navigator.platform || navigator.userAgent || ''); } catch (e) { return false; } }
  var AGENT_IDS = ['analista', 'radar', 'cadena', 'tecnico', 'comite'];
  // "Preguntar a": el token que el chat YA entiende (engine/pickers.js ANALYSTS / khipu_chat SEAT_OF)
  var AGENT_TOK = { analista: ['@fundamental', '@fundamental'], radar: ['@noticias', '@news'], cadena: ['@cadena', '@supply'],
    tecnico: ['@tecnico', '@technical'], comite: ['@comite', '@committee'] };
  var AGENT_FALLBACK = { khipu: ['#f07fa0', '#7a4ce8', 'Khipu', 'Khipu'], analista: ['#7d8be6', '#4054cf', 'Analista', 'Analyst'],
    radar: ['#f78189', '#e63e52', 'Radar', 'Radar'], cadena: ['#4cb1ab', '#83cd70', 'Cadena', 'Chain'],
    tecnico: ['#f7cc63', '#e6a117', 'Técnico', 'Technical'], comite: ['#bc78e5', '#7a3fe0', 'Comité', 'Committee'] };
  // mascota burbuja (engine/mascot.js); si el módulo no cargó, un círculo con su degradado
  function _mascot(id, size, opts) {
    try { if (window.KhipuMascot && window.KhipuMascot.svg) return window.KhipuMascot.svg(id, size, opts); } catch (e) {}
    var c = AGENT_FALLBACK[id] || ['#8D90A0', '#5B5E6B'];
    return '<span class="km" style="display:inline-block;width:' + size + 'px;height:' + size + 'px;border-radius:50%;flex-shrink:0;background:linear-gradient(135deg,' + c[0] + ',' + c[1] + ')"></span>';
  }
  function _stackHTML(ids, size) {
    try { if (window.KhipuMascot && window.KhipuMascot.stack) return window.KhipuMascot.stack(ids, size); } catch (e) {}
    return '<span class="km-stack" style="display:inline-flex">' + ids.map(function (id, i) { return '<span style="margin-left:' + (i ? -6 : 0) + 'px;display:inline-flex">' + _mascot(id, size) + '</span>'; }).join('') + '</span>';
  }
  function _agentName(id) {
    try { if (window.KhipuMascot && window.KhipuMascot.name) return window.KhipuMascot.name(id); } catch (e) {}
    var c = AGENT_FALLBACK[id]; return c ? L(c[2], c[3]) : String(id || '');
  }
  function _agentRole(id) {
    try {
      var a = (window.KhipuMascot && window.KhipuMascot.agents ? window.KhipuMascot.agents() : []).filter(function (x) { return x.id === id; })[0];
      if (a) return L(a.role_es, a.role_en);
    } catch (e) {}
    return '';
  }
  function _agentsOn() {
    try { if (window.KhipuAgentPrefs) return window.KhipuAgentPrefs.enabled().filter(function (a) { return a !== 'khipu' && AGENT_IDS.indexOf(a) >= 0; }); } catch (e) {}
    return AGENT_IDS.slice();
  }
  function _mode() { try { return window.KhipuAgentPrefs ? window.KhipuAgentPrefs.mode() : null; } catch (e) { return null; } }
  function _setMode(m) {
    try { if (window.KhipuAgentPrefs) window.KhipuAgentPrefs.set({ mode: m === 'pro' ? 'pro' : 'simple' }); } catch (e) {}
    try {
      if (window.KhipuToast && window.KhipuToast.show) window.KhipuToast.show({ kind: 'info',
        title: m === 'pro' ? L('Modo Pro', 'Pro mode') : L('Modo Simple', 'Simple mode'),
        body: m === 'pro' ? L('Respuestas densas: cifras, rangos y horizonte.', 'Dense answers: figures, ranges and horizon.')
                          : L('Lenguaje llano: cada término explicado y una conclusión clara.', 'Plain language: every term explained and a clear conclusion.') });
    } catch (e) {}
  }
  // dinero con el formato del idioma ($50.218,49 / $50,218.49); nunca inventa: sin número → —
  function _money(v) {
    var n = Number(v); if (!isFinite(n)) return '—';
    return '$' + n.toLocaleString(ckLang() === 'en' ? 'en-US' : 'es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  function _selNode() { try { return (window._liveSelectedNode && window._liveSelectedNode()) || null; } catch (e) { return null; } }
  // overlays de otros módulos que viven DEBAJO de la Cabina (z 7000): se suben mientras están abiertos
  function _raise(id, z) {
    var el = document.getElementById(id); if (!el) return;
    el.style.zIndex = String(z);
    if (el._kosRaise || !window.MutationObserver) return;
    el._kosRaise = true;
    var mo = new MutationObserver(function () {
      if (el.classList.contains('show')) return;
      el.style.zIndex = ''; el._kosRaise = false; mo.disconnect();
    });
    mo.observe(el, { attributes: true, attributeFilter: ['class'] });
  }
  function _openSistemaOS(tab) {
    if (typeof window.openSistema !== 'function') return;
    window.openSistema(tab);
    _raise('sistema-overlay', 7900); _raise('sistema-panel', 7901);
  }

  /* ══ REGISTRO ÚNICO DE PANTALLAS (menú "Más ▾" y paleta ⌘K) — sale de los chips, de
     KIND_META y de los overlays de otros módulos. Cada entrada sabe abrirse. ══ */
  var GROUPS = [['explore', 'Explorar', 'Explore'], ['invest', 'Invertir', 'Invest'], ['discover', 'Descubrir', 'Discover'], ['help', 'Ayuda y sistema', 'Help & system']];
  function screens() {
    var W = window, sel = _selNode();
    var all = [
      { g: 'explore', id: 'graph', ic: '🗺️', es: 'Mapa de la cadena', en: 'Supply-chain map', k: 'mapa grafo red cadena map graph network', run: function () { stage('graph'); } },
      { g: 'explore', id: 'market', ic: '📈', es: 'Mercado', en: 'Market', k: 'mercado precios cotizaciones market prices quotes', run: function () { stage('market'); } },
      { g: 'explore', id: 'terminal', ic: '🖥️', es: 'Terminal', en: 'Terminal', k: 'terminal graficos charts bloomberg velas', run: function () { stage('terminal'); } },
      { g: 'explore', id: 'geo', ic: '🌐', es: 'Geopolítica', en: 'Geopolitics', k: 'geopolitica world monitor mundo conflictos estrechos geo', run: function () { stage('geo'); } },
      { g: 'explore', id: 'space', ic: '🚀', es: 'Espacio', en: 'Space', k: 'espacio space lanzamientos launches satelites', run: function () { stage('space'); } },
      { g: 'explore', id: 'simulation', ic: '🔮', es: 'Simulación', en: 'Simulation', k: 'simulacion escenarios scenarios what if guerra war room', run: function () { stage('simulation'); } },
      { g: 'explore', id: 'crypto', ic: '💠', es: 'Cripto', en: 'Crypto', k: 'cripto crypto bitcoin ethereum', run: function () { stage('crypto'); } },
      { g: 'explore', id: 'tkg', ic: '⏱', es: 'Grafo temporal', en: 'Temporal graph', k: 'grafo temporal historia tiempo timeline', run: function () { stage('tkg'); } },
      { g: 'invest', id: 'portfolios', ic: '💼', es: 'Carteras de práctica', en: 'Practice portfolios', k: 'carteras portafolio simuladas practica portfolios paper', run: function () { stage('portfolios'); }, ok: function () { return !!W.KhipuPortfolios; } },
      { g: 'invest', id: 'broker', ic: '💳', es: 'Mi cuenta (bróker)', en: 'My account (broker)', k: 'cuenta broker bróker invertir comprar vender alpaca account invest buy sell posiciones', run: function () { stage('broker'); } },
      { g: 'invest', id: 'committee', ic: '🏛', es: 'Comité de inversión', en: 'Investment committee', k: 'comite committee veredicto memo pizarra board', run: function () { W.KhipuCommittee.open(); }, ok: function () { return !!(W.KhipuCommittee && W.KhipuCommittee.open); } },
      { g: 'invest', id: 'risk', ic: '🛡', es: 'Riesgo de cartera', en: 'Portfolio risk', k: 'riesgo var risk cartera griegas vega', run: function () { W.KhipuRisk.open({ tab: 'var' }); }, ok: function () { return !!(W.KhipuRisk && W.KhipuRisk.open); } },
      { g: 'invest', id: 'clients', ic: '👥', es: 'Clientes', en: 'Clients', k: 'clientes clients aprobaciones approvals', run: function () { W.KhipuClients.open(); }, ok: function () { return !!(W.KhipuClients && W.KhipuClients.open); } },
      { g: 'invest', id: 'scalp', ic: '⚡', es: 'Scalping', en: 'Scalping', k: 'scalping rapido trading corto', run: function () { stage('scalp'); } },
      { g: 'discover', id: 'insights', ic: '💡', es: 'Oportunidades', en: 'Opportunities', k: 'oportunidades insights riesgos hipergrafo', run: function () { stage('insights'); } },
      { g: 'discover', id: 'screener', ic: '🔥', es: 'Explosivas', en: 'Breakouts', k: 'explosivas breakouts momentum screener', run: function () { stage('screener'); } },
      { g: 'discover', id: 'xray', ic: '🔬', es: 'X-Ray de una empresa', en: 'Company X-Ray', k: 'xray x-ray radiografia desarmar', run: function () { if (sel) stage('xray', sel); else stage('pick', { for: 'xray' }); } },
      { g: 'discover', id: 'compare', ic: '⇄', es: 'Comparar empresas', en: 'Compare companies', k: 'comparar compare vs versus', run: function () { stage('pick', { for: 'compare', a: sel }); } },
      { g: 'discover', id: 'research', ic: '🧠', es: 'Investigar a fondo', en: 'Deep research', k: 'investigar research investigacion analistas', run: function () { stage('pick', { for: 'research' }); } },
      { g: 'discover', id: 'sim', ic: '◉', es: 'Simular una caída', en: 'Simulate a failure', k: 'simular shock caida colapso', run: function () { if (sel) stage('sim', { id: sel, kind: 'collapse' }); else stage('pick', { for: 'sim' }); } },
      { g: 'discover', id: 'canvas', ic: '✦', es: 'Gráfico a pedido', en: 'Chart on demand', k: 'grafico canvas lienzo chart dibujar', run: function () { stage('canvas'); } },
      { g: 'help', id: 'agents', ic: '◍', es: 'Tus agentes', en: 'Your agents', k: 'agentes agents mascotas analista radar cadena tecnico comite', run: function () { stage('agents'); }, ok: function () { return !!_custom.agents; } },
      { g: 'help', id: 'brief', ic: '☀️', es: 'Brief de hoy', en: 'Today’s brief', k: 'brief matinal resumen hoy today morning', run: function () { W._briefOpen(); _raise('brief-ov', 7600); }, ok: function () { return typeof W._briefOpen === 'function'; } },
      { g: 'help', id: 'guia', ic: '❓', es: 'Guía', en: 'Guide', k: 'guia ayuda help guide como usar', run: function () { stage('guia'); } },
      { g: 'help', id: 'sistema', ic: '🩺', es: 'Sistema', en: 'System', k: 'sistema diagnostico salud health gasto ia registro', run: function () { _openSistemaOS(); }, ok: function () { return typeof W.openSistema === 'function'; } },
      { g: 'help', id: 'mcp', ic: '🤖', es: 'Conectar IAs', en: 'Connect AIs', k: 'mcp conectar ias claude chatgpt connect', run: function () { W.KhipuMCP.open('connect'); }, ok: function () { return !!(W.KhipuMCP && W.KhipuMCP.open); } },
      { g: 'help', id: 'universe', ic: '🪐', es: 'Universo 3D', en: '3D universe', k: 'universo 3d universe', run: function () { W._go3D(); }, ok: function () { return typeof W._go3D === 'function'; } },
    ];
    return all.filter(function (s) { try { return !s.ok || s.ok(); } catch (e) { return false; } });
  }
  function _runScreen(id) {
    var s = screens().filter(function (x) { return x.id === id; })[0];
    if (!s) return false;
    try { s.run(); } catch (e) { try { console.warn('[Khipus OS]', id, e); } catch (x) {} }
    return true;
  }

  // Re-etiqueta la cáscara en el idioma ACTUAL (al abrir y al cambiar de idioma desde la barra)
  function relabelShell(ov) {
    ov = ov || document.getElementById('bcp-ov');
    if (!ov) return;
    var labels = {};
    actChips().forEach(function (c) { labels[c[0]] = c[1] + ' ' + L(c[2], c[3]); });
    ov.querySelectorAll('.bcp-act').forEach(function (b) {
      var k = b.getAttribute('data-act');
      if (labels[k]) b.textContent = labels[k];
    });
    var inp = ov.querySelector('#bcp-input');
    if (inp) {
      inp.setAttribute('placeholder', L('Pregúntale a Khipu…', 'Ask Khipu…'));
      if (_inv) _paintInvoke(false);   // el agente invocado sigue en la barra (otro idioma)
      inp.setAttribute('title', L('Escribe tu pregunta. «/» abre los comandos y «@» le habla a un agente.', 'Type your question. “/” opens the commands and “@” talks to an agent.'));
      inp.setAttribute('aria-label', L('Pregúntale a Khipu', 'Ask Khipu'));
    }
    var setT = function (sel, es, en) {
      var el = ov.querySelector(sel);
      if (el) { el.setAttribute('title', L(es, en)); el.setAttribute('aria-label', L(es, en)); }
    };
    setT('#bcp-close', 'Cerrar', 'Close');
    setT('#bcp-send', 'Enviar', 'Send');
    setT('#bcp-mic', 'Hablar con Khipu', 'Talk to Khipu');
    var cd = ov.querySelector('#bcp-chatdock');
    if (cd) {
      cd.querySelector('.ttl').textContent = '💬 ' + L('Conversación con Khipu', 'Conversation with Khipu');
      cd.querySelector('[data-cd="full"]').textContent = L('⤢ Ampliar', '⤢ Expand');
      cd.querySelector('[data-cd="min"]').textContent = cd.classList.contains('min') ? L('▴ Mostrar', '▴ Show') : L('▾ Ocultar', '▾ Hide');
    }
    // ── barra superior ──
    var sk = ov.querySelector('#kos-search');
    if (sk) {
      sk.querySelector('.kos-kbd').textContent = _isMac() ? '⌘K' : 'Ctrl K';
      sk.querySelector('.tx').textContent = L('Busca una empresa o abre una pantalla…', 'Search a company or open a screen…');
      sk.setAttribute('aria-label', L('Buscar empresas, pantallas y acciones', 'Search companies, screens and actions'));
    }
    var mb = ov.querySelector('#kos-more');
    if (mb) { mb.querySelector('.tx').textContent = L('Herramientas', 'Tools'); mb.setAttribute('title', L('Todas las herramientas y pantallas', 'All tools and screens')); mb.setAttribute('aria-label', L('Herramientas: todas las pantallas', 'Tools: all screens')); }
    var lb = ov.querySelector('#kos-lang');
    if (lb) { lb.textContent = ckLang() === 'en' ? 'EN' : 'ES'; lb.setAttribute('title', L('Idioma: español — cambiar a English', 'Language: English — switch to español')); lb.setAttribute('aria-label', lb.getAttribute('title')); }
    _paintThemeBtn(); _paintAgentsBtn(); _paintMe();
    if (deskActive()) desk().relabel();   // títulos de ventanas y barra de tareas en el idioma actual
    var st = ov.querySelector('#bcp-state');
    var tx = st && st.querySelector('.txt');
    // solo el estado de reposo se re-traduce (no pisar "Escuchando"/"Pensando")
    if (tx && (!st.className || !tx.textContent)) tx.textContent = L('Listo', 'Ready');
    _paintChatHeader();
    _balRefresh();
  }
  function _paintThemeBtn() {
    var b = document.getElementById('kos-theme'); if (!b) return;
    var dark = document.body.classList.contains('dark');
    b.innerHTML = dark ? SVG.sun : SVG.moon;
    b.setAttribute('title', dark ? L('Cambiar a tema claro', 'Switch to light theme') : L('Cambiar a tema oscuro', 'Switch to dark theme'));
    b.setAttribute('aria-label', b.getAttribute('title'));
  }
  function _paintAgentsBtn() {
    var b = document.getElementById('kos-agents'); if (!b) return;
    var ag = _agentsOn();
    b.innerHTML = ag.length ? _stackHTML(ag, 24) : _mascot('khipu', 24);
    b.setAttribute('title', L('Tus agentes: qué hace cada uno y cómo participan', 'Your agents: what each one does and how they take part'));
    b.setAttribute('aria-label', L('Tus agentes', 'Your agents'));
  }
  function _actorName() { try { return (localStorage.getItem('khipu_actor') || '').trim(); } catch (e) { return ''; } }
  function _initials() {
    var p = _actorName().split(/\s+/).filter(Boolean);
    if (!p.length) return '?';
    return (p[0].charAt(0) + (p.length > 1 ? p[p.length - 1].charAt(0) : '')).toUpperCase();
  }
  function _paintMe() {
    var b = document.getElementById('kos-me'); if (!b) return;
    b.textContent = _initials();
    b.setAttribute('title', (_actorName() || L('Invitado', 'Guest')) + ' — ' + L('menú', 'menu'));
    b.setAttribute('aria-label', b.getAttribute('title'));
  }
  function _toggleTheme() {
    var b = document.getElementById('theme-toggle');   // el de la app: guarda eco_theme y re-colorea el mapa
    if (b) b.click(); else document.body.classList.toggle('dark');
    _paintThemeBtn();
  }
  function _toggleLang() {
    var b = document.getElementById('lang-toggle');    // el de la app: LANG + eco_lang + applyLang
    if (b) b.click();
    else { try { localStorage.setItem('eco_lang', ckLang() === 'en' ? 'es' : 'en'); } catch (e) {} }
    relabelShell();
    _paintHome(true);
    if (_popFor) _popClose();
    if (palIsOpen()) palRender();
  }

  // ── menús desplegables (Más ▾ y el de tus iniciales) ──
  var _popEl = null, _popFor = null;
  function _popIsOpen() { return !!_popEl; }
  function _popClose() {
    if (_popEl && _popEl.parentNode) _popEl.parentNode.removeChild(_popEl);
    _popEl = null;
    if (_popFor) { _popFor.classList.remove('on'); _popFor.setAttribute('aria-expanded', 'false'); _popFor = null; }
  }
  function _popOpen(btn, cls, html, align) {
    var ov = ensureShell();
    var again = _popFor === btn;
    _popClose();
    if (again) return null;   // segundo clic en el mismo botón = cerrar
    var el = document.createElement('div');
    el.className = 'kos-pop ' + cls; el.setAttribute('role', 'menu'); el.innerHTML = html;
    ov.appendChild(el);
    var r = btn.getBoundingClientRect(), ow = el.offsetWidth, vw = window.innerWidth || 1024;
    var left = align === 'right' ? r.right - ow : r.left + r.width / 2 - ow / 2;
    el.style.left = Math.round(Math.max(8, Math.min(vw - ow - 8, left))) + 'px';
    el.style.top = Math.round(r.bottom + 8) + 'px';
    btn.classList.add('on'); btn.setAttribute('aria-expanded', 'true');
    _popEl = el; _popFor = btn;
    return el;
  }
  function _openMore(btn) {
    var en = ckLang() === 'en', by = {};
    screens().forEach(function (s) { (by[s.g] = by[s.g] || []).push(s); });
    var html = GROUPS.filter(function (g) { return by[g[0]]; }).map(function (g) {
      return '<div class="grp"><div class="kos-ph">' + esc(en ? g[2] : g[1]) + '</div>' + by[g[0]].map(function (s) {
        return '<button type="button" class="kos-mi" role="menuitem" data-s="' + esc(s.id) + '"><span class="ic">' + esc(s.ic) + '</span><span class="tx">' + esc(en ? s.en : s.es) + '</span></button>';
      }).join('') + '</div>';
    }).join('');
    var el = _popOpen(btn, 'kos-more', html, 'center');
    if (!el) return;
    el.addEventListener('click', function (e) {
      var b = e.target.closest && e.target.closest('[data-s]'); if (!b) return;
      _popClose(); _runScreen(b.getAttribute('data-s'));
    });
    var first = el.querySelector('.kos-mi'); if (first) try { first.focus({ preventScroll: true }); } catch (x) {}
  }
  function _openMe(btn) {
    var name = _actorName(), mode = _mode();
    var html = '<div class="kos-mehd"><button type="button" class="kos-av" tabindex="-1" aria-hidden="true">' + esc(_initials()) + '</button>' +
      '<div style="min-width:0;flex:1"><div class="nm">' + esc(name || L('Invitado', 'Guest')) + '</div>' +
      '<div class="sb"><a href="#" data-k="name" style="color:var(--os-accent);text-decoration:none">' + esc(name ? L('Cambiar nombre', 'Change name') : L('Ponte un nombre', 'Add your name')) + '</a></div></div></div>';
    if (mode) {
      html += '<div class="kos-segl">' + esc(L('Cómo te explica Khipu', 'How Khipu explains things')) + '</div>' +
        '<div class="kos-seg" role="group"><button type="button" data-mode="simple" class="' + (mode === 'simple' ? 'on' : '') + '">' + esc(L('Simple', 'Simple')) + '</button>' +
        '<button type="button" data-mode="pro" class="' + (mode === 'pro' ? 'on' : '') + '">Pro</button></div>' +
        '<div class="kos-segl" style="padding-top:0;margin-bottom:4px">' + esc(mode === 'pro' ? L('Cifras, rangos y horizonte.', 'Figures, ranges and horizon.') : L('Lenguaje llano y una conclusión clara.', 'Plain language and a clear conclusion.')) + '</div>';
    }
    // en el teléfono la barra no tiene sitio: idioma, tema y saldo viven aquí
    html += '<div class="kos-mob"><div class="kos-sep"></div>' +
      '<button type="button" class="kos-mi" data-k="bal"><span class="ic" id="kos-me-bal-ic">' + esc(_bal.ic || '🧪') + '</span><span class="tx" id="kos-me-bal">' + esc(_balText()) + '</span></button>' +
      '<button type="button" class="kos-mi" data-k="lang"><span class="ic">🌐</span><span class="tx">' + esc(ckLang() === 'en' ? 'Cambiar a español' : 'Switch to English') + '</span></button>' +
      '<button type="button" class="kos-mi" data-k="theme"><span class="ic">' + (document.body.classList.contains('dark') ? '☀️' : '🌙') + '</span><span class="tx">' + esc(document.body.classList.contains('dark') ? L('Tema claro', 'Light theme') : L('Tema oscuro', 'Dark theme')) + '</span></button></div>';
    html += '<div class="kos-sep"></div>' +
      (_custom.agents ? '<button type="button" class="kos-mi" data-k="agents"><span class="ic">◍</span><span class="tx">' + esc(L('Tus agentes', 'Your agents')) + '</span></button>' : '') +
      (typeof window.openSistema === 'function' ? '<button type="button" class="kos-mi" data-k="sistema"><span class="ic">🩺</span><span class="tx">' + esc(L('Sistema', 'System')) + '</span></button>' : '') +
      '<div class="kos-sep"></div>' +
      '<button type="button" class="kos-mi" data-k="classic"><span class="ic">▭</span><span class="tx">' + esc(L('Vista clásica', 'Classic view')) + '</span><span class="hint">' + esc(L('pestañas', 'tabs')) + '</span></button>';
    var el = _popOpen(btn, 'kos-me', html, 'right');
    if (!el) return;
    el.addEventListener('click', function (e) {
      var m = e.target.closest && e.target.closest('[data-mode]');
      if (m) { _setMode(m.getAttribute('data-mode')); _popClose(); _paintChatHeader(); return; }
      var b = e.target.closest && e.target.closest('[data-k]'); if (!b) return;
      var k = b.getAttribute('data-k');
      if (k === 'name') { e.preventDefault(); _editName(el); return; }
      _popClose();
      if (k === 'agents') stage('agents');
      else if (k === 'sistema') _openSistemaOS();
      else if (k === 'classic') toClassicView();
      else if (k === 'lang') _toggleLang();
      else if (k === 'theme') _toggleTheme();
      else if (k === 'bal') _balGo();
    });
  }
  function _editName(el) {
    var sb = el.querySelector('.kos-mehd .sb'); if (!sb) return;
    sb.innerHTML = '<input type="text" maxlength="40" autocomplete="name" placeholder="' + esc(L('Tu nombre', 'Your name')) + '" value="' + esc(_actorName()) + '">';
    var i = sb.querySelector('input'); i.focus(); i.select();
    i.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter') return;
      e.preventDefault();
      var v = (i.value || '').trim().slice(0, 40);
      try { if (v) localStorage.setItem('khipu_actor', v); } catch (x) {}
      _popClose(); _paintMe();
    });
  }

  // ── saldo de práctica en la barra (NUNCA pide el PIN; insignia 🧪/🔴 obligatoria) ──
  // ic = insignia de la fila del menú (teléfono/tablet): 🧪 práctica/papel · 🔴 DINERO REAL — va APARTE del
  // texto (antes la columna del ícono era un 🧪 fijo: un saldo de dinero real salía con insignia de práctica)
  var _bal = { t: null, seq: 0, text: '', ic: '🧪' };
  function _simBalance() {
    var P = window.KhipuPortfolios; if (!P || !P._list || !P._stats) return null;
    var list = []; try { list = P._list() || []; } catch (e) { list = []; }
    if (!list.length) return { none: true };
    var act = null; try { act = localStorage.getItem('kh_pf_active'); } catch (e) {}
    var pf = list.filter(function (x) { return x && x.id === act; })[0] || list[0];
    var st = null; try { st = P._stats(pf); } catch (e) { st = null; }
    if (!st || !isFinite(+st.total)) return null;
    return { name: pf.name, total: +st.total, plPct: +st.plPct || 0, n: (pf.positions || []).length, count: list.length };
  }
  function _balText() { return _bal.text || L('Cuenta de práctica', 'Practice account'); }
  function _balPaint(o) {
    var el = document.getElementById('kos-bal'); if (!el) return;
    if (!o) { el.style.display = 'none'; _bal.text = ''; _bal.ic = '🧪'; _balPaintMenu(); return; }
    el.style.display = '';
    el.querySelector('.l').innerHTML = o.label;
    var v = el.querySelector('.v'); v.textContent = o.value; v.classList.toggle('sm', !!o.small);
    el.setAttribute('title', o.title); el.setAttribute('aria-label', o.title);
    el.setAttribute('data-go', o.go);
    _bal.text = o.plain; _bal.ic = o.ic || '🧪';
    _balPaintMenu();
  }
  // la fila del saldo del menú (si está abierto): texto e insignia SIEMPRE juntos
  function _balPaintMenu() {
    var mb = document.getElementById('kos-me-bal'); if (mb) mb.textContent = _balText();
    var mi = document.getElementById('kos-me-bal-ic'); if (mi) mi.textContent = _bal.ic || '🧪';
  }
  function _balRefresh() {
    var el = document.getElementById('kos-bal'); if (!el) return;
    var my = ++_bal.seq;
    var sim = _simBalance();
    if (!sim) _balPaint(null);
    else if (sim.none) _balPaint({ label: '🧪 <span class="lt">' + esc(L('Práctica', 'Practice')) + '</span>', value: L('Crear cartera', 'Create a portfolio'), small: true, go: 'portfolios',
      title: L('Aún no tienes carteras de práctica. Crea una con dinero simulado (no es dinero real).', 'You have no practice portfolios yet. Create one with simulated money (not real money).'),
      plain: L('Práctica: crear cartera', 'Practice: create a portfolio') });
    else _balPaint({ label: '🧪 <span class="lt">' + esc(L('Cuenta de práctica', 'Practice account')) + '</span>', value: _money(sim.total), go: 'portfolios',
      title: L('Cartera simulada «' + sim.name + '» · ' + sim.n + ' posiciones · valor con precios en vivo (si falta un precio se usa el de compra). No es dinero real.',
               'Simulated portfolio “' + sim.name + '” · ' + sim.n + ' positions · valued at live prices (if a price is missing, the purchase price is used). Not real money.'),
      plain: L('Práctica: ', 'Practice: ') + _money(sim.total) });
    var hasPin = false; try { hasPin = !!(window._tradePinStored && window._tradePinStored()); } catch (e) {}
    if (!hasPin || !window._tradeAccountInfo) return;
    // con PIN guardado: la cuenta del bróker, SIN diálogo (interactive=false)
    Promise.resolve(window._tradeAccountInfo(false, false)).then(function (a) {
      if (my !== _bal.seq || !a || a.error || !isFinite(+a.equity)) return null;
      if (typeof a.paper === 'boolean') return { a: a, paper: a.paper };
      return (window._tradeStatusInfo ? window._tradeStatusInfo() : Promise.resolve(null)).then(function (s) {
        return (s && typeof s.paper === 'boolean') ? { a: a, paper: s.paper } : null;   // sin saber papel/real NO se muestra
      });
    }).then(function (r) {
      if (!r || my !== _bal.seq) return;
      var hh = new Date().toLocaleTimeString(ckLang() === 'en' ? 'en-US' : 'es-AR', { hour: '2-digit', minute: '2-digit' });
      _balPaint(r.paper
        ? { label: '<span class="kos-badge paper">🧪 ' + esc(L('PAPEL', 'PAPER')) + '</span><span class="lt">' + esc(L('Bróker', 'Broker')) + '</span>', value: _money(r.a.equity), go: 'broker',
            title: L('Cuenta del bróker en modo papel (SIMULADO) · actualizado ' + hh, 'Broker account in paper mode (SIMULATED) · updated ' + hh),
            ic: '🧪', plain: L('Bróker (papel): ', 'Broker (paper): ') + _money(r.a.equity) }
        : { label: '<span class="kos-badge real">🔴 ' + esc(L('DINERO REAL', 'REAL MONEY')) + '</span>', value: _money(r.a.equity), go: 'broker',
            title: L('Cuenta del bróker con DINERO REAL · actualizado ' + hh, 'Broker account with REAL MONEY · updated ' + hh),
            ic: '🔴', plain: L('Bróker (dinero real): ', 'Broker (real money): ') + _money(r.a.equity) });
    }).catch(function () {});
  }
  function _balGo() {
    var el = document.getElementById('kos-bal');
    var go = (el && el.getAttribute('data-go')) || 'portfolios';
    if (go === 'broker') stage('broker'); else stage('portfolios');
  }
  function _balStart() { _balStop(); _balRefresh(); _bal.t = setInterval(function () { if (open && !document.hidden) _balRefresh(); }, 45000); }
  function _balStop() { if (_bal.t) { clearInterval(_bal.t); _bal.t = null; } }

  // ── shell (una vez) ──
  function ensureShell() {
    ensureStyles();
    if (window.xrayEnsureStyles) window.xrayEnsureStyles();
    var ov = document.getElementById('bcp-ov');
    if (ov) return ov;
    ov = document.createElement('div');
    ov.id = 'bcp-ov';
    ov.innerHTML =
      // BARRA SUPERIOR mínima (Khipus OS): Khipu · ⌘K buscar · Más ▾ · agentes · saldo · ES/EN · tema · iniciales
      '<div id="bcp-top">' +
        '<div class="kos-brand">' +
          '<div id="bcp-orb-wrap"><canvas id="bcp-orb-canvas" width="64" height="64"></canvas></div>' +
          '<div id="bcp-idwrap"><div id="bcp-word" title="Khipus Finance Intelligence">Khipus<span class="sub">Finance Intelligence</span></div>' +
            '<div id="bcp-state"><span class="dot"></span><span class="txt"></span></div></div>' +
        '</div>' +
        '<div class="kos-mid">' +
          '<button type="button" class="kos-search" id="kos-search"><span class="kos-kbd"></span><span class="tx"></span></button>' +
          '<button type="button" class="kos-btn kos-more-btn" id="kos-more" aria-haspopup="menu" aria-expanded="false">' + SVG.tools + '<span class="tx"></span>' + SVG.chev + '</button>' +
        '</div>' +
        '<div class="kos-right">' +
          '<button type="button" class="kos-btn kos-agbtn" id="kos-agents"></button>' +
          '<button type="button" class="kos-bal" id="kos-bal"><span class="l"></span><span class="v"></span></button>' +
          '<button type="button" class="kos-btn kos-round" id="kos-lang"></button>' +
          '<button type="button" class="kos-btn kos-round" id="kos-theme"></button>' +
          '<button type="button" class="kos-av" id="kos-me" aria-haspopup="menu" aria-expanded="false"></button>' +
          '<button type="button" class="bcp-iconbtn" id="bcp-close">✕</button>' +
        '</div>' +
      '</div>' +
      // fila de chips de la Cabina vieja: OCULTA (se conserva el nodo y sus escuchadores)
      '<div id="bcp-actions">' +
        actChips().map(function (c) {
          return '<button class="bcp-act" data-act="' + c[0] + '"></button>';
        }).join('') +
      '</div>' +
      '<div id="bcp-stage"></div>' +
      '<div id="bcp-chatdock"><div class="hd"><span class="ttl"></span><span class="sp"></span>' +
        '<button type="button" data-cd="full"></button><button type="button" data-cd="min"></button></div>' +
        '<div class="bd"></div></div>' +
      // barra de entrada: en Khipus OS (≥ 1100 px) se muda a la columna central del chat
      '<div id="bcp-barwrap"><div id="bcp-bar">' +
        '<span id="kos-inv" hidden></span>' +
        '<input id="bcp-input" type="text" autocomplete="off" spellcheck="false">' +
        '<button type="button" class="bcp-iconbtn" id="bcp-mic">' + SVG.mic + '</button>' +
        '<button type="button" class="bcp-iconbtn" id="bcp-send">' + SVG.send + '</button>' +
      '</div></div>' +
      '<div id="kos-pal" role="dialog" aria-modal="true"></div>';
    document.body.appendChild(ov);
    _syncClassicClass(ov);
    relabelShell(ov);

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
        if (act === 'scalp') return stage('scalp');
        if (act === 'crypto') return stage('crypto');
        if (act === 'market') return stage('market');
        if (act === 'geo') return stage('geo');
        if (act === 'space') return stage('space');
        if (act === 'simulation') return stage('simulation');
        // acciones que necesitan una empresa → prellenar la barra (enseña la sintaxis)
        var sel = (window._liveSelectedNode && window._liveSelectedNode()) || null;
        var name = sel && window.NODE_BY_ID && window.NODE_BY_ID[sel] ? window.NODE_BY_ID[sel].label : '';
        // sin empresa elegida, estos chips abren un SELECTOR (antes solo prellenaban la
        // barra y parecía que "el botón no hacía nada" — feedback 2026-10-04)
        if (act === 'xray') return name ? stage('xray', sel) : stage('pick', { for: 'xray' });
        if (act === 'sim') return name ? stage('sim', { id: sel, kind: 'collapse' }) : stage('pick', { for: 'sim' });
        if (act === 'compare') return stage('pick', { for: 'compare', a: name ? sel : null });
        if (act === 'deep') return stage('pick', { for: 'research' });
        input.focus();
      });
    });

    var input = ov.querySelector('#bcp-input');
    if (window.KhipuPick) window.KhipuPick.chatMenu(input);   // menú de "/" y "@" (antes del Enter que envía)
    ov.querySelector('#bcp-send').addEventListener('click', function () { submit(); });
    input.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.isComposing) { e.preventDefault(); submit(); } });
    // "solo chat" (tablet/celular): escribir en la barra —o que otro módulo la llene y dispare 'input', como
    // "Pregúntale a Radar" de oswindows.js— destapa la conversación (antes se escribía a ciegas bajo una ventana)
    input.addEventListener('input', function () { _revealChat(); });
    ov.querySelector('#bcp-mic').addEventListener('click', toggleMic);
    ov.querySelector('#bcp-close').addEventListener('click', close);
    ov.querySelectorAll('#bcp-chatdock [data-cd]').forEach(function (b) {
      b.addEventListener('click', function () {
        var d = document.getElementById('bcp-chatdock');
        if (b.getAttribute('data-cd') === 'full') return stage('chat');
        d.classList.toggle('min'); relabelShell();
      });
    });
    function submit() {
      var v = (input.value || '').trim(); if (!v) return; input.value = '';
      // agente INVOCADO: sigue en la conversación hasta que lo despidas (✕); un @ escrito a mano manda
      if (_inv && AGENT_TOK[_inv] && v.charAt(0) !== '@' && v.charAt(0) !== '/') v = (ckLang() === 'en' ? AGENT_TOK[_inv][1] : AGENT_TOK[_inv][0]) + ' ' + v;
      ask(v);
    }

    // barra superior
    ov.querySelector('#kos-search').addEventListener('click', function () { palOpen(''); });
    ov.querySelector('#kos-more').addEventListener('click', function (e) { e.stopPropagation(); _openMore(this); });
    ov.querySelector('#kos-me').addEventListener('click', function (e) { e.stopPropagation(); _openMe(this); });
    ov.querySelector('#kos-agents').addEventListener('click', function () { _popClose(); stage('agents'); });
    ov.querySelector('#kos-bal').addEventListener('click', function () { _popClose(); _balGo(); });
    ov.querySelector('#kos-lang').addEventListener('click', function () { _toggleLang(); });
    ov.querySelector('#kos-theme').addEventListener('click', function () { _toggleTheme(); });
    // clic fuera de un menú lo cierra
    ov.addEventListener('pointerdown', function (e) {
      if (!_popEl) return;
      if (_popEl.contains(e.target) || (_popFor && _popFor.contains(e.target))) return;
      _popClose();
    }, true);
    window.addEventListener('resize', function () { if (_popEl) _popClose(); });
    // el tema puede cambiar desde otro lado (app clásica): el ícono ☾/☀ lo sigue
    try { new MutationObserver(function () { _paintThemeBtn(); }).observe(document.body, { attributes: true, attributeFilter: ['class'] }); } catch (e) {}
    // agentes encendidos/apagados (ventana "Tus agentes") → pila de mascotas y encabezado del chat
    window.addEventListener('khipu:agentprefs', function () { _paintAgentsBtn(); _paintChatHeader(); _paintAgentRow(); });
    // carteras o nombre cambiados en otra pestaña
    window.addEventListener('storage', function (e) {
      if (!e || !e.key) return;
      if (e.key === 'kh_portfolios' || e.key === 'kh_pf_active') _balRefresh();
      if (e.key === 'khipu_actor') _paintMe();
      if (e.key === 'kh_desk_mode') _deskModeFromStorage();   // ⊞ → "una sola pantalla" en otra pestaña
    });

    mountCockpitOrb();
    return ov;
  }
  // la Cabina clásica (kh_desk_mode=off) siempre en oscuro: sus escenas tienen colores fijos oscuros
  function _syncClassicClass(ov) {
    ov = ov || document.getElementById('bcp-ov'); if (!ov) return;
    ov.classList.toggle('kos-classic', !desk());
  }

  // ── Mascota de Khipu en la barra (Khipus OS). Sin engine/mascot.js cae al orbe de voz
  // (engine/orb.js) o al orbe pequeño. La mascota no tiene bucle de animación → más liviano.
  function mountCockpitOrb() {
    var wrap = document.getElementById('bcp-orb-wrap');
    if (!wrap) return;
    if (window.KhipuMascot && window.KhipuMascot.svg) {
      if (!wrap.querySelector('.km')) {
        stopCockpitOrb();
        Array.prototype.forEach.call(wrap.children, function (c) { c.style.display = 'none'; });
        var sp = document.createElement('span'); sp.innerHTML = _mascot('khipu', 30); wrap.appendChild(sp.firstChild);
      }
      return;
    }
    if (window.BixbyOrb && window.BixbyOrb.mount) {
      try {
        var old = document.getElementById('bcp-orb-canvas');
        if (old) old.style.display = 'none';
        window.BixbyOrb.mount(wrap);
        window.BixbyOrb.start();
        return;
      } catch (e) { /* cae al fallback */ }
    }
    if (window.registerBixbyOrb) window.registerBixbyOrb('bcp-orb-canvas', 30);
    else { var c2 = document.getElementById('bcp-orb-canvas'); if (c2) { c2.style.display = 'none'; if (!wrap.querySelector('.kos-orbf')) wrap.insertAdjacentHTML('beforeend', '<span class="kos-orbf"></span>'); } }
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
    // la mascota de Khipu "piensa" (barra y encabezado del chat)
    try {
      document.querySelectorAll('#bcp-ov .kos-brand .km, #bcp-ov .kos-chathd-m .km').forEach(function (m) { m.classList.toggle('km-think', mode === 'think'); });
    } catch (e) {}
  }
  // ── micrófono / voz ──
  function toggleMic() {
    var btn = document.getElementById('bcp-mic');
    if (!window.BixbyVoice) { setState('', L('Voz no disponible', 'Voice unavailable')); return; }
    var on = window.BixbyVoice.isConnected;
    if (on) { window.BixbyVoice.stop && window.BixbyVoice.stop(); if (btn) btn.classList.remove('on'); setState('', L('Listo', 'Ready')); }
    else { window.BixbyVoice.toggle && window.BixbyVoice.toggle(); if (btn) btn.classList.add('on'); setState('live', L('Escuchando', 'Listening')); }
  }

  // ── ADOPCIÓN de paneles reales: el grafo y la terminal se MUEVEN al
  // escenario de la Cabina (con un placeholder para devolverlos intactos al
  // salir). Así Khipu los muestra EN SU PANTALLA, no te lleva a otra pestaña.
  var _adopted = [];
  var _adoptCtx = null;   // ESCRITORIO (engine/desktop.js): ventana que está adoptando ahora

  // sin argumento devuelve TODO; con id de ventana, solo lo que adoptó esa ventana
  function restoreAdopted(winId) {
    var hadGraph = false, keep = [];
    while (_adopted.length) {
      var a = _adopted.pop();
      if (winId && a.win !== winId) { keep.push(a); continue; }
      try {
        if (a.el.tagName === 'MAIN') hadGraph = true;
        a.el.style.display = a.prevDisplay;
        if (a.ph.parentNode) a.ph.parentNode.replaceChild(a.el, a.ph);
      } catch (e) {}
    }
    while (keep.length) _adopted.push(keep.pop());
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
    _adopted.push({ el: el, ph: ph, prevDisplay: el.style.display, win: _adoptCtx });
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
  var _curKind = null;   // escena actual (para re-pintar el inicio al reabrir)
  var CHIP_KINDS = ['graph', 'terminal', 'insights', 'canvas', 'deep', 'broker', 'crypto', 'market', 'geo', 'space', 'simulation', 'tkg', 'guia', 'scalp'];
  // escenas que pinta la propia Cabina (además de ADOPT_TABS y de las registradas con registerKind)
  var BUILTIN_KINDS = ['broker', 'scalp', 'crypto', 'pick', 'xray', 'compare', 'agentsim', 'research', 'sim', 'screener', 'insights', 'canvas', 'deep', 'graph', 'terminal'];
  // escenas viejas con colores oscuros FIJOS: su ventana lleva .kd-legacy-dark (isla oscura legible en tema claro)
  // 2026-10-10: xray, insights y portfolios ya pintan con tokens --os-* (siguen el tema claro/oscuro)
  var LEGACY_DARK = ['broker', 'scalp', 'screener', 'deep', 'research', 'agentsim', 'compare', 'sim', 'pick'];

  // ESCRITORIO KHIPU (engine/desktop.js, 2026-10-04): si está activo, cada
  // escena se abre como VENTANA (movible, redimensionable, barra de tareas).
  // Khipus OS (≥ 1100 px): el chat vive en la columna central y las ventanas en los
  // flancos. Si no (kh_desk_mode=off o sin el módulo), la Cabina clásica de una sola
  // pantalla. Una sola puerta: todo pasa por stage().
  function desk() {
    var D = window.KhipuDesk;
    return (D && D.enabled()) ? D : null;
  }
  function deskActive() { var D = desk(); return !!(D && D.active()); }
  function isCentered() { var D = desk(); return !!(D && D.active() && D.isCentered && D.isCentered()); }
  // ¿el hilo y la barra viven en #kd-center? (flancos ≥ 1100 px o "solo chat" en tablet/celular)
  function chatCentered() { var D = desk(); return !!(D && D.active() && (D.chatInCenter ? D.chatInCenter() : (D.isCentered && D.isCentered()))); }
  // "SOLO CHAT" (tablet/celular, < 1100 px): la conversación es la capa de abajo y las ventanas se abren
  // ENCIMA. Todo camino que lleva al chat (preguntar, 💬, "Pregúntale a…", escribir en la barra) la destapa:
  // las ventanas que la cubren pasan a la barra de tareas (un toque en su chip las devuelve; nada se pierde).
  // En el celular toda hoja la cubre; en la tablet, las que se cruzan con la tarjeta del chat.
  function _revealChat() {
    if (!open || !chatCentered() || isCentered()) return 0;
    var D = desk(); if (!D || !D.list || !D.minimize) return 0;
    var mob = !!(D.isMobile && D.isMobile()), cr = null;
    if (!mob && _centerBox) { try { cr = _centerBox.getBoundingClientRect(); } catch (e) { cr = null; } }
    var foc = D.focused ? D.focused() : null;
    var hit = D.list().filter(function (w) {
      if (w.min) return false;
      if (mob || !cr || !cr.width) return true;
      var o = D.get ? D.get(w.id) : null, r = null;
      try { r = o && o.el ? o.el.getBoundingClientRect() : null; } catch (e) { r = null; }
      if (!r || !r.width) return true;
      return r.left < cr.right && r.right > cr.left && r.top < cr.bottom && r.bottom > cr.top;
    });
    // la enfocada al final: refocusAfter() corre una sola vez (sin mostrar hojas de paso)
    hit.sort(function (a, b) { return (a.id === foc ? 1 : 0) - (b.id === foc ? 1 : 0); });
    hit.forEach(function (w) { try { D.minimize(w.id); } catch (e) {} });
    return hit.length;
  }
  // kh_desk_mode cambió en OTRA pestaña (desk() lee localStorage en cada llamada) y aquí el escritorio
  // sigue montado: desmontarlo con onLayout(false) saca la barra y el hilo de #kd-center ANTES de vaciarlo
  function _deskTeardownStale() {
    var K = window.KhipuDesk;
    if (!K || !K.active || !K.active() || (K.enabled && K.enabled())) return false;
    try { K.unmount(); } catch (e) {}
    var ov = document.getElementById('bcp-ov'); if (ov) ov.classList.remove('desk', 'kos-centered');
    return true;
  }
  // modo ventanas ⇄ Cabina clásica (aquí o, vía 'storage', en otra pestaña)
  function _onDeskMode(on) {
    var ov = document.getElementById('bcp-ov');
    if (ov) { ov.classList.toggle('desk', !!on); if (!on) ov.classList.remove('kos-centered'); }
    _syncClassicClass(ov);
    if (open) stage('empty');
  }
  function _deskModeFromStorage() {
    var K = window.KhipuDesk; if (!K || !K.enabled || !K.active) return;
    var on = !!K.enabled();
    if (on === !!K.active()) return;   // nada que cambiar aquí
    if (!on) _deskTeardownStale();
    _onDeskMode(on);
  }
  function _knownKind(kind) {
    return kind === 'chat' || kind === 'empty' || !!_custom[kind] || !!ADOPT_TABS[kind] || BUILTIN_KINDS.indexOf(kind) >= 0;
  }
  function stage(kind, arg, opts) {
    ensureShell();
    kind = kind || 'empty';
    // una escena que nadie registró (p. ej. 'agents' antes de que cargue su módulo) no hace nada:
    // antes caía al inicio dentro de una ventana con un título raro
    if (!_knownKind(kind)) { try { console.warn('[Khipus OS] escena no registrada:', kind); } catch (e) {} return null; }
    var s = document.getElementById('bcp-stage');
    if (!s) return;
    var D = desk();
    // kh_desk_mode='off' puesto en OTRA pestaña: aquí el escritorio sigue montado con la barra de entrada
    // dentro de #kd-center → se desmonta ANTES de que el camino clásico vacíe #bcp-stage (si no, la barra
    // y sus escuchadores se destruían y la pestaña quedaba sin dónde escribir hasta recargar)
    if (!D) _deskTeardownStale();
    _syncClassicClass();
    if (D) {
      if (!D.active()) {              // primer uso: el escenario clásico se vacía y pasa a escritorio
        restoreAdopted(); closeConfirmDialog(); _scalpStop();
        var ovd = document.getElementById('bcp-ov'); if (ovd) ovd.classList.add('desk');
        D.mount(s);
      }
      // con el chat al centro, "la conversación" ya está siempre a la vista: no hay ventana 💬
      if (kind === 'chat' && chatCentered()) { _revealChat(); _focusChat(); return; }
      if (kind === 'empty') {
        if (_demo.on) D.closeAll();   // la demostración arranca con el escritorio limpio
        _curKind = 'empty'; markActive(null); _placeThread('empty');
        _paintHome(Date.now() - _homeTs > 30000);   // fresco si pasó un rato; nunca dos veces seguidas
        return;
      }
      _paintHome(false);
      _curKind = kind;
      _placeThread(kind);
      opts = opts || {};
      if (_demo.on) { opts.solo = true; opts.max = true; }   // la demostración: una ventana a la vez, grande
      _noteEntity(kind, arg);
      return D.open(kind, arg, opts);
    }
    restoreAdopted();   // devolver cualquier panel adoptado antes de cambiar de escena
    closeConfirmDialog();   // un diálogo de orden pendiente no sobrevive al cambio de escena
    _scalpStop();       // detener el polling de scalping al cambiar de escena
    _curKind = kind;
    _placeThread(kind);
    markActive(kind === 'chat' ? null : (CHIP_KINDS.indexOf(kind) >= 0 ? kind : null));
    return render(s, kind, arg);
  }
  // la empresa de la escena → memoria corta del chat ("ella", "su proveedor", "este")
  function _noteEntity(kind, arg) {
    try {
      if (!window.KhipuChat || !window.KhipuChat.noteEntity) return;
      var id = null;
      if (kind === 'compare' && arg && arg.a) { window.KhipuChat.noteEntity(arg.b); id = arg.a; }
      else if (arg && typeof arg === 'object') id = arg.id || (arg.ticker && (resolveNode(arg.ticker) || {}).id);
      else if (typeof arg === 'string' && (['xray', 'sim', 'research', 'graph', 'terminal'].indexOf(kind) >= 0 || (_custom[kind] && _custom[kind].multi))) id = (resolveNode(arg) || {}).id;
      if (id) window.KhipuChat.noteEntity(id);
    } catch (e) {}
  }
  // pinta la escena `kind` DENTRO de `s` (el escenario clásico o el cuerpo de una ventana)
  function render(s, kind, arg) {
    if (kind === 'chat') return stageChat(s);
    if (kind === 'empty') return stageEmpty(s);
    if (_custom[kind]) return _renderCustom(s, kind, arg);
    if (kind === 'broker') return stageBroker(s, arg);
    if (kind === 'scalp') return stageScalp(s, arg);
    if (kind === 'crypto') return stageCrypto(s, arg);
    if (ADOPT_TABS[kind]) return stageAdoptTab(s, kind);
    if (kind === 'pick') return stagePick(s, arg);
    if (kind === 'xray') return stageXRay(s, arg);
    if (kind === 'compare') return stageCompare(s, arg);
    if (kind === 'agentsim') return stageAgentSim(s, arg);
    if (kind === 'research') return stageResearch(s, arg);
    if (kind === 'sim') return stageSim(s, arg);
    if (kind === 'screener') return stageScreener(s);
    if (kind === 'insights') return stageInsights(s);
    if (kind === 'canvas') return stageCanvas(s, arg);
    if (kind === 'deep') return stageDeep(s, arg);
    if (kind === 'graph') return stageGraph(s, arg);
    if (kind === 'terminal') return stageTerminal(s, arg);
    return stageEmpty(s);
  }

  // ── ESCRITORIO: título, ícono y limpieza por ventana ──
  // mismo ícono y nombre que el chip de la barra (actChips) para que el usuario los reconozca
  var KIND_META = {
    graph: ['🗺️', 'Grafo', 'Graph'], terminal: ['🖥️', 'Terminal', 'Terminal'],
    insights: ['💡', 'Oportunidades', 'Opportunities'], canvas: ['✦', 'Gráfico', 'Chart'], deep: ['🧠', 'Investigación', 'Research'],
    broker: ['💳', 'Mi cuenta', 'My account'], scalp: ['⚡', 'Scalping', 'Scalping'], crypto: ['💠', 'Cripto', 'Crypto'],
    market: ['📈', 'Mercado', 'Market'], geo: ['🌐', 'Geopolítica', 'Geopolitics'], space: ['🚀', 'Espacio', 'Space'],
    simulation: ['🔮', 'Simulación', 'Simulation'], tkg: ['⏱', 'Grafo Temporal', 'Temporal Graph'], guia: ['❓', 'Guía', 'Guide'],
    xray: ['🔬', 'X-Ray', 'X-Ray'], compare: ['⇄', 'Comparar', 'Compare'], sim: ['◉', 'Caída simulada', 'Simulated failure'],
    agentsim: ['🧪', 'Simulación por agentes', 'Agent simulation'], research: ['🧠', 'Investigación', 'Research'],
    screener: ['🔥', 'Explosivas', 'Breakouts'], chat: ['💬', 'Conversación', 'Conversation'],
    pick: ['🔎', 'Elegir empresa', 'Choose a company'], portfolios: ['💼', 'Carteras de práctica', 'Practice portfolios'],
  };

  /* ══ KHIPUS OS — REGISTRO DE VENTANAS NATIVAS (contrato §3.1 de docs/KHIPUS_OS.md) ══
     BixbyCockpit.registerKind(kind, {icon, es, en, multi, title(arg), render(body, arg), mascot?})
     - render pinta SOLO con body.querySelector (sin ids globales) y puede re-llamarse con otro arg.
     - multi:true → una ventana por empresa (arg.id): el kind se suma a multiKinds del escritorio.
     - mascot (opcional): id de mascota ('analista', 'cadena'…) para el ícono de la barra de título. */
  var _custom = {};
  var MULTI_KINDS = ['xray', 'sim'];
  function registerKind(kind, spec) {
    if (!kind || typeof kind !== 'string' || !spec || typeof spec.render !== 'function') return false;
    if (kind === 'chat' || kind === 'empty') return false;
    _custom[kind] = spec;
    KIND_META[kind] = [String(spec.icon || '▫'), String(spec.es || spec.en || kind), String(spec.en || spec.es || kind)];
    var i = MULTI_KINDS.indexOf(kind);
    if (spec.multi && i < 0) MULTI_KINDS.push(kind);
    else if (!spec.multi && i >= 0 && kind !== 'xray' && kind !== 'sim') MULTI_KINDS.splice(i, 1);
    if (window.KhipuDesk) window.KhipuDesk.configure({ multiKinds: MULTI_KINDS });
    return true;
  }
  function _renderCustom(s, kind, arg) {
    var spec = _custom[kind], host = s;
    // Cabina clásica (sin ventanas): un "← Inicio" arriba y la ventana nativa debajo
    if (!(s.classList && s.classList.contains('kd-body'))) {
      s.innerHTML = backBar(winTitle(kind, arg)) + '<div class="bcp-inner kos-native"></div>';
      host = s.querySelector('.kos-native');
    }
    try { spec.render(host, arg); }
    catch (e) { host.innerHTML = '<div class="bcp-loading" style="color:var(--os-bad)">⚠ ' + esc((e && e.message) || e) + '</div>'; }
  }
  function _argLabel(kind, arg) {
    try {
      if (arg == null) return '';
      if (kind === 'compare' && arg && arg.a) { var a = resolveNode(arg.a), b = resolveNode(arg.b); return (a ? a.label : arg.a) + ' vs ' + (b ? b.label : arg.b); }
      if (kind === 'agentsim') return String((arg && arg.scenario) || '').slice(0, 40);
      if (kind === 'deep') return String(arg || '').slice(0, 40);
      if (kind === 'canvas') return typeof arg === 'string' ? arg.slice(0, 40) : '';
      if (kind === 'scalp') return (arg && arg.sym) || '';
      var id = (arg && typeof arg === 'object') ? (arg.id || arg.ticker) : arg;
      if (!id || typeof id !== 'string') return '';
      var n = resolveNode(id);
      return n ? n.label : id;
    } catch (e) { return ''; }
  }
  function winTitle(kind, arg) {
    var sp = _custom[kind];
    if (sp && typeof sp.title === 'function') { try { var tt = sp.title(arg); if (tt) return String(tt); } catch (e) {} }
    var m = KIND_META[kind]; var base = m ? (ckLang() === 'en' ? m[2] : m[1]) : kind;
    var extra = _argLabel(kind, arg);
    return extra ? base + ' · ' + extra : base;
  }
  // Al cerrar la Cabina los paneles vuelven a su pestaña (parkAdopted) recordando
  // en qué ventana y caja estaban; al reabrir, readopt() devuelve el MISMO nodo sin
  // volver a inicializarlo (la terminal conserva sus gráficos, el mapa su zoom).
  var _parked = [];
  function parkAdopted() {
    _parked = _adopted.filter(function (a) { return a.win; })
      .map(function (a) { return { win: a.win, el: a.el, box: a.el.parentNode, mode: a.el.style.display }; });
    restoreAdopted();
  }
  function readopt(kind, winId, body) {
    var mine = _parked.filter(function (p) { return p.win === winId; });
    _parked = _parked.filter(function (p) { return p.win !== winId; });
    mine = mine.filter(function (p) { return p.box && body.contains(p.box) && p.el && p.el.parentNode; });
    if (!mine.length) return false;
    _adoptCtx = winId;
    try { mine.forEach(function (p) { adoptInto(p.box, p.el, p.mode); }); } finally { _adoptCtx = null; }
    if (mine.some(function (p) { return p.el.tagName === 'MAIN'; })) _mapSettleSoon();   // el mapa vuelve a su ventana
    return true;
  }
  function winCleanup(kind, winId) {
    restoreAdopted(winId);
    _parked = _parked.filter(function (p) { return p.win !== winId; });
    if (kind === 'scalp') _scalpStop();
    if (kind === 'broker') closeConfirmDialog();
    if (kind === 'deep' && _deepTimer) { clearInterval(_deepTimer); _deepTimer = null; }
  }
  if (window.KhipuDesk) window.KhipuDesk.configure({
    render: function (body, kind, arg, winId) {
      _adoptCtx = winId;
      try { render(body, kind, arg); } finally { _adoptCtx = null; }
      try {
        body.classList.toggle('kd-legacy-dark', LEGACY_DARK.indexOf(kind) >= 0);
        body.classList.toggle('kos-native', !!_custom[kind]);
      } catch (e) {}
    },
    title: winTitle,
    icon: function (kind) { var m = KIND_META[kind]; return m ? m[0] : '▫'; },
    // ventanas nativas con mascota (contrato registerKind: mascot) → burbuja del agente en la barra de título
    iconHTML: function (kind) { var sp = _custom[kind]; return (sp && sp.mascot) ? _mascot(sp.mascot, 22) : null; },
    beforeRender: winCleanup,
    onClose: function (kind, winId) {
      winCleanup(kind, winId);
      if (kind === 'chat') _placeThread(_curKind === 'chat' ? 'empty' : _curKind);   // el hilo vuelve al dock
    },
    onFocus: function (kind) {
      if (!kind) { _curKind = 'empty'; markActive(null); return; }
      _curKind = kind;
      markActive(CHIP_KINDS.indexOf(kind) >= 0 ? kind : null);
    },
    onModeChange: _onDeskMode,
    // Khipus OS: el escritorio avisa cuando el chat pasa a la columna central (≥ 1100 px) o vuelve abajo
    onLayout: function (on, centerEl) { _onLayout(on, centerEl); },
    resume: readopt,
    adoptKinds: ['graph', 'terminal', 'crypto', 'tkg', 'guia', 'market', 'geo', 'space', 'simulation', 'portfolios'],
    resumeKinds: ['scalp'],          // sin panel adoptado pero con polling: se re-pinta al reabrir
    multiKinds: MULTI_KINDS,
  });

  /* ══ KHIPUS OS — CHAT AL CENTRO ══════════════════════════════════════════
     El escritorio reserva #kd-center; aquí vive la tarjeta del chat: encabezado (Khipu ·
     "N agentes trabajando contigo" · pila de mascotas · 🧹), el hilo (#bcp-thread, el MISMO
     nodo de siempre) y la barra de entrada (#bcp-barwrap, mudada con sus escuchadores).
     Mientras el hilo está vacío se ve el estado vacío (Khipu grande, sugerencias, lo vivo). */
  var _centerBox = null, _homeTs = 0, _homeLang = null, _threadMO = null;
  function _buildCenter(centerEl) {
    var box = centerEl.querySelector('.kos-chat');
    if (!box) {
      box = document.createElement('div'); box.className = 'kos-chat';
      box.innerHTML = '<div class="kos-chathd"></div><div class="kos-chatbody"></div>';
      centerEl.appendChild(box);
      box.querySelector('.kos-chathd').addEventListener('click', function (e) {
        var b = e.target.closest && e.target.closest('[data-k]'); if (!b) return;
        if (b.getAttribute('data-k') === 'agents') stage('agents');
        else if (b.getAttribute('data-k') === 'new') _newConversation();
      });
    }
    _centerBox = box;
    _paintChatHeader();
    return box;
  }
  function _paintChatHeader() {
    var box = _centerBox; if (!box) return;
    var hd = box.querySelector('.kos-chathd'); if (!hd) return;
    var ag = _agentsOn(), n = ag.length;
    var sub = !n ? L('Solo Khipu, sin agentes extra', 'Just Khipu, no extra agents')
      : n === 1 ? L('1 agente trabajando contigo', '1 agent working with you')
      : L(n + ' agentes trabajando contigo', n + ' agents working with you');
    var mode = _mode();
    if (mode) sub += ' · ' + (mode === 'pro' ? 'Pro' : L('Simple', 'Simple'));
    var think = !!document.querySelector('#bcp-state.think');
    hd.innerHTML = '<span class="kos-chathd-m">' + _mascot('khipu', 40, think ? { state: 'think' } : null) + '</span>' +
      '<div class="who"><div class="nm">Khipu</div><div class="sb">' + esc(sub) + '</div></div><span class="sp"></span>' +
      (n ? '<button type="button" class="kos-stackbtn" data-k="agents" title="' + esc(L('Tus agentes', 'Your agents')) + '" aria-label="' + esc(L('Tus agentes', 'Your agents')) + '">' + _stackHTML(ag, 22) + '</button>' : '') +
      '<button type="button" class="kos-ib" data-k="new" title="' + esc(L('Nueva conversación', 'New conversation')) + '" aria-label="' + esc(L('Nueva conversación', 'New conversation')) + '">' + SVG.compose + '</button>';
  }
  function _syncHasMsgs() {
    if (!_centerBox) return;
    _centerBox.classList.toggle('kos-has-msgs', chatThread().children.length > 0);
  }
  function _watchThread() {
    if (_threadMO || !window.MutationObserver) return;
    try { _threadMO = new MutationObserver(_syncHasMsgs); _threadMO.observe(chatThread(), { childList: true }); } catch (e) { _threadMO = null; }
  }
  function _newConversation() {
    try { if (window.KhipuChat && window.KhipuChat.clear) window.KhipuChat.clear(); } catch (e) {}
    chatThread().innerHTML = '';
    _syncHasMsgs();
    _paintHome(true);
    _focusChat();
  }
  function _focusChat() {
    var i = document.getElementById('bcp-input');
    if (i) try { i.focus({ preventScroll: true }); } catch (e) { i.focus(); }
    var body = _centerBox && _centerBox.querySelector('.kos-chatbody');
    if (body) body.scrollTop = body.scrollHeight;
  }
  function _onLayout(on, centerEl) {
    var ov = document.getElementById('bcp-ov'); if (!ov) return;
    ov.classList.toggle('kos-centered', !!on);
    var bw = document.getElementById('bcp-barwrap'), inp = document.getElementById('bcp-input');
    var hadFocus = !!(inp && document.activeElement === inp);
    if (on && centerEl) {
      var box = _buildCenter(centerEl);
      if (bw && bw.parentNode !== box) box.appendChild(bw);   // misma barra, mismos escuchadores
      var D = desk(); if (D && D.has('chat')) D.closeKind('chat');   // la ventana 💬 ya no hace falta
      _placeThread(_curKind || 'empty');
      _paintHome(false);
    } else {
      var dock = document.getElementById('bcp-chatdock');
      if (bw && dock && bw.parentNode !== ov) ov.insertBefore(bw, dock.nextSibling);
      _centerBox = null;
      _placeThread(_curKind || 'empty');
      // pantalla mediana: el inicio vuelve al muro (después: el escritorio puede estar desmontándose)
      setTimeout(function () { if (open && deskActive() && !chatCentered()) _paintHome(false); }, 0);
    }
    if (hadFocus && inp) { try { inp.focus({ preventScroll: true }); } catch (e) {} }
  }
  // pinta el inicio UNA vez (en el centro o en el muro); ids #bcp-home-* siempre únicos
  function _paintHome(force) {
    var D = desk(); if (!D || !D.active()) return;
    var lang = ckLang(), wall = D.wall();
    if (chatCentered()) {
      if (wall && wall.children.length) wall.innerHTML = '';
      var body = _centerBox && _centerBox.querySelector('.kos-chatbody'); if (!body) return;
      if (!force && body.querySelector('#kos-empty') && _homeLang === lang) return;
      _homeLang = lang; _homeTs = Date.now();
      _renderCenterHome(body);
      return;
    }
    var ce = document.getElementById('kos-empty'); if (ce && ce.parentNode) ce.parentNode.removeChild(ce);
    if (!wall) return;
    if (!force && wall.children.length && _homeLang === lang) return;
    _homeLang = lang; _homeTs = Date.now();
    stageEmpty(wall);
  }
  function _renderCenterHome(body) {
    var en = ckLang() === 'en';
    var old = body.querySelector('#kos-empty'); if (old) old.parentNode.removeChild(old);
    var sugg = en ? ['How is Nvidia doing and what is its biggest risk?', 'Which companies depend on TSMC?', 'What happened today in the chip chain?',
                     'Compare Nvidia and AMD', 'What do my agents think about ASML?', 'Simulate that China bans HBM exports']
                  : ['¿Cómo está Nvidia y cuál es su mayor riesgo?', '¿Qué empresas dependen de TSMC?', '¿Qué pasó hoy en la cadena de chips?',
                     'Compara Nvidia y AMD', '¿Qué opinan mis agentes de ASML?', 'Simula que China prohíbe exportar HBM'];
    var e = document.createElement('div'); e.id = 'kos-empty';
    e.innerHTML = '<div class="kos-hero">' + _mascot('khipu', 84) + '</div>' +
      '<h2 class="kos-empty-h">Khipus <span class="sub">Finance Intelligence</span></h2>' +
      '<p class="kos-empty-p">' + esc(L('Pregúntale lo que quieras, como a un analista.', 'Ask anything, the way you would ask an analyst.')) + '</p>' +
      '<div class="kos-sugg">' + sugg.map(function (q) { return '<button type="button" class="kos-chip" data-q="' + esc(q) + '">' + esc(q) + '</button>'; }).join('') + '</div>' +
      '<div id="bcp-home-hyper" class="bcp-live"></div>' +
      '<div id="bcp-home-pulse" class="bcp-live"></div>' +
      '<div class="kos-agrow"></div>';
    body.insertBefore(e, body.firstChild);
    e.addEventListener('click', function (ev) {
      var c = ev.target.closest && ev.target.closest('.kos-chip');
      if (c) { ask(c.getAttribute('data-q')); return; }
      var a = ev.target.closest && ev.target.closest('.kos-ag');
      if (a) {
        var id = a.getAttribute('data-ag');
        invokeAgent(id);
      }
    });
    _paintAgentRow();
    _syncHasMsgs();
    try { _homeHyper(); } catch (x) {}   // frase viva del hipergrafo (una sola petición, con caché)
    try { _homePulse(); } catch (x) {}   // tus carteras en una línea
  }
  function _paintAgentRow() {
    var row = document.querySelector('#kos-empty .kos-agrow'); if (!row) return;
    var on = _agentsOn();
    row.innerHTML = AGENT_IDS.map(function (id) {
      var tt = _agentName(id) + (_agentRole(id) ? ' — ' + _agentRole(id) : '') + (on.indexOf(id) < 0 ? ' (' + L('apagado', 'off') + ')' : '');
      var inv = L('Invocar a ', 'Invoke ') + _agentName(id);
      return '<button type="button" class="kos-ag' + (on.indexOf(id) < 0 ? ' off' : '') + (_inv === id ? ' inv' : '') + '" data-ag="' + id + '" title="' + esc(inv + ' — ' + tt) + '" aria-label="' + esc(inv) + '">' +
        _mascot(id, 34) + '<span>' + esc(_agentName(id)) + '</span><span class="iv">' + esc(L('Invocar', 'Invoke')) + '</span></button>';
    }).join('');
  }
  /* INVOCAR (2026-10-06, pedido de Fabrizio: "que se llame invocar dentro de la app, nuestro toque"): tocar un
     agente lo llama a la conversación — aparece en la barra con su mascota y responde TODO lo que escribas
     (con sus habilidades, research/agent_skills) hasta que lo despidas con ✕. Un @agente escrito a mano manda. */
  var _inv = null;
  function _paintInvoke(pop) {
    var pill = document.getElementById('kos-inv'), inp = document.getElementById('bcp-input');
    if (!pill) return;
    if (!_inv) {
      pill.hidden = true; pill.innerHTML = '';
      if (inp) inp.setAttribute('placeholder', L('Pregúntale a Khipu…', 'Ask Khipu…'));
    } else {
      var nm = _agentName(_inv);
      pill.innerHTML = _mascot(_inv, 26) + '<span>' + esc(nm) + '</span>' +
        '<button type="button" class="x" aria-label="' + esc(L('Despedir a ', 'Dismiss ') + nm) + '" title="' + esc(L('Despedir a ', 'Dismiss ') + nm) + '">✕</button>';
      pill.hidden = false;
      pill.setAttribute('title', L('Invocaste a ' + nm + ': responde desde su especialidad', 'You invoked ' + nm + ': answers from its specialty'));
      if (pop) { pill.classList.remove('pop'); void pill.offsetWidth; pill.classList.add('pop'); }
      if (inp) inp.setAttribute('placeholder', L('Invocaste a ' + nm + ' — escríbele…', 'You invoked ' + nm + ' — write to it…'));
      var x = pill.querySelector('.x');
      if (x) x.addEventListener('click', function (e) { e.stopPropagation(); invokeAgent(null); });
    }
    _paintAgentRow();
  }
  function invokeAgent(id) {
    _inv = (id && AGENT_TOK[id]) ? id : null;        // Khipu no se invoca: ya está siempre
    var inp = document.getElementById('bcp-input');
    if (inp && _inv && /^\s*@\S+\s*$/.test(inp.value || '')) inp.value = '';   // quita el viejo "@agente " suelto
    _paintInvoke(!!_inv);
    _revealChat();   // "solo chat": la barra no puede quedar tapada por una ventana mientras se escribe
    if (inp) try { inp.focus(); } catch (e) {}
  }
  function _askAgentPrefill(id) { invokeAgent(id); }

  /* ══ KHIPUS OS — PALETA ⌘K: empresas · pantallas · preguntar a un agente · acciones ══ */
  var _pal = { items: [], idx: 0 };
  var _nodeIdx = null;
  function _palEl() { return document.getElementById('kos-pal'); }
  function palIsOpen() { var p = _palEl(); return !!(p && p.classList.contains('show')); }
  function _wordScore(hay, w) {
    if (!w) return 1;
    if (hay === w) return 100;
    if (hay.indexOf(w) === 0) return 82;
    if (hay.indexOf(' ' + w) >= 0) return 66;
    if (w.length >= 3 && hay.indexOf(w) >= 0) return 48;
    if (w.length >= 4) {   // letras en orden ("cmte" → comité)
      var j = 0; for (var k = 0; k < hay.length && j < w.length; k++) if (hay.charAt(k) === w.charAt(j)) j++;
      if (j === w.length) return 18;
    }
    return 0;
  }
  function _matchScore(text, fq) {
    if (!fq) return 1;
    var hay = _fold(text), words = fq.split(/\s+/).filter(Boolean), min = 100;
    for (var i = 0; i < words.length; i++) { var s = _wordScore(hay, words[i]); if (!s) return 0; if (s < min) min = s; }
    return min;
  }
  function _nodeIndex() {
    var N = window.NODES || [];
    if (_nodeIdx && _nodeIdx.n === N.length) return _nodeIdx.list;
    var list = N.map(function (n) { return { n: n, f: _fold(n.label), t: _fold(n.mkt || ''), i: _fold(n.id) }; });
    _nodeIdx = { n: N.length, list: list };
    return list;
  }
  function _palCompanies(fq, raw) {
    var out = [], seen = {};
    function add(n) { if (n && n.id && !seen[n.id] && out.length < 6) { seen[n.id] = 1; out.push(n); } }
    if (!fq) {   // sin texto: lo que miraste hace poco (o la seleccionada), y si no hay nada, las más consultadas
      var ids = [];
      try { var cx = window.KhipuChat && window.KhipuChat.context ? window.KhipuChat.context() : null; ids = (cx && cx.recent_entities) || []; } catch (e) {}
      var sel = _selNode(); if (sel) ids = [sel].concat(ids);
      var recent = ids.length > 0;
      ids.forEach(function (id) { add(resolveNode(id)); });
      if (!recent) ['Nvidia', 'TSMC', 'ASML', 'SK Hynix'].forEach(function (q) { add(resolveNode(q)); });
      return { recent: recent, nodes: out.slice(0, 4) };
    }
    var scored = [];
    _nodeIndex().forEach(function (x) {
      var s = 0;
      if (x.t && x.t === fq) s = 100;
      else if (x.f === fq || x.i === fq) s = 98;
      else if (x.f.indexOf(fq) === 0) s = 84;
      else if (x.t && fq.length >= 2 && x.t.indexOf(fq) === 0) s = 72;
      else if (x.f.indexOf(' ' + fq) >= 0) s = 64;
      else if (fq.length >= 3 && x.f.indexOf(fq) >= 0) s = 50;
      if (s) scored.push({ n: x.n, s: s + (x.n.mkt ? 2 : 0) - Math.min(6, x.f.length / 12) });
    });
    // el resolutor robusto (alias de voz, sin acentos, aproximado) manda arriba si está seguro
    try { var r = window.KhipuResolve && window.KhipuResolve.find(raw); if (r && r.node && (r.score || 0) >= 70) scored.push({ n: r.node, s: 101 }); } catch (e) {}
    scored.sort(function (a, b) { return b.s - a.s; });
    scored.forEach(function (x) { add(x.n); });
    return { recent: false, nodes: out };
  }
  function _openCompany(id) {
    if (_custom.glance) stage('glance', { id: id }); else stage('xray', id);
  }
  function _palActions() {
    var dark = document.body.classList.contains('dark'), mode = _mode();
    var A = [
      { ic: dark ? '☀️' : '🌙', label: dark ? L('Tema claro', 'Light theme') : L('Tema oscuro', 'Dark theme'), k: 'tema theme claro oscuro light dark apariencia', run: _toggleTheme, keep: true },
      { ic: '🌐', label: ckLang() === 'en' ? 'Cambiar a español' : 'Switch to English', k: 'idioma language english espanol ingles spanish', run: _toggleLang, keep: true },
    ];
    if (mode) A.push({ ic: '◐', label: mode === 'pro' ? L('Modo Simple (lenguaje llano)', 'Simple mode (plain language)') : L('Modo Pro (cifras y rangos)', 'Pro mode (figures and ranges)'),
      k: 'modo simple pro mode explicacion', run: function () { _setMode(mode === 'pro' ? 'simple' : 'pro'); _paintChatHeader(); } });
    A.push({ ic: '🧹', label: L('Nueva conversación', 'New conversation'), k: 'nueva conversacion limpiar borrar new conversation clear', run: _newConversation });
    if (deskActive()) A.push({ ic: '▦', label: L('Ordenar ventanas', 'Arrange windows'), k: 'ordenar ventanas acomodar arrange windows tile', run: function () { desk().arrange(true); } });
    A.push({ ic: '▭', label: L('Vista clásica (pestañas de antes)', 'Classic view (the old tabs)'), k: 'vista clasica classic view pestanas tabs salir exit', run: toClassicView });
    return A;
  }
  function palOpen(q) {
    if (!open) openCockpit();
    ensureShell();
    _popClose();
    var p = _palEl(); if (!p) return;
    if (!p.firstChild) {
      p.innerHTML = '<div class="kos-pal-box">' +
        '<div class="kos-pal-in">' + SVG.search + '<input type="text" id="kos-pal-input" autocomplete="off" spellcheck="false" role="combobox" aria-expanded="true" aria-autocomplete="list" aria-controls="kos-pal-list"></div>' +
        '<div class="kos-pal-list" id="kos-pal-list" role="listbox"></div>' +
        '<div class="kos-pal-foot"></div></div>';
      var inp = p.querySelector('input'), list = p.querySelector('.kos-pal-list');
      inp.addEventListener('input', function () { _pal.idx = 0; palRender(); });
      inp.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); _palMove(e.key === 'ArrowDown' ? 1 : -1); }
        else if (e.key === 'Enter' && !e.isComposing) { e.preventDefault(); _palRun(_pal.idx); }
        else if (e.key === 'Escape') { e.preventDefault(); palClose(); }
      });
      list.addEventListener('mousemove', function (e) {
        var it = e.target.closest && e.target.closest('.kos-pi'); if (!it) return;
        var i = +it.getAttribute('data-i'); if (i !== _pal.idx) { _pal.idx = i; _palMark(false); }
      });
      list.addEventListener('click', function (e) {
        var it = e.target.closest && e.target.closest('.kos-pi'); if (it) _palRun(+it.getAttribute('data-i'));
      });
      p.addEventListener('pointerdown', function (e) { if (e.target === p) palClose(); });   // clic en el fondo
    }
    var input = p.querySelector('input');
    input.value = q || '';
    input.setAttribute('placeholder', L('Busca una empresa, una pantalla o una acción…', 'Search a company, a screen or an action…'));
    input.setAttribute('aria-label', input.getAttribute('placeholder'));
    p.querySelector('.kos-pal-foot').innerHTML = '<span><b>↑↓</b> ' + esc(L('moverte', 'move')) + '</span><span><b>↵</b> ' + esc(L('abrir', 'open')) + '</span>' +
      '<span><b>esc</b> ' + esc(L('cerrar', 'close')) + '</span><span style="margin-left:auto">' + esc(L('¿Una pregunta? Escríbela y Khipu responde.', 'A question? Type it and Khipu answers.')) + '</span>';
    p.classList.add('show');
    _pal.idx = 0;
    palRender();
    setTimeout(function () { try { input.focus(); input.select(); } catch (e) {} }, 0);
  }
  function palClose(keepFocus) {
    var p = _palEl(); if (!p || !p.classList.contains('show')) return;
    p.classList.remove('show');
    if (!keepFocus && chatCentered()) { var i = document.getElementById('bcp-input'); if (i) try { i.focus({ preventScroll: true }); } catch (e) {} }
  }
  function palRender() {
    var p = _palEl(); if (!p) return;
    var inp = p.querySelector('input'), list = p.querySelector('.kos-pal-list');
    var raw = (inp.value || '').trim(), fq = _fold(raw), en = ckLang() === 'en';
    var items = [];
    function sec(title, arr) { arr.forEach(function (it, i) { it.sec = i === 0 ? title : null; items.push(it); }); }
    // ¿parece una pregunta? → primero "Preguntar a Khipu"
    var askIt = raw ? [{ ic: _mascot('khipu', 22), label: L('Preguntar a Khipu: «', 'Ask Khipu: “') + raw + L('»', '”'), go: '↵', run: function () { palClose(); ask(raw); } }] : [];
    var question = /[?¿]/.test(raw) || raw.split(/\s+/).length >= 3;
    if (question) sec(L('Preguntar', 'Ask'), askIt);
    var comp = _palCompanies(fq, raw);
    var goLabel = _custom.glance ? L('En una mirada', 'At a glance') : 'X-Ray';
    sec(comp.recent ? L('Recientes', 'Recent') : L('Empresas', 'Companies'), comp.nodes.map(function (n) {
      return { ic: '<i style="background:' + esc(sectorColor(n.cat)) + '"></i>', label: n.label, sub: n.mkt || '', go: goLabel, run: function () { palClose(true); _openCompany(n.id); } };
    }));
    var scr = screens().map(function (s) { return { s: s, sc: _matchScore([s.es, s.en, s.k].join(' '), fq) }; })
      .filter(function (x) { return x.sc > 0; }).sort(function (a, b) { return b.sc - a.sc; }).slice(0, fq ? 6 : 8);
    sec(L('Abrir', 'Open'), scr.map(function (x) {
      return { ic: esc(x.s.ic), label: en ? x.s.en : x.s.es, go: L('Abrir', 'Open'), run: function () { palClose(true); _runScreen(x.s.id); } };
    }));
    var ags = AGENT_IDS.filter(function (id) { return _matchScore(_agentName(id) + ' ' + _agentRole(id) + ' agente agent ' + id, fq) > 0; });
    sec(L('Invocar', 'Invoke'), ags.map(function (id) {
      return { ic: _mascot(id, 22), label: _agentName(id), sub: _agentRole(id), go: L('Invocar', 'Invoke'), run: function () { palClose(); invokeAgent(id); } };
    }));
    var acts = _palActions().filter(function (a) { return _matchScore(a.label + ' ' + a.k, fq) > 0; }).slice(0, fq ? 4 : 8);
    sec(L('Acciones', 'Actions'), acts.map(function (a) {
      return { ic: esc(a.ic), label: a.label, go: '↵', run: function () { if (a.keep) { a.run(); palRender(); return; } palClose(); a.run(); } };
    }));
    if (!question && askIt.length) sec(L('Preguntar', 'Ask'), askIt);
    _pal.items = items;
    if (_pal.idx >= items.length) _pal.idx = Math.max(0, items.length - 1);
    if (!items.length) { list.innerHTML = '<div class="kos-pal-empty">' + esc(L('Nada coincide. Prueba con el ticker (NVDA) o escribe tu pregunta.', 'Nothing matches. Try the ticker (NVDA) or type your question.')) + '</div>'; return; }
    list.innerHTML = items.map(function (it, i) {
      return (it.sec ? '<div class="kos-pal-sec">' + esc(it.sec) + '</div>' : '') +
        '<div class="kos-pi" role="option" id="kos-pi-' + i + '" data-i="' + i + '" aria-selected="false">' +
          '<span class="ic">' + it.ic + '</span>' +
          '<span class="tx">' + esc(it.label) + (it.sub ? '<span class="sub">' + esc(it.sub) + '</span>' : '') + '</span>' +
          '<span class="go">' + esc(it.go || '') + '</span></div>';
    }).join('');
    _palMark(true);
  }
  function _palMark(scroll) {
    var p = _palEl(); if (!p) return;
    p.querySelectorAll('.kos-pi').forEach(function (el) {
      var on = +el.getAttribute('data-i') === _pal.idx;
      el.classList.toggle('on', on); el.setAttribute('aria-selected', on ? 'true' : 'false');
      if (on && scroll && el.scrollIntoView) { try { el.scrollIntoView({ block: 'nearest' }); } catch (e) {} }
    });
    var inp = p.querySelector('input'); if (inp) inp.setAttribute('aria-activedescendant', 'kos-pi-' + _pal.idx);
  }
  function _palMove(d) {
    var n = _pal.items.length; if (!n) return;
    _pal.idx = (_pal.idx + d + n) % n;
    _palMark(true);
  }
  function _palRun(i) {
    var it = _pal.items[i]; if (!it) return;
    try { it.run(); } catch (e) { try { console.warn('[Khipus OS] paleta', e); } catch (x) {} }
  }
  // ── el GRAFO en vivo, dentro de la Cabina ──
  // el mapa (app.html) se mide a sí mismo: tras mudarlo a una ventana se le pide que se asiente con su
  // tamaño real (idempotente y gratis si nada cambió; tras el orden automático del escritorio, por eso el
  // setTimeout, y una segunda vez cuando la ventana ya terminó de acomodarse)
  function _mapSettleSoon() {
    var f = function () { try { if (typeof window._ensureMapSettled === 'function') window._ensureMapSettled(false); } catch (e) {} };
    setTimeout(f, 0); setTimeout(f, 260);
  }
  function stageGraph(s, focusId) {
    s.innerHTML = backBar(L('Grafo en vivo', 'Live graph')) + '<div class="bcp-embed" id="bcp-embed-graph"></div>';
    var main = document.querySelector('main');
    if (!adoptInto(s.querySelector('#bcp-embed-graph'), main, 'flex')) {
      s.innerHTML += '<div class="bcp-loading">' + L('No se pudo montar el grafo', 'Could not mount the graph') + '</div>';
      return;
    }
    _mapSettleSoon();   // medir y asentar el mapa YA con el tamaño de la ventana (no esperar a un 'resize')
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
  //    la Cabina y callaba a Khipu) y cumple la visión: TODO vive en Khipu. Adopta
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

  // ── Unificación progresiva: más pestañas DENTRO de la Cabina (adopción del
  //    panel vivo, igual que grafo/terminal/cripto). Así navegar a ellas por voz
  //    ya NO cierra la Cabina ni corta a Khipu. Solo paneles DOM/SVG seguros. ──
  var ADOPT_TABS = {
    tkg:  { panel: 'tkg-panel',  es: 'Grafo Temporal', en: 'Temporal Graph', init: function () { if (typeof window.initTKGTab === 'function') window.initTKGTab(); } },
    guia: { panel: 'guia-panel', es: 'Guía',           en: 'Guide',          init: function () { if (typeof window.initGuiaTab === 'function') window.initGuiaTab(); } },
    // Integración total (feedback Fabrizio: "que todos los mapas se vean dentro de Khipu").
    market:     { panel: 'market',           es: 'Mercado',     en: 'Market',      init: function () { try { if (typeof window.renderMarket === 'function') window.renderMarket(); if (typeof window.fetchQuotes === 'function' && !(window.MKT && window.MKT.ts)) window.fetchQuotes(); } catch (e) {} } },
    geo:        { panel: 'geo-panel',         es: 'Geopolítica', en: 'Geopolitics', init: function () { if (typeof window.renderGeoPanel === 'function') window.renderGeoPanel(); } },
    space:      { panel: 'space-panel',       es: 'Espacio',     en: 'Space',       init: function () { if (typeof window.initSpaceTab === 'function') window.initSpaceTab(); } },
    simulation: { panel: 'simulation-panel',  es: 'Escenarios',  en: 'Scenarios',   init: function () { if (typeof window.initSimTab === 'function') window.initSimTab(); } },
    // Khipus OS: las carteras de práctica también viven DENTRO (antes abrirlas cerraba la Cabina)
    portfolios: { panel: 'portfolios-panel', es: 'Carteras de práctica', en: 'Practice portfolios', init: function () { if (window.KhipuPortfolios && window.KhipuPortfolios.mount) window.KhipuPortfolios.mount('portfolios-panel'); } },
  };
  function stageAdoptTab(s, tabId) {
    var cfg = ADOPT_TABS[tabId]; if (!cfg) return stageEmpty(s);
    var en = ckLang() === 'en';
    s.innerHTML = backBar(en ? cfg.en : cfg.es) + '<div class="bcp-embed" id="bcp-embed-' + tabId + '" style="overflow:auto"></div>';
    var pane = document.getElementById(cfg.panel);
    if (!pane || !adoptInto(s.querySelector('#bcp-embed-' + tabId), pane, 'block')) {
      s.innerHTML += '<div class="bcp-loading">' + (en ? 'Could not mount' : 'No se pudo montar') + '</div>';
      return;
    }
    try { pane.style.minHeight = '100%'; } catch (e) {}
    // doble rAF: el contenedor necesita layout antes de que el init MIDA su tamaño
    requestAnimationFrame(function () { requestAnimationFrame(function () {
      try { cfg.init(); } catch (e) {}
      // globos 3D (geo/space): un 2º resize por si el layout del embed aún no estaba
      // estable en el 1er frame → evita canvas negro / mal dimensionado.
      if (tabId === 'geo' || tabId === 'space') setTimeout(function () { try { window.dispatchEvent(new Event('resize')); } catch (e) {} }, 240);
    }); });
  }

  // ── la TERMINAL Bloomberg, dentro de la Cabina ──
  function stageTerminal(s, arg) {
    arg = arg || {};
    s.innerHTML = backBar('Terminal') + '<div class="bcp-embed" id="bcp-embed-term"></div>';
    var term = document.getElementById('terminal-panel');
    if (!adoptInto(s.querySelector('#bcp-embed-term'), term, 'flex')) {
      s.innerHTML += '<div class="bcp-loading">' + L('No se pudo montar la terminal', 'Could not mount the terminal') + '</div>';
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
    /* INICIO (rediseño 2026-10-04, pedido: "más estético, menos saturado"): una
       sola idea por línea. Saludo en serif (Fraunces) según la hora, UNA frase
       viva (lo nuevo del grafo o lo estructural, con fecha), tu cartera en una
       línea si hay PIN, y dos columnas de texto plano: "Pregúntame" / "Abre".
       Sin tarjetas, sin píldoras, sin mayúsculas decorativas. */
    var en = ckLang() === 'en';
    var h = new Date().getHours();
    var hello = en ? (h < 12 ? 'Good morning.' : h < 19 ? 'Good afternoon.' : 'Good evening.')
                   : (h < 12 ? 'Buenos días.' : h < 19 ? 'Buenas tardes.' : 'Buenas noches.');
    var askList = en ? [
      ['What are the main risks for TSMC?', ''], ['What happened with Nvidia today?', ''],
      ['simulate that China bans HBM exports', 'Simulate that China bans HBM exports'],
      ['compare Nvidia and AMD', 'Compare Nvidia and AMD'], ['research Nvidia', 'Research Nvidia in depth'],
      ['chart: margins of NVIDIA, TSMC and ASML', 'Chart the margins of NVIDIA, TSMC and ASML'],
    ] : [
      ['¿Cuáles son los riesgos de TSMC?', ''], ['¿Qué pasó hoy con Nvidia?', ''],
      ['simula que China prohíbe exportar HBM', 'Simula que China prohíbe exportar HBM'],
      ['compara Nvidia y AMD', 'Compara Nvidia y AMD'], ['investiga Nvidia', 'Investiga Nvidia a fondo'],
      ['gráfico: márgenes de NVIDIA, TSMC y ASML', 'Grafica los márgenes de NVIDIA, TSMC y ASML'],
    ];
    var open_ = en ? [
      ['graph', 'The live map of 949 companies'], ['xray', 'Take a company apart (X-Ray)'], ['screener', 'Companies breaking out'],
      ['broker', 'My account and positions'], ['insights', 'What the chain is saying now'], ['terminal', 'Charts side by side'],
    ] : [
      ['graph', 'El mapa vivo de 949 empresas'], ['xray', 'Desarmar una empresa (X-Ray)'], ['screener', 'Empresas explosivas'],
      ['broker', 'Mi cuenta y mis posiciones'], ['insights', 'Qué dice la cadena ahora'], ['terminal', 'Gráficos lado a lado'],
    ];
    function li(q, label) { return '<li><a href="#" class="bcp-hq" data-q="' + esc(q) + '">' + esc(label || q) + '</a></li>'; }
    s.innerHTML = '<div id="bcp-empty">' +
      '<h2 class="bcp-hello">' + esc(hello) + ' <span>' + esc(en ? 'What are we looking at?' : '¿Qué miramos hoy?') + '</span></h2>' +
      '<p class="bcp-lead">' + esc(en ? 'Ask me in your own words. I check real data first: prices, suppliers, risk, news.' : 'Pregúntame con tus palabras. Antes de responder consulto datos reales: precios, proveedores, riesgo, noticias.') + '</p>' +
      '<div id="bcp-home-hyper" class="bcp-live"></div>' +
      '<div id="bcp-home-pulse" class="bcp-live"></div>' +
      '<div class="bcp-cols">' +
        '<div><h3>' + esc(en ? 'Ask me' : 'Pregúntame') + '</h3><ul>' + askList.map(function (x) { return li(x[0], x[1]); }).join('') + '</ul></div>' +
        '<div><h3>' + esc(en ? 'Open' : 'Abre') + '</h3><ul>' + open_.map(function (x) { return '<li><a href="#" class="bcp-ho" data-k="' + x[0] + '">' + esc(x[1]) + '</a></li>'; }).join('') + '</ul></div>' +
      '</div>' +
      '<p class="bcp-foot"><a href="#" class="bcp-hq" data-q="demo">' + esc(en ? 'Watch the one-minute tour' : 'Ver el recorrido de un minuto') + '</a></p>' +
      '</div>';
    s.querySelectorAll('.bcp-hq').forEach(function (el) {
      el.addEventListener('click', function (e) { e.preventDefault(); ask(el.getAttribute('data-q')); });
    });
    s.querySelectorAll('.bcp-ho').forEach(function (el) {
      el.addEventListener('click', function (e) {
        e.preventDefault();
        var k = el.getAttribute('data-k');
        if (k === 'xray') { var sel = (window._liveSelectedNode && window._liveSelectedNode()) || null; if (sel) return stage('xray', sel); var i = document.getElementById('bcp-input'); if (i) { i.value = en ? 'break down ' : 'desármame '; i.focus(); } return; }
        stage(k);
      });
    });
    // ESCRITORIO apagado (modo clásico): un solo camino de vuelta a las ventanas
    // (en el escritorio, "una sola pantalla" vive en el menú ⊞ de la barra de tareas)
    if (window.KhipuDesk && !window.KhipuDesk.enabled()) {
      var sw = document.createElement('p');
      sw.id = 'bcp-deskmode'; sw.className = 'bcp-foot';
      sw.innerHTML = esc(en ? 'Single-screen mode. ' : 'Modo una pantalla. ') + '<a href="#" id="bcp-deskmode-sw">' + esc(en ? 'Use windows' : 'Usar ventanas') + '</a>';
      s.querySelector('#bcp-empty').appendChild(sw);
      sw.querySelector('#bcp-deskmode-sw').addEventListener('click', function (e) { e.preventDefault(); window.KhipuDesk.setEnabled(true); });
    }
    try { _homeHyper(); } catch (e) {}   // frase viva del hipergrafo (siempre)
    try { _homePulse(); } catch (e) {}   // tu cartera en una línea (con PIN)
  }

  /* ══ CAPA PROACTIVA en la PANTALLA DE INICIO (pedido de Fabrizio: "primero la
     capa proactiva"). El hipergrafo ya narra la situación en vivo → aquí un
     banner compacto SIEMPRE visible (no requiere cuenta ni PIN) con el insight
     principal + los factores activos, y un clic al panel completo. Reusa
     /api/matrix/insights (cacheado 180s en el server → barato). Si la ontología
     está caída, no aparece nada (silencioso). ══ */
  // caché compartida (inicio + pantalla de Oportunidades): una petición por idioma cada 2 min;
  // si falla, la próxima vez se reintenta (no se guarda el error)
  var _mxIns = { key: '', ts: 0, p: null };
  function _matrixInsights(en) {
    var key = en ? 'en' : 'es', now = Date.now();
    if (_mxIns.p && _mxIns.key === key && now - _mxIns.ts < 120000) return _mxIns.p;
    var p = fetch('/api/matrix/insights', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lang: key, tier: 'fast' }) })
      .then(function (r) { return r.json(); })
      .catch(function () { return null; });
    _mxIns = { key: key, ts: now, p: p };
    p.then(function (d) { if ((!d || d.error) && _mxIns.p === p) _mxIns.ts = 0; });
    return p;
  }
  async function _homeHyper() {
    var el = document.getElementById('bcp-home-hyper'); if (!el) return;
    var en = ckLang() === 'en';
    try {
      var d = await _matrixInsights(en);
      el = document.getElementById('bcp-home-hyper');
      if (!el) return;   // el usuario ya navegó
      if (!d || d.available === false || !(d.insights && d.insights.length)) return;
      var top = d.insights[0];
      var kico = { riesgo: '⚠️', oportunidad: '📈', estructura: '🕸' };
      // FECHAS (2026-10-02): cada factor dice desde cuándo rige; uno viejo no es "noticia"
      function since(f) {
        if (!f.since) return '';
        var dt = new Date(f.since);
        return isNaN(dt) ? '' : (en ? ', since ' : ', desde ') + dt.toLocaleDateString(en ? 'en' : 'es', { month: 'short', year: 'numeric' });
      }
      var facts = (d.factors || []).slice(0, 2).map(function (f) {
        return '<span title="' + esc(f.fresh ? (en ? 'Recent factor' : 'Factor reciente') : (en ? 'Structural factor (not news)' : 'Factor estructural (no es noticia nueva)')) +
          '" style="font-size:10.5px;color:' + (f.fresh ? '#FFD27A' : '#9BA6C4') + ';border:1px solid ' + (f.fresh ? 'rgba(255,179,0,.3)' : 'rgba(155,166,196,.3)') + ';border-radius:999px;padding:1px 8px">' +
          (f.fresh ? '⚡ ' : '◈ ') + esc(f.label) + esc(since(f)) + '</span>';
      }).join(' ');
      var factsTxt = (d.factors || []).slice(0, 2).map(function (f) { return esc(f.label) + esc(since(f)); }).join(en ? ' and ' : ' y ');
      el.innerHTML = '<span class="' + (d.fresh ? 'new' : 'old') + '">' + (d.fresh ? (en ? 'New: ' : 'Nuevo: ') : (en ? 'Structural, not news: ' : 'Estructural, no es noticia nueva: ')) + '</span>' +
        esc(top.title) + (factsTxt ? ' <span class="dim">(' + factsTxt + ')</span>' : '') +
        ' <a href="#" id="bcp-home-hyperbtn">' + (en ? 'See insights' : 'Ver insights') + '</a>';
      var b = document.getElementById('bcp-home-hyperbtn');
      if (b) b.addEventListener('click', function (e) { e.preventDefault(); stage('insights'); });
    } catch (e) {}
  }

  // ── SELECTOR DE EMPRESA: X-Ray / Simular / Comparar / Investigar sin empresa elegida ──
  var PICK_META = {
    xray: ['¿Qué empresa desarmo?', 'Which company should I take apart?'],
    sim: ['¿Qué empresa simulo que cae?', 'Which company should I simulate failing?'],
    compare: ['¿Qué dos empresas comparo?', 'Which two companies should I compare?'],
    research: ['¿Qué empresa investigo a fondo?', 'Which company should I research in depth?'],
  };
  function stagePick(s, arg) {
    arg = arg || {};
    var en = ckLang() === 'en', kind = PICK_META[arg.for] ? arg.for : 'xray';
    var two = kind === 'compare';
    var aNode = arg.a ? resolveNode(arg.a) : null;
    function field(id, ph, val) {
      return '<div class="bcp-pick-f"><input id="' + id + '" type="text" autocomplete="off" spellcheck="false" placeholder="' + esc(ph) + '"' + (val ? ' value="' + esc(val) + '"' : '') + '><div class="bcp-pick-sug" data-for="' + id + '"></div></div>';
    }
    s.innerHTML = backBar(en ? PICK_META[kind][1] : PICK_META[kind][0]) +
      '<div class="bcp-inner bcp-pick" style="max-width:640px">' +
        '<h3 class="bcp-pick-h">' + esc(en ? PICK_META[kind][1] : PICK_META[kind][0]) + '</h3>' +
        '<p class="bcp-pick-p">' + esc(en ? 'Type a name or ticker and pick from the list.' : 'Escribe un nombre o ticker y elige de la lista.') + '</p>' +
        field('bcp-pick-a', en ? 'e.g. Nvidia, TSM, SK Hynix' : 'p. ej. Nvidia, TSM, SK Hynix', aNode ? aNode.label : '') +
        (two ? field('bcp-pick-b', en ? 'Second company' : 'Segunda empresa', '') : '') +
        '<div class="bcp-pick-go"><button type="button" class="bcp-back" id="bcp-pick-ok">' + esc(en ? 'Continue' : 'Continuar') + '</button></div>' +
      '</div>';
    var chosen = { a: aNode ? aNode.id : null, b: null };
    function suggest(inp, box, key) {
      var q = (inp.value || '').trim();
      chosen[key] = null;
      if (q.length < 2) { box.innerHTML = ''; return; }
      var hits = [];
      try {
        var r = window.KhipuResolve ? window.KhipuResolve.find(q) : null;
        if (r && r.node) hits.push(r.node);
        (r && r.suggestions || []).forEach(function (n) { if (n && n.id && !hits.some(function (h) { return h.id === n.id; })) hits.push(n); });
      } catch (e) {}
      if (!hits.length && typeof NODES !== 'undefined') {
        var lc = q.toLowerCase();
        hits = NODES.filter(function (n) { return (n.label || '').toLowerCase().indexOf(lc) >= 0 || (n.mkt || '').toLowerCase() === lc; }).slice(0, 6);
      }
      box.innerHTML = hits.slice(0, 6).map(function (n) {
        return '<button type="button" class="bcp-pick-it" data-id="' + esc(n.id) + '"><b>' + esc(n.label) + '</b>' + (n.mkt ? ' <span>' + esc(n.mkt) + '</span>' : '') + '</button>';
      }).join('');
      box.querySelectorAll('.bcp-pick-it').forEach(function (b) {
        b.addEventListener('click', function () { chosen[key] = b.getAttribute('data-id'); inp.value = b.querySelector('b').textContent; box.innerHTML = ''; if (!two || (chosen.a && chosen.b)) go(); else { var nb = s.querySelector('#bcp-pick-' + (key === 'a' ? 'b' : 'a')); if (nb && !nb.value) nb.focus(); } });
      });
    }
    function go() {
      // opciones FIJAS (2026-10-05): solo lo elegido de la lista o una coincidencia EXACTA (ticker/nombre)
      var exactId = function (v) { var h = window.KhipuPick ? window.KhipuPick.exact(v || '', 'entity') : null; return h ? h.value : null; };
      var a = chosen.a || exactId(s.querySelector('#bcp-pick-a').value);
      var b = two ? (chosen.b || exactId(s.querySelector('#bcp-pick-b').value)) : null;
      if (!a || (two && !b)) { var okb = s.querySelector('#bcp-pick-ok'); if (okb) { okb.textContent = en ? 'Pick a company from the list' : 'Elige una empresa de la lista'; } return; }
      if (kind === 'xray') return stage('xray', a);
      if (kind === 'sim') return stage('sim', { id: a, kind: 'collapse' });
      if (kind === 'compare') return stage('compare', { a: a, b: b });
      if (kind === 'research') return stage('research', { id: a });
    }
    ['a', 'b'].forEach(function (key) {
      var inp = s.querySelector('#bcp-pick-' + key); if (!inp) return;
      var box = s.querySelector('.bcp-pick-sug[data-for="bcp-pick-' + key + '"]');
      inp.addEventListener('input', function () { suggest(inp, box, key); });
      inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); var first = box.querySelector('.bcp-pick-it'); if (first) first.click(); else go(); } });
    });
    s.querySelector('#bcp-pick-ok').addEventListener('click', go);
    setTimeout(function () { var f = s.querySelector(aNode ? '#bcp-pick-b' : '#bcp-pick-a'); if (f) f.focus(); }, 60);
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
    if (!window.buildXRayHTML) { s.innerHTML = '<div class="bcp-loading">' + L('X-Ray no disponible', 'X-Ray unavailable') + '</div>'; return; }
    s.innerHTML = backBar(L('Radiografía', 'X-Ray')) +
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
        '<div style="margin-top:10px;font-size:10.5px;color:#5b6580">' + (function () { var SM = { fmp: 'FMP', yahoo: 'Yahoo Finance', alphavantage: 'Alpha Vantage' }; var srcs = [da.source, db.source].filter(Boolean).map(function (x) { return SM[x] || x; }).filter(function (x, i, a) { return a.indexOf(x) === i; }).join(' + ') || '—'; return en ? 'Latest available fiscal year · source ' + srcs + ' · green = better in that row · not financial advice.' : 'Último año fiscal disponible · fuente ' + srcs + ' · verde = mejor en esa fila · no es asesoría financiera.'; })() + '</div>';
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
    s.innerHTML = backBar(L('Comparar', 'Compare')) +
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
    var kindLabel = { collapse: L('Corte / caída', 'Outage / collapse'), demand: L('Auge de demanda', 'Demand boom'), price: L('Shock de precio', 'Price shock'), sanction: L('Sanción', 'Sanction') }[kind];
    var tint = dir === 'up' ? UP : DOWN;
    if (!window.KhipuState || !window.KhipuState.simulate) { s.innerHTML = backBar() + '<div class="bcp-loading">' + L('Motor de simulación no disponible', 'Simulation engine unavailable') + '</div>'; return; }
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
    }).join('') || '<div class="bcp-loading" style="padding:16px">' + L('Sin propagación significativa', 'No significant spillover') + '</div>';

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

    s.innerHTML = backBar(L('Simulación', 'Simulation')) +
      '<div class="bcp-inner">' +
        '<div class="bcp-simhd"><span class="big">' + esc(n.label) + '</span>' +
          '<span class="kind" style="background:' + tint + '22;color:' + tint + '">' + esc(kindLabel) + '</span>' +
          '<span style="color:#7C87A3;font-size:12px">' + arr.length + ' ' + L('empresas movidas', 'companies moved') + '</span>' +
          '<button class="bcp-back" style="margin-left:auto" onclick="window._cockpitMapSim(\'' + esc(n.id) + '\',\'' + kind + '\')">⚡ ' + L('Ver en el mapa', 'See on the map') + '</button></div>' +
        '<div class="bcp-grid3">' +
          '<div class="bcp-stat"><b style="color:' + tint + '">' + arr.length + '</b><span>' + L('empresas afectadas', 'companies affected') + '</span></div>' +
          '<div class="bcp-stat"><b style="color:' + tint + '">' + (arr[0] ? Math.round(arr[0].v) + '%' : '—') + '</b><span>' + L('golpe máximo', 'max hit') + '</span></div>' +
          '<div class="bcp-stat"><b style="color:' + UP + '">' + winners.length + '</b><span>' + L('ganadores', 'winners') + '</span></div>' +
        '</div>' +
        '<div class="bcp-two">' +
          '<div><div class="bcp-lh" style="color:' + tint + '">' + (dir === 'up' ? L('Quién se beneficia ↑', 'Who benefits ↑') : L('Quién sufre ↓', 'Who suffers ↓')) + '</div>' + victimRows + '</div>' +
          '<div><div class="bcp-lh" style="color:' + UP + '">' + L('Quién gana ↑ (rivales)', 'Who gains ↑ (rivals)') + '</div>' + winRows +
            '<div class="bcp-lh" style="margin-top:18px">' + L('Por sector', 'By sector') + '</div>' + secRowsHTML + '</div>' +
        '</div>' +
      '</div>';
  }

  /* ══ SCREENER DE EXPLOSIVAS — la tesis de la app ("spotear empresas con
     potencial de crecimiento exponencial") hecha ranking computable:
     momentum 5/20/60d multi-bolsa (server, invariante a la moneda) +
     centralidad PageRank del grafo + tendencia MA20. Señales, no asesoría. ══ */
  function stageScreener(s) {
    var en = ckLang() === 'en';
    s.innerHTML = backBar(en ? '🚀 Breakouts' : '🚀 Explosivas') +
      '<div class="bcp-inner" style="max-width:980px"><div id="bcp-scr">' +
      '<div class="bcp-loading">' + (en ? 'Scanning all markets…' : 'Barriendo todas las bolsas…') + '</div></div></div>';
    fetch((typeof BASE !== 'undefined' ? BASE : '') + '/api/screener/growth?top=30')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var host = document.getElementById('bcp-scr');
        if (!host) return;
        if (!d || !d.ranked) { host.innerHTML = '<div class="bcp-loading">' + (en ? 'Screener unavailable' : 'Screener no disponible') + '</div>'; return; }
        var cov = d.coverage || {};
        var covLine = !cov.complete
          ? '<div style="font-size:11px;color:#FFB300;margin:0 0 10px">⏳ ' +
            (en ? 'Warming up: ' : 'Calentando: ') + (cov.warm || 0) + '/' + (cov.total || '?') +
            (en ? ' symbols scanned — ranking improves in minutes' : ' símbolos barridos — el ranking mejora en minutos') + '</div>'
          : '<div style="font-size:11px;color:#7C87A3;margin:0 0 10px">✓ ' + (cov.warm || 0) + '/' + (cov.total || '?') + (en ? ' symbols scanned (all markets)' : ' símbolos barridos (todas las bolsas)') + '</div>';
        var maxs = Math.max.apply(null, d.ranked.map(function (x) { return Math.abs(x.score) || 1; }));
        var rows = d.ranked.map(function (x, i) {
          var col = x.score >= 0 ? UP : DOWN;
          var pr = x.pagerank_rank ? '<span title="' + (en ? 'PageRank of the graph: the system depends on it' : 'PageRank del grafo: el sistema depende de ella') + '" style="font-size:9.5px;color:#00E0FF;border:1px solid rgba(0,224,255,.35);border-radius:999px;padding:1px 6px">🕸 #' + x.pagerank_rank + '</span>' : '';
          var ma = x.above_ma20 ? '<span style="font-size:9.5px;color:#2BE38B">↗MA20</span>' : '';
          var fx = function (v) { return v == null ? '—' : (v >= 0 ? '+' : '') + v.toFixed(1) + '%'; };
          return '<div class="bcp-row" style="gap:10px" onclick="window.BixbyCockpit.stage(\'xray\',\'' + esc(x.id) + '\')">' +
            '<span style="width:20px;text-align:right;color:#5E6884;font-size:11px">' + (i + 1) + '</span>' +
            '<span class="nm" style="font-weight:650">' + esc(x.label) + '</span>' + pr + ma +
            '<span class="mono" style="font-size:10.5px;color:#9BA6C4;width:150px;text-align:right">5d ' + fx(x.r5) + ' · 20d ' + fx(x.r20) + ' · 60d ' + fx(x.r60) + '</span>' +
            '<span class="bar" style="width:70px;background:rgba(122,158,255,.1)"><i style="width:' + Math.min(100, Math.abs(x.score) / maxs * 100) + '%;background:' + col + '"></i></span>' +
            '<span class="pv" style="color:' + col + ';width:48px">' + x.score.toFixed(1) + '</span></div>';
        }).join('');
        host.innerHTML = covLine + rows +
          '<div style="font-size:10px;color:#5E6884;margin-top:12px;line-height:1.5">' + esc(en ? 'Signals, not predictions: 5/20/60-day momentum (multi-exchange, currency-neutral) + graph PageRank centrality (what the system depends on) + trend vs. MA20. Analysis, not financial advice.' : (d.method_es || '')) + '</div>';
      })
      .catch(function () {
        var host = document.getElementById('bcp-scr');
        if (host) host.innerHTML = '<div class="bcp-loading">' + (en ? 'Could not reach the screener' : 'No se pudo consultar el screener') + '</div>';
      });
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
    var en = ckLang() === 'en';
    s.innerHTML = backBar('Insights') +
      '<div class="bcp-inner">' +
        // El HIPERGRAFO corre una simulación en vivo y la narra (se llena async).
        '<div id="bcp-hyper" class="bcp-hyper"><div class="bcp-loading">' +
          (en ? 'The hypergraph is running a live simulation…' : 'El hipergrafo corre una simulación en vivo…') +
        '</div></div>' +
        '<div class="bcp-two">' +
          '<div><div class="bcp-lh" style="color:' + DOWN + '">' + (en ? 'Highest risk (NRS)' : 'Mayor riesgo (NRS)') + '</div>' +
            (risk.map(function (x) { return row(x, DOWN, function (y) { return y.nrs; }); }).join('') || '<div class="bcp-loading">—</div>') + '</div>' +
          '<div><div class="bcp-lh" style="color:' + UP + '">' + (en ? 'Resilient (low risk + growth)' : 'Resilientes (bajo riesgo + crecimiento)') + '</div>' +
            '<div style="font-size:10px;color:var(--ink-3,#7C87A3);margin:-2px 0 6px">' + (en ? 'Ranked by NRS and catalog growth/margin (may be outdated). Not a buy recommendation.' : 'Ordenado por NRS y crecimiento/margen del catálogo (puede estar desactualizado). No es una recomendación de compra.') + '</div>' +
            (opps.map(function (x) { return row(x, UP, function (y) { return 'NRS ' + y.nrs; }); }).join('') || '<div class="bcp-loading">' + (en ? 'No clear opportunities right now' : 'Sin oportunidades claras ahora') + '</div>') + '</div>' +
        '</div>' +
      '</div>';
    _fetchHyperInsights(en);
  }

  /* ══ INSIGHTS DEL HIPERGRAFO — el pago del hipergrafo agéntico temporal: el
     motor corre una simulación EN VIVO con los factores (hiperaristas) activos
     y la NARRA. /api/matrix/insights ya trae la narración IA + fallback de
     plantilla, así que el bloque NUNCA sale vacío. Si la ontología está caída
     (503) el bloque se oculta y la vista NRS de abajo sigue intacta. ══ */
  function _fetchHyperInsights(en) {
    var host = document.getElementById('bcp-hyper'); if (!host) return;
    _matrixInsights(en)
      .then(function (d) {
        var h = document.getElementById('bcp-hyper'); if (!h) return;   // el usuario cambió de escena
        if (!d || d.available === false || d.error) { h.style.display = 'none'; return; }
        _renderHyperInsights(h, d, en);
      })
      .catch(function () { var h = document.getElementById('bcp-hyper'); if (h) h.style.display = 'none'; });
  }

  function _renderHyperInsights(host, d, en) {
    var kicon = { riesgo: '⚠️', oportunidad: '📈', estructura: '🕸' };
    var facts = (d.factors || []).map(function (f) {
      return '<span class="bcp-fact">⚡ <b>' + esc(f.label) + '</b> · ' + (en ? 'sev' : 'sev') + ' ' +
        Math.round(f.severity || 5) + '/10 · ' + (f.members || []).length + (en ? ' hit' : ' afecta') + '</span>';
    }).join('');
    var cards = (d.insights || []).map(function (it) {
      var k = (it.kind === 'riesgo' || it.kind === 'oportunidad' || it.kind === 'estructura') ? it.kind : 'estructura';
      return '<div class="bcp-icard k-' + k + '"><div class="ih"><span class="ic">' + (kicon[k] || '🕸') + '</span>' +
        '<span class="it">' + esc(it.title || '') + '</span></div>' +
        '<div class="id">' + esc(it.detail || '') + '</div></div>';
    }).join('');
    var casc = '';
    if ((d.cascade || []).length) {
      var mx = Math.max.apply(null, d.cascade.map(function (c) { return c.impact || 0; })) || 100;
      casc = '<div class="bcp-casc"><div class="ch">' +
        (en ? 'Live cascade' : 'Cascada en vivo') + (d.trigger ? ' · ' + esc(d.trigger) : '') +
        (d.affected ? ' · ' + d.affected + (en ? ' nodes reached' : ' nodos alcanzados') : '') + '</div>' +
        d.cascade.slice(0, 6).map(function (c) {
          var id = c.id || '';
          return '<div class="bcp-cascrow" onclick="window.BixbyCockpit.stage(\'xray\',\'' + esc(id) + '\')">' +
            '<span class="nm">' + esc(c.name || id) + '</span>' +
            '<span class="bar"><i style="width:' + Math.round((c.impact || 0) / mx * 100) + '%"></i></span>' +
            '<span class="pv">' + Math.round(c.impact || 0) + '%</span></div>';
        }).join('') + '</div>';
    }
    var model = d.model && d.model !== 'plantilla' ? d.model : (en ? 'template' : 'plantilla');
    host.innerHTML =
      '<div class="bcp-hyper-hd"><span class="t">' + (en ? '🕸 What the hypergraph sees' : '🕸 Lo que ve el hipergrafo') + '</span>' +
        '<span class="live">' + (en ? 'LIVE SIM' : 'SIM EN VIVO') + '</span></div>' +
      (facts ? '<div class="bcp-facts">' + facts + '</div>' : '') +
      (cards ? '<div class="bcp-icards">' + cards + '</div>' : '') +
      casc +
      '<div class="bcp-hyper-foot">' + (en
        ? 'Analysis, not financial advice · narrated by ' + esc(model)
        : 'Análisis, no asesoría financiera · narrado por ' + esc(model)) + '</div>';
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
    if (!el) return;
    if (_bkAcct && typeof _bkAcct.paper === 'boolean') { el.innerHTML = badgeHTML(_bkAcct.paper); return; }
    // Cuenta aún sin cargar (sin PIN guardado, p. ej. tras caducar las 12 h):
    // el modo sale de /api/trade/status, público → la tarjeta de confirmación
    // NUNCA queda sin 🧪/🔴 (la cuenta, cuando llegue, manda sobre éste).
    if (window._tradeStatusInfo) window._tradeStatusInfo().then(function (s) {
      var e2 = document.getElementById('bcp-bk-cbadge');
      if (e2 && s && typeof s.paper === 'boolean' && !(_bkAcct && typeof _bkAcct.paper === 'boolean')) e2.innerHTML = badgeHTML(s.paper);
    }).catch(function () {});
  }
  function fmtUsd(v) { return '$' + (Number(v) || 0).toLocaleString('en-US', { maximumFractionDigits: 2 }); }

  /* ══ INFORME DE PORTAFOLIO (pedido de Fabrizio: que Khipu "mande" informes de
     cómo va el portafolio). Rendimiento + mejor/peor + concentración por sector
     + comentario CAUTO de Khipu (Sonnet 5, sin órdenes de compra/venta). Todo
     sobre la cuenta de PAPEL. Reusa NODES/catLabel y los helpers de trade. ══ */
  function _sectorOf(p) {
    var en = ckLang() === 'en';
    var symbol = (p && p.symbol != null) ? p.symbol : p;   // acepta el objeto posición o un string
    var ac = (p && p.asset_class) || '';
    var sym = String(symbol || '').toUpperCase();
    if (!sym) return en ? 'Other' : 'Otro';
    // cripto: por asset_class de Alpaca, por par con barra ("BTC/USD"), o por sufijo
    // USD/USDT/USDC ("BTCUSD" — así lo devuelve /v2/positions, SIN barra → antes caía
    // a "Otro" y Khipu decía "~100% en Otro" en carteras cripto).
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
          '<span style="color:#7C87A3">💬 ' + (en ? 'Khipu is looking at your portfolio…' : 'Khipu está mirando tu portafolio…') + '</span></div></div>';
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
        ? '<span style="color:#00E0FF;font-weight:700">💬 Khipu:</span> ' + esc(d.comment)
        : '<span style="color:#7C87A3">💬 ' + (en ? 'No comment available.' : 'Sin comentario disponible.') + '</span>';
    } catch (e) {
      el = document.getElementById('bcp-bk-aicomment');
      if (el) el.innerHTML = '<span style="color:#7C87A3">💬 ' + (en ? "Could not load Khipu's comment." : 'No pude cargar el comentario de Khipu.') + '</span>';
    }
  }

  /* ══ SCALPING (elección de Fabrizio: 1-clic + ticks en vivo · cripto y acciones ·
     TODO PAPEL). Precio spot polleado (2.5s), botones de entrada/salida inmediata
     (sin tarjeta de confirmación: la velocidad ES el punto y es dinero de papel),
     posición + P&L en vivo y cierre de un toque. ══ */
  var _scalpTimer = null, _scalpPosTimer = null, _scalpSym = 'BTC/USD', _scalpAmt = 500, _scalpHist = [], _scalpSessOpen = null;
  var SCALP_PRESETS = [
    { sym: 'BTC/USD', label: 'BTC' }, { sym: 'ETH/USD', label: 'ETH' }, { sym: 'SOL/USD', label: 'SOL' },
    { sym: 'NVDA', label: 'NVDA' }, { sym: 'TSM', label: 'TSMC' }, { sym: 'AMD', label: 'AMD' },
  ];
  function _scalpStop() {
    if (_scalpTimer) { clearInterval(_scalpTimer); _scalpTimer = null; }
    if (_scalpPosTimer) { clearInterval(_scalpPosTimer); _scalpPosTimer = null; }
  }
  function _scalpFmtPrice(p) {
    p = +p || 0;
    var dec = p < 10 ? 4 : 2;
    return '$' + p.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
  }
  function _scalpDrawSpark() {
    var svg = document.getElementById('bcp-scalp-spark');
    if (!svg || _scalpHist.length < 2) return;
    var W = 320, H = 60, min = Math.min.apply(null, _scalpHist), max = Math.max.apply(null, _scalpHist), rng = (max - min) || 1;
    var pts = _scalpHist.map(function (v, i) { return (i / (_scalpHist.length - 1) * W).toFixed(1) + ',' + (H - (v - min) / rng * (H - 8) - 4).toFixed(1); });
    var up = _scalpHist[_scalpHist.length - 1] >= _scalpHist[0];
    svg.innerHTML = '<path d="M ' + pts.join(' L ') + '" fill="none" stroke="' + (up ? '#34d399' : '#f87171') + '" stroke-width="2" stroke-linejoin="round"/>';
  }
  function _scalpPoll() {
    var sym = _scalpSym;
    fetch((window.BASE || '') + '/api/scalp/price/' + encodeURIComponent(sym)).then(function (r) { return r.json(); }).then(function (d) {
      if (_scalpSym !== sym || !d || d.price == null) return;
      var p = +d.price;
      if (_scalpSessOpen == null) _scalpSessOpen = +(d.prev || p);
      var prev = _scalpHist.length ? _scalpHist[_scalpHist.length - 1] : p;
      _scalpHist.push(p); if (_scalpHist.length > 50) _scalpHist.shift();
      var el = document.getElementById('bcp-scalp-price');
      if (el) { el.textContent = _scalpFmtPrice(p); el.style.color = p > prev ? '#34d399' : p < prev ? '#f87171' : '#E8EDFB'; }
      var chg = document.getElementById('bcp-scalp-chg');
      if (chg && _scalpSessOpen) { var pct = (p / _scalpSessOpen - 1) * 100; chg.innerHTML = (pct >= 0 ? '<span style="color:#34d399">▲ +' : '<span style="color:#f87171">▼ ') + pct.toFixed(2) + '%</span>'; }
      _scalpDrawSpark();
    }).catch(function () {});
  }
  async function _scalpOrder(side) {
    var st = document.getElementById('bcp-scalp-status'), en = ckLang() === 'en';
    if (!window._executeTradeOrder || !window._resolveTradeSymbol) { if (st) st.innerHTML = '<span style="color:#f87171">' + (en ? 'Trading not loaded.' : 'Trading no cargado.') + '</span>'; return; }
    var col = side === 'buy' ? '#34d399' : '#f87171';
    if (st) { st.style.color = col; st.textContent = en ? 'Sending…' : 'Enviando…'; }
    try {
      var res = await window._resolveTradeSymbol(_scalpSym);
      if (!res.ok) { st = document.getElementById('bcp-scalp-status'); if (st) st.innerHTML = '<span style="color:#f87171">' + esc(res.error || L('símbolo', 'symbol')) + '</span>'; return; }
      // 1 clic SOLO en papel (elección de Fabrizio: la velocidad es el punto y es
      // dinero simulado). Con DINERO REAL — o si no se sabe el modo — pide la
      // confirmación pop-up como cualquier otra orden.
      var KT = window.KhipuToast;
      var mode = KT ? await KT.order.resolveMode({}) : null;
      if (KT && mode !== 'paper') {
        var yes = await KT.confirmOrder({ side: side, symbol: res.symbol, label: res.label, kind: res.kind, notional: _scalpAmt, mode: mode });
        if (!yes) { st = document.getElementById('bcp-scalp-status'); if (st) { st.style.color = '#7C87A3'; st.textContent = tb('canceled'); } return; }
      }
      var r = await window._executeTradeOrder({ symbol: res.symbol, side: side, label: res.label, kind: res.kind, notional: _scalpAmt });
      st = document.getElementById('bcp-scalp-status');
      if (r && r.ok && r.dedup) { if (st) st.innerHTML = '<span style="color:#FFB300">' + (r.broker_dup ? esc(tb('brokerDup')) : (en ? 'That same order was already sent a moment ago — it was not sent twice.' : 'Esa misma orden ya se envió hace un momento — no se envió dos veces.')) + '</span>'; setTimeout(_scalpLoadPos, 900); }
      else if (r && r.ok) { if (st) st.innerHTML = '<span style="color:' + col + '">✓ ' + (side === 'buy' ? (en ? 'Bought' : 'Compraste') : (en ? 'Sold' : 'Vendiste')) + ' $' + _scalpAmt + ' ' + esc(res.label) + '</span>'; setTimeout(_scalpLoadPos, 900); }
      else if (st) st.innerHTML = '<span style="color:#f87171">⚠ ' + esc((r && r.error) || 'error') + '</span>';
    } catch (e) { st = document.getElementById('bcp-scalp-status'); if (st) st.innerHTML = '<span style="color:#f87171">⚠ ' + esc((e && e.message) || e) + '</span>'; }
  }
  async function _scalpLoadPos() {
    var mount = document.getElementById('bcp-scalp-pos'), en = ckLang() === 'en';
    if (!mount || !window._tradeFetch) return;
    try {
      var r = await window._tradeFetch('/api/trade/positions/detail', {}, false);
      var dp = await r.json();
      mount = document.getElementById('bcp-scalp-pos');
      if (!mount || !Array.isArray(dp)) return;
      var symNorm = _scalpSym.replace('/', '').toUpperCase();
      var pos = dp.filter(Boolean).find(function (p) { return String(p.symbol || '').replace('/', '').toUpperCase() === symNorm; });
      if (!pos) { mount.innerHTML = '<div style="text-align:center;color:#7C87A3;font-size:12.5px">' + (en ? 'No open position in ' : 'Sin posición abierta en ') + esc(_scalpSym) + '</div>'; return; }
      var pl = +pos.unrealized_pct || 0, plUsd = +pos.unrealized || 0, col = pl >= 0 ? '#34d399' : '#f87171';
      mount.innerHTML = '<div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;justify-content:center;padding:12px 16px;border:1px solid ' + col + '33;border-radius:14px;background:' + col + '0d">' +
        '<div><div style="font-size:11px;color:#7C87A3">' + (en ? 'Position' : 'Posición') + '</div><div style="font-weight:750;font-family:\'JetBrains Mono\',monospace">' + fmtUsd(pos.market_val) + '</div></div>' +
        '<div><div style="font-size:11px;color:#7C87A3">P&L</div><div style="font-weight:750;color:' + col + '">' + (pl >= 0 ? '+' : '') + pl.toFixed(2) + '% (' + (plUsd >= 0 ? '+' : '') + fmtUsd(plUsd) + ')</div></div>' +
        '<button id="bcp-scalp-close" style="margin-left:auto;padding:8px 18px;border-radius:10px;cursor:pointer;font-size:13px;font-weight:700;border:1px solid rgba(248,113,113,.5);background:rgba(248,113,113,.14);color:#f87171">' + (en ? 'Close' : 'Cerrar') + '</button></div>';
      var cb = document.getElementById('bcp-scalp-close');
      if (cb) cb.addEventListener('click', _scalpClose);
    } catch (e) {}
  }
  async function _scalpClose() {
    var st = document.getElementById('bcp-scalp-status'), en = ckLang() === 'en';
    if (!window._tradeFetch) return;
    if (st) { st.style.color = '#7C87A3'; st.textContent = en ? 'Closing…' : 'Cerrando…'; }
    try {
      var r = await window._tradeFetch('/api/trade/close', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ symbol: _scalpSym }) }, false);
      st = document.getElementById('bcp-scalp-status');
      if (r && r.status < 400) { if (st) st.innerHTML = '<span style="color:#34d399">✓ ' + (en ? 'Position closed' : 'Posición cerrada') + '</span>'; setTimeout(_scalpLoadPos, 900); }
      else { var d = {}; try { d = await r.json(); } catch (e2) {} if (st) st.innerHTML = '<span style="color:#f87171">⚠ ' + esc(window._tradeErrText ? window._tradeErrText(d, r.status) : ((d && (d.message || d.error)) || 'error')) + '</span>'; }
    } catch (e) { st = document.getElementById('bcp-scalp-status'); if (st) st.innerHTML = '<span style="color:#f87171">⚠ ' + esc((e && e.message) || e) + '</span>'; }
  }
  // modo ya conocido (cuenta cargada) para pintar la insignia sin esperar; null = aún no
  function _scalpPaperGuess() { return (_bkAcct && typeof _bkAcct.paper === 'boolean') ? _bkAcct.paper : null; }
  function stageScalp(s, arg) {
    arg = arg || {}; _scalpStop();
    var en = ckLang() === 'en';
    if (arg.sym) _scalpSym = arg.sym;
    _scalpHist = []; _scalpSessOpen = null;
    var symChips = SCALP_PRESETS.map(function (p) {
      var on = p.sym === _scalpSym;
      return '<button class="bcp-scalp-sym" data-sym="' + esc(p.sym) + '" style="padding:6px 14px;border-radius:999px;cursor:pointer;font-size:13px;font-weight:700;font-family:inherit;white-space:nowrap;flex-shrink:0;' +
        'border:1px solid ' + (on ? '#00E0FF' : 'rgba(122,158,255,.25)') + ';background:' + (on ? 'rgba(0,224,255,.14)' : 'transparent') + ';color:' + (on ? '#00E0FF' : '#9BA6C4') + '">' + esc(p.label) + '</button>';
    }).join('');
    var amtChips = [100, 500, 1000].map(function (v) {
      var on = v === _scalpAmt;
      return '<button class="bcp-scalp-amt" data-amt="' + v + '" style="padding:6px 15px;border-radius:999px;cursor:pointer;font-size:13px;font-weight:700;font-family:inherit;' +
        'border:1px solid ' + (on ? '#00E0FF' : 'rgba(122,158,255,.25)') + ';background:' + (on ? 'rgba(0,224,255,.14)' : 'transparent') + ';color:' + (on ? '#00E0FF' : '#9BA6C4') + '">$' + v.toLocaleString('en-US') + '</button>';
    }).join('');
    s.innerHTML = backBar('⚡ Scalping') +
      '<div class="bcp-inner" style="max-width:720px">' +
        '<div style="display:flex;gap:8px;overflow-x:auto;padding-bottom:6px;margin-bottom:16px">' + symChips + '</div>' +
        '<div style="text-align:center;padding:18px;border:1px solid rgba(122,158,255,.18);border-radius:16px;background:rgba(12,18,32,.5);margin-bottom:16px">' +
          '<div style="font-size:13px;color:#7C87A3;margin-bottom:4px">' + esc(_scalpSym) + ' <span id="bcp-scalp-mode" style="margin-left:6px">' + badgeHTML(_scalpPaperGuess()) + '</span></div>' +
          '<div id="bcp-scalp-price" style="font-size:38px;font-weight:800;font-family:\'JetBrains Mono\',monospace;color:#E8EDFB">—</div>' +
          '<div id="bcp-scalp-chg" style="font-size:13px;color:#7C87A3;margin-top:2px">&nbsp;</div>' +
          '<svg id="bcp-scalp-spark" viewBox="0 0 320 60" preserveAspectRatio="none" style="width:100%;max-width:320px;height:60px;margin-top:10px"></svg>' +
        '</div>' +
        '<div style="display:flex;gap:8px;justify-content:center;margin-bottom:14px">' + amtChips + '</div>' +
        '<div style="display:flex;gap:12px;margin-bottom:16px">' +
          '<button id="bcp-scalp-buy" style="flex:1;padding:16px;border-radius:14px;cursor:pointer;font-size:17px;font-weight:800;font-family:inherit;border:1px solid #34d39988;background:rgba(52,211,153,.16);color:#34d399">▲ ' + (en ? 'BUY' : 'COMPRAR') + '</button>' +
          '<button id="bcp-scalp-sell" style="flex:1;padding:16px;border-radius:14px;cursor:pointer;font-size:17px;font-weight:800;font-family:inherit;border:1px solid #f8717188;background:rgba(248,113,113,.16);color:#f87171">▼ ' + (en ? 'SELL' : 'VENDER') + '</button>' +
        '</div>' +
        '<div id="bcp-scalp-status" style="text-align:center;font-size:13px;min-height:18px;margin-bottom:14px"></div>' +
        '<div id="bcp-scalp-pos"></div>' +
      '</div>';
    s.querySelectorAll('.bcp-scalp-sym').forEach(function (b) { b.addEventListener('click', function () { stage('scalp', { sym: b.getAttribute('data-sym') }); }); });
    s.querySelectorAll('.bcp-scalp-amt').forEach(function (b) { b.addEventListener('click', function () { _scalpAmt = +b.getAttribute('data-amt'); stage('scalp', { sym: _scalpSym }); }); });
    var buy = s.querySelector('#bcp-scalp-buy'), sell = s.querySelector('#bcp-scalp-sell');
    if (buy) buy.addEventListener('click', function () { _scalpOrder('buy'); });
    if (sell) sell.addEventListener('click', function () { _scalpOrder('sell'); });
    // insignia según la cuenta REAL (antes decía PAPEL siempre): /api/trade/status
    if (window._tradeStatusInfo) window._tradeStatusInfo().then(function (x) {
      var b = document.getElementById('bcp-scalp-mode');
      if (b) b.innerHTML = badgeHTML(x && typeof x.paper === 'boolean' ? x.paper : false);
    }).catch(function () {});
    _scalpPoll(); _scalpTimer = setInterval(_scalpPoll, 2500);
    _scalpLoadPos(); _scalpPosTimer = setInterval(_scalpLoadPos, 5000);
  }

  /* ══ CAPA PROACTIVA (Opus 4.8) — "sugiere y tú decides" (elección de Fabrizio).
     Khipu mira tu cartera + candidatos del universo y propone incluir/reducir/
     vigilar, cada sugerencia con botón "Aplicar" que abre la confirmación (NUNCA
     ejecuta solo). ══ */
  function _portfolioCandidates(heldSymbols) {
    var held = {}; (heldSymbols || []).forEach(function (s) { held[String(s).toUpperCase().replace('/', '')] = 1; });
    var nrs = function (id) { try { return typeof computeNRS === 'function' ? computeNRS(id) : null; } catch (e) { return null; } };
    return (window.NODES || []).filter(function (n) { return n.mkt && !held[String(n.mkt).toUpperCase()]; })
      .map(function (n) { return { label: n.label, ticker: n.mkt, sector: (typeof window.catLabel === 'function' ? window.catLabel(n.cat) : n.cat), nrs: nrs(n.id) }; })
      .filter(function (c) { return c.nrs != null; })
      .sort(function (a, b) { return b.nrs - a.nrs; }).slice(0, 15);
  }

  async function _fetchAdvice(mount) {
    if (!mount) return;
    var en = ckLang() === 'en';
    mount.innerHTML = '<div class="bcp-loading">' + (en ? 'Khipu is studying your portfolio…' : 'Khipu está estudiando tu cartera…') + '</div>';
    if (!window._tradeAccountInfo || !window._tradeFetch) { mount.innerHTML = '<div style="color:#FFB300;padding:12px;font-size:13px">' + (en ? 'Trading module not loaded.' : 'El módulo de trading no está cargado.') + '</div>'; return; }
    var acct = null, positions = [];
    try { acct = await window._tradeAccountInfo(true, false); } catch (e) {}
    if (!acct || acct.error) { mount.innerHTML = '<div style="color:#FFB300;padding:12px;font-size:13px">' + esc((acct && acct.error) || (en ? 'Connect the broker first.' : 'Conecta el bróker primero.')) + '</div>'; return; }
    try { var rp = await window._tradeFetch('/api/trade/positions/detail', {}, false); var dp = await rp.json(); if (Array.isArray(dp)) positions = dp; } catch (e) {}
    var m = _computePortfolio(acct, positions);
    var payload = {
      lang: en ? 'en' : 'es', paper: m.paper, equity: Math.round(m.equity || 0), pnl_pct: +m.pnlPct.toFixed(2),
      positions: positions.slice(0, 20).map(function (p) { return { symbol: p.symbol, sector: _sectorOf(p), pct: m.totalMV ? Math.round((+p.market_val || 0) / m.totalMV * 100) : 0, pnl_pct: +(+p.unrealized_pct || 0).toFixed(1) }; }),
      sectors: m.sectors.slice(0, 8).map(function (s) { return { sector: s.sector, pct: +s.pct.toFixed(0) }; }),
      candidates: _portfolioCandidates(positions.map(function (p) { return p.symbol; })),
    };
    try {
      var r = await fetch((window.BASE || '') + '/api/portfolio/advice', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      var d = await r.json();
      mount.innerHTML = _renderAdvice(d, en);
      _wireAdvice(mount);
    } catch (e) { mount.innerHTML = '<div style="color:#f87171;padding:12px;font-size:13px">⚠ ' + (en ? 'Could not get advice.' : 'No pude obtener consejos.') + '</div>'; }
  }

  function _renderAdvice(d, en) {
    var pulse = (d && d.pulse) || '';
    var sug = (d && Array.isArray(d.suggestions)) ? d.suggestions : [];
    var mdl = String((d && d.model) || '');
    var mLbl = /opus/i.test(mdl) ? 'Claude Opus 4.8' : /sonnet/i.test(mdl) ? 'Claude Sonnet 5' : /haiku/i.test(mdl) ? 'Claude Haiku' : 'Claude';
    var ico = { add: '➕', reduce: '➖', watch: '👁' };
    var alab = en ? { add: 'Add', reduce: 'Reduce', watch: 'Watch' } : { add: 'Incluir', reduce: 'Reducir', watch: 'Vigilar' };
    var sevCol = { alta: '#f87171', media: '#FFB300', baja: '#34d399', high: '#f87171', medium: '#FFB300', low: '#34d399' };
    var cards = sug.map(function (s) {
      var col = sevCol[String(s.severity || '').toLowerCase()] || '#00E0FF';
      var canApply = (s.action === 'add' || s.action === 'reduce') && s.ticker;
      return '<div style="border:1px solid ' + col + '40;border-radius:12px;background:' + col + '0d;padding:12px 14px;margin-bottom:10px">' +
        '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;flex-wrap:wrap">' +
          '<span>' + (ico[s.action] || '•') + '</span>' +
          '<span style="font-weight:750;font-size:13.5px">' + esc(alab[s.action] || s.action) + ': ' + esc(s.target || s.ticker || '') + '</span>' +
          (s.ticker ? '<span style="color:#7C87A3;font-family:\'JetBrains Mono\',monospace;font-size:12px">' + esc(s.ticker) + '</span>' : '') + '</div>' +
        '<div style="font-size:12.5px;color:#C3CBE0;line-height:1.5;margin-bottom:' + (canApply ? '10px' : '0') + '">' + esc(s.rationale || '') + '</div>' +
        (canApply ? '<button class="bcp-adv-apply" data-side="' + (s.action === 'reduce' ? 'sell' : 'buy') + '" data-ticker="' + esc(s.ticker) + '" data-label="' + esc(s.target || s.ticker) + '" ' +
          'style="padding:5px 14px;border-radius:8px;cursor:pointer;font-size:12.5px;font-weight:700;border:1px solid ' + col + '66;background:' + col + '1a;color:' + col + '">' + (en ? 'Apply →' : 'Aplicar →') + '</button>' : '') +
      '</div>';
    }).join('');
    return '<div style="margin-bottom:14px;padding:12px 14px;border-radius:10px;background:rgba(0,224,255,.05);border:1px solid rgba(0,224,255,.16);font-size:13px;line-height:1.55;color:#C3CBE0">' +
      '<span style="color:#00E0FF;font-weight:700">🧠 Khipu:</span> ' + esc(pulse) + '</div>' +
      (sug.length ? cards : '<div style="color:#7C87A3;font-size:12.5px;padding:6px">' + (en ? 'No changes suggested right now.' : 'Sin cambios sugeridos por ahora.') + '</div>') +
      '<div style="margin-top:6px;font-size:10.5px;color:#5b6580">' + (en ? 'Suggestions by ' + mLbl + ' · you approve every action · not financial advice.' : 'Sugerencias por ' + mLbl + ' · tú apruebas cada acción · no es asesoría financiera.') + '</div>';
  }

  function _wireAdvice(mount) {
    mount.querySelectorAll('.bcp-adv-apply').forEach(function (b) {
      b.addEventListener('click', function () {
        if (window._openBrokerStage) window._openBrokerStage({ confirm: {
          symbol: b.getAttribute('data-ticker'), side: b.getAttribute('data-side'),
          notional: 100, label: b.getAttribute('data-label'), kind: 'equity' } });
      });
    });
  }

  // Pulso LIGERO en el home (sin IA): UNA línea por cartera, cada una con su NOMBRE.
  // 2026-10-06 (Fabrizio: "¿de qué cartera habla? tengo 2"): antes solo mostraba la cuenta
  // del bróker como "Tu cartera" (1 ETF) y no las carteras simuladas. Ahora: cada cartera
  // simulada (engine/portfolios.js, precios en vivo) + la cuenta del bróker si hay PIN.
  function _pfLine(name, value, pct, n, en) {
    var col = pct >= 0 ? 'var(--os-good,' + UP + ')' : 'var(--os-bad,' + DOWN + ')', sign = pct >= 0 ? '+' : '';
    return esc(name) + ': ' + _money(value) +   // mismo formato que el saldo de la barra superior
      (n ? ' · <span style="color:' + col + '">' + sign + pct.toFixed(1) + '%</span> · ' + n + ' ' + (en ? (n === 1 ? 'position' : 'positions') : (n === 1 ? 'posición' : 'posiciones'))
         : ' · ' + (en ? 'no positions' : 'sin posiciones'));
  }
  function _homePfLines(en) {
    var P = window.KhipuPortfolios, out = [];
    if (!P || !P._list || !P._stats) return out;
    var list = []; try { list = P._list() || []; } catch (e) { list = []; }
    list.forEach(function (pf) {
      var st = null; try { st = P._stats(pf); } catch (e) {}
      if (!st) return;
      out.push('🧪 ' + _pfLine(pf.name, st.total, st.plPct, (pf.positions || []).length, en) +
        ' <a href="#" class="bcp-home-pf" data-pf="' + esc(pf.id) + '">' + (en ? 'Open' : 'Abrir') + '</a>');
    });
    return out;
  }
  async function _homePulse() {
    var el = document.getElementById('bcp-home-pulse');
    if (!el) return;
    var en = ckLang() === 'en';
    var lines = _homePfLines(en);
    function paint() {
      el.innerHTML = lines.map(function (l) { return '<div>' + l + '</div>'; }).join('');
      el.querySelectorAll('.bcp-home-pf').forEach(function (a) {
        a.addEventListener('click', function (e) {
          e.preventDefault();
          try { localStorage.setItem('kh_pf_active', a.getAttribute('data-pf')); } catch (x) {}
          if (open) stage('portfolios');
          else if (window._surface) window._surface('tab', 'portfolios'); else if (window.switchTab) window.switchTab('portfolios');
          setTimeout(function () { try { window.KhipuPortfolios.refresh(); } catch (x) {} _balRefresh(); }, 300);
        });
      });
      var b = document.getElementById('bcp-home-adv');
      if (b) b.addEventListener('click', function (e) { e.preventDefault(); stage('broker', { advice: true }); });
    }
    paint();
    var hasPin = !!(window._tradePinStored && window._tradePinStored());
    if (!hasPin || !window._tradeAccountInfo || !window._tradeFetch) return;
    try {
      var acct = await window._tradeAccountInfo(false, false);   // NO interactivo
      if (!acct || acct.error) return;
      var positions = [];
      try { var rp = await window._tradeFetch('/api/trade/positions/detail', {}, false); var dp = await rp.json(); if (Array.isArray(dp)) positions = dp; } catch (e) {}
      var m = _computePortfolio(acct, positions);
      var bname = (en ? 'Broker account' : 'Cuenta del bróker') +
        (m.paper === false ? (en ? ' (REAL money)' : ' (dinero REAL)') : m.paper === true ? (en ? ' (paper)' : ' (papel)') : '');
      lines.push('🔒 ' + _pfLine(bname, m.equity, m.pnlPct, m.n, en) + ' <a href="#" id="bcp-home-adv">' + (en ? 'Advice' : 'Consejos') + '</a>');
      paint();
    } catch (e) {}
  }

  function stageBroker(s, arg) {
    arg = arg || {};
    var en = ckLang() === 'en';
    s.innerHTML = backBar(tb('broker')) +
      '<div class="bcp-inner" style="max-width:980px">' +
        '<div id="bcp-bk-confirm"></div>' +
        '<div id="bcp-bk-acct"><div class="bcp-loading">' + tb('loading') + '</div></div>' +
        '<div id="bcp-bk-report"></div>' +
        // CAPA PROACTIVA: consejos de Khipu (Opus 4.8), "sugiere y tú decides".
        '<div style="margin-top:18px">' +
          '<button id="bcp-bk-advbtn" class="bcp-back" style="border-color:rgba(0,224,255,.4);color:#00E0FF;font-weight:700">🧠 ' + (en ? 'Khipu advice' : 'Consejos de Khipu') + '</button>' +
          '<div id="bcp-bk-advice" style="margin-top:12px"></div>' +
        '</div>' +
        '<div class="bcp-two" style="margin-top:18px">' +
          '<div><div class="bcp-lh">' + tb('positions') + '</div><div id="bcp-bk-pos"><div class="bcp-loading">…</div></div></div>' +
          '<div><div class="bcp-lh">' + tb('orders') + '</div><div id="bcp-bk-ord"><div class="bcp-loading">…</div></div></div>' +
        '</div>' +
      '</div>';
    var advBtn = s.querySelector('#bcp-bk-advbtn');
    if (advBtn) advBtn.addEventListener('click', function () { _fetchAdvice(document.getElementById('bcp-bk-advice')); });
    if (arg.advice) { try { _fetchAdvice(s.querySelector('#bcp-bk-advice')); } catch (e) {} }
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

  // Diálogo pop-up de confirmación abierto (engine/toast.js) para _pendingOrder
  var _confirmH = null;
  function closeConfirmDialog() {
    if (_confirmH) { var h = _confirmH; _confirmH = null; try { h.close('dismissed'); } catch (e) {} }
  }

  // confirmación — SOLO el clic en Confirmar (o el «sí» por voz) envía la orden.
  // Con engine/toast.js es un POP-UP (mismo diálogo que el panel de trading:
  // lado, activo, monto, cuenta 🧪/🔴, fichas de monto rápido); sin él, la
  // tarjeta en línea de siempre.
  function renderTradeConfirm(o) {
    var box = document.getElementById('bcp-bk-confirm');
    if (!box || !o || !o.symbol) return;
    _pendingOrder = o;
    var KT = window.KhipuToast;
    if (KT && KT.confirmOrder) {
      closeConfirmDialog();
      box.innerHTML = '<div id="bcp-bk-cstatus" style="font-size:12.5px;color:#7C87A3;padding:2px 0 14px">' +
        esc(L('Esperando tu confirmación en la ventana emergente…', 'Waiting for your confirmation in the pop-up…')) + '</div>';
      var acctMode = (_bkAcct && typeof _bkAcct.paper === 'boolean') ? (_bkAcct.paper ? 'paper' : 'live') : undefined;
      var ord = { side: o.side, symbol: o.symbol, label: o.label, kind: o.kind, notional: o.notional, qty: o.qty, mode: acctMode };
      var handle = null;
      KT.confirmOrder(ord, {
        amounts: o.notional != null ? [100, 500, 1000, 5000] : null,
        onAmount: function (v) { if (_pendingOrder === o) o.notional = v; },
        onHandle: function (h) {
          handle = h;
          // la escena cambió mientras se resolvía el modo de la cuenta → no abrirlo huérfano
          if (_pendingOrder !== o || !document.getElementById('bcp-bk-confirm')) { h.close('dismissed'); return; }
          _confirmH = h;
        },
      }).then(function (yes) {
        if (_confirmH === handle) _confirmH = null;
        var why = handle && handle.reason;
        if (why === 'superseded') return;            // el «sí» por voz ya la está enviando
        if (_pendingOrder !== o) return;              // otra orden/escena tomó su lugar
        if (yes) { confirmPendingOrder(); return; }
        _pendingOrder = null;
        var b = document.getElementById('bcp-bk-confirm');
        if (!b) return;
        b.innerHTML = why === 'dismissed' ? '' : '<div style="color:#7C87A3;font-size:12.5px;padding:6px 0 16px">' + tb('canceled') + '</div>';
        setTimeout(function () { var b2 = document.getElementById('bcp-bk-confirm'); if (b2 && !_pendingOrder) b2.innerHTML = ''; }, 3000);
      });
      return;
    }
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
        '<div style="font-size:11.5px;color:#7C87A3;margin-bottom:12px">' + tb('marketOrder') + '</div>' +
        // chips de monto rápido (feedback Fabrizio: "más fácil invertir") — 1 toque
        // cambia el monto, el 2º confirma. Solo para órdenes en dólares (notional).
        (o.notional != null ? '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">' +
          [100, 500, 1000, 5000].map(function (v) {
            var on = Math.round(+o.notional) === v;
            return '<button class="bcp-amt" data-amt="' + v + '" style="padding:6px 15px;border-radius:999px;cursor:pointer;font-size:13px;font-weight:700;font-family:inherit;' +
              'border:1px solid ' + (on ? col : 'rgba(122,158,255,.25)') + ';background:' + (on ? col + '1f' : 'transparent') + ';color:' + (on ? col : '#9BA6C4') + '">$' + v.toLocaleString('en-US') + '</button>';
          }).join('') + '</div>' : '') +
        '<div style="display:flex;gap:10px">' +
          '<button id="bcp-bk-ok" class="bcp-back" style="border-color:' + col + '66;color:' + col + ';font-weight:700">' + tb('confirm') + '</button>' +
          '<button id="bcp-bk-no" class="bcp-back">' + tb('cancel') + '</button>' +
        '</div><div id="bcp-bk-cstatus" style="margin-top:10px;font-size:12.5px"></div></div>';
    paintConfirmBadge();   // pinta 🧪/🔴 en cuanto la cuenta esté cargada
    box.querySelectorAll('.bcp-amt').forEach(function (b) {
      b.addEventListener('click', function () {
        if (!_pendingOrder) return;
        _pendingOrder.notional = +b.getAttribute('data-amt');
        renderTradeConfirm(_pendingOrder);   // re-pinta con el nuevo monto resaltado
      });
    });
    box.querySelector('#bcp-bk-ok').addEventListener('click', confirmPendingOrder);
    box.querySelector('#bcp-bk-no').addEventListener('click', function () {
      _pendingOrder = null;
      box.innerHTML = '<div style="color:#7C87A3;font-size:12.5px;padding:6px 0 16px">' + tb('canceled') + '</div>';
      setTimeout(function () { var b = document.getElementById('bcp-bk-confirm'); if (b && !_pendingOrder) b.innerHTML = ''; }, 3000);
    });
  }

  function confirmPendingOrder() {
    var o = _pendingOrder;
    if (!o) return;
    var en = ckLang() === 'en';
    var ok = document.getElementById('bcp-bk-ok'), no = document.getElementById('bcp-bk-no');
    var stEl = document.getElementById('bcp-bk-cstatus');
    if (ok) ok.disabled = true;
    if (no) no.disabled = true;
    // (los avisos pop-up de enviando/enviada/ejecutada los da window._executeTradeOrder)
    // OPTIMISTA (feedback Fabrizio: "invertí y se quedó cargando"): mostramos
    // ENVIADA ✓ al instante y ejecutamos en segundo plano; si el bróker la
    // rechaza, avisamos claramente. Se siente inmediato.
    _pendingOrder = null;
    if (stEl) { stEl.style.color = UP; stEl.textContent = '✓ ' + tb('sent') + (en ? ' (confirming…)' : ' (confirmando…)'); }
    setTimeout(function () { loadBroker(false, true); }, 900);   // refresca posiciones pronto
    var exec = window._executeTradeOrder ? window._executeTradeOrder(o)
      : Promise.resolve({ ok: false, error: L('trading no disponible', 'trading unavailable') });
    exec.then(function (r) {
      var st = document.getElementById('bcp-bk-cstatus');   // pudo cambiar de escena
      if (r && r.ok && r.broker_dup) {
        // el server devolvió la orden que YA existía (duplicate:true): no hay orden nueva
        if (st) { st.style.color = '#FFB300'; st.textContent = tb('brokerDup'); }
        setTimeout(function () { loadBroker(false, true); }, 1000);
      } else if (r && r.ok) {
        if (st) { st.style.color = UP; st.textContent = '✓ ' + tb('sent') + ' — ' + ((r.data && r.data.status) || 'accepted') + (r.dedup ? ' ' + tb('dedup') : ''); }
        setTimeout(function () { loadBroker(false, true); }, 1000);
      } else if (st) {
        st.style.color = DOWN;
        // ambigua (red/timeout/5xx) = NO es un rechazo: pudo haber entrado
        st.textContent = '⚠ ' + ((r && r.ambiguous) ? '' : (en ? 'The broker rejected it: ' : 'El bróker la rechazó: ')) + ((r && r.error) || 'error');
      }
    }).catch(function (e) {
      var st = document.getElementById('bcp-bk-cstatus');
      if (st) { st.style.color = DOWN; st.textContent = '⚠ ' + (en ? 'Order error: ' : 'Error en la orden: ') + ((e && e.message) || e); }
    });
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
              (en2 ? 'Enter the PIN you set as TRADE_PIN in Railway. It is remembered on this device for 12 hours.'
                   : 'Ingresa el PIN que configuraste como TRADE_PIN en Railway. Se recuerda 12 horas en este dispositivo.') + '</div>' +
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
          if (window._tradePinSave) window._tradePinSave(v);   // recordado 12 h (app.html)
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
    s.innerHTML = backBar(L('Investigación profunda', 'Deep research')) +
      '<div class="bcp-inner" style="max-width:820px">' +
        '<div class="bcp-simhd"><span class="big">🧠 ' + esc(question || L('Análisis profundo', 'Deep analysis')) + '</span></div>' +
        '<div id="bcp-deep-steps" style="display:flex;flex-direction:column;gap:7px;margin-bottom:18px"></div>' +
        '<div id="bcp-deep-result"></div>' +
      '</div>';
    if (!question) return;
    setState('think', L('Investigando', 'Researching'));

    fetch((window.BASE || '') + '/api/deep/analyze', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: question }),
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (d.error) { renderDeepError(d.error); return; }
      _deepTimer = setInterval(pollDeep, 2500);
      pollDeep();
    }).catch(function () { renderDeepError(L('No se pudo conectar con el servidor', 'Could not reach the server')); });

    function renderDeepError(msg) {
      var el = document.getElementById('bcp-deep-result');
      if (el) el.innerHTML = '<div class="bcp-loading" style="color:#FF4D6A">⚠ ' + esc(msg) + '</div>';
      setState('', L('Listo', 'Ready'));
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
          setState('', L('Listo', 'Ready'));
          var el = document.getElementById('bcp-deep-result');
          if (!el) return;
          if (d.result.error) { renderDeepError(d.result.error); return; }
          var simHTML = d.result.sim ?
            '<div class="bcp-grid3" style="margin:14px 0">' +
              '<div class="bcp-stat"><b style="color:#FF4D6A">' + d.result.sim.afectadas + '</b><span>' + L('afectadas si cae ', 'affected if it falls: ') + esc(d.result.sim.shock) + '</span></div>' +
              '<div class="bcp-stat"><b style="color:#E8EDFB;font-size:14px">' + esc((d.result.focos || []).join(', ').slice(0, 40) || '—') + '</b><span>' + L('foco', 'focus') + '</span></div>' +
              '<div class="bcp-stat"><b style="color:#E8EDFB;font-size:13px">' + esc(d.result.model || '') + '</b><span>' + L('modelo', 'model') + '</span></div>' +
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
    s.innerHTML = backBar(L('Lienzo', 'Canvas')) +
      '<div class="bcp-inner bcp-canvaswrap">' +
        '<div class="bcp-canvasbar">' +
          '<input id="bcp-cv-q" class="" type="text" autocomplete="off" placeholder="' + esc(L('Describe el gráfico o la tabla…  «top 10 por riesgo NRS»', 'Describe the chart or table…  “top 10 by NRS risk”')) + '" ' +
            'style="flex:1;min-width:0;background:var(--os-surface-2);border:1px solid var(--os-line);border-radius:999px;color:var(--os-ink);font-size:14px;padding:11px 16px;outline:none;font-family:inherit">' +
          '<button class="bcp-iconbtn" id="bcp-cv-go" style="width:auto;padding:0 18px;border-radius:999px;background:var(--os-btn);color:var(--os-btn-ink);font-size:13.5px;font-weight:600">✦ ' + L('Generar', 'Generate') + '</button>' +
        '</div>' +
        '<div id="bcp-cv-cards"></div>' +
      '</div>';
    var q = s.querySelector('#bcp-cv-q');
    function go() { var v = (q.value || '').trim(); if (v) cockpitCanvas(v); }
    s.querySelector('#bcp-cv-go').addEventListener('click', go);
    q.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); go(); } });
    if (query) { q.value = query; cockpitCanvas(query); } else { q.focus(); }
  }

  // (2026-10-02) Se eliminó _cvFallbackSpec: ante una falla de la IA dibujaba
  // "empresas de mayor riesgo" aunque la pregunta fuera otra (gráfico sin
  // relación presentado como respuesta). Ahora: KhipuLocalCharts.honest →
  // "no puedo responder esto con precisión sin IA" + la parcial correcta.

  var _cvSeq = 0;
  async function cockpitCanvas(query) {
    var cards = document.getElementById('bcp-cv-cards');
    if (!cards) return;
    return canvasInto(cards, query, 'afterbegin');
  }
  // FUSIÓN Khipu + Canvas (2026-10-04): el mismo generador pinta una tarjeta de gráfico
  // DENTRO de cualquier contenedor (la respuesta del chat, una ventana…).
  async function canvasInto(cards, query, where) {
    if (!cards || !query) return null;
    var cardId = 'bcpcv-' + (++_cvSeq);
    cards.insertAdjacentHTML(where || 'beforeend',
      '<div id="' + cardId + '" class="cv-card"><div class="cv-card-hdr"><div><div class="cv-card-title">' + esc(query) +
      '</div><div class="cv-card-sub">' + L('Generando…', 'Generating…') + '</div></div></div>' +
      '<div style="height:180px;display:flex;align-items:center;justify-content:center"><div class="cv-spinner"></div></div></div>');
    // 1º: generador LOCAL determinista (0 ms, 0 errores) — la IA solo para lo exótico
    // (router de intención: solo responde local si la confianza es alta)
    var local = window.KhipuLocalCharts && window.KhipuLocalCharts.try(query);
    if (local && window._cvRenderCard) { window._cvRenderCard(cardId, query, local, 'local'); return; }
    // 2º: local con datos del servidor (precio histórico, estados anuales, cripto)
    if (window.KhipuLocalCharts && window.KhipuLocalCharts.tryAsync) {
      var localA = await window.KhipuLocalCharts.tryAsync(query);
      if (localA && window._cvRenderCard) { window._cvRenderCard(cardId, query, localA, 'local'); return; }
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
      if (ct.indexOf('application/json') < 0) throw new Error(L('El servidor está ocupado. Reintenta en ~1 min.', 'The server is busy. Try again in ~1 min.'));
      var d = await r.json();
      if (d.error) throw new Error(d.error);
      if (window._cvRenderCard) window._cvRenderCard(cardId, query, d.spec, d.model);
    } catch (e) {
      // Sin IA: respuesta HONESTA + la parcial correcta más cercana (nunca un
      // gráfico por defecto sin relación con la pregunta).
      try {
        var hs = (window.KhipuLocalCharts && window.KhipuLocalCharts.honest) ? await window.KhipuLocalCharts.honest(query, e && e.message) : null;
        if (hs && window._cvRenderCard) { window._cvRenderCard(cardId, query, hs, 'local'); return; }
      } catch (e2) {}
      var card = document.getElementById(cardId);
      if (card) card.innerHTML = '<div class="cv-card-hdr"><div class="cv-card-title">' + esc(query) + '</div></div>' +
        '<div style="padding:20px;text-align:center;color:#f87171;font-size:13px">⚠ ' + esc(e.message) + '</div>';
    }
    return cardId;
  }

  /* ══ SIMULACIÓN POR AGENTES (motor interno, desde la terminal de Khipu) ══
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

  var CHAN = { direct: ['#FF4D6A', 'Golpe directo', 'Direct hit'], substitute: ['#2BE38B', 'Podría ganar cuota', 'Could gain share'],
    customer: ['#FFB300', 'Cliente: pierde suministro', 'Customer: loses supply'], second_order: ['#9BA6C4', 'Efecto de segundo orden', 'Second-order effect'],
    supplier: ['#7AA2FF', 'Proveedor: cambian sus pedidos', 'Supplier: its orders change'] };
  function simBox(inner, col) {
    return '<div style="border:1px solid ' + (col || 'rgba(122,158,255,.16)') + ';border-radius:14px;background:rgba(11,18,34,.55);padding:14px 16px;margin-bottom:14px">' + inner + '</div>';
  }
  function essentialsHTML(d, en) {
    var sm = d.summary || {}, bits = [];
    if (d.theme) bits.push('<div style="font-size:13.5px;color:#E8EDFB"><b>' + (en ? 'At stake: ' : 'En juego: ') + '</b>' + esc(d.theme) + '</div>');
    if (d.actor) bits.push('<div style="font-size:12.5px;color:#9BA6C4">' + (en ? 'Who acts: ' : 'Quién actúa: ') + esc(d.actor) + '</div>');
    if (d.mechanism) bits.push('<div style="font-size:13px;line-height:1.55;color:#C9D2EA;margin-top:6px">💡 ' + esc(d.mechanism) + '</div>');
    if (sm.n_hit != null) {
      bits.push('<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px">' +
        '<span style="padding:4px 10px;border-radius:999px;border:1px solid ' + DOWN + '66;color:' + DOWN + ';font-size:12px;font-weight:700">▼ ' + sm.n_hit + (en ? ' hit' : ' perjudicadas') + '</span>' +
        '<span style="padding:4px 10px;border-radius:999px;border:1px solid ' + UP + '66;color:' + UP + ';font-size:12px;font-weight:700">▲ ' + sm.n_benefit + (en ? ' could benefit' : ' podrían ganar') + '</span>' +
        (sm.sectors && sm.sectors.length ? '<span style="padding:4px 10px;border-radius:999px;border:1px solid rgba(122,158,255,.3);color:#9BA6C4;font-size:12px">' + sm.sectors.length + (en ? ' sectors' : ' sectores') + '</span>' : '') + '</div>');
    }
    return bits.length ? simBox('<div class="bcp-lh" style="margin-top:0">' + (en ? 'The essentials' : 'Lo esencial') + '</div>' + bits.join('')) : '';
  }
  function sidesHTML(impacts, en) {
    var lose = impacts.filter(function (x) { return x.pct < 0; }).slice(0, 5), win = impacts.filter(function (x) { return x.pct > 0; }).slice(0, 5);
    if (!lose.length && !win.length) return '';
    function col(title, arr, c) {
      return '<div style="flex:1 1 240px;min-width:0"><div class="bcp-lh" style="color:' + c + ';margin-top:0">' + title + '</div>' +
        (arr.length ? arr.map(function (x) { return '<div style="display:flex;justify-content:space-between;gap:8px;font-size:13px;padding:3px 0"><span style="overflow-wrap:anywhere">' + esc(x.label) + '</span><b style="color:' + c + '">' + (x.pct > 0 ? '+' : '') + x.pct + '%</b></div>'; }).join('')
          : '<div style="font-size:12px;color:#7C87A3">' + (en ? 'None clear' : 'Ninguna clara') + '</div>') + '</div>';
    }
    return simBox('<div style="display:flex;gap:18px;flex-wrap:wrap">' + col(en ? '▼ Most hit' : '▼ Más perjudicadas', lose, DOWN) + col(en ? '▲ Possible winners' : '▲ Posibles ganadoras', win, UP) + '</div>');
  }
  function quotesHTML(d, en) {
    var q = Array.isArray(d.quotes) ? d.quotes : [];
    if (!q.length) return '';
    return '<div class="bcp-lh">' + (en ? 'What the agents say' : 'Lo que dicen los agentes') + '</div>' +
      q.map(function (x) { return '<div style="border-left:3px solid ' + NEON + ';padding:6px 12px;margin:0 0 8px;background:rgba(0,224,255,.04);border-radius:0 10px 10px 0;font-size:13px;color:#D5DCF0"><b>' + esc(x.agent) + ':</b> «' + esc(x.quote) + '»</div>'; }).join('');
  }
  function timelineHTML(d, en) {
    var r = Array.isArray(d.rounds) ? d.rounds : [];
    if (!r.length) return '';
    return '<div class="bcp-lh">' + (en ? 'How it unfolds' : 'Cómo se desarrolla') + '</div>' + simBox(r.map(function (x) {
      return '<div style="display:flex;gap:10px;align-items:flex-start;margin:4px 0"><span style="flex:0 0 22px;height:22px;border-radius:50%;background:' + NEON + '22;color:' + NEON + ';font-size:11px;font-weight:800;display:flex;align-items:center;justify-content:center">' + esc(x.round) + '</span>' +
        '<div style="font-size:13px;line-height:1.5;color:#C9D2EA">' + (x.events || []).map(esc).join('<br>') + '</div></div>';
    }).join(''));
  }
  function watchHTML(d, en) {
    var w = Array.isArray(d.watch) ? d.watch : [];
    if (!w.length) return '';
    return '<div class="bcp-lh">👁 ' + (en ? 'What to watch' : 'Qué vigilar') + '</div>' + simBox('<ul style="margin:0;padding-left:18px;font-size:13px;line-height:1.6;color:#C9D2EA">' +
      w.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>');
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
        (x.channel && CHAN[x.channel] ? '<div class="bcp-agwhy"><span style="color:' + CHAN[x.channel][0] + ';font-weight:700">' + esc(en ? CHAN[x.channel][2] : CHAN[x.channel][1]) + '</span>' +
          (x.path && x.path.indexOf('→') >= 0 ? ' · ' + esc(x.path) : '') + '</div>'
          : (x.rationale ? '<div class="bcp-agwhy">' + esc(x.rationale) + '</div>' : '')) +
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
    var simNote = '<div style="margin-bottom:12px;padding:8px 12px;border:1px dashed #f59e0b;border-radius:10px;background:rgba(245,158,11,.08);font-size:11.5px;color:#fbbf24;line-height:1.5">🧪 ' +
      (en ? 'SIMULATION of a hypothetical scenario: the % are model estimates, not real prices nor recommendations.'
          : 'SIMULACIÓN de un escenario hipotético: los % son estimaciones del modelo, no precios reales ni recomendaciones.') +
      (d.fallback ? ' <b>' + (d.structural
        ? (en ? 'No AI available: structural estimate (who produces it, who acts, and the strength of each supply-chain link).'
              : 'Sin IA disponible: estimación estructural (quién lo produce, quién actúa y la fuerza de cada vínculo de la cadena).')
        : (en ? 'No AI was available: rough fixed-magnitude estimate by supply-chain proximity.'
              : 'Sin IA disponible: estimación gruesa de magnitud fija según cercanía en la cadena.')) + '</b>' : '') + '</div>';
    return modelHTML + simNote + essentialsHTML(d, en) + narrHTML + sidesHTML(impacts, en) + agentsHTML + quotesHTML(d, en) +
      timelineHTML(d, en) + watchHTML(d, en) +
      '<div class="bcp-lh">' + (en ? 'Estimated impact by company (and how it reaches each one)' : 'Impacto estimado por empresa (y cómo le llega)') + '</div>' + impactsHTML;
  }

  function stageAgentSim(s, arg) {
    arg = arg || {};
    var en = ckLang() === 'en';
    var scen = arg.scenario || '';
    var title = en ? 'Agent simulation' : 'Simulación por agentes';
    s.innerHTML = backBar(title) +
      '<div class="bcp-inner" style="max-width:1040px">' +
        '<div class="bcp-simhd"><span class="big">🧪 ' + esc(scen || title) + '</span>' +
          '<span class="kind" style="background:' + NEON + '22;color:' + NEON + '">' + (en ? 'Agents' : 'Agentes') + '</span>' +
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
  // devuelve la promesa del resultado para que Khipu narre el consenso.
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
  // devuelve la promesa del informe para que Khipu narre la tesis.
  // OJO: NO usar el nombre window._openResearch — app.html ya lo usa para el
  // panel "📄 SEC" (10-K de EDGAR). Aquí es la investigación PROFUNDA de la Cabina.
  window._openDeepResearch = function (id, lang) {
    ensureShell();
    var p = fetchResearch(id, lang);
    openCockpit({ kind: 'research', arg: { id: id, promise: p } });
    return p || Promise.resolve({ ok: false, error: 'no fetch' });
  };

  // ══ CHAT: hilo de conversación (engine/khipu_chat.js → /api/khipu/chat) ══
  var _thread = null;
  function chatThread() {
    if (!_thread) {
      _thread = document.createElement('div');
      _thread.id = 'bcp-thread';
      _thread.className = 'kc-thread';
      if (window.KhipuChat) window.KhipuChat.ensureStyles();
    }
    return _thread;
  }
  // el hilo va a la escena 'chat' (pantalla completa) o al dock (sobre la barra)
  function _placeThread(kind) {
    var th = chatThread();
    _watchThread();
    var dock = document.getElementById('bcp-chatdock');
    if (!dock) return;
    // Khipus OS: con el chat al centro el hilo vive SIEMPRE en la columna central (el dock no se usa)
    if (_centerBox && chatCentered()) {
      var cb = _centerBox.querySelector('.kos-chatbody');
      if (cb && th.parentNode !== cb) cb.appendChild(th);
      dock.classList.remove('show');
      _syncHasMsgs();
      if (cb && th.children.length) setTimeout(function () { cb.scrollTop = cb.scrollHeight; }, 30);
      return;
    }
    var D = deskActive() ? desk() : null;
    if (kind === 'chat' || (D && D.has('chat'))) { dock.classList.remove('show'); return; }   // stageChat / la ventana 💬 lo adopta
    var bd = dock.querySelector('.bd');
    if (th.parentNode !== bd) bd.appendChild(th);
    // en el escritorio la conversación queda SIEMPRE abajo (sin dejar de ser un chatbot)
    dock.classList.toggle('show', th.children.length > 0 && (!!D || kind !== 'empty'));
    if (th.children.length) setTimeout(function () { bd.scrollTop = bd.scrollHeight; }, 30);
  }
  function stageChat(s) {
    var en = ckLang() === 'en';
    s.innerHTML = backBar(en ? 'Conversation' : 'Conversación') +
      '<div class="bcp-chatwrap"><div class="bcp-chattools"><button type="button" id="bcp-chat-clear">' +
      esc(en ? '🧹 New conversation' : '🧹 Nueva conversación') + '</button></div></div>';
    var th = chatThread();
    s.querySelector('.bcp-chatwrap').appendChild(th);
    s.querySelector('#bcp-chat-clear').addEventListener('click', function () {
      if (window.KhipuChat) window.KhipuChat.clear();
      th.innerHTML = '';
      if (deskActive()) desk().closeKind('chat'); else stage('empty');
    });
    setTimeout(function () { s.scrollTop = s.scrollHeight; }, 30);
  }
  // dónde se ve la respuesta: en el escritorio, en el dock de abajo (o en la
  // ventana 💬 si ya está abierta); en la Cabina clásica, en la escena 'chat'
  function _chatWin() {
    if (!deskActive()) return null;
    return desk().list().filter(function (w) { return w.kind === 'chat'; })[0] || null;
  }
  function _ensureThread() {
    if (chatCentered()) { _revealChat(); _placeThread(_curKind || 'empty'); return; }
    if (deskActive()) {
      // si la ventana 💬 existe (minimizada o detrás de otra hoja), la respuesta no se vería: al frente
      var cw = _chatWin();
      if (cw) desk().focus(cw.id);
      _placeThread(_curKind || 'empty');
      return;
    }
    if (_curKind !== 'chat') stage('chat');
  }
  // la respuesta abrió una ventana (X-Ray, gráfico…) encima de la ventana 💬 → en pantallas
  // anchas van lado a lado (resultado a la izquierda, conversación a la derecha); si no, 💬 al frente
  function _chatBeside() {
    if (chatCentered()) return;   // Khipus OS: la ventana ya cayó en un flanco; el chat no se tapa
    var cw = _chatWin(); if (!cw) return;
    var D = desk(), other = D.focused();
    if (!other || other === cw.id) return;
    if (D.autoOn && D.autoOn()) { D.focus(cw.id); return; }   // el orden automático ya los puso lado a lado
    if (!D.isMobile() && (window.innerWidth || 0) >= 1100) { D.snap(other, 'left'); D.snap(cw.id, 'right'); }
    D.focus(cw.id);
  }
  // acción devuelta por el cerebro → escena de la Cabina (la respuesta queda en el dock)
  function runChatAction(a) {
    if (!a || !a.type) return;
    var opened = true;
    if (a.type === 'open_xray') stage('xray', a.arg);
    else if (a.type === 'navigate') stage('graph', a.arg);
    else if (a.type === 'compare') stage('compare', a.arg);
    else if (a.type === 'chart') stage('canvas', a.arg);
    else if (a.type === 'agent_sim') stage('agentsim', { scenario: a.arg, seeds: extractSeeds(a.arg) });
    else if (a.type === 'broker') stage('broker');
    else { opened = false; if (window.KhipuChat) window.KhipuChat.runAction(a); }
    if (opened) setTimeout(_chatBeside, 60);   // la ventana nueva no debe tapar la conversación
  }
  // pregunta libre → cerebro con herramientas
  function chatAsk(text) {
    var K = window.KhipuChat;
    if (!K) { stage('deep', text); return; }
    _ensureThread();
    var th = chatThread();
    K.appendUser(th, text, window.KhipuPick && window.KhipuPick.agentOf ? window.KhipuPick.agentOf(text) : null);
    _ensureThread();
    var pend = K.appendPending(th);
    setState('think', L('Pensando', 'Thinking'));
    K.send(text).then(function (d) {
      // en el celular (≤ 760 px, ventanas = hojas) NO se auto-ejecuta: la vista nueva taparía la
      // respuesta (queda como botón); en escritorio la respuesta sigue visible (centro o dock)
      // "solo chat" (tablet): una ventana automática taparía la respuesta recién llegada → solo botones
      K.fillReply(pend, d, { onAction: runChatAction, autoRun: (window.innerWidth || 1024) > 760 && !(chatCentered() && !isCentered()), retry: true });
      var rb = pend.querySelector('.kc-retry'); if (rb) rb.addEventListener('click', function () { chatAsk(text); });
      setState('', L('Listo', 'Ready'));
    }).catch(function (e) {
      K.fillError(pend, (e && e.message) || String(e));
      setState('', L('Listo', 'Ready'));
    });
  }
  // agente con chip (💼 comité de cartera): responde EN el hilo, sin abrir pantallas
  function chatAgent(text, route) {
    var K = window.KhipuChat;
    if (!K || !K.askAgent) { chatAsk(text); return; }
    _ensureThread();
    var th = chatThread();
    K.appendUser(th, text, K.agentInfo(route));
    _ensureThread();
    var pend = K.appendPending(th);
    setState('think', L('El comité mide tu cartera', 'The committee is measuring your portfolio'));
    K.askAgent(route).then(function (d) {
      K.fillReply(pend, d, { onAction: runChatAction, autoRun: false, retry: true });
      var rb = pend.querySelector('.kc-retry'); if (rb) rb.addEventListener('click', function () { chatAgent(text, route); });
      setState('', L('Listo', 'Ready'));
    }).catch(function (e) {
      K.fillError(pend, (e && e.message) || String(e));
      setState('', L('Listo', 'Ready'));
    });
  }
  // respuesta de un comando KHIPU (no-escena) → al hilo, como cualquier respuesta
  function commandToThread(text, r) {
    var K = window.KhipuChat;
    if (!K) return;
    _ensureThread();
    var th = chatThread();
    K.appendUser(th, text);
    _ensureThread();
    var el = K.appendPending(th);
    var acts = ((r && r.actions) || []).map(function (a) {
      if (a.type === 'second_brain' || a.type === 'xray') return { type: 'open_xray', arg: a.arg };
      if (a.type === 'tkg_object') return null;
      return a;
    }).filter(Boolean);
    K.fillReply(el, { answer: (r && r.answer) || L('Listo.', 'Done.'), actions: acts }, { onAction: runChatAction });
    ((r && r.actions) || []).forEach(function (a) {
      if (a.type === 'tkg_object') {
        if (window._surface) window._surface('tab', 'tkg');
        setTimeout(function () { if (window.__tkgOpenObj) window.__tkgOpenObj(a.arg); }, 250);
      }
    });
  }
  function _resolveHit(q) {
    if (window.KhipuResolve) { var r = window.KhipuResolve.find(q); if (r && r.node) return r; return null; }
    var n = resolveNode(q); return n ? { node: n, score: 90 } : null;
  }

  // ══ ENRUTADOR de lo que pides (texto) ══
  // Solo atajos EXPLÍCITOS y de alta precisión (engine/khipu_chat.js:classify);
  // todo lo demás —y SIEMPRE las preguntas— va al cerebro de Khipu. Antes una
  // cadena de regex sueltas secuestraba preguntas normales y lo que no calzaba
  // terminaba dibujado como gráfico (feedback de Fabrizio, 2026-09-30).
  function ask(text) {
    text = (text || '').trim(); if (!text) return;
    ensureShell();
    var K = window.KhipuChat;
    var route = K ? K.classify(text, {
      resolve: _resolveHit,
      tryParse: (window.KHIPU && window.KHIPU.tryParse) ? window.KHIPU.tryParse : null,
      parseTrade: window._parseTradeCommand || null,
    }) : { kind: 'brain' };

    if (K && K.remember && route.kind !== 'none' && route.kind !== 'brain' && route.kind !== 'command' && route.kind !== 'agentask') {
      try {
        K.remember('user', text);
        var what = { xray: L('Abrí la radiografía de ', 'Opened the X-Ray of '), shock: L('Simulé la caída de ', 'Simulated the failure of '),
                     compare: L('Abrí la comparación ', 'Opened the comparison '), research: L('Abrí la investigación de ', 'Opened the research on '),
                     dossier: L('Abrí el dossier de ', 'Opened the dossier of '), terminal: L('Abrí la terminal de ', 'Opened the terminal for ') }[route.kind];
        var lbl = route.id ? ((window.NODE_BY_ID || {})[route.id] || {}).label || route.id : (route.a ? route.a + ' vs ' + route.b : (route.screen || ''));
        if (what) K.remember('assistant', what + lbl + '.');
      } catch (e) {}
    }
    switch (route.kind) {
      case 'none': return;
      case 'demo': demoStart(); return;
      case 'trade':
        if (window._openBrokerConfirm) window._openBrokerConfirm(route.parsed); else stage('broker');
        return;
      case 'account': stage('broker'); return;
      case 'agentask': chatAgent(text, route); return;
      case 'command':
        Promise.resolve(route.pending).then(function (r) {
          if (r && r.actions && r.actions.length === 1 && dispatchAction(r.actions[0])) return;
          commandToThread(text, r);
        }).catch(function () { chatAsk(text); });
        return;
      case 'chart': stage('canvas', route.spec); return;
      case 'screen':
        // el Universo es un overlay que ya queda ENCIMA de Khipus OS: no hace falta cerrarlo
        if (route.screen === 'universe') { if (window._go3D) window._go3D(); return; }
        if (route.screen === 'portfolios') { stage('portfolios'); return; }
        stage(route.screen); return;
      case 'shock': stage('sim', { id: route.id, kind: 'collapse' }); return;
      case 'xray': stage('xray', route.id); return;
      case 'compare': stage('compare', { a: route.a, b: route.b }); return;
      case 'agentsim': stage('agentsim', { scenario: route.scenario, seeds: extractSeeds(route.scenario) }); return;
      case 'research': stage('research', { id: route.id }); return;
      case 'dossier': {
        var dn = (window.NODE_BY_ID || {})[route.id];
        if (window._surface) window._surface('dossier', (dn && dn.mkt) || route.id);
        else if (window.openFinCard) window.openFinCard((dn && dn.mkt) || route.id);
        return;
      }
      case 'terminal': {
        var tn = (window.NODE_BY_ID || {})[route.id];
        stage('terminal', { ticker: (tn && tn.mkt) || route.id }); return;
      }
    }
    chatAsk(text);
  }

  // convierte una acción del parser KHIPU en escena
  function dispatchAction(act) {
    if (!act || !act.type) return false;
    if (act.type === 'xray' && act.arg) { stage('xray', act.arg); return true; }
    if (act.type === 'compare' && act.arg) { stage('compare', { a: act.arg.a, b: act.arg.b }); return true; }
    if (act.type === 'insights') { stage('insights'); return true; }
    if (act.type === 'livesim' && act.arg) { stage('sim', { id: act.arg.id || act.arg, kind: act.arg.kind || 'collapse' }); return true; }
    if (act.type === 'stress' && act.arg && window._surface) { window._surface('stress', act.arg); return true; }
    if (act.type === 'navigate' && act.arg) { stage('graph', act.arg); return true; }
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
    // abrir Khipus OS = salir de la "Vista clásica" (si se había elegido en esta sesión)
    try { sessionStorage.removeItem('kh_os_classic'); } catch (e) {}
    var was = open;
    ensureShell();
    var ov = document.getElementById('bcp-ov');
    ov.classList.add('show');
    open = true;
    _syncClassicClass(ov);
    if (!was) {
      relabelShell(ov);   // idioma al día (la cáscara se construyó una sola vez)
      mountCockpitOrb();
      if (deskActive()) desk().resume();   // las ventanas vuelven a adoptar grafo/terminal/etc.
      _balStart();
    }
    if (initial && initial.kind) stage(initial.kind, initial.arg);
    // pantalla de inicio vacía o ya mostrada → se re-pinta (textos en el idioma actual);
    // si YA estaba abierta no se re-pinta nada (⌘K / el botón de Khipu solo enfocan)
    else if (!was && (!document.getElementById('bcp-stage').children.length || _curKind === 'empty')) stage('empty');
    setTimeout(function () { var i = document.getElementById('bcp-input'); if (i && !palIsOpen()) i.focus(); }, 60);
  }
  function close() {
    closeConfirmDialog();
    palClose(true); _popClose(); _balStop();
    if (deskActive()) { parkAdopted(); desk().suspend(); }   // paneles a su pestaña; las ventanas recuerdan re-adoptarlos
    else restoreAdopted();   // devolver grafo/terminal a su sitio original
    _scalpStop();       // detener el polling de scalping al cerrar la Cabina
    demoStop();         // cortar la demostración (timers + voz) al cerrar
    stopCockpitOrb();
    var ov = document.getElementById('bcp-ov');
    if (ov) ov.classList.remove('show');
    open = false;
    var btn = document.getElementById('bcp-mic');
    if (btn && btn.classList.contains('on') && window.BixbyVoice && window.BixbyVoice.stop) { window.BixbyVoice.stop(); btn.classList.remove('on'); }
  }
  // "Vista clásica" (menú de tus iniciales / paleta): cierra Khipus OS y la app vieja de pestañas
  // queda hasta que el usuario lo vuelva a abrir (botón de Khipu o ⌘K) — recordado en esta sesión
  function toClassicView() {
    try { sessionStorage.setItem('kh_os_classic', '1'); } catch (e) {}
    close();
    try {
      if (window.KhipuToast && window.KhipuToast.show) window.KhipuToast.show({ kind: 'info', title: L('Vista clásica', 'Classic view'),
        body: L('Para volver a Khipus OS toca el botón de Khipu (arriba a la derecha) o pulsa ' + (_isMac() ? '⌘K' : 'Ctrl+K') + '.',
                'To go back to Khipus OS tap the Khipu button (top right) or press ' + (_isMac() ? '⌘K' : 'Ctrl+K') + '.') });
    } catch (e) {}
  }
  // ¿Khipus OS está al frente? (otro overlay —comité, investigación, órdenes, confirmaciones— maneja su Esc)
  function _osOnTop() {
    try {
      var el = document.elementFromPoint(Math.round((window.innerWidth || 0) / 2), Math.round((window.innerHeight || 0) / 2));
      var ov = document.getElementById('bcp-ov');
      return !!(el && ov && ov.contains(el));
    } catch (e) { return true; }
  }
  // Teclado (fase de captura: antes que el ⌘K de command_center.js, que abre la Cabina):
  //  · ⌘K / Ctrl+K con Khipus OS al frente → paleta (abrir/cerrar)
  //  · Esc NUNCA cierra Khipus OS: cierra la paleta, un menú, la demostración o la ventana enfocada
  //    (el ⊞ del escritorio y su selector de acomodo ya se cerraron en desktop.js, que va antes)
  document.addEventListener('keydown', function (e) {
    if (!open) return;
    var k = e.key;
    if ((e.metaKey || e.ctrlKey) && !e.altKey && !e.shiftKey && (k === 'k' || k === 'K')) {
      if (!palIsOpen() && !_osOnTop()) return;
      e.preventDefault(); e.stopPropagation();
      if (palIsOpen()) palClose(); else palOpen('');
      return;
    }
    if (k !== 'Escape') return;
    if (palIsOpen()) { e.preventDefault(); e.stopPropagation(); palClose(); return; }
    if (_popIsOpen()) { e.preventDefault(); e.stopPropagation(); _popClose(); return; }
    if (_demo.on) { e.stopPropagation(); demoStop(); return; }
    if (!_osOnTop()) return;
    var t = e.target;
    if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName || ''))) return;   // no borrar lo que escribes
    if (deskActive()) {
      var f = desk().focused();
      if (f) { e.preventDefault(); desk().close(f); }
      return;
    }
    if (_curKind && _curKind !== 'empty') stage('empty');   // Cabina clásica: Esc vuelve al inicio
  }, true);
  /* ══ MODO DEMOSTRACIÓN ═══════════════════════════════════════════════════
     Khipu maneja la app SOLO y va narrando lo que hace, paso a paso — para
     enseñar el producto (inversionistas) sin depender de ElevenLabs:
     - la narración SIEMPRE se ve ESCRITA en pantalla (máquina de escribir), así
       funciona aunque no haya voz premium contratada;
     - además la lee la voz NATIVA del navegador (speechSynthesis, gratis). Si
       la voz premium ya está conversando (mic encendido), se calla para no
       pisarla → el día que ElevenLabs esté activo, el demo no cambia.
     Controles: pausar/seguir · siguiente · silenciar · salir (Esc). ══ */
  // muted:true por defecto — la narración VISUAL es el show; la voz del
  // navegador (robótica) solo si el usuario la pide con 🔇→🔊. Con la voz
  // premium de ElevenLabs activa, jamás se le habla encima.
  var _demo = { on: false, i: -1, t: null, typer: null, paused: false, muted: true, steps: [] };

  function _demoNode(name) {
    try { var n = resolveNode(name); return n ? n.id : null; } catch (e) { return null; }
  }

  function demoSteps() {
    var en = ckLang() === 'en';
    var nvda = _demoNode('Nvidia'), tsmc = _demoNode('TSMC');
    return en ? [
      { say: "I'm Khipu. I watch nearly a thousand companies across the AI supply chain — chips, cloud, space and nuclear. Let me show you what I do in one minute.",
        act: function () { stage('empty'); } },
      { say: "This is the live map. Every dot is a company; every line is a real dependency — who fabricates for whom, who provides the cloud, who sells the power.",
        act: function () { stage('graph'); } },
      { say: "I can take any company apart. Here's Nvidia: what it depends on, who depends on it, and how fragile that makes it.",
        act: function () { if (nvda) stage('xray', nvda); else stage('graph'); } },
      { say: "Now the important part. What happens if TSMC falls? I shock it and propagate the damage through the whole chain, hop by hop.",
        act: function () { if (tsmc) stage('sim', { id: tsmc, kind: 'collapse' }); else stage('graph'); } },
      { say: "And this is what I see on my own: the active systemic factors and who they hit. It isn't a dashboard — it's a simulation running live.",
        act: function () { stage('insights'); } },
      { say: "I also follow the market and crypto in real time, so the graph and the prices are the same story.",
        act: function () { stage('market'); } },
      { say: "And you can invest from right here, on a simulated account, without leaving my screen.",
        act: function () { stage('broker'); } },
      { say: "That's Khipu. Ask me anything: “break down Nvidia”, “what if TSMC falls?”, “show me opportunities”.",
        act: function () { stage('empty'); } },
    ] : [
      { say: 'Soy Khipu. Vigilo casi mil empresas de la cadena de la inteligencia artificial: chips, nube, espacio y nuclear. Te muestro en un minuto lo que hago.',
        act: function () { stage('empty'); } },
      { say: 'Este es el mapa vivo. Cada punto es una empresa; cada línea, una dependencia real: quién le fabrica a quién, quién le da la nube, quién le vende la energía.',
        act: function () { stage('graph'); } },
      { say: 'Puedo desarmar cualquier empresa. Aquí Nvidia: de quién depende, quién depende de ella, y qué tan frágil la deja eso.',
        act: function () { if (nvda) stage('xray', nvda); else stage('graph'); } },
      { say: 'Ahora lo importante. ¿Qué pasa si cae TSMC? Le pego el golpe y lo propago por toda la cadena, salto por salto.',
        act: function () { if (tsmc) stage('sim', { id: tsmc, kind: 'collapse' }); else stage('graph'); } },
      { say: 'Y esto es lo que veo yo solo: los factores sistémicos activos y a quién golpean. No es un tablero: es una simulación corriendo en vivo.',
        act: function () { stage('insights'); } },
      { say: 'También sigo el mercado y el cripto en tiempo real, para que el grafo y los precios cuenten la misma historia.',
        act: function () { stage('market'); } },
      { say: 'Y puedes invertir desde aquí mismo, en cuenta simulada, sin salir de mi pantalla.',
        act: function () { stage('broker'); } },
      { say: 'Eso es Khipu. Pregúntame lo que quieras: «desármame Nvidia», «¿qué pasa si cae TSMC?», «muéstrame oportunidades».',
        act: function () { stage('empty'); } },
    ];
  }

  function _demoDur(text) {
    // tiempo suficiente para leer/escuchar la frase y ver el resultado en pantalla
    return Math.max(5200, Math.min(12000, 3200 + String(text || '').length * 55));
  }

  function _demoSilence() {
    try { if (window.speechSynthesis) window.speechSynthesis.cancel(); } catch (e) {}
  }

  function _demoSpeak(text) {
    if (_demo.muted) return;
    try {   // si la voz premium está conversando, NO la pisamos
      var mic = document.getElementById('bcp-mic');
      if (mic && mic.classList.contains('on')) return;
    } catch (e) {}
    try {
      if (!window.speechSynthesis) return;
      window.speechSynthesis.cancel();
      var u = new SpeechSynthesisUtterance(text);
      u.lang = ckLang() === 'en' ? 'en-US' : 'es-ES';
      u.rate = 1.02;
      window.speechSynthesis.speak(u);
    } catch (e) {}
  }

  function _demoType(text) {
    var el = document.getElementById('bcp-demotxt');
    if (!el) return;
    clearInterval(_demo.typer);
    var i = 0;
    el.textContent = '';
    _demo.typer = setInterval(function () {
      if (i >= text.length) { clearInterval(_demo.typer); _demo.typer = null; return; }
      i += 1;
      el.textContent = text.slice(0, i);   // textContent → nunca inyecta HTML
    }, 16);
  }

  function _demoDots(n, cur) {
    var d = document.getElementById('bcp-demodots'); if (!d) return;
    var h = '';
    for (var k = 0; k < n; k++) {
      h += '<span class="bcp-demodot' + (k === cur ? ' on' : (k < cur ? ' done' : '')) + '"></span>';
    }
    d.innerHTML = h;
  }

  function _demoRenderBar() {
    var ov = ensureShell();
    var old = document.getElementById('bcp-demo');
    if (old) old.remove();
    var en = ckLang() === 'en';
    var wrap = document.createElement('div');
    wrap.id = 'bcp-demo';
    wrap.innerHTML =
      '<div class="bcp-demobox">' +
        '<div class="bcp-demoav"></div>' +
        '<div class="bcp-demotxtwrap">' +
          '<div class="bcp-demolabel">' + (en ? 'GUIDED DEMO' : 'DEMOSTRACIÓN GUIADA') + '</div>' +
          '<div class="bcp-demotxt" id="bcp-demotxt"></div>' +
        '</div>' +
        '<div class="bcp-democtl">' +
          '<span class="bcp-demodots" id="bcp-demodots"></span>' +
          '<button class="bcp-demobtn" id="bcp-demopause" title="' + (en ? 'Pause' : 'Pausar') + '">⏸</button>' +
          '<button class="bcp-demobtn" id="bcp-demonext" title="' + (en ? 'Next' : 'Siguiente') + '">⏭</button>' +
          '<button class="bcp-demobtn" id="bcp-demomute" title="' + (en ? 'Mute' : 'Silenciar') + '">' + (_demo.muted ? '🔇' : '🔊') + '</button>' +
          '<button class="bcp-demobtn" id="bcp-demoexit" title="' + (en ? 'Exit' : 'Salir') + '">✕</button>' +
        '</div>' +
      '</div>';
    ov.appendChild(wrap);
    wrap.querySelector('#bcp-demopause').addEventListener('click', demoToggle);
    wrap.querySelector('#bcp-demonext').addEventListener('click', function () { demoNext(); });
    wrap.querySelector('#bcp-demomute').addEventListener('click', demoMute);
    wrap.querySelector('#bcp-demoexit').addEventListener('click', function () { demoStop(); });
  }

  function demoStart() {
    if (!open) openCockpit();
    ensureShell();
    _demo.on = true; _demo.i = -1; _demo.paused = false;
    _demo.steps = demoSteps();
    _demoRenderBar();
    demoNext();
  }

  function demoNext() {
    if (!_demo.on) return;
    clearTimeout(_demo.t); _demo.t = null;
    _demo.i += 1;
    if (_demo.i >= _demo.steps.length) return demoStop(true);
    var st = _demo.steps[_demo.i];
    try { if (st.act) st.act(); } catch (e) {}
    // stage() re-dibuja el escenario, no el overlay — pero re-montamos por si acaso
    if (!document.getElementById('bcp-demo')) _demoRenderBar();
    _demoDots(_demo.steps.length, _demo.i);
    _demoType(st.say);
    _demoSpeak(st.say);
    if (!_demo.paused) {
      _demo.t = setTimeout(function () { demoNext(); }, st.t || _demoDur(st.say));
    }
  }

  function demoToggle() {
    if (!_demo.on) return;
    _demo.paused = !_demo.paused;
    var b = document.getElementById('bcp-demopause');
    if (b) b.textContent = _demo.paused ? '▶' : '⏸';
    if (_demo.paused) { clearTimeout(_demo.t); _demo.t = null; _demoSilence(); }
    else { _demo.t = setTimeout(function () { demoNext(); }, 1500); }
  }

  function demoMute() {
    _demo.muted = !_demo.muted;
    var b = document.getElementById('bcp-demomute');
    if (b) b.textContent = _demo.muted ? '🔇' : '🔊';
    if (_demo.muted) _demoSilence();
  }

  function demoStop(finished) {
    _demo.on = false;
    clearTimeout(_demo.t); _demo.t = null;
    clearInterval(_demo.typer); _demo.typer = null;
    _demoSilence();
    var el = document.getElementById('bcp-demo');
    if (el) el.remove();
    if (finished === true) { if (deskActive()) desk().closeAll(); stage('empty'); }
  }

  window.BixbyCockpit = {
    invoke: function (id) { invokeAgent(id); return _inv; },
    invoked: function () { return _inv; },
    open: openCockpit,
    close: close,
    isOpen: function () { return open; },
    stage: stage,
    render: render,
    canvasInto: canvasInto,
    ask: ask,
    agentSim: function (scenario) {
      if (!open) openCockpit();
      stage('agentsim', { scenario: String(scenario || ''), seeds: extractSeeds(String(scenario || '')) });
    },
    chat: function (text) { if (!open) openCockpit(); chatAsk(String(text || '')); },
    setState: setState,
    demo: demoStart,
    demoStop: demoStop,
    isDemo: function () { return !!_demo.on; },
    // ── Khipus OS (contrato §3.1 de docs/KHIPUS_OS.md) ──
    registerKind: registerKind,                       // ventanas nativas de otros módulos
    isCentered: isCentered,                           // ¿chat al centro con ventanas en los flancos?
    palette: function (q) { palOpen(q || ''); },      // paleta ⌘K (empresas, pantallas, agentes, acciones)
    screens: function () {                            // registro único de pantallas (solo lectura)
      return screens().map(function (s) { return { id: s.id, group: s.g, icon: s.ic, es: s.es, en: s.en }; });
    },
    openScreen: _runScreen,
    classicView: toClassicView,
    refreshBalance: _balRefresh,
    revealChat: _revealChat,                          // "solo chat": las ventanas que tapan la conversación → barra de tareas
  };
  // módulos que cargaron ANTES que la Cabina pueden dejar sus ventanas en una cola:
  // window.__kosKindQueue = [[kind, spec], …]
  try {
    (Array.isArray(window.__kosKindQueue) ? window.__kosKindQueue : []).forEach(function (x) { if (x) registerKind(x[0], x[1]); });
    window.__kosKindQueue = { push: function (x) { if (x) registerKind(x[0], x[1]); return 0; } };
  } catch (e) {}
  // tokens del tema (también .kos-themed) disponibles desde el arranque, aunque la Cabina aún no se abra
  try { if (document.head) ensureStyles(); else document.addEventListener('DOMContentLoaded', ensureStyles); } catch (e) {}
})();
