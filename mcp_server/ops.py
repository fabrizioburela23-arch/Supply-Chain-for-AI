"""mcp_server/ops.py — las operaciones MCP que faltaban (ARQUITECTURA_V2 §15; BRECHAS L4-09, decisión #15).

Orden de la decisión #15 (sugerido, vigente mientras Fabrizio no conteste): run_scenario, get_subgraph,
get_exposure; después find_similar_entities, calculate_correlation y get_history. Todas de SOLO LECTURA, scope
`read`, con los tokens y límites de siempre, y con el contrato común (detail / max_chars, mcp_server/contract.py).

  run_scenario           choque what-if con EL kernel (vistas rápidas: impact.scenario = propagate_block, los
                         parámetros del kernel.params VIGENTE) + pérdida estructural estimada de una cartera.
  get_subgraph           vecindario por relevancia R(v|Q) con presupuesto (core/context_engine.subgraph).
  get_exposure           exposición de una cartera (sector, país, país de los proveedores, cadena vía Ψ —la vista
                         AccountRisk—) o de una empresa (tensor: concentración, países, fuentes de riesgo).
  find_similar_entities  comparables con puntaje POR ESPACIO (cadena compartida, rasgos, categoría) — matrix/tensor.
  calculate_correlation  correlación de retornos diarios (Pearson/Spearman) + error estándar, de la historia
                         propia de Khipus (prices_eod) o, si no la cubre, Yahoo ajustado (core/risk_report).
  get_history            serie de cierres ajustados con fuente y as_of (misma cascada), diaria/semanal/mensual.

Este módulo lo importa mcp_server/tools.py al final (registro único de herramientas).
"""
import math
from datetime import date, datetime, timezone

from mcp_server.tools import InvalidParams, ToolError, _bounded, _now_iso, _resolve_or_fail, tool

STRUCTURAL_NOTE = ('structural estimate from the Khipus supply-chain graph (one kernel: propagate@1 with the active '
                   'kernel.params) — NOT a price forecast; real moves depend on substitutes, inventories and markets')


def _graph():
    from core.hotviews import hot
    v = hot.graph()
    if v is None or v.core is None:
        raise ToolError('the graph is warming up — retry in a few seconds', code='unavailable')
    return v


def _kernel(v):
    try:
        k = dict(v.impact.kernel) if v.impact is not None else None
    except Exception:  # noqa: BLE001
        k = None
    if not k:
        from core.hotviews.views.impact import default_kernel
        k = default_kernel()
    return {kk: k.get(kk) for kk in ('semver', 'method', 'damping', 'max_hops', 'threshold', 'damage_rels')}


def _gen_meta(v):
    return {'generation': v.generation, 'graph_version': v.graph_version, 'graph_source': v.source}


# ════════════════════════════════════════════════════════════════════════════
# run_scenario
# ════════════════════════════════════════════════════════════════════════════
@tool('run_scenario', 'What-if shock on the supply-chain graph (one kernel)', 'read',
      'Structural what-if: shock one or more companies (magnitude 0-1, 1 = it stops supplying) or describe the '
      'scenario in plain words (e.g. "China blockades Taiwan": its direct hits seed the shock). Returns the impact '
      'per company from Khipus\' single propagation kernel (same numbers as the app), reach, hops and, if you pass '
      'positions [{symbol, usd}], the estimated STRUCTURAL loss of that portfolio. Not a price forecast.',
      {'shocks': {'type': 'array', 'minItems': 1, 'maxItems': 20,
                  'items': {'type': 'object', 'properties': {
                      'id': {'type': 'string', 'minLength': 1, 'maxLength': 120},
                      'magnitude': {'type': 'number', 'minimum': 0, 'maximum': 1}}, 'required': ['id']}},
       'scenario': {'type': 'string', 'maxLength': 300, 'description': 'Plain-words what-if (used when shocks is empty).'},
       'factors': {'type': 'string', 'enum': ['active', 'none'], 'default': 'active',
                   'description': 'Include the active systemic factors (fragility) or not.'},
       'top': {'type': 'integer', 'minimum': 1, 'maximum': 100, 'default': 25},
       'positions': {'type': 'array', 'maxItems': 60, 'items': {'type': 'object', 'properties': {
           'symbol': {'type': 'string', 'minLength': 1, 'maxLength': 40},
           'usd': {'type': 'number', 'minimum': 0}}, 'required': ['symbol', 'usd']}}})
