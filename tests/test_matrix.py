"""tests/test_matrix.py — Etapa 3: motor de matrices + hiperaristas.

Requiere Postgres (DATABASE_URL) con la migración corrida — igual que los
tests de ontología, se auto-saltan sin base de datos.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv('DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')


@pytest.fixture(scope='module')
def db():
    """Base poblada con el snapshot canónico real (migración completa)."""
    import subprocess
    from ontology.db import init_schema, _get_engine
    from ontology.models import Base
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    init_schema()
    script = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'migrate_v0_to_ontology.py')
    r = subprocess.run([sys.executable, script, '--reset'], capture_output=True, text=True,
                       env={**os.environ, 'DATABASE_URL': DATABASE_URL,
                            'PYTHONIOENCODING': 'utf-8'})
    assert r.returncode == 0, r.stderr
    yield
    Base.metadata.drop_all(engine)


def test_build_matrices_ground_truths(db):
    """La matriz supply contiene ASML→TSMC; fab contiene TSMC→Nvidia; y las
    direcciones invertidas NO existen (convención canónica de la Etapa 2)."""
    from ontology.db import session_scope
    from matrix.engine import build_matrices

    with session_scope() as s:
        mats, idx, ids = build_matrices(s)
    assert mats['supply'][idx['ASML'], idx['TSMC']] > 0
    assert mats['supply'][idx['TSMC'], idx['ASML']] == 0
    assert mats['fab'][idx['TSMC'], idx['Nvidia']] > 0
    assert mats['invest'][idx['Microsoft'], idx['OpenAI']] > 0
    # partner es simétrico
    p = mats['partner']
    assert (p == p.T).all()


def test_propagate_tsmc_shock_hits_customers(db):
    """Si TSMC cae, sus clientes fabless sufren — y más que un nodo lejano."""
    from ontology.db import session_scope
    from matrix.engine import build_matrices, propagate

    with session_scope() as s:
        mats, idx, ids = build_matrices(s)
    impacts, cascade = propagate(mats, idx, ids, ['TSMC'])
    assert impacts.get('TSMC') == 100.0
    assert impacts.get('Nvidia', 0) > 5          # cliente directo con peso alto
    assert impacts.get('Apple', 0) > 5
    assert len(impacts) > 30                     # la onda alcanza a decenas
    hops = {c['id']: c['hop'] for c in cascade}
    assert hops.get('Nvidia') == 1               # cliente directo = hop 1


def test_hyperedge_factor_amplifies_impact(db):
    """Un Factor activo (hiperarista) amplifica el daño de sus miembros."""
    from ontology.db import session_scope
    from ontology.service import apply_event
    from matrix.engine import active_factors, build_matrices, fragility, propagate

    with session_scope() as s:
        mats, idx, ids = build_matrices(s)
        base_impacts, _ = propagate(mats, idx, ids, ['TSMC'])

    with session_scope() as s:
        apply_event(s, 'ObjectCreated', {
            'label': 'Conflicto en el estrecho de Taiwán', 'type': 'Factor',
            'properties': {'severity': 8},
        }, valid_from='2026-07-01', source='test', actor='pytest',
            object_id='FACTOR_taiwan_test')
        apply_event(s, 'LinkCreated', {'rel_type': 'affects', 'weight': 0.8},
                    valid_from='2026-07-01', source='test', actor='pytest',
                    object_id='FACTOR_taiwan_test', target_id='Nvidia')

    with session_scope() as s:
        factors = active_factors(s)
        assert any(f['id'] == 'FACTOR_taiwan_test' for f in factors)
        mats, idx, ids = build_matrices(s)
        frag = fragility(idx, factors)
        mod_impacts, _ = propagate(mats, idx, ids, ['TSMC'], frag=frag)

    assert mod_impacts.get('Nvidia', 0) > base_impacts.get('Nvidia', 0)

    # y con time-travel ANTES del factor, no modula
    with session_scope() as s:
        past = active_factors(s, as_of='2026-01-01')
    assert not any(f['id'] == 'FACTOR_taiwan_test' for f in past)


def test_metrics_chokepoints(db):
    from ontology.db import session_scope
    from matrix.engine import compute_metrics

    with session_scope() as s:
        metrics, _ = compute_metrics(s)
    assert 'TSMC' in metrics
    assert metrics['TSMC']['cascade_size'] > 20
    top10 = [k for k, v in metrics.items() if v['chokepoint_rank'] <= 10]
    assert 'TSMC' in top10


def test_api_endpoints(db):
    import server
    client = server.app.test_client()

    st = client.get('/api/matrix/status').get_json()
    assert st['available'] is True and st['objects'] > 400

    m = client.get('/api/matrix/supply').get_json()
    assert m['nnz'] > 300

    r = client.post('/api/matrix/impact', json={'shock': ['TSMC']}).get_json()
    assert r['impacts']['TSMC'] == 100.0
    assert r['affected'] > 30

    bad = client.post('/api/matrix/impact', json={'shock': ['NoExiste123']})
    assert bad.status_code == 400


# ── Historial de insights (Track B) ─────────────────────────────────────────
# OJO: /api/matrix/insights YA EXISTÍA (sim narrada del hipergrafo). El
# historial es una ruta NUEVA bajo /insights/history para no colisionar.

def test_insights_history_guarda_una_fila_por_epoca(db):
    """Dos lecturas del MISMO grafo no deben duplicar historia: la clave de
    deduplicación es (graph_epoch, as_of, lang)."""
    import server
    from ontology.db import session_scope
    from ontology.models import InsightSnapshot
    client = server.app.test_client()

    with session_scope() as s:
        s.query(InsightSnapshot).delete()

    first = client.post('/api/matrix/insights', json={'lang': 'es'})
    assert first.status_code == 200

    h1 = client.get('/api/matrix/insights/history').get_json()
    assert h1['available'] is True
    assert h1['count'] == 1
    assert h1['history'][0]['lang'] == 'es'

    # segunda lectura del mismo grafo → sin fila nueva (aunque venga de caché)
    client.post('/api/matrix/insights', json={'lang': 'es'})
    h2 = client.get('/api/matrix/insights/history').get_json()
    assert h2['count'] == 1


def test_insights_history_nueva_fila_cuando_cambia_el_grafo(db):
    """Un cambio real del grafo (época nueva) SÍ debe dejar una fila nueva."""
    import server
    from ontology.db import session_scope
    from ontology.models import InsightSnapshot
    from ontology.actions import execute_action
    client = server.app.test_client()

    with session_scope() as s:
        s.query(InsightSnapshot).delete()

    client.post('/api/matrix/insights', json={'lang': 'es'})
    antes = client.get('/api/matrix/insights/history').get_json()['count']

    # escribir en la ontología mueve MAX(recorded_at) = la época del grafo
    with session_scope() as s:
        execute_action(s, 'AnotarObjeto',
                       {'object_id': 'TSMC', 'texto': 'nota que cambia la época'}, actor='pytest')

    client.post('/api/matrix/insights', json={'lang': 'es'})
    despues = client.get('/api/matrix/insights/history').get_json()['count']
    assert despues == antes + 1


def test_insights_history_filtra_por_idioma_y_respeta_limit(db):
    import server
    from ontology.db import session_scope
    from ontology.models import InsightSnapshot
    client = server.app.test_client()

    with session_scope() as s:
        s.query(InsightSnapshot).delete()

    client.post('/api/matrix/insights', json={'lang': 'es'})
    client.post('/api/matrix/insights', json={'lang': 'en'})

    solo_en = client.get('/api/matrix/insights/history?lang=en').get_json()
    assert solo_en['count'] == 1
    assert all(h['lang'] == 'en' for h in solo_en['history'])

    limitado = client.get('/api/matrix/insights/history?limit=1').get_json()
    assert limitado['count'] == 1


def test_shock_manual_no_ensucia_el_historial(db):
    """Un shock manual es exploración, no historia — no debe persistirse."""
    import server
    from ontology.db import session_scope
    from ontology.models import InsightSnapshot
    client = server.app.test_client()

    with session_scope() as s:
        s.query(InsightSnapshot).delete()

    r = client.post('/api/matrix/insights', json={'lang': 'es', 'shock': ['TSMC']})
    assert r.status_code == 200
    h = client.get('/api/matrix/insights/history').get_json()
    assert h['count'] == 0
