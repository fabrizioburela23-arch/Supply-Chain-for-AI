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
    check(got, where, strict, ip)  # igual que pin_error pero devuelve (dict, status)
                                   # sin Flask (lo usa mcp_server/auth.check_pin)

Reglas del contador:
  · un PIN VACÍO (la UI aún no lo pidió) responde 401 pero NO cuenta: no da
    información al atacante y así un sondeo sin PIN no bloquea al dueño;
  · mientras hay bloqueo, los intentos NO se cuentan (el bloqueo dura hasta que
    los fallos viejos salen de la ventana; `retry_after` + cabecera Retry-After);
  · el bloqueo global dispara los callbacks de on_global_lock UNA vez por
    episodio (cuando el contador llega exactamente a PIN_GLOBAL_MAX);
  · IP DE CONFIANZA (revisión 2026-09-30, DoS del bloqueo global): una IP que
    acertó el PIN en los últimos PIN_TRUST_S (7 días) sigue pudiendo usar el
    PIN correcto DURANTE el bloqueo global mientras ella misma tenga menos de
    PIN_TRUSTED_MAX_FAILS fallos. Así 3 IPs × 10 fallos no dejan al dueño sin
    cerrar una posición ni parar el agente. Una IP nueva NO pasa (si pasara,
    cada IP nueva de una botnet ganaría un intento extra y el tope global
    dejaría de servir). Trade-off documentado: el dueño desde una IP nueva
    durante un ataque debe usar el panel de Alpaca o el interruptor
    BROKERAGE_TRADING_ENABLED en Railway.

Estado EN MEMORIA del proceso (1 worker de gunicorn): contadores, bloqueos e
IPs de confianza se pierden en cada reinicio/deploy. Por eso
GUNICORN_MAX_REQUESTS debe seguir en 0 (Dockerfile): reciclar el worker
borraría el bloqueo cada N peticiones.

