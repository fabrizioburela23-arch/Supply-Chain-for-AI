/* ============================================================================
   engine/signals.js — «1 TOQUE»: señales del agente de trading listas para aprobar (2026-10-20)
   El agente en modo MANUAL propone (servidor: core/trading_agent.py, GET /api/trade/agent/signals): lado, monto,
   precio que vio, stop, confianza, RSI/tendencia/convicción y el motivo. Aquí se ven como tarjetas flotantes y:
     · cuenta de PAPEL 🧪 → un toque en «Comprar 500 USD» la envía;
     · DINERO REAL 🔴 → un toque + el diálogo de confirmación de siempre (KhipuToast.confirmOrder, casilla «entiendo»).
   La orden sale por POST /api/trade/agent/signals/<id>/take (PIN por window._tradeFetch → EL camino único
   brokerage.service.house_order). El servidor la rechaza si venció (15 min) o si el precio se movió > 1,5 % en contra.
   Nada se envía solo. Sondeo cada 20 s SOLO con PIN guardado y la pestaña visible; aviso del navegador si lo activas.
   ============================================================================ */
(function () {
  'use strict';
  if (window.KhipuSignals) return;
  var W = window, POLL_MS = 20000, seen = {}, busy = {}, last = [], timer = null;

  function isEn() { var l = W.LANG; if (!l) { try { l = localStorage.getItem('eco_lang'); } catch (e) { l = null; } } return l === 'en'; }
  function L(es, en) { return isEn() ? en : es; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function money(v) { return Number(v).toLocaleString(isEn() ? 'en-US' : 'es-PE', { maximumFractionDigits: 2 }) + ' USD'; }
  function hasPin() { try { return typeof W._tradePinStored === 'function' && !!W._tradePinStored(); } catch (e) { return false; } }
  function label(sym) {
    var NB = W.NODE_BY_ID || {};
    for (var k in NB) { var n = NB[k]; if (n && n.id === k && String(n.mkt || '').toUpperCase() === sym) return n.label; }
    return sym;
  }
  function verb(s) {
    if (s.kind === 'stop') return L('Vender todo (stop)', 'Sell all (stop)');
    if (s.side === 'buy') return L('Comprar', 'Buy');
    return L('Vender', 'Sell');
  }
  function amount(s) { return s.notional != null ? money(s.notional) : (s.qty != null ? s.qty + ' ' + L('acciones', 'shares') : ''); }
  function left(s) {
    var ms = Date.parse(s.expires_at) - Date.now();
    if (!(ms > 0)) return L('vencida', 'expired');
    var m = Math.floor(ms / 60000), sec = Math.floor(ms / 1000) % 60;
    return L('vence en ', 'expires in ') + m + ':' + (sec < 10 ? '0' : '') + sec;
  }

  function css() {
    if (document.getElementById('ksig-css')) return;
    var st = document.createElement('style'); st.id = 'ksig-css';
    st.textContent = '#ksig{position:fixed;right:16px;bottom:64px;z-index:7700;display:flex;flex-direction:column;gap:10px;width:min(360px,calc(100vw - 32px));' +
      'font-family:var(--os-font,Nunito,system-ui,sans-serif)}' +
      '#ksig .c{background:var(--os-surface,#17181F);color:var(--os-ink,#F2F2F5);border-radius:16px;padding:12px 14px;' +
      'box-shadow:0 2px 8px rgba(0,0,0,.35),0 14px 36px rgba(0,0,0,.35);font-size:13px;line-height:1.45}' +
      '#ksig .h{display:flex;align-items:center;gap:8px;font-weight:800;font-size:14px}' +
      '#ksig .b{font-size:10.5px;font-weight:800;padding:2px 7px;border-radius:999px;letter-spacing:.04em}' +
      '#ksig .b.live{background:#7f1d1d;color:#fff}#ksig .b.paper{background:var(--os-surface-2,#2A2B35);color:var(--os-ink,#F2F2F5)}' +
      '#ksig .m{color:var(--os-ink-2,#A6A8B5);font-size:12px;margin-top:4px}' +
      '#ksig .r{margin-top:6px}' +
      '#ksig .a{display:flex;gap:8px;margin-top:10px}' +
      '#ksig button{font:inherit;font-weight:800;border:0;border-radius:999px;padding:9px 14px;cursor:pointer}' +
      '#ksig .go.buy{background:#15803d;color:#fff;flex:1}#ksig .go.sell{background:#b91c1c;color:#fff;flex:1}' +
      '#ksig .no{background:var(--os-surface-2,#2A2B35);color:var(--os-ink,#F2F2F5)}' +
      '#ksig button:focus-visible{outline:2px solid var(--os-accent,#4C8DF6);outline-offset:2px}' +
      '#ksig .bell{background:none;color:var(--os-accent,#4C8DF6);padding:0;font-weight:700;font-size:12px}';
    document.head.appendChild(st);
  }
  function box() {
    var b = document.getElementById('ksig');
    if (!b) { css(); b = document.createElement('div'); b.id = 'ksig'; b.setAttribute('aria-live', 'polite'); document.body.appendChild(b); }
    return b;
  }

  function card(s) {
    var live = !s.paper;
    var facts = [];
    if (s.price) facts.push(L('precio visto ', 'price seen ') + s.price);
    if (s.confidence) facts.push(L('confianza ', 'confidence ') + s.confidence + '/100');
    if (s.rsi14 != null) facts.push('RSI ' + s.rsi14);
    if (s.trend) facts.push(L('tendencia ', 'trend ') + (isEn() ? ({ alcista: 'up', bajista: 'down', mixta: 'mixed' }[s.trend] || s.trend) : s.trend));
    if (s.conviction != null) facts.push(L('analistas ', 'analysts ') + (s.conviction > 0 ? '+' : '') + Math.round(s.conviction));
    if (s.kind !== 'stop' && s.stop_loss_pct) facts.push('stop −' + s.stop_loss_pct + ' %');
    var go = verb(s) + ' ' + amount(s);
    return '<div class="c" data-id="' + esc(s.id) + '">' +
      '<div class="h"><span class="b ' + (live ? 'live' : 'paper') + '">' + (live ? L('🔴 DINERO REAL', '🔴 REAL MONEY') : L('🧪 SIMULADO', '🧪 PAPER')) + '</span>' +
      esc(verb(s)) + ' ' + esc(label(s.ticker)) + ' <span style="opacity:.7">(' + esc(s.ticker) + ')</span></div>' +
      '<div class="r">' + esc(s.reason || '') + '</div>' +
      '<div class="m">' + esc(facts.join(' · ')) + ' · <span class="t">' + esc(left(s)) + '</span></div>' +
      '<div class="a"><button type="button" class="go ' + (s.side === 'sell' ? 'sell' : 'buy') + '" data-act="take">' + esc(go) + '</button>' +
      '<button type="button" class="no" data-act="dismiss" aria-label="' + esc(L('Descartar', 'Dismiss')) + '">✕</button></div>' +
      (('Notification' in W) && Notification.permission === 'default'
        ? '<div class="m"><button type="button" class="bell" data-act="bell">' + esc(L('🔔 Avisarme aunque esté en otra pestaña', '🔔 Notify me even in another tab')) + '</button></div>' : '') +
      '<div class="m">' + esc(L('Información de un agente automático, no consejo. Tú decides.', 'Information from an automated agent, not advice. You decide.')) + '</div>' +
      '</div>';
  }

  function render(list) {
    last = list;
    var pend = list.filter(function (s) { return s.status === 'pending' && Date.parse(s.expires_at) > Date.now(); }).slice(0, 3);
    var b = box();
    b.innerHTML = pend.map(card).join('');
    b.style.display = pend.length ? 'flex' : 'none';
  }

  function notifyNew(list) {
    list.forEach(function (s) {
      if (s.status !== 'pending' || seen[s.id]) return;
      seen[s.id] = 1;
      try {
        if (('Notification' in W) && Notification.permission === 'granted' && document.hidden) {
          new Notification('Khipus · ' + verb(s) + ' ' + s.ticker, { body: amount(s) + ' — ' + (s.reason || ''), tag: 'ksig-' + s.id });
        }
      } catch (e) {}
    });
  }

  function poll() {
    if (!hasPin() || document.hidden || typeof W._tradeFetch !== 'function') return Promise.resolve(null);
    return W._tradeFetch('/api/trade/agent/signals', {}, false).then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { if (d && d.signals) { notifyNew(d.signals); render(d.signals); } return d; })
      .catch(function () { return null; });
  }

  function take(s) {
    if (busy[s.id]) return;
    var o = { symbol: s.ticker, side: s.side, notional: s.notional, qty: s.notional == null ? s.qty : undefined,
      label: label(s.ticker), mode: s.paper ? 'paper' : 'live', type: 'market' };
    var T = W.KhipuToast;
    var ok = s.paper || !T ? Promise.resolve(true)
      : T.confirmOrder(o, { title: L('Aprobar la señal del agente', 'Approve the agent signal'),
          subtitle: (s.reason || '') + ' — ' + L('información, no consejo.', 'information, not advice.') });
    ok.then(function (yes) {
      if (!yes) return;
      busy[s.id] = 1;
      var tid = T && T.order ? T.order.sending(o) : null;
      W._tradeFetch('/api/trade/agent/signals/' + encodeURIComponent(s.id) + '/take', { method: 'POST',
        headers: { 'Content-Type': 'application/json' }, body: '{}', timeout: 20000 }, true)
        .then(function (r) { return r.json().then(function (j) { return { st: r.status, j: j }; }); })
        .then(function (x) {
          var good = x.st === 200 || x.st === 202;
          if (T && T.order) T.order.result(o, good ? { ok: true, data: x.j } : { ok: false, error: (isEn() ? x.j.error_en : x.j.error) || x.j.error || ('HTTP ' + x.st), data: x.j }, tid);
        })
        .catch(function (e) { if (T && T.order) T.order.result(o, { ok: false, error: String(e && e.message || e) }, tid); })
        .then(function () { delete busy[s.id]; poll(); });
    });
  }

  function dismiss(s) {
    W._tradeFetch('/api/trade/agent/signals/' + encodeURIComponent(s.id) + '/dismiss', { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: '{}' }, true).catch(function () {}).then(poll);
  }

  document.addEventListener('click', function (e) {
    var btn = e.target && e.target.closest && e.target.closest('#ksig button[data-act]');
    if (!btn) return;
    var c = btn.closest('.c'), id = c && c.getAttribute('data-id');
    var s = last.filter(function (x) { return x.id === id; })[0];
    var act = btn.getAttribute('data-act');
    if (act === 'bell') { try { Notification.requestPermission().then(function () { render(last); }); } catch (er) {} return; }
    if (!s) return;
    if (act === 'take') take(s); else if (act === 'dismiss') dismiss(s);
  });

  function start() {
    if (timer) return;
    timer = setInterval(poll, POLL_MS);
    setInterval(function () {                    // cuenta regresiva cada segundo, sin pedir al servidor
      var b = document.getElementById('ksig');
      if (!b || !last.length || b.style.display === 'none') return;
      b.querySelectorAll('.c').forEach(function (c) {
        var s = last.filter(function (x) { return x.id === c.getAttribute('data-id'); })[0];
        var t = c.querySelector('.t'); if (s && t) t.textContent = left(s);
      });
    }, 1000);
    document.addEventListener('visibilitychange', function () { if (!document.hidden) poll(); });
    setTimeout(poll, 4000);
  }

  W.KhipuSignals = { poll: poll, render: render, take: take, dismiss: dismiss, _card: card };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
