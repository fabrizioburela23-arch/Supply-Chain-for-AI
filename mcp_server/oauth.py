"""mcp_server/oauth.py — OAuth 2.1 mínimo (y correcto) para conectores remotos.

Lo usan los «conectores personalizados» de claude.ai y ChatGPT, que no dejan
pegar una cabecera Authorization: descubren el servidor de autorización y
hacen el flujo estándar. Piezas (spec MCP «Authorization» 2025-06-18):

  GET  /.well-known/oauth-protected-resource[/mcp]  RFC 9728 (recurso → AS)
  GET  /.well-known/oauth-authorization-server       RFC 8414 (metadatos del AS)
  POST /oauth/register                               RFC 7591 (registro dinámico)
  GET  /oauth/authorize                              página bilingüe: PIN →
  POST /oauth/authorize                              alcances + cliente → código
  POST /oauth/token                                  authorization_code (+PKCE S256
                                                     obligatorio) y refresh_token
  POST /oauth/revoke                                 RFC 7009

Los tokens emitidos son los MISMOS kmcp_… (tabla mcp_tokens, kind='oauth'),
visibles y revocables desde 🩺 Sistema → 🤖 Conectar IAs. Caducan (MCP_OAUTH_TTL_HOURS,
168 h por defecto) y se renuevan con refresh token rotativo.

Seguridad: solo quien conoce el TRADE_PIN puede aprobar (5 intentos cada 10
min por IP —la IP del proxy de confianza, no la que escribe el cliente— y un
bloqueo GLOBAL tras MCP_PIN_MAX_FAILS fallos por hora, ver auth.check_pin); el
formulario de consentimiento va firmado (HMAC con SECRET_KEY, 10 min) y se
canjea UNA sola vez (consent_nonce único); códigos de un solo uso (10 min,
guardados como sha256, consumidos con un UPDATE atómico; si se reutilizan se
revocan los tokens que ya emitieron — OAuth 2.1); redirect_uri debe coincidir
EXACTAMENTE con uno registrado (https, o http solo loopback).
Errores de la petición ANTES del PIN (response_type/PKCE inválidos) NO
redirigen solos: se muestra una página de error con un enlace que el usuario
debe pulsar, rotulado con el dominio destino (evita un «open redirect» con
clientes registrados por cualquiera — RFC 9700 §4.11.2).
Tras aprobar NO se hace un 302 desde el POST: la CSP global (form-action
'self') lo bloquearía en Chrome; se responde una página que navega al
redirect_uri (meta refresh + enlace) — solo tras el PIN del dueño.
"""
import base64
import hashlib
import hmac
import html
import json
import logging
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse

from flask import Response, jsonify, request

from mcp_server import auth as _auth

log = logging.getLogger('khipu')

CODE_TTL_S = 600
CONSENT_TTL_S = 600
REFRESH_PREFIX = 'kmcpr_'
_PROCESS_KEY = secrets.token_bytes(32)
_BAD_SCHEMES = {'javascript', 'data', 'file', 'vbscript', 'about', 'blob', 'ftp', 'ws', 'wss'}


def oauth_enabled():
    return (os.getenv('MCP_OAUTH_ENABLED', 'on').strip().lower() not in ('off', '0', 'false', 'no')
            and _auth.db_available())


def _ttl_hours():
    try:
        return max(1, int(os.getenv('MCP_OAUTH_TTL_HOURS', '168')))
    except ValueError:
        return 168


def _now():
    return datetime.now(timezone.utc)


def _base():
    from mcp_server.api import base_url
    return base_url()


def _sign_key():
    k = os.getenv('SECRET_KEY', '')
    if not k or k == 'khipu-dev-secret-change-me':
        return _PROCESS_KEY
    return hashlib.sha256(('mcp-oauth:' + k).encode()).digest()


def _b64u(b):
    return base64.urlsafe_b64encode(b).decode().rstrip('=')


def _b64u_dec(s):
    return base64.urlsafe_b64decode(s + '=' * (-len(s) % 4))


def sign(obj):
    body = _b64u(json.dumps(obj, separators=(',', ':'), sort_keys=True).encode())
    mac = _b64u(hmac.new(_sign_key(), body.encode(), hashlib.sha256).digest())
    return body + '.' + mac