También vive aquí la postura de SECRET_KEY (auditoría #15): `secret_key_default()`,
`in_production()` e `insecure_production_secret()` — los usan server.py
(/api/health, /api/diagnostics) y mcp_server/oauth.py.
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
PIN_TRUST_S = 7 * 24 * 3600  # una IP que acertó el PIN es "de confianza" 7 días
PIN_TRUSTED_MAX_FAILS = 3   # …y sortea el bloqueo GLOBAL mientras tenga < 3 fallos propios
PIN_MAX_TRUSTED = 256

_FAILS = {}                 # ip → [ts]
_GLOBAL = []                # [ts]
_TRUSTED = {}               # ip → ts del último PIN correcto
_LOCK = threading.Lock()
_STATE = {'global_warned_at': 0.0}
_listeners = []             # callbacks(scope, n) al activarse el bloqueo global (p. ej. auditoría)


def client_ip():
    xff = request.headers.get('X-Forwarded-For', '')
    hops = [h.strip() for h in xff.split(',') if h.strip()]
    return (hops[-1] if hops else (request.remote_addr or 'unknown'))[:64]


def on_global_lock(fn):
    """Registra un callback(scope, n) para auditar el bloqueo global (idempotente)."""
    if fn not in _listeners:
        _listeners.append(fn)
    return fn


def _prune(now):
    cut = now - PIN_WINDOW_S
    _GLOBAL[:] = [t for t in _GLOBAL if t > cut]
    for ip in [k for k, v in _FAILS.items() if not v or v[-1] <= cut]:
        _FAILS.pop(ip, None)
    for ip in list(_FAILS):
        _FAILS[ip] = [t for t in _FAILS[ip] if t > cut]
    if len(_FAILS) > PIN_MAX_IPS:
        for ip in sorted(_FAILS, key=lambda k: _FAILS[k][-1])[:len(_FAILS) - PIN_MAX_IPS]:
            _FAILS.pop(ip, None)
    for ip in [k for k, t in _TRUSTED.items() if t <= now - PIN_TRUST_S]:
        _TRUSTED.pop(ip, None)
    if len(_TRUSTED) > PIN_MAX_TRUSTED:
        for ip in sorted(_TRUSTED, key=_TRUSTED.get)[:len(_TRUSTED) - PIN_MAX_TRUSTED]:
            _TRUSTED.pop(ip, None)


def _lock_left(stamps, limit, now):
    """Segundos de bloqueo que quedan (0 = libre): el bloqueo se levanta cuando
    el fallo nº (n-limit) sale de la ventana y el conteo baja de `limit`."""
    live = [t for t in stamps if t > now - PIN_WINDOW_S]
    if len(live) < limit:
        return 0
    return max(1, int(live[len(live) - limit] + PIN_WINDOW_S - now + 0.999))


def trusted(ip):
    """¿Esta IP acertó el PIN hace < PIN_TRUST_S y tiene < PIN_TRUSTED_MAX_FAILS
    fallos propios? (la usa mcp_server/auth para su bloqueo propio)."""
    ip = str(ip or '')[:64]
    now = time.time()
    with _LOCK:
        t = _TRUSTED.get(ip)
        fails = [x for x in (_FAILS.get(ip) or ()) if x > now - PIN_WINDOW_S]
        return bool(t and t > now - PIN_TRUST_S and len(fails) < PIN_TRUSTED_MAX_FAILS)


def configured():
    return bool(os.getenv('TRADE_PIN', ''))


def _disabled_body():
    return {'error': 'Trading deshabilitado — configura TRADE_PIN en Railway',
            'error_en': 'Trading disabled — set TRADE_PIN in Railway',
            'code': 'trading_disabled'}


def check(got=None, where='api', strict=True, ip=None):
    """Núcleo sin Flask-response: None si el PIN es válido (o no hace falta);
    si no, (dict_error_bilingüe, status). `got=None` → cabecera X-Trade-Pin.
    `ip` opcional (MCP pasa la suya); por defecto client_ip()."""
    want = os.getenv('TRADE_PIN', '')
    if not want:
        return (_disabled_body(), 403) if strict else None
    ip = str(ip or client_ip())[:64]
    now = time.time()
    with _LOCK:
        _prune(now)
        g_left = _lock_left(_GLOBAL, PIN_GLOBAL_MAX, now)
        ip_fails = _FAILS.get(ip) or ()
        ip_left = _lock_left(ip_fails, PIN_MAX_FAILS, now)
        is_trusted = ip in _TRUSTED and len(ip_fails) < PIN_TRUSTED_MAX_FAILS
    if g_left and not is_trusted:
        return ({'error': 'Demasiados intentos de PIN fallidos (desde varias direcciones): bloqueado 10 minutos',
                 'error_en': 'Too many failed PIN attempts (from several addresses): locked for 10 minutes',
                 'code': 'pin_locked_global', 'retry_after': g_left}, 429)
    if ip_left:
        return ({'error': 'Demasiados intentos de PIN fallidos: espera 10 minutos',
                 'error_en': 'Too many failed PIN attempts: wait 10 minutes', 'code': 'pin_locked',
                 'retry_after': ip_left}, 429)
    got = request.headers.get('X-Trade-Pin', '') if got is None else str(got)
    if got and hmac.compare_digest(got.encode(), want.encode()):
        with _LOCK:
            _TRUSTED[ip] = now
        return None
    bad = ({'error': 'PIN incorrecto o faltante', 'error_en': 'Wrong or missing PIN', 'code': 'invalid_pin'}, 401)
    if not got:                      # PIN vacío: 401 sin contar (no revela nada)
        return bad
    fire = False
    with _LOCK:
        _FAILS.setdefault(ip, []).append(now)
        _GLOBAL.append(now)
        n_global = len(_GLOBAL)
        if n_global == PIN_GLOBAL_MAX:          # una vez por episodio de bloqueo
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
    return bad


def pin_error(got=None, where='api', strict=True):
    """None si el PIN es válido; si no, (respuesta_json, status).
    strict=False: sin TRADE_PIN configurado se permite (escrituras de ontología
    en desarrollo); con strict=True sin TRADE_PIN → 403 'deshabilitado'."""
    err = check(got=got, where=where, strict=strict)
    if err is None:
        return None
    body, status = err
    resp = jsonify(body)
    if body.get('retry_after'):
        resp.headers['Retry-After'] = str(body['retry_after'])
    return resp, status


# ── Postura de SECRET_KEY (auditoría #15) ───────────────────────────────────
DEFAULT_SECRET_KEY = 'khipu-dev-secret-change-me'


def secret_key_default():
    """True si SECRET_KEY falta o es la del repo (pública)."""
    k = (os.getenv('SECRET_KEY') or '').strip()
    return (not k) or k == DEFAULT_SECRET_KEY


def in_production():
    """Railway define RAILWAY_ENVIRONMENT (o *_NAME / RAILWAY_PROJECT_ID)."""
    return any((os.getenv(n) or '').strip() for n in
               ('RAILWAY_ENVIRONMENT', 'RAILWAY_ENVIRONMENT_NAME', 'RAILWAY_PROJECT_ID'))


def insecure_production_secret():
    """En producción con SECRET_KEY por defecto: lo que se firme con ella es falsificable."""
    return in_production() and secret_key_default()


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
        _TRUSTED.clear()
        _STATE['global_warned_at'] = 0.0
