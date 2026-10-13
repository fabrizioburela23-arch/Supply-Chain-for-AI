"""core/ledger_guard.py — GUARDIA DE PROYECCIONES «sin decisión no hay cambio» (docs/INFRA_OPERATIVA.md §2.1; paso 22).

La base, no la disciplina del código, vigila que toda escritura sobre las tablas que PROYECTAN decisiones
(claims, memos del comité, órdenes, propuestas, alertas, clientes del corretaje, ajustes de IA) ocurra dentro de
una transacción que lleva una decisión del libro: `core/decisions.decision_scope` marca la transacción con
`set_config('khipus.decision_id', <id>, true)` (local a la transacción: con el pool no se filtra a otra petición) y
el disparador `kh_require_decision()` lo comprueba.

    UPDATE/DELETE en GUARD_TABLES (+ INSERT en broker_orders), dos disparadores por tabla:
      `<t>_kh_guard` (BEFORE, inmediato): con el GUC puesto no hace nada; sin él, un NOTICE por (tabla, operación)
        para anotar el camino del código (nunca bloquea);
      `<t>_kh_guard_commit` (CONSTRAINT TRIGGER diferido AL CONFIRMAR): la transacción lleva decisión si el GUC quedó
        puesto o si escribió una fila en `decisions` (mismo txid) — así cuenta también la decisión que se registra
        DESPUÉS de la escritura en la misma transacción (confirmar una orden, aprobar una propuesta).
      sin decisión y modo 'warn'    → se confirma igual; se cuenta UNA vez por (transacción, tabla, operación) en
                                       `kh_guard_violations` (append-only) + RAISE WARNING 'kh_guard: …';
      sin decisión y modo 'enforce' → el COMMIT falla y la transacción entera se revierte.

Modo: lo manda el artefacto de gobernanza `policy.guard` (1.0.0 = 'warn'; 2.0.0 = 'enforce', `"activation": "pin"`:
solo Fabrizio lo activa con su PIN, después de ver el contador en 0 una semana). Las variables de entorno NO lo
cambian (D2). La base lo lee de `kh_guard_modes` (append-only; la última fila manda), que este módulo sincroniza con
el release vigente al arrancar y en cada cambio de release (`governance.on_release_change`). El GUC de sesión
`khipus.guard_mode` solo existe para las pruebas.

Camino del código: los avisos llegan al cliente (psycopg2 `connection.notices`) sin ida y vuelta extra; el oyente
`after_cursor_execute` de SQLAlchemy anota qué archivo:línea escribió (NOTICE inmediato) y el oyente `checkin` del
pool, al volver la conexión tras el COMMIT, cuenta los WARNING con ese camino (`status()['paths']`, 🩺 → Gobernanza).
Costo medido con decisión: una lectura de GUC por fila en cada disparador. Nunca IA. Nunca UPDATE/DELETE de sus
propias tablas.
"""
import logging
import os
import re
import sys
import threading
import time

log = logging.getLogger('khipu')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# tabla → operaciones vigiladas (los nombres REALES de los modelos: research/models.py, brokerage/models.py,
# ontology/models.py). broker_orders también en INSERT: una orden nueva sin decisión es justo lo que se evita.
GUARD_TABLES = {
    'research_claims': ('UPDATE', 'DELETE'),
    'committee_memos': ('UPDATE', 'DELETE'),
    'broker_orders': ('INSERT', 'UPDATE', 'DELETE'),
    'proposed_actions': ('UPDATE', 'DELETE'),
    'alerts': ('UPDATE', 'DELETE'),
    'broker_clients': ('UPDATE', 'DELETE'),
    'ai_settings': ('UPDATE', 'DELETE'),
}
# Columnas que NO son decisiones: un UPDATE que solo toca estas no cuenta para la guardia. Son el mundo observado (el
# máximo histórico y el último patrimonio que devolvió Alpaca, el estado crudo de Alpaca de una orden) o datos
# descriptivos que no mueven dinero ni reglas (nombre, correo y notas de un cliente). Todo lo demás exige decisión.
OBSERVATION_COLUMNS = {
    'broker_clients': ('hwm_equity', 'hwm_at', 'last_equity', 'last_snapshot_at', 'updated_at', 'name', 'email',
                       'notes'),
    'broker_orders': ('alpaca_status', 'updated_at'),
    # cuándo disparó por última vez una alerta (el disparo en sí queda como decisión alert.fire, async)
    'alerts': ('last_fired_at',),
    # la bitácora interna del memo (lista `audit`) y su hora; el estado, la decisión y el tamaño sí exigen decisión
    'committee_memos': ('audit', 'updated_at'),
}
GUARD_LOG_TABLES = ('kh_guard_violations', 'kh_guard_modes')     # append-only (core/ledger_ddl.APPEND_ONLY_TABLES)
MODES = ('warn', 'enforce')
DEFAULT_MODE = 'warn'

