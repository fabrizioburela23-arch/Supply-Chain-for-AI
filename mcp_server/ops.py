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
  find_anomalies         días inusuales: z del retorno (y del log del volumen guardado) contra la volatilidad EWMA
                         EX-ANTE (RiskMetrics, λ de policy.risk) — batch I2.
  project_portfolio      rango de valores de una cartera a N días (bandas de percentiles, lognormal, deriva 0) con su
                         covarianza EWMA o Ledoit-Wolf — rotulado "no es un pronóstico" — batch I2.

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
           # «ganadores» = rivales del mismo rubro POCO golpeados, con su % de DAÑO (nunca un % de ganancia): la
           # regla de KhipuHot.rivals sobre TODOS los impactos del kernel (core/genui/rivals.py, paridad con el JS)
           'least_hit_rivals': _least_hit_rivals(v, [u['id'] for u in used], impacts),
           'least_hit_rivals_rule': RIVALS_RULE,
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
        # batch I3 (L2-13): la traducción CALIBRADA (κ de kernel.calibration, con banda) — o, si el ajuste es débil,
        # falta o es de otro motor, `status` lo dice y no hay cifra
        from core import scenario_pnl
        cal = scenario_pnl.translate(impacts, [{'id': r['id'], 'symbol': r['symbol'], 'usd': r['usd']} for r in rows])
        out['portfolio']['calibrated'] = {k: cal.get(k) for k in (
            'status', 'pnl_usd', 'band_usd', 'lo_usd', 'hi_usd', 'pnl_pct', 'extrapolated', 'note_en', 'calibration')
            if k in cal}
    return out


RIVALS_RULE = ('least-hit rivals: same category as companies hit >= 40%, own damage < 15% (they could capture the '
               'orphaned demand); impact_pct is their DAMAGE, never a gain')


def _least_hit_rivals(v, seed_ids, impacts):
    """[{id, label, impact_pct, cat_damaged}] ≤ 4 — nunca rompe el choque (sin datos → [])."""
    try:
        from core.genui.rivals import rivals
        nodes = [{'id': nid, 'cat': n.get('cat')} for nid, n in (v.by_id or {}).items()
                 if isinstance(n, dict) and n.get('id', nid) == nid]
        caps = {}
        try:
            from core.live_caps import get_caps
            for nid, c in ((get_caps() or {}).get('caps') or {}).items():
                if isinstance(c, dict) and isinstance(c.get('mcap_b'), (int, float)):
                    caps[nid] = c['mcap_b']
        except Exception:  # noqa: BLE001
            caps = {}
        return [{'id': r['id'], 'label': v.core.label(r['id']) if v.core is not None else r['id'],
                 'impact_pct': r['hit'], 'cat_damaged': r['cat_damaged']}
                for r in rivals(seed_ids, impacts, nodes, caps, 4)]
    except Exception:  # noqa: BLE001
        return []


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
    # mismo orden que tensor.peers: mayor a menor, comparando a 12 decimales (el producto disperso del perfil difiere
    # del denso en la última cifra binaria) y, en empate, por id
    key2 = np.array(key, dtype=float)
    key2[j] = -np.inf
    order = [int(i) for i in tensor._order(np.round(key2, 12), int(k) + 1) if i != j][:int(k)]
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


# ════════════════════════════════════════════════════════════════════════════
# find_anomalies y project_portfolio (BRECHAS L4-09: las 2 operaciones que faltaban; batch I2)
# ════════════════════════════════════════════════════════════════════════════
def _risk_pol():
    from core.risk_report import risk_policy
    return risk_policy()


def ewma_zscores(x, lam=0.94, seed_n=25, demean=False):
    """[(i, z_i)] de cada observación contra la desviación EWMA EX-ANTE (estimada solo con lo anterior; RiskMetrics).
    demean=True: también una media EWMA ex-ante (para el log del volumen); False: media cero (retornos)."""
    n = len(x)
    if n <= seed_n + 1:
        return []
    head = x[:seed_n]
    m = sum(head) / seed_n if demean else 0.0
    v = sum((h - m) ** 2 for h in head) / seed_n
    out = []
    for i in range(seed_n, n):
        if v > 0:
            out.append((i, (x[i] - m) / math.sqrt(v)))
        dev = x[i] - m
        if demean:
            m = lam * m + (1 - lam) * x[i]
        v = lam * v + (1 - lam) * dev * dev
    return out


