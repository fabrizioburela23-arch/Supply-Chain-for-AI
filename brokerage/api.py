"""brokerage/api.py — blueprint /api/brokerage/* (corretaje multi-cliente).

Todas las rutas de cuenta y todas las que modifican algo exigen el PIN de
trading (header X-Trade-Pin == env TRADE_PIN, misma semántica que
server._trade_auth: sin TRADE_PIN → 403; PIN malo → 401).
Excepciones SIN PIN: GET /status (solo `available` y `trading_enabled`) y
GET /oauth/callback (Alpaca redirige ahí; se valida el `state` firmado).

Freno a la adivinación del PIN (en memoria; 1 worker, ver CLAUDE.md):
  · por IP: 10 fallos en 10 min → 429. La IP es el ÚLTIMO salto de
    X-Forwarded-For (el que añade el proxy de Railway), NO el primero (ese lo
    escribe el cliente y se puede falsificar para esquivar el freno o para
    bloquear a otra persona). Sin X-Forwarded-For → remote_addr.
  · global (respaldo contra ataques repartidos entre muchas IP): 30 fallos en
    10 min desde cualquier IP → todas las rutas con PIN dan 429 hasta que
    pase la ventana, y queda una fila 'pin_lockout' en broker_audit.

GET    /status                          (sin PIN) {available, trading_enabled}
GET    /status/detail                   (PIN) dinero real, OAuth, cifrado, auto-aprobación…
GET    /clients                         lista de clientes (sin secretos)
POST   /clients                         {name, email?, notes?, mode?, risk_profile?, limits?, mandate?, actor}
GET    /clients/<id>                    ficha
PATCH  /clients/<id>                    {name?, notes?, risk_profile?, limits?, mandate?, status?, live_enabled?, confirm_live?, reset_hwm?}
POST   /clients/<id>/credentials        {api_key, api_secret, env: paper|live}
POST   /clients/<id>/oauth/start        {env} → {url} para autorizar en Alpaca
GET    /oauth/callback?code&state       (sin PIN) → página "Cuenta conectada"
GET    /clients/<id>/account            patrimonio y posiciones EN VIVO
POST   /clients/<id>/sync               actualiza estados de órdenes desde Alpaca
GET    /clients/<id>/audit              registro de auditoría del cliente
POST   /orders/preview                  {client_id, symbol, side, notional|qty, order_type?, limit_price?, rationale?}
POST   /orders/<preview_id>/confirm     {actor, confirm: true}
GET    /orders?client_id=&status=&limit=
POST   /orders/<id>/cancel
GET    /approvals                       cola de aprobación humana (propuestas de MCP / comité)
POST   /approvals/<id>/approve          {actor}
POST   /approvals/<id>/reject           {actor, reason?}
GET    /audit                           registro global (últimas 200)
"""
import hmac
import html
import logging
import os
import threading
import time
from functools import wraps

from flask import Blueprint, Response, jsonify, request

from core.http import rate_limit

log = logging.getLogger('khipu')

brokerage_bp = Blueprint('brokerage', __name__, url_prefix='/api/brokerage')


def _db_ok():
    try:
        from ontology.db import ontology_available
        return ontology_available()
    except Exception:  # noqa: BLE001
        return False


def _unavailable():
    return jsonify({'error': 'Corretaje no disponible — falta DATABASE_URL (Postgres)',
                    'error_en': 'Brokerage unavailable — DATABASE_URL (Postgres) is missing',
                    'available': False, 'code': 'no_database'}), 503


# Freno a la adivinación del PIN (ver docstring). Estructuras acotadas y con lock
# (gunicorn corre 8 hilos): solo se guardan IPs con fallos recientes.
_PIN_FAILS = {}                 # ip → [timestamps de fallos]
_PIN_GLOBAL = []                # timestamps de fallos de cualquier IP
_PIN_LOCK = threading.Lock()
_PIN_STATE = {'global_audited_at': 0.0}
PIN_MAX_FAILS, PIN_WINDOW_S = 10, 600
PIN_GLOBAL_MAX = 30
PIN_MAX_IPS = 5000


