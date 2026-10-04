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
                           'n': len(out)}
    return out, cur


def history_meta(symbol, rng='1y'):
    """{adjusted, tz, gmtoffset, n} de la última serie bajada (D1) o None."""
    return _HIST_META.get((symbol, rng))


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


def compute(histories, shares, fx, bench=None, horizon=10, rf=0.0, rf_source=None):
    """histories: {sym: {date: price}} · shares: {sym: n} · fx: {sym: moneda→USD}.
    bench: {date: price} del S&P 500 (opcional). rf: tasa libre de riesgo anual
    (decimal; D2: T-bill 13 semanas ^IRX) con su fuente. Devuelve el reporte (dict)."""
    syms = [s for s in shares if histories.get(s)]
    if not syms:
        return {'ok': False, 'error': 'sin historia de precios para ninguna posición'}
    common = sorted(set.intersection(*(set(histories[s]) for s in syms)))
    if len(common) < 60:
        return {'ok': False, 'error': f'historia común insuficiente ({len(common)} días; se necesitan ≥ 60)'}
    last = common[-1]
    values = {s: shares[s] * histories[s][last] * fx.get(s, 1.0) for s in syms}
    total = sum(values.values())
    if total <= 0:
        return {'ok': False, 'error': 'valor de cartera cero'}
    w = {s: values[s] / total for s in syms}
    rets = {s: _returns(histories[s], common) for s in syms}
    n = len(common) - 1
    port = [sum(w[s] * rets[s][i] for s in syms) for i in range(n)]

    sig_d = _std(port)
    mu_d = _mean(port)
    srt = sorted(port)

    def var_block(conf):
        q = 1 - conf
        hist = -_quantile(srt, q)
        tail = [r for r in port if r <= _quantile(srt, q)]
        cvar = -_mean(tail) if tail else hist
        param = -(mu_d - Z[conf] * sig_d)
        scale = math.sqrt(horizon)
        return {'conf': conf,
                'hist_1d_pct': round(hist * 100, 3), 'hist_1d_usd': round(hist * total, 2),
                'param_1d_pct': round(param * 100, 3), 'param_1d_usd': round(param * total, 2),
                'hist_nd_pct': round(hist * scale * 100, 3), 'hist_nd_usd': round(hist * scale * total, 2),
                'cvar_1d_pct': round(cvar * 100, 3), 'cvar_1d_usd': round(cvar * total, 2)}

    v95, v99 = var_block(0.95), var_block(0.99)

    # covarianza, contribución al riesgo, correlaciones
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
    # D1: cuántos días se emparejaron de verdad con el índice y qué rango usó cada símbolo
    # (un índice corrido un día hunde la correlación: aquí se ve, no se adivina)
    aligned = {s: {'from': common[0], 'to': common[-1], 'n': len(common)} for s in syms}

    # backtest del VaR 95 % fuera de muestra (D3) — el "en muestra" va dentro, de referencia
    backtest = rolling_backtest(port, srt, 0.95)
    worst = sorted(((port[i], common[i + 1]) for i in range(n)))[:5]
    # D2: retorno anual COMPUESTO (lo que de verdad ganó quien mantuvo la cartera) y
    # aritmético aparte (insumo del VaR paramétrico); Sharpe = (compuesto − rf) / vol
    vol_ann = sig_d * math.sqrt(TRADING_DAYS)
    ret_geom = (eq ** (TRADING_DAYS / n) - 1.0) if (n > 0 and eq > 0) else 0.0
    ret_arith = mu_d * TRADING_DAYS
    rf = float(rf or 0.0)
    sharpe = round((ret_geom - rf) / vol_ann, 2) if vol_ann else None

    positions = [{'symbol': s, 'shares': shares[s], 'price': round(histories[s][last], 4),
                  'value_usd': round(values[s], 2), 'weight_pct': round(w[s] * 100, 2),
                  'vol_ann_pct': round(sd[s] * math.sqrt(TRADING_DAYS) * 100, 2),
                  'risk_contrib_pct': round(contrib[s] * 100, 2)} for s in syms]
    positions.sort(key=lambda p: -p['risk_contrib_pct'])
    hist_bins = _histogram(port, 30)
    return {
        'ok': True, 'as_of': last, 'days': n, 'from': common[0], 'horizon_days': horizon,
        'portfolio_value_usd': round(total, 2),
        'vol_daily_pct': round(sig_d * 100, 3),
        'vol_ann_pct': round(vol_ann * 100, 2),
        'return_ann_pct': round(ret_geom * 100, 2),            # compuesto (geométrico)
        'return_arith_ann_pct': round(ret_arith * 100, 2),     # media diaria × 252
        'sharpe': sharpe, 'risk_free_pct': round(rf * 100, 2),
        'risk_free_source': rf_source or 'sin dato — 0 %',
        'sharpe_method': '(retorno anual compuesto − tasa libre de riesgo) / volatilidad anual',
        'var95': v95, 'var99': v99,
        'max_drawdown_pct': round(mdd * 100, 2), 'max_drawdown_date': mdd_date,
        'beta_spy': beta, 'corr_spy': corr_mkt, 'bench_overlap_days': overlap, 'aligned_dates': aligned,
        'diversification_ratio': round(divers, 2) if divers else None,
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
def build_report(positions, horizon=10, rng='1y', getter=None, fx_fn=None):
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
    for p in positions[:30]:
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
    histories, fx, excluded = {}, {}, []
    for s in clean:
        h, cur = got[s]
        if len(h) < 60:
            excluded.append({'symbol': s, 'label': labels[s], 'reason': 'sin historia suficiente de precios',
                             'reason_code': 'no_history'})
            continue
        cur = 'GBP' if cur == 'GBp' else (cur or 'USD').upper()
        rate = fx_fn(cur)
        if not rate:
            excluded.append({'symbol': s, 'label': labels[s], 'reason': f'sin tipo de cambio {cur}→USD',
                             'reason_code': 'no_fx'})
            continue
        if (got[s][1] or '') == 'GBp':
            rate = rate / 100.0            # precio en peniques
        histories[s], fx[s] = h, rate
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
            px_usd = h[d] * fx[s]
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
        rep = compute({s: histories[s] for s in shares}, shares, fx, bench=got[BENCH][0] or None,
                      horizon=horizon, rf=rf, rf_source=rf_source)
        if not rep.get('ok') and 'error_code' not in rep:
            err = rep.get('error') or ''
            rep['error_code'] = ('short_history' if 'insuficiente' in err
                                 else 'zero_value' if 'cero' in err else 'data_unavailable')
    rep['excluded'] = excluded
    rep['labels'] = labels
    rep['converted'] = converted
    unadj = []
    for p in rep.get('positions') or []:
        m = history_meta(p['symbol'], rng) or {}
        p['adjusted'] = bool(m.get('adjusted', True))
        p['exchange_tz'] = m.get('tz')
        if not p['adjusted']:
            unadj.append(p['symbol'])
    rep['unadjusted_symbols'] = unadj
    rep['source'] = ('Yahoo Finance (precios diarios ajustados' +
                     ('; cierres SIN ajustar por dividendos/splits en: ' + ', '.join(unadj) if unadj else '') + ')')
    rep['generated_at'] = datetime.now(timezone.utc).isoformat()
    return rep
