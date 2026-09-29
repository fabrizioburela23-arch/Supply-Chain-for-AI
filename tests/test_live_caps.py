"""Capitalización EN VIVO de todo el grafo (core/live_caps + lote Yahoo)."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_refresh_mapea_simbolos_a_ids_y_no_borra_lo_bueno():
    from core import live_caps as lc
    lc._STATE.update(caps={}, as_of=None, ts=0.0, running=False, error=None)
    lc.refresh(fetch=lambda syms: {'AVGO': {'mcap_b': 1105.2, 'price': 235.4, 'currency': 'USD',
                                            'change_pct': 1.2}})
    st = lc.get_caps(start=False)
    assert st['caps']['Broadcom']['mcap_b'] == 1105.2 and st['n'] >= 1 and st['as_of']
    # un fallo total posterior NO borra el último dato bueno
    lc.refresh(fetch=lambda syms: {})
    st = lc.get_caps(start=False)
    assert st['caps']['Broadcom']['mcap_b'] == 1105.2 and st['error']


def test_lote_yahoo_convierte_moneda_y_omite_sin_dato(monkeypatch):
    from core import quotes

    class R:
        status_code = 200

        def __init__(self, rows):
            self._rows = rows

        def json(self):
            return {'quoteResponse': {'result': self._rows}}

    class S:
        def get(self, url, params=None, timeout=None):
            return R([{'symbol': 'AVGO', 'marketCap': 1.1052e12, 'currency': 'USD', 'regularMarketPrice': 235.4},
                      {'symbol': '2330.TW', 'marketCap': 3.0e13, 'currency': 'TWD', 'regularMarketPrice': 1150},
                      {'symbol': 'XXX'}])
    monkeypatch.setattr(quotes, '_yahoo_session', lambda: (S(), 'crumb'))
    monkeypatch.setattr(quotes, '_fx_to_usd', lambda cur: 1.0 if cur == 'USD' else 0.031)
    out = quotes.fetch_quotes_batch_yahoo(['AVGO', '2330.TW', 'XXX'])
    assert out['AVGO']['mcap_b'] == 1105.2
    assert out['2330.TW']['mcap_b'] == round(3.0e13 * 0.031 / 1e9, 2)
    assert 'XXX' not in out


def test_endpoint_devuelve_estado(monkeypatch):
    import server
    from core import live_caps as lc
    lc._STATE.update(caps={'Broadcom': {'mcap_b': 1105.2}}, as_of='2026-09-29T00:00:00+00:00',
                     ts=time.time(), running=False, error=None)
    r = server.app.test_client().get('/api/market/live_caps')
    assert r.status_code == 200 and r.get_json()['caps']['Broadcom']['mcap_b'] == 1105.2
