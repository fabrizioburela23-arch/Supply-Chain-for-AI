"""V2 Impact (INFRA_OPERATIVA §4.2): el colapso unitario de CADA nodo, ya calculado, con los factores activos.

Usa `matrix.engine.propagate_many` — el MISMO kernel que `propagate`, en lote (tests/test_hot_views_parity.py
exige igualdad exacta en los 937 choques). Por fuente: víctimas {id, pct, hop} ordenadas, alcance ≥ 1 %
(= cascade_size de compute_metrics) y ≥ 10 %, Σ impacto (en "empresas equivalentes": Σ pct / 100, sin el
origen). Cuellos de botella por Σ (PROP-06: el conteo premia cascadas largas y débiles) y por conteo.
También arma el payload de /api/matrix/metrics con la MISMA forma y los mismos números que compute_metrics.
"""
import gc
import hashlib
import itertools
import time

import numpy as np

_ZEROS = itertools.repeat(0)


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
    # La construcción crea cientos de miles de tuplas/dicts que viven hasta el final: con el recolector de ciclos
    # activo, cada pasada de generación 1-2 vuelve a recorrer todo ese montón (a 20k: 20-40 % del tiempo y mucho
    # ruido). Se apaga SOLO durante la construcción (el conteo de referencias sigue liberando lo demás) y se deja
    # como estaba; no cambia ningún resultado.
    gc_estaba = gc.isenabled()
    gc.disable()
    try:
        res = E.propagate_many(core.mats, core.idx, core.ids, v.sources, frag=core.frag, dt=core.dt)
        t_kernel = (time.perf_counter() - t0) * 1000
        v.victims, v.stats, v.nnz, v.content_sha, v.by_sum, v.by_count = _order_and_stats(core, v.sources, res)
        v.metrics = _metrics(core, v)
    finally:
        if gc_estaba:
            gc.enable()
    v.timings = {'kernel_ms': round(t_kernel, 2), 'total_ms': round((time.perf_counter() - t0) * 1000, 2)}
    return v


