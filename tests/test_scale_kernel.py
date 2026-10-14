"""tests/test_scale_kernel.py — EXPANSION_5K E0.2 + E1.1: el kernel en lote DISPERSO da EXACTAMENTE lo mismo.

  · `propagate_many` (bloques CSR, matrix/engine._propagate_many_sparse) == el lote DENSO de antes (copia privada de
    referencia AQUÍ, no en el motor), impactos Y saltos, igualdad exacta (también el orden de inserción), en TODAS las
    fuentes del snapshot real con kernel.params 1.0.0, 2.0.0 y 2.1.0 (PROP-08 persistente), y en el grafo sintético
    de 5k (scripts/gen_synth_graph.py); 10k/20k solo con KH_SCALE=1;
  · otros parámetros (damping, saltos, magnitud, umbral, no lineal 'saturate'/'amplify', sin fragilidad, chunk);
  · el redondeo vectorizado (_pct_list) == round() de Python;
  · a 5k el lote no aloca bloques densos n×k (pico de memoria acotado);
  · E0.2: MATRIX_ENGINE=dense por encima de DENSE_MAX_NODES usa disperso y deja el aviso para el 🩺;
  · el generador sintético cumple el contrato (determinista, no toca la entrada ni data/).
Sin base, sin red.
"""
import json
import os
import random
import subprocess
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

VERSIONS = ('1.0.0', '2.0.0', '2.1.0')
scale = pytest.mark.skipif(os.getenv('KH_SCALE') != '1', reason='escala 10k/20k: solo con KH_SCALE=1')


# ── referencia: el lote DENSO tal como era antes de E1.1 (no se importa del motor a propósito) ──────────────────
def _ref_block(DT, frag, X0, damping, max_hops, threshold, nonlinear=False):
    from matrix import engine as E
    n, k = X0.shape
    fcol = (frag if frag is not None else np.ones(n))[:, None]
    total = X0.copy()
    reached = X0 != 0
    first = np.zeros((n, k), dtype=np.int8)
    cur = X0
    persistent = E.persistent_source()
    for hop in range(1, max_hops + 1):
        prev = cur
        cur = damping * np.asarray(DT @ cur) * fcol
        if nonlinear:
            cur = E._nonlinear(cur)
        cur = np.minimum(cur, 1.0)
        cur[cur < threshold] = 0.0
        if persistent:
            cur = np.maximum(X0, cur)
            if np.array_equal(cur, prev):
                break
        elif not cur.any():
            break
        newly = (cur > 0) & ~reached
        first[newly] = hop
        reached |= newly
        total = np.maximum(total, cur)
    return total, first


def _ref_many(core, sources, magnitude=None, damping=None, max_hops=None, threshold=None, frag='core',
              nonlinear=False, dt=None, chunk=128):
    from matrix import engine as E
    magnitude, damping, max_hops, threshold = E._kp(magnitude, damping, max_hops, threshold)
    frag = core.frag if isinstance(frag, str) else frag
    DT = core.dt if dt is None else dt
    ids, n = core.ids, len(core.ids)
    cols = [core.idx[s] for s in sources if s in core.idx]
    out = {}
    for start in range(0, len(cols), chunk):
        part = cols[start:start + chunk]
        X0 = np.zeros((n, len(part)))
        for c, i in enumerate(part):
            X0[i, c] = magnitude
        total, first = _ref_block(DT, frag, X0, damping, max_hops, threshold, nonlinear)
        for c, i in enumerate(part):
            col = total[:, c]
            impacts = {ids[j]: round(float(min(1.0, col[j])) * 100, 2) for j in np.nonzero(col > 0)[0].tolist()}
            fh = first[:, c]
            out[ids[i]] = (impacts, {ids[j]: int(fh[j]) for j in np.nonzero(fh)[0].tolist()})
    return out


def _sources(core):
    return [oid for oid, i in core.idx.items() if not (core.out_w[i] == 0 and core.in_w[i] == 0)]


def _assert_same(ref, new, label):
    assert set(ref) == set(new), label
    bad_i = [s for s in ref if list(ref[s][0].items()) != list(new[s][0].items())]
    bad_h = [s for s in ref if list(ref[s][1].items()) != list(new[s][1].items())]
    assert not bad_i and not bad_h, (label, len(bad_i), len(bad_h), bad_i[:5], bad_h[:5])


def _core_for(semver, n=None):
    from core import governance
    from core.hotviews import source
    from core.hotviews.views import graph_core
    with governance.counterfactual({'kernel.params': semver}):
        if n is None:
            data = source.load_snapshot()
        else:
            from scripts import gen_synth_graph
            data = gen_synth_graph.synth_graphdata(n)
        return graph_core.build(data)


