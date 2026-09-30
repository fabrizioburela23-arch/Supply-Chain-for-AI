"""tests/test_brokerage.py — corretaje multi-cliente (brokerage/).

Sin red: Alpaca se sustituye por un bróker FALSO (FakeAlpaca) o por respuestas
HTTP grabadas (monkeypatch de requests). Los tests con base requieren Postgres:

    DATABASE_URL=postgresql://postgres:devpass@localhost:5432/khipus_bk \
        python3 -m pytest tests/test_brokerage.py -q
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')

KEY = 'PKTESTKEY0001ABCD'
SECRET = 'sEcReTvAlUe-9876-NEVER-LEAK'
PIN = '4321'


# ════════════════════════════════════════════════════════════════════════════
# Bróker falso (mismas formas de JSON que Alpaca: números como strings)
# ════════════════════════════════════════════════════════════════════════════
class FakeAlpaca:
    def __init__(self, equity=10000.0, cash=10000.0, buying_power=10000.0, positions=None, paper=True,
                 clock_open=True, price=100.0):
        self.paper = paper
        self.account = {'equity': str(equity), 'cash': str(cash), 'buying_power': str(buying_power),
                        'portfolio_value': str(equity), 'currency': 'USD', 'status': 'ACTIVE',
                        'trading_blocked': False, 'account_blocked': False}
        self.positions = positions or []
        self.clock_open = clock_open
        self.price = price
        self.orders, self.by_coid, self.submits = {}, {}, []
        self.timeout_after_accept = False
        self.fail_before_accept = False      # la red cae ANTES de que Alpaca reciba la orden
        self.lookup_down = False             # GET por client_order_id también falla (red)
        self.reject_submit = None

    def get_account(self):
        return dict(self.account)

    def get_positions(self):
        return [dict(p) for p in self.positions]

    def get_clock(self):
        return {'is_open': self.clock_open}

    def latest_price(self, symbol):
        return self.price

    def submit_order(self, symbol, side, notional=None, qty=None, order_type='market', limit_price=None,
                     time_in_force=None, client_order_id=None):
        from brokerage.alpaca import AlpacaError
        self.submits.append({'symbol': symbol, 'side': side, 'notional': notional, 'qty': qty,
                             'client_order_id': client_order_id, 'tif': time_in_force})
        if self.reject_submit:
            raise AlpacaError(self.reject_submit, status=403)
        if self.fail_before_accept:
            raise AlpacaError('no se pudo conectar con Alpaca (ConnectionError)', network=True)
        if client_order_id in self.by_coid:
            raise AlpacaError('Alpaca HTTP 422: client_order_id must be unique', status=422)
        oid = f'alp-{len(self.orders) + 1}'
        od = {'id': oid, 'client_order_id': client_order_id, 'status': 'accepted', 'symbol': symbol,
              'side': side, 'filled_qty': '0', 'filled_avg_price': None}
        self.orders[oid] = od
        self.by_coid[client_order_id] = od
        if self.timeout_after_accept:
            raise AlpacaError('Alpaca no respondió a tiempo', network=True)
        return dict(od)

    def get_order(self, order_id):
        from brokerage.alpaca import AlpacaError
        if order_id not in self.orders:
            raise AlpacaError('Alpaca HTTP 404', status=404)
        return dict(self.orders[order_id])

    def get_order_by_client_id(self, coid):
        from brokerage.alpaca import AlpacaError
        if self.lookup_down:
            raise AlpacaError('Alpaca no respondió a tiempo', network=True)
        if coid not in self.by_coid:
            raise AlpacaError('Alpaca HTTP 404', status=404)
        return dict(self.by_coid[coid])

    def cancel_order(self, order_id):
        self.orders[order_id]['status'] = 'canceled'
        return {}


# ════════════════════════════════════════════════════════════════════════════
# 1. Cifrado (sin base)
# ════════════════════════════════════════════════════════════════════════════
def test_crypto_roundtrip_and_mask(monkeypatch):
    from cryptography.fernet import Fernet
    from brokerage import crypto
    monkeypatch.setenv('BROKERAGE_ENC_KEY', Fernet.generate_key().decode())
    tok = crypto.encrypt_json({'key': KEY, 'secret': SECRET})
    assert SECRET not in tok and KEY not in tok
    assert crypto.decrypt_json(tok) == {'key': KEY, 'secret': SECRET}
    assert crypto.key_source() == 'env'
    assert crypto.mask(KEY) == '****ABCD'
    assert crypto.mask('abc') == '****'
    assert crypto.mask('') == ''
    # otra clave → no se puede descifrar (error claro, sin filtrar nada)
    monkeypatch.setenv('BROKERAGE_ENC_KEY', Fernet.generate_key().decode())
    with pytest.raises(crypto.CryptoUnavailable) as ei:
        crypto.decrypt_json(tok)
    assert SECRET not in str(ei.value)


def test_crypto_derived_key_and_signature(monkeypatch):
    from brokerage import crypto
    monkeypatch.delenv('BROKERAGE_ENC_KEY', raising=False)
    monkeypatch.setenv('SECRET_KEY', 'algo-secreto-de-prueba')
    assert crypto.key_source() == 'secret_key'
    assert crypto.decrypt_json(crypto.encrypt_json({'a': 1})) == {'a': 1}
    monkeypatch.setenv('SECRET_KEY', 'khipu-dev-secret-change-me')
    assert crypto.key_source() == 'default'
    sig = crypto.sign('abc|cli|paper')
    assert crypto.verify('abc|cli|paper', sig)
    assert not crypto.verify('abc|OTRO|paper', sig)
    monkeypatch.setenv('BROKERAGE_ENC_KEY', 'no-es-fernet')
    with pytest.raises(crypto.CryptoUnavailable):
        crypto.encrypt_json({'x': 1})


# ════════════════════════════════════════════════════════════════════════════
# 2. Cliente HTTP de Alpaca con respuestas grabadas (sin base)
# ════════════════════════════════════════════════════════════════════════════
class _Resp:
    def __init__(self, status, payload):
        self.status_code = status
        self._p = payload
        self.content = b'' if payload is None else json.dumps(payload).encode()
        self.text = self.content.decode()

    def json(self):
        if self._p is None:
            raise ValueError('no json')
        return self._p


REC_ACCOUNT = {'id': 'x', 'account_number': 'PA123', 'status': 'ACTIVE', 'currency': 'USD', 'cash': '5000.12',
               'buying_power': '10000.24', 'equity': '10250.5', 'portfolio_value': '10250.5',
               'last_equity': '10100', 'trading_blocked': False, 'account_blocked': False}
REC_ORDER = {'id': '61e69015-8549-4bfd-b9c3-01e75843f47d', 'client_order_id': 'abc', 'status': 'accepted',
             'symbol': 'AAPL', 'side': 'buy', 'filled_qty': '0', 'filled_avg_price': None}


def test_alpaca_client_headers_and_order_body(monkeypatch):
    from brokerage import alpaca
    calls = []

    def fake_request(method, url, headers=None, params=None, json=None, timeout=None):
        calls.append({'method': method, 'url': url, 'headers': headers, 'params': params, 'json': json,
                      'timeout': timeout})
        if url.endswith('/v2/account'):
            return _Resp(200, REC_ACCOUNT)
        if url.endswith('/v2/orders') and method == 'POST':
            return _Resp(200, REC_ORDER)
        if '/v2/orders/' in url and method == 'DELETE':
            return _Resp(204, None)
        return _Resp(404, {'message': 'not found'})
    monkeypatch.setattr(alpaca.requests, 'request', fake_request)

    c = alpaca.AlpacaClient('paper-api.alpaca.markets/v2/', key=KEY, secret=SECRET)
    assert c.base == 'https://paper-api.alpaca.markets' and c.paper
    assert c.get_account()['equity'] == '10250.5'
    assert calls[-1]['headers']['APCA-API-KEY-ID'] == KEY and calls[-1]['timeout']
    c.submit_order('btc/usd', 'buy', notional=25, client_order_id='coid-1')
    body = calls[-1]['json']
    assert body == {'symbol': 'BTC/USD', 'side': 'buy', 'type': 'market', 'time_in_force': 'gtc',
                    'notional': '25.00', 'client_order_id': 'coid-1'}
    c.submit_order('AAPL', 'sell', qty=1.5, order_type='limit', limit_price=190.1)
    body = calls[-1]['json']
    assert body['qty'] == '1.5' and body['limit_price'] == '190.1' and body['time_in_force'] == 'day'
    assert c.cancel_order('abc') == {}
    with pytest.raises(alpaca.AlpacaError) as ei:
        c.get_order('nope')
    assert ei.value.status == 404

    t = alpaca.AlpacaClient(alpaca.LIVE_BASE, token='tok-123')
    t.get_account()
    assert calls[-1]['headers']['Authorization'] == 'Bearer tok-123'
    assert 'APCA-API-KEY-ID' not in calls[-1]['headers'] and not t.paper


def test_alpaca_errors_and_base_whitelist(monkeypatch):
    from brokerage import alpaca
    monkeypatch.setattr(alpaca.requests, 'request',
                        lambda *a, **k: _Resp(401, {'code': 40110000, 'message': 'request is not authorized'}))
    c = alpaca.AlpacaClient(alpaca.PAPER_BASE, key=KEY, secret=SECRET)
    with pytest.raises(alpaca.AlpacaError) as ei:
        c.get_account()
    assert ei.value.status == 401 and SECRET not in str(ei.value) and KEY not in str(ei.value)
    with pytest.raises(ValueError):
        alpaca.norm_base('https://evil.example.com')
    with pytest.raises(ValueError):
        alpaca.AlpacaClient('https://api.alpaca.markets.evil.com', key=KEY, secret=SECRET)
    assert alpaca.is_crypto('ETH/USD') and not alpaca.is_crypto('NVDA')


def test_oauth_authorize_url_and_exchange(monkeypatch):
    from brokerage import alpaca
    monkeypatch.setenv('ALPACA_OAUTH_CLIENT_ID', 'cid-1')
    monkeypatch.setenv('ALPACA_OAUTH_CLIENT_SECRET', 'csecret-1')
    monkeypatch.setenv('ALPACA_OAUTH_REDIRECT_URI', 'https://app.example.com/api/brokerage/oauth/callback')
    url = alpaca.oauth_authorize_url('st.sig', 'paper')
    assert url.startswith('https://app.alpaca.markets/oauth/authorize?')
    assert 'scope=account:write%20trading' in url
    q = parse_qs(urlparse(url).query)
    assert q['response_type'] == ['code'] and q['client_id'] == ['cid-1'] and q['env'] == ['paper']
    assert q['redirect_uri'] == ['https://app.example.com/api/brokerage/oauth/callback'] and q['state'] == ['st.sig']
    assert 'env=' not in alpaca.oauth_authorize_url('s', 'live')

    seen = {}

    def fake_post(url, data=None, timeout=None, headers=None):
        seen.update({'url': url, 'data': data, 'headers': headers})
        if data['code'] == 'good':
            return _Resp(200, {'access_token': '79500537-5796-4230-9661-7f7108877c60', 'token_type': 'bearer',
                               'scope': 'account:write trading'})
        if data['code'] == 'weird':
            return _Resp(200, {'token_type': 'bearer'})
        return _Resp(401, {'error': 'invalid_grant', 'error_description': 'code expired'})
    monkeypatch.setattr(alpaca.requests, 'post', fake_post)
    tok = alpaca.oauth_exchange('good')
    assert tok['access_token'].startswith('79500537') and tok['scope'] == 'account:write trading'
    assert seen['url'] == 'https://api.alpaca.markets/oauth/token'
    assert seen['data']['grant_type'] == 'authorization_code' and seen['data']['client_secret'] == 'csecret-1'
    assert seen['headers']['Content-Type'] == 'application/x-www-form-urlencoded'
    with pytest.raises(alpaca.AlpacaError) as ei:
        alpaca.oauth_exchange('bad')
    assert 'code expired' in str(ei.value) and 'csecret-1' not in str(ei.value)
    with pytest.raises(alpaca.AlpacaError):
        alpaca.oauth_exchange('weird')


# ════════════════════════════════════════════════════════════════════════════
# 3. Controles de riesgo (unitarios, sin base)
# ════════════════════════════════════════════════════════════════════════════
def _ctx(**over):
    ctx = {
        'client': {'status': 'active', 'mode': 'paper', 'live_enabled': False, 'connected': True,
                   'risk_profile': 'moderado', 'risk_limits': {}, 'mandate': {}, 'hwm_equity': None},
        'order': {'symbol': 'NVDA', 'side': 'buy', 'notional': 500.0, 'qty': None, 'order_type': 'market'},
        'account': {'equity': 10000.0, 'cash': 10000.0, 'buying_power': 10000.0},
        'account_error': None, 'positions': [], 'price': 100.0, 'est_usd': 500.0,
        'daily_used_usd': 0.0, 'recent_duplicate': False, 'market_open': True, 'clock_source': 'alpaca',
    }
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(ctx.get(k), dict):
            ctx[k] = dict(ctx[k], **v)
        else:
            ctx[k] = v
    return ctx


def _by(checks):
    return {c['name']: c for c in checks}


def test_risk_happy_path_all_ok(monkeypatch):
    from brokerage import risk
    monkeypatch.delenv('BROKERAGE_TRADING_ENABLED', raising=False)
    ch = risk.run_checks(_ctx())
    assert not risk.is_blocked(ch), [c for c in ch if not c['ok']]
    names = set(_by(ch))
    for n in ('kill_switch', 'mode', 'client_status', 'account', 'symbol', 'restricted', 'order_size',
              'daily_limit', 'buying_power', 'position_limit', 'drawdown_stop', 'duplicate', 'market_hours'):
        assert n in names, n
    assert all(c['detail'] and c.get('detail_en') for c in ch)


def test_risk_each_block(monkeypatch):
    from brokerage import risk
    monkeypatch.delenv('BROKERAGE_TRADING_ENABLED', raising=False)
    monkeypatch.delenv('BROKERAGE_LIVE_ENABLED', raising=False)

    def blocked_by(name, **over):
        ch = _by(risk.run_checks(_ctx(**over)))
        assert ch[name]['ok'] is False, (name, ch[name])
        assert risk.is_blocked(list(ch.values()))

    monkeypatch.setenv('BROKERAGE_TRADING_ENABLED', 'off')
    blocked_by('kill_switch')
    monkeypatch.setenv('BROKERAGE_TRADING_ENABLED', 'on')
    # dinero real: sin env → bloqueado; env sin cliente → bloqueado; ambos → ok
    blocked_by('mode', client={'mode': 'live', 'live_enabled': True})
    monkeypatch.setenv('BROKERAGE_LIVE_ENABLED', 'on')
    blocked_by('mode', client={'mode': 'live', 'live_enabled': False})
    assert _by(risk.run_checks(_ctx(client={'mode': 'live', 'live_enabled': True})))['mode']['ok']
    monkeypatch.delenv('BROKERAGE_LIVE_ENABLED')
    blocked_by('client_status', client={'status': 'paused'})
    blocked_by('account', client={'connected': False})
    blocked_by('account', account_error='Alpaca HTTP 401')
    blocked_by('symbol', order={'symbol': 'NV DA'})
    blocked_by('symbol', order={'symbol': 'BTC/XYZ'})
    blocked_by('symbol', order={'symbol': 'BTC/USD'}, client={'risk_profile': 'conservador'})   # sin cripto
    blocked_by('restricted', client={'mandate': {'restricted_symbols': ['NVDA']}})
    blocked_by('restricted', client={'mandate': {'allowed_symbols': ['AAPL', 'MSFT']}})
    blocked_by('order_size', est_usd=6000.0)                     # moderado: máx US$5.000
    blocked_by('order_size', est_usd=0.5)
    blocked_by('order_size', est_usd=None)
    blocked_by('order_size', est_usd=800.0, client={'risk_limits': {'max_order_usd': 700}})
    blocked_by('daily_limit', daily_used_usd=14800.0)            # moderado: US$15.000/día
    blocked_by('buying_power', account={'buying_power': 100.0})
    blocked_by('position_limit', positions=[{'symbol': 'NVDA', 'qty': 20, 'market_value': 1800.0}])  # 23 % > 20 %
    blocked_by('drawdown_stop', client={'hwm_equity': 20000.0})   # 50 % de caída > 20 %
    blocked_by('duplicate', recent_duplicate=True)
    blocked_by('holdings', order={'side': 'sell'})               # sin posición → no cortos
    blocked_by('holdings', order={'side': 'sell', 'qty': 5, 'notional': None},
               positions=[{'symbol': 'NVDA', 'qty': 2, 'market_value': 200.0}])


def test_risk_warn_and_sell_allowed_in_drawdown(monkeypatch):
    from brokerage import risk
    monkeypatch.delenv('BROKERAGE_TRADING_ENABLED', raising=False)
    ch = _by(risk.run_checks(_ctx(market_open=False)))
    assert ch['market_hours']['ok'] is True and ch['market_hours']['warn'] is True
    assert not risk.is_blocked(list(ch.values()))
    # en caída fuerte se puede VENDER
    ch = risk.run_checks(_ctx(client={'hwm_equity': 20000.0}, order={'side': 'sell', 'notional': 100.0},
                              positions=[{'symbol': 'NVDA', 'qty': 5, 'market_value': 500.0}], est_usd=100.0))
    assert not risk.is_blocked(ch), [c for c in ch if not c['ok']]
    # cripto: sin aviso de horario; posición de Alpaca 'BTCUSD' casa con 'BTC/USD'
    ch = _by(risk.run_checks(_ctx(order={'symbol': 'BTC/USD', 'side': 'sell', 'notional': 50.0}, est_usd=50.0,
                                  positions=[{'symbol': 'BTCUSD', 'qty': 0.01, 'market_value': 600.0}])))
    assert 'market_hours' not in ch and ch['holdings']['ok']


def test_risk_profiles_and_limits():
    from brokerage import risk
    lim = risk.effective_limits('conservador', {'max_order_usd': 250, 'max_daily_usd': ''})
    assert lim['max_order_usd'] == 250 and lim['max_daily_usd'] == 2500 and lim['max_position_pct'] == 10
    assert risk.effective_limits('agresivo', {'max_order_usd': 10 ** 9})['max_order_usd'] == risk.HARD_MAX_ORDER_USD
    m = risk.effective_mandate('moderado', {'restricted_symbols': 'tsla, gme', 'allowed_asset_classes': ['crypto']})
    assert m['restricted_symbols'] == ['GME', 'TSLA'] and m['allowed_asset_classes'] == ['crypto']


# ════════════════════════════════════════════════════════════════════════════
# 4. Servicio con base de datos
# ════════════════════════════════════════════════════════════════════════════
@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    import brokerage.models  # noqa: F401
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    yield
    Base.metadata.drop_all(engine)


def _gen_key():
    try:
        from cryptography.fernet import Fernet
        return Fernet.generate_key().decode()
    except Exception:  # noqa: BLE001
        return ''


_FERNET_KEY = _gen_key()


@pytest.fixture
def env(monkeypatch):
    for k in ('BROKERAGE_TRADING_ENABLED', 'BROKERAGE_LIVE_ENABLED', 'BROKERAGE_AUTO_APPROVE_PAPER',
              'ALPACA_KEY', 'ALPACA_SECRET', 'ALPACA_BASE', 'ALPACA_OAUTH_CLIENT_ID',
              'ALPACA_OAUTH_CLIENT_SECRET', 'ALPACA_OAUTH_REDIRECT_URI'):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv('BROKERAGE_ENC_KEY', _FERNET_KEY)
    return monkeypatch


@pytest.fixture
def fakes(env):
    """Un FakeAlpaca por cliente (se crea al primer uso)."""
    from brokerage import service
    table = {}

    def factory(rec):
        if rec.id not in table:
            table[rec.id] = FakeAlpaca(paper=rec.mode != 'live')
        return table[rec.id]
    env.setattr(service, 'make_alpaca', factory)
    return table


def _new_client(s, name='Ana Test', **kw):
    from brokerage import service
    r = service.create_client(s, name, email='ana@example.com', actor='pytest', **kw)
    assert r['ok'], r
    cid = r['client']['id']
    r = service.set_credentials(s, cid, KEY, SECRET, env=kw.get('mode', 'paper'), actor='pytest')
    assert r['ok'] and r['verified'] is True, r
    return cid


@needs_db
def test_client_crud_and_no_secret_leak(db, fakes):
    from ontology.db import session_scope
    from brokerage import service
    from brokerage.models import BrokerClient
    with session_scope() as s:
        cid = _new_client(s)
    with session_scope() as s:
        c = service.get_client(s, cid)
        blob = json.dumps(service.list_clients(s)) + json.dumps(c)
        assert SECRET not in blob and KEY not in blob
        assert c['credentials_hint'] == '****ABCD' and c['connected'] and c['paper'] and c['mode'] == 'paper'
        assert 'enc_credentials' not in blob
        raw = s.get(BrokerClient, cid).enc_credentials
        assert SECRET not in raw and KEY not in raw
        assert service.get_client(s, 'ana test')['id'] == cid          # también por nombre
        r = service.update_client(s, cid, {'risk_profile': 'conservador', 'limits': {'max_order_usd': 300},
                                          'mandate': {'restricted_symbols': ['gme']}}, actor='pytest')
        assert r['ok'] and r['client']['limits']['max_order_usd'] == 300
        assert r['client']['mandate']['restricted_symbols'] == ['GME']
        assert r['client']['mandate']['max_position_pct'] == 10       # el comité lo lee del mandato
        assert not service.update_client(s, cid, {'limits': {'max_order_usd': -5}})['ok']
        assert not service.update_client(s, cid, {'risk_profile': 'yolo'})['ok']
        assert not service.update_client(s, cid, {'mode': 'live'})['ok']   # conectado: hay que reconectar
        assert service.pause_client(s, cid, 'pytest')['client']['status'] == 'paused'
        assert service.resume_client(s, cid, 'pytest')['client']['status'] == 'active'
        acts = [a['action'] for a in service.list_audit(s, client_id=cid)]
        assert 'client_created' in acts and 'credentials_set' in acts and 'client_updated' in acts
        assert SECRET not in json.dumps(service.list_audit(s))


@needs_db
def test_real_make_alpaca_decrypts_per_auth_type(db, env):
    """El make_alpaca REAL: claves descifradas (paper/live) y token OAuth como Bearer."""
    from ontology.db import session_scope
    from brokerage import alpaca, crypto, service
    from brokerage.models import BrokerClient
    with session_scope() as s:
        cid = service.create_client(s, 'Real Factory', actor='pytest')['client']['id']
        assert service.set_credentials(s, cid, KEY, SECRET, env='live', actor='pytest', verify=False)['ok']
        rec = s.get(BrokerClient, cid)
        cli = service.make_alpaca(rec)
        assert isinstance(cli, alpaca.AlpacaClient) and cli.key == KEY and cli.secret == SECRET
        assert cli.base == alpaca.LIVE_BASE and not cli.paper and rec.mode == 'live'
        rec.enc_credentials, rec.auth_type, rec.mode, rec.base_url = (
            crypto.encrypt_json({'token': 'tok-xyz'}), 'oauth', 'paper', alpaca.PAPER_BASE)
        cli = service.make_alpaca(rec)
        assert cli.token == 'tok-xyz' and cli.paper and cli._headers()['Authorization'] == 'Bearer tok-xyz'
        rec.enc_credentials = None
        with pytest.raises(alpaca.AlpacaError):
            service.make_alpaca(rec)
        # sin conexión: la previsualización se bloquea con un control claro (no revienta)
        p = service.preview_order(s, cid, 'NVDA', 'buy', notional=10)
        assert p['blocked'] and any(c['name'] == 'account' and not c['ok'] for c in p['checks'])


@needs_db
def test_credentials_rejected_are_not_stored(db, env):
    from ontology.db import session_scope
    from brokerage import alpaca, service

    class Bad:
        def get_account(self):
            raise alpaca.AlpacaError('Alpaca HTTP 401', status=401)
    env.setattr(service, 'make_alpaca', lambda rec: Bad())
    with session_scope() as s:
        cid = service.create_client(s, 'Rechazo', actor='pytest')['client']['id']
        r = service.set_credentials(s, cid, KEY, SECRET, env='paper', actor='pytest')
        assert not r['ok'] and r['verified'] is False
        assert not service.get_client(s, cid)['connected']


@needs_db
def test_preview_confirm_happy_path(db, fakes):
    from ontology.db import session_scope
    from brokerage import service
    with session_scope() as s:
        cid = _new_client(s, 'Happy')
        p = service.preview_order(s, cid, 'nvda', 'buy', notional=500, requested_by='pytest')
    assert p['ok'] and not p['blocked'] and p['status'] == 'previewed' and not p['requires_human_approval']
    assert p['summary_es'].startswith('🧪 PAPEL') and 'NVDA' in p['summary_es'] and p['summary_en']
    assert p['expires_at'] and p['preview_id'] and p['est_usd'] == 500
    with session_scope() as s:
        r = service.confirm_order(s, p['preview_id'], 'pytest', source='ui')
    assert r['ok'], r
    o = r['order']
    assert o['status'] == 'submitted' and o['alpaca_order_id'] == 'alp-1' and o['submitted_at']
    fake = fakes[cid]
    assert fake.submits[0]['client_order_id'] == p['preview_id']      # idempotencia
    assert fake.submits[0]['notional'] == 500
    with session_scope() as s:
        acts = [a['action'] for a in service.list_audit(s, client_id=cid)]
        assert 'order_previewed' in acts and 'order_submitted' in acts
        # usada → no se puede volver a confirmar (Alpaca recibe UNA sola orden)
        again = service.confirm_order(s, p['preview_id'], 'pytest', source='ui')
    assert not again['ok'] and again['code'] == 'used' and len(fake.submits) == 1


@needs_db
def test_expired_preview(db, fakes):
    from ontology.db import session_scope
    from brokerage import service
    from brokerage.models import BrokerOrder
    with session_scope() as s:
        cid = _new_client(s, 'Expira')
        p = service.preview_order(s, cid, 'AAPL', 'buy', notional=100)
        s.get(BrokerOrder, p['preview_id']).expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    with session_scope() as s:
        r = service.confirm_order(s, p['preview_id'], 'pytest')
    assert not r['ok'] and r['status'] == 'expired'
    assert fakes[cid].submits == []


@needs_db
def test_blocked_preview_and_recheck_at_confirm(db, fakes):
    from ontology.db import session_scope
    from brokerage import service
    with session_scope() as s:
        cid = _new_client(s, 'Bloqueo')
        p = service.preview_order(s, cid, 'NVDA', 'buy', notional=9000)       # > US$5.000 (moderado)
    assert p['ok'] and p['blocked'] and p['status'] == 'rejected' and 'BLOQUEADA' in p['summary_es']
    with session_scope() as s:
        assert not service.confirm_order(s, p['preview_id'], 'pytest')['ok']
        ok = service.preview_order(s, cid, 'NVDA', 'buy', notional=100)
    # el interruptor se apaga ENTRE la previsualización y la confirmación → no se envía
    fakes_env = fakes[cid]
    os.environ['BROKERAGE_TRADING_ENABLED'] = 'off'
    try:
        with session_scope() as s:
            r = service.confirm_order(s, ok['preview_id'], 'pytest')
    finally:
        os.environ.pop('BROKERAGE_TRADING_ENABLED', None)
    assert not r['ok'] and r['status'] == 'rejected' and 'Interruptor' in r['error']
    assert fakes_env.submits == []


@needs_db
def test_live_gating(db, fakes):
    from ontology.db import session_scope
    from brokerage import service
    with session_scope() as s:
        cid = _new_client(s, 'Real', mode='live')
        c = service.get_client(s, cid)
        assert c['mode'] == 'live' and not c['paper'] and not c['live_enabled']
        p = service.preview_order(s, cid, 'MSFT', 'buy', notional=100)
        assert p['blocked'] and p['summary_es'].startswith('🔴 DINERO REAL')
        assert not service.update_client(s, cid, {'live_enabled': True})['ok']       # falta confirm_live
        assert service.update_client(s, cid, {'live_enabled': True, 'confirm_live': True}, 'pytest')['ok']
        p = service.preview_order(s, cid, 'MSFT', 'buy', notional=100)
        assert p['blocked']                                  # sigue: falta BROKERAGE_LIVE_ENABLED=on
    os.environ['BROKERAGE_LIVE_ENABLED'] = 'on'
    try:
        with session_scope() as s:
            p = service.preview_order(s, cid, 'MSFT', 'buy', notional=100)
            assert not p['blocked'], p['checks']
            assert service.confirm_order(s, p['preview_id'], 'pytest')['ok']
    finally:
        os.environ.pop('BROKERAGE_LIVE_ENABLED', None)


@needs_db
def test_approval_queue_for_mcp_and_committee(db, fakes):
    from ontology.db import session_scope
    from brokerage import service
    with session_scope() as s:
        cid = _new_client(s, 'Cola')
        pm = service.preview_order(s, cid, 'AMD', 'buy', notional=200, source='mcp', requested_by='agent:gpt',
                                   rationale='tesis X')
        pc = service.preview_order(s, cid, 'TSM', 'buy', notional=300, source='committee', requested_by='fab',
                                   proposal_id='memo-123')
    for p in (pm, pc):
        assert p['ok'] and p['status'] == 'pending_approval' and p['requires_human_approval'], p
        assert 'aprobación humana' in p['summary_es']
    with session_scope() as s:
        # el agente NO puede ejecutar lo que propuso
        r = service.confirm_order(s, pm['preview_id'], 'agent:gpt', source='mcp')
        assert not r['ok'] and r['error'] == 'requires human approval' and r['status'] == 'pending_approval'
        r = service.confirm_order(s, pc['preview_id'], 'committee', source='committee')
        assert not r['ok'] and r['status'] == 'pending_approval'
        # un agente tampoco puede confirmar una previsualización hecha por una persona en la app
        ui = service.preview_order(s, cid, 'AMD', 'sell', notional=10)
        r = service.confirm_order(s, ui['preview_id'], 'agent:gpt', source='mcp')
        assert not r['ok'] and r['code'] == 'source_mismatch'
        q = service.pending_approvals(s)
        ids = {a['preview_id'] for a in q}
        assert {pm['preview_id'], pc['preview_id']} <= ids
        assert all(a['client_name'] == 'Cola' for a in q if a['client_id'] == cid)
    assert fakes[cid].submits == []
    with session_scope() as s:
        assert not service.approve_preview(s, pm['preview_id'], '')['ok']       # quién aprueba: obligatorio
        a = service.approve_preview(s, pm['preview_id'], 'Fabrizio')
        assert a['ok'] and a['order']['status'] == 'submitted' and a['order']['approved_by'] == 'Fabrizio'
        rj = service.reject_preview(s, pc['preview_id'], 'Fabrizio', reason='no ahora')
        assert rj['ok'] and rj['status'] == 'rejected'
        assert not service.approve_preview(s, pc['preview_id'], 'Fabrizio')['ok']
        assert {a['preview_id'] for a in service.pending_approvals(s)}.isdisjoint({pm['preview_id'], pc['preview_id']})
        acts = [a['action'] for a in service.list_audit(s, client_id=cid)]
        assert 'confirm_denied' in acts and 'order_approved' in acts and 'order_rejected' in acts
    assert len(fakes[cid].submits) == 1


@needs_db
def test_auto_approve_paper_only(db, fakes):
    from ontology.db import session_scope
    from brokerage import service
    os.environ['BROKERAGE_AUTO_APPROVE_PAPER'] = 'on'
    try:
        with session_scope() as s:
            cid = _new_client(s, 'Auto')
            p = service.preview_order(s, cid, 'AMD', 'buy', notional=50, source='mcp')
            assert p['status'] == 'previewed' and not p['requires_human_approval']
            assert service.confirm_order(s, p['preview_id'], 'agent', source='mcp')['ok']
            live = _new_client(s, 'AutoLive', mode='live')
            p = service.preview_order(s, live, 'AMD', 'buy', notional=50, source='mcp')
            assert p['requires_human_approval']          # dinero real: SIEMPRE humano
    finally:
        os.environ.pop('BROKERAGE_AUTO_APPROVE_PAPER', None)


@needs_db
def test_idempotent_client_order_id_on_timeout(db, fakes):
    from ontology.db import session_scope
    from brokerage import service
    with session_scope() as s:
        cid = _new_client(s, 'Timeout')
        p = service.preview_order(s, cid, 'INTC', 'buy', notional=120)
    fake = fakes[cid]
    fake.timeout_after_accept = True          # Alpaca aceptó pero la respuesta se perdió
    with session_scope() as s:
        r = service.confirm_order(s, p['preview_id'], 'pytest')
    assert r['ok'] and r['order']['alpaca_order_id'] == 'alp-1', r
    assert len(fake.orders) == 1
    # reintento de envío tras una caída (fila quedó 'approved'): Alpaca rechaza el
    # client_order_id repetido y se adopta la orden existente → nunca 2 órdenes
    from brokerage.models import BrokerOrder
    fake.timeout_after_accept = False
    fake.positions = [{'symbol': 'INTC', 'qty': '3', 'market_value': '90', 'current_price': '30'}]
    with session_scope() as s:
        p2 = service.preview_order(s, cid, 'INTC', 'sell', qty=1)
        assert not p2['blocked'], p2['checks']
    fake.by_coid[p2['preview_id']] = {'id': 'alp-pre', 'client_order_id': p2['preview_id'], 'status': 'filled',
                                      'filled_qty': '1', 'filled_avg_price': '30.1'}
    fake.orders['alp-pre'] = fake.by_coid[p2['preview_id']]
    with session_scope() as s:
        s.get(BrokerOrder, p2['preview_id']).status = 'approved'
    with session_scope() as s:
        r = service.confirm_order(s, p2['preview_id'], 'pytest')
    assert r['ok'] and r['order']['alpaca_order_id'] == 'alp-pre' and r['order']['status'] == 'filled'
    assert r['order']['filled_avg_price'] == 30.1


@needs_db
def test_duplicate_and_daily_limit_through_service(db, fakes):
    from ontology.db import session_scope
    from brokerage import service
    with session_scope() as s:
        cid = _new_client(s, 'Duplicado')
        p = service.preview_order(s, cid, 'ORCL', 'buy', notional=100)
        assert service.confirm_order(s, p['preview_id'], 'pytest')['ok']
        d = service.preview_order(s, cid, 'ORCL', 'buy', notional=100)
        assert d['blocked'] and any(c['name'] == 'duplicate' and not c['ok'] for c in d['checks'])
        service.update_client(s, cid, {'limits': {'max_daily_usd': 150}}, 'pytest')
        d = service.preview_order(s, cid, 'IBM', 'buy', notional=100)
        assert d['blocked'] and any(c['name'] == 'daily_limit' and not c['ok'] for c in d['checks'])


@needs_db
def test_cancel_and_sync(db, fakes):
    from ontology.db import session_scope
    from brokerage import service
    with session_scope() as s:
        cid = _new_client(s, 'Sync')
        a = service.preview_order(s, cid, 'QCOM', 'buy', notional=100)
        oa = service.confirm_order(s, a['preview_id'], 'pytest')['order']
        b = service.preview_order(s, cid, 'AVGO', 'buy', notional=100)
        ob = service.confirm_order(s, b['preview_id'], 'pytest')['order']
        pend = service.preview_order(s, cid, 'MU', 'buy', notional=100, source='mcp')
    fake = fakes[cid]
    fake.orders[oa['alpaca_order_id']].update({'status': 'filled', 'filled_qty': '0.5', 'filled_avg_price': '200'})
    with session_scope() as s:
        r = service.sync_orders(s, cid, actor='pytest')
        assert r['ok'] and r['checked'] == 2 and r['updated'] == 1
        c = service.cancel_order(s, ob['id'], 'pytest')
        assert c['ok'] and c['status'] == 'canceled' and fake.orders[ob['alpaca_order_id']]['status'] == 'canceled'
        bad = service.cancel_order(s, oa['id'], 'pytest')
        assert not bad['ok'] and bad['status'] == 'filled'
        pc = service.cancel_order(s, pend['preview_id'], 'pytest')
        assert pc['ok'] and pc['status'] == 'canceled'
        orders = service.list_orders(s, client_id=cid)
        st = {o['id']: o['status'] for o in orders}
        assert st[oa['id']] == 'filled' and st[ob['id']] == 'canceled'
        assert service.list_orders(s, client_id=cid, status='filled')[0]['filled_avg_price'] == 200


@needs_db
def test_account_snapshot_and_hwm(db, fakes):
    from ontology.db import session_scope
    from brokerage import service
    with session_scope() as s:
        cid = _new_client(s, 'Snapshot')
    fake = fakes[cid]
    fake.positions = [{'symbol': 'NVDA', 'qty': '2', 'avg_entry_price': '100', 'current_price': '110',
                       'market_value': '220', 'unrealized_pl': '20', 'unrealized_plpc': '0.1', 'side': 'long'}]
    with session_scope() as s:
        snap = service.account_snapshot(s, cid)
    assert snap['ok'] and snap['account']['equity'] == 10000.0 and snap['account']['paper'] is True
    assert snap['positions'][0]['unrealized_plpc'] == 0.1 and snap['client']['hwm_equity'] == 10000.0
    fake.account['equity'] = '7000'
    with session_scope() as s:
        snap = service.account_snapshot(s, cid)
        assert snap['client']['hwm_equity'] == 10000.0 and round(snap['client']['drawdown_pct']) == 30
        p = service.preview_order(s, cid, 'AMD', 'buy', notional=100)
        assert any(c['name'] == 'drawdown_stop' and not c['ok'] for c in p['checks'])
        assert service.update_client(s, cid, {'reset_hwm': True}, 'pytest')['client']['hwm_equity'] is None


@needs_db
def test_house_client_from_env(db, env):
    from ontology.db import session_scope
    from brokerage import service
    env.setenv('ALPACA_KEY', 'PKHOUSEKEY7777')
    env.setenv('ALPACA_SECRET', 'house-secret-zzz')
    env.setenv('ALPACA_BASE', 'https://paper-api.alpaca.markets/v2/')
    with session_scope() as s:
        rows = service.list_clients(s)
        rows2 = service.list_clients(s)               # idempotente
    house = [c for c in rows if c['id'] == 'house']
    assert len(house) == 1 and len([c for c in rows2 if c['id'] == 'house']) == 1
    h = house[0]
    assert h['name'] == 'Cuenta principal' and h['auth_type'] == 'env' and h['connected'] and h['mode'] == 'paper'
    assert 'house-secret-zzz' not in json.dumps(rows) and 'PKHOUSEKEY7777' not in json.dumps(rows)
    with session_scope() as s:
        assert not service.set_credentials(s, 'house', KEY, SECRET)['ok']
        assert not service.update_client(s, 'house', {'mode': 'live'})['ok']
        cli = service.make_alpaca(s.get(__import__('brokerage.models', fromlist=['BrokerClient']).BrokerClient,
                                        'house'))
        assert cli.key == 'PKHOUSEKEY7777' and cli.paper


@needs_db
def test_oauth_state_flow(db, fakes):
    from ontology.db import session_scope
    from brokerage import alpaca, service
    from brokerage.models import BrokerClient, BrokerOAuthState
    with session_scope() as s:
        cid = service.create_client(s, 'OAuth Persona', actor='pytest')['client']['id']
        assert not service.oauth_start(s, cid)['ok']                     # sin configurar
    fakes_env = os.environ
    fakes_env['ALPACA_OAUTH_CLIENT_ID'] = 'cid'
    fakes_env['ALPACA_OAUTH_CLIENT_SECRET'] = 'csec'
    fakes_env['ALPACA_OAUTH_REDIRECT_URI'] = 'https://x.example.com/api/brokerage/oauth/callback'
    try:
        calls = []

        def fake_exchange(code):
            calls.append(code)
            if code == 'bad':
                raise alpaca.AlpacaError('canje OAuth rechazado (HTTP 401): invalid_grant', status=401)
            return {'access_token': 'oauth-token-SECRET-1234', 'token_type': 'bearer', 'scope': 'account:write trading'}
        orig = alpaca.oauth_exchange
        alpaca.oauth_exchange = fake_exchange
        with session_scope() as s:
            st = service.oauth_start(s, cid, env='paper', actor='pytest')
        assert st['ok'] and 'env=paper' in st['url']
        state = parse_qs(urlparse(st['url']).query)['state'][0]
        with session_scope() as s:
            # manipulado → inválido
            raw, sig = state.rsplit('.', 1)
            assert not service.oauth_callback(s, raw + '.' + 'f' * 32, 'good')['ok']
            assert not service.oauth_callback(s, 'basura', 'good')['ok']
        with session_scope() as s:
            r = service.oauth_callback(s, state, 'good')
        assert r['ok'] and r['client_id'] == cid and r['env'] == 'paper', r
        with session_scope() as s:
            rec = s.get(BrokerClient, cid)
            assert rec.auth_type == 'oauth' and rec.mode == 'paper' and 'oauth-token-SECRET' not in rec.enc_credentials
            c = service.get_client(s, cid)
            assert c['connected'] and 'oauth-token-SECRET' not in json.dumps(c)
            # reutilizar el mismo state → rechazado (un solo uso)
            assert 'ya se usó' in service.oauth_callback(s, state, 'good')['error']
        # state caducado
        with session_scope() as s:
            st2 = service.oauth_start(s, cid, env='live', actor='pytest')
            state2 = parse_qs(urlparse(st2['url']).query)['state'][0]
            s.get(BrokerOAuthState, state2).created_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        with session_scope() as s:
            assert 'caducó' in service.oauth_callback(s, state2, 'good')['error']
        # el usuario cancela en Alpaca / canje falla
        with session_scope() as s:
            st3 = service.oauth_start(s, cid, env='paper')
            state3 = parse_qs(urlparse(st3['url']).query)['state'][0]
            assert not service.oauth_callback(s, state3, None, error='access_denied')['ok']
            st4 = service.oauth_start(s, cid, env='paper')
            state4 = parse_qs(urlparse(st4['url']).query)['state'][0]
            assert 'invalid_grant' in service.oauth_callback(s, state4, 'bad')['error']
        assert calls == ['good', 'bad']
        # el cliente OAuth usa el token como Bearer
        with session_scope() as s:
            service.make_alpaca  # (sustituido por el fake en este test)
            from brokerage.service import _crypto
            assert _crypto.decrypt_json(s.get(BrokerClient, cid).enc_credentials)['token'] == 'oauth-token-SECRET-1234'
    finally:
        alpaca.oauth_exchange = orig
        for k in ('ALPACA_OAUTH_CLIENT_ID', 'ALPACA_OAUTH_CLIENT_SECRET', 'ALPACA_OAUTH_REDIRECT_URI'):
            fakes_env.pop(k, None)


@needs_db
def test_committee_proposal_executes_after_approval(db, fakes):
    """source='committee' con proposal_id: tras aprobar se intenta marcar el memo
    (research.committee es opcional; un memo inexistente no rompe nada)."""
    from ontology.db import session_scope
    from brokerage import service
    with session_scope() as s:
        cid = _new_client(s, 'Comite')
        p = service.preview_order(s, cid, 'AAPL', 'buy', notional=100, source='committee', proposal_id='no-existe')
        r = service.approve_preview(s, p['preview_id'], 'Fabrizio')
    assert r['ok'] and r['order']['proposal_id'] == 'no-existe'


# ════════════════════════════════════════════════════════════════════════════
# 5. API (PIN, 503, sin secretos)
# ════════════════════════════════════════════════════════════════════════════
@pytest.fixture
def client(fakes):
    from flask import Flask
    from core import http as core_http
    from brokerage import api as bk_api
    from brokerage.api import brokerage_bp
    core_http._rate_buckets.clear()
    bk_api._PIN_FAILS.clear()
    bk_api._PIN_GLOBAL.clear()
    bk_api._PIN_STATE['global_audited_at'] = 0.0
    app = Flask('bk-test')
    app.register_blueprint(brokerage_bp)
    return app.test_client()


@needs_db
def test_api_pin_semantics(db, client, env):
    env.delenv('TRADE_PIN', raising=False)
    r = client.get('/api/brokerage/clients')
    assert r.status_code == 403 and r.get_json()['code'] == 'trading_disabled'
    env.setenv('TRADE_PIN', PIN)
    assert client.get('/api/brokerage/clients').status_code == 401
    assert client.get('/api/brokerage/clients', headers={'X-Trade-Pin': 'nope'}).status_code == 401
    assert client.post('/api/brokerage/orders/preview', json={}).status_code == 401
    assert client.get('/api/brokerage/clients', headers={'X-Trade-Pin': PIN}).status_code == 200
    st = client.get('/api/brokerage/status').get_json()                     # sin PIN: lo mínimo
    assert set(st) == {'available', 'trading_enabled'} and st['available'] and st['trading_enabled']
    assert client.get('/api/brokerage/status/detail').status_code == 401     # la postura de seguridad, con PIN
    d = client.get('/api/brokerage/status/detail', headers={'X-Trade-Pin': PIN}).get_json()
    assert not d['live_enabled_env'] and d['pin_set'] and d['encryption']['key_source'] == 'env'
    assert d['encryption']['can_store_credentials'] and 'profiles' in d and SECRET not in json.dumps(d)


@needs_db
def test_api_full_flow(db, client, env):
    env.setenv('TRADE_PIN', PIN)
    H = {'X-Trade-Pin': PIN}
    r = client.post('/api/brokerage/clients', json={'name': 'API Persona', 'risk_profile': 'agresivo',
                                                    'actor': 'pytest'}, headers=H)
    assert r.status_code == 201, r.get_json()
    cid = r.get_json()['client']['id']
    r = client.post(f'/api/brokerage/clients/{cid}/credentials',
                    json={'api_key': KEY, 'api_secret': SECRET, 'env': 'paper'}, headers=H)
    assert r.status_code == 200 and SECRET not in r.get_data(as_text=True) and KEY not in r.get_data(as_text=True)
    for path in ('/api/brokerage/clients', f'/api/brokerage/clients/{cid}', f'/api/brokerage/clients/{cid}/account',
                 f'/api/brokerage/clients/{cid}/audit', '/api/brokerage/audit'):
        body = client.get(path, headers=H).get_data(as_text=True)
        assert SECRET not in body and KEY not in body, path
    r = client.patch(f'/api/brokerage/clients/{cid}', json={'limits': {'max_order_usd': 800}}, headers=H)
    assert r.status_code == 200 and r.get_json()['client']['limits']['max_order_usd'] == 800
    r = client.post('/api/brokerage/orders/preview', json={'client_id': cid, 'symbol': 'NVDA', 'side': 'buy',
                                                           'notional': 250}, headers=H)
    pv = r.get_json()
    assert r.status_code == 200 and pv['ok'] and pv['status'] == 'previewed'
    # sin la casilla "confirmo" → 400
    r = client.post(f'/api/brokerage/orders/{pv["preview_id"]}/confirm', json={}, headers=H)
    assert r.status_code == 400 and r.get_json()['code'] == 'confirmation_required'
    r = client.post(f'/api/brokerage/orders/{pv["preview_id"]}/confirm', json={'confirm': True, 'actor': 'pytest'},
                    headers=H)
    assert r.status_code == 200 and r.get_json()['order']['status'] == 'submitted'
    r = client.post(f'/api/brokerage/orders/{pv["preview_id"]}/confirm', json={'confirm': True}, headers=H)
    assert r.status_code == 409
    r = client.post('/api/brokerage/orders/preview', json={'client_id': cid, 'symbol': 'NVDA', 'side': 'hold',
                                                           'notional': 250}, headers=H)
    assert r.status_code == 400
    # propuesta de un agente → cola de aprobación
    from ontology.db import session_scope
    from brokerage import service
    with session_scope() as s:
        mp = service.preview_order(s, cid, 'AMD', 'buy', notional=100, source='mcp', requested_by='agent')
    ap = client.get('/api/brokerage/approvals', headers=H).get_json()['approvals']
    assert any(a['preview_id'] == mp['preview_id'] for a in ap)
    r = client.post(f'/api/brokerage/approvals/{mp["preview_id"]}/approve', json={'actor': 'Fabrizio'}, headers=H)
    assert r.status_code == 200 and r.get_json()['order']['status'] == 'submitted'
    r = client.post(f'/api/brokerage/approvals/{mp["preview_id"]}/reject', json={'actor': 'x'}, headers=H)
    assert r.status_code == 409
    orders = client.get(f'/api/brokerage/orders?client_id={cid}', headers=H).get_json()['orders']
    assert len(orders) >= 2
    r = client.post(f'/api/brokerage/clients/{cid}/sync', json={}, headers=H)
    assert r.status_code == 200 and r.get_json()['checked'] >= 2
    r = client.post(f'/api/brokerage/orders/{orders[0]["id"]}/cancel', json={}, headers=H)
    assert r.status_code == 200
    assert client.get('/api/brokerage/clients/nope', headers=H).status_code == 404


@needs_db
def test_api_oauth_callback_page(db, client, env):
    env.setenv('TRADE_PIN', PIN)
    r = client.get('/api/brokerage/oauth/callback?state=zzz.yyy&code=abc')
    assert r.status_code == 400 and 'text/html' in r.content_type
    assert 'No se pudo conectar' in r.get_data(as_text=True) and 'Could not connect' in r.get_data(as_text=True)
    r = client.post('/api/brokerage/clients/whatever/oauth/start', json={}, headers={'X-Trade-Pin': PIN})
    assert r.status_code == 400 and 'OAuth no configurado' in r.get_json()['error']


def test_api_without_database(monkeypatch):
    """Sin DATABASE_URL el blueprint responde 503 (y /status no se cae)."""
    from flask import Flask
    from core import http as core_http
    from brokerage import api
    core_http._rate_buckets.clear()
    monkeypatch.setattr(api, '_db_ok', lambda: False)
    monkeypatch.setenv('TRADE_PIN', PIN)
    app = Flask('bk-nodb')
    app.register_blueprint(api.brokerage_bp)
    c = app.test_client()
    r = c.get('/api/brokerage/clients', headers={'X-Trade-Pin': PIN})
    assert r.status_code == 503 and r.get_json()['code'] == 'no_database'
    assert c.get('/api/brokerage/status').status_code == 200


@needs_db
def test_api_pin_lockout(db, client, env):
    """10 PIN fallidos desde la misma IP → 429 (incluso con el PIN correcto) durante la ventana."""
    env.setenv('TRADE_PIN', PIN)
    for _ in range(10):
        assert client.get('/api/brokerage/approvals', headers={'X-Trade-Pin': '0000'}).status_code == 401
    r = client.get('/api/brokerage/approvals', headers={'X-Trade-Pin': PIN})
    assert r.status_code == 429 and r.get_json()['code'] == 'pin_locked'
    from brokerage import api as bk_api
    bk_api._PIN_FAILS.clear()
    bk_api._PIN_GLOBAL.clear()
    assert client.get('/api/brokerage/approvals', headers={'X-Trade-Pin': PIN}).status_code == 200


# ════════════════════════════════════════════════════════════════════════════
# 6. Correcciones de la revisión (2026-09-30)
# ════════════════════════════════════════════════════════════════════════════
@needs_db
def test_unknown_state_is_never_failed_and_blocks_retry(db, fakes):
    """Envío que se corta tras llegar a Alpaca + consulta por client_order_id
    también caída → NO 'failed' (un reintento duplicaría la orden real): queda
    'submitted'/'unknown', bloquea repetirla, cuenta en el diario y sync la adopta."""
    from ontology.db import session_scope
    from brokerage import service
    with session_scope() as s:
        cid = _new_client(s, 'Red Caida')
        p = service.preview_order(s, cid, 'NVDA', 'buy', notional=200)
    fake = fakes[cid]
    fake.timeout_after_accept, fake.lookup_down = True, True
    with session_scope() as s:
        r = service.confirm_order(s, p['preview_id'], 'pytest')
    assert not r['ok'] and r['code'] == 'unknown_state' and r['status'] == 'submitted', r
    assert r['order']['unknown'] and r['order']['alpaca_status'] == 'unknown' and r['error_en']
    assert len(fake.orders) == 1                                     # Alpaca SÍ la tiene
    fake.timeout_after_accept = False
    with session_scope() as s:
        assert service._daily_used(s, cid) == 200.0                  # cuenta en el límite diario
        again = service.preview_order(s, cid, 'NVDA', 'buy', notional=200)
        by = {c['name']: c for c in again['checks']}
        assert again['blocked'] and not by['unresolved']['ok'], again['checks']
        # sync con la red caída: error, nada cambia
        r = service.sync_orders(s, cid)
        assert not r['ok'] and r['checked'] == 1 and r['error_en']
    fake.lookup_down = False
    with session_scope() as s:
        r = service.sync_orders(s, cid, actor='pytest')
        assert r['ok'] and r['checked'] == 1 and r['updated'] == 1
        o = service.get_order(s, p['preview_id'])
        assert o['alpaca_order_id'] == 'alp-1' and o['status'] == 'submitted' and not o['unknown'] and not o['error']
        acts = [a['action'] for a in service.list_audit(s, client_id=cid)]
        assert 'order_unknown' in acts and 'order_reconciled' in acts
    assert len(fake.orders) == 1 and len(fake.submits) == 1          # nunca 2 órdenes


@needs_db
def test_unknown_state_never_reached_alpaca_becomes_failed_after_grace(db, fakes):
    from ontology.db import session_scope
    from brokerage import service
    from brokerage.models import BrokerOrder
    with session_scope() as s:
        cid = _new_client(s, 'Nunca Llego')
        p = service.preview_order(s, cid, 'AMD', 'buy', notional=100)
    fake = fakes[cid]
    fake.fail_before_accept, fake.lookup_down = True, True
    with session_scope() as s:
        r = service.confirm_order(s, p['preview_id'], 'pytest')
    assert r['code'] == 'unknown_state' and fake.orders == {}
    fake.fail_before_accept, fake.lookup_down = False, False
    with session_scope() as s:
        r = service.sync_orders(s, cid)                               # 404 pero muy reciente → espera
        assert r['ok'] and r['updated'] == 0
        assert service.get_order(s, p['preview_id'])['status'] == 'submitted'
        s.get(BrokerOrder, p['preview_id']).submitted_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    with session_scope() as s:
        r = service.sync_orders(s, cid)
        o = service.get_order(s, p['preview_id'])
        assert r['updated'] == 1 and o['status'] == 'failed' and 'nunca llegó' in o['error'] and o['error_en']
        # ya resuelta: se puede volver a intentar
        again = service.preview_order(s, cid, 'AMD', 'buy', notional=100)
        assert not any(c['name'] == 'unresolved' for c in again['checks'])
    # rechazo DEFINITIVO de Alpaca (4xx) → 'failed' de inmediato
    fake.reject_submit = 'Alpaca HTTP 403: insufficient buying power'
    with session_scope() as s:
        r = service.confirm_order(s, again['preview_id'], 'pytest')
    assert r['code'] == 'broker_rejected' and r['status'] == 'failed' and 'rejected' in r['error_en']


def test_definitive_reject_classification():
    from brokerage import alpaca, service
    E = alpaca.AlpacaError
    assert service._definitive_reject(E('Alpaca HTTP 403', status=403))
    assert service._definitive_reject(E('Alpaca HTTP 422: qty must be > 0', status=422))
    assert not service._definitive_reject(E('Alpaca HTTP 422: client_order_id must be unique', status=422))
    assert not service._definitive_reject(E('Alpaca no respondió a tiempo', network=True))
    assert not service._definitive_reject(E('Alpaca HTTP 503', status=503))
    assert not service._definitive_reject(E('respuesta no-JSON de Alpaca (HTTP 200)', status=200))


def test_risk_sells_skip_order_and_daily_caps(monkeypatch):
    """Vender para reducir riesgo no se frena por orden máx./diario máx. (hallazgos 3 y 19)."""
    from brokerage import risk
    monkeypatch.delenv('BROKERAGE_TRADING_ENABLED', raising=False)
    pos = [{'symbol': 'NVDA', 'qty': 80, 'market_value': 8000.0, 'current_price': 100.0}]
    ch = _by(risk.run_checks(_ctx(client={'risk_profile': 'conservador', 'hwm_equity': 20000.0},
                                  account={'equity': 8000.0, 'cash': 0.0, 'buying_power': 0.0},
                                  order={'side': 'sell', 'notional': 2000.0}, est_usd=2000.0,
                                  daily_used_usd=1000.0, positions=pos)))
    assert ch['order_size']['ok'] and ch['daily_limit']['ok'] and ch['holdings']['ok']
    assert not risk.is_blocked(list(ch.values()))
    # vender MÁS de lo que se tiene sigue bloqueado (sin cortos)
    ch = _by(risk.run_checks(_ctx(order={'side': 'sell', 'qty': 81, 'notional': None}, est_usd=8100.0,
                                  positions=pos, client={'risk_profile': 'conservador'})))
    assert not ch['holdings']['ok']
    # la compra equivalente sí se frena
    ch = _by(risk.run_checks(_ctx(client={'risk_profile': 'conservador'}, est_usd=2000.0)))
    assert not ch['order_size']['ok']


def test_risk_no_margin_by_default(monkeypatch):
    """Cuenta de margen de Alpaca: buying_power 2x con cash 0 → sin mandato allow_margin NO se compra."""
    from brokerage import risk
    monkeypatch.delenv('BROKERAGE_TRADING_ENABLED', raising=False)
    acct = {'equity': 10000.0, 'cash': 0.0, 'buying_power': 10000.0}
    ch = _by(risk.run_checks(_ctx(account=acct, est_usd=1500.0, order={'notional': 1500.0})))
    assert not ch['buying_power']['ok'] and 'sin préstamo' in ch['buying_power']['detail']
    ch = _by(risk.run_checks(_ctx(account=acct, est_usd=1500.0, order={'notional': 1500.0},
                                  client={'mandate': {'allow_margin': True}})))
    assert ch['buying_power']['ok']
    # cripto no es marginable: manda non_marginable_buying_power aunque el mandato permita margen
    acct = {'equity': 10000.0, 'cash': 5000.0, 'buying_power': 10000.0, 'non_marginable_buying_power': 800.0}
    for mandate in ({}, {'allow_margin': True}):
        ch = _by(risk.run_checks(_ctx(account=acct, est_usd=1000.0, client={'mandate': mandate},
                                      order={'symbol': 'BTC/USD', 'notional': 1000.0})))
        assert not ch['buying_power']['ok'], mandate
    assert risk.effective_mandate('moderado', {})['allow_margin'] is False


def test_risk_limit_price_deviation(monkeypatch):
    from brokerage import risk
    monkeypatch.delenv('BROKERAGE_TRADING_ENABLED', raising=False)
    pos = [{'symbol': 'NVDA', 'qty': 100, 'market_value': 9000.0, 'current_price': 90.0}]

    def lim(side, lp, ref=90.0):
        return _by(risk.run_checks(_ctx(order={'side': side, 'qty': 10, 'notional': None, 'order_type': 'limit',
                                               'limit_price': lp}, ref_price=ref, est_usd=10 * max(lp, ref or 0),
                                        positions=pos)))['limit_price']
    assert not lim('sell', 0.5)['ok']                 # vender a US$0,50 algo que vale US$90 → error de tipeo
    assert lim('sell', 88)['ok'] and not lim('sell', 88).get('warn')
    assert lim('sell', 120)['ok'] and lim('sell', 120)['warn']      # no se ejecutará pronto: aviso
    assert not lim('buy', 120)['ok']                 # comprar 33 % sobre el mercado
    assert lim('buy', 70)['warn']
    assert lim('buy', 95, ref=None)['warn']           # sin precio de referencia: aviso


@needs_db
def test_limit_sell_estimate_uses_market_price(db, fakes):
    """Venta límite muy baja: el monto se estima al precio de MERCADO (no al límite)
    y el control de precio límite la bloquea (hallazgo 17)."""
    from ontology.db import session_scope
    from brokerage import service
    with session_scope() as s:
        cid = _new_client(s, 'Limite Bajo', risk_profile='conservador')
    fake = fakes[cid]
    fake.positions = [{'symbol': 'NVDA', 'qty': '100', 'market_value': '9000', 'current_price': '90'}]
    with session_scope() as s:
        p = service.preview_order(s, cid, 'NVDA', 'sell', qty=100, order_type='limit', limit_price=0.5,
                                  source='mcp', requested_by='agent')
        assert p['est_usd'] == 9000.0 and p['blocked'], p
        assert 'US$9,000.00' in p['summary_es'] and 'mercado ~US$90.00' in p['summary_es']
        assert any(c['name'] == 'limit_price' and not c['ok'] for c in p['checks'])
        ok = service.preview_order(s, cid, 'NVDA', 'sell', qty=100, order_type='limit', limit_price=89)
        assert not ok['blocked'] and ok['est_usd'] == 9000.0, ok['checks']
        # compra límite: el límite es la cota superior honesta
        b = service.preview_order(s, cid, 'NVDA', 'buy', qty=5, order_type='limit', limit_price=91)
        assert b['est_usd'] == 455.0


@needs_db
def test_sell_whole_position_for_conservative_client(db, fakes):
    from ontology.db import session_scope
    from brokerage import service
    with session_scope() as s:
        cid = _new_client(s, 'Salida Total', risk_profile='conservador')
    fake = fakes[cid]
    fake.positions = [{'symbol': 'NVDA', 'qty': '30', 'market_value': '3000', 'current_price': '100'}]
    with session_scope() as s:
        p = service.preview_order(s, cid, 'NVDA', 'sell', qty=30)
        assert not p['blocked'], [c for c in p['checks'] if not c['ok']]
        assert service.confirm_order(s, p['preview_id'], 'pytest')['ok']
        assert service._daily_used(s, cid) == 0.0                   # las ventas no consumen el diario
        assert service.daily_used(s, cid) == 0.0


@needs_db
def test_mode_change_after_preview_never_executes_live(db, fakes):
    """Propuesta hecha en PAPEL; la cuenta pasa a DINERO REAL antes de aprobar →
    nunca llega al bróker real (hallazgos 6 y 14)."""
    from ontology.db import session_scope
    from brokerage import service
    from brokerage.models import BrokerClient
    os.environ['BROKERAGE_LIVE_ENABLED'] = 'on'
    try:
        with session_scope() as s:
            cid = _new_client(s, 'Papel a Real')
            p1 = service.preview_order(s, cid, 'NVDA', 'buy', notional=100, source='mcp', requested_by='agent')
            p2 = service.preview_order(s, cid, 'AAPL', 'buy', notional=100, source='mcp', requested_by='agent')
            ui = service.preview_order(s, cid, 'MSFT', 'buy', notional=100)
            assert p1['status'] == 'pending_approval' and p1['mode'] == 'paper'
        paper_fake = fakes.pop(cid)
        # A) reconexión con claves de dinero real → las propuestas abiertas caducan
        with session_scope() as s:
            r = service.set_credentials(s, cid, 'AKLIVEKEY9999', SECRET, env='live', actor='pytest')
            assert r['ok'] and r['client']['mode'] == 'live'
            service.update_client(s, cid, {'live_enabled': True, 'confirm_live': True}, 'pytest')
        live_fake = fakes[cid]
        assert not live_fake.paper
        with session_scope() as s:
            a = service.approve_preview(s, p1['preview_id'], 'Fabrizio')
            assert not a['ok'] and a['status'] == 'expired', a
            c = service.confirm_order(s, ui['preview_id'], 'Fabrizio')
            assert not c['ok'] and c['status'] == 'expired' and c['error_en']
            acts = [x['action'] for x in service.list_audit(s, client_id=cid)]
            assert 'account_changed' in acts
        # B) aunque algo cambie el modo SIN caducar (p. ej. un script), la huella lo frena
        with session_scope() as s:
            p3 = service.preview_order(s, cid, 'AMD', 'buy', notional=100, source='mcp', requested_by='agent')
            assert p3['mode'] == 'live' and p3['status'] == 'pending_approval'
            rec = s.get(BrokerClient, cid)
            rec.mode, rec.base_url = 'paper', 'https://paper-api.alpaca.markets'   # manipulado a mano
        with session_scope() as s:
            a = service.approve_preview(s, p3['preview_id'], 'Fabrizio')
        assert not a['ok'] and a['code'] == 'account_changed' and a['order']['status'] == 'rejected', a
        assert paper_fake.submits == [] and live_fake.submits == []
        assert p2['preview_id']
    finally:
        os.environ.pop('BROKERAGE_LIVE_ENABLED', None)


@needs_db
def test_auto_approval_rechecked_at_confirm(db, fakes):
    """Auto-aprobación de papel decidida al previsualizar NO basta: se recalcula al
    confirmar (hallazgo 15); el comité con auto-aprobación sí ejecuta (hallazgos 5/20)."""
    from ontology.db import session_scope
    from brokerage import service
    from brokerage.models import BrokerClient
    os.environ['BROKERAGE_AUTO_APPROVE_PAPER'] = 'on'
    try:
        with session_scope() as s:
            cid = _new_client(s, 'Auto Recheck')
            a = service.preview_order(s, cid, 'AMD', 'buy', notional=50, source='mcp')
            b = service.preview_order(s, cid, 'INTC', 'buy', notional=50, source='mcp')
            cm = service.preview_order(s, cid, 'TSM', 'buy', notional=50, source='committee', proposal_id='memo-x')
            assert a['status'] == b['status'] == cm['status'] == 'previewed'
            # el comité confirma su propia previsualización (research.committee.approve_memo lo hace)
            r = service.confirm_order(s, cm['preview_id'], 'Fabrizio', source='committee')
            assert r['ok'] and r['order']['status'] == 'submitted', r
        # se apaga la auto-aprobación → el agente ya no puede enviar: pasa a la cola humana
        os.environ['BROKERAGE_AUTO_APPROVE_PAPER'] = 'off'
        with session_scope() as s:
            r = service.confirm_order(s, a['preview_id'], 'agent', source='mcp')
            assert not r['ok'] and r['code'] == 'requires_human_approval' and r['status'] == 'pending_approval'
            assert a['preview_id'] in {x['preview_id'] for x in service.pending_approvals(s)}
        os.environ['BROKERAGE_AUTO_APPROVE_PAPER'] = 'on'
        # la cuenta cambia a dinero real (manipulado sin caducar) → rechazo por cuenta cambiada
        with session_scope() as s:
            rec = s.get(BrokerClient, cid)
            rec.mode, rec.base_url, rec.live_enabled = 'live', 'https://api.alpaca.markets', True
        with session_scope() as s:
            r = service.confirm_order(s, b['preview_id'], 'agent', source='mcp')
        assert not r['ok'] and r['code'] == 'account_changed'
        assert [x['symbol'] for x in fakes[cid].submits] == ['TSM']
    finally:
        os.environ.pop('BROKERAGE_AUTO_APPROVE_PAPER', None)


@needs_db
def test_hwm_reset_when_account_changes(db, fakes, env):
    from ontology.db import session_scope
    from brokerage import service
    with session_scope() as s:
        cid = _new_client(s, 'Cambio Cuenta')
    fakes[cid].account['equity'] = '100000'
    with session_scope() as s:
        assert service.account_snapshot(s, cid)['client']['hwm_equity'] == 100000.0
    fakes[cid] = FakeAlpaca(equity=2000.0, cash=2000.0, buying_power=2000.0)
    with session_scope() as s:
        r = service.set_credentials(s, cid, 'PKOTHERKEY5555', SECRET, env='paper', actor='pytest')
        assert r['ok'] and r['client']['hwm_equity'] is None
        p = service.preview_order(s, cid, 'AMD', 'buy', notional=100)
        dd = {c['name']: c for c in p['checks']}['drawdown_stop']
        assert dd['ok'] and not p['blocked'], p['checks']
    # la cuenta de la casa: cambiar ALPACA_BASE/KEY reinicia el máximo y lo audita
    env.setenv('ALPACA_KEY', 'PKHOUSEKEY7777')
    env.setenv('ALPACA_SECRET', 'house-secret-zzz')
    env.setenv('ALPACA_BASE', 'https://paper-api.alpaca.markets')
    from brokerage.models import BrokerClient
    with session_scope() as s:
        service.list_clients(s)
        s.get(BrokerClient, 'house').hwm_equity = 100000.0
    env.setenv('ALPACA_KEY', 'AKHOUSELIVE1234')
    env.setenv('ALPACA_BASE', 'https://api.alpaca.markets')
    with session_scope() as s:
        h = service.get_client(s, 'house')
        assert h['mode'] == 'live' and h['hwm_equity'] is None
        assert 'account_changed' in [a['action'] for a in service.list_audit(s, client_id='house')]


@needs_db
def test_input_lengths_and_bilingual_errors(db, fakes, client, env):
    from ontology.db import session_scope
    from brokerage import service
    with session_scope() as s:
        cid = _new_client(s, 'Largos')
        r = service.preview_order(s, cid, 'A' * 25, 'buy', notional=10)
        assert not r['ok'] and r['code'] == 'bad_request' and r['error_en']
        for bad in (service.preview_order(s, cid, 'NVDA', 'buy', notional='nan'),
                    service.preview_order(s, cid, 'NVDA', 'hold', notional=10),
                    service.update_client(s, cid, {'limits': {'max_order_usd': -1}}),
                    service.confirm_order(s, 'no-existe', 'x'),
                    service.reject_preview(s, 'no-existe', 'x'),
                    service.preview_order(s, 'no-existe', 'NVDA', 'buy', notional=1)):
            assert not bad['ok'] and bad.get('error') and bad.get('error_en') and bad['error'] != bad['error_en'], bad
    env.setenv('TRADE_PIN', PIN)
    H = {'X-Trade-Pin': PIN}
    r = client.post('/api/brokerage/orders/preview', json={'client_id': cid, 'symbol': 'B' * 30, 'side': 'buy',
                                                           'notional': 5}, headers=H)
    assert r.status_code == 400 and r.get_json()['error_en']
    r = client.patch(f'/api/brokerage/clients/{cid}', json={'email': 'x' * 300 + '@e.com'}, headers=H)
    assert r.status_code == 200 and len(r.get_json()['client']['email']) == 200
    r = client.post(f'/api/brokerage/orders/abc/confirm', json={}, headers=H)
    assert r.status_code == 400 and r.get_json()['error_en']


@needs_db
def test_committee_hooks_run_in_savepoints(db, fakes, monkeypatch):
    """mark_executed que revienta con un error de BASE no deshace la orden enviada;
    rechazar/caducar una propuesta del comité avisa a mark_preview_closed (hallazgos 10 y 13)."""
    cm = pytest.importorskip('research.committee')
    from sqlalchemy import text
    from ontology.db import session_scope
    from brokerage import service

    def boom(session, memo_id, order=None, actor='brokerage'):
        session.execute(text('SELECT * FROM tabla_que_no_existe'))
    closed = []
    monkeypatch.setattr(cm, 'mark_executed', boom)
    monkeypatch.setattr(cm, 'mark_preview_closed',
                        lambda session, memo_id, preview_id=None, status=None, reason='', actor='':
                        closed.append((memo_id, preview_id, status)), raising=False)
    with session_scope() as s:
        cid = _new_client(s, 'Comite Hooks')
        p = service.preview_order(s, cid, 'AAPL', 'buy', notional=100, source='committee', proposal_id='memo-a')
        r = service.approve_preview(s, p['preview_id'], 'Fabrizio')
        assert r['ok']
    with session_scope() as s:                                        # el commit NO falló
        o = service.get_order(s, p['preview_id'])
        assert o['status'] == 'submitted' and o['alpaca_order_id']
        q = service.preview_order(s, cid, 'MSFT', 'buy', notional=100, source='committee', proposal_id='memo-b')
        service.reject_preview(s, q['preview_id'], 'Fabrizio', reason='no')
    assert ('memo-b', q['preview_id'], 'rejected') in closed


@needs_db
def test_encryption_default_key_refuses_credentials(db, fakes, client, env):
    from ontology.db import session_scope
    from brokerage import service
    env.delenv('BROKERAGE_ENC_KEY', raising=False)
    env.setenv('SECRET_KEY', 'khipu-dev-secret-change-me')
    env.setenv('ALPACA_OAUTH_CLIENT_ID', 'cid')
    env.setenv('ALPACA_OAUTH_CLIENT_SECRET', 'csec')
    env.setenv('ALPACA_OAUTH_REDIRECT_URI', 'https://x.example.com/api/brokerage/oauth/callback')
    with session_scope() as s:
        cid = service.create_client(s, 'Sin Clave', actor='pytest')['client']['id']
        for env_name in ('paper', 'live'):
            r = service.set_credentials(s, cid, KEY, SECRET, env=env_name, actor='pytest')
            assert not r['ok'] and r['code'] == 'encryption_key_missing' and 'BROKERAGE_ENC_KEY' in r['error_en']
        assert not service.get_client(s, cid)['connected']
        r = service.oauth_start(s, cid, env='paper')
        assert not r['ok'] and r['code'] == 'encryption_key_missing'
    env.setenv('TRADE_PIN', PIN)
    d = client.get('/api/brokerage/status/detail', headers={'X-Trade-Pin': PIN}).get_json()
    assert d['encryption']['key_source'] == 'default' and not d['encryption']['can_store_credentials']
    assert 'encryption' not in client.get('/api/brokerage/status').get_json()


@needs_db
def test_client_names_unique_and_ambiguity(db, fakes):
    from ontology.db import session_scope
    from brokerage import service
    from brokerage.models import BrokerClient
    with session_scope() as s:
        a = service.create_client(s, 'Juan Perez', actor='pytest')['client']['id']
        dup = service.create_client(s, 'juan perez', actor='pytest')
        assert not dup['ok'] and dup['code'] == 'duplicate_name' and dup['error_en']
        b = service.create_client(s, 'Juan Perez Soto', actor='pytest')['client']['id']
        assert service.update_client(s, b, {'name': 'JUAN PEREZ'})['code'] == 'bad_request'
        # un duplicado heredado (creado por fuera del servicio) → ambiguo, nunca se elige uno
        s.add(BrokerClient(name='juan perez', mode='paper', auth_type='keys', risk_profile='moderado',
                           risk_limits={}, mandate={}, status='active', live_enabled=False))
    with session_scope() as s:
        assert service.get_client(s, 'Juan Perez') is None
        r = service.preview_order(s, 'Juan Perez', 'NVDA', 'buy', notional=10)
        assert not r['ok'] and r['code'] == 'ambiguous' and a in r['error'] and len(r['candidates']) == 2
        assert service.get_client(s, a)['name'] == 'Juan Perez'       # por id sí


@needs_db
def test_audit_table_is_append_only(db, fakes):
    from sqlalchemy import text
    from ontology.db import session_scope
    from brokerage import service
    with session_scope() as s:
        service.audit(s, 'pytest', 'probe', detail={'x': 1})
    for sql in ("UPDATE broker_audit SET actor = 'hacker'", 'DELETE FROM broker_audit', 'TRUNCATE broker_audit'):
        with pytest.raises(Exception) as ei:
            with session_scope() as s:
                s.execute(text(sql))
        assert 'append-only' in str(ei.value)
    with session_scope() as s:
        assert any(a['action'] == 'probe' for a in service.list_audit(s, limit=500))


@needs_db
def test_pin_lockout_uses_last_proxy_hop_and_global_backstop(db, client, env):
    """El primer X-Forwarded-For lo escribe el cliente: rotarlo no esquiva el freno
    ni sirve para bloquear a otra IP. Respaldo global ante ataques repartidos."""
    from brokerage import api as bk_api
    env.setenv('TRADE_PIN', PIN)
    url = '/api/brokerage/approvals'
    for i in range(25):
        r = client.get(url, headers={'X-Trade-Pin': '0000', 'X-Forwarded-For': f'10.9.{i}.1, 203.0.113.7'})
        assert r.status_code == (401 if i < 10 else 429), (i, r.status_code)
    # el fundador (otra IP real) NO queda bloqueado aunque el atacante falsifique su IP como primer salto
    for _ in range(10):
        client.get(url, headers={'X-Trade-Pin': '0000', 'X-Forwarded-For': '198.51.100.5, 203.0.113.8'})
    r = client.get(url, headers={'X-Trade-Pin': PIN, 'X-Forwarded-For': '198.51.100.5'})
    assert r.status_code == 200
    assert len(bk_api._PIN_FAILS) == 2                     # solo IPs con fallos; los aciertos no ocupan memoria
    # respaldo global: 30 fallos desde varias IP → todo bloqueado 10 min (y queda auditado)
    for i in range(10):
        client.get(url, headers={'X-Trade-Pin': '1111', 'X-Forwarded-For': f'192.0.2.{i + 10}'})
    r = client.get(url, headers={'X-Trade-Pin': PIN, 'X-Forwarded-For': '198.51.100.99'})
    assert r.status_code == 429 and r.get_json()['code'] == 'pin_locked_global' and r.get_json()['error_en']
    from ontology.db import session_scope
    from brokerage import service
    with session_scope() as s:
        assert any(a['action'] == 'pin_lockout' for a in service.list_audit(s, limit=50))
