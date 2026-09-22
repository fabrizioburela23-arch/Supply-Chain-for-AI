"""tests/test_ingest_news.py — Phase 1 · M4: las noticias entran al grafo.

Antes de M4, GDELT era un pasamanos: se consultaba, se devolvía al navegador y
ahí moría. No se podía preguntar "¿qué se publicó sobre X en marzo?" ni
rastrear un hecho hasta el artículo que lo respalda.

Se prueba con un proveedor FALSO: la red no debe decidir si los tests pasan.
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
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    init_schema()
    with session_scope() as s:
        apply_event(s, 'ObjectCreated',
                    {'label': 'ACME Corp', 'type': 'Company', 'properties': {'mkt': 'ACME'}},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id='ACME')
    yield
    Base.metadata.drop_all(engine)


class _ProveedorFalso:
    """Doble del proveedor de noticias: los tests no deben depender de la red."""
    name = 'falso'
    kind = 'news'

    def __init__(self, items=None, revienta=False):
        self._items = items or []
        self._revienta = revienta

    def status(self):
        from core.providers.base import ProviderStatus
        return ProviderStatus(self.name, True, '', kind='news')

    def get_latest(self, query, limit=10):
        if self._revienta:
            raise RuntimeError('proveedor de noticias caído')
        return self._items[:limit]


def _registro(items=None, revienta=False):
    from core.providers.base import ProviderRegistry
    return ProviderRegistry([_ProveedorFalso(items, revienta)])


_ARTICULO = {
    'title': 'ACME gana un contrato de 2.000 millones',
    'url': 'https://www.reuters.com/business/acme-contract-2026',
    'published_at': '2026-03-15T10:00:00+00:00',
    'publisher': 'reuters.com', 'language': 'spa',
    'source_kind': 'press', 'provider': 'falso',
}


# ── Ingesta básica ──────────────────────────────────────────────────────────

def test_la_noticia_entra_al_grafo_con_su_fuente(db):
    from ontology.db import session_scope
    from ontology.ingest_news import ingest_news_for
    from ontology.service import get_object, object_links

    with session_scope() as s:
        r = ingest_news_for(s, 'ACME', actor='pytest', provider_registry=_registro([_ARTICULO]))
        assert r['ok'] and r['ingested'] == 1 and r['new'] == 1
        nid = r['items'][0]['news_id']
        sid = r['items'][0]['source_id']

    with session_scope() as s:
        noticia = get_object(s, nid)
        assert noticia.type == 'NewsItem'
        assert noticia.properties['publisher'] == 'reuters.com'
        # la fuente existe como entidad citable (M1)
        assert get_object(s, sid).type == 'Source'

        rels = {l.rel_type: l.target_id for l in object_links(s, nid, direction='out')}
        assert rels.get('reports_on') == 'ACME'    # pegada a la empresa
        assert rels.get('published_by') == sid     # y a quien la publicó


def test_valid_from_es_la_fecha_de_publicacion_no_la_de_ingesta(db):
    """El corazón del modelo bitemporal: la noticia fue cierta en el mundo
    cuando se publicó, aunque la leamos hoy. Sin esto, consultar el grafo
    'as_of marzo' no devolvería lo que se sabía en marzo."""
    from ontology.db import session_scope
    from ontology.ingest_news import ingest_news_for, news_id_for
    from ontology.models import Event
    from sqlalchemy import select

    art = dict(_ARTICULO, url='https://www.reuters.com/business/acme-fecha')
    with session_scope() as s:
        ingest_news_for(s, 'ACME', actor='pytest', provider_registry=_registro([art]))

    nid = news_id_for(art['url'])
    with session_scope() as s:
        ev = s.scalars(select(Event).where(
            Event.object_id == nid, Event.event_type == 'ObjectCreated')).first()
        assert ev.valid_from.year == 2026 and ev.valid_from.month == 3
        # …y recorded_at es HOY: las dos líneas de tiempo, separadas
        assert ev.recorded_at.year >= 2026
        assert ev.source_id      # el evento apunta al documento


def test_reingerir_no_duplica(db):
    """Id derivado de la URL: el mismo artículo es el mismo objeto."""
    from ontology.db import session_scope
    from ontology.ingest_news import ingest_news_for
    from ontology.models import ObjectRecord
    from sqlalchemy import select

    art = dict(_ARTICULO, url='https://www.reuters.com/business/acme-repetida')
    reg = _registro([art])

    with session_scope() as s:
        r1 = ingest_news_for(s, 'ACME', actor='pytest', provider_registry=reg)
        assert r1['new'] == 1
    with session_scope() as s:
        antes = s.query(ObjectRecord).filter(ObjectRecord.type == 'NewsItem').count()
    with session_scope() as s:
        r2 = ingest_news_for(s, 'ACME', actor='pytest', provider_registry=reg)
        assert r2['ingested'] == 1
        assert r2['new'] == 0            # ya existía
    with session_scope() as s:
        assert s.query(ObjectRecord).filter(ObjectRecord.type == 'NewsItem').count() == antes


def test_la_misma_url_con_ruido_es_la_misma_noticia(db):
    from ontology.db import session_scope
    from ontology.ingest_news import ingest_news_for, news_id_for

    base = 'https://www.reuters.com/business/acme-utm'
    a = dict(_ARTICULO, url=base)
    b = dict(_ARTICULO, url=base + '?utm_source=twitter')
    assert news_id_for(a['url']) == news_id_for(b['url'])

    with session_scope() as s:
        ingest_news_for(s, 'ACME', actor='pytest', provider_registry=_registro([a]))
    with session_scope() as s:
        r = ingest_news_for(s, 'ACME', actor='pytest', provider_registry=_registro([b]))
        assert r['new'] == 0


# ── Robustez ────────────────────────────────────────────────────────────────

def test_articulo_sin_url_se_descarta_sin_romper_el_lote(db):
    """Sin URL no hay procedencia posible (regla de M1). El resto del lote debe
    ingerirse igual: un artículo malo no puede tumbar a los buenos."""
    from ontology.db import session_scope
    from ontology.ingest_news import ingest_news_for

    lote = [
        dict(_ARTICULO, url='', title='Sin enlace'),
        dict(_ARTICULO, url='https://www.reuters.com/business/acme-buena'),
    ]
    with session_scope() as s:
        r = ingest_news_for(s, 'ACME', actor='pytest', provider_registry=_registro(lote))
        assert r['ingested'] == 1
        assert r['skipped_no_url'] == 1


def test_proveedor_caido_no_revienta_la_ingesta(db):
    from ontology.db import session_scope
    from ontology.ingest_news import ingest_news_for

    with session_scope() as s:
        r = ingest_news_for(s, 'ACME', actor='pytest', provider_registry=_registro(revienta=True))
        assert r['ok'] is True          # la app sigue
        assert r['ingested'] == 0
        assert r['errors'] and 'caído' in r['errors'][0]['error']


def test_no_se_crean_empresas_desde_una_noticia(db):
    """Una noticia no puede inventar una entidad: para eso está la Acción
    IncorporarEmpresa, que pasa por revisión humana."""
    from ontology.db import session_scope
    from ontology.ingest_news import ingest_news_for

    with session_scope() as s:
        r = ingest_news_for(s, 'EmpresaQueNoExiste', actor='pytest',
                            provider_registry=_registro([_ARTICULO]))
        assert r['ok'] is False
        assert 'no encontrada' in r['error']
        assert r['ingested'] == 0


def test_fecha_invalida_cae_a_ahora_sin_romper(db):
    from ontology.db import session_scope
    from ontology.ingest_news import ingest_news_for

    art = dict(_ARTICULO, url='https://www.reuters.com/business/acme-sinfecha',
               published_at='')
    with session_scope() as s:
        r = ingest_news_for(s, 'ACME', actor='pytest', provider_registry=_registro([art]))
        assert r['ingested'] == 1


# ── Confiabilidad heredada ──────────────────────────────────────────────────

def test_la_confianza_de_la_noticia_hereda_la_de_su_fuente(db):
    """Un filing y un agregador anónimo no valen lo mismo, y el grafo debe
    poder distinguirlo para que los agentes de Fase 2 razonen sobre evidencia."""
    from ontology.db import session_scope
    from ontology.ingest_news import ingest_news_for, news_id_for
    from ontology.models import Event
    from sqlalchemy import select

    primaria = dict(_ARTICULO, url='https://www.sec.gov/Archives/acme-8k',
                    source_kind='primary', publisher='SEC')
    floja = dict(_ARTICULO, url='https://blog-random.example/acme-rumor',
                 source_kind='aggregator', publisher='blog-random.example')

    with session_scope() as s:
        ingest_news_for(s, 'ACME', actor='pytest', provider_registry=_registro([primaria, floja]))

    with session_scope() as s:
        def conf(url):
            ev = s.scalars(select(Event).where(
                Event.object_id == news_id_for(url),
                Event.event_type == 'ObjectCreated')).first()
            return ev.confidence

        assert conf(primaria['url']) > conf(floja['url'])
        assert conf(primaria['url']) == pytest.approx(1.0)


# ── Lectura ─────────────────────────────────────────────────────────────────

def test_news_for_object_devuelve_lo_ingerido(db):
    from ontology.db import session_scope
    from ontology.ingest_news import news_for_object

    with session_scope() as s:
        items = news_for_object(s, 'ACME')
        assert items
        assert all(i['url'] for i in items)
        assert any('reuters' in (i['url'] or '') for i in items)


# ── API ─────────────────────────────────────────────────────────────────────

def test_endpoints_de_noticias(db):
    import server
    os.environ.setdefault('SECRET_KEY', 'test')
    server.app.config['TESTING'] = True
    c = server.app.test_client()

    r = c.get('/api/ontology/objects/ACME/news')
    assert r.status_code == 200
    assert r.get_json()['count'] >= 1

    assert c.get('/api/ontology/objects/NoExiste/news').status_code == 404

    # la ingesta exige actor: toda escritura queda atribuida
    assert c.post('/api/ontology/ingest/news', json={'entity_id': 'ACME'}).status_code == 400
    assert c.post('/api/ontology/ingest/news', json={'actor': 'x'}).status_code == 400


def test_time_travel_no_muestra_noticias_del_futuro(db):
    """La propiedad central del modelo bitemporal (spec §3): consultar el grafo
    'as_of' una fecha devuelve lo que se sabía ENTONCES. Como `valid_from` es la
    fecha de publicación, una noticia no puede aparecer antes de publicarse —
    ni siquiera si la ingerimos hoy."""
    from ontology.db import session_scope
    from ontology.ingest_news import ingest_news_for
    from ontology.service import as_of_graph

    lote = [
        dict(_ARTICULO, url='https://www.sec.gov/Archives/acme-tt-abril',
             published_at='2026-04-15T00:00:00+00:00', source_kind='primary'),
        dict(_ARTICULO, url='https://www.reuters.com/business/acme-tt-mayo',
             published_at='2026-05-02T00:00:00+00:00', source_kind='press'),
    ]
    with session_scope() as s:
        ingest_news_for(s, 'ACME', actor='pytest', provider_registry=_registro(lote))

    def reportajes(fecha):
        with session_scope() as s:
            g = as_of_graph(s, fecha)
        links = g['links'] if isinstance(g, dict) else g
        return [l for l in links
                if (l.get('rel_type') if isinstance(l, dict) else None) == 'reports_on'
                and (l.get('target') or l.get('target_id')) == 'ACME']

    antes = len(reportajes('2026-04-01'))
    entre = len(reportajes('2026-04-20'))
    despues = len(reportajes('2026-06-01'))

    assert entre > antes, 'la noticia de abril debe aparecer recién después de publicarse'
    assert despues > entre, 'la de mayo tampoco puede existir antes de su fecha'
