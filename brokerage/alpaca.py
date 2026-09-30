"""brokerage/alpaca.py — cliente HTTP mínimo de Alpaca (Trading API v2 + OAuth).

Tres formas de autenticarse (una por cliente):
  · 'env'   — la cuenta de la casa: ALPACA_KEY / ALPACA_SECRET / ALPACA_BASE
              (las mismas que usan las rutas /api/trade/* del server).
  · 'keys'  — clave y secreto API propios del cliente (paper o live).
  · 'oauth' — token de "Alpaca Connect" (OAuth2). El cliente autoriza a la app
              desde Alpaca; se usa `Authorization: Bearer <token>`.

Detalles OAuth (verificados el 2026-09-30 con extractos de buscador de
docs.alpaca.markets/us/docs/using-oauth2-and-trading-api y del repo público
github.com/alpacahq/alpaca-docs — la red del entorno bloqueó abrir la página
completa, así que NO se probó en vivo contra Alpaca):
  · autorizar: GET https://app.alpaca.markets/oauth/authorize
      ?response_type=code&client_id=..&redirect_uri=..&state=..
      &scope=account:write%20trading   (+ &env=paper para cuentas de papel)
  · canje: POST https://api.alpaca.markets/oauth/token (x-www-form-urlencoded)
      grant_type=authorization_code, code, client_id, client_secret,
      redirect_uri → {"access_token", "token_type":"bearer", "scope"}.
      El client_secret va en el CUERPO (no en el header Authorization).
  · uso: Authorization: Bearer <token> contra paper-api.alpaca.markets (papel)
      o api.alpaca.markets (dinero real).

Seguridad: la base URL SOLO puede ser un host oficial de Alpaca (evita que una
base manipulada mande las claves de un cliente a un servidor ajeno).
"""
import os
import re
from urllib.parse import urlencode, quote, urlparse

import requests

PAPER_BASE = 'https://paper-api.alpaca.markets'
LIVE_BASE = 'https://api.alpaca.markets'
DATA_BASE = 'https://data.alpaca.markets'
OAUTH_AUTHORIZE_URL = 'https://app.alpaca.markets/oauth/authorize'
OAUTH_TOKEN_URL = 'https://api.alpaca.markets/oauth/token'
OAUTH_SCOPE = 'account:write trading'
ALLOWED_HOSTS = {'paper-api.alpaca.markets', 'api.alpaca.markets'}
TIMEOUT = 12

_CRYPTO_RE = re.compile(r'^[A-Z0-9]{2,10}/(USD|USDT|USDC|BTC)$')


class AlpacaError(Exception):
    """Error de Alpaca con status HTTP (None = error de red/tiempo agotado)."""

    def __init__(self, message, status=None, body=None, network=False):
        super().__init__(message)
        self.status = status
        self.body = body
        self.network = network


def clean_env(v):
    return (v or '').strip().strip('"').strip("'").strip()


def norm_base(v, default=PAPER_BASE):
    """Normaliza una base de Alpaca igual que server._norm_alpaca_base (quita
    barra final, /v2, comillas; añade https://) y exige un host oficial."""
    v = (clean_env(v) or default).strip().rstrip('/')
    if not v.startswith('http'):
        v = 'https://' + v
    for suf in ('/v2', '/v1'):
        if v.endswith(suf):
            v = v[:-len(suf)]
    v = v.rstrip('/') or default
    host = (urlparse(v).hostname or '').lower()
    if host not in ALLOWED_HOSTS:
        raise ValueError(f'base de Alpaca no permitida: {host or v!r} (solo paper-api/api.alpaca.markets)')
    return 'https://' + host


def base_for_mode(mode):
    return LIVE_BASE if mode == 'live' else PAPER_BASE


def is_paper_base(base):
    return 'paper-api' in (base or '')


def is_crypto(symbol):
    return bool(_CRYPTO_RE.match(str(symbol or '').upper()))


