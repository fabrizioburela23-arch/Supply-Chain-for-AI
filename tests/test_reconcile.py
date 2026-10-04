"""tests/test_reconcile.py — G3 (misión de reparación 2026-10-04): reconciliar
el catálogo (snapshot) con la ontología en Postgres SOLO con eventos.

Se monta una base "vieja" como la de producción (filas sin event_id, una
empresa duplicada por alias, un vínculo repetido, direcciones al revés, otro
peso, un faltante y un sobrante, más filas que NO deben tocarse) y se verifica:
dry-run sin escrituras, confirmación del nombre de la base, aplicar por
categorías hasta quedar isomorfo al catálogo, replay == tablas, nada borrado,
y deshacer cada corrida con eventos nuevos.
"""
import os
import sys
from collections import Counter

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv('DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres) configurada')

GEN = '2000-01-01'
SNAP = {
    'exported_at': '2026-09-29T00:00:00Z',
    'node_id_alias': {'Mobileye_Auto': 'Mobileye'},
    'nodes': [{'id': i} for i in ('TSMC', 'Nvidia', 'Apple', 'Mobileye', 'Hesai', 'Meta', 'Qualcomm')],
    'links': [
        {'source': 'TSMC', 'target': 'Nvidia', 'w': 6, 'rel': 'CoWoS + N4', 'type': 'fab'},
        {'source': 'TSMC', 'target': 'Apple', 'w': 6, 'rel': 'A18', 'type': 'fab'},
        {'source': 'TSMC', 'target': 'Mobileye', 'w': 2, 'rel': 'EyeQ', 'type': 'supply'},
        {'source': 'TSMC', 'target': 'Hesai', 'w': 2, 'rel': '', 'type': 'supply'},
        {'source': 'TSMC', 'target': 'Meta', 'w': 4, 'rel': 'MTIA', 'type': 'fab'},
        {'source': 'Qualcomm', 'target': 'Nvidia', 'w': 2, 'rel': 'x', 'type': 'partner'},
    ],
}


@pytest.fixture(scope='module')
def db():
    from ontology.db import init_schema, _get_engine, session_scope
    from ontology.models import Base
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    init_schema()
    with session_scope() as s:
        for oid in ('TSMC', 'Nvidia', 'Apple', 'Mobileye', 'Mobileye_Auto', 'Hesai', 'Meta', 'Qualcomm', 'WikiCo', 'Factor1'):
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company', 'properties': {}},
                        valid_from=GEN, source='migration_v0', actor='script:migrate_v0_to_ontology', object_id=oid)

        def L(src, tgt, rel, w, props=None, vf=GEN, source='migration_v0_links'):
            p = dict(props or {}); p['allow_duplicate'] = True       # la migración vieja NO deduplicaba
            apply_event(s, 'LinkCreated', {'rel_type': rel, 'weight': w, 'properties': p}, valid_from=vf,
                        source=source, actor='script:migrate_v0_to_ontology', object_id=src, target_id=tgt)
        L('TSMC', 'Nvidia', 'fab', 6)
        L('TSMC', 'Nvidia', 'fab', 6)                          # duplicado exacto
        L('TSMC', 'Apple', 'fab', 6)
        L('TSMC', 'Apple', 'fab', 5)                           # mismo vínculo, otro peso
        L('Mobileye_Auto', 'TSMC', 'supply', 2)                # alias + dirección vieja
        L('Hesai', 'TSMC', 'supply', 2)                        # dirección vieja
        L('TSMC', 'Meta', 'partner', 1, {'rel_label': '<script>alert(1)</script>'})   # sobra (y prueba el escape)
        # NO deben tocarse:
        L('Qualcomm', 'Nvidia', 'partner', None, vf='2023-05-01', source='migration_v0_temporal')   # fecha real
        L('WikiCo', 'Nvidia', 'supply', 3, {'source': 'wikidata'}, source='wikidata')             # fuente externa
        L('Factor1', 'Nvidia', 'affects', 2, {'factor': True}, source='migration_multicapa')        # factor
    with session_scope() as s:                                  # filas "heredadas": sin event_id (como producción)
        from ontology.models import LinkRecord
        for r in s.query(LinkRecord).all():
            r.event_id = None
    yield
    Base.metadata.drop_all(engine)


def _snap():
    from ontology.reconcile import snapshot_from_dict
    return snapshot_from_dict(SNAP)


def _state(s):
    from ontology.models import LinkRecord
    rows = s.query(LinkRecord).filter(LinkRecord.valid_to.is_(None)).all()
    return Counter((r.source_id, r.target_id, r.rel_type, None if r.weight is None else float(r.weight)) for r in rows)


