"""tests/test_bitemporal_review.py — revisión del paso 23 (G(t, κ)): tres hallazgos reproducidos y corregidos.

  1. props_at plegaba por VALIDEZ: una corrección retroactiva registrada DESPUÉS de una actualización con
     valid_from más nuevo quedaba tapada → G(ahora, κ=ahora) ≠ la fila materializada / el motor vivo.
     Ahora pliega en orden de REGISTRO (el de `_materialize`).
  2. Known.key() reducía un κ ISO a su versión: un evento económico SIN versión (huérfano: contenedor viejo,
     guion sin el hook) hacía que dos instantes con la misma versión compartieran clave → la LRU AsOf y el
     índice de nodos servían el grafo equivocado. Ahora la clave lleva la marca de huérfanos.
  3. κ = ahora sin as_of pasaba por el replay de VALIDEZ en utcnow: un vínculo con ventana (valid_to futuro) o
     fechado a futuro hacía que known_at=now ≠ el grafo vivo. Ahora t=None = semántica de la TABLA.
"""
import os
import sys
import time
from datetime import datetime, timezone

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')


def _ev(s, et, payload, oid, tgt=None, vf='2000-01-01', vt=None):
    from ontology.service import apply_event
    return apply_event(s, et, payload, valid_from=vf, valid_to=vt, source='test', actor='pytest',
                       object_id=oid, target_id=tgt)


def _clock():
    from sqlalchemy import text

    from ontology.db import session_scope
    with session_scope() as s:
        return s.execute(text('SELECT clock_timestamp()')).scalar()


def _fresh():
    from core.hotviews import registry
    from core.hotviews.views import asof
    from matrix import engine as E
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    registry.reset()
    asof.reset()
    getattr(E, '_CACHE', {}).clear()


def test_correccion_retroactiva_registrada_despues_manda_como_en_la_tabla():
    from core.hotviews.views import asof
    from matrix import engine as E
    from ontology import bitemporal
    from ontology.db import session_scope
    from ontology.models import ObjectRecord
    _fresh()
    with session_scope() as s:
        for n in ('RV_A', 'RV_B'):
            _ev(s, 'ObjectCreated', {'label': n, 'type': 'Company', 'properties': {}}, n)
        _ev(s, 'ObjectCreated', {'label': 'F', 'type': 'Factor', 'properties': {'severity': 3.0}}, 'RV_F')
        _ev(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 3}, 'RV_A', 'RV_B')
        _ev(s, 'LinkCreated', {'rel_type': 'affects', 'weight': 0.5}, 'RV_F', 'RV_B')
    with session_scope() as s:            # tipo ActivarFactor: valid_from = ahora
        _ev(s, 'ObjectUpdated', {'properties': {'severity': 7.0}}, 'RV_F', vf=datetime.now(timezone.utc))
    with session_scope() as s:            # corrección posterior, retroactiva
        _ev(s, 'ObjectUpdated', {'properties': {'severity': 8.0}}, 'RV_F', vf='2001-01-01')
    with session_scope() as s:
        assert s.get(ObjectRecord, 'RV_F').properties['severity'] == 8.0
        live = [(f['id'], f['severity']) for f in E.active_factors(s)]
        k = bitemporal.now_known(s)
        assert [(f['id'], f['severity']) for f in E.active_factors(s, known=k)] == live == [('RV_F', 8.0)]
        assert bitemporal.props_at(s, ids=['RV_F'], known=k)['RV_F']['properties']['severity'] == 8.0
        # en 2000-06 la corrección (desde 2001) todavía no regía
        assert bitemporal.props_at(s, ids=['RV_F'], t=datetime(2000, 6, 1, tzinfo=timezone.utc),
                                   known=k)['RV_F']['properties']['severity'] == 3.0
        data = asof.load(s, None, k)                  # la vista AsOf con κ = ahora: la misma severidad
        assert [(f['id'], f['severity']) for f in data.factors] == [('RV_F', 8.0)]


