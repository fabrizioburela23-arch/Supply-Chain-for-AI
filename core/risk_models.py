"""core/risk_models.py — estimadores ROBUSTOS de riesgo (BRECHAS L2-14/L2-15/L2-16/L2-18; ARQUITECTURA_V2 §9.2-§9.3).

Matemática pura (numpy, sin red ni base), cada estimador con su referencia de libro y su prueba contra una
implementación independiente en tests/test_risk_robust.py:

  ewma_var / ewma_cov     RiskMetrics (J.P. Morgan 1996): σ²_{t+1} = λ·σ²_t + (1−λ)·r_t²  (media cero, λ = 0,94).
  ledoit_wolf             Ledoit & Wolf (2004), "A well-conditioned estimator for large-dimensional covariance
                          matrices": Σ̂ = (1−δ)·S + δ·μ·I, μ = tr(S)/p, δ = min(b̄², d²)/d² — la MISMA cuenta que
                          sklearn.covariance.ledoit_wolf (S con 1/n). Nunca singular con μ > 0 y δ > 0.
  shrink / nearest_psd    la contracción aplicada a una covarianza PAREADA (cada par con su ventana) + reparación a
                          semidefinida positiva (recorte de autovalores) — una covarianza pareada puede no serlo.
  pairwise_cov            covarianza muestral (n−1) de cada par sobre SUS fechas comunes (L2-14: una posición con
                          poca historia ya no recorta la ventana de las demás).
  cornish_fisher_z        cuantil ajustado por asimetría y curtosis (Zangari 1996; Hull, "Risk Management and
                          Financial Institutions"): z + (z²−1)s/6 + (z³−3z)k/24 − (2z³−5z)s²/36.
  overlapping_returns     retornos COMPUESTOS de h días en ventanas superpuestas (VaR/CVaR histórico a h días).
  sharpe_arith            (media aritmética diaria del exceso × 252) / (σ diaria × √252) — el estándar (L2-18).
  tbill_yield             ^IRX cotiza TASA DE DESCUENTO bancaria: d → rendimiento equivalente
                          (bond-equivalent 365·d/(360 − 91·d) o money-market 360·d/(360 − 91·d)).
  liquidity               días para vender una posición al `participation` del volumen medio diario (ADV) real.

Nada de esto inventa datos: si falta la historia o el volumen, la función devuelve None y quien la llama lo dice.
"""
import math

import numpy as np

TRADING_DAYS = 252
Z_LEFT = {0.95: -1.6448536269514722, 0.99: -2.3263478740408408}   # Φ⁻¹(1 − conf): cuantil de la cola izquierda


# ── EWMA (RiskMetrics) ───────────────────────────────────────────────────────
def _seed_var(r, seed_n):
    k = max(1, min(len(r), int(seed_n)))
    return float(np.mean(np.square(r[:k])))


def ewma_var(returns, lam=0.94, seed_n=25):
    """Varianza EWMA PRONOSTICADA para el día siguiente al último retorno (media cero, RiskMetrics).
    Semilla: media de r² de las primeras `seed_n` observaciones. None con menos de 2 retornos."""
    r = np.asarray(returns, dtype=float)
    if r.size < 2 or not (0.0 < lam < 1.0):
        return None
    v = _seed_var(r, seed_n)
    for x in r:
        v = lam * v + (1.0 - lam) * x * x
    return float(v)


def ewma_cov(R, lam=0.94, seed_n=25):
    """Matriz EWMA (T×p → p×p): Σ_{t+1} = λΣ_t + (1−λ) r_t r_tᵀ, semilla = media de r rᵀ de las primeras `seed_n`."""
    R = np.asarray(R, dtype=float)
    if R.ndim != 2 or R.shape[0] < 2:
        return None
    k = max(1, min(R.shape[0], int(seed_n)))
    S = R[:k].T @ R[:k] / k
    for x in R:
        S = lam * S + (1.0 - lam) * np.outer(x, x)
    return S


