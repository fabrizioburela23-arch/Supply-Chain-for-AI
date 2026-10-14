"""tests/test_import_fast_path.py — EXPANSION_5K E2.8: la escritura por bloques (ontology/bulk_import.write_events_fast)
deja los MISMOS eventos que apply_event, campo a campo (tipo, extremos, payload con dedup_of, valid_from/valid_to
reales, source_id, confidence, release_hash) y la misma materialización (objects/links); los vínculos llevan su
fecha real (D-3: un vínculo con start 2021-07 nace en 2021-07; sin start, en GENESIS con valid_from_known false);
21.000 eventos entran en ≤ 30 s (lento: KH_SCALE=1). Requiere DATABASE_URL (base desechable, sin migrar el catálogo)."""
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('KHIPU_SCHEDULER', 'off')

DATABASE_URL = os.getenv('DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
SCALE = os.getenv('KH_SCALE') == '1'


@pytest.fixture(scope='module')
def db():
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    with session_scope() as s:
        for oid in ('FA', 'FB', 'FC', 'FD'):
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company', 'properties': {'cat': 'memory'}},
                        valid_from='2000-01-01', source='pytest', actor='pytest', object_id=oid)
        apply_event(s, 'ObjectCreated', {'label': 'Fuente', 'type': 'Source', 'properties': {'url': 'https://s.com/a', 'trust': 3,
                                                                                            'kind': 'primary'}},
                    valid_from='2000-01-01', source='pytest', actor='pytest', object_id='src_fast0001')
    yield engine
    Base.metadata.drop_all(engine)


def _events(prefix):
    return [
        {'event_type': 'ObjectCreated', 'object_id': f'{prefix}N1', 'payload': {'label': 'N1', 'type': 'Company',
                                                                                'properties': {'cat': 'memory', 'country': 'Corea'}},
         'valid_from': '2010-03-01', 'source_id': 'src_fast0001'},
        {'event_type': 'ObjectUpdated', 'object_id': 'FA', 'payload': {'properties': {'hq_country': 'US', prefix + 'k': 1},
                                                                       'properties_prev': None},
         'valid_from': '2026-10-14T00:00:00+00:00'},
        {'event_type': 'LinkCreated', 'object_id': f'{prefix}N1', 'target_id': 'FB',
         'payload': {'rel_type': 'supply', 'weight': 4.0, 'properties': {'rel_label': 'celdas', 'confidence': 0.8, 'since': '2021-07'}},
         'valid_from': '2021-07-01T00:00:00+00:00', 'source_id': 'src_fast0001', 'confidence': 0.8},
        {'event_type': 'LinkCreated', 'object_id': f'{prefix}N1', 'target_id': 'FC',
         'payload': {'rel_type': 'supply', 'weight': 2.0, 'properties': {'rel_label': 'sin fecha', 'confidence': 0.6}},
         'valid_from': '2000-01-01', 'confidence': 0.6},
        {'event_type': 'LinkCreated', 'object_id': f'{prefix}N1', 'target_id': 'FD',
         'payload': {'rel_type': 'supply', 'weight': 2.0, 'properties': {'rel_label': 'terminado'}},
         'valid_from': '2018-01-01', 'valid_to': '2020-07-01'},
        # duplicado EXACTO del segundo vínculo → dedup_of (no abre fila), en los dos caminos
        {'event_type': 'LinkCreated', 'object_id': f'{prefix}N1', 'target_id': 'FC',
         'payload': {'rel_type': 'supply', 'weight': 2.0, 'properties': {'rel_label': 'sin fecha', 'confidence': 0.6}},
         'valid_from': '2000-01-01', 'confidence': 0.6},
    ]


def _norm_event(e, prefix):
    p = dict(e.payload or {})
    props = dict(p.get('properties') or {})
    for k in ('dedup_of', 'dedup_event_id'):
        if k in props:
            props[k] = '<dedup>'
    props = {k.replace(prefix, '@'): v for k, v in props.items()}
    if isinstance(p.get('properties_prev'), dict):
        p['properties_prev'] = {k.replace(prefix, '@'): v for k, v in p['properties_prev'].items()}
    p['properties'] = props
    return (e.event_type, (e.object_id or '').replace(prefix, '@'), e.target_id, p,
            e.valid_from.isoformat(), e.valid_to.isoformat() if e.valid_to else None, e.source_id, e.confidence, e.release_hash)


