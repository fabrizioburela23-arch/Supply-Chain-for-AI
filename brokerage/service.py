"""brokerage/service.py — lógica del corretaje multi-cliente (CONTRATO COMPARTIDO).

Lo consumen: brokerage/api.py (UI con PIN), research/committee.py (comité de
inversión, source='committee') y mcp_server/ (agentes e IAs, source='mcp').
Esos módulos lo importan de forma perezosa y toleran que no exista.

Flujo de una orden (el mismo registro avanza de estado en broker_orders):

  preview_order ──► 'previewed'          (UI; caduca a los 5 min)
               └──► 'pending_approval'   (MCP/comité: SIEMPRE espera a un humano,
                                           salvo BROKERAGE_AUTO_APPROVE_PAPER=on
                                           y cliente en papel — y eso se vuelve a
                                           comprobar al confirmar)
               └──► 'rejected'           (algún control de riesgo bloquea)
  confirm_order / approve_preview ──► ¿misma cuenta y modo que al previsualizar?
      ──► controles OTRA VEZ ──► 'approved' ──► envío a Alpaca con
      client_order_id = id de la previsualización (idempotente) ──► 'submitted'
      ──► sync_orders ──► 'filled' / 'canceled'…
  Si la red falla al enviar y no se puede saber si Alpaca la recibió, la fila
  queda 'submitted' con alpaca_status='unknown' (cuenta para duplicados y
  límite diario, y bloquea repetirla) hasta que sync_orders la reconcilia por
  client_order_id. 'failed' SOLO con un rechazo definitivo (4xx) de Alpaca.

Reglas de dinero: papel por defecto; dinero real SOLO con
BROKERAGE_LIVE_ENABLED=on Y client.live_enabled; interruptor global
BROKERAGE_TRADING_ENABLED=off bloquea todo lo que pasa por este módulo; toda
acción queda en broker_audit (append-only, lo impone un trigger).
Nunca se devuelve una credencial: solo `credentials_hint` (****1234).
Todo error devuelto trae `error` (es) y `error_en` (en).
"""
import hashlib
import logging
import math
import os
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from brokerage import alpaca as _alp
from brokerage import crypto as _crypto
from brokerage import risk as _risk
from brokerage.models import (BrokerAudit, BrokerClient, BrokerOAuthState, BrokerOrder,
                              RISK_PROFILES, SOURCES)

log = logging.getLogger('khipu')

HOUSE_ID = 'house'
HOUSE_NAME = 'Cuenta principal'
PREVIEW_TTL_S = 300
OAUTH_STATE_TTL_S = 900
UNKNOWN_GRACE_S = 120          # tras esto, "Alpaca no la tiene" = nunca llegó → 'failed'
MAX_SYMBOL_LEN = 20            # = BrokerOrder.symbol String(20)
OPEN_STATUSES = ('submitted', 'partially_filled')
SENT_STATUSES = ('approved', 'submitted', 'filled', 'partially_filled')
FINAL_STATUSES = ('filled', 'canceled', 'rejected', 'expired', 'failed')

# Alpaca → nuestro vocabulario
_ALPACA_STATUS = {
    'new': 'submitted', 'accepted': 'submitted', 'pending_new': 'submitted', 'accepted_for_bidding': 'submitted',
    'calculated': 'submitted', 'pending_replace': 'submitted', 'replaced': 'submitted', 'held': 'submitted',
    'done_for_day': 'submitted', 'stopped': 'submitted', 'suspended': 'submitted', 'pending_cancel': 'submitted',
    'partially_filled': 'partially_filled', 'filled': 'filled', 'canceled': 'canceled', 'expired': 'expired',
    'rejected': 'rejected',
}


# ════════════════════════════════════════════════════════════════════════════
# utilidades
# ════════════════════════════════════════════════════════════════════════════
def available():
    """¿Se puede usar el corretaje? (requiere la base de la ontología)."""
    try:
        from ontology.db import ontology_available
        return bool(ontology_available())
    except Exception:  # noqa: BLE001
        return False


def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.isoformat() if dt else None


def _f(x):
    """float finito o None (NaN/inf nunca pasan como montos)."""
    try:
        v = float(x) if x is not None and x != '' else None
    except (TypeError, ValueError):
        return None
    return v if v is not None and math.isfinite(v) else None


def _aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _err(code, es, en, **extra):
    """Error bilingüe uniforme: {ok: False, code, error (es), error_en}."""
    d = {'ok': False, 'error': es, 'error_en': en}
    if code:
        d['code'] = code
    d.update(extra)
    return d


def _not_found():
    return _err('not_found', 'cliente no encontrado', 'client not found')


class _Bad(ValueError):
    """Validación con mensaje en ambos idiomas."""

    def __init__(self, es, en):
        super().__init__(es)
        self.es, self.en = es, en


def _sha(s):
    return hashlib.sha256(str(s or '').encode()).hexdigest()


def approval_ttl_s():
    try:
        return max(5, int(os.getenv('BROKERAGE_APPROVAL_TTL_MIN', '1440'))) * 60
    except ValueError:
        return 1440 * 60


def audit(session, actor, action, client_id=None, order_id=None, detail=None):
    """APPEND-ONLY. Jamás se escribe un secreto en `detail`."""
    session.add(BrokerAudit(actor=str(actor or 'sistema')[:120], action=str(action)[:40],
                            client_id=client_id, order_id=order_id, detail=detail or {}))


def list_audit(session, client_id=None, limit=100):
    q = session.query(BrokerAudit)
    if client_id:
        q = q.filter(BrokerAudit.client_id == client_id)
    rows = q.order_by(BrokerAudit.id.desc()).limit(max(1, min(int(limit or 100), 500))).all()
    return [{'id': r.id, 'ts': _iso(r.ts), 'actor': r.actor, 'action': r.action, 'client_id': r.client_id,
             'order_id': r.order_id, 'detail': r.detail or {}} for r in rows]


# ════════════════════════════════════════════════════════════════════════════
# clientes
# ════════════════════════════════════════════════════════════════════════════
def _connected(rec):
    if rec.auth_type == 'env':
        return _alp.house_env() is not None
    return bool(rec.enc_credentials)


def account_fingerprint(rec):
    """Huella de la cuenta REAL detrás del cliente (modo + URL + credenciales).
    Se guarda en cada previsualización: si cambia antes de ejecutar (otra
    cuenta, papel → dinero real…), la orden no se envía. Nunca expone secretos."""
    if rec is None:
        return None
    if rec.auth_type == 'env':
        env = _alp.house_env() or {}
        mat = f"env|{env.get('base') or ''}|{_sha(env.get('key'))}"
    else:
        mat = f"{rec.auth_type}|{rec.mode}|{rec.base_url or _alp.base_for_mode(rec.mode)}|{_sha(rec.enc_credentials)}"
    return _sha(mat)[:32]


def client_dict(rec):
    """Vista pública del cliente — SIN secretos (solo el hint enmascarado)."""
    limits = _risk.effective_limits(rec.risk_profile, rec.risk_limits)
    mandate = _risk.effective_mandate(rec.risk_profile, rec.mandate)
    hwm, eq = rec.hwm_equity, rec.last_equity
    dd = (max(0.0, (hwm - eq) / hwm * 100.0) if (hwm and eq is not None and hwm > 0) else None)
    return {
        'id': rec.id, 'client_id': rec.id, 'name': rec.name, 'email': rec.email, 'notes': rec.notes,
        'mode': rec.mode, 'paper': rec.mode != 'live', 'live_enabled': bool(rec.live_enabled),
        'auth_type': rec.auth_type, 'is_house': rec.auth_type == 'env', 'connected': _connected(rec),
        'credentials_hint': rec.credentials_hint or '',
        'base_url': rec.base_url or _alp.base_for_mode(rec.mode),
        'risk_profile': rec.risk_profile, 'limits': limits, 'limit_overrides': dict(rec.risk_limits or {}),
        # el comité lee mandate.max_position_pct / restricted_symbols / allowed_symbols
        'mandate': dict(mandate, **limits),
        'status': rec.status, 'hwm_equity': hwm, 'hwm_at': _iso(rec.hwm_at),
        'last_equity': eq, 'last_snapshot_at': _iso(rec.last_snapshot_at), 'drawdown_pct': dd,
        'created_at': _iso(rec.created_at), 'updated_at': _iso(rec.updated_at),
    }


def _expire_open(session, client_id, actor, reason_es, reason_en):
    """Caduca las previsualizaciones/propuestas abiertas de un cliente (la cuenta
    cambió). SKIP LOCKED: la que otra transacción esté ejecutando en este
    instante la frena su propio control de huella en _execute."""
    rows = (session.query(BrokerOrder)
            .filter(BrokerOrder.client_id == client_id, BrokerOrder.status.in_(('previewed', 'pending_approval')))
            .with_for_update(skip_locked=True).all())
    for r in rows:
        r.status, r.updated_at = 'expired', _now()
        r.error, r.error_en = reason_es[:1000], reason_en[:1000]
        audit(session, actor, 'preview_expired', client_id, r.id, detail={'reason': 'account_changed'})
        _notify_closed(session, r, actor, reason_es)
    return len(rows)


def _account_changed(session, rec, actor, why_es, why_en, detail=None):
    """La cuenta detrás del cliente cambió (modo, URL o credenciales): el máximo
    histórico ya no sirve (si no, el stop por caída bloquearía toda compra) y
    ninguna previsualización hecha contra la cuenta anterior puede ejecutarse."""
    rec.hwm_equity = rec.hwm_at = rec.last_equity = rec.last_snapshot_at = None
    with session.no_autoflush:          # bloquea órdenes ANTES que el cliente (mismo orden que _execute)
        n = _expire_open(session, rec.id, actor,
                         f'la cuenta del cliente cambió ({why_es}): vuelve a previsualizar',
                         f"the client's account changed ({why_en}): preview again")
    audit(session, actor, 'account_changed', rec.id,
          detail=dict(detail or {}, reason=why_es, hwm_reset=True, expired_previews=n))
    return n


