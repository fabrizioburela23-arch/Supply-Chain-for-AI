"""core/quotes.py — cotización cruda compartida (server rutas + agentes de alertas).

MULTI-MERCADO (pedido de Fabrizio 2026-07: "info de todos los mercados, no solo
los gringos"): los símbolos con sufijo de bolsa (688825.SS Shanghái, 1347.HK
Hong Kong, 6239.TW Taipéi, 7203.T Tokio, 005930.KS Seúl, .L/.DE/.PA/.AS Europa,
.NS India…) se cotizan vía Yahoo Finance y se convierten SIEMPRE a USD con el
tipo de cambio en vivo (cacheado 1 h) — mostrar yuanes con el símbolo $ sería
mentirle al usuario. El resto de la app sigue operando 100% en USD.
"""
import threading
import os
import time
from concurrent.futures import ThreadPoolExecutor, wait as _wait
from datetime import datetime, timezone

import requests as _requests

from core.config import FINNHUB
from core.http import _safe_get

_YH = {'User-Agent': 'Mozilla/5.0 (compatible; Khipu/1.0)'}
_FX_CACHE = {}    # 'CNY' → (ts, tasa_a_usd)
_INTL_CACHE = {}  # símbolo → (ts, quote)

# ── Circuito abierto para Finnhub (2026-10-04) ───────────────────────────────
# El plan gratuito corta con HTTP 429 cuando se agota la cuota por minuto.
# Antes cada ticker seguía golpeando a Finnhub (quemando más cuota y tardando)
# aunque ya sabíamos que estaba cerrado. Ahora, tras un 429, Finnhub queda en
# PAUSA 60 s y la cascada va directo a Yahoo; /api/quotes/live y
# /api/market/providers exponen `finnhub_quota: true` para que la UI lo diga.
FINNHUB_PAUSE_S = 60
_FH_CIRCUIT = {'until': 0.0, 'hits': 0, 'last_429': None}
_FH_LOCK = threading.Lock()


def finnhub_quota_active():
    """True mientras Finnhub está en pausa por cuota (HTTP 429)."""
    with _FH_LOCK:
        return time.time() < _FH_CIRCUIT['until']


def finnhub_pause(seconds=FINNHUB_PAUSE_S):
    with _FH_LOCK:
        _FH_CIRCUIT['until'] = time.time() + seconds
        _FH_CIRCUIT['hits'] += 1
        _FH_CIRCUIT['last_429'] = datetime.now(timezone.utc).isoformat()


def finnhub_resume():
    """Cierra el circuito (tests / reinicio manual)."""
    with _FH_LOCK:
        _FH_CIRCUIT['until'] = 0.0


def finnhub_circuit_state():
    with _FH_LOCK:
        rem = max(0, int(_FH_CIRCUIT['until'] - time.time()))
        return {'paused': rem > 0, 'seconds_left': rem, 'hits': _FH_CIRCUIT['hits'],
                'last_429': _FH_CIRCUIT['last_429']}


def _fetch_quote_raw(ticker, timeout=None):
    """Cotización cruda de Finnhub para un ticker ya saneado. Devuelve
    (data, error) — reusada por las rutas HTTP y por el evaluador de alertas
    (ontology/agents.py) para no duplicar la llamada. El caller debe checar
    FINNHUB antes de llamar (aquí asumimos que la key existe).
    timeout: los loops batch usan 4s para no colgar el request completo.
    Con el circuito abierto (HTTP 429 reciente) NO llama: devuelve el error de
    pausa para que la cascada siga con Yahoo sin gastar cuota."""
    if finnhub_quota_active():
        return None, ('Finnhub en pausa por cuota (HTTP 429 reciente) / '
                      'Finnhub paused after quota (recent HTTP 429)')
    url = f'https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB}'
    data, err = _safe_get(url, timeout=timeout) if timeout else _safe_get(url)
    if err and 'HTTP 429' in err:
        finnhub_pause()
    return data, err


def is_intl(symbol):
    """¿Símbolo de bolsa no-estadounidense? (sufijo Yahoo: 688825.SS, 1347.HK…)
    Finnhub free no los cubre — van directo a Yahoo, sin quemar la llamada."""
    return '.' in (symbol or '')


