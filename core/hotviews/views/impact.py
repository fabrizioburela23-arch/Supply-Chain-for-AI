"""V2 Impact (INFRA_OPERATIVA §4.2): el colapso unitario de CADA nodo, ya calculado, con los factores activos.

Usa `matrix.engine.propagate_many` — el MISMO kernel que `propagate`, en lote (tests/test_hot_views_parity.py
exige igualdad exacta en los 937 choques). Por fuente: víctimas {id, pct, hop} ordenadas, alcance ≥ 1 %
(= cascade_size de compute_metrics) y ≥ 10 %, Σ impacto (en "empresas equivalentes": Σ pct / 100, sin el
origen). Cuellos de botella por Σ (PROP-06: el conteo premia cascadas largas y débiles) y por conteo.
También arma el payload de /api/matrix/metrics con la MISMA forma y los mismos números que compute_metrics.
"""
import hashlib
import time

import numpy as np



def default_kernel():
    """Parámetros del kernel con que se construyó la vista (kernel.params del release vigente, paso 9)."""
    from matrix import engine as E
    return {'magnitude': E._P('magnitude'), 'damping': E._P('damping'), 'max_hops': E._P('max_hops'),
            'threshold': E._P('threshold'), 'damage_rels': E._P('damage_rels', None),
            'chokepoint_rank_by': E._P('chokepoint_rank_by', 'count'), 'semver': _kernel_semver()}


def _kernel_semver():
    try:
        from core import governance
        return governance.artifact_semver('kernel.params')
    except Exception:  # noqa: BLE001
        return None


class ImpactView:
    __slots__ = ('sources', 'victims', 'stats', 'by_sum', 'by_count', 'metrics', 'content_sha', 'nnz',
                 'timings', 'kernel')

    def lookup(self, oid):
        return self.victims.get(oid)


def build(core):
    from matrix import engine as E
    t0 = time.perf_counter()
    v = ImpactView()
    v.kernel = dict(default_kernel(), method='propagate@1')
    # mismas fuentes que compute_metrics: nodos con algún peso de entrada o salida
    v.sources = [oid for oid, i in core.idx.items() if not (core.out_w[i] == 0 and core.in_w[i] == 0)]
    res = E.propagate_many(core.mats, core.idx, core.ids, v.sources, frag=core.frag, dt=core.dt)
    t_kernel = (time.perf_counter() - t0) * 1000
    v.victims, v.stats = {}, {}
    h = hashlib.sha256()
    nnz = 0
    for oid in v.sources:
        impacts, hops = res[oid]
        order = sorted(impacts.items(), key=lambda kv: (-kv[1], hops.get(kv[0], 0), kv[0]))
        ids_ = tuple(k for k, _ in order)
        pct = tuple(p for _, p in order)
        hop = tuple(hops.get(k, 0) for k in ids_)
        v.victims[oid] = (ids_, pct, hop)
        nnz += len(ids_)
        others = [p for k, p in order if k != oid]
        v.stats[oid] = {'reach_1': max(0, sum(1 for p in impacts.values() if p >= 1.0) - 1),
                        'reach_10': sum(1 for p in others if p >= 10.0),
                        'affected': len(others),
                        'sum_impact': round(sum(others) / 100.0, 4),
                        'max_hop': max(hop) if hop else 0}
        h.update(repr((oid, ids_, pct, hop)).encode())
    v.nnz = nnz
    v.content_sha = h.hexdigest()
    v.by_sum = sorted(v.sources, key=lambda k: (-v.stats[k]['sum_impact'], -v.stats[k]['reach_1'], k))
    v.by_count = sorted(v.sources, key=lambda k: (-v.stats[k]['reach_1'], -v.stats[k]['sum_impact'], k))
    v.metrics = _metrics(core, v)
    v.timings = {'kernel_ms': round(t_kernel, 2), 'total_ms': round((time.perf_counter() - t0) * 1000, 2)}
    return v


def _metrics(core, v):
    """EXACTAMENTE matrix.engine.compute_metrics (mismo orden de inserción, mismos redondeos, mismos rangos)."""
    from matrix import engine as E
    metrics = {}
    for oid, i in core.idx.items():
        if core.out_w[i] == 0 and core.in_w[i] == 0:
            continue
        metrics[oid] = {
            'out_weight': round(float(core.out_w[i]), 2),
            'in_weight': round(float(core.in_w[i]), 2),
            'cascade_size': v.stats[oid]['reach_1'],
            'pagerank': round(float(core.pagerank[i]), 6),
        }
    sums = {oid: v.stats[oid]['sum_impact'] for oid in metrics}
    ranked = E.chokepoint_order(metrics, sums)          # 1.0.0: por conteo · 2.0.0: por Σ impacto (PROP-06)
    for rank, (oid, m) in enumerate(ranked, 1):
        m['chokepoint_rank'] = rank
    if E._P('chokepoint_rank_by', 'count') == 'sum':
        for oid, m in metrics.items():
            m['sum_impact'] = sums[oid]
    pr_ranked = sorted(metrics.items(), key=lambda kv: -kv[1]['pagerank'])
    for rank, (oid, m) in enumerate(pr_ranked, 1):
        m['pagerank_rank'] = rank
    return metrics


