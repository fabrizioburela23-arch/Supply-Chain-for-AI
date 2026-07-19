"""tests/test_matrix_sparse.py — migración a matrices dispersas + centralidad.

Estos tests NO requieren base de datos: operan sobre el núcleo numérico puro
(`build_matrices_from_triples`) con grafos sintéticos, así validan la
matemática del motor de forma reproducible y aislada. Complementan (no
reemplazan) a tests/test_matrix.py, que sí valida contra el snapshot real en
Postgres y sigue siendo el árbitro del comportamiento con datos reales.

Cubren:
- Equivalencia DENSA vs DISPERSA (numpy.allclose) — el árbitro de la migración.
- Invariantes matemáticos (acotación, simetría de partner, decaimiento,
  monotonicidad por arista saliente del shock).
- Centralidad PageRank (distribución válida, componentes desconectados sin NaN,
  nodos colgantes, Personalized PageRank).
- Radio espectral ρ(T) y la condición de estabilidad damping·ρ(T) < 1.
- Ponderación de procedencia (bulto vs curado).
- Benchmark a escala (10k+ nodos, distribución power-law/scale-free).
- Extensiones bajo flag (Monte Carlo, kernel no-lineal) sin romper el default.
"""
import os
import sys
import time

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matrix import engine as E  # noqa: E402

REL = E.REL_TYPES


def _dense(m):
    """Densifica SOLO para comparar en tests con grafos pequeños."""
    return m.toarray() if hasattr(m, 'toarray') else np.asarray(m)


def _idx(n):
    return {f'n{i}': i for i in range(n)}


def _rand_triples(n, edges, rng, rels=None):
    """Triples aleatorios (source, target, rel, weight) sobre n nodos."""
    rels = rels or REL
    out = []
    for _ in range(edges):
        a, b = int(rng.integers(n)), int(rng.integers(n))
        if a == b:
            continue
        rel = rels[int(rng.integers(len(rels)))]
        w = float(rng.uniform(0.5, 5.0))
        out.append((f'n{a}', f'n{b}', rel, w))
    return out


def _scale_free_triples(n, m, rng, rels=None):
    """Grafo dirigido scale-free (Barabási–Albert): pocos nodos-hub con muchas
    conexiones, la mayoría con pocas — la forma de una economía real (spec
    §"Distribución de grado no uniforme"). NO Erdős–Rényi uniforme."""
    rels = rels or REL
    m0 = max(2, m)
    repeated = list(range(m0))
    triples = []
    for v in range(m0, n):
        targets = set()
        while len(targets) < m and repeated:
            targets.add(repeated[int(rng.integers(len(repeated)))])
        for t in targets:
            rel = rels[int(rng.integers(len(rels)))]
            w = float(rng.uniform(0.5, 5.0))
            triples.append((f'n{v}', f'n{t}', rel, w))
            repeated.append(v)
            repeated.append(t)
    return triples


# ── EQUIVALENCIA densa ↔ dispersa (el árbitro de la migración) ─────────────
def test_build_matrices_dense_vs_sparse_equivalence():
    rng = np.random.default_rng(42)
    n = 120
    idx = _idx(n)
    triples = _rand_triples(n, 600, rng)
    md, _, ids = E.build_matrices_from_triples(list(triples), idx, sparse=False)
    ms, _, _ = E.build_matrices_from_triples(list(triples), idx, sparse=True)
    for r in REL:
        assert np.allclose(_dense(md[r]), _dense(ms[r])), f'matriz {r} difiere'


def test_max_semantics_preserved_on_duplicate_pairs():
    """Colisiones de par toman el MÁXIMO (no la suma) — el error clásico al
    portar a COO→CSR, que suma duplicados."""
    idx = _idx(3)
    triples = [('n0', 'n1', 'supply', 2.0), ('n0', 'n1', 'supply', 5.0),
               ('n0', 'n1', 'supply', 3.0)]
    md, _, _ = E.build_matrices_from_triples(triples, idx, sparse=False)
    ms, _, _ = E.build_matrices_from_triples(triples, idx, sparse=True)
    assert md['supply'][0, 1] == 5.0
    assert _dense(ms['supply'])[0, 1] == 5.0


