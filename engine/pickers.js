/* engine/pickers.js — opciones FIJAS en vez de texto libre (pedido de Fabrizio 2026-10-05:
   "donde se escriban cosas fijas como tickers de empresas no quiero que te deje escribir
   sino que te vaya recomendando en base a lo que escribes y sean fixed options").

   window.KhipuPick.attach(input, opts)   → selector con sugerencias; SOLO acepta opciones de la lista
     opts.kind   'entity' (empresas del grafo) | 'symbol' (tickers cotizados + cripto X/USD)
     opts.multi  true → lista separada por comas ("NVDA, AMD"); cada elemento validado
     opts.extras [{value, label, hint, icon}] opciones fijas arriba (p. ej. "💼 Mi cartera")
     opts.onPick(item) item = {value, label, id?, sym?, extra?}
     Tras elegir: input.dataset.pickValue (id o símbolo) / dataset.pickLabel. Texto que no está
     en la lista se rechaza al salir del campo (borde rojo + aviso bilingüe).
   window.KhipuPick.chatMenu(input, opts) → menú al escribir "/" o "@" en el chat de Khipu
     (comandos, analistas y luego empresas). Enter/Tab completa; Esc cierra.
   window.KhipuPick.search(q, kind, n)    → búsqueda reutilizable. */
