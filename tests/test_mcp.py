"""tests/test_mcp.py — servidor MCP (mcp_server/): protocolo, auth, alcances,
herramientas, flujo de trading con aprobación humana, auditoría y OAuth.

Sin red: las fuentes en vivo (Yahoo, GDELT, Alpaca…) se sustituyen con
monkeypatch; el corretaje, con un módulo FALSO brokerage.service. Los tests con
base requieren Postgres (base PROPIA para no pisar a otros):

    DATABASE_URL=postgresql://postgres:devpass@localhost:5432/khipus_mcp \
        python3 -m pytest tests/test_mcp.py -q
"""
import base64
import hashlib
import json
import os
import re
import sys
import types
from datetime import datetime, timezone
from urllib.parse import parse_qs, unquote, urlparse

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')

PIN = '4321'
STATIC = 'static-read-token-0123456789abcdef'


# ════════════════════════════════════════════════════════════════════════════
# fixtures
# ════════════════════════════════════════════════════════════════════════════
@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv('TRADE_PIN', PIN)
    for k in ('MCP_ENABLED', 'MCP_ALLOWED_ORIGINS', 'MCP_PUBLIC_URL', 'MCP_RATE_PER_MIN', 'MCP_TRADING_ENABLED',
              'MCP_OAUTH_ENABLED', 'MCP_STATIC_TOKEN', 'MCP_ALLOWED_HOSTS', 'MCP_PIN_MAX_FAILS', 'MCP_PIN_LOCK_MIN',
              'MCP_TRUSTED_PROXY_HOPS', 'MCP_MAX_INFLIGHT', 'MCP_MAX_INFLIGHT_TOTAL', 'RAILWAY_PUBLIC_DOMAIN',
              'RESEARCH_DAILY_BUDGET_USD', 'BROKERAGE_AUTO_APPROVE_PAPER'):
        monkeypatch.delenv(k, raising=False)
    from core import http as _h
    from mcp_server import api as _api
    from mcp_server import auth as _a

    def _reset():
        _h._rate_buckets.clear()
        _a.reset_pin_guard()
        _a._INFLIGHT['total'] = 0
        _a._INFLIGHT['by'].clear()
        _api._SESSIONS.clear()
        _api._CLOSED.clear()
    _reset()
    yield
    _reset()


@pytest.fixture
def app():
    from flask import Flask
    from mcp_server.api import mcp_bp
    a = Flask('mcp-test')
    a.config['TESTING'] = True
    a.register_blueprint(mcp_bp)
    return a


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def nodb(monkeypatch):
    """Simula un servidor SIN DATABASE_URL + token estático de lectura."""
    import ontology.db as odb
    monkeypatch.setattr(odb, 'DATABASE_URL', '')
    monkeypatch.setenv('MCP_STATIC_TOKEN', STATIC)
    return STATIC


@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    import mcp_server.models  # noqa: F401
    import research.models  # noqa: F401
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    yield
    Base.metadata.drop_all(engine)


def rpc(client, token, method, params=None, id_=1, headers=None):
    msg = {'jsonrpc': '2.0', 'method': method}
    if id_ is not None:
        msg['id'] = id_
    if params is not None:
        msg['params'] = params
    h = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'}
    if token:
        h['Authorization'] = f'Bearer {token}'
    h.update(headers or {})
    return client.post('/mcp', data=json.dumps(msg), headers=h)


def call_tool(client, token, name, args=None, id_=7):
    r = rpc(client, token, 'tools/call', {'name': name, 'arguments': args or {}}, id_=id_)
    return r, r.get_json()


def pin_h():
    return {'X-Trade-Pin': PIN, 'Content-Type': 'application/json'}


def make_token(client, scopes=('read',), client_id=None, name='test agent'):
    r = client.post('/api/mcp/tokens', headers=pin_h(),
                    data=json.dumps({'name': name, 'scopes': list(scopes), 'client_id': client_id}))
    assert r.status_code == 201, r.get_json()
    return r.get_json()


# ════════════════════════════════════════════════════════════════════════════
# unidades sin Flask
# ════════════════════════════════════════════════════════════════════════════
def test_version_negotiation_unit():
    from mcp_server.protocol import LATEST_VERSION, negotiate
    assert negotiate('2025-06-18') == '2025-06-18'
    assert negotiate('2025-03-26') == '2025-03-26'
    assert negotiate('2099-01-01') == LATEST_VERSION
    assert negotiate(None) == LATEST_VERSION


def test_schema_validation_unit():
    from mcp_server.tools import InvalidParams, REGISTRY, validate
    sch = REGISTRY['get_supply_chain'].input_schema
    out = validate(sch, {'id': 'NVDA', 'depth': '2', 'direction': 'UP'})
    assert out == {'id': 'NVDA', 'depth': 2, 'direction': 'up'}
    with pytest.raises(InvalidParams):
        validate(sch, {'id': 'NVDA', 'depth': 3})
    with pytest.raises(InvalidParams):
        validate(sch, {'depth': 1})
    with pytest.raises(InvalidParams):
        validate(sch, {'id': 'x', 'bogus': 1})
    with pytest.raises(InvalidParams):
        validate(REGISTRY['get_risk_report'].input_schema, {'positions': [{'symbol': 'NVDA', 'shares': -1}]})


def test_every_tool_has_schema_and_annotations():
    from mcp_server.tools import REGISTRY
    assert len(REGISTRY) >= 20
    for t in REGISTRY.values():
        d = t.describe()
        assert d['inputSchema']['type'] == 'object'
        assert set(d['annotations']) >= {'readOnlyHint', 'destructiveHint', 'openWorldHint'}
        assert t.scope in ('read', 'research', 'trade')
        assert len(d['description']) > 40
    assert REGISTRY['submit_order'].annotations['destructiveHint'] is True
    assert REGISTRY['search_companies'].annotations['readOnlyHint'] is True


def test_summarize_args_redacts_secrets():
    from mcp_server.auth import summarize_args
    s = summarize_args({'query': 'x' * 500, 'api_key': 'SECRET', 'nested': {'Trade_PIN': '1'},
                        'tok': 'kmcp_abcdef', 'lst': list(range(30))})
    assert s['api_key'] == '***' and s['nested']['Trade_PIN'] == '***' and s['tok'] == '***'
    assert len(s['query']) == 200 and len(s['lst']) == 11


def test_redirect_uri_rules():
    from mcp_server.oauth import valid_redirect_uri
    assert valid_redirect_uri('https://claude.ai/api/mcp/auth_callback')
    assert valid_redirect_uri('http://localhost:6274/oauth/callback')
    assert valid_redirect_uri('http://127.0.0.1:3000/cb')
    assert valid_redirect_uri('cursor://anysphere.cursor-retrieval/oauth/callback')
    assert not valid_redirect_uri('http://evil.example.com/cb')
    assert not valid_redirect_uri('javascript:alert(1)')
    assert not valid_redirect_uri('https://x.com/cb#frag')


def test_sign_unsign_roundtrip():
    from mcp_server.oauth import sign, unsign
    tok = sign({'p': {'a': 1}, 'exp': 9999999999})
    assert unsign(tok)['p'] == {'a': 1}
    assert unsign(tok[:-2] + 'xx') is None
    assert unsign(sign({'exp': 1})) is None


# ════════════════════════════════════════════════════════════════════════════
# transporte / protocolo (sin base: token estático de lectura)
# ════════════════════════════════════════════════════════════════════════════
def test_initialize_and_session(client, nodb):
    r = rpc(client, nodb, 'initialize', {'protocolVersion': '2025-06-18', 'capabilities': {},
                                         'clientInfo': {'name': 'pytest', 'version': '1'}})
    assert r.status_code == 200
    assert r.headers['Content-Type'].startswith('application/json')
    body = r.get_json()
    res = body['result']
    assert body['id'] == 1 and body['jsonrpc'] == '2.0'
    assert res['protocolVersion'] == '2025-06-18'
    assert res['serverInfo']['name'] == 'khipus-finance'
    assert res['capabilities'] == {'tools': {'listChanged': False}}
    assert 'human' in res['instructions'].lower() or 'Trading tools are not enabled' in res['instructions']
    assert r.headers.get('Mcp-Session-Id')
    # versión antigua soportada → eco; desconocida → la más nueva
    r2 = rpc(client, nodb, 'initialize', {'protocolVersion': '2025-03-26'})
    assert r2.get_json()['result']['protocolVersion'] == '2025-03-26'
    r3 = rpc(client, nodb, 'initialize', {'protocolVersion': '1999-01-01'})
    assert r3.get_json()['result']['protocolVersion'] == '2025-06-18'


def test_initialized_notification_202(client, nodb):
    r = rpc(client, nodb, 'notifications/initialized', id_=None)
    assert r.status_code == 202
    assert r.data == b''


def test_ping_resources_prompts(client, nodb):
    assert rpc(client, nodb, 'ping').get_json()['result'] == {}
    assert rpc(client, nodb, 'resources/list').get_json()['result'] == {'resources': []}
    assert rpc(client, nodb, 'prompts/list').get_json()['result'] == {'prompts': []}


def test_tools_list_read_only_for_static(client, nodb):
    tools = rpc(client, nodb, 'tools/list').get_json()['result']['tools']
    names = {t['name'] for t in tools}
    assert {'search_companies', 'get_company', 'get_supply_chain', 'get_world_events'} <= names
    assert 'run_research' not in names and 'preview_order' not in names
    t = next(t for t in tools if t['name'] == 'search_companies')
    assert t['inputSchema']['required'] == ['query']
    assert t['annotations']['readOnlyHint'] is True


def test_jsonrpc_errors(client, nodb):
    h = {'Authorization': f'Bearer {nodb}', 'Content-Type': 'application/json'}
    r = client.post('/mcp', data='{not json', headers=h)
    assert r.status_code == 400 and r.get_json()['error']['code'] == -32700
    r = rpc(client, nodb, 'does/not/exist')
    assert r.get_json()['error']['code'] == -32601
    r = rpc(client, nodb, 'tools/call', {'arguments': {}})
    assert r.get_json()['error']['code'] == -32602
    r = rpc(client, nodb, 'tools/call', {'name': 'no_such_tool', 'arguments': {}})
    assert r.get_json()['error']['code'] == -32602 and 'Unknown tool' in r.get_json()['error']['message']
    r = rpc(client, nodb, 'tools/call', {'name': 'search_companies', 'arguments': {'limit': 5}})
    assert r.get_json()['error']['code'] == -32602
    r = client.post('/mcp', data=json.dumps({'jsonrpc': '1.0', 'id': 1, 'method': 'ping'}), headers=h)
    assert r.get_json()['error']['code'] == -32600
    r = client.post('/mcp', data='[]', headers=h)
    assert r.status_code == 400


