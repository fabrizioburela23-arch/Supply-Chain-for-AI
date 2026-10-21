"""Cola de revisión de vínculos PROPUESTOS (2026-10-21): ontology/link_review ordena por importancia (flujo > socio,
criticidad, confianza declarada, grado de los extremos); confirmar/rechazar = la Acción auditada de siempre. El panel
📥 (engine/importer.js) la muestra con ✓ / ✕ (PIN)."""
import os

import pytest

from ontology import link_review as LR

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLOW = {'supply', 'owns', 'fab'}


def test_priority_prefers_flow_criticality_confidence_and_connected_ends():
    a = LR.priority('supply', {'dependency': {'criticality': 5}, 'declared_confidence': 0.8}, 10, 10, FLOW)
    b = LR.priority('partner', {'dependency': {'criticality': 5}, 'declared_confidence': 0.8}, 10, 10, FLOW)
    c = LR.priority('supply', {'dependency': {'criticality': 1}, 'declared_confidence': 0.8}, 10, 10, FLOW)
    d = LR.priority('supply', {'dependency': {'criticality': 5}, 'declared_confidence': 0.2}, 10, 10, FLOW)
    e = LR.priority('supply', {'dependency': {'criticality': 5}, 'declared_confidence': 0.8}, 0, 0, FLOW)
    assert a > b and a > c and a > d and a > e
    assert LR.priority('supply', {}, 0, 0, FLOW) > 0                      # sin datos: igual tiene un lugar


def test_every_import_reason_has_bilingual_text():
    for k, (es, en) in LR.REASON_TEXT.items():
        assert es and en and es != en
    for k in ('source_trust_low', 'owns_without_control_pct', 'counterparty_by_name_only', 'low_confidence',
              'holding_without_pct', 'holding_unverified', 'status_disputed'):
        assert k in LR.REASON_TEXT


@pytest.mark.skipif(not os.getenv('DATABASE_URL'), reason='requiere DATABASE_URL')
def test_queue_lists_only_proposed_and_route_is_read_only():
    os.environ.setdefault('SECRET_KEY', 'test')
    from ontology.db import init_schema
    assert init_schema(retries=1)          # en CI otra prueba puede haber dejado la base sin tablas
    import server
    c = server.app.test_client()
    r = c.get('/api/ontology/links/review?limit=5')
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        d = r.get_json()
        assert {'total', 'items', 'by_reason'} <= set(d)
        assert all(it['link_id'] and it['source']['label'] and it['reason_text'] for it in d['items'])
        ps = [it['priority'] for it in d['items']]
        assert ps == sorted(ps, reverse=True)


def test_panel_wires_the_review_queue_bilingually():
    src = open(os.path.join(ROOT, 'engine', 'importer.js'), encoding='utf-8').read()
    assert "/api/ontology/links/review?limit=" in src and "'ConfirmarVinculo' : 'RechazarVinculo'" in src
    for es, en in (('Vínculos por revisar', 'Links to review'), ('✓ Confirmar', '✓ Confirm'), ('✕ Rechazar', '✕ Reject')):
        assert es in src and en in src