# ── Ledoit-Wolf ──────────────────────────────────────────────────────────────
def ledoit_wolf(X):
    """(Σ̂, δ, μ) para X (T×p, retornos). Igual que sklearn.covariance.ledoit_wolf (assume_centered=False):
    X se centra, S = XᵀX/T, objetivo μ·I con μ = tr(S)/p."""
    X = np.asarray(X, dtype=float)
    if X.ndim != 2 or X.shape[0] < 2 or X.shape[1] < 1:
        return None
    n, p = X.shape
    X = X - X.mean(axis=0)
    S = X.T @ X / n
    if p == 1:
        return S, 0.0, float(S[0, 0])
    X2 = X ** 2
    emp_cov_trace = X2.sum(axis=0) / n
    mu = float(emp_cov_trace.sum() / p)
    beta_ = float((X2.T @ X2).sum())
    delta_ = float(((X.T @ X) ** 2).sum()) / n ** 2
    beta = 1.0 / (p * n) * (beta_ / n - delta_)
    delta = (delta_ - 2.0 * mu * emp_cov_trace.sum() + p * mu ** 2) / p
    beta = min(beta, delta)
    shrinkage = 0.0 if beta == 0 else beta / delta
    shrinkage = float(min(1.0, max(0.0, shrinkage)))
    return shrink(S, shrinkage), shrinkage, mu


def shrink(S, delta):
    """(1−δ)·S + δ·μ·I con μ = tr(S)/p."""
    S = np.asarray(S, dtype=float)
    p = S.shape[0]
    mu = float(np.trace(S)) / p if p else 0.0
    return (1.0 - delta) * S + delta * mu * np.eye(p)


def nearest_psd(S, rel_floor=1e-10):
    """(matriz semidefinida positiva más cercana por recorte de autovalores, ¿se reparó?)."""
    S = np.asarray(S, dtype=float)
    S = (S + S.T) / 2.0
    vals, vecs = np.linalg.eigh(S)
    floor = rel_floor * max(1e-300, float(np.trace(S)) / max(1, S.shape[0]))
    if vals.min() >= floor:
        return S, False
    vals = np.maximum(vals, floor)
    out = (vecs * vals) @ vecs.T
    return (out + out.T) / 2.0, True


def pairwise_cov(rets, syms, min_obs=20):
    """rets {sym: {fecha: retorno}} → (S p×p con n−1, N p×p de observaciones comunes). Un par con menos de
    `min_obs` observaciones comunes queda en 0 fuera de la diagonal (y se informa con N). Vectorizado: con 60
    posiciones son 1.830 pares (un bucle por par tardaba ~0,4 s)."""
    S, N, _V = _pairwise_moments(rets, syms, min_obs)
    return S, N


def pairwise_corr(rets, syms, min_obs=20):
    """Correlación de CADA par con los momentos de SU ventana común: cov_ij / √(var_i|ij · var_j|ij), recortada a
    [−1, 1]. Revisión lote I: dividir la covarianza del par por las σ de la historia COMPLETA de cada uno (otra
    ventana) daba |ρ| > 1 (p. ej. 1,38). Par sin `min_obs` días comunes → NaN (el informe lo dice como «—»)."""
    S, N, V = _pairwise_moments(rets, syms, min_obs)
    p = len(syms)
    with np.errstate(invalid='ignore', divide='ignore'):
        den = np.sqrt(np.clip(V, 0, None) * np.clip(V.T, 0, None))
        C = np.where(den > 0, S / den, np.nan)
    ok = (N >= 2) & ((N >= min_obs) | np.eye(p, dtype=bool))
    C = np.where(ok, np.clip(C, -1.0, 1.0), np.nan)
    return C, N


