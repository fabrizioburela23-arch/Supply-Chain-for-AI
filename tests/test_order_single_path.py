"""tests/test_order_single_path.py — INFRA_OPERATIVA pasos 15-16 (BRECHAS G5-01, M-code-03, G5-08 servidor):
UN SOLO CAMINO DE DINERO.

Antes la cuenta de la casa recibía órdenes por TRES caminos con controles distintos (brokerage.service, server.py
/api/trade/order y el agente de trading con requests.post directo) y /api/trade/close liquidaba con un DELETE sin
controles. Ahora TODOS — panel (ui), cripto, voz, terminal, Cabina, cierre de posición, agente de trading, MCP y
comité — pasan por brokerage.service (preview_order → confirm_order → AlpacaClient.submit_order) con:
  · los MISMOS controles (brokerage.risk.run_checks; la casa con los límites de HOY: US$100.000 por orden y los
    topes nuevos solo en SOMBRA mientras BRECHAS #1 siga abierta);
  · client_order_id (el del navegador o uno del servidor) e idempotencia (un reintento nunca duplica);
  · broker_audit y el libro de decisiones (order.preview → order.confirm → order.submit; approval.* al aprobar);
  · el candado del libro para dinero real (money_gate) y el doble candado BROKERAGE_LIVE_ENABLED + live_enabled.
Sin red: Alpaca es un bróker FALSO en la capa HTTP (monkeypatch de requests). NUNCA se envía una orden real: las
pruebas con dinero real solo comprueban que se BLOQUEA.

    DATABASE_URL=postgresql://postgres:devpass@localhost:5432/khipus_e2 python3 -m pytest tests/test_order_single_path.py -q
"""
import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('FINNHUB_KEY', '')
os.environ.setdefault('ANTHROPIC_KEY', '')

import requests  # noqa: E402

import server  # noqa: E402

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
PIN = '4321-strong-pin'
PAPER = 'https://paper-api.alpaca.markets'
LIVE = 'https://api.alpaca.markets'


# ════════════════════════════════════════════════════════════════════════════
# Bróker falso en la capa HTTP (formas de JSON de Alpaca: números como strings)
# ════════════════════════════════════════════════════════════════════════════
class R:
    def __init__(self, status, payload=None):
        self.status_code, self._p = status, payload
        self.ok = 200 <= status < 300
        self.text = json.dumps(payload) if payload is not None else ''
        self.content = self.text.encode()
        self.headers = {'Content-Type': 'application/json'}

    def json(self):
        if self._p is None:
            raise ValueError('no json')
        return self._p


