"""Router de modelos del chat (core/model_router, 2026-11-07): Jev elige pequeño / mediano / frontera; si Jev no
llega, reglas instantáneas. Pequeño = pasos con Haiku; frontera = respuesta final con Opus."""
import json

import pytest

from core import ai, decide
from core import khipu_chat as kc
from core import model_router as mr


def _plan(route, conf=0.9, pf=0.0):
    return {'route': route, 'confidence': conf, 'about_portfolio': pf}


def test_jev_manda_el_carril():
    assert mr.from_jev(_plan('local_fact')) == 'local'
    assert mr.from_jev(_plan('needs_tools')) == 'small'
    assert mr.from_jev(_plan('needs_tools', pf=0.9)) == 'mid'          # su cartera: no el más chico
    assert mr.from_jev(_plan('needs_deep_reasoning', 0.9)) == 'frontier'
    assert mr.from_jev(_plan('needs_deep_reasoning', 0.65)) == 'mid'   # dudoso: mediano
    assert mr.from_jev(None) is None and mr.from_jev({'route': None}) is None


@pytest.mark.parametrize('q,lane', [
    ('precio de AMD', 'small'), ('¿cuándo reporta Nvidia?', 'small'), ('noticias de Micron', 'small'),
    ('compara AMD vs Nvidia', 'mid'), ('¿Nvidia ya tocó fondo? simula', 'mid'),
    ('dame la tesis de Nvidia a 3 años', 'frontier'), ('¿debería invertir en TSMC?', 'frontier'),
    ('analiza a fondo la cadena de HBM', 'frontier')])
def test_reglas_de_respaldo(q, lane):
    assert mr.from_rules(q) == lane


def test_choose_y_modelos(monkeypatch):
    monkeypatch.delenv('AI_MODEL_SMALL', raising=False)
    monkeypatch.delenv('AI_MODEL_FRONTIER', raising=False)
    c = mr.choose(None, 'precio de AMD')
    assert c['by'] == 'reglas' and c['lane'] == 'small' and c['step_model'] == 'claude-haiku-5-5' and not c['final_model']
    c = mr.choose(_plan('needs_deep_reasoning'), 'x')
    assert c['by'] == 'jev' and c['final_model'] == 'claude-opus-5-5' and c['step_model'] is None
    monkeypatch.setenv('AI_MODEL_FRONTIER', 'claude-fable-5-1')
    assert mr.choose(_plan('needs_deep_reasoning'), 'x')['final_model'] == 'claude-fable-5-1'
    monkeypatch.setenv('AI_ROUTER', 'off')
    assert not mr.enabled()


def _offline(monkeypatch):
    from mcp_server import tools as mt
    monkeypatch.setattr(mt, '_live_profile', lambda sym: {'available': False, 'reason': 'test (offline)'})
    monkeypatch.setattr(mt._auth, 'db_available', lambda: False)
    monkeypatch.setattr(decide, '_persist', lambda row: None)
    monkeypatch.setattr('core.live_facts.live_facts_block', lambda m: '')
    monkeypatch.setattr(ai, '_ai_configured', lambda: True)


def _jev(route):
    return {'route': {'choice': route, 'confidence': 0.9}, 'mentions_company': {'noul': 0.9},
            'asks_trade': {'noul': 0.0}, 'about_portfolio': {'noul': 0.0}, 'urgency': {'score': 1}}


def test_chat_usa_el_modelo_del_carril(monkeypatch):
    _offline(monkeypatch)
    monkeypatch.delenv('TYPESAFE_API_KEY', raising=False)
    monkeypatch.delenv('TYPESAFE_KEY', raising=False)
    calls = []

    def fake_ai(system, prompt, max_tokens=1000, tier='fast', **kw):
        calls.append((tier, kw.get('model')))
        return json.dumps({'final': {'answer': 'Respuesta corta y clara para el inversionista.', 'actions': []}}), \
            kw.get('model') or f'fake:{tier}'
    monkeypatch.setattr(ai, '_ai_complete', fake_ai)
    out = kc.run_chat('precio de AMD', [], 'es', {})                     # sin Jev → reglas → pequeño
    assert out['router']['lane'] == 'small' and out['router']['lane_by'] == 'reglas'
    assert calls and all(m == 'claude-haiku-5-5' for _t, m in calls)
    assert out['router']['lane_es'].endswith('modelo pequeño')
    # con Jev: análisis → la respuesta final la escribe el modelo frontera
    calls.clear()
    monkeypatch.setenv('TYPESAFE_API_KEY', 'ts-test')
    monkeypatch.delenv('DECIDE_CONTROL', raising=False)
    monkeypatch.setattr(decide, 'ask', lambda state, q, feature=None, timeout=None: _jev('needs_deep_reasoning'))
    out = kc.run_chat('¿cuál es la tesis de Nvidia a 3 años?', [], 'es', {})
    assert out['router']['by'] == 'jev' and out['router']['lane'] == 'frontier' and out['router']['lane_by'] == 'jev'
    assert ('deep', 'claude-opus-5-5') in calls and calls[0][1] is None   # los pasos, con el modelo de siempre