def _pairwise_moments(rets, syms, min_obs=20):
    """(S covarianza del par, N días comunes, V[i, j] = varianza de i sobre los días comunes con j), todo n−1."""
    p = len(syms)
    dates = sorted(set().union(*(rets[s].keys() for s in syms))) if syms else []
    pos = {d: i for i, d in enumerate(dates)}
    R = np.zeros((len(dates), p))
    M = np.zeros((len(dates), p))
    for j, s in enumerate(syms):
        for d, r in rets[s].items():
            R[pos[d], j] = r
            M[pos[d], j] = 1.0
    N = (M.T @ M).astype(int)                 # días comunes de cada par
    SX = R.T @ M                              # SX[i, j] = Σ x_i sobre los días comunes con j
    SXY = R.T @ R
    SXX = (R * R).T @ M                       # SXX[i, j] = Σ x_i² sobre los días comunes con j
    with np.errstate(invalid='ignore', divide='ignore'):
        S = (SXY - SX * SX.T / N) / (N - 1)
        V = (SXX - SX * SX / N) / (N - 1)
    ok = (N >= 2) & ((N >= min_obs) | np.eye(p, dtype=bool))
    S = np.where(ok, S, 0.0)
    V = np.where(N >= 2, V, 0.0)
    return S, N, V


# ── colas: momentos, Cornish-Fisher, h días ──────────────────────────────────
def moments(x):
    """(media, σ muestral n−1, asimetría g1, curtosis en EXCESO g2) — momentos poblacionales para g1/g2."""
    a = np.asarray(x, dtype=float)
    n = a.size
    if n < 4:
        return None
    m = float(a.mean())
    d = a - m
    m2 = float((d ** 2).mean())
    if m2 <= 0:
        return m, 0.0, 0.0, 0.0
    g1 = float((d ** 3).mean() / m2 ** 1.5)
    g2 = float((d ** 4).mean() / m2 ** 2 - 3.0)
    return m, float(a.std(ddof=1)), g1, g2


def cornish_fisher_z(z, skew, exkurt):
    return (z + (z * z - 1.0) * skew / 6.0 + (z ** 3 - 3.0 * z) * exkurt / 24.0
            - (2.0 * z ** 3 - 5.0 * z) * skew * skew / 36.0)


def cf_valid(skew, exkurt):
    """¿La expansión de Cornish-Fisher es usable en la cola izquierda? (revisión lote I) Fuera de su dominio (gran
    asimetría POSITIVA con curtosis alta: un solo día de +40 %) el cuantil ajustado deja de crecer con z o se vuelve
    positivo: el «VaR» sale como GANANCIA y el 99 % por debajo del 95 %. Se exige, en [z₉₉, z₉₅]: derivada
    dz_cf/dz > 0 (monótono) y z_cf < 0 (una pérdida). Con los momentos YA escalados al horizonte."""
    lo, hi = Z_LEFT[0.99], Z_LEFT[0.95]
    for k in range(41):
        z = lo + (hi - lo) * k / 40.0
        d = (1.0 + z * skew / 3.0 + (3.0 * z * z - 3.0) * exkurt / 24.0
             - (6.0 * z * z - 5.0) * skew * skew / 36.0)
        if d <= 0 or cornish_fisher_z(z, skew, exkurt) >= 0:
            return False
    return True


def cf_var(mu, sigma, skew, exkurt, conf=0.95, h=1):
    """VaR Cornish-Fisher a h días (fracción positiva = pérdida). Escala iid: μh, σ√h, asimetría/√h, curtosis/h.
    None si la expansión está fuera de su dominio (cf_valid): nunca se publica una «pérdida» con el signo cambiado."""
    h = max(1, int(h))
    s_h, k_h = skew / math.sqrt(h), exkurt / h
    if not cf_valid(s_h, k_h):
        return None
    zc = cornish_fisher_z(Z_LEFT[conf], s_h, k_h)
    return -(mu * h + sigma * math.sqrt(h) * zc)


def param_var(mu, sigma, conf=0.95, h=1):
    """VaR normal a h días: −(μh + z·σ√h)."""
    h = max(1, int(h))
    return -(mu * h + Z_LEFT[conf] * sigma * math.sqrt(h))


def overlapping_returns(r, h):
    """Retornos compuestos de h días en ventanas superpuestas (n − h + 1 ventanas)."""
    a = np.asarray(r, dtype=float)
    h = max(1, int(h))
    if a.size < h:
        return np.array([])
    lg = np.concatenate([[0.0], np.cumsum(np.log1p(a))])
    return np.expm1(lg[h:] - lg[:-h])


