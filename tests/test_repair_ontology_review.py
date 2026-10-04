"""tests/test_repair_ontology_review.py — G5: hallazgos de la revisión
adversarial de G2/G3 (lentes "ontología" y "despliegue"). Cada test reproduce
el escenario del hallazgo; sin los cambios de G5 fallan.

Requiere Postgres real (DATABASE_URL).
"""
import os
import sys
import threading
import time
import uuid
from collections import Counter

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv('DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres) configurada')
GEN = '2000-01-01'


@pytest.fixture()
def db():
    from ontology.db import init_schema, _get_engine
    from ontology.models import Base
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    init_schema(retries=1)
    yield
    Base.metadata.drop_all(engine)


def _objs(*ids, props=None):
    from ontology.db import session_scope
    from ontology.service import apply_event
    with session_scope() as s:
        for i in ids:
            apply_event(s, 'ObjectCreated', {'label': i, 'type': 'Company', 'properties': dict((props or {}).get(i) or {})},
                        valid_from=GEN, source='migration_v0', actor='pytest', object_id=i)


def _link(s_, t, rel='supply', w=2, props=None, vf=GEN, source='migration_v0_links', dup=True, **kw):
    from ontology.db import session_scope
    from ontology.service import apply_event
    p = dict(props or {})
    if dup:
        p['allow_duplicate'] = True
    with session_scope() as s:
        ev = apply_event(s, 'LinkCreated', {'rel_type': rel, 'weight': w, 'properties': p}, valid_from=vf,
                         source=source, actor='pytest', object_id=s_, target_id=t, **kw)
        return str(ev.id)


def _legacy():
    from ontology.db import session_scope
    from ontology.models import LinkRecord
    with session_scope() as s:
        for r in s.query(LinkRecord).all():
            r.event_id = None


def _state(s):
    from ontology.models import LinkRecord
    return Counter((r.source_id, r.target_id, r.rel_type, r.weight, (r.properties or {}).get('rel_label'))
                   for r in s.query(LinkRecord).filter(LinkRecord.valid_to.is_(None)).all())


def _replay(s, as_of=None):
    from ontology.service import as_of_graph
    return Counter((l['source'], l['target'], l['rel_type'], l['weight'], (l['properties'] or {}).get('rel_label'))
                   for l in as_of_graph(s, as_of)['links'])


def _rows(s, a, b):
    from ontology.models import LinkRecord
    return s.query(LinkRecord).filter(LinkRecord.source_id == a, LinkRecord.target_id == b,
                                      LinkRecord.valid_to.is_(None)).all()


def _snap(links, alias=None, nodes=None):
    from ontology.reconcile import snapshot_from_dict
    ids = set(nodes or [])
    for l in links:
        ids.update((l['source'], l['target']))
    return snapshot_from_dict({'exported_at': 'test', 'node_id_alias': alias or {},
                               'nodes': [{'id': i} for i in sorted(ids)], 'links': links})


def _dbname():
    from ontology.db import session_scope
    from ontology.reconcile import _db_name
    with session_scope() as s:
        return _db_name(s)


# ── O-1 (alta): una fila heredada se empareja con SU evento (no con el de su gemela)
def test_g5_fila_heredada_se_empareja_con_su_propio_evento(db):
    from ontology.db import session_scope
    from ontology.actions import execute_action
    _objs('TSMC', 'NVDA')
    _link('TSMC', 'NVDA', w=3, props={'rel_label': 'CoWoS'})
    _link('TSMC', 'NVDA', w=3, props={'rel_label': 'CoWoS (no verificado)'})
    _legacy()
    with session_scope() as s:
        victim = next(r for r in _rows(s, 'TSMC', 'NVDA') if 'no verificado' in r.properties['rel_label'])
        execute_action(s, 'RetractarVinculo', {'link_id': str(victim.id), 'razon': 'copia'}, actor='fabrizio')
    with session_scope() as s:
        assert _state(s) == _replay(s) == Counter({('TSMC', 'NVDA', 'supply', 3.0, 'CoWoS'): 1})


