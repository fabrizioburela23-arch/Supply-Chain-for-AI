/* engine/a2ui.js — LECTOR A2UI v1.0 de Khipus OS (2026-11-25, pedido de Fabrizio: «interfaz interactiva lo más avanzada
   posible, con futuro, rápida, útil y adaptable»).

   A2UI (Google, Apache-2.0) = un agente describe la interfaz en JSON (componentes por id + un modelo de datos) y cada
   app la dibuja con sus piezas. Khipus ya hablaba esa idea (kblocks/1); ahora además:
     · el servidor puede entregar la misma respuesta en A2UI (core/genui/a2ui.py, context.ui_format='a2ui'), y
     · Khipus OS sabe PINTAR A2UI de cualquier agente (el nuestro o uno externo) con este lector.

   Soporta: createSurface · updateComponents · updateDataModel (JSON Pointer, null borra) · deleteSurface; catálogo básico
   (Text, Row, Column, List, Card, Button, Divider, Image, Tabs, TextField, CheckBox, Slider, ChoicePicker) + KhipusBlock
   (nuestros bloques verificados, pintados con KhipuGenUI.renderBlock); valores literales / {"@path"} / {"@call"}
   (formatString, formatNumber, formatCurrency, formatDate, pluralize, required, and, or, not); hijos por lista o por
   plantilla {path, componentId}; botones con evento (→ opts.onAction con el mensaje `action` del estándar) u openUrl
   (solo http/https, con clic). Entradas con enlace en los dos sentidos: escribir actualiza el modelo.
   Seguridad: nunca innerHTML con datos (todo textContent), sin scripts, URLs filtradas.

   Bandera: localStorage kh_a2ui = '1' → el chat pide A2UI y lo pinta este lector (beta; por defecto, el de siempre).
   API: window.KhipuA2UI = { on(), set(on), process(host, msgs, opts) → surface, get(id), update(id, path, value) } */
