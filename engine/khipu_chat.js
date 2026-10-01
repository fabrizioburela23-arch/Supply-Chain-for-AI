/* ============================================================================
   engine/khipu_chat.js — EL CHAT de Khipu (texto), compartido por la Cabina
   (engine/cockpit.js) y el Command Center (engine/command_center.js).

   Por qué existe (feedback de Fabrizio, 2026-09-30: "le pregunto algo y me
   responde otra cosa… siento que está limitado"): antes el texto pasaba por
   una cadena de regex sueltas que secuestraban las preguntas (p. ej. "dónde
   invertir" → pantalla de oportunidades) y TODO lo que no calzaba se
   convertía en un GRÁFICO de la pregunta. Ahora:

   1) classify(texto, deps) — enrutador PURO y de ALTA PRECISIÓN. Solo atajos
      explícitos: gramática KHIPU (NVDA XRAY…), "demo", órdenes (compra/vende,
      siempre con confirmación), "gráfico: …", "mi cuenta", nombres exactos de
      pantallas e imperativos anclados con empresa reconocida ("desármame
      Nvidia", "compara A y B", "simula que …"). Todo lo demás —y SIEMPRE las
      preguntas— va al cerebro: POST /api/khipu/chat (core/khipu_chat.py),
      que usa herramientas con datos reales.
   2) send(texto) — llama al cerebro con el historial (memoria en
      sessionStorage, últimos 12 turnos) y el contexto de pantalla.
   3) md(texto) — markdown ligero SEGURO (escapa HTML primero).
   4) appendUser / appendPending / fillReply — burbujas del hilo.
   5) runAction(acción) — ejecuta las acciones validadas por el servidor.

   API: window.KhipuChat. Bilingüe (window.LANG / localStorage.eco_lang).
   ============================================================================ */