def ensure_house_client(session):
    """Registra la cuenta de la casa (ALPACA_KEY/SECRET/BASE) como cliente
    «Cuenta principal» si hay credenciales en el entorno. Idempotente y a
    prueba de carreras (INSERT … ON CONFLICT DO NOTHING). Si cambió
    ALPACA_BASE o ALPACA_KEY, el modo sigue al entorno, se reinicia el máximo
    y caducan las previsualizaciones abiertas."""
    env = _alp.house_env()
    if not env:
        return None
    mode = 'paper' if _alp.is_paper_base(env['base']) else 'live'
    hint = _crypto.mask(env['key'])
    try:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(BrokerClient.__table__).values(
            id=HOUSE_ID, name=HOUSE_NAME, notes='Cuenta de Alpaca configurada en el servidor (ALPACA_KEY).',
            mode=mode, live_enabled=False, auth_type='env', base_url=env['base'],
            credentials_hint=hint, risk_profile='moderado', risk_limits={}, mandate={},
            status='active').on_conflict_do_nothing(index_elements=['id'])
        with session.begin_nested():          # SAVEPOINT: un fallo no aborta la transacción del llamador
            res = session.execute(stmt)
        if getattr(res, 'rowcount', 0):
            audit(session, 'sistema', 'client_created', HOUSE_ID, detail={'auth_type': 'env', 'mode': mode})
    except Exception as e:  # noqa: BLE001
        log.warning('brokerage: no se pudo registrar la cuenta principal: %s', type(e).__name__)
        return None
    rec = session.get(BrokerClient, HOUSE_ID)
    if rec and rec.auth_type == 'env':
        if rec.base_url != env['base'] or rec.mode != mode or (rec.credentials_hint or '') != hint:
            before = {'from_mode': rec.mode, 'to_mode': mode}
            rec.base_url, rec.mode, rec.credentials_hint = env['base'], mode, hint
            rec.updated_at = _now()
            _account_changed(session, rec, 'sistema', 'cambió ALPACA_KEY/ALPACA_BASE en el servidor',
                             'ALPACA_KEY/ALPACA_BASE changed on the server', detail=before)
    return rec


def list_clients(session):
    ensure_house_client(session)
    rows = session.query(BrokerClient).order_by(BrokerClient.created_at.asc(), BrokerClient.name.asc()).all()
    return [client_dict(r) for r in rows]


def _lookup(session, client_id):
    """(rec, None) o (None, error). Acepta id o nombre EXACTO (sin mayúsculas);
    un nombre que coincide con varios clientes NUNCA elige uno: 'ambiguous'."""
    if client_id is None or not str(client_id).strip():
        return None, _not_found()
    if str(client_id) == HOUSE_ID:
        ensure_house_client(session)
    rec = session.get(BrokerClient, str(client_id)[:40])
    if rec is not None:
        return rec, None
    name = str(client_id).strip().lower()[:200]
    rows = session.query(BrokerClient).filter(func.lower(BrokerClient.name) == name).limit(6).all()
    if len(rows) == 1:
        return rows[0], None
    if rows:
        ids = ', '.join(r.id for r in rows)
        return None, _err('ambiguous', f'hay {len(rows)} clientes llamados «{client_id}»: usa su id ({ids})',
                          f'there are {len(rows)} clients named "{client_id}": use the id ({ids})',
                          candidates=[{'id': r.id, 'name': r.name} for r in rows])
    return None, _not_found()


def _client_rec(session, client_id):
    return _lookup(session, client_id)[0]


def get_client(session, client_id):
    rec = _client_rec(session, client_id)
    return client_dict(rec) if rec else None


def _name_taken(session, name, exclude_id=None):
    q = session.query(BrokerClient.id).filter(func.lower(BrokerClient.name) == str(name).strip().lower())
    if exclude_id:
        q = q.filter(BrokerClient.id != exclude_id)
    return q.first() is not None


def _clean_limits(raw):
    out = {}
    for k in _risk.LIMIT_KEYS:
        if k not in (raw or {}):
            continue
        v = raw.get(k)
        if v is None or v == '':
            continue
        fv = _f(v)
        if fv is None or fv <= 0:
            raise _Bad(f'límite inválido {k}={v!r} (debe ser un número mayor que 0)',
                       f'invalid limit {k}={v!r} (must be a number greater than 0)')
        out[k] = fv
    return out


def _clean_mandate(raw):
    raw = raw if isinstance(raw, dict) else {}
    m = _risk.effective_mandate(None, raw)
    out = {'restricted_symbols': m['restricted_symbols'], 'allowed_symbols': m['allowed_symbols'],
           'notes': m['notes'], 'allow_margin': raw.get('allow_margin') is True}
    if isinstance(raw.get('allowed_asset_classes'), list) and raw['allowed_asset_classes']:
        out['allowed_asset_classes'] = m['allowed_asset_classes']
    for s in out['restricted_symbols'] + out['allowed_symbols']:
        if not _risk.valid_symbol(s):
            raise _Bad(f'símbolo inválido en el mandato: {s}', f'invalid symbol in the mandate: {s}')
    return out


def create_client(session, name, email=None, notes=None, mode='paper', risk_profile='moderado',
                  limits=None, mandate=None, actor='ui'):
    name = str(name or '').strip()[:200]
    if not name:
        return _err('bad_request', 'el nombre es obligatorio', 'the name is required')
    if mode not in ('paper', 'live'):
        return _err('bad_request', "mode debe ser 'paper' o 'live'", "mode must be 'paper' or 'live'")
    if risk_profile not in RISK_PROFILES:
        return _err('bad_request', f'perfil de riesgo inválido (usa: {", ".join(RISK_PROFILES)})',
                    f'invalid risk profile (use: {", ".join(RISK_PROFILES)})')
    if _name_taken(session, name):
        return _err('duplicate_name', f'ya existe un cliente llamado «{name}»: usa otro nombre (p. ej. con apellido)',
                    f'a client named "{name}" already exists: use another name (e.g. with surname)')
    try:
        lim = _clean_limits(limits or {})
        man = _clean_mandate(mandate or {})
    except _Bad as e:
        return _err('bad_request', e.es, e.en)
    rec = BrokerClient(name=name, email=(str(email).strip()[:200] or None) if email else None,
                       notes=(str(notes)[:2000] if notes else None), mode=mode, live_enabled=False,
                       auth_type='keys', base_url=_alp.base_for_mode(mode), risk_profile=risk_profile,
                       risk_limits=lim, mandate=man, status='active')
    session.add(rec)
    session.flush()
    audit(session, actor, 'client_created', rec.id, detail={'name': name, 'mode': mode, 'risk_profile': risk_profile})
    return {'ok': True, 'client': client_dict(rec)}


def update_client(session, client_id, patch, actor='ui'):
    rec, err = _lookup(session, client_id)
    if err:
        return err
    patch = patch or {}
    changed = {}
    mode_changed = False
    try:
        for k in ('name', 'email', 'notes'):
            if k in patch:
                v = str(patch[k] or '').strip()
                if k == 'name':
                    if not v:
                        raise _Bad('el nombre no puede quedar vacío', 'the name cannot be empty')
                    v = v[:200]
                    if _name_taken(session, v, exclude_id=rec.id):
                        raise _Bad(f'ya existe otro cliente llamado «{v}»', f'another client is already named "{v}"')
                    rec.name = v
                elif k == 'email':
                    rec.email = v[:200] or None           # = String(200)
                else:
                    rec.notes = v[:2000] or None
                changed[k] = True
        if 'risk_profile' in patch:
            if patch['risk_profile'] not in RISK_PROFILES:
                raise _Bad(f'perfil de riesgo inválido (usa: {", ".join(RISK_PROFILES)})',
                           f'invalid risk profile (use: {", ".join(RISK_PROFILES)})')
            rec.risk_profile = patch['risk_profile']
            changed['risk_profile'] = rec.risk_profile
        if 'limits' in patch:
            rec.risk_limits = _clean_limits(patch.get('limits') or {})
            changed['limits'] = rec.risk_limits
        if 'mandate' in patch:
            rec.mandate = _clean_mandate(patch.get('mandate') or {})
            changed['mandate'] = rec.mandate
        if 'status' in patch:
            if patch['status'] not in ('active', 'paused'):
                raise _Bad("status debe ser 'active' o 'paused'", "status must be 'active' or 'paused'")
            rec.status = patch['status']
            changed['status'] = rec.status
        if 'mode' in patch and patch['mode'] != rec.mode:
            if patch['mode'] not in ('paper', 'live'):
                raise _Bad("mode debe ser 'paper' o 'live'", "mode must be 'paper' or 'live'")
            if rec.auth_type == 'env':
                raise _Bad('el modo de la cuenta principal lo decide ALPACA_BASE en el servidor',
                           "the main account's mode is set by ALPACA_BASE on the server")
            if rec.enc_credentials:
                raise _Bad('para cambiar de modo, vuelve a conectar la cuenta con claves/autorización de ese modo '
                           '(las de papel no sirven en dinero real y viceversa)',
                           'to change mode, reconnect the account with keys/authorization for that mode '
                           '(paper keys do not work for real money and vice versa)')
            rec.mode = patch['mode']
            rec.base_url = _alp.base_for_mode(rec.mode)
            changed['mode'] = rec.mode
            mode_changed = True
        if 'live_enabled' in patch:
            want = bool(patch['live_enabled'])
            if want and not rec.live_enabled and patch.get('confirm_live') is not True:
                raise _Bad('habilitar DINERO REAL exige confirmación explícita (confirm_live=true)',
                           'enabling REAL MONEY requires explicit confirmation (confirm_live=true)')
            rec.live_enabled = want
            changed['live_enabled'] = want
        if patch.get('reset_hwm'):
            rec.hwm_equity, rec.hwm_at = None, None
            changed['reset_hwm'] = True
    except _Bad as e:
        return _err('bad_request', e.es, e.en)
    rec.updated_at = _now()
    if mode_changed:
        _account_changed(session, rec, actor, 'cambió el modo papel/real', 'paper/live mode changed')
    session.flush()
    if changed:
        audit(session, actor, 'client_updated', rec.id, detail=changed)
        if 'live_enabled' in changed:
            audit(session, actor, 'live_enabled_on' if changed['live_enabled'] else 'live_enabled_off', rec.id)
    return {'ok': True, 'client': client_dict(rec)}


