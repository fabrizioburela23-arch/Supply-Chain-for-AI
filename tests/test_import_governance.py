"""tests/test_import_governance.py — EXPANSION_5K E2.5: los artefactos del importador están en el registro de gobernanza
(policy.import@1.1.0, ontology.import_schema@2.0.0 —lote L—, ledger.kinds@5.0.0 con ontology.import_rollback, ontology.shapes@7.0.0)
y el código lee la política de ahí; nada cambia números del kernel (los dorados siguen iguales)."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('KHIPU_SCHEDULER', 'off')


def test_manifest_al_dia_con_los_artefactos_nuevos():
    from scripts import build_governance as B
    assert B.check(verbose=False) == []
    with open(os.path.join(ROOT, 'governance', 'manifest.json'), encoding='utf-8') as fh:
        man = json.load(fh)
    arts = man['release']['artifacts']
    assert arts['policy.import']['semver'] == '1.1.0'
    assert arts['ontology.import_schema']['semver'] == '2.0.0'
    assert arts['ledger.kinds']['semver'] >= '5.0.0'
    assert arts['ontology.shapes']['semver'] >= '7.0.0'
    for a in man['available']:
        if a['id'] in ('policy.import', 'ontology.import_schema'):
            assert a.get('activation') != 'pin'      # vigentes desde ya: solo describen el importador, no el kernel
    assert arts['kernel.params']['semver'] == '1.0.0'  # el kernel no se toca


def test_ledger_kinds_incluye_import_rollback_y_alguien_lo_escribe():
    from core import decisions
    assert 'ontology.import_rollback' in decisions.KINDS and 'ontology.bulk_import' in decisions.KINDS
    with open(os.path.join(ROOT, 'ontology', 'company_import.py'), encoding='utf-8') as fh:
        src = fh.read()
    assert "'ontology.import_rollback'" in src and "'ontology.bulk_import'" in src


def test_policy_import_es_la_de_hoy_y_el_codigo_la_lee():
    from core import governance
    from ontology import company_import as CI
    p = governance.section('policy.import')
    assert p == CI.POLICY_DEFAULTS
    assert CI.policy('live_min_confidence') == 0.5 and CI.policy('live_min_trust') == 2 and CI.policy('owns_min_pct') == 50
    assert CI.policy('unverified_confidence') == 0.4 and CI.policy('block_size') == 250
    assert CI.policy('upload_chunk_max_bytes') <= 1024 * 1024 - 100 * 1024   # cabe en MAX_CONTENT_LENGTH (1 MB)


def test_import_schema_artefacto_igual_al_archivo():
    from core import governance
    with open(os.path.join(ROOT, 'data', 'import', 'company.schema.json'), encoding='utf-8') as fh:
        schema = json.load(fh)
    art = governance.repo_bundle().artifacts['ontology.import_schema']['params']
    assert art['schema'] == schema and art['schema_file'] == 'data/import/company.schema.json'


def test_los_dorados_del_kernel_no_cambian():
    from scripts import build_impl_goldens as BG
    assert BG.main(check=True) == 0