def _order_and_stats(core, sources, res):
    """Víctimas ordenadas por fuente + estadísticas + huella, con UN solo orden global (np.lexsort) en vez de un
    `sorted` por fuente (E1.1, pendiente del lote J: a 20k este bucle era ~430 de 630 ms).

    Resultado IDÉNTICO al bucle de antes, por construcción:
      · orden por fuente = (-pct, salto, id): lexsort con las mismas claves; el id se compara por su RANGO en la
        lista ordenada de ids (misma relación de orden que comparar las cadenas); dentro de una fuente los ids no se
        repiten, así que el orden queda totalmente determinado (la estabilidad no entra en juego);
      · pct/hop vuelven a ser float/int de Python (`tolist()`) antes de `repr`: la huella es byte a byte la misma;
      · `sum_impact` sigue siendo el `sum` de Python sobre la lista en ese orden (la suma en coma flotante no es
        asociativa: no se vectoriza);
      · los conteos (≥ 1 %, ≥ 10 %, afectadas) son enteros: cumsum exacto.
    tests/test_resolve_ids_impact_perf.py compara content_sha/stats/orden con el bucle de referencia a 937 y 5k.
    """
    idx_of = core.idx
    ids_list = list(core.ids)
    n = len(ids_list)
    # rango lexicográfico de cada id (índice de nodo → posición en sorted(ids)): comparar rangos = comparar cadenas
    rank_of_node = np.empty(n, dtype=np.int64)
    rank_of_node[np.fromiter(map(idx_of.__getitem__, sorted(ids_list)), dtype=np.int64, count=n)] = np.arange(n)
    keys_all, pct_all, hop_all, counts = [], [], [], []
    for oid in sources:
        impacts, hops = res[oid]
        ks = list(impacts)
        keys_all.extend(ks)
        pct_all.extend(impacts.values())
        hop_all.extend(map(hops.get, ks, _ZEROS))   # = hops.get(k, 0), sin bucle de Python
        counts.append(len(ks))
    total = len(keys_all)
    node = np.fromiter(map(idx_of.__getitem__, keys_all), dtype=np.int64, count=total)
    pct = np.asarray(pct_all, dtype=np.float64)
    hop = np.asarray(hop_all, dtype=np.int64)
    counts = np.asarray(counts, dtype=np.int64)
    src = np.repeat(np.arange(len(sources), dtype=np.int64), counts)
    order = _orden(src, pct, hop, rank_of_node[node], n)
    node_s, pct_s, hop_s = node[order], pct[order], hop[order]
    starts = np.concatenate(([0], np.cumsum(counts)))
    src_node = np.fromiter(map(idx_of.__getitem__, sources), dtype=np.int64, count=len(sources))
    is_origin = node_s == np.repeat(src_node, counts)
    # conteos por fuente (enteros: exactos) = diferencias de la suma acumulada en los cortes de cada fuente
    lo, hi = starts[:-1], starts[1:]

    def por_fuente(flags):
        cs = np.concatenate(([0], np.cumsum(flags, dtype=np.int64)))
        return cs[hi] - cs[lo]
    reach_1 = np.maximum(0, por_fuente(pct_s >= 1.0) - 1).tolist()
    reach_10 = por_fuente((pct_s >= 10.0) & ~is_origin).tolist()
    affected = (counts - por_fuente(is_origin)).tolist()
    # posición del origen dentro de su fuente (si aparece): para quitarlo de `others` sin cambiar el orden
    opos = {}
    for g in np.nonzero(is_origin)[0].tolist():
        s = int(src[order[g]])
        opos[s] = g - int(starts[s])
    # salto máximo por fuente (enteros): reduceat sobre las fuentes con víctimas; sin víctimas → 0
    max_hop = np.zeros(len(sources), dtype=np.int64)
    nz = counts > 0
    if nz.any():
        max_hop[nz] = np.maximum.reduceat(hop_s, lo[nz])
    max_hop = max_hop.tolist()
    ids_arr = np.array(ids_list, dtype=object)
    keys_l, pct_l, hop_l = ids_arr[node_s].tolist(), pct_s.tolist(), hop_s.tolist()
    starts_l = starts.tolist()
    # huella: repr((oid, ids, pct, hop)) armado con el repr de cada elemento calculado UNA vez (por nodo / por valor)
    # — la misma cadena que repr() de la tupla (tests/test_resolve_ids_impact_perf.py la compara); con un -0.0 (no
    # lo produce el kernel) se usa repr() tal cual, porque 0.0 y -0.0 son la misma clave.
    rapido = not bool(np.signbit(pct_s).any())
    if rapido:
        krepr_l = np.array([repr(x) for x in ids_list], dtype=object)[node_s].tolist()
        pcache = {x: repr(x) for x in set(pct_l)}
        prepr_l = list(map(pcache.__getitem__, pct_l))
        hcache = {x: repr(x) for x in set(hop_l)}
        hrepr_l = list(map(hcache.__getitem__, hop_l))
    victims, stats = {}, {}
    sums = []
    h = hashlib.sha256()
    for s, oid in enumerate(sources):
        a, b = starts_l[s], starts_l[s + 1]
        ids_, pc, hp = tuple(keys_l[a:b]), tuple(pct_l[a:b]), tuple(hop_l[a:b])
        victims[oid] = (ids_, pc, hp)
        p = opos.get(s)
        seg = pct_l[a:b]
        others = seg if p is None else seg[:p] + seg[p + 1:]
        si = round(sum(others) / 100.0, 4)
        sums.append(si)
        stats[oid] = {'reach_1': reach_1[s], 'reach_10': reach_10[s], 'affected': affected[s],
                      'sum_impact': si, 'max_hop': max_hop[s]}
        if not rapido:
            h.update(repr((oid, ids_, pc, hp)).encode())
        elif b - a > 1:
            h.update(('(%s, (%s), (%s), (%s))' % (repr(oid), ', '.join(krepr_l[a:b]), ', '.join(prepr_l[a:b]),
                                                 ', '.join(hrepr_l[a:b]))).encode())
        elif b - a == 1:
            h.update(('(%s, (%s,), (%s,), (%s,))' % (repr(oid), krepr_l[a], prepr_l[a], hrepr_l[a])).encode())
        else:
            h.update(('(%s, (), (), ())' % repr(oid)).encode())
    # rankings de cuellos de botella: mismas claves que sorted(..., key=(-Σ, -alcance, id)) / (-alcance, -Σ, id)
    r1 = np.asarray(reach_1, dtype=np.int64)
    sm = np.asarray(sums, dtype=np.float64)
    srank = rank_of_node[src_node]
    by_sum = [sources[i] for i in np.lexsort((srank, -r1, -sm)).tolist()]
    by_count = [sources[i] for i in np.lexsort((srank, -sm, -r1)).tolist()]
    return victims, stats, total, h.hexdigest(), by_sum, by_count


