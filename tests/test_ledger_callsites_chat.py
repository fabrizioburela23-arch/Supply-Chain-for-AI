"""tests/test_ledger_callsites_chat.py — INFRA_OPERATIVA §2.5, paso 20: decisiones ASYNC de chat, Jev, MCP,
qué-pasaría-si e insights (la parte de dinero/comité/investigación vive en tests/test_ledger_callsites.py).

Cada una se ENCOLA al responder (0 ms para el usuario) y la escribe el hilo del libro (core/decisions.submit_async):
  · chat.answer: principal de la petición, mensaje SOLO como HMAC, fuentes con as_of, herramientas con la huella de
    sus argumentos, agentes, modelo, ruta y las llamadas de IA de esa pregunta (refs ai_call ↔ ai_calls.decision_id);
  · chat.route (Jev): ruta + probabilidades + política policy.decide + modelo; outcome 'agree'; la clave de la sombra
    (decision_shadow.key) es un HMAC, nunca el texto;
  · mcp.tool_call: principal mcp:<token_id>, herramienta, huella de los argumentos y del RESULTADO (nunca el resultado
    ni los valores de los argumentos);
  · whatif.shock / whatif.factor_fire: request_params, generación usada, top-50 + content_sha;
  · insight.snapshot: una por fila nueva del historial, con las llamadas de IA que la narraron.
"""
import json
import os
import sys
import zlib

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

