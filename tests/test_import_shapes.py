"""tests/test_import_shapes.py — EXPANSION_5K E2.5: la puerta G-IMPORT (governance/shapes/company.ttl) en SOMBRA.

  · el IR compilado y el artefacto ontology.shapes@7.0.0 traen las 14 reglas khr:import.*;
  · el evaluador compilado (core/gates/engine) sobre `company_import.import_triples` marca lo esperado (un defecto
    por regla) y nada en un ítem limpio;
  · con pySHACL (requirements-dev.txt; fuera de CI se salta): ≥ 1.000 focos aleatorios → 0 diferencias en
    (foco, regla, severidad) y en `conforms` entre el evaluador compilado y pySHACL sobre company.ttl;
  · la puerta nunca BLOQUEA (no está en policy.gates.block_gates): modo sombra.
"""
import os
import random
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('KHIPU_SCHEDULER', 'off')

IN_CI = (os.getenv('CI') or os.getenv('GITHUB_ACTIONS') or '').lower() in ('1', 'true', 'yes')
try:
    import pyshacl  # noqa: F401
    import rdflib  # noqa: F401
    HAVE = True
except ImportError:
    HAVE = False

IMPORT_RULES = {'khr:import.schema_valid', 'khr:import.hq_country_iso2', 'khr:import.hq_country_known', 'khr:import.cat_known',
                'khr:import.summary_bilingual', 'khr:import.one_primary_listing', 'khr:import.unverified_confidence',
                'khr:import.possible_duplicate', 'khr:import.no_live_fields', 'khr:import.route_in_vocab',
                'khr:import.criticality_range', 'khr:import.live_needs_trust', 'khr:import.counterparty_resolved',
                'khr:import.owns_share_min'}


def _ir():
    from core.gates import engine
    return engine.read_ir_file()


def test_ir_y_artefacto_traen_las_reglas_de_importacion():
    from core import governance
    ir = _ir()
    assert IMPORT_RULES <= set(ir['rules'])
    art = governance.repo_bundle().artifacts['ontology.shapes']
    assert art['semver'] >= '7.0.0' and IMPORT_RULES <= set(art['params']['ir']['rules'])
    assert art['params']['ir_hash'] == ir['ir_hash']


def _clean_item():
    return {'record_id': 'r-1', 'name': 'X', 'action': 'create', 'id': 'X', 'method': 'new', 'score': 0, 'conflicts': [],
            'warnings': [], 'props': {'hq_country': 'KR', 'verified': True, 'listings': [{'is_primary': True}],
                                      'research_meta': {'confidence': 0.7}},
            'links': [{'relation_id': 'rel-1', 'rel_type': 'supply', 'route': 'live', 'confidence': 0.8,
                       'properties': {'verified': True, 'dependency': {'criticality': 3}}},
                      {'relation_id': 'h-1', 'rel_type': 'owns', 'route': 'live', 'confidence': 0.9,
                       'properties': {'verified': True, 'share_pct': 60}}]}


def _run(item):
    from core.gates import engine
    from ontology import company_import as CI
    comp = engine.load(force=True)
    assert comp is not None, engine.state()
    triples, _f = CI.import_triples(item)
    return {s['rule'] for _t, _k, s, _v, _l in engine.run(comp, triples)}


DEFECTOS = [
    ('khr:import.schema_valid', lambda it: it.__setitem__('schema_valid', False)),
    ('khr:import.hq_country_iso2', lambda it: it['props'].__setitem__('hq_country', 'EEUU')),
    ('khr:import.hq_country_known', lambda it: it['warnings'].append({'code': 'hq_unknown'}) or it['props'].pop('hq_country')),
    ('khr:import.cat_known', lambda it: it['warnings'].append({'code': 'cat_unknown'})),
    ('khr:import.summary_bilingual', lambda it: it['warnings'].append({'code': 'en_missing'})),
    ('khr:import.one_primary_listing', lambda it: it['props'].__setitem__('listings', [{'is_primary': True}, {'is_primary': True}])),
    ('khr:import.unverified_confidence', lambda it: it['props'].update(verified=False, research_meta={'confidence': 0.9})),
    ('khr:import.possible_duplicate', lambda it: it['conflicts'].append({'kind': 'possible_duplicate', 'id': 'Y', 'score': 70})),
    ('khr:import.no_live_fields', lambda it: it['props'].__setitem__('price', 10)),
    ('khr:import.criticality_range', lambda it: it['links'][0]['properties']['dependency'].__setitem__('criticality', 7)),
    ('khr:import.live_needs_trust', lambda it: it['links'][0]['properties'].__setitem__('verified', False)),
    ('khr:import.counterparty_resolved', lambda it: it['links'][0].__setitem__('route', 'pending')),
    ('khr:import.owns_share_min', lambda it: it['links'][1]['properties'].__setitem__('share_pct', 30)),
    ('khr:import.route_in_vocab', lambda it: it['links'][0].__setitem__('route', 'volando')),
]


def test_item_limpio_no_marca_nada():
    assert _run(_clean_item()) == set()


@pytest.mark.parametrize('rule,mut', DEFECTOS, ids=[r for r, _m in DEFECTOS])
def test_un_defecto_por_regla(rule, mut):
    it = _clean_item()
    mut(it)
    got = _run(it)
    assert got == {rule}, (rule, got)                      # exactamente ESA regla y ninguna otra