def house_env():
    """Credenciales de la casa desde el entorno (o None si faltan)."""
    key = clean_env(os.getenv('ALPACA_KEY', ''))
    secret = clean_env(os.getenv('ALPACA_SECRET', ''))
    if not key or not secret:
        return None
    try:
        base = norm_base(os.getenv('ALPACA_BASE', PAPER_BASE))
    except ValueError:
        base = PAPER_BASE
    return {'key': key, 'secret': secret, 'base': base}


class AlpacaClient:
    """Cliente fino. Todos los métodos devuelven JSON (dict/list) o lanzan
    AlpacaError. Nunca incluye claves en los mensajes de error."""

    def __init__(self, base_url, key=None, secret=None, token=None, timeout=TIMEOUT):
        self.base = norm_base(base_url)
        self.key, self.secret, self.token = key, secret, token
        self.timeout = timeout
        if not token and not (key and secret):
            raise AlpacaError('cuenta sin credenciales de Alpaca', status=None)

    @property
    def paper(self):
        return is_paper_base(self.base)

    def _headers(self):
        h = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        if self.token:
            h['Authorization'] = f'Bearer {self.token}'
        else:
            h['APCA-API-KEY-ID'] = self.key
            h['APCA-API-SECRET-KEY'] = self.secret
        return h

    def _req(self, method, url, params=None, json=None, ok=(200, 201, 204)):
        try:
            r = requests.request(method, url, headers=self._headers(), params=params, json=json,
                                 timeout=self.timeout)
        except requests.exceptions.Timeout as e:
            raise AlpacaError('Alpaca no respondió a tiempo', network=True) from e
        except Exception as e:  # noqa: BLE001
            raise AlpacaError(f'no se pudo conectar con Alpaca ({type(e).__name__})', network=True) from e
        if r.status_code not in ok:
            msg = ''
            try:
                body = r.json()
                msg = body.get('message') or body.get('error') or ''
            except Exception:  # noqa: BLE001
                body = (r.text or '')[:300]
            hint = {401: 'credenciales rechazadas (¿clave de paper usada en live o al revés?)',
                    403: 'Alpaca rechazó la operación (permiso, poder de compra o cuenta bloqueada)',
                    404: 'no encontrado', 422: 'orden inválida para Alpaca',
                    429: 'demasiadas solicitudes a Alpaca'}.get(r.status_code, '')
            text = f'Alpaca HTTP {r.status_code}' + (f': {msg}' if msg else '') + (f' — {hint}' if hint else '')
            raise AlpacaError(text[:300], status=r.status_code, body=body)
        if r.status_code == 204 or not (r.content or b'').strip():
            return {}
        try:
            return r.json()
        except Exception as e:  # noqa: BLE001
            raise AlpacaError(f'respuesta no-JSON de Alpaca (HTTP {r.status_code})', status=r.status_code) from e

    # ── cuenta ──────────────────────────────────────────────────────────
    def get_account(self):
        return self._req('GET', f'{self.base}/v2/account')

    def get_positions(self):
        data = self._req('GET', f'{self.base}/v2/positions')
        return data if isinstance(data, list) else []

    def get_clock(self):
        return self._req('GET', f'{self.base}/v2/clock')

    # ── órdenes ─────────────────────────────────────────────────────────
    def submit_order(self, symbol, side, notional=None, qty=None, order_type='market', limit_price=None,
                     time_in_force=None, client_order_id=None):
        symbol = str(symbol).upper().strip()
        tif = time_in_force or 'day'
        if is_crypto(symbol):
            tif = 'gtc'     # Alpaca solo acepta gtc/ioc en cripto (igual que server.trade_order)
        body = {'symbol': symbol, 'side': side, 'type': order_type, 'time_in_force': tif}
        if notional is not None:
            body['notional'] = f'{float(notional):.2f}'
        else:
            body['qty'] = f'{float(qty):.9f}'.rstrip('0').rstrip('.')
        if order_type == 'limit' and limit_price is not None:
            body['limit_price'] = f'{float(limit_price):.4f}'.rstrip('0').rstrip('.')
        if client_order_id:
            body['client_order_id'] = str(client_order_id)[:128]
        return self._req('POST', f'{self.base}/v2/orders', json=body)

    def get_order(self, order_id):
        return self._req('GET', f'{self.base}/v2/orders/{quote(str(order_id), safe="")}')

    def get_order_by_client_id(self, client_order_id):
        return self._req('GET', f'{self.base}/v2/orders:by_client_order_id',
                         params={'client_order_id': str(client_order_id)})

    def cancel_order(self, order_id):
        return self._req('DELETE', f'{self.base}/v2/orders/{quote(str(order_id), safe="")}')

    def list_orders(self, status='all', limit=50):
        data = self._req('GET', f'{self.base}/v2/orders',
                         params={'status': status, 'limit': int(limit), 'direction': 'desc'})
        return data if isinstance(data, list) else []

    # ── precio de referencia (market data; puede fallar sin plan de datos) ──
    def latest_price(self, symbol):
        symbol = str(symbol).upper()
        try:
            if is_crypto(symbol):
                d = self._req('GET', f'{DATA_BASE}/v1beta3/crypto/us/latest/trades', params={'symbols': symbol})
                tr = ((d or {}).get('trades') or {}).get(symbol) or {}
            else:
                d = self._req('GET', f'{DATA_BASE}/v2/stocks/{quote(symbol, safe="")}/trades/latest')
                tr = (d or {}).get('trade') or {}
            p = float(tr.get('p') or 0)
            return p if p > 0 else None
        except (AlpacaError, TypeError, ValueError):
            return None


