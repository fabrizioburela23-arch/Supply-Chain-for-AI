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
   ============================================================================ */
(function () {
  'use strict';
  function isEn() { var l = window.LANG; if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = null; } } return l === 'en'; }
  function L(es, en) { return isEn() ? en : es; }
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
      return card('<div class="cm-t">🧭 ' + esc(L('Tu perfil de inversionista (30 segundos)', 'Your investor profile (30 seconds)')) + '</div>' +
        '<div class="cm-note" style="margin-bottom:8px">' + esc(L('Con esto el comité sabe cuánto riesgo es "demasiado" para ti. Puedes cambiarlo cuando quieras.', 'This tells the committee how much risk is "too much" for you. You can change it anytime.')) + '</div>' +
        QUESTIONS.map(function (q) {
          return '<div style="margin:10px 0 4px;font-size:13px;font-weight:600">' + esc(L(q.es, q.en)) + '</div><div style="display:flex;gap:6px;flex-wrap:wrap">' +
            q.opts.map(function (o) { var on = S.answers[q.k] === o[0]; return '<button class="cm-tab' + (on ? ' on' : '') + '" data-q="' + q.k + '" data-v="' + o[0] + '">' + esc(L(o[1], o[2])) + '</button>'; }).join('') + '</div>';
        }).join('') +
        '<div style="margin:12px 0 4px;font-size:13px;font-weight:600">' + esc(L('¿Cuánto quieres involucrarte?', 'How involved do you want to be?')) + '</div><div style="display:flex;gap:6px;flex-wrap:wrap">' +
        INVOLVE.map(function (o) { var on = S.answers.involvement === o[0]; return '<button class="cm-tab' + (on ? ' on' : '') + '" data-q="involvement" data-v="' + o[0] + '" title="' + esc(L(o[3], o[4])) + '">' + esc(L(o[1], o[2])) + '</button>'; }).join('') + '</div>' +
        '<div style="margin-top:12px"><button class="cm-btn" id="pfc-save-prof">' + esc(L('Guardar perfil', 'Save profile')) + '</button>' +
        (p ? ' <button class="cm-btn ghost" id="pfc-cancel-prof">' + esc(L('Cancelar', 'Cancel')) + '</button>' : '') + '</div>');
    }
    var inv = INVOLVE.filter(function (x) { return x[0] === p.involvement; })[0] || INVOLVE[1];
    return '<div class="cm-note" style="margin:0 0 10px;display:flex;gap:8px;flex-wrap:wrap;align-items:center">🧭 ' + esc(L('Perfil', 'Profile')) + ': <b style="color:#E8EDFB">' + esc(L(RISK_LBL[p.risk][0], RISK_LBL[p.risk][1])) + '</b> · ' +
      esc(L(inv[1], inv[2])) + ' <button class="cm-btn ghost" id="pfc-edit-prof" style="padding:3px 10px;font-size:11.5px">✎ ' + esc(L('Cambiar', 'Change')) + '</button>' +
      (window.KhipuSync ? ' <button class="cm-btn ghost" id="pfc-sync" style="padding:3px 10px;font-size:11.5px">📱 ' + esc(L('Otros dispositivos', 'Other devices')) + '</button>' : '') + '</div>' +
      (S.showSync && window.KhipuSync ? syncHtml() : '');
  }
  // 📱 sincronización entre dispositivos (engine/sync.js)
  function syncHtml() {
    return card('<div class="cm-t">📱 ' + esc(L('Usar tus carteras en otro dispositivo', 'Use your portfolios on another device')) + '</div>' +
      '<div class="cm-note" style="margin-bottom:8px">' + esc(L('Tus carteras simuladas, tu perfil y tus posiciones se guardan solos en el servidor. Para verlos en el teléfono (u otra PC), copia este código y pégalo allá en esta misma pantalla. Guárdalo en privado: quien lo tenga ve tus carteras.',
        'Your simulated portfolios, profile and positions are saved to the server automatically. To see them on your phone (or another PC), copy this code and paste it there on this same screen. Keep it private: whoever has it sees your portfolios.')) + '</div>' +
      '<div class="cm-form" style="margin-bottom:8px"><input id="pfc-sync-code" readonly value="' + esc(window.KhipuSync.code()) + '" style="font-family:monospace;letter-spacing:.04em">' +
        '<button class="cm-btn ghost" id="pfc-sync-copy">📋 ' + esc(L('Copiar', 'Copy')) + '</button></div>' +
      '<div class="cm-form" style="margin:0"><input id="pfc-sync-in" placeholder="' + esc(L('Pega aquí el código de tu otro dispositivo', 'Paste the code from your other device')) + '">' +
        '<button class="cm-btn" id="pfc-sync-link">🔗 ' + esc(L('Vincular', 'Link')) + '</button></div>' +
      (S.syncMsg ? '<div class="cm-note" style="margin-top:6px;color:' + (S.syncMsg.bad ? '#FFB300' : '#2BE38B') + '">' + esc(S.syncMsg.text) + '</div>' : ''));
  }

  function riskFromAnswers(a) {
    var sc = 0, n = 0;
    QUESTIONS.forEach(function (q) { var o = q.opts.filter(function (x) { return x[0] === a[q.k]; })[0]; if (o) { sc += o[3]; n++; } });
    if (n < 3) return null;
    if (a.drop === 'sell' || a.horizon === 'short') return 'conservador';
    return sc >= 5 ? 'agresivo' : sc >= 3 ? 'moderado' : 'conservador';
  }

  function hbar(label, v, max, col, cap, right) {
    var w = max ? Math.max(0, Math.min(100, v / max * 100)) : 0, c = cap && max ? Math.min(100, cap / max * 100) : null;
    return '<div style="display:grid;grid-template-columns:minmax(0,120px) minmax(0,1fr) 64px;gap:8px;align-items:center;font-size:12px;margin:4px 0">' +
      '<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + esc(label) + '">' + esc(label) + '</span>' +
      '<span style="position:relative;height:10px;border-radius:5px;background:rgba(122,158,255,.12)"><i style="position:absolute;left:0;top:0;bottom:0;width:' + w + '%;border-radius:5px;background:' + col + '"></i>' +
      (c != null ? '<b title="' + esc(L('tope de tu perfil', 'your profile cap')) + '" style="position:absolute;top:-3px;bottom:-3px;left:' + c + '%;width:2px;background:#FFB300"></b>' : '') + '</span>' +
      '<span style="text-align:right;font-variant-numeric:tabular-nums">' + (right || pct(v)) + '</span></div>';
  }
  var KIND = { sell: ['🔻', '#FF4D6A', 'Vender', 'Sell'], reduce: ['➖', '#FFB300', 'Reducir', 'Reduce'], consolidate: ['🔗', '#FFB300', 'Consolidar', 'Consolidate'],
    add: ['➕', '#2BE38B', 'Aumentar', 'Add'], buy_new: ['🆕', '#5FC6E8', 'Añadir nueva', 'Add new'] };
  var PRIO = { 1: ['Prioritaria', 'Priority', '#FF4D6A'], 2: ['Recomendada', 'Recommended', '#FFB300'], 3: ['Opcional', 'Optional', '#9BA6C4'] };

  function resultHtml(r) {
    var k = r.kpis, h = r.health, P = r.profile;
    var col = h.tone === 'good' ? '#2BE38B' : h.tone === 'warn' ? '#FFB300' : '#FF4D6A';
    var maxW = Math.max.apply(null, r.positions.map(function (p) { return p.weight_pct; }).concat([P.max_position * 1.2]));
    var perf = r.performance;
    var src = S.lastSrc || {};
    var startPerf = (src.start && isFinite(src.start)) ? { start: src.start, now: k.value_usd } : null;
    return card('<div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap">' +
        '<div style="width:74px;height:74px;border-radius:50%;border:5px solid ' + col + ';display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:800;color:' + col + '">' + h.score + '</div>' +
        '<div style="flex:1;min-width:200px"><div style="font-size:15px;font-weight:700;color:#E8EDFB">' + esc(h.verdict) + '</div>' +
        '<div class="cm-note">' + esc(L('Salud de la cartera frente a tu perfil ', 'Portfolio health vs your profile ') + P.label + ' (0-100).') + '</div></div></div>' +
        '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:10px">' +
          '<span class="cm-pill">💰 ' + usd(k.value_usd) + '</span>' +
          '<span class="cm-pill" style="color:' + (k.vol_ann_pct > P.target_vol * 1.2 ? '#FF4D6A' : '#2BE38B') + '">〰 ' + esc(L('se mueve ', 'moves ')) + pct(k.vol_ann_pct, 0) + esc(L(' al año (tu perfil: ', ' a year (your profile: ')) + pct(P.target_vol, 0) + ')</span>' +
          '<span class="cm-pill">📉 ' + esc(L('peor caída del año ', 'worst fall this year ')) + pct(k.max_drawdown_pct, 0) + '</span>' +
          (k.var95_1d_usd != null ? '<span class="cm-pill" title="VaR 95 %">⚠ ' + esc(L('en un mal día (1 de cada 20) podrías perder ~', 'on a bad day (1 in 20) you could lose ~')) + usd(k.var95_1d_usd) + '</span>' : '') +
          (perf ? '<span class="cm-pill" style="color:' + (perf.pnl_usd >= 0 ? '#2BE38B' : '#FF4D6A') + '">' + esc(L('vs lo que pagaste: ', 'vs what you paid: ')) + (perf.pnl_usd >= 0 ? '+' : '') + usd(perf.pnl_usd) + ' (' + (perf.pnl_pct >= 0 ? '+' : '') + pct(perf.pnl_pct) + ')</span>' : '') +
          (startPerf ? '<span class="cm-pill">' + esc(L('desde el inicio: ', 'since start: ')) + usd(startPerf.start) + ' → ' + usd(startPerf.now) + '</span>' : '') +
        '</div>') +
      '<div class="cm-disc">🤖 ' + esc(r.disclaimer) + '</div>' +
      (r.explanation ? card('<div class="cm-t">💬 ' + esc(L('Lo que dice el comité', 'What the committee says')) + (r.explanation.ai ? ' <span class="cm-pill" style="color:#B48CFF;margin-left:6px">🧠 IA</span>' : '') + '</div>' +
        '<div class="cm-note" style="font-size:13px;color:#E8EDFB;line-height:1.6">' + esc(r.explanation.text).replace(/\n/g, '<br>') + '</div>') : '') +
      card('<div class="cm-t">✅ ' + esc(L('Acciones sugeridas', 'Suggested actions')) + '</div>' +
        (r.actions.length ? r.actions.map(function (a) {
          var kd = KIND[a.kind] || ['•', '#9BA6C4', a.kind, a.kind], pr = PRIO[a.priority] || PRIO[3];
          var done = S.applied[a.id];
          var canApply = S.lastSrc && S.lastSrc.pfId && (a.kind !== 'buy_new' || a.entity_id);
          return '<div style="border:1px solid rgba(122,158,255,.15);border-left:3px solid ' + kd[1] + ';border-radius:10px;padding:9px 12px;margin-bottom:8px">' +
            '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><b style="color:' + kd[1] + '">' + kd[0] + ' ' + esc(L(kd[2], kd[3])) + ' ' + esc(a.label || '') + '</b>' +
            '<span class="cm-pill">' + pct(a.from_pct) + ' → ' + pct(a.to_pct) + ' · ' + (a.delta_usd >= 0 ? '+' : '') + usd(a.delta_usd) + '</span>' +
            '<span class="cm-pill" style="color:' + pr[2] + ';border-color:' + pr[2] + '66">' + esc(L(pr[0], pr[1])) + '</span>' +
            '<span style="margin-left:auto;display:flex;gap:6px">' +
              (canApply ? (done ? '<span class="cm-pill" style="color:#2BE38B">✓ ' + esc(L('aplicado en la simulación', 'applied in the simulation')) + '</span>'
                : '<button class="cm-btn ghost" data-apply="' + a.id + '" style="padding:4px 10px;font-size:11.5px">🧪 ' + esc(L('Aplicar en simulación', 'Apply in simulation')) + '</button>') : '') +
              (S.lastSrc && S.lastSrc.broker && (a.kind === 'sell' || a.kind === 'reduce' || a.kind === 'add' || a.kind === 'buy_new') ? '<button class="cm-btn ghost" data-trade="' + a.id + '" style="padding:4px 10px;font-size:11.5px">🧾 ' + esc(L('Preparar orden', 'Prepare order')) + '</button>' : '') +
            '</span></div><div class="cm-note" style="margin-top:4px">' + esc(isEn() ? a.why_en : a.why_es) + '</div></div>';
        }).join('') : '<div class="cm-note">' + esc(L('No vemos cambios necesarios ahora. 👌', 'No changes needed right now. 👌')) + '</div>')) +
      '<div class="cm-grid"><div style="min-width:0">' +
        card('<div class="cm-t">⚖️ ' + esc(L('Cuánto pesa cada posición', 'How much each position weighs')) + ' <span style="text-transform:none;letter-spacing:0;font-weight:400">· ' + esc(L('línea amarilla = tope de tu perfil', 'yellow line = your profile cap')) + '</span></div>' +
          r.positions.map(function (p) { return hbar(p.label, p.weight_pct, maxW, '#00E0FF', P.max_position); }).join('')) +
        card('<div class="cm-t">🎯 ' + esc(L('Dinero vs riesgo que aporta', 'Money vs risk it brings')) + '</div>' +
          r.positions.map(function (p) { return '<div style="font-size:11.5px;margin-top:6px;color:#C9D2EA">' + esc(p.label) + '</div>' + hbar(L('dinero', 'money'), p.weight_pct, 100, '#00E0FF') + hbar(L('riesgo', 'risk'), p.risk_contrib_pct, 100, '#FF4D6A'); }).join('')) +
      '</div><div style="min-width:0">' +
        card('<div class="cm-t">🏭 ' + esc(L('Sectores', 'Sectors')) + '</div>' + r.sectors.map(function (s) { return hbar(s.label, s.weight_pct, 100, '#B48CFF', P.max_sector); }).join('')) +
        card('<div class="cm-t">🔬 ' + esc(L('Qué dicen los analistas de tus posiciones', 'What the analysts say about your holdings')) + '</div>' +
          r.positions.map(function (p) {
            var c = p.conviction;
            return '<div class="cm-kv"><span>' + esc(p.label) + '</span><span style="color:' + (c == null ? '#7C87A3' : c >= 15 ? '#2BE38B' : c <= -15 ? '#FF4D6A' : '#9BA6C4') + '">' + (c == null ? esc(L('sin investigar', 'not researched')) : (c > 0 ? '+' : '') + Math.round(c)) + '</span></div>';
          }).join('') + '<div class="cm-note" style="font-size:10.5px;margin-top:4px">' + esc(L('Convicción −100 a +100. "Sin investigar": pulsa 🔬 Actualizar en la Pizarra.', 'Conviction −100 to +100. "Not researched": press 🔬 Refresh on the Board.')) + '</div>') +
        (r.excluded && r.excluded.length ? card('<div class="cm-t">⚠ ' + esc(L('No se pudieron analizar', 'Could not be analyzed')) + '</div>' + r.excluded.map(function (x) { return '<div class="cm-note">' + esc((x.label || x.symbol) + ': ' + x.reason) + '</div>'; }).join('')) : '') +
      '</div></div>' +
      '<div class="cm-note" style="font-size:10.5px">' + esc(L('Datos: ', 'Data: ') + (r.source || '') + ' · ' + (r.as_of || '')) + '</div>';
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
    return card('<div class="cm-t">🗂 ' + esc(L('Análisis anteriores del comité', 'Previous committee analyses')) + ' <span class="cm-note">(' + S.past.length + ')</span></div>' +
      S.past.slice(0, 12).map(function (h) {
        var d = new Date(h.created_at), when = isNaN(d) ? '' : d.toLocaleString(isEn() ? 'en' : 'es', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
        var on = S.viewingPast && S.viewingPast.id === h.id;
        return '<div data-past="' + esc(h.id) + '" style="cursor:pointer;display:flex;gap:10px;align-items:baseline;padding:6px 8px;border-radius:8px;margin-top:4px;' +
          (on ? 'background:rgba(0,224,255,.08);' : '') + 'border:1px solid rgba(122,158,255,.12)">' +
          '<span style="font-size:11px;color:#7C87A3;min-width:96px">' + esc(when) + '</span>' +
          '<span style="flex:1;font-size:12.5px;color:#E8EDFB">' + esc(h.title) + '</span>' +
          '<span class="cm-note" style="font-size:11.5px">' + esc(h.summary || '') + '</span></div>';
      }).join(''));
  }

  function paint() {
    var el = S.el; if (!el) return;
    var srcs = sources();
    if (!S.src) S.src = srcs[0] && srcs[0].key;
    el.innerHTML = profileHtml() +
      (getProfile() && !S.editingProfile ? '<div class="cm-form">' +
        '<select id="pfc-src">' + srcs.map(function (s) { return '<option value="' + esc(s.key) + '"' + (S.src === s.key ? ' selected' : '') + '>' + esc(s.label) + '</option>'; }).join('') + '</select>' +
        '<button class="cm-btn" id="pfc-run"' + (S.busy ? ' disabled' : '') + '>' + esc(S.busy ? L('El comité analiza tu cartera…', 'The committee is analyzing your portfolio…') : L('💼 Analizar mi cartera', '💼 Analyze my portfolio')) + '</button></div>' +
        '<div class="cm-tabs" style="margin:-2px 0 12px">' + SECTIONS.map(function (x) { return '<button class="cm-tab' + (S.section === x[0] ? ' on' : '') + '" data-sec="' + x[0] + '">' + x[1] + ' ' + esc(L(x[2], x[3])) + '</button>'; }).join('') + '</div>' +
        (srcs.length === 1 ? '<div class="cm-note" style="margin:-4px 0 10px">' + esc(L('No tienes posiciones en Mercado ni carteras simuladas. Crea una en Mercado → Carteras (o pídele una al 🤖 Asistente) y vuelve.', 'You have no positions in Market nor simulated portfolios. Create one in Market → Portfolios (or ask the 🤖 Assistant) and come back.')) + '</div>' : '') : '') +
      (S.section !== 'diag' && getProfile() && !S.editingProfile ? '<div id="pfx"></div>' : '') +
      (S.err ? card('<div class="cm-note" style="color:#FFB300">' + esc(S.err) + '</div>') : '') +
      (S.section !== 'diag' ? '' : S.busy ? card('<div class="cm-note"><span class="cm-spin">◌</span> ' + esc(L('Midiendo el riesgo con precios reales, cruzando con la investigación y preparando consejos… (10-40 s)', 'Measuring risk with real prices, crossing with research and preparing advice… (10-40 s)')) + '</div>') : '') +
      (S.section === 'diag' && S.res && !S.busy && S.viewingPast ? card('<div class="cm-note" style="color:#FFB300">🗂 ' +
        esc(L('Estás viendo un análisis guardado: ', 'You are viewing a saved analysis: ') + (S.viewingPast.title || '')) +
        ' <button class="cm-tab" id="pfc-past-close" style="margin-left:6px">✕ ' + esc(L('Cerrar', 'Close')) + '</button></div>') : '') +
      (S.section === 'diag' && S.res && !S.busy ? resultHtml(S.res) : '') +
      (S.section === 'diag' && getProfile() && !S.editingProfile && !S.busy ? pastHtml() : '');
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
    el.querySelectorAll('[data-past]').forEach(function (x) { x.onclick = function () { openPast(x.getAttribute('data-past')); }; });
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
      .catch(function (e) { box.innerHTML = card('<div class="cm-note" style="color:#FFB300">' + esc(String((e && e.message) || e)) + '</div>'); });
    function go(src) {
      var b = document.getElementById('pfx'); if (!b) return;
      if (!src.positions.length) { b.innerHTML = card('<div class="cm-note">' + esc(L('Esa cartera está vacía.', 'That portfolio is empty.')) + '</div>'); return; }
      window.KhipuPortfolioExtras.render(b, S.section, { source: { key: key, label: src.label || label, positions: src.positions, cash: src.cash, start: src.start, startDate: src.startDate },
        profile: getProfile(), analysis: S.res });
    }
  }

  function run() {
    var p = getProfile(); if (!p) return;
    S.busy = true; S.err = null; S.res = null; S.viewingPast = null; S.applied = {}; paint();
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
    if (out && out.ok) { S.applied[aid] = 1; S._srcCache = null; if (KP.refresh) try { KP.refresh(); } catch (e) {} }
    else S.err = (out && out.msg) || L('No se pudo aplicar.', 'Could not apply.');
    paint();
  }

  window.KhipuPortfolioCommittee = { render: function (el) { S.el = typeof el === 'string' ? document.getElementById(el) : el; S.err = null; paint(); }, _sources: sources };
})();
