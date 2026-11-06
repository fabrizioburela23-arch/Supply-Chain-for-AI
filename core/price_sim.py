"""core/price_sim.py — «¿ya tocó fondo? ¿hasta dónde puede caer?»: simulación Monte Carlo del PRECIO de una acción.

Pedido de Fabrizio (2026-11-06): un inversionista experto pregunta si Nvidia seguirá cayendo o si este es el punto más
bajo. La respuesta honesta no es un «sí/no»: es una DISTRIBUCIÓN con probabilidades, hecha con datos reales y supuestos
a la vista. Esto la calcula la app (no la IA): la IA solo la explica.

Método (simulación histórica filtrada, FHS):
  · cierres diarios ajustados de 2 años (la historia propia de Khipus primero, Yahoo si falta: core.risk_report);
  · residuos estandarizados con la volatilidad EWMA (λ=0,94) → se remuestrean (colas gordas reales, no una normal);
  · volatilidad que parte de la ACTUAL (EWMA) y vuelve a la de 1 año con vida media ~20 días;
  · SIN tendencia (deriva 0): no apuesta a que suba ni a que baje;
  · si hay resultados trimestrales dentro del horizonte (calendario de Finnhub), un SALTO ese día: t de Student (4 g.l.)
    con la desviación de las reacciones REALES de la acción a sus últimos reportes (+15 %), o 2,5 × su volatilidad
    diaria si no hay historia de reportes. Supuesto rotulado.
Salidas por horizonte: percentiles del precio, P(sube), P(que el cierre de HOY sea el más bajo del período) — la
respuesta directa a «¿es el piso?» —, P(tocar −10 %, el mínimo de 52 semanas, −20 %, −30 %), el mínimo esperado y en qué
día cae; los mismos números separados por buen/mal reporte; técnico (RSI, medias de 50/200, caída desde el máximo) y
qué pasó después de caídas de un día ≥ 7 % en la misma historia. Nunca es una recomendación ni un pronóstico seguro."""
import logging
from datetime import date, timedelta

import numpy as np

log = logging.getLogger(__name__)

N_PATHS = 20000
EWMA_LAMBDA = 0.94
VOL_DECAY = 0.965              # vida media ~20 días hábiles hacia la volatilidad de 1 año
EARN_T_DF = 4
EARN_STRESS = 1.15             # el mercado ya está nervioso: +15 % sobre la desviación histórica de las reacciones
BIG_DROP = 0.07
HORIZONS = ((21, '1 mes', '1 month'), (63, '3 meses', '3 months'), (126, '6 meses', '6 months'))


def _rsi(p, n=14):
    d = np.diff(p)
    up, dn = np.where(d > 0, d, 0.0), np.where(d < 0, -d, 0.0)
    au, ad = up[:n].mean(), dn[:n].mean()
    for i in range(n, len(d)):
        au = (au * (n - 1) + up[i]) / n
        ad = (ad * (n - 1) + dn[i]) / n
    return 100.0 if ad == 0 else 100 - 100 / (1 + au / ad)


def _bdays_between(d0, d1):
    """Días hábiles (lun-vie) de d0 (excl.) a d1 (incl.). Sin feriados: ±1 día."""
    n, d = 0, d0
    while d < d1:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def earnings_calendar(symbol, getter=None, today=None):
    """→ (fechas pasadas [(date, hour)], próxima (date, hour) | None, fuente). Finnhub; sin clave → ([], None, None)."""
    from core.config import FINNHUB
    if not FINNHUB and getter is None:
        return [], None, None
    if getter is None:
        from core.http import _safe_get as getter
    today = today or date.today()
    url = (f'https://finnhub.io/api/v1/calendar/earnings?symbol={symbol}&from={(today - timedelta(days=760)).isoformat()}'
           f'&to={(today + timedelta(days=200)).isoformat()}&token={FINNHUB}')
    try:
        data, err = getter(url)
    except Exception:  # noqa: BLE001
        return [], None, None
    rows = (data or {}).get('earningsCalendar') if isinstance(data, dict) and not err else None
    past, nxt = [], None
    for r in rows or []:
        try:
            d = date.fromisoformat(str(r.get('date'))[:10])
        except ValueError:
            continue
        h = str(r.get('hour') or '').lower()
        if d < today or (d == today and r.get('epsActual') is not None):
            past.append((d, h))
        elif nxt is None or d < nxt[0]:
            nxt = (d, h)
    return sorted(past), nxt, 'Finnhub earnings calendar'


