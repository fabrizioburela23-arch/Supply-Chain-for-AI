"""tests/test_voice_agent_split.py — lote I4 (Fase 2+): G5-05 server.py partido sin cambiar comportamiento.

  1. La voz (/api/voice/*) vive en core/voice_api.py y el agente de trading (/api/trade/agent/*) en
     core/trading_agent.py: las MISMAS rutas con los MISMOS métodos siguen en la app, server.py ya no las define y
     re-exporta los nombres que leen el 🩺 y las pruebas (mismo objeto, no copias). server.py < 5.000 líneas.
  2. La config sigue siendo del servidor y se lee EN CADA LLAMADA (un cambio sobre `server` se ve en el módulo).
  3. Las tres rutas que cambian el agente de ElevenLabs dejan policy.change voice.agent ANTES de llamarlo (nunca la
     clave); si ElevenLabs falla queda un decision_outcomes 'error'; con el libro caído no se toca ElevenLabs (503);
     sin base todo sigue como antes.

Sin red: ElevenLabs falso. Las de base se saltan sin DATABASE_URL.
"""
import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

import requests  # noqa: E402

import server  # noqa: E402
from core import trading_agent, voice_api  # noqa: E402

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
PIN = '4321-split-pin'
KEY = 'sk_el_SPLIT_KEY_NEVER_IN_LEDGER_777'
AGENT = 'agent_01splitkhipu'
H = {'X-Trade-Pin': PIN, 'Content-Type': 'application/json'}

VOICE_ROUTES = {
    ('/api/voice/agent-diag', 'GET'), ('/api/voice/voices', 'GET'), ('/api/voice/adopt', 'POST'),
    ('/api/voice/agent-tune', 'POST'), ('/api/voice/sync-agent', 'GET'), ('/api/voice/sync-agent', 'POST'),
    ('/api/voice/bixby-prompt', 'GET'), ('/api/voice/session', 'POST'), ('/api/voice/tour/<lang>/<int:step>', 'GET'),
}
AGENT_ROUTES = {('/api/trade/agent/start', 'POST'), ('/api/trade/agent/stop', 'POST'),
                ('/api/trade/agent/status', 'GET'), ('/api/trade/agent/config', 'POST')}


def _src(p):
    with open(os.path.join(ROOT, p), encoding='utf-8') as f:
        return f.read()


# ── 1. estructura ─────────────────────────────────────────────────────────────────────────────────────────────────
def test_rutas_siguen_en_la_app_con_sus_metodos_y_su_modulo():
    have = {}
    for r in server.app.url_map.iter_rules():
        for m in (r.methods or set()) - {'HEAD', 'OPTIONS'}:
            have[(r.rule, m)] = server.app.view_functions[r.endpoint]
    for rule, m in VOICE_ROUTES:
        assert (rule, m) in have, (rule, m)
        assert have[(rule, m)].__module__ == 'core.voice_api', rule
    for rule, m in AGENT_ROUTES:
        assert (rule, m) in have, (rule, m)
        assert have[(rule, m)].__module__ == 'core.trading_agent', rule


def test_server_ya_no_las_define_y_reexporta_los_mismos_objetos():
    src = _src('server.py')
    assert "@app.route('/api/voice/" not in src and "@app.route('/api/trade/agent/" not in src
    assert 'BIXBY_SYSTEM_PROMPT = """' not in src and 'def _agent_run_cycle' not in src
    assert src.count('\n') < 5000, 'G5-05: server.py debe quedar por debajo de ~5.000 líneas'
    for name in ('BIXBY_SYSTEM_PROMPT', 'RETIRED_VOICE_TOOLS', 'VOICE_SCREENS', '_TOUR_AUDIO', '_bixby_client_tools',
                 'voice_agent_diag'):
        assert getattr(server, name) is getattr(voice_api, name), name
    for name in ('_AGENT', '_AGENT_RESTORE', '_TRADABLE_CACHE', '_AgentOrderError', '_agent_run_cycle'):
        assert getattr(server, name) is getattr(trading_agent, name), name
    assert voice_api._S is server and trading_agent._S is server