def test_huerfano_sin_version_separa_la_clave_de_dos_instantes():
    from core.hotviews.views import asof
    from matrix import engine as E
    from ontology import bitemporal
    from ontology.db import session_scope
    from ontology.service import as_of_graph
    _fresh()
    with session_scope() as s:
        for n in ('OR_A', 'OR_B', 'OR_C'):
            _ev(s, 'ObjectCreated', {'label': n, 'type': 'Company', 'properties': {}}, n)
        _ev(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 3}, 'OR_A', 'OR_B')
    ts1 = _clock()
    time.sleep(0.02)
    with session_scope() as s:            # escritor SIN el hook de versión (contenedor viejo durante un despliegue)
        _ev(s, 'ObjectCreated', {'label': 'OR_D', 'type': 'Company', 'properties': {}}, 'OR_D')
        _ev(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 5}, 'OR_B', 'OR_C')
        _ev(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 5}, 'OR_D', 'OR_A')
        s.info.pop('kh_touched', None)
    time.sleep(0.02)
    ts2 = _clock()
    with session_scope() as s:
        k1, k2 = bitemporal.resolve(s, ts1), bitemporal.resolve(s, ts2)
        assert k1.gv == k2.gv
        assert k1.key() != k2.key()
        assert as_of_graph(s, None, known_at=ts1)['counts']['links'] == 1
        assert as_of_graph(s, None, known_at=ts2)['counts']['links'] == 3
        assert E.node_index(s, known=k1)[1] == ['OR_A', 'OR_B', 'OR_C']
        assert E.node_index(s, known=k2)[1] == ['OR_A', 'OR_B', 'OR_C', 'OR_D']
        # un instante posterior sin huérfanos nuevos comparte clave con ts2 (la caché sigue sirviendo)
        assert bitemporal.resolve(s, _clock()).key() == k2.key()
    asof.reset()
    a1, m1 = asof.get(known_at=ts1.isoformat())
    a2, m2 = asof.get(known_at=ts2.isoformat())
    assert a1.views['graph_core'].ids == ['OR_A', 'OR_B', 'OR_C']
    assert a2.views['graph_core'].ids == ['OR_A', 'OR_B', 'OR_C', 'OR_D'] and m2['cache'] == 'miss'


def test_kappa_ahora_igual_al_vivo_con_vinculos_con_ventana_y_futuros():
    from core.hotviews import source
    from core.hotviews.views import asof
    from matrix import engine as E
    from ontology import bitemporal
    from ontology.db import session_scope
    _fresh()
    with session_scope() as s:
        for n in ('FW_A', 'FW_B', 'FW_C', 'FW_D'):
            _ev(s, 'ObjectCreated', {'label': n, 'type': 'Company', 'properties': {}}, n)
        _ev(s, 'ObjectCreated', {'label': 'F', 'type': 'Factor', 'properties': {'severity': 4.0}}, 'FW_F')
        _ev(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 3}, 'FW_A', 'FW_B', vt='2099-01-01')   # con ventana
        _ev(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 3}, 'FW_B', 'FW_C', vf='2099-01-01')   # a futuro
        _ev(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 2}, 'FW_C', 'FW_D')
        _ev(s, 'LinkCreated', {'rel_type': 'affects', 'weight': 0.5}, 'FW_F', 'FW_C', vf='2099-01-01')
    with session_scope() as s:
        k = bitemporal.now_known(s)
        live, kn = E.build_matrices(s, sparse=False), E.build_matrices(s, known=k, sparse=False)
        for rel in live[0]:
            assert (live[0][rel] == kn[0][rel]).all(), rel
        assert live[0]['supply'][live[1]['FW_B'], live[1]['FW_C']] == 3          # el vivo incluye el futuro
        assert live[0]['supply'][live[1]['FW_A'], live[1]['FW_B']] == 0          # y no el de ventana
        assert ([(f['id'], f['severity'], f['members']) for f in E.active_factors(s)]
                == [(f['id'], f['severity'], f['members']) for f in E.active_factors(s, known=k)])
    pg = source.load_pg()
    asof.reset()
    with session_scope() as s:
        data = asof.load(s, None, bitemporal.now_known(s))
    assert sorted(data.triples) == sorted(pg.triples)
    assert data.ids == pg.ids
    assert ([(f['id'], f['members']) for f in data.factors] == [(f['id'], f['members']) for f in pg.factors])