# ── O-2 / D-1: deshacer no resucita lo que una persona cerró DESPUÉS
def test_g5_deshacer_no_resucita_un_vinculo_rechazado_despues(db):
    from ontology.db import session_scope
    from ontology.actions import execute_action
    from ontology.reconcile import apply_plan, rollback_run
    _objs('TSMC', 'NVDA')
    _link('TSMC', 'NVDA', w=3)
    _link('TSMC', 'NVDA', w=3)
    _legacy()
    snap = _snap([{'source': 'TSMC', 'target': 'NVDA', 'w': 3, 'type': 'supply', 'rel': ''}])
    r = apply_plan(session_scope, snap, include=['duplicates'], confirm_db=_dbname())
    assert r['applied'] == {'duplicates': 1}
    time.sleep(0.05)
    with session_scope() as s:
        keep = _rows(s, 'TSMC', 'NVDA')[0]
        execute_action(s, 'RechazarVinculo', {'link_id': str(keep.id)}, actor='fabrizio')
    with session_scope() as s:
        out = rollback_run(s, r['run_id'], confirm_db=_dbname())
        assert out['skipped_closed_later'] == 1 and out['links_reopened'] == 0
    with session_scope() as s:
        assert _rows(s, 'TSMC', 'NVDA') == [] and _replay(s) == _state(s) == Counter()


# ── O-3: una re-creación registrada DESPUÉS de una remoción sigue viva en el replay
def test_g5_replay_respeta_el_orden_de_registro(db):
    from ontology.db import session_scope
    from ontology.service import apply_event
    _objs('A', 'B')
    _link('A', 'B', w=2, dup=False)
    with session_scope() as s:
        apply_event(s, 'LinkRemoved', {'rel_type': 'supply'}, valid_from='2026-01-01', source='manual', actor='f',
                    object_id='A', target_id='B')
    time.sleep(0.05)
    _link('A', 'B', w=2, props={'merged_from': 'A_old'}, source='manual', dup=False)    # re-creada con fecha vieja
    with session_scope() as s:
        assert _state(s) == _replay(s) and sum(_state(s).values()) == 1


# ── O-4: un hecho INDEPENDIENTE deduplicado sobrevive al DESHACER de su gemela;
#    una CORRECCIÓN (RetractarVinculo) no resucita copias del mismo hecho falso
def test_g5_deshacer_fusion_no_pierde_un_hecho_independiente(db):
    from ontology.db import session_scope
    from ontology.bulk_import import import_links_bulk
    from ontology.reconcile import apply_plan, rollback_run
    _objs('Luminar', 'Luminar_Lidar', 'Volvo')
    _link('Luminar_Lidar', 'Volvo', w=1.0, props={'rel_label': 'lidar'})
    snap = _snap([{'source': 'Luminar', 'target': 'Volvo', 'w': 1, 'type': 'supply', 'rel': 'lidar'}],
                 alias={'Luminar_Lidar': 'Luminar'})
    r = apply_plan(session_scope, snap, include=['alias'], confirm_db=_dbname())
    with session_scope() as s:                 # Wikidata afirma lo mismo DESPUÉS, por su cuenta
        out = import_links_bulk(s, [{'source': 'Luminar', 'target': 'Volvo', 'rel_type': 'supply', 'weight': 1.0}],
                                'wikidata')
        assert out['created'] == 0
    with session_scope() as s:
        rollback_run(s, r['run_id'], confirm_db=_dbname())
    with session_scope() as s:
        st = _state(s)
        assert st == _replay(s)
        assert st[('Luminar_Lidar', 'Volvo', 'supply', 1.0, 'lidar')] == 1          # el alias vuelve
        assert sum(v for k, v in st.items() if k[:2] == ('Luminar', 'Volvo')) == 1    # y el hecho de Wikidata sigue


def test_g5_una_correccion_no_resucita_copias(db):
    from ontology.db import session_scope
    from ontology.actions import execute_action
    _objs('X', 'TSMC')
    _link('X', 'TSMC', w=2, dup=False)
    _link('X', 'TSMC', w=2, props={'source': 'wikidata'}, source='wikidata', vf='2024-01-01', dup=False)   # dedup
    with session_scope() as s:
        execute_action(s, 'RetractarVinculo', {'link_id': str(_rows(s, 'X', 'TSMC')[0].id),
                                               'razon': 'dirección al revés'}, actor='f')
    with session_scope() as s:
        assert _state(s) == _replay(s) == Counter()


