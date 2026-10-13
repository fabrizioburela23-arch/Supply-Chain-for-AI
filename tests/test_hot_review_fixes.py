"""tests/test_hot_review_fixes.py — revisión del paso 4 (vistas rápidas / graph_version), hallazgos reproducidos:

  · SAVEPOINTs: los hooks de la versión solo actúan en la transacción RAÍZ (auto_cycle aplica cada propuesta en
    `begin_nested()`: la 2.ª chocaba con UNIQUE(txid) de kh_tx_versions y quedaba 'rejected');
  · el contador kh_versions es el ÚLTIMO candado (se vuelca la sesión antes): sin DeadlockDetected nuevos;
  · escrituras económicas de un proceso SIN el hook (contenedor viejo en el deploy) → el sondeo mueve la versión;
  · la tarea de 30 s no reconstruye si nada cambió (ni deja filas en hot_view_builds);
  · el agrupamiento de 1 s se corta si un lector espera; una construcción que falla no hace esperar 2 s a cada
    ruta ni reintenta en bucle cerrado;
  · el id de la generación (ETag) cambia con el linaje y el contenido;
  · /api/matrix/metrics y /factors por el camino directo traen el sobre `view`;
  · el screener lee el PageRank de la vista publicada.
"""
import os
import sys
import threading
import time
from types import SimpleNamespace

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')


# ── sin base ────────────────────────────────────────────────────────────────
def _fake_data(lineage, version=0, source='snapshot'):
    return SimpleNamespace(graph_version=version, lineage=lineage, source=source, read_ms=0.0, extra={})


def test_id_de_generacion_cambia_con_linaje_y_contenido():
    from core.hotviews import registry
    a = registry.make(_fake_data('l1'), {}, 'r' * 64, 'x', {}, {'impact': 'a' * 64})
    b = registry.make(_fake_data('l1'), {}, 'r' * 64, 'x', {}, {'impact': 'b' * 64})
    c = registry.make(_fake_data('l2'), {}, 'r' * 64, 'x', {}, {'impact': 'a' * 64})
    d = registry.make(_fake_data('l1'), {}, 'r' * 64, 'x', {}, {'impact': 'a' * 64})
    assert len({a.id, b.id, c.id}) == 3
    assert a.id == d.id                               # mismo contenido y linaje → mismo ETag (304 legítimo)
    assert a.id.startswith('g0.r') and a.id.endswith('.snapshot') and len(a.id) <= 96


def test_etag_no_da_304_con_contenido_distinto(monkeypatch):
    import ontology.db as odb
    from core.hotviews import builder, registry, source
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    monkeypatch.setenv('KHIPU_SCHEDULER', 'off')
    import server
    registry.reset()
    try:
        data = source.load_snapshot()
        builder.build_once(data)
        c = server.app.test_client()
        r1 = c.get('/api/hot/impact/TSMC')
        tag = r1.headers.get('ETag')
        assert r1.status_code == 200 and tag
        drop = {t for t in data.triples if t[0] == 'TSMC'}
        data2 = source.GraphData(data.source, data.graph_version, 'snap:otro', data.ids, data.meta,
                                 [t for t in data.triples if t not in drop],
                                 [f for f in data.flow_links if f['source'] != 'TSMC'], data.factors,
                                 extra=data.extra)
        builder.build_once(data2)
        r2 = c.get('/api/hot/impact/TSMC', headers={'If-None-Match': tag})
        assert r2.status_code == 200 and r2.headers.get('ETag') != tag
    finally:
        registry.reset()


def test_coalesce_se_corta_si_un_lector_espera(monkeypatch):
    """Modo ansioso tras una señal (demand=0) → el hilo agrupa 1 s; un ensure() que llega debe cortarlo."""
    import ontology.db as odb
    from core.hotviews import builder, registry
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    monkeypatch.setattr(builder, 'COALESCE_S', 3.0)
    registry.reset()
    builder._ST.update(consecutive_failures=0, retry_at=0.0)
    try:
        builder.build_once()                          # que la primera no cuente
        g0 = registry.generation()
        builder._ST['eager'] = True
        builder._on_signal('graph', 0, ())            # señal sin lector → el hilo entra a agrupar 3 s
        time.sleep(0.2)
        registry.reset()                              # el lector necesita una generación nueva
        t0 = time.time()
        g = builder.ensure(None, None, timeout=6)
        took = time.time() - t0
        assert g is not None and g is not g0
        assert took < 2.0, took                       # antes: 3 s de agrupamiento + construcción
    finally:
        builder._ST['eager'] = False
        registry.reset()


