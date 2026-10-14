"""tests/test_resolve_ids_impact_perf.py — lote K (E1.1, pendiente del lote J): el bucle de orden/huella por fuente de
core/hotviews/views/impact.py se vectorizó (un solo np.lexsort + conteos exactos) SIN cambiar nada de lo que publica:
víctimas (ids, pct, salto) en el mismo orden, estadísticas, rankings by_sum/by_count, métricas y content_sha byte a byte.

Aquí vive el bucle de ANTES (copiado tal cual) como referencia, y se compara contra `impact.build` a 937 (catálogo real)
y a 5k (grafo levantado de scripts/gen_synth_graph.py). También fija que el kernel sigue siendo propagate_many (mismo
`res`) y que la vista no tarda más que antes a 937 (humo; la medida a 20k va en docs/ESTADO.md).
"""
import hashlib
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))


def _referencia(core, sources, res):
    """El bucle de impact.build de antes (lote J), tal cual."""
    victims, stats = {}, {}
    h = hashlib.sha256()
    nnz = 0
    for oid in sources:
        impacts, hops = res[oid]
        order = sorted(impacts.items(), key=lambda kv: (-kv[1], hops.get(kv[0], 0), kv[0]))
        ids_ = tuple(k for k, _ in order)
        pct = tuple(p for _, p in order)
        hop = tuple(hops.get(k, 0) for k in ids_)
        victims[oid] = (ids_, pct, hop)
        nnz += len(ids_)
        others = [p for k, p in order if k != oid]
        stats[oid] = {'reach_1': max(0, sum(1 for p in impacts.values() if p >= 1.0) - 1),
                      'reach_10': sum(1 for p in others if p >= 10.0),
                      'affected': len(others),
                      'sum_impact': round(sum(others) / 100.0, 4),
                      'max_hop': max(hop) if hop else 0}
        h.update(repr((oid, ids_, pct, hop)).encode())
    by_sum = sorted(sources, key=lambda k: (-stats[k]['sum_impact'], -stats[k]['reach_1'], k))
    by_count = sorted(sources, key=lambda k: (-stats[k]['reach_1'], -stats[k]['sum_impact'], k))
    return victims, stats, nnz, h.hexdigest(), by_sum, by_count


def _core(n):
    from core.hotviews import source
    from core.hotviews.views import graph_core
    if n <= 937:
        return graph_core.build(source.load_snapshot())
    import gen_synth_graph as G
    return graph_core.build(G.synth_graphdata(n))


def _comparar(core):
    from matrix import engine as E
    from core.hotviews.views import impact
    v = impact.build(core)
    res = E.propagate_many(core.mats, core.idx, core.ids, v.sources, frag=core.frag, dt=core.dt)
    victims, stats, nnz, sha, by_sum, by_count = _referencia(core, v.sources, res)
    assert v.content_sha == sha
    assert v.nnz == nnz
    assert list(v.victims) == list(victims)                       # mismo orden de inserción
    for oid in victims:
        a, b = v.victims[oid], victims[oid]
        assert a == b, oid
        assert all(type(x) is type(y) for x, y in zip(a[1], b[1])), oid   # float de Python, no np.float64
        assert all(type(x) is type(y) for x, y in zip(a[2], b[2])), oid
    assert list(v.stats) == list(stats) and v.stats == stats
    assert v.by_sum == by_sum and v.by_count == by_count
    # métricas: mismos rangos que el sorted de antes (pagerank_rank = orden estable por -pagerank; chokepoint_rank
    # = matrix.engine.chokepoint_order, sin cambios); la paridad con compute_metrics vive en test_hot_views_parity
    pr_ranked = sorted(v.metrics.items(), key=lambda kv: -kv[1]['pagerank'])
    assert [m2['pagerank_rank'] for _k, m2 in pr_ranked] == list(range(1, len(pr_ranked) + 1))
    assert list(v.metrics) == [oid for oid, i in core.idx.items() if not (core.out_w[i] == 0 and core.in_w[i] == 0)]
    for oid, m2 in v.metrics.items():
        i = core.idx[oid]
        assert m2['out_weight'] == round(float(core.out_w[i]), 2) and m2['in_weight'] == round(float(core.in_w[i]), 2)
        assert m2['pagerank'] == round(float(core.pagerank[i]), 6) and m2['cascade_size'] == stats[oid]['reach_1']
        assert type(m2['out_weight']) is float and type(m2['pagerank']) is float
    return v


def test_vectorizado_identico_al_bucle_de_referencia_937():
    core = _core(937)
    v = _comparar(core)
    assert len(v.sources) >= 900 and v.nnz > len(v.sources)


def test_vectorizado_identico_al_bucle_de_referencia_5k():
    core = _core(5000)
    v = _comparar(core)
    assert len(v.sources) >= 4800


