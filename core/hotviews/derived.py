"""core/hotviews/derived.py — vistas DERIVADAS de una generación, construidas una vez y en segundo plano
(INFRA_OPERATIVA §4.2 V3 Card + NRS, V2b DownCap; paso 14).

Una Generation (registry.py) publica juntas GraphCore + Impact + graph. Las vistas de lectura más pesadas (la
tarjeta de cada empresa, su NRS y su estructura) se derivan de ESA generación —nunca de otra— y se guardan aquí
con la clave `(generation.id, nombre)`: una tarjeta jamás mezcla un impacto de una versión con un grafo de otra.

    derived.get(g, 'card', fn)      # fn(g) UNA vez por generación (otros hilos esperan la misma construcción)
    derived.peek(g, 'card')         # lo ya construido o None (no construye: el camino de lectura nunca espera)
    derived.prewarm(g)              # el constructor, tras publicar: tarjeta + NRS + modelo del tensor en un hilo

Leer nunca reconstruye el grafo: lo único que se calcula a pedido es lo derivado de la generación vigente, una
vez. Se guardan como MÁXIMO 2 generaciones (`_KEEP`) CONTANDO la que se está construyendo (E1.3): antes de armar lo de
una generación nueva se suelta la más vieja, así una reconstrucción nunca tiene 3 copias en memoria. La que se suelta
es la de MENOR `built_ts` (o la que llegó primero); una generación más vieja que todas las guardadas se arma y se
devuelve sin guardarla (no desplaza a las nuevas). EXCEPCIÓN: la generación de los LECTORES (hot.graph(): la publicada o,
si no sirve, la privada del snapshot) siempre se guarda y nunca se suelta — si no, con los lectores en la privada cada
ficha se rearmaba en cada pedido.
"""
import logging
import threading
import time

log = logging.getLogger('khipu')

_KEEP = 2
_LOCK = threading.Lock()
_STORE = {}           # (gen_id, name) → valor
_BUILDING = {}        # (gen_id, name) → threading.Event
_ORDER = []           # gen_ids guardados (≤ _KEEP), de la más vieja a la más nueva
_AGE = {}             # gen_id → edad (built_ts de la generación; si no tiene, orden de llegada)
_SEQ = [0]
_STATS = {'builds': {}, 'last_ms': {}, 'errors': 0, 'last_error': None, 'prewarms': 0, 'evictions': 0,
          'uncached': 0}


class _Flight(threading.Event):
    """Una construcción en curso; `value` lo leen quienes la esperan (también si no se guardó)."""
    value = None


def _age(g):
    ts = getattr(g, 'built_ts', None)
    if isinstance(ts, (int, float)):
        return (float(ts), 0)
    _SEQ[0] += 1
    return (float('inf'), _SEQ[0])


def _drop_locked(gid):
    if gid in _ORDER:
        _ORDER.remove(gid)
    _AGE.pop(gid, None)
    for k in [k for k in _STORE if k[0] == gid]:
        _STORE.pop(k, None)
    _STATS['evictions'] += 1


def _reader_gid():
    """id de la generación que leen hoy los lectores (sin construir ni contar lecturas); None si no se sabe."""
    try:
        from core.hotviews import hot
        v = hot.published(wait=False) or hot._FB.get('view')
        g = getattr(v, 'generation_obj', None) if v is not None else None
        return g.id if g is not None else None
    except Exception:  # noqa: BLE001
        return None


def _admit_locked(g, reader=None):
    """Hace lugar para `g` ANTES de construir (como mucho _KEEP generaciones contando esta). False = `g` es más vieja
    que todas las guardadas (salvo la de los lectores) y el lugar está lleno: se construye pero no se guarda. La de los
    lectores (`reader`) siempre entra y nunca se suelta."""
    gid = g.id
    if gid in _ORDER:
        return True
    age = _age(g)
    others = [o for o in _ORDER if o != reader]
    if gid != reader and len(_ORDER) >= _KEEP and (not others or all(age < _AGE[o] for o in others)):
        return False
    while len(_ORDER) >= _KEEP and others:
        old = min(others, key=lambda o: _AGE[o])
        _drop_locked(old)
        others.remove(old)
    _AGE[gid] = age
    _ORDER.append(gid)
    _ORDER.sort(key=lambda o: _AGE[o])
    return True


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
            ev = _Flight()
            _BUILDING[key] = ev
    if not mine:
        ev.wait(timeout)
        v = _STORE.get(key)
        if v is None:
            v = ev.value
        if v is None:
            raise RuntimeError(f'vista derivada {name} no disponible / derived view {name} unavailable')
        return v
    t0 = time.perf_counter()
    try:
        reader = _reader_gid()
        with _LOCK:
            keep = _admit_locked(g, reader)          # suelta la más vieja ANTES de construir (E1.3)
        v = fn(g)
        ev.value = v
        with _LOCK:
            if keep and g.id in _ORDER:
                _STORE[key] = v
            else:
                _STATS['uncached'] += 1
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
            try:
                cv.structure_model()                 # lo que espera la primera ficha va primero; el NRS de todas después
            except Exception as e:  # noqa: BLE001 — un tensor roto no deja sin el vector NRS
                _STATS['last_error'] = f'prewarm structure: {type(e).__name__}: {str(e)[:160]}'
            cv.nrs_all()
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
        _AGE.clear()