@tool('find_anomalies', 'Unusual moves (returns and volume)', 'read',
      'Flags unusual DAILY moves of 1-30 companies/tickers: each return (and, when Khipus has stored volume, each '
      'day\'s log-volume) is compared with its EWMA volatility estimated ONLY from the days before (RiskMetrics, '
      'λ from the governance artifact policy.risk) → z-score. Returns the days with |z| ≥ threshold inside the '
      'lookback window, ranked by |z|. Prices: Khipus\' own adjusted history first, Yahoo adjusted otherwise. '
      'A statistical flag, not a cause: check news/events.',
      {'symbols': {'type': 'array', 'minItems': 1, 'maxItems': 30,
                   'items': {'type': 'string', 'minLength': 1, 'maxLength': 120}},
       'window': {'type': 'string', 'enum': ['6mo', '1y', '2y'], 'default': '1y'},
       'lookback_days': {'type': 'integer', 'minimum': 1, 'maximum': 120,
                         'description': 'How many of the most recent sessions to scan (default from policy.risk).'},
       'z_threshold': {'type': 'number', 'minimum': 1.5, 'maximum': 10,
                       'description': '|z| at or above which a day is flagged (default from policy.risk).'}},
      required=['symbols'], open_world=True)
def t_find_anomalies(ctx, symbols, window='1y', lookback_days=None, z_threshold=None):
    pol = _risk_pol()
    lam = float(pol.get('ewma_lambda') or 0.94)
    seed_n = int(pol.get('ewma_seed_days') or 25)
    thr = float(z_threshold if z_threshold is not None else (pol.get('anomaly_z') or 3.0))
    look = int(lookback_days if lookback_days is not None else (pol.get('anomaly_lookback_days') or 20))
    items, missing, seen = [], [], set()
    for raw in symbols:
        sym, eid = _symbol_of(raw)
        if not sym or sym in seen:
            if not sym:
                missing.append(str(raw)[:40])
            continue
        seen.add(sym)
        try:
            prices, cur, m = _series(sym, window)
        except ToolError:
            prices, cur, m = {}, None, {}
        ds = sorted(prices)
        if len(ds) < seed_n + 10:
            missing.append(sym)
            continue
        rdates = ds[1:]
        rets = [prices[ds[i]] / prices[ds[i - 1]] - 1.0 for i in range(1, len(ds))]
        zr = {rdates[i]: z for i, z in ewma_zscores(rets, lam, seed_n)}
        vol_meta, zv, vols = None, {}, {}
        try:
            from core import prices_store
            vh = prices_store.volume_history(sym, window)
        except Exception:  # noqa: BLE001
            vh = None
        if vh:
            vols, vol_meta = vh
            vd = sorted(d for d, v in vols.items() if v > 0)
            lv = [math.log(vols[d]) for d in vd]
            zv = {vd[i]: z for i, z in ewma_zscores(lv, lam, seed_n, demean=True)}
        recent = rdates[-look:]
        flags = []
        for d in recent:
            z1, z2 = zr.get(d), zv.get(d)
            hit_r = z1 is not None and abs(z1) >= thr
            hit_v = z2 is not None and z2 >= thr                  # volumen: solo lo INUSUALMENTE alto
            if hit_r or hit_v:
                i = rdates.index(d)
                flags.append({'date': d, 'return_pct': round(rets[i] * 100, 2),
                              'z_return': round(z1, 2) if z1 is not None else None,
                              'volume': vols.get(d), 'z_volume': round(z2, 2) if z2 is not None else None,
                              'kind': ('return+volume' if hit_r and hit_v else 'return' if hit_r else 'volume')})
        flags.sort(key=lambda f: -max(abs(f['z_return'] or 0), abs(f['z_volume'] or 0)))
        last = rdates[-1]
        items.append({'symbol': sym, 'id': eid, 'currency': cur, 'anomalies': flags,
                      'n_flagged': len(flags), 'max_abs_z': (max(max(abs(f['z_return'] or 0), abs(f['z_volume'] or 0))
                                                                 for f in flags) if flags else 0.0),
                      'latest': {'date': last, 'return_pct': round(rets[-1] * 100, 2),
                                 'z_return': round(zr[last], 2) if last in zr else None,
                                 'z_volume': round(zv[last], 2) if last in zv else None},
                      'volume': ({'available': True, 'source': vol_meta.get('source'), 'as_of': vol_meta.get('as_of')}
                                 if vol_meta else {'available': False,
                                                   'reason': 'no stored daily volume for this range (prices_eod)'}),
                      'source': m.get('source') or 'yahoo_live', 'as_of': m.get('as_of') or last,
                      'n_returns': len(rets)})
    if not items:
        raise ToolError('no price history for any of the symbols', code='no_data', data={'missing': missing})
    items.sort(key=lambda x: -x['max_abs_z'])
    return {'items': items, 'missing': missing, 'window': window, 'lookback_days': look, 'z_threshold': thr,
            'ewma_lambda': lam, 'policy': {'artifact': 'policy.risk', 'semver': pol.get('semver')},
            'method': ('z = return / ex-ante EWMA volatility (zero mean, RiskMetrics); volume: z of log-volume vs '
                       'ex-ante EWMA mean/variance (only unusually HIGH volume is flagged)'),
            'uncertainty': ('statistical flag only — returns have fat tails, so |z| ≥ 3 happens more often than a '
                            'normal curve says; it does not explain WHY (check news and graph events)'),
            'source': 'Khipus prices_eod / Yahoo adjusted closes', 'as_of': _now_iso()}