DATABASE_URL = os.getenv('DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
SECRET = 'mi cartera privada tiene 48.250 USD en Calle Falsa 123'
PIN = '4321'


@pytest.fixture(scope='module')
def db():
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    import mcp_server.models  # noqa: F401
    import research.models  # noqa: F401
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    yield
    Base.metadata.drop_all(engine)


def _flush():
    from core import ai_calls, decisions
    decisions.flush_async(timeout=10)
    ai_calls.flush()


def _decs(kind):
    from sqlalchemy import text
    from ontology.db import session_scope
    with session_scope() as s:
        rows = s.execute(text('SELECT id, kind, status, durability, principal_id, principal_kind, channel, subject, '
                              'manifest, output, model, correlation_id FROM decisions WHERE kind = :k ORDER BY seq'),
                         {'k': kind}).all()
    return [dict(r._mapping) for r in rows]


def _everything_of(did):
    """Todo lo que el libro guardó de UNA decisión (filas + blobs descomprimidos), como texto."""
    from sqlalchemy import text
    from ontology.db import session_scope
    with session_scope() as s:
        d = s.execute(text('SELECT to_jsonb(d) FROM decisions d WHERE id = :i'), {'i': str(did)}).scalar()
        refs = s.execute(text('SELECT to_jsonb(r) FROM decision_refs r WHERE decision_id = :i'), {'i': str(did)}).all()
        outs = s.execute(text('SELECT to_jsonb(o) FROM decision_outcomes o WHERE decision_id = :i'),
                         {'i': str(did)}).all()
        shas = {x for x in json.dumps(d).split('"') if len(x) == 64 and all(c in '0123456789abcdef' for c in x)}
        blobs = [zlib.decompress(bytes(b[0])).decode() for b in s.execute(
            text('SELECT body FROM decision_blobs WHERE sha256 = ANY(:s)'), {'s': list(shas)}) if b[0] is not None]
    return json.dumps(d) + json.dumps([r[0] for r in refs]) + json.dumps([o[0] for o in outs]) + ''.join(blobs)


# ── chat.answer ──────────────────────────────────────────────────────────────
@pytest.fixture
def chat_app(monkeypatch, db):
    from flask import Flask

    from core import ai as core_ai
    from core import khipu_chat as kc
    from mcp_server import tools as mt
    monkeypatch.setattr(mt, '_live_profile', lambda sym: {'available': False, 'reason': 'test (offline)'})
    monkeypatch.setattr(mt._auth, 'db_available', lambda: False)
    monkeypatch.setattr(core_ai, '_ai_configured', lambda: True)
    script = [json.dumps({'tool': 'search_companies', 'args': {'query': 'TSMC'}}),
              json.dumps({'final': {'answer': 'TSMC fabrica los chips de Nvidia [F1].', 'actions': []}})]
    monkeypatch.setattr(core_ai, '_cascade', lambda *a, **k: (script.pop(0), 'claude-haiku-4-5'))
    import core.live_facts as lf
    monkeypatch.setattr(lf, 'live_facts_block', lambda *a, **k: '')
    app = Flask('chat-ledger-test')
    app.register_blueprint(kc.khipu_chat_bp)
    from core import http as h
    with h._rate_lock:
        h._rate_buckets.clear()
    return app.test_client()


def test_chat_answer_queda_async_con_hmac_fuentes_y_llamadas_de_ia(chat_app):
    msg = SECRET + ' ¿quién fabrica los chips de Nvidia?'
    r = chat_app.post('/api/khipu/chat', json={'message': msg,
                                               'lang': 'es', 'req_id': 'req-chat-0001'},
                      headers={'X-Khipu-Owner': 'owner-abc-777'})
    assert r.status_code == 200, r.get_json()
    out = r.get_json()
    assert out['answer'].startswith('TSMC') and out['answer_source'] == 'ai'
    _flush()
    decs = _decs('chat.answer')
    assert len(decs) == 1
    d = decs[0]
    assert d['durability'] == 'async' and d['status'] == 'answered' and d['channel'] == 'chat'
    assert d['principal_id'] == 'ui:anon' and d['correlation_id'] == 'req-chat-0001'
    m = d['manifest']
    assert m['privacy']['message']['hmac'] and m['privacy']['message']['len'] == len(msg)
    names = [t['name'] for t in m['tools']]          # (la ficha pre-consultada de Nvidia va antes)
    assert 'search_companies' in names and all(t['args_sha'] for t in m['tools'])
    assert m['facts']['cited'] == [1]
    assert d['output']['answer_source'] == 'ai' and d['output']['n_ai_calls'] == 2
    assert len(d['model']['ai_call_ids']) == 2
    from sqlalchemy import text
    from ontology.db import session_scope
    with session_scope() as s:
        n = s.execute(text('SELECT count(*) FROM ai_calls WHERE decision_id = :i'), {'i': str(d['id'])}).scalar()
        blob = s.execute(text('SELECT retention_class FROM decision_blobs WHERE sha256 = :b'),
                         {'b': m['answer_blob']}).scalar()
    assert n == 2 and blob == 'standard_90d'
    everything = _everything_of(d['id'])
    assert 'Calle Falsa' not in everything and '48.250' not in everything and 'owner-abc-777' not in everything


def test_chat_sin_base_no_encola_nada(monkeypatch):
    import ontology.db as odb
    from core import decisions
    monkeypatch.setattr(odb, 'DATABASE_URL', '')
    assert decisions.submit_async(lambda: None) is False


# ── chat.route (Jev) ─────────────────────────────────────────────────────────
def test_chat_route_con_hmac_politica_y_acuerdo(db, monkeypatch):
    from sqlalchemy import text

    from core import decide
    from ontology.db import session_scope
    monkeypatch.setenv('TYPESAFE_API_KEY', 'ts-test')
    ans = {'route': {'choice': 'needs_tools', 'confidence': 0.82,
                     'probabilities': {'needs_tools': 0.82, 'local_fact': 0.1, 'needs_deep_reasoning': 0.08}},
           'asks_trade': {'noul': 0.01}}
    out = {'steps': 2, 'tools_used': [{'name': 'get_news'}], 'answer_source': 'ai', 'router': {'by': 'jev'}}
    dec = decide._compare(ans, out, SECRET, correlation_id='req-route-01')
    assert dec['route'] == 'needs_tools'
    import time
    time.sleep(0.3)                    # la sombra se guarda en el pool de decide
    _flush()
    with session_scope() as s:
        keys = [r[0] for r in s.execute(text('SELECT key FROM decision_shadow'))]
    assert keys and all(k.startswith('hmac:') and 'Calle' not in k for k in keys)
    d = _decs('chat.route')[-1]
    assert d['correlation_id'] == 'req-route-01' and d['principal_id'] == 'system:chat_gate'
    assert d['manifest']['jev']['probabilities']['needs_tools'] == 0.82
    assert d['output']['agree'] is True and d['model']['model'] == decide.MODEL
    with session_scope() as s:
        oc = s.execute(text("SELECT outcome_kind, result FROM decision_outcomes WHERE decision_id = :i"),
                       {'i': str(d['id'])}).all()
        pol = s.execute(text("SELECT ref_id FROM decision_refs WHERE decision_id = :i AND role = 'policy'"),
                        {'i': str(d['id'])}).all()
    assert oc and oc[0][0] == 'agree' and oc[0][1]['agree'] is True
    assert pol and pol[0][0].startswith('policy.decide@')
    assert 'Calle Falsa' not in _everything_of(d['id'])


# ── mcp.tool_call ────────────────────────────────────────────────────────────
@pytest.fixture
def mcp_client(monkeypatch, db):
    from flask import Flask

    from core import http as _h
    from mcp_server import api as _api
    from mcp_server import auth as _a
    from mcp_server import tools as mt
    monkeypatch.setenv('TRADE_PIN', PIN)
    for k in ('MCP_ENABLED', 'MCP_ALLOWED_ORIGINS', 'MCP_STATIC_TOKEN', 'MCP_ALLOWED_HOSTS'):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(mt, '_live_profile', lambda sym: {'available': False, 'reason': 'test (offline)'})
    _h._rate_buckets.clear()
    _a.reset_pin_guard()
    _api._SESSIONS.clear()
    a = Flask('mcp-ledger-test')
    a.config['TESTING'] = True
    a.register_blueprint(_api.mcp_bp)
    return a.test_client()


def test_mcp_tool_call_con_huellas_y_sin_resultado(mcp_client):
    r = mcp_client.post('/api/mcp/tokens', headers={'X-Trade-Pin': PIN, 'Content-Type': 'application/json'},
                        data=json.dumps({'name': 'agente de prueba', 'scopes': ['read']}))
    assert r.status_code == 201, r.get_json()
    tok = r.get_json()
    msg = {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call',
           'params': {'name': 'search_companies', 'arguments': {'query': 'consulta-privada-xyz TSMC'}}}
    r = mcp_client.post('/mcp', data=json.dumps(msg), headers={
        'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
        'Authorization': f"Bearer {tok['token']}"})
    assert r.status_code == 200, r.get_data(as_text=True)
    result = r.get_json()['result']
    _flush()
    d = _decs('mcp.tool_call')[-1]
    assert d['principal_id'] == f"mcp:{tok['id']}" and d['principal_kind'] == 'external_ai' and d['channel'] == 'mcp'
    assert d['subject']['tool'] == 'search_companies' and d['subject']['scope'] == 'read'
    from core.decisions import canonical, sha256_hex
    assert d['output']['result_sha'] == sha256_hex(canonical(result)) and d['status'] == 'executed'
    assert d['manifest']['tool_call']['arg_keys'] == ['query']
    everything = _everything_of(d['id'])
    assert 'consulta-privada-xyz' not in everything
    assert json.dumps(result.get('structuredContent') or {})[:200] not in everything


def test_mcp_tool_call_con_error_guarda_solo_el_codigo(mcp_client):
    """Revisión §2.7: el mensaje de un ToolError repite el argumento ('entity not found …: "<texto>"') → la ficha
    guarda solo el CÓDIGO del error y la huella de los argumentos es con CLAVE (pii_hmac), nunca un sha sin clave."""
    r = mcp_client.post('/api/mcp/tokens', headers={'X-Trade-Pin': PIN, 'Content-Type': 'application/json'},
                        data=json.dumps({'name': 'agente error', 'scopes': ['read']}))
    tok = r.get_json()
    msg = {'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call',
           'params': {'name': 'get_company', 'arguments': {'id_or_ticker': 'mi nota privada zqxw'}}}
    r = mcp_client.post('/mcp', data=json.dumps(msg), headers={
        'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
        'Authorization': f"Bearer {tok['token']}"})
    assert r.status_code == 200 and r.get_json()['result']['isError'] is True
    _flush()
    d = [x for x in _decs('mcp.tool_call') if x['subject']['tool'] == 'get_company'][-1]
    assert d['output']['error_code'] == 'not_found' and 'error' not in d['output'] and d['status'] == 'failed'
    tc = d['manifest']['tool_call']
    assert 'args_sha' not in tc and tc['args_hmac']['key_id'] and len(tc['args_hmac']['hmac']) == 64
    assert 'zqxw' not in _everything_of(d['id'])


# ── qué-pasaría-si e insights ────────────────────────────────────────────────
def test_whatif_desde_hot_scenario_y_factor_fire(db, monkeypatch):
    import ontology.db as odb
    import server
    from core.hotviews import builder, registry
    real = odb.ontology_available
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    registry.reset()
    builder.build_once()                         # vistas del snapshot (la base de la prueba está vacía)
    monkeypatch.setattr(odb, 'ontology_available', real)
    from core import http as h
    with h._rate_lock:
        h._rate_buckets.clear()
    c = server.app.test_client()
    r = c.post('/api/hot/scenario', json={'shocks': [{'id': 'TSMC', 'magnitude': 1}, 'Nvidia'], 'max_hops': 4})
    assert r.status_code == 200, r.get_json()
    gen = r.get_json()['view']['generation']
    _flush()
    d = _decs('whatif.shock')[-1]
    rp = d['manifest']['request_params']
    assert rp['endpoint'] == '/api/hot/scenario' and rp['max_hops'] == 4 and set(rp['shock']) == {'TSMC', 'Nvidia'}
    assert d['output']['generation'] == gen and len(d['output']['content_sha']) == 64
    assert 0 < len(d['output']['top']) <= 50 and d['durability'] == 'async'
    assert any(v['name'] == 'impact' and v['version'] == gen for v in d['manifest']['views'])
    registry.reset()


def test_ledger_whatif_factor_fire_y_insight(db):
    import uuid

    from flask import Flask

    from matrix import api as mapi
    app = Flask('whatif-test')
    with app.test_request_context(headers={'X-Khipu-Channel': 'terminal'}):
        assert mapi.ledger_whatif('whatif.factor_fire', {'factor_id': 'f_taiwan', 'members': ['TSMC'],
                                                         'severity_crisis': 8.0, 'damping': 0.6},
                                  {'TSMC': 80.0, 'Nvidia': 41.5, 'AMD': 12.0}, None, {'rho_crisis': 0.9})
    did, ids = uuid.uuid4(), ['00000000-0000-0000-0000-0000000000aa']
    assert mapi.ledger_insight(77, 'g12.rabc', 'es', {'trigger': 'factor X', 'affected': 3, 'model': 'claude-x',
                                                      'insights': ['a']}, (did, ids))
    _flush()
    d = _decs('whatif.factor_fire')[-1]
    assert d['subject']['factor_id'] == 'f_taiwan' and d['manifest']['request_params']['severity_crisis'] == 8.0
    assert d['output']['top'][0] == ['TSMC', 80.0] and d['output']['rho_crisis'] == 0.9 and d['channel'] == 'terminal'
    i = _decs('insight.snapshot')[-1]
    assert str(i['id']) == str(did) and i['output']['snapshot_id'] == 77 and i['model']['ai_call_ids'] == ids


def test_insight_repetido_igual_escribe_la_ficha_que_su_ia_ya_cito(db):
    """Revisión paso 21: una narración con IA sobre una versión del grafo YA narrada no deja fila nueva de historial,
    pero sus filas de ai_calls ya citan el id reservado → la ficha insight.snapshot se escribe igual
    (output.persisted=false, apuntando a la fila vigente). Sin IA (sin ids) no se escribe nada extra."""
    import uuid

    from sqlalchemy import text

    from matrix import api as mapi
    from ontology.db import session_scope
    payload = {'trigger': 'factor Y', 'affected': 4, 'model': 'claude-x', 'insights': ['b'], 'situation': {}}
    d1, d2, d3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    gk = 'g-dup-test.r1'
    mapi._persist_insight(session_scope, gk, None, 'es', payload, ledger=(d1, ['00000000-0000-0000-0000-0000000000b1']))
    mapi._persist_insight(session_scope, gk, None, 'es', payload, ledger=(d2, ['00000000-0000-0000-0000-0000000000b2']))
    mapi._persist_insight(session_scope, gk, None, 'es', payload, ledger=(d3, []))
    _flush()
    with session_scope() as s:
        rows = {str(r.id): dict(r._mapping) for r in s.execute(text(
            "SELECT id, output FROM decisions WHERE kind = 'insight.snapshot' AND id IN (:a, :b, :c)"),
            {'a': str(d1), 'b': str(d2), 'c': str(d3)}).all()}
        n_hist = s.execute(text("SELECT count(*) FROM insight_snapshots WHERE graph_epoch = :g"), {'g': gk}).scalar()
    assert n_hist == 1
    assert rows[str(d1)]['output']['persisted'] is True
    assert rows[str(d2)]['output']['persisted'] is False
    assert rows[str(d2)]['output']['snapshot_id'] == rows[str(d1)]['output']['snapshot_id']
    assert str(d3) not in rows
