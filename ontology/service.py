"""ontology/service.py — lógica de negocio de la ontología.

apply_event(): valida y aplica UN evento — lo inserta en `events` (inmutable)
y actualiza la vista materializada (`objects`/`links`) para que las lecturas
normales sean rápidas sin tener que reproducir toda la historia.

as_of_graph() / diff_graph(): consultan `events` directamente para
reconstruir qué estaba vigente en una fecha de VALIDEZ dada (time-travel),
igual que ya hace el Grafo Temporal en el cliente (status() vigente/expirado).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, or_, and_

from ontology.models import Event, ObjectRecord, LinkRecord, EventType


class OntologyError(ValueError):
    pass


VALID_EVENT_TYPES = {e.value for e in EventType}


def _utcnow():
    return datetime.now(timezone.utc)


def _parse_dt(v, default=None):
    if v is None:
        return default
    if isinstance(v, datetime):
        return v
    s = str(v)
    try:
        # acepta 'YYYY-MM-DD' o ISO completo
        if len(s) == 10:
            return datetime.fromisoformat(s + 'T00:00:00+00:00')
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except ValueError:
        raise OntologyError(f'fecha inválida: {v!r}')


def apply_event(session, event_type, payload, valid_from, source, actor,
                 object_id=None, target_id=None, valid_to=None):
    """Inserta el evento (inmutable) y actualiza objects/links (materializado).
    Devuelve el Event insertado. Lanza OntologyError si el evento es inválido."""
    if event_type not in VALID_EVENT_TYPES:
        raise OntologyError(f'event_type desconocido: {event_type}')
    valid_from = _parse_dt(valid_from, default=_utcnow())
    valid_to = _parse_dt(valid_to)

    ev = Event(
        id=uuid.uuid4(), event_type=event_type, object_id=object_id, target_id=target_id,
        payload=payload or {}, valid_from=valid_from, valid_to=valid_to,
        source=source, actor=actor,
    )
    session.add(ev)
    session.flush()  # para tener ev.recorded_at si hiciera falta, y detectar errores de constraint ya

    _materialize(session, ev)
    return ev


def _materialize(session, ev):
    """Aplica el efecto del evento sobre las tablas de estado actual."""
    p = ev.payload or {}

    if ev.event_type in (EventType.OBJECT_CREATED.value, EventType.OBJECT_UPDATED.value):
        if not ev.object_id:
            raise OntologyError(f'{ev.event_type} requiere object_id')
        obj = session.get(ObjectRecord, ev.object_id)
        new_props = p.get('properties', {}) or {}
        label = p.get('label') or (obj.label if obj else ev.object_id)
        otype = p.get('type') or (obj.type if obj else 'Company')
        if obj is None:
            obj = ObjectRecord(id=ev.object_id, type=otype, label=label, properties=new_props)
            session.add(obj)
        else:
            merged = dict(obj.properties or {})
            merged.update(new_props)
            obj.properties = merged
            obj.label = label
            obj.type = otype

    elif ev.event_type == EventType.LINK_CREATED.value:
        if not ev.object_id or not ev.target_id:
            raise OntologyError('LinkCreated requiere object_id (source) y target_id')
        rel_type = p.get('rel_type') or p.get('type') or 'supply'
        link = LinkRecord(
            id=uuid.uuid4(), source_id=ev.object_id, target_id=ev.target_id,
            rel_type=rel_type, weight=p.get('weight'), properties=p.get('properties', {}) or {},
            valid_from=ev.valid_from, valid_to=ev.valid_to,
        )
        session.add(link)

    elif ev.event_type == EventType.LINK_REMOVED.value:
        if not ev.object_id or not ev.target_id:
            raise OntologyError('LinkRemoved requiere object_id (source) y target_id')
        rel_type = p.get('rel_type') or p.get('type')
        q = select(LinkRecord).where(
            LinkRecord.source_id == ev.object_id, LinkRecord.target_id == ev.target_id,
            LinkRecord.valid_to.is_(None),
        )
        if rel_type:
            q = q.where(LinkRecord.rel_type == rel_type)
        for link in session.scalars(q).all():
            link.valid_to = ev.valid_from

    elif ev.event_type == EventType.PRICE_OBSERVED.value:
        pass  # se consulta vía events; no toca objects/links (evita hinchar la tabla materializada)

    # ActionExecuted (Fase 2): se registra el evento; su efecto de dominio (si
    # crea/edita otro objeto) se modela con eventos ObjectCreated/Updated aparte.


def get_object(session, object_id):
    return session.get(ObjectRecord, object_id)


def list_objects(session, type_=None, q=None, limit=200, offset=0):
    query = select(ObjectRecord)
    if type_:
        query = query.where(ObjectRecord.type == type_)
    if q:
        like = f'%{q.lower()}%'
        query = query.where(func_lower_like(ObjectRecord.label, like))
    query = query.order_by(ObjectRecord.label).offset(offset).limit(min(limit, 1000))
    return session.scalars(query).all()


def func_lower_like(col, pattern):
    from sqlalchemy import func
    return func.lower(col).like(pattern)


def object_links(session, object_id, direction='out'):
    """Vínculos VIGENTES ahora (valid_to IS NULL) para un objeto."""
    if direction == 'in':
        q = select(LinkRecord).where(LinkRecord.target_id == object_id, LinkRecord.valid_to.is_(None))
    elif direction == 'both':
        q = select(LinkRecord).where(
            or_(LinkRecord.source_id == object_id, LinkRecord.target_id == object_id),
            LinkRecord.valid_to.is_(None),
        )
    else:
        q = select(LinkRecord).where(LinkRecord.source_id == object_id, LinkRecord.valid_to.is_(None))
    return session.scalars(q).all()


def object_history(session, object_id):
    """Todos los eventos donde el objeto participó (como object_id o target_id),
    ordenados por valid_from. Es la 'línea de tiempo' del objeto."""
    q = select(Event).where(
        or_(Event.object_id == object_id, Event.target_id == object_id)
    ).order_by(Event.valid_from)
    return session.scalars(q).all()


def _links_active_at(session, as_of_dt):
    """Reconstruye desde EVENTS (no desde la tabla materializada) qué vínculos
    estaban vigentes en `as_of_dt` (tiempo de VALIDEZ). Es el time-travel real:
    un LinkCreated con valid_from<=as_of y (sin LinkRemoved antes de as_of, o
    su propio valid_to>as_of) cuenta como activo en esa fecha."""
    created = session.scalars(
        select(Event).where(
            Event.event_type == EventType.LINK_CREATED.value,
            Event.valid_from <= as_of_dt,
        )
    ).all()
    removed = session.scalars(
        select(Event).where(
            Event.event_type == EventType.LINK_REMOVED.value,
            Event.valid_from <= as_of_dt,
        )
    ).all()
    # remociones por (source,target): lista de (fecha, rel). rel=None actúa de
    # COMODÍN (igual que _materialize, que sin rel_type cierra todos los rel de
    # ese par) — antes un LinkRemoved sin rel cerraba en tablas pero no casaba
    # nada aquí, y el replay divergía de la vista materializada.
    removals = {}
    for ev in removed:
        rel = (ev.payload or {}).get('rel_type') or (ev.payload or {}).get('type')
        removals.setdefault((ev.object_id, ev.target_id), []).append((ev.valid_from, rel))

    active = []
    for ev in created:
        p = ev.payload or {}
        rel = p.get('rel_type') or p.get('type') or 'supply'
        # ¿este evento propio ya expiró (valid_to) antes de as_of?
        if ev.valid_to is not None and ev.valid_to <= as_of_dt:
            continue
        # una remoción solo mata creaciones ANTERIORES a ella: si el vínculo se
        # re-creó después de la remoción, sigue vigente en as_of.
        rms = removals.get((ev.object_id, ev.target_id), [])
        if any(rm_rel in (None, rel) and ev.valid_from <= rm_at <= as_of_dt
               for rm_at, rm_rel in rms):
            continue
        active.append({
            'source': ev.object_id, 'target': ev.target_id, 'rel_type': rel,
            'weight': p.get('weight'), 'properties': p.get('properties', {}),
            'valid_from': ev.valid_from.isoformat() if ev.valid_from else None,
        })
    return active


def as_of_graph(session, as_of_dt=None):
    """Grafo (nodos + aristas) vigente en `as_of_dt` (default: ahora)."""
    as_of_dt = as_of_dt or _utcnow()
    links = _links_active_at(session, as_of_dt)
    node_ids = set()
    for l in links:
        node_ids.add(l['source']); node_ids.add(l['target'])
    objs = session.scalars(select(ObjectRecord).where(ObjectRecord.id.in_(node_ids))).all() if node_ids else []
    nodes = [{'id': o.id, 'type': o.type, 'label': o.label} for o in objs]
    return {'as_of': as_of_dt.isoformat(), 'nodes': nodes, 'links': links,
            'counts': {'nodes': len(nodes), 'links': len(links)}}


def diff_graph(session, from_dt, to_dt):
    """Qué vínculos aparecieron/desaparecieron entre dos fechas de validez."""
    a = {(l['source'], l['target'], l['rel_type']) for l in _links_active_at(session, from_dt)}
    b = {(l['source'], l['target'], l['rel_type']) for l in _links_active_at(session, to_dt)}
    added = b - a
    removed = a - b
    return {
        'from': from_dt.isoformat(), 'to': to_dt.isoformat(),
        'added': [{'source': s, 'target': t, 'rel_type': r} for s, t, r in sorted(added)],
        'removed': [{'source': s, 'target': t, 'rel_type': r} for s, t, r in sorted(removed)],
        'counts': {'added': len(added), 'removed': len(removed)},
    }