def _client_ip():
    """ÚLTIMO salto de X-Forwarded-For (lo añade el proxy de confianza); el
    primero lo controla quien hace la petición."""
    xff = request.headers.get('X-Forwarded-For', '')
    hops = [h.strip() for h in xff.split(',') if h.strip()]
    return (hops[-1] if hops else (request.remote_addr or 'unknown'))[:64]


def _prune(now):
    cut = now - PIN_WINDOW_S
    _PIN_GLOBAL[:] = [t for t in _PIN_GLOBAL if t > cut]
    for ip in [k for k, v in _PIN_FAILS.items() if not v or v[-1] <= cut]:
        _PIN_FAILS.pop(ip, None)
    if len(_PIN_FAILS) > PIN_MAX_IPS:             # tope duro de memoria: se descartan las más viejas
        for ip in sorted(_PIN_FAILS, key=lambda k: _PIN_FAILS[k][-1])[:len(_PIN_FAILS) - PIN_MAX_IPS]:
            _PIN_FAILS.pop(ip, None)


def _audit_global_lock(n):
    try:
        if not _db_ok():
            return
        from ontology.db import session_scope
        from brokerage.service import audit
        with session_scope() as s:
            audit(s, 'sistema', 'pin_lockout', detail={'scope': 'global', 'failures_10min': n})
    except Exception as e:  # noqa: BLE001
        log.warning('brokerage: no se registró el bloqueo global del PIN (%s)', type(e).__name__)


def _pin_error():
    want = os.getenv('TRADE_PIN', '')
    if not want:
        return jsonify({'error': 'Trading deshabilitado — configura TRADE_PIN en Railway',
                        'error_en': 'Trading disabled — set TRADE_PIN in Railway',
                        'code': 'trading_disabled'}), 403
    ip, now = _client_ip(), time.time()
    with _PIN_LOCK:
        _prune(now)
        n_global = len(_PIN_GLOBAL)
        n_ip = len(_PIN_FAILS.get(ip) or ())
    if n_global >= PIN_GLOBAL_MAX:
        log.warning('brokerage: PIN bloqueado globalmente (%d fallos en 10 min)', n_global)
        return jsonify({'error': 'Demasiados intentos de PIN fallidos (desde varias direcciones): el corretaje '
                                 'queda bloqueado 10 minutos',
                        'error_en': 'Too many failed PIN attempts (from several addresses): brokerage is locked '
                                    'for 10 minutes', 'code': 'pin_locked_global'}), 429
    if n_ip >= PIN_MAX_FAILS:
        return jsonify({'error': 'Demasiados intentos de PIN fallidos: espera 10 minutos',
                        'error_en': 'Too many failed PIN attempts: wait 10 minutes', 'code': 'pin_locked'}), 429
    got = request.headers.get('X-Trade-Pin', '')
    if not hmac.compare_digest(got.encode(), want.encode()):
        audit_now = False
        with _PIN_LOCK:
            _PIN_FAILS.setdefault(ip, []).append(now)
            _PIN_GLOBAL.append(now)
            n_global = len(_PIN_GLOBAL)
            if n_global >= PIN_GLOBAL_MAX and now - _PIN_STATE['global_audited_at'] > PIN_WINDOW_S:
                _PIN_STATE['global_audited_at'] = now
                audit_now = True
        if audit_now:
            _audit_global_lock(n_global)
        return jsonify({'error': 'PIN de trading incorrecto o faltante', 'error_en': 'Wrong or missing trading PIN',
                        'code': 'invalid_pin'}), 401
    return None


