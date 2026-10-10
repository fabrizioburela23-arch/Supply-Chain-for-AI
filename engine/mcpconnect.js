/* engine/mcpconnect.js — 🤖 CONECTAR IAs (MCP): que Claude, ChatGPT, Cursor o
   un agente propio usen Khipus desde SU propia interfaz.

   window.KhipuMCP.open(tab?)   tab ∈ 'connect' | 'tokens' | 'audit' | 'tools'
   window.KhipuMCP.close()
   Entrada en la app: 🩺 Sistema → fila «🤖 Conectar IAs (MCP)» (la instala
   este archivo bajo las pestañas del panel; no añade botones a la barra).

   Server: mcp_server/ (POST /mcp = protocolo MCP; /api/mcp/* = administración;
   /oauth/* = OAuth para conectores remotos). TODA llamada con PIN va por
   window._tradeFetch (header X-Trade-Pin) — nunca se reimplementa el PIN.
   El token se muestra UNA sola vez (el servidor solo guarda su huella sha256).
   Órdenes propuestas por una IA: SIEMPRE esperan aprobación humana en
   👥 Clientes → Aprobaciones. Bilingüe (window.LANG) y con "?" (explain.js). */
(function () {
  'use strict';

  var S = { tab: 'connect', status: null, tokens: [], audit: [], tools: [], clients: null, clientsErr: null,
    created: null, busy: false, msg: null, cfg: 'claude_code',
    form: { name: '', read: true, research: false, trade: false, client: '' } };

  function en() { return (window.LANG || (function () { try { return localStorage.getItem('eco_lang'); } catch (e) { return ''; } })() || '') === 'en'; }
  function L(es, e) { return en() ? e : es; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function chip(k) { return window.explainChip ? window.explainChip(k) : ''; }
  function when(iso) {
    if (!iso) return '—';
    try { return new Date(iso).toLocaleString(en() ? 'en-US' : 'es-PE', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }); } catch (e) { return iso; }
  }
  function actor() {
    var a = '';
    try { a = localStorage.getItem('khipu_actor') || ''; } catch (e) {}
    return a || 'ui (PIN)';
  }

  /* ── explicaciones "?" ─────────────────────────────────────────────── */
  function registerExplain() {
    if (!window.explainRegister) return;
    window.explainRegister('mcp', {
      es: { t: '¿Qué es MCP (conectar IAs)?', b: '<b>MCP</b> (Model Context Protocol) es un «enchufe» estándar para que una IA —Claude, ChatGPT, Cursor o un agente propio— use herramientas externas.<br><br>Al conectar Khipus, tu IA puede <b>consultar</b> el grafo de la cadena de suministro, la ficha en vivo de cada empresa, la investigación de los agentes, el riesgo de una cartera y los eventos mundiales, y —si le das permiso— <b>proponer</b> órdenes para un cliente.<br><br>Todo lo que devuelve Khipus trae su <b>fuente</b> y <b>fecha</b>: la IA no necesita inventar cifras.' },
      en: { t: 'What is MCP (connect AIs)?', b: '<b>MCP</b> (Model Context Protocol) is a standard “plug” that lets an AI —Claude, ChatGPT, Cursor or your own agent— use external tools.<br><br>Once connected to Khipus, your AI can <b>query</b> the supply-chain graph, each company’s live profile, the agents’ research, portfolio risk and world events, and —if you allow it— <b>propose</b> orders for a client.<br><br>Everything Khipus returns carries its <b>source</b> and <b>date</b>: the AI does not need to make up numbers.' }
    });
    window.explainRegister('mcp_scopes', {
      es: { t: 'Permisos de una conexión (alcances)', b: '<b>read</b> (siempre incluido): solo consultar — grafo, empresas, ontología, investigación, riesgo, opciones, eventos mundiales, comité.<br><b>research</b>: además puede <b>lanzar</b> investigaciones y el comité de inversión (gasta el presupuesto diario de IA).<br><b>trade</b>: puede ver la cuenta y <b>proponer</b> órdenes de <b>UN solo cliente</b> (el que elijas). Nunca puede aprobarlas: cada orden espera tu aprobación.<br><br>Da a cada IA el mínimo que necesite. Puedes revocar una conexión en cualquier momento.' },
      en: { t: 'Connection permissions (scopes)', b: '<b>read</b> (always included): query only — graph, companies, ontology, research, risk, options, world events, committee.<br><b>research</b>: can also <b>start</b> research runs and the investment committee (uses the daily AI budget).<br><b>trade</b>: can see the account and <b>propose</b> orders for <b>ONE client</b> (the one you pick). It can never approve them: every order waits for your approval.<br><br>Give each AI the minimum it needs. You can revoke a connection at any time.' }
    });
    window.explainRegister('human_approval', {
      es: { t: 'Aprobación humana', b: 'Una IA conectada por MCP <b>no puede mover dinero sola</b>. Cuando propone una orden, Khipus corre los controles de riesgo del cliente y la deja <b>pendiente</b> en <b>👥 Clientes → Aprobaciones</b>. Solo una persona con el PIN de trading la aprueba (o la rechaza).<br><br>Única excepción, opcional: si en Railway pones <code>BROKERAGE_AUTO_APPROVE_PAPER=on</code>, las órdenes de cuentas de <b>PAPEL</b> (dinero simulado) se envían sin esperar. El dinero real siempre requiere aprobación.<br><br>Interruptores: <code>MCP_TRADING_ENABLED=off</code> apaga el trading por MCP; <code>BROKERAGE_TRADING_ENABLED=off</code> bloquea toda orden nueva.' },
      en: { t: 'Human approval', b: 'An AI connected through MCP <b>cannot move money on its own</b>. When it proposes an order, Khipus runs the client’s risk checks and leaves it <b>pending</b> in <b>👥 Clients → Approvals</b>. Only a person with the trading PIN can approve (or reject) it.<br><br>Only optional exception: if you set <code>BROKERAGE_AUTO_APPROVE_PAPER=on</code> in Railway, orders for <b>PAPER</b> accounts (simulated money) are sent without waiting. Real money always requires approval.<br><br>Kill switches: <code>MCP_TRADING_ENABLED=off</code> turns off MCP trading; <code>BROKERAGE_TRADING_ENABLED=off</code> blocks every new order.' }
    });
  }

  /* ── red ───────────────────────────────────────────────────────────── */
  function tfetch(url, opts) {
    if (window._tradeFetch) return window._tradeFetch(url, opts || {}, true);
    return Promise.reject(new Error(L('Falta el módulo de PIN de trading', 'Trading PIN helper missing')));
  }
  function readJSON(r) {
    return r.json().catch(function () { return { error: 'HTTP ' + r.status }; }).then(function (d) { d = d || {}; d._status = r.status; return d; });
  }
  function pinCall(method, path, body) {
    var o = { method: method, headers: { 'Content-Type': 'application/json', 'X-Khipu-Actor': actor() } };
    if (body) o.body = JSON.stringify(body);
    return tfetch(path, o).then(readJSON);
  }
  function errText(d) {
    if (!d) return L('Error desconocido', 'Unknown error');
    if (d._status === 403 && d.code === 'trading_disabled') return L('El PIN de trading no está configurado en el servidor: añade TRADE_PIN en Railway.', 'The trading PIN is not configured on the server: add TRADE_PIN in Railway.');
    if (d._status === 401) return L('PIN de trading incorrecto. Vuelve a intentarlo.', 'Wrong trading PIN. Try again.');
    if (d._status === 503) return L('Falta la base de datos (DATABASE_URL): los tokens se guardan en Postgres.', 'The database (DATABASE_URL) is missing: tokens are stored in Postgres.');
    return (en() ? (d.error_en || d.error) : d.error) || ('HTTP ' + d._status);
  }

  function endpoint() { return (S.status && S.status.endpoint) || (location.origin + '/mcp'); }

  function loadStatus() {
    return fetch('/api/mcp/status').then(readJSON).then(function (d) { S.status = d._status === 200 ? d : null; })
      .catch(function () { S.status = null; });
  }
  function loadTools() {
    return fetch('/api/mcp/tools').then(readJSON).then(function (d) { S.tools = d.tools || []; }).catch(function () { S.tools = []; });
  }
  function loadClients() {
    // tolera 404/503: sin módulo de corretaje simplemente no hay «trade»
    return tfetch('/api/brokerage/clients', { method: 'GET' }).then(readJSON).then(function (d) {
      if (d._status === 200) { S.clients = d.clients || []; S.clientsErr = null; }
      else { S.clients = []; S.clientsErr = d._status === 404 ? L('El módulo de corretaje no está instalado.', 'The brokerage module is not installed.') : errText(d); }
    }).catch(function () { S.clients = []; S.clientsErr = L('No se pudo leer la lista de clientes.', 'Could not read the client list.'); });
  }
  function loadTokens() {
    return pinCall('GET', '/api/mcp/tokens').then(function (d) {
      if (d._status === 200) { S.tokens = d.tokens || []; } else { S.tokens = []; S.msg = { err: true, t: errText(d) }; }
    });
  }
  function loadAudit() {
    return pinCall('GET', '/api/mcp/audit?limit=150').then(function (d) {
      if (d._status === 200) { S.audit = d.audit || []; } else { S.audit = []; S.msg = { err: true, t: errText(d) }; }
    });
  }

  /* ── estilos ───────────────────────────────────────────────────────── */
  // KHIPUS OS (2026-10-10): el overlay vive FUERA de #bcp-ov y lleva .kos-themed → mismos tokens --os-*
  // que las ventanas (claro = body sin .dark, oscuro = body.dark; los define engine/cockpit.js). Solo tokens:
  // el valor tras la coma es el respaldo OSCURO por si cockpit.js aún no cargó. Tarjetas de Khipus OS sin
  // bordes, botones píldora, pestañas = control segmentado, textos semánticos con contraste AA (*-ink).
  var F = "'Nunito','Geist',system-ui,-apple-system,'Segoe UI',sans-serif", MONO = 'ui-monospace,SFMono-Regular,Menlo,Consolas,monospace';
  function css() {
    if (document.getElementById('kmcp-css')) return;
    var st = document.createElement('style'); st.id = 'kmcp-css';
    st.textContent =
      '#kmcp-ov{position:fixed;inset:0;z-index:7850;display:none;align-items:flex-start;justify-content:center;overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain;' +
        'background:var(--kos-scrim,rgba(0,0,0,.5));-webkit-backdrop-filter:blur(10px) saturate(1.1);backdrop-filter:blur(10px) saturate(1.1);font-family:var(--os-font,' + F + ')}' +
      '#kmcp-ov.show{display:flex}' +
      '#kmcp{box-sizing:border-box;width:min(980px,96vw);max-width:100%;margin:3vh 0;border-radius:24px;min-width:0;padding:22px 24px 24px;' +
        'background:var(--os-bg,#0E0F14);color:var(--os-ink,#F2F2F5);box-shadow:var(--kos-shadow-lg,0 2px 8px rgba(0,0,0,.45),0 22px 56px rgba(0,0,0,.55));' +
        'font-size:14px;line-height:1.5;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;animation:kmcpPop .22s ease}' +
      '@keyframes kmcpPop{from{opacity:0;transform:translateY(6px) scale(.985)}to{opacity:1;transform:none}}' +
      '#kmcp *{box-sizing:border-box}' +
      '#kmcp button,#kmcp input,#kmcp select{font-family:inherit}' +
      '#kmcp .hd{display:flex;align-items:center;gap:10px;margin-bottom:6px}' +
      '#kmcp .hd h2{margin:0;font-size:20px;font-weight:800;letter-spacing:-.015em;flex:1;min-width:0;color:var(--os-ink,#F2F2F5);overflow-wrap:anywhere}' +
      '#kmcp .x{appearance:none;-webkit-appearance:none;width:40px;height:40px;flex:none;padding:0;border:0;border-radius:999px;background:transparent;color:var(--os-ink-2,#A6A8B5);' +
        'cursor:pointer;font-size:15px;font-weight:600;display:inline-flex;align-items:center;justify-content:center;transition:background-color .15s,color .15s}' +
      '#kmcp .x:hover{background:var(--os-surface-2,#1F2029);color:var(--os-ink,#F2F2F5)}' +
      '#kmcp .sub{font-size:13px;color:var(--os-ink-2,#A6A8B5);line-height:1.55;margin:0 0 14px;max-width:820px}' +
      // pestañas = control segmentado (como el comité y las ventanas nativas). Clases propias kmcp-tab(s): las
      // genéricas .tab/.tabs de app.html (barra clásica: mayúsculas, subrayado ::after) se colaban aquí.
      '#kmcp .kmcp-tabs{display:flex;flex-wrap:wrap;gap:2px;width:fit-content;max-width:100%;padding:3px;border-radius:20px;background:var(--os-surface-3,#2A2B36);margin-bottom:16px}' +
      '#kmcp .kmcp-tab{appearance:none;-webkit-appearance:none;border:0;cursor:pointer;min-height:34px;padding:0 14px;border-radius:999px;background:none;color:var(--os-ink-2,#A6A8B5);' +
        'font-size:13px;font-weight:700;white-space:nowrap;transition:background-color .15s,color .15s,box-shadow .15s}' +
      '#kmcp .kmcp-tab:hover{color:var(--os-ink,#F2F2F5)}' +
      '#kmcp .kmcp-tab.on{background:var(--os-surface,#17181F);color:var(--os-ink,#F2F2F5);box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35))}' +
      // tarjetas de Khipus OS: superficie, radio 18, sombra suave, sin bordes
      '#kmcp .card{background:var(--os-surface,#17181F);border-radius:var(--os-r,18px);box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35));' +
        'padding:16px 18px;margin-bottom:14px;min-width:0}' +
      '#kmcp .card.hi{box-shadow:0 0 0 2px var(--os-accent,#4C8DF6),var(--os-shadow,0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35))}' +
      '#kmcp h3{display:flex;align-items:center;flex-wrap:wrap;gap:4px;font-size:13.5px;font-weight:800;letter-spacing:-.005em;margin:0 0 10px;color:var(--os-ink,#F2F2F5)}' +
      '#kmcp .row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:8px 0}' +
      '#kmcp .kv{margin:0;padding:7px 0;border-bottom:1px solid var(--os-line,rgba(255,255,255,.07))}#kmcp .kv:last-child{border-bottom:0}' +
      '#kmcp .kv .note{min-width:150px}' +
      // campos: sin borde, fondo suave, anillo de foco
      '#kmcp input[type=text],#kmcp select{height:40px;border:0;border-radius:var(--os-r-sm,12px);padding:0 12px;font-size:13.5px;color:var(--os-ink,#F2F2F5);' +
        'background:var(--os-surface-2,#1F2029);outline:none;max-width:100%;min-width:0;transition:box-shadow .15s}' +
      '#kmcp select{cursor:pointer;padding-right:8px}' +
      '#kmcp input::placeholder{color:var(--os-ink-2,#A6A8B5);opacity:.85}' +
      '#kmcp input[type=text]:focus,#kmcp select:focus{box-shadow:inset 0 0 0 1.5px var(--os-accent,#4C8DF6),0 0 0 3px var(--kos-accent-soft,rgba(76,141,246,.16))}' +
      '#kmcp input[type=checkbox]{width:16px;height:16px;accent-color:var(--os-accent,#4C8DF6);cursor:pointer}' +
      '#kmcp input[type=checkbox]:disabled{cursor:default}' +
      '#kmcp .sc{display:flex;gap:9px;align-items:flex-start;font-size:13.5px;line-height:1.5;margin:8px 0;color:var(--os-ink,#F2F2F5)}#kmcp .sc input{margin-top:3px;flex:none}' +
      '#kmcp .sc label{cursor:pointer}' +
      // botones = píldoras: principal oscuro/claro según el tema, secundario suave, peligro teñido
      '#kmcp .btn{appearance:none;-webkit-appearance:none;border:0;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:6px;height:40px;padding:0 18px;' +
        'border-radius:999px;background:var(--os-btn,#F2F2F5);color:var(--os-btn-ink,#111216);font-size:13.5px;font-weight:700;letter-spacing:-.005em;white-space:nowrap;' +
        'transition:opacity .15s,background-color .15s,transform .1s}' +
      '#kmcp .btn:hover:not(:disabled){opacity:.88}#kmcp .btn:active{transform:scale(.98)}' +
      '#kmcp .btn:disabled{opacity:.45;cursor:default;transform:none}' +
      '#kmcp .btn.gh{background:var(--os-surface-2,#1F2029);color:var(--os-ink,#F2F2F5);font-weight:600}' +
      '#kmcp .btn.gh:hover:not(:disabled){background:var(--os-surface-3,#2A2B36);opacity:1}' +
      '#kmcp .btn.red{color:var(--os-bad-ink,#F47C7C);background:var(--os-surface-2,#1F2029);background:color-mix(in srgb,var(--os-bad,#f06565) 12%,transparent)}' +
      '#kmcp .btn.red:hover:not(:disabled){opacity:1;background:color-mix(in srgb,var(--os-bad,#f06565) 20%,transparent)}' +
      '#kmcp .btn.sm{height:34px;padding:0 14px;font-size:12.5px}' +
      // foco de teclado VISIBLE (WCAG 2.4.7)
      '#kmcp button:focus-visible,#kmcp input:focus-visible,#kmcp select:focus-visible,#kmcp label:focus-visible{outline:2px solid var(--os-accent,#4C8DF6);outline-offset:2px}' +
      // textos y avisos (colores semánticos de TEXTO = *-ink: ≥ 4.5:1 en claro y oscuro)
      '#kmcp .note{font-size:12.5px;color:var(--os-ink-2,#A6A8B5);line-height:1.55}' +
      '#kmcp .ok{color:var(--os-good-ink,#2fbf5b)}#kmcp .bad{color:var(--os-bad-ink,#F47C7C)}#kmcp .wtx{color:var(--os-warn-ink,#F2C46D)}' +
      '#kmcp .msg{padding:10px 14px;border-radius:var(--os-r-sm,12px);font-size:13px;font-weight:600;margin:4px 0 14px;line-height:1.5;overflow-wrap:anywhere}' +
      '#kmcp .msg.err{color:var(--os-bad-ink,#F47C7C);background:var(--os-surface-2,#1F2029);background:color-mix(in srgb,var(--os-bad,#f06565) 12%,transparent)}' +
      '#kmcp .msg.inf{color:var(--os-ink,#F2F2F5);background:var(--os-surface-2,#1F2029);background:color-mix(in srgb,var(--os-accent,#4C8DF6) 12%,transparent)}' +
      '#kmcp .warn{padding:10px 14px;border-radius:var(--os-r-sm,12px);color:var(--os-warn-ink,#F2C46D);font-size:13px;line-height:1.55;margin:8px 0;' +
        'background:var(--os-surface-2,#1F2029);background:color-mix(in srgb,var(--os-warn,#F2C46D) 14%,transparent)}' +
      '#kmcp code{font-family:' + MONO + ';font-size:12.5px}#kmcp code.ep{color:var(--os-accent,#4C8DF6);word-break:break-all}' +
      '#kmcp pre{margin:8px 0;padding:12px 14px;border-radius:var(--os-r-sm,12px);background:var(--os-surface-2,#1F2029);color:var(--os-ink,#F2F2F5);font-family:' + MONO + ';' +
        'font-size:12px;line-height:1.55;white-space:pre-wrap;word-break:break-all;overflow-wrap:anywhere;max-width:100%}' +
      '#kmcp .tok{font-family:' + MONO + ';font-size:13.5px;color:var(--os-ink,#F2F2F5);word-break:break-all;padding:12px 14px;border-radius:var(--os-r-sm,12px);' +
        'background:var(--os-surface-2,#1F2029);box-shadow:inset 0 0 0 1.5px var(--os-accent,#4C8DF6)}' +
      '#kmcp .pill{display:inline-flex;align-items:center;padding:2px 9px;border-radius:999px;font-size:11.5px;font-weight:700;margin:1px 4px 1px 0;' +
        'background:var(--os-surface-2,#1F2029);color:var(--os-ink-2,#A6A8B5)}' +
      '#kmcp .pill.t{color:var(--os-warn-ink,#F2C46D);background:color-mix(in srgb,var(--os-warn,#F2C46D) 16%,transparent)}' +
      '#kmcp .pill.r{color:var(--os-ai,#B48CFF);background:color-mix(in srgb,var(--os-ai,#B48CFF) 13%,transparent)}' +
      // selector de IA = control segmentado pequeño
      '#kmcp .cfgt{display:flex;gap:2px;flex-wrap:wrap;width:fit-content;max-width:100%;padding:3px;border-radius:18px;background:var(--os-surface-2,#1F2029);margin:8px 0}' +
      '#kmcp .cfgt button{appearance:none;-webkit-appearance:none;border:0;min-height:30px;padding:0 12px;border-radius:999px;background:none;color:var(--os-ink-2,#A6A8B5);' +
        'cursor:pointer;font-size:12.5px;font-weight:700;white-space:nowrap;transition:background-color .15s,color .15s,box-shadow .15s}' +
      '#kmcp .cfgt button:hover{color:var(--os-ink,#F2F2F5)}' +
      '#kmcp .cfgt button.on{background:var(--os-surface,#17181F);color:var(--os-ink,#F2F2F5);box-shadow:var(--os-shadow,0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.35))}' +
      '#kmcp .list .it{border-bottom:1px solid var(--os-line,rgba(255,255,255,.07));padding:10px 0;display:flex;gap:10px;align-items:flex-start;flex-wrap:wrap}' +
      '#kmcp .list .it:last-child{border-bottom:0}#kmcp .list .it .grow{flex:1;min-width:200px}' +
      '#kmcp .scroll{overflow-x:auto;max-width:100%}#kmcp table{width:100%;border-collapse:collapse;font-size:12.5px}' +
      '#kmcp th,#kmcp td{padding:7px 8px;border-bottom:1px solid var(--os-line,rgba(255,255,255,.07));text-align:left;vertical-align:top}' +
      '#kmcp th{color:var(--os-ink-2,#A6A8B5);font-weight:700;font-size:11.5px;white-space:nowrap}#kmcp tbody tr:last-child td{border-bottom:0}' +
      '#kmcp td.args{font-family:' + MONO + ';font-size:11px;color:var(--os-ink-2,#A6A8B5);max-width:260px;word-break:break-all}' +
      '#kmcp .tl .it b{color:var(--os-ink,#F2F2F5)}#kmcp .tl .it .d{font-size:12.5px;color:var(--os-ink-2,#A6A8B5);line-height:1.5;margin-top:2px}' +
      '#kmcp .aud-cards{display:none}#kmcp .aud-cards .it{border-bottom:1px solid var(--os-line,rgba(255,255,255,.07));padding:9px 0}' +
      '#kmcp .aud-cards .it:last-child{border-bottom:0}' +
      // el «?» de explain.js trae cian fijo: aquí toma el acento del tema (legible en claro)
      '#kmcp span[onclick*="explainMetric"]{color:var(--os-accent,#4C8DF6)!important;border-color:color-mix(in srgb,var(--os-accent,#4C8DF6) 45%,transparent)!important}' +
      '@media(prefers-reduced-motion:reduce){#kmcp{animation:none}#kmcp .kmcp-tab,#kmcp .btn,#kmcp .cfgt button,#kmcp .x{transition:none}}' +
      // móvil: hoja a pantalla completa, una sola columna, registro en tarjetas
      '@media(max-width:760px){#kmcp-ov{align-items:stretch}' +
        '#kmcp{width:100vw;max-width:100vw;margin:0;border-radius:0;min-height:100%;padding:16px 14px calc(22px + env(safe-area-inset-bottom,0px))}' +
        '#kmcp .hd h2{font-size:17px}#kmcp .card{padding:14px}' +
        '#kmcp .aud-cards{display:block}#kmcp .aud-table{display:none}' +
        '#kmcp .btn{width:100%}#kmcp .row .btn.sm{width:auto}#kmcp td.args{max-width:140px}#kmcp .kv .note{min-width:120px}}';
    document.head.appendChild(st);
  }
  function shell() {
    css();
    var ov = document.getElementById('kmcp-ov');
    if (!ov) {
      ov = document.createElement('div'); ov.id = 'kmcp-ov';
      ov.className = 'kos-themed';   // tokens --os-* de Khipus OS (claro/oscuro) fuera de #bcp-ov
      ov.innerHTML = '<div id="kmcp" role="dialog" aria-modal="true"></div>';
      ov.addEventListener('click', function (e) { if (e.target === ov) close(); });
      document.body.appendChild(ov);
    }
    return ov;
  }

  /* ── configuraciones listas para pegar ─────────────────────────────── */
  function configs(tok) {
    var url = endpoint(), t = tok || '<TOKEN>';
    var out = {
      claude_code: { name: 'Claude Code', how: L('Pega esto en tu terminal:', 'Paste this in your terminal:'),
        code: 'claude mcp add --transport http khipus ' + url + ' --header "Authorization: Bearer ' + t + '"' },
      claude_desktop: { name: 'Claude Desktop', how: L('Ajustes → Desarrollador → Editar config (claude_desktop_config.json), pega esto y reinicia Claude Desktop (necesita Node.js):', 'Settings → Developer → Edit config (claude_desktop_config.json), paste this and restart Claude Desktop (needs Node.js):'),
        code: JSON.stringify({ mcpServers: { khipus: { command: 'npx', args: ['-y', 'mcp-remote', url, '--header', 'Authorization:${KHIPUS_AUTH}'], env: { KHIPUS_AUTH: 'Bearer ' + t } } } }, null, 2) },
      cursor: { name: 'Cursor', how: L('Cursor → Settings → MCP → Add new global MCP server (archivo ~/.cursor/mcp.json):', 'Cursor → Settings → MCP → Add new global MCP server (file ~/.cursor/mcp.json):'),
        code: JSON.stringify({ mcpServers: { khipus: { url: url, headers: { Authorization: 'Bearer ' + t } } } }, null, 2) },
      curl: { name: L('Prueba (curl)', 'Test (curl)'), how: L('Prueba rápida desde cualquier terminal: debe listar las herramientas.', 'Quick test from any terminal: it should list the tools.'),
        code: 'curl -s -X POST ' + url + ' \\\n  -H "Authorization: Bearer ' + t + '" \\\n  -H "Content-Type: application/json" \\\n  -H "Accept: application/json, text/event-stream" \\\n  -d \'{"jsonrpc":"2.0","id":1,"method":"tools/list"}\'' }
    };
    if (S.status && S.status.oauth) {
      out.connector = { name: 'claude.ai / ChatGPT', how: L('claude.ai: Ajustes → Conectores → Añadir conector personalizado. ChatGPT: Ajustes → Conectores (modo desarrollador) → Crear. Pega SOLO esta URL; al conectar se abrirá una página de Khipus donde escribes tu PIN y eliges permisos (no necesitas el token de arriba):', 'claude.ai: Settings → Connectors → Add custom connector. ChatGPT: Settings → Connectors (developer mode) → Create. Paste ONLY this URL; when connecting a Khipus page opens where you enter your PIN and pick permissions (you do not need the token above):'),
        code: url };
    }
    return out;
  }
  function cfgBlock(tok) {
    var c = configs(tok), keys = Object.keys(c);
    if (keys.indexOf(S.cfg) < 0) S.cfg = keys[0];
    var cur = c[S.cfg];
    return '<div class="cfgt">' + keys.map(function (k) { return '<button data-cfg="' + k + '" class="' + (k === S.cfg ? 'on' : '') + '">' + esc(c[k].name) + '</button>'; }).join('') + '</div>' +
      '<div class="note">' + esc(cur.how) + '</div><pre id="kmcp-cfg">' + esc(cur.code) + '</pre>' +
      '<div class="row"><button class="btn sm" data-act="copy-cfg">📋 ' + esc(L('Copiar', 'Copy')) + '</button></div>';
  }

  /* ── vistas ────────────────────────────────────────────────────────── */
  function header() {
    return '<div class="hd"><h2>🤖 ' + esc(L('Conectar IAs (MCP)', 'Connect AIs (MCP)')) + chip('mcp') + '</h2><button class="x" data-act="close" aria-label="close">✕</button></div>' +
      '<div class="sub">' + esc(L('Deja que Claude, ChatGPT, Cursor o tu propio agente consulten Khipus (grafo, empresas en vivo, investigación, riesgo) y —si lo permites— propongan órdenes que TÚ apruebas.',
        'Let Claude, ChatGPT, Cursor or your own agent query Khipus (graph, live companies, research, risk) and —if you allow it— propose orders that YOU approve.')) + '</div>' +
      '<div class="kmcp-tabs" role="tablist">' + [['connect', '🔌 ' + L('Conectar', 'Connect')], ['tokens', '🔑 ' + L('Conexiones', 'Connections')], ['audit', '📜 ' + L('Registro', 'Log')], ['tools', '🧰 ' + L('Herramientas', 'Tools')]]
        .map(function (t) { return '<button type="button" role="tab" aria-selected="' + (S.tab === t[0]) + '" class="kmcp-tab' + (S.tab === t[0] ? ' on' : '') + '" data-tab="' + t[0] + '">' + esc(t[1]) + '</button>'; }).join('') + '</div>' +
      (S.msg ? '<div class="msg ' + (S.msg.err ? 'err' : 'inf') + '">' + esc(S.msg.t) + '</div>' : '');
  }

  function statusCard() {
    var st = S.status;
    if (!st) return '<div class="msg err">' + esc(L('El servidor MCP no responde (¿módulo no instalado?).', 'The MCP server does not respond (module not installed?).')) + '</div>';
    var items = [
      [L('Dirección MCP', 'MCP address'), '<code class="ep">' + esc(st.endpoint) + '</code>'],
      [L('Estado', 'Status'), st.enabled ? '<span class="ok">● ' + esc(L('encendido', 'on')) + '</span>' : '<span class="bad">● ' + esc(L('apagado (MCP_ENABLED=off)', 'off (MCP_ENABLED=off)')) + '</span>'],
      [L('Base de datos', 'Database'), st.db ? '<span class="ok">✓</span>' : '<span class="bad">✗ ' + esc(L('falta DATABASE_URL: no se pueden crear tokens', 'DATABASE_URL missing: tokens cannot be created')) + '</span>'],
      ['OAuth (claude.ai / ChatGPT)', st.oauth ? '<span class="ok">✓</span>' : '<span class="bad">✗</span>'],
      [L('Trading por MCP', 'MCP trading'), st.mcp_trading_enabled && st.brokerage_available ? '<span class="ok">✓ ' + esc(L('con aprobación humana', 'with human approval')) + '</span>' + chip('human_approval') : '<span class="bad">✗</span>' + chip('human_approval')],
      [L('Versiones del protocolo', 'Protocol versions'), esc((st.protocol_versions || []).join(', '))],
      [L('PIN de trading', 'Trading PIN'), !st.pin_set ? '<span class="bad">✗ ' + esc(L('falta TRADE_PIN en Railway', 'TRADE_PIN missing in Railway')) + '</span>' :
        (st.pin_locked_s > 0 ? '<span class="bad">🔒 ' + esc(L('bloqueado por demasiados intentos fallidos (~' + Math.ceil(st.pin_locked_s / 60) + ' min)', 'locked after too many wrong attempts (~' + Math.ceil(st.pin_locked_s / 60) + ' min)')) + '</span>' :
        (st.pin_strong ? '<span class="ok">✓</span>' : '<span class="wtx">⚠ ' + esc(L('corto: usa al menos ' + (st.pin_min_length || 8) + ' caracteres (letras y números)', 'short: use at least ' + (st.pin_min_length || 8) + ' characters (letters and numbers)')) + '</span>'))]
    ];
    return '<div class="card"><h3>' + esc(L('Estado', 'Status')) + '</h3>' + items.map(function (x) { return '<div class="row kv"><span class="note">' + esc(x[0]) + '</span><span style="font-size:13px;min-width:0">' + x[1] + '</span></div>'; }).join('') + '</div>';
  }

  function viewConnect() {
    var f = S.form, h = statusCard();
    if (S.created) {
      var c = S.created;
      h = '<div class="card hi"><h3>✅ ' + esc(L('Conexión creada: ', 'Connection created: ')) + esc(c.name) + '</h3>' +
        '<div class="warn">⚠️ ' + esc(L('Copia el token AHORA: no se vuelve a mostrar. Trátalo como una contraseña (quien lo tenga puede usar estos permisos).', 'Copy the token NOW: it is never shown again. Treat it like a password (whoever has it can use these permissions).')) + '</div>' +
        '<div class="tok" id="kmcp-tok">' + esc(c.token) + '</div><div class="row"><button class="btn sm" data-act="copy-tok">📋 ' + esc(L('Copiar token', 'Copy token')) + '</button>' +
        '<span class="note">' + esc(L('Permisos: ', 'Scopes: ')) + (c.scopes || []).map(scopePill).join('') + (c.client_name ? ' · ' + esc(L('cliente: ', 'client: ')) + esc(c.client_name) : '') + '</span></div>' +
        '<h3 style="margin-top:12px">' + esc(L('Pégalo en tu IA', 'Paste it into your AI')) + '</h3>' + cfgBlock(c.token) +
        '<div class="row"><button class="btn gh sm" data-act="new">➕ ' + esc(L('Crear otra conexión', 'Create another connection')) + '</button></div></div>';
      return h + statusCard();
    }
    var cl = S.clients;
    var clientSel = cl === null ? '<span class="note">' + esc(L('Cargando clientes…', 'Loading clients…')) + '</span>' :
      (cl.length ? '<select id="kmcp-client"><option value="">' + esc(L('— elige el cliente —', '— pick the client —')) + '</option>' + cl.map(function (c) {
        return '<option value="' + esc(c.id) + '"' + (f.client === c.id ? ' selected' : '') + '>' + esc(c.name) + ' · ' + (c.mode === 'live' ? '🔴 ' + L('DINERO REAL', 'REAL MONEY') : '🧪 ' + L('PAPEL', 'PAPER')) + '</option>';
      }).join('') + '</select>' : '<span class="note">' + esc(S.clientsErr || L('No hay clientes de corretaje todavía (👥 Clientes).', 'No brokerage clients yet (👥 Clients).')) + '</span>');
    h += '<div class="card"><h3>' + esc(L('1 · Crear una conexión', '1 · Create a connection')) + chip('mcp_scopes') + '</h3>' +
      '<div class="row"><input type="text" id="kmcp-name" maxlength="100" style="flex:1;min-width:0;width:100%" placeholder="' + esc(L('Nombre (ej. «Claude de Fabrizio»)', 'Name (e.g. “Fabrizio’s Claude”)')) + '" value="' + esc(f.name) + '"></div>' +
      '<div class="sc"><input type="checkbox" checked disabled><span><b>read</b> — ' + esc(L('consultar grafo, empresas, ontología, investigación, riesgo, eventos (siempre incluido).', 'query graph, companies, ontology, research, risk, events (always included).')) + '</span></div>' +
      '<div class="sc"><input type="checkbox" id="kmcp-sr"' + (f.research ? ' checked' : '') + '><label for="kmcp-sr"><b>research</b> — ' + esc(L('lanzar investigación y el comité (gasta presupuesto de IA).', 'start research and the committee (uses AI budget).')) + '</label></div>' +
      '<div class="sc"><input type="checkbox" id="kmcp-st"' + (f.trade ? ' checked' : '') + (cl && !cl.length && !f.trade ? ' disabled' : '') + '><span><label for="kmcp-st"><b>trade</b> — ' + esc(L('ver la cuenta y PROPONER órdenes de UN cliente. Cada orden espera tu aprobación en 👥 Clientes → Aprobaciones.', 'see the account and PROPOSE orders for ONE client. Every order waits for your approval in 👥 Clients → Approvals.')) + '</label>' + chip('human_approval') + '</span></div>' +
      (f.trade ? '<div class="row" style="margin-left:24px">' + clientSel + '</div>' : '') +
      '<div class="row"><button class="btn" data-act="create"' + (S.busy || (S.status && !S.status.db) ? ' disabled' : '') + '>' + esc(S.busy ? L('Creando…', 'Creating…') : L('Crear token (pide tu PIN)', 'Create token (asks your PIN)')) + '</button></div>' +
      '<div class="note">' + esc(L('El token se muestra una sola vez. Khipus solo guarda su huella; si lo pierdes, revócalo y crea otro.', 'The token is shown once. Khipus only stores its fingerprint; if you lose it, revoke it and create another.')) + '</div></div>';
    h += '<div class="card"><h3>' + esc(L('2 · Cómo se conecta cada IA', '2 · How each AI connects')) + '</h3><div class="note">' + esc(L('Vista previa: al crear el token, estas instrucciones ya lo traen pegado.', 'Preview: once you create the token, these instructions include it.')) + '</div>' + cfgBlock(null) + '</div>';
    return h;
  }

  function scopePill(s) { return '<span class="pill ' + (s === 'trade' ? 't' : s === 'research' ? 'r' : '') + '">' + esc(s) + '</span>'; }

  function viewTokens() {
    var h = '<div class="card"><h3>' + esc(L('Conexiones', 'Connections')) + chip('mcp_scopes') + '</h3>';
    if (!S.tokens.length) return h + '<div class="note">' + esc(L('Todavía no hay conexiones.', 'No connections yet.')) + '</div></div>';
    h += '<div class="list">' + S.tokens.map(function (t) {
      var state = t.revoked ? '<span class="bad">' + esc(L('revocada', 'revoked')) + '</span>' : t.expired ? '<span class="bad">' + esc(L('caducada', 'expired')) + '</span>' : '<span class="ok">' + esc(L('activa', 'active')) + '</span>';
      return '<div class="it"><div class="grow"><b>' + esc(t.name) + '</b> <span class="note">' + esc(t.prefix) + ' · ' + esc(t.kind === 'oauth' ? 'OAuth' : L('token manual', 'manual token')) + '</span><br>' +
        (t.scopes || []).map(scopePill).join('') + (t.client_name || t.client_id ? '<span class="note"> · ' + esc(L('cliente: ', 'client: ')) + esc(t.client_name || t.client_id) + '</span>' : '') +
        '<div class="note">' + esc(L('Creada ', 'Created ')) + esc(when(t.created_at)) + ' · ' + esc(L('último uso ', 'last used ')) + esc(when(t.last_used_at)) + ' · ' + esc(String(t.use_count || 0)) + ' ' + esc(L('llamadas', 'calls')) + (t.expires_at ? ' · ' + esc(L('caduca ', 'expires ')) + esc(when(t.expires_at)) : '') + ' · ' + state + '</div></div>' +
        (t.revoked ? '' : '<button class="btn red sm" data-revoke="' + esc(t.id) + '">' + esc(L('Revocar', 'Revoke')) + '</button>') + '</div>';
    }).join('') + '</div></div>';
    if (window.KhipuClients && window.KhipuClients.open) h += '<div class="row"><button class="btn gh" data-act="approvals">👥 ' + esc(L('Ver órdenes pendientes de aprobación', 'See orders waiting for approval')) + '</button></div>';
    return h;
  }

  function viewAudit() {
    var h = '<div class="card"><h3>' + esc(L('Últimas llamadas de las IAs', 'Latest AI calls')) + '</h3><div class="note">' + esc(L('Registro permanente de cada llamada (no se edita ni se borra; sin secretos): quién, qué herramienta, con qué argumentos, resultado y demora.', 'Append-only log of every call (never edited or deleted; no secrets): who, which tool, which arguments, result and latency.')) + '</div>';
    if (!S.audit.length) return h + '<div class="note" style="margin-top:8px">' + esc(L('Sin llamadas todavía.', 'No calls yet.')) + '</div></div>';
    // móvil: tarjetas apiladas (una tabla de 6 columnas no cabe en 375 px)
    h += '<div class="aud-cards">' + S.audit.map(function (a) {
      var args = '';
      try { args = JSON.stringify(a.args || {}); } catch (e) { args = ''; }
      if (args.length > 120) args = args.slice(0, 120) + '…';
      return '<div class="it"><div class="grow"><b>' + esc(a.tool || a.method || '—') + '</b> <span class="' + (a.status === 'ok' ? 'ok' : 'bad') + '">' + esc(a.status) + '</span>' +
        '<div class="note">' + esc(when(a.ts)) + ' · ' + esc(a.token_name || '—') + (a.latency_ms == null ? '' : ' · ' + esc(a.latency_ms) + ' ms') + '</div>' +
        (a.error ? '<div class="note bad">' + esc(String(a.error).slice(0, 120)) + '</div>' : '') +
        (args && args !== '{}' ? '<div class="note" style="font-family:ui-monospace,Menlo,monospace;word-break:break-all">' + esc(args) + '</div>' : '') + '</div></div>';
    }).join('') + '</div>';
    h += '<div class="scroll aud-table"><table><thead><tr><th>' + esc(L('Hora', 'Time')) + '</th><th>' + esc(L('Conexión', 'Connection')) + '</th><th>' + esc(L('Acción', 'Action')) + '</th><th>' + esc(L('Resultado', 'Result')) + '</th><th>ms</th><th>' + esc(L('Argumentos', 'Arguments')) + '</th></tr></thead><tbody>' +
      S.audit.map(function (a) {
        var cls = a.status === 'ok' ? 'ok' : 'bad';
        var args = '';
        try { args = JSON.stringify(a.args || {}); } catch (e) { args = ''; }
        if (args.length > 160) args = args.slice(0, 160) + '…';
        return '<tr><td>' + esc(when(a.ts)) + '</td><td>' + esc(a.token_name || '—') + '</td><td>' + esc(a.tool || a.method || '—') + '</td><td class="' + cls + '">' + esc(a.status) + (a.error ? '<br><span class="note">' + esc(String(a.error).slice(0, 120)) + '</span>' : '') + '</td><td>' + esc(a.latency_ms == null ? '—' : a.latency_ms) + '</td><td class="args">' + esc(args) + '</td></tr>';
      }).join('') + '</tbody></table></div></div>';
    return h;
  }

  function viewTools() {
    var groups = { read: [], research: [], trade: [] };
    (S.tools || []).forEach(function (t) { (groups[t.scope] = groups[t.scope] || []).push(t); });
    var lab = { read: L('Consultar (read)', 'Query (read)'), research: L('Investigar (research)', 'Research'), trade: L('Operar (trade · con aprobación humana)', 'Trade (with human approval)') };
    var h = '<div class="note" style="margin-bottom:8px">' + esc(L('Lo que una IA conectada puede hacer, según los permisos de su conexión. Las descripciones están en inglés porque las lee la IA.', 'What a connected AI can do, depending on its connection’s permissions. Descriptions are in English because the AI reads them.')) + '</div>';
    Object.keys(groups).forEach(function (g) {
      if (!groups[g].length) return;
      h += '<div class="card tl"><h3>' + esc(lab[g] || g) + (g === 'trade' ? chip('human_approval') : '') + '</h3><div class="list">' + groups[g].map(function (t) {
        return '<div class="it"><div class="grow"><b>' + esc(t.name) + '</b> <span class="note">' + esc(t.title || '') + '</span><div class="d">' + esc(t.description) + '</div></div></div>';
      }).join('') + '</div></div>';
    });
    return h;
  }

  function render() {
    var box = document.getElementById('kmcp'); if (!box) return;
    var body = S.tab === 'tokens' ? viewTokens() : S.tab === 'audit' ? viewAudit() : S.tab === 'tools' ? viewTools() : viewConnect();
    box.innerHTML = header() + body;
    wire(box);
  }

  /* ── acciones ──────────────────────────────────────────────────────── */
  function copy(text) {
    function fallback() {
      var ta = document.createElement('textarea'); ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); } catch (e) {}
      document.body.removeChild(ta);
    }
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).catch(fallback);
      else fallback();
    } catch (e) { fallback(); }
    if (typeof window.toast === 'function') window.toast(L('Copiado', 'Copied'));
  }
  function readForm() {
    var f = S.form, g = function (id) { return document.getElementById(id); };
    if (g('kmcp-name')) f.name = g('kmcp-name').value;
    if (g('kmcp-sr')) f.research = g('kmcp-sr').checked;
    if (g('kmcp-st')) f.trade = g('kmcp-st').checked;
    if (g('kmcp-client')) f.client = g('kmcp-client').value;
  }
  function create() {
    readForm();
    var f = S.form;
    if (!f.name.trim()) { S.msg = { err: true, t: L('Ponle un nombre a la conexión.', 'Give the connection a name.') }; return render(); }
    if (f.trade && !f.client) { S.msg = { err: true, t: L('Para «trade» elige el cliente que esta IA podrá operar.', 'For “trade” pick the client this AI may operate.') }; return render(); }
    var scopes = ['read'].concat(f.research ? ['research'] : []).concat(f.trade ? ['trade'] : []);
    S.busy = true; S.msg = null; render();
    pinCall('POST', '/api/mcp/tokens', { name: f.name.trim(), scopes: scopes, client_id: f.trade ? f.client : null, actor: actor() }).then(function (d) {
      S.busy = false;
      if (d._status === 201 && d.token) {
        S.created = d; S.form = { name: '', read: true, research: false, trade: false, client: '' };
        S.msg = { err: false, t: L('Listo. Copia el token y elige tu IA abajo.', 'Done. Copy the token and pick your AI below.') };
      } else { S.msg = { err: true, t: errText(d) }; }
      render();
    }).catch(function (e) { S.busy = false; S.msg = { err: true, t: String(e && e.message || e) }; render(); });
  }
  function revoke(id) {
    var t = S.tokens.filter(function (x) { return x.id === id; })[0];
    if (!window.confirm(L('¿Revocar «' + (t ? t.name : id) + '»? La IA perderá el acceso al instante.', 'Revoke “' + (t ? t.name : id) + '”? The AI loses access immediately.'))) return;
    pinCall('POST', '/api/mcp/tokens/' + encodeURIComponent(id) + '/revoke', { actor: actor() }).then(function (d) {
      S.msg = d._status === 200 ? { err: false, t: L('Conexión revocada.', 'Connection revoked.') } : { err: true, t: errText(d) };
      return loadTokens();
    }).then(render);
  }
  function setTab(tab) {
    S.tab = tab; S.msg = null; render();
    var p = tab === 'tokens' ? loadTokens() : tab === 'audit' ? loadAudit() : tab === 'tools' ? loadTools() : null;
    if (p) p.then(render);
  }
  function wire(box) {
    box.querySelectorAll('[data-tab]').forEach(function (b) { b.onclick = function () { setTab(b.getAttribute('data-tab')); }; });
    box.querySelectorAll('[data-cfg]').forEach(function (b) { b.onclick = function () { readForm(); S.cfg = b.getAttribute('data-cfg'); render(); }; });
    box.querySelectorAll('[data-revoke]').forEach(function (b) { b.onclick = function () { revoke(b.getAttribute('data-revoke')); }; });
    box.querySelectorAll('[data-act]').forEach(function (b) {
      b.onclick = function () {
        var a = b.getAttribute('data-act');
        if (a === 'close') close();
        else if (a === 'create') create();
        else if (a === 'new') { S.created = null; S.msg = null; render(); }
        else if (a === 'copy-tok' && S.created) copy(S.created.token);
        else if (a === 'copy-cfg') { var c = configs(S.created && S.created.token)[S.cfg]; if (c) copy(c.code); }
        else if (a === 'approvals') { close(); window.KhipuClients.open('approvals'); }
      };
    });
    var st = document.getElementById('kmcp-st');
    if (st) st.onchange = function () {
      readForm(); render();
      if (S.form.trade && S.clients === null) loadClients().then(render);
    };
  }

  function onKey(e) { if (e.key === 'Escape') close(); }
  function open(tab) {
    registerExplain();
    var ov = shell();
    ov.classList.add('show');
    document.addEventListener('keydown', onKey);
    S.tab = tab || S.tab || 'connect';
    S.msg = null;
    render();
    Promise.all([loadStatus(), loadTools()]).then(function () {
      render();
      if (S.tab === 'tokens') return loadTokens().then(render);
      if (S.tab === 'audit') return loadAudit().then(render);
    });
  }
  function close() {
    var ov = document.getElementById('kmcp-ov'); if (ov) ov.classList.remove('show');
    document.removeEventListener('keydown', onKey);
    // el token en claro no queda en memoria más de lo necesario
    if (S.created) S.created = null;
  }

  /* ── punto de entrada: dentro de 🩺 Sistema (regla «simplificar»: sin botón
     nuevo en la barra). Fila bajo las pestañas Diagnóstico/Registro/Propuestas,
     visible en las tres; abre este panel y cierra el de Sistema. ─────────── */
  function entryLabel() {
    return '<b>🤖 ' + esc(L('Conectar IAs (MCP)', 'Connect AIs (MCP)')) + '</b> <span style="opacity:.75;font-weight:400">— ' +
      esc(L('Claude, ChatGPT, Cursor o tu agente usan Khipus', 'Claude, ChatGPT, Cursor or your agent use Khipus')) + ' →</span>';
  }
  function installEntry() {
    var seg = document.getElementById('sistema-tabseg');
    if (!seg || !seg.parentNode) return false;
    var b = document.getElementById('kmcp-entry');
    if (!b) {
      b = document.createElement('button');
      b.id = 'kmcp-entry'; b.type = 'button'; b.className = 'key-btn';
      b.style.cssText = 'display:block;width:100%;text-align:left;margin:-6px 0 14px;padding:8px 11px;font-size:12.5px;line-height:1.4;white-space:normal;cursor:pointer';
      b.addEventListener('click', function (e) {
        e.preventDefault(); e.stopPropagation();
        if (window.closeSistema) window.closeSistema();
        open('connect');
      });
      seg.parentNode.insertBefore(b, seg.nextSibling);
      // el idioma puede cambiar: se re-rotula cada vez que se abre 🩺 Sistema
      var sb = document.getElementById('sistema-btn');
      if (sb) sb.addEventListener('click', function () { b.innerHTML = entryLabel(); b.title = L('Conectar IAs por MCP', 'Connect AIs through MCP'); });
    }
    b.innerHTML = entryLabel();
    b.title = L('Conectar IAs por MCP', 'Connect AIs through MCP');
    return true;
  }

  function boot() { registerExplain(); installEntry(); }
  registerExplain();
  // explain.js y el script inline de 🩺 Sistema corren ANTES/DESPUÉS de este archivo:
  // se registra/instala de nuevo cuando el DOM está listo (idempotente)
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
  window.KhipuMCP = { open: open, close: close, installEntry: installEntry };
})();
