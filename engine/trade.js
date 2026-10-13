/* engine/trade.js — TRADING COMPARTIDO del navegador (lote I4, G5-07: salió TAL CUAL de engine/voice.js).
   Lo usan la voz (engine/voice.js: place_order / get_account_status), la Cabina (engine/cockpit.js, ventana
   'broker') y engine/command_center.js. Se carga ANTES de voice.js (app.html y SHELL de sw.js).
   Regla de oro del dinero: toda orden va por window._tradeFetch (PIN X-Trade-Pin) → POST /api/trade/order →
   brokerage.service (house_order). Nada de aquí envía sin confirmación explícita (clic o «sí» verbal). */
/* ============================================================================
   TRADING COMPARTIDO (Etapa M) — helpers usados por voice.js (tools de Khipu),
   engine/cockpit.js (stage 'broker') y engine/command_center.js. UN solo lugar
   para: resolver el símbolo (cripto → equity), leer la cuenta, ejecutar la
   orden (con guard anti-doble-envío) y abrir el stage del bróker. NO duplicar.
   Contrato server: POST /api/trade/order {symbol, side, notional|qty,
   type:'market'} — cripto usa 'BTC/USD' y el server fuerza time_in_force=gtc.
   Todas las rutas /api/trade/* van por window._tradeFetch (PIN X-Trade-Pin).
   ============================================================================ */
