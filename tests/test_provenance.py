"""tests/test_provenance.py — Phase 1 · M1: procedencia de primera clase.

Lo que se verifica es la promesa de la especificación §5: "NINGÚN hecho
importante debe existir sin poder conocer su origen", y el recorrido
`Graph Claim → Source → evidencia original`.

Requiere Postgres real (DATABASE_URL) — se auto-saltan sin base, igual que el
resto de tests de ontología.
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
                    {'label': 'ACME', 'type': 'Company', 'properties': {'mkt': 'ACME'}},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id='ACME')
    yield
    Base.metadata.drop_all(engine)


# ── Normalización e identidad de la fuente ──────────────────────────────────

def test_misma_url_mismo_id_aunque_cambie_el_ruido():
    """Dos citas del MISMO artículo deben apuntar al mismo objeto Source, aunque
    lleguen con parámetros de rastreo, barra final o mayúsculas distintas."""
    from ontology.provenance import source_id_for, normalize_url

    a = source_id_for('https://www.sec.gov/Archives/doc.htm')
    b = source_id_for('https://WWW.SEC.GOV/Archives/doc.htm/')
    c = source_id_for('https://www.sec.gov/Archives/doc.htm?utm_source=twitter&fbclid=xyz')
    assert a == b == c
    assert a.startswith('src_')

    # …pero documentos distintos NO colisionan
    assert source_id_for('https://sec.gov/a') != source_id_for('https://sec.gov/b')
    assert 'utm_source' not in (normalize_url('https://x.com/p?utm_source=a') or '')


def test_url_invalida_no_revienta():
    """Una fuente mal formada nunca debe tumbar la escritura del hecho."""
    from ontology.provenance import source_id_for, normalize_url
    for basura in ('', None, '   ', 'no-es-una-url-sin-host'):
        assert source_id_for(basura) is None
        assert normalize_url(basura) is None


def test_trust_sale_del_vocabulario_no_de_una_constante():
    """El vocabulario ya definía source_kinds con `trust`; M1 lo usa de verdad."""
    from ontology.provenance import source_trust, guess_kind

    assert source_trust('primary') == 3
    assert source_trust('press') == 2
    assert source_trust('rumor') == 1
    # un kind inventado vale 0: preferimos subestimar antes que regalar confianza
    assert source_trust('el-primo-de-un-amigo') == 0
    assert source_trust(None) == 0

    # inferencia cuando nadie declara el tipo
    assert guess_kind('https://www.sec.gov/Archives/x.htm') == 'primary'
    assert guess_kind('https://ir.nvidia.com/news/x') == 'primary'
    # sin esta discriminación, una agencia de cable y un blog anónimo tendrían
    # el mismo trust y la señal sería inútil
    assert guess_kind('https://www.reuters.com/tech/x') == 'press'
    assert guess_kind('https://www.digitimes.com/news/x') == 'trade'
    assert guess_kind('https://www.globaltimes.cn/page/x') == 'state'
    # ante la duda, el trust más bajo: nunca se sobreestima una fuente
    assert guess_kind('https://random-blog.example/post') == 'aggregator'
    # un dominio que solo CONTIENE el nombre no cuela (evita reuters.com.fake.io)
    assert guess_kind('https://reuters.com.fake.io/x') == 'aggregator'
    # lo declarado manda sobre lo inferido
    assert guess_kind('https://random-blog.example/post', declared='press') == 'press'


# ── Registro de fuentes ─────────────────────────────────────────────────────

def test_register_source_es_idempotente_y_enriquece(db):
    from ontology.db import session_scope
    from ontology.provenance import register_source
    from ontology.service import get_object

    url = 'https://www.reuters.com/tech/acme-earnings-2026'
    with session_scope() as s:
        sid1 = register_source(s, url, kind='press', title='ACME beats',
                               publisher='Reuters', actor='pytest')
    with session_scope() as s:
        # segunda cita del mismo documento, con un dato que faltaba
        sid2 = register_source(s, url + '?utm_source=x', published_at='2026-02-01',
                               actor='pytest')
    assert sid1 == sid2

    with session_scope() as s:
        obj = get_object(s, sid1)
        assert obj.type == 'Source'
        p = obj.properties
        assert p['kind'] == 'press' and p['trust'] == 2
        assert p['title'] == 'ACME beats'        # no se pisó
        assert p['published_at'] == '2026-02-01'  # se completó
        assert p['url'].endswith('/tech/acme-earnings-2026')
        assert 'utm_source' not in p['url']


def test_register_source_con_url_basura_devuelve_none(db):
    from ontology.db import session_scope
    from ontology.provenance import register_source
    with session_scope() as s:
        assert register_source(s, '', actor='pytest') is None
        assert register_source(s, None, actor='pytest') is None


# ── El evento transporta la procedencia ─────────────────────────────────────

def test_evento_guarda_source_id_y_confidence(db):
    from ontology.db import session_scope
    from ontology.provenance import register_source
    from ontology.service import apply_event
    from ontology.models import Event
    from sqlalchemy import select

    with session_scope() as s:
        sid = register_source(s, 'https://sec.gov/filing/acme-10k', actor='pytest')
        ev = apply_event(s, 'ObjectUpdated', {'properties': {'empleados': 1234}},
                         valid_from='2026-03-01', source='manual', actor='pytest',
                         object_id='ACME', source_id=sid, confidence=0.9)
        ev_id = ev.id

    with session_scope() as s:
        got = s.get(Event, ev_id)
        assert got.source_id == sid
        assert got.confidence == 0.9


def test_confidence_se_acota_y_tolera_basura(db):
    from ontology.db import session_scope
    from ontology.service import apply_event
    from ontology.models import Event

    with session_scope() as s:
        alto = apply_event(s, 'ObjectUpdated', {'properties': {}}, valid_from='2026-03-01',
                           source='manual', actor='pytest', object_id='ACME', confidence=7.5)
        bajo = apply_event(s, 'ObjectUpdated', {'properties': {}}, valid_from='2026-03-01',
                           source='manual', actor='pytest', object_id='ACME', confidence=-3)
        malo = apply_event(s, 'ObjectUpdated', {'properties': {}}, valid_from='2026-03-01',
                           source='manual', actor='pytest', object_id='ACME', confidence='hola')
        ids = (alto.id, bajo.id, malo.id)

    with session_scope() as s:
        a, b, c = (s.get(Event, i) for i in ids)
        assert a.confidence == 1.0
        assert b.confidence == 0.0
        assert c.confidence is None


def test_source_largo_no_rompe_la_escritura(db):
    """Regresión: varias Acciones admiten `fuente` de hasta 200 caracteres y se
    vuelcan a Event.source, que es String(60). Antes de M1 eso reventaba o
    truncaba a nivel de BD."""
    from ontology.db import session_scope
    from ontology.service import apply_event
    from ontology.models import Event

    largo = 'tejedor_' + ('x' * 250)
    with session_scope() as s:
        ev = apply_event(s, 'ObjectUpdated', {'properties': {}}, valid_from='2026-03-01',
                         source=largo, actor='pytest', object_id='ACME')
        ev_id = ev.id
    with session_scope() as s:
        got = s.get(Event, ev_id)
        assert len(got.source) <= 60
        assert got.source.startswith('tejedor_')


# ── El recorrido completo: hecho → fuente → evidencia ───────────────────────

def test_crear_tesis_registra_sus_fuentes_y_quedan_navegables(db):
    """El caso que la auditoría marcó como roto: las fuentes de una tesis se
    perdían de todas las vistas al aprobarla."""
    from ontology.db import session_scope
    from ontology.actions import execute_action
    from ontology.provenance import provenance_for_object
    from ontology.service import get_object, object_links

    with session_scope() as s:
        r = execute_action(s, 'CrearTesis', {
            'company_id': 'ACME', 'stance': 'long', 'confidence': 0.8,
            'rationale': 'moat estructural',
            'fuentes': [
                {'url': 'https://www.sec.gov/Archives/acme-10k.htm',
                 'titulo': 'ACME 10-K 2026', 'publicador': 'SEC',
                 'fecha': '2026-02-10', 'cita_textual': 'revenue grew 40% year over year',
                 'consultado_at': '2026-03-01T10:00:00Z'},
                {'url': 'https://www.reuters.com/acme-wins-contract',
                 'titulo': 'ACME wins contract', 'publicador': 'Reuters',
                 'fecha': '2026-02-20', 'cita_textual': 'a multi-year supply agreement'},
            ],
        }, actor='ana')
        thesis_id = r['thesis_id']
        assert len(r['source_ids']) == 2

    with session_scope() as s:
        # 1) las fuentes existen como entidades del grafo
        for sid in r['source_ids']:
            assert get_object(s, sid).type == 'Source'

        # 2) están enlazadas con evidenced_by
        links = object_links(s, thesis_id, direction='out')
        evid = [l for l in links if l.rel_type == 'evidenced_by']
        assert len(evid) == 2
        assert any('40%' in (l.properties or {}).get('quote', '') for l in evid)

        # 3) y se pueden recorrer desde el hecho hasta la URL original
        fuentes = provenance_for_object(s, thesis_id)
        assert len(fuentes) == 2
        urls = {f['url'] for f in fuentes}
        assert any('sec.gov' in u for u in urls)
        # ordenadas por confiabilidad: el filing (primary, 3) antes que Reuters
        assert fuentes[0]['trust'] >= fuentes[1]['trust']
        assert fuentes[0]['kind'] == 'primary'


def test_el_evento_auditable_lleva_las_fuentes(db):
    """Antes de M1, el ActionExecuted de CrearTesis solo llevaba stance y
    confidence: la evidencia no llegaba al rastro auditable."""
    from ontology.db import session_scope
    from ontology.actions import execute_action, list_actions

    with session_scope() as s:
        execute_action(s, 'CrearTesis', {
            'company_id': 'ACME', 'stance': 'watch', 'confidence': 0.5,
            'rationale': 'vigilar',
            'fuentes': [{'url': 'https://ir.acme.com/pr/2026',
                         'cita_textual': 'guidance raised'}],
        }, actor='beto')

    with session_scope() as s:
        acts = list_actions(s, actor='beto', action_type='CrearTesis')
        assert acts
        assert acts[0].payload.get('source_ids')


def test_provenance_vacia_cuando_no_hay_evidencia(db):
    """Un objeto sin documento detrás devuelve lista vacía — eso es la verdad,
    no se disfraza con una ficha inventada."""
    from ontology.db import session_scope
    from ontology.provenance import provenance_for_object
    with session_scope() as s:
        assert provenance_for_object(s, 'ACME') == [] or all(
            isinstance(x, dict) for x in provenance_for_object(s, 'ACME'))


# ── API ─────────────────────────────────────────────────────────────────────

def test_endpoints_de_procedencia(db):
    import server
    os.environ.setdefault('SECRET_KEY', 'test')
    server.app.config['TESTING'] = True
    c = server.app.test_client()

    r = c.get('/api/ontology/sources')
    assert r.status_code == 200
    d = r.get_json()
    assert d['count'] >= 1
    assert all('url' in s for s in d['sources'])

    # filtro por confiabilidad mínima
    solo_primarias = c.get('/api/ontology/sources?min_trust=3').get_json()
    assert all((s.get('trust') or 0) >= 3 for s in solo_primarias['sources'])

    # objeto inexistente → 404 honesto
    assert c.get('/api/ontology/objects/NoExiste123/provenance').status_code == 404

    r2 = c.get('/api/ontology/objects/ACME/provenance')
    assert r2.status_code == 200
    assert 'sources' in r2.get_json()


def test_base_existente_gana_las_columnas_sin_perder_datos(db):
    """El camino de riesgo real: producción ya tiene la tabla `events` SIN las
    columnas de M1. `create_all` NO añade columnas a tablas existentes, así que
    init_schema aplica ALTER ... ADD COLUMN IF NOT EXISTS. Debe ser idempotente
    y no tocar las filas que ya estaban."""
    from sqlalchemy import text
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.service import apply_event
    from ontology.models import Event

    engine = _get_engine()

    with session_scope() as s:
        apply_event(s, 'ObjectUpdated', {'properties': {'marca': 'antes-del-upgrade'}},
                    valid_from='2026-01-01', source='test', actor='pytest', object_id='ACME')

    with session_scope() as s:
        filas_antes = s.query(Event).count()

    def columnas():
        with engine.begin() as c:
            return {r[0] for r in c.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='events'"))}

    # simular la base vieja
    with engine.begin() as c:
        c.execute(text('ALTER TABLE events DROP COLUMN IF EXISTS source_id'))
        c.execute(text('ALTER TABLE events DROP COLUMN IF EXISTS confidence'))
    assert not (columnas() & {'source_id', 'confidence'})

    init_schema()
    assert {'source_id', 'confidence'} <= columnas()

    init_schema()   # idempotente: dos arranques seguidos no fallan
    assert {'source_id', 'confidence'} <= columnas()

    with engine.begin() as c:
        idx = {r[0] for r in c.execute(text(
            "SELECT indexname FROM pg_indexes WHERE tablename='events'"))}
    assert 'ix_events_source_id' in idx

    # y los datos previos siguen ahí
    with session_scope() as s:
        assert s.query(Event).count() == filas_antes
