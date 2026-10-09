/* ============================================================================
   engine/pfcommittee.js — 💼 COMITÉ DE CARTERA (pestaña "Mi cartera" del Comité)

   Pedido (2026-10-02): "que el comité pueda analizar carteras, no solo empresas,
   y que te dé acciones concretas (quitar una posición, reducir riesgo, adquirir
   otra), a modo de consejo y advirtiendo que es una IA… que una persona sin
   experiencia pueda tener carteras de acuerdo a sus expectativas".

   · Fuente: tus posiciones de Mercado (MKT.pos), cualquier cartera simulada
     (window.KhipuPortfolios) o tu cuenta del bróker (🔒 PIN, /api/trade/positions/detail).
   · Perfil del inversionista (3 preguntas + nivel de involucramiento), guardado
     en localStorage 'kh_investor_profile' (window.KhipuProfile.get()).
   · POST /api/committee/portfolio → salud vs perfil, KPIs, gráficos (pesos,
     riesgo vs dinero, sectores) y ACCIONES con botón para aplicarlas en una
     cartera simulada (las cuentas reales pasan por el bróker con confirmación).
   window.KhipuPortfolioCommittee.render(el)

   Piel Khipus OS (2026-10-09, "el comité todavía no está actualizado"): SOLO tokens
   --os-* (claro/oscuro los pone el overlay #cm-ov o la Cabina) con el valor OSCURO de
   respaldo en var(--x, respaldo); TEXTO verde/rojo/ámbar = var(--cm-good/--cm-bad/--cm-warn) (en claro llegan a
   4.5:1 sobre su píldora teñida; los define el overlay del comité). Tarjetas, píldoras,
   controles segmentados y mascotas de agentes (engine/mascot.js). Clases propias
   'pfo-*' (CSS inyectado al pintar, id 'pfo-css'); los ids pfc-* no cambian.
   ============================================================================ */
