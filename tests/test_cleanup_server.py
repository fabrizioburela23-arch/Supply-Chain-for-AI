"""Limpieza 2026-10-11 ("que no queden cosas sueltas"), lado servidor. Cada prueba fija un arreglo
del inventario para que la copia suelta no vuelva:
§3 vocabulario re-escrito a mano · §8 preguntas abiertas guardadas como "errores" · §9 agente de
noticias sin perfil en vivo y permisos que no coincidían · §13 el chat no podía abrir Cripto ·
§15 rutas sin candado o muertas · §21 restos (alias _claude_complete, precio de respaldo de Gemini,
"skipped por presupuesto" por analista)."""
import inspect
import json
import os
import re
from types import SimpleNamespace

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIN = '4321'


def _read(rel):
    return open(os.path.join(ROOT, rel), encoding='utf-8').read()


def _vocab_json():
    return json.load(open(os.path.join(ROOT, 'ontology', 'vocabulary.json'), encoding='utf-8'))['relation_types']


# ── §3 vocabulario ───────────────────────────────────────────────────────────
def test_respaldo_del_vocabulario_es_copia_exacta_del_json():
    from ontology.vocabulary import _FALLBACK, _FLOW_FALLBACK
    rt = _vocab_json()
    for k, v in _FALLBACK['relation_types'].items():
        assert v['weight'] == rt[k]['weight'], k                     # license era 0.8 (json 0.5 desde 2026-10-06)
        assert bool(v.get('flow')) == bool(rt[k].get('flow')), k
    flow = {k for k, v in rt.items() if v.get('structural') and v.get('flow')}
    assert set(_FLOW_FALLBACK) == flow


def test_listas_de_relaciones_del_cliente_y_scripts_coinciden_con_el_json():
    rt = _vocab_json()
    flow = {k for k, v in rt.items() if v.get('structural') and v.get('flow')}
    html = _read('app.html')
    m = re.search(r'const NRS_FLOW_TYPES = \{([^}]*)\}', html)
    assert m and set(re.findall(r'(\w+)\s*:', m.group(1))) == flow
    from scripts import audit_graph
    assert set(audit_graph._FALLBACK_RELS) == {k for k, v in rt.items() if v.get('structural')}
    from matrix import tensor
    assert set(tensor.SUPPLIER_RELS) <= flow
    from mcp_server.tools import RELATION_CLASS
    assert {k for k, v in rt.items() if v.get('structural')} <= set(RELATION_CLASS)


# ── §8 preguntas abiertas ────────────────────────────────────────────────────
def test_preguntas_abiertas_tienen_su_columna_y_leen_las_filas_viejas():
    from ontology.db import _COLUMNAS_TARDIAS
    from research.models import AgentRun, errors_of, open_questions_of
    assert ('agent_runs', 'open_questions', 'JSONB') in _COLUMNAS_TARDIAS
    assert 'open_questions' in AgentRun.__table__.columns
    nueva = SimpleNamespace(open_questions=['¿Guía Q4?'], errors=[])
    vieja = SimpleNamespace(open_questions=None, errors=[{'unresolved_questions': ['¿Capex?']}, 'modelo: 429'])
    assert open_questions_of(nueva) == ['¿Guía Q4?'] and errors_of(nueva) == []
    assert open_questions_of(vieja) == ['¿Capex?'] and errors_of(vieja) == ['modelo: 429']


def test_runner_guarda_preguntas_fuera_de_errors_y_sin_skip_por_presupuesto():
    from research import runner
    src = inspect.getsource(runner._finish_run) + inspect.getsource(runner._finish_run_inner)   # paso 19: dentro de research.run
    assert "run.open_questions" in src and "{'unresolved_questions'" not in src
    assert 'presupuesto' not in inspect.getsource(runner._prepare_run).split('"""')[-1]   # solo el job difiere
    assert not hasattr(runner, 'run_agent')                                              # camino muerto
    from research import committee
    assert 'errors_of(run)' in inspect.getsource(committee)                              # la sala no muestra el dict crudo