def _fx_to_usd(cur):
    """Tasa cur→USD vía Yahoo ({CUR}USD=X), cacheada 1 h. Si Yahoo falla se usa
    la última tasa conocida; sin tasa alguna → None (no se inventa)."""
    if not cur or cur == 'USD':
        return 1.0
    e = _FX_CACHE.get(cur)
    if e and time.time() - e[0] < 3600:
        return e[1]
    try:
        r = _requests.get(
            f'https://query1.finance.yahoo.com/v8/finance/chart/{cur}USD=X',
            params={'interval': '1d', 'range': '5d'}, headers=_YH, timeout=6)
        m = ((r.json().get('chart') or {}).get('result') or [None])[0]
        rate = (m or {}).get('meta', {}).get('regularMarketPrice')
        if rate:
            _FX_CACHE[cur] = (time.time(), float(rate))
            return float(rate)
    except Exception:  # noqa: BLE001
        pass
    return e[1] if e else None


def fetch_quote_intl(symbol, timeout=6):
    """Cotización de CUALQUIER bolsa del mundo vía Yahoo, SIEMPRE en USD.
    Devuelve {close, prev, live, pct, vol, currency, converted, ts, market_state} o None.
    `currency` = moneda ORIGINAL de la bolsa; `converted`=True si se aplicó
    tipo de cambio. Caché 20 s por símbolo (los batch no martillan a Yahoo)."""
    e = _INTL_CACHE.get(symbol)
    if e and time.time() - e[0] < 20:
        return e[1]
    try:
        r = _requests.get(
            f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}',
            params={'interval': '1d', 'range': '5d'}, headers=_YH, timeout=timeout)
        res = ((r.json().get('chart') or {}).get('result') or [None])[0]
        if not res:
            return None
        meta = res.get('meta', {})
        closes = [c for c in (res.get('indicators', {}).get('quote', [{}])[0]
                              .get('close') or []) if c is not None]
        if len(closes) < 2:
            return None
        raw_cur = meta.get('currency') or 'USD'
        # R9 (misión de reparación): Yahoo cotiza Londres en PENIQUES (GBp), Sudáfrica en
        # centavos (ZAc), Israel en agorot (ILA): el precio va ÷100 ANTES del tipo de
        # cambio (antes BA.L salía ×100 en "$"). `currency` devuelve la moneda ENTERA.
        minor = _MINOR_UNITS.get(raw_cur)
        cur = minor[0] if minor else str(raw_cur).upper()
        div = float(minor[1]) if minor else 1.0
        fx = _fx_to_usd(cur)
        if fx is None:
            return None            # sin tasa de cambio no se publica un precio falso
        close, prev = closes[-1] / div * fx, closes[-2] / div * fx
        live = float(meta.get('regularMarketPrice') or closes[-1]) / div * fx
        q = {'close': round(close, 4), 'prev': round(prev, 4), 'live': round(live, 4),
             'pct': round((live - prev) / prev * 100, 3) if prev else 0,
             'vol': meta.get('regularMarketVolume', 0),
             'currency': cur, 'converted': cur != 'USD', 'minor_unit': raw_cur if minor else None,
             # hora REAL del precio (UNIX) y estado del mercado (REGULAR/CLOSED/
             # PRE/POST): sin esto la UI no podía decir "hace 3 min" vs "cierre"
             'ts': meta.get('regularMarketTime'),
             'market_state': meta.get('marketState')}
        if len(_INTL_CACHE) > 500:
            _INTL_CACHE.clear()
        _INTL_CACHE[symbol] = (time.time(), q)
        return q
    except Exception:  # noqa: BLE001
        return None


# ── Capitalización vía Yahoo (bolsas fuera de EE.UU.) ───────────────────────
# El endpoint /v7/finance/quote exige una "crumb" ligada a una cookie de
# sesión: se obtiene una vez (fc.yahoo.com → getcrumb) y se reutiliza ~1 h.
_Y_SESS = {'s': None, 'crumb': None, 'ts': 0}
_MCAP_CACHE = {}   # símbolo → (ts, mcap_b)


def _yahoo_session():
    if _Y_SESS['s'] is not None and time.time() - _Y_SESS['ts'] < 3600:
        return _Y_SESS['s'], _Y_SESS['crumb']
    s = _requests.Session()
    s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'})
    try:
        s.get('https://fc.yahoo.com', timeout=6)
        r = s.get('https://query2.finance.yahoo.com/v1/test/getcrumb', timeout=6)
        crumb = (r.text or '').strip() if r.ok else None
    except Exception:  # noqa: BLE001
        crumb = None
    _Y_SESS.update({'s': s, 'crumb': crumb, 'ts': time.time()})
    return s, crumb


