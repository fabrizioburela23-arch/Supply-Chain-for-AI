"""mcp_server/auth.py — tokens kmcp_…, alcances, límites por token y auditoría.

Modelo de seguridad (ver docs/MCP.md):
  · El token se muestra UNA sola vez al crearlo; en la base solo queda su
    sha256 (token_hash). Revocar es inmediato (se consulta en cada llamada).
  · Alcances: read (consultas) · research (lanzar investigación/comité, gasta
    presupuesto de IA) · trade (proponer órdenes a UN cliente de corretaje).
    'read' siempre va incluido. 'trade' exige client_id: el token solo opera
    esa cuenta.
  · Sin DATABASE_URL no hay tokens; MCP_STATIC_TOKEN (opcional) da acceso de
    SOLO LECTURA para instalaciones sin base.
  · Auditoría append-only en mcp_audit (sin secretos) — escribirla nunca rompe
    la llamada.
  · PIN (TRADE_PIN): los fallos suman en el contador COMPARTIDO de core/pin.py
    (por IP y global, el mismo de /api/trade y /api/brokerage) y, además, un
    contador GLOBAL propio bloquea TODA comprobación de PIN de MCP
    (MCP_PIN_MAX_FAILS=10 por hora → MCP_PIN_LOCK_MIN=30 min) y queda en la
    auditoría: rotar IPs, cabeceras o superficies no sirve para adivinarlo. La IP de los límites es la que añade el proxy de
    confianza (MCP_TRUSTED_PROXY_HOPS=1, Railway), nunca el primer valor de
    X-Forwarded-For (lo controla el cliente).
  · Base caída ≠ token inválido: authenticate() lanza AuthUnavailable (→ 503 +
    Retry-After) para que los clientes OAuth no descarten un token válido.
"""
import hashlib
import hmac
import json
import logging
import math
import os
import re
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

log = logging.getLogger('khipu')

TOKEN_PREFIX = 'kmcp_'
SCOPES = ('read', 'research', 'trade')
_SECRETISH = re.compile(r'(token|secret|pin|password|passwd|authorization|api[_-]?key|credential)', re.I)


def _now():
    return datetime.now(timezone.utc)


def _aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def db_available():
    try:
        from ontology.db import ontology_available
        return bool(ontology_available())
    except Exception:  # noqa: BLE001
        return False


def ensure_late_columns():
    """ADD COLUMN IF NOT EXISTS de las columnas añadidas después (idempotente)."""
    from sqlalchemy import text

    from mcp_server.models import LATE_COLUMNS
    from ontology.db import _get_engine
    with _get_engine().begin() as conn:
        for tabla, col, tipo in LATE_COLUMNS:
            conn.execute(text(f'ALTER TABLE IF EXISTS {tabla} ADD COLUMN IF NOT EXISTS {col} {tipo}'))
        conn.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS ux_mcp_oauth_codes_consent_nonce '
                          'ON mcp_oauth_codes (consent_nonce)'))


def with_schema(fn):
    """Si las tablas mcp_* (o una columna nueva) aún no existen, las crea y reintenta."""
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        msg = type(e).__name__ + str(e)
        if 'does not exist' not in msg and 'UndefinedTable' not in msg and 'UndefinedColumn' not in msg:
            raise
        from ontology.db import init_schema
        init_schema(retries=1)
        try:
            ensure_late_columns()
        except Exception as e2:  # noqa: BLE001
            log.warning('mcp late columns: %s', type(e2).__name__)
        return fn()


class BiError(ValueError):
    """Error de validación con texto en español E inglés (regla bilingüe)."""

    def __init__(self, es, en, code='bad_request'):
        super().__init__(es)
        self.es, self.en, self.code = es, en, code


class AuthUnavailable(Exception):
    """La base no respondió al validar un token: NO es un token inválido (→ 503)."""


def hash_secret(raw):
    return hashlib.sha256(str(raw or '').encode('utf-8')).hexdigest()


def new_token():
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


def normalize_scopes(raw):
    """Lista ordenada ⊆ SCOPES; 'read' siempre incluido. Acepta lista o 'a b,c'."""
    if isinstance(raw, str):
        raw = re.split(r'[\s,]+', raw)
    got = {str(s).strip().lower() for s in (raw or []) if str(s).strip()}
    got.add('read')
    return [s for s in SCOPES if s in got]


def unknown_scopes(raw):
    if isinstance(raw, str):
        raw = re.split(r'[\s,]+', raw)
    return sorted({str(s).strip().lower() for s in (raw or []) if str(s).strip()} - set(SCOPES))