def test_batch(client, nodb):
    h = {'Authorization': f'Bearer {nodb}', 'Content-Type': 'application/json'}
    batch = [{'jsonrpc': '2.0', 'id': 1, 'method': 'ping'},
             {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
             {'jsonrpc': '2.0', 'id': 'b', 'method': 'tools/list'}]
    r = client.post('/mcp', data=json.dumps(batch), headers=h)
    out = r.get_json()
    assert isinstance(out, list) and [x['id'] for x in out] == [1, 'b']


def test_get_is_405_and_bad_protocol_header(client, nodb):
    r = client.get('/mcp', headers={'Authorization': f'Bearer {nodb}'})
    assert r.status_code == 405 and 'POST' in r.headers['Allow']
    r = rpc(client, nodb, 'ping', headers={'MCP-Protocol-Version': '2020-01-01'})
    assert r.status_code == 400
    err = r.get_json()
    assert err['id'] == 1 and err['error']['code'] == -32022
    assert err['error']['data']['supported'] == ['2025-06-18', '2025-03-26']
    # sonda moderna (server/discover) → método desconocido → el cliente vuelve a initialize
    assert rpc(client, nodb, 'server/discover').get_json()['error']['code'] == -32601
    r = rpc(client, nodb, 'ping', headers={'MCP-Protocol-Version': '2025-03-26'})
    assert r.status_code == 200


def test_auth_failures_401_with_resource_metadata(client, nodb):
    r = rpc(client, None, 'initialize', {'protocolVersion': '2025-06-18'})
    assert r.status_code == 401
    www = r.headers['WWW-Authenticate']
    assert www.startswith('Bearer ') and 'resource_metadata="' in www
    assert '/.well-known/oauth-protected-resource' in www
    r = rpc(client, 'kmcp_totally-wrong', 'ping')
    assert r.status_code == 401 and 'invalid_token' in r.headers['WWW-Authenticate']
    r = rpc(client, 'short', 'ping')
    assert r.status_code == 401


def test_protected_resource_metadata(client, nodb):
    for path in ('/.well-known/oauth-protected-resource', '/.well-known/oauth-protected-resource/mcp'):
        d = client.get(path).get_json()
        assert d['resource'].endswith('/mcp')
        assert 'read' in d['scopes_supported'] and d['bearer_methods_supported'] == ['header']
        assert 'authorization_servers' not in d          # sin base no hay OAuth


def test_origin_validation(client, nodb, monkeypatch):
    r = rpc(client, nodb, 'ping', headers={'Origin': 'https://evil.example'})
    assert r.status_code == 403
    r = rpc(client, nodb, 'ping', headers={'Origin': 'http://localhost'})      # mismo host del test
    assert r.status_code == 200 and r.headers['Access-Control-Allow-Origin'] == 'http://localhost'
    monkeypatch.setenv('MCP_ALLOWED_ORIGINS', 'https://inspector.example, https://other.example')
    r = rpc(client, nodb, 'ping', headers={'Origin': 'https://inspector.example'})
    assert r.status_code == 200
    r = client.options('/mcp', headers={'Origin': 'https://inspector.example',
                                        'Access-Control-Request-Method': 'POST'})
    assert r.status_code == 204 and 'Mcp-Session-Id' in r.headers['Access-Control-Allow-Headers']
    r = client.options('/mcp', headers={'Origin': 'https://evil.example'})
    assert r.status_code == 403


def test_kill_switch_and_size_limit(client, nodb, monkeypatch):
    monkeypatch.setenv('MCP_ENABLED', 'off')
    assert rpc(client, nodb, 'ping').status_code == 503
    monkeypatch.delenv('MCP_ENABLED')
    big = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'ping', 'params': {'x': 'a' * 300_000}})
    r = client.post('/mcp', data=big, headers={'Authorization': f'Bearer {nodb}', 'Content-Type': 'application/json'})
    assert r.status_code == 413


def test_search_and_supply_chain_real_snapshot(client, nodb):
    r, d = call_tool(client, nodb, 'search_companies', {'query': 'NVDA', 'limit': 5})
    res = d['result']
    assert res['isError'] is False
    sc = res['structuredContent']
    assert sc['results'][0]['id'] == 'Nvidia' and sc['results'][0]['symbol'] == 'NVDA'
    assert sc['source'] and sc['as_of']
    assert json.loads(res['content'][0]['text']) == sc          # texto = JSON serializado
    _, d = call_tool(client, nodb, 'search_companies', {'query': 'taiwan semi'})
    assert any(x['id'] == 'TSMC' for x in d['result']['structuredContent']['results'])
    _, d = call_tool(client, nodb, 'get_supply_chain', {'id': 'TSMC', 'direction': 'down', 'depth': 1, 'limit': 5})
    sc = d['result']['structuredContent']
    assert sc['root'] == 'TSMC' and sc['edges'] and all(e['source'] == 'TSMC' for e in sc['edges'])
    assert len(sc['edges']) <= 5 and sc['convention'] == 'edge source SUPPLIES target'
    _, d = call_tool(client, nodb, 'get_supply_chain', {'id': 'Nvidia', 'direction': 'up', 'depth': 2, 'limit': 3})
    sc = d['result']['structuredContent']
    assert max(n['hop'] for n in sc['nodes']) == 2


def test_get_company_live_and_private(client, nodb, monkeypatch):
    from mcp_server import tools
    calls = []

    def fake_profile(sym):
        calls.append(sym)
        return {'available': True, 'symbol': sym, 'price': 123.45, 'currency': 'USD', 'market_cap_usd_b': 3000.0,
                'source': 'yahoo', 'as_of': '2026-09-30T12:00:00+00:00'}
    monkeypatch.setattr(tools, '_live_profile', fake_profile)
    _, d = call_tool(client, nodb, 'get_company', {'id_or_ticker': 'NVDA'})
    sc = d['result']['structuredContent']
    assert sc['id'] == 'Nvidia' and calls == ['NVDA']
    assert sc['live_market']['price'] == 123.45 and sc['live_market']['source'] == 'yahoo'
    assert sc['network_risk_score']['value'] is not None
    assert 'catalog formula' in sc['network_risk_score']['method']       # sin base → fórmula de la app
    assert sc['top_suppliers'] and sc['top_customers']
    # privada: valuación verificada con fuente, nunca un "precio"
    _, d = call_tool(client, nodb, 'get_company', {'id_or_ticker': 'OpenAI'})
    sc = d['result']['structuredContent']
    assert sc['live_market']['available'] is False
    pv = sc.get('private_valuation')
    assert pv and pv['source_url'].startswith('http') and 'NOT a live price' in pv['kind']
    assert calls == ['NVDA']
    # no encontrada → isError con sugerencias
    _, d = call_tool(client, nodb, 'get_company', {'id_or_ticker': 'zzzz-no-existe-zzzz'})
    assert d['result']['isError'] is True
    assert d['result']['structuredContent']['code'] == 'not_found'


def test_scope_enforcement_trade_and_research(client, nodb):
    _, d = call_tool(client, nodb, 'preview_order', {'symbol': 'NVDA', 'side': 'buy', 'notional': 10,
                                                     'rationale': 'test rationale here'})
    assert d['result']['isError'] is True and d['result']['structuredContent']['code'] == 'insufficient_scope'
    _, d = call_tool(client, nodb, 'run_research', {'entity': 'NVDA'})
    assert d['result']['structuredContent']['code'] == 'insufficient_scope'


def test_db_tools_without_db_are_clear_errors(client, nodb):
    for name, args in (('get_research', {'entity': 'NVDA'}), ('get_ontology_object', {'id': 'Nvidia'}),
                       ('get_claim_evidence', {'claim_id': 'x'}), ('get_track_record', {})):
        _, d = call_tool(client, nodb, name, args)
        assert d['result']['isError'] is True, name
        assert d['result']['structuredContent']['code'] == 'unavailable', name


def test_world_risk_options_with_fakes(client, nodb, monkeypatch):
    import core.options
    import core.risk_report
    import core.world
    seen = {}

    def fake_world(layers=None, window='24h'):
        seen['world'] = (layers, window)
        return {'items': [{'id': 'a', 'layer': 'quakes', 'lat': 1, 'lon': 2, 'title': 'M6 quake', 'severity': 3,
                           'time': '2026-09-30T01:00:00Z', 'source': 'USGS', 'url': 'https://usgs.gov/x'},
                          {'id': 'b', 'layer': 'conflict', 'lat': 3, 'lon': 4, 'title': 'clash', 'severity': 5,
                           'time': '2026-09-30T02:00:00Z', 'source': 'GDELT', 'url': 'https://g/x'}],
                'sources': {'quakes': {'ok': True, 'count': 1, 'as_of': 'now'}}, 'window': window,
                'as_of': '2026-09-30T03:00:00Z'}
    monkeypatch.setattr(core.world, 'world_events', fake_world)
    _, d = call_tool(client, nodb, 'get_world_events', {'layers': ['quakes', 'conflict'], 'window': '7d', 'limit': 5})
    sc = d['result']['structuredContent']
    assert seen['world'] == (['quakes', 'conflict'], '7d')
    assert [x['id'] for x in sc['items']] == ['b', 'a'] and sc['sources']['quakes']['ok']
    _, d = call_tool(client, nodb, 'get_world_events', {'layers': ['martians']})
    assert d['error']['code'] == -32602

    monkeypatch.setattr(core.risk_report, 'build_report',
                        lambda positions, horizon=10: {'ok': True, 'var95': {'hist_1d_usd': 10}, 'histogram': [1],
                                                       'source': 'Yahoo', 'as_of': '2026-09-29', 'positions': positions})
    _, d = call_tool(client, nodb, 'get_risk_report', {'positions': [{'symbol': 'NVDA', 'shares': 3}]})
    sc = d['result']['structuredContent']
    assert sc['var95']['hist_1d_usd'] == 10 and 'histogram' not in sc
    monkeypatch.setattr(core.risk_report, 'build_report',
                        lambda positions, horizon=10: {'ok': False, 'error': 'no hay posiciones'})
    _, d = call_tool(client, nodb, 'get_risk_report', {'positions': [{'symbol': 'NVDA', 'shares': 3}]})
    assert d['result']['isError'] is True

    monkeypatch.setattr(core.options, 'vega_report',
                        lambda options: {'ok': True, 'positions': [], 'totals': {'vega_usd': 1.5},
                                         'generated_at': '2026-09-30T00:00:00Z'})
    _, d = call_tool(client, nodb, 'get_option_greeks', {'options': [
        {'symbol': 'NVDA', 'kind': 'call', 'strike': 100, 'expiry': '2026-12-18', 'contracts': 1}]})
    assert d['result']['structuredContent']['totals']['vega_usd'] == 1.5