def pause_client(session, client_id, actor='ui'):
    return update_client(session, client_id, {'status': 'paused'}, actor)


def resume_client(session, client_id, actor='ui'):
    return update_client(session, client_id, {'status': 'active'}, actor)


# ════════════════════════════════════════════════════════════════════════════
# conexión con Alpaca
# ════════════════════════════════════════════════════════════════════════════
def make_alpaca(rec):
    """AlpacaClient para el cliente (los tests lo sustituyen por uno falso)."""
    if rec.auth_type == 'env':
        env = _alp.house_env()
        if not env:
            raise _alp.AlpacaError('ALPACA_KEY/ALPACA_SECRET sin configurar en el servidor')
        return _alp.AlpacaClient(env['base'], key=env['key'], secret=env['secret'])
    try:
        creds = _crypto.decrypt_json(rec.enc_credentials)
    except _crypto.CryptoUnavailable as e:
        raise _alp.AlpacaError(str(e)) from e
    base = rec.base_url or _alp.base_for_mode(rec.mode)
    if rec.auth_type == 'oauth':
        if not creds.get('token'):
            raise _alp.AlpacaError('cuenta sin autorizar: usa «Conectar con Alpaca»')
        return _alp.AlpacaClient(base, token=creds['token'])
    if not (creds.get('key') and creds.get('secret')):
        raise _alp.AlpacaError('cuenta sin claves de Alpaca: pégalas en «Conectar»')
    return _alp.AlpacaClient(base, key=creds['key'], secret=creds['secret'])


def _valid_cred(s):
    s = str(s or '').strip()
    return s if (4 <= len(s) <= 256 and not any(ch.isspace() for ch in s)) else ''


def _enc_key_error():
    """Con la clave de cifrado por defecto (pública, está en el repo) NO se
    guardan credenciales: cualquiera con una copia de la base las leería."""
    try:
        src = _crypto.key_source()
    except Exception:  # noqa: BLE001
        src = 'unknown'
    if src == 'default':
        return _err('encryption_key_missing',
                    'configura BROKERAGE_ENC_KEY en Railway antes de conectar cuentas: sin ella las credenciales se '
                    'cifrarían con una clave pública (ver docs/BROKERAGE.md §2.1)',
                    'set BROKERAGE_ENC_KEY in Railway before connecting accounts: without it credentials would be '
                    'encrypted with a public key (see docs/BROKERAGE.md §2.1)')
    return None


def set_credentials(session, client_id, api_key, api_secret, env='paper', actor='ui', verify=True):
    rec, err = _lookup(session, client_id)
    if err:
        return err
    if rec.auth_type == 'env':
        return _err('bad_request', 'la cuenta principal usa ALPACA_KEY/ALPACA_SECRET del servidor',
                    'the main account uses the server ALPACA_KEY/ALPACA_SECRET')
    if env not in ('paper', 'live'):
        return _err('bad_request', "env debe ser 'paper' o 'live'", "env must be 'paper' or 'live'")
    key, sec = _valid_cred(api_key), _valid_cred(api_secret)
    if not key or not sec:
        return _err('bad_request', 'clave y secreto de API requeridos (sin espacios)',
                    'API key and secret required (no spaces)')
    bad = _enc_key_error()
    if bad:
        return bad
    try:
        token = _crypto.encrypt_json({'key': key, 'secret': sec})
    except _crypto.CryptoUnavailable as e:
        return _err('encryption_unavailable', str(e), f'encryption unavailable: {e}')
    prev = (rec.enc_credentials, rec.auth_type, rec.mode, rec.base_url, rec.credentials_hint)
    rec.enc_credentials, rec.auth_type = token, 'keys'
    rec.mode, rec.base_url, rec.credentials_hint = env, _alp.base_for_mode(env), _crypto.mask(key)
    verified, detail, detail_en = None, '', ''
    if verify:
        try:
            acct = make_alpaca(rec).get_account()
            verified = True
            detail = detail_en = f'{acct.get("status") or "OK"}'
            detail, detail_en = f'cuenta {detail}', f'account {detail_en}'
        except _alp.AlpacaError as e:
            if e.status in (401, 403, 404):
                rec.enc_credentials, rec.auth_type, rec.mode, rec.base_url, rec.credentials_hint = prev
                audit(session, actor, 'credentials_rejected', rec.id, detail={'env': env, 'status': e.status})
                return _err('credentials_rejected', f'Alpaca rechazó las claves ({e}). ¿Son de {env}?',
                            f'Alpaca rejected the keys ({e}). Are they {env} keys?', verified=False)
            verified = False
            detail = f'no se pudo verificar ahora ({e}); se guardaron igual'
            detail_en = f'could not verify now ({e}); saved anyway'
    rec.updated_at = _now()
    if prev[0] or prev[2] != env or prev[1] != 'keys':
        _account_changed(session, rec, actor, 'se conectaron credenciales nuevas', 'new credentials were connected',
                         detail={'env': env})
    session.flush()
    audit(session, actor, 'credentials_set', rec.id,
          detail={'env': env, 'hint': rec.credentials_hint, 'verified': verified})
    return {'ok': True, 'verified': verified, 'detail': detail, 'detail_en': detail_en, 'client': client_dict(rec)}


def _read_account(alp):
    a = alp.get_account() or {}
    return {'equity': _f(a.get('equity')), 'cash': _f(a.get('cash')), 'buying_power': _f(a.get('buying_power')),
            # cripto no es marginable en Alpaca: su poder de compra es este
            'non_marginable_buying_power': _f(a.get('non_marginable_buying_power')),
            'multiplier': _f(a.get('multiplier')),
            'portfolio_value': _f(a.get('portfolio_value')), 'last_equity': _f(a.get('last_equity')),
            'currency': a.get('currency') or 'USD', 'status': a.get('status'),
            'trading_blocked': bool(a.get('trading_blocked')), 'account_blocked': bool(a.get('account_blocked')),
            'paper': bool(alp.paper)}


def _read_positions(alp):
    out = []
    for p in alp.get_positions() or []:
        out.append({'symbol': p.get('symbol'), 'qty': _f(p.get('qty')), 'side': p.get('side'),
                    'avg_entry_price': _f(p.get('avg_entry_price')), 'current_price': _f(p.get('current_price')),
                    'market_value': _f(p.get('market_value')), 'cost_basis': _f(p.get('cost_basis')),
                    'unrealized_pl': _f(p.get('unrealized_pl')),
                    'unrealized_plpc': _f(p.get('unrealized_plpc')),   # FRACCIÓN (0.05 = 5 %), como Alpaca
                    'asset_class': p.get('asset_class')})
    return out


def _touch_hwm(rec, equity):
    if equity is None:
        return
    now = _now()
    rec.last_equity, rec.last_snapshot_at = equity, now
    if rec.hwm_equity is None or equity > rec.hwm_equity:
        rec.hwm_equity, rec.hwm_at = equity, now


def _paper_mismatch(alp, rec):
    """¿La URL real del cliente de Alpaca contradice el modo guardado?"""
    return bool(getattr(alp, 'paper', rec.mode != 'live')) != (rec.mode != 'live')


def account_snapshot(session, client_id):
    rec, err = _lookup(session, client_id)
    if err:
        return dict(err, client=None, account={}, positions=[])
    try:
        alp = make_alpaca(rec)
        if _paper_mismatch(alp, rec):
            return _err('mode_mismatch', 'la URL de Alpaca no coincide con el modo del cliente: reconecta la cuenta',
                        "the Alpaca URL does not match the client's mode: reconnect the account",
                        client=client_dict(rec), account={}, positions=[])
        account = _read_account(alp)
        positions = _read_positions(alp)
    except _alp.AlpacaError as e:
        return _err('broker_error', str(e), f'Alpaca error: {e}', client=client_dict(rec), account={}, positions=[])
    _touch_hwm(rec, account.get('equity'))
    session.flush()
    return {'ok': True, 'client': client_dict(rec), 'account': account, 'positions': positions,
            'as_of': _iso(_now()), 'source': 'alpaca_live'}