def test_propagate_dense_vs_sparse_equivalence():
    rng = np.random.default_rng(7)
    n = 150
    idx = _idx(n)
    ids = [f'n{i}' for i in range(n)]
    triples = _rand_triples(n, 900, rng)
    md, _, _ = E.build_matrices_from_triples(list(triples), idx, sparse=False)
    ms, _, _ = E.build_matrices_from_triples(list(triples), idx, sparse=True)
    shock = ['n0', 'n5', 'n9']
    imp_d, ord_d = E.propagate(md, idx, ids, shock)
    imp_s, ord_s = E.propagate(ms, idx, ids, shock)
    assert set(imp_d) == set(imp_s)
    for k in imp_d:
        assert abs(imp_d[k] - imp_s[k]) < 1e-6, f'{k}: {imp_d[k]} vs {imp_s[k]}'
    # el orden de cascada (hops) coincide
    assert {c['id']: c['hop'] for c in ord_d} == {c['id']: c['hop'] for c in ord_s}


def test_propagate_with_fragility_equivalence():
    rng = np.random.default_rng(11)
    n = 100
    idx = _idx(n)
    ids = [f'n{i}' for i in range(n)]
    triples = _rand_triples(n, 500, rng)
    md, _, _ = E.build_matrices_from_triples(list(triples), idx, sparse=False)
    ms, _, _ = E.build_matrices_from_triples(list(triples), idx, sparse=True)
    factors = [{'id': 'F1', 'label': 'x', 'severity': 8.0,
                'members': {'n3': 0.8, 'n4': 0.5}}]
    frag = E.fragility(idx, factors)
    imp_d, _ = E.propagate(md, idx, ids, ['n0'], frag=frag)
    imp_s, _ = E.propagate(ms, idx, ids, ['n0'], frag=frag)
    for k in set(imp_d) | set(imp_s):
        assert abs(imp_d.get(k, 0) - imp_s.get(k, 0)) < 1e-6


def test_modulate_equivalence():
    rng = np.random.default_rng(3)
    n = 60
    idx = _idx(n)
    triples = _rand_triples(n, 300, rng)
    md, _, _ = E.build_matrices_from_triples(list(triples), idx, sparse=False)
    ms, _, _ = E.build_matrices_from_triples(list(triples), idx, sparse=True)
    factors = [{'id': 'F', 'label': 'x', 'severity': 6.0, 'members': {'n1': 0.5}}]
    mod_d = E.modulate(md, idx, factors)
    mod_s = E.modulate(ms, idx, factors)
    for r in REL:
        assert np.allclose(_dense(mod_d[r]), _dense(mod_s[r]))


# ── INVARIANTES matemáticos ────────────────────────────────────────────────
@pytest.mark.parametrize('sparse', [False, True])
def test_impacts_bounded_0_100(sparse):
    rng = np.random.default_rng(1)
    n = 80
    idx = _idx(n)
    ids = [f'n{i}' for i in range(n)]
    md, _, _ = E.build_matrices_from_triples(_rand_triples(n, 400, rng), idx, sparse=sparse)
    imp, _ = E.propagate(md, idx, ids, ['n0'])
    assert all(0.0 <= v <= 100.0 for v in imp.values())
    assert imp['n0'] == 100.0


@pytest.mark.parametrize('sparse', [False, True])
def test_partner_symmetry_preserved(sparse):
    idx = _idx(4)
    triples = [('n0', 'n1', 'partner', 3.0), ('n2', 'n3', 'partner', 1.5)]
    m, _, _ = E.build_matrices_from_triples(triples, idx, sparse=sparse)
    p = _dense(m['partner'])
    assert np.allclose(p, p.T)
    assert p[0, 1] == 3.0 and p[1, 0] == 3.0


@pytest.mark.parametrize('sparse', [False, True])
def test_monotonicity_edge_out_of_shock(sparse):
    """Aumentar el peso de una arista SALIENTE del nodo en shock nunca reduce el
    impacto de su destino (invariante que sí sostiene la normalización por
    columna; ver nota en el informe sobre por qué la versión 'cualquier arista'
    no puede sostenerse bajo normalización columna-estocástica)."""
    idx = _idx(5)
    ids = [f'n{i}' for i in range(5)]
    base = [('n0', 'n1', 'supply', 1.0), ('n2', 'n1', 'supply', 1.0),
            ('n1', 'n3', 'supply', 1.0)]
    m0, _, _ = E.build_matrices_from_triples(base, idx, sparse=sparse)
    imp0, _ = E.propagate(m0, idx, ids, ['n0'])
    up = [('n0', 'n1', 'supply', 5.0), ('n2', 'n1', 'supply', 1.0),
          ('n1', 'n3', 'supply', 1.0)]
    m1, _, _ = E.build_matrices_from_triples(up, idx, sparse=sparse)
    imp1, _ = E.propagate(m1, idx, ids, ['n0'])
    assert imp1.get('n1', 0) >= imp0.get('n1', 0) - 1e-9


