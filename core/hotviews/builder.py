"""core/hotviews/builder.py — UN solo hilo constructor, señales agrupadas, doble búfer (INFRA_OPERATIVA §4.4).

Entradas: after_commit (camino rápido), LISTEN khipu_graph (escritores fuera del proceso) y el sondeo de 30 s
(core/scheduler, tarea 'hot_views'). Las señales se AGRUPAN durante HOTVIEWS_COALESCE_S (1 s) y nunca hay
más de una construcción en curso; si alguien está esperando una versión (una ruta /api/matrix/* que vio la
base más adelante), se construye sin esperar el agrupamiento.

Construir = source.load() (foto REPEATABLE READ de Postgres o el snapshot) → GraphCore → Impact → graph (el
grafo de los lectores, paso 8; no va a hot_view_builds: su versión es la de la generación) → publicar
la Generation entera (una asignación) → una fila por vista en `hot_view_builds` (append-only, sin cuerpos).
Si falla, se queda la generación anterior (stale:true, last_error) y se reintenta con espera creciente.

Modo perezoso (pruebas, KHIPU_SCHEDULER=off): sin `start()`, el hilo solo construye cuando alguien lo pide
(`ensure`/`request_build`) — una escritura no dispara reconstrucciones que nadie va a leer.

Escrituras masivas (EXPANSION_5K E1.4): una transacción = UNA versión (signals.py), y una versión = UNA construcción:
el aviso de la misma versión llega dos veces al proceso (after_commit y su propio NOTIFY) y antes, si un lector había
cortado el agrupamiento, el segundo aviso caía DURANTE la construcción y repetía la misma versión. Ahora una señal
'graph' que la generación publicada ya cubre (versión y linaje que el proceso conoce) se descarta, también al terminar
una construcción. Lo que pide un lector (`ensure`) construye si la publicada no le sirve, pero un lector que llega
DURANTE la construcción de su versión no provoca otra igual; `request_build` y un cambio de release construyen siempre.
Un importador que parte el lote en VARIAS transacciones puede envolverlo en `with builder.coalesced('import'):` →
el modo ansioso espera a que termine (tope HOLD_MAX_S) y construye una vez; un lector que espera nunca queda
bloqueado por la retención. Entre medio el sobre dice stale:true (lag_versions > 0).
"""
import contextlib
import logging
import os
import threading
import time

log = logging.getLogger('khipu')

COALESCE_S = max(0.0, min(10.0, float(os.getenv('HOTVIEWS_COALESCE_S', '1.0') or 1.0)))
HOLD_MAX_S = 120.0                    # tope de `coalesced()`: una retención olvidada nunca congela las vistas
VIEW_NAMES = ('graph_core', 'impact')

_COND = threading.Condition()
_ST = {'thread': None, 'eager': False, 'dirty': True, 'force': False, 'demand': 0, 'building': False, 'builds': 0,
       'failures': 0, 'consecutive_failures': 0, 'last_error': None, 'last_error_at': None,
       'retry_at': 0.0, 'last_build_ms': None, 'last_signal_at': None, 'last_build_at': None,
       'started_at': None, 'skipped_signals': 0, 'skipped_builds': 0, 'holds': 0, 'hold_until': 0.0,
       'hold_reason': None}
_LOGGED = {}                          # vista → última generación registrada en hot_view_builds (sin repetir)


def _backoff(n):
    """Espera tras la n-ésima falla seguida: 0,5 s, 1, 2, 4… hasta 60 s — TAMBIÉN si hay lectores esperando
    (antes reintentaba en bucle cerrado y cada /api/matrix/* esperaba los HOT_WAIT_S enteros)."""
    return min(60.0, 0.5 * 2.0 ** max(0, n - 1))


def _covered(g=None):
    """¿La generación publicada ya cubre TODO lo que el proceso sabe del grafo (versión, linaje, release)? Entonces
    otra señal 'graph' de esa versión (el NOTIFY del propio commit, un sondeo) no necesita construir nada."""
    from core.hotviews import registry, signals
    g = registry.generation() if g is None else g
    if g is None or g.source != 'pg' or not release_current(g):
        return False
    k = signals.known()
    if k.get('lineage') and g.lineage != k['lineage']:
        return False
    return int(k.get('v') or 0) <= g.graph_version


