"""tests/test_ontology_alerts.py — Fase 4: alertas de precio/NRS/noticias.
Requiere Postgres real (DATABASE_URL)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv('DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres) configurada')


@pytest.fixture(scope='module')
def db():
    from ontology.db import init_schema, _get_engine, session_scope
    from ontology.models import Base
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    init_schema()
    with session_scope() as s:
        apply_event(s, 'ObjectCreated', {
            'label': 'AlertCo', 'type': 'Company', 'properties': {'mkt': 'ALRT', 'nrs_override': 82},
        }, valid_from='2000-01-01', source='test', actor='pytest', object_id='AlertCo')
    yield
    Base.metadata.drop_all(engine)


def test_evaluate_nrs_alert_fires(db):
    from ontology.db import session_scope
    from ontology.agents import evaluate_alert

    with session_scope() as s:
        fired, value, detail = evaluate_alert(s, {'entity': 'AlertCo', 'metric': 'nrs', 'op': '>', 'value': 70})
        assert fired is True
        assert value == 82


def test_evaluate_nrs_alert_does_not_fire_below_threshold(db):
    from ontology.db import session_scope
    from ontology.agents import evaluate_alert

    with session_scope() as s:
        fired, value, detail = evaluate_alert(s, {'entity': 'AlertCo', 'metric': 'nrs', 'op': '>', 'value': 95})
        assert fired is False


def test_evaluate_price_alert_without_finnhub_key_does_not_crash(db):
    from ontology.db import session_scope
    from ontology.agents import evaluate_alert
    os.environ['FINNHUB_KEY'] = ''

    with session_scope() as s:
        fired, value, detail = evaluate_alert(s, {'entity': 'AlertCo', 'metric': 'price', 'op': '>', 'value': 100})
        assert fired is False
        assert value is None


def test_create_and_check_alert_via_api(db):
    import server
    os.environ.setdefault('SECRET_KEY', 'test')
    server.app.config['TESTING'] = True
    c = server.app.test_client()

    r = c.post('/api/ontology/alerts', json={'owner': 'fabrizio',
                                              'rule': {'entity': 'AlertCo', 'metric': 'nrs', 'op': '>', 'value': 50}})
    assert r.status_code == 200
    alert_id = r.get_json()['alert']['id']

    r2 = c.get('/api/ontology/alerts/check?owner=fabrizio')
    assert r2.status_code == 200
    fired = r2.get_json()['fired']
    assert any(f['id'] == alert_id for f in fired)

    r3 = c.get('/api/ontology/alerts?owner=fabrizio')
    assert r3.get_json()['count'] >= 1

    r4 = c.delete(f'/api/ontology/alerts/{alert_id}')
    assert r4.status_code == 200

    r5 = c.get('/api/ontology/alerts?owner=fabrizio')
    assert all(a['id'] != alert_id for a in r5.get_json()['alerts'])


def test_create_alert_rejects_invalid_metric(db):
    import server
    c = server.app.test_client()
    r = c.post('/api/ontology/alerts', json={'owner': 'x', 'rule': {'metric': 'banana', 'value': 1}})
    assert r.status_code == 400
