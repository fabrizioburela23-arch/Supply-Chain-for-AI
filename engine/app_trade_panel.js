
/* ===== Professional Trade Panel ===== */
(function(){
  let _tp = { ticker:'', label:'', side:'buy', price:0, prev:0, buyingPower:0, agentRunning:false, chart:null, paper:null, sending:false, ambSig:null,
              acct:null, positions:null, history:null, agent:null };   // últimos datos → re-pintar al cambiar de idioma

  // Textos del panel (regla bilingüe ES/EN). Los fijos llevan data-tpt / -title /
  // -aria / -ph en el HTML; los dinámicos se re-pintan desde _tp.* en _tpRelabel.
  const _TPT = {
    es: {
      close: '✕ Cerrar', closeAria: 'Cerrar el panel de trading',
      chartLbl: 'Gráfico — 1D', chartIntra: '{t} — 1D (intradía)',
      positions: 'Posiciones abiertas', orders: 'Órdenes recientes',
      refresh: '↻ Actualizar', refreshPosTip: 'Volver a cargar las posiciones', refreshOrdTip: 'Volver a cargar las órdenes',
      thTicker: 'Ticker', thQty: 'Cant.', thEntry: 'Entrada', thPrice: 'Precio',
      noPos: 'Sin posiciones abiertas', noOrd: 'Sin órdenes recientes', errLoad: 'No se pudo cargar', errOrd: 'Error al cargar órdenes',
      side: 'Dirección', buy: 'COMPRAR', sell: 'VENDER',
      otype: 'Tipo de orden', otMarket: 'Mercado — ejecución inmediata', otLimit: 'Límite — a un precio concreto',
      limitPx: 'Precio límite', qty: 'Cantidad (acciones)', max: 'MÁX',
      pctTip: 'Usar este % de tu poder de compra',
      tif: 'Vigencia (TIF)', tifDay: 'Day — vence al cierre', tifGtc: 'GTC — hasta cancelar',
      tifIoc: 'IOC — inmediata o cancela', tifFok: 'FOK — completa o cancela',
      risk: 'Calculadora de riesgo', rQty: 'Cantidad', rTotal: 'Total', rCap: '% del capital', rSl: 'Stop-loss',
      submit: 'ENVIAR ORDEN',
      agent: 'AGENTE IA', off: 'APAGADO', analysis: 'ANÁLISIS', auto: 'AUTO',
      mode: 'Modo', modeManual: 'Manual — solo analiza, no ejecuta', modeAuto: 'Auto — analiza y ejecuta órdenes',
      interval: 'Intervalo de análisis', m5: '5 minutos', m15: '15 minutos', m30: '30 minutos', h1: '1 hora',
      maxPos: 'Posición máx. %', sl: 'Stop-loss %', maxLoss: 'Pérdida diaria máx. %',
      start: '▶ INICIAR', stop: '■ DETENER', refreshAgentTip: 'Actualizar el estado del agente',
      log: 'Registro de decisiones', logEmpty: 'El agente no está activo. Inícialo para ver su análisis en tiempo real.',
      last: 'Último: ', executed: 'ejecutado',
      universe: 'Universo de activos', universeNote: 'Los activos analizados son los del grafo con ticker de mercado en EE. UU.',
      bp: 'Poder de compra', equity: 'Patrimonio',
      pinLater: '🔒 El PIN se pedirá al enviar la orden',
      paper: '🧪 SIMULADO', live: '🔴 DINERO REAL',
      st: { filled: 'ejecutada', partially_filled: 'parcial', canceled: 'cancelada', accepted: 'aceptada', new: 'nueva',
            pending_new: 'pendiente', rejected: 'rechazada', expired: 'vencida', done_for_day: 'cerrada (día)' },
    },
    en: {
      close: '✕ Close', closeAria: 'Close the trading panel',
      chartLbl: 'Chart — 1D', chartIntra: '{t} — 1D (intraday)',
      positions: 'Open positions', orders: 'Recent orders',
      refresh: '↻ Refresh', refreshPosTip: 'Reload positions', refreshOrdTip: 'Reload orders',
      thTicker: 'Ticker', thQty: 'Qty', thEntry: 'Entry', thPrice: 'Price',
      noPos: 'No open positions', noOrd: 'No recent orders', errLoad: 'Could not load', errOrd: 'Could not load orders',
      side: 'Side', buy: 'BUY', sell: 'SELL',
      otype: 'Order type', otMarket: 'Market — fills right away', otLimit: 'Limit — at a set price',
      limitPx: 'Limit price', qty: 'Quantity (shares)', max: 'MAX',
      pctTip: 'Use this % of your buying power',
      tif: 'Time in force (TIF)', tifDay: 'Day — expires at the close', tifGtc: 'GTC — until canceled',
      tifIoc: 'IOC — immediate or cancel', tifFok: 'FOK — fill or kill',
      risk: 'Risk calculator', rQty: 'Qty', rTotal: 'Total', rCap: '% of capital', rSl: 'Stop-loss',
      submit: 'SEND ORDER',
      agent: 'AI AGENT', off: 'OFFLINE', analysis: 'ANALYSIS', auto: 'AUTO',
      mode: 'Mode', modeManual: 'Manual — analyzes only, never trades', modeAuto: 'Auto — analyzes and places orders',
      interval: 'Analysis interval', m5: '5 minutes', m15: '15 minutes', m30: '30 minutes', h1: '1 hour',
      maxPos: 'Max position %', sl: 'Stop-loss %', maxLoss: 'Max daily loss %',
      start: '▶ START', stop: '■ STOP', refreshAgentTip: 'Refresh the agent status',
      log: 'Decision log', logEmpty: 'The agent is not running. Start it to see its analysis in real time.',
      last: 'Last: ', executed: 'executed',
      universe: 'Asset universe', universeNote: 'The analyzed assets are the graph companies with a US market ticker.',
      bp: 'Buying power', equity: 'Equity',
      pinLater: '🔒 The PIN will be asked when you send the order',
      paper: '🧪 SIMULATED', live: '🔴 REAL MONEY',
      st: { filled: 'filled', partially_filled: 'partial', canceled: 'canceled', accepted: 'accepted', new: 'new',
            pending_new: 'pending', rejected: 'rejected', expired: 'expired', done_for_day: 'done for day' },
    },
  };
  const _tpt = (k, vars) => {
    const d = _TPT[(window.LANG || '') === 'en' ? 'en' : 'es'];
    let v = d[k] != null ? d[k] : (_TPT.es[k] != null ? _TPT.es[k] : k);
    if (vars) Object.keys(vars).forEach(n => { v = v.split('{' + n + '}').join(vars[n]); });
    return v;
  };

  // Re-etiqueta el panel (fijos + lo dinámico ya cargado) — se llama al abrirlo
  // y en cada cambio de idioma (applyLang, enganche al final de este bloque).
  window._tpRelabel = function() {
    const root = document.getElementById('trade-panel');
    if (!root) return;
    root.querySelectorAll('[data-tpt]').forEach(el => { el.textContent = _tpt(el.dataset.tpt); });
    root.querySelectorAll('[data-tpt-title]').forEach(el => { el.title = _tpt(el.dataset.tptTitle); });
    root.querySelectorAll('[data-tpt-aria]').forEach(el => { el.setAttribute('aria-label', _tpt(el.dataset.tptAria)); });
    root.querySelectorAll('[data-tpt-ph]').forEach(el => { el.placeholder = _tpt(el.dataset.tptPh); });
    if (_tp.ticker) {
      const cl = document.getElementById('tp-chart-label');
      if (cl) cl.textContent = _tpt('chartIntra', { t: _tp.ticker });
    }
    _tpPaintBadge(_tp.paper);
    _tpPaintAccount();
    if (_tp.positions !== null) _tpPaintPositions();
    if (_tp.history !== null) _tpPaintBlotter();
    _tpPaintAgent();
    updateTradePanelRisk();
  };

  window.openTradeModal = function(nodeId, ticker, label) {
    openTradePanelFn(nodeId, ticker, label);
  };

  window.openTradePanelFn = function(nodeId, ticker, label) {
    if (_tp.ticker !== ticker) _tp.ambSig = null;   // el aviso de orden ambigua es de otro ticker
    _tp.ticker = ticker; _tp.label = label || ticker;
    const q = MKT.quotes[ticker] || {};
    _tp.price = quotePx(q);
    _tp.prev  = parseFloat(q.prev || 0) || 0;
    const pct = _tp.prev > 0 ? (_tp.price - _tp.prev) / _tp.prev * 100 : 0;

    document.getElementById('tp-ticker-badge').textContent = ticker;
    document.getElementById('tp-price-badge').textContent = _tp.price > 0 ? '$' + _tp.price.toFixed(2) : '—';
    const chgEl = document.getElementById('tp-chg-badge');
    chgEl.textContent = _tp.prev > 0 ? (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%' : '';
    chgEl.style.color = pct >= 0 ? '#4ade80' : '#f87171';

    document.getElementById('trade-panel').style.display = 'block';
    try { window._tpRelabel(); } catch (e) {}
    setTradePanelSide('buy');
    updateTradePanelRisk();
    // Badge 🧪/🔴 YA, sin PIN: /api/trade/status es público y dice `paper`.
    // /api/trade/account (con PIN) lo confirma después y manda sobre éste.
    if (window._tradeStatusInfo) window._tradeStatusInfo().then(s => {
      if (s && typeof s.paper === 'boolean' && _tp.paper === null) { _tp.paper = s.paper; _tpPaintBadge(s.paper); }
    }).catch(() => {});
    _tpLoadAccount();
    _tpLoadChart(ticker);
    _tpRefreshPositions();
    _tpRefreshBlotter();
    _tpRefreshAgentStatus();
    _tpBuildUniverseChips();
  };

  window.closeTradePanelFn = function() {
    document.getElementById('trade-panel').style.display = 'none';
  };
  // Orden ejecutada/cerrada (aviso de engine/toast.js) → refrescar el panel si está abierto
  window.addEventListener('khipu:order', e => {
    const ph = e && e.detail && e.detail.phase;
    const tp = document.getElementById('trade-panel');
    if ((ph === 'filled' || ph === 'closed') && tp && tp.style.display !== 'none') {
      window.__tradeAcctCache = null;
      _tpRefreshPositions(); _tpRefreshBlotter(); _tpLoadAccount();
    }
  });

  window.setTradePanelSide = function(side) {
    _tp.side = side;
    const buy  = document.getElementById('tp-side-buy-btn');
    const sell = document.getElementById('tp-side-sell-btn');
    // colores por clase (CSS del panel): activo = relleno, inactivo = contorno
    if (buy)  { buy.classList.toggle('active', side === 'buy');   buy.setAttribute('aria-pressed', side === 'buy'); }
    if (sell) { sell.classList.toggle('active', side === 'sell'); sell.setAttribute('aria-pressed', side === 'sell'); }
    const sb = document.getElementById('tp-submit-btn');
    if (sb) { sb.classList.toggle('tp-side-buy', side === 'buy'); sb.classList.toggle('tp-side-sell', side !== 'buy'); }
    updateTradePanelRisk();
  };

  window.updateTradePanelRisk = function() {
    const otype = document.getElementById('tp-order-type').value;
    document.getElementById('tp-limit-row').style.display = otype === 'limit' ? '' : 'none';

    const qty   = parseFloat(document.getElementById('tp-qty').value) || 0;
    const price = _tp.price || 0;
    const total = qty * price;
    const pct   = _tp.buyingPower > 0 ? (total / _tp.buyingPower * 100) : 0;
    const sl    = parseFloat(document.getElementById('tp-agent-sl')?.value || 3);
    const loss  = total * sl / 100;
    const rInfo = document.getElementById('tp-risk-info');
    if (rInfo) rInfo.innerHTML =
      `${_tpt('rQty')}: <b>${_tpE(qty)}</b> × $${price.toFixed(2)}<br>` +
      `${_tpt('rTotal')}: <b>$${total.toLocaleString('en-US',{minimumFractionDigits:2})}</b><br>` +
      `${_tpt('rCap')}: <b style="color:${pct>10?'#f87171':'#4ade80'}">${pct.toFixed(1)}%</b><br>` +
      `${_tpt('rSl')} (${_tpE(sl)}%): <b style="color:#f87171">-$${loss.toFixed(2)}</b>`;
  };

  window.setTradePanelQtyPct = function(pct) {
    if (!_tp.price || !_tp.buyingPower) return;
    const notional = _tp.buyingPower * pct / 100;
    const qty = Math.max(1, Math.floor(notional / _tp.price));
    document.getElementById('tp-qty').value = qty;
    updateTradePanelRisk();
  };

  // ── PIN de trading ────────────────────────────────────────────────────────
  // El server exige X-Trade-Pin (env TRADE_PIN) en todas las rutas /api/trade/*.
  // El manejo del PIN vive en UN solo lugar: window._tradeFetch (primer bloque
  // inline de app.html; lo usan también crypto.js, voice.js y cockpit.js).
  const _tradeFetch = (url, opts, interactive) =>
    window._tradeFetch(url, Object.assign({ channel: 'terminal' }, opts || {}), interactive);   // paso 5: canal
  const _tpL = (es, en) => ((window.LANG || '') === 'en' ? en : es);
  const _tpE = s => (typeof esc === 'function' ? esc(s) : String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])));
  const TP_MAX_NOTIONAL = 100000;              // mismo tope que el server por orden
  const TP_TIFS = ['day', 'gtc', 'ioc', 'fok'];

  // Badge obligatorio 🧪 SIMULADO / 🔴 DINERO REAL según account.paper.
  function _tpPaintBadge(paper) {
    const b = document.getElementById('tp-paper-badge');
    if (!b) return;
    if (paper === true || paper === false) {
      b.textContent = _tpt(paper ? 'paper' : 'live');
      b.className = paper ? 'tp-mode-paper' : 'tp-mode-live';
      b.style.display = '';
    } else {
      b.style.display = 'none';
    }
  }

  // ÚNICO caso en el que se permite la operación simulada LOCAL (portafolio del
  // navegador): el trading NO está configurado en el server (sin TRADE_PIN o
  // sin Alpaca). Cualquier otro fallo (PIN malo, rechazo de Alpaca, red, 5xx,
  // interruptor de apagado) se MUESTRA — nunca se disfraza de "✓ simulada",
  // porque el usuario reintentaría y podría duplicar una orden real.
  function _tpNotConfigured(status, d) {
    const code = d && d.code;
    if (['trading_disabled', 'broker_not_configured', 'alpaca_not_configured', 'not_configured'].indexOf(code) >= 0) return true;
    const msg = String((d && d.error) || '');
    return status === 400 && /ALPACA_KEY/i.test(msg) && /(not configured|sin configurar)/i.test(msg);
  }

  function _tpLocalSim(ticker, side, qty, setS, ord, tid) {
    const node = (window.NODES || []).find(n => n.mkt === ticker);
    const q = (window.MKT && MKT.quotes && MKT.quotes[ticker]) || {};
    const px = quotePx(q) || (parseFloat(q.prev) || 0);
    if (node && px > 0) {
      const cur = (MKT.pos[node.id]) || { sh: 0, bp: px };
      const newSh = side === 'sell' ? Math.max(0, (cur.sh || 0) - qty) : (cur.sh || 0) + qty;
      const bp = side === 'sell' ? (cur.bp || px)
        : (((cur.sh || 0) * (cur.bp || px) + qty * px) / Math.max(1, newSh));
      if (newSh <= 0) delete MKT.pos[node.id]; else MKT.pos[node.id] = { sh: newSh, bp };
      if (typeof savePos === 'function') savePos();
      if (typeof renderMarket === 'function' && typeof activeTab !== 'undefined' && activeTab === 'market') renderMarket(true);
      setS('#fbbf24', _tpL(
        `✓ Operación <b>simulada en tu portafolio local</b> (no hay bróker configurado): ${side.toUpperCase()} ${qty}× ${_tpE(ticker)} @ $${px.toFixed(2)}.<br><span style="font-size:10px;opacity:.7">Para operar en el bróker hay que configurar TRADE_PIN y Alpaca en Railway (revisa 🩺).</span>`,
        `✓ <b>Simulated in your local portfolio</b> (no broker configured): ${side.toUpperCase()} ${qty}× ${_tpE(ticker)} @ $${px.toFixed(2)}.<br><span style="font-size:10px;opacity:.7">To trade on the broker, set TRADE_PIN and Alpaca in Railway (see 🩺).</span>`));
      if (window.KhipuToast) window.KhipuToast.order.result(Object.assign({}, ord || { side, symbol: ticker, qty }, { price: px }), { ok: true, local: true }, tid);
      else if (typeof toast === 'function') toast(_tpL('Simulada (local): ', 'Simulated (local): ') + `${side} ${qty}× ${ticker}`);
    } else {
      const msg = _tpL(
        `No se pudo simular ${ticker}: todavía no hay precio. El trading en el bróker requiere TRADE_PIN y Alpaca (revisa 🩺).`,
        `Could not simulate ${ticker}: no price available yet. Broker trading requires TRADE_PIN and Alpaca (see 🩺).`);
      setS('#f87171', _tpE(msg));
      if (window.KhipuToast) window.KhipuToast.order.result(Object.assign({}, ord || { side, symbol: ticker, qty }, { mode: 'sim' }), { ok: false, error: msg }, tid);
    }
  }

  window.submitTradePanelOrder = async function() {
    const ticker = _tp && _tp.ticker;
    const qtyEl = document.getElementById('tp-qty');
    const qty   = parseFloat(qtyEl && qtyEl.value);
    const side  = (_tp && _tp.side) === 'sell' ? 'sell' : 'buy';
    const otypeEl = document.getElementById('tp-order-type');
    const otype = (otypeEl && otypeEl.value) || 'market';
    const tifEl = document.getElementById('tp-tif');
    let tif     = (tifEl && tifEl.value) || 'day';
    const status = document.getElementById('tp-order-status');
    const setS = (color, html) => { if (status) { status.style.color = color; status.innerHTML = html; } };
    if (_tp.sending) return;                                   // anti doble clic
    if (!ticker || !isFinite(qty) || qty <= 0) { setS('#f87171', _tpL('Introduce una cantidad válida', 'Enter a valid quantity')); return; }
    if (otype !== 'market' && otype !== 'limit') { setS('#f87171', _tpL('Tipo de orden no soportado', 'Unsupported order type')); return; }
    if (TP_TIFS.indexOf(tif) < 0) tif = 'day';
    if (ticker.indexOf('/') >= 0) tif = 'gtc';                // cripto: Alpaca solo acepta gtc/ioc

    const body = { symbol: ticker, qty, side, type: otype, time_in_force: tif };
    if (otype === 'limit') {
      const lp = parseFloat(document.getElementById('tp-limit-price')?.value);
      if (!isFinite(lp) || lp <= 0) { setS('#f87171', _tpL('Precio límite inválido: debe ser mayor que 0', 'Invalid limit price: it must be greater than 0')); return; }
      body.limit_price = lp;
    }
    const refPx = otype === 'limit' ? body.limit_price : (_tp.price || 0);
    if (refPx > 0 && qty * refPx > TP_MAX_NOTIONAL) {
      setS('#f87171', _tpL('La orden supera el máximo de $100,000 por orden (cantidad × precio).', 'The order exceeds the $100,000 per-order limit (quantity × price).'));
      return;
    }
    // ── CONFIRMACIÓN EXPLÍCITA (pop-up): lado, activo, cantidad, tipo,
    // vigencia, monto estimado y cuenta 🧪/🔴. NADA sale sin «Confirmar».
    const KT = window.KhipuToast;
    const ord = { side, symbol: ticker, label: _tp.label, qty, orderType: otype, limitPrice: body.limit_price, tif,
      price: _tp.price || null, mode: _tp.paper === true ? 'paper' : _tp.paper === false ? 'live' : undefined };
    const btn = document.getElementById('tp-submit-btn'); if (btn) btn.disabled = true;
    _tp.sending = true;                                        // también mientras el diálogo está abierto
    let go = false;
    try {
      // dinero: SOLO el diálogo de Khipus; si no cargó, NO se envía (nunca window.confirm)
      go = (KT && KT.confirmOrder) ? await KT.confirmOrder(ord) : false;
    } catch (e) { go = false; }
    if (!go) {
      _tp.sending = false; if (btn) btn.disabled = false;
      setS('rgba(229,226,225,0.55)', _tpL('Orden cancelada — no se envió nada.', 'Order canceled — nothing was sent.'));
      return;
    }

    // client_order_id estable para ESTA orden: si el envío termina en error
    // ambiguo y el usuario reintenta lo mismo, Alpaca rechaza el duplicado.
    const sig = ['panel', ticker, side, otype, qty, body.limit_price || '', tif].join('|');
    body.client_order_id = window._tradeOrderId(sig);
    ord.client_order_id = body.client_order_id;

    setS('rgba(229,226,225,0.6)', _tpL('Enviando…', 'Sending…'));
    const tid = KT ? KT.order.sending(ord) : null;            // aviso: «Enviando orden de compra/venta…»

    let r = null, d = null, netErr = null;
    _tp.ambSig = null;
    try {
      r = await _tradeFetch('/api/trade/order', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body), timeout: 30000 }, true);
      d = await r.json().catch(() => null);
    } catch (e) { netErr = e || new Error('network'); }
    const st = r ? r.status : 0;
    // Modo (obligatorio): la cuenta (_tp.paper) y la respuesta de la orden
    // (d.paper); ante la duda manda DINERO REAL.
    const pp = (_tp.paper === false || (d && d.paper === false)) ? false
      : (_tp.paper === true || (d && d.paper === true)) ? true : null;
    if (pp !== null && _tp.paper === null) { _tp.paper = pp; _tpPaintBadge(pp); }
    const mode = pp === false ? _tpL('🔴 DINERO REAL', '🔴 REAL MONEY') : pp === true ? _tpL('🧪 simulada (papel)', '🧪 simulated (paper)') : '';
    if (pp !== null) ord.mode = pp ? 'paper' : 'live';
    const note = (res) => { if (KT) KT.order.result(ord, res, tid); };

    // PRIMERO el duplicado: el server responde 200 + duplicate:true con la
    // orden que YA existía (mismo client_order_id). No es una orden nueva.
    if (!netErr && r && window._tradeOrderIsDup(st, d)) {
      window._tradeOrderSettle(sig, false);
      const prevSt = d && d.status ? ` (${_tpL('estado', 'status')}: ${_tpE(d.status)})` : '';
      setS('#fbbf24', _tpL(
        `Esta orden ya había llegado al bróker${prevSt} — no se envió dos veces. Revisa «Órdenes recientes». Si quieres OTRA orden igual, vuelve a enviarla.`,
        `This order had already reached the broker${prevSt} — it was not sent twice. Check "Recent orders". If you want ANOTHER identical order, send it again.`));
      if (KT) note({ ok: true, dedup: true, broker_dup: true, data: d });
      else if (typeof toast === 'function') toast(_tpL('Ya estaba en el bróker — no se duplicó', 'Already at the broker — not duplicated'));
      window.__tradeAcctCache = null;
      setTimeout(() => { _tpRefreshPositions(); _tpRefreshBlotter(); }, 800);
    } else if (!netErr && r && r.ok && d && (d.id || d.status)) {
      window._tradeOrderSettle(sig, false);
      setS('#4ade80', `✓ ${side.toUpperCase()} ${qty}× ${_tpE(ticker)} — ${_tpE(d.status || 'accepted')}${mode ? ' · ' + mode : ''}`);
      // aviso «Orden enviada» + sondeo ligero hasta «Compra/Venta ejecutada ✓»
      if (KT) note({ ok: true, data: Object.assign({ client_order_id: body.client_order_id }, d) });
      else if (typeof toast === 'function') toast(_tpL('Orden enviada: ', 'Order sent: ') + `${side} ${qty}× ${ticker}`);
      window.__tradeAcctCache = null;
      setTimeout(() => { _tpRefreshPositions(); _tpRefreshBlotter(); _tpLoadAccount(); }, 2000);
    } else if (!netErr && r && _tpNotConfigured(st, d)) {
      window._tradeOrderSettle(sig, false);
      _tpLocalSim(ticker, side, qty, setS, ord, tid);
    } else if (netErr || window._tradeOrderAmbiguous(st)) {
      // Sin respuesta clara: la orden PUDO haber llegado. Se conserva el
      // client_order_id (también tras recargar, 24 h) para que un reintento
      // idéntico no la duplique; el blotter avisa si aparece.
      window._tradeOrderSettle(sig, true);
      _tp.ambSig = sig;
      const why = (d && (d.offline || st >= 500)) ? _tpL('el servidor no respondió', 'the server did not respond')
        : _tpL('sin respuesta (red o tiempo agotado)', 'no response (network or timeout)');
      setS('#f87171', _tpL(
        `⚠ No se pudo confirmar la orden (${why}). Puede que SÍ haya llegado al bróker: revisa «Órdenes recientes» antes de reintentar. Si reintentas esta misma orden (aunque recargues la página) no se duplicará.`,
        `⚠ The order could not be confirmed (${why}). It MAY have reached the broker: check "Recent orders" before retrying. Retrying this same order (even after reloading the page) will not duplicate it.`));
      note({ ok: false, ambiguous: true, error: _tpL(
        `Motivo: ${why}. Puede que SÍ haya llegado al bróker: revisa «Órdenes recientes» antes de reintentar (reintentar esta misma orden no la duplica).`,
        `Reason: ${why}. It MAY have reached the broker: check "Recent orders" before retrying (retrying this same order will not duplicate it).`) });
      setTimeout(_tpRefreshBlotter, 2500);
    } else {
      window._tradeOrderSettle(sig, false);
      setS('#f87171', '⚠ ' + _tpE(window._tradeErrText(d, st)));
      note({ ok: false, error: window._tradeErrText(d, st) });   // el texto del server tal cual
    }
    _tp.sending = false;
    if (btn) btn.disabled = false;
  };

  async function _tpLoadAccount() {
    const info = document.getElementById('tp-account-info');
    try {
      const r = await _tradeFetch('/api/trade/account');
      const d = await r.json().catch(() => ({}));
      if (r.ok && d && typeof d.paper === 'boolean') { _tp.paper = d.paper; _tpPaintBadge(d.paper); }
      if (r.ok && d.buying_power) _tp.buyingPower = parseFloat(d.buying_power);
      _tp.acct = { ok: r.ok, status: r.status, d: d || {} };
      _tpPaintAccount();
      if (r.ok && d.buying_power) updateTradePanelRisk();
    } catch(e) {}
  }
  function _tpPaintAccount() {
    const info = document.getElementById('tp-account-info');
    const a = _tp.acct;
    if (!info || !a) return;
    const d = a.d || {};
    if (a.ok && d.buying_power) {
      const f0 = v => (parseFloat(v) || 0).toLocaleString('en-US', { maximumFractionDigits: 0 });
      info.textContent = _tpt('bp') + ': $' + f0(d.buying_power) + ' · ' + _tpt('equity') + ': $' + f0(d.equity);
    } else {
      info.textContent = d.code === 'pin_required' ? _tpt('pinLater') : window._tradeErrText(d, a.status);
    }
  }

  async function _tpLoadChart(ticker) {
    const canvas = document.getElementById('tp-chart');
    if (!canvas) return;
    if (_tp.chart) { _tp.chart.destroy(); _tp.chart = null; }
    document.getElementById('tp-chart-label').textContent = _tpt('chartIntra', { t: ticker });
    try {
      // intradía de 5 min por /api/candles (Yahoo, forma Finnhub {s,c,t}). Limpieza 2026-10-11: llamaba a
      // /api/chart/<t>, una ruta que no existe → el gráfico del panel de operaciones salía SIEMPRE vacío
      const r = await fetch(`/api/candles/${encodeURIComponent(ticker)}?range=1d&interval=5m`);
      if (!r.ok) return;
      const data = await r.json();
      const labels = (data.t||[]).map(t=>{ const d=new Date(t*1000); return d.getHours()+':'+(d.getMinutes()<10?'0':'')+d.getMinutes(); });
      const prices = data.c || [];
      if (data.s !== 'ok' || !prices.length) return;
      const cs = getComputedStyle(document.body);
      const tick = (cs.getPropertyValue('--ink-3') || cs.getPropertyValue('--ink-2') || '').trim() || 'rgba(229,226,225,0.4)';
      const grid = (cs.getPropertyValue('--line') || '').trim() || 'rgba(255,255,255,0.04)';
      const color = prices[prices.length-1] >= prices[0] ? '#4ade80' : '#f87171';
      const ctx = canvas.getContext('2d');
      _tp.chart = new Chart(ctx, {
        type:'line',
        data: { labels, datasets: [{ data: prices, borderColor: color, borderWidth: 1.5, pointRadius: 0,
          fill: true, backgroundColor: ctx => {
            const g = ctx.chart.ctx.createLinearGradient(0,0,0,160);
            g.addColorStop(0, color + '33'); g.addColorStop(1, 'transparent');
            return g;
          }}] },
        options: { animation:false, responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}},
          scales:{ x:{ticks:{font:{size:9},maxRotation:0,color:tick},grid:{color:grid}},
                   y:{ticks:{font:{size:9},color:tick},grid:{color:grid}} } }
      });
    } catch(e) {}
  }

  window._tpRefreshPositions = async function() {
    const tbody = document.getElementById('tp-positions-body');
    if (!tbody) return;
    try {
      const d = await _tradeFetch('/api/trade/positions/detail').then(r=>r.json());
      _tp.positions = Array.isArray(d) ? d : [];
    } catch(e) { _tp.positions = 'error'; }
    _tpPaintPositions();
  };
  function _tpPaintPositions() {
    const tbody = document.getElementById('tp-positions-body');
    if (!tbody) return;
    const d = _tp.positions;
    if (d === 'error') { tbody.innerHTML = '<tr><td colspan="6" class="tp-empty" style="color:#f87171">' + _tpE(_tpt('errLoad')) + '</td></tr>'; return; }
    {
      if (!Array.isArray(d) || !d.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="tp-empty">' + _tpE(_tpt('noPos')) + '</td></tr>';
        return;
      }
      const n2 = v => (+v || 0).toFixed(2);
      tbody.innerHTML = d.filter(Boolean).map(p => {
        const u = +p.unrealized || 0, up = +p.unrealized_pct || 0;
        const plColor = u >= 0 ? '#4ade80' : '#f87171';
        return `<tr>
          <td class="tp-mono" style="color:var(--kt-ink);font-weight:600">${_tpE(p.symbol)}</td>
          <td class="tp-mono">${_tpE(p.qty)}</td>
          <td class="tp-mono">$${n2(p.avg_entry)}</td>
          <td class="tp-mono">$${n2(p.current)}</td>
          <td class="tp-mono" style="color:${plColor}">${u >= 0 ? '+' : ''}$${n2(u)}</td>
          <td class="tp-mono" style="color:${plColor}">${up >= 0 ? '+' : ''}${n2(up)}%</td>
        </tr>`;
      }).join('');
    }
  }

  window._tpRefreshBlotter = async function() {
    const el = document.getElementById('tp-blotter-body');
    if (!el) return;
    try {
      const d = await _tradeFetch('/api/trade/history').then(r=>r.json());
      // ¿La orden que quedó AMBIGUA aparece ya en el bróker? → decirlo (el id
      // se conserva: un reintento igual recibe "ya había llegado").
      if (_tp.ambSig && Array.isArray(d)) {
        const hit = window._tradeOrderResolve(_tp.ambSig, d);
        if (hit) {
          _tp.ambSig = null;
          const stEl = document.getElementById('tp-order-status');
          if (stEl) {
            stEl.style.color = '#4ade80';
            stEl.innerHTML = _tpL(
              `✓ Confirmado: la orden SÍ llegó al bróker (estado: ${_tpE(hit.status || '?')}). No hace falta reintentarla.`,
              `✓ Confirmed: the order DID reach the broker (status: ${_tpE(hit.status || '?')}). No need to retry it.`);
          }
        }
      }
      _tp.history = Array.isArray(d) ? d : [];
    } catch(e) { _tp.history = 'error'; }
    _tpPaintBlotter();
  };
  function _tpPaintBlotter() {
    const el = document.getElementById('tp-blotter-body');
    if (!el) return;
    const d = _tp.history;
    if (d === 'error') { el.innerHTML = '<div class="tp-empty" style="color:#f87171">' + _tpE(_tpt('errOrd')) + '</div>'; return; }
    {
      if (!Array.isArray(d) || !d.length) { el.innerHTML = '<div class="tp-empty">' + _tpE(_tpt('noOrd')) + '</div>'; return; }
      el.innerHTML = d.slice(0,20).filter(Boolean).map(o => {
        const ts = new Date(o.created_at||'').toLocaleTimeString((window.LANG||'')==='en'?'en':'es',{hour:'2-digit',minute:'2-digit'});
        const sColor = o.side === 'buy' ? '#4ade80' : '#f87171';
        const stColor = o.status === 'filled' ? '#4ade80' : o.status === 'canceled' ? 'rgba(229,226,225,0.35)' : '#fbbf24';
        const sideTxt = o.side === 'buy' ? _tpt('buy') : o.side === 'sell' ? _tpt('sell') : String(o.side || '').toUpperCase();
        return `<div class="tp-ord">
          <span style="color:var(--kt-ink-3)">${_tpE(ts)}</span>
          <span style="color:${sColor};font-weight:700">${_tpE(sideTxt)}</span>
          <span style="color:var(--kt-ink);overflow:hidden;text-overflow:ellipsis">${_tpE(o.symbol)}</span>
          <span>${(parseFloat(o.qty||o.filled_qty||0)||0).toFixed(0)}×</span>
          <span style="color:${stColor}" title="${_tpE(o.status)}">${_tpE((_tpt('st') || {})[o.status] || o.status)}</span>
        </div>`;
      }).join('');
    }
  }

  window._tpRefreshAgentStatus = async function() {
    try {
      const d = await _tradeFetch('/api/trade/agent/status').then(r=>r.json());
      _tp.agentRunning = !!(d && d.running);
      _tp.agent = d || {};
      _tpPaintAgent();
    } catch(e) {}
  };
  function _tpPaintAgent() {
    const d = _tp.agent || {};
    {
      const badge = document.getElementById('tp-agent-badge');
      const btn   = document.getElementById('tp-agent-start-btn');
      if (badge) {
        badge.textContent = d.running ? (d.mode === 'auto' ? _tpt('auto') : _tpt('analysis')) : _tpt('off');
        badge.style.background = d.running ? 'rgba(56,189,248,0.15)' : '';
        badge.style.color      = d.running ? 'var(--kt-cyan)' : '';
        badge.style.borderColor = d.running ? 'rgba(56,189,248,0.32)' : '';
      }
      if (btn) {
        btn.textContent = d.running ? _tpt('stop') : _tpt('start');
        btn.style.background = d.running ? 'rgba(220,38,38,0.15)' : '';
        btn.style.color = d.running ? '#f87171' : '';
        btn.style.borderColor = d.running ? 'rgba(220,38,38,0.3)' : '';
      }
      const lastEl = document.getElementById('tp-agent-last-run');
      if (lastEl && d.last_run) lastEl.textContent = _tpt('last') + (String(d.last_run).split(' ')[1] || String(d.last_run));

      // El log trae texto de la IA (razones) → SIEMPRE escapado.
      const logEl = document.getElementById('tp-agent-log');
      if (logEl && Array.isArray(d.log) && d.log.length) {
        logEl.innerHTML = d.log.slice().reverse().filter(Boolean).map(entry => {
          const lvl = /^(info|success|warn|error)$/.test(entry.level || '') ? entry.level : 'info';
          const cls = 'tp-log-' + lvl;
          const act = String(entry.action || '');
          const ticker = entry.ticker ? `<b style="color:#e5e2e1">${_tpE(entry.ticker)}</b> ` : '';
          const action = act ? `<span style="color:${act==='buy'?'#4ade80':act==='sell'?'#f87171':'#a8a8b3'}">[${_tpE(act.toUpperCase())}]</span> ` : '';
          const conf   = entry.confidence != null ? `<span style="color:rgba(229,226,225,0.4)">(${_tpE(entry.confidence)}%)</span> ` : '';
          const exec   = entry.executed ? `<span style="color:#4ade80">✓ ${_tpE(_tpt('executed'))}</span>` : '';
          const msg    = entry.msg ? `<span>${_tpE(entry.msg)}</span>` : '';
          return `<div class="${cls}" style="border-bottom:1px solid rgba(255,255,255,0.04);padding:2px 0">
            <span style="color:rgba(229,226,225,0.3)">${_tpE(entry.ts)} </span>${ticker}${action}${conf}<span style="color:rgba(229,226,225,0.6)">${_tpE(entry.reason||'')}</span>${exec}${msg}
          </div>`;
        }).join('');
        logEl.scrollTop = 0;
      }
    }
  }

  // Universo del agente: solo tickers de EE. UU. operables en Alpaca (sin
  // sufijos de bolsa extranjera tipo .HK/.AS/.T). El server lo vuelve a sanear.
  function _tpUniverse() {
    return (window.NODES || []).map(n => n && n.mkt).filter(t => typeof t === 'string' && /^[A-Z]{1,5}(\.[AB])?$/.test(t))
      .filter((t, i, a) => a.indexOf(t) === i).slice(0, 30);
  }

  window.toggleTradingAgent = async function() {
    const logEl = document.getElementById('tp-agent-log');
    const showErr = (d, st) => {
      if (logEl) logEl.insertAdjacentHTML('afterbegin', `<div class="tp-log-error" style="padding:2px 0">⚠ ${_tpE(window._tradeErrText(d, st))}</div>`);
    };
    try {
      if (_tp.agentRunning) {
        const r = await _tradeFetch('/api/trade/agent/stop', {method:'POST'}, true);
        if (!r.ok) showErr(await r.json().catch(() => null), r.status);
        setTimeout(_tpRefreshAgentStatus, 500);
      } else {
        const mode = document.getElementById('tp-agent-mode').value === 'auto' ? 'auto' : 'manual';
        if (mode === 'auto' && _tp.paper === false) {
          showErr({ error: 'El modo Auto no se permite con DINERO REAL: usa Manual (solo analiza) o una cuenta de papel.',
                    error_en: 'Auto mode is not allowed with REAL MONEY: use Manual (analysis only) or a paper account.' }, 0);
          return;
        }
        const body = {
          mode,
          interval_min:     parseInt(document.getElementById('tp-agent-interval').value),
          max_pos_pct:      parseFloat(document.getElementById('tp-agent-maxpos').value),
          stop_loss_pct:    parseFloat(document.getElementById('tp-agent-sl').value),
          max_daily_loss_pct: parseFloat(document.getElementById('tp-agent-maxloss').value),
          universe: _tpUniverse(),
        };
        const r = await _tradeFetch('/api/trade/agent/start', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)}, true);
        if (!r.ok) showErr(await r.json().catch(() => null), r.status);
        setTimeout(_tpRefreshAgentStatus, 800);
      }
    } catch (e) {
      showErr({ error: 'Error de red — el servidor no respondió', error_en: 'Network error — the server did not respond' }, 0);
    }
  };

  function _tpBuildUniverseChips() {
    const el = document.getElementById('tp-universe-chips');
    if (!el) return;
    el.innerHTML = _tpUniverse().map(t => `<span>${_tpE(t)}</span>`).join('');
  }

  // Cambio de idioma (botón EN/ES → applyLang) → re-etiquetar el panel (mismo
  // patrón que window._termRelabel de la Terminal).
  if (typeof applyLang === 'function') {
    const _applyLangTP = applyLang;
    applyLang = function() { _applyLangTP.apply(this, arguments); try { window._tpRelabel(); } catch (e) {} };
  }
  try { window._tpRelabel(); } catch (e) {}

})();