def test_construccion_que_falla_no_hace_esperar_ni_gira(monkeypatch):
    import ontology.db as odb
    from core.hotviews import builder, registry, source
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    calls = []

    def boom():
        calls.append(time.time())
        raise RuntimeError('fuente caída')
    monkeypatch.setattr(source, 'load', boom)
    registry.reset()
    builder._ST.update(consecutive_failures=0, retry_at=0.0, eager=False)
    try:
        t0 = time.time()
        assert builder.ensure(None, None, timeout=2.0) is None
        first = time.time() - t0
        assert first < 1.0, first                     # vio la falla: no agota los 2 s
        times = []
        for _ in range(3):                            # en la espera creciente: directo al instante
            t1 = time.time()
            assert builder.ensure(None, None, timeout=2.0) is None
            times.append(time.time() - t1)
        assert max(times) < 0.2, times
        time.sleep(0.3)
        assert len(calls) <= 2, len(calls)            # antes: ~20 lecturas completas por segundo esperando
        assert builder.state()['consecutive_failures'] >= 1
    finally:
        monkeypatch.undo()
        builder._ST.update(consecutive_failures=0, retry_at=0.0)
        registry.reset()


# ── con Postgres ────────────────────────────────────────────────────────────
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
        for oid in ('RF_A', 'RF_B', 'RF_C', 'RF_D', 'RF_E'):
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company'}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=oid)
        apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 6.0}, valid_from='2000-01-01',
                    source='test', actor='pytest', object_id='RF_A', target_id='RF_B')
    registry.reset()
    builder._ST.update(consecutive_failures=0, retry_at=0.0)
    yield engine
    builder._ST['eager'] = False
    registry.reset()
    Base.metadata.drop_all(engine)


def _v():
    from sqlalchemy import text

    from ontology.db import session_scope
    with session_scope() as s:
        return int(s.execute(text("SELECT v FROM kh_versions WHERE name = 'graph'")).scalar())


def _upd(s, oid, k):
    from ontology.service import apply_event
    return apply_event(s, 'ObjectUpdated', {'properties': {k: time.time()}}, valid_from=None, source='t',
                       actor='t', object_id=oid)


@needs_db
def test_auto_cycle_con_savepoints_aprueba_todo_y_sube_una_version(db, monkeypatch):
    from sqlalchemy import select

    from ontology import agents
    from ontology.db import session_scope
    from ontology.models import ProposedAction
    monkeypatch.setattr(agents, 'run_agents', lambda s, **k: {})
    with session_scope() as s:
        for i, (a, b) in enumerate((('RF_C', 'RF_A'), ('RF_D', 'RF_A'), ('RF_E', 'RF_B'))):
            s.add(ProposedAction(agent='rf_test', action_type='ProponerVinculo',
                                 payload={'from_id': b, 'to_id': a, 'tipo': 'supply', 'fuente': f'rf{i}'},
                                 object_id=a, confidence=0.9, status='pending'))
    v0 = _v()
    with session_scope() as s:
        out = agents.auto_cycle(s)
    assert len(out['auto_applied']) == 3, out
    with session_scope() as s:
        st = [p.status for p in s.scalars(select(ProposedAction).where(ProposedAction.agent == 'rf_test'))]
    assert st == ['approved'] * 3
    assert _v() == v0 + 1                             # una transacción raíz = una versión


@needs_db
def test_savepoint_confirmado_y_raiz_deshecha_no_adelanta_lo_conocido(db):
    from core.hotviews import signals
    from ontology.db import get_session_factory
    signals.poll()
    v0, k0 = _v(), signals.known()['v']
    s = get_session_factory()()
    try:
        sp = s.begin_nested()
        _upd(s, 'RF_A', 'sp')
        sp.commit()
        assert signals.known()['v'] == k0             # antes: +1 sin que la raíz confirmara
        s.rollback()
    finally:
        s.close()
    assert _v() == v0 and signals.known()['v'] == k0


@needs_db
def test_savepoint_deshecho_no_borra_lo_anotado_por_la_raiz(db):
    from ontology.db import get_session_factory
    v0 = _v()
    s = get_session_factory()()
    try:
        _upd(s, 'RF_A', 'outer')
        s.begin_nested().rollback()
        s.commit()
    finally:
        s.close()
    assert _v() == v0 + 1                             # antes: el cambio económico quedaba sin versión


@needs_db
def test_contador_es_el_ultimo_candado_sin_deadlock(db):
    from ontology.db import get_session_factory
    res = {}

    def a():
        s = get_session_factory()()
        try:
            _upd(s, 'RF_B', 'a1')
            _upd(s, 'RF_B', 'a2')                     # vuelca el UPDATE de objects[RF_B] → fila tomada
            time.sleep(1.0)
            s.commit()
            res['A'] = 'ok'
        except Exception as e:  # noqa: BLE001
            res['A'] = type(e).__name__
            s.rollback()
        finally:
            s.close()

    def b():
        time.sleep(0.3)
        s = get_session_factory()()
        try:
            _upd(s, 'RF_B', 'b1')                     # su UPDATE queda pendiente hasta el commit
            s.commit()
            res['B'] = 'ok'
        except Exception as e:  # noqa: BLE001
            res['B'] = type(e).__name__
            s.rollback()
        finally:
            s.close()
    ta, tb = threading.Thread(target=a), threading.Thread(target=b)
    ta.start()
    tb.start()
    ta.join()
    tb.join()
    assert res == {'A': 'ok', 'B': 'ok'}, res


