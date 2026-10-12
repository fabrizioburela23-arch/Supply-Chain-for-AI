"""core/hotviews/signals.py — graph_version TOMADO AL CONFIRMAR + señales a las vistas (INFRA_OPERATIVA §4.3-4.5).

Paso a paso (medido en el Anexo B del diseño):
1. `apply_event` llama a `mark(session, ev)`: si el evento es ECONÓMICO (vínculo de un rel_type del kernel o
   'affects', objeto de un tipo `economic` del vocabulario o Factor, LinkStatusChanged, remoción comodín o
   dirigida) solo anota los ids en `session.info['kh_touched']` — sin candados.
2. El hook `before_commit` (SQLAlchemy, toda Session): si hay ids tocados,
   `UPDATE kh_versions SET v=v+1 WHERE name='graph' RETURNING v` + `INSERT INTO kh_tx_versions(txid, …)` +
   `pg_notify('khipu_graph', …)` en la MISMA transacción. El candado de la fila dura ~1 ms (desde el UPDATE
   hasta el COMMIT), así que el orden de `version` es el orden REAL de confirmación (arregla la carrera de
   MAX(recorded_at), MAP 3 §3.3).
3. El hook `after_commit` llama a `signal('graph', v, ids)` → el constructor de vistas (core/hotviews/builder).

Escritores fuera del proceso (CLI de reconcile, migración, el contenedor viejo durante un deploy): el hilo
`LISTEN khipu_graph` (start_listener) y el sondeo de 30 s (`poll`, desde core/scheduler) los ven.

NO mueven la versión: noticias, fuentes, simulaciones guardadas, notas, tesis, decisiones, ajustes de posición,
ActionExecuted, PriceObserved (W10-W12: antes cada noticia tiraba metrics/insights/ρ, 410-435 ms).

Linaje: `l{oid(events)}.{oid(kh_versions)}` — cambia si la tabla de eventos se re-crea (re-migración, tests),
así una caché nunca confunde la versión N de una base con la versión N de otra.

Este módulo es LIVIANO (lo importa ontology/service.py): nada de numpy aquí.
"""
import hashlib
import json
import logging
import os
import threading
import time

log = logging.getLogger('khipu')

CHANNEL = 'khipu_graph'
_LOCK = threading.Lock()
# Última versión conocida por el proceso (la mueven after_commit, LISTEN, el sondeo y on_schema_init).
_KNOWN = {'v': 0, 'lineage': None, 'at': None, 'via': None, 'ids': (), 'n_ids': 0}
_SUBSCRIBERS = []
_INSTALLED = [False]
_READY = {'ok': None, 'at': 0.0}
_RELEASE = {}
_STATS = {'bumps': 0, 'signals': 0, 'notifies': 0, 'polls': 0, 'poll_changes': 0, 'listen_errors': 0,
          'skipped_not_ready': 0, 'last_bump_ms': None}
_LISTENER = {'thread': None, 'stop': False, 'connected': False, 'last_error': None}


# ── qué es "económico" ─────────────────────────────────────────────────────
def kernel_rels():
    """Relaciones que entran a las matrices (REL_TYPES del vocabulario) + 'affects' (hiperaristas)."""
    try:
        from ontology import vocabulary as vocab
        return set(vocab.relation_types()) | {'affects'}
    except Exception:  # noqa: BLE001
        return {'supply', 'cloud', 'fab', 'license', 'partner', 'invest', 'deploy', 'owns', 'ppa', 'affects'}


def _economic_type(otype):
    if not otype:
        return False
    if otype == 'Factor':
        return True
    try:
        from ontology import vocabulary as vocab
        return otype in vocab.economic_types()
    except Exception:  # noqa: BLE001
        return otype in ('Company', 'Country', 'Energy', 'Material', 'Org', 'Policy', 'Product', 'Tech')


def pre_type(session, event_type, object_id):
    """Tipo del objeto ANTES de materializar (un ObjectUpdated que lo saca del grafo también es económico)."""
    if event_type not in ('ObjectCreated', 'ObjectUpdated') or not object_id:
        return None
    try:
        from ontology.models import ObjectRecord
        o = session.get(ObjectRecord, object_id)
        return o.type if o is not None else None
    except Exception:  # noqa: BLE001
        return None