def _usd_series(sym, rng):
    """({fecha: precio EN USD}, moneda, meta, fx_method) — FX diario alineado si existe, si no la tasa de hoy."""
    from core import risk_report as rr
    prices, cur, meta = _series(sym, rng)
    if not prices:
        return {}, cur, meta, None
    c = str(cur or 'USD')
    if c.upper() == 'USD':
        return prices, cur, meta, 'usd'
    try:
        fxs = rr.fx_series(c, rng)
    except Exception:  # noqa: BLE001
        fxs = None
    if fxs:
        al = rr.align_fx(prices, fxs[0])
        if len(al) >= 60:
            return {d: prices[d] * al[d] for d in al}, cur, meta, 'daily'
    from core.instruments import major_ccy
    from core.quotes import _fx_to_usd
    maj, mult = major_ccy(c)
    rate = _fx_to_usd(maj)
    if not rate:
        return {}, cur, meta, None
    return {d: p * rate * mult for d, p in prices.items()}, cur, meta, 'spot'


@tool('project_portfolio', 'Portfolio value range over a horizon (not a forecast)', 'read',
      'Projects the RANGE of values a portfolio [{symbol, usd} or {symbol, shares}] could have after N trading days, '
      'from its own daily-return covariance (EWMA — RiskMetrics λ — or Ledoit-Wolf shrunk) on 1 year of adjusted '
      'prices in USD: percentile bands (5/25/50/75/95) under a lognormal model with ZERO drift by default. It is a '
      'risk range, NOT a forecast: past volatility, normal tails, no jumps.',
      {'positions': {'type': 'array', 'minItems': 1, 'maxItems': 30, 'items': {'type': 'object', 'properties': {
           'symbol': {'type': 'string', 'minLength': 1, 'maxLength': 40},
           'usd': {'type': 'number', 'minimum': 0}, 'shares': {'type': 'number', 'minimum': 0}},
           'required': ['symbol']}},
       'horizon_days': {'type': 'integer', 'minimum': 1, 'maximum': 504, 'default': 21},
       'covariance': {'type': 'string', 'enum': ['ewma', 'ledoit_wolf'], 'default': 'ewma'},
       'drift': {'type': 'string', 'enum': ['zero', 'historical'], 'default': 'zero',
                 'description': 'zero (honest default) or the historical mean daily return (backward-looking).'}},
      required=['positions'], open_world=True)