def test_decay_on_layered_dag():
    """En un DAG por capas y subcrítico (damping·ρ<1), el impacto máximo de los
    nodos alcanzados por primera vez en el hop k es no-creciente en k."""
    idx = _idx(4)
    ids = [f'n{i}' for i in range(4)]
    triples = [('n0', 'n1', 'supply', 1.0), ('n1', 'n2', 'supply', 1.0),
               ('n2', 'n3', 'supply', 1.0)]
    m, _, _ = E.build_matrices_from_triples(triples, idx, sparse=True)
    sr = E.spectral_radius(m)
    assert sr['damping_rho'] < 1.0
    _, order = E.propagate(m, idx, ids, ['n0'])
    by_hop = {}
    for c in order:
        by_hop.setdefault(c['hop'], []).append(c['impact'])
    hops = sorted(by_hop)
    maxes = [max(by_hop[h]) for h in hops]
    assert all(maxes[i] >= maxes[i + 1] - 1e-9 for i in range(len(maxes) - 1))


# ── CENTRALIDAD PageRank ───────────────────────────────────────────────────
@pytest.mark.parametrize('sparse', [False, True])
def test_pagerank_valid_distribution(sparse):
    rng = np.random.default_rng(5)
    n = 100
    idx = _idx(n)
    md, _, _ = E.build_matrices_from_triples(_rand_triples(n, 500, rng), idx, sparse=sparse)
    agg = None
    for m in md.values():
        agg = m.copy() if agg is None else agg + m
    pr = E.pagerank(agg)
    assert pr.shape == (n,)
    assert np.all(pr >= 0)
    assert not np.any(np.isnan(pr))
    assert abs(pr.sum() - 1.0) < 1e-6


def test_pagerank_disconnected_components_no_nan():
    """Robustez ante componentes desconectados (el motivo de usar PageRank y no
    eigenvector centrality pura): dos triángulos sin conexión entre sí."""
    idx = _idx(6)
    triples = [('n0', 'n1', 'supply', 1.0), ('n1', 'n2', 'supply', 1.0), ('n2', 'n0', 'supply', 1.0),
               ('n3', 'n4', 'supply', 1.0), ('n4', 'n5', 'supply', 1.0), ('n5', 'n3', 'supply', 1.0)]
    agg = None
    md, _, _ = E.build_matrices_from_triples(triples, idx, sparse=True)
    for m in md.values():
        agg = m.copy() if agg is None else agg + m
    pr = E.pagerank(agg)
    assert not np.any(np.isnan(pr))
    assert abs(pr.sum() - 1.0) < 1e-6
    assert np.all(pr > 0)


def test_pagerank_dangling_nodes():
    """Nodos colgantes (sin dependientes) no rompen la distribución."""
    idx = _idx(4)
    triples = [('n0', 'n1', 'supply', 1.0), ('n1', 'n2', 'supply', 1.0)]  # n3 aislado, n2 colgante
    md, _, _ = E.build_matrices_from_triples(triples, idx, sparse=True)
    agg = None
    for m in md.values():
        agg = m.copy() if agg is None else agg + m
    pr = E.pagerank(agg)
    assert not np.any(np.isnan(pr))
    assert abs(pr.sum() - 1.0) < 1e-6


def test_personalized_pagerank_concentrates():
    """Personalized PageRank concentra masa cerca del nodo del portafolio."""
    idx = _idx(6)
    triples = [('n0', 'n1', 'supply', 1.0), ('n1', 'n2', 'supply', 1.0),
               ('n3', 'n4', 'supply', 1.0), ('n4', 'n5', 'supply', 1.0)]
    md, _, _ = E.build_matrices_from_triples(triples, idx, sparse=True)
    agg = None
    for m in md.values():
        agg = m.copy() if agg is None else agg + m
    pers = np.zeros(6)
    pers[idx['n2']] = 1.0        # el portafolio es {n2}
    pr = E.pagerank(agg, personalization=pers)
    # la masa se concentra en el componente de n2 (n0,n1,n2), no en el otro
    comp_a = pr[idx['n0']] + pr[idx['n1']] + pr[idx['n2']]
    comp_b = pr[idx['n3']] + pr[idx['n4']] + pr[idx['n5']]
    assert comp_a > comp_b


# ── RADIO ESPECTRAL / estabilidad ──────────────────────────────────────────
def test_spectral_radius_subcritical_chain():
    idx = _idx(4)
    triples = [('n0', 'n1', 'supply', 1.0), ('n1', 'n2', 'supply', 1.0), ('n2', 'n3', 'supply', 1.0)]
    m, _, _ = E.build_matrices_from_triples(triples, idx, sparse=True)
    sr = E.spectral_radius(m, damping=0.6)
    assert sr['rho'] >= 0.0
    assert abs(sr['damping_rho'] - 0.6 * sr['rho']) < 1e-6
    assert sr['stable'] is True


