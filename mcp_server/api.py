"""mcp_server/api.py — blueprint mcp_bp (transporte + administración).

MCP (Streamable HTTP, spec 2025-06-18 / 2025-03-26):
  POST   /mcp       JSON-RPC 2.0 → application/json. Lotes (arrays) SOLO con la
                    versión 2025-03-26 (la 2025-06-18 eliminó los lotes → 400).
                    Solo notificaciones/respuestas → 202 sin cuerpo.
                    Authorization: Bearer kmcp_…  (sin token → 401 +
                    WWW-Authenticate con resource_metadata, RFC 9728; base caída
                    → 503 + Retry-After, NUNCA 401: el token sigue siendo válido).
                    initialize → cabecera Mcp-Session-Id.
  GET    /mcp       405 (no ofrecemos stream SSE del servidor) + Allow.
  DELETE /mcp       cierra la sesión (Mcp-Session-Id) → 204; después ese id → 404.
  OPTIONS /mcp      preflight CORS (solo orígenes permitidos).

Administración (X-Trade-Pin == TRADE_PIN, misma semántica que server._trade_auth
+ bloqueo global anti-adivinanza de auth.check_pin):
  GET  /api/mcp/status                (sin PIN) disponibilidad, endpoint, versiones
  GET  /api/mcp/tools                 (sin PIN) catálogo de herramientas por alcance
  GET  /api/mcp/tokens                lista (sin secretos)
  POST /api/mcp/tokens                {name, scopes[], client_id?, actor?} → token UNA vez
  POST /api/mcp/tokens/<id>/revoke    revoca al instante
  GET  /api/mcp/audit?limit=&token_id= últimas llamadas

OAuth 2.1 (conectores remotos claude.ai / ChatGPT) → mcp_server/oauth.py.

Protecciones: interruptor MCP_ENABLED=off (503); Origin validado contra una
lista FIJA (MCP_PUBLIC_URL, RAILWAY_PUBLIC_DOMAIN, MCP_ALLOWED_ORIGINS; localhost
solo si el servidor se alcanzó por localhost) — nunca contra la cabecera Host,
que en un DNS-rebinding es la del atacante; MCP_ALLOWED_HOSTS opcional; 256 KB
por petición; lotes ≤ 20; límite por token (MCP_RATE_PER_MIN) contado POR
MENSAJE; peticiones simultáneas por token (MCP_MAX_INFLIGHT=3) y en total
(MCP_MAX_INFLIGHT_TOTAL=5, deja hilos libres para la app); límite por IP ante
tokens inválidos; números no finitos (NaN/Infinity) rechazados; auditoría en
mcp_audit.
"""
import json
import logging
import os
import secrets
import threading
import time
from urllib.parse import urlparse

from flask import Blueprint, Response, jsonify, request

from core.http import rate_limit
from mcp_server import auth as _auth
from mcp_server import protocol as _proto
from mcp_server import tools as _tools

log = logging.getLogger('khipu')

mcp_bp = Blueprint('mcp', __name__)

MAX_BODY = 256 * 1024
MAX_BATCH = 20
_AUTHFAIL_LIMIT, _AUTHFAIL_WINDOW = 30, 600
NO_BATCH_VERSIONS = ('2025-06-18',)          # la revisión 2025-06-18 eliminó los lotes JSON-RPC

# Mcp-Session-Id → {token_id, version, created}. En memoria (1 worker, ver
# CLAUDE.md). El servidor es SIN ESTADO: una sesión desconocida (p. ej. tras un
# redeploy) se acepta; una conocida pero de OTRO token → 404; una CERRADA con
# DELETE → 404 (spec 2025-06-18: tras terminarla, el servidor DEBE responder 404).
_SESSIONS = {}
_CLOSED = {}                                   # sid → momento del cierre
_SESS_LOCK = threading.Lock()
_SESS_MAX = 5000
_CLOSED_TTL_S = 24 * 3600


# ── utilidades ──────────────────────────────────────────────────────────────
def mcp_enabled():
    return os.getenv('MCP_ENABLED', 'on').strip().lower() not in ('off', '0', 'false', 'no')


def base_url():
    """URL pública (para metadatos OAuth y configuraciones). MCP_PUBLIC_URL manda;
    si no, el Host de la petición + X-Forwarded-Proto (Railway termina TLS)."""
    env = os.getenv('MCP_PUBLIC_URL', '').strip().rstrip('/')
    if env:
        return env
    proto = (request.headers.get('X-Forwarded-Proto') or request.scheme or 'http').split(',')[0].strip()
    if proto not in ('http', 'https'):
        proto = 'https'
    return f'{proto}://{request.host}'