def metrics_payload(core, v):
    """El cuerpo de GET /api/matrix/metrics (sin as_of), idéntico al que armaba la ruta con compute_metrics."""
    metrics = v.metrics
    top = sorted(metrics.items(), key=lambda kv: kv[1]['chokepoint_rank'])[:25]
    pr_top = sorted(metrics.items(), key=lambda kv: kv[1].get('pagerank_rank', 1e9))[:25]
    return {'nodes': len(metrics),
            'factors_active': [f['label'] for f in core.factors],
            'chokepoints_top25': [{'id': k, **m} for k, m in top],
            'central_pagerank_top25': [{'id': k, 'pagerank': m.get('pagerank'),
                                        'pagerank_rank': m.get('pagerank_rank')} for k, m in pr_top],
            'spectral': core.rho,
            'metrics': metrics}


def impact_payload(core, v, oid, top=50):
    """Víctimas del colapso unitario de `oid` (precalculado)."""
    ids_, pct, hop = v.victims.get(oid) or ((oid,), (100.0,), (0,))
    st = v.stats.get(oid) or {'reach_1': 0, 'reach_10': 0, 'affected': 0, 'sum_impact': 0.0, 'max_hop': 0}
    out = []
    for k, p, hp in zip(ids_, pct, hop):
        if k == oid:
            continue
        out.append({'id': k, 'label': core.label(k), 'pct': p, 'hop': hp})
        if len(out) >= top:
            break
    by_hop = {}
    for k, hp in zip(ids_, hop):
        if k != oid and hp:
            by_hop[str(hp)] = by_hop.get(str(hp), 0) + 1
    return {'id': oid, 'label': core.label(oid), 'severity': 100, 'kind': 'collapse',
            'affected': st['affected'], 'reach_1': st['reach_1'], 'reach_10': st['reach_10'],
            'sum_impact': st['sum_impact'], 'max_hop': st['max_hop'], 'by_hop': by_hop,
            'victims': out, 'precomputed': True}


def chokepoints_payload(core, v, by='sum', limit=25):
    order = v.by_count if by == 'count' else v.by_sum
    out = []
    for rank, oid in enumerate(order[:limit], 1):
        st = v.stats[oid]
        out.append({'rank': rank, 'id': oid, 'label': core.label(oid), 'sum_impact': st['sum_impact'],
                    'reach_1': st['reach_1'], 'reach_10': st['reach_10'],
                    'sector': (core.meta.get(oid) or {}).get('sector')})
    return {'by': 'count' if by == 'count' else 'sum', 'limit': limit, 'total_sources': len(v.sources),
            'chokepoints': out}


def status(v):
    return {'sources': len(v.sources), 'nnz': v.nnz, 'content_sha': v.content_sha, 'timings': v.timings,
            'kernel': v.kernel,
            'top_by_sum': v.by_sum[:5], 'top_by_count': v.by_count[:5]}


def scenario(core, x0, factors='active', damping=None, max_hops=None, threshold=None, top=50, direction='down'):
    """Choque con varias fuentes y magnitudes (vector inicial x0) con el MISMO kernel en lote.
    factors: 'active' (fragilidad de la vista) | 'none' | lista de ids de factores activos.
    direction='up' (auge de demanda, PROP-17): misma regla con la matriz normalizada por fila y el mismo piso; solo
    si el release lo habilita (matrix.engine.direction_up_enabled) — si no, ValueError."""
    from matrix import engine as E
    if factors == 'none':
        frag = None
    elif isinstance(factors, (list, tuple)):
        want = set(factors)
        frag = E.fragility(core.idx, [f for f in core.factors if f['id'] in want])
    else:
        frag = core.frag
    dt = core.dt if direction != 'up' else E.dependency_transpose(core.mats, direction='up')
    total, first = E.propagate_block(dt, frag, x0, damping=damping, max_hops=max_hops, threshold=threshold)
    col, fh = total[:, 0], first[:, 0]
    seeds = {core.ids[i] for i in np.nonzero(x0)[0].tolist()}
    impacts = {core.ids[j]: round(float(min(1.0, col[j])) * 100, 2) for j in np.nonzero(col > 0)[0].tolist()}
    victims = sorted(((k, p) for k, p in impacts.items() if k not in seeds), key=lambda kv: (-kv[1], kv[0]))
    by_hop = {}
    for j in np.nonzero(fh)[0].tolist():
        by_hop[str(int(fh[j]))] = by_hop.get(str(int(fh[j])), 0) + 1
    return {'impacts': impacts,
            'victims': [{'id': k, 'label': core.label(k), 'pct': p, 'hop': int(fh[core.idx[k]])}
                        for k, p in victims[:top]],
            'affected': len(victims), 'reach_1': sum(1 for _, p in victims if p >= 1.0),
            'reach_10': sum(1 for _, p in victims if p >= 10.0),
            'sum_impact': round(sum(p for _, p in victims) / 100.0, 4), 'by_hop': by_hop}