# ── O-5 / D-1: aplicar y deshacer nunca corren dos a la vez
def test_g5_candado_aplicar_y_deshacer(db):
    from sqlalchemy import text
    from ontology.db import _get_engine, session_scope
    from ontology.reconcile import apply_plan, rollback_run, ReconcileError, LOCK_KEY
    _objs('A', 'B')
    _link('A', 'B', w=1)
    snap = _snap([{'source': 'A', 'target': 'B', 'w': 1, 'type': 'supply', 'rel': ''}])
    conn = _get_engine().connect()
    try:
        assert conn.execute(text('SELECT pg_try_advisory_lock(:k)'), {'k': LOCK_KEY}).scalar()
        with pytest.raises(ReconcileError, match='en curso'):
            apply_plan(session_scope, snap, include=['duplicates'], confirm_db=_dbname())
        with session_scope() as s:
            with pytest.raises(ReconcileError, match='en curso'):
                rollback_run(s, 'x', confirm_db=_dbname())
    finally:
        conn.execute(text('SELECT pg_advisory_unlock(:k)'), {'k': LOCK_KEY})
        conn.close()


# ── O-6: deshacer una fusión restaura el estado EXACTO del alias (p. ej. en quiebra)
def test_g5_deshacer_fusion_restaura_estado_previo(db):
    from ontology.db import session_scope
    from ontology.service import get_object
    from ontology.reconcile import apply_plan, rollback_run
    _objs('Luminar', 'Luminar_Lidar', 'Volvo',
          props={'Luminar_Lidar': {'retired': True, 'retired_razon': 'quiebra 2025 (chapter 11)'}})
    _link('Luminar_Lidar', 'Volvo', w=2)
    snap = _snap([{'source': 'Luminar', 'target': 'Volvo', 'w': 2, 'type': 'supply', 'rel': ''}],
                 alias={'Luminar_Lidar': 'Luminar'})
    r = apply_plan(session_scope, snap, include=['alias'], confirm_db=_dbname())
    assert r['applied'] == {'alias': 1}
    with session_scope() as s:
        rollback_run(s, r['run_id'], confirm_db=_dbname())
    with session_scope() as s:
        a = get_object(s, 'Luminar_Lidar').properties
        assert a['retired'] is True and a['retired_razon'] == 'quiebra 2025 (chapter 11)' and not a.get('merged_into')
        assert (get_object(s, 'Luminar').properties.get('aliases') or []) == []


# ── O-7: la fusión conserva documento de procedencia, confianza y canal
def test_g5_fusion_conserva_procedencia(db):
    from ontology.db import session_scope
    from ontology.actions import execute_action
    from ontology.models import Event
    _objs('Luminar', 'Luminar_Lidar', 'Volvo')
    _link('Luminar_Lidar', 'Volvo', w=2, source='edgar', source_id='src_1', confidence=0.9, dup=False)
    with session_scope() as s:
        execute_action(s, 'FusionarEntidad', {'alias_id': 'Luminar_Lidar', 'canonical_id': 'Luminar', 'razon': 'misma'},
                       actor='f')
    with session_scope() as s:
        row = _rows(s, 'Luminar', 'Volvo')[0]
        ev = s.get(Event, row.event_id)
        assert ev.source_id == 'src_1' and abs(ev.confidence - 0.9) < 1e-9
        assert row.properties.get('orig_channel') == 'edgar'


# ── O-8: deshacer con vínculos entre dos alias de la misma corrida vuelve EXACTO
def test_g5_deshacer_cadena_de_alias_exacto(db):
    from ontology.db import session_scope
    from ontology.reconcile import apply_plan, rollback_run
    _objs('A1', 'A2', 'C1', 'C2')
    _link('A1', 'A2', w=2)
    with session_scope() as s:
        before = _state(s)
    snap = _snap([{'source': 'C1', 'target': 'C2', 'w': 2, 'type': 'supply', 'rel': ''}],
                 alias={'A1': 'C1', 'A2': 'C2'})
    r = apply_plan(session_scope, snap, include=['alias'], confirm_db=_dbname())
    with session_scope() as s:
        assert _state(s) == _replay(s) == Counter({('C1', 'C2', 'supply', 2.0, None): 1})
        rollback_run(s, r['run_id'], confirm_db=_dbname())
    with session_scope() as s:
        assert _state(s) == _replay(s) == before


