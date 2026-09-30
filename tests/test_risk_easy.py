"""Reporte de riesgo "fácil": montos en DÓLARES y códigos de error estables — sin red."""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.test_risk_options import _data  # noqa: E402


def _getter_for(hist):
    def getter(url, params=None, timeout=None):
        sym = url.rsplit('/', 1)[1]
        h = hist.get(sym)
        if not h:
            return None, 'not found'
        ts = [int(date.fromisoformat(d).strftime('%s')) + 43200 for d in sorted(h)]
        return {'chart': {'result': [{'timestamp': ts, 'meta': {'currency': 'USD'},
                                      'indicators': {'quote': [{'close': [h[d] for d in sorted(h)]}]}}]}}, None
    return getter


def test_montos_en_dolares_se_convierten_con_el_ultimo_cierre_real():
    from core import risk_report
    A, B, SPY = _data(5)
    risk_report._HIST_CACHE.clear()
    r = risk_report.build_report([{'symbol': 'AAA', 'usd': 6000, 'label': 'Alfa'},
                                  {'symbol': 'BBB', 'usd': 4000}],
                                 getter=_getter_for({'AAA': A, 'BBB': B, 'SPY': SPY}), fx_fn=lambda c: 1.0)
    assert r['ok']
    assert abs(r['portfolio_value_usd'] - 10000) < 0.05
    w = {p['symbol']: p['weight_pct'] for p in r['positions']}
    assert abs(w['AAA'] - 60) < 0.01 and abs(w['BBB'] - 40) < 0.01
    conv = {c['symbol']: c for c in r['converted']}
    last = max(A)
    assert conv['AAA']['date'] == last and abs(conv['AAA']['price_usd'] - A[last]) < 1e-3
    assert abs(conv['AAA']['shares'] - 6000 / A[last]) < 1e-4
    assert r['labels']['AAA'] == 'Alfa'


def test_dolares_y_acciones_se_suman_y_fx_aplica():
    from core import risk_report
    A, B, SPY = _data(6)
    risk_report._HIST_CACHE.clear()
    # moneda "local" con tipo de cambio 0,5 → $1.000 compran el doble de acciones
    r = risk_report.build_report([{'symbol': 'AAA', 'shares': 2}, {'symbol': 'AAA', 'usd': 1000}],
                                 getter=_getter_for({'AAA': A, 'SPY': SPY}), fx_fn=lambda c: 0.5)
    assert r['ok']
    last = max(A)
    assert abs(r['portfolio_value_usd'] - (2 * A[last] * 0.5 + 1000)) < 0.05
    assert abs(r['converted'][0]['price_usd'] - A[last] * 0.5) < 1e-3


def test_codigos_de_error_estables():
    from core import risk_report
    risk_report._HIST_CACHE.clear()
    r = risk_report.build_report([{'symbol': 'AAA', 'usd': 0}, {'symbol': 'bad sym!', 'usd': 100}],
                                 getter=_getter_for({}), fx_fn=lambda c: 1.0)
    assert not r['ok'] and r['error_code'] == 'no_positions'
    r = risk_report.build_report([{'symbol': 'AAA', 'usd': 500}], getter=_getter_for({}), fx_fn=lambda c: 1.0)
    assert not r['ok'] and r['error_code'] == 'data_unavailable'
    assert r['excluded'][0]['reason_code'] == 'no_history'
    long_ = _data(8)[0]
    risk_report._HIST_CACHE.clear()
    # dos historias sin suficientes días en común → short_history
    shifted = {k.replace('2025-', '2024-'): v for k, v in long_.items()}
    r = risk_report.build_report([{'symbol': 'AAA', 'usd': 500}, {'symbol': 'CCC', 'usd': 500}],
                                 getter=_getter_for({'AAA': long_, 'CCC': shifted}), fx_fn=lambda c: 1.0)
    assert not r['ok'] and r['error_code'] == 'short_history'


def test_chain_meta_distingue_proveedor_caido_de_sin_opciones():
    from core.options import chain_meta, vega_report
    assert chain_meta('NVDA', fetch=lambda u, p: None)['reason'] == 'data_unavailable'
    empty = {'optionChain': {'result': [{'quote': {'regularMarketPrice': 10}, 'expirationDates': []}]}}
    assert chain_meta('XYZ', fetch=lambda u, p: empty)['reason'] == 'no_options'
    ok = {'optionChain': {'result': [{'quote': {'regularMarketPrice': 10}, 'expirationDates': [1800000000],
                                      'strikes': [9, 10, 11]}]}}
    m = chain_meta('XYZ', fetch=lambda u, p: ok)
    assert m['available'] and 'reason' not in m and m['strikes'] == [9.0, 10.0, 11.0]
    r = vega_report([{'symbol': 'NVDA', 'kind': 'call', 'strike': 100, 'expiry': '2027-01-15', 'contracts': 1}],
                    live=lambda *a: {}, rate=(0.0, False), hvol=lambda s: None, today=date(2026, 9, 30))
    assert not r['ok'] and r['error_code'] == 'none_valued'


def test_endpoint_acepta_usd():
    import server
    from core import risk_report
    A, B, SPY = _data(9)
    orig = risk_report.fetch_history
    hist = {'AAA': A, 'SPY': SPY}
    risk_report.fetch_history = lambda s, rng='1y', getter=None: (hist.get(s, {}), 'USD')
    try:
        from unittest import mock
        with mock.patch('core.quotes._fx_to_usd', lambda c: 1.0):
            r = server.app.test_client().post('/api/portfolio/risk_report',
                                              json={'positions': [{'symbol': 'AAA', 'usd': 2500}]})
        d = r.get_json()
        assert r.status_code == 200 and d['ok'] and abs(d['portfolio_value_usd'] - 2500) < 0.05
    finally:
        risk_report.fetch_history = orig
