"""tests/test_ledger_chain.py — INFRA_OPERATIVA paso 6: sellado asíncrono y verificación de la cadena (core/ledger).

Garantiza (docs/INFRA_OPERATIVA.md §2.8 y §9):
  · transacción A abierta mientras B confirma → el sellador sella B y NO A (A no terminó); al confirmar A, la
    siguiente pasada la sella: sin huecos (cada evento/decisión/ref queda sellado exactamente una vez);
  · el sellado es idempotente y seguro con dos selladores a la vez (candado de asesoría + índice único);
  · broker_audit gana txid/seq (columnas tardías) y entra a la cadena;
  · manipular una fila (desactivando el disparador, como haría un superusuario) → verify marca el sello EXACTO
    (row_changed / row_missing); manipular un sello → 'chain';
  · linaje: una sola fila en ledger_meta; las decisiones la citan; un esquema re-creado es otro linaje.
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
pytestmark = needs_db


@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    with session_scope() as s:
        for oid in ('CH_A', 'CH_B'):
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company'}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=oid)
    yield engine
    Base.metadata.drop_all(engine)


def _unsealed(engine, table, idexpr='t.id::text'):
    from sqlalchemy import text
    with engine.connect() as c:
        return c.execute(text(f"SELECT count(*) FROM {table} t WHERE NOT EXISTS (SELECT 1 FROM ledger_seals s "
                              f"WHERE s.row_table = '{table}' AND s.row_id = {idexpr})")).scalar()


def _seal_all(engine, timeout=60):
    """Sella hasta que no quede nada pendiente (xmin es de todo el clúster: otra base con una transacción larga
    puede atrasar el sellado unos segundos; el sellador nunca sella lo que aún puede cambiar)."""
    from core import ledger
    t_end = time.time() + timeout
    while True:
        ledger.seal()
        left = sum(_unsealed(engine, t) for t in ('events', 'decisions', 'broker_audit')) + \
            _unsealed(engine, 'decision_refs', ledger._RID_REFS)
        if left == 0 or time.time() > t_end:
            return left
        time.sleep(0.25)


def _act(texto='nota'):
    from core import identity
    from ontology.actions import execute_action
    from ontology.db import session_scope
    meta = {}
    with session_scope() as s:
        execute_action(s, 'AnotarObjeto', {'object_id': 'CH_A', 'texto': texto}, 'op:fabrizio',
                       principal=identity.operator(), meta=meta)
    return meta['decision_id']


def test_transaccion_abierta_no_se_sella_hasta_terminar_y_no_quedan_huecos(db):
    from sqlalchemy import text

    from core import ledger
    ledger.seal()
    # A: abre una transacción y escribe un evento SIN confirmar
    conn_a = db.connect()
    tx_a = conn_a.begin()
    conn_a.execute(text("INSERT INTO events (id, event_type, object_id, payload, valid_from, source, actor, recorded_at) "
                        "VALUES (gen_random_uuid(), 'PriceObserved', 'CH_A', '{}'::jsonb, now(), 'test', 'A', "
                        "clock_timestamp())"))
    a_id = conn_a.execute(text("SELECT id::text FROM events WHERE actor = 'A'")).scalar()
    # B: confirma una Acción completa mientras A sigue abierta
    b_dec = _act('B confirma')
    r1 = ledger.seal()
    with db.connect() as c:
        sealed = {r[0] for r in c.execute(text("SELECT row_id FROM ledger_seals WHERE row_table IN "
                                               "('events', 'decisions')"))}
    # B tiene txid > A (A empezó antes) → ninguna de las dos es < xmin mientras A esté abierta
    assert a_id not in sealed and b_dec not in sealed
    assert r1.get('sealed') is not None
    tx_a.commit()
    conn_a.close()
    # xmin es de TODO el clúster: otra base con una transacción larga puede atrasar el sellado unos segundos
    sealed, t_end = set(), time.time() + 60
    while time.time() < t_end:
        ledger.seal()
        with db.connect() as c:
            sealed = {r[0] for r in c.execute(text("SELECT row_id FROM ledger_seals"))}
        if a_id in sealed and b_dec in sealed:
            break
        time.sleep(0.25)
    assert a_id in sealed and b_dec in sealed
    for table in ('events', 'decisions', 'decision_outcomes', 'broker_audit'):
        assert _unsealed(db, table) == 0, table
    assert _unsealed(db, 'decision_refs', ledger._RID_REFS) == 0
    assert _unsealed(db, 'kh_tx_versions', "t.name || ':' || t.version::text") == 0
    v = ledger.verify()
    assert v['ok'] and v['checked'] == v['head']['seal_no']


def test_sellado_idempotente_y_dos_selladores_a_la_vez(db):
    from sqlalchemy import text

    from core import ledger
    for i in range(5):
        _act(f'concurrencia {i}')
    out = []
    ths = [threading.Thread(target=lambda: out.append(ledger.seal())) for _ in range(3)]
    [t.start() for t in ths]
    [t.join() for t in ths]
    assert len(out) == 3 and all('sealed' in o or o.get('skipped') == 'locked' for o in out), out
    assert _seal_all(db) == 0
    assert ledger.seal()['sealed'] == 0
    with db.connect() as c:
        dup = c.execute(text('SELECT count(*) - count(DISTINCT (row_table, row_id)) FROM ledger_seals')).scalar()
    assert dup == 0
    assert ledger.verify()['ok']


def test_broker_audit_tiene_txid_y_entra_a_la_cadena(db):
    from sqlalchemy import text

    from brokerage.service import audit
    from core import ledger
    from ontology.db import session_scope
    with session_scope() as s:
        audit(s, 'system:test', 'chain_probe', detail={'n': 1})
    with db.connect() as c:
        row = c.execute(text("SELECT id, txid IS NOT NULL, seq IS NOT NULL FROM broker_audit "
                             "WHERE action = 'chain_probe'")).first()
    assert row[1] and row[2]
    assert _seal_all(db) == 0
    with db.connect() as c:
        assert c.execute(text("SELECT count(*) FROM ledger_seals WHERE row_table = 'broker_audit' AND row_id = :i"),
                         {'i': str(row[0])}).scalar() == 1


def test_linaje_unico_y_citado(db):
    from sqlalchemy import text

    from core import ledger
    with db.connect() as c:
        rows = c.execute(text('SELECT lineage_id FROM ledger_meta')).all()
        cited = {r[0] for r in c.execute(text('SELECT DISTINCT lineage_id FROM decisions'))}
    assert len(rows) == 1 and cited == {rows[0][0]}
    assert ledger.lineage_id() == rows[0][0]


def test_columna_tardia_nula_no_invalida_lo_sellado(db):
    """Las columnas tardías (ontology/db._COLUMNAS_TARDIAS) se añaden sin DEFAULT: la huella omite los NULL, así
    una columna nueva no hace que verify marque TODA la tabla como cambiada."""
    from sqlalchemy import text

    from core import ledger
    _act('antes de la columna')
    assert _seal_all(db) == 0
    with db.begin() as c:
        c.execute(text('ALTER TABLE events ADD COLUMN kh_probe text'))
    try:
        assert ledger.verify()['ok']
    finally:
        with db.begin() as c:
            c.execute(text('ALTER TABLE events DROP COLUMN kh_probe'))


def test_verify_marca_el_sello_exacto_de_una_fila_manipulada(db):
    """Último de la cadena: manipula filas desactivando los disparadores (lo que haría un superusuario)."""
    from sqlalchemy import text

    from core import ledger
    victim = _act('víctima')
    assert _seal_all(db) == 0
    assert ledger.verify()['ok']
    with db.connect() as c:
        seal_no = c.execute(text("SELECT seal_no FROM ledger_seals WHERE row_table = 'decisions' AND row_id = :i"),
                            {'i': victim}).scalar()
        ev_id, ev_seal = c.execute(text(
            "SELECT e.id::text, s.seal_no FROM events e JOIN ledger_seals s ON s.row_table = 'events' "
            "AND s.row_id = e.id::text WHERE e.actor = 'pytest' ORDER BY s.seal_no LIMIT 1")).first()
    with db.begin() as c:
        c.execute(text('ALTER TABLE decisions DISABLE TRIGGER decisions_no_modify'))
        c.execute(text("UPDATE decisions SET status = 'approved' WHERE id = :i"), {'i': victim})
        c.execute(text('ALTER TABLE decisions ENABLE TRIGGER decisions_no_modify'))
    v = ledger.verify()
    assert not v['ok']
    assert {'seal_no': seal_no, 'row_table': 'decisions', 'row_id': victim, 'reason': 'row_changed'} in v['broken']
    assert len(v['broken']) == 1
    # borrar un evento sellado → row_missing en SU sello
    with db.begin() as c:
        c.execute(text('ALTER TABLE events DISABLE TRIGGER events_no_modify'))
        c.execute(text('DELETE FROM events WHERE id = CAST(:i AS uuid)'), {'i': ev_id})
        c.execute(text('ALTER TABLE events ENABLE TRIGGER events_no_modify'))
    v = ledger.verify()
    assert {'seal_no': ev_seal, 'row_table': 'events', 'row_id': ev_id, 'reason': 'row_missing'} in v['broken']
    # manipular un sello → la cadena se rompe en ese eslabón
    with db.begin() as c:
        c.execute(text('ALTER TABLE ledger_seals DISABLE TRIGGER ledger_seals_no_modify'))
        c.execute(text("UPDATE ledger_seals SET row_sha = repeat('0', 64) WHERE seal_no = 2"))
        c.execute(text('ALTER TABLE ledger_seals ENABLE TRIGGER ledger_seals_no_modify'))
    v = ledger.verify()
    assert any(b['seal_no'] == 2 and b['reason'] == 'chain' for b in v['broken'])
    # verificación incremental desde un sello posterior no ve lo de antes
    v2 = ledger.verify(from_seal=seal_no + 1)
    assert all(b['seal_no'] > seal_no for b in v2['broken'])


def test_esquema_recreado_es_otro_linaje(db):
    from core import ledger
    from ontology.db import init_schema
    from ontology.models import Base
    before = ledger.lineage_id()
    Base.metadata.drop_all(db)
    assert init_schema(retries=1)
    assert ledger.lineage_id() != before
