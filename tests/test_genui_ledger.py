"""tests/test_genui_ledger.py — la interfaz generativa en el LIBRO (docs/CHAT_UI_GENERATIVA.md §5.7, F1 paso 14).

Sin base: genui.build@1 está retenido en core/impls (STAMPS, catálogo, salida dorada); el armado es DETERMINISTA
(mismas entradas → mismo sobre, misma huella); las entradas que se guardan NO llevan el mensaje del usuario.
Con base (DATABASE_URL): en `shadow` la decisión chat.answer lleva el blob `ui_blocks` (90 días) + `ui_sha`, las
entradas del cálculo (`ui_inputs`) y el impl `ui: genui.build@1`; el replay rehace el sobre y lo da por igual, y si
el código cambiara sin nacer @2 lo delata (`differs`).
"""
import hashlib
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

from core import genui  # noqa: E402

SECRET = 'mi cartera privada tiene 48.250 USD en Calle Falsa 123'
GOLDEN_INPUTS = os.path.join(ROOT, 'tests', 'fixtures', 'genui', 'golden_inputs.json')


def _canon(obj):
    from core.decisions import canonical
    return canonical(obj)


# ── sin base ─────────────────────────────────────────────────────────────────────────────────────────────────────
def test_impl_retenido():
    from core import impls
    assert genui.IMPL == 'genui.build@1' and genui.IMPL in impls.STAMPS
    i = impls.resolve_stamp(genui.IMPL)
    assert (i.key, i.version, i.module, i.attr) == ('genui.build', 1, 'core.genui', 'rebuild')
    assert 'genui.build' in impls.GOLDEN_CASES
    assert impls.missing_for({'impl': {'ui': genui.IMPL, 'decisions': 'record@1'}}) == []
    assert os.path.exists(os.path.join(ROOT, 'tests', 'golden', 'impl_genui.build@1.json'))


def test_rearmado_determinista():
    with open(GOLDEN_INPUTS, encoding='utf-8') as fh:
        cases = json.load(fh)['cases']
    for c in cases:
        a = genui.public(genui.rebuild(c))
        b = genui.public(genui.rebuild(json.loads(json.dumps(c))))
        assert hashlib.sha256(_canon(a)).hexdigest() == hashlib.sha256(_canon(b)).hexdigest()


def test_entradas_sin_el_mensaje_del_usuario():
    with open(os.path.join(ROOT, 'tests', 'fixtures', 'genui', 'tools', 'get_company__nvidia.json'),
              encoding='utf-8') as fh:
        d = json.load(fh)
    calls = [('get_company', {'id_or_ticker': SECRET}, True, d['result']), ('web_search', {'query': SECRET}, True,
                                                                              {'results': [], 'q': 'x'})]
    env, _ = genui.build_ui(SECRET + ' ¿cómo va Nvidia?', calls, [{'id': 'Nvidia', 'label': 'Nvidia'}], None, 'es',
                            {'answer': 'Nvidia va bien.'})
    raw = json.dumps(env['_inputs'], ensure_ascii=False)
    assert 'Calle Falsa' not in raw and '48.250' not in raw
    assert env['_inputs']['intent'] == 'price'
    assert env['_inputs']['calls'][1][3] is None            # resultados sin constructor no se guardan


# ── con base ─────────────────────────────────────────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')


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


@pytest.fixture
def chat(monkeypatch, db):
    from flask import Flask

    from core import ai as core_ai
    from core import khipu_chat as kc
    from mcp_server import tools as mt
    monkeypatch.setattr(mt, '_live_profile', lambda sym: {'available': False, 'reason': 'test (offline)'})
    monkeypatch.setattr(mt._auth, 'db_available', lambda: False)
    monkeypatch.setattr(core_ai, '_ai_configured', lambda: True)
    import core.live_facts as lf
    monkeypatch.setattr(lf, 'live_facts_block', lambda *a, **k: '')
    app = Flask('genui-ledger-test')
    app.register_blueprint(kc.khipu_chat_bp)
    from core import http as h
    with h._rate_lock:
        h._rate_buckets.clear()

    def ask(mode, req_id):
        script = [json.dumps({'tool': 'run_scenario', 'args': {'shocks': [{'id': 'TSMC'}]}}),
                  json.dumps({'final': {'answer': 'Si TSMC cae, el golpe llega lejos [F2].', 'actions': []}})]
        monkeypatch.setattr(core_ai, '_cascade', lambda *a, **k: (script.pop(0), 'claude-haiku-4-5'))
        monkeypatch.setenv('GENUI', mode)
        r = app.test_client().post('/api/khipu/chat', json={
            'message': SECRET + ' ¿qué pasa si cae TSMC?', 'lang': 'es', 'req_id': req_id, 'context': {'genui': 1}})
        assert r.status_code == 200, r.get_json()
        _flush()
        return r.get_json()
    return ask


def _dec(req_id):
    from sqlalchemy import text
    from ontology.db import session_scope
    with session_scope() as s:
        r = s.execute(text("SELECT id, manifest FROM decisions WHERE kind = 'chat.answer' AND correlation_id = :c"),
                      {'c': req_id}).first()
    return str(r[0]), r[1]