_LOCK = threading.Lock()
STATE = {'ready': False, 'mode_db': None, 'mode_policy': None, 'last_sync': None, 'last_error': None,
         'listener': False}
PATHS = {}             # (tabla, op, camino) → {'n', 'last_at'}
MAX_PATHS = 200
_NOTICE = re.compile(r'kh_guard: (\w+) (\w+)')
_NOTICE_PENDING = re.compile(r'kh_guard_pending: (\w+) (\w+)')

# INMEDIATO (BEFORE … FOR EACH ROW): con decisión en la transacción (GUC) no hace nada; sin ella, la PRIMERA vez por
# (tabla, operación) en la transacción manda un NOTICE para que el oyente anote el camino del código. Nunca bloquea.
_FN_REQUIRE_DECISION = """
CREATE OR REPLACE FUNCTION kh_require_decision() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  k text;
  seen text;
BEGIN
  IF coalesce(current_setting('khipus.decision_id', true), '') <> '' THEN
    RETURN COALESCE(NEW, OLD);
  END IF;
  IF TG_OP = 'UPDATE' AND TG_NARGS > 0 AND (to_jsonb(NEW) - TG_ARGV::text[]) = (to_jsonb(OLD) - TG_ARGV::text[]) THEN
    RETURN NEW;                       -- solo columnas de observación (OBSERVATION_COLUMNS)
  END IF;
  k := TG_TABLE_NAME || ':' || TG_OP;
  seen := coalesce(current_setting('khipus.guard_seen', true), '');
  IF position('|' || k || '|' in seen) = 0 THEN
    PERFORM set_config('khipus.guard_seen', seen || '|' || k || '|', true);
    RAISE NOTICE 'kh_guard_pending: % %', TG_TABLE_NAME, TG_OP;
  END IF;
  RETURN COALESCE(NEW, OLD);
END $$
"""

# AL CONFIRMAR (CONSTRAINT TRIGGER … DEFERRABLE INITIALLY DEFERRED): "la transacción que escribe lleva una decisión" =
# el GUC quedó puesto (decision_scope) o la transacción escribió una fila en `decisions` (txid). Así una decisión
# registrada DESPUÉS de la escritura, en la misma transacción (confirmar una orden, aprobar una propuesta), cuenta.
# Sin decisión: 'warn' → se cuenta una vez por (transacción, tabla, operación) + WARNING; 'enforce' → excepción y la
# transacción entera se revierte.
_FN_REQUIRE_DECISION_COMMIT = """
CREATE OR REPLACE FUNCTION kh_require_decision_commit() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  m text;
  n integer := 0;
  has boolean := false;
BEGIN
  IF coalesce(current_setting('khipus.decision_id', true), '') <> '' THEN
    RETURN NULL;
  END IF;
  IF TG_OP = 'UPDATE' AND TG_NARGS > 0 AND (to_jsonb(NEW) - TG_ARGV::text[]) = (to_jsonb(OLD) - TG_ARGV::text[]) THEN
    RETURN NULL;                      -- solo columnas de observación (OBSERVATION_COLUMNS)
  END IF;
  BEGIN
    -- una decisión de esta transacción, o el RESULTADO posterior de una decisión ya registrada (decision_outcomes:
    -- el estado de una orden que informa Alpaca es el resultado del envío, no una decisión nueva)
    SELECT EXISTS (SELECT 1 FROM decisions d WHERE d.txid = {txid})
        OR EXISTS (SELECT 1 FROM decision_outcomes o WHERE o.txid = {txid}) INTO has;
  EXCEPTION WHEN OTHERS THEN
    has := false;
  END;
  IF has THEN
    RETURN NULL;
  END IF;
  m := nullif(current_setting('khipus.guard_mode', true), '');
  IF m IS NULL THEN
    BEGIN
      SELECT g.mode INTO m FROM kh_guard_modes g ORDER BY g.id DESC LIMIT 1;
    EXCEPTION WHEN OTHERS THEN
      m := NULL;
    END;
  END IF;
  m := coalesce(m, 'warn');
  IF m = 'enforce' THEN
    RAISE EXCEPTION 'cambio sin decision registrada / change without a recorded decision (% %)', TG_TABLE_NAME, TG_OP
      USING HINT = 'kh_guard';
  END IF;
  BEGIN
    INSERT INTO kh_guard_violations (table_name, op, mode)
    VALUES (TG_TABLE_NAME, TG_OP, m) ON CONFLICT DO NOTHING;
    GET DIAGNOSTICS n = ROW_COUNT;
  EXCEPTION WHEN OTHERS THEN
    n := 1;
  END;
  IF n > 0 THEN
    RAISE WARNING 'kh_guard: % % sin decision_id / without decision_id', TG_TABLE_NAME, TG_OP;
  END IF;
  RETURN NULL;
END $$
"""

