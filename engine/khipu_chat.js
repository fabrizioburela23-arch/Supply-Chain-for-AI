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

   KHIPUS OS (2026-10-06, docs/KHIPUS_OS.md §3.2/§3.5):
   · Burbujas con los tokens --os-* (claro/oscuro); Khipu habla con su mascota.
   · Pensando: fila de mascotas + "Analista, Cadena y Comité están investigando…" —
     primero predictAgents(texto), luego el progreso REAL (req_id en el pedido +
     GET /api/khipu/chat/progress/<req_id> cada 0,7 s; servidor viejo → se calla).
   · Respuesta: tarjeta con lo que aportó cada agente (agents_used; sin él, tools_used
     con TOOL_AGENT, el mismo mapa del servidor) y fuentes con su hora (as_of).
   · Ventanas automáticas: planWindows() → glance / supplychain / conviction en los
     flancos (solo si BixbyCockpit.isCentered() y la ventana está registrada).
   · El contexto lleva mode (Simple/Pro) y agents_enabled (KhipuAgentPrefs).

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
      '• /portfolio <question> — ask anything about YOUR portfolio (pick which in the chip). Add an analyst (@geo, @fundamental…) to have them answer.',
      '• /committee my portfolio — the full committee gives its verdict on your portfolio.',
      '• @fundamental, @technical, @news, @supply, @geo, @macro, @all + your question — ask an analyst directly.',
      '• Terminal commands: NVDA XRAY · NVDA RESEARCH · COMPARE NVDA AMD · PORT VAR · SHOCK TSMC.',
      '• /help — this list.',
      'Nothing here places orders: buying and selling always asks for your confirmation.'].join('\n') : [
      'Comandos que puedes escribir aquí:',
      '• /investigar <empresa> — el equipo de investigación (8 analistas) estudia la empresa. También: "@investigación NVDA".',
      '• /comite <empresa> — el comité de inversión da su recomendación.',
      '• /cartera <pregunta> — pregúntale lo que quieras sobre TU cartera (elige cuál en el chip). Suma un analista (@geo, @fundamental…) para que responda él.',
      '• /comite mi cartera — el comité completo da su veredicto sobre tu cartera.',
      '• @fundamental, @tecnico, @noticias, @cadena, @geopolitico, @macro, @todos + tu pregunta — le preguntas a un analista.',
      '• Comandos de terminal: NVDA XRAY · NVDA RESEARCH · COMPARE NVDA AMD · PORT VAR · SHOCK TSMC.',
      '• /ayuda — esta lista.',
      'Nada de esto da órdenes: comprar y vender siempre pide tu confirmación.'].join('\n');
  }
  function _cmdActs(answer, actions) {
    return { kind: 'command', pending: Promise.resolve({ answer: answer, actions: actions }) };
  }
  function _cmd(answer, fn) {
    return { kind: 'command', pending: Promise.resolve().then(function () { if (fn) { try { fn(); } catch (e) {} } return { answer: answer, actions: [] }; }) };
  }
  // 2026-10-05: el comité de cartera RESPONDE dentro del chat ("/cartera dime si debería reducir…"
  // antes solo abría una pantalla). La pregunta viaja al agente con la cartera elegida en el chip.
  // analistas del comité: token → puesto (research/ask_agent.SEAT_WORDS) + nombre/ícono (research/deliberation.AGENT_NAMES)
  // Khipus OS (2026-10-06): las mascotas también son menciones — @analista = fundamental, @radar = noticias
  var SEAT_OF = { fundamental: 'fundamental', fundamentales: 'fundamental', tecnico: 'technical', technical: 'technical',
    noticias: 'news', news: 'news', cadena: 'supply_chain', supply: 'supply_chain', geopolitico: 'geopolitical', geo: 'geopolitical',
    geopolitical: 'geopolitical', macro: 'macro', analista: 'fundamental', analyst: 'fundamental', radar: 'news' };
  var SEAT_NAME = { fundamental: ['📊', 'Analista fundamental', 'Fundamental analyst'], technical: ['📈', 'Analista técnico', 'Technical analyst'],
    news: ['📰', 'Analista de noticias', 'News analyst'], supply_chain: ['🔗', 'Analista de cadena de suministro', 'Supply-chain analyst'],
    geopolitical: ['🗺️', 'Analista geopolítico', 'Geopolitical analyst'], macro: ['🌐', 'Analista macro', 'Macro analyst'] };
  // 2026-10-05 (feedback): la cartera es el CONTEXTO de la pregunta; quién responde es otra cosa.
  //   seat null        → Khipu responde SOLO tu pregunta con los datos de tu cartera (sin veredicto)
  //   seat <analista>  → ese analista, desde su especialidad
  //   seat 'committee' → el comité completo con su tarjeta (solo si lo pides: /comite …)
  function _pfCommittee(en, question, seat) {
    var q = String(question || '').trim(), sm = q.match(/^@\s*([^\s:,]+)\s*[:,]?\s*([\s\S]*)$/);
    if (!seat && sm && (SEAT_OF[_fold(sm[1])] || /^(comite|committee)$/.test(_fold(sm[1])))) {
      seat = SEAT_OF[_fold(sm[1])] || 'committee'; q = sm[2].trim();
    }
    return { kind: 'agentask', agent: 'portfolio', question: q, seat: seat || null };
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
      if (!q || _CARTERA_RX.test(q.trim())) return _pfCommittee(en, '', 'committee');
      var mc = q.match(/^(?:de\s+|a\s+)?(?:mi|my|la|the)?\s*(?:cartera|portafolio|portfolio)\s*[:,]?\s+([\s\S]+)$/i);
      if (mc) return _pfCommittee(en, mc[1], 'committee');
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
    // "@geopolitico ¿qué riesgos tiene mi cartera?" → ese analista, sobre TU cartera (no todo el comité)
    var ma = t.match(/^@\s*([^\s:,]+)\s*[:,]?\s*([\s\S]*)$/);
    if (ma && SEAT_OF[_fold(ma[1])] && /\b(mi|mis|my)\s+(cartera|portafolio|portfolio|posiciones|positions|inversiones|holdings)\b/i.test(ma[2]))
      return _pfCommittee(en, ma[2], SEAT_OF[_fold(ma[1])]);
    var f = _fold(t).replace(/[?¿!¡.]+$/g, '').trim();
    // @investigación X · @research X · @investigador X
    if ((m = f.match(/^@\s*(?:investigacion|investigador(?:es)?|research|researcher)\s*[:,]?\s*(?:sobre\s+|de\s+|a\s+|on\s+)?(.*)$/))) return research(m[1]);
    // "llama/llamar/invoca al agente (o equipo) de investigación (para|sobre|de) X"
    if ((m = f.match(/^(?:llama(?:r|le)?|invoca(?:r)?|pide(?:le)?|call|ask)\s+(?:al?|a\s+los|the)?\s*(?:agente|agentes|equipo|team|agent|agents)\s+(?:de\s+)?(?:investigacion|research)\s*(?:para|sobre|de|a|que\s+investigue|on|about|for)?\s*(.*)$/))) return research(m[1]);
    // @comité (mi) cartera · "que el comité analice mi cartera" · "analiza mi cartera con el comité"
    if (/^@\s*(?:comite|committee)\s*[:,]?\s*(?:analiza\s+|analyze\s+|revisa\s+|review\s+)?(?:mi|my)?\s*(?:cartera|portafolio|portfolio)/.test(f) ||
        /^(?:que\s+)?(?:el\s+)?comite\s+(?:analice|revise|evalue|mire)\s+(?:mi|la)\s+(?:cartera|portafolio)/.test(f) ||
        /^(?:analiza|revisa|evalua)\s+(?:mi|la)\s+(?:cartera|portafolio)\s+con\s+el\s+comite/.test(f) ||
        /^(?:have\s+)?the\s+committee\s+(?:analy[sz]e|review)\s+my\s+portfolio/.test(f)) return _pfCommittee(en, '', 'committee');
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
    // "abre mi cuenta" (2026-10-05): antes abría SIEMPRE el bróker (Alpaca, con un solo ETF) y nunca ofrecía
    // tus carteras simuladas. Ahora, si tienes carteras, Khipu pregunta cuál abrir; "mi bróker" va directo.
    var accRx = /^(?:abre(?:me)?\s+|abrir\s+|ver\s+|mu[eé]strame\s+|open\s+|show(?:\s+me)?\s+)?(mi\s+|mis\s+|la\s+|my\s+)?(cuenta|cuentas|br[oó]ker|broker|account|accounts|portafolio|portfolio|posiciones|positions)(\s+del?\s+(br[oó]ker|broker|alpaca))?\s*[?.!]*$/;
    var am = low.match(accRx);
    if (am) {
      var brokerOnly = /br[oó]ker|broker|alpaca/.test(low);
      var pfs = brokerOnly ? [] : pfSources().filter(function (x) { return x.key.indexOf('pf:') === 0 || x.key === 'market'; });
      if (!pfs.length) return { kind: 'account' };
      var en2 = _lang();
      var acts = [{ type: 'broker' }].concat(pfs.map(function (x) {
        return x.key === 'market' ? { type: 'switch_tab', arg: 'market', label: en2 ? 'My Market positions' : 'Mis posiciones de Mercado' }
          : { type: 'open_portfolio', arg: x.key.slice(3), label: String(x.label).replace(/^[^\wÀ-ÿ]+\s*/, '') };
      }));
      return _cmdActs(en2 ? 'Which one do you want to open? You have your broker account (Alpaca — real or paper money, the one with your actual orders) and ' + pfs.length + ' simulated portfolio(s):'
                          : '¿Cuál quieres abrir? Tienes tu cuenta del bróker (Alpaca — la de tus órdenes reales o de papel) y ' + pfs.length + ' cartera(s) simulada(s):', acts);
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

  /* ══ 1b) AGENTES (Khipus OS, 2026-10-06 — docs/KHIPUS_OS.md §3.2/§3.5) ══════
     Seis mascotas: khipu (te responde), analista, radar, cadena, tecnico, comite.
     · TOOL_AGENT: herramienta del cerebro → mascota. EL MISMO mapa vive en el servidor
       (core/khipu_chat.py TOOL_AGENT/SEAT_AGENT) y el de puesto → mascota en engine/mascot.js:
       cambiar los tres juntos.
     · predictAgents(texto): quién VA a investigar (predicción por intención, se reemplaza
       en vivo por el progreso real del servidor y, al final, por agents_used).
     · planWindows(respuesta, pregunta, prefs, centrado): qué ventanas nativas abrir solas. */
  var AGENT_ORDER = ['khipu', 'analista', 'radar', 'cadena', 'tecnico', 'comite'];
  var AGENT_NAME = { khipu: ['Khipu', 'Khipu'], analista: ['Analista', 'Analyst'], radar: ['Radar', 'Radar'],
    cadena: ['Cadena', 'Chain'], tecnico: ['Técnico', 'Technical'], comite: ['Comité', 'Committee'] };
  // respaldo visual si engine/mascot.js no cargó (mismos tonos que las mascotas)
  var AGENT_TINT = { khipu: ['#f07fa0', '#7a4ce8', '#ff8746'], analista: ['#7d8be6', '#4054cf', '#6b9ff4'], radar: ['#f78189', '#e63e52', '#f6808a'],
    cadena: ['#4cb1ab', '#1b9386', '#83cd70'], tecnico: ['#f7cc63', '#e6a117', '#f5c54a'], comite: ['#bc78e5', '#7a3fe0', '#d88ae6'] };
  var TOOL_AGENT = {
    get_company: 'analista', search_companies: 'analista', get_research: 'analista', get_claim_evidence: 'analista',
    get_supply_chain: 'cadena', rank_companies: 'cadena',
    get_news: 'radar', get_world_events: 'radar', web_search: 'radar', scenario_exposure: 'radar',
    market_movers: 'tecnico', get_option_greeks: 'tecnico', get_risk_report: 'tecnico',
    get_committee_memo: 'comite', get_conclusions_board: 'comite', get_track_record: 'comite',
  };
  var SEAT_AGENT = {};
  [['khipu', ['khipu', 'brain']],
   ['analista', ['fundamental', 'fundamentals', 'macro', 'valuation']],
   ['radar', ['news', 'sentiment', 'geopolitical', 'geo', 'events', 'crypto']],
   ['cadena', ['supply_chain', 'chain', 'supply']],
   ['tecnico', ['technical', 'momentum', 'risk', 'risk_observation', 'risk_officer', 'market']],
   ['comite', ['committee', 'chair', 'portfolio', 'president', 'quant', 'mandate', 'all']]].forEach(function (p) {
    p[1].forEach(function (s) { SEAT_AGENT[s] = p[0]; });
  });
  // palabras (sin acentos) de una mención → mascota ("@noticias", "@geo", "@todos"…)
  var MENTION_AGENT = { fundamental: 'analista', fundamentales: 'analista', analista: 'analista', analyst: 'analista', macro: 'analista',
    financiero: 'analista', investigacion: 'analista', research: 'analista',
    noticias: 'radar', news: 'radar', radar: 'radar', geo: 'radar', geopolitico: 'radar', geopolitical: 'radar', cripto: 'radar', crypto: 'radar',
    cadena: 'cadena', supply: 'cadena', supply_chain: 'cadena', suministro: 'cadena', proveedores: 'cadena', chain: 'cadena',
    tecnico: 'tecnico', technical: 'tecnico', grafico: 'tecnico',
    comite: 'comite', committee: 'comite', todos: 'comite', all: 'comite', analistas: 'comite' };

  function agentName(id) {
    try { if (W.KhipuMascot && W.KhipuMascot.name && AGENT_NAME[id]) return W.KhipuMascot.name(id); } catch (e) {}
    var n = AGENT_NAME[id]; return n ? n[lang() === 'en' ? 1 : 0] : String(id || '');
  }
  // herramienta (+ args o args_summary) → mascota. ask_agent → según el puesto (por defecto, Analista)
  function toolAgent(name, args) {
    if (name === 'ask_agent') {
      var seat = '';
      if (args && typeof args === 'object') seat = args.seat || '';
      else seat = String(args || '').split(/[,\s]+/)[0];
      seat = _fold(seat).trim();
      return SEAT_AGENT[seat] || MENTION_AGENT[seat] || 'analista';
    }
    return TOOL_AGENT[name] || 'khipu';
  }
  // ids de los agentes que aportaron a una respuesta (agents_used del servidor o, si falta, tools_used)
  function agentsOf(d) {
    d = d || {};
    var out = [];
    if (Array.isArray(d.agents_used) && d.agents_used.length) {
      d.agents_used.forEach(function (a) { var id = a && (a.agent || a.id); if (id && AGENT_NAME[id] && out.indexOf(id) < 0) out.push(id); });
      return out;
    }
    (Array.isArray(d.tools_used) ? d.tools_used : []).forEach(function (t) {
      var id = toolAgent(t && t.name, t && t.args_summary);
      if (out.indexOf(id) < 0) out.push(id);
    });
    return AGENT_ORDER.filter(function (id) { return out.indexOf(id) >= 0; });
  }

  // ── ¿el texto nombra una empresa del grafo? (índice exacto, sin fuzzy: barato y sin falsos positivos)
  // Palabras comunes que también son nombres de empresas: solo cuentan si vienen con Mayúscula inicial.
  var NAME_STOP = { meta: 1, vale: 1, disco: 1, canon: 1, shell: 1, ice: 1, glean: 1, cohere: 1, bis: 1, ups: 1, mol: 1, toto: 1, hoya: 1,
    terna: 1, rumo: 1, data: 1, apple: 1, tesla: 1, micron: 1, target: 1, block: 1, snap: 1, global: 1, general: 1, first: 1, nuro: 1, sify: 1 };
  // siglas que NO son empresas aunque coincidan con un ticker (HBM = Hudbay, LNG = Cheniere…)
  var TICKER_STOP = { AI: 1, IA: 1, ON: 1, IT: 1, HBM: 1, GPU: 1, CPU: 1, TPU: 1, ETF: 1, IPO: 1, CEO: 1, CFO: 1, USA: 1, EEUU: 1, EE: 1, UU: 1,
    PIB: 1, GDP: 1, FED: 1, VAR: 1, API: 1, EV: 1, US: 1, UK: 1, EU: 1, UE: 1, OK: 1, TV: 1, PC: 1, SO: 1, BE: 1, LNG: 1, NET: 1, FIX: 1,
    GEN: 1, MOD: 1, FLY: 1, ET: 1, DE: 1, LA: 1, EL: 1, AL: 1, NO: 1, SI: 1, YA: 1, MI: 1, TU: 1, ES: 1, Y: 1, O: 1, A: 1, S: 1, Q: 1, C: 1, D: 1, J: 1 };
  var _cIdx = null, _cIdxN = -1;
  function _companyIndex() {
    var NB = W.NODE_BY_ID; if (!NB) return null;
    var keys = Object.keys(NB);
    if (_cIdx && _cIdxN === keys.length) return _cIdx;
    var names = {}, tickers = {};
    var addName = function (s, id) { var k = _fold(s).replace(/[^a-z0-9&.\- ]+/g, ' ').replace(/\s+/g, ' ').trim(); if (k.length >= 3 && !names[k]) names[k] = id; };
    keys.forEach(function (k) {
      var n = NB[k]; if (!n || n.id !== k) return;               // solo canónicos (NODE_BY_ID[alias] → canónico)
      var lab = String(n.label || '');
      addName(lab, n.id);
      var p = lab.indexOf('('); if (p > 0) addName(lab.slice(0, p), n.id);
      if (n.mkt) { var t = String(n.mkt).split(/[\s·(]/)[0].toUpperCase(); if (t.length >= 1 && !tickers[t]) tickers[t] = n.id; }
    });
    var LN = W.LEGAL_NAMES || {};
    Object.keys(LN).forEach(function (k) { if (NB[LN[k]] && k.length >= 4) addName(k, NB[LN[k]].id); });
    _cIdx = { names: names, tickers: tickers }; _cIdxN = keys.length;
    return _cIdx;
  }
  function detectCompany(text) {
    var idx = _companyIndex(); if (!idx) return null;
    var raw = String(text || '').replace(/[¿?¡!,;:()"«»“”]+/g, ' ').split(/\s+/).filter(Boolean);
    var i;
    for (i = 0; i < raw.length; i++) {                           // tickers: SOLO en MAYÚSCULAS (NVDA, TSM)
      var tk = raw[i].replace(/[.'’]+$/, '').replace(/^\$/, '');
      if (/^[A-Z][A-Z0-9.]{0,5}$/.test(tk) && !TICKER_STOP[tk] && idx.tickers[tk] && (tk.length >= 2 || raw[i].charAt(0) === '$')) return idx.tickers[tk];
    }
    var fw = raw.map(function (w) { return _fold(w).replace(/[.'’]+$/, ''); });
    for (var len = 4; len >= 1; len--) {
      for (i = 0; i + len <= fw.length; i++) {
        var key = fw.slice(i, i + len).join(' ');
        var id = idx.names[key]; if (!id) continue;
        if (len === 1) {
          var orig = raw[i];
          if (key.length <= 3 && key !== 'amd' && orig !== orig.toUpperCase()) continue;   // "arm", "kla" en minúscula: ambiguo
          // "meta", "vale" → palabras: solo cuentan con Mayúscula y NO al inicio de la frase ("¿Vale la pena…?")
          if (NAME_STOP[key] && (i === 0 || orig.charAt(0) !== orig.charAt(0).toUpperCase())) continue;
        }
        return id;
      }
    }
    return null;
  }

  var RX_RADAR = /\b(riesgos?|noticias?|guerras?|sanci[oó]n(es)?|sancionad[oa]s?|conflictos?|aranceles?|geopol[ií]tic[oa]s?|invasi[oó]n|eventos?|elecciones|qu[eé]\s+pasa(r[ií]a)?\s+si|news|wars?|sanctions?|tariffs?|risks?|what\s+if|conflict|geopolitic\w*)\b/i;
  var RX_CADENA = /\b(proveedor(es|a|as)?|clientes?|cadena|suministro|depende(n|ncia)?|dependiente|abastec\w*|suppliers?|customers?|clients?|chain|supply|depends?|dependen(ce|cy))\b/i;
  var RX_TECNICO = /\b(precios?|gr[aá]fic[oa]s?|tendencias?|sube|suben|subi[oó]|baja|bajan|baj[oó]|cotiza\w*|momentum|volatilidad|price|prices|chart|trend|trending|rall(y|ies)|drops?|volatility)\b/i;
  var RX_COMITE = /\b(comit[eé]|convicci[oó]n|comprar?|vender?|compro|vendo|opinan|veredicto|recomiendas?|conviene|invertir|committee|conviction|buy|sell|verdict|invest|should\s+i)\b/i;
  var RX_RISKQ = /riesgo|proveedor|cadena|suministro|depend|risk|supplier|supply|chain/i;

  function _enabledList(opts) {
    if (opts && Array.isArray(opts.enabled)) return opts.enabled;
    try { if (W.KhipuAgentPrefs && W.KhipuAgentPrefs.enabled) return W.KhipuAgentPrefs.enabled(); } catch (e) {}
    return AGENT_ORDER.slice();
  }
  /* predictAgents(texto, {enabled?, hasCompany?}) → ['analista','radar',…] (orden de las mascotas).
     Pura salvo por leer NODE_BY_ID / KhipuAgentPrefs cuando no se pasan. */
  function predictAgents(text, opts) {
    opts = opts || {};
    var t = String(text || ''), f = _fold(t).trim();
    var enabled = _enabledList(opts);
    var on = function (id) { return id === 'khipu' || enabled.indexOf(id) >= 0; };
    // menciones explícitas ("@fundamental …", "/cartera @geo …") → ese agente y nadie más
    var mm = f.match(/^(?:\/(?:cartera|portafolio|portfolio|micartera)\s+)?@\s*([a-z_]+)/);
    if (mm && MENTION_AGENT[mm[1]]) return [MENTION_AGENT[mm[1]]];
    if (/^\/(?:cartera|portafolio|portfolio|micartera)\b/.test(f) || /^@\s*(?:cartera|portafolio|portfolio)\b/.test(f)) return ['khipu'];
    if (/^\/(?:comite|committee)\b/.test(f)) return ['comite'];
    if (/^\/(?:investigar|investiga|investigacion|research|investigate)\b/.test(f))
      return ['analista', 'radar', 'cadena', 'tecnico'].filter(on);
    var company = opts.hasCompany != null ? !!(typeof opts.hasCompany === 'function' ? opts.hasCompany(t) : opts.hasCompany) : !!detectCompany(t);
    var want = {};
    if (company) want.analista = 1;
    if (RX_RADAR.test(f)) want.radar = 1;
    if (RX_CADENA.test(f)) want.cadena = 1;
    if (RX_TECNICO.test(f)) want.tecnico = 1;
    if (RX_COMITE.test(f)) want.comite = 1;
    var out = AGENT_ORDER.filter(function (id) { return id !== 'khipu' && want[id] && on(id); });
    if (!out.length && company && on('analista')) out = ['analista'];
    return out.length ? out : ['khipu'];
  }

  function _autoFn(prefs) {
    if (prefs && typeof prefs.auto === 'function') return function (id) { return !!prefs.auto(id); };
    if (prefs && prefs.agents) return function (id) { var a = prefs.agents[id]; return !!(a && a.on !== false && a.auto); };
    try { if (W.KhipuAgentPrefs && W.KhipuAgentPrefs.auto) return function (id) { return W.KhipuAgentPrefs.auto(id); }; } catch (e) {}
    var DEF = { analista: 1, cadena: 1, comite: 1 };
    return function (id) { return !!DEF[id]; };
  }
  /* planWindows(respuesta, pregunta, prefs, centrado) → [{kind, arg:{id}, agent}] — PURA.
     Solo con la Cabina en modo flancos y una empresa en la respuesta (entities[0]):
       glance       ← auto Analista
       supplychain  ← auto Cadena  y (Cadena aportó o la pregunta habla de riesgo/proveedores)
       conviction   ← auto Comité  y (hay tarjeta del comité o el Comité aportó) */
  function planWindows(reply, question, prefs, centered) {
    reply = reply || {};
    if (!centered) return [];
    var e0 = Array.isArray(reply.entities) ? reply.entities[0] : null;
    var id = e0 && (typeof e0 === 'string' ? e0 : e0.id);
    if (!id) return [];
    var auto = _autoFn(prefs), used = agentsOf(reply), out = [];
    var arg = function () { return { id: String(id) }; };
    if (auto('analista')) out.push({ kind: 'glance', arg: arg(), agent: 'analista' });
    if (auto('cadena') && (used.indexOf('cadena') >= 0 || RX_RISKQ.test(String(question || ''))))
      out.push({ kind: 'supplychain', arg: arg(), agent: 'cadena' });
    if (auto('comite') && ((reply.cards && reply.cards.committee) || used.indexOf('comite') >= 0))
      out.push({ kind: 'conviction', arg: arg(), agent: 'comite' });
    return out;
  }
  function _kindRegistered(kind) {
    try {
      if (W.KhipuOSWin && W.KhipuOSWin.kinds && W.KhipuOSWin.kinds[kind]) return true;
      var ck = W.BixbyCockpit;
      if (ck && typeof ck.hasKind === 'function') return !!ck.hasKind(kind);
    } catch (e) {}
    return false;
  }
  function _centered() {
    try {
      var ck = W.BixbyCockpit;
      return !!(ck && typeof ck.stage === 'function' && ck.isCentered && ck.isCentered() && (!ck.isOpen || ck.isOpen()));
    } catch (e) { return false; }
  }

  function newReqId() {
    var a = new Array(16), i;
    try {
      var c = W.crypto || (typeof crypto !== 'undefined' ? crypto : null);   // eslint-disable-line no-undef
      if (c && c.getRandomValues) { var u = new Uint8Array(16); c.getRandomValues(u); for (i = 0; i < 16; i++) a[i] = u[i]; }
      else throw new Error('no crypto');
    } catch (e) { for (i = 0; i < 16; i++) a[i] = Math.floor(Math.random() * 256); }
    return 'kc' + a.map(function (b) { return ('0' + b.toString(16)).slice(-2); }).join('');
  }

  // "hace 3 min" / "14:32" / "29 sept" — la hora de un dato (as_of), nunca inventada
  function relTime(iso, now) {
    if (!iso) return '';
    var s = String(iso), dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(s);
    var t = Date.parse(dateOnly ? s + 'T12:00:00' : s);
    if (!isFinite(t)) return '';
    now = now || Date.now();
    var en = lang() === 'en', d = new Date(t), n = new Date(now);
    var MES = en ? ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                 : ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sept', 'oct', 'nov', 'dic'];
    var day = function () { return en ? MES[d.getMonth()] + ' ' + d.getDate() : d.getDate() + ' ' + MES[d.getMonth()]; };
    if (dateOnly) return day() + (d.getFullYear() !== n.getFullYear() ? ' ' + d.getFullYear() : '');
    var sec = Math.round((now - t) / 1000);
    if (sec >= -90 && sec < 60) return en ? 'just now' : 'ahora';
    if (sec >= 60 && sec < 3600) { var m = Math.round(sec / 60); return en ? m + ' min ago' : 'hace ' + m + ' min'; }
    var hm = ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
    if (d.toDateString() === n.toDateString()) return hm;
    return day() + (d.getFullYear() !== n.getFullYear() ? ' ' + d.getFullYear() : '') + ' ' + hm;
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
    // Khipus OS: cómo quieres que te hable (Simple/Pro) y qué agentes participan (solo PRESENTACIÓN:
    // nunca cambia decisiones del comité ni tamaños de órdenes)
    try {
      var P = W.KhipuAgentPrefs;
      if (P && P.mode && P.enabled) { ctx.mode = P.mode() === 'pro' ? 'pro' : 'simple'; ctx.agents_enabled = P.enabled().slice(0, 6); }
    } catch (e) {}
    return ctx;
  }

  function _base() { return (typeof BASE !== 'undefined' && BASE) ? BASE : (W.BASE || ''); }   // eslint-disable-line no-undef

  function send(text, opts) {
    opts = opts || {};
    var base = _base();
    var body = { message: String(text || '').slice(0, 2000), history: history.slice(-MAX_TURNS), lang: lang(), context: context() };
    // req_id (contrato §3.2): el servidor publica qué agentes trabajan → la burbuja "pensando" lo muestra en vivo.
    // La Cabina y el Command Center llaman appendPending() y en el MISMO instante send(): se enlazan solos.
    var pend = opts.pending || null;
    if (!pend && _lastPending && !_lastPending._kcBound && _lastPending.classList && _lastPending.classList.contains('kc-pending') &&
        Date.now() - (_lastPending._kcT0 || 0) < 2500) pend = _lastPending;
    var rid = (typeof opts.req_id === 'string' && /^[A-Za-z0-9_-]{1,64}$/.test(opts.req_id)) ? opts.req_id : (pend && pend._kcReq) || newReqId();
    body.req_id = rid;
    if (pend) {
      pend._kcBound = true; pend._kcReq = rid;
      if (!pend._kcQ) { pend._kcQ = String(text || ''); _paintThinking(pend, predictAgents(pend._kcQ).map(function (id) { return { id: id, state: 'working' }; })); }
      _pollProgress(pend, rid);
    }
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
      var src = pfSelected(), sn = route.seat && SEAT_NAME[route.seat];
      var pl = '💼 ' + (src ? String(src.label).replace(/^[^\wÀ-ÿ]+\s*/, '').replace(/\s·\s[^·]*$/, '') : L('sin cartera', 'no portfolio'));
      if (sn) return { name: L(sn[1], sn[2]), emoji: sn[0], seat: route.seat, label: pl };
      if (route.seat !== 'committee') return { name: 'Khipu', emoji: '💬', seat: 'khipu', label: pl };
      return { name: L('Comité de cartera', 'Portfolio committee'), emoji: '💼', seat: 'portfolio',
        label: src ? String(src.label).replace(/^[^\wÀ-ÿ]+\s*/, '').replace(/\s·\s[^·]*$/, '') : L('sin cartera', 'no portfolio') };
    }
    return null;
  }
  function askAgent(route) {
    var base = _base();
    var src = pfSelected();
    // la burbuja "pensando" recién creada es de ESTA pregunta (no va por /api/khipu/chat): que otro send() no la tome
    if (_lastPending && !_lastPending._kcBound && Date.now() - (_lastPending._kcT0 || 0) < 2500) _lastPending._kcBound = true;
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
        body: JSON.stringify({ question: route.question || '', seat: route.seat || null, positions: p.positions, cash_usd: p.cash || 0, profile: prof || {},
          lang: lang(), source_label: label, history: history.slice(-MAX_TURNS), actor: actor || 'usuario' }),
      }).then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (d) {
          if (timer) clearTimeout(timer);
          if (!r.ok && !d.answer) throw new Error((lang() === 'en' ? d.error_en : d.error) || d.error || ('HTTP ' + r.status));
          d.agent = d.agent || agentInfo(route);
          if (!prof && route.seat === 'committee') d.profile_missing = true;
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

  /* ══ 4) HILO (burbujas) ═════════════════════════════════════════════════
     Khipus OS (2026-10-06, video): tu pregunta a la DERECHA en gris suave; Khipu a la
     izquierda con su mascota y el texto directo sobre la superficie; debajo, una tarjeta
     con lo que aportó cada agente. Colores = tokens --os-* de la Cabina (claro/oscuro);
     fuera de ella (Command Center viejo) los respaldos son los oscuros de siempre. */
  var CSS = '' +
    '.kc-thread{display:flex;flex-direction:column;gap:16px;width:100%;max-width:860px;margin:0 auto;padding:6px 2px 10px;box-sizing:border-box;color:var(--os-ink,#E8EDFB);--kc-warn:#F2C46D}' +
    'body:not(.dark) #bcp-ov:not(.kos-classic) .kc-thread{--kc-warn:#8F5B00}' +
    '.kc-msg{font-size:14.5px;line-height:1.55;overflow-wrap:anywhere;word-break:break-word;letter-spacing:-.003em}' +
    '.kc-user{align-self:flex-end;max-width:86%;box-sizing:border-box;background:var(--os-surface-2,rgba(255,255,255,.07));color:var(--os-ink,#E8EDFB);' +
      'border-radius:18px;padding:11px 16px;white-space:pre-wrap;animation:kcIn .2s ease both}' +
    '.kc-bot{align-self:stretch;display:flex;align-items:flex-start;gap:12px;min-width:0;color:var(--os-ink,#E8EDFB)}' +
    '.kc-av{flex:0 0 26px;width:26px;height:26px;line-height:0}' +
    '.kc-main{flex:1;min-width:0;padding-top:2px}' +
    '.kc-bot:not(.kc-pending) .kc-main{animation:kcIn .26s cubic-bezier(.2,.7,.2,1) both}' +
    '.kc-body p{margin:0 0 9px}.kc-body p:last-child{margin-bottom:0}.kc-body ul,.kc-body ol{margin:4px 0 9px;padding-left:20px}.kc-body li{margin:3px 0}' +
    '.kc-bot code{font-family:"JetBrains Mono",ui-monospace,monospace;font-size:12.5px;background:var(--os-surface-2,rgba(255,255,255,.07));padding:1px 5px;border-radius:6px}' +
    '.kc-bot a{color:var(--os-accent,#7EB6FF);text-decoration:none}.kc-bot a:hover{text-decoration:underline}' +
    '.kc-h{font-weight:650;margin:10px 0 4px;color:var(--os-ink,#FFFFFF);letter-spacing:-.01em}' +
    '.kc-who{font-size:12.5px;font-weight:600;color:var(--os-ink-2,#A6A8B5);margin:2px 0 6px}' +
    '.kc-agent{display:inline-flex;align-items:center;gap:6px;flex-wrap:wrap}' +
    '.kc-agent-av{display:inline-flex;width:20px;height:20px;border-radius:50%;overflow:hidden}.kc-agent-av svg{width:100%;height:100%}' +
    '.kc-agent-ent{color:var(--os-ink-3,#7C8096);font-weight:500}' +
    // lo que aportó cada agente (tarjeta suave, como el video)
    '.kc-contrib{margin-top:12px;background:var(--os-surface-2,rgba(255,255,255,.05));border-radius:14px;padding:12px 14px;display:flex;flex-direction:column;gap:10px}' +
    '.kc-ag{display:flex;gap:10px;align-items:flex-start;font-size:13.5px;line-height:1.45;color:var(--os-ink-2,#A6A8B5)}' +
    '.kc-ag>.km,.kc-ag>.kc-mf{margin-top:1px}' +
    '.kc-agn{min-width:0}.kc-agn b{color:var(--os-ink,#F2F2F5);font-weight:650;margin-right:4px}' +
    '.kc-agt{color:var(--os-ink-3,#7C8096);font-size:12px;white-space:nowrap;font-variant-numeric:tabular-nums}' +
    '.kc-ag.off .kc-agn{color:var(--os-ink-3,#7C8096)}' +
    '.kc-bad{color:var(--os-bad,#F06565);font-weight:500}' +
    '.kc-foot{margin-top:10px}' +
    '.kc-src{font-size:12px;line-height:1.5;color:var(--os-ink-3,#7C8096)}' +
    '.kc-src a{color:var(--os-ink-2,#A6A8B5);text-decoration:underline;text-decoration-color:var(--os-line,rgba(255,255,255,.18));text-underline-offset:2px}' +
    '.kc-t{font-variant-numeric:tabular-nums;white-space:nowrap}' +
    '.kc-meta{font-size:11.5px;color:var(--os-ink-3,#7C8096);margin-top:4px;font-variant-numeric:tabular-nums}' +
    '.kc-note{margin-top:10px;font-size:12.5px;line-height:1.45;color:var(--kc-warn,#F2C46D)}' +
    '.kc-chart{margin-top:12px;max-width:760px}.kc-chart .cv-card{margin:0}.kc-chart .cv-card-close{display:none}.kc-chart-open{margin-top:8px}' +
    '.kc-acts{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}' +
    '.kc-act{font-size:13px;font-weight:500;line-height:1.2;padding:8px 13px;border-radius:999px;cursor:pointer;border:0;font-family:inherit;' +
      'background:var(--os-surface-2,rgba(255,255,255,.08));color:var(--os-ink,#E8EDFB);transition:background .14s,transform .14s}' +
    '.kc-act:hover{background:var(--os-surface-3,rgba(255,255,255,.14))}.kc-act:active{transform:scale(.98)}' +
    '.kc-act:focus-visible,.kc-retry:focus-visible{outline:none;box-shadow:0 0 0 3px rgba(76,141,246,.35)}' +
    '.kc-retry{margin-left:8px;border:0;background:var(--os-surface-2,rgba(255,255,255,.08));color:var(--os-ink,#E8EDFB);border-radius:999px;padding:3px 10px;cursor:pointer;font-size:12px;font-family:inherit}' +
    '.kc-retry:hover{background:var(--os-surface-3,rgba(255,255,255,.14))}' +
    // pensando: fila de mascotas + "Analista, Cadena y Comité están investigando…"
    '.kc-pending{animation:kcIn .2s ease both}' +
    '.kc-think{display:flex;align-items:center;gap:10px;color:var(--os-ink-3,#8D90A0);font-size:13px;line-height:1.35;min-height:22px}' +
    '.kc-tm{display:inline-flex;align-items:center;gap:5px;flex-shrink:0}' +
    '.kc-tmi{display:inline-flex;line-height:0;transition:opacity .3s}.kc-tmi.kc-done{opacity:.42}.kc-tmi.kc-fail{opacity:.22}' +
    '.kc-tt{min-width:0}.kc-el{font-variant-numeric:tabular-nums;white-space:nowrap;opacity:.8}' +
    '.kc-err{color:var(--os-bad,#FF8FA3);padding-top:2px}' +
    '.kc-mf{display:inline-block;flex-shrink:0;border-radius:50%;vertical-align:middle}' +
    // chip del agente en TU burbuja (@analista, 💼 cartera…)
    '.kc-uchip{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;color:var(--os-ink-2,#A6A8B5);background:var(--os-surface,rgba(255,255,255,.08));' +
      'border-radius:999px;padding:2px 10px 2px 3px;margin:0 6px 5px 0;white-space:nowrap;vertical-align:middle}' +
    '.kc-uchip i{font-style:normal;display:inline-flex;width:18px;height:18px;border-radius:50%;align-items:center;justify-content:center;font-size:11px;line-height:0}' +
    // tarjeta del comité de cartera
    '.kc-pf{margin-top:12px;border-radius:14px;padding:12px 14px;background:var(--os-surface-2,rgba(255,255,255,.05))}' +
    '.kc-pf-top{display:flex;gap:12px;align-items:center}.kc-pf-sc{width:46px;height:46px;flex:0 0 46px;border-radius:50%;border:4px solid;display:flex;align-items:center;justify-content:center;font-weight:750;font-size:15px;font-variant-numeric:tabular-nums}' +
    '.kc-pf-v{font-weight:650;font-size:13.5px}.kc-pf-m{font-size:12px;color:var(--os-ink-2,#A6A8B5);margin-top:2px;font-variant-numeric:tabular-nums}' +
    '.kc-pf-a{display:flex;gap:8px;align-items:baseline;font-size:12.5px;margin-top:6px}.kc-pf-a b{white-space:nowrap}.kc-pf-a span{color:var(--os-ink-2,#A6A8B5)}' +
    '.kc-pf-x{color:var(--kc-warn,#F2C46D);margin-top:6px}' +
    '@keyframes kcIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}' +
    // Command Center viejo: su tarjeta ya rotula la respuesta (sin avatar ni encabezado)
    '.bcc-card .kc-av{display:none}.bcc-card .kc-bot{display:block}' +
    '@media(max-width:600px){.kc-msg{font-size:14px}.kc-user{max-width:92%;padding:10px 14px}.kc-bot{gap:10px}.kc-av{flex-basis:24px;width:24px;height:24px}.kc-contrib{padding:11px 12px}}' +
    '@media(prefers-reduced-motion:reduce){.kc-user,.kc-pending,.kc-bot .kc-main{animation:none!important}}';

  function ensureStyles() {
    if (!W.document || !W.document.head || W.document.getElementById('kc-styles')) return;
    var st = W.document.createElement('style'); st.id = 'kc-styles'; st.textContent = CSS;
    W.document.head.appendChild(st);
  }

  // mascota (engine/mascot.js); sin el módulo, una burbuja con los mismos tonos (nunca un hueco)
  function mascot(id, size, state) {
    id = AGENT_NAME[id] ? id : 'khipu';
    try { if (W.KhipuMascot && W.KhipuMascot.svg) return W.KhipuMascot.svg(id, size, state ? { state: state } : undefined); } catch (e) {}
    var c = AGENT_TINT[id];
    return '<span class="kc-mf" role="img" aria-label="' + esc(agentName(id)) + '" style="width:' + size + 'px;height:' + size + 'px;' +
      'background:radial-gradient(circle at 32% 26%,rgba(255,255,255,.5) 0,rgba(255,255,255,0) 42%),linear-gradient(135deg,' + c[0] + ',' + c[1] + ' 62%,' + c[2] + ')"></span>';
  }

  function _scroll(el) {
    try {
      var p = el; while (p && p.parentElement) { p = p.parentElement; if (p.scrollHeight > p.clientHeight + 4 && /(auto|scroll)/.test(getComputedStyle(p).overflowY)) { p.scrollTop = p.scrollHeight; break; } }
      if (el.scrollIntoView) el.scrollIntoView({ block: 'end' });
    } catch (e) {}
  }

  function appendUser(thread, text, agent) {
    ensureStyles();
    try { thread._kcLastQ = String(text || ''); } catch (e) {}   // appendPending lo usa para predecir quién investiga
    var d = W.document.createElement('div'); d.className = 'kc-msg kc-user';
    if (agent && agent.name) {
      var chip = W.document.createElement('span'); chip.className = 'kc-uchip';
      var mid = agent.mascot || null;
      if (!mid && agent.seat) { try { mid = (W.KhipuMascot && W.KhipuMascot.of) ? W.KhipuMascot.of(agent.seat) : SEAT_AGENT[agent.seat]; } catch (e) { mid = null; } }
      chip.innerHTML = '<i>' + (mid && W.KhipuMascot ? mascot(mid, 18) : esc(agent.emoji || '🤖')) + '</i>' + esc(agent.name + (agent.label ? ' · ' + agent.label : ''));
      d.appendChild(chip);
      text = String(text || '').replace(/^\s*(?:(?:\/\S+|@\S+)\s*){1,2}/, '');
      if (text) { d.appendChild(W.document.createElement('br')); }
    }
    d.appendChild(W.document.createTextNode(text));
    thread.appendChild(d); _scroll(d); return d;
  }

  /* ── "pensando": quién investiga (predicción → progreso REAL del servidor) ── */
  function _joinNames(names) {
    var en = lang() === 'en';
    if (names.length <= 1) return names[0] || '';
    return names.slice(0, -1).join(', ') + (en ? ' and ' : ' y ') + names[names.length - 1];
  }
  // list = [{id, state:'working'|'done'|'error'}]
  function thinkingText(list) {
    var en = lang() === 'en';
    var real = (list || []).filter(function (a) { return a.id !== 'khipu'; });
    var working = real.filter(function (a) { return a.state === 'working'; });
    if (!real.length) return en ? 'Khipu is thinking…' : 'Khipu está pensando…';
    if (!working.length) return en ? 'Khipu is writing the answer…' : 'Khipu está redactando la respuesta…';
    var names = working.map(function (a) { return agentName(a.id); });
    return _joinNames(names) + (names.length === 1 ? (en ? ' is researching…' : ' está investigando…') : (en ? ' are researching…' : ' están investigando…'));
  }
  function _paintThinking(el, list) {
    if (!el || !el.querySelector) return;
    var tm = el.querySelector('.kc-tm'), tt = el.querySelector('.kc-tt');
    if (!tm || !tt) return;
    list = (list || []).filter(function (a) { return a && AGENT_NAME[a.id]; });
    var sig = list.map(function (a) { return a.id + ':' + a.state; }).join(',') + '|' + lang();
    if (el._kcSig === sig) return;
    el._kcSig = sig; el._kcList = list;
    var shown = list.filter(function (a) { return a.id !== 'khipu'; });
    if (!shown.length) shown = [{ id: 'khipu', state: 'working' }];
    // actualización por mascota: las que siguen igual no reinician su animación
    var have = {};
    Array.prototype.slice.call(tm.children).forEach(function (c) { have[c.getAttribute('data-ag')] = c; });
    shown.forEach(function (a, i) {
      var c = have[a.id];
      if (!c) { c = W.document.createElement('span'); c.className = 'kc-tmi'; c.setAttribute('data-ag', a.id); }
      if (c.getAttribute('data-st') !== a.state) {
        c.innerHTML = mascot(a.id, 18, a.state === 'working' ? 'think' : null);
        c.setAttribute('data-st', a.state);
        c.classList.toggle('kc-done', a.state === 'done');
        c.classList.toggle('kc-fail', a.state === 'error');
        c.title = agentName(a.id) + (a.state === 'done' ? ' ✓' : a.state === 'error' ? ' — ' + L('sin datos', 'no data') : '');
      }
      if (tm.children[i] !== c) tm.insertBefore(c, tm.children[i] || null);
      delete have[a.id];
    });
    Object.keys(have).forEach(function (k) { if (have[k].parentNode === tm) tm.removeChild(have[k]); });
    tt.textContent = thinkingText(list);
  }
  var _lastPending = null;
  function appendPending(thread, opts) {
    opts = opts || {};
    ensureStyles();
    var d = W.document.createElement('div'); d.className = 'kc-msg kc-bot kc-pending';
    d.innerHTML = '<div class="kc-think" role="status" aria-live="polite"><span class="kc-tm"></span><span class="kc-tt"></span><span class="kc-el"></span></div>';
    d._kcQ = opts.text != null ? String(opts.text) : ((thread && thread._kcLastQ) || '');
    try { if (thread) thread._kcLastQ = ''; } catch (e) {}
    d._kcT0 = Date.now(); d._kcBound = false;
    d._kcReq = (typeof opts.req_id === 'string' && opts.req_id) ? opts.req_id : newReqId();
    thread.appendChild(d);
    _paintThinking(d, (d._kcQ ? predictAgents(d._kcQ) : ['khipu']).map(function (id) { return { id: id, state: 'working' }; }));
    // segundos transcurridos (a partir de 4 s): la espera se ve honesta, no colgada
    var elx = d.querySelector('.kc-el');
    d._timer = setInterval(function () {
      var s = Math.round((Date.now() - d._kcT0) / 1000);
      if (elx) elx.textContent = s >= 4 ? s + ' s' : '';
      if (d._kcSig && d._kcSig.split('|')[1] !== lang() && d._kcList) { d._kcSig = ''; _paintThinking(d, d._kcList); }   // cambió el idioma
    }, 1000);
    _lastPending = d;
    _scroll(d); return d;
  }
  // progreso por agente: [{agent, tool, state}] (una fila por herramienta) → una mascota por agente
  function progressAgents(p) {
    var by = {};
    ((p && p.agents) || []).forEach(function (a) {
      var id = a && a.agent; if (!AGENT_NAME[id]) return;
      var g = by[id] || (by[id] = { w: 0, d: 0, e: 0 });
      if (a.state === 'working') g.w++; else if (a.state === 'error') g.e++; else g.d++;
    });
    return AGENT_ORDER.filter(function (id) { return by[id]; }).map(function (id) {
      var g = by[id]; return { id: id, state: g.w ? 'working' : (g.d ? 'done' : 'error') };
    });
  }
  function _stopPending(el) {
    if (!el) return;
    if (el._timer) { clearInterval(el._timer); el._timer = null; }
    if (el._kcPollStop) { try { el._kcPollStop(); } catch (e) {} }
    if (_lastPending === el) _lastPending = null;
  }
  // GET /api/khipu/chat/progress/<req_id> cada ~0,7 s mientras se espera. Servidor viejo (404 seguidos),
  // límite de tasa o red caída → se detiene en silencio y queda la predicción.
  function _pollProgress(el, rid) {
    if (!el || typeof fetch !== 'function') return;
    if (el._kcPollStop) el._kcPollStop();
    var stopped = false, seen = false, misses = 0, fails = 0, t0 = Date.now(), tm = null;
    var stop = function () { stopped = true; if (tm) { clearTimeout(tm); tm = null; } el._kcPollStop = null; };
    el._kcPollStop = stop;
    var next = function (ms) { if (!stopped) tm = setTimeout(tick, ms); };
    function tick() {
      tm = null;
      if (stopped) return;
      if (!el.classList.contains('kc-pending') || el.isConnected === false || Date.now() - t0 > 90000) { stop(); return; }
      fetch(_base() + '/api/khipu/chat/progress/' + encodeURIComponent(rid), { cache: 'no-store', headers: { Accept: 'application/json' } })
        .then(function (r) {
          if (r.status === 404) { misses++; return null; }
          if (r.status === 429) { fails += 3; return null; }
          var ct = (r.headers && r.headers.get && r.headers.get('content-type')) || '';
          if (!r.ok || ct.indexOf('application/json') < 0) { fails++; return null; }
          return r.json();
        })
        .then(function (p) {
          if (stopped) return;
          if (p && Array.isArray(p.agents)) {
            seen = true; misses = 0;
            var list = progressAgents(p);
            if (list.length) { el._kcLive = true; _paintThinking(el, list); }
            if (p.done) { stop(); return; }
          }
          if ((!seen && misses >= 8) || fails >= 6) { stop(); return; }
          next(fails ? 1400 : 700);
        }, function () { if (stopped) return; fails++; if (fails >= 6) { stop(); return; } next(1400); });
    }
    next(350);
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
    ask_agent: ['Pregunta a un analista', 'Asked an analyst'], scenario_exposure: ['Exposición a un escenario', 'Scenario exposure'],
    get_conclusions_board: ['Pizarra del comité', 'Committee board'], get_research_health: ['Salud de la investigación', 'Research health'],
  };
  function toolLabel(n) { var x = TOOL_LABEL[n]; return x ? x[lang() === 'en' ? 1 : 0] : n; }

  var ACT_LABEL = {
    open_xray: ['🔬 Ver X-Ray', '🔬 Open X-Ray'], navigate: ['🎯 Ver en el mapa', '🎯 Show on map'],
    stress: ['🚨 Simular caída', '🚨 Simulate failure'], dossier: ['📊 Dossier', '📊 Dossier'],
    open_research: ['🧪 Investigación', '🧪 Research'], open_committee: ['🏛 Comité', '🏛 Committee'],
    simulate: ['🔮 Escenario', '🔮 Scenario'], agent_sim: ['🧬 Simular con agentes', '🧬 Agent simulation'],
    chart: ['✦ Gráfico', '✦ Chart'], compare: ['⇄ Comparar', '⇄ Compare'],
    open_risk_report: ['🛡 Riesgo de mi cartera', '🛡 My portfolio risk'], switch_tab: ['📂 Abrir', '📂 Open'],
    open_world: ['🌐 Monitor mundial', '🌐 World monitor'], broker: ['🔒 Cuenta del bróker (Alpaca)', '🔒 Broker account (Alpaca)'],
    open_pf_committee: ['💼 Ver el análisis completo', '💼 See the full analysis'],
    open_portfolio: ['🧪 Cartera', '🧪 Portfolio'],
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

  function _mode() { try { return W.KhipuAgentPrefs && W.KhipuAgentPrefs.mode && W.KhipuAgentPrefs.mode() === 'pro' ? 'pro' : 'simple'; } catch (e) { return 'simple'; } }
  // la hora de un dato con su atributo para refrescar "hace N min" mientras el hilo sigue abierto
  function _timeTag(iso, prefix) {
    var r = relTime(iso); if (!r) return '';
    return '<span class="kc-t" data-asof="' + esc(iso) + '" data-pre="' + esc(prefix || '') + '" title="' + esc(String(iso)) + '">' + esc((prefix || '') + r) + '</span>';
  }
  var _timesTimer = null;
  function _armTimes() {
    if (_timesTimer || !W.document || typeof setInterval !== 'function') return;
    _timesTimer = setInterval(function () {
      try {
        var els = W.document.querySelectorAll('.kc-t[data-asof]');
        for (var i = 0; i < els.length; i++) { var r = relTime(els[i].getAttribute('data-asof')); if (r) els[i].textContent = (els[i].getAttribute('data-pre') || '') + r; }
      } catch (e) {}
    }, 30000);
  }
  function _toolsText(tools) {
    return (tools || []).map(function (t) {
      if (typeof t === 'string') return esc(toolLabel(t));
      return esc(toolLabel(t.name) + (t.args_summary ? ' (' + String(t.args_summary).slice(0, 40) + ')' : '')) +
        (t.ok === false ? ' <span class="kc-bad" title="' + esc(t.error || '') + '">✕</span>' : '');
    }).join(' · ');
  }
  /* Lo que aportó cada agente. Con agents_used (servidor): mascota + nombre en negrita + nota
     DETERMINISTA (hecha con datos de las herramientas, nunca texto del modelo). Sin él (servidor
     viejo): se deriva de tools_used con el mismo mapa TOOL_AGENT y se listan las consultas. */
  function contribRows(d) {
    d = d || {};
    var en = lang() === 'en', rows = [];
    if (Array.isArray(d.agents_used) && d.agents_used.length) {
      var list = d.agents_used.filter(function (a) { return a && AGENT_NAME[a.agent]; });
      var nonK = list.filter(function (a) { return a.agent !== 'khipu'; });
      if (nonK.length) list = nonK;
      list.forEach(function (a) {
        var tools = Array.isArray(a.tools) ? a.tools : [];
        var note = en ? (a.note_en || a.note_es) : (a.note_es || a.note_en);
        // la nota genérica del servidor ("Consultó get_company, get_news") → nombres legibles
        var generic = note && tools.length && (note === 'Consultó ' + tools.join(', ') || note === 'Checked ' + tools.join(', '));
        rows.push({ id: a.agent, ok: a.ok !== false, note: generic ? null : (note || null), tools: tools, source: a.source || null, as_of: a.as_of || null });
      });
      return rows;
    }
    if (d.agent && d.agent.name) return rows;   // respondió un analista en persona: ya lo dice su encabezado
    var by = {}, order = [];
    (Array.isArray(d.tools_used) ? d.tools_used : []).forEach(function (t) {
      if (!t || !t.name) return;
      var id = toolAgent(t.name, t.args_summary);
      if (!by[id]) { by[id] = { id: id, ok: false, note: null, tools: [], source: null, as_of: null }; order.push(id); }
      by[id].tools.push(t); if (t.ok) by[id].ok = true;
    });
    var ids = AGENT_ORDER.filter(function (id) { return by[id]; });
    var nk = ids.filter(function (id) { return id !== 'khipu'; });
    (nk.length ? nk : ids).forEach(function (id) { rows.push(by[id]); });
    return rows;
  }
  function contribHTML(d) {
    var rows = contribRows(d);
    if (!rows.length) return '';
    var pro = _mode() === 'pro';
    return '<div class="kc-contrib" role="list" aria-label="' + esc(L('Lo que aportó cada agente', 'What each agent contributed')) + '">' + rows.map(function (r) {
      var toolNames = (r.tools || []).map(function (t) { return toolLabel(typeof t === 'string' ? t : t.name); }).join(', ');
      var tip = toolNames + (r.source ? ' · ' + r.source : '') + (r.as_of ? ' · ' + r.as_of : '');
      var body;
      if (r.note) body = esc(r.note);
      else if (r.tools && r.tools.length && typeof r.tools[0] === 'object') body = _toolsText(r.tools);
      else if (r.tools && r.tools.length) body = esc(toolNames);
      else body = '';
      if (!r.ok && !r.note) body += (body ? ' · ' : '') + '<span class="kc-bad">' + esc(L('no pudo obtener los datos ahora', 'could not get the data right now')) + '</span>';
      var when = r.as_of ? _timeTag(r.as_of, pro && r.source ? r.source + ', ' : '') : '';
      return '<div class="kc-ag' + (r.ok ? '' : ' off') + '" role="listitem"' + (tip ? ' title="' + esc(tip) + '"' : '') + '>' + mascot(r.id, 18) +
        '<div class="kc-agn"><b>' + esc(agentName(r.id)) + '</b>' + body + (pro && when ? ' <span class="kc-agt">· ' + when + '</span>' : '') + '</div></div>';
    }).join('') + '</div>';
  }

  /* replyHTML(d) — el HTML de una respuesta (sin botones ni gráfico, que se cablean en fillReply).
     PURA respecto del DOM: se puede probar en node. */
  function replyHTML(d, opts) {
    opts = opts || {};
    d = d || {};
    var avId = 'khipu', who = '';
    // un ANALISTA respondió en persona (@fundamental, @noticias, @todos…): su mascota y su nombre
    if (d.agent && d.agent.name) {
      var mid = null;
      try { mid = (W.KhipuMascot && W.KhipuMascot.of) ? W.KhipuMascot.of(d.agent.seat) : null; } catch (e) { mid = null; }
      if (!mid) mid = SEAT_AGENT[String(d.agent.seat || '')] || null;
      if (mid) avId = mid;
      var old = '';
      if (!W.KhipuMascot) {
        try { old = (W.KhipuCommittee && W.KhipuCommittee.avatar && d.agent.seat !== 'all') ? W.KhipuCommittee.avatar(d.agent.seat, d.agent.emoji, true) : ''; } catch (e) { old = ''; }
      }
      who = '<div class="kc-who"><span class="kc-agent">' + (old ? '<span class="kc-agent-av">' + old + '</span>' : (W.KhipuMascot ? '' : esc(d.agent.emoji || '🤖') + ' ')) +
        esc(d.agent.name) + (d.agent.label ? '<span class="kc-agent-ent"> · ' + esc(d.agent.label) + '</span>' : '') + '</span></div>';
    }
    var h = '<div class="kc-av">' + mascot(avId, 26) + '</div><div class="kc-main">' + who +
      '<div class="kc-body">' + md(d.answer || L('(sin respuesta)', '(no answer)')) + '</div>';
    if (d.portfolio) h += pfCardHTML(d.portfolio);
    if (d.profile_missing) h += '<div class="kc-note">🧭 ' + esc(L('Usé el perfil «moderado» porque aún no definiste el tuyo (Comité → 💼 Mi cartera → 4 preguntas).', 'I used the "moderate" profile because you have not set yours yet (Committee → 💼 My portfolio → 4 questions).')) + '</div>';
    h += contribHTML(d);
    if (d.degraded) {
      var why = (lang() === 'en' ? d.ai_detail_en : d.ai_detail_es) || d.ai_detail || '';
      h += '<div class="kc-note">⚠ ' + esc(L('Respuesta sin IA (solo datos).', 'Answer without AI (data only).')) +
        (why ? ' <span style="opacity:.85">' + esc(why) + '</span>' : '') +
        (opts.retry ? ' <button type="button" class="kc-retry">↻ ' + esc(L('Reintentar', 'Retry')) + '</button>' : '') + '</div>';
    }
    var foot = '';
    var src = Array.isArray(d.sources) ? d.sources : [];
    if (src.length) {
      foot += '<div class="kc-src">' + esc(L('Fuentes', 'Sources')) + ': ' + src.slice(0, 6).map(function (s) {
        var u = s.url && /^https?:\/\//i.test(s.url) ? (W.safeUrl ? W.safeUrl(s.url) : esc(s.url)) : null;
        var lab = u && u !== '#' ? '<a href="' + u + '" target="_blank" rel="noopener noreferrer">' + esc(s.label) + '</a>' : esc(s.label);
        return lab + (s.as_of ? _timeTag(s.as_of, ', ') : '');
      }).join(' · ') + '</div>';
    }
    if (!d.degraded && d.ai && (d.model || d.elapsed_ms)) {
      var mdl = String(d.model || '').replace(/^gemini:/, 'Gemini ').replace(/^claude-/, 'Claude ').replace(/^nvidia:/, 'NVIDIA ');
      foot += '<div class="kc-meta">' + esc(mdl) + (d.steps ? ' · ' + d.steps + ' ' + esc(d.steps === 1 ? L('consulta', 'query') : L('consultas', 'queries')) : '') +
        (d.elapsed_ms ? ' · ' + (d.elapsed_ms / 1000).toFixed(0) + ' s' : '') + '</div>';
    }
    if (foot) h += '<div class="kc-foot">' + foot + '</div>';
    return h + '</div>';
  }

  function fillReply(el, d, opts) {
    opts = opts || {};
    _stopPending(el);
    el.classList.remove('kc-pending');
    d = d || {};
    var question = opts.question != null ? String(opts.question) : (el._kcQ || '');
    el.innerHTML = replyHTML(d, opts);
    _armTimes();
    var main = el.querySelector('.kc-main') || el, foot = main.querySelector('.kc-foot');
    var put = function (node) { if (foot && foot.parentNode === main) main.insertBefore(node, foot); else main.appendChild(node); };
    var acts = Array.isArray(d.actions) ? d.actions : [];
    // FUSIÓN Khipu + Canvas: un gráfico pedido se dibuja AQUÍ, dentro de la respuesta
    // (y se puede abrir en ventana); así no hay que saltar a otra pantalla
    var inlineChart = acts.filter(function (a) { return a.type === 'chart' && typeof a.arg === 'string'; })[0];
    if (inlineChart && opts.inlineChart !== false && W.BixbyCockpit && W.BixbyCockpit.canvasInto) {
      var host = W.document.createElement('div'); host.className = 'kc-chart';
      put(host);
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
      put(box);
    }
    _scroll(el);
    // VENTANAS AUTOMÁTICAS (contrato §3.5): con la Cabina en modo flancos y una empresa en la respuesta,
    // las ventanas nativas de los agentes (en una mirada / cadena / convicción) se abren solas a los costados.
    var plan = [];
    if (opts.autoRun !== false && opts.windows !== false && Array.isArray(d.entities) && d.entities.length) {
      try { plan = planWindows(d, question, null, _centered()).filter(function (w) { return _kindRegistered(w.kind); }); } catch (e) { plan = []; }
    }
    el._kcPlan = plan;
    var delay = opts.autoDelay || 450;
    plan.forEach(function (w, i) {
      setTimeout(function () { try { W.BixbyCockpit.stage(w.kind, w.arg); } catch (e) {} }, delay + i * 260);
    });
    // auto-ejecutar la PRIMERA acción de escenario, DESPUÉS de mostrar el texto
    // (si ya se abrieron las ventanas de los agentes, el X-Ray queda como botón: no se tapa nada)
    if (opts.autoRun !== false) {
      var first = acts.filter(function (a) { return AUTO[a.type] && (!opts.autoFilter || opts.autoFilter(a)); })[0];
      if (first && plan.length && first.type === 'open_xray') first = null;
      if (first) setTimeout(function () { try { (opts.onAction || runAction)(first); } catch (e) {} }, delay + plan.length * 260);
    }
    return el;
  }

  function pfCardHTML(c) {
    var col = c.tone === 'good' ? 'var(--os-good,#2BE38B)' : c.tone === 'warn' ? 'var(--kc-warn,#F2C46D)' : 'var(--os-bad,#FF4D6A)';
    var money = function (v) { v = Number(v); return isFinite(v) ? '$' + Math.round(v).toLocaleString('en-US') : '—'; };
    var KIND = { sell: ['➖', L('Salir de', 'Exit')], reduce: ['➖', L('Reducir', 'Trim')], add: ['➕', L('Aumentar', 'Add')], buy_new: ['🆕', L('Añadir', 'Add new')] };
    var cv = c.coverage || {};
    var h = '<div class="kc-pf"><div class="kc-pf-top"><div class="kc-pf-sc" style="border-color:' + col + ';color:' + col + '">' + esc(c.score) + '</div><div>' +
      '<div class="kc-pf-v">' + esc(c.verdict || '') + '</div><div class="kc-pf-m">' + esc(L('Salud vs tu perfil ', 'Health vs your profile ') + (c.profile || '') + ' · ' + money(c.value_usd) +
      (c.vol_ann_pct != null ? ' · ' + L('se mueve ', 'moves ') + Math.round(c.vol_ann_pct) + L(' % al año', '% a year') : '') +
      (cv.requested ? ' · ' + L('analizadas ', 'analyzed ') + cv.analyzed + '/' + cv.requested : '')) + '</div></div></div>';
    (c.actions || []).forEach(function (a) {
      var k = KIND[a.kind] || ['•', a.kind];
      h += '<div class="kc-pf-a"><b>' + esc(k[0] + ' ' + k[1] + ' ' + (a.label || '')) + '</b><span>' +
        esc(Math.round(a.from_pct) + '% → ' + Math.round(a.to_pct) + '% · ' + (lang() === 'en' ? a.why_en : a.why_es)) + '</span></div>';
    });
    (c.geo || []).forEach(function (g) {
      h += '<div class="kc-pf-a"><b>🌐 ' + esc(g.label || '') + '</b><span>' + esc((lang() === 'en' ? g.title_en : g.title_es) + ' — ' + (lang() === 'en' ? g.why_en : g.why_es)) + '</span></div>';
    });
    if ((c.excluded || []).length) h += '<div class="kc-pf-m kc-pf-x">⚠ ' + esc(L('Sin analizar: ', 'Not analyzed: ') + c.excluded.join(', ')) + '</div>';
    return h + '<div class="kc-pf-m" style="margin-top:6px">🤖 ' + esc(L('Consejo educativo de IA; nada se ejecuta sin tu confirmación.', 'Educational AI advice; nothing runs without your confirmation.')) + '</div></div>';
  }

  function fillError(el, msg) {
    _stopPending(el);
    el.classList.remove('kc-pending');
    el.innerHTML = '<div class="kc-av">' + mascot('khipu', 26) + '</div><div class="kc-main"><div class="kc-err" role="alert">⚠ ' +
      esc(msg || L('No pude procesar eso.', 'I could not process that.')) + '</div></div>';
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
        case 'open_portfolio':
          try { W.localStorage.setItem('kh_pf_active', String(a.arg)); } catch (e) {}
          surf('tab', 'portfolios') || (W.switchTab && W.switchTab('portfolios'));
          setTimeout(function () { try { if (W.KhipuPortfolios && W.KhipuPortfolios.refresh) W.KhipuPortfolios.refresh(); } catch (e) {} }, 300);
          return true;
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
    // Khipus OS (2026-10-06): agentes en el chat
    AGENT_ORDER: AGENT_ORDER, TOOL_AGENT: TOOL_AGENT, SEAT_AGENT: SEAT_AGENT, toolAgent: toolAgent, agentsOf: agentsOf, agentName: agentName,
    predictAgents: predictAgents, detectCompany: detectCompany, planWindows: planWindows, progressAgents: progressAgents,
    thinkingText: thinkingText, contribRows: contribRows, replyHTML: replyHTML, relTime: relTime, newReqId: newReqId,
    toolLabel: toolLabel, mascot: mascot,
  };
})(typeof window !== 'undefined' ? window : globalThis);
