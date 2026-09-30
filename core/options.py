"""core/options.py — griegas de opciones y REPORTE VEGA (a.k.a. Kappa).

Pedido (2026-09-29, curso MIT): "el reporte Vega mide la sensibilidad de una
cartera a los cambios en la volatilidad del subyacente".

Modelo: Black-Scholes-Merton europeo (con rendimiento de dividendo q = 0).
Datos EN VIVO: precio del subyacente y VOLATILIDAD IMPLÍCITA del contrato
(cadena de opciones de Yahoo). Si el contrato no tiene IV publicada, se usa la
volatilidad HISTÓRICA de 1 año del subyacente y se rotula como tal. Tasa libre
de riesgo: rendimiento del T-bill a 13 semanas (^IRX); sin dato → 0 (rotulado).

Vega = ∂V/∂σ por 1 punto de volatilidad (0,01). Una acción tiene Vega 0.
"""
import math
from datetime import date, datetime, timezone

CONTRACT = 100          # acciones por contrato (EE.UU.)


def _ncdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _npdf(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def bs(S, K, T, r, sigma, kind='call'):
    """Precio y griegas por 1 opción (no por contrato).
    vega: cambio de precio por +1 punto de volatilidad (σ + 0,01).
    theta: por día calendario. rho: por +1 punto de tasa."""
    kind = 'put' if str(kind).lower().startswith('p') else 'call'
    if S <= 0 or K <= 0:
        raise ValueError('S y K deben ser positivos')
    if T <= 0 or sigma <= 0:        # vencida o sin volatilidad → valor intrínseco
        intr = max(0.0, S - K) if kind == 'call' else max(0.0, K - S)
        d = (1.0 if S > K else 0.0) if kind == 'call' else (-1.0 if S < K else 0.0)
        return {'price': intr, 'delta': d, 'gamma': 0.0, 'vega': 0.0, 'theta': 0.0, 'rho': 0.0}
    sq = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sq)
    d2 = d1 - sigma * sq
    disc = math.exp(-r * T)
    if kind == 'call':
        price = S * _ncdf(d1) - K * disc * _ncdf(d2)
        delta = _ncdf(d1)
        theta = (-S * _npdf(d1) * sigma / (2 * sq) - r * K * disc * _ncdf(d2)) / 365.0
        rho = K * T * disc * _ncdf(d2) / 100.0
    else:
        price = K * disc * _ncdf(-d2) - S * _ncdf(-d1)
        delta = _ncdf(d1) - 1.0
        theta = (-S * _npdf(d1) * sigma / (2 * sq) + r * K * disc * _ncdf(-d2)) / 365.0
        rho = -K * T * disc * _ncdf(-d2) / 100.0
    return {'price': price, 'delta': delta, 'gamma': _npdf(d1) / (S * sigma * sq),
            'vega': S * _npdf(d1) * sq / 100.0, 'theta': theta, 'rho': rho}


def years_to(expiry, today=None):
    d = date.fromisoformat(str(expiry)[:10])
    t = today or datetime.now(timezone.utc).date()
    return max(0.0, (d - t).days / 365.0)


# ── datos en vivo ────────────────────────────────────────────────────────────
def _yahoo_json(url, params=None, timeout=10):
    from core.quotes import _Y_SESS, _yahoo_session
    try:
        s, crumb = _yahoo_session()
        p = dict(params or {})
        if crumb:
            p['crumb'] = crumb
        r = s.get(url, params=p, timeout=timeout)
        if r.status_code in (401, 403):
            _Y_SESS['ts'] = 0
            s, crumb = _yahoo_session()
            if crumb:
                p['crumb'] = crumb
            r = s.get(url, params=p, timeout=timeout)
        return r.json() if r.ok else None
    except Exception:  # noqa: BLE001
        return None


