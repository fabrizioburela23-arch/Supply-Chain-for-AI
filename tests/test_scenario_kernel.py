"""tests/test_scenario_kernel.py — INFRA_OPERATIVA paso 12 (PROP-09/10, L4-03/04, L4-M2): con kernel.params@2.0.0 los
escenarios solo SIEMBRAN y propaga EL kernel; en la simulación por agentes los % salen del kernel y la IA solo narra.
Con 1.0.0 (vigente) todo queda como hoy (la BFS propia se conserva como implementación retenida de 1.0.0).
"""
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCEN = ('Taiwan blockade', 'China prohíbe exportar HBM', 'boom de demanda de GPUs', 'huelga en ASML')


def _cf():
    from core import governance
    return governance.counterfactual({'kernel.params': '2.0.0'})


def test_1_0_0_conserva_la_bfs_de_siempre():
    from core import scenario_engine as SE
    from core import semantic
    a = SE.analyze('Taiwan blockade', semantic._load_snapshot())
    assert a['engine']['method'].startswith('scenario_bfs@1')
    assert {x['sev'] for x in a['impacts'] if x['channel'] == 'customer'} <= {-0.7, -0.56, -0.42, -0.28, -0.21, -0.14,
                                                                              -0.63, -0.49, -0.35, -0.07}


def test_2_0_0_ningun_camino_usa_una_arista_que_no_es_de_flujo():
    from core import scenario_engine as SE
    from core import semantic
    from ontology import vocabulary as vocab
    snap = semantic._load_snapshot()
    flow = set(vocab.flow_relation_types())
    pairs = {(l['source'], l['target']) for v in snap['out'].values() for l in v if (l.get('type') or 'supply') in flow}
    with _cf():
        for q in SCEN:
            a = SE.analyze(q, snap)
            assert a['engine']['method'].startswith('propagate@1'), q
            for x in a['impacts']:
                if x['channel'] in ('customer', 'second_order', 'supplier'):
                    ids = [i for i in _path_ids(x, snap)]
                    for u, v in zip(ids, ids[1:]):
                        assert (u, v) in pairs, (q, x['label'], u, v)


def _path_ids(x, snap):
    lab = {}
    for nid, n in snap['by_id'].items():
        lab.setdefault(n.get('label') or nid, nid)
    out = []
    for step in x['path'].split(' · '):
        for part in step.split(' → '):
            name = re.sub(r'\s*\(.*$', '', part).strip()
            if name in lab and (not out or out[-1] != lab[name]):
                out.append(lab[name])
    return out


def test_2_0_0_las_magnitudes_son_las_del_kernel():
    from core import scenario_engine as SE
    from core import semantic
    from core.hotviews import hot
    from core.hotviews.views import impact as IV
    snap = semantic._load_snapshot()
    with _cf():
        a = SE.analyze('Taiwan blockade', snap)
        core = hot.graph().core
        x0 = np.zeros(len(core.ids))
        for h in a['hit']:
            x0[core.idx[h]] = 1.0
        sc = IV.scenario(core, x0, factors='active', top=500)
    for x in a['impacts']:
        if x['channel'] in ('customer', 'second_order'):
            assert x['sev'] < 0 and abs(x['sev']) >= sc['impacts'][x['id']] / 100.0 - 6e-4, x   # (redondeo a 3 dec.)


def test_2_0_0_simulacion_por_agentes_toma_los_porcentajes_del_kernel(monkeypatch):
    from core import ai, sim_agents

    def fake(system, prompt, max_tokens=1000, tier='fast'):
        ids = re.findall(r'"id":\s*"([^"]+)"', prompt)
        return (json.dumps({'events': ['e'], 'narrative': 'n',
                            'impacts': [{'id': i, 'pct': -33.3, 'rationale': 'inventado'} for i in ids[:6]]}), 'mock')
    monkeypatch.setattr(ai, '_ai_complete', fake)
    monkeypatch.setattr(ai, '_ai_configured', lambda: True)
    with _cf():
        res = sim_agents.run('Taiwan blockade', ['TSMC'], 'es')
        from core import scenario_engine as SE
        from core import semantic
        snap = semantic._load_snapshot()
        a = SE.analyze('Taiwan blockade', snap, named_ids=['TSMC'])
        cast = sim_agents._cast_from_analysis(a, snap)
        want = sim_agents.kernel_pcts(a, cast)
    assert res['pct_source'] == 'kernel' and res['ai_pct_overridden'] > 0
    got = {i['id']: i['pct'] for i in res['impacts']}
    assert got == want and -33.3 not in got.values()


def test_1_0_0_la_simulacion_por_agentes_sigue_igual(monkeypatch):
    from core import ai, sim_agents

    def fake(system, prompt, max_tokens=1000, tier='fast'):
        ids = re.findall(r'"id":\s*"([^"]+)"', prompt)
        return (json.dumps({'events': ['e'], 'narrative': 'n',
                            'impacts': [{'id': ids[0], 'pct': -3.3, 'rationale': 'r'}]}), 'mock')
    monkeypatch.setattr(ai, '_ai_complete', fake)
    monkeypatch.setattr(ai, '_ai_configured', lambda: True)
    res = sim_agents.run('Taiwan blockade', ['TSMC'], 'es')
    assert 'pct_source' not in res and [i['pct'] for i in res['impacts']] == [-3.3]