def fetch_market_cap_yahoo(symbol, timeout=6):
    """Capitalización en MILES DE MILLONES de USD vía Yahoo, o None.
    Cacheada 6 h por símbolo (cambia despacio y no conviene martillar)."""
    if not symbol:
        return None
    e = _MCAP_CACHE.get(symbol)
    if e and time.time() - e[0] < 6 * 3600:
        return e[1]
    val = None
    try:
        s, crumb = _yahoo_session()
        params = {'symbols': symbol}
        if crumb:
            params['crumb'] = crumb
        r = s.get('https://query2.finance.yahoo.com/v7/finance/quote', params=params, timeout=timeout)
        res = (((r.json() or {}).get('quoteResponse') or {}).get('result') or [None])[0] or {}
        mc = res.get('marketCap')
        # marketCap viene en la moneda de COTIZACIÓN ('currency'); 'GBp'
        # (peniques) es solo el precio — la capitalización ya está en libras
        cur = (res.get('currency') or res.get('financialCurrency') or 'USD')
        cur = 'GBP' if cur == 'GBp' else cur.upper()
        if mc and float(mc) > 0:
            rate = _fx_to_usd(cur)
            if rate:
                val = round(float(mc) * rate / 1e9, 2)
    except Exception:  # noqa: BLE001
        val = None
    if val is not None:
        _MCAP_CACHE[symbol] = (time.time(), val)
    else:
        # la sesión pudo caducar: forzar una nueva la próxima vez
        _Y_SESS['ts'] = 0
    return val


_MINOR_UNITS = {'GBp': ('GBP', 100), 'ZAc': ('ZAR', 100), 'ILA': ('ILS', 100)}


def fetch_quotes_batch_yahoo(symbols, chunk=40, timeout=10):
    """Cotización + capitalización EN LOTE (Yahoo v7 quote, `chunk` símbolos
    por pedido). Devuelve {símbolo: {mcap_b (USD), price (moneda local),
    price_usd, currency, change_pct}}; los símbolos sin dato se omiten (nunca
    se inventan)."""
    out, rates = {}, {}
    syms = [s for s in dict.fromkeys(symbols or []) if s]
    for i in range(0, len(syms), chunk):
        part = syms[i:i + chunk]
        try:
            s, crumb = _yahoo_session()
            params = {'symbols': ','.join(part)}
            if crumb:
                params['crumb'] = crumb
            r = s.get('https://query2.finance.yahoo.com/v7/finance/quote', params=params, timeout=timeout)
            if r.status_code in (401, 403):
                _Y_SESS['ts'] = 0          # crumb caducado → sesión nueva
                s, crumb = _yahoo_session()
                if crumb:
                    params['crumb'] = crumb
                r = s.get('https://query2.finance.yahoo.com/v7/finance/quote', params=params, timeout=timeout)
            rows = (((r.json() or {}).get('quoteResponse') or {}).get('result')) or []
        except Exception:  # noqa: BLE001
            rows = []
        for q in rows:
            sym = q.get('symbol')
            if not sym:
                continue
            raw_cur = (q.get('currency') or q.get('financialCurrency') or 'USD')
            # Yahoo cotiza algunas bolsas en SUBUNIDADES (GBp = peniques, ZAc =
            # centavos sudafricanos, ILA = agorot): el precio va ÷100; la
            # capitalización ya viene en la moneda entera.
            minor = _MINOR_UNITS.get(raw_cur)
            cur = minor[0] if minor else raw_cur.upper()
            if cur not in rates:          # una consulta por moneda por lote (también si falla)
                rates[cur] = _fx_to_usd(cur)
            rate = rates[cur]
            mc = q.get('marketCap')
            px = q.get('regularMarketPrice')
            px_usd = None
            try:
                if px is not None and rate:
                    px_usd = round(float(px) / (minor[1] if minor else 1) * rate, 4)
            except (TypeError, ValueError):
                px_usd = None
            row = {'price': px, 'currency': q.get('currency'),
                   # precio YA en USD (tipo de cambio en vivo): es el único que
                   # puede pintarse con "$" en la Terminal/Mercado
                   'price_usd': px_usd,
                   # R9: hora REAL del precio y estado del mercado (no la hora del lote)
                   'ts': q.get('regularMarketTime'), 'market_state': q.get('marketState'),
                   'change_pct': q.get('regularMarketChangePercent'),
                   'mcap_b': round(float(mc) * rate / 1e9, 2) if (mc and rate and float(mc) > 0) else None}
            if row['mcap_b'] is not None or row['price'] is not None:
                out[sym] = row
                if row['mcap_b'] is not None:
                    _MCAP_CACHE[sym] = (time.time(), row['mcap_b'])
    return out