def guarded(f):
    """PIN + base de datos + manejo uniforme de errores."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        bad = _pin_error()
        if bad:
            return bad
        if not _db_ok():
            return _unavailable()
        try:
            return _with_schema(lambda: f(*args, **kwargs))
        except Exception as e:  # noqa: BLE001
            log.warning('brokerage %s: %s', f.__name__, e)
            return jsonify({'error': 'error interno del corretaje', 'error_en': 'internal brokerage error',
                            'detail': f'{type(e).__name__}: {str(e).splitlines()[0][:200] if str(e) else ""}'}), 500
    return wrapper


def _with_schema(fn):
    """Si las tablas aún no existen (base que arrancó después), las crea y reintenta."""
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        msg = type(e).__name__ + str(e)
        if 'does not exist' not in msg and 'UndefinedTable' not in msg:
            raise
        from ontology.db import init_schema
        init_schema(retries=1)
        return fn()


def _body():
    return request.get_json(silent=True) or {}


def _actor(body=None):
    a = str((body or {}).get('actor') or request.headers.get('X-Khipu-Actor') or '').strip()[:120]
    return a or 'ui (PIN)'


def _svc():
    from brokerage import service
    return service


def _session():
    from ontology.db import session_scope
    return session_scope()


def _res(d, ok_code=200, err_code=400):
    if not isinstance(d, dict):
        return jsonify(d)
    if d.get('ok') is False:
        code = {'not_found': 404, 'requires_human_approval': 409, 'used': 409, 'expired': 410,
                'bad_status': 409, 'source_mismatch': 403, 'ambiguous': 409, 'duplicate_name': 409,
                'account_changed': 409, 'bad_request': 400, 'unknown_state': 502,
                'broker_rejected': 502}.get(d.get('code'), err_code)
        return jsonify(d), code
    return jsonify(d), ok_code


# ── estado ──────────────────────────────────────────────────────────────────
@brokerage_bp.route('/status')
@rate_limit(60, 60)
def bk_status():
    """SIN PIN: solo si está disponible y si el interruptor está encendido
    (la postura de seguridad —cifrado, auto-aprobación…— va en /status/detail)."""
    try:
        info = _svc().public_status()
    except Exception as e:  # noqa: BLE001
        return jsonify({'available': False, 'error': f'{type(e).__name__}'}), 200
    info['available'] = bool(info.get('available') and _db_ok())
    return jsonify(info)


@brokerage_bp.route('/status/detail')
@rate_limit(60, 60)
def bk_status_detail():
    bad = _pin_error()
    if bad:
        return bad
    try:
        info = _svc().status_info()
    except Exception as e:  # noqa: BLE001
        return jsonify({'available': False, 'error': f'{type(e).__name__}'}), 200
    info['available'] = bool(info.get('available') and _db_ok())
    return jsonify(info)


# ── clientes ────────────────────────────────────────────────────────────────
@brokerage_bp.route('/clients', methods=['GET'])
@rate_limit(120, 60)
@guarded
def bk_clients():
    with _session() as s:
        return jsonify({'clients': _svc().list_clients(s)})


@brokerage_bp.route('/clients', methods=['POST'])
@rate_limit(20, 60)
@guarded
def bk_client_create():
    b = _body()
    with _session() as s:
        return _res(_svc().create_client(s, b.get('name'), email=b.get('email'), notes=b.get('notes'),
                                         mode=b.get('mode') or 'paper', risk_profile=b.get('risk_profile') or 'moderado',
                                         limits=b.get('limits'), mandate=b.get('mandate'), actor=_actor(b)), 201)


@brokerage_bp.route('/clients/<client_id>', methods=['GET'])
@rate_limit(120, 60)
@guarded
def bk_client_get(client_id):
    with _session() as s:
        c = _svc().get_client(s, client_id)
    if not c:
        return jsonify({'ok': False, 'error': 'cliente no encontrado', 'error_en': 'client not found',
                        'code': 'not_found'}), 404
    return jsonify({'ok': True, 'client': c})


@brokerage_bp.route('/clients/<client_id>', methods=['PATCH'])
@rate_limit(40, 60)
@guarded
def bk_client_patch(client_id):
    b = _body()
    patch = {k: b[k] for k in ('name', 'email', 'notes', 'risk_profile', 'limits', 'mandate', 'status', 'mode',
                               'live_enabled', 'confirm_live', 'reset_hwm') if k in b}
    with _session() as s:
        return _res(_svc().update_client(s, client_id, patch, actor=_actor(b)))


@brokerage_bp.route('/clients/<client_id>/credentials', methods=['POST'])
@rate_limit(10, 60)
@guarded
def bk_client_creds(client_id):
    b = _body()
    with _session() as s:
        return _res(_svc().set_credentials(s, client_id, b.get('api_key'), b.get('api_secret'),
                                           env=b.get('env') or 'paper', actor=_actor(b),
                                           verify=b.get('verify', True) is not False))


@brokerage_bp.route('/clients/<client_id>/oauth/start', methods=['POST'])
@rate_limit(10, 60)
@guarded
def bk_oauth_start(client_id):
    b = _body()
    with _session() as s:
        return _res(_svc().oauth_start(s, client_id, env=b.get('env') or 'paper', actor=_actor(b)))


@brokerage_bp.route('/clients/<client_id>/account', methods=['GET'])
@rate_limit(60, 60)
@guarded
def bk_account(client_id):
    with _session() as s:
        snap = _svc().account_snapshot(s, client_id)
    code = 200 if snap.get('ok') else (404 if not snap.get('client') else 502)
    return jsonify(snap), code


@brokerage_bp.route('/clients/<client_id>/sync', methods=['POST'])
@rate_limit(20, 60)
@guarded
def bk_sync(client_id):
    b = _body()
    with _session() as s:
        return _res(_svc().sync_orders(s, client_id, actor=_actor(b)), err_code=502)


@brokerage_bp.route('/clients/<client_id>/audit', methods=['GET'])
@rate_limit(60, 60)
@guarded
def bk_client_audit(client_id):
    with _session() as s:
        return jsonify({'items': _svc().list_audit(s, client_id=client_id,
                                                   limit=request.args.get('limit', 100, type=int))})


@brokerage_bp.route('/audit', methods=['GET'])
@rate_limit(60, 60)
@guarded
def bk_audit():
    with _session() as s:
        return jsonify({'items': _svc().list_audit(s, limit=request.args.get('limit', 200, type=int))})


# ── órdenes ─────────────────────────────────────────────────────────────────
@brokerage_bp.route('/orders/preview', methods=['POST'])
@rate_limit(30, 60)
@guarded
def bk_preview():
    b = _body()
    with _session() as s:
        return _res(_svc().preview_order(
            s, b.get('client_id'), b.get('symbol'), b.get('side'), notional=b.get('notional'), qty=b.get('qty'),
            order_type=b.get('order_type') or b.get('type') or 'market', limit_price=b.get('limit_price'),
            source='ui', requested_by=_actor(b), rationale=b.get('rationale')))


@brokerage_bp.route('/orders/<preview_id>/confirm', methods=['POST'])
@rate_limit(20, 60)
@guarded
def bk_confirm(preview_id):
    b = _body()
    if b.get('confirm') is not True:
        return jsonify({'ok': False, 'error': 'marca «confirmo» para enviar la orden (confirm=true)',
                        'error_en': 'tick "I confirm" to send the order (confirm=true)',
                        'code': 'confirmation_required'}), 400
    with _session() as s:
        return _res(_svc().confirm_order(s, preview_id, _actor(b), source='ui'), err_code=422)


@brokerage_bp.route('/orders', methods=['GET'])
@rate_limit(120, 60)
@guarded
def bk_orders():
    with _session() as s:
        return jsonify({'orders': _svc().list_orders(s, client_id=request.args.get('client_id') or None,
                                                     status=request.args.get('status') or None,
                                                     limit=request.args.get('limit', 50, type=int))})


@brokerage_bp.route('/orders/<order_id>/cancel', methods=['POST'])
@rate_limit(30, 60)
@guarded
def bk_cancel(order_id):
    b = _body()
    with _session() as s:
        return _res(_svc().cancel_order(s, order_id, _actor(b)), err_code=502)


# ── aprobaciones (humano en el circuito) ────────────────────────────────────
@brokerage_bp.route('/approvals', methods=['GET'])
@rate_limit(120, 60)
@guarded
def bk_approvals():
    with _session() as s:
        return jsonify({'approvals': _svc().pending_approvals(s)})


@brokerage_bp.route('/approvals/<preview_id>/approve', methods=['POST'])
@rate_limit(20, 60)
@guarded
def bk_approve(preview_id):
    b = _body()
    with _session() as s:
        return _res(_svc().approve_preview(s, preview_id, _actor(b)), err_code=422)


@brokerage_bp.route('/approvals/<preview_id>/reject', methods=['POST'])
@rate_limit(30, 60)
@guarded
def bk_reject(preview_id):
    b = _body()
    with _session() as s:
        return _res(_svc().reject_preview(s, preview_id, _actor(b), reason=str(b.get('reason') or '')[:300]))


# ── OAuth: Alpaca redirige aquí (SIN PIN; se valida el state firmado) ───────
_PAGE = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Khipus · Alpaca</title>
<style>body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
background:#06090F;color:#E8EDFB;font-family:Inter,system-ui,sans-serif;padding:16px;box-sizing:border-box}}
.c{{max-width:460px;width:100%;border:1px solid rgba(122,158,255,.25);border-radius:16px;padding:24px;
background:#0B1222;text-align:center}}h1{{font-size:20px;margin:8px 0 12px}}p{{color:#9BA6C4;line-height:1.55;font-size:14px}}
.i{{font-size:40px}}.en{{margin-top:14px;padding-top:12px;border-top:1px solid rgba(122,158,255,.15)}}</style></head>
<body><div class="c"><div class="i">{icon}</div><h1>{title_es}</h1><p>{body_es}</p>
<div class="en"><h1>{title_en}</h1><p>{body_en}</p></div></div></body></html>"""


