"""tests/test_scale_hot_rebuild.py — EXPANSION_5K E1.4: reconstrucción AGRUPADA en escrituras masivas.

Un lote de 250 vínculos en UNA transacción (el camino real: ontology.bulk_import → apply_event) debe dar:
  · UNA versión del grafo (una fila en kh_tx_versions, un pg_notify);
  · UNA reconstrucción de las vistas — también en modo ansioso con LISTEN activo (el aviso del propio proceso
    llega por after_commit Y por NOTIFY) y con un lector esperando (`ensure`, que se salta el agrupamiento);
  · mientras se reconstruye, el sobre dice stale:true (lag_versions 1) y `rebuilding`;
  · una señal de una versión que la generación publicada YA cubre no reconstruye nada;
  · varias transacciones dentro de `builder.coalesced()` → una sola reconstrucción al salir.
"""
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')

N_SRC = 25                      # 25 × 10 destinos = 250 pares (un lote)


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
        for i in range(N_SRC):
            apply_event(s, 'ObjectCreated', {'label': f'SR src {i}', 'type': 'Company'}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=f'SR_S{i:02d}')
        for j in range(10):
            apply_event(s, 'ObjectCreated', {'label': f'SR dst {j}', 'type': 'Company'}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=f'SR_D{j:02d}')
        for k in range(8):
            apply_event(s, 'ObjectCreated', {'label': f'SR extra {k}', 'type': 'Company'}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=f'SR_X{k:02d}')
    registry.reset()
    yield engine
    _stop_eager()
    registry.reset()
    Base.metadata.drop_all(engine)


def _stop_eager():
    from core.hotviews import builder, signals
    builder._ST['eager'] = False
    signals._LISTENER['stop'] = True
    _settle()


def _settle(timeout=15.0):
    from core.hotviews import builder
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = builder.state()
        if not st.get('building') and not (st.get('dirty') and st.get('eager')):
            return
        time.sleep(0.02)


def _db_version():
    from core.hotviews import signals
    from ontology.db import session_scope
    with session_scope() as s:
        return signals.read_db_version(s)


def _tx_rows():
    from sqlalchemy import text

    from ontology.db import session_scope
    with session_scope() as s:
        return int(s.execute(text("SELECT count(*) FROM kh_tx_versions WHERE name = 'graph'")).scalar())


def _records(rel, n=250, weight=2.0, tag='a'):
    out = []
    for i in range(N_SRC):
        for j in range(10):
            if len(out) >= n:
                return out
            out.append({'source': f'SR_S{i:02d}', 'target': f'SR_D{j:02d}', 'rel_type': rel, 'weight': weight,
                        'external_id': f'{tag}-{i}-{j}'})
    return out


def _bulk(rel, tag, n=250):
    from ontology.bulk_import import import_links_bulk
    from ontology.db import session_scope
    with session_scope() as s:                       # UNA transacción (flush cada 100 = 3 lotes adentro)
        res = import_links_bulk(s, _records(rel, n=n, tag=tag), provenance=f'scale_{tag}', batch_size=100,
                                actor='pytest')
    assert res['created'] == n and res['batches'] == 3, res
    return res


