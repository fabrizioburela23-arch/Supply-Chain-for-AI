"""core/live_fundamentals.py (2026-10-05, "en vivo siempre lo que varía"): margen, crecimiento, ingresos y
empleados REALES de todas las cotizadas, por tandas en segundo plano; el NRS del servidor usa el margen real."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import live_fundamentals as LF  # noqa: E402


def setup_function(_):
    LF._STATE.update(data={}, running=False, last_run=None, last_error=None, runs=0)


def teardown_function(_):
    LF._STATE.update(data={}, running=False)


def _fake_profile(sym):
    if sym == 'NVDA':
        return {'available': True, 'operating_margin': 61.2, 'revenue_growth_q': 56, 'employees': 36000,
                'revenue_ttm_usd_b': 187.1, 'source': 'yahoo', 'as_of': '2026-10-05T20:00:00Z'}
    return {'available': False}


def test_tandas_sin_repetir_y_lo_ultimo_bueno_no_se_pierde(monkeypatch):
    monkeypatch.setattr(LF, '_universe', lambda: {'Nvidia': 'NVDA', 'AMD': 'AMD', 'TSMC': 'TSM'})
    r = LF.refresh(profile_fn=_fake_profile, now=1000.0, n=2)
    assert r['ok'] == 1 and r['no_data'] == 1 and r['universe'] == 3
    r2 = LF.refresh(profile_fn=_fake_profile, now=1001.0, n=2)      # la siguiente tanda toma la que faltaba
    assert r2['ok'] + r2['no_data'] == 1
    d = LF.get_all()
    assert set(d['fund']) == {'Nvidia'} and d['fund']['Nvidia']['operating_margin'] == 61.2
    assert LF.live_margin('Nvidia') == 0.612 and LF.live_margin('AMD') is None
    # un fallo posterior NO borra el dato bueno
    LF.refresh(profile_fn=lambda s: {'available': False}, now=1000.0 + LF.MAX_AGE_S + 5, n=3)
    assert LF.live_margin('Nvidia') == 0.612


def test_nrs_del_servidor_usa_el_margen_real(monkeypatch):
    from core.world import client_nrs
    node = {'id': 'Nvidia', 'country': 'EEUU', 'margin': -1.0}          # catálogo absurdo
    sin = client_nrs(node, 0)
    LF._STATE['data']['Nvidia'] = {'operating_margin': 61.2, 'ts': 1.0}
    con = client_nrs(node, 0)
    assert sin == 8 + 0 + 20 + 0 + 4 and con == 8 + 0 + 0 + 0 + 4


def test_tras_un_redeploy_la_tanda_se_triplica_hasta_cubrir_todo(monkeypatch):
    # un redeploy borra la memoria: con tandas de 40 cada 5 min tardaba ~1 h en volver a cubrir 568 empresas
    uni = {f'N{i}': f'T{i}' for i in range(LF.BATCH * LF.CATCHUP + 10)}
    monkeypatch.setattr(LF, '_universe', lambda: uni)
    prof = lambda s: {'available': True, 'operating_margin': 10.0}  # noqa: E731
    r = LF.refresh(profile_fn=prof, now=1000.0)
    assert r['batch'] == LF.BATCH * LF.CATCHUP and r['ok'] == LF.BATCH * LF.CATCHUP
    r = LF.refresh(profile_fn=prof, now=1001.0)                    # quedan 10 nunca pedidas → sigue en modo rápido
    assert r['ok'] == 10
    r = LF.refresh(profile_fn=prof, now=1002.0)                    # ya están todas → tanda normal
    assert r['batch'] == LF.BATCH