def is_economic(session, ev, prev_type=None):
    t = ev.event_type
    p = ev.payload or {}
    props = p.get('properties') or {}
    if t == 'LinkStatusChanged':
        return True
    if t in ('LinkCreated', 'LinkRemoved'):
        if t == 'LinkCreated' and props.get('dedup_of'):
            return False                    # duplicado exacto: no-op en tablas y replay (G2)
        rel = p.get('rel_type') or p.get('type')
        if t == 'LinkRemoved' and (not rel or props.get('retracts_event_id')):
            return True                     # comodín o retracción dirigida: puede tocar cualquier relación
        return (rel or 'supply') in kernel_rels()
    if t in ('ObjectCreated', 'ObjectUpdated'):
        if _economic_type(prev_type) or _economic_type(p.get('type')):
            return True
        try:
            from ontology.models import ObjectRecord
            o = session.get(ObjectRecord, ev.object_id) if ev.object_id else None
            return bool(o is not None and _economic_type(o.type))
        except Exception:  # noqa: BLE001
            return False
    return False


def mark(session, ev, prev_type=None):
    """Anota los ids tocados por un evento económico (nunca lanza: vigilar no tumba una escritura)."""
    try:
        if not is_economic(session, ev, prev_type):
            return False
        bag = session.info.setdefault('kh_touched', set())
        for x in (ev.object_id, ev.target_id):
            if x:
                bag.add(str(x))
        if not ev.object_id and not ev.target_id:
            bag.add('*')
        return True
    except Exception:  # noqa: BLE001
        return False


# ── release (κ de configuración) ────────────────────────────────────────────
def release_hash():
    """(sha256, etiqueta). Hasta el registro de gobernanza (paso 9) el release es el del REPOSITORIO,
    sin aprobar: hash canónico de los parámetros del kernel que hoy fijan los números (vocabulario,
    SOLE_LINK_FLOOR, tope de fragilidad, descuentos y valores por defecto de propagate). El CÓDIGO no entra
    (cada deploy pediría aprobación); los parámetros sí."""
    if _RELEASE.get('hash'):
        return _RELEASE['hash'], _RELEASE['label']
    body = {}
    try:
        from ontology import vocabulary as vocab
        with open(vocab._path(), 'rb') as fh:
            body['vocabulary_sha'] = hashlib.sha256(fh.read()).hexdigest()
    except Exception:  # noqa: BLE001
        body['vocabulary_sha'] = None
    try:
        import inspect

        from matrix import engine as E
        sig = inspect.signature(E.propagate)
        body.update({
            'sole_link_floor': E.SOLE_LINK_FLOOR, 'fragility_cap': E.fragility_cap(),
            'bulk_weight_factor': E.bulk_weight_factor(), 'unverified_conf': E.UNVERIFIED_CONF,
            'rel_weights': dict(sorted(E.DEFAULT_REL_WEIGHTS.items())),
            'damping': sig.parameters['damping'].default, 'max_hops': sig.parameters['max_hops'].default,
            'threshold': sig.parameters['threshold'].default, 'bulk_sources': sorted(E.BULK_SOURCES),
        })
    except Exception:  # noqa: BLE001
        pass
    canon = json.dumps(body, sort_keys=True, separators=(',', ':'), default=str).encode()
    _RELEASE['hash'] = hashlib.sha256(canon).hexdigest()
    _RELEASE['label'] = 'repo-unapproved'
    _RELEASE['body'] = body
    return _RELEASE['hash'], _RELEASE['label']


# ── estado de la base ───────────────────────────────────────────────────────
def _ready(session):
    """¿Existen kh_versions/kh_tx_versions? Sondeo seguro (to_regclass nunca falla), cacheado 60 s."""
    now = time.time()
    if _READY['ok'] and now - _READY['at'] < 3600:
        return True
    if _READY['ok'] is False and now - _READY['at'] < 60:
        return False
    try:
        from sqlalchemy import text
        ok = session.execute(text(
            "SELECT to_regclass('kh_versions') IS NOT NULL AND to_regclass('kh_tx_versions') IS NOT NULL")).scalar()
    except Exception:  # noqa: BLE001
        ok = False
    _READY.update(ok=bool(ok), at=now)
    return bool(ok)


