"""tests/test_security.py — rutas de DINERO y endurecimiento estructural (auditoría 2026-09-30).

Sin red: Alpaca/Finnhub se sustituyen por un bróker FALSO (monkeypatch de
`requests`). Cubre:
  · PIN (core/pin.py) faltante / incorrecto / correcto y bloqueo COMPARTIDO
    entre /api/trade, /api/brokerage y /api/mcp; X-Forwarded-For falsificado
    no esquiva el freno; bloqueo global + auditoría;
  · /api/trade/order: tope $100k (notional y qty × precio), limit_price,
    time_in_force, tipos no soportados, client_order_id reenviado y
    duplicados idempotentes, interruptor BROKERAGE_TRADING_ENABLED;
  · /api/trade/close: regex estricta del símbolo (nunca DELETE /v2/positions);
  · agente: orden rechazada = ERROR, stop-loss cripto 'gtc' sin re-cierre,
    parámetros acotados, AUTO prohibido con dinero real, arranque único;
  · caché sin errores, rate-limit por el último salto de XFF, redacción de
    secretos, /api/ws-token de mismo origen, SECRET_KEY por defecto.

    DATABASE_URL=postgresql://postgres:devpass@localhost:5432/khipus_s2 \
        python3 -m pytest tests/test_security.py -q
"""
import json
import os
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('FINNHUB_KEY', '')
os.environ.setdefault('ANTHROPIC_KEY', '')

import requests  # noqa: E402

import server  # noqa: E402

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')

PIN = '4321-strong-pin'
ALPACA_SECRET_VALUE = 'ALPACA-SECRET-DO-NOT-LEAK-123'


# ════════════════════════════════════════════════════════════════════════════
# Bróker falso (formas de JSON de Alpaca: números como strings)
# ════════════════════════════════════════════════════════════════════════════
class FakeResp:
    def __init__(self, status, payload=None, text=None, content=b''):
        self.status_code = status
        self.ok = 200 <= status < 300
        self._payload = payload
        self.text = text if text is not None else (json.dumps(payload) if payload is not None else '')
        self.content = content or self.text.encode()
        self.headers = {'Content-Type': 'application/json'}

    def json(self):
        if self._payload is None:
            raise ValueError('no json')
        return self._payload


class FakeAlpaca:
    def __init__(self):
        self.calls = []
        self.orders = {}               # client_order_id → orden
        self.positions = []
        self.open_orders = []
        self.reject = None             # (status, message) → POST /v2/orders lo rechaza
        self.price = 100.0
        self.tradable = {}             # símbolo → bool (por defecto True)
        self.raise_on_get = None

    def posts(self):
        return [c for c in self.calls if c[0] == 'POST' and '/v2/orders' in c[1]]

    def get(self, url, params=None, headers=None, timeout=None, **_k):
        self.calls.append(('GET', url, params, None))
        if self.raise_on_get:
            raise self.raise_on_get
        if url.endswith('/v2/account'):
            return FakeResp(200, {'equity': '10000', 'last_equity': '10000', 'status': 'ACTIVE'})
        if url.endswith('/v2/positions'):
            return FakeResp(200, list(self.positions))
        if url.endswith('/v2/orders') and (params or {}).get('status') == 'open':
            return FakeResp(200, list(self.open_orders))
        if '/v2/orders:by_client_order_id' in url:
            o = self.orders.get((params or {}).get('client_order_id'))
            return FakeResp(200, dict(o)) if o else FakeResp(404, {'message': 'order not found'})
        if url.endswith('/v2/assets') and (params or {}).get('asset_class') == 'crypto':
            return FakeResp(200, [{'symbol': 'BTC/USD', 'name': 'Bitcoin', 'tradable': True}])
        if '/v2/assets/' in url:
            sym = url.rsplit('/', 1)[1]
            return FakeResp(200, {'symbol': sym, 'tradable': self.tradable.get(sym, True), 'status': 'active'})
        if 'finnhub.io' in url:
            return FakeResp(200, {'c': self.price or 0, 'pc': (self.price or 0) * 0.99})
        if 'data.alpaca.markets' in url and 'crypto' in url:
            sym = (params or {}).get('symbols')
            return FakeResp(200, {'trades': {sym: {'p': 60000.0}}})
        if 'data.alpaca.markets/v2/stocks' in url:
            return FakeResp(200, {'trade': {'p': self.price}}) if self.price else FakeResp(404, {'message': 'nf'})
        if 'gdeltproject' in url:
            return FakeResp(200, {'tonechart': []})
        return FakeResp(404, {'message': 'unknown ' + url})

    def post(self, url, json=None, headers=None, timeout=None, **_k):  # noqa: A002 — firma de requests
        self.calls.append(('POST', url, None, json))
        if self.reject:
            return FakeResp(self.reject[0], {'code': 40310000, 'message': self.reject[1]})
        coid = (json or {}).get('client_order_id')
        if coid in self.orders:
            return FakeResp(422, {'code': 40010001, 'message': 'client_order_id must be unique'})
        o = dict(json or {}, id=f'ord-{len(self.orders) + 1}', status='accepted')
        self.orders[coid] = o
        return FakeResp(200, dict(o))

    def delete(self, url, headers=None, timeout=None, **_k):
        self.calls.append(('DELETE', url, None, None))
        return FakeResp(200, {'id': 'close-1', 'status': 'accepted'})


# ════════════════════════════════════════════════════════════════════════════
# fixtures
# ════════════════════════════════════════════════════════════════════════════
def _reset_guards():
    from core import http as core_http
    from core import pin as core_pin
    core_http._rate_buckets.clear()
    core_pin._reset_for_tests()
    try:
        from mcp_server import auth as mcp_auth
        mcp_auth.reset_pin_guard()
    except Exception:  # noqa: BLE001
        pass
    server._TRADE_STATUS_CACHE.update(ts=0.0, data=None)
    server._crypto_assets_cache.clear()
    server._TRADABLE_CACHE.clear()
    server._WS_USED.clear()
    try:
        server.cache.clear()
    except Exception:  # noqa: BLE001
        pass


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.setenv('TRADE_PIN', PIN)
    for k in ('BROKERAGE_TRADING_ENABLED', 'RAILWAY_ENVIRONMENT', 'RAILWAY_ENVIRONMENT_NAME', 'RAILWAY_PROJECT_ID',
              'MCP_PIN_MAX_FAILS', 'MCP_PIN_LOCK_MIN', 'MCP_TRUSTED_PROXY_HOPS', 'FINNHUB_WS_KEY'):
        monkeypatch.delenv(k, raising=False)
    _reset_guards()
    yield
    _reset_guards()


@pytest.fixture
def alpaca(monkeypatch):
    fake = FakeAlpaca()
    monkeypatch.setattr(requests, 'get', fake.get)
    monkeypatch.setattr(requests, 'post', fake.post)
    monkeypatch.setattr(requests, 'delete', fake.delete)
    monkeypatch.setattr(server, 'ALPACA_KEY', 'PKFAKEKEY0001')
    monkeypatch.setattr(server, 'ALPACA_SECRET', ALPACA_SECRET_VALUE)
    monkeypatch.setattr(server, 'ALPACA_BASE', 'https://paper-api.alpaca.markets')
    monkeypatch.setattr(server, 'FINNHUB', 'fh-server-key-000')
    return fake


