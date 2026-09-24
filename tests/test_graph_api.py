"""tests/test_graph_api.py — Phase 1 · M5: completar la Graph API.

Cierra el criterio de éxito del spec: buscar una empresa desde el servidor,
abrir un evento con su procedencia, y ver en UN solo hilo qué le ha pasado a
una entidad (eventos del grafo + noticias), con de dónde salió cada cosa.

Requiere Postgres real (DATABASE_URL).
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
    from ontology.provenance import register_source
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    init_schema()
    with session_scope() as s:
        apply_event(s, 'ObjectCreated',
                    {'label': 'ACME Corp', 'type': 'Company', 'properties': {'mkt': 'ACME'}},
                    valid_from='2020-01-01', source='test', actor='pytest', object_id='ACME')
        apply_event(s, 'ObjectCreated',
                    {'label': 'Proveedora SA', 'type': 'Company', 'properties': {}},
                    valid_from='2020-01-01', source='test', actor='pytest', object_id='Prov')
        # un vínculo y un cambio de datos, con fuente citable
        apply_event(s, 'LinkCreated', {'rel_type': 'supply'}, valid_from='2021-06-01',
                    source='test', actor='pytest', object_id='Prov', target_id='ACME')
        sid = register_source(s, 'https://www.sec.gov/Archives/acme-10k.htm',
                              title='ACME 10-K', publisher='SEC', actor='pytest')
        apply_event(s, 'ObjectUpdated', {'properties': {'empleados': 5000, 'margin': 0.31}},
                    valid_from='2023-03-15', source='manual', actor='ana',
                    object_id='ACME', source_id=sid, confidence=0.95)
    yield
    Base.metadata.drop_all(engine)


def _c():
    import server
    os.environ.setdefault('SECRET_KEY', 'test')
    server.app.config['TESTING'] = True
    return server.app.test_client()


# ── Búsqueda ────────────────────────────────────────────────────────────────

def test_busqueda_encuentra_por_texto(db):
    r = _c().get('/api/ontology/search?q=ACME')
    assert r.status_code == 200
    d = r.get_json()
    assert d['count'] >= 1
    assert any(x['id'] == 'ACME' for x in d['results'])
    assert all('match' in x for x in d['results'])   # dice CÓMO lo encontró


def test_busqueda_exige_query(db):
    assert _c().get('/api/ontology/search').status_code == 400
    assert _c().get('/api/ontology/search?q=  ').status_code == 400


def test_busqueda_filtra_por_tipo(db):
    d = _c().get('/api/ontology/search?q=a&type=Source').get_json()
    assert all(x['type'] == 'Source' for x in d['results'])


def test_busqueda_sin_resultados_no_inventa(db):
    d = _c().get('/api/ontology/search?q=zzzz-no-existe-nada').get_json()
    assert d['count'] == 0 and d['results'] == []


# ── Evento concreto ─────────────────────────────────────────────────────────

def test_evento_trae_su_procedencia(db):
    from ontology.db import session_scope
    from ontology.models import Event
    from sqlalchemy import select

    with session_scope() as s:
        ev = s.scalars(select(Event).where(Event.source_id.isnot(None))).first()
        eid = str(ev.id)

    d = _c().get(f'/api/ontology/events/{eid}').get_json()
    assert d['id'] == eid
    assert d['confidence'] == 0.95
    assert d['source'] and 'sec.gov' in d['source']['url']
    assert d['actor'] == 'ana'
    # las dos líneas de tiempo, visibles por separado
    assert d['valid_from'].startswith('2023-03-15')
    assert d['recorded_at']


def test_evento_inexistente_o_id_malo(db):
    import uuid
    c = _c()
    assert c.get('/api/ontology/events/no-es-un-uuid').status_code == 400
    assert c.get(f'/api/ontology/events/{uuid.uuid4()}').status_code == 404


# ── Línea de tiempo ─────────────────────────────────────────────────────────

def test_timeline_fusiona_y_ordena_por_validez(db):
    d = _c().get('/api/ontology/objects/ACME/timeline').get_json()
    assert d['count'] >= 3
    fechas = [e['at'] for e in d['timeline'] if e['at']]
    assert fechas == sorted(fechas, reverse=True)   # más reciente primero

    tipos = {e['event_type'] for e in d['timeline']}
    assert 'ObjectCreated' in tipos
    assert 'ObjectUpdated' in tipos
    assert 'LinkCreated' in tipos     # el vínculo ENTRANTE también cuenta


def test_timeline_arrastra_la_procedencia(db):
    d = _c().get('/api/ontology/objects/ACME/timeline').get_json()
    con_fuente = [e for e in d['timeline'] if e.get('source')]
    assert con_fuente, 'ningún evento llegó con su fuente'
    assert any('sec.gov' in (e['source'].get('url') or '') for e in con_fuente)
    # y los que NO tienen evidencia lo dicen con un hueco, no con relleno
    sin_fuente = [e for e in d['timeline'] if not e.get('source')]
    assert all(e.get('url') is None for e in sin_fuente)


def test_timeline_es_bilingue(db):
    es = _c().get('/api/ontology/objects/ACME/timeline?lang=es').get_json()
    en = _c().get('/api/ontology/objects/ACME/timeline?lang=en').get_json()

    def titulo(d, tipo):
        return next(e['title'] for e in d['timeline'] if e['event_type'] == tipo)

    assert titulo(es, 'ObjectCreated') == 'Entró al grafo'
    assert titulo(en, 'ObjectCreated') == 'Entered the graph'
    # un idioma desconocido cae a español en vez de romperse
    raro = _c().get('/api/ontology/objects/ACME/timeline?lang=zz').get_json()
    assert raro['count'] == es['count']


def test_timeline_muestra_ambas_lineas_temporales(db):
    """`at` es cuándo fue cierto; `recorded_at`, cuándo lo supimos. La
    diferencia es el corazón del modelo, y a veces es lo interesante."""
    d = _c().get('/api/ontology/objects/ACME/timeline').get_json()
    upd = next(e for e in d['timeline'] if e['event_type'] == 'ObjectUpdated')
    assert upd['at'].startswith('2023-03-15')
    assert upd['recorded_at'] and upd['recorded_at'] > upd['at']
    assert upd['detail']            # nombra los campos que cambiaron
    assert upd['actor'] == 'ana'


def test_timeline_incluye_noticias_y_se_pueden_excluir(db):
    from ontology.db import session_scope
    from ontology.ingest_news import ingest_news_for
    from core.providers.base import ProviderRegistry, ProviderStatus

    class P:
        name, kind = 'falso', 'news'
        def status(self): return ProviderStatus('falso', True, '', kind='news')
        def get_latest(self, q, limit=10):
            return [{'title': 'ACME firma contrato', 'url': 'https://www.reuters.com/acme-x',
                     'published_at': '2024-05-02T00:00:00+00:00', 'publisher': 'reuters.com',
                     'source_kind': 'press', 'provider': 'falso'}]

    with session_scope() as s:
        ingest_news_for(s, 'ACME', actor='pytest', provider_registry=ProviderRegistry([P()]))

    con = _c().get('/api/ontology/objects/ACME/timeline').get_json()
    assert any(e['kind'] == 'news' for e in con['timeline'])
    # la noticia se ordena por su fecha de PUBLICACIÓN dentro del mismo hilo
    noticia = next(e for e in con['timeline'] if e['kind'] == 'news')
    assert noticia['at'].startswith('2024-05')
    assert noticia['url']

    sin = _c().get('/api/ontology/objects/ACME/timeline?news=0').get_json()
    assert not any(e['kind'] == 'news' for e in sin['timeline'])


def test_timeline_de_objeto_inexistente(db):
    assert _c().get('/api/ontology/objects/NoExiste/timeline').status_code == 404


def test_la_accion_auditable_arrastra_su_fuente_al_timeline(db):
    """La línea de tiempo mostraba la acción SIN su evidencia, aunque la
    evidencia existiera: _log_action no pasaba source_id al evento. La UI
    (M6) pinta el enlace desde ahí, así que sin esto el recorrido
    hecho → fuente → documento se cortaba justo en el rastro auditable."""
    c = _c()
    r = c.post('/api/ontology/actions/CrearTesis', json={
        'actor': 'beto', 'company_id': 'ACME', 'stance': 'long', 'confidence': 0.7,
        'rationale': 'tesis con evidencia',
        'fuentes': [{'url': 'https://www.sec.gov/Archives/acme-8k.htm',
                     'titulo': 'ACME 8-K', 'publicador': 'SEC',
                     'cita_textual': 'material agreement signed'}],
    })
    assert r.status_code == 200

    d = c.get('/api/ontology/objects/ACME/timeline?limit=20').get_json()
    accion = next(e for e in d['timeline']
                  if e['event_type'] == 'ActionExecuted' and e['actor'] == 'beto')
    assert accion['source'], 'la acción llegó sin fuente al timeline'
    assert 'sec.gov' in accion['source']['url']
    assert accion['source']['trust'] == 3       # filing = fuente primaria
    assert accion['confidence'] == 0.7