def _orden(src, pct, hop, rank, n):
    """Permutación que ordena por (fuente, -pct, salto, rango del id). Si todo pct es un valor de 2 decimales (lo que
    publica el kernel: round(…, 2)), las cuatro claves caben en UN entero de 64 bits y basta un argsort; si no (otro
    redondeo en un kernel futuro), lexsort con las cuatro claves. Las dos dan el mismo orden."""
    if pct.size:
        k = np.rint(pct * 100.0)
        hmax = int(hop.max()) + 1 if hop.size else 1
        if (k / 100.0 == pct).all() and k.min() >= 0 and k.max() <= 10000 \
                and 10001 * hmax * n * (int(src.max()) + 1) < (1 << 62):
            ki = k.astype(np.int64)
            key = ((src * 10001 + (10000 - ki)) * hmax + hop) * n + rank
            return np.argsort(key, kind='stable')
    return np.lexsort((rank, hop, -pct, src))


def _round_exact(x, nd):
    """[round(v, nd) for v in x] de Python, vectorizado y EXACTO — la misma regla que matrix.engine._pct_list: lejos
    de un empate ,5 rint(v·10^nd)/10^nd es el double más cercano al decimal redondeado (lo que devuelve round()); los
    casi-empates van por round() de Python. Solo valores ≥ 0 (pesos y PageRank)."""
    y = np.asarray(x, dtype=float)
    m = 10.0 ** nd
    t = y * m
    out = np.rint(t) / m
    near = np.abs(t - np.floor(t) - 0.5) < 1e-6
    out = out.tolist()
    if near.any():
        for i in np.nonzero(near)[0].tolist():
            out[i] = round(float(y[i]), nd)
    return out


def _metrics(core, v):
    """EXACTAMENTE matrix.engine.compute_metrics (mismo orden de inserción, mismos redondeos, mismos rangos)."""
    from matrix import engine as E
    metrics = {}
    out_w, in_w = core.out_w.tolist(), core.in_w.tolist()
    ow2, iw2, pr6 = _round_exact(core.out_w, 2), _round_exact(core.in_w, 2), _round_exact(core.pagerank, 6)
    for oid, i in core.idx.items():
        if out_w[i] == 0 and in_w[i] == 0:
            continue
        metrics[oid] = {
            'out_weight': ow2[i],
            'in_weight': iw2[i],
            'cascade_size': v.stats[oid]['reach_1'],
            'pagerank': pr6[i],
        }
    sums = {oid: v.stats[oid]['sum_impact'] for oid in metrics}
    ranked = E.chokepoint_order(metrics, sums)          # 1.0.0: por conteo · 2.0.0: por Σ impacto (PROP-06)
    for rank, (oid, m) in enumerate(ranked, 1):
        m['chokepoint_rank'] = rank
    if E._P('chokepoint_rank_by', 'count') == 'sum':
        for oid, m in metrics.items():
            m['sum_impact'] = sums[oid]
    # = sorted(metrics.items(), key=-pagerank): orden ESTABLE sobre el de inserción, misma clave
    ms = list(metrics.values())
    for rank, i in enumerate(np.argsort(-np.asarray([m['pagerank'] for m in ms], dtype=np.float64),
                                        kind='stable').tolist(), 1):
        ms[i]['pagerank_rank'] = rank
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