@pytest.fixture
def nodb(monkeypatch):
    import ontology.db as odb
    monkeypatch.setattr(odb, 'DATABASE_URL', '')
    return True


@pytest.fixture
def no_rate(monkeypatch):
    """Quita el rate-limit en tests que no lo prueban (muchas órdenes seguidas)."""
    from core import http as core_http
    monkeypatch.setattr(core_http, '_rate_limit', lambda *a, **k: True)


@pytest.fixture
def client():
    server.app.config['TESTING'] = True
    return server.app.test_client()


@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    import brokerage.models  # noqa: F401
    import mcp_server.models  # noqa: F401
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    yield
    Base.metadata.drop_all(engine)


def H(pin=PIN, ip=None, **extra):
    h = {'Content-Type': 'application/json'}
    if pin is not None:
        h['X-Trade-Pin'] = pin
    if ip:
        h['X-Forwarded-For'] = ip
    h.update(extra)
    return h


def _audit_rows(action):
    from ontology.db import session_scope
    from brokerage.service import list_audit
    with session_scope() as s:
        return [r for r in list_audit(s, limit=500) if r['action'] == action]


# ════════════════════════════════════════════════════════════════════════════
# 1. PIN — un solo contador para todas las superficies
# ════════════════════════════════════════════════════════════════════════════
SURFACES = ('/api/trade/account', '/api/brokerage/clients', '/api/mcp/tokens')


def test_pin_disabled_without_env(client, alpaca, nodb, monkeypatch):
    monkeypatch.delenv('TRADE_PIN')
    for url in SURFACES:
        r = client.get(url, headers=H())
        assert r.status_code == 403 and r.get_json()['code'] == 'trading_disabled', url
        assert r.get_json()['error_en']
    assert not alpaca.calls                                    # nada llegó al bróker


def test_pin_missing_wrong_right_on_every_surface(client, alpaca, nodb):
    for url in SURFACES:
        assert client.get(url, headers=H(pin=None)).status_code == 401, url
        r = client.get(url, headers=H(pin='nope'))
        assert r.status_code == 401 and r.get_json()['code'] == 'invalid_pin' and r.get_json()['error_en'], url
    assert client.get('/api/trade/account', headers=H()).status_code == 200
    # con PIN correcto el corretaje/MCP siguen (y responden 503 por falta de base, no 401)
    assert client.get('/api/brokerage/clients', headers=H()).status_code == 503
    assert client.get('/api/mcp/tokens', headers=H()).status_code == 503
    body = client.get('/api/trade/account', headers=H()).get_json()
    assert body['paper'] is True


def test_empty_pin_does_not_count(client, alpaca, nodb):
    for _ in range(15):
        assert client.get('/api/trade/account', headers=H(pin='')).status_code == 401
    assert client.get('/api/trade/account', headers=H()).status_code == 200


def test_lockout_is_shared_across_trade_brokerage_mcp(client, alpaca, nodb):
    """Repartir los intentos entre superficies ya no da 3× más oportunidades."""
    ip = '203.0.113.50'
    for _ in range(4):
        assert client.get('/api/trade/account', headers=H(pin='bad1', ip=ip)).status_code == 401
    for _ in range(3):
        assert client.get('/api/brokerage/clients', headers=H(pin='bad2', ip=ip)).status_code == 401
    for _ in range(3):
        assert client.get('/api/mcp/tokens', headers=H(pin='bad3', ip=ip)).status_code == 401
    for url in SURFACES:                                       # 10 fallos → bloqueado en TODAS
        r = client.get(url, headers=H(ip=ip))
        assert r.status_code == 429 and r.get_json()['code'] == 'pin_locked', url
        assert int(r.headers.get('Retry-After', '0')) > 0 or r.get_json().get('retry_after')
    # otra IP real no queda bloqueada
    assert client.get('/api/trade/account', headers=H(ip='198.51.100.1')).status_code == 200


def test_spoofed_first_xff_hop_does_not_bypass(client, alpaca, nodb):
    for i in range(10):
        r = client.get('/api/trade/account', headers=H(pin='0000', ip=f'10.0.{i}.1, 203.0.113.9'))
        assert r.status_code == 401
    r = client.get('/api/trade/account', headers=H(ip='10.99.99.99, 203.0.113.9'))
    assert r.status_code == 429 and r.get_json()['code'] == 'pin_locked'
    # el atacante no puede bloquear a otro escribiendo su IP como primer salto
    assert client.get('/api/trade/account', headers=H(ip='203.0.113.9, 198.51.100.77')).status_code == 200


def test_global_lockout_fires_callback_once(client, alpaca, nodb):
    from core import pin as core_pin
    seen = []

    def listener(scope, n):
        seen.append((scope, n))
    core_pin.on_global_lock(listener)
    try:
        for i in range(30):
            url = '/api/trade/account' if i % 2 else '/api/brokerage/clients'
            assert client.get(url, headers=H(pin='x', ip=f'192.0.2.{i + 1}')).status_code == 401
        r = client.get('/api/mcp/tokens', headers=H(ip='198.51.100.200'))
        assert r.status_code == 429 and r.get_json()['code'] == 'pin_locked_global'
        r = client.get('/api/trade/account', headers=H(ip='198.51.100.201'))
        assert r.status_code == 429 and r.get_json()['code'] == 'pin_locked_global'
        assert seen == [('global', 30)]
    finally:
        core_pin._listeners.remove(listener)


@needs_db
def test_global_lockout_from_trade_is_audited(client, alpaca, db):
    for i in range(30):
        client.get('/api/trade/account', headers=H(pin='x', ip=f'192.0.2.{i + 100}'))
    rows = _audit_rows('pin_lockout')
    assert rows and rows[0]['detail']['scope'] == 'global'


def test_rate_limit_key_is_last_xff_hop(client, alpaca, nodb, monkeypatch):
    monkeypatch.setattr(server, 'ALPACA_KEY', '')          # /api/trade/status sin red
    for i in range(30):
        assert client.get('/api/trade/status', headers={'X-Forwarded-For': f'1.2.3.{i}, 203.0.113.60'}
                          ).status_code == 200
    r = client.get('/api/trade/status', headers={'X-Forwarded-For': '9.9.9.9, 203.0.113.60'})
    assert r.status_code == 429 and r.get_json()['error_en'] and r.headers.get('Retry-After')
    assert client.get('/api/trade/status', headers={'X-Forwarded-For': '203.0.113.61'}).status_code == 200


def test_rate_buckets_are_pruned():
    from core import http as core_http
    core_http._rate_buckets.clear()
    core_http._rate_buckets['old:x'] = [time.time() - 10_000]
    core_http._rate_buckets['empty:x'] = []
    core_http._rate_state['pruned_at'] = 0.0
    assert core_http._rate_limit('fresh:x', 5, 60)
    assert 'old:x' not in core_http._rate_buckets and 'empty:x' not in core_http._rate_buckets
    assert 'fresh:x' in core_http._rate_buckets


def test_trade_status_is_cached_30s(client, alpaca, nodb):
    for _ in range(3):
        d = client.get('/api/trade/status').get_json()
        assert d['ok'] and d['paper'] is True and 'hint_en' in d
    assert sum(1 for c in alpaca.calls if c[1].endswith('/v2/account')) == 1