(function () {
  'use strict';
  function en() { try { return (window.LANG || localStorage.getItem('eco_lang') || 'es') === 'en'; } catch (e) { return false; } }
  function L(es, e) { return en() ? e : es; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function fold(s) { return String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); }
  function sym(n) { return n && n.mkt ? String(n.mkt).split(/[\s·(]/)[0].toUpperCase() : ''; }

  // ── universo de opciones ──
  function entities() {
    var N = window.NODES || [];
    return N.filter(function (n) { return n && n.id && (!window.NODE_BY_ID || !window.NODE_BY_ID[n.id] || window.NODE_BY_ID[n.id].id === n.id); })
      .map(function (n) { return { value: n.id, id: n.id, label: n.label || n.id, sym: sym(n), hint: sym(n) }; });
  }
  var _cryptoCache = null;
  function cryptos() {
    if (_cryptoCache) return _cryptoCache;
    var C = window.CRYPTO_INTEL || {};
    _cryptoCache = Object.keys(C).map(function (k) {
      var c = C[k] || {}; var t = String(c.ticker || '').toUpperCase();
      return t ? { value: t + '/USD', sym: t + '/USD', label: (c.name || t) + ' (' + t + '/USD)', hint: L('cripto', 'crypto') } : null;
    }).filter(Boolean);
    return _cryptoCache;
  }
  function symbols() {
    var seen = {}, out = [];
    entities().forEach(function (e) { if (e.sym && !seen[e.sym]) { seen[e.sym] = 1; out.push({ value: e.sym, sym: e.sym, id: e.id, label: e.label, hint: e.sym }); } });
    cryptos().forEach(function (c) { if (!seen[c.sym]) { seen[c.sym] = 1; out.push(c); } });
    return out;
  }
  function universe(kind) { return kind === 'symbol' ? symbols() : entities(); }

  function search(q, kind, n) {
    n = n || 8;
    var f = fold(q).trim();
    var U = universe(kind);
    if (!f) return [];
    var scored = [];
    U.forEach(function (o) {
      var lab = fold(o.label), s = fold(o.sym), id = fold(o.id || o.value), sc = 0;
      if (s && s === f) sc = 100; else if (id === f || lab === f) sc = 95;
      else if (s && s.indexOf(f) === 0) sc = 80; else if (lab.indexOf(f) === 0) sc = 75;
      else if (lab.split(/[\s\-_.()]+/).some(function (w) { return w && w.indexOf(f) === 0; })) sc = 65;
      else if (f.length >= 3 && (lab.indexOf(f) >= 0 || id.indexOf(f) >= 0)) sc = 50;
      if (sc) scored.push([sc, o]);
    });
    if (scored.length < 3 && kind !== 'symbol' && window.KhipuResolve && f.length >= 3) {   // nombres raros / voz
      try {
        var r = window.KhipuResolve.find(q), extra = [];
        if (r && r.node) extra.push(r.node);
        (r && r.suggestions || []).forEach(function (x) { extra.push(x); });
        extra.forEach(function (x) {
          if (x && x.id && !scored.some(function (p) { return p[1].id === x.id; })) scored.push([40, { value: x.id, id: x.id, label: x.label || x.id, sym: sym(x), hint: sym(x) }]);
        });
      } catch (e) { /* sin resolutor */ }
    }
    scored.sort(function (a, b) { return b[0] - a[0] || a[1].label.length - b[1].label.length; });
    return scored.slice(0, n).map(function (p) { return p[1]; });
  }
  function exact(q, kind) {
    var f = fold(q).trim(); if (!f) return null;
    var hits = search(q, kind, 3);
    if (!hits.length) return null;
    var h = hits[0];
    if (fold(h.sym) === f || fold(h.label) === f || fold(h.id || '') === f || fold(h.value) === f) return h;
    return hits.length === 1 ? h : null;
  }

  // ── lista desplegable (una sola, flotante) ──
  var css = '.kpk-list{position:fixed;z-index:2147483000;background:#0d1424;border:1px solid rgba(122,158,255,.35);border-radius:10px;' +
    'box-shadow:0 12px 30px rgba(0,0,0,.45);max-height:300px;overflow:auto;padding:4px;min-width:220px;font:13px/1.35 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}' +
    '.kpk-it{display:flex;gap:8px;align-items:baseline;padding:7px 10px;border-radius:7px;cursor:pointer;color:#E8EDFB}' +
    '.kpk-it b{font-weight:600}.kpk-it span{color:#8E9AB8;font-size:12px;margin-left:auto;white-space:nowrap}' +
    '.kpk-it.on,.kpk-it:hover{background:rgba(0,224,255,.12)}' +
    '.kpk-hd{padding:5px 10px 3px;color:#7f8bab;font-size:11px;letter-spacing:.04em;text-transform:uppercase}' +
    '.kpk-bad{outline:2px solid #e23b3b !important;outline-offset:1px}' +
    // chip del agente en el campo del chat (como un conector): ícono + nombre (+ selector de cartera)
    '.kpk-chip{display:inline-flex;align-items:center;gap:6px;flex:0 0 auto;align-self:center;margin-right:6px;padding:3px 4px 3px 3px;border-radius:999px;' +
    'border:1px solid rgba(0,224,255,.45);background:rgba(0,224,255,.1);color:#9EEBFF;font:600 12px/1.2 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:60%}' +
    '.kpk-chip>i{font-style:normal;display:inline-flex;width:22px;height:22px;border-radius:50%;align-items:center;justify-content:center;background:rgba(0,224,255,.2);font-size:12px}' +
    '.kpk-chip>b{font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.kpk-chip select{background:#0d1424;color:#E8EDFB;border:1px solid rgba(122,158,255,.3);border-radius:7px;font:500 11.5px system-ui;max-width:180px;padding:2px 4px}' +
    '.kpk-chip button{border:none;background:transparent;color:#8E9AB8;cursor:pointer;font-size:13px;padding:0 4px;line-height:1}.kpk-chip button:hover{color:#FF8FA3}' +
    '@media(max-width:600px){.kpk-chip>b{display:none}.kpk-chip select{max-width:120px}}';   // la app es siempre oscura
  function ensureCss() {
    if (document.getElementById('kpk-css')) return;
    var st = document.createElement('style'); st.id = 'kpk-css'; st.textContent = css; document.head.appendChild(st);
  }
  var LIST = { el: null, items: [], idx: 0, owner: null, onPick: null };
  function listEl() {
    ensureCss();
    if (!LIST.el) {
      LIST.el = document.createElement('div'); LIST.el.className = 'kpk-list'; LIST.el.setAttribute('role', 'listbox'); LIST.el.style.display = 'none';
      LIST.el.addEventListener('mousedown', function (e) { e.preventDefault(); });   // no robar el foco al input
      document.body.appendChild(LIST.el);
    }
    return LIST.el;
  }
  function hide() { if (LIST.el) LIST.el.style.display = 'none'; LIST.items = []; LIST.owner = null; LIST.onPick = null; }
  function isOpen(input) { return !!(LIST.el && LIST.el.style.display !== 'none' && LIST.owner === input && LIST.items.length); }
  function show(input, items, onPick, header) {
    var el = listEl();
    LIST.items = items; LIST.idx = 0; LIST.owner = input; LIST.onPick = onPick;
    if (!items.length) { hide(); return; }
    el.innerHTML = (header ? '<div class="kpk-hd">' + esc(header) + '</div>' : '') + items.map(function (o, i) {
      return '<div class="kpk-it' + (i === 0 ? ' on' : '') + '" role="option" data-i="' + i + '">' + (o.icon ? esc(o.icon) + ' ' : '') +
        '<b>' + esc(o.label) + '</b>' + (o.hint ? '<span>' + esc(o.hint) + '</span>' : '') + '</div>';
    }).join('');
    el.querySelectorAll('.kpk-it').forEach(function (it) {
      it.addEventListener('click', function () { var o = LIST.items[+it.getAttribute('data-i')], cb = LIST.onPick; hide(); if (cb) cb(o); });
    });
    var r = input.getBoundingClientRect(), vh = window.innerHeight || 800;
    el.style.display = 'block';
    el.style.left = Math.max(4, r.left) + 'px';
    el.style.width = Math.max(220, r.width) + 'px';
    var below = vh - r.bottom, h = Math.min(300, el.scrollHeight);
    if (below < h + 8 && r.top > below) { el.style.top = ''; el.style.bottom = (vh - r.top + 4) + 'px'; }
    else { el.style.bottom = ''; el.style.top = (r.bottom + 4) + 'px'; }
  }
  function move(d) {
    if (!LIST.items.length) return;
    LIST.idx = (LIST.idx + d + LIST.items.length) % LIST.items.length;
    LIST.el.querySelectorAll('.kpk-it').forEach(function (it, i) { it.classList.toggle('on', i === LIST.idx); if (i === LIST.idx) it.scrollIntoView({ block: 'nearest' }); });
  }
  function pickCurrent() { var o = LIST.items[LIST.idx], cb = LIST.onPick; hide(); if (o && cb) cb(o); return !!o; }
  window.addEventListener('resize', hide);
  document.addEventListener('scroll', function (e) { if (LIST.el && !LIST.el.contains(e.target)) hide(); }, true);

  // ── selector con opciones fijas ──
  function attach(input, opts) {
    if (!input || input._kpk) return input;
    opts = opts || {};
    var kind = opts.kind === 'symbol' ? 'symbol' : 'entity', multi = !!opts.multi, extras = opts.extras || [];
    input._kpk = true;
    input.setAttribute('autocomplete', 'off'); input.setAttribute('spellcheck', 'false');
    input.setAttribute('role', 'combobox'); input.setAttribute('aria-autocomplete', 'list');
    if (!input.title) input.title = L('Escribe y elige de la lista', 'Type and pick from the list');
    function tokens() { return input.value.split(',').map(function (t) { return t.trim(); }); }
    function current() { return multi ? tokens().pop() : input.value.trim(); }
    function setChosen(o) {
      input.classList.remove('kpk-bad');
      if (multi) {
        var tk = tokens(); tk.pop();
        var val = kind === 'symbol' ? o.sym || o.value : o.value;
        if (tk.indexOf(val) < 0) tk.push(val);
        input.value = tk.filter(Boolean).join(', ') + ', ';
      } else {
        input.value = o.extra ? o.label : (kind === 'symbol' ? (o.sym || o.value) : o.label);
        input.dataset.pickValue = o.value; input.dataset.pickLabel = o.label;
      }
      if (opts.onPick) { try { opts.onPick(o); } catch (e) { /* el consumidor decide */ } }
    }
    function refresh() {
      var q = current();
      if (!multi) { delete input.dataset.pickValue; }
      var ex = extras.filter(function (x) { return !q || fold(x.label).indexOf(fold(q)) >= 0 || fold(x.value).indexOf(fold(q)) >= 0; })
        .map(function (x) { return { value: x.value, label: x.label, hint: x.hint, icon: x.icon, extra: true }; });
      var hits = q ? search(q, kind, 8) : [];
      var items = ex.concat(hits);
      if (!items.length && q) { show(input, [{ value: '', label: L('Sin coincidencias — prueba otro nombre o ticker', 'No match — try another name or ticker'), hint: '' }], function () {}); return; }
      show(input, items, setChosen, q ? '' : L('Opciones', 'Options'));
    }
    input.addEventListener('input', refresh);
    input.addEventListener('focus', function () { if (extras.length || current()) refresh(); });
    input.addEventListener('keydown', function (e) {
      if (!isOpen(input)) { if (e.key === 'ArrowDown') { refresh(); e.preventDefault(); } return; }
      if (e.key === 'ArrowDown') { move(1); e.preventDefault(); }
      else if (e.key === 'ArrowUp') { move(-1); e.preventDefault(); }
      else if (e.key === 'Enter' || e.key === 'Tab') { if (LIST.items[LIST.idx] && LIST.items[LIST.idx].value !== '') { e.preventDefault(); e.stopImmediatePropagation(); pickCurrent(); } }
      else if (e.key === 'Escape') { hide(); }
    }, true);
    input.addEventListener('blur', function () {
      setTimeout(function () {
        if (LIST.owner === input) hide();
        if (multi) {
          var ok = [], bad = [];
          tokens().filter(Boolean).forEach(function (t) {
            var h = exact(t, kind); if (h) { var v = kind === 'symbol' ? h.sym || h.value : h.value; if (ok.indexOf(v) < 0) ok.push(v); } else bad.push(t);
          });
          input.value = ok.join(', ');
          input.classList.toggle('kpk-bad', !!bad.length);
          input.title = bad.length ? L('Quité lo que no está en la lista: ', 'Removed what is not in the list: ') + bad.join(', ') : L('Escribe y elige de la lista', 'Type and pick from the list');
          return;
        }
        var q = input.value.trim();
        if (!q) { delete input.dataset.pickValue; input.classList.remove('kpk-bad'); return; }
        if (input.dataset.pickValue && q === (kind === 'symbol' ? input.dataset.pickValue : input.dataset.pickLabel)) return;
        var x = extras.filter(function (z) { return fold(z.label) === fold(q); })[0];
        var h = x ? { value: x.value, label: x.label, extra: true } : exact(q, kind);
        if (h) { setChosen(h); return; }
        input.classList.add('kpk-bad');
        input.title = L('Elige una opción de la lista', 'Pick an option from the list');
      }, 120);
    });
    return input;
  }
  // ¿el input tiene una opción VÁLIDA elegida? (para que los formularios no envíen texto libre)
  function value(input) {
    if (!input) return null;
    if (input.dataset.pickValue) return input.dataset.pickValue;
    var h = exact(input.value, input._kpkKind || 'entity');
    return h ? h.value : null;
  }

  // ── menú "/" y "@" del chat de Khipu ──
  var COMMANDS = [
    { c: '/cartera', ce: '/portfolio', es: 'pregunta sobre TU cartera (elige cuál; suma un @analista si quieres)', en: 'ask about YOUR portfolio (pick which; add an @analyst if you like)',
      i: '💼', n: 'Mi cartera', ne: 'My portfolio', portfolio: true },
    { c: '/investigar', ce: '/research', es: 'el equipo de investigación estudia una empresa', en: 'the research team studies a company', ent: true,
      i: '🔬', n: 'Equipo de investigación', ne: 'Research team' },
    { c: '/comite', ce: '/committee', es: 'el comité de inversión: veredicto sobre una empresa o tu cartera', en: 'the investment committee: verdict on a company or your portfolio', ent: true, cartera: true,
      i: '🏛', n: 'Comité de inversión', ne: 'Investment committee' },
    { c: '/ayuda', ce: '/help', es: 'todos los comandos', en: 'all the commands' },
  ];
  var ANALYSTS = [
    { c: '@cartera', ce: '@portfolio', es: 'usar TU cartera como contexto de la pregunta', en: 'use YOUR portfolio as the context of the question',
      i: '💼', n: 'Mi cartera', ne: 'My portfolio', portfolio: true },
    { c: '@fundamental', es: 'analista fundamental: balances y márgenes', en: 'fundamental analyst: financials and margins', i: '📊', n: 'Analista fundamental', ne: 'Fundamental analyst' },
    { c: '@tecnico', ce: '@technical', es: 'analista técnico: precio y tendencias', en: 'technical analyst: price and trends', i: '📈', n: 'Analista técnico', ne: 'Technical analyst' },
    { c: '@noticias', ce: '@news', es: 'analista de noticias', en: 'news analyst', i: '📰', n: 'Analista de noticias', ne: 'News analyst' },
    { c: '@cadena', ce: '@supply', es: 'analista de cadena de suministro', en: 'supply-chain analyst', i: '🔗', n: 'Analista de cadena', ne: 'Supply-chain analyst' },
    { c: '@geopolitico', ce: '@geo', es: 'analista geopolítico', en: 'geopolitical analyst', i: '🌐', n: 'Analista geopolítico', ne: 'Geopolitical analyst' },
    { c: '@macro', es: 'analista macroeconómico', en: 'macro analyst', i: '🏦', n: 'Analista macro', ne: 'Macro analyst' },
    { c: '@todos', ce: '@all', es: 'responden todos los analistas', en: 'all analysts answer', i: '👥', n: 'Todos los analistas', ne: 'All analysts' },
    { c: '@investigacion', ce: '@research', es: 'lanza la investigación de una empresa', en: 'starts research on a company', ent: true, i: '🔬', n: 'Equipo de investigación', ne: 'Research team' },
    { c: '@comite', ce: '@committee', es: 'el comité (empresa o "mi cartera")', en: 'the committee (company or "my portfolio")', cartera: true, i: '🏛', n: 'Comité de inversión', ne: 'Investment committee' },
  ];
  function chatMenu(input, opts) {
    if (!input || input._kpkChat) return input;
    input._kpkChat = true;
    opts = opts || {};
    function state() {
      var v = input.value, pos = input.selectionStart == null ? v.length : input.selectionStart;
      var before = v.slice(0, pos);
      var m = before.match(/^(\/\S*)$/) || before.match(/(?:^|\s)(@\S*)$/);
      if (m) return { mode: 'cmd', tok: m[1], start: pos - m[1].length, pos: pos };
      // tras un comando/analista que pide empresa: "/investigar nv", "@fundamental tsm"
      var m2 = before.match(/^(\/\S+|@\S+)\s+([^\s,][^,]*)?$/);
      if (m2) {
        var head = fold(m2[1]), def = COMMANDS.concat(ANALYSTS).filter(function (d) { return fold(d.c) === head || fold(d.ce || '') === head; })[0];
        // solo comandos que piden EMPRESA (no la pregunta libre a un analista) y mientras se escribe la
        // primera palabra: ya elegida ("…NVDA ") la lista no vuelve a abrirse y Enter envía
        var tk = m2[2] || '';
        if (def && (def.ent || def.cartera) && !/\s$/.test(tk) && tk.trim().split(/\s+/).length <= 3)
          return { mode: 'ent', def: def, tok: tk, start: pos - tk.length, pos: pos };
      }
      return null;
    }
    function replace(st, text) {
      var v = input.value;
      input.value = v.slice(0, st.start) + text + v.slice(st.pos);
      var p = st.start + text.length; try { input.setSelectionRange(p, p); } catch (e) {}
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.focus();
    }
    function refresh() {
      var st = state();
      if (!st) { if (LIST.owner === input) hide(); return; }
      if (st.mode === 'cmd') {
        var defs = st.tok.charAt(0) === '/' ? COMMANDS : ANALYSTS, f = fold(st.tok);
        var items = defs.filter(function (d) { return fold(d.c).indexOf(f) === 0 || fold(d.ce || '').indexOf(f) === 0; })
          .map(function (d) { return { value: en() && d.ce ? d.ce : d.c, label: en() && d.ce ? d.ce : d.c, hint: en() ? d.en : d.es, def: d }; });
        show(input, items, function (o) {
          // agentes SIN empresa (comité de cartera, analistas): el token sale del texto y queda como CHIP
          // (como un conector); solo se escribe la pregunta. Los que piden empresa siguen en el texto.
          if (o.def && o.def.portfolio) { replace(st, ''); setCtx(); return; }                 // 💼 cartera = CONTEXTO
          if (o.def && (isSeat(o.def) || (o.def.cartera && input._ctxPf && /comite|committee/.test(fold(o.def.c))))) {
            replace(st, ''); input._agentTok = o.value; chipKey = ''; chipRefresh(); return;           // 🤖 quién responde
          }
          replace(st, o.value + ' ');
        },
          st.tok.charAt(0) === '/' ? L('Comandos', 'Commands') : L('Analistas', 'Analysts'));
        return;
      }
      var q = st.tok.trim();
      var items2 = [];
      if (st.def.cartera && (!q || fold(L('mi cartera', 'my portfolio')).indexOf(fold(q)) === 0 || 'cartera'.indexOf(fold(q)) === 0))
        items2.push({ value: L('mi cartera', 'my portfolio'), label: L('mi cartera', 'my portfolio'), icon: '💼', hint: L('analiza tu cartera', 'analyze your portfolio') });
      if (q) items2 = items2.concat(search(q, 'entity', 7));
      if (!items2.length) { if (LIST.owner === input) hide(); return; }
      show(input, items2, function (o) { replace(st, (o.icon ? o.value : (o.sym || o.label)) + ' '); }, q ? '' : L('Elige', 'Pick'));
    }
    // ── CHIPS (como conectores): 💼 CONTEXTO (tu cartera) + 🤖 AGENTE (quién responde) ──
    // 2026-10-05 (feedback): elegir la cartera NO debe llamar al comité ni quitar al analista elegido.
    // Ambos chips son independientes y quedan puestos entre preguntas hasta tocar ✕.
    var bar = null, chipKey = '';
    function defOf(tok) {
      var t = fold(tok || '');
      return COMMANDS.concat(ANALYSTS).filter(function (x) { return fold(x.c) === t || fold(x.ce || '') === t; })[0] || null;
    }
    function textDef() {      // agente escrito a mano al inicio del texto
      var m = input.value.match(/^\s*([\/@][^\s]+)/);
      var d = m ? defOf(m[1]) : null;
      return d && d.i && !d.portfolio ? d : null;
    }
    function isSeat(d) { return d && d.i && !d.portfolio && !d.ent && !d.cartera && !/^@(todos|all)$/.test(d.c); }
    function agentDef() { return input._agentTok ? defOf(input._agentTok) : textDef(); }
    function chipRefresh() {
      var K = window.KhipuChat, ctx = input._ctxPf || '', ad = agentDef();
      var srcs = (K && K.pfSources) ? K.pfSources() : [];
      var key = ctx + '|' + (ad ? ad.c : '') + '|' + srcs.length;
      if (key === chipKey) return;
      chipKey = key;
      if (!ctx && !ad) { if (bar && bar.parentNode) bar.parentNode.removeChild(bar); bar = null; return; }
      ensureCss();
      if (!bar) { bar = document.createElement('span'); bar.style.cssText = 'display:inline-flex;gap:6px;align-items:center;flex:0 1 auto;min-width:0'; }
      if (!bar.parentNode && input.parentNode) input.parentNode.insertBefore(bar, input);
      var h = '';
      if (ctx) {
        h += '<span class="kpk-chip" data-chip="ctx"><i>💼</i><select title="' + esc(L('¿Sobre qué cartera?', 'Which portfolio?')) + '">' +
          srcs.map(function (x) { return '<option value="' + esc(x.key) + '"' + (x.key === ctx ? ' selected' : '') + '>' + esc(x.label) + '</option>'; }).join('') +
          '</select><button type="button" title="' + esc(L('Quitar la cartera', 'Remove the portfolio')) + '">✕</button></span>';
      }
      if (ad) {
        h += '<span class="kpk-chip" data-chip="agent"><i>' + esc(ad.i) + '</i><b>' + esc(en() ? ad.ne : ad.n) + '</b>' +
          '<button type="button" title="' + esc(L('Quitar el agente', 'Remove the agent')) + '">✕</button></span>';
      } else if (ctx) {
        h += '<span class="kpk-chip" data-chip="agent" style="opacity:.75" title="' + esc(L('Escribe @ para que responda un analista concreto', 'Type @ to have a specific analyst answer')) + '"><i>💬</i><b>Khipu</b></span>';
      }
      bar.innerHTML = h;
      var cs = bar.querySelector('[data-chip="ctx"] select');
      if (cs) cs.addEventListener('change', function () { input._ctxPf = cs.value; if (K && K.pfSelect) K.pfSelect(cs.value); chipKey = ''; chipRefresh(); input.focus(); });
      var cx = bar.querySelector('[data-chip="ctx"] button');
      if (cx) cx.addEventListener('click', function () { input._ctxPf = null; chipKey = ''; chipRefresh(); input.focus(); });
      var ax = bar.querySelector('[data-chip="agent"] button');
      if (ax) ax.addEventListener('click', function () {
        if (input._agentTok) input._agentTok = null; else input.value = input.value.replace(/^\s*[\/@][^\s]+\s*/, '');
        chipKey = ''; input.dispatchEvent(new Event('input', { bubbles: true })); input.focus();
      });
    }
    function setCtx() {
      var K = window.KhipuChat, sel = K && K.pfSelected ? K.pfSelected() : null;
      input._ctxPf = sel ? sel.key : ((K && K.pfSources && K.pfSources()[0]) || {}).key || 'market';
      chipKey = ''; chipRefresh();
    }
    // al ENVIAR: los chips se traducen al texto que entiende el enrutador del chat
    //   cartera + analista → "/cartera @geo …" · cartera sola → "/cartera …" · cartera + comité → "/cartera @comite …"
    function flushTok() {
      var K = window.KhipuChat, tok = input._agentTok, body = input.value.replace(/^\s+/, '');
      if (!tok) { var m = body.match(/^([\/@][^\s]+)\s*/), d0 = m ? defOf(m[1]) : null; if (d0 && d0.i && !d0.portfolio) { tok = m[1]; body = body.slice(m[0].length); } }
      if (input._ctxPf) {
        if (K && K.pfSelect) K.pfSelect(input._ctxPf);
        var d = tok ? defOf(tok) : null;
        var who = d && (isSeat(d) || /comite|committee/.test(fold(d.c))) ? (/comite|committee/.test(fold(d.c)) ? '@comite' : d.c) + ' ' : '';
        input.value = '/cartera ' + who + body;
      } else if (tok) {
        input.value = tok + ' ' + body;
      }
    }
    input.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !isOpen(input)) flushTok(); }, true);
    var sendBtn = input.parentNode && input.parentNode.querySelector('#bcp-send, #bcc-send, [data-send]');
    if (sendBtn) sendBtn.addEventListener('click', flushTok, true);
    input.addEventListener('input', chipRefresh);
    input.addEventListener('focus', function () { chipKey = ''; chipRefresh(); });
    setInterval(function () { if (bar) chipRefresh(); }, 600);
    input.addEventListener('input', refresh);
    input.addEventListener('click', refresh);
    input.addEventListener('keydown', function (e) {
      if (!isOpen(input)) return;
      if (e.key === 'ArrowDown') { move(1); e.preventDefault(); e.stopImmediatePropagation(); }
      else if (e.key === 'ArrowUp') { move(-1); e.preventDefault(); e.stopImmediatePropagation(); }
      else if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); e.stopImmediatePropagation(); pickCurrent(); }
      else if (e.key === 'Escape') { e.stopImmediatePropagation(); hide(); }
    }, true);
    input.addEventListener('blur', function () { setTimeout(function () { if (LIST.owner === input) hide(); }, 150); });
    return input;
  }

  // {name, emoji} del agente con el que empieza un texto ("@fundamental …", "/investigar …"), para la burbuja
  function agentOf(text) {
    var m = String(text || '').match(/^\s*([\/@][^\s]+)/);
    if (!m) return null;
    var t = fold(m[1]), d = COMMANDS.concat(ANALYSTS).filter(function (x) { return x.i && (fold(x.c) === t || fold(x.ce || '') === t); })[0];
    return d ? { name: en() ? d.ne : d.n, emoji: d.i } : null;
  }
  window.KhipuPick = { attach: attach, chatMenu: chatMenu, search: search, exact: exact, value: value, hide: hide, agentOf: agentOf };
})();