def test_spectral_radius_dense_sparse_agree():
    rng = np.random.default_rng(9)
    n = 40
    idx = _idx(n)
    triples = _rand_triples(n, 120, rng)
    md, _, _ = E.build_matrices_from_triples(list(triples), idx, sparse=False)
    ms, _, _ = E.build_matrices_from_triples(list(triples), idx, sparse=True)
    rd = E.spectral_radius(md)['rho']
    rs = E.spectral_radius(ms)['rho']
    assert abs(rd - rs) < 1e-3


# ── PROCEDENCIA (bulto vs curado) ──────────────────────────────────────────
def test_provenance_weight_discount(monkeypatch):
    monkeypatch.setenv('IMPORT_BULK_WEIGHT_FACTOR', '0.5')
    assert E._eff_weight(4.0, 'curated') == 4.0
    assert E._eff_weight(4.0, None) == 4.0
    assert E._eff_weight(4.0, 'wikidata') == 2.0
    assert E._eff_weight(4.0, 'gleif') == 2.0
    # peso por defecto histórico (None/0 → 2) preservado
    assert E._eff_weight(None, 'curated') == 2.0
    assert E._eff_weight(0, 'curated') == 2.0


# ── FLAGS aditivos (Monte Carlo, no-lineal) ────────────────────────────────
def test_nonlinear_flag_off_is_identical():
    rng = np.random.default_rng(2)
    n = 60
    idx = _idx(n)
    ids = [f'n{i}' for i in range(n)]
    m, _, _ = E.build_matrices_from_triples(_rand_triples(n, 300, rng), idx, sparse=True)
    a, _ = E.propagate(m, idx, ids, ['n0'])
    b, _ = E.propagate(m, idx, ids, ['n0'], nonlinear=False)
    assert a == b


def test_monte_carlo_bands_reproducible():
    rng = np.random.default_rng(4)
    n = 60
    idx = _idx(n)
    ids = [f'n{i}' for i in range(n)]
    m, _, _ = E.build_matrices_from_triples(_rand_triples(n, 300, rng), idx, sparse=True)
    r1 = E.propagate_bands(m, idx, ids, ['n0'], n_samples=50, seed=123)
    r2 = E.propagate_bands(m, idx, ids, ['n0'], n_samples=50, seed=123)
    assert r1['bands'] == r2['bands']            # semilla fija → reproducible
    for oid, b in r1['bands'].items():
        assert b['p5'] <= b['p50'] + 1e-9 <= b['p95'] + 1e-9


# ── BENCHMARK a escala (power-law) ─────────────────────────────────────────
def test_benchmark_scale_free_sparse():
    """El motor disperso corre a escala grande en tiempo razonable con grafo
    scale-free (nodos hub). La versión densa a este tamaño requeriría ~decenas
    de GB (n×n×8 bytes × 9 matrices) — el motivo del cambio."""
    n = int(os.getenv('BENCH_N', '12000'))
    rng = np.random.default_rng(2026)
    idx = _idx(n)
    ids = [f'n{i}' for i in range(n)]
    t0 = time.time()
    triples = _scale_free_triples(n, 4, rng)
    t_gen = time.time() - t0

    t0 = time.time()
    mats, _, _ = E.build_matrices_from_triples(triples, idx, sparse=True)
    t_build = time.time() - t0

    nnz = sum(m.nnz for m in mats.values())
    t0 = time.time()
    imp, _ = E.propagate(mats, idx, ids, ['n0'])
    t_prop = time.time() - t0

    agg = None
    for m in mats.values():
        agg = m.copy() if agg is None else agg + m
    t0 = time.time()
    pr = E.pagerank(agg)
    t_pr = time.time() - t0

    t0 = time.time()
    sr = E.spectral_radius(mats)
    t_sr = time.time() - t0

    total = t_gen + t_build + t_prop + t_pr + t_sr
    print(f'\n[benchmark n={n}] gen={t_gen:.2f}s build={t_build:.2f}s '
          f'propagate={t_prop:.3f}s pagerank={t_pr:.3f}s spectral={t_sr:.3f}s '
          f'| nnz={nnz} total_matrix_ops={total - t_gen:.2f}s rho={sr["rho"]:.3f}')
    assert pr.shape == (n,) and not np.any(np.isnan(pr))
    assert (total - t_gen) < 60.0, f'motor tardó {total - t_gen:.1f}s (>60s)'
