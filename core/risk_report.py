"""core/risk_report.py — REPORTE DE RIESGO DE CARTERA (VaR, estilo curso MIT).

Pedido (2026-09-29): "un reporte para medir la volatilidad de una cartera".
Todo se calcula con PRECIOS DIARIOS REALES (Yahoo, ~1 año, ajustados por
dividendos/splits). Nada se inventa: una posición sin historia suficiente se
excluye y se dice cuál y por qué.

Métricas (retornos diarios, días comunes a todas las posiciones):
  · volatilidad anualizada (cartera y por posición)            σ·√252
  · VaR 95 % y 99 % a 1 día y a N días (histórico y paramétrico normal)
  · CVaR / Expected Shortfall 95 % y 99 % (histórico)
  · contribución de cada posición al riesgo (w_i·(Σw)_i / σ²)
  · beta y correlación contra el S&P 500 (SPY)
  · matriz de correlaciones entre posiciones
  · máxima caída (drawdown), retorno anual COMPUESTO (+ aritmético aparte) y
    Sharpe = (compuesto − tasa libre de riesgo T-bill 13 semanas ^IRX) / vol (D2)
  · ratio de diversificación (Σ w_i σ_i / σ_p)
  · peores días reales de la cartera (con fecha)
  · backtest del VaR 95 % FUERA de muestra (ventana móvil) + prueba de Kupiec (D3);
    el conteo en muestra (siempre ≈5 %, tautológico) queda solo de referencia

Batch I2 (BRECHAS L2-14/15/16/18; reglas en governance/artifacts/policy.risk@*.json, matemática en
core/risk_models.py): AL LADO de lo anterior, volatilidad EWMA (RiskMetrics λ 0,94) y con contracción de
Ledoit-Wolf, VaR/CVaR a h días con ventanas superpuestas, VaR normal a h días y Cornish-Fisher, Sharpe aritmético
con ^IRX convertido de tasa de descuento a rendimiento equivalente, liquidez con el volumen REAL (ADV) y quién
recorta la ventana. policy.risk 1.0.0 (vigente) deja cada número de antes IGUAL; 2.0.0 (`activation: pin`) cambia lo
principal: covarianza pareada + Ledoit-Wolf (una posición corta queda fuera y se dice cuánto dinero), Sharpe aritmético.

El VaR es una ESTIMACIÓN estadística basada en el pasado, no una predicción.
"""
import math
import time
from datetime import datetime, timezone

TRADING_DAYS = 252
Z = {0.95: 1.6448536, 0.99: 2.3263479}
BENCH = 'SPY'
RF_SYMBOL = '^IRX'       # T-bill 13 semanas (D2): la misma que usa core/options.risk_free_rate
_HIST_CACHE = {}          # (símbolo, rango) → (ts, {date: price}, currency)
_HIST_META = {}           # (símbolo, rango) → {adjusted, tz, gmtoffset, n}   (D1, misión de reparación)
_HIST_TTL = 6 * 3600


# ── datos ───────────────────────────────────────────────────────────────────
def fetch_history(symbol, rng='1y', getter=None):
    """{fecha 'YYYY-MM-DD': precio ajustado} + moneda, o ({}, None)."""
    key = (symbol, rng)
    e = _HIST_CACHE.get(key)
    if e and time.time() - e[0] < _HIST_TTL:
        return e[1], e[2]
    if getter is None:
        # BRECHAS bloque 2 (L2-12): la historia PROPIA de Khipus primero (cierres ajustados guardados día a día);
        # si la base no cubre el rango o no hay base, la descarga en vivo de siempre.
        try:
            from core import prices_store
            db = prices_store.history(symbol, rng)
        except Exception:  # noqa: BLE001
            db = None
        if db:
            out, cur, m = db
            _HIST_CACHE[key] = (time.time(), out, cur)
            _HIST_META[key] = {'adjusted': bool(m.get('adjusted', True)), 'tz': None, 'gmtoffset': None, 'n': len(out),
                               'source': m.get('source'), 'as_of': m.get('as_of'), 'adv': m.get('adv')}
            return out, cur
        from core.company_data import _get_json as getter
    data, err = getter(f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}',
                       params={'interval': '1d', 'range': rng}, timeout=10)
    if err or not isinstance(data, dict):
        return {}, None
    res = ((data.get('chart') or {}).get('result') or [None])[0] or {}
    ts = res.get('timestamp') or []
    ind = res.get('indicators') or {}
    meta = res.get('meta') or {}
    adj = ((ind.get('adjclose') or [{}])[0] or {}).get('adjclose')
    close = ((ind.get('quote') or [{}])[0] or {}).get('close')
    adjusted = bool(adj and len(adj) == len(ts))
    series = adj if adjusted else close
    # D1: la fecha de la vela es la del DÍA DE LA BOLSA (gmtoffset de Yahoo), no la
    # UTC: una sesión de Sídney/Tokio que abre antes de medianoche UTC quedaba
    # corrida un día y se emparejaba con otra sesión de EE.UU.
    try:
        off = int(meta.get('gmtoffset') or 0)
    except (TypeError, ValueError):
        off = 0
    out = {}
    for t, p in zip(ts, series or []):
        if p is not None and p > 0:
            out[datetime.fromtimestamp(int(t) + off, tz=timezone.utc).strftime('%Y-%m-%d')] = float(p)
    cur = meta.get('currency')
    if out:
        _HIST_CACHE[key] = (time.time(), out, cur)
        _HIST_META[key] = {'adjusted': adjusted, 'tz': meta.get('exchangeTimezoneName'), 'gmtoffset': off,
                           'n': len(out), 'source': 'yahoo_live', 'as_of': max(out), 'adv': _adv_of(ts, off, ind)}
    return out, cur


