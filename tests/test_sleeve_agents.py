"""Agente programable de cada cartera (core/sleeve_agents, fase 3, 2026-11-19): configuración acotada, programar en
palabras, y el ciclo — compra solo con SU efectivo, regla «comprar en caídas», stop-loss, y con dinero real solo propone."""
import contextlib
from types import SimpleNamespace as NS

import pytest

from core import sleeve_agents as sa
from core import trading_agent as ta


def test_config_acotada():
    cfg, notes = sa.clean_config({'enabled': True, 'mode': 'AUTO', 'max_pos_pct': 500, 'stop_loss_pct': 0.1,
                                  'min_confidence': 10, 'interval_min': 1, 'universe': ['nvda', 'AMD', 'nvda', '$$$'],
                                  'buy_on_dip_pct': 15, 'rules': 'x' * 900})
    assert cfg['enabled'] and cfg['mode'] == 'auto' and cfg['max_pos_pct'] == 100 and cfg['stop_loss_pct'] == 0.5
    assert cfg['min_confidence'] == 50 and cfg['interval_min'] == 15 and cfg['universe'] == ['NVDA', 'AMD']
    assert len(cfg['rules']) == 500 and any('descartados' in n for n in notes)
    assert 'NVDA, AMD' in sa.describe(cfg) and 'solo tras caer 15' in sa.describe(cfg)
    assert sa.clean_config(None)[0] == sa.DEFAULT


def test_programar_en_palabras(monkeypatch):
    from core import ai
    monkeypatch.setattr(ai, '_ai_json', lambda *a, **k: ({'universe': ['NVDA', 'AMD'], 'buy_on_dip_pct': 15,
                                                         'stop_loss_pct': 8, 'mode': 'manual',
                                                         'summary_es': 'Compra chips en caídas'}, 'm'))
    cfg, summary, notes = sa.parse_text('compra Nvidia y AMD cuando caigan 15 % y vende si pierden 8 %')
    assert cfg['enabled'] and cfg['universe'] == ['NVDA', 'AMD'] and cfg['buy_on_dip_pct'] == 15
    assert summary == 'Compra chips en caídas' and cfg['rules'].startswith('compra Nvidia')


@pytest.fixture
def world(monkeypatch):
    """Una cartera con US$1.000: 2 NVDA a 100 (costo 200) y 800 libres; NVDA hoy a 90 (−10 %)."""
    from brokerage import sleeves as sv
    import ontology.db as odb
    sl = NS(id='s1', status='active', alloc_usd=1000.0)

    class Q:
        def filter(self, *a):
            return self

        def first(self):
            return sl
    monkeypatch.setattr(odb, 'session_scope', lambda: contextlib.nullcontext(NS(query=lambda m: Q())))
    monkeypatch.setattr(sv, 'ledger', lambda s, x: {'cash': 800.0, 'reserved': 0.0, 'available': 800.0,
                                                    'holdings': {'NVDA': 2.0}, 'cost': {'NVDA': 200.0}})
    px = {'NVDA': (90.0, 92.0), 'AMD': (150.0, 149.0)}
    monkeypatch.setattr(sa, '_price', lambda t: px.get(t, (0.0, 0.0)))
    host = NS(_paper=lambda: True, MAX_ORDER_USD=100000.0, _num_str=lambda q: format(q, 'g'))
    monkeypatch.setattr(ta, '_S', host, raising=False)
    monkeypatch.setitem(ta._AGENT, 'running', True)
    monkeypatch.setitem(ta._AGENT, 'log', [])
    calls = {'orders': [], 'places': [], 'signals': []}
    monkeypatch.setattr(ta, '_agent_order', lambda order, *a, **k: calls['orders'].append((order, k.get('sleeve_id'))))
    monkeypatch.setattr(ta, '_agent_place', lambda t, side, n, sig=None, sleeve_id=None:
                        calls['places'].append((t, side, n, sleeve_id)))
    monkeypatch.setattr(ta, '_signal_add', lambda t, side, **k: calls['signals'].append((t, side, k)))
    monkeypatch.setattr(ta, '_agent_tone', lambda t: 0.0)
    monkeypatch.setattr(ta, '_agent_context', lambda t: {'tech': {'pct_from_52w_high': -20.0 if t == 'AMD' else -5.0}})
    monkeypatch.setattr(ta, '_agent_analyze', lambda *a, **k: {})
    monkeypatch.setattr(ta, '_agent_clean_analysis', lambda raw: ('buy', 80, 'tesis', 10))
    monkeypatch.setattr(ta, '_agent_guard', lambda action, facts: None)
    return host, calls


def test_ciclo_en_papel_opera_solo_con_lo_suyo(world):
    host, calls = world
    cfg = sa.clean_config({'enabled': True, 'mode': 'auto', 'universe': ['NVDA', 'AMD'], 'stop_loss_pct': 8,
                           'max_pos_pct': 50, 'buy_on_dip_pct': 15})[0]
    sa.run_one('s1', 'Chips', cfg)
    # stop-loss: NVDA a 90 ≤ 100 × (1 − 8 %) → vende sus 2 acciones, en SU cartera
    assert calls['orders'] and calls['orders'][0][0]['side'] == 'sell' and calls['orders'][0][1] == 's1'
    # NVDA solo a −5 % del máximo → la regla de caídas la descarta; AMD a −20 % → compra ≤ su efectivo
    assert [p[0] for p in calls['places']] == ['AMD']
    t, side, n, sid = calls['places'][0]
    assert side == 'buy' and sid == 's1' and 1 <= n <= 800
    assert any('regla: comprar solo 15' in (e.get('msg') or '') for e in ta._AGENT['log'])


def test_con_dinero_real_solo_propone(world):
    host, calls = world
    host._paper = lambda: False
    cfg = sa.clean_config({'enabled': True, 'mode': 'auto', 'universe': ['AMD'], 'stop_loss_pct': 8,
                           'max_pos_pct': 50})[0]
    sa.run_one('s1', 'Chips', cfg)
    assert not calls['orders'] and not calls['places']
    sides = sorted((t, s) for t, s, _k in calls['signals'])
    assert sides == [('AMD', 'buy'), ('NVDA', 'sell')]
    assert all(k.get('sleeve_id') == 's1' for _t, _s, k in calls['signals'])


def test_intervalo(monkeypatch):
    sa._LAST.clear()
    cfg = sa.clean_config({'interval_min': 60})[0]
    assert sa._due('x', cfg, 1000.0) and not sa._due('x', cfg, 1000.0 + 59 * 60) and sa._due('x', cfg, 1000.0 + 3600)
    sa._LAST.clear()