# ════════════════════════════════════════════════════════════════════════════
# previsualización, confirmación y aprobaciones
# ════════════════════════════════════════════════════════════════════════════
def reference_price(alp, symbol, positions):
    """(precio, fuente) de MERCADO para estimar montos — nunca inventado:
    posición en Alpaca → último trade de Alpaca → Finnhub. (None, None) si no hay dato."""
    sym = symbol.upper()
    for p in positions or []:
        if str(p.get('symbol') or '').upper().replace('/', '') == sym.replace('/', '') and p.get('current_price'):
            return float(p['current_price']), 'alpaca_position'
    try:
        px = _f(alp.latest_price(sym))
        if px and px > 0:
            return px, 'alpaca_trade'
    except Exception:  # noqa: BLE001
        pass
    if '/' not in sym:
        try:
            from core.config import FINNHUB
            if FINNHUB:
                from core.quotes import _fetch_quote_raw
                d, err = _fetch_quote_raw(sym, timeout=5)
                c = _f((d or {}).get('c')) if not err else None
                if c and c > 0:
                    return c, 'finnhub'
        except Exception:  # noqa: BLE001
            pass
    return None, None


def market_clock(alp):
    try:
        c = alp.get_clock() or {}
        if 'is_open' in c:
            return bool(c['is_open']), 'alpaca'
    except Exception:  # noqa: BLE001
        pass
    return _risk.market_open_approx(), 'approx'


def _daily_used(session, client_id, exclude_id=None, now=None):
    """US$ en COMPRAS enviadas hoy (día de mercado de NY). Las ventas no cuentan:
    reducir riesgo nunca consume el límite diario."""
    start = _risk.trading_day_start(now)
    q = (session.query(func.coalesce(func.sum(BrokerOrder.est_usd), 0.0))
         .filter(BrokerOrder.client_id == client_id, BrokerOrder.side == 'buy',
                 BrokerOrder.status.in_(SENT_STATUSES),
                 func.coalesce(BrokerOrder.submitted_at, BrokerOrder.updated_at) >= start))
    if exclude_id:
        q = q.filter(BrokerOrder.id != exclude_id)
    return float(q.scalar() or 0.0)


def daily_used(session, client_id):
    """Público (lo lee el comité): US$ comprados hoy por el cliente."""
    rec = _client_rec(session, client_id)
    return _daily_used(session, rec.id if rec else str(client_id)[:40])


def _recent_duplicate(session, client_id, symbol, side, exclude_id=None, include_pending=False, now=None):
    since = (now or _now()) - timedelta(seconds=_risk.DUPLICATE_WINDOW_S)
    statuses = SENT_STATUSES + (('pending_approval',) if include_pending else ())
    q = (session.query(BrokerOrder.id)
         .filter(BrokerOrder.client_id == client_id, BrokerOrder.symbol == symbol, BrokerOrder.side == side,
                 BrokerOrder.status.in_(statuses),
                 func.coalesce(BrokerOrder.submitted_at, BrokerOrder.updated_at, BrokerOrder.created_at) >= since))
    if exclude_id:
        q = q.filter(BrokerOrder.id != exclude_id)
    return q.first() is not None


def _unresolved(session, client_id, symbol, side, exclude_id=None):
    """¿Hay una orden igual cuyo envío quedó en estado DESCONOCIDO (sin id de Alpaca)?"""
    q = (session.query(BrokerOrder.id)
         .filter(BrokerOrder.client_id == client_id, BrokerOrder.symbol == symbol, BrokerOrder.side == side,
                 BrokerOrder.status.in_(OPEN_STATUSES + ('approved',)), BrokerOrder.alpaca_order_id.is_(None)))
    if exclude_id:
        q = q.filter(BrokerOrder.id != exclude_id)
    return q.first() is not None


def _evaluate(session, rec, spec, exclude_id=None, include_pending=False):
    """Lee la cuenta EN VIVO, estima el monto y corre los controles."""
    alp, account, positions, acct_err = None, None, [], None
    connected = _connected(rec)
    if connected:
        try:
            alp = make_alpaca(rec)
            if _paper_mismatch(alp, rec):
                acct_err = ('la URL de Alpaca no coincide con el modo del cliente (papel/real): reconecta la cuenta')
            else:
                account = _read_account(alp)
                positions = _read_positions(alp)
                _touch_hwm(rec, account.get('equity'))
                if account.get('trading_blocked') or account.get('account_blocked'):
                    acct_err = 'Alpaca tiene la cuenta BLOQUEADA para operar'
        except _alp.AlpacaError as e:
            acct_err = str(e)
    sym, side = spec['symbol'], spec['side']
    ref, rsrc = (None, None)
    if alp is not None and not acct_err:
        ref, rsrc = reference_price(alp, sym, positions)
    price, psrc = ref, rsrc
    lp = spec.get('limit_price') if spec.get('order_type') == 'limit' else None
    if lp:
        # compra límite: se paga como mucho el límite (cota superior honesta).
        # venta límite: se cobra el límite O MÁS — con un límite bajo se vende a
        # mercado, así que el monto se estima con el mayor de los dos.
        if side == 'sell' and ref and ref > lp:
            price, psrc = ref, rsrc
        else:
            price, psrc = float(lp), 'limit'
    if spec.get('notional') is not None:
        est = float(spec['notional'])
    elif price:
        est = float(spec['qty']) * price
    else:
        est = None
    mo, csrc = (market_clock(alp) if alp is not None and '/' not in sym else (None, 'approx'))
    if mo is None and '/' not in sym:
        mo, csrc = _risk.market_open_approx(), 'approx'
    ctx = {
        'client': {'status': rec.status, 'mode': rec.mode, 'live_enabled': rec.live_enabled,
                   'connected': connected, 'risk_profile': rec.risk_profile, 'risk_limits': rec.risk_limits,
                   'mandate': rec.mandate, 'hwm_equity': rec.hwm_equity},
        'order': spec, 'account': account, 'account_error': acct_err, 'positions': positions,
        'price': price, 'ref_price': ref, 'est_usd': est,
        'daily_used_usd': _daily_used(session, rec.id, exclude_id=exclude_id),
        'recent_duplicate': _recent_duplicate(session, rec.id, sym, side, exclude_id=exclude_id,
                                              include_pending=include_pending),
        'unresolved_order': _unresolved(session, rec.id, sym, side, exclude_id=exclude_id),
        'market_open': mo, 'clock_source': csrc,
    }
    return {'checks': _risk.run_checks(ctx), 'price': price, 'est': est, 'psrc': psrc, 'alp': alp,
            'ref': ref, 'rsrc': rsrc}


PRICE_SOURCES = {'alpaca_position': ('precio de la posición en Alpaca', 'Alpaca position price'),
                 'alpaca_trade': ('último trade en Alpaca', 'last Alpaca trade'),
                 'finnhub': ('cotización Finnhub', 'Finnhub quote'),
                 'limit': ('precio límite', 'limit price')}


def _summaries(rec, spec, ev, blocked, requires_approval):
    est_price, est_usd, psrc, checks = ev['price'], ev['est'], ev['psrc'], ev['checks']
    src_es, src_en = PRICE_SOURCES.get(psrc, (psrc or '', psrc or ''))
    live = rec.mode == 'live'
    badge_es = '🔴 DINERO REAL' if live else '🧪 PAPEL (simulado)'
    badge_en = '🔴 REAL MONEY' if live else '🧪 PAPER (simulated)'
    sym, side = spec['symbol'], spec['side']
    crypto = '/' in sym
    verb_es, verb_en = ('COMPRAR', 'BUY') if side == 'buy' else ('VENDER', 'SELL')
    if spec.get('notional') is not None:
        amt_es = amt_en = f'US${float(spec["notional"]):,.2f}'
        extra_es = extra_en = ''
        if est_price:
            extra_es = f' (≈ {float(spec["notional"]) / est_price:,.4g} {"unidades" if crypto else "acciones"} a ~US${est_price:,.2f}, {src_es})'
            extra_en = f' (≈ {float(spec["notional"]) / est_price:,.4g} {"units" if crypto else "shares"} at ~US${est_price:,.2f}, {src_en})'
    else:
        q = float(spec['qty'])
        amt_es = f'{q:g} {"unidades" if crypto else "acciones"}'
        amt_en = f'{q:g} {"units" if crypto else "shares"}'
        extra_es = f' (≈ US${est_usd:,.2f} a ~US${est_price:,.2f}, {src_es})' if est_usd and est_price else ' (monto sin estimar)'
        extra_en = f' (≈ US${est_usd:,.2f} at ~US${est_price:,.2f}, {src_en})' if est_usd and est_price else ' (amount not estimated)'
    if spec.get('order_type') == 'limit':
        lp = float(spec['limit_price'])
        typ_es, typ_en = f'orden límite a US${lp:,.2f}', f'limit order at US${lp:,.2f}'
        ref = ev.get('ref')
        if ref:
            r_es, r_en = PRICE_SOURCES.get(ev.get('rsrc'), ('', ''))
            typ_es += f' (mercado ~US${ref:,.2f}, {r_es})'
            typ_en += f' (market ~US${ref:,.2f}, {r_en})'
        else:
            typ_es += ' (sin precio de mercado de referencia)'
            typ_en += ' (no market reference price)'
    else:
        typ_es, typ_en = 'orden a mercado', 'market order'
    es = f'{badge_es} · {verb_es} {amt_es} de {sym} para «{rec.name}» — {typ_es}{extra_es}.'
    en = f'{badge_en} · {verb_en} {amt_en} of {sym} for "{rec.name}" — {typ_en}{extra_en}.'
    if blocked:
        why = [c for c in _risk.failed(checks)]
        es += ' BLOQUEADA: ' + '; '.join(c['detail'] for c in why) + '.'
        en += ' BLOCKED: ' + '; '.join(c.get('detail_en') or c['detail'] for c in why) + '.'
    elif requires_approval:
        es += ' Requiere aprobación humana en 👥 Clientes → Aprobaciones.'
        en += ' Requires human approval in 👥 Clients → Approvals.'
    return es[:1500], en[:1500]