_TRIGGER = """
DO $$
BEGIN
  IF to_regclass('{t}') IS NOT NULL THEN
    -- otra lista de columnas de observación que la instalada → se recrea (los disparadores no guardan datos)
    IF EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = '{t}_kh_guard' AND tgrelid = '{t}'::regclass
               AND tgnargs <> {nargs}) THEN
      DROP TRIGGER {t}_kh_guard ON {t};
    END IF;
    IF EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = '{t}_kh_guard_commit' AND tgrelid = '{t}'::regclass
               AND tgnargs <> {nargs}) THEN
      DROP TRIGGER {t}_kh_guard_commit ON {t};
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = '{t}_kh_guard' AND tgrelid = '{t}'::regclass) THEN
      CREATE TRIGGER {t}_kh_guard BEFORE {ops} ON {t} FOR EACH ROW EXECUTE PROCEDURE kh_require_decision({args});
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = '{t}_kh_guard_commit' AND tgrelid = '{t}'::regclass) THEN
      CREATE CONSTRAINT TRIGGER {t}_kh_guard_commit AFTER {ops} ON {t} DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE PROCEDURE kh_require_decision_commit({args});
    END IF;
  END IF;
END $$
"""


def _tables_sql(txid_type, txid_expr):
    return (
        # una fila por (transacción, tabla, operación) sin decisión: el contador del 🩺 (append-only)
        f"""CREATE TABLE IF NOT EXISTS kh_guard_violations (
             id bigserial PRIMARY KEY,
             txid {txid_type} NOT NULL DEFAULT {txid_expr},
             table_name varchar(48) NOT NULL,
             op varchar(8) NOT NULL,
             mode varchar(8) NOT NULL,
             at timestamptz NOT NULL DEFAULT clock_timestamp(),
             UNIQUE (txid, table_name, op))""",
        'CREATE INDEX IF NOT EXISTS ix_kh_guard_violations_at ON kh_guard_violations (at DESC)',
        # el modo que lee el disparador: la ÚLTIMA fila manda (append-only; quién/qué release lo fijó)
        """CREATE TABLE IF NOT EXISTS kh_guard_modes (
             id bigserial PRIMARY KEY,
             mode varchar(8) NOT NULL CHECK (mode IN ('warn', 'enforce')),
             artifact varchar(64),
             release_hash char(64),
             set_at timestamptz NOT NULL DEFAULT clock_timestamp())""",
    )


def ensure(conn):
    """Tablas + función + disparadores (idempotente; lo llama core/ledger_ddl.ensure_all). Nunca lanza."""
    from core import ledger_ddl as D
    ok = True
    for sql in _tables_sql(D._txid_type(), D.txid_expr()):
        ok = D.safe_ddl(conn, sql) and ok
    if D.safe_ddl(conn, _FN_REQUIRE_DECISION) and D.safe_ddl(conn, _FN_REQUIRE_DECISION_COMMIT.replace(
            '{txid}', D.txid_expr())):
        for t, ops in GUARD_TABLES.items():
            obs = OBSERVATION_COLUMNS.get(t, ())
            ok = D.safe_ddl(conn, _TRIGGER.format(t=t, ops=' OR '.join(ops), nargs=len(obs),
                                                  args=', '.join(f"'{c}'" for c in obs))) and ok
    else:
        ok = False
    STATE['ready'] = bool(ok)
    return ok


