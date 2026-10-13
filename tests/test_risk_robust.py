"""tests/test_risk_robust.py — batch I2: riesgo con estadística ROBUSTA (BRECHAS L2-09/L2-14/L2-15/L2-16/L2-18/L2-M2).

Cada estimador contra una referencia INDEPENDIENTE escrita aquí (numpy, fórmulas de libro):
  · Ledoit-Wolf  vs el algoritmo de sklearn transcrito con bucles y vs la forma del artículo (m, d², b̄², b²);
  · EWMA         vs la recursión RiskMetrics con un bucle y vs su forma cerrada;
  · Cornish-Fisher vs el polinomio de libro evaluado paso a paso;
  · h días       vs el compuesto por fuerza bruta;
  · Sharpe       aritmético vs numpy y ^IRX convertido (bond-equivalent / money-market).
Y el comportamiento: policy.risk 1.0.0 deja TODO lo de hoy igual; 2.0.0 (PIN) quita la ventana común y nunca da
una covarianza singular (59 acciones con un año + 1 con 61 días; 60 posiciones con 60 días). Sin red ni base.
"""
import math
import os
import sys
from datetime import date, timedelta
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import risk_models as rm  # noqa: E402
from core import risk_report as rr  # noqa: E402


def _dates(n, start=date(2025, 1, 2)):
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _px(rets, ds, p0=100.0):
    out, p = {ds[0]: p0}, p0
    for i, r in enumerate(rets):
        p *= 1 + r
        out[ds[i + 1]] = p
    return out


# ════════════════════════════════════════════════════════════════════════════
# Ledoit-Wolf
# ════════════════════════════════════════════════════════════════════════════
def _lw_sklearn_loops(X):
    """sklearn.covariance.ledoit_wolf_shrinkage + ledoit_wolf (assume_centered=False), transcrito con bucles."""
    n, p = X.shape
    Xc = X - X.mean(axis=0)
    S = np.zeros((p, p))
    for t in range(n):
        S += np.outer(Xc[t], Xc[t])
    S /= n
    mu = np.trace(S) / p
    beta_ = sum(((Xc[:, i] ** 2) * (Xc[:, j] ** 2)).sum() for i in range(p) for j in range(p))
    delta_ = sum(((Xc[:, i] * Xc[:, j]).sum()) ** 2 for i in range(p) for j in range(p)) / n ** 2
    beta = (beta_ / n - delta_) / (p * n)
    delta = (delta_ - 2 * mu * np.trace(S) + p * mu ** 2) / p
    beta = min(beta, delta)
    sh = 0.0 if beta == 0 else beta / delta
    return (1 - sh) * S + sh * mu * np.eye(p), sh


def _lw_paper(X):
    """Ledoit & Wolf (2004), JMA 88: m = <S,I>, d² = ‖S − mI‖², b̄² = (1/n²) Σ ‖x xᵀ − S‖², b² = min(b̄², d²);
    norma de Frobenius normalizada ‖A‖² = tr(A Aᵀ)/p."""
    n, p = X.shape
    Xc = X - X.mean(axis=0)
    S = Xc.T @ Xc / n

    def nf(A):
        return np.trace(A @ A.T) / p
    m = np.trace(S) / p
    d2 = nf(S - m * np.eye(p))
    b2bar = sum(nf(np.outer(x, x) - S) for x in Xc) / n ** 2
    b2 = min(b2bar, d2)
    return (b2 / d2) * m * np.eye(p) + (1 - b2 / d2) * S, b2 / d2


@pytest.mark.parametrize('n,p,seed', [(250, 10, 1), (60, 60, 2), (40, 25, 3), (500, 3, 4)])
def test_ledoit_wolf_igual_a_sklearn_y_al_articulo(n, p, seed):
    rng = np.random.default_rng(seed)
    f = rng.normal(0, 0.01, (n, 1))
    X = f @ rng.uniform(0.5, 1.5, (1, p)) + rng.normal(0, 0.015, (n, p))
    sig, sh, mu = rm.ledoit_wolf(X)
    ref1, sh1 = _lw_sklearn_loops(X)
    ref2, sh2 = _lw_paper(X)
    assert sh == pytest.approx(sh1, abs=1e-12) == pytest.approx(sh2, abs=1e-12)
    assert np.allclose(sig, ref1, atol=1e-15, rtol=1e-10) and np.allclose(sig, ref2, atol=1e-15, rtol=1e-10)
    assert 0 < sh < 1 and mu == pytest.approx(np.trace(np.cov(X.T, bias=True)) / p)
    assert np.linalg.eigvalsh(sig).min() > 0                    # nunca singular (con n ≤ p la muestral sí lo es)