# ════════════════════════════════════════════════════════════════════════════
# 2. /api/trade/order — validación, tope, client_order_id, interruptor
# ════════════════════════════════════════════════════════════════════════════
def _order(client, **body):
    return client.post('/api/trade/order', data=json.dumps(body), headers=H())


def test_order_qty_times_price_is_capped(client, alpaca, nodb, no_rate):
    r = _order(client, symbol='NVDA', side='buy', qty=2000)       # 2000 × $100 = $200k
    assert r.status_code == 400 and r.get_json()['code'] == 'over_cap' and r.get_json()['error_en']
    r = _order(client, symbol='NVDA', side='buy', qty=3000, type='limit', limit_price=50)   # $150k
    assert r.status_code == 400 and r.get_json()['code'] == 'over_cap'
    r = _order(client, symbol='NVDA', side='buy', notional=150000)
    assert r.status_code == 400 and r.get_json()['code'] == 'over_cap'
    assert not alpaca.posts()


def test_order_field_validation(client, alpaca, nodb, no_rate):
    cases = [
        dict(symbol='NVDA', side='buy', qty=1, type='limit', limit_price=0),
        dict(symbol='NVDA', side='buy', qty=1, type='limit', limit_price='abc'),
        dict(symbol='NVDA', side='buy', qty=1, type='limit'),
        dict(symbol='NVDA', side='buy', qty=1, time_in_force='forever'),
        dict(symbol='NVDA', side='hold', qty=1),
        dict(symbol='NVDA', side='buy', qty=-1),
        dict(symbol='NVDA', side='buy', qty='nan'),
        dict(symbol='NVDA', side='buy', qty=1, notional=10),
        dict(symbol='NVDA', side='buy'),
        dict(symbol='NVDA?x=1', side='buy', qty=1),
        dict(symbol='..', side='buy', qty=1),
        dict(symbol='NVDA', side='buy', qty=1, client_order_id='x'),
        dict(symbol='NVDA', side='buy', qty=1, client_order_id='bad id with spaces'),
        dict(symbol='NVDA', side='buy', qty=1e-10),                     # _num_str → '0'
        dict(symbol='X.', side='buy', qty=1),
        dict(symbol='ß', side='buy', qty=1),                             # 'ß'.upper() == 'SS'
    ]
    for body in cases:
        r = _order(client, **body)
        assert r.status_code == 400, (body, r.get_json())
        assert r.get_json()['error'] and r.get_json()['error_en'], body
    for t in ('stop', 'trailing_stop'):
        r = _order(client, symbol='NVDA', side='buy', qty=1, type=t, stop_price=90)
        assert r.status_code == 400 and r.get_json()['code'] == 'unsupported_type'
    assert not alpaca.posts()


def test_order_forwards_client_order_id_and_fields(client, alpaca, nodb, no_rate):
    coid = '3f1c2a9e-8b7d-4c6e-9f00-1234567890ab'
    r = _order(client, symbol='nvda', side='buy', qty=10, time_in_force='ioc', client_order_id=coid)
    d = r.get_json()
    assert r.status_code == 200 and d['id'] and d['paper'] is True
    sent = alpaca.posts()[-1][3]
    assert sent['client_order_id'] == coid and sent['symbol'] == 'NVDA' and sent['qty'] == '10'
    assert sent['time_in_force'] == 'ioc' and sent['type'] == 'market'
    # limit → limit_price reenviado como número limpio
    r = _order(client, symbol='NVDA', side='sell', qty=0.5, type='limit', limit_price=101.25)
    sent = alpaca.posts()[-1][3]
    assert r.status_code == 200 and sent['limit_price'] == '101.25' and sent['qty'] == '0.5'
    assert sent['client_order_id'].startswith('kh-')          # sin id del cliente → uno del servidor


def test_order_duplicate_client_order_id_is_idempotent(client, alpaca, nodb, no_rate):
    coid = 'retry-0000-1111-2222'
    r1 = _order(client, symbol='NVDA', side='buy', notional=100, client_order_id=coid)
    r2 = _order(client, symbol='NVDA', side='buy', notional=100, client_order_id=coid)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r2.get_json()['duplicate'] is True and r2.get_json()['id'] == r1.get_json()['id']
    assert len(alpaca.orders) == 1


def test_order_crypto_forces_gtc_and_checks_catalog(client, alpaca, nodb, no_rate):
    r = _order(client, symbol='BTC/USD', side='buy', notional=50, time_in_force='day')
    assert r.status_code == 200 and alpaca.posts()[-1][3]['time_in_force'] == 'gtc'
    r = _order(client, symbol='DOGE/USD', side='buy', notional=50)
    assert r.status_code == 400 and r.get_json()['code'] == 'not_tradable'
    r = _order(client, symbol='BTC/USD', side='buy', qty=2)        # 2 × $60k = $120k
    assert r.status_code == 400 and r.get_json()['code'] == 'over_cap'


def test_order_without_verifiable_price_is_refused(client, alpaca, nodb, no_rate):
    alpaca.price = 0
    r = _order(client, symbol='NVDA', side='buy', qty=1)
    assert r.status_code == 422 and r.get_json()['code'] == 'price_unavailable'
    assert not alpaca.posts()
    assert _order(client, symbol='NVDA', side='buy', notional=10).status_code == 200   # notional sí


def test_order_rejected_by_alpaca_is_an_error(client, alpaca, nodb, no_rate):
    alpaca.reject = (403, 'insufficient buying power')
    r = _order(client, symbol='NVDA', side='buy', notional=10)
    d = r.get_json()
    assert r.status_code == 403 and d['code'] == 'broker_rejected' and 'insufficient' in d['error']


def test_kill_switch_blocks_order_and_close(client, alpaca, nodb, no_rate, monkeypatch):
    monkeypatch.setenv('BROKERAGE_TRADING_ENABLED', 'off')
    r = _order(client, symbol='NVDA', side='buy', notional=10)
    assert r.status_code == 423 and r.get_json()['code'] == 'trading_halted' and r.get_json()['error_en']
    r = client.post('/api/trade/close', data=json.dumps({'symbol': 'NVDA'}), headers=H())
    assert r.status_code == 423
    assert not alpaca.posts() and not [c for c in alpaca.calls if c[0] == 'DELETE']
    assert any(w['code'] == 'trading_halted' for w in server._security_warnings())


def test_broker_not_configured_has_code(client, nodb, monkeypatch):
    monkeypatch.setattr(server, 'ALPACA_KEY', '')
    r = _order(client, symbol='NVDA', side='buy', notional=10)
    assert r.status_code == 400 and r.get_json()['code'] == 'broker_not_configured'


@needs_db
def test_order_attempts_are_audited(client, alpaca, db, no_rate):
    coid = 'audit-0000-1111-2222'
    assert _order(client, symbol='NVDA', side='buy', notional=25, client_order_id=coid).status_code == 200
    _order(client, symbol='NVDA', side='buy', qty=5000)                               # rechazada por tope
    rows = _audit_rows('trade_order')
    ok = [r for r in rows if r['detail'].get('client_order_id') == coid]
    assert ok and ok[0]['detail']['outcome'] == 'submitted' and ok[0]['detail']['alpaca_order_id']
    assert ok[0]['detail']['paper'] is True and ok[0]['detail']['symbol'] == 'NVDA'
    assert any(r['detail'].get('outcome') == 'rejected' and r['detail'].get('reason') == 'over_cap' for r in rows)
    assert ALPACA_SECRET_VALUE not in json.dumps(rows) and PIN not in json.dumps(rows)
    client.post('/api/trade/close', data=json.dumps({'symbol': 'NVDA'}), headers=H())
    assert any(r['detail'].get('outcome') == 'submitted' for r in _audit_rows('trade_close'))