def triggers_present(conn):
    from sqlalchemy import text
    rows = conn.execute(text(
        "SELECT c.relname, t.tgname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
        "WHERE t.tgname IN (c.relname || '_kh_guard', c.relname || '_kh_guard_commit')")).all()
    have = {(r, n) for r, n in rows}
    return {t: (t, f'{t}_kh_guard') in have and (t, f'{t}_kh_guard_commit') in have for t in GUARD_TABLES}


# ── modo (gobernanza → base) ─────────────────────────────────────────────────
def policy_mode():
    """El modo que pide el release VIGENTE (`policy.guard.mode`). Sin artefacto → 'warn'."""
    try:
        from core import governance
        m = str(governance.param('policy.guard', 'mode', DEFAULT_MODE)).strip().lower()
    except Exception:  # noqa: BLE001
        m = DEFAULT_MODE
    return m if m in MODES else DEFAULT_MODE


def db_mode(conn):
    from sqlalchemy import text
    try:
        return conn.execute(text('SELECT mode FROM kh_guard_modes ORDER BY id DESC LIMIT 1')).scalar()
    except Exception:  # noqa: BLE001
        return None


def sync_mode(engine=None):
    """Si la última fila de kh_guard_modes no es la del release vigente, agrega una (append-only). Nunca lanza."""
    from sqlalchemy import text
    want = policy_mode()
    STATE['mode_policy'] = want
    try:
        if engine is None:
            from ontology.db import _get_engine, ontology_available
            if not ontology_available():
                return None
            engine = _get_engine()
        with engine.begin() as c:
            c.execute(text("SET LOCAL lock_timeout = '3s'"))
            cur = db_mode(c)
            if cur != want:
                try:
                    from core import governance
                    art = f"policy.guard@{governance.artifact_semver('policy.guard')}"
                    rh = governance.release()[0]
                except Exception:  # noqa: BLE001
                    art, rh = None, None
                c.execute(text('INSERT INTO kh_guard_modes (mode, artifact, release_hash) VALUES (:m, :a, :r)'),
                          {'m': want, 'a': art, 'r': rh})
                if cur is not None:
                    log.warning('ledger_guard: modo de la guardia %s → %s (%s)', cur, want, art)
        STATE.update(mode_db=want, last_sync=time.time(), last_error=None)
        return want
    except Exception as e:  # noqa: BLE001
        STATE['last_error'] = f'{type(e).__name__}: {str(e)[:160]}'
        return None


def _on_release_change(_old, _new):
    sync_mode()


_REGISTERED = [False]


def register_release_listener():
    if _REGISTERED[0]:
        return
    try:
        from core import governance
        governance.on_release_change(_on_release_change)
        _REGISTERED[0] = True
    except Exception:  # noqa: BLE001
        pass


# ── camino del código (oyente de avisos, sin ida y vuelta extra) ─────────────
_SKIP = ('/site-packages/', '/dist-packages/', '/lib/python', 'core/ledger_guard.py', 'ontology/db.py',
         '<frozen', 'contextlib.py', 'threading.py')


def code_path(depth=4):
    """'brokerage/service.py:412 confirm_order < server.py:2501 trade_order' — los primeros marcos del repo."""
    out = []
    try:
        f = sys._getframe(2)
    except ValueError:
        return ''
    while f is not None and len(out) < depth:
        fn = f.f_code.co_filename
        if fn.startswith(ROOT) and not any(s in fn for s in _SKIP):
            out.append(f'{os.path.relpath(fn, ROOT)}:{f.f_lineno} {f.f_code.co_name}')
        f = f.f_back
    return ' < '.join(out)


def _note(table, op, path):
    key = (table, op, path)
    with _LOCK:
        cur = PATHS.get(key)
        if cur is None:
            if len(PATHS) >= MAX_PATHS:
                return
            cur = PATHS[key] = {'n': 0, 'last_at': None}
        cur['n'] += 1
        cur['last_at'] = time.time()
    trace = os.getenv('KH_GUARD_TRACE')          # solo diagnóstico/pruebas: una línea por aviso
    if trace:
        try:
            with open(trace, 'a', encoding='utf-8') as fh:
                fh.write(f'{table}\t{op}\t{path}\n')
        except Exception:  # noqa: BLE001
            pass


_PENDING = {}            # id(conexión DBAPI) → {(tabla, op): camino} de la transacción en curso