def test_el_agente_sigue_sin_hablar_con_alpaca_directo():
    # solo brokerage/alpaca.py hace POST/DELETE a /v2/orders|positions (tests/test_order_single_path.py lo escanea);
    # el módulo nuevo tampoco
    src = _src('core/trading_agent.py')
    assert not re.search(r"requests\.(post|delete)\(", src)
    assert 'house_order' in src or 'service' in src


def test_la_config_se_lee_en_cada_llamada(monkeypatch):
    c = server.app.test_client()
    monkeypatch.setattr(server, 'ELEVENLABS_KEY', '')
    r = c.post('/api/voice/session', json={})
    assert r.status_code == 400 and r.get_json()['code'] == 'not_configured'
    monkeypatch.setattr(server, 'ELEVENLABS_KEY', KEY)
    monkeypatch.setattr(server, 'ELEVENLABS_AGENT_ID', '')
    r = c.post('/api/voice/session', json={})
    assert r.status_code == 400 and r.get_json()['code'] == 'agent_missing'


# ── 3. decisiones de la voz ───────────────────────────────────────────────────────────────────────────────────────
class _R:
    def __init__(self, status, payload=None):
        self.status_code, self.ok, self._p = status, 200 <= status < 300, payload
        self.text = json.dumps(payload) if payload is not None else ''

    def json(self):
        return self._p


@pytest.fixture
def el(monkeypatch):
    calls = []

    def patch(url, json=None, headers=None, timeout=None, **_):  # noqa: A002
        calls.append(('PATCH', url, json))
        return _R(200, {'agent_id': AGENT})

    def post(url, json=None, headers=None, timeout=None, **_):  # noqa: A002
        calls.append(('POST', url, json))
        return _R(200, {'voice_id': 'v_new'})

    def get(url, **_):
        calls.append(('GET', url, None))
        raise requests.ConnectionError('sin red en la prueba')
    monkeypatch.setattr(requests, 'patch', patch)
    monkeypatch.setattr(requests, 'post', post)
    monkeypatch.setattr(requests, 'get', get)
    monkeypatch.setattr(server, 'ELEVENLABS_KEY', KEY)
    monkeypatch.setattr(server, 'ELEVENLABS_AGENT_ID', AGENT)
    monkeypatch.setenv('TRADE_PIN', PIN)
    monkeypatch.setenv('ELEVENLABS_ALLOW_OVERRIDE', '1')
    from core import http as h
    from core import pin as core_pin
    with h._rate_lock:
        h._rate_buckets.clear()
    core_pin._reset_for_tests()
    monkeypatch.setattr(voice_api, '_sync_bixby_agent',
                        lambda: {'ok': True, 'mode': 'tool_ids', 'tools_registered': 17, 'tools_expected': 17})
    return calls


def test_sin_base_las_rutas_de_la_voz_siguen_igual(el, monkeypatch):
    import ontology.db as odb
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    c = server.app.test_client()
    r = c.post('/api/voice/agent-tune', data=json.dumps({'tts_model': 'eleven_v4'}), headers=H)
    assert r.status_code == 200 and r.get_json()['ok'] and el[-1][0] == 'PATCH'
    assert c.post('/api/voice/sync-agent', headers=H).status_code == 200


@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    import brokerage.models  # noqa: F401
    import mcp_server.models  # noqa: F401
    import research.models  # noqa: F401
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    yield
    Base.metadata.drop_all(engine)


def _voice_decisions():
    from sqlalchemy import text
    from core import decision_sites, decisions
    from ontology.db import session_scope
    decision_sites.flush()
    decisions.flush_async(timeout=10)
    with session_scope() as s:
        rows = s.execute(text(
            "SELECT d.id, d.principal_id, d.subject, d.output, d.status, "
            "(SELECT o.result FROM decision_outcomes o WHERE o.decision_id = d.id AND o.outcome_kind = 'error' "
            " ORDER BY o.id DESC LIMIT 1) FROM decisions d WHERE d.kind = 'policy.change' "
            "AND d.subject @> CAST(:sub AS jsonb) ORDER BY d.seq"), {'sub': json.dumps({'policy': 'voice.agent'})}
        ).fetchall()
    return rows


