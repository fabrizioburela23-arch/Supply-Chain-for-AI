"""core/hotviews/hot.py — EL accesor del grafo para los lectores del servidor (INFRA_OPERATIVA §4.7, paso 8).

    from core.hotviews import hot
    g = hot.graph()            # GraphView de la generación vigente (inmutable, versionada)
    g.nodes / g.by_id / g.links / g.alias / g.catalog / g.flow_degree / g.snapshot
    g.generation / g.graph_version / g.source / g.core (V1 GraphCore) / g.impact (V2 Impact)

    datos = hot.cached('world.graph', construir)   # lo derivado, UNA vez por generación

Reglas:
  · Un solo grafo: el de la Generation publicada por core/hotviews/builder (Postgres si hay DATABASE_URL, el
    snapshot si no). Ningún lector abre data/grafo_v0.json por su cuenta (tests/test_ops_single_source.py);
    solo source.py (la fuente de las vistas) y ontology/reconcile.py (compara catálogo ↔ base a propósito).
  · Nunca se queda sin respuesta: si la generación publicada no sirve para leer —todavía calentando, la base
    configurada pero caída, o una base que NO trae el catálogo (menos del MIN_COVERAGE de sus empresas: una base
    nueva o vacía dejaría a la app sin empresas)— los lectores usan una generación PRIVADA del snapshot, construida
    con el mismo código (`fallback: true`, `stale: true` si hay base). No se publica: /api/hot/* sigue siendo la
    de la base.
  · Las cachés de cada lector se claves con la generación (`cached`): una escritura económica (graph_version+1)
    renueva todo lo derivado en la siguiente lectura, en vez de "cargar una vez y para siempre".
"""
import threading
import time

HOT_WAIT_S = 3.0          # primera lectura del proceso: espera la primera construcción hasta 3 s
MIN_COVERAGE = 0.5        # fracción de empresas del catálogo que la base debe traer para servir a los lectores

_FB = {'key': None, 'view': None, 'built': 0, 'reason': None}
_FB_LOCK = threading.Lock()
_CACHE = {}               # nombre → (generation, valor)
_CACHE_LOCK = threading.Lock()
_STATS = {'fallback_reads': 0, 'published_reads': 0, 'fallback_builds': 0, 'last_fallback_reason': None}


def _usable(v):
    return v is not None and v.coverage >= MIN_COVERAGE


def published(wait=True, timeout=None):
    """La GraphView de la generación publicada si sirve para leer; None si no (o si no hay ninguna)."""
    from core.hotviews import builder, registry
    g = registry.generation()
    if wait:
        try:
            g = builder.current(HOT_WAIT_S if timeout is None else timeout)
        except Exception:  # noqa: BLE001 — sin vistas: los lectores siguen con el snapshot
            g = registry.generation()
    v = g.views.get('graph') if g is not None else None
    return v if _usable(v) else None


def _fallback_reason():
    from core.hotviews import registry
    g = registry.generation()
    if g is None:
        return 'warming'
    v = g.views.get('graph')
    if v is None:
        return 'no_reader_graph'
    return f'low_coverage:{v.coverage}'


def fallback(build=True):
    """Generación PRIVADA del snapshot (mismo código: GraphCore + Impact + graph), una por versión del archivo."""
    from core.hotviews import source
    try:
        _raw, sha = source._snapshot_bytes()
    except OSError:
        return None
    v = _FB['view']
    if v is not None and _FB['key'] == sha:
        return v
    if not build:
        return None
    with _FB_LOCK:
        if _FB['view'] is not None and _FB['key'] == sha:
            return _FB['view']
        from core.hotviews import registry, signals
        from core.hotviews.views import graph as graph_view
        from core.hotviews.views import graph_core, impact
        t0 = time.perf_counter()
        data = source.load_snapshot()
        core = graph_core.build(data)
        imp = impact.build(core)
        gv = graph_view.build(data)
        rel, label = signals.release_hash()
        g = registry.make(data, {'graph_core': core, 'impact': imp, 'graph': gv}, rel, label,
                          {'total': round((time.perf_counter() - t0) * 1000, 1)},
                          {'graph_core': core.content_sha, 'impact': imp.content_sha})
        gv.attach(g, fallback=True)
        _FB.update(key=sha, view=gv, built=time.time())
        _STATS['fallback_builds'] += 1
        return gv


def graph(wait=True, timeout=None):
    """EL grafo de los lectores. wait=False: no construye nada (devuelve lo ya disponible o None)."""
    v = published(wait=wait, timeout=timeout)
    if v is not None:
        _STATS['published_reads'] += 1
        return v
    _STATS['fallback_reads'] += 1
    try:
        _STATS['last_fallback_reason'] = _fallback_reason()
    except Exception:  # noqa: BLE001
        pass
    return fallback(build=wait)


def cached(name, fn, view=None):
    """fn(view) UNA vez por generación (y por nombre). Devuelve el valor derivado de la vista vigente."""
    v = view if view is not None else graph()
    if v is None:
        raise RuntimeError('grafo no disponible / graph unavailable')
    key = v.generation
    hit = _CACHE.get(name)
    if hit is not None and hit[0] == key:
        return hit[1]
    val = fn(v)
    with _CACHE_LOCK:
        _CACHE[name] = (key, val)
    return val


def cached_versions():
    """{nombre: generación} de lo que cada lector tiene derivado (todos deberían coincidir)."""
    with _CACHE_LOCK:
        return {k: v[0] for k, v in _CACHE.items()}


def invalidate(name=None):
    """Solo pruebas / diagnóstico: olvida lo derivado (todo o un nombre)."""
    with _CACHE_LOCK:
        if name is None:
            _CACHE.clear()
        else:
            _CACHE.pop(name, None)


def reset():
    """Solo pruebas: olvida lo derivado y la generación privada del snapshot."""
    invalidate()
    with _FB_LOCK:
        _FB.update(key=None, view=None, built=0)


def status():
    try:                       # sin construir ni contar como lectura
        v = published(wait=False) or fallback(build=False)
    except Exception:  # noqa: BLE001
        v = None
    return {'reader': v.meta() if v is not None else None, 'min_coverage': MIN_COVERAGE,
            'cached': cached_versions(), 'stats': dict(_STATS),
            'fallback_built': bool(_FB['view'] is not None)}
