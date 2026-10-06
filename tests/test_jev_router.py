"""Jev AL MANDO del chat (core/decide.chat_plan + core/khipu_chat): elige el camino más barato que alcanza.
local_fact → ficha con datos en vivo SIN IA · needs_tools → pocas consultas · deep → lo de siempre ·
@agente → nivel del analista (local / rápido / profundo). Sin control o sin confianza → nada cambia."""
import json
import os
import sys
from concurrent.futures import Future

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import ai as core_ai  # noqa: E402
from core import decide  # noqa: E402
from core import khipu_chat as kc  # noqa: E402
from research import agent_skills as sk  # noqa: E402
from research import ask_agent as aa  # noqa: E402


def _jev(route, conf=0.9, trade=0.0, pf=0.0):
    return {'route': {'choice': route, 'confidence': conf}, 'mentions_company': {'noul': 0.9},
            'asks_trade': {'noul': trade}, 'about_portfolio': {'noul': pf}, 'urgency': {'score': 1}}


def _done(v):
    f = Future()
    f.set_result(v)
    return f


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    from mcp_server import tools as mt
    monkeypatch.setattr(mt, '_live_profile', lambda sym: {'available': False, 'reason': 'test (offline)'})
    monkeypatch.setattr(mt._auth, 'db_available', lambda: False)
    monkeypatch.setattr(decide, '_persist', lambda row: None)
    monkeypatch.setattr('core.live_facts.live_facts_block', lambda m: '')


@pytest.fixture
def jev_on(monkeypatch):
    monkeypatch.setenv('TYPESAFE_API_KEY', 'ts-test')
    monkeypatch.setenv('DECIDE_CONTROL', 'chat_gate')
    box = {'ans': _jev('needs_deep_reasoning')}
    monkeypatch.setattr(decide, 'ask', lambda state, q, feature=None, timeout=None: box['ans'])
    return box


class CountingAI:
    def __init__(self, script):
        self.script, self.calls = list(script), []

    def __call__(self, system, prompt, max_tokens=1000, tier='fast', **kw):
        self.calls.append(tier)
        item = self.script.pop(0) if self.script else {'final': {'answer': 'Listo.', 'actions': []}}
        return json.dumps(item), 'fake:model'


def test_decision_y_plan(monkeypatch):
    d = decide.decision_of({'route': {'choice': 'needs_tools', 'probabilities': {'needs_tools': 0.82}}})
    assert d['route'] == 'needs_tools' and d['confidence'] == 0.82
    assert decide.decision_of({'route': {'choice': 'inventada'}})['route'] is None
    monkeypatch.setenv('TYPESAFE_API_KEY', 'ts-test')
    # sin DECIDE_CONTROL: Jev no manda
    monkeypatch.delenv('DECIDE_CONTROL', raising=False)
    assert decide.chat_plan(_done(_jev('local_fact'))) is None
    monkeypatch.setenv('DECIDE_CONTROL', 'chat_gate')
    assert decide.chat_plan(_done(_jev('local_fact')))['route'] == 'local_fact'
    assert decide.chat_plan(_done(_jev('local_fact', conf=0.4))) is None          # poca confianza
    assert decide.chat_plan(_done(_jev('local_fact', trade=0.8))) is None         # parece una orden
    assert decide.chat_plan(_done(None)) is None and decide.chat_plan(None) is None
    slow = Future()                                                               # no llegó a tiempo
    assert decide.chat_plan(slow, wait_s=0.01) is None


def test_dato_puntual_se_responde_sin_ia(monkeypatch, jev_on):
    jev_on['ans'] = _jev('local_fact')
    ai = CountingAI([])
    monkeypatch.setattr(core_ai, '_ai_complete', ai)
    monkeypatch.setattr(core_ai, '_ai_configured', lambda: True)
    out = kc.run_chat('¿cuál es el precio de nvidia?', [], 'es', {})
    assert ai.calls == []                                              # cero tokens de IA
    assert out['answer_source'] == 'local' and out['ai'] is False and out['steps'] == 0
    assert '**Nvidia**' in out['answer'] and 'Fuente' in out['answer']
    assert out['router'] == {'by': 'jev', 'route': 'local_fact', 'confidence': 0.9, 'ai_calls': 0}
    assert out['actions'][0]['type'] == 'open_xray'


