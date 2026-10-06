"""core/portfolio_report.py — REPORTE DE CARTERA (a pedido, diario, semanal o mensual).

Pedido (2026-10-02): "generar reportes, ya sean mensuales, diarios o solo de una
vez o a pedido, en base a tus carteras en relación con tu posición inicial, que
te dé gráficos… como un NotebookLM pero que el contexto sea tu cartera".

Contenido (todo con datos reales; la IA solo redacta el resumen con guardián):
  · Rendimiento: valor hoy vs posición INICIAL (lo invertido o el capital de
    partida) y vs el inicio del periodo; comparado con el S&P 500 (SPY).
  · Curva de valor diaria (cartera vs SPY, base 100) — supone que tuviste las
    MISMAS acciones todo el periodo (se rotula).
  · Quién sumó y quién restó (contribución en USD por posición).
  · Riesgo y acciones sugeridas (core/portfolio_advisor).
  · Noticias del periodo sobre tus posiciones (core/news_feed), con fecha.
  · Resumen en lenguaje simple (IA con guardián de cifras; plantilla si no hay IA).
"""
import logging
import math
from datetime import date, datetime, timedelta, timezone

log = logging.getLogger('khipu')
PERIOD_DAYS = {'day': 1, 'week': 7, 'month': 31, 'quarter': 92, 'since_start': None}


def _f(v, d=None):
    try:
        x = float(v)
        return x if math.isfinite(x) else d
    except (TypeError, ValueError):
        return d


def _histories(symbols, rng, fetch=None):
    from concurrent.futures import ThreadPoolExecutor
    from core.risk_report import fetch_history
    fetch = fetch or fetch_history
    with ThreadPoolExecutor(max_workers=8) as ex:
        return dict(zip(symbols, ex.map(lambda s: fetch(s, rng), symbols)))


