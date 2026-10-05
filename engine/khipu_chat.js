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

  // ── Comandos y agentes en el chat (pedido de Fabrizio 2026-10-05) ──────────
  // "/investigar NVDA", "@investigación TSMC", "llama al agente de investigación
  // para AMD" → el equipo de investigación; "/comite NVDA" → comité de esa empresa;
  // "/cartera", "/comite cartera", "@comité mi cartera", "que el comité analice mi
  // cartera" → comité de cartera; "/ayuda" → la lista. Los @analistas
  // (@fundamental, @noticias, @todos…) siguen yendo al cerebro (research/ask_agent).
  function _fold(s) { return String(s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, ''); }
  function _lang() { try { return (window.LANG || localStorage.getItem('eco_lang') || 'es') === 'en'; } catch (e) { return false; } }
  var _CARTERA_RX = /^(?:de\s+|a\s+)?(?:mi|my|la|the)?\s*(?:cartera|portafolio|portfolio|posiciones|positions)$/i;
  function helpText(en) {
    return en ? [
      'Commands you can type here:',
      '• /research <company> — the research team (8 analysts) studies the company. Also: "@research NVDA".',
      '• /committee <company> — the investment committee gives its recommendation.',
      '• /portfolio <question> — the portfolio committee measures YOUR portfolio and answers here (pick which portfolio in the chip). Also "@portfolio".',
      '• @fundamental, @technical, @news, @supply, @geo, @macro, @all + your question — ask an analyst directly.',
      '• Terminal commands: NVDA XRAY · NVDA RESEARCH · COMPARE NVDA AMD · PORT VAR · SHOCK TSMC.',
      '• /help — this list.',
      'Nothing here places orders: buying and selling always asks for your confirmation.'].join('\n') : [
      'Comandos que puedes escribir aquí:',
      '• /investigar <empresa> — el equipo de investigación (8 analistas) estudia la empresa. También: "@investigación NVDA".',
      '• /comite <empresa> — el comité de inversión da su recomendación.',
      '• /cartera <pregunta> — el comité de cartera mide TU cartera y te responde aquí (elige cuál cartera en el chip). También "@cartera".',
      '• @fundamental, @tecnico, @noticias, @cadena, @geopolitico, @macro, @todos + tu pregunta — le preguntas a un analista.',
      '• Comandos de terminal: NVDA XRAY · NVDA RESEARCH · COMPARE NVDA AMD · PORT VAR · SHOCK TSMC.',
      '• /ayuda — esta lista.',
      'Nada de esto da órdenes: comprar y vender siempre pide tu confirmación.'].join('\n');
  }
  function _cmd(answer, fn) {
    return { kind: 'command', pending: Promise.resolve().then(function () { if (fn) { try { fn(); } catch (e) {} } return { answer: answer, actions: [] }; }) };
  }
  // 2026-10-05: el comité de cartera RESPONDE dentro del chat ("/cartera dime si debería reducir…"
  // antes solo abría una pantalla). La pregunta viaja al agente con la cartera elegida en el chip.
  function _pfCommittee(en, question) {
    return { kind: 'agentask', agent: 'portfolio', question: String(question || '').trim() };
  }
  function agentCommand(t, deps) {
    var en = _lang();
    var R = function (q) { return deps.resolve ? deps.resolve(String(q || '').replace(/[?¿!¡.]+$/g, '').trim()) : null; };
    var notFound = function (q) {
      var msg = (window.KhipuResolve && window.KhipuResolve.notFound) ? window.KhipuResolve.notFound(q)
        : (en ? 'I could not find "' + q + '" in the graph.' : 'No encontré «' + q + '» en el grafo.');
      return _cmd(msg);
    };
    var research = function (q) {
      if (!q) return _cmd(en ? 'Which company? E.g. /research NVDA' : '¿Qué empresa? Por ejemplo: /investigar NVDA');
      var h = R(q); return (h && h.node && h.score >= 70) ? { kind: 'research', id: h.node.id } : notFound(q);
    };
    var committee = function (q) {
      if (!q || _CARTERA_RX.test(q.trim())) return _pfCommittee(en);
      var mc = q.match(/^(?:de\s+|a\s+)?(?:mi|my|la|the)?\s*(?:cartera|portafolio|portfolio)\s*[:,]?\s+([\s\S]+)$/i);
      if (mc) return _pfCommittee(en, mc[1]);
      var h = R(q);
      if (!(h && h.node && h.score >= 70)) return notFound(q);
      var id = h.node.id, label = h.node.label || id;
      return _cmd(en ? 'Opening the investment committee for ' + label + '. Nothing executes without your approval.'
                     : 'Abriendo el comité de inversión para ' + label + '. Nada se ejecuta sin tu aprobación.',
        function () { if (window.KhipuCommittee) window.KhipuCommittee.open(id); });
    };
    var m = t.match(/^\/(\S+)\s*([\s\S]*)$/);
    if (m) {
      var c = _fold(m[1]), rest = m[2].trim();
      if (['ayuda', 'help', 'comandos', 'commands', '?'].indexOf(c) >= 0) return _cmd(helpText(en));
      if (['investigar', 'investiga', 'investigacion', 'research', 'investigate'].indexOf(c) >= 0) return research(rest);
      if (['comite', 'committee'].indexOf(c) >= 0) return committee(rest);
      if (['cartera', 'portafolio', 'portfolio', 'micartera'].indexOf(c) >= 0) return _pfCommittee(en, rest);
      return _cmd((en ? 'I do not know the command /' + m[1] + '.\n\n' : 'No conozco el comando /' + m[1] + '.\n\n') + helpText(en));
    }
    var mp = t.match(/^@\s*(?:cartera|portafolio|portfolio|micartera|mi\s+cartera|my\s+portfolio)\b\s*[:,]?\s*([\s\S]*)$/i);
    if (mp) return _pfCommittee(en, mp[1]);
    var f = _fold(t).replace(/[?¿!¡.]+$/g, '').trim();
    // @investigación X · @research X · @investigador X
    if ((m = f.match(/^@\s*(?:investigacion|investigador(?:es)?|research|researcher)\s*[:,]?\s*(?:sobre\s+|de\s+|a\s+|on\s+)?(.*)$/))) return research(m[1]);
    // "llama/llamar/invoca al agente (o equipo) de investigación (para|sobre|de) X"
    if ((m = f.match(/^(?:llama(?:r|le)?|invoca(?:r)?|pide(?:le)?|call|ask)\s+(?:al?|a\s+los|the)?\s*(?:agente|agentes|equipo|team|agent|agents)\s+(?:de\s+)?(?:investigacion|research)\s*(?:para|sobre|de|a|que\s+investigue|on|about|for)?\s*(.*)$/))) return research(m[1]);
    // @comité (mi) cartera · "que el comité analice mi cartera" · "analiza mi cartera con el comité"
    if (/^@\s*(?:comite|committee)\s*[:,]?\s*(?:analiza\s+|analyze\s+|revisa\s+|review\s+)?(?:mi|my)?\s*(?:cartera|portafolio|portfolio)/.test(f) ||
        /^(?:que\s+)?(?:el\s+)?comite\s+(?:analice|revise|evalue|mire)\s+(?:mi|la)\s+(?:cartera|portafolio)/.test(f) ||
        /^(?:analiza|revisa|evalua)\s+(?:mi|la)\s+(?:cartera|portafolio)\s+con\s+el\s+comite/.test(f) ||
        /^(?:have\s+)?the\s+committee\s+(?:analy[sz]e|review)\s+my\s+portfolio/.test(f)) return _pfCommittee(en);
    return null;
  }

  // deps: { resolve(q) → {node, score} | null, tryParse(text), parseTrade(text) }
  function classify(text, deps) {
    deps = deps || {};
    var t = String(text || '').trim();
    if (!t) return { kind: 'none' };
    var low = t.toLowerCase();
    var ag = agentCommand(t, deps);
    if (ag) return ag;

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
  // historial en localStorage con caducidad de 24 h (antes sessionStorage: se perdía al cerrar la pestaña)
  var history = [];
  var HIST_TTL = 24 * 3600e3;
  try {
    var raw = W.localStorage && W.localStorage.getItem(HIST_KEY);
    if (raw) { var saved = JSON.parse(raw) || {}; if (saved && Array.isArray(saved.items) && Date.now() - (saved.ts || 0) < HIST_TTL) history = saved.items; }
  } catch (e) { history = []; }
  if (!Array.isArray(history)) history = [];

  function saveHistory() {
    try { if (W.localStorage) W.localStorage.setItem(HIST_KEY, JSON.stringify({ ts: Date.now(), items: history.slice(-MAX_TURNS * 2) })); } catch (e) {}
  }
  function remember(role, content) {
    if (!content) return;
    history.push({ role: role === 'user' ? 'user' : 'assistant', content: String(content).slice(0, 1500) });
    if (history.length > MAX_TURNS * 2) history = history.slice(-MAX_TURNS * 2);
    saveHistory();
  }
  // empresas vistas hace poco (X-Ray, simulación, comparar…): la Cabina las anota al abrir cada escena
  var recent = [];
  function noteEntity(id) {
    if (!id) return;
    id = String(id);
    recent = [id].concat(recent.filter(function (x) { return x !== id; })).slice(0, 5);
  }
  function clearHistory() { history = []; saveHistory(); }

  function context() {
    var ctx = {};
    try {
      var sel = (W._liveSelectedNode && W._liveSelectedNode()) || W._selectedNode || null;
      if (sel) ctx.selected_node = String(sel).slice(0, 120);
    } catch (e) {}
    try { if (typeof activeTab !== 'undefined' && activeTab) ctx.tab = String(activeTab); } catch (e) {}   // eslint-disable-line no-undef
    // qué hay EN PANTALLA (escritorio Khipu) y qué empresas se vieron hace poco → "ella / su / este"
    try {
      if (W.KhipuDesk && W.KhipuDesk.active && W.KhipuDesk.active()) {
        var ws = W.KhipuDesk.list().filter(function (w) { return !w.min; }).slice(0, 8);
        var titles = [];
        ws.forEach(function (w) { var el = W.document.querySelector('.kd-win[data-id="' + w.id + '"] .kd-name'); if (el && el.textContent) titles.push(el.textContent.slice(0, 60)); });
        if (titles.length) ctx.open_windows = titles;
      }
    } catch (e) {}
    if (recent.length) ctx.recent_entities = recent.slice();
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
        if (!d.degraded) remember('assistant', d.answer || '');   // una respuesta sin IA no es memoria útil
        return d;
      });
    }).catch(function (e) {
      if (e && e.name === 'AbortError') throw new Error(L('Khipu tardó demasiado en responder. Reintenta.', 'Khipu took too long to answer. Please retry.'));
      throw e;
    }).then(function (d) { if (timer) clearTimeout(timer); return d; }, function (e) { if (timer) clearTimeout(timer); throw e; });
  }

  /* ══ 2b) AGENTES CON CHIP: el comité de cartera dentro del chat ══════════
     La cartera se elige en el chip del campo de texto (engine/pickers.js →
     localStorage 'kh_chat_pf_src'); por defecto la primera disponible. */
  var PF_KEY = 'kh_chat_pf_src';
  function pfSources() {
    try { return (W.KhipuPortfolioCommittee && W.KhipuPortfolioCommittee._sources) ? W.KhipuPortfolioCommittee._sources() : []; } catch (e) { return []; }
  }
  function pfSelected() {
    var srcs = pfSources(), k = null;
    try { k = W.localStorage.getItem(PF_KEY); } catch (e) {}
    var hit = srcs.filter(function (x) { return x.key === k; })[0];
    if (!hit) hit = srcs.filter(function (x) { return x.key !== 'broker' && !/· (vacía|empty)$/.test(x.label); })[0] || srcs[0] || null;
    return hit;
  }
  function pfSelect(key) { try { W.localStorage.setItem(PF_KEY, key); } catch (e) {} }
  function _owner() {
    var k = null; try { k = W.localStorage.getItem('kh_owner_key'); } catch (e) {}
    return k && k.length >= 16 ? k : '';
  }
  function agentInfo(route) {
    if (route && route.agent === 'portfolio') {
      var src = pfSelected();
      return { name: L('Comité de cartera', 'Portfolio committee'), emoji: '💼', seat: 'portfolio',
        label: src ? String(src.label).replace(/^[^\wÀ-ÿ]+\s*/, '').replace(/\s·\s[^·]*$/, '') : L('sin cartera', 'no portfolio') };
    }
    return null;
  }
  function askAgent(route) {
    var base = (typeof BASE !== 'undefined' && BASE) ? BASE : (W.BASE || '');   // eslint-disable-line no-undef
    var src = pfSelected();
    var PC = W.KhipuPortfolioCommittee;
    if (!src || !PC || !PC._positionsFor) {
      return Promise.resolve({ agent: agentInfo(route), degraded: true, answer: L(
        'No tienes posiciones en Mercado ni carteras simuladas todavía. Crea una en Mercado → Carteras (o pídele una al 🤖 Asistente) y vuelve a preguntarme.',
        'You have no positions in Market nor simulated portfolios yet. Create one in Market → Portfolios (or ask the 🤖 Assistant) and ask me again.') });
    }
    var label = String(src.label).replace(/^[^\wÀ-ÿ]+\s*/, '').replace(/\s·\s[^·]*$/, '');
    var prof = null; try { prof = W.KhipuProfile && W.KhipuProfile.get ? W.KhipuProfile.get() : null; } catch (e) {}
    return Promise.resolve(PC._positionsFor(src.key)).then(function (p) {
      p = p || {};
      if (!(p.positions || []).length) {
        return { agent: agentInfo(route), degraded: true, answer: L('La cartera «' + label + '» está vacía: añádele empresas en Mercado → Carteras.',
          'The portfolio «' + label + '» is empty: add companies in Market → Portfolios.') };
      }
      var ctl = (typeof AbortController !== 'undefined') ? new AbortController() : null;
      var timer = ctl ? setTimeout(function () { try { ctl.abort(); } catch (e) {} }, 110000) : null;
      var actor = null; try { actor = W.localStorage.getItem('khipu_actor'); } catch (e) {}
      return fetch(base + '/api/committee/portfolio/ask', {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Khipu-Owner': _owner() },
        signal: ctl ? ctl.signal : undefined,
        body: JSON.stringify({ question: route.question || '', positions: p.positions, cash_usd: p.cash || 0, profile: prof || {},
          lang: lang(), source_label: label, history: history.slice(-MAX_TURNS), actor: actor || 'usuario' }),
      }).then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (d) {
          if (timer) clearTimeout(timer);
          if (!r.ok && !d.answer) throw new Error((lang() === 'en' ? d.error_en : d.error) || d.error || ('HTTP ' + r.status));
          d.agent = d.agent || agentInfo(route);
          if (!prof) d.profile_missing = true;
          remember('user', '/cartera ' + (route.question || ''));
          if (d.answer && !d.degraded) remember('assistant', d.answer);
          return d;
        });
      }, function (e) {
        if (timer) clearTimeout(timer);
        if (e && e.name === 'AbortError') throw new Error(L('El comité tardó demasiado. Reintenta.', 'The committee took too long. Please retry.'));
        throw e;
      });
    });
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
    '.kc-agent{display:inline-flex;align-items:center;gap:6px;text-transform:none;letter-spacing:0;font-size:12px;color:#C7D0EA}' +
    '.kc-meta{font-size:10.5px;color:#5E6884;margin-top:6px}' +
    '.kc-chart{margin-top:10px;max-width:760px}.kc-chart .cv-card{margin:0}.kc-chart .cv-card-close{display:none}' +
    '.kc-chart-open{margin-top:8px}' +
    '.kc-retry{margin-left:8px;border:1px solid rgba(122,158,255,.3);background:transparent;color:#C7D0EA;border-radius:7px;padding:2px 9px;cursor:pointer;font-size:11.5px;font-family:inherit}' +
    '.kc-retry:hover{border-color:#00E0FF;color:#00E0FF}' +
    '.kc-agent-av{display:inline-flex;width:22px;height:22px;border-radius:50%;overflow:hidden;border:1px solid rgba(122,158,255,.35)}' +
    '.kc-agent-av svg{width:100%;height:100%}.kc-agent-ent{color:#8E9AB8;font-weight:500}' +
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
    '.kc-uchip{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:700;color:#9EEBFF;background:rgba(0,224,255,.1);border:1px solid rgba(0,224,255,.35);border-radius:999px;padding:1px 9px 1px 4px;margin:0 6px 4px 0;white-space:nowrap}' +
    '.kc-uchip i{font-style:normal;display:inline-flex;width:18px;height:18px;border-radius:50%;align-items:center;justify-content:center;background:rgba(0,224,255,.18);font-size:11px}' +
    '.kc-pf{margin-top:10px;border:1px solid rgba(122,158,255,.2);border-radius:12px;padding:10px 12px;background:rgba(6,10,20,.5)}' +
    '.kc-pf-top{display:flex;gap:12px;align-items:center}.kc-pf-sc{width:46px;height:46px;flex:0 0 46px;border-radius:50%;border:4px solid;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:15px}' +
    '.kc-pf-v{font-weight:700;font-size:13px}.kc-pf-m{font-size:11.5px;color:#8E9AB8;margin-top:2px}' +
    '.kc-pf-a{display:flex;gap:8px;align-items:baseline;font-size:12.5px;margin-top:6px}.kc-pf-a b{white-space:nowrap}' +
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

  function appendUser(thread, text, agent) {
    ensureStyles();
    var d = W.document.createElement('div'); d.className = 'kc-msg kc-user';
    if (agent && agent.name) {
      var chip = W.document.createElement('span'); chip.className = 'kc-uchip';
      chip.innerHTML = '<i>' + esc(agent.emoji || '🤖') + '</i>' + esc(agent.name + (agent.label ? ' · ' + agent.label : ''));
      d.appendChild(chip);
      text = String(text || '').replace(/^\s*(?:\/\S+|@\S+)\s*/, '');
      if (text) { d.appendChild(W.document.createElement('br')); }
    }
    d.appendChild(W.document.createTextNode(text));
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
    open_pf_committee: ['💼 Ver el análisis completo', '💼 See the full analysis'],
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
    // un ANALISTA respondió en persona (@fundamental, @noticias, @todos…): su avatar y su nombre
    var who = 'Khipu';
    if (d.agent && d.agent.name) {
      var av = '';
      try { av = (W.KhipuCommittee && W.KhipuCommittee.avatar && d.agent.seat !== 'all') ? W.KhipuCommittee.avatar(d.agent.seat, d.agent.emoji, true) : ''; } catch (e) { av = ''; }
      who = '<span class="kc-agent">' + (av ? '<span class="kc-agent-av">' + av + '</span>' : esc(d.agent.emoji || '🤖') + ' ') + esc(d.agent.name) +
        (d.agent.label ? '<span class="kc-agent-ent"> · ' + esc(d.agent.label) + '</span>' : '') + '</span>';
    }
    var h = '<div class="kc-who">' + who + '</div><div class="kc-body">' + md(d.answer || L('(sin respuesta)', '(no answer)')) + '</div>';
    if (d.portfolio) h += pfCardHTML(d.portfolio);
    if (d.profile_missing) h += '<div class="kc-note">🧭 ' + esc(L('Usé el perfil «moderado» porque aún no definiste el tuyo (Comité → 💼 Mi cartera → 4 preguntas).', 'I used the "moderate" profile because you have not set yours yet (Committee → 💼 My portfolio → 4 questions).')) + '</div>';
    if (d.degraded) {
      var why = (lang() === 'en' ? d.ai_detail_en : d.ai_detail_es) || d.ai_detail || '';
      h += '<div class="kc-note">⚠ ' + esc(L('Respuesta sin IA (solo datos).', 'Answer without AI (data only).')) +
        (why ? ' <span style="opacity:.85">' + esc(why) + '</span>' : '') +
        (opts.retry ? ' <button type="button" class="kc-retry">↻ ' + esc(L('Reintentar', 'Retry')) + '</button>' : '') + '</div>';
    } else if (d.ai && (d.model || d.elapsed_ms)) {
      var mdl = String(d.model || '').replace(/^gemini:/, 'Gemini ').replace(/^claude-/, 'Claude ').replace(/^nvidia:/, 'NVIDIA ');
      h += '<div class="kc-meta">' + esc(mdl) + (d.steps ? ' · ' + d.steps + ' ' + esc(d.steps === 1 ? L('consulta', 'query') : L('consultas', 'queries')) : '') +
        (d.elapsed_ms ? ' · ' + (d.elapsed_ms / 1000).toFixed(0) + ' s' : '') + '</div>';
    }
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
    // FUSIÓN Khipu + Canvas: un gráfico pedido se dibuja AQUÍ, dentro de la respuesta
    // (y se puede abrir en ventana); así no hay que saltar a otra pantalla
    var inlineChart = acts.filter(function (a) { return a.type === 'chart' && typeof a.arg === 'string'; })[0];
    if (inlineChart && opts.inlineChart !== false && W.BixbyCockpit && W.BixbyCockpit.canvasInto) {
      var host = W.document.createElement('div'); host.className = 'kc-chart';
      el.appendChild(host);
      try { W.BixbyCockpit.canvasInto(host, inlineChart.arg); } catch (e) {}
      var ow = W.document.createElement('button'); ow.type = 'button'; ow.className = 'kc-act kc-chart-open';
      ow.textContent = '🪟 ' + L('Abrir en ventana', 'Open in a window');
      ow.addEventListener('click', function () { (opts.onAction || runAction)(inlineChart); });
      host.appendChild(ow);
      acts = acts.filter(function (a) { return a !== inlineChart; });
    }
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

  function pfCardHTML(c) {
    var col = c.tone === 'good' ? '#2BE38B' : c.tone === 'warn' ? '#FFB300' : '#FF4D6A';
    var money = function (v) { v = Number(v); return isFinite(v) ? '$' + Math.round(v).toLocaleString('en-US') : '—'; };
    var KIND = { sell: ['➖', L('Salir de', 'Exit')], reduce: ['➖', L('Reducir', 'Trim')], add: ['➕', L('Aumentar', 'Add')], buy_new: ['🆕', L('Añadir', 'Add new')] };
    var cv = c.coverage || {};
    var h = '<div class="kc-pf"><div class="kc-pf-top"><div class="kc-pf-sc" style="border-color:' + col + ';color:' + col + '">' + esc(c.score) + '</div><div>' +
      '<div class="kc-pf-v">' + esc(c.verdict || '') + '</div><div class="kc-pf-m">' + esc(L('Salud vs tu perfil ', 'Health vs your profile ') + (c.profile || '') + ' · ' + money(c.value_usd) +
      (c.vol_ann_pct != null ? ' · ' + L('se mueve ', 'moves ') + Math.round(c.vol_ann_pct) + L(' % al año', '% a year') : '') +
      (cv.requested ? ' · ' + L('analizadas ', 'analyzed ') + cv.analyzed + '/' + cv.requested : '')) + '</div></div></div>';
    (c.actions || []).forEach(function (a) {
      var k = KIND[a.kind] || ['•', a.kind];
      h += '<div class="kc-pf-a"><b>' + esc(k[0] + ' ' + k[1] + ' ' + (a.label || '')) + '</b><span style="color:#8E9AB8">' +
        esc(Math.round(a.from_pct) + '% → ' + Math.round(a.to_pct) + '% · ' + (lang() === 'en' ? a.why_en : a.why_es)) + '</span></div>';
    });
    if ((c.excluded || []).length) h += '<div class="kc-pf-m" style="color:#FFB300;margin-top:6px">⚠ ' + esc(L('Sin analizar: ', 'Not analyzed: ') + c.excluded.join(', ')) + '</div>';
    return h + '<div class="kc-pf-m" style="margin-top:6px">🤖 ' + esc(L('Consejo educativo de IA; nada se ejecuta sin tu confirmación.', 'Educational AI advice; nothing runs without your confirmation.')) + '</div></div>';
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
        case 'open_pf_committee': if (W.KhipuCommittee) { W.KhipuCommittee.openTab('portfolio'); return true; } return false;
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
    noteEntity: noteEntity,
    classify: classify, isQuestion: isQuestion, send: send, md: md, esc: esc,
    appendUser: appendUser, appendPending: appendPending, fillReply: fillReply, fillError: fillError,
    runAction: runAction, actionLabel: actionLabel, remember: remember, context: context,
    history: function () { return history.slice(); }, clear: clearHistory, ensureStyles: ensureStyles,
    AUTO: AUTO, askAgent: askAgent, agentInfo: agentInfo, pfSources: pfSources, pfSelected: pfSelected, pfSelect: pfSelect,
  };
})(typeof window !== 'undefined' ? window : globalThis);
