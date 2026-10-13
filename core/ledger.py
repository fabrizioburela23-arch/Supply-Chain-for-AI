"""core/ledger.py — sellado y verificación del libro (docs/INFRA_OPERATIVA.md §2.8; paso 6 del plan).

UNA cadena de hashes para todo lo que es verdad o evidencia: events, kh_tx_versions, decisions, decision_refs,
decision_outcomes y broker_audit. El sellado es ASÍNCRONO (encadenar dentro de la transacción serializa los 12
hilos: p50 264 ms con 20 ms de trabajo, §2.8): la tarea `ledger_seal` de core/scheduler (cada 30 s):

  1. toma pg_try_advisory_xact_lock (un solo sellador aunque haya dos contenedores durante un deploy);
  2. lee la cabeza de la cadena;
  3. por cada tabla toma las filas NO selladas de transacciones TERMINADAS (txid < xmin del snapshot actual;
     las filas viejas sin txid —anteriores a la migración— también), en orden (txid, seq);
  4. row_sha = sha256 de to_jsonb(fila) en forma canónica (core.decisions.canonical), sin las columnas NULL
     (una columna tardía nueva no invalida lo ya sellado): sellar y verificar leen la base por el MISMO camino;
  5. hash = sha256(prev_hash ‖ row_table ‖ row_id ‖ row_sha) e inserta los sellos en lote.

`verify(from_seal)` recalcula la cadena y vuelve a leer cada fila: marca el sello EXACTO de una fila cambiada,
borrada o de un eslabón roto. El ancla diaria externa y el bloqueo del dinero con la cadena rota son el paso 7.

Linaje (`ledger_meta`): un uuid por base (cluster_id + primer txid). Lo cachea el proceso; init_schema lo
renueva (on_schema_init). Nunca IA; nunca UPDATE/DELETE.
"""
import hashlib
import json
import logging
import threading
import time
import uuid

log = logging.getLogger('khipu')

GENESIS = '0' * 64
SEAL_EVERY_S = 30
SEAL_BATCH = 5000
ADVISORY_KEY = 0x4B48_4C47      # 'KHLG'
_LOCK = threading.Lock()
_LINEAGE = {'id': None}
STATE = {'last_seal_at': None, 'last_sealed': 0, 'last_ms': None, 'last_error': None, 'runs': 0,
         'last_verify': None}

# (tabla, expresión del id de fila, orden, búsqueda por lote para verify)
_RID_REFS = ("t.decision_id::text || ':' || substr(encode(sha256(convert_to("
             "t.role || '|' || t.ref_kind || '|' || t.ref_id, 'UTF8')), 'hex'), 1, 24)")
SOURCES = (
    ('events', 't.id::text', 't.seq NULLS FIRST, t.recorded_at, t.id', 'uuid'),
    ('kh_tx_versions', "t.name || ':' || t.version::text", 't.version', 'text'),
    ('decisions', 't.id::text', 't.seq', 'uuid'),
    ('decision_refs', _RID_REFS, 't.recorded_at, t.decision_id, t.role, t.ref_kind, t.ref_id', 'refs'),
    ('decision_outcomes', 't.id::text', 't.id', 'bigint'),
    ('broker_audit', 't.id::text', 't.id', 'bigint'),
)
SEALED_TABLES = tuple(s[0] for s in SOURCES)


def _canon_sha(obj):
    from core.decisions import canonical
    return hashlib.sha256(canonical(obj)).hexdigest()


def row_sha(j):
    """sha de una fila leída con to_jsonb. Las columnas NULL se omiten: una columna NUEVA y nula (columna tardía,
    ALTER … ADD COLUMN sin DEFAULT) no cambia la huella de las filas ya selladas; poner o quitar un valor sí."""
    if isinstance(j, dict):
        j = {k: v for k, v in j.items() if v is not None}
    return _canon_sha(j)


def chain_hash(prev_hash, row_table, row_id, row_sha):
    return hashlib.sha256(f'{prev_hash}{row_table}{row_id}{row_sha}'.encode('utf-8')).hexdigest()


