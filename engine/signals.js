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

  // ── Panel del AGENTE dentro de Khipus OS (ventana «Mi cuenta (bróker)»; antes solo en la vista clásica) ──
  // Mismos endpoints que el panel clásico: /api/trade/agent/status|start|stop (PIN por _tradeFetch). AUTO solo se
  // ofrece si el servidor dice auto_allowed (cuenta de papel); con dinero real el servidor lo rechaza igual.
  var IV = [5, 15, 30, 60, 240];
  function agentBox(el) {
    if (!el || typeof W._tradeFetch !== 'function') return;
    el.innerHTML = '<div class="bcp-loading">' + esc(L('Cargando el agente…', 'Loading the agent…')) + '</div>';
    W._tradeFetch('/api/trade/agent/status', {}, false).then(function (r) {
      if (r.status === 401 || r.status === 403) { el.innerHTML = '<div class="ksa-m">' + esc(L('Ingresa tu PIN (arriba) para ver y manejar el agente.', 'Enter your PIN (above) to see and run the agent.')) + '</div>'; return null; }
      return r.json();
    }).then(function (d) { if (d) paintAgent(el, d); })
      .catch(function () { el.innerHTML = '<div class="ksa-m">' + esc(L('No se pudo leer el agente.', 'Could not read the agent.')) + '</div>'; });
  }
  function paintAgent(el, d) {
    var on = !!d.running, live = d.paper === false;
    var pend = (d.signals || []).filter(function (s) { return s.status === 'pending'; }).length;
    var css = '<style>.ksa{background:var(--os-surface,#17181F);border-radius:16px;padding:14px 16px;font-size:13.5px}' +
      '.ksa h4{margin:0 0 8px;font-size:15px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}.ksa-m{font-size:12.5px;color:var(--os-ink-2,#A6A8B5)}' +
      '.ksa .g{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin:10px 0}' +
      '.ksa label{display:block;font-size:11.5px;font-weight:700;color:var(--os-ink-2,#A6A8B5);margin-bottom:3px}' +
      '.ksa input,.ksa select{width:100%;box-sizing:border-box;font:inherit;padding:8px 10px;border-radius:10px;border:1px solid var(--os-surface-2,#2A2B35);background:var(--os-bg,#0E0F14);color:var(--os-ink,#F2F2F5)}' +
      '.ksa .b{font:inherit;font-weight:800;border:0;border-radius:999px;padding:10px 18px;cursor:pointer}' +
      '.ksa .st{background:#15803d;color:#fff}.ksa .sp{background:#b91c1c;color:#fff}.ksa .pill{font-size:11px;font-weight:800;padding:2px 8px;border-radius:999px}' +
      '.ksa .log{margin-top:10px;font-size:12px;color:var(--os-ink-2,#A6A8B5);max-height:150px;overflow:auto}</style>';
    var h = css + '<div class="ksa"><h4>🤖 ' + esc(L('Agente de trading', 'Trading agent')) +
      '<span class="pill" style="background:' + (on ? '#15803d' : 'var(--os-surface-2,#2A2B35)') + ';color:#fff">' + esc(on ? L('ENCENDIDO', 'ON') : L('APAGADO', 'OFF')) + '</span>' +
      '<span class="pill" style="background:' + (live ? '#7f1d1d' : 'var(--os-surface-2,#2A2B35)') + ';color:#fff">' + esc(live ? L('🔴 DINERO REAL', '🔴 REAL MONEY') : L('🧪 PAPEL', '🧪 PAPER')) + '</span></h4>' +
      '<ol class="ksa-m" style="margin:4px 0 0;padding-left:18px;line-height:1.6">' +
        '<li>' + esc(L('Elige qué acciones vigilar y cada cuánto, y toca ▶ Iniciar.', 'Pick which stocks to watch and how often, then tap ▶ Start.')) + '</li>' +
        '<li>' + esc(L('El agente analiza precio, tendencia, RSI y lo que opinan los analistas de Khipus.', 'The agent analyzes price, trend, RSI and what the Khipus analysts think.')) + '</li>' +
        '<li>' + esc(L('Si ve una oportunidad, aparece una tarjeta abajo a la derecha: «Comprar 500 USD de NVDA». Tú la apruebas con un toque o la descartas. Nada se compra solo.',
          'If it sees an opportunity, a card appears at the bottom right: "Buy 500 USD of NVDA". You approve it with one tap or dismiss it. Nothing is bought on its own.')) + '</li></ol>' +
      (d.notice ? '<div class="ksa-m" style="color:var(--os-warn-ink,#F2C46D);margin-top:6px">⚠ ' + esc(isEn() ? d.notice.en : d.notice.es) + '</div>' : '') +
      (d.broker_error ? '<div class="ksa-m" style="color:var(--os-bad-ink,#F47C7C);margin-top:6px">⚠ ' + esc(d.broker_error) + '</div>' : '') +
      '<div class="g">' +
      '<div><label>' + esc(L('Modo', 'Mode')) + '</label><select data-k="mode"><option value="manual">' + esc(L('Manual (1 toque)', 'Manual (1 tap)')) + '</option>' +
        (d.auto_allowed ? '<option value="auto"' + (d.mode === 'auto' ? ' selected' : '') + '>' + esc(L('Automático (papel)', 'Automatic (paper)')) + '</option>' : '') + '</select></div>' +
      '<div><label>' + esc(L('Revisar cada', 'Check every')) + '</label><select data-k="interval_min">' + IV.map(function (m) { return '<option value="' + m + '"' + (+d.interval_min === m ? ' selected' : '') + '>' + m + ' min</option>'; }).join('') + '</select></div>' +
      '<div><label>' + esc(L('Máx. por posición %', 'Max per position %')) + '</label><input data-k="max_pos_pct" type="number" inputmode="decimal" step="0.5" value="' + esc(d.max_pos_pct) + '"></div>' +
      '<div><label>Stop-loss %</label><input data-k="stop_loss_pct" type="number" inputmode="decimal" step="0.5" value="' + esc(d.stop_loss_pct) + '"></div>' +
      '<div><label>' + esc(L('Confianza mínima', 'Min confidence')) + '</label><input data-k="min_confidence" type="number" inputmode="numeric" step="5" value="' + esc(d.min_confidence) + '"></div>' +
      '<div><label>' + esc(L('Pérdida diaria máx. %', 'Max daily loss %')) + '</label><input data-k="max_daily_loss_pct" type="number" inputmode="decimal" step="0.5" value="' + esc(d.max_daily_loss_pct) + '"></div>' +
      '</div><div><label style="font-size:11.5px;font-weight:700;color:var(--os-ink-2,#A6A8B5)">' + esc(L('Acciones a vigilar (tickers de EE.UU., separados por coma)', 'Stocks to watch (US tickers, comma separated)')) + '</label>' +
      '<input data-k="universe" value="' + esc((d.universe || []).join(', ')) + '" style="width:100%;box-sizing:border-box;font:inherit;padding:8px 10px;border-radius:10px;border:1px solid var(--os-surface-2,#2A2B35);background:var(--os-bg,#0E0F14);color:var(--os-ink,#F2F2F5)"></div>' +
      '<div style="display:flex;gap:10px;align-items:center;margin-top:12px;flex-wrap:wrap">' +
      (on ? '<button type="button" class="b sp" data-a="stop">■ ' + esc(L('Detener', 'Stop')) + '</button>'
          : '<button type="button" class="b st" data-a="start">▶ ' + esc(L('Iniciar', 'Start')) + '</button>') +
      '<span class="ksa-m">' + esc((d.last_run ? L('Última revisión: ', 'Last check: ') + d.last_run : L('Aún no revisó', 'Not run yet')) + ' · ' + pend + L(' señal(es) esperando', ' signal(s) waiting')) + '</span></div>' +
      '<div class="ksa-m" data-msg style="margin-top:6px"></div>';
    var log = (d.log || []).slice(-6).reverse();
    if (log.length) h += '<div class="log">' + log.map(function (e) {
      return esc((e.ts || '') + ' · ' + (e.ticker ? e.ticker + ' ' : '') + (e.action ? e.action.toUpperCase() + ' ' + (e.confidence != null ? e.confidence + '/100 ' : '') : '') + (e.msg || e.reason || '') + (e.skipped ? ' — ' + e.skipped : ''));
    }).join('<br>') + '</div>';
    el.innerHTML = h + '</div>';
    var msg = el.querySelector('[data-msg]');
    el.querySelectorAll('button[data-a]').forEach(function (b) {
      b.addEventListener('click', function () {
        var start = b.getAttribute('data-a') === 'start', body = {};
        if (start) {
          el.querySelectorAll('[data-k]').forEach(function (x) {
            var k = x.getAttribute('data-k');
            body[k] = k === 'universe' ? String(x.value || '').split(/[\s,;]+/).map(function (t) { return t.trim().toUpperCase(); }).filter(Boolean)
              : (k === 'mode' ? x.value : +x.value);
          });
        }
        b.disabled = true; msg.textContent = L('Enviando…', 'Sending…');
        W._tradeFetch('/api/trade/agent/' + (start ? 'start' : 'stop'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }, true)
          .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
          .then(function (x) {
            if (!x.ok) { msg.textContent = '⚠ ' + ((isEn() ? x.j.error_en : x.j.error) || x.j.error || 'error'); b.disabled = false; return; }
            setTimeout(function () { agentBox(el); }, 600);
          })
          .catch(function (e) { msg.textContent = '⚠ ' + String(e && e.message || e); b.disabled = false; });
      });
    });
  }

  W.KhipuSignals = { poll: poll, render: render, take: take, dismiss: dismiss, agentBox: agentBox, _card: card };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