@brokerage_bp.route('/oauth/callback', methods=['GET'])
@rate_limit(20, 60)
def bk_oauth_callback():
    def page(ok, detail='', detail_en=None):
        d = html.escape(detail or '')
        de = html.escape(detail_en if detail_en is not None else (detail or ''))
        if ok:
            txt = dict(icon='✅', title_es='Cuenta conectada', title_en='Account connected',
                       body_es=f'{d} Ya puedes cerrar esta ventana y volver a Khipus.',
                       body_en=f'{de} You can close this window and return to Khipus.')
        else:
            txt = dict(icon='⚠️', title_es='No se pudo conectar la cuenta', title_en='Could not connect the account',
                       body_es=f'{d} Vuelve a Khipus e inténtalo otra vez desde 👥 Clientes.',
                       body_en=f'{de} Go back to Khipus and try again from 👥 Clients.')
        return Response(_PAGE.format(**txt), status=200 if ok else 400, mimetype='text/html')

    if not _db_ok():
        return page(False, 'Falta DATABASE_URL en el servidor.', 'DATABASE_URL is missing on the server.')
    try:
        def run():
            with _session() as s:
                return _svc().oauth_callback(s, request.args.get('state'), request.args.get('code'),
                                             error=request.args.get('error'))
        r = _with_schema(run)
    except Exception as e:  # noqa: BLE001
        log.warning('brokerage oauth callback: %s', type(e).__name__)
        return page(False, 'Error interno.', 'Internal error.')
    if r.get('ok'):
        paper = r.get('env') == 'paper'
        return page(True, f'«{r.get("client_name")}» quedó conectado en modo '
                          f'{"papel (simulado)" if paper else "DINERO REAL"}.',
                    f'"{r.get("client_name")}" is now connected in '
                    f'{"paper (simulated)" if paper else "REAL MONEY"} mode.')
    return page(False, r.get('error') or '', r.get('error_en') or r.get('error') or '')