(function () {
  'use strict';
  var W = window, V = '1.0';
  var BASIC = 'https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json', KHIPUS = 'urn:khipus:a2ui:catalog:1.0';
  var surfaces = {};

  // ?a2ui=1 / ?a2ui=0 en la dirección enciende o apaga la prueba (sin consola)
  try { var _q = /[?&]a2ui=([01])/.exec(W.location && W.location.search || ''); if (_q) { if (_q[1] === '1') localStorage.setItem('kh_a2ui', '1'); else localStorage.removeItem('kh_a2ui'); } } catch (e) {}
  function on() { try { return localStorage.getItem('kh_a2ui') === '1'; } catch (e) { return false; } }
  function set(v) { try { if (v) localStorage.setItem('kh_a2ui', '1'); else localStorage.removeItem('kh_a2ui'); } catch (e) {} }
  function lang() { try { return W.LANG === 'en' || localStorage.getItem('eco_lang') === 'en' ? 'en' : 'es'; } catch (e) { return 'es'; } }
  function el(tag, cls) { var n = W.document.createElement(tag); if (cls) n.className = cls; return n; }

  // ── modelo de datos: JSON Pointer ──
  function ptr(p) { return String(p || '').split('/').slice(1).map(function (s) { return s.replace(/~1/g, '/').replace(/~0/g, '~'); }); }
  function abs(path, scope) {
    path = String(path == null ? '' : path);
    if (path.charAt(0) === '/') return path;
    return (scope || '') + (path ? '/' + path : '');
  }
  function getAt(model, path) {
    var cur = model, ks = ptr(path);
    for (var i = 0; i < ks.length; i++) { if (cur == null) return undefined; cur = cur[ks[i]]; }
    return cur;
  }
  function setAt(s, path, value) {
    if (!path || path === '/') { s.model = value == null ? {} : value; return; }
    var ks = ptr(path), cur = s.model;
    for (var i = 0; i < ks.length - 1; i++) {
      if (cur[ks[i]] == null || typeof cur[ks[i]] !== 'object') cur[ks[i]] = /^\d+$/.test(ks[i + 1]) ? [] : {};
      cur = cur[ks[i]];
    }
    var k = ks[ks.length - 1];
    if (value === null) { if (Array.isArray(cur)) cur.splice(+k, 1); else delete cur[k]; } else cur[k] = value;
  }

  // ── valores dinámicos y funciones del catálogo básico ──
  function num(x) { var n = Number(x); return isFinite(n) ? n : null; }
  function loc() { return lang() === 'en' ? 'en-US' : 'es-PE'; }
  var FN = {
    formatString: function (a, s, scope) {
      return String(a.value == null ? '' : a.value).replace(/(\\)?\$\{([^}]*)\}/g, function (m, esc, p) {
        if (esc) return m.slice(1);
        var v = getAt(s.model, abs(p, scope)); return v == null ? '' : String(v);
      });
    },
    formatNumber: function (a) { var n = num(a.value); if (n == null) return '—'; var d = a.decimals != null ? +a.decimals : 2;
      return n.toLocaleString(loc(), { minimumFractionDigits: a.decimals != null ? d : 0, maximumFractionDigits: d, useGrouping: a.grouping !== false }); },
    formatCurrency: function (a) { var n = num(a.value); if (n == null) return '—';
      try { return n.toLocaleString(loc(), { style: 'currency', currency: String(a.currency || 'USD').slice(0, 3) }); } catch (e) { return n.toFixed(2) + ' ' + (a.currency || 'USD'); } },
    formatDate: function (a) { var d = new Date(a.value); if (isNaN(d)) return String(a.value || ''); return d.toLocaleDateString(loc(), { dateStyle: 'medium' }); },
    pluralize: function (a) { var n = num(a.value); var o = a.options || a; return (n === 1 ? (o.one || o.other) : (n === 0 && o.zero) || o.other) || ''; },
    required: function (a) { var v = a.value; return { valid: !(v == null || v === '' || (Array.isArray(v) && !v.length)) }; },
    not: function (a) { return !truthy(a.value); },
    and: function (a) { return (a.values || []).every(truthy); },
    or: function (a) { return (a.values || []).some(truthy); },
    openUrl: function (a) { var u = String(a.url || ''); if (/^https?:\/\//i.test(u)) { try { W.open(u, '_blank', 'noopener'); } catch (e) {} } return null; }
  };
  function truthy(v) { return v && typeof v === 'object' && 'valid' in v ? !!v.valid : !!v; }
  function val(x, s, scope) {
    if (x && typeof x === 'object' && !Array.isArray(x)) {
      if ('@path' in x) return getAt(s.model, abs(x['@path'], scope));
      if ('@call' in x) {
        var f = FN[x['@call']], args = {};
        Object.keys(x.args || {}).forEach(function (k) { var v = x.args[k]; args[k] = Array.isArray(v) ? v.map(function (y) { return val(y, s, scope); }) : val(v, s, scope); });
        return f ? f(args, s, scope) : undefined;
      }
    }
    return x;
  }
  function str(x, s, scope) { var v = val(x, s, scope); return v == null ? '' : (typeof v === 'object' ? JSON.stringify(v) : String(v)); }

  // ── texto: **negrita** y saltos, sin HTML ──
  function rich(node, text) {
    String(text).split('\n').forEach(function (line, i) {
      if (i) node.appendChild(el('br'));
      line.split(/(\*\*[^*]+\*\*)/).forEach(function (part) {
        if (/^\*\*[^*]+\*\*$/.test(part)) { var b = el('b'); b.textContent = part.slice(2, -2); node.appendChild(b); }
        else if (part) node.appendChild(W.document.createTextNode(part));
      });
    });
  }

  function sendAction(s, comp, ev, scope) {
    var ctx = {};
    Object.keys(ev.context || {}).forEach(function (k) { ctx[k] = val(ev.context[k], s, scope); });
    var msg = { version: V, action: { name: String(ev.name || ''), surfaceId: s.id, sourceComponentId: comp.id,
      timestamp: new Date().toISOString(), context: ctx } };
    if (ev.userMessage != null) msg.action.userMessage = str(ev.userMessage, s, scope);
    if (s.opts.sendDataModel) msg.metadata = { dataModel: s.model };
    try { if (s.opts.onAction) s.opts.onAction(msg); } catch (e) {}
    return msg;
  }

  function bindInput(s, comp, scope) {
    var b = comp.value;
    return function (v) { if (b && typeof b === 'object' && '@path' in b) { setAt(s, abs(b['@path'], scope), v); if (s.opts.onChange) try { s.opts.onChange(s.id, abs(b['@path'], scope), v); } catch (e) {} } };
  }

  var R = {
    Text: function (c, s, sc) { var n = el('div', 'a2-text' + (c.variant === 'caption' ? ' a2-cap' : '')); rich(n, str(c.text, s, sc)); return n; },
    Row: function (c, s, sc) { return box('a2-row', c, s, sc); },
    Column: function (c, s, sc) { return box('a2-col', c, s, sc); },
    List: function (c, s, sc) { return box(c.direction === 'horizontal' ? 'a2-row a2-list' : 'a2-col a2-list', c, s, sc); },
    Card: function (c, s, sc) { var n = el('div', 'a2-card'); kid(n, c.child, s, sc); return n; },
    Divider: function (c) { return el('hr', 'a2-div' + (c.axis === 'vertical' ? ' a2-vdiv' : '')); },
    Image: function (c, s, sc) { var u = str(c.url, s, sc); if (!/^https?:\/\//i.test(u)) return null;
      var n = el('img', 'a2-img a2-' + (c.variant || 'mediumFeature')); n.src = u; n.alt = str(c.description, s, sc); n.loading = 'lazy'; return n; },
    Button: function (c, s, sc) {
      var n = el('button', 'a2-btn a2-' + (c.variant || 'default')); n.type = 'button'; kid(n, c.child, s, sc);
      n.addEventListener('click', function () {
        var a = c.action || {};
        if (a.event) sendAction(s, c, a.event, sc);
        else if (a.functionCall) val(a.functionCall, s, sc);
      });
      return n;
    },
    Tabs: function (c, s, sc) {
      var n = el('div', 'a2-tabs'), bar = el('div', 'a2-row a2-tabbar'), body = el('div', 'a2-tabbody'), tabs = c.tabs || [];
      function pick(i) { body.textContent = ''; kid(body, tabs[i] && tabs[i].child, s, sc);
        Array.prototype.forEach.call(bar.children, function (b, j) { b.classList.toggle('on', j === i); }); }
      tabs.forEach(function (t, i) { var b = el('button', 'a2-tab'); b.type = 'button'; b.textContent = str(t.title, s, sc); b.addEventListener('click', function () { pick(i); }); bar.appendChild(b); });
      n.appendChild(bar); n.appendChild(body); if (tabs.length) pick(0); return n;
    },
    TextField: function (c, s, sc) {
      var n = el('label', 'a2-field'), lab = el('span', 'a2-cap'); lab.textContent = str(c.label, s, sc);
      var long = c.variant === 'longText', i = el(long ? 'textarea' : 'input', 'a2-in');
      if (!long) i.type = c.variant === 'number' ? 'number' : c.variant === 'obscured' ? 'password' : 'text';
      i.value = str(c.value, s, sc); if (c.placeholder) i.placeholder = str(c.placeholder, s, sc);
      var w = bindInput(s, c, sc); i.addEventListener('input', function () { w(c.variant === 'number' ? num(i.value) : i.value); });
      n.appendChild(lab); n.appendChild(i); return n;
    },
    CheckBox: function (c, s, sc) {
      var n = el('label', 'a2-check'), i = el('input'); i.type = 'checkbox'; i.checked = !!val(c.value, s, sc);
      var w = bindInput(s, c, sc); i.addEventListener('change', function () { w(i.checked); });
      var t = el('span'); t.textContent = str(c.label, s, sc); n.appendChild(i); n.appendChild(t); return n;
    },
    Slider: function (c, s, sc) {
      var n = el('label', 'a2-field'), lab = el('span', 'a2-cap'), i = el('input', 'a2-in'), out = el('b');
      i.type = 'range'; i.min = val(c.min, s, sc) || 0; i.max = val(c.max, s, sc); if (c.steps) i.step = (i.max - i.min) / val(c.steps, s, sc);
      i.value = val(c.value, s, sc) || 0; out.textContent = i.value; lab.textContent = str(c.label, s, sc);
      var w = bindInput(s, c, sc); i.addEventListener('input', function () { out.textContent = i.value; w(num(i.value)); });
      n.appendChild(lab); n.appendChild(i); n.appendChild(out); return n;
    },
    ChoicePicker: function (c, s, sc) {
      var n = el('div', 'a2-row a2-chips'), cur = val(c.value, s, sc), sel = Array.isArray(cur) ? cur.slice() : [], multi = c.variant === 'multipleSelection';
      var w = bindInput(s, c, sc);
      (val(c.options, s, sc) || []).forEach(function (o) {
        var v = o && typeof o === 'object' ? o.value : o, b = el('button', 'a2-chip'); b.type = 'button';
        b.textContent = o && typeof o === 'object' ? str(o.label, s, sc) : String(o); b.classList.toggle('on', sel.indexOf(v) >= 0);
        b.addEventListener('click', function () {
          var k = sel.indexOf(v); if (k >= 0) sel.splice(k, 1); else { if (!multi) sel = []; sel.push(v); }
          Array.prototype.forEach.call(n.children, function (x) { x.classList.toggle('on', false); });
          w(sel.slice()); paint(s);
        });
        n.appendChild(b);
      });
      return n;
    },
    KhipusBlock: function (c, s, sc) {
      var blk = val(c.block, s, sc), G = W.KhipuGenUI, n = el('div', 'a2-kb');
      var alt = function () { var t = el('div', 'a2-text'); t.textContent = str(c.alt, s, sc) || (blk && blk.alt && (blk.alt[lang()] || blk.alt.es)) || ''; n.appendChild(t); };
      if (!blk || !G || !G.renderBlock) { alt(); return n; }
      var draw = function () { try { if (!G.renderBlock(n, blk, { compact: !!c.compact, facts: s.facts })) alt(); } catch (e) { alt(); } };
      if (G.extrasReady && !G.extrasReady() && G.loadExtras && /^(chart|geo)/.test(blk.type || '')) { alt(); G.loadExtras().then(draw); } else draw();
      return n;
    }
  };

  function box(cls, c, s, sc) {
    var n = el('div', cls);
    if (c.justify) n.style.justifyContent = { spaceBetween: 'space-between', spaceAround: 'space-around', spaceEvenly: 'space-evenly', start: 'flex-start', end: 'flex-end' }[c.justify] || c.justify;
    if (c.align) n.style.alignItems = { start: 'flex-start', end: 'flex-end' }[c.align] || c.align;
    var ch = c.children;
    if (Array.isArray(ch)) ch.forEach(function (id) { kid(n, id, s, sc); });
    else if (ch && typeof ch === 'object' && ch.componentId) {
      var base = abs(ch.path, sc), items = getAt(s.model, base);
      (Array.isArray(items) ? items.map(function (x, i) { return i; }) : Object.keys(items || {})).forEach(function (k) { kid(n, ch.componentId, s, base + '/' + k); });
    }
    return n;
  }
  function kid(parent, id, s, sc) {
    if (id == null) return;
    var c = s.comps[id];
    if (!c || s._depth > 40) return;
    s._depth++;
    var f = R[c.component], node = null;
    try { node = f ? f(c, s, sc) : null; } catch (e) { node = null; }
    s._depth--;
    if (!node) return;
    if (c.weight) node.style.flex = String(+c.weight || 1);
    node.setAttribute('data-a2-id', String(id));
    parent.appendChild(node);
  }
  function paint(s) {
    if (!s.host) return;
    s._depth = 0;
    s.host.textContent = '';
    var root = el('div', 'a2-surface kos-themed');
    root.setAttribute('data-a2-surface', s.id);
    kid(root, 'root', s, '');
    s.host.appendChild(root);
  }

  function process(host, msgs, opts) {
    ensureStyles();
    var last = null;
    (Array.isArray(msgs) ? msgs : [msgs]).forEach(function (m) {
      if (!m || typeof m !== 'object' || String(m.version || V).charAt(0) !== '1') return;
      var c = m.createSurface, u = m.updateComponents, d = m.updateDataModel, x = m.deleteSurface, s;
      if (c && c.surfaceId) {
        s = surfaces[c.surfaceId] = { id: c.surfaceId, catalogId: c.catalogId || BASIC, comps: {}, model: c.dataModel || {}, host: host, opts: opts || {} };
        (c.components || []).forEach(function (k) { if (k && k.id) s.comps[k.id] = k; });
        s.opts.sendDataModel = !!c.sendDataModel; last = s; paint(s);
      } else if (u && surfaces[u.surfaceId]) {
        s = surfaces[u.surfaceId]; (u.components || []).forEach(function (k) { if (k && k.id) s.comps[k.id] = k; }); last = s; paint(s);
      } else if (d && surfaces[d.surfaceId]) {
        s = surfaces[d.surfaceId]; setAt(s, d.path || '/', d.value); last = s; paint(s);
      } else if (x && surfaces[x.surfaceId]) {
        s = surfaces[x.surfaceId]; if (s.host) s.host.textContent = ''; delete surfaces[x.surfaceId];
      }
    });
    return last;
  }
  function update(id, path, value) { return process(null, { version: V, updateDataModel: { surfaceId: id, path: path, value: value } }); }

  var _css = false;
  function ensureStyles() {
    if (_css || !W.document || !W.document.head) return; _css = true;
    var st = el('style');
    st.textContent = '.a2-surface{display:flex;flex-direction:column;gap:10px;font:inherit;color:var(--os-ink,inherit)}' +
      '.a2-row{display:flex;flex-direction:row;gap:8px;flex-wrap:wrap}.a2-col{display:flex;flex-direction:column;gap:6px}' +
      '.a2-card{border:1px solid var(--os-line,rgba(127,127,127,.25));border-radius:12px;padding:12px;background:var(--os-surface-2,transparent)}' +
      '.a2-cap{font-size:.82em;opacity:.72}.a2-text{line-height:1.5}.a2-div{border:0;border-top:1px solid var(--os-line,rgba(127,127,127,.25));width:100%}' +
      '.a2-btn{font:600 13px inherit;border-radius:999px;padding:6px 12px;cursor:pointer;border:1px solid var(--os-line,rgba(127,127,127,.3));background:transparent;color:inherit}' +
      '.a2-primary{background:var(--os-accent,#2F6BEA);color:#fff;border-color:transparent}.a2-borderless{border-color:transparent;padding:4px 6px;text-align:left}' +
      '.a2-img{max-width:100%;border-radius:8px}.a2-icon{width:20px}.a2-avatar{width:40px;height:40px;border-radius:50%}' +
      '.a2-field{display:flex;flex-direction:column;gap:4px}.a2-in{font:inherit;padding:6px 8px;border-radius:8px;border:1px solid var(--os-line,rgba(127,127,127,.3));background:transparent;color:inherit}' +
      '.a2-chip,.a2-tab{border-radius:999px;padding:4px 10px;border:1px solid var(--os-line,rgba(127,127,127,.3));background:transparent;color:inherit;cursor:pointer}' +
      '.a2-chip.on,.a2-tab.on{background:var(--os-accent,#2F6BEA);color:#fff;border-color:transparent}.a2-check{display:flex;gap:6px;align-items:center}';
    W.document.head.appendChild(st);
  }

  // el chat: con la bandera, una respuesta que trae A2UI se pinta con este lector (los botones vuelven al chat)
  function hook() {
    var G = W.KhipuGenUI;
    if (!G || typeof G.renderAnswer !== 'function') return false;
    if (G._a2ui) return true;
    var orig = G.renderAnswer;
    G.renderAnswer = function (host, env, opts) {
      if (on() && opts && Array.isArray(opts.a2ui) && opts.a2ui.length) {
        var oa = opts.onAction;
        var s = process(host, opts.a2ui, { onAction: function (m) {
          var cx = (m.action || {}).context || {};
          if (oa && cx.kind) oa({ kind: cx.kind, entity: cx.entity ? { id: cx.entity } : null, window: cx.window, lat: cx.lat, lon: cx.lon });
        } });
        if (s) return host.firstChild;
      }
      return orig.apply(this, arguments);
    };
    G._a2ui = 1;
    return true;
  }
  if (!hook()) { var tries = 0, iv = setInterval(function () { if (hook() || ++tries > 40) clearInterval(iv); }, 500); }

  W.KhipuA2UI = { V: V, BASIC: BASIC, KHIPUS: KHIPUS, on: on, set: set, process: process, update: update,
    get: function (id) { return surfaces[id] || null; }, _fn: FN };
})();