def test_mismos_eventos_que_apply_event_campo_a_campo(db):
    from sqlalchemy import select

    from ontology.bulk_import import write_events_fast
    from ontology.db import session_scope
    from ontology.models import Event, LinkRecord, ObjectRecord
    from ontology.service import apply_event
    with session_scope() as s:
        for ev in _events('slow_'):
            apply_event(s, ev['event_type'], ev['payload'], valid_from=ev['valid_from'], source='slow', actor='pytest',
                        object_id=ev.get('object_id'), target_id=ev.get('target_id'), valid_to=ev.get('valid_to'),
                        source_id=ev.get('source_id'), confidence=ev.get('confidence'))
    with session_scope() as s:
        res = write_events_fast(s, _events('fast_'), source='fast', actor='pytest')
        assert len(res['ids']) == 6 and res['links_created'] == 3 and res['links_dedup'] == 1
        assert res['objects_created'] == 1 and res['objects_updated'] == 1 and res['slow_path'] == 0
    with session_scope() as s:
        slow = [_norm_event(e, 'slow_') for e in s.scalars(select(Event).where(Event.source == 'slow').order_by(Event.recorded_at, Event.id)).all()]
        fast = [_norm_event(e, 'fast_') for e in s.scalars(select(Event).where(Event.source == 'fast').order_by(Event.recorded_at, Event.id)).all()]
        # apply_event no guarda properties_prev (lo pone el camino rápido para poder deshacer): se compara sin esa clave
        slow = [(t, o, g, {k: v for k, v in p.items() if k != 'properties_prev'}, *rest) for t, o, g, p, *rest in slow]
        fast = [(t, o, g, {k: v for k, v in p.items() if k != 'properties_prev'}, *rest) for t, o, g, p, *rest in fast]
        assert slow == fast
        for prefix in ('slow_', 'fast_'):
            o = s.get(ObjectRecord, f'{prefix}N1')
            assert o is not None and o.properties.get('country') == 'Corea' and o.type == 'Company'
            links = s.scalars(select(LinkRecord).where(LinkRecord.source_id == f'{prefix}N1')).all()
            by = {l.target_id: l for l in links}
            assert set(by) == {'FB', 'FC', 'FD'} and len(links) == 3           # el duplicado NO abrió fila
            assert by['FB'].valid_from.isoformat().startswith('2021-07-01') and by['FD'].valid_to.isoformat().startswith('2020-07-01')
            assert by['FB'].event_id is not None
        fa = s.get(ObjectRecord, 'FA')
        assert fa.properties.get('hq_country') == 'US' and fa.properties.get('fast_k') == 1 and fa.properties.get('slow_k') == 1
        prev = next(e for e in s.scalars(select(Event).where(Event.source == 'fast', Event.event_type == 'ObjectUpdated')).all())
        assert prev.payload['properties_prev'] == {'hq_country': 'US', 'fast_k': None}   # el lento ya había puesto US


def test_valid_from_obligatoria_y_tipo_valido(db):
    from ontology.bulk_import import write_events_fast
    from ontology.db import session_scope
    from ontology.service import OntologyError
    with pytest.raises(OntologyError), session_scope() as s:
        write_events_fast(s, [{'event_type': 'ObjectCreated', 'object_id': 'X', 'payload': {}}], source='t', actor='t')
    with pytest.raises(OntologyError), session_scope() as s:
        write_events_fast(s, [{'event_type': 'Inventado', 'object_id': 'X', 'payload': {}, 'valid_from': '2020-01-01'}],
                          source='t', actor='t')


def test_la_fecha_del_registro_manda_en_import_links_bulk(db):
    from sqlalchemy import select

    from ontology.bulk_import import import_links_bulk
    from ontology.db import session_scope
    from ontology.models import LinkRecord
    with session_scope() as s:
        res = import_links_bulk(s, [{'source': 'FA', 'target': 'FB', 'rel_type': 'supply', 'weight': 1,
                                     'external_id': 'd3-1', 'valid_from': '2021-07-01', 'valid_to': '2022-01-01'}], 'pytest_d3')
        assert res['created'] == 1
    with session_scope() as s:
        l = next(x for x in s.scalars(select(LinkRecord).where(LinkRecord.source_id == 'FA', LinkRecord.target_id == 'FB')).all()
                 if (x.properties or {}).get('external_id') == 'd3-1')
        assert l.valid_from.isoformat().startswith('2021-07-01') and l.valid_to.isoformat().startswith('2022-01-01')


@pytest.mark.skipif(not SCALE, reason='lento: KH_SCALE=1 (21.000 eventos)')
def test_21k_eventos_en_menos_de_30_s(db):
    from ontology.bulk_import import write_events_fast
    from ontology.db import session_scope
    evs = []
    n_nodes = 3000
    for i in range(n_nodes):
        evs.append({'event_type': 'ObjectCreated', 'object_id': f'S{i:05d}', 'payload': {'label': f'S{i}', 'type': 'Company',
                                                                                        'properties': {'cat': 'memory'}},
                    'valid_from': '2000-01-01'})
    k = 0
    while len(evs) < 21000:
        a, b = k % n_nodes, (k * 7 + 1) % n_nodes
        if a != b:
            evs.append({'event_type': 'LinkCreated', 'object_id': f'S{a:05d}', 'target_id': f'S{b:05d}',
                        'payload': {'rel_type': 'supply', 'weight': 1 + k % 6, 'properties': {'rel_label': 'x', 'confidence': 0.7}},
                        'valid_from': '2021-01-01', 'confidence': 0.7})
        k += 1
    t0 = time.perf_counter()
    with session_scope() as s:
        res = write_events_fast(s, evs, source='scale', actor='pytest', chunk=1000)
    secs = time.perf_counter() - t0
    assert len(res['ids']) == 21000 and res['links_created'] + res['links_dedup'] == 21000 - n_nodes
    assert secs <= 30, f'{secs:.1f} s para 21.000 eventos'