class HTTPAlpaca:
    def __init__(self):
        self.calls, self.orders, self.positions = [], {}, []
        self.price, self.reject = 100.0, None
        self.account = {'equity': '10000', 'cash': '10000', 'buying_power': '20000', 'last_equity': '10000',
                        'status': 'ACTIVE', 'account_number': 'PA123'}

    def posts(self):
        return [c for c in self.calls if c[0] == 'POST' and c[1].endswith('/v2/orders')]

    def request(self, method, url, headers=None, params=None, json=None, timeout=None, **_k):  # noqa: A002
        m = str(method).upper()
        self.calls.append((m, url, params, json))
        if m == 'POST' and url.endswith('/v2/orders'):
            if self.reject:
                return R(self.reject[0], {'code': 40310000, 'message': self.reject[1]})
            coid = (json or {}).get('client_order_id')
            if coid in self.orders:
                return R(422, {'code': 40010001, 'message': 'client_order_id must be unique'})
            o = dict(json or {}, id=f'ord-{id(self):x}-{len(self.orders) + 1}', status='accepted', filled_qty='0')
            self.orders[coid] = o
            return R(200, dict(o))
        if m == 'DELETE':
            return R(200, {'id': 'del', 'status': 'accepted'})
        if url.endswith('/v2/account'):
            return R(200, dict(self.account))
        if url.endswith('/v2/positions'):
            return R(200, list(self.positions))
        if url.endswith('/v2/clock'):
            return R(200, {'is_open': True})
        if '/v2/orders:by_client_order_id' in url:
            o = self.orders.get((params or {}).get('client_order_id'))
            return R(200, dict(o)) if o else R(404, {'message': 'order not found'})
        if '/v2/orders/' in url:
            oid = url.rsplit('/', 1)[1]
            o = next((x for x in self.orders.values() if x['id'] == oid), None)
            return R(200, dict(o)) if o else R(404, {'message': 'nf'})
        if url.endswith('/v2/assets') and (params or {}).get('asset_class') == 'crypto':
            return R(200, [{'symbol': 'BTC/USD', 'name': 'Bitcoin', 'tradable': True}])
        if '/v2/assets/' in url:
            return R(200, {'symbol': url.rsplit('/', 1)[1], 'tradable': True, 'status': 'active'})
        if 'data.alpaca.markets' in url and 'crypto' in url:
            return R(200, {'trades': {(params or {}).get('symbols'): {'p': 60000.0}}})
        if 'data.alpaca.markets/v2/stocks' in url:
            return R(200, {'trade': {'p': self.price}}) if self.price else R(404, {'message': 'nf'})
        if 'gdeltproject' in url:
            return R(200, {'tonechart': []})
        return R(404, {'message': 'unknown ' + url})

    def get(self, url, **k):
        return self.request('GET', url, **k)

    def post(self, url, **k):
        return self.request('POST', url, **k)

    def delete(self, url, **k):
        return self.request('DELETE', url, **k)


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.setenv('TRADE_PIN', PIN)
    for k in ('BROKERAGE_TRADING_ENABLED', 'BROKERAGE_LIVE_ENABLED', 'BROKERAGE_AUTO_APPROVE_PAPER',
              'RAILWAY_ENVIRONMENT', 'RAILWAY_ENVIRONMENT_NAME', 'RAILWAY_PROJECT_ID'):
        monkeypatch.delenv(k, raising=False)
    from core import http as core_http
    from core import pin as core_pin
    core_http._rate_buckets.clear()
    core_pin._reset_for_tests()
    monkeypatch.setattr(core_http, '_rate_limit', lambda *a, **k: True)
    server._crypto_assets_cache.clear()
    server._TRADABLE_CACHE.clear()
    yield


def _base(monkeypatch, fake, base):
    monkeypatch.setattr(server, 'ALPACA_BASE', base)
    monkeypatch.setenv('ALPACA_BASE', base)


@pytest.fixture
def alpaca(monkeypatch):
    fake = HTTPAlpaca()
    for name in ('request', 'get', 'post', 'delete'):
        monkeypatch.setattr(requests, name, getattr(fake, name))
    monkeypatch.setattr(server, 'ALPACA_KEY', 'PKFAKEKEY0001')
    monkeypatch.setattr(server, 'ALPACA_SECRET', 'FAKE-SECRET-123')
    monkeypatch.setattr(server, 'FINNHUB', '')
    monkeypatch.setenv('ALPACA_KEY', 'PKFAKEKEY0001')
    monkeypatch.setenv('ALPACA_SECRET', 'FAKE-SECRET-123')
    _base(monkeypatch, fake, PAPER)
    return fake


@pytest.fixture
def nodb(monkeypatch):
    import ontology.db as odb
    monkeypatch.setattr(odb, 'DATABASE_URL', '')


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
    import research.models  # noqa: F401
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    yield
    Base.metadata.drop_all(engine)


def H(channel=None, **extra):
    h = {'Content-Type': 'application/json', 'X-Trade-Pin': PIN}
    if channel:
        h['X-Khipu-Channel'] = channel
    h.update(extra)
    return h


def _order(client, channel=None, **body):
    return client.post('/api/trade/order', data=json.dumps(body), headers=H(channel))


# ════════════════════════════════════════════════════════════════════════════
# 1. Estático: UN solo lugar del servidor envía o cierra órdenes en Alpaca
# ════════════════════════════════════════════════════════════════════════════
_SEND = re.compile(r"(requests\.(post|delete)\(|\.request\(|['\"](POST|DELETE)['\"])")