def build(positions, start_value=None, start_date=None, period='month', profile=None, cash_usd=0.0,
          lang='es', fetch=None, fx_fn=None, advisor=None, news=None):
    """positions: [{id?, symbol, label, shares, cost_usd?}] (acciones actuales)."""
    es = not str(lang).startswith('en')
    period = period if period in PERIOD_DAYS else 'month'
    pos = [p for p in (positions or []) if isinstance(p, dict) and p.get('symbol') and _f(p.get('shares'), 0) > 0][:30]
    if not pos:
        return {'ok': False, 'error_code': 'no_positions',
                'error': 'La cartera no tiene posiciones cotizadas.' if es else 'The portfolio has no listed positions.'}
    today = date.today()
    sd = None
    try:
        sd = date.fromisoformat(str(start_date)[:10]) if start_date else None
    except ValueError:
        sd = None
    if period == 'since_start':
        p_from = sd or (today - timedelta(days=365))
    else:
        p_from = today - timedelta(days=PERIOD_DAYS[period])
    span = (today - min(p_from, sd or p_from)).days
    rng = '1y' if span <= 360 else '2y' if span <= 720 else '5y'
    if fx_fn is None:
        from core.quotes import _fx_to_usd as fx_fn
    syms = sorted({p['symbol'].upper() for p in pos})
    got = _histories(syms + ['SPY'], rng, fetch)
    series, fx, missing = {}, {}, []
    for s in syms:
        h, cur = got.get(s) or ({}, None)
        if not h or len(h) < 2:
            missing.append(s)
            continue
        cur = 'GBP' if cur == 'GBp' else (cur or 'USD').upper()
        rate = fx_fn(cur) or None
        if not rate:
            missing.append(s)
            continue
        if (got[s][1] or '') == 'GBp':
            rate /= 100.0
        series[s], fx[s] = h, rate
    if not series:
        return {'ok': False, 'error_code': 'data_unavailable',
                'error': 'No se pudieron obtener precios históricos.' if es else 'Could not fetch price history.'}
    shares = {}
    for p in pos:
        s = p['symbol'].upper()
        if s in series:
            shares[s] = shares.get(s, 0.0) + _f(p['shares'], 0.0)
    dates = sorted(set.intersection(*(set(series[s]) for s in shares)))
    dates = [d for d in dates if d >= p_from.isoformat()] or dates[-2:]
    if len(dates) < 2:
        dates = sorted(set.intersection(*(set(series[s]) for s in shares)))[-2:]
    spy = (got.get('SPY') or ({}, None))[0] or {}
    cash = max(0.0, _f(cash_usd, 0.0))

    def value_at(d):
        return sum(shares[s] * series[s][d] * fx[s] for s in shares) + cash
    curve = []
    v0 = value_at(dates[0])
    spy0 = spy.get(dates[0])
    for d in dates:
        v = value_at(d)
        curve.append({'d': d, 'value': round(v, 2), 'idx': round(v / v0 * 100, 3) if v0 else None,
                      'spy_idx': round(spy[d] / spy0 * 100, 3) if spy0 and spy.get(d) else None})
    v_now, v_from = curve[-1]['value'], curve[0]['value']
    spy_ret = (curve[-1]['spy_idx'] - 100) if curve[-1]['spy_idx'] is not None else None
    contrib = []
    for p in pos:
        s = p['symbol'].upper()
        if s not in shares:
            continue
        a, b = series[s].get(dates[0]), series[s].get(dates[-1])
        if a is None or b is None:
            continue
        n = _f(p['shares'], 0.0)
        cost = _f(p.get('cost_usd'))
        contrib.append({'symbol': s, 'label': p.get('label') or s, 'value_usd': round(n * b * fx[s], 2),
                        'change_pct': round((b / a - 1) * 100, 2), 'contrib_usd': round(n * (b - a) * fx[s], 2),
                        'pnl_vs_cost_usd': round(n * b * fx[s] - cost, 2) if cost else None,
                        'pnl_vs_cost_pct': round((n * b * fx[s] / cost - 1) * 100, 2) if cost else None})
    contrib.sort(key=lambda x: -x['contrib_usd'])
    cost_total = sum(_f(p.get('cost_usd'), 0.0) for p in pos)
    base = _f(start_value) or (cost_total + cash if cost_total else None)
    perf = {'value_now_usd': round(v_now, 2), 'period_from': dates[0], 'period_to': dates[-1],
            'period_change_usd': round(v_now - v_from, 2), 'period_change_pct': round((v_now / v_from - 1) * 100, 2) if v_from else None,
            'spy_period_pct': round(spy_ret, 2) if spy_ret is not None else None,
            'initial_usd': round(base, 2) if base else None,
            'since_start_usd': round(v_now - base, 2) if base else None,
            'since_start_pct': round((v_now / base - 1) * 100, 2) if base else None,
            'start_date': sd.isoformat() if sd else None}
    if perf['spy_period_pct'] is not None and perf['period_change_pct'] is not None:
        perf['vs_spy_pts'] = round(perf['period_change_pct'] - perf['spy_period_pct'], 2)
    # pico/caída del periodo
    peak, mdd = curve[0]['value'], 0.0
    for c in curve:
        peak = max(peak, c['value'])
        mdd = min(mdd, c['value'] / peak - 1 if peak else 0)
    perf['period_max_drawdown_pct'] = round(mdd * 100, 2)

    holdings = [{'entity_id': p.get('id'), 'label': p.get('label') or p['symbol'], 'symbol': p['symbol'],
                 'weight_pct': (next((c['value_usd'] for c in contrib if c['symbol'] == p['symbol'].upper()), 0) / v_now * 100) if v_now else 0}
                for p in pos]
    try:
        from core import portfolio_advisor
        adv = (advisor or portfolio_advisor.analyze)(
            [{'id': p.get('id'), 'symbol': p['symbol'], 'label': p.get('label'), 'shares': p['shares'],
              'cost_usd': p.get('cost_usd')} for p in pos], profile=profile, lang=lang, cash_usd=cash)
    except Exception as e:  # noqa: BLE001
        log.info('portfolio_report advisor: %s', type(e).__name__)
        adv = {'ok': False}
    try:
        from core import news_feed
        nd = max(2, min(30, (today - date.fromisoformat(dates[0])).days or 2))
        nw = (news or news_feed.portfolio_news)(holdings, days=nd, limit=12, lang=lang)
    except Exception as e:  # noqa: BLE001
        log.info('portfolio_report news: %s', type(e).__name__)
        nw = {'items': []}
    rep = {'ok': True, 'lang': 'es' if es else 'en', 'period': period, 'generated_at': datetime.now(timezone.utc).isoformat(),
           'performance': perf, 'curve': curve[-260:], 'contributions': contrib,
           'allocation': [{'label': c['label'], 'value_usd': c['value_usd'],
                           'weight_pct': round(c['value_usd'] / v_now * 100, 2) if v_now else 0} for c in contrib] +
                         ([{'label': 'Caja' if es else 'Cash', 'value_usd': round(cash, 2),
                            'weight_pct': round(cash / v_now * 100, 2) if v_now else 0}] if cash else []),
           'advisor': {k: adv.get(k) for k in ('health', 'kpis', 'actions', 'profile', 'disclaimer')} if adv.get('ok') else None,
           'news': nw.get('items', []), 'missing': missing,
           'assumption': ('La curva supone que tuviste las mismas acciones durante todo el periodo.' if es else
                          'The curve assumes you held the same shares for the whole period.'),
           'source': 'Yahoo Finance (cierres diarios) · Finnhub/GDELT (noticias)'}
    rep['summary'] = summarize(rep)
    return rep