def test_tool_crash_is_iserror_not_500(client, nodb, monkeypatch):
    import core.world
    monkeypatch.setattr(core.world, 'world_events', lambda layers=None, window='24h': 1 / 0)
    r, d = call_tool(client, nodb, 'get_world_events', {})
    assert r.status_code == 200 and d['result']['isError'] is True
    assert d['result']['structuredContent']['code'] == 'internal'


def test_status_and_catalog_endpoints(client, nodb):
    d = client.get('/api/mcp/status').get_json()
    assert d['protocol_versions'] == ['2025-06-18', '2025-03-26'] and d['endpoint'].endswith('/mcp')
    assert 'preview_order' in d['tools_by_scope']['trade'] and d['db'] is False
    cat = client.get('/api/mcp/tools').get_json()['tools']
    assert any(t['name'] == 'submit_order' and t['scope'] == 'trade' for t in cat)


def test_token_api_without_db_or_pin(client, nodb, monkeypatch):
    assert client.get('/api/mcp/tokens').status_code == 401
    assert client.get('/api/mcp/tokens', headers={'X-Trade-Pin': PIN}).status_code == 503
    monkeypatch.delenv('TRADE_PIN')
    assert client.get('/api/mcp/tokens', headers={'X-Trade-Pin': PIN}).status_code == 403


# ════════════════════════════════════════════════════════════════════════════
# con base de datos: tokens, alcances, auditoría, investigación
# ════════════════════════════════════════════════════════════════════════════
@needs_db
def test_token_lifecycle_and_revocation(client, db):
    t = make_token(client, ['read'])
    tok = t['token']
    assert tok.startswith('kmcp_') and t['scopes'] == ['read'] and t['prefix'].endswith('…')
    lst = client.get('/api/mcp/tokens', headers=pin_h()).get_json()['tokens']
    row = next(x for x in lst if x['id'] == t['id'])
    assert 'token' not in row and not any(tok in json.dumps(x) for x in lst)
    r = rpc(client, tok, 'initialize', {'protocolVersion': '2025-06-18'})
    assert r.status_code == 200
    row = next(x for x in client.get('/api/mcp/tokens', headers=pin_h()).get_json()['tokens'] if x['id'] == t['id'])
    assert row['use_count'] >= 1 and row['last_used_at']
    assert client.post(f'/api/mcp/tokens/{t["id"]}/revoke', headers=pin_h(), data='{}').status_code == 200
    r = rpc(client, tok, 'ping')
    assert r.status_code == 401 and 'invalid_token' in r.headers['WWW-Authenticate']
    assert client.post('/api/mcp/tokens/nope/revoke', headers=pin_h(), data='{}').status_code == 404


@needs_db
def test_token_validation(client, db):
    r = client.post('/api/mcp/tokens', headers=pin_h(), data=json.dumps({'name': 'x', 'scopes': ['admin']}))
    assert r.status_code == 400
    r = client.post('/api/mcp/tokens', headers=pin_h(), data=json.dumps({'name': '', 'scopes': ['read']}))
    assert r.status_code == 400
    r = client.post('/api/mcp/tokens', headers=pin_h(), data=json.dumps({'name': 'x', 'scopes': ['trade']}))
    assert r.status_code == 400 and 'client_id' in r.get_json()['error']
    r = client.post('/api/mcp/tokens', headers={'X-Trade-Pin': 'wrong'}, data='{}')
    assert r.status_code == 401


@needs_db
def test_scopes_filter_tools_list(client, db):
    read_tok = make_token(client, ['read'])['token']
    res_tok = make_token(client, ['read', 'research'])['token']
    names_r = {t['name'] for t in rpc(client, read_tok, 'tools/list').get_json()['result']['tools']}
    names_s = {t['name'] for t in rpc(client, res_tok, 'tools/list').get_json()['result']['tools']}
    assert 'run_research' not in names_r and 'run_research' in names_s and 'run_committee' in names_s
    assert not ({'preview_order', 'submit_order', 'get_account'} & (names_r | names_s))


@needs_db
def test_audit_rows_no_secrets(client, db):
    tok = make_token(client, ['read'], name='audit-probe')['token']
    assert rpc(client, 'kmcp_not-a-real-token-xyz', 'ping').status_code == 401
    call_tool(client, tok, 'search_companies', {'query': 'AMD'})
    call_tool(client, tok, 'search_companies', {'query': 'AMD', 'api_key': 'sk-SECRET-VALUE'})   # → -32602
    rows = client.get('/api/mcp/audit?limit=50', headers=pin_h()).get_json()['audit']
    mine = [x for x in rows if x['token_name'] == 'audit-probe']
    ok = next(x for x in mine if x['tool'] == 'search_companies' and x['status'] == 'ok')
    assert ok['args'] == {'query': 'AMD'} and ok['latency_ms'] is not None
    bad = next(x for x in mine if x['status'] == 'invalid')
    assert bad['args']['api_key'] == '***'
    assert 'sk-SECRET-VALUE' not in json.dumps(rows) and tok not in json.dumps(rows)
    assert any(x['method'] == 'auth' and x['status'] == 'unauthorized' and x['token_id'] is None for x in rows)
    assert 'kmcp_not-a-real-token-xyz' not in json.dumps(rows)


@needs_db
def test_rate_limit_per_token(client, db, monkeypatch):
    monkeypatch.setenv('MCP_RATE_PER_MIN', '3')
    tok = make_token(client, ['read'])['token']
    codes = [rpc(client, tok, 'ping').status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]


@needs_db
def test_ontology_object_and_research_tools(client, db):
    from ontology.db import session_scope
    from ontology.models import Event, ObjectRecord
    from research.models import ResearchClaim, ResearchEvidence, ResearchJob
    now = datetime.now(timezone.utc)
    with session_scope() as s:
        s.add(ObjectRecord(id='Nvidia', type='Company', label='Nvidia', properties={'country': 'EEUU', 'margin': 0.55}))
        s.flush()
        s.add(Event(event_type='ObjectCreated', object_id='Nvidia', payload={'label': 'Nvidia'}, valid_from=now,
                    source='manual', actor='pytest'))
        base = dict(agent_id='a1', agent_version='1', subject_entity_id='Nvidia', predicate='P', claim_type='risk',
                    depth='QUICK', valid_from=now, confidence=0.62, horizon='MEDIUM_TERM', status='active')
        s.add(ResearchClaim(id='c-ok', agent_type='fundamental', topic='margins', stance='positive',
                            statement_es='Márgenes altos', statement_en='High margins', **base))
        s.add(ResearchClaim(id='c-bad', agent_type='news', topic='demand', stance='positive',
                            statement_es='Ingresos de $999B', statement_en='Revenue of $999B', **base))
        s.add(ResearchEvidence(claim_id='c-ok', stance='supporting', source_type='financials',
                               source_reference='yahoo:fundamentals:NVDA', title='Margins', excerpt='gross margin 75%'))
        s.add(ResearchEvidence(claim_id='c-bad', stance='supporting', source_type='news',
                               source_reference='https://example.com', title='t', excerpt='no figures'))
        s.add(ResearchJob(id='job-1', entity_id='Nvidia', depth='QUICK', agents=['fundamental'], status='done',
                          trigger={'kind': 'user'}, dedupe_key='k'))
    tok = make_token(client, ['read'])['token']
    _, d = call_tool(client, tok, 'get_ontology_object', {'id': 'NVDA'})
    sc = d['result']['structuredContent']
    assert sc['object']['id'] == 'Nvidia' and sc['recent_events'][0]['event_type'] == 'ObjectCreated'
    _, d = call_tool(client, tok, 'get_research', {'entity': 'NVDA'})
    sc = d['result']['structuredContent']
    ids = [c['claim_id'] for lst in sc['claims_by_agent'].values() for c in lst]
    assert ids == ['c-ok'] and sc['withheld_unsupported_figures'] == 1
    assert sc['last_job']['job_id'] == 'job-1'
    _, d = call_tool(client, tok, 'get_claim_evidence', {'claim_id': 'c-ok'})
    sc = d['result']['structuredContent']
    assert sc['supporting'][0]['source_reference'] == 'yahoo:fundamentals:NVDA' and sc['n_supporting'] == 1
    _, d = call_tool(client, tok, 'get_research_job', {'job_id': 'job-1'})
    assert d['result']['structuredContent']['status'] == 'done'
    # con base, el NRS de get_company sale del servidor (objeto en la ontología)
    _, d = call_tool(client, tok, 'get_company', {'id_or_ticker': 'Nvidia', 'include_live': False})
    assert d['result']['structuredContent']['network_risk_score']['method'].startswith('server')


@needs_db
def test_run_research_budget_and_job(client, db, monkeypatch):
    import core.ai
    import research.runner as runner
    monkeypatch.setattr(core.ai, '_ai_configured', lambda: True)
    started = []
    monkeypatch.setattr(runner, 'execute_job_async', lambda jid: started.append(jid))
    tok = make_token(client, ['read', 'research'])['token']
    _, d = call_tool(client, tok, 'run_research', {'entity': 'AMD', 'depth': 'quick'})
    sc = d['result']['structuredContent']
    assert d['result']['isError'] is False and sc['entity_id'] == 'AMD' and sc['depth'] == 'QUICK'
    assert started == [sc['job_id']] and sc['reused'] is False
    _, d = call_tool(client, tok, 'run_research', {'entity': 'AMD', 'depth': 'QUICK'})
    assert d['result']['structuredContent']['reused'] is True and len(started) == 1
    monkeypatch.setattr(runner, 'spent_today', lambda s: 99.0)
    _, d = call_tool(client, tok, 'run_research', {'entity': 'Intel'})
    assert d['result']['isError'] and d['result']['structuredContent']['code'] == 'budget_exhausted'
    _, d = call_tool(client, tok, 'run_research', {'entity': 'X', 'depth': 'DEEP'})
    assert d['error']['code'] == -32602


