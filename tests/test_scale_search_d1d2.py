"""tests/test_scale_search_d1d2.py — EXPANSION_5K E1.8: defectos D-1 y D-2 (requiere Postgres).

D-1: IncorporarEmpresa escribía su vínculo `link_to` con `proposed: True` pero SIN `status: 'proposed'`, y las vistas
     (core/hotviews/source) solo excluyen `status in ('proposed', 'rejected')`: el vínculo entraba VIVO al grafo de
     lectura. Ahora es una propuesta de verdad (igual que las del tensor, confianza 0): existe en la ontología y NO
     aparece en hot.graph() hasta que una persona la confirme.
D-2: la puerta G-BULK no recibía evidencia, tipos de extremos, inversos ni `dated`: 1.000 vínculos con una fuente de
     trust 2 daban 1.000 avisos falsos `link.high_conf_trusted_source`, y `flow_supplier_type` / `inverse_flow_live` /
     `dated_fact_has_source` nunca podían dispararse. Ahora el foco lleva lo mismo que G1 (focus.gather_link).
"""
import os
import sys
from datetime import datetime, timezone

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')

N_EMP = 48                    # 48 × 47 / 2 = 1.128 pares (a < b): sin inversos dentro del lote
HIGH_CONF = 'khr:link.high_conf_trusted_source'
FLOW_SUPPLIER = 'khr:link.flow_supplier_type'
INVERSE = 'khr:link.inverse_flow_live'
DATED = 'khr:link.dated_fact_has_source'


@pytest.fixture(scope='module')
def db():
    from core import governance
    from core.hotviews import hot, registry
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    governance._reset_for_tests()
    assert init_schema(retries=1)
    with session_scope() as s:
        objs = [('TSMC', 'Company'), ('Microsoft', 'Company'), ('Nvidia', 'Company'), ('PERU', 'Country')]
        objs += [(f'EmpD2_{i:02d}', 'Company') for i in range(N_EMP)]
        for oid, t in objs:
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': t, 'properties': {}}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=oid)
        apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 3, 'properties': {'rel_label': 'chips'}},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id='TSMC', target_id='Nvidia')
    yield engine
    registry.reset()
    hot.reset()
    governance._reset_for_tests()
    Base.metadata.drop_all(engine)


def _rules_vigentes():
    from core import governance
    return set(governance.param('ontology.shapes', 'ir')['rules'])


def test_reglas_existen_en_el_ir_vigente(db):
    assert {HIGH_CONF, FLOW_SUPPLIER, INVERSE, DATED} <= _rules_vigentes()


# ── D-1 ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def _fake_suggest(**_kw):
    c = lambda i, sc, side: {'direction': side, 'id': i, 'label': i, 'rel': 'supply', 'score': sc,  # noqa: E731
                             'peers_with_link': 3, 'via': [{'id': 'Nvidia', 'label': 'Nvidia'}]}
    return {'suppliers': [c('TSMC', 0.6, 'supplier')], 'customers': [c('Microsoft', 0.4, 'customer')]}