def t_project_portfolio(ctx, positions, horizon_days=21, covariance='ewma', drift='zero'):
    from statistics import NormalDist

    import numpy as np

    from core import risk_models as rm
    pol = _risk_pol()
    h = max(1, min(int(horizon_days), int(pol.get('projection_max_days') or 504)))
    pcts = [p for p in (pol.get('projection_percentiles') or [5, 25, 50, 75, 95]) if 0 < p < 100]
    want, missing = {}, []
    for p in positions[:30]:
        sym, _eid = _symbol_of(p.get('symbol'))
        if not sym:
            missing.append({'symbol': str(p.get('symbol'))[:40], 'reason': 'no listed ticker'})
            continue
        w = want.setdefault(sym, {'usd': 0.0, 'shares': 0.0})
        w['usd'] += float(p.get('usd') or 0)
        w['shares'] += float(p.get('shares') or 0)
    series, meta = {}, {}
    for sym in want:
        try:
            s, cur, m, how = _usd_series(sym, '1y')
        except ToolError:
            s, cur, m, how = {}, None, {}, None
        if len(s) < 61:
            missing.append({'symbol': sym, 'reason': 'not enough price history (≥ 60 days)'})
            continue
        series[sym] = s
        meta[sym] = {'currency': cur, 'fx': how, 'source': m.get('source') or 'yahoo_live',
                     'as_of': m.get('as_of') or max(s)}
    if not series:
        raise ToolError('no price history for any position', code='no_data', data={'missing': missing})
    syms = list(series)
    common = sorted(set.intersection(*(set(series[s]) for s in syms)))
    if len(common) < 61:
        raise ToolError(f'only {len(common)} common days between the positions (≥ 61 needed)', code='no_data',
                        data={'missing': missing})
    last = common[-1]
    vals = {s: want[s]['usd'] + want[s]['shares'] * series[s][last] for s in syms}
    total = sum(vals.values())
    if total <= 0:
        raise InvalidParams('positions need usd or shares > 0')
    wv = np.array([vals[s] / total for s in syms])
    R = np.array([[math.log(series[s][common[i]] / series[s][common[i - 1]]) for s in syms]
                  for i in range(1, len(common))])
    if covariance == 'ledoit_wolf':
        C, delta, _mu = rm.ledoit_wolf(R)
        cov_meta = {'estimator': 'ledoit_wolf', 'shrinkage': round(float(delta), 4)}
    else:
        lam = float(pol.get('ewma_lambda') or 0.94)
        C = rm.ewma_cov(R - R.mean(axis=0), lam, int(pol.get('ewma_seed_days') or 25))
        cov_meta = {'estimator': 'ewma', 'lambda': lam}
    var_d = float(wv @ C @ wv)
    sig = math.sqrt(max(0.0, var_d))
    mu = float(wv @ R.mean(axis=0)) if drift == 'historical' else 0.0
    # revisión lote I: R son retornos LOG → su media YA es la deriva log (= aritmética − σ²/2); restar σ²/2 otra vez
    # sesgaba toda la banda 'historical' hacia abajo (σ²·d/2: 11 % a un año con σ diaria de 3 %). Sin deriva (0),
    # −σ²/2 es lo que hace a V una martingala (mediana = V·e^(−σ²d/2)).
    m_log = mu if drift == 'historical' else -0.5 * var_d
    nd = NormalDist()
    days = sorted({d for d in (1, 5, 10, 21, 63, 126, 252, 504) if d < h} | {h})
    bands = []
    for d in days:
        row = {'day': d}
        for p in pcts:
            z = nd.inv_cdf(p / 100.0)
            row[f'p{p}_usd'] = round(total * math.exp(m_log * d + z * sig * math.sqrt(d)), 2)
        bands.append(row)
    end = bands[-1]
    return {'value_usd': round(total, 2), 'as_of_prices': last, 'horizon_days': h, 'covariance': cov_meta,
            'drift': drift, 'drift_daily_pct': round(mu * 100, 4),
            'vol_daily_pct': round(sig * 100, 3), 'vol_ann_pct': round(sig * math.sqrt(252) * 100, 2),
            'bands': bands,
            'at_horizon': {k: v for k, v in end.items() if k != 'day'},
            'weights': [{'symbol': s, 'usd': round(vals[s], 2), 'weight_pct': round(float(wv[i]) * 100, 2)}
                        for i, s in enumerate(syms)],
            'common_days': len(common) - 1, 'series': meta, 'missing': missing,
            'policy': {'artifact': 'policy.risk', 'semver': pol.get('semver')},
            'label': 'NOT A FORECAST — a range from past volatility',
            'method': ('lognormal: V·exp(m·d + z·σ·√d) with σ² = wᵀΣw of daily LOG returns in USD over the '
                       'common dates; m = −σ²/2 (zero drift, a martingale) or, with drift=historical, the mean daily '
                       'LOG return (which already includes −σ²/2)'),
            'uncertainty': ('assumes normal log-returns and a constant covariance: real crashes (fat tails, jumps, '
                            'correlations going to 1) are worse than the 5th percentile more often than 5%'),
            'source': 'Khipus prices_eod / Yahoo adjusted closes (+ daily FX when not USD)', 'as_of': _now_iso()}


# ════════════════════════════════════════════════════════════════════════════
# get_fundamentals — estados financieros por período (lote K: «no tengo la serie histórica de ganancias»)
# ════════════════════════════════════════════════════════════════════════════
FUND_MAX_PERIODS = 5
FUND_FIELDS = ('revenue', 'gross_profit', 'operating_income', 'net_income', 'fcf')
# Yahoo fundamentals-timeseries, serie TRIMESTRAL (misma fuente que la anual de core/company_data; sin FMP/AV)
_Q_TYPES = {'quarterlyTotalRevenue': 'revenue', 'quarterlyGrossProfit': 'gross_profit',
            'quarterlyOperatingIncome': 'operating_income', 'quarterlyNetIncome': 'net_income',
            'quarterlyFreeCashFlow': 'fcf', 'quarterlyOperatingCashFlow': 'ocf', 'quarterlyCapitalExpenditure': 'capex'}
_Q_CACHE = {}                       # símbolo → (ts, resultado); TTL 1 h ok / 10 min fallo
_Q_TTL_OK, _Q_TTL_FAIL, _Q_MAX = 3600, 600, 300
_UNAVAILABLE = 'unavailable'