def _scan(dbapi_conn, path_now=None):
    """Lee los avisos de la conexión: 'kh_guard_pending' (escritura sin decisión AÚN) anota el camino; 'kh_guard'
    (al confirmar: de verdad sin decisión) lo cuenta con el camino anotado. Quita solo los suyos."""
    notices = getattr(dbapi_conn, 'notices', None)
    if not notices:
        return
    mine = [n for n in notices if 'kh_guard' in n]
    if not mine:
        return
    notices[:] = [n for n in notices if 'kh_guard' not in n]
    key = id(dbapi_conn)
    for n in mine:
        if 'kh_guard_pending:' in n:
            m = _NOTICE_PENDING.search(n)
            if m:
                pend = _PENDING.setdefault(key, {})
                pend.setdefault((m.group(1), m.group(2)), path_now if path_now is not None else code_path())
        else:
            m = _NOTICE.search(n)
            if m:
                path = (_PENDING.get(key) or {}).get((m.group(1), m.group(2))) or '?'
                _note(m.group(1), m.group(2), path)


def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    try:
        dbapi_conn = getattr(cursor, 'connection', None)
        if dbapi_conn is not None and getattr(dbapi_conn, 'notices', None):
            _scan(dbapi_conn)
    except Exception:  # noqa: BLE001 — vigilar nunca tumba una escritura
        pass


def _on_checkin(dbapi_conn, _record):
    """Al devolver la conexión al pool (tras confirmar o revertir): los WARNING del COMMIT ya llegaron."""
    try:
        if getattr(dbapi_conn, 'notices', None):
            _scan(dbapi_conn, path_now='?')
    except Exception:  # noqa: BLE001
        pass
    _PENDING.pop(id(dbapi_conn), None)


def install_listener(engine):
    from sqlalchemy import event
    try:
        if not event.contains(engine, 'after_cursor_execute', _after_cursor_execute):
            event.listen(engine, 'after_cursor_execute', _after_cursor_execute)
        if not event.contains(engine.pool, 'checkin', _on_checkin):
            event.listen(engine.pool, 'checkin', _on_checkin)
        STATE['listener'] = True
    except Exception:  # noqa: BLE001
        pass


def on_schema_init(engine):
    """Lo llama core/ledger_ddl.ensure_all después de crear todo: oyente + modo de la base + oyente de releases."""
    install_listener(engine)
    register_release_listener()
    sync_mode(engine)


# ── 🩺 ───────────────────────────────────────────────────────────────────────
_CACHE = {'at': 0.0, 'data': None}


def status(engine=None, days=7, fresh=False):
    """{mode, mode_policy, ready, by_table: [{table, op, n}], total, paths: [...], since_days}. Caché 60 s."""
    now = time.time()
    if not fresh and _CACHE['data'] is not None and now - _CACHE['at'] < 60:
        out = dict(_CACHE['data'])
    else:
        out = {'mode': None, 'mode_policy': policy_mode(), 'ready': STATE['ready'], 'by_table': [], 'total': 0,
               'since_days': days, 'triggers': None}
        try:
            from sqlalchemy import text
            if engine is None:
                from ontology.db import _get_engine, ontology_available
                if not ontology_available():
                    return {**out, 'available': False}
                engine = _get_engine()
            with engine.connect() as c:
                out['mode'] = db_mode(c)
                rows = c.execute(text(
                    "SELECT table_name, op, count(*) AS n, max(at) AS last FROM kh_guard_violations "
                    "WHERE at > clock_timestamp() - make_interval(days => :d) GROUP BY 1, 2 ORDER BY 3 DESC"),
                    {'d': int(days)}).all()
                out['by_table'] = [{'table': r.table_name, 'op': r.op, 'n': int(r.n),
                                    'last': r.last.isoformat() if r.last else None} for r in rows]
                out['total'] = sum(r['n'] for r in out['by_table'])
                tp = triggers_present(c)
                out['triggers'] = sum(1 for v in tp.values() if v)
                out['triggers_expected'] = len(tp)
            out['available'] = True
        except Exception as e:  # noqa: BLE001
            out['available'] = False
            out['error'] = type(e).__name__
        _CACHE.update(at=now, data=dict(out))
    with _LOCK:
        paths = sorted(({'table': t, 'op': o, 'path': p, 'n': v['n']} for (t, o, p), v in PATHS.items()),
                       key=lambda x: -x['n'])[:12]
    out['paths'] = paths
    return out


def _reset_for_tests():
    with _LOCK:
        PATHS.clear()
    _CACHE.update(at=0.0, data=None)
