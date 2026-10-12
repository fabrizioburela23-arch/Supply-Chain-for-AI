"""core/hotviews/builder.py — UN solo hilo constructor, señales agrupadas, doble búfer (INFRA_OPERATIVA §4.4).

Entradas: after_commit (camino rápido), LISTEN khipu_graph (escritores fuera del proceso) y el sondeo de 30 s
(core/scheduler, tarea 'hot_views'). Las señales se AGRUPAN durante HOTVIEWS_COALESCE_S (1 s) y nunca hay
más de una construcción en curso; si alguien está esperando una versión (una ruta /api/matrix/* que vio la
base más adelante), se construye sin esperar el agrupamiento.

Construir = source.load() (foto REPEATABLE READ de Postgres o el snapshot) → GraphCore → Impact → publicar
la Generation entera (una asignación) → una fila por vista en `hot_view_builds` (append-only, sin cuerpos).
Si falla, se queda la generación anterior (stale:true, last_error) y se reintenta con espera creciente.

Modo perezoso (pruebas, KHIPU_SCHEDULER=off): sin `start()`, el hilo solo construye cuando alguien lo pide
(`ensure`/`request_build`) — una escritura no dispara reconstrucciones que nadie va a leer.
"""
import logging
import os
import threading
import time

log = logging.getLogger('khipu')

COALESCE_S = max(0.0, min(10.0, float(os.getenv('HOTVIEWS_COALESCE_S', '1.0') or 1.0)))
VIEW_NAMES = ('graph_core', 'impact')

_COND = threading.Condition()
_ST = {'thread': None, 'eager': False, 'dirty': True, 'demand': 0, 'building': False, 'builds': 0,
       'failures': 0, 'consecutive_failures': 0, 'last_error': None, 'last_error_at': None,
       'last_build_ms': None, 'last_signal_at': None, 'last_build_at': None, 'started_at': None}


def _on_signal(name, version, ids):
    with _COND:
        _ST['dirty'] = True
        _ST['last_signal_at'] = time.time()
        _COND.notify_all()
    if _ST['eager']:
        _ensure_thread()


def _install():
    from core.hotviews import signals
    signals.subscribe(_on_signal)


_install()


def state():
    with _COND:
        out = {k: v for k, v in _ST.items() if k != 'thread'}
    out['thread_alive'] = bool(_ST['thread'] is not None and _ST['thread'].is_alive())
    return out


def _log_builds(g):
    """Bitácora append-only de qué contenía cada vista (§4.4). Nunca rompe la construcción."""
    if g.source != 'pg':
        return
    try:
        from sqlalchemy import text

        from ontology.db import session_scope
        with session_scope() as s:
            for name in VIEW_NAMES:
                v = g.views.get(name)
                if v is None:
                    continue
                n = len(getattr(v, 'ids', None) or getattr(v, 'sources', None) or [])
                s.execute(text(
                    'INSERT INTO hot_view_builds (name, generation, graph_version, release_hash, source, '
                    'content_sha, n, build_ms) VALUES (:n, :g, :v, :r, :s, :c, :k, :ms)'),
                    {'n': name, 'g': g.id, 'v': g.graph_version, 'r': g.release, 's': g.source,
                     'c': v.content_sha, 'k': n, 'ms': int(round(g.build_ms.get(name, 0)))})
    except Exception as e:  # noqa: BLE001
        log.debug('hot_view_builds no registrado: %s', type(e).__name__)


def build_once(data=None):
    """Construye y PUBLICA una generación (sincrónico). Lanza si la fuente falla."""
    from core.hotviews import registry, signals, source
    from core.hotviews.views import graph_core, impact
    t0 = time.perf_counter()
    if data is None:
        data = source.load()
    t1 = time.perf_counter()
    core = graph_core.build(data)
    t2 = time.perf_counter()
    imp = impact.build(core)
    t3 = time.perf_counter()
    rel, label = signals.release_hash()
    build_ms = {'read': round((t1 - t0) * 1000, 1), 'graph_core': round((t2 - t1) * 1000, 1),
                'impact': round((t3 - t2) * 1000, 1), 'total': round((t3 - t0) * 1000, 1)}
    g = registry.make(data, {'graph_core': core, 'impact': imp}, rel, label, build_ms,
                      {'graph_core': core.content_sha, 'impact': imp.content_sha})
    registry.publish(g)
    if data.source == 'pg' and data.lineage:
        signals._observe(g.graph_version, data.lineage, via='build')
    _log_builds(g)
    return g


