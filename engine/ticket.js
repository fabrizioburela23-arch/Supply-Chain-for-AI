/* engine/ticket.js — MODO TICKET del panel de trading (2026-10-30, pedido de Fabrizio).
   Dos modos en el MISMO panel (se elige arriba del botón; queda guardado en localStorage 'kh_trade_mode'):
     · 'broker' (por defecto) — como siempre: confirmar + PIN → Alpaca (papel 🧪 o real 🔴). No cambia nada.
     · 'ticket'              — NO envía NADA a ningún bróker: arma el ticket de la orden (qué, cuánto, a qué precio, por qué
                               ojo), le pasa revisiones LOCALES sobre tu cartera y lo deja listo para copiar a Interactive
                               Brokers (o cualquier otro). Después «Ya lo ejecuté» anota lo que de verdad pasó en tu cartera
                               (engine/pfstore.js: la misma cartera de Mercado, Terminal y chat).
   Regla de oro del dinero (CLAUDE.md): este archivo NUNCA llama a /api/trade ni a un bróker; no crea otro camino de órdenes
   (tests/test_ticket_mode.py lo vigila). Se carga DESPUÉS de engine/app_trade_panel.js y envuelve sus funciones. */
(function () {
  'use strict';
  var KEY = 'kh_trade_mode';
  var TP_MAX_NOTIONAL = 100000;           // mismo tope por orden que el panel y el server
  var STALE_MS = 15 * 60 * 1000;          // un precio más viejo que esto se avisa
  var nodeId = '';

  var T = {
    es: {
      mode: 'Destino de la orden', broker: 'Enviar a Alpaca (papel o real)', ticket: 'Solo ticket (IBKR / manual) — no envía nada',
      tipTicket: '📝 Modo ticket: Khipus NO envía la orden a ningún bróker. Te arma el ticket para copiarlo a tu bróker.',
      btn: 'CREAR TICKET', title: '📝 TICKET — NO ENVIADO', buy: 'COMPRAR', sell: 'VENDER',
      market: 'a mercado', limit: 'límite', ref: 'Precio de referencia', est: 'Monto estimado', pf: 'Tu cartera activa',
      checks: 'Revisiones locales (sobre tu cartera, no del bróker)', ok: 'Sin alertas.',
      wQty: 'Introduce una cantidad válida', wLimit: 'Precio límite inválido: debe ser mayor que 0',
      wMax: 'La orden supera el máximo de $100,000 por orden (cantidad × precio).',
      wNoPx: 'No hay precio de referencia: confirma el precio en tu bróker antes de enviar.',
      wStale: 'El precio de referencia tiene {m} min: puede estar desactualizado.',
      wNotLive: 'El precio no es en vivo (cierre anterior o de respaldo).',
      wBuyLimit: 'Tu límite de compra está {p}% por ENCIMA del precio: se ejecutaría al instante y quizá más caro de lo que quieres.',
      wSellLimit: 'Tu límite de venta está {p}% por DEBAJO del precio: se ejecutaría al instante y quizá más barato de lo que quieres.',
      wFar: 'Tu límite está {p}% lejos del precio: puede no ejecutarse nunca.',
      wConc: 'Esta orden pesa {p}% de tu cartera (más de 10%): ojo con la concentración.',
      wSellMore: 'Vendes {q} pero tu cartera anotada tiene solo {h} de {s}.',
      wNoPf: 'No se pudo leer tu cartera: no se revisó el peso de la orden.',
      copy: '📋 Copiar ticket', copied: 'Ticket copiado ✓', done: '✔ Ya lo ejecuté (anotar en mi cartera)', drop: 'Descartar',
      rec: 'Anota lo que PASÓ en tu bróker', recQty: 'Cantidad ejecutada', recPx: 'Precio de ejecución', recSave: 'Guardar en mi cartera',
      recBad: 'Cantidad o precio inválidos', recNoNode: 'No sé a qué empresa del grafo corresponde: ábrela desde el mapa o Mercado y repite.',
      recOk: '✓ Anotado en tu cartera: {s} {q}× {t} a ${p}', discarded: 'Ticket descartado — no se envió nada.',
      note: 'Khipus no ejecuta este ticket: tú lo pones en tu bróker. Información, no asesoría financiera.',
      cp_head: 'TICKET (no enviado)', cp_when: 'Fecha', cp_src: 'Generado por Khipus Finance Intelligence'
    },
    en: {
      mode: 'Order destination', broker: 'Send to Alpaca (paper or real)', ticket: 'Ticket only (IBKR / manual) — sends nothing',
      tipTicket: '📝 Ticket mode: Khipus does NOT send the order to any broker. It builds a ticket you copy into your broker.',
      btn: 'CREATE TICKET', title: '📝 TICKET — NOT SENT', buy: 'BUY', sell: 'SELL',
      market: 'market', limit: 'limit', ref: 'Reference price', est: 'Estimated amount', pf: 'Your active portfolio',
      checks: 'Local checks (on your portfolio, not the broker\'s)', ok: 'No alerts.',
      wQty: 'Enter a valid quantity', wLimit: 'Invalid limit price: it must be greater than 0',
      wMax: 'The order exceeds the $100,000 per-order limit (quantity × price).',
      wNoPx: 'No reference price: confirm the price at your broker before sending.',
      wStale: 'The reference price is {m} min old: it may be out of date.',
      wNotLive: 'The price is not live (previous close or fallback).',
      wBuyLimit: 'Your buy limit is {p}% ABOVE the price: it would fill instantly, maybe higher than you want.',
      wSellLimit: 'Your sell limit is {p}% BELOW the price: it would fill instantly, maybe lower than you want.',
      wFar: 'Your limit is {p}% away from the price: it may never fill.',
      wConc: 'This order is {p}% of your portfolio (over 10%): watch concentration.',
      wSellMore: 'You sell {q} but your recorded portfolio holds only {h} of {s}.',
      wNoPf: 'Could not read your portfolio: order weight was not checked.',
      copy: '📋 Copy ticket', copied: 'Ticket copied ✓', done: '✔ I executed it (record in my portfolio)', drop: 'Discard',
      rec: 'Record what HAPPENED at your broker', recQty: 'Executed quantity', recPx: 'Execution price', recSave: 'Save to my portfolio',
      recBad: 'Invalid quantity or price', recNoNode: 'I do not know which graph company this is: open it from the map or Market and retry.',
      recOk: '✓ Recorded in your portfolio: {s} {q}× {t} at ${p}', discarded: 'Ticket discarded — nothing was sent.',
      note: 'Khipus does not execute this ticket: you place it at your broker. Information, not financial advice.',
      cp_head: 'TICKET (not sent)', cp_when: 'Date', cp_src: 'Generated by Khipus Finance Intelligence'
    }
  };
  function lang() { return (window.LANG || '') === 'en' ? 'en' : 'es'; }
  function t(k, v) {
    var s = (T[lang()][k] != null ? T[lang()][k] : T.es[k]) || k;
    if (v) Object.keys(v).forEach(function (x) { s = s.split('{' + x + '}').join(String(v[x])); });
    return s;
  }
  function getMode() { try { return localStorage.getItem(KEY) === 'ticket' ? 'ticket' : 'broker'; } catch (e) { return 'broker'; } }
  function setMode(m) { try { localStorage.setItem(KEY, m === 'ticket' ? 'ticket' : 'broker'); } catch (e) {} }
  function $(id) { return document.getElementById(id); }
  function el(tag, attrs, kids) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === 'text') n.textContent = attrs[k]; else if (k === 'style') n.style.cssText = attrs[k]; else n.setAttribute(k, attrs[k]);
    });
    (kids || []).forEach(function (c) { if (c) n.appendChild(typeof c === 'string' ? document.createTextNode(c) : c); });
    return n;
  }
  function money(n) { return '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  function status(color, text) { var s = $('tp-order-status'); if (s) { s.style.color = color; s.textContent = text; } }

  // ── selector de modo (inyectado una vez, encima del botón de enviar) ─────────────────────────────
  function paintMode() {
    var m = getMode(), sel = $('tp-mode-sel'), tip = $('tp-mode-tip'), btn = $('tp-submit-btn'), lbl = $('tp-mode-lbl');
    if (lbl) lbl.textContent = t('mode');
    if (sel) {
      sel.options[0].textContent = t('broker'); sel.options[1].textContent = t('ticket'); sel.value = m;
    }
    if (tip) { tip.textContent = m === 'ticket' ? t('tipTicket') : ''; tip.style.display = m === 'ticket' ? '' : 'none'; }
    if (btn) {
      if (m === 'ticket') { btn.textContent = t('btn'); btn.setAttribute('data-tkt', '1'); }
      else if (btn.getAttribute('data-tkt')) { btn.removeAttribute('data-tkt'); if (typeof window._tpRelabel === 'function') { try { window._tpRelabel(); } catch (e) {} } }
    }
    if (m !== 'ticket') { var c = $('tp-ticket-card'); if (c) c.remove(); }
  }
  function inject() {
    var btn = $('tp-submit-btn');
    if (!btn || $('tp-mode-sel')) return;
    var sel = el('select', { id: 'tp-mode-sel', class: 'tp-input', 'aria-label': 'mode' }, [el('option', { value: 'broker' }), el('option', { value: 'ticket' })]);
    sel.addEventListener('change', function () { setMode(sel.value); paintMode(); });
    var box = el('div', { class: 'tp-card', id: 'tp-mode-box' }, [
      el('label', { class: 'tp-label', id: 'tp-mode-lbl', for: 'tp-mode-sel', style: 'display:block' }), sel,
      el('div', { id: 'tp-mode-tip', style: 'font-size:11px;margin-top:6px;color:#fbbf24;display:none' })]);
    btn.parentNode.insertBefore(box, btn);
    paintMode();
  }

  // ── revisiones locales ───────────────────────────────────────────────────────────────────────────
  function portfolioValue() {
    var pos = (window.MKT && MKT.pos) || {}, q = (window.MKT && MKT.quotes) || {}, total = 0, any = false;
    Object.keys(pos).forEach(function (id) {
      var p = pos[id], n = window.NODE_BY_ID && NODE_BY_ID[id], tk = n && n.ticker, px = 0;
      var qq = tk && q[tk];
      if (qq && window.quotePx) px = quotePx(qq);
      if (!(px > 0)) px = +p.bp || 0;                       // sin precio vivo: su costo (aviso en el valor)
      total += (+p.sh || 0) * px; any = true;
    });
    return any ? total : 0;
  }
  function buildChecks(o) {
    var w = [];
    if (!(o.ref > 0)) w.push(t('wNoPx'));
    if (o.q && typeof window.quoteIsLive === 'function' && o.ref > 0 && !window.quoteIsLive(o.q)) w.push(t('wNotLive'));
    if (o.asOf) {
      var ms = Date.now() - Date.parse(o.asOf);
      if (isFinite(ms) && ms > STALE_MS) w.push(t('wStale', { m: Math.round(ms / 60000) }));
    }
    if (o.type === 'limit' && o.ref > 0 && o.limit > 0) {
      var d = (o.limit / o.ref - 1) * 100;
      if (o.side === 'buy' && d > 1) w.push(t('wBuyLimit', { p: d.toFixed(1) }));
      else if (o.side === 'sell' && d < -1) w.push(t('wSellLimit', { p: Math.abs(d).toFixed(1) }));
      else if (Math.abs(d) > 15) w.push(t('wFar', { p: Math.abs(d).toFixed(1) }));
    }
    var pv = portfolioValue();
    if (pv > 0 && o.total > 0) {
      var share = o.total / (pv + (o.side === 'buy' ? o.total : 0)) * 100;
      if (share > 10) w.push(t('wConc', { p: share.toFixed(1) }));
    } else if (!(pv > 0)) w.push(t('wNoPf'));
    if (o.side === 'sell' && nodeId && window.MKT && MKT.pos) {
      var held = (MKT.pos[nodeId] && +MKT.pos[nodeId].sh) || 0;
      if (o.qty > held) w.push(t('wSellMore', { q: o.qty, h: held, s: o.symbol }));
    }
    return w;
  }

  // ── texto del ticket (para copiar) ───────────────────────────────────────────────────────────────
  function ticketText(o) {
    var lines = [t('cp_head'), (o.side === 'buy' ? t('buy') : t('sell')) + ' ' + o.qty + ' × ' + o.symbol + (o.label && o.label !== o.symbol ? ' (' + o.label + ')' : ''),
      (o.type === 'limit' ? t('limit') + ' ' + money(o.limit) : t('market')) + ' · TIF ' + String(o.tif).toUpperCase()];
    if (o.ref > 0) lines.push(t('ref') + ': ' + money(o.ref) + (o.src ? ' (' + o.src + ')' : ''));
    if (o.total > 0) lines.push(t('est') + ': ' + money(o.total));
    lines.push(t('cp_when') + ': ' + new Date().toISOString().slice(0, 16).replace('T', ' ') + ' UTC', t('cp_src'));
    return lines.join('\n');
  }
  function copyText(s) {
    function fb() {
      var ta = el('textarea', { style: 'position:fixed;left:-9999px' }); ta.value = s; document.body.appendChild(ta); ta.select();
      var ok = false; try { ok = document.execCommand('copy'); } catch (e) {} ta.remove(); return ok;
    }
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(s).then(function () { return true; }, function () { return fb(); });
    return Promise.resolve(fb());
  }

  // ── anotar la ejecución real en la cartera activa ────────────────────────────────────────────────
  function record(o, q, px) {
    if (!nodeId || !window.MKT) return { ok: false, msg: t('recNoNode') };
    if (!(q > 0) || !(px > 0)) return { ok: false, msg: t('recBad') };
    MKT.pos = MKT.pos || {};
    var cur = MKT.pos[nodeId] || { sh: 0, bp: 0 }, sh = +cur.sh || 0, bp = +cur.bp || 0;
    if (o.side === 'buy') { var n = sh + q; MKT.pos[nodeId] = { sh: n, bp: n > 0 ? (sh * bp + q * px) / n : px }; }
    else { var rest = sh - q; if (rest > 1e-9) MKT.pos[nodeId] = { sh: rest, bp: bp }; else delete MKT.pos[nodeId]; }
    if (typeof window.savePos === 'function') window.savePos();
    else if (window.KhipuPfStore) window.KhipuPfStore.applyView(MKT.pos);
    return { ok: true, msg: t('recOk', { s: o.side === 'buy' ? t('buy') : t('sell'), q: q, t: o.symbol, p: px.toFixed(2) }) };
  }

  function showTicket(o) {
    var old = $('tp-ticket-card'); if (old) old.remove();
    var warns = buildChecks(o);
    var card = el('div', { id: 'tp-ticket-card', class: 'tp-card', style: 'border:1px dashed #fbbf24;margin-top:10px' });
    card.appendChild(el('div', { style: 'font-weight:700;color:#fbbf24;margin-bottom:6px', text: t('title') }));
    card.appendChild(el('div', { style: 'font-size:13px;margin-bottom:4px', text: (o.side === 'buy' ? t('buy') : t('sell')) + ' ' + o.qty + ' × ' + o.symbol + ' · ' + (o.type === 'limit' ? t('limit') + ' ' + money(o.limit) : t('market')) + ' · ' + String(o.tif).toUpperCase() }));
    if (o.ref > 0) card.appendChild(el('div', { style: 'font-size:12px;opacity:.8', text: t('ref') + ': ' + money(o.ref) + (o.src ? ' (' + o.src + ')' : '') }));
    if (o.total > 0) card.appendChild(el('div', { style: 'font-size:12px;opacity:.8', text: t('est') + ': ' + money(o.total) }));
    card.appendChild(el('div', { style: 'font-size:12px;margin-top:8px;font-weight:600', text: t('checks') }));
    if (!warns.length) card.appendChild(el('div', { style: 'font-size:12px;color:#4ade80', text: '✓ ' + t('ok') }));
    warns.forEach(function (x) { card.appendChild(el('div', { style: 'font-size:12px;color:#fbbf24', text: '⚠ ' + x })); });
    var acts = el('div', { style: 'display:flex;gap:6px;flex-wrap:wrap;margin-top:10px' });
    var bCopy = el('button', { type: 'button', class: 'tp-btn', text: t('copy') });
    bCopy.addEventListener('click', function () { copyText(ticketText(o)).then(function (ok) { if (ok) status('#4ade80', t('copied')); }); });
    var bDone = el('button', { type: 'button', class: 'tp-btn', text: t('done') });
    var bDrop = el('button', { type: 'button', class: 'tp-btn', text: t('drop') });
    bDrop.addEventListener('click', function () { card.remove(); status('rgba(229,226,225,0.55)', t('discarded')); });
    bDone.addEventListener('click', function () {
      if ($('tp-ticket-rec')) return;
      var iq = el('input', { type: 'number', class: 'tp-input', min: '0', step: 'any', value: String(o.qty), 'aria-label': t('recQty') });
      var ip = el('input', { type: 'number', class: 'tp-input', min: '0', step: '0.01', value: o.ref > 0 ? String(o.type === 'limit' ? o.limit : o.ref.toFixed(2)) : '', 'aria-label': t('recPx') });
      var bSave = el('button', { type: 'button', class: 'tp-btn', text: t('recSave') });
      var rec = el('div', { id: 'tp-ticket-rec', style: 'margin-top:10px' }, [el('div', { style: 'font-size:12px;font-weight:600', text: t('rec') }),
        el('label', { class: 'tp-label', style: 'display:block', text: t('recQty') }), iq, el('label', { class: 'tp-label', style: 'display:block', text: t('recPx') }), ip, bSave]);
      bSave.addEventListener('click', function () {
        var r = record(o, parseFloat(iq.value), parseFloat(ip.value));
        if (r.ok) { card.remove(); status('#4ade80', r.msg); try { if (typeof window._tpRefreshPositions === 'function') window._tpRefreshPositions(); } catch (e) {} }
        else status('#f87171', r.msg);
      });
      card.appendChild(rec);
    });
    [bCopy, bDone, bDrop].forEach(function (b) { acts.appendChild(b); });
    card.appendChild(acts);
    card.appendChild(el('div', { style: 'font-size:11px;opacity:.65;margin-top:8px', text: t('note') }));
    var anchor = $('tp-order-status'); anchor.parentNode.insertBefore(card, anchor.nextSibling);
    status('#fbbf24', '📝 ' + (o.side === 'buy' ? t('buy') : t('sell')) + ' ' + o.qty + '× ' + o.symbol);
  }

  // ── envolver las funciones del panel (el modo 'broker' queda INTACTO) ────────────────────────────
  function wrap() {
    var origOpen = window.openTradePanelFn, origSubmit = window.submitTradePanelOrder, origRelabel = window._tpRelabel;
    if (typeof origOpen === 'function') window.openTradePanelFn = function (id, ticker, label) { nodeId = id || ''; return origOpen.apply(this, arguments); };
    if (typeof origRelabel === 'function') window._tpRelabel = function () { var r = origRelabel.apply(this, arguments); paintMode(); return r; };
    if (typeof origSubmit === 'function') window.submitTradePanelOrder = function () {
      if (getMode() !== 'ticket') return origSubmit.apply(this, arguments);
      var symbol = ($('tp-ticker-badge') || {}).textContent || '';
      var qty = parseFloat(($('tp-qty') || {}).value);
      var sideBtn = $('tp-side-sell-btn');
      var side = sideBtn && sideBtn.classList.contains('active') ? 'sell' : 'buy';
      var type = (($('tp-order-type') || {}).value) === 'limit' ? 'limit' : 'market';
      var tif = (($('tp-tif') || {}).value) || 'day';
      if (symbol.indexOf('/') >= 0) tif = 'gtc';
      if (!symbol || !isFinite(qty) || qty <= 0) { status('#f87171', t('wQty')); return; }
      var limit = type === 'limit' ? parseFloat(($('tp-limit-price') || {}).value) : 0;
      if (type === 'limit' && !(limit > 0)) { status('#f87171', t('wLimit')); return; }
      var q = (window.MKT && MKT.quotes && MKT.quotes[symbol]) || null;
      var ref = q && window.quotePx ? quotePx(q) : 0;
      var px = type === 'limit' ? limit : ref;
      if (px > 0 && qty * px > TP_MAX_NOTIONAL) { status('#f87171', t('wMax')); return; }
      var src = q && q.src ? q.src + (q.as_of ? ' · ' + String(q.as_of).slice(0, 16).replace('T', ' ') : '') : '';
      var label = (($('tp-ticker-badge') || {}).textContent) || symbol;
      showTicket({ symbol: symbol, label: label, side: side, qty: qty, type: type, limit: limit, tif: tif, ref: ref, total: px > 0 ? qty * px : 0, src: src, asOf: q && q.as_of, q: q });
    };
  }

  window.KhipuTicket = { getMode: getMode, setMode: function (m) { setMode(m); paintMode(); }, text: ticketText, checks: buildChecks, record: record };
  function start() { inject(); wrap(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
