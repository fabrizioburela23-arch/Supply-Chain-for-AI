/* ============================================================================
   engine/loading.js — Sistema de animaciones de carga por NIVEL DE ESPERA.
   Pedido de Fabrizio (2026-07-14): "que todo lo que tarde tenga una animación
   de carga adecuada; hay tipos de animación según cuánto se espera que tarde".

   Regla de UX:
     · Corto  (0.3–1s)  → spinner()  : rueda pequeña.
     · Medio  (1–5s)    → skeleton()  : placeholder con brillo (forma del contenido).
     · Largo  (5s+, IA) → staged()    : progreso por PASOS con mensajes que avanzan
                                        (nunca un vacío; se siente que algo pasa).

   API (window.KhipuLoading):
     spinner({size,label})            → string HTML
     dots(text)                       → string HTML (texto + puntos animados)
     skeleton({lines,chart,height})   → string HTML
     staged(mountElOrId, {title,steps,accent,cycle}) → {stop()}
   Bilingüe: los textos los pasa quien llama; este módulo no fija idioma.

   KHIPUS OS (2026-10-10): sin tintas oscuras fijas — los cargadores se leen bien EN CUALQUIER
   lugar. Cada color es var(--os-* , var(--<token de app.html>, respaldo-oscuro)):
     · dentro de Khipus OS (#bcp-ov) o de un overlay .kos-themed → tokens --os-* (claro = body sin
       .dark, oscuro = body.dark), los mismos que engine/cockpit.js;
     · en la vista clásica (fuera de ambos) → los tokens del tema de app.html (--ink-2, --line-2,
       --accent…), que también cambian con claro/oscuro;
     · sin ninguno (página suelta) → el respaldo oscuro de siempre.
   El orbe es decorativo: su brillo usa `accent` si quien llama lo pasa (hex), si no el acento.
   ============================================================================ */