def _loop():
    while True:
        with _COND:
            while not (_ST['dirty'] and (_ST['eager'] or _ST['demand'] > 0)):
                _COND.wait(timeout=30.0)
            demand = _ST['demand'] > 0
        if not demand and COALESCE_S > 0:
            time.sleep(COALESCE_S)                  # agrupa las señales de un lote de escrituras
        with _COND:
            _ST['dirty'] = False
            _ST['building'] = True
        try:
            g = build_once()
            with _COND:
                _ST.update(builds=_ST['builds'] + 1, consecutive_failures=0, last_build_ms=g.build_ms,
                           last_build_at=time.time())
        except Exception as e:  # noqa: BLE001
            with _COND:
                from core.hotviews.signals import _redact
                _ST.update(failures=_ST['failures'] + 1, consecutive_failures=_ST['consecutive_failures'] + 1,
                           last_error=_redact(f'{type(e).__name__}: {e}')[:200], last_error_at=time.time(),
                           dirty=True)
                wait = 0.0 if _ST['demand'] > 0 else min(60.0, 2.0 ** min(6, _ST['consecutive_failures']))
            log.warning('hotviews: construcción falló (%s); se conserva la generación anterior', type(e).__name__)
            if wait:
                with _COND:
                    _COND.notify_all()
                time.sleep(wait)
        finally:
            with _COND:
                _ST['building'] = False
                _COND.notify_all()


def _ensure_thread():
    with _COND:
        t = _ST['thread']
        if t is not None and t.is_alive():
            return
        t = threading.Thread(target=_loop, name='hotviews-builder', daemon=True)
        _ST['thread'] = t
        _ST['started_at'] = time.time()
        t.start()


def start(eager=True, listen=True):
    """Arranque del servidor: modo ansioso (reconstruye tras cada señal), LISTEN y primera construcción."""
    with _COND:
        _ST['eager'] = bool(eager) or _ST['eager']
        _ST['dirty'] = True
        _COND.notify_all()
    _ensure_thread()
    if listen:
        try:
            from core.hotviews import signals
            signals.start_listener()
        except Exception:  # noqa: BLE001
            pass
    return state()


def request_build():
    with _COND:
        _ST['dirty'] = True
        _COND.notify_all()
    _ensure_thread()


def _satisfies(g, min_version, lineage):
    if g is None:
        return False
    if min_version is None:
        return True
    if g.source != 'pg':
        return False
    if lineage is not None and g.lineage != lineage:
        return False
    return g.graph_version >= int(min_version)


def ensure(min_version=None, lineage=None, timeout=2.0):
    """La generación publicada si ya cubre (min_version, linaje); si no, pide una construcción y espera hasta
    `timeout` s. None si no llegó a tiempo (la ruta calcula directo y lo marca source:'direct')."""
    from core.hotviews import registry
    g = registry.generation()
    if _satisfies(g, min_version, lineage):
        return g
    deadline = time.time() + max(0.0, float(timeout))
    with _COND:
        _ST['dirty'] = True
        _ST['demand'] += 1
        _COND.notify_all()
    try:
        _ensure_thread()
        with _COND:
            while True:
                g = registry.generation()
                if _satisfies(g, min_version, lineage):
                    return g
                left = deadline - time.time()
                if left <= 0:
                    return None
                _COND.wait(timeout=left)
    finally:
        with _COND:
            _ST['demand'] -= 1


def current(timeout=2.0):
    """Para /api/hot/*: la generación publicada (aunque lleve atraso: se marca stale); si todavía no hay
    ninguna, espera la primera hasta `timeout` s."""
    from core.hotviews import registry
    g = registry.generation()
    if g is not None:
        if _ST['eager'] is False and registry.lag(g)[0]:
            request_build()                  # modo perezoso: la lectura pide ponerse al día (no espera)
        return g
    return ensure(None, None, timeout)
