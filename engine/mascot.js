/* ============================================================================
   engine/mascot.js — MASCOTAS BURBUJA de Khipus OS (2026-10-06)

   Pedido de Fabrizio (video "Khipus OS"): Khipu y sus agentes son burbujas con
   degradado y dos ojitos. Colores tomados del video cuadro a cuadro:
     Khipu   rosa → violeta → naranja → magenta   (te responde)
     Analista azul                                (fundamentales)
     Radar    rojo coral                          (noticias, eventos y geopolítica)
     Cadena   turquesa → verde                    (cadena de suministro)
     Técnico  ámbar                               (precio y momento)
     Comité   violeta → rosa                      (decisiones)

   API (sin dependencias, SVG puro, se puede usar en cualquier módulo):
     KhipuMascot.svg(id, size?, {state:'idle'|'think'|'talk', title?})  → HTML
     KhipuMascot.agents()           → [{id, es, en, role_es, role_en, colors, seats}]
     KhipuMascot.of(seatOrId)       → agente al que pertenece un puesto del comité
                                      (fundamental, technical, news, supply_chain,
                                       geopolitical, macro, committee…)
     KhipuMascot.stack(ids, size)   → burbujas superpuestas (encabezado del chat)
   Sin animación si el sistema pide "reducir movimiento".
   ============================================================================ */
