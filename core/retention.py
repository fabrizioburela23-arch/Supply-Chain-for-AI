"""core/retention.py — PURGA POR RETENCIÓN del libro (docs/INFRA_OPERATIVA.md §2.7; paso 26; decisión D3).

D3: dinero, ontología, comité y gobernanza = para siempre (blobs 'legal'); chat y qué-pasaría-si = 90 días
('standard_90d'). La purga NO borra filas: deja `decision_blobs.body = NULL` y conserva sha256, tipo, tamaño, clase y
fecha, con `purged_at` y `purge_decision_id` (la decisión `retention.purge` de la corrida). La integridad sigue
demostrable: el sello del libro nunca hashea cuerpos (las decisiones citan el sha) y `core/ledger.verify_blobs`
comprueba que cada cuerpo presente coincide con su sha y que cada cuerpo ausente fue purgado por una decisión
`retention.purge` (tests/test_retention_purge.py lo prueba sobre una base creada con el código anterior).

La base acepta SOLO esa forma de UPDATE (core/ledger_ddl `kh_blob_guard`: GUC `khipus.retention_job=on`, blob
standard_90d con > 90 días y cuerpo, mismo sha/tipo/tamaño/clase/fecha, purged_at y purge_decision_id puestos, y
ninguna decisión sync ni llamada de IA 'legal' que lo cite). Este módulo además excluye cualquier sha de 64 hex que
aparezca en el manifiesto/sujeto/salida de una decisión sync (notas, motivos, desbordes del manifiesto): un blob
de contenido idéntico creado antes como 90 días NUNCA se purga si algo legal lo cita.

También limpia las claves VIEJAS en texto plano de `decision_shadow.key` (hasta 200 caracteres del mensaje del
usuario, anteriores al paso 20): las reescribe como `hmac0:` + HMAC-SHA256 (clave derivada de SECRET_KEY, §2.7) con
una decisión `retention.migrate`; esa tabla no es append-only (es la sombra de Jev). Idempotente.

Tarea del reloj `retention_daily` (core/scheduler, cada hora; corre UNA vez por día UTC). Parámetros: artefacto
`ledger.retention` (días, tope por corrida, interruptor). Nunca IA. Sin DATABASE_URL no hace nada.
"""
import logging
import re
import threading
import time

log = logging.getLogger('khipu')

_LOCK = threading.Lock()
STATE = {'last_run': None, 'last_result': None, 'last_error': None, 'runs': 0}
ADVISORY_KEY = 0x4B48_5254      # 'KHRT'
_HEX64 = re.compile(r'[0-9a-f]{64}')

_INDEXES = (
    ('decisions', 'ix_dec_sync_inputs', "CREATE INDEX IF NOT EXISTS ix_dec_sync_inputs ON decisions (inputs_sha) "
                                        "WHERE durability = 'sync' AND inputs_sha IS NOT NULL"),
    ('decisions', 'ix_dec_sync_output', "CREATE INDEX IF NOT EXISTS ix_dec_sync_output ON decisions (output_sha) "
                                        "WHERE durability = 'sync' AND output_sha IS NOT NULL"),
    ('ai_calls', 'ix_aicall_legal_sys', "CREATE INDEX IF NOT EXISTS ix_aicall_legal_sys ON ai_calls (system_blob) "
                                        "WHERE retention_class = 'legal'"),
    ('ai_calls', 'ix_aicall_legal_in', "CREATE INDEX IF NOT EXISTS ix_aicall_legal_in ON ai_calls (input_blob) "
                                       "WHERE retention_class = 'legal'"),
    ('ai_calls', 'ix_aicall_legal_out', "CREATE INDEX IF NOT EXISTS ix_aicall_legal_out ON ai_calls (output_blob) "
                                        "WHERE retention_class = 'legal'"),
    ('decision_blobs', 'ix_blobs_purgeable', "CREATE INDEX IF NOT EXISTS ix_blobs_purgeable ON decision_blobs "
                                             "(created_at) WHERE body IS NOT NULL AND retention_class = 'standard_90d'"),
    # revisión batch G: "citado HACE POCO" (cualquier clase/durabilidad) — un blob se identifica por su contenido y
    # su fila guarda la PRIMERA vez que se vio; lo que lo cita dentro de la ventana lo mantiene vivo
    ('ai_calls', 'ix_aicall_sys_blob', "CREATE INDEX IF NOT EXISTS ix_aicall_sys_blob ON ai_calls (system_blob) "
                                       "WHERE system_blob IS NOT NULL"),
    ('ai_calls', 'ix_aicall_in_blob', "CREATE INDEX IF NOT EXISTS ix_aicall_in_blob ON ai_calls (input_blob) "
                                      "WHERE input_blob IS NOT NULL"),
    ('ai_calls', 'ix_aicall_out_blob', "CREATE INDEX IF NOT EXISTS ix_aicall_out_blob ON ai_calls (output_blob) "
                                       "WHERE output_blob IS NOT NULL"),
    ('decisions', 'ix_dec_inputs_sha', "CREATE INDEX IF NOT EXISTS ix_dec_inputs_sha ON decisions (inputs_sha) "
                                       "WHERE inputs_sha IS NOT NULL"),
    ('decisions', 'ix_dec_output_sha', "CREATE INDEX IF NOT EXISTS ix_dec_output_sha ON decisions (output_sha) "
                                       "WHERE output_sha IS NOT NULL"),
)