@needs_db
def test_lote_de_250_en_una_transaccion_es_una_version_y_una_reconstruccion(db, monkeypatch):
    import threading

    from core.hotviews import builder, registry, signals
    _stop_eager()
    v0, lin = _db_version()
    g0 = builder.ensure(v0, lin, timeout=15)
    assert g0 is not None and g0.graph_version == v0
    _settle()
    rows0, bumps0, builds0 = _tx_rows(), signals._STATS['bumps'], builder.state()['builds']
    _bulk('supply', 'a')
    v1, _ = _db_version()
    assert v1 == v0 + 1                                       # 250 eventos → UNA versión
    assert _tx_rows() == rows0 + 1 and signals._STATS['bumps'] == bumps0 + 1
    assert signals.known()['n_ids'] == N_SRC + 10             # ids tocados: los 35 extremos, una vez
    # mientras nadie reconstruye (modo perezoso), el sobre lo dice: atrasado y stale
    meta = registry.meta('impact', registry.generation())
    assert meta['stale'] is True and meta['lag_versions'] == 1 and meta['graph_version'] == v0
    real_build, seen = builder.build_once, []

    def slow_build(data=None):                                # construcción lenta: el sobre se mira entre medio
        time.sleep(0.6)
        return real_build(data)
    monkeypatch.setattr(builder, 'build_once', slow_build)
    out = {}
    th = threading.Thread(target=lambda: out.setdefault('g', builder.ensure(v1, lin, timeout=15)))
    th.start()
    t0 = time.time()
    while th.is_alive() and time.time() - t0 < 15:
        m = registry.meta('impact', registry.generation())
        if m['graph_version'] == v0:
            seen.append((m['stale'], m['rebuilding']))
        time.sleep(0.02)
    th.join()
    monkeypatch.setattr(builder, 'build_once', real_build)
    assert (True, True) in seen and all(st for st, _rb in seen)   # durante la reconstrucción: stale + rebuilding
    g1 = out['g']
    assert g1 is not None and g1.graph_version == v1
    _settle()
    assert builder.state()['builds'] - builds0 == 1           # UNA reconstrucción para el lote entero
    core = g1.views['graph_core']
    assert all(f'SR_S{i:02d}' in core.idx for i in range(N_SRC))
    assert all(core.out_w[core.idx[f'SR_S{i:02d}']] > 0 for i in range(N_SRC))
    meta = registry.meta('impact', g1)
    assert meta['stale'] is False and meta['lag_versions'] == 0 and meta.get('rebuilding') is False


@needs_db
def test_modo_ansioso_con_listen_y_lector_esperando_reconstruye_una_vez(db):
    """El peor caso de antes: un lector esperando (`ensure`) corta el agrupamiento → la construcción arranca al
    instante, el NOTIFY del propio proceso llega DURANTE la construcción y marcaba otra (misma versión, 2 builds)."""
    from core.hotviews import builder, registry, signals
    _stop_eager()
    v0, lin = _db_version()
    assert builder.ensure(v0, lin, timeout=15) is not None
    _settle()
    signals._LISTENER['stop'] = False
    builder.start(eager=True, listen=True)
    t0 = time.time()
    while not signals._LISTENER['connected'] and time.time() - t0 < 10:
        time.sleep(0.05)
    assert signals._LISTENER['connected'], signals._LISTENER
    _settle()
    builds0, notifies0 = builder.state()['builds'], signals._STATS['notifies']
    _bulk('fab', 'b')
    v1, _ = _db_version()
    assert v1 == v0 + 1
    g1 = builder.ensure(v1, lin, timeout=15)                  # lector esperando: sin agrupamiento
    assert g1 is not None and g1.graph_version == v1
    deadline = time.time() + 10
    while signals._STATS['notifies'] == notifies0 and time.time() - deadline < 0:
        time.sleep(0.05)
    assert signals._STATS['notifies'] - notifies0 == 1        # UN aviso por la transacción
    time.sleep(builder.COALESCE_S + 1.0)                      # tiempo de sobra para una 2.ª construcción
    _settle()
    assert builder.state()['builds'] - builds0 == 1, builder.state()
    assert registry.generation().graph_version == v1
    # una señal repetida de una versión ya cubierta (NOTIFY tardío, sondeo) no reconstruye
    skipped0 = builder.state().get('skipped_signals', 0)
    signals.signal('graph', v1, ('SR_S00',), via='notify')
    time.sleep(builder.COALESCE_S + 0.5)
    _settle()
    assert builder.state()['builds'] - builds0 == 1
    assert builder.state()['skipped_signals'] == skipped0 + 1
    _stop_eager()


