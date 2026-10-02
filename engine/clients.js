/* engine/clients.js — 👥 CLIENTES E INVERSIÓN (corretaje multi-cliente vía Alpaca).

   window.KhipuClients.open(tab?)   tab ∈ 'clients' | 'detail' | 'approvals' | 'orders' | 'new'
   window.KhipuClients.open('detail', clientId)   ficha de un cliente
   window.KhipuClients.close()
   window.KhipuClients.pendingCount()  → Promise<number|null> (propuestas esperando aprobación;
                                          NUNCA pide el PIN: sin PIN guardado → null, apto para badges)

   Server: /api/brokerage/* (brokerage/api.py). TODAS las llamadas van por
   window._tradeFetch (header X-Trade-Pin) — nunca se reimplementa el PIN.
   Papel por defecto; el dinero real exige BROKERAGE_LIVE_ENABLED=on en el
   servidor Y "dinero real habilitado" en el cliente. Lo que proponen los
   agentes (MCP) y el comité espera en «Aprobaciones»: nada se ejecuta sin un
   humano. Bilingüe (window.LANG) y con "?" (engine/explain.js). Nada se
   inventa: patrimonio y posiciones se leen EN VIVO de Alpaca; si no hay dato
   se dice. */
(function () {
  'use strict';

  var API = '/api/brokerage';
  var LEGAL_URL = 'https://github.com/fabrizioburela23-arch/Supply-Chain-for-AI/blob/main/docs/INVERSION_TERCEROS.md';
  var S = { tab: 'clients', clients: [], status: null, sel: null, snap: null, snapErr: null, approvals: [],
    orders: [], ofilter: '', preview: null, result: null, audit: [], busy: false, msg: null, loaded: false,
    showNew: false, legalOpen: false,
    form: { sym: '', side: 'buy', type: 'market', unit: 'usd', amt: '', lp: '', why: '' } };
  var timer = null;

  function en() { return (window.LANG || localStorage.getItem('eco_lang') || '') === 'en'; }
  function L(es, e) { return en() ? e : es; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function chip(k) { return window.explainChip ? window.explainChip(k) : ''; }
  function usd(v) {
    if (v == null || v === '' || !isFinite(v)) return '—';
    v = +v; var a = Math.abs(v), s = v < 0 ? '−' : '';
    return s + 'US$' + (a >= 1e6 ? (a / 1e6).toFixed(2) + 'M' : a.toLocaleString(en() ? 'en-US' : 'es-PE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
  }
  function num(v, d) { return v == null || !isFinite(v) ? '—' : (+v).toLocaleString(en() ? 'en-US' : 'es-PE', { maximumFractionDigits: d == null ? 4 : d }); }
  function pct(v, d) { return v == null || !isFinite(v) ? '—' : (+v).toFixed(d == null ? 2 : d) + '%'; }
  function when(iso) {
    if (!iso) return '—';
    try { var d = new Date(iso); return d.toLocaleString(en() ? 'en-US' : 'es-PE', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }); } catch (e) { return iso; }
  }
  function actor() {
    var a = '';
    try { a = localStorage.getItem('khipu_actor') || ''; } catch (e) {}
    if (!a) {
      a = (window.prompt(L('¿Tu nombre? (queda en el registro de auditoría)', 'Your name? (goes into the audit log)')) || '').trim();
      if (a) { try { localStorage.setItem('khipu_actor', a); } catch (e) {} }
    }
    return a || 'ui';
  }

  /* ── red (siempre con PIN vía _tradeFetch) ───────────────────────────── */
  // interactive=false → nunca muestra el prompt del PIN (refrescos en segundo plano, badges)
  function tfetch(url, opts, interactive) {
    if (window._tradeFetch) return window._tradeFetch(url, opts || {}, interactive !== false);
    var o = Object.assign({}, opts || {});
    var pin = (window._tradePinStored && window._tradePinStored()) || '';   // PIN vigente (12 h, app.html)
    o.headers = Object.assign({}, o.headers, { 'X-Trade-Pin': pin });
    return fetch(url, o);
  }
  function call(method, path, body, interactive) {
    var opts = { method: method, headers: {} };
    if (body !== undefined && body !== null) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
    return tfetch(API + path, opts, interactive).then(function (r) {
      return r.json().catch(function () { return { error: 'HTTP ' + r.status }; }).then(function (d) {
        if (d && typeof d === 'object') d._http = r.status;
        return d;
      });
    }).catch(function (e) { return { ok: false, error: L('Sin conexión con el servidor', 'No connection to the server') + ' (' + (e && e.message || e) + ')' }; });
  }
  function isErr(d) { return !d || d.ok === false || (d._http && d._http >= 400); }
  function errText(d) { return (d && (en() && d.error_en ? d.error_en : d.error)) || L('Error desconocido', 'Unknown error'); }
  function flash(kind, text) { S.msg = { kind: kind, text: text }; render(); }

  /* ── "?" ─────────────────────────────────────────────────────────────── */
  function registerExplain() {
    if (!window.explainRegister) return;
    var R = window.explainRegister;
    R('paper_live', {
      es: { t: 'Papel 🧪 vs. dinero real 🔴', b: '<b>Papel</b> = una cuenta de práctica de Alpaca con dinero SIMULADO: las órdenes se "ejecutan" a precios reales, pero no se mueve dinero de verdad. <b>Dinero real</b> = una cuenta con fondos reales. Para operar dinero real hacen falta DOS candados: (1) en el servidor, la variable <b>BROKERAGE_LIVE_ENABLED=on</b>; (2) en el cliente, activar «dinero real habilitado». Si falta cualquiera, la orden se bloquea. Consejo: todo en papel hasta tener el visto bueno legal.' },
      en: { t: 'Paper 🧪 vs. real money 🔴', b: '<b>Paper</b> = an Alpaca practice account with SIMULATED money: orders "fill" at real prices but no real money moves. <b>Real money</b> = a funded account. Trading real money needs TWO locks: (1) on the server, <b>BROKERAGE_LIVE_ENABLED=on</b>; (2) on the client, turn on "real money enabled". If either is missing, the order is blocked. Advice: keep everything on paper until you have legal sign-off.' } });
    R('risk_limits', {
      es: { t: 'Límites de riesgo por cliente', b: 'Controles que se revisan ANTES de cada orden (y otra vez al confirmar): <b>posición máx.</b> = cuánto puede pesar una sola acción en el patrimonio después de comprar; <b>orden máx.</b> = monto máximo por compra; <b>diario máx.</b> = suma de compras enviadas en el día; <b>stop por caída</b> = si el patrimonio cae más de X % desde su máximo, se bloquean compras. <b>Vender</b> lo que el cliente tiene nunca se frena por orden máx. ni diario máx. (salir de una posición en una caída no debe esperar días). Perfiles: conservador 10 % / US$1.000 / US$2.500 / 10 %; moderado 20 % / US$5.000 / US$15.000 / 20 %; agresivo 35 % / US$25.000 / US$75.000 / 35 %. Puedes cambiar cualquier número a mano.' },
      en: { t: 'Per-client risk limits', b: 'Checks run BEFORE every order (and again on confirm): <b>max position</b> = how much one stock may weigh in equity after buying; <b>max order</b> = max amount per buy; <b>max daily</b> = total of buys sent that day; <b>drawdown stop</b> = if equity falls more than X% from its peak, buys are blocked. <b>Selling</b> what the client holds is never limited by max order or max daily (exiting a position in a crash should not take days). Profiles: conservative 10% / US$1,000 / US$2,500 / 10%; moderate 20% / US$5,000 / US$15,000 / 20%; aggressive 35% / US$25,000 / US$75,000 / 35%. You can override any number.' } });
    R('approval_queue', {
      es: { t: 'Cola de aprobación (humano en el circuito)', b: 'Cuando un <b>agente de IA</b> (vía MCP) o el <b>comité de inversión</b> propone una orden, NO se ejecuta: queda aquí esperando que una persona la apruebe o la rechace. Al aprobar, los controles de riesgo se vuelven a revisar con datos en vivo; si algo cambió, se bloquea. Cada aprobación y rechazo queda en el registro de auditoría con tu nombre.' },
      en: { t: 'Approval queue (human in the loop)', b: 'When an <b>AI agent</b> (via MCP) or the <b>investment committee</b> proposes an order, it is NOT executed: it waits here until a person approves or rejects it. On approval the risk checks run again with live data; if something changed, it is blocked. Every approval and rejection is written to the audit log with your name.' } });
    R('kill_switch', {
      es: { t: 'Interruptor general', b: 'Un botón de emergencia en el servidor: con la variable <b>BROKERAGE_TRADING_ENABLED=off</b> en Railway, ninguna orden nueva sale de <b>👥 Clientes</b>, de los <b>agentes de IA (MCP)</b> ni del <b>comité de inversión</b>. Ojo: el panel de trading clásico de la cuenta principal y su agente automático tienen sus propios controles. Las órdenes ya enviadas a Alpaca no se cancelan solas: cancélalas en «Órdenes». Para reactivar: poner <b>on</b> (o borrar la variable).' },
      en: { t: 'Master switch', b: 'An emergency button on the server: with <b>BROKERAGE_TRADING_ENABLED=off</b> in Railway, no new order goes out from <b>👥 Clients</b>, <b>AI agents (MCP)</b> or the <b>investment committee</b>. Note: the classic trading panel of the main account and its automatic agent have their own controls. Orders already at Alpaca are not canceled automatically: cancel them in "Orders". To re-enable: set <b>on</b> (or delete the variable).' } });
    R('mandate', {
      es: { t: 'Mandato del cliente', b: 'Las reglas que el cliente pidió por escrito: qué <b>tipos de activo</b> se permiten (acciones de EE.UU., cripto), qué <b>símbolos están prohibidos</b> (p. ej. no tabaco, no una empresa donde trabaja) y, si quiere, una <b>lista cerrada</b> de símbolos permitidos. Toda orden que lo contradiga se bloquea automáticamente, venga de donde venga.' },
      en: { t: "Client's mandate", b: 'The rules the client asked for in writing: which <b>asset types</b> are allowed (US stocks, crypto), which <b>symbols are forbidden</b> (e.g. no tobacco, not their employer) and, optionally, a <b>closed list</b> of allowed symbols. Any order that contradicts it is blocked automatically, wherever it comes from.' } });
    R('margin', {
      es: { t: 'Margen (dinero prestado)', b: 'Las cuentas de Alpaca suelen ser "de margen": su <b>poder de compra</b> puede ser 2 o 4 veces el patrimonio porque incluye dinero PRESTADO. Por defecto Khipus solo compra con el <b>efectivo</b> del cliente (el menor entre efectivo y poder de compra; en cripto, lo "no marginable"), así nunca se endeuda sin querer. Solo si el mandato lo permite por escrito («Permitir margen») se usa el poder de compra completo. Cripto nunca usa margen.' },
      en: { t: 'Margin (borrowed money)', b: 'Alpaca accounts are usually "margin" accounts: their <b>buying power</b> can be 2 or 4 times equity because it includes BORROWED money. By default Khipus only buys with the client\'s <b>cash</b> (the lower of cash and buying power; for crypto, the "non-marginable" amount), so it never borrows by accident. Only if the mandate allows it in writing ("Allow margin") is the full buying power used. Crypto never uses margin.' } });
    R('unknown_order', {
      es: { t: 'Orden con estado desconocido', b: 'Si la conexión con Alpaca se corta justo al enviar, no se puede saber si la orden llegó. Khipus NO la marca como fallida (si la repitieras, podrías comprar dos veces): la deja como «estado desconocido», la cuenta en tus límites y bloquea repetirla. Pulsa <b>⇅ Sincronizar</b>: Khipus pregunta a Alpaca por el identificador único de la orden y la actualiza (si nunca llegó, pasa a «falló» y ya puedes repetirla).' },
      en: { t: 'Order in unknown state', b: 'If the connection to Alpaca drops right while sending, it is impossible to know whether the order arrived. Khipus does NOT mark it failed (repeating it could buy twice): it keeps it as "unknown state", counts it in your limits and blocks repeating it. Press <b>⇅ Sync</b>: Khipus asks Alpaca for the order by its unique id and updates it (if it never arrived, it becomes "failed" and you can repeat it).' } });
    R('hwm_drawdown', {
      es: { t: 'Máximo histórico y caída', b: 'El <b>máximo</b> (high-water mark) es el patrimonio más alto que Khipus ha visto en esta cuenta. La <b>caída</b> es cuánto está por debajo de ese máximo, en %. Si cambias la cuenta conectada (otras claves, papel → dinero real) el máximo se reinicia solo. Ojo: un retiro de dinero también baja el patrimonio y cuenta como caída; en ese caso usa «Reiniciar máximo».' },
      en: { t: 'High-water mark and drawdown', b: 'The <b>high-water mark</b> is the highest equity Khipus has seen for this account. The <b>drawdown</b> is how far below that peak it is, in %. If you change the connected account (other keys, paper → real money) the peak resets automatically. Note: a withdrawal also lowers equity and counts as drawdown; in that case use "Reset peak".' } });
  }

  /* ── estilos ─────────────────────────────────────────────────────────── */
  function css() {
    if (document.getElementById('kc-css')) return;
    var st = document.createElement('style'); st.id = 'kc-css';
    st.textContent =
      '#kc-ov{position:fixed;inset:0;z-index:7700;display:none;align-items:flex-start;justify-content:center;background:rgba(3,6,12,.74);backdrop-filter:blur(4px);overflow-y:auto;overflow-x:hidden;font-family:Inter,system-ui,sans-serif}' +
      '#kc-ov.show{display:flex}' +
      '#kc{width:min(1100px,96vw);margin:3vh 0;border-radius:16px;background:radial-gradient(900px 500px at 50% -10%,#0B1222 0%,#06090F 60%);border:1px solid rgba(122,158,255,.22);box-shadow:0 24px 70px rgba(0,0,0,.6);padding:18px 20px;color:#E8EDFB;box-sizing:border-box;max-width:100vw}' +
      '#kc *{box-sizing:border-box}' +
      '#kc .hd{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px}#kc .hd h2{margin:0;font-size:19px;flex:1;min-width:180px}' +
      '#kc .x{width:32px;height:32px;border-radius:8px;border:1px solid rgba(122,158,255,.25);background:rgba(21,28,45,.7);color:#9BA6C4;cursor:pointer;flex:none}' +
      '#kc .tabs{display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap}#kc .tab{padding:7px 12px;border-radius:9px;border:1px solid rgba(122,158,255,.22);background:rgba(21,28,45,.6);color:#9BA6C4;cursor:pointer;font-size:13px;white-space:nowrap}#kc .tab.on{background:rgba(0,224,255,.12);border-color:#00E0FF;color:#00E0FF}' +
      '#kc .tab .n{display:inline-block;min-width:18px;padding:0 5px;margin-left:5px;border-radius:9px;background:#FFB300;color:#06090F;font-weight:800;font-size:11px;text-align:center}' +
      '#kc .row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:8px}' +
      '#kc select,#kc input,#kc textarea{background:#0B1222;border:1px solid rgba(122,158,255,.25);color:#E8EDFB;border-radius:8px;padding:7px 9px;font-size:13px;font-family:inherit;max-width:100%;min-width:0}' +
      '#kc input[type=checkbox]{width:17px;height:17px;padding:0;margin:2px 0 0;flex:none;accent-color:#00E0FF;cursor:pointer}' +
      '#kc label.f{display:flex;flex-direction:column;gap:4px;font-size:11px;color:#9BA6C4;flex:1 1 150px;min-width:0}' +
      '#kc label.ck{display:flex;gap:8px;align-items:flex-start;font-size:13px;color:#E8EDFB;cursor:pointer;line-height:1.45}' +
      '#kc .btn{padding:8px 14px;border-radius:9px;border:1px solid #00E0FF;background:rgba(0,224,255,.12);color:#00E0FF;cursor:pointer;font-weight:650;font-size:13px;white-space:nowrap}#kc .btn:disabled{opacity:.45;cursor:default}' +
      '#kc .btn.gh{border-color:rgba(122,158,255,.3);background:transparent;color:#9BA6C4}#kc .btn.ok{border-color:#2BE38B;color:#2BE38B;background:rgba(43,227,139,.1)}#kc .btn.bad{border-color:#FF4D6A;color:#FF4D6A;background:rgba(255,77,106,.08)}#kc .btn.sm{padding:5px 10px;font-size:12px}' +
      '#kc .note{font-size:11.5px;color:#9BA6C4;line-height:1.55}' +
      '#kc .legal{padding:8px 12px;border:1px dashed #f59e0b;border-radius:9px;background:rgba(245,158,11,.07);color:#fbbf24;font-size:12px;line-height:1.5;margin:0 0 10px}#kc .legal a{color:#fcd34d}' +
      '#kc .msg{padding:8px 12px;border-radius:9px;font-size:12.5px;margin:0 0 10px;line-height:1.5;word-break:break-word}#kc .msg.ok{border:1px solid rgba(43,227,139,.4);background:rgba(43,227,139,.08);color:#7CF0B8}#kc .msg.err{border:1px solid rgba(255,77,106,.45);background:rgba(255,77,106,.08);color:#FF9DAE}#kc .msg.info{border:1px solid rgba(122,158,255,.3);background:rgba(122,158,255,.07);color:#C9D4EC}' +
      '#kc .sbar{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 10px}#kc .pill{display:inline-flex;align-items:center;gap:4px;padding:3px 9px;border-radius:999px;font-size:11px;border:1px solid rgba(122,158,255,.25);color:#C9D4EC;background:rgba(21,28,45,.6);white-space:nowrap}' +
      '#kc .pill.g{border-color:rgba(43,227,139,.45);color:#7CF0B8}#kc .pill.r{border-color:rgba(255,77,106,.5);color:#FF9DAE}#kc .pill.y{border-color:rgba(255,179,0,.5);color:#FFD27A}' +
      '#kc .badge{display:inline-block;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:800;letter-spacing:.02em;white-space:nowrap}#kc .badge.paper{background:rgba(0,224,255,.12);color:#00E0FF;border:1px solid rgba(0,224,255,.4)}#kc .badge.live{background:rgba(255,77,106,.14);color:#FF6B84;border:1px solid rgba(255,77,106,.55)}' +
      '#kc .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px}' +
      '#kc .card{border:1px solid rgba(122,158,255,.16);border-radius:12px;background:rgba(11,18,34,.6);padding:12px;min-width:0}#kc .card.click{cursor:pointer}#kc .card.click:hover{border-color:rgba(0,224,255,.45)}' +
      '#kc .card h4{margin:0 0 6px;font-size:14.5px;display:flex;gap:6px;align-items:center;flex-wrap:wrap}' +
      '#kc .kv{display:flex;justify-content:space-between;gap:8px;font-size:12px;color:#9BA6C4;padding:2px 0}#kc .kv b{color:#E8EDFB;font-weight:650;text-align:right}' +
      '#kc .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin:8px 0}#kc .stat{border:1px solid rgba(122,158,255,.16);border-radius:11px;background:rgba(11,18,34,.6);padding:9px 11px;min-width:0}#kc .stat .l{font-size:10.5px;color:#7C87A3;text-transform:uppercase;letter-spacing:.05em}#kc .stat .v{font-size:18px;font-weight:750;margin-top:3px;word-break:break-word}' +
      '#kc .sec{margin-top:14px;padding-top:12px;border-top:1px solid rgba(122,158,255,.1)}#kc .sec h3{font-size:12.5px;margin:0 0 8px;color:#C9D4EC;text-transform:uppercase;letter-spacing:.05em;display:flex;align-items:center;gap:4px;flex-wrap:wrap}' +
      '#kc .scroll{overflow-x:auto;max-width:100%}#kc table{width:100%;border-collapse:collapse;font-size:12.5px;min-width:520px}#kc th,#kc td{padding:6px 8px;border-bottom:1px solid rgba(122,158,255,.1);text-align:right;white-space:nowrap}#kc th:first-child,#kc td:first-child{text-align:left}#kc th{color:#7C87A3;font-weight:600;font-size:11px}' +
      '#kc .chk{display:flex;gap:7px;font-size:12px;line-height:1.45;padding:3px 0;color:#C9D4EC}#kc .chk i{font-style:normal;flex:none;width:16px;text-align:center}' +
      '#kc .ord{border:1px solid rgba(122,158,255,.14);border-radius:10px;padding:9px 11px;margin-bottom:7px;background:rgba(11,18,34,.5)}#kc .ord .t{display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:13px}#kc .ord .s{font-size:11.5px;color:#9BA6C4;margin-top:3px;word-break:break-word}' +
      '#kc .st{padding:1px 7px;border-radius:6px;font-size:11px;font-weight:700;border:1px solid rgba(122,158,255,.3);color:#C9D4EC}#kc .st.filled,#kc .st.submitted{border-color:rgba(43,227,139,.5);color:#7CF0B8}#kc .st.rejected,#kc .st.failed{border-color:rgba(255,77,106,.5);color:#FF9DAE}#kc .st.pending_approval{border-color:rgba(255,179,0,.55);color:#FFD27A}' +
      '#kc .sum{font-size:13.5px;line-height:1.55;padding:10px 12px;border-radius:10px;background:rgba(0,224,255,.05);border:1px solid rgba(0,224,255,.2);margin:8px 0;word-break:break-word}' +
      '#kc .empty{padding:18px;text-align:center;color:#7C87A3;font-size:13px;border:1px dashed rgba(122,158,255,.2);border-radius:12px}' +
      '@media(max-width:600px){#kc{width:100vw;margin:0;border-radius:0;padding:14px 12px;min-height:100vh}#kc .stat .v{font-size:15px}#kc .hd h2{font-size:17px}#kc .grid{grid-template-columns:1fr}}';
    document.head.appendChild(st);
  }

  function shell() {
    css();
    var ov = document.getElementById('kc-ov');
    if (!ov) {
      ov = document.createElement('div'); ov.id = 'kc-ov';
      ov.innerHTML = '<div id="kc"></div>';
      ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
      ov.addEventListener('click', onClick);
      ov.addEventListener('change', onChange);
      document.body.appendChild(ov);
    }
    return ov;
  }

  /* ── utilidades de presentación ──────────────────────────────────────── */
  function modeBadge(mode) {
    return mode === 'live' ? '<span class="badge live">🔴 ' + esc(L('DINERO REAL', 'REAL MONEY')) + '</span>'
      : '<span class="badge paper">🧪 ' + esc(L('PAPEL', 'PAPER')) + '</span>';
  }
  var ST = { previewed: ['previsualizada', 'previewed'], pending_approval: ['esperando aprobación', 'awaiting approval'],
    approved: ['aprobada', 'approved'], submitted: ['enviada', 'submitted'], filled: ['ejecutada', 'filled'],
    partially_filled: ['ejecución parcial', 'partially filled'], canceled: ['cancelada', 'canceled'],
    rejected: ['rechazada / bloqueada', 'rejected / blocked'], expired: ['caducada', 'expired'], failed: ['falló', 'failed'] };
  function stLabel(s) { var x = ST[s] || [s, s]; return '<span class="st ' + esc(s) + '">' + esc(L(x[0], x[1])) + '</span>'; }
  function orderStLabel(o) {
    if (o.unknown) return '<span class="st pending_approval">' + esc(L('estado desconocido', 'unknown state')) + '</span>' + chip('unknown_order');
    return stLabel(o.expired ? 'expired' : o.status);
  }
  function oErr(o) { return en() ? (o.error_en || o.error) : o.error; }
  var SRC = { ui: ['👤 app', '👤 app'], mcp: ['🤖 agente (MCP)', '🤖 agent (MCP)'], committee: ['🏛 comité', '🏛 committee'] };
  function srcLabel(s) { var x = SRC[s] || [s, s]; return esc(L(x[0], x[1])); }
  var CHK = { kill_switch: ['Interruptor general', 'Master switch', 'kill_switch'], mode: ['Modo', 'Mode', 'paper_live'],
    client_status: ['Estado del cliente', 'Client status'], account: ['Cuenta', 'Account'], symbol: ['Símbolo', 'Symbol', 'mandate'],
    restricted: ['Mandato', 'Mandate', 'mandate'], order_size: ['Tamaño de orden', 'Order size', 'risk_limits'],
    daily_limit: ['Límite diario', 'Daily limit', 'risk_limits'], buying_power: ['Dinero disponible', 'Available funds', 'margin'],
    limit_price: ['Precio límite', 'Limit price'], unresolved: ['Orden sin confirmar', 'Unconfirmed order', 'unknown_order'],
    position_limit: ['Tamaño de posición', 'Position size', 'risk_limits'], drawdown_stop: ['Stop por caída', 'Drawdown stop', 'hwm_drawdown'],
    holdings: ['Tenencia (sin cortos)', 'Holdings (no shorts)'], duplicate: ['Duplicado', 'Duplicate'], market_hours: ['Horario', 'Market hours'] };
  function checksHtml(checks) {
    if (!checks || !checks.length) return '';
    return checks.map(function (c) {
      var x = CHK[c.name] || [c.name, c.name];
      var icon = !c.ok ? '<i style="color:#FF4D6A">✗</i>' : (c.warn ? '<i style="color:#FFB300">⚠</i>' : '<i style="color:#2BE38B">✓</i>');
      return '<div class="chk">' + icon + '<span><b>' + esc(L(x[0], x[1])) + '</b>' + (x[2] ? chip(x[2]) : '') + ' — ' +
        esc(en() ? (c.detail_en || c.detail) : c.detail) + '</span></div>';
    }).join('');
  }
  function amount(o) {
    if (o.notional != null) return usd(o.notional);
    return num(o.qty) + ' ' + (String(o.symbol || '').indexOf('/') >= 0 ? L('unid.', 'units') : L('acc.', 'sh.')) +
      (o.est_usd ? ' (≈ ' + usd(o.est_usd) + ')' : '');
  }
  function clientById(id) { for (var i = 0; i < S.clients.length; i++) if (S.clients[i].id === id) return S.clients[i]; return null; }
  function clientOptions(sel, withAll) {
    var h = withAll ? '<option value="">' + esc(L('Todos los clientes', 'All clients')) + '</option>' : '';
    S.clients.forEach(function (c) {
      h += '<option value="' + esc(c.id) + '"' + (c.id === sel ? ' selected' : '') + '>' + esc(c.name) + ' · ' +
        (c.mode === 'live' ? '🔴' : '🧪') + (c.status === 'paused' ? ' ⏸' : '') + '</option>';
    });
    return h;
  }

  /* ── cabecera, aviso legal y barra de estado ─────────────────────────── */
  function header() {
    var n = S.approvals.length;
    var tabs = [['clients', '👥 ' + L('Clientes', 'Clients'), ''], ['detail', '📋 ' + L('Detalle', 'Detail'), ''],
      ['approvals', '✅ ' + L('Aprobaciones', 'Approvals'), n ? '<span class="n">' + n + '</span>' : ''],
      ['orders', '🧾 ' + L('Órdenes', 'Orders'), ''], ['new', '➕ ' + L('Nueva orden', 'New order'), '']];
    return '<div class="hd"><h2>👥 ' + esc(L('Clientes e inversión', 'Clients & investing')) + '</h2>' +
      '<button class="btn gh sm" data-act="reload">↻ ' + esc(L('Actualizar', 'Refresh')) + '</button>' +
      '<button class="x" data-act="close" aria-label="close">✕</button></div>' +
      legal() + statusBar() +
      '<div class="tabs">' + tabs.map(function (t) {
        return '<button class="tab' + (S.tab === t[0] ? ' on' : '') + '" data-tab="' + t[0] + '">' + esc(t[1]) + t[2] + '</button>';
      }).join('') + '</div>' +
      (S.msg ? '<div class="msg ' + esc(S.msg.kind) + '">' + esc(S.msg.text) + '</div>' : '');
  }
  function legal() {
    var more = S.legalOpen ? '<ul style="margin:6px 0 0 16px;padding:0">' +
      '<li>' + esc(L('Recibir dinero de terceros e invertirlo de forma habitual puede ser "captación" no autorizada (SBS) y administrar carteras ajenas es actividad regulada (SMV) en Perú.', 'Habitually receiving and investing third-party money can be unauthorized "deposit-taking" (SBS), and managing other people\'s portfolios is a regulated activity (SMV) in Peru.')) + '</li>' +
      '<li>' + esc(L('Cada persona debe tener SU PROPIA cuenta a su nombre; nunca mezcles dinero en tu cuenta.', 'Each person must have THEIR OWN account in their name; never pool money in your account.')) + '</li>' +
      '<li>' + esc(L('Para operar dinero real de otros vía OAuth, Alpaca debe aprobar tu app.', 'To trade other people\'s real money via OAuth, Alpaca must approve your app.')) + '</li>' +
      '<li>' + esc(L('Sin cobrar comisiones hasta que un abogado lo apruebe por escrito.', 'Charge no fees until a lawyer approves it in writing.')) + '</li></ul>' : '';
    return '<div class="legal">⚖ <b>' + esc(L('Aviso legal:', 'Legal notice:')) + '</b> ' +
      esc(L('operar el dinero de otras personas requiere autorización o registro (no es asesoría legal). Usa cuentas de PAPEL hasta tener el visto bueno de un abogado.',
        'operating other people\'s money requires authorization or registration (this is not legal advice). Use PAPER accounts until a lawyer signs off.')) +
      ' <a href="' + LEGAL_URL + '" target="_blank" rel="noopener">docs/INVERSION_TERCEROS.md</a> · ' +
      '<a href="#" data-act="legal">' + esc(S.legalOpen ? L('ocultar', 'hide') : L('ver resumen', 'see summary')) + '</a>' + more + '</div>';
  }
  function statusBar() {
    var st = S.status;
    if (!st) return '';
    var p = [];
    p.push('<span class="pill ' + (st.trading_enabled ? 'g' : 'r') + '">' + (st.trading_enabled ? '● ' : '⛔ ') +
      esc(st.trading_enabled ? L('Interruptor: encendido', 'Switch: on') : L('Interruptor: APAGADO', 'Switch: OFF')) + chip('kill_switch') + '</span>');
    p.push('<span class="pill ' + (st.live_enabled_env ? 'r' : '') + '">' + esc(st.live_enabled_env ? L('🔴 Dinero real permitido en el servidor', '🔴 Real money allowed on server') : L('🧪 Servidor solo papel', '🧪 Server paper-only')) + chip('paper_live') + '</span>');
    p.push('<span class="pill ' + (st.oauth_configured ? 'g' : '') + '">OAuth Alpaca: ' + esc(st.oauth_configured ? L('listo', 'ready') : L('no configurado', 'not set')) + '</span>');
    if (st.auto_approve_paper) p.push('<span class="pill y">' + esc(L('Auto-aprobación en papel ACTIVA', 'Paper auto-approval ON')) + '</span>');
    var ks = st.encryption && st.encryption.key_source;
    if (ks && ks !== 'env') p.push('<span class="pill ' + (ks === 'default' ? 'r' : 'y') + '">🔐 ' + esc(ks === 'default'
      ? L('Sin BROKERAGE_ENC_KEY: no se pueden conectar cuentas hasta configurarla', 'No BROKERAGE_ENC_KEY: accounts cannot be connected until it is set')
      : L('Cifrado derivado de SECRET_KEY (mejor: BROKERAGE_ENC_KEY)', 'Encryption derived from SECRET_KEY (better: BROKERAGE_ENC_KEY)')) + '</span>');
    return '<div class="sbar">' + p.join('') + '</div>';
  }

  /* ── pestaña: Clientes ───────────────────────────────────────────────── */
  function viewClients() {
    var h = '<div class="row"><button class="btn" data-act="toggle-new">' + esc(S.showNew ? L('Cancelar', 'Cancel') : '+ ' + L('Nuevo cliente', 'New client')) + '</button>' +
      '<span class="note">' + esc(L('Cada cliente = una cuenta de Alpaca a SU nombre. Toca una tarjeta para ver el detalle.', 'Each client = an Alpaca account in THEIR name. Tap a card for details.')) + '</span></div>';
    if (S.showNew) {
      h += '<div class="card" style="margin-bottom:10px"><div class="row">' +
        '<label class="f">' + esc(L('Nombre', 'Name')) + '<input id="kc-n-name" maxlength="200"></label>' +
        '<label class="f">Email<input id="kc-n-email" type="email" maxlength="200"></label>' +
        '<label class="f">' + esc(L('Perfil de riesgo', 'Risk profile')) + chip('risk_limits') + '<select id="kc-n-prof">' + profOptions('moderado') + '</select></label>' +
        '<label class="f">' + esc(L('Modo', 'Mode')) + chip('paper_live') + '<select id="kc-n-mode"><option value="paper">🧪 ' + esc(L('Papel (simulado)', 'Paper (simulated)')) + '</option><option value="live">🔴 ' + esc(L('Dinero real', 'Real money')) + '</option></select></label></div>' +
        '<label class="f" style="margin-bottom:8px">' + esc(L('Notas (acuerdo, objetivo…)', 'Notes (agreement, goal…)')) + '<textarea id="kc-n-notes" rows="2" maxlength="2000"></textarea></label>' +
        '<button class="btn ok" data-act="create"' + (S.busy ? ' disabled' : '') + '>' + esc(L('Crear cliente', 'Create client')) + '</button></div>';
    }
    if (!S.loaded) return h + '<div class="empty">' + esc(L('Cargando…', 'Loading…')) + '</div>';
    if (!S.clients.length) return h + '<div class="empty">' + esc(L('Aún no hay clientes. Crea el primero (en papel).', 'No clients yet. Create the first one (on paper).')) + '</div>';
    h += '<div class="grid">' + S.clients.map(function (c) {
      return '<div class="card click" data-act="open-client" data-id="' + esc(c.id) + '"><h4>' + esc(c.name) + ' ' + modeBadge(c.mode) +
        (c.status === 'paused' ? '<span class="pill y">⏸ ' + esc(L('pausado', 'paused')) + '</span>' : '') + '</h4>' +
        kv(L('Conexión', 'Connection'), c.connected ? '✓ ' + esc(authLabel(c)) : '<span style="color:#FF9DAE">✗ ' + esc(L('sin conectar', 'not connected')) + '</span>') +
        kv(L('Patrimonio (último dato)', 'Equity (last reading)'), c.last_equity != null ? usd(c.last_equity) + ' <span class="note">' + esc(when(c.last_snapshot_at)) + '</span>' : '<span class="note">' + esc(L('sin leer aún', 'not read yet')) + '</span>') +
        kv(L('Perfil', 'Profile'), esc(profName(c.risk_profile))) +
        (c.mode === 'live' ? kv(L('Dinero real habilitado', 'Real money enabled'), c.live_enabled ? '🔴 ' + esc(L('sí', 'yes')) : esc(L('no', 'no'))) : '') +
        '</div>';
    }).join('') + '</div>';
    return h;
  }
  function kv(k, v) { return '<div class="kv"><span>' + esc(k) + '</span><b>' + v + '</b></div>'; }
  function authLabel(c) {
    if (c.auth_type === 'env') return L('claves del servidor', 'server keys') + ' ' + (c.credentials_hint || '');
    if (c.auth_type === 'oauth') return 'OAuth';
    return L('claves API', 'API keys') + ' ' + (c.credentials_hint || '');
  }
  var PROF = { conservador: ['Conservador', 'Conservative'], moderado: ['Moderado', 'Moderate'], agresivo: ['Agresivo', 'Aggressive'] };
  function profName(p) { var x = PROF[p] || [p, p]; return L(x[0], x[1]); }
  function profOptions(sel) {
    return Object.keys(PROF).map(function (k) { return '<option value="' + k + '"' + (k === sel ? ' selected' : '') + '>' + esc(profName(k)) + '</option>'; }).join('');
  }

  /* ── pestaña: Detalle ────────────────────────────────────────────────── */
  function viewDetail() {
    if (!S.clients.length) return '<div class="empty">' + esc(L('Crea un cliente primero.', 'Create a client first.')) + '</div>';
    var c = clientById(S.sel) || S.clients[0];
    S.sel = c.id;
    var h = '<div class="row"><select id="kc-sel" style="flex:1;min-width:0">' + clientOptions(c.id) + '</select>' +
      '<button class="btn" data-act="snap"' + (S.busy ? ' disabled' : '') + '>↻ ' + esc(L('Leer cuenta en vivo', 'Read live account')) + '</button></div>';
    h += '<div class="card"><h4>' + esc(c.name) + ' ' + modeBadge(c.mode) + chip('paper_live') +
      (c.status === 'paused' ? '<span class="pill y">⏸ ' + esc(L('pausado', 'paused')) + '</span>' : '<span class="pill g">● ' + esc(L('activo', 'active')) + '</span>') + '</h4>' +
      (c.email ? kv('Email', esc(c.email)) : '') +
      kv(L('Conexión', 'Connection'), c.connected ? '✓ ' + esc(authLabel(c)) : '<span style="color:#FF9DAE">✗ ' + esc(L('sin conectar', 'not connected')) + '</span>') +
      kv(L('Perfil de riesgo', 'Risk profile'), esc(profName(c.risk_profile))) +
      (c.notes ? '<div class="note" style="margin-top:6px;white-space:pre-wrap">' + esc(c.notes) + '</div>' : '') +
      '<div class="row" style="margin-top:8px">' +
      '<button class="btn sm ' + (c.status === 'paused' ? 'ok' : 'gh') + '" data-act="pause">' + esc(c.status === 'paused' ? L('▶ Reactivar', '▶ Resume') : L('⏸ Pausar', '⏸ Pause')) + '</button>' +
      '<button class="btn sm gh" data-act="goto-new">➕ ' + esc(L('Nueva orden', 'New order')) + '</button>' +
      '<button class="btn sm gh" data-act="goto-orders">🧾 ' + esc(L('Sus órdenes', 'Their orders')) + '</button></div></div>';
    h += snapView(c) + connectView(c) + limitsView(c) + liveView(c) + auditView();
    return h;
  }
  function snapView(c) {
    var h = '<div class="sec"><h3>💼 ' + esc(L('Cuenta en vivo (Alpaca)', 'Live account (Alpaca)')) + '</h3>';
    if (S.snapErr) return h + '<div class="msg err">' + esc(S.snapErr) + '</div></div>';
    var sn = S.snap && S.snap.client && S.snap.client.id === c.id ? S.snap : null;
    if (!sn) return h + '<div class="note">' + esc(c.connected ? L('Pulsa «Leer cuenta en vivo» para ver patrimonio y posiciones.', 'Press "Read live account" to see equity and positions.') : L('Conecta la cuenta de Alpaca más abajo.', 'Connect the Alpaca account below.')) + '</div></div>';
    var a = sn.account || {}, cl = sn.client || c;
    h += '<div class="note">' + esc(L('Fuente: Alpaca (en vivo)', 'Source: Alpaca (live)')) + ' · ' + esc(when(sn.as_of)) + '</div>' +
      '<div class="cards">' + stat(L('Patrimonio', 'Equity'), usd(a.equity)) + stat(L('Efectivo', 'Cash'), usd(a.cash)) +
      stat(L('Poder de compra', 'Buying power'), usd(a.buying_power)) +
      stat(L('Máximo / caída', 'Peak / drawdown') + chip('hwm_drawdown'), usd(cl.hwm_equity) + '<div class="note">' + (cl.drawdown_pct != null ? (cl.drawdown_pct > 0.05 ? '−' : '') + pct(cl.drawdown_pct, 1) : '—') + '</div>') + '</div>';
    var ps = sn.positions || [];
    if (!ps.length) return h + '<div class="note">' + esc(L('Sin posiciones abiertas.', 'No open positions.')) + '</div></div>';
    h += '<div class="scroll"><table><thead><tr><th>' + esc(L('Símbolo', 'Symbol')) + '</th><th>' + esc(L('Cantidad', 'Qty')) + '</th><th>' + esc(L('Precio medio', 'Avg price')) + '</th><th>' + esc(L('Precio', 'Price')) + '</th><th>' + esc(L('Valor', 'Value')) + '</th><th>P/L</th><th>P/L %</th></tr></thead><tbody>' +
      ps.map(function (p) {
        var col = (p.unrealized_pl || 0) >= 0 ? '#2BE38B' : '#FF4D6A';
        return '<tr><td>' + esc(p.symbol) + '</td><td>' + num(p.qty) + '</td><td>' + usd(p.avg_entry_price) + '</td><td>' + usd(p.current_price) + '</td><td>' + usd(p.market_value) +
          '</td><td style="color:' + col + '">' + usd(p.unrealized_pl) + '</td><td style="color:' + col + '">' + (p.unrealized_plpc != null ? pct(p.unrealized_plpc * 100) : '—') + '</td></tr>';
      }).join('') + '</tbody></table></div></div>';
    return h;
  }
  function stat(l, v) { return '<div class="stat"><div class="l">' + l + '</div><div class="v">' + v + '</div></div>'; }
  function connectView(c) {
    var h = '<div class="sec"><h3>🔗 ' + esc(L('Conectar Alpaca', 'Connect Alpaca')) + chip('paper_live') + '</h3>';
    if (c.auth_type === 'env') return h + '<div class="note">' + esc(L('Esta es la cuenta principal: usa ALPACA_KEY / ALPACA_SECRET / ALPACA_BASE configuradas en Railway. Su modo lo decide ALPACA_BASE.', 'This is the main account: it uses ALPACA_KEY / ALPACA_SECRET / ALPACA_BASE set in Railway. Its mode is set by ALPACA_BASE.')) + '</div></div>';
    var oauth = S.status && S.status.oauth_configured;
    h += '<div class="note" style="margin-bottom:8px">' + esc(L('Recomendado: que la persona autorice desde SU cuenta de Alpaca (OAuth). Khipus nunca ve su contraseña; puede revocar el acceso cuando quiera.', 'Recommended: the person authorizes from THEIR Alpaca account (OAuth). Khipus never sees their password; they can revoke access anytime.')) + '</div>';
    h += '<div class="row"><select id="kc-c-env"><option value="paper">🧪 ' + esc(L('Papel', 'Paper')) + '</option><option value="live">🔴 ' + esc(L('Dinero real', 'Real money')) + '</option></select>' +
      (oauth ? '<button class="btn" data-act="oauth">🔐 ' + esc(L('Conectar con Alpaca (OAuth)', 'Connect with Alpaca (OAuth)')) + '</button>'
        : '<span class="note">' + esc(L('OAuth no configurado (faltan ALPACA_OAUTH_* en Railway) — usa claves API:', 'OAuth not configured (ALPACA_OAUTH_* missing in Railway) — use API keys:')) + '</span>') + '</div>';
    h += '<div class="row"><label class="f">API Key ID<input id="kc-c-key" autocomplete="off" spellcheck="false"></label>' +
      '<label class="f">Secret Key<input id="kc-c-sec" type="password" autocomplete="new-password" spellcheck="false"></label></div>' +
      '<div class="row"><button class="btn gh" data-act="creds"' + (S.busy ? ' disabled' : '') + '>🔑 ' + esc(L('Guardar claves (cifradas)', 'Save keys (encrypted)')) + '</button>' +
      '<span class="note">' + esc(L('Se verifican con Alpaca, se guardan CIFRADAS y nunca se vuelven a mostrar (solo ****1234). Las claves de papel solo sirven en papel.', 'They are verified with Alpaca, stored ENCRYPTED and never shown again (only ****1234). Paper keys only work on paper.')) + '</span></div></div>';
    return h;
  }
  function limitsView(c) {
    var lim = c.limits || {}, ov = c.limit_overrides || {}, m = c.mandate || {};
    var cls = m.allowed_asset_classes || [];
    function inp(k, label, unit) {
      return '<label class="f">' + esc(label) + ' (' + unit + ')<input id="kc-l-' + k + '" type="number" min="0" step="any" value="' + esc(ov[k] != null ? ov[k] : '') + '" placeholder="' + esc(L('perfil: ', 'profile: ') + lim[k]) + '"></label>';
    }
    return '<div class="sec"><h3>🛡 ' + esc(L('Límites y mandato', 'Limits & mandate')) + chip('risk_limits') + chip('mandate') + '</h3>' +
      '<div class="row"><label class="f">' + esc(L('Perfil de riesgo', 'Risk profile')) + '<select id="kc-l-prof">' + profOptions(c.risk_profile) + '</select></label>' +
      inp('max_position_pct', L('Posición máx.', 'Max position'), '%') + inp('max_order_usd', L('Orden máx.', 'Max order'), 'US$') + '</div>' +
      '<div class="row">' + inp('max_daily_usd', L('Diario máx.', 'Max daily'), 'US$') + inp('max_drawdown_stop_pct', L('Stop por caída', 'Drawdown stop'), '%') + '</div>' +
      '<div class="note" style="margin:-2px 0 8px">' + esc(L('Vacío = usa el valor del perfil. Vigentes: ', 'Empty = profile value. In force: ')) +
      esc(L('posición ', 'position ') + lim.max_position_pct + '% · ' + L('orden ', 'order ') + usd(lim.max_order_usd) + ' · ' + L('diario ', 'daily ') + usd(lim.max_daily_usd) + ' · ' + L('stop ', 'stop ') + lim.max_drawdown_stop_pct + '%') + '</div>' +
      '<div class="row"><label class="ck"><input type="checkbox" id="kc-m-eq"' + (cls.indexOf('us_equity') >= 0 ? ' checked' : '') + '> ' + esc(L('Acciones de EE.UU.', 'US stocks')) + '</label>' +
      '<label class="ck"><input type="checkbox" id="kc-m-cr"' + (cls.indexOf('crypto') >= 0 ? ' checked' : '') + '> ' + esc(L('Cripto', 'Crypto')) + '</label>' +
      '<label class="ck"><input type="checkbox" id="kc-m-mg"' + (m.allow_margin ? ' checked' : '') + '> ' + esc(L('Permitir margen (préstamo) — no recomendado', 'Allow margin (borrowing) — not recommended')) + '</label>' + chip('margin') + '</div>' +
      '<div class="row"><label class="f">' + esc(L('Símbolos prohibidos (coma)', 'Forbidden symbols (comma)')) + '<input id="kc-m-rs" value="' + esc((m.restricted_symbols || []).join(', ')) + '" placeholder="TSLA, GME"></label>' +
      '<label class="f">' + esc(L('Solo estos símbolos (vacío = todos)', 'Only these symbols (empty = all)')) + '<input id="kc-m-as" value="' + esc((m.allowed_symbols || []).join(', ')) + '"></label></div>' +
      '<div class="row"><button class="btn" data-act="save-limits"' + (S.busy ? ' disabled' : '') + '>💾 ' + esc(L('Guardar límites y mandato', 'Save limits & mandate')) + '</button>' +
      '<button class="btn gh sm" data-act="reset-hwm">' + esc(L('Reiniciar máximo', 'Reset peak')) + '</button>' + chip('hwm_drawdown') + '</div></div>';
  }
  function liveView(c) {
    if (c.mode !== 'live') return '';
    var envOn = S.status && S.status.live_enabled_env;
    return '<div class="sec"><h3>🔴 ' + esc(L('Dinero real', 'Real money')) + chip('paper_live') + '</h3>' +
      '<div class="note">' + esc(L('Servidor (BROKERAGE_LIVE_ENABLED): ', 'Server (BROKERAGE_LIVE_ENABLED): ')) + '<b>' + esc(envOn ? L('permitido', 'allowed') : L('bloqueado', 'blocked')) + '</b> · ' +
      esc(L('Este cliente: ', 'This client: ')) + '<b>' + esc(c.live_enabled ? L('habilitado', 'enabled') : L('no habilitado', 'not enabled')) + '</b></div>' +
      '<div class="row" style="margin-top:8px">' + (c.live_enabled
        ? '<button class="btn gh" data-act="live-off">' + esc(L('Deshabilitar dinero real', 'Disable real money')) + '</button>'
        : '<label class="ck"><input type="checkbox" id="kc-live-ck"> ' + esc(L('Entiendo que se operará dinero REAL de esta persona, que tengo su autorización escrita y el visto bueno legal.', 'I understand REAL money of this person will be traded, and I have their written authorization and legal sign-off.')) + '</label>' +
          '<button class="btn bad" data-act="live-on">' + esc(L('Habilitar dinero real', 'Enable real money')) + '</button>') + '</div></div>';
  }
  var ACT = { client_created: ['cliente creado', 'client created'], client_updated: ['cliente modificado', 'client updated'],
    credentials_set: ['claves conectadas', 'keys connected'], credentials_rejected: ['claves rechazadas por Alpaca', 'keys rejected by Alpaca'],
    oauth_started: ['OAuth iniciado', 'OAuth started'], oauth_connected: ['conectado por OAuth', 'connected via OAuth'],
    oauth_failed: ['OAuth falló', 'OAuth failed'], oauth_denied: ['OAuth denegado', 'OAuth denied'],
    order_previewed: ['orden previsualizada', 'order previewed'], order_approved: ['orden aprobada', 'order approved'],
    order_rejected: ['orden rechazada', 'order rejected'], order_blocked: ['orden bloqueada al confirmar', 'order blocked on confirm'],
    order_submitted: ['orden enviada a Alpaca', 'order sent to Alpaca'], order_failed: ['envío fallido', 'send failed'],
    order_canceled: ['orden cancelada', 'order canceled'], cancel_failed: ['cancelación fallida', 'cancel failed'],
    order_synced: ['estado sincronizado', 'status synced'], confirm_denied: ['confirmación denegada (requiere humano)', 'confirmation denied (needs a human)'],
    preview_expired: ['previsualización caducada', 'preview expired'], approval_expired: ['propuesta caducada', 'proposal expired'],
    live_enabled_on: ['🔴 dinero real HABILITADO', '🔴 real money ENABLED'], live_enabled_off: ['dinero real deshabilitado', 'real money disabled'],
    account_changed: ['cuenta cambiada (máximo reiniciado, propuestas caducadas)', 'account changed (peak reset, proposals expired)'],
    order_unknown: ['⚠ envío con estado desconocido', '⚠ send in unknown state'], order_reconciled: ['orden reconciliada con Alpaca', 'order reconciled with Alpaca'],
    approval_required: ['pasó a aprobación humana', 'moved to human approval'], pin_lockout: ['⛔ PIN bloqueado por intentos fallidos', '⛔ PIN locked after failed attempts'] };
  function actLabel(a) { var x = ACT[a]; return x ? L(x[0], x[1]) : a; }
  function auditView() {
    var items = S.audit || [];
    var h = '<div class="sec"><h3>📜 ' + esc(L('Registro de auditoría', 'Audit log')) + '</h3>';
    if (!items.length) return h + '<div class="note">' + esc(L('Sin registros aún.', 'No entries yet.')) + '</div></div>';
    return h + items.slice(0, 30).map(function (a) {
      var d = a.detail || {}, extra = [];
      ['symbol', 'side', 'status', 'mode', 'env', 'source', 'reason', 'error'].forEach(function (k) { if (d[k] != null && d[k] !== '') extra.push(k + ': ' + d[k]); });
      if (d.failed_checks && d.failed_checks.length) extra.push('✗ ' + d.failed_checks.join(', '));
      return '<div class="ord"><div class="t"><b>' + esc(actLabel(a.action)) + '</b><span class="note">' + esc(when(a.ts)) + ' · ' + esc(a.actor) + '</span></div>' +
        (extra.length ? '<div class="s">' + esc(extra.join(' · ')) + '</div>' : '') + '</div>';
    }).join('') + '</div>';
  }

  /* ── pestaña: Aprobaciones ───────────────────────────────────────────── */
  function viewApprovals() {
    var h = '<div class="note" style="margin-bottom:8px">' + esc(L('Lo que proponen los agentes de IA (MCP) y el comité espera aquí. NADA se ejecuta sin tu clic. Al aprobar se revisan otra vez los controles con datos en vivo.', 'Proposals from AI agents (MCP) and the committee wait here. NOTHING runs without your click. On approval the checks run again with live data.')) + chip('approval_queue') + '</div>';
    if (!S.approvals.length) return h + '<div class="empty">✅ ' + esc(L('No hay propuestas pendientes.', 'No pending proposals.')) + '</div>';
    return h + S.approvals.map(function (a) {
      return '<div class="card" style="margin-bottom:10px"><h4>' + modeBadge(a.mode) + ' ' + esc(a.client_name || a.client_id) + ' · ' + srcLabel(a.source) + '</h4>' +
        '<div class="sum">' + esc(en() ? (a.summary_en || a.summary_es) : a.summary_es) + '</div>' +
        (a.rationale ? '<div class="note" style="white-space:pre-wrap;margin-bottom:6px"><b>' + esc(L('Motivo del proponente:', "Proposer's rationale:")) + '</b> ' + esc(a.rationale) + '</div>' : '') +
        '<div class="note">' + esc(L('Pedido por ', 'Requested by ')) + esc(a.requested_by || '—') + ' · ' + esc(when(a.created_at)) + ' · ' + esc(L('caduca ', 'expires ')) + esc(when(a.expires_at)) + '</div>' +
        '<details style="margin:6px 0"><summary class="note" style="cursor:pointer">' + esc(L('Controles al proponer', 'Checks at proposal time')) + '</summary>' + checksHtml(a.checks) + '</details>' +
        '<div class="row"><button class="btn ok" data-act="approve" data-id="' + esc(a.preview_id) + '"' + (S.busy ? ' disabled' : '') + '>✓ ' + esc(L('Aprobar y enviar', 'Approve & send')) + '</button>' +
        '<button class="btn bad" data-act="reject" data-id="' + esc(a.preview_id) + '"' + (S.busy ? ' disabled' : '') + '>✗ ' + esc(L('Rechazar', 'Reject')) + '</button></div></div>';
    }).join('');
  }

  /* ── pestaña: Órdenes ────────────────────────────────────────────────── */
  function viewOrders() {
    var h = '<div class="row"><select id="kc-o-cli" style="flex:1;min-width:0">' + clientOptions(S.ofilter, true) + '</select>' +
      '<button class="btn gh" data-act="sync"' + (S.busy ? ' disabled' : '') + '>⇅ ' + esc(L('Sincronizar con Alpaca', 'Sync with Alpaca')) + '</button></div>';
    if (!S.orders.length) return h + '<div class="empty">' + esc(L('Sin órdenes todavía.', 'No orders yet.')) + '</div>';
    return h + S.orders.map(function (o) {
      var open = !o.expired && (o.status === 'submitted' || o.status === 'partially_filled' || o.status === 'previewed' || o.status === 'pending_approval');
      var side = o.side === 'buy' ? '<b style="color:#2BE38B">' + esc(L('COMPRA', 'BUY')) + '</b>' : '<b style="color:#FF4D6A">' + esc(L('VENTA', 'SELL')) + '</b>';
      return '<div class="ord"><div class="t">' + modeBadge(o.mode) + side + '<b>' + esc(o.symbol) + '</b><span>' + amount(o) + '</span>' + orderStLabel(o) +
        (open ? '<button class="btn sm bad" style="margin-left:auto" data-act="cancel" data-id="' + esc(o.id) + '">' + esc(L('Cancelar', 'Cancel')) + '</button>' : '') + '</div>' +
        '<div class="s">' + esc(o.client_name || o.client_id) + ' · ' + srcLabel(o.source) + ' · ' + esc(when(o.created_at)) +
        (o.filled_qty ? ' · ' + esc(L('ejecutado ', 'filled ')) + num(o.filled_qty) + ' @ ' + usd(o.filled_avg_price) : '') +
        (o.approved_by ? ' · ' + esc(L('aprobó ', 'approved by ')) + esc(o.approved_by) : '') +
        (o.alpaca_status ? ' · Alpaca: ' + esc(o.alpaca_status) : '') + '</div>' +
        (o.error ? '<div class="s" style="color:#FF9DAE">' + esc(oErr(o)) + '</div>' : '') + '</div>';
    }).join('');
  }

  /* ── pestaña: Nueva orden ────────────────────────────────────────────── */
  function viewNew() {
    if (!S.clients.length) return '<div class="empty">' + esc(L('Crea un cliente primero.', 'Create a client first.')) + '</div>';
    var c = clientById(S.sel) || S.clients[0], F = S.form;
    S.sel = c.id;
    var h = '<div class="note" style="margin-bottom:8px">' + esc(L('Paso 1: previsualiza (se revisan los límites del cliente con su cuenta EN VIVO). Paso 2: marca «confirmo» y envía. La previsualización caduca en 5 minutos.', 'Step 1: preview (the client limits are checked against their LIVE account). Step 2: tick "I confirm" and send. The preview expires in 5 minutes.')) + '</div>' +
      '<div class="row"><label class="f">' + esc(L('Cliente', 'Client')) + '<select id="kc-sel">' + clientOptions(c.id) + '</select></label>' +
      '<label class="f">' + esc(L('Símbolo', 'Symbol')) + '<input id="kc-o-sym" maxlength="20" placeholder="NVDA · BTC/USD" autocapitalize="characters" spellcheck="false" value="' + esc(F.sym) + '"></label></div>' +
      '<div class="row"><label class="f">' + esc(L('Operación', 'Side')) + '<select id="kc-o-side">' + opt('buy', L('Comprar', 'Buy'), F.side) + opt('sell', L('Vender', 'Sell'), F.side) + '</select></label>' +
      '<label class="f">' + esc(L('Tipo', 'Type')) + '<select id="kc-o-type">' + opt('market', L('A mercado', 'Market'), F.type) + opt('limit', L('Límite (por cantidad)', 'Limit (by quantity)'), F.type) + '</select></label>' +
      '<label class="f">' + esc(L('Expresar en', 'Amount in')) + '<select id="kc-o-unit">' + opt('usd', 'US$', F.unit) + opt('qty', L('Cantidad', 'Quantity'), F.unit) + '</select></label>' +
      '<label class="f">' + esc(L('Monto / cantidad', 'Amount / quantity')) + '<input id="kc-o-amt" type="number" min="0" step="any" value="' + esc(F.amt) + '"></label>' +
      '<label class="f">' + esc(L('Precio límite', 'Limit price')) + '<input id="kc-o-lp" type="number" min="0" step="any" value="' + esc(F.lp) + '" placeholder="' + esc(L('solo órdenes límite', 'limit orders only')) + '"></label></div>' +
      '<label class="f" style="margin-bottom:8px">' + esc(L('Motivo (queda en la auditoría)', 'Rationale (kept in the audit log)')) + '<input id="kc-o-why" maxlength="500" value="' + esc(F.why) + '"></label>' +
      '<button class="btn" data-act="preview"' + (S.busy ? ' disabled' : '') + '>🔎 ' + esc(L('Previsualizar', 'Preview')) + '</button>';
    var p = S.preview;
    if (p) {
      h += '<div class="sec"><h3>' + esc(L('Previsualización', 'Preview')) + '</h3><div class="sum">' + esc(en() ? (p.summary_en || p.summary_es) : p.summary_es) + '</div>' + checksHtml(p.checks);
      if (p.blocked) {
        h += '<div class="msg err" style="margin-top:8px">' + esc(L('Bloqueada por los controles de riesgo: no se puede enviar. Ajusta la orden o los límites.', 'Blocked by the risk checks: it cannot be sent. Adjust the order or the limits.')) + '</div>';
      } else if (p.status === 'previewed') {
        h += '<div class="note" style="margin:8px 0">' + esc(L('Caduca en ', 'Expires in ')) + '<b id="kc-exp">' + remaining(p.expires_at) + '</b></div>' +
          '<label class="ck" style="margin-bottom:8px"><input type="checkbox" id="kc-confirm-ck"> ' + esc(p.mode === 'live'
            ? L('Confirmo que quiero enviar esta orden con DINERO REAL de este cliente.', 'I confirm I want to send this order with this client\'s REAL MONEY.')
            : L('Confirmo que quiero enviar esta orden (papel, dinero simulado).', 'I confirm I want to send this order (paper, simulated money).')) + '</label>' +
          '<button class="btn ' + (p.mode === 'live' ? 'bad' : 'ok') + '" data-act="confirm"' + (S.busy ? ' disabled' : '') + '>🚀 ' + esc(L('Enviar orden', 'Send order')) + '</button>';
      }
      h += '</div>';
    }
    var r = S.result;
    if (r) h += '<div class="msg ' + (r.ok ? 'ok' : 'err') + '" style="margin-top:10px">' + esc(r.ok
      ? L('Orden enviada a Alpaca · estado: ', 'Order sent to Alpaca · status: ') + ((r.order && r.order.status) || '') + ' · id ' + ((r.order && r.order.alpaca_order_id) || '—')
      : errText(r)) + (r.code === 'unknown_state' ? chip('unknown_order') + ' <button class="btn sm gh" data-act="goto-orders">🧾 ' + esc(L('Ir a Órdenes', 'Go to Orders')) + '</button>' : '') + '</div>';
    return h;
  }
  function opt(v, label, sel) { return '<option value="' + esc(v) + '"' + (v === sel ? ' selected' : '') + '>' + esc(label) + '</option>'; }
  function saveForm() {
    if (!document.getElementById('kc-o-sym')) return;
    S.form = { sym: val('kc-o-sym').toUpperCase(), side: val('kc-o-side') || 'buy', type: val('kc-o-type') || 'market',
      unit: val('kc-o-unit') || 'usd', amt: val('kc-o-amt'), lp: val('kc-o-lp'), why: val('kc-o-why') };
  }
  function remaining(iso) {
    if (!iso) return '—';
    var s = Math.max(0, Math.round((new Date(iso).getTime() - Date.now()) / 1000));
    return s <= 0 ? L('caducada', 'expired') : Math.floor(s / 60) + ':' + ('0' + (s % 60)).slice(-2);
  }

  /* ── render ──────────────────────────────────────────────────────────── */
  function render() {
    var box = document.getElementById('kc'); if (!box) return;
    var body = S.tab === 'detail' ? viewDetail() : S.tab === 'approvals' ? viewApprovals() : S.tab === 'orders' ? viewOrders() : S.tab === 'new' ? viewNew() : viewClients();
    box.innerHTML = header() + body;
  }

  /* ── carga de datos ──────────────────────────────────────────────────── */
  function loadStatus() {
    // /status es público (solo disponible + interruptor); el resto (cifrado,
    // dinero real, OAuth, auto-aprobación) va con PIN en /status/detail
    return fetch(API + '/status').then(function (r) { return r.json(); }).then(function (d) {
      S.status = d;
      return call('GET', '/status/detail').then(function (x) { if (!isErr(x)) S.status = Object.assign({}, d, x); });
    }).catch(function () { S.status = null; });
  }
  function loadClients() {
    return call('GET', '/clients').then(function (d) {
      S.loaded = true;
      if (isErr(d)) { S.msg = { kind: 'err', text: errText(d) }; S.clients = []; return; }
      S.clients = d.clients || [];
      if (!S.sel && S.clients.length) S.sel = S.clients[0].id;
    });
  }
  function loadApprovals() {
    return call('GET', '/approvals').then(function (d) { S.approvals = isErr(d) ? [] : (d.approvals || []); });
  }
  function loadOrders() {
    return call('GET', '/orders?limit=100' + (S.ofilter ? '&client_id=' + encodeURIComponent(S.ofilter) : '')).then(function (d) {
      S.orders = isErr(d) ? [] : (d.orders || []);
    });
  }
  function loadAudit() {
    if (!S.sel) return Promise.resolve();
    return call('GET', '/clients/' + encodeURIComponent(S.sel) + '/audit?limit=30').then(function (d) { S.audit = isErr(d) ? [] : (d.items || []); });
  }
  function loadSnap() {
    if (!S.sel) return Promise.resolve();
    S.busy = true; S.snapErr = null; render();
    return call('GET', '/clients/' + encodeURIComponent(S.sel) + '/account').then(function (d) {
      S.busy = false;
      if (isErr(d)) { S.snap = null; S.snapErr = errText(d); }
      else {
        S.snap = d;
        for (var i = 0; i < S.clients.length; i++) if (S.clients[i].id === S.sel && d.client) S.clients[i] = d.client;
      }
      render();
    });
  }
  function reloadAll() {
    S.msg = null;
    return loadStatus().then(function () { return loadClients(); }).then(function () {
      if (S.status && S.status.available === false) S.msg = { kind: 'err', text: L('Corretaje no disponible: falta la base de datos (DATABASE_URL).', 'Brokerage unavailable: the database (DATABASE_URL) is missing.') };
      return Promise.all([loadApprovals(), S.tab === 'orders' ? loadOrders() : null, S.tab === 'detail' ? loadAudit() : null]);
    }).then(render);
  }

  /* ── acciones ────────────────────────────────────────────────────────── */
  function val(id) { var el = document.getElementById(id); return el ? String(el.value || '').trim() : ''; }
  function checked(id) { var el = document.getElementById(id); return !!(el && el.checked); }
  function after(d, okText, then) {
    S.busy = false;
    if (isErr(d)) { flash('err', errText(d)); return false; }
    S.msg = okText ? { kind: 'ok', text: okText } : null;
    if (then) then(d);
    render();
    return true;
  }
  function patchClient(patch, okText) {
    patch.actor = actor();
    S.busy = true; render();
    return call('PATCH', '/clients/' + encodeURIComponent(S.sel), patch).then(function (d) {
      after(d, okText, function (x) {
        for (var i = 0; i < S.clients.length; i++) if (S.clients[i].id === x.client.id) S.clients[i] = x.client;
      });
      return loadAudit().then(render);
    });
  }

  /* ── avisos pop-up (engine/toast.js): confirmar, enviada, rechazada, ejecutada ──
     Solo informan y piden la confirmación explícita: el envío sigue siendo
     preview → confirm / approve del server (regla de oro del dinero). */
  function KT() { return window.KhipuToast || null; }
  function ordInfo(x) {
    x = x || {};
    return { side: x.side, symbol: x.symbol, label: x.symbol, qty: x.qty, notional: x.notional,
      orderType: x.order_type, limitPrice: x.limit_price, tif: x.time_in_force, price: x.est_price, estUsd: x.est_usd,
      mode: x.mode === 'live' ? 'live' : 'paper', client: x.client_name || x.client_id };
  }
  // pop-up con el resumen de la orden; sin engine/toast.js → window.confirm de siempre
  function askOrder(x, opts, fallbackText) {
    var k = KT();
    if (k && k.confirmOrder) return k.confirmOrder(ordInfo(x), opts);
    if (!window.confirm(fallbackText)) return Promise.resolve(false);
    if (x && x.mode === 'live' && !window.confirm(L('🔴 Es DINERO REAL. ¿Seguro?', '🔴 This is REAL MONEY. Sure?'))) return Promise.resolve(false);
    return Promise.resolve(true);
  }
  function what(x) {
    var amt = x.notional != null ? usd(x.notional) + ' ' + L('de', 'of') : (x.qty != null ? num(x.qty) + ' ×' : '');
    return (amt ? amt + ' ' : '') + (x.symbol || '') + (x.client_name ? ' · ' + x.client_name : '');
  }
  function sendingToast(x) {
    var k = KT(); if (!k) return null;
    return k.show({ kind: x.side === 'sell' ? 'sell' : 'buy', busy: true, mode: x.mode === 'live' ? 'live' : 'paper',
      title: x.side === 'sell' ? L('Enviando orden de venta…', 'Sending sell order…') : L('Enviando orden de compra…', 'Sending buy order…'),
      body: what(x) });
  }
  // resultado de confirm/approve: {ok, order} o error (texto del server tal cual)
  function resultToast(x, d, tid) {
    var k = KT(); if (!k) return;
    var o = (d && d.order) || x || {};
    var mode = (o.mode || x.mode) === 'live' ? 'live' : 'paper';
    var put = function (opts) { opts.busy = false; opts.mode = mode; return tid ? k.update(tid, opts) : k.show(opts); };
    if (isErr(d)) {
      var unknown = d && d.code === 'unknown_state';
      put({ kind: unknown ? 'warn' : 'error', title: unknown ? L('No se pudo confirmar la orden', 'The order could not be confirmed')
        : (x.side === 'sell' ? L('La venta no se envió', 'The sell order was not sent') : L('La compra no se envió', 'The buy order was not sent')),
        body: errText(d) });
      return;
    }
    if (o.status === 'filled') return filledToast(o, tid, mode);
    put({ kind: x.side === 'sell' ? 'sell' : 'buy', timeout: 0,
      title: x.side === 'sell' ? L('Orden de venta enviada', 'Sell order sent') : L('Orden de compra enviada', 'Buy order sent'),
      body: what(Object.assign({}, x, o)) + ' · ' + L('estado: ', 'status: ') + (o.status || '—') + '. ' + L('Te aviso cuando se ejecute.', "I'll let you know when it fills.") });
    watchClientOrder(o, tid, mode);
  }
  function filledToast(o, tid, mode) {
    var k = KT(); if (!k) return;
    k.order.filled({ side: o.side, symbol: o.symbol, mode: mode },
      { symbol: o.symbol, filled_qty: o.filled_qty, filled_avg_price: o.filled_avg_price }, tid, mode);
    if (S.tab === 'orders') loadOrders().then(render);
  }
  // Sondeo LIGERO (≤ 60 s): ⇅ Sincronizar de ese cliente (el mismo endpoint del
  // botón; audita solo si el estado cambia) + leer la orden. Sin pedir PIN.
  var WATCH_AT = [5000, 12000, 25000, 40000, 60000];
  var FINAL_BAD = { canceled: 1, cancelled: 1, rejected: 1, expired: 1, failed: 1, done_for_day: 1 };
  function watchClientOrder(o, tid, mode) {
    var k = KT(); if (!k || !o || !o.id || !o.client_id) return;
    var t0 = Date.now(), i = 0;
    function tick() {
      if (i >= WATCH_AT.length) {
        if (tid) k.update(tid, { kind: 'info', timeout: 12000, title: L('La orden sigue pendiente', 'The order is still pending'),
          body: what(o) + ' — ' + L('aún no se ejecuta (¿mercado cerrado?). Revisa la pestaña Órdenes.', 'it has not filled yet (market closed?). Check the Orders tab.') });
        return;
      }
      setTimeout(function () {
        call('POST', '/clients/' + encodeURIComponent(o.client_id) + '/sync', { actor: actor() }, false)
          .then(function () { return call('GET', '/orders?limit=40&client_id=' + encodeURIComponent(o.client_id), null, false); })
          .then(function (d) {
            var hit = null;
            ((d && d.orders) || []).forEach(function (x) { if (x.id === o.id) hit = x; });
            if (!hit) return tick();
            if (hit.status === 'filled') return filledToast(hit, tid, mode);
            if (FINAL_BAD[hit.status]) {
              var opt = { busy: false, mode: mode, kind: hit.status === 'rejected' || hit.status === 'failed' ? 'error' : 'warn', timeout: 12000,
                title: L('La orden no se ejecutó', 'The order did not fill'),
                body: what(hit) + ' · ' + L('estado final: ', 'final status: ') + hit.status + (hit.error ? ' — ' + errText(hit) : '') };
              if (tid) k.update(tid, opt); else k.show(opt);
              return;
            }
            tick();
          });
      }, Math.max(0, WATCH_AT[i++] - (Date.now() - t0)));
    }
    tick();
  }

  function onChange(e) {
    var t = e.target;
    saveForm();
    if (t.id === 'kc-sel') { S.sel = t.value; S.snap = null; S.snapErr = null; S.preview = null; S.result = null; S.audit = []; render(); if (S.tab === 'detail') loadAudit().then(render); }
    if (t.id === 'kc-o-cli') { S.ofilter = t.value; loadOrders().then(render); }
  }

  function onClick(e) {
    var el = e.target.closest ? e.target.closest('[data-act],[data-tab]') : null;
    if (!el || !document.getElementById('kc').contains(el)) return;
    saveForm();
    if (el.getAttribute('data-tab')) { e.preventDefault(); setTab(el.getAttribute('data-tab')); return; }
    var act = el.getAttribute('data-act'), id = el.getAttribute('data-id');
    if (act === 'close') return close();
    if (act === 'legal') { e.preventDefault(); S.legalOpen = !S.legalOpen; render(); return; }
    if (act === 'reload') { reloadAll(); return; }
    if (act === 'toggle-new') { S.showNew = !S.showNew; render(); return; }
    if (act === 'open-client') { S.sel = id; S.snap = null; S.snapErr = null; setTab('detail'); if (clientById(id) && clientById(id).connected) loadSnap(); return; }
    if (act === 'goto-new') { S.preview = null; S.result = null; setTab('new'); return; }
    if (act === 'goto-orders') { S.ofilter = S.sel; setTab('orders'); return; }
    if (act === 'snap') { loadSnap(); return; }
    if (act === 'create') {
      var name = val('kc-n-name');
      if (!name) { flash('err', L('Escribe el nombre del cliente.', 'Enter the client name.')); return; }
      S.busy = true; render();
      call('POST', '/clients', { name: name, email: val('kc-n-email'), notes: val('kc-n-notes'), risk_profile: val('kc-n-prof'), mode: val('kc-n-mode'), actor: actor() })
        .then(function (d) { if (after(d, L('Cliente creado. Ahora conecta su cuenta de Alpaca.', 'Client created. Now connect their Alpaca account.'))) { S.showNew = false; S.sel = d.client.id; reloadAll().then(function () { setTab('detail'); }); } });
      return;
    }
    if (act === 'pause') { var c = clientById(S.sel); patchClient({ status: c && c.status === 'paused' ? 'active' : 'paused' }, L('Estado actualizado.', 'Status updated.')); return; }
    if (act === 'reset-hwm') { if (window.confirm(L('¿Reiniciar el máximo histórico? (úsalo tras un retiro de dinero)', 'Reset the peak? (use it after a withdrawal)'))) patchClient({ reset_hwm: true }, L('Máximo reiniciado.', 'Peak reset.')); return; }
    if (act === 'save-limits') {
      var limits = {};
      ['max_position_pct', 'max_order_usd', 'max_daily_usd', 'max_drawdown_stop_pct'].forEach(function (k) { var v = val('kc-l-' + k); if (v !== '') limits[k] = +v; });
      var classes = []; if (checked('kc-m-eq')) classes.push('us_equity'); if (checked('kc-m-cr')) classes.push('crypto');
      if (!classes.length) { flash('err', L('Permite al menos un tipo de activo.', 'Allow at least one asset type.')); return; }
      var cur = clientById(S.sel) || {};
      var margin = checked('kc-m-mg');
      if (margin && !(cur.mandate && cur.mandate.allow_margin) && !window.confirm(L('¿Permitir que este cliente compre con dinero PRESTADO (margen)? Puede perder más de lo que tiene.', 'Allow this client to buy with BORROWED money (margin)? They can lose more than they have.'))) return;
      patchClient({ risk_profile: val('kc-l-prof'), limits: limits, mandate: { allowed_asset_classes: classes, restricted_symbols: val('kc-m-rs'), allowed_symbols: val('kc-m-as'), allow_margin: margin, notes: (cur.mandate && cur.mandate.notes) || '' } }, L('Límites y mandato guardados.', 'Limits and mandate saved.'));
      return;
    }
    if (act === 'live-on') {
      if (!checked('kc-live-ck')) { flash('err', L('Marca la casilla de confirmación primero.', 'Tick the confirmation box first.')); return; }
      if (!window.confirm(L('⚠ DINERO REAL: ¿habilitar operaciones con dinero real para este cliente?', '⚠ REAL MONEY: enable real-money trading for this client?'))) return;
      patchClient({ live_enabled: true, confirm_live: true }, L('Dinero real habilitado para este cliente (el servidor también debe permitirlo).', 'Real money enabled for this client (the server must allow it too).'));
      return;
    }
    if (act === 'live-off') { patchClient({ live_enabled: false }, L('Dinero real deshabilitado.', 'Real money disabled.')); return; }
    if (act === 'creds') {
      var key = val('kc-c-key'), sec = val('kc-c-sec'), envv = val('kc-c-env') || 'paper';
      if (!key || !sec) { flash('err', L('Pega la API Key ID y la Secret Key.', 'Paste the API Key ID and Secret Key.')); return; }
      if (envv === 'live' && !window.confirm(L('Son claves de DINERO REAL. ¿Continuar?', 'These are REAL MONEY keys. Continue?'))) return;
      S.busy = true; render();
      call('POST', '/clients/' + encodeURIComponent(S.sel) + '/credentials', { api_key: key, api_secret: sec, env: envv, actor: actor() }).then(function (d) {
        var k = document.getElementById('kc-c-sec'); if (k) k.value = '';
        if (after(d, d.verified === false ? L('Claves guardadas, pero no se pudieron verificar ahora: ', 'Keys saved but could not be verified now: ') + (d.detail || '') : L('Cuenta conectada y verificada ✓', 'Account connected and verified ✓'),
          function (x) { for (var i = 0; i < S.clients.length; i++) if (S.clients[i].id === x.client.id) S.clients[i] = x.client; })) loadSnap();
      });
      return;
    }
    if (act === 'oauth') {
      var env2 = val('kc-c-env') || 'paper';
      var w = window.open('about:blank', '_blank');
      call('POST', '/clients/' + encodeURIComponent(S.sel) + '/oauth/start', { env: env2, actor: actor() }).then(function (d) {
        if (isErr(d) || !d.url) { if (w) w.close(); flash('err', errText(d)); return; }
        if (w) w.location.href = d.url; else window.location.href = d.url;
        flash('info', L('Se abrió Alpaca en otra pestaña. Cuando la persona autorice, vuelve aquí y pulsa ↻ Actualizar.', 'Alpaca opened in another tab. Once the person authorizes, come back and press ↻ Refresh.'));
      });
      return;
    }
    if (act === 'preview') {
      var sym = val('kc-o-sym').toUpperCase(), amt = val('kc-o-amt'), unit = val('kc-o-unit'), otype = val('kc-o-type');
      if (!sym || !(+amt > 0)) { flash('err', L('Escribe el símbolo y un monto mayor que 0.', 'Enter the symbol and an amount above 0.')); return; }
      var body = { client_id: S.sel, symbol: sym, side: val('kc-o-side'), order_type: otype, rationale: val('kc-o-why'), actor: actor() };
      if (otype === 'limit') { body.qty = +amt; body.limit_price = +val('kc-o-lp'); if (unit === 'usd') { flash('err', L('Las órdenes límite se expresan en cantidad.', 'Limit orders are expressed as quantity.')); return; } }
      else if (unit === 'usd') body.notional = +amt; else body.qty = +amt;
      S.busy = true; S.preview = null; S.result = null; render();
      call('POST', '/orders/preview', body).then(function (d) { S.busy = false; if (isErr(d)) { flash('err', errText(d)); return; } S.preview = d; S.msg = null; render(); });
      return;
    }
    if (act === 'confirm') {
      var p = S.preview;
      if (!p) return;
      if (!checked('kc-confirm-ck')) { flash('err', L('Marca «confirmo» para enviar.', 'Tick "I confirm" to send.')); return; }
      // DINERO REAL: además del «confirmo», el pop-up con el resumen y su casilla
      (p.mode === 'live'
        ? askOrder(p, { title: L('🔴 DINERO REAL — ¿enviar la orden ahora?', '🔴 REAL MONEY — send the order now?'),
            subtitle: en() ? (p.summary_en || p.summary_es) : p.summary_es, confirmLabel: L('Enviar orden', 'Send order') },
            L('🔴 DINERO REAL — ¿enviar la orden ahora?', '🔴 REAL MONEY — send the order now?'))
        : Promise.resolve(true)
      ).then(function (go) {
        if (!go || S.preview !== p) return;
        S.busy = true; render();
        var tid = sendingToast(p);
        call('POST', '/orders/' + encodeURIComponent(p.preview_id) + '/confirm', { confirm: true, actor: actor() }).then(function (d) {
          S.busy = false; S.result = d; S.preview = null; S.msg = null; render();
          resultToast(p, d, tid);
          loadApprovals().then(render);
        });
      });
      return;
    }
    if (act === 'approve') {
      var a = null; S.approvals.forEach(function (x) { if (x.preview_id === id) a = x; });
      var txt = a ? (en() ? (a.summary_en || a.summary_es) : a.summary_es) : '';
      // pop-up: resumen + cuenta 🧪/🔴 (con DINERO REAL exige marcar la casilla)
      (a ? askOrder(a, { title: L('¿Aprobar y ENVIAR esta orden?', 'Approve and SEND this order?'), subtitle: txt,
          confirmLabel: L('Aprobar y enviar', 'Approve & send') },
        L('¿Aprobar y ENVIAR esta orden?\n\n', 'Approve and SEND this order?\n\n') + txt)
        : Promise.resolve(window.confirm(L('¿Aprobar y ENVIAR esta orden?', 'Approve and SEND this order?')))
      ).then(function (go) {
        if (!go) return;
        S.busy = true; render();
        var tid = a ? sendingToast(a) : null;
        call('POST', '/approvals/' + encodeURIComponent(id) + '/approve', { actor: actor() }).then(function (d) {
          after(d, L('Aprobada y enviada a Alpaca ✓ (estado: ', 'Approved and sent to Alpaca ✓ (status: ') + ((d.order && d.order.status) || '') + ')');
          if (a) resultToast(a, d, tid);
          loadApprovals().then(render);
        });
      });
      return;
    }
    if (act === 'reject') {
      var reason = window.prompt(L('Motivo del rechazo (opcional):', 'Reason for rejection (optional):'), '');
      if (reason === null) return;
      S.busy = true; render();
      call('POST', '/approvals/' + encodeURIComponent(id) + '/reject', { actor: actor(), reason: reason }).then(function (d) {
        after(d, L('Propuesta rechazada.', 'Proposal rejected.'));
        if (KT() && !isErr(d)) KT().show({ kind: 'info', title: L('Propuesta rechazada', 'Proposal rejected'),
          body: L('No se envió ninguna orden.', 'No order was sent.') });
        loadApprovals().then(render);
      });
      return;
    }
    if (act === 'cancel') {
      var co = null; S.orders.forEach(function (x) { if (x.id === id) co = x; });
      (KT() ? KT().confirm({ title: L('¿Cancelar esta orden?', 'Cancel this order?'), subtitle: co ? what(co) : '',
          mode: co ? (co.mode === 'live' ? 'live' : 'paper') : undefined, confirmLabel: L('Sí, cancelarla', 'Yes, cancel it'), cancelLabel: L('No', 'No') })
        : Promise.resolve(window.confirm(L('¿Cancelar esta orden?', 'Cancel this order?')))
      ).then(function (go) {
        if (!go) return;
        S.busy = true; render();
        call('POST', '/orders/' + encodeURIComponent(id) + '/cancel', { actor: actor() }).then(function (d) {
          after(d, L('Orden cancelada (estado: ', 'Order canceled (status: ') + (d.status || '') + ')');
          if (KT()) KT().show(isErr(d)
            ? { kind: 'error', title: L('No se pudo cancelar', 'Could not cancel'), body: errText(d) }
            : { kind: 'info', title: L('Orden cancelada', 'Order canceled'), body: (co ? what(co) + ' · ' : '') + L('estado: ', 'status: ') + (d.status || '—') });
          Promise.all([loadOrders(), loadApprovals()]).then(render);
        });
      });
      return;
    }
    if (act === 'sync') {
      var ids = S.ofilter ? [S.ofilter] : S.clients.filter(function (c) { return c.connected; }).map(function (c) { return c.id; });
      S.busy = true; render();
      var up = 0, errs = [];
      ids.reduce(function (pr, cid) {
        return pr.then(function () {
          return call('POST', '/clients/' + encodeURIComponent(cid) + '/sync', { actor: actor() }).then(function (d) {
            up += d.updated || 0;
            if (isErr(d) || (d.errors && d.errors.length)) errs.push(errText(d.errors && d.errors[0] ? d.errors[0] : d));
          });
        });
      }, Promise.resolve()).then(function () {
        S.busy = false;
        S.msg = errs.length ? { kind: 'err', text: L('Sincronizado con errores: ', 'Synced with errors: ') + errs.join(' · ') } : { kind: 'ok', text: L('Sincronizado · órdenes actualizadas: ', 'Synced · orders updated: ') + up };
        loadOrders().then(render);
      });
      return;
    }
  }

  function setTab(t) {
    S.tab = t; S.msg = null; render();
    if (t === 'approvals') loadApprovals().then(render);
    if (t === 'orders') loadOrders().then(render);
    if (t === 'detail') loadAudit().then(render);
  }

  /* ── API pública ─────────────────────────────────────────────────────── */
  function open(tab, clientId) {
    registerExplain();
    var ov = shell();
    ov.classList.add('show');
    if (tab) S.tab = tab;
    if (clientId) S.sel = clientId;
    S.msg = null; S.preview = null; S.result = null;
    render();
    reloadAll().then(function () {
      if (S.tab === 'detail' && S.sel && clientById(S.sel) && clientById(S.sel).connected && !S.snap) loadSnap();
    });
    if (!timer) timer = setInterval(function () {
      var el = document.getElementById('kc-exp');
      if (el && S.preview) el.textContent = remaining(S.preview.expires_at);
    }, 1000);
  }
  function close() {
    var ov = document.getElementById('kc-ov'); if (ov) ov.classList.remove('show');
    if (timer) { clearInterval(timer); timer = null; }
  }
  function pendingCount() {
    // para badges/sondeos: SIN prompt de PIN; sin PIN guardado o PIN malo → null, en silencio
    var pin = (window._tradePinStored && window._tradePinStored()) || '';   // PIN vigente (12 h, app.html)
    if (!pin) return Promise.resolve(null);
    return call('GET', '/approvals', null, false).then(function (d) {
      if (!d || d._http === 401 || d._http === 403 || d._http === 429) return null;
      return isErr(d) ? null : (d.approvals || []).length;
    });
  }
  document.addEventListener('keydown', function (e) {
    var ov = document.getElementById('kc-ov');
    if (e.key === 'Escape' && ov && ov.classList.contains('show')) close();
  });

  registerExplain();
  window.KhipuClients = { open: open, close: close, pendingCount: pendingCount };
})();