def _on_signal(name, version, ids):
    with _COND:
        _ST['last_signal_at'] = time.time()
        if name == 'graph' and not _ST['dirty'] and not _ST['building'] and _covered():
            _ST['skipped_signals'] += 1         # misma versión otra vez (after_commit + NOTIFY): nada que hacer
            return
        _ST['dirty'] = True
        if name != 'graph':
            _ST['force'] = True                 # cambio de release: el contenido cambia sin versión nueva
        _COND.notify_all()
    if _ST['eager']:
        _ensure_thread()


def _on_release_change(old, new):
    """Gobernanza cambió el release vigente (governance._swap ya re-asignó E.DAMPING, pesos, tope…): la
    generación publicada se armó con el kernel VIEJO → reconstruir. Hasta entonces `lag()` la marca stale y
    `current()` espera la nueva (antes /api/hot/impact seguía con el kernel viejo y /api/hot/scenario con el
    nuevo, ambos con el sello viejo)."""
    try:
        from core.hotviews import hot
        hot.reset()                      # la generación privada del snapshot y lo derivado también eran del viejo
    except Exception:  # noqa: BLE001
        pass
    _on_signal('release', None, None)


def _install():
    from core import governance
    from core.hotviews import signals
    signals.subscribe(_on_signal)
    governance.on_release_change(_on_release_change)


def release_current(g):
    """¿La generación `g` se armó con el release de gobernanza VIGENTE? (en memoria, sin SQL)."""
    if g is None:
        return False
    try:
        from core.hotviews import signals
        return g.release == signals.release_hash()[0]
    except Exception:  # noqa: BLE001
        return True


_install()


def state():
    with _COND:
        out = {k: v for k, v in _ST.items() if k != 'thread'}
        out['held'] = _held()
    out['thread_alive'] = bool(_ST['thread'] is not None and _ST['thread'].is_alive())
    return out


def _held():
    """Hay una retención `coalesced()` vigente (y no venció su tope)."""
    return _ST['holds'] > 0 and time.time() < _ST['hold_until']


@contextlib.contextmanager
def coalesced(reason='bulk'):
    """Escrituras en VARIAS transacciones seguidas (un importador por bloques): el modo ansioso no reconstruye hasta
    salir del bloque (tope HOLD_MAX_S) → UNA construcción para todo. No frena a quien espera una versión (`ensure`)
    ni cambia lo que se escribe; mientras tanto el sobre de /api/hot/* dice stale:true."""
    with _COND:
        _ST['holds'] += 1
        _ST['hold_until'] = max(_ST['hold_until'], time.time() + float(HOLD_MAX_S))
        _ST['hold_reason'] = str(reason)[:60]
    try:
        yield
    finally:
        with _COND:
            _ST['holds'] = max(0, _ST['holds'] - 1)
            if _ST['holds'] == 0:
                _ST['hold_until'] = 0.0
                _ST['hold_reason'] = None
            _COND.notify_all()


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
                if v is None or _LOGGED.get(name) == g.id:
                    continue                  # misma generación (= mismo contenido): una sola fila
                n = len(getattr(v, 'ids', None) or getattr(v, 'sources', None) or [])
                s.execute(text(
                    'INSERT INTO hot_view_builds (name, generation, graph_version, release_hash, source, '
                    'content_sha, n, build_ms) VALUES (:n, :g, :v, :r, :s, :c, :k, :ms)'),
                    {'n': name, 'g': g.id, 'v': g.graph_version, 'r': g.release, 's': g.source,
                     'c': v.content_sha, 'k': n, 'ms': int(round(g.build_ms.get(name, 0)))})
        for name in VIEW_NAMES:
            if g.views.get(name) is not None:
                _LOGGED[name] = g.id
    except Exception as e:  # noqa: BLE001
        log.debug('hot_view_builds no registrado: %s', type(e).__name__)


