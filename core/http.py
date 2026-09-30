"""core/http.py — llamadas upstream saneadas y límite de tasa (compartidos
entre server, ontology y matrix).

`rate_limit` vivía en server.py, lo que dejaba a los blueprints (matrix/,
ontology/) sin forma de limitarse sin importar el server — justo la
dependencia circular que core/ existe para romper. Los buckets son en memoria
del proceso: correcto con gunicorn a 1 worker (ver CLAUDE.md), no compartidos
entre procesos.

Endurecimiento (auditoría estructural 2026-09-30, #7/#13):
  · la IP del límite es el ÚLTIMO salto de X-Forwarded-For (core.pin.client_ip:
    lo añade el proxy de Railway); el primero lo escribe el cliente → rotarlo
    daba cupo ilimitado;
  · los buckets van bajo un lock (8 hilos) y se podan (antes crecían sin fin);
  · `redact_secrets()` quita valores de keys y patrones key=/token=/Bearer de
    cualquier texto que vaya a un cliente o al log; `_safe_get` ya NO devuelve
    str(e) (la URL de Finnhub lleva `token=` y viajaba en el error).
"""
import logging
import os
import re
import threading
import time
from collections import defaultdict
from functools import wraps

import requests
from flask import jsonify

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


# ── Redacción de secretos ───────────────────────────────────────────────────
# Variables cuyo VALOR nunca debe salir en un error (ni al cliente ni al log).
SECRET_ENV_NAMES = (
    'ANTHROPIC_KEY', 'ANTHROPIC_API_KEY', 'CLAUDE_KEY', 'GEMINI_KEY', 'GOOGLE_API_KEY', 'NVIDIA_KEY',
    'NVIDIA_API_KEY', 'FINNHUB_KEY', 'FINNHUB_WS_KEY', 'FMP_KEY', 'MARKETSTACK_KEY', 'AV_KEY',
    'ALPHA_VANTAGE_KEY', 'ELEVENLABS_KEY', 'ALPACA_KEY', 'ALPACA_SECRET', 'ALPACA_OAUTH_CLIENT_SECRET',
    'TRADE_PIN', 'KHIPU_ADMIN_SECRET', 'SECRET_KEY', 'TAVILY_KEY', 'TAVILY_API_KEY', 'COINGECKO_KEY',
    'NEO4J_PASSWORD', 'BROKERAGE_ENC_KEY', 'MCP_STATIC_TOKEN', 'DATABASE_URL', 'REDIS_URL',
)
_MASK = '••••'
# key=… / token=… / apikey=… en URLs o textos (la URL de Finnhub lleva &token=).
# El nombre puede llevar PREFIJOS separados por _ o - (access_key= de
# Marketstack, x_cg_demo_api_key= de CoinGecko, x-api-key:): antes el \b
# inicial los dejaba pasar. El inicio exige un borde "de token" (ni letra, ni
# dígito, ni _/-) → sin retroceso cuadrático, y 'monkey:' no se tapa.
_QS_SECRET_RE = re.compile(
    r'(?i)(?<![A-Za-z0-9_\-])((?:[A-Za-z0-9]+[_-])*'
    r'(?:api[_-]?key|apikey|access[_-]?key|access[_-]?token|auth[_-]?token|token|secret|client[_-]?secret|'
    r'password|passwd|key)\s*[=:]\s*)[^&\s"\'<>,;)}]+')
_BEARER_RE = re.compile(r'(?i)\b(bearer\s+)[A-Za-z0-9._~+/=\-]{6,}')
_HDR_SECRET_RE = re.compile(
    r'(?i)((?:x-goog-api-key|x-api-key|xi-api-key|apca-api-key-id|apca-api-secret-key|x-trade-pin|'
    r'x-admin-secret|authorization)["\']?\s*[:=]\s*["\']?)[^\s"\',}]+')
# esquema acotado a 32 caracteres: con '*' un texto tipo '-a-a-a…' costaba O(n²) (ReDoS)
_DSN_PASS_RE = re.compile(r'(?i)\b([a-z][a-z0-9+.\-]{0,31}://[^:/\s@]+:)[^@\s/]+@')


def secret_values(min_len=6, extra=()):
    """Valores actuales de las variables secretas (≥ min_len), del más largo al más corto."""
    vals = set()
    for n in SECRET_ENV_NAMES:
        v = (os.getenv(n) or '').strip().strip('"\'')
        if len(v) >= min_len:
            vals.add(v)
    for v in extra or ():
        v = str(v or '').strip()
        if len(v) >= min_len:
            vals.add(v)
    return sorted(vals, key=len, reverse=True)