# ── IP del cliente (límites) ────────────────────────────────────────────────
def client_ip():
    """IP para los límites por IP: la que añade el proxy de CONFIANZA (Railway
    añade/escribe la IP real al final de X-Forwarded-For). El primer valor de
    X-Forwarded-For lo escribe el cliente → rotarlo daba intentos ilimitados.
    MCP_TRUSTED_PROXY_HOPS=0 → sin proxy: remote_addr."""
    try:
        from flask import request
        hops = _int_env('MCP_TRUSTED_PROXY_HOPS', 1, minimum=0)
        xff = [x.strip() for x in (request.headers.get('X-Forwarded-For') or '').split(',') if x.strip()]
        if hops and xff:
            ip = xff[-hops] if len(xff) >= hops else xff[0]
        else:
            ip = request.remote_addr or 'unknown'
        return str(ip)[:64]
    except Exception:  # noqa: BLE001 — fuera de una petición
        return 'unknown'


# ── PIN (contador compartido core/pin.py + bloqueo GLOBAL propio de MCP) ──
_PIN_LOCK = threading.Lock()
_PIN_STATE = {'fails': [], 'locked_until': 0.0}
PIN_FAIL_WINDOW_S = 3600
MIN_STRONG_PIN = 8


def pin_policy():
    return {'max_fails': _int_env('MCP_PIN_MAX_FAILS', 10), 'window_s': PIN_FAIL_WINDOW_S,
            'lock_s': 60 * _int_env('MCP_PIN_LOCK_MIN', 30)}


def pin_strong():
    return len(os.getenv('TRADE_PIN', '')) >= MIN_STRONG_PIN


def pin_locked_for():
    """Segundos que quedan de bloqueo global del PIN (0 = libre)."""
    with _PIN_LOCK:
        return max(0, int(_PIN_STATE['locked_until'] - time.time() + 0.999))


def reset_pin_guard():
    """Limpia el bloqueo propio de MCP y el contador COMPARTIDO de core.pin
    (solo tests / soporte)."""
    with _PIN_LOCK:
        _PIN_STATE['fails'] = []
        _PIN_STATE['locked_until'] = 0.0
    try:
        from core import pin as _core_pin
        _core_pin._reset_for_tests()
    except Exception:  # noqa: BLE001
        pass