def _spec(symbol, side, notional, qty, order_type, limit_price):
    """Valida la forma de la orden. Devuelve (spec, None) o (None, (es, en))."""
    sym = str(symbol or '').upper().strip()
    side = str(side or '').lower().strip()
    order_type = str(order_type or 'market').lower().strip()
    if not sym:
        return None, ('símbolo requerido', 'symbol required')
    if len(sym) > MAX_SYMBOL_LEN:
        return None, (f'símbolo demasiado largo (máx. {MAX_SYMBOL_LEN} caracteres)',
                      f'symbol too long (max {MAX_SYMBOL_LEN} characters)')
    if side not in ('buy', 'sell'):
        return None, ("side debe ser 'buy' o 'sell'", "side must be 'buy' or 'sell'")
    if order_type not in ('market', 'limit'):
        return None, ("order_type debe ser 'market' o 'limit'", "order_type must be 'market' or 'limit'")
    if (notional is None or notional == '') == (qty is None or qty == ''):
        return None, ('envía exactamente uno de: notional (monto en USD) o qty (cantidad)',
                      'send exactly one of: notional (USD amount) or qty (quantity)')
    n = _f(notional) if notional not in (None, '') else None
    q = _f(qty) if qty not in (None, '') else None
    if notional not in (None, '') and (n is None or n <= 0):
        return None, ('notional debe ser un número mayor que 0 (monto en USD)',
                      'notional must be a number greater than 0 (USD amount)')
    if qty not in (None, '') and (q is None or q <= 0):
        return None, ('qty debe ser un número mayor que 0', 'qty must be a number greater than 0')
    lp = None
    if order_type == 'limit':
        lp = _f(limit_price)
        if lp is None or lp <= 0:
            return None, ('una orden límite requiere limit_price > 0', 'a limit order requires limit_price > 0')
        if n is not None:
            return None, ('una orden límite se expresa en cantidad (qty), no en monto',
                          'a limit order is expressed as quantity (qty), not amount')
    if n is not None and n > _risk.HARD_MAX_ORDER_USD:
        return None, (f'notional supera el tope absoluto de US${_risk.HARD_MAX_ORDER_USD:,.0f} por orden',
                      f'notional exceeds the absolute cap of US${_risk.HARD_MAX_ORDER_USD:,.0f} per order')
    return {'symbol': sym, 'side': side, 'notional': n, 'qty': q, 'order_type': order_type,
            'limit_price': lp}, None


def order_dict(row, client_name=None):
    exp = _aware(row.expires_at)
    return {
        'id': row.id, 'preview_id': row.id, 'client_id': row.client_id, 'client_name': client_name,
        'symbol': row.symbol, 'side': row.side, 'notional': row.notional, 'qty': row.qty,
        'order_type': row.order_type, 'limit_price': row.limit_price, 'time_in_force': row.time_in_force,
        'est_price': row.est_price, 'est_usd': row.est_usd, 'mode': row.mode, 'paper': row.mode != 'live',
        'status': row.status, 'alpaca_status': row.alpaca_status, 'source': row.source,
        'requires_human_approval': bool(row.requires_approval), 'proposal_id': row.proposal_id,
        'rationale': row.rationale, 'checks': row.checks or [], 'blocked': _risk.is_blocked(row.checks),
        'summary_es': row.summary_es, 'summary_en': row.summary_en,
        'requested_by': row.requested_by, 'approved_by': row.approved_by, 'approved_at': _iso(row.approved_at),
        'alpaca_order_id': row.alpaca_order_id, 'client_order_id': row.client_order_id,
        'filled_qty': row.filled_qty, 'filled_avg_price': row.filled_avg_price,
        'error': row.error, 'error_en': row.error_en or row.error,
        # envío con estado desconocido (la red falló): hay que sincronizar antes de repetir
        'unknown': bool(row.alpaca_status == 'unknown' and not row.alpaca_order_id),
        'created_at': _iso(row.created_at), 'expires_at': _iso(exp), 'submitted_at': _iso(row.submitted_at),
        'updated_at': _iso(row.updated_at),
        'expired': bool(exp and exp < _now() and row.status in ('previewed', 'pending_approval')),
    }


def preview_order(session, client_id, symbol, side, notional=None, qty=None, order_type='market',
                  limit_price=None, source='ui', requested_by='', proposal_id=None, rationale=None):
    if source not in SOURCES:
        return _err('bad_request', f'source inválido (usa: {", ".join(SOURCES)})',
                    f'invalid source (use: {", ".join(SOURCES)})')
    rec, err = _lookup(session, client_id)
    if err:
        return err
    spec, bad = _spec(symbol, side, notional, qty, order_type, limit_price)
    if bad:
        return _err('bad_request', bad[0], bad[1])
    if rec.auth_type == 'env':
        ensure_house_client(session)               # el modo de la casa sigue a ALPACA_BASE
    ev = _evaluate(session, rec, spec, include_pending=source != 'ui')
    checks = ev['checks']
    blocked = _risk.is_blocked(checks)
    requires = source in ('mcp', 'committee') and not (_risk.auto_approve_paper() and rec.mode == 'paper')
    now = _now()
    status = 'rejected' if blocked else ('pending_approval' if requires else 'previewed')
    ttl = approval_ttl_s() if requires else PREVIEW_TTL_S
    s_es, s_en = _summaries(rec, spec, ev, blocked, requires)
    why_es = '; '.join(c['detail'] for c in _risk.failed(checks))
    why_en = '; '.join(c.get('detail_en') or c['detail'] for c in _risk.failed(checks))
    row = BrokerOrder(client_id=rec.id, symbol=spec['symbol'], side=spec['side'], notional=spec['notional'],
                      qty=spec['qty'], order_type=spec['order_type'], limit_price=spec['limit_price'],
                      time_in_force='gtc' if '/' in spec['symbol'] else 'day',
                      est_price=ev['price'], est_usd=ev['est'], mode=rec.mode, status=status, source=source,
                      requires_approval=requires, proposal_id=(str(proposal_id)[:60] if proposal_id else None),
                      rationale=(str(rationale)[:4000] if rationale else None), checks=checks,
                      summary_es=s_es, summary_en=s_en, requested_by=str(requested_by or source)[:120],
                      expires_at=now + timedelta(seconds=ttl), account_fp=account_fingerprint(rec),
                      error=('bloqueada por controles de riesgo' if blocked else None),
                      error_en=('blocked by risk checks' if blocked else None))
    session.add(row)
    session.flush()
    row.client_order_id = row.id
    audit(session, requested_by or source, 'order_previewed', rec.id, row.id,
          detail={'symbol': row.symbol, 'side': row.side, 'notional': row.notional, 'qty': row.qty,
                  'source': source, 'status': status, 'blocked': blocked, 'mode': rec.mode,
                  'failed_checks': [c['name'] for c in _risk.failed(checks)]})
    session.flush()
    d = order_dict(row, rec.name)
    d.update({'ok': True, 'blocked': blocked, 'requires_human_approval': requires})
    if blocked:
        d['error'] = 'bloqueada por controles de riesgo: ' + why_es
        d['error_en'] = 'blocked by risk checks: ' + why_en
    return d


def _apply_alpaca(row, od):
    od = od or {}
    if od.get('id'):
        row.alpaca_order_id = str(od['id'])[:64]
    raw = str(od.get('status') or '').lower()
    if raw:
        row.alpaca_status = raw[:30]
        row.status = _ALPACA_STATUS.get(raw, 'submitted')
    fq, fp = _f(od.get('filled_qty')), _f(od.get('filled_avg_price'))
    if fq is not None:
        row.filled_qty = fq
    if fp is not None:
        row.filled_avg_price = fp
    row.updated_at = _now()


def _mark_committee(session, row, actor):
    """Orden del comité enviada → research.committee.mark_executed (opcional).
    En un SAVEPOINT: un error del comité nunca deshace el registro de la orden
    (que YA está en Alpaca)."""
    if row.source != 'committee' or not row.proposal_id:
        return
    try:
        from research.committee import mark_executed
    except Exception:  # noqa: BLE001 — el comité es opcional
        return
    try:
        with session.begin_nested():
            mark_executed(session, row.proposal_id, order=order_dict(row), actor=actor or 'brokerage')
    except Exception as e:  # noqa: BLE001
        log.info('brokerage: no se marcó el memo %s como ejecutado (%s)', row.proposal_id, type(e).__name__)


def _notify_closed(session, row, actor, reason=''):
    """Propuesta del comité cerrada SIN ejecutarse (rechazada, caducada, bloqueada,
    cancelada, fallida) → research.committee.mark_preview_closed(session, memo_id,
    preview_id=, status=, reason=, actor=) si el comité la define. Opcional, en
    SAVEPOINT, nunca rompe la operación del corretaje."""
    if row.source != 'committee' or not row.proposal_id:
        return
    try:
        from research import committee as _cm
    except Exception:  # noqa: BLE001
        return
    fn = getattr(_cm, 'mark_preview_closed', None)
    if fn is None:
        return
    try:
        with session.begin_nested():
            fn(session, row.proposal_id, preview_id=row.id, status=row.status, reason=str(reason or '')[:300],
               actor=actor or 'brokerage')
    except Exception as e:  # noqa: BLE001
        log.info('brokerage: no se avisó al comité del cierre de %s (%s)', row.id, type(e).__name__)


def _definitive_reject(e):
    """¿Alpaca RESPONDIÓ con un rechazo definitivo (la orden seguro no existe)?
    Red caída, tiempo agotado, 5xx, 408/409 o "client_order_id repetido" NO lo
    son: la orden puede estar en Alpaca."""
    st = getattr(e, 'status', None)
    if getattr(e, 'network', False) or not isinstance(st, int):
        return False
    if st in (408, 409, 425) or st >= 500:
        return False
    if st == 422 and 'client_order_id' in str(e).lower():
        return False
    return 400 <= st < 500