(function (root) {
  'use strict';
  var W = root;
  var HIST_KEY = 'khipu_chat_hist_v1';
  var MAX_TURNS = 12;

  function lang() {
    try { return (W.LANG || (W.localStorage && W.localStorage.getItem('eco_lang')) || 'es') === 'en' ? 'en' : 'es'; }
    catch (e) { return 'es'; }
  }
  function L(es, en) { return lang() === 'en' ? en : es; }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  /* ══ 1) ENRUTADOR ══════════════════════════════════════════════════════ */
  var Q_START = /^(¿\s*)?(qu[eé]|c[oó]mo|cu[aá]l(es)?|cu[aá]nt[oa]s?|por\s*qu[eé]|porqu[eé]|para\s+qu[eé]|dime|expl[ií]ca(me|nos)?|cu[eé]ntame|qui[eé]n(es)?|d[oó]nde|cu[aá]ndo|conviene|vale\s+la\s+pena|es\s+(buena|bueno|mala|malo|cierto|verdad|posible|seguro|recomendable)|hay|puedes|podr[ií]as|deber[ií]a|what|how|why|which|who|whom|whose|when|where|explain|tell\s+me|is|are|does|do|did|can|could|should|would|will|has|have)\b/i;

  function isQuestion(t) {
    t = String(t || '').trim();
    return /[?¿]/.test(t) || Q_START.test(t);
  }

  var SCREENS = {
    'mapa': 'graph', 'grafo': 'graph', 'map': 'graph', 'graph': 'graph', 'el mapa': 'graph', 'el grafo': 'graph',
    'terminal': 'terminal', 'la terminal': 'terminal',
    'mercado': 'market', 'market': 'market', 'el mercado': 'market',
    'geo': 'geo', 'geopolitica': 'geo', 'geopolítica': 'geo', 'geopolitics': 'geo', 'monitor mundial': 'geo', 'world monitor': 'geo',
    'espacio': 'space', 'space': 'space', 'el espacio': 'space',
    'escenarios': 'simulation', 'scenarios': 'simulation',
    'cripto': 'crypto', 'crypto': 'crypto',
    'oportunidades': 'insights', 'opportunities': 'insights', 'insights': 'insights', 'las oportunidades': 'insights',
    'explosivas': 'screener', 'breakouts': 'screener', 'spotea explosivas': 'screener', 'spot breakouts': 'screener',
    'guia': 'guia', 'guía': 'guia', 'la guia': 'guia', 'la guía': 'guia', 'guide': 'guia',
    'lienzo': 'canvas', 'canvas': 'canvas', 'lienzo en blanco': 'canvas', 'blank canvas': 'canvas',
    'grafo temporal': 'tkg', 'temporal graph': 'tkg',
    'universo': 'universe', 'universo 3d': 'universe', '3d': 'universe',
    'carteras': 'portfolios', 'portfolios': 'portfolios', 'mis carteras': 'portfolios',
  };

  function _clean(s) { return String(s || '').replace(/[?¿!¡.]+$/g, '').replace(/^[¿¡]+/, '').trim(); }

  // deps: { resolve(q) → {node, score} | null, tryParse(text), parseTrade(text) }
  function classify(text, deps) {
    deps = deps || {};
    var t = String(text || '').trim();
    if (!t) return { kind: 'none' };
    var low = t.toLowerCase();

    // demostración: SOLO pedida de forma exacta
    if (/^(ver\s+)?(la\s+)?(demo|demostraci[óo]n|tour|recorrido(\s+guiado)?|guided\s+(demo|tour))\s*[.!]?$/i.test(t) ||
        /^(hazme|dame|give\s+me)\s+(una\s+demo|un\s+tour|un\s+recorrido|a\s+demo|a\s+tour)\s*[.!]?$/i.test(t)) {
      return { kind: 'demo' };
    }
    // órdenes (la confirmación SIEMPRE ocurre en la Cabina)
    var tc = deps.parseTrade ? deps.parseTrade(t) : null;
    if (tc) return { kind: 'trade', parsed: tc };
    // cuenta del bróker (frase exacta)
    if (/^(mi\s+|la\s+|my\s+)?(cuenta|br[oó]ker|broker|account)\s*$/.test(low) ||
        /^(mi\s+|my\s+)?(portafolio|portfolio|posiciones|positions)(\s+del?\s+(br[oó]ker|broker|alpaca))?\s*$/.test(low)) {
      return { kind: 'account' };
    }
    // gramática KHIPU (NVDA XRAY, COMPARE A B, PORT VAR…) — ejecuta y devuelve {answer, actions}
    if (deps.tryParse) {
      var pending = null;
      try { pending = deps.tryParse(t); } catch (e) { pending = null; }
      if (pending) return { kind: 'command', pending: pending };
    }
    // gráfico con prefijo explícito
    var cm = t.match(/^(gr[aá]fico|gr[aá]fica|chart|tabla|table|plot)\s*:\s*(.+)$/i) ||
             t.match(/^(graf[ií]ca(me)?|dib[uú]ja(me)?|plot|draw\s+(me\s+)?a\s+chart\s+of)\s+(.+)$/i);
    if (cm) return { kind: 'chart', spec: _clean(cm[cm.length - 1]) };

    // «¿qué pasa si cae X?» — el atajo del shock, SOLO si la frase entera es eso
    var sh = t.match(/^¿?\s*(?:qu[eé]\s+pasa(?:r[ií]a)?\s+si\s+(?:cae|colapsa|quiebra|se\s+cae)|what\s+(?:happens\s+)?if)\s+(.{2,40}?)\s*(?:falls|collapses|goes\s+down|cae)?\s*\??$/i);
    if (sh && deps.resolve) {
      var hs = deps.resolve(_clean(sh[1]));
      if (hs && hs.node && hs.score >= 85) return { kind: 'shock', id: hs.node.id };
    }

    // PREGUNTAS → siempre al cerebro (no a pantallas ni gráficos)
    if (isQuestion(t)) return { kind: 'brain' };

    // nombres exactos de pantallas ("abre el mapa", "terminal", "oportunidades")
    var sm = low.replace(/[.!]+$/, '').match(/^(?:abre|abrir|ver|ve\s+a|ir\s+a|mu[eé]strame|show(?:\s+me)?|open|go\s+to)?\s*(?:el\s+|la\s+|los\s+|las\s+|the\s+)?(.+)$/);
    var sk = sm ? sm[1].trim() : '';
    if (SCREENS[sk]) return { kind: 'screen', screen: SCREENS[sk] };
    if (SCREENS[low.replace(/[.!]+$/, '')]) return { kind: 'screen', screen: SCREENS[low.replace(/[.!]+$/, '')] };

    var R = function (q) { return deps.resolve ? deps.resolve(_clean(q)) : null; };
    var ok = function (h, min) { return h && h.node && h.score >= (min || 70); };
    var m;
    // imperativos anclados con empresa reconocida
    if ((m = t.match(/^(?:des[aá]rma(?:me)?|radiograf[ií]a(?:\s+de)?|x-?ray(?:\s+of)?|destripa(?:me)?|break\s*down|analiza(?:me)?|analyze|abre|open)\s+(?:la\s+empresa\s+|a\s+)?(.{2,40})$/i))) {
      var hx = R(m[1]); if (ok(hx)) return { kind: 'xray', id: hx.node.id };
    }
    if ((m = t.match(/^(?:compara(?:r|me)?|compare)\s+(.+?)\s+(?:y|vs\.?|versus|con|contra|and|with)\s+(.+)$/i))) {
      var ha = R(m[1]), hb = R(m[2]);
      if (ok(ha) && ok(hb)) return { kind: 'compare', a: ha.node.id, b: hb.node.id };
    }
    if ((m = t.match(/^(?:simula(?:r|me)?|simulate|run\s+a\s+simulation(?:\s+of)?)\s+(?:que\s+|that\s+|el\s+escenario\s+|the\s+scenario\s+|:\s*)?(.{4,})$/i))) {
      return { kind: 'agentsim', scenario: _clean(m[1]) };
    }
    if ((m = t.match(/^(?:investiga(?:ci[oó]n)?(?:\s+(?:de|sobre|a))?|research)\s+(.{2,40})$/i))) {
      var hr = R(m[1]); if (ok(hr, 85)) return { kind: 'research', id: hr.node.id };
    }
    if ((m = t.match(/^(?:dossier|fundamentales|financieros|financials)\s+(?:de\s+|of\s+)?(.{2,40})$/i))) {
      var hd = R(m[1]); if (ok(hd)) return { kind: 'dossier', id: hd.node.id };
    }
    if ((m = t.match(/^(?:abre\s+)?(?:la\s+)?terminal\s+(?:de|con|of|for)\s+(.{2,30})$/i))) {
      var ht = R(m[1]); if (ok(ht)) return { kind: 'terminal', id: ht.node.id };
    }
    // el texto ES una empresa ("Nvidia", "TSMC") → X-Ray
    if (t.length <= 40 && t.split(/\s+/).length <= 4) {
      var hn = R(t); if (ok(hn, 85)) return { kind: 'xray', id: hn.node.id };
    }
    return { kind: 'brain' };
  }

  /* ══ 2) MEMORIA + LLAMADA AL CEREBRO ═══════════════════════════════════ */
  var history = [];
  try { var raw = W.sessionStorage && W.sessionStorage.getItem(HIST_KEY); if (raw) history = JSON.parse(raw) || []; } catch (e) { history = []; }
  if (!Array.isArray(history)) history = [];

  function saveHistory() {
    try { if (W.sessionStorage) W.sessionStorage.setItem(HIST_KEY, JSON.stringify(history.slice(-MAX_TURNS * 2))); } catch (e) {}
  }
  function remember(role, content) {
    if (!content) return;
    history.push({ role: role === 'user' ? 'user' : 'assistant', content: String(content).slice(0, 1500) });
    if (history.length > MAX_TURNS * 2) history = history.slice(-MAX_TURNS * 2);
    saveHistory();
  }
  function clearHistory() { history = []; saveHistory(); }

  function context() {
    var ctx = {};
    try {
      var sel = (W._liveSelectedNode && W._liveSelectedNode()) || W._selectedNode || null;
      if (sel) ctx.selected_node = String(sel).slice(0, 120);
    } catch (e) {}
    try { if (typeof activeTab !== 'undefined' && activeTab) ctx.tab = String(activeTab); } catch (e) {}   // eslint-disable-line no-undef
    try {
      var pos = (W.MKT && W.MKT.pos) || {}, NB = W.NODE_BY_ID || {}, out = [];
      Object.keys(pos).forEach(function (id) {
        var n = NB[id], p = pos[id];
        if (n && n.mkt && p && +p.sh > 0 && out.length < 30) out.push({ symbol: String(n.mkt), shares: +p.sh });
      });
      if (out.length) ctx.portfolio = { positions: out };
    } catch (e) {}
    return ctx;
  }

  function send(text, opts) {
    opts = opts || {};
    var base = (typeof BASE !== 'undefined' && BASE) ? BASE : (W.BASE || '');   // eslint-disable-line no-undef
    var body = { message: String(text || '').slice(0, 2000), history: history.slice(-MAX_TURNS), lang: lang(), context: context() };
    var ctl = (typeof AbortController !== 'undefined') ? new AbortController() : null;
    var timer = ctl ? setTimeout(function () { try { ctl.abort(); } catch (e) {} }, opts.timeout || 70000) : null;
    return fetch(base + '/api/khipu/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      signal: ctl ? ctl.signal : undefined,
    }).then(function (r) {
      var ct = (r.headers && r.headers.get && r.headers.get('content-type')) || '';
      if (ct.indexOf('application/json') < 0) {
        throw new Error(r.status >= 500 ? L('El servidor se está reiniciando (¿despliegue en curso?). Reintenta en ~1 min.',
          'The server is restarting (deploy in progress?). Retry in ~1 min.') : L('Respuesta inesperada', 'Unexpected response') + ' (HTTP ' + r.status + ')');
      }
      return r.json().then(function (d) {
        if (!r.ok) throw new Error((lang() === 'en' ? d.error_en : d.error) || d.error || ('HTTP ' + r.status));
        remember('user', text);
        remember('assistant', d.answer || '');
        return d;
      });
    }).catch(function (e) {
      if (e && e.name === 'AbortError') throw new Error(L('Khipu tardó demasiado en responder. Reintenta.', 'Khipu took too long to answer. Please retry.'));
      throw e;
    }).then(function (d) { if (timer) clearTimeout(timer); return d; }, function (e) { if (timer) clearTimeout(timer); throw e; });
  }

  /* ══ 3) MARKDOWN LIGERO (escapa HTML ANTES de dar formato) ═══════════════ */
  function inline(s) {
    // s YA viene escapado
    s = s.replace(/`([^`\n]{1,200})`/g, '<code>$1</code>');
    s = s.replace(/\*\*([^*\n]{1,400}?)\*\*/g, '<b>$1</b>');
    s = s.replace(/(^|[\s(])\*([^*\n]{1,200}?)\*(?=[\s).,;:!?]|$)/g, '$1<i>$2</i>');
    s = s.replace(/\bhttps?:\/\/[^\s<>"']{3,300}/g, function (u) {
      var trail = ''; var mm = u.match(/(?:&quot;|&#39;|&gt;|[.,;:!?)])+$/); if (mm) { trail = mm[0]; u = u.slice(0, -trail.length); }
      return '<a href="' + u + '" target="_blank" rel="noopener noreferrer">' + u.replace(/^https?:\/\//, '').slice(0, 60) + '</a>' + trail;
    });
    return s;
  }
  function md(text) {
    var lines = esc(String(text == null ? '' : text).replace(/\r\n?/g, '\n')).split('\n');
    var out = [], list = null, para = [];
    function flushPara() { if (para.length) { out.push('<p>' + para.map(inline).join('<br>') + '</p>'); para = []; } }
    function flushList() { if (list) { out.push('<' + list.tag + '>' + list.items.map(function (x) { return '<li>' + inline(x) + '</li>'; }).join('') + '</' + list.tag + '>'); list = null; } }
    lines.forEach(function (ln) {
      var m;
      if (!ln.trim()) { flushPara(); flushList(); return; }
      if ((m = ln.match(/^\s*[-*•]\s+(.*)$/))) { flushPara(); if (!list || list.tag !== 'ul') { flushList(); list = { tag: 'ul', items: [] }; } list.items.push(m[1]); return; }
      if ((m = ln.match(/^\s*\d{1,2}[.)]\s+(.*)$/))) { flushPara(); if (!list || list.tag !== 'ol') { flushList(); list = { tag: 'ol', items: [] }; } list.items.push(m[1]); return; }
      if ((m = ln.match(/^\s*#{1,4}\s+(.*)$/))) { flushPara(); flushList(); out.push('<div class="kc-h">' + inline(m[1]) + '</div>'); return; }
      flushList(); para.push(ln);
    });
    flushPara(); flushList();
    return out.join('');
  }

  /* ══ 4) HILO (burbujas) ═════════════════════════════════════════════════ */
  var CSS = '' +
    '.kc-thread{display:flex;flex-direction:column;gap:12px;width:100%;max-width:860px;margin:0 auto;padding:4px 2px 8px;box-sizing:border-box}' +
    '.kc-msg{max-width:92%;border-radius:14px;padding:10px 14px;font-size:14px;line-height:1.55;overflow-wrap:anywhere;word-break:break-word}' +
    '.kc-user{align-self:flex-end;background:rgba(0,224,255,.12);border:1px solid rgba(0,224,255,.32);color:#E8EDFB;white-space:pre-wrap}' +
    '.kc-bot{align-self:flex-start;background:rgba(11,18,34,.78);border:1px solid rgba(122,158,255,.2);color:#E8EDFB}' +
    '.kc-bot p{margin:0 0 8px}.kc-bot p:last-child{margin-bottom:0}.kc-bot ul,.kc-bot ol{margin:4px 0 8px;padding-left:20px}.kc-bot li{margin:2px 0}' +
    '.kc-bot code{font-family:"JetBrains Mono",monospace;font-size:12.5px;background:rgba(122,158,255,.12);padding:1px 5px;border-radius:5px}' +
    '.kc-bot a{color:#7ecbff}.kc-h{font-weight:750;margin:6px 0 4px;color:#fff}' +
    '.kc-who{font-size:10px;font-weight:800;letter-spacing:.12em;color:#8e9dff;margin-bottom:4px;text-transform:uppercase}' +
    '.kc-tools{margin-top:8px;font-size:11.5px;color:#8FA0C4}.kc-tools .bad{color:#f6a0b5}' +
    '.kc-src{margin-top:6px;font-size:11px;color:#6F7C99}.kc-src a{color:#8fb7ff}' +
    '.kc-note{margin-top:8px;font-size:11.5px;color:#FFD27A}' +
    '.kc-acts{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}' +
    '.kc-act{font-size:12px;padding:5px 11px;border-radius:999px;cursor:pointer;border:1px solid rgba(0,224,255,.45);background:rgba(0,224,255,.08);color:#9EEBFF;font-family:inherit}' +
    '.kc-act:hover{background:rgba(0,224,255,.2)}' +
    '.kc-think{display:flex;align-items:center;gap:8px;color:#9BA6C4;font-size:13px}' +
    '.kc-dots span{display:inline-block;width:6px;height:6px;border-radius:50%;background:#8e5aff;margin-right:3px;animation:kcDot 1s infinite ease-in-out}' +
    '.kc-dots span:nth-child(2){animation-delay:.15s}.kc-dots span:nth-child(3){animation-delay:.3s}' +
    '@keyframes kcDot{0%,80%,100%{opacity:.25;transform:scale(.8)}40%{opacity:1;transform:scale(1)}}' +
    '.kc-err{color:#FF8FA3}' +
    '@media(max-width:600px){.kc-msg{max-width:100%;font-size:13.5px;padding:9px 12px}}' +
    '@media(prefers-reduced-motion:reduce){.kc-dots span{animation:none}}';

  function ensureStyles() {
    if (!W.document || W.document.getElementById('kc-styles')) return;
    var st = W.document.createElement('style'); st.id = 'kc-styles'; st.textContent = CSS;
    W.document.head.appendChild(st);
  }

  function _scroll(el) {
    try {
      var p = el; while (p && p.parentElement) { p = p.parentElement; if (p.scrollHeight > p.clientHeight + 4 && /(auto|scroll)/.test(getComputedStyle(p).overflowY)) { p.scrollTop = p.scrollHeight; break; } }
      if (el.scrollIntoView) el.scrollIntoView({ block: 'end' });
    } catch (e) {}
  }

  function appendUser(thread, text) {
    ensureStyles();
    var d = W.document.createElement('div'); d.className = 'kc-msg kc-user'; d.textContent = text;
    thread.appendChild(d); _scroll(d); return d;
  }

  var THINK = {
    es: ['Pensando', 'Buscando datos reales', 'Consultando fuentes en vivo', 'Armando la respuesta'],
    en: ['Thinking', 'Looking up real data', 'Checking live sources', 'Putting the answer together'],
  };
  function appendPending(thread) {
    ensureStyles();
    var d = W.document.createElement('div'); d.className = 'kc-msg kc-bot kc-pending';
    d.innerHTML = '<div class="kc-who">Khipu</div><div class="kc-think"><span class="kc-dots"><span></span><span></span><span></span></span><span class="kc-tt"></span></div>';
    thread.appendChild(d);
    var i = 0, tt = d.querySelector('.kc-tt');
    var tick = function () { var arr = THINK[lang()]; tt.textContent = '🔎 ' + arr[Math.min(i, arr.length - 1)] + '…'; i++; };
    tick();
    d._timer = setInterval(tick, 2600);
    _scroll(d); return d;
  }

  var TOOL_LABEL = {
    search_companies: ['Buscar empresas', 'Company search'], get_company: ['Ficha de empresa', 'Company profile'],
    get_supply_chain: ['Cadena de suministro', 'Supply chain'], get_research: ['Investigación de agentes', 'Agent research'],
    get_claim_evidence: ['Evidencia', 'Evidence'], get_ontology_object: ['Ontología', 'Ontology'],
    get_committee_memo: ['Comité de inversión', 'Investment committee'], get_track_record: ['Historial de aciertos', 'Track record'],
    get_risk_report: ['Riesgo de cartera', 'Portfolio risk'], get_option_greeks: ['Griegas de opciones', 'Option greeks'],
    get_world_events: ['Monitor mundial', 'World monitor'], get_news: ['Noticias', 'News'],
    market_movers: ['Movimientos del día', "Today's movers"], rank_companies: ['Ranking del grafo', 'Graph ranking'],
    get_space_summary: ['Espacio', 'Space'], web_search: ['Búsqueda web', 'Web search'],
  };
  function toolLabel(n) { var x = TOOL_LABEL[n]; return x ? x[lang() === 'en' ? 1 : 0] : n; }

  var ACT_LABEL = {
    open_xray: ['🔬 Ver X-Ray', '🔬 Open X-Ray'], navigate: ['🎯 Ver en el mapa', '🎯 Show on map'],
    stress: ['🚨 Simular caída', '🚨 Simulate failure'], dossier: ['📊 Dossier', '📊 Dossier'],
    open_research: ['🧪 Investigación', '🧪 Research'], open_committee: ['🏛 Comité', '🏛 Committee'],
    simulate: ['🔮 Escenario', '🔮 Scenario'], agent_sim: ['🧬 Simular con agentes', '🧬 Agent simulation'],
    chart: ['✦ Gráfico', '✦ Chart'], compare: ['⇄ Comparar', '⇄ Compare'],
    open_risk_report: ['🛡 Riesgo de mi cartera', '🛡 My portfolio risk'], switch_tab: ['📂 Abrir', '📂 Open'],
    open_world: ['🌐 Monitor mundial', '🌐 World monitor'], broker: ['💼 Abrir el bróker', '💼 Open the broker'],
  };
  function actionLabel(a) {
    var x = ACT_LABEL[a.type] || [a.type, a.type];
    var base = x[lang() === 'en' ? 1 : 0];
    if (a.label && a.type !== 'compare') return base + ': ' + a.label;
    if (a.type === 'compare' && a.label) return '⇄ ' + a.label;
    if (a.type === 'switch_tab' || a.type === 'simulate') return base + ': ' + a.arg;
    if (a.type === 'chart' || a.type === 'agent_sim') return base + ': ' + String(a.arg || '').slice(0, 40);
    return base;
  }

  // acciones que cambian el ESCENARIO (se pueden auto-ejecutar sin tapar el chat
  // en la Cabina); las de overlay (investigación, comité, riesgo, dossier, bróker)
  // quedan como botón para que la respuesta siga visible.
  var AUTO = { open_xray: 1, navigate: 1, stress: 1, compare: 1, chart: 1, simulate: 1, agent_sim: 1, switch_tab: 1, open_world: 1 };

  function fillReply(el, d, opts) {
    opts = opts || {};
    if (el._timer) { clearInterval(el._timer); el._timer = null; }
    el.classList.remove('kc-pending');
    d = d || {};
    var h = '<div class="kc-who">Khipu</div><div class="kc-body">' + md(d.answer || L('(sin respuesta)', '(no answer)')) + '</div>';
    if (d.degraded) h += '<div class="kc-note">⚠ ' + esc(L('Respuesta sin IA (solo datos).', 'Answer without AI (data only).')) + '</div>';
    var tu = Array.isArray(d.tools_used) ? d.tools_used : [];
    if (tu.length) {
      h += '<div class="kc-tools">🔎 ' + esc(L('Consultó', 'Checked')) + ': ' + tu.slice(0, 8).map(function (t) {
        return '<span class="' + (t.ok ? '' : 'bad') + '" title="' + esc(t.name + (t.error ? ' — ' + t.error : '')) + '">' +
          esc(toolLabel(t.name) + (t.args_summary ? ' (' + t.args_summary + ')' : '')) + (t.ok ? '' : ' ✕') + '</span>';
      }).join(' · ') + '</div>';
    }
    var src = Array.isArray(d.sources) ? d.sources : [];
    if (src.length) {
      h += '<div class="kc-src">' + esc(L('Fuentes', 'Sources')) + ': ' + src.slice(0, 6).map(function (s) {
        var u = s.url && /^https?:\/\//i.test(s.url) ? (W.safeUrl ? W.safeUrl(s.url) : esc(s.url)) : null;
        return u && u !== '#' ? '<a href="' + u + '" target="_blank" rel="noopener noreferrer">' + esc(s.label) + '</a>' : esc(s.label);
      }).join(' · ') + '</div>';
    }
    el.innerHTML = h;
    var acts = Array.isArray(d.actions) ? d.actions : [];
    if (acts.length) {
      var box = W.document.createElement('div'); box.className = 'kc-acts';
      acts.forEach(function (a) {
        var b = W.document.createElement('button'); b.className = 'kc-act'; b.type = 'button';
        b.textContent = actionLabel(a);
        b.addEventListener('click', function () { (opts.onAction || runAction)(a); });
        box.appendChild(b);
      });
      el.appendChild(box);
    }
    _scroll(el);
    // auto-ejecutar la PRIMERA acción de escenario, DESPUÉS de mostrar el texto
    if (opts.autoRun !== false) {
      var first = acts.filter(function (a) { return AUTO[a.type] && (!opts.autoFilter || opts.autoFilter(a)); })[0];
      if (first) setTimeout(function () { try { (opts.onAction || runAction)(first); } catch (e) {} }, opts.autoDelay || 450);
    }
    return el;
  }

  function fillError(el, msg) {
    if (el._timer) { clearInterval(el._timer); el._timer = null; }
    el.classList.remove('kc-pending');
    el.innerHTML = '<div class="kc-who">Khipu</div><div class="kc-err">⚠ ' + esc(msg || L('No pude procesar eso.', 'I could not process that.')) + '</div>';
    _scroll(el);
  }

  /* ══ 5) ACCIONES ═════════════════════════════════════════════════════════ */
  function runAction(a) {
    if (!a || !a.type) return false;
    var ck = W.BixbyCockpit, inCk = !!(ck && ck.isOpen && ck.isOpen());
    var surf = function (k, x) { try { return W._surface ? W._surface(k, x) : false; } catch (e) { return false; } };
    var NB = W.NODE_BY_ID || {};
    try {
      switch (a.type) {
        case 'open_xray':
          if (inCk) { ck.stage('xray', a.arg); return true; }
          return surf('xray', a.arg) || (W.openXRay && W.openXRay(a.arg));
        case 'navigate':
          if (surf('graph', a.arg)) return true;
          if (W.switchTab) W.switchTab('map');
          setTimeout(function () { if (W.jumpTo) W.jumpTo(a.arg); }, 150); return true;
        case 'stress': return surf('stress', a.arg);
        case 'compare': return surf('compare', a.arg);
        case 'chart':
          if (inCk) { ck.stage('canvas', a.arg); return true; }
          return surf('canvas', a.arg);
        case 'simulate':
          surf('tab', 'simulation');
          setTimeout(function () { try { if (W.nexusCore && W.nexusCore.runPreset) W.nexusCore.runPreset(a.arg); } catch (e) {} }, 600);
          return true;
        case 'agent_sim':
          if (ck && ck.agentSim) { ck.agentSim(a.arg); return true; }
          return false;
        case 'switch_tab':
          if (a.arg === 'portfolios' && W.KhipuPortfolios && W.KhipuPortfolios.open) { W.KhipuPortfolios.open(); return true; }
          return surf('tab', a.arg) || (W.switchTab && W.switchTab(a.arg));
        case 'open_world':
          surf('tab', 'geo');
          if (a.arg && W.KhipuWorld && W.KhipuWorld.focus) setTimeout(function () { try { W.KhipuWorld.focus(a.arg.lat, a.arg.lon); } catch (e) {} }, 900);
          return true;
        case 'dossier': { var n = NB[a.arg]; return surf('dossier', (n && n.mkt) || a.arg) || (W.openFinCard && W.openFinCard((n && n.mkt) || a.arg)); }
        case 'open_research': if (W.KhipuResearch) { W.KhipuResearch.open(a.arg); return true; } return false;
        case 'open_committee': if (W.KhipuCommittee) { W.KhipuCommittee.open(a.arg); return true; } return false;
        case 'open_risk_report': if (W.KhipuRisk) { W.KhipuRisk.open({}); return true; } return false;
        case 'broker':
          if (!ck) return false;
          if (inCk) ck.stage('broker'); else ck.open({ kind: 'broker' });
          return true;
      }
    } catch (e) {}
    return false;
  }

  W.KhipuChat = {
    classify: classify, isQuestion: isQuestion, send: send, md: md, esc: esc,
    appendUser: appendUser, appendPending: appendPending, fillReply: fillReply, fillError: fillError,
    runAction: runAction, actionLabel: actionLabel, remember: remember, context: context,
    history: function () { return history.slice(); }, clear: clearHistory, ensureStyles: ensureStyles,
    AUTO: AUTO,
  };
})(typeof window !== 'undefined' ? window : globalThis);