def test_consulta_corta_limita_rondas(monkeypatch, jev_on):
    jev_on['ans'] = _jev('needs_tools')
    ai = CountingAI([{'tool': 'search_companies', 'args': {'query': 'TSMC'}},
                     {'tool': 'search_companies', 'args': {'query': 'ASML'}},
                     {'final': {'answer': 'Respuesta corta.', 'actions': []}}])
    monkeypatch.setattr(core_ai, '_ai_complete', ai)
    monkeypatch.setattr(core_ai, '_ai_configured', lambda: True)
    out = kc.run_chat('¿quién le vende a nvidia?', [], 'es', {})
    assert out['router']['route'] == 'needs_tools' and out['router']['max_steps'] == 2
    assert out['answer'] == 'Respuesta corta.' and len(ai.calls) == 3


def test_sin_jev_todo_igual(monkeypatch):
    monkeypatch.delenv('TYPESAFE_API_KEY', raising=False)
    ai = CountingAI([{'final': {'answer': 'Hola.', 'actions': []}}])
    monkeypatch.setattr(core_ai, '_ai_complete', ai)
    monkeypatch.setattr(core_ai, '_ai_configured', lambda: True)
    out = kc.run_chat('¿cuál es el precio de nvidia?', [], 'es', {})
    assert out['router'] == {'by': 'default'} and out['answer'] == 'Hola.' and ai.calls == ['fast']


def test_dato_puntual_sin_ficha_usa_la_ia(monkeypatch, jev_on):
    jev_on['ans'] = _jev('local_fact')
    ai = CountingAI([{'final': {'answer': 'Una tasa es…', 'actions': []}}])
    monkeypatch.setattr(core_ai, '_ai_complete', ai)
    monkeypatch.setattr(core_ai, '_ai_configured', lambda: True)
    out = kc.run_chat('¿qué es una tasa de interés?', [], 'es', {})
    assert out['answer'] == 'Una tasa es…' and out['router']['max_steps'] == 1


def test_agente_jev_elige_su_nivel(monkeypatch, jev_on):
    monkeypatch.setattr('ontology.db.ontology_available', lambda: False)
    seen = {}

    def fake_ask(s, seat, q, ent, lang, **k):
        seen['mode'] = k.get('mode', 'deep')
        return {'ok': True, 'seat': seat, 'emoji': '⛓', 'name': 'Cadena', 'entity': 'OpenAI', 'label': 'OpenAI',
                'answer': 'Datos.', 'refs': {}, 'n_claims': 0, 'needs_research': False, 'model': None, 'skill': {}}
    monkeypatch.setattr(aa, 'ask', fake_ask)
    for route, mode in (('local_fact', 'local'), ('needs_tools', 'fast'), ('needs_deep_reasoning', 'deep')):
        jev_on['ans'] = _jev(route)
        out = kc.run_chat('@cadena de quién depende open ai', [], 'es', {})
        assert seen['mode'] == mode, route
        assert out['router']['by'] == 'jev' and out['router']['mode'] == mode


_PKT = {'text': 'S1 <data>Concentración de proveedores: Microsoft (Azure) 17,2 % del peso</data>',
        'facts': {}, 'sources': [], 'n_evidence': 1, 'ok': True, 'listed': False}


def test_ask_modo_local_y_rapido(monkeypatch):
    monkeypatch.setattr(aa, '_resolve', lambda e: ('OpenAI', 'OpenAI', None))
    monkeypatch.setattr(aa, '_load_claims', lambda s, eid, seat: [])
    monkeypatch.setattr(sk, 'skill_packet', lambda seat, eid: dict(_PKT))
    tiers = []

    def ai(system, prompt, mt, tier):
        tiers.append(tier)
        return 'Respuesta [S1].', 'm'
    r = aa.ask(None, 'supply_chain', '?', 'OpenAI', 'es', ai=ai, mode='local')
    assert tiers == [] and r['mode'] == 'local' and r['model'] is None
    assert r['answer'].startswith('Esto muestran mis datos de OpenAI:') and 'Microsoft (Azure) 17,2 %' in r['answer']
    r = aa.ask(None, 'supply_chain', '?', 'OpenAI', 'es', ai=ai, mode='fast')
    assert tiers == ['fast'] and r['mode'] == 'fast'
    r = aa.ask(None, 'supply_chain', '?', 'OpenAI', 'es', ai=ai)
    assert tiers == ['fast', 'deep']
    # sin datos propios, 'local' cae a la IA rápida
    monkeypatch.setattr(sk, 'skill_packet', lambda seat, eid: dict(_PKT, text='', n_evidence=0, ok=True))
    r = aa.ask(None, 'supply_chain', '?', 'OpenAI', 'es', ai=ai, mode='local')
    assert tiers[-1] == 'fast' and r['mode'] == 'fast'
