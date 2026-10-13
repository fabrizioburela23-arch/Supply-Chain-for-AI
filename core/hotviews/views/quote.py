"""V4 Quote con SELLO (INFRA_OPERATIVA §4.2; paso 14): la cotización que ya existe (core.quotes.fetch_quotes_live,
caché de 15 s, cascada Finnhub→Yahoo) + un sello uniforme para que quien la use (chat, voz, alertas de precio,
precio de referencia de órdenes) sepa de dónde viene y qué tan vieja es — sin una llamada a Finnhub por alerta.

    stamped(['NVDA', 'TSM']) → {'NVDA': {px, prev, pct, currency, stamp: {src, as_of, age_s, live, stale, ttl_s}}}

Vista VIVA: no pertenece a una generación del grafo (lleva su propia versión: `as_of` de cada cotización).
"""
import time

STALE_AFTER_S = 15 * 60        # una cotización de más de 15 min ya no es "en vivo" (se dice, nunca se oculta)
_STATS = {'calls': 0, 'symbols': 0, 'cached': 0, 'last_ms': None}


def _px(q):
    for k in ('live', 'close', 'c', 'price'):
        v = q.get(k)
        if isinstance(v, bool):
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if f == f and f > 0:
            return f
    return None


def stamp_of(q):
    """Sello de una cotización de core.quotes (contrato MKT.quotes de CLAUDE.md)."""
    age = q.get('age_seconds')
    try:
        age = None if age is None else float(age)
    except (TypeError, ValueError):
        age = None
    src = q.get('src') or q.get('provider')
    return {'src': src, 'via': q.get('via'), 'as_of': q.get('as_of'), 'age_s': None if age is None else int(age),
            'live': bool(isinstance(q.get('live'), (int, float)) and not isinstance(q.get('live'), bool)
                         and age is not None and age <= STALE_AFTER_S),
            'stale': bool(age is None or age > STALE_AFTER_S), 'ttl_s': 15}


def stamped(symbols, fetch=None):
    """{SÍMBOLO: {px, prev, pct, currency, stamp}} — solo los que algún proveedor devolvió (nunca se inventa)."""
    from core import quotes
    t0 = time.perf_counter()
    res = (fetch or quotes.fetch_quotes_live)(list(symbols or [])[:quotes.LIVE_MAX_TICKERS]) or {}
    out = {}
    for sym, q in (res.get('quotes') or {}).items():
        if not isinstance(q, dict):
            continue
        px = _px(q)
        if px is None:
            continue
        prev = q.get('prev')
        try:
            prev = float(prev) if prev is not None else None
        except (TypeError, ValueError):
            prev = None
        pct = q.get('pct')
        if pct is None and prev:
            pct = round((px / prev - 1) * 100, 2)
        out[sym] = {'px': px, 'prev': prev, 'pct': pct, 'currency': q.get('currency'),
                    'converted': q.get('converted'), 'stamp': stamp_of(q)}
    _STATS['calls'] += 1
    _STATS['symbols'] += len(out)
    _STATS['cached'] += int(bool(res.get('cached')))
    _STATS['last_ms'] = round((time.perf_counter() - t0) * 1000, 2)
    return out


def price(symbol, fetch=None):
    """(px, stamp) de UN símbolo o (None, None)."""
    r = stamped([symbol], fetch=fetch)
    if not r:
        return None, None
    v = next(iter(r.values()))
    return v['px'], v['stamp']


def stats():
    return dict(_STATS)
