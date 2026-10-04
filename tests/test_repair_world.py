"""tests/test_repair_world.py — W1 (misión de reparación 2026-10-04).

Producción: la API de mapas de GDELT (GEO 2.0) responde HTTP 404. Antes el
World Monitor la volvía a pedir cada 90 s, ocupando el acelerador COMPARTIDO de
GDELT (también lo usa la Sala de Situación) y mostrando "error" genérico. Ahora
tras N errores DEFINITIVOS seguidos la fuente queda en pausa 1 h con un mensaje
honesto y bilingüe; las capas curadas se declaran como lo que son.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import world as W  # noqa: E402
from tests.test_world import GDELT_PAYLOAD, SITUATION, NOW  # noqa: E402


@pytest.fixture(autouse=True)
def _iso(monkeypatch):
    W._reset_cache()
    W._GDELT_LAST[0] = 0.0
    monkeypatch.setattr(W, 'GDELT_MIN_GAP', 0.0)
    monkeypatch.setattr(W, '_situation', lambda: SITUATION)
    clock = {'t': NOW}
    monkeypatch.setattr(W, '_now', lambda: clock['t'])
    monkeypatch.delenv('WORLD_SOURCE_DOWN_AFTER', raising=False)
    monkeypatch.delenv('WORLD_SOURCE_DOWN_TTL', raising=False)
    yield clock
    W._reset_cache()


def _settle():
    """Espera los refrescos en segundo plano (world_events no los espera si ya hay caché)."""
    with W._LOCK:
        ths = list(W._INFLIGHT.values())
    for th in ths:
        th.join(5)


def _http(seq, calls):
    def fake(url, params=None, timeout=10):   # noqa: ARG001
        calls.append(url)
        r = seq[min(len(calls) - 1, len(seq) - 1)]
        return (GDELT_PAYLOAD, None) if r is None else (None, r)
    return fake


def test_w1_404_repetido_pausa_gdelt_sin_red_ni_acelerador(monkeypatch, _iso):
    calls, turns = [], []
    monkeypatch.setattr(W, '_http_get_json', _http(['http:404'], calls))
    real = W.gdelt_throttle
    monkeypatch.setattr(W, 'gdelt_throttle', lambda *a, **k: turns.append(1) or real(*a, **k))
    for _ in range(3):
        items, err = W._fetch_gdelt('conflict', '24h')
        assert items is None
    assert err.startswith('source_down:gdelt_geo'), err          # la 3.ª ya deja la fuente en pausa
    n_calls, n_turns = len(calls), len(turns)
    for _ in range(5):                                            # en pausa: ni red ni turno
        items, err = W._fetch_gdelt('unrest', '7d')
        assert items is None and err.startswith('source_down:gdelt_geo')
    assert (len(calls), len(turns)) == (n_calls, n_turns) == (3, 3)
    info = W.err_info(err)
    assert info['error_code'] == 'source_unavailable'
    assert 'HTTP 404' in info['error_es'] and 'cada hora' in info['error_es'] and 'USGS' in info['error_es']
    assert 'retired or moved' in info['error_en'] and 'every hour' in info['error_en']
    st = W.sources_state()['gdelt_geo']
    assert st['paused'] and st['fails'] == 3 and st['retry_at']
    # pasada la hora: UNA consulta de prueba; si responde, todo vuelve a la normalidad
    _iso['t'] = NOW + W.SOURCE_DOWN_TTL + 1
    monkeypatch.setattr(W, '_http_get_json', _http([None], calls))
    items, err = W._fetch_gdelt('conflict', '24h')
    assert err is None and items
    assert W.source_down('gdelt_geo') is None and W.sources_state()['gdelt_geo']['fails'] == 0


@pytest.mark.parametrize('transient', ['timeout', 'rate_limited', 'http:503', 'http:500', 'conn:api.gdeltproject.org'])
def test_w1_errores_pasajeros_nunca_pausan(monkeypatch, transient):
    calls = []
    monkeypatch.setattr(W, '_http_get_json', _http([transient], calls))
    for _ in range(6):
        _items, err = W._fetch_gdelt('conflict', '24h')
        assert err == transient
    assert W.source_down('gdelt_geo') is None and len(calls) == 6


def test_w1_403_dice_que_pide_credenciales(monkeypatch):
    monkeypatch.setattr(W, '_http_get_json', _http(['http:403'], []))
    for _ in range(3):
        _i, err = W._fetch_gdelt('trade', '24h')
    info = W.err_info(err)
    assert info['error_code'] == 'source_unavailable'
    assert 'credenciales' in info['error_es'] and 'no se contratan' in info['error_es']
    assert 'credentials' in info['error_en']


def test_w1_world_events_publica_retry_at_y_no_reintenta_cada_90s(monkeypatch, _iso):
    calls = []
    monkeypatch.setattr(W, '_http_get_json', _http(['http:404'], calls))
    for k in range(4):                                             # 3 refrescos fallidos → pausa
        _iso['t'] = NOW + k * (W.ERROR_TTL + 1)
        W.world_events(['conflict'], wait=5)
        _settle()
    out = W.world_events(['conflict'], wait=5)
    src = out['sources']['conflict']
    assert src['error_code'] == 'source_unavailable' and not src.get('pending'), src
    assert src.get('retry_at'), src
    n = len(calls)
    _iso['t'] += W.ERROR_TTL * 5                                   # 7,5 min después: sigue en pausa, sin red
    W.world_events(['conflict'], wait=5)
    _settle()
    assert len(calls) == n


def test_w1_capas_curadas_se_declaran_curadas():
    from core.geosit import CURATED_AS_OF
    out = W.world_events(['chokepoints', 'instability'], wait=0)
    for lyr in ('chokepoints', 'instability'):
        s = out['sources'][lyr]
        assert s['static'] is True and s['live'] is False and s['curated_as_of'] == CURATED_AS_OF
        assert 'news_live' in s


def test_w1_noticias_gdelt_doc_en_pausa_no_tocan_la_red(monkeypatch):
    from core import geosit as G
    for _ in range(3):
        W.source_result('gdelt_doc', 'http:404')

    def boom(*a, **k):
        raise AssertionError('no debe consultar GDELT DOC en pausa')
    monkeypatch.setattr(G.requests, 'get', boom)
    assert G._gdelt_activity('"Taiwan Strait"') is None
    st = G._news_status()
    assert st['live'] is False and st['error_code'] == 'source_unavailable' and 'GDELT DOC' in st['error_es']
    out = W.world_events(['chokepoints'], wait=0)
    assert out['sources']['chokepoints']['news_live'] is False


def test_w1_prewarm_no_espera_y_resume_estados(monkeypatch):
    monkeypatch.setattr(W, '_http_get_json', _http([None], []))
    res = W.prewarm()
    assert set(res) == set(W.LIVE_LAYERS)
    assert res['chokepoints'] == 'ok'