def resource_url():
    return base_url() + '/mcp'


def resource_metadata_url():
    return base_url() + '/.well-known/oauth-protected-resource/mcp'


def _ip():
    return _auth.client_ip()


def _origin_of(url):
    """'https://Foo.example:443/x' → 'https://foo.example:443' (esquema + host[:puerto])."""
    try:
        u = urlparse(str(url or '').strip().lower())
        if u.scheme in ('http', 'https') and u.netloc:
            return f'{u.scheme}://{u.netloc}'
    except Exception:  # noqa: BLE001
        pass
    return None


def _allowed_origins():
    raw = os.getenv('MCP_ALLOWED_ORIGINS', '')
    return [o.strip().rstrip('/').lower() for o in raw.split(',') if o.strip()]


_LOOPBACK = ('localhost', '127.0.0.1', '::1')


def _request_hostname():
    try:
        return (urlparse('//' + (request.host or '')).hostname or '').lower()
    except Exception:  # noqa: BLE001
        return ''


def known_origins():
    """Orígenes de confianza FIJOS (no dependen de la petición)."""
    out = set()
    for o in _allowed_origins():
        out.add('*' if o == '*' else (_origin_of(o) or o))
    pub = _origin_of(os.getenv('MCP_PUBLIC_URL', ''))
    if pub:
        out.add(pub)
    rail = os.getenv('RAILWAY_PUBLIC_DOMAIN', '').strip().lower().rstrip('/')
    if rail:
        out.add(f'https://{rail}')
    return out


def origin_allowed(origin):
    """Protección DNS-rebinding (spec «Security Warning»). Sin Origin (clientes
    de servidor/CLI) → se permite. Con Origin, debe estar en la lista FIJA
    (known_origins) o ser localhost cuando el propio servidor se alcanzó por
    localhost (desarrollo). NUNCA se compara con la cabecera Host: en un
    DNS-rebinding Origin y Host son ambos el dominio del atacante."""
    if not origin:
        return True
    o = _origin_of(origin)
    if o is None:
        return False                           # 'null', esquemas raros…
    allow = known_origins()
    if '*' in allow or o in allow:
        return True
    oh = (urlparse(o).hostname or '').lower()
    return oh in _LOOPBACK and _request_hostname() in _LOOPBACK


def host_allowed():
    """MCP_ALLOWED_HOSTS (opcional, 'a.example,b.example:8080'): si está, el Host debe coincidir."""
    raw = [h.strip().lower() for h in os.getenv('MCP_ALLOWED_HOSTS', '').split(',') if h.strip()]
    if not raw:
        return True
    host = (request.host or '').lower()
    return host in raw or _request_hostname() in raw


def _guard_origin_host():
    if not origin_allowed(request.headers.get('Origin')):
        return _rpc_http(_proto.error(None, -32600, 'Forbidden: Origin not allowed (MCP_ALLOWED_ORIGINS)'), 403)
    if not host_allowed():
        return _rpc_http(_proto.error(None, -32600, 'Forbidden: Host not allowed (MCP_ALLOWED_HOSTS)'), 403)
    return None


def _cors(resp):
    origin = request.headers.get('Origin')
    if origin and origin_allowed(origin):
        resp.headers['Access-Control-Allow-Origin'] = origin
        resp.headers['Vary'] = 'Origin'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, GET, DELETE, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = ('Authorization, Content-Type, Accept, Mcp-Session-Id, '
                                                        'MCP-Protocol-Version, Last-Event-ID')
        resp.headers['Access-Control-Expose-Headers'] = 'Mcp-Session-Id, WWW-Authenticate, MCP-Protocol-Version'
        resp.headers['Access-Control-Max-Age'] = '600'
    return resp


def _rpc_http(body, status, headers=None):
    resp = Response(json.dumps(body, ensure_ascii=False, default=str), status=status, mimetype='application/json')
    for k, v in (headers or {}).items():
        resp.headers[k] = v
    return _cors(resp)


def _unauthorized(had_token):
    hdr = f'Bearer resource_metadata="{resource_metadata_url()}"'
    if had_token:
        hdr += ', error="invalid_token", error_description="token missing, unknown, revoked or expired"'
    return _rpc_http(_proto.error(None, -32001, 'Unauthorized: send "Authorization: Bearer kmcp_…" '
                                              '(create a token in Khipus → 🩺 Sistema → 🤖 Conectar IAs) or use '
                                              'OAuth'),
                     401, {'WWW-Authenticate': hdr})


