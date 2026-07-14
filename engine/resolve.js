/* ============================================================================
   engine/resolve.js — RESOLUTOR DE EMPRESAS + SUPERFICIE DE RESULTADOS (2026-07)
   Feedback real de Fabrizio: "bixby a veces me dice que una empresa no existe
   o no me entiende, especialmente con nvidia" y "le pido algo y no me muestra
   y es pq esta atras del interfaz".

   Dos APIs globales, compartidas por voice.js / command_center.js /
   cockpit.js / khipu_lang.js (NO duplicar esta lógica en otros archivos):

   1) window.KhipuResolve.find(texto) → { node, score, suggestions }
      - node: nodo de window.NODES (o null si no hay match confiable)
      - score: 0-100 (100 = id exacto … 45 = match por tokens)
      - suggestions: hasta 3 nodos cercanos cuando la confianza es baja
      Normaliza acentos/puntuación, entiende alias de TRANSCRIPCIÓN DE VOZ
      en español ("en vidia" → Nvidia) y tolera typos (Levenshtein).

      window.KhipuResolve.notFound(texto) → { es, en, text, spoken, suggestions }
      Mensaje bilingüe "No encontré «X». ¿Quisiste decir A, B o C?".

   2) window._surface(kind, arg) → garantiza que TODO resultado quede AL FRENTE:
      - Cabina (BixbyCockpit) abierta → se pinta DENTRO de su escenario.
      - Cabina cerrada → cierra overlays que tapan (X-Ray 6000 / compare 6100 /
        dossier 6500 / sistema / explicador 11000) y hace switchTab a la
        pestaña dueña ANTES de renderizar.
      kinds: xray · compare · sim · stress · graph · chart · terminal ·
             insights · canvas · deep · dossier · secondbrain · trade ·
             tab · clear
   ============================================================================ */