def ensure(conn):
    """Índices parciales de la purga (solo los que faltan: un CREATE INDEX toma candado aunque exista)."""
    from sqlalchemy import text

    from core import ledger_ddl as D
    have = {n for (n,) in conn.execute(text(
        "SELECT indexname FROM pg_indexes WHERE schemaname = current_schema()")).all()}
    tables = {n for (n,) in conn.execute(text(
        "SELECT tablename FROM pg_tables WHERE schemaname = current_schema()")).all()}
    for tbl, name, sql in _INDEXES:
        if tbl in tables and name not in have:
            D.safe_ddl(conn, sql)


def params():
    """Parámetros del artefacto `ledger.retention` (sin artefacto: los de D3)."""
    out = {'standard_days': 90, 'purge_enabled': True, 'purge_max_per_run': 20000}
    try:
        from core import governance
        p = governance.section('ledger.retention')
        out.update({k: p[k] for k in out if k in p})
    except Exception:  # noqa: BLE001
        pass
    # la base nunca deja purgar antes de 90 días (kh_blob_guard): un número menor no tiene efecto
    out['standard_days'] = max(90, int(out['standard_days']))
    return out


# ── candidatos ───────────────────────────────────────────────────────────────
_CANDIDATES = """
SELECT b.sha256, b.kind, b.size_bytes, b.created_at FROM decision_blobs b
WHERE b.retention_class = 'standard_90d' AND b.body IS NOT NULL AND b.purged_at IS NULL
  AND b.created_at < now() - make_interval(days => :days)
  AND NOT EXISTS (SELECT 1 FROM decision_refs r JOIN decisions d ON d.id = r.decision_id
                  WHERE r.ref_kind = 'blob' AND r.ref_id = b.sha256 AND d.durability = 'sync')
  AND NOT EXISTS (SELECT 1 FROM decisions d WHERE d.durability = 'sync' AND d.inputs_sha = b.sha256)
  AND NOT EXISTS (SELECT 1 FROM decisions d WHERE d.durability = 'sync' AND d.output_sha = b.sha256)
  AND NOT EXISTS (SELECT 1 FROM ai_calls a WHERE a.retention_class = 'legal' AND a.system_blob = b.sha256)
  AND NOT EXISTS (SELECT 1 FROM ai_calls a WHERE a.retention_class = 'legal' AND a.input_blob = b.sha256)
  AND NOT EXISTS (SELECT 1 FROM ai_calls a WHERE a.retention_class = 'legal' AND a.output_blob = b.sha256)
  -- revisión batch G: el MISMO contenido citado dentro de la ventana (system prompt del chat, qué-pasaría-si repetido)
  AND NOT EXISTS (SELECT 1 FROM ai_calls a WHERE a.system_blob = b.sha256
                  AND a.started_at >= now() - make_interval(days => :days))
  AND NOT EXISTS (SELECT 1 FROM ai_calls a WHERE a.input_blob = b.sha256
                  AND a.started_at >= now() - make_interval(days => :days))
  AND NOT EXISTS (SELECT 1 FROM ai_calls a WHERE a.output_blob = b.sha256
                  AND a.started_at >= now() - make_interval(days => :days))
  AND NOT EXISTS (SELECT 1 FROM decisions d WHERE d.inputs_sha = b.sha256
                  AND d.recorded_at >= now() - make_interval(days => :days))
  AND NOT EXISTS (SELECT 1 FROM decisions d WHERE d.output_sha = b.sha256
                  AND d.recorded_at >= now() - make_interval(days => :days))
  AND NOT EXISTS (SELECT 1 FROM decision_refs r WHERE r.ref_kind = 'blob' AND r.ref_id = b.sha256
                  AND r.recorded_at >= now() - make_interval(days => :days))
ORDER BY b.created_at
LIMIT :n
"""