def t_run_scenario(ctx, shocks=None, scenario=None, factors='active', top=25, positions=None):
    import numpy as np

    from core.context_engine import canon
    from core.hotviews.views import impact
    if not shocks and not (scenario and str(scenario).strip()):
        raise InvalidParams('shocks or scenario is required')
    v = _graph()
    core = v.core
    x0 = np.zeros(len(core.ids))
    used, unknown, seeded_by, about = [], [], 'shocks', None
    if shocks:
        for it in shocks:
            raw = str(it.get('id') or '')[:120]
            oid = core.resolve(raw) or canon(raw)
            if oid not in core.idx:
                unknown.append(raw)
                continue
            mag = float(it.get('magnitude', 1.0))
            x0[core.idx[oid]] = max(x0[core.idx[oid]], mag)
            used.append({'id': oid, 'label': core.label(oid), 'magnitude': mag})
    else:
        from core import scenario_engine, semantic
        a = scenario_engine.analyze(str(scenario)[:300], semantic._load_snapshot(), lang='en')
        seeded_by = 'scenario_engine (direct hits of the described scenario)'
        if a:
            about = {'theme': a.get('theme_en') or a.get('theme_es'), 'actor': a.get('actor_en'),
                     'disrupted_country': a.get('disrupted'), 'event': a.get('event'),
                     'mechanism': a.get('mechanism_en'), 'seeds': list(a.get('hit') or [])[:20]}
            for oid in (a.get('hit') or [])[:20]:
                if oid in core.idx:
                    x0[core.idx[oid]] = 1.0
                    used.append({'id': oid, 'label': core.label(oid), 'magnitude': 1.0})
    if not used:
        raise ToolError('no company of the scenario exists in the graph — name at least one (search_companies)',
                        code='not_found', data={'unknown_ids': unknown[:20]})
    sc = impact.scenario(core, x0, factors=factors, top=int(top))
    impacts = sc.pop('impacts', {}) or {}
    out = {'shocks': used, 'unknown_ids': unknown, 'seeded_by': seeded_by, 'scenario': about, 'factors': factors,
           'affected': sc['affected'], 'reach_1pct': sc['reach_1'], 'reach_10pct': sc['reach_10'],
           'sum_impact_companies': sc['sum_impact'], 'by_hop': sc['by_hop'],
           'victims': [{'id': x['id'], 'label': x['label'], 'impact_pct': x['pct'], 'hop': x['hop']}
                       for x in sc['victims']],
           'kernel': _kernel(v), **_gen_meta(v),
           'uncertainty': STRUCTURAL_NOTE, 'method': 'matrix.engine.propagate_block on the hot Impact view',
           'source': 'Khipus supply-chain graph + kernel.params (governance release)', 'as_of': _now_iso()}
    if positions:
        from core.hotviews import hot
        from core.hotviews.views.account import _ticker_map
        tm = hot.cached('account.ticker_map', _ticker_map, view=v)
        rows, total, loss = [], 0.0, 0.0
        for p in positions:
            sym = str(p.get('symbol') or '').strip().upper()
            usd = float(p.get('usd') or 0)
            oid = tm.get(sym.replace('/', '')) or canon(sym)
            pct = float(impacts.get(oid, 0.0)) if oid else None
            est = round(usd * pct / 100.0, 2) if pct is not None else None
            total += usd
            loss += est or 0.0
            rows.append({'symbol': sym, 'id': oid, 'usd': usd, 'structural_hit_pct': pct, 'est_loss_usd': est})
        out['portfolio'] = {'positions': rows, 'total_usd': round(total, 2),
                            'est_structural_loss_usd': round(loss, 2),
                            'est_structural_loss_pct': round(100.0 * loss / total, 2) if total else None,
                            'unmapped': [r['symbol'] for r in rows if r['id'] is None],
                            'note': 'loss = value × structural hit of that company; an UPPER-BOUND style structural '
                                    'estimate, not a P&L forecast'}
    return out