def test_origen_fuera_de_la_primera_posicion_y_fuentes_sin_victimas():
    """Casos de borde del orden: una fuente cuyo origen NO queda primero (otra víctima al 100 % con el mismo salto 0
    es imposible, pero una con 100 % y salto 1 sí ordena DESPUÉS del origen; aquí se fuerza un `res` artificial con el
    origen en medio y una fuente sin impactos) → mismas estadísticas que la referencia."""
    import types
    from core.hotviews.views import impact
    ids = ['A', 'B', 'C', 'D']
    core = types.SimpleNamespace(ids=ids, idx={k: i for i, k in enumerate(ids)})
    res = {'A': ({'B': 100.0, 'A': 100.0, 'C': 0.5, 'D': 12.0}, {'B': 1, 'C': 2, 'D': 1}),
           'B': ({}, {}),
           'C': ({'C': 100.0}, {}),
           'D': ({'A': 3.0, 'D': 100.0, 'B': 3.0}, {'A': 2, 'B': 1})}
    got = impact._order_and_stats(core, ['A', 'B', 'C', 'D'], res)
    want = _referencia(core, ['A', 'B', 'C', 'D'], res)
    assert got == want
    assert got[0]['A'] == (('A', 'B', 'D', 'C'), (100.0, 100.0, 12.0, 0.5), (0, 1, 1, 2))
    assert got[1]['A'] == {'reach_1': 2, 'reach_10': 2, 'affected': 3, 'sum_impact': 1.125, 'max_hop': 2}
    assert got[1]['B'] == {'reach_1': 0, 'reach_10': 0, 'affected': 0, 'sum_impact': 0.0, 'max_hop': 0}


def test_humo_de_tiempo_937():
    """La vista a 937 no tarda más que antes (lote J: 25 ms; aquí con margen ×4 para máquinas lentas)."""
    from core.hotviews.views import impact
    core = _core(937)
    impact.build(core)
    best = min(_ms(lambda: impact.build(core)) for _ in range(3))
    assert best <= 400, f'impact.build a 937: {best:.1f} ms'


def _ms(fn):
    t0 = time.perf_counter()
    fn()
    return (time.perf_counter() - t0) * 1000


@pytest.mark.skipif(os.getenv('KH_SCALE') != '1', reason='lento: solo con KH_SCALE=1')
def test_impact_20k_bajo_la_meta():
    """E1.1 meta: Impact ≤ 500 ms a 20k (kernel incluido), con el mismo margen del 20 % que tests/test_scale_budget.py.
    Medido en el lote K (máquina de CI, ~1,2× más lenta que la de referencia): 743 → 446-556 ms (mejor de 3), de los
    que 185-250 ms son el kernel (propagate_many, sin tocar)."""
    from core.hotviews.views import impact
    core = _core(20000)
    impact.build(core)
    best = min(_ms(lambda: impact.build(core)) for _ in range(3))
    assert best <= 500 * 1.2, f'impact.build a 20k: {best:.1f} ms (meta 500 ms + 20 %)'


# ── piezas vectorizadas: cada una = la versión de Python ──────────────────────────────────────────────────────────

def test_orden_compuesto_igual_a_lexsort_y_cae_a_lexsort_con_otro_redondeo():
    import random
    import numpy as np
    from core.hotviews.views import impact
    rng = random.Random(7)
    n = 300
    src = np.asarray([rng.randrange(40) for _ in range(5000)], dtype=np.int64)
    pct = np.asarray([round(rng.random() * 100, 2) for _ in range(5000)])
    hop = np.asarray([rng.randrange(6) for _ in range(5000)], dtype=np.int64)
    rank = np.asarray([rng.randrange(n) for _ in range(5000)], dtype=np.int64)
    key = list(zip(src.tolist(), (-pct).tolist(), hop.tolist(), rank.tolist()))
    ref = sorted(range(5000), key=lambda i: key[i])
    got = impact._orden(src, pct, hop, rank, n).tolist()
    assert [key[i] for i in got] == [key[i] for i in ref]          # mismo orden (empates: mismas claves)
    pct3 = np.asarray([round(rng.random() * 100, 3) for _ in range(5000)])   # 3 decimales → lexsort
    assert impact._orden(src, pct3, hop, rank, n).tolist() == np.lexsort((rank, hop, -pct3, src)).tolist()
    assert impact._orden(src[:0], pct[:0], hop[:0], rank[:0], n).tolist() == []


def test_redondeo_exacto_igual_a_round_de_python():
    import random
    import numpy as np
    from core.hotviews.views import impact
    rng = random.Random(11)
    xs = [rng.random() * 10 ** rng.randint(-3, 4) for _ in range(200000)]
    xs += [2.675, 1.005, 0.125, 0.375, 2.5, 0.0, 1e-9, 123456.785, 0.000005, 0.0000045, 0.9999995, 1.0]
    for nd in (2, 6):
        got = impact._round_exact(np.asarray(xs), nd)
        assert got == [round(x, nd) for x in xs], nd
        assert all(type(v) is float for v in got)


def test_huella_rapida_igual_a_repr_con_ids_raros():
    """ids con comillas, barras, no ASCII y pct/hop de todo tipo: la cadena que se hashea es repr() exacto."""
    import hashlib
    import types
    from core.hotviews.views import impact
    ids = ["O'Reilly", 'Ñandú Ltd', 'a"b', 'x\\y', '宁德时代', 'Plain', 'Zeta']
    core = types.SimpleNamespace(ids=ids, idx={k: i for i, k in enumerate(ids)})
    res = {ids[0]: ({ids[0]: 100.0, ids[1]: 12.5, ids[4]: 0.01, ids[2]: 99.99}, {ids[1]: 1, ids[4]: 3, ids[2]: 1}),
           ids[1]: ({ids[1]: 100.0}, {}),
           ids[2]: ({}, {}),
           ids[3]: ({ids[3]: 100.0, ids[6]: 100.0}, {ids[6]: 2})}
    srcs = [ids[0], ids[1], ids[2], ids[3]]
    got = impact._order_and_stats(core, srcs, res)
    want = _referencia(core, srcs, res)
    assert got == want
    h = hashlib.sha256()
    for oid in srcs:
        h.update(repr((oid,) + want[0][oid]).encode())
    assert got[3] == h.hexdigest()
