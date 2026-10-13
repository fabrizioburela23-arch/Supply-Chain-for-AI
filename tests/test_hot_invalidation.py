"""tests/test_hot_invalidation.py — INFRA_OPERATIVA paso 4 (§4.4-4.5): cuándo se reconstruyen las vistas.

  · sin base: la generación sale del snapshot con el MISMO código (source='snapshot', versión 0);
  · una escritura económica deja la vista atrasada (lag_versions > 0, stale) hasta que el constructor publica
    la versión nueva; una noticia/nota NO;
  · las rutas /api/matrix/* leen lo propio: tras escribir, la respuesta ya refleja la escritura;
  · ConfirmarVinculo (LinkStatusChanged) cambia el impacto en la vista nueva;
  · coherencia: con escritores concurrentes, cada generación contiene EXACTAMENTE lo de su versión
    (foto REPEATABLE READ: versión y datos de la misma foto);
  · una base re-creada (linaje nuevo) invalida la vista aunque el número de versión no retroceda;
  · cada construcción deja su fila en hot_view_builds (append-only, sin cuerpos);
  · modo ansioso: varias escrituras seguidas se AGRUPAN (no una construcción por escritura).
"""
import os
import sys
import threading
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')


def test_sin_base_la_generacion_sale_del_snapshot(monkeypatch):
    import ontology.db as odb
    from core.hotviews import builder, registry
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    registry.reset()
    try:
        g = builder.build_once()
        assert g.source == 'snapshot' and g.graph_version == 0 and g.id.endswith('.snapshot')
        assert g.id.startswith('g0.r') and len(g.release) == 64 and g.release_label == 'repo-unapproved'
        meta = registry.meta('impact', g)
        assert meta['stale'] is False and meta['lag_versions'] == 0 and meta['source'] == 'snapshot'
        core = g.views['graph_core']
        assert len(core.ids) >= 937 and len(core.factors) > 50
    finally:
        registry.reset()


@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from core.hotviews import builder, registry
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    with session_scope() as s:
        for oid in ('HI_A', 'HI_B', 'HI_C', 'HI_D'):
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company'}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=oid)
        for a, b, w in (('HI_A', 'HI_B', 6.0), ('HI_B', 'HI_C', 6.0)):
            apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': w}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=a, target_id=b)
        apply_event(s, 'LinkCreated', {'rel_type': 'fab', 'weight': 6.0,
                                       'properties': {'rel_label': 'Posible fundición'}},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id='HI_C', target_id='HI_D')
    registry.reset()
    yield engine
    builder._ST['eager'] = False
    registry.reset()
    Base.metadata.drop_all(engine)


def _db_version():
    from core.hotviews import signals
    from ontology.db import session_scope
    with session_scope() as s:
        return signals.read_db_version(s)


@needs_db
def test_escritura_economica_atrasa_la_vista_y_la_nueva_generacion_la_cubre(db):
    from core.hotviews import builder, registry
    from ontology.db import session_scope
    from ontology.service import apply_event
    v0, lin = _db_version()
    g0 = builder.ensure(v0, lin, timeout=10)
    assert g0 is not None and g0.graph_version == v0 and g0.source == 'pg'
    assert registry.lag(g0) == (0, False)
    # noticia → la versión no se mueve → la vista sigue al día
    with session_scope() as s:
        apply_event(s, 'ObjectCreated', {'label': 'n', 'type': 'NewsItem'}, valid_from='2026-01-01', source='t',
                    actor='t', object_id=f'news_{time.time_ns()}')
    assert registry.lag(registry.generation()) == (0, False)
    # vínculo nuevo → atrasada hasta reconstruir
    with session_scope() as s:
        apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 6.0}, valid_from='2000-01-01',
                    source='test', actor='pytest', object_id='HI_A', target_id='HI_D')
    lag_v, stale = registry.lag(registry.generation())
    assert lag_v == 1 and stale is True
    g1 = builder.ensure(v0 + 1, lin, timeout=10)
    assert g1 is not None and g1.graph_version == v0 + 1 and g1 is not g0
    d1 = dict(zip(*g1.views['impact'].victims['HI_A'][:2]))['HI_D']
    d0 = dict(zip(*g0.views['impact'].victims['HI_A'][:2]))['HI_D']
    assert d1 > d0                                     # A→D directo ahora; la generación vieja no cambió