# ── §9 agentes de investigación ──────────────────────────────────────────────
def test_noticias_recibe_perfil_en_vivo_y_permisos_salen_de_agent_needs():
    from research.agents.registry import AGENTS
    from research.context import AGENT_NEEDS
    assert 'profile' in AGENT_NEEDS['news']
    for a in AGENTS:
        assert list(a.permitted_tools) == [('live_profile' if n == 'profile' else n) for n in AGENT_NEEDS[a.agent_type]]
    assert 'permitted_tools=' not in _read('research/agents/registry.py').split('AGENTS = [', 1)[1].split(']\n', 1)[0]


# ── §13 pestañas del chat ────────────────────────────────────────────────────
def test_pestanas_del_chat_son_las_de_app_html():
    from core.khipu_chat import TABS
    html = _read('app.html')
    tabs_html = set(re.findall(r'data-tab="([a-z_]+)"', html))
    assert set(TABS) == tabs_html | {'tkg'}
    body = html[html.index('function switchTab(tab){'):html.index('function switchTab(tab){') + 4000]
    for t in TABS:
        assert f"'{t}'" in body, t


# ── §15 rutas ────────────────────────────────────────────────────────────────
@pytest.fixture
def client(monkeypatch):
    import server
    from core import http as core_http
    from core import pin as core_pin
    monkeypatch.setenv('TRADE_PIN', PIN)
    core_http._rate_buckets.clear()
    core_pin._reset_for_tests()
    server.app.config['TESTING'] = True
    yield server.app.test_client()
    core_http._rate_buckets.clear()
    core_pin._reset_for_tests()


def test_rutas_de_operador_piden_pin_y_la_ruta_muerta_no_existe(client, monkeypatch):
    import server
    for url in ('/api/voice/voices', '/api/diag/recent'):
        r = client.get(url)
        assert r.status_code == 401 and r.get_json()['code'] == 'invalid_pin', url
    monkeypatch.setattr(server, 'ELEVENLABS_KEY', '')
    r = client.get('/api/voice/voices', headers={'X-Trade-Pin': PIN})
    assert r.status_code == 400 and r.get_json()['error_en']
    r = client.get('/api/diag/recent', headers={'X-Trade-Pin': PIN})
    assert r.status_code == 200 and 'diags' in r.get_json()
    assert client.post('/api/ai/command', json={'query': 'hola'}).status_code in (404, 405)


def test_voice_agent_es_el_unico_cliente_rest_de_elevenlabs():
    assert 'api.elevenlabs.io' not in _read('server.py')
    from core import voice_agent as va

    class _R:
        def __init__(self, status, payload):
            self.status_code, self._p, self.text = status, payload, json.dumps(payload)

        def json(self):
            return self._p

    class _Http:
        def get(self, url, **kw):
            if url.endswith('/v1/voices'):
                return _R(200, {'voices': [{'voice_id': 'v1', 'name': 'Ana', 'category': 'premade'}]})
            return _R(401, {'detail': {'status': 'invalid_api_key', 'message': 'bad'}})

        def post(self, url, **kw):
            assert url.endswith('/v1/voices/add/owner1/v9') and kw['json']['new_name'] == 'Khipu ES'
            return _R(200, {'voice_id': 'v9'})

    out = va.list_voices('k', _Http())
    assert out['mine'][0]['voice_id'] == 'v1' and out['upstream']['mine'] == 200
    assert out['shared_es'] == [] and out['upstream']['shared']['code'] == 'invalid_api_key'
    assert va.adopt_shared_voice('k', 'owner1', 'v9', None, _Http()) == {'ok': True, 'voice_id': 'v9'}


# ── §21 restos ───────────────────────────────────────────────────────────────
def test_restos_alias_y_precios():
    from core import ai
    from core.ai_usage import FEATURE_BY_PATH, price_for
    assert not hasattr(ai, '_claude_complete')
    assert '_claude_complete' not in _read('server.py')
    assert price_for('gemini', 'gemini-3.5-flash') == (1.5, 9.0)              # 1.er respaldo: antes al genérico
    assert price_for('gemini', 'gemini-3.5-flash-lite') == (0.3, 2.5)        # el prefijo más largo sigue mandando
    assert not any(p in ('/api/bixby', '/api/ai/command') for p, _f in FEATURE_BY_PATH)