def unsign(tok):
    try:
        body, mac = str(tok).split('.', 1)
        want = _b64u(hmac.new(_sign_key(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(mac, want):
            return None
        obj = json.loads(_b64u_dec(body))
        if not isinstance(obj, dict) or obj.get('exp', 0) < time.time():
            return None
        return obj
    except Exception:  # noqa: BLE001
        return None


def pkce_s256(verifier):
    return _b64u(hashlib.sha256(verifier.encode('ascii')).digest())


def valid_redirect_uri(uri):
    try:
        u = urlparse(str(uri))
    except Exception:  # noqa: BLE001
        return False
    if not u.scheme or u.fragment:
        return False
    sch = u.scheme.lower()
    if sch == 'https':
        return bool(u.netloc)
    if sch == 'http':
        return (u.hostname or '') in ('localhost', '127.0.0.1', '::1')
    # esquemas privados de apps nativas (RFC 8252 §7.1): cursor://…, vscode://…
    return sch not in _BAD_SCHEMES and all(c.isalnum() or c in '+.-' for c in sch)


def _json_err(error, desc, status=400, headers=None):
    resp = jsonify({'error': error, 'error_description': desc})
    resp.status_code = status
    resp.headers['Cache-Control'] = 'no-store'
    for k, v in (headers or {}).items():
        resp.headers[k] = v
    return resp


def _cors_public(resp):
    # los metadatos y el registro los leen también clientes en navegador
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, MCP-Protocol-Version'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return resp


# ── metadatos ───────────────────────────────────────────────────────────────
def protected_resource_metadata():
    base = _base()
    out = {'resource': base + '/mcp', 'scopes_supported': list(_auth.SCOPES),
           'bearer_methods_supported': ['header'], 'resource_name': 'Khipus Finance AI (MCP)'}
    if oauth_enabled():
        out['authorization_servers'] = [base]
    return out


def authorization_server_metadata():
    base = _base()
    return {'issuer': base,
            'authorization_endpoint': base + '/oauth/authorize',
            'token_endpoint': base + '/oauth/token',
            'registration_endpoint': base + '/oauth/register',
            'revocation_endpoint': base + '/oauth/revoke',
            'response_types_supported': ['code'],
            'response_modes_supported': ['query'],
            'grant_types_supported': ['authorization_code', 'refresh_token'],
            'code_challenge_methods_supported': ['S256'],
            'token_endpoint_auth_methods_supported': ['none', 'client_secret_post', 'client_secret_basic'],
            'revocation_endpoint_auth_methods_supported': ['none', 'client_secret_post', 'client_secret_basic'],
            'scopes_supported': list(_auth.SCOPES),
            'authorization_response_iss_parameter_supported': True}


# ── clientes / códigos ──────────────────────────────────────────────────────
def _session():
    from ontology.db import session_scope
    return session_scope()


def _get_client(s, client_id):
    from mcp_server.models import McpOAuthClient
    return s.get(McpOAuthClient, str(client_id or '')[:80]) if client_id else None


def _client_auth(s, form):
    """Autenticación del cliente en /oauth/token y /oauth/revoke → (cliente, error)."""
    cid, secret = form.get('client_id'), form.get('client_secret')
    ah = request.headers.get('Authorization', '')
    if ah.lower().startswith('basic '):
        try:
            from urllib.parse import unquote
            dec = base64.b64decode(ah[6:].strip()).decode()
            u, _, p = dec.partition(':')
            cid, secret = unquote(u), unquote(p)
        except Exception:  # noqa: BLE001
            return None, 'invalid basic authorization'
    c = _get_client(s, cid)
    if c is None:
        return None, 'unknown client_id'
    if c.secret_hash:
        if not secret or not hmac.compare_digest(_auth.hash_secret(secret), c.secret_hash):
            return None, 'client authentication failed'
    return c, None


def _issue(s, row_or_none, client, scopes, broker_client_id, name, approved_by, code_hash=None):
    """Crea (o rota) el token OAuth → respuesta del token endpoint."""
    exp = _now() + timedelta(hours=_ttl_hours())
    refresh = REFRESH_PREFIX + secrets.token_urlsafe(32)
    if row_or_none is None:
        row, plain = _auth.create_token(s, name, scopes, client_id=broker_client_id, created_by=approved_by,
                                        kind='oauth', expires_at=exp, oauth_client_id=client.client_id,
                                        oauth_code_hash=code_hash)
    else:
        row = row_or_none
        plain = _auth.new_token()
        row.token_hash, row.token_prefix, row.expires_at = _auth.hash_secret(plain), plain[:10], exp
    row.refresh_hash = _auth.hash_secret(refresh)
    s.flush()
    return {'access_token': plain, 'token_type': 'Bearer', 'expires_in': _ttl_hours() * 3600,
            'refresh_token': refresh, 'scope': ' '.join(row.scopes or [])}


def _revoke_from_code(s, code_hash):
    """Código reutilizado (¿robado?) → se revocan los tokens que ya emitió (OAuth 2.1 / RFC 6749 §4.1.2)."""
    from mcp_server.models import McpToken
    n = (s.query(McpToken)
         .filter(McpToken.oauth_code_hash == code_hash, McpToken.revoked.is_(False))
         .update({McpToken.revoked: True, McpToken.revoked_at: _now(),
                  McpToken.revoked_by: 'oauth: authorization code reused', McpToken.refresh_hash: None},
                 synchronize_session=False))
    if n:
        log.warning('mcp oauth: código reutilizado → %d token(s) revocado(s)', n)
    return n


# ── páginas (bilingües) ─────────────────────────────────────────────────────
_CSS = ('body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;'
        'background:radial-gradient(900px 500px at 50% -10%,#0B1222 0%,#06090F 60%);color:#E8EDFB;'
        'font-family:Inter,system-ui,sans-serif;padding:16px;box-sizing:border-box}'
        '.card{width:min(520px,100%);border:1px solid rgba(122,158,255,.25);border-radius:16px;'
        'background:rgba(11,18,34,.85);padding:22px 20px;box-shadow:0 24px 70px rgba(0,0,0,.6)}'
        'h1{font-size:19px;margin:0 0 4px}.en{color:#8b96b5;font-size:12px}.muted{color:#9BA6C4;font-size:13px;'
        'line-height:1.55}label{display:block;margin:10px 0 4px;font-size:13px}'
        'input[type=password],input[type=text],select{width:100%;box-sizing:border-box;background:#0B1222;'
        'border:1px solid rgba(122,158,255,.3);color:#E8EDFB;border-radius:9px;padding:10px;font-size:15px}'
        '.sc{display:flex;gap:9px;align-items:flex-start;margin:8px 0;font-size:13px;line-height:1.45}'
        '.sc input{margin-top:3px}.btns{display:flex;gap:10px;margin-top:16px;flex-wrap:wrap}'
        'button{flex:1;min-width:130px;padding:11px 14px;border-radius:10px;font-weight:700;font-size:14px;'
        'cursor:pointer;border:1px solid #00E0FF;background:rgba(0,224,255,.14);color:#00E0FF}'
        'button.no{border-color:rgba(122,158,255,.35);background:transparent;color:#9BA6C4}'
        '.err{border:1px dashed #f87171;color:#fca5a5;border-radius:9px;padding:8px 10px;margin:10px 0;'
        'font-size:13px}.warn{border:1px dashed #f59e0b;color:#fbbf24;border-radius:9px;padding:8px 10px;'
        'margin:10px 0;font-size:12.5px;line-height:1.5}code{color:#00E0FF;word-break:break-all}')


def _page(title_es, title_en, body_html, status=200, extra_head=''):
    doc = ('<!doctype html><html lang="es"><head><meta charset="utf-8">'
           '<meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>{html.escape(title_es)} · Khipus</title>{extra_head}<style>{_CSS}</style></head>'
           f'<body><div class="card"><h1>🤖 {html.escape(title_es)}</h1><div class="en">{html.escape(title_en)}</div>'
           f'{body_html}</div></body></html>')
    resp = Response(doc, status=status, mimetype='text/html')
    resp.headers['Cache-Control'] = 'no-store'
    return resp


def _error_page(es, en, status=400, extra_html=''):
    return _page('No se pudo autorizar', 'Authorization failed',
                 f'<div class="err">{html.escape(es)}<br><span class="en">{html.escape(en)}</span></div>{extra_html}',
                 status)


def _request_error_page(uri, params):
    """Error de la petición ANTES del PIN: NO se redirige solo (open redirect).
    Enlace que el usuario debe pulsar, rotulado con el dominio destino."""
    sep = '&' if urlparse(uri).query else '?'
    target = uri + sep + urlencode({k: v for k, v in params.items() if v is not None})
    host = urlparse(uri).netloc or urlparse(uri).scheme + ':'
    link = (f'<p class="muted">Si esperabas volver a tu aplicación, puedes hacerlo aquí. '
            f'<span class="en">If you expected to return to your application, you can do so here.</span></p>'
            f'<div class="btns"><a href="{html.escape(target, quote=True)}" rel="noopener noreferrer" '
            f'style="flex:1"><button type="button" class="no">Volver a · Return to <b>{html.escape(host)}</b>'
            f'</button></a></div>')
    return _error_page(f'La aplicación envió una solicitud de autorización inválida ({params.get("error")}): '
                       f'{params.get("error_description")}.',
                       f'The application sent an invalid authorization request ({params.get("error")}): '
                       f'{params.get("error_description")}.', 400, link)


_AUTH_PARAMS = ('response_type', 'client_id', 'redirect_uri', 'code_challenge', 'code_challenge_method',
                'state', 'scope', 'resource')


def _hidden(params):
    return ''.join(f'<input type="hidden" name="{html.escape(k)}" value="{html.escape(str(v))}">'
                   for k, v in params.items() if v is not None)


def _redirect_page(uri, params):
    sep = '&' if urlparse(uri).query else '?'
    target = uri + sep + urlencode({k: v for k, v in params.items() if v is not None})
    t = html.escape(target, quote=True)
    body = ('<p class="muted">Listo. Volviendo a la aplicación…<br><span class="en">Done. Returning to the '
            'application…</span></p>'
            f'<div class="btns"><a href="{t}" style="flex:1"><button type="button">Continuar · Continue</button></a></div>')
    return _page('Conexión autorizada' if 'code' in params else 'Autorización cancelada',
                 'Connection authorized' if 'code' in params else 'Authorization cancelled', body,
                 extra_head=f'<meta http-equiv="refresh" content="0;url={t}">')


def _validate_auth_request(s, p):
    """→ (cliente, error_page | None, redirect_error | None)."""
    client = _get_client(s, p.get('client_id'))
    if client is None:
        return None, _error_page('Cliente OAuth desconocido (client_id). Vuelve a conectar desde tu app.',
                                 'Unknown OAuth client (client_id). Reconnect from your app.'), None
    uris = list(client.redirect_uris or [])
    ru = p.get('redirect_uri') or (uris[0] if len(uris) == 1 else None)
    if not ru or ru not in uris:
        return None, _error_page('redirect_uri no coincide con el registrado.',
                                 'redirect_uri does not match the registered one.'), None
    p['redirect_uri'] = ru
    if p.get('response_type') != 'code':
        return client, None, ('unsupported_response_type', 'only response_type=code is supported')
    if not p.get('code_challenge') or p.get('code_challenge_method') != 'S256':
        return client, None, ('invalid_request', 'PKCE with code_challenge_method=S256 is required')
    if len(p['code_challenge']) < 43 or len(p['code_challenge']) > 128:
        return client, None, ('invalid_request', 'invalid code_challenge')
    return client, None, None


def _broker_clients():
    try:
        import importlib
        svc = importlib.import_module('brokerage.service')
        if not svc.available():
            return []
        with _session() as s:
            return [{'id': c.get('id'), 'name': c.get('name'), 'mode': c.get('mode')} for c in svc.list_clients(s)]
    except Exception:  # noqa: BLE001
        return []


def _pin_step(client, p, err=None):
    host = urlparse(p.get('redirect_uri') or '').netloc or p.get('redirect_uri')
    body = (f'<p class="muted"><b>{html.escape(client.client_name or client.client_id)}</b> quiere conectarse a '
            f'tu Khipus por MCP (volverá a <code>{html.escape(host or "")}</code>).<br>'
            f'<span class="en">wants to connect to your Khipus via MCP.</span></p>'
            + (f'<div class="err">{html.escape(err[0])}<br><span class="en">{html.escape(err[1])}</span></div>' if err else '')
            + '<form method="post" action="/oauth/authorize" autocomplete="off">' + _hidden(
                {k: p.get(k) for k in _AUTH_PARAMS}) +
            '<input type="hidden" name="step" value="pin">'
            '<label>PIN de trading (TRADE_PIN) <span class="en">· Trading PIN</span></label>'
            '<input type="password" name="pin" required autofocus autocomplete="off">'
            '<p class="muted" style="font-size:12px">Solo el dueño de la cuenta Khipus conoce este PIN. '
            '<span class="en">Only the Khipus account owner knows this PIN.</span></p>'
            '<div class="btns"><button type="submit">Continuar · Continue</button></div></form>')
    return _page('Conectar una IA a Khipus', 'Connect an AI to Khipus', body)


def _consent_step(client, p, consent_tok, err=None, selected=None):
    if selected is not None:
        req = set(selected)
    else:
        req = set(_auth.normalize_scopes(p.get('scope'))) if p.get('scope') else {'read', 'research'}
    bcs = _broker_clients()
    opts = ''.join(f'<option value="{html.escape(str(c["id"]))}">{html.escape(str(c["name"]))} '
                   f'({"PAPEL · paper" if c.get("mode") != "live" else "DINERO REAL · LIVE"})</option>' for c in bcs)
    trade_block = (
        '<div class="sc"><input type="checkbox" name="scope_trade" id="st" value="1"'
        + (' checked' if 'trade' in req else '') + '><label for="st" style="margin:0"><b>trade</b> — proponer '
        'órdenes a UN cliente; cada orden queda <b>pendiente de tu aprobación</b> en 👥 Clientes → Aprobaciones.'
        '<br><span class="en">propose orders for ONE client; every order waits for YOUR approval.</span></label></div>'
        '<label>Cliente de corretaje <span class="en">· Brokerage client</span></label>'
        f'<select name="broker_client_id"><option value="">—</option>{opts}</select>'
    ) if bcs else ('<p class="muted" style="font-size:12px">trade: no hay clientes de corretaje configurados. '
                   '<span class="en">no brokerage clients configured.</span></p>')
    body = (f'<p class="muted"><b>{html.escape(client.client_name or client.client_id)}</b> — elige qué puede '
            'hacer esta conexión. <span class="en">Choose what this connection may do.</span></p>'
            + (f'<div class="err">{html.escape(err[0])}<br><span class="en">{html.escape(err[1])}</span></div>' if err else '')
            + '<form method="post" action="/oauth/authorize" autocomplete="off">'
            f'<input type="hidden" name="step" value="consent"><input type="hidden" name="consent" value="{html.escape(consent_tok)}">'
            '<div class="sc"><input type="checkbox" checked disabled><label style="margin:0"><b>read</b> — consultar '
            'grafo, empresas, investigación, riesgo. <span class="en">query graph, companies, research, risk.</span>'
            '</label></div>'
            '<div class="sc"><input type="checkbox" name="scope_research" id="sr" value="1"'
            + (' checked' if 'research' in req else '') + '><label for="sr" style="margin:0"><b>research</b> — lanzar '
            'investigación y comité (gasta presupuesto de IA). <span class="en">start research and committee runs '
            '(uses AI budget).</span></label></div>' + trade_block +
            '<label>Nombre de la conexión <span class="en">· Connection name</span></label>'
            f'<input type="text" name="token_name" maxlength="100" value="{html.escape((client.client_name or "OAuth")[:100])}">'
            '<div class="warn">Puedes revocar esta conexión cuando quieras en Khipus → 🩺 Sistema → 🤖 Conectar IAs. '
            '<span class="en">You can revoke it anytime in Khipus → 🩺 System → 🤖 Connect AIs.</span></div>'
            '<div class="btns"><button type="submit" name="decision" value="approve">Autorizar · Authorize</button>'
            '<button class="no" type="submit" name="decision" value="deny">Cancelar · Deny</button></div></form>')
    return _page('Permisos de la conexión', 'Connection permissions', body)


# ── registro de rutas ───────────────────────────────────────────────────────
def register(bp):
    from core.http import rate_limit

    def _meta_resource(suffix=None):
        if request.method == 'OPTIONS':
            return _cors_public(Response(status=204))
        return _cors_public(jsonify(protected_resource_metadata()))

    def _meta_as():
        if request.method == 'OPTIONS':
            return _cors_public(Response(status=204))
        if not oauth_enabled():
            return _cors_public(_json_err('temporarily_unavailable', 'OAuth is disabled on this server', 404))
        return _cors_public(jsonify(authorization_server_metadata()))

    bp.add_url_rule('/.well-known/oauth-protected-resource', 'oauth_prm', _meta_resource, methods=['GET', 'OPTIONS'])
    bp.add_url_rule('/.well-known/oauth-protected-resource/mcp', 'oauth_prm_mcp', _meta_resource,
                    methods=['GET', 'OPTIONS'])
    bp.add_url_rule('/.well-known/oauth-authorization-server', 'oauth_asm', _meta_as, methods=['GET', 'OPTIONS'])
    bp.add_url_rule('/.well-known/oauth-authorization-server/mcp', 'oauth_asm_mcp', _meta_as,
                    methods=['GET', 'OPTIONS'])

    @rate_limit(20, 3600)
    def oauth_register():
        if request.method == 'OPTIONS':
            return _cors_public(Response(status=204))
        if not oauth_enabled():
            return _cors_public(_json_err('temporarily_unavailable', 'OAuth needs DATABASE_URL on this server', 503))
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return _cors_public(_json_err('invalid_client_metadata', 'JSON body required'))
        uris = body.get('redirect_uris')
        if not isinstance(uris, list) or not uris or len(uris) > 10:
            return _cors_public(_json_err('invalid_redirect_uri', 'redirect_uris (1-10) is required'))
        uris = [str(u)[:500] for u in uris]
        if not all(valid_redirect_uri(u) for u in uris):
            return _cors_public(_json_err('invalid_redirect_uri',
                                          'redirect URIs must be https, http loopback or a private app scheme'))
        method = str(body.get('token_endpoint_auth_method') or 'none')
        if method not in ('none', 'client_secret_post', 'client_secret_basic'):
            return _cors_public(_json_err('invalid_client_metadata', 'unsupported token_endpoint_auth_method'))
        gts = body.get('grant_types') or ['authorization_code', 'refresh_token']
        if not isinstance(gts, list) or any(g not in ('authorization_code', 'refresh_token') for g in gts):
            return _cors_public(_json_err('invalid_client_metadata', 'unsupported grant_types'))
        from mcp_server.models import McpOAuthClient
        cid = 'kmcpc_' + secrets.token_urlsafe(18)
        secret = secrets.token_urlsafe(32) if method != 'none' else None
        name = str(body.get('client_name') or 'MCP client')[:200]
        scope = ' '.join(_auth.normalize_scopes(body.get('scope') or 'read research'))

        def _w():
            with _session() as s:
                s.add(McpOAuthClient(client_id=cid, client_name=name, redirect_uris=uris,
                                     token_endpoint_auth_method=method,
                                     secret_hash=_auth.hash_secret(secret) if secret else None, scope=scope,
                                     meta={k: str(body.get(k))[:300] for k in ('client_uri', 'logo_uri', 'software_id',
                                                                               'software_version') if body.get(k)}))
        try:
            _auth.with_schema(_w)
        except Exception as e:  # noqa: BLE001
            log.warning('mcp oauth register: %s', e)
            return _cors_public(_json_err('server_error', 'could not register the client', 500))
        out = {'client_id': cid, 'client_id_issued_at': int(time.time()), 'client_name': name,
               'redirect_uris': uris, 'grant_types': gts, 'response_types': ['code'],
               'token_endpoint_auth_method': method, 'scope': scope}
        if secret:
            out.update({'client_secret': secret, 'client_secret_expires_at': 0})
        resp = jsonify(out)
        resp.status_code = 201
        resp.headers['Cache-Control'] = 'no-store'
        return _cors_public(resp)

    bp.add_url_rule('/oauth/register', 'oauth_register', oauth_register, methods=['POST', 'OPTIONS'])

    def oauth_authorize_get():
        if not oauth_enabled():
            return _error_page('OAuth no está disponible (falta DATABASE_URL o MCP_OAUTH_ENABLED=off).',
                               'OAuth is not available (DATABASE_URL missing or MCP_OAUTH_ENABLED=off).', 503)
        p = {k: request.args.get(k) for k in _AUTH_PARAMS}
        with _session() as s:
            client, page, rerr = _validate_auth_request(s, p)
            if page is not None:
                return page
            if rerr:
                return _request_error_page(p['redirect_uri'], {'error': rerr[0], 'error_description': rerr[1],
                                                               'state': p.get('state'), 'iss': _base()})
            return _pin_step(client, p)

    bp.add_url_rule('/oauth/authorize', 'oauth_authorize_get', oauth_authorize_get, methods=['GET'])

    def oauth_authorize_post():
        if not oauth_enabled():
            return _error_page('OAuth no está disponible.', 'OAuth is not available.', 503)
        f = request.form
        step = f.get('step')
        if step == 'pin':
            p = {k: f.get(k) for k in _AUTH_PARAMS}
            with _session() as s:
                client, page, rerr = _validate_auth_request(s, p)
                if page is not None:
                    return page
                if rerr:
                    return _request_error_page(p['redirect_uri'], {'error': rerr[0], 'error_description': rerr[1],
                                                                   'state': p.get('state'), 'iss': _base()})
                ip = _auth.client_ip()
                if not _auth.allow(f'ip:{ip}', 'oauth_pin', 5, 600):
                    return _pin_step(client, p, ('Demasiados intentos. Espera 10 minutos.',
                                                 'Too many attempts. Wait 10 minutes.'))
                bad = _auth.check_pin(f.get('pin', ''), ip=ip, where='oauth_authorize')
                if bad:
                    if bad[1] == 403:
                        return _error_page('El trading/PIN no está configurado en el servidor (TRADE_PIN).',
                                           'TRADE_PIN is not configured on the server.', 403)
                    if bad[1] == 429:
                        return _pin_step(client, p, (bad[0]['error'], bad[0]['error_en']))
                    return _pin_step(client, p, ('PIN incorrecto.', 'Wrong PIN.'))
                consent = sign({'p': p, 'exp': int(time.time()) + CONSENT_TTL_S, 'n': secrets.token_hex(16)})
                return _consent_step(client, p, consent)
        if step == 'consent':
            data = unsign(f.get('consent', ''))
            if not data:
                return _error_page('El formulario caducó (10 min). Vuelve a conectar desde tu app.',
                                   'The form expired (10 min). Reconnect from your app.')
            p = data['p']
            nonce = str(data.get('n') or '')[:40] or None
            from mcp_server.models import McpOAuthCode
            with _session() as s:
                client, page, rerr = _validate_auth_request(s, dict(p))
                if page is not None:
                    return page
                if nonce and s.query(McpOAuthCode.code_hash).filter(McpOAuthCode.consent_nonce == nonce).first():
                    return _error_page('Este formulario ya se usó. Vuelve a conectar desde tu app.',
                                       'This form was already used. Reconnect from your app.', 409)
                if f.get('decision') != 'approve':
                    return _redirect_page(p['redirect_uri'], {'error': 'access_denied',
                                                              'error_description': 'the user denied access',
                                                              'state': p.get('state'), 'iss': _base()})
                scopes = ['read'] + (['research'] if f.get('scope_research') else []) + \
                    (['trade'] if f.get('scope_trade') else [])
                bcid = (f.get('broker_client_id') or '').strip()[:60] or None
                if 'trade' in scopes:
                    if not bcid:
                        return _consent_step(client, p, f.get('consent'),
                                             ('Para «trade» elige un cliente de corretaje.',
                                              'For "trade" pick a brokerage client.'), selected=scopes)
                    try:
                        bcid, _ = _auth.resolve_broker_client(s, bcid)
                    except ValueError as e:
                        return _consent_step(client, p, f.get('consent'),
                                             (getattr(e, 'es', str(e)), getattr(e, 'en', str(e))), selected=scopes)
                else:
                    bcid = None
                code = secrets.token_urlsafe(32)
                name = (f.get('token_name') or client.client_name or 'OAuth').strip()[:100] or 'OAuth'
                s.add(McpOAuthCode(code_hash=_auth.hash_secret(code), oauth_client_id=client.client_id,
                                   redirect_uri=p['redirect_uri'], code_challenge=p['code_challenge'],
                                   scopes=scopes, broker_client_id=bcid, resource=p.get('resource'),
                                   token_name=f'{name} (OAuth)', approved_by='owner (PIN)',
                                   expires_at=_now() + timedelta(seconds=CODE_TTL_S), used=False,
                                   consent_nonce=nonce))
                try:
                    s.flush()
                except Exception as e:  # noqa: BLE001 — carrera: el mismo consentimiento enviado dos veces
                    if 'unique' in str(e).lower() or 'IntegrityError' in type(e).__name__:
                        s.rollback()
                        return _error_page('Este formulario ya se usó. Vuelve a conectar desde tu app.',
                                           'This form was already used. Reconnect from your app.', 409)
                    raise
            return _redirect_page(p['redirect_uri'], {'code': code, 'state': p.get('state'), 'iss': _base()})
        return _error_page('Solicitud inválida.', 'Invalid request.')

    bp.add_url_rule('/oauth/authorize', 'oauth_authorize_post', rate_limit(30, 600)(oauth_authorize_post),
                    methods=['POST'])

    def oauth_token():
        if request.method == 'OPTIONS':
            return _cors_public(Response(status=204))
        if not oauth_enabled():
            return _cors_public(_json_err('temporarily_unavailable', 'OAuth is not available', 503))
        form = request.form if request.form else (request.get_json(silent=True) or {})
        gt = form.get('grant_type')
        from mcp_server.models import McpOAuthCode, McpToken

        def _do():
            with _session() as s:
                client, cerr = _client_auth(s, form)
                if cerr:
                    return _json_err('invalid_client', cerr, 401)
                if gt == 'authorization_code':
                    code, verifier = form.get('code') or '', form.get('code_verifier') or ''
                    ch = _auth.hash_secret(code)
                    row = s.get(McpOAuthCode, ch) if code else None
                    if row is None or row.oauth_client_id != client.client_id:
                        return _json_err('invalid_grant', 'unknown authorization code')
                    if row.used:
                        _revoke_from_code(s, ch)
                        return _json_err('invalid_grant', 'authorization code already used')
                    exp = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
                    if exp < _now():
                        return _json_err('invalid_grant', 'authorization code expired')
                    ru = form.get('redirect_uri')
                    if ru and ru != row.redirect_uri:
                        return _json_err('invalid_grant', 'redirect_uri mismatch')
                    if not (43 <= len(verifier) <= 128) or not hmac.compare_digest(pkce_s256(verifier),
                                                                                  row.code_challenge):
                        return _json_err('invalid_grant', 'PKCE verification failed')
                    res = form.get('resource')
                    if res and row.resource and res.rstrip('/') != row.resource.rstrip('/'):
                        return _json_err('invalid_target', 'resource does not match the authorization request')
                    # consumo ATÓMICO: dos canjes simultáneos del mismo código → solo uno gana
                    won = (s.query(McpOAuthCode)
                           .filter(McpOAuthCode.code_hash == ch, McpOAuthCode.used.is_(False))
                           .update({McpOAuthCode.used: True}, synchronize_session=False))
                    if won != 1:
                        _revoke_from_code(s, ch)
                        return _json_err('invalid_grant', 'authorization code already used')
                    try:
                        out = _issue(s, None, client, row.scopes or ['read'], row.broker_client_id,
                                     row.token_name or 'OAuth', row.approved_by, code_hash=ch)
                    except ValueError as e:
                        return _json_err('invalid_grant', getattr(e, 'en', str(e)))
                    return out
                if gt == 'refresh_token':
                    rt = form.get('refresh_token') or ''
                    row = (s.query(McpToken).filter(McpToken.refresh_hash == _auth.hash_secret(rt)).first()
                           if rt.startswith(REFRESH_PREFIX) else None)
                    if row is None or row.revoked or row.oauth_client_id != client.client_id:
                        return _json_err('invalid_grant', 'invalid refresh token')
                    return _issue(s, row, client, row.scopes, row.client_id, row.name, None)
                return _json_err('unsupported_grant_type', 'use authorization_code or refresh_token')
        try:
            out = _auth.with_schema(_do)
        except Exception as e:  # noqa: BLE001
            log.warning('mcp oauth token: %s', e)
            return _cors_public(_json_err('server_error', 'token endpoint error', 500))
        if isinstance(out, Response):
            return _cors_public(out)
        resp = jsonify(out)
        resp.headers['Cache-Control'] = 'no-store'
        resp.headers['Pragma'] = 'no-cache'
        return _cors_public(resp)

    bp.add_url_rule('/oauth/token', 'oauth_token', rate_limit(60, 600)(oauth_token), methods=['POST', 'OPTIONS'])

    def oauth_revoke():
        if request.method == 'OPTIONS':
            return _cors_public(Response(status=204))
        if not oauth_enabled():
            return _cors_public(Response(status=200))
        form = request.form if request.form else (request.get_json(silent=True) or {})
        tok = form.get('token') or ''
        from mcp_server.models import McpToken

        def _do():
            with _session() as s:
                client, cerr = _client_auth(s, form)
                if cerr:
                    return _json_err('invalid_client', cerr, 401)
                h = _auth.hash_secret(tok)
                row = s.query(McpToken).filter((McpToken.token_hash == h) | (McpToken.refresh_hash == h)).first()
                if row is not None and row.oauth_client_id == client.client_id and not row.revoked:
                    row.revoked, row.revoked_at, row.revoked_by = True, _now(), f'oauth:{client.client_id}'[:120]
                    row.refresh_hash = None
                return None
        try:
            r = _auth.with_schema(_do)
        except Exception as e:  # noqa: BLE001
            log.warning('mcp oauth revoke: %s', e)
            r = None
        return _cors_public(r if r is not None else Response(status=200))

    bp.add_url_rule('/oauth/revoke', 'oauth_revoke', rate_limit(60, 600)(oauth_revoke), methods=['POST', 'OPTIONS'])