# ── Lote EN VIVO por la capa de proveedores (2026-10-04) ────────────────────
# ÚNICA función detrás de /api/quote, /api/quotes y /api/quotes/live.
# Antes había tres rutas con tres cascadas distintas y el lote iba en SERIE
# (100 tickers × ~0,4 s = 40 s por petición) y solo cubría 100 de 569.
# Ahora: cascada Finnhub→Yahoo de core/providers (TODO ticker, también EE.UU.),
# en PARALELO (pool compartido de 8 hilos = tope de salida del proceso), con
# caché de 15 s por frozenset(tickers) Y por ticker (los lotes del cliente se
# solapan entre pestañas) protegida por un lock — patrón de core/live_caps.
LIVE_TTL_S = 15
LIVE_MAX_TICKERS = 150
LIVE_WORKERS = 8
LIVE_DEADLINE_S = max(1.0, min(60.0, float(os.getenv('LIVE_DEADLINE_S') or 8)))   # R11: ~8 s (antes 25): lo que falte entra por la caché
LIVE_BACKLOG_MAX = 400        # R11: tareas pendientes en el pool por encima de esto → no se encola más (degraded)
_LIVE_CACHE = {'batches': {}, 'tickers': {}, 'inflight': {}}
_LIVE_LOCK = threading.Lock()
_LIVE_POOL = {'ex': None}


def _live_pool():
    with _LIVE_LOCK:
        if _LIVE_POOL['ex'] is None:
            _LIVE_POOL['ex'] = ThreadPoolExecutor(max_workers=LIVE_WORKERS,
                                                  thread_name_prefix='quotes-live')
        return _LIVE_POOL['ex']


def _age_seconds(iso):
    try:
        dt = datetime.fromisoformat(str(iso).replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0, int((datetime.now(timezone.utc) - dt).total_seconds()))
    except (TypeError, ValueError):
        return None


def live_row_from_quote(q):
    """make_quote() (core/providers/base) → fila del contrato /api/quotes/live:
    {close, prev, pct, live:<precio numérico>, provider, as_of, age_seconds,
    currency, converted, vol, market_state}. `live` es SIEMPRE un número (la
    UI hacía parseFloat(q.live) y antes podía llegar un booleano)."""
    if not q or q.get('price') is None:
        return None
    price = q.get('price')
    prev = q.get('prev_close')
    pct = q.get('change_pct')
    if pct is None and prev:
        try:
            pct = round((float(price) - float(prev)) / float(prev) * 100, 3)
        except (TypeError, ValueError, ZeroDivisionError):
            pct = None
    return {'close': price, 'prev': prev, 'pct': pct, 'live': price,
            'provider': q.get('provider') or '', 'as_of': q.get('as_of'),
            'age_seconds': q.get('age_seconds'),
            'currency': q.get('currency') or 'USD', 'converted': bool(q.get('converted')),
            'vol': q.get('volume'), 'market_state': q.get('market_state')}


def _live_payload(rows, cached):
    quotes = {}
    provs = set()
    for sym, r in rows.items():
        if not r:
            continue
        rr = dict(r)
        age = _age_seconds(rr.get('as_of'))
        if age is not None:
            rr['age_seconds'] = age
        quotes[sym] = rr
        if rr.get('provider'):
            provs.add(rr['provider'])
    return {'quotes': quotes, 'n': len(quotes), 'cached': bool(cached),
            'as_of': datetime.now(timezone.utc).isoformat(),
            'providers': sorted(provs),
            'finnhub_quota': finnhub_quota_active()}


def live_cache_clear():
    with _LIVE_LOCK:
        _LIVE_CACHE['batches'].clear()
        _LIVE_CACHE['tickers'].clear()
        _LIVE_CACHE['inflight'].clear()