def _committee_memo_ok(session, row):
    """Segundo candado: una orden del comité solo sale si su memo está aprobado
    por un humano. Falla CERRADO: sin memo o sin módulo de comité → no se envía."""
    if not row.proposal_id:
        return False, 'missing'
    try:
        from research.committee import memo_allows_order
    except Exception:  # noqa: BLE001
        return False, 'committee_unavailable'
    try:
        return memo_allows_order(session, row.proposal_id, preview_id=row.id)
    except Exception as e:  # noqa: BLE001
        log.info('brokerage: no se pudo verificar el memo %s (%s)', row.proposal_id, type(e).__name__)
        return False, 'unverifiable'


def _execute(session, row, actor, source):
    """Misma cuenta → controles otra vez → Alpaca con client_order_id = row.id (idempotente)."""
    rec = session.get(BrokerClient, row.client_id)
    if not rec:
        row.status, row.error, row.error_en = 'failed', 'cliente ya no existe', 'client no longer exists'
        return _err('not_found', row.error, row.error_en, status=row.status, order=order_dict(row))
    if rec.auth_type == 'env':
        ensure_house_client(session)               # si cambió ALPACA_BASE, caduca esta misma fila
    if row.status == 'expired':
        return _err('account_changed', row.error or 'la cuenta cambió: vuelve a previsualizar',
                    row.error_en or 'the account changed: preview again', status='expired',
                    order=order_dict(row, rec.name))
    if row.source == 'committee':
        ok_memo, memo_st = _committee_memo_ok(session, row)
        if not ok_memo:
            row.status, row.updated_at = 'rejected', _now()
            row.error = (f'el memo del comité no está aprobado (estado «{memo_st}»): no se envió nada; '
                         'apruébalo en 🏛 Comité y vuelve a intentarlo')
            row.error_en = (f'the committee memo is not approved (status "{memo_st}"): nothing was sent; '
                            'approve it in 🏛 Committee and try again')
            audit(session, actor, 'order_blocked', rec.id, row.id,
                  detail={'source': source, 'reason': 'memo_not_approved', 'memo_status': memo_st,
                          'memo_id': row.proposal_id})
            session.flush()
            return _err('memo_not_approved', row.error, row.error_en, status=row.status,
                        order=order_dict(row, rec.name))
    # ¿la cuenta/modo sigue siendo la de la previsualización? (papel → real = NO se envía)
    if (row.mode and row.mode != rec.mode) or (row.account_fp and row.account_fp != account_fingerprint(rec)):
        row.status, row.updated_at = 'rejected', _now()
        row.error = ('la cuenta o el modo del cliente cambió desde la previsualización (p. ej. papel → dinero real): '
                     'no se envió nada; crea una nueva previsualización')
        row.error_en = ("the client's account or mode changed since the preview (e.g. paper → real money): "
                        'nothing was sent; create a new preview')
        audit(session, actor, 'order_blocked', rec.id, row.id,
              detail={'source': source, 'reason': 'account_changed', 'preview_mode': row.mode, 'client_mode': rec.mode})
        _notify_closed(session, row, actor, row.error)
        session.flush()
        return _err('account_changed', row.error, row.error_en, status=row.status, order=order_dict(row, rec.name))
    spec = {'symbol': row.symbol, 'side': row.side, 'notional': row.notional, 'qty': row.qty,
            'order_type': row.order_type, 'limit_price': row.limit_price}
    ev = _evaluate(session, rec, spec, exclude_id=row.id)
    checks, alp = ev['checks'], ev['alp']
    row.checks = checks
    if ev['est'] is not None:
        row.est_usd, row.est_price = ev['est'], ev['price']
    if _risk.is_blocked(checks):
        why = '; '.join(c['detail'] for c in _risk.failed(checks))
        why_en = '; '.join(c.get('detail_en') or c['detail'] for c in _risk.failed(checks))
        row.status, row.updated_at = 'rejected', _now()
        row.error, row.error_en = f'bloqueada al confirmar: {why}'[:1000], f'blocked on confirm: {why_en}'[:1000]
        audit(session, actor, 'order_blocked', rec.id, row.id,
              detail={'source': source, 'failed_checks': [c['name'] for c in _risk.failed(checks)]})
        _notify_closed(session, row, actor, row.error)
        session.flush()
        return _err('blocked', row.error, row.error_en, status=row.status, checks=checks,
                    order=order_dict(row, rec.name))
    row.status, row.updated_at = 'approved', _now()
    if not row.approved_by:
        row.approved_by, row.approved_at = str(actor or source)[:120], _now()
    session.flush()
    od, err = None, None
    try:
        od = alp.submit_order(row.symbol, row.side, notional=row.notional, qty=row.qty,
                              order_type=row.order_type, limit_price=row.limit_price,
                              time_in_force=row.time_in_force, client_order_id=row.id)
    except _alp.AlpacaError as e:
        err = e
        # ¿Llegó igual? (tiempo agotado, o reintento tras una caída: Alpaca
        # rechaza un client_order_id repetido) → se adopta la orden existente.
        try:
            found = alp.get_order_by_client_id(row.id)
            if isinstance(found, dict) and found.get('id'):
                od, err = found, None
        except _alp.AlpacaError:
            pass
    if err is not None and _definitive_reject(err):
        row.status, row.updated_at = 'failed', _now()
        row.error, row.error_en = f'Alpaca rechazó la orden: {err}'[:1000], f'Alpaca rejected the order: {err}'[:1000]
        audit(session, actor, 'order_failed', rec.id, row.id,
              detail={'error': str(err)[:300], 'status': getattr(err, 'status', None), 'source': source})
        _notify_closed(session, row, actor, row.error)
        session.flush()
        return _err('broker_rejected', row.error, row.error_en, status=row.status, order=order_dict(row, rec.name))
    if err is not None:
        # AMBIGUO: no sabemos si Alpaca la tiene. NUNCA 'failed' (un reintento
        # crearía una segunda orden real): queda 'submitted' + 'unknown', cuenta
        # para duplicados y límite diario, y sync_orders la reconcilia.
        row.status, row.alpaca_status, row.updated_at = 'submitted', 'unknown', _now()
        row.submitted_at = row.submitted_at or _now()
        row.error = (f'estado DESCONOCIDO: falló la conexión con Alpaca al enviar ({err}) y puede haberse ejecutado. '
                     'Pulsa ⇅ Sincronizar en Órdenes — NO la repitas.')[:1000]
        row.error_en = (f'UNKNOWN state: the connection to Alpaca failed while sending ({err}) and it may have '
                        'executed. Press ⇅ Sync in Orders — do NOT repeat it.')[:1000]
        audit(session, actor, 'order_unknown', rec.id, row.id,
              detail={'error': str(err)[:300], 'status': getattr(err, 'status', None), 'source': source,
                      'mode': rec.mode, 'symbol': row.symbol, 'side': row.side})
        session.flush()
        return _err('unknown_state', row.error, row.error_en, status=row.status, order=order_dict(row, rec.name))
    _apply_alpaca(row, od)
    if row.status == 'approved':
        row.status = 'submitted'
    row.submitted_at, row.error, row.error_en = _now(), None, None
    audit(session, actor, 'order_submitted', rec.id, row.id,
          detail={'alpaca_order_id': row.alpaca_order_id, 'status': row.status, 'mode': rec.mode,
                  'symbol': row.symbol, 'side': row.side, 'notional': row.notional, 'qty': row.qty,
                  'source': row.source})
    _mark_committee(session, row, actor)
    session.flush()
    return {'ok': True, 'status': row.status, 'order': order_dict(row, rec.name)}


def _lock(session, preview_id):
    return (session.query(BrokerOrder).filter(BrokerOrder.id == str(preview_id or '')[:40])
            .with_for_update().first())


def _expired(row):
    exp = _aware(row.expires_at)
    return bool(exp and exp < _now())


def _expire_row(session, row, actor, action, es, en):
    row.status, row.updated_at = 'expired', _now()
    row.error, row.error_en = es, en
    audit(session, actor, action, row.client_id, row.id)
    _notify_closed(session, row, actor, es)
    session.flush()
    return _err('expired', es, en, status='expired', order=order_dict(row))


def _needs_human(session, row, actor, source, reason):
    audit(session, actor or source, 'confirm_denied', row.client_id, row.id,
          detail={'source': source, 'reason': reason})
    session.flush()
    return _err('requires_human_approval', 'requires human approval',
                'requires human approval', status='pending_approval', order=order_dict(row))


