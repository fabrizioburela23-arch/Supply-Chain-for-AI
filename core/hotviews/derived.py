"""core/hotviews/derived.py — vistas DERIVADAS de una generación, construidas una vez y en segundo plano
(INFRA_OPERATIVA §4.2 V3 Card + NRS, V2b DownCap; paso 14).

Una Generation (registry.py) publica juntas GraphCore + Impact + graph. Las vistas de lectura más pesadas (la
tarjeta de cada empresa, su NRS y su estructura) se derivan de ESA generación —nunca de otra— y se guardan aquí
con la clave `(generation.id, nombre)`: una tarjeta jamás mezcla un impacto de una versión con un grafo de otra.

    derived.get(g, 'card', fn)      # fn(g) UNA vez por generación (otros hilos esperan la misma construcción)
    derived.peek(g, 'card')         # lo ya construido o None (no construye: el camino de lectura nunca espera)
    derived.prewarm(g)              # el constructor, tras publicar: tarjeta + NRS + modelo del tensor en un hilo

Leer nunca reconstruye el grafo: lo único que se calcula a pedido es lo derivado de la generación vigente, una
vez. Se guardan las 2 últimas generaciones (la vigente y la anterior, para quien tomó la referencia vieja).
"""
import logging
import threading
import time

log = logging.getLogger('khipu')

_KEEP = 2
_LOCK = threading.Lock()
_STORE = {}           # (gen_id, name) → valor
_BUILDING = {}        # (gen_id, name) → threading.Event
_ORDER = []           # gen_ids en orden de llegada
_STATS = {'builds': {}, 'last_ms': {}, 'errors': 0, 'last_error': None, 'prewarms': 0}


def _evict_locked(gid):
    if gid not in _ORDER:
        _ORDER.append(gid)
    while len(_ORDER) > _KEEP:
        old = _ORDER.pop(0)
        for k in [k for k in _STORE if k[0] == old]:
            _STORE.pop(k, None)


def peek(g, name):
    if g is None:
        return None
    return _STORE.get((g.id, name))


def get(g, name, fn, timeout=30.0):
    """fn(g) una vez por (generación, nombre). Si otro hilo ya la está construyendo, espera hasta `timeout`."""
    key = (g.id, name)
    v = _STORE.get(key)
    if v is not None:
        return v
    with _LOCK:
        v = _STORE.get(key)
        if v is not None:
            return v
        ev = _BUILDING.get(key)
        mine = ev is None
        if mine:
            ev = threading.Event()
            _BUILDING[key] = ev
    if not mine:
        ev.wait(timeout)
        v = _STORE.get(key)
        if v is None:
            raise RuntimeError(f'vista derivada {name} no disponible / derived view {name} unavailable')
        return v
    t0 = time.perf_counter()
    try:
        v = fn(g)
        with _LOCK:
            _STORE[key] = v
            _evict_locked(g.id)
            _STATS['builds'][name] = _STATS['builds'].get(name, 0) + 1
            _STATS['last_ms'][name] = round((time.perf_counter() - t0) * 1000, 1)
        return v
    except Exception as e:  # noqa: BLE001
        _STATS['errors'] += 1
        _STATS['last_error'] = f'{name}: {type(e).__name__}: {str(e)[:160]}'
        raise
    finally:
        with _LOCK:
            _BUILDING.pop(key, None)
        ev.set()


def prewarm(g):
    """Tras publicar una generación: tarjeta, vector NRS y modelo del tensor (estructura) en un hilo aparte, así la
    primera lectura ya no paga los ~1-2 s. Nunca lanza."""
    if g is None:
        return

    def run():
        try:
            from core.hotviews.views import card
            cv = card.view(g)
            cv.nrs_all()
            cv.structure_model()
            _STATS['prewarms'] += 1
        except Exception as e:  # noqa: BLE001
            _STATS['last_error'] = f'prewarm: {type(e).__name__}: {str(e)[:160]}'
            log.debug('hotviews prewarm: %s', type(e).__name__)
    threading.Thread(target=run, name='hotviews-prewarm', daemon=True).start()


def stats():
    with _LOCK:
        return {'held': sorted({k[1] for k in _STORE}), 'generations': list(_ORDER), **{k: (dict(v) if isinstance(v, dict)
                                                                                           else v) for k, v in _STATS.items()}}


def reset():
    """Solo pruebas."""
    with _LOCK:
        _STORE.clear()
        _BUILDING.clear()
        _ORDER.clear()
