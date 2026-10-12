"""Bloque 0 (docs/BRECHAS_V2.md) — matemática del comité, confianza y cartera:
L2-05 (mitad "no validado" aunque muerda el tope), L2-06 (convicción por
analista, no por claim), L2-08 (independencia por proveedor), L2-17 (mismo
denominador para riesgo y peso), L2-19 (unidades declaradas, sin adivinar)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── L2-05 ───────────────────────────────────────────────────────────────────
@pytest.mark.parametrize('vol', [10.0, 12.0, 15.0, 20.0, 40.0])
def test_no_validado_es_siempre_la_mitad_del_validado(vol):
    from research.committee import compute_sizing, mandate_from
    m = mandate_from({})                                    # 2 % de riesgo, tope 10 %, vol mínima 10 %
    full = compute_sizing('BUY', vol, m)
    half = compute_sizing('BUY', vol, m, validated=False)
    assert half['target_weight_pct'] == pytest.approx(full['target_weight_pct'] * 0.5, abs=1e-3)


def test_orden_tamano_mitad_tope_queda_en_el_memo():
    from research.committee import compute_sizing, mandate_from
    s = compute_sizing('BUY', 10.0, mandate_from({}), equity=100000.0, validated=False)
    assert s['sizing_order'] == ['size', 'halve', 'cap'] and s['unvalidated_factor'] == 0.5
    assert s['raw_weight_pct'] == pytest.approx(20.0)        # 1) 2 % ÷ 10 %
    assert s['halved_weight_pct'] == pytest.approx(10.0)     # 2) mitad
    assert s['cap_pct'] == pytest.approx(5.0)                # 3) tope 10 % → 5 %
    assert s['target_weight_pct'] == pytest.approx(5.0) and s['notional'] == pytest.approx(5000.0)
    assert s['capped_by'] == 'max_position' and s['unvalidated'] is True
    assert [x[:2] for x in s['steps_es'] if x[:2] in ('1)', '2)', '3)')] == ['1)', '2)', '3)']
    v = compute_sizing('BUY', 10.0, mandate_from({}), equity=100000.0)
    assert v['target_weight_pct'] == pytest.approx(10.0) and v['notional'] == pytest.approx(10000.0)


# ── L2-06 ───────────────────────────────────────────────────────────────────
def _c(i, agent, stance, hz, conf):
    return {'id': f'c{i}', 'agent_type': agent, 'stance': stance, 'horizon': hz, 'confidence': conf}


def test_un_solo_analista_con_muchas_claims_no_pesa_como_el_comite():
    from research.committee import conviction_by_horizon
    one_agent = [_c(i, 'fundamental', 'positive', 'LONG_TERM', 0.6) for i in range(4)]
    four_agents = [_c(i, a, 'positive', 'LONG_TERM', 0.6)
                   for i, a in enumerate(('fundamental', 'technical', 'news', 'supply_chain'))]
    c1, _ = conviction_by_horizon(one_agent)
    c4, _ = conviction_by_horizon(four_agents)
    assert c1['LONG_TERM']['score'] == pytest.approx(100 * 0.6 / 1.6, abs=0.1)      # 37.5: una voz
    assert c4['LONG_TERM']['score'] == pytest.approx(100 * 2.4 / 3.4, abs=0.1)      # 70.6: cuatro voces
    assert c1['LONG_TERM']['n_agents'] == 1 and c1['LONG_TERM']['agents']['fundamental']['n_claims'] == 4
    assert c1['LONG_TERM']['aggregation'] == 'per_agent'


def test_postura_del_agente_es_su_media_ponderada():
    from research.committee import conviction_by_horizon
    claims = [_c(1, 'fundamental', 'positive', 'MEDIUM_TERM', 0.9), _c(2, 'fundamental', 'negative', 'MEDIUM_TERM', 0.3),
              _c(3, 'technical', 'negative', 'MEDIUM_TERM', 0.6)]
    conv, _ = conviction_by_horizon(claims)
    f = conv['MEDIUM_TERM']['agents']['fundamental']
    assert f['weight'] == pytest.approx(0.6) and f['stance'] == pytest.approx((0.9 - 0.3) / 1.2)
    # 100 · (0.6·0.5 − 0.6·1) / (1.2 + 1)
    assert conv['MEDIUM_TERM']['score'] == pytest.approx(100 * (0.3 - 0.6) / 2.2, abs=0.1)


# ── L2-08 ───────────────────────────────────────────────────────────────────
def test_dos_endpoints_de_yahoo_son_una_sola_fuente():
    from research.confidence import compute_confidence
    support = [{'source_type': 'financials', 'reference': 'https://finance.yahoo.com/quote/NVDA/financials',
                'reliability': 0.9},
               {'source_type': 'market', 'reference': 'https://finance.yahoo.com/quote/NVDA', 'reliability': 0.85},
               {'source_type': 'catalog', 'reference': 'khipus:catalog:Nvidia', 'reliability': 0.5}]
    _s, parts = compute_confidence(support, [], 0.8, 1.0)
    assert parts['distinct_sources'] == 2 and parts['components']['independence'] == pytest.approx(0.667)
    only_yahoo, p2 = compute_confidence(support[:2], [], 0.8, 1.0)
    assert p2['distinct_sources'] == 1 and only_yahoo <= 0.6


def test_www_y_subdominios_del_mismo_medio_cuentan_una_vez():
    from research.confidence import _key, compute_confidence
    assert _key({'reference': 'https://www.reuters.com/a'}) == _key({'reference': 'https://reuters.com/b'})
    assert _key({'reference': 'https://query1.finance.yahoo.com/v7/x'}) == 'yahoo'
    assert _key({'reference': 'yahoo:financials:NVDA'}) == 'yahoo'
    assert _key({'reference': 'https://www.bbc.co.uk/n'}) == 'bbc.co.uk'
    news = [{'source_type': 'news', 'reference': 'https://www.reuters.com/a', 'reliability': 0.8},
            {'source_type': 'news', 'reference': 'https://reuters.com/b', 'reliability': 0.8}]
    _s, parts = compute_confidence(news, [], 0.8, 1.0)
    assert parts['distinct_sources'] == 1


# ── L2-17 ───────────────────────────────────────────────────────────────────
def _risk_cash(positions, horizon=10, **_k):
    vals = {'NVDA': 2000.0, 'AMD': 4000.0, 'MSFT': 4000.0}
    rc = {'NVDA': 26.0, 'AMD': 37.0, 'MSFT': 37.0}
    syms = [p['symbol'] for p in positions]
    tot = sum(vals[s] for s in syms)
    return {'ok': True, 'portfolio_value_usd': tot, 'vol_ann_pct': 25.0, 'max_drawdown_pct': -20.0,
            'var95': {'hist_1d_pct': 2.0, 'hist_1d_usd': 200.0}, 'beta_spy': 1.1, 'return_ann_pct': 10.0,
            'diversification_ratio': 1.2, 'as_of': '2026-10-12', 'source': 'test',
            'positions': [{'symbol': s, 'shares': 1, 'price': 1, 'value_usd': vals[s], 'weight_pct': vals[s] / tot * 100,
                           'vol_ann_pct': 30.0, 'risk_contrib_pct': rc[s]} for s in syms],
            'correlation': {'symbols': [], 'matrix': []}, 'excluded': []}


def test_con_mucho_efectivo_no_pide_reducir_por_riesgo_si_frente_a_lo_invertido_no_sobra():
    """NVDA = 20 % de lo invertido y 26 % del riesgo invertido; con 50 % en efectivo su peso total es 10 %.
    Antes: 26 > 2×10 → "reducir". Ahora se compara con 20 % (26 < 40) → sin acción por riesgo."""
    from core import portfolio_advisor as pa
    pos = [{'symbol': 'NVDA', 'shares': 1}, {'symbol': 'AMD', 'shares': 1}, {'symbol': 'MSFT', 'shares': 1}]
    a = pa.analyze(pos, profile={'risk': 'agresivo'}, risk_fn=_risk_cash, board_fn=lambda: ({}, []),
                   cash_usd=10000.0)
    nv = next(r for r in a['positions'] if r['symbol'] == 'NVDA')
    assert nv['weight_pct'] == pytest.approx(10.0) and nv['weight_invested_pct'] == pytest.approx(20.0)
    assert not [x for x in a['actions'] if x['symbol'] == 'NVDA' and x['kind'] == 'reduce']


# ── L2-19 ───────────────────────────────────────────────────────────────────
def test_roe_roic_en_fraccion_siempre_se_pasan_a_porcentaje():
    from research.analytics import fundamental_ratios
    fin = {'available': True, 'years': [2023, 2024], 'revenue': [10e9, 12e9], 'roic': [0.2, 6.0], 'roe': [0.1, 0.25]}
    r, txt = fundamental_ratios(fin, {})
    assert r['roic_pct'] == pytest.approx(600.0) and r['roe_pct'] == pytest.approx(25.0)


def test_pares_respetan_el_porcentaje_del_perfil_en_vivo():
    from research.analytics import peer_table
    me = {'available': True, 'pe_trailing': 20, 'gross_margin': 1.5, 'revenue_growth': 250.0}
    peers = [('A', {'available': True, 'pe_trailing': 20, 'gross_margin': 40.0, 'revenue_growth': 10.0}),
             ('B', {'available': True, 'pe_trailing': 30, 'gross_margin': 60.0, 'revenue_growth': 20.0})]
    r, txt = peer_table('X', me, peers)
    assert r['gross_margin']['entity'] == pytest.approx(1.5)            # antes 150 %
    assert r['revenue_growth']['entity'] == pytest.approx(250.0)
    assert 'margen bruto 1.5 % vs mediana de pares 50.0 %' in txt
