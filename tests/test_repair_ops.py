"""tests/test_repair_ops.py — O1 (misión de reparación 2026-10-04): humo del
MCP vivo (scripts/smoke_mcp.py) + chequeo diario guardado (core/ops_check.py).

Antes: ~60 tests del MCP con dobles pero NADA contra el despliegue vivo ni un
"último chequeo" consultable. Aquí se verifica que el humo funciona contra un
servidor MCP real (en proceso), que JAMÁS llama herramientas que no sean de
lectura y que el chequeo diario queda guardado y respeta su cadencia.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv('DATABASE_URL', '')
STATIC = 'static-read-token-smoke-0123456789abcdef'


class _Resp:
    def __init__(self, r):
        self.status_code, self.headers, self._r = r.status_code, r.headers, r

    def json(self):
        return self._r.get_json()


class _Shim:
    """Adapta el cliente de pruebas de Flask a la interfaz de requests.Session."""
    def __init__(self, client, base):
        self.c, self.base, self.calls = client, base, []

    def _path(self, url):
        return url[len(self.base):] if url.startswith(self.base) else url

    def post(self, url, data=None, headers=None, timeout=None):  # noqa: ARG002
        msg = json.loads(data)
        if msg.get('method') == 'tools/call':
            self.calls.append(msg['params']['name'])
        r = self.c.post(self._path(url), data=data, headers=headers)
        return _Resp(r)

    def delete(self, url, headers=None, timeout=None):  # noqa: ARG002
        return self.c.delete(self._path(url), headers=headers)


@pytest.fixture
def mcp_client(monkeypatch):
    from flask import Flask
    import ontology.db as odb
    from core import http as _h
    from core import world as W
    from mcp_server import api as _api
    from mcp_server import auth as _a
    from mcp_server.api import mcp_bp
    for k in ('MCP_ENABLED', 'MCP_ALLOWED_ORIGINS', 'MCP_ALLOWED_HOSTS', 'MCP_RATE_PER_MIN', 'MCP_PUBLIC_URL'):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(odb, 'DATABASE_URL', '')
    monkeypatch.setenv('MCP_STATIC_TOKEN', STATIC)
    monkeypatch.setattr(W, '_http_get_json', lambda *a, **k: (None, 'timeout'))   # sin red
    _h._rate_buckets.clear(); _a._INFLIGHT['total'] = 0; _a._INFLIGHT['by'].clear()
    _api._SESSIONS.clear(); _api._CLOSED.clear()
    a = Flask('smoke-test'); a.config['TESTING'] = True; a.register_blueprint(mcp_bp)
    return a.test_client()


def test_o1_smoke_contra_mcp_real_en_proceso(mcp_client):
    from scripts.smoke_mcp import smoke, SMOKE, DENY
    base = 'http://localhost'
    shim = _Shim(mcp_client, base)
    out = smoke(base, STATIC, http=shim)
    st = {r['name']: r['status'] for r in out['results']}
    for name in ('initialize', 'tools/list', 'search_companies', 'get_company', 'get_supply_chain',
                 'get_research_health', 'get_world_events'):
        assert st[name] == 'ok', (name, out['results'])
    # sin base: las herramientas de la ontología avisan, no fallan
    assert st['get_track_record'] == 'warn' and st['get_conclusions_board'] == 'warn'
    assert out['ok'] is True
    assert not (set(shim.calls) & DENY), 'el humo jamás llama herramientas con poder'
    assert set(shim.calls) == {n for n, _a, _m in SMOKE}


def test_o1_smoke_se_niega_si_el_token_ve_trading():
    from scripts.smoke_mcp import smoke, SmokeConfigError

    class R:
        def __init__(self, body, headers=None):
            self.status_code, self._b, self.headers = 200, body, headers or {}

        def json(self):
            return self._b

    class Fake:
        calls = []

        def post(self, url, data=None, headers=None, timeout=None):  # noqa: ARG002
            m = json.loads(data)
            self.calls.append(m['method'])
            if m['method'] == 'initialize':
                return R({'jsonrpc': '2.0', 'id': 1, 'result': {'serverInfo': {'name': 'x'}}}, {'Mcp-Session-Id': 's'})
            if m['method'] == 'tools/list':
                return R({'jsonrpc': '2.0', 'id': 2, 'result': {'tools': [
                    {'name': 'search_companies', 'annotations': {'readOnlyHint': True}},
                    {'name': 'preview_order', 'annotations': {'readOnlyHint': False}}]}})
            r = R(None); r.status_code = 202
            return r

        def delete(self, *a, **k):
            return R(None)
    f = Fake()
    with pytest.raises(SmokeConfigError, match='SOLO lectura'):
        smoke('http://x', 'kmcp_' + 'a' * 30, http=f)
    assert 'tools/call' not in f.calls


def test_o1_smoke_sin_token_es_error_de_configuracion(monkeypatch, capsys):
    from scripts import smoke_mcp
    monkeypatch.delenv('KHIPU_MCP_TOKEN', raising=False)
    assert smoke_mcp.main(['--url', 'http://127.0.0.1:9']) == 2
    assert 'KHIPU_MCP_TOKEN' in capsys.readouterr().err


def test_o1_chequeo_solo_llama_herramientas_de_lectura():
    from core import ops_check as O
    ok, detail = O._mcp_tool('preview_order', {}, ())()
    assert ok is False and 'LECTURA' in detail
    ok, detail = O._mcp_tool('run_research', {}, ())()
    assert ok is False
    assert {n for n, _a, _m in O.SMOKE_TOOLS} == {n for n, _a, _m in __import__('scripts.smoke_mcp', fromlist=['x']).SMOKE}


def test_o1_cadencia_arranque_luego_diaria(monkeypatch):
    from core import ops_check as O
    runs = []
    monkeypatch.setattr(O, 'run_checks', lambda kind='manual', persist=True: runs.append(kind) or {'ok': True})
    O._LAST.update(data=None, ts=0.0, boot_done=False)
    assert O.scheduled() is True and runs == ['boot']
    O._LAST['ts'] = __import__('time').time()
    assert O.scheduled() == 'skip'
    O._LAST['ts'] -= O.DAILY_S + 1
    assert O.scheduled() is True and runs == ['boot', 'daily']


@pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL')
def test_o1_chequeo_se_guarda_y_se_consulta(monkeypatch):
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    from core import ops_check as O
    from core import world as W
    import mcp_server.models  # noqa: F401
    import research.models  # noqa: F401
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    monkeypatch.setattr(W, '_http_get_json', lambda *a, **k: (None, 'timeout'))
    try:
        r1 = O.run_checks('manual')
        assert r1['saved'] is True and r1['version']
        names = {c['name'] for c in r1['checks']}
        assert {'base_de_datos', 'catalogo', 'grafo_vs_catalogo', 'mcp:get_company'} <= names
        assert next(c for c in r1['checks'] if c['name'] == 'base_de_datos')['status'] == 'ok'
        last = O.last_check()
        assert last['last']['started_at'] == r1['started_at'] and last['history'][0]['ok'] == r1['ok']
        # API: lectura libre; correrlo a mano exige PIN de operador
        import server
        from core import pin
        pin._reset_for_tests()
        monkeypatch.setenv('TRADE_PIN', 'pin-ops-9876')
        c = server.app.test_client()
        g = c.get('/api/ops/last_check')
        assert g.status_code == 200 and g.get_json()['last']
        assert c.post('/api/ops/check').status_code == 401
    finally:
        Base.metadata.drop_all(engine)