# ── O-9: la importación masiva no repite eventos no-op ni cuenta lo que no creó
def test_g5_bulk_import_idempotente_por_fuente(db):
    from ontology.db import session_scope
    from ontology.bulk_import import import_links_bulk
    from ontology.models import Event
    _objs('Luminar', 'Volvo')
    _link('Luminar', 'Volvo', w=1.0, dup=False)
    rec = [{'source': 'Luminar', 'target': 'Volvo', 'rel_type': 'supply', 'weight': 1.0}]
    with session_scope() as s:
        n0 = s.query(Event).count()
        r1 = import_links_bulk(s, rec, 'wikidata')
        assert r1['created'] == 0                              # se registró como duplicado, no como creado
    with session_scope() as s:
        n1 = s.query(Event).count()
        assert n1 == n0 + 1
        r2 = import_links_bulk(s, rec, 'wikidata')
        assert r2['created'] == 0 and r2['skipped_duplicates'] == 1 and s.query(Event).count() == n1


# ── O-10: si el canónico no existe en la base, el ítem no rompe la categoría
def test_g5_canonico_ausente_va_a_objetos_faltantes(db):
    from ontology.db import session_scope
    from ontology.reconcile import apply_plan, build_plan
    _objs('AWS', 'X')
    _link('AWS', 'X', w=2, rel='cloud')
    snap = _snap([{'source': 'X', 'target': 'Amazon', 'w': 2, 'type': 'cloud', 'rel': ''}], alias={'AWS': 'Amazon'})
    with session_scope() as s:
        plan = build_plan(s, snap)
    assert plan['summary']['direction'] == 0 and plan['summary']['variants'] == 0
    assert any('Amazon' in o['missing'] for o in plan['objects_missing'])
    r = apply_plan(session_scope, snap, include=['direction', 'variants'], confirm_db=_dbname())
    assert 'error' not in r


# ── O-11: retracts_event_id en mayúsculas: tablas y replay coinciden
def test_g5_uuid_no_canonico_en_la_retraccion(db):
    from ontology.db import session_scope
    from ontology.service import apply_event
    _objs('A', 'B')
    eid = _link('A', 'B', w=2, dup=False)
    with session_scope() as s:
        apply_event(s, 'LinkRemoved', {'rel_type': 'supply', 'properties': {'retracts_event_id': eid.upper()}},
                    valid_from=GEN, source='manual', actor='f', object_id='A', target_id='B')
    with session_scope() as s:
        assert _state(s) == _replay(s) == Counter()


# ── O-12 / D-5: índice de event_id y arranque sin candado exclusivo si la columna ya existe
def test_g5_indice_y_arranque_no_bloquea(db):
    from sqlalchemy import text
    from ontology.db import _get_engine, init_schema
    eng = _get_engine()
    with eng.connect() as c:
        assert c.execute(text("SELECT 1 FROM pg_indexes WHERE indexname = 'ix_links_event_id'")).first()
    holder = eng.connect()
    tx = holder.begin()
    holder.execute(text('LOCK TABLE links IN ROW SHARE MODE'))     # una transacción larga sobre links
    try:
        out = {}
        th = threading.Thread(target=lambda: out.update(ok=init_schema(retries=1)))
        t0 = time.time(); th.start(); th.join(20)
        assert out.get('ok') is True and time.time() - t0 < 10, 'init_schema no debe esperar el candado de links'
    finally:
        tx.rollback(); holder.close()


# ── O-13 + D-6: errata en categorías y plan cambiado → se niega (bilingüe)
def test_g5_include_invalido_y_plan_cambiado(db):
    from ontology.db import session_scope
    from ontology.reconcile import apply_plan, ReconcileError
    _objs('A', 'B')
    _link('A', 'B', w=1); _link('A', 'B', w=1)
    _legacy()
    snap = _snap([{'source': 'A', 'target': 'B', 'w': 1, 'type': 'supply', 'rel': ''}])
    with pytest.raises(ReconcileError) as e:
        apply_plan(session_scope, snap, include=['alias', 'duplicate'], confirm_db=_dbname())
    assert 'duplicate' in str(e.value) and 'unknown categories' in e.value.en
    with pytest.raises(ReconcileError, match='cambió'):
        apply_plan(session_scope, snap, include=['duplicates'], confirm_db=_dbname(), expect={'duplicates': 7})
    r = apply_plan(session_scope, snap, include=['duplicates'], confirm_db=_dbname(), expect={'duplicates': 1})
    assert r['applied'] == {'duplicates': 1}


