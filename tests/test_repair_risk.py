"""tests/test_repair_risk.py — Misión de reparación (2026-10-04), P1 · Motor de riesgo.

Sin red. Referencia independiente con numpy (ya instalado por matrix/).
"""
import math
import os
import sys
from datetime import date, timedelta

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _dates(n, start=date(2025, 10, 1)):
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _prices(rets, dates, p0=100.0):
    out, p = {dates[0]: p0}, p0
    for i, r in enumerate(rets):
        p *= (1 + r)
        out[dates[i + 1]] = p
    return out


def _world(seed=42, n=251):
    rng = np.random.default_rng(seed)
    m = rng.normal(0.0004, 0.01, n - 1)
    a = 1.5 * m + rng.normal(0, 0.006, n - 1)
    b = 0.5 * m + rng.normal(0, 0.012, n - 1)
    d = _dates(n)
    return _prices(a, d), _prices(b, d), _prices(m, d, 400.0), d


# ════════════════════════════════════════════════════════════════════════════
# D1 · Referencia numpy + alineación de fechas + zona horaria de la bolsa + "ajustado"
# ════════════════════════════════════════════════════════════════════════════

def test_d1_el_motor_coincide_con_numpy():
    from core.risk_report import compute
    A, B, SPY, d = _world()
    r = compute({'A': A, 'B': B}, {'A': 3, 'B': 7}, {}, bench=SPY)
    common = sorted(set(A) & set(B))
    ra = np.array([A[common[i]] / A[common[i - 1]] - 1 for i in range(1, len(common))])
    rb = np.array([B[common[i]] / B[common[i - 1]] - 1 for i in range(1, len(common))])
    rm = np.array([SPY[common[i]] / SPY[common[i - 1]] - 1 for i in range(1, len(common))])
    va, vb = 3 * A[common[-1]], 7 * B[common[-1]]
    w = np.array([va, vb]) / (va + vb)
    rp = w[0] * ra + w[1] * rb
    # (el reporte redondea: beta/corr a 3 decimales, % a 3 decimales, vol a 2)
    assert abs(r['beta_spy'] - np.cov(rp, rm, ddof=1)[0, 1] / np.var(rm, ddof=1)) < 6e-4
    assert abs(r['corr_spy'] - np.corrcoef(rp, rm)[0, 1]) < 6e-4
    assert abs(r['correlation']['matrix'][0][1] - np.corrcoef(ra, rb)[0, 1]) < 6e-4
    assert abs(r['var95']['hist_1d_pct'] / 100 + np.quantile(rp, 0.05)) < 1e-5
    q = np.quantile(rp, 0.05)
    assert abs(r['var99']['hist_1d_pct'] / 100 + np.quantile(rp, 0.01)) < 1e-5
    assert abs(r['var95']['cvar_1d_pct'] / 100 + rp[rp <= q].mean()) < 1e-5
    assert abs(r['vol_ann_pct'] / 100 - rp.std(ddof=1) * math.sqrt(252)) < 1e-4


def test_d1_cartera_solo_spy_tiene_beta_y_correlacion_1_y_dice_cuantos_dias_emparejo():
    from core.risk_report import compute
    _a, _b, SPY, d = _world()
    r = compute({'SPY': SPY}, {'SPY': 1}, {}, bench=SPY)
    assert r['beta_spy'] == 1.0 and r['corr_spy'] == 1.0
    assert r['bench_overlap_days'] == len(SPY) - 1
    assert r['aligned_dates']['SPY'] == {'from': d[0], 'to': d[-1], 'n': len(d)}


def test_d1_un_indice_corrido_un_dia_hunde_la_correlacion_y_se_ve_en_los_dias_emparejados():
    from core.risk_report import compute
    A, _b, SPY, d = _world()
    keys = sorted(SPY)
    shifted = {keys[i + 1]: SPY[keys[i]] for i in range(len(keys) - 1)}     # misma serie, +1 día
    r0 = compute({'A': A}, {'A': 1}, {}, bench=SPY)
    r1 = compute({'A': A}, {'A': 1}, {}, bench=shifted)
    assert r0['corr_spy'] > 0.8 and abs(r1['corr_spy']) < 0.25
    assert r1['bench_overlap_days'] < r0['bench_overlap_days']


