"""core/ai_usage.py — registro de gasto, límites y reporte · core/scenario_engine.py."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import ai_usage  # noqa: E402

needs_db = pytest.mark.skipif(not os.getenv('DATABASE_URL'), reason='requiere DATABASE_URL')


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.setattr(ai_usage, 'settings', lambda: dict(ai_usage.default_settings(), daily_usd=1.0, monthly_usd=50.0,
                                                          per_who_daily_usd=0.5, per_feature_daily_usd={'canvas': 0.2}))
    monkeypatch.setattr(ai_usage, '_load_from_db', lambda: None)
    monkeypatch.setattr(ai_usage, '_ensure_writer', lambda: None)
    ai_usage._reset_for_tests()
    yield
    ai_usage._reset_for_tests()


def test_precios_por_modelo_y_costo():
    assert ai_usage.price_for('claude', 'claude-sonnet-5') == (2.0, 10.0)
    assert ai_usage.price_for('claude', 'claude-haiku-4-5') == (1.0, 5.0)
    assert ai_usage.price_for('gemini', 'gemini-2.5-flash') == (0.3, 2.5)
    assert ai_usage.price_for('nvidia', 'meta/llama-3.3') == (0.0, 0.0)
    assert ai_usage.cost_of('claude', 'claude-sonnet-5', 1_000_000, 100_000) == pytest.approx(3.0)


def test_registro_atribuye_funcion_y_persona_y_limites():
    with ai_usage.ai_context('canvas', 'fabrizio'):
        ai_usage.record('claude', 'claude-sonnet-5', 50_000, 10_000)          # $0.20
        with pytest.raises(ai_usage.AIBudgetError) as e:
            ai_usage.check('claude', 1000)                                       # tope de canvas 0.20
        assert e.value.scope == 'feature' and 'Canvas' in e.value.es
    with ai_usage.ai_context('khipu_chat', 'fabrizio'):
        ai_usage.record('gemini', 'gemini-2.5-flash', 100_000, 100_000)      # $0.28 → fabrizio 0.48
        ai_usage.check('claude', 1000)                                           # aún bajo 0.5
        ai_usage.record('claude', 'claude-sonnet-5', 10_000, 1_000)          # +0.03 → 0.51
        with pytest.raises(ai_usage.AIBudgetError) as e:
            ai_usage.check('claude', 1000)
        assert e.value.scope == 'who'
    with ai_usage.ai_context('comite', 'otro'):
        ai_usage.check('claude', 4)                                              # ping del 🩺: nunca bloquea
        ai_usage.record('claude', 'claude-sonnet-5', 200_000, 50_000)        # total > $1 diario
        with pytest.raises(ai_usage.AIBudgetError) as e:
            ai_usage.check('claude', 1000)
        assert e.value.scope == 'daily'
    r = ai_usage.report(days=7)
    assert r['totals']['today'] == pytest.approx(0.20 + 0.28 + 0.03 + 0.9, abs=0.01)
    feats = {f['key']: f for f in r['by_feature']}
    assert feats['canvas']['label'] == 'Canvas IA' and feats['comite']['calls'] == 1
    assert {p['key'] for p in r['by_provider']} == {'claude', 'gemini'}
    assert r['recent'][0]['feature'] == 'comite' and r['remaining']['today'] == 0


def test_bind_propaga_contexto_a_otro_hilo():
    from concurrent.futures import ThreadPoolExecutor
    with ai_usage.ai_context('investigacion', 'ana'):
        f = ai_usage.bind(lambda: ai_usage.current())
    with ThreadPoolExecutor(1) as ex:
        assert ex.submit(f).result() == {'feature': 'investigacion', 'who': 'ana'}


def test_cascada_se_detiene_por_limite(monkeypatch):
    from core import ai
    calls = []

    def boom(*a, **k):
        calls.append('claude')
        raise ai_usage.AIBudgetError('límite diario de gasto', 'daily spend limit', 'daily')
    monkeypatch.setattr(ai, '_AI_PROVIDERS', {'claude': (lambda: True, boom),
                                              'gemini': (lambda: True, lambda *a, **k: calls.append('gemini'))})
    monkeypatch.setattr(ai, 'AI_ORDER', ['claude', 'gemini'])
    with pytest.raises(ai_usage.AIBudgetError):
        ai._ai_complete_raw('s', 'p', 100)
    assert calls == ['claude']


@needs_db
def test_persistencia_y_api(monkeypatch):
    from ontology.db import init_schema
    init_schema(retries=1)
    import server
    with ai_usage.ai_context('comite', 'pytest-db'):
        ai_usage.record('claude', 'claude-haiku-4-5', 1000, 1000)
    assert ai_usage.flush() == 1
    server.app.config['TESTING'] = True
    c = server.app.test_client()
    r = c.get('/api/ai/usage?days=1')
    assert r.status_code == 200 and r.get_json()['source'] == 'database'
    assert any(w['key'] == 'pytest-db' for w in r.get_json()['by_who'])
    monkeypatch.setenv('TRADE_PIN', '9999')
    assert c.post('/api/ai/usage/limits', json={'limits': {'daily_usd': 3}}).status_code == 401
    r = c.post('/api/ai/usage/limits', json={'actor': 't', 'limits': {'daily_usd': 3, 'per_feature_daily_usd': {'canvas': 1}}},
               headers={'X-Trade-Pin': '9999'})
    assert r.status_code == 200 and r.get_json()['limits']['daily_usd'] == 3.0


def test_motor_de_escenarios_hbm_y_taiwan():
    from core import scenario_engine as se
    from core import semantic, sim_agents
    snap = semantic._load_snapshot()
    a = se.analyze('China prohíbe exportar HBM', snap)
    assert a['event'] == 'export_ban' and a['actor'] == 'china'
    assert 'CXMT' in a['hit'] and 'SKHynix' in a['benefit']
    r = sim_agents.run('China prohíbe exportar HBM', ['XPO'], 'es')      # XPO ya no entra por "eXPOrtar"
    assert 'XPO' not in [i['id'] for i in r['impacts']] and r['structural'] and r['watch']
    assert any(i['channel'] == 'customer' and '→' in i['path'] for i in r['impacts'])
    t = se.analyze('¿Qué pasa si Taiwán es bloqueado?', snap)
    assert 'TSMC' in t['hit'] and t['event'] == 'disruption'
    assert se.analyze('zzzz qqqq', snap) is None