# ════════════════════════════════════════════════════════════════════════════
# 3. /api/trade/close — símbolo estricto
# ════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize('sym', ['.', '..', '?cancel_orders=true', '../orders', 'AAPL?x=1', 'A..B', '.AAPL',
                                 'AAPL/', 'BTC/US', 'a b', 'AAPL#', '%2e', 'TOOLONGSYMBOL123', 'X.', 'AAPL.',
                                 'ß', 'ＡＡＰＬ', 'BRK.B.C'])
def test_close_rejects_bad_symbols(client, alpaca, nodb, no_rate, sym):
    r = client.post('/api/trade/close', data=json.dumps({'symbol': sym}), headers=H())
    assert r.status_code == 400 and r.get_json()['code'] in ('invalid_symbol', 'bad_request'), sym
    assert not [c for c in alpaca.calls if c[0] == 'DELETE']


def test_close_valid_symbols_are_encoded(client, alpaca, nodb, no_rate):
    for sym, path in (('btc/usd', '/v2/positions/BTCUSD'), ('BRK.B', '/v2/positions/BRK.B'),
                      ('NVDA', '/v2/positions/NVDA')):
        r = client.post('/api/trade/close', data=json.dumps({'symbol': sym}), headers=H())
        assert r.status_code == 200, sym
        assert [c for c in alpaca.calls if c[0] == 'DELETE'][-1][1].endswith(path)
    assert client.post('/api/trade/close', data=json.dumps({}), headers=H()).status_code == 400
    assert not any(c[1].endswith('/v2/positions') for c in alpaca.calls if c[0] == 'DELETE')


# ════════════════════════════════════════════════════════════════════════════
# 4. Agente de trading
# ════════════════════════════════════════════════════════════════════════════
@pytest.fixture
def agent(monkeypatch, alpaca):
    for k, v in (('running', True), ('mode', 'auto'), ('universe', ['NVDA']), ('log', []),
                 ('pending_close', {}), ('daily_pnl_pct', 0.0), ('min_confidence', 65),
                 ('max_orders_per_cycle', 3), ('max_pos_pct', 5.0), ('stop_loss_pct', 3.0),
                 ('interval_min', 15), ('max_daily_loss_pct', 2.0), ('thread', None), ('status', 'stopped')):
        monkeypatch.setitem(server._AGENT, k, v)
    monkeypatch.setattr(server, '_agent_analyze',
                        lambda *a, **k: {'action': 'buy', 'confidence': 90, 'reason': 'test', 'size_pct': 2})
    return server._AGENT


def test_agent_rejected_order_is_logged_as_error(agent, alpaca, nodb):
    alpaca.reject = (403, 'insufficient buying power')
    server._agent_run_cycle()
    e = [x for x in agent['log'] if x.get('ticker') == 'NVDA'][-1]
    assert e['executed'] is False and e['level'] == 'error' and 'Alpaca HTTP 403' in e['exec_error']


def test_agent_accepted_order_is_executed(agent, alpaca, nodb):
    server._agent_run_cycle()
    e = [x for x in agent['log'] if x.get('ticker') == 'NVDA'][-1]
    sent = alpaca.posts()[-1][3]
    assert e['executed'] is True and e['level'] == 'success' and e['order_id']
    assert sent['time_in_force'] == 'day' and sent['client_order_id'].startswith('kh-agent-')
    assert float(sent['notional']) <= 10000 * 0.05


def test_agent_skips_non_tradable(agent, alpaca, nodb):
    alpaca.tradable['NVDA'] = False
    server._agent_run_cycle()
    e = [x for x in agent['log'] if x.get('ticker') == 'NVDA'][-1]
    assert not alpaca.posts() and 'Alpaca' in e['skipped']


def test_agent_crypto_stop_loss_gtc_and_no_reclose(agent, alpaca, nodb, monkeypatch):
    monkeypatch.setitem(agent, 'universe', [])
    alpaca.positions = [{'symbol': 'BTCUSD', 'asset_class': 'crypto', 'qty': '0.5', 'unrealized_plpc': '-0.10',
                         'market_value': '30000'}]
    server._agent_run_cycle()
    posts = alpaca.posts()
    assert len(posts) == 1 and posts[0][3]['time_in_force'] == 'gtc' and posts[0][3]['side'] == 'sell'
    assert posts[0][3]['qty'] == '0.5'
    server._agent_run_cycle()                                   # la posición sigue ahí: NO se reenvía
    assert len(alpaca.posts()) == 1
    assert any('pendiente' in (x.get('msg') or '') for x in agent['log'])
    # con una orden abierta en Alpaca (reinicio del server: sin memoria) tampoco
    agent['pending_close'].clear()
    alpaca.open_orders = [{'symbol': 'BTC/USD', 'side': 'sell', 'status': 'new'}]
    server._agent_run_cycle()
    assert len(alpaca.posts()) == 1


def test_agent_equity_stop_loss_uses_day(agent, alpaca, nodb, monkeypatch):
    monkeypatch.setitem(agent, 'universe', ['NVDA'])
    alpaca.positions = [{'symbol': 'NVDA', 'asset_class': 'us_equity', 'qty': '3', 'unrealized_plpc': '-0.05',
                         'market_value': '300'}]
    server._agent_run_cycle()
    posts = alpaca.posts()
    assert posts[0][3]['time_in_force'] == 'day' and posts[0][3]['side'] == 'sell'
    assert len(posts) == 1                                      # no recompra en el mismo ciclo


def test_agent_kill_switch_sends_nothing(agent, alpaca, nodb, monkeypatch):
    monkeypatch.setenv('BROKERAGE_TRADING_ENABLED', 'off')
    alpaca.positions = [{'symbol': 'AMD', 'qty': '1', 'unrealized_plpc': '-0.5', 'market_value': '50'}]
    server._agent_run_cycle()
    assert not alpaca.posts()
    assert any('BROKERAGE_TRADING_ENABLED' in (x.get('msg') or x.get('skipped') or '') for x in agent['log'])


def test_agent_live_account_never_executes(agent, alpaca, nodb, monkeypatch):
    monkeypatch.setattr(server, 'ALPACA_BASE', 'https://api.alpaca.markets')
    server._agent_run_cycle()
    assert not alpaca.posts()


def test_agent_universe_is_sanitized():
    uni, skipped = server._agent_universe(['nvda', '8411.T', 'BAD&token=x', 'brk.b', 'SAP.DE', 'NVDA', 'BTC/USD'])
    assert uni == ['NVDA', 'BRK.B'] and '8411.T' in skipped and 'BAD&token=x' in skipped


