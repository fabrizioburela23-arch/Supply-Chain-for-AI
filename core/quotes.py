"""core/quotes.py — cotización cruda compartida (server rutas + agentes de alertas).

MULTI-MERCADO (pedido de Fabrizio 2026-07: "info de todos los mercados, no solo
los gringos"): los símbolos con sufijo de bolsa (688825.SS Shanghái, 1347.HK
Hong Kong, 6239.TW Taipéi, 7203.T Tokio, 005930.KS Seúl, .L/.DE/.PA/.AS Europa,
.NS India…) se cotizan vía Yahoo Finance y se convierten SIEMPRE a USD con el
tipo de cambio en vivo (cacheado 1 h) — mostrar yuanes con el símbolo $ sería
mentirle al usuario. El resto de la app sigue operando 100% en USD.
"""
import time

import requests as _requests

from core.config import FINNHUB
from core.http import _safe_get

_YH = {'User-Agent': 'Mozilla/5.0 (compatible; Khipu/1.0)'}
_FX_CACHE = {}    # 'CNY' → (ts, tasa_a_usd)
_INTL_CACHE = {}  # símbolo → (ts, quote)


def _fetch_quote_raw(ticker, timeout=None):
    """Cotización cruda de Finnhub para un ticker ya saneado. Devuelve
    (data, error) — reusada por las rutas HTTP y por el evaluador de alertas
    (ontology/agents.py) para no duplicar la llamada. El caller debe checar
    FINNHUB antes de llamar (aquí asumimos que la key existe).
    timeout: los loops batch usan 4s para no colgar el request completo."""
    url = f'https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB}'
    return _safe_get(url, timeout=timeout) if timeout else _safe_get(url)


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
    Devuelve {close, prev, live, pct, vol, currency, converted} o None.
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
        cur = meta.get('currency') or 'USD'
        fx = _fx_to_usd(cur)
        if fx is None:
            return None            # sin tasa de cambio no se publica un precio falso
        close, prev = closes[-1] * fx, closes[-2] * fx
        live = float(meta.get('regularMarketPrice') or closes[-1]) * fx
        q = {'close': round(close, 4), 'prev': round(prev, 4), 'live': round(live, 4),
             'pct': round((live - prev) / prev * 100, 3) if prev else 0,
             'vol': meta.get('regularMarketVolume', 0),
             'currency': cur, 'converted': cur != 'USD'}
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


def fetch_quotes_batch_yahoo(symbols, chunk=40, timeout=10):
    """Cotización + capitalización EN LOTE (Yahoo v7 quote, `chunk` símbolos
    por pedido). Devuelve {símbolo: {mcap_b (USD), price, currency,
    change_pct}}; los símbolos sin dato se omiten (nunca se inventan)."""
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
            cur = (q.get('currency') or q.get('financialCurrency') or 'USD')
            cur = 'GBP' if cur == 'GBp' else cur.upper()
            if cur not in rates:          # una consulta por moneda por lote (también si falla)
                rates[cur] = _fx_to_usd(cur)
            rate = rates[cur]
            mc = q.get('marketCap')
            row = {'price': q.get('regularMarketPrice'), 'currency': q.get('currency'),
                   'change_pct': q.get('regularMarketChangePercent'),
                   'mcap_b': round(float(mc) * rate / 1e9, 2) if (mc and rate and float(mc) > 0) else None}
            if row['mcap_b'] is not None or row['price'] is not None:
                out[sym] = row
                if row['mcap_b'] is not None:
                    _MCAP_CACHE[sym] = (time.time(), row['mcap_b'])
    return out