# ── un vínculo que una persona rechazó no se propone como "faltante"
def test_g5_faltante_rechazado_no_se_propone(db):
    from ontology.db import session_scope
    from ontology.actions import execute_action
    from ontology.reconcile import build_plan
    _objs('X', 'Y')
    _link('X', 'Y', w=2, dup=False)
    with session_scope() as s:
        execute_action(s, 'RechazarVinculo', {'link_id': str(_rows(s, 'X', 'Y')[0].id)}, actor='fabrizio')
    snap = _snap([{'source': 'X', 'target': 'Y', 'w': 2, 'type': 'supply', 'rel': ''}])
    with session_scope() as s:
        plan = build_plan(s, snap)
    assert plan['summary']['missing'] == 0 and plan['summary']['missing_rejected'] == 1


# ── D-4 / D-8: sin TRADE_PIN no hay "modo desarrollo" para reconcile; tipos raros → 400
def test_g5_api_exige_pin_configurado_y_valida_tipos(db, monkeypatch):
    import server
    from core import pin
    from core import http as _h
    pin._reset_for_tests(); _h._rate_buckets.clear()
    server.app.config['TESTING'] = True
    c = server.app.test_client()
    monkeypatch.delenv('TRADE_PIN', raising=False)
    assert c.post('/api/ontology/reconcile/apply', json={'actor': 'x', 'confirm_db': _dbname()}).status_code == 403
    assert c.post('/api/ontology/reconcile/rollback', json={'actor': 'x', 'run_id': 'r'}).status_code == 403
    monkeypatch.setenv('TRADE_PIN', 'pin-g5-2468')
    h = {'X-Trade-Pin': 'pin-g5-2468'}
    assert c.post('/api/ontology/reconcile/apply', json={'actor': 123, 'confirm_db': 'x'}, headers=h).status_code == 400
    assert c.post('/api/ontology/reconcile/rollback', json={'actor': 'a', 'run_id': 5}, headers=h).status_code == 400
    g = c.get('/api/ontology/reconcile/plan?summary=1')
    assert g.status_code == 200 and 'path' not in (g.get_json().get('snapshot') or {})


# ── revisión de G5 (ensayo realista): un duplicado escrito por la MISMA corrida no asciende al deshacerla
def test_g5_deshacer_no_asciende_duplicados_de_la_misma_corrida(db):
    from ontology.db import session_scope
    from ontology.reconcile import rollback_run, RUN_PREFIX
    _objs('A', 'B')
    with session_scope() as s:
        before = _state(s)
    run = '20990101T000000Z-abcdef'
    _link('A', 'B', w=2, source=RUN_PREFIX + run, dup=False)
    _link('A', 'B', w=2, source=RUN_PREFIX + run, dup=False)          # deduplicado (misma corrida)
    with session_scope() as s:
        out = rollback_run(s, run, confirm_db=_dbname())
        assert out['links_retracted'] == 1
    with session_scope() as s:
        assert _state(s) == _replay(s) == before


# ════════ G5c — segunda revisión adversarial (sobre G5) ════════

def test_g5c_orden_por_defecto_no_cambia_un_duplicado_por_otro(db):
    """RR-1: el canónico tiene dos copias heredadas (una con el texto del catálogo)
    y el alias otra más: tras alias+duplicates queda UNA fila, y deshacer es exacto."""
    from ontology.db import session_scope
    from ontology.reconcile import apply_plan, build_plan, rollback_run
    _objs('C', 'AL', 'X')
    _link('C', 'X', w=2, props={'rel_label': 'old'})
    _link('C', 'X', w=2, props={'rel_label': 'cat'})
    _link('AL', 'X', w=2, props={'rel_label': 'alias'})
    _legacy()
    with session_scope() as s:
        before = _state(s)
    snap = _snap([{'source': 'C', 'target': 'X', 'w': 2, 'type': 'supply', 'rel': 'cat'}], alias={'AL': 'C'})
    r = apply_plan(session_scope, snap, include=['alias', 'duplicates'], confirm_db=_dbname())
    with session_scope() as s:
        assert build_plan(s, snap)['summary']['duplicates'] == 0
        assert sum(v for k, v in _state(s).items() if k[:2] == ('C', 'X')) == 1 and _state(s) == _replay(s)
        rollback_run(s, r['run_id'], confirm_db=_dbname())
    with session_scope() as s:
        assert _state(s) == _replay(s) == before