# ════════════════════════════════════════════════════════════════════════════
# get_subgraph
# ════════════════════════════════════════════════════════════════════════════
@tool('get_subgraph', 'Relevant subgraph under a budget (context engine)', 'read',
      'Neighborhood of one or more companies in the FLOW graph (suppliers/customers; partners and investors '
      'only as `related`) up to 3 hops, ranked by relevance to your question R(v|Q) (personalized PageRank from '
      'the seeds × systemic impact × confidence) and packed under a character budget; what is left out is '
      'summarized in `tail` (count, weight, hops, countries). Use it instead of get_supply_chain for big neighborhoods.',
      {'seeds': {'type': 'array', 'minItems': 1, 'maxItems': 10,
                 'items': {'type': 'string', 'minLength': 1, 'maxLength': 120}},
       'question': {'type': 'string', 'maxLength': 300,
                    'description': 'Optional: orients relevance (suppliers / customers / what-if).'},
       'depth': {'type': 'integer', 'minimum': 1, 'maximum': 3, 'default': 2},
       'direction': {'type': 'string', 'enum': ['up', 'down', 'both'], 'default': 'both'},
       'budget_chars': {'type': 'integer', 'minimum': 1000, 'maximum': 40000, 'default': 6000},
       'include_partners': {'type': 'boolean', 'default': False},
       'min_confidence': {'type': 'number', 'minimum': 0, 'maximum': 1, 'default': 0}},
      required=['seeds'])
def t_get_subgraph(ctx, seeds, question=None, depth=2, direction='both', budget_chars=6000,
                   include_partners=False, min_confidence=0):
    from core import context_engine as ce
    res = ce.subgraph(seeds, question=question, depth=depth, direction=direction, budget_chars=budget_chars,
                      include_partners=include_partners, min_conf=float(min_confidence or 0))
    if not res['seeds']:
        raise ToolError('none of the seeds exists in the Khipus graph — use search_companies first',
                        code='not_found', data={'unknown': res.get('unknown_seeds')})
    res['source'] = 'Khipus supply-chain graph (context engine)'
    return res


# ════════════════════════════════════════════════════════════════════════════
# get_exposure
# ════════════════════════════════════════════════════════════════════════════
def _prices(symbols):
    from core.quotes import fetch_quotes_live
    q = (_bounded(fetch_quotes_live, 12, list(symbols)) or {}).get('quotes') or {}
    out = {}
    for s, row in q.items():
        px = row.get('live') if isinstance(row.get('live'), (int, float)) else row.get('close')
        if isinstance(px, (int, float)) and px > 0:
            out[s.upper()] = (float(px), row.get('src'), row.get('as_of'))
    return out


def _pct_map(d):
    return [{'key': k, 'pct': round(v * 100, 2)} for k, v in sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))]


@tool('get_exposure', 'Exposure of a portfolio or a company', 'read',
      'Exposure vector. Portfolio (positions [{symbol|id, usd | shares}]): weight by sector, country of the company, '
      'country of its SUPPLIERS (indirect, from the flow tensor) and the worst single upstream supplier for the '
      'whole portfolio via the influence matrix Ψ (fraction of the portfolio hit if that supplier fails). Company '
      '(entity): supplier concentration, supplier countries, upstream risk sources (direct and indirect) and '
      'downstream market cap at risk. Shares are valued with live quotes (with source/as_of).',
      {'positions': {'type': 'array', 'maxItems': 60, 'items': {'type': 'object', 'properties': {
          'symbol': {'type': 'string', 'maxLength': 40}, 'id': {'type': 'string', 'maxLength': 120},
          'usd': {'type': 'number', 'minimum': 0}, 'shares': {'type': 'number', 'minimum': 0}}}},
       'entity': {'type': 'string', 'maxLength': 120, 'description': 'A company instead of a portfolio.'}},
      open_world=True)