def test_only_brokerage_alpaca_sends_orders():
    hits = []
    for dirpath, dirs, files in os.walk(ROOT):
        rel = os.path.relpath(dirpath, ROOT)
        if rel.split(os.sep)[0] in ('tests', 'vault', 'node_modules', '.git', 'scripts', 'data', 'docs'):
            dirs[:] = []
            continue
        for f in files:
            if not f.endswith('.py'):
                continue
            path = os.path.join(dirpath, f)
            with open(path, encoding='utf-8') as fh:
                lines = fh.read().splitlines()
            for i, line in enumerate(lines):
                if ('/v2/orders' in line or '/v2/positions' in line) and _SEND.search(line):
                    hits.append(f'{os.path.relpath(path, ROOT)}:{i + 1}')
    assert hits and all(h.startswith('brokerage/alpaca.py:') for h in hits), hits
    src = open(os.path.join(ROOT, 'server.py'), encoding='utf-8').read()
    assert "requests.post(f'{ALPACA_BASE}/v2/orders'" not in src and '/v2/positions/{path_sym}' not in src
    assert 'house_order' in src and 'house_close' in src


# ════════════════════════════════════════════════════════════════════════════
# 2. Sin base (desarrollo, papel — D4): cada camino corre run_checks y sale por AlpacaClient.submit_order
# ════════════════════════════════════════════════════════════════════════════
@pytest.fixture
def spies(monkeypatch):
    from brokerage import alpaca as A
    from brokerage import risk
    seen = {'checks': 0, 'submits': []}
    orig_run, orig_submit = risk.run_checks, A.AlpacaClient.submit_order

    def run(ctx):
        seen['checks'] += 1
        return orig_run(ctx)

    def submit(self, *a, **k):
        seen['submits'].append(k.get('client_order_id'))
        return orig_submit(self, *a, **k)
    monkeypatch.setattr(risk, 'run_checks', run)
    monkeypatch.setattr(A.AlpacaClient, 'submit_order', submit)
    return seen


@pytest.mark.parametrize('channel', ['ui', 'crypto', 'voice', 'terminal'])
def test_every_ui_channel_uses_the_service_without_db(client, alpaca, nodb, spies, channel):
    sym = 'BTC/USD' if channel == 'crypto' else 'NVDA'
    r = _order(client, channel, symbol=sym, side='buy', notional=25, client_order_id=f'kh-{channel}-0001')
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    assert d['id'] and d['paper'] is True and d['order']['client_order_id'] == f'kh-{channel}-0001'
    assert spies['checks'] >= 1 and spies['submits'] == [f'kh-{channel}-0001']
    assert alpaca.posts()[-1][3]['client_order_id'] == f'kh-{channel}-0001'


def test_close_and_agent_use_the_service_without_db(client, alpaca, nodb, spies, monkeypatch):
    alpaca.positions = [{'symbol': 'NVDA', 'qty': '3', 'side': 'long', 'market_value': '300', 'current_price': '100'}]
    r = client.post('/api/trade/close', data=json.dumps({'symbol': 'NVDA'}), headers=H())
    assert r.status_code == 200 and alpaca.posts()[-1][3]['qty'] == '3' and alpaca.posts()[-1][3]['side'] == 'sell'
    n = len(spies['submits'])
    for k, v in (('running', True), ('mode', 'auto'), ('universe', ['AMD']), ('log', []), ('pending_close', {}),
                 ('daily_pnl_pct', 0.0), ('min_confidence', 65), ('max_orders_per_cycle', 3), ('max_pos_pct', 5.0),
                 ('stop_loss_pct', 3.0)):
        monkeypatch.setitem(server._AGENT, k, v)
    monkeypatch.setattr(server._trading_agent, '_agent_analyze',
                        lambda *a, **k: {'action': 'buy', 'confidence': 90, 'reason': 't', 'size_pct': 2})
    monkeypatch.setattr(server, 'FINNHUB', 'fh')
    monkeypatch.setattr(server, '_fetch_quote_raw', lambda t, timeout=8: ({'c': 100.0, 'pc': 99.0}, None))
    server._agent_run_cycle()
    assert len(spies['submits']) == n + 1 and spies['submits'][-1].startswith('kh-agent-')
    assert [e for e in server._AGENT['log'] if e.get('ticker') == 'AMD'][-1]['executed'] is True