# ════════════════════════════════════════════════════════════════════════════
# trading con un brokerage.service FALSO (contrato compartido)
# ════════════════════════════════════════════════════════════════════════════
def _fake_brokerage(auto_approve=False):
    m = types.ModuleType('brokerage.service')
    m.orders = {}
    m.calls = []
    clients = {'c1': {'id': 'c1', 'name': 'Diego', 'mode': 'paper', 'paper': True, 'email': 'd@x.com',
                      'notes': 'private', 'risk_profile': 'moderado', 'limits': {}, 'status': 'active'},
               'c2': {'id': 'c2', 'name': 'Other', 'mode': 'paper', 'paper': True}}
    m.available = lambda: True
    m.get_client = lambda s, cid: clients.get(cid) or next((c for c in clients.values() if c['name'] == cid), None)
    m.list_clients = lambda s: list(clients.values())

    def account_snapshot(s, cid):
        return {'ok': True, 'client': clients[cid],
                'account': {'equity': 1000.0, 'cash': 500.0, 'buying_power': 500.0, 'currency': 'USD', 'paper': True},
                'positions': [{'symbol': 'NVDA', 'qty': 2, 'avg_entry_price': 100, 'market_value': 250,
                               'unrealized_pl': 50, 'unrealized_plpc': 0.25}]}
    m.account_snapshot = account_snapshot

    def preview_order(s, cid, symbol, side, notional=None, qty=None, order_type='market', limit_price=None,
                      source='ui', requested_by='', proposal_id=None, rationale=None):
        m.calls.append(('preview', cid, source, requested_by, rationale))
        pid = f'p{len(m.orders) + 1}'
        req = source in ('mcp', 'committee') and not auto_approve
        o = {'ok': True, 'preview_id': pid, 'id': pid, 'client_id': cid, 'symbol': symbol, 'side': side,
             'notional': notional, 'qty': qty, 'summary_es': 'Comprar', 'summary_en': 'Buy', 'checks': [],
             'blocked': False, 'requires_human_approval': req, 'paper': True, 'mode': 'paper',
             'source': source, 'requested_by': requested_by or source,
             'status': 'pending_approval' if req else 'previewed', 'expires_at': None, 'client_order_id': pid}
        m.orders[pid] = dict(o)
        return o
    m.preview_order = preview_order

    def confirm_order(s, preview_id, approved_by, source='ui'):
        m.calls.append(('confirm', preview_id, source))
        o = m.orders[preview_id]
        if o['requires_human_approval'] and source != 'ui':
            return {'ok': False, 'error': 'requires human approval', 'status': 'pending_approval',
                    'code': 'requires_human_approval', 'order': dict(o)}
        o['status'] = 'submitted'
        o['alpaca_order_id'] = 'alp-1'
        return {'ok': True, 'status': 'submitted', 'order': dict(o)}
    m.confirm_order = confirm_order
    m.get_order = lambda s, oid: dict(m.orders[oid]) if oid in m.orders else None
    m.list_orders = lambda s, client_id=None, status=None, limit=50: [
        dict(o) for o in m.orders.values() if (client_id is None or o['client_id'] == client_id)]

    def cancel_order(s, oid, actor):
        m.orders[oid]['status'] = 'canceled'
        return {'ok': True, 'status': 'canceled', 'order': dict(m.orders[oid])}
    m.cancel_order = cancel_order
    m.clients = clients
    return m


@needs_db
def test_trade_flow_requires_human_approval(client, db, monkeypatch):
    fake = _fake_brokerage()
    monkeypatch.setitem(sys.modules, 'brokerage.service', fake)
    t = make_token(client, ['read', 'trade'], client_id='Diego')          # por nombre → id canónico
    assert t['client_id'] == 'c1' and t['client_name'] == 'Diego'
    tok = t['token']
    init = rpc(client, tok, 'initialize', {'protocolVersion': '2025-06-18'}).get_json()['result']
    assert 'HUMAN APPROVAL' in init['instructions'] and 'c1' in init['instructions']
    names = {x['name'] for x in rpc(client, tok, 'tools/list').get_json()['result']['tools']}
    assert {'get_account', 'preview_order', 'submit_order', 'cancel_order', 'get_order_status'} <= names

    _, d = call_tool(client, tok, 'get_account')
    sc = d['result']['structuredContent']
    assert sc['account']['equity'] == 1000.0 and sc['mode_badge'].startswith('PAPER')
    assert 'email' not in sc['client'] and 'notes' not in sc['client']

    _, d = call_tool(client, tok, 'preview_order', {'symbol': 'NVDA', 'side': 'BUY', 'notional': 50,
                                                    'rationale': 'Supply-chain research is positive'})
    sc = d['result']['structuredContent']
    assert d['result']['isError'] is False and sc['status'] == 'pending_approval'
    assert '👥 Clientes → Aprobaciones' in sc['next']
    assert fake.calls[0][:3] == ('preview', 'c1', 'mcp') and fake.calls[0][3].startswith('mcp:')
    pid = sc['preview_id']

    _, d = call_tool(client, tok, 'submit_order', {'preview_id': pid})
    sc = d['result']['structuredContent']
    assert d['result']['isError'] is False
    assert sc['status'] == 'pending_human_approval'
    assert 'queued for human approval in Khipus (👥 Clientes → Aprobaciones)' in sc['message']
    assert fake.orders[pid]['status'] == 'pending_approval'          # NO se ejecutó
    assert ('confirm', pid, 'mcp') in fake.calls

    _, d = call_tool(client, tok, 'get_order_status', {'order_id': pid})
    assert d['result']['structuredContent']['order']['status'] == 'pending_approval'
    _, d = call_tool(client, tok, 'list_orders')
    assert d['result']['structuredContent']['count'] == 1

    # órdenes de OTRO cliente: invisibles e intocables
    other = fake.preview_order(None, 'c2', 'AMD', 'buy', notional=10, source='ui')
    for name in ('get_order_status', 'cancel_order', 'submit_order'):
        key = 'preview_id' if name == 'submit_order' else 'order_id'
        _, d = call_tool(client, tok, name, {key: other['preview_id']})
        assert d['result']['isError'] and d['result']['structuredContent']['code'] == 'not_found', name
    assert fake.orders[other['preview_id']]['status'] == 'previewed'

    _, d = call_tool(client, tok, 'cancel_order', {'order_id': pid})
    assert d['result']['structuredContent']['status'] == 'canceled'

    # validación: notional XOR qty, límite exige limit_price, rationale obligatorio
    _, d = call_tool(client, tok, 'preview_order', {'symbol': 'NVDA', 'side': 'buy', 'notional': 5, 'qty': 1,
                                                    'rationale': 'both amounts given'})
    assert d['error']['code'] == -32602
    _, d = call_tool(client, tok, 'preview_order', {'symbol': 'NVDA', 'side': 'buy', 'qty': 1,
                                                    'order_type': 'limit', 'rationale': 'limit without price'})
    assert d['error']['code'] == -32602
    _, d = call_tool(client, tok, 'preview_order', {'symbol': 'NVDA', 'side': 'buy', 'qty': 1})
    assert d['error']['code'] == -32602


@needs_db
def test_trade_auto_approve_paper_and_kill_switch(client, db, monkeypatch):
    fake = _fake_brokerage(auto_approve=True)
    monkeypatch.setitem(sys.modules, 'brokerage.service', fake)
    tok = make_token(client, ['trade'], client_id='c1')['token']
    _, d = call_tool(client, tok, 'preview_order', {'symbol': 'NVDA', 'side': 'buy', 'notional': 25,
                                                    'rationale': 'auto approve paper path'})
    pid = d['result']['structuredContent']['preview_id']
    _, d = call_tool(client, tok, 'submit_order', {'preview_id': pid})
    sc = d['result']['structuredContent']
    assert sc['status'] == 'submitted' and sc['order']['alpaca_order_id'] == 'alp-1'
    monkeypatch.setenv('MCP_TRADING_ENABLED', 'off')
    names = {x['name'] for x in rpc(client, tok, 'tools/list').get_json()['result']['tools']}
    assert 'preview_order' not in names
    _, d = call_tool(client, tok, 'get_account')
    assert d['result']['structuredContent']['code'] == 'trading_disabled'


@needs_db
def test_trade_without_brokerage_module(client, db, monkeypatch):
    fake = _fake_brokerage()
    monkeypatch.setitem(sys.modules, 'brokerage.service', fake)
    tok = make_token(client, ['trade'], client_id='c1')['token']
    monkeypatch.setitem(sys.modules, 'brokerage.service', None)      # import → ImportError
    _, d = call_tool(client, tok, 'get_account')
    assert d['result']['isError'] and d['result']['structuredContent']['code'] == 'unavailable'


@needs_db
def test_committee_memo_redaction(client, db, monkeypatch):
    fake = types.ModuleType('research.committee')
    memo = {'memo_id': 'm1', 'entity_id': 'Nvidia', 'client_id': 'c1', 'decision': 'BUY',
            'sizing': {'notional': 1234.0}, 'audit': list(range(30)), 'inputs': {'package': 'BIG', 'label': 'Nvidia'}}
    seen = []

    def get_memo(s, mid, redact_client=False):
        seen.append(redact_client)
        d = dict(memo)
        if redact_client:
            d['sizing'] = {'notional': None}
        return d
    fake.get_memo = get_memo
    fake.latest_memo = lambda s, eid, redact_client=False: get_memo(s, 'm1', redact_client)
    monkeypatch.setitem(sys.modules, 'research.committee', fake)
    tok = make_token(client, ['read'])['token']
    _, d = call_tool(client, tok, 'get_committee_memo', {'entity': 'NVDA'})
    sc = d['result']['structuredContent']
    assert sc['sizing']['notional'] is None and seen[-1] is True
    assert len(sc['audit']) == 10 and 'package' not in sc['inputs']
    _, d = call_tool(client, tok, 'get_committee_memo', {})
    assert d['error']['code'] == -32602
    monkeypatch.setitem(sys.modules, 'brokerage.service', _fake_brokerage())
    ttok = make_token(client, ['trade'], client_id='c1')['token']
    _, d = call_tool(client, ttok, 'get_committee_memo', {'memo_id': 'm1'})
    assert d['result']['structuredContent']['sizing']['notional'] == 1234.0


# ════════════════════════════════════════════════════════════════════════════
# OAuth 2.1 + PKCE S256
# ════════════════════════════════════════════════════════════════════════════
def _pkce():
    verifier = base64.urlsafe_b64encode(os.urandom(40)).decode().rstrip('=')
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    return verifier, challenge


def _hidden(html_text, name):
    m = re.search(r'name="%s" value="([^"]*)"' % re.escape(name), html_text)
    return m.group(1) if m else None