def _pct(num, den):
    """Margen en % (1 decimal) con denominador POSITIVO; si no, None (nunca un margen sobre ingresos negativos)."""
    if num is None or den is None or not den > 0:
        return None
    return round(100.0 * num / den, 1)


def _growth(cur, prev):
    """Crecimiento en % contra el período anterior; con base ≤ 0 no tiene sentido (None)."""
    if cur is None or prev is None or not prev > 0:
        return None
    return round((cur / prev - 1.0) * 100.0, 1)


def _fund_row(label, period_end, vals):
    row = {'period': label, 'period_end': period_end}
    for k in FUND_FIELDS:
        v = vals.get(k)
        row[k] = (round(float(v), 2) if isinstance(v, (int, float)) and not isinstance(v, bool) else None)
    row['gross_margin_pct'] = _pct(row['gross_profit'], row['revenue'])
    row['operating_margin_pct'] = _pct(row['operating_income'], row['revenue'])
    row['net_margin_pct'] = _pct(row['net_income'], row['revenue'])
    return row


def _annual_rows(fin, years):
    ys = list(fin.get('years') or [])
    rows = []
    for i, y in enumerate(ys):
        vals = {k: (fin.get(k) or [None] * len(ys))[i] for k in FUND_FIELDS}
        rows.append((y, _fund_row(f'FY{y}', str(y), vals)))      # cierre fiscal exacto: no lo da la serie anual
    from core.company_data import _consecutive
    for i, (y, r) in enumerate(rows):
        prev = rows[i - 1] if i > 0 and _consecutive(rows[i - 1][0], y) else None
        r['revenue_growth_pct'] = _growth(r['revenue'], prev[1]['revenue']) if prev else None
        r['net_income_growth_pct'] = _growth(r['net_income'], prev[1]['net_income']) if prev else None
    return [r for _y, r in rows][-years:]


def _quarterly_yahoo(sym):
    """Trimestres (≤ 8) de Yahoo fundamentals-timeseries en USD: {'available', 'rows', 'currency', 'fx_rate',
    'reason_en'}. Caché propia (1 h); la fuente puede no cubrir una bolsa: entonces se dice."""
    import time as _t
    hit = _Q_CACHE.get(sym)
    if hit and _t.time() - hit[0] < (_Q_TTL_OK if hit[1].get('available') else _Q_TTL_FAIL):
        return hit[1]
    from core import company_data as cd
    out = {'available': False, 'rows': [], 'currency': None, 'fx_rate': None, 'reason_en': None}
    try:
        payload, err = cd._yahoo_get(cd._Y_TS_URL.format(sym=cd._sym(sym)),
                                     {'symbol': sym, 'type': ','.join(_Q_TYPES), 'period1': cd._PERIOD1,
                                      'period2': int(_t.time())})
    except Exception as e:  # noqa: BLE001
        payload, err = None, type(e).__name__
    if payload is None:
        out['reason_en'] = f'Yahoo Finance: {err or "no data"}'
    else:
        by_date, curs = {}, {}
        for item in (((payload or {}).get('timeseries') or {}).get('result') or []):
            if not isinstance(item, dict):
                continue
            typ = ((item.get('meta') or {}).get('type') or [None])[0]
            field = _Q_TYPES.get(typ)
            if not field:
                continue
            for e in item.get(typ) or []:
                if not isinstance(e, dict):
                    continue
                d, v = str(e.get('asOfDate') or '')[:10], cd._num(e.get('reportedValue'))
                if len(d) != 10 or v is None:
                    continue
                by_date.setdefault(d, {})[field] = v
                c = e.get('currencyCode')
                if c:
                    curs[c] = curs.get(c, 0) + 1
        cur = max(curs, key=curs.get) if curs else 'USD'
        conv = cd._Converter(None, cur)
        rate = conv.rate(cur)
        if not by_date:
            out['reason_en'] = 'Yahoo Finance: no quarterly statements for this symbol'
        elif rate is None:
            out['reason_en'] = f'no {cur}→USD exchange rate'
        else:
            rows = []
            for d in sorted(by_date):
                r = by_date[d]
                if r.get('fcf') is None and r.get('ocf') is not None and r.get('capex') is not None:
                    r['fcf'] = r['ocf'] - abs(r['capex'])
                if all(r.get(k) is None for k in ('revenue', 'net_income')):
                    continue
                rows.append(_fund_row(f'Q {d}', d, {k: conv(r.get(k), cur) for k in FUND_FIELDS}))
            for i, r in enumerate(rows):
                p1 = rows[i - 1] if i >= 1 else None
                p4 = rows[i - 4] if i >= 4 else None
                r['revenue_growth_pct'] = _growth(r['revenue'], p1['revenue']) if p1 else None
                r['net_income_growth_pct'] = _growth(r['net_income'], p1['net_income']) if p1 else None
                r['revenue_growth_yoy_pct'] = _growth(r['revenue'], p4['revenue']) if p4 else None
            out.update(available=bool(rows), rows=rows[-8:], currency=cur, fx_rate=rate,
                       reason_en=None if rows else 'Yahoo Finance: no quarterly statements for this symbol')
    if len(_Q_CACHE) >= _Q_MAX:
        _Q_CACHE.clear()
    _Q_CACHE[sym] = (_t.time(), out)
    return out