def t_get_exposure(ctx, positions=None, entity=None):
    if not positions and not entity:
        raise InvalidParams('positions or entity is required')
    v = _graph()
    if entity and not positions:
        r = _resolve_or_fail(entity)
        from matrix import tensor
        st = tensor.structure(r['id']) or {}
        n = v.by_id.get(r['id']) or {}
        return {'entity': r['id'], 'label': n.get('label') or r['id'], 'sector': n.get('sector'),
                'country': n.get('country'), 'supplier_concentration': st.get('supplier_concentration'),
                'supplier_countries': st.get('supplier_countries'),
                'upstream_risk_sources': st.get('upstream_risk_sources'), 'downstream': st.get('downstream'),
                'method': st.get('method'), 'caps_as_of': st.get('caps_as_of'), **_gen_meta(v),
                'source': 'Khipus flow tensor (matrix/tensor.py) on the current graph generation',
                'as_of': _now_iso()}
    from core.hotviews.views import account
    from core.portfolio_advisor import _resolve_positions
    pos = _resolve_positions(positions)
    need = sorted({p['symbol'] for p in pos if p.get('symbol') and p.get('usd') is None and p.get('shares')})
    px, unpriced, priced_src = {}, [], {}
    if need:
        try:
            px = _prices(need)
        except ToolError:
            px = {}
    rows = []
    for p in pos:
        usd = p.get('usd')
        if usd is None and p.get('shares') and p.get('symbol') in px:
            price, src, as_of = px[p['symbol']]
            usd = p['shares'] * price
            priced_src[p['symbol']] = {'price': price, 'source': src, 'as_of': as_of}
        if usd is None:
            unpriced.append(p.get('symbol') or p.get('entity_id'))
            continue
        rows.append(dict(p, usd=float(usd)))
    total = sum(r['usd'] for r in rows)
    if total <= 0:
        raise ToolError('no position could be valued (give usd, or shares of a listed symbol)', code='no_data',
                        data={'unpriced': unpriced})
    # MISMA matemática que la vista AccountRisk (core/hotviews/views/account.py: Ψ invertido de la vista Impact),
    # pero por id de empresa: así también cuentan las posiciones sin ticker (privadas, ids del grafo)
    tm, rev = account._derived(v)
    sector, country, w_by_id, unmapped = {}, {}, {}, []
    for r in rows:
        nid = r.get('entity_id') or tm.get(str(r.get('symbol') or '').upper().replace('/', ''))
        if not nid or nid not in v.by_id:
            unmapped.append(r.get('symbol') or r.get('entity_id'))
            continue
        w = r['usd'] / total
        n = v.by_id.get(nid) or {}
        w_by_id[nid] = w_by_id.get(nid, 0.0) + w
        sector[n.get('sector') or 'otros'] = sector.get(n.get('sector') or 'otros', 0.0) + w
        country[n.get('country') or '?'] = country.get(n.get('country') or '?', 0.0) + w
    chain = {}
    for nid, w in w_by_id.items():
        for src, pct in rev.get(nid, ()):
            chain[src] = chain.get(src, 0.0) + w * pct / 100.0
    chain_top = sorted(chain.items(), key=lambda kv: (-kv[1], kv[0]))[:account.TOP_CHAIN]
    # país de los PROVEEDORES (indirecto): participación de cada país en los proveedores de cada posición × su peso
    sup_ctry = {}
    try:
        from matrix import tensor
        m = tensor.model()
        for nid, w in w_by_id.items():
            st = tensor.structure(nid, m=m) or {}
            for c in st.get('supplier_countries') or []:
                sup_ctry[c['country']] = sup_ctry.get(c['country'], 0.0) + w * c['share_pct'] / 100.0
    except Exception:  # noqa: BLE001
        sup_ctry = {}
    return {'positions': [{'symbol': r.get('symbol'), 'id': r.get('entity_id'), 'usd': round(r['usd'], 2),
                           'weight_pct': round(100 * r['usd'] / total, 2)} for r in rows],
            'total_usd': round(total, 2), 'unpriced': unpriced, 'valued_with_quotes': priced_src,
            'by_sector': _pct_map(sector), 'by_country': _pct_map(country),
            'by_supplier_country': _pct_map(sup_ctry),
            'chain_worst_suppliers': [{'id': k, 'label': (v.by_id.get(k) or {}).get('label') or k,
                                       'portfolio_hit_pct': round(x * 100, 2)} for k, x in chain_top],
            'unmapped': unmapped,
            'method': 'AccountRisk math (sum_w_psi@1: Σ_i w_i·Ψ[c→i], Ψ = Impact view, propagate_many) by company id; '
                      'supplier countries: flow tensor shares × weights',
            'uncertainty': 'weights from the values you passed or live quotes; chain exposure is structural (Ψ), '
                           'not a price forecast',
            **_gen_meta(v), 'source': 'Khipus AccountRisk view + flow tensor', 'as_of': _now_iso()}