@pytest.fixture(scope='module')
def snap_cores():
    return {v: _core_for(v) for v in VERSIONS}


@pytest.fixture(scope='module')
def synth5k_cores():
    return {v: _core_for(v, 5000) for v in VERSIONS}


def _parity_all_sources(core, semver, label, sources=None):
    from core import governance
    from matrix import engine as E
    import scipy.sparse as sp
    assert sp.issparse(core.dt)
    srcs = _sources(core) if sources is None else sources
    with governance.counterfactual({'kernel.params': semver}):
        assert E.persistent_source() is (semver == '2.1.0')
        new = E.propagate_many(core.mats, core.idx, core.ids, srcs, frag=core.frag, dt=core.dt)
        ref = _ref_many(core, srcs)
    _assert_same(ref, new, label)
    return new


# ── paridad exacta ─────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize('semver', VERSIONS)
def test_snapshot_todas_las_fuentes_igual_al_lote_denso(snap_cores, semver):
    core = snap_cores[semver]
    assert len(core.ids) >= 937
    new = _parity_all_sources(core, semver, f'snapshot@{semver}')
    assert sum(len(v[0]) for v in new.values()) > 5000          # no es un empate trivial de diccionarios vacíos


@pytest.mark.parametrize('semver', VERSIONS)
def test_sintetico_5k_todas_las_fuentes_igual_al_lote_denso(synth5k_cores, semver):
    core = synth5k_cores[semver]
    assert len(core.ids) >= 5000
    _parity_all_sources(core, semver, f'synth5k@{semver}')


@pytest.mark.parametrize('semver', VERSIONS)
def test_otros_parametros_tambien_identicos(snap_cores, semver):
    from core import governance
    from matrix import engine as E
    core = snap_cores[semver]
    sample = ['TSMC', 'Nvidia', 'ASML'] + random.Random(11).sample(core.ids, 150)
    variants = ({'damping': 0.8, 'max_hops': 9}, {'magnitude': 0.4, 'threshold': 0.02}, {'nonlinear': True},
                {'frag': None}, {'frag': None, 'nonlinear': True, 'damping': 0.9}, {'magnitude': 0.0},
                {'threshold': 0.0, 'max_hops': 3}, {'chunk': 7})
    with governance.counterfactual({'kernel.params': semver}):
        for kw in variants:
            kw = dict(kw)
            frag = kw.pop('frag', 'core')
            chunk = kw.pop('chunk', None)
            new = E.propagate_many(core.mats, core.idx, core.ids, sample, dt=core.dt,
                                   frag=core.frag if isinstance(frag, str) else frag, chunk=chunk, **kw)
            ref = _ref_many(core, sample, frag=frag, **kw)
            _assert_same(ref, new, (semver, kw, frag, chunk))


def test_igual_a_propagate_del_bucle_en_2_1_0_y_no_lineal(snap_cores):
    """El lote disperso también == `propagate` (un choque) — la regla de PROP-19 que cumplen los tres."""
    from core import governance
    from matrix import engine as E
    for semver in ('2.0.0', '2.1.0'):
        core = snap_cores[semver]
        sample = ['TSMC', 'Microsoft'] + random.Random(5).sample(core.ids, 60)
        with governance.counterfactual({'kernel.params': semver}):
            for kw in ({}, {'nonlinear': True}):
                many = E.propagate_many(core.mats, core.idx, core.ids, sample, frag=core.frag, dt=core.dt, **kw)
                for oid in sample:
                    imp, order = E.propagate(core.mats, core.idx, core.ids, [oid], frag=core.frag, dt=core.dt,
                                             **kw)
                    assert imp == many[oid][0], (semver, kw, oid)
                    assert {o['id']: o['hop'] for o in order} == many[oid][1], (semver, kw, oid)


def test_fuentes_repetidas_o_desconocidas(snap_cores):
    from matrix import engine as E
    core = snap_cores['1.0.0']
    srcs = ['TSMC', 'no-existe', 'TSMC', 'ASML']
    new = E.propagate_many(core.mats, core.idx, core.ids, srcs, frag=core.frag, dt=core.dt)
    assert set(new) == {'TSMC', 'ASML'}
    _assert_same(_ref_many(core, srcs), new, 'repetidas')
    assert E.propagate_many(core.mats, core.idx, core.ids, [], frag=core.frag, dt=core.dt) == {}


