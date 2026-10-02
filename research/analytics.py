"""research/analytics.py — ANÁLISIS CUANTITATIVO determinista para los agentes.

Pedido (2026-10-02): "los análisis no son tan buenos, quiero algo más profundo".
Antes los agentes recibían series crudas (ingresos, beneficio, FCF…) y tenían
que hacer las cuentas ellos mismos (la IA calcula mal y el guardián de cifras
rechazaba sus resultados). Ahora Khipus CALCULA y les entrega el resultado:

- fundamental_ratios(fin, profile): crecimiento (interanual y anual compuesto),
  márgenes bruto/operativo/neto/FCF y su tendencia, caja neta, deuda/EBITDA,
  rendimiento del flujo de caja libre (FCF ÷ capitalización en vivo), ROIC/ROE,
  dilución de acciones.
- technical_indicators(series, bench): 1 año diario vs S&P 500 — medias de 50 y
  200 días (cruce dorado/de la muerte), RSI(14), distancia al máximo/mínimo de
  52 semanas, máxima caída, rendimientos 1/3/6/12 meses y fuerza RELATIVA vs SPY.
- peer_table(entity, peers): valuación y calidad frente a sus pares del grafo
  (P/E, márgenes, crecimiento) con mediana, prima/descuento y posición.

Todo es puro (sin red ni base): los fetchers viven en research/context.py.
Cada función devuelve (dict, texto_es) — el texto es la EVIDENCIA que lee la IA,
y como trae las cifras calculadas, el guardián de cifras las acepta.
"""
import math