def test_g5c_extra_y_deshacer_con_hecho_independiente(db):
    """RR-2: un hecho de wikidata deduplicado contra una fila que 'extra' retracta
    (corrección): no asciende; deshacer vuelve EXACTO (1 fila, no 2)."""
    from ontology.db import session_scope
    from ontology.reconcile import apply_plan, rollback_run
    _objs('A', 'B', 'Z')
    _link('A', 'B', w=2)
    _legacy()
    _link('A', 'B', w=2, props={'source': 'wikidata'}, source='wikidata', vf='2024-01-01', dup=False)
    with session_scope() as s:
        before = _state(s)
    snap = _snap([{'source': 'A', 'target': 'Z', 'w': 1, 'type': 'supply', 'rel': ''}], nodes=['B'])
    r = apply_plan(session_scope, snap, include=['extra'], confirm_db=_dbname())
    assert r['applied'] == {'extra': 1}
    with session_scope() as s:
        assert _state(s) == _replay(s) == Counter()
        rollback_run(s, r['run_id'], confirm_db=_dbname())
    with session_scope() as s:
        assert _state(s) == _replay(s) == before


def test_g5c_misma_transaccion_remocion_y_recreacion(db):
    """RR-4: remoción no dirigida y re-creación en la MISMA transacción: con
    now() empataban y el replay mataba la re-creación; ahora coinciden."""
    from ontology.db import session_scope
    from ontology.service import apply_event
    _objs('A', 'B')
    _link('A', 'B', w=2, dup=False)
    with session_scope() as s:
        apply_event(s, 'LinkRemoved', {'rel_type': 'supply'}, valid_from='2026-01-01', source='manual', actor='f',
                    object_id='A', target_id='B')
        apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 2, 'properties': {'allow_duplicate': True}},
                    valid_from=GEN, source='manual', actor='f', object_id='A', target_id='B')
    with session_scope() as s:
        assert _state(s) == _replay(s) and sum(_state(s).values()) == 1


def test_g5c_deshacer_fusion_conserva_alias_posteriores(db):
    from ontology.db import session_scope
    from ontology.actions import execute_action
    from ontology.service import get_object
    from ontology.reconcile import apply_plan, rollback_run
    _objs('C', 'AL', 'AL2', 'X')
    _link('AL', 'X', w=2)
    snap = _snap([{'source': 'C', 'target': 'X', 'w': 2, 'type': 'supply', 'rel': ''}], alias={'AL': 'C'})
    r = apply_plan(session_scope, snap, include=['alias'], confirm_db=_dbname())
    with session_scope() as s:
        execute_action(s, 'FusionarEntidad', {'alias_id': 'AL2', 'canonical_id': 'C', 'razon': 'a mano'}, actor='f')
    with session_scope() as s:
        rollback_run(s, r['run_id'], confirm_db=_dbname())
    with session_scope() as s:
        assert get_object(s, 'C').properties.get('aliases') == ['AL2']


def test_g5c_deshacer_fusion_no_resucita_lo_rechazado_en_el_canonico(db):
    from ontology.db import session_scope
    from ontology.actions import execute_action
    from ontology.reconcile import apply_plan, rollback_run
    _objs('C', 'AL', 'X')
    _link('AL', 'X', w=2)
    snap = _snap([{'source': 'C', 'target': 'X', 'w': 2, 'type': 'supply', 'rel': ''}], alias={'AL': 'C'})
    r = apply_plan(session_scope, snap, include=['alias'], confirm_db=_dbname())
    time.sleep(0.05)
    with session_scope() as s:
        execute_action(s, 'RechazarVinculo', {'link_id': str(_rows(s, 'C', 'X')[0].id)}, actor='fabrizio')
    with session_scope() as s:
        out = rollback_run(s, r['run_id'], confirm_db=_dbname())
        assert out['skipped_closed_later'] == 1
    with session_scope() as s:
        assert _rows(s, 'AL', 'X') == [] and _state(s) == _replay(s)


def test_g5c_expect_no_numerico_es_400(db, monkeypatch):
    import server
    from core import pin
    from core import http as _h
    pin._reset_for_tests(); _h._rate_buckets.clear()
    monkeypatch.setenv('TRADE_PIN', 'pin-g5c-1357')
    c = server.app.test_client()
    r = c.post('/api/ontology/reconcile/apply', json={'actor': 'f', 'confirm_db': _dbname(), 'include': ['duplicates'],
                                                       'expect': {'duplicates': {'n': 1}}},
               headers={'X-Trade-Pin': 'pin-g5c-1357'})
    assert r.status_code == 400 and r.get_json()['error_en']