def _authorize(client, cid, redirect, challenge, state='st-123', scope='read research', pin=PIN, extra=None):
    q = {'response_type': 'code', 'client_id': cid, 'redirect_uri': redirect, 'code_challenge': challenge,
         'code_challenge_method': 'S256', 'state': state, 'scope': scope, 'resource': 'http://localhost/mcp'}
    r = client.get('/oauth/authorize', query_string=q)
    assert r.status_code == 200 and 'name="pin"' in r.get_data(as_text=True)
    form = dict(q, step='pin', pin=pin)
    r = client.post('/oauth/authorize', data=form)
    page = r.get_data(as_text=True)
    consent = _hidden(page, 'consent')
    if consent is None:
        return None, page
    data = {'step': 'consent', 'consent': consent.replace('&amp;', '&'), 'decision': 'approve',
            'scope_research': '1', 'token_name': 'Claude'}
    data.update(extra or {})
    r = client.post('/oauth/authorize', data=data)
    page = r.get_data(as_text=True)
    m = re.search(r'url=([^"]+)"', page)
    if not m:
        return None, page
    target = m.group(1).replace('&amp;', '&')
    return parse_qs(urlparse(target).query), page


@needs_db
def test_oauth_metadata(client, db):
    d = client.get('/.well-known/oauth-authorization-server').get_json()
    assert d['issuer'] == 'http://localhost' and d['code_challenge_methods_supported'] == ['S256']
    assert d['registration_endpoint'].endswith('/oauth/register') and 'refresh_token' in d['grant_types_supported']
    prm = client.get('/.well-known/oauth-protected-resource/mcp').get_json()
    assert prm['authorization_servers'] == ['http://localhost'] and prm['resource'] == 'http://localhost/mcp'


@needs_db
def test_oauth_full_flow_pkce_refresh_revoke(client, db):
    redirect = 'https://claude.ai/api/mcp/auth_callback'
    r = client.post('/oauth/register', json={'client_name': 'Claude', 'redirect_uris': [redirect],
                                             'token_endpoint_auth_method': 'none'})
    assert r.status_code == 201
    cid = r.get_json()['client_id']
    assert 'client_secret' not in r.get_json()
    bad = client.post('/oauth/register', json={'redirect_uris': ['http://evil.example/cb']})
    assert bad.status_code == 400
    # GET con redirect_uri no registrado → página de error, SIN redirigir
    r = client.get('/oauth/authorize', query_string={'response_type': 'code', 'client_id': cid,
                                                     'redirect_uri': 'https://evil.example/cb',
                                                     'code_challenge': 'x' * 43, 'code_challenge_method': 'S256'})
    assert r.status_code == 400 and 'evil.example/cb?' not in r.get_data(as_text=True)
    # PIN incorrecto → sin consentimiento
    verifier, challenge = _pkce()
    q, page = _authorize(client, cid, redirect, challenge, pin='0000')
    assert q is None and 'PIN incorrecto' in page
    # flujo completo
    q, _page = _authorize(client, cid, redirect, challenge)
    assert q, _page
    assert q['state'] == ['st-123'] and q['iss'] == ['http://localhost']
    code = q['code'][0]
    tok_form = {'grant_type': 'authorization_code', 'code': code, 'redirect_uri': redirect, 'client_id': cid,
                'code_verifier': 'wrong' * 10, 'resource': 'http://localhost/mcp'}
    r = client.post('/oauth/token', data=tok_form)
    assert r.status_code == 400 and r.get_json()['error'] == 'invalid_grant'
    tok_form['code_verifier'] = verifier
    r = client.post('/oauth/token', data=tok_form)
    assert r.status_code == 200, r.get_json()
    t = r.get_json()
    assert r.headers['Cache-Control'] == 'no-store'
    assert t['token_type'] == 'Bearer' and t['access_token'].startswith('kmcp_') and t['expires_in'] > 0
    assert set(t['scope'].split()) == {'read', 'research'}
    assert rpc(client, t['access_token'], 'ping').status_code == 200
    # el código es de un solo uso — y reutilizarlo REVOCA lo que ya emitió (OAuth 2.1)
    r = client.post('/oauth/token', data=tok_form)
    assert r.status_code == 400 and r.get_json()['error'] == 'invalid_grant'
    assert rpc(client, t['access_token'], 'ping').status_code == 401
    # nueva autorización para seguir el flujo
    verifier, challenge = _pkce()
    q, _page = _authorize(client, cid, redirect, challenge)
    tok_form.update(code=q['code'][0], code_verifier=verifier)
    r = client.post('/oauth/token', data=tok_form)
    assert r.status_code == 200, r.get_json()
    t = r.get_json()
    # el token sirve en /mcp
    r = rpc(client, t['access_token'], 'tools/list')
    names = {x['name'] for x in r.get_json()['result']['tools']}
    assert 'run_research' in names and 'preview_order' not in names
    # visible y revocable desde la UI (kind oauth)
    lst = client.get('/api/mcp/tokens', headers=pin_h()).get_json()['tokens']
    assert any(x['kind'] == 'oauth' and x['name'] == 'Claude (OAuth)' for x in lst)
    # refresh rota el par: el access token viejo deja de servir
    r = client.post('/oauth/token', data={'grant_type': 'refresh_token', 'refresh_token': t['refresh_token'],
                                          'client_id': cid})
    assert r.status_code == 200
    t2 = r.get_json()
    assert t2['access_token'] != t['access_token']
    assert rpc(client, t['access_token'], 'ping').status_code == 401
    assert rpc(client, t2['access_token'], 'ping').status_code == 200
    r = client.post('/oauth/token', data={'grant_type': 'refresh_token', 'refresh_token': t['refresh_token'],
                                          'client_id': cid})
    assert r.status_code == 400
    # revocación RFC 7009
    assert client.post('/oauth/revoke', data={'token': t2['access_token'], 'client_id': cid}).status_code == 200
    assert rpc(client, t2['access_token'], 'ping').status_code == 401
    # otro cliente no puede canjear
    assert client.post('/oauth/token', data={'grant_type': 'password', 'client_id': cid}).get_json()['error'] \
        == 'unsupported_grant_type'
    assert client.post('/oauth/token', data={'grant_type': 'authorization_code', 'client_id': 'nope'}).status_code == 401


@needs_db
def test_oauth_deny_and_trade_consent(client, db, monkeypatch):
    monkeypatch.setitem(sys.modules, 'brokerage.service', _fake_brokerage())
    redirect = 'http://localhost:6274/oauth/callback'
    cid = client.post('/oauth/register', json={'client_name': 'Inspector', 'redirect_uris': [redirect]}).get_json()['client_id']
    verifier, challenge = _pkce()
    # trade sin cliente → vuelve a pedir
    q, page = _authorize(client, cid, redirect, challenge, extra={'scope_trade': '1'})
    assert q is None and 'elige un cliente de corretaje' in page
    assert 'name="scope_trade" id="st" value="1" checked' in page      # conserva lo elegido
    # trade con cliente → token ligado a c1
    q, _ = _authorize(client, cid, redirect, challenge, extra={'scope_trade': '1', 'broker_client_id': 'c1'})
    r = client.post('/oauth/token', data={'grant_type': 'authorization_code', 'code': q['code'][0],
                                          'redirect_uri': redirect, 'client_id': cid, 'code_verifier': verifier})
    t = r.get_json()
    assert 'trade' in t['scope'].split()
    names = {x['name'] for x in rpc(client, t['access_token'], 'tools/list').get_json()['result']['tools']}
    assert 'preview_order' in names
    # denegar → error=access_denied con el state
    qd = {'response_type': 'code', 'client_id': cid, 'redirect_uri': redirect, 'code_challenge': challenge,
          'code_challenge_method': 'S256', 'state': 'zz'}
    page = client.post('/oauth/authorize', data=dict(qd, step='pin', pin=PIN)).get_data(as_text=True)
    consent = _hidden(page, 'consent')
    page = client.post('/oauth/authorize', data={'step': 'consent', 'consent': consent,
                                                 'decision': 'deny'}).get_data(as_text=True)
    target = unquote(re.search(r'url=([^"]+)"', page).group(1)).replace('&amp;', '&')
    assert 'error=access_denied' in target and 'state=zz' in target


# ════════════════════════════════════════════════════════════════════════════
# integración con el brokerage.service REAL (Alpaca falso, sin red)
# ════════════════════════════════════════════════════════════════════════════
class _MiniAlpaca:
    paper = True

    def __init__(self):
        self.submits = []

    def get_account(self):
        return {'equity': '10000', 'cash': '10000', 'buying_power': '10000', 'portfolio_value': '10000',
                'currency': 'USD', 'status': 'ACTIVE'}

    def get_positions(self):
        return []

    def get_clock(self):
        return {'is_open': True}

    def latest_price(self, symbol):
        return 100.0

    def submit_order(self, symbol, side, notional=None, qty=None, order_type='market', limit_price=None,
                     time_in_force=None, client_order_id=None):
        self.submits.append(client_order_id)
        return {'id': 'alp-real-1', 'client_order_id': client_order_id, 'status': 'accepted',
                'filled_qty': '0', 'filled_avg_price': None}

    def get_order(self, oid):
        return {'id': oid, 'status': 'accepted', 'filled_qty': '0'}

    def get_order_by_client_id(self, coid):
        from brokerage.alpaca import AlpacaError
        raise AlpacaError('Alpaca HTTP 404', status=404)

    def cancel_order(self, oid):
        return {}