def redact_secrets(text, extra=(), limit=None, patterns=True, min_len=6):
    """Texto sin secretos: valores exactos de las env de SECRET_ENV_NAMES (+extra)
    y, con patterns=True, los patrones key=/token=/Bearer/cabeceras/DSN. Se
    redacta ANTES de truncar (truncar primero podía dejar medio secreto).
    min_len: valores más cortos no se buscan (un PIN numérico corto podría
    coincidir con cifras legítimas)."""
    s = str(text if text is not None else '')
    for v in secret_values(min_len=min_len, extra=extra):
        if v in s:
            s = s.replace(v, _MASK)
    if patterns:
        s = _DSN_PASS_RE.sub(r'\1' + _MASK + '@', s)
        s = _BEARER_RE.sub(r'\1' + _MASK, s)
        s = _HDR_SECRET_RE.sub(r'\1' + _MASK, s)
        s = _QS_SECRET_RE.sub(r'\1' + _MASK, s)
    return s[:limit] if limit else s


def _safe_get(url, timeout=HTTP_TIMEOUT):
    """GET con manejo de errores uniforme. Devuelve (json, error). El error es
    GENÉRICO (tipo de fallo): str(e) de requests incluye la URL con la key.
    Texto BILINGÜE 'español / english' (regla bilingüe: muchas rutas lo
    devuelven tal cual en {'error': err}); conserva 'HTTP <n>' para quien lo busque."""
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code != 200:
            return None, f'el proveedor respondió HTTP {r.status_code} / upstream HTTP {r.status_code}'
        return r.json(), None
    except requests.exceptions.Timeout:
        return None, 'el proveedor no respondió a tiempo / upstream timeout'
    except requests.exceptions.ConnectionError as e:
        log.info('upstream inalcanzable: %s', redact_secrets(e, limit=200))
        return None, 'no se pudo conectar con el proveedor / upstream unreachable'
    except ValueError:
        return None, 'respuesta no válida del proveedor / upstream invalid JSON'
    except Exception as e:  # noqa: BLE001
        log.info('upstream error: %s', redact_secrets(e, limit=200))
        return None, f'error del proveedor ({type(e).__name__}) / upstream error ({type(e).__name__})'


# ── Límite de tasa en memoria del proceso ───────────────────────────────────
_rate_buckets: dict = defaultdict(list)
_rate_lock = threading.Lock()
_rate_state = {'max_window': 60, 'pruned_at': 0.0}
RATE_MAX_KEYS = 50000          # tope duro de memoria (se descartan las claves más viejas)
RATE_PRUNE_EVERY_S = 60


def _prune_rate_buckets(now):
    """Quita buckets vacíos o sin marcas dentro de la ventana más larga vista."""
    cut = now - _rate_state['max_window']
    for k in [k for k, v in _rate_buckets.items() if not v or v[-1] <= cut]:
        _rate_buckets.pop(k, None)
    if len(_rate_buckets) > RATE_MAX_KEYS:
        for k in sorted(_rate_buckets, key=lambda k: _rate_buckets[k][-1])[:len(_rate_buckets) - RATE_MAX_KEYS]:
            _rate_buckets.pop(k, None)
    _rate_state['pruned_at'] = now


def _rate_limit(key: str, limit: int, window: int) -> bool:
    """Returns True if request is allowed. key=ip+endpoint, limit=max calls, window=seconds."""
    now = time.time()
    with _rate_lock:
        if window > _rate_state['max_window']:
            _rate_state['max_window'] = window
        if now - _rate_state['pruned_at'] > RATE_PRUNE_EVERY_S or len(_rate_buckets) > RATE_MAX_KEYS:
            _prune_rate_buckets(now)
        bucket = [t for t in _rate_buckets.get(key, ()) if now - t < window]
        if len(bucket) >= limit:
            _rate_buckets[key] = bucket
            return False
        bucket.append(now)
        _rate_buckets[key] = bucket
        return True


def _client_ip():
    try:
        from core.pin import client_ip
        return client_ip()
    except Exception:  # noqa: BLE001 — fuera de una petición
        return 'unknown'


def rate_limit(limit: int, window: int = 3600):
    """Decorator: limit calls per IP. limit=max, window=seconds (default 1 hour).
    IP = último salto de X-Forwarded-For (el del proxy de confianza)."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            ip = _client_ip()
            key = f'{ip}:{f.__name__}'
            if not _rate_limit(key, limit, window):
                log.warning('Rate limit hit: %s %s', ip, f.__name__)
                resp = jsonify({'error': 'Demasiadas solicitudes: espera un momento y reintenta',
                                'error_en': 'Rate limit exceeded. Try again later.', 'code': 'rate_limited'})
                resp.headers['Retry-After'] = str(min(window, 60))
                return resp, 429
            return f(*args, **kwargs)
        return wrapper
    return decorator