def test_d1_la_fecha_de_la_vela_usa_la_zona_horaria_de_la_bolsa():
    from datetime import datetime, timezone

    from core.risk_report import _HIST_CACHE, fetch_history, history_meta
    _HIST_CACHE.clear()
    # Sídney (UTC+11): la sesión del 2 de junio abre a las 23:00 UTC del 1 de junio
    ts = [int(datetime(2026, 6, d, 23, 0, tzinfo=timezone.utc).timestamp()) for d in (1, 2, 3)]

    def getter(url, params=None, timeout=None):
        return {'chart': {'result': [{'timestamp': ts, 'meta': {'currency': 'AUD', 'gmtoffset': 39600,
                                                                 'exchangeTimezoneName': 'Australia/Sydney'},
                                      'indicators': {'quote': [{'close': [10.0, 11.0, 12.0]}],
                                                     'adjclose': [{'adjclose': [10.0, 11.0, 12.0]}]}}]}}, None
    h, cur = fetch_history('XYZ.AX', '1y', getter=getter)
    assert sorted(h) == ['2026-06-02', '2026-06-03', '2026-06-04'] and cur == 'AUD'
    m = history_meta('XYZ.AX', '1y')
    assert m['adjusted'] is True and m['tz'] == 'Australia/Sydney' and m['gmtoffset'] == 39600
    # EE.UU. (13:30 UTC, offset −4 h): misma fecha
    _HIST_CACHE.clear()
    ts2 = [int(datetime(2026, 6, d, 13, 30, tzinfo=timezone.utc).timestamp()) for d in (1, 2)]
    h2, _ = fetch_history('ABC', '1y', getter=lambda u, params=None, timeout=None: ({'chart': {'result': [{
        'timestamp': ts2, 'meta': {'currency': 'USD', 'gmtoffset': -14400},
        'indicators': {'quote': [{'close': [1.0, 2.0]}], 'adjclose': [{'adjclose': [1.0, 2.0]}]}}]}}, None))
    assert sorted(h2) == ['2026-06-01', '2026-06-02']


def test_d1_sin_adjclose_se_rotula_no_ajustado():
    from core.risk_report import _HIST_CACHE, build_report
    _HIST_CACHE.clear()
    A, _b, SPY, d = _world()

    def getter(url, params=None, timeout=None):
        sym = url.rsplit('/', 1)[1]
        src = A if sym == 'AAA' else SPY if sym == 'SPY' else None
        if src is None:
            return None, 'upstream 404'
        ks = sorted(src)
        from datetime import datetime, timezone
        ts = [int(datetime.fromisoformat(k).replace(hour=13, minute=30, tzinfo=timezone.utc).timestamp()) for k in ks]
        ind = {'quote': [{'close': [src[k] for k in ks]}]}
        if sym == 'SPY':
            ind['adjclose'] = [{'adjclose': [src[k] for k in ks]}]
        return {'chart': {'result': [{'timestamp': ts, 'meta': {'currency': 'USD', 'gmtoffset': -14400},
                                      'indicators': ind}]}}, None
    rep = build_report([{'symbol': 'AAA', 'shares': 1}], getter=getter, fx_fn=lambda c: 1.0)
    assert rep['ok'] and rep['positions'][0]['adjusted'] is False and rep['unadjusted_symbols'] == ['AAA']
    assert 'SIN ajustar' in rep['source'] and 'AAA' in rep['source']


# ════════════════════════════════════════════════════════════════════════════
# D2 · Retorno anual compuesto (geométrico) + Sharpe con tasa libre de riesgo real (^IRX)
# ════════════════════════════════════════════════════════════════════════════

def test_d2_retorno_anual_es_el_compuesto_y_el_aritmetico_va_aparte():
    from core.risk_report import compute
    d = _dates(201)
    alt = _prices([0.10, -0.10] * 100, d)              # media aritmética 0; cada par pierde 1 %
    r = compute({'A': alt}, {'A': 1}, {}, bench=None)
    assert r['return_ann_pct'] < -50 and abs(r['return_arith_ann_pct']) < 1.0
    flat = _prices([0.001] * 200, d)                    # +0,1 % diario: compuesto 28,6 %, aritmético 25,2 %
    r2 = compute({'A': flat}, {'A': 1}, {}, bench=None)
    assert 28 < r2['return_ann_pct'] < 29.5 and abs(r2['return_arith_ann_pct'] - 25.2) < 0.05


def test_d2_sharpe_usa_la_tasa_libre_de_riesgo_y_cuadra_con_las_tarjetas():
    from core.risk_report import compute
    A, _b, SPY, d = _world()
    r = compute({'A': A}, {'A': 1}, {}, bench=SPY, rf=0.04, rf_source='T-bill 13 semanas (^IRX)')
    assert r['risk_free_pct'] == 4.0 and '^IRX' in r['risk_free_source']
    assert abs(r['sharpe'] - (r['return_ann_pct'] - 4.0) / r['vol_ann_pct']) < 0.01
    assert r['sharpe_method'].startswith('(retorno anual compuesto')
    r0 = compute({'A': A}, {'A': 1}, {}, bench=SPY)
    assert r0['risk_free_pct'] == 0.0 and 'sin dato' in r0['risk_free_source'] and r0['sharpe'] > r['sharpe']


