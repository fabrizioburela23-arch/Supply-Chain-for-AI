/* ============================================================================
   engine/fincard.js — DOSSIER FINANCIERO de una empresa (Etapa G, 2026-07-11)
   Estilo investingvisuals que pidió Fabrizio: una tarjeta con small-multiples
   de indicadores reales — crecimiento de ingresos, dilución, free cash flow,
   acción, valuación EV/Ventas, deuda/capital, márgenes y ROE.

   window.openFinCard(idOrTicker[, labelHint]) — overlay NEXUS. Funciona para
   TODOS los nodos (2026-09-28: "que todas las empresas tengan dossier y que la
   info se actualice en vivo"):
     · Cotiza → franja EN VIVO (/api/company/live/<t>, refresco cada 60 s)
       + 8 mini-gráficos anuales (/api/findossier/<t>, fuente dicha tal cual)
       + acción ~90 d (/api/candles/<t>). Sin estados → franja + acción + nota
       clara: NUNCA un overlay vacío. Botón "⇄ Comparar en Análisis".
     · No cotiza (privada, filial, comprada, organismo) → ficha del catálogo
       + franja en vivo del DUEÑO si n.listing.parent_ticker + noticias en vivo
       (GDELT: se revisa cada 5 min, pero /api/news/gdelt guarda cada búsqueda
       30 min en el server — la UI lo dice así) + Historia de la ontología.
     · La franja dice la hora REAL del precio (market_time), no la de la
       consulta; "EN VIVO" solo si la sesión está en curso (quoteInfo).
   Honestidad: nada se inventa; lo que falta se dice ("—" o nota).
   Los intervalos se limpian al cerrar o al abrir otra ficha.
   ============================================================================ */