def test_tension_densa_sigue_por_el_lote_denso():
    """Con Tᵀ densa (MATRIX_ENGINE=dense ≤ DENSE_MAX_NODES o sin scipy) el lote es el de siempre."""
    from matrix import engine as E
    ids = ['A', 'B', 'C', 'D', 'E']
    idx = {k: i for i, k in enumerate(ids)}
    tri = [('A', 'B', 'supply', 6.0), ('B', 'C', 'fab', 4.0), ('A', 'C', 'cloud', 2.0), ('C', 'D', 'supply', 3.0),
           ('D', 'B', 'partner', 1.0), ('E', 'A', 'supply', 5.0)]
    mats, _, _ = E.build_matrices_from_triples(tri, idx, sparse=False)
    dt = E.dependency_transpose(mats)
    assert isinstance(dt, np.ndarray)
    frag = E.fragility(idx, [{'id': 'F', 'severity': 4.0, 'members': {'B': 0.8}}])

    class _C:
        pass
    core = _C()
    core.ids, core.idx, core.frag, core.dt = ids, idx, frag, dt
    new = E.propagate_many(mats, idx, ids, ids, frag=frag, dt=dt)
    _assert_same(_ref_many(core, ids), new, 'denso')
    sp_mats, _, _ = E.build_matrices_from_triples(tri, idx, sparse=True)
    sp_new = E.propagate_many(sp_mats, idx, ids, ids, frag=frag)
    assert {k: v[1] for k, v in sp_new.items()} == {k: v[1] for k, v in new.items()}


# ── redondeo vectorizado ───────────────────────────────────────────────────────────────────────────────────────
def test_pct_list_es_round_de_python():
    from matrix import engine as E
    rng = np.random.default_rng(0)
    ties = (np.arange(0, 20001) + 0.5) / 20000.0
    arrays = [rng.random(400_000), rng.random(200_000) ** 8, np.arange(0, 200_001) / 200_000.0, ties,
              np.nextafter(ties, 2.0), np.nextafter(ties, -1.0),
              np.array([1.0, 1.5, 7.0, 1e-300, 5e-5, 4.9999999e-5, 1e-4, 0.12345, 0.99995, 0.999949999])]
    for x in arrays:
        got = E._pct_list(x)
        want = [round(float(min(1.0, v)) * 100, 2) for v in x]
        bad = [(v, a, b) for v, a, b in zip(x.tolist(), got, want) if a != b or repr(a) != repr(b)]
        assert not bad, bad[:5]


# ── memoria: nada de bloques densos n×k ────────────────────────────────────────────────────────────────────────
def test_5k_sin_bloques_densos(synth5k_cores):
    import tracemalloc

    from matrix import engine as E
    core = synth5k_cores['1.0.0']
    srcs = _sources(core)
    tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        m0 = tracemalloc.get_traced_memory()[0]
        E.propagate_many(core.mats, core.idx, core.ids, srcs, frag=core.frag, dt=core.dt)
        peak = tracemalloc.get_traced_memory()[1] - m0
    finally:
        tracemalloc.stop()
    dense_block = len(core.ids) * E.SPARSE_CHUNK * 8
    assert peak < dense_block / 2, (peak, dense_block)              # medido: ~7 MB contra 82 MB por bloque denso


# ── E0.2: MATRIX_ENGINE=dense con más de DENSE_MAX_NODES ──────────────────────────────────────────────────────
def test_dense_rechazado_sobre_2000_nodos(monkeypatch):
    import scipy.sparse as sp

    from matrix import engine as E
    monkeypatch.setattr(E, '_DENSE_REFUSED', {})
    monkeypatch.setenv('MATRIX_ENGINE', 'dense')
    assert E.dense_refused() is None
    n = E.DENSE_MAX_NODES + 1
    assert n == 2001
    ids = [f'N{i:05d}' for i in range(n)]
    idx = {k: i for i, k in enumerate(ids)}
    tri = [(ids[i], ids[i + 1], 'supply', 3.0) for i in range(n - 1)]
    mats, _, _ = E.build_matrices_from_triples(tri, idx)
    assert all(sp.issparse(m) for m in mats.values())
    w = E.dense_refused()
    assert w and w['requested'] == 'dense' and w['used'] == 'sparse' and w['n'] == 2001 and w['limit'] == 2000
    assert '2001' in w['es'] and '2001' in w['en'] and w['es'] != w['en']
    # el kernel funciona igual sobre las matrices dispersas
    dt = E.dependency_transpose(mats)
    res = E.propagate_many(mats, idx, ids, [ids[0]], dt=dt)
    assert res[ids[0]][1].get(ids[1]) == 1
    # la variable ya no está en 'dense' → sin aviso
    monkeypatch.setenv('MATRIX_ENGINE', 'sparse')
    assert E.dense_refused() is None