def _cited_by_sync(conn, since):
    """Todos los sha de 64 hex citados en el manifiesto/sujeto/salida de una decisión sync registrada desde `since`
    (una decisión que cita un blob se registró a la vez o después de crearlo). Notas, motivos, desbordes."""
    from sqlalchemy import text
    rows = conn.execute(text(
        "SELECT d.manifest::text AS m, d.subject::text AS s, coalesce(d.output::text, '') AS o FROM decisions d "
        "WHERE d.durability = 'sync' AND d.recorded_at >= :since"), {'since': since})
    out = set()
    for r in rows:
        for col in (r.m, r.s, r.o):
            if col:
                out.update(_HEX64.findall(col))
    return out


def _cited_recently(conn, days):
    """Los sha de 64 hex citados en el manifiesto/sujeto/salida de CUALQUIER decisión (sync o async) registrada en
    los últimos `days` días: lo que una decisión reciente cita sigue vivo aunque su blob se viera por primera vez
    hace más tiempo (revisión batch G)."""
    from sqlalchemy import text
    rows = conn.execute(text(
        "SELECT d.manifest::text AS m, d.subject::text AS s, coalesce(d.output::text, '') AS o FROM decisions d "
        "WHERE d.recorded_at >= now() - make_interval(days => :d)"), {'d': int(days)})
    out = set()
    for r in rows:
        for col in (r.m, r.s, r.o):
            if col:
                out.update(_HEX64.findall(col))
    return out


def candidates(conn, days=None, limit=None):
    """[(sha, kind, size)] purgables YA (lo mismo que la base aceptaría + lo citado en manifiestos sync o en
    cualquier decisión de la ventana)."""
    from sqlalchemy import text
    p = params()
    days = int(days or p['standard_days'])
    rows = conn.execute(text(_CANDIDATES), {'days': days, 'n': int(limit or p['purge_max_per_run'])}).all()
    if not rows:
        return [], 0
    cited = _cited_by_sync(conn, min(r.created_at for r in rows)) | _cited_recently(conn, days)
    keep = [(r.sha256, r.kind, int(r.size_bytes)) for r in rows if r.sha256 not in cited]
    return keep, len(rows) - len(keep)


# ── purga ────────────────────────────────────────────────────────────────────
def purge(dry_run=False):
    """Una corrida: purga los blobs vencidos y deja UNA decisión `retention.purge` (system:retention_purge) con los
    conteos y la lista de sha purgados (blob legal). {'purged', 'bytes', 'by_kind', 'protected', 'decision_id'}."""
    from sqlalchemy import text

    from core import decisions, identity
    from ontology.db import session_scope
    p = params()
    if not p['purge_enabled'] and not dry_run:
        return {'skipped': 'disabled_by_policy'}
    t0 = time.perf_counter()
    with session_scope() as s:
        if not s.execute(text('SELECT pg_try_advisory_xact_lock(:k)'), {'k': ADVISORY_KEY}).scalar():
            return {'skipped': 'locked'}
        conn = s.connection()
        keep, protected = candidates(conn)
        by_kind, total = {}, 0
        for _sha, kind, size in keep:
            by_kind[kind] = by_kind.get(kind, 0) + 1
            total += size
        summary = {'candidates': len(keep) + protected, 'purged': 0 if dry_run else len(keep), 'bytes': total,
                   'by_kind': dict(sorted(by_kind.items())), 'protected_by_manifest': protected,
                   'standard_days': p['standard_days'], 'dry_run': bool(dry_run)}
        if dry_run:
            return summary
        with decisions.decision_scope('retention.purge', identity.system('retention_purge'), session=s,
                                      subject={'standard_days': p['standard_days'], 'n': len(keep)}) as ctx:
            n = 0
            if keep:
                s.execute(text("SELECT set_config('khipus.retention_job', 'on', true)"))
                shas = [k[0] for k in keep]
                for i in range(0, len(shas), 1000):
                    n += s.execute(text(
                        'UPDATE decision_blobs SET body = NULL, purged_at = clock_timestamp(), '
                        'purge_decision_id = CAST(:did AS uuid) WHERE sha256 = ANY(:shas) AND body IS NOT NULL'),
                        {'did': str(ctx.id), 'shas': shas[i:i + 1000]}).rowcount
                s.execute(text("SELECT set_config('khipus.retention_job', '', true)"))
                ctx.extra['purged_list_blob'] = ctx.blob('payload', {'purged': shas})
            summary['purged'] = n
            summary['ms'] = round((time.perf_counter() - t0) * 1000, 1)
            ctx.output = summary
            ctx.status = 'executed' if n else 'noop'
        summary['decision_id'] = str(ctx.id)
    return summary


# ── decision_shadow.key: texto plano viejo → HMAC ────────────────────────────
_PLAIN = ("SELECT id, key FROM decision_shadow WHERE key IS NOT NULL AND key <> '' AND key NOT LIKE 'hmac:%' "
          "AND key NOT LIKE 'hmac0:%' AND key NOT LIKE 'len:%' ORDER BY id LIMIT :n")


