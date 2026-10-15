"""tests/test_import_sanitize_schema.py — lote L (2026-10-15): el esquema de la ficha khipus.company/1 versión 2.0.0
(artefacto ontology.import_schema@2.0.0) solo AFLOJA formato: el espejo Pydantic sigue siendo EQUIVALENTE al JSON Schema
del repositorio; los 13 negativos de 1.0.0 (y los campos EN VIVO) se siguen rechazando; lo que la investigación real
necesitaba (fundada en 1867, semestres, value_en en sanciones, % opcional, confianza opcional en ESG/línea de tiempo,
owns/partner/invest sin dependency, id_hint) ahora valida; un vínculo de FLUJO sin criticidad sigue rechazado; la
política policy.import@1.1.0 solo AGREGA claves y el código la lee."""
import copy
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('KHIPU_SCHEDULER', 'off')

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
EVID = [{'source_url': 'https://www.sec.gov/y', 'as_of': '2025', 'source_kind': 'press', 'quote': 'q'}]
REL = {'relation_id': 'rel-001', 'counterparty': {'name': 'Apple', 'khipus_id': 'Apple'}, 'rel_type': 'supply',
       'this_role': 'supplier', 'label_es': 'provee chips', 'label_en': 'supplies chips', 'status': 'active',
       'dependency': {'criticality': 3}, 'confidence': 0.7, 'evidence': EVID}


def _ok(mut):
    d = copy.deepcopy(BASE)
    mut(d)
    m, errs = CS.validate_record(d)
    return m is not None, errs


# ── equivalencia y gobernanza ────────────────────────────────────────────────────────────────────────────────────
def test_pydantic_equivale_al_json_schema_2_0_0():
    art = CS.load_artifact_schema()
    assert art['$id'] == 'urn:khipus:schema:company:2.0.0' and CS.SCHEMA_VERSION == '2.0.0'
    assert CS.canonical_shape(art) == CS.canonical_shape(CS.json_schema())


def test_artefacto_2_0_0_es_el_archivo_y_1_0_0_sigue_intacto():
    from core import governance as G
    docs = G.scan_repo()
    a2 = docs[('ontology.import_schema', '2.0.0')]
    assert a2['params']['schema'] == CS.load_artifact_schema()
    assert a2['change_kind'] == 'major' and a2['parent'] == 'ontology.import_schema@1.0.0'
    assert a2.get('activation') != 'pin'                      # describe el importador, no el kernel: vigente ya
    assert a2['params']['schema_id'] == 'khipus.company/1'     # el FORMATO de la ficha no cambia de nombre
    a1 = docs[('ontology.import_schema', '1.0.0')]
    assert a1['params']['schema']['$id'] == 'urn:khipus:schema:company:1.0.0'   # el registro solo crece
    man = G.load_manifest()
    assert man['release']['artifacts']['ontology.import_schema']['semver'] == '2.0.0'
    assert man['release']['artifacts']['policy.import']['semver'] == '1.1.0'


def test_policy_import_1_1_0_solo_agrega_y_el_codigo_la_lee():
    from core import governance as G
    from core import governance_lint as GL
    from ontology import company_import as CI
    docs = G.scan_repo()
    old, new = docs[('policy.import', '1.0.0')]['params'], docs[('policy.import', '1.1.0')]['params']
    assert GL.diff_kind(old, new) == 'add'
    assert {k: new[k] for k in old} == old                     # los números de hoy no cambian
    assert new == CI.POLICY_DEFAULTS == G.section('policy.import')
    assert CI.policy('owns_default_criticality') == {'pct_ge_90': 5, 'pct_ge_50': 4, 'pct_lt_50': 3, 'pct_unknown': 3}
    assert CI.policy('owns_default_live_min_pct') == 50 and CI.policy('nonflow_default_weight') == 1


def test_build_governance_y_formas_limpias():
    from scripts import build_governance as B
    assert B.check(verbose=False) == []


