"""V7 AccountRisk (INFRA_OPERATIVA §4.2, §3.2; paso 17): la exposición de UNA cuenta de bróker, antes y después de una
orden, con el MISMO kernel que el resto de las vistas.

No se publica con la Generation (depende de la cuenta en vivo, no solo del grafo): se calcula A PEDIDO desde la foto de
la cuenta que el corretaje ya leyó (brokerage/service._evaluate, ≤ 30 s) y desde la generación vigente (GraphView +
Impact). Nunca construye nada (hot.graph(wait=False)): si todavía no hay grafo, la vista dice `available: false` y la
orden sigue (los controles de hoy no dependen de ella).

  · pesos por posición w_i = valor de mercado / patrimonio (después de la orden: la compra suma, la venta resta);
  · peso del SECTOR y del PAÍS de la empresa de la orden (sector/país del catálogo, por el ticker principal);
  · exposición a la CADENA = max_c Σ_i w_i · Ψ[c→i] / 100, con Ψ = la vista Impact (propagate_many del kernel: el %
    de golpe que recibe la empresa i si colapsa el proveedor c). Es la fracción de la cartera que caería por el peor
    proveedor único — un número entre 0 y ~1, no una probabilidad.

Sin IA. Sin red. Las cifras van al grafo foco de la puerta de órdenes (core/gates/focus.order_triples) y al
manifiesto de la decisión (`views`), con la versión de la generación que se leyó.
"""
import hashlib
import json
import time
from datetime import datetime, timezone

TOP_CHAIN = 5


def _ticker_map(g):
    """{TICKER: id de la empresa} del catálogo (ticker principal = `mkt`). Una vez por generación."""
    out = {}
    for n in g.nodes or ():
        t = str(n.get('mkt') or '').strip().upper()
        if t and t not in out:
            out[t] = n.get('id')
    return out


def _reverse_impact(g):
    """{empresa i: [(proveedor c, pct)]} invirtiendo las víctimas de la vista Impact. Una vez por generación."""
    imp = getattr(g, 'impact', None)
    rev = {}
    if imp is None:
        return rev
    for src, (ids, pct, _hop) in imp.victims.items():
        for k, p in zip(ids, pct):
            if k != src and p:
                rev.setdefault(k, []).append((src, float(p)))
    return rev


def _derived(g):
    from core.hotviews import hot
    tm = hot.cached('account.ticker_map', _ticker_map, view=g)
    rev = hot.cached('account.reverse_impact', _reverse_impact, view=g)
    return tm, rev


def _norm(sym):
    return str(sym or '').strip().upper()


def weights_after(positions, equity, order=None):
    """{SÍMBOLO: valor de mercado} después de la orden y el patrimonio de referencia. La compra suma su monto; la
    venta resta (sin bajar de 0). Cripto 'BTC/USD' y la posición 'BTCUSD' de Alpaca son el mismo símbolo."""
    mv = {}
    for p in positions or ():
        s = _norm(p.get('symbol')).replace('/', '')
        try:
            v = abs(float(p.get('market_value') or 0))
        except (TypeError, ValueError):
            v = 0.0
        if s:
            mv[s] = mv.get(s, 0.0) + v
    if order and order.get('est_usd'):
        s = _norm(order.get('symbol')).replace('/', '')
        d = float(order['est_usd'])
        mv[s] = max(0.0, mv.get(s, 0.0) + (d if order.get('side') == 'buy' else -d))
    return mv, (float(equity) if equity else None)


def compute(positions, equity, order=None, graph=None):
    """AccountRisk de una cuenta (y de la orden, si viene). `graph` = GraphView; None → la vigente sin construir."""
    t0 = time.perf_counter()
    if graph is None:
        try:
            from core.hotviews import hot
            graph = hot.graph(wait=False)
        except Exception:  # noqa: BLE001
            graph = None
    out = {'name': 'account', 'available': False, 'as_of': datetime.now(timezone.utc).isoformat(timespec='seconds')}
    mv, eq = weights_after(positions, equity, order)
    if graph is None or not eq or eq <= 0:
        out['reason'] = 'no_graph' if graph is None else 'no_equity'
        return out
    tm, rev = _derived(graph)
    by_id = graph.by_id
    sector, country, unmapped, w_by_id = {}, {}, [], {}
    for sym, v in mv.items():
        w = v / eq
        cid = tm.get(sym)
        if cid is None:
            unmapped.append(sym)
            continue
        n = by_id.get(cid) or {}
        w_by_id[cid] = w_by_id.get(cid, 0.0) + w
        sec = n.get('sector') or 'otros'
        ctry = n.get('country') or '?'
        sector[sec] = sector.get(sec, 0.0) + w
        country[ctry] = country.get(ctry, 0.0) + w
    chain = {}
    for cid, w in w_by_id.items():
        for src, pct in rev.get(cid, ()):
            chain[src] = chain.get(src, 0.0) + w * pct / 100.0
    top = sorted(chain.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_CHAIN]
    out.update(available=True, generation=getattr(graph, 'generation', None),
               graph_version=getattr(graph, 'graph_version', None), equity=round(eq, 2),
               weights={k: round(v / eq, 6) for k, v in sorted(mv.items())},
               sector={k: round(v, 6) for k, v in sorted(sector.items())},
               country={k: round(v, 6) for k, v in sorted(country.items())},
               chain_top=[{'source': k, 'exposure': round(v, 6)} for k, v in top],
               chain_max=round(top[0][1], 6) if top else 0.0, unmapped=sorted(unmapped),
               method='sum_w_psi@1 (Ψ = Impact, propagate_many)')
    if order:
        cid = tm.get(_norm(order.get('symbol')).replace('/', ''))
        n = by_id.get(cid) or {} if cid else {}
        out['order'] = {'company_id': cid, 'sector': n.get('sector') if cid else None,
                        'country': n.get('country') if cid else None,
                        'sector_weight_after': round(sector.get(n.get('sector') or 'otros', 0.0), 6) if cid else None,
                        'country_weight_after': round(country.get(n.get('country') or '?', 0.0), 6) if cid else None,
                        'chain_exposure_after': out['chain_max']}
    body = {k: out[k] for k in ('weights', 'sector', 'country', 'chain_top', 'generation')}
    out['content_sha'] = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    out['ms'] = round((time.perf_counter() - t0) * 1000, 3)
    return out


def order_extra(acc, limits=None):
    """Hechos para el foco de la orden (brokerage/risk.order_facts extra) desde una AccountRisk + límites de política
    (ausentes = la regla no aplica)."""
    lim = limits or {}
    o = (acc or {}).get('order') or {}
    return {'sector_weight_after': o.get('sector_weight_after'), 'max_sector_weight': lim.get('max_sector_weight'),
            'country_weight_after': o.get('country_weight_after'),
            'max_country_weight': lim.get('max_country_weight'),
            'chain_exposure_after': o.get('chain_exposure_after') if acc and acc.get('available') else None,
            'max_chain_exposure': lim.get('max_chain_exposure')}