(function () {
  'use strict';

  // c: [luz arriba-izq, arriba-der, abajo-izq, abajo-der] — degradado de 4 esquinas como en el video
  var AGENTS = [
    { id: 'khipu', es: 'Khipu', en: 'Khipu', role_es: 'Te responde', role_en: 'Answers you',
      c: ['#f07fa0', '#7a4ce8', '#ff8746', '#c23a8c'], seats: ['khipu', 'brain'] },
    { id: 'analista', es: 'Analista', en: 'Analyst', role_es: 'Fundamentales', role_en: 'Fundamentals',
      c: ['#7d8be6', '#5b81e4', '#4054cf', '#6b9ff4'], seats: ['fundamental', 'fundamentals', 'macro', 'valuation', 'quant'] },
    { id: 'radar', es: 'Radar', en: 'Radar', role_es: 'Noticias y eventos', role_en: 'News & events',
      c: ['#f78189', '#f26570', '#e63e52', '#f6808a'], seats: ['news', 'sentiment', 'geopolitical', 'geo', 'events'] },
    { id: 'cadena', es: 'Cadena', en: 'Chain', role_es: 'Cadena de suministro', role_en: 'Supply chain',
      c: ['#4cb1ab', '#56b87c', '#1b9386', '#83cd70'], seats: ['supply_chain', 'chain', 'supply'] },
    { id: 'tecnico', es: 'Técnico', en: 'Technical', role_es: 'Precio y momento', role_en: 'Price & momentum',
      c: ['#f7cc63', '#f2bc3a', '#e6a117', '#f5c54a'], seats: ['technical', 'momentum', 'risk'] },
    { id: 'comite', es: 'Comité', en: 'Committee', role_es: 'Decisiones', role_en: 'Decisions',
      c: ['#bc78e5', '#9f60e5', '#7a3fe0', '#d88ae6'], seats: ['committee', 'chair', 'portfolio', 'president'] },
  ];
  var BY = {}; AGENTS.forEach(function (a) { BY[a.id] = a; a.seats.forEach(function (s) { BY[s] = a; }); });

  function lang() { var l = window.LANG; if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) {} } return l === 'en' ? 'en' : 'es'; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function of(x) { return BY[String(x || '').toLowerCase()] || null; }

  var CSS = '' +
    '.km{display:inline-block;flex-shrink:0;line-height:0;vertical-align:middle}' +
    '.km svg{display:block;overflow:visible}' +
    '.km .km-eye{transform-box:fill-box;transform-origin:center;animation:km-blink 5.2s infinite}' +
    '.km.km-think .km-body{animation:km-bob 1.1s ease-in-out infinite;transform-box:fill-box;transform-origin:center}' +
    '.km.km-talk .km-body{animation:km-pulse .9s ease-in-out infinite;transform-box:fill-box;transform-origin:center}' +
    '.km.km-think .km-eye{animation:km-look 1.6s ease-in-out infinite}' +
    '@keyframes km-blink{0%,92%,100%{transform:scaleY(1)}95%{transform:scaleY(.12)}}' +
    '@keyframes km-bob{0%,100%{transform:translateY(0) scale(1)}50%{transform:translateY(-6%) scale(1.03,.97)}}' +
    '@keyframes km-pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.05)}}' +
    '@keyframes km-look{0%,100%{transform:translateX(0)}50%{transform:translateX(12%)}}' +
    '.km-stack{display:inline-flex;align-items:center}.km-stack .km{margin-left:-28%;border-radius:50%;box-shadow:0 0 0 2px var(--km-ring,#fff)}' +
    '.km-stack .km:first-child{margin-left:0}' +
    '@media (prefers-reduced-motion:reduce){.km .km-eye,.km.km-think .km-body,.km.km-talk .km-body,.km.km-think .km-eye{animation:none}}';
  function ensureCss() {
    if (document.getElementById('km-css')) return;
    var st = document.createElement('style'); st.id = 'km-css'; st.textContent = CSS;
    (document.head || document.documentElement).appendChild(st);
  }

  var _uid = 0;
  // Forma: burbuja algo irregular (no un círculo perfecto), luz arriba a la izquierda, sombra suave debajo.
  function svg(id, size, opts) {
    opts = opts || {};
    var a = of(id) || AGENTS[0], c = a.c, s = size || 32, u = 'km' + (++_uid);
    var face = s >= 18;                         // con menos de 18 px los ojos no se distinguen
    var st = opts.state === 'think' ? ' km-think' : opts.state === 'talk' ? ' km-talk' : '';
    var title = opts.title != null ? opts.title : (lang() === 'en' ? a.en : a.es);
    return '<span class="km' + st + '" style="width:' + s + 'px;height:' + s + 'px" role="img" aria-label="' + esc(title) + '">' +
      '<svg viewBox="0 0 100 100" width="' + s + '" height="' + s + '" aria-hidden="true" focusable="false">' +
      '<defs>' +
        '<linearGradient id="' + u + 'a" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="' + c[0] + '"/><stop offset="1" stop-color="' + c[3] + '"/></linearGradient>' +
        '<linearGradient id="' + u + 'b" x1="1" y1="0" x2="0" y2="1"><stop offset="0" stop-color="' + c[1] + '"/><stop offset=".55" stop-color="' + c[1] + '" stop-opacity="0"/></linearGradient>' +
        '<radialGradient id="' + u + 'c" cx=".28" cy=".85" r=".6"><stop offset="0" stop-color="' + c[2] + '"/><stop offset="1" stop-color="' + c[2] + '" stop-opacity="0"/></radialGradient>' +
        '<radialGradient id="' + u + 'h" cx=".32" cy=".26" r=".42"><stop offset="0" stop-color="#fff" stop-opacity=".45"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>' +
        '<radialGradient id="' + u + 's" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="' + c[3] + '" stop-opacity=".35"/><stop offset="1" stop-color="' + c[3] + '" stop-opacity="0"/></radialGradient>' +
      '</defs>' +
      (s >= 40 ? '<ellipse cx="50" cy="99" rx="30" ry="6" fill="url(#' + u + 's)"/>' : '') +
      '<g class="km-body">' +
        '<path d="M50 4C76 4 96 20 96 49C96 77 77 96 49 96C22 96 4 78 4 51C4 22 24 4 50 4Z" fill="url(#' + u + 'a)"/>' +
        '<path d="M50 4C76 4 96 20 96 49C96 77 77 96 49 96C22 96 4 78 4 51C4 22 24 4 50 4Z" fill="url(#' + u + 'b)"/>' +
        '<path d="M50 4C76 4 96 20 96 49C96 77 77 96 49 96C22 96 4 78 4 51C4 22 24 4 50 4Z" fill="url(#' + u + 'c)"/>' +
        '<path d="M50 4C76 4 96 20 96 49C96 77 77 96 49 96C22 96 4 78 4 51C4 22 24 4 50 4Z" fill="url(#' + u + 'h)"/>' +
        (face ? '<g class="km-eye"><rect x="36" y="36" width="7.5" height="17" rx="3.75" fill="#fff"/><rect x="56.5" y="36" width="7.5" height="17" rx="3.75" fill="#fff"/></g>' : '') +
      '</g></svg></span>';
  }

  function stack(ids, size) {
    return '<span class="km-stack">' + (ids || AGENTS.slice(1).map(function (a) { return a.id; })).map(function (id) { return svg(id, size || 22); }).join('') + '</span>';
  }

  function agents() {
    return AGENTS.map(function (a) { return { id: a.id, es: a.es, en: a.en, role_es: a.role_es, role_en: a.role_en, colors: a.c.slice(), seats: a.seats.slice() }; });
  }
  function name(id) { var a = of(id); return a ? (lang() === 'en' ? a.en : a.es) : String(id || ''); }
  function color(id) { var a = of(id); return a ? a.c[2] : '#8a8577'; }

  ensureCss();
  window.KhipuMascot = { svg: svg, stack: stack, agents: agents, of: function (x) { var a = of(x); return a ? a.id : null; }, name: name, color: color };
})();