def summarize(rep):
    es = rep.get('lang') == 'es'
    p = rep['performance']
    best = rep['contributions'][0] if rep['contributions'] else None
    worst = rep['contributions'][-1] if len(rep['contributions']) > 1 else None
    facts = [f"Periodo {p['period_from']} a {p['period_to']}: la cartera pasó a valer {p['value_now_usd']} USD, "
             f"cambio {p['period_change_usd']} USD ({p['period_change_pct']} %); el S&P 500 hizo {p['spy_period_pct']} %."]
    if p.get('initial_usd'):
        facts.append(f"Desde la posición inicial ({p['initial_usd']} USD): {p['since_start_usd']} USD ({p['since_start_pct']} %).")
    for c in rep['contributions'][:6]:
        facts.append(f"{c['label']}: {c['change_pct']} % en el periodo, aportó {c['contrib_usd']} USD.")
    adv = rep.get('advisor') or {}
    for a in (adv.get('actions') or [])[:3]:
        facts.append(f"Acción sugerida {a['id']}: {a['kind']} {a['label']} — {a['why_es']}")
    for n in rep.get('news', [])[:5]:
        facts.append(f"Noticia ({n['published_at'][:10]}, {', '.join(n['holdings'])}): {n['title']}")
    sys_ = ('Eres el analista de Khipus Finance Intelligence y escribes el resumen de un reporte de cartera para un '
            'inversionista SIN experiencia. 5-8 frases claras: cómo le fue en el periodo y desde el inicio, frente '
            'al S&P 500, qué posiciones explican el resultado, qué noticias importan (con su fecha) y qué conviene '
            'revisar (las acciones sugeridas, por su id). Usa SOLO los datos dados; no inventes cifras. Cierra '
            'recordando que es un análisis automático de IA, no asesoría personalizada. Responde en ' +
            ('español.' if es else 'English.'))
    try:
        from core import ai
        from core.ai_usage import ai_context
        if ai._ai_configured():
            with ai_context('reporte_cartera'):
                text, model = ai._ai_complete(sys_, '\n'.join(facts), max_tokens=650, tier='deep')
            if text and text.strip():
                return {'text': text.strip(), 'ai': True, 'model': model}
    except Exception as e:  # noqa: BLE001
        log.info('portfolio_report summary: %s', str(e)[:120])
    sign = lambda v: ('+' if (v or 0) >= 0 else '')  # noqa: E731
    if es:
        t = (f"En el periodo ({p['period_from']} → {p['period_to']}) tu cartera cambió {sign(p['period_change_pct'])}{p['period_change_pct']} % "
             f"({sign(p['period_change_usd'])}{p['period_change_usd']:,.0f} USD)")
        t += (f"; el S&P 500 hizo {sign(p['spy_period_pct'])}{p['spy_period_pct']} %." if p.get('spy_period_pct') is not None else '.')
        if p.get('initial_usd'):
            t += f" Desde tu posición inicial vas {sign(p['since_start_pct'])}{p['since_start_pct']} %."
        if best:
            t += f" Lo que más sumó: {best['label']} ({sign(best['contrib_usd'])}{best['contrib_usd']:,.0f} USD)."
        if worst and worst['contrib_usd'] < 0:
            t += f" Lo que más restó: {worst['label']} ({worst['contrib_usd']:,.0f} USD)."
        t += ' Análisis automático, no asesoría personalizada.'
    else:
        t = (f"Over the period ({p['period_from']} → {p['period_to']}) your portfolio moved {sign(p['period_change_pct'])}{p['period_change_pct']}% "
             f"({sign(p['period_change_usd'])}{p['period_change_usd']:,.0f} USD)")
        t += (f"; the S&P 500 did {sign(p['spy_period_pct'])}{p['spy_period_pct']}%." if p.get('spy_period_pct') is not None else '.')
        if p.get('initial_usd'):
            t += f" Since your starting position you are {sign(p['since_start_pct'])}{p['since_start_pct']}%."
        if best:
            t += f" Biggest contributor: {best['label']} ({sign(best['contrib_usd'])}{best['contrib_usd']:,.0f} USD)."
        if worst and worst['contrib_usd'] < 0:
            t += f" Biggest drag: {worst['label']} ({worst['contrib_usd']:,.0f} USD)."
        t += ' Automated analysis, not personalized advice.'
    return {'text': t, 'ai': False, 'model': None}