@needs_db
def test_las_rutas_matrix_leen_lo_propio_y_confirmar_cambia_el_impacto(db):
    import server
    from ontology.actions import execute_action
    from ontology.db import session_scope
    from ontology.models import LinkRecord
    c = server.app.test_client()
    before = c.post('/api/matrix/impact', json={'shock': ['HI_C']}).get_json()
    with session_scope() as s:
        lid = str(s.query(LinkRecord).filter_by(source_id='HI_C', target_id='HI_D').first().id)
        execute_action(s, 'ConfirmarVinculo', {'link_id': lid}, actor='fabrizio')
    v, _ = _db_version()
    after = c.post('/api/matrix/impact', json={'shock': ['HI_C']}).get_json()
    assert after['view']['graph_version'] == v and after['view']['source'] == 'pg'
    assert after['impacts']['HI_D'] > before['impacts']['HI_D']        # sin el descuento "posible" (0,3×)


@needs_db
def test_coherencia_version_contenido_con_escritores_concurrentes(db):
    """Cada escritor confirma UN vínculo por transacción (= una versión). En toda generación construida
    mientras escriben, nº de vínculos del escritor == versión − versión inicial."""
    from core.hotviews import builder
    from ontology.db import session_scope
    from ontology.service import apply_event
    with session_scope() as s:
        for i in range(40):
            apply_event(s, 'ObjectCreated', {'label': f'W{i}', 'type': 'Company'}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=f'HI_W{i:02d}')
    v0, _ = _db_version()
    stop = threading.Event()

    def writer(k):
        i = 0
        while not stop.is_set() and i < 10:
            with session_scope() as s:
                apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 1.0}, valid_from='2000-01-01',
                            source='race', actor='race', object_id=f'HI_W{k * 10 + i:02d}', target_id='HI_A')
            i += 1

    ths = [threading.Thread(target=writer, args=(k,)) for k in range(4)]
    for t in ths:
        t.start()
    gens = []
    try:
        while any(t.is_alive() for t in ths) or len(gens) < 3:
            gens.append(builder.build_once())
            if len(gens) > 30:
                break
    finally:
        stop.set()
        for t in ths:
            t.join()
    gens.append(builder.build_once())
    for g in gens:
        core = g.views['graph_core']
        n_race = sum(1 for oid in core.ids if oid.startswith('HI_W') and core.out_w[core.idx[oid]] > 0)
        assert n_race == g.graph_version - v0, (g.id, n_race)
    assert gens[-1].graph_version == v0 + 40


@needs_db
def test_cada_construccion_queda_en_hot_view_builds(db):
    from sqlalchemy import text

    from core.hotviews import builder
    g = builder.build_once()
    with db.begin() as c:
        rows = c.execute(text("SELECT name, graph_version, content_sha, source, build_ms FROM hot_view_builds "
                              "WHERE generation = :g ORDER BY name"), {'g': g.id}).all()
    names = {r[0] for r in rows}
    assert names == {'graph_core', 'impact'}
    by = {r[0]: r for r in rows}
    assert by['impact'][2] == g.views['impact'].content_sha and by['graph_core'][2] == g.views['graph_core'].content_sha
    assert all(r[1] == g.graph_version and r[3] == 'pg' for r in rows)


@needs_db
def test_modo_ansioso_agrupa_las_senales(db):
    from core.hotviews import builder, registry
    from ontology.db import session_scope
    from ontology.service import apply_event
    v0, lin = _db_version()
    assert builder.ensure(v0, lin, timeout=10) is not None
    builder.start(eager=True, listen=False)
    time.sleep(0.2)
    n0 = builder.state()['builds']
    for i in range(6):
        with session_scope() as s:
            apply_event(s, 'ObjectUpdated', {'properties': {'n': i}}, valid_from='2026-01-01', source='t',
                        actor='t', object_id='HI_B')
    deadline = time.time() + 10
    while time.time() < deadline and registry.generation().graph_version < v0 + 6:
        time.sleep(0.1)
    builder._ST['eager'] = False
    assert registry.generation().graph_version == v0 + 6
    assert builder.state()['builds'] - n0 <= 2          # 6 escrituras → 1-2 construcciones (agrupadas)


@needs_db
def test_linaje_nuevo_invalida_aunque_la_version_no_retroceda(db):
    from core.hotviews import builder, registry
    from ontology.db import init_schema, session_scope
    from ontology.models import Base
    from ontology.service import apply_event
    v0, lin0 = _db_version()
    g = builder.ensure(v0, lin0, timeout=10)
    assert g is not None
    Base.metadata.drop_all(db)
    assert init_schema(retries=1)                     # = re-migración: otra tabla events
    with session_scope() as s:
        apply_event(s, 'ObjectCreated', {'label': 'Z', 'type': 'Company'}, valid_from='2000-01-01', source='t',
                    actor='t', object_id='HI_Z')
    v1, lin1 = _db_version()
    assert lin1 != lin0 and v1 >= v0
    assert not builder._satisfies(g, v1, lin1)
    g2 = builder.ensure(v1, lin1, timeout=10)
    assert g2 is not None and g2.lineage == lin1 and g2.views['graph_core'].ids == ['HI_Z']
    assert registry.lag(g)[1] is True                 # la generación vieja queda marcada stale


