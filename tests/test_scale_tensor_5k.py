"""tests/test_scale_tensor_5k.py — metas de E1.2/E1.3 (docs/expansion/EXPANSION_5K.md §3) con 5.000 empresas sintéticas
(scripts/gen_synth_graph.py). LENTA: solo corre con KH_SCALE=1 (fuera de la suite rápida, como test_scale_budget).

Metas: construir el modelo del tensor ≤ 150 ms y ≤ +10 MB; ficha p50 ≤ 1 ms; primera ficha tras una generación
nueva ≤ 500 ms (proceso ya caliente); dos generaciones seguidas sin pasar de 350 MB de pico del proceso."""
import gc
import os
import random
import sys
import time

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

pytestmark = pytest.mark.skipif(os.getenv('KH_SCALE') != '1', reason='prueba de escala: KH_SCALE=1')


def _rss_mb():
    with open('/proc/self/status') as fh:
        for line in fh:
            if line.startswith('VmRSS'):
                return int(line.split()[1]) / 1024
    return 0.0


def _hwm_mb():
    with open('/proc/self/status') as fh:
        for line in fh:
            if line.startswith('VmHWM'):
                return int(line.split()[1]) / 1024
    return 0.0


@pytest.fixture(scope='module')
def world(request):
    import core.live_fundamentals as lf
    import gen_synth_graph as G
    import ontology.db as odb
    from core.hotviews import derived, registry, source
    from matrix import tensor as T
    mp = pytest.MonkeyPatch()
    mp.setattr(odb, 'ontology_available', lambda: False)
    mp.setattr(lf, 'live_margin', lambda *_a, **_k: None)
    g, f = G.lift(G._read_snapshot(), n_target=5000, seed=42)
    datas = [source.from_snapshot(dict(g, links=[l for i, l in enumerate(g['links']) if i != k]), factors_data=f)
             for k in range(3)]
    rng = np.random.default_rng(7)
    caps = {n['id']: float(rng.lognormal(2, 2.2)) for n in g['nodes'] if rng.random() < 0.6}
    mp.setattr(T, '_caps_live', lambda: (caps, 'scale-caps'))
    registry.reset()
    derived.reset()
    yield datas, caps
    registry.reset()
    derived.reset()
    mp.undo()


def test_metas_5k(world):
    from core.hotviews import builder, derived
    from core.hotviews.views import card
    from matrix import tensor as T
    datas, caps = world
    try:                                                        # el pico (VmHWM) se mide desde aquí
        with open('/proc/self/clear_refs', 'w') as fh:
            fh.write('5')
    except OSError:
        pass
    g0 = builder.build_once(datas[0])
    cv0 = card.view(g0)
    cv0.card('TSMC')                                            # proceso caliente (imports, cachés de módulo)
    cv0.nrs_all()
    gv = g0.views['graph']
    assert len(gv.nodes) == 5000
    ts, rss = [], []
    for _ in range(3):
        T._PSI.update(key=None, val=None)
        gc.collect()
        r0 = _rss_mb()
        t = time.perf_counter()
        m = T.Model(gv.snapshot, caps, {}, 'scale', view=gv)
        ts.append((time.perf_counter() - t) * 1000)
        rss.append(_rss_mb() - r0)
        del m
    assert min(ts) <= 150, ts
    assert min(rss) <= 10, rss
    sample = random.Random(1).sample([n['id'] for n in gv.nodes], 300)
    lat = []
    for oid in sample:
        t = time.perf_counter()
        cv0.card(oid)
        lat.append((time.perf_counter() - t) * 1000)
    lat.sort()
    assert lat[len(lat) // 2] <= 1.0, lat[len(lat) // 2]
    firsts = []
    for d in datas[1:]:                                        # dos generaciones nuevas seguidas
        g = builder.build_once(d)
        t = time.perf_counter()
        c = card.view(g).card('TSMC')
        firsts.append((time.perf_counter() - t) * 1000)
        assert c['structure'] and c['structure']['downstream']['n_companies'] > 0
        card.view(g).nrs_all()
    assert max(firsts) <= 500, firsts
    assert len(derived._ORDER) <= 2
    assert _hwm_mb() <= 350, _hwm_mb()