def test_no_db_rules_d4(alpaca, nodb, monkeypatch):
    """D4: sin base solo desarrollo + PAPEL. En producción, sin libro no hay órdenes; con dinero real tampoco."""
    from brokerage import service
    monkeypatch.setenv('RAILWAY_ENVIRONMENT', 'production')
    r = service.house_order(None, 'NVDA', 'buy', notional=10)
    assert r['code'] == 'ledger_unavailable' and r['error_en']
    monkeypatch.delenv('RAILWAY_ENVIRONMENT')
    _base(monkeypatch, alpaca, LIVE)
    r = service.house_order(None, 'NVDA', 'buy', notional=10)
    assert r['code'] == 'paper_only_without_db' and r['error_en']
    assert not alpaca.posts()


def test_house_keeps_todays_limits_without_db(client, alpaca, nodb):
    """BRECHAS #1 sin respuesta: US$100.000 por orden (también ventas), ningún tope nuevo que bloquee."""
    r = _order(client, symbol='NVDA', side='buy', notional=20000)     # > orden y diario del perfil moderado
    d = r.get_json()
    assert r.status_code == 200, d
    assert any('BRECHAS #1' in (w or '') for w in d.get('warnings') or []), d.get('warnings')
    r = _order(client, symbol='NVDA', side='buy', qty=1001)            # 1001 × $100 > $100k
    assert r.status_code == 400 and r.get_json()['code'] == 'over_cap'
    r = _order(client, symbol='NVDA', side='sell', qty=1001)           # las ventas también (como hasta hoy)
    assert r.status_code == 400 and r.get_json()['code'] == 'over_cap'
    assert len(alpaca.posts()) == 1


def test_exits_are_never_blocked_by_the_per_order_cap(client, alpaca, nodb):
    """Revisión batch E: CLOSE de una posición > US$100.000 (antes DELETE /v2/positions, sin tope) NO se frena por
    el tope por orden; solo hasta la cantidad que se tiene. Abrir/aumentar exposición sigue con el tope."""
    from brokerage import risk, service
    alpaca.positions = [{'symbol': 'NVDA', 'qty': '1500', 'side': 'long', 'market_value': '150000',
                         'current_price': '100', 'asset_class': 'us_equity'}]
    r = client.post('/api/trade/close', data=json.dumps({'symbol': 'NVDA'}), headers=H())
    assert r.status_code == 200, r.get_json()
    assert alpaca.posts()[-1][3]['qty'] == '1500' and alpaca.posts()[-1][3]['side'] == 'sell'
    # vender MÁS de lo que se tiene por la vía de salida → vuelve el tope (no es una salida)
    d = service.house_order(None, 'NVDA', 'sell', qty=1600, checks_mode='house_reduce')
    assert d.get('code') == 'over_cap' or 'order_size' in (d.get('failed_checks') or []), d
    # comprar (aumentar) con la vía de salida → tope de siempre
    d = service.house_order(None, 'NVDA', 'buy', qty=1500, checks_mode='house_reduce')
    assert 'order_size' in (d.get('failed_checks') or []), d
    # el panel normal sigue con el tope también en ventas (como hasta hoy)
    r = _order(client, symbol='NVDA', side='sell', qty=1001)
    assert r.status_code == 400 and r.get_json()['code'] == 'over_cap'
    # una corta grande también se puede cerrar (compra hasta la cantidad en corto)
    alpaca.positions = [{'symbol': 'AMD', 'qty': '-1200', 'side': 'short', 'market_value': '-120000',
                         'current_price': '100', 'asset_class': 'us_equity'}]
    r = client.post('/api/trade/close', data=json.dumps({'symbol': 'AMD'}), headers=H())
    assert r.status_code == 200 and alpaca.posts()[-1][3]['side'] == 'buy', r.get_json()
    assert risk.reduces_position({'symbol': 'AMD', 'side': 'buy', 'qty': 1200}, alpaca.positions)
    assert not risk.reduces_position({'symbol': 'AMD', 'side': 'buy', 'notional': 5000}, alpaca.positions)