(function () {
  'use strict';
  function isEn() { var l = window.LANG; if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = null; } } return l === 'en'; }
  function L(es, en) { return isEn() ? en : es; }

  // ── colores = tokens de Khipus OS (nunca hex sueltos: un test lo verifica) ──
  var INK = 'var(--os-ink,#F2F2F5)', INK2 = 'var(--os-ink-2,#A6A8B5)', INK3 = 'var(--os-ink-3,#6E7080)',
    ACC = 'var(--os-accent,#4C8DF6)', NEG = 'var(--os-neg,#F07A52)',
    GOOD = 'var(--cm-good,#2fbf5b)', BAD = 'var(--cm-bad,#F47C7C)', WARN = 'var(--cm-warn,#B7791F)', AI = 'var(--cm-ai,#B48CFF)';
  // reglas con doble alcance: dentro del comité (#cm, gana a sus estilos generales) y suelto
  function scoped(rules) {
    return rules.map(function (r) {
      return r[0].split(',').map(function (s) { s = s.trim(); return '#cm .pfo ' + s + ',.pfo ' + s; }).join(',') + '{' + r[1] + '}';
    }).join('');
  }
  var CSS = '.pfo{font-family:var(--os-font,\'Nunito\',\'Geist\',system-ui,-apple-system,\'Segoe UI\',sans-serif);color:var(--os-ink,#F2F2F5);font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}' +
    scoped([
      ['.pfo-q', 'margin:16px 0 8px;font-size:13.5px;font-weight:700;color:var(--os-ink,#F2F2F5);line-height:1.35'],
      ['.pfo-seg', 'display:inline-flex;flex-wrap:wrap;gap:2px;padding:3px;border-radius:20px;background:var(--os-surface-2,#1F2029);max-width:100%'],
      ['.pfo-seg button', 'appearance:none;-webkit-appearance:none;border:0;background:none;cursor:pointer;min-height:32px;padding:6px 14px;border-radius:999px;' +
        'font:inherit;font-size:13px;font-weight:600;line-height:1.25;color:var(--os-ink-2,#A6A8B5);text-align:center;transition:background-color .15s ease,color .15s ease,box-shadow .15s ease'],
      ['.pfo-seg button:hover', 'color:var(--os-ink,#F2F2F5)'],
      ['.pfo-seg button.on', 'background:var(--os-surface,#17181F);color:var(--os-ink,#F2F2F5);box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4), 0 10px 30px rgba(0,0,0,.35))'],
      ['.pfo-seg button:focus-visible,.pfo-row:focus-visible,.pfo-qx:focus-visible', 'outline:2px solid var(--os-accent,#4C8DF6);outline-offset:2px'],
      ['.pfo-nav', 'margin:0 0 16px;background:var(--os-surface-3,#2A2B36)'],
      ['.pfo-hint', 'font-size:12px;color:var(--os-ink-3,#6E7080);margin-top:6px;line-height:1.45'],
      ['.pfo-actions', 'display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:18px'],
      ['.cm-btn.pfo-sm', 'height:auto;min-height:30px;padding:5px 13px;font-size:12px;line-height:1.2'],
      ['.pfo-prof', 'display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:0 0 14px'],
      ['.pfo-chip', 'display:inline-flex;align-items:center;gap:6px;padding:6px 14px;border-radius:999px;background:var(--os-surface,#17181F);' +
        'box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4), 0 10px 30px rgba(0,0,0,.35));' +
        'color:var(--os-ink-2,#A6A8B5);font-size:13px;font-weight:600;white-space:nowrap;max-width:100%;overflow:hidden;text-overflow:ellipsis'],
      ['.pfo-chip b', 'color:var(--os-ink,#F2F2F5)'],
      ['.pfo-tag', 'display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:999px;font-size:11.5px;font-weight:700;white-space:nowrap;' +
        'color:var(--c,var(--os-ink-2,#A6A8B5));background:var(--os-surface-2,#1F2029);background:color-mix(in srgb,var(--c,var(--os-ink-2,#A6A8B5)) 13%,transparent)'],
      ['.pfo-tag.neu', 'color:var(--os-ink-2,#A6A8B5);background:var(--os-surface-2,#1F2029)'],
      ['.pfo-tags', 'display:flex;gap:6px;flex-wrap:wrap;align-items:center'],
      ['.pfo-hero', 'display:flex;gap:16px;align-items:center;flex-wrap:wrap'],
      ['.pfo-ring', 'position:relative;width:78px;height:78px;flex:none'],
      ['.pfo-ring svg', 'display:block;width:100%;height:100%;transform:rotate(-90deg)'],
      ['.pfo-ring circle', 'fill:none;stroke-width:7'],
      ['.pfo-ring .t', 'stroke:var(--os-surface-3,#2A2B36)'],
      ['.pfo-ring .v', 'stroke:var(--c,var(--os-accent,#4C8DF6));stroke-linecap:round'],
      ['.pfo-ring b', 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:23px;font-weight:800;color:var(--c,var(--os-ink,#F2F2F5));letter-spacing:-.02em'],
      ['.pfo-verdict', 'font-size:17px;font-weight:800;color:var(--os-ink,#F2F2F5);letter-spacing:-.01em;line-height:1.3'],
      ['.pfo-kpis', 'display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin-top:16px'],
      ['.pfo-kpi', 'background:var(--os-surface-2,#1F2029);border-radius:var(--os-r-sm,12px);padding:10px 12px;min-width:0'],
      ['.pfo-kpi .k', 'font-size:11.5px;color:var(--os-ink-2,#A6A8B5);line-height:1.3'],
      ['.pfo-kpi .v', 'font-size:18px;font-weight:800;color:var(--c,var(--os-ink,#F2F2F5));margin-top:4px;letter-spacing:-.01em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'],
      ['.pfo-kpi .s', 'font-size:11.5px;color:var(--os-ink-3,#6E7080);margin-top:2px;line-height:1.3'],
      ['.pfo-act', 'background:var(--os-surface-2,#1F2029);border-radius:14px;padding:12px 14px;margin-bottom:8px'],
      ['.pfo-act-hd', 'display:flex;gap:8px;align-items:center;flex-wrap:wrap'],
      ['.pfo-act-ic', 'width:30px;height:30px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:14px;flex:none;' +
        'background:var(--os-surface-3,#2A2B36);background:color-mix(in srgb,var(--c,var(--os-ink-2,#A6A8B5)) 16%,transparent)'],
      ['.pfo-act-tt', 'font-size:13.5px;font-weight:700;color:var(--os-ink,#F2F2F5);min-width:0;overflow-wrap:anywhere'],
      ['.pfo-act-tt em', 'font-style:normal;color:var(--c,var(--os-ink,#F2F2F5))'],
      ['.pfo-act-btns', 'margin-left:auto;display:flex;gap:6px;flex-wrap:wrap'],
      ['.pfo-act-why', 'font-size:12.5px;color:var(--os-ink-2,#A6A8B5);margin-top:8px;line-height:1.55;overflow-wrap:anywhere'],
      ['.pfo-bar', 'display:grid;grid-template-columns:minmax(0,120px) minmax(0,1fr) 64px;gap:10px;align-items:center;font-size:12.5px;margin:7px 0'],
      ['.pfo-bar .n', 'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--os-ink,#F2F2F5)'],
      ['.pfo-bar .tr', 'position:relative;height:8px;border-radius:999px;background:var(--os-surface-3,#2A2B36)'],
      ['.pfo-bar .tr i', 'position:absolute;left:0;top:0;bottom:0;border-radius:999px;background:var(--c,var(--os-accent,#4C8DF6))'],
      ['.pfo-bar .tr b', 'position:absolute;top:-4px;bottom:-4px;width:2px;border-radius:2px;background:var(--cm-warn-fill,#F2C46D)'],
      ['.pfo-bar .v', 'text-align:right;color:var(--os-ink,#F2F2F5);font-weight:600'],
      ['.pfo-sub', 'font-size:12px;font-weight:700;color:var(--os-ink-2,#A6A8B5);margin-top:12px'],
      ['.pfo-legend', 'text-transform:none;letter-spacing:0;font-weight:500;color:var(--os-ink-3,#6E7080)'],
      ['.pfo-row', 'display:flex;gap:10px;align-items:baseline;padding:8px 10px;border-radius:12px;margin-top:2px;cursor:pointer;transition:background-color .15s ease'],
      ['.pfo-row:hover', 'background:var(--os-surface-2,#1F2029)'],
      ['.pfo-row.on', 'background:var(--kos-accent-soft,rgba(76,141,246,.16))'],
      ['.pfo-row .w', 'font-size:11.5px;color:var(--os-ink-3,#6E7080);min-width:96px'],
      ['.pfo-row .t', 'flex:1;min-width:0;font-size:13px;color:var(--os-ink,#F2F2F5)'],
      ['.pfo-row .s', 'font-size:12px;color:var(--os-ink-2,#A6A8B5)'],
      ['.pfo-busy', 'display:flex;gap:12px;align-items:center;font-size:13px;color:var(--os-ink-2,#A6A8B5);line-height:1.5'],
      ['.pfo-say', 'font-size:13.5px;color:var(--os-ink,#F2F2F5);line-height:1.65;overflow-wrap:anywhere'],
      ['.pfo-hd', 'display:flex;align-items:center;gap:6px;flex-wrap:wrap'],
      ['.pfo-qx', 'display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;margin-left:5px;border-radius:50%;vertical-align:2px;' +
        'border:1px solid var(--os-line,rgba(255,255,255,.07));background:var(--os-surface,#17181F);color:var(--os-ink-3,#6E7080);font-size:10px;font-weight:700;line-height:1;cursor:pointer;letter-spacing:0'],
      ['.pfo-qx:hover,.pfo-qx:focus-visible', 'color:var(--os-accent,#4C8DF6);border-color:var(--os-accent,#4C8DF6)'],
      ['a.pfo-link', 'color:var(--os-accent,#4C8DF6);text-decoration:none;font-weight:600'],
      ['a.pfo-link:hover', 'text-decoration:underline'],
    ]) +
    '@media (max-width:560px){.pfo .pfo-bar{grid-template-columns:minmax(0,88px) minmax(0,1fr) 56px;gap:8px}.pfo .pfo-act-btns{margin-left:0;width:100%}.pfo .pfo-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}}' +
    '@media (prefers-reduced-motion:reduce){.pfo .pfo-seg button,.pfo .pfo-row{transition:none}}';
  function ensureCss() {
    if (typeof document === 'undefined' || typeof document.createElement !== 'function' || document.getElementById('pfo-css')) return;
    var st = document.createElement('style'); st.id = 'pfo-css'; st.textContent = CSS;
    (document.head || document.documentElement).appendChild(st);
  }
  // mascota de un agente (engine/mascot.js): Comité, Analista, Radar, Cadena, Técnico; sin el módulo, nada
  function masc(id, size, state) {
    try { return window.KhipuMascot ? window.KhipuMascot.svg(id, size || 20, state ? { state: state } : null) : ''; } catch (e) { return ''; }
  }
  function mstack(ids, size) {
    try { return window.KhipuMascot && window.KhipuMascot.stack ? window.KhipuMascot.stack(ids, size || 18) : ''; } catch (e) { return ''; }
  }
  // control segmentado (como .osw-seg de Khipus OS): opts = [[valor, texto, ayuda?]]
  function seg(key, opts, cur, lblId) {
    return '<div class="pfo-seg" role="radiogroup"' + (lblId ? ' aria-labelledby="' + lblId + '"' : '') + '>' + opts.map(function (o) {
      var on = cur === o[0];
      return '<button type="button" role="radio" aria-checked="' + on + '"' + (on ? ' class="on"' : '') + ' data-q="' + key + '" data-v="' + o[0] + '"' +
        (o[2] ? ' title="' + esc(o[2]) + '"' : '') + '>' + esc(o[1]) + '</button>';
    }).join('') + '</div>';
  }
  // color también en línea: dentro de .cm-kv el comité fija el color del último span
  function tag(text, color) { return '<span class="pfo-tag' + (color ? '' : ' neu') + '"' + (color ? ' style="--c:' + color + ';color:' + color + '"' : '') + '>' + text + '</span>'; }
  // "?" que explica la métrica en lenguaje simple (engine/explain.js), con el aspecto de .osw-q
  function qx(key) {
    if (!window.explainMetric) return '';
    var tip = L('¿Qué es esto?', 'What is this?');
    return '<span class="pfo-qx" role="button" tabindex="0" title="' + esc(tip) + '" aria-label="' + esc(tip) + '" ' +
      'onclick="event.stopPropagation();window.explainMetric(\'' + key + '\')" onkeydown="if(event.key===\'Enter\'||event.key===\' \'){event.preventDefault();window.explainMetric(\'' + key + '\')}">?</span>';
  }
  function kpi(label, value, sub, color, title) {
    return '<div class="pfo-kpi"' + (title ? ' title="' + esc(title) + '"' : '') + '><div class="k">' + esc(label) + '</div>' +
      '<div class="v"' + (color ? ' style="--c:' + color + '"' : '') + '>' + value + '</div>' + (sub ? '<div class="s">' + esc(sub) + '</div>' : '') + '</div>';
  }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function usd(v) { v = Number(v); if (!isFinite(v)) return '—'; return (v < 0 ? '−$' : '$') + Math.abs(v).toLocaleString('en-US', { maximumFractionDigits: 0 }); }
  function pct(v, d) { v = Number(v); return isFinite(v) ? v.toFixed(d == null ? 1 : d) + '%' : '—'; }
  function owner() {   // misma llave del navegador que engine/sync.js y engine/pfreports.js
    var k = null; try { k = localStorage.getItem('kh_owner_key'); } catch (e) {}
    if (!k || k.length < 16) {
      var a = new Uint8Array(16); if (window.crypto && window.crypto.getRandomValues) window.crypto.getRandomValues(a); else for (var i = 0; i < 16; i++) a[i] = Math.random() * 256;
      k = Array.prototype.map.call(a, function (b) { return ('0' + b.toString(16)).slice(-2); }).join('');
      try { localStorage.setItem('kh_owner_key', k); } catch (e) {}
    }
    return k;
  }
  function actor() { var a = null; try { a = localStorage.getItem('khipu_actor'); } catch (e) {} return (a && a.trim()) || 'usuario'; }

  // ── perfil del inversionista ──────────────────────────────────────────────
  var PKEY = 'kh_investor_profile';
  var QUESTIONS = [
    { k: 'drop', es: 'Si tu cartera cae 20 % en un mes, ¿qué haces?', en: 'If your portfolio falls 20% in a month, what do you do?',
      opts: [['sell', 'Vendo para no perder más', 'I sell to stop the loss', 0], ['wait', 'Espero, me pongo nervioso', 'I wait, nervously', 1], ['buy', 'Compro más: está barato', 'I buy more: it is cheap', 2]] },
    { k: 'horizon', es: '¿Cuándo vas a necesitar este dinero?', en: 'When will you need this money?',
      opts: [['short', 'En menos de 2 años', 'In under 2 years', 0], ['mid', 'En 2 a 5 años', 'In 2 to 5 years', 1], ['long', 'En más de 5 años', 'In more than 5 years', 2]] },
    { k: 'goal', es: '¿Qué buscas principalmente?', en: 'What are you mainly after?',
      opts: [['protect', 'Proteger lo que tengo', 'Protect what I have', 0], ['balance', 'Crecer con calma', 'Grow steadily', 1], ['grow', 'Crecer mucho aunque haya sustos', 'Grow a lot, even with scares', 2]] },
  ];
  var INVOLVE = [['autopilot', '🛋 Piloto automático', '🛋 Autopilot', 'Solo un resumen mensual y avisos graves.', 'Only a monthly summary and serious alerts.'],
    ['informed', '📬 Informado', '📬 Informed', 'Resumen semanal y alertas importantes.', 'Weekly summary and important alerts.'],
    ['active', '🎛 Activo', '🎛 Active', 'Reporte diario y todo el detalle.', 'Daily report and full detail.']];
  var RISK_LBL = { conservador: ['Conservador', 'Conservative'], moderado: ['Moderado', 'Moderate'], agresivo: ['Agresivo', 'Aggressive'] };
  function getProfile() { try { var p = JSON.parse(localStorage.getItem(PKEY) || 'null'); return p && p.risk ? p : null; } catch (e) { return null; } }
  function saveProfile(p) { try { localStorage.setItem(PKEY, JSON.stringify(p)); } catch (e) {} }
  window.KhipuProfile = { get: getProfile, save: saveProfile };

  var S = { el: null, src: null, editingProfile: false, answers: {}, busy: false, res: null, err: null, applied: {}, brokerPos: null, section: 'diag',
    past: null, viewingPast: null };
  var SECTIONS = [['diag', '🩺', 'Diagnóstico y consejos', 'Diagnosis & advice'], ['reports', '📄', 'Reportes', 'Reports'],
    ['news', '📰', 'Noticias', 'News'], ['ask', '💬', 'Pregúntale', 'Ask it']];

  // ── fuentes de posiciones ──────────────────────────────────────────────────
  function sources() {
    var out = [];
    var mp = (window.MKT && window.MKT.pos) || {}, ids = Object.keys(mp);
    if (ids.length) out.push({ key: 'market', label: L('Mis posiciones (Mercado)', 'My positions (Market)') + ' · ' + ids.length });
    var list = [];
    try { list = (window.KhipuPortfolios && window.KhipuPortfolios._list && window.KhipuPortfolios._list()) || []; } catch (e) {}
    // TODAS las carteras (2026-10-05): antes se ocultaban las vacías y parecía que no se habían guardado
    list.forEach(function (p) { var n = (p.positions || []).length; out.push({ key: 'pf:' + p.id, label: '🧪 ' + p.name + ' · ' + (n || L('vacía', 'empty')) }); });
    out.push({ key: 'broker', label: '🔒 ' + L('Mi cuenta del bróker (PIN)', 'My broker account (PIN)') });
    return out;
  }
  function nodeOf(id) { return (window.NODE_BY_ID || {})[id] || null; }
  function positionsFor(key) {
    if (key === 'market') {
      var mp = (window.MKT && window.MKT.pos) || {};
      return Promise.resolve({ positions: Object.keys(mp).map(function (id) {
        var p = mp[id], n = nodeOf(id);
        return { id: id, symbol: n && n.mkt, label: n ? n.label : id, shares: p.sh, cost_usd: p.sh * p.bp };
      }), cash: 0, start: null });
    }
    if (key && key.indexOf('pf:') === 0) {
      var id = key.slice(3), pf = null;
      try { (window.KhipuPortfolios._list() || []).forEach(function (p) { if (p.id === id) pf = p; }); } catch (e) {}
      if (!pf) return Promise.resolve({ positions: [] });
      return Promise.resolve({ positions: pf.positions.map(function (p) {
        var n = nodeOf(p.nodeId);
        return { id: p.nodeId, symbol: n && n.mkt, label: n ? n.label : p.nodeId, shares: p.shares, cost_usd: p.shares * p.avgPrice };
      }), cash: pf.cash, start: pf.startCash, pfId: pf.id, label: pf.name,
        startDate: pf.createdAt ? new Date(pf.createdAt).toISOString().slice(0, 10) : null });
    }
    if (key === 'broker') {
      var f = typeof window._tradeFetch === 'function' ? window._tradeFetch((window.BASE || '') + '/api/trade/positions/detail', {}, true) : fetch('/api/trade/positions/detail');
      return f.then(function (r) { return r.json(); }).then(function (rows) {
        if (!Array.isArray(rows)) throw new Error((rows && (isEn() ? rows.error_en || rows.error : rows.error)) || L('No pude leer la cuenta del bróker.', 'Could not read the broker account.'));
        return { positions: rows.map(function (p) { return { symbol: p.symbol, label: p.symbol, shares: parseFloat(p.qty), cost_usd: parseFloat(p.cost_basis) }; }), cash: 0, broker: true };
      });
    }
    return Promise.resolve({ positions: [] });
  }

  // ── pantallas ──────────────────────────────────────────────────────────────
  function card(inner, style) { return '<div class="cm-cell"' + (style ? ' style="' + style + '"' : '') + '>' + inner + '</div>'; }
  function profileHtml() {
    var p = getProfile();
    if (!p || S.editingProfile) {
      var invSel = INVOLVE.filter(function (x) { return x[0] === S.answers.involvement; })[0];
      return card('<div class="cm-t pfo-hd">' + masc('comite', 18) + '🧭 ' + esc(L('Tu perfil de inversionista (30 segundos)', 'Your investor profile (30 seconds)')) + '</div>' +
        '<div class="cm-note">' + esc(L('Con esto el comité sabe cuánto riesgo es "demasiado" para ti. Puedes cambiarlo cuando quieras.', 'This tells the committee how much risk is "too much" for you. You can change it anytime.')) + '</div>' +
        QUESTIONS.map(function (q) {
          return '<div class="pfo-q" id="pfo-q-' + q.k + '">' + esc(L(q.es, q.en)) + '</div>' +
            seg(q.k, q.opts.map(function (o) { return [o[0], L(o[1], o[2])]; }), S.answers[q.k], 'pfo-q-' + q.k);
        }).join('') +
        '<div class="pfo-q" id="pfo-q-involvement">' + esc(L('¿Cuánto quieres involucrarte?', 'How involved do you want to be?')) + '</div>' +
        seg('involvement', INVOLVE.map(function (o) { return [o[0], L(o[1], o[2]), L(o[3], o[4])]; }), S.answers.involvement, 'pfo-q-involvement') +
        (invSel ? '<div class="pfo-hint">' + esc(L(invSel[3], invSel[4])) + '</div>' : '') +
        '<div class="pfo-actions"><button class="cm-btn" id="pfc-save-prof">' + esc(L('Guardar perfil', 'Save profile')) + '</button>' +
        (p ? '<button class="cm-btn ghost" id="pfc-cancel-prof">' + esc(L('Cancelar', 'Cancel')) + '</button>' : '') + '</div>');
    }
    var inv = INVOLVE.filter(function (x) { return x[0] === p.involvement; })[0] || INVOLVE[1];
    return '<div class="pfo-prof"><span class="pfo-chip">🧭 ' + esc(L('Perfil', 'Profile')) + ': <b>' + esc(L(RISK_LBL[p.risk][0], RISK_LBL[p.risk][1])) + '</b> · ' + esc(L(inv[1], inv[2])) + '</span>' +
      '<button class="cm-btn ghost pfo-sm" id="pfc-edit-prof">✎ ' + esc(L('Cambiar', 'Change')) + '</button>' +
      (window.KhipuSync ? '<button class="cm-btn ghost pfo-sm" id="pfc-sync">📱 ' + esc(L('Otros dispositivos', 'Other devices')) + '</button>' : '') + '</div>' +
      (S.showSync && window.KhipuSync ? syncHtml() : '');
  }
  // 📱 sincronización entre dispositivos (engine/sync.js)
  function syncHtml() {
    return card('<div class="cm-t">📱 ' + esc(L('Usar tus carteras en otro dispositivo', 'Use your portfolios on another device')) + '</div>' +
      '<div class="cm-note" style="margin-bottom:10px">' + esc(L('Tus carteras simuladas, tu perfil y tus posiciones se guardan solos en el servidor. Para verlos en el teléfono (u otra PC), copia este código y pégalo allá en esta misma pantalla. Guárdalo en privado: quien lo tenga ve tus carteras.',
        'Your simulated portfolios, profile and positions are saved to the server automatically. To see them on your phone (or another PC), copy this code and paste it there on this same screen. Keep it private: whoever has it sees your portfolios.')) + '</div>' +
      '<div class="cm-form" style="margin-bottom:8px"><input id="pfc-sync-code" readonly value="' + esc(window.KhipuSync.code()) + '" style="font-family:ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.04em">' +
        '<button class="cm-btn ghost" id="pfc-sync-copy">📋 ' + esc(L('Copiar', 'Copy')) + '</button></div>' +
      '<div class="cm-form" style="margin:0"><input id="pfc-sync-in" placeholder="' + esc(L('Pega aquí el código de tu otro dispositivo', 'Paste the code from your other device')) + '">' +
        '<button class="cm-btn" id="pfc-sync-link">🔗 ' + esc(L('Vincular', 'Link')) + '</button></div>' +
      (S.syncMsg ? '<div class="cm-note" style="margin-top:8px;color:' + (S.syncMsg.bad ? WARN : GOOD) + '">' + esc(S.syncMsg.text) + '</div>' : ''));
  }

  function riskFromAnswers(a) {
    var sc = 0, n = 0;
    QUESTIONS.forEach(function (q) { var o = q.opts.filter(function (x) { return x[0] === a[q.k]; })[0]; if (o) { sc += o[3]; n++; } });
    if (n < 3) return null;
    if (a.drop === 'sell' || a.horizon === 'short') return 'conservador';
    return sc >= 5 ? 'agresivo' : sc >= 3 ? 'moderado' : 'conservador';
  }

  // barra horizontal (col = token de color); cap = tope del perfil (marca ámbar)
  function hbar(label, v, max, col, cap, right) {
    var w = max ? Math.max(0, Math.min(100, v / max * 100)) : 0, c = cap && max ? Math.min(100, cap / max * 100) : null;
    return '<div class="pfo-bar"><span class="n" title="' + esc(label) + '">' + esc(label) + '</span>' +
      '<span class="tr"' + (col ? ' style="--c:' + col + '"' : '') + '><i style="width:' + w + '%"></i>' +
      (c != null ? '<b title="' + esc(L('tope de tu perfil', 'your profile cap')) + '" style="left:' + c + '%"></b>' : '') + '</span>' +
      '<span class="v">' + (right || pct(v)) + '</span></div>';
  }
  var KIND = { sell: ['🔻', BAD, 'Vender', 'Sell'], reduce: ['➖', WARN, 'Reducir', 'Reduce'], consolidate: ['🔗', WARN, 'Consolidar', 'Consolidate'],
    add: ['➕', GOOD, 'Aumentar', 'Add'], buy_new: ['🆕', ACC, 'Añadir nueva', 'Add new'] };
  var PRIO = { 1: ['Prioritaria', 'Priority', BAD], 2: ['Recomendada', 'Recommended', WARN], 3: ['Opcional', 'Optional', INK3] };

  // Cobertura (2026-10-05, "no analizó todas mis posiciones"): cuántas se midieron, cuáles
  // no y por qué, y cuántas tienen opinión de los analistas — con botón para investigar las que faltan.
  function coverageHtml(r) {
    var cv = r.coverage; if (!cv) return '';
    var miss = (cv.not_researched || []), ex = r.excluded || [];
    var full = cv.analyzed >= cv.requested && !ex.length;
    var col = full ? GOOD : WARN;
    var rs = S.researching || {};
    return card('<div class="pfo-tags">' +
        tag('📊 ' + esc(L('Analizadas ', 'Analyzed ')) + cv.analyzed + esc(L(' de ', ' of ')) + cv.requested + esc(L(' posiciones', ' positions')), col) +
        tag(mstack(['analista', 'radar', 'cadena', 'tecnico'], 14) + ' ' + cv.researched + esc(L(' con opinión de los analistas', ' with analyst opinion')), miss.length ? WARN : GOOD) +
        (miss.length && !S.viewingPast ? '<button class="cm-btn ghost pfo-sm" id="pfc-research"' + (rs.busy ? ' disabled' : '') + '>🔬 ' +
          esc(rs.busy ? L('Encargando…', 'Requesting…') : L('Investigar las que faltan (' + Math.min(3, miss.length) + ')', 'Research the missing ones (' + Math.min(3, miss.length) + ')')) + '</button>' : '') +
      '</div>' +
      (ex.length ? '<div class="cm-note" style="margin-top:10px;color:' + WARN + '">⚠ ' + esc(L('Sin analizar: ', 'Not analyzed: ')) +
        ex.map(function (x) { return esc((x.label || x.symbol) + ' (' + (isEn() ? (x.reason_en || x.reason) : x.reason) + ')'); }).join(' · ') + '</div>' : '') +
      (miss.length ? '<div class="cm-note" style="margin-top:8px">' + esc(L('Sin investigar todavía: ', 'Not researched yet: ')) + esc(miss.map(function (m) { return m.label; }).join(', ')) +
        esc(L('. Su peso y riesgo SÍ están medidos; falta la opinión de los analistas (usa la IA, máx. 3 por vez, dentro del presupuesto diario).',
              '. Their weight and risk ARE measured; the analysts\' opinion is missing (uses AI, max 3 at a time, within the daily budget).')) + '</div>' : '') +
      (rs.msg ? '<div class="cm-note" style="margin-top:8px;color:' + (rs.bad ? BAD : GOOD) + '">' + esc(rs.msg) + '</div>' : ''));
  }
  // encarga investigación (POST /api/research/jobs) para hasta 3 posiciones sin investigar, una tras otra
  function researchMissing() {
    var miss = ((S.res && S.res.coverage && S.res.coverage.not_researched) || []).slice(0, 3);
    if (!miss.length) return;
    S.researching = { busy: true }; paint();
    var ok = [], bad = [];
    miss.reduce(function (pr, m) {
      return pr.then(function () {
        return fetch((window.BASE || '') + '/api/research/jobs', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Khipu-Actor': actor() },
          body: JSON.stringify({ entity: m.entity_id, actor: actor(), only_missing: true }) })
          .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { if (r.ok) ok.push(m.label); else bad.push(m.label + ': ' + ((isEn() ? (j.error_en || j.error) : j.error) || r.status)); }); })
          .catch(function () { bad.push(m.label); });
      });
    }, Promise.resolve()).then(function () {
      S.researching = { busy: false, bad: !ok.length,
        msg: (ok.length ? L('Encargado: ', 'Requested: ') + ok.join(', ') + L('. Tarda unos minutos; luego vuelve a pulsar «Analizar mi cartera».', '. It takes a few minutes; then press «Analyze my portfolio» again.') : '') +
             (bad.length ? (ok.length ? ' · ' : '') + L('No se pudo: ', 'Could not: ') + bad.join(' · ') : '') };
      paint();
    });
  }

  // 🌐 geopolítica EN VIVO de tus posiciones (World Monitor: reglas que las nombran, rutas, eventos cerca, riesgo país)
  function geoHtml(r) {
    var g = r.geo_risks || [];
    if (!g.length) return '';
    return card('<div class="cm-t pfo-hd">' + masc('radar', 18) + esc(L('Radar · geopolítica en vivo de tus posiciones', 'Radar · live geopolitics of your holdings')) + '</div>' +
      g.slice(0, 8).map(function (x) {
        return x.items.map(function (it) {
          var u = it.url && /^https?:\/\//i.test(it.url) ? it.url : null;
          return '<div class="cm-kv"><div style="min-width:0"><b>' + esc(x.label) + '</b> · ' + esc(isEn() ? it.title_en : it.title_es) + '<div class="cm-note" style="font-size:12px;margin-top:2px">' +
            esc((isEn() ? it.why_en : it.why_es) + (it.distance_km != null ? ' · ' + it.distance_km + ' km' : '') + ' · ' + (it.source || '') + ' · ' + String(it.time || '').slice(0, 10)) +
            (u ? ' · <a class="pfo-link" href="' + esc(u) + '" target="_blank" rel="noopener noreferrer">' + esc(L('fuente ↗', 'source ↗')) + '</a>' : '') + '</div></div>' +
            tag(String(it.severity), it.severity >= 70 ? BAD : it.severity >= 50 ? WARN : INK3) + '</div>';
        }).join('');
      }).join('') + '<div class="cm-note" style="font-size:11px;margin-top:8px">' + esc(L('Datos en vivo del World Monitor (pestaña Geopolítica). Severidad 0-100.', 'Live data from the World Monitor (Geopolitics tab). Severity 0-100.')) + '</div>');
  }

  function resultHtml(r) {
    var k = r.kpis, h = r.health, P = r.profile;
    var col = h.tone === 'good' ? GOOD : h.tone === 'warn' ? WARN : BAD;
    var maxW = Math.max.apply(null, r.positions.map(function (p) { return p.weight_pct; }).concat([P.max_position * 1.2]));
    var perf = r.performance;
    var src = S.lastSrc || {};
    var startPerf = (src.start && isFinite(src.start)) ? { start: src.start, now: k.value_usd } : null;
    var sc = Math.max(0, Math.min(100, Number(h.score) || 0));
    return card('<div class="pfo-hero">' +
        '<div class="pfo-ring" style="--c:' + col + '" role="img" aria-label="' + esc(L('Salud ', 'Health ') + h.score + '/100') + '">' +
          '<svg viewBox="0 0 80 80" aria-hidden="true"><circle class="t" cx="40" cy="40" r="34"/><circle class="v" cx="40" cy="40" r="34" style="stroke-dasharray:' + (sc * 2.1363).toFixed(1) + ' 214"/></svg>' +
          '<b>' + esc(h.score) + '</b></div>' +
        '<div style="flex:1;min-width:200px"><div class="pfo-verdict">' + esc(h.verdict) + '</div>' +
        '<div class="cm-note" style="margin-top:2px">' + esc(L('Salud de la cartera frente a tu perfil ', 'Portfolio health vs your profile ') + P.label + ' (0-100).') + '</div></div></div>' +
        '<div class="pfo-kpis">' +
          kpi(L('Valor hoy', 'Value today'), usd(k.value_usd)) +
          kpi(L('Cuánto se mueve al año', 'How much it moves a year'), pct(k.vol_ann_pct, 0) + qx('vol_ann'), L('tu perfil: ', 'your profile: ') + pct(P.target_vol, 0),
            k.vol_ann_pct > P.target_vol * 1.2 ? BAD : GOOD) +
          kpi(L('Peor caída del año', 'Worst fall this year'), pct(k.max_drawdown_pct, 0) + qx('drawdown')) +
          (k.var95_1d_usd != null ? kpi(L('En un mal día (1 de cada 20)', 'On a bad day (1 in 20)'), '~' + usd(k.var95_1d_usd) + qx('var'), L('podrías perder', 'you could lose'), null, 'VaR 95 %') : '') +
          (perf ? kpi(L('Vs lo que pagaste', 'Vs what you paid'), (perf.pnl_usd >= 0 ? '+' : '') + usd(perf.pnl_usd), (perf.pnl_pct >= 0 ? '+' : '') + pct(perf.pnl_pct), perf.pnl_usd >= 0 ? GOOD : BAD) : '') +
          (startPerf ? kpi(L('Desde el inicio', 'Since start'), usd(startPerf.now), L('empezó con ', 'started with ') + usd(startPerf.start)) : '') +
        '</div>') +
      '<div class="cm-disc">🤖 ' + esc(r.disclaimer) + '</div>' + coverageHtml(r) +
      (r.explanation ? card('<div class="cm-t pfo-hd">' + masc('comite', 18, 'talk') + esc(L('Lo que dice el comité', 'What the committee says')) +
          (r.explanation.ai ? ' ' + tag('🧠 ' + esc(L('IA', 'AI')), AI) : '') + '</div>' +
        '<div class="pfo-say">' + esc(r.explanation.text).replace(/\*\*([^*\n]+)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>') + '</div>') : '') +
      card('<div class="cm-t">✅ ' + esc(L('Acciones sugeridas', 'Suggested actions')) + '</div>' +
        (r.actions.length ? r.actions.map(function (a) {
          var kd = KIND[a.kind] || ['•', INK2, a.kind, a.kind], pr = PRIO[a.priority] || PRIO[3];
          var done = S.applied[a.id];
          var canApply = S.lastSrc && S.lastSrc.pfId && (a.kind !== 'buy_new' || a.entity_id);
          var btns = (canApply ? (done ? tag('✓ ' + esc(L('aplicado en la simulación', 'applied in the simulation')), GOOD)
                : '<button class="cm-btn ghost pfo-sm" data-apply="' + a.id + '">🧪 ' + esc(L('Aplicar en simulación', 'Apply in simulation')) + '</button>') : '') +
              (S.lastSrc && S.lastSrc.broker && (a.kind === 'sell' || a.kind === 'reduce' || a.kind === 'add' || a.kind === 'buy_new') ? '<button class="cm-btn ghost pfo-sm" data-trade="' + a.id + '">🧾 ' + esc(L('Preparar orden', 'Prepare order')) + '</button>' : '');
          return '<div class="pfo-act" style="--c:' + kd[1] + '">' +
            '<div class="pfo-act-hd"><span class="pfo-act-ic" aria-hidden="true">' + kd[0] + '</span>' +
            '<span class="pfo-act-tt"><em>' + esc(L(kd[2], kd[3])) + '</em> ' + esc(a.label || '') + '</span>' +
            tag(pct(a.from_pct) + ' → ' + pct(a.to_pct) + ' · ' + (a.delta_usd >= 0 ? '+' : '') + usd(a.delta_usd)) +
            tag(esc(L(pr[0], pr[1])), pr[2]) +
            (btns ? '<span class="pfo-act-btns">' + btns + '</span>' : '') + '</div>' +
            '<div class="pfo-act-why">' + esc(isEn() ? a.why_en : a.why_es) + '</div></div>';
        }).join('') : '<div class="cm-note">' + esc(L('No vemos cambios necesarios ahora. 👌', 'No changes needed right now. 👌')) + '</div>')) +
      geoHtml(r) +
      '<div class="cm-grid"><div style="min-width:0">' +
        card('<div class="cm-t">⚖️ ' + esc(L('Cuánto pesa cada posición', 'How much each position weighs')) + ' <span class="pfo-legend">· ' + esc(L('línea ámbar = tope de tu perfil', 'amber line = your profile cap')) + '</span></div>' +
          r.positions.map(function (p) { return hbar(p.label, p.weight_pct, maxW, ACC, P.max_position); }).join('')) +
        card('<div class="cm-t">🎯 ' + esc(L('Dinero vs riesgo que aporta', 'Money vs risk it brings')) + qx('risk_contrib') + '</div>' +
          r.positions.map(function (p) { return '<div class="pfo-sub">' + esc(p.label) + '</div>' + hbar(L('dinero', 'money'), p.weight_pct, 100, ACC) + hbar(L('riesgo', 'risk'), p.risk_contrib_pct, 100, NEG); }).join('')) +
      '</div><div style="min-width:0">' +
        card('<div class="cm-t">🏭 ' + esc(L('Sectores', 'Sectors')) + '</div>' + r.sectors.map(function (s) { return hbar(s.label, s.weight_pct, 100, ACC, P.max_sector); }).join('')) +
        card('<div class="cm-t pfo-hd">' + mstack(['analista', 'radar', 'cadena', 'tecnico'], 18) + esc(L('Qué dicen los analistas de tus posiciones', 'What the analysts say about your holdings')) + '</div>' +
          r.positions.map(function (p) {
            var c = p.conviction;
            return '<div class="cm-kv"><span>' + esc(p.label) + '</span><span style="font-weight:700;color:' + (c == null ? INK3 : c >= 15 ? GOOD : c <= -15 ? BAD : INK2) + '">' + (c == null ? esc(L('sin investigar', 'not researched')) : (c > 0 ? '+' : '') + Math.round(c)) + '</span></div>';
          }).join('') + '<div class="cm-note" style="font-size:11px;margin-top:8px">' + esc(L('Convicción −100 a +100 (Analista, Radar, Cadena y Técnico). "Sin investigar": pulsa 🔬 Actualizar en la Pizarra.', 'Conviction −100 to +100 (Analyst, Radar, Chain and Technical). "Not researched": press 🔬 Refresh on the Board.')) + '</div>') +
        (r.excluded && r.excluded.length && !r.coverage ? card('<div class="cm-t">⚠ ' + esc(L('No se pudieron analizar', 'Could not be analyzed')) + '</div>' + r.excluded.map(function (x) { return '<div class="cm-note">' + esc((x.label || x.symbol) + ': ' + x.reason) + '</div>'; }).join('')) : '') +
      '</div></div>' +
      '<div class="cm-note" style="font-size:11px">' + esc(L('Datos: ', 'Data: ') + (r.source || '') + ' · ' + (r.as_of || '')) + '</div>';
  }

  // 🗂 Análisis anteriores (cada corrida del comité queda registrada en el servidor, por dueño)
  function api(url) {
    return fetch((window.BASE || '') + url, { headers: { 'X-Khipu-Owner': owner() } })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { j._status = r.status; return j; }); });
  }
  function loadPast() {
    api('/api/portfolio-report/list?kind=committee').then(function (d) { S.past = d.available === false ? [] : (d.reports || []); paint(); })
      .catch(function () { S.past = []; });
  }
  function openPast(id) {
    api('/api/portfolio-report/' + encodeURIComponent(id)).then(function (d) {
      if (!d.health) { S.err = (isEn() ? (d.error_en || d.error) : d.error) || L('No se pudo abrir.', 'Could not open.'); paint(); return; }
      S.res = d; S.viewingPast = { id: id, title: d.title, at: d.created_at }; S.lastSrc = null; S.applied = {}; S.err = null; paint();
      try { S.el.scrollIntoView({ block: 'start' }); } catch (e) {}
    });
  }
  function pastHtml() {
    if (!S.past || !S.past.length) return '';
    return card('<div class="cm-t pfo-hd">' + masc('comite', 18) + '🗂 ' + esc(L('Análisis anteriores del comité', 'Previous committee analyses')) + ' <span class="pfo-legend">(' + S.past.length + ')</span></div>' +
      S.past.slice(0, 12).map(function (h) {
        var d = new Date(h.created_at), when = isNaN(d) ? '' : d.toLocaleString(isEn() ? 'en' : 'es', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
        var on = S.viewingPast && S.viewingPast.id === h.id;
        return '<div class="pfo-row' + (on ? ' on' : '') + '" data-past="' + esc(h.id) + '" role="button" tabindex="0">' +
          '<span class="w">' + esc(when) + '</span><span class="t">' + esc(h.title) + '</span><span class="s">' + esc(h.summary || '') + '</span></div>';
      }).join(''));
  }

  function paint() {
    var el = S.el; if (!el) return;
    ensureCss();
    var srcs = sources();
    if (!S.src) S.src = srcs[0] && srcs[0].key;
    el.innerHTML = '<div class="pfo">' + profileHtml() +
      (getProfile() && !S.editingProfile ? '<div class="cm-form">' +
        '<select id="pfc-src">' + srcs.map(function (s) { return '<option value="' + esc(s.key) + '"' + (S.src === s.key ? ' selected' : '') + '>' + esc(s.label) + '</option>'; }).join('') + '</select>' +
        '<button class="cm-btn" id="pfc-run"' + (S.busy ? ' disabled' : '') + '>' + esc(S.busy ? L('El comité analiza tu cartera…', 'The committee is analyzing your portfolio…') : L('💼 Analizar mi cartera', '💼 Analyze my portfolio')) + '</button></div>' +
        '<div class="pfo-seg pfo-nav" role="tablist" aria-label="' + esc(L('Secciones de tu cartera', 'Portfolio sections')) + '">' + SECTIONS.map(function (x) {
          var on = S.section === x[0];
          return '<button type="button" role="tab" aria-selected="' + on + '"' + (on ? ' class="on"' : '') + ' data-sec="' + x[0] + '">' + x[1] + ' ' + esc(L(x[2], x[3])) + '</button>'; }).join('') + '</div>' +
        (srcs.length === 1 ? '<div class="cm-note" style="margin:-4px 0 12px">' + esc(L('No tienes posiciones en Mercado ni carteras simuladas. Crea una en Mercado → Carteras (o pídele una al 🤖 Asistente) y vuelve.', 'You have no positions in Market nor simulated portfolios. Create one in Market → Portfolios (or ask the 🤖 Assistant) and come back.')) + '</div>' : '') : '') +
      (S.section !== 'diag' && getProfile() && !S.editingProfile ? '<div id="pfx"></div>' : '') +
      (S.err ? card('<div class="cm-note" style="color:' + WARN + '">' + esc(S.err) + '</div>') : '') +
      (S.section !== 'diag' ? '' : S.busy ? card('<div class="pfo-busy">' + masc('comite', 34, 'think') + '<span><span class="cm-spin">◌</span> ' + esc(L('Midiendo el riesgo con precios reales, cruzando con la investigación y preparando consejos… (10-40 s)', 'Measuring risk with real prices, crossing with research and preparing advice… (10-40 s)')) + '</span></div>') : '') +
      (S.section === 'diag' && S.res && !S.busy && S.viewingPast ? card('<div class="pfo-tags" style="justify-content:space-between"><span class="cm-note" style="color:' + WARN + '">🗂 ' +
        esc(L('Estás viendo un análisis guardado: ', 'You are viewing a saved analysis: ') + (S.viewingPast.title || '')) + '</span>' +
        '<button class="cm-btn ghost pfo-sm" id="pfc-past-close">✕ ' + esc(L('Cerrar', 'Close')) + '</button></div>') : '') +
      (S.section === 'diag' && S.res && !S.busy ? resultHtml(S.res) : '') +
      (S.section === 'diag' && getProfile() && !S.editingProfile && !S.busy ? pastHtml() : '') + '</div>';
    el.querySelectorAll('[data-q]').forEach(function (b) { b.onclick = function () { S.answers[b.getAttribute('data-q')] = b.getAttribute('data-v'); paint(); }; });
    var sp = document.getElementById('pfc-save-prof');
    if (sp) sp.onclick = function () {
      var risk = riskFromAnswers(S.answers);
      if (!risk || !S.answers.involvement) { S.err = L('Responde las 4 preguntas.', 'Answer the 4 questions.'); paint(); return; }
      saveProfile({ risk: risk, involvement: S.answers.involvement, answers: S.answers, at: new Date().toISOString() });
      S.editingProfile = false; S.err = null; paint();
    };
    var cp = document.getElementById('pfc-cancel-prof'); if (cp) cp.onclick = function () { S.editingProfile = false; paint(); };
    var sy = document.getElementById('pfc-sync'); if (sy) sy.onclick = function () { S.showSync = !S.showSync; S.syncMsg = null; paint(); };
    var sc = document.getElementById('pfc-sync-copy');
    if (sc) sc.onclick = function () {
      var t = window.KhipuSync.code();
      (navigator.clipboard && navigator.clipboard.writeText ? navigator.clipboard.writeText(t) : Promise.reject()).then(function () {
        S.syncMsg = { text: L('Código copiado.', 'Code copied.') }; paint();
      }).catch(function () { var i = document.getElementById('pfc-sync-code'); if (i) { i.select(); } });
    };
    var sl = document.getElementById('pfc-sync-link');
    if (sl) sl.onclick = function () {
      var v = (document.getElementById('pfc-sync-in') || {}).value || '';
      window.KhipuSync.link(v).then(function (r) {
        S.syncMsg = r.ok ? { text: L('Vinculado: ', 'Linked: ') + (r.changed ? L('se trajeron tus carteras.', 'your portfolios were loaded.') : L('no había datos nuevos en ese código.', 'no new data under that code.')) }
          : { bad: true, text: L('Código inválido.', 'Invalid code.') };
        S._srcCache = null; if (r.ok) S.src = null;   // vuelve a elegir la primera cartera disponible (la recién traída)
        paint();
      });
    };
    var ep = document.getElementById('pfc-edit-prof'); if (ep) ep.onclick = function () { var p = getProfile(); S.answers = (p && p.answers) || {}; S.editingProfile = true; paint(); };
    var ss = document.getElementById('pfc-src'); if (ss) ss.onchange = function () { S.src = ss.value; S.res = null; if (S.section !== 'diag') extras(); };
    el.querySelectorAll('[data-sec]').forEach(function (b) { b.onclick = function () { S.section = b.getAttribute('data-sec'); S.err = null; paint(); }; });
    if (S.section !== 'diag') extras();
    var rb = document.getElementById('pfc-run'); if (rb) rb.onclick = run;
    var rr = document.getElementById('pfc-research'); if (rr) rr.onclick = researchMissing;
    el.querySelectorAll('[data-past]').forEach(function (x) {
      x.onclick = function () { openPast(x.getAttribute('data-past')); };
      x.onkeydown = function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openPast(x.getAttribute('data-past')); } };
    });
    var pc = document.getElementById('pfc-past-close'); if (pc) pc.onclick = function () { S.res = null; S.viewingPast = null; paint(); };
    if (S.past === null && S.section === 'diag') { S.past = []; loadPast(); }
    el.querySelectorAll('[data-apply]').forEach(function (b) { b.onclick = function () { apply(b.getAttribute('data-apply')); }; });
    el.querySelectorAll('[data-trade]').forEach(function (b) { b.onclick = function () { if (window._surface) { if (window.KhipuCommittee) window.KhipuCommittee.close(); window._surface('trade'); } }; });
  }

  // 📄 Reportes · 📰 Noticias · 💬 Pregúntale (engine/pfreports.js)
  function extras() {
    var box = document.getElementById('pfx'); if (!box || !window.KhipuPortfolioExtras) return;
    var key = S.src, label = (sources().filter(function (s) { return s.key === key; })[0] || {}).label;
    if (S._srcCache && S._srcCache.key === key) { go(S._srcCache.src); return; }
    box.innerHTML = card('<div class="cm-note"><span class="cm-spin">◌</span></div>');
    positionsFor(key).then(function (src) { S._srcCache = { key: key, src: src }; go(src); })
      .catch(function (e) { box.innerHTML = card('<div class="cm-note" style="color:' + WARN + '">' + esc(String((e && e.message) || e)) + '</div>'); });
    function go(src) {
      var b = document.getElementById('pfx'); if (!b) return;
      if (!src.positions.length) { b.innerHTML = card('<div class="cm-note">' + esc(L('Esa cartera está vacía.', 'That portfolio is empty.')) + '</div>'); return; }
      window.KhipuPortfolioExtras.render(b, S.section, { source: { key: key, label: src.label || label, positions: src.positions, cash: src.cash, start: src.start, startDate: src.startDate },
        profile: getProfile(), analysis: S.res });
    }
  }

  function run() {
    var p = getProfile(); if (!p) return;
    S.busy = true; S.err = null; S.res = null; S.viewingPast = null; S.applied = {}; S.researching = null; paint();
    positionsFor(S.src).then(function (src) {
      S.lastSrc = src;
      if (!src.positions.length) throw new Error(L('Esa cartera está vacía: añádele empresas en Mercado → Carteras (🔍 buscar → Comprar) y vuelve.',
        'That portfolio is empty: add companies in Market → Portfolios (🔍 search → Buy) and come back.'));
      var label = (sources().filter(function (s) { return s.key === S.src; })[0] || {}).label || '';
      return fetch((window.BASE || '') + '/api/committee/portfolio', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Khipu-Actor': actor(), 'X-Khipu-Owner': owner() },
        body: JSON.stringify({ positions: src.positions, cash_usd: src.cash || 0, profile: p, lang: isEn() ? 'en' : 'es', actor: actor(),
          source_label: label.replace(/^[^\wÀ-ÿ]+/, '').replace(/\s·\s[^·]*$/, '') }) })
        .then(function (r) { return r.json(); });
    }).then(function (d) {
      S.busy = false;
      if (!d.ok) { S.err = (isEn() ? (d.error_en || d.error) : d.error) || L('No se pudo analizar.', 'Could not analyze.'); }
      else {
        S.res = d; S.viewingPast = null;
        if (d.saved_id) loadPast();
        if (window.KhipuPortfolioExtras && S.lastSrc) window.KhipuPortfolioExtras.syncWatch({ source: { key: S.src, label: S.lastSrc.label, positions: S.lastSrc.positions,
          cash: S.lastSrc.cash, start: S.lastSrc.start, startDate: S.lastSrc.startDate }, profile: getProfile() });
      }
      paint();
    }).catch(function (e) { S.busy = false; S.err = String((e && e.message) || e); paint(); });
  }

  function apply(aid) {
    var r = S.res, src = S.lastSrc; if (!r || !src || !src.pfId || !window.KhipuPortfolios) return;
    var a = r.actions.filter(function (x) { return x.id === aid; })[0]; if (!a) return;
    var msg = (a.label || '') + ': ' + pct(a.from_pct) + ' → ' + pct(a.to_pct) + ' (' + usd(a.delta_usd) + ')';
    var T = window.KhipuToast;
    var ask = T && T.confirm ? T.confirm({ title: L('¿Aplicar en tu cartera SIMULADA?', 'Apply to your SIMULATED portfolio?'), subtitle: msg, mode: 'sim',
      confirmLabel: L('Aplicar', 'Apply') }) : Promise.resolve(window.confirm(L('¿Aplicar en tu cartera SIMULADA?\n\n', 'Apply to your SIMULATED portfolio?\n\n') + msg));
    ask.then(function (ok) { if (ok) doApply(a, src); });
  }
  function doApply(a, src) {
    var KP = window.KhipuPortfolios, out;
    if (a.delta_usd < 0 && KP._sell) {
      var pos = (src.positions || []).filter(function (p) { return p.id === a.entity_id || p.symbol === a.symbol; })[0];
      var frac = a.from_pct > 0 ? Math.min(1, Math.abs(a.to_pct - a.from_pct) / a.from_pct) : 1;
      out = KP._sell(src.pfId, pos ? pos.id : a.entity_id, a.to_pct <= 0 ? undefined : (pos ? pos.shares * frac : undefined));
    } else if (a.delta_usd > 0 && KP._buy) {
      out = KP._buy(src.pfId, a.entity_id, { usd: a.delta_usd });
    }
    if (out && out.ok) { S.applied[a.id] = 1; S._srcCache = null; if (KP.refresh) try { KP.refresh(); } catch (e) {} }
    else S.err = (out && out.msg) || L('No se pudo aplicar.', 'Could not apply.');
    paint();
  }

  window.KhipuPortfolioCommittee = { render: function (el) { S.el = typeof el === 'string' ? document.getElementById(el) : el; S.err = null; paint(); }, _sources: sources, _positionsFor: positionsFor };
})();
