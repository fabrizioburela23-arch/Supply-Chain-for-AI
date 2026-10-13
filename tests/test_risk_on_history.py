"""tests/test_risk_on_history.py — el riesgo sobre la historia correcta (BRECHAS bloque 2: L2-01, L3-14, L2-M1, L2-12).

  · L2-01/L3-14: una acción PLANA en yenes con un yen que se mueve tiene riesgo en dólares (antes ~0: se aplicaba la
    tasa de HOY a toda la serie); un activo plano con FX que cae 10 % pierde 10 % en dólares;
  · L2-M1: una acción asiática que reacciona a Wall Street al día siguiente tiene beta ≈ 1 (Dimson), no ~0;
    la volatilidad de una cartera mixta recupera la covarianza perdida por el desfase horario;
  · L2-12: con historia propia en la base, el reporte la usa SIN red y lo dice (source + as_of por serie).
Sin red (todo simulado). La parte de base se salta sin DATABASE_URL."""
import math
import os
import random
import sys
from datetime import date, datetime, timedelta, timezone

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')


@pytest.fixture(autouse=True)
def _limpia_cache():
    from core import risk_report
    risk_report._HIST_CACHE.clear()
    risk_report._HIST_META.clear()
    yield
    risk_report._HIST_CACHE.clear()
    risk_report._HIST_META.clear()


def _bdays(n, end=None):
    end = end or date.today() - timedelta(days=1)
    out, d = [], end
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d -= timedelta(days=1)
    return sorted(out)


def _chart(dates, closes, currency='USD', adj=None):
    ts = [int(datetime(d.year, d.month, d.day, 15, tzinfo=timezone.utc).timestamp()) for d in dates]
    return {'chart': {'result': [{'timestamp': ts, 'meta': {'currency': currency, 'gmtoffset': 0,
                                                            'currentTradingPeriod': {'regular': {'start': 0, 'end': 1}}},
                                  'indicators': {'quote': [{'close': closes, 'open': closes, 'high': closes,
                                                            'low': closes, 'volume': [1000] * len(closes)}],
                                                 'adjclose': [{'adjclose': adj or closes}]}}]}}


def _getter(series):
    """series: {símbolo: (dates, closes, currency)} → getter compatible con core.company_data._get_json."""
    def g(url, params=None, timeout=None):
        sym = url.rsplit('/', 1)[-1]
        if sym not in series:
            return None, 'upstream 404'
        d, c, cur = series[sym]
        return _chart(d, c, cur), None
    return g


def _walk(n, sigma, seed, start=100.0):
    rnd = random.Random(seed)
    r = [rnd.gauss(0, sigma) for _ in range(n - 1)]
    px = [start]
    for x in r:
        px.append(px[-1] * (1 + x))
    return px, r


# ── L2-01 / L3-14: tipo de cambio diario ─────────────────────────────────────
def test_accion_plana_en_yenes_tiene_el_riesgo_del_yen():
    from core.risk_report import build_report
    d = _bdays(250)
    fx, _r = _walk(250, 0.008, 1, start=0.0067)
    spy, _ = _walk(250, 0.01, 2, start=500)
    g = _getter({'FLAT.T': (d, [1000.0] * 250, 'JPY'), 'JPYUSD=X': (d, fx, 'USD'), 'SPY': (d, spy, 'USD')})
    rep = build_report([{'symbol': 'FLAT.T', 'shares': 100}], getter=g, fx_fn=lambda c: 0.0067)
    assert rep['ok'], rep
    pos = rep['positions'][0]
    assert pos['fx_method'] == 'daily' and rep['fx']['FLAT.T']['method'] == 'daily'
    # vol anual ≈ 0,8 % · √252 ≈ 12,7 % (antes: 0 % — la tasa de hoy aplicada a toda la serie)
    assert 9.0 < rep['vol_ann_pct'] < 16.5, rep['vol_ann_pct']
    assert pos['value_usd'] == pytest.approx(100 * 1000 * fx[-1], abs=0.01)


def test_sin_serie_de_fx_usa_la_tasa_de_hoy_y_lo_dice():
    from core.risk_report import build_report
    d = _bdays(250)
    spy, _ = _walk(250, 0.01, 3, start=500)
    px, _ = _walk(250, 0.01, 4, start=1000)
    g = _getter({'NOFX.T': (d, px, 'JPY'), 'SPY': (d, spy, 'USD')})        # sin JPYUSD=X
    rep = build_report([{'symbol': 'NOFX.T', 'shares': 10}], getter=g, fx_fn=lambda c: 0.0067)
    assert rep['ok']
    assert rep['fx']['NOFX.T']['method'] == 'spot' and 'HOY' in rep['fx']['NOFX.T']['note_es']
    assert rep['positions'][0]['fx_method'] == 'spot'