@needs_db
def test_real_brokerage_contract_end_to_end(client, db, monkeypatch):
    try:
        from cryptography.fernet import Fernet
        from brokerage import service
    except Exception:  # noqa: BLE001
        pytest.skip('brokerage/cryptography no disponible')
    for k in ('BROKERAGE_TRADING_ENABLED', 'BROKERAGE_LIVE_ENABLED', 'BROKERAGE_AUTO_APPROVE_PAPER',
              'ALPACA_KEY', 'ALPACA_SECRET', 'ALPACA_BASE'):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv('BROKERAGE_ENC_KEY', Fernet.generate_key().decode())
    fake = _MiniAlpaca()
    monkeypatch.setattr(service, 'make_alpaca', lambda rec: fake)
    from ontology.db import session_scope
    with session_scope() as s:
        r = service.create_client(s, 'Cliente MCP', actor='pytest')
        cid = r['client']['id']
        assert service.set_credentials(s, cid, 'PKTESTKEY0001ABCD', 'sEcReT-value-1234', env='paper',
                                       actor='pytest', verify=False)['ok']
    tok = make_token(client, ['read', 'trade'], client_id=cid)['token']
    _, d = call_tool(client, tok, 'get_account')
    sc = d['result']['structuredContent']
    assert d['result']['isError'] is False and sc['account']['equity'] == 10000.0 and sc['client']['id'] == cid
    _, d = call_tool(client, tok, 'preview_order', {'symbol': 'NVDA', 'side': 'buy', 'notional': 20,
                                                    'rationale': 'integration test with the real service'})
    sc = d['result']['structuredContent']
    assert d['result']['isError'] is False, sc
    assert sc['status'] == 'pending_approval' and sc['requires_human_approval'] is True and sc['source'] == 'mcp'
    pid = sc['preview_id']
    _, d = call_tool(client, tok, 'submit_order', {'preview_id': pid})
    sc = d['result']['structuredContent']
    assert sc['status'] == 'pending_human_approval' and fake.submits == []          # nada llegó al bróker
    with session_scope() as s:
        pend = [o['id'] for o in service.pending_approvals(s)]
        assert pid in pend                                                            # visible en Aprobaciones
        res = service.approve_preview(s, pid, 'Fabrizio (PIN)')                      # el humano aprueba
        assert res['ok'] and res['status'] == 'submitted', res
    assert fake.submits == [pid]
    _, d = call_tool(client, tok, 'get_order_status', {'order_id': pid})
    assert d['result']['structuredContent']['order']['status'] in ('submitted', 'accepted')
    # auto-aprobación de PAPEL: el agente puede enviar él mismo
    monkeypatch.setenv('BROKERAGE_AUTO_APPROVE_PAPER', 'on')
    _, d = call_tool(client, tok, 'preview_order', {'symbol': 'AMD', 'side': 'buy', 'notional': 15,
                                                    'rationale': 'auto-approve paper integration'})
    sc = d['result']['structuredContent']
    assert sc['status'] == 'previewed' and sc['requires_human_approval'] is False
    _, d = call_tool(client, tok, 'submit_order', {'preview_id': sc['preview_id']})
    assert d['result']['structuredContent']['status'] == 'submitted'
    # interruptor global del corretaje → bloqueado con un control claro
    monkeypatch.setenv('BROKERAGE_TRADING_ENABLED', 'off')
    _, d = call_tool(client, tok, 'preview_order', {'symbol': 'AMD', 'side': 'buy', 'notional': 15,
                                                    'rationale': 'kill switch must block this'})
    sc = d['result']['structuredContent']
    assert sc.get('blocked') is True and 'BLOCKED' in sc['next']


# ════════════════════════════════════════════════════════════════════════════
# correcciones tras la revisión (2026-09-30)
# ════════════════════════════════════════════════════════════════════════════
def test_non_finite_numbers_rejected(client, nodb):
    """#3 NaN/Infinity: -32700 en el transporte, -32602 en la validación, la
    auditoría y los resultados nunca llevan números no finitos."""
    from mcp_server.auth import summarize_args
    from mcp_server.protocol import _tool_result
    from mcp_server.tools import InvalidParams, REGISTRY, validate
    h = {'Authorization': f'Bearer {nodb}', 'Content-Type': 'application/json'}
    for const in ('Infinity', '-Infinity', 'NaN'):
        body = ('{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_risk_report",'
                '"arguments":{"positions":[{"symbol":"NVDA","shares":%s}]}}}' % const)
        r = client.post('/mcp', data=body, headers=h)
        assert r.status_code == 400 and r.get_json()['error']['code'] == -32700, const
    sch = REGISTRY['preview_order'].input_schema
    for bad in (float('inf'), float('nan'), 'inf', '-Infinity', 'nan'):
        with pytest.raises(InvalidParams):
            validate(sch, {'symbol': 'NVDA', 'side': 'buy', 'qty': bad, 'rationale': 'x' * 12})
    with pytest.raises(InvalidParams):
        validate(REGISTRY['search_companies'].input_schema, {'query': 'x', 'limit': float('inf')})
    s = summarize_args({'qty': float('inf'), 'lp': float('nan'), 'ok': 1.5, 'nested': [float('-inf')]})
    assert s == {'qty': 'inf', 'lp': 'nan', 'ok': 1.5, 'nested': ['-inf']}
    json.dumps(s, allow_nan=False)
    res = _tool_result({'var': float('nan'), 'rows': [{'x': float('inf')}], 'n': 2})
    assert res['isError'] is False and res['structuredContent'] == {'var': None, 'rows': [{'x': None}], 'n': 2}
    json.dumps(res, allow_nan=False)


def test_origin_dns_rebinding_blocked(client, nodb, monkeypatch):
    """#5/#19 Origin == Host (DNS rebinding) ya NO pasa: solo la lista fija."""
    h = {'Authorization': f'Bearer {nodb}', 'Content-Type': 'application/json', 'Origin': 'http://evil.example:5000'}
    msg = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'ping'})
    r = client.post('/mcp', data=msg, headers=h, base_url='http://evil.example:5000')
    assert r.status_code == 403 and 'Access-Control-Allow-Origin' not in r.headers
    # localhost solo cuando el propio servidor se alcanzó por localhost
    r = client.post('/mcp', data=msg, base_url='http://evil.example:5000',
                    headers=dict(h, Origin='http://localhost:6274'))
    assert r.status_code == 403
    r = client.post('/mcp', data=msg, headers=dict(h, Origin='http://localhost:6274'))
    assert r.status_code == 200
    # orígenes FIJOS: MCP_PUBLIC_URL, RAILWAY_PUBLIC_DOMAIN, MCP_ALLOWED_ORIGINS
    monkeypatch.setenv('MCP_PUBLIC_URL', 'https://khipus.example/app')
    monkeypatch.setenv('RAILWAY_PUBLIC_DOMAIN', 'khipus-prod.up.railway.app')
    for o in ('https://khipus.example', 'https://KHIPUS-prod.up.railway.app'):
        r = client.post('/mcp', data=msg, headers=dict(h, Origin=o), base_url='https://anything.example')
        assert r.status_code == 200, o
    r = client.post('/mcp', data=msg, headers=dict(h, Origin='https://khipus.example.evil.com'),
                    base_url='https://khipus.example.evil.com')
    assert r.status_code == 403
    assert client.post('/mcp', data=msg, headers=dict(h, Origin='null')).status_code == 403
    # MCP_ALLOWED_HOSTS (opcional)
    monkeypatch.setenv('MCP_ALLOWED_HOSTS', 'khipus.example')
    h2 = {'Authorization': f'Bearer {nodb}', 'Content-Type': 'application/json'}
    assert client.post('/mcp', data=msg, headers=h2, base_url='https://rebind.attacker.example').status_code == 403
    assert client.post('/mcp', data=msg, headers=h2, base_url='https://khipus.example').status_code == 200


def test_session_termination_is_honoured(client, nodb):
    """#10 DELETE → después ese Mcp-Session-Id responde 404."""
    r = rpc(client, nodb, 'initialize', {'protocolVersion': '2025-06-18'})
    sid = r.headers['Mcp-Session-Id']
    hs = {'Mcp-Session-Id': sid, 'MCP-Protocol-Version': '2025-06-18'}
    assert rpc(client, nodb, 'ping', headers=hs).status_code == 200
    d = client.delete('/mcp', headers={'Authorization': f'Bearer {nodb}', 'Mcp-Session-Id': sid})
    assert d.status_code == 204
    assert rpc(client, nodb, 'ping', headers=hs).status_code == 404
    assert client.delete('/mcp', headers={'Authorization': f'Bearer {nodb}', 'Mcp-Session-Id': sid}).status_code == 404
    # un id desconocido (p. ej. tras un redeploy) se acepta… hasta que se cierra
    hs2 = {'Mcp-Session-Id': 'unknown-after-redeploy'}
    assert rpc(client, nodb, 'ping', headers=hs2).status_code == 200
    assert client.delete('/mcp', headers={'Authorization': f'Bearer {nodb}',
                                          'Mcp-Session-Id': 'unknown-after-redeploy'}).status_code == 204
    assert rpc(client, nodb, 'ping', headers=hs2).status_code == 404
    assert client.delete('/mcp', headers={'Authorization': f'Bearer {nodb}'}).status_code == 400
    # re-initialize → sesión nueva que funciona
    sid2 = rpc(client, nodb, 'initialize', {'protocolVersion': '2025-06-18'}).headers['Mcp-Session-Id']
    assert sid2 != sid and rpc(client, nodb, 'ping', headers={'Mcp-Session-Id': sid2}).status_code == 200


def test_batch_rate_limit_per_message_and_version(client, nodb, monkeypatch):
    """#17 el límite cuenta MENSAJES; lotes prohibidos en 2025-06-18; initialize no va en lote."""
    monkeypatch.setenv('MCP_RATE_PER_MIN', '3')
    h = {'Authorization': f'Bearer {nodb}', 'Content-Type': 'application/json'}
    batch = [{'jsonrpc': '2.0', 'id': i, 'method': 'ping'} for i in range(5)]
    out = client.post('/mcp', data=json.dumps(batch), headers=h).get_json()
    assert [x['id'] for x in out] == [0, 1, 2, 3, 4]
    assert sum(1 for x in out if 'result' in x) == 3
    assert all(x['error']['code'] == -32000 and 'Rate limit' in x['error']['message'] for x in out if 'error' in x)
    assert rpc(client, nodb, 'ping').status_code == 429                       # el cupo del minuto se agotó
    monkeypatch.setenv('MCP_RATE_PER_MIN', '100')
    r = client.post('/mcp', data=json.dumps(batch[:2]), headers=dict(h, **{'MCP-Protocol-Version': '2025-06-18'}))
    assert r.status_code == 400 and 'batching is not supported' in r.get_json()['error']['message']
    sid = rpc(client, nodb, 'initialize', {'protocolVersion': '2025-06-18'}).headers['Mcp-Session-Id']
    r = client.post('/mcp', data=json.dumps(batch[:2]), headers=dict(h, **{'Mcp-Session-Id': sid}))
    assert r.status_code == 400                                               # versión negociada de la sesión
    init_batch = [{'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-03-26'}},
                  {'jsonrpc': '2.0', 'id': 2, 'method': 'ping'}]
    assert client.post('/mcp', data=json.dumps(init_batch), headers=h).status_code == 400


def test_inflight_cap_per_token_and_total(client, nodb, monkeypatch):
    """#17 tope de peticiones EN CURSO: por token (3) y en total (5)."""
    from mcp_server import auth as _a
    assert _a.limits()['inflight_per_token'] == 3 and _a.limits()['inflight_total'] == 5
    for _ in range(3):
        assert _a.inflight_acquire('static') is None
    r = rpc(client, nodb, 'ping')
    assert r.status_code == 429 and r.headers['Retry-After'] == '5' and 'concurrent' in r.get_json()['error']['message']
    _a.inflight_release('static')
    assert rpc(client, nodb, 'ping').status_code == 200
    _a.inflight_release('static')
    _a.inflight_release('static')
    assert _a._INFLIGHT == {'total': 0, 'by': {}}                              # se libera siempre (finally)
    monkeypatch.setenv('MCP_MAX_INFLIGHT_TOTAL', '2')
    assert _a.inflight_acquire('other-1') is None and _a.inflight_acquire('other-2') is None
    r = rpc(client, nodb, 'ping')
    assert r.status_code == 429 and 'busy' in r.get_json()['error']['message']
    _a.inflight_release('other-1')
    _a.inflight_release('other-2')