(function () {
  'use strict';

  function tlang() {
    try { return (window.LANG || localStorage.getItem('eco_lang') || 'es'); } catch (e) { return 'es'; }
  }
  function tnorm(s) {
    if (window.KhipuResolve && window.KhipuResolve.norm) return window.KhipuResolve.norm(s);
    return String(s == null ? '' : s).toLowerCase().replace(/\s+/g, ' ').trim();
  }

  // Alias estáticos de cripto (fallback si la lista de Alpaca aún no cargó) —
  // clave normalizada (como la dicta/escribe el usuario) → símbolo base;
  // el par tradeable siempre es <BASE>/USD.
  var CRYPTO_ALIAS = {
    'btc': 'BTC', 'bitcoin': 'BTC', 'bit coin': 'BTC', 'bitcoin core': 'BTC',
    'eth': 'ETH', 'ethereum': 'ETH', 'ether': 'ETH', 'etherium': 'ETH', 'eterium': 'ETH', 'iterium': 'ETH',
    'sol': 'SOL', 'solana': 'SOL',
    'doge': 'DOGE', 'dogecoin': 'DOGE', 'doge coin': 'DOGE', 'dogue coin': 'DOGE',
    'ltc': 'LTC', 'litecoin': 'LTC', 'lite coin': 'LTC',
    'xrp': 'XRP', 'ripple': 'XRP',
    'ada': 'ADA', 'cardano': 'ADA',
    'avax': 'AVAX', 'avalanche': 'AVAX',
    'link': 'LINK', 'chainlink': 'LINK', 'chain link': 'LINK',
    'dot': 'DOT', 'polkadot': 'DOT',
    'shib': 'SHIB', 'shiba': 'SHIB', 'shiba inu': 'SHIB',
    'uni': 'UNI', 'uniswap': 'UNI',
    'aave': 'AAVE',
    'bch': 'BCH', 'bitcoin cash': 'BCH',
    'usdt': 'USDT', 'tether': 'USDT',
    'usdc': 'USDC', 'usd coin': 'USDC',
    'mkr': 'MKR', 'maker': 'MKR',
    'crv': 'CRV', 'curve': 'CRV',
    'xtz': 'XTZ', 'tezos': 'XTZ',
    'bat': 'BAT', 'basic attention token': 'BAT',
    'sushi': 'SUSHI', 'sushiswap': 'SUSHI',
    'grt': 'GRT', 'the graph': 'GRT',
    'pepe': 'PEPE',
  };
  var CRYPTO_LABEL = {
    BTC: 'Bitcoin', ETH: 'Ethereum', SOL: 'Solana', DOGE: 'Dogecoin', LTC: 'Litecoin',
    XRP: 'XRP', ADA: 'Cardano', AVAX: 'Avalanche', LINK: 'Chainlink', DOT: 'Polkadot',
    SHIB: 'Shiba Inu', UNI: 'Uniswap', AAVE: 'Aave', BCH: 'Bitcoin Cash', USDT: 'Tether',
    USDC: 'USD Coin', MKR: 'Maker', CRV: 'Curve', XTZ: 'Tezos', BAT: 'BAT',
    SUSHI: 'SushiSwap', GRT: 'The Graph', PEPE: 'Pepe',
  };

  var _assetsCache = null;   // { ts, list: [{symbol:'BTC/USD', name:'Bitcoin'}, …] }
  async function cryptoAssets() {
    if (_assetsCache && (Date.now() - _assetsCache.ts) < 3600000) return _assetsCache.list;
    if (!window._tradeFetch) return null;
    try {
      // interactive=false: NUNCA pedir el PIN solo para resolver un nombre
      var r = await window._tradeFetch('/api/trade/crypto/assets', { channel: 'voice' }, false);
      if (!r.ok) return null;
      var d = await r.json();
      var list = (d && Array.isArray(d.assets)) ? d.assets : null;
      if (list && list.length) _assetsCache = { ts: Date.now(), list: list };
      return list;
    } catch (e) { return null; }
  }

  // window._resolveTradeSymbol(texto) → Promise<
  //   {ok:true, kind:'crypto'|'equity', symbol:'BTC/USD'|'NVDA', label, node?} |
  //   {ok:false, error (bilingüe, hablable), suggestions:[labels]}>
  // Orden del contrato: cripto primero (alias estático + lista real de Alpaca),
  // después equity vía KhipuResolve → ticker.
  window._resolveTradeSymbol = async function (q) {
    var en = tlang() === 'en';
    var raw = String(q == null ? '' : q).trim().replace(/[?!.]+$/, '').trim();
    if (!raw) return { ok: false, error: en ? 'Which asset?' : '¿Qué activo?', suggestions: [] };

    // ¿ya viene como par cripto? ("BTC/USD", "eth/usd")
    var pair = raw.toUpperCase().match(/^([A-Z0-9]{2,10})\s*\/\s*(USD[TC]?)$/);
    if (pair) return { ok: true, kind: 'crypto', symbol: pair[1] + '/USD', label: CRYPTO_LABEL[pair[1]] || pair[1] };

    var nq = tnorm(raw).replace(/^(de |del |el |la )/, '').trim();
    if (!nq) return { ok: false, error: en ? 'Which asset?' : '¿Qué activo?', suggestions: [] };

    // 1) alias estático de cripto
    var base = CRYPTO_ALIAS[nq] || null;

    // 2) lista real de activos cripto tradeables en Alpaca
    if (!base) {
      var assets = await cryptoAssets();
      if (assets && assets.length) {
        var up = nq.toUpperCase();
        for (var i = 0; i < assets.length; i++) {
          var sym = String(assets[i].symbol || '');
          var b = sym.split('/')[0];
          if (b === up || tnorm(assets[i].name || '') === nq) { base = b; break; }
        }
        if (!base && nq.length >= 4) {
          for (var j = 0; j < assets.length; j++) {
            var nm = tnorm(assets[j].name || '');
            if (nm && (nm.indexOf(nq) === 0 || nq.indexOf(nm) === 0)) {
              base = String(assets[j].symbol || '').split('/')[0];
              break;
            }
          }
        }
      }
    }
    if (base) return { ok: true, kind: 'crypto', symbol: base + '/USD', label: CRYPTO_LABEL[base] || base };

    // 3) equity vía el resolutor compartido (alias de voz, fuzzy, sugerencias)
    if (window.KhipuResolve) {
      var r = window.KhipuResolve.find(raw);
      if (r && r.node) {
        if (r.node.mkt) return { ok: true, kind: 'equity', symbol: r.node.mkt, label: r.node.label, node: r.node };
        return { ok: false, suggestions: [], error: en
          ? (r.node.label + ' is not publicly traded — I cannot place orders on it.')
          : (r.node.label + ' no cotiza en bolsa — no puedo operarla.') };
      }
      var nf = window.KhipuResolve.notFound(raw);
      return { ok: false, error: nf.spoken, suggestions: (nf.suggestions || []).map(function (n) { return n.label; }) };
    }
    return { ok: false, error: en ? ('I could not find "' + raw + '".') : ('No encontré «' + raw + '».'), suggestions: [] };
  };

  // window._tradeAccountInfo(interactive, force) → JSON de la cuenta de Alpaca
  // (+ campo paper) con caché de 30 s. En error devuelve {error, status}: el
  // 403 sin TRADE_PIN trae el mensaje del server TAL CUAL (ya en español).
  window._tradeAccountInfo = async function (interactive, force) {
    var c = window.__tradeAcctCache;
    if (!force && c && (Date.now() - c.ts) < 30000) return c.data;
    if (!window._tradeFetch) return { error: 'trading no disponible' };
    try {
      var r = await window._tradeFetch('/api/trade/account', {}, !!interactive);
      var d = await r.json().catch(function () { return {}; });
      if (!r.ok) return { error: window._tradeErrText ? window._tradeErrText(d, r.status) : ((d && d.error) || ('HTTP ' + r.status)), status: r.status, code: d && d.code };
      window.__tradeAcctCache = { ts: Date.now(), data: d };
      return d;
    } catch (e) { return { error: String((e && e.message) || e) }; }
  };

  // window._executeTradeOrder({symbol, side, notional?|qty?, kind?, label?})
  // → POST /api/trade/order (PIN interactivo). Montos: $1–$100,000 por orden.
  // Guard anti-doble-envío: la MISMA orden (símbolo+lado+monto) en <90 s no se
  // re-envía (la voz y el clic de la Cabina pueden confirmar a la vez).
  window._executeTradeOrder = async function (o) {
    o = o || {};
    var en = tlang() === 'en';
    if (!window._tradeFetch) return { ok: false, error: 'trading no disponible' };
    if (!o.symbol) return { ok: false, error: en ? 'Missing symbol.' : 'Falta el símbolo.' };
    var side = o.side === 'sell' ? 'sell' : 'buy';
    var body = { symbol: o.symbol, side: side, type: 'market' };
    if (o.notional != null && isFinite(+o.notional)) {
      var amt = Math.round(+o.notional * 100) / 100;
      if (!(amt >= 1 && amt <= 100000)) {
        return { ok: false, error: en
          ? 'The amount must be between $1 and $100,000 per order.'
          : 'El monto debe estar entre $1 y $100,000 por orden.' };
      }
      body.notional = amt;
    } else if (o.qty != null && +o.qty > 0) {
      body.qty = +o.qty;
    } else {
      return { ok: false, error: en ? 'Missing order amount.' : 'Falta el monto de la orden.' };
    }
    // el server fuerza gtc para cripto; day para acciones
    body.time_in_force = (o.kind === 'crypto' || o.symbol.indexOf('/') >= 0) ? 'gtc' : 'day';

    var key = body.symbol + '|' + side + '|' + (body.notional || '') + '|' + (body.qty || '');
    // AVISOS pop-up (engine/toast.js): enviando → enviada/rechazada → ejecutada.
    // Solo informan: no cambian qué se envía ni cuándo.
    var KT = window.KhipuToast;
    var info = { side: side, symbol: body.symbol, label: o.label || body.symbol, kind: o.kind,
      notional: body.notional != null ? body.notional : undefined, qty: body.qty != null ? body.qty : undefined };
    var last = window.__lastTradeExec;
    if (last && last.key === key && (Date.now() - last.ts) < 90000) {
      if (KT) KT.order.result(info, { ok: true, dedup: true, data: last.data });
      return { ok: true, dedup: true, data: last.data };
    }
    // La MISMA orden ya en vuelo (sí verbal + clic en la Cabina a la vez) →
    // se espera a esa, no se manda otra.
    var inflight = window.__tradeInflight || (window.__tradeInflight = {});
    if (inflight[key]) {
      return inflight[key].then(function (res) { return res && res.ok ? { ok: true, dedup: true, data: res.data } : res; });
    }
    // client_order_id estable por orden (window._tradeOrderId, app.html): si la
    // respuesta se pierde (red/timeout/5xx) y se reintenta la misma orden,
    // Alpaca rechaza el duplicado en vez de ejecutarla dos veces.
    var sig = 'khipu|' + key;
    if (window._tradeOrderId) body.client_order_id = window._tradeOrderId(sig);
    // paso 16 (INFRA_OPERATIVA §2.5): orden por VOZ → prueba de que el resumen se leyó en voz alta antes del «sí»:
    // sha256 del texto leído + hora de la confirmación (el servidor lo guarda en la decisión; nunca el audio).
    if (o.channel === 'voice' && o.readback) {
      try {
        var _dg = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(String(o.readback)));
        body.readback_sha = Array.prototype.map.call(new Uint8Array(_dg), function (b) {
          return ('0' + b.toString(16)).slice(-2); }).join('');
      } catch (e) {}
      body.confirmed_at = new Date().toISOString();
    }
    info.client_order_id = body.client_order_id;
    var settle = function (ambiguous) { if (window._tradeOrderSettle) window._tradeOrderSettle(sig, ambiguous); };
    var tid = KT ? KT.order.sending(info) : null;
    var p = (async function () {
      try {
        var r = await window._tradeFetch('/api/trade/order', {
          // paso 5 (INFRA_OPERATIVA §2.5): X-Khipu-Channel = canal de quien llama (voz → 'voice'; Cabina → 'ui').
          // Es metadato: nunca autoriza nada.
          channel: o.channel === 'voice' ? 'voice' : 'ui',
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), timeout: 30000,
        }, true);
        var d = await r.json().catch(function () { return null; });
        // PRIMERO el duplicado: el server responde 200 + duplicate:true con la
        // orden que YA existía (mismo client_order_id) — NO es una orden nueva
        // y no se puede anunciar como "orden enviada".
        var isDup = window._tradeOrderIsDup ? window._tradeOrderIsDup(r.status, d)
          : !!(r.ok && d && d.duplicate === true);
        if (isDup) {
          settle(false);
          window.__tradeAcctCache = null;
          return { ok: true, dedup: true, broker_dup: true, data: d || {} };
        }
        if (r.ok && d && (d.id || d.status)) {
          settle(false);
          window.__lastTradeExec = { key: key, ts: Date.now(), data: d };
          window.__tradeAcctCache = null;   // la cuenta cambió — invalidar caché
          return { ok: true, data: d };
        }
        var amb = window._tradeOrderAmbiguous ? window._tradeOrderAmbiguous(r.status) : r.status >= 500;
        settle(amb);
        var msg = window._tradeErrText ? window._tradeErrText(d, r.status) : ((d && (d.error || d.message)) || ('HTTP ' + r.status));
        if (amb) {
          msg = (en ? 'The order could not be confirmed (' : 'No se pudo confirmar la orden (') + msg + ').' + (en
            ? ' It MAY have reached the broker: check your orders before retrying — retrying this same order will not duplicate it.'
            : ' Puede que SÍ haya llegado al bróker: revisa tus órdenes antes de reintentar — reintentar esta misma orden no la duplica.');
        }
        return { ok: false, status: r.status, ambiguous: amb, error: msg };
      } catch (e) {
        settle(true);   // sin respuesta: pudo haber llegado
        return { ok: false, ambiguous: true, error: en
          ? 'No response from the server (network or timeout). The order MAY have reached the broker: check your orders before retrying — retrying this same order will not duplicate it.'
          : 'Sin respuesta del servidor (red o tiempo agotado). Puede que la orden SÍ haya llegado al bróker: revisa tus órdenes antes de reintentar — reintentar esta misma orden no la duplica.' };
      } finally {
        delete inflight[key];
      }
    })();
    inflight[key] = p;
    if (KT) p.then(function (res) {
      try { KT.order.result(info, res, tid); } catch (e) {}
    });
    return p;
  };

  // Abre el stage 'broker' de la Cabina (y abre la Cabina si está cerrada).
  // arg: {} · {confirm:{symbol,side,notional|qty,label,kind}} · etc.
  window._openBrokerStage = function (arg) {
    var ck = window.BixbyCockpit;
    if (!ck) return false;
    try {
      if (ck.isOpen && ck.isOpen()) ck.stage('broker', arg || {});
      else ck.open({ kind: 'broker', arg: arg || {} });
      return true;
    } catch (e) { return false; }
  };
})();
