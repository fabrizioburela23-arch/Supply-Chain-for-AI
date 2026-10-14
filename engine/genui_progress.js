/* engine/genui_progress.js — RESPUESTAS VISUALES PROGRESIVAS (F3, docs/CHAT_UI_GENERATIVA.md §6): el motor del chat que
   pinta los bloques provisionales y hace ATERRIZAR la respuesta final sobre ellos.

   PEREZOSO (lote J, revisión F3): lo carga KhipuGenUI.loadExtras (engine/genui.js, EXTRAS) junto a los gráficos, solo con
   la bandera kh_genui encendida (o al llegar el primer sobre): sin la bandera ningún usuario descarga estos ~12 KB.
   engine/khipu_chat.js conserva la identidad de un bloque (KhipuChat.keyOf = core/khipu_chat._ui_key), el sondeo y los
   ayudantes de movimiento que usa también la fila de pasos (KhipuChat._f3); este archivo los lee a la hora de usarlos.

   Los bloques que el servidor ya armó con las herramientas que volvieron (GET …/progress?since=, kblocks/1 parcial) se
   pintan ANTES que el texto, cada uno con KhipuGenUI.renderBlock. Esqueleto con la forma y la altura del bloque
   (height() con un contenido TÍPICO); esqueleto → bloque = fundido cruzado en el mismo sitio; lo de abajo se desliza
   con FLIP (solo transform). Al llegar la respuesta, el sobre FINAL manda: el mismo bloque (misma identidad) se reusa
   sin repintarse, el texto se revela, la fila de pasos se pliega y lo listo que el sobre no usa pasa a «Más datos de
   esta respuesta». Las acciones de los bloques (📊, 🔬…) llegan SIEMPRE al onAction de quien pintó la respuesta (la
   Cabina): se enlazan tarde (el._kcAct), también en los bloques reusados o plegados. Un error después de haber
   mostrado bloques los deja a la vista con el aviso arriba (nunca desaparecen de golpe). Reducir movimiento = todo de
   golpe. */
