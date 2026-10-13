"""V7 AsOf (INFRA_OPERATIVA §4.2 y §5.5, paso 23): GraphCore + Impact de G(t, κ) — el grafo vigente en la fecha t
tal como Khipus lo CONOCÍA en κ (graph_version o instante; ontology/bitemporal.py).

  · Se construye con el MISMO código que la vista viva (graph_core.build → impact.build: mismo kernel
    `propagate_many`), sobre una foto REPEATABLE READ READ ONLY propia: nunca toma el hilo ni el candado del
    constructor vivo (core/hotviews/builder) ni publica nada — la generación vigente no se entera.
  · LRU de LRU_MAX entradas por (t, κ canónico, release): κ canónico = la versión del grafo (dos instantes que
    caen entre las mismas dos confirmaciones económicas dan el mismo grafo económico). Acertar ≈ 1 ms; fallar =
    leer + construir (medido en el informe del paso 23: ~0,3-0,6 s en el catálogo migrado).
  · Construcciones concurrentes: UNA a la vez (semáforo propio) y la misma clave no se construye dos veces
    (los demás esperan a la primera). Si la espera pasa de BUILD_WAIT_S → AsOfBusy (503 en la ruta).
  · Sin base (snapshot) no hay historia: AsOfUnavailable.
"""
import threading
import time
from collections import OrderedDict

LRU_MAX = 16
BUILD_WAIT_S = 20.0

_LRU = OrderedDict()                 # clave → (Generation, meta)
_LOCK = threading.Lock()
_INFLIGHT = {}                       # clave → threading.Event
_SEM = threading.BoundedSemaphore(1)
_STATS = {'hits': 0, 'misses': 0, 'builds': 0, 'busy': 0, 'last_build_ms': None, 'last_key': None}


class AsOfUnavailable(RuntimeError):
    pass


class AsOfBusy(RuntimeError):
    pass


def _iso(dt):
    return dt.isoformat() if dt is not None else None


def _resolve(session, as_of, known_at):
    """(t | None, Known) — κ por defecto = la versión actual (G(t, hoy) = el as_of de siempre)."""
    from ontology import bitemporal
    from ontology.service import _parse_dt
    t = _parse_dt(as_of) if as_of not in (None, '') else None
    known = bitemporal.resolve(session, known_at) if known_at not in (None, '') else None
    if known is None:
        known = bitemporal.now_known(session)
    return t, known


def load(session, t, known):
    """GraphData de G(t, κ) con la forma de core/hotviews/source (las mismas fórmulas que matrix/engine)."""
    from sqlalchemy import text

    from core.hotviews import source
    from matrix import engine as E
    from ontology import bitemporal, vocabulary as vocab
    from ontology.service import _links_active_at
    t0 = time.perf_counter()
    row = session.execute(text(
        "SELECT to_regclass('events')::oid, to_regclass('kh_versions')::oid")).first()
    lineage = f'{row[0]}.{row[1]}' if row else None
    objs = bitemporal.props_at(session, t=t, known=known, types=vocab.economic_types())
    ids = sorted(objs)
    meta = {i: source._meta_of(objs[i]['label'], objs[i]['type'], objs[i]['properties']) for i in ids}
    triples, flow_links = [], []
    # t=None: la tabla `links` tal como estaba en κ (κ = ahora → exactamente la vista viva; revisión del paso 23)
    links = _links_active_at(session, t, known=known)
    for l in links:
        props = l.get('properties') or {}
        triples.append((l['source'], l['target'], l['rel_type'],
                        E._eff_weight(l.get('weight'), props.get('source'), E.link_confidence(props))))
        flow_links.append({'source': l['source'], 'target': l['target'], 'type': l['rel_type']})
    factors = E._active_factors_known(session, t, known, links=links)    # = active_factors(t, κ), sin re-replay
    alias = {}
    try:
        snap, _sha = source._snapshot_parsed()
        alias.update(snap.get('node_id_alias') or {})
    except OSError:
        pass
    for oid, o in objs.items():
        if o.get('merged_into') and oid not in alias:
            alias[oid] = o['merged_into']
    return source.GraphData('asof', int(known.gv or 0), lineage, ids, meta, triples, flow_links, factors,
                            read_ms=round((time.perf_counter() - t0) * 1000, 1),
                            extra={'alias': alias, 'as_of': _iso(t), **known.to_dict()})


