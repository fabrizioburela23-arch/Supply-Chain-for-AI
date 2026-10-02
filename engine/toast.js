/* ============================================================================
   engine/toast.js — NOTIFICACIONES y CONFIRMACIÓN de órdenes (pedido de
   Fabrizio 2026-10-02: "que te avise cuando estás comprando con una
   notificación pop up o vendiendo").

   UN solo lugar para:
   · window.KhipuToast.show({kind, title, body|html, mode, timeout, actions})
       kind: 'buy' | 'sell' | 'success' | 'info' | 'warn' | 'error'
       mode: 'paper' | 'live' | 'sim' (cartera local) → insignia OBLIGATORIA
             🧪 SIMULADO / 🔴 DINERO REAL. Sin mode → sin insignia (avisos
             que no son órdenes).
       timeout: ms (0 = fija hasta cerrarla). Devuelve un id.
     .update(id, opts) · .dismiss(id) · .clear()
   · KhipuToast.confirm(opts) → Promise<boolean>: ventana modal genérica.
   · KhipuToast.confirmOrder(order, opts) → Promise<boolean>: resumen de la
       orden (lado, activo, cantidad/monto, tipo, vigencia, monto estimado,
       cuenta 🧪/🔴). NADA se envía aquí: el que llama envía SOLO si resuelve
       true. opts.amounts=[100,500…] → fichas de monto (cambian order.notional).
   · KhipuToast.order.sending(o) / .result(o, r, id) / .watch(o, data, id):
       ciclo de vida de una orden de la cuenta de la casa (/api/trade/order):
       enviando → aceptada / rechazada (texto del server tal cual) / ambigua /
       duplicada → EJECUTADA (sondeo ligero de /api/trade/history ≤ 60 s).
   Reglas: bilingüe ES/EN (window.LANG / eco_lang); cifras SOLO de lo que
   devuelve el bróker o de lo que el usuario escribió (nunca inventadas);
   accesible (role=status/alert, diálogo con foco atrapado, Esc cancela).
   Idempotente: si el archivo se carga dos veces no se redefine.
   ============================================================================ */