def fetch_quotes_live(tickers, registry=None, ttl=LIVE_TTL_S, deadline=LIVE_DEADLINE_S):
    """Cotizaciones EN VIVO de hasta LIVE_MAX_TICKERS tickers, en paralelo.
    `registry` inyectable (tests): objeto con get_quote(sym) → (quote, intentos).
    Devuelve {quotes:{T:{…}}, n, cached, as_of, providers, finnhub_quota}.
    Un ticker sin dato en ningún proveedor simplemente no aparece (nunca se
    inventa). Si un proveedor se cuelga más allá de `deadline`, se responde
    con lo que haya y el resto entra a la caché al terminar."""
    from core.http import _safe_ticker
    syms = []
    for t in tickers or []:
        s = _safe_ticker(t)
        if s and s not in syms:
            syms.append(s)
    syms = syms[:LIVE_MAX_TICKERS]
    if not syms:
        return _live_payload({}, cached=False)
    key = frozenset(syms)
    now = time.time()
    rows, pending = {}, []
    with _LIVE_LOCK:
        hit = _LIVE_CACHE['batches'].get(key)
        if hit and now - hit[0] < ttl:
            return _live_payload(hit[1], cached=True)
        for s in syms:
            e = _LIVE_CACHE['tickers'].get(s)
            if e and now - e[0] < ttl:
                rows[s] = e[1]
            else:
                pending.append(s)

    _not_done = set()
    degraded = False
    if pending:
        if registry is None:
            from core.providers.market import market_registry
            registry = market_registry()

        def _one(sym):
            try:
                q, _intentos = registry.get_quote(sym)
            except Exception:  # noqa: BLE001 — un proveedor roto no tumba el lote
                q = None
            return sym, live_row_from_quote(q)

        def _store(fut):
            try:
                sym, row = fut.result()
            except Exception:  # noqa: BLE001
                return
            with _LIVE_LOCK:
                _LIVE_CACHE['tickers'][sym] = (time.time(), row)
                if _LIVE_CACHE['inflight'].get(sym) is fut:
                    _LIVE_CACHE['inflight'].pop(sym, None)
                if len(_LIVE_CACHE['tickers']) > 5000:
                    _LIVE_CACHE['tickers'].clear()

        # R11: registro de futuros EN VUELO — un ticker que ya está consultándose se
        # espera, no se vuelve a encolar (antes cada lote repetido duplicaba el trabajo
        # y el backlog del pool crecía sin tope mientras 12 hilos de gunicorn esperaban).
        pool = _live_pool()
        futs, fresh = [], []
        with _LIVE_LOCK:
            try:
                backlog = pool._work_queue.qsize()
            except Exception:  # noqa: BLE001
                backlog = 0
            for sym in pending:
                f = _LIVE_CACHE['inflight'].get(sym)
                if f is None or f.done():
                    if backlog >= LIVE_BACKLOG_MAX:
                        degraded = True
                        continue
                    f = pool.submit(_one, sym)
                    _LIVE_CACHE['inflight'][sym] = f
                    fresh.append(f)
                    backlog += 1
                futs.append(f)
        for f in fresh:                 # fuera del lock: si ya terminó, el callback corre aquí y toma el lock
            f.add_done_callback(_store)
        done, _not_done = _wait(futs, timeout=deadline) if futs else (set(), set())
        for f in done:
            try:
                sym, row = f.result()
            except Exception:  # noqa: BLE001
                continue
            rows[sym] = row

    out = {s: r for s, r in rows.items() if r}
    partial = bool(pending) and bool(_not_done)
    with _LIVE_LOCK:
        # R9: un lote que NO terminó antes del deadline no se guarda como lote completo
        # (las filas que llegan tarde entran a la caché por ticker; el próximo pedido
        # se arma desde ahí). Antes el lote truncado se servía 15 s como "cached".
        if not partial:
            _LIVE_CACHE['batches'][key] = (time.time(), out)
        if len(_LIVE_CACHE['batches']) > 64:
            oldest = sorted(_LIVE_CACHE['batches'].items(), key=lambda kv: kv[1][0])[:16]
            for k, _ in oldest:
                _LIVE_CACHE['batches'].pop(k, None)
    res = _live_payload(out, cached=False)
    res['partial'] = partial or degraded
    res['degraded'] = degraded
    return res