def test_ledoit_wolf_cura_la_singular_de_60_posiciones_con_60_dias():
    rng = np.random.default_rng(7)
    X = rng.normal(0, 0.02, (60, 60))
    S = np.cov(X.T)
    assert np.linalg.matrix_rank(S) == 59                     # la muestral: singular (rango n − 1)
    sig, sh, _ = rm.ledoit_wolf(X)
    assert np.linalg.matrix_rank(sig) == 60 and np.linalg.cond(sig) < 1e3 and sh > 0.5


def test_contraccion_pareada_y_reparacion_psd():
    S = np.array([[1.0, 0.99, -0.99], [0.99, 1.0, 0.99], [-0.99, 0.99, 1.0]])   # pareada imposible: no es PSD
    assert np.linalg.eigvalsh(S).min() < 0
    fixed, rep = rm.nearest_psd(S)
    assert rep and np.linalg.eigvalsh(fixed).min() >= 0 and np.allclose(fixed, fixed.T)
    ok, rep2 = rm.nearest_psd(np.eye(3))
    assert not rep2 and np.allclose(ok, np.eye(3))
    assert np.allclose(rm.shrink(S, 0.25), 0.75 * S + 0.25 * np.eye(3))


def test_covarianza_pareada_usa_la_ventana_de_cada_par():
    rets = {'A': {f'd{i:03d}': 0.01 * math.sin(i) for i in range(200)},
            'B': {f'd{i:03d}': 0.02 * math.sin(i) for i in range(120, 200)}}
    S, N = rm.pairwise_cov(rets, ['A', 'B'], min_obs=20)
    a = np.array(list(rets['A'].values()))
    assert N[0, 0] == 200 and N[1, 1] == 80 and N[0, 1] == 80
    assert S[0, 0] == pytest.approx(a.var(ddof=1))            # A con SUS 200 días, no recortada a 80
    common = [rets['A'][d] for d in sorted(rets['B'])]
    assert S[0, 1] == pytest.approx(np.cov(common, list(rets['B'].values()))[0, 1])


def test_correlacion_pareada_usa_los_momentos_de_su_ventana_y_nunca_pasa_de_1():
    """Revisión lote I: la cov del par dividida por las σ de la historia COMPLETA de cada uno daba ρ = 1,38."""
    rng = np.random.default_rng(1)
    ds = _dates(251)
    ra = np.concatenate([rng.normal(0, 0.002, 120), rng.normal(0, 0.03, 130)])
    A = _px(list(ra), ds)
    B = {d: A[d] for d in ds[120:]}                            # B = A en los últimos 131 días
    C = _px(list(rng.normal(0, 0.01, 250)), ds)
    r = rr.compute({'A': A, 'B': B, 'C': C}, {'A': 10, 'B': 10, 'C': 10}, {'A': 1.0, 'B': 1.0, 'C': 1.0},
                   policy=dict(_pol('2.0.0'), min_history_days=120))
    m = np.array(r['correlation']['matrix'], dtype=float)
    assert np.nanmax(np.abs(m)) <= 1.0 and m[0, 1] == pytest.approx(1.0, abs=1e-3)
    rets = {'A': {f'd{i:03d}': 0.01 * math.sin(i) for i in range(200)},
            'B': {f'd{i:03d}': 0.02 * math.sin(i) + 0.001 * math.cos(3 * i) for i in range(120, 200)}}
    Cm, N = rm.pairwise_corr(rets, ['A', 'B'], min_obs=20)
    common = [rets['A'][d] for d in sorted(rets['B'])]
    assert Cm[0, 1] == pytest.approx(np.corrcoef(common, list(rets['B'].values()))[0, 1]) and N[0, 1] == 80


# ════════════════════════════════════════════════════════════════════════════
# EWMA (RiskMetrics)
# ════════════════════════════════════════════════════════════════════════════
def test_ewma_igual_a_la_recursion_riskmetrics_y_a_su_forma_cerrada():
    rng = np.random.default_rng(11)
    r = rng.standard_t(4, 300) * 0.01
    lam, k = 0.94, 25
    v = float(np.mean(r[:k] ** 2))
    v0 = v
    for x in r:                                               # σ²_{t+1} = λσ²_t + (1−λ)r_t²
        v = lam * v + (1 - lam) * x * x
    T = len(r)
    closed = lam ** T * v0 + (1 - lam) * sum(lam ** (T - 1 - i) * r[i] ** 2 for i in range(T))
    got = rm.ewma_var(r, lam, k)
    assert got == pytest.approx(v, rel=1e-12) == pytest.approx(closed, rel=1e-12)
    C = rm.ewma_cov(np.column_stack([r, 2 * r]), lam, k)
    assert C[0, 0] == pytest.approx(got, rel=1e-12) and C[1, 1] == pytest.approx(4 * got, rel=1e-12)
    w = np.array([0.3, 0.7])
    assert float(w @ C @ w) == pytest.approx(rm.ewma_var(r * (0.3 + 1.4), lam, k), rel=1e-12)   # lineal
    assert rm.ewma_var([0.01], 0.94) is None and rm.ewma_var(r, 1.0) is None


