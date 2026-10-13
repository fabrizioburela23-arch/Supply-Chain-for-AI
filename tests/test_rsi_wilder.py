"""tests/test_rsi_wilder.py — L2-11: el RSI que leen los analistas es el de WILDER (el de las plataformas de bolsa),
y los técnicos usan cierres AJUSTADOS (L2-03). Sin red ni base."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# serie de referencia clásica (StockCharts/Wilder) y su RSI(14) de Wilder sin redondeos intermedios
CLOSES = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28,
          46.00, 46.03, 46.41, 46.22, 45.64, 46.21, 46.25, 45.71, 46.45, 45.78, 45.35, 44.03, 44.18, 44.22, 44.57,
          43.42, 42.66, 43.13]
WILDER = [70.46, 66.25, 66.48, 69.35, 66.29, 57.91, 62.88, 63.21, 56.01, 62.34, 54.67, 50.39, 40.02, 41.49, 41.90,
          45.50, 37.32, 33.09, 37.79]


def _cutler(xs, n=14):
    g = sum(max(xs[i] - xs[i - 1], 0) for i in range(len(xs) - n, len(xs)))
    lo = sum(max(xs[i - 1] - xs[i], 0) for i in range(len(xs) - n, len(xs)))
    return 100 - 100 / (1 + g / lo)


def test_rsi_coincide_con_la_referencia_de_wilder():
    from research.analytics import _rsi
    got = [_rsi(CLOSES[:k + 1]) for k in range(14, len(CLOSES))]
    assert len(got) == len(WILDER)
    for g, w in zip(got, WILDER):
        assert abs(g - w) <= 0.06, (g, w)


def test_ya_no_es_la_media_simple_de_cutler():
    from research.analytics import _rsi
    # al final de la serie Wilder y Cutler difieren claramente (el viejo cálculo daba otro número)
    assert abs(_rsi(CLOSES) - round(_cutler(CLOSES), 1)) > 1.0


def test_casos_borde():
    from research.analytics import _rsi
    assert _rsi([1.0] * 10) is None                         # menos de n+1 cierres
    assert _rsi([float(i) for i in range(1, 40)]) == 100.0  # sin bajadas
    assert _rsi([float(i) for i in range(40, 1, -1)]) == 0.0


def test_el_texto_de_evidencia_dice_wilder_y_el_guardian_lo_respeta():
    from core.numbers import unsupported_in
    from research.analytics import technical_indicators
    series = [(i, 100 + (i % 7) - (i % 5) * 0.8 + i * 0.05) for i in range(260)]
    out, txt = technical_indicators(series)
    assert 'RSI(14) de Wilder' in txt
    rsi = out['rsi14']
    assert unsupported_in(f'El RSI(14) de Wilder está en {rsi}.', txt) == []
    assert unsupported_in('El RSI está en 99,9.', txt) != []


def test_los_tecnicos_usan_cierres_ajustados_en_el_respaldo_en_vivo(monkeypatch):
    """L2-03: research/context._fetch_candles toma adjclose de Yahoo (no 'close' crudo) y dice la fuente."""
    from core import company_data, prices_store
    from research import context
    monkeypatch.setattr(prices_store, 'history', lambda *a, **k: None)
    ts = [1_700_000_000 + 86400 * i for i in range(5)]

    def fake(url, params=None, timeout=None):
        return {'chart': {'result': [{'timestamp': ts, 'meta': {'currency': 'USD'},
                                      'indicators': {'quote': [{'close': [400, 404, 101, 102, 103]}],
                                                     'adjclose': [{'adjclose': [100, 101, 101, 102, 103]}]}}]}}, None
    monkeypatch.setattr(company_data, '_get_json', fake)
    c = context._fetch_candles('ZZZ')
    assert [x[1] for x in c] == [100, 101, 101, 102, 103]       # sin el "desplome" falso del split 4:1
    assert c.source == 'yahoo_live' and c.as_of


def test_los_tecnicos_leen_la_historia_propia_cuando_existe(monkeypatch):
    from core import prices_store
    from research import context
    monkeypatch.setattr(prices_store, 'history', lambda sym, rng='1y', today=None: (
        {'2026-10-08': 10.0, '2026-10-09': 11.0}, 'USD',
        {'source': 'khipus_eod:yahoo', 'as_of': '2026-10-09', 'adjusted': True}))
    c = context._fetch_candles('NVDA')
    assert [x[1] for x in c] == [10.0, 11.0]
    assert c.source == 'khipus_eod:yahoo' and c.as_of == '2026-10-09'


def test_screener_usa_adjclose(monkeypatch):
    from core import screener

    class R:
        def json(self):
            closes = [400.0] * 10 + [100.0] * 30
            adj = [100.0] * 40
            return {'chart': {'result': [{'indicators': {'quote': [{'close': closes}], 'adjclose': [{'adjclose': adj}]}}]}}
    monkeypatch.setattr(screener._requests, 'get', lambda *a, **k: R())
    m = screener._momentum('ZZZ')
    assert m['r60'] is None or m['r60'] == 0.0
    assert m['r20'] == 0.0 and m['r5'] == 0.0