def _annual_financials(sym):
    """Estados anuales normalizados en USD (core/company_data: FMP → Yahoo → Alpha Vantage, caché)."""
    from core import company_data as cd
    return _bounded(cd.get_annual_financials, 15, sym)


FUND_SRC_LABEL = {'fmp': 'FMP', 'yahoo': 'Yahoo Finance', 'alphavantage': 'Alpha Vantage'}


@tool('get_fundamentals', 'Financial statements by period (revenue, profit, margins)', 'read',
      'Reported financial statements of ONE listed company by period: revenue, gross profit, operating income, net '
      'income and free cash flow in USD, the margins (gross / operating / net, % of revenue) and the growth vs the '
      'previous period (%). period=annual (FMP → Yahoo → Alpha Vantage, cached) or quarterly (Yahoo). Each figure '
      'is as REPORTED by the source (never estimated); a missing figure is null. Use it for "earnings / revenue / '
      'profit / margins of X", also "in a chart". Private companies have no statements.',
      {'id_or_ticker': {'type': 'string', 'minLength': 1, 'maxLength': 120},
       'period': {'type': 'string', 'enum': ['annual', 'quarterly'], 'default': 'annual'},
       'years': {'type': 'integer', 'minimum': 1, 'maximum': FUND_MAX_PERIODS, 'default': FUND_MAX_PERIODS,
                 'description': 'How many fiscal years (annual) — quarterly always returns up to 8 quarters.'}},
      required=['id_or_ticker'], open_world=True)
def t_get_fundamentals(ctx, id_or_ticker, period='annual', years=FUND_MAX_PERIODS):
    sym, eid = _symbol_of(id_or_ticker)
    label = None
    if eid:
        try:
            from core.hotviews import hot
            n = hot.graph().by_id.get(eid) or {}
            label = n.get('label')
            if not n.get('mkt'):
                sym = None                   # empresa del grafo SIN ticker (privada): no hay estados que pedir
        except Exception:  # noqa: BLE001
            label = None
    if not sym:
        raise ToolError('no listed ticker for this entity (private companies publish no financial statements)',
                        code='no_data')
    years = max(1, min(FUND_MAX_PERIODS, int(years or FUND_MAX_PERIODS)))
    base = {'symbol': sym, 'id': eid, 'label': label or eid or sym, 'period': period, 'unit': 'USD',
            'fields': list(FUND_FIELDS), 'known_at': _now_iso()}
    if period == 'quarterly':
        q = _quarterly_yahoo(sym)
        if not q.get('available'):
            raise ToolError(f'quarterly statements {_UNAVAILABLE} for {sym}: {q.get("reason_en") or "no data"}',
                            code=_UNAVAILABLE)
        rows = q['rows']
        src = 'yahoo'
        base.update(reported_currency=q.get('currency'), fx_rate=q.get('fx_rate'))
    else:
        fin = _annual_financials(sym) or {}
        if not fin.get('available'):
            raise ToolError(f'annual statements {_UNAVAILABLE} for {sym}: {fin.get("reason_en") or "no data"}',
                            code=_UNAVAILABLE, data={'tried': fin.get('tried')})
        rows = _annual_rows(fin, years)
        src = str(fin.get('source') or 'yahoo')
        base.update(reported_currency=fin.get('currency'), fx_rate=fin.get('fx_rate'), tried=fin.get('tried'))
    if not rows:
        raise ToolError(f'statements {_UNAVAILABLE} for {sym}: the source returned no usable period',
                        code=_UNAVAILABLE)
    last = rows[-1]
    base.update({
        'periods': rows, 'n': len(rows), 'latest': dict(last),
        'source': src, 'source_label': FUND_SRC_LABEL.get(src, src), 'as_of': _now_iso(),
        'method': ('figures as reported by the source and converted to USD at today\'s rate when the report is in '
                   'another currency; margins = item / revenue × 100 (only with revenue > 0); growth = vs the previous '
                   'period in this list (annual only between consecutive fiscal years; quarterly also YoY vs 4 quarters '
                   'back)'),
        'uncertainty': 'as_of is when Khipus read the statements; each period is the fiscal period as reported',
    })
    return base


