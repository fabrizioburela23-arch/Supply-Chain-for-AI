"""tests/test_screen_stocks.py — herramienta del chat `screen_stocks` (2026-11-03): «¿qué empresas con potencial de
crecimiento están baratas?». Usa los fundamentales EN VIVO (core/live_fundamentals) con P/E adelantado, crecimiento
implícito del consenso y precio objetivo; NUNCA inventa una proyección a 2027."""
import pytest

from core import khipu_chat as K
from core import live_fundamentals as lf


@pytest.fixture
def fund(monkeypatch):
    snap = K._snapshot()
    ids = list(snap['nodes'])[:40]
    data = {}
    for k, i in enumerate(ids):
        data[i] = {'symbol': f'T{k}', 'pe_forward': 10.0 + k, 'pe_trailing': 20.0 + 2 * k, 'price': 100.0,
                   'target_mean': 100.0 + k, 'week52_high': 120.0, 'revenue_growth': 5.0 + k, 'recommendation': 'buy',
                   'source': 'yahoo', 'as_of': '2026-11-03T00:00:00Z', 'ts': 1}
    monkeypatch.setitem(lf._STATE, 'data', data)
    return ids


def test_registered_and_advertised():
    assert 'screen_stocks' in K._EXTRA
    assert 'screen_stocks' in K._NOTE_FN and 'screen_stocks' in K._TOOL_HUMAN


def test_peg_orders_cheapest_per_growth_and_explains_limits(fund):
    r = K.x_screen_stocks(by='peg', limit=5)
    pegs = [x['peg'] for x in r['items']]
    assert pegs == sorted(pegs) and all(p is not None for p in pegs)
    it = r['items'][0]
    assert it['eps_growth_next_year_pct'] == round((it['pe_trailing'] / it['pe_forward'] - 1) * 100, 1)
    assert 'NOT 2027' in r['explain'] and r['universe_with_forward_pe'] == 40


def test_modes_and_bad_values(fund, monkeypatch):
    assert K.x_screen_stocks(by='raro')['by'] == 'peg'
    up = K.x_screen_stocks(by='upside', limit=3)['items']
    assert [x['upside_to_target_pct'] for x in up] == sorted((x['upside_to_target_pct'] for x in up), reverse=True)
    lf._STATE['data'][fund[0]]['pe_forward'] = -5          # P/E negativo → fuera
    lf._STATE['data'][fund[1]]['pe_forward'] = 900         # absurdo → fuera
    assert K.x_screen_stocks(limit=20)['universe_with_forward_pe'] == 38


def test_warming_up_is_an_honest_failure(monkeypatch):
    monkeypatch.setitem(lf._STATE, 'data', {})
    with pytest.raises(K.ToolFailure):
        K.x_screen_stocks()
