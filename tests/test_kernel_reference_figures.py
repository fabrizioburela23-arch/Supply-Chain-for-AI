"""tests/test_kernel_reference_figures.py — INFRA_OPERATIVA paso 12 (BRECHAS bloque 1): las cifras de REFERENCIA del
kernel con `kernel.params@2.0.0` (sin activarlo: core.governance.counterfactual, solo en este hilo) sobre el snapshot.

Qué fija (PROP-05/06/07/17/19, L4-03, M-code-02):
  · socios e inversores NO transmiten daño: quitar TODOS los vínculos partner/invest deja el Impact idéntico, y
    CBCTaiwan (cuello #10 solo por 'partner' con TSMC) ya no aparece en la caída de TSMC;
  · Ψ del tensor (solo flujo) == la vista Impact: un solo motor;
  · escala de severidad 0-10 (fragilidad máxima con los factores latentes ≤ 1 + Σcoef·1/10);
  · ranking de cuellos de botella por Σ impacto (el de /api/matrix/metrics también);
  · 'up' (auge de demanda) con el piso: OpenAI → Tesla ya no pasa el 60 % por un vínculo de peso 1;
  · y que el release vigente sigue en 1.0.0 (las cifras de producción no cambian solas).
Si el CATÁLOGO cambia, regenerar los números de REF con el código del paso 12 (nunca para "arreglar" el kernel).
"""
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# cifras del snapshot data/grafo_v0.json (937 nodos / 2.510 vínculos, 69 factores latentes) con kernel.params@2.0.0
REF = {'TSMC': {'reach_1': 254, 'reach_10': 149, 'sum_impact': 41.7937},
       'Nvidia': {'reach_1': 162, 'reach_10': 88, 'sum_impact': 17.7745},
       'ASML': {'reach_1': 69, 'reach_10': 9, 'sum_impact': 3.4464},
       'Microsoft': {'reach_1': 98, 'reach_10': 25, 'sum_impact': 7.1983}}
REF_RHO = 0.907958
REF_TOP_SUM = ['TSMC', 'Nvidia', 'Amazon', 'Microsoft', 'ARM']
REF_TSMC_NVIDIA = 94.67
REF_UP_OPENAI_TESLA = 13.2


def _views(snap=None):
    from core.hotviews import source
    from core.hotviews.views import graph_core, impact
    data = source.load_snapshot() if snap is None else source.from_snapshot(snap)
    core = graph_core.build(data)
    return data, core, impact.build(core)


@pytest.fixture(scope='module')
def v2():
    from core import governance
    with governance.counterfactual({'kernel.params': '2.0.0'}):
        out = _views()
    return out                     # la vista ya calculada; el contrafactual NO queda activo para otras pruebas


def test_el_release_vigente_sigue_en_1_0_0():
    from core import governance
    assert governance.artifact_semver('kernel.params') == '1.0.0'
    assert governance.repo_bundle().artifacts['kernel.params']['semver'] == '1.0.0'
    from matrix import engine as E
    assert E.direction_up_enabled() is False and E._damage_rels() is None


def test_cifras_de_referencia_2_0_0(v2):
    from core import governance
    _d, core, imp = v2
    with governance.counterfactual({'kernel.params': '2.0.0'}):
        assert governance.artifact_semver('kernel.params') == '2.0.0'
    for oid, ref in REF.items():
        st = imp.stats[oid]
        assert (st['reach_1'], st['reach_10'], st['sum_impact']) == (ref['reach_1'], ref['reach_10'], ref['sum_impact']), oid
    assert core.rho['rho'] == pytest.approx(REF_RHO, abs=1e-5) and core.rho['stable'] is True
    assert imp.by_sum[:5] == REF_TOP_SUM
    v = dict(zip(*imp.victims['TSMC'][:2]))
    assert v['Nvidia'] == REF_TSMC_NVIDIA
    assert 'CBCTaiwan' not in v                          # solo llegaba por 'partner' (PROP-07)


def test_socios_e_inversores_no_transmiten_dano(v2):
    from core import governance
    from core.hotviews import source
    _d, _core, imp = v2
    snap, _sha = source._snapshot_parsed()
    sin = dict(snap, links=[l for l in snap['links'] if (l.get('type') or 'supply') not in ('partner', 'invest')])
    with governance.counterfactual({'kernel.params': '2.0.0'}):
        _d2, _c2, imp2 = _views(sin)
    common = set(imp.sources) & set(imp2.sources)
    assert len(common) > 700
    for oid in common:
        assert imp.victims[oid] == imp2.victims[oid], oid
    for oid in set(imp.sources) - common:      # nodos que solo tenían socios/inversores: no contagian a nadie
        assert imp.victims[oid][0] == (oid,), oid


def test_psi_del_tensor_es_la_vista_impact(v2):
    from core import governance
    from matrix import tensor as T
    _d, core, imp = v2
    with governance.counterfactual({'kernel.params': '2.0.0'}):
        fl = T._flow_impact(core)
    for oid in ('TSMC', 'Nvidia', 'ASML', 'SKHynix', 'Microsoft', 'AESCorp'):
        a = {k: p for k, p in zip(*fl.victims[oid][:2])}
        b = {k: p for k, p in zip(*imp.victims[oid][:2])}
        assert a == b, oid


def test_escala_0_10_y_ranking_por_suma(v2):
    _d, core, imp = v2
    bound = max(1.0 + sum(f['members'].get(m, 0.0) for f in core.factors) / 10.0 for m in core.idx)
    assert float(core.frag.max()) <= bound + 1e-9
    assert float(core.frag.max()) < 2.5                  # con escala 0-10 los latentes ya no rozan el tope
    top = sorted(imp.metrics.items(), key=lambda kv: kv[1]['chokepoint_rank'])[:5]
    assert [k for k, _ in top] == REF_TOP_SUM            # /api/matrix/metrics ordena por Σ (PROP-06)
    assert all('sum_impact' in m for _, m in top)


def test_auge_up_con_piso(v2):
    from core import governance
    from core.hotviews.views import impact
    _d, core, _imp = v2
    with governance.counterfactual({'kernel.params': '2.0.0'}):
        x0 = np.zeros(len(core.ids))
        x0[core.idx['OpenAI']] = 1.0
        sc = impact.scenario(core, x0, direction='up', top=500)
    assert sc['impacts']['Tesla'] == REF_UP_OPENAI_TESLA        # antes 60 en el cliente (PROP-17)
    assert all(p <= 100.0 for p in sc['impacts'].values())
    with pytest.raises(ValueError):                              # 1.0.0 (vigente): 'up' sigue sin calcularse
        impact.scenario(core, x0, direction='up')


def test_api_scenario_up_solo_con_2_0_0(monkeypatch):
    import ontology.db as odb
    import server
    from core.hotviews import builder, registry
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    registry.reset()
    builder.build_once()
    c = server.app.test_client()
    r = c.post('/api/hot/scenario', json={'shocks': ['OpenAI'], 'direction': 'up'})
    assert r.status_code == 400 and r.get_json()['param'] == 'direction'
    registry.reset()