def _reaction_moves(dates, closes, past):
    """Reacción REAL del precio a cada reporte: amc → cierre del día hábil siguiente vs el del día del reporte;
    bmo/sin hora → cierre del día del reporte vs el anterior."""
    idx = {d: i for i, d in enumerate(dates)}
    out = []
    for d, h in past:
        ds = d.isoformat()
        if ds not in idx:
            continue
        i = idx[ds]
        j = i + 1 if h == 'amc' else i
        k = j - 1
        if 0 <= k < j < len(closes):
            out.append(closes[j] / closes[k] - 1)
    return out


def simulate(symbol, prices, *, earnings=None, today=None, n_paths=N_PATHS, seed=7, levels=None, fan_days=0):
    """`prices` {fecha: cierre ajustado}; `earnings` = (pasadas, próxima, fuente) de earnings_calendar.
    → dict con todo lo de arriba. Lanza ValueError si la historia es corta."""
    items = sorted((d, float(p)) for d, p in (prices or {}).items() if p and float(p) > 0)
    if len(items) < 150:
        raise ValueError('price history too short (need ~150 daily closes)')
    dates = [d for d, _ in items]
    P = np.array([p for _, p in items])
    last = float(P[-1])
    r = np.diff(np.log(P))
    # ── técnico ──
    p252 = P[-252:]
    tech = {'last_close': round(last, 2), 'last_date': dates[-1], 'rsi14': round(_rsi(P), 1),
            'ma50': round(float(P[-50:].mean()), 2), 'ma200': round(float(P[-200:].mean()), 2),
            'vs_ma200_pct': round((last / P[-200:].mean() - 1) * 100, 1),
            'peak_close': round(float(P.max()), 2), 'drawdown_from_peak_pct': round((last / P.max() - 1) * 100, 1),
            'low_52w_close': round(float(p252.min()), 2), 'high_52w_close': round(float(p252.max()), 2),
            'last_day_change_pct': round((P[-1] / P[-2] - 1) * 100, 2)}
    # ── qué pasó tras caídas de un día ≥ 7 % (misma historia) ──
    episodes = []
    for i, x in enumerate(r[:-1]):
        if x <= np.log(1 - BIG_DROP):
            j = i + 1

            def fwd(h, j=j):
                return round((P[j + h] / P[j] - 1) * 100, 1) if j + h < len(P) else None

            def low(h, j=j):
                return round((P[j:j + h + 1].min() / P[j] - 1) * 100, 1) if j + h < len(P) else None
            episodes.append({'date': dates[j], 'drop_pct': round((np.exp(x) - 1) * 100, 1), 'ret_20d_pct': fwd(20),
                             'ret_60d_pct': fwd(60), 'worst_next_60d_pct': low(60)})
    # ── volatilidad ──
    s2 = float(np.var(r[:30]))
    sig = np.empty(len(r))
    for i, x in enumerate(r):
        sig[i] = np.sqrt(s2)
        s2 = EWMA_LAMBDA * s2 + (1 - EWMA_LAMBDA) * x * x
    z = r / sig
    z = (z - z.mean()) / z.std()
    sig_now, sig_long = float(np.sqrt(s2)), float(r[-252:].std())
    H = max(h for h, _e, _n in HORIZONS)
    sd = np.sqrt(sig_long ** 2 + (sig_now ** 2 - sig_long ** 2) * VOL_DECAY ** np.arange(H))
    # ── resultados trimestrales ──
    today = today or date.today()
    past, nxt, esrc = earnings if earnings else ([], None, None)
    moves = _reaction_moves(dates, P, past or [])
    earn = None
    eday = None
    if nxt:
        react = nxt[0] + timedelta(days=1) if nxt[1] == 'amc' else nxt[0]
        while react.weekday() >= 5:
            react += timedelta(days=1)
        try:
            base = date.fromisoformat(dates[-1])
        except ValueError:
            base = today
        eday = _bdays_between(base, react)
        if not (1 <= eday <= H):
            eday = None
    if eday:
        if len(moves) >= 3:
            sig_e = float(np.sqrt(np.mean(np.square(moves)))) * EARN_STRESS
            how = (f'desviación de las reacciones reales a sus últimos {len(moves)} reportes (+15 %)',
                   f'deviation of the real reactions to its last {len(moves)} reports (+15%)')
        else:
            sig_e = 2.5 * sig_long
            how = ('2,5 × su volatilidad diaria de 1 año (no hay suficientes reportes en la historia)',
                   '2.5 × its 1-year daily volatility (not enough past reports in the history)')
        earn = {'date': nxt[0].isoformat(), 'hour': nxt[1] or None, 'reaction_trading_day': eday,
                'jump_sd_pct': round(sig_e * 100, 2), 'past_reactions_pct': [round(m * 100, 1) for m in moves],
                'method_es': how[0], 'method_en': how[1], 'source': esrc}
    # ── caminos ──
    rng = np.random.default_rng(seed)
    R = z[rng.integers(0, len(z), (n_paths, H))] * sd - 0.5 * sd ** 2
    J = np.zeros(n_paths)
    if earn:
        J = rng.standard_t(EARN_T_DF, n_paths) * sig_e / np.sqrt(EARN_T_DF / (EARN_T_DF - 2))
        R[:, eday - 1] += np.log1p(np.clip(J, -0.6, 0.6))
    paths = last * np.exp(np.cumsum(R, axis=1))
    lv = levels or [('-10%', last * 0.9), ('52w_low', float(p252.min())), ('-20%', last * 0.8), ('-30%', last * 0.7)]
    lv = [(k, v) for k, v in lv if v < last]

    def block(p):
        term, mn = p[:, -1], p.min(axis=1)
        return {'p5': round(float(np.percentile(term, 5)), 2), 'p25': round(float(np.percentile(term, 25)), 2),
                'p50': round(float(np.percentile(term, 50)), 2), 'p75': round(float(np.percentile(term, 75)), 2),
                'p95': round(float(np.percentile(term, 95)), 2),
                'prob_up_pct': round(float((term > last).mean() * 100), 1),
                'prob_today_is_the_low_pct': round(float((mn >= last).mean() * 100), 1),
                'prob_low_within_5pct_of_today_pct': round(float((mn >= last * 0.95).mean() * 100), 1),
                'prob_touch': {k: {'price': round(v, 2), 'pct': round(float((mn < v).mean() * 100), 1)} for k, v in lv},
                'lowest_close_p10': round(float(np.percentile(mn, 10)), 2),
                'lowest_close_p50': round(float(np.median(mn)), 2),
                'lowest_close_p90': round(float(np.percentile(mn, 90)), 2),
                'day_of_low_median': int(np.median(p.argmin(axis=1) + 1))}
    horizons = []
    for h, es, en in HORIZONS:
        horizons.append({'trading_days': h, 'label_es': es, 'label_en': en, **block(paths[:, :h])})
    by_earn = None
    if earn:
        by_earn = {}
        for k, m, es, en in (('good', J > 0.03, 'si el reporte sale bien (reacción > +3 %)', 'if the report goes well (> +3%)'),
                             ('bad', J < -0.03, 'si el reporte decepciona (reacción < −3 %)', 'if the report disappoints (< −3%)')):
            if m.sum() > 200:
                b = block(paths[m, :63])
                by_earn[k] = {'label_es': es, 'label_en': en, 'share_of_paths_pct': round(float(m.mean() * 100), 1),
                              'horizon': '3m', 'p50': b['p50'], 'prob_today_is_the_low_pct': b['prob_today_is_the_low_pct'],
                              'prob_touch': b['prob_touch'], 'lowest_close_p50': b['lowest_close_p50']}
    fan = None
    if fan_days:     # abanico día a día (percentiles por día de negociación) para dibujar el gráfico
        q = np.percentile(paths[:, :min(int(fan_days), H)], [5, 25, 50, 75, 95], axis=0)
        fan = [{'day': i + 1, 'p5': round(float(q[0, i]), 2), 'p25': round(float(q[1, i]), 2),
                'p50': round(float(q[2, i]), 2), 'p75': round(float(q[3, i]), 2), 'p95': round(float(q[4, i]), 2)}
               for i in range(q.shape[1])]
    return {'symbol': symbol, 'as_of_close': dates[-1], 'technical': tech, 'horizons': horizons, 'fan': fan,
            'earnings_event': earn, 'by_earnings_outcome': by_earn, 'big_drop_episodes': episodes,
            'volatility': {'now_ann_pct': round(sig_now * np.sqrt(252) * 100, 1),
                           'one_year_ann_pct': round(sig_long * np.sqrt(252) * 100, 1)},
            'n_paths': n_paths, 'history_days': len(P),
            'method': ('filtered historical simulation: EWMA-standardised daily residuals bootstrapped, vol decays from the '
                       'current EWMA level to the 1-year level (half-life ~20 days), zero drift; earnings day adds a '
                       f'Student-t({EARN_T_DF}) jump'),
            'assumptions_es': ('Sin tendencia (no apuesta a subir ni a bajar); la volatilidad parte de la actual y vuelve a '
                               'la de 1 año; el día de resultados suma un salto del tamaño de las reacciones pasadas. Es '
                               'una distribución de probabilidades con datos reales, NO un pronóstico ni una recomendación: '
                               'noticias nuevas (regulación, China, guía) cambian todo.'),
            'assumptions_en': ('No drift (no bet up or down); volatility starts at the current level and reverts to the '
                               '1-year one; earnings day adds a jump sized like past reactions. A probability distribution '
                               'from real data, NOT a forecast or advice: new news (regulation, China, guidance) changes it.')}