def live_option(symbol, expiry, strike, kind, fetch=None):
    """{spot, iv, bid, ask, last, open_interest, currency} del contrato, o {}.
    La IV viene de la cadena publicada por la bolsa (vía Yahoo)."""
    fetch = fetch or _yahoo_json
    ts = int(datetime.fromisoformat(str(expiry)[:10]).replace(tzinfo=timezone.utc).timestamp())
    d = fetch(f'https://query2.finance.yahoo.com/v7/finance/options/{symbol}', {'date': ts})
    res = (((d or {}).get('optionChain') or {}).get('result') or [None])[0] or {}
    quote = res.get('quote') or {}
    chains = (res.get('options') or [{}])[0] or {}
    rows = chains.get('puts' if str(kind).lower().startswith('p') else 'calls') or []
    row = next((c for c in rows if abs(float(c.get('strike', -1)) - float(strike)) < 1e-6), None)
    out = {'spot': quote.get('regularMarketPrice'), 'currency': quote.get('currency'),
           'expirations': [datetime.fromtimestamp(x, tz=timezone.utc).date().isoformat()
                           for x in (res.get('expirationDates') or [])][:24],
           'strikes': [float(x) for x in (res.get('strikes') or [])][:200]}
    if row:
        out.update({'iv': row.get('impliedVolatility'), 'bid': row.get('bid'), 'ask': row.get('ask'),
                    'last': row.get('lastPrice'), 'open_interest': row.get('openInterest'),
                    'contract': row.get('contractSymbol')})
    return out


def chain_meta(symbol, expiry=None, fetch=None):
    """Vencimientos y strikes disponibles (para los selectores de la UI)."""
    fetch = fetch or _yahoo_json
    params = {}
    if expiry:
        params['date'] = int(datetime.fromisoformat(str(expiry)[:10]).replace(tzinfo=timezone.utc).timestamp())
    d = fetch(f'https://query2.finance.yahoo.com/v7/finance/options/{symbol}', params)
    res = (((d or {}).get('optionChain') or {}).get('result') or [None])[0] or {}
    out = {'symbol': symbol, 'spot': (res.get('quote') or {}).get('regularMarketPrice'),
           'expirations': [datetime.fromtimestamp(x, tz=timezone.utc).date().isoformat()
                           for x in (res.get('expirationDates') or [])][:30],
           'strikes': [float(x) for x in (res.get('strikes') or [])][:300],
           'available': bool(res.get('expirationDates'))}
    if not out['available']:
        # la UI distingue "el proveedor no respondió" de "esta acción no tiene opciones"
        out['reason'] = 'data_unavailable' if d is None else 'no_options'
    return out


def risk_free_rate(fetch_hist=None):
    """Rendimiento del T-bill 13 semanas (^IRX, en %) como decimal, o (0, False)."""
    try:
        from core.risk_report import fetch_history
        h, _ = (fetch_hist or fetch_history)('^IRX', '1mo')
        if h:
            return h[max(h)] / 100.0, True
    except Exception:  # noqa: BLE001
        pass
    return 0.0, False


def hist_vol(symbol, fetch_hist=None):
    from core.risk_report import _returns, _std, fetch_history
    h, _ = (fetch_hist or fetch_history)(symbol, '1y')
    ds = sorted(h)
    if len(ds) < 60:
        return None
    return _std(_returns(h, ds)) * math.sqrt(252)


# ── reporte ──────────────────────────────────────────────────────────────────
VOL_SHOCKS = (-10, -5, -2, 2, 5, 10)       # puntos de volatilidad