def _backend_down():
    return _rpc_http(_proto.error(None, -32000, 'Authentication backend temporarily unavailable (database) — '
                                              'your token is still valid; retry in ~30 s'),
                     503, {'Retry-After': '30'})


def _authenticate():
    """→ (principal | None, respuesta_503 | None)."""
    try:
        return _auth.authenticate(request.headers.get('Authorization')), None
    except _auth.AuthUnavailable:
        return None, _backend_down()


def _new_session(principal, version):
    sid = secrets.token_urlsafe(24)
    with _SESS_LOCK:
        if len(_SESSIONS) >= _SESS_MAX:
            for k in sorted(_SESSIONS, key=lambda k: _SESSIONS[k]['created'])[:_SESS_MAX // 5]:
                _SESSIONS.pop(k, None)
        _SESSIONS[sid] = {'token_id': principal.token_id, 'version': version, 'created': time.time()}
    return sid


def _close_session(sid):
    now = time.time()
    with _SESS_LOCK:
        _SESSIONS.pop(sid, None)
        if len(_CLOSED) >= _SESS_MAX:
            for k in [k for k, t in _CLOSED.items() if now - t > _CLOSED_TTL_S]:
                _CLOSED.pop(k, None)
            if len(_CLOSED) >= _SESS_MAX:
                for k in sorted(_CLOSED, key=_CLOSED.get)[:_SESS_MAX // 5]:
                    _CLOSED.pop(k, None)
        _CLOSED[sid] = now


def _session_state(sid, principal):
    """→ (sesión conocida | None, 'closed' | 'foreign' | None)."""
    with _SESS_LOCK:
        t = _CLOSED.get(sid)
        if t is not None:
            if time.time() - t <= _CLOSED_TTL_S:
                return None, 'closed'
            _CLOSED.pop(sid, None)
        known = _SESSIONS.get(sid)
    if known and known['token_id'] != principal.token_id:
        return known, 'foreign'
    return known, None


def _reject_constant(c):
    raise ValueError(f'non-finite number {c} is not valid JSON')


# ── /mcp ────────────────────────────────────────────────────────────────────
@mcp_bp.route('/mcp', methods=['OPTIONS'])
def mcp_options():
    bad = _guard_origin_host()
    if bad is not None:
        return bad
    return _cors(Response(status=204))


@mcp_bp.route('/mcp', methods=['GET'])
def mcp_get():
    resp = _rpc_http({'error': 'this MCP server does not offer a server-initiated SSE stream; use POST',
                      'error_es': 'este servidor MCP no ofrece stream SSE; usa POST'}, 405,
                     {'Allow': 'POST, DELETE, OPTIONS'})
    return resp


@mcp_bp.route('/mcp', methods=['DELETE'])
def mcp_delete():
    bad = _guard_origin_host()
    if bad is not None:
        return bad
    principal, down = _authenticate()
    if down is not None:
        return down
    if principal is None:
        return _unauthorized(bool(request.headers.get('Authorization')))
    sid = (request.headers.get('Mcp-Session-Id') or '').strip()[:100]
    if not sid:
        return _rpc_http(_proto.error(None, _proto.INVALID_REQUEST, 'Mcp-Session-Id header is required'), 400)
    known, state = _session_state(sid, principal)
    if state == 'foreign':
        return _rpc_http(_proto.error(None, -32001, 'Session not found'), 404)
    if state == 'closed':
        return _rpc_http(_proto.error(None, -32001, 'Session already terminated'), 404)
    _close_session(sid)                    # conocida o no (p. ej. tras un redeploy): queda cerrada
    return _cors(Response(status=204))


@mcp_bp.route('/mcp', methods=['POST'])
def mcp_post():
    if not mcp_enabled():
        return _rpc_http(_proto.error(None, -32000, 'MCP server switched off by the administrator (MCP_ENABLED=off)'),
                         503)
    bad = _guard_origin_host()
    if bad is not None:
        return bad
    ip = _ip()
    # ── autenticación (antes de leer el cuerpo) ──
    authz = request.headers.get('Authorization')
    principal, down = _authenticate()
    if down is not None:
        return down
    if principal is None:
        if not _auth.allow(f'ip:{ip}', 'authfail', _AUTHFAIL_LIMIT, _AUTHFAIL_WINDOW):
            return _rpc_http(_proto.error(None, -32000, 'Too many failed authentications — wait a few minutes'),
                             429, {'Retry-After': '600'})
        if authz:
            _auth.write_audit(None, method='auth', status='unauthorized', error='invalid token', ip=ip)
        return _unauthorized(bool(authz))
    # ── peticiones simultáneas (por token y en total) ──
    busy = _auth.inflight_acquire(principal)
    if busy:
        lim = _auth.limits()
        msg = (f'Too many concurrent requests for this token (max {lim["inflight_per_token"]} in flight) — wait for '
               'the previous call to finish' if busy == 'token' else
               'The MCP server is busy with other agents — retry in a few seconds')
        return _rpc_http(_proto.error(None, -32000, msg), 429, {'Retry-After': '5'})
    try:
        return _mcp_post_body(principal, ip)
    finally:
        _auth.inflight_release(principal)


def _mcp_post_body(principal, ip):
    lim = _auth.limits()
    # ── tamaño y JSON ──
    if (request.content_length or 0) > MAX_BODY:
        return _rpc_http(_proto.error(None, _proto.INVALID_REQUEST, f'Request too large (max {MAX_BODY // 1024} KB)'),
                         413)
    raw = request.get_data(cache=False)
    if len(raw) > MAX_BODY:
        return _rpc_http(_proto.error(None, _proto.INVALID_REQUEST, f'Request too large (max {MAX_BODY // 1024} KB)'),
                         413)
    try:
        # NaN / Infinity / -Infinity NO son JSON: json.loads los aceptaría y
        # romperían la validación numérica y la auditoría (JSONB).
        payload = json.loads(raw.decode('utf-8') if raw else '', parse_constant=_reject_constant)
    except Exception:  # noqa: BLE001
        return _rpc_http(_proto.error(None, _proto.PARSE_ERROR, 'Parse error: body is not valid JSON'), 400)
    batch = isinstance(payload, list)
    msgs = payload if batch else [payload]
    if batch and (not msgs or len(msgs) > MAX_BATCH):
        return _rpc_http(_proto.error(None, _proto.INVALID_REQUEST,
                                      f'Invalid Request: batch must have 1-{MAX_BATCH} messages'), 400)
    is_init = any(isinstance(m, dict) and m.get('method') == 'initialize' for m in msgs)
    # ── versión de protocolo (cabecera obligatoria tras initialize en 2025-06-18) ──
    # Versión no soportada → 400 (spec 2025-06-18). El código -32022 + data.supported
    # es el de revisiones posteriores (sonda server/discover de 2026-07-28): así un
    # cliente moderno sabe que debe volver al handshake `initialize` con 2025-06-18.
    pv = (request.headers.get('MCP-Protocol-Version') or '').strip()
    if pv and not is_init and pv not in _proto.SUPPORTED_VERSIONS:
        one = msgs[0] if (not batch and isinstance(msgs[0], dict)) else {}
        rid = one.get('id') if isinstance(one.get('id'), (str, int)) and not isinstance(one.get('id'), bool) else None
        return _rpc_http(_proto.error(rid, _proto.UNSUPPORTED_VERSION,
                                      f'Unsupported MCP-Protocol-Version: {pv[:20]} '
                                      f'(supported: {", ".join(_proto.SUPPORTED_VERSIONS)})',
                                      {'supported': list(_proto.SUPPORTED_VERSIONS), 'requested': pv[:40]}), 400)
    # ── sesión (opcional) ──
    sid = (request.headers.get('Mcp-Session-Id') or '').strip()[:100]
    known = None
    if sid and not is_init:
        known, state = _session_state(sid, principal)
        if state in ('foreign', 'closed'):
            return _rpc_http(_proto.error(None, -32001, 'Session not found' if state == 'foreign'
                                          else 'Session terminated — send initialize again'), 404)
    version = pv or (known or {}).get('version') or '2025-03-26'
    # ── lotes: no en 2025-06-18; initialize nunca dentro de un lote ──
    if batch and version in NO_BATCH_VERSIONS:
        return _rpc_http(_proto.error(None, _proto.INVALID_REQUEST,
                                      f'Invalid Request: JSON-RPC batching is not supported in protocol version '
                                      f'{version}; send one message per request'), 400)
    if batch and is_init:
        return _rpc_http(_proto.error(None, _proto.INVALID_REQUEST,
                                      'Invalid Request: initialize must not be part of a batch'), 400)
    # ── límite por token, contado POR MENSAJE (un lote de 20 = 20 llamadas) ──
    per_min = lim['calls_per_min']
    if not batch:
        if not _auth.allow(principal, 'calls', per_min, 60):
            _auth.write_audit(principal, method='rate_limit', status='rate_limited', ip=ip)
            return _rpc_http(_proto.error(None, -32000, f'Rate limit: max {per_min} calls/min per token'),
                             429, {'Retry-After': '60'})
    ctx = _tools.Ctx(principal=principal, session_id=sid or None, ip=ip, protocol_version=version)
    responses = []
    limited = 0
    for m in msgs:
        if batch and not _auth.allow(principal, 'calls', per_min, 60):
            limited += 1
            mid = m.get('id') if isinstance(m, dict) else None
            if isinstance(m, dict) and 'id' in m and m.get('method') and _proto._is_valid_id(mid):
                responses.append(_proto.error(mid, -32000, f'Rate limit: max {per_min} calls/min per token',
                                              {'retry_after_s': 60}))
            continue
        t0 = time.monotonic()
        resp, audit = _proto.handle(m, ctx)
        if audit is not None:
            _auth.write_audit(principal, method=audit.get('method'), tool=audit.get('tool'),
                              args=audit.get('args'), status=audit.get('status', 'ok'), error=audit.get('error'),
                              latency_ms=(time.monotonic() - t0) * 1000, ip=ip, session_id=ctx.session_id)
        if resp is not None:
            responses.append(resp)
    if limited:
        _auth.write_audit(principal, method='rate_limit', status='rate_limited', ip=ip,
                          error=f'{limited} batched message(s) over the per-token limit')
    if not responses:
        return _cors(Response(status=202))
    headers = {}
    if is_init:
        init_ok = any('result' in r and isinstance(r.get('result'), dict) and 'protocolVersion' in r['result']
                      for r in responses)
        if init_ok:
            headers['Mcp-Session-Id'] = _new_session(principal, ctx.protocol_version)
    return _rpc_http(responses if batch else responses[0], 200, headers)


# ── administración (PIN) ────────────────────────────────────────────────────
def _pin_guard():
    bad = _auth.check_pin(request.headers.get('X-Trade-Pin', ''), ip=_ip(), where='admin_api')
    if bad:
        resp = jsonify(bad[0])
        resp.status_code = bad[1]
        if bad[0].get('retry_after'):
            resp.headers['Retry-After'] = str(bad[0]['retry_after'])
        return resp
    if not _auth.db_available():
        return jsonify({'error': 'MCP sin base de datos: falta DATABASE_URL (los tokens se guardan en Postgres)',
                        'error_en': 'MCP has no database: DATABASE_URL is missing (tokens live in Postgres)',
                        'code': 'no_database', 'available': False}), 503
    return None


def _actor(body=None):
    a = str((body or {}).get('actor') or request.headers.get('X-Khipu-Actor') or '').strip()[:120]
    return a or 'ui (PIN)'


def _brokerage_available():
    try:
        import importlib
        svc = importlib.import_module('brokerage.service')
        return bool(svc.available())
    except Exception:  # noqa: BLE001
        return False


@mcp_bp.route('/api/mcp/status')
@rate_limit(60, 60)
def mcp_status():
    by_scope = {}
    for t in _tools.REGISTRY.values():
        by_scope.setdefault(t.scope, []).append(t.name)
    try:
        from mcp_server import oauth as _oauth
        oauth_on = _oauth.oauth_enabled()
    except Exception:  # noqa: BLE001
        oauth_on = False
    return jsonify({
        'available': mcp_enabled(), 'enabled': mcp_enabled(), 'db': _auth.db_available(),
        'endpoint': resource_url(), 'base_url': base_url(),
        'public_url_configured': bool(os.getenv('MCP_PUBLIC_URL', '').strip()),
        'protocol_versions': list(_proto.SUPPORTED_VERSIONS), 'transport': 'streamable-http (application/json)',
        'oauth': oauth_on, 'oauth_metadata': base_url() + '/.well-known/oauth-authorization-server',
        'scopes': list(_auth.SCOPES), 'tools_by_scope': by_scope,
        'mcp_trading_enabled': _tools.trading_enabled(), 'brokerage_available': _brokerage_available(),
        'pin_set': bool(os.getenv('TRADE_PIN', '')), 'pin_strong': _auth.pin_strong(),
        'pin_min_length': _auth.MIN_STRONG_PIN, 'pin_locked_s': _auth.pin_locked_for(),
        'origins_configured': sorted(known_origins()),
        'static_token_configured': bool(os.getenv('MCP_STATIC_TOKEN', '')),
        'limits': _auth.limits(),
    })


@mcp_bp.route('/api/mcp/tools')
@rate_limit(60, 60)
def mcp_tools_catalog():
    return jsonify({'tools': _tools.catalog()})


@mcp_bp.route('/api/mcp/tokens', methods=['GET'])
@rate_limit(120, 60)
def mcp_tokens_list():
    bad = _pin_guard()
    if bad:
        return bad
    from ontology.db import session_scope

    def _q():
        with session_scope() as s:
            return _auth.list_tokens(s)
    try:
        return jsonify({'tokens': _auth.with_schema(_q)})
    except Exception as e:  # noqa: BLE001
        log.warning('mcp tokens list: %s', e)
        return jsonify({'error': 'no se pudieron leer los tokens', 'error_en': 'could not read the tokens',
                        'detail': type(e).__name__}), 500


@mcp_bp.route('/api/mcp/tokens', methods=['POST'])
@rate_limit(20, 60)
def mcp_tokens_create():
    bad = _pin_guard()
    if bad:
        return bad
    body = request.get_json(silent=True) or {}
    from ontology.db import session_scope

    def _c():
        with session_scope() as s:
            row, plain = _auth.create_token(s, body.get('name'), body.get('scopes') or ['read'],
                                            client_id=body.get('client_id'), created_by=_actor(body))
            d = _auth.token_dict(row, _auth._client_names(s, [row.client_id]))
            return d, plain
    try:
        d, plain = _auth.with_schema(_c)
    except ValueError as e:
        return jsonify({'error': getattr(e, 'es', str(e)), 'error_en': getattr(e, 'en', str(e)),
                        'code': getattr(e, 'code', 'bad_request')}), 400
    except Exception as e:  # noqa: BLE001
        log.warning('mcp token create: %s', e)
        return jsonify({'error': 'no se pudo crear el token', 'error_en': 'the token could not be created',
                        'detail': type(e).__name__}), 500
    d.update({'token': plain, 'endpoint': resource_url(),
              'note_es': 'Copia el token AHORA: no se vuelve a mostrar (solo guardamos su huella sha256).',
              'note_en': 'Copy the token NOW: it is never shown again (we only store its sha256 fingerprint).'})
    resp = jsonify(d)
    resp.headers['Cache-Control'] = 'no-store'
    return resp, 201


@mcp_bp.route('/api/mcp/tokens/<token_id>/revoke', methods=['POST'])
@rate_limit(30, 60)
def mcp_tokens_revoke(token_id):
    bad = _pin_guard()
    if bad:
        return bad
    body = request.get_json(silent=True) or {}
    from ontology.db import session_scope

    def _r():
        with session_scope() as s:
            return _auth.revoke_token(s, token_id, _actor(body))
    try:
        res = _auth.with_schema(_r)
    except Exception as e:  # noqa: BLE001
        log.warning('mcp token revoke: %s', e)
        return jsonify({'error': 'no se pudo revocar el token', 'error_en': 'the token could not be revoked',
                        'detail': type(e).__name__}), 500
    return jsonify(res), (200 if res.get('ok') else 404)


@mcp_bp.route('/api/mcp/audit')
@rate_limit(60, 60)
def mcp_audit_list():
    bad = _pin_guard()
    if bad:
        return bad
    try:
        limit = int(request.args.get('limit', 100))
    except (TypeError, ValueError):
        limit = 100
    from ontology.db import session_scope

    def _q():
        with session_scope() as s:
            return _auth.list_audit(s, limit=limit, token_id=request.args.get('token_id') or None)
    try:
        return jsonify({'audit': _auth.with_schema(_q)})
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': 'no se pudo leer la auditoría', 'error_en': 'could not read the audit log',
                        'detail': type(e).__name__}), 500


# ── OAuth 2.1 (rutas en oauth.py) ───────────────────────────────────────────
try:
    from mcp_server import oauth as _oauth_mod
    _oauth_mod.register(mcp_bp)
except Exception as _e:  # noqa: BLE001 — OAuth es opcional; los tokens bearer siguen funcionando
    log.warning('MCP OAuth no registrado (opcional): %s', _e)
