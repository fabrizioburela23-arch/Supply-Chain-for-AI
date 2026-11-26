"""core/connectors.py — 🧩 CONECTORES: Khipus usa tus apps (Gmail, Sheets, Slack, Notion, Calendar…) por UNA sola puerta,
Composio (2026-11-26, pedido de Fabrizio: «algo que se conecte a todo, sin un MCP por cada cosa»).

Cómo funciona:
  · Una clave del servidor (COMPOSIO_API_KEY en Railway). Cada persona conecta SUS apps con el inicio de sesión oficial
    de cada app (OAuth gestionado por Composio): Khipus nunca ve contraseñas. Persona = huella de su navegador
    (X-Khipu-Owner → `user_id` «kh_<huella>»), así lo de uno nunca se mezcla con lo de otro.
  · El chat tiene dos herramientas: `apps_search` (qué acciones hay) y `apps_run` (usar una).
      - LEER (buscar correos, leer una hoja, ver la agenda) = directo.
      - ESCRIBIR (enviar, crear, borrar, publicar…) = NUNCA directo: queda PENDIENTE y la persona confirma con un clic +
        PIN (engine/connectors.js → POST /api/connectors/confirm). Así un correo con instrucciones escondidas no puede
        hacer que Khipus mande nada por su cuenta.
  · Lo que llega de una app es DATO EXTERNO, nunca instrucciones (se marca así para la IA).
  · Dinero: ninguna acción de Composio toca órdenes; eso sigue siendo solo brokerage.service.
API REST v3.1 de Composio: /tools (buscar), /tools/execute/{slug}, /auth_configs, /connected_accounts(/link), /toolkits.
"""
import hashlib
import json
import logging
import os
import re
import threading
import time
import uuid

log = logging.getLogger('khipu')

DEFAULT_BASE = 'https://backend.composio.dev/api/v3.1'
TIMEOUT_S = 15
MAX_RESULT_CHARS = 6000
PENDING_TTL_S = 15 * 60
# apps sugeridas en la ventana 🧩 (cualquier otra se puede buscar)
SUGGESTED = ('gmail', 'googlecalendar', 'googlesheets', 'googledrive', 'slack', 'notion', 'outlook', 'whatsapp')

_READ_RX = re.compile(r'(^|_)(GET|LIST|SEARCH|FETCH|FIND|READ|RETRIEVE|QUERY|DESCRIBE|VIEW|LOOKUP|COUNT)(_|$)')
_WRITE_RX = re.compile(r'(^|_)(SEND|CREATE|DELETE|REMOVE|UPDATE|POST|REPLY|ADD|MOVE|INSERT|PATCH|SHARE|INVITE|UPLOAD|'
                       r'WRITE|ARCHIVE|TRASH|MODIFY|SET|EXECUTE|RUN|DRAFT|FORWARD|APPEND|CLEAR|BATCH|PUT|MERGE|'
                       r'TRANSFER|PAY|ACCEPT|DECLINE|CANCEL|STAR|LABEL|MARK|RENAME|COPY|PUBLISH|SCHEDULE|EDIT)(_|$)')
_SLUG_RX = re.compile(r'^[A-Z0-9_]{3,120}$')
_APP_RX = re.compile(r'^[a-z0-9_-]{2,60}$')

_PENDING = {}          # id → {owner, tool, app, arguments, summary, at}
_AUTH_CFG = {}         # toolkit → auth_config_id (caché)
_LOCK = threading.Lock()


def api_key():
    return (os.getenv('COMPOSIO_API_KEY') or os.getenv('COMPOSIO_KEY') or '').strip()


def enabled():
    return bool(api_key()) and (os.getenv('COMPOSIO_ENABLED') or 'on').strip().lower() not in ('off', '0', 'false', 'no')


def base():
    return (os.getenv('COMPOSIO_BASE') or DEFAULT_BASE).rstrip('/')


def user_id(owner_key_or_hash):
    """La persona en Composio: huella estable y opaca de la llave del navegador (nunca la llave)."""
    s = str(owner_key_or_hash or '').strip()
    if len(s) < 16:
        return None
    return 'kh_' + hashlib.sha256(('khipu-apps|' + s[:200]).encode('utf-8')).hexdigest()[:32]


class ConnectorError(Exception):
    def __init__(self, msg, code='connector_error', status=502):
        super().__init__(msg)
        self.code, self.status = code, status


def _req(method, path, params=None, body=None, http=None):
    if not enabled():
        raise ConnectorError('Composio no está configurado (falta COMPOSIO_API_KEY)', 'not_configured', 503)
    import requests
    h = http or requests
    try:
        r = h.request(method, base() + path, params=params, json=body, timeout=TIMEOUT_S,
                      headers={'x-api-key': api_key(), 'accept': 'application/json'})
    except Exception as e:  # noqa: BLE001
        raise ConnectorError(f'Composio no respondió ({type(e).__name__})', 'unreachable', 502)
    try:
        data = r.json()
    except Exception:  # noqa: BLE001
        data = {}
    if r.status_code >= 400:
        err = (data or {}).get('error') if isinstance(data, dict) else None
        msg = (err.get('message') if isinstance(err, dict) else err) or f'HTTP {r.status_code}'
        raise ConnectorError(f'Composio: {str(msg)[:200]}', 'upstream', 502 if r.status_code >= 500 else 400)
    return data


def is_write(slug, description=''):
    """¿La acción CAMBIA algo fuera de Khipus? Ante la duda, sí (pedir confirmación nunca hace daño)."""
    s = str(slug or '').upper()
    if _WRITE_RX.search(s):
        return True
    return not _READ_RX.search(s)


