"""core/http.py — llamadas upstream saneadas y límite de tasa (compartidos
entre server, ontology y matrix).

`rate_limit` vivía en server.py, lo que dejaba a los blueprints (matrix/,
ontology/) sin forma de limitarse sin importar el server — justo la
dependencia circular que core/ existe para romper. Los buckets son en memoria
del proceso: correcto con gunicorn a 1 worker (ver CLAUDE.md), no compartidos
entre procesos.
"""
import logging
import re
import time
from collections import defaultdict
from functools import wraps

import requests
from flask import jsonify, request

from core.config import HTTP_TIMEOUT

log = logging.getLogger('khipu')

# Tickers válidos: letras, dígitos y los símbolos reales de mercado (., -, ^, =, :).
# Bloquea inyección de parámetros (&token=, ?, espacios) en las URLs upstream.
_TICKER_RE = re.compile(r'^[A-Za-z0-9.\-^=:]{1,15}$')


def _safe_ticker(raw):
    """Valida y normaliza un ticker. Devuelve el símbolo en mayúsculas, o None si
    es inválido. Defensa contra inyección en las llamadas a Finnhub/FMP/etc."""
    if not raw:
        return None
    t = str(raw).strip().upper()
    return t if _TICKER_RE.match(t) else None


def _safe_get(url, timeout=HTTP_TIMEOUT):
    """GET con manejo de errores uniforme. Devuelve (json, error)."""
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code != 200:
            return None, f'upstream {r.status_code}'
        return r.json(), None
    except requests.exceptions.Timeout:
        return None, 'timeout'
    except Exception as e:  # noqa: BLE001
        return None, str(e)[:120]


# ── Límite de tasa en memoria del proceso ───────────────────────────────────
_rate_buckets: dict = defaultdict(list)


def _rate_limit(key: str, limit: int, window: int) -> bool:
    """Returns True if request is allowed. key=ip+endpoint, limit=max calls, window=seconds."""
    now = time.time()
    bucket = _rate_buckets[key]
    _rate_buckets[key] = [t for t in bucket if now - t < window]
    if len(_rate_buckets[key]) >= limit:
        return False
    _rate_buckets[key].append(now)
    return True


def rate_limit(limit: int, window: int = 3600):
    """Decorator: limit calls per IP. limit=max, window=seconds (default 1 hour)."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            ip = request.headers.get('X-Forwarded-For', request.remote_addr or 'unknown').split(',')[0].strip()
            key = f'{ip}:{f.__name__}'
            if not _rate_limit(key, limit, window):
                log.warning('Rate limit hit: %s %s', ip, f.__name__)
                return jsonify({'error': 'Rate limit exceeded. Try again later.'}), 429
            return f(*args, **kwargs)
        return wrapper
    return decorator