def _jsonb(v):
    return v if isinstance(v, (dict, list)) else json.loads(v)


# ── linaje ───────────────────────────────────────────────────────────────────
def on_schema_init(engine=None):
    """init_schema: el esquema pudo re-crearse (tests, re-migración) → otro linaje; se relee/crea ahora."""
    with _LOCK:
        _LINEAGE['id'] = None
    try:
        return lineage_id(engine)
    except Exception as e:  # noqa: BLE001
        log.warning('ledger: linaje no disponible (%s)', type(e).__name__)
        return None


def lineage_id(engine=None):
    """uuid del linaje de esta base (ledger_meta). Lo crea una vez, en su PROPIA transacción (no se pierde si
    la transacción del caller se revierte)."""
    v = _LINEAGE['id']
    if v is not None:
        return v
    from sqlalchemy import text

    from core import ledger_ddl
    if engine is None:
        from ontology.db import _get_engine
        engine = _get_engine()
    with engine.begin() as c:
        c.execute(text('SELECT pg_advisory_xact_lock(:k)'), {'k': ADVISORY_KEY + 1})
        row = c.execute(text('SELECT lineage_id FROM ledger_meta ORDER BY created_at LIMIT 1')).first()
        if row is None:
            cluster = 0
            try:
                with c.begin_nested():
                    cluster = int(c.execute(text('SELECT system_identifier FROM pg_control_system()')).scalar() or 0)
            except Exception:  # noqa: BLE001 — sin permiso para pg_control_system: 0 (el 🩺 lo verá)
                cluster = 0
            new = uuid.uuid4()
            c.execute(text(f'INSERT INTO ledger_meta (lineage_id, cluster_id, first_txid, note) '
                           f"VALUES (:l, :c, {ledger_ddl.txid_expr()}, 'paso 6: libro de decisiones')"),
                      {'l': new, 'c': cluster})
            v = new
        else:
            v = row[0] if isinstance(row[0], uuid.UUID) else uuid.UUID(str(row[0]))
    with _LOCK:
        _LINEAGE['id'] = v
    return v


# ── sesión canónica ──────────────────────────────────────────────────────────
# to_jsonb() pinta timestamptz con el desplazamiento de la zona de la SESIÓN, double precision según
# extra_float_digits y bytea según bytea_output: sin fijarlos, la MISMA fila da otro row_sha si la base cambia de
# TimeZone (ALTER DATABASE, un restore en un Postgres con zona local, PGTZ del cliente) y verify marcaría TODO
# como 'row_changed' (y el paso 7 bloquearía el dinero por un falso positivo). Sellar y verificar los fijan igual,
# SOLO para su transacción (SET LOCAL). UTC = lo que ya usaba la base de Railway (no invalida sellos previos).
_CANON_SETTINGS = (("TimeZone", "UTC"), ("extra_float_digits", "1"), ("bytea_output", "hex"))


def _canonical_session(conn):
    from sqlalchemy import text
    for k, v in _CANON_SETTINGS:
        conn.execute(text(f"SET LOCAL {k} = '{v}'"))


# ── sellado ──────────────────────────────────────────────────────────────────
def _existing(conn):
    from sqlalchemy import text
    rows = conn.execute(text(
        "SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = current_schema() "
        "AND column_name = 'txid'")).all()
    return {t for t, _c in rows}


def _head(conn):
    from sqlalchemy import text
    r = conn.execute(text('SELECT seal_no, hash FROM ledger_seals ORDER BY seal_no DESC LIMIT 1')).first()
    return (int(r[0]), r[1]) if r else (0, GENESIS)