def test_agent_config_clamps_and_validates(client, alpaca, nodb, agent, no_rate, monkeypatch):
    monkeypatch.setitem(agent, 'running', False)
    monkeypatch.setitem(agent, 'mode', 'manual')
    r = client.post('/api/trade/agent/config', headers=H(), data=json.dumps({
        'max_pos_pct': 100, 'stop_loss_pct': -5, 'min_confidence': 0, 'max_daily_loss_pct': 50,
        'max_orders_per_cycle': 99, 'interval_min': 1, 'universe': ['NVDA', '8411.T']}))
    d = r.get_json()
    assert r.status_code == 200, d
    assert d['max_pos_pct'] == 10.0 and d['stop_loss_pct'] == 0.5 and d['min_confidence'] == 50
    assert d['max_daily_loss_pct'] == 5.0 and d['max_orders_per_cycle'] == 5 and d['interval_min'] == 5
    assert d['universe'] == ['NVDA'] and d['notes']
    for bad in ({'mode': 'yolo'}, {'max_pos_pct': 'abc'}, {'universe': 'NVDA'}, {'universe': ['8411.T']}):
        r = client.post('/api/trade/agent/config', headers=H(), data=json.dumps(bad))
        assert r.status_code == 400 and r.get_json()['error_en'], bad
    st = client.get('/api/trade/agent/status', headers=H()).get_json()
    assert st['bounds']['max_pos_pct'] == [0.5, 10.0] and st['auto_allowed'] is True


def test_agent_auto_refused_on_live_account(client, alpaca, nodb, agent, no_rate, monkeypatch):
    monkeypatch.setitem(agent, 'running', False)
    monkeypatch.setitem(agent, 'mode', 'manual')
    monkeypatch.setattr(server, 'ALPACA_BASE', 'https://api.alpaca.markets')
    for url in ('/api/trade/agent/config', '/api/trade/agent/start'):
        r = client.post(url, headers=H(), data=json.dumps({'mode': 'auto'}))
        assert r.status_code == 403 and r.get_json()['code'] == 'auto_live_refused' and r.get_json()['error_en']
    assert agent['mode'] == 'manual' and agent['running'] is False
    r = client.post('/api/trade/agent/config', headers=H(), data=json.dumps({'mode': 'manual'}))
    assert r.status_code == 200


def test_agent_start_is_single_threaded(client, alpaca, nodb, agent, no_rate, monkeypatch):
    monkeypatch.setitem(agent, 'running', False)
    monkeypatch.setitem(agent, 'mode', 'manual')
    release = threading.Event()
    started = []

    def fake_loop():
        started.append(1)
        server._AGENT['status'] = 'running'
        release.wait(5)
        server._AGENT['status'] = 'stopped'
    monkeypatch.setattr(server, '_agent_thread_fn', fake_loop)
    results = []
    barrier = threading.Barrier(4)

    def go():
        c = server.app.test_client()
        barrier.wait()
        results.append(c.post('/api/trade/agent/start', headers=H(), data='{}').get_json().get('status'))
    ths = [threading.Thread(target=go) for _ in range(4)]
    for t in ths:
        t.start()
    for t in ths:
        t.join(5)
    try:
        assert sorted(results).count('started') == 1 and results.count('already_running') == 3
        assert len(started) == 1
        # parar y re-arrancar mientras el hilo viejo sigue vivo → 409 (no dos hilos)
        client.post('/api/trade/agent/stop', headers=H())
        r = client.post('/api/trade/agent/start', headers=H(), data='{}')
        assert r.status_code == 409 and r.get_json()['code'] == 'agent_stopping'
    finally:
        release.set()
        th = server._AGENT.get('thread')
        if th is not None:
            th.join(5)
        server._AGENT['running'] = False


@needs_db
def test_agent_orders_are_audited(agent, alpaca, db):
    alpaca.reject = (422, 'qty must be > 0')
    server._agent_run_cycle()
    rows = _audit_rows('agent_order')
    assert rows and rows[0]['actor'] == 'agente-trading' and rows[0]['detail']['outcome'] == 'rejected'
    assert rows[0]['detail']['http_status'] == 422


# ════════════════════════════════════════════════════════════════════════════
# 5. Caché sin errores
# ════════════════════════════════════════════════════════════════════════════
def test_cache_filter_statuses():
    from flask import Response
    f = server._cacheable_response
    assert f({'ok': 1}) and f('text') and f(Response('x', status=200)) and f((Response('x'), 201))
    assert not f((Response('x'), 502)) and not f(({'error': 1}, 404)) and not f(Response('x', status=500))
    assert not f(({'e': 1}, '503 SERVICE UNAVAILABLE')) and f(({'ok': 1}, {'X-H': '1'}))


def test_vendor_error_is_not_cached(client, monkeypatch):
    state = {'ok': False, 'n': 0}

    def fake_get(url, **k):
        state['n'] += 1
        if not state['ok']:
            return FakeResp(502, {'message': 'bad gateway'})
        return FakeResp(200, None, text='/* d3 */', content=b'/* d3 */')
    monkeypatch.setattr(requests, 'get', fake_get)
    assert client.get('/vendor/d3.min.js').status_code == 502
    state['ok'] = True
    # caché NEGATIVA: durante 60 s el fallo se repite SIN volver a esperar al CDN
    r = client.get('/vendor/d3.min.js')
    assert r.status_code == 502 and r.headers.get('X-Khipu-Neg-Cache') == '1' and state['n'] == 1
    assert r.get_json()['error'] and r.get_json()['error_en']
    server.cache.clear()                                           # = pasaron los 60 s
    r = client.get('/vendor/d3.min.js')
    assert r.status_code == 200 and b'd3' in r.data
    assert client.get('/vendor/d3.min.js').status_code == 200 and state['n'] == 2     # el 200 SÍ se cachea


def test_vendor_is_rate_limited_and_times_out_fast(client, monkeypatch):
    seen = {}

    def fake_get(url, **k):
        seen['timeout'] = k.get('timeout')
        return FakeResp(200, None, text='/* x */', content=b'/* x */')
    monkeypatch.setattr(requests, 'get', fake_get)
    assert client.get('/vendor/three.min.js').status_code == 200 and seen['timeout'] <= 10
    codes = [client.get('/vendor/three.min.js', headers={'X-Forwarded-For': '203.0.113.90'}).status_code
             for _ in range(125)]
    assert codes.count(429) >= 1


# ════════════════════════════════════════════════════════════════════════════
# 6. Secretos: redacción, _safe_get, /api/ws-*, SECRET_KEY
# ════════════════════════════════════════════════════════════════════════════
def test_safe_get_error_never_contains_the_url(monkeypatch):
    from core import http as core_http

    def boom(url, timeout=None):
        raise requests.exceptions.ConnectionError(f'Max retries exceeded with url: {url}')
    monkeypatch.setattr(requests, 'get', boom)
    data, err = core_http._safe_get('https://finnhub.io/api/v1/quote?symbol=X&token=SUPERSECRETTOKEN99')
    assert data is None and 'SUPERSECRETTOKEN99' not in err and 'token' not in err

    def boom2(url, timeout=None):
        raise RuntimeError('weird ' + url)
    monkeypatch.setattr(requests, 'get', boom2)
    _d, err = core_http._safe_get('https://x.example/?apikey=SUPERSECRETTOKEN99')
    assert 'SUPERSECRETTOKEN99' not in err and err.startswith('error del proveedor') and 'upstream error' in err