def test_ewma_reacciona_a_un_regimen_nuevo():
    calm, storm = [0.005 * (-1) ** i for i in range(200)], [0.03 * (-1) ** i for i in range(30)]
    e = math.sqrt(rm.ewma_var(calm + storm, 0.94))
    s = float(np.std(calm + storm, ddof=1))
    assert e > 2 * s                                          # la EWMA ya "vio" la tormenta; la muestral no


# ════════════════════════════════════════════════════════════════════════════
# Colas: Cornish-Fisher, h días
# ════════════════════════════════════════════════════════════════════════════
def test_cornish_fisher_igual_al_libro():
    z, S, K = -1.6448536269514722, -0.8, 4.0
    # Hull, Risk Management (cap. VaR): z + (z²−1)S/6 + (z³−3z)K/24 − (2z³−5z)S²/36, paso a paso
    t1 = (z ** 2 - 1) * S / 6
    t2 = (z ** 3 - 3 * z) * K / 24
    t3 = -(2 * z ** 3 - 5 * z) * S ** 2 / 36
    assert rm.cornish_fisher_z(z, S, K) == pytest.approx(z + t1 + t2 + t3, abs=1e-15)
    assert rm.cornish_fisher_z(z, 0, 0) == z
    assert rm.cf_var(0.0, 0.02, 0.0, 0.0, 0.95, 1) == pytest.approx(rm.param_var(0.0, 0.02, 0.95, 1))
    assert rm.cf_var(0.0, 0.02, -0.8, 4.0, 0.99, 1) > rm.param_var(0.0, 0.02, 0.99, 1)   # cola gorda/izq.: más VaR
    # escala iid a h días: asimetría/√h, curtosis/h
    h = 10
    assert rm.cf_var(0.001, 0.02, S, K, 0.95, h) == pytest.approx(
        -(0.001 * h + 0.02 * math.sqrt(h) * rm.cornish_fisher_z(z, S / math.sqrt(h), K / h)))


def test_cornish_fisher_se_acerca_al_cuantil_real_de_una_cola_gorda():
    rng = np.random.default_rng(5)
    x = 0.01 * rng.standard_t(8, 200_000)                     # t de Student (8 g.l.: curtosis en exceso ≈ 1,5)
    m, sd, s, k = rm.moments(x)
    for conf in (0.95, 0.99):
        q = -np.quantile(x, 1 - conf)
        assert abs(rm.cf_var(m, sd, s, k, conf) - q) < abs(rm.param_var(m, sd, conf) - q)
    # límite conocido (y por eso va AL LADO, no reemplaza): con colas muy gordas (t de 4 g.l.) se pasa de largo


def test_cornish_fisher_fuera_de_su_dominio_no_publica_cifra():
    """Revisión lote I: un solo día de +40 % (asimetría ≈ 10, curtosis ≈ 135) daba VaR CF NEGATIVO (una «pérdida» que
    es ganancia) y el 99 % por debajo del 95 %. Fuera del dominio → None + nota bilingüe; dentro, igual que antes."""
    assert rm.cf_var(0, 0.02, 10.03, 134.6, 0.95, 1) is None and not rm.cf_valid(10.03, 134.6)
    assert rm.cf_valid(-0.8, 4.0) and rm.cf_var(0.0, 0.02, -0.8, 4.0, 0.99, 1) > 0
    rng = np.random.default_rng(7)
    ds = _dates(251)
    x = rng.normal(0, 0.015, 250)
    x[100] = 0.4
    r = rr.compute({'X': _px(list(x), ds)}, {'X': 10}, {'X': 1.0}, horizon=10)
    for v in (r['var95'], r['var99']):
        assert v['cf_1d_pct'] is None and v['cf_1d_usd'] is None and v['cf_note']['es'] and v['cf_note']['en']
        assert v['param_1d_pct'] > 0
    for v in (r['var95'], r['var99']):                       # si hay cifra, nunca es una ganancia
        assert v['cf_nd_pct'] is None or v['cf_nd_pct'] > 0
    js = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'engine', 'riskreport.js'),
              encoding='utf-8').read()
    assert 'cf_note' in js and 'outside its valid range' in js