def seal(engine=None, batch=SEAL_BATCH):
    """Una pasada del sellador. {'sealed': n, 'by_table': {...}, 'head': {seal_no, hash}, 'ms'} o
    {'skipped': 'locked'|'no_xid8'}. Idempotente; seguro con dos procesos (candado de asesoría)."""
    from sqlalchemy import text

    from core import ledger_ddl
    if ledger_ddl.STATE.get('xid8') is False:
        return {'skipped': 'no_xid8'}
    if engine is None:
        from ontology.db import _get_engine
        engine = _get_engine()
    t0 = time.perf_counter()
    by_table = {}
    with engine.begin() as c:
        c.execute(text("SET LOCAL lock_timeout = '5s'"))
        _canonical_session(c)
        if not c.execute(text('SELECT pg_try_advisory_xact_lock(:k)'), {'k': ADVISORY_KEY}).scalar():
            return {'skipped': 'locked'}
        have = _existing(c)
        seal_no, prev = _head(c)
        left = batch
        rows_out = []
        for table, rid, order, _lk in SOURCES:
            if left <= 0 or table not in have:
                continue
            rows = c.execute(text(
                f'SELECT {rid} AS rid, to_jsonb(t) AS j FROM {table} t '
                f'WHERE (t.txid IS NULL OR t.txid < pg_snapshot_xmin(pg_current_snapshot())) '
                f'AND NOT EXISTS (SELECT 1 FROM ledger_seals s WHERE s.row_table = :tb AND s.row_id = {rid}) '
                f'ORDER BY t.txid NULLS FIRST, {order} LIMIT :n'), {'tb': table, 'n': left}).all()
            for r in rows:
                rsha = row_sha(_jsonb(r.j))
                h = chain_hash(prev, table, r.rid, rsha)
                rows_out.append({'row_table': table, 'row_id': r.rid, 'row_sha': rsha, 'prev_hash': prev,
                                 'hash': h})
                prev = h
            by_table[table] = len(rows)
            left -= len(rows)
        if rows_out:
            from ontology.ledger_models import LedgerSeal
            t = LedgerSeal.__table__
            for i in range(0, len(rows_out), 500):        # VALUES en orden → seal_no en orden de la cadena
                c.execute(t.insert().values(rows_out[i:i + 500]))
        head_no = seal_no + len(rows_out)
    ms = round((time.perf_counter() - t0) * 1000, 2)
    with _LOCK:
        STATE.update(last_seal_at=time.time(), last_sealed=len(rows_out), last_ms=ms, last_error=None,
                     runs=STATE['runs'] + 1)
    return {'sealed': len(rows_out), 'by_table': by_table, 'head': {'seal_no': head_no, 'hash': prev}, 'ms': ms,
            'more': len(rows_out) >= batch}


def seal_job():
    """Tarea del reloj (core/scheduler, `system:ledger_seal`): sella hasta 4 lotes seguidos si hay atraso."""
    from ontology.db import ontology_available
    if not ontology_available():
        return {'skipped': 'no_database'}
    total, out = 0, {}
    try:
        for _ in range(4):
            out = seal()
            total += out.get('sealed', 0)
            if not out.get('more'):
                break
    except Exception as e:  # noqa: BLE001
        with _LOCK:
            STATE['last_error'] = f'{type(e).__name__}: {str(e)[:160]}'
        raise
    return {'sealed': total, 'head': out.get('head'), 'skipped': out.get('skipped')}


# ── verificación ─────────────────────────────────────────────────────────────
def _fetch_rows(conn, table, ids):
    """{row_id: row_sha} actual de las filas pedidas (mismo camino que el sellador)."""
    from sqlalchemy import text
    src = next(s for s in SOURCES if s[0] == table)
    rid, lk = src[1], src[3]
    if lk == 'uuid':
        cond, params = 't.id = ANY(CAST(:ids AS uuid[]))', {'ids': list(ids)}
    elif lk == 'bigint':
        cond, params = 't.id = ANY(CAST(:ids AS bigint[]))', {'ids': [int(x) for x in ids]}
    elif lk == 'refs':
        cond, params = 't.decision_id = ANY(CAST(:ids AS uuid[]))', {'ids': sorted({x.split(':', 1)[0] for x in ids})}
    else:
        cond, params = f'{rid} = ANY(:ids)', {'ids': list(ids)}
    rows = conn.execute(text(f'SELECT {rid} AS rid, to_jsonb(t) AS j FROM {table} t WHERE {cond}'), params).all()
    want = set(ids)
    return {r.rid: row_sha(_jsonb(r.j)) for r in rows if r.rid in want}


