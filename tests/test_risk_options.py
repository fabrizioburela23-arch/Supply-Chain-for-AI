"""Reporte de riesgo (VaR) y reporte Vega/Kappa de opciones — sin red."""
import math
import os
import random
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATES = [f'2025-{m:02d}-{d:02d}' for m in range(1, 13) for d in range(1, 22)]


def _series(rets, p0=100.0):
    out, p = {}, p0
    for d, r in zip(DATES, rets):
        p *= (1 + r)
        out[d] = p
    return out


def _data(seed=7):
    rnd = random.Random(seed)
    mkt = [rnd.gauss(0.0004, 0.01) for _ in DATES]
    a = [1.5 * m + rnd.gauss(0, 0.008) for m in mkt]
    b = [rnd.gauss(0.0003, 0.02) for _ in DATES]
    return _series(a), _series(b), _series(mkt, 400)


def test_var_cvar_contribucion_y_beta():
    from core.risk_report import compute
    A, B, SPY = _data()
    r = compute({'A': A, 'B': B}, {'A': 10, 'B': 5}, {'A': 1.0, 'B': 1.0}, bench=SPY, horizon=10)
    assert r['ok'] and r['days'] == len(DATES) - 1
    v = r['var95']
    assert v['hist_1d_pct'] > 0 and v['cvar_1d_pct'] >= v['hist_1d_pct']      # CVaR ≥ VaR
    assert r['var99']['hist_1d_pct'] >= v['hist_1d_pct']
    assert abs(v['hist_nd_pct'] - v['hist_1d_pct'] * math.sqrt(10)) < 0.01     # √N
    assert abs(sum(p['risk_contrib_pct'] for p in r['positions']) - 100) < 0.1
    assert abs(sum(p['weight_pct'] for p in r['positions']) - 100) < 0.1
    wa = [p['weight_pct'] for p in r['positions'] if p['symbol'] == 'A'][0] / 100
    assert abs(r['beta_spy'] - wa * 1.5) < 0.15                                # beta = Σ w·β (A 1,5 · B 0)
    assert r['correlation']['matrix'][0][0] == 1.0
    assert r['max_drawdown_pct'] <= 0 and 0 <= r['backtest95']['breaches'] <= r['days']


def test_historia_insuficiente_se_dice():
    from core.risk_report import compute
    r = compute({'A': {'2025-01-01': 1, '2025-01-02': 2}}, {'A': 1}, {'A': 1})
    assert not r['ok'] and 'insuficiente' in r['error']


def test_build_report_excluye_y_valida_tickers():
    from core import risk_report
    A, B, SPY = _data(3)
    hist = {'AAA': A, 'SPY': SPY}

    def getter(url, params=None, timeout=None):
        sym = url.rsplit('/', 1)[1]
        h = hist.get(sym)
        if not h:
            return None, 'not found'
        ts = [int(date.fromisoformat(d).strftime('%s')) + 43200 for d in sorted(h)]
        return {'chart': {'result': [{'timestamp': ts, 'meta': {'currency': 'USD'},
                                      'indicators': {'quote': [{'close': [h[d] for d in sorted(h)]}]}}]}}, None
    risk_report._HIST_CACHE.clear()
    r = risk_report.build_report([{'symbol': 'AAA', 'shares': 10}, {'symbol': 'ZZZ', 'shares': 3},
                                  {'symbol': 'bad sym!', 'shares': 1}], getter=getter, fx_fn=lambda c: 1.0)
    assert r['ok'] and [p['symbol'] for p in r['positions']] == ['AAA']
    assert any(e['symbol'] == 'ZZZ' for e in r['excluded'])


def test_black_scholes_ejemplo_de_hull():
    from core.options import bs
    c, p = bs(42, 40, 0.5, 0.10, 0.20, 'call'), bs(42, 40, 0.5, 0.10, 0.20, 'put')
    assert round(c['price'], 2) == 4.76 and round(p['price'], 2) == 0.81
    # paridad put-call
    assert abs((c['price'] - p['price']) - (42 - 40 * math.exp(-0.05))) < 1e-9
    # Vega analítica ≈ numérica (por 1 punto de volatilidad)
    num = bs(42, 40, 0.5, 0.10, 0.2001, 'call')['price'] - bs(42, 40, 0.5, 0.10, 0.1999, 'call')['price']
    assert abs(c['vega'] - num * 50) < 1e-4
    # Gamma ≈ derivada numérica de Delta
    dg = (bs(42.01, 40, 0.5, 0.10, 0.2)['delta'] - bs(41.99, 40, 0.5, 0.10, 0.2)['delta']) / 0.02
    assert abs(c['gamma'] - dg) < 1e-4
    assert c['theta'] < 0 and 0 < c['delta'] < 1 and -1 < p['delta'] < 0


def test_reporte_vega_corta_iv_y_escenarios():
    from core.options import vega_report
    live = lambda s, e, k, kind: {'spot': 181.2, 'iv': 0.45 if kind == 'call' else 0.0, 'bid': 10, 'ask': 11}
    r = vega_report([{'symbol': 'NVDA', 'kind': 'call', 'strike': 200, 'expiry': '2027-01-15', 'contracts': 2},
                     {'symbol': 'NVDA', 'kind': 'put', 'strike': 150, 'expiry': '2027-01-15', 'contracts': -1},
                     {'symbol': 'x y', 'kind': 'call', 'strike': 1, 'expiry': '2027-01-15', 'contracts': 1}],
                    live=live, rate=(0.04, True), hvol=lambda s: 0.5, today=date(2026, 9, 29))
    assert r['ok'] and len(r['positions']) == 2 and r['excluded'][0]['reason'] == 'ticker inválido'
    put = [p for p in r['positions'] if p['kind'] == 'put'][0]
    assert put['vega_usd'] < 0 and put['iv_source'].startswith('histórica')        # vendida → Vega < 0
    sc = {s['shock_pts']: s['pnl_usd'] for s in r['vol_scenarios']}
    assert sc[2] > 0 > sc[-2] and abs(sc[2] - 2 * r['totals']['vega_usd']) < abs(r['totals']['vega_usd']) * 0.1


def test_endpoints_validan_el_cuerpo():
    import server
    c = server.app.test_client()
    assert c.post('/api/portfolio/risk_report', json={}).status_code == 400
    assert c.post('/api/portfolio/vega_report', json={'options': []}).status_code == 400
    assert c.get('/api/options/chain/bad%20sym!').status_code == 400
