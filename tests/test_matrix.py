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


# ── Restauración de factores + asientos en la migración ─────────────────────
# Regresión: grafo_v0.json son SOLO empresas y sus links. Los ~70 factores
# sistémicos y los 28 asientos viven en data/multicapa_factors_seats.json.
# Antes, una re-migración (REMIGRATE_ON_BOOT en prod) dejaba la ontología a
# medias: sin factores no hay FACTOR LIST/FIRE, ni hiperaristas en la
# fragilidad, ni objeto para Activar/DesactivarFactor.
#
# Los tests filtran por properties.fuente == 'multicapa': otros tests de este
# módulo crean factores propios (p.ej. FACTOR_taiwan_test con severidad 8) y
# el fixture es de módulo, así que aserciones sobre TODOS los factores serían
# frágiles y engañosas.

def _factores_migrados(session):
    from ontology.models import ObjectRecord
    from sqlalchemy import select
    objs = session.scalars(select(ObjectRecord).where(ObjectRecord.type == 'Factor')).all()
    return [o for o in objs if (o.properties or {}).get('fuente') == 'multicapa']


def test_migracion_restaura_los_factores_latentes(db):
    from ontology.db import session_scope

    with session_scope() as s:
        migrados = _factores_migrados(s)
        assert len(migrados) >= 60, f'se esperaban ~69 factores migrados, hay {len(migrados)}'

        props = [o.properties or {} for o in migrados]
        # TODOS latentes: cargarlos en severidad de CRISIS satura el modelo
        # (ρ 2.63, cascadas al 100%) — lección registrada en docs/ESTADO.md.
        assert {p.get('severity') for p in props} == {1.0}
        assert all(p.get('activo') is False for p in props)

        # cada uno conserva su nivel de crisis para el what-if (escala 0-10 del
        # documento fuente, NO la 0-5 del esquema de CrearFactor)
        con_crisis = [p for p in props if p.get('severity_crisis')]
        assert len(con_crisis) >= 60
        assert all(4.0 <= p['severity_crisis'] <= 10.0 for p in con_crisis)

        # el porqué no se pierde (Track B: rationale servido)
        assert any((p.get('razon') or '').strip() for p in props)


def test_migracion_restaura_asientos_y_no_deja_links_colgantes(db):
    from ontology.db import session_scope
    from ontology.models import ObjectRecord, LinkRecord
    from sqlalchemy import select

    with session_scope() as s:
        seats = s.scalars(select(ObjectRecord).where(ObjectRecord.type == 'Seat')).all()
        assert len(seats) >= 25, f'se esperaban ~28 asientos, hay {len(seats)}'

        # ningún 'affects' puede apuntar a un objeto inexistente: corrompería
        # la matriz de fragilidad
        ids = {o.id for o in s.scalars(select(ObjectRecord)).all()}
        affects = s.scalars(select(LinkRecord).where(LinkRecord.rel_type == 'affects')).all()
        assert affects, 'la migración no creó vínculos affects'
        colgantes = [(l.source_id, l.target_id) for l in affects
                     if l.source_id not in ids or l.target_id not in ids]
        assert not colgantes, f'links affects colgantes: {colgantes[:5]}'


def test_factores_latentes_no_saturan_el_modelo(db):
    """ρ con los factores MIGRADOS latentes debe quedar lejos del 2.63 saturado."""
    from ontology.db import session_scope
    from matrix.engine import active_factors, build_matrices, spectral_radius

    with session_scope() as s:
        ids_migrados = {o.id for o in _factores_migrados(s)}
        fx = [f for f in active_factors(s) if f['id'] in ids_migrados]
        mats, idx, _ids = build_matrices(s)
        base = spectral_radius(mats, factors=[], idx=idx)
        lat = spectral_radius(mats, factors=fx, idx=idx)

    assert lat['rho'] > base['rho'], 'los factores deben añadir fragilidad'
    assert lat['rho'] < 2.3, f'ρ latente {lat["rho"]} — ¿volvieron a severidad de crisis?'