@needs_db
def test_lector_que_llega_durante_la_construccion_no_repite_la_version(db, monkeypatch):
    """Revisión E1.4: dos lectores de la MISMA versión, el 2.º llega a mitad de la construcción que pidió el 1.º —
    antes `ensure` forzaba otra construcción idéntica (2 builds por versión con cada /api/matrix/* en vuelo)."""
    import threading

    from core.hotviews import builder
    from ontology.db import session_scope
    from ontology.service import apply_event
    _stop_eager()
    v0, lin = _db_version()
    assert builder.ensure(v0, lin, timeout=15) is not None
    _settle()
    with session_scope() as s:
        apply_event(s, 'LinkCreated', {'rel_type': 'license', 'weight': 1.0}, valid_from='2000-01-01',
                    source='test', actor='pytest', object_id='SR_X00', target_id='SR_X07')
    v1, _ = _db_version()
    real_build = builder.build_once

    def slow_build(data=None):
        time.sleep(0.6)
        return real_build(data)
    monkeypatch.setattr(builder, 'build_once', slow_build)
    builds0, out = builder.state()['builds'], {}

    def reader(name, delay):
        time.sleep(delay)
        g = builder.ensure(v1, lin, timeout=15)
        out[name] = g.graph_version if g is not None else None
    ths = [threading.Thread(target=reader, args=('r1', 0.0)), threading.Thread(target=reader, args=('r2', 0.3))]
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    time.sleep(builder.COALESCE_S + 0.8)
    _settle()
    monkeypatch.setattr(builder, 'build_once', real_build)
    assert out == {'r1': v1, 'r2': v1}
    assert builder.state()['builds'] - builds0 == 1, builder.state()


@needs_db
def test_varias_transacciones_dentro_de_coalesced_una_reconstruccion(db):
    """Para importadores que parten el lote en varias transacciones (E2.8): `builder.coalesced()` difiere la
    reconstrucción ansiosa hasta salir (con tope de tiempo); el sobre sigue diciendo stale entre medio."""
    from core.hotviews import builder, registry, signals
    from ontology.db import session_scope
    from ontology.service import apply_event
    _stop_eager()
    v0, lin = _db_version()
    assert builder.ensure(v0, lin, timeout=15) is not None
    _settle()
    builder.start(eager=True, listen=False)
    _settle()
    builds0 = builder.state()['builds']
    with builder.coalesced('pytest'):
        for k in range(4):
            with session_scope() as s:
                apply_event(s, 'LinkCreated', {'rel_type': 'cloud', 'weight': 1.0}, valid_from='2000-01-01',
                            source='test', actor='pytest', object_id=f'SR_X{k:02d}', target_id=f'SR_X{k + 4:02d}')
            time.sleep(builder.COALESCE_S + 0.3)               # sin la retención, cada una construía
        assert builder.state()['builds'] == builds0
        assert registry.meta('impact', registry.generation())['stale'] is True
        assert builder.state()['holds'] == 1
    v1, _ = _db_version()
    assert v1 == v0 + 4
    deadline = time.time() + 15
    while time.time() < deadline and registry.generation().graph_version < v1:
        time.sleep(0.05)
    _settle()
    assert registry.generation().graph_version == v1
    assert builder.state()['builds'] - builds0 == 1
    assert builder.state()['holds'] == 0
    _stop_eager()
    assert signals.known()['v'] == v1


def test_coalesced_tiene_tope_y_no_bloquea_al_lector(monkeypatch):
    """Sin base: la retención caduca sola (HOLD_MAX_S) y `ensure` (un lector) nunca queda esperándola."""
    from core.hotviews import builder
    monkeypatch.setattr(builder, 'HOLD_MAX_S', 0.2)
    with builder.coalesced('t1'):
        assert builder._held() is True
        time.sleep(0.3)
        assert builder._held() is False                       # caducó aunque el bloque siga abierto
    assert builder.state()['holds'] == 0
