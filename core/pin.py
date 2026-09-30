"""core/pin.py — verificación ÚNICA del PIN de operador (X-Trade-Pin).

Un solo lugar para: comparar el PIN en tiempo constante, frenar la adivinación
por IP y globalmente (compartido por TODAS las superficies: /api/trade/*,
/api/brokerage/*, /api/mcp/*, escrituras de la ontología), y responder JSON
bilingüe. Antes cada módulo tenía su propio contador → un atacante podía
repartir intentos entre superficies (auditoría estructural 2026-09-30).

La IP es el ÚLTIMO salto de X-Forwarded-For (lo agrega el proxy de Railway);
el primero lo escribe el cliente y se puede falsificar.

Uso:
    from core.pin import require_pin, require_operator, pin_error
    @require_pin            # trading/corretaje: sin TRADE_PIN → 403 (deshabilitado)
    @require_operator       # escrituras de la ontología: sin TRADE_PIN → se permite
                            # (modo desarrollo) con aviso en el log; con TRADE_PIN → exige PIN
"""
import hmac
import logging
import os
import threading
import time
from functools import wraps

from flask import jsonify, request

log = logging.getLogger('khipu')

PIN_MAX_FAILS = 10          # por IP en la ventana
PIN_GLOBAL_MAX = 30         # desde cualquier IP en la ventana → bloqueo global
PIN_WINDOW_S = 600
PIN_MAX_IPS = 5000

_FAILS = {}                 # ip → [ts]
_GLOBAL = []                # [ts]
_LOCK = threading.Lock()
_STATE = {'global_warned_at': 0.0}
_listeners = []             # callbacks(scope, n) al activarse el bloqueo global (p. ej. auditoría)


def client_ip():
    xff = request.headers.get('X-Forwarded-For', '')
    hops = [h.strip() for h in xff.split(',') if h.strip()]
    return (hops[-1] if hops else (request.remote_addr or 'unknown'))[:64]


def on_global_lock(fn):
    """Registra un callback(scope, n) para auditar el bloqueo global."""
    _listeners.append(fn)
    return fn


def _prune(now):
    cut = now - PIN_WINDOW_S
    _GLOBAL[:] = [t for t in _GLOBAL if t > cut]
    for ip in [k for k, v in _FAILS.items() if not v or v[-1] <= cut]:
        _FAILS.pop(ip, None)
    if len(_FAILS) > PIN_MAX_IPS:
        for ip in sorted(_FAILS, key=lambda k: _FAILS[k][-1])[:len(_FAILS) - PIN_MAX_IPS]:
            _FAILS.pop(ip, None)


def configured():
    return bool(os.getenv('TRADE_PIN', ''))


def pin_error(got=None, where='api', strict=True):
    """None si el PIN es válido; si no, (respuesta_json, status).
    strict=False: sin TRADE_PIN configurado se permite (escrituras de ontología
    en desarrollo); con strict=True sin TRADE_PIN → 403 'deshabilitado'."""
    want = os.getenv('TRADE_PIN', '')
    if not want:
        if strict:
            return jsonify({'error': 'Trading deshabilitado — configura TRADE_PIN en Railway',
                            'error_en': 'Trading disabled — set TRADE_PIN in Railway',
                            'code': 'trading_disabled'}), 403
        return None
    ip, now = client_ip(), time.time()
    with _LOCK:
        _prune(now)
        n_global, n_ip = len(_GLOBAL), len(_FAILS.get(ip) or ())
    if n_global >= PIN_GLOBAL_MAX:
        return jsonify({'error': 'Demasiados intentos de PIN fallidos (desde varias direcciones): bloqueado 10 minutos',
                        'error_en': 'Too many failed PIN attempts (from several addresses): locked for 10 minutes',
                        'code': 'pin_locked_global'}), 429
    if n_ip >= PIN_MAX_FAILS:
        return jsonify({'error': 'Demasiados intentos de PIN fallidos: espera 10 minutos',
                        'error_en': 'Too many failed PIN attempts: wait 10 minutes', 'code': 'pin_locked'}), 429
    got = request.headers.get('X-Trade-Pin', '') if got is None else str(got)
    if hmac.compare_digest(got.encode(), want.encode()):
        return None
    fire = False
    with _LOCK:
        _FAILS.setdefault(ip, []).append(now)
        _GLOBAL.append(now)
        n_global = len(_GLOBAL)
        if n_global >= PIN_GLOBAL_MAX and now - _STATE['global_warned_at'] > PIN_WINDOW_S:
            _STATE['global_warned_at'] = now
            fire = True
    log.warning('PIN incorrecto (%s) desde %s', where, ip)
    if fire:
        log.warning('PIN bloqueado globalmente (%d fallos en 10 min)', n_global)
        for fn in list(_listeners):
            try:
                fn('global', n_global)
            except Exception:  # noqa: BLE001
                pass
    return jsonify({'error': 'PIN incorrecto o faltante', 'error_en': 'Wrong or missing PIN',
                    'code': 'invalid_pin'}), 401


def require_pin(f):
    @wraps(f)
    def wrapper(*a, **k):
        err = pin_error(where=f.__name__, strict=True)
        return err if err else f(*a, **k)
    return wrapper


def require_operator(f):
    @wraps(f)
    def wrapper(*a, **k):
        err = pin_error(where=f.__name__, strict=False)
        if err:
            return err
        if not configured():
            log.warning('escritura sin PIN (%s): TRADE_PIN no configurado — modo desarrollo', f.__name__)
        return f(*a, **k)
    return wrapper


def _reset_for_tests():
    with _LOCK:
        _FAILS.clear()
        _GLOBAL.clear()
        _STATE['global_warned_at'] = 0.0
