"""tests/test_price_sim.py — simulación de precio de la app (core/price_sim + herramienta simulate_price, 2026-11-06).
«¿Va a seguir cayendo? ¿es el piso?» lo responde la APP con una distribución de probabilidades hecha con datos reales."""
import os
import sys
from datetime import date, timedelta

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('SECRET_KEY', 'test')

from core import price_sim as PS  # noqa: E402


def _prices(n=500, seed=1, crash=True):
    rng = np.random.default_rng(seed)
    r = rng.standard_t(4, n) * 0.015
    if crash:
        r[-1] = -0.09                              # una caída de un día como la del 5-nov
        r[200] = -0.08
    p = 100 * np.exp(np.cumsum(r))
    d0 = date(2024, 11, 5)
    days, d = [], d0
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d.isoformat())
        d += timedelta(days=1)
    return dict(zip(days, p.tolist()))


def test_salidas_coherentes_y_reproducibles():
    pr = _prices()
    a = PS.simulate('X', pr, n_paths=4000)
    b = PS.simulate('X', pr, n_paths=4000)
    assert a['horizons'] == b['horizons']                         # semilla fija: el mismo número dos veces
    last = a['technical']['last_close']
    for h in a['horizons']:
        assert h['p5'] < h['p25'] < h['p50'] < h['p75'] < h['p95']
        assert 0 <= h['prob_today_is_the_low_pct'] <= h['prob_low_within_5pct_of_today_pct'] <= 100
        assert h['lowest_close_p50'] <= last
        touch = [v['pct'] for v in h['prob_touch'].values()]
        assert all(0 <= x <= 100 for x in touch)
    hs = a['horizons']
    assert hs[0]['prob_today_is_the_low_pct'] >= hs[-1]['prob_today_is_the_low_pct']   # más tiempo, menos probable
    assert a['technical']['last_day_change_pct'] == pytest.approx(-8.61, abs=0.05)
    assert any(e['drop_pct'] <= -7 for e in a['big_drop_episodes'])
    assert 'NO es un pronóstico' in a['assumptions_es'] or 'NO un pronóstico' in a['assumptions_es']


def test_salto_de_resultados_con_reacciones_reales():
    pr = _prices()
    days = sorted(pr)
    vals = [pr[d] for d in days]
    for i, mv in ((101, 0.08), (164, -0.07), (227, 0.06), (290, -0.09)):    # reacciones grandes (amc → día siguiente)
        vals = vals[:i] + [v * (1 + mv) for v in vals[i:]]
    pr = dict(zip(days, vals))
    last = date.fromisoformat(days[-1])
    past = [(date.fromisoformat(days[i]), 'amc') for i in (100, 163, 226, 289)]
    out = PS.simulate('X', pr, earnings=(past, (last + timedelta(days=7), 'amc'), 'test'), n_paths=4000)
    ev = out['earnings_event']
    assert ev and len(ev['past_reactions_pct']) == 4 and 1 <= ev['reaction_trading_day'] <= 10
    assert set(out['by_earnings_outcome']) == {'good', 'bad'}
    g, b = out['by_earnings_outcome']['good'], out['by_earnings_outcome']['bad']
    assert g['p50'] > b['p50'] and g['prob_today_is_the_low_pct'] >= b['prob_today_is_the_low_pct']


def test_sin_resultados_no_hay_salto_y_historia_corta_falla():
    out = PS.simulate('X', _prices(), n_paths=2000)
    assert out['earnings_event'] is None and out['by_earnings_outcome'] is None
    with pytest.raises(ValueError):
        PS.simulate('X', dict(list(_prices().items())[:100]))


def test_calendario_de_finnhub():
    rows = {'earningsCalendar': [{'date': '2026-08-26', 'hour': 'amc', 'epsActual': 1.0},
                                 {'date': '2026-11-17', 'hour': 'amc', 'epsActual': None},
                                 {'date': '2027-02-24', 'hour': 'amc'}]}
    past, nxt, src = PS.earnings_calendar('NVDA', getter=lambda u: (rows, None), today=date(2026, 11, 6))
    assert past == [(date(2026, 8, 26), 'amc')] and nxt == (date(2026, 11, 17), 'amc') and 'Finnhub' in src


def test_herramienta_en_el_chat_y_el_mcp():
    from core import khipu_chat as K
    from mcp_server import ops  # noqa: F401  (registra la herramienta)
    from mcp_server.tools import REGISTRY
    assert 'simulate_price' in K.MCP_READ_TOOLS and 'simulate_price' in REGISTRY
    src = open(K.__file__, encoding='utf-8').read()
    assert '¿ya tocó fondo' in src and 'prob_today_is_the_low_pct' in src


def test_fechas_de_reportes_de_la_sec():
    """Respaldo de Finnhub: 8-K con ítem 2.02 → fecha y hora (amc/bmo) del reporte (2026-11-07)."""
    import datetime as dt
    from core import sec

    class R:
        def __init__(self, j):
            self.ok, self._j = True, j

        def json(self):
            return self._j
    today = dt.date.today()
    d1, d2, d3 = (today - dt.timedelta(days=n) for n in (300, 200, 100))
    sub = {'filings': {'recent': {
        'form': ['8-K', '8-K', '10-Q', '8-K', '8-K'],
        'items': ['2.02,9.01', '5.02', '', '2.02', '2.02,7.01'],
        'filingDate': [d3.isoformat(), d3.isoformat(), d2.isoformat(), d2.isoformat(), d1.isoformat()],
        'acceptanceDateTime': [f'{d3}T16:21:00.000Z', f'{d3}T10:00:00.000Z', '', f'{d2}T08:05:00.000Z', f'{d1}T12:00:00.000Z']}}}

    def get(url, headers=None, timeout=None):
        if url.endswith('company_tickers.json'):
            return R({'0': {'ticker': 'ZZTEST', 'cik_str': 123}})
        return R(sub)
    sec._TICKERS.update(map=None, ts=0.0)
    sec._CACHE.clear()
    out = sec.earnings_dates('ZZTEST', getter=get)
    assert out == [(d1, ''), (d2, 'bmo'), (d3, 'amc')]          # el 8-K 5.02 y el 10-Q no cuentan
    sec._TICKERS.update(map=None, ts=0.0)
    sec._CACHE.clear()
