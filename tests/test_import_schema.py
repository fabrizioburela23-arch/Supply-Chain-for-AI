"""tests/test_import_schema.py — EXPANSION_5K E2.1: el espejo Pydantic (ontology/company_schema) ≡ el artefacto
`ontology.import_schema` (= data/import/company.schema.json) en forma normalizada; los 13 negativos del plan se
rechazan; un margen de -250 % se acepta; nulos explícitos y repetidos se rechazan como en JSON Schema."""
import copy
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ontology import company_schema as CS  # noqa: E402

F = {'source_url': 'https://www.sec.gov/x', 'source_kind': 'primary', 'as_of': '2025-06', 'confidence': 0.9}
BASE = {
    'schema': 'khipus.company/1', 'record_id': 't-001',
    'research_meta': {'researcher': 'x', 'researched_at': '2026-10-14T10:00:00Z', 'method': 'manual', 'tier': 'A'},
    'identity': {'legal_name': {'value': 'Test Co', **F}, 'short_name': 'Test', 'status': {'value': 'public', **F},
                 'hq_country': {'value': 'US', **F}},
    'classification': {'cat': 'foundry', 'chain_layers': ['power', 'cloud']},
    'profile': {'summary': {'value': 'Empresa de prueba larga', 'value_en': 'Test company long enough', **F}},
}
REL = {'relation_id': 'rel-001', 'counterparty': {'name': 'Apple', 'khipus_id': 'Apple'}, 'rel_type': 'supply',
       'this_role': 'supplier', 'label_es': 'provee chips', 'label_en': 'supplies chips', 'status': 'active',
       'dependency': {'criticality': 3}, 'confidence': 0.7,
       'evidence': [{'source_url': 'https://www.sec.gov/y', 'as_of': '2025', 'source_kind': 'press', 'quote': 'q'}]}


def _ok(d):
    m, errs = CS.validate_record(d)
    return m is not None, errs


def _neg(mut):
    d = copy.deepcopy(BASE)
    mut(d)
    ok, errs = _ok(d)
    return ok, errs


def test_artefacto_es_el_schema_del_repositorio():
    from core import governance as G
    art = G.scan_repo()[('ontology.import_schema', '2.0.0')]
    assert art['params']['schema'] == CS.load_artifact_schema()
    assert art['params']['schema_id'] == 'khipus.company/1'
    assert 'ontology.import_schema' in G.load_manifest()['release']['artifacts']


def test_pydantic_equivale_al_artefacto_en_forma_normalizada():
    a = CS.canonical_shape(CS.load_artifact_schema())
    b = CS.canonical_shape(CS.json_schema())
    assert a == b


def test_ficha_minima_valida_y_ejemplo_catl_es_plantilla():
    ok, errs = _ok(BASE)
    assert ok, errs
    with open(os.path.join(ROOT, 'data', 'import', 'ejemplo_CATL.json'), encoding='utf-8') as fh:
        ok2, errs2 = _ok(json.load(fh))
    assert not ok2 and errs2           # un ejemplo con <marcadores> no es una ficha


NEGATIVOS = [
    ('price', lambda d: d.__setitem__('price', 123.4)),
    ('market_cap', lambda d: d['identity'].__setitem__('market_cap', {'value': 1, **F})),
    ('shares_outstanding', lambda d: d['profile'].__setitem__('shares_outstanding', {'value': 10, **F})),
    ('criticidad 7', lambda d: d.__setitem__('relations', [dict(REL, dependency={'criticality': 7})])),
    ('this_role incoherente', lambda d: d.__setitem__('relations', [dict(REL, this_role='investor')])),
    ('sin fuente', lambda d: d['profile']['summary'].pop('source_url')),
    ('sin fecha', lambda d: d['profile']['summary'].pop('as_of')),
    ('sin inglés', lambda d: d['profile']['summary'].pop('value_en')),
    ('participación 150 %', lambda d: d.__setitem__('corporate', {'parent': {'entity': {'name': 'Holding'},
                                                                              'pct': {'value': 150, **F}}})),
    ('puesto sin rango ni cuota', lambda d: d.__setitem__('market_position', [{'market': 'baterías', 'metric': 'revenue',
                                                                               'region': 'GLOBAL', **F}])),
    ('capacidad sin unidad', lambda d: d.__setitem__('facilities', [{'name': 'Planta', 'kind': 'cell_plant', 'country': 'KR',
                                                                     'status': 'operating', 'capacity': {'value': 10},
                                                                     'source_url': 'https://ex.com/p', 'as_of': '2025'}])),
    ('ended sin end', lambda d: d.__setitem__('relations', [dict(REL, status='ended')])),
    ('país no ISO', lambda d: d['identity']['hq_country'].__setitem__('value', 'EEUU')),
]


@pytest.mark.parametrize('name,mut', NEGATIVOS, ids=[n for n, _m in NEGATIVOS])
def test_los_13_negativos_se_rechazan(name, mut):
    ok, errs = _neg(mut)
    assert not ok and errs, name
    assert all(e['msg_es'] and e['msg_en'] for e in errs)


def test_campo_en_vivo_dice_que_lo_trae_el_servidor():
    ok, errs = _neg(lambda d: d.__setitem__('nrs', 50))
    assert not ok and 'EN VIVO' in errs[0]['msg_es']


def test_margen_muy_negativo_se_acepta_y_mas_de_100_no():
    ok, errs = _neg(lambda d: d.__setitem__('financials', {'annual': [{'fiscal_year': 2025, 'gross_margin_pct': {'value': -250, **F}}]}))
    assert ok, errs
    ok2, _ = _neg(lambda d: d.__setitem__('financials', {'annual': [{'fiscal_year': 2025, 'gross_margin_pct': {'value': 101, **F}}]}))
    assert not ok2


def test_json_estricto_nulos_y_repetidos():
    ok, _ = _neg(lambda d: d['identity']['hq_country'].__setitem__('value', None))
    assert not ok                                              # null no es "ausente"
    ok, _ = _neg(lambda d: d['research_meta'].__setitem__('researched_at', 123))
    assert not ok
    ok, _ = _neg(lambda d: d['classification'].__setitem__('chain_layers', ['power', 'power']))
    assert not ok                                              # uniqueItems
    ok, _ = _neg(lambda d: d['profile'].__setitem__('employees', {'value': 3.5, **F}))
    assert not ok                                              # integer


def test_relacion_valida_con_planta_y_pieza():
    rel = dict(REL, start='2021-07', dependency={'criticality': 5, 'tier': 2, 'component': 'HBM3E', 'bom_share_pct': {'value': 12, **F},
                                                 'supplier_facility': {'name': 'Hsinchu', 'country': 'TW', 'share_of_flow_pct': 100},
                                                 'alternatives': ['Samsung']})
    ok, errs = _neg(lambda d: d.__setitem__('relations', [rel]))
    assert ok, errs
    ok2, _ = _neg(lambda d: d.__setitem__('relations', [dict(rel, dependency={'criticality': 5, 'supplier_facility': {'name': 'Hsinchu'}})]))
    assert not ok2                                             # planta sin país ni facility_id