def _quantile_linear(sorted_x, q):
    pos = (len(sorted_x) - 1) * q
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    return sorted_x[lo] + (sorted_x[hi] - sorted_x[lo]) * (pos - lo)


def hist_var_cvar(x, conf=0.95):
    """(VaR, CVaR) históricos (pérdida positiva) con el mismo cuantil lineal que core/risk_report."""
    s = sorted(float(v) for v in x)
    if not s:
        return None, None
    q = _quantile_linear(s, 1 - conf)
    tail = [v for v in s if v <= q]
    return -q, (-sum(tail) / len(tail) if tail else -q)


# ── Sharpe y tasa libre de riesgo ────────────────────────────────────────────
def sharpe_arith(r, rf_annual=0.0, periods=TRADING_DAYS):
    """(media diaria − rf/252)·252 / (σ diaria·√252). None si σ = 0 o pocos datos."""
    a = np.asarray(r, dtype=float)
    if a.size < 2:
        return None
    sd = float(a.std(ddof=1))
    if sd <= 0:
        return None
    ex = float(a.mean()) - rf_annual / periods
    return ex * periods / (sd * math.sqrt(periods))


def tbill_yield(discount, days=91, basis='bond_equivalent'):
    """Tasa de descuento bancaria (decimal, p. ej. 0,04) → rendimiento equivalente (decimal).
    basis 'bond_equivalent' (365) o 'money_market' (360); 'discount' = sin conversión."""
    d = float(discount or 0.0)
    if basis == 'discount' or d <= 0:
        return d
    den = 360.0 - days * d
    if den <= 0:
        return d
    return (365.0 if basis == 'bond_equivalent' else 360.0) * d / den


# ── liquidez (ADV real) ──────────────────────────────────────────────────────
def adv_from_rows(rows, days=20):
    """rows [(fecha, cierre, volumen)] (cierre en moneda local) → {adv_shares, adv_value, n, as_of} con las últimas
    `days` sesiones que SÍ traen volumen > 0. None sin volumen (nunca se inventa)."""
    ok = [(d, c, v) for d, c, v in rows if c and v and v > 0]
    if len(ok) < max(5, days // 2):
        return None
    ok = sorted(ok)[-days:]
    return {'adv_shares': sum(v for _, _, v in ok) / len(ok),
            'adv_value': sum(c * v for _, c, v in ok) / len(ok), 'n': len(ok), 'as_of': ok[-1][0]}


def liquidity(value_usd, adv_value_usd, participation=0.2, flag_days=5.0):
    """{days_to_liquidate, flag} — días vendiendo el `participation` del volumen medio diario."""
    if not adv_value_usd or adv_value_usd <= 0 or value_usd is None:
        return None
    days = float(value_usd) / (participation * float(adv_value_usd))
    return {'days_to_liquidate': round(days, 2), 'participation': participation, 'flag': days > flag_days,
            'pct_of_adv': round(100.0 * float(value_usd) / float(adv_value_usd), 2)}


def rc_dispersion(w, cov):
    """Contribuciones al riesgo RC_i = w_i(Σw)_i/σ² (fracciones) + dispersión: {rc, min, max, max_over_min, cv,
    hhi, n_eff} (HHI y n_eff = 1/HHI sobre los PESOS). L2-09."""
    w = np.asarray(w, dtype=float)
    C = np.asarray(cov, dtype=float)
    var = float(w @ C @ w)
    if var <= 0:
        return None
    rc = w * (C @ w) / var
    hhi = float((w ** 2).sum())
    mn, mx = float(rc.min()), float(rc.max())
    return {'rc': rc.tolist(), 'min': mn, 'max': mx, 'max_over_min': (mx / mn) if mn > 0 else None,
            'cv': float(rc.std() / rc.mean()) if rc.mean() else None, 'hhi': hhi, 'n_eff': 1.0 / hhi if hhi else None}