(function () {
  'use strict';

  // tokens (var() anidados: Khipus OS → tema de app.html → respaldo oscuro)
  var T = {
    ink:   'var(--os-ink,var(--ink,#F2F2F5))',
    ink2:  'var(--os-ink-2,var(--ink-2,#A6A8B5))',
    track: 'var(--os-surface-3,var(--line-2,#2A2B36))',
    line:  'var(--os-line,var(--line,rgba(255,255,255,.07)))',
    acc:   'var(--os-accent,var(--accent,#4C8DF6))',
    ai:    'var(--os-ai,var(--accent,#B48CFF))',
    good:  'var(--os-good-ink,currentColor)',
    font:  "var(--os-font,'Nunito','Geist',system-ui,-apple-system,'Segoe UI',sans-serif)",
  };

  function ensureCSS() {
    if (document.getElementById('khl-css')) return;
    var st = document.createElement('style');
    st.id = 'khl-css';
    st.textContent = [
      '@keyframes khl-spin{to{transform:rotate(360deg)}}',
      '@keyframes khl-shimmer{0%{background-position:-420px 0}100%{background-position:420px 0}}',
      '@keyframes khl-indet{0%{left:-40%;width:40%}50%{width:55%}100%{left:100%;width:35%}}',
      '@keyframes khl-pulse{0%,100%{transform:scale(.85);opacity:.7}50%{transform:scale(1.12);opacity:1}}',
      '@keyframes khl-dots{0%,20%{opacity:0}50%{opacity:1}100%{opacity:0}}',
      '@keyframes khl-rise{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}',
      '.khl-spin{display:inline-block;border-radius:50%;border:2.5px solid ' + T.track + ';' +
        'border-top-color:' + T.acc + ';animation:khl-spin .7s linear infinite;vertical-align:middle}',
      '.khl-inl{display:inline-flex;align-items:center;gap:9px;color:' + T.ink2 + ';font-size:13px}',
      '.khl-dots{color:' + T.ink2 + ';font-size:13px}',
      '.khl-dot{animation:khl-dots 1.2s infinite}.khl-dot:nth-child(2){animation-delay:.2s}.khl-dot:nth-child(3){animation-delay:.4s}',
      // esqueleto: la línea del tema de base + una franja de la superficie más marcada (se ve en claro y en oscuro)
      '.khl-sk{background:linear-gradient(90deg,' + T.line + ' 25%,' + T.track + ' 37%,' + T.line + ' 63%);' +
        'background-size:840px 100%;animation:khl-shimmer 1.4s ease infinite;border-radius:8px}',
      '.khl-staged{max-width:440px;margin:8px auto;padding:26px 22px;text-align:left;font-family:' + T.font + '}',
      '.khl-orb{width:54px;height:54px;margin:0 auto 16px;border-radius:50%;' +
        'background:radial-gradient(circle at 35% 30%,' + T.acc + ',' + T.ai + ' 70%);' +
        'box-shadow:0 0 26px var(--kos-accent-soft,rgba(76,141,246,.16));animation:khl-pulse 1.5s ease-in-out infinite}',
      '.khl-bar{position:relative;height:3px;border-radius:3px;background:' + T.track + ';overflow:hidden;margin:0 0 18px}',
      '.khl-bar i{position:absolute;top:0;height:100%;border-radius:3px;' +
        'background:linear-gradient(90deg,' + T.ai + ',' + T.acc + ');animation:khl-indet 1.6s ease-in-out infinite}',
      // pasos: pendientes y hechos en tinta secundaria (≥ 4.5:1); el actual en la tinta principal
      '.khl-step{display:flex;align-items:center;gap:11px;padding:7px 0;font-size:13px;color:' + T.ink2 + ';transition:color .3s}',
      '.khl-step .ic{width:18px;height:18px;flex:0 0 18px;display:flex;align-items:center;justify-content:center;font-size:12px}',
      '.khl-step.done{color:' + T.ink2 + '}.khl-step.done .ic{color:' + T.good + '}',
      '.khl-step.now{color:' + T.ink + ';font-weight:600;animation:khl-rise .3s ease}',
      '.khl-title{text-align:center;font-size:14px;font-weight:700;color:' + T.ink + ';margin-bottom:2px}',
      '.khl-sub{text-align:center;font-size:11.5px;color:' + T.ink2 + ';margin-bottom:18px;min-height:15px}',
      '@media(prefers-reduced-motion:reduce){.khl-sk,.khl-orb,.khl-step.now{animation:none}.khl-spin{animation-duration:2s}.khl-bar i{animation-duration:3.2s}}',
    ].join('\n');
    document.head.appendChild(st);
  }

  function esc(s) { return String(s == null ? '' : s).replace(/[<>&]/g, function (c) { return { '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c]; }); }

  // ── CORTO: spinner + puntos ──
  function spinner(o) {
    o = o || {};
    var sz = o.size || 18;
    ensureCSS();
    return '<span class="khl-inl">' +
      '<span class="khl-spin" style="width:' + sz + 'px;height:' + sz + 'px"></span>' +
      (o.label ? '<span>' + esc(o.label) + '</span>' : '') + '</span>';
  }
  function dots(text) {
    ensureCSS();
    return '<span class="khl-dots">' + esc(text || '') +
      '<span class="khl-dot">.</span><span class="khl-dot">.</span><span class="khl-dot">.</span></span>';
  }

  // ── MEDIO: skeleton (forma del contenido, con brillo) ──
  function skeleton(o) {
    o = o || {};
    ensureCSS();
    if (o.chart) {
      return '<div class="khl-sk" style="width:100%;height:' + (o.height || 240) + 'px"></div>';
    }
    var n = o.lines || 4, h = '';
    for (var i = 0; i < n; i++) {
      var w = 60 + Math.round((Math.sin(i * 1.7) * 0.5 + 0.5) * 35); // 60–95%
      h += '<div class="khl-sk" style="height:12px;margin:9px 0;width:' + w + '%"></div>';
    }
    return '<div style="padding:6px 2px">' + h + '</div>';
  }

  // ── LARGO: progreso por pasos (IA) ──
  // steps: [str,…]. Avanza uno cada ~cycle ms; se queda "en curso" en el último
  // hasta que quien llama reemplace el contenido (o llame stop()). Auto-limpia
  // el intervalo si su nodo se desmonta.
  function staged(mount, o) {
    o = o || {};
    ensureCSS();
    var el = (typeof mount === 'string') ? document.getElementById(mount) : mount;
    if (!el) return { stop: function () {} };
    var steps = (o.steps && o.steps.length) ? o.steps.slice() : ['Procesando…'];
    var cycle = o.cycle || 2600;
    // brillo del orbe (decorativo): hex de quien llama (+66 = 40 % de opacidad); sin él, el del CSS
    var glow = /^#[0-9a-f]{6}$/i.test(String(o.accent || '')) ? ' style="box-shadow:0 0 26px ' + o.accent + '66"' : '';
    el.innerHTML =
      '<div class="khl-staged">' +
        '<div class="khl-orb"' + glow + '></div>' +
        (o.title ? '<div class="khl-title">' + esc(o.title) + '</div>' : '') +
        '<div class="khl-sub" id="khl-sub"></div>' +
        '<div class="khl-bar"><i></i></div>' +
        '<div id="khl-steps">' +
          steps.map(function (t, i) {
            return '<div class="khl-step" data-i="' + i + '"><span class="ic">○</span><span>' + esc(t) + '</span></div>';
          }).join('') +
        '</div></div>';
    var cur = -1;
    function advance() {
      if (!el.isConnected) { clearInterval(iv); return; }   // desmontado → parar
      cur++;
      var stepEls = el.querySelectorAll('.khl-step');
      if (cur >= stepEls.length) { cur = stepEls.length - 1; return; }   // se queda en el último
      for (var i = 0; i < stepEls.length; i++) {
        stepEls[i].classList.remove('now', 'done');
        var ic = stepEls[i].querySelector('.ic');
        if (i < cur) { stepEls[i].classList.add('done'); ic.textContent = '✓'; }
        else if (i === cur) { stepEls[i].classList.add('now'); ic.innerHTML = '<span class="khl-spin" style="width:12px;height:12px;border-width:2px"></span>'; }
        else { ic.textContent = '○'; }
      }
      var sub = el.querySelector('#khl-sub');
      if (sub) sub.textContent = steps[cur] || '';
    }
    advance();
    var iv = setInterval(advance, cycle);
    return { stop: function () { clearInterval(iv); } };
  }

  window.KhipuLoading = { spinner: spinner, dots: dots, skeleton: skeleton, staged: staged, _ensureCSS: ensureCSS };
})();
