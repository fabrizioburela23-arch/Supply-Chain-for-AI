"""tests/test_options_greeks_totals.py — batch I2 · BRECHAS L2-10 (core/options.py).

  · Black-Scholes-Merton con rendimiento de dividendo q: ejemplo de libro (Hull), paridad put-call con dividendos y
    griegas = diferencias finitas; con q = 0 es exactamente el Black-Scholes de antes.
  · Totales: nunca se suman acciones de subyacentes distintos (Δ en acciones y Γ solo POR SUBYACENTE); la delta en
    dólares sí; una cadena en EUR se convierte a USD y se rotula. Sin red.
"""
import math
import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import options as O  # noqa: E402


def test_hull_indice_con_dividendos():
    # Hull, Options, Futures and Other Derivatives (ej. 17.1): S=930, K=900, r=8 %, q=3 %, σ=20 %, T=2/12 → c ≈ 51,83
    c = O.bs(930, 900, 2 / 12, 0.08, 0.20, 'call', q=0.03)
    assert c['price'] == pytest.approx(51.83, abs=0.01)
    d1 = (math.log(930 / 900) + (0.08 - 0.03 + 0.02) * 2 / 12) / (0.2 * math.sqrt(2 / 12))
    assert d1 == pytest.approx(0.5444, abs=1e-4)
    assert c['delta'] == pytest.approx(math.exp(-0.03 * 2 / 12) * 0.5 * (1 + math.erf(d1 / math.sqrt(2))))


@pytest.mark.parametrize('S,K,T,r,sig,q', [(100, 95, 0.5, 0.04, 0.3, 0.02), (50, 60, 1.2, 0.01, 0.45, 0.05),
                                          (200, 200, 0.1, 0.05, 0.2, 0.0)])
def test_paridad_put_call_con_dividendos_y_griegas_por_diferencias_finitas(S, K, T, r, sig, q):
    c, p = O.bs(S, K, T, r, sig, 'call', q), O.bs(S, K, T, r, sig, 'put', q)
    assert c['price'] - p['price'] == pytest.approx(S * math.exp(-q * T) - K * math.exp(-r * T), abs=1e-10)
    h = 1e-4
    for kind, g in (('call', c), ('put', p)):
        up, dn = O.bs(S + h, K, T, r, sig, kind, q), O.bs(S - h, K, T, r, sig, kind, q)
        assert g['delta'] == pytest.approx((up['price'] - dn['price']) / (2 * h), abs=1e-6)
        assert g['gamma'] == pytest.approx((up['delta'] - dn['delta']) / (2 * h), abs=1e-5)
        vu, vd = O.bs(S, K, T, r, sig + h, kind, q), O.bs(S, K, T, r, sig - h, kind, q)
        assert g['vega'] == pytest.approx((vu['price'] - vd['price']) / (2 * h) / 100, abs=1e-6)
        tu, td = O.bs(S, K, T + h, r, sig, kind, q), O.bs(S, K, T - h, r, sig, kind, q)
        assert g['theta'] == pytest.approx(-(tu['price'] - td['price']) / (2 * h) / 365, abs=1e-6)


def test_con_q_cero_es_el_black_scholes_de_siempre():
    a = O.bs(42, 40, 0.5, 0.10, 0.2, 'call')
    assert a == O.bs(42, 40, 0.5, 0.10, 0.2, 'call', q=0.0)
    assert a['price'] == pytest.approx(4.76, abs=0.01)                 # Hull 15.6 sin dividendos


def test_dividend_yield_de_yahoo():
    assert O.dividend_yield({'trailingAnnualDividendYield': 0.0042}) == 0.0042
    assert O.dividend_yield({'dividendYield': 0.42}) == pytest.approx(0.0042)      # Yahoo lo da en %
    assert O.dividend_yield({'dividendYield': 'x'}) is None and O.dividend_yield({}) is None
    assert O.dividend_yield({'trailingAnnualDividendYield': 3.5}) is None          # imposible: no se usa


LIVE = {'NVDA': {'spot': 180.0, 'iv': 0.45, 'currency': 'USD', 'dividend_yield': 0.0002},
        'BRK-B': {'spot': 480.0, 'iv': 0.20, 'currency': 'USD'},
        'ASML.AS': {'spot': 700.0, 'iv': 0.35, 'currency': 'EUR', 'dividend_yield': 0.009}}
OPTS = [{'symbol': 'NVDA', 'kind': 'call', 'strike': 200, 'expiry': '2027-01-15', 'contracts': 3},
        {'symbol': 'NVDA', 'kind': 'put', 'strike': 150, 'expiry': '2027-01-15', 'contracts': -2},
        {'symbol': 'BRK-B', 'kind': 'call', 'strike': 500, 'expiry': '2027-01-15', 'contracts': 1},
        {'symbol': 'ASML.AS', 'kind': 'call', 'strike': 720, 'expiry': '2027-01-15', 'contracts': 2}]