def _f(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _pct(a, b):
    a, b = _f(a), _f(b)
    return round(a / b * 100, 1) if a is not None and b not in (None, 0) else None


def _b(v):
    """USD → texto en miles de millones."""
    v = _f(v)
    return None if v is None else f'{v / 1e9:,.1f} mil millones USD'


def _series(fin, key):
    ys = fin.get('years') or []
    vals = fin.get(key) or []
    return [(y, _f(v)) for y, v in zip(ys, vals)]


def _last_two(pairs):
    ok = [(y, v) for y, v in pairs if v is not None]
    return (ok[-2] if len(ok) > 1 else None), (ok[-1] if ok else None)


def fundamental_ratios(fin, profile=None):
    """fin: get_annual_financials() (USD). profile: get_live_profile() o None."""
    fin = fin or {}
    if not fin.get('available'):
        return None, ''
    profile = profile or {}
    out, parts = {}, []
    rev = _series(fin, 'revenue')
    revs = [(y, v) for y, v in rev if v]
    if len(revs) >= 2:
        (y0, v0), (y1, v1) = revs[-2], revs[-1]
        out['revenue_yoy_pct'] = round((v1 / v0 - 1) * 100, 1) if v0 > 0 else None
        n = len(revs) - 1
        if revs[0][1] > 0 and v1 > 0 and n >= 2:
            out['revenue_cagr_pct'] = round(((v1 / revs[0][1]) ** (1 / n) - 1) * 100, 1)
            out['cagr_years'] = f'{revs[0][0]}–{y1}'
        parts.append(f"Ingresos {y1}: {_b(v1)} ({'+' if (out['revenue_yoy_pct'] or 0) >= 0 else ''}"
                     f"{out['revenue_yoy_pct']} % vs {y0})" if out.get('revenue_yoy_pct') is not None else
                     f'Ingresos {y1}: {_b(v1)}')
        if out.get('revenue_cagr_pct') is not None:
            parts.append(f"crecimiento anual compuesto {out['cagr_years']}: {out['revenue_cagr_pct']} %")
    last_year = revs[-1][0] if revs else None
    first_year = revs[0][0] if revs else None

    def margin(key, label, code):
        s = dict(_series(fin, key))
        r = dict(revs)
        if last_year is None:
            return
        m1 = _pct(s.get(last_year), r.get(last_year))
        m0 = _pct(s.get(first_year), r.get(first_year)) if first_year != last_year else None
        if m1 is None:
            return
        out[code] = m1
        if m0 is not None:
            out[code + '_first'] = m0
            trend = 'mejora' if m1 > m0 + 1 else 'empeora' if m1 < m0 - 1 else 'estable'
            parts.append(f'{label} {m1} % en {last_year} (vs {m0} % en {first_year}: {trend})')
        else:
            parts.append(f'{label} {m1} % en {last_year}')
    margin('gross_profit', 'margen bruto', 'gross_margin_pct')
    margin('operating_income', 'margen operativo', 'operating_margin_pct')
    margin('net_income', 'margen neto', 'net_margin_pct')
    margin('fcf', 'margen de flujo de caja libre', 'fcf_margin_pct')

    _p, cash = _last_two(_series(fin, 'cash'))
    _p, debt = _last_two(_series(fin, 'total_debt'))
    if cash and debt:
        net = cash[1] - debt[1]
        out['net_cash_usd'] = net
        parts.append(('caja neta' if net >= 0 else 'deuda neta') + f' {_b(abs(net))} ({cash[0]})')
    _p, ebitda = _last_two(_series(fin, 'ebitda'))
    if debt and ebitda and ebitda[1] and ebitda[1] > 0:
        out['debt_to_ebitda'] = round(debt[1] / ebitda[1], 2)
        parts.append(f"deuda/EBITDA {out['debt_to_ebitda']}x")
    _p, fcf = _last_two(_series(fin, 'fcf'))
    mcap_b = _f(profile.get('market_cap_usd_b'))
    if fcf and mcap_b:
        out['fcf_yield_pct'] = round(fcf[1] / (mcap_b * 1e9) * 100, 2)
        parts.append(f"rendimiento del flujo de caja libre {out['fcf_yield_pct']} % "
                     f"(FCF {fcf[0]} ÷ capitalización en vivo {mcap_b} mil millones USD)")
        if fcf[1] > 0:
            out['p_fcf'] = round(mcap_b * 1e9 / fcf[1], 1)
            parts.append(f"precio/FCF {out['p_fcf']}x")
    for key, label in (('roic', 'ROIC'), ('roe', 'ROE')):
        _p, v = _last_two(_series(fin, key))
        if v is not None and v[1] is not None:
            val = v[1] * 100 if abs(v[1]) < 5 else v[1]
            out[key + '_pct'] = round(val, 1)
            parts.append(f'{label} {round(val, 1)} % ({v[0]})')
    sh = [(y, v) for y, v in _series(fin, 'shares') if v]
    if len(sh) >= 2 and sh[0][1] > 0:
        d = round((sh[-1][1] / sh[0][1] - 1) * 100, 1)
        out['share_change_pct'] = d
        parts.append(f"acciones en circulación {'+' if d >= 0 else ''}{d} % {sh[0][0]}–{sh[-1][0]} "
                     f"({'dilución' if d > 1 else 'recompras' if d < -1 else 'estable'})")
    for k, lbl in (('pe_trailing', 'P/E (12 meses)'), ('pe_forward', 'P/E estimado')):
        if _f(profile.get(k)):
            out[k] = _f(profile.get(k))
            parts.append(f'{lbl} {round(out[k], 1)}')
    if not parts:
        return None, ''
    return out, ' · '.join(parts)


# ── técnico ──────────────────────────────────────────────────────────────────
def _sma(xs, n):
    return sum(xs[-n:]) / n if len(xs) >= n else None


def _rsi(xs, n=14):
    if len(xs) <= n:
        return None
    gains = losses = 0.0
    for i in range(len(xs) - n, len(xs)):
        d = xs[i] - xs[i - 1]
        gains += max(d, 0)
        losses += max(-d, 0)
    if losses == 0:
        return 100.0
    rs = (gains / n) / (losses / n)
    return round(100 - 100 / (1 + rs), 1)


def _ret(xs, n):
    return round((xs[-1] / xs[-1 - n] - 1) * 100, 1) if len(xs) > n and xs[-1 - n] else None


def technical_indicators(series, bench=None):
    """series/bench: [(ts, close)] diarios (~1 año). Devuelve (dict, texto)."""
    xs = [c for _t, c in series or [] if c]
    if len(xs) < 30:
        return None, ''
    last = xs[-1]
    out = {'last_close': round(last, 2), 'n_days': len(xs)}
    for n, k in ((21, 'ret_1m_pct'), (63, 'ret_3m_pct'), (126, 'ret_6m_pct'), (250, 'ret_12m_pct')):
        out[k] = _ret(xs, n)
    s50, s200 = _sma(xs, 50), _sma(xs, 200)
    out['sma50'], out['sma200'] = (round(s50, 2) if s50 else None), (round(s200, 2) if s200 else None)
    out['rsi14'] = _rsi(xs)
    hi, lo = max(xs[-250:]), min(xs[-250:])
    out['pct_from_52w_high'] = round((last / hi - 1) * 100, 1)
    out['pct_above_52w_low'] = round((last / lo - 1) * 100, 1) if lo else None
    peak, mdd = xs[0], 0.0
    for c in xs[-250:]:
        peak = max(peak, c)
        mdd = min(mdd, c / peak - 1)
    out['max_drawdown_1y_pct'] = round(mdd * 100, 1)
    rets = [math.log(xs[i] / xs[i - 1]) for i in range(max(1, len(xs) - 20), len(xs)) if xs[i - 1]]
    out['vol_20d_pct'] = round(math.sqrt(sum(r * r for r in rets) / max(1, len(rets))) * math.sqrt(252) * 100, 1) if rets else None
    parts = [f'cierre {out["last_close"]}']
    rr = [(lbl, out[k]) for k, lbl in (('ret_1m_pct', '1 mes'), ('ret_3m_pct', '3 meses'), ('ret_6m_pct', '6 meses'),
                                        ('ret_12m_pct', '12 meses')) if out.get(k) is not None]
    if rr:
        parts.append('rendimiento ' + ', '.join(f"{lbl} {'+' if v >= 0 else ''}{v} %" for lbl, v in rr))
    bx = [c for _t, c in bench or [] if c]
    if len(bx) >= 64:
        for n, k, lbl in ((63, 'rel_3m_pct', '3 meses'), (126, 'rel_6m_pct', '6 meses')):
            a, b = _ret(xs, n), _ret(bx, n)
            if a is not None and b is not None:
                out[k] = round(a - b, 1)
                parts.append(f"vs S&P 500 (SPY) a {lbl}: {'+' if out[k] >= 0 else ''}{out[k]} puntos "
                             f"({'le gana' if out[k] > 0 else 'pierde'} al mercado)")
    if s50 and s200:
        out['trend'] = 'alcista' if s50 > s200 and last > s50 else 'bajista' if s50 < s200 and last < s50 else 'mixta'
        parts.append(f"media 50 días {out['sma50']} {'>' if s50 > s200 else '<'} media 200 días {out['sma200']} "
                     f"(tendencia {out['trend']}; precio {'sobre' if last > s200 else 'bajo'} la de 200)")
    elif s50:
        parts.append(f"media 50 días {out['sma50']} (precio {'sobre' if last > s50 else 'bajo'} ella)")
    if out['rsi14'] is not None:
        tag = 'sobrecompra' if out['rsi14'] >= 70 else 'sobreventa' if out['rsi14'] <= 30 else 'zona neutral'
        parts.append(f"RSI(14) {out['rsi14']} ({tag})")
    parts.append(f"a {out['pct_from_52w_high']} % de su máximo de 52 semanas; máxima caída del año "
                 f"{out['max_drawdown_1y_pct']} %")
    if out['vol_20d_pct'] is not None:
        parts.append(f"volatilidad 20 días anualizada {out['vol_20d_pct']} %")
    return out, ' · '.join(parts)


# ── pares ────────────────────────────────────────────────────────────────────
PEER_KEYS = (('pe_trailing', 'P/E'), ('pe_forward', 'P/E estimado'), ('gross_margin', 'margen bruto'),
             ('operating_margin', 'margen operativo'), ('revenue_growth', 'crecimiento de ingresos'))


def _median(vs):
    vs = sorted(v for v in vs if v is not None)
    if not vs:
        return None
    m = len(vs) // 2
    return vs[m] if len(vs) % 2 else (vs[m - 1] + vs[m]) / 2


def _as_pct(v):
    v = _f(v)
    return None if v is None else (v * 100 if abs(v) <= 2 else v)


def peer_table(entity_label, entity_profile, peers):
    """peers: [(label, profile)]. Devuelve (dict, texto) o (None, '') con < 2 pares."""
    peers = [(lbl, p) for lbl, p in peers if p and p.get('available')]
    if len(peers) < 2 or not (entity_profile or {}).get('available'):
        return None, ''
    out, parts = {'peers': [lbl for lbl, _p in peers]}, []
    for key, lbl in PEER_KEYS:
        is_pct = key not in ('pe_trailing', 'pe_forward')
        conv = _as_pct if is_pct else _f
        me = conv(entity_profile.get(key))
        vals = [conv(p.get(key)) for _l, p in peers]
        if is_pct is False:
            vals = [v for v in vals if v and 0 < v < 400]
        med = _median(vals)
        if me is None or med is None or len([v for v in vals if v is not None]) < 2:
            continue
        unit = ' %' if is_pct else 'x'
        if is_pct:
            diff = round(me - med, 1)
            parts.append(f'{lbl} {round(me, 1)}{unit} vs mediana de pares {round(med, 1)}{unit} '
                         f"({'+' if diff >= 0 else ''}{diff} puntos)")
        else:
            prem = round((me / med - 1) * 100) if med else None
            parts.append(f'{lbl} {round(me, 1)}{unit} vs mediana de pares {round(med, 1)}{unit} '
                         f"({'prima' if (prem or 0) >= 0 else 'descuento'} {abs(prem)} %)")
        out[key] = {'entity': me, 'median': med}
    if not parts:
        return None, ''
    lines = [f"{lbl}: P/E {round(_f(p.get('pe_trailing')), 1) if _f(p.get('pe_trailing')) else '—'}, "
             f"capitalización {p.get('market_cap_usd_b') if p.get('market_cap_usd_b') is not None else '—'} mil millones USD"
             for lbl, p in peers]
    text = (f'{entity_label} frente a {len(peers)} pares del grafo ({", ".join(out["peers"])}): ' + ' · '.join(parts)
            + ' || pares: ' + ' ; '.join(lines))
    return out, text