@needs_db
def test_escritura_economica_sin_hook_la_detecta_el_sondeo(db, monkeypatch):
    from core.hotviews import builder, registry, signals
    from ontology.db import session_scope
    from ontology.service import apply_event
    g = builder.build_once()
    v0 = _v()
    assert g.extra.get('snapshot')
    # = el contenedor viejo: escribe eventos sin anotar la versión
    monkeypatch.setattr(signals, 'mark', lambda *a, **k: False)
    with session_scope() as s:
        apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 6.0}, valid_from='2000-01-01',
                    source='old', actor='old', object_id='RF_C', target_id='RF_D')
    with session_scope() as s:                        # y una noticia (no económica)
        apply_event(s, 'ObjectCreated', {'label': 'n', 'type': 'NewsItem'}, valid_from='2026-01-01', source='t',
                    actor='t', object_id=f'news_rf_{time.time_ns()}')
    monkeypatch.undo()
    assert _v() == v0
    out = signals.poll()
    assert out['orphans'].get('economic') == 1, out
    assert _v() == v0 + 1
    assert registry.lag(registry.generation())[1] is True     # la vista vieja queda marcada atrasada
    out2 = signals.poll()                             # ya revisado: no vuelve a subir
    assert out2['orphans'].get('economic') == 0, out2
    assert _v() == v0 + 1
    g2 = builder.ensure(v0 + 1, signals.known()['lineage'], timeout=10)
    assert g2 is not None and g2.graph_version == v0 + 1
    core = g2.views['graph_core']
    assert core.out_w[core.idx['RF_C']] > 0           # el vínculo del "contenedor viejo" ya está en la vista
    # solo noticia sin hook → sin versión nueva
    monkeypatch.setattr(signals, 'mark', lambda *a, **k: False)
    with session_scope() as s:
        apply_event(s, 'ObjectCreated', {'label': 'n2', 'type': 'NewsItem'}, valid_from='2026-01-01', source='t',
                    actor='t', object_id=f'news_rf2_{time.time_ns()}')
    monkeypatch.undo()
    assert signals.poll()['orphans'].get('economic') == 0 and _v() == v0 + 1


@needs_db
def test_la_tarea_de_30s_no_reconstruye_sin_cambios(db):
    from sqlalchemy import text

    from core.hotviews import builder, registry, signals
    from ontology.db import session_scope
    with session_scope() as s:
        v, lin = signals.read_db_version(s)
    assert builder.ensure(v, lin, timeout=10) is not None
    g0 = registry.generation()

    def rows():
        with session_scope() as s:
            return s.execute(text('SELECT count(*) FROM hot_view_builds')).scalar()
    n_rows, n_builds = rows(), builder.state()['builds']
    try:
        for _ in range(3):                            # = tres ticks de la tarea 'hot_views' (server.py)
            builder.start(eager=True, listen=False)
            signals.poll()
            time.sleep(0.4 + builder.COALESCE_S)
        assert registry.generation() is g0
        assert builder.state()['builds'] == n_builds
        assert rows() == n_rows
        builder.build_once()                          # misma generación otra vez → sin filas repetidas
        assert rows() == n_rows
    finally:
        builder._ST['eager'] = False


@needs_db
def test_metrics_y_factors_directos_traen_el_sobre(db, monkeypatch):
    import matrix.api as M
    import server
    monkeypatch.setattr(M, '_hot', lambda scope, as_of=None: None)
    monkeypatch.setattr(M, '_TTL_CACHE', {})
    c = server.app.test_client()
    for url in ('/api/matrix/metrics', '/api/matrix/metrics', '/api/matrix/factors', '/api/matrix/status'):
        r = c.get(url)
        assert r.status_code == 200, (url, r.get_json())
        d = r.get_json()
        assert d.get('view') and d['view']['source'] == 'direct', url
        assert r.headers.get('X-Khipu-Graph-Version') is not None, url


@needs_db
def test_screener_lee_pagerank_de_la_vista(db, monkeypatch):
    """Paso 8: el PageRank sale de la vista Impact de la MISMA generación que lee el screener (hot.graph()):
    la publicada si trae el catálogo; con esta base de prueba (5 empresas) los lectores usan el snapshot."""
    from core import screener
    from core.hotviews import builder, hot, registry
    registry.reset()
    hot.reset()
    assert screener._pagerank_ranks() == {}
    builder.build_once()
    view = hot.graph()
    ranks = screener._pagerank_ranks()
    assert ranks and set(ranks) <= set(view.core.ids)
    assert ranks == {k: m['pagerank_rank'] for k, m in view.impact.metrics.items() if m.get('pagerank_rank')}
    hot.reset()