def build_once(data=None):
    """Construye y PUBLICA una generación (sincrónico). Lanza si la fuente falla."""
    from core.hotviews import registry, signals, source
    from core.hotviews.views import graph as graph_view
    from core.hotviews.views import graph_core, impact
    t0 = time.perf_counter()
    if data is None:
        data = source.load()
    t1 = time.perf_counter()
    core = graph_core.build(data)
    t2 = time.perf_counter()
    imp = impact.build(core)
    t3 = time.perf_counter()
    gv = graph_view.build(data)          # paso 8: el grafo de los lectores, de la MISMA foto (None si no la trae)
    t4 = time.perf_counter()
    rel, label = signals.release_hash()
    build_ms = {'read': round((t1 - t0) * 1000, 1), 'graph_core': round((t2 - t1) * 1000, 1),
                'impact': round((t3 - t2) * 1000, 1), 'graph': round((t4 - t3) * 1000, 1),
                'total': round((t4 - t0) * 1000, 1)}
    views = {'graph_core': core, 'impact': imp}
    if gv is not None:
        views['graph'] = gv
    g = registry.make(data, views, rel, label, build_ms,
                      {'graph_core': core.content_sha, 'impact': imp.content_sha})
    if gv is not None:
        gv.attach(g)
    registry.publish(g)
    if data.source == 'pg' and data.lineage:
        signals._observe(g.graph_version, data.lineage, via='build')
    _log_builds(g)
    return g


def _ready_to_build():
    """Hay algo que construir y nadie lo frena: un lector esperando siempre; el modo ansioso, si no hay retención."""
    if not _ST['dirty']:
        return False
    return _ST['demand'] > 0 or (_ST['eager'] and not _held())


def _loop():
    while True:
        with _COND:
            while not _ready_to_build():
                wait = 30.0
                if _ST['dirty'] and _ST['eager'] and _held():
                    wait = max(0.05, min(1.0, _ST['hold_until'] - time.time()))   # re-mirar el tope
                _COND.wait(timeout=wait)
            if _ST['demand'] == 0 and COALESCE_S > 0:
                # agrupa las señales de un lote de escrituras; un lector que llega a esperar lo corta
                _COND.wait_for(lambda: _ST['demand'] > 0, timeout=COALESCE_S)
            if not _ST['force'] and _ST['demand'] == 0 and _covered():
                _ST['dirty'] = False            # las señales eran de una versión ya publicada
                _ST['skipped_builds'] += 1
                continue
            _ST['dirty'] = False
            _ST['force'] = False
            _ST['building'] = True
        try:
            g = build_once()
            with _COND:
                _ST.update(builds=_ST['builds'] + 1, consecutive_failures=0, retry_at=0.0, last_build_ms=g.build_ms,
                           last_build_at=time.time())
                if _ST['dirty'] and not _ST['force'] and _covered(g):
                    # el aviso que llegó DURANTE la construcción era de esta misma versión (p. ej. el NOTIFY del
                    # propio commit tras un lector que cortó el agrupamiento): no repetir la construcción
                    _ST['dirty'] = False
                    _ST['skipped_builds'] += 1
            if _ST['eager']:
                try:   # paso 14: tarjeta V3 + vector NRS + estructura, en segundo plano (la primera lectura no espera)
                    from core.hotviews import derived
                    derived.prewarm(g)
                except Exception:  # noqa: BLE001
                    pass
        except Exception as e:  # noqa: BLE001
            with _COND:
                from core.hotviews.signals import _redact
                n = _ST['consecutive_failures'] + 1
                wait = _backoff(n)
                _ST.update(failures=_ST['failures'] + 1, consecutive_failures=n,
                           last_error=_redact(f'{type(e).__name__}: {e}')[:200], last_error_at=time.time(),
                           retry_at=time.time() + wait, dirty=True, building=False)
                _COND.notify_all()              # quien espera ve la falla y calcula directo sin agotar su plazo
            log.warning('hotviews: construcción falló (%s); se conserva la generación anterior', type(e).__name__)
            with _COND:
                # espera interrumpible (antes time.sleep de hasta 60 s): si alguien suelta la espera (reset_backoff,
                # pruebas que recrean la base) el hilo no queda dormido mientras un lector agota su plazo
                _COND.wait_for(lambda: time.time() >= _ST['retry_at'], timeout=wait)
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
    """Arranque del servidor: modo ansioso (reconstruye tras cada señal), LISTEN y primera construcción.
    Idempotente: la tarea 'hot_views' lo llama cada 30 s y SOLO construye si todavía no hay ninguna
    generación — los cambios los detectan las señales y el sondeo (antes cada tick reconstruía todo y dejaba
    2 filas imborrables en hot_view_builds)."""
    from core.hotviews import registry
    with _COND:
        _ST['eager'] = bool(eager) or _ST['eager']
        if registry.generation() is None:
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