# ── paso 14: la tarjeta V3 vive con SU generación; el NRS se renueva con los fundamentales en vivo ──
def test_tarjeta_por_generacion_y_nrs_por_version_de_fundamentales(monkeypatch):
    import core.live_fundamentals as lf
    import ontology.db as odb
    from core.hotviews import builder, derived, registry
    from core.hotviews.views import card
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    registry.reset()
    derived.reset()
    try:
        g1 = builder.build_once()
        c1 = card.view(g1)
        assert card.view(g1) is c1                              # una vez por generación
        monkeypatch.setattr(lf, 'version', lambda: 1)
        monkeypatch.setattr(lf, 'live_margin', lambda nid: None)
        n_before = c1.nrs('TSMC')
        monkeypatch.setattr(lf, 'live_margin', lambda nid: -1.0 if nid == 'TSMC' else None)
        assert c1.nrs('TSMC') == n_before                       # misma versión de fundamentales: no recalcula
        monkeypatch.setattr(lf, 'version', lambda: 2)
        assert c1.nrs('TSMC') != n_before                       # tanda nueva → el margen real entra
        g2 = builder.build_once()                               # mismo contenido → MISMA generación → misma tarjeta
        assert g2.id == g1.id and card.view(g2) is c1

        class _G:                                               # generaciones distintas (ids distintos)
            def __init__(self, i):
                self.id = i
        built = []
        for i in ('gA', 'gB', 'gC'):
            derived.get(_G(i), 'probe', lambda g: built.append(g.id) or {'gen': g.id})
        assert built == ['gA', 'gB', 'gC']
        assert derived.peek(_G('gA'), 'probe') is None          # se guardan solo las 2 últimas generaciones
        assert derived.peek(_G('gC'), 'probe') == {'gen': 'gC'}
    finally:
        registry.reset()
        derived.reset()


@needs_db
def test_tarjeta_refleja_la_escritura_en_la_generacion_nueva(db):
    from core.hotviews import builder
    from core.hotviews.views import card
    from ontology.db import session_scope
    from ontology.service import apply_event
    with session_scope() as s:
        for oid in ('HC_X', 'HC_Y'):
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company'}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=oid)
    v0, lin = _db_version()
    g0 = builder.ensure(v0, lin, timeout=10)
    c0 = card.view(g0).cards.get('HC_Y')
    with session_scope() as s:
        apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 3.0}, valid_from='2000-01-01',
                    source='test', actor='pytest', object_id='HC_X', target_id='HC_Y')
    g1 = builder.ensure(v0 + 1, lin, timeout=10)
    assert g1 is not None and g1.id != g0.id
    c1 = card.view(g1).cards.get('HC_Y')
    assert c0 is not None and c1 is not None and card.view(g1) is not card.view(g0)
    assert c0['counts']['suppliers'] == 0 and c1['counts']['suppliers'] == 1
    assert c1['top_suppliers'][0]['id'] == 'HC_X'


@needs_db
def test_alertas_en_lote_iguales_a_una_por_una(db):
    from core.hotviews.views import alerts
    from ontology.agents import evaluate_alert
    from ontology.db import session_scope
    from ontology.service import apply_event
    with session_scope() as s:
        apply_event(s, 'ObjectCreated', {'label': 'AIdx', 'type': 'Company', 'properties': {'nrs_override': 77}},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id='AIdx')
    rules = [{'entity': 'AIdx', 'metric': 'nrs', 'op': '>', 'value': 70},
             {'entity': 'HI_A', 'metric': 'nrs', 'op': '<', 'value': 101},
             {'entity': 'NoSuch', 'metric': 'nrs', 'op': '>', 'value': 1}]
    with session_scope() as s:
        vals = alerts.values(s, rules)
        batch = [evaluate_alert(s, r, values=vals) for r in rules]
        one = [evaluate_alert(s, r) for r in rules]
    assert batch == one
    assert batch[0][:2] == (True, 77) and batch[2] == (False, None, 'objeto no encontrado')
    assert alerts.index(rules)[('nrs', 'AIdx')] == [0]
    # la lectura pidió ponerse al día en segundo plano (modo perezoso): se espera a que termine para no dejar una
    # construcción en vuelo que publique después en la prueba siguiente
    from core.hotviews import builder
    v, lin = _db_version()
    builder.ensure(v, lin, timeout=10)
    _settle()


def _settle(timeout=10.0):
    from core.hotviews import builder
    t0 = time.time()
    while builder.state().get('building') and time.time() - t0 < timeout:
        time.sleep(0.02)