def _rep(opts=OPTS, fx=None):
    return O.vega_report(opts, live=lambda s, e, k, kind: dict(LIVE[s]), rate=(0.04, True), hvol=lambda s: None,
                         today=date(2026, 10, 13), fx_fn=fx or (lambda c: {'EUR': 1.10}.get(c)))


def test_totales_por_subyacente_nunca_mezclan_acciones_de_empresas_distintas():
    r = _rep()
    t = r['totals']
    assert t['delta_shares'] is None and t['gamma'] is None and t['mixed_underlyings'] and t['n_underlyings'] == 3
    by = {u['symbol']: u for u in r['by_underlying']}
    assert set(by) == {'NVDA', 'BRK-B', 'ASML.AS'}
    rows = r['positions']
    nv = [p for p in rows if p['symbol'] == 'NVDA']
    assert by['NVDA']['delta_shares'] == pytest.approx(sum(p['delta_shares'] for p in nv), abs=0.02)
    # delta en dólares = Σ Δ·S·contratos·100·fx, y ESA sí se suma entre empresas
    assert t['dollar_delta_usd'] == pytest.approx(sum(p['dollar_delta_usd'] for p in rows), abs=0.05)
    asml = next(p for p in rows if p['symbol'] == 'ASML.AS')
    g = O.bs(700.0, 720, O.years_to('2027-01-15', date(2026, 10, 13)), 0.04, 0.35, 'call', 0.009)
    assert asml['dollar_delta_usd'] == pytest.approx(g['delta'] * 700 * 200 * 1.10, abs=0.01)
    assert asml['dollar_gamma_1pct_usd'] == pytest.approx(0.5 * g['gamma'] * 7.0 ** 2 * 200 * 1.10, abs=0.01)


def test_cadena_en_euros_se_convierte_a_usd_y_se_rotula():
    r = _rep()
    asml = next(p for p in r['positions'] if p['symbol'] == 'ASML.AS')
    assert asml['currency'] == 'EUR' and asml['fx_to_usd'] == 1.10
    assert asml['value_usd'] == pytest.approx(asml['value_local'] * 1.10, abs=0.02)
    assert r['currencies'] == ['EUR'] and asml['dividend_yield_pct'] == 0.9
    assert 'proveedor' in asml['dividend_source']
    brk = next(p for p in r['positions'] if p['symbol'] == 'BRK-B')
    assert brk['dividend_yield_pct'] == 0 and brk['dividend_source'].startswith('sin dato')
    # sin tipo de cambio: fuera y dicho (nunca en USD como si nada)
    r2 = _rep(fx=lambda c: None)
    assert any(e['symbol'] == 'ASML.AS' and 'tipo de cambio' in e['reason'] for e in r2['excluded'])
    assert r2['totals']['value_usd'] == pytest.approx(sum(p['value_usd'] for p in r2['positions']), abs=0.02)


def test_un_solo_subyacente_mantiene_acciones_equivalentes_y_gamma():
    r = _rep(OPTS[:2])
    t = r['totals']
    assert not t['mixed_underlyings'] and t['n_underlyings'] == 1
    assert t['delta_shares'] == pytest.approx(sum(p['delta_shares'] for p in r['positions']), abs=0.02)
    assert t['gamma'] == pytest.approx(sum(p['gamma'] for p in r['positions']), abs=1e-3)
    # escenarios de volatilidad en USD con el mismo q
    sc = {s['shock_pts']: s['pnl_usd'] for s in r['vol_scenarios']}
    assert sc[2] > 0 > sc[-2] if t['vega_usd'] > 0 else sc[2] < 0 < sc[-2]


def test_ui_usa_la_delta_en_dolares_cuando_hay_varias_empresas():
    js = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'engine', 'riskreport.js'),
              encoding='utf-8').read()
    assert "chip('dollar_delta')" in js and "t.delta_shares != null" in js and "'Delta en dólares', 'Dollar Delta'" in js
    assert "'solo por empresa (abajo)', 'per company only (below)'" in js
    ex = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'engine', 'explain.js'),
              encoding='utf-8').read()
    for k in ('dollar_delta', 'vol_ewma', 'shrinkage', 'var_nd', 'sharpe_arith', 'liquidity', 'rp_capped'):
        i = ex.index(f'    {k}: {{')
        blk = ex[i:i + 2500]
        assert 'es: { t:' in blk and 'en: { t:' in blk, k