def _clip(v, n):
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n] + '…'


def _params_summary(schema):
    props = (schema or {}).get('properties') or {}
    req = set((schema or {}).get('required') or [])
    out = []
    for k, v in list(props.items())[:14]:
        t = (v or {}).get('type') or 'any'
        out.append(f"{k}{'' if k in req else '?'}:{t}")
    return ', '.join(out)


def search_tools(query, app=None, limit=6, http=None):
    params = {'query': str(query or '')[:200], 'limit': max(1, min(10, int(limit or 6))), 'toolkit_versions': 'latest'}
    if app and _APP_RX.match(str(app).lower()):
        params['toolkit_slug'] = str(app).lower()
    data = _req('GET', '/tools', params=params, http=http)
    out = []
    for it in (data.get('items') or [])[:params['limit']]:
        slug = str(it.get('slug') or '')
        if not _SLUG_RX.match(slug):
            continue
        out.append({'tool': slug, 'app': ((it.get('toolkit') or {}).get('slug') or ''),
                    'what': _clip(it.get('human_description') or it.get('description') or it.get('name') or '', 220),
                    'params': _params_summary(it.get('input_parameters')),
                    'changes_something': is_write(slug, it.get('description'))})
    return out


def connections(uid, http=None):
    """{app: status} de las apps que esta persona conectó."""
    if not uid:
        return {}
    data = _req('GET', '/connected_accounts', params={'user_ids': [uid], 'limit': 50}, http=http)
    out = {}
    for it in data.get('items') or []:
        app = ((it.get('toolkit') or {}).get('slug') or '').lower()
        st = str(it.get('status') or '').upper()
        if app and (st == 'ACTIVE' or app not in out):
            out[app] = st
    return out


def _auth_config(app, http=None):
    with _LOCK:
        if app in _AUTH_CFG:
            return _AUTH_CFG[app]
    data = _req('GET', '/auth_configs', params={'toolkit_slug': app, 'limit': 5}, http=http)
    items = data.get('items') or []
    cid = next((i.get('id') for i in items if i.get('id')), None)
    if not cid:
        made = _req('POST', '/auth_configs', body={'toolkit': {'slug': app},
                                                   'auth_config': {'type': 'use_composio_managed_auth'}}, http=http)
        cid = ((made or {}).get('auth_config') or {}).get('id')
    if not cid:
        raise ConnectorError(f'{app}: no se pudo preparar el inicio de sesión', 'no_auth_config', 502)
    with _LOCK:
        _AUTH_CFG[app] = cid
    return cid


def connect_link(uid, app, callback_url=None, http=None):
    app = str(app or '').lower()
    if not uid or not _APP_RX.match(app):
        raise ConnectorError('app inválida', 'bad_request', 400)
    body = {'auth_config_id': _auth_config(app, http=http), 'user_id': uid}
    if callback_url and str(callback_url).startswith(('https://', 'http://localhost')):
        body['callback_url'] = str(callback_url)[:500]
    data = _req('POST', '/connected_accounts/link', body=body, http=http)
    url = data.get('redirect_url')
    if not (isinstance(url, str) and url.startswith('https://')):
        raise ConnectorError('Composio no devolvió el enlace de inicio de sesión', 'upstream', 502)
    return {'app': app, 'redirect_url': url, 'expires_at': data.get('expires_at')}


def execute(uid, slug, arguments, http=None):
    if not uid or not _SLUG_RX.match(str(slug or '')):
        raise ConnectorError('acción inválida', 'bad_request', 400)
    data = _req('POST', f'/tools/execute/{slug}', body={'user_id': uid, 'arguments': arguments or {}}, http=http)
    ok = bool(data.get('successful'))
    return {'ok': ok, 'data': _clip(data.get('data'), MAX_RESULT_CHARS) if ok else None,
            'error': None if ok else _clip(data.get('error') or 'falló', 300)}


# ── acciones que ESCRIBEN: pendientes hasta que la persona confirma ─────────────
def _gc():
    now = time.time()
    for k in [k for k, v in _PENDING.items() if now - v['at'] > PENDING_TTL_S]:
        _PENDING.pop(k, None)


def propose(uid, slug, app, arguments, summary):
    with _LOCK:
        _gc()
        mine = [k for k, v in _PENDING.items() if v['owner'] == uid]
        for k in mine[:-4]:                   # máximo 5 pendientes por persona
            _PENDING.pop(k, None)
        pid = uuid.uuid4().hex[:16]
        _PENDING[pid] = {'owner': uid, 'tool': slug, 'app': app, 'arguments': arguments or {},
                         'summary': _clip(summary or slug, 300), 'at': time.time()}
    return pid


def pending(uid):
    with _LOCK:
        _gc()
        return [{'id': k, 'tool': v['tool'], 'app': v['app'], 'summary': v['summary'],
                 'arguments': _clip(v['arguments'], 1200), 'at': v['at']}
                for k, v in _PENDING.items() if v['owner'] == uid]


def take(uid, pid):
    """Saca la pendiente (una sola vez) si es de esta persona."""
    with _LOCK:
        _gc()
        p = _PENDING.get(str(pid or ''))
        if not p or p['owner'] != uid:
            return None
        return _PENDING.pop(str(pid))


def drop(uid, pid):
    return take(uid, pid) is not None


def status():
    return {'enabled': enabled(), 'base': base(), 'pending': len(_PENDING), 'suggested': list(SUGGESTED)}