# ════════════════════════════════════════════════════════════════════════════
# find_similar_entities
# ════════════════════════════════════════════════════════════════════════════
@tool('find_similar_entities', 'Similar companies with a score per space', 'read',
      'Comparable companies of one company in the Khipus graph, with an explainable score PER SPACE: '
      '`chain` (cosine of shared suppliers/customers in the flow tensor), `features` (closeness of structural '
      'features) and `category` (same category). combined = 0.6·chain + 0.25·features + 0.15·category (the same '
      'blend the app uses for peers).',
      {'id': {'type': 'string', 'minLength': 1, 'maxLength': 120},
       'k': {'type': 'integer', 'minimum': 1, 'maximum': 25, 'default': 8},
       'space': {'type': 'string', 'enum': ['combined', 'chain', 'features', 'category'], 'default': 'combined'}},
      required=['id'])
def t_find_similar_entities(ctx, id, k=8, space='combined'):  # noqa: A002
    import numpy as np

    from matrix import tensor
    r = _resolve_or_fail(id)
    m = tensor.model()
    j = m.i_of(r['id'])
    if j is None:
        raise ToolError('this company has no position in the flow tensor (no supply-chain links)', code='no_data')
    chain = m.prof @ m.prof[j]
    feat = np.exp(-np.linalg.norm(m.X - m.X[j], axis=1) / 2.0)
    cat = (np.array(m.cat) == m.cat[j]).astype(float)
    comb = 0.6 * chain + 0.25 * feat + 0.15 * cat
    key = {'combined': comb, 'chain': chain, 'features': feat, 'category': cat}[space]
    order = [i for i in np.argsort(-key, kind='stable') if i != j][:int(k)]
    return {'id': m.ids[j], 'label': m.label(m.ids[j]), 'space': space,
            'results': [{'id': m.ids[i], 'label': m.label(m.ids[i]), 'score': round(float(key[i]), 4),
                         'by_space': {'chain': round(float(chain[i]), 4), 'features': round(float(feat[i]), 4),
                                      'category': int(cat[i])}} for i in order],
            'method': 'matrix/tensor peers: chain = cosine of flow profiles; features = exp(-‖Δx‖/2); '
                      'category = same category; combined = 0.6/0.25/0.15',
            'source': 'Khipus flow tensor', 'as_of': _now_iso()}


