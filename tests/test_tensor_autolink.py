"""Ontología nivel 2: al incorporar una empresa, sus proveedores/clientes probables quedan PROPUESTOS
(confianza 0: no pesan en el riesgo hasta que una persona los confirma). Requiere Postgres."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv('DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')


@pytest.fixture(scope='module')
def db():
    from ontology.db import init_schema, _get_engine, session_scope
    from ontology.models import Base
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    init_schema()
    with session_scope() as s:
        for oid in ('TSMC', 'Microsoft'):
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company', 'properties': {}},
                        valid_from='2000-01-01', source='test', actor='pytest', object_id=oid)
    yield
    Base.metadata.drop_all(engine)


def _fake(**kw):
    c = lambda i, sc, side: {'direction': side, 'id': i, 'label': i, 'rel': 'supply', 'score': sc,  # noqa: E731
                             'peers_with_link': 3, 'via': [{'id': 'Nvidia', 'label': 'Nvidia'}]}
    return {'suppliers': [c('TSMC', 0.6, 'supplier'), c('NoExiste', 0.5, 'supplier')],
            'customers': [c('Microsoft', 0.4, 'customer'), c('TSMC', 0.05, 'customer')]}


def test_incorporar_empresa_propone_vinculos_sin_peso(db, monkeypatch):
    from matrix import engine as E
    from matrix import tensor
    from ontology.actions import IncorporarEmpresaInput, incorporar_empresa
    from ontology.db import session_scope
    monkeypatch.setattr(tensor, 'suggest_links', _fake)
    with session_scope() as s:
        r = incorporar_empresa(s, IncorporarEmpresaInput(company_id='NuevaGPU', label='Nueva GPU', cat='fabless',
                                                         razon='prueba'), 'pytest')
    got = {(p['from'], p['to']) for p in r['propuestas']}
    assert got == {('TSMC', 'NuevaGPU'), ('NuevaGPU', 'Microsoft')}   # sin la inexistente ni la de puntaje bajo
    with session_scope() as s:
        mats, idx, _ = E.build_matrices(s, sparse=True)
        assert mats['supply'][idx['TSMC'], idx['NuevaGPU']] == 0          # propuesta = 0 en el riesgo


def test_sin_auto_proponer_no_propone(db, monkeypatch):
    from matrix import tensor
    from ontology.actions import IncorporarEmpresaInput, incorporar_empresa
    from ontology.db import session_scope
    monkeypatch.setattr(tensor, 'suggest_links', _fake)
    with session_scope() as s:
        r = incorporar_empresa(s, IncorporarEmpresaInput(company_id='OtraGPU', label='Otra GPU', razon='x',
                                                         auto_proponer=False), 'pytest')
    assert r['propuestas'] == []