def confirm_order(session, preview_id, approved_by, source='ui'):
    row = _lock(session, preview_id)
    if not row:
        return _err('not_found', 'previsualización no encontrada', 'preview not found')
    who = approved_by or source
    if source != 'ui' and row.source != source:
        # un agente/comité solo puede confirmar SUS propias previsualizaciones
        audit(session, who, 'confirm_denied', row.client_id, row.id,
              detail={'source': source, 'reason': f'origen distinto ({row.source})'})
        return _err('source_mismatch',
                    f'esta previsualización se creó desde «{row.source}»: solo ese origen o una persona en la app '
                    'puede confirmarla',
                    f'this preview was created from "{row.source}": only that origin or a person in the app can '
                    'confirm it', status=row.status, order=order_dict(row))
    if row.status in ('submitted', 'filled', 'partially_filled', 'canceled', 'failed'):
        return _err('used', f'esta previsualización ya se usó (estado «{row.status}»)',
                    f'this preview was already used (status "{row.status}")', status=row.status,
                    order=order_dict(row))
    if row.status in ('rejected', 'expired'):
        return _err(row.status, f'la previsualización está «{row.status}»: crea una nueva',
                    f'the preview is "{row.status}": create a new one', status=row.status, order=order_dict(row))
    if row.status == 'pending_approval':
        if source != 'ui':
            return _needs_human(session, row, approved_by, source, 'requires human approval')
        if _expired(row):
            return _expire_row(session, row, who, 'approval_expired', 'la propuesta caducó sin aprobación',
                               'the proposal expired without approval')
        row.approved_by, row.approved_at = str(approved_by or 'ui')[:120], _now()
        audit(session, approved_by or 'ui', 'order_approved', row.client_id, row.id, detail={'via': 'confirm'})
        return _execute(session, row, who, source)
    if row.status == 'previewed' and _expired(row):
        return _expire_row(session, row, who, 'preview_expired', 'la previsualización caducó (5 min): crea una nueva',
                           'the preview expired (5 min): create a new one')
    if source != 'ui' and row.status == 'previewed':
        if row.requires_approval:
            return _needs_human(session, row, approved_by, source, 'requires human approval')
        # auto-aprobada en papel AL PREVISUALIZAR: se vuelve a comprobar AHORA
        # (el interruptor pudo apagarse, o la cuenta pasar a dinero real)
        rec = session.get(BrokerClient, row.client_id)
        if rec is not None and rec.auth_type == 'env':
            ensure_house_client(session)
        same = (rec is not None and row.mode == rec.mode
                and (not row.account_fp or row.account_fp == account_fingerprint(rec)))
        if not same:
            return _execute(session, row, who, source)          # la rechaza con 'account_changed'
        if not (_risk.auto_approve_paper() and rec.mode == 'paper' and row.mode == 'paper'):
            row.status, row.requires_approval, row.updated_at = 'pending_approval', True, _now()
            row.expires_at = _now() + timedelta(seconds=approval_ttl_s())
            audit(session, who, 'approval_required', row.client_id, row.id,
                  detail={'source': source, 'reason': 'auto_approve_paper no longer applies', 'mode': rec.mode})
            return _needs_human(session, row, approved_by, source, 'auto-approval no longer applies')
    return _execute(session, row, who, source)


def approve_preview(session, preview_id, approved_by):
    """Aprobación HUMANA (la ruta exige PIN) de una propuesta de MCP/comité."""
    if not str(approved_by or '').strip():
        return _err('bad_request', 'approved_by (quién aprueba) es obligatorio', 'approved_by (who approves) is required')
    row = _lock(session, preview_id)
    if not row:
        return _err('not_found', 'propuesta no encontrada', 'proposal not found')
    if row.status != 'pending_approval':
        return _err('bad_status', f'la propuesta ya está «{row.status}»', f'the proposal is already "{row.status}"',
                    status=row.status, order=order_dict(row))
    if _expired(row):
        return _expire_row(session, row, approved_by, 'approval_expired', 'la propuesta caducó sin aprobación',
                           'the proposal expired without approval')
    row.approved_by, row.approved_at = str(approved_by)[:120], _now()
    audit(session, approved_by, 'order_approved', row.client_id, row.id, detail={'source': row.source})
    session.flush()
    return _execute(session, row, approved_by, 'ui')


def reject_preview(session, preview_id, actor, reason=''):
    row = _lock(session, preview_id)
    if not row:
        return _err('not_found', 'propuesta no encontrada', 'proposal not found')
    if row.status not in ('previewed', 'pending_approval'):
        return _err('bad_status', f'la propuesta ya está «{row.status}»', f'the proposal is already "{row.status}"',
                    status=row.status, order=order_dict(row))
    who = str(actor or 'humano')
    row.status, row.updated_at = 'rejected', _now()
    row.error = ('rechazada por ' + who + (f': {reason}' if reason else ''))[:1000]
    row.error_en = ('rejected by ' + who + (f': {reason}' if reason else ''))[:1000]
    audit(session, actor or 'ui', 'order_rejected', row.client_id, row.id, detail={'reason': str(reason or '')[:300]})
    _notify_closed(session, row, actor or 'ui', row.error)
    session.flush()
    return {'ok': True, 'status': 'rejected', 'order': order_dict(row)}


def _names(session, ids):
    ids = list({i for i in ids if i})
    if not ids:
        return {}
    return {r.id: r.name for r in session.query(BrokerClient.id, BrokerClient.name).filter(BrokerClient.id.in_(ids))}


def pending_approvals(session):
    rows = (session.query(BrokerOrder).filter(BrokerOrder.status == 'pending_approval')
            .order_by(BrokerOrder.created_at.asc()).all())
    out, now = [], _now()
    for r in rows:
        exp = _aware(r.expires_at)
        if exp and exp < now:
            r.status, r.updated_at = 'expired', now
            r.error, r.error_en = 'la propuesta caducó sin aprobación', 'the proposal expired without approval'
            audit(session, 'sistema', 'approval_expired', r.client_id, r.id)
            _notify_closed(session, r, 'sistema', r.error)
            continue
        out.append(r)
    session.flush()
    names = _names(session, [r.client_id for r in out])
    return [order_dict(r, names.get(r.client_id)) for r in out]


def list_orders(session, client_id=None, status=None, limit=50):
    q = session.query(BrokerOrder)
    if client_id:
        rec = _client_rec(session, client_id)
        q = q.filter(BrokerOrder.client_id == (rec.id if rec else str(client_id)[:40]))
    if status:
        sts = [s.strip() for s in str(status).split(',') if s.strip()]
        q = q.filter(BrokerOrder.status.in_(sts))
    rows = q.order_by(BrokerOrder.created_at.desc()).limit(max(1, min(int(limit or 50), 500))).all()
    names = _names(session, [r.client_id for r in rows])
    return [order_dict(r, names.get(r.client_id)) for r in rows]


def get_order(session, order_id):
    r = session.get(BrokerOrder, str(order_id or '')[:40])
    if not r:
        return None
    return order_dict(r, _names(session, [r.client_id]).get(r.client_id))


def _age_s(row, now=None):
    ref = _aware(row.submitted_at or row.updated_at or row.created_at)
    return ((now or _now()) - ref).total_seconds() if ref else 1e9


def _reconcile_unknown(session, row, alp, actor):
    """Orden sin id de Alpaca (envío con estado desconocido): la busca por
    client_order_id. → 'adopted' | 'not_found' (tras la gracia → 'failed') |
    'pending' (aún muy reciente) | lanza AlpacaError (red caída otra vez)."""
    try:
        od = alp.get_order_by_client_id(row.id)
    except _alp.AlpacaError as e:
        if e.status != 404:
            raise
        if _age_s(row) < UNKNOWN_GRACE_S:
            return 'pending'
        row.status, row.alpaca_status, row.updated_at = 'failed', None, _now()
        row.error = 'Alpaca no tiene esta orden: nunca llegó (se puede volver a previsualizar)'
        row.error_en = 'Alpaca does not have this order: it never arrived (you can preview it again)'
        audit(session, actor, 'order_reconciled', row.client_id, row.id, detail={'result': 'not_found'})
        _notify_closed(session, row, actor, row.error)
        return 'not_found'
    if not (isinstance(od, dict) and od.get('id')):
        return 'pending'
    _apply_alpaca(row, od)
    if row.status == 'approved':
        row.status = 'submitted'
    row.error = row.error_en = None
    row.submitted_at = row.submitted_at or _now()
    audit(session, actor, 'order_reconciled', row.client_id, row.id,
          detail={'result': 'adopted', 'alpaca_order_id': row.alpaca_order_id, 'status': row.status})
    if row.status in SENT_STATUSES:
        _mark_committee(session, row, actor)
    return 'adopted'


def cancel_order(session, order_id, actor):
    row = _lock(session, order_id)
    if not row:
        return _err('not_found', 'orden no encontrada', 'order not found')
    if row.status in ('previewed', 'pending_approval'):
        row.status, row.updated_at = 'canceled', _now()
        audit(session, actor, 'order_canceled', row.client_id, row.id, detail={'stage': 'before_submit'})
        _notify_closed(session, row, actor, 'cancelada antes de enviarse')
        session.flush()
        return {'ok': True, 'status': row.status, 'order': order_dict(row)}
    rec = session.get(BrokerClient, row.client_id)
    if row.status in OPEN_STATUSES + ('approved',) and not row.alpaca_order_id:
        # estado desconocido: primero averiguar si Alpaca la tiene
        try:
            res = _reconcile_unknown(session, row, make_alpaca(rec), actor)
        except _alp.AlpacaError as e:
            session.flush()
            return _err('unknown_state', f'estado desconocido y Alpaca no responde ({e}): inténtalo en un momento',
                        f'unknown state and Alpaca is not responding ({e}): try again shortly',
                        status=row.status, order=order_dict(row))
        session.flush()
        if res != 'adopted':
            if res == 'not_found':
                return {'ok': True, 'status': row.status, 'order': order_dict(row)}
            return _err('unknown_state', 'aún no se sabe si Alpaca recibió la orden: sincroniza en 2 minutos',
                        'it is not yet known whether Alpaca received the order: sync in 2 minutes',
                        status=row.status, order=order_dict(row))
    if row.status not in OPEN_STATUSES or not row.alpaca_order_id:
        return _err('bad_status', f'no se puede cancelar una orden «{row.status}»',
                    f'an order in status "{row.status}" cannot be canceled', status=row.status,
                    order=order_dict(row))
    try:
        alp = make_alpaca(rec)
        alp.cancel_order(row.alpaca_order_id)
        try:
            _apply_alpaca(row, alp.get_order(row.alpaca_order_id))
        except _alp.AlpacaError:
            row.alpaca_status = 'pending_cancel'
    except _alp.AlpacaError as e:
        audit(session, actor, 'cancel_failed', row.client_id, row.id, detail={'error': str(e)[:300]})
        session.flush()
        return _err('broker_error', str(e), f'Alpaca error: {e}', status=row.status, order=order_dict(row))
    audit(session, actor, 'order_canceled', row.client_id, row.id,
          detail={'alpaca_order_id': row.alpaca_order_id, 'alpaca_status': row.alpaca_status})
    session.flush()
    return {'ok': True, 'status': row.status, 'order': order_dict(row)}