def test_pin_global_lockout_and_trusted_ip(client, nodb, monkeypatch):
    """#12/#14 rotar X-Forwarded-For no sirve: bloqueo GLOBAL tras N fallos, también
    para el PIN correcto; el PIN vacío no cuenta; IP = salto del proxy de confianza."""
    from flask import Flask

    from mcp_server import auth as _a
    monkeypatch.setenv('MCP_PIN_MAX_FAILS', '3')
    assert client.get('/api/mcp/tokens').status_code == 401                   # vacío: no cuenta
    for i in range(3):
        r = client.get('/api/mcp/tokens', headers={'X-Trade-Pin': f'999{i}', 'X-Forwarded-For': f'10.0.0.{i}'})
        assert r.status_code == 401
    r = client.get('/api/mcp/tokens', headers={'X-Trade-Pin': PIN, 'X-Forwarded-For': '10.9.9.9'})
    assert r.status_code == 429 and r.get_json()['code'] == 'pin_locked' and int(r.headers['Retry-After']) > 60
    assert r.get_json()['error_en'].startswith('Too many wrong PINs')
    assert client.get('/api/mcp/status').get_json()['pin_locked_s'] > 0
    _a.reset_pin_guard()
    assert client.get('/api/mcp/tokens', headers={'X-Trade-Pin': PIN}).status_code == 503   # libre (sin base)
    # IP: el salto que añade el proxy (el último), no el primero que escribe el cliente
    app = Flask('ip-test')
    with app.test_request_context('/', headers={'X-Forwarded-For': '6.6.6.6, 203.0.113.7'},
                                  environ_base={'REMOTE_ADDR': '10.0.0.1'}):
        assert _a.client_ip() == '203.0.113.7'
        monkeypatch.setenv('MCP_TRUSTED_PROXY_HOPS', '0')
        assert _a.client_ip() == '10.0.0.1'
    monkeypatch.setenv('TRADE_PIN', '12345678ab')
    assert client.get('/api/mcp/status').get_json()['pin_strong'] is True


def test_mcpconnect_chip_outside_label():
    """#9 el «?» de human_approval no puede estar dentro del <label> del checkbox."""
    js = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'engine',
                           'mcpconnect.js'), encoding='utf-8').read()
    assert "chip('human_approval') + '</label>" not in js
    assert "'</label>' + chip('human_approval')" in js
    assert 'installEntry' in js and 'sistema-tabseg' in js                    # #2 entrada desde 🩺 Sistema


@needs_db
def test_db_outage_is_503_not_invalid_token(client, db, monkeypatch):
    """#6 base caída → 503 + Retry-After (el token sigue siendo válido), nunca 401."""
    tok = make_token(client, ['read'])['token']
    import ontology.db as odb
    from sqlalchemy.exc import OperationalError

    class _Down:
        def __enter__(self):
            raise OperationalError('SELECT 1', {}, Exception('server closed the connection unexpectedly'))

        def __exit__(self, *a):
            return False
    monkeypatch.setattr(odb, 'session_scope', lambda: _Down())
    r = rpc(client, tok, 'ping')
    assert r.status_code == 503 and r.headers['Retry-After'] == '30'
    assert 'WWW-Authenticate' not in r.headers
    assert client.delete('/mcp', headers={'Authorization': f'Bearer {tok}', 'Mcp-Session-Id': 'x'}).status_code == 503
    monkeypatch.undo()
    monkeypatch.setenv('TRADE_PIN', PIN)
    assert rpc(client, tok, 'ping').status_code == 200


@needs_db
def test_use_count_concurrent_increments(client, db):
    """#8 incremento en SQL: 30 autenticaciones simultáneas = 30 usos."""
    from concurrent.futures import ThreadPoolExecutor

    from mcp_server import auth as _a
    t = make_token(client, ['read'], name='concurrency-probe')
    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(lambda _: _a.authenticate(f'Bearer {t["token"]}'), range(30)))
    assert all(p is not None and p.token_id == t['id'] for p in res)
    row = next(x for x in client.get('/api/mcp/tokens', headers=pin_h()).get_json()['tokens'] if x['id'] == t['id'])
    assert row['use_count'] == 30


@needs_db
def test_bilingual_token_errors(client, db, monkeypatch):
    """#22 los errores del API de tokens traen error (es) y error_en (en)."""
    r = client.post('/api/mcp/tokens', headers=pin_h(), data=json.dumps({'name': 'x', 'scopes': ['admin']}))
    d = r.get_json()
    assert r.status_code == 400 and d['error'].startswith('alcances desconocidos') and d['error_en'].startswith(
        'unknown scopes')
    d = client.post('/api/mcp/tokens', headers=pin_h(), data=json.dumps({'name': 'x', 'scopes': ['trade']})).get_json()
    assert 'client_id' in d['error_en'] and d['error'] != d['error_en']
    monkeypatch.setitem(sys.modules, 'brokerage.service', _fake_brokerage())
    d = client.post('/api/mcp/tokens', headers=pin_h(),
                    data=json.dumps({'name': 'x', 'scopes': ['trade'], 'client_id': 'nobody'})).get_json()
    assert d['error'] == 'cliente de corretaje no encontrado' and d['error_en'] == 'brokerage client not found'
    d = client.post('/api/mcp/tokens/nope/revoke', headers=pin_h(), data='{}').get_json()
    assert d['error_en'] == 'token not found'


@needs_db
def test_run_research_budget_zero_and_env(client, db, monkeypatch):
    """#21 RESEARCH_DAILY_BUDGET_USD=0 = investigación apagada (no «$2.00»)."""
    import core.ai
    import research.runner as runner
    monkeypatch.setattr(core.ai, '_ai_configured', lambda: True)
    monkeypatch.setattr(runner, 'execute_job_async', lambda jid: None)
    tok = make_token(client, ['read', 'research'])['token']
    monkeypatch.setenv('RESEARCH_DAILY_BUDGET_USD', '0')
    _, d = call_tool(client, tok, 'run_research', {'entity': 'AMD'})
    sc = d['result']['structuredContent']
    assert d['result']['isError'] and sc['code'] == 'budget_exhausted' and 'switched off' in sc['error']
    monkeypatch.setenv('RESEARCH_DAILY_BUDGET_USD', '3.5')
    _, d = call_tool(client, tok, 'run_research', {'entity': 'AMD'})
    assert d['result']['structuredContent']['daily_budget_usd'] == 3.5
    monkeypatch.setenv('RESEARCH_DAILY_BUDGET_USD', 'lots')                    # ilegible → 2.0 (como el runner)
    _, d = call_tool(client, tok, 'run_research', {'entity': 'AMD'})
    assert d['result']['structuredContent']['daily_budget_usd'] == 2.0


def _fake_committee():
    import threading as _th
    m = types.ModuleType('research.committee')
    m.slots = _th.BoundedSemaphore(2)
    m.recent = None
    m.placeholders, m.runs, m.released = [], [], []
    m.fail_placeholder = False
    m.gate = _th.Event()

    class _Row:
        def __init__(self, id_, status='running'):
            self.id, self.status = id_, status

    def recent_memo(s, eid, cid=None):
        return m.recent
    m.recent_memo = recent_memo
    m.acquire_run_slot = lambda: m.slots.acquire(blocking=False)

    def release_run_slot():
        m.released.append(1)
        m.slots.release()
    m.release_run_slot = release_run_slot

    def create_placeholder(s, eid, actor, cid=None):
        if m.fail_placeholder:
            raise RuntimeError('db hiccup')
        m.placeholders.append((eid, actor, cid))
        return _Row(f'memo-{len(m.placeholders)}')
    m.create_placeholder = create_placeholder

    def run_committee(s, eid, actor, client_id=None, memo_id=None):
        m.gate.wait(5)
        m.runs.append(memo_id)
    m.run_committee = run_committee
    m.fail_memo = lambda s, mid, err, err_en=None: None
    return m, _Row


@needs_db
def test_run_committee_reuses_and_respects_slots(client, db, monkeypatch):
    """#1/#18 run_committee por MCP: reutiliza el memo reciente y respeta el tope
    de comités simultáneos (acquire/release como committee_api)."""
    import time as _t
    fake, _Row = _fake_committee()
    monkeypatch.setitem(sys.modules, 'research.committee', fake)
    tok = make_token(client, ['read', 'research'])['token']
    ids = []
    for _ in range(2):
        _, d = call_tool(client, tok, 'run_committee', {'entity': 'AMD'})
        sc = d['result']['structuredContent']
        assert d['result']['isError'] is False and sc['reused'] is False and sc['status'] == 'running'
        ids.append(sc['memo_id'])
    _, d = call_tool(client, tok, 'run_committee', {'entity': 'AMD'})            # los 2 cupos ocupados
    assert d['result']['isError'] and d['result']['structuredContent']['code'] == 'busy'
    assert len(fake.placeholders) == 2
    fake.gate.set()
    for _ in range(50):
        if len(fake.released) == 2:
            break
        _t.sleep(0.05)
    assert sorted(fake.runs) == sorted(ids) and len(fake.released) == 2      # el hilo libera el cupo
    # memo reciente para el mismo (entidad, cliente) → se devuelve ese, sin IA ni cupo
    fake.recent = _Row('memo-prev', 'proposed')
    _, d = call_tool(client, tok, 'run_committee', {'entity': 'AMD'})
    sc = d['result']['structuredContent']
    assert sc['reused'] is True and sc['memo_id'] == 'memo-prev' and sc['status'] == 'proposed'
    assert len(fake.placeholders) == 2
    # si falla la creación del memo, el cupo se libera en el acto
    fake.recent = None
    fake.fail_placeholder = True
    _, d = call_tool(client, tok, 'run_committee', {'entity': 'AMD'})
    assert d['result']['isError'] and len(fake.released) == 3
    assert fake.slots.acquire(blocking=False) and fake.slots.acquire(blocking=False)   # ambos cupos libres