def test_diag_redact_covers_all_secrets(monkeypatch):
    monkeypatch.setattr(server, 'GEMINI_KEY', 'AIzaGEMINI-KEY-123456')
    monkeypatch.setattr(server, 'KHIPU_ADMIN_SECRET', 'admin-secret-value-9')
    monkeypatch.setenv('TAVILY_KEY', 'tvly-SECRET-abcdef')
    monkeypatch.setenv('NVIDIA_KEY', 'nvapi-SECRET-000111')
    txt = ('404 for https://generativelanguage.googleapis.com/v1beta/models/x?key=AIzaGEMINI-KEY-123456 '
           'admin=admin-secret-value-9 tavily tvly-SECRET-abcdef Bearer nvapi-SECRET-000111 '
           'password=hunter2hunter2 ' + 'x' * 300)
    red = server._diag_redact(txt)
    for s in ('AIzaGEMINI-KEY-123456', 'admin-secret-value-9', 'tvly-SECRET-abcdef', 'nvapi-SECRET-000111',
              'hunter2hunter2'):
        assert s not in red
    assert len(red) <= 200
    # un secreto que cruza el borde de truncado tampoco queda a medias
    edge = 'y' * 190 + 'AIzaGEMINI-KEY-123456'
    assert 'AIzaGEMI' not in server._diag_redact(edge)


def test_json_error_responses_never_leak_env_secrets(client, alpaca, nodb, monkeypatch):
    monkeypatch.setenv('ALPACA_SECRET', ALPACA_SECRET_VALUE)
    alpaca.raise_on_get = RuntimeError(f'proxy said: header APCA-API-SECRET-KEY={ALPACA_SECRET_VALUE} rejected')
    r = client.get('/api/trade/account', headers=H())
    assert r.status_code == 502 and ALPACA_SECRET_VALUE not in r.get_data(as_text=True)


def test_ws_token_same_origin_single_use_and_browser_key(client, monkeypatch):
    monkeypatch.setattr(server, 'FINNHUB', 'fh-server-key-000')
    monkeypatch.setenv('FINNHUB_WS_KEY', 'fh-browser-key-111')
    assert client.get('/api/ws-token').status_code == 403                                 # curl / sin origen
    assert client.get('/api/ws-token', headers={'Sec-Fetch-Site': 'cross-site'}).status_code == 403
    assert client.get('/api/ws-token', headers={'Origin': 'https://evil.example'}).status_code == 403
    same = {'Sec-Fetch-Site': 'same-origin', 'X-Forwarded-For': '203.0.113.70'}
    tok = client.get('/api/ws-token', headers=same).get_json()['session_token']
    r = client.post('/api/ws-key', data=json.dumps({'session_token': tok}),
                    headers=dict(same, **{'Content-Type': 'application/json'}))
    assert r.status_code == 200 and r.get_json()['token'] == 'fh-browser-key-111'
    assert r.headers.get('Cache-Control') == 'no-store'
    r = client.post('/api/ws-key', data=json.dumps({'session_token': tok}),
                    headers=dict(same, **{'Content-Type': 'application/json'}))
    assert r.status_code == 401 and r.get_json()['error'] == 'token ya usado'             # un solo uso
    assert r.get_json()['error_en'] == 'token already used'
    # atado a la IP
    tok = client.get('/api/ws-token', headers=same).get_json()['session_token']
    other = {'Sec-Fetch-Site': 'same-origin', 'X-Forwarded-For': '203.0.113.71', 'Content-Type': 'application/json'}
    assert client.post('/api/ws-key', data=json.dumps({'session_token': tok}), headers=other).status_code == 401
    # Origin del mismo host (navegadores sin Sec-Fetch-Site)
    assert client.get('/api/ws-token', headers={'Origin': 'http://localhost'}).status_code == 200
    # cross-origin en ws-key también se rechaza
    assert client.post('/api/ws-key', data=json.dumps({'session_token': tok}),
                       headers={'Sec-Fetch-Site': 'cross-site'}).status_code == 403


def test_secret_key_default_flag(client, monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'a-real-long-random-secret-value')
    assert client.get('/api/health').get_json()['secret_key_default'] is False
    monkeypatch.setenv('SECRET_KEY', 'khipu-dev-secret-change-me')
    assert client.get('/api/health').get_json()['secret_key_default'] is True
    monkeypatch.setenv('RAILWAY_ENVIRONMENT', 'production')
    w = [x for x in server._security_warnings() if x['code'] == 'secret_key_default']
    assert w and w[0]['severity'] == 'critical' and w[0]['es'] and w[0]['en']


@needs_db
def test_mcp_oauth_refuses_default_secret_in_production(client, db, monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'khipu-dev-secret-change-me')
    monkeypatch.setenv('RAILWAY_ENVIRONMENT', 'production')
    r = client.get('/oauth/authorize', query_string={'response_type': 'code', 'client_id': 'x'})
    assert r.status_code == 503 and 'SECRET_KEY' in r.get_data(as_text=True)
    r = client.post('/oauth/authorize', data={'step': 'pin', 'pin': PIN})
    assert r.status_code == 503
    r = client.post('/oauth/register', json={'redirect_uris': ['https://claude.ai/api/mcp/auth_callback']})
    assert r.status_code == 503 and 'SECRET_KEY' in r.get_json()['error_description']
    assert client.get('/api/mcp/status').get_json()['secret_key_insecure'] is True
    # fuera de producción sigue funcionando (registro dinámico)
    monkeypatch.delenv('RAILWAY_ENVIRONMENT')
    r = client.post('/oauth/register', json={'redirect_uris': ['https://claude.ai/api/mcp/auth_callback']})
    assert r.status_code == 201


def test_degraded_fallbacks_are_not_cached(client, monkeypatch):
    """Upstream caído → la ruta responde 200 con lista vacía (la UI no se rompe)
    pero marcada como degradada: no se guarda 30 min / 24 h."""
    monkeypatch.setattr(server, 'FINNHUB', 'fh-k')
    state = {'err': True}
    monkeypatch.setattr(server, '_safe_get', lambda url, *a, **k: (None, 'timeout') if state['err']
                        else ([{'headline': 'ok'}], None))
    r = client.get('/api/news/NVDA')
    assert r.status_code == 200 and r.get_json() == [] and r.headers.get('X-Khipu-Degraded') == '1'
    state['err'] = False
    # el respaldo se repite unos segundos (caché negativa corta, no 30 min)…
    r = client.get('/api/news/NVDA')
    assert r.get_json() == [] and r.headers.get('X-Khipu-Neg-Cache') == '1'
    server.cache.clear()                                           # …y al vencer vuelve el dato real
    assert client.get('/api/news/NVDA').get_json() == [{'headline': 'ok'}]
    state['err'] = True
    assert client.get('/api/news/NVDA').get_json() == [{'headline': 'ok'}]     # el bueno sí quedó en caché


def test_brokerage_never_encrypts_with_public_key_in_production(monkeypatch):
    from brokerage import crypto
    monkeypatch.delenv('BROKERAGE_ENC_KEY', raising=False)
    monkeypatch.setenv('SECRET_KEY', 'khipu-dev-secret-change-me')
    monkeypatch.setenv('RAILWAY_ENVIRONMENT', 'production')
    with pytest.raises(crypto.CryptoUnavailable) as ei:
        crypto.encrypt_json({'key': 'k', 'secret': 's'})
    assert 'BROKERAGE_ENC_KEY' in str(ei.value)
    monkeypatch.setenv('SECRET_KEY', 'a-real-long-random-secret-value')
    assert crypto.decrypt_json(crypto.encrypt_json({'a': 1})) == {'a': 1}