(function () {
  'use strict';

  var NEON = '#00E0FF', DOWN = '#FF4D6A', UP = '#2BE38B', INK = '#9BA6C4';
  var LIVE_MS = 60 * 1000, NEWS_MS = 5 * 60 * 1000;
  var charts = [];
  var _gen = 0;          // sube en cada apertura/cierre: las respuestas viejas se ignoran
  var _timers = [];      // intervalos vivos de la ficha abierta
  var _st = {};          // estado de la ficha abierta (último perfil, botones…)

  // bilingüe (regla del proyecto): idioma activo = window.LANG → eco_lang
  function isEn() { var l = window.LANG; if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = null; } } return l === 'en'; }
  function L(es, en) { return isEn() ? en : es; }

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function base() { return window.BASE || ''; }
  function safeUrl(u) { return (typeof u === 'string' && /^https?:\/\//i.test(u)) ? u : null; }
  function num(v) { return (typeof v === 'number' && isFinite(v)) ? v : null; }

  // nombres de fuentes, dichos tal cual (honestidad: siempre decir de dónde sale)
  var SRC = { fmp: 'Financial Modeling Prep', yahoo: 'Yahoo Finance', yahoo_chart: 'Yahoo Finance', alphavantage: 'Alpha Vantage', finnhub: 'Finnhub' };
  function srcName(s) { return s ? (SRC[s] || String(s)) : null; }
  // lista de fuentes sin repetir ("Yahoo Finance + Finnhub")
  function srcList(arr, fallback) {
    var out = [];
    (Array.isArray(arr) ? arr : []).forEach(function (x) { var nm = srcName(x); if (nm && out.indexOf(nm) < 0) out.push(nm); });
    if (!out.length && fallback) { var f = srcName(fallback); if (f) out.push(f); }
    return out;
  }
  // el server manda el motivo en los dos idiomas (reason / reason_en)
  function reasonOf(d) { return d ? (isEn() ? (d.reason_en || d.reason) : (d.reason || d.reason_en)) : null; }
  // estado del mercado (Yahoo marketState) → etiqueta honesta
  function mktState(st) {
    st = String(st || '').toUpperCase();
    if (!st) return null;
    if (st === 'REGULAR') return { open: true, es: 'mercado abierto', en: 'market open' };
    if (st.indexOf('PRE') === 0) return { open: false, es: 'pre-apertura', en: 'pre-market' };
    if (st.indexOf('POST') === 0) return { open: false, es: 'después del cierre', en: 'after hours' };
    return { open: false, es: 'mercado cerrado', en: 'market closed' };
  }
  // ¿El precio es de la sesión en curso? `as_of` es cuándo lo CONSULTÓ el
  // server, no de cuándo es el precio: la hora real es `market_time`. Solo
  // quoteSummary de Yahoo trae marketState; con Finnhub o el gráfico de Yahoo
  // (respaldos) se deduce por la antigüedad del precio. Muchas bolsas fuera
  // de EE.UU. dan el precio con 15-20 min de retraso (delay_min si el server
  // lo manda). live: true = sesión en curso · false = último cierre · null =
  // la fuente no dice ni estado ni hora.
  var STALE_UNKNOWN_MS = 30 * 60 * 1000;     // sin estado de mercado: > 30 min → no es "en vivo"
  var STALE_OPEN_MS = 6 * 3600 * 1000;       // aun con mercado abierto: > 6 h → no es "de hoy"
  function quoteInfo(p) {
    p = p || {};
    var ms = mktState(p.market_state);
    var qt = p.market_time ? new Date(p.market_time) : null;
    if (qt && isNaN(qt.getTime())) qt = null;
    var age = num(p.quote_age_s) != null ? Math.max(0, p.quote_age_s * 1000) : null;
    if (age == null && qt) {
      // reloj del server (as_of) vs hora del precio: no depende del reloj del usuario
      var ref = p.as_of ? Date.parse(p.as_of) : NaN;
      age = Math.max(0, (isNaN(ref) ? Date.now() : ref) - qt.getTime());
    }
    var live;
    if (ms) live = ms.open && !(age != null && age > STALE_OPEN_MS);
    else live = age != null ? age <= STALE_UNKNOWN_MS : null;
    var dl = num(p.delay_min);
    return { ms: ms, qt: qt, age: age, live: live, delay: (dl != null && dl > 0) ? Math.round(dl) : null };
  }
  // "precio de las 14:32" (hoy) / "precio del 26 sep, 22:00" (otro día)
  function quoteWhen(d) {
    if (!d) return null;
    var sameDay = d.toDateString() === new Date().toDateString();
    var s;
    try {
      s = sameDay
        ? d.toLocaleTimeString(locale(), { hour: '2-digit', minute: '2-digit', hour12: false })
        : d.toLocaleString(locale(), { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false });
    } catch (e) { s = d.toISOString().slice(sameDay ? 11 : 0, 16).replace('T', ' '); }
    return sameDay ? L('precio de las ' + s, 'price as of ' + s) : L('precio del ' + s, 'price as of ' + s);
  }

  function ensureStyles() {
    if (document.getElementById('fincard-styles')) return;
    var css = `
#fc-ov{position:fixed;inset:0;z-index:6500;display:none;align-items:center;justify-content:center;
  background:rgba(3,6,12,.7);backdrop-filter:blur(4px);font-family:'Inter',system-ui,sans-serif}
#fc-ov.show{display:flex}
#fc{width:min(1060px,96vw);max-height:92vh;overflow-y:auto;border-radius:18px;color:#E8EDFB;
  background:radial-gradient(1000px 500px at 50% -10%,#0B1222 0%,#06090F 60%);
  border:1px solid rgba(122,158,255,.2);box-shadow:0 30px 80px rgba(0,0,0,.6);padding:22px 24px;box-sizing:border-box}
#fc .fc-hd{display:flex;align-items:baseline;gap:12px;margin-bottom:4px;flex-wrap:wrap}
#fc .fc-name{font-size:22px;font-weight:750}
#fc .fc-tk{font-family:'JetBrains Mono',monospace;font-size:12px;color:#7C87A3}
#fc .fc-acts{margin-left:auto;display:flex;gap:8px;align-items:center}
#fc .fc-close{margin-left:auto;width:32px;height:32px;border-radius:9px;cursor:pointer;
  border:1px solid rgba(122,158,255,.2);background:rgba(21,28,45,.7);color:#7C87A3;font-size:16px}
#fc .fc-close:hover{color:#E8EDFB}
#fc .fc-btn{height:32px;padding:0 12px;border-radius:9px;cursor:pointer;white-space:nowrap;
  border:1px solid rgba(0,224,255,.4);background:rgba(0,224,255,.08);color:#00E0FF;font-size:12px;font-weight:650}
#fc .fc-btn:hover{background:rgba(0,224,255,.16)}
#fc .fc-btn.sm{height:26px;padding:0 10px;font-size:11px;border-radius:7px}
#fc .fc-sub{font-size:11px;color:#5b6580;margin-bottom:16px;line-height:1.5}
#fc .fc-sub a,#fc .fc-foot a{color:#00E0FF;text-decoration:none}
#fc .fc-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
#fc .fc-cell{border:1px solid rgba(122,158,255,.14);border-radius:13px;background:rgba(11,18,34,.55);padding:13px 14px;min-width:0}
#fc .fc-wide{grid-column:1/-1}
#fc .fc-t{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#9BA6C4;
  display:flex;align-items:center;gap:7px;margin-bottom:2px;flex-wrap:wrap}
#fc .fc-t .fc-tr{margin-left:auto;font-size:9.5px;font-weight:500;letter-spacing:.02em;text-transform:none;color:#5b6580}
#fc .fc-d{font-size:9.5px;color:#5b6580;margin-bottom:8px}
#fc .fc-cv{position:relative;height:130px}
#fc .fc-note{padding:36px 10px;text-align:center;color:#7C87A3;font-size:12.5px;line-height:1.55}
#fc .fc-foot{margin-top:14px;font-size:9.5px;color:#5b6580;display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px}
#fc .fc-live{border:1px solid rgba(0,224,255,.22);border-radius:13px;margin:10px 0 12px;padding:11px 13px 9px;
  background:linear-gradient(180deg,rgba(0,224,255,.06),rgba(11,18,34,.55))}
#fc .fc-lv-hd{display:flex;align-items:center;gap:7px;flex-wrap:wrap;font-size:10.5px;color:#7C87A3;margin-bottom:8px}
#fc .fc-lv-hd b{color:#2BE38B;letter-spacing:.08em;font-size:10px}
#fc .fc-lv-hd b.off{color:#7C87A3}
#fc .fc-lv-hd .fc-lv-sym{margin-left:auto;font-family:'JetBrains Mono',monospace;color:#5b6580}
#fc .fc-lv-par{font-size:12px;color:#C9D4EC;margin:-2px 0 8px;display:flex;align-items:center;gap:8px;flex-wrap:wrap;line-height:1.45}
#fc .fc-lv-par em{font-style:normal;color:#7C87A3;font-size:10.5px}
#fc .fc-dot{width:8px;height:8px;border-radius:50%;background:#2BE38B;flex:0 0 8px;animation:fcPulse 2s infinite}
#fc .fc-dot.off{background:#5b6580;animation:none}
@keyframes fcPulse{0%{box-shadow:0 0 0 0 rgba(43,227,139,.55)}70%{box-shadow:0 0 0 7px rgba(43,227,139,0)}100%{box-shadow:0 0 0 0 rgba(43,227,139,0)}}
#fc .fc-lv-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
#fc .fc-tile{border:1px solid rgba(122,158,255,.12);border-radius:10px;background:rgba(6,9,15,.45);padding:8px 10px;cursor:pointer;min-width:0}
#fc .fc-tile:hover,#fc .fc-tile.sel{border-color:rgba(0,224,255,.45)}
#fc .fc-tl{font-size:9.5px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:#7C87A3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#fc .fc-tv{font-family:'JetBrains Mono',monospace;font-size:15px;font-weight:700;color:#E8EDFB;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#fc .fc-tv small{font-size:10px;color:#7C87A3;font-weight:500}
#fc .fc-tv.sm{font-size:13px}
#fc .fc-ts{font-size:10.5px;color:#7C87A3;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#fc .fc-up{color:#2BE38B}
#fc .fc-dn{color:#FF4D6A}
#fc .fc-na{color:#5b6580}
#fc .fc-rng{position:relative;height:4px;border-radius:2px;margin:8px 2px 3px;opacity:.85;
  background:linear-gradient(90deg,#FF4D6A,#9BA6C4,#2BE38B)}
#fc .fc-rng i{position:absolute;top:-3px;width:3px;height:10px;border-radius:2px;background:#E8EDFB;transform:translateX(-50%)}
#fc .fc-lv-x{font-size:11px;color:#8FA0C0;line-height:1.5;margin-top:8px;min-height:16px}
#fc .fc-flash{animation:fcFlash 1.2s ease-out}
@keyframes fcFlash{0%{background:rgba(0,224,255,.28)}100%{background:rgba(6,9,15,.45)}}
#fc .fc-kv{display:flex;justify-content:space-between;gap:12px;font-size:12.5px;padding:6px 0;border-bottom:1px solid rgba(122,158,255,.08)}
#fc .fc-kv span:first-child{color:#7C87A3;flex:0 0 auto}
#fc .fc-kv span:last-child{color:#E8EDFB;text-align:right;min-width:0;overflow-wrap:anywhere}
#fc .fc-p{font-size:12.5px;line-height:1.6;color:#C9D4EC;padding:4px 0}
#fc .fc-pl{font-size:9.5px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:#7C87A3;margin-top:8px}
#fc .fc-item{padding:7px 0;border-bottom:1px solid rgba(122,158,255,.07);font-size:12.5px;line-height:1.45}
#fc .fc-item:last-child{border-bottom:0}
#fc .fc-item a{color:#E8EDFB;text-decoration:none}
#fc .fc-item a:hover{color:#00E0FF;text-decoration:underline}
#fc .fc-meta{font-size:10.5px;color:#7C87A3;margin-top:2px}
@media (max-width:560px){
  #fc{padding:16px 14px;border-radius:14px}
  #fc .fc-name{font-size:18px}
  #fc .fc-grid{grid-template-columns:minmax(0,1fr)}
  #fc .fc-lv-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  #fc .fc-lv-hd .fc-lv-sym{margin-left:0}
}
@media (prefers-reduced-motion:reduce){#fc .fc-dot,#fc .fc-flash{animation:none}}
`;
    var st = document.createElement('style'); st.id = 'fincard-styles'; st.textContent = css;
    document.head.appendChild(st);
  }

  function ensureShell() {
    ensureStyles();
    var ov = document.getElementById('fc-ov');
    if (ov) return ov;
    ov = document.createElement('div');
    ov.id = 'fc-ov';
    ov.innerHTML = '<div id="fc"></div>';
    ov.addEventListener('click', function (e) {
      if (e.target === ov) { close(); return; }
      // tocar un dato de la franja en vivo → su explicación en lenguaje simple
      var t = e.target && e.target.closest ? e.target.closest('.fc-tile') : null;
      if (t && t.getAttribute('data-x')) {
        _st.xKey = t.getAttribute('data-x');
        showExplain();
      }
    });
    document.body.appendChild(ov);
    return ov;
  }

  function isShown() {
    var ov = document.getElementById('fc-ov');
    return !!(ov && ov.classList.contains('show'));
  }

  function stopTimers() {
    _timers.forEach(function (h) { try { clearInterval(h); } catch (e) {} });
    _timers = [];
  }

  // intervalo atado a la ficha abierta: se apaga solo si la cerraron desde fuera
  // (p.ej. _surface quita la clase .show sin llamar a close()) y no pide datos
  // con la pestaña del navegador oculta.
  function every(ms, fn, gen) {
    var h = setInterval(function () {
      if (gen !== _gen) { clearInterval(h); return; }
      if (!isShown()) { stopTimers(); return; }
      if (document.hidden) return;
      fn();
    }, ms);
    _timers.push(h);
  }

  function destroyCharts() {
    charts.forEach(function (c) { try { c.destroy(); } catch (e) {} });
    charts = [];
  }

  function close() {
    _gen++;
    stopTimers();
    var ov = document.getElementById('fc-ov');
    if (ov) ov.classList.remove('show');
    destroyCharts();
    _st = {};
  }

  function baseOpts(unit) {
    return {
      responsive: true, maintainAspectRatio: false, animation: { duration: 350 },
      plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
      scales: {
        x: { grid: { color: 'rgba(122,158,255,.07)' }, ticks: { color: INK, font: { size: 9 } } },
        y: { grid: { color: 'rgba(122,158,255,.07)' },
             ticks: { color: INK, font: { size: 9 },
                      callback: function (v) { return v + (unit || ''); } } },
      },
    };
  }

  function cell(title, desc, id) {
    return '<div class="fc-cell"><div class="fc-t">' + title + '</div>' +
      '<div class="fc-d">' + desc + '</div><div class="fc-cv"><canvas id="' + id + '"></canvas></div></div>';
  }

  function cellNote(id, title, msg) {
    var el = document.getElementById(id);
    if (el && el.parentNode && el.parentNode.parentNode) {
      el.parentNode.parentNode.innerHTML = '<div class="fc-t">' + title + '</div>' +
        '<div class="fc-note" style="padding:26px 8px">' + msg + '</div>';
    }
  }

  function noChartLib(id) {
    var el = document.getElementById(id); if (!el) return true;
    if (typeof Chart === 'undefined') {
      el.parentNode.innerHTML = '<div class="fc-note" style="padding:26px 8px">' +
        L('Los gráficos no cargaron (sin conexión a la librería). Recarga la página.', 'Charts did not load (chart library unavailable). Reload the page.') + '</div>';
      return true;
    }
    return false;
  }

  function lineChart(id, years, values, unit, colorPos) {
    if (noChartLib(id)) return;
    var el = document.getElementById(id);
    charts.push(new Chart(el, {
      type: 'line',
      data: { labels: years, datasets: [{
        data: values, borderColor: colorPos || NEON, borderWidth: 2, pointRadius: 2.5,
        pointBackgroundColor: colorPos || NEON, tension: .35, spanGaps: true,
        fill: true, backgroundColor: 'rgba(0,224,255,.06)',
      }] },
      options: baseOpts(unit),
    }));
  }

  function barChart(id, years, values, unit, colorFn) {
    if (noChartLib(id)) return;
    var el = document.getElementById(id);
    charts.push(new Chart(el, {
      type: 'bar',
      data: { labels: years, datasets: [{
        data: values, borderWidth: 0, borderRadius: 3,
        backgroundColor: values.map(function (v) { return colorFn ? colorFn(v) : NEON; }),
      }] },
      options: baseOpts(unit),
    }));
  }

  function posneg(v) { return v == null ? INK : v >= 0 ? UP : DOWN; }
  function posnegInv(v) { return v == null ? INK : v <= 0 ? UP : DOWN; }   // dilución: menos es mejor

  /* ── formatos ────────────────────────────────────────────────────────── */
  function locale() { return isEn() ? 'en-US' : 'es-ES'; }
  function fmtUsdB(b) {
    b = num(b); if (b == null) return null;
    var a = Math.abs(b);
    if (a >= 1000) return '$' + (b / 1000).toFixed(a >= 10000 ? 1 : 2) + 'T';
    if (a >= 1) return '$' + b.toFixed(a >= 100 ? 0 : 1) + 'B';
    return '$' + Math.round(b * 1000) + 'M';
  }
  function fmtPx(v) {
    v = num(v); if (v == null) return null;
    var a = Math.abs(v);
    var d = a >= 1000 ? 0 : a >= 1 ? 2 : 4;
    try { return v.toLocaleString(locale(), { minimumFractionDigits: d, maximumFractionDigits: d }); }
    catch (e) { return v.toFixed(d); }
  }
  function fmtPct(v, signed) {
    v = num(v); if (v == null) return null;
    return (signed && v > 0 ? '+' : '') + v.toFixed(Math.abs(v) >= 100 ? 0 : 1) + '%';
  }
  function fmtInt(v) {
    v = num(v); if (v == null) return null;
    try { return Math.round(v).toLocaleString(locale()); } catch (e) { return String(Math.round(v)); }
  }
  function fmtClock(d) {
    if (!d || isNaN(d.getTime())) return '—';
    try { return d.toLocaleTimeString(locale(), { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }); }
    catch (e) { return d.toTimeString().slice(0, 8); }
  }
  function ago(ms) {
    if (ms == null || isNaN(ms)) return '';
    var m = Math.max(0, Math.round((Date.now() - ms) / 60000));
    if (m < 1) return L('ahora', 'just now');
    if (m < 60) return L('hace ' + m + ' min', m + ' min ago');
    var h = Math.round(m / 60);
    if (h < 48) return L('hace ' + h + ' h', h + ' h ago');
    return L('hace ' + Math.round(h / 24) + ' d', Math.round(h / 24) + ' d ago');
  }
  // GDELT: "20260928T101500Z"; ontología: ISO-8601
  function parseWhen(s) {
    if (!s) return null;
    var m = /^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$/.exec(String(s));
    if (m) return Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6]);
    var t = Date.parse(s);
    return isNaN(t) ? null : t;
  }

  /* ── resolución: CUALQUIER id de nodo, ticker o nombre ──────────────────── */
  function allNodes() {
    try { if (typeof NODES !== 'undefined' && NODES && NODES.length) return NODES; } catch (e) {}
    return window.NODES || [];
  }
  function resolveNode(raw) {
    var s = String(raw == null ? '' : raw).trim();
    if (!s) return null;
    var NB = window.NODE_BY_ID || {};
    if (NB[s]) return NB[s];                                   // 1) id exacto
    var lc = s.toLowerCase(), arr = allNodes(), i;
    for (i = 0; i < arr.length; i++) {                         // 2) id / ticker exacto sin casing
      var n = arr[i];
      if (n && ((n.id && String(n.id).toLowerCase() === lc) || (n.mkt && String(n.mkt).toLowerCase() === lc))) return n;
    }
    for (i = 0; i < arr.length; i++) {                         // 2b) nombre exacto sin casing
      if (arr[i] && arr[i].label && String(arr[i].label).toLowerCase() === lc) return arr[i];
    }
    // 3) resolutor robusto. Un TICKER que no está en el catálogo (p.ej. el de
    //    una matriz extranjera) no debe caer en un parecido difuso: se exige
    //    confianza de ESCRITURA (85) para esos; los nombres usan _resolveNode.
    var tickerShaped = /^[A-Z0-9][A-Z0-9.\-=^&]{0,19}$/.test(s);
    if (tickerShaped) {
      if (window.KhipuResolve && window.KhipuResolve.find) {
        try { var r = window.KhipuResolve.find(s); if (r && r.node && r.score >= 85) return r.node; } catch (e) {}
      }
      return null;
    }
    if (window.BixbyVoice && window.BixbyVoice._resolveNode) {
      try { return window.BixbyVoice._resolveNode(s) || null; } catch (e) {}
    }
    return null;
  }

  // qué tipo de entidad es (para no llamar "privada pre-IPO" a la Fed)
  var ORG_CATS = { central_bank: 1, bis: 1, treasury: 1, derivatives_standards: 1, canal_authority: 1 };
  var FUND_CATS = { sovereign_fund: 1, pension_fund: 1 };
  function kindOf(n) {
    var ls = n.listing || {}, tk = String(n.ticker || '');
    if (ls.status === 'subsidiary') return { icon: '🏢', es: 'filial · no cotiza por separado', en: 'subsidiary · not separately listed' };
    if (ls.status === 'acquired') return { icon: '🔄', es: 'comprada · ya no cotiza', en: 'acquired · no longer listed' };
    if (ls.status === 'merged') return { icon: '🔄', es: 'fusionada · ya no cotiza', en: 'merged · no longer listed' };
    if (ls.status === 'defunct') return { icon: '⚫', es: 'cerró · ya no opera', en: 'defunct · no longer operating' };
    if (ORG_CATS[n.cat] || /banco central|sin fines de lucro|instituci[oó]n/i.test(tk)) return { icon: '🏛️', es: 'organismo · no emite acciones', en: 'public body · issues no shares' };
    if (FUND_CATS[n.cat] || /fondo soberano|fondo de pensi/i.test(tk)) return { icon: '🏦', es: 'fondo estatal · no cotiza', en: 'state-owned fund · not listed' };
    if (/estatal/i.test(tk)) return { icon: '🏛️', es: 'empresa estatal · no cotiza', en: 'state-owned company · not listed' };
    if (n.preipo || /pre-?ipo/i.test(tk)) return { icon: '🔒', es: 'empresa privada · pre-IPO', en: 'private company · pre-IPO' };
    if (/privad/i.test(tk)) return { icon: '🔒', es: 'empresa privada · no cotiza', en: 'private company · not listed' };
    return { icon: '🔒', es: 'sin cotización en bolsa registrada', en: 'no stock listing on record' };
  }
  function bi(n, k) { return isEn() ? (n[k + '_en'] || n[k]) : n[k]; }

  /* ── FRANJA EN VIVO (/api/company/live/<ticker>) ─────────────────────────── */
  var EXPL = {
    price: ['Último precio de la acción en su bolsa y en su moneda local, y cuánto cambió frente al cierre anterior: "hoy" si la sesión está en curso, "última sesión" si el mercado ya cerró. Arriba ves la hora exacta del precio; algunas bolsas lo dan con 15-20 min de retraso.',
            'Latest share price on its home exchange, in local currency, and its change vs. the previous close: "today" while the session is running, "last session" once the market has closed. The exact time of the price is shown above; some exchanges report it with a 15-20 min delay.'],
    mcap: ['Capitalización: lo que vale la empresa entera en bolsa (precio × acciones), convertido a dólares.',
           'Market cap: what the whole company is worth on the stock market (price × shares), converted to US dollars.'],
    emp: ['Personas empleadas a tiempo completo según el último reporte de la empresa.',
          'Full-time employees according to the company’s latest report.'],
    rev: ['Ingresos de los últimos 12 meses (TTM), en dólares: todo lo que vendió en el último año. Debajo, cuánto crecieron: frente al año anterior ("anual") o, si la fuente solo da eso, el último trimestre frente al mismo trimestre del año anterior.',
          'Revenue over the trailing twelve months (TTM), in US dollars: everything it sold in the last year. Below, how much it grew: vs. the prior year ("YoY") or, when the source only gives that, the last quarter vs. the same quarter a year earlier.'],
    margin: ['Margen neto: de cada $100 que vende, cuántos le quedan como ganancia final. Margen bruto: cuántos le quedan tras pagar lo que cuesta fabricar lo vendido.',
             'Net margin: out of every $100 in sales, how much is left as final profit. Gross margin: how much is left after paying what it costs to make what it sold.'],
    w52: ['Rango de 52 semanas: el precio más bajo y el más alto del último año. La marca blanca muestra dónde está hoy.',
          '52-week range: the lowest and highest price over the last year. The white marker shows where it is today.'],
    target: ['Precio objetivo: el promedio de lo que los analistas creen que valdrá la acción en ~12 meses (no es una garantía). Entre paréntesis, la distancia al precio de hoy.',
             'Target price: the average of where analysts think the stock will be in ~12 months (not a guarantee). In parentheses, the distance from today’s price.'],
    pe: ['P/E (precio / ganancia): cuántos años de ganancias actuales pagas al comprar la acción. Más alto = el mercado espera más crecimiento, o está cara. "Próx. 12 m" usa las ganancias que los analistas ESTIMAN para el próximo año.',
         'P/E (price / earnings): how many years of current earnings you pay when buying the stock. Higher = the market expects more growth, or it is expensive. "Forward" uses the earnings analysts ESTIMATE for the next year.'],
  };
  function showExplain() {
    var x = document.getElementById('fc-lv-x'); if (!x) return;
    var k = _st.xKey, e = k && EXPL[k];
    x.innerHTML = e ? 'ℹ️ ' + esc(L(e[0], e[1])) : esc(L('Toca un dato para ver qué significa.', 'Tap a figure to see what it means.'));
    var tiles = document.querySelectorAll('#fc .fc-tile');
    for (var i = 0; i < tiles.length; i++) tiles[i].classList.toggle('sel', tiles[i].getAttribute('data-x') === k);
  }

  var RECO = {
    strong_buy: ['compra fuerte', 'strong buy'], buy: ['compra', 'buy'], hold: ['mantener', 'hold'],
    underperform: ['bajo rendimiento', 'underperform'], sell: ['venta', 'sell'], strong_sell: ['venta fuerte', 'strong sell'],
  };

  // `value` llega YA escapado (HTML propio + esc()), por eso el title no se re-escapa
  function tile(key, label, value, sub, extra, small) {
    var has = value != null && value !== '';
    return '<div class="fc-tile" data-x="' + key + '"' + (key === 'price' ? ' id="fc-tile-px"' : '') + '>' +
      '<div class="fc-tl">' + esc(label) + '</div>' +
      '<div class="fc-tv' + (small ? ' sm' : '') + (has ? '' : ' fc-na') + '"' + (has ? ' title="' + String(value).replace(/<[^>]*>/g, '') + '"' : '') + '>' + (has ? value : '—') + '</div>' +
      (extra || '') +
      (sub ? '<div class="fc-ts">' + sub + '</div>' : '') + '</div>';
  }

  function liveTiles(p, qi) {
    var cur = p.currency ? ' <small>' + esc(p.currency) + '</small>' : '';
    var px = num(p.price), chg = num(p.change_pct);
    qi = qi || quoteInfo(p);
    // "hoy" SOLO si sabemos que la sesión está en curso; si cerró, "última
    // sesión"; si la fuente no lo dice, lo neutro: frente al cierre anterior
    var chgWhen = qi.live === true ? L('hoy', 'today')
      : qi.live === false ? L('última sesión', 'last session')
      : L('vs. cierre anterior', 'vs. prev. close');
    var chgHtml = chg != null
      ? '<span class="' + (chg >= 0 ? 'fc-up' : 'fc-dn') + '">' + (chg >= 0 ? '▲ ' : '▼ ') + esc(fmtPct(chg, true)) + '</span> ' + esc(chgWhen)
      : null;
    // rango 52 semanas con marca de posición
    var lo = num(p.week52_low), hi = num(p.week52_high), rng = null, bar = '';
    if (lo != null && hi != null) {
      rng = esc(fmtPx(lo)) + ' – ' + esc(fmtPx(hi));
      if (px != null && hi > lo) {
        var pos = Math.max(0, Math.min(100, (px - lo) / (hi - lo) * 100));
        bar = '<div class="fc-rng"><i style="left:' + pos.toFixed(1) + '%"></i></div>';
      }
    }
    var tgt = num(p.target_mean), up = (tgt != null && px) ? (tgt / px - 1) * 100 : null;
    var reco = p.recommendation && RECO[String(p.recommendation).toLowerCase()];
    var tgtSub = [];
    if (up != null) tgtSub.push('<span class="' + (up >= 0 ? 'fc-up' : 'fc-dn') + '">' + esc(fmtPct(up, true)) + '</span>');
    if (reco) tgtSub.push(esc(L(reco[0], reco[1])));
    var nm = num(p.profit_margin), gm = num(p.gross_margin);
    var pet = num(p.pe_trailing), pef = num(p.pe_forward);
    // TTM interanual si la fuente lo da (Finnhub); si no, el del último
    // trimestre vs el mismo del año anterior (Yahoo) — rotulado distinto
    var revG = num(p.revenue_growth), revGq = revG == null ? num(p.revenue_growth_q) : null;
    return '<div class="fc-lv-grid">' +
      tile('price', L('Precio', 'Price'), px != null ? esc(fmtPx(px)) + cur : null, chgHtml) +
      tile('mcap', L('Capitalización', 'Market cap'), esc(fmtUsdB(p.market_cap_usd_b)), L('en USD', 'in USD')) +
      tile('emp', L('Empleados', 'Employees'), esc(fmtInt(p.employees))) +
      tile('rev', L('Ingresos (12 m)', 'Revenue (TTM)'), esc(fmtUsdB(p.revenue_ttm_usd_b)),
           revG != null ? '<span class="' + (revG >= 0 ? 'fc-up' : 'fc-dn') + '">' + esc(fmtPct(revG, true)) + '</span> ' + L('anual', 'YoY')
             : revGq != null ? '<span class="' + (revGq >= 0 ? 'fc-up' : 'fc-dn') + '">' + esc(fmtPct(revGq, true)) + '</span> ' + L('últ. trimestre vs año ant.', 'last quarter YoY') : null) +
      tile('margin', L('Margen neto', 'Net margin'), nm != null ? '<span class="' + (nm >= 0 ? '' : 'fc-dn') + '">' + esc(fmtPct(nm)) + '</span>' : null,
           gm != null ? L('bruto ', 'gross ') + esc(fmtPct(gm)) : null) +
      tile('w52', L('Rango 52 sem.', '52-week range'), rng, null, bar, true) +
      tile('target', L('Precio objetivo', 'Target price'), tgt != null ? esc(fmtPx(tgt)) + cur : null, tgtSub.length ? tgtSub.join(' · ') : null) +
      tile('pe', 'P/E', pet != null ? esc(pet.toFixed(1)) + 'x' : null, pef != null ? L('próx. 12 m ', 'forward ') + esc(pef.toFixed(1)) + 'x' : null) +
      '</div>';
  }

  // opts: {ticker, parent:{name, ticker, child}}
  function renderLive(p, opts) {
    var el = document.getElementById('fc-live'); if (!el) return;
    opts = opts || {};
    var ok = !!(p && p.available);
    var stale = false;
    if (!ok && _st.lastLive) { p = _st.lastLive; stale = true; }   // no borrar lo último bueno
    var par = opts.parent;
    var parHtml = par
      ? '<div class="fc-lv-par">🔗 ' + esc(L('Cotiza a través de ', 'Listed through ')) + '<b>' + esc(par.name || par.ticker) + '</b>' +
          (par.name && par.name !== par.ticker ? ' <span class="fc-tk">(' + esc(par.ticker) + ')</span>' : '') +
          ' <em>' + esc(L('— cifras del dueño, no de ' + par.child, '— figures are the owner’s, not ' + par.child + '’s')) + '</em>' +
          '<button class="fc-btn sm" onclick="window._finCardOpenParent()">📊 ' + esc(L('Dossier del dueño', 'Owner’s dossier')) + '</button></div>'
      : '';

    if (!p || !p.available) {
      var why = reasonOf(p) || L('la fuente no respondió', 'the source did not answer');
      el.innerHTML = '<div class="fc-lv-hd"><span class="fc-dot off"></span><b class="off">' + esc(L('EN VIVO: NO DISPONIBLE AHORA', 'LIVE: UNAVAILABLE RIGHT NOW')) + '</b> · ' +
        esc(why) + ' · ' + esc(L('reintento automático cada 60 s', 'auto-retry every 60 s')) +
        '<span class="fc-lv-sym">' + esc(opts.ticker || '') + '</span></div>' + parHtml;
      return;
    }

    if (!stale) _st.lastLive = p;
    if (_st.nameFromLive && p.name && !opts.parent) {             // abierto con un ticker suelto → nombre real
      var nmEl = document.querySelector('#fc .fc-name');
      if (nmEl) nmEl.textContent = '📊 ' + p.name;
      _st.nameFromLive = false;
    }
    // `as_of` = cuándo lo consultó el server (NO la hora del precio)
    var when = p.as_of ? new Date(p.as_of) : new Date();
    if (isNaN(when.getTime())) when = new Date();
    var src = srcList(p.sources, p.source).join(' + ') || L('fuente no indicada', 'source not stated');
    var qi = quoteInfo(p);
    // hora REAL del precio, siempre a la vista (+ retraso de la bolsa si se conoce)
    var qParts = [];
    if (qi.ms) qParts.push(L(qi.ms.es, qi.ms.en));
    qParts.push(qi.qt ? quoteWhen(qi.qt) : L('la fuente no indica la hora del precio', 'the source does not state the price time'));
    if (qi.delay) qParts.push(L('con ' + qi.delay + ' min de retraso', qi.delay + '-min delayed'));
    var qHtml = qParts.map(esc).join(' · ');
    var hd;
    if (stale) {
      hd = '<span class="fc-dot off"></span><b class="off">' + esc(L('ÚLTIMO DATO', 'LAST DATA')) + '</b> · ' +
        esc(L('la fuente no respondió ahora; mostrando lo consultado a las ', 'the source did not answer just now; showing what we fetched at ')) +
        esc(fmtClock(when)) + ' · ' + qHtml + ' · ' + esc(src) + ' · ' + esc(L('reintento cada 60 s', 'retrying every 60 s'));
    } else if (qi.live === true) {
      hd = '<span class="fc-dot"></span><b>' + esc(L('EN VIVO', 'LIVE')) + '</b> · ' + esc(src) + ' · ' + qHtml + ' · ' +
        esc(L('consultado ', 'checked ')) + esc(fmtClock(when)) + ' · ' + esc(L('se refresca cada 60 s', 'refreshes every 60 s'));
    } else {
      // mercado cerrado, precio viejo, o sin forma de saberlo → nada de "EN VIVO"
      hd = '<span class="fc-dot off"></span><b class="off">' + esc(L('ÚLTIMO PRECIO', 'LAST PRICE')) + '</b> · ' + esc(src) + ' · ' + qHtml + ' · ' +
        esc(L('consultado ', 'checked ')) + esc(fmtClock(when)) + ' · ' + esc(L('se refresca cada 60 s', 'refreshes every 60 s'));
    }
    var sym = (p.symbol || opts.ticker || '') + (p.currency ? ' · ' + p.currency : '');
    el.innerHTML = '<div class="fc-lv-hd">' + hd + '<span class="fc-lv-sym">' + esc(sym) + '</span></div>' +
      parHtml + liveTiles(p, qi) + '<div class="fc-lv-x" id="fc-lv-x"></div>';
    showExplain();

    // destello si el precio cambió desde la última lectura
    var px = num(p.price);
    if (!stale && px != null && _st.lastPx != null && px !== _st.lastPx) {
      var t = document.getElementById('fc-tile-px'); if (t) t.classList.add('fc-flash');
    }
    if (!stale && px != null) _st.lastPx = px;
  }

  function liveLoading(ticker) {
    return '<div class="fc-live" id="fc-live"><div class="fc-lv-hd"><span class="fc-dot off"></span>' +
      esc(L('Conectando con el mercado en vivo…', 'Connecting to the live market…')) +
      '<span class="fc-lv-sym">' + esc(ticker || '') + '</span></div></div>';
  }

  function fetchLive(opts, gen) {
    fetch(base() + '/api/company/live/' + encodeURIComponent(opts.ticker))
      .then(function (r) { return r.json().catch(function () { return null; }); })
      .then(function (p) { if (gen === _gen) renderLive(p, opts); })
      .catch(function () { if (gen === _gen) renderLive(null, opts); });
  }

  function startLive(opts, gen) {
    fetchLive(opts, gen);
    every(LIVE_MS, function () { fetchLive(opts, gen); }, gen);
  }

  /* ── acción ~90 días (/api/candles) ───────────────────────────────────── */
  function loadCandles(ticker, id, gen) {
    fetch(base() + '/api/candles/' + encodeURIComponent(ticker))
      .then(function (r) { return r.json(); })
      .then(function (c) {
        if (gen !== _gen) return;
        if (!c || c.s !== 'ok' || !c.c || !c.c.length) {
          cellNote(id, L('📈 Acción', '📈 Stock'), L('Sin datos de mercado para este ticker.', 'No market data for this ticker.'));
          return;
        }
        var labels = (c.t || []).map(function (ts) { var dt = new Date(ts * 1000); return (dt.getMonth() + 1) + '/' + dt.getDate(); });
        var up = c.c[c.c.length - 1] >= c.c[0];
        lineChart(id, labels, c.c, '', up ? UP : DOWN);
      })
      .catch(function () {
        if (gen !== _gen) return;
        cellNote(id, L('📈 Acción', '📈 Stock'), L('No se pudo cargar el precio histórico — reintenta en un momento.', 'Could not load the price history — try again in a moment.'));
      });
  }

  /* ── cabecera y pie ─────────────────────────────────────────────────────── */
  function header(icon, name, tk, withCompare) {
    return '<div class="fc-hd"><span class="fc-name">' + icon + ' ' + esc(name) + '</span>' +
      '<span class="fc-tk">' + tk + '</span>' +
      '<div class="fc-acts">' +
        (withCompare ? '<button class="fc-btn" onclick="window._finCardCompare()" title="' +
          esc(L('Abre esta empresa en la pestaña Análisis para compararla con otras', 'Open this company in the Analysis tab to compare it with others')) + '">⇄ ' +
          esc(L('Comparar en Análisis', 'Compare in Analysis')) + '</button>' : '') +
        '<button class="fc-close" onclick="window._finCardClose()" title="' + esc(L('Cerrar', 'Close')) + '">✕</button>' +
      '</div></div>';
  }
  function footer(srcHtml) {
    return '<div class="fc-foot"><span>Khipus Finance AI · ' + esc(L('análisis, no asesoría financiera', 'analysis, not financial advice')) + '</span>' +
      '<span id="fc-foot-src">' + srcHtml + '</span></div>';
  }

  function catalogAbout(n) {
    if (!n) return '';
    var m = (window.NODE_META || {})[n.id] || {};
    var what = (isEn() ? m.desc_en : null) || m.desc || bi(n, 'role');
    var moat = bi(n, 'moat');
    if (!what && !moat) return '';
    return '<div class="fc-cell"><div class="fc-t">📖 ' + esc(L('Qué hace', 'What it does')) +
      '<span class="fc-tr">' + esc(L('catálogo Khipus', 'Khipus catalog')) + '</span></div>' +
      (what ? '<div class="fc-p">' + esc(what) + '</div>' : '') +
      (moat ? '<div class="fc-p" style="font-size:11.5px;color:#8FA0C0"><b style="color:#9BA6C4">' + esc(L('Ventaja (moat):', 'Moat:')) + '</b> ' + esc(moat) + '</div>' : '') +
      '</div>';
  }

  /* ── EMPRESA QUE COTIZA ─────────────────────────────────────────────────── */
  function renderListed(n, ticker, label, gen) {
    var ov = ensureShell();
    var fc = document.getElementById('fc');
    var canCompare = !!(n && n.id && window._openDossier);
    _st.cmp = canCompare ? { id: n.id, mkt: ticker } : null;
    fc.innerHTML =
      header('📊', label, esc(ticker) + ' · ' + esc(L('dossier financiero', 'financial dossier')), canCompare) +
      liveLoading(ticker) +
      '<div class="fc-sub" id="fc-src">' + esc(L('Buscando estados financieros anuales…', 'Looking up annual financial statements…')) + '</div>' +
      '<div id="fc-body"><div class="fc-note">' + esc(L('Cargando fundamentales…', 'Loading fundamentals…')) + '</div></div>' +
      footer(esc(L('fuentes: estados financieros + mercado en vivo', 'sources: financial statements + live market')));
    ov.classList.add('show');

    startLive({ ticker: ticker }, gen);

    fetch(base() + '/api/findossier/' + encodeURIComponent(ticker))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (gen !== _gen) return;
        if (!d || !d.available) { renderNoStatements(n, ticker, d, gen); return; }
        renderStatements(d, ticker, gen);
      })
      .catch(function () {
        if (gen !== _gen) return;
        renderNoStatements(n, ticker, { reason: L('no se pudo contactar al servidor', 'could not reach the server') }, gen);
      });
  }

  function statementsSourceLine(d) {
    var src = srcName(d.source);
    var Y = d.years || [];
    var span = Y.length ? (Y[0] + (Y.length > 1 ? '–' + Y[Y.length - 1] : '')) : '';
    var cur = d.currency && String(d.currency).toUpperCase() !== 'USD'
      ? L('montos en USD (reportados en ' + d.currency + ' y convertidos al tipo de cambio actual)',
          'amounts in USD (reported in ' + d.currency + ' and converted at the current exchange rate)')
      : L('montos en USD', 'amounts in USD');
    return esc(L('Estados financieros anuales', 'Annual financial statements')) + (span ? ' ' + esc(span) : '') +
      ' · ' + esc(L('fuente: ', 'source: ')) + '<b style="color:#9BA6C4">' + esc(src || L('proveedor no indicado', 'provider not stated')) + '</b>' +
      ' · ' + esc(cur) + ' · ' + esc(L('los años sin dato se omiten', 'years without data are skipped'));
  }

  function renderStatements(d, ticker, gen) {
    var body = document.getElementById('fc-body'); if (!body) return;
    var srcEl = document.getElementById('fc-src');
    if (srcEl) srcEl.innerHTML = statementsSourceLine(d);
    var footSrc = document.getElementById('fc-foot-src');
    if (footSrc) footSrc.textContent = L('fuentes: ', 'sources: ') + (srcName(d.source) || '—') + ' (' + L('estados', 'statements') + ') · ' +
      L('mercado en vivo y precio: Yahoo Finance u otro proveedor de respaldo', 'live market and price: Yahoo Finance or a fallback provider');

    var Y = d.years || [];
    var has = function (a) { return Array.isArray(a) && a.some(function (v) { return v != null; }); };
    var revB = (d.revenue || []).map(function (v) { return v != null ? Math.round(v / 1e8) / 10 : null; });
    var fcfB = (d.fcf || []).map(function (v) { return v != null ? Math.round(v / 1e8) / 10 : null; });
    var GM = d.gross_margin || [], FM = d.fcf_margin || [];

    // GARANTÍA "nunca una celda vacía" (feedback real): cada indicador
    // tiene un plan B con datos reales; si ni eso, una nota clara.
    var CELLS = [
      has(d.revenue_growth)
        ? { t: L('💵 Crecimiento de ingresos', '💵 Revenue growth'), d: L('variación anual, %', 'year-over-year change, %'), r: function (id) { lineChart(id, Y, d.revenue_growth, '%'); } }
        : { t: L('💵 Ingresos', '💵 Revenue'), d: L('miles de millones USD por año', 'USD billions per year'), r: has(revB) ? function (id) { barChart(id, Y, revB, '$B'); } : null },
      has(d.dilution)
        ? { t: L('🩸 Dilución', '🩸 Dilution') + (window.explainChip ? window.explainChip('dilucion') : ''), d: L('cambio de acciones en circulación, % (menos es mejor)', 'change in shares outstanding, % (lower is better)'), r: function (id) { barChart(id, Y, d.dilution, '%', posnegInv); } }
        : { t: L('🩸 Acciones en circulación', '🩸 Shares outstanding'), d: L('miles de millones de acciones', 'billions of shares'), r: has(d.shares) ? function (id) { lineChart(id, Y, d.shares, 'B'); } : null },
      has(d.fcf_growth)
        ? { t: '💰 Free cash flow', d: L('crecimiento anual, %', 'annual growth, %'), r: function (id) { lineChart(id, Y, d.fcf_growth, '%'); } }
        : { t: '💰 Free cash flow', d: L('miles de millones USD por año', 'USD billions per year'), r: has(fcfB) ? function (id) { barChart(id, Y, fcfB, '$B', posneg); } : null },
      { t: L('📈 Acción', '📈 Stock'), d: L('últimos ~90 días · moneda local', 'last ~90 days · local currency'), r: 'candles' },
      has(d.ev_to_sales)
        ? { t: L('🏷️ Valuación', '🏷️ Valuation'), d: L('EV / Ventas', 'EV / Sales'), r: function (id) { lineChart(id, Y, d.ev_to_sales, 'x'); } }
        : { t: L('🏷️ Margen bruto anual', '🏷️ Annual gross margin'), d: L('evolución del margen bruto, %', 'gross margin trend, %'), r: has(GM) ? function (id) { lineChart(id, Y, GM, '%'); } : null },
      { t: L('🏦 Balance', '🏦 Balance sheet'), d: L('deuda / capital (menos es mejor)', 'debt / equity (lower is better)'), r: has(d.de_ratio) ? function (id) { barChart(id, Y, d.de_ratio, '', function (v) { return v == null ? INK : v > 1 ? DOWN : NEON; }); } : null },
      { t: L('🧮 Márgenes', '🧮 Margins'), d: L('bruto vs FCF, último año, %', 'gross vs FCF, latest year, %'), r: 'margins' },
      { t: '♻️ Return on equity', d: L('ROE anual, %', 'annual ROE, %'), r: has(d.roe) ? function (id) { barChart(id, Y, d.roe, '%', posneg); } : null },
    ];

    body.innerHTML = '<div class="fc-grid">' +
      CELLS.map(function (c, i) { return cell(c.t, c.d, 'fc-c' + i); }).join('') +
      '</div>';

    CELLS.forEach(function (c, i) {
      var id = 'fc-c' + i;
      if (typeof c.r === 'function') { c.r(id); return; }
      if (c.r === 'candles') { loadCandles(ticker, id, gen); return; }
      if (c.r === 'margins') {
        var gm = null, fm = null;
        for (var k = Y.length - 1; k >= 0; k--) {
          if (gm == null && GM[k] != null) gm = GM[k];
          if (fm == null && FM[k] != null) fm = FM[k];
        }
        if (gm != null || fm != null) {
          barChart(id, [L('Margen bruto', 'Gross margin'), L('Margen FCF', 'FCF margin')], [gm, fm], '%', function (v) { return v == null ? INK : v >= 0 ? NEON : DOWN; });
          return;
        }
        c.r = null;
      }
      if (c.r == null) cellNote(id, c.t, L('El proveedor no publica este dato para esta empresa.', 'The provider does not publish this data for this company.'));
    });
  }

  // sin estados financieros: franja en vivo (arriba) + acción + nota clara.
  // NUNCA un overlay vacío.
  function renderNoStatements(n, ticker, d, gen) {
    var body = document.getElementById('fc-body'); if (!body) return;
    var srcEl = document.getElementById('fc-src');
    var tried = srcList(d && d.tried);
    // la línea de arriba solo orienta (qué hay en la ficha); el "por qué
    // faltan" se dice UNA vez, en la celda de abajo
    if (srcEl) srcEl.innerHTML = esc(L('Arriba: el mercado en vivo · abajo: la acción, qué hace la empresa y por qué faltan sus estados financieros anuales',
      'Above: the live market · below: the stock, what the company does and why its annual financial statements are missing'));
    // el server antepone "Sin estados financieros públicos para X — " (ya lo
    // dice el párrafo) → aquí solo el detalle útil: qué fuente falló y por qué
    var why = String(reasonOf(d) || '');
    if (why.indexOf(' — ') >= 0) why = why.split(' — ').slice(1).join(' — ');
    var srcTxt = tried.length ? tried.join(', ')
      : L('Financial Modeling Prep, Yahoo Finance y Alpha Vantage, según las claves configuradas',
          'Financial Modeling Prep, Yahoo Finance and Alpha Vantage, depending on configured keys');
    body.innerHTML = '<div class="fc-grid">' +
      cell(L('📈 Acción', '📈 Stock'), L('últimos ~90 días · moneda local', 'last ~90 days · local currency'), 'fc-c3') +
      '<div class="fc-cell"><div class="fc-t">📄 ' + esc(L('Estados financieros', 'Financial statements')) + '</div>' +
        '<div class="fc-p" style="padding-top:8px">' +
          esc(L('No encontramos estados financieros anuales de ' + ticker + ' en nuestras fuentes (' + srcTxt + '). No rellenamos los huecos con cifras inventadas: preferimos decirte que faltan.',
                'We found no annual financial statements for ' + ticker + ' in our sources (' + srcTxt + '). We do not fill the gaps with made-up figures: we would rather tell you they are missing.')) +
        '</div>' +
        (why ? '<div class="fc-meta">' + esc(L('Detalle: ', 'Details: ')) + esc(why) + '</div>' : '') +
        '<div class="fc-meta" style="margin-top:8px">' + esc(L('Suele pasar con bolsas fuera de EE.UU. poco cubiertas, empresas recién listadas, tickers ADR/OTC, o cuando un proveedor falla o no tiene su clave configurada. Ninguna cifra de esta ficha es inventada: todo viene de una fuente nombrada (el precio objetivo, la recomendación y el P/E de los próximos 12 meses son estimaciones de analistas).',
          'This is common for thinly covered non-US exchanges, newly listed companies, ADR/OTC tickers, or when a provider fails or has no key configured. No figure on this card is made up: everything comes from a named source (the target price, the recommendation and the forward P/E are analyst estimates).')) + '</div>' +
      '</div>' +
      catalogAbout(n) +
      '</div>';
    var footSrc = document.getElementById('fc-foot-src');
    if (footSrc) footSrc.textContent = L('fuentes: mercado en vivo + precio (Yahoo Finance u otro proveedor de respaldo) + catálogo Khipus',
      'sources: live market + price (Yahoo Finance or a fallback provider) + Khipus catalog');
    loadCandles(ticker, 'fc-c3', gen);
  }

  /* ── NO COTIZA: privada / filial / comprada / organismo ─────────────────── */
  function kv(k, v) {
    return (v != null && v !== '') ? '<div class="fc-kv"><span>' + esc(k) + '</span><span>' + esc(v) + '</span></div>' : '';
  }
  // dato corto → fila clave/valor; texto largo → párrafo (no una columna angosta)
  function kvAuto(k, v) {
    if (v == null || v === '') return '';
    return String(v).length > 48 ? '<div class="fc-kv" style="display:block"><span style="display:block;margin-bottom:3px">' + esc(k) + '</span>' +
      '<span style="display:block;text-align:left;color:#C9D4EC;line-height:1.5">' + esc(v) + '</span></div>' : kv(k, v);
  }
  function para(k, v) {
    return v ? '<div class="fc-pl">' + esc(k) + '</div><div class="fc-p">' + esc(v) + '</div>' : '';
  }

  function renderPrivate(n, gen) {
    var ov = ensureShell();
    var fc = document.getElementById('fc');
    var m = (window.NODE_META || {})[n.id] || {};
    var pi = (window.PREIPO_INTEL || {})[n.id] || {};
    var ls = n.listing || {};
    var kind = kindOf(n);
    var parentTk = ls.parent_ticker ? String(ls.parent_ticker) : null;
    _st.parent = parentTk ? { ticker: parentTk, name: ls.parent || parentTk } : null;
    _st.cmp = null;

    var rounds = (pi.rounds || []).map(function (r) {
      return '<div style="display:flex;gap:10px;font-size:11.5px;padding:5px 0;border-bottom:1px solid rgba(122,158,255,.06)">' +
        '<span style="color:#00E0FF;font-family:monospace;flex:0 0 52px">' + esc(r.date || '') + '</span>' +
        '<span style="color:#E8EDFB;flex:1">' + esc(r.round || '') + '</span>' +
        '<span style="color:#2BE38B;font-family:monospace">' + esc(r.amount || '') + '</span></div>';
    }).join('');
    var miles = (pi.milestones || []).map(function (h) {
      return '<div style="font-size:11.5px;padding:4px 0;color:#9BA6C4"><span style="color:#00E0FF;font-family:monospace">' + esc(h.date || '') + '</span> · ' + esc(h.event || '') + '</div>';
    }).join('');

    // estado en bolsa verificado (nodes/listing_status.js) con su fuente
    var lsNote = isEn() ? (ls.note_en || ls.note_es) : (ls.note_es || ls.note_en);
    var lsSrc = safeUrl(ls.source_url);
    var sub = lsNote
      ? esc(lsNote) + (lsSrc ? ' · <a href="' + esc(lsSrc) + '" target="_blank" rel="noopener">' + esc(L('fuente', 'source')) + ' ↗</a>' : '') +
        (ls.as_of ? ' · ' + esc(L('verificado ', 'verified ')) + esc(ls.as_of) : '')
      : (Object.keys(pi).length
          ? esc(L('Sin estados financieros públicos — esto es lo que sabemos del catálogo, la inteligencia pre-IPO y las noticias en vivo',
                  'No public financial statements — this is what we know from the catalog, pre-IPO intelligence and live news'))
          : esc(L('Sin estados financieros públicos — esto es lo que sabemos del catálogo y las noticias en vivo',
                  'No public financial statements — this is what we know from the catalog and live news')));

    var marginCat = num(n.margin) != null ? Math.round(n.margin * 100) + '%' : null;
    var ficha =
      '<div class="fc-cell"><div class="fc-t">🏢 ' + esc(L('Ficha', 'Profile')) + '<span class="fc-tr">' + esc(L('catálogo Khipus', 'Khipus catalog')) + '</span></div>' +
        kv(L('Situación', 'Status'), L(kind.es, kind.en)) +
        kv(L('Dueño / matriz', 'Owner / parent'), ls.parent ? ls.parent + (parentTk ? ' (' + parentTk + ')' : '') : null) +
        kv(L('País', 'Country'), n.country) +
        kv(L('Sede', 'Location'), (n.loc && n.loc !== n.country) ? n.loc : null) +
        kv(L('Fundada', 'Founded'), m.founded) +
        kv(L('Empleados', 'Employees'), m.employees ? fmtInt(Number(m.employees)) : null) +
        kvAuto(L('Ingresos 2025 (catálogo)', 'Revenue 2025 (catalog)'), m.revenue_2025) +
        kv(L('Margen (catálogo)', 'Margin (catalog)'), marginCat) +
        kvAuto(L('Riesgo geopolítico', 'Geopolitical risk'), m.geo_risk) +
      '</div>';

    var showVal = !!(pi.valuation || pi.total_raised || pi.ipo_timeline || (pi.investors && pi.investors.length) || n.preipo);
    var val = showVal
      ? '<div class="fc-cell"><div class="fc-t">💎 ' + esc(L('Valuación', 'Valuation')) + '<span class="fc-tr">' + esc(L('inteligencia pre-IPO', 'pre-IPO intelligence')) + '</span></div>' +
          kv(L('Valuación', 'Valuation'), pi.valuation) + kv(L('Capital levantado', 'Capital raised'), pi.total_raised) +
          kv(L('IPO estimada', 'Expected IPO'), pi.ipo_timeline) +
          kv(L('Inversores', 'Investors'), (pi.investors || []).slice(0, 4).join(', ') || null) +
          (!pi.valuation ? '<div class="fc-note" style="padding:14px 4px">' + esc(L('Sin inteligencia pre-IPO registrada para esta empresa.', 'No pre-IPO intelligence on record for this company.')) + '</div>' : '') +
        '</div>'
      : '';

    var now = para(L('Crecimiento / momento', 'Growth / momentum'), bi(n, 'growth')) +
      para(L('Capex 2026', 'Capex 2026'), bi(n, 'capex_2026')) +
      para(L('Cartera de pedidos', 'Backlog'), bi(n, 'backlog_status'));
    var what = (isEn() ? m.desc_en : null) || m.desc || bi(n, 'role');

    fc.innerHTML =
      header(kind.icon, n.label || n.id, esc(L(kind.es, kind.en)) + ' · dossier', false) +
      (parentTk ? liveLoading(parentTk) : '') +
      '<div class="fc-sub">' + sub + '</div>' +
      '<div class="fc-grid">' +
        ficha + val +
        (rounds ? '<div class="fc-cell"><div class="fc-t">💸 ' + esc(L('Rondas', 'Funding rounds')) + '</div>' + rounds + '</div>' : '') +
        (miles ? '<div class="fc-cell"><div class="fc-t">🏁 ' + esc(L('Hitos', 'Milestones')) + '</div>' + miles + '</div>' : '') +
        ((what || n.moat || n.supplies) ? '<div class="fc-cell"><div class="fc-t">📖 ' + esc(L('Qué hace', 'What it does')) + '</div>' +
          (what ? '<div class="fc-p">' + esc(what) + '</div>' : '') +
          para(L('Qué provee', 'What it supplies'), bi(n, 'supplies')) +
          para(L('Ventaja (moat)', 'Moat'), bi(n, 'moat')) + '</div>' : '') +
        (now ? '<div class="fc-cell"><div class="fc-t">📌 ' + esc(L('Situación actual', 'Current situation')) +
          '<span class="fc-tr">' + esc(L('catálogo Khipus', 'Khipus catalog')) + '</span></div>' + now + '</div>' : '') +
        '<div class="fc-cell fc-wide" id="fc-news"><div class="fc-t">📰 ' + esc(L('Noticias recientes', 'Recent news')) +
          '<span class="fc-tr" id="fc-news-st">' + esc(L('buscando…', 'searching…')) + '</span></div>' +
          '<div id="fc-news-list"><div class="fc-note" style="padding:18px 8px">' + esc(L('Buscando noticias en vivo…', 'Looking for live news…')) + '</div></div></div>' +
        '<div class="fc-cell fc-wide" id="fc-hist" style="display:none"><div class="fc-t">🕰 ' + esc(L('Historia', 'History')) +
          '<span class="fc-tr">' + esc(L('ontología Khipus, con fuentes', 'Khipus ontology, with sources')) + '</span></div><div id="fc-hist-list"></div></div>' +
      '</div>' +
      footer(esc(L('fuentes: catálogo Khipus + inteligencia pre-IPO + noticias GDELT', 'sources: Khipus catalog + pre-IPO intelligence + GDELT news')) +
        (parentTk ? esc(L(' + mercado en vivo del dueño', ' + owner’s live market')) : ''));
    ov.classList.add('show');

    if (parentTk) startLive({ ticker: parentTk, parent: { name: ls.parent || parentTk, ticker: parentTk, child: n.label || n.id } }, gen);
    startNews(n, gen);
    loadHistory(n, gen);
  }

  // GDELT: el server limpia a [A-Za-z0-9 ._-]; aquí quitamos acentos y el
  // texto entre paréntesis para que "Møller" no quede como "Mller".
  function newsQuery(n) {
    var s = String(n.label || n.id || '').replace(/\([^)]*\)/g, ' ');
    try { s = s.normalize('NFD').replace(/[̀-ͯ]/g, ''); } catch (e) {}
    s = s.replace(/[øØ]/g, 'o').replace(/[æÆ]/g, 'ae').replace(/ß/g, 'ss').replace(/&/g, ' and ');
    return s.replace(/[^A-Za-z0-9 ._-]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 60);
  }

  function fetchNews(n, gen) {
    var q = newsQuery(n);
    var st = document.getElementById('fc-news-st');
    var list = document.getElementById('fc-news-list');
    if (!q) {
      if (list) list.innerHTML = '<div class="fc-note" style="padding:18px 8px">' + esc(L('No hay un nombre con el que buscar noticias.', 'There is no name to search news with.')) + '</div>';
      if (st) st.textContent = '';
      return;
    }
    fetch(base() + '/api/news/gdelt/' + encodeURIComponent(q))
      .then(function (r) { return r.json(); })
      .then(function (arr) {
        if (gen !== _gen) return;
        st = document.getElementById('fc-news-st'); list = document.getElementById('fc-news-list');
        if (!list) return;
        var items = (Array.isArray(arr) ? arr : []).filter(function (a) { return a && a.headline && safeUrl(a.url); });
        // sin duplicados por titular (GDELT repite la misma nota en varios medios)
        var seen = {};
        items = items.filter(function (a) { var k = String(a.headline).toLowerCase().slice(0, 80); if (seen[k]) return false; seen[k] = 1; return true; }).slice(0, 6);
        // Honestidad sobre la frescura: el servidor guarda cada búsqueda de
        // GDELT hasta 30 min (también cuando GDELT falla y vuelve vacía), así
        // que "revisado HH:MM" es cuándo PREGUNTAMOS, no cuándo se buscó; lo
        // que de verdad dice qué tan nuevas son es la fecha de cada nota.
        var now = new Date();
        if (!items.length) {
          if (_st.newsOk) {
            // se queda la lista anterior: el sello NO se renueva como si fuera nueva
            if (st) st.textContent = L('vía GDELT · lista revisada a las ', 'via GDELT · list checked at ') + fmtClock(_st.newsAt) +
              ' · ' + L('la última revisión (' + fmtClock(now) + ') vino vacía', 'the latest check (' + fmtClock(now) + ') came back empty');
            return;
          }
          if (st) st.textContent = L('vía GDELT · revisado ', 'via GDELT · checked ') + fmtClock(now) + ' · ' + L('sin resultados', 'no results');
          list.innerHTML = '<div class="fc-note" style="padding:18px 8px">' +
            esc(L('Sin noticias recientes de «' + q + '» en GDELT (o GDELT no respondió). Seguimos revisando solos cada 5 min, pero nuestro servidor guarda cada búsqueda hasta 30 min: si GDELT falló, puede tardar hasta media hora en volver a intentarlo.',
                  'No recent news for “' + q + '” on GDELT (or GDELT did not answer). We keep checking every 5 min on our own, but our server keeps each search for up to 30 min: if GDELT failed, it may take up to half an hour to try again.')) + '</div>';
          return;
        }
        _st.newsOk = true;
        _st.newsAt = now;
        var newest = null;
        items.forEach(function (a) { var t = parseWhen(a.datetime); if (t != null && (newest == null || t > newest)) newest = t; });
        if (st) st.textContent = L('vía GDELT · revisado ', 'via GDELT · checked ') + fmtClock(now) +
          (newest != null ? ' · ' + L('nota más reciente: ', 'newest story: ') + ago(newest) : '');
        list.innerHTML = items.map(function (a) {
          var t = parseWhen(a.datetime);
          return '<div class="fc-item"><a href="' + esc(safeUrl(a.url)) + '" target="_blank" rel="noopener">' + esc(a.headline) + '</a>' +
            '<div class="fc-meta">' + esc(a.source || '') + (t ? ' · ' + esc(ago(t)) : '') +
            (a.language && !/^(english|spanish)$/i.test(a.language) ? ' · ' + esc(a.language) : '') + '</div></div>';
        }).join('') +
          '<div class="fc-meta" style="margin-top:8px">' + esc(L('Revisamos solos cada 5 min; nuestro servidor guarda cada búsqueda en GDELT hasta 30 min, así que una nota nueva puede tardar hasta media hora en aparecer aquí.',
            'We check on our own every 5 min; our server keeps each GDELT search for up to 30 min, so a new story can take up to half an hour to show up here.')) + '</div>';
      })
      .catch(function () {
        if (gen !== _gen) return;
        st = document.getElementById('fc-news-st'); list = document.getElementById('fc-news-list');
        // esto es nuestro servidor sin respuesta (no la caché de GDELT): el reintento a 5 min es real
        if (st) st.textContent = L('sin conexión con el servidor de noticias · reintento en 5 min', 'no connection to the news server · retry in 5 min');
        if (list && !_st.newsOk) list.innerHTML = '<div class="fc-note" style="padding:18px 8px">' +
          esc(L('No se pudieron traer noticias ahora. Reintentamos solos en 5 minutos.', 'Could not fetch news right now. We retry automatically in 5 minutes.')) + '</div>';
      });
  }

  function startNews(n, gen) {
    fetchNews(n, gen);
    every(NEWS_MS, function () { fetchNews(n, gen); }, gen);
  }

  // Historia (ontología): si no hay base de datos (503) o el objeto no existe
  // (404), la celda simplemente no aparece — sin error a la vista.
  function loadHistory(n, gen) {
    fetch(base() + '/api/ontology/objects/' + encodeURIComponent(n.id) + '/timeline?limit=6&lang=' + (isEn() ? 'en' : 'es'))
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (gen !== _gen || !d) return;
        var rows = Array.isArray(d.timeline) ? d.timeline : [];
        if (!rows.length) return;
        var cellEl = document.getElementById('fc-hist'), list = document.getElementById('fc-hist-list');
        if (!cellEl || !list) return;
        list.innerHTML = rows.map(function (e) {
          var at = e.at ? String(e.at).slice(0, 10) : '—';
          var u = safeUrl(e.url);
          var title = esc(e.title || e.event_type || '');
          var pub = e.source && (e.source.publisher || e.source.label || e.source.domain);
          return '<div class="fc-item"><span style="color:#00E0FF;font-family:monospace;font-size:11px">' + esc(at) + '</span> · ' +
            (e.kind === 'news' ? '📰 ' : '') +
            (u ? '<a href="' + esc(u) + '" target="_blank" rel="noopener">' + title + '</a>' : title) +
            ((e.detail || pub) ? '<div class="fc-meta">' + esc(e.detail || pub) + '</div>' : '') + '</div>';
        }).join('');
        cellEl.style.display = '';
      })
      .catch(function () {});
  }

  /* ── API pública ─────────────────────────────────────────────────────────── */
  window.openFinCard = function (idOrTicker, labelHint) {
    // cerrar lo anterior: intervalos, gráficos y respuestas pendientes
    _gen++;
    var gen = _gen;
    stopTimers();
    destroyCharts();
    _st = {};

    var raw = String(idOrTicker == null ? '' : idOrTicker).trim();
    var n = resolveNode(raw);
    if (n && !n.mkt) { renderPrivate(n, gen); return; }        // no cotiza → dossier igual

    var ticker = (n && n.mkt) ? String(n.mkt) : raw.toUpperCase();
    if (!ticker || /\s/.test(ticker)) {
      var msg = (window.KhipuResolve && window.KhipuResolve.notFound && raw)
        ? (function () { try { return window.KhipuResolve.notFound(raw).text; } catch (e) { return null; } })()
        : null;
      if (typeof toast === 'function') toast(msg || L('No encuentro esa empresa', "I can't find that company"));
      return;
    }
    var label = (n && n.label) || (labelHint ? String(labelHint) : ticker);
    renderListed(n, ticker, label, gen);
    if (!n && !labelHint) _st.nameFromLive = true;
  };

  // "⇄ Comparar en Análisis": cierra la ficha (y la Cabina, que taparía la
  // pestaña) y abre la empresa en el comparador de Análisis.
  window._finCardCompare = function () {
    var c = _st.cmp; if (!c) return;
    close();
    try { var ck = window.BixbyCockpit; if (ck && ck.isOpen && ck.isOpen() && ck.close) ck.close(); } catch (e) {}
    if (window._openDossier) window._openDossier(c.id, c.mkt);
  };

  // dossier de la matriz que cotiza (desde la franja "Cotiza a través de…")
  window._finCardOpenParent = function () {
    var p = _st.parent; if (!p) return;
    window.openFinCard(p.ticker, p.name);
  };

  window._finCardClose = close;
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && isShown()) close(); });
})();
