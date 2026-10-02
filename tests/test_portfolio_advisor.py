"""core/portfolio_advisor.py — comité de cartera (sin red: riesgo y pizarra inyectados)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import portfolio_advisor as pa  # noqa: E402


def _risk(positions, horizon=10):
    syms = [p['symbol'] for p in positions]
    vals = {'NVDA': 6000.0, 'AMD': 2500.0, 'INTC': 1000.0, 'TSM': 500.0}
    rc = {'NVDA': 70.0, 'AMD': 20.0, 'INTC': 6.0, 'TSM': 4.0}
    tot = sum(vals[s] for s in syms)
    return {'ok': True, 'portfolio_value_usd': tot, 'vol_ann_pct': 38.0, 'max_drawdown_pct': -35.0,
            'var95': {'hist_1d_pct': 3.1, 'hist_1d_usd': 310.0}, 'beta_spy': 1.6, 'return_ann_pct': 20.0,
            'diversification_ratio': 1.1, 'as_of': '2026-10-01', 'source': 'test',
            'positions': [{'symbol': s, 'shares': 1, 'price': 1, 'value_usd': vals[s], 'weight_pct': vals[s] / tot * 100,
                           'vol_ann_pct': 50.0, 'risk_contrib_pct': rc[s]} for s in syms],
            'correlation': {'symbols': ['NVDA', 'AMD'], 'matrix': [[1, 0.86], [0.86, 1]]}, 'excluded': []}


def _board():
    items = [
        {'entity_id': 'Intel', 'label': 'Intel', 'overall_conviction': -48, 'best_for': None, 'best_against': {'text_es': 'x'}, 'memo': None},
        {'entity_id': 'TSMC', 'label': 'TSMC', 'overall_conviction': 52, 'best_for': {'text_es': 'y'}, 'best_against': None, 'memo': None},
        {'entity_id': 'Cameco', 'label': 'Cameco', 'overall_conviction': 40, 'best_for': {'text_es': 'uranio'}, 'best_against': None, 'memo': None},
        {'entity_id': 'Constellation', 'label': 'Constellation Energy', 'overall_conviction': 33, 'best_for': {'text_es': 'nuclear'}, 'best_against': None, 'memo': None},
    ]
    return {x['entity_id']: x for x in items}, items


POS = [{'symbol': 'NVDA', 'shares': 10}, {'symbol': 'AMD', 'shares': 5}, {'symbol': 'INTC', 'shares': 40},
       {'symbol': 'TSM', 'shares': 2}]


def test_acciones_concretas_para_perfil_conservador():
    a = pa.analyze(POS, profile={'risk': 'conservador'}, risk_fn=_risk, board_fn=_board)
    assert a['ok'] and a['profile']['key'] == 'conservador' and a['health']['tone'] == 'bad'
    kinds = {(x['kind'], x['symbol']) for x in a['actions']}
    assert ('sell', 'INTC') in kinds                      # convicción −48 → salir
    assert ('reduce', 'NVDA') in kinds                    # 60 % de la cartera > 12 %
    nv = next(x for x in a['actions'] if x['symbol'] == 'NVDA')
    assert nv['to_pct'] == 12.0 and nv['delta_usd'] == -4800.0 and nv['priority'] == 1
    assert any(x['kind'] == 'buy_new' for x in a['actions'])     # diversificar (vol 38 % > 14 %)
    assert 'IA' in a['disclaimer'] or 'AI' in a['disclaimer']
    ex = pa.explain(a)
    assert ex['text'] and 'tú decides' in ex['text']


def test_agresivo_tolera_mas_y_sin_posiciones():
    a = pa.analyze(POS, profile={'risk': 'agresivo'}, risk_fn=_risk, board_fn=_board)
    nv = [x for x in a['actions'] if x['symbol'] == 'NVDA']
    assert not nv or nv[0]['to_pct'] == 30.0
    assert pa.analyze([], risk_fn=_risk, board_fn=_board)['error_code'] == 'no_positions'