def migrate_shadow_keys(limit=5000):
    """Reescribe las claves en texto plano de decision_shadow (anteriores al paso 20) como 'hmac0:<hmac>' (HMAC del
    texto guardado, que ya venía recortado a 200 caracteres) o 'len:<n>' si la clave de privacidad es débil en
    producción. Una decisión `retention.migrate` con el conteo. Idempotente: sin filas, no escribe nada."""
    from sqlalchemy import text

    from core import decisions, identity
    from ontology.db import session_scope
    with session_scope() as s:
        try:
            rows = s.execute(text(_PLAIN), {'n': int(limit)}).all()
        except Exception as e:  # noqa: BLE001 — sin la tabla (base sin research.models)
            return {'skipped': type(e).__name__}
        if not rows:
            return {'migrated': 0}
        with decisions.decision_scope('retention.migrate', identity.system('retention_migrate'), session=s,
                                      subject={'table': 'decision_shadow', 'column': 'key', 'n': len(rows)}) as ctx:
            n = 0
            for r in rows:
                h = decisions.pii_hmac(r.key)
                new = ('hmac0:' + h['hmac'][:40]) if h.get('hmac') else f"len:{h.get('len', 0)}"
                n += s.execute(text('UPDATE decision_shadow SET key = :k WHERE id = :i AND key = :old'),
                               {'k': new, 'i': r.id, 'old': r.key}).rowcount
            ctx.output = {'migrated': n, 'key_id': decisions.pii_key()[1], 'format': 'hmac0'}
            ctx.status = 'executed'
    return {'migrated': n, 'decision_id': str(ctx.id)}


# ── tarea diaria ─────────────────────────────────────────────────────────────
def _ran_today(conn):
    from sqlalchemy import text
    return bool(conn.execute(text(
        "SELECT 1 FROM decisions WHERE kind = 'retention.purge' AND recorded_at >= date_trunc('day', now() AT TIME "
        "ZONE 'UTC') AT TIME ZONE 'UTC' LIMIT 1")).first())


def daily_job(force=False):
    """`system:retention_daily` (cada hora; una vez por día UTC): purga + limpieza de claves viejas de la sombra."""
    from ontology.db import _get_engine, ontology_available
    if not ontology_available():
        return {'skipped': 'no_database'}
    out = {}
    try:
        if not force:
            with _get_engine().connect() as c:
                if _ran_today(c):
                    return {'skipped': 'already_today'}
        out['purge'] = purge()
        out['shadow_keys'] = migrate_shadow_keys()
        with _LOCK:
            STATE.update(last_run=time.time(), last_result=out, last_error=None, runs=STATE['runs'] + 1)
    except Exception as e:  # noqa: BLE001
        with _LOCK:
            STATE['last_error'] = f'{type(e).__name__}: {str(e)[:160]}'
        raise
    return out


def status():
    """Para el 🩺: última corrida (de la base), pendientes y parámetros."""
    from sqlalchemy import text
    out = {'params': params(), 'last': None, 'pending': None}
    try:
        from ontology.db import _get_engine, ontology_available
        if not ontology_available():
            return out
        with _get_engine().connect() as c:
            r = c.execute(text("SELECT recorded_at, output FROM decisions WHERE kind = 'retention.purge' "
                               "ORDER BY recorded_at DESC LIMIT 1")).first()
            if r is not None:
                out['last'] = {'at': r.recorded_at.isoformat(), **(r.output or {})}
            old = int(c.execute(text(
                "SELECT count(*) FROM decision_blobs WHERE body IS NOT NULL AND retention_class = 'standard_90d' "
                "AND created_at < now() - make_interval(days => :d)"), {'d': out['params']['standard_days']}).scalar())
            # revisión batch G: 'pendientes' = lo que la PRÓXIMA purga vaciaría (el mismo predicado que purge());
            # lo viejo que algo vigente cita queda aparte como 'protegidos' (antes contaba y nunca llegaba a 0)
            pend = 0
            if old:
                ck = (old, out['last'] and out['last'].get('at'))
                hit = _PENDING_CACHE.get('v')
                if hit and hit[0] == ck and time.time() - hit[1] < _PENDING_TTL_S:
                    pend = hit[2]
                else:
                    keep, _prot = candidates(c)
                    pend = len(keep)
                    _PENDING_CACHE['v'] = (ck, time.time(), pend)
            out['pending'] = pend
            out['protected'] = max(0, old - pend)
    except Exception as e:  # noqa: BLE001
        out['error'] = type(e).__name__
    return out


_PENDING_CACHE = {}
_PENDING_TTL_S = 300
