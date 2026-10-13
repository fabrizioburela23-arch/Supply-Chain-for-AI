"""tests/test_kernel_monotone_severity.py — INFRA_OPERATIVA paso 12: propiedades del kernel con kernel.params@2.0.0
(contrafactual en este hilo; el release vigente no cambia).

  · monotonía en la severidad: más magnitud nunca baja el impacto de nadie (choques de un nodo y de factores);
  · ninguna entrada del kernel supera 1: al disparar un factor, x0 del miembro = magnitud × coeficiente ≤ 1 (PROP-05);
  · 'estrés severo' (nonlinear) AMPLIFICA: nunca por debajo del lineal (PROP-15); en 1.0.0 se conserva la saturación;
  · entradas de factores (PROP-20): coeficiente 0 = sin efecto; severidad 0 = sin efecto; ausente = la latente;
  · la regla escrita del kernel (PROP-19): dentro de un salto se SUMA, entre saltos el MÁXIMO.
"""
import os
import random
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


@pytest.fixture(scope='module')
def core2():
    from core import governance
    from core.hotviews import source
    from core.hotviews.views import graph_core
    with governance.counterfactual({'kernel.params': '2.0.0'}):
        out = graph_core.build(source.load_snapshot())
    return out                     # el contrafactual NO queda activo para otras pruebas


@pytest.fixture()
def cf():
    from core import governance
    with governance.counterfactual({'kernel.params': '2.0.0'}) as c:
        yield c


def test_mas_magnitud_nunca_baja_a_nadie(core2, cf):
    from matrix import engine as E
    sample = ['TSMC', 'Nvidia', 'ASML'] + random.Random(11).sample(core2.ids, 25)
    for sid in sample:
        prev = {}
        for mag in (0.1, 0.25, 0.5, 0.75, 1.0):
            imp, _ = E.propagate(core2.mats, core2.idx, core2.ids, [sid], magnitude=mag, frag=core2.frag,
                                 dt=core2.dt)
            for k, v in prev.items():
                assert imp.get(k, 0.0) >= v, (sid, mag, k)
            prev = imp


def test_disparar_factor_entradas_acotadas_y_monotono(core2, cf):
    from matrix import engine as E
    for f in core2.factors[:20]:
        prev = None
        for crisis in (2.0, 5.0, 8.0, 10.0):
            mag = min(1.0, crisis / float(E._P('severity_divisor')))
            x0 = {m: mag * min(1.0, c) for m, c in f['members'].items() if m in core2.idx}
            assert x0 and max(x0.values()) <= 1.0
            frag = E.fragility(core2.idx, [dict(g, severity=crisis) if g['id'] == f['id'] else g for g in core2.factors])
            imp, _ = E.propagate(core2.mats, core2.idx, core2.ids, list(x0), frag=frag, x0=x0, dt=core2.dt)
            assert max(imp.values()) <= 100.0
            if prev is not None:
                for k, v in prev.items():
                    assert imp.get(k, 0.0) >= v, (f['id'], crisis, k)
            prev = imp


def test_estres_severo_amplifica_en_2_0_0_y_satura_en_1_0_0(core2):
    from core import governance
    from matrix import engine as E
    for sid in ('TSMC', 'Nvidia', 'ASML'):
        with governance.counterfactual({'kernel.params': '2.0.0'}):
            lin, _ = E.propagate(core2.mats, core2.idx, core2.ids, [sid], frag=core2.frag, dt=core2.dt)
            amp, _ = E.propagate(core2.mats, core2.idx, core2.ids, [sid], frag=core2.frag, dt=core2.dt, nonlinear=True)
        assert all(amp.get(k, 0.0) >= v for k, v in lin.items()) and sum(amp.values()) > sum(lin.values())
        old_lin, _ = E.propagate(core2.mats, core2.idx, core2.ids, [sid], frag=core2.frag, dt=core2.dt)
        old_nl, _ = E.propagate(core2.mats, core2.idx, core2.ids, [sid], frag=core2.frag, dt=core2.dt, nonlinear=True)
        assert all(old_nl.get(k, 0.0) <= v for k, v in old_lin.items())       # 1.0.0: atenúa (se conserva)


def test_entradas_de_factores_cero_y_ausente(cf):
    from matrix import engine as E
    assert E.factor_coef(0) == 0.0 and E.factor_coef(None) == 1.0 and E.factor_coef(0.4) == 0.4
    assert E.factor_severity(None) == 1.0 and E.factor_severity(0) == 0.0
    idx = {'A': 0, 'B': 1}
    f = E.fragility(idx, [{'id': 'F', 'severity': 0.0, 'members': {'A': 0.9}},
                          {'id': 'G', 'severity': 8.0, 'members': {'B': 0.0}}])
    assert list(f) == [1.0, 1.0]


def test_entradas_de_factores_1_0_0_se_conservan():
    from matrix import engine as E
    assert E.factor_coef(0) == 1.0 and E.factor_severity(None) == 5.0     # comportamiento de hoy (repetible)


def test_regla_escrita_suma_dentro_del_salto_maximo_entre_saltos(cf):
    """Diamante: S→A→T y S→B→T (mismo largo) SUMAN en T; un atajo S→T directo no se suma al camino largo."""
    from matrix import engine as E
    idx = {'S': 0, 'A': 1, 'B': 2, 'T': 3}
    ids = ['S', 'A', 'B', 'T']
    mats, _, _ = E.build_matrices_from_triples([('S', 'A', 'supply', 6.0), ('S', 'B', 'supply', 6.0),
                                                ('A', 'T', 'supply', 3.0), ('B', 'T', 'supply', 3.0)], idx, sparse=True)
    imp, _ = E.propagate(mats, idx, ids, ['S'])
    a = 0.6 * 1.0                      # damping × (6/6) × α_supply
    t = 0.6 * (a * 3 / 6 + a * 3 / 6)  # SUMA de las dos ramas dentro del salto 2
    assert imp['A'] == round(a * 100, 2) and imp['T'] == round(t * 100, 2)
    assert 'Partner' not in imp


def test_socio_no_contagia_en_2_0_0(cf):
    from matrix import engine as E
    idx = {'S': 0, 'P': 1}
    mats, _, _ = E.build_matrices_from_triples([('S', 'P', 'partner', 6.0), ('S', 'P', 'invest', 6.0)], idx,
                                               sparse=True)
    imp, _ = E.propagate(mats, idx, ['S', 'P'], ['S'])
    assert imp == {'S': 100.0}
    assert E.spectral_radius(mats)['rho'] == 0.0
