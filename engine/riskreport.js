/* engine/riskreport.js — REPORTE DE RIESGO DE CARTERA: VaR + Vega (Kappa).

   window.KhipuRisk.open({ tab: 'var'|'vega', source?: 'market'|'pf:<id>'|'manual', autorun? })

   REDISEÑO 2026-09-30 (pedido de Fabrizio: "los análisis de riesgo de cartera
   no los entiendo, cómo usar, no me deja — que haya una forma más fácil"):
   · Antes: `source:'market'` + autorun con "Mi portafolio" VACÍO → un error
     ámbar y nada más; el modo manual exigía la sintaxis "NVDA:10" escondida en
     un <select>; Vega pedía escribir un ticker y pulsar "Buscar vencimientos".
   · Ahora: PANTALLA DE INICIO GUIADA con 3 caminos — (a) usar mis posiciones
     (Mercado y cada Cartera simulada, con su conteo; deshabilitado con pista si
     está vacío), (b) armar una cartera rápida buscando empresas del mapa y
     poniendo DÓLARES (el server convierte a acciones con el último cierre real:
     core/risk_report.build_report {symbol, usd}), (c) probar con un EJEMPLO
     (montos hipotéticos, rotulados). El resultado abre con un SEMÁFORO y 3-5
     frases en lenguaje simple generadas de forma DETERMINISTA a partir de los
     números (sin IA), "Qué podrías hacer" educativo (nunca compra/venta), un
     botón opcional "Explícame con IA" y el detalle técnico plegado.
   · Vega: explica primero que las acciones no tienen Vega; flujo por botones
     (empresa → vencimiento → strike con el precio actual marcado → contratos).

   Server: POST /api/portfolio/risk_report (precios diarios REALES de 1 año) ·
   POST /api/portfolio/vega_report (Black-Scholes con IV EN VIVO) ·
   GET /api/options/chain/<sym>. Nada se inventa: lo que no tiene datos se
   excluye y se dice por qué. Todo bilingüe (window.LANG); cada métrica con su
   "?" (engine/explain.js). */
