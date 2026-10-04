"""tests/test_repair_prices.py — Misión de reparación (2026-10-04), R9 · precios en vivo (hallazgos de la revisión)."""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import quotes  # noqa: E402


@pytest.fixture(autouse=True)
def _limpio():
    quotes.live_cache_clear()
    quotes._INTL_CACHE.clear()
    yield
    quotes.live_cache_clear()
    quotes._INTL_CACHE.clear()


class _R:
    def __init__(self, data):
        self._d = data

    def json(self):
        return self._d


def test_r9_londres_en_peniques_se_divide_por_100_antes_del_tipo_de_cambio(monkeypatch):
    asked = []
    monkeypatch.setattr(quotes, '_fx_to_usd', lambda cur: asked.append(cur) or 1.30)
    monkeypatch.setattr(quotes._requests, 'get', lambda url, **kw: _R({'chart': {'result': [{
        'meta': {'currency': 'GBp', 'regularMarketPrice': 1250.0, 'regularMarketTime': 1700000000, 'marketState': 'CLOSED'},
        'indicators': {'quote': [{'close': [1234.0, 1250.0]}]}}]}}))
    q = quotes.fetch_quote_intl('BA.L')
    assert asked == ['GBP']                                   # la moneda ENTERA, nunca 'GBp'
    assert q['live'] == pytest.approx(12.5 * 1.30) and q['prev'] == pytest.approx(12.34 * 1.30)
    assert q['currency'] == 'GBP' and q['converted'] is True and q['minor_unit'] == 'GBp'
    quotes._INTL_CACHE.clear()
    monkeypatch.setattr(quotes._requests, 'get', lambda url, **kw: _R({'chart': {'result': [{
        'meta': {'currency': 'JPY', 'regularMarketPrice': 3000.0}, 'indicators': {'quote': [{'close': [2900.0, 3000.0]}]}}]}}))
    monkeypatch.setattr(quotes, '_fx_to_usd', lambda cur: 0.0067)
    q2 = quotes.fetch_quote_intl('6758.T')
    assert q2['live'] == pytest.approx(3000 * 0.0067) and q2['minor_unit'] is None


def test_r9_finnhub_no_se_consulta_para_tickers_de_otras_bolsas(monkeypatch):
    import core.config
    from core.providers.market import FinnhubProvider
    monkeypatch.setattr(core.config, 'FINNHUB', 'fh-test-key')
    calls = []

    def raw(tk):
        calls.append(tk)
        return {'c': 10.0, 'pc': 9.5, 't': 1700000000}, None
    monkeypatch.setattr(quotes, '_fetch_quote_raw', raw)
    p = FinnhubProvider()
    assert p.get_quote('BA.L') is None and p.get_quote('6758.T') is None and calls == []
    assert p.get_quote('AAPL') is not None and calls == ['AAPL']


def test_r9_un_lote_que_no_termino_no_se_cachea_como_completo():
    from tests.test_quotes_live import FakeRegistry
    reg = FakeRegistry(hang='BBB', hang_s=0.6)
    r1 = quotes.fetch_quotes_live(['AAA', 'BBB', 'CCC'], registry=reg, deadline=0.15)
    assert r1['partial'] is True and 'BBB' not in r1['quotes'] and {'AAA', 'CCC'} <= set(r1['quotes'])
    assert frozenset(['AAA', 'BBB', 'CCC']) not in quotes._LIVE_CACHE['batches']       # no se "congela" truncado
    time.sleep(0.9)
    r2 = quotes.fetch_quotes_live(['AAA', 'BBB', 'CCC'], registry=reg, deadline=0.15)
    assert r2['partial'] is False and 'BBB' in r2['quotes']


def test_r9_las_capitalizaciones_llevan_la_hora_real_del_precio(monkeypatch):
    from core import live_caps
    monkeypatch.setattr(live_caps, '_symbols_by_id', lambda: {'Nvidia': 'NVDA'})
    monkeypatch.setattr(live_caps, '_daily_outcomes', lambda now=None: None)
    live_caps.refresh(fetch=lambda syms: {'NVDA': {'price': 100.0, 'price_usd': 100.0, 'currency': 'USD', 'mcap_b': 1.0,
                                                    'ts': 1700000000, 'market_state': 'CLOSED', 'change_pct': 1.0}})
    c = live_caps.get_caps(start=False)['caps']['Nvidia']
    assert c['price_ts'] == 1700000000 and c['market_state'] == 'CLOSED'
