"""tests/test_governance_activation.py — INFRA_OPERATIVA paso 12: activar kernel.params@2.0.0 con el PIN de Fabrizio
(pieza mínima del paso 25) y deshacerlo.

  · sin base: "¿qué cambia para mí?" (/api/governance/preview) es un contrafactual que NO toca el kernel vivo;
  · con base: POST /api/governance/activate exige PIN de persona → fila nueva en gov_releases (ratified=true) +
    decisión governance.activate de op:fabrizio; el release vigente cambia, las constantes y las vistas también;
  · deshacer = activar 1.0.0: el release del bootstrap se REACTIVA (otra decisión; ninguna fila se toca);
  · nada se activa solo: un deploy con kernel.params@2.0.0 en el repositorio deja 1.0.0 vigente.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
PIN = 'pin-activa-12345'


def test_preview_sin_base_no_toca_el_kernel_vivo(monkeypatch):
    import ontology.db as odb
    import server
    from core import governance, governance_preview
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    governance_preview.reset()
    c = server.app.test_client()
    r = c.get('/api/governance/preview?artifact=kernel.params&semver=2.0.0')
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    k = d['kernel']
    tsmc = next(x for x in k['reference'] if x['id'] == 'TSMC')
    assert tsmc['reach_before'] > tsmc['reach_after'] == 254
    assert k['shocks_changed'] > 0 and k['direction_up_before'] is False and k['direction_up_after'] is True
    assert k['rho_after'] < k['rho_before']
    assert [x['id'] for x in k['chokepoints_after'][:2]] == ['TSMC', 'Nvidia']
    assert d['nrs_affected'] is False and 'NRS' in d['summary_es'] and 'NRS' in d['summary_en']
    assert any(p['key'] == 'damage_rels' for p in d['params_diff']['kernel.params'])
    assert governance.artifact_semver('kernel.params') == '1.0.0'          # el vivo no cambió
    from matrix import engine as E
    assert E.direction_up_enabled() is False
    assert c.get('/api/governance/preview?artifact=kernel.params&semver=9.9.9').status_code == 404
    assert c.get('/api/governance/preview?artifact=kernel.params&semver=2.0.0').get_json()['cached'] is True


def test_sin_base_activar_responde_503(monkeypatch):
    import ontology.db as odb
    import server
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    r = server.app.test_client().post('/api/governance/activate', json={'artifact': 'kernel.params', 'semver': '2.0.0'})
    assert r.status_code == 503 and r.get_json()['code'] == 'ledger_unavailable'


def test_las_propuestas_del_repo_incluyen_2_0_0_sin_activarlo():
    from core import governance
    props = [p for p in governance.proposals() if p['id'] == 'kernel.params']
    assert props and props[0]['semver'] == '2.0.0' and props[0]['activation'] == 'pin'
    assert props[0]['four_eyes'] == 'unavailable' and props[0]['summary_es'] and props[0]['summary_en']


@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from core import governance
    from core.hotviews import hot, registry
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    governance._reset_for_tests()
    assert init_schema(retries=1)
    yield engine
    import time
    from core.hotviews import builder
    t0 = time.time()
    while builder.state().get('building') and time.time() - t0 < 10:   # sin construcciones en vuelo al salir
        time.sleep(0.02)
    governance._reset_for_tests()
    registry.reset()
    hot.reset()
    Base.metadata.drop_all(engine)


@needs_db
def test_activar_2_0_0_con_pin_y_deshacer(db, monkeypatch):
    from sqlalchemy import text

    import server
    from core import governance, pin
    from core.hotviews import builder
    from matrix import engine as E
    monkeypatch.setenv('TRADE_PIN', PIN)
    pin._reset_for_tests()
    governance.refresh()
    boot = governance.active()
    assert boot.source == 'db' and boot.artifacts['kernel.params']['semver'] == '1.0.0'
    from core import http as core_http
    c = server.app.test_client()
    real_post = c.post

    def post(*a, **k):                     # el límite real (6/min) no es lo que se prueba aquí
        core_http._rate_buckets.clear()
        return real_post(*a, **k)
    c.post = post
    body = {'artifact': 'kernel.params', 'semver': '2.0.0', 'note': 'probado'}
    assert c.post('/api/governance/activate', json=body).status_code == 401           # sin PIN
    assert c.post('/api/governance/activate', json=body, headers={'X-Trade-Pin': 'malo'}).status_code in (401, 403)
    r = c.post('/api/governance/activate', json=body, headers={'X-Trade-Pin': PIN})
    assert r.status_code == 200, r.get_json()
    d = r.get_json()
    assert d['in_force'] is True and d['changes'] == {'kernel.params': {'from': '1.0.0', 'to': '2.0.0'}}
    assert d['semver'] == '2.0.0' and d['reactivation'] is False and d['four_eyes'] == 'unavailable'
    assert governance.artifact_semver('kernel.params') == '2.0.0' and governance.active().ratified is True
    assert E.direction_up_enabled() is True and E._P('severity_divisor') == 10.0
    g = builder.current(timeout=10)
    assert g is not None and g.release == d['release_hash']                       # las vistas se reconstruyeron
    with db.connect() as cn:
        rows = cn.execute(text('SELECT release_hash, ratified, semver FROM gov_releases ORDER BY recorded_at')).all()
        dec = cn.execute(text("SELECT principal_id, auth, status, subject FROM decisions WHERE kind = "
                              "'governance.activate' ORDER BY recorded_at")).all()
    assert len(rows) == 2 and rows[1].ratified is True and rows[1].release_hash == d['release_hash']
    assert dec[-1].principal_id == 'op:fabrizio' and dec[-1].auth == 'pin' and dec[-1].status == 'executed'
    assert dec[-1].subject['from_release'] == boot.release_hash
    # otra vez lo mismo → 409 (nada que cambiar)
    assert c.post('/api/governance/activate', json=body, headers={'X-Trade-Pin': PIN}).status_code == 409
    # deshacer = activar 1.0.0 → REACTIVA el release del bootstrap (sin filas nuevas, sin UPDATE)
    r = c.post('/api/governance/activate', json={'artifact': 'kernel.params', 'semver': '1.0.0'},
               headers={'X-Trade-Pin': PIN})
    assert r.status_code == 200, r.get_json()
    d2 = r.get_json()
    assert d2['reactivation'] is True and d2['release_hash'] == boot.release_hash and d2['in_force'] is True
    assert governance.artifact_semver('kernel.params') == '1.0.0' and E.direction_up_enabled() is False
    # revisión batch E: volver a 1.0.0 con el PIN ES una aprobación de una persona → no vuelve a pedir «Ratificar»
    assert governance.active().ratified is True
    with db.connect() as cn:
        assert cn.execute(text('SELECT count(*) FROM gov_releases')).scalar() == 2
        n = cn.execute(text("SELECT count(*) FROM decisions WHERE kind = 'governance.activate'")).scalar()
    assert n == 3                                                            # bootstrap + activar + deshacer
    # y de nuevo hacia 2.0.0: la fila de 2.0.0 ya existe → también es una reactivación
    r = c.post('/api/governance/activate', json=body, headers={'X-Trade-Pin': PIN})
    assert r.status_code == 200 and r.get_json()['reactivation'] is True
    assert governance.artifact_semver('kernel.params') == '2.0.0'
    r = c.post('/api/governance/activate', json={'artifact': 'kernel.params', 'semver': '1.0.0'},
               headers={'X-Trade-Pin': PIN})
    assert r.status_code == 200 and governance.artifact_semver('kernel.params') == '1.0.0'
