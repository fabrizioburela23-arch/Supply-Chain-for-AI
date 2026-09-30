/* ============================================================================
   engine/committee.js — PHASE 3 · COMITÉ DE INVERSIÓN (con aprobación humana)

   window.KhipuCommittee.open(entityId?)   overlay con 3 pestañas
   window.KhipuCommittee.close()

   · Comité: elegir empresa (y cliente opcional) → correr → memo: decisión,
     convicción por horizonte, tamaño con la cuenta a la vista, tesis, riesgos,
     disenso, falsadores, aprobar / rechazar (PIN vía window._tradeFetch).
   · Historial: aciertos por agente, Brier, fiabilidad, curva de calibración
     (Chart.js si existe), últimas calificaciones reales.
   · Cómo aprende: explicación en lenguaje simple.
   Solo muestra lo que existe en el servidor (/api/committee/*). Bilingüe.
   Una propuesta NUNCA se ejecuta sola: aprobar crea una previsualización que
   también se aprueba en la pantalla de clientes.
   ============================================================================ */
(function () {
  'use strict';

  function isEn() { var l = window.LANG; if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = null; } } return l === 'en'; }
  function L(es, en) { return isEn() ? en : es; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function base() { return window.BASE || ''; }
  function chip(k) { return window.explainChip ? window.explainChip(k) : ''; }
  function nodeLabel(id) { var n = (window.NODE_BY_ID || {})[id]; return (n && n.label) || id || ''; }
  function clock(iso) { var d = new Date(iso); return isNaN(d) ? '' : d.toLocaleString(isEn() ? 'en' : 'es', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }); }
  function day(iso) { var d = new Date(iso); return isNaN(d) ? (iso || '') : d.toLocaleDateString(isEn() ? 'en' : 'es', { day: '2-digit', month: 'short', year: 'numeric' }); }
  function pct(v, nd) { return v == null ? '—' : (v * 100).toFixed(nd == null ? 0 : nd) + '%'; }
  function money(v) { return v == null ? '—' : '$' + Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 }); }
  function actor() { var a = null; try { a = localStorage.getItem('khipu_actor'); } catch (e) {} return (a && a.trim()) || 'usuario'; }

  var AG = {
    fundamental: ['📊', 'Fundamental', 'Fundamental'], technical: ['📈', 'Técnico', 'Technical'],
    news: ['📰', 'Noticias', 'News'], supply_chain: ['🔗', 'Cadena de suministro', 'Supply chain'],
    geopolitical: ['🗺️', 'Geopolítica', 'Geopolitics'], macro: ['🌐', 'Macro', 'Macro'],
    crypto: ['₿', 'Cripto', 'Crypto'], risk_observation: ['⚠️', 'Riesgos', 'Risks'], committee: ['🏛', 'Comité', 'Committee'],
  };
  function ag(t) { var a = AG[t] || ['🤖', t, t]; return a[0] + ' ' + L(a[1], a[2]); }
  var HZ = { INTRADAY: ['Intradía', 'Intraday'], SHORT_TERM: ['Corto plazo', 'Short term'], MEDIUM_TERM: ['Mediano plazo', 'Medium term'],
    LONG_TERM: ['Largo plazo', 'Long term'], STRUCTURAL: ['Estructural', 'Structural'] };
  function hz(h) { var x = HZ[h] || [h, h]; return L(x[0], x[1]); }
  var HZ_ORDER = ['SHORT_TERM', 'MEDIUM_TERM', 'LONG_TERM', 'STRUCTURAL', 'INTRADAY'];
  var DEC = { BUY: ['#2BE38B', 'COMPRAR', 'BUY'], ADD: ['#2BE38B', 'AUMENTAR', 'ADD'], HOLD: ['#9BA6C4', 'MANTENER / ESPERAR', 'HOLD / WAIT'],
    TRIM: ['#FFB300', 'REDUCIR', 'TRIM'], SELL: ['#FF4D6A', 'VENDER', 'SELL'], AVOID: ['#FF4D6A', 'EVITAR', 'AVOID'] };
  var STATUS = { running: ['deliberando…', 'deliberating…'], failed: ['falló', 'failed'], proposed: ['propuesta (pendiente de aprobación)', 'proposal (awaiting approval)'],
    approved: ['aprobada por un humano', 'approved by a human'], rejected: ['rechazada', 'rejected'], executed: ['ejecutada', 'executed'] };
  var RES = { hit: ['#2BE38B', 'acierto', 'hit'], miss: ['#FF4D6A', 'fallo', 'miss'], 'n/a': ['#9BA6C4', 'n/a', 'n/a'] };

  // ── "?" de cada métrica (registradas en engine/explain.js) ────────────────
  function registerExplain() {
    if (!window.explainRegister) return;
    var R = window.explainRegister;
    R('conviction', {
      es: { t: 'Convicción del comité (−100 a +100)', b: 'Resume qué tan de acuerdo están los agentes, por plazo. Cada conclusión pesa según su <b>confianza calibrada</b> y el <b>historial</b> del agente que la escribió. A favor suma, en contra resta. Con poca evidencia el número se acerca a 0 (hay un "peso de la duda"), y si las conclusiones se contradicen entre sí se recorta hasta a la mitad. +100 = todos muy seguros a favor; −100 = todos muy seguros en contra. <b>No es una probabilidad de ganar dinero.</b>' },
      en: { t: 'Committee conviction (−100 to +100)', b: 'Summarizes how much the agents agree, per horizon. Each conclusion weighs by its <b>calibrated confidence</b> and the <b>track record</b> of the agent that wrote it. For adds, against subtracts. With little evidence the number moves toward 0 (a "weight of doubt"), and if conclusions contradict each other it is cut up to half. +100 = everyone very sure in favor; −100 = everyone very sure against. <b>It is not a probability of making money.</b>' } });
    R('brier', {
      es: { t: 'Puntaje de Brier', b: 'Mide si la confianza que declaró un agente fue honesta. Por cada predicción calificada: (confianza − resultado)², donde resultado es 1 si acertó y 0 si falló; luego se promedia. <b>0 es perfecto</b>; 0.25 es lo que saca alguien que siempre dice "50 %"; más alto es peor. Premia acertar Y no exagerar la seguridad.' },
      en: { t: 'Brier score', b: 'Measures whether the confidence an agent stated was honest. For each scored prediction: (confidence − outcome)², where outcome is 1 for a hit and 0 for a miss; then averaged. <b>0 is perfect</b>; 0.25 is what someone who always says "50%" gets; higher is worse. It rewards being right AND not overstating certainty.' } });
    R('calibration', {
      es: { t: 'Confianza calibrada', b: 'La confianza "cruda" sale de la calidad de la evidencia. La calibrada la corrige con lo que de verdad pasó: si las conclusiones de un agente con ~70 % de confianza acertaron solo 50 % de las veces, sus próximas conclusiones de ~70 % se ajustan hacia abajo. Fórmula: (aciertos del tramo + 10 × cruda) ÷ (n del tramo + 10). Con poca historia casi no cambia; por eso decimos "sin historial suficiente" cuando hay menos de 5 casos.' },
      en: { t: 'Calibrated confidence', b: 'The "raw" confidence comes from evidence quality. The calibrated one corrects it with what actually happened: if an agent\'s ~70%-confidence conclusions were right only 50% of the time, its next ~70% conclusions are adjusted down. Formula: (bucket hits + 10 × raw) ÷ (bucket n + 10). With little history it barely changes; that is why we say "not enough history" with fewer than 5 cases.' } });
    R('hit_rate', {
      es: { t: 'Tasa de acierto', b: 'De las predicciones ya vencidas, cuántas se cumplieron. Se califica con precios reales: el retorno de la acción MENOS el del S&P 500 (SPY) en el plazo de la conclusión. Si era positiva, acierta si le ganó al mercado por más de 2 %; si era negativa, si quedó más de 2 % por debajo; si era neutral, si quedó dentro de ±2 %. Las posturas mixtas y las empresas que no cotizan no se califican (n/a).' },
      en: { t: 'Hit rate', b: 'Of the predictions already due, how many came true. Scored with real prices: the stock\'s return MINUS the S&P 500 (SPY) over the conclusion\'s horizon. A positive one is a hit if it beat the market by more than 2%; a negative one if it lagged by more than 2%; a neutral one if it stayed within ±2%. Mixed stances and unlisted companies are not scored (n/a).' } });
    R('position_sizing', {
      es: { t: 'Tamaño de la posición (por volatilidad)', b: 'El tamaño NO lo decide la IA: es una cuenta fija. Se elige cuánto riesgo anual aceptar por posición (por defecto 2 % del patrimonio) y se divide entre la volatilidad anual de la acción: una acción el doble de movida recibe la mitad del dinero. Luego se aplican topes: máximo por posición del mandato (por defecto 10 %), lo que ya tienes y tu poder de compra. Ejemplo: 2 % ÷ 40 % de volatilidad = 5 % del patrimonio.' },
      en: { t: 'Position size (volatility targeting)', b: 'The size is NOT decided by the AI: it is a fixed calculation. You choose how much annual risk to accept per position (2% of equity by default) and divide it by the stock\'s annual volatility: a stock twice as volatile gets half the money. Then caps apply: the mandate\'s max per position (10% by default), what you already hold and your buying power. Example: 2% ÷ 40% volatility = 5% of equity.' } });
    R('committee_decision', {
      es: { t: 'Decisión del comité', b: '<b>COMPRAR</b> (abrir) si la convicción global es ≥ +35 · <b>AUMENTAR</b> si ya tienes y estás bajo tu tamaño objetivo · <b>MANTENER / ESPERAR</b> si no alcanza · <b>REDUCIR</b> si baja de −20 o tu posición pasó el 125 % del objetivo · <b>VENDER</b> si baja de −50 · <b>EVITAR</b> si no la tienes y es negativa (o no cotiza). El presidente IA puede rebajar a MANTENER explicando por qué, nunca subir. Es una PROPUESTA: nada se ejecuta sin tu aprobación, y no es asesoría personalizada.' },
      en: { t: 'Committee decision', b: '<b>BUY</b> (open) if overall conviction is ≥ +35 · <b>ADD</b> if you already hold it and are below your target size · <b>HOLD / WAIT</b> if it does not reach that · <b>TRIM</b> if it falls below −20 or your position exceeds 125% of target · <b>SELL</b> below −50 · <b>AVOID</b> if you do not hold it and it is negative (or unlisted). The AI chair may downgrade to HOLD explaining why, never upgrade. It is a PROPOSAL: nothing executes without your approval, and it is not personalized advice.' } });
    R('reliability', {
      es: { t: 'Fiabilidad del agente', b: 'Qué tanto confiar en un agente según su historial REAL: sus aciertos más 10 "aciertos a medias" imaginarios, divididos entre sus predicciones calificadas más 10. Sin historial vale 50 % (neutral); con muchos aciertos sube hacia 100 %, con muchos fallos baja hacia 0 %. En el comité multiplica el peso de sus conclusiones: 50 % = ×1, 75 % = ×1.5.' },
      en: { t: 'Agent reliability', b: 'How much to trust an agent based on its REAL track record: its hits plus 10 imaginary "half hits", divided by its scored predictions plus 10. With no history it is 50% (neutral); many hits push it toward 100%, many misses toward 0%. In the committee it multiplies the weight of its conclusions: 50% = ×1, 75% = ×1.5.' } });
    R('early_signal', {
      es: { t: 'Señal temprana', b: 'Tasa de acierto en las revisiones INTERMEDIAS (por ejemplo a los 7 días de una conclusión de 30 días, o a los 90 y 180 días de una de largo plazo). Sirve para ver cómo va un agente antes de que venzan sus predicciones, pero NO cuenta para su fiabilidad ni para la calibración: solo cuentan las revisiones finales.' },
      en: { t: 'Early signal', b: 'Hit rate on INTERMEDIATE checks (e.g. at 7 days for a 30-day conclusion, or at 90 and 180 days for a long-term one). It shows how an agent is doing before its predictions come due, but it does NOT count toward its reliability or calibration: only final checks count.' } });
    R('committee_confidence', {
      es: { t: 'Confianza del comité', b: 'Qué tan seguro está el comité de SU decisión (0–100 %). Con presidente IA es su estimación honesta considerando el disenso y la calidad de la evidencia; sin IA se calcula: qué parte del peso de las conclusiones apoya la dirección elegida × su confianza calibrada promedio. No es la probabilidad de ganar dinero.' },
      en: { t: 'Committee confidence', b: 'How sure the committee is of ITS decision (0–100%). With the AI chair it is its honest estimate given dissent and evidence quality; without AI it is computed: the share of conclusion weight that supports the chosen direction × their average calibrated confidence. It is not the probability of making money.' } });
    return true;
  }
  // committee.js carga ANTES que engine/explain.js: se registra al estar el DOM
  // listo (explain.js ya corrió) y se reintenta al abrir. Sin esto los "?" de
  // research.js (🎯 calibrada) no hacían nada hasta abrir el comité.
  var _explained = false;
  function ensureExplain() { if (!_explained && window.explainRegister) _explained = !!registerExplain(); }
  ensureExplain();
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ensureExplain);
  setTimeout(ensureExplain, 0);

  function ensureStyles() {
    if (document.getElementById('cm-styles')) return;
    var css = '' +
      '#cm-ov{position:fixed;inset:0;z-index:7650;display:none;align-items:center;justify-content:center;background:rgba(3,6,12,.72);backdrop-filter:blur(4px);font-family:Inter,system-ui,sans-serif}' +
      '#cm-ov.show{display:flex}' +
      '#cm{width:min(1120px,96vw);max-height:92vh;overflow-y:auto;overflow-x:hidden;border-radius:18px;color:#E8EDFB;background:radial-gradient(1000px 500px at 50% -10%,#0B1222 0%,#06090F 60%);border:1px solid rgba(122,158,255,.2);box-shadow:0 30px 80px rgba(0,0,0,.6);padding:20px 22px;box-sizing:border-box}' +
      '#cm *{box-sizing:border-box}' +
      '#cm .cm-hd{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:6px}' +
      '#cm .cm-name{font-size:21px;font-weight:750;min-width:0;overflow-wrap:anywhere}' +
      '#cm .cm-x{margin-left:auto;width:32px;height:32px;border-radius:9px;cursor:pointer;border:1px solid rgba(122,158,255,.2);background:rgba(21,28,45,.7);color:#7C87A3;font-size:16px;flex:0 0 auto}' +
      '#cm .cm-sub{font-size:11.5px;color:#7C87A3;margin-bottom:12px;line-height:1.5}' +
      '#cm .cm-tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}' +
      '#cm .cm-tab{font-size:12.5px;padding:6px 12px;border-radius:999px;border:1px solid rgba(122,158,255,.2);background:none;color:#9BA6C4;cursor:pointer}' +
      '#cm .cm-tab.on{border-color:#00E0FF;color:#00E0FF;background:rgba(0,224,255,.08)}' +
      '#cm .cm-btn{border:1px solid #00E0FF;background:rgba(0,224,255,.12);color:#00E0FF;font-weight:700;font-size:12.5px;padding:7px 14px;border-radius:9px;cursor:pointer}' +
      '#cm .cm-btn[disabled]{opacity:.5;cursor:default}' +
      '#cm .cm-btn.ok{border-color:#2BE38B;color:#2BE38B;background:rgba(43,227,139,.1)}' +
      '#cm .cm-btn.no{border-color:#FF4D6A;color:#FF4D6A;background:rgba(255,77,106,.08)}' +
      '#cm .cm-btn.ghost{border-color:rgba(122,158,255,.3);color:#9BA6C4;background:none;font-weight:600}' +
      '#cm input,#cm select{background:#0B1222;color:#E8EDFB;border:1px solid rgba(122,158,255,.25);border-radius:8px;padding:7px 9px;font-size:12.5px;min-width:0;max-width:100%}' +
      '#cm .cm-form{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px}' +
      '#cm .cm-form input{flex:1 1 180px}#cm .cm-form select{flex:1 1 180px}' +
      '#cm .cm-grid{display:grid;grid-template-columns:minmax(0,3fr) minmax(0,2fr);gap:14px}' +
      '#cm .cm-cell{border:1px solid rgba(122,158,255,.14);border-radius:13px;background:rgba(11,18,34,.55);padding:12px 14px;margin-bottom:12px;min-width:0}' +
      '#cm .cm-t{font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#7C87A3;margin-bottom:8px;display:flex;align-items:center;gap:2px}' +
      '#cm .cm-note{font-size:12px;color:#9BA6C4;line-height:1.55;overflow-wrap:anywhere}' +
      '#cm .cm-dec{display:inline-flex;align-items:center;gap:6px;font-size:15px;font-weight:800;letter-spacing:.04em;padding:6px 14px;border-radius:10px;border:1.5px solid}' +
      '#cm .cm-pill{font-size:10.5px;padding:2px 9px;border-radius:999px;border:1px solid rgba(122,158,255,.25);color:#9BA6C4;white-space:nowrap}' +
      '#cm .cm-g{display:grid;grid-template-columns:110px minmax(0,1fr) 46px;align-items:center;gap:8px;font-size:12px;margin:5px 0}' +
      '#cm .cm-gt{position:relative;height:10px;border-radius:5px;background:rgba(122,158,255,.1);overflow:hidden}' +
      '#cm .cm-gt i{position:absolute;top:0;bottom:0;border-radius:4px}' +
      '#cm .cm-gt b{position:absolute;left:50%;top:-2px;bottom:-2px;width:1px;background:rgba(155,166,196,.6)}' +
      '#cm .cm-gv{text-align:right;font-variant-numeric:tabular-nums;font-weight:700}' +
      '#cm .cm-list{margin:4px 0 0 18px;padding:0;font-size:12.5px;line-height:1.55;color:#C9D2EA}' +
      '#cm .cm-list li{margin-bottom:5px;overflow-wrap:anywhere}' +
      '#cm .cm-ref{font-size:10.5px;color:#5FC6E8;cursor:pointer;margin-left:4px;white-space:nowrap}' +
      '#cm .cm-kv{display:flex;justify-content:space-between;gap:10px;font-size:12px;padding:4px 0;border-bottom:1px solid rgba(122,158,255,.06)}' +
      '#cm .cm-kv span:last-child{text-align:right;font-variant-numeric:tabular-nums}' +
      '#cm .cm-disc{font-size:11.5px;color:#FFB300;border:1px solid rgba(255,179,0,.35);background:rgba(255,179,0,.06);border-radius:10px;padding:9px 12px;line-height:1.5;margin-bottom:12px}' +
      '#cm .cm-msg{border-radius:10px;padding:9px 12px;font-size:12.5px;margin-bottom:10px;line-height:1.5}' +
      '#cm .cm-tw{overflow-x:auto;max-width:100%}' +
      '#cm table{width:100%;border-collapse:collapse;font-size:12px}' +
      '#cm th{font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:#7C87A3;text-align:left;padding:6px 8px;border-bottom:1px solid rgba(122,158,255,.15);white-space:nowrap}' +
      '#cm td{padding:6px 8px;border-bottom:1px solid rgba(122,158,255,.06);white-space:nowrap;font-variant-numeric:tabular-nums}' +
      '#cm .cm-steps{margin:6px 0 0 16px;padding:0;font-size:12px;color:#C9D2EA;line-height:1.55}' +
      '#cm .cm-hist{font-size:11.5px;padding:5px 0;border-bottom:1px solid rgba(122,158,255,.07);cursor:pointer}' +
      '#cm .cm-hist:hover{color:#00E0FF}' +
      '#cm a{color:#5FC6E8;text-decoration:none}' +
      '#cm .cm-learn p{font-size:13px;line-height:1.65;color:#C9D2EA;margin:0 0 10px}' +
      '#cm .cm-learn h4{font-size:13.5px;margin:14px 0 6px;color:#E8EDFB}' +
      '@media(max-width:760px){#cm .cm-grid{grid-template-columns:minmax(0,1fr)}#cm{padding:16px 12px;width:100vw;max-height:100vh;border-radius:0}#cm .cm-g{grid-template-columns:86px minmax(0,1fr) 40px}}';
    var st = document.createElement('style'); st.id = 'cm-styles'; st.textContent = css;
    document.head.appendChild(st);
  }

  var S = { tab: 'committee', entity: null, clientId: '', memo: null, history: [], poll: null, busy: false, msg: null,
    clients: null, clientsErr: null, tr: null, cal: null, recent: null, agentSel: '__all', chart: null,
    running: null, deciding: false };
  function T(d, k) { return d ? (isEn() ? (d[k + '_en'] || d[k]) : d[k]) : ''; }   // texto del servidor es/en
  function decLabel(code) { var d = DEC[code]; return d ? L(d[1], d[2]) : (code || '—'); }
  function badge(cm) {
    if (!cm) return '';
    return (cm.paper === false || cm.mode === 'live') ? L('🔴 DINERO REAL', '🔴 REAL MONEY') : L('🧪 SIMULADO', '🧪 PAPER');
  }

  // ── red ────────────────────────────────────────────────────────────────────
  function parse(r) {
    return r.text().then(function (t) {
      var d; try { d = JSON.parse(t); } catch (e) { d = { _raw: String(t || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 160) }; }
      if (!d || typeof d !== 'object') d = {};
      d._status = r.status; return d;
    });
  }
  function getJSON(url, opts) { return fetch(base() + url, opts).then(parse); }
  function pinJSON(url, opts, interactive) {
    if (typeof window._tradeFetch === 'function') return window._tradeFetch(base() + url, opts || {}, !!interactive).then(parse);
    return getJSON(url, opts);
  }
  function errText(d) {
    var st = d && d._status;
    if (st === 403 && d.code === 'trading_disabled') return L('Aprobar/rechazar está deshabilitado: configura TRADE_PIN en Railway.', 'Approve/reject is disabled: set TRADE_PIN on Railway.');
    if (st === 401) return L('PIN de trading incorrecto o faltante.', 'Wrong or missing trading PIN.');
    if (st === 429) return L('Demasiados pedidos en poco tiempo. Espera unos minutos.', 'Too many requests. Wait a few minutes.');
    if (st === 429) return T(d, 'error') || L('Demasiados pedidos en poco tiempo. Espera unos minutos.', 'Too many requests. Wait a few minutes.');
    if (st === 404) return T(d, 'error') || L('No encontrado.', 'Not found.');
    if (st === 503) return L('El comité necesita la base de datos (DATABASE_URL en Railway).', 'The committee needs the database (DATABASE_URL on Railway).');
    if (st === 409) return T(d, 'error') || L('La acción no aplica en el estado actual del memo.', 'The action does not apply to the memo\'s current state.');
    return (T(d, 'error') || L('Algo falló.', 'Something failed.')) + ' [' + (st || '?') + (d && d.detail ? ' · ' + d.detail : '') + ']';
  }

  // ── shell ──────────────────────────────────────────────────────────────────
  function shell() {
    ensureStyles();
    var ov = document.getElementById('cm-ov');
    if (!ov) {
      ov = document.createElement('div'); ov.id = 'cm-ov';
      ov.innerHTML = '<div id="cm" role="dialog" aria-modal="true"></div>';
      ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
      document.body.appendChild(ov);
    }
    return ov;
  }
  function close() {
    var ov = document.getElementById('cm-ov'); if (ov) ov.classList.remove('show');
    // el comité sigue deliberando en el servidor: se recuerda (S.running) y al
    // volver a abrir se retoma la consulta; si no, «Correr comité» quedaría
    // deshabilitado para siempre
    if (S.poll) { clearInterval(S.poll); S.poll = null; }
    if (S.chart) { try { S.chart.destroy(); } catch (e) {} S.chart = null; }
    S.deciding = false;
  }

  function render() {
    var el = document.getElementById('cm'); if (!el) return;
    if (S.chart) { try { S.chart.destroy(); } catch (e) {} S.chart = null; }
    var tabs = [['committee', '🏛 ' + L('Comité', 'Committee')], ['history', '🎯 ' + L('Historial', 'Track record')], ['learn', '🧠 ' + L('Cómo aprende', 'How it learns')]];
    el.innerHTML =
      '<div class="cm-hd"><span class="cm-name">🏛 ' + esc(L('Comité de inversión', 'Investment committee')) + (S.entity ? ' · ' + esc(nodeLabel(S.entity)) : '') + '</span>' +
        '<button class="cm-x" onclick="window.KhipuCommittee.close()" title="' + esc(L('Cerrar', 'Close')) + '">✕</button></div>' +
      '<div class="cm-sub">' + esc(L('Un comité automatizado reúne la investigación de todos los agentes, su historial real de aciertos, el riesgo medido y datos en vivo, y propone una decisión con su tamaño. Nada se ejecuta sin tu aprobación.',
        'An automated committee gathers the research of every agent, their real track record, measured risk and live data, and proposes a decision with its size. Nothing executes without your approval.')) + '</div>' +
      '<div class="cm-tabs">' + tabs.map(function (t) { return '<button class="cm-tab' + (S.tab === t[0] ? ' on' : '') + '" data-t="' + t[0] + '">' + esc(t[1]) + '</button>'; }).join('') + '</div>' +
      (S.msg ? '<div class="cm-msg" style="border:1px solid ' + (S.msg.bad ? '#FFB300' : '#2BE38B') + ';color:' + (S.msg.bad ? '#FFB300' : '#2BE38B') + '">' + esc(S.msg.text) + '</div>' : '') +
      '<div id="cm-body"></div>';
    el.querySelectorAll('.cm-tab').forEach(function (b) { b.onclick = function () { S.tab = b.getAttribute('data-t'); S.msg = null; render(); }; });
    var body = document.getElementById('cm-body');
    if (S.tab === 'history') renderHistory(body);
    else if (S.tab === 'learn') renderLearn(body);
    else renderCommittee(body);
  }

  // ── pestaña Comité ─────────────────────────────────────────────────────────
  function clientOptions() {
    var o = '<option value="">' + esc(L('Sin cliente (referencia ilustrativa)', 'No client (illustrative reference)')) + '</option>';
    (S.clients || []).forEach(function (c) {
      var id = c.id || c.client_id;
      o += '<option value="' + esc(id) + '"' + (S.clientId === id ? ' selected' : '') + '>' + esc((c.name || c.display_name || id) + ' · ' + (c.mode === 'live' ? L('real', 'live') : L('simulado', 'paper'))) + '</option>';
    });
    return o;
  }

  function renderCommittee(body) {
    var m = S.memo;
    body.innerHTML =
      '<div class="cm-form">' +
        '<input id="cm-ent" placeholder="' + esc(L('Empresa o ticker (ej. NVDA)', 'Company or ticker (e.g. NVDA)')) + '" value="' + esc(S.entity ? nodeLabel(S.entity) : '') + '">' +
        '<select id="cm-cli">' + clientOptions() + '</select>' +
        (S.clients === null ? '<button class="cm-btn ghost" id="cm-lc">🔒 ' + esc(L('Cargar clientes (PIN)', 'Load clients (PIN)')) + '</button>' : '') +
        '<button class="cm-btn" id="cm-run"' + (S.busy ? ' disabled' : '') + '>' + esc(S.busy ? L('El comité delibera…', 'Committee deliberating…') : L('Correr comité', 'Run committee')) + '</button>' +
      '</div>' +
      (S.clientsErr ? '<div class="cm-note" style="margin:-4px 0 10px">' + esc(S.clientsErr) + '</div>' : '') +
      (S.busy ? '<div class="cm-cell"><div class="cm-note">⏳ ' + esc(L('Reuniendo investigación, historial de los agentes, riesgo medido y datos en vivo; el presidente IA redacta el memo (hasta ~1 minuto).', 'Gathering research, agent track records, measured risk and live data; the AI chair writes the memo (up to ~1 minute).')) + '</div></div>' : '') +
      (m && !S.busy ? memoHtml(m) : (!S.busy ? '<div class="cm-cell"><div class="cm-note">' + esc(S.entity ? L('Todavía no hay memo del comité para esta empresa. Pulsa «Correr comité». Consejo: primero corre 🔬 Investigación IA para que el comité tenga conclusiones.', 'No committee memo for this company yet. Press “Run committee”. Tip: run 🔬 AI research first so the committee has conclusions.') : L('Escribe una empresa y pulsa «Correr comité».', 'Type a company and press “Run committee”.')) + '</div>' +
        (S.entity && window.KhipuResearch ? '<div style="margin-top:8px"><button class="cm-btn ghost" onclick="window.KhipuResearch.open(\'' + esc(S.entity) + '\')">🔬 ' + esc(L('Investigación IA', 'AI research')) + '</button></div>' : '') + '</div>' : '')) +
      (S.history && S.history.length > 1 ? '<div class="cm-cell"><div class="cm-t">🗂 ' + esc(L('Memos anteriores', 'Previous memos')) + '</div>' +
        S.history.map(function (h) {
          var d = DEC[h.decision] || ['#9BA6C4', h.decision || '—', h.decision || '—'];
          var st = STATUS[h.status] || [h.status, h.status];
          return '<div class="cm-hist" data-id="' + esc(h.memo_id) + '"><b style="color:' + d[0] + '">' + esc(L(d[1], d[2])) + '</b> · ' + esc(clock(h.created_at)) + ' · ' + esc(L(st[0], st[1])) +
            (h.overall_conviction != null ? ' · ' + (h.overall_conviction > 0 ? '+' : '') + Math.round(h.overall_conviction) : '') + (h.ai_used ? '' : ' · ' + esc(L('sin IA', 'no AI'))) + (h.has_client ? ' · 👤' : '') + '</div>';
        }).join('') + '</div>' : '');
    var run = document.getElementById('cm-run'); if (run) run.onclick = runCommittee;
    var cli = document.getElementById('cm-cli'); if (cli) cli.onchange = function () { S.clientId = cli.value; };
    var lc = document.getElementById('cm-lc'); if (lc) lc.onclick = function () { loadClients(true); };
    body.querySelectorAll('.cm-hist').forEach(function (x) { x.onclick = function () { loadMemo(x.getAttribute('data-id')); }; });
    body.querySelectorAll('[data-ref]').forEach(function (x) { x.onclick = function () { openRef(x.getAttribute('data-ref')); }; });
    var ap = document.getElementById('cm-approve'); if (ap) ap.onclick = approve;
    var rj = document.getElementById('cm-reject'); if (rj) rj.onclick = reject;
  }

  function gauge(label, score, sub) {
    var v = Math.max(-100, Math.min(100, Number(score) || 0));
    var col = v > 0 ? '#2BE38B' : v < 0 ? '#FF4D6A' : '#9BA6C4';
    var w = Math.abs(v) / 2;
    var left = v >= 0 ? 50 : 50 - w;
    return '<div class="cm-g"><span style="min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + esc(label) + '">' + esc(label) + '</span>' +
      '<span class="cm-gt" title="' + esc(sub || '') + '"><b></b><i style="left:' + left + '%;width:' + w + '%;background:' + col + '"></i></span>' +
      '<span class="cm-gv">' + (v > 0 ? '+' : '') + Math.round(v) + '</span></div>' +
      (sub ? '<div class="cm-note" style="font-size:10.5px;margin:-3px 0 4px 0">' + esc(sub) + '</div>' : '');
  }

  function refs(arr) {
    return (arr || []).map(function (r) { return '<span class="cm-ref" data-ref="' + esc(r) + '">[' + esc(r) + ']</span>'; }).join('');
  }
  function openRef(ref) {
    var m = S.memo; if (!m) return;
    var cid = ((m.memo || {}).ref_map || {})[ref];
    if (cid && window.KhipuResearch) { window.KhipuResearch.open(m.entity_id); setTimeout(function () { window.KhipuResearch.why(cid); }, 400); }
  }

  function memoHtml(m) {
    if (m.status === 'running') return '';
    if (m.status === 'failed') return '<div class="cm-cell"><div class="cm-note" style="color:#FFB300">' + esc(L('El comité falló: ', 'The committee failed: ') + (T(m, 'error') || '')) + '</div></div>';
    var b = m.memo || {};
    var d = DEC[m.decision] || ['#9BA6C4', m.decision, m.decision];
    var st = STATUS[m.status] || [m.status, m.status];
    var sz = m.sizing || {};
    var conv = m.conviction || {};
    var summary = isEn() ? (b.summary_en || b.summary_es) : b.summary_es;
    var hzRows = HZ_ORDER.filter(function (h) { return conv[h]; }).map(function (h) {
      var r = conv[h];
      var sub = r.n_claims + ' ' + L('concl.', 'concl.') + ' (' + r.n_pos + ' ' + L('a favor', 'for') + ', ' + r.n_neg + ' ' + L('en contra', 'against') + ')' +
        (r.contra_share > 0 ? ' · −' + Math.round((1 - r.penalty) * 100) + '% ' + L('por contradicciones', 'for contradictions') : '') +
        (r.horizon_weight === 0 ? ' · ' + L('no pesa en la decisión', 'does not weigh in the decision') : '');
      return gauge(hz(h), r.score, sub);
    }).join('');
    var steps = (isEn() ? sz.steps_en : sz.steps_es) || [];
    var thesis = (b.thesis || []).map(function (t) { return '<li><b>' + esc(hz(t.horizon)) + ':</b> ' + esc(isEn() ? (t.thesis_en || t.thesis_es) : t.thesis_es) + refs(t.refs) + '</li>'; }).join('');
    var risks = (b.key_risks || []).map(function (r) { return '<li>' + esc(isEn() ? (r.risk_en || r.risk_es) : r.risk_es) + refs(r.refs) + '</li>'; }).join('');
    var diss = (b.dissent || []).map(function (x) { return '<li><b>' + esc(ag(x.agent_type)) + ':</b> ' + esc(isEn() ? (x.view_en || x.view_es) : x.view_es) + refs(x.refs) + '</li>'; }).join('');
    var fal = ((isEn() && b.falsifiers_en && b.falsifiers_en.length) ? b.falsifiers_en : (b.falsifiers_es || [])).map(function (f) { return '<li>' + esc(f) + '</li>'; }).join('');
    var note = isEn() ? (b.chair_note_en || b.chair_note_es) : b.chair_note_es;
    var cl = (m.inputs || {}).client;
    var pv = m.preview;
    var actionable = { BUY: 1, ADD: 1, TRIM: 1, SELL: 1 }[m.decision];
    return '' +
      '<div class="cm-cell">' +
        '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px">' +
          '<span class="cm-dec" style="color:' + d[0] + ';border-color:' + d[0] + '">' + esc(L(d[1], d[2])) + '</span>' + chip('committee_decision') +
          '<span style="font-weight:700;overflow-wrap:anywhere">' + esc(m.label || nodeLabel(m.entity_id)) + (m.symbol ? ' · ' + esc(m.symbol) : '') + '</span>' +
          '<span class="cm-pill">' + esc(L(st[0], st[1])) + '</span>' +
          '<span class="cm-pill">' + esc(m.ai_used ? L('presidente IA', 'AI chair') + (m.model ? ' · ' + m.model : '') : L('sin IA (plantilla determinista)', 'no AI (deterministic template)')) + '</span>' +
          (m.client_id ? '<span class="cm-pill">👤 ' + esc(cl ? (cl.name || m.client_id) : L('cliente (montos ocultos sin PIN)', 'client (amounts hidden without PIN)')) +
            ((m.client_mode || cl) ? ' · ' + esc(badge(m.client_mode || cl)) : '') + '</span>' : '') +
        '</div>' +
        '<div class="cm-note" style="font-size:13px;color:#E8EDFB">' + esc(summary || '') + '</div>' +
        (m.quant_decision && m.quant_decision !== m.decision ? '<div class="cm-note" style="margin-top:6px;color:#FFB300">' + esc(L('El núcleo cuantitativo proponía ', 'The quantitative core proposed ') + decLabel(m.quant_decision) + L('; el presidente rebajó a MANTENER: ', '; the chair downgraded to HOLD: ') + (note || '')) + '</div>' : '') +
        (b.quant_reason_es ? '<div class="cm-note" style="margin-top:6px;font-size:11px">' + esc(L('Regla aplicada: ', 'Rule applied: ') + (isEn() ? b.quant_reason_en : b.quant_reason_es)) + '</div>' : '') +
        (m.symbol && (m.inputs || {}).us_listing === false ? '<div class="cm-note" style="margin-top:4px;font-size:11px;color:#FFB300">' + esc(L('Cotiza fuera de EE.UU. (' + m.symbol + ', en moneda local): Alpaca no la opera, así que el comité no propone órdenes para clientes; su historial se califica en moneda local.', 'Trades outside the US (' + m.symbol + ', in local currency): Alpaca does not trade it, so the committee does not propose client orders; its track record is scored in local currency.')) + '</div>' : '') +
        (b.ai_error ? '<div class="cm-note" style="margin-top:4px;font-size:11px;color:#7C87A3">' + esc(L('Nota: ', 'Note: ') + T(b, 'ai_error')) + '</div>' : '') +
        '<div class="cm-note" style="margin-top:6px;font-size:11px;color:#7C87A3">' + esc(clock(m.created_at) + ' · ' + L('pedido por ', 'requested by ') + (m.requested_by || '—') + (m.expires_at ? ' · ' + L('vence ', 'expires ') + clock(m.expires_at) : '') + (m.expired ? ' · ' + L('VENCIDO: vuelve a correrlo', 'EXPIRED: run it again') : '')) + '</div>' +
      '</div>' +
      '<div class="cm-grid"><div style="min-width:0">' +
        '<div class="cm-cell"><div class="cm-t">🧭 ' + esc(L('Convicción por horizonte', 'Conviction by horizon')) + chip('conviction') + '</div>' +
          gauge(L('GLOBAL', 'OVERALL'), m.overall_conviction, null) + (hzRows || '<div class="cm-note">' + esc(L('Sin conclusiones activas.', 'No active conclusions.')) + '</div>') + '</div>' +
        (thesis ? '<div class="cm-cell"><div class="cm-t">📌 ' + esc(L('Tesis por horizonte', 'Thesis by horizon')) + '</div><ul class="cm-list">' + thesis + '</ul></div>' : '') +
        (risks ? '<div class="cm-cell"><div class="cm-t">⚠️ ' + esc(L('Riesgos clave', 'Key risks')) + '</div><ul class="cm-list">' + risks + '</ul></div>' : '') +
        '<div class="cm-cell"><div class="cm-t">🗣 ' + esc(L('Disenso (quién no está de acuerdo)', 'Dissent (who disagrees)')) + '</div>' + (diss ? '<ul class="cm-list">' + diss + '</ul>' : '<div class="cm-note">' + esc(L('Ningún agente se opone con fuerza a la decisión.', 'No agent strongly opposes the decision.')) + '</div>') + '</div>' +
        (fal ? '<div class="cm-cell"><div class="cm-t">🔎 ' + esc(L('Qué demostraría que estamos equivocados', 'What would prove us wrong')) + '</div><ul class="cm-list">' + fal + '</ul></div>' : '') +
      '</div><div style="min-width:0">' +
        '<div class="cm-cell"><div class="cm-t">📐 ' + esc(L('Tamaño propuesto (la cuenta)', 'Proposed size (the math)')) + chip('position_sizing') + '</div>' +
          '<div class="cm-kv"><span>' + esc(L('Peso objetivo', 'Target weight')) + '</span><span>' + (sz.target_weight_pct != null ? sz.target_weight_pct.toFixed(2) + '%' : '—') + '</span></div>' +
          (sz.reference_only ? '<div class="cm-kv"><span>' + esc(L('Por cada $10,000 (ilustrativo)', 'Per $10,000 (illustrative)')) + '</span><span>' + money(sz.per_10k) + '</span></div>'
            : '<div class="cm-kv"><span>' + esc(L('Orden', 'Order')) + '</span><span>' + (sz.side ? esc(sz.side.toUpperCase()) + ' ' + (sz.qty ? esc(sz.qty) + ' ' + L('acciones', 'shares') : money(sz.notional)) : '—') + '</span></div>' +
              (sz.qty_est ? '<div class="cm-kv"><span>' + esc(L('≈ acciones al precio en vivo', '≈ shares at live price')) + '</span><span>' + esc(sz.qty_est) + '</span></div>' : '') +
              (sz.current_weight_pct != null ? '<div class="cm-kv"><span>' + esc(L('Peso actual', 'Current weight')) + '</span><span>' + sz.current_weight_pct.toFixed(2) + '%</span></div>' : '')) +
          (steps.length ? '<ol class="cm-steps">' + steps.map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('') + '</ol>' : '') +
          '<div class="cm-note" style="font-size:10.5px;margin-top:6px">' + esc(L('El tamaño lo calcula una fórmula fija, nunca la IA.', 'The size comes from a fixed formula, never from the AI.')) + '</div></div>' +
        riskHtml(m) +
        '<div class="cm-cell"><div class="cm-t">🗓 ' + esc(L('Revisión y confianza', 'Review and confidence')) + '</div>' +
          '<div class="cm-kv"><span>' + esc(L('Revisar el', 'Review on')) + '</span><span>' + esc(day(b.review_date)) + '</span></div>' +
          '<div class="cm-kv"><span>' + esc(L('Confianza del comité', 'Committee confidence')) + chip('committee_confidence') + '</span><span>' + pct(b.confidence) + '</span></div>' +
          '<div class="cm-kv"><span>' + esc(L('Conclusiones usadas', 'Conclusions used')) + '</span><span>' + esc(((m.inputs || {}).n_claims) || 0) + '</span></div>' +
          '<div class="cm-kv"><span>' + esc(L('Contradicciones', 'Contradictions')) + '</span><span>' + esc(((m.inputs || {}).n_contradictions) || 0) + '</span></div>' +
          (window.KhipuResearch ? '<div style="margin-top:8px"><button class="cm-btn ghost" onclick="window.KhipuResearch.open(\'' + esc(m.entity_id) + '\')">🔬 ' + esc(L('Ver la investigación', 'See the research')) + '</button></div>' : '') +
        '</div>' +
        (pv ? previewHtml(pv, m) : '') +
        ((m.status === 'proposed' && !m.expired) || m.status === 'approved' ? '<div class="cm-cell"><div class="cm-t">✋ ' + esc(L('Tu decisión', 'Your decision')) + '</div>' +
          (m.status === 'proposed' ? '<div class="cm-note" style="margin-bottom:8px">' + (m.client_id && actionable && m.client_mode ? '<b>' + esc(badge(m.client_mode)) + '</b> · ' : '') + esc(m.client_id && actionable ? L('Aprobar prepara una orden (previsualización) para el cliente; la ejecución se confirma aparte en Clientes.', 'Approving prepares an order (preview) for the client; execution is confirmed separately in Clients.') : L('Aprobar registra la decisión; sin cliente no se prepara ninguna orden.', 'Approving records the decision; with no client no order is prepared.')) + '</div>'
            : '<div class="cm-note" style="margin-bottom:8px">' + esc(L('Rechazar ahora también retira la orden que espera aprobación en Clientes.', 'Rejecting now also withdraws the order awaiting approval in Clients.')) + '</div>') +
          '<div style="display:flex;gap:8px;flex-wrap:wrap">' + (m.status === 'proposed' ? '<button class="cm-btn ok" id="cm-approve"' + (S.deciding ? ' disabled' : '') + '>' + esc(S.deciding ? L('Procesando…', 'Working…') : '✅ ' + L('Aprobar', 'Approve')) + '</button>' : '') +
          '<button class="cm-btn no" id="cm-reject"' + (S.deciding ? ' disabled' : '') + '>✖ ' + esc(L('Rechazar', 'Reject')) + '</button></div></div>' : '') +
        (m.decided_by ? '<div class="cm-cell"><div class="cm-note">' + esc(L('Decidido por ', 'Decided by ') + m.decided_by + ' · ' + clock(m.decided_at) + (m.decision_note ? ' · «' + m.decision_note + '»' : '')) + '</div></div>' : '') +
      '</div></div>' +
      '<div class="cm-disc">⚖️ ' + esc(isEn() ? (m.disclaimer_en || '') : (m.disclaimer_es || '')) + '</div>';
  }

  function riskHtml(m) {
    var r = (m.inputs || {}).risk || {};
    var lv = (m.inputs || {}).live || {};
    if (!r.ok && !lv.ok) return '';
    return '<div class="cm-cell"><div class="cm-t">📉 ' + esc(L('Riesgo medido y datos en vivo', 'Measured risk and live data')) + '</div>' +
      (lv.ok && lv.price != null ? '<div class="cm-kv"><span>' + esc(L('Precio en vivo', 'Live price')) + '</span><span>' + esc(lv.price + ' ' + (lv.currency || '')) + '</span></div>' : '') +
      (lv.ok && lv.line ? '<div class="cm-note">' + esc(lv.line) + '</div>' : '') +
      (r.ok ? '<div class="cm-kv"><span>' + esc(L('Volatilidad anual', 'Annual volatility')) + '</span><span>' + esc(r.vol_ann_pct != null ? r.vol_ann_pct + '%' : '—') + '</span></div>' +
        '<div class="cm-kv"><span>' + esc(L('Máxima caída (1 año)', 'Max drawdown (1y)')) + '</span><span>' + esc(r.max_drawdown_pct != null ? r.max_drawdown_pct + '%' : '—') + '</span></div>' +
        '<div class="cm-kv"><span>' + esc(L('Beta vs S&P 500', 'Beta vs S&P 500')) + '</span><span>' + esc(r.beta_spy != null ? r.beta_spy : '—') + '</span></div>' +
        '<div class="cm-note" style="font-size:10.5px;margin-top:4px">' + esc((r.source || '') + (r.as_of ? ' · ' + r.as_of : '')) + '</div>'
        : '<div class="cm-note">' + esc(L('Sin riesgo medido: ', 'No measured risk: ') + (T(r, 'error') || '')) + '</div>') + '</div>';
  }

  var PV_DEAD = { rejected: 1, expired: 1, failed: 1, canceled: 1 };
  var PV_SENT = { approved: 1, submitted: 1, filled: 1, partially_filled: 1, accepted: 1, 'new': 1 };
  function pvFailed(pv) { return !pv || !pv.ok || pv.blocked || !!PV_DEAD[pv.status]; }
  function pvChecks(pv) {
    return (pv.checks || []).filter(function (c) { return !c.ok; }).map(function (c) {
      return '<div class="cm-kv"><span>⛔ ' + esc(c.name) + '</span><span style="white-space:normal">' + esc(isEn() ? (c.detail_en || c.detail || '') : (c.detail || '')) + '</span></div>'; }).join('');
  }
  var PV_ST = { pending_approval: ['esperando tu aprobación final en Clientes', 'awaiting your final approval in Clients'],
    previewed: ['previsualizada (caduca en 5 min)', 'previewed (expires in 5 min)'], rejected: ['rechazada / bloqueada', 'rejected / blocked'],
    expired: ['vencida', 'expired'], failed: ['falló', 'failed'], canceled: ['cancelada', 'canceled'], submitted: ['enviada al bróker', 'sent to the broker'],
    filled: ['ejecutada', 'filled'], partially_filled: ['ejecutada en parte', 'partially filled'], approved: ['aprobada', 'approved'] };
  function pvStatus(st) { var x = PV_ST[st]; return x ? L(x[0], x[1]) : (st || '—'); }

  function previewHtml(pv, m) {
    var bad = pvFailed(pv);
    var summary = isEn() ? (pv.summary_en || pv.summary_es || '') : (pv.summary_es || '');
    var goClients = window.KhipuClients && window.KhipuClients.open ? '<div style="margin-top:8px"><button class="cm-btn ghost" onclick="window.KhipuCommittee.close();window.KhipuClients.open()">👥 ' + esc(L('Ir a Clientes', 'Go to Clients')) + '</button></div>' : '';
    var head = '<div class="cm-cell" style="border-color:' + (bad ? 'rgba(255,179,0,.45)' : 'rgba(43,227,139,.4)') + '"><div class="cm-t">🧾 ' +
      esc(bad ? L('Orden NO preparada', 'Order NOT prepared') : L('Orden preparada', 'Prepared order')) + (pv.mode || (m && m.client_mode) ? ' · ' + esc(badge(pv.mode ? { mode: pv.mode } : m.client_mode)) : '') + '</div>';
    if (pv.redacted) {
      return head + '<div class="cm-kv"><span>' + esc(L('Estado', 'Status')) + '</span><span>' + esc(pvStatus(pv.status)) + '</span></div>' +
        '<div class="cm-note">' + esc(L('Detalle y montos visibles con tu PIN.', 'Details and amounts visible with your PIN.')) + '</div></div>';
    }
    if (bad) {
      return head + '<div class="cm-note" style="color:#FFB300">' + esc(T(pv, 'error') || summary || L('No se pudo preparar la orden.', 'Could not prepare the order.')) + '</div>' + pvChecks(pv) +
        (m && m.status === 'proposed' ? '<div class="cm-note" style="margin-top:6px">' + esc(L('El memo sigue propuesto: corrige el límite o el problema y vuelve a aprobar, o recházalo.', 'The memo is still proposed: fix the limit or the problem and approve again, or reject it.')) + '</div>' : '') + '</div>';
    }
    var note = pv.status === 'pending_approval' ? L('Falta tu aprobación final en 👥 Clientes → Aprobaciones para ejecutarla.', 'Your final approval in 👥 Clients → Approvals is still needed to execute it.')
      : pv.status === 'previewed' ? L('Previsualizada: se confirma en Clientes dentro de 5 minutos o caduca.', 'Previewed: confirm it in Clients within 5 minutes or it expires.')
      : PV_SENT[pv.status] ? L('Orden enviada al bróker.', 'Order sent to the broker.') : '';
    return head + '<div class="cm-note">' + esc(summary) + '</div>' +
      '<div class="cm-kv"><span>' + esc(L('Estado', 'Status')) + '</span><span>' + esc(pvStatus(pv.status)) + '</span></div>' +
      (pv.checks || []).map(function (c) { return '<div class="cm-kv"><span>' + (c.ok ? (c.warn ? '⚠️ ' : '✅ ') : '⛔ ') + esc(c.name) + '</span><span style="white-space:normal">' + esc(isEn() ? (c.detail_en || c.detail || '') : (c.detail || '')) + '</span></div>'; }).join('') +
      (note ? '<div class="cm-note" style="margin-top:6px;color:' + (pv.status === 'pending_approval' || pv.status === 'previewed' ? '#FFB300' : '#2BE38B') + '">' + esc(note) + '</div>' : '') +
      (pv.status === 'pending_approval' || pv.status === 'previewed' ? goClients : '') + '</div>';
  }

  // ── acciones ───────────────────────────────────────────────────────────────
  function loadClients(interactive) {
    return pinJSON('/api/committee/clients', {}, interactive).then(function (d) {
      if (d._status === 200) {
        S.clients = d.clients || []; S.clientsErr = d.available ? null : L('Módulo de clientes no disponible: el comité corre sin cliente.', 'Clients module not available: the committee runs without a client.');
      } else if (interactive) { S.clientsErr = errText(d); }
      if (S.tab === 'committee') render();
    }).catch(function () {});
  }

  function loadEntity(eid) {
    return pinJSON('/api/committee/entity/' + encodeURIComponent(eid), {}, false).then(function (d) {
      if (d._status !== 200) { S.memo = null; S.history = []; if (d._status === 503) S.msg = { bad: true, text: errText(d) }; render(); return; }
      S.entity = d.entity_id || eid; S.memo = d.latest; S.history = d.history || []; render();
    }).catch(function () { render(); });
  }

  function loadMemo(id) {
    return pinJSON('/api/committee/memo/' + encodeURIComponent(id), {}, false).then(function (d) {
      if (d.memo_id) { S.memo = d; S.entity = d.entity_id; }
      return d;
    });
  }

  function startPoll(mid) {
    S.running = { memo_id: mid, entity: S.entity }; S.busy = true;
    var n = 0;
    if (S.poll) clearInterval(S.poll);
    S.poll = setInterval(function () {
      n++;
      loadMemo(mid).then(function (m) {
        if (!S.running || S.running.memo_id !== mid) return;
        if (m.status && m.status !== 'running') {
          clearInterval(S.poll); S.poll = null; S.busy = false; S.running = null;
          if (m.status === 'failed') S.msg = { bad: true, text: L('El comité falló: ', 'The committee failed: ') + (T(m, 'error') || '') };
          loadEntity(S.entity);
        } else if (n > 60) {
          clearInterval(S.poll); S.poll = null; S.busy = false; S.running = null;
          S.msg = { bad: true, text: L('El comité tarda más de lo normal. Vuelve a abrir esta ventana en un minuto.', 'The committee is taking longer than usual. Reopen this window in a minute.') }; render();
        }
      }).catch(function () {});
    }, 2000);
  }

  function runCommittee() {
    var inp = document.getElementById('cm-ent');
    var q = (inp && inp.value || '').trim();
    if (!q) { S.msg = { bad: true, text: L('Escribe una empresa.', 'Type a company.') }; render(); return; }
    var sel = document.getElementById('cm-cli'); S.clientId = sel ? sel.value : '';
    var ent = (S.entity && q === nodeLabel(S.entity)) ? S.entity : q;
    var body = { entity: ent, actor: actor() };
    if (S.clientId) body.client_id = S.clientId;
    S.busy = true; S.msg = null; S.memo = null; render();
    var opts = { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
    (S.clientId ? pinJSON('/api/committee/run', opts, true) : getJSON('/api/committee/run', opts)).then(function (d) {
      if (!d.memo_id) { S.busy = false; S.msg = { bad: true, text: errText(d) }; render(); return; }
      S.entity = d.entity_id || S.entity;
      if (d.reused) S.msg = { bad: false, text: L('Ya había un comité reciente para esta empresa: se muestra ese (no se gasta IA dos veces).', 'There was already a recent committee for this company: showing it (no double AI spend).') };
      if (d.status && d.status !== 'running') { S.busy = false; loadEntity(S.entity); return; }
      startPoll(d.memo_id);
    }).catch(function () { S.busy = false; S.msg = { bad: true, text: L('Sin conexión con el servidor.', 'No connection to the server.') }; render(); });
  }

  function decideMemo(kind) {
    var m = S.memo; if (!m || S.deciding) return;
    var sz = m.sizing || {};
    var body = { actor: actor() };
    if (kind === 'approve') {
      var what = decLabel(m.decision) + ' ' + (m.symbol || '') +
        (sz.side && !sz.reference_only && (sz.notional || sz.qty) ? ' · ' + (sz.qty ? sz.qty + ' ' + L('acciones', 'shares') : money(sz.notional)) : '');
      var mode = m.client_id ? '\n' + (m.client_mode ? badge(m.client_mode) : L('Modo de la cuenta: se muestra en Clientes', 'Account mode: shown in Clients')) : '';
      if (!window.confirm(L('¿Aprobar la propuesta del comité?\n\n', 'Approve the committee proposal?\n\n') + what + mode + '\n\n' +
        (m.client_id ? L('Se preparará una orden que TAMBIÉN tendrás que aprobar en Clientes antes de ejecutarse (salvo que el servidor tenga activada la auto-aprobación de cuentas SIMULADAS).', 'An order will be prepared that you will ALSO have to approve in Clients before it executes (unless the server has auto-approval of PAPER accounts turned on).') : L('Sin cliente: solo se registra tu aprobación.', 'No client: only your approval is recorded.')))) return;
    } else {
      var why = window.prompt(L('¿Por qué la rechazas? (opcional)', 'Why do you reject it? (optional)'), '');
      if (why === null) return;
      body.reason = why;
    }
    S.deciding = true; render();
    pinJSON('/api/committee/memo/' + encodeURIComponent(m.memo_id) + '/' + kind, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }, true).then(function (d) {
      S.deciding = false;
      if (d._status !== 200 || !d.ok) { S.msg = { bad: true, text: errText(d) }; if (d.memo) S.memo = d.memo; render(); return; }
      S.memo = d.memo;
      var pv = d.preview, text;
      if (kind !== 'approve') text = L('Rechazado y registrado.', 'Rejected and recorded.') + (d.withdrawn && d.withdrawn.ok ? ' ' + L('La orden pendiente en Clientes se retiró.', 'The pending order in Clients was withdrawn.') : '');
      else if (!pv) text = T(d, 'note') || L('Aprobado y registrado.', 'Approved and recorded.');
      else if (d.executed || PV_SENT[pv.status]) text = L('Aprobado y orden ENVIADA al bróker', 'Approved and order SENT to the broker') + (S.memo && S.memo.client_mode ? ' (' + badge(S.memo.client_mode) + ')' : '') + '.';
      else if (pv.status === 'pending_approval') text = L('Aprobado. Orden preparada: falta tu aprobación final en Clientes → Aprobaciones.', 'Approved. Order prepared: your final approval in Clients → Approvals is still needed.');
      else if (pv.status === 'previewed') text = L('Aprobado. Orden previsualizada: confírmala en Clientes dentro de 5 minutos.', 'Approved. Order previewed: confirm it in Clients within 5 minutes.');
      else text = L('Aprobado.', 'Approved.');
      S.msg = { bad: false, text: text };
      loadEntity(S.entity);
    }).catch(function () { S.deciding = false; S.msg = { bad: true, text: L('Sin conexión con el servidor.', 'No connection to the server.') }; render(); });
  }
  function approve() { decideMemo('approve'); }
  function reject() { decideMemo('reject'); }

  // ── pestaña Historial ─────────────────────────────────────────────────────
  function renderHistory(body) {
    body.innerHTML = '<div class="cm-cell"><div class="cm-note">…</div></div>';
    Promise.all([getJSON('/api/committee/track-record'), getJSON('/api/committee/outcomes/recent?limit=15')]).then(function (res) {
      S.tr = res[0]; S.recent = res[1];
      if (S.tab !== 'history') return;
      drawHistory(body);
    }).catch(function () { body.innerHTML = '<div class="cm-cell"><div class="cm-note">' + esc(L('Sin conexión con el servidor.', 'No connection to the server.')) + '</div></div>'; });
  }

  function drawHistory(body) {
    var tr = S.tr || {};
    if (tr._status && tr._status !== 200) { body.innerHTML = '<div class="cm-cell"><div class="cm-note">' + esc(errText(tr)) + '</div></div>'; return; }
    var agents = tr.agents || [];
    var ov = tr.overall || {};
    var minN = tr.min_n || 5;
    var rows = agents.map(function (a) {
      var enough = a.n_scored >= minN;
      return '<tr><td>' + esc(ag(a.agent_type)) + '</td><td>' + a.n_scored + '</td><td>' + a.hits + '</td>' +
        '<td>' + (enough ? pct(a.hit_rate) : '<span style="color:#7C87A3">' + (a.n_scored ? pct(a.hit_rate) + ' · ' : '') + esc(L('poca historia', 'little history')) + '</span>') + '</td>' +
        '<td>' + (a.brier == null ? '—' : a.brier.toFixed(3)) + '</td><td>' + pct(a.reliability) + '</td>' +
        '<td>' + (a.interim && a.interim.n_scored ? pct(a.interim.hit_rate) + ' (n=' + a.interim.n_scored + ')' : '—') + '</td><td>' + (a.n_na || 0) + '</td></tr>';
    }).join('');
    var sel = '<select id="cm-agsel"><option value="__all">' + esc(L('Todos los agentes', 'All agents')) + '</option>' +
      agents.map(function (a) { return '<option value="' + esc(a.agent_type) + '"' + (S.agentSel === a.agent_type ? ' selected' : '') + '>' + esc(ag(a.agent_type)) + '</option>'; }).join('') + '</select>';
    var recent = ((S.recent || {}).outcomes || []).map(function (o) {
      var r = RES[o.result] || RES['n/a'];
      return '<div class="cm-hist" style="cursor:default"><b style="color:' + r[0] + '">' + esc(L(r[1], r[2])) + '</b> · ' + esc(nodeLabel(o.entity_id)) + ' · ' + esc(ag(o.agent_type)) + ' · ' + esc(hz(o.horizon)) + ' · ' + esc(o.checkpoint) +
        '<div style="color:#7C87A3;white-space:normal;overflow-wrap:anywhere">' + esc(T(o, 'reason') || '') + '</div></div>';
    }).join('');
    body.innerHTML =
      '<div class="cm-cell"><div class="cm-t">🎯 ' + esc(L('Historial real de los agentes', 'Agents\' real track record')) + chip('hit_rate') + chip('brier') + '</div>' +
        '<div class="cm-note" style="margin-bottom:8px">' + esc(L('Solo predicciones YA vencidas y calificadas con precios reales contra el S&P 500 (banda ±', 'Only predictions ALREADY due, scored with real prices against the S&P 500 (band ±') + ((tr.band || 0.02) * 100).toFixed(0) + '%). ' +
          L('Global: ', 'Overall: ') + (ov.n_scored || 0) + L(' calificadas', ' scored') + (ov.n_scored ? ' · ' + L('acierto ', 'hit rate ') + pct(ov.hit_rate) + ' · Brier ' + (ov.brier == null ? '—' : ov.brier.toFixed(3)) : '') +
          (ov.n_scored < minN ? ' · ' + L('todavía sin historial suficiente (se necesitan ≥ ', 'not enough history yet (needs ≥ ') + minN + ')' : '')) + '</div>' +
        (rows ? '<div class="cm-tw"><table><thead><tr><th>' + esc(L('Agente', 'Agent')) + '</th><th>n</th><th>' + esc(L('Aciertos', 'Hits')) + '</th><th>' + esc(L('Tasa', 'Rate')) + '</th><th>Brier' + chip('brier') + '</th><th>' + esc(L('Fiabilidad', 'Reliability')) + chip('reliability') + '</th><th>' + esc(L('Señal temprana', 'Early signal')) + chip('early_signal') + '</th><th>n/a</th></tr></thead><tbody>' + rows + '</tbody></table></div>'
          : '<div class="cm-note">' + esc(L('Todavía no vence ninguna predicción. Las de corto plazo se califican a los 7 y 30 días; las de largo plazo, a los 90, 180 y 365 días.', 'No prediction is due yet. Short-term ones are scored at 7 and 30 days; long-term ones at 90, 180 and 365 days.')) + '</div>') +
        '<div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap"><button class="cm-btn ghost" id="cm-eval">⟳ ' + esc(L('Calificar vencidas ahora (PIN)', 'Score due ones now (PIN)')) + '</button></div>' +
      '</div>' +
      '<div class="cm-grid"><div class="cm-cell" style="min-width:0"><div class="cm-t">📈 ' + esc(L('Curva de calibración', 'Calibration curve')) + chip('calibration') + '</div>' +
        '<div style="margin-bottom:8px">' + sel + '</div><div id="cm-calwrap" style="position:relative;height:230px"></div>' +
        '<div class="cm-note" style="font-size:11px;margin-top:6px">' + esc(L('Si los puntos quedan sobre la línea gris, la confianza declarada fue honesta. Debajo = exceso de confianza; encima = demasiado prudente.', 'If points sit on the gray line, stated confidence was honest. Below = overconfident; above = too cautious.')) + '</div></div>' +
        '<div class="cm-cell" style="min-width:0"><div class="cm-t">🧾 ' + esc(L('Últimas calificaciones', 'Latest scores')) + '</div>' + (recent || '<div class="cm-note">' + esc(L('Sin calificaciones todavía.', 'No scores yet.')) + '</div>') + '</div></div>';
    var s = document.getElementById('cm-agsel'); if (s) s.onchange = function () { S.agentSel = s.value; drawCal(); };
    var ev = document.getElementById('cm-eval'); if (ev) ev.onclick = evaluateNow;
    drawCal();
  }

  function drawCal() {
    var wrap = document.getElementById('cm-calwrap'); if (!wrap) return;
    if (S.chart) { try { S.chart.destroy(); } catch (e) {} S.chart = null; }
    var tr = S.tr || {};
    var src = S.agentSel === '__all' ? tr.overall : (tr.agents || []).filter(function (a) { return a.agent_type === S.agentSel; })[0];
    var buckets = ((src || {}).calibration || []).filter(function (b) { return b.n > 0; });
    if (!buckets.length) { wrap.style.height = 'auto'; wrap.innerHTML = '<div class="cm-note">' + esc(L('Sin predicciones finales calificadas todavía: la curva aparece cuando venzan.', 'No final predictions scored yet: the curve appears when they come due.')) + '</div>'; return; }
    var tbl = '<table style="margin-top:6px"><thead><tr><th>' + esc(L('Tramo', 'Bucket')) + '</th><th>n</th><th>' + esc(L('Conf. media', 'Mean conf.')) + '</th><th>' + esc(L('Acierto real', 'Actual hit rate')) + '</th></tr></thead><tbody>' +
      buckets.map(function (b) { return '<tr><td>' + esc(b.bucket) + '</td><td>' + b.n + '</td><td>' + pct(b.mean_conf) + '</td><td>' + pct(b.hit_rate) + '</td></tr>'; }).join('') + '</tbody></table>';
    if (!window.Chart) { wrap.style.height = 'auto'; wrap.innerHTML = '<div class="cm-tw">' + tbl + '</div>'; return; }
    wrap.style.height = '230px';
    wrap.innerHTML = '<canvas id="cm-cal" aria-label="' + esc(L('Curva de calibración', 'Calibration curve')) + '"></canvas>';
    var grid = 'rgba(122,158,255,.08)', ink = '#7C87A3';
    try {
      S.chart = new window.Chart(document.getElementById('cm-cal').getContext('2d'), {
        type: 'scatter',
        data: { datasets: [
          { label: L('Acierto real por tramo', 'Actual hit rate by bucket'), data: buckets.map(function (b) { return { x: Math.round(b.mean_conf * 1000) / 10, y: Math.round(b.hit_rate * 1000) / 10, n: b.n }; }),
            showLine: true, borderColor: '#00E0FF', backgroundColor: '#00E0FF', borderWidth: 2, pointRadius: 5, pointHoverRadius: 7, pointBorderColor: '#06090F', pointBorderWidth: 2 },
          { label: L('Calibración perfecta', 'Perfect calibration'), data: [{ x: 0, y: 0 }, { x: 100, y: 100 }], showLine: true, borderColor: 'rgba(155,166,196,.55)', borderWidth: 1, pointRadius: 0, pointHoverRadius: 0 }] },
        options: { responsive: true, maintainAspectRatio: false, animation: false,
          scales: { x: { min: 0, max: 100, title: { display: true, text: L('Confianza declarada (%)', 'Stated confidence (%)'), color: ink }, grid: { color: grid }, ticks: { color: ink } },
            y: { min: 0, max: 100, title: { display: true, text: L('Acierto real (%)', 'Actual hit rate (%)'), color: ink }, grid: { color: grid }, ticks: { color: ink } } },
          plugins: { legend: { labels: { color: '#9BA6C4', boxWidth: 10, font: { size: 11 } } },
            tooltip: { filter: function (it) { return it.datasetIndex === 0; }, callbacks: { label: function (c) { var p = c.raw || {}; return L('confianza ', 'confidence ') + p.x + '% → ' + L('acierto ', 'hit rate ') + p.y + '% (n=' + p.n + ')'; } } } } } });
    } catch (e) { wrap.style.height = 'auto'; wrap.innerHTML = '<div class="cm-tw">' + tbl + '</div>'; }
  }

  function evaluateNow() {
    pinJSON('/api/committee/outcomes/evaluate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }, true).then(function (d) {
      if (d._status !== 200) { S.msg = { bad: true, text: errText(d) }; render(); return; }
      S.msg = { bad: false, text: L('Calificadas: ', 'Scored: ') + (d.evaluated || 0) + ' (' + (d.hits || 0) + L(' aciertos, ', ' hits, ') + (d.misses || 0) + L(' fallos, ', ' misses, ') + (d.n_a || 0) + ' n/a) · ' + L('pendientes: ', 'pending: ') + (d.pending || 0) };
      render();
    }).catch(function () { S.msg = { bad: true, text: L('Sin conexión con el servidor.', 'No connection to the server.') }; render(); });
  }

  // ── pestaña Cómo aprende ──────────────────────────────────────────────────
  function renderLearn(body) {
    var P = function (es, en) { return '<p>' + L(es, en) + '</p>'; };
    body.innerHTML = '<div class="cm-cell cm-learn">' +
      '<h4>1 · ' + esc(L('Los agentes investigan (Fase 2)', 'Agents research (Phase 2)')) + '</h4>' +
      P('Cada agente (fundamental, noticias, técnico, cadena de suministro…) escribe conclusiones con evidencia, un plazo y una confianza calculada. Nunca dicen "compra" o "vende".',
        'Each agent (fundamental, news, technical, supply chain…) writes conclusions with evidence, a horizon and a computed confidence. They never say "buy" or "sell".') +
      '<h4>2 · ' + esc(L('Se guarda una foto del momento', 'A snapshot of the moment is saved')) + '</h4>' +
      P('Al escribir cada conclusión se anota el precio de la acción y del S&P 500 (SPY) y las fechas en que se va a revisar: a 7 y 30 días si es de corto plazo, a 30, 90 y 180 días si es de mediano, a 90, 180 y 365 días si es de largo. Las "estructurales" (más de 5 años) no se califican.',
        'When each conclusion is written, the stock and S&P 500 (SPY) prices are recorded along with the dates it will be checked: 7 and 30 days for short term, 30, 90 and 180 days for medium term, 90, 180 and 365 days for long term. "Structural" ones (over 5 years) are not scored.') +
      '<h4>3 · ' + esc(L('Se califica con precios reales', 'It is scored with real prices')) + chip('hit_rate') + '</h4>' +
      P('Una vez al día el sistema revisa las fechas vencidas: compara cuánto se movió la acción contra el mercado. Si el agente dijo "positivo" y la acción le ganó al mercado por más de 2 %, es un acierto. Nada de IA en este paso: solo precios. Cada calificación queda guardada y no se borra.',
        'Once a day the system checks due dates: it compares how much the stock moved versus the market. If the agent said "positive" and the stock beat the market by more than 2%, it is a hit. No AI in this step: only prices. Every score is stored and never deleted.') +
      '<h4>4 · ' + esc(L('La confianza se corrige (calibración)', 'Confidence gets corrected (calibration)')) + chip('calibration') + chip('brier') + '</h4>' +
      P('Si un agente dice 80 % de confianza pero acierta solo la mitad de las veces, sus próximas conclusiones de ~80 % valen menos. Con pocos casos casi no se corrige: hace falta historia para aprender.',
        'If an agent says 80% confidence but is right only half the time, its next ~80% conclusions count for less. With few cases it barely corrects: learning needs history.') +
      '<h4>5 · ' + esc(L('El comité decide… y tú apruebas', 'The committee decides… and you approve')) + chip('conviction') + chip('position_sizing') + chip('committee_decision') + '</h4>' +
      P('El comité suma las conclusiones pesadas por su confianza calibrada y por el historial de cada agente, descuenta las contradicciones, mide el riesgo real de la acción y calcula un tamaño con una fórmula fija. Un presidente IA escribe el memo (tesis, riesgos, quién disiente, qué nos demostraría equivocados), pero no puede cambiar el tamaño ni inventar cifras. Nada se ejecuta sin tu aprobación, y para dinero de clientes hay una segunda aprobación en Clientes.',
        'The committee adds up conclusions weighted by calibrated confidence and each agent\'s track record, discounts contradictions, measures the stock\'s real risk and computes a size with a fixed formula. An AI chair writes the memo (thesis, risks, who dissents, what would prove us wrong), but it cannot change the size or invent figures. Nothing executes without your approval, and client money needs a second approval in Clients.') +
      '<div class="cm-disc" style="margin-top:12px">⚖️ ' + esc(L('Es una herramienta de apoyo: puede equivocarse y no es asesoría financiera personalizada.', 'It is a support tool: it can be wrong and it is not personalized financial advice.')) + '</div></div>';
  }

  // ── API pública ───────────────────────────────────────────────────────────
  function open(entityId) {
    ensureExplain();
    // Investigación IA (z-index 7700) tapaba al comité (7650): se cierra al abrirlo.
    // «Ver la investigación» / [C#] la vuelven a abrir ENCIMA (y al cerrarla se vuelve aquí).
    var rov = document.getElementById('rs-ov');
    if (rov && rov.classList.contains('show') && window.KhipuResearch && window.KhipuResearch.close) window.KhipuResearch.close();
    var ov = shell(); ov.classList.add('show');
    S.tab = 'committee'; S.msg = null; S.memo = null; S.history = []; S.deciding = false;
    if (S.running && entityId && S.running.entity && entityId !== S.running.entity) {
      S.running = null; S.busy = false;                 // otra empresa: el comité anterior sigue en el servidor
    }
    if (entityId) S.entity = entityId;
    if (S.running) { S.entity = S.running.entity || S.entity; startPoll(S.running.memo_id); } else { S.busy = false; }
    render();
    if (S.clients === null) {
      var hasPin = !!(window._tradePinStored && window._tradePinStored());   // PIN vigente (12 h, app.html)
      if (hasPin) loadClients(false);
    }
    if (S.entity) loadEntity(S.entity);
  }

  window.KhipuCommittee = { open: open, close: close };
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { var ov = document.getElementById('cm-ov'); if (ov && ov.classList.contains('show')) close(); } });
})();