def _blob(sha):
    import zlib
    from sqlalchemy import text
    from ontology.db import session_scope
    with session_scope() as s:
        r = s.execute(text('SELECT body, retention_class FROM decision_blobs WHERE sha256 = :s'), {'s': sha}).first()
    return json.loads(zlib.decompress(bytes(r[0]))), r[1]


@needs_db
def test_shadow_queda_en_el_libro_y_el_replay_lo_repite(chat, monkeypatch):
    out = chat('shadow', 'req-genui-0001')
    assert 'ui' not in out
    did, m = _dec('req-genui-0001')
    assert m['impl']['ui'] == 'genui.build@1'
    assert m['ui']['mode'] == 'shadow' and m['ui']['sent'] is False and m['ui']['n_blocks'] >= 3
    assert m['ui_sha'] == m['ui_blocks']
    env, ret = _blob(m['ui_blocks'])
    assert ret == 'standard_90d' and env['v'] == 'kblocks/1'
    assert hashlib.sha256(_canon(env)).hexdigest() == m['ui_sha']
    assert 'impact.cascade' in [b['type'] for b in env['blocks']]
    inputs, ret2 = _blob(m['ui']['replay_blob'])
    assert ret2 == 'standard_90d' and 'Calle Falsa' not in json.dumps(inputs, ensure_ascii=False)
    from core import replay
    rep = replay.replay(did, record=False, use_cache=False)
    st = {s['name']: s for s in rep['steps']}
    assert st['ui_blocks']['ok'] is True and rep['verdict'] != 'differs'
    assert st['impl']['ok'] is True                          # genui.build@1 retenido: nada «perdido»
    # si el código del armado cambiara SIN nacer @2, el replay lo delata
    real = genui.build_core

    def otro(inp):
        env2, info = real(inp)
        env2['blocks'] = env2['blocks'][:-1]
        return env2, info
    monkeypatch.setattr(genui, 'build_core', otro)
    rep2 = replay.replay(did, record=False, use_cache=False)
    st2 = {s['name']: s for s in rep2['steps']}
    assert st2['ui_blocks']['ok'] is False and rep2['verdict'] == 'differs' and st2['ui_blocks']['diffs']


@needs_db
def test_on_envia_y_registra_lo_mismo(chat):
    out = chat('on', 'req-genui-0002')
    _did, m = _dec('req-genui-0002')
    assert m['ui']['mode'] == 'on' and m['ui']['sent'] is True
    env, _ = _blob(m['ui_blocks'])
    assert env == out['ui']                                  # lo que vio el usuario = lo que quedó en el libro


@needs_db
def test_off_no_deja_nada_de_ui(chat):
    chat('off', 'req-genui-0003')
    _did, m = _dec('req-genui-0003')
    assert 'ui' not in m and 'ui_blocks' not in m and 'ui' not in (m.get('impl') or {})


@needs_db
def test_camino_real_sin_texto_libre_y_cartera_del_servidor(chat, monkeypatch):
    """Revisión F2: por _genui_attach (no build_ui directo) una búsqueda web con la pregunta copiada NO queda en los
    blobs, y run_scenario recibe la cartera del NAVEGADOR (usd validado), nunca la que escribió el modelo."""
    from flask import Flask

    from core import ai as core_ai
    from core import khipu_chat as kc
    script = [json.dumps({'tool': 'web_search', 'args': {'query': SECRET}}),
              json.dumps({'tool': 'run_scenario', 'args': {'shocks': [{'id': 'TSMC'}],
                                                           'positions': [{'symbol': 'NVDA', 'usd': 12345}]}}),
              json.dumps({'final': {'answer': 'Si TSMC cae, el golpe llega lejos.', 'actions': []}})]
    monkeypatch.setattr(core_ai, '_cascade', lambda *a, **k: (script.pop(0) if script else script_final(), 'claude-haiku-4-5'))

    def script_final():
        return json.dumps({'final': {'answer': 'listo', 'actions': []}})
    monkeypatch.setenv('GENUI', 'shadow')
    app = Flask('genui-ledger-test-2')
    app.register_blueprint(kc.khipu_chat_bp)
    r = app.test_client().post('/api/khipu/chat', json={
        'message': SECRET + ' ¿qué pasa si cae TSMC?', 'lang': 'es', 'req_id': 'req-genui-0004',
        'context': {'genui': 1, 'portfolio': {'positions': [{'symbol': 'NVDA', 'shares': 10, 'usd': 1800.5}]}}})
    assert r.status_code == 200, r.get_json()
    _flush()
    _did, m = _dec('req-genui-0004')
    inputs, _ = _blob(m['ui']['replay_blob'])
    env, _ = _blob(m['ui_blocks'])
    raw = json.dumps(inputs, ensure_ascii=False) + json.dumps(env, ensure_ascii=False)
    assert 'Calle Falsa' not in raw and '48.250' not in raw
    rs = [c for c in inputs['calls'] if c[0] == 'run_scenario']
    assert rs and rs[0][3]['portfolio']['positions'][0]['usd'] == 1800.5          # el valor del navegador
    assert '12345' not in json.dumps(rs[0][3])                                      # nunca el del modelo