def test_agent_failure_after_send_is_unknown_and_blocks_a_resend(alpaca, nodb, monkeypatch):
    """Revisión batch E: si el agente falla DESPUÉS de tocar Alpaca, la orden queda DESCONOCIDA (no «nada salió») y
    el ticker no se vuelve a operar (ni otro stop-loss que podría abrir un corto) durante la ventana de pendientes."""
    from brokerage import service
    monkeypatch.setitem(server._AGENT, 'unknown_orders', {})

    def boom(session, symbol, side, **kw):
        service._SEND_TRACE.coids.append(kw.get('client_order_id'))
        raise RuntimeError('commit failed')
    monkeypatch.setattr(service, 'house_order', boom)
    with pytest.raises(server._AgentOrderError) as ei:
        server._agent_order({'symbol': 'NVDA', 'side': 'buy', 'notional': 50, 'time_in_force': 'day'},
                            'agent_order', {'symbol': 'NVDA'})
    assert getattr(ei.value, 'unknown', False) is True and 'UNKNOWN' in str(ei.value)
    assert 'NVDA' in server._AGENT['unknown_orders']


# ════════════════════════════════════════════════════════════════════════════
# 3. Con base: la MISMA huella por cada camino (fila, client_order_id, auditoría, decisiones)
# ════════════════════════════════════════════════════════════════════════════
def _row_by_coid(coid):
    from ontology.db import session_scope
    from brokerage.models import BrokerOrder
    with session_scope() as s:
        r = s.query(BrokerOrder).filter(BrokerOrder.client_order_id == coid).one()
        s.expunge(r)
        return r


def _decisions(**where):
    from sqlalchemy import text
    from ontology.db import session_scope
    cond = ' AND '.join(f"{k} = :{k}" for k in where) or 'true'
    with session_scope() as s:
        return [dict(r._mapping) for r in s.execute(text(
            f'SELECT id, kind, status, parent_id, principal_id, channel, subject, manifest, verdict, output '
            f'FROM decisions WHERE {cond} ORDER BY seq'), where)]


def _dec(did):
    rows = _decisions(id=str(did))
    return rows[0] if rows else None


def _audit(order_id):
    from ontology.db import session_scope
    from brokerage.service import list_audit
    with session_scope() as s:
        return [a['action'] for a in list_audit(s, limit=500) if a['order_id'] == order_id]


def _chain(row):
    """preview → confirm → submit, encadenadas por parent_id, con los estados esperados."""
    m = row.meta or {}
    pv, cf, sb = (_dec(m['preview_decision_id']), _dec(m['confirm_decision_id']), _dec(m['submit_decision_id']))
    assert pv['kind'] == 'order.preview' and pv['status'] == 'proposed'
    assert cf['kind'] == 'order.confirm' and cf['status'] == 'approved' and cf['parent_id'] == pv['id']
    assert sb['kind'] == 'order.submit' and sb['status'] == 'executed' and sb['parent_id'] == cf['id']
    assert sb['output']['client_order_id'] == row.client_order_id
    q = (pv['manifest'].get('quotes') or [{}])[0]
    assert q.get('px') and q.get('src') and q.get('as_of')                  # lo que el sistema SABÍA
    assert pv['manifest']['release']['hash'] and pv['manifest']['checks_mode'] in ('house_today', 'house_reduce',
                                                                                    'standard')
    return pv, cf, sb


@needs_db
@pytest.mark.parametrize('channel', ['ui', 'crypto', 'voice', 'terminal'])
def test_every_channel_leaves_the_same_trail(db, client, alpaca, channel):
    sym = 'BTC/USD' if channel == 'crypto' else 'NVDA'
    coid = f'kh-trail-{channel}-01'
    body = dict(symbol=sym, side='buy', notional=30, client_order_id=coid)
    if channel == 'voice':
        body.update(readback_sha='a' * 64, confirmed_at='2026-10-13T10:00:00Z')
    r = _order(client, channel, **body)
    assert r.status_code == 200, r.get_json()
    assert r.get_json()['decision_id'] and alpaca.posts()[-1][3]['client_order_id'] == coid
    row = _row_by_coid(coid)
    assert row.client_id == 'house' and row.source == 'ui' and row.status == 'submitted' and row.alpaca_order_id
    assert row.meta['channel'] == channel and row.meta['checks_mode'] == 'house_today'
    acts = _audit(row.id)
    assert 'order_previewed' in acts and 'order_submitted' in acts
    pv, cf, sb = _chain(row)
    assert sb['channel'] == channel and pv['principal_id'] == 'op:fabrizio'
    if channel == 'voice':
        assert sb['manifest']['channel_proof']['readback_sha'] == 'a' * 64
        assert cf['manifest']['channel_proof']['confirmed_at'] == '2026-10-13T10:00:00Z'