def test_retornos_superpuestos_y_cvar_a_h_dias_por_fuerza_bruta():
    rng = np.random.default_rng(3)
    r = rng.normal(0.0005, 0.015, 120)
    h = 10
    brute = [float(np.prod(1 + r[i:i + h]) - 1) for i in range(len(r) - h + 1)]
    got = rm.overlapping_returns(r, h)
    assert len(got) == 111 and np.allclose(got, brute, atol=1e-14)
    v, c = rm.hist_var_cvar(brute, 0.95)
    q = np.quantile(brute, 0.05)                              # numpy 'linear' = el cuantil de risk_report
    assert v == pytest.approx(-q) and c == pytest.approx(-np.mean([b for b in brute if b <= q]))


def test_momentos_igual_a_numpy():
    rng = np.random.default_rng(9)
    x = rng.gamma(2.0, 0.01, 5000) - 0.02
    m, sd, s, k = rm.moments(x)
    d = x - x.mean()
    assert m == pytest.approx(x.mean()) and sd == pytest.approx(x.std(ddof=1))
    assert s == pytest.approx((d ** 3).mean() / (d ** 2).mean() ** 1.5)
    assert k == pytest.approx((d ** 4).mean() / (d ** 2).mean() ** 2 - 3)


# ════════════════════════════════════════════════════════════════════════════
# Sharpe y ^IRX
# ════════════════════════════════════════════════════════════════════════════
def test_sharpe_aritmetico_y_tbill():
    rng = np.random.default_rng(1)
    r = rng.normal(0.0008, 0.02, 252)
    rf = 0.04
    ref = (r.mean() - rf / 252) * 252 / (r.std(ddof=1) * math.sqrt(252))
    assert rm.sharpe_arith(r, rf) == pytest.approx(ref)
    # ^IRX es tasa de DESCUENTO: d = 4 % → bond-equivalent 365·d/(360−91·d), money-market 360·d/(360−91·d)
    assert rm.tbill_yield(0.04) == pytest.approx(365 * 0.04 / (360 - 91 * 0.04)) == pytest.approx(0.0409698, abs=1e-6)
    assert rm.tbill_yield(0.04, basis='money_market') == pytest.approx(360 * 0.04 / (360 - 91 * 0.04))
    assert rm.tbill_yield(0.04, basis='discount') == 0.04 and rm.tbill_yield(0.0) == 0.0


# ════════════════════════════════════════════════════════════════════════════
# compute(): 1.0.0 = lo de hoy + métricas al lado · 2.0.0 (PIN) = robusto
# ════════════════════════════════════════════════════════════════════════════
def _world(seed=42, n=252, k=4, fat=False):
    rng = np.random.default_rng(seed)
    ds = _dates(n)
    m = rng.normal(0.0004, 0.01, n - 1)
    hist = {}
    for i in range(k):
        e = (rng.standard_t(3, n - 1) * 0.008) if fat else rng.normal(0, 0.012, n - 1)
        hist[f'S{i}'] = _px((0.5 + 0.4 * i) * m + e, ds)
    return hist, _px(m, ds, 400.0), ds


def _pol(semver):
    from core import governance
    return dict(governance.available_artifact('policy.risk', semver)['params'], semver=semver)


def test_politica_vigente_del_repositorio_es_la_1_0_0_y_la_2_0_0_pide_pin():
    from core import governance
    assert governance.repo_bundle().artifacts['policy.risk']['semver'] == '1.0.0'
    v2 = governance.available_artifact('policy.risk', '2.0.0')
    assert v2['activation'] == 'pin' and v2['change_kind'] == 'major'
    assert v2['params']['window'] == 'pairwise' and v2['params']['covariance'] == 'ledoit_wolf'
    assert v2['params']['sharpe'] == 'arithmetic' and v2['params']['ewma_lambda'] == 0.94
    p = rr.risk_policy()
    assert p['semver'] == '1.0.0' and p['window'] == 'intersection' and p['sharpe'] == 'geometric'