def read_db_version(session):
    """(v, linaje) de la base dentro de `session` (una lectura por PK, ~0,05 ms). None si no hay contador.
    Actualiza lo conocido por el proceso si la base va adelante o cambió de linaje."""
    from sqlalchemy import text
    if not _ready(session):
        return None
    try:
        row = session.execute(text(
            "SELECT v, to_regclass('events')::oid, to_regclass('kh_versions')::oid "
            "FROM kh_versions WHERE name = 'graph'")).first()
    except Exception:  # noqa: BLE001
        _READY.update(ok=None, at=0.0)
        raise
    if row is None:
        return (0, None)
    lineage = f'{row[1]}.{row[2]}'
    _observe(int(row[0]), lineage, via='db')
    return int(row[0]), lineage


def graph_key(session):
    """Clave de caché derivada del grafo: `g{v}.l{linaje}.r{release[:8]}` (reemplaza a _graph_epoch).
    Sin contador (base vieja o caída), una clave VOLÁTIL (no cachea de más)."""
    rel = release_hash()[0]
    try:
        r = read_db_version(session)
    except Exception:  # noqa: BLE001
        r = None
    if r is None:
        return f'vol-{time.time():.6f}'
    return f'g{r[0]}.l{r[1]}.r{rel[:8]}'


# ── hooks de SQLAlchemy ─────────────────────────────────────────────────────
def _before_commit(session):
    touched = session.info.pop('kh_touched', None)
    if not touched:
        return
    if not _ready(session):
        _STATS['skipped_not_ready'] += 1
        return
    from sqlalchemy import text

    from core import ledger_ddl
    t0 = time.perf_counter()
    rel = release_hash()[0]
    session.execute(text("SET LOCAL lock_timeout = '5s'"))
    v = session.execute(text(
        "INSERT INTO kh_versions (name, v) VALUES ('graph', 1) "
        "ON CONFLICT (name) DO UPDATE SET v = kh_versions.v + 1 RETURNING v")).scalar()
    ids = sorted(touched)
    session.execute(text(
        f"INSERT INTO kh_tx_versions (txid, name, version, release_hash, n_ids) "
        f"VALUES ({ledger_ddl.txid_expr()}, 'graph', :v, :rel, :n)"), {'v': v, 'rel': rel, 'n': len(ids)})
    sample, size = [], 0
    for x in ids:
        size += len(x) + 4
        if size > 6000:
            break
        sample.append(x)
    session.execute(text('SELECT pg_notify(:ch, :p)'),
                    {'ch': CHANNEL, 'p': json.dumps({'v': v, 'ids': sample, 'n': len(ids)}, separators=(',', ':'))})
    session.info['kh_committed'] = (int(v), tuple(sample), len(ids))
    _STATS['bumps'] += 1
    _STATS['last_bump_ms'] = round((time.perf_counter() - t0) * 1000, 3)


def _after_commit(session):
    c = session.info.pop('kh_committed', None)
    if c:
        signal('graph', c[0], c[1], n_ids=c[2], via='after_commit')


def _after_rollback(session):
    session.info.pop('kh_touched', None)
    session.info.pop('kh_committed', None)


def install():
    """Engancha los hooks a TODA Session (idempotente). Solo actúan si apply_event marcó ids."""
    if _INSTALLED[0]:
        return
    from sqlalchemy import event
    from sqlalchemy.orm import Session
    event.listen(Session, 'before_commit', _before_commit)
    event.listen(Session, 'after_commit', _after_commit)
    event.listen(Session, 'after_rollback', _after_rollback)
    _INSTALLED[0] = True


# ── señales en el proceso ───────────────────────────────────────────────────
def subscribe(fn):
    """fn(name, version, ids) — se llama en el hilo que confirmó: debe ser no bloqueante."""
    if fn not in _SUBSCRIBERS:
        _SUBSCRIBERS.append(fn)


def _observe(v, lineage, via, ids=(), n_ids=0):
    """Actualiza lo conocido. Devuelve True si cambió (versión mayor, o linaje distinto: otra base)."""
    with _LOCK:
        lin_changed = lineage is not None and lineage != _KNOWN['lineage']
        if not (lin_changed or v > _KNOWN['v']):
            return False
        _KNOWN['v'] = v
        if lineage is not None:
            _KNOWN['lineage'] = lineage
        _KNOWN.update(at=time.time(), via=via, ids=tuple(ids)[:200], n_ids=n_ids)
        return True