def _replay_state(s):
    from ontology.service import as_of_graph
    return Counter((l['source'], l['target'], l['rel_type'], None if l['weight'] is None else float(l['weight']))
                   for l in as_of_graph(s)['links'])


def _counts(s):
    from ontology.models import Event, LinkRecord
    return s.query(Event).count(), s.query(LinkRecord).count()


def _dbname(s):
    from ontology.reconcile import _db_name
    return _db_name(s)


def test_g3_dry_run_clasifica_y_no_escribe(db):
    from ontology.db import session_scope
    from ontology.reconcile import build_plan
    with session_scope() as s:
        before = _counts(s)
        plan = build_plan(s, _snap())
        assert _counts(s) == before, 'el dry-run no escribe nada'
    sm = plan['summary']
    assert (sm['alias'], sm['duplicates'], sm['direction'], sm['variants'], sm['missing'], sm['extra']) == (1, 1, 2, 1, 1, 1), sm
    assert plan['alias'][0]['alias'] == 'Mobileye_Auto' and plan['alias'][0]['canonical'] == 'Mobileye'
    assert plan['duplicates'][0]['copies'] == 2
    dirs = {(d['db_source'], d['db_target']) for d in plan['direction']}
    assert dirs == {('Mobileye_Auto', 'TSMC'), ('Hesai', 'TSMC')}
    assert plan['variants'][0]['weight_db'] == 5 and plan['variants'][0]['catalog_row_exists'] is True
    assert (plan['missing'][0]['source'], plan['missing'][0]['target'], plan['missing'][0]['rel']) == ('TSMC', 'Meta', 'fab')
    assert (plan['extra'][0]['source'], plan['extra'][0]['target']) == ('TSMC', 'Meta')
    # lo dudoso/externo queda fuera y Qualcomm→Nvidia (con fecha real) NO se cuenta como faltante
    assert plan['out_of_scope'] == {'fecha_real': 1, 'fuente_externa': 1, 'rel_fuera_del_catalogo': 1}


def test_g3_informe_bilingue_y_html_escapado(db):
    from ontology.db import session_scope
    from ontology.reconcile import build_plan, render_markdown, markdown_to_html
    with session_scope() as s:
        plan = build_plan(s, _snap())
    es, en = render_markdown(plan, dbname='x'), render_markdown(plan, dbname='x', lang='en')
    assert 'Direcciones al revés' in es and 'Hesai → TSMC' in es and 'TSMC → Hesai' in es
    assert 'Reversed directions' in en and 'Direcciones' not in en
    h = markdown_to_html(es)
    assert '<script>' not in h and '&lt;script&gt;' in h and '<table>' in h


def test_g3_confirm_db_obligatorio(db):
    from ontology.db import session_scope
    from ontology.reconcile import apply_plan, ReconcileError
    with session_scope() as s:
        before = _counts(s)
    for bad in (None, '', 'railway-otra'):
        with pytest.raises(ReconcileError):
            apply_plan(session_scope, _snap(), confirm_db=bad)
    with session_scope() as s:
        assert _counts(s) == before