def test_activo_plano_con_fx_que_cae_10_pierde_10_en_dolares():
    from core.risk_report import compute
    dates = [d.isoformat() for d in _bdays(120)]
    flat = {d: 100.0 for d in dates}
    fx = {d: 1.0 - 0.1 * i / (len(dates) - 1) for i, d in enumerate(dates)}      # cae 10 % en el período
    rep = compute({'EU': flat}, {'EU': 10}, {'EU': fx})
    assert rep['ok']
    eq = 1.0
    for i in range(1, len(dates)):
        eq *= (100 * fx[dates[i]]) / (100 * fx[dates[i - 1]])
    assert eq == pytest.approx(0.9, rel=1e-9)
    assert rep['portfolio_value_usd'] == pytest.approx(10 * 100 * 0.9, rel=1e-9)
    assert rep['max_drawdown_pct'] == pytest.approx(-10.0, abs=0.01)


def test_align_fx_rellena_feriados_pero_no_huecos_largos():
    from core.risk_report import align_fx
    px = {'2026-01-05': 1, '2026-01-06': 1, '2026-01-20': 1}
    fx = {'2026-01-02': 0.5, '2026-01-06': 0.6}
    al = align_fx(px, fx)
    assert al == {'2026-01-05': 0.5, '2026-01-06': 0.6}           # el 20 queda fuera (14 días sin tasa)


def test_reporte_de_cartera_valora_cada_fecha_con_su_tipo_de_cambio(monkeypatch):
    from core import portfolio_report, risk_report
    dates = [d.isoformat() for d in _bdays(40)]
    flat = {d: 100.0 for d in dates}
    fxd = {d: 1.0 - 0.1 * i / (len(dates) - 1) for i, d in enumerate(dates)}
    monkeypatch.setattr(portfolio_report, '_histories', lambda syms, rng, fetch=None: {
        s: ((flat, 'EUR') if s == 'EUX.DE' else ({d: 400.0 for d in dates}, 'USD')) for s in syms})
    monkeypatch.setattr(risk_report, 'fx_series', lambda cur, rng='1y', getter=None: (fxd, {'source': 't', 'as_of': dates[-1]}))
    rep = portfolio_report.build([{'symbol': 'EUX.DE', 'label': 'EU', 'shares': 10}], period='month',
                                 fx_fn=lambda c: 1.0, advisor=lambda *a, **k: {'ok': False},
                                 news=lambda *a, **k: {'items': []})
    c = rep['contributions'][0]
    a, b = fxd[rep['performance']['period_from']], fxd[dates[-1]]
    assert c['change_pct'] == pytest.approx((b / a - 1) * 100, abs=0.01)
    assert c['value_usd'] == pytest.approx(10 * 100 * b, abs=0.01)


# ── L2-M1: bolsas que cierran antes que Nueva York ───────────────────────────
def _lagged_case(n=300, seed=7):
    dates = [d.isoformat() for d in _bdays(n)]
    spy, r = _walk(n, 0.01, seed, start=400)
    bench = dict(zip(dates, spy))
    # la acción asiática del día t refleja la sesión de EE.UU. del día t−1
    rnd = random.Random(seed + 1)
    asia = [100.0]
    for i in range(1, n):
        prev_us = r[i - 2] if i >= 2 else 0.0
        asia.append(asia[-1] * (1 + prev_us + rnd.gauss(0, 0.002)))
    return dates, bench, dict(zip(dates, asia)), dict(zip(dates, spy))


def test_beta_de_dimson_para_una_accion_asiatica():
    from core.risk_report import compute
    dates, bench, asia, _us = _lagged_case()
    same = compute({'ASIA.T': asia}, {'ASIA.T': 10}, {'ASIA.T': 1.0}, bench=bench)
    dim = compute({'ASIA.T': asia}, {'ASIA.T': 10}, {'ASIA.T': 1.0}, bench=bench, nonsync={'ASIA.T'})
    assert abs(same['beta_spy']) < 0.2                        # el error de hoy: beta ~0
    assert dim['beta_spy'] == pytest.approx(1.0, abs=0.15)    # Dimson: ≈ 1
    assert dim['nonsync_adjusted'] and dim['nonsync']['beta_method'] == 'dimson'
    assert abs(dim['nonsync']['beta_same_day']) < 0.2
    assert not same['nonsync_adjusted']


