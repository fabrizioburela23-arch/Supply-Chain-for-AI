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
  // Colores SEMÁNTICOS: solo tokens de Khipus OS (definidos sobre #cm-ov en ensureStyles; claro/oscuro
  // los pone body.dark). Valen dentro de style="" pero NO en atributos de presentación SVG.
  // C.* son colores de TEXTO: --cm-good/--cm-bad/--cm-warn/--cm-ai llegan a 4.5:1 (WCAG AA) también sobre su
  // píldora teñida en el tema claro; los vivos (--os-good, --os-bad, --cm-warn-fill) quedan para rellenos,
  // barras y anillos (fill()).
  var C = { good: 'var(--cm-good)', bad: 'var(--cm-bad)', neu: 'var(--os-ink-2)', mute: 'var(--os-ink-3)', warn: 'var(--cm-warn)',
    accent: 'var(--os-accent)', ai: 'var(--cm-ai)', ink: 'var(--os-ink)' };
  var FILL = { 'var(--cm-good)': 'var(--os-good)', 'var(--cm-bad)': 'var(--os-bad)', 'var(--cm-warn)': 'var(--cm-warn-fill)' };
  function fill(col) { return FILL[col] || col; }
  // texto en color + fondo teñido suave (la "píldora" de Khipus OS); sin color-mix queda el fondo neutro
  function tint(col, p) { return 'color:' + col + ';background:var(--os-surface-2);background:color-mix(in srgb,' + fill(col) + ' ' + (p || 12) + '%,transparent)'; }

  // ── AGENTES = MASCOTAS de Khipus OS (engine/mascot.js). Cada puesto del comité pertenece a una
  // mascota (Analista, Radar, Cadena, Técnico, Comité) y lleva una insignia con su rol. ──
  var SEAT_MASCOT = { fundamental: 'analista', macro: 'analista', news: 'radar', geopolitical: 'radar', crypto: 'radar',
    supply_chain: 'cadena', technical: 'tecnico', risk_observation: 'tecnico', risk_officer: 'tecnico', market: 'tecnico',
    chair: 'comite', quant: 'comite', mandate: 'comite', committee: 'comite' };
  var MNAME = { analista: ['Analista', 'Analyst'], radar: ['Radar', 'Radar'], cadena: ['Cadena', 'Chain'], tecnico: ['Técnico', 'Technical'],
    comite: ['Comité', 'Committee'], khipu: ['Khipu', 'Khipu'] };
  var MCOLOR = { analista: '#4054cf', radar: '#e63e52', cadena: '#1b9386', tecnico: '#e6a117', comite: '#7a3fe0', khipu: '#c23a8c' };
  var ROLE = { fundamental: ['Fundamental', 'Fundamental'], macro: ['Macro', 'Macro'], news: ['Noticias', 'News'], geopolitical: ['Geopolítica', 'Geopolitics'],
    crypto: ['Cripto', 'Crypto'], supply_chain: ['Suministro', 'Supply'], technical: ['Precio', 'Price'], risk_observation: ['Riesgos', 'Risks'],
    market: ['Mesa de mercado', 'Market desk'], risk_officer: ['Oficial de riesgo', 'Risk officer'], quant: ['Cuantitativo', 'Quant'],
    chair: ['Presidencia', 'Chair'], mandate: ['Mandato', 'Mandate'] };
  var EMO = { market: '📡', risk_officer: '🛡️', quant: '🧮', chair: '🏛', mandate: '👤' };
  function mascotOf(seat) {
    var id = null;
    try { id = (window.KhipuMascot && window.KhipuMascot.of) ? window.KhipuMascot.of(seat) : null; } catch (e) { id = null; }
    return id || SEAT_MASCOT[seat] || 'comite';
  }
  function mascotName(id) {
    try { if (window.KhipuMascot && window.KhipuMascot.name && MNAME[id]) return window.KhipuMascot.name(id); } catch (e) {}
    var x = MNAME[id]; return x ? L(x[0], x[1]) : String(id || '');
  }
  function mascotColor(id) {
    var c = null;
    try { c = (window.KhipuMascot && window.KhipuMascot.color) ? window.KhipuMascot.color(id) : null; } catch (e) { c = null; }
    return /^#[0-9a-f]{3,8}$/i.test(c || '') ? c : (MCOLOR[id] || '#8D90A0');
  }
  function roleOf(seat, fallback) { var r = ROLE[seat]; return r ? L(r[0], r[1]) : (fallback || ''); }
  // "Analista · Fundamental" / "Técnico · Oficial de riesgo"; un puesto nuevo del servidor usa su propio nombre como rol
  function seatLabel(seat, fallback) {
    var role = roleOf(seat, fallback ? shortName(fallback) : '');
    var n = mascotName(mascotOf(seat));
    return role && role !== n ? n + ' · ' + role : n;
  }
  function ag(t) { return seatLabel(t, AG[t] ? L(AG[t][1], AG[t][2]) : t); }
  var HZ = { INTRADAY: ['Intradía', 'Intraday'], SHORT_TERM: ['Corto plazo', 'Short term'], MEDIUM_TERM: ['Mediano plazo', 'Medium term'],
    LONG_TERM: ['Largo plazo', 'Long term'], STRUCTURAL: ['Estructural', 'Structural'] };
  function hz(h) { var x = HZ[h] || [h, h]; return L(x[0], x[1]); }
  var HZ_ORDER = ['SHORT_TERM', 'MEDIUM_TERM', 'LONG_TERM', 'STRUCTURAL', 'INTRADAY'];
  var DEC = { BUY: [C.good, 'COMPRAR', 'BUY'], ADD: [C.good, 'AUMENTAR', 'ADD'], HOLD: [C.neu, 'MANTENER / ESPERAR', 'HOLD / WAIT'],
    TRIM: [C.warn, 'REDUCIR', 'TRIM'], SELL: [C.bad, 'VENDER', 'SELL'], AVOID: [C.bad, 'EVITAR', 'AVOID'] };
  var STATUS = { running: ['deliberando…', 'deliberating…'], failed: ['falló', 'failed'], proposed: ['propuesta (pendiente de aprobación)', 'proposal (awaiting approval)'],
    approved: ['aprobada por un humano', 'approved by a human'], rejected: ['rechazada', 'rejected'], executed: ['ejecutada', 'executed'] };
  var RES = { hit: [C.good, 'acierto', 'hit'], miss: [C.bad, 'fallo', 'miss'], 'n/a': [C.mute, 'n/a', 'n/a'] };

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
      es: { t: 'Decisión del comité', b: '<b>COMPRAR</b> (abrir) si la convicción global es ≥ +35 · <b>AUMENTAR</b> si ya tienes y estás bajo tu tamaño objetivo · <b>MANTENER / ESPERAR</b> si no alcanza · <b>REDUCIR</b> si baja de −20 o tu posición pasó el 125 % del objetivo · <b>VENDER</b> si baja de −50 · <b>EVITAR</b> si no la tienes y es negativa (o no cotiza). La presidencia IA del Comité puede rebajar a MANTENER explicando por qué, nunca subir. Es una PROPUESTA: nada se ejecuta sin tu aprobación, y no es asesoría personalizada.' },
      en: { t: 'Committee decision', b: '<b>BUY</b> (open) if overall conviction is ≥ +35 · <b>ADD</b> if you already hold it and are below your target size · <b>HOLD / WAIT</b> if it does not reach that · <b>TRIM</b> if it falls below −20 or your position exceeds 125% of target · <b>SELL</b> below −50 · <b>AVOID</b> if you do not hold it and it is negative (or unlisted). The AI chair may downgrade to HOLD explaining why, never upgrade. It is a PROPOSAL: nothing executes without your approval, and it is not personalized advice.' } });
    R('reliability', {
      es: { t: 'Fiabilidad del agente', b: 'Qué tanto confiar en un agente según su historial REAL: sus aciertos más 10 "aciertos a medias" imaginarios, divididos entre sus predicciones calificadas más 10. Sin historial vale 50 % (neutral); con muchos aciertos sube hacia 100 %, con muchos fallos baja hacia 0 %. En el comité multiplica el peso de sus conclusiones: 50 % = ×1, 75 % = ×1.5.' },
      en: { t: 'Agent reliability', b: 'How much to trust an agent based on its REAL track record: its hits plus 10 imaginary "half hits", divided by its scored predictions plus 10. With no history it is 50% (neutral); many hits push it toward 100%, many misses toward 0%. In the committee it multiplies the weight of its conclusions: 50% = ×1, 75% = ×1.5.' } });
    R('early_signal', {
      es: { t: 'Señal temprana', b: 'Tasa de acierto en las revisiones INTERMEDIAS (por ejemplo a los 7 días de una conclusión de 30 días, o a los 90 y 180 días de una de largo plazo). Sirve para ver cómo va un agente antes de que venzan sus predicciones, pero NO cuenta para su fiabilidad ni para la calibración: solo cuentan las revisiones finales.' },
      en: { t: 'Early signal', b: 'Hit rate on INTERMEDIATE checks (e.g. at 7 days for a 30-day conclusion, or at 90 and 180 days for a long-term one). It shows how an agent is doing before its predictions come due, but it does NOT count toward its reliability or calibration: only final checks count.' } });
    R('committee_room', {
      es: { t: 'La sala del comité', b: 'En la mesa se sientan los agentes de Khipus, cada uno con su burbuja y una insignia que dice su rol: el <b>Analista</b> (fundamentales y macro), el <b>Radar</b> (noticias, geopolítica y cripto), la <b>Cadena</b> (cadena de suministro) y el <b>Técnico</b> (precio y riesgos; también lleva la mesa de mercado con el precio en vivo y el oficial de riesgo con la volatilidad real). El <b>Comité</b> pone la cuenta (núcleo cuantitativo) y la presidencia. <b>Lo que dice cada agente NO es inventado</b>: es su conclusión real con su fuente, su historial de aciertos y las contradicciones detectadas. Verde = a favor, rojo = en contra, gris = neutral. Si hay IA disponible, cada agente razona sobre SU evidencia y la presidencia redacta el veredicto; todas las cifras pasan por el guardián.' },
      en: { t: 'The committee room', b: 'The Khipus agents sit at the table, each with its bubble and a badge that shows its role: the <b>Analyst</b> (fundamentals and macro), the <b>Radar</b> (news, geopolitics and crypto), the <b>Chain</b> (supply chain) and the <b>Technical</b> agent (price and risks; it also runs the market desk with the live price and the risk officer with real volatility). The <b>Committee</b> brings the math (quant core) and the chair. <b>What each agent says is NOT made up</b>: it is its real conclusion with its source, its hit record and the detected contradictions. Green = for, red = against, grey = neutral. When AI is available, each agent reasons over ITS evidence and the chair writes the verdict; every figure goes through the guardian.' } });
    R('committee_confidence', {
      es: { t: 'Confianza del comité', b: 'Qué tan seguro está el comité de SU decisión (0–100 %). Con presidencia IA es su estimación honesta considerando el disenso y la calidad de la evidencia; sin IA se calcula: qué parte del peso de las conclusiones apoya la dirección elegida × su confianza calibrada promedio. No es la probabilidad de ganar dinero.' },
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

  // ── TEMA KHIPUS OS (2026-10-09, "el comité todavía no está actualizado") ──────
  // Tokens --os-* = COPIA EXACTA de engine/cockpit.js (#bcp-ov). El comité es un overlay propio
  // (z-index 7650, fuera de #bcp-ov), por eso los redefine sobre #cm-ov; claro = body sin .dark,
  // oscuro = body.dark. tests/test_committee_os_ui.py compara ambos: si cambian allá, cambiar aquí.
  // Propios del comité: --cm-warn-fill (ámbar de aviso para rellenos/anillos), --cm-warn / --cm-good / --cm-bad /
  // --cm-ai (TEXTO en ámbar/verde/rojo/violeta: en claro, versiones oscuras que pasan 4.5:1 sobre su píldora
  // teñida; los vivos #0ca30c/#B7791F daban 2.6–3.3:1), --cm-on-sem (texto sobre un botón de color semántico).
  var OS_LIGHT = '--os-bg:#EDEDF5;--os-surface:#FFFFFF;--os-surface-2:#F2F2F7;--os-surface-3:#E7E7EF;' +
    '--os-ink:#111216;--os-ink-2:#5B5E6B;--os-ink-3:#8D90A0;--os-line:rgba(17,18,22,.08);' +
    '--os-shadow:0 1px 2px rgba(17,18,40,.04), 0 8px 28px rgba(17,18,40,.06);' +
    '--os-accent:#2F6BEA;--os-pos:#2F6BEA;--os-neg:#E8623A;--os-mute:#C9CAD6;--os-good:#0ca30c;--os-bad:#d03b3b;' +
    '--os-btn:#111216;--os-btn-ink:#FFFFFF;' +
    '--kos-shadow-lg:0 2px 6px rgba(17,18,40,.06), 0 18px 48px rgba(17,18,40,.14);' +
    '--kos-scrim:rgba(24,26,44,.22);--kos-accent-soft:rgba(47,107,234,.12);' +
    '--cm-warn-fill:#B7791F;--cm-warn:#7F5200;--cm-good:#066B06;--cm-bad:#A82424;--cm-ai:#6236C9;--cm-on-sem:#FFFFFF;color-scheme:light';
  var OS_DARK = '--os-bg:#0E0F14;--os-surface:#17181F;--os-surface-2:#1F2029;--os-surface-3:#2A2B36;' +
    '--os-ink:#F2F2F5;--os-ink-2:#A6A8B5;--os-ink-3:#6E7080;--os-line:rgba(255,255,255,.07);' +
    '--os-shadow:0 1px 2px rgba(0,0,0,.4), 0 10px 30px rgba(0,0,0,.35);' +
    '--os-accent:#4C8DF6;--os-pos:#4C8DF6;--os-neg:#F07A52;--os-mute:#3A3C4A;--os-good:#2fbf5b;--os-bad:#f06565;' +
    '--os-btn:#F2F2F5;--os-btn-ink:#111216;' +
    '--kos-shadow-lg:0 2px 8px rgba(0,0,0,.45), 0 22px 56px rgba(0,0,0,.55);' +
    '--kos-scrim:rgba(0,0,0,.5);--kos-accent-soft:rgba(76,141,246,.16);' +
    '--cm-warn-fill:#F2C46D;--cm-warn:#F2C46D;--cm-good:#2fbf5b;--cm-bad:#F47C7C;--cm-ai:#B48CFF;--cm-on-sem:#0E0F14;color-scheme:dark';
  var OS_SHARED = '--os-r:18px;--os-r-sm:12px;--os-font:\'Nunito\', \'Geist\', system-ui, -apple-system, \'Segoe UI\', sans-serif;--km-ring:var(--os-surface)';
  // Módulos que pintan DENTRO del comité con colores fijos del tema oscuro viejo (engine/pfcommittee.js,
  // pestaña 💼): sin este puente, en el tema claro su texto blanco quedaba invisible. Solo actúa sobre
  // style="" ajenos; este archivo ya no escribe ninguno de esos colores.
  var LEGACY = [['#E8EDFB', 'var(--os-ink)'], ['#C9D2EA', 'var(--os-ink)'], ['#9BA6C4', 'var(--os-ink-2)'], ['#7C87A3', 'var(--os-ink-3)'],
    ['#FFB300', 'var(--cm-warn)'], ['#2BE38B', 'var(--cm-good)'], ['#FF4D6A', 'var(--cm-bad)'], ['#00E0FF', 'var(--os-accent)'],
    ['#5FC6E8', 'var(--os-accent)'], ['#7ecbff', 'var(--os-accent)'], ['#B48CFF', 'var(--cm-ai)']];

  function ensureStyles() {
    if (document.getElementById('cm-styles')) return;
    var css = '' +
      'body:not(.dark) #cm-ov{' + OS_LIGHT + '}' +
      'body.dark #cm-ov{' + OS_DARK + '}' +
      '#cm-ov{' + OS_SHARED + ';position:fixed;inset:0;z-index:7650;display:none;align-items:center;justify-content:center;' +
        'background:var(--kos-scrim);-webkit-backdrop-filter:blur(10px) saturate(1.1);backdrop-filter:blur(10px) saturate(1.1);font-family:var(--os-font)}' +
      '#cm-ov.show{display:flex}' +
      '#cm{width:min(1120px,96vw);max-height:92vh;overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain;border-radius:24px;' +
        'background:var(--os-bg);color:var(--os-ink);box-shadow:var(--kos-shadow-lg);padding:22px 26px 26px;box-sizing:border-box;' +
        'font-family:var(--os-font);font-size:14px;line-height:1.5;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;animation:cmPop .22s ease}' +
      '@keyframes cmPop{from{opacity:0;transform:translateY(6px) scale(.985)}to{opacity:1;transform:none}}' +
      '#cm *{box-sizing:border-box}' +
      '#cm button,#cm input,#cm select{font-family:inherit}' +
      // encabezado: mascota del Comité + título + cerrar redondo (como la barra de Khipus OS)
      '#cm .cm-hd{display:flex;align-items:center;gap:12px;margin-bottom:6px}' +
      '#cm .cm-name{display:flex;align-items:center;gap:10px;font-size:20px;font-weight:800;letter-spacing:-.015em;min-width:0;overflow-wrap:anywhere}' +
      '#cm .cm-name .cm-ent{color:var(--os-ink-2);font-weight:700}' +
      '#cm .cm-x{margin-left:auto;width:40px;height:40px;padding:0;border:0;border-radius:999px;cursor:pointer;background:transparent;color:var(--os-ink-2);' +
        'font-size:15px;font-weight:600;flex:0 0 auto;display:inline-flex;align-items:center;justify-content:center;transition:background-color .15s,color .15s}' +
      '#cm .cm-x:hover{background:var(--os-surface-2);color:var(--os-ink)}' +
      '#cm .cm-sub{font-size:13px;color:var(--os-ink-2);margin:0 0 16px;line-height:1.55;max-width:820px}' +
      // pestañas = control segmentado (como .osw-seg); un .cm-tab suelto es una opción tipo píldora
      '#cm .cm-tabs{display:flex;flex-wrap:wrap;gap:2px;width:fit-content;max-width:100%;padding:3px;border-radius:20px;background:var(--os-surface-2);margin-bottom:16px}' +
      '#cm>.cm-tabs{background:var(--os-surface-3)}' +
      '#cm .cm-tab{appearance:none;-webkit-appearance:none;border:0;cursor:pointer;height:32px;padding:0 14px;border-radius:999px;font-size:13px;font-weight:600;' +
        'white-space:nowrap;background:var(--os-surface-2);color:var(--os-ink-2);transition:background-color .15s,color .15s,box-shadow .15s}' +
      '#cm .cm-tab:hover{background:var(--os-surface-3);color:var(--os-ink)}' +
      '#cm .cm-tab.on{background:var(--os-btn);color:var(--os-btn-ink)}' +
      '#cm .cm-tabs .cm-tab{background:none}' +
      '#cm .cm-tabs .cm-tab:hover{background:none;color:var(--os-ink)}' +
      '#cm .cm-tabs .cm-tab.on{background:var(--os-surface);color:var(--os-ink);box-shadow:var(--os-shadow)}' +
      // botones = píldoras: principal oscuro/claro según el tema, secundario suave
      '#cm .cm-btn{appearance:none;-webkit-appearance:none;border:0;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:6px;' +
        'height:40px;padding:0 18px;border-radius:999px;font-size:13.5px;font-weight:700;letter-spacing:-.005em;white-space:nowrap;' +
        'background:var(--os-btn);color:var(--os-btn-ink);transition:opacity .15s,background-color .15s,transform .1s}' +
      '#cm .cm-btn:hover{opacity:.88}#cm .cm-btn:active{transform:scale(.98)}' +
      '#cm .cm-btn[disabled]{opacity:.45;cursor:default;transform:none}' +
      '#cm .cm-btn.ghost{background:var(--os-surface);color:var(--os-ink);font-weight:600;box-shadow:var(--os-shadow)}' +
      '#cm .cm-cell .cm-btn.ghost,#cm .cm-room .cm-btn.ghost{background:var(--os-surface-2);box-shadow:none}' +
      '#cm .cm-btn.ghost:hover{background:var(--os-surface-3);opacity:1}' +
      '#cm .cm-btn.ok{background:var(--cm-good);color:var(--cm-on-sem)}' +
      '#cm .cm-btn.no{color:var(--cm-bad);background:var(--os-surface-2);background:color-mix(in srgb,var(--os-bad) 12%,transparent)}' +
      '#cm .cm-btn.no:hover{opacity:1;background:color-mix(in srgb,var(--os-bad) 18%,transparent)}' +
      // foco de teclado VISIBLE (WCAG 2.4.7): contorno de acento de 2 px; el anillo suave queda solo como extra
      '#cm .cm-tab:focus-visible,#cm .cm-btn:focus-visible,#cm .cm-x:focus-visible,#cm .cm-ref:focus-visible,#cm .cm-hist:focus-visible{outline:2px solid var(--os-accent);outline-offset:2px}' +
      // campos: sin borde, fondo suave, anillo de foco
      '#cm input,#cm select{height:40px;border:0;border-radius:var(--os-r-sm);padding:0 14px;font-size:13.5px;color:var(--os-ink);background:var(--os-surface);' +
        'box-shadow:var(--os-shadow);outline:none;min-width:0;max-width:100%;transition:box-shadow .15s,background-color .15s}' +
      '#cm select{padding-right:10px;cursor:pointer}' +
      '#cm input::placeholder{color:var(--os-ink-3)}' +
      '#cm .cm-cell input,#cm .cm-cell select{background:var(--os-surface-2);box-shadow:none}' +
      '#cm input:focus,#cm select:focus{box-shadow:0 0 0 3px var(--kos-accent-soft)}' +
      '#cm input:focus-visible,#cm select:focus-visible{outline:2px solid var(--os-accent);outline-offset:2px}' +
      '#cm .cm-form{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:16px}' +
      '#cm .cm-form input{flex:1 1 220px}#cm .cm-form select{flex:1 1 200px}' +
      '#cm .cm-grid{display:grid;grid-template-columns:minmax(0,3fr) minmax(0,2fr);gap:14px}' +
      // tarjetas de Khipus OS: superficie, radio 18, sombra suave, sin bordes
      '#cm .cm-cell{background:var(--os-surface);border-radius:var(--os-r);box-shadow:var(--os-shadow);padding:16px 18px;margin-bottom:14px;min-width:0}' +
      '#cm .cm-t{display:flex;align-items:center;gap:6px;font-size:13px;font-weight:700;letter-spacing:-.005em;color:var(--os-ink);margin-bottom:10px}' +
      '#cm .cm-sec{color:var(--os-ink-2);margin:6px 2px 10px}' +
      '#cm .cm-note{font-size:13px;color:var(--os-ink-2);line-height:1.55;overflow-wrap:anywhere}' +
      '#cm .cm-lead{font-size:14px;color:var(--os-ink);line-height:1.6}' +
      '#cm .cm-dec{display:inline-flex;align-items:center;gap:6px;font-size:14.5px;font-weight:800;letter-spacing:.03em;padding:7px 16px;border-radius:999px}' +
      '#cm .cm-pill{display:inline-flex;align-items:center;gap:4px;font-size:11.5px;font-weight:600;padding:3px 10px;border-radius:999px;' +
        'background:var(--os-surface-2);color:var(--os-ink-2);white-space:nowrap}' +
      '#cm .cm-callout{margin-top:10px;font-size:12.5px;line-height:1.55;border-radius:var(--os-r-sm);padding:9px 12px;overflow-wrap:anywhere}' +
      '#cm .cm-g{display:grid;grid-template-columns:120px minmax(0,1fr) 46px;align-items:center;gap:10px;font-size:13px;margin:7px 0}' +
      '#cm .cm-gt{position:relative;height:8px;border-radius:999px;background:var(--os-surface-3);overflow:hidden}' +
      '#cm .cm-gt i{position:absolute;top:0;bottom:0;border-radius:999px}' +
      '#cm .cm-gt b{position:absolute;left:50%;top:0;bottom:0;width:2px;margin-left:-1px;background:var(--os-ink-3);opacity:.55}' +
      '#cm .cm-gv{text-align:right;font-variant-numeric:tabular-nums;font-weight:700}' +
      '#cm .cm-list{margin:4px 0 0 18px;padding:0;font-size:13px;line-height:1.6;color:var(--os-ink)}' +
      '#cm .cm-list li{margin-bottom:6px;overflow-wrap:anywhere}' +
      '#cm .cm-ref{font-size:11px;font-weight:600;color:var(--os-accent);cursor:pointer;margin-left:4px;white-space:nowrap;border-radius:6px}' +
      '#cm .cm-ref:hover{text-decoration:underline}' +
      '#cm .cm-kv{display:flex;justify-content:space-between;align-items:center;gap:12px;font-size:13px;padding:7px 0;border-bottom:1px solid var(--os-line)}' +
      '#cm .cm-kv:last-child{border-bottom:0}' +
      '#cm .cm-kv span:first-child{color:var(--os-ink-2)}' +
      '#cm .cm-kv span:last-child{text-align:right;font-variant-numeric:tabular-nums;font-weight:600;color:var(--os-ink)}' +
      '#cm .cm-disc{font-size:12.5px;line-height:1.55;color:var(--cm-warn);background:var(--os-surface-2);background:color-mix(in srgb,var(--cm-warn-fill) 12%,transparent);' +
        'border-radius:var(--os-r-sm);padding:11px 14px;margin-bottom:14px}' +
      '#cm .cm-msg{border-radius:var(--os-r-sm);padding:10px 14px;font-size:13px;font-weight:600;margin-bottom:14px;line-height:1.5}' +
      '#cm .cm-tw{overflow-x:auto;max-width:100%}' +
      '#cm table{width:100%;border-collapse:collapse;font-size:13px}' +
      '#cm th{font-size:11px;font-weight:700;letter-spacing:.02em;color:var(--os-ink-3);text-align:left;padding:8px 10px;border-bottom:1px solid var(--os-line);white-space:nowrap}' +
      '#cm td{padding:8px 10px;border-bottom:1px solid var(--os-line);white-space:nowrap;font-variant-numeric:tabular-nums}' +
      '#cm tbody tr:last-child td{border-bottom:0}' +
      '#cm td .cm-mav{margin-right:8px}' +
      '#cm .cm-steps{margin:8px 0 0 18px;padding:0;font-size:12.5px;color:var(--os-ink-2);line-height:1.6}' +
      '#cm .cm-hist{font-size:13px;padding:9px 0;border-bottom:1px solid var(--os-line);cursor:pointer;transition:color .15s}' +
      '#cm .cm-hist:last-child{border-bottom:0}' +
      '#cm .cm-hist:hover{color:var(--os-accent)}' +
      '#cm .cm-hist.static{cursor:default}#cm .cm-hist.static:hover{color:inherit}' +
      '#cm a{color:var(--os-accent);text-decoration:none}#cm a:hover{text-decoration:underline}' +
      '#cm .cm-learn p{font-size:14px;line-height:1.65;color:var(--os-ink-2);margin:0 0 12px}' +
      '#cm .cm-learn h4{display:flex;align-items:center;gap:6px;flex-wrap:wrap;font-size:15px;font-weight:700;margin:20px 0 6px;color:var(--os-ink)}' +
      '#cm .cm-agents{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:4px 0 6px}' +
      '#cm .cm-agent{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:var(--os-r-sm);background:var(--os-surface-2);min-width:0}' +
      '#cm .cm-agent b{display:block;font-size:13.5px;color:var(--os-ink)}#cm .cm-agent span.r{display:block;font-size:11.5px;color:var(--os-ink-2);line-height:1.35}' +
      '#cm .cm-bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap}' +
      '#cm .cm-bar .cm-tabs{margin-bottom:0}' +
      '#cm .cm-score{font-size:22px;font-weight:800;min-width:52px;font-variant-numeric:tabular-nums;letter-spacing:-.02em}' +
      '#cm .cm-spin{display:inline-block;animation:cmspin 1s linear infinite;color:var(--os-accent)}' +
      '@keyframes cmspin{to{transform:rotate(360deg)}}';
    // ── sala del comité: las MASCOTAS sentadas a la mesa + la conversación ──
    css += '#cm .cm-room{background:var(--os-surface);border-radius:var(--os-r);box-shadow:var(--os-shadow);padding:16px 16px 14px;margin-bottom:14px;min-width:0}' +
      '#cm .cm-room>.cm-t{flex-wrap:wrap}' +
      '#cm .cm-onair{display:inline-flex;align-items:center;gap:5px;margin-left:4px;font-size:11px;font-weight:800;letter-spacing:.06em;color:var(--cm-bad)}' +
      '#cm .cm-onair i{width:7px;height:7px;border-radius:50%;background:var(--os-bad);animation:cmdot 1.4s infinite}' +
      '#cm .cm-count{margin-left:auto;display:inline-flex;gap:12px;font-size:12.5px;font-weight:700;font-variant-numeric:tabular-nums}' +
      '#cm .cm-table{display:flex;flex-wrap:wrap;justify-content:center;gap:16px 6px;padding:18px 8px 14px;border-radius:var(--os-r);background:var(--os-surface-2);margin-bottom:12px}' +
      '#cm .cm-brk{flex-basis:100%;height:0}' +
      // quien todavía no habló se nota en la MASCOTA (desaturada y tenue), nunca en el texto: el rol escrito
      // es lo único que distingue a los puestos que comparten mascota y debe leerse siempre (≥4.5:1)
      '#cm .cm-seat{width:96px;text-align:center;font-size:11.5px;line-height:1.3;color:var(--os-ink-2);transition:transform .3s}' +
      '#cm .cm-seat.talk{transform:translateY(-3px)}' +
      '#cm .cm-av{position:relative;width:52px;height:52px;margin:0 auto 8px;border-radius:50%;transition:box-shadow .35s,filter .35s,opacity .35s}' +
      '#cm .cm-seat:not(.spoke):not(.talk) .cm-av{filter:saturate(.35);opacity:.6}' +
      '#cm .cm-seat.spoke .cm-av{box-shadow:0 0 0 3px var(--os-surface-2),0 0 0 5px var(--cm-ring,transparent)}' +
      '#cm .cm-seat.talk .cm-av{box-shadow:0 0 0 3px var(--os-surface-2),0 0 0 7px var(--kos-accent-soft);animation:cmglow 1.6s ease-in-out infinite}' +
      '#cm .cm-seat.absent:not(.spoke):not(.talk) .cm-av{filter:grayscale(1) opacity(.7);outline:1.5px dashed var(--os-ink-3);outline-offset:4px}' +
      '@keyframes cmglow{0%,100%{box-shadow:0 0 0 3px var(--os-surface-2),0 0 0 6px var(--kos-accent-soft)}50%{box-shadow:0 0 0 3px var(--os-surface-2),0 0 0 10px var(--kos-accent-soft)}}' +
      '#cm .cm-seat .cm-sn{color:var(--os-ink);font-weight:700;font-size:12px;overflow-wrap:anywhere}' +
      '#cm .cm-seat .cm-sr{font-size:11px;color:var(--os-ink-2);margin-top:1px;overflow-wrap:anywhere}' +
      '#cm .cm-seat .cm-ss{font-size:10.5px;font-weight:800;letter-spacing:.05em;margin-top:4px;color:var(--os-ink-2)}' +
      '#cm .cm-seat .cm-rec{font-size:11px;color:var(--os-ink-2);font-variant-numeric:tabular-nums}' +
      '#cm .cm-feed{max-height:560px;overflow-y:auto;overscroll-behavior:contain;padding:2px 4px 2px 0}' +
      '#cm .cm-bub{display:flex;gap:10px;margin:0 0 10px;align-items:flex-start}' +
      '#cm .cm-bub.new{animation:cmin .45s ease-out}' +
      '@keyframes cmin{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}' +
      '#cm .cm-bav{flex:0 0 32px;width:32px;height:32px;line-height:0}' +
      '#cm .cm-btx{flex:1 1 auto;min-width:0;border-radius:6px 18px 18px 18px;padding:9px 14px;background:var(--os-surface-2);box-shadow:inset 3px 0 0 var(--cm-sc,transparent);' +
        'font-size:13px;line-height:1.55;color:var(--os-ink);overflow-wrap:anywhere}' +
      '#cm .cm-btx .cm-hl{color:var(--os-ink);font-weight:700}' +
      '#cm .cm-bh{display:flex;gap:6px;align-items:center;flex-wrap:wrap;font-size:12px;color:var(--os-ink-3);margin-bottom:3px}' +
      '#cm .cm-bh b{color:var(--os-ink);font-weight:700}#cm .cm-bh .cm-role{color:var(--os-ink-2);font-weight:600}' +
      '#cm .cm-tag{font-size:10px;font-weight:800;letter-spacing:.05em;padding:2px 8px;border-radius:999px;background:var(--os-surface-3)}' +
      '#cm .cm-src{display:block;font-size:11.5px;color:var(--os-ink-3);margin-top:4px}' +
      '#cm .cm-typing{display:flex;align-items:center;gap:8px;font-size:12.5px;color:var(--os-ink-2);padding:4px 2px 2px}' +
      '#cm .cm-typing .cm-dots{display:inline-flex;gap:3px}' +
      '#cm .cm-typing i{display:inline-block;width:5px;height:5px;border-radius:50%;background:var(--os-accent);animation:cmdot 1.2s infinite}' +
      '#cm .cm-typing i:nth-child(2){animation-delay:.2s}#cm .cm-typing i:nth-child(3){animation-delay:.4s}' +
      '@keyframes cmdot{0%,80%,100%{opacity:.2}40%{opacity:1}}' +
      '#cm .cm-strip{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:12px}' +
      '#cm .cm-strip span{font-size:11.5px;font-weight:600;padding:4px 10px;border-radius:999px;background:var(--os-surface);color:var(--os-ink-3);box-shadow:var(--os-shadow)}' +
      '#cm .cm-strip span.d{color:var(--cm-good)}' +
      '#cm .cm-strip span.c{color:var(--os-accent);box-shadow:0 0 0 2px var(--kos-accent-soft)}' +
      '#cm .cm-strip span.cm-clock{margin-left:auto;background:none;box-shadow:none;color:var(--os-ink-2);font-variant-numeric:tabular-nums}' +
      '#cm .cm-votes{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}' +
      '@media(prefers-reduced-motion:reduce){#cm,#cm .cm-seat.talk .cm-av,#cm .cm-bub.new,#cm .cm-typing i,#cm .cm-onair i,#cm .cm-spin{animation:none}#cm .cm-seat,#cm .cm-av{transition:none}}' +
      // móvil: hoja a pantalla completa, una sola columna
      '@media(max-width:760px){#cm-ov{align-items:stretch}' +
        '#cm{width:100vw;max-width:100vw;height:100%;max-height:none;border-radius:0;padding:16px 14px calc(22px + env(safe-area-inset-bottom,0px))}' +
        '#cm .cm-grid{grid-template-columns:minmax(0,1fr);gap:0}' +
        '#cm .cm-form>*{flex:1 1 100%}' +
        '#cm .cm-g{grid-template-columns:86px minmax(0,1fr) 40px}' +
        '#cm .cm-cell,#cm .cm-room{padding:14px}' +
        '#cm .cm-seat{width:80px;font-size:10.5px}#cm .cm-av,#cm .cm-av .cm-mav,#cm .cm-av .km,#cm .cm-av .km svg{width:44px!important;height:44px!important}' +
        '#cm .cm-feed{max-height:380px}}';
    css += LEGACY.map(function (p) { return '#cm-body [style*="color:' + p[0] + '" i]{color:' + p[1] + '!important}'; }).join('') +
      LEGACY.slice(4).map(function (p) { return '#cm-body [style*="background:' + p[0] + '" i]{background:' + fill(p[1]) + '!important}'; }).join('') +
      '#cm-body [style*="rgba(122,158,255"]{border-color:var(--os-line)!important}' +
      '#cm-body [style*="background:rgba(122,158,255"]{background:var(--os-surface-3)!important}';
    var st = document.createElement('style'); st.id = 'cm-styles'; st.textContent = css;
    document.head.appendChild(st);
  }

  var S = { tab: 'committee', entity: null, clientId: '', memo: null, history: [], poll: null, busy: false, msg: null,
    clients: null, clientsErr: null, tr: null, cal: null, recent: null, agentSel: '__all', chart: null,
    running: null, deciding: false, shown: 0, animIdx: -1, reveal: null, replay: null };
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
    // Lecturas NO interactivas sin PIN guardado → pedido normal (el server
    // oculta los datos del cliente). Antes _tradeFetch respondía 401 local y la
    // pantalla del comité quedaba "cargando" para siempre (bug 2026-09-30).
    var stored = window._tradePinStored ? window._tradePinStored() : null;
    if (!interactive && !stored) return getJSON(url, opts);
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
    stopReveal();
    if (S.chart) { try { S.chart.destroy(); } catch (e) {} S.chart = null; }
    S.deciding = false;
  }

  function render() {
    var el = document.getElementById('cm'); if (!el) return;
    if (S.chart) { try { S.chart.destroy(); } catch (e) {} S.chart = null; }
    var tabs = [['board', '📋 ' + L('Pizarra', 'Board')], ['committee', '🏛 ' + L('Comité', 'Committee')], ['portfolio', '💼 ' + L('Mi cartera', 'My portfolio')], ['history', '🎯 ' + L('Historial', 'Track record')], ['learn', '🧠 ' + L('Cómo aprende', 'How it learns')]];
    el.innerHTML =
      '<div class="cm-hd"><span class="cm-name">' + mascotHtml('comite', 30, 'idle', '🏛') + '<span>' + esc(L('Comité de inversión', 'Investment committee')) +
          (S.entity ? '<span class="cm-ent"> · ' + esc(nodeLabel(S.entity)) + '</span>' : '') + '</span></span>' +
        '<button class="cm-x" onclick="window.KhipuCommittee.close()" title="' + esc(L('Cerrar', 'Close')) + '" aria-label="' + esc(L('Cerrar', 'Close')) + '">✕</button></div>' +
      '<div class="cm-sub">' + esc(L('Los agentes (Analista, Radar, Cadena y Técnico) traen su investigación, su historial real de aciertos, el riesgo medido y datos en vivo; el Comité propone una decisión con su tamaño. Nada se ejecuta sin tu aprobación.',
        'The agents (Analyst, Radar, Chain and Technical) bring their research, their real track record, measured risk and live data; the Committee proposes a decision with its size. Nothing executes without your approval.')) + '</div>' +
      '<div class="cm-tabs" role="tablist">' + tabs.map(function (t) { return '<button class="cm-tab' + (S.tab === t[0] ? ' on' : '') + '" data-t="' + t[0] + '" role="tab" aria-selected="' + (S.tab === t[0]) + '">' + esc(t[1]) + '</button>'; }).join('') + '</div>' +
      (S.msg ? '<div class="cm-msg" role="status" style="' + tint(S.msg.bad ? C.warn : C.good) + '">' + esc(S.msg.text) + '</div>' : '') +
      '<div id="cm-body"></div>';
    el.querySelectorAll('.cm-tab').forEach(function (b) { b.onclick = function () { S.tab = b.getAttribute('data-t'); S.msg = null; render(); }; });
    var body = document.getElementById('cm-body');
    if (S.tab === 'board') renderBoard(body);
    else if (S.tab === 'portfolio') { if (window.KhipuPortfolioCommittee) window.KhipuPortfolioCommittee.render(body); else body.innerHTML = ''; }
    else if (S.tab === 'history') renderHistory(body);
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
        '<input id="cm-ent" placeholder="' + esc(L('Busca una empresa y elígela de la lista (ej. NVDA)', 'Search a company and pick it from the list (e.g. NVDA)')) + '" value="' + esc(S.entity ? nodeLabel(S.entity) : '') + '"' + (S.entity ? ' data-pick-value="' + esc(S.entity) + '" data-pick-label="' + esc(nodeLabel(S.entity)) + '"' : '') + '>' +
        '<select id="cm-cli">' + clientOptions() + '</select>' +
        (S.clients === null ? '<button class="cm-btn ghost" id="cm-lc">🔒 ' + esc(L('Cargar clientes (PIN)', 'Load clients (PIN)')) + '</button>' : '') +
        '<button class="cm-btn" id="cm-run"' + (S.busy ? ' disabled' : '') + '>' + esc(S.busy ? L('El comité delibera…', 'Committee deliberating…') : L('Correr comité', 'Run committee')) + '</button>' +
        '<button class="cm-btn ghost" id="cm-pf">💼 ' + esc(L('Analizar mi cartera', 'Analyze my portfolio')) + '</button>' +
      '</div>' +
      (S.clientsErr ? '<div class="cm-note" style="margin:-4px 0 10px">' + esc(S.clientsErr) + '</div>' : '') +
      (S.busy ? '<div id="cm-live">' + liveHtml() + '</div>' : '') +
      (m && !S.busy ? memoHtml(m) : (!S.busy ? '<div class="cm-cell"><div class="cm-note" style="display:flex;gap:12px;align-items:center">' + mascotHtml('comite', 36, 'idle', '🏛') + esc(S.entity ? L('Todavía no hay memo del comité para esta empresa. Pulsa «Correr comité». Consejo: primero corre 🔬 Investigación IA para que el comité tenga conclusiones.', 'No committee memo for this company yet. Press “Run committee”. Tip: run 🔬 AI research first so the committee has conclusions.') : L('Escribe una empresa y pulsa «Correr comité».', 'Type a company and press “Run committee”.')) + '</div>' +
        (S.entity && window.KhipuResearch ? '<div style="margin-top:8px"><button class="cm-btn ghost" onclick="window.KhipuResearch.open(\'' + esc(S.entity) + '\')">🔬 ' + esc(L('Investigación IA', 'AI research')) + '</button></div>' : '') + '</div>' : '')) +
      (S.history && S.history.length > 1 ? '<div class="cm-cell"><div class="cm-t">🗂 ' + esc(L('Memos anteriores', 'Previous memos')) + '</div>' +
        S.history.map(function (h) {
          var d = DEC[h.decision] || [C.neu, h.decision || '—', h.decision || '—'];
          var st = STATUS[h.status] || [h.status, h.status];
          return '<div class="cm-hist" data-id="' + esc(h.memo_id) + '"><b style="color:' + d[0] + '">' + esc(L(d[1], d[2])) + '</b> · ' + esc(clock(h.created_at)) + ' · ' + esc(L(st[0], st[1])) +
            (h.overall_conviction != null ? ' · ' + (h.overall_conviction > 0 ? '+' : '') + Math.round(h.overall_conviction) : '') + (h.ai_used ? '' : ' · ' + esc(L('sin IA', 'no AI'))) + (h.has_client ? ' · 👤' : '') + '</div>';
        }).join('') + '</div>' : '');
    var run = document.getElementById('cm-run'); if (run) run.onclick = runCommittee;
    var pfb = document.getElementById('cm-pf'); if (pfb) pfb.onclick = function () { S.tab = 'portfolio'; S.msg = null; render(); };
    var ent = document.getElementById('cm-ent');
    if (ent && window.KhipuPick) {   // opciones FIJAS: empresas del grafo + "Mi cartera" (pedido 2026-10-05)
      window.KhipuPick.attach(ent, { kind: 'entity',
        extras: [{ value: '__portfolio__', icon: '💼', label: L('Mi cartera', 'My portfolio'), hint: L('el comité analiza tu cartera completa', 'the committee analyzes your whole portfolio') }],
        onPick: function (o) { if (o.value === '__portfolio__') { S.tab = 'portfolio'; S.msg = null; render(); } } });
    }
    var cli = document.getElementById('cm-cli'); if (cli) cli.onchange = function () { S.clientId = cli.value; };
    var lc = document.getElementById('cm-lc'); if (lc) lc.onclick = function () { loadClients(true); };
    body.querySelectorAll('.cm-hist').forEach(function (x) { x.onclick = function () { loadMemo(x.getAttribute('data-id')); }; });
    body.querySelectorAll('[data-ref]').forEach(function (x) { x.onclick = function () { openRef(x.getAttribute('data-ref')); }; });
    wireRoom(body); scrollFeed();
    var ap = document.getElementById('cm-approve'); if (ap) ap.onclick = approve;
    var rj = document.getElementById('cm-reject'); if (rj) rj.onclick = reject;
  }

  function gauge(label, score, sub) {
    var v = Math.max(-100, Math.min(100, Number(score) || 0));
    var col = v > 0 ? C.good : v < 0 ? C.bad : C.mute;
    var w = Math.abs(v) / 2;
    var left = v >= 0 ? 50 : 50 - w;
    return '<div class="cm-g"><span style="min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + esc(label) + '">' + esc(label) + '</span>' +
      '<span class="cm-gt" title="' + esc(sub || '') + '"><b></b><i style="left:' + left + '%;width:' + w + '%;background:' + fill(col) + '"></i></span>' +
      '<span class="cm-gv">' + (v > 0 ? '+' : '') + Math.round(v) + '</span></div>' +
      (sub ? '<div class="cm-note" style="font-size:11.5px;color:var(--os-ink-3);margin:-3px 0 6px 0">' + esc(sub) + '</div>' : '');
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
    if (m.status === 'failed') return '<div class="cm-cell"><div class="cm-note" style="color:var(--cm-warn)">' + esc(L('El comité falló: ', 'The committee failed: ') + (T(m, 'error') || '')) + '</div></div>';
    var b = m.memo || {};
    var d = DEC[m.decision] || [C.neu, m.decision, m.decision];
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
        '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px">' +
          (b.decision_code === 'INSUFFICIENT_DATA'
            ? '<span class="cm-dec" style="' + tint(C.warn, 14) + '" title="' + esc(isEn() ? (b.quant_reason_en || '') : (b.quant_reason_es || '')) + '">' + esc(L(b.decision_label_es || d[1], b.decision_label_en || d[2])) + '</span>'
            : '<span class="cm-dec" style="' + tint(d[0], 14) + '">' + esc(L(d[1], d[2])) + '</span>') + chip('committee_decision') +
          (b.track_validation && !b.track_validation.validated
            ? '<span class="cm-pill" style="' + tint(C.warn) + '" title="' + esc(L(b.track_validation.label_es, b.track_validation.label_en) + (b.track_validation.effect_es ? ' · ' + L(b.track_validation.effect_es, b.track_validation.effect_en) : '')) + '">⚠ ' +
              esc(L('no validado', 'not validated')) + (b.track_validation.effect_es ? ' · ' + esc(L('tamaño ½', 'size ½')) : '') + '</span>'
            : (b.track_validation ? '<span class="cm-pill" style="' + tint(C.good) + '">✓ ' + esc(L('historial validado', 'validated record')) + '</span>' : '')) +
          '<span style="font-weight:800;font-size:15px;color:var(--os-ink);overflow-wrap:anywhere">' + esc(m.label || nodeLabel(m.entity_id)) + (m.symbol ? ' · ' + esc(m.symbol) : '') + '</span>' +
          '<span class="cm-pill">' + esc(L(st[0], st[1])) + '</span>' +
          '<span class="cm-pill">' + esc(m.ai_used ? L('presidencia con IA', 'AI chair') + (m.model ? ' · ' + m.model : '') : L('sin IA (plantilla determinista)', 'no AI (deterministic template)')) + '</span>' +
          (m.client_id ? '<span class="cm-pill">👤 ' + esc(cl ? (cl.name || m.client_id) : L('cliente (montos ocultos sin PIN)', 'client (amounts hidden without PIN)')) +
            ((m.client_mode || cl) ? ' · ' + esc(badge(m.client_mode || cl)) : '') + '</span>' : '') +
        '</div>' +
        '<div class="cm-lead">' + esc(summary || '') + '</div>' +
        (b.tally ? '<div class="cm-votes"><span class="cm-pill" style="' + tint(C.good) + '">👍 ' + b.tally['for'] + ' ' + esc(L('a favor', 'for')) + '</span>' +
          '<span class="cm-pill" style="' + tint(C.bad) + '">👎 ' + b.tally.against + ' ' + esc(L('en contra', 'against')) + '</span>' +
          '<span class="cm-pill">✋ ' + b.tally.neutral + ' ' + esc(L('neutral', 'neutral')) + '</span>' +
          (b.tally.absent ? '<span class="cm-pill" style="' + tint(C.warn) + '">⬜ ' + b.tally.absent + ' ' + esc(L('ausente(s)', 'absent')) + '</span>' : '') +
          '<span class="cm-pill">🧭 ' + esc(L('convicción ', 'conviction ')) + (m.overall_conviction > 0 ? '+' : '') + Math.round(m.overall_conviction || 0) + '/100</span></div>' : '') +
        (b.track_validation && !b.track_validation.validated ? '<div class="cm-callout" style="' + tint(C.warn, 10) + '">⚠ ' +
          esc(L('Los analistas todavía no tienen historial validado (' + b.track_validation.min_n + ' predicciones calificadas cada uno): esta propuesta no está probada contra el mercado. Por eso el tamaño sugerido es la mitad del normal. El historial se llena solo con el tiempo (ver pestaña Historial).',
                'The analysts have no validated track record yet (' + b.track_validation.min_n + ' scored predictions each): this proposal is not yet proven against the market, so the suggested size is half the normal one. The record fills in over time (see the History tab).')) + '</div>' : '') +
        (m.falsified_claims && m.falsified_claims.length ? '<div class="cm-callout" style="' + tint(C.bad, 10) + '">⛔ ' +
          esc(L('El mercado ya FALSÓ ' + m.falsified_claims.length + ' conclusión(es) de este memo: ', 'The market has already FALSIFIED ' + m.falsified_claims.length + ' conclusion(s) of this memo: ') +
              m.falsified_claims.map(function (f) { return ag(f.agent_type) + ' — ' + (isEn() ? (f.statement_en || f.statement_es) : f.statement_es); }).join(' · ') + ' ' +
              L('Vuelve a convocar al comité antes de actuar.', 'Reconvene the committee before acting.')) + '</div>' : '') +
        (b.decision_code === 'INSUFFICIENT_DATA' && b.quorum ? '<div class="cm-callout" style="' + tint(C.warn, 10) + '">' +
          esc(L('Sin quórum no hay decisión: ', 'No quorum, no decision: ') + (isEn() ? (b.quorum.reason_en || '') : (b.quorum.reason_es || '')) + ' ' +
              L('Faltan: ', 'Missing: ') + (b.quorum.to_run || []).map(function (a) { return ag(a); }).join(', ') + '. ' +
              L('Corre 🔬 Investigación IA para completar a los analistas y vuelve a convocar al comité.', 'Run 🔬 AI research to complete the analysts and reconvene the committee.')) + '</div>' : '') +
        (m.quant_decision && m.quant_decision !== m.decision ? '<div class="cm-callout" style="' + tint(C.warn, 10) + '">' + esc(L('El núcleo cuantitativo proponía ', 'The quantitative core proposed ') + decLabel(m.quant_decision) + L('; la presidencia rebajó a MANTENER: ', '; the chair downgraded to HOLD: ') + (note || '')) + '</div>' : '') +
        conclusionsHtml(b) + debateNote(b) +
        (b.quant_reason_es ? '<div class="cm-note" style="margin-top:8px;font-size:12px">' + esc(L('Regla aplicada: ', 'Rule applied: ') + (isEn() ? b.quant_reason_en : b.quant_reason_es)) + '</div>' : '') +
        (m.symbol && (m.inputs || {}).us_listing === false ? '<div class="cm-note" style="margin-top:6px;font-size:12px;color:var(--cm-warn)">' + esc(L('Cotiza fuera de EE.UU. (' + m.symbol + ', en moneda local): Alpaca no la opera, así que el comité no propone órdenes para clientes; su historial se califica en moneda local.', 'Trades outside the US (' + m.symbol + ', in local currency): Alpaca does not trade it, so the committee does not propose client orders; its track record is scored in local currency.')) + '</div>' : '') +
        (b.ai_error ? '<div class="cm-note" style="margin-top:6px;font-size:12px;color:var(--os-ink-3)">' + esc(L('Nota: ', 'Note: ') + T(b, 'ai_error')) + '</div>' : '') +
        '<div class="cm-note" style="margin-top:8px;font-size:12px;color:var(--os-ink-3)">' + esc(clock(m.created_at) + ' · ' + L('pedido por ', 'requested by ') + (m.requested_by || '—') + (m.expires_at ? ' · ' + L('vence ', 'expires ') + clock(m.expires_at) : '') + (m.expired ? ' · ' + L('VENCIDO: vuelve a correrlo', 'EXPIRED: run it again') : '')) + '</div>' +
      '</div>' +
      '<div id="cm-live">' + memoRoomHtml(m) + '</div>' +
        (pv ? previewHtml(pv, m) : '') +
        ((m.status === 'proposed' && !m.expired) || m.status === 'approved' ? '<div class="cm-cell"><div class="cm-t">✋ ' + esc(L('Tu decisión', 'Your decision')) + '</div>' +
          (m.status === 'proposed' ? '<div class="cm-note" style="margin-bottom:8px">' + (m.client_id && actionable && m.client_mode ? '<b>' + esc(badge(m.client_mode)) + '</b> · ' : '') + esc(m.client_id && actionable ? L('Aprobar prepara una orden (previsualización) para el cliente; la ejecución se confirma aparte en Clientes.', 'Approving prepares an order (preview) for the client; execution is confirmed separately in Clients.') : L('Aprobar registra la decisión; sin cliente no se prepara ninguna orden.', 'Approving records the decision; with no client no order is prepared.')) + '</div>'
            : '<div class="cm-note" style="margin-bottom:8px">' + esc(L('Rechazar ahora también retira la orden que espera aprobación en Clientes.', 'Rejecting now also withdraws the order awaiting approval in Clients.')) + '</div>') +
          '<div style="display:flex;gap:8px;flex-wrap:wrap">' + (m.status === 'proposed' ? '<button class="cm-btn ok" id="cm-approve"' + (S.deciding ? ' disabled' : '') + '>' + esc(S.deciding ? L('Procesando…', 'Working…') : '✅ ' + L('Aprobar', 'Approve')) + '</button>' : '') +
          '<button class="cm-btn no" id="cm-reject"' + (S.deciding ? ' disabled' : '') + '>✖ ' + esc(L('Rechazar', 'Reject')) + '</button></div></div>' : '') +
        (m.decided_by ? '<div class="cm-cell"><div class="cm-note">' + esc(L('Decidido por ', 'Decided by ') + m.decided_by + ' · ' + clock(m.decided_at) + (m.decision_note ? ' · «' + m.decision_note + '»' : '')) + '</div></div>' : '') +
      '<div class="cm-t cm-sec">🔍 ' + esc(L('El detalle (para quien quiera ver la cuenta)', 'The detail (for those who want to see the math)')) + '</div>' +
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
          '<div class="cm-note" style="font-size:12px;color:var(--os-ink-3);margin-top:8px">' + esc(L('El tamaño lo calcula una fórmula fija, nunca la IA.', 'The size comes from a fixed formula, never from the AI.')) + '</div></div>' +
        riskHtml(m) +
        '<div class="cm-cell"><div class="cm-t">🗓 ' + esc(L('Revisión y confianza', 'Review and confidence')) + '</div>' +
          '<div class="cm-kv"><span>' + esc(L('Revisar el', 'Review on')) + '</span><span>' + esc(day(b.review_date)) + '</span></div>' +
          '<div class="cm-kv"><span>' + esc(L('Confianza del comité', 'Committee confidence')) + chip('committee_confidence') + '</span><span>' + pct(b.confidence) + '</span></div>' +
          '<div class="cm-kv"><span>' + esc(L('Conclusiones usadas', 'Conclusions used')) + '</span><span>' + esc(((m.inputs || {}).n_claims) || 0) + '</span></div>' +
          '<div class="cm-kv"><span>' + esc(L('Contradicciones', 'Contradictions')) + '</span><span>' + esc(((m.inputs || {}).n_contradictions) || 0) + '</span></div>' +
          (window.KhipuResearch ? '<div style="margin-top:12px"><button class="cm-btn ghost" onclick="window.KhipuResearch.open(\'' + esc(m.entity_id) + '\')">🔬 ' + esc(L('Ver la investigación', 'See the research')) + '</button></div>' : '') +
        '</div>' +
      '</div></div>' +
      '<div class="cm-disc">⚖️ ' + esc(isEn() ? (m.disclaimer_en || '') : (m.disclaimer_es || '')) + '</div>';
  }

  function conclusionsHtml(b) {
    var k = b.key_conclusions || [];
    if (!k.length) return '';
    return '<div class="cm-callout" style="margin-top:12px;padding:12px 14px;background:var(--os-surface-2);background:color-mix(in srgb,var(--os-good) 8%,transparent)">' +
      '<div class="cm-t" style="color:var(--cm-good);margin-bottom:4px">✅ ' + esc(L('Conclusiones del comité', 'Committee conclusions')) + '</div>' +
      '<ol class="cm-list" style="margin-left:16px">' + k.map(function (c) {
        return '<li>' + esc(isEn() ? (c.text_en || c.text_es) : c.text_es) + refs(c.refs) + '</li>'; }).join('') + '</ol></div>';
  }
  function debateNote(b) {
    var d = b.debate;
    if (!d) return '';
    if (d.no_research) return '<div class="cm-callout" style="' + tint(C.warn, 10) + '">⚠ ' +
      esc(L('No hubo análisis: ' + (d.reason_es || 'no hay investigación') + '. Sin investigación los analistas no tienen nada que debatir. Revisa 🩺 Sistema → IA y vuelve a correr el comité (los analistas investigarán primero).',
        'No analysis happened: ' + (d.reason_en || 'no research') + '. Without research the analysts have nothing to debate. Check 🩺 System → AI and run the committee again (the analysts will research first).')) + '</div>';
    if (d.ai) return '<div class="cm-note" style="margin-top:10px;font-size:12px;color:var(--cm-ai)">🧠 ' +
      esc(L(d.n_ai + ' analistas razonaron con IA y hubo ' + d.n_rebuttals + ' réplica(s)' + (d.seconds ? ' · ' + Math.round(d.seconds) + ' s de debate' : '') + '. Sus cifras pasaron el guardián.',
        d.n_ai + ' analysts reasoned with AI with ' + d.n_rebuttals + ' rebuttal(s)' + (d.seconds ? ' · ' + Math.round(d.seconds) + ' s of debate' : '') + '. Their figures passed the guardian.')) + '</div>';
    return '<div class="cm-callout" style="' + tint(C.warn, 10) + '">⚠ ' +
      esc(L('Este comité corrió SIN razonamiento de IA' + (d.reason_es ? ' (' + d.reason_es + ')' : '') + ': los analistas solo leyeron sus conclusiones guardadas. Revisa 🩺 Sistema → IA y vuelve a correrlo.',
        'This committee ran WITHOUT AI reasoning' + (d.reason_en ? ' (' + d.reason_en + ')' : '') + ': the analysts only read their saved conclusions. Check 🩺 System → AI and run it again.')) + '</div>';
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
        '<div class="cm-note" style="font-size:11.5px;color:var(--os-ink-3);margin-top:6px">' + esc((r.source || '') + (r.as_of ? ' · ' + r.as_of : '')) + '</div>'
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
    var goClients = window.KhipuClients && window.KhipuClients.open ? '<div style="margin-top:12px"><button class="cm-btn ghost" onclick="window.KhipuCommittee.close();window.KhipuClients.open()">👥 ' + esc(L('Ir a Clientes', 'Go to Clients')) + '</button></div>' : '';
    var head = '<div class="cm-cell" style="box-shadow:var(--os-shadow),inset 0 0 0 1.5px ' + (bad ? 'color-mix(in srgb,var(--cm-warn-fill) 45%,transparent)' : 'color-mix(in srgb,var(--os-good) 40%,transparent)') + '"><div class="cm-t">🧾 ' +
      esc(bad ? L('Orden NO preparada', 'Order NOT prepared') : L('Orden preparada', 'Prepared order')) + (pv.mode || (m && m.client_mode) ? ' · ' + esc(badge(pv.mode ? { mode: pv.mode } : m.client_mode)) : '') + '</div>';
    if (pv.redacted) {
      return head + '<div class="cm-kv"><span>' + esc(L('Estado', 'Status')) + '</span><span>' + esc(pvStatus(pv.status)) + '</span></div>' +
        '<div class="cm-note">' + esc(L('Detalle y montos visibles con tu PIN.', 'Details and amounts visible with your PIN.')) + '</div></div>';
    }
    if (bad) {
      return head + '<div class="cm-note" style="color:var(--cm-warn)">' + esc(T(pv, 'error') || summary || L('No se pudo preparar la orden.', 'Could not prepare the order.')) + '</div>' + pvChecks(pv) +
        (m && m.status === 'proposed' ? '<div class="cm-note" style="margin-top:6px">' + esc(L('El memo sigue propuesto: corrige el límite o el problema y vuelve a aprobar, o recházalo.', 'The memo is still proposed: fix the limit or the problem and approve again, or reject it.')) + '</div>' : '') + '</div>';
    }
    var note = pv.status === 'pending_approval' ? L('Falta tu aprobación final en 👥 Clientes → Aprobaciones para ejecutarla.', 'Your final approval in 👥 Clients → Approvals is still needed to execute it.')
      : pv.status === 'previewed' ? L('Previsualizada: se confirma en Clientes dentro de 5 minutos o caduca.', 'Previewed: confirm it in Clients within 5 minutes or it expires.')
      : PV_SENT[pv.status] ? L('Orden enviada al bróker.', 'Order sent to the broker.') : '';
    return head + '<div class="cm-note">' + esc(summary) + '</div>' +
      '<div class="cm-kv"><span>' + esc(L('Estado', 'Status')) + '</span><span>' + esc(pvStatus(pv.status)) + '</span></div>' +
      (pv.checks || []).map(function (c) { return '<div class="cm-kv"><span>' + (c.ok ? (c.warn ? '⚠️ ' : '✅ ') : '⛔ ') + esc(c.name) + '</span><span style="white-space:normal">' + esc(isEn() ? (c.detail_en || c.detail || '') : (c.detail || '')) + '</span></div>'; }).join('') +
      (note ? '<div class="cm-note" style="margin-top:8px;color:' + (pv.status === 'pending_approval' || pv.status === 'previewed' ? C.warn : C.good) + '">' + esc(note) + '</div>' : '') +
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


  // ── SALA DEL COMITÉ: puestos + conversación (research/deliberation.py) ──
  // Los mensajes llegan del servidor a medida que ocurre cada etapa; aquí se
  // revelan de a uno (≈1 s) para que se pueda leer el debate "en vivo".
  var STANCE = { 'for': [C.good, 'A FAVOR', 'FOR'], against: [C.bad, 'EN CONTRA', 'AGAINST'], neutral: [C.neu, 'NEUTRAL', 'NEUTRAL'] };
  var KIND = { open: ['Apertura', 'Opening'], position: ['Postura', 'Position'], rebuttal: ['Réplica', 'Rebuttal'], moderate: ['Moderación', 'Moderation'],
    data: ['Dato', 'Data'], verdict: ['Veredicto', 'Verdict'], reply: ['Respuesta', 'Reply'] };
  var DESK = [['market', '📡', 'Mesa de mercado', 'Market desk'], ['risk_officer', '🛡️', 'Oficial de riesgo', 'Risk officer'],
    ['mandate', '👤', 'Mandato', 'Mandate'], ['quant', '🧮', 'Núcleo cuantitativo', 'Quant core'], ['chair', '🏛', 'Presidencia', 'Chair']];

  // ── LOS AGENTES SON MASCOTAS (2026-10-09): cada puesto se dibuja con la burbuja de su agente
  // (engine/mascot.js) y una insignia chica abajo a la derecha con el objeto de su rol. Varios puestos
  // comparten mascota (p. ej. el Técnico lleva precio, riesgos, mesa de mercado y oficial de riesgo):
  // la insignia y el rol escrito los distinguen. Sin mascot.js → círculo con el emoji del puesto.
  var GLYPH = { fundamental: 'coin', macro: 'pct', crypto: 'btc', technical: 'chart', news: 'paper', supply_chain: 'link',
    geopolitical: 'globe', risk_observation: 'warn', market: 'signal', risk_officer: 'shield', quant: 'calc', chair: 'gavel', mandate: 'case' };
  // insignia: círculo de superficie (centro 51,51 en un viewBox 22×22) + el objeto del rol en el color de la mascota
  function glyphSvg(k, col) {
    var w = 'fill="none" stroke="' + col + '" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"';
    var t = function (s, fs) { return '<text x="51" y="' + (51 + fs * 0.36) + '" text-anchor="middle" font-size="' + fs + '" font-weight="800" font-family="system-ui,sans-serif" fill="' + col + '">' + s + '</text>'; };
    var g = '';
    switch (k) {
      case 'coin': g = t('$', 11); break;
      case 'btc': g = t('₿', 11); break;
      case 'pct': g = t('%', 10); break;
      case 'chart': g = '<path d="M45 55l4-5 3 3 5-7" ' + w + '/>'; break;
      case 'paper': g = '<rect x="45.5" y="46" width="11" height="10" rx="1.2" ' + w + '/><path d="M48 49.5h6M48 52.5h4" ' + w + '/>'; break;
      case 'link': g = '<rect x="44.5" y="48.5" width="7" height="5" rx="2.5" ' + w + '/><rect x="50.5" y="48.5" width="7" height="5" rx="2.5" ' + w + '/>'; break;
      case 'globe': g = '<circle cx="51" cy="51" r="5.5" ' + w + '/><path d="M45.5 51h11M51 45.5q-3 5.5 0 11q3-5.5 0-11" ' + w + '/>'; break;
      case 'warn': g = '<path d="M51 45.5l5.5 10h-11Z" ' + w + '/><path d="M51 49v3" ' + w + '/>'; break;
      case 'signal': g = '<circle cx="51" cy="53" r="1.3" fill="' + col + '"/><path d="M47.5 50.5q3.5-3.5 7 0M45.5 48q5.5-5.5 11 0" ' + w + '/>'; break;
      case 'shield': g = '<path d="M51 45l5 2v3.5q0 4-5 6q-5-2-5-6V47Z" ' + w + '/>'; break;
      case 'calc': g = '<rect x="46.5" y="45.5" width="9" height="11" rx="1.5" ' + w + '/><path d="M48.8 48.5h4.4M49 52h.1M53 52h.1M49 54.5h.1M53 54.5h.1" ' + w + '/>'; break;
      case 'gavel': g = '<path d="M46 56.5h6M48.5 52.5l6-6M47 48l4.5-4.5M52 53l4.5-4.5M47 48l5 5" ' + w + '/>'; break;
      case 'case': g = '<rect x="45" y="48" width="12" height="8" rx="1.5" ' + w + '/><path d="M49 48v-2h4v2" ' + w + '/>'; break;
    }
    return '<svg viewBox="40 40 22 22" width="100%" height="100%" aria-hidden="true" focusable="false">' +
      '<circle cx="51" cy="51" r="10.5" style="fill:var(--os-surface,#FFFFFF)"/>' + g + '</svg>';
  }
  // la burbuja de una mascota (por id de mascota: analista, radar, cadena, tecnico, comite)
  function mascotHtml(id, size, state, emo) {
    var M = window.KhipuMascot, h = '';
    if (M && M.svg) { try { h = M.svg(id, size, { state: state || 'idle' }); } catch (e) { h = ''; } }
    return h || '<span class="cm-mfb" aria-hidden="true" style="display:inline-flex;align-items:center;justify-content:center;flex:none;width:' + size + 'px;height:' + size +
      'px;border-radius:50%;background:var(--os-surface-2,#F2F2F7);color:var(--os-ink,#111216);font-size:' + Math.round(size * 0.5) + 'px;line-height:1">' + esc(emo || '🤖') + '</span>';
  }
  // el avatar de un PUESTO: su mascota + insignia del rol (sin insignia por debajo de 28 px: no se distingue)
  function avatarHtml(seat, size, state, emoji) {
    size = Math.max(12, Math.round(Number(size) || 32));
    var mid = mascotOf(seat), g = size >= 28 ? GLYPH[seat] : null, b = Math.round(size * 0.38), off = -Math.round(b * 0.12);
    var emo = emoji || (AG[seat] && AG[seat][0]) || EMO[seat] || '🤖';
    return '<span class="cm-mav" data-mascot="' + esc(mid) + '" style="position:relative;display:inline-block;flex:none;line-height:0;vertical-align:middle;width:' + size + 'px;height:' + size + 'px">' +
      mascotHtml(mid, size, state, emo) +
      (g ? '<span class="cm-badge" title="' + esc(roleOf(seat)) + '" style="position:absolute;right:' + off + 'px;bottom:' + off + 'px;width:' + b + 'px;height:' + b +
        'px;line-height:0;border-radius:50%;box-shadow:0 1px 3px rgba(17,18,40,.22)">' + glyphSvg(GLYPH[seat], mascotColor(mid)) + '</span>' : '') + '</span>';
  }

  function tx(m) { return isEn() ? (m.text_en || m.text_es) : m.text_es; }
  function nm(m) { return isEn() ? (m.name_en || m.name_es) : m.name_es; }
  function shortName(n) { var x = String(n || '').replace(/^Analista (de |del )?/i, '').replace(/ analyst$/i, ''); return x.charAt(0).toUpperCase() + x.slice(1); }

  function seatsHtml(seats, msgs, withClient) {
    var spoke = {}, last = msgs.length ? msgs[msgs.length - 1].seat : null;
    msgs.forEach(function (m) { spoke[m.seat] = m.stance || spoke[m.seat] || 'spoke'; });
    function who(seat, fallback) {
      var n = mascotName(mascotOf(seat)), r = roleOf(seat, fallback ? shortName(fallback) : '');
      return '<div class="cm-sn">' + esc(n) + '</div>' + (r && r !== n ? '<div class="cm-sr">' + esc(r) + '</div>' : '');
    }
    var agents = (seats || []).map(function (st) {
      var full = L(st.name_es, st.name_en);
      if (st.absent) {
        return '<div class="cm-seat absent" title="' + esc(seatLabel(st.seat, full) + ' · ' + L('Sin conclusiones sobre esta empresa: este agente no participó (falta para el quórum).', 'No conclusions on this company: this agent did not take part (needed for quorum).')) + '">' +
          '<div class="cm-av">' + avatarHtml(st.seat, 52, 'idle', st.emoji) + '</div>' + who(st.seat, full) +
          '<div class="cm-ss" style="color:var(--cm-warn)">' + esc(L('ausente', 'absent')) + '</div></div>';
      }
      var said = spoke[st.seat], sc = STANCE[st.stance] || STANCE.neutral, talk = last === st.seat;
      var rec = st.n_scored > 0 ? st.hits + '/' + st.n_scored + ' ✓' : L('sin historial', 'no record');
      return '<div class="cm-seat' + (said ? ' spoke' : '') + (talk ? ' talk' : '') + '" style="--cm-ring:' + fill(sc[0]) + '" title="' +
          esc(seatLabel(st.seat, full) + ' · ' + L('Fiabilidad ', 'Reliability ') + pct(st.reliability) + ' · ' + rec) + '">' +
        '<div class="cm-av">' + avatarHtml(st.seat, 52, talk ? 'talk' : 'idle', st.emoji) + '</div>' + who(st.seat, full) +
        '<div class="cm-ss"' + (said ? ' style="color:' + sc[0] + '"' : '') + '>' + esc(said ? L(sc[1], sc[2]) : L('por hablar', 'to speak')) + '</div>' +
        '<div class="cm-rec">' + esc(rec) + '</div></div>';
    }).join('');
    var desk = DESK.filter(function (d) { return d[0] !== 'mandate' || withClient; }).map(function (d) {
      var said = spoke[d[0]], talk = last === d[0];
      return '<div class="cm-seat' + (said ? ' spoke' : '') + (talk ? ' talk' : '') + '" style="--cm-ring:' + C.accent + '" title="' + esc(seatLabel(d[0], L(d[2], d[3]))) + '">' +
        '<div class="cm-av">' + avatarHtml(d[0], 52, talk ? 'talk' : 'idle', d[1]) + '</div>' + who(d[0], L(d[2], d[3])) + '</div>';
    }).join('');
    return '<div class="cm-table">' + (agents || '<div class="cm-note" style="align-self:center">' + esc(L('Sentando a los agentes…', 'Seating the agents…')) + '</div>') +
      '<div class="cm-brk"></div>' + desk + '</div>';
  }

  function bubbleHtml(m, isNew) {
    var st = m.stance && STANCE[m.stance];
    var col = st ? st[0] : (m.seat === 'chair' ? C.ai : C.accent);
    var k = KIND[m.kind] || [m.kind || '', m.kind || ''];
    var src = m.source && (m.source.title || m.source.url)
      ? '<span class="cm-src">📎 ' + (m.source.url ? '<a href="' + esc(window.safeUrl ? window.safeUrl(m.source.url) : m.source.url) + '" target="_blank" rel="noopener">' + esc(m.source.title || m.source.url) + '</a>' : esc(m.source.title)) +
        (m.source.date ? ' · ' + esc(day(m.source.date)) : '') + '</span>' : '';
    var mn = mascotName(mascotOf(m.seat)), role = roleOf(m.seat, shortName(nm(m)));
    return '<div class="cm-bub' + (isNew ? ' new' : '') + '"><div class="cm-bav">' + avatarHtml(m.seat, 32, 'idle', m.emoji || '🤖') + '</div>' +
      '<div class="cm-btx" style="--cm-sc:' + fill(col) + '"><div class="cm-bh"><b>' + esc(mn) + '</b>' +
      (role && role !== mn ? '<span class="cm-role">· ' + esc(role) + '</span>' : '') +
      (st ? '<span class="cm-tag" style="' + tint(col, 14) + '">' + esc(L(st[1], st[2])) + '</span>' : '') +
      '<span>' + esc(L(k[0], k[1])) + '</span>' +
      (m.ai ? '<span class="cm-tag" style="' + tint(C.ai, 14) + '" title="' + esc(L('Razonado por IA a partir de su evidencia; cifras verificadas por el guardián', 'Reasoned by AI from its evidence; figures checked by the guardian')) + '">🧠 ' + esc(L('IA', 'AI')) + (m.secs ? ' · ' + Math.round(m.secs) + ' s' : '') + '</span>' : '') +
      '</div>' + bodyText(m) + refs(m.refs) + src + '</div></div>';
  }

  function bodyText(m) {
    var t = esc(tx(m));
    if (m.ai && m.kind === 'position') {           // 1ª línea = titular
      var i = t.indexOf('\n');
      if (i > 0) t = '<b class="cm-hl">' + t.slice(0, i) + '</b>' + t.slice(i);
    }
    return t.replace(/\n/g, '<br>');
  }

  // quién "está pensando" en cada etapa sin mensaje propio
  var STAGE_SEAT = { live: 'market', risk: 'risk_officer', scoring: 'quant', chair: 'chair', saving: 'committee', client: 'mandate' };
  function typingHtml(msgs, total, stage) {
    var next = total > msgs.length ? S._allMsgs[msgs.length] : null;
    var whoSeat = next ? next.seat : STAGE_SEAT[stage] || null;
    var who = next ? seatLabel(next.seat, nm(next)) : stage === 'chair' ? seatLabel('chair') : '';
    var what = next ? L('está hablando', 'is speaking') : stage === 'chair' ? L('está redactando el veredicto (suele tardar 20–90 s)', 'is writing the verdict (usually 20–90 s)')
      : stage === 'live' ? L('📡 consultando el precio en vivo', '📡 fetching the live price') : stage === 'risk' ? L('🛡️ midiendo el riesgo con precios reales', '🛡️ measuring risk with real prices')
      : stage === 'scoring' ? L('🧮 haciendo la cuenta', '🧮 running the numbers')
      : stage === 'research' ? L('🔬 los analistas están investigando (puede tardar unos minutos)', '🔬 the analysts are researching (may take a few minutes)')
      : stage === 'debate' ? L('🧠 los analistas están razonando con IA', '🧠 the analysts are reasoning with AI')
      : stage === 'saving' ? L('💾 guardando la propuesta', '💾 saving the proposal') : L('el comité se está reuniendo', 'the committee is gathering');
    var face = whoSeat ? avatarHtml(whoSeat, 26, 'think', next && next.emoji)
      : (stage === 'research' || stage === 'debate') && window.KhipuMascot && window.KhipuMascot.stack ? window.KhipuMascot.stack(['analista', 'radar', 'cadena', 'tecnico'], 22)
      : mascotHtml('comite', 26, 'think', '🏛');
    return '<div class="cm-typing">' + face + '<span>' + esc(who ? who + ' ' + what : what) + '</span><span class="cm-dots" aria-hidden="true"><i></i><i></i><i></i></span></div>';
  }

  // msgs visibles · seats · ¿en vivo? · etapa
  function roomHtml(all, shown, seats, live, stage, withClient) {
    S._allMsgs = all;
    var msgs = all.slice(0, shown);
    var t = { 'for': 0, against: 0, neutral: 0 };
    (seats || []).forEach(function (st) { if (msgs.some(function (m) { return m.seat === st.seat && m.kind === 'position'; })) t[st.stance]++; });
    return '<div class="cm-room"><div class="cm-t">' + mascotHtml('comite', 22, live ? 'talk' : 'idle', '🏛') + ' ' + esc(L('Sala del comité', 'Committee room')) + chip('committee_room') +
      (live ? '<span class="cm-onair"><i></i>' + esc(L('EN VIVO', 'LIVE')) + '</span>' : '') +
      '<span class="cm-count"><span style="color:var(--cm-good)">👍 ' + t['for'] + '</span><span style="color:var(--cm-bad)">👎 ' + t.against + '</span>' +
        '<span style="color:var(--os-ink-2)">✋ ' + t.neutral + '</span></span></div>' +
      seatsHtml(seats, msgs, withClient) +
      '<div class="cm-feed" id="cm-feed">' + msgs.map(function (m, i) { return bubbleHtml(m, i === S.animIdx); }).join('') +
      (live || shown < all.length ? typingHtml(msgs, all.length, stage) : '') + '</div>' +
      (!live && shown >= all.length && all.length ? '<div style="text-align:right;margin-top:8px"><button class="cm-btn ghost" id="cm-replay">▶ ' + esc(L('Repetir la sesión', 'Replay the session')) + '</button></div>' : '') +
      '</div>';
  }

  function scrollFeed() { var f = document.getElementById('cm-feed'); if (f) f.scrollTop = f.scrollHeight; }

  // Revela de a un mensaje mientras haya pendientes (en vivo o repetición)
  function tickReveal() {
    var all = S._allMsgs || [];
    if (S.shown < all.length) { S.animIdx = S.shown; S.shown++; paintLive(); }
    else if (!S.busy && S.replay) { stopReveal(); render(); }
  }
  function startReveal() { if (!S.reveal) S.reveal = setInterval(tickReveal, 1000); }
  function stopReveal() { if (S.reveal) { clearInterval(S.reveal); S.reveal = null; } S.replay = null; S.animIdx = -1; }

  function liveHtml() {
    var p = S.progress || {}, done = p.done || [], cur = p.stage || 'claims';
    var list = STAGES.filter(function (st) { return (st[0] !== 'client' || S.clientId) && (st[0] !== 'research' || cur === 'research' || done.indexOf('research') >= 0); });
    var el = S.runStart ? (Date.now() - S.runStart) / 1000 : (p.elapsed_s || 0);
    var strip = '<div class="cm-strip">' + list.map(function (st) {
      var cls = done.indexOf(st[0]) >= 0 ? 'd' : st[0] === cur ? 'c' : '';
      return '<span class="' + cls + '">' + (cls === 'd' ? '✓ ' : '') + st[1] + ' ' + esc(L(st[4], st[5])) + '</span>'; }).join('') +
      '<span class="cm-clock">⏱ ' + fmtT(el) + '</span></div>';
    return strip + roomHtml(p.messages || [], S.shown, p.seats || [], true, cur, !!S.clientId) +
      '<div class="cm-note" style="margin:-4px 0 12px">' + esc(el > 420
        ? L('Está tardando más de lo normal (la IA puede estar lenta). Puedes cerrar esta ventana: el comité sigue trabajando y el resultado aparecerá aquí al volver.', 'Taking longer than usual (the AI may be slow). You can close this window: the committee keeps working and the result will appear here when you come back.')
        : L('Un comité con análisis real tarda: 1–3 minutos si ya hay investigación, 3–6 si los analistas investigan primero. Puedes cerrar esta ventana: sigue trabajando.', 'A committee with real analysis takes time: 1–3 minutes if research exists, 3–6 if the analysts research first. You can close this window: it keeps working.')) + '</div>';
  }
  // repinta SOLO la sala (sin reconstruir el formulario ni perder el foco)
  function paintLive() {
    var box = document.getElementById('cm-live');
    if (!box) { render(); return; }
    if (S.busy) box.innerHTML = liveHtml();
    else if (S.memo) box.innerHTML = memoRoomHtml(S.memo);
    wireRoom(box); scrollFeed();
  }
  function wireRoom(root) {
    (root || document).querySelectorAll('[data-ref]').forEach(function (x) { x.onclick = function () { openRef(x.getAttribute('data-ref')); }; });
    var rp = document.getElementById('cm-replay');
    if (rp) rp.onclick = function () { S.replay = true; S.shown = 0; S.animIdx = -1; paintLive(); startReveal(); };
  }
  function memoRoomHtml(m) {
    var b = m.memo || {}, tr = b.transcript || [];
    if (!tr.length) return '<div class="cm-room"><div class="cm-note">' + esc(L('Este memo es anterior a la sala del comité: vuelve a correrlo para ver el debate entre los analistas.', 'This memo predates the committee room: run it again to see the debate between the analysts.')) + '</div></div>';
    var shown = S.replay ? S.shown : tr.length;
    return roomHtml(tr, shown, b.seats || [], false, null, !!m.client_id);
  }

  // ── PANTALLA DE PROGRESO: pasos reales que reporta el servidor ──────────
  var STAGES = [
    ['research', '🔬', 'Los analistas investigan con datos en vivo', 'The analysts research with live data', 'Investigación', 'Research'],
    ['claims', '📚', 'Leyendo las conclusiones de los analistas IA', 'Reading the AI analysts\' conclusions', 'Analistas', 'Analysts'],
    ['live', '📡', 'Consultando precio y datos en vivo', 'Fetching live price and data', 'En vivo', 'Live'],
    ['risk', '📉', 'Midiendo el riesgo con 1 año de precios reales', 'Measuring risk with 1 year of real prices', 'Riesgo', 'Risk'],
    ['client', '👤', 'Revisando la cuenta y el mandato del cliente', 'Checking the client account and mandate', 'Cliente', 'Client'],
    ['scoring', '🧮', 'Calculando convicción y tamaño de la posición', 'Computing conviction and position size', 'Cuenta', 'Math'],
    ['debate', '🗣', 'Debate: cada analista razona con IA', 'Debate: each analyst reasons with AI', 'Debate', 'Debate'],
    ['chair', '🏛', 'La presidencia del Comité redacta el memo con IA (suele tardar 20–90 s)', 'The Committee chair writes the memo with AI (usually 20–90 s)', 'Presidencia', 'Chair'],
    ['saving', '💾', 'Guardando la propuesta', 'Saving the proposal', 'Guardar', 'Save'],
  ];
  function fmtT(s) { s = Math.max(0, Math.round(s || 0)); return Math.floor(s / 60) + ':' + ('0' + (s % 60)).slice(-2); }
  function startPoll(mid) {
    S.running = { memo_id: mid, entity: S.entity }; S.busy = true;
    if (!S.runStart) S.runStart = Date.now();
    var n = 0, errs = 0;
    if (S.poll) clearInterval(S.poll);
    function stop(msg) {
      clearInterval(S.poll); S.poll = null; S.busy = false; S.running = null; S.progress = null; S.runStart = null;
      // lo que no se alcanzó a leer en vivo se sigue revelando sobre el memo final
      var pend = (S._allMsgs || []).length - S.shown;
      if (pend > 0 && S.shown > 0) { S.replay = true; startReveal(); } else stopReveal();
      if (msg) S.msg = msg;
    }
    S.poll = setInterval(function () {
      n++;
      loadMemo(mid).then(function (m) {
        if (!S.running || S.running.memo_id !== mid) return;
        if (!m || !m.memo_id) {                     // error HTTP (401/404/500/sin red): decirlo, no girar para siempre
          errs++;
          if (errs >= 3) { stop({ bad: true, text: errText(m || {}) }); render(); }
          return;
        }
        errs = 0;
        if (m.status && m.status !== 'running') {
          stop(m.status === 'failed' ? { bad: true, text: L('El comité no pudo terminar: ', 'The committee could not finish: ') + (T(m, 'error') || '') } : null);
          loadEntity(S.entity);
        } else if (n > 450) {                        // 15 min
          stop({ bad: true, text: L('El comité sigue sin terminar tras 15 minutos. Vuelve a intentar más tarde (revisa 🩺 Sistema → IA).', 'The committee has not finished after 15 minutes. Try again later (check 🩺 System → AI).') }); render();
        } else {
          S.progress = m.progress || S.progress;
          if (document.getElementById('cm-live')) paintLive(); else render();
          startReveal();
        }
      }).catch(function () { errs++; if (errs >= 3) { stop({ bad: true, text: L('Sin conexión con el servidor.', 'No connection to the server.') }); render(); } });
    }, 2000);
  }

  function runCommittee() {
    var inp = document.getElementById('cm-ent');
    var q = (inp && inp.value || '').trim();
    if (!q) { S.msg = { bad: true, text: L('Elige una empresa de la lista.', 'Pick a company from the list.') }; render(); return; }
    var picked = window.KhipuPick ? window.KhipuPick.value(inp) : q;   // solo opciones de la lista
    if (picked === '__portfolio__') { S.tab = 'portfolio'; S.msg = null; render(); return; }
    if (!picked) { S.msg = { bad: true, text: L('«' + q + '» no está en la lista: escribe y elige una empresa de las sugerencias.', '“' + q + '” is not in the list: type and pick a company from the suggestions.') }; render(); return; }
    q = picked;
    var sel = document.getElementById('cm-cli'); S.clientId = sel ? sel.value : '';
    var ent = q;   // id del grafo elegido de la lista
    var body = { entity: ent, actor: actor() };
    if (S.clientId) body.client_id = S.clientId;
    stopReveal(); S.shown = 0; S.animIdx = -1;
    S.busy = true; S.msg = null; S.memo = null; S.progress = null; S.runStart = Date.now(); render();
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
      var note = m.client_id ? L('Se preparará una orden que TAMBIÉN tendrás que aprobar en Clientes antes de ejecutarse (salvo que el servidor tenga activada la auto-aprobación de cuentas SIMULADAS).', 'An order will be prepared that you will ALSO have to approve in Clients before it executes (unless the server has auto-approval of PAPER accounts turned on).') : L('Sin cliente: solo se registra tu aprobación.', 'No client: only your approval is recorded.');
      var T = window.KhipuToast, live = m.client_mode && (m.client_mode.paper === false || m.client_mode.mode === 'live');
      var side = { BUY: 'buy', ADD: 'buy', TRIM: 'sell', SELL: 'sell' }[m.decision];
      // pop-up de confirmación (engine/toast.js); DINERO REAL exige marcar la casilla
      var ask = T && T.confirm ? T.confirm({ title: L('¿Aprobar la propuesta del comité?', 'Approve the committee proposal?'), side: side,
          sideLabel: decLabel(m.decision), mode: m.client_id ? (live ? 'live' : 'paper') : undefined,
          rows: [[L('Empresa', 'Company'), (m.label || '') + (m.symbol ? ' · ' + m.symbol : '')], [L('Decisión', 'Decision'), what]],
          note: note, requireCheck: live ? L('Entiendo que esta orden usa DINERO REAL.', 'I understand this order uses REAL MONEY.') : null,
          confirmLabel: L('Aprobar', 'Approve') })
        : Promise.resolve(window.confirm(L('¿Aprobar la propuesta del comité?\n\n', 'Approve the committee proposal?\n\n') + what + mode + '\n\n' + note));
      ask.then(function (ok) { if (ok) sendDecision(kind, body); });
      return;
    } else {
      var why = window.prompt(L('¿Por qué la rechazas? (opcional)', 'Why do you reject it? (optional)'), '');
      if (why === null) return;
      body.reason = why;
    }
    sendDecision(kind, body);
  }
  function sendDecision(kind, body) {
    var m = S.memo; if (!m) return;
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
      return '<tr><td>' + avatarHtml(a.agent_type, 22, 'idle') + esc(ag(a.agent_type)) + '</td><td>' + a.n_scored + '</td><td>' + a.hits + '</td>' +
        '<td>' + (enough ? pct(a.hit_rate) : '<span style="color:var(--os-ink-3)">' + (a.n_scored ? pct(a.hit_rate) + ' · ' : '') + esc(L('poca historia', 'little history')) + '</span>') + '</td>' +
        '<td>' + (a.brier == null ? '—' : a.brier.toFixed(3)) + '</td><td>' + pct(a.reliability) + '</td>' +
        '<td>' + (a.interim && a.interim.n_scored ? pct(a.interim.hit_rate) + ' (n=' + a.interim.n_scored + ')' : '—') + '</td><td>' + (a.n_na || 0) + '</td></tr>';
    }).join('');
    var sel = '<select id="cm-agsel"><option value="__all">' + esc(L('Todos los agentes', 'All agents')) + '</option>' +
      agents.map(function (a) { return '<option value="' + esc(a.agent_type) + '"' + (S.agentSel === a.agent_type ? ' selected' : '') + '>' + esc(ag(a.agent_type)) + '</option>'; }).join('') + '</select>';
    var recent = ((S.recent || {}).outcomes || []).map(function (o) {
      var r = RES[o.result] || RES['n/a'];
      return '<div class="cm-hist static"><b style="color:' + r[0] + '">' + esc(L(r[1], r[2])) + '</b> · ' + esc(nodeLabel(o.entity_id)) + ' · ' + esc(ag(o.agent_type)) + ' · ' + esc(hz(o.horizon)) + ' · ' + esc(o.checkpoint) +
        '<div style="color:var(--os-ink-3);font-size:12px;margin-top:2px;white-space:normal;overflow-wrap:anywhere">' + esc(T(o, 'reason') || '') + '</div></div>';
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
    // colores del gráfico = tokens de Khipus OS del tema actual (Chart.js pinta en canvas: no entiende var())
    var cs = null; try { cs = window.getComputedStyle(document.getElementById('cm-ov')); } catch (e) { cs = null; }
    var tok = function (k, dflt) { var v = cs ? String(cs.getPropertyValue(k) || '').trim() : ''; return v || dflt; };
    var dark = document.body && document.body.classList && document.body.classList.contains('dark');
    var accent = tok('--os-accent', dark ? '#4C8DF6' : '#2F6BEA'), surf = tok('--os-surface', dark ? '#17181F' : '#FFFFFF');
    var grid = tok('--os-line', dark ? 'rgba(255,255,255,.07)' : 'rgba(17,18,22,.08)'), ink = tok('--os-ink-3', dark ? '#6E7080' : '#8D90A0'), ink2 = tok('--os-ink-2', dark ? '#A6A8B5' : '#5B5E6B');
    var font = tok('--os-font', 'system-ui, sans-serif');
    try {
      S.chart = new window.Chart(document.getElementById('cm-cal').getContext('2d'), {
        type: 'scatter',
        data: { datasets: [
          { label: L('Acierto real por tramo', 'Actual hit rate by bucket'), data: buckets.map(function (b) { return { x: Math.round(b.mean_conf * 1000) / 10, y: Math.round(b.hit_rate * 1000) / 10, n: b.n }; }),
            showLine: true, borderColor: accent, backgroundColor: accent, borderWidth: 2, pointRadius: 5, pointHoverRadius: 7, pointBorderColor: surf, pointBorderWidth: 2 },
          { label: L('Calibración perfecta', 'Perfect calibration'), data: [{ x: 0, y: 0 }, { x: 100, y: 100 }], showLine: true, borderColor: ink, borderDash: [4, 4], borderWidth: 1, pointRadius: 0, pointHoverRadius: 0 }] },
        options: { responsive: true, maintainAspectRatio: false, animation: false,
          scales: { x: { min: 0, max: 100, title: { display: true, text: L('Confianza declarada (%)', 'Stated confidence (%)'), color: ink2, font: { family: font, size: 12 } }, grid: { color: grid }, ticks: { color: ink2, font: { family: font, size: 11 } } },
            y: { min: 0, max: 100, title: { display: true, text: L('Acierto real (%)', 'Actual hit rate (%)'), color: ink2, font: { family: font, size: 12 } }, grid: { color: grid }, ticks: { color: ink2, font: { family: font, size: 11 } } } },
          plugins: { legend: { labels: { color: ink2, boxWidth: 10, font: { size: 12, family: font } } },
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
  // ── PIZARRA: conclusiones de todas las empresas investigadas (sin IA) ────
  function renderBoard(body) {
    if (!S.board) body.innerHTML = '<div class="cm-cell"><div class="cm-note"><span class="cm-spin">◌</span> ' + esc(L('Armando la pizarra…', 'Building the board…')) + '</div></div>';
    else paintBoard(body);
    getJSON('/api/committee/board?limit=60').then(function (d) {
      if (S.tab !== 'board') return;
      if (d._status !== 200) { body.innerHTML = '<div class="cm-cell"><div class="cm-note" style="color:var(--cm-warn)">' + esc(errText(d)) + '</div></div>'; return; }
      S.board = d.items || [];
      paintBoard(body);
    }).catch(function () { body.innerHTML = '<div class="cm-cell"><div class="cm-note">' + esc(L('Sin conexión con el servidor.', 'No connection to the server.')) + '</div></div>'; });
  }
  function ageTxt(iso) {
    var h = (Date.now() - new Date(iso).getTime()) / 3.6e6;
    if (isNaN(h)) return '';
    if (h < 1) return L('hace minutos', 'minutes ago');
    if (h < 48) return L('hace ' + Math.round(h) + ' h', Math.round(h) + ' h ago');
    return L('hace ' + Math.round(h / 24) + ' días', Math.round(h / 24) + ' days ago');
  }
  function paintBoard(body) {
    var items = S.board || [], f = S.boardFilter || 'all';
    var shown = items.filter(function (x) { return f === 'all' || (f === 'for' ? x.overall_conviction >= 15 : f === 'against' ? x.overall_conviction <= -15 : Math.abs(x.overall_conviction) < 15); });
    var flt = [['all', L('Todas', 'All')], ['for', '👍 ' + L('A favor', 'Favorable')], ['against', '👎 ' + L('En contra', 'Unfavorable')], ['mixed', '✋ ' + L('Sin consenso', 'No consensus')]];
    body.innerHTML = '<div class="cm-cell"><div class="cm-note" style="margin-bottom:12px">' +
      esc(L('Todas las empresas que los analistas ya investigaron, ordenadas por convicción (de más favorable a menos). Cada fila resume el argumento más fuerte a favor y en contra, y la última decisión del comité. Pulsa 🏛 para que el comité debata esa empresa.',
        'Every company the analysts already researched, ranked by conviction (most to least favorable). Each row summarizes the strongest argument for and against, and the latest committee decision. Press 🏛 to have the committee debate that company.')) + chip('conviction') + '</div>' +
      '<div class="cm-bar"><div class="cm-tabs" role="radiogroup" aria-label="' + esc(L('Filtrar', 'Filter')) + '">' + flt.map(function (x) { return '<button class="cm-tab' + (f === x[0] ? ' on' : '') + '" data-f="' + x[0] + '" role="radio" aria-checked="' + (f === x[0]) + '">' + esc(x[1]) + '</button>'; }).join('') + '</div>' +
        '<button class="cm-btn ghost" id="cm-refresh" style="margin-left:auto"' + (S.refreshing ? ' disabled' : '') + ' title="' + esc(L('Pone a investigar hasta 3 empresas: las de investigación más vieja (más de 7 días) o, si la pizarra está vacía, empresas clave de la cadena de IA. Gasta presupuesto de IA.', 'Puts up to 3 companies under research: those with the oldest research (over 7 days) or, if the board is empty, key AI supply-chain companies. Uses AI budget.')) + '">' +
        (S.refreshing ? '<span class="cm-spin">◌</span> ' + esc(L('Investigando…', 'Researching…')) : '🔬 ' + esc(L('Actualizar investigación', 'Refresh research'))) + '</button></div>' +
      (S.refreshMsg ? '<div class="cm-msg" role="status" style="margin:12px 0 0;' + tint(S.refreshMsg.bad ? C.warn : C.good) + '">' + esc(S.refreshMsg.text) + '</div>' : '') + '</div>' +
      (shown.length ? shown.map(boardRow).join('') : '<div class="cm-cell"><div class="cm-note">' + esc(items.length ? L('Nada en este filtro.', 'Nothing in this filter.') :
        L('Todavía no hay empresas investigadas. Escribe una en la pestaña 🏛 Comité y pulsa «Correr comité»: los analistas la investigarán primero.', 'No researched companies yet. Type one in the 🏛 Committee tab and press “Run committee”: the analysts will research it first.')) + '</div></div>');
    body.querySelectorAll('[data-f]').forEach(function (b) { b.onclick = function () { S.boardFilter = b.getAttribute('data-f'); paintBoard(body); }; });
    var rf = document.getElementById('cm-refresh'); if (rf) rf.onclick = function () { refreshBoard(body); };
    body.querySelectorAll('[data-go]').forEach(function (b) { b.onclick = function () {
      S.entity = b.getAttribute('data-go'); S.tab = 'committee'; S.memo = null; S.msg = null; render(); loadEntity(S.entity); }; });
    body.querySelectorAll('[data-rs]').forEach(function (b) { b.onclick = function () { if (window.KhipuResearch) window.KhipuResearch.open(b.getAttribute('data-rs')); }; });
  }
  function refreshBoard(body) {
    if (S.refreshing) return;
    S.refreshing = true; S.refreshMsg = null; paintBoard(body);
    getJSON('/api/committee/board/refresh', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ actor: actor() }) }).then(function (d) {
      if (d._status !== 202) { S.refreshing = false; S.refreshMsg = { bad: true, text: d._status === 429 ? L('Ya pediste varias actualizaciones esta hora. Espera un poco.', 'You already asked for several refreshes this hour. Wait a bit.') : errText(d) }; paintBoard(body); return; }
      var jobs = d.jobs || [];
      if (!jobs.length) { S.refreshing = false; S.refreshMsg = { bad: false, text: L('Todo está al día: ninguna investigación tiene más de 7 días.', 'Everything is up to date: no research is older than 7 days.') }; paintBoard(body); return; }
      var names = jobs.map(function (j) { return nodeLabel(j.entity_id); }).join(', ');
      S.refreshMsg = { bad: false, text: L('Los analistas están investigando ' + names + ' (una tras otra, ~1-2 min cada una). La pizarra se actualiza sola.', 'The analysts are researching ' + names + ' (one after another, ~1-2 min each). The board updates by itself.') };
      paintBoard(body);
      var ids = jobs.map(function (j) { return j.job_id; }), n = 0;
      if (S.refreshPoll) clearInterval(S.refreshPoll);
      S.refreshPoll = setInterval(function () {
        n++;
        Promise.all(ids.map(function (id) { return getJSON('/api/research/jobs/' + encodeURIComponent(id)).catch(function () { return {}; }); })).then(function (rs) {
          var done = rs.filter(function (r) { return r.status === 'done' || r.status === 'partial' || r.status === 'deferred' || r.status === 'failed' || r._status === 404; }).length;
          var failed = rs.filter(function (r) { return r.status === 'failed'; }).length;
          var partial = rs.filter(function (r) { return r.status === 'partial'; }).length;
          var deferred = rs.filter(function (r) { return r.status === 'deferred'; }).length;
          if (done >= ids.length || n > 60) {
            clearInterval(S.refreshPoll); S.refreshPoll = null; S.refreshing = false;
            var parts = [];
            if (failed) parts.push(L(failed + ' investigación(es) fallaron: ábrelas con 🔬 para ver el motivo.', failed + ' research job(s) failed: open them with 🔬 to see why.'));
            if (partial) parts.push(L(partial + ' quedaron PARCIALES (algún analista no respondió): ábrelas con 🔬 y pulsa «Completar lo que falta».', partial + ' are PARTIAL (some analyst did not answer): open them with 🔬 and press “Complete the missing part”.'));
            if (deferred) parts.push(L(deferred + ' en espera por presupuesto: se reanudan solas mañana.', deferred + ' waiting for budget: they resume automatically tomorrow.'));
            S.refreshMsg = parts.length ? { bad: !!(failed || partial), text: parts.join(' ') }
              : { bad: false, text: L('Listo: investigación actualizada.', 'Done: research refreshed.') };
          } else {
            S.refreshMsg = { bad: false, text: L('Investigando… ' + done + ' de ' + ids.length + ' listas.', 'Researching… ' + done + ' of ' + ids.length + ' done.') };
          }
          if (S.tab === 'board') renderBoard(document.getElementById('cm-body'));
        });
      }, 20000);
    }).catch(function () { S.refreshing = false; S.refreshMsg = { bad: true, text: L('Sin conexión con el servidor.', 'No connection to the server.') }; paintBoard(body); });
  }

  function boardRow(x) {
    var v = Math.round(x.overall_conviction || 0), col = v >= 15 ? C.good : v <= -15 ? C.bad : C.neu;
    var arg = function (a, icon) {
      if (!a) return '';
      return '<div class="cm-note" style="margin-top:8px;font-size:12.5px;display:flex;gap:8px;align-items:flex-start"><span style="flex:none">' + icon + '</span>' + avatarHtml(a.agent_type, 20, 'idle') +
        '<span style="min-width:0"><b style="color:var(--os-ink)">' + esc(ag(a.agent_type)) + '</b> · ' + esc(hz(a.horizon)) + ': ' + esc(isEn() ? a.text_en : a.text_es) + '</span></div>';
    };
    var m = x.memo, d = m ? (DEC[m.decision] || [C.neu, m.decision, m.decision]) : null;
    return '<div class="cm-cell">' +
      '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">' +
        '<span class="cm-score" style="color:' + col + '">' + (v > 0 ? '+' : '') + v + '</span>' +
        '<b style="font-size:15px;overflow-wrap:anywhere">' + esc(x.label) + '</b>' +
        (d ? '<span class="cm-pill" style="' + tint(d[0]) + '">🏛 ' + esc(L(d[1], d[2])) + ' · ' + esc(ageTxt(m.created_at)) + (m.ai ? '' : ' · ' + esc(L('sin IA', 'no AI'))) + '</span>' : '') +
        '<span class="cm-pill">' + x.n_claims + ' ' + esc(L('concl.', 'concl.')) + ' · ' + x.agents.length + ' ' + esc(L('analistas', 'analysts')) + (x.n_contradictions ? ' · ⚡' + x.n_contradictions : '') + ' · ' + esc(ageTxt(x.last_research)) + '</span>' +
        '<span style="margin-left:auto;display:flex;gap:8px"><button class="cm-btn" data-go="' + esc(x.entity_id) + '">🏛 ' + esc(L('Comité', 'Committee')) + '</button>' +
        (window.KhipuResearch ? '<button class="cm-btn ghost" data-rs="' + esc(x.entity_id) + '" title="' + esc(L('Investigación IA', 'AI research')) + '" aria-label="' + esc(L('Investigación IA', 'AI research')) + '">🔬</button>' : '') + '</span></div>' +
      (m && (isEn() ? m.conclusion_en : m.conclusion_es) ? '<div class="cm-note" style="margin-top:8px;font-size:13px;color:var(--os-ink)">✅ ' + esc(isEn() ? (m.conclusion_en || m.conclusion_es) : m.conclusion_es) + '</div>' : '') +
      arg(x.best_for, '👍') + arg(x.best_against, '👎') + '</div>';
  }

  function renderLearn(body) {
    var P = function (es, en) { return '<p>' + L(es, en) + '</p>'; };
    // quién es quién: las 5 mascotas y los puestos que ocupa cada una en la mesa
    var CREW = [['analista', 'fundamental', 'Fundamentales y macro', 'Fundamentals and macro'], ['radar', 'news', 'Noticias, geopolítica y cripto', 'News, geopolitics and crypto'],
      ['cadena', 'supply_chain', 'Cadena de suministro', 'Supply chain'], ['tecnico', 'technical', 'Precio, riesgos, mesa de mercado y oficial de riesgo', 'Price, risks, market desk and risk officer'],
      ['comite', 'chair', 'La cuenta (núcleo cuantitativo), el mandato y la presidencia', 'The math (quant core), the mandate and the chair']];
    body.innerHTML = '<div class="cm-cell cm-learn">' +
      '<div class="cm-t">' + esc(L('Quién se sienta en la mesa', 'Who sits at the table')) + chip('committee_room') + '</div>' +
      '<div class="cm-agents">' + CREW.map(function (c) {
        return '<div class="cm-agent">' + mascotHtml(c[0], 34, 'idle', AG[c[1]] ? AG[c[1]][0] : (EMO[c[1]] || '🤖')) + '<span style="min-width:0"><b>' + esc(mascotName(c[0])) + '</b><span class="r">' + esc(L(c[2], c[3])) + '</span></span></div>';
      }).join('') + '</div>' +
      '<h4>1 · ' + esc(L('Los agentes investigan (Fase 2)', 'Agents research (Phase 2)')) + '</h4>' +
      P('Cada agente —el Analista (fundamentales y macro), el Radar (noticias, geopolítica y cripto), la Cadena (cadena de suministro) y el Técnico (precio y riesgos)— escribe conclusiones con evidencia, un plazo y una confianza calculada. Nunca dicen "compra" o "vende".',
        'Each agent —the Analyst (fundamentals and macro), the Radar (news, geopolitics and crypto), the Chain (supply chain) and the Technical agent (price and risks)— writes conclusions with evidence, a horizon and a computed confidence. They never say "buy" or "sell".') +
      '<h4>2 · ' + esc(L('Se guarda una foto del momento', 'A snapshot of the moment is saved')) + '</h4>' +
      P('Al escribir cada conclusión se anota el precio de la acción y del S&P 500 (SPY) y las fechas en que se va a revisar: a 7 y 30 días si es de corto plazo, a 30, 90 y 180 días si es de mediano, a 90, 180 y 365 días si es de largo. Las "estructurales" (más de 5 años) no se califican.',
        'When each conclusion is written, the stock and S&P 500 (SPY) prices are recorded along with the dates it will be checked: 7 and 30 days for short term, 30, 90 and 180 days for medium term, 90, 180 and 365 days for long term. "Structural" ones (over 5 years) are not scored.') +
      '<h4>3 · ' + esc(L('Se califica con precios reales', 'It is scored with real prices')) + chip('hit_rate') + '</h4>' +
      P('Una vez al día el sistema revisa las fechas vencidas: compara cuánto se movió la acción contra el mercado. Si el agente dijo "positivo" y la acción le ganó al mercado por más de 2 %, es un acierto. Nada de IA en este paso: solo precios. Cada calificación queda guardada y no se borra.',
        'Once a day the system checks due dates: it compares how much the stock moved versus the market. If the agent said "positive" and the stock beat the market by more than 2%, it is a hit. No AI in this step: only prices. Every score is stored and never deleted.') +
      '<h4>4 · ' + esc(L('La confianza se corrige (calibración)', 'Confidence gets corrected (calibration)')) + chip('calibration') + chip('brier') + '</h4>' +
      P('Si un agente dice 80 % de confianza pero acierta solo la mitad de las veces, sus próximas conclusiones de ~80 % valen menos. Con pocos casos casi no se corrige: hace falta historia para aprender.',
        'If an agent says 80% confidence but is right only half the time, its next ~80% conclusions count for less. With few cases it barely corrects: learning needs history.') +
      '<h4>5 · ' + esc(L('El Comité decide… y tú apruebas', 'The Committee decides… and you approve')) + chip('conviction') + chip('position_sizing') + chip('committee_decision') + '</h4>' +
      P('El Comité suma las conclusiones pesadas por su confianza calibrada y por el historial de cada agente, descuenta las contradicciones, mide el riesgo real de la acción y calcula un tamaño con una fórmula fija. Su presidencia (IA) escribe el memo (tesis, riesgos, quién disiente, qué nos demostraría equivocados), pero no puede cambiar el tamaño ni inventar cifras. Nada se ejecuta sin tu aprobación, y para dinero de clientes hay una segunda aprobación en Clientes.',
        'The Committee adds up conclusions weighted by calibrated confidence and each agent\'s track record, discounts contradictions, measures the stock\'s real risk and computes a size with a fixed formula. Its chair (AI) writes the memo (thesis, risks, who dissents, what would prove us wrong), but it cannot change the size or invent figures. Nothing executes without your approval, and client money needs a second approval in Clients.') +
      '<div class="cm-disc" style="margin:16px 0 0">⚖️ ' + esc(L('Es una herramienta de apoyo: puede equivocarse y no es asesoría financiera personalizada.', 'It is a support tool: it can be wrong and it is not personalized financial advice.')) + '</div></div>';
  }

  // ── API pública ───────────────────────────────────────────────────────────
  function open(entityId) {
    ensureExplain();
    // Investigación IA (z-index 7700) tapaba al comité (7650): se cierra al abrirlo.
    // «Ver la investigación» / [C#] la vuelven a abrir ENCIMA (y al cerrarla se vuelve aquí).
    var rov = document.getElementById('rs-ov');
    if (rov && rov.classList.contains('show') && window.KhipuResearch && window.KhipuResearch.close) window.KhipuResearch.close();
    var ov = shell(); ov.classList.add('show');
    S.tab = (entityId || S.running) ? 'committee' : 'board'; S.msg = null; S.memo = null; S.history = []; S.deciding = false;
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

  window.KhipuCommittee = {
    // avatar(puesto, emoji?, mini?) → la MASCOTA del agente + insignia del rol (mini = 20 px sin insignia;
    // un número = tamaño en px). Lo usa engine/khipu_chat.js cuando mascot.js no cargó.
    avatar: function (seat, emoji, mini) { try { return avatarHtml(seat, typeof mini === 'number' ? mini : (mini ? 20 : 40), 'idle', emoji); } catch (e) { return ''; } },
    open: open, close: close,
    // abre directo en una pestaña: 'board' | 'committee' | 'portfolio' | 'history' | 'learn'
    openTab: function (tab) { open(); S.tab = tab || 'board'; render(); } };
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { var ov = document.getElementById('cm-ov'); if (ov && ov.classList.contains('show')) close(); } });
})();