def verify(from_seal=1, limit=None, engine=None, max_broken=20):
    """Recalcula la cadena desde `from_seal` y vuelve a leer cada fila sellada.
    {'ok', 'checked', 'from_seal', 'head': {seal_no, hash}, 'broken': [{seal_no, row_table, row_id, reason}], 'ms'}
    reason ∈ chain (eslabón/hash recalculado distinto) · row_changed · row_missing."""
    from sqlalchemy import text
    if engine is None:
        from ontology.db import _get_engine
        engine = _get_engine()
    t0 = time.perf_counter()
    from_seal = max(1, int(from_seal or 1))
    broken, checked = [], 0
    head = {'seal_no': 0, 'hash': GENESIS}
    with engine.begin() as c:          # transacción explícita: SET LOCAL vale para todas las lecturas
        _canonical_session(c)
        prev = GENESIS
        if from_seal > 1:
            r = c.execute(text('SELECT hash FROM ledger_seals WHERE seal_no < :f ORDER BY seal_no DESC LIMIT 1'),
                          {'f': from_seal}).first()
            prev = r[0] if r else GENESIS
        cursor = from_seal
        while True:
            n = 1000 if limit is None else max(0, min(1000, limit - checked))
            if n == 0:
                break
            seals = c.execute(text('SELECT seal_no, row_table, row_id, row_sha, prev_hash, hash FROM ledger_seals '
                                   'WHERE seal_no >= :f ORDER BY seal_no LIMIT :n'), {'f': cursor, 'n': n}).all()
            if not seals:
                break
            per = {}
            for s in seals:
                per.setdefault(s.row_table, set()).add(s.row_id)
            current = {t: _fetch_rows(c, t, ids) for t, ids in per.items() if t in SEALED_TABLES}
            for s in seals:
                checked += 1
                reason = None
                if s.prev_hash != prev or chain_hash(s.prev_hash, s.row_table, s.row_id, s.row_sha) != s.hash:
                    reason = 'chain'
                else:
                    cur = current.get(s.row_table, {}).get(s.row_id)
                    if cur is None:
                        reason = 'row_missing'
                    elif cur != s.row_sha:
                        reason = 'row_changed'
                if reason and len(broken) < max_broken:
                    broken.append({'seal_no': int(s.seal_no), 'row_table': s.row_table, 'row_id': s.row_id,
                                   'reason': reason})
                prev = s.hash
                head = {'seal_no': int(s.seal_no), 'hash': s.hash}
            cursor = int(seals[-1].seal_no) + 1
    out = {'ok': not broken, 'checked': checked, 'from_seal': from_seal, 'head': head, 'broken': broken,
           'ms': round((time.perf_counter() - t0) * 1000, 2)}
    with _LOCK:
        STATE['last_verify'] = {k: out[k] for k in ('ok', 'checked', 'from_seal', 'ms')} | {'at': time.time()}
    return out


def status(engine=None):
    """Resumen barato para el 🩺 y /api/ledger/status (sin cuerpos)."""
    from sqlalchemy import text
    if engine is None:
        from ontology.db import _get_engine
        engine = _get_engine()
    with engine.connect() as c:
        n_dec = c.execute(text('SELECT count(*) FROM decisions')).scalar()
        seal_no, h = _head(c)
    with _LOCK:
        st = dict(STATE)
    lag = (time.time() - st['last_seal_at']) if st.get('last_seal_at') else None
    return {'decisions': int(n_dec or 0), 'head': {'seal_no': seal_no, 'hash': h},
            'lineage_id': str(_LINEAGE['id']) if _LINEAGE['id'] else None,
            'sealer': {'last_ms': st['last_ms'], 'last_sealed': st['last_sealed'], 'runs': st['runs'],
                       'last_error': st['last_error'], 'seconds_since_last': round(lag, 1) if lag else None,
                       'stale': bool(lag is not None and lag > 600)},
            'last_verify': st.get('last_verify')}