(function () {
  'use strict';
  var LS_OPT = 'kh_options', LS_QUICK = 'kh_risk_quick';
  var S = {
    tab: 'var', source: 'market', manual: '', view: 'start', notice: null,
    spec: null, rep: null, vrep: null, busy: false, chart: null, detail: false, vdetail: false,
    ai: null, aiBusy: false, q: '', amt: 1000, advanced: false,
    vq: '', vsym: '', vlabel: '', chain: null, chainBusy: false, chainErr: null,
    vexp: null, vk: null, vkind: 'call', vside: 'long', vn: 1,
  };

  function en() { return (window.LANG || '') === 'en'; }
  function L(es, e) { return en() ? e : es; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function chip(k) { return window.explainChip ? window.explainChip(k) : ''; }
  // números con separadores del idioma (es: 1.234,5 · en: 1,234.5)
  function num(v, d) {
    if (v == null || !isFinite(v)) return '—';
    var s = Math.abs(+v).toFixed(d == null ? 0 : d).split('.');
    var ip = s[0].replace(/\B(?=(\d{3})+(?!\d))/g, en() ? ',' : '.');
    return (v < 0 && +s.join('.') !== 0 ? '−' : '') + ip + (s[1] ? (en() ? '.' : ',') + s[1] : '');
  }
  function strike(k) { return '$' + num(+k, +k % 1 ? 2 : 0); }
  function smoney(v) { return (v > 0 ? '+' : '') + money(v); }
  function money(v) { if (v == null || !isFinite(v)) return '—'; var a = Math.abs(v); return (v < 0 ? '−' : '') + '$' + num(a, a >= 100 ? 0 : 2); }
  function usd(v) {
    if (v == null || !isFinite(v)) return '—';
    var a = Math.abs(v);
    return (v < 0 ? '−' : '') + '$' + (a >= 1e6 ? num(a / 1e6, 2) + 'M' : num(a, a >= 1e4 ? 0 : 2));
  }
  function pct(v, d) { return v == null || !isFinite(v) ? '—' : num(+v, d == null ? 2 : d) + '%'; }
  function base() { return (typeof window.BASE !== 'undefined' && window.BASE) || ''; }

  /* ── explicaciones propias (explain.js) ──────────────────────────────── */
  function registerExplain() {
    if (!window.explainRegister || registerExplain.done) return;
    registerExplain.done = true;
    window.explainRegister('risk_level', {
      es: { t: '¿Cómo se decide el semáforo de riesgo?', b: 'Usamos la <b>volatilidad anual</b> de tu cartera (cuánto sube y baja en un año, medido con precios diarios reales del último año):<br><br>🟢 <b>Bajo</b>: menos de 15% al año.<br>🟡 <b>Medio</b>: entre 15% y 30%.<br>🔴 <b>Alto</b>: más de 30%.<br><br>Una acción tecnológica sola suele estar en "alto"; una mezcla amplia de muchas empresas distintas suele bajar. No dice si vas a ganar o perder: dice cuánto se <b>mueve</b>.' },
      en: { t: 'How is the risk light decided?', b: 'We use your portfolio\'s <b>annual volatility</b> (how much it swings in a year, measured with real daily prices from the last year):<br><br>🟢 <b>Low</b>: under 15% a year.<br>🟡 <b>Medium</b>: between 15% and 30%.<br>🔴 <b>High</b>: over 30%.<br><br>A single tech stock usually lands in "high"; a broad mix of many different companies usually brings it down. It does not say whether you will win or lose: it says how much it <b>moves</b>.' },
    });
    window.explainRegister('options_basics', {
      es: { t: '¿Qué es una opción (call / put)?', b: 'Una <b>opción</b> es un contrato que da el <b>derecho</b> (no la obligación) de comprar o vender 100 acciones a un precio fijo (<b>strike</b>) hasta una fecha (<b>vencimiento</b>).<br><br><b>Call</b> = derecho a COMPRAR: gana valor si la acción sube.<br><b>Put</b> = derecho a VENDER: gana valor si la acción baja (se usa como seguro).<br><br><b>Comprada</b> = pagaste por ese derecho. <b>Vendida</b> = cobraste por darlo (más riesgo).<br><br>Aquí solo se <b>simula</b>: no se envía ninguna orden.' },
      en: { t: 'What is an option (call / put)?', b: 'An <b>option</b> is a contract giving the <b>right</b> (not the obligation) to buy or sell 100 shares at a fixed price (<b>strike</b>) until a date (<b>expiry</b>).<br><br><b>Call</b> = right to BUY: gains value if the stock rises.<br><b>Put</b> = right to SELL: gains value if the stock falls (used as insurance).<br><br><b>Bought</b> = you paid for that right. <b>Sold</b> = you got paid to grant it (more risk).<br><br>This is only a <b>simulation</b>: no order is sent.' },
    });
  }

  /* ── empresas del mapa que cotizan (autocompletar) ───────────────────── */
  var _listed = null;
  function listed() {
    if (_listed && _listed.n === (window.NODES || []).length) return _listed.v;
    var seen = {}, out = [];
    (window.NODES || []).forEach(function (n) {
      if (!n || !n.mkt || seen[n.mkt]) return;
      seen[n.mkt] = 1;
      out.push({ id: n.id, sym: String(n.mkt), label: n.label || n.id });
    });
    _listed = { n: (window.NODES || []).length, v: out };
    return out;
  }
  function search(q) {
    q = String(q || '').trim().toLowerCase(); if (!q) return [];
    var res = [];
    listed().forEach(function (c) {
      var s = c.sym.toLowerCase(), l = String(c.label).toLowerCase(), i = String(c.id).toLowerCase(), sc = 0;
      if (s === q) sc = 100; else if (l === q) sc = 95; else if (s.indexOf(q) === 0) sc = 80;
      else if (l.indexOf(q) === 0) sc = 70; else if (l.indexOf(' ' + q) >= 0) sc = 60;
      else if (l.indexOf(q) >= 0 || i.indexOf(q) >= 0) sc = 45;
      if (sc) res.push({ c: c, sc: sc });
    });
    res.sort(function (a, b) { return b.sc - a.sc || a.c.label.length - b.c.label.length; });
    return res.slice(0, 8).map(function (x) { return x.c; });
  }
  function bySym(sym) { return listed().filter(function (c) { return c.sym === sym; })[0]; }

  /* ── ejemplos (tickers reales del mapa; montos HIPOTÉTICOS) ──────────── */
  var EXAMPLES = [
    { id: 'semis', icon: '🔌', es: 'Semiconductores IA', en: 'AI semiconductors', syms: ['NVDA', 'AMD', 'TSM', 'AVGO', 'ASML'],
      des: 'Los fabricantes de chips que mueven la IA.', den: 'The chipmakers powering AI.' },
    { id: 'bigtech', icon: '☁️', es: 'Big Tech', en: 'Big Tech', syms: ['MSFT', 'GOOGL', 'AMZN', 'META', 'AAPL'],
      des: 'Las grandes tecnológicas que compran esos chips.', den: 'The tech giants that buy those chips.' },
    { id: 'energy', icon: '⚡', es: 'Energía para IA', en: 'Energy for AI', syms: ['VST', 'CEG', 'NEE', 'GEV', 'VRT'],
      des: 'Electricidad y equipos para los centros de datos.', den: 'Power and equipment for data centers.' },
  ];
  var EX_TOTAL = 10000;
  function examplePositions(ex) {
    var cs = ex.syms.map(bySym).filter(Boolean);
    var each = cs.length ? EX_TOTAL / cs.length : 0;
    return cs.map(function (c) { return { symbol: c.sym, usd: each, label: c.label }; });
  }

  /* ── fuentes de posiciones del usuario ───────────────────────────────── */
  function pfList() {
    try { return (window.KhipuPortfolios && window.KhipuPortfolios._list ? window.KhipuPortfolios._list() : []) || []; } catch (e) { return []; }
  }
  function positionsFrom(src) {
    var NB = window.NODE_BY_ID || {}, out = [], skipped = [];
    if (src === 'market') {
      var pos = (window.MKT && window.MKT.pos) || {};
      Object.keys(pos).forEach(function (id) {
        var n = NB[id], p = pos[id] || {};
        if (n && n.mkt && (p.sh || p.shares)) out.push({ symbol: n.mkt, shares: +(p.sh || p.shares), label: n.label });
        else skipped.push((n && n.label) || id);
      });
    } else if (src.indexOf('pf:') === 0) {
      var id = src.slice(3);
      var pf = pfList().filter(function (x) { return x.id === id; })[0];
      ((pf && pf.positions) || []).forEach(function (p) {
        var n = NB[p.nodeId];
        if (n && n.mkt && p.shares > 0) out.push({ symbol: n.mkt, shares: +p.shares, label: n.label });
        else skipped.push((n && n.label) || p.nodeId);
      });
    } else {
      String(S.manual || '').split(/[,;\n]+/).forEach(function (tok) {
        var m = tok.trim().match(/^([A-Za-z0-9.^-]{1,15})\s*[: ]\s*([\d.]+)$/);
        if (m) out.push({ symbol: m[1].toUpperCase(), shares: +m[2], label: m[1].toUpperCase() });
        else if (tok.trim()) skipped.push(tok.trim());
      });
    }
    return { positions: out, skipped: skipped };
  }
  function sourceName(src) {
    if (src === 'market') return L('Mi portafolio (Mercado)', 'My portfolio (Market)');
    if (src.indexOf('pf:') === 0) { var p = pfList().filter(function (x) { return x.id === src.slice(3); })[0]; return '🧪 ' + ((p && p.name) || src.slice(3)); }
    return L('Tickers escritos a mano', 'Hand-typed tickers');
  }

  /* ── persistencia local (comodidades por usuario) ────────────────────── */
  function lsGet(k, d) { try { var v = JSON.parse(localStorage.getItem(k) || 'null'); return v == null ? d : v; } catch (e) { return d; } }
  function lsSet(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  function loadOpts() { var a = lsGet(LS_OPT, []); return Array.isArray(a) ? a : []; }
  function saveOpts(a) { lsSet(LS_OPT, a); }
  function loadQuick() { var a = lsGet(LS_QUICK, []); return Array.isArray(a) ? a.filter(function (x) { return x && x.sym && x.usd > 0; }) : []; }
  function saveQuick(a) { lsSet(LS_QUICK, a); }

  /* ── estructura ──────────────────────────────────────────────────────── */
  function css() {
    if (document.getElementById('krr-css')) return;
    var st = document.createElement('style'); st.id = 'krr-css';
    st.textContent =
      '#krr-ov{position:fixed;inset:0;z-index:7800;display:none;align-items:flex-start;justify-content:center;background:rgba(3,6,12,.74);backdrop-filter:blur(4px);overflow-y:auto;font-family:Inter,system-ui,sans-serif}' +
      '#krr-ov.show{display:flex}' +
      '#krr{width:min(1100px,96vw);margin:3vh 0;border-radius:16px;background:radial-gradient(900px 500px at 50% -10%,#0B1222 0%,#06090F 60%);border:1px solid rgba(122,158,255,.22);box-shadow:0 24px 70px rgba(0,0,0,.6);padding:18px 20px;color:#E8EDFB;box-sizing:border-box}' +
      '#krr *{box-sizing:border-box}' +
      '#krr .hd{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px}#krr .hd h2{margin:0;font-size:19px;flex:1;min-width:180px}' +
      '#krr .x{width:34px;height:34px;border-radius:8px;border:1px solid rgba(122,158,255,.25);background:rgba(21,28,45,.7);color:#9BA6C4;cursor:pointer}' +
      '#krr .ktabs{display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap}#krr .ktab{padding:8px 14px;border-radius:9px;border:1px solid rgba(122,158,255,.22);background:rgba(21,28,45,.6);color:#9BA6C4;cursor:pointer;font-size:13px}#krr .ktab.on{background:rgba(0,224,255,.12);border-color:#00E0FF;color:#00E0FF}' +
      '#krr .row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px}#krr select,#krr input,#krr textarea{background:#0B1222;border:1px solid rgba(122,158,255,.25);color:#E8EDFB;border-radius:8px;padding:9px 10px;font-size:14px;font-family:inherit;max-width:100%}' +
      '#krr .btn{padding:9px 14px;border-radius:9px;border:1px solid #00E0FF;background:rgba(0,224,255,.12);color:#00E0FF;cursor:pointer;font-weight:650;font-size:13px}#krr .btn:disabled{opacity:.45;cursor:default}#krr .btn.gh{border-color:rgba(122,158,255,.3);background:transparent;color:#9BA6C4}#krr .btn.big{font-size:15px;padding:12px 18px}' +
      '#krr .note{font-size:12px;color:#9BA6C4;line-height:1.55}#krr .warn{padding:10px 12px;border:1px dashed #f59e0b;border-radius:9px;background:rgba(245,158,11,.08);color:#fbbf24;font-size:13px;line-height:1.55;margin:8px 0}' +
      '#krr .info{padding:10px 12px;border:1px solid rgba(0,224,255,.28);border-radius:10px;background:rgba(0,224,255,.06);color:#C9D4EC;font-size:13px;line-height:1.55;margin:8px 0}' +
      '#krr .lead{font-size:14.5px;color:#C9D4EC;line-height:1.55;margin:0 0 12px}' +
      '#krr .start{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}' +
      '#krr .opt{border:1px solid rgba(122,158,255,.2);border-radius:14px;background:rgba(11,18,34,.65);padding:14px;display:flex;flex-direction:column;gap:8px;min-width:0}' +
      '#krr .opt h3{margin:0;font-size:15px;color:#E8EDFB}#krr .opt .k{font-size:22px}' +
      '#krr .pick{display:flex;justify-content:space-between;align-items:center;gap:8px;width:100%;text-align:left;padding:10px 12px;border-radius:10px;border:1px solid rgba(122,158,255,.25);background:rgba(21,28,45,.6);color:#E8EDFB;cursor:pointer;font-size:13.5px}' +
      '#krr .pick:hover:not(:disabled){border-color:#00E0FF}#krr .pick:disabled{opacity:.55;cursor:default}#krr .pick small{color:#7C87A3;font-size:11.5px}' +
      '#krr .tag{display:inline-block;font-size:10.5px;font-weight:700;letter-spacing:.06em;padding:2px 7px;border-radius:6px;background:rgba(245,158,11,.14);color:#fbbf24;border:1px solid rgba(245,158,11,.35)}' +
      '#krr .qwrap{position:relative}#krr .sugg{position:absolute;left:0;right:0;top:100%;z-index:3;background:#0B1222;border:1px solid rgba(122,158,255,.35);border-radius:10px;margin-top:4px;max-height:260px;overflow-y:auto;box-shadow:0 12px 30px rgba(0,0,0,.5)}' +
      '#krr .sugg button{display:flex;justify-content:space-between;width:100%;padding:9px 11px;background:none;border:0;border-bottom:1px solid rgba(122,158,255,.08);color:#E8EDFB;cursor:pointer;font-size:13px;text-align:left}#krr .sugg button:hover,#krr .sugg button.hi{background:rgba(0,224,255,.1)}#krr .sugg .sy{color:#00E0FF;font-weight:700;margin-left:8px}' +
      '#krr .chips{display:flex;flex-wrap:wrap;gap:6px}#krr .chipx{display:inline-flex;align-items:center;gap:6px;padding:6px 8px 6px 10px;border-radius:20px;border:1px solid rgba(0,224,255,.35);background:rgba(0,224,255,.07);font-size:12.5px}#krr .chipx b{color:#00E0FF}#krr .chipx button{border:0;background:rgba(255,77,106,.15);color:#FF8FA3;border-radius:50%;width:20px;height:20px;cursor:pointer;font-size:11px}' +
      '#krr .light{display:flex;gap:16px;align-items:center;border-radius:14px;padding:16px;border:1px solid;margin:6px 0 12px}#krr .light .dot{width:64px;height:64px;border-radius:50%;flex:0 0 64px;box-shadow:0 0 28px currentColor}#krr .light .lv{font-size:24px;font-weight:800}#krr .light .rule{font-size:12.5px;color:#9BA6C4;line-height:1.5;margin-top:3px}' +
      '#krr .say{margin:0;padding-left:0;list-style:none}#krr .say li{font-size:15px;line-height:1.6;margin:0 0 8px;padding-left:22px;position:relative}#krr .say li:before{content:"•";position:absolute;left:6px;color:#00E0FF}' +
      '#krr .tips li{font-size:13.5px}#krr .tips li:before{content:"→"}' +
      '#krr .actions{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}' +
      '#krr .ai{border:1px solid rgba(167,139,250,.35);background:rgba(167,139,250,.07);border-radius:12px;padding:12px;font-size:14px;line-height:1.6;white-space:pre-wrap}' +
      '#krr .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin:10px 0}#krr .card{border:1px solid rgba(122,158,255,.16);border-radius:11px;background:rgba(11,18,34,.6);padding:10px 12px}#krr .card .l{font-size:10.5px;color:#7C87A3;text-transform:uppercase;letter-spacing:.05em}#krr .card .v{font-size:19px;font-weight:750;margin-top:3px}#krr .card .s{font-size:11px;color:#9BA6C4;margin-top:2px}' +
      '#krr .sec{margin-top:14px}#krr .sec h3{font-size:13px;margin:0 0 8px;color:#C9D4EC;text-transform:uppercase;letter-spacing:.05em}' +
      '#krr .detail{border-top:1px solid rgba(122,158,255,.18);margin-top:14px;padding-top:6px}' +
      '#krr table{width:100%;border-collapse:collapse;font-size:12.5px}#krr th,#krr td{padding:6px 8px;border-bottom:1px solid rgba(122,158,255,.1);text-align:right}#krr th:first-child,#krr td:first-child{text-align:left}#krr th{color:#7C87A3;font-weight:600;font-size:11px}' +
      '#krr .bar{height:7px;border-radius:4px;background:rgba(122,158,255,.12);position:relative;min-width:60px}#krr .bar i{position:absolute;left:0;top:0;bottom:0;border-radius:4px}' +
      '#krr .grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}' +
      '#krr .steps{display:flex;flex-direction:column;gap:12px}#krr .step{border:1px solid rgba(122,158,255,.18);border-radius:12px;padding:12px;background:rgba(11,18,34,.55)}#krr .step h4{margin:0 0 8px;font-size:13.5px;color:#C9D4EC}' +
      '#krr .pills{display:flex;flex-wrap:wrap;gap:6px}#krr .pill{padding:8px 11px;border-radius:9px;border:1px solid rgba(122,158,255,.25);background:rgba(21,28,45,.6);color:#C9D4EC;cursor:pointer;font-size:12.5px}#krr .pill.on{border-color:#00E0FF;background:rgba(0,224,255,.14);color:#00E0FF;font-weight:700}#krr .pill small{display:block;font-size:10.5px;color:#7C87A3;font-weight:400}' +
      '#krr .spot{padding:8px 10px;border-radius:9px;border:1px dashed #2BE38B;color:#2BE38B;font-size:12px;font-weight:700}' +
      '#krr .hm td{text-align:center;font-size:11px;color:#06090F;font-weight:650}#krr .scroll{overflow-x:auto}' +
      '@media(max-width:860px){#krr .start{grid-template-columns:1fr}}' +
      '@media(max-width:760px){#krr .grid2{grid-template-columns:1fr}#krr{padding:14px 12px;width:100vw;margin:0;border-radius:0;min-height:100%}#krr .card .v{font-size:16px}#krr .light .dot{width:46px;height:46px;flex-basis:46px}#krr .light .lv{font-size:20px}#krr .say li{font-size:14px}}';
    document.head.appendChild(st);
  }
  function shell() {
    css();
    var ov = document.getElementById('krr-ov');
    if (!ov) {
      ov = document.createElement('div'); ov.id = 'krr-ov';
      ov.innerHTML = '<div id="krr"></div>';
      ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
      document.body.appendChild(ov);
      document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && ov.classList.contains('show')) close(); });
    }
    return ov;
  }
  function close() { var ov = document.getElementById('krr-ov'); if (ov) ov.classList.remove('show'); }
  function isOpen() { var ov = document.getElementById('krr-ov'); return !!(ov && ov.classList.contains('show')); }

  function header() {
    return '<div class="hd"><h2>📉 ' + esc(L('Riesgo de mi cartera', 'My portfolio risk')) + '</h2>' +
      '<button class="btn gh" data-act="lang" title="' + esc(L('Cambiar idioma', 'Switch language')) + '">' + (en() ? 'ES' : 'EN') + '</button>' +
      '<button class="x" data-act="close" title="' + esc(L('Cerrar', 'Close')) + '">✕</button></div>' +
      '<div class="ktabs"><button class="ktab' + (S.tab === 'var' ? ' on' : '') + '" data-tab="var">📉 ' + esc(L('¿Cuánto podría perder?', 'How much could I lose?')) + '</button>' +
      '<button class="ktab' + (S.tab === 'vega' ? ' on' : '') + '" data-tab="vega">🌪 ' + esc(L('Opciones (Vega)', 'Options (Vega)')) + '</button></div>';
  }

  function render() {
    var box = document.getElementById('krr'); if (!box) return;
    registerExplain();
    var sc = document.getElementById('krr-ov'); var top = sc ? sc.scrollTop : 0;
    box.innerHTML = header() + (S.tab === 'var' ? viewVar() : viewVega());
    wire(box);
    if (S.tab === 'var' && S.view === 'result' && S.rep && S.rep.ok && S.detail) drawHist();
    if (sc) sc.scrollTop = top;
  }

  /* ════════════════════════ VaR ════════════════════════════════════════ */
  function viewVar() {
    if (S.busy) return '<div class="info" style="text-align:center;padding:26px">⏳ ' + esc(L('Calculando con precios reales del último año… (puede tardar unos segundos)', 'Computing with real prices from the last year… (may take a few seconds)')) + '</div>';
    if (S.view === 'result' && S.rep) return viewResult();
    return viewStart();
  }

  /* ── pantalla de inicio guiada ───────────────────────────────────────── */
  function viewStart() {
    var h = '<p class="lead">' + esc(L(
      'Descubre, en lenguaje simple, cuánto podría perder tu cartera en un mal día. Elige cómo empezar:',
      'Find out, in plain words, how much your portfolio could lose on a bad day. Pick how to start:')) + '</p>';
    if (S.notice) h += '<div class="info">ℹ️ ' + esc(S.notice) + '</div>';
    h += '<div class="start">';
    // (a) mis posiciones — si no hay ninguna, va al final (primero lo que sí funciona)
    var mk = positionsFrom('market').positions.length, pfs = pfList();
    var hasMine = mk > 0 || pfs.some(function (p) { return positionsFrom('pf:' + p.id).positions.length > 0; });
    var ha = '<div class="opt" style="order:' + (hasMine ? 0 : 3) + '"><div class="k">📂</div><h3>' + esc(L('Usar mis posiciones', 'Use my positions')) + '</h3>' +
      '<div class="note">' + esc(L('Las acciones que ya guardaste en la app.', 'The stocks you already saved in the app.')) + '</div>' +
      srcBtn('market', L('Mi portafolio (Mercado)', 'My portfolio (Market)'), mk,
        L('Vacío — agrega acciones en Mercado (✏️ en cada fila)', 'Empty — add stocks in Market (✏️ on each row)'));
    pfs.forEach(function (p) {
      ha += srcBtn('pf:' + p.id, '🧪 ' + (p.name || p.id), positionsFrom('pf:' + p.id).positions.length,
        L('Sin acciones todavía — compra en la Cartera simulada', 'No stocks yet — buy in the simulated portfolio'));
    });
    if (!pfs.length) ha += '<div class="note">' + esc(L('Tip: en Mercado → Carteras puedes crear carteras simuladas.', 'Tip: in Market → Portfolios you can create simulated portfolios.')) + '</div>';
    h += ha + '</div>';
    // (b) cartera rápida
    var qk = loadQuick(), tot = qk.reduce(function (a, x) { return a + x.usd; }, 0);
    h += '<div class="opt" style="order:1"><div class="k">🧺</div><h3>' + esc(L('Armar una cartera rápida', 'Build a quick portfolio')) + '</h3>' +
      '<div class="note">' + esc(L('1) Pon cuántos dólares. 2) Busca la empresa y tócala.', '1) Enter how many dollars. 2) Search the company and tap it.')) + '</div>' +
      '<div class="row" style="margin:0"><span style="color:#9BA6C4">$</span><input id="krr-amt" type="number" min="1" step="100" inputmode="decimal" value="' + esc(S.amt) + '" style="width:110px" aria-label="' + esc(L('Monto en dólares', 'Amount in dollars')) + '"></div>' +
      '<div class="qwrap"><input id="krr-q" autocomplete="off" style="width:100%" placeholder="' + esc(L('Buscar empresa: Nvidia, TSMC, AMD…', 'Search company: Nvidia, TSMC, AMD…')) + '" value="' + esc(S.q) + '"><div class="sugg" id="krr-sugg" style="display:none"></div></div>' +
      '<div class="chips">' + qk.map(function (x, i) {
        return '<span class="chipx"><b>' + esc(x.sym) + '</b> ' + esc(x.label) + ' · ' + money(x.usd) + ' <button data-qdel="' + i + '" title="' + esc(L('Quitar', 'Remove')) + '">✕</button></span>';
      }).join('') + '</div>' +
      (qk.length ? '<div class="note">' + esc(L('Total: ', 'Total: ')) + '<b style="color:#E8EDFB">' + money(tot) + '</b> · ' + esc(L('se convierte a acciones con el último precio de cierre real.', 'converted to shares at the latest real closing price.')) + '</div>' : '') +
      '<button class="btn" data-act="runquick"' + (qk.length ? '' : ' disabled') + '>' + esc(L('Calcular el riesgo', 'Compute the risk')) + '</button>' +
      (qk.length ? '<button class="btn gh" data-act="qclear">' + esc(L('Vaciar', 'Clear')) + '</button>' : '') + '</div>';
    // (c) ejemplos
    h += '<div class="opt" style="order:2"><div class="k">🎓</div><h3>' + esc(L('Probar con un ejemplo', 'Try an example')) + '</h3>' +
      '<div><span class="tag">' + esc(L('EJEMPLO', 'EXAMPLE')) + '</span> <span class="note">' + esc(L('Carteras de ' + money(EX_TOTAL) + ' HIPOTÉTICAS, repartidas en partes iguales, con precios reales.',
        'HYPOTHETICAL ' + money(EX_TOTAL) + ' portfolios, split equally, with real prices.')) + '</span></div>';
    EXAMPLES.forEach(function (ex) {
      var cs = ex.syms.filter(bySym);
      if (!cs.length) return;
      h += '<button class="pick" data-ex="' + ex.id + '"><span>' + ex.icon + ' ' + esc(en() ? ex.en : ex.es) + '<br><small>' + esc(en() ? ex.den : ex.des) + ' ' + esc(cs.join(' · ')) + '</small></span><span>›</span></button>';
    });
    h += '</div></div>';
    // avanzado: sintaxis de acciones
    h += '<div style="margin-top:14px"><button class="btn gh" data-act="adv">' + (S.advanced ? '▾ ' : '▸ ') + esc(L('Avanzado: escribir tickers con número de acciones', 'Advanced: type tickers with number of shares')) + '</button>';
    if (S.advanced) h += '<div class="row" style="margin-top:8px"><input id="krr-man" style="flex:1;min-width:200px" placeholder="' + esc(L('Ej: NVDA:10, AMD:20, TSM:5', 'E.g. NVDA:10, AMD:20, TSM:5')) + '" value="' + esc(S.manual) + '"><button class="btn" data-act="runman">' + esc(L('Calcular', 'Compute')) + '</button></div>';
    h += '</div><div class="note" style="margin-top:10px">' + esc(L('Usa precios diarios REALES del último año. Es una estimación del pasado, no una predicción, y no es una recomendación de compra o venta.',
      'Uses REAL daily prices from the last year. It is an estimate from the past, not a forecast, and not a buy or sell recommendation.')) + '</div>';
    return h;
  }
  function srcBtn(id, name, n, hint) {
    return '<button class="pick" data-src="' + esc(id) + '"' + (n ? '' : ' disabled') + '><span>' + esc(name) + '<br><small>' +
      esc(n ? (n + ' ' + L(n === 1 ? 'acción' : 'acciones', n === 1 ? 'stock' : 'stocks')) : hint) + '</small></span><span>' + (n ? '›' : '') + '</span></button>';
  }

  /* ── resultado en lenguaje simple ────────────────────────────────────── */
  function level(r) {
    var v = r.vol_ann_pct;
    if (v < 15) return { k: 'low', c: '#2BE38B', t: L('Riesgo BAJO', 'LOW risk') };
    if (v <= 30) return { k: 'mid', c: '#FFC400', t: L('Riesgo MEDIO', 'MEDIUM risk') };
    return { k: 'high', c: '#FF4D6A', t: L('Riesgo ALTO', 'HIGH risk') };
  }
  function avgCorr(r) {
    var c = r.correlation; if (!c || c.symbols.length < 2) return null;
    var s = 0, n = 0;
    c.matrix.forEach(function (row, i) { row.forEach(function (v, j) { if (j > i && v != null) { s += v; n++; } }); });
    return n ? s / n : null;
  }
  function nameOf(r, sym) { var l = (r.labels || {})[sym]; return l && l !== sym ? (l.indexOf('(') >= 0 ? l + ' · ' + sym : l + ' (' + sym + ')') : sym; }
  function sentences(r) {
    var out = [], v95 = r.var95, v99 = r.var99, pv = money(r.portfolio_value_usd);
    out.push(L('En un día malo (1 de cada 20), tu cartera de ' + pv + ' podría perder unos <b>' + money(v95.hist_1d_usd) + '</b> (' + pct(v95.hist_1d_pct, 1) + ').',
      'On a bad day (1 in 20), your ' + pv + ' portfolio could lose about <b>' + money(v95.hist_1d_usd) + '</b> (' + pct(v95.hist_1d_pct, 1) + ').'));
    out.push(L('En el peor 1% de los días (1 de cada 100), la pérdida sería de unos <b>' + money(v99.hist_1d_usd) + '</b>.',
      'On the worst 1% of days (1 in 100), the loss would be about <b>' + money(v99.hist_1d_usd) + '</b>.'));
    if (r.beta_spy != null) {
      var b = r.beta_spy, bs = num(b, 2), ten = num(Math.abs(b) * 10, 0);
      if (b > 1.1) out.push(L('Se mueve <b>más que el mercado</b> (beta ' + bs + '): si el S&amp;P 500 cae 10%, tu cartera tiende a caer ~' + ten + '%.',
        'It moves <b>more than the market</b> (beta ' + bs + '): if the S&amp;P 500 falls 10%, your portfolio tends to fall ~' + ten + '%.'));
      else if (b < 0.9) out.push(L('Se mueve <b>menos que el mercado</b> (beta ' + bs + '): si el S&amp;P 500 cae 10%, tu cartera tiende a caer ~' + ten + '%.',
        'It moves <b>less than the market</b> (beta ' + bs + '): if the S&amp;P 500 falls 10%, your portfolio tends to fall ~' + ten + '%.'));
      else out.push(L('Se mueve <b>parecido al mercado</b> (beta ' + bs + ').', 'It moves <b>about like the market</b> (beta ' + bs + ').'));
    }
    var top = (r.positions || [])[0];
    if (top && r.positions.length > 1) out.push(L('La acción que más riesgo aporta es <b>' + esc(nameOf(r, top.symbol)) + '</b>: ' + pct(top.risk_contrib_pct, 0) + ' del riesgo con ' + pct(top.weight_pct, 0) + ' del dinero.',
      'The stock adding the most risk is <b>' + esc(nameOf(r, top.symbol)) + '</b>: ' + pct(top.risk_contrib_pct, 0) + ' of the risk with ' + pct(top.weight_pct, 0) + ' of the money.'));
    if (r.max_drawdown_pct != null && r.max_drawdown_pct < 0) out.push(L('En el último año, su peor caída desde un máximo fue de <b>' + pct(r.max_drawdown_pct, 0) + '</b>' + (r.max_drawdown_date ? ' (tocó fondo el ' + esc(r.max_drawdown_date) + ')' : '') + '.',
      'Over the last year, its worst fall from a peak was <b>' + pct(r.max_drawdown_pct, 0) + '</b>' + (r.max_drawdown_date ? ' (bottom on ' + esc(r.max_drawdown_date) + ')' : '') + '.'));
    return out;
  }
  function tips(r, lv) {
    var out = [], n = (r.positions || []).length, top = (r.positions || [])[0], ac = avgCorr(r);
    if (n === 1) out.push(L('Tienes una sola acción: todo tu riesgo depende de ella. Combinar varias empresas de sectores distintos suele suavizar los movimientos.',
      'You hold a single stock: all your risk depends on it. Combining several companies from different sectors usually smooths the swings.'));
    else if (top && top.risk_contrib_pct >= 40) out.push(L('Una sola acción (' + esc(top.symbol) + ') concentra ' + pct(top.risk_contrib_pct, 0) + ' del riesgo. Repartir mejor el dinero suele bajar esa dependencia.',
      'A single stock (' + esc(top.symbol) + ') concentrates ' + pct(top.risk_contrib_pct, 0) + ' of the risk. Spreading the money more evenly usually lowers that dependence.'));
    if (ac != null && ac >= 0.6) out.push(L('Tus acciones se mueven muy parecido (correlación promedio ' + num(ac, 2) + '): cuando una cae, las demás suelen caer también. Empresas de sectores diferentes diversifican más.',
      'Your stocks move very alike (average correlation ' + num(ac, 2) + '): when one falls, the others tend to fall too. Companies from different sectors diversify more.'));
    if (r.beta_spy != null && r.beta_spy > 1.2) out.push(L('Tu cartera amplifica los movimientos del mercado: en las caídas generales, espera caídas mayores.',
      'Your portfolio amplifies market moves: in broad sell-offs, expect bigger drops.'));
    if (lv.k === 'high') out.push(L('Si una caída como la de arriba te quitaría el sueño, tener una parte en activos más estables (por ejemplo fondos amplios o bonos) baja el riesgo total.',
      'If a drop like the one above would keep you up at night, holding part in steadier assets (for example broad funds or bonds) lowers total risk.'));
    var bt = r.backtest95;
    if (bt && bt.verdict === 'subestima') out.push(L('En los últimos meses las pérdidas reales superaron el "día malo" más veces de lo esperado (prueba de Kupiec): toma estas cifras como un mínimo.',
      'In recent months real losses beat the "bad day" figure more often than expected (Kupiec test): treat these numbers as a floor.'));
    if (!out.length) out.push(L('Tu cartera no muestra una concentración fuerte. Revisa el riesgo de nuevo cuando cambies posiciones.',
      'Your portfolio shows no strong concentration. Check the risk again when you change positions.'));
    return out;
  }
  function viewResult() {
    var r = S.rep, spec = S.spec || {};
    var h = '<div class="row"><button class="btn gh" data-act="back">← ' + esc(L('Cambiar cartera', 'Change portfolio')) + '</button>' +
      '<div style="flex:1;min-width:160px;font-size:13.5px;color:#C9D4EC"><b>' + esc(spec.label || '') + '</b>' +
      (spec.hypo ? ' <span class="tag">' + esc(L('EJEMPLO HIPOTÉTICO', 'HYPOTHETICAL EXAMPLE')) + '</span>' : '') + '</div></div>';
    if (!r.ok) return h + errorBox(r) + excluded(r);
    var lv = level(r);
    h += '<div class="light" style="border-color:' + lv.c + '55;background:' + lv.c + '12"><div class="dot" style="background:' + lv.c + ';color:' + lv.c + '"></div><div style="min-width:0">' +
      '<div class="lv" style="color:' + lv.c + '">' + esc(lv.t) + chip('risk_level') + '</div>' +
      '<div class="rule">' + esc(L('Se mueve ~' + num(r.vol_ann_pct, 0) + '% al año.', 'It swings ~' + num(r.vol_ann_pct, 0) + '% a year.')) + ' ' +
      esc(L('Regla: bajo < 15% · medio 15–30% · alto > 30%.', 'Rule: low < 15% · medium 15–30% · high > 30%.')) + '</div></div></div>';
    h += '<ul class="say">' + sentences(r).map(function (s) { return '<li>' + s + '</li>'; }).join('') + '</ul>';
    h += '<div class="note">' + esc(L('Calculado con precios diarios reales del ' + r.from + ' al ' + r.as_of + '. Es una estimación basada en el pasado, no una predicción.',
      'Computed with real daily prices from ' + r.from + ' to ' + r.as_of + '. It is an estimate based on the past, not a forecast.')) + '</div>';
    h += excluded(r);
    h += '<div class="sec"><h3>💡 ' + esc(L('Qué podrías hacer', 'What you could do')) + '</h3><ul class="say tips">' +
      tips(r, lv).map(function (s) { return '<li>' + s + '</li>'; }).join('') + '</ul>' +
      '<div class="note">' + esc(L('Ideas educativas y generales — no son recomendaciones de compra o venta.', 'Educational, general ideas — not buy or sell recommendations.')) + '</div></div>';
    h += '<div class="actions"><button class="btn" data-act="ai"' + (S.aiBusy ? ' disabled' : '') + '>🤖 ' + esc(S.aiBusy ? L('Pensando…', 'Thinking…') : L('Explícame con IA', 'Explain it with AI')) + '</button>' +
      '<button class="btn gh" data-act="detail">' + (S.detail ? '▾ ' : '▸ ') + '🔬 ' + esc(L('Ver detalle técnico', 'Show technical detail')) + '</button>' +
      '<button class="btn gh" data-act="print">🖨 ' + esc(L('Imprimir / PDF', 'Print / PDF')) + '</button></div>';
    if (S.ai) h += '<div class="ai">' + (S.ai.err ? '<span style="color:#fbbf24">' + esc(S.ai.err) + '</span>' : esc(S.ai.text)) + '</div>';
    if (S.detail) h += '<div class="detail">' + techVar(r) + '</div>';
    return h;
  }
  function errorBox(r) {
    var code = r.error_code || '', msg, todo;
    if (code === 'network') { msg = L('No pude conectar con el servidor.', 'I could not reach the server.'); todo = L('Revisa tu internet y vuelve a intentar en un minuto.', 'Check your internet and try again in a minute.'); }
    else if (code === 'rate_limited') { msg = L('Hiciste muchos reportes seguidos.', 'You ran many reports in a row.'); todo = L('Espera unos minutos y vuelve a intentar (hay un límite por hora).', 'Wait a few minutes and try again (there is an hourly limit).'); }
    else if (code === 'data_unavailable') { msg = L('El proveedor de precios (Yahoo Finance) no respondió o no tiene historia para estas acciones.', 'The price provider (Yahoo Finance) did not answer or has no history for these stocks.'); todo = L('Suele ser temporal: prueba de nuevo en unos minutos. No tienes que configurar nada.', 'It is usually temporary: try again in a few minutes. Nothing to configure.'); }
    else if (code === 'short_history') { msg = L('Alguna acción cotiza hace muy poco: no hay 3 meses de precios en común.', 'A stock has been listed too recently: there are not 3 months of prices in common.'); todo = L('Quita la empresa más nueva y vuelve a calcular.', 'Remove the newest company and compute again.'); }
    else if (code === 'no_positions') { msg = L('No hay acciones con cantidad para calcular.', 'There are no stocks with an amount to compute.'); todo = L('Vuelve y agrega al menos una empresa.', 'Go back and add at least one company.'); }
    else { msg = L('No se pudo calcular el reporte.', 'The report could not be computed.') + (r.error && !en() ? ' (' + r.error + ')' : ''); todo = L('Vuelve a intentar en un momento.', 'Try again in a moment.'); }
    return '<div class="warn">⚠️ <b>' + esc(msg) + '</b><br>' + esc(todo) + '</div><div class="actions"><button class="btn" data-act="retry">↻ ' + esc(L('Reintentar', 'Retry')) + '</button><button class="btn gh" data-act="back">← ' + esc(L('Volver', 'Back')) + '</button></div>';
  }
  function reasonText(e) {
    var c = e.reason_code || '', r = e.reason || '';
    if (!en()) return r;
    if (c === 'no_history' || /historia/.test(r)) return 'not enough price history';
    if (c === 'no_fx' || /cambio/.test(r)) return 'no exchange rate to USD';
    if (/inválido/.test(r)) return 'invalid ticker';
    if (/precio en vivo/.test(r)) return 'no live price for the stock';
    if (/volatilidad/.test(r)) return 'no implied or historical volatility';
    if (/incompletos/.test(r)) return 'incomplete data';
    return r;
  }
  function excluded(r) {
    var ex = (r && r.excluded) || [], sk = S._skipped || [];
    if (!ex.length && !sk.length) return '';
    return '<div class="warn">' + esc(L('No se incluyeron: ', 'Not included: ')) +
      ex.map(function (e) { return esc((e.label || e.symbol) + ' (' + reasonText(e) + ')'); }).concat(sk.map(function (x) { return esc(x + ' (' + L('no cotiza o sin cantidad', 'not listed or no quantity') + ')'); })).join(' · ') + '</div>';
  }

  /* ── detalle técnico (lo de antes, plegado) ──────────────────────────── */
  function techVar(r) {
    var v95 = r.var95, v99 = r.var99, h = '';
    h += '<div class="note">' + esc(L('Datos: ', 'Data: ')) + esc(r.source) + ' · ' + esc(r.from) + ' → ' + esc(r.as_of) + ' (' + r.days + ' ' + esc(L('días', 'days')) + ')</div>';
    h += '<div class="cards">' +
      card(L('Valor de la cartera', 'Portfolio value'), usd(r.portfolio_value_usd), L('a precio de cierre', 'at closing price')) +
      card(L('Volatilidad anual', 'Annual volatility') + chip('vol_ann'), pct(r.vol_ann_pct, 1), L('diaria ', 'daily ') + pct(r.vol_daily_pct)) +
      card('VaR 95% · 1 ' + L('día', 'day') + chip('var'), usd(v95.hist_1d_usd), pct(v95.hist_1d_pct) + ' · ' + L('paramétrico ', 'parametric ') + usd(v95.param_1d_usd) + chip('var_method')) +
      card('CVaR 95% · 1 ' + L('día', 'day') + chip('cvar'), usd(v95.cvar_1d_usd), pct(v95.cvar_1d_pct)) +
      card('VaR 99% · 1 ' + L('día', 'day'), usd(v99.hist_1d_usd), pct(v99.hist_1d_pct) + ' · CVaR ' + usd(v99.cvar_1d_usd)) +
      card('VaR 95% · ' + r.horizon_days + ' ' + L('días', 'days'), usd(v95.hist_nd_usd), pct(v95.hist_nd_pct) + ' (√' + r.horizon_days + ')') +
      card(L('Máxima caída', 'Max drawdown') + chip('drawdown'), pct(r.max_drawdown_pct, 1), r.max_drawdown_date ? L('fondo el ', 'trough on ') + r.max_drawdown_date : '') +
      card(L('Beta vs S&P 500', 'Beta vs S&P 500') + chip('beta'), r.beta_spy == null ? '—' : num(r.beta_spy, 2), r.corr_spy == null ? '' : L('correlación ', 'correlation ') + num(r.corr_spy, 2)) +
      card('Sharpe' + chip('sharpe'), r.sharpe == null ? '—' : num(r.sharpe, 2), L('retorno anual compuesto ', 'compounded annual return ') + pct(r.return_ann_pct, 1) + (r.risk_free_pct != null ? ' − ' + L('tasa libre ', 'risk-free ') + pct(r.risk_free_pct, 2) : '')) +
      card(L('Diversificación', 'Diversification') + chip('correlation'), r.diversification_ratio == null ? '—' : num(r.diversification_ratio, 2) + '×', L('1 = sin beneficio', '1 = no benefit')) +
      '</div>';
    var bt = r.backtest95;
    if (bt && bt.method === 'rolling_oos') {
      h += '<div class="note">' + chip('backtest') + ' ' + esc(L(
        'Backtest fuera de muestra: en los últimos ' + bt.days + ' días la pérdida real superó el VaR 95% (calculado cada día con los ' + bt.window + ' días previos) ' + bt.breaches + ' veces; lo esperado es ~' + num(bt.expected, 1) + ' (prueba de Kupiec p = ' + num(bt.kupiec_p, 3) + ').',
        'Out-of-sample backtest: over the last ' + bt.days + ' days the real loss exceeded the 95% VaR (computed each day from the previous ' + bt.window + ' days) ' + bt.breaches + ' times; about ' + num(bt.expected, 1) + ' expected (Kupiec test p = ' + num(bt.kupiec_p, 3) + ').')) +
        (bt.verdict === 'subestima' ? ' <b style="color:#FFB300">' + esc(L('El VaR está subestimando el riesgo.', 'VaR is underestimating risk.')) + '</b>' : '') +
        (bt.verdict === 'sobreestima' ? ' <b style="color:#5FC6E8">' + esc(L('El VaR fue más prudente de lo necesario en este período.', 'VaR was more cautious than needed in this period.')) + '</b>' : '') +
        (bt.low_power ? ' ' + esc(L('(Pocos días para concluir con fuerza.)', '(Few days to conclude strongly.)')) : '') + '</div>';
    } else if (bt) {
      h += '<div class="note">' + chip('backtest') + ' ' + esc(L(
        'En el último año la pérdida real superó el VaR 95% en ' + bt.breaches + ' de ' + bt.days + ' días (lo esperado es ~' + num(bt.expected, 1) + ').',
        'Over the last year the real loss exceeded the 95% VaR on ' + bt.breaches + ' of ' + bt.days + ' days (about ' + num(bt.expected, 1) + ' expected).')) + '</div>';
    }
    if (r.unadjusted_symbols && r.unadjusted_symbols.length) {
      h += '<div class="warn">' + esc(L('Cierres SIN ajustar por dividendos/splits en: ' + r.unadjusted_symbols.join(', ') + ' (el proveedor no entregó la serie ajustada).', 'Closes NOT adjusted for dividends/splits in: ' + r.unadjusted_symbols.join(', ') + ' (the provider did not return the adjusted series).')) + '</div>';
    }
    h += '<div class="grid2"><div class="sec"><h3>' + esc(L('Distribución de retornos diarios', 'Daily return distribution')) + '</h3>' +
      '<div style="height:220px"><canvas id="krr-hist"></canvas></div><div class="note">' + esc(L('En rojo: días peores que el VaR 95%.', 'In red: days worse than the 95% VaR.')) + '</div></div>' +
      '<div class="sec"><h3>' + esc(L('Peores días reales', 'Worst real days')) + '</h3><table><tr><th>' + esc(L('Fecha', 'Date')) + '</th><th>%</th><th>USD</th></tr>' +
      (r.worst_days || []).map(function (d) { return '<tr><td>' + esc(d.date) + '</td><td style="color:#FF4D6A">' + pct(d.pct) + '</td><td>' + usd(d.usd) + '</td></tr>'; }).join('') + '</table></div></div>';
    var lab = r.labels || {};
    h += '<div class="sec"><h3>' + esc(L('¿Quién pone el riesgo?', 'Who brings the risk?')) + chip('risk_contrib') + '</h3><div class="scroll"><table><tr><th>' + esc(L('Posición', 'Position')) + '</th><th>' + esc(L('Valor', 'Value')) + '</th><th>' + esc(L('Peso', 'Weight')) + '</th><th>' + esc(L('Aporte al riesgo', 'Risk share')) + '</th><th></th><th>' + esc(L('Vol. anual', 'Ann. vol')) + '</th></tr>' +
      r.positions.map(function (p) {
        var hot = p.risk_contrib_pct > p.weight_pct * 1.3;
        return '<tr><td>' + esc(lab[p.symbol] || p.symbol) + ' <span style="color:#7C87A3">' + esc(p.symbol) + '</span></td><td>' + usd(p.value_usd) + '</td><td>' + pct(p.weight_pct, 1) + '</td><td style="color:' + (hot ? '#FFB300' : '#E8EDFB') + '">' + pct(p.risk_contrib_pct, 1) + '</td>' +
          '<td style="width:22%"><div class="bar"><i style="width:' + Math.max(0, Math.min(100, p.risk_contrib_pct)) + '%;background:' + (hot ? '#FFB300' : '#00E0FF') + '"></i></div></td><td>' + pct(p.vol_ann_pct, 1) + '</td></tr>';
      }).join('') + '</table></div><div class="note">' + esc(L('En ámbar: aporta mucho más riesgo que su peso en dinero.', 'Amber: brings far more risk than its money weight.')) + '</div></div>';
    if (r.converted && r.converted.length) {
      h += '<div class="sec"><h3>' + esc(L('Dólares → acciones', 'Dollars → shares')) + '</h3><div class="scroll"><table><tr><th>' + esc(L('Empresa', 'Company')) + '</th><th>USD</th><th>' + esc(L('Precio de cierre', 'Closing price')) + '</th><th>' + esc(L('Acciones', 'Shares')) + '</th><th>' + esc(L('Fecha', 'Date')) + '</th></tr>' +
        r.converted.map(function (c) { return '<tr><td>' + esc(c.symbol) + '</td><td>' + usd(c.usd) + '</td><td>' + usd(c.price_usd) + '</td><td>' + num(c.shares, 3) + '</td><td>' + esc(c.date) + '</td></tr>'; }).join('') +
        '</table></div></div>';
    }
    h += heatmap(r);
    h += '<div class="note" style="margin-top:12px">' + esc(L(
      'Nota: una cartera solo de acciones tiene Vega 0. La Vega mide la sensibilidad de OPCIONES a la volatilidad — está en la otra pestaña.',
      'Note: a stock-only portfolio has zero Vega. Vega measures OPTIONS sensitivity to volatility — see the other tab.')) + '</div>';
    return h;
  }
  function card(l, v, s) { return '<div class="card"><div class="l">' + l + '</div><div class="v">' + v + '</div>' + (s ? '<div class="s">' + s + '</div>' : '') + '</div>'; }
  function heatmap(r) {
    var c = r.correlation; if (!c || c.symbols.length < 2) return '';
    var col = function (v) {
      if (v == null) return '#333';
      var t = Math.max(-1, Math.min(1, v));
      return t >= 0 ? 'rgba(255,77,106,' + (0.15 + 0.85 * t) + ')' : 'rgba(43,227,139,' + (0.15 + 0.85 * -t) + ')';
    };
    return '<div class="sec"><h3>' + esc(L('Correlaciones', 'Correlations')) + chip('correlation') + '</h3><div class="scroll"><table class="hm"><tr><th></th>' +
      c.symbols.map(function (s) { return '<th>' + esc(s) + '</th>'; }).join('') + '</tr>' +
      c.matrix.map(function (row, i) {
        return '<tr><th style="text-align:left">' + esc(c.symbols[i]) + '</th>' + row.map(function (v) { return '<td style="background:' + col(v) + '">' + (v == null ? '—' : num(v, 2)) + '</td>'; }).join('') + '</tr>';
      }).join('') + '</table></div><div class="note">' + esc(L('Rojo = se mueven juntas (no diversifican); verde = en sentido contrario (cubren).', 'Red = move together (no diversification); green = opposite (hedge).')) + '</div></div>';
  }
  function drawHist() {
    var r = S.rep, cv = document.getElementById('krr-hist');
    if (!cv || !window.Chart || !r.histogram) return;
    if (S.chart) { try { S.chart.destroy(); } catch (e) {} }
    var ed = r.histogram.edges_pct, cnt = r.histogram.counts, cut = -r.var95.hist_1d_pct;
    var labels = cnt.map(function (_, i) { return num((ed[i] + ed[i + 1]) / 2, 1) + '%'; });
    var colors = cnt.map(function (_, i) { return ed[i + 1] <= cut ? '#FF4D6A' : '#00E0FF'; });
    S.chart = new window.Chart(cv.getContext('2d'), {
      type: 'bar', data: { labels: labels, datasets: [{ data: cnt, backgroundColor: colors, borderWidth: 0 }] },
      options: { responsive: true, maintainAspectRatio: false, animation: false, plugins: { legend: { display: false } },
        scales: { x: { ticks: { color: '#7C87A3', maxTicksLimit: 8, font: { size: 10 } }, grid: { display: false } },
                  y: { ticks: { color: '#7C87A3', font: { size: 10 } }, grid: { color: 'rgba(122,158,255,.08)' } } } },
    });
  }

  /* ── cálculo ─────────────────────────────────────────────────────────── */
  function postJSON(url, body) {
    return fetch(base() + url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (d) {
          d = d || {};
          if (r.status === 429) return { ok: false, error_code: 'rate_limited', error: d.error };
          if (d.offline || r.status === 502 || r.status === 503 || r.status === 504) return { ok: false, error_code: 'network', error: d.error };
          if (!r.ok && d.ok === undefined) d.ok = false;
          if (!r.ok && !d.error) d.error = 'HTTP ' + r.status;
          return d;
        });
      })
      .catch(function () { return { ok: false, error_code: 'network' }; });
  }
  function runSpec(spec) {
    if (S.busy || !spec || !spec.positions || !spec.positions.length) return;
    S.spec = spec; S._skipped = spec.skipped || []; S.ai = null; S.notice = null;
    S.busy = true; S.view = 'result'; render();
    postJSON('/api/portfolio/risk_report', { positions: spec.positions, horizon_days: 10 })
      .then(function (d) { S.rep = d; })
      .then(function () { S.busy = false; render(); });
  }
  function runSource(src) {
    var got = positionsFrom(src);
    if (!got.positions.length) {
      S.view = 'start';
      S.notice = src === 'market'
        ? L('Tu portafolio de Mercado está vacío. Elige otra opción: arma una cartera rápida en dólares o prueba un ejemplo.', 'Your Market portfolio is empty. Pick another option: build a quick portfolio in dollars or try an example.')
        : src === 'manual' ? L('No entendí los tickers. Usa el formato NVDA:10, AMD:5 — o mejor, arma una cartera rápida en dólares.', 'I could not read the tickers. Use the NVDA:10, AMD:5 format — or better, build a quick portfolio in dollars.')
          : L('Esa cartera simulada no tiene acciones todavía. Elige otra opción.', 'That simulated portfolio has no stocks yet. Pick another option.');
      return render();
    }
    S.source = src;
    runSpec({ positions: got.positions, skipped: got.skipped, label: sourceName(src), kind: 'mine' });
  }
  function runQuick() {
    var qk = loadQuick(); if (!qk.length) return;
    runSpec({ positions: qk.map(function (x) { return { symbol: x.sym, usd: x.usd, label: x.label }; }), label: L('Mi cartera rápida', 'My quick portfolio'), kind: 'quick' });
  }
  function runExample(id) {
    var ex = EXAMPLES.filter(function (e) { return e.id === id; })[0]; if (!ex) return;
    runSpec({ positions: examplePositions(ex), label: L('Ejemplo: ', 'Example: ') + (en() ? ex.en : ex.es), kind: 'example', hypo: true, exId: id });
  }
  function addQuick(c) {
    var amt = parseFloat((document.getElementById('krr-amt') || {}).value);
    if (!(amt > 0)) amt = 1000;
    S.amt = amt;
    var qk = loadQuick(), ex = qk.filter(function (x) { return x.sym === c.sym; })[0];
    if (ex) ex.usd += amt; else qk.push({ sym: c.sym, label: c.label, usd: amt });
    saveQuick(qk.slice(0, 30)); S.q = ''; render();
    var q = document.getElementById('krr-q'); if (q) q.focus();
  }

  /* ── "Explícame con IA" (opcional; las cifras van en el prompt y el
        guardián de cifras del server las verifica) ────────────────────── */
  function explainAI() {
    var r = S.rep; if (!r || !r.ok || S.aiBusy) return;
    if (!window.DataLayer || !window.DataLayer.aiComplete) { S.ai = { err: L('La IA no está disponible aquí.', 'AI is not available here.') }; return render(); }
    var lv = level(r), plain = sentences(r).map(function (s) { return '- ' + s.replace(/<[^>]+>/g, '').replace(/&amp;/g, '&'); }).join('\n');
    var pos = r.positions.map(function (p) { return p.symbol + ': ' + L('peso ', 'weight ') + p.weight_pct + '%, ' + L('aporte al riesgo ', 'risk share ') + p.risk_contrib_pct + '%, ' + L('vol. anual ', 'ann. vol ') + p.vol_ann_pct + '%'; }).join('\n');
    var sys = L('Eres un educador financiero paciente. Explicas el riesgo de una cartera a alguien SIN conocimientos financieros, en español simple, sin jerga (si usas un término, lo explicas). Usa SOLO las cifras que te doy. NUNCA recomiendes comprar ni vender un activo concreto. Máximo 150 palabras, sin títulos.',
      'You are a patient financial educator. You explain portfolio risk to someone with NO financial background, in plain English, no jargon (if you use a term, explain it). Use ONLY the figures given. NEVER recommend buying or selling a specific asset. Max 150 words, no headings.');
    var prompt = L('Datos reales de la cartera (precios diarios ' + r.from + ' a ' + r.as_of + '):\n', 'Real portfolio data (daily prices ' + r.from + ' to ' + r.as_of + '):\n') +
      L('Valor: $', 'Value: $') + r.portfolio_value_usd + '\n' + L('Nivel: ', 'Level: ') + lv.t + ' (' + L('volatilidad anual ', 'annual volatility ') + r.vol_ann_pct + '%)\n' +
      'VaR 95% 1d: $' + r.var95.hist_1d_usd + ' (' + r.var95.hist_1d_pct + '%) · VaR 99% 1d: $' + r.var99.hist_1d_usd + ' · CVaR 95% 1d: $' + r.var95.cvar_1d_usd + '\n' +
      'Beta S&P 500: ' + r.beta_spy + ' · ' + L('máxima caída ', 'max drawdown ') + r.max_drawdown_pct + '%\n' + pos + '\n\n' +
      L('Resumen ya mostrado al usuario:\n', 'Summary already shown to the user:\n') + plain + '\n\n' +
      L('Explícale qué significa esto para él con una analogía cotidiana y qué preguntas debería hacerse.', 'Explain what this means for them with an everyday analogy and which questions they should ask themselves.');
    S.aiBusy = true; S.ai = null; render();
    window.DataLayer.aiComplete(sys, prompt, 500)
      .then(function (t) { S.ai = { text: String(t || '').trim() || L('(sin respuesta)', '(no answer)') }; })
      .catch(function () { S.ai = { err: L('La IA no está disponible ahora. El resumen de arriba ya está calculado con tus datos reales.', 'AI is not available right now. The summary above is already computed from your real data.') }; })
      .then(function () { S.aiBusy = false; render(); });
  }

  /* ════════════════════════ Vega ═══════════════════════════════════════ */
  function fmtDate(e) {
    try { return new Date(e + 'T12:00:00Z').toLocaleDateString(en() ? 'en-US' : 'es-ES', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }); } catch (x) { return e; }
  }
  function daysTo(e) { var d = Math.round((Date.parse(e + 'T00:00:00Z') - Date.now()) / 864e5); return isFinite(d) ? Math.max(0, d) : null; }
  function nearStrikes(ch) {
    var ks = (ch.strikes || []).slice().sort(function (a, b) { return a - b; });
    if (!ks.length) return [];
    var sp = +ch.spot;
    if (!sp) { var m = Math.floor(ks.length / 2); return ks.slice(Math.max(0, m - 6), m + 6); }
    return ks.map(function (k) { return { k: k, d: Math.abs(k - sp) }; }).sort(function (a, b) { return a.d - b.d; })
      .slice(0, 12).map(function (x) { return x.k; }).sort(function (a, b) { return a - b; });
  }
  function viewVega() {
    var opts = loadOpts();
    var h = '<div class="info">🧭 <b>' + esc(L('¿Esto es para ti?', 'Is this for you?')) + '</b> ' + esc(L(
      'Solo si tienes (o quieres estudiar) OPCIONES. Tus acciones normales no tienen Vega: su valor no depende directamente de la volatilidad. Si no usas opciones, puedes ignorar esta pestaña.',
      'Only if you hold (or want to study) OPTIONS. Regular stocks have no Vega: their value does not depend directly on volatility. If you do not use options, you can ignore this tab.')) +
      chip('options_basics') + ' ' + chip('vega') + '</div>';
    h += '<div class="steps">';
    // paso 1: empresa
    var mine = [];
    try { var NB = window.NODE_BY_ID || {}, pos = (window.MKT && window.MKT.pos) || {}; Object.keys(pos).forEach(function (id) { var n = NB[id]; if (n && n.mkt && mine.indexOf(n.mkt) < 0) mine.push(n.mkt); }); } catch (e) {}
    var quick = mine.slice(0, 6); ['NVDA', 'AAPL', 'MSFT'].forEach(function (s) { if (quick.length < 6 && quick.indexOf(s) < 0 && bySym(s)) quick.push(s); });
    h += '<div class="step"><h4>1 · ' + esc(L('¿De qué empresa son las opciones?', 'Which company are the options on?')) + '</h4>' +
      '<div class="qwrap" style="max-width:420px"><input id="kv-q" autocomplete="off" style="width:100%" placeholder="' + esc(L('Buscar empresa: Nvidia, Apple…', 'Search company: Nvidia, Apple…')) + '" value="' + esc(S.vq) + '"><div class="sugg" id="kv-sugg" style="display:none"></div></div>' +
      '<div class="pills" style="margin-top:8px">' + quick.map(function (s) { return '<button class="pill' + (s === S.vsym ? ' on' : '') + '" data-vsym="' + esc(s) + '">' + esc(s) + '</button>'; }).join('') + '</div>' +
      (S.chainBusy ? '<div class="note" style="margin-top:6px">⏳ ' + esc(L('Buscando opciones listadas…', 'Looking up listed options…')) + '</div>' : '') +
      (S.chainErr ? '<div class="warn">' + esc(S.chainErr) + '</div>' : '') + '</div>';
    // paso 2: contrato
    var ch = S.chain;
    if (ch && ch.available && S.vsym) {
      var exps = (ch.expirations || []).slice(0, 10), ks = nearStrikes(ch), sp = +ch.spot, spotShown = false;
      h += '<div class="step"><h4>2 · ' + esc(L('Elige el contrato de ', 'Pick the contract on ')) + esc(S.vlabel || S.vsym) + (sp ? ' <span style="color:#2BE38B">· ' + esc(L('precio actual ', 'current price ')) + '$' + num(sp, 2) + '</span>' : '') + '</h4>' +
        '<div class="note">' + esc(L('Tipo', 'Type')) + chip('options_basics') + '</div><div class="pills" style="margin:4px 0 10px">' +
        '<button class="pill' + (S.vkind === 'call' ? ' on' : '') + '" data-vkind="call">Call<small>' + esc(L('gana si la acción sube', 'gains if the stock rises')) + '</small></button>' +
        '<button class="pill' + (S.vkind === 'put' ? ' on' : '') + '" data-vkind="put">Put<small>' + esc(L('gana si la acción baja', 'gains if the stock falls')) + '</small></button></div>' +
        '<div class="note">' + esc(L('Vencimiento', 'Expiry')) + '</div><div class="pills" style="margin:4px 0 10px">' +
        exps.map(function (e) { var d = daysTo(e); return '<button class="pill' + (e === S.vexp ? ' on' : '') + '" data-vexp="' + esc(e) + '">' + esc(fmtDate(e)) + (d != null ? '<small>' + d + ' ' + esc(d === 1 ? L('día', 'day') : L('días', 'days')) + '</small>' : '') + '</button>'; }).join('') + '</div>' +
        '<div class="note">' + esc(L('Precio de ejercicio (strike) — los más cercanos al precio actual', 'Strike price — the closest to the current price')) + '</div><div class="pills" style="margin:4px 0 10px">';
      ks.forEach(function (k) {
        if (sp && !spotShown && k > sp) { h += '<span class="spot">▼ $' + num(sp, 2) + '</span>'; spotShown = true; }
        h += '<button class="pill' + (k === S.vk ? ' on' : '') + '" data-vk="' + k + '">' + strike(k) + '</button>';
      });
      if (sp && !spotShown) h += '<span class="spot">▼ $' + num(sp, 2) + '</span>';
      h += '</div><div class="note">' + esc(L('¿Cuántos contratos? (1 contrato = 100 acciones)', 'How many contracts? (1 contract = 100 shares)')) + '</div>' +
        '<div class="row" style="margin-top:4px"><button class="btn gh" data-act="vminus">−</button><input id="kv-n" type="number" min="1" step="1" value="' + esc(S.vn) + '" style="width:70px;text-align:center"><button class="btn gh" data-act="vplus">＋</button>' +
        '<div class="pills"><button class="pill' + (S.vside === 'long' ? ' on' : '') + '" data-vside="long">' + esc(L('Compradas', 'Bought')) + '</button><button class="pill' + (S.vside === 'short' ? ' on' : '') + '" data-vside="short">' + esc(L('Vendidas', 'Sold')) + '</button></div></div>' +
        '<button class="btn" data-act="addopt"' + (S.vexp && S.vk != null ? '' : ' disabled') + '>＋ ' + esc(L('Agregar a mi lista', 'Add to my list')) + '</button>' +
        (S.vexp && S.vk != null ? '' : ' <span class="note">' + esc(L('Elige vencimiento y strike.', 'Pick expiry and strike.')) + '</span>') + '</div>';
    }
    // paso 3: lista + calcular
    h += '<div class="step"><h4>3 · ' + esc(L('Tus opciones (simuladas — no se envía ninguna orden)', 'Your options (simulated — no order is sent)')) + '</h4>';
    if (opts.length) {
      h += '<div class="chips">' + opts.map(function (o, i) {
        return '<span class="chipx"><b>' + esc(o.symbol) + '</b> ' + esc(String(o.kind).toUpperCase() + ' ' + strike(o.strike) + ' · ' + fmtDate(o.expiry) + ' · ' + (o.contracts < 0 ? L('vendidas ', 'sold ') : L('compradas ', 'bought ')) + Math.abs(o.contracts)) + ' <button data-del="' + i + '" title="' + esc(L('Quitar', 'Remove')) + '">✕</button></span>';
      }).join('') + '</div><div class="row" style="margin-top:10px"><button class="btn big" data-act="runvega"' + (S.busy ? ' disabled' : '') + '>' + esc(S.busy ? L('Calculando…', 'Computing…') : L('Calcular sensibilidad', 'Compute sensitivity')) + '</button></div>';
    } else {
      h += '<div class="note">' + esc(L('Aún no agregaste opciones. Sigue los pasos 1 y 2.', 'No options added yet. Follow steps 1 and 2.')) + '</div>';
    }
    h += '</div></div>';
    var r = S.vrep;
    if (!r) return h;
    if (!r.ok) {
      var net = r.error_code === 'network', rl = r.error_code === 'rate_limited';
      return h + '<div class="warn">⚠️ <b>' + esc(net ? L('No pude conectar con el servidor.', 'I could not reach the server.') : rl ? L('Hiciste muchos cálculos seguidos.', 'You ran many calculations in a row.') : L('No se pudieron valorar tus opciones.', 'Your options could not be valued.')) + '</b><br>' +
        esc(net ? L('Revisa tu internet y vuelve a intentar.', 'Check your internet and try again.') : rl ? L('Espera unos minutos.', 'Wait a few minutes.') : L('Suele ser porque el proveedor de datos (Yahoo Finance) no respondió. Prueba de nuevo en unos minutos.', 'Usually the data provider (Yahoo Finance) did not answer. Try again in a few minutes.')) +
        (r.excluded && r.excluded.length ? '<br>' + r.excluded.map(function (e) { return esc(e.symbol + ': ' + reasonText(e)); }).join(' · ') : '') + '</div>';
    }
    var t = r.totals;
    h += '<div class="sec"><h3>🗣 ' + esc(L('En pocas palabras', 'In short')) + '</h3><ul class="say">' + vegaSentences(r).map(function (s) { return '<li>' + s + '</li>'; }).join('') + '</ul>' +
      '<div class="note">' + esc(L('Modelo Black-Scholes con la volatilidad implícita en vivo de cada contrato. Es una estimación; no se envía ninguna orden.', 'Black-Scholes model with each contract\'s live implied volatility. It is an estimate; no order is sent.')) + '</div></div>';
    if (r.excluded && r.excluded.length) h += '<div class="warn">' + esc(L('No valoradas: ', 'Not valued: ')) + r.excluded.map(function (e) { return esc(e.symbol + ' (' + reasonText(e) + ')'); }).join(' · ') + '</div>';
    h += '<div class="actions"><button class="btn gh" data-act="vdetail">' + (S.vdetail ? '▾ ' : '▸ ') + '🔬 ' + esc(L('Ver detalle técnico', 'Show technical detail')) + '</button></div>';
    if (!S.vdetail) return h;
    h += '<div class="detail"><div class="cards">' +
      card('Vega' + chip('vega'), usd(t.vega_usd), L('por +1 punto de volatilidad', 'per +1 volatility point')) +
      card(L('Valor de las opciones', 'Options value'), usd(t.value_usd), L('según el modelo', 'per the model')) +
      card('Delta' + chip('delta'), (t.delta_shares >= 0 ? '+' : '') + num(t.delta_shares, 0) + ' ' + L('acc.', 'sh.'), L('equivalente en acciones', 'share equivalent')) +
      card('Theta' + chip('theta'), usd(t.theta_usd_day), L('por día que pasa', 'per day that passes')) +
      card('Gamma' + chip('gamma'), num(t.gamma, 2), L('cambio de Delta por $1', 'Delta change per $1')) +
      '</div>';
    h += '<div class="sec"><h3>' + esc(L('Si la volatilidad cambia…', 'If volatility changes…')) + '</h3><table><tr><th>' + esc(L('Cambio de volatilidad', 'Volatility change')) + '</th><th>' + esc(L('Ganancia / pérdida', 'Gain / loss')) + '</th></tr>' +
      r.vol_scenarios.map(function (s) { return '<tr><td>' + (s.shock_pts > 0 ? '+' : '') + s.shock_pts + ' ' + esc(L('puntos', 'points')) + '</td><td style="color:' + (s.pnl_usd >= 0 ? '#2BE38B' : '#FF4D6A') + '">' + usd(s.pnl_usd) + '</td></tr>'; }).join('') +
      '</table><div class="note">' + esc(L('Revaluación completa con el modelo (no solo Vega × cambio). Todo lo demás constante.', 'Full model revaluation (not just Vega × change). Everything else held constant.')) + '</div></div>';
    h += '<div class="sec"><h3>' + esc(L('Detalle por opción', 'Detail per option')) + '</h3><div class="scroll"><table><tr><th>' + esc(L('Contrato', 'Contract')) + '</th><th>' + esc(L('Días', 'Days')) + '</th><th>' + esc(L('Precio acción', 'Stock price')) + '</th><th>IV' + chip('iv') + '</th><th>' + esc(L('Modelo', 'Model')) + '</th><th>' + esc(L('Mercado (medio)', 'Market (mid)')) + '</th><th>Vega' + chip('vega') + '</th><th>Delta' + chip('delta') + '</th><th>Gamma' + chip('gamma') + '</th><th>Theta' + chip('theta') + '/' + esc(L('día', 'day')) + '</th></tr>' +
      r.positions.map(function (p) {
        return '<tr><td>' + esc(p.symbol + ' ' + p.kind.toUpperCase() + ' ' + p.strike + ' · ' + p.expiry + ' ×' + p.contracts) + '</td><td>' + p.days + '</td><td>' + usd(p.spot) + '</td><td title="' + esc(p.iv_source) + '">' + pct(p.iv_pct, 1) + (String(p.iv_source).indexOf('hist') === 0 ? '*' : '') + '</td><td>' + usd(p.model_price) + '</td><td>' + (p.market_mid == null ? '—' : usd(p.market_mid)) + '</td><td>' + usd(p.vega_usd) + '</td><td>' + num(p.delta_shares, 0) + '</td><td>' + num(p.gamma, 2) + '</td><td>' + usd(p.theta_usd_day) + '</td></tr>';
      }).join('') + '</table></div><div class="note">* ' + esc(L('volatilidad histórica de 1 año (el contrato no publica implícita).', '1-year historical volatility (the contract publishes no implied).')) +
      ' · ' + esc(r.model) + ' · ' + esc(L('tasa libre de riesgo ', 'risk-free rate ')) + num(r.rate.value_pct, 2) + '% (' + esc(r.rate.source) + ')</div></div>';
    h += greeksByUnderlying(r) + '</div>';
    return h;
  }
  function vegaSentences(r) {
    var t = r.totals, out = [], v = t.vega_usd, th = t.theta_usd_day, d = t.delta_shares;
    if (Math.abs(v) < 0.5) out.push(L('Tus opciones casi no reaccionan a cambios de volatilidad.', 'Your options barely react to volatility changes.'));
    else if (v > 0) out.push(L('Si la volatilidad del mercado sube 1 punto, tus opciones <b>ganan unos ' + money(v) + '</b>; si baja 1 punto, pierden más o menos lo mismo.',
      'If market volatility rises 1 point, your options <b>gain about ' + money(v) + '</b>; if it falls 1 point, they lose about the same.'));
    else out.push(L('Si la volatilidad del mercado sube 1 punto, tus opciones <b>pierden unos ' + money(-v) + '</b> (porque las vendiste); si baja, ganan más o menos lo mismo.',
      'If market volatility rises 1 point, your options <b>lose about ' + money(-v) + '</b> (because you sold them); if it falls, they gain about the same.'));
    if (th < -0.005) out.push(L('Cada día que pasa, aunque nada cambie, <b>pierden unos ' + money(-th) + '</b> de valor (el "costo del tiempo").', 'Each day that passes, even if nothing changes, they <b>lose about ' + money(-th) + '</b> in value (the "cost of time").'));
    else if (th > 0.005) out.push(L('Cada día que pasa, aunque nada cambie, <b>ganan unos ' + money(th) + '</b> (cobras el paso del tiempo por haberlas vendido).', 'Each day that passes, even if nothing changes, they <b>gain about ' + money(th) + '</b> (you collect time decay because you sold them).'));
    out.push(L('Hoy valen unos <b>' + money(t.value_usd) + '</b> según el modelo.', 'Today they are worth about <b>' + money(t.value_usd) + '</b> per the model.'));
    if (Math.abs(d) >= 1) out.push(d > 0
      ? L('Frente al precio, se comportan como tener <b>' + num(d, 0) + ' acciones</b>: si la acción sube $1, ganas ~' + money(d) + '.', 'Against the price, they behave like holding <b>' + num(d, 0) + ' shares</b>: if the stock rises $1, you gain ~' + money(d) + '.')
      : L('Frente al precio, se comportan como estar vendido en <b>' + num(-d, 0) + ' acciones</b>: si la acción sube $1, pierdes ~' + money(-d) + '.', 'Against the price, they behave like being short <b>' + num(-d, 0) + ' shares</b>: if the stock rises $1, you lose ~' + money(-d) + '.'));
    var up = (r.vol_scenarios || []).filter(function (s) { return s.shock_pts === 10; })[0], dn = (r.vol_scenarios || []).filter(function (s) { return s.shock_pts === -10; })[0];
    if (up && dn) out.push(L('Un susto grande en el mercado (volatilidad +10 puntos): ' + smoney(up.pnl_usd) + '. Calma total (−10 puntos): ' + smoney(dn.pnl_usd) + '.',
      'A big market scare (volatility +10 points): ' + smoney(up.pnl_usd) + '. Total calm (−10 points): ' + smoney(dn.pnl_usd) + '.'));
    return out;
  }
  // Griegas por empresa: las ACCIONES de "Mi portafolio" aportan Delta = nº de
  // acciones (Gamma, Theta y Vega 0); las opciones, lo que dice el modelo.
  function greeksByUnderlying(r) {
    var NB = window.NODE_BY_ID || {}, pos = (window.MKT && window.MKT.pos) || {}, sh = {};
    Object.keys(pos).forEach(function (id) { var n = NB[id]; if (n && n.mkt) sh[n.mkt] = (sh[n.mkt] || 0) + (+(pos[id].sh || pos[id].shares) || 0); });
    var g = {};
    r.positions.forEach(function (p) {
      var x = g[p.symbol] || (g[p.symbol] = { d: 0, gm: 0, v: 0, t: 0 });
      x.d += p.delta_shares; x.gm += p.gamma; x.v += p.vega_usd; x.t += p.theta_usd_day;
    });
    var syms = Object.keys(g); if (!syms.length) return '';
    return '<div class="sec"><h3>' + esc(L('Griegas por empresa (acciones + opciones)', 'Greeks by company (stocks + options)')) + '</h3><div class="scroll"><table><tr><th>' + esc(L('Empresa', 'Company')) +
      '</th><th>' + esc(L('Acciones', 'Shares')) + '</th><th>Delta' + chip('delta') + '</th><th>Gamma' + chip('gamma') + '</th><th>Theta' + chip('theta') + '</th><th>Vega' + chip('vega') + '</th></tr>' +
      syms.map(function (k) {
        var x = g[k], s0 = sh[k] || 0;
        return '<tr><td>' + esc(k) + '</td><td>' + num(s0, 0) + '</td><td>' + num(s0 + x.d, 0) + '</td><td>' + num(x.gm, 2) + '</td><td>' + usd(x.t) + '</td><td>' + usd(x.v) + '</td></tr>';
      }).join('') + '</table></div><div class="note">' + esc(L('Delta total = tus acciones (de "Mi portafolio") + la Delta de tus opciones. Las acciones no tienen Gamma, Theta ni Vega.',
        'Total Delta = your shares (from "My portfolio") + your options\' Delta. Shares have no Gamma, Theta or Vega.')) + '</div></div>';
  }
  function pickVSym(sym, label) {
    S.vsym = sym; S.vlabel = label || ((bySym(sym) || {}).label) || sym; S.vq = S.vlabel;
    S.chain = null; S.vexp = null; S.vk = null; loadChain(sym);
  }
  function loadChain(sym, exp) {
    S.chainErr = null; S.chainBusy = true; render();
    fetch(base() + '/api/options/chain/' + encodeURIComponent(sym) + (exp ? '?expiry=' + encodeURIComponent(exp) : ''))
      .then(function (r) { return r.json().catch(function () { return { available: false, reason: 'data_unavailable' }; }); })
      .then(function (d) {
        if (sym !== S.vsym) return;
        S.chainBusy = false;
        d = d || {};
        if (!d.available) {
          S.chain = null;
          S.chainErr = d.reason === 'no_options'
            ? L('No encontré opciones listadas para ' + sym + '. Solo algunas acciones (sobre todo de EE.UU.) tienen opciones.', 'No listed options found for ' + sym + '. Only some stocks (mostly US) have options.')
            : L('No pude obtener las opciones de ' + sym + ' ahora (el proveedor de datos no respondió). Prueba de nuevo en unos minutos.', 'I could not get ' + sym + ' options right now (the data provider did not answer). Try again in a few minutes.');
          return render();
        }
        var prevK = S.vk;
        S.chain = d;
        if (!exp && d.expirations && d.expirations.length) {
          // primer vencimiento con ≥ ~2 semanas (más útil que el de esta semana)
          var pick = d.expirations.filter(function (e) { var x = daysTo(e); return x != null && x >= 14; })[0] || d.expirations[0];
          S.vexp = pick; return loadChain(sym, pick);
        }
        var ks = nearStrikes(d);
        S.vk = prevK != null && ks.indexOf(prevK) >= 0 ? prevK : null;
        render();
      }).catch(function () { if (sym !== S.vsym) return; S.chainBusy = false; S.chainErr = L('Sin conexión con el servidor. Revisa tu internet y reintenta.', 'No connection to the server. Check your internet and retry.'); render(); });
  }
  function runVega() {
    var opts = loadOpts(); if (!opts.length || S.busy) return;
    S.busy = true; render();
    postJSON('/api/portfolio/vega_report', { options: opts })
      .then(function (d) { S.vrep = d; })
      .then(function () { S.busy = false; render(); });
  }

  /* ── autocompletar (sin re-render para no perder el foco) ────────────── */
  function wireSuggest(inputId, boxId, onPick, onType) {
    var inp = document.getElementById(inputId), box = document.getElementById(boxId);
    if (!inp || !box) return;
    var hi = 0, list = [];
    function draw() {
      list = search(inp.value);
      if (!inp.value.trim()) { box.style.display = 'none'; return; }
      box.innerHTML = list.length ? list.map(function (c, i) {
        return '<button type="button" data-i="' + i + '" class="' + (i === hi ? 'hi' : '') + '"><span>' + esc(c.label) + '</span><span class="sy">' + esc(c.sym) + '</span></button>';
      }).join('') : '<div class="note" style="padding:9px 11px">' + esc(L('No encontré esa empresa entre las que cotizan en el mapa.', 'That company is not among the listed ones on the map.')) + '</div>';
      box.style.display = 'block';
      box.querySelectorAll('button[data-i]').forEach(function (b) {
        b.onmousedown = function (e) { e.preventDefault(); onPick(list[+b.getAttribute('data-i')]); };
      });
    }
    inp.oninput = function () { hi = 0; if (onType) onType(inp.value); draw(); };
    inp.onfocus = function () { if (inp.value.trim()) draw(); };
    inp.onblur = function () { setTimeout(function () { box.style.display = 'none'; }, 150); };
    inp.onkeydown = function (e) {
      if (e.key === 'ArrowDown') { hi = Math.min(hi + 1, list.length - 1); draw(); e.preventDefault(); }
      else if (e.key === 'ArrowUp') { hi = Math.max(hi - 1, 0); draw(); e.preventDefault(); }
      else if (e.key === 'Enter') { list = search(inp.value); if (list[hi] || list[0]) { onPick(list[hi] || list[0]); } e.preventDefault(); }
      else if (e.key === 'Escape') { box.style.display = 'none'; e.stopPropagation(); }
    };
  }

  /* ── eventos ─────────────────────────────────────────────────────────── */
  function wire(box) {
    box.querySelectorAll('[data-tab]').forEach(function (b) { b.onclick = function () { S.tab = b.getAttribute('data-tab'); render(); }; });
    box.querySelectorAll('[data-src]').forEach(function (b) { b.onclick = function () { runSource(b.getAttribute('data-src')); }; });
    box.querySelectorAll('[data-ex]').forEach(function (b) { b.onclick = function () { runExample(b.getAttribute('data-ex')); }; });
    box.querySelectorAll('[data-qdel]').forEach(function (b) { b.onclick = function () { var q = loadQuick(); q.splice(+b.getAttribute('data-qdel'), 1); saveQuick(q); render(); }; });
    box.querySelectorAll('[data-del]').forEach(function (b) { b.onclick = function () { var o = loadOpts(); o.splice(+b.getAttribute('data-del'), 1); saveOpts(o); S.vrep = null; render(); }; });
    box.querySelectorAll('[data-vsym]').forEach(function (b) { b.onclick = function () { pickVSym(b.getAttribute('data-vsym')); }; });
    box.querySelectorAll('[data-vkind]').forEach(function (b) { b.onclick = function () { S.vkind = b.getAttribute('data-vkind'); render(); }; });
    box.querySelectorAll('[data-vside]').forEach(function (b) { b.onclick = function () { S.vside = b.getAttribute('data-vside'); render(); }; });
    box.querySelectorAll('[data-vexp]').forEach(function (b) { b.onclick = function () { S.vexp = b.getAttribute('data-vexp'); if (S.vsym) loadChain(S.vsym, S.vexp); }; });
    box.querySelectorAll('[data-vk]').forEach(function (b) { b.onclick = function () { S.vk = parseFloat(b.getAttribute('data-vk')); readN(); render(); }; });
    box.querySelectorAll('[data-act]').forEach(function (b) {
      b.onclick = function () {
        var a = b.getAttribute('data-act');
        if (a === 'close') close();
        else if (a === 'lang') { var lt = document.getElementById('lang-toggle'); if (lt) lt.click(); else { try { localStorage.setItem('eco_lang', en() ? 'es' : 'en'); } catch (e) {} } render(); }
        else if (a === 'print') printReport();
        else if (a === 'runquick') runQuick();
        else if (a === 'qclear') { saveQuick([]); render(); }
        else if (a === 'adv') { S.advanced = !S.advanced; render(); }
        else if (a === 'runman') { var m = document.getElementById('krr-man'); if (m) S.manual = m.value; runSource('manual'); }
        else if (a === 'back') { S.view = 'start'; S.rep = null; S.ai = null; render(); }
        else if (a === 'retry') runSpec(S.spec);
        else if (a === 'detail') { S.detail = !S.detail; render(); }
        else if (a === 'vdetail') { S.vdetail = !S.vdetail; render(); }
        else if (a === 'ai') explainAI();
        else if (a === 'vminus') { readN(); S.vn = Math.max(1, S.vn - 1); render(); }
        else if (a === 'vplus') { readN(); S.vn = Math.min(999, S.vn + 1); render(); }
        else if (a === 'addopt') {
          readN();
          if (!S.vsym || !S.vexp || S.vk == null || !(S.vn > 0)) { S.chainErr = L('Elige empresa, vencimiento, strike y contratos.', 'Pick company, expiry, strike and contracts.'); return render(); }
          var o = loadOpts(); o.push({ symbol: S.vsym, kind: S.vkind, strike: S.vk, expiry: S.vexp, contracts: S.vside === 'short' ? -S.vn : S.vn, label: S.vlabel });
          saveOpts(o.slice(-40)); S.vrep = null; render();
        } else if (a === 'runvega') runVega();
      };
    });
    var amt = document.getElementById('krr-amt'); if (amt) amt.onchange = function () { var v = parseFloat(amt.value); if (v > 0) S.amt = v; };
    wireSuggest('krr-q', 'krr-sugg', addQuick, function (v) { S.q = v; });
    wireSuggest('kv-q', 'kv-sugg', function (c) { pickVSym(c.sym, c.label); }, function (v) { S.vq = v; });
  }
  function readN() { var n = document.getElementById('kv-n'); if (n) { var v = Math.round(parseFloat(n.value)); if (v > 0) S.vn = Math.min(999, v); } }
  function printReport() {
    var box = document.getElementById('krr'); if (!box) return;
    var wasDetail = S.detail;
    if (S.tab === 'var' && S.rep && S.rep.ok && !S.detail) { S.detail = true; render(); }
    var img = '';
    try { var cv = document.getElementById('krr-hist'); if (cv) img = cv.toDataURL('image/png'); } catch (e) {}
    var html = box.innerHTML.replace(/<canvas id="krr-hist"><\/canvas>/, img ? '<img src="' + img + '" style="max-width:100%">' : '');
    if (!wasDetail && S.detail) { S.detail = false; render(); }
    var w = window.open('', '_blank'); if (!w) return;
    w.document.write('<!doctype html><meta charset="utf-8"><title>' + esc(L('Reporte de riesgo — Khipus', 'Risk report — Khipus')) + '</title>' +
      '<style>body{font-family:Inter,system-ui,sans-serif;color:#111;padding:20px}button,select,input,.ktabs,.actions{display:none!important}table{width:100%;border-collapse:collapse;font-size:12px}th,td{border-bottom:1px solid #ddd;padding:4px 6px;text-align:right}th:first-child,td:first-child{text-align:left}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.card{border:1px solid #ccc;border-radius:8px;padding:8px}.card .l{font-size:10px;color:#555;text-transform:uppercase}.card .v{font-size:17px;font-weight:700}.note{font-size:11px;color:#444}.warn{font-size:11px;color:#8a5a00;border:1px dashed #c90;padding:6px;margin:6px 0}.bar{height:6px;background:#eee;position:relative}.bar i{position:absolute;left:0;top:0;bottom:0;background:#0aa}.light{display:flex;gap:12px;align-items:center;border:1px solid #ccc;border-radius:10px;padding:10px}.light .dot{width:36px;height:36px;border-radius:50%}.light .lv{font-size:20px;font-weight:800}.say li{margin:4px 0}.ai{border:1px solid #ccc;padding:8px;white-space:pre-wrap}</style>' +
      '<body>' + html + '<p class="note">Khipus Finance AI · ' + new Date().toLocaleString() + '</p></body>');
    w.document.close(); setTimeout(function () { try { w.print(); } catch (e) {} }, 400);
  }

  // el botón de idioma de la app queda tapado por el overlay; si cambia por
  // otro camino (p. ej. Khipu), re-renderizar al volver a abrir basta.
  window.KhipuRisk = {
    open: function (o) {
      o = o || {};
      if (o.tab) S.tab = o.tab;
      if (o.source) S.source = o.source;
      shell().classList.add('show');
      S.notice = null;
      if (S.tab === 'var' && o.autorun && o.source) {
        if (S.busy) return render();
        return runSource(o.source);          // vacío → pantalla guiada con aviso (no un error)
      }
      if (S.tab === 'var' && S.view === 'result' && !S.rep) S.view = 'start';
      render();
    },
    close: close,
    isOpen: isOpen,
  };
})();
