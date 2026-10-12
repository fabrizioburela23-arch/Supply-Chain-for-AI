"""core/hotviews/registry.py — la Generation publicada y el sobre de versión de cada respuesta (§4.1).

Una Generation es INMUTABLE: todas las vistas derivadas del grafo se publican JUNTAS (nunca una tarjeta de
una versión con un impacto de otra). Publicar = asignar una referencia (atómico bajo el GIL; medido 1,7 µs y 0
errores en 532 millones de lecturas concurrentes). Leer = tomar UNA referencia: `g = generation()`.
"""
import threading
import time
from collections import deque
from datetime import datetime, timezone

_GEN = [None]
_HISTORY = deque(maxlen=20)          # últimas construcciones (sin cuerpos), también sin base
_LOCK = threading.Lock()


class Generation:
    __slots__ = ('id', 'graph_version', 'lineage', 'release', 'release_label', 'source', 'built_at',
                 'built_ts', 'build_ms', 'views', 'content_sha', 'read_ms', 'extra')

    def view(self, name):
        return self.views.get(name)


def make(data, views, release, release_label, build_ms, content_sha):
    g = Generation()
    g.graph_version = int(data.graph_version)
    g.lineage = data.lineage
    g.release = release
    g.release_label = release_label
    g.source = data.source
    g.id = f'g{g.graph_version}.r{release[:8]}.{g.source}'
    g.built_ts = time.time()
    g.built_at = datetime.fromtimestamp(g.built_ts, tz=timezone.utc).isoformat(timespec='milliseconds')
    g.build_ms = build_ms
    g.views = views
    g.content_sha = content_sha
    g.read_ms = data.read_ms
    g.extra = dict(data.extra or {})
    return g


def generation():
    return _GEN[0]


def publish(g):
    _GEN[0] = g
    with _LOCK:
        _HISTORY.appendleft({'generation': g.id, 'graph_version': g.graph_version, 'source': g.source,
                             'built_at': g.built_at, 'build_ms': g.build_ms, 'content_sha': g.content_sha})


def history():
    with _LOCK:
        return list(_HISTORY)


def reset():
    """Solo pruebas: olvida la generación publicada."""
    _GEN[0] = None
    with _LOCK:
        _HISTORY.clear()


def lag(g):
    """(lag_versions, stale) contra lo que el proceso SABE (after_commit, LISTEN, sondeo) — sin ir a la base."""
    from core.hotviews import builder, signals
    if g is None:
        return None, True
    k = signals.known()
    if g.source == 'snapshot':
        lag_v = 0
    elif k.get('lineage') and g.lineage and k['lineage'] != g.lineage:
        lag_v = max(1, int(k.get('v') or 0) - g.graph_version)
    else:
        lag_v = max(0, int(k.get('v') or 0) - g.graph_version)
    st = builder.state()
    stale = bool(lag_v > 0 or st.get('dirty') or (st.get('last_error_at') or 0) > g.built_ts)
    return lag_v, stale


def meta(name, g, source_override=None):
    """El sobre `view` común a /api/hot/* y a las rutas /api/matrix/* que delegan."""
    if g is None:
        return {'name': name, 'generation': None, 'graph_version': None, 'release': None, 'built_at': None,
                'age_ms': None, 'source': source_override or 'none', 'stale': True, 'lag_versions': None}
    lag_v, stale = lag(g)
    return {'name': name, 'generation': g.id, 'graph_version': g.graph_version, 'release': g.release,
            'release_label': g.release_label, 'built_at': g.built_at,
            'age_ms': int((time.time() - g.built_ts) * 1000), 'source': source_override or g.source,
            'stale': stale, 'lag_versions': lag_v, 'method': 'propagate@1'}
