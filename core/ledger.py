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
borrada o de un eslabón roto.

Paso 7 (§2.8, §7):
  · ANCLA DIARIA: `anchor()` sella, verifica y escribe una fila en `ledger_anchors` (una por día UTC y linaje);
    GET /api/ledger/anchor (público) da solo {day, head_seal, head_hash} y el GitHub Action smoke-mcp.yml la
    guarda fuera de la base (artefacto del run + resumen) — decisión D7;
  · CADENA ROTA: una verificación que encuentra sellos rotos deja la decisión `ledger.chain_break`
    (system:ledger_verify). Mientras no haya un `ledger.chain_ack` (persona con PIN) que la cite, el DINERO REAL
    queda bloqueado (`money_gate()`: brokerage/risk.run_checks lo consulta en preview Y confirm; papel sigue).
    Si no se puede leer el estado de la cadena estando la base configurada → bloquea (falla cerrado, D4);
  · LINAJE: `check_lineage()` detecta una restauración (system_identifier distinto o el contador de
    transacciones por DETRÁS del mayor txid ya escrito): deja `ledger.lineage_break` y abre un linaje nuevo en
    ledger_meta (el replay marca 'approximate' lo que no es grafo). No bloquea el dinero.

Linaje (`ledger_meta`): un uuid por base (cluster_id + primer txid). Lo cachea el proceso; init_schema lo
renueva (on_schema_init). Nunca IA; nunca UPDATE/DELETE.
"""
import hashlib
import json
import logging
import threading
import time
import uuid
import zlib

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
    # paso 9: el registro de gobernanza también entra a la cadena (qué reglas y números hubo, a prueba de cambios)
    ('gov_artifacts', 't.hash::text', 't.recorded_at, t.hash', 'text'),
    ('gov_releases', 't.release_hash::text', 't.recorded_at, t.release_hash', 'text'),
    # paso 21: cada pedido a la IA (core/ai_calls) también queda a prueba de cambios
    ('ai_calls', 't.id::text', 't.seq', 'uuid'),
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
        # el linaje VIGENTE es el más nuevo: tras una restauración (paso 7) se abre otro y los anteriores quedan
        row = c.execute(text('SELECT lineage_id FROM ledger_meta ORDER BY created_at DESC LIMIT 1')).first()
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


def verify(from_seal=1, limit=None, engine=None, max_broken=20, record_break=False):
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
    keys = []          # TODAS las rupturas (la lista `broken` se recorta a max_broken para mostrar; la decisión
    #                    de "¿hay algo NUEVO?" no: antes, tras reconocer una ruptura de ≥20 sellos, una alteración
    #                    nueva más adelante nunca entraba en la lista y el dinero real seguía habilitado)
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
                reason, cur = None, None
                if s.prev_hash != prev or chain_hash(s.prev_hash, s.row_table, s.row_id, s.row_sha) != s.hash:
                    reason, cur = 'chain', s.hash
                else:
                    cur = current.get(s.row_table, {}).get(s.row_id)
                    if cur is None:
                        reason = 'row_missing'
                    elif cur != s.row_sha:
                        reason = 'row_changed'
                if reason:
                    keys.append(break_key(s.seal_no, reason, cur))
                    if len(broken) < max_broken:
                        broken.append({'seal_no': int(s.seal_no), 'row_table': s.row_table, 'row_id': s.row_id,
                                       'reason': reason})
                prev = s.hash
                head = {'seal_no': int(s.seal_no), 'hash': s.hash}
            cursor = int(seals[-1].seal_no) + 1
        for a in _anchor_mismatches(c):     # el ancla de días anteriores sigue en la cadena (alterar + re-sellar)
            keys.append(break_key(a['seal_no'], 'anchor_mismatch', a['now_hash']))
            if len(broken) < max_broken:
                broken.append({'seal_no': a['seal_no'], 'row_table': 'ledger_anchors', 'row_id': a['day'],
                               'reason': 'anchor_mismatch'})
    out = {'ok': not keys, 'checked': checked, 'from_seal': from_seal, 'head': head, 'broken': broken,
           'broken_total': len(keys), 'broken_keys': keys,
           'ms': round((time.perf_counter() - t0) * 1000, 2)}
    with _LOCK:
        STATE['last_verify'] = {k: out[k] for k in ('ok', 'checked', 'from_seal', 'ms', 'broken_total')} | {
            'at': time.time()}
    if record_break and not out['ok']:      # paso 7: la ruptura queda en el libro y bloquea el dinero real
        try:
            out['break_id'] = str(record_chain_break(out, engine=engine) or '') or None
        except Exception as e:  # noqa: BLE001
            log.error('ledger: no se registró la ruptura de la cadena (%s)', type(e).__name__)
            out['break_record_error'] = type(e).__name__
    return out


def verify_blobs(engine=None, limit=None, batch=500):
    """Paso 26: los blobs se verifican POR SU SHA (la cadena de sellos nunca hashea cuerpos: las decisiones citan el
    sha, así una purga por retención no rompe `verify`). Cada cuerpo presente debe descomprimir a bytes cuyo sha256
    es su clave; cada cuerpo ausente debe estar purgado (purged_at) por una decisión `retention.purge`.
    {'ok', 'checked', 'present', 'purged', 'mismatch': [sha…], 'unexplained_null': [sha…], 'ms'}."""
    from sqlalchemy import text
    if engine is None:
        from ontology.db import _get_engine
        engine = _get_engine()
    t0 = time.perf_counter()
    out = {'checked': 0, 'present': 0, 'purged': 0, 'mismatch': [], 'unexplained_null': []}
    with engine.connect() as c:
        purge_ids = {str(r[0]) for r in c.execute(text(
            "SELECT id FROM decisions WHERE kind = 'retention.purge'")).all()}
        last = ''
        while limit is None or out['checked'] < limit:
            n = batch if limit is None else min(batch, limit - out['checked'])
            rows = c.execute(text('SELECT sha256, body, purged_at, purge_decision_id FROM decision_blobs '
                                  'WHERE sha256 > :last ORDER BY sha256 LIMIT :n'), {'last': last, 'n': n}).all()
            if not rows:
                break
            for r in rows:
                out['checked'] += 1
                if r.body is None:
                    if r.purged_at is not None and str(r.purge_decision_id) in purge_ids:
                        out['purged'] += 1
                    else:
                        out['unexplained_null'].append(r.sha256)
                    continue
                try:
                    ok = hashlib.sha256(zlib.decompress(bytes(r.body))).hexdigest() == r.sha256
                except Exception:  # noqa: BLE001
                    ok = False
                if ok:
                    out['present'] += 1
                else:
                    out['mismatch'].append(r.sha256)
            last = rows[-1].sha256
    out['ok'] = not out['mismatch'] and not out['unexplained_null']
    out['mismatch'], out['unexplained_null'] = out['mismatch'][:50], out['unexplained_null'][:50]
    out['ms'] = round((time.perf_counter() - t0) * 1000, 2)
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
            'last_verify': st.get('last_verify'), 'chain': _chain_summary(engine)}


def _chain_summary(engine=None):
    """Para el 🩺 y /api/ledger/status: ¿cadena rota? ¿dinero real bloqueado? última ancla (sin cuerpos)."""
    out = {}
    try:
        st = chain_state(engine=engine)
        out.update(broken=st['broken'], money_blocked=st['broken'], since=st['since'],
                   pending_ack=len(st.get('open_breaks') or []))
    except Exception as e:  # noqa: BLE001
        out.update(broken=None, money_blocked=True, error=type(e).__name__)
    try:
        a = latest_anchor(engine)
        out['anchor'] = {k: a[k] for k in ('day', 'head_seal', 'head_hash', 'verified')} if a else None
    except Exception:  # noqa: BLE001
        out['anchor'] = None
    return out


# ── paso 7: estado de la cadena, ancla diaria y linaje ──────────────────────
BREAK_KIND = 'ledger.chain_break'
ACK_KIND = 'ledger.chain_ack'
LINEAGE_KIND = 'ledger.lineage_break'
CHAIN_TTL_S = 10.0                  # caché del estado de la cadena (una consulta indexada; el ack la invalida)
FULL_VERIFY_MAX = 300_000           # hasta aquí el ancla re-verifica TODA la cadena (~10,5 ms / 1.000 filas)
_CHAIN = {'at': 0.0, 'state': None}


def _engine(engine=None):
    if engine is not None:
        return engine
    from ontology.db import _get_engine
    return _get_engine()


ANCHOR_CHECK_N = 60                 # últimas anclas del linaje vigente que verify compara con la cadena


def break_key(seal_no, reason, cur_hash=None):
    """Clave de una ruptura: sello + motivo + hash ACTUAL de la fila (o del eslabón). Un segundo cambio en una
    fila ya rota (y reconocida) da otra clave → ruptura nueva."""
    return f"{int(seal_no)}:{reason}:{(cur_hash or '-')[:16]}"


def _broken_key(broken):
    """Compatibilidad: claves sin hash (solo para listas `broken` sueltas)."""
    return sorted(f"{int(b['seal_no'])}:{b['reason']}" for b in (broken or ()))


def _anchor_mismatches(conn, n=ANCHOR_CHECK_N):
    """Anclas del linaje vigente cuyo (head_seal, head_hash) ya no está en ledger_seals (cadena re-sellada tras
    alterar filas, o la cabeza retrocedió). Una consulta indexada; [] si las tablas no existen."""
    from sqlalchemy import text
    try:
        with conn.begin_nested():
            rows = conn.execute(text(
                'SELECT a.day, a.head_seal, a.head_hash, s.hash AS now_hash FROM ('
                '  SELECT day, head_seal, head_hash FROM ledger_anchors WHERE lineage_id = ('
                '    SELECT lineage_id FROM ledger_meta ORDER BY created_at DESC LIMIT 1) AND head_seal > 0 '
                '  ORDER BY day DESC, id DESC LIMIT :n) a '
                'LEFT JOIN ledger_seals s ON s.seal_no = a.head_seal'), {'n': int(n)}).all()
    except Exception as e:  # noqa: BLE001
        log.debug('ledger: anclas no comparadas (%s)', type(e).__name__)
        return []
    return [{'day': r.day.isoformat(), 'seal_no': int(r.head_seal), 'anchor_hash': r.head_hash,
             'now_hash': r.now_hash} for r in rows if r.now_hash != r.head_hash]


def _known_break_keys(conn):
    """(claves exactas, prefijos viejos 'sello:motivo') de TODAS las rupturas registradas (reconocidas o no).
    Las rupturas nuevas guardan la lista completa en un blob (`subject.keys_blob`); las de antes, en subject."""
    from sqlalchemy import text
    exact, legacy, blobs = set(), set(), []
    for r in _decision_rows(conn, BREAK_KIND, 500):
        subj = r.subject or {}
        if subj.get('keys_blob'):
            blobs.append(subj['keys_blob'])
        for k in subj.get('broken_key') or ():
            (exact if k.count(':') >= 2 else legacy).add(k)
    if blobs:
        for b in conn.execute(text('SELECT body FROM decision_blobs WHERE sha256 = ANY(:s)'), {'s': blobs}):
            if b.body is not None:
                try:
                    exact.update(json.loads(zlib.decompress(bytes(b.body))).get('keys') or ())
                except Exception:  # noqa: BLE001
                    pass
    return exact, legacy


def _is_known(k, exact, legacy):
    return k in exact or k.rsplit(':', 1)[0] in legacy


def _invalidate_chain():
    with _LOCK:
        _CHAIN.update(at=0.0, state=None)


def _decision_rows(conn, kind, limit=50):
    from sqlalchemy import text
    return conn.execute(text(
        'SELECT id, parent_id, subject, output, recorded_at, principal_id FROM decisions WHERE kind = :k '
        'ORDER BY seq DESC LIMIT :n'), {'k': kind, 'n': limit}).all()


def record_chain_break(verify_out, engine=None):
    """Una verificación con sellos rotos → decisión `ledger.chain_break` (sync, sesión propia). Si TODOS sus
    sellos rotos ya están en una ruptura anterior (reconocida o no), no se repite: el dinero real solo vuelve a
    bloquearse si aparece algo NUEVO. Devuelve el id de la ruptura (nueva o la vigente) o None."""
    if not verify_out or verify_out.get('ok'):
        return None
    from core import decisions, identity
    from ontology.db import session_scope
    key = sorted(set(verify_out.get('broken_keys') or _broken_key(verify_out.get('broken'))))
    eng = _engine(engine)
    with eng.connect() as c:
        exact, legacy = _known_break_keys(c)
    new = [k for k in key if not _is_known(k, exact, legacy)]
    if key and not new:
        st = chain_state(engine=engine, fresh=True)
        return st.get('break_id')
    with session_scope() as s:
        with decisions.decision_scope(BREAK_KIND, identity.system('ledger_verify'), session=s,
                                      subject={'broken_key': new[:200], 'n_keys': len(new),
                                               'from_seal': verify_out.get('from_seal')}) as ctx:
            if len(new) > 200:              # la lista COMPLETA de lo nuevo (para no volver a contarlo)
                ctx.subject['keys_blob'] = ctx.blob('broken_keys', {'keys': new})
            ctx.output = {'checked': verify_out.get('checked'), 'head': verify_out.get('head'),
                          'broken': (verify_out.get('broken') or [])[:20], 'new_keys': new[:20],
                          'broken_total': verify_out.get('broken_total', len(key))}
            ctx.status = 'recorded'
        bid = ctx.id
    _invalidate_chain()
    log.error('ledger: CADENA ROTA (%d sello(s) nuevo(s)); dinero real bloqueado hasta ledger.chain_ack', len(new))
    return bid


def chain_state(engine=None, fresh=False):
    """{'broken', 'break_id', 'since', 'broken_count', 'acked': [...], 'error'}. Rota = hay una
    `ledger.chain_break` sin un `ledger.chain_ack` que la cite (parent_id). Caché de CHAIN_TTL_S."""
    now = time.time()
    with _LOCK:
        st = _CHAIN['state']
        if not fresh and st is not None and now - _CHAIN['at'] < CHAIN_TTL_S:
            return st
    eng = _engine(engine)
    with eng.connect() as c:
        breaks = _decision_rows(c, BREAK_KIND, 50)
        acks = {str(r.parent_id) for r in _decision_rows(c, ACK_KIND, 200) if r.parent_id is not None}
    open_ = [b for b in breaks if str(b.id) not in acks]
    st = {'broken': bool(open_), 'break_id': str(open_[0].id) if open_ else None,
          'since': open_[-1].recorded_at.isoformat() if open_ else None,
          'broken_count': sum(int((b.subject or {}).get('n_keys') or len((b.subject or {}).get('broken_key') or ()))
                              for b in open_),
          'open_breaks': [str(b.id) for b in open_], 'acked_breaks': len(breaks) - len(open_), 'error': None}
    with _LOCK:
        _CHAIN.update(at=now, state=st)
    return st


def money_gate(engine=None):
    """¿Puede moverse DINERO REAL? (ok, es, en). Cadena rota sin reconocer → no. Sin poder leer el estado con la
    base configurada → no (falla cerrado, D4). Sin DATABASE_URL no hay dinero real posible (solo papel)."""
    try:
        from ontology.db import ontology_available
        if not ontology_available():
            return (False, 'Libro de decisiones no disponible (sin base de datos): solo se opera en PAPEL',
                    'Decision ledger unavailable (no database): PAPER trading only')
        st = chain_state(engine=engine)
    except Exception as e:  # noqa: BLE001
        log.warning('ledger.money_gate: estado de la cadena ilegible (%s) → dinero real bloqueado', type(e).__name__)
        return (False, 'No se pudo comprobar la cadena del libro de decisiones: dinero real bloqueado (falla cerrado)',
                'Could not check the decision-ledger chain: real money blocked (fail closed)')
    if st.get('broken'):
        return (False, 'CADENA DEL LIBRO ROTA: el dinero real queda bloqueado hasta que el operador la reconozca '
                       'con PIN (🩺 → Libro → Reconocer)',
                'LEDGER CHAIN BROKEN: real money is blocked until the operator acknowledges it with the PIN '
                '(🩺 → Ledger → Acknowledge)')
    return True, 'Cadena del libro de decisiones íntegra', 'Decision-ledger chain intact'


def chain_ack(session, principal, note=None, break_id=None):
    """Reconoce la ruptura vigente (o `break_id`) — decisión `ledger.chain_ack` con parent_id = la ruptura.
    Exige una PERSONA con PIN. Devuelve {'ack_id', 'break_id'}; LookupError si no hay nada que reconocer."""
    from sqlalchemy import text

    from core import decisions
    if not getattr(principal, 'is_human_pin', False):
        raise PermissionError('reconocer la cadena rota exige una persona autenticada con PIN (op:…)')
    st = chain_state(fresh=True)
    target = break_id or st.get('break_id')
    if not target or target not in (st.get('open_breaks') or []):
        raise LookupError('no hay una ruptura de la cadena pendiente de reconocer' if not target else
                          f'la ruptura {target} no está pendiente')
    session.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))'), {'k': f'chain_ack:{target}'})
    dup = session.execute(text('SELECT id FROM decisions WHERE kind = :k AND parent_id = CAST(:p AS uuid)'),
                          {'k': ACK_KIND, 'p': target}).first()
    if dup is not None:
        raise ValueError(f'la ruptura ya fue reconocida por {dup[0]}')
    with decisions.decision_scope(ACK_KIND, principal, session=session, parent_id=uuid.UUID(target),
                                  subject={'break_id': target}) as ctx:
        ctx.cause('decision', target)
        if note:
            ctx.extra['note_blob'] = ctx.blob('payload', {'note': str(note)[:2000]})
        ctx.output = {'acknowledged': target}
        ctx.status = 'approved'
    _invalidate_chain()          # el caller vuelve a invalidar DESPUÉS del commit (ledger_api)
    return {'ack_id': str(ctx.id), 'break_id': target}


def latest_anchor(engine=None):
    from sqlalchemy import text
    with _engine(engine).connect() as c:
        r = c.execute(text('SELECT day, head_seal, head_hash, lineage_id, verified, checked, created_at '
                           'FROM ledger_anchors ORDER BY day DESC, id DESC LIMIT 1')).first()
    if r is None:
        return None
    return {'day': r.day.isoformat(), 'head_seal': int(r.head_seal), 'head_hash': r.head_hash,
            'lineage_id': str(r.lineage_id), 'verified': r.verified, 'checked': r.checked,
            'created_at': r.created_at.isoformat()}


def anchor(engine=None, force_verify=True):
    """Ancla del día (UTC de la base): sella lo pendiente, verifica la cadena (completa hasta FULL_VERIFY_MAX
    sellos; si no, desde la última ancla), registra la ruptura si la hay y escribe UNA fila por día y linaje
    (idempotente: si ya existe la devuelve). {'anchor': {...}, 'created': bool, 'verify': {...}}."""
    from sqlalchemy import text
    eng = _engine(engine)
    with eng.connect() as c:
        today = c.execute(text("SELECT (clock_timestamp() AT TIME ZONE 'UTC')::date")).scalar()
        lin = lineage_id(eng)
        have = c.execute(text('SELECT 1 FROM ledger_anchors WHERE day = :d AND lineage_id = :l'),
                         {'d': today, 'l': lin}).first()
    if have is not None:
        return {'anchor': latest_anchor(eng), 'created': False, 'verify': None}
    try:
        seal_job()
    except Exception as e:  # noqa: BLE001
        log.warning('ledger.anchor: sellado previo falló (%s)', type(e).__name__)
    ver = None
    if force_verify:
        with eng.connect() as c:
            head_no, _h = _head(c)
            last = c.execute(text('SELECT head_seal FROM ledger_anchors ORDER BY day DESC, id DESC LIMIT 1')).first()
        start = 1 if head_no <= FULL_VERIFY_MAX or last is None else int(last[0]) + 1
        ver = verify(from_seal=start, engine=eng)
        if not ver['ok']:
            record_chain_break(ver, engine=eng)
    with eng.begin() as c:
        _canonical_session(c)
        head_no, head_h = _head(c)
        c.execute(text('INSERT INTO ledger_anchors (day, head_seal, head_hash, lineage_id, verified, checked) '
                       'VALUES (:d, :n, :h, :l, :v, :k) ON CONFLICT (day, lineage_id) DO NOTHING'),
                  {'d': today, 'n': head_no, 'h': head_h, 'l': lin,
                   'v': None if ver is None else bool(ver['ok']), 'k': None if ver is None else ver['checked']})
    return {'anchor': latest_anchor(eng), 'created': True,
            'verify': None if ver is None else {k: ver[k] for k in ('ok', 'checked', 'from_seal', 'ms')}}


def anchor_job():
    """Tarea del reloj (`system:ledger_anchor`, cada hora): ancla del día si aún no existe + linaje."""
    from ontology.db import ontology_available
    if not ontology_available():
        return {'skipped': 'no_database'}
    out = {}
    try:
        out['lineage'] = check_lineage()
    except Exception as e:  # noqa: BLE001
        out['lineage_error'] = type(e).__name__
    res = anchor()
    out.update(created=res['created'], anchor=res['anchor'], verify=res['verify'])
    return out


def check_lineage(engine=None):
    """¿Hubo una restauración? (a) el cluster (pg_control_system().system_identifier) cambió respecto del linaje
    vigente, o (b) el contador de transacciones está POR DETRÁS del mayor txid ya escrito en `decisions`
    (los txid nunca retroceden en un mismo cluster). → decisión `ledger.lineage_break` + linaje nuevo en
    ledger_meta. Idempotente: el linaje nuevo ya no cumple la condición. {'ok', 'reason'?, 'lineage_id'}."""
    from sqlalchemy import text

    from core import ledger_ddl
    eng = _engine(engine)
    with eng.connect() as c:
        meta = c.execute(text('SELECT lineage_id, cluster_id FROM ledger_meta ORDER BY created_at DESC '
                              'LIMIT 1')).first()
        if meta is None:
            return {'ok': True, 'lineage_id': str(lineage_id(eng))}
        cluster = None
        try:
            with c.begin_nested():
                cluster = int(c.execute(text('SELECT system_identifier FROM pg_control_system()')).scalar() or 0)
        except Exception:  # noqa: BLE001
            cluster = None
        reason, detail = None, {}
        if cluster and int(meta.cluster_id or 0) and cluster != int(meta.cluster_id):
            reason = 'cluster_changed'
            detail = {'cluster_before': str(meta.cluster_id), 'cluster_now': str(cluster)}
        elif ledger_ddl.STATE.get('xid8') is not False:
            r = c.execute(text(
                "SELECT d.txid::text AS mx, pg_snapshot_xmax(pg_current_snapshot())::text AS cur, "
                "d.txid >= pg_snapshot_xmax(pg_current_snapshot()) AS behind "
                "FROM decisions d WHERE d.lineage_id = :l ORDER BY d.txid DESC LIMIT 1"),
                {'l': meta.lineage_id}).first()
            if r is not None and r.behind:
                reason = 'txid_behind'
                detail = {'max_txid': r.mx, 'current_xmax': r.cur}
    if reason is None:
        return {'ok': True, 'lineage_id': str(meta.lineage_id)}
    old = meta.lineage_id
    new = uuid.uuid4()
    with eng.begin() as c:
        c.execute(text('SELECT pg_advisory_xact_lock(:k)'), {'k': ADVISORY_KEY + 1})
        cur = c.execute(text('SELECT lineage_id FROM ledger_meta ORDER BY created_at DESC LIMIT 1')).first()
        if cur is not None and cur[0] != old:          # otro proceso ya abrió el linaje nuevo
            with _LOCK:
                _LINEAGE['id'] = cur[0]
            return {'ok': False, 'reason': reason, 'lineage_id': str(cur[0]), 'already_recorded': True}
        c.execute(text(f'INSERT INTO ledger_meta (lineage_id, cluster_id, first_txid, note) '
                       f'VALUES (:l, :c, {ledger_ddl.txid_expr()}, :n)'),
                  {'l': new, 'c': cluster or 0, 'n': f'paso 7: restauración detectada ({reason})'})
    with _LOCK:
        _LINEAGE['id'] = new
    try:
        from core import decisions, identity
        from ontology.db import session_scope
        with session_scope() as s:
            with decisions.decision_scope(LINEAGE_KIND, identity.system('ledger_lineage'), session=s,
                                          subject={'reason': reason, 'old_lineage': str(old)}) as ctx:
                ctx.output = {'reason': reason, **detail, 'old_lineage': str(old), 'new_lineage': str(new)}
                ctx.status = 'recorded'
    except Exception as e:  # noqa: BLE001
        log.error('ledger: no se registró ledger.lineage_break (%s)', type(e).__name__)
    log.error('ledger: RESTAURACIÓN detectada (%s): linaje nuevo %s', reason, new)
    return {'ok': False, 'reason': reason, 'lineage_id': str(new), **detail}