def test_las_14_reglas_tienen_su_defecto():
    assert {r for r, _m in DEFECTOS} == IMPORT_RULES


def import_single_defect_cases():
    """[(regla | None, 'import', ítem)] para tests/gates_cases.single_defect_cases (conformidad pySHACL de TODAS las
    reglas): un ítem limpio + un defecto por regla. Se arma el foco con company_import.import_triples(ítem)."""
    out = [(None, 'import', _clean_item())]
    for rule, mut in DEFECTOS:
        it = _clean_item()
        mut(it)
        out.append((rule, 'import', it))
    return out


def test_la_puerta_de_importacion_nunca_bloquea():
    import core.gates as G
    assert 'ontology.g_import' not in G.BLOCKABLE
    assert G.mode_for('ontology.g_import') in ('shadow', 'off')


def test_gate_plan_en_sombra_devuelve_reporte_sin_lanzar():
    from ontology import company_import as CI
    it = _clean_item()
    it['warnings'].append({'code': 'en_missing'})
    rep = CI.gate_plan([it], session=None)
    if rep is None:          # puertas apagadas (KHIPU_GATES=off)
        pytest.skip('puertas apagadas')
    assert rep['mode'] in ('shadow', 'block') and rep['outcome'] in ('pass', 'warn', 'info', 'requires_approval', 'block')
    assert rep['by_rule'].get('khr:import.summary_bilingual') == 1


# ── conformidad con pySHACL ──────────────────────────────────────────────────────────────────────────────────────
def _random_item(rng, n):
    routes = ['live', 'proposed', 'pending', 'quarantine', 'raro']
    it = {'record_id': f'c{n}', 'name': 'X', 'action': rng.choice(['create', 'merge']), 'id': f'c{n}', 'method': 'new',
          'score': 0, 'conflicts': [], 'warnings': [], 'links': [],
          'props': {'hq_country': rng.choice(['KR', 'US', 'ZZ', 'EEUU', None]), 'verified': rng.choice([True, False, None]),
                    'listings': [{'is_primary': rng.random() < 0.6} for _ in range(rng.randint(0, 3))],
                    'research_meta': {'confidence': rng.choice([0.2, 0.4, 0.7, 0.95, None])}}}
    if it['props']['hq_country'] in ('ZZ', None):
        it['warnings'].append({'code': 'hq_unknown'})
    for code in ('cat_unknown', 'en_missing'):
        if rng.random() < 0.4:
            it['warnings'].append({'code': code})
    if rng.random() < 0.3:
        it['conflicts'].append({'kind': 'possible_duplicate', 'id': 'Y', 'score': 70})
    if rng.random() < 0.2:
        it['props'][rng.choice(['price', 'market_cap', 'nrs'])] = 1
    for k in range(rng.randint(0, 3)):
        rel = rng.choice(['supply', 'owns', 'invest', 'partner'])
        props = {'verified': rng.choice([True, False]), 'dependency': {'criticality': rng.choice([1, 3, 6, 7, 0])}}
        if rel == 'owns':
            props['share_pct'] = rng.choice([10, 50, 80, None])
        it['links'].append({'relation_id': f'rel-{k}', 'rel_type': rel, 'route': rng.choice(routes),
                            'confidence': rng.choice([0.1, 0.5, 0.9]), 'properties': props})
    return it


@pytest.mark.skipif(not HAVE, reason='pyshacl/rdflib no instalados (requirements-dev.txt)')
def test_conformidad_pyshacl_1000_focos():
    import pyshacl
    from rdflib import RDF, Graph, URIRef
    from rdflib.namespace import SH

    from core.gates import engine
    from core.gates import focus as F
    from ontology import company_import as CI
    from scripts import build_shapes as BS
    sg = Graph()
    for name in tuple(BS.SOURCES) + (('company.ttl',) if 'company.ttl' not in BS.SOURCES else ()):
        sg.parse(os.path.join(BS.SHAPES_DIR, name), format='turtle')
    comp = engine.load(force=True)
    assert comp is not None
    rule_p = URIRef(F.KHS + 'rule')
    rng = random.Random(int(comp.ir_hash[:8], 16))
    n_total = int(os.getenv('GATES_CONFORMANCE_N') or 1000)
    diffs = 0
    for start in range(0, n_total, 25):
        triples = []
        for n in range(start, min(start + 25, n_total)):
            t, _f = CI.import_triples(_random_item(rng, n))
            triples += t
        mine = {(str(t), s['rule'], F.expand(s['severity'])) for t, _k, s, _v, _l in engine.run(comp, triples)
                if s['rule'] in IMPORT_RULES}
        g = F.to_rdflib(triples)
        conforms, rg, _ = pyshacl.validate(g, shacl_graph=sg, inference='none', inplace=True, allow_warnings=False,
                                           abort_on_first=False)
        theirs = set()
        for r in rg.subjects(RDF.type, SH.ValidationResult):
            ss = rg.value(r, SH.sourceShape)
            rule = sg.value(ss, rule_p)
            rule_c = F.compact(rule) if rule is not None else F.compact(ss)
            if rule_c in IMPORT_RULES:
                theirs.add((str(rg.value(r, SH.focusNode)), rule_c, str(rg.value(r, SH.resultSeverity))))
        if mine != theirs:
            diffs += len(mine ^ theirs)
        assert conforms == (not theirs)
    assert diffs == 0