def test_d1_incorporar_empresa_deja_propuestas_fuera_del_grafo_de_lectura(db, monkeypatch):
    from sqlalchemy import or_, select

    from core.hotviews import builder, hot, registry
    from matrix import tensor
    from ontology.actions import IncorporarEmpresaInput, incorporar_empresa
    from ontology.db import session_scope
    from ontology.models import LinkRecord
    monkeypatch.setattr(tensor, 'suggest_links', _fake_suggest)
    with session_scope() as s:
        r = incorporar_empresa(s, IncorporarEmpresaInput(company_id='NuevaD1', label='Nueva D1 Robotics', cat='fabless',
                                                         link_to='Nvidia', rel_type='supply', razon='prueba D-1'),
                               'pytest')
    assert {(p['from'], p['to']) for p in r['propuestas']} == {('TSMC', 'NuevaD1'), ('NuevaD1', 'Microsoft')}
    # revisión: la respuesta dice que el vínculo QUEDÓ PENDIENTE y con qué id confirmarlo (como ProponerVinculo)
    assert r['link']['status'] == 'proposed' and r['link']['link_id'] and r['link']['rel_type'] == 'supply'
    with session_scope() as s:
        rows = s.scalars(select(LinkRecord).where(or_(LinkRecord.source_id == 'NuevaD1',
                                                      LinkRecord.target_id == 'NuevaD1'))).all()
        got = {(l.source_id, l.target_id): (l.properties or {}) for l in rows}
    assert set(got) == {('NuevaD1', 'Nvidia'), ('TSMC', 'NuevaD1'), ('NuevaD1', 'Microsoft')}
    assert all(p.get('status') == 'proposed' for p in got.values())          # existen, como PROPUESTAS
    assert got[('NuevaD1', 'Nvidia')].get('proposed_by') == 'pytest'
    assert got[('NuevaD1', 'Nvidia')].get('confidence') == 0.0               # el kernel tampoco la cuenta hasta confirmarla
    with session_scope() as s:
        lid = str(s.scalars(select(LinkRecord).where(LinkRecord.source_id == 'NuevaD1',
                                                     LinkRecord.target_id == 'Nvidia')).first().id)
    assert r['link']['link_id'] == lid
    assert got[('TSMC', 'NuevaD1')].get('confidence') == 0.0                  # las del tensor: confianza 0

    monkeypatch.setattr(hot, 'MIN_COVERAGE', 0.0)      # la base de prueba no trae el catálogo: leerla igual
    registry.reset()
    hot.reset()
    try:
        g = builder.build_once()
        view = hot.graph()
        assert view.generation == g.id and view.source == 'pg' and not view.fallback
        assert 'NuevaD1' in view.by_id                                        # la empresa sí está
        pares = {(l['source'], l['target']) for l in view.links}
        assert ('TSMC', 'Nvidia') in pares                                    # control: un vínculo vivo sí aparece
        assert not [p for p in pares if 'NuevaD1' in p]                       # ninguna propuesta en el grafo
        assert view.stats.get('proposed_excluded', 0) >= 3
        # …ni en el kernel: un choque en la empresa nueva no propaga por su propuesta (antes: peso 1 → Nvidia golpeada)
        from core.hotviews.views import impact
        p = impact.impact_payload(g.views['graph_core'], g.views['impact'], 'NuevaD1', top=10) or {}
        assert not p.get('affected') and 'Nvidia' not in [x.get('id') for x in (p.get('victims') or [])], p
    finally:
        registry.reset()
        hot.reset()


# ── D-2 ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def _pares(n):
    ids = [f'EmpD2_{i:02d}' for i in range(N_EMP)]
    out = [(a, b) for i, a in enumerate(ids) for b in ids[i + 1:]]
    return out[:n]


def _lote(n, props):
    return [{'source': a, 'target': b, 'rel_type': 'supply', 'weight': 2, 'properties': dict(props)}
            for a, b in _pares(n)]


def _gate(records, s):
    from sqlalchemy import select

    from ontology.bulk_import import _gate_bulk, validate_bulk_links
    from ontology.models import ObjectRecord
    existing = {r for (r,) in s.execute(select(ObjectRecord.id)).all()}
    accepted, quarantined = validate_bulk_links(records, existing)
    assert not quarantined
    return _gate_bulk(s, accepted, existing, datetime.now(timezone.utc).isoformat())


def _fuente(s, url, kind):
    from ontology.provenance import register_source
    return register_source(s, url, kind=kind, title='prueba D-2', actor='pytest')


def test_d2_mil_vinculos_con_fuente_trust_2_sin_avisos_falsos(db):
    from ontology.bulk_import import import_links_bulk
    from ontology.db import session_scope
    from ontology.models import ObjectRecord
    with session_scope() as s:
        sid = _fuente(s, 'https://www.reuters.com/technology/prueba-d2-trust2', 'press')
        assert s.get(ObjectRecord, sid).properties['trust'] == 2
        out = import_links_bulk(s, _lote(1000, {'confidence': 0.8, 'source_id': sid}), provenance='prueba_d2')
    assert out['created'] == 1000 and out['gate']['checked'] == 1000
    assert out['gate']['by_rule'].get(HIGH_CONF, 0) == 0                      # antes: 1.000 avisos falsos


def test_d2_sin_fuente_o_con_trust_1_la_regla_si_avisa(db):
    """Control: la regla corre de verdad — sin evidencia, o con una fuente de trust 1, cada flujo ≥ 0,5 avisa."""
    from ontology.db import session_scope
    with session_scope() as s:
        sid1 = _fuente(s, 'https://blog.ejemplo-agregador.net/prueba-d2', 'aggregator')
        sin = _gate(_lote(200, {'confidence': 0.8}), s)
        t1 = _gate(_lote(200, {'confidence': 0.8, 'evidenced_by': [sid1]}), s)
        baja = _gate(_lote(200, {'confidence': 0.3}), s)
    assert sin['by_rule'].get(HIGH_CONF) == 200
    assert t1['by_rule'].get(HIGH_CONF) == 200
    assert baja['by_rule'].get(HIGH_CONF, 0) == 0                             # confianza < 0,5: no aplica