# ════════════════════════════════════════════════════════════════════════════
# 7. Revisión del endurecimiento (fixer SERVER, 2026-09-30)
# ════════════════════════════════════════════════════════════════════════════
@needs_db
def test_committee_pin_uses_shared_counter_and_global_lock(client, db):
    """El comité comparaba el PIN por su cuenta: 50 intentos → 50 × 401, nunca
    429, y el PIN correcto pasaba aunque hubiera bloqueo global."""
    ip = '203.0.113.120'
    for _ in range(10):
        r = client.get('/api/committee/clients', headers=H(pin='wrong', ip=ip))
        assert r.status_code == 401 and r.get_json()['code'] == 'invalid_pin'
    r = client.get('/api/committee/clients', headers=H(ip=ip))                  # PIN correcto, IP bloqueada
    assert r.status_code == 429 and r.get_json()['code'] == 'pin_locked'
    assert client.get('/api/trade/account', headers=H(ip=ip)).status_code == 429   # contador COMPARTIDO
    from core import pin as core_pin
    assert len(core_pin._GLOBAL) == 10
    for i in range(20):
        client.get('/api/committee/clients', headers=H(pin='x', ip=f'192.0.2.{i + 150}'))
    r = client.get('/api/committee/clients', headers=H(ip='198.51.100.150'))
    assert r.status_code == 429 and r.get_json()['code'] == 'pin_locked_global'
    # la vista redactada del memo NO suma fallos con PIN vacío
    before = len(core_pin._GLOBAL)
    client.get('/api/committee/memo/nope', headers=H(pin='', ip='198.51.100.151'))
    assert len(core_pin._GLOBAL) == before


@needs_db
def test_committee_clients_is_rate_limited(client, db):
    codes = [client.get('/api/committee/clients', headers=H(ip='203.0.113.121')).status_code for _ in range(65)]
    assert codes[0] == 200 and codes.count(429) >= 1


def test_sell_limit_far_below_market_is_capped_at_market(client, alpaca, nodb, no_rate):
    """qty × limit_price subestimaba una VENTA limit muy por debajo del mercado
    (se llena al mercado): 1M × $0.10 pasaba el tope y eran ~$100M."""
    alpaca.price = 180.0
    r = _order(client, symbol='NVDA', side='sell', type='limit', qty=1000000, limit_price=0.1)
    assert r.status_code == 400 and r.get_json()['code'] == 'over_cap'
    r = _order(client, symbol='NVDA', side='sell', type='limit', qty=600, limit_price=100)   # 600 × $180 > $100k
    assert r.status_code == 400 and r.get_json()['code'] == 'over_cap'
    assert not alpaca.posts()
    # sin precio de mercado verificable una venta limit se rechaza (una compra limit no lo necesita)
    alpaca.price = 0
    r = _order(client, symbol='NVDA', side='sell', type='limit', qty=1, limit_price=0.1)
    assert r.status_code == 422 and r.get_json()['code'] == 'price_unavailable' and r.get_json()['error_en']
    assert _order(client, symbol='NVDA', side='buy', type='limit', qty=1, limit_price=50).status_code == 200
    alpaca.price = 180.0
    assert _order(client, symbol='NVDA', side='sell', type='limit', qty=10, limit_price=200).status_code == 200


def test_stop_loss_ignores_open_order_on_the_other_side(agent, alpaca, nodb, monkeypatch):
    """Una compra límite abierta (GTC 'comprar la caída') NO es un cierre
    pendiente de una posición larga: antes apagaba el stop-loss."""
    monkeypatch.setitem(agent, 'universe', [])
    alpaca.positions = [{'symbol': 'NVDA', 'asset_class': 'us_equity', 'qty': '10', 'unrealized_plpc': '-0.15',
                         'market_value': '850'}]
    alpaca.open_orders = [{'symbol': 'NVDA', 'side': 'buy', 'type': 'limit', 'limit_price': '50', 'status': 'new'}]
    server._agent_run_cycle()
    posts = alpaca.posts()
    assert len(posts) == 1 and posts[0][3]['side'] == 'sell' and posts[0][3]['qty'] == '10'
    # una VENTA abierta del mismo símbolo sí es un cierre pendiente (no se duplica)
    agent['pending_close'].clear()
    alpaca.open_orders = [{'symbol': 'NVDA', 'side': 'sell', 'status': 'new'}]
    server._agent_run_cycle()
    assert len(alpaca.posts()) == 1
    # corto: el cierre es una COMPRA
    agent['pending_close'].clear()
    alpaca.positions = [{'symbol': 'AMD', 'qty': '-4', 'unrealized_plpc': '-0.2', 'market_value': '-400'}]
    alpaca.open_orders = [{'symbol': 'AMD', 'side': 'sell', 'status': 'new'}]
    server._agent_run_cycle()
    assert alpaca.posts()[-1][3]['side'] == 'buy' and alpaca.posts()[-1][3]['symbol'] == 'AMD'


def test_global_lock_keeps_trusted_owner_ip_for_emergency_actions(client, alpaca, nodb, no_rate, agent,
                                                                  monkeypatch):
    """3 IPs × 10 fallos dejaban al dueño sin cerrar posiciones ni parar el
    agente (429 aun con el PIN correcto). Una IP que acertó el PIN hace poco
    sigue pasando; una IP nueva no (sin oráculo para una botnet)."""
    owner = '198.51.100.10'
    assert client.get('/api/trade/account', headers=H(ip=owner)).status_code == 200      # IP de confianza
    for i in range(30):
        assert client.get('/api/trade/account', headers=H(pin='bad', ip=f'192.0.2.{i + 1}')).status_code == 401
    fresh = client.post('/api/trade/close', data=json.dumps({'symbol': 'NVDA'}), headers=H(ip='198.51.100.99'))
    assert fresh.status_code == 429 and fresh.get_json()['code'] == 'pin_locked_global'
    r = client.post('/api/trade/close', data=json.dumps({'symbol': 'NVDA'}), headers=H(ip=owner))
    assert r.status_code == 200
    r = client.post('/api/trade/agent/stop', headers=H(ip=owner))
    assert r.status_code == 200 and r.get_json()['status'] == 'stopping'
    # la IP de confianza con 3 fallos propios pierde el atajo
    for _ in range(3):
        assert client.get('/api/trade/account', headers=H(pin='oops', ip=owner)).status_code == 401
    r = client.post('/api/trade/agent/stop', headers=H(ip=owner))
    assert r.status_code == 429 and r.get_json()['code'] == 'pin_locked_global'