# ── OAuth (Alpaca Connect) ───────────────────────────────────────────────────
def oauth_config():
    cid = clean_env(os.getenv('ALPACA_OAUTH_CLIENT_ID', ''))
    sec = clean_env(os.getenv('ALPACA_OAUTH_CLIENT_SECRET', ''))
    red = clean_env(os.getenv('ALPACA_OAUTH_REDIRECT_URI', ''))
    return {'client_id': cid, 'client_secret': sec, 'redirect_uri': red,
            'configured': bool(cid and sec and red)}


def oauth_authorize_url(state, env='paper'):
    cfg = oauth_config()
    params = {'response_type': 'code', 'client_id': cfg['client_id'], 'redirect_uri': cfg['redirect_uri'],
              'state': state, 'scope': OAUTH_SCOPE}
    if env == 'paper':
        params['env'] = 'paper'
    return OAUTH_AUTHORIZE_URL + '?' + urlencode(params, quote_via=quote, safe=':')


def oauth_exchange(code):
    """Canjea el `code` por un token. Devuelve {access_token, token_type, scope}
    o lanza AlpacaError. El secreto viaja en el cuerpo (lo exige Alpaca)."""
    cfg = oauth_config()
    if not cfg['configured']:
        raise AlpacaError('OAuth de Alpaca no configurado (ALPACA_OAUTH_CLIENT_ID/SECRET/REDIRECT_URI)')
    data = {'grant_type': 'authorization_code', 'code': str(code), 'client_id': cfg['client_id'],
            'client_secret': cfg['client_secret'], 'redirect_uri': cfg['redirect_uri']}
    try:
        r = requests.post(OAUTH_TOKEN_URL, data=data, timeout=TIMEOUT,
                          headers={'Content-Type': 'application/x-www-form-urlencoded',
                                   'Accept': 'application/json'})
    except Exception as e:  # noqa: BLE001
        raise AlpacaError(f'no se pudo conectar con Alpaca para el canje OAuth ({type(e).__name__})',
                          network=True) from e
    try:
        body = r.json()
    except Exception:  # noqa: BLE001
        body = {}
    if r.status_code != 200 or not isinstance(body, dict) or not body.get('access_token'):
        msg = (body.get('error_description') or body.get('message') or body.get('error') or '') \
            if isinstance(body, dict) else ''
        raise AlpacaError(f'canje OAuth rechazado (HTTP {r.status_code})' + (f': {msg}' if msg else ''),
                          status=r.status_code)
    if str(body.get('token_type') or 'bearer').lower() != 'bearer':
        raise AlpacaError(f'tipo de token inesperado: {body.get("token_type")}')
    return {'access_token': body['access_token'], 'token_type': 'bearer', 'scope': body.get('scope') or ''}