@needs_db
def test_close_leaves_the_same_trail(db, client, alpaca):
    alpaca.positions = [{'symbol': 'AMD', 'qty': '7', 'side': 'long', 'market_value': '700', 'current_price': '100'}]
    r = client.post('/api/trade/close', data=json.dumps({'symbol': 'AMD', 'client_order_id': 'kh-close-amd-001'}),
                    headers=H('terminal'))
    assert r.status_code == 200, r.get_json()
    row = _row_by_coid('kh-close-amd-001')
    assert row.side == 'sell' and row.qty == 7 and row.order_type == 'market'
    _chain(row)
    assert not [c for c in alpaca.calls if c[0] == 'DELETE']


@needs_db
@pytest.mark.parametrize('exc', ['op', 'generic'])
def test_commit_failure_after_send_is_unknown_never_nothing_sent(db, client, alpaca, exc, monkeypatch):
    """Revisión batch E: si la transacción falla DESPUÉS de que Alpaca aceptó la orden (commit caído, timeout), la
    respuesta es «estado desconocido» (502, con su client_order_id: el navegador lo conserva), queda un rastro
    durable aparte, y el reintento con el MISMO id ADOPTA la orden de Alpaca en vez de crear otra."""
    import contextlib
    import ontology.db as odb
    from brokerage.models import BrokerAudit, BrokerOrder
    from sqlalchemy.exc import OperationalError
    real = odb.session_scope

    @contextlib.contextmanager
    def flaky():
        s = odb.get_session_factory()()
        n0 = len(alpaca.posts())
        try:
            yield s
            if len(alpaca.posts()) > n0:
                if exc == 'op':
                    raise OperationalError('COMMIT', {}, Exception('server closed the connection unexpectedly'))
                raise RuntimeError('commit failed')
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()
    monkeypatch.setattr(odb, 'session_scope', flaky)
    coid = f'kh-commitfail-{exc}-01'
    r = _order(client, symbol='NVDA', side='buy', notional=50, client_order_id=coid)
    d = r.get_json()
    assert r.status_code == 502 and d['code'] == 'broker_unreachable', d
    assert d['client_order_id'] == coid and 'nothing was sent' not in d['error_en'] and 'UNKNOWN' in d['error_en']
    assert len(alpaca.posts()) == 1
    monkeypatch.setattr(odb, 'session_scope', real)
    with real() as s:
        assert s.query(BrokerOrder).filter(BrokerOrder.client_order_id == coid).count() == 0   # revertida…
        trail = [a.detail for a in s.query(BrokerAudit).filter(BrokerAudit.action == 'order_unknown_after_send')]
        assert any(t.get('client_order_id') == coid for t in trail)                         # …pero con rastro
    # el reintento idéntico (mismo client_order_id) adopta la orden que Alpaca YA tiene: ninguna orden nueva
    r = _order(client, symbol='NVDA', side='buy', notional=50, client_order_id=coid)
    assert r.status_code == 200, r.get_json()
    assert len(alpaca.orders) == 1 and r.get_json()['id'] == alpaca.orders[coid]['id']
    row = _row_by_coid(coid)
    assert row is not None and row.alpaca_order_id == alpaca.orders[coid]['id']