# ── lo de 1.0.0 que sigue prohibido ─────────────────────────────────────────────────────────────────────────────
NEGATIVOS_1_0_0 = [
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


@pytest.mark.parametrize('name,mut', NEGATIVOS_1_0_0, ids=[n for n, _m in NEGATIVOS_1_0_0])
def test_los_13_negativos_de_1_0_0_siguen_rechazados(name, mut):
    ok, errs = _ok(mut)
    assert not ok and errs and all(e['msg_es'] and e['msg_en'] for e in errs), name


NEGATIVOS_2_0_0 = [
    ('flujo sin dependency', lambda d: d.__setitem__('relations', [{k: v for k, v in REL.items() if k != 'dependency'}])),
    ('flujo con dependency sin criticidad', lambda d: d.__setitem__('relations', [dict(REL, dependency={'sole_source': True})])),
    ('año 999', lambda d: d['identity'].__setitem__('founded', {'value': '0999', **F})),
    ('año 2100', lambda d: d['identity'].__setitem__('founded', {'value': '2100', **F})),
    ('URL con espacio', lambda d: d['profile']['summary'].__setitem__('source_url', 'https://ex.com/a b.pdf')),
    ('ticker con espacio', lambda d: d['identity'].__setitem__('ids', {'ticker': 'ERIC B'})),
    ('khipus_id con guion', lambda d: d.__setitem__('relations', [dict(REL, counterparty={'name': 'LM', 'khipus_id': 'lockheed-martin'})])),
    ('semestre H3', lambda d: d.__setitem__('financials', {'quarterly': [{'period': '2025-H3'}]})),
    ('FY partido sin normalizar', lambda d: d.__setitem__('financials', {'annual': [{'fiscal_year': 2026, 'revenue': {
        'value': 1, 'currency': 'CHF', 'period': 'FY2025/26', **F}}]})),
    ('año fiscal como texto', lambda d: d.__setitem__('financials', {'annual': [{'fiscal_year': '2025'}]})),
    ('cotización sin símbolo de Yahoo', lambda d: d.__setitem__('listings', [{'ticker': 'KAP', 'exchange_mic': 'AIXK',
                                                                             'currency': 'USD', 'kind': 'equity',
                                                                             'is_primary': True, 'source_url': 'https://ex.com/l',
                                                                             'as_of': '2026'}])),
    ('confianza obligatoria fuera de ESG', lambda d: d['identity']['hq_country'].pop('confidence')),
    ('value_en fuera de exposure', lambda d: d['identity']['legal_name'].__setitem__('value_en', 'Test Co')),
]


@pytest.mark.parametrize('name,mut', NEGATIVOS_2_0_0, ids=[n for n, _m in NEGATIVOS_2_0_0])
def test_lo_que_2_0_0_sigue_rechazando(name, mut):
    ok, errs = _ok(mut)
    assert not ok and errs, name


# ── lo que 2.0.0 acepta (datos reales del lote) ──────────────────────────────────────────────────────────────────
OWNS = dict(REL, relation_id='rel-002', rel_type='owns', this_role='owned', counterparty={'name': 'HD Hyundai Co., Ltd.'})
POSITIVOS = [
    ('fundada en 1867', lambda d: d['identity'].__setitem__('founded', {'value': '1867', **F})),
    ('línea de tiempo 1868 sin confianza', lambda d: d.__setitem__('timeline', [{
        'date': '1868', 'kind': 'founded', 'text_es': 'fundada', 'text_en': 'founded', 'source_url': 'https://ex.com/t',
        'as_of': '1889'}])),
    ('ESG sin confianza', lambda d: d.__setitem__('esg', {'emissions_scope1_tco2e': {
        'value': 1200.5, 'unit': 'tCO2e', 'source_url': 'https://ex.com/e', 'as_of': '2025'},
        'renewable_share_pct': {'value': 40, 'source_url': 'https://ex.com/e', 'as_of': '2025'}})),
    ('semestre 2025-H1', lambda d: d.__setitem__('financials', {'quarterly': [{'period': '2025-H1', 'revenue': {
        'value': 5, 'currency': 'KRW', 'period': '2025-H1', **F}}]})),
    ('sanciones bilingües', lambda d: d.__setitem__('exposure', {'sanctions': {'value': 'Sancionada por OFAC', 'value_en':
                                                                             'Sanctioned by OFAC', **F}})),
    ('controles de exportación bilingües', lambda d: d.__setitem__('exposure', {'export_controls': {
        'value': 'Restricciones de 2022', 'value_en': 'Export restrictions (2022)', **F}})),
    ('filial sin %', lambda d: d.__setitem__('corporate', {'subsidiaries': [{'entity': {'name': 'Hitachi Energy', 'country': 'CH'}}],
                                                          'parent': {'entity': {'name': 'Holding'}}})),
    ('owns sin dependency', lambda d: d.__setitem__('relations', [{k: v for k, v in OWNS.items() if k != 'dependency'}])),
    ('invest con dependency sin criticidad', lambda d: d.__setitem__('relations', [dict(
        REL, rel_type='invest', this_role='investor', dependency={'contract_value': {'value': 3e10, 'currency': 'JPY', **F}})])),
    ('partner sin dependency', lambda d: d.__setitem__('relations', [dict(
        {k: v for k, v in REL.items() if k != 'dependency'}, rel_type='partner', this_role='partner')])),
    ("other_names kind 'other'", lambda d: d['identity'].__setitem__('other_names', [{'name': 'Toyota Motor', 'kind': 'other'}])),
    ('id_hint con guion y espacio', lambda d: d.__setitem__('relations', [dict(
        REL, counterparty={'name': 'Lockheed Martin', 'id_hint': 'lockheed-martin'}), dict(
        REL, relation_id='rel-009', counterparty={'name': 'CBRE', 'id_hint': 'CBRE Group'})])),
    ('textos largos reales', lambda d: (d.__setitem__('listings', [{
        'ticker': 'TRTN-PA', 'exchange_mic': 'XNYS', 'yahoo_symbol': 'TRTN-PA', 'currency': 'USD', 'kind': 'preferred',
        'is_primary': False, 'share_class': 'Series A cumulative redeemable perpetual preference shares',
        'source_url': 'https://ex.com/l', 'as_of': '2026'}]), d['research_meta'].__setitem__('not_found', ['x' * 250]),
        d.__setitem__('facilities', [{'name': 'Planta', 'kind': 'other', 'country': 'MY', 'source_url': 'https://ex.com/f',
                                      'as_of': '2026', 'capacity': {'value': 1.2e9, 'unit': 'u' * 67}}]))),
    ('lista restringida sin fecha y litigio sin estado', lambda d: d.__setitem__('regulatory', {
        'restricted_lists': [{'list': 'BIS_entity_list', 'source_url': 'https://ex.com/r', 'as_of': '2025', 'confidence': 0.8}],
        'litigation': [{'kind': 'patent', 'text_es': 'demanda', 'text_en': 'lawsuit', 'source_url': 'https://ex.com/l',
                        'as_of': '2025'}]})),
    ('ticker con guion', lambda d: d['identity'].__setitem__('ids', {'ticker': 'ERIC-B', 'yahoo_symbol': 'ERIC-B.ST'})),
]


@pytest.mark.parametrize('name,mut', POSITIVOS, ids=[n for n, _m in POSITIVOS])
def test_lo_que_la_investigacion_real_necesitaba_ahora_valida(name, mut):
    ok, errs = _ok(mut)
    assert ok, (name, errs[:3])


def test_toda_ficha_de_1_0_0_sigue_valida():
    """2.0.0 es un SUPERCONJUNTO: el ejemplo mínimo y la relación completa de las pruebas de 1.0.0 siguen valiendo."""
    ok, errs = _ok(lambda d: d.__setitem__('relations', [dict(REL, start='2021-07', dependency={
        'criticality': 5, 'tier': 2, 'component': 'HBM3E', 'bom_share_pct': {'value': 12, **F},
        'supplier_facility': {'name': 'Hsinchu', 'country': 'TW', 'share_of_flow_pct': 100}, 'alternatives': ['Samsung']})]))
    assert ok, errs
    with open(os.path.join(ROOT, 'data', 'import', 'company.schema.json'), encoding='utf-8') as fh:
        s = json.load(fh)
    assert s['properties']['schema'] == {'const': 'khipus.company/1'}