def _register_pin_fail(ip, where):
    pol = pin_policy()
    now = time.time()
    locked = False
    with _PIN_LOCK:
        fails = [t for t in _PIN_STATE['fails'] if now - t < pol['window_s']]
        fails.append(now)
        if len(fails) >= pol['max_fails']:
            _PIN_STATE['locked_until'] = now + pol['lock_s']
            fails = []
            locked = True
        _PIN_STATE['fails'] = fails
    write_audit(None, method='pin_check', tool=where, status='denied', error='wrong trading PIN', ip=ip)
    if locked:
        log.error('ALERTA MCP: %d PIN incorrectos en %d min → todas las comprobaciones de PIN de MCP bloqueadas '
                  '%d min (última IP %s)', pol['max_fails'], pol['window_s'] // 60, pol['lock_s'] // 60, ip)
        write_audit(None, method='pin_lockout', tool=where, status='locked',
                    error=f'{pol["max_fails"]} wrong PINs → PIN locked {pol["lock_s"] // 60} min', ip=ip)


def check_pin(got, ip=None, where='mcp', safety=False):
    """→ None si el PIN es válido; si no, (dict_error, código_http).

    Dos frenos, en este orden:
      1. el bloqueo propio de MCP (más estricto): tras MCP_PIN_MAX_FAILS PIN
         incorrectos en una hora se rechaza TODO PIN (también el correcto)
         durante MCP_PIN_LOCK_MIN minutos → 429 code='pin_locked'. Excepción
         `safety=True` (listar/REVOCAR tokens: la acción de emergencia ante un
         token filtrado): una IP de CONFIANZA (core.pin.trusted: acertó el PIN
         hace poco y casi no falla) pasa; una IP nueva sigue bloqueada;
      2. el contador COMPARTIDO de core/pin.py (por IP y global, el mismo de
         /api/trade/* y /api/brokerage/*): los intentos fallidos de cualquier
         superficie suman juntos y su bloqueo también frena a MCP.
    Un PIN vacío (la UI aún no lo pidió) no cuenta en ninguno."""
    want = os.getenv('TRADE_PIN', '')
    if not want:
        return ({'error': 'Trading deshabilitado — configura TRADE_PIN en Railway',
                 'error_en': 'Trading disabled — set TRADE_PIN in Railway', 'code': 'trading_disabled'}, 403)
    ip = ip or client_ip()
    from core import pin as _core_pin
    left = pin_locked_for()
    # Acciones de EMERGENCIA (safety) desde una IP de confianza: el bloqueo de
    # MCP no la deja fuera — si no, 10 PIN malos en la página pública de OAuth
    # impedían al dueño revocar un token filtrado durante 30 min (core/pin.py).
    if left > 0 and not (safety and _core_pin.trusted(ip)):
        mins = max(1, (left + 59) // 60)
        return ({'error': f'Demasiados PIN incorrectos: por seguridad el PIN queda bloqueado ~{mins} min. '
                          'Si no fuiste tú, cambia TRADE_PIN en Railway.',
                 'error_en': f'Too many wrong PINs: for safety the PIN is locked for ~{mins} min. '
                             'If it was not you, change TRADE_PIN in Railway.',
                 'code': 'pin_locked', 'retry_after': left}, 429)
    got = str(got or '')
    bad = _core_pin.check(got=got, where=where, strict=True, ip=ip)
    if bad is None:
        return None
    if bad[1] == 401:
        if got:
            _register_pin_fail(ip, where)
        return ({'error': 'PIN de trading incorrecto o faltante',
                 'error_en': 'Wrong or missing trading PIN', 'code': 'invalid_pin'}, 401)
    return bad


# ── principal autenticado ───────────────────────────────────────────────────
@dataclass
class Principal:
    token_id: str
    name: str
    scopes: frozenset = field(default_factory=frozenset)
    client_id: str = None
    kind: str = 'manual'

    def has(self, scope):
        return scope in self.scopes

    @property
    def actor(self):
        return f'mcp:{self.name}'[:120]


def _brokerage_service():
    import importlib
    return importlib.import_module('brokerage.service')


def resolve_broker_client(session, client_id):
    """Valida el cliente de corretaje → (id canónico, nombre) o lanza ValueError."""
    try:
        svc = _brokerage_service()
    except Exception as e:  # noqa: BLE001
        raise BiError('el módulo de corretaje no está disponible: no se puede dar alcance trade',
                      'the brokerage module is not available: the trade scope cannot be granted',
                      'unavailable') from e
    c = svc.get_client(session, client_id)
    if not c:
        raise BiError('cliente de corretaje no encontrado', 'brokerage client not found', 'not_found')
    return str(c.get('id') or c.get('client_id') or client_id), c.get('name')


def create_token(session, name, scopes, client_id=None, created_by=None, kind='manual',
                 expires_at=None, oauth_client_id=None, oauth_code_hash=None):
    """→ (fila McpToken, token en claro). El token en claro NO se guarda."""
    from mcp_server.models import McpToken
    bad = unknown_scopes(scopes)
    if bad:
        raise BiError(f'alcances desconocidos: {", ".join(bad)} (usa: {", ".join(SCOPES)})',
                      f'unknown scopes: {", ".join(bad)} (use: {", ".join(SCOPES)})')
    sc = normalize_scopes(scopes)
    name = re.sub(r'\s+', ' ', str(name or '')).strip()[:120]
    if not name:
        raise BiError('name (nombre de la conexión) es obligatorio', 'name (the connection name) is required')
    cid = str(client_id or '').strip()[:60] or None
    if 'trade' in sc:
        if not cid:
            raise BiError("el alcance 'trade' exige client_id (la cuenta que este token puede operar)",
                          "the 'trade' scope requires client_id (the account this token may operate)")
        cid, _ = resolve_broker_client(session, cid)
    elif cid:
        cid, _ = resolve_broker_client(session, cid)
    plain = new_token()
    row = McpToken(name=name, token_hash=hash_secret(plain), token_prefix=plain[:10], scopes=sc,
                   client_id=cid, created_by=str(created_by or 'ui')[:120], kind=kind,
                   expires_at=expires_at, oauth_client_id=oauth_client_id, oauth_code_hash=oauth_code_hash,
                   use_count=0, revoked=False)
    session.add(row)
    session.flush()
    return row, plain


def token_dict(row, client_names=None):
    exp = _aware(row.expires_at)
    return {'id': row.id, 'name': row.name, 'prefix': (row.token_prefix or '') + '…', 'scopes': list(row.scopes or []),
            'client_id': row.client_id, 'client_name': (client_names or {}).get(row.client_id),
            'kind': row.kind, 'oauth_client_id': row.oauth_client_id,
            'created_by': row.created_by,
            'created_at': row.created_at.isoformat() if row.created_at else None,
            'last_used_at': row.last_used_at.isoformat() if row.last_used_at else None,
            'use_count': row.use_count or 0,
            'expires_at': exp.isoformat() if exp else None,
            'expired': bool(exp and exp < _now()),
            'revoked': bool(row.revoked),
            'revoked_at': row.revoked_at.isoformat() if row.revoked_at else None,
            'revoked_by': row.revoked_by}


def _client_names(session, ids):
    ids = [i for i in set(ids) if i]
    if not ids:
        return {}
    try:
        svc = _brokerage_service()
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for i in ids:
        try:
            c = svc.get_client(session, i)
            if c:
                out[i] = c.get('name')
        except Exception:  # noqa: BLE001
            pass
    return out


def list_tokens(session, include_revoked=True):
    from mcp_server.models import McpToken
    q = session.query(McpToken)
    if not include_revoked:
        q = q.filter(McpToken.revoked.is_(False))
    rows = q.order_by(McpToken.created_at.desc()).limit(200).all()
    names = _client_names(session, [r.client_id for r in rows])
    return [token_dict(r, names) for r in rows]


def revoke_token(session, token_id, actor):
    from mcp_server.models import McpToken
    row = session.get(McpToken, str(token_id or '')[:40])
    if not row:
        return {'ok': False, 'error': 'token no encontrado', 'error_en': 'token not found', 'code': 'not_found'}
    if not row.revoked:
        row.revoked, row.revoked_at, row.revoked_by = True, _now(), str(actor or 'ui')[:120]
        row.refresh_hash = None
        session.flush()
    return {'ok': True, 'token': token_dict(row)}


def _static_principal(raw):
    want = os.getenv('MCP_STATIC_TOKEN', '')
    if want and len(want) >= 24 and hmac.compare_digest(str(raw).encode(), want.encode()):
        return Principal(token_id='static', name='static (env)', scopes=frozenset({'read'}), kind='static')
    return None


def authenticate(authorization_header):
    """Header Authorization → Principal o None (token ausente, desconocido,
    revocado o caducado). Si la BASE falla (reinicio de Postgres, pool agotado…)
    lanza AuthUnavailable: eso NO es un token inválido (→ 503, no 401)."""
    h = str(authorization_header or '').strip()
    if not h.lower().startswith('bearer '):
        return None
    raw = h[7:].strip()
    if not raw or len(raw) > 200:
        return None
    st = _static_principal(raw)
    if st:
        return st
    if not raw.startswith(TOKEN_PREFIX) or not db_available():
        return None
    try:
        from sqlalchemy import func

        from ontology.db import session_scope
        from mcp_server.models import McpToken

        def _q():
            with session_scope() as s:
                row = s.query(McpToken).filter(McpToken.token_hash == hash_secret(raw)).first()
                if not row or row.revoked:
                    return None
                exp = _aware(row.expires_at)
                if exp and exp < _now():
                    return None
                # incremento en SQL (no leer-sumar-escribir en Python: con 8 hilos se perdían cuentas)
                s.query(McpToken).filter(McpToken.id == row.id).update(
                    {McpToken.use_count: func.coalesce(McpToken.use_count, 0) + 1, McpToken.last_used_at: _now()},
                    synchronize_session=False)
                return Principal(token_id=row.id, name=row.name, scopes=frozenset(row.scopes or ['read']),
                                 client_id=row.client_id, kind=row.kind or 'manual')
        return with_schema(_q)
    except Exception as e:  # noqa: BLE001
        log.warning('mcp auth: backend error %s', type(e).__name__)
        raise AuthUnavailable(type(e).__name__) from e


# ── límites de tasa por token (en memoria; 1 worker — ver CLAUDE.md) ───────
def _int_env(name, default, minimum=1):
    try:
        return max(minimum, int(os.getenv(name, default)))
    except (TypeError, ValueError):
        return default


def limits():
    return {'calls_per_min': _int_env('MCP_RATE_PER_MIN', 60),
            'research_per_hour': _int_env('MCP_RESEARCH_PER_HOUR', 10),
            'trade_per_hour': _int_env('MCP_TRADE_PER_HOUR', 30),
            # Claude/ChatGPT suelen pedir 2-3 herramientas en paralelo; 5 en total deja ≥3 hilos a la app
            'inflight_per_token': _int_env('MCP_MAX_INFLIGHT', 3),
            'inflight_total': _int_env('MCP_MAX_INFLIGHT_TOTAL', 5)}


# ── concurrencia: peticiones EN CURSO por token y en total ─────────────────
# (1 worker + 8 hilos: sin tope, un agente con lotes lentos ocupaba todos los
# hilos y tumbaba la app entera)
_INFLIGHT = {'total': 0, 'by': {}}
_INFLIGHT_LOCK = threading.Lock()


def inflight_acquire(principal):
    """→ None si hay cupo (llamar luego a inflight_release); si no, 'token' | 'total'."""
    lim = limits()
    key = principal.token_id if isinstance(principal, Principal) else str(principal)
    with _INFLIGHT_LOCK:
        if _INFLIGHT['by'].get(key, 0) >= lim['inflight_per_token']:
            return 'token'
        if _INFLIGHT['total'] >= lim['inflight_total']:
            return 'total'
        _INFLIGHT['by'][key] = _INFLIGHT['by'].get(key, 0) + 1
        _INFLIGHT['total'] += 1
    return None


def inflight_release(principal):
    key = principal.token_id if isinstance(principal, Principal) else str(principal)
    with _INFLIGHT_LOCK:
        n = _INFLIGHT['by'].get(key, 0) - 1
        if n > 0:
            _INFLIGHT['by'][key] = n
        else:
            _INFLIGHT['by'].pop(key, None)
        _INFLIGHT['total'] = max(0, _INFLIGHT['total'] - 1)


def allow(principal_or_key, bucket, limit, window):
    from core.http import _rate_limit
    key = principal_or_key.token_id if isinstance(principal_or_key, Principal) else str(principal_or_key)
    return _rate_limit(f'mcp:{key}:{bucket}', limit, window)


# ── auditoría ───────────────────────────────────────────────────────────────
def summarize_args(args, depth=0):
    """Resumen de argumentos para la auditoría: SIN secretos, acotado."""
    if depth > 3:
        return '…'
    if isinstance(args, dict):
        out = {}
        for i, (k, v) in enumerate(args.items()):
            if i >= 20:
                out['…'] = f'+{len(args) - 20}'
                break
            ks = str(k)[:40]
            out[ks] = '***' if _SECRETISH.search(ks) else summarize_args(v, depth + 1)
        return out
    if isinstance(args, list):
        items = [summarize_args(v, depth + 1) for v in args[:10]]
        if len(args) > 10:
            items.append(f'+{len(args) - 10}')
        return items
    if isinstance(args, str):
        if args.startswith(TOKEN_PREFIX):
            return '***'
        return args[:200]
    if isinstance(args, float) and not math.isfinite(args):
        return str(args)             # JSONB no admite NaN/Infinity: la auditoría no debe fallar
    if isinstance(args, (int, float, bool)) or args is None:
        return args
    return str(args)[:100]


def write_audit(principal=None, method=None, tool=None, args=None, status='ok', error=None,
                latency_ms=None, ip=None, session_id=None):
    if not db_available():
        return
    try:
        from ontology.db import session_scope
        from mcp_server.models import McpAudit
        summ = summarize_args(args or {})
        if len(json.dumps(summ, default=str)) > 2000:
            summ = {'_truncated': True, 'keys': list(summ.keys())[:20] if isinstance(summ, dict) else None}

        def _w():
            with session_scope() as s:
                s.add(McpAudit(token_id=getattr(principal, 'token_id', None),
                               token_name=getattr(principal, 'name', None),
                               client_id=getattr(principal, 'client_id', None),
                               method=(str(method)[:60] if method else None), tool=(str(tool)[:60] if tool else None),
                               args_summary=summ if isinstance(summ, dict) else {'value': summ},
                               status=str(status)[:20], error=(str(error)[:300] if error else None),
                               latency_ms=(int(latency_ms) if latency_ms is not None else None),
                               ip=(str(ip)[:64] if ip else None), session_id=(str(session_id)[:64] if session_id else None)))
        with_schema(_w)
    except Exception as e:  # noqa: BLE001 — la auditoría nunca rompe la llamada
        log.warning('mcp audit: %s', type(e).__name__)


def list_audit(session, limit=100, token_id=None):
    from mcp_server.models import McpAudit
    q = session.query(McpAudit)
    if token_id:
        q = q.filter(McpAudit.token_id == str(token_id)[:40])
    rows = q.order_by(McpAudit.id.desc()).limit(max(1, min(int(limit or 100), 500))).all()
    return [{'id': r.id, 'ts': r.ts.isoformat() if r.ts else None, 'token_id': r.token_id, 'token_name': r.token_name,
             'client_id': r.client_id, 'method': r.method, 'tool': r.tool, 'args': r.args_summary or {},
             'status': r.status, 'error': r.error, 'latency_ms': r.latency_ms, 'ip': r.ip} for r in rows]