# ════════════════════════════════════════════════════════════════════════════
# rank_by_market — posición de mercado (E2.9): «¿cuál es la empresa de baterías más grande?»
# ════════════════════════════════════════════════════════════════════════════
MKT_GLOBAL = ('', 'global', 'world', 'worldwide', 'mundial', 'mundo', 'internacional', 'international')
# raíces es ↔ en de mercados frecuentes: una pregunta en un idioma encuentra fichas escritas en el otro
MKT_SYNONYMS = {
    'bater': ('batter', 'bater', 'cell'), 'batter': ('batter', 'bater', 'cell'),
    'memor': ('memor', 'dram', 'hbm', 'nand'), 'fundic': ('foundr', 'fundic'), 'foundr': ('foundr', 'fundic'),
    'litogr': ('lithogr', 'litogr'), 'lithogr': ('lithogr', 'litogr'), 'nube': ('cloud', 'nube'),
    'cloud': ('cloud', 'nube'), 'chip': ('chip', 'semicond'), 'semicond': ('semicond', 'chip'),
    'graf': ('gpu', 'graf', 'graph'), 'gpu': ('gpu', 'graf', 'graph'), 'acelerad': ('accelerat', 'acelerad', 'gpu'),
    'accelerat': ('accelerat', 'acelerad', 'gpu'), 'servid': ('server', 'servid'), 'server': ('server', 'servid'),
    'equip': ('equip', 'tool'), 'robot': ('robot',), 'litio': ('lithium', 'litio'), 'lithium': ('lithium', 'litio'),
    'energ': ('energ', 'power'), 'solar': ('solar', 'fotovolt', 'photovolt'), 'elect': ('elect',),
    'vehic': ('vehic', 'ev', 'auto', 'car'), 'auto': ('auto', 'vehic', 'car'), 'red': ('network', 'red'),
    'ev': ('ev', 'vehic', 'electr'),
    'network': ('network', 'red'), 'almacen': ('storage', 'almacen'), 'storage': ('storage', 'almacen'),
    'sustrat': ('substrat', 'sustrat'), 'substrat': ('substrat', 'sustrat'), 'oblea': ('wafer', 'oblea'),
    'wafer': ('wafer', 'oblea'), 'satel': ('satell', 'satel'), 'satell': ('satell', 'satel'),
    'refriger': ('cool', 'refriger'), 'cool': ('cool', 'refriger'), 'centro': ('data', 'centro'), 'dato': ('data', 'dato'),
}
_MKT_STOP = {'de', 'del', 'la', 'el', 'los', 'las', 'en', 'para', 'por', 'y', 'the', 'of', 'in', 'for', 'and', 'a',
             'market', 'mercado', 'empresa', 'empresas', 'company', 'companies', 'sector', 'industria', 'industry',
             'mas', 'más', 'grande', 'grandes', 'largest', 'biggest', 'mayor', 'lider', 'líder', 'leader'}


def _mkt_tokens(text):
    import re
    import unicodedata
    s = unicodedata.normalize('NFKD', str(text or '').lower())
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    return [t for t in re.split(r'[^a-z0-9]+', s) if t and t not in _MKT_STOP]


def _stem(tok):
    """Raíz CORTA (≤ 6) que iguala singular/plural y es/en cercanos (baterías/batteries → 'bater'/'batter')."""
    t = tok
    for suf in ('ies', 'es', 's'):
        if t.endswith(suf) and len(t) - len(suf) >= 3:
            t = t[:-len(suf)]
            break
    return t[:6]


def mkt_match(query, market):
    """Puntaje 0-1: fracción de las raíces de la pregunta que aparecen (prefijo ≥ 3) en el texto del mercado,
    con sinónimos es/en. 1 token en común alcanza para preguntas de una palabra."""
    q = [_stem(t) for t in _mkt_tokens(query)]
    m = [_stem(t) for t in _mkt_tokens(market)]
    if not q or not m:
        return 0.0
    hit = 0
    for qs in q:
        alts = {qs}
        for k, syn in MKT_SYNONYMS.items():          # la raíz de la pregunta y la clave se contienen (bateri ~ bater)
            if qs.startswith(k) or k.startswith(qs):
                alts |= set(syn)
        if any(ms == a or (len(a) >= 3 and len(ms) >= 3 and (ms.startswith(a[:4]) or a.startswith(ms[:4])))
               for ms in m for a in alts):
            hit += 1
    return hit / len(q)