def test_1_0_0_agrega_metricas_sin_tocar_las_de_hoy():
    hist, spy, _ = _world(fat=True)
    sh = {s: 10.0 for s in hist}
    r = rr.compute(hist, sh, {s: 1.0 for s in hist}, bench=spy, horizon=10, rf=0.04, rf_source='t')
    assert r['risk_policy']['semver'] == '1.0.0' and r['covariance_model'] is None
    # Sharpe de hoy (compuesto, ^IRX tal cual) sigue siendo el principal
    assert r['sharpe'] == r['sharpe_geom'] and r['risk_free_pct'] == 4.0
    assert abs(r['sharpe'] - (r['return_ann_pct'] - 4.0) / r['vol_ann_pct']) < 0.01
    # al lado: aritmético con ^IRX convertido, EWMA, Ledoit-Wolf, Cornish-Fisher, h días superpuestos
    port = _port(hist, sh)
    rf_y = rm.tbill_yield(0.04)
    sd = port.std(ddof=1)
    assert r['sharpe_arith'] == round((port.mean() - rf_y / 252) * 252 / (sd * math.sqrt(252)), 2)
    assert r['risk_free_yield_pct'] == round(rf_y * 100, 2)
    assert r['vol_ann_ewma_pct'] == round(math.sqrt(rm.ewma_var(port, 0.94, 25) * 252) * 100, 2)
    X = np.column_stack([np.diff(np.array([hist[s][d] for d in sorted(hist[s])])) /
                         np.array([hist[s][d] for d in sorted(hist[s])])[:-1] for s in hist])
    w = _weights(hist, sh)
    assert r['vol_ann_lw_pct'] == round(math.sqrt(w @ rm.ledoit_wolf(X)[0] @ w * 252) * 100, 2)
    over = rm.overlapping_returns(port, 10)
    v, c = rm.hist_var_cvar(over, 0.95)
    assert r['var95']['hist_nd_overlap_pct'] == round(v * 100, 3) and r['var95']['cvar_nd_pct'] == round(c * 100, 3)
    assert r['var95']['cvar_nd_pct'] >= r['var95']['hist_nd_overlap_pct'] and r['nd_windows'] == len(over)
    m, s, g1, g2 = rm.moments(port)
    assert r['var99']['cf_1d_pct'] == round(rm.cf_var(m, sd, g1, g2, 0.99, 1) * 100, 3)
    assert r['var95']['param_nd_pct'] == round(rm.param_var(m, sd, 0.95, 10) * 100, 3)
    assert r['moments'] == {'skew': round(g1, 3), 'excess_kurtosis': round(g2, 3)}
    assert abs(r['var95']['hist_nd_pct'] - r['var95']['hist_1d_pct'] * math.sqrt(10)) < 0.002   # √N de siempre


def _weights(hist, sh):
    last = max(set.intersection(*(set(h) for h in hist.values())))
    v = np.array([sh[s] * hist[s][last] for s in hist])
    return v / v.sum()


def _port(hist, sh):
    w = _weights(hist, sh)
    ds = sorted(set.intersection(*(set(h) for h in hist.values())))
    R = np.column_stack([[hist[s][ds[i]] / hist[s][ds[i - 1]] - 1 for i in range(1, len(ds))] for s in hist])
    return R @ w


def _trunc_world(k=60, short_days=61, seed=3):
    """El caso de la auditoría (trunc.py): 59 acciones con un año + 1 con 61 días."""
    rng = np.random.default_rng(seed)
    ds = _dates(253)
    m = rng.normal(0.0004, 0.01, 252)
    hist = {}
    for i in range(k):
        r = (0.6 + 0.01 * i) * m + rng.normal(0, 0.012, 252)
        px = _px(r, ds)
        if i == k - 1:
            px = {d: p for d, p in px.items() if d >= ds[-short_days]}
        hist[f'S{i:02d}'] = px
    return hist, ds


def test_l2_14_con_1_0_0_la_ventana_se_recorta_y_ahora_se_dice_quien():
    hist, ds = _trunc_world()
    r = rr.compute(hist, {s: 1.0 for s in hist}, {s: 1.0 for s in hist}, horizon=10)
    assert r['ok'] and r['days'] == 60                                   # lo de hoy (1.0.0): 60 días para TODAS
    assert r['window']['truncated_by'] == ['S59'] and r['window']['longest_history_days'] == 252