def test_d2_build_report_baja_irx_con_la_misma_cache_y_sin_irx_lo_dice():
    from datetime import datetime, timezone

    from core.risk_report import _HIST_CACHE, build_report
    _HIST_CACHE.clear()
    A, _b, SPY, d = _world()

    def mk(src, with_irx):
        def getter(url, params=None, timeout=None):
            sym = url.rsplit('/', 1)[1]
            if sym == '^IRX':
                if not with_irx:
                    return None, 'upstream 404'
                ts = [int(datetime(2026, 10, dd, 13, 30, tzinfo=timezone.utc).timestamp()) for dd in (1, 2)]
                return {'chart': {'result': [{'timestamp': ts, 'meta': {'currency': 'USD', 'gmtoffset': -14400},
                                              'indicators': {'quote': [{'close': [3.95, 3.99]}]}}]}}, None
            s = src.get(sym)
            if s is None:
                return None, 'upstream 404'
            ks = sorted(s)
            ts = [int(datetime.fromisoformat(k).replace(hour=13, minute=30, tzinfo=timezone.utc).timestamp()) for k in ks]
            return {'chart': {'result': [{'timestamp': ts, 'meta': {'currency': 'USD', 'gmtoffset': -14400},
                                          'indicators': {'quote': [{'close': [s[k] for k in ks]}],
                                                         'adjclose': [{'adjclose': [s[k] for k in ks]}]}}]}}, None
        return getter
    rep = build_report([{'symbol': 'AAA', 'shares': 1}], getter=mk({'AAA': A, 'SPY': SPY}, True), fx_fn=lambda c: 1.0)
    assert rep['ok'] and rep['risk_free_pct'] == 3.99 and '^IRX' in rep['risk_free_source']
    _HIST_CACHE.clear()
    rep2 = build_report([{'symbol': 'AAA', 'shares': 1}], getter=mk({'AAA': A, 'SPY': SPY}, False), fx_fn=lambda c: 1.0)
    assert rep2['ok'] and rep2['risk_free_pct'] == 0.0 and 'sin dato' in rep2['risk_free_source']


# ════════════════════════════════════════════════════════════════════════════
# D3 · Backtest del VaR fuera de muestra (ventana móvil) + prueba de Kupiec
# ════════════════════════════════════════════════════════════════════════════

def test_d3_kupiec_valores_conocidos():
    from core.risk_report import kupiec_pof
    lr, p = kupiec_pof(round(0.05 * 250), 250, 0.05)          # 12.5 → 12: casi exacto
    assert lr < 0.05 and p > 0.8
    lr0, p0 = kupiec_pof(0, 250, 0.05)
    assert abs(lr0 - (-2 * 250 * math.log(0.95))) < 1e-3 and p0 < 1e-5
    lr25, p25 = kupiec_pof(25, 250, 0.05)
    assert p25 < 0.01


def test_d3_backtest_es_fuera_de_muestra_y_no_tautologico():
    from core.risk_report import compute
    rng = np.random.default_rng(3)
    d = _dates(251)
    iid = _prices(rng.normal(0.0003, 0.01, 250), d)
    r = compute({'A': iid}, {'A': 1}, {})
    bt = r['backtest95']
    assert bt['method'] == 'rolling_oos' and bt['window'] == 125 and bt['days'] == 250 - 125
    assert bt['expected'] == pytest.approx(0.05 * 125, abs=0.01) and 0 <= bt['kupiec_p'] <= 1
    assert bt['in_sample'] == {'breaches': 13, 'days': 250, 'expected': 12.5}     # la tautología, solo de referencia
    # cambio de régimen: calma y luego tormenta → el VaR (estimado en la calma) subestima
    storm = _prices(np.concatenate([rng.normal(0, 0.01, 125), rng.normal(0, 0.03, 125)]), d)
    bt2 = compute({'A': storm}, {'A': 1}, {})['backtest95']
    assert bt2['breaches'] >= 2 * bt2['expected'] and bt2['kupiec_p'] < 0.05 and bt2['verdict'] == 'subestima'
    # tormenta y luego calma → sobreestima
    calm = _prices(np.concatenate([rng.normal(0, 0.03, 125), rng.normal(0, 0.01, 125)]), d)
    bt3 = compute({'A': calm}, {'A': 1}, {})['backtest95']
    assert bt3['breaches'] < bt3['expected'] and bt3['verdict'] == 'sobreestima'
    # historia corta (≥60): ventana 60
    short = _prices(rng.normal(0, 0.01, 100), _dates(101))
    assert compute({'A': short}, {'A': 1}, {})['backtest95']['window'] == 60