def _region_key(x):
    s = str(x or '').strip()
    if s.lower() in MKT_GLOBAL:
        return 'GLOBAL'
    if len(s) == 2 and s.isalpha():
        return s.upper()
    try:
        from core.countries import iso2_of
        iso = iso2_of(s)
        if iso:
            return iso.upper()
    except Exception:  # noqa: BLE001
        pass
    return s.upper()[:20]


_MP_KEYS = ('market', 'rank', 'share_pct', 'metric', 'region', 'period', 'measured_by', 'source_url', 'as_of',
            'confidence')


@tool('rank_by_market', 'Who is biggest in a market (researched market position)', 'read',
      'Ranks the companies of the Khipus graph by their RESEARCHED market position in one market (e.g. "EV '
      'batteries", "DRAM", "foundry", "cloud"): market share % or rank, with the period, who measured it, the source '
      'URL and the as_of of every entry. Use it for "which is the largest / leading company in X", "market share of '
      'X". It only knows what the research cards recorded: when nothing matches it says so instead of guessing.',
      {'market': {'type': 'string', 'minLength': 2, 'maxLength': 80},
       'metric': {'type': 'string', 'enum': ['share_pct', 'rank'], 'default': 'share_pct'},
       'region': {'type': 'string', 'minLength': 2, 'maxLength': 40, 'default': 'GLOBAL',
                  'description': 'GLOBAL or an ISO-2 country code (CN, US…).'},
       'limit': {'type': 'integer', 'minimum': 1, 'maximum': 20, 'default': 10}},
      required=['market'])
def t_rank_by_market(ctx, market, metric='share_pct', region='GLOBAL', limit=10):
    from core.hotviews.views import card as _card
    cv = _card.reader_view()
    if cv is None:
        raise ToolError('the graph is warming up — retry in a few seconds', code='unavailable')
    want_region = _region_key(region)
    rows, markets, any_entries = [], {}, 0
    for oid, c in cv.cards.items():
        for e in c.get('market_position') or []:
            any_entries += 1
            score = mkt_match(market, e.get('market'))
            if score < 0.5:
                continue
            if _region_key(e.get('region')) != want_region:
                continue
            markets[str(e.get('market'))] = markets.get(str(e.get('market')), 0) + 1
            rows.append((score, oid, c, e))
    if rows:
        # solo el MEJOR parecido: «EV batteries» no mezcla celdas de smartphone ni ánodos (que solo comparten «baterías»)
        best = max(r[0] for r in rows)
        rows = [r for r in rows if r[0] >= best - 1e-9]
        markets = {k: n for k, n in markets.items() if any(str(r[3].get('market')) == k for r in rows)}
    if not rows:
        raise ToolError(f'I do not have that ranking: no company in the Khipus graph records a market position for '
                        f'"{market}" ({want_region}); {any_entries} market-position entries exist for other markets',
                        code='no_data', data={'market': market, 'region': want_region, 'entries_total': any_entries})
    share_known = any(isinstance(e.get('share_pct'), (int, float)) for _s, _o, _c, e in rows)
    rank_known = any(isinstance(e.get('rank'), (int, float)) for _s, _o, _c, e in rows)
    by = metric if (metric == 'share_pct' and share_known) or (metric == 'rank' and rank_known) else (
        'share_pct' if share_known else 'rank')

    def key(t):
        s, oid, c, e = t
        if by == 'share_pct':
            v = e.get('share_pct')
            return (0 if isinstance(v, (int, float)) else 1, -(v if isinstance(v, (int, float)) else 0), -s, oid)
        v = e.get('rank')
        return (0 if isinstance(v, (int, float)) else 1, v if isinstance(v, (int, float)) else 10 ** 6, -s, oid)
    rows.sort(key=key)
    items = []
    for i, (s, oid, c, e) in enumerate(rows[:int(limit)], 1):
        it = {'position': i, 'id': oid, 'label': c.get('label') or oid, 'symbol': c.get('ticker'),
              'match_score': round(s, 2)}
        it.update({k: e.get(k) for k in _MP_KEYS})
        items.append(it)
    return {'market': market, 'region': want_region, 'metric': metric, 'sorted_by': by, 'items': items,
            'n_matched': len(rows), 'markets_matched': sorted(markets, key=lambda k: -markets[k])[:8],
            'source': 'Khipus graph — market_position facts researched per company (source_url and as_of per entry)',
            'method': ('text match of the market name against each company\'s market_position entries (es/en roots), '
                       'same region; sorted by share_pct (desc) or rank (asc); entries without the metric go last'),
            'uncertainty': 'only companies whose research card records a market position; measured_by/period differ '
                           'between entries — compare like with like',
            'generation': cv.generation, 'graph_version': cv.graph_version, 'graph_source': cv.source,
            'as_of': _now_iso()}