def signal(name, version, ids=(), n_ids=None, via='signal', lineage=None):
    _STATS['signals'] += 1
    changed = _observe(int(version), lineage, via, ids, n_ids if n_ids is not None else len(ids))
    for fn in list(_SUBSCRIBERS):
        try:
            fn(name, int(version), tuple(ids))
        except Exception as e:  # noqa: BLE001
            log.warning('hotviews: suscriptor falló (%s)', type(e).__name__)
    return changed


def known():
    with _LOCK:
        return dict(_KNOWN)


def stats():
    out = dict(_STATS)
    out['listener'] = {k: v for k, v in _LISTENER.items() if k != 'thread'}
    out['listener']['alive'] = bool(_LISTENER['thread'] and _LISTENER['thread'].is_alive())
    return out


def poll():
    """Sondeo (core/scheduler cada 30 s): compara kh_versions con lo conocido por si se perdió un aviso."""
    from ontology.db import ontology_available, session_scope
    if not ontology_available():
        return {'skipped': 'no_db'}
    _STATS['polls'] += 1
    before = known()
    with session_scope() as s:
        r = read_db_version(s)
    if r is None:
        return {'ready': False}
    if (r[0], r[1]) != (before['v'], before['lineage']):
        _STATS['poll_changes'] += 1
        for fn in list(_SUBSCRIBERS):
            try:
                fn('graph', r[0], ())
            except Exception:  # noqa: BLE001
                pass
    return {'v': r[0], 'lineage': r[1], 'changed': (r[0], r[1]) != (before['v'], before['lineage'])}


def on_schema_init():
    """init_schema terminó: relee (v, linaje) — una base re-creada es OTRO linaje — y avisa."""
    try:
        from core import ledger_ddl
        if ledger_ddl.STATE.get('ready'):
            _READY.update(ok=True, at=time.time())
        poll()
    except Exception as e:  # noqa: BLE001
        log.debug('hotviews.on_schema_init: %s', e)


# ── LISTEN khipu_graph (escritores fuera del proceso) ───────────────────────
def _dsn():
    from ontology.db import DATABASE_URL
    url = DATABASE_URL or ''
    if '://' in url:
        scheme, rest = url.split('://', 1)
        base = scheme.split('+', 1)[0]
        if base == 'postgres':
            base = 'postgresql'
        url = f'{base}://{rest}'
    return url


def _listen_loop():
    import select
    backoff = 5.0
    while not _LISTENER['stop']:
        conn = None
        try:
            import psycopg2
            conn = psycopg2.connect(_dsn(), connect_timeout=5)
            conn.set_isolation_level(0)          # AUTOCOMMIT: LISTEN entrega al confirmar
            with conn.cursor() as cur:
                cur.execute(f'LISTEN {CHANNEL}')
            _LISTENER.update(connected=True, last_error=None)
            backoff = 5.0
            while not _LISTENER['stop']:
                r, _, _ = select.select([conn], [], [], 30.0)
                if not r:
                    try:
                        poll()                   # 30 s sin avisos: sondeo barato
                    except Exception:  # noqa: BLE001
                        pass
                    continue
                conn.poll()
                while conn.notifies:
                    n = conn.notifies.pop(0)
                    _STATS['notifies'] += 1
                    try:
                        d = json.loads(n.payload or '{}')
                        signal('graph', int(d.get('v') or 0), d.get('ids') or (), n_ids=d.get('n'), via='notify')
                    except Exception:  # noqa: BLE001
                        pass
        except Exception as e:  # noqa: BLE001
            _STATS['listen_errors'] += 1
            _LISTENER.update(connected=False, last_error=f'{type(e).__name__}: {str(e)[:160]}')
            time.sleep(backoff)
            backoff = min(60.0, backoff * 2)
        finally:
            _LISTENER['connected'] = False
            try:
                if conn is not None:
                    conn.close()
            except Exception:  # noqa: BLE001
                pass


def start_listener():
    """Hilo demonio LISTEN (solo con DATABASE_URL). Idempotente."""
    from ontology.db import ontology_available
    if not ontology_available() or os.getenv('HOTVIEWS_LISTEN', 'on').lower() in ('off', '0', 'false', 'no'):
        return False
    t = _LISTENER['thread']
    if t is not None and t.is_alive():
        return True
    _LISTENER['stop'] = False
    t = threading.Thread(target=_listen_loop, name='hotviews-listen', daemon=True)
    _LISTENER['thread'] = t
    t.start()
    return True