def _adv_of(ts, off, ind):
    """L2-16: volumen medio diario REAL de la misma respuesta de Yahoo (cierre × volumen, últimas 20 sesiones con
    volumen). None si el proveedor no trae volumen — nunca se inventa."""
    try:
        from core.risk_models import adv_from_rows
        q = (ind.get('quote') or [{}])[0] or {}
        cl, vo = q.get('close') or [], q.get('volume') or []
        rows = [(datetime.fromtimestamp(int(t) + off, tz=timezone.utc).strftime('%Y-%m-%d'), c, v)
                for t, c, v in list(zip(ts, cl, vo))[-40:] if isinstance(c, (int, float)) and isinstance(v, (int, float))]
        return adv_from_rows(rows)
    except Exception:  # noqa: BLE001
        return None


def history_meta(symbol, rng='1y'):
    """{adjusted, tz, gmtoffset, n, source, as_of} de la última serie bajada (D1) o None."""
    return _HIST_META.get((symbol, rng))


def fx_series(cur, rng='1y', getter=None):
    """L2-01 / L3-14: tipo de cambio DIARIO moneda→USD ({fecha: tasa}, meta) — base primero (fx_daily), si no la
    serie {CUR}USD=X de Yahoo. Subunidades (GBp, ZAc, ILA) ya divididas. None si no hay serie (→ tasa spot)."""
    from core.instruments import major_ccy
    maj, mult = major_ccy(cur)
    if maj == 'USD':
        return None
    if getter is None:
        try:
            from core import prices_store
            db = prices_store.fx_history(maj, rng)
        except Exception:  # noqa: BLE001
            db = None
        if db:
            return {d: r * mult for d, r in db[0].items()}, db[1]
    h, _c = fetch_history(f'{maj}USD=X', rng, getter)
    if len(h) < 20:
        return None
    m = history_meta(f'{maj}USD=X', rng) or {}
    return {d: r * mult for d, r in h.items()}, {'source': m.get('source') or 'yahoo_live', 'as_of': max(h)}


def align_fx(prices, fx, max_gap_days=7):
    """{fecha: tasa} para cada fecha de `prices`: la tasa de ese día o la última anterior (≤ max_gap_days; los
    feriados de cada mercado no coinciden). Las fechas sin tasa cercana quedan fuera."""
    from datetime import date as _date
    fd = sorted(fx)
    out, j, last = {}, 0, None
    for d in sorted(prices):
        while j < len(fd) and fd[j] <= d:
            last = fd[j]
            j += 1
        if last is not None and (_date.fromisoformat(d) - _date.fromisoformat(last)).days <= max_gap_days:
            out[d] = fx[last]
    return out


# ── matemática pura (testeable sin red) ──────────────────────────────────────
def _returns(prices, dates):
    return [prices[dates[i]] / prices[dates[i - 1]] - 1.0 for i in range(1, len(dates))]


def _mean(x):
    return sum(x) / len(x) if x else 0.0


def _std(x):
    if len(x) < 2:
        return 0.0
    m = _mean(x)
    return math.sqrt(sum((v - m) ** 2 for v in x) / (len(x) - 1))


def _cov(a, b):
    ma, mb = _mean(a), _mean(b)
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (len(a) - 1) if len(a) > 1 else 0.0


def _quantile(sorted_x, q):
    """Cuantil con interpolación lineal (como numpy 'linear')."""
    if not sorted_x:
        return 0.0
    pos = (len(sorted_x) - 1) * q
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    return sorted_x[lo] + (sorted_x[hi] - sorted_x[lo]) * (pos - lo)


def kupiec_pof(x, n, p=0.05):
    """Prueba de Kupiec (proportion of failures): x excepciones en n días con
    probabilidad p. Devuelve (LR, p-valor χ²(1)); sin scipy (erfc)."""
    x, n = int(x), int(n)
    if n <= 0:
        return 0.0, 1.0
    if x <= 0:
        lr = -2.0 * n * math.log(1.0 - p)
    elif x >= n:
        lr = -2.0 * n * math.log(p)
    else:
        f = x / n
        lr = 2.0 * ((n - x) * math.log((1 - f) / (1 - p)) + x * math.log(f / p))
    lr = max(0.0, lr)
    pval = math.erfc(math.sqrt(lr / 2.0))
    return round(lr, 4), round(min(1.0, max(0.0, pval)), 6)