@needs_db
def test_las_tres_rutas_dejan_policy_change_voice_agent_sin_la_clave(db, el):
    c = server.app.test_client()
    n0 = len(_voice_decisions())
    r = c.post('/api/voice/agent-tune', data=json.dumps({'tts_model': 'eleven_v4', 'language': 'ES'}), headers=H)
    assert r.status_code == 200, r.get_json()
    r = c.post('/api/voice/adopt', data=json.dumps({'public_owner_id': 'owner1', 'voice_id': 'v9',
                                                     'name': 'Khipu ES'}), headers=H)
    assert r.status_code == 200, r.get_json()
    r = c.post('/api/voice/sync-agent', headers=H)
    assert r.status_code == 200, r.get_json()
    rows = _voice_decisions()[n0:]
    assert [row[2]['action'] for row in rows] == ['tune', 'adopt', 'sync']
    tune, adopt, sync = rows
    assert tune[1] == 'op:fabrizio' and tune[3]['after'] == {'tts_model': 'eleven_v4', 'language': 'es'}
    assert tune[2]['agent_id'] == AGENT and tune[4] == 'executed'
    assert adopt[3]['after'] == {'public_owner_id': 'owner1', 'voice_id': 'v9', 'name': 'Khipu ES'}
    assert len(sync[3]['after']['prompt_sha']) == 64 and 'place_order' in sync[3]['after']['tools']
    for row in rows:
        assert row[5] is None, row                         # sin 'error' = ElevenLabs lo aplicó
        assert KEY not in json.dumps([str(x) for x in row], default=str)


@needs_db
def test_libro_caido_no_toca_elevenlabs(db, el, monkeypatch):
    from core import decision_sites
    from core.decisions import LedgerUnavailable

    def down(*_a, **_k):
        raise LedgerUnavailable('libro caído (prueba)')
    monkeypatch.setattr(decision_sites, 'policy_change', down)
    c = server.app.test_client()
    n = len(el)
    r = c.post('/api/voice/agent-tune', data=json.dumps({'tts_model': 'eleven_v4'}), headers=H)
    assert r.status_code == 503 and r.get_json()['code'] == 'ledger_unavailable'
    r = c.post('/api/voice/adopt', data=json.dumps({'public_owner_id': 'o', 'voice_id': 'v'}), headers=H)
    assert r.status_code == 503
    r = c.post('/api/voice/sync-agent', headers=H)
    assert r.status_code == 503
    assert len(el) == n, 'con el libro caído no se llama a ElevenLabs'


@needs_db
def test_un_fallo_de_elevenlabs_queda_como_resultado(db, el, monkeypatch):
    monkeypatch.setattr(requests, 'patch', lambda *a, **k: _R(401, {'detail': {'status': 'invalid_api_key'}}))
    c = server.app.test_client()
    n0 = len(_voice_decisions())
    r = c.post('/api/voice/agent-tune', data=json.dumps({'voice_id': 'v_abc'}), headers=H)
    assert r.status_code == 502
    rows = _voice_decisions()[n0:]
    assert len(rows) == 1 and rows[0][5]['ok'] is False and rows[0][5]['http'] == 401


@needs_db
def test_agent_tune_igual_a_la_cache_igual_deja_ficha(db, el, monkeypatch):
    """Revisión lote I: si la caché del agente (600 s) ya tenía esos valores, policy_change veía «sin cambio» y no
    escribía nada — pero el PATCH a ElevenLabs salía igual (y la caché pudo quedar vieja). Ahora: SIEMPRE una ficha."""
    import time
    from core import voice_agent as va
    monkeypatch.setitem(va._AGENT_CACHE, AGENT, (time.time(), {'conversation_config': {'tts': {'voice_id': 'V1'}}}))
    c = server.app.test_client()
    n0 = len(_voice_decisions())
    n_patch = sum(1 for x in el if x[0] == 'PATCH')
    r = c.post('/api/voice/agent-tune', data=json.dumps({'voice_id': 'V1'}), headers=H)
    assert r.status_code == 200, r.get_json()
    assert sum(1 for x in el if x[0] == 'PATCH') == n_patch + 1
    rows = _voice_decisions()[n0:]
    assert len(rows) == 1 and rows[0][2]['action'] == 'tune' and rows[0][2].get('same_as_cache') is True
    assert rows[0][3]['after'] == {'voice_id': 'V1'}