def reset_backoff():
    """Solo pruebas / arranque limpio: olvida las fallas seguidas y despierta al hilo si estaba esperando."""
    with _COND:
        _ST.update(consecutive_failures=0, retry_at=0.0)
        _COND.notify_all()


def request_build():
    with _COND:
        _ST['dirty'] = True
        _ST['force'] = True
        _COND.notify_all()
    _ensure_thread()


def _satisfies(g, min_version, lineage):
    if g is None or not release_current(g):
        return False
    if min_version is None:
        return True
    if g.source != 'pg':
        return False
    if lineage is not None and g.lineage != lineage:
        return False
    return g.graph_version >= int(min_version)


def _unknown_requirement(min_version, lineage):
    """¿(min_version, linaje) va más allá de lo que el proceso conoce? Solo entonces `_covered` podría dar por cubierta
    una generación que no le sirve al lector."""
    if min_version is None:
        return False                        # sin versión pedida: g falta o cambió el release → _covered ya es False
    try:
        from core.hotviews import signals
        k = signals.known()
        if lineage is not None and k.get('lineage') != lineage:
            return True
        return int(k.get('v') or 0) < int(min_version)
    except Exception:  # noqa: BLE001
        return True


def ensure(min_version=None, lineage=None, timeout=2.0):
    """La generación publicada si ya cubre (min_version, linaje); si no, pide una construcción y espera hasta
    `timeout` s. None si no llegó a tiempo (la ruta calcula directo y lo marca source:'direct')."""
    from core.hotviews import registry
    g = registry.generation()
    if _satisfies(g, min_version, lineage):
        return g
    deadline = time.time() + max(0.0, float(timeout))
    need_force = _unknown_requirement(min_version, lineage)
    with _COND:
        _ST['dirty'] = True
        if need_force:
            # lo que pide el lector no está en lo conocido (signals.known): "ya cubierta" no lo vería → construir
            # siempre. Si SÍ está (lo normal: read_db_version lo observó), no se fuerza: un lector que llega
            # DURANTE una construcción de esa versión no provoca otra igual (revisión E1.4)
            _ST['force'] = True
        if _ST['consecutive_failures'] and time.time() < _ST['retry_at']:
            _COND.notify_all()              # fallando y en espera: no hacer esperar al lector (calcula directo)
            backing_off = True
        else:
            backing_off = False
            _ST['demand'] += 1
            failures0 = _ST['failures']
            _COND.notify_all()
    if backing_off:
        _ensure_thread()
        return None
    try:
        _ensure_thread()
        with _COND:
            while True:
                g = registry.generation()
                if _satisfies(g, min_version, lineage):
                    return g
                if _ST['failures'] != failures0:
                    return None             # la construcción que esperábamos falló: directo, sin agotar el plazo
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
    if g is not None and not release_current(g):
        # cambió el release de gobernanza: esperar la generación con el kernel nuevo (si no llega a tiempo, la
        # vieja sale marcada stale por lag())
        return ensure(None, None, timeout) or g
    if g is not None:
        if _ST['eager'] is False and registry.lag(g)[0]:
            request_build()                  # modo perezoso: la lectura pide ponerse al día (no espera)
        return g
    return ensure(None, None, timeout)
