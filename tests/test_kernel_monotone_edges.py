"""tests/test_kernel_monotone_edges.py — PROP-08 (batch I3): kernel.params@2.1.0 hace el kernel MONÓTONO.

  · la regla nueva (`propagation: 'persistent'`) solo existe en 2.1.0 ("activation": "pin"): con 1.0.0 y 2.0.0 la
    propagación es la de siempre (bit a bit), y el release del repositorio sigue en 1.0.0;
  · con 2.1.0, AGREGAR un vínculo que sale de la empresa que cae (magnitud 1) NUNCA baja el impacto de nadie
    (en 2.0.0 sí pasaba: 4 de ~80 casos, hasta ~5 puntos) — prueba de propiedad sobre el grafo real (snapshot);
  · 2.1.0 ≥ 2.0.0 nodo a nodo; más magnitud nunca baja a nadie; propagate == propagate_block (vistas rápidas);
  · la iteración corta en el punto fijo (x_k == x_{k-1}) y nunca pasa de max_hops.
Sin base, sin red.
"""
import json
import os
import random
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _core(semver):
    from core import governance
    from core.hotviews import source
    from core.hotviews.views import graph_core
    with governance.counterfactual({'kernel.params': semver}):
        return graph_core.build(source.load_snapshot())


@pytest.fixture(scope='module')
def core20():
    return _core('2.0.0')


@pytest.fixture(scope='module')
def core21():
    return _core('2.1.0')


def _with_edge(core, s, j, w=2.0, rel='supply'):
    import scipy.sparse as sp

    from matrix import engine as E
    mats = {}
    for r, m in core.mats.items():
        if r == rel:
            mm = m.tolil(copy=True) if sp.issparse(m) else m.copy()
            mm[core.idx[s], core.idx[j]] += w
            mats[r] = sp.csr_matrix(mm) if sp.issparse(m) else mm
        else:
            mats[r] = m
    return mats, E.dependency_transpose(mats)


def test_artefacto_2_1_0_es_minor_sobre_2_0_0_con_pin_y_no_entra_al_release():
    with open(os.path.join(ROOT, 'governance', 'artifacts', 'kernel.params@2.1.0.json'), encoding='utf-8') as fh:
        d = json.load(fh)
    with open(os.path.join(ROOT, 'governance', 'artifacts', 'kernel.params@2.0.0.json'), encoding='utf-8') as fh:
        p = json.load(fh)
    assert d['activation'] == 'pin' and d['change_kind'] == 'minor' and d['parent'] == 'kernel.params@2.0.0'
    extra = {k: v for k, v in d['params'].items() if k not in p['params']}
    assert extra == {'propagation': 'persistent'}
    assert all(d['params'][k] == v for k, v in p['params'].items())      # minor: solo AGREGA
    from core import governance
    man = governance.load_manifest()
    assert man['release']['artifacts']['kernel.params']['semver'] == '1.0.0'
    assert any(a['id'] == 'kernel.params' and a['semver'] == '2.1.0' and a.get('activation') == 'pin'
               for a in man['available'])


def test_1_0_0_y_2_0_0_no_usan_la_regla_nueva():
    from core import governance
    from matrix import engine as E
    assert E.persistent_source() is False                                # release vigente (1.0.0)
    with governance.counterfactual({'kernel.params': '2.0.0'}):
        assert E.persistent_source() is False
    with governance.counterfactual({'kernel.params': '2.1.0'}):
        assert E.persistent_source() is True


def test_agregar_un_vinculo_desde_la_que_cae_nunca_baja_a_nadie_en_2_1_0(core21):
    from core import governance
    from matrix import engine as E
    rng = random.Random(8)
    with governance.counterfactual({'kernel.params': '2.1.0'}):
        for src in ('TSMC', 'ASML', 'Nvidia'):
            base, _ = E.propagate(core21.mats, core21.idx, core21.ids, [src], frag=core21.frag, dt=core21.dt)
            for _ in range(25):
                j = rng.choice(core21.ids)
                if j == src:
                    continue
                mats, dt = _with_edge(core21, src, j)
                imp, _ = E.propagate(mats, core21.idx, core21.ids, [src], frag=core21.frag, dt=dt)
                drops = {k: v - imp.get(k, 0.0) for k, v in base.items() if imp.get(k, 0.0) < v - 1e-9}
                assert not drops, (src, j, sorted(drops.items(), key=lambda kv: -kv[1])[:3])


def test_en_2_0_0_el_mismo_experimento_si_bajaba_a_alguien(core20):
    """El defecto que cierra PROP-08 existe de verdad en la versión anterior (si no, la prueba de arriba no probaría
    nada): con la fuente que no re-emite, un vínculo nuevo diluye a los otros proveedores del cliente."""
    from core import governance
    from matrix import engine as E
    rng = random.Random(5)
    found = 0
    with governance.counterfactual({'kernel.params': '2.0.0'}):
        base, _ = E.propagate(core20.mats, core20.idx, core20.ids, ['TSMC'], frag=core20.frag, dt=core20.dt)
        for _ in range(80):
            j = rng.choice(core20.ids)
            if j == 'TSMC':
                continue
            mats, dt = _with_edge(core20, 'TSMC', j)
            imp, _ = E.propagate(mats, core20.idx, core20.ids, ['TSMC'], frag=core20.frag, dt=dt)
            if any(imp.get(k, 0.0) < v - 1e-9 for k, v in base.items()):
                found += 1
    assert found >= 1