@needs_db
def test_mcp_and_human_approval_share_the_path(db, alpaca, monkeypatch):
    """MCP propone (pending) → una persona con PIN aprueba → approval.grant → confirm → submit (mismo envío)."""
    from core import identity
    from ontology.db import session_scope
    from brokerage import service
    with identity.use(identity.mcp('tok1', 'Claude')):
        with session_scope() as s:
            p = service.preview_order(s, 'house', 'AAPL', 'buy', notional=40, source='mcp', requested_by='mcp:tok1',
                                      rationale='prueba del camino único')
    assert p['ok'] and p['status'] == 'pending_approval', p
    pvd = _dec(p['decision_id'])
    assert pvd['status'] == 'pending_approval' and pvd['principal_id'] == 'mcp:tok1'
    with identity.use(identity.operator('ui')):
        with session_scope() as s:
            res = service.approve_preview(s, p['id'], 'op:fabrizio')
    assert res['ok'] and res['status'] == 'submitted', res
    row = _row_by_coid(p['id'])
    cf, sb = _dec(row.meta['confirm_decision_id']), _dec(row.meta['submit_decision_id'])
    ap = _dec(cf['parent_id'])
    assert ap['kind'] == 'approval.grant' and ap['status'] == 'approved' and ap['parent_id'] == pvd['id']
    assert ap['principal_id'] == 'op:fabrizio' and sb['parent_id'] == cf['id']
    assert alpaca.posts()[-1][3]['client_order_id'] == p['id']


@needs_db
def test_duplicate_client_order_id_never_sends_twice(db, client, alpaca):
    coid = 'kh-dup-000111222'
    r1 = _order(client, symbol='NVDA', side='buy', notional=11, client_order_id=coid)
    r2 = _order(client, symbol='NVDA', side='buy', notional=11, client_order_id=coid)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r2.get_json()['duplicate'] is True and r2.get_json()['id'] == r1.get_json()['id']
    assert len([p for p in alpaca.posts() if p[3]['client_order_id'] == coid]) == 1
    # un id cuya orden se BLOQUEÓ (nunca llegó a Alpaca) se puede reutilizar
    coid2 = 'kh-reuse-0001112'
    r = _order(client, symbol='NVDA', side='buy', qty=5000, client_order_id=coid2)
    assert r.status_code == 400 and r.get_json()['code'] == 'over_cap'
    assert _order(client, symbol='NVDA', side='buy', notional=12, client_order_id=coid2).status_code == 200


@needs_db
def test_house_todays_limits_are_shadow_in_the_ledger(db, client, alpaca):
    """Los topes del perfil moderado NO bloquean a la casa (BRECHAS #1) pero quedan en el libro como aviso."""
    coid = 'kh-shadow-000123'
    r = _order(client, symbol='NVDA', side='buy', notional=20000, client_order_id=coid)
    assert r.status_code == 200, r.get_json()
    from sqlalchemy import text
    from ontology.db import session_scope
    row = _row_by_coid(coid)
    with session_scope() as s:
        v = s.execute(text('SELECT rule_iri, severity, value FROM decision_violations WHERE decision_id = '
                           'CAST(:d AS uuid)'), {'d': row.meta['preview_decision_id']}).all()
    enforced = {x.rule_iri: x.severity for x in v if (x.value or {}).get('engine') == 'run_checks@1'}
    assert enforced.get('khr:order.daily_cap') == 'warn' and 'block' not in enforced.values(), enforced
    gates = {x.rule_iri for x in v if (x.value or {}).get('gate') == 'order.pre_trade'}
    assert 'khr:order.daily_cap' in gates                     # la puerta compilada (sombra) ve lo mismo


@needs_db
def test_live_house_needs_both_locks_and_the_ledger(db, client, alpaca, monkeypatch):
    """Dinero real: sin BROKERAGE_LIVE_ENABLED=on + «dinero real habilitado» en la casa → 403; cadena del libro
    rota → 423. En NINGÚN caso sale una orden (las pruebas jamás envían una orden real)."""
    _base(monkeypatch, alpaca, LIVE)
    alpaca.account['account_number'] = '6AB123'
    r = _order(client, symbol='NVDA', side='buy', notional=10)
    assert r.status_code == 403 and r.get_json()['code'] == 'live_not_enabled', r.get_json()
    monkeypatch.setenv('BROKERAGE_LIVE_ENABLED', 'on')               # el cliente casa sigue SIN live_enabled
    r = _order(client, symbol='NVDA', side='buy', notional=10)
    assert r.status_code == 403 and r.get_json()['code'] == 'live_not_enabled'
    import core.ledger as L
    monkeypatch.setattr(L, 'money_gate', lambda engine=None: (False, 'rota', 'broken'))
    r = _order(client, symbol='NVDA', side='buy', notional=10)
    assert r.status_code == 423 and r.get_json()['code'] == 'ledger_chain_broken'
    alpaca.positions = [{'symbol': 'NVDA', 'qty': '1', 'side': 'long', 'market_value': '100'}]
    r = client.post('/api/trade/close', data=json.dumps({'symbol': 'NVDA'}), headers=H())
    assert r.status_code == 423
    assert not alpaca.posts()