def test_d2_pais_como_proveedor_da_un_aviso(db):
    from ontology.db import session_scope
    recs = _lote(20, {}) + [{'source': 'PERU', 'target': 'TSMC', 'rel_type': 'supply', 'weight': 2},
                            {'source': 'PERU', 'target': 'Nvidia', 'rel_type': 'partner', 'weight': 1}]   # no flujo
    with session_scope() as s:
        rep = _gate(recs, s)
    assert rep['by_rule'].get(FLOW_SUPPLIER) == 1


def test_d2_inversos_y_hechos_fechados(db):
    from ontology.db import session_scope
    with session_scope() as s:
        sid = _fuente(s, 'https://www.reuters.com/technology/prueba-d2-fechado', 'press')
        inv_base = _gate([{'source': 'Nvidia', 'target': 'TSMC', 'rel_type': 'supply', 'weight': 2}], s)
        inv_lote = _gate([{'source': 'Microsoft', 'target': 'Nvidia', 'rel_type': 'cloud', 'weight': 2},
                          {'source': 'Nvidia', 'target': 'Microsoft', 'rel_type': 'cloud', 'weight': 2},
                          {'source': 'Nvidia', 'target': 'Microsoft', 'rel_type': 'supply', 'weight': 2}], s)
        fechado = _gate([{'source': 'TSMC', 'target': 'Microsoft', 'rel_type': 'supply', 'weight': 2,
                          'properties': {'since': '2024-03-01'}},
                         {'source': 'Nvidia', 'target': 'Microsoft', 'rel_type': 'supply', 'weight': 2,
                          'properties': {'since': '2024-03-01'}, 'evidenced_by': [sid]}], s)
    assert inv_base['by_rule'].get(INVERSE) == 1             # TSMC → Nvidia vigente en la base
    assert inv_lote['by_rule'].get(INVERSE) == 2             # A→B y B→A del mismo tipo en el lote: los dos
    assert fechado['by_rule'].get(DATED) == 1                # el fechado SIN fuente; el que cita una fuente no


def test_d3_la_fuente_que_la_puerta_acredita_es_la_que_se_escribe(db):
    """Revisión D-2/D-3: antes la puerta acreditaba `evidenced_by` del registro y la escritura lo tiraba (evento sin
    source_id ni confianza): G1, el replay y la auditoría no lo veían. Ahora la fuente PRINCIPAL (la citada con más
    trust) va al evento, la lista queda en el vínculo y la confianza declarada también va al evento."""
    from sqlalchemy import select

    from ontology.bulk_import import import_links_bulk
    from ontology.db import session_scope
    from ontology.models import Event, LinkRecord
    with session_scope() as s:
        t1 = _fuente(s, 'https://blog.ejemplo-agregador.net/prueba-d3', 'aggregator')
        t2 = _fuente(s, 'https://www.reuters.com/technology/prueba-d3', 'press')
        out = import_links_bulk(s, [{'source': 'Microsoft', 'target': 'TSMC', 'rel_type': 'license', 'weight': 2,
                                     'evidenced_by': [t1, t2], 'properties': {'confidence': 0.9}}], provenance='prueba_d3')
    assert out['created'] == 1 and out['gate']['by_rule'].get(HIGH_CONF, 0) == 0
    with session_scope() as s:
        l = s.scalars(select(LinkRecord).where(LinkRecord.source_id == 'Microsoft', LinkRecord.target_id == 'TSMC',
                                               LinkRecord.rel_type == 'license')).first()
        e = s.get(Event, l.event_id)
        assert e.source_id == t2 and abs(e.confidence - 0.9) < 1e-9              # la de trust 2, no la primera citada
        assert l.properties['evidenced_by'] == [t1, t2] and l.properties['source'] == 'prueba_d3'
    # un registro SIN `source` usa `source_id` como extremo de origen: no es una fuente citada
    from ontology.bulk_import import evidence_ids
    assert evidence_ids({'source_id': 'TSMC', 'target_id': 'Nvidia'}) == []


def test_d2_evidencia_se_normaliza_en_el_registro():
    from ontology.bulk_import import evidence_ids, validate_bulk_links
    assert evidence_ids({'evidenced_by': ['src_a', 'src_b'], 'source_id': 'src_a',
                         'properties': {'source_id': 'src_c', 'evidenced_by': 'src_b'}}) == ['src_a', 'src_b', 'src_c']
    assert evidence_ids({'properties': None}) == []
    acc, _q = validate_bulk_links([{'source': 'A', 'target': 'B', 'rel_type': 'supply', 'source_id': 'src_x'}],
                                  {'A', 'B'})
    assert acc[0]['evidenced_by'] == ['src_x']