def test_2_1_0_es_mayor_o_igual_que_2_0_0_y_monotono_en_la_magnitud(core21):
    from core import governance
    from matrix import engine as E
    sample = ['TSMC', 'Nvidia', 'ASML'] + random.Random(3).sample(core21.ids, 12)
    for sid in sample:
        with governance.counterfactual({'kernel.params': '2.0.0'}):
            old, _ = E.propagate(core21.mats, core21.idx, core21.ids, [sid], frag=core21.frag, dt=core21.dt)
        with governance.counterfactual({'kernel.params': '2.1.0'}):
            new, _ = E.propagate(core21.mats, core21.idx, core21.ids, [sid], frag=core21.frag, dt=core21.dt)
            assert all(new.get(k, 0.0) >= v for k, v in old.items()), sid
            prev = {}
            for mag in (0.1, 0.4, 0.7, 1.0):
                imp, _ = E.propagate(core21.mats, core21.idx, core21.ids, [sid], magnitude=mag, frag=core21.frag,
                                     dt=core21.dt)
                assert all(imp.get(k, 0.0) >= v for k, v in prev.items()), (sid, mag)
                prev = imp


def test_propagate_igual_a_propagate_block_y_many_en_2_1_0(core21):
    from core import governance
    from matrix import engine as E
    srcs = ['TSMC', 'Nvidia', 'ASML', 'Microsoft'] + random.Random(4).sample(core21.ids, 20)
    with governance.counterfactual({'kernel.params': '2.1.0'}):
        many = E.propagate_many(core21.mats, core21.idx, core21.ids, srcs, frag=core21.frag, dt=core21.dt, chunk=7)
        for s in srcs:
            imp, order = E.propagate(core21.mats, core21.idx, core21.ids, [s], frag=core21.frag, dt=core21.dt)
            assert many[s][0] == imp, s
            assert many[s][1] == {o['id']: o['hop'] for o in order}, s


def test_punto_fijo_y_tope_de_saltos():
    """Grafo chico: la cadena A→B→C converge antes del tope; un ciclo nunca pasa de max_hops ni de 1."""
    from core import governance
    from matrix import engine as E
    ids = ['A', 'B', 'C', 'D']
    idx = {k: i for i, k in enumerate(ids)}
    tri = [('A', 'B', 'supply', 6.0), ('B', 'C', 'supply', 6.0), ('C', 'B', 'supply', 6.0), ('C', 'D', 'supply', 3.0)]
    with governance.counterfactual({'kernel.params': '2.1.0'}):
        mats, _, _ = E.build_matrices_from_triples(tri, idx, sparse=None)
        imp, order = E.propagate(mats, idx, ids, ['A'])
        assert imp['A'] == 100.0 and 0 < imp['D'] <= imp['C'] <= 100.0
        assert max(o['hop'] for o in order) <= E._P('max_hops')
        tot, first = E.propagate_block(E.dependency_transpose(mats), None, np.array([1.0, 0.0, 0.0, 0.0]))
        assert [round(float(x) * 100, 2) for x in tot[:, 0]] == [imp.get(k, 0.0) for k in ids]
        assert np.all(tot <= 1.0)


def test_el_resumen_de_2_1_0_dice_solo_la_propiedad_que_se_cumple(core21):
    """Revisión lote I: el resumen que Fabrizio lee ANTES de poner el PIN decía «sumar un proveedor afectado nunca
    puede hacer que alguien parezca menos golpeado» — falso para vínculos desde OTRA empresa golpeada (reparten la
    columna). Ahora dice la propiedad acotada; el hash no cambia (el resumen no es parte del cuerpo con hash) y aquí
    queda documentado un contraejemplo real del grafo."""
    from core import governance
    from matrix import engine as E
    with open(os.path.join(ROOT, 'governance', 'artifacts', 'kernel.params@2.1.0.json'), encoding='utf-8') as fh:
        d = json.load(fh)
    assert 'proveedor afectado nunca' not in d['summary_es'] and 'affected supplier can never' not in d['summary_en']
    assert 'SALE de la empresa que cae' in d['summary_es'] and 'OUT OF the failing company' in d['summary_en']
    assert 'OTRA empresa' in d['summary_es'] and 'ANOTHER hit company' in d['summary_en']
    with governance.counterfactual({'kernel.params': '2.1.0'}):
        src = core21.resolve('TSMC')
        base, _ = E.propagate(core21.mats, core21.idx, core21.ids, [src], frag=core21.frag,
                              dt=E.dependency_transpose(core21.mats))
        hit = [k for k, v in base.items() if 5 < v < 60 and k != src]
        rnd, drops = random.Random(7), 0
        for _ in range(300):
            a, j = rnd.choice(hit), rnd.choice(core21.ids)
            if j in (a, src):
                continue
            mats, dt = _with_edge(core21, a, j)
            imp, _ = E.propagate(mats, core21.idx, core21.ids, [src], frag=core21.frag, dt=dt)
            if any(imp.get(k, 0) < v - 1e-9 for k, v in base.items()):
                drops += 1
                break
    assert drops == 1, 'un vínculo desde otra empresa golpeada puede bajar impactos (lo que el resumen ahora dice)'