def test_l2_14_con_2_0_0_una_posicion_corta_no_recorta_a_las_demas_y_la_covarianza_no_es_singular():
    hist, ds = _trunc_world()
    pol = _pol('2.0.0')
    r = rr.compute(hist, {s: 1.0 for s in hist}, {s: 1.0 for s in hist}, horizon=10, rf=0.04, policy=pol)
    assert r['ok'] and r['days'] == 252 and r['window']['method'] == 'pairwise'
    assert [x['symbol'] for x in r['excluded_short']] == ['S59'] and r['excluded_short'][0]['history_days'] == 60
    assert 0 < r['excluded_value_pct'] < 5
    cm = r['covariance_model']
    assert cm['estimator'] == 'ledoit_wolf' and 0 < cm['shrinkage'] < 1 and cm['window'] == 'pairwise'
    assert sum(p['risk_contrib_pct'] for p in r['positions']) == pytest.approx(100, abs=0.2)
    # Sharpe principal = aritmético con ^IRX convertido
    assert r['sharpe'] == r['sharpe_arith'] and r['risk_free_pct'] == round(rm.tbill_yield(0.04) * 100, 2)
    # 60 posiciones con 60 días comunes: la muestral es singular, la que usa 2.0.0 no
    short = {s: {d: p for d, p in h.items() if d >= ds[-61]} for s, h in hist.items()}
    X = np.column_stack([[short[s][ds[-61 + i]] / short[s][ds[-62 + i]] - 1 for i in range(1, 61)] for s in short])
    assert np.linalg.matrix_rank(np.cov(X.T)) < 60
    pol60 = dict(pol, min_history_days=60)
    r60 = rr.compute(short, {s: 1.0 for s in short}, {s: 1.0 for s in short}, policy=pol60)
    assert r60['ok'] and r60['covariance_model']['shrinkage'] > 0 and not r60['excluded_short']
    sig, _, _ = rm.ledoit_wolf(X)
    assert np.linalg.eigvalsh(sig).min() > 0


def test_2_0_0_con_historias_completas_coincide_con_la_muestral_salvo_la_contraccion():
    hist, spy, _ = _world(k=5)
    pol = dict(_pol('2.0.0'), covariance='sample')            # ventana pareada SIN contracción
    sh = {s: 5.0 for s in hist}
    a = rr.compute(hist, sh, {s: 1.0 for s in hist}, bench=spy, policy=pol)
    b = rr.compute(hist, sh, {s: 1.0 for s in hist}, bench=spy)      # 1.0.0
    ca = {p['symbol']: p['risk_contrib_pct'] for p in a['positions']}
    cb = {p['symbol']: p['risk_contrib_pct'] for p in b['positions']}
    assert ca == pytest.approx(cb, abs=0.02)                             # misma ventana → misma contribución
    assert a['vol_ann_pct'] == b['vol_ann_pct'] and a['covariance_model']['vol_ann_pct'] == pytest.approx(
        b['vol_ann_pct'], abs=0.02)


def test_2_0_0_por_contrafactual_de_gobernanza():
    from core import governance
    hist, spy, _ = _world(k=3)
    with governance.counterfactual({'policy.risk': '2.0.0'}):
        r = rr.compute(hist, {s: 1.0 for s in hist}, {s: 1.0 for s in hist}, bench=spy, rf=0.04)
    assert r['risk_policy']['semver'] == '2.0.0' and r['sharpe'] == r['sharpe_arith']
    r1 = rr.compute(hist, {s: 1.0 for s in hist}, {s: 1.0 for s in hist}, bench=spy, rf=0.04)
    assert r1['risk_policy']['semver'] == '1.0.0' and r1['sharpe'] == r1['sharpe_geom']


# ════════════════════════════════════════════════════════════════════════════
# Liquidez (ADV real) en build_report
# ════════════════════════════════════════════════════════════════════════════
def _chart(prices, vols, ds):
    ts = [int(datetime_ts(d)) for d in ds]
    return {'chart': {'result': [{'timestamp': ts, 'meta': {'currency': 'USD', 'gmtoffset': 0},
                                  'indicators': {'quote': [{'close': prices, 'volume': vols}],
                                                 'adjclose': [{'adjclose': prices}]}}]}}


def datetime_ts(d):
    from datetime import datetime, timezone
    return datetime.fromisoformat(d).replace(tzinfo=timezone.utc).timestamp() + 20 * 3600