def test_volatilidad_de_cartera_mixta_recupera_la_covarianza_perdida():
    from core.risk_report import compute
    dates, bench, asia, us = _lagged_case(n=400, seed=11)
    sh = {'ASIA.T': 1000 / asia[dates[-1]], 'US': 1000 / us[dates[-1]]}       # 50/50
    rep = compute({'ASIA.T': asia, 'US': us}, sh, {'ASIA.T': 1.0, 'US': 1.0}, bench=bench, nonsync={'ASIA.T'})
    true_vol = 0.01 * math.sqrt(252) * 100                                       # misma exposición al mismo factor
    same = rep['nonsync']['vol_ann_same_day_pct']
    assert same < 0.85 * true_vol                                                # mismo día: ≈ 0,71 × la real
    assert rep['vol_ann_pct'] == pytest.approx(true_vol, rel=0.15)
    assert rep['vol_ann_pct'] > same


def test_build_report_marca_no_sincronizadas_por_bolsa():
    from core.instruments import nonsync
    assert nonsync('2330.TW') and nonsync('8035.T') and nonsync('SAP.DE')
    assert not nonsync('NVDA') and not nonsync('SHOP.TO') and not nonsync('TSM')


# ── L2-12: historia propia primero ───────────────────────────────────────────
@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from ontology.db import _get_engine, init_schema
    assert init_schema(retries=1)
    yield _get_engine()


def _store(sym, dates, closes, currency='USD'):
    from core import prices_store
    from ontology.db import session_scope
    rows = [{'date': d, 'open': c, 'high': c, 'low': c, 'close': c, 'adj_close': c, 'volume': 10} for d, c in zip(dates, closes)]
    with session_scope() as s:
        return prices_store.ingest_series(s, sym, rows, currency=currency)


def test_reporte_usa_la_historia_propia_sin_red_y_lo_dice(db, monkeypatch):
    from core import company_data, prices_store, risk_report
    tag = str(random.randint(10 ** 6, 10 ** 7))
    sym = f'H{tag}'
    d = _bdays(260)
    px, _ = _walk(260, 0.012, 5, start=50)
    _store(sym, d, px)
    calls = []
    spy, _ = _walk(260, 0.01, 6, start=500)

    def net(url, params=None, timeout=None):
        calls.append(url.rsplit('/', 1)[-1])
        if url.endswith('/SPY'):
            return _chart(d, spy), None
        return None, 'upstream 404'
    monkeypatch.setattr(company_data, '_get_json', net)
    h, cur = risk_report.fetch_history(sym, '1y')
    assert len(h) == 260 and cur == 'USD' and sym not in calls
    m = risk_report.history_meta(sym, '1y')
    assert m['source'] == 'khipus_eod:yahoo' and m['as_of'] == d[-1].isoformat()
    rep = risk_report.build_report([{'symbol': sym, 'shares': 3}], fx_fn=lambda c: 1.0)
    assert rep['ok'], rep
    assert rep['series'][sym]['source'] == 'khipus_eod:yahoo'
    assert rep['series']['SPY']['source'] == 'yahoo_live'
    assert 'Historia propia de Khipus' in rep['source'] and sym in rep['source']
    assert rep['source_es'] == rep['source'] and rep['source_en'].startswith('Khipus own history') \
        and sym in rep['source_en']                                      # bilingüe (revisión batch E)
    assert sym not in calls
    assert prices_store.history(f'NOPE{tag}', '1y') is None                 # sin filas → respaldo en vivo


def test_historia_vieja_o_corta_no_se_usa(db):
    from core import prices_store
    tag = str(random.randint(10 ** 6, 10 ** 7))
    old = [d - timedelta(days=30) for d in _bdays(260)]                       # la última fila tiene 30 días
    _store(f'OLD{tag}', old, [10.0 + i * 0.01 for i in range(260)])
    assert prices_store.history(f'OLD{tag}', '1y') is None
    short = _bdays(40)
    _store(f'SHO{tag}', short, [10.0] * 40)
    assert prices_store.history(f'SHO{tag}', '1y') is None                    # no cubre 1 año
    assert prices_store.history(f'SHO{tag}', '1mo') is not None               # sí cubre 1 mes


def test_serie_guardada_sin_ajustar_conserva_el_aviso(monkeypatch):
    """Revisión batch E: una serie de la base SIN cierre ajustado de Yahoo sigue marcada «sin ajustar» en el reporte
    (antes la ruta de la base decía siempre adjusted=True y el aviso se perdía)."""
    from core import prices_store, risk_report
    d = _bdays(5)
    h = {x.isoformat(): 10.0 + i for i, x in enumerate(d)}
    monkeypatch.setattr(prices_store, 'history', lambda s, r='1y', today=None: (
        h, 'USD', {'source': 'khipus_eod:yahoo', 'as_of': d[-1].isoformat(), 'adjusted': False, 'n': len(h)}))
    out, cur = risk_report.fetch_history('RAWX', '1y')
    assert out == h and risk_report.history_meta('RAWX', '1y')['adjusted'] is False