(function () {
  'use strict';

  function lang() {
    try { return (window.LANG || localStorage.getItem('eco_lang') || 'es'); } catch (e) { return 'es'; }
  }

  // ── normalización: minúsculas, sin acentos (NFD), sin puntuación ──────────
  // rango U+0300-U+036F (diacríticos combinantes) construido en ASCII puro
  // para que ningún editor/encoding pueda corromper el regex.
  var DIACRITICS = new RegExp('[' + String.fromCharCode(0x300) + '-' + String.fromCharCode(0x36f) + ']', 'g');
  function norm(s) {
    return String(s == null ? '' : s)
      .toLowerCase()
      .normalize('NFD').replace(DIACRITICS, '')
      .replace(/[^a-z0-9\s]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  // palabras vacías típicas de una frase dictada ("la empresa nvidia")
  var STOP = { la: 1, el: 1, los: 1, las: 1, de: 1, del: 1, a: 1, al: 1, un: 1, una: 1, empresa: 1, compania: 1, company: 1, the: 1 };

  function stripStop(nq) {
    var t = nq.split(' ').filter(function (w) { return !STOP[w]; });
    return t.join(' ');
  }

  // ── ALIAS de VOZ (transcripción en español; el usuario DICTA los nombres) ──
  // clave = texto normalizado que puede salir del ASR · valor = id REAL del grafo
  // (ids verificados contra nodes/*.js; los que no existan se ignoran solos).
  var VOICE_ALIAS = {
    // Nvidia — el caso que más falla en la transcripción
    'nvidia': 'Nvidia', 'en vidia': 'Nvidia', 'envidia': 'Nvidia', 'invidia': 'Nvidia',
    'nvidea': 'Nvidia', 'nbidia': 'Nvidia', 'video': 'Nvidia', 'nvdia': 'Nvidia', 'nvidia corporation': 'Nvidia',
    // fabs / equipos
    'tsmc': 'TSMC', 'taiwan semiconductor': 'TSMC', 'te ese eme ce': 'TSMC', 'tsm': 'TSMC',
    'asml': 'ASML', 'a ese eme ele': 'ASML',
    'intel': 'Intel', 'samsung': 'Samsung', 'samsun': 'Samsung', 'sansung': 'Samsung',
    'global foundries': 'GF', 'globalfoundries': 'GF',
    'umc': 'UMC', 'smic': 'SMIC', 'rapidus': 'Rapidus',
    'applied materials': 'AMAT', 'applied': 'AMAT', 'amat': 'AMAT',
    'lam research': 'Lam', 'lam': 'Lam', 'lam risech': 'Lam',
    'kla': 'KLA', 'ka ele a': 'KLA',
    'tokyo electron': 'TEL', 'tel': 'TEL',
    'zeiss': 'Zeiss', 'zaiss': 'Zeiss', 'carl zeiss': 'Zeiss',
    'nikon': 'Nikon', 'canon': 'Canon',
    'teradyne': 'Teradyne', 'advantest': 'Advantest', 'entegris': 'Entegris',
    'shin etsu': 'ShinEtsu', 'shinetsu': 'ShinEtsu', 'sumco': 'SUMCO',
    'siltronic': 'Siltronic', 'global wafers': 'GlobalWafers',
    // diseño / EDA / IP
    'amd': 'AMD', 'a eme de': 'AMD',
    'qualcomm': 'Qualcomm', 'cualcom': 'Qualcomm', 'qualcom': 'Qualcomm', 'kualcom': 'Qualcomm',
    'broadcom': 'Broadcom', 'brodcom': 'Broadcom', 'broadcon': 'Broadcom',
    'arm': 'ARM', 'a erre eme': 'ARM', 'arm holdings': 'ARM',
    'cadence': 'Cadence', 'cadens': 'Cadence', 'kadence': 'Cadence',
    'synopsys': 'Synopsys', 'sinopsis': 'Synopsys', 'synopsis': 'Synopsys', 'sinopsys': 'Synopsys',
    'marvell': 'Marvell', 'marvel': 'Marvell',
    'texas instruments': 'TexasInstruments', 'texas': 'TexasInstruments',
    'nxp': 'NXP', 'infineon': 'Infineon',
    'st micro': 'STMicroelectronics', 'st microelectronics': 'STMicroelectronics', 'stmicroelectronics': 'STMicroelectronics',
    'renesas': 'Renesas', 'onsemi': 'onsemi', 'on semi': 'onsemi', 'wolfspeed': 'Wolfspeed',
    'mobileye': 'Mobileye', 'kioxia': 'Kioxia',
    'western digital': 'WesternDigital', 'seagate': 'Seagate',
    // memoria
    'micron': 'Micron', 'maicron': 'Micron',
    'sk hynix': 'SKHynix', 'hynix': 'SKHynix', 'sk aynix': 'SKHynix', 'aynix': 'SKHynix',
    'hinix': 'SKHynix', 'esca hynix': 'SKHynix',
    // big tech / cloud
    'apple': 'Apple', 'apel': 'Apple', 'aple': 'Apple',
    'microsoft': 'Microsoft', 'micro soft': 'Microsoft', 'azure': 'Microsoft', 'asur': 'Microsoft',
    'google': 'Alphabet', 'alphabet': 'Alphabet', 'alfabet': 'Alphabet', 'gugel': 'Alphabet', 'guguel': 'Alphabet', 'google cloud': 'Alphabet',
    'meta': 'Meta', 'facebook': 'Meta', 'feisbuk': 'Meta',
    'amazon': 'Amazon', 'aws': 'Amazon', 'amazon web services': 'Amazon', 'a doble u ese': 'Amazon',
    'oracle': 'Oracle', 'orakle': 'Oracle', 'oracle cloud': 'Oracle',
    'ibm': 'IBMQuantum', 'i be eme': 'IBMQuantum', 'ibm quantum': 'IBMQuantum',
    'tesla': 'Tesla', 'palantir': 'Palantir', 'palantier': 'Palantir', 'palanter': 'Palantir',
    'alibaba': 'AlibabaCloud', 'alibaba cloud': 'AlibabaCloud',
    'huawei': 'Huawei', 'softbank': 'SoftBank', 'soft bank': 'SoftBank',
    'coreweave': 'CoreWeave', 'core weave': 'CoreWeave', 'core wif': 'CoreWeave', 'corwif': 'CoreWeave',
    'nebius': 'Nebius', 'equinix': 'Equinix', 'digital realty': 'DigitalRealty',
    // labs de IA
    'openai': 'OpenAI', 'open ai': 'OpenAI', 'openia': 'OpenAI', 'open ei': 'OpenAI', 'open i a': 'OpenAI', 'chatgpt': 'OpenAI', 'chat gpt': 'OpenAI',
    'anthropic': 'Anthropic', 'antropic': 'Anthropic', 'antrophic': 'Anthropic', 'antropik': 'Anthropic', 'claude': 'Anthropic',
    'xai': 'xAI', 'x ai': 'xAI', 'equis ai': 'xAI', 'equis a i': 'xAI', 'grok': 'xAI',
    'mistral': 'Mistral', 'mistral ai': 'Mistral',
    'deepseek': 'DeepSeek', 'deep seek': 'DeepSeek', 'dip sik': 'DeepSeek',
    'perplexity': 'Perplexity', 'perplejity': 'Perplexity',
    'hugging face': 'HuggingFace', 'huggingface': 'HuggingFace',
    'databricks': 'Databricks', 'data bricks': 'Databricks',
    'scale ai': 'ScaleAI', 'groq': 'Groq', 'cerebras': 'Cerebras',
    // espacio / defensa / robots
    'spacex': 'SpaceX', 'space x': 'SpaceX', 'espace x': 'SpaceX', 'espacex': 'SpaceX', 'espeis x': 'SpaceX',
    'rocket lab': 'RocketLab', 'rocketlab': 'RocketLab',
    'blue origin': 'BlueOrigin', 'anduril': 'Anduril',
    'waymo': 'Waymo', 'figure': 'Figure', 'figure ai': 'Figure',
    'boston dynamics': 'BostonDynamics',
    // servidores / energía / nuclear
    'super micro': 'SuperMicro', 'supermicro': 'SuperMicro',
    'dell': 'Dell', 'hpe': 'HPE', 'hewlett packard': 'HPE',
    'foxconn': 'Foxconn', 'hon hai': 'Foxconn', 'quanta': 'Quanta',
    'vertiv': 'Vertiv', 'eaton': 'Eaton', 'schneider': 'Schneider',
    'arista': 'Arista', 'cisco': 'Cisco', 'sisco': 'Cisco',
    'constellation': 'Constellation', 'constellation energy': 'Constellation',
    'cameco': 'Cameco', 'oklo': 'Oklo', 'nuscale': 'NuScale', 'nu scale': 'NuScale',
    'terrapower': 'TerraPower', 'terra power': 'TerraPower',
    'ge vernova': 'GEVernova', 'siemens energy': 'SiemensEnergy',
    // óptica / networking
    'coherent': 'Coherent', 'lumentum': 'Lumentum', 'corning': 'Corning',
    'astera labs': 'Astera', 'astera': 'Astera', 'credo': 'Credo', 'ciena': 'Ciena',
    'nokia': 'Nokia', 'ericsson': 'Ericsson',
  };

  // ── Levenshtein con tope (corta temprano si se pasa de max) ───────────────
  function lev(a, b, max) {
    var la = a.length, lb = b.length;
    if (Math.abs(la - lb) > max) return max + 1;
    var prev = [], cur = [], j;
    for (j = 0; j <= lb; j++) prev[j] = j;
    for (var i = 1; i <= la; i++) {
      cur[0] = i;
      var rowMin = i;
      for (j = 1; j <= lb; j++) {
        cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a.charAt(i - 1) === b.charAt(j - 1) ? 0 : 1));
        if (cur[j] < rowMin) rowMin = cur[j];
      }
      if (rowMin > max) return max + 1;
      var t = prev; prev = cur; cur = t;
    }
    return prev[lb];
  }

  // ── índice (lazy; se reconstruye si NODES cambia de tamaño) ───────────────
  // entries: [{key: <texto normalizado>, node, w: <confianza base>}]
  var _entries = null, _exact = null, _builtFor = -1;

  function buildIndex() {
    var NODES = window.NODES || [];
    if (_entries && _builtFor === NODES.length) return;
    _entries = []; _exact = {}; _builtFor = NODES.length;

    function add(key, node, w) {
      if (!key || !node) return;
      _entries.push({ key: key, node: node, w: w });
      var prev = _exact[key];
      if (!prev || w > prev.w) _exact[key] = { node: node, w: w };
    }

    NODES.forEach(function (n) {
      if (!n || !n.id) return;
      add(norm(n.id), n, 100);
      if (n.mkt) add(norm(n.mkt), n, 95);
      var L = norm(n.label);
      add(L, n, 90);
      // "Microsoft (Azure)" → también "microsoft" y "azure"
      var raw = String(n.label || '');
      var p = raw.indexOf('(');
      if (p > 0) {
        add(norm(raw.slice(0, p)), n, 88);
        var inside = raw.slice(p + 1).replace(/\).*$/, '');
        add(norm(inside), n, 82);
      }
    });

    var NB = window.NODE_BY_ID || {};
    // alias de voz (solo si el id destino existe en el grafo)
    Object.keys(VOICE_ALIAS).forEach(function (k) {
      var n = NB[VOICE_ALIAS[k]];
      if (n) add(norm(k), n, 85);
    });
    // NODE_ID_ALIAS (tabla canónica del merge) — ids alias también resuelven
    var IDA = (typeof NODE_ID_ALIAS !== 'undefined') ? NODE_ID_ALIAS
      : (window.NODE_ID_ALIAS || null);
    if (IDA) {
      Object.keys(IDA).forEach(function (k) {
        var n = NB[k] || NB[IDA[k]];
        if (n) add(norm(k), n, 84);
      });
    }
  }

  // ── candidatos más cercanos (para sugerencias) ────────────────────────────
  function nearest(nq, limit) {
    buildIndex();
    if (!nq) return [];
    var cand = [];
    for (var i = 0; i < _entries.length; i++) {
      var e = _entries[i], d;
      if (e.key === nq) d = 0;
      else if (e.key.indexOf(nq) === 0 || nq.indexOf(e.key) === 0) d = 0.5;
      else if (nq.length >= 4 && (e.key.indexOf(nq) >= 0 || nq.indexOf(e.key) >= 0)) d = 1;
      else {
        var max = Math.max(2, Math.floor(Math.max(nq.length, e.key.length) / 3));
        var l = lev(nq, e.key, max);
        if (l > max) continue;
        d = 1 + l;
      }
      cand.push({ node: e.node, d: d, w: e.w });
    }
    cand.sort(function (a, b) { return a.d - b.d || b.w - a.w; });
    var seen = {}, out = [];
    for (var j = 0; j < cand.length && out.length < (limit || 3); j++) {
      var id = cand[j].node.id;
      if (seen[id]) continue;
      seen[id] = 1; out.push(cand[j].node);
    }
    return out;
  }

  // ── find(texto) → {node, score, suggestions} ──────────────────────────────
  function find(q) {
    var NB = window.NODE_BY_ID || {};
    var empty = { node: null, score: 0, suggestions: [] };
    if (q == null) return empty;
    var raw = String(q).trim();
    if (!raw) return empty;
    buildIndex();

    // 0) id exacto tal cual (NODE_BY_ID incluye las claves alias del merge)
    if (NB[raw]) return { node: NB[raw], score: 100, suggestions: [] };

    var nq = norm(raw);
    if (!nq) return empty;
    var nq2 = stripStop(nq) || nq;

    // 1-4) exactos normalizados: id (100) → ticker (95) → label (90) → alias (85)
    var hit = _exact[nq] || _exact[nq2];
    if (hit) return { node: hit.node, score: hit.w, suggestions: [] };

    var i, e, best;

    // 5) prefijo de label/alias (≥3 letras) — gana la clave más corta
    if (nq2.length >= 3) {
      best = null;
      for (i = 0; i < _entries.length; i++) {
        e = _entries[i];
        if (e.key.indexOf(nq2) === 0 && (!best || e.key.length < best.key.length || (e.key.length === best.key.length && e.w > best.w))) best = e;
      }
      if (best) return { node: best.node, score: 70, suggestions: [] };
    }

    // 6) substring (≥4 letras)
    if (nq2.length >= 4) {
      best = null;
      for (i = 0; i < _entries.length; i++) {
        e = _entries[i];
        if (e.key.indexOf(nq2) >= 0 && (!best || e.key.length < best.key.length || (e.key.length === best.key.length && e.w > best.w))) best = e;
      }
      if (best) return { node: best.node, score: 60, suggestions: nearest(nq2, 3).filter(function (n) { return n.id !== best.node.id; }).slice(0, 2) };
    }

    // 7) fuzzy Levenshtein: ≤1 si largo<6, ≤2 si ≥6 (sobre labels+alias+tickers)
    var maxD = nq2.length < 6 ? 1 : 2;
    var bf = null, bfD = maxD + 1, bfW = 0;
    for (i = 0; i < _entries.length; i++) {
      e = _entries[i];
      var d = lev(nq2, e.key, maxD);
      if (d <= maxD && (d < bfD || (d === bfD && e.w > bfW))) { bf = e.node; bfD = d; bfW = e.w; }
    }
    if (bf) {
      var sc = 55 - bfD * 5;
      return { node: bf, score: sc, suggestions: nearest(nq2, 3).filter(function (n) { return n.id !== bf.id; }).slice(0, 2) };
    }

    // 8) tokens (labels multi-palabra): todos los tokens de la consulta
    //    aparecen en el label — gana el label más corto (más específico)
    var qt = nq2.split(' ').filter(function (t) { return t.length > 1; });
    if (qt.length) {
      var bt = null, btLen = 1e9;
      (window.NODES || []).forEach(function (n) {
        var lt = norm(n.label);
        var ok = qt.every(function (t) { return lt.indexOf(t) >= 0; });
        if (ok && lt.length < btLen) { btLen = lt.length; bt = n; }
      });
      if (bt) return { node: bt, score: 45, suggestions: nearest(nq2, 3).filter(function (n) { return n.id !== bt.id; }).slice(0, 2) };
    }

    // nada confiable → solo sugerencias
    return { node: null, score: 0, suggestions: nearest(nq2, 3) };
  }

  // ── mensaje bilingüe de "no encontrado" con sugerencias ───────────────────
  function joinNames(names, o) {
    if (!names.length) return '';
    if (names.length === 1) return names[0];
    return names.slice(0, -1).join(', ') + ' ' + o + ' ' + names[names.length - 1];
  }

  function notFound(q) {
    var r = find(q);
    var sugg = (r.node ? [r.node] : []).concat(r.suggestions || []);
    if (!sugg.length) sugg = nearest(norm(String(q || '')), 3);
    // dedupe
    var seen = {}, list = [];
    sugg.forEach(function (n) { if (n && !seen[n.id]) { seen[n.id] = 1; list.push(n); } });
    list = list.slice(0, 3);
    var names = list.map(function (n) { return n.label; });
    var es = 'No encontré «' + String(q) + '».' + (names.length ? ' ¿Quisiste decir ' + joinNames(names, 'o') + '?' : '');
    var en = 'I couldn\'t find «' + String(q) + '».' + (names.length ? ' Did you mean ' + joinNames(names, 'or') + '?' : '');
    var text = lang() === 'en' ? en : es;
    return { es: es, en: en, text: text, spoken: text.replace(/[«»]/g, ''), suggestions: list };
  }

  window.KhipuResolve = { find: find, notFound: notFound, norm: norm, nearest: nearest, lang: lang };

  /* ==========================================================================
     window._surface(kind, arg) — TODO resultado AL FRENTE, un solo camino.
     ========================================================================== */

  function tab(t) { try { if (typeof window.switchTab === 'function') window.switchTab(t); } catch (e) {} }
  function defer(fn, ms) { setTimeout(function () { try { fn(); } catch (e) {} }, ms || 0); }

  // cierra los overlays que tapan (salvo el que vamos a usar).
  // OJO: NO usar window._xrayClose aquí — con la Cabina abierta ese helper
  // re-pinta el escenario a 'empty' y borraría lo que estamos por mostrar.
  function closeBlocking(except) {
    except = except || '';
    try { if (except !== 'xray') { var x = document.getElementById('xray-ov'); if (x) x.classList.remove('show'); } } catch (e) {}
    try { if (except !== 'dossier') { var f = document.getElementById('fc-ov'); if (f) f.classList.remove('show'); } } catch (e) {}
    try { if (except !== 'compare') { var c = document.getElementById('cmp-ov'); if (c) c.classList.remove('show'); } } catch (e) {}
    try { if (typeof window.closeSistema === 'function') window.closeSistema(); } catch (e) {}
    try { var xp = document.getElementById('xpl-ov'); if (xp) xp.style.display = 'none'; } catch (e) {}
  }

  function openDossier(x, raiseAboveCockpit) {
    if (!window.openFinCard) return false;
    try {
      window.openFinCard(x);
      var fc = document.getElementById('fc-ov');
      // la Cabina vive en z 7000 y el dossier en 6500: si la Cabina está
      // abierta lo subimos por encima para que NO quede atrás (bug real)
      if (fc) fc.style.zIndex = raiseAboveCockpit ? '7600' : '';
    } catch (e) { return false; }
    return true;
  }

  function openTrade(a) {
    // sin empresa → escenario del broker (cuenta/posiciones papel) en la Cabina
    if (!a || !a.ticker) {
      if (typeof window._openBrokerStage === 'function') { window._openBrokerStage(); return true; }
      return false;
    }
    // con empresa → trade-panel (z 9900) queda encima de todo, incluida la Cabina
    if (typeof window.openTradeModal !== 'function') return false;
    defer(function () { window.openTradeModal(a.id, a.ticker, a.label); }, 300);
    return true;
  }

  function surfaceTabInCockpit(t, ck) {
    if (t === 'map') { ck.stage('graph'); return true; }
    if (t === 'terminal') { ck.stage('terminal'); return true; }
    if (t === 'analysis') { ck.stage('insights'); return true; }
    if (t === 'canvas') { ck.stage('canvas'); return true; }
    if (t === 'crypto') { ck.stage('crypto'); return true; }   // cripto vive DENTRO de la Cabina (no la cierra → no calla a Bixby)
    ck.close();
    tab(t);
    return true;
  }

  window._surface = function (kind, arg) {
    var ck = window.BixbyCockpit;
    var inCk = !!(ck && ck.isOpen && ck.isOpen());

    if (kind === 'clear') { closeBlocking(''); return true; }

    // investigación profunda: SIEMPRE en la Cabina (su escenario la pinta)
    if (kind === 'deep') {
      closeBlocking('');
      if (ck) { ck.open(); ck.stage('deep', arg); return true; }
      return false;
    }

    if (inCk) {
      // ── Cabina abierta: todo va DENTRO de su escenario ──
      closeBlocking(kind === 'dossier' ? 'dossier' : '');
      switch (kind) {
        case 'xray': ck.stage('xray', arg); return true;
        case 'compare': ck.stage('compare', arg || {}); return true;
        case 'sim': ck.stage('sim', { id: arg && (arg.id || arg), kind: (arg && arg.kind) || 'collapse' }); return true;
        case 'stress':
          ck.stage('graph', arg);
          defer(function () { if (typeof window.activateStress === 'function') window.activateStress(arg); }, 320);
          return true;
        case 'graph': ck.stage('graph', arg); return true;
        case 'chart': ck.stage('terminal', { ticker: arg && (arg.ticker || arg) }); return true;
        case 'terminal': ck.stage('terminal', arg || {}); return true;
        case 'insights': ck.stage('insights'); return true;
        case 'canvas': ck.stage('canvas', arg); return true;
        case 'dossier': return openDossier(arg, true);
        case 'secondbrain': ck.stage('xray', arg); return true;   // la ficha rica dentro de la Cabina
        case 'trade': return openTrade(arg);
        case 'tab': return surfaceTabInCockpit(arg, ck);
      }
      return false;
    }

    // ── Cabina cerrada: cerrar lo que tapa y llevar la pestaña dueña al frente ──
    closeBlocking(kind);
    switch (kind) {
      case 'xray':
        if (window.openXRay) { window.openXRay(arg); return true; }
        return false;
      case 'compare':
        if (window.openCompare && arg) { window.openCompare(arg.a, arg.b); return true; }
        return false;
      case 'sim': {
        var sid = arg && (arg.id || arg);
        tab('map');
        defer(function () {
          if (typeof window.jumpTo === 'function' && sid) window.jumpTo(sid);
          if (arg && typeof arg.after === 'function') arg.after();
        }, 200);
        return true;
      }
      case 'stress':
        tab('map');
        defer(function () { if (typeof window.activateStress === 'function') window.activateStress(arg); }, 200);
        return true;
      case 'graph':
        tab('map');
        if (arg) defer(function () { if (typeof window.jumpTo === 'function') window.jumpTo(arg); }, 180);
        return true;
      case 'chart': {
        var cid = arg && arg.id, ctk = arg && arg.ticker;
        tab('map');
        defer(function () {
          if (typeof window.jumpTo === 'function' && cid) window.jumpTo(cid);
          if (ctk && typeof window.loadStockChart === 'function') setTimeout(function () { window.loadStockChart(cid, ctk); }, 350);
        }, 180);
        return true;
      }
      case 'terminal': {
        var tk = arg && (arg.ticker || arg);
        tab('terminal');
        defer(function () { if (tk && typeof tk === 'string' && window._termOpenTicker) window._termOpenTicker(tk); }, 250);
        return true;
      }
      case 'insights':
        tab('analysis');
        defer(function () { if (window.renderKhipuInsights) window.renderKhipuInsights(); }, 150);
        return true;
      case 'canvas':
        tab('canvas');
        defer(function () {
          var qi = document.getElementById('canvas-query');
          if (qi && arg) { qi.value = String(arg); if (typeof window.canvasGenerate === 'function') window.canvasGenerate(); }
        }, 280);
        return true;
      case 'dossier': return openDossier(arg, false);
      case 'secondbrain':
        if (typeof window._openSecondBrain === 'function') { tab('map'); defer(function () { window._openSecondBrain(arg); }, 150); return true; }
        return false;
      case 'trade': return openTrade(arg);
      case 'tab': tab(arg); return true;
    }
    return false;
  };
})();
