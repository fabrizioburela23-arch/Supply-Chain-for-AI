"""ontology/checkpoints.py — PUNTOS DE CONTROL del grafo (docs/INFRA_OPERATIVA.md §5.5; paso 26).

El grafo "en una fecha" (`service.as_of_graph`) se reconstruye plegando TODOS los eventos: con ~5.000 eventos tarda
decenas de ms; MAP V M4 midió ~27 µs por evento → más de 1 s por encima de ~25.000. Un punto de control es la foto
YA PLEGADA del grafo en la fecha `valid_at` con todos los eventos que existían al tomarla (`events_n`,
`events_seq_hi`, `gv_hi`), guardada comprimida y con su sha256 en `graph_checkpoints` (append-only, misma base).

Reutilización EXACTA (nunca aproximada): una consulta `as_of = t` se sirve desde el punto de control solo si
  · es la misma base (linaje del libro) y no hay NINGÚN evento nuevo (mismo conteo y misma secuencia máxima), y
  · ningún evento tiene valid_from ni valid_to dentro de la ventana (min(t, valid_at), max(t, ahora)] — así el
    pliegue en t daría exactamente lo mismo que en valid_at (incluidas las reglas que miran "ahora").
Si no, se pliega como siempre. Las pruebas (tests/test_checkpoints.py) comparan byte a byte con el pliegue.

APAGADO hasta el umbral: el artefacto `ledger.retention` fija `checkpoint_min_events` (20.000; producción ~5.000) y
`checkpoint_every_events` (10.000). Por debajo del umbral no hay ni una consulta extra en el camino del usuario (un
diccionario en memoria). La migración `object_versions` (historia de propiedades materializada) tampoco se construye
hasta ese umbral (§5.5). Tarea del reloj `graph_checkpoints` (cada hora). Nunca IA. Nunca UPDATE/DELETE.
"""
import hashlib
import logging
import threading
import time
import zlib

from sqlalchemy import (CHAR, BigInteger, Column, DateTime, Identity, Index, Integer, LargeBinary, text)
from sqlalchemy.dialects.postgresql import UUID

from ontology.models import Base

log = logging.getLogger('khipu')

_LOCK = threading.Lock()
STATE = {'enabled': False, 'events_n': None, 'checked_at': None, 'last_build': None, 'hits': 0, 'misses': 0,
         'last_error': None}
_MEM = {'id': None, 'meta': None, 'graph': None}        # último punto de control decodificado (uno)
ADVISORY_KEY = 0x4B48_4350      # 'KHCP'


class GraphCheckpoint(Base):
    __tablename__ = 'graph_checkpoints'
    id = Column(BigInteger, Identity(always=True), primary_key=True)
    lineage_id = Column(UUID(as_uuid=True), nullable=True)       # linaje del libro (otra base = otro linaje)
    gv_hi = Column(BigInteger, nullable=True)                    # versión del grafo al tomarlo (κ)
    events_n = Column(BigInteger, nullable=False)
    events_seq_hi = Column(BigInteger, nullable=True)
    valid_at = Column(DateTime(timezone=True), nullable=False)   # t de la foto
    release_hash = Column(CHAR(64), nullable=True)
    sha256 = Column(CHAR(64), nullable=False)                    # de los bytes canónicos SIN comprimir
    body = Column(LargeBinary, nullable=False)                   # zlib(json canónico de as_of_graph)
    n_nodes = Column(Integer, nullable=True)
    n_links = Column(Integer, nullable=True)
    build_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text('clock_timestamp()'))

    __table_args__ = (Index('ix_graph_checkpoints_created', text('created_at DESC')),)


def params():
    out = {'checkpoint_min_events': 20000, 'checkpoint_every_events': 10000}
    try:
        from core import governance
        p = governance.section('ledger.retention')
        out.update({k: int(p[k]) for k in out if k in p})
    except Exception:  # noqa: BLE001
        pass
    return out


def _event_stats(session):
    r = session.execute(text('SELECT count(*), max(seq) FROM events')).first()
    return int(r[0] or 0), (int(r[1]) if r[1] is not None else None)


def _graph_version(session):
    try:
        return session.execute(text("SELECT v FROM kh_versions WHERE name = 'graph'")).scalar()
    except Exception:  # noqa: BLE001
        return None


def _lineage():
    try:
        from core import ledger
        return ledger.lineage_id()
    except Exception:  # noqa: BLE001
        return None


def refresh_state(session, min_events=None):
    """¿Ya pasó el umbral? (una consulta; lo llama la tarea del reloj, nunca el camino del usuario)."""
    n, _ = _event_stats(session)
    thr = int(min_events if min_events is not None else params()['checkpoint_min_events'])
    with _LOCK:
        STATE.update(enabled=n >= thr, events_n=n, checked_at=time.time(), threshold=thr)
    return STATE['enabled']