# ════════════════════════════════════════════════════════════════════════════
# historia de precios: get_history y calculate_correlation
# ════════════════════════════════════════════════════════════════════════════
RANGES = ['1mo', '3mo', '6mo', '1y', '2y', '5y']


def _symbol_of(text):
    """Ticker de una empresa del grafo (o el texto si ya es un ticker que no está en el grafo)."""
    from core.entities import resolve
    r = resolve(str(text)[:120])
    if r:
        from core.hotviews import hot
        n = hot.graph().by_id.get(r['id']) or {}
        if n.get('mkt'):
            return str(n['mkt']).upper(), r['id']
    t = str(text).strip().upper()
    if t and len(t) <= 15 and ' ' not in t:
        return t, (r['id'] if r else None)
    return None, (r['id'] if r else None)


def _series(sym, rng):
    from core import risk_report as rr
    prices, cur = _bounded(rr.fetch_history, 15, sym, rng)
    meta = rr.history_meta(sym, rng) or {}
    return prices or {}, cur, meta


def _downsample(prices, freq):
    if freq == 'daily':
        return sorted(prices.items())
    out = {}
    for d, p in sorted(prices.items()):
        y, m, dd = (int(x) for x in d.split('-'))
        key = (y, m) if freq == 'monthly' else date(y, m, dd).isocalendar()[:2]
        out[key] = (d, p)                     # el ÚLTIMO cierre de la semana / del mes
    return sorted(out.values())


@tool('get_history', 'Price history with source and as_of', 'read',
      'Adjusted closing prices of one company (or ticker): Khipus\' own end-of-day history first (prices_eod), '
      'Yahoo adjusted closes otherwise. Each series says its source, as_of, currency and whether it is adjusted. '
      'frequency daily|weekly|monthly (last close of each period). For graph events use get_ontology_object.',
      {'id_or_ticker': {'type': 'string', 'minLength': 1, 'maxLength': 120},
       'range': {'type': 'string', 'enum': RANGES, 'default': '1y'},
       'frequency': {'type': 'string', 'enum': ['daily', 'weekly', 'monthly'], 'default': 'weekly'},
       'max_points': {'type': 'integer', 'minimum': 10, 'maximum': 1500, 'default': 300}},
      required=['id_or_ticker'], open_world=True)
def t_get_history(ctx, id_or_ticker, range='1y', frequency='weekly', max_points=300):  # noqa: A002
    sym, eid = _symbol_of(id_or_ticker)
    if not sym:
        raise ToolError('no listed ticker for this entity (private companies have no price history)', code='no_data')
    prices, cur, meta = _series(sym, range)
    if not prices:
        raise ToolError(f'no price history available for {sym} right now', code='unavailable')
    pts = _downsample(prices, frequency)
    dropped = max(0, len(pts) - int(max_points))
    pts = pts[dropped:]
    first, last = pts[0][1], pts[-1][1]
    return {'symbol': sym, 'id': eid, 'range': range, 'frequency': frequency, 'currency': cur,
            'adjusted': meta.get('adjusted', True), 'points': [{'date': d, 'close': round(p, 4)} for d, p in pts],
            'n': len(pts), 'dropped_oldest': dropped,
            'change_pct': round((last / first - 1) * 100, 2) if first else None,
            'source': meta.get('source') or 'yahoo_live', 'as_of': meta.get('as_of') or (pts[-1][0] if pts else None),
            'known_at': _now_iso(), 'method': 'adjusted close (splits/dividends); last close of each period'}


def _ranks(x):
    order = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2.0 + 1
        i = j + 1
    return r


def correlation(a, b, method='pearson'):
    """(r, n) de dos listas alineadas; Spearman = Pearson de los rangos."""
    n = len(a)
    if n < 3:
        return None, n
    if method == 'spearman':
        a, b = _ranks(a), _ranks(b)
    ma, mb = sum(a) / n, sum(b) / n
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((x - mb) ** 2 for x in b))
    if sa == 0 or sb == 0:
        return None, n
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb), n