def test_liquidez_con_volumen_real_y_sin_volumen_no_se_inventa(monkeypatch):
    monkeypatch.setattr(rr, '_HIST_CACHE', {})
    monkeypatch.setattr(rr, '_HIST_META', {})
    import core.prices_store as ps
    monkeypatch.setattr(ps, 'history', lambda *a, **k: None)
    ds = _dates(200)
    rng = np.random.default_rng(2)
    base = [100 * float(np.exp(x)) for x in np.cumsum(rng.normal(0, 0.01, 200))]
    data = {'BIG': _chart(base, [5_000_000] * 200, ds), 'THIN': _chart([p / 2 for p in base], [1000] * 200, ds),
            'NOVOL': _chart([p * 1.5 for p in base], [None] * 200, ds), 'SPY': _chart(base, [1] * 200, ds),
            '^IRX': _chart([4.0] * 200, [0] * 200, ds)}

    def getter(url, params=None, timeout=10):
        sym = url.rsplit('/', 1)[1]
        return data.get(sym), None
    rep = rr.build_report([{'symbol': 'BIG', 'usd': 100000}, {'symbol': 'THIN', 'usd': 100000},
                           {'symbol': 'NOVOL', 'usd': 1000}], getter=getter, fx_fn=lambda c: 1.0)
    assert rep['ok']
    pos = {p['symbol']: p for p in rep['positions']}
    big, thin = pos['BIG']['liquidity'], pos['THIN']['liquidity']
    adv_thin = thin['adv_usd']
    assert adv_thin == pytest.approx(np.mean([p / 2 * 1000 for p in base[-20:]]), rel=1e-6)
    assert thin['days_to_liquidate'] == pytest.approx(round(pos['THIN']['value_usd'] / (0.2 * adv_thin), 2), abs=0.01)
    assert thin['flag'] and not big['flag'] and rep['liquidity_flags'] == ['THIN']
    assert pos['NOVOL']['liquidity'] is None                              # sin volumen: no hay dato


# ════════════════════════════════════════════════════════════════════════════
# L2-09: paridad de riesgo con topes, rotulada
# ════════════════════════════════════════════════════════════════════════════
def test_rc_dispersion_igual_a_la_cuenta_a_mano():
    C = np.array([[0.04, 0.006, 0.0], [0.006, 0.09, 0.01], [0.0, 0.01, 0.01]])
    w = np.array([0.5, 0.2, 0.3])
    d = rm.rc_dispersion(w, C)
    var = w @ C @ w
    rc = w * (C @ w) / var
    assert np.allclose(d['rc'], rc) and sum(d['rc']) == pytest.approx(1.0)
    assert d['hhi'] == pytest.approx((w ** 2).sum()) and d['n_eff'] == pytest.approx(1 / (w ** 2).sum())
    assert d['max_over_min'] == pytest.approx(rc.max() / rc.min())


def test_paridad_de_riesgo_con_topes_se_rotula_con_honestidad():
    from core import portfolio_ai as pa
    ds = _dates(252)
    rng = np.random.default_rng(4)
    m = rng.normal(0, 0.01, 251)
    vols = [0.004, 0.006, 0.03, 0.035, 0.04]                  # dos muy tranquilas → la ERC les daría mucho peso
    hist = {f'S{i}': _px(0.3 * m + rng.normal(0, v, 251), ds) for i, v in enumerate(vols)}
    chosen = [{'symbol': s, 'id': s.lower(), 'label': s, 'sector': f'sec{i}', 'country': 'US', 'nrs': 50}
              for i, s in enumerate(hist)]
    prof = {'max_name': 0.25, 'max_sector': 0.6, 'max_country': 1.0}
    pf = pa._size_and_measure('baja_vol', 'Baja volatilidad', 'Low volatility', 'risk_parity', chosen, hist,
                              {s: 1.0 for s in hist}, {s: 'USD' for s in hist}, None, prof, 10000, 'es')
    assert pf['method'] == 'risk_parity' and pf['method_capped'] is True
    assert pf['method_label_es'] == 'paridad de riesgo con topes' and pf['method_label_en'] == 'capped risk parity'
    rp = pf['metrics']['risk_parity']
    assert rp['target_pct'] == 20.0 and rp['rc_min_pct'] < 20 < rp['rc_max_pct'] and rp['rc_max_over_min'] > 1.5
    assert any('CON TOPES' in n['es'] and 'CAPPED' in n['en'] for n in pf['notes'])
    assert 'con topes' in pa.deterministic_rationale(pf, {'themes': []}, 'es')
    # sin topes que muerdan: ERC exacta, contribuciones iguales y rótulo normal
    prof2 = {'max_name': 1.0, 'max_sector': 1.0, 'max_country': 1.0}
    pf2 = pa._size_and_measure('baja_vol', 'Baja volatilidad', 'Low volatility', 'risk_parity', chosen, hist,
                               {s: 1.0 for s in hist}, {s: 'USD' for s in hist}, None, prof2, 10000, 'es')
    assert pf2['method_capped'] is False and pf2['method_label_es'] == 'paridad de riesgo'
    assert pf2['metrics']['risk_parity']['rc_max_over_min'] == pytest.approx(1.0, abs=1e-3)