def test_g3_aplicar_rollback_ida_y_vuelta(db):
    from ontology.db import session_scope
    from ontology.service import get_object
    from ontology.reconcile import apply_plan, build_plan, rollback_run, ReconcileError
    snap = _snap()
    with session_scope() as s:
        name = _dbname(s)
        original = _state(s)
        ev0, lk0 = _counts(s)

    # ── corrida 1: lo seguro (alias + duplicados)
    r1 = apply_plan(session_scope, snap, confirm_db=name)
    assert r1['applied'] == {'alias': 1, 'duplicates': 1}
    with session_scope() as s:
        st1 = _state(s)
        assert get_object(s, 'Mobileye_Auto').properties.get('merged_into') == 'Mobileye'
        assert st1[('TSMC', 'Nvidia', 'fab', 6.0)] == 1
        assert st1[('Mobileye', 'TSMC', 'supply', 2.0)] == 1 and not any('Mobileye_Auto' in k[:2] for k in st1)
        assert _replay_state(s) == st1, 'replay desde eventos == tablas'
        sm = build_plan(s, snap)['summary']
        assert (sm['alias'], sm['duplicates'], sm['direction']) == (0, 0, 2)
        ev1, lk1 = _counts(s)
        assert ev1 > ev0 and lk1 >= lk0, 'append-only: eventos y filas solo crecen'

    # ── corrida 2: lo que necesita OK (direcciones, pesos, faltantes, sobrantes)
    r2 = apply_plan(session_scope, snap, include=['direction', 'variants', 'missing', 'extra'], confirm_db=name)
    assert r2['applied'] == {'direction': 2, 'variants': 1, 'missing': 1, 'extra': 1}
    with session_scope() as s:
        st2 = _state(s)
        assert all(v == 0 for k, v in build_plan(s, snap)['summary'].items() if k in
                   ('alias', 'duplicates', 'direction', 'variants', 'missing', 'extra'))
        genesis_in_catalog = {k for k in st2 if k[0] in {'TSMC', 'Nvidia', 'Apple', 'Mobileye', 'Hesai', 'Meta'}
                              and k[2] in ('fab', 'supply', 'partner') and k[0] != 'Qualcomm'}
        assert genesis_in_catalog == {('TSMC', 'Nvidia', 'fab', 6.0), ('TSMC', 'Apple', 'fab', 6.0),
                                      ('TSMC', 'Mobileye', 'supply', 2.0), ('TSMC', 'Hesai', 'supply', 2.0),
                                      ('TSMC', 'Meta', 'fab', 4.0)}
        assert all(v == 1 for v in st2.values()), st2
        # lo que estaba fuera de alcance sigue intacto
        for k in (('Qualcomm', 'Nvidia', 'partner', None), ('WikiCo', 'Nvidia', 'supply', 3.0), ('Factor1', 'Nvidia', 'affects', 2.0)):
            assert st2[k] == 1
        assert _replay_state(s) == st2
        # time-travel: en 2010 la dirección vieja tampoco aparece (corrección retroactiva)
        from ontology.service import as_of_graph
        g2010 = {(l['source'], l['target']) for l in as_of_graph(s, '2010-01-01')['links']}
        assert ('Hesai', 'TSMC') not in g2010 and ('TSMC', 'Hesai') in g2010

    # ── deshacer corrida 2 → vuelve al estado tras la corrida 1
    with session_scope() as s:
        with pytest.raises(ReconcileError):
            rollback_run(s, r2['run_id'], confirm_db='otra')
    with session_scope() as s:
        with pytest.raises(ReconcileError, match='posteriores'):
            rollback_run(s, r1['run_id'], confirm_db=name)       # de la más nueva a la más vieja
    with session_scope() as s:
        rb2 = rollback_run(s, r2['run_id'], confirm_db=name)
        assert rb2['links_reopened'] == 4 and rb2['links_retracted'] == 3   # 2 dir + 1 peso + 1 sobra · 2 dir + 1 faltante
    with session_scope() as s:
        assert _state(s) == st1 and _replay_state(s) == st1

    # ── deshacer corrida 1 → vuelve al estado ORIGINAL (con su alias y su duplicado)
    with session_scope() as s:
        rollback_run(s, r1['run_id'], confirm_db=name)
    with session_scope() as s:
        assert _state(s) == original and _replay_state(s) == original
        assert not get_object(s, 'Mobileye_Auto').properties.get('merged_into')
    with session_scope() as s:
        with pytest.raises(ReconcileError, match='ya fue deshecha'):
            rollback_run(s, r1['run_id'], confirm_db=name)
        ev_end, lk_end = _counts(s)
        assert ev_end > ev1 and lk_end >= lk1, 'deshacer también es append-only'


def test_g3_api_plan_lectura_y_apply_con_pin(db, monkeypatch):
    import server
    from core import pin
    from core import http as _h
    pin._reset_for_tests(); _h._rate_buckets.clear()
    monkeypatch.setenv('TRADE_PIN', 'pin-g3-1234')
    server.app.config['TESTING'] = True
    c = server.app.test_client()
    r = c.get('/api/ontology/reconcile/plan?summary=1&fresh=1')
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    j = r.get_json()
    assert j['db'] and 'summary' in j and j['default_apply'] == ['alias', 'duplicates']
    h = c.get('/api/ontology/reconcile/plan?format=html&lang=en')
    assert h.status_code == 200 and 'text/html' in h.content_type and b'Graph review' in h.data
    assert c.post('/api/ontology/reconcile/apply', json={'actor': 'x', 'confirm_db': j['db']}).status_code == 401
    r2 = c.post('/api/ontology/reconcile/apply', json={'actor': 'fabrizio', 'confirm_db': 'otra-base'},
                headers={'X-Trade-Pin': 'pin-g3-1234'})
    assert r2.status_code == 400 and 'confirm-db' in r2.get_json()['error']
    r3 = c.post('/api/ontology/reconcile/apply', json={'actor': 'fabrizio', 'confirm_db': j['db'], 'include': ['bogus']},
                headers={'X-Trade-Pin': 'pin-g3-1234'})
    assert r3.status_code == 400
