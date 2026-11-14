"""tests/test_crypto_symbol_normalize.py — una venta de «ETHUSD» (símbolo de POSICIÓN de Alpaca, sin barra) salía con
tif 'day' y Alpaca la rechazaba: «invalid crypto time_in_force» (orden real fallida, 2026-10-30). Ahora la validación de
la orden (el único lugar: brokerage.service._spec) convierte las bases de cripto conocidas a su par y fuerza gtc."""
import pytest

from brokerage import service as S


@pytest.mark.parametrize('raw,pair', [('ETHUSD', 'ETH/USD'), ('eth/usd', 'ETH/USD'), ('BTCUSDT', 'BTC/USDT'),
                                      ('SOLUSD', 'SOL/USD'), ('ETH/USD', 'ETH/USD')])
def test_crypto_without_slash_becomes_pair_and_gtc(raw, pair):
    spec, err = S._spec(raw, 'sell', 100, None, 'market', None, 'day')
    assert err is None and spec['symbol'] == pair and spec['time_in_force'] == 'gtc'


@pytest.mark.parametrize('raw', ['AAPL', 'NVDA', 'USD', 'BASUSD', 'TSM'])
def test_stocks_and_unknown_symbols_are_untouched(raw):
    spec, err = S._spec(raw, 'buy', 100, None, 'market', None, 'day')
    assert err is None and spec['symbol'] == raw and spec['time_in_force'] == 'day'


def test_historia_de_cripto_usa_el_simbolo_de_yahoo():
    """Riesgo de la cartera con ETHUSD (2026-11-14): la historia se pide como ETH-USD."""
    from core import risk_report as rr
    assert rr.yahoo_symbol('ETHUSD') == 'ETH-USD' and rr.yahoo_symbol('BTC/USD') == 'BTC-USD'
    assert rr.yahoo_symbol('NVDA') == 'NVDA' and rr.yahoo_symbol('AUSD') == 'AUSD'
    seen = []

    def getter(url, params=None, timeout=None):
        seen.append(url)
        return {'chart': {'result': [{'timestamp': [1700000000, 1700086400], 'meta': {'currency': 'USD'},
                                      'indicators': {'quote': [{'close': [2000.0, 2010.0]}],
                                                     'adjclose': [{'adjclose': [2000.0, 2010.0]}]}}]}}, None
    rr._HIST_CACHE.clear()
    h, cur = rr.fetch_history('ETHUSD', '1y', getter=getter)
    assert seen and seen[0].endswith('/ETH-USD') and len(h) == 2 and cur == 'USD'
