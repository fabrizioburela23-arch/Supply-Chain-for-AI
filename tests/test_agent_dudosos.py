"""tests/test_agent_dudosos.py — Phase 1 · M2: matches de baja confianza.

Antes, cuando el tejedor de hiperaristas (un LLM) nombraba una empresa de forma
aproximada ("Hynix", "Samsung Elec"), el nombre no pasaba el umbral de
ESCRITURA y se descartaba EN SILENCIO: el factor se creaba sin esa empresa y
nadie se enteraba. Ahora esos nombres viajan en la propuesta como `dudosos`
(con id sugerido, score y método), y la propuesta queda por debajo del umbral
de auto-aplicación para que decida un humano.

Requiere Postgres (DATABASE_URL). La red y la IA se simulan.
"""
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
        for oid, lbl in [('TSMC', 'TSMC'), ('Nvidia', 'Nvidia'), ('SKHynix', 'SK Hynix'),
                         ('Samsung', 'Samsung Electronics')]:
            apply_event(s, 'ObjectCreated', {'label': lbl, 'type': 'Company', 'properties': {}},
                        valid_from='2000-01-01', source='test', actor='pytest', object_id=oid)
    yield
    Base.metadata.drop_all(engine)


class _Resp:
    ok = True
    def json(self):
        return {'articles': [{'title': 'Escasez de HBM golpea a toda la cadena'}]}


def _proponer(monkeypatch, empresas):
    import requests
    import core.ai
    from ontology.db import session_scope
    from ontology.agents import TejedorHiperaristas
    from ontology.models import ObjectRecord
    monkeypatch.setattr(requests, 'get', lambda *a, **k: _Resp())
    monkeypatch.setattr(core.ai, '_ai_complete', lambda *a, **k: (
        '{"factor": {"label": "Escasez HBM prueba %d", "severity": 4, "empresas": %s, '
        '"resumen": "falta memoria HBM"}}' % (len(empresas), str(empresas).replace("'", '"')), 'fake'))
    with session_scope() as s:
        c = s.get(ObjectRecord, 'Nvidia')
        return TejedorHiperaristas().propose(s, {'company': c})


def test_nombres_dudosos_no_se_pierden_en_silencio(db, monkeypatch):
    p = _proponer(monkeypatch, ['TSMC', 'Hynix', 'Samsung Elec'])
    assert p and p['action_type'] == 'CrearFactor'
    # solo lo SEGURO entra a affects
    assert set(p['payload']['affects']) == {'Nvidia', 'TSMC'}
    dud = {d['id']: d for d in p['payload']['dudosos']}
    assert set(dud) == {'SKHynix', 'Samsung'}
    assert dud['SKHynix']['nombre'] == 'Hynix' and dud['SKHynix']['score'] < 85
    assert dud['SKHynix']['method']
    # y se lo decimos al humano en la explicación
    assert 'SK Hynix' in p['explanation'] and '¿También?' in p['explanation']
    # por debajo del umbral de auto-aplicación
    from ontology.agents import AUTO_MIN_CONFIDENCE
    assert p['confidence'] < AUTO_MIN_CONFIDENCE


def test_sin_dudosos_la_propuesta_queda_igual(db, monkeypatch):
    p = _proponer(monkeypatch, ['TSMC', 'SK Hynix'])
    assert p and set(p['payload']['affects']) == {'Nvidia', 'TSMC', 'SKHynix'}
    assert p['payload']['dudosos'] == []
    assert p['confidence'] == 0.6