def build(session):
    """Toma un punto de control AHORA (as_of_graph sin known_at, la vista de siempre). Devuelve sus metadatos."""
    from core.decisions import canonical

    from ontology.service import as_of_graph
    t0 = time.perf_counter()
    if not session.execute(text('SELECT pg_try_advisory_xact_lock(:k)'), {'k': ADVISORY_KEY}).scalar():
        return {'skipped': 'locked'}
    n, seq_hi = _event_stats(session)
    valid_at = session.execute(text('SELECT clock_timestamp()')).scalar()
    g = as_of_graph(session, valid_at)
    raw = canonical(g)
    try:
        from core import governance
        rh = governance.release()[0]
    except Exception:  # noqa: BLE001
        rh = None
    row = GraphCheckpoint(lineage_id=_lineage(), gv_hi=_graph_version(session), events_n=n, events_seq_hi=seq_hi,
                          valid_at=valid_at, release_hash=rh, sha256=hashlib.sha256(raw).hexdigest(),
                          body=zlib.compress(raw, 6), n_nodes=len(g.get('nodes') or ()),
                          n_links=len(g.get('links') or ()), build_ms=int((time.perf_counter() - t0) * 1000))
    session.add(row)
    session.flush()
    meta = {'id': int(row.id), 'events_n': n, 'events_seq_hi': seq_hi, 'valid_at': valid_at.isoformat(),
            'gv_hi': row.gv_hi, 'sha256': row.sha256, 'bytes': len(row.body), 'n_nodes': row.n_nodes,
            'n_links': row.n_links, 'build_ms': row.build_ms}
    with _LOCK:
        STATE['last_build'] = meta
        _MEM.update(id=None, meta=None, graph=None)
    return meta


def _latest(session):
    lin = _lineage()
    q = 'SELECT id, lineage_id, events_n, events_seq_hi, valid_at, sha256, body FROM graph_checkpoints '
    if lin is not None:
        r = session.execute(text(q + 'WHERE lineage_id = :l ORDER BY id DESC LIMIT 1'), {'l': str(lin)}).first()
    else:
        r = session.execute(text(q + 'ORDER BY id DESC LIMIT 1')).first()
    return r


def lookup(session, as_of_dt, force=False):
    """El grafo en `as_of_dt` desde el último punto de control, o None (→ pliegue de siempre). Exacto o nada.
    Desactivado (sin ninguna consulta) mientras la ontología no pase el umbral, salvo `force` (pruebas)."""
    if not (STATE['enabled'] or force):
        return None
    try:
        r = _latest(session)
        if r is None:
            return None
        n, seq_hi = _event_stats(session)
        if n != int(r.events_n) or seq_hi != (int(r.events_seq_hi) if r.events_seq_hi is not None else None):
            with _LOCK:
                STATE['misses'] += 1
            return None
        now = session.execute(text('SELECT clock_timestamp()')).scalar()
        lo, hi = min(as_of_dt, r.valid_at), max(as_of_dt, now)
        hit = session.execute(text(
            'SELECT 1 FROM events WHERE (valid_from > :lo AND valid_from <= :hi) OR '
            '(valid_to IS NOT NULL AND valid_to > :lo AND valid_to <= :hi) LIMIT 1'), {'lo': lo, 'hi': hi}).first()
        if hit is not None:
            with _LOCK:
                STATE['misses'] += 1
            return None
        with _LOCK:
            cached = _MEM['graph'] if _MEM['id'] == int(r.id) else None
        if cached is None:
            import json
            raw = zlib.decompress(bytes(r.body))
            if hashlib.sha256(raw).hexdigest() != r.sha256:
                log.error('checkpoints: el punto de control %s no coincide con su sha256 (se ignora)', r.id)
                return None
            cached = json.loads(raw.decode('utf-8'))
            with _LOCK:
                _MEM.update(id=int(r.id), graph=cached)
        with _LOCK:
            STATE['hits'] += 1
        out = dict(cached)
        out['as_of'] = as_of_dt.isoformat()
        out['checkpoint'] = {'id': int(r.id), 'valid_at': r.valid_at.isoformat(), 'sha256': r.sha256}
        return out
    except Exception as e:  # noqa: BLE001 — un punto de control roto nunca tumba la consulta: se pliega
        with _LOCK:
            STATE['last_error'] = f'{type(e).__name__}: {str(e)[:160]}'
        return None


def job(force=False):
    """`system:graph_checkpoints` (cada hora): mira el umbral; por encima, toma uno si hay ≥ every eventos nuevos o el
    último tiene más de un día."""
    from ontology.db import ontology_available, session_scope
    if not ontology_available():
        return {'skipped': 'no_database'}
    p = params()
    with session_scope() as s:
        if not refresh_state(s) and not force:
            return {'skipped': 'below_threshold', 'events': STATE['events_n'], 'threshold': p['checkpoint_min_events']}
        r = s.execute(text('SELECT events_n, created_at < clock_timestamp() - interval \'1 day\' AS old '
                           'FROM graph_checkpoints ORDER BY id DESC LIMIT 1')).first()
        if r is not None and not force and not r.old and STATE['events_n'] - int(r.events_n) < p['checkpoint_every_events']:
            return {'skipped': 'recent', 'events': STATE['events_n']}
        return build(s)


def status():
    with _LOCK:
        return {**{k: v for k, v in STATE.items()}, **params()}


def _reset_for_tests():
    with _LOCK:
        STATE.update(enabled=False, events_n=None, checked_at=None, last_build=None, hits=0, misses=0,
                     last_error=None)
        _MEM.update(id=None, meta=None, graph=None)
