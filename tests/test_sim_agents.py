"""tests/test_sim_agents.py — motor de simulación por agentes (core/sim_agents).

Prueba la FORMA del dict devuelto y la robustez, con la IA MOCKEADA (no toca la
red ni requiere keys). No requiere Postgres.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import ai, sim_agents  # noqa: E402


def _fake_ai_factory(pct=999):
    """Devuelve un _ai_complete falso que responde con JSON válido, apuntando a
    una empresa REAL del elenco (la primera 'id' que aparece en el prompt) con un
    pct exagerado para verificar el clamp."""
    def fake(system, prompt, max_tokens=1000, tier='fast'):
        ids = re.findall(r'"id":\s*"([^"]+)"', prompt)
        target = ids[0] if ids else 'X'
        return (json.dumps({
            'events': ['Evento de prueba A', 'Evento de prueba B'],
            'impacts': [
                {'id': target, 'pct': pct, 'rationale': 'razón de prueba'},
                {'id': '__no_existe__', 'pct': 5, 'rationale': 'debe ignorarse'},
            ],
            'narrative': 'Narrativa de prueba.',
        }), 'mock-model')
    return fake


def _assert_shape(res):
    assert isinstance(res, dict)
    assert res.get('ok') is True
    assert isinstance(res.get('narrative'), str) and res['narrative']
    assert isinstance(res.get('impacts'), list)
    assert isinstance(res.get('agents'), list) and res['agents']
    assert isinstance(res.get('rounds'), list)
    for imp in res['impacts']:
        assert set(('id', 'label', 'pct', 'rationale')).issubset(imp.keys())
        assert isinstance(imp['pct'], (int, float))
        # nunca supera la cota global más laxa (35%)
        assert abs(imp['pct']) <= 35.0
    for ag in res['agents']:
        assert set(('name', 'type', 'stance')).issubset(ag.keys())
    for rnd in res['rounds']:
        assert isinstance(rnd.get('round'), int)
        assert isinstance(rnd.get('events'), list)


def test_run_shape_with_mocked_ai(monkeypatch):
    monkeypatch.setattr(ai, '_ai_complete', _fake_ai_factory(pct=999))
    monkeypatch.setattr(ai, '_ai_configured', lambda: True)

    res = sim_agents.run('China restringe la exportación de galio', ['Amazon'], 'es')
    _assert_shape(res)

    ids = [i['id'] for i in res['impacts']]
    assert 'Amazon' in ids                       # la semilla aparece
    assert '__no_existe__' not in ids            # los ids desconocidos se ignoran
    # el pct 999 quedó acotado (Amazon = mid -> 20%)
    amz = next(i for i in res['impacts'] if i['id'] == 'Amazon')
    assert abs(amz['pct']) <= 20.0
    # 2 rondas de IA correcta -> 2 entradas en rounds
    assert len(res['rounds']) == sim_agents.ROUNDS
    # impacts ordenados por magnitud absoluta descendente
    mags = [abs(i['pct']) for i in res['impacts']]
    assert mags == sorted(mags, reverse=True)
    # roster incluye al menos un agente externo (gobierno)
    assert any(a['type'] == 'gobierno' for a in res['agents'])


def test_run_fallback_when_ai_fails(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError('IA caída')
    monkeypatch.setattr(ai, '_ai_complete', boom)
    monkeypatch.setattr(ai, '_ai_configured', lambda: True)

    res = sim_agents.run('Conflicto en el estrecho de Taiwán', ['Amazon'], 'es')
    _assert_shape(res)
    assert res['narrative'].startswith('(estimación sin IA)')
    assert len(res['impacts']) >= 1               # el fallback siempre produce algo
    assert len(res['rounds']) >= 1


def test_run_fallback_when_ai_not_configured(monkeypatch):
    monkeypatch.setattr(ai, '_ai_configured', lambda: False)
    res = sim_agents.run('HBM shortage 2027', ['Amazon'], 'en')
    _assert_shape(res)
    assert res['narrative'].startswith('(estimate without AI)')  # inglés


def test_run_empty_seeds_uses_chokepoints(monkeypatch):
    monkeypatch.setattr(ai, '_ai_complete', _fake_ai_factory(pct=50))
    monkeypatch.setattr(ai, '_ai_configured', lambda: True)
    res = sim_agents.run('Escenario sin semillas', [], 'es')
    _assert_shape(res)
    assert len(res['impacts']) >= 1               # arma elenco desde chokepoints


def test_run_never_raises_on_garbage(monkeypatch):
    monkeypatch.setattr(ai, '_ai_complete', _fake_ai_factory(pct=10))
    monkeypatch.setattr(ai, '_ai_configured', lambda: True)
    # entradas basura: no debe lanzar
    res = sim_agents.run(None, None, None)
    assert isinstance(res, dict) and res.get('ok') is True
