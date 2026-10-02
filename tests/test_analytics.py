"""research/analytics.py — análisis cuantitativo determinista (sin red)."""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.analytics import fundamental_ratios, peer_table, technical_indicators  # noqa: E402

FIN = {'available': True, 'years': [2022, 2023, 2024],
       'revenue': [100e9, 120e9, 150e9], 'gross_profit': [50e9, 66e9, 90e9],
       'operating_income': [20e9, 30e9, 45e9], 'net_income': [15e9, 22e9, 33e9],
       'fcf': [10e9, 20e9, 30e9], 'cash': [20e9, 25e9, 40e9], 'total_debt': [30e9, 28e9, 25e9],
       'ebitda': [30e9, 40e9, 50e9], 'shares': [1000, 990, 970], 'roic': [0.2, 0.25, 0.3]}


def test_ratios_fundamentales_calculados():
    r, txt = fundamental_ratios(FIN, {'market_cap_usd_b': 600, 'pe_trailing': 25})
    assert r['revenue_yoy_pct'] == 25.0 and r['revenue_cagr_pct'] == round((1.5 ** 0.5 - 1) * 100, 1)
    assert r['gross_margin_pct'] == 60.0 and r['gross_margin_pct_first'] == 50.0
    assert r['fcf_margin_pct'] == 20.0 and r['net_cash_usd'] == 15e9
    assert r['debt_to_ebitda'] == 0.5 and r['fcf_yield_pct'] == 5.0 and r['p_fcf'] == 20.0
    assert r['roic_pct'] == 30.0 and r['share_change_pct'] == -3.0
    assert 'margen bruto 60.0 % en 2024 (vs 50.0 % en 2022: mejora)' in txt and 'recompras' in txt
    assert 'caja neta 15.0 mil millones USD' in txt


def test_ratios_sin_datos():
    assert fundamental_ratios({'available': False}) == (None, '')


def _series(n, start=100.0, daily=0.001):
    return [(i, start * math.exp(daily * i)) for i in range(n)]


def test_tecnico_tendencia_y_fuerza_relativa():
    t, txt = technical_indicators(_series(260, daily=0.002), _series(260, daily=0.0005))
    assert t['trend'] == 'alcista' and t['sma50'] > t['sma200'] and t['rsi14'] == 100.0
    assert t['rel_3m_pct'] > 0 and 'le gana' in txt and t['pct_from_52w_high'] == 0.0
    d, _ = technical_indicators(_series(260, daily=-0.002))
    assert d['trend'] == 'bajista' and d['max_drawdown_1y_pct'] < -30
    assert technical_indicators(_series(10)) == (None, '')


def test_pares_mediana_y_prima():
    me = {'available': True, 'pe_trailing': 40, 'gross_margin': 0.7, 'operating_margin': 0.4}
    peers = [('A', {'available': True, 'pe_trailing': 20, 'gross_margin': 0.5, 'market_cap_usd_b': 100}),
             ('B', {'available': True, 'pe_trailing': 30, 'gross_margin': 0.6, 'market_cap_usd_b': 50}),
             ('C', {'available': False})]
    r, txt = peer_table('X', me, peers)
    assert r['peers'] == ['A', 'B'] and r['pe_trailing']['median'] == 25
    assert 'prima 60 %' in txt and 'margen bruto 70.0 % vs mediana de pares 55.0 %' in txt
    assert peer_table('X', me, peers[:1]) == (None, '')


def test_guardian_no_acepta_porcentajes_ni_fechas_como_dinero():
    from core.numbers import evidence_numbers, unsupported_money
    vals = evidence_numbers([{'title': '', 'excerpt': 'rendimiento FCF 1.38 % · 2026-09-29 · P/FCF 12.5x'}])
    assert unsupported_money('vale $1.2T', vals) == ['$1.2T']
    assert unsupported_money('vale $9,999 mil millones', vals)


def test_errores_en_lenguaje_simple():
    from research.errors import friendly, run_hint
    assert 'saldo' in friendly('claude: Your credit balance is too low')[0]
    assert 'retirado' in friendly('gemini: 404 models/gemini-1.5 is not found')[0]
    assert 'presupuesto' in friendly('presupuesto diario agotado (≈$2.00 estimados)')[0]
    assert friendly('algo raro') == (None, None)
    assert run_hint([{'unresolved_questions': []}, 'modelo: 429 Too Many Requests'])[1].startswith('The AI provider')