def _build(t, known, key):
    from core.hotviews import registry, signals
    from core.hotviews.views import graph_core, impact
    from ontology.db import get_session_factory
    t0 = time.perf_counter()
    s = get_session_factory()()
    try:
        s.connection(execution_options={'isolation_level': 'REPEATABLE READ', 'postgresql_readonly': True})
        data = load(s, t, known)
    finally:
        try:
            s.rollback()
        finally:
            s.close()
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
    meta = {'as_of': _iso(t), **known.to_dict(), 'key': repr(key)}
    _STATS['builds'] += 1
    _STATS['last_build_ms'] = build_ms['total']
    _STATS['last_key'] = repr(key)
    return g, meta


def get(as_of=None, known_at=None, timeout=BUILD_WAIT_S):
    """(Generation, meta) de G(as_of, known_at). Lanza KnownAtError/OntologyError (400), AsOfUnavailable, AsOfBusy."""
    from core.hotviews import signals
    from ontology.db import ontology_available, session_scope
    if not ontology_available():
        raise AsOfUnavailable('sin base de datos no hay historia / no database, no history')
    from sqlalchemy import text
    with session_scope() as s:
        t, known = _resolve(s, as_of, known_at)
        lin = tuple(s.execute(text("SELECT to_regclass('events')::oid, to_regclass('kh_versions')::oid")).first())
    key = (_iso(t), known.key(), signals.release_hash()[0], lin)   # linaje: otra base con la misma versión ≠
    while True:
        with _LOCK:
            hit = _LRU.get(key)
            if hit is not None:
                _LRU.move_to_end(key)
                _STATS['hits'] += 1
                return hit[0], dict(hit[1], cache='hit')
            ev = _INFLIGHT.get(key)
            if ev is None:
                ev = _INFLIGHT[key] = threading.Event()
                mine = True
            else:
                mine = False
        if not mine:
            if not ev.wait(timeout):
                _STATS['busy'] += 1
                raise AsOfBusy('vista AsOf ocupada / AsOf view busy')
            continue                       # la construyó otro: ahora está en el LRU (o falló: reintentar)
        try:
            if not _SEM.acquire(timeout=timeout):
                _STATS['busy'] += 1
                raise AsOfBusy('vista AsOf ocupada / AsOf view busy')
            try:
                _STATS['misses'] += 1
                g, meta = _build(t, known, key)
            finally:
                _SEM.release()
            with _LOCK:
                _LRU[key] = (g, meta)
                _LRU.move_to_end(key)
                while len(_LRU) > LRU_MAX:
                    _LRU.popitem(last=False)
            return g, dict(meta, cache='miss')
        finally:
            with _LOCK:
                _INFLIGHT.pop(key, None)
            ev.set()


def view_meta(g, meta, name='impact'):
    """El sobre `view` de una respuesta AsOf (misma forma que registry.meta + t/κ; nunca 'stale': es una foto)."""
    return {'name': name, 'generation': g.id, 'graph_version': g.graph_version, 'release': g.release,
            'release_label': g.release_label, 'built_at': g.built_at,
            'age_ms': int((time.time() - g.built_ts) * 1000), 'source': 'asof', 'stale': False,
            'lag_versions': None, 'method': 'propagate@1', 'build_ms': g.build_ms, **meta}


def stats():
    with _LOCK:
        return dict(_STATS, entries=len(_LRU), lru_max=LRU_MAX)


def reset():
    """Solo pruebas."""
    with _LOCK:
        _LRU.clear()
        _INFLIGHT.clear()