@needs_db
def test_cancel_only_own_mcp_orders_and_mode_guard(client, db, monkeypatch):
    """#7/#16 un agente no cancela órdenes de una persona ni del comité; #15 si la
    cuenta cambió de modo desde la previsualización, submit_order no confirma."""
    fake = _fake_brokerage(auto_approve=True)
    monkeypatch.setitem(sys.modules, 'brokerage.service', fake)
    tok = make_token(client, ['trade'], client_id='c1', name='agent-A')['token']
    human = fake.preview_order(None, 'c1', 'NVDA', 'sell', qty=1, order_type='limit', source='ui',
                               requested_by='Fabrizio')
    committee = fake.preview_order(None, 'c1', 'AMD', 'buy', notional=10, source='committee',
                                   requested_by='committee')
    for o in (human, committee):
        _, d = call_tool(client, tok, 'cancel_order', {'order_id': o['preview_id']})
        sc = d['result']['structuredContent']
        assert d['result']['isError'] and sc['code'] == 'forbidden' and '👥 Clientes' in sc['error']
        assert fake.orders[o['preview_id']]['status'] != 'canceled'
    # otro agente (otro token) del mismo cliente tampoco
    other_tok = make_token(client, ['trade'], client_id='c1', name='agent-B')['token']
    _, d = call_tool(client, tok, 'preview_order', {'symbol': 'NVDA', 'side': 'buy', 'notional': 5,
                                                    'rationale': 'own order to cancel later'})
    mine = d['result']['structuredContent']['preview_id']
    _, d = call_tool(client, other_tok, 'cancel_order', {'order_id': mine})
    assert d['result']['structuredContent']['code'] == 'forbidden'
    _, d = call_tool(client, tok, 'cancel_order', {'order_id': mine})
    assert d['result']['isError'] is False and fake.orders[mine]['status'] == 'canceled'
    # modo cambió (papel → real) entre preview y submit → no se confirma
    _, d = call_tool(client, tok, 'preview_order', {'symbol': 'NVDA', 'side': 'buy', 'notional': 5,
                                                    'rationale': 'mode guard defence in depth'})
    pid = d['result']['structuredContent']['preview_id']
    fake.clients['c1']['mode'], fake.clients['c1']['paper'] = 'live', False
    _, d = call_tool(client, tok, 'submit_order', {'preview_id': pid})
    sc = d['result']['structuredContent']
    assert d['result']['isError'] and sc['code'] == 'account_changed'
    assert ('confirm', pid, 'mcp') not in fake.calls


@needs_db
def test_instructions_when_trading_switched_off(client, db, monkeypatch):
    """#11 con MCP_TRADING_ENABLED=off las instrucciones no prometen trading."""
    monkeypatch.setitem(sys.modules, 'brokerage.service', _fake_brokerage())
    tok = make_token(client, ['read', 'trade'], client_id='c1')['token']
    monkeypatch.setenv('MCP_TRADING_ENABLED', 'off')
    ins = rpc(client, tok, 'initialize', {'protocolVersion': '2025-06-18'}).get_json()['result']['instructions']
    assert 'switched off' in ins and 'HUMAN APPROVAL queue' not in ins
    assert not any(t['name'] == 'preview_order' for t in rpc(client, tok, 'tools/list').get_json()['result']['tools'])


@needs_db
def test_oauth_request_errors_do_not_auto_redirect(client, db):
    """#4 open redirect: errores ANTES del PIN → página con enlace rotulado, sin meta refresh."""
    redirect = 'https://phish.example/login'
    cid = client.post('/oauth/register', json={'client_name': 'Attacker', 'redirect_uris': [redirect]}).get_json()[
        'client_id']
    for q in ({'response_type': 'token'}, {'response_type': 'code'},                          # sin PKCE
              {'response_type': 'code', 'code_challenge': 'short', 'code_challenge_method': 'S256'}):
        r = client.get('/oauth/authorize', query_string=dict(q, client_id=cid, redirect_uri=redirect, state='s'))
        page = r.get_data(as_text=True)
        assert r.status_code == 400 and 'http-equiv="refresh"' not in page
        assert 'phish.example' in page and 'href="https://phish.example/login?error=' in page
    # también por POST (paso PIN) sin redirigir solo
    _v, ch = _pkce()
    r = client.post('/oauth/authorize', data={'step': 'pin', 'pin': PIN, 'client_id': cid, 'redirect_uri': redirect,
                                              'response_type': 'token', 'code_challenge': ch,
                                              'code_challenge_method': 'S256'})
    assert r.status_code == 400 and 'http-equiv="refresh"' not in r.get_data(as_text=True)


@needs_db
def test_oauth_consent_replay_and_pin_lockout(client, db, monkeypatch):
    """#20 el mismo consentimiento firmado solo se canjea UNA vez; #14 el paso PIN
    de OAuth respeta el bloqueo global."""
    redirect = 'https://claude.ai/api/mcp/auth_callback'
    cid = client.post('/oauth/register', json={'client_name': 'Claude', 'redirect_uris': [redirect]}).get_json()[
        'client_id']
    verifier, challenge = _pkce()
    q = {'response_type': 'code', 'client_id': cid, 'redirect_uri': redirect, 'code_challenge': challenge,
         'code_challenge_method': 'S256', 'state': 's1'}
    page = client.post('/oauth/authorize', data=dict(q, step='pin', pin=PIN)).get_data(as_text=True)
    consent = _hidden(page, 'consent').replace('&amp;', '&')
    form = {'step': 'consent', 'consent': consent, 'decision': 'approve', 'token_name': 'Claude'}
    r1 = client.post('/oauth/authorize', data=form)
    assert 'code=' in r1.get_data(as_text=True)
    r2 = client.post('/oauth/authorize', data=form)
    assert r2.status_code == 409 and 'code=' not in r2.get_data(as_text=True)
    # bloqueo global: rotar X-Forwarded-For no da más intentos
    monkeypatch.setenv('MCP_PIN_MAX_FAILS', '2')
    for i in range(2):
        client.post('/oauth/authorize', data=dict(q, step='pin', pin=f'bad{i}'),
                    headers={'X-Forwarded-For': f'1.1.1.{i}'})
    page = client.post('/oauth/authorize', data=dict(q, step='pin', pin=PIN),
                       headers={'X-Forwarded-For': '9.9.9.9'}).get_data(as_text=True)
    assert 'PIN queda bloqueado' in page and _hidden(page, 'consent') is None
    rows = client.get('/api/mcp/audit?limit=20', headers=pin_h())
    assert rows.status_code == 429                                              # el panel también queda bloqueado
    from mcp_server import auth as _a
    _a.reset_pin_guard()
    rows = client.get('/api/mcp/audit?limit=50', headers=pin_h()).get_json()['audit']
    assert any(x['method'] == 'pin_lockout' and x['status'] == 'locked' for x in rows)
    assert sum(1 for x in rows if x['method'] == 'pin_check' and x['status'] == 'denied') >= 2


@needs_db
def test_oauth_code_concurrent_redemption_single_winner(client, db):
    """#13 dos canjes simultáneos del mismo código → uno gana; el otro revoca al ganador."""
    from concurrent.futures import ThreadPoolExecutor
    redirect = 'https://claude.ai/api/mcp/auth_callback'
    cid = client.post('/oauth/register', json={'client_name': 'Claude', 'redirect_uris': [redirect]}).get_json()[
        'client_id']
    verifier, challenge = _pkce()
    qq, _ = _authorize(client, cid, redirect, challenge)
    form = {'grant_type': 'authorization_code', 'code': qq['code'][0], 'redirect_uri': redirect, 'client_id': cid,
            'code_verifier': verifier}
    app = client.application

    def _x(_):
        with app.test_client() as c:
            r = c.post('/oauth/token', data=form)
            return r.status_code, r.get_json()
    with ThreadPoolExecutor(max_workers=4) as ex:
        res = list(ex.map(_x, range(4)))
    oks = [d for st, d in res if st == 200]
    assert len(oks) == 1, res
    assert all(d['error'] == 'invalid_grant' for st, d in res if st != 200)
    assert rpc(client, oks[0]['access_token'], 'ping').status_code == 401        # reutilización → revocado


@needs_db
def test_real_brokerage_cancel_denied_for_ui_order(client, db, monkeypatch):
    """#7/#16 con el servicio REAL: una previsualización de la UI no la cancela un agente."""
    try:
        from cryptography.fernet import Fernet
        from brokerage import service
    except Exception:  # noqa: BLE001
        pytest.skip('brokerage/cryptography no disponible')
    for k in ('BROKERAGE_TRADING_ENABLED', 'BROKERAGE_LIVE_ENABLED', 'ALPACA_KEY', 'ALPACA_SECRET', 'ALPACA_BASE'):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv('BROKERAGE_ENC_KEY', Fernet.generate_key().decode())
    monkeypatch.setattr(service, 'make_alpaca', lambda rec: _MiniAlpaca())
    from ontology.db import session_scope
    with session_scope() as s:
        cid = service.create_client(s, 'Cliente Cancel', actor='pytest')['client']['id']
        assert service.set_credentials(s, cid, 'PKTESTKEY0002ABCD', 'sEcReT-value-5678', env='paper',
                                       actor='pytest', verify=False)['ok']
        ui = service.preview_order(s, cid, 'NVDA', 'buy', notional=12, source='ui', requested_by='Fabrizio')
        assert ui['ok'], ui
    tok = make_token(client, ['trade'], client_id=cid)['token']
    _, d = call_tool(client, tok, 'cancel_order', {'order_id': ui['preview_id']})
    assert d['result']['isError'] and d['result']['structuredContent']['code'] == 'forbidden'
    with session_scope() as s:
        assert service.get_order(s, ui['preview_id'])['status'] == 'previewed'
    # preview_order con limit_price=Infinity ya no llega al corretaje (-32602) y queda auditado
    _, d = call_tool(client, tok, 'preview_order', {'symbol': 'NVDA', 'side': 'buy', 'qty': 1, 'order_type': 'limit',
                                                    'limit_price': 'Infinity', 'rationale': 'non finite limit price'})
    assert d['error']['code'] == -32602
    rows = client.get('/api/mcp/audit?limit=5', headers=pin_h()).get_json()['audit']
    assert rows[0]['tool'] == 'preview_order' and rows[0]['status'] == 'invalid'


@needs_db
def test_late_columns_self_heal(client, db):
    """Una base con las tablas mcp_* de la primera versión (sin columnas nuevas) se
    repara sola con ADD COLUMN IF NOT EXISTS en el primer uso."""
    from sqlalchemy import text

    from ontology.db import _get_engine
    with _get_engine().begin() as conn:
        conn.execute(text('ALTER TABLE mcp_tokens DROP COLUMN IF EXISTS oauth_code_hash'))
        conn.execute(text('ALTER TABLE mcp_oauth_codes DROP COLUMN IF EXISTS consent_nonce'))
    t = make_token(client, ['read'], name='late-columns')
    assert rpc(client, t['token'], 'ping').status_code == 200
    with _get_engine().connect() as conn:
        cols = {r[0] for r in conn.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name IN ('mcp_tokens','mcp_oauth_codes')"))}
    assert {'oauth_code_hash', 'consent_nonce'} <= cols
