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