def vega_report(options, live=None, rate=None, hvol=None, today=None):
    """options: [{symbol, kind, strike, expiry, contracts (+ largo / − corto), label?}]
    live(symbol, expiry, strike, kind) → dict · rate → (r, is_live) · hvol(symbol) → σ|None.
    Revalúa COMPLETO (no solo la aproximación lineal) cada choque de volatilidad."""
    live = live or live_option
    r, r_live = rate if rate is not None else risk_free_rate()
    hvol = hvol or hist_vol
    rows, excluded = [], []
    tot = {'value': 0.0, 'delta_sh': 0.0, 'gamma': 0.0, 'vega': 0.0, 'theta': 0.0}
    scen = {k: 0.0 for k in VOL_SHOCKS}
    for o in options[:40]:
        from core.http import _safe_ticker
        sym = _safe_ticker(o.get('symbol')) or ''
        if not sym:
            excluded.append({'symbol': str(o.get('symbol'))[:20], 'reason': 'ticker inválido'})
            continue
        kind = 'put' if str(o.get('kind', 'call')).lower().startswith('p') else 'call'
        try:
            K, n = float(o.get('strike')), float(o.get('contracts'))
            T = years_to(o.get('expiry'), today)
        except (TypeError, ValueError):
            excluded.append({'symbol': sym, 'reason': 'datos incompletos (strike, vencimiento o contratos)'})
            continue
        lv = live(sym, o.get('expiry'), K, kind) or {}
        S = lv.get('spot')
        if not S:
            excluded.append({'symbol': sym, 'reason': 'sin precio en vivo del subyacente'})
            continue
        iv, iv_src = lv.get('iv'), 'implícita (mercado)'
        if not iv or iv <= 0.0001:
            iv, iv_src = hvol(sym), 'histórica 1 año (el contrato no publica IV)'
        if not iv:
            excluded.append({'symbol': sym, 'reason': 'sin volatilidad implícita ni histórica'})
            continue
        g = bs(S, K, T, r, iv, kind)
        mult = n * CONTRACT
        row = {'symbol': sym, 'label': o.get('label') or sym, 'kind': kind, 'strike': K,
               'expiry': str(o.get('expiry'))[:10], 'contracts': n, 'days': round(T * 365),
               'spot': round(S, 4), 'iv_pct': round(iv * 100, 2), 'iv_source': iv_src,
               'model_price': round(g['price'], 4),
               'market_mid': (round((lv['bid'] + lv['ask']) / 2, 4) if lv.get('bid') and lv.get('ask') else None),
               'value_usd': round(g['price'] * mult, 2), 'delta_shares': round(g['delta'] * mult, 2),
               'gamma': round(g['gamma'] * mult, 4), 'vega_usd': round(g['vega'] * mult, 2),
               'theta_usd_day': round(g['theta'] * mult, 2), 'contract': lv.get('contract'),
               'currency': lv.get('currency')}
        rows.append(row)
        tot['value'] += g['price'] * mult
        tot['delta_sh'] += g['delta'] * mult
        tot['gamma'] += g['gamma'] * mult
        tot['vega'] += g['vega'] * mult
        tot['theta'] += g['theta'] * mult
        for k in VOL_SHOCKS:
            s2 = max(0.0001, iv + k / 100.0)
            scen[k] += (bs(S, K, T, r, s2, kind)['price'] - g['price']) * mult
    if not rows:
        return {'ok': False, 'error_code': 'none_valued', 'error': 'ninguna opción se pudo valorar',
                'excluded': excluded}
    return {'ok': True, 'positions': rows, 'excluded': excluded,
            'totals': {'value_usd': round(tot['value'], 2), 'delta_shares': round(tot['delta_sh'], 2),
                       'gamma': round(tot['gamma'], 4), 'vega_usd': round(tot['vega'], 2),
                       'theta_usd_day': round(tot['theta'], 2)},
            'vol_scenarios': [{'shock_pts': k, 'pnl_usd': round(scen[k], 2)} for k in VOL_SHOCKS],
            'rate': {'value_pct': round(r * 100, 3), 'live': r_live,
                     'source': 'T-bill 13 semanas (^IRX)' if r_live else 'sin dato — se usó 0 %'},
            'model': 'Black-Scholes-Merton (europeo, sin dividendos)',
            'generated_at': datetime.now(timezone.utc).isoformat()}