(function () {
  'use strict';
  if (window.KhipuToast && window.KhipuToast.__v) return;

  /* ── idioma ─────────────────────────────────────────────────────────── */
  function en() {
    try { return String(window.LANG || localStorage.getItem('eco_lang') || 'es').slice(0, 2) === 'en'; }
    catch (e) { return false; }
  }
  function L(es, eng) { return en() ? eng : es; }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function num(v) { var n = +v; return isFinite(n) ? n : null; }
  // $ con 2 decimales (≥ $1) o hasta 6 (centavos de cripto)
  function money(v) {
    var n = num(v); if (n == null) return '—';
    var a = Math.abs(n), d = a > 0 && a < 1 ? 6 : 2;
    return (n < 0 ? '-$' : '$') + a.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: d });
  }
  function qtyFmt(v) {
    var n = num(v); if (n == null) return '—';
    return n.toLocaleString('en-US', { maximumFractionDigits: 6 });
  }

  /* ── estilos (una vez) ──────────────────────────────────────────────── */
  var CSS = [
    '#kht-stack{position:fixed;top:64px;right:16px;z-index:13000;display:flex;flex-direction:column;gap:10px;',
    '  width:372px;max-width:calc(100vw - 24px);pointer-events:none}',
    '.kht{--k:#7C8CFF;position:relative;pointer-events:auto;display:grid;grid-template-columns:28px 1fr 22px;gap:10px;align-items:start;',
    '  padding:12px 12px 14px 12px;border-radius:12px;background:#11151D;color:#E8EAF0;',
    '  border:1px solid rgba(255,255,255,.10);border-left:3px solid var(--k);',
    '  box-shadow:0 10px 32px rgba(0,0,0,.45),0 2px 6px rgba(0,0,0,.3);overflow:hidden;',
    "  font:400 13px/1.45 'Geist','Inter',system-ui,sans-serif;animation:kht-in .22s ease-out}",
    '.kht.out{animation:kht-out .18s ease-in forwards}',
    '@keyframes kht-in{from{opacity:0;transform:translateX(16px)}to{opacity:1;transform:none}}',
    '@keyframes kht-out{to{opacity:0;transform:translateX(16px)}}',
    '.kht-buy,.kht-success{--k:#2EBD85}.kht-sell,.kht-error{--k:#F6465D}.kht-warn{--k:#F0A92E}.kht-info{--k:#8B8CF6}',
    '.kht-ico{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;',
    '  font-size:13px;font-weight:800;color:var(--k);background:color-mix(in srgb,var(--k) 16%,transparent)}',
    '.kht-ico.spin::before{content:"";width:14px;height:14px;border-radius:50%;border:2px solid color-mix(in srgb,var(--k) 30%,transparent);',
    '  border-top-color:var(--k);animation:kht-spin .7s linear infinite}',
    '@keyframes kht-spin{to{transform:rotate(360deg)}}',
    '.kht-main{min-width:0}',
    '.kht-top{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:2px}',
    '.kht-title{font-weight:650;font-size:13.5px;color:#F3F4F8;letter-spacing:-.005em}',
    '.kht-body{color:#A9AFBE;font-size:12.5px;overflow-wrap:anywhere}',
    '.kht-body b{color:#E8EAF0;font-weight:600}',
    ".kht-num{font-family:'JetBrains Mono',ui-monospace,monospace;font-variant-numeric:tabular-nums;font-size:12px;color:#E8EAF0}",
    '.kht-actions{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap}',
    '.kht-actions button{font-weight:600;font-size:12px;line-height:1;font-family:inherit;padding:6px 10px;border-radius:7px;cursor:pointer;',
    '  border:1px solid rgba(255,255,255,.14);background:rgba(255,255,255,.05);color:#E8EAF0}',
    '.kht-actions button:hover{background:rgba(255,255,255,.1)}',
    '.kht-x{width:22px;height:22px;border:0;background:none;color:#7D8496;font-size:17px;line-height:1;cursor:pointer;border-radius:6px;padding:0}',
    '.kht-x:hover,.kht-x:focus-visible{color:#E8EAF0;background:rgba(255,255,255,.08)}',
    '.kht-bar{position:absolute;left:0;right:0;bottom:0;height:2px;background:rgba(255,255,255,.04)}',
    '.kht-bar i{display:block;height:100%;width:100%;background:var(--k);opacity:.55;transform-origin:left}',
    /* insignia OBLIGATORIA de modo */
    '.kht-mode{display:inline-flex;align-items:center;gap:4px;font-weight:800;font-size:10px;line-height:1;font-family:inherit;letter-spacing:.06em;',
    '  padding:4px 8px;border-radius:999px;white-space:nowrap}',
    '.kht-mode.paper{background:rgba(255,179,0,.13);color:#FFB300;border:1px solid rgba(255,179,0,.38)}',
    '.kht-mode.live{background:rgba(246,70,93,.16);color:#FF6B7D;border:1px solid rgba(246,70,93,.55)}',
    /* diálogo de confirmación */
    '#khm-ov{position:fixed;inset:0;z-index:12500;display:flex;align-items:center;justify-content:center;padding:20px;',
    '  background:rgba(3,6,12,.68);backdrop-filter:blur(3px);-webkit-backdrop-filter:blur(3px);animation:khm-fade .15s ease-out}',
    '@keyframes khm-fade{from{opacity:0}to{opacity:1}}',
    ".khm{width:440px;max-width:100%;max-height:calc(100vh - 40px);overflow:auto;background:#11151D;color:#E8EAF0;",
    '  border:1px solid rgba(255,255,255,.12);border-radius:16px;box-shadow:0 24px 60px rgba(0,0,0,.6);padding:20px 20px 18px;',
    "  font:400 13.5px/1.5 'Geist','Inter',system-ui,sans-serif;outline:none;animation:khm-up .18s ease-out}",
    '@keyframes khm-up{from{opacity:0;transform:translateY(10px) scale(.98)}to{opacity:1;transform:none}}',
    '.khm-hd{display:flex;align-items:center;gap:8px;margin-bottom:12px}',
    '.khm-side{font-weight:800;font-size:11px;line-height:1;font-family:inherit;letter-spacing:.08em;padding:6px 10px;border-radius:999px}',
    '.khm-side.buy{color:#2EBD85;background:rgba(46,189,133,.14);border:1px solid rgba(46,189,133,.4)}',
    '.khm-side.sell{color:#F6465D;background:rgba(246,70,93,.14);border:1px solid rgba(246,70,93,.45)}',
    '.khm-side.info{color:#A5A6FF;background:rgba(139,140,246,.14);border:1px solid rgba(139,140,246,.4)}',
    '.khm-x{margin-left:auto;width:30px;height:30px;border-radius:8px;border:1px solid rgba(255,255,255,.12);background:none;color:#9097A8;font-size:18px;line-height:1;cursor:pointer}',
    '.khm-x:hover,.khm-x:focus-visible{color:#E8EAF0;background:rgba(255,255,255,.07)}',
    '.khm-title{font-size:18px;font-weight:700;letter-spacing:-.01em;margin:0 0 2px;color:#F5F6FA}',
    '.khm-sub{color:#9097A8;font-size:13px;margin-bottom:14px}',
    '.khm-rows{margin:0;border-top:1px solid rgba(255,255,255,.07)}',
    '.khm-rows>div{display:flex;justify-content:space-between;gap:14px;padding:9px 0;border-bottom:1px solid rgba(255,255,255,.07)}',
    '.khm-rows dt{color:#9097A8;font-size:12.5px}',
    '.khm-rows dd{margin:0;text-align:right;color:#E8EAF0;font-weight:550}',
    ".khm .num{font-family:'JetBrains Mono',ui-monospace,monospace;font-variant-numeric:tabular-nums}",
    '.khm-total{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin:14px 0 4px;padding:12px 14px;border-radius:12px;',
    '  background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08)}',
    '.khm-total span{color:#9097A8;font-size:12.5px}',
    '.khm-total b{font-size:20px;font-weight:700;color:#F5F6FA}',
    '.khm-chips{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 2px}',
    ".khm-chips button{font-weight:600;font-size:12.5px;line-height:1;font-family:'JetBrains Mono',ui-monospace,monospace;padding:7px 12px;border-radius:999px;cursor:pointer;",
    '  border:1px solid rgba(255,255,255,.14);background:transparent;color:#B7BDCB}',
    '.khm-chips button[aria-pressed="true"]{border-color:var(--kc,#2EBD85);color:var(--kc,#2EBD85);background:color-mix(in srgb,var(--kc,#2EBD85) 13%,transparent)}',
    '.khm-warn{margin-top:12px;padding:10px 12px;border-radius:10px;font-size:12.5px;line-height:1.5;',
    '  background:rgba(246,70,93,.10);border:1px solid rgba(246,70,93,.4);color:#FFB3BD}',
    '.khm-warn b{color:#FF6B7D}',
    '.khm-note{margin-top:10px;color:#7D8496;font-size:12px;line-height:1.5}',
    '.khm-ck{display:flex;gap:8px;align-items:flex-start;margin-top:12px;font-size:12.5px;color:#D5D9E3;cursor:pointer}',
    '.khm-ck input{margin-top:2px;accent-color:#F6465D;width:16px;height:16px}',
    '.khm-btns{display:flex;gap:10px;margin-top:18px}',
    '.khm-btns button{flex:1;padding:12px 14px;border-radius:10px;font-weight:700;font-size:14px;line-height:1;font-family:inherit;cursor:pointer;letter-spacing:.01em}',
    '.khm-cancel{background:rgba(255,255,255,.05);color:#E8EAF0;border:1px solid rgba(255,255,255,.14)}',
    '.khm-cancel:hover{background:rgba(255,255,255,.09)}',
    '.khm-ok{border:0;color:#fff;background:#6E6FE0}',
    '.khm-ok.buy{background:#1F9D6C}.khm-ok.sell{background:#D63A50}',
    '.khm-ok:hover{filter:brightness(1.08)}',
    '.khm-ok:disabled{opacity:.45;cursor:not-allowed;filter:none}',
    '.khm button:focus-visible,.khm-chips button:focus-visible,.kht button:focus-visible{outline:2px solid #A5A6FF;outline-offset:2px}',
    /* teléfono: arriba a lo ancho y el diálogo como hoja inferior */
    '@media(max-width:560px){',
    '  #kht-stack{top:calc(8px + env(safe-area-inset-top,0px));left:8px;right:8px;width:auto;max-width:none}',
    '  @keyframes kht-in{from{opacity:0;transform:translateY(-12px)}to{opacity:1;transform:none}}',
    '  @keyframes kht-out{to{opacity:0;transform:translateY(-12px)}}',
    '  #khm-ov{align-items:flex-end;padding:0}',
    '  .khm{width:100%;max-height:92vh;border-radius:18px 18px 0 0;padding:18px 16px calc(16px + env(safe-area-inset-bottom,0px))}',
    '}',
    '@media(prefers-reduced-motion:reduce){.kht,.kht.out,.khm,#khm-ov{animation:none!important}.kht-ico.spin::before{animation-duration:2s}}',
  ].join('\n');
  function ensureCss() {
    if (document.getElementById('kht-css')) return;
    var st = document.createElement('style'); st.id = 'kht-css'; st.textContent = CSS;
    (document.head || document.documentElement).appendChild(st);
  }

  /* ── insignia de modo ───────────────────────────────────────────────── */
  function normMode(m) {
    if (m === true) return 'paper';
    if (m === false) return 'live';
    m = String(m || '').toLowerCase();
    return (m === 'paper' || m === 'sim' || m === 'live') ? m : '';
  }
  function modeLabel(m) {
    m = normMode(m);
    if (m === 'live') return L('🔴 DINERO REAL', '🔴 REAL MONEY');
    if (m === 'paper' || m === 'sim') return L('🧪 SIMULADO', '🧪 SIMULATED');
    return '';
  }
  function modeBadge(m) {
    m = normMode(m); if (!m) return '';
    return '<span class="kht-mode ' + (m === 'live' ? 'live' : 'paper') + '">' + esc(modeLabel(m)) + '</span>';
  }

  /* ── toasts ─────────────────────────────────────────────────────────── */
  var MAX = 4, _seq = 0, _items = {};
  var ICON = { buy: '▲', sell: '▼', success: '✓', info: 'i', warn: '!', error: '!' };
  var DEF_TIMEOUT = { info: 5000, success: 6500, buy: 7000, sell: 7000, warn: 9000, error: 12000 };

  function stack() {
    var s = document.getElementById('kht-stack');
    if (!s) {
      s = document.createElement('div'); s.id = 'kht-stack';
      s.setAttribute('role', 'region');
      s.setAttribute('aria-label', L('Notificaciones', 'Notifications'));
      document.body.appendChild(s);
    }
    return s;
  }
  function render(it) {
    var o = it.o, kind = ICON[o.kind] ? o.kind : 'info';
    var el = it.el;
    el.className = 'kht kht-' + kind;
    // errores y advertencias interrumpen al lector de pantalla; el resto es cortés
    el.setAttribute('role', (kind === 'error' || kind === 'warn') ? 'alert' : 'status');
    el.setAttribute('aria-live', (kind === 'error' || kind === 'warn') ? 'assertive' : 'polite');
    el.setAttribute('aria-atomic', 'true');
    var bodyHtml = o.html != null ? String(o.html) : (o.body != null ? esc(o.body) : '');
    el.innerHTML =
      '<div class="kht-ico' + (o.busy ? ' spin' : '') + '" aria-hidden="true">' + (o.busy ? '' : ICON[kind]) + '</div>' +
      '<div class="kht-main">' +
        '<div class="kht-top"><div class="kht-title">' + esc(o.title || '') + '</div>' + modeBadge(o.mode) + '</div>' +
        (bodyHtml ? '<div class="kht-body">' + bodyHtml + '</div>' : '') +
        ((o.actions && o.actions.length) ? '<div class="kht-actions">' + o.actions.map(function (a, i) {
          return '<button type="button" data-i="' + i + '">' + esc(a.label) + '</button>';
        }).join('') + '</div>' : '') +
      '</div>' +
      '<button type="button" class="kht-x" aria-label="' + esc(L('Cerrar notificación', 'Dismiss notification')) + '">×</button>' +
      (it.timeout > 0 ? '<div class="kht-bar" aria-hidden="true"><i></i></div>' : '');
    el.querySelector('.kht-x').onclick = function () { dismiss(it.id); };
    if (o.actions) el.querySelectorAll('.kht-actions button').forEach(function (b) {
      b.onclick = function () {
        var a = o.actions[+b.getAttribute('data-i')];
        try { if (a && a.onClick) a.onClick(); } catch (e) {}
        if (!a || a.keep !== true) dismiss(it.id);
      };
    });
    arm(it);
  }
  // temporizador con pausa al pasar el mouse / al enfocar (lectura tranquila)
  function arm(it) {
    clearTimeout(it.t);
    var bar = it.el.querySelector('.kht-bar i');
    if (!(it.timeout > 0)) return;
    it.left = it.timeout; it.start = Date.now();
    if (bar) { bar.style.transition = 'none'; bar.style.transform = 'scaleX(1)'; void bar.offsetWidth;
      bar.style.transition = 'transform ' + it.left + 'ms linear'; bar.style.transform = 'scaleX(0)'; }
    it.t = setTimeout(function () { dismiss(it.id); }, it.left);
  }
  function pause(it) {
    if (!(it.timeout > 0) || it.paused) return;
    it.paused = true; clearTimeout(it.t);
    it.left = Math.max(800, it.left - (Date.now() - it.start));
    var bar = it.el.querySelector('.kht-bar i');
    if (bar) { var cs = getComputedStyle(bar).transform; bar.style.transition = 'none'; bar.style.transform = cs === 'none' ? 'scaleX(1)' : cs; }
  }
  function resume(it) {
    if (!it.paused) return;
    it.paused = false; it.start = Date.now();
    var bar = it.el.querySelector('.kht-bar i');
    if (bar) { void bar.offsetWidth; bar.style.transition = 'transform ' + it.left + 'ms linear'; bar.style.transform = 'scaleX(0)'; }
    it.t = setTimeout(function () { dismiss(it.id); }, it.left);
  }
  function show(o) {
    o = Object.assign({}, o || {});
    if (!document.body) return null;
    ensureCss();
    if (o.id && _items[o.id]) return update(o.id, o);
    var id = o.id || ('kt' + (++_seq));
    var el = document.createElement('div');
    var it = { id: id, el: el, o: o, timeout: o.timeout != null ? +o.timeout : (o.busy ? 0 : DEF_TIMEOUT[o.kind] || 6000) };
    _items[id] = it;
    el.addEventListener('mouseenter', function () { pause(it); });
    el.addEventListener('mouseleave', function () { resume(it); });
    el.addEventListener('focusin', function () { pause(it); });
    el.addEventListener('focusout', function () { resume(it); });
    var s = stack();
    s.insertBefore(el, s.firstChild);   // lo más nuevo arriba
    render(it);
    var ids = Object.keys(_items);
    if (ids.length > MAX) ids.slice(0, ids.length - MAX).forEach(function (k) { dismiss(k); });
    return id;
  }
  function update(id, o) {
    var it = _items[id];
    if (!it) return show(Object.assign({}, o, { id: id }));
    o = o || {};
    it.o = Object.assign({}, it.o, o);
    if ('html' in o && o.html == null) delete it.o.html;
    if (o.body != null && o.html == null) delete it.o.html;
    // el plazo solo cambia si se pide o si cambia el estado (enviando → resultado);
    // un parche menor (p. ej. completar la insignia) NO acorta un aviso fijo
    if (o.timeout != null) it.timeout = +o.timeout;
    else if ('busy' in o || 'kind' in o) it.timeout = it.o.busy ? 0 : (DEF_TIMEOUT[it.o.kind] || 6000);
    it.paused = false;
    render(it);
    return id;
  }
  function dismiss(id) {
    var it = _items[id]; if (!it) return;
    delete _items[id]; clearTimeout(it.t);
    var el = it.el;
    el.classList.add('out');
    setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 200);
  }
  function clear() { Object.keys(_items).forEach(dismiss); }

  /* ── diálogo de confirmación (genérico) ─────────────────────────────── */
  var _dlg = null;   // { close(result), key }
  function confirmDlg(opts) {
    opts = opts || {};
    if (_dlg) _dlg.close(false, 'dismissed');   // nunca dos diálogos de dinero a la vez
    if (!document.body) return Promise.resolve(window.confirm(String(opts.title || '')));
    ensureCss();
    var prevFocus = document.activeElement;
    var ov = document.createElement('div'); ov.id = 'khm-ov';
    var tone = opts.side === 'sell' ? 'sell' : opts.side === 'buy' ? 'buy' : 'info';
    var settled = false, resolveFn;
    var p = new Promise(function (res) { resolveFn = res; });
    // reason: 'confirm' | 'cancel' (el usuario) | 'superseded' (la misma orden
    // ya se está enviando por otra vía, p. ej. el «sí» por voz) | 'dismissed'
    // (la pantalla que lo abrió se cerró). Queda en p.reason para el llamador.
    function close(v, reason) {
      if (settled) return; settled = true;
      p.reason = reason || (v ? 'confirm' : 'cancel');
      document.removeEventListener('keydown', onKey, true);
      if (ov.parentNode) ov.parentNode.removeChild(ov);
      if (_dlg && _dlg.ov === ov) _dlg = null;
      try { if (prevFocus && prevFocus.focus && document.contains(prevFocus)) prevFocus.focus(); } catch (e) {}
      resolveFn(!!v);
    }
    function paint() {
      var rows = (opts.rows || []).filter(Boolean).map(function (r) {
        return '<div><dt>' + esc(r[0]) + '</dt><dd' + (r[2] && r[2].mono ? ' class="num"' : '') +
          (r[2] && r[2].color ? ' style="color:' + esc(r[2].color) + '"' : '') + '>' + (r[2] && r[2].html ? r[1] : esc(r[1])) + '</dd></div>';
      }).join('');
      var chips = (opts.chips && opts.chips.values && opts.chips.values.length)
        ? '<div class="khm-chips" role="group" aria-label="' + esc(opts.chips.label || '') + '" style="--kc:' + (tone === 'sell' ? '#F6465D' : '#2EBD85') + '">' +
            opts.chips.values.map(function (v) {
              return '<button type="button" data-v="' + esc(v) + '" aria-pressed="' + (+v === +opts.chips.current ? 'true' : 'false') + '">' + esc(money(v).replace('.00', '')) + '</button>';
            }).join('') + '</div>' : '';
      var box = ov.querySelector('.khm');
      box.innerHTML =
        '<div class="khm-hd">' +
          (opts.sideLabel ? '<span class="khm-side ' + tone + '">' + esc(opts.sideLabel) + '</span>' : '') +
          modeBadge(opts.mode) +
          '<button type="button" class="khm-x" aria-label="' + esc(L('Cancelar', 'Cancel')) + '">×</button></div>' +
        '<h2 class="khm-title" id="khm-t">' + esc(opts.title || '') + '</h2>' +
        (opts.subtitle ? '<div class="khm-sub" id="khm-d">' + esc(opts.subtitle) + '</div>' : '') +
        (rows ? '<dl class="khm-rows">' + rows + '</dl>' : '') +
        chips +
        (opts.total ? '<div class="khm-total"><span>' + esc(opts.total[0]) + '</span><b class="num">' + esc(opts.total[1]) + '</b></div>' : '') +
        (opts.warnHtml ? '<div class="khm-warn" role="note">' + opts.warnHtml + '</div>' : '') +
        (opts.note ? '<div class="khm-note">' + esc(opts.note) + '</div>' : '') +
        (opts.requireCheck ? '<label class="khm-ck"><input type="checkbox" id="khm-ck"> <span>' + esc(opts.requireCheck) + '</span></label>' : '') +
        '<div class="khm-btns">' +
          '<button type="button" class="khm-cancel">' + esc(opts.cancelLabel || L('Cancelar', 'Cancel')) + '</button>' +
          '<button type="button" class="khm-ok ' + (tone === 'info' ? '' : tone) + '"' + (opts.requireCheck ? ' disabled' : '') + '>' +
            esc(opts.confirmLabel || L('Confirmar', 'Confirm')) + '</button></div>';
      if (opts.subtitle) box.setAttribute('aria-describedby', 'khm-d'); else box.removeAttribute('aria-describedby');
      box.querySelector('.khm-x').onclick = function () { close(false); };
      box.querySelector('.khm-cancel').onclick = function () { close(false); };
      var ok = box.querySelector('.khm-ok');
      ok.onclick = function () { if (!ok.disabled) close(true); };
      var ck = box.querySelector('#khm-ck');
      if (ck) ck.onchange = function () { ok.disabled = !ck.checked; };
      box.querySelectorAll('.khm-chips button').forEach(function (b) {
        b.onclick = function () {
          var v = +b.getAttribute('data-v');
          if (opts.chips.onPick) opts.chips.onPick(v, opts);   // el llamador recalcula filas/total
          opts.chips.current = v;
          paint();
          var nb = ov.querySelector('.khm-chips button[data-v="' + v + '"]'); if (nb) nb.focus();
        };
      });
    }
    function onKey(e) {
      if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close(false); return; }
      if (e.key !== 'Tab') return;
      var f = Array.prototype.filter.call(ov.querySelectorAll('button,input'), function (x) { return !x.disabled; });
      if (!f.length) return;
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && (document.activeElement === first || document.activeElement === ov.querySelector('.khm'))) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
    ov.innerHTML = '<div class="khm" role="dialog" aria-modal="true" aria-labelledby="khm-t" tabindex="-1"></div>';
    paint();
    ov.addEventListener('mousedown', function (e) { if (e.target === ov) close(false); });
    document.addEventListener('keydown', onKey, true);
    document.body.appendChild(ov);
    // foco en el diálogo (no en Confirmar): un Enter suelto NUNCA envía dinero
    try { ov.querySelector('.khm').focus(); } catch (e) {}
    _dlg = { ov: ov, key: opts.key || null, close: close };
    p.close = function (reason) { close(false, reason || 'dismissed'); };
    return p;
  }

  /* ── confirmación de ORDEN ──────────────────────────────────────────── */
  function orderKey(o) {
    o = o || {};
    return [String(o.symbol || '').toUpperCase(), o.side === 'sell' ? 'sell' : 'buy',
      o.notional != null ? Math.round(+o.notional * 100) / 100 : '', o.qty != null ? +o.qty : ''].join('|');
  }
  // modo de la cuenta: explícito → paper/live del objeto → /api/trade/status
  // (público, caché 5 min). Ante la duda: DINERO REAL (convención de la app).
  function resolveMode(o) {
    var m = normMode(o && (o.mode != null ? o.mode : o.paper));
    if (m) return Promise.resolve(m);
    if (!window._tradeStatusInfo) return Promise.resolve('live');
    return Promise.resolve(window._tradeStatusInfo()).then(function (s) {
      return (s && typeof s.paper === 'boolean') ? (s.paper ? 'paper' : 'live') : 'live';
    }).catch(function () { return 'live'; });
  }
  var TIF = {
    day: { es: 'Solo hoy (day)', en: 'Day only (day)' },
    gtc: { es: 'Hasta cancelarla (GTC)', en: 'Until canceled (GTC)' },
    ioc: { es: 'Inmediata o se cancela (IOC)', en: 'Immediate or cancel (IOC)' },
    fok: { es: 'Completa o se cancela (FOK)', en: 'Fill or kill (FOK)' },
  };
  function orderRows(o, mode) {
    var side = o.side === 'sell' ? 'sell' : 'buy';
    var isLimit = o.orderType === 'limit' || o.type === 'limit';
    var lp = num(o.limitPrice != null ? o.limitPrice : o.limit_price);
    var px = num(o.price);
    var crypto = String(o.symbol || '').indexOf('/') >= 0 || o.kind === 'crypto';
    var unit = crypto ? L('unidades', 'units') : L('acciones', 'shares');
    var rows = [];
    rows.push([L('Operación', 'Side'), side === 'buy' ? L('Compra', 'Buy') : L('Venta', 'Sell'), { color: side === 'buy' ? '#2EBD85' : '#F6465D' }]);
    rows.push([L('Activo', 'Asset'), (o.label && o.label !== o.symbol ? o.label + ' · ' : '') + (o.symbol || '—')]);
    if (o.client) rows.push([L('Cliente', 'Client'), o.client]);
    // por monto (notional): la cifra va en el recuadro de abajo, no se repite aquí
    if (o.notional == null) rows.push([L('Cantidad', 'Quantity'), qtyFmt(o.qty) + ' ' + unit, { mono: true }]);
    rows.push([L('Tipo de orden', 'Order type'), isLimit
      ? L('Límite a ', 'Limit at ') + money(lp)
      : L('A mercado (precio actual)', 'Market (current price)')]);
    if (!isLimit && px != null && px > 0 && o.notional == null) rows.push([L('Último precio', 'Last price'), money(px), { mono: true }]);
    var tif = String(o.tif || o.time_in_force || '').toLowerCase();
    if (TIF[tif]) rows.push([L('Vigencia', 'Time in force'), en() ? TIF[tif].en : TIF[tif].es]);
    // monto estimado: notional exacto, o cantidad × (límite | último precio).
    // Sin precio de referencia NO se inventa: se dice que no hay.
    var est = null;
    if (o.notional != null) est = num(o.notional);
    else if (num(o.estUsd) != null) est = num(o.estUsd);
    else if (num(o.qty) != null) { var ref = isLimit ? lp : px; if (ref != null && ref > 0) est = num(o.qty) * ref; }
    return { rows: rows, est: est, isLimit: isLimit };
  }
  function confirmOrder(o, opts) {
    o = o || {}; opts = opts || {};
    var side = o.side === 'sell' ? 'sell' : 'buy';
    return resolveMode(o).then(function (mode) {
      function build(dlg) {
        var r = orderRows(o, mode);
        dlg.rows = r.rows;
        dlg.total = [r.est != null && o.notional == null ? L('Monto estimado', 'Estimated amount') : L('Monto de la orden', 'Order amount'),
          r.est != null ? (o.notional == null ? '≈ ' : '') + money(r.est) : L('sin precio de referencia', 'no reference price')];
        dlg.note = r.isLimit
          ? L('Orden límite: solo se ejecuta a ese precio o mejor.', 'Limit order: it only fills at that price or better.')
          : L('Orden a mercado: el precio final lo fija el mercado al ejecutarse.', 'Market order: the final price is set by the market when it fills.');
        return dlg;
      }
      var dlg = build({
        key: orderKey(o), side: side, mode: mode,
        sideLabel: side === 'buy' ? L('▲ COMPRA', '▲ BUY') : L('▼ VENTA', '▼ SELL'),
        title: opts.title || (side === 'buy' ? L('Confirma tu orden de compra', 'Confirm your buy order') : L('Confirma tu orden de venta', 'Confirm your sell order')),
        subtitle: opts.subtitle || L('Revisa los datos. Nada se envía hasta que confirmes.', 'Review the details. Nothing is sent until you confirm.'),
        confirmLabel: opts.confirmLabel || (side === 'buy' ? L('Confirmar compra', 'Confirm buy') : L('Confirmar venta', 'Confirm sell')),
        cancelLabel: opts.cancelLabel,
        warnHtml: mode === 'live'
          ? '<b>' + esc(L('DINERO REAL.', 'REAL MONEY.')) + '</b> ' + esc(L('Esta orden usa dinero real de la cuenta y no se puede deshacer una vez ejecutada.', 'This order uses real money from the account and cannot be undone once filled.'))
          : '',
        requireCheck: (mode === 'live' && opts.liveCheck !== false)
          ? L('Entiendo que esta orden usa DINERO REAL.', 'I understand this order uses REAL MONEY.') : '',
      });
      if (opts.amounts && o.notional != null) {
        dlg.chips = { label: L('Monto rápido', 'Quick amount'), values: opts.amounts, current: +o.notional,
          onPick: function (v, d) { o.notional = v; build(d); if (opts.onAmount) opts.onAmount(v); } };
      }
      var p = confirmDlg(dlg);
      if (opts.onHandle) opts.onHandle(p);
      return p;
    });
  }

  /* ── ciclo de vida de la orden (cuenta de la casa) ──────────────────── */
  function sideWord(o, past) {
    var buy = o.side !== 'sell';
    if (past) return buy ? L('Compra', 'Buy') : L('Venta', 'Sell');
    return buy ? L('compra', 'buy') : L('venta', 'sell');
  }
  function what(o) {
    var amt = o.notional != null ? '<span class="kht-num">' + esc(money(o.notional)) + '</span> ' + esc(L('de', 'of')) + ' '
      : (o.qty != null ? '<span class="kht-num">' + esc(qtyFmt(o.qty)) + ' ×</span> ' : '');
    var nm = o.label && o.label !== o.symbol ? esc(o.label) + ' <span class="kht-num">(' + esc(o.symbol) + ')</span>' : '<b>' + esc(o.symbol || '') + '</b>';
    return amt + nm;
  }
  function emit(phase, o, data) {
    try { window.dispatchEvent(new CustomEvent('khipu:order', { detail: { phase: phase, order: o, data: data || null } })); } catch (e) {}
  }
  function sending(o) {
    o = o || {};
    // si el usuario confirmó POR VOZ, el diálogo de esa misma orden sobra
    if (_dlg && _dlg.key && _dlg.key === orderKey(o)) _dlg.close(false, 'superseded');
    var id = show({ kind: o.side === 'sell' ? 'sell' : 'buy', busy: true, mode: normMode(o.mode != null ? o.mode : o.paper) || undefined,
      title: o.side === 'sell' ? L('Enviando orden de venta…', 'Sending sell order…') : L('Enviando orden de compra…', 'Sending buy order…'),
      html: what(o) });
    // el modo se completa en cuanto se sepa (la insignia es obligatoria)
    if (!normMode(o.mode != null ? o.mode : o.paper)) resolveMode(o).then(function (m) { if (_items[id] && !_items[id].o.mode) update(id, { mode: m }); });
    emit('sending', o);
    return id;
  }
  // r = { ok, dedup, broker_dup, ambiguous, error, data, local } (contrato de window._executeTradeOrder)
  function result(o, r, id) {
    o = o || {}; r = r || {};
    var d = r.data || {};
    var mode = r.local ? 'sim' : normMode(o.mode != null ? o.mode : o.paper);
    if (!mode && typeof d.paper === 'boolean') mode = d.paper ? 'paper' : 'live';
    // pinta YA (el id queda fijo) y completa la insignia en cuanto se sepa el modo
    function put(x) {
      x.busy = false;
      if (mode) x.mode = mode;
      id = (id && _items[id]) ? update(id, x) : show(x);
      if (!mode) resolveMode(o).then(function (m) { if (_items[id] && !_items[id].o.mode) update(id, { mode: m }); });
      return id;
    }
    if (r.ok && r.dedup) {
      emit('duplicate', o, d);
      return put({ kind: 'warn', title: L('No se envió dos veces', 'Not sent twice'),
        body: r.broker_dup
          ? L('Esa orden ya había llegado al bróker' + (d.status ? ' (estado: ' + d.status + ')' : '') + '. Si quieres OTRA igual, vuelve a enviarla.',
              'That order had already reached the broker' + (d.status ? ' (status: ' + d.status + ')' : '') + '. If you want ANOTHER identical one, send it again.')
          : L('Esa misma orden ya se envió hace un momento.', 'That same order was already sent a moment ago.') });
    }
    if (r.ok && r.local) {
      emit('filled', o, d);
      return put({ kind: o.side === 'sell' ? 'sell' : 'buy',
        title: o.side === 'sell' ? L('Venta simulada en tu cartera local', 'Simulated sell in your local portfolio') : L('Compra simulada en tu cartera local', 'Simulated buy in your local portfolio'),
        html: what(o) + (num(o.price) ? ' @ <span class="kht-num">' + esc(money(o.price)) + '</span>' : '') +
          '<br>' + esc(L('No hay bróker configurado: no salió ninguna orden real.', 'No broker configured: no real order was sent.')) });
    }
    if (r.ok) {
      emit('accepted', o, d);
      var st = String(d.status || 'accepted');
      if (st === 'filled') return filled(o, d, id, mode);
      put({ kind: o.side === 'sell' ? 'sell' : 'buy', timeout: 0,
        title: o.side === 'sell' ? L('Orden de venta enviada', 'Sell order sent') : L('Orden de compra enviada', 'Buy order sent'),
        html: what(o) + ' · ' + esc(L('estado en el bróker: ', 'broker status: ')) + '<b>' + esc(st) + '</b>' +
          '<br>' + esc(L('Te aviso cuando se ejecute.', "I'll let you know when it fills.")) });
      watch(o, d, id);
      return id;
    }
    emit(r.ambiguous ? 'unknown' : 'failed', o, d);
    return put({ kind: r.ambiguous ? 'warn' : 'error',
      title: r.ambiguous ? L('No se pudo confirmar la orden', 'The order could not be confirmed')
        : (o.side === 'sell' ? L('La venta no se envió', 'The sell order was not sent') : L('La compra no se envió', 'The buy order was not sent')),
      // el texto del server TAL CUAL (ya viene bilingüe por _tradeErrText)
      body: String(r.error || L('Error desconocido', 'Unknown error')) });
  }
  function filled(o, d, id, mode) {
    var fq = num(d.filled_qty), fp = num(d.filled_avg_price);
    var tot = (fq != null && fp != null) ? fq * fp : null;
    emit('filled', o, d);
    var x = { busy: false, kind: o.side === 'sell' ? 'sell' : 'buy', mode: mode || normMode(d.paper) || undefined, timeout: 10000,
      title: o.side === 'sell' ? L('Venta ejecutada ✓', 'Sell filled ✓') : L('Compra ejecutada ✓', 'Buy filled ✓'),
      html: (fq != null ? '<span class="kht-num">' + esc(qtyFmt(fq)) + '</span> ' : '') + '<b>' + esc(d.symbol || o.symbol || '') + '</b>' +
        (fp != null ? ' @ <span class="kht-num">' + esc(money(fp)) + '</span>' : '') +
        (tot != null ? ' · ' + esc(L('total ', 'total ')) + '<span class="kht-num">' + esc(money(tot)) + '</span>' : '') };
    id = (id && _items[id]) ? update(id, x) : show(x);
    if (!x.mode) resolveMode(o).then(function (m) { if (_items[id] && !_items[id].o.mode) update(id, { mode: m }); });
    return id;
  }
  // Sondeo LIGERO del estado: /api/trade/history (el mismo que usan el panel
  // y la Cabina), sin pedir PIN (interactive=false), ≤ ~60 s y se detiene en
  // cuanto la orden queda en un estado final.
  var POLL_AT = [2500, 5000, 9000, 14000, 20000, 28000, 38000, 48000, 60000];
  var FINAL_BAD = { canceled: 1, expired: 1, rejected: 1, done_for_day: 1, stopped: 1, suspended: 1 };
  function watch(o, d, id) {
    d = d || {};
    var oid = d.id, coid = d.client_order_id || o.client_order_id;
    if ((!oid && !coid) || !window._tradeFetch) return;
    var t0 = Date.now(), i = 0, lastPartial = null;
    function done() { return !_items[id]; }
    function tick() {
      if (i >= POLL_AT.length) return pending();
      var wait = Math.max(0, POLL_AT[i++] - (Date.now() - t0));
      setTimeout(function () {
        window._tradeFetch('/api/trade/history', {}, false)
          .then(function (r) { return r.ok ? r.json() : null; })
          .then(function (list) {
            if (!Array.isArray(list)) return tick();
            var hit = null;
            for (var k = 0; k < list.length; k++) {
              var x = list[k];
              if (x && ((oid && x.id === oid) || (coid && x.client_order_id === coid))) { hit = x; break; }
            }
            if (!hit) return tick();
            var st = String(hit.status || '');
            if (st === 'filled') return filled(o, hit, _items[id] ? id : null, normMode(o.mode != null ? o.mode : o.paper) || normMode(d.paper));
            if (FINAL_BAD[st]) {
              emit('closed', o, hit);
              var x2 = { busy: false, kind: st === 'rejected' ? 'error' : 'warn', timeout: 12000,
                title: L('La orden no se ejecutó', 'The order did not fill'),
                html: what(o) + ' · ' + esc(L('estado final: ', 'final status: ')) + '<b>' + esc(st) + '</b>' };
              return done() ? show(Object.assign({ mode: normMode(hit.paper) || undefined }, x2)) : update(id, x2);
            }
            if (st === 'partially_filled' && hit.filled_qty !== lastPartial && !done()) {
              lastPartial = hit.filled_qty;
              update(id, { html: what(o) + ' · ' + esc(L('ejecutada en parte: ', 'partially filled: ')) +
                '<span class="kht-num">' + esc(qtyFmt(hit.filled_qty)) + '</span>' + (hit.qty ? ' / <span class="kht-num">' + esc(qtyFmt(hit.qty)) + '</span>' : ''), timeout: 0 });
            }
            tick();
          })
          .catch(function () { tick(); });
      }, wait);
    }
    function pending() {
      // sigue abierta: lo decimos claro (p. ej. mercado cerrado) y se cierra el sondeo
      var x = { busy: false, kind: 'info', timeout: 12000,
        title: L('La orden sigue pendiente', 'The order is still pending'),
        html: what(o) + '<br>' + esc(L('Aún no se ejecuta (¿mercado cerrado?). La verás en tus órdenes recientes.',
          'It has not filled yet (market closed?). You will see it in your recent orders.')) };
      if (!done()) update(id, x);
    }
    tick();
  }

  window.KhipuToast = {
    __v: 1,
    show: show, update: update, dismiss: dismiss, clear: clear,
    confirm: confirmDlg, confirmOrder: confirmOrder,
    modeLabel: modeLabel, modeBadge: modeBadge,
    order: { confirm: confirmOrder, sending: sending, result: result, watch: watch, filled: filled, key: orderKey, resolveMode: resolveMode },
  };
})();