def corr_matrix(series, method='pearson', min_obs=20):
    """series {símbolo: {fecha: precio}} → (símbolos, matriz r, matriz n, matriz error estándar) con retornos
    diarios simples sobre las fechas COMUNES de cada par (feriados distintos no rompen el par)."""
    syms = list(series)
    rets = {}
    for s in syms:
        ds = sorted(series[s])
        rets[s] = {ds[i]: series[s][ds[i]] / series[s][ds[i - 1]] - 1.0 for i in range(1, len(ds))
                   if series[s][ds[i - 1]]}
    R, N, SE = [], [], []
    for s in syms:
        rr, nn, ee = [], [], []
        for t in syms:
            if s == t:
                rr.append(1.0)
                nn.append(len(rets[s]))
                ee.append(0.0)
                continue
            common = sorted(set(rets[s]) & set(rets[t]))
            r, n = correlation([rets[s][d] for d in common], [rets[t][d] for d in common], method)
            ok = r is not None and n >= min_obs
            rr.append(round(r, 4) if ok else None)
            nn.append(n)
            ee.append(round(math.sqrt(max(0.0, 1 - r * r) / (n - 2)), 4) if ok and n > 2 else None)
        R.append(rr)
        N.append(nn)
        SE.append(ee)
    return syms, R, N, SE


@tool('calculate_correlation', 'Correlation of daily returns', 'read',
      'Correlation matrix of DAILY returns between 2-15 companies/tickers over a window (Pearson or Spearman), '
      'with the number of common days and the standard error of each coefficient (√((1−r²)/(n−2))). Prices: '
      'Khipus\' own adjusted history first, Yahoo adjusted otherwise; each series reports its source and as_of.',
      {'symbols': {'type': 'array', 'minItems': 2, 'maxItems': 15,
                   'items': {'type': 'string', 'minLength': 1, 'maxLength': 120}},
       'window': {'type': 'string', 'enum': ['3mo', '6mo', '1y', '2y'], 'default': '1y'},
       'method': {'type': 'string', 'enum': ['pearson', 'spearman'], 'default': 'pearson'}},
      required=['symbols'], open_world=True)
def t_calculate_correlation(ctx, symbols, window='1y', method='pearson'):
    series, meta, missing = {}, {}, []
    for raw in symbols:
        sym, _eid = _symbol_of(raw)
        if not sym or sym in series:
            if not sym:
                missing.append(str(raw)[:40])
            continue
        try:
            prices, cur, m = _series(sym, window)
        except ToolError:
            prices, cur, m = {}, None, {}
        if len(prices) < 25:
            missing.append(sym)
            continue
        series[sym] = prices
        meta[sym] = {'source': m.get('source') or 'yahoo_live', 'as_of': m.get('as_of') or max(prices),
                     'currency': cur, 'n_prices': len(prices)}
    if len(series) < 2:
        raise ToolError('need price history for at least 2 symbols', code='no_data', data={'missing': missing})
    syms, R, N, SE = corr_matrix(series, method)
    pairs = []
    for i in range(len(syms)):
        for j in range(i + 1, len(syms)):
            if R[i][j] is not None:
                pairs.append({'a': syms[i], 'b': syms[j], 'r': R[i][j], 'n': N[i][j], 'se': SE[i][j]})
    pairs.sort(key=lambda p: -abs(p['r']))
    return {'symbols': syms, 'window': window, 'method': method, 'returns': 'daily simple returns, common dates',
            'matrix': R, 'n_obs': N, 'std_error': SE, 'strongest_pairs': pairs[:10], 'series': meta,
            'missing': missing, 'uncertainty': 'sample correlation over the window; regimes change — check se and n',
            'source': 'Khipus prices_eod / Yahoo adjusted closes', 'as_of': _now_iso(),
            'known_at': datetime.now(timezone.utc).isoformat(timespec='seconds')}