@needs_db
def test_ledger_down_means_no_order(db, client, alpaca, monkeypatch):
    """Sin decisión no hay orden: si el libro no puede escribir order.submit, Alpaca NUNCA recibe la orden y la fila
    no queda como enviada. Base configurada pero caída (D4) → 503 sin enviar nada."""
    from core import decisions
    orig = decisions.record

    def broken(session, ctx, **kw):
        if ctx.kind == 'order.submit':
            raise decisions.LedgerUnavailable('libro caído (prueba)')
        return orig(session, ctx, **kw)
    monkeypatch.setattr(decisions, 'record', broken)
    n = len(alpaca.posts())
    r = _order(client, symbol='NVDA', side='buy', notional=13, client_order_id='kh-ledger-down-1')
    assert r.status_code == 503 and r.get_json()['code'] == 'ledger_unavailable' and r.get_json()['error_en']
    assert len(alpaca.posts()) == n
    from ontology.db import session_scope
    from brokerage.models import BrokerOrder
    with session_scope() as s:
        assert s.query(BrokerOrder).filter(BrokerOrder.client_order_id == 'kh-ledger-down-1').count() == 0
    monkeypatch.setattr(decisions, 'record', orig)
    import ontology.db as odb
    from sqlalchemy.exc import OperationalError

    class Down:
        def __enter__(self):
            raise OperationalError('SELECT 1', {}, Exception('connection refused'))

        def __exit__(self, *a):
            return False
    monkeypatch.setattr(odb, 'session_scope', lambda: Down())
    r = _order(client, symbol='NVDA', side='buy', notional=14)
    assert r.status_code == 503 and r.get_json()['code'] == 'ledger_unavailable'
    assert len(alpaca.posts()) == n


# ════════════════════════════════════════════════════════════════════════════
# 4. AccountRisk (paso 17): pesos y exposición Σw·Ψ con el kernel
# ════════════════════════════════════════════════════════════════════════════
def test_account_risk_view_uses_the_kernel():
    from core.hotviews import hot
    from core.hotviews.views import account
    g = hot.fallback()
    assert g is not None and g.impact is not None
    pos = [{'symbol': 'NVDA', 'market_value': '5000'}, {'symbol': 'TSM', 'market_value': '2000'},
           {'symbol': 'BTCUSD', 'market_value': '1000'}]
    a = account.compute(pos, 10000, order={'symbol': 'NVDA', 'side': 'buy', 'est_usd': 1000}, graph=g)
    assert a['available'] and a['generation'] == g.generation and a['content_sha']
    assert a['weights']['NVDA'] == pytest.approx(0.6) and 'BTCUSD' in a['unmapped']
    nvda = g.by_id[a['order']['company_id']]
    assert a['order']['sector'] == nvda['sector']
    assert a['order']['sector_weight_after'] >= 0.6 and 0 < a['chain_max'] <= 0.9
    top = a['chain_top'][0]
    # Σ_i w_i · Ψ[c→i] / 100 recalculado a mano para el peor proveedor
    ids, pct, _h = g.impact.victims[top['source']]
    tm = {n.get('mkt'): n['id'] for n in g.nodes if n.get('mkt')}
    want = sum(w * dict(zip(ids, pct)).get(tm.get(s), 0.0) / 100.0 for s, w in
               (('NVDA', 0.6), ('TSM', 0.2)) if tm.get(s) != top['source'])
    assert top['exposure'] == pytest.approx(want, abs=1e-6)
    extra = account.order_extra(a, {'max_sector_weight': 0.4})
    assert extra['sector_weight_after'] == a['order']['sector_weight_after'] and extra['max_sector_weight'] == 0.4
    assert account.compute(pos, 0, graph=g)['available'] is False
