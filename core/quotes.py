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