(function (W) {
  'use strict';
  function K() { return W.KhipuChat || {}; }
  function H() { return K()._f3 || {}; }
  function L(es, en) { var f = H().L; return f ? f(es, en) : es; }
  // contenido TÍPICO de un bloque que aún no llegó (solo para medir su altura con height(); nunca se pinta). La cascada
  // típica es la de un choque real (TSMC): 4 saltos (los dos primeros con sus empresas), rivales y la línea de cartera
  var TYPICAL = { 'metric.tiles': { items: [0, 0, 0, 0] },
    'impact.cascade': { hops: [{ entities: [0, 0, 0, 0, 0, 0, 0, 0] }, { entities: [0, 0, 0, 0, 0, 0, 0] }, {}, {}], least_hit_rivals: [0, 0, 0, 0], portfolio: {} },
    'graph.mini': { nodes: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] }, ranking: { items: [0, 0, 0, 0, 0] } };
  // las acciones de un bloque provisional van a quien pinte la respuesta (fillReply fija el._kcAct): enlace TARDÍO
  function act(el) { return function (a, b) { return el && el._kcAct ? el._kcAct(a, b) : false; }; }

  // esqueleto → bloque: el esqueleto se apaga ENCIMA del bloque, en el mismo sitio (solo opacidad)
  function _xfade(old, nu, oh) {
    if (typeof old.animate !== 'function') return;
    old.classList.add('kc-xf'); old.classList.remove('kc-in'); old.style.height = oh + 'px';
    old.setAttribute('aria-hidden', 'true');
    nu.appendChild(old);
    var a = old.animate([{ opacity: 1 }, { opacity: 0 }], { duration: H().dur(nu, 2) || 1, easing: 'ease-out', fill: 'forwards' });
    a.onfinish = function () { if (old.parentNode) old.parentNode.removeChild(old); };
  }
  /* progressBlocks(el, parcial) — aplica los bloques nuevos (por seq) en la burbuja pendiente, cada uno por su
     identidad: nuevo → entra al final; esqueleto → listo con fundido cruzado; listo → listo al instante. */
  function progressBlocks(el, part) {
    var G = W.KhipuGenUI, F = H(), keyOf = K().keyOf;
    if (!el || !el._kgShell || !G || !keyOf || !part || part.v !== G.V || !Array.isArray(part.blocks)) return 0;
    var body = el.querySelector('.kc-body'); if (!body) return 0;
    // gráficos aún sin cargar (genui_charts.js / genui_shapes.js son perezosos): el MISMO parcial al llegar
    if (G.extrasReady && !G.extrasReady() && G.loadExtras && !part._kcWait) {
      part._kcWait = 1;
      G.loadExtras().then(function () { if (el.classList.contains('kc-pending')) progressBlocks(el, part); });
      return 0;
    }
    var box = el._kcProv;
    if (!box) { box = W.document.createElement('div'); box.className = 'kc-prov'; body.appendChild(box); el._kcProv = box; }
    var stick = F.stick(el), red = F.reduced(), w = box.clientWidth || body.clientWidth || 600, n = 0, cmp = w < 520;
    var kids = [], rects = [];
    for (var c = box.firstChild; c; c = c.nextSibling) { kids.push(c); rects.push(c.getBoundingClientRect()); }
    part.blocks.slice(0, 14).forEach(function (b) {
      if (!b || typeof b.type !== 'string' || typeof b.id !== 'string') return;
      var k = keyOf(b), old = null;
      for (var x = box.firstChild; x; x = x.nextSibling) if (x._kcKey === k) { old = x; break; }
      if (old && old._kcBlock && old._kcBlock.seq != null && old._kcBlock.seq === b.seq) return;
      var sk = !!(old && old._kcBlock && old._kcBlock.state === 'planned' && b.state !== 'planned');
      var pb = W.document.createElement('div'); pb.className = 'kc-pb'; pb._kcKey = k; pb._kcBlock = b;
      if (!G.renderBlock(pb, b, { instant: !!(old && !sk), compact: cmp, onAction: act(el) })) return;
      // el esqueleto RESERVA la altura del bloque: la del renderizador (height()) con un contenido típico
      if (b.state === 'planned') { try { pb.querySelector('[data-kg-id]').style.minHeight = G._u.height({ type: b.type, state: 'ready', data: TYPICAL[b.type] || {} }, w) + 'px'; } catch (e) {} }
      if (old) { var oh = old.offsetHeight; box.replaceChild(pb, old); if (sk && !red) _xfade(old, pb, oh); }
      else { box.appendChild(pb); if (!red) pb.classList.add('kc-in'); }
      n++;
    });
    if (n) { F.flip(kids, rects); if (stick) F.follow(el); }
    return n;
  }
  // revelado del texto que YA llegó completo (§6.3): ~60 caracteres por fotograma, tope 900 ms; la altura ya es la
  // final (nada se mueve): cada palabra pasa de oculta a visible, sin animaciones; un reloj de respaldo lo termina
  function _reveal(el) {
    var d = W.document, tw = d.createTreeWalker(el, 4, null), ws = [], ns = [], n, tot = 0, i = 0;
    while ((n = tw.nextNode())) ns.push(n);
    ns.forEach(function (tn) {
      var f = d.createDocumentFragment();
      tn.nodeValue.split(/(\s+)/).forEach(function (p) {
        if (!p) return;
        if (/^\s+$/.test(p)) f.appendChild(d.createTextNode(p));
        else { var s = d.createElement('span'); s.className = 'kc-w'; s.textContent = p; ws.push(s); tot += p.length; f.appendChild(s); }
      });
      tn.parentNode.replaceChild(f, tn);
    });
    var per = Math.max(60, Math.ceil(tot / 54)), all = function () { while (i < ws.length) ws[i++].className = ''; };
    (function step() {
      for (var c = 0; i < ws.length && c < per; i++) { c += ws[i].textContent.length; ws[i].className = ''; }
      if (i < ws.length) { if (W.requestAnimationFrame) W.requestAnimationFrame(step); else all(); }
    })();
    setTimeout(all, 1000);
  }
  // la fila de pasos se pliega EN SU SITIO (misma altura): «✓ 3 pasos · 2,1 s»
  function _foldSteps(el, d) {
    var th = el.querySelector('.kc-think'); if (!th) return;
    var en = (H().lang ? H().lang() : 'es') === 'en', tools = Array.isArray(d.tools_used) ? d.tools_used : [], n = tools.length, s = (+d.elapsed_ms || 0) / 1000;
    var txt = '✓ ' + (n ? n + ' ' + (n === 1 ? L('paso', 'step') : L('pasos', 'steps')) : L('Respuesta', 'Answer')) +
      (s ? ' · ' + s.toFixed(1).replace('.', en ? '.' : ',') + ' s' : '');
    th.classList.add('kc-fold'); th.removeAttribute('aria-live'); th.setAttribute('role', 'note');
    var tt = th.querySelector('.kc-tt'), ex = th.querySelector('.kc-el');
    if (tt) tt.textContent = txt;
    if (ex) ex.textContent = '';
    th.title = tools.map(function (t) { return K().toolLabel ? K().toolLabel(t && t.name) : String(t && t.name); }).join(' · ');
  }
  function _factsOf(env) {
    var f = {};
    ((env && env.blocks) || []).forEach(function (b) { if (b && b.type === 'sources' && b.data && Array.isArray(b.data.items)) b.data.items.forEach(function (it) { if (it && it.id) f[it.id] = it; }); });
    return f;
  }
  // el bloque reusado se pintó antes de que llegaran las fuentes: sus chips [F#] toman el nombre y la hora del sobre
  // final, en su sitio (lo mismo que mostraría un bloque recién pintado)
  function _patchFacts(el, facts) {
    [].forEach.call(el.querySelectorAll('.kg-src[data-kg-fact]'), function (c) {
      var id = c.getAttribute('data-kg-fact'), f = facts[id], b = c.firstChild;
      if (!f || !f.label || !b || b.nodeName !== 'B') return;
      while (b.nextSibling) c.removeChild(b.nextSibling);
      c.appendChild(W.document.createTextNode(f.label + (f.as_of && K().relTime ? ' · ' + K().relTime(f.as_of) : '')));
      c.setAttribute('data-kg-tip', id + ' · ' + f.label);
    });
  }
  // «Más datos de esta respuesta»: bloques que ya se vieron y que el sobre final no usa (nunca desaparecen de golpe)
  function _moreFold(el, blocks, facts, cmp) {
    var G = W.KhipuGenUI, d = W.document, det = d.createElement('details'), sm = d.createElement('summary');
    det.className = 'kc-more';
    sm.textContent = L('Más datos de esta respuesta', 'More data from this answer') + ' (' + blocks.length + ')';
    det.appendChild(sm);
    blocks.forEach(function (b) { var t = d.createElement('div'); t.className = 'kc-pb'; G.renderBlock(t, b, { instant: true, facts: facts, compact: cmp, onAction: act(el) }); det.appendChild(t); });
    return det;
  }
  /* land(el, d, opts) — la respuesta FINAL aterriza sobre la burbuja que ya muestra bloques provisionales: nada se
     reemplaza de golpe. → el .kg-root final (o null: queda el texto de siempre). */
  function land(el, d, opts) {
    var G = W.KhipuGenUI, F = H(), KC = K(), keyOf = KC.keyOf, main = el.querySelector('.kc-main'), body = main && main.querySelector('.kc-body');
    // lo provisional que ya está a la vista y su lugar en pantalla (ANTES de tocar nada), para deslizarlo (FLIP)
    var prev = {}, keys = [], box = el._kcProv;
    for (var p = box && box.firstChild; p; p = p.nextSibling) {
      var sec = p.querySelector('[data-kg-id]'), st = p._kcBlock && p._kcBlock.state;
      if (sec && (st === 'ready' || st === 'stale') && !prev[p._kcKey]) { prev[p._kcKey] = { el: sec, b: p._kcBlock, r: sec.getBoundingClientRect() }; keys.push(p._kcKey); }
    }
    var tmp = W.document.createElement('div'); tmp.innerHTML = KC.replyHTML(d, opts);
    var nm = tmp.querySelector('.kc-main'), nb = nm && nm.querySelector('.kc-body');
    if (!body || !nb) { el.innerHTML = KC.replyHTML(d, opts); return F.genui(el, d, opts); }
    el.classList.add('kc-landed');
    var av = el.querySelector('.kc-av'), nav = tmp.querySelector('.kc-av');
    if (av && nav && av.innerHTML !== nav.innerHTML) el.replaceChild(nav, av);   // un analista en persona: SU mascota
    _foldSteps(el, d);
    var who = nm.querySelector('.kc-who'); if (who) main.insertBefore(who, body);
    var facts = _factsOf(d.ui), moved = [], rects = [], live = true, cmp = (body.clientWidth || 600) < 520;
    var reuse = function (b) {
      var k = keyOf(b), o = live && prev[k]; if (!o) return null;
      delete prev[k];
      var x = o.el;
      if (!F.same(o.b, b)) {          // mismo bloque, otra versión (p. ej. ya con su [F#]): se pinta al instante, sin entrada
        var t = W.document.createElement('div'); G.renderBlock(t, b, { instant: true, facts: facts, compact: cmp, onAction: act(el) });
        x = t.querySelector('[data-kg-id]'); if (!x) return null;
      }
      else _patchFacts(x, facts);
      moved.push(x); rects.push(o.r);
      return x;
    };
    // ¿ya estaba a la vista? (sin consumirlo): varias fichas que el final agrupa en UNA fila se pintan sin entrada
    reuse.has = function (b) { return !!(live && b && prev[keyOf(b)]); };
    el._kcProv = null;
    var root = F.genui(el, d, Object.assign({}, opts, { reuse: reuse }));
    live = false;
    F.flip(moved, rects);
    // a «Más datos» solo va lo que el sobre final NO trae (varias fichas seguidas se pintan juntas en una fila nueva)
    var inFinal = {}; d.ui.blocks.forEach(function (b) { if (b && b.type) inFinal[keyOf(b)] = 1; });
    var left = keys.filter(function (k) { return prev[k] && !inFinal[k]; }).map(function (k) { return prev[k].b; });
    if (left.length && root) main.appendChild(_moreFold(el, left, facts, cmp));
    for (var c = nb.nextSibling; c; c = nb.nextSibling) main.appendChild(c);
    if (root && !F.reduced()) [].forEach.call(root.querySelectorAll(':scope > [data-kg-type=text]'), _reveal);
    return root;
  }
  /* keepOnError(el, aviso) — falló la respuesta (plazo del cliente, 5xx, red) DESPUÉS de mostrar bloques listos: el
     aviso reemplaza la fila de pasos y los bloques quedan a la vista (los esqueletos sin llenar se quitan). false si
     no había nada listo (fillError pinta el aviso de siempre). */
  function keepOnError(el, noteHTML) {
    var box = el && el._kcProv, ready = 0;
    if (!box) return false;
    for (var p = box.firstChild; p; p = p.nextSibling) { var st = p._kcBlock && p._kcBlock.state; if (st === 'ready' || st === 'stale') ready++; }
    if (!ready) return false;
    [].slice.call(box.children).forEach(function (p) { if (p._kcBlock && p._kcBlock.state === 'planned') box.removeChild(p); });
    [].slice.call(box.querySelectorAll('.kc-xf')).forEach(function (x) { if (x.parentNode) x.parentNode.removeChild(x); });   // fundidos a medias
    var main = el.querySelector('.kc-main'), th = main && main.querySelector('.kc-think');
    if (!main) return false;
    var t = W.document.createElement('div'); t.innerHTML = noteHTML;
    var note = t.firstChild; if (!note) return false;
    if (th) main.replaceChild(note, th); else main.insertBefore(note, main.firstChild);
    el._kcProv = null;
    return true;
  }

  W.KhipuGenUIProgress = { progressBlocks: progressBlocks, land: land, keepOnError: keepOnError, reveal: _reveal,
    foldSteps: _foldSteps, TYPICAL: TYPICAL };
})(typeof window !== 'undefined' ? window : globalThis);