def rolling_backtest(port, srt, conf=0.95):
    """D3: backtest FUERA DE MUESTRA: el VaR de cada día se estima solo con los W días
    anteriores (W = max(60, min(125, n//2))) y se cuenta si la pérdida real lo superó.
    El viejo conteo dentro de la muestra (tautológico: siempre ≈5 %) queda como
    `in_sample`, solo de referencia."""
    n = len(port)
    q = 1 - conf
    w = max(60, min(125, n // 2))
    breaches, days = 0, 0
    for t in range(w, n):
        window = sorted(port[t - w:t])
        var_t = -_quantile(window, q)
        days += 1
        if port[t] < -var_t:
            breaches += 1
    expected = round(q * days, 2)
    lr, pval = kupiec_pof(breaches, days, q)
    if breaches > expected and pval < 0.05:
        verdict = 'subestima'
    elif breaches < expected and pval < 0.05:
        verdict = 'sobreestima'
    else:
        verdict = 'ok'
    thr = _quantile(srt, q)
    return {'breaches': breaches, 'days': days, 'expected': expected, 'window': w, 'method': 'rolling_oos',
            'kupiec_lr': lr, 'kupiec_p': pval, 'verdict': verdict, 'low_power': days < 100,
            'in_sample': {'breaches': sum(1 for r in port if r < thr), 'days': n, 'expected': round(n * q, 1)}}


def _fx_at(fx, s, d):
    v = fx.get(s, 1.0)
    return v.get(d) if isinstance(v, dict) else v


def _solve(a, b):
    """Gauss-Jordan con pivote parcial (sistemas chicos: OLS de Dimson). None si es singular."""
    n = len(b)
    m = [list(a[i]) + [b[i]] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        if abs(m[p][c]) < 1e-18:
            return None
        m[c], m[p] = m[p], m[c]
        for r in range(n):
            if r != c:
                f = m[r][c] / m[c][c]
                m[r] = [x - f * y for x, y in zip(m[r], m[c])]
    return [m[i][n] / m[i][i] for i in range(n)]


def dimson_beta(y, b_lag, b_0, b_lead):
    """L2-M1: beta de Dimson = suma de las pendientes de r_p,t sobre r_m,t−1, r_m,t y r_m,t+1 (OLS con constante).
    Las bolsas de Asia/Europa cierran ANTES que Nueva York: su reacción a la sesión de EE.UU. llega al día siguiente
    y la beta del mismo día sale ~0."""
    rows = [(1.0, x1, x2, x3) for x1, x2, x3 in zip(b_lag, b_0, b_lead)]
    k = 4
    xtx = [[sum(r[i] * r[j] for r in rows) for j in range(k)] for i in range(k)]
    xty = [sum(r[i] * yy for r, yy in zip(rows, y)) for i in range(k)]
    sol = _solve(xtx, xty)
    return None if sol is None else sol[1] + sol[2] + sol[3]


# ── política de riesgo (governance/artifacts/policy.risk@*.json) ─────────────
_POLICY_CODE = {      # = policy.risk@1.0.0 (lo de HOY) si el release vigente todavía no trae el artefacto
    'ewma_lambda': 0.94, 'ewma_seed_days': 25, 'pairwise_min_obs': 20, 'min_history_days': 60,
    'window': 'intersection', 'covariance': 'sample', 'sharpe': 'geometric', 'rf_basis': 'discount',
    'liquidity': {'adv_days': 20, 'participation': 0.2, 'flag_days': 5.0},
}


def risk_policy():
    """Parámetros del release VIGENTE (policy.risk) + su versión. 1.0.0 = el reporte de hoy + métricas al lado;
    2.0.0 (`activation: pin`) = ventana pareada, Ledoit-Wolf y Sharpe aritmético."""
    out = dict(_POLICY_CODE)
    sv = None
    try:
        from core import governance
        out.update(governance.section('policy.risk'))
        sv = governance.artifact_semver('policy.risk')
    except Exception:  # noqa: BLE001 — sin artefacto: lo de hoy
        pass
    out['semver'] = sv
    return out


def _own_returns(h, fxs=None):
    """{fecha: retorno} de UNA serie sobre SUS fechas (en USD si trae FX diario)."""
    ds = sorted(h)
    px = {d: h[d] * (fxs[d] if isinstance(fxs, dict) else 1.0) for d in ds}
    return {ds[i]: px[ds[i]] / px[ds[i - 1]] - 1.0 for i in range(1, len(ds)) if px[ds[i - 1]]}


def compute(histories, shares, fx, bench=None, horizon=10, rf=0.0, rf_source=None, nonsync=None, policy=None):
    """histories: {sym: {date: price}} · shares: {sym: n} · fx: {sym: moneda→USD} — un número (tasa de hoy) o
    {fecha: tasa} (L2-01/L3-14: la serie en USD se arma FECHA A FECHA y el riesgo cambiario queda dentro).
    bench: {date: price} del S&P 500 (opcional). rf: tasa libre de riesgo anual
    (decimal; D2: T-bill 13 semanas ^IRX, COTIZADA como tasa de descuento) con su fuente. nonsync: símbolos cuya
    bolsa cierra en otro horario que Nueva York (L2-M1 → beta de Dimson y varianza con 1 rezago).
    policy: parámetros de policy.risk (por defecto los del release vigente). Devuelve el reporte (dict)."""
    import numpy as np

    from core import risk_models as rm
    pol = dict(policy) if policy is not None else risk_policy()
    pairwise = pol.get('window') == 'pairwise'
    use_lw = pol.get('covariance') == 'ledoit_wolf'
    min_hist = int(pol.get('min_history_days') or 60)
    syms = [s for s in shares if histories.get(s)]
    if not syms:
        return {'ok': False, 'error': 'sin historia de precios para ninguna posición'}
    for s in syms:          # con FX diario, solo cuentan las fechas que tienen tasa
        if isinstance(fx.get(s), dict):
            histories = dict(histories, **{s: {d: p for d, p in histories[s].items() if fx[s].get(d)}})
    own_days = {s: max(0, len(histories[s]) - 1) for s in syms}
    # L2-14 (policy.risk 2.0.0): una posición con menos de `min_history_days` retornos NO recorta la ventana de las
    # demás: queda fuera y se dice cuánto dinero no se midió
    excluded_short = []
    if pairwise:
        for s in [x for x in syms if own_days[x] < min_hist]:
            d = max(histories[s])
            excluded_short.append({'symbol': s, 'history_days': own_days[s], 'min_history_days': min_hist,
                                   'value_usd': round(shares[s] * histories[s][d] * (_fx_at(fx, s, d) or 0.0), 2),
                                   'reason_code': 'short_history'})
        syms = [s for s in syms if own_days[s] >= min_hist]
        if not syms:
            return {'ok': False, 'error': f'historia insuficiente en todas las posiciones (< {min_hist} días)',
                    'excluded_short': excluded_short}
    common = sorted(set.intersection(*(set(histories[s]) for s in syms)))
    if len(common) < 60:
        return {'ok': False, 'error': f'historia común insuficiente ({len(common)} días; se necesitan ≥ 60)'}
    last = common[-1]
    values = {s: shares[s] * histories[s][last] * _fx_at(fx, s, last) for s in syms}
    total = sum(values.values())
    if total <= 0:
        return {'ok': False, 'error': 'valor de cartera cero'}
    w = {s: values[s] / total for s in syms}
    rets = {s: _returns({d: histories[s][d] * fx[s][d] for d in common} if isinstance(fx.get(s), dict)
                        else histories[s], common) for s in syms}
    n = len(common) - 1
    port = [sum(w[s] * rets[s][i] for s in syms) for i in range(n)]

    sig_d = _std(port)
    mu_d = _mean(port)
    # L2-M1: con bolsas no sincronizadas la covarianza del mismo día se pierde; la varianza de largo plazo con
    # 1 rezago (var + 2·autocov₁) la recupera. Solo sube (conservador): nunca baja la volatilidad medida.
    ns = sorted(s for s in syms if s in set(nonsync or ()) and w[s] > 0)
    sig_same_day = sig_d
    if ns and n > 3:
        ac1 = _cov(port[1:], port[:-1])
        sig_d = math.sqrt(max(sig_d ** 2, sig_d ** 2 + 2 * ac1))
    srt = sorted(port)
    mom = rm.moments(port)
    skew, exk = (mom[2], mom[3]) if mom else (0.0, 0.0)
    over = rm.overlapping_returns(port, horizon)

    def var_block(conf):
        q = 1 - conf
        hist = -_quantile(srt, q)
        tail = [r for r in port if r <= _quantile(srt, q)]
        cvar = -_mean(tail) if tail else hist
        param = -(mu_d - Z[conf] * sig_d)
        scale = math.sqrt(horizon)
        out = {'conf': conf,
               'hist_1d_pct': round(hist * 100, 3), 'hist_1d_usd': round(hist * total, 2),
               'param_1d_pct': round(param * 100, 3), 'param_1d_usd': round(param * total, 2),
               'hist_nd_pct': round(hist * scale * 100, 3), 'hist_nd_usd': round(hist * scale * total, 2),
               'cvar_1d_pct': round(cvar * 100, 3), 'cvar_1d_usd': round(cvar * total, 2)}
        # L2-15 (al lado, sin tocar lo de arriba): normal a h días, Cornish-Fisher (asimetría/curtosis) y la
        # simulación histórica con retornos COMPUESTOS de h días en ventanas superpuestas (VaR y CVaR)
        pnd = rm.param_var(mu_d, sig_d, conf, horizon)
        cf1 = rm.cf_var(mu_d, sig_d, skew, exk, conf, 1)
        cfn = rm.cf_var(mu_d, sig_d, skew, exk, conf, horizon)
        out.update({'param_nd_pct': round(pnd * 100, 3), 'param_nd_usd': round(pnd * total, 2),
                    'cf_1d_pct': None if cf1 is None else round(cf1 * 100, 3),
                    'cf_1d_usd': None if cf1 is None else round(cf1 * total, 2),
                    'cf_nd_pct': None if cfn is None else round(cfn * 100, 3),
                    'cf_nd_usd': None if cfn is None else round(cfn * total, 2)})
        if cf1 is None or cfn is None:      # revisión lote I: fuera del dominio de Cornish-Fisher → se dice, sin cifra
            out['cf_note'] = {'es': 'Cornish-Fisher no aplica: la asimetría/curtosis de esta cartera (p. ej. un salto '
                                    'grande de un día) está fuera de su rango válido.',
                              'en': 'Cornish-Fisher does not apply: this portfolio\'s skew/kurtosis (e.g. one large '
                                    'one-day jump) is outside its valid range.'}
        if len(over) >= 20:
            hv, cv = rm.hist_var_cvar(over, conf)
            out.update({'hist_nd_overlap_pct': round(hv * 100, 3), 'hist_nd_overlap_usd': round(hv * total, 2),
                        'cvar_nd_pct': round(cv * 100, 3), 'cvar_nd_usd': round(cv * total, 2)})
        else:
            out.update({'hist_nd_overlap_pct': None, 'hist_nd_overlap_usd': None, 'cvar_nd_pct': None,
                        'cvar_nd_usd': None})
        return out

    v95, v99 = var_block(0.95), var_block(0.99)

    # covarianza, contribución al riesgo, correlaciones
    X = np.array([[rets[s][i] for s in syms] for i in range(n)])
    lw = rm.ledoit_wolf(X)
    wv = np.array([w[s] for s in syms])
    vol_lw = math.sqrt(max(0.0, float(wv @ lw[0] @ wv))) * math.sqrt(TRADING_DAYS) if lw else None
    model = None
    if pairwise or use_lw:
        # policy.risk 2.0.0: covarianza de CADA par sobre su propia ventana (o la común) + contracción de
        # Ledoit-Wolf con la intensidad δ de la ventana común (nunca singular) + reparación a semidefinida
        pcorr = None
        if pairwise:
            own = {s: _own_returns(histories[s], fx.get(s)) for s in syms}
            base, nobs = rm.pairwise_cov(own, syms, int(pol.get('pairwise_min_obs') or 20))
            pcorr, _n = rm.pairwise_corr(own, syms, int(pol.get('pairwise_min_obs') or 20))
        else:
            base = np.atleast_2d(np.cov(X.T, ddof=1))
            nobs = np.full((len(syms), len(syms)), n)
        delta = lw[1] if (use_lw and lw) else 0.0
        sig_m, repaired = rm.nearest_psd(rm.shrink(base, delta) if delta else base)
        var_m = float(wv @ sig_m @ wv)
        sdm = np.sqrt(np.clip(np.diag(sig_m), 0, None))
        sdb = np.sqrt(np.clip(np.diag(base), 0, None))
        contrib = {a: (float(wv[i] * (sig_m @ wv)[i]) / var_m) if var_m > 0 else 0.0 for i, a in enumerate(syms)}
        sd = {s: float(sdb[i]) for i, s in enumerate(syms)}
        if pcorr is not None:       # revisión lote I: cada par con SU ventana (antes σ de otra ventana → |ρ| > 1)
            corr = {a: {b: (round(float(pcorr[i, j]), 3) if np.isfinite(pcorr[i, j]) else None)
                        for j, b in enumerate(syms)} for i, a in enumerate(syms)}
        else:
            corr = {a: {b: (round(float(base[i, j] / (sdb[i] * sdb[j])), 3) if sdb[i] and sdb[j] and nobs[i, j] > 1
                            else None) for j, b in enumerate(syms)} for i, a in enumerate(syms)}
        divers = (float(wv @ sdm) / math.sqrt(var_m)) if var_m > 0 else None
        model = {'window': 'pairwise' if pairwise else 'common', 'estimator': 'ledoit_wolf' if delta else 'sample',
                 'shrinkage': round(float(delta), 4), 'psd_repaired': bool(repaired),
                 'vol_ann_pct': round(math.sqrt(max(0.0, var_m)) * math.sqrt(TRADING_DAYS) * 100, 2),
                 'min_pair_days': int(nobs.min()) if nobs.size else None,
                 'max_pair_days': int(nobs.max()) if nobs.size else None}
    else:                       # policy.risk 1.0.0: EXACTAMENTE la cuenta de siempre (paridad de cifras)
        cov = {a: {b: _cov(rets[a], rets[b]) for b in syms} for a in syms}
        var_p = sum(w[a] * w[b] * cov[a][b] for a in syms for b in syms)
        contrib = {a: (w[a] * sum(w[b] * cov[a][b] for b in syms) / var_p) if var_p > 0 else 0.0 for a in syms}
        sd = {s: _std(rets[s]) for s in syms}
        corr = {a: {b: round(cov[a][b] / (sd[a] * sd[b]), 3) if sd[a] and sd[b] else None for b in syms}
                for a in syms}
        divers = (sum(w[s] * sd[s] for s in syms) / sig_d) if sig_d else None

    # drawdown
    eq, peak, mdd, mdd_date = 1.0, 1.0, 0.0, None
    for i, r in enumerate(port):
        eq *= (1 + r)
        peak = max(peak, eq)
        dd = eq / peak - 1
        if dd < mdd:
            mdd, mdd_date = dd, common[i + 1]

    # beta vs S&P 500 (mismos pares de días consecutivos en ambas series)
    beta = corr_mkt = None
    overlap = 0
    nonsync_info = {'symbols': ns, 'beta_method': 'same_day', 'beta_same_day': None} if ns else None
    if bench:
        pr, br = [], []
        for i in range(1, len(common)):
            d0, d1 = common[i - 1], common[i]
            if d0 in bench and d1 in bench:
                pr.append(port[i - 1])
                br.append(bench[d1] / bench[d0] - 1)
        overlap = len(pr)
        vb = _cov(br, br)
        if len(pr) > 30 and vb > 0:
            beta = round(_cov(pr, br) / vb, 3)
            sp, sb = _std(pr), _std(br)
            corr_mkt = round(_cov(pr, br) / (sp * sb), 3) if sp and sb else None
        if ns:
            b = [bench[common[i + 1]] / bench[common[i]] - 1 if (common[i] in bench and common[i + 1] in bench)
                 else None for i in range(n)]
            y, x1, x2, x3 = [], [], [], []
            for i in range(1, n - 1):
                if None not in (b[i - 1], b[i], b[i + 1]):
                    y.append(port[i])
                    x1.append(b[i - 1])
                    x2.append(b[i])
                    x3.append(b[i + 1])
            beta_same_day = beta
            bd = dimson_beta(y, x1, x2, x3) if len(y) > 30 else None
            if bd is not None:
                beta = round(bd, 3)
            nonsync_info = {'symbols': ns, 'beta_method': 'dimson' if bd is not None else 'same_day',
                            'beta_same_day': beta_same_day, 'dimson_days': len(y)}
    # D1: cuántos días se emparejaron de verdad con el índice y qué rango usó cada símbolo
    # (un índice corrido un día hunde la correlación: aquí se ve, no se adivina)
    aligned = {s: {'from': common[0], 'to': common[-1], 'n': len(common)} for s in syms}

    # backtest del VaR 95 % fuera de muestra (D3) — el "en muestra" va dentro, de referencia
    backtest = rolling_backtest(port, srt, 0.95)
    worst = sorted(((port[i], common[i + 1]) for i in range(n)))[:5]
    # D2: retorno anual COMPUESTO (lo que de verdad ganó quien mantuvo la cartera) y aritmético aparte.
    # L2-18: Sharpe ARITMÉTICO (el estándar: media del exceso diario × 252 / σ·√252) con ^IRX convertido de tasa de
    # descuento a rendimiento equivalente; policy.risk elige cuál es el principal (1.0.0 = el compuesto de hoy).
    vol_ann = sig_d * math.sqrt(TRADING_DAYS)
    ret_geom = (eq ** (TRADING_DAYS / n) - 1.0) if (n > 0 and eq > 0) else 0.0
    ret_arith = mu_d * TRADING_DAYS
    rf = float(rf or 0.0)
    basis = pol.get('rf_basis') or 'discount'
    rf_head = rm.tbill_yield(rf, basis=basis)
    rf_arith = rm.tbill_yield(rf, basis='bond_equivalent' if basis == 'discount' else basis)
    sharpe_geom = round((ret_geom - rf_head) / vol_ann, 2) if vol_ann else None
    sharpe_arith = round((mu_d - rf_arith / TRADING_DAYS) * TRADING_DAYS / vol_ann, 2) if vol_ann else None
    arith_head = pol.get('sharpe') == 'arithmetic'
    sharpe = sharpe_arith if arith_head else sharpe_geom
    # L2-16: volatilidad EWMA (RiskMetrics, λ del artefacto) al lado de la muestral
    lam = float(pol.get('ewma_lambda') or 0.94)
    seed_n = int(pol.get('ewma_seed_days') or 25)
    ev = rm.ewma_var(port, lam, seed_n)
    vol_ewma = math.sqrt(ev) * math.sqrt(TRADING_DAYS) if ev else None
    # ventana: quién la recortó (L2-14, informativo en 1.0.0 también)
    starts = {s: min(histories[s]) for s in syms}
    longest = max(own_days[s] for s in syms)
    late = max(starts.values())
    truncated_by = sorted(s for s in syms if starts[s] == late) if longest - n >= 10 else []

    if nonsync_info is not None:
        nonsync_info.update(vol_ann_same_day_pct=round(sig_same_day * math.sqrt(TRADING_DAYS) * 100, 2),
                            vol_method='var + 2·autocov(1) (bolsas en otro horario)')
    positions = []
    for s in syms:
        pe = rm.ewma_var(rets[s], lam, seed_n)
        positions.append({'symbol': s, 'shares': shares[s], 'price': round(histories[s][last], 4),
                          'fx_to_usd': round(_fx_at(fx, s, last), 8), 'fx_method': 'daily' if isinstance(fx.get(s), dict)
                          else 'spot',
                          'value_usd': round(values[s], 2), 'weight_pct': round(w[s] * 100, 2),
                          'vol_ann_pct': round(sd[s] * math.sqrt(TRADING_DAYS) * 100, 2),
                          'vol_ann_ewma_pct': round(math.sqrt(pe) * math.sqrt(TRADING_DAYS) * 100, 2) if pe else None,
                          'history_days': own_days[s],
                          'risk_contrib_pct': round(contrib[s] * 100, 2)})
    positions.sort(key=lambda p: -p['risk_contrib_pct'])
    hist_bins = _histogram(port, 30)
    short_val = sum(x['value_usd'] for x in excluded_short)
    return {
        'ok': True, 'as_of': last, 'days': n, 'from': common[0], 'horizon_days': horizon,
        'portfolio_value_usd': round(total, 2),
        'vol_daily_pct': round(sig_d * 100, 3),
        'vol_ann_pct': round(vol_ann * 100, 2),
        'vol_ann_ewma_pct': round(vol_ewma * 100, 2) if vol_ewma else None, 'ewma_lambda': lam,
        'vol_ann_lw_pct': round(vol_lw * 100, 2) if vol_lw is not None else None,
        'lw_shrinkage': round(lw[1], 4) if lw else None,
        'return_ann_pct': round(ret_geom * 100, 2),            # compuesto (geométrico)
        'return_arith_ann_pct': round(ret_arith * 100, 2),     # media diaria × 252
        'sharpe': sharpe, 'sharpe_geom': sharpe_geom, 'sharpe_arith': sharpe_arith,
        'risk_free_pct': round(rf_head * 100, 2), 'risk_free_quote_pct': round(rf * 100, 2),
        'risk_free_yield_pct': round(rf_arith * 100, 2),
        'risk_free_basis': basis,
        'risk_free_source': rf_source or 'sin dato — 0 %',
        'sharpe_method': ('(media aritmética del exceso diario × 252) / volatilidad anual; ^IRX convertido a '
                          'rendimiento equivalente' if arith_head else
                          '(retorno anual compuesto − tasa libre de riesgo) / volatilidad anual'),
        'sharpe_method_en': ('(arithmetic mean daily excess × 252) / annual volatility; ^IRX converted to equivalent '
                             'yield' if arith_head else '(compounded annual return − risk-free rate) / annual volatility'),
        'moments': {'skew': round(skew, 3), 'excess_kurtosis': round(exk, 3)},
        'var95': v95, 'var99': v99, 'nd_windows': int(len(over)),
        'nd_method': {'hist_nd': f'1 día × √{horizon}', 'param_nd': 'normal: μh − z·σ√h',
                      'cf_nd': 'Cornish-Fisher (asimetría/√h, curtosis/h)',
                      'hist_nd_overlap': f'retornos compuestos de {horizon} días en ventanas superpuestas '
                                         f'(≈{max(1, len(over) // max(1, horizon))} independientes)'},
        'max_drawdown_pct': round(mdd * 100, 2), 'max_drawdown_date': mdd_date,
        'beta_spy': beta, 'corr_spy': corr_mkt, 'bench_overlap_days': overlap, 'aligned_dates': aligned,
        'nonsync_adjusted': bool(nonsync_info), 'nonsync': nonsync_info,
        'diversification_ratio': round(divers, 2) if divers else None,
        'covariance_model': model,
        'window': {'method': 'pairwise' if pairwise else 'intersection', 'from': common[0], 'to': last, 'days': n,
                   'longest_history_days': longest, 'truncated_by': truncated_by, 'min_history_days': min_hist},
        'excluded_short': excluded_short,
        'excluded_value_pct': round(100.0 * short_val / (total + short_val), 2) if short_val > 0 else 0.0,
        'risk_policy': {'artifact': 'policy.risk', 'semver': pol.get('semver'), 'window': pol.get('window'),
                        'covariance': pol.get('covariance'), 'sharpe': pol.get('sharpe'),
                        'rf_basis': basis, 'ewma_lambda': lam},
        'backtest95': backtest,
        'worst_days': [{'date': d, 'pct': round(r * 100, 2), 'usd': round(r * total, 2)} for r, d in worst],
        'positions': positions,
        'correlation': {'symbols': syms, 'matrix': [[corr[a][b] for b in syms] for a in syms]},
        'histogram': hist_bins,
    }


def _histogram(x, bins):
    lo, hi = min(x), max(x)
    if hi <= lo:
        return {'edges_pct': [round(lo * 100, 3)], 'counts': [len(x)]}
    step = (hi - lo) / bins
    counts = [0] * bins
    for v in x:
        counts[min(bins - 1, int((v - lo) / step))] += 1
    return {'edges_pct': [round((lo + i * step) * 100, 3) for i in range(bins + 1)], 'counts': counts}


# ── orquestación (red) ───────────────────────────────────────────────────────
def build_report(positions, horizon=10, rng='1y', getter=None, fx_fn=None, max_positions=30):
    """positions: [{symbol, shares, label?}] o [{symbol, usd, label?}] → reporte
    + lo excluido.

    `usd` (pedido 2026-09-30, "armar una cartera rápida" en DÓLARES): se
    convierte a acciones con el ÚLTIMO CIERRE COMÚN de la misma historia que se
    usa para el cálculo (convertido a USD) — nunca se adivina un precio. La
    conversión se devuelve en `converted` para que la UI la muestre.

    Los errores llevan `error_code` estable (no_positions · data_unavailable ·
    short_history · zero_value) para que la UI dé un mensaje bilingüe claro."""
    from concurrent.futures import ThreadPoolExecutor
    from core.http import _safe_ticker
    if fx_fn is None:
        from core.quotes import _fx_to_usd as fx_fn
    clean, usd_amt, labels = {}, {}, {}
    for p in positions[:max_positions]:
        if not isinstance(p, dict):
            continue
        sym = _safe_ticker(p.get('symbol')) or ''     # va en la URL: validar
        if not sym:
            continue
        sh = us = None
        try:
            sh = float(p['shares']) if p.get('shares') not in (None, '') else None
        except (TypeError, ValueError):
            sh = None
        try:
            us = float(p['usd']) if p.get('usd') not in (None, '') else None
        except (TypeError, ValueError):
            us = None
        ok = False
        if sh is not None and math.isfinite(sh) and sh > 0:
            clean[sym] = clean.get(sym, 0) + sh
            ok = True
        if us is not None and math.isfinite(us) and 0 < us <= 1e10:
            usd_amt[sym] = usd_amt.get(sym, 0) + us
            clean.setdefault(sym, 0.0)
            ok = True
        if ok:
            labels[sym] = str(p.get('label') or sym)[:80]
    if not clean:
        return {'ok': False, 'error_code': 'no_positions',
                'error': 'no hay posiciones con ticker y cantidad (acciones o dólares)'}
    syms = list(clean) + [BENCH]
    with ThreadPoolExecutor(max_workers=8) as ex:
        irx_fut = ex.submit(fetch_history, RF_SYMBOL, '1mo', getter)       # D2: tasa libre de riesgo, misma caché
        got = dict(zip(syms, ex.map(lambda s: fetch_history(s, rng, getter), syms)))
        try:
            irx, _c = irx_fut.result()
        except Exception:  # noqa: BLE001
            irx = {}
    rf, rf_source = (irx[max(irx)] / 100.0, f'T-bill 13 semanas ({RF_SYMBOL}) {irx[max(irx)]:.2f} % al {max(irx)}') \
        if irx else (0.0, 'sin dato — 0 % (no se pudo bajar ^IRX)')
    histories, fx, excluded, fx_info = {}, {}, [], {}
    for s in clean:
        h, cur = got[s]
        if len(h) < 60:
            excluded.append({'symbol': s, 'label': labels[s], 'reason': 'sin historia suficiente de precios',
                             'reason_code': 'no_history'})
            continue
        raw_cur = cur or 'USD'
        cur = 'GBP' if cur == 'GBp' else (cur or 'USD').upper()
        if cur != 'USD':
            # L2-01 / L3-14: tipo de cambio DIARIO alineado por fecha (el riesgo cambiario entra en el cálculo);
            # sin serie → la tasa de hoy, como antes, y se dice
            try:
                fxs = fx_series(raw_cur, rng, getter)
            except Exception:  # noqa: BLE001
                fxs = None
            if fxs:
                al = align_fx(h, fxs[0])
                if len(al) >= 60:
                    histories[s], fx[s] = {d: h[d] for d in al}, al
                    fx_info[s] = {'ccy': raw_cur, 'method': 'daily', 'source': fxs[1].get('source'),
                                  'as_of': fxs[1].get('as_of')}
                    continue
        rate = fx_fn(cur)
        if not rate:
            excluded.append({'symbol': s, 'label': labels[s], 'reason': f'sin tipo de cambio {cur}→USD',
                             'reason_code': 'no_fx'})
            continue
        if (got[s][1] or '') == 'GBp':
            rate = rate / 100.0            # precio en peniques
        histories[s], fx[s] = h, rate
        if cur != 'USD':
            fx_info[s] = {'ccy': raw_cur, 'method': 'spot', 'source': 'yahoo_live (tasa de hoy)',
                          'note_es': 'tipo de cambio de HOY aplicado a toda la serie: el riesgo cambiario no entra',
                          'note_en': "TODAY's exchange rate applied to the whole series: currency risk is not included"}
    # dólares → acciones al último cierre COMÚN (la fecha que usa compute)
    converted = []
    if usd_amt and histories:
        common = set.intersection(*(set(histories[s]) for s in histories))
        last = max(common) if common else None
        for s in list(usd_amt):
            if s not in histories:
                continue
            h = histories[s]
            d = last if last in h else max(h)
            px_usd = h[d] * _fx_at(fx, s, d)
            if px_usd > 0:
                n = usd_amt[s] / px_usd
                clean[s] += n
                converted.append({'symbol': s, 'usd': round(usd_amt[s], 2), 'price_usd': round(px_usd, 4),
                                  'shares': round(n, 6), 'date': d})
    shares = {s: clean[s] for s in histories if clean[s] > 0}
    if not histories:
        rep = {'ok': False, 'error_code': 'data_unavailable',
               'error': 'no se pudieron obtener precios históricos (proveedor de datos no disponible o tickers sin historia)'}
    else:
        from core.instruments import nonsync as _nonsync
        rep = compute({s: histories[s] for s in shares}, shares, fx, bench=got[BENCH][0] or None,
                      horizon=horizon, rf=rf, rf_source=rf_source, nonsync={s for s in shares if _nonsync(s)})
        if not rep.get('ok') and 'error_code' not in rep:
            err = rep.get('error') or ''
            rep['error_code'] = ('short_history' if 'insuficiente' in err
                                 else 'zero_value' if 'cero' in err else 'data_unavailable')
    for x in rep.get('excluded_short') or []:      # L2-14 (policy.risk 2.0.0): fuera, con su valor y por qué
        excluded.append({'symbol': x['symbol'], 'label': labels.get(x['symbol'], x['symbol']),
                         'reason': f"historia corta ({x['history_days']} días; se piden ≥ {x['min_history_days']}): "
                                   'fuera del cálculo para no recortar la ventana de las demás',
                         'reason_en': f"short history ({x['history_days']} days; ≥ {x['min_history_days']} needed): "
                                      'left out so it does not trim the window of the others',
                         'reason_code': 'short_history', 'value_usd': x['value_usd']})
    rep['excluded'] = excluded
    rep['labels'] = labels
    rep['converted'] = converted
    unadj = []
    liq = risk_policy().get('liquidity') or _POLICY_CODE['liquidity']
    from core.risk_models import liquidity as _liquidity
    for p in rep.get('positions') or []:
        m = history_meta(p['symbol'], rng) or {}
        p['adjusted'] = bool(m.get('adjusted', True))
        p['exchange_tz'] = m.get('tz')
        if not p['adjusted']:
            unadj.append(p['symbol'])
        # L2-16: liquidez con el volumen REAL del proveedor (sin volumen → None, nunca se inventa)
        adv = m.get('adv')
        if adv and adv.get('adv_value'):
            adv_usd = adv['adv_value'] * (p.get('fx_to_usd') or 1.0)
            lq = _liquidity(p['value_usd'], adv_usd, float(liq.get('participation', 0.2)),
                            float(liq.get('flag_days', 5.0)))
            p['liquidity'] = dict(lq or {}, adv_usd=round(adv_usd, 2), adv_days=adv.get('n'), as_of=adv.get('as_of'))
        else:
            p['liquidity'] = None
    rep['unadjusted_symbols'] = unadj
    rep['liquidity_flags'] = [p['symbol'] for p in rep.get('positions') or [] if (p.get('liquidity') or {}).get('flag')]
    # cada serie usada lleva su fuente y su fecha (BRECHAS bloque 2: la historia propia primero)
    series = {}
    for sym in list(shares) + [BENCH]:
        m = history_meta(sym, rng) or {}
        if m:
            series[sym] = {'source': m.get('source') or 'yahoo_live', 'as_of': m.get('as_of'),
                           'adjusted': bool(m.get('adjusted', True)), 'n': m.get('n')}
    rep['series'] = series
    rep['fx'] = fx_info
    own = sorted(k for k, v in series.items() if str(v.get('source') or '').startswith('khipus_eod'))
    rep['source'] = (('Historia propia de Khipus (cierres diarios guardados) para: ' + ', '.join(own) + '; '
                      if own else '') + 'Yahoo Finance (precios diarios ajustados' +
                     ('; cierres SIN ajustar por dividendos/splits en: ' + ', '.join(unadj) if unadj else '') + ')')
    # REGLA BILINGÜE: la misma frase en inglés (engine/riskreport.js elige por idioma)
    rep['source_es'] = rep['source']
    rep['source_en'] = (('Khipus own history (stored daily closes) for: ' + ', '.join(own) + '; '
                         if own else '') + 'Yahoo Finance (adjusted daily prices' +
                        ('; closes NOT adjusted for dividends/splits in: ' + ', '.join(unadj) if unadj else '') + ')')
    rep['generated_at'] = datetime.now(timezone.utc).isoformat()
    return rep