# ── §14 instrucciones de la voz ──────────────────────────────────────────────
def test_prompt_de_voz_describe_khipus_os_y_sus_agentes():
    """Desde la voz para Khipus OS (2026-10-11) la voz abre PANTALLAS del menú Herramientas (open_screen), no
    pestañas: la lista sale de server.VOICE_SCREENS, que tests/test_voice_os_server.py compara con cockpit.js."""
    import server
    from core.agents_registry import AGENTS
    p = server.BIXBY_SYSTEM_PROMPT
    assert 'KHIPUS OS' in p and '4 PRIMARY TABS' not in p and 'NEXUS' not in p and '{agents}' not in p
    assert '{screens}' not in p and 'switch_tab' not in p
    for a in AGENTS:
        assert a['es'] in p, a['id']
    for es, en in server.VOICE_SCREENS.values():
        assert f'"{es}" / "{en}"' in p, es
    assert 'ALWAYS waits for human approval' in p


# ── §20 motor de matrices: el disperso es el predeterminado ─────────────────
def test_motor_disperso_por_defecto_y_denso_como_respaldo(monkeypatch):
    from matrix import engine as E
    monkeypatch.delenv('MATRIX_ENGINE', raising=False)
    assert E._use_sparse() is (E.sp is not None)
    monkeypatch.setenv('MATRIX_ENGINE', 'dense')
    assert E._use_sparse() is False
    monkeypatch.setattr(E, 'sp', None)                      # sin scipy → denso, nunca se rompe
    monkeypatch.delenv('MATRIX_ENGINE', raising=False)
    assert E._use_sparse() is False


def test_metricas_calculan_la_dependencia_una_sola_vez():
    """compute_metrics propagaba N choques reconstruyendo Tᵀ cada vez (O(N·R·N²), ~30-47 s); ahora la
    calcula una vez (dependency_transpose) y el resultado es IDÉNTICO."""
    import inspect as _inspect
    from matrix import engine as E
    snap = json.load(open(os.path.join(ROOT, 'data', 'grafo_v0.json'), encoding='utf-8'))
    ids = [n['id'] for n in snap['nodes']][:300]
    idx = {k: i for i, k in enumerate(ids)}
    tr = [(l['source'], l['target'], l.get('type') or 'supply', float(l.get('w') or 1)) for l in snap['links']]
    mats, _, ids2 = E.build_matrices_from_triples(tr, idx)
    dt = E.dependency_transpose(mats)
    for x in ids[:40]:
        assert E.propagate(mats, idx, ids2, [x]) == E.propagate(mats, idx, ids2, [x], dt=dt)
    assert 'dt=dt' in _inspect.getsource(E.compute_metrics)


# ── restos del inventario cuantitativo y de contexto ─────────────────────────
def test_caida_maxima_de_un_ano_ignora_maximos_mas_viejos():
    from research.analytics import technical_indicators
    xs = [200.0] + [100.0] * 260 + [90.0]           # pico viejo (hace > 1 año) a 200; el último año va de 100 a 90
    out = technical_indicators(xs) if technical_indicators.__code__.co_argcount == 1 else None
    if out is None:
        import inspect as _i
        src = _i.getsource(technical_indicators)
        assert 'win = xs[-250:]' in src and 'peak, mdd = win[0], 0.0' in src
    else:
        assert out['max_drawdown_1y_pct'] == -10.0


def test_contexto_de_investigacion_y_semantico_solo_flujo():
    from core import semantic
    from core.world import client_nrs
    from core.sim_agents import _approx_nrs
    ctx = semantic.build_context(['Nvidia'])
    foco = ctx['foco'][0]
    flow = semantic._load_snapshot()['flow_types']
    assert all(x['tipo'] in flow for x in foco['depende_de'] + foco['provee_a'])
    snap = semantic._load_snapshot()
    assert ctx['chokepoints_por_grado'][0]['links'] == max(snap['flow_deg'].values())
    n = snap['by_id']['Nvidia']
    assert _approx_nrs(snap, 'Nvidia') == client_nrs(n, snap['flow_deg'].get('Nvidia', 0))
    src = _read('research/context.py')
    assert 'rel_types=set(flow_relation_types())' in src and 'NO VERIFICADO' in src