def test_dense_obedecido_hasta_el_tope(monkeypatch):
    import scipy.sparse as sp

    from matrix import engine as E
    monkeypatch.setattr(E, '_DENSE_REFUSED', {})
    monkeypatch.setattr(E, 'DENSE_MAX_NODES', 4)
    monkeypatch.setenv('MATRIX_ENGINE', 'dense')
    tri = [('A', 'B', 'supply', 2.0)]
    m4, _, _ = E.build_matrices_from_triples(tri, {k: i for i, k in enumerate('ABCD')})
    assert all(isinstance(m, np.ndarray) for m in m4.values()) and E.dense_refused() is None
    m5, _, _ = E.build_matrices_from_triples(tri, {k: i for i, k in enumerate('ABCDE')})
    assert all(sp.issparse(m) for m in m5.values()) and E.dense_refused()['n'] == 5
    # explícito sparse=False manda (comparación denso↔disperso de /api/matrix/parity)
    m5d, _, _ = E.build_matrices_from_triples(tri, {k: i for i, k in enumerate('ABCDE')}, sparse=False)
    assert all(isinstance(m, np.ndarray) for m in m5d.values())
    assert E._use_sparse() is False                                  # sin n: el comportamiento de siempre


# ── generador sintético (contrato compartido) ──────────────────────────────────────────────────────────────────
def test_lift_contrato_y_determinismo():
    from scripts import gen_synth_graph as G
    from core.hotviews import source
    g, _ = source._snapshot_parsed()
    before = (len(g['nodes']), len(g['links']), json.dumps(g['nodes'][0], sort_keys=True))
    fdata = G._read_factors()
    nf = len(fdata['factors'])
    g2, f2 = G.lift(g, n_target=2000, seed=7, factors=fdata)
    assert (len(g['nodes']), len(g['links']), json.dumps(g['nodes'][0], sort_keys=True)) == before
    assert len(fdata['factors']) == nf                                 # la entrada no se toca
    assert len(g2['nodes']) == 2000 and len({n['id'] for n in g2['nodes']}) == 2000
    assert len(g2['links']) > len(g['links']) and len(f2['factors']) > nf
    assert set(g2) == set(g) and set(f2) == set(fdata)
    g3, f3 = G.lift(g, n_target=2000, seed=7, factors=fdata)
    assert json.dumps(g3['links']) == json.dumps(g2['links']) and json.dumps(f3) == json.dumps(f2)
    gh, _ = G.lift(g, n_target=2000, seed=7, hub_bias=0.3, factors=fdata)
    assert json.dumps(gh['links']) != json.dumps(g2['links'])
    keys = {(l['source'], l['target'], l['type']) for l in g2['links']}
    assert len(keys) == len(g2['links'])                               # sin vínculos repetidos


def test_from_snapshot_factors_data_reemplaza_al_archivo():
    from scripts import gen_synth_graph as G
    from core.hotviews import source
    g, sha = source._snapshot_parsed()
    base = source.from_snapshot(g, sha)
    assert len(base.factors) > 0
    none = source.from_snapshot(g, sha, factors_data={})
    assert none.factors == [] and none.triples == base.triples
    d = G.synth_graphdata(1500, seed=3)
    assert len(d.ids) >= 1500 and len(d.factors) > len(base.factors)
    assert any('_S' in f['id'] for f in d.factors)


def test_cli_escribe_en_out_y_nunca_en_data(tmp_path):
    script = os.path.join(ROOT, 'scripts', 'gen_synth_graph.py')
    r = subprocess.run([sys.executable, script, '--n', '1200', '--out', str(tmp_path)], capture_output=True,
                       text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    info = json.loads(r.stdout.strip().splitlines()[-1])
    assert info['nodes'] == 1200
    assert os.path.exists(tmp_path / 'grafo.json') and os.path.exists(tmp_path / 'factors.json')
    r = subprocess.run([sys.executable, script, '--n', '1200', '--out', os.path.join(ROOT, 'data')],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode != 0


# ── escala grande (KH_SCALE=1) ─────────────────────────────────────────────────────────────────────────────────
@scale
@pytest.mark.parametrize('n', (10000, 20000))
def test_sintetico_grande_igual_al_lote_denso(n):
    for semver in ('1.0.0', '2.1.0'):
        _parity_all_sources(_core_for(semver, n), semver, f'synth{n}@{semver}')
