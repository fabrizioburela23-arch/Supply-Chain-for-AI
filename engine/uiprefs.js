/* engine/uiprefs.js — LA INTERFAZ APRENDE DE CADA PERSONA (2026-11-21, pedido de Fabrizio: «que la interfaz aprenda
   de cada persona»).

   Qué aprende: qué TIPOS de bloque visual (gráfico de línea, cifras, tabla, barras…) muestra Khipu y cuáles TOCA la
   persona (clic, tecla). Un bloque que se muestra seguido y nunca se toca baja; uno que siempre se toca sube.
   Dónde vive: localStorage `kh_ui_prefs` (y se sincroniza entre tus dispositivos con engine/sync.js). No sale nada
   más: ni textos, ni empresas, ni montos — solo contadores por tipo de bloque.
   Para qué sirve: cada pregunta al chat lleva `context.ui_prefs = {more:[tipos], less:[tipos]}`; el servidor
   (core/genui.clean_prefs) lo valida y (1) se lo dice a la IA para que elija el "layout" y (2) ordena los bloques
   cuando la IA no eligió. Solo PRESENTACIÓN: nunca cambia una cifra, una recomendación ni una orden.
   Olvida solo: los contadores se reducen a la mitad al pasar de 400 (lo reciente pesa más).

   API: window.KhipuUiPrefs = { ctx(), summary(lang), reset(), _state() } */
(function () {
  'use strict';
  var W = window, KEY = 'kh_ui_prefs', MAXN = 400;
  var MIN_SHOWN = 3, LESS_SHOWN = 6;

  function fresh() { return { v: 1, shown: {}, used: {} }; }
  function load() {
    try { var o = JSON.parse(localStorage.getItem(KEY) || 'null'); if (o && o.v === 1 && o.shown && o.used) return o; } catch (e) {}
    return fresh();
  }
  var st = load(), timer = null, seenEnv = (typeof WeakSet === 'function') ? new WeakSet() : null, lastUse = {};

  function save() {
    clearTimeout(timer);
    timer = setTimeout(function () { try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) {} }, 600);
  }
  function total(m) { var n = 0; for (var k in m) if (Object.prototype.hasOwnProperty.call(m, k)) n += m[k]; return n; }
  function halve(m) { for (var k in m) if (Object.prototype.hasOwnProperty.call(m, k)) { m[k] = Math.floor(m[k] / 2); if (!m[k]) delete m[k]; } }
  function okType(t) { return typeof t === 'string' && /^[a-z][a-z.]{1,30}$/.test(t) && t !== 'text'; }
  function bump(m, t) {
    if (!okType(t)) return;
    m[t] = (m[t] || 0) + 1;
    if (total(st.shown) > MAXN) { halve(st.shown); halve(st.used); }
    save();
  }

  // lo que se MUESTRA: cada sobre kblocks/1 que pinta el chat (una vez por sobre, aunque se repinte)
  function hook() {
    var G = W.KhipuGenUI;
    if (!G || typeof G.renderAnswer !== 'function') return false;
    if (G._uiprefs) return true;
    var orig = G.renderAnswer;
    G.renderAnswer = function (host, env) {
      var r = orig.apply(this, arguments);
      try {
        if (env && Array.isArray(env.blocks) && !(seenEnv && seenEnv.has(env))) {
          if (seenEnv) seenEnv.add(env);
          var types = {};
          env.blocks.forEach(function (b) { if (b && okType(b.type)) types[b.type] = 1; });
          Object.keys(types).forEach(function (t) { bump(st.shown, t); });
        }
      } catch (e) {}
      return r;
    };
    G._uiprefs = 1;
    return true;
  }
  if (!hook()) {
    var tries = 0, iv = setInterval(function () { if (hook() || ++tries > 40) clearInterval(iv); }, 500);
  }

  // lo que se USA: clic o tecla dentro de un bloque (una vez cada 20 s por bloque)
  function onUse(e) {
    try {
      var el = e.target && e.target.closest && e.target.closest('[data-kg-type]');
      if (!el) return;
      var t = el.getAttribute('data-kg-type'), id = (el.getAttribute('data-kg-id') || '') + '|' + t, now = Date.now();
      if (lastUse[id] && now - lastUse[id] < 20000) return;
      lastUse[id] = now;
      bump(st.used, t);
    } catch (x) {}
  }
  try { W.document.addEventListener('click', onUse, true); W.document.addEventListener('keydown', onUse, true); } catch (e) {}

  // otra pestaña / otro dispositivo (sync.js) escribió la clave → recargar
  try { W.addEventListener('storage', function (e) { if (e.key === KEY) st = load(); }); } catch (e) {}

  function rates() {
    var out = [];
    Object.keys(st.shown).forEach(function (t) {
      var s = st.shown[t] || 0, u = Math.min(st.used[t] || 0, s);
      if (s >= MIN_SHOWN) out.push({ type: t, shown: s, used: u, rate: (u + 1) / (s + 2) });
    });
    return out.sort(function (a, b) { return b.rate - a.rate || b.shown - a.shown; });
  }

  // lo que va al servidor: solo tipos (nada personal)
  function ctx() {
    var r = rates();
    if (!r.length) return null;
    var more = r.filter(function (x) { return x.used >= 2 && x.rate >= 0.4; }).slice(0, 4).map(function (x) { return x.type; });
    var less = r.filter(function (x) { return x.shown >= LESS_SHOWN && x.used === 0; }).slice(-4).map(function (x) { return x.type; });
    if (!more.length && !less.length) return null;
    return { more: more, less: less };
  }

  var NAMES = {
    'chart.line': ['gráficos de evolución', 'trend charts'], 'chart.bar': ['gráficos de barras', 'bar charts'],
    'metric.tiles': ['cifras clave', 'key figures'], 'table': ['tablas', 'tables'], 'company.card': ['fichas de empresa', 'company cards'],
    'news.list': ['noticias', 'news'], 'graph.mini': ['mapas de conexiones', 'connection maps']
  };
  function nm(t, en) { var n = NAMES[t]; return n ? n[en ? 1 : 0] : t; }
  function summary(lang) {
    var en = lang === 'en', c = ctx();
    if (!c) return en ? 'Still learning what you like to see.' : 'Todavía estoy aprendiendo qué te gusta ver.';
    var parts = [];
    if (c.more.length) parts.push((en ? 'You use: ' : 'Usas más: ') + c.more.map(function (t) { return nm(t, en); }).join(', '));
    if (c.less.length) parts.push((en ? 'You skip: ' : 'Casi no miras: ') + c.less.map(function (t) { return nm(t, en); }).join(', '));
    return parts.join(' · ');
  }
  function reset() { st = fresh(); try { localStorage.removeItem(KEY); } catch (e) {} }

  W.KhipuUiPrefs = { ctx: ctx, summary: summary, reset: reset, _state: function () { return st; }, _hook: hook };
})();