def test_mcp_own_lock_lets_trusted_owner_revoke(client, alpaca, nodb):
    """El bloqueo propio de MCP (10 PIN malos/hora → 30 min) sigue frenando
    todo, salvo listar/REVOCAR tokens desde una IP de confianza (emergencia)."""
    owner = '198.51.100.11'
    assert client.get('/api/trade/account', headers=H(ip=owner)).status_code == 200
    for i in range(10):                                  # 10 fallos en MCP → bloqueo propio de MCP (30 min)
        client.get('/api/mcp/tokens', headers=H(pin='zz', ip=f'192.0.2.{i + 60}'))
    r = client.get('/api/mcp/tokens', headers=H(ip='198.51.100.98'))
    assert r.status_code == 429
    assert client.get('/api/mcp/tokens', headers=H(ip=owner)).status_code == 503         # pasa el PIN (sin base)
    assert client.post('/api/mcp/tokens/t1/revoke', headers=H(ip=owner), data='{}').status_code == 503
    assert client.post('/api/mcp/tokens/t1/revoke', headers=H(ip='198.51.100.97'), data='{}').status_code == 429
    assert client.get('/api/mcp/audit', headers=H(ip=owner)).status_code == 429          # lo demás, bloqueado


@pytest.mark.parametrize('url', ['/api/trade/order', '/api/trade/close', '/api/trade/agent/start',
                                 '/api/trade/agent/config'])
@pytest.mark.parametrize('body', ['[1, 2]', '"NVDA"', '42'])
def test_non_object_json_body_is_a_bilingual_400(client, alpaca, nodb, no_rate, agent, monkeypatch, url, body):
    monkeypatch.setitem(agent, 'running', False)
    r = client.post(url, data=body, headers=H())
    assert r.status_code == 400, (url, body, r.get_data(as_text=True)[:200])
    d = r.get_json()
    assert d['code'] == 'bad_json' and d['error'] and d['error_en']
    assert not alpaca.posts()


def test_paper_is_decided_by_host_not_substring(monkeypatch):
    for base, paper in (('https://paper-api.alpaca.markets', True), ('https://paper-api.alpaca.markets/v2', True),
                        ('https://api.alpaca.markets', False), ('https://paper-proxy.example.com', False),
                        ('https://api.alpaca.markets/?paper=1', False), ('', False)):
        monkeypatch.setattr(server, 'ALPACA_BASE', base)
        assert server._paper() is paper, base
    assert server._account_is_live({'account_number': 'PA3XYZ'}) is False
    assert server._account_is_live({'account_number': '6AB12345'}) is True
    assert server._account_is_live({}) is None


def test_agent_blocks_when_account_number_is_live(agent, alpaca, nodb, monkeypatch):
    orig = alpaca.get

    def get(url, **k):
        if url.endswith('/v2/account'):
            return FakeResp(200, {'equity': '10000', 'last_equity': '10000', 'account_number': '6AB123'})
        return orig(url, **k)
    monkeypatch.setattr(requests, 'get', get)
    server._agent_run_cycle()
    assert not alpaca.posts()
    assert any('DINERO REAL' in (x.get('msg') or '') for x in agent['log'])


def test_redaction_catches_prefixed_key_names_and_text_errors():
    from core.http import redact_secrets
    for raw, secret in (('https://api.marketstack.com/v1/eod?access_key=abcdef1234567&symbols=X', 'abcdef1234567'),
                        ('https://api.coingecko.com/x?x_cg_demo_api_key=CG-abc123def456', 'CG-abc123def456'),
                        ('header x-api-key: sk-1234567890', 'sk-1234567890')):
        assert secret not in redact_secrets(raw), raw
    assert redact_secrets('monkey: banana') == 'monkey: banana'
    t0 = time.time()
    redact_secrets('-a' * 130000)                       # sin retroceso cuadrático
    assert time.time() - t0 < 2
    from flask import Response
    with server.app.test_request_context('/api/x'):
        resp = Response('boom https://x.example/?access_key=abcdef1234567', status=500, mimetype='text/html')
        out = server._redact_secrets_in_json(resp)
        assert 'abcdef1234567' not in out.get_data(as_text=True)
        ok = Response('access_key=abcdef1234567', status=200, mimetype='text/html')   # 200 HTML: no se toca
        assert 'abcdef1234567' in server._redact_secrets_in_json(ok).get_data(as_text=True)


def test_voice_admin_routes_need_operator_pin(client, monkeypatch):
    monkeypatch.setenv('ELEVENLABS_ALLOW_OVERRIDE', '1')
    called = []
    monkeypatch.setattr(server, '_sync_bixby_agent', lambda: called.append(1) or {'ok': True})
    for method, url in (('post', '/api/voice/adopt'), ('post', '/api/voice/agent-tune'),
                        ('get', '/api/voice/sync-agent'), ('post', '/api/voice/sync-agent')):
        r = getattr(client, method)(url, data='{}', headers=H(pin=None))
        assert r.status_code == 401 and r.get_json()['code'] == 'invalid_pin', url
    assert not called
    r = client.post('/api/voice/sync-agent', headers=H())
    assert r.status_code == 200 and called
    monkeypatch.setattr(server, 'ELEVENLABS_KEY', 'el-key-000000')
    r = client.post('/api/voice/adopt', data=json.dumps({'public_owner_id': '../x', 'voice_id': 'v'}), headers=H())
    assert r.status_code == 400 and r.get_json()['error_en']
    monkeypatch.delenv('ELEVENLABS_ALLOW_OVERRIDE')
    r = client.post('/api/voice/agent-tune', data='{}', headers=H())
    assert r.status_code == 403 and r.get_json()['error_en']
    # sin TRADE_PIN (desarrollo) se permiten, como las escrituras de la ontología
    monkeypatch.delenv('TRADE_PIN')
    assert client.post('/api/voice/sync-agent').status_code == 200


def test_security_warnings_recommend_browser_finnhub_key(monkeypatch):
    monkeypatch.setattr(server, 'FINNHUB', 'fh-server-key-000')
    assert any(w['code'] == 'finnhub_ws_key_missing' and w['es'] and w['en'] for w in server._security_warnings())
    monkeypatch.setenv('FINNHUB_WS_KEY', 'fh-browser-key-111')
    assert not any(w['code'] == 'finnhub_ws_key_missing' for w in server._security_warnings())


def test_remigrate_gate_defers_to_the_database_name_check():
    """server.py solo mira que REMIGRATE_ON_BOOT exista; el script exige el
    nombre de la base (antes '1'/'true' en el server vs nombre en el script:
    la re-migración nunca podía correr)."""
    import inspect
    src = inspect.getsource(server)
    assert "if os.getenv('REMIGRATE_ON_BOOT', '').strip():" in src
    assert "os.getenv('REMIGRATE_ON_BOOT', '').strip() in (" not in src


def test_negative_cache_never_outlives_the_route_cache(client, monkeypatch):
    """/api/scalp/price cachea 2 s: su fallo no puede repetirse 60 s."""
    monkeypatch.setattr(server, 'FINNHUB', 'fh-k')
    monkeypatch.setattr(server, '_fetch_quote_raw', lambda *a, **k: (None, 'timeout'))
    sets = []
    orig = server.cache.set

    def spy(key, value, timeout=None):
        sets.append((key, timeout))
        return orig(key, value, timeout=timeout)
    monkeypatch.setattr(server.cache, 'set', spy)
    assert client.get('/api/scalp/price/NVDA').status_code == 502
    assert client.get('/vendor/nope.js').status_code == 404               # un 404 no entra en la caché negativa
    neg = [t for k, t in sets if k.startswith('neg:')]
    assert neg == [2]