# ════════════════════════════════════════════════════════════════════════════
# L2-M2: suspendida → último cierre antes del vencimiento (deslistada: tests/test_phase3.py)
# ════════════════════════════════════════════════════════════════════════════
def test_suspendida_al_vencimiento_se_califica_con_el_ultimo_cierre():
    from research.outcomes import score_checkpoint
    anchor = date(2026, 6, 1)
    days = [anchor + timedelta(days=i) for i in range(0, 90)]
    spy = {d.isoformat(): 100.0 for d in days}
    nv = {d.isoformat(): 100.0 + i for i, d in enumerate(days) if not (20 <= i <= 50)}   # sin cotizar 30 días
    b = SimpleNamespace(scoreable=True, na_reason=None, baseline_date=anchor.isoformat(), symbol='NVDA',
                        benchmark_symbol='SPY', stance='positive', band=0.02)
    cp = {'label': 'final_20b', 'days': 30, 'due_date': (anchor + timedelta(days=30)).isoformat(), 'final': True}
    r = score_checkpoint(b, cp, lambda s, since: nv if s == 'NVDA' else spy, anchor + timedelta(days=80))
    assert r['terminal'] == 'suspended' and r['eval_date'] == (anchor + timedelta(days=19)).isoformat()
    assert r['result'] == 'hit' and '[suspendida]' in r['reason'] and '[suspended]' in r['reason_en']
    assert len(r['price_source']) <= 60


# ════════════════════════════════════════════════════════════════════════════
# UI (engine/riskreport.js en Node): las métricas nuevas se pintan, bilingües y solo con tokens
# ════════════════════════════════════════════════════════════════════════════
def test_ui_pinta_las_metricas_nuevas_con_tokens():
    import json
    import subprocess

    from tests import test_overnight_ui_portfolios_risk as U
    if not U.NODE:
        pytest.skip('requiere node')
    js = U.JS.replace("histogram: { edges_pct: [-4, 0, 4], counts: [3, 9] },",
                      "histogram: { edges_pct: [-4, 0, 4], counts: [3, 9] }, vol_ann_ewma_pct: 44.1, ewma_lambda: 0.94, "
                      "vol_ann_lw_pct: 38.2, sharpe_geom: 0.88, sharpe_arith: 0.97, excluded_value_pct: 12.5, "
                      "liquidity_flags: ['TSM'], window: { from: '2026-06-01', days: 90, longest_history_days: 251, "
                      "truncated_by: ['NEWCO'] }, risk_policy: { semver: '2.0.0', sharpe: 'arithmetic' }, "
                      "covariance_model: { estimator: 'ledoit_wolf', shrinkage: 0.03, window: 'pairwise' },")
    js = js.replace("var99: { hist_1d_usd: 3020,", "var99: { hist_1d_usd: 3020, cvar_nd_usd: 9100, cf_nd_usd: 9800, "
                    "hist_nd_overlap_usd: 8500,")
    js = js.replace("hist_nd_usd: 6116, hist_nd_pct: 12.4 }", "hist_nd_usd: 6116, hist_nd_pct: 12.4, cvar_nd_usd: 7000, "
                    "cf_nd_usd: 6900, hist_nd_overlap_usd: 6300 }")
    js = js.replace("risk_contrib_pct: 30, vol_ann_pct: 38 }", "risk_contrib_pct: 30, vol_ann_pct: 38, liquidity: "
                    "{ days_to_liquidate: 7.5, flag: true } }")
    js = js.replace("totals: { vega_usd: 62.4, value_usd: 1830, delta_shares: 54, theta_usd_day: -9.1, gamma: 2.1 },",
                    "totals: { vega_usd: 62.4, value_usd: 1830, delta_shares: null, dollar_delta_usd: 9784, "
                    "theta_usd_day: -9.1, gamma: null, mixed_underlyings: true }, currencies: ['EUR'], model_en: 'BSM (q)',")
    assert js.count('cvar_nd_usd') == 2 and 'dollar_delta_usd: 9784' in js
    r = subprocess.run([U.NODE, '-e', js, U.ROOT], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    det, vd = out['rr_detail'], out['rr_vega_detail']
    for frag in ('Volatilidad reciente (EWMA)', 'Ledoit-Wolf', 'CVaR 95% · 10', 'Cornish-Fisher',
                 'promedio diario × 252', 'compuesto ', 'policy.risk 2.0.0', '12,5% de tu dinero', 'Días p/ vender', 'NEWCO'):
        assert frag in det, frag
    for frag in ('Delta en dólares', 'solo por empresa (abajo)', 'convertidas a USD'):
        assert frag in vd, frag
    for html in (det, vd):
        assert U.stray_colors(U.strip_mascots(html)) == []