def sync_orders(session, client_id=None, actor='sistema'):
    """Actualiza desde Alpaca el estado de las órdenes abiertas, y reconcilia por
    client_order_id las que quedaron con estado desconocido (sin id de Alpaca)."""
    q = session.query(BrokerOrder).filter(BrokerOrder.status.in_(OPEN_STATUSES + ('approved',)))
    if client_id:
        rec, err = _lookup(session, client_id)
        if err:
            return dict(err, checked=0, updated=0, errors=[])
        q = q.filter(BrokerOrder.client_id == rec.id)
    rows = q.all()
    by_client, checked, updated, errors = {}, 0, 0, []
    for r in rows:
        by_client.setdefault(r.client_id, []).append(r)
    for cid, items in by_client.items():
        rec = session.get(BrokerClient, cid)
        try:
            alp = make_alpaca(rec)
        except _alp.AlpacaError as e:
            errors.append({'client_id': cid, 'error': str(e), 'error_en': f'Alpaca error: {e}'})
            continue
        for r in items:
            checked += 1
            before = (r.status, r.filled_qty, r.alpaca_order_id)
            try:
                if r.alpaca_order_id:
                    _apply_alpaca(r, alp.get_order(r.alpaca_order_id))
                else:
                    _reconcile_unknown(session, r, alp, actor)
            except _alp.AlpacaError as e:
                errors.append({'order_id': r.id, 'error': str(e), 'error_en': f'Alpaca error: {e}'})
                continue
            if (r.status, r.filled_qty, r.alpaca_order_id) != before:
                updated += 1
                audit(session, actor, 'order_synced', cid, r.id,
                      detail={'from': before[0], 'to': r.status, 'filled_qty': r.filled_qty})
    session.flush()
    out = {'ok': not errors, 'checked': checked, 'updated': updated, 'errors': errors}
    if errors:
        out['error'] = f'{len(errors)} error(es) al sincronizar: {errors[0]["error"]}'
        out['error_en'] = f'{len(errors)} error(s) while syncing: {errors[0]["error_en"]}'
    return out


# ════════════════════════════════════════════════════════════════════════════
# OAuth (Alpaca Connect)
# ════════════════════════════════════════════════════════════════════════════
def oauth_start(session, client_id, env='paper', actor='ui'):
    cfg = _alp.oauth_config()
    if not cfg['configured']:
        return _err('oauth_not_configured', 'OAuth no configurado: faltan ALPACA_OAUTH_CLIENT_ID, '
                                            'ALPACA_OAUTH_CLIENT_SECRET y ALPACA_OAUTH_REDIRECT_URI',
                    'OAuth not configured: ALPACA_OAUTH_CLIENT_ID, ALPACA_OAUTH_CLIENT_SECRET and '
                    'ALPACA_OAUTH_REDIRECT_URI are missing')
    rec, err = _lookup(session, client_id)
    if err:
        return err
    if rec.auth_type == 'env':
        return _err('bad_request', 'la cuenta principal usa las claves del servidor',
                    'the main account uses the server keys')
    if env not in ('paper', 'live'):
        return _err('bad_request', "env debe ser 'paper' o 'live'", "env must be 'paper' or 'live'")
    bad = _enc_key_error()
    if bad:
        return bad
    raw = secrets.token_urlsafe(24)
    state = f'{raw}.{_crypto.sign(f"{raw}|{rec.id}|{env}")}'
    session.add(BrokerOAuthState(state=state, client_id=rec.id, env=env, created_by=str(actor)[:120]))
    audit(session, actor, 'oauth_started', rec.id, detail={'env': env})
    session.flush()
    return {'ok': True, 'url': _alp.oauth_authorize_url(state, env), 'env': env,
            'expires_in_s': OAUTH_STATE_TTL_S}


def oauth_callback(session, state, code, error=None):
    """Valida el `state` (firmado, de un solo uso, < 15 min), canjea el código
    y guarda el token CIFRADO. Devuelve {ok, client_id, client_name, env, error, error_en}."""
    state = str(state or '')[:120]
    if '.' not in state:
        return _err('bad_state', 'enlace de autorización inválido (state)', 'invalid authorization link (state)')
    st = (session.query(BrokerOAuthState).filter(BrokerOAuthState.state == state).with_for_update().first())
    raw, sig = state.rsplit('.', 1)
    if not st or not _crypto.verify(f'{raw}|{st.client_id}|{st.env}', sig):
        return _err('bad_state', 'enlace de autorización inválido o manipulado (state)',
                    'invalid or tampered authorization link (state)')
    if st.used:
        return _err('state_used', 'este enlace de autorización ya se usó: inicia la conexión otra vez',
                    'this authorization link was already used: start the connection again')
    st.used = True                      # un solo uso, aunque el canje falle
    session.flush()
    created = _aware(st.created_at) or _now()
    if (_now() - created).total_seconds() > OAUTH_STATE_TTL_S:
        audit(session, 'alpaca-oauth', 'oauth_failed', st.client_id, detail={'reason': 'state caducado'})
        return _err('state_expired', 'el enlace caducó (15 min): inicia la conexión otra vez',
                    'the link expired (15 min): start the connection again')
    if error:
        audit(session, 'alpaca-oauth', 'oauth_denied', st.client_id, detail={'error': str(error)[:120]})
        return _err('oauth_denied', f'Alpaca no autorizó la conexión ({str(error)[:80]})',
                    f'Alpaca did not authorize the connection ({str(error)[:80]})')
    if not code:
        return _err('bad_request', 'falta el código de autorización', 'the authorization code is missing')
    rec = session.get(BrokerClient, st.client_id)
    if not rec:
        return _not_found()
    bad = _enc_key_error()
    if bad:
        audit(session, 'alpaca-oauth', 'oauth_failed', rec.id, detail={'reason': 'encryption_key_missing'})
        return dict(bad, client_id=rec.id)
    try:
        tok = _alp.oauth_exchange(code)
        enc = _crypto.encrypt_json({'token': tok['access_token'], 'scope': tok.get('scope') or ''})
    except (_alp.AlpacaError, _crypto.CryptoUnavailable) as e:
        audit(session, 'alpaca-oauth', 'oauth_failed', rec.id, detail={'error': str(e)[:300]})
        return _err('oauth_failed', str(e), f'OAuth failed: {e}', client_id=rec.id)
    had_creds, prev_mode, prev_auth = bool(rec.enc_credentials), rec.mode, rec.auth_type
    rec.enc_credentials, rec.auth_type = enc, 'oauth'
    rec.mode, rec.base_url = st.env, _alp.base_for_mode(st.env)
    rec.credentials_hint = 'OAuth ' + _crypto.mask(tok['access_token'])
    rec.updated_at = _now()
    if had_creds or prev_mode != st.env or prev_auth != 'oauth':
        _account_changed(session, rec, st.created_by or 'alpaca-oauth', 'se conectó una cuenta por OAuth',
                         'an account was connected via OAuth', detail={'env': st.env})
    audit(session, st.created_by or 'alpaca-oauth', 'oauth_connected', rec.id,
          detail={'env': st.env, 'scope': tok.get('scope') or ''})
    session.flush()
    return {'ok': True, 'client_id': rec.id, 'client_name': rec.name, 'env': st.env}


# ════════════════════════════════════════════════════════════════════════════
# estado (sin secretos)
# ════════════════════════════════════════════════════════════════════════════
def public_status():
    """Lo único que se muestra SIN PIN."""
    return {'available': available(), 'trading_enabled': _risk.trading_enabled()}


def status_info():
    """Detalle de configuración (va detrás del PIN: revela la postura de seguridad)."""
    try:
        key_src = _crypto.key_source()
        crypto_ok = _crypto.crypto_available()
    except Exception:  # noqa: BLE001
        key_src, crypto_ok = 'unknown', False
    return {
        'available': available(),
        'trading_enabled': _risk.trading_enabled(),
        'live_enabled_env': _risk.live_env_enabled(),
        'auto_approve_paper': _risk.auto_approve_paper(),
        'oauth_configured': _alp.oauth_config()['configured'],
        'house_env_configured': _alp.house_env() is not None,
        'pin_set': bool(os.getenv('TRADE_PIN', '')),
        'encryption': {'available': crypto_ok, 'key_source': key_src,
                       'can_store_credentials': crypto_ok and key_src != 'default'},
        'approval_ttl_min': approval_ttl_s() // 60,
        'preview_ttl_s': PREVIEW_TTL_S,
        'profiles': _risk.PROFILES,
    }


__all__ = [
    'available', 'list_clients', 'get_client', 'account_snapshot', 'preview_order', 'confirm_order',
    'approve_preview', 'reject_preview', 'pending_approvals', 'list_orders', 'cancel_order', 'sync_orders',
    'create_client', 'update_client', 'pause_client', 'resume_client', 'set_credentials', 'oauth_start',
    'oauth_callback', 'status_info', 'public_status', 'list_audit', 'get_order', 'ensure_house_client',
    'make_alpaca', 'daily_used', 'account_fingerprint',
]
