"""ontology/service.py — lógica de negocio de la ontología.

apply_event(): valida y aplica UN evento — lo inserta en `events` (inmutable)
y actualiza la vista materializada (`objects`/`links`) para que las lecturas
normales sean rápidas sin tener que reproducir toda la historia.

as_of_graph() / diff_graph(): consultan `events` directamente para
reconstruir qué estaba vigente en una fecha de VALIDEZ dada (time-travel),
igual que ya hace el Grafo Temporal en el cliente (status() vigente/expirado).
"""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select, or_, and_, func

from ontology.models import Event, ObjectRecord, LinkRecord, EventType


class OntologyError(ValueError):
    pass


VALID_EVENT_TYPES = {e.value for e in EventType}

# ── fecha CENTINELA de la migración (G4b, misión de reparación 2026-10-04) ──
# scripts/migrate_v0_to_ontology.py puso valid_from = 2000-01-01 a todas las
# empresas y a los ~2.500 links del catálogo sin fecha propia: significa
# "desde que rastreamos este universo", NO una fecha real de inicio. En la UI y
# en el MCP se leía como fecha real (TSMC: todos sus vínculos "desde 2000").
# Este es el ÚNICO lugar que define el centinela; quien serialice un
# valid_from debe marcar `valid_from_known: false` cuando `is_genesis(dt)`.
GENESIS_SENTINEL = '2000-01-01'
VALID_FROM_NOTE_ES = 'desde que se rastrea; fecha de inicio real desconocida'
VALID_FROM_NOTE_EN = 'since tracking began; real start date unknown'


def is_genesis(dt):
    """¿`dt` es la fecha centinela (2000-01-01)? Acepta datetime (con o sin zona),
    date, texto ISO o None. Solo mira el día: el centinela se guardó a medianoche UTC."""
    if dt is None:
        return False
    if isinstance(dt, datetime):
        if dt.tzinfo is not None:          # revisión: una sesión con otra zona horaria lo devolvía como 1999-12-31
            dt = dt.astimezone(timezone.utc)
        return dt.date().isoformat() == GENESIS_SENTINEL
    if isinstance(dt, date):
        return dt.isoformat() == GENESIS_SENTINEL
    return str(dt)[:10] == GENESIS_SENTINEL


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


def _vigilar_vocabulario(kind, value):
    """Deja constancia de un tipo fuera del vocabulario, SIN rechazar la
    escritura.

    apply_event es la puerta principal de escritura y no validaba nada: un
    rel_type inventado (p.ej. 'justified_by', que llevaba meses persistiéndose)
    entraba a la base en silencio y luego el motor de matrices lo descartaba
    también en silencio. Rechazar ahora podría romper escrituras que hoy
    funcionan sobre la base ORIGINAL de producción, así que se observa: queda
    en /api/vocabulary/unknown y en el log, y se decide caso por caso."""
    try:
        from ontology import vocabulary as _v
        if kind == 'object_type':
            conocidos = _v.object_types()
        else:
            conocidos = _v.relation_types_all()
        if value and value not in conocidos:
            _v.note_unknown(kind, value)
    except Exception:  # noqa: BLE001 — vigilar nunca debe tumbar una escritura
        pass


def apply_event(session, event_type, payload, valid_from, source, actor,
                 object_id=None, target_id=None, valid_to=None,
                 source_id=None, confidence=None):
    """Inserta el evento (inmutable) y actualiza objects/links (materializado).
    Devuelve el Event insertado. Lanza OntologyError si el evento es inválido.

    `source` es el CANAL por el que entró el hecho ('manual', 'gdelt'…).
    `source_id` (Phase 1 · M1, opcional) apunta al DOCUMENTO que lo evidencia
    — un objeto type='Source' con url/kind/trust; ver ontology/provenance.py.
    `confidence` (0-1, opcional) es la confianza declarada sobre ESTE evento.

    Ambos son opcionales a propósito: los eventos derivados (migración,
    cálculo, materialización) no citan ningún documento, y obligarlos a
    inventar uno sería peor que no tenerlo."""
    if event_type not in VALID_EVENT_TYPES:
        raise OntologyError(f'event_type desconocido: {event_type}')
    valid_from = _parse_dt(valid_from, default=_utcnow())
    valid_to = _parse_dt(valid_to)

    # `Event.source` es String(60) y varias Acciones admiten `fuente` de hasta
    # 200 caracteres: sin este corte, una fuente larga rompe la escritura del
    # hecho (defecto detectado en la auditoría de Phase 1).
    source = (str(source) if source is not None else '')[:60]

    if confidence is not None:
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            confidence = None

    # G2: un LinkCreated idéntico a una fila VIGENTE (mismo par, rel y peso) que
    # ya lo cubre (empezó antes o igual y el nuevo no trae fin) no abre una
    # segunda fila: el evento se registra (append-only) marcado como `dedup_of`
    # y es un no-op en tablas y en el replay. Un hecho con ventana propia
    # (valid_to) o que empieza ANTES no es duplicado. `allow_duplicate: true`
    # lo desactiva explícitamente.
    if event_type == EventType.LINK_CREATED.value and object_id and target_id and valid_to is None:
        payload = _dedup_link_payload(session, payload or {}, object_id, target_id, valid_from)

    ev = Event(
        id=uuid.uuid4(), event_type=event_type, object_id=object_id, target_id=target_id,
        payload=payload or {}, valid_from=valid_from, valid_to=valid_to,
        source=source, actor=actor, source_id=source_id, confidence=confidence,
        # G5c: hora REAL de la escritura (clock_timestamp), no el inicio de la
        # transacción (now()): el replay ordena creaciones y remociones por
        # registro, y con now() dos eventos de la misma transacción —o una
        # remoción cuya transacción empezó antes de una creación concurrente—
        # quedaban empatados o al revés respecto de las tablas.
        recorded_at=func.clock_timestamp(),
    )
    session.add(ev)
    session.flush()  # para tener ev.recorded_at si hiciera falta, y detectar errores de constraint ya

    _materialize(session, ev)
    return ev


def _same_weight(a, b):
    try:
        if a is None or b is None:
            return a is None and b is None
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return False


def _dedup_link_payload(session, payload, source_id, target_id, valid_from=None):
    props = dict(payload.get('properties') or {})
    if props.get('allow_duplicate'):
        return payload
    rel = payload.get('rel_type') or payload.get('type') or 'supply'
    q = select(LinkRecord).where(
        LinkRecord.source_id == source_id, LinkRecord.target_id == target_id,
        LinkRecord.rel_type == rel, LinkRecord.valid_to.is_(None))
    if valid_from is not None:
        q = q.where(LinkRecord.valid_from <= valid_from)      # el gemelo ya cubre esa fecha
    twins = session.scalars(q.order_by(LinkRecord.valid_from)).all()
    twin = next((t for t in twins if _same_weight(t.weight, payload.get('weight'))), None)
    if twin is not None:
        if not twin.event_id:              # fila heredada: se empareja YA con su evento (G5, revisión)
            cev = _creation_event_for(session, twin)
            if cev is not None:
                twin.event_id = cev.id
        props['dedup_of'] = str(twin.id)
        if twin.event_id:
            props['dedup_event_id'] = str(twin.event_id)
        return dict(payload, properties=props)
    return payload


def _creation_event_for(session, link):
    """Evento LinkCreated que creó la fila (event_id o emparejamiento para filas
    anteriores a G2: mismo par/rel/valid_from/peso, el más antiguo no asignado)."""
    if link.event_id:
        return session.get(Event, link.event_id)
    cands = session.scalars(select(Event).where(
        Event.event_type == EventType.LINK_CREATED.value, Event.object_id == link.source_id,
        Event.target_id == link.target_id, Event.valid_from == link.valid_from).order_by(Event.recorded_at)).all()
    taken = {str(r.event_id) for r in session.scalars(select(LinkRecord).where(
        LinkRecord.source_id == link.source_id, LinkRecord.target_id == link.target_id,
        LinkRecord.event_id.isnot(None))).all()}
    # G5 (revisión adversarial): entre los candidatos, preferir el evento cuyas
    # propiedades son las de ESTA fila (dos filas con el mismo peso pero distinto
    # texto — p. ej. una "no verificado" — no son intercambiables).
    lp = dict(link.properties or {})
    best, best_score = None, -1
    for ev in cands:
        p = ev.payload or {}
        rel = p.get('rel_type') or p.get('type') or 'supply'
        if rel != link.rel_type or not _same_weight(p.get('weight'), link.weight):
            continue
        ep = p.get('properties') or {}
        if ep.get('dedup_of') or str(ev.id) in taken:
            continue
        if ev.valid_to != link.valid_to and link.valid_to is None and ev.valid_to is not None:
            continue
        score = 2 if ep == lp else (1 if ep.get('rel_label') == lp.get('rel_label') else 0)
        if score > best_score:
            best, best_score = ev, score
            if score == 2:
                break
    return best


def _wkey(w):
    try:
        return None if w is None else round(float(w), 9)
    except (TypeError, ValueError):
        return None


def _pair_history(session, src, tgt):
    """(creaciones, retracciones dirigidas {creación: evento}, remociones no dirigidas [(fecha, rel, registrada)])."""
    evs = session.scalars(select(Event).where(
        Event.object_id == src, Event.target_id == tgt,
        Event.event_type.in_([EventType.LINK_CREATED.value, EventType.LINK_REMOVED.value]))
        .order_by(Event.recorded_at, Event.id)).all()
    created, dirs, rms = [], {}, []
    for e in evs:
        p = e.payload or {}
        if e.event_type == EventType.LINK_CREATED.value:
            created.append(e)
            continue
        rid = (p.get('properties') or {}).get('retracts_event_id')
        if rid:
            dirs[_uuid_str(rid)] = e
        else:
            rms.append((e.valid_from, p.get('rel_type') or p.get('type'), e.recorded_at))
    return created, dirs, rms


def _killed(e, rel, rms, at):
    """¿Una remoción NO dirigida (anterior en validez y en registro) mata esta creación en `at`?"""
    return any(rm_rel in (None, rel) and e.valid_from <= rm_at <= at
               and (e.recorded_at is None or rm_rec is None or e.recorded_at <= rm_rec)
               for rm_at, rm_rel, rm_rec in rms)


def _promotion_choice(session, src, tgt, rel, wk, now=None):
    """G5 — regla ÚNICA (tablas y replay) para un LinkCreated deduplicado:
    asciende el más antiguo cuya creación gemela fue retractada por un DESHACER
    (LinkRemoved dirigido con `promote_dedups: true`, solo lo emite rollback_run)
    y que no está él mismo retractado ni muerto por una remoción, SOLO si no
    queda ninguna creación no deduplicada idéntica (par, rel, peso) viva AHORA.
    Una CORRECCIÓN ("esta fila es falsa": dirección, peso, sobrante, fusión) no
    asciende nada: el mismo hecho repetido es igual de falso. Devuelve el evento o None."""
    now = now or _utcnow()
    created, dirs, rms = _pair_history(session, src, tgt)

    def same(e):
        p = e.payload or {}
        return (p.get('rel_type') or p.get('type') or 'supply') == rel and _wkey(p.get('weight')) == wk

    def alive(e):
        return (str(e.id) not in dirs and not (e.valid_to is not None and e.valid_to <= now)
                and not _killed(e, rel, rms, now))
    pool = [e for e in created if same(e)]
    if any(alive(e) for e in pool if not ((e.payload or {}).get('properties') or {}).get('dedup_of')):
        return None
    for d in pool:
        dp = (d.payload or {}).get('properties') or {}
        if not dp.get('dedup_of'):
            continue
        tid = dp.get('dedup_event_id')
        rm = dirs.get(_uuid_str(tid)) if tid else None
        if rm is None or not ((rm.payload or {}).get('properties') or {}).get('promote_dedups') or not alive(d):
            continue
        twin = next((e for e in created if str(e.id) == _uuid_str(tid)), None)
        if twin is not None and (twin.source or '') == (d.source or ''):
            continue                 # mismo canal que su gemela: no es un hecho independiente
        return d
    return None


def _promote_dedup(session, src, tgt, rel, weight):
    """Tablas: tras una retracción dirigida, aplica _promotion_choice."""
    session.flush()
    d = _promotion_choice(session, src, tgt, rel, _wkey(weight))
    if d is None:
        return
    if session.scalars(select(LinkRecord).where(LinkRecord.event_id == d.id)).first() is not None:
        return
    p = d.payload or {}
    props = {k: v for k, v in (p.get('properties') or {}).items() if k not in ('dedup_of', 'dedup_event_id')}
    session.add(LinkRecord(id=uuid.uuid4(), source_id=d.object_id, target_id=d.target_id,
                           rel_type=rel, weight=p.get('weight'),
                           properties=props, valid_from=d.valid_from, valid_to=d.valid_to, event_id=d.id))


def _replay_promotions(session):
    """Replay: el conjunto de eventos deduplicados que ascienden (misma regla)."""
    dedups = session.scalars(select(Event).where(
        Event.event_type == EventType.LINK_CREATED.value,
        Event.payload['properties']['dedup_of'].astext.isnot(None))).all()
    keys = set()
    for d in dedups:
        p = d.payload or {}
        keys.add((d.object_id, d.target_id, p.get('rel_type') or p.get('type') or 'supply', _wkey(p.get('weight'))))
    out = set()
    for src, tgt, rel, wk in keys:
        d = _promotion_choice(session, src, tgt, rel, wk)
        if d is not None:
            out.add(d.id)
    return out


def _uuid_str(x):
    try:
        return str(uuid.UUID(str(x)))
    except (TypeError, ValueError):
        return str(x)


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
        _vigilar_vocabulario('object_type', otype)
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
        _vigilar_vocabulario('rel_type', rel_type)
        if (p.get('properties') or {}).get('dedup_of'):
            return                      # G2: duplicado exacto → no abre fila (el evento queda)
        link = LinkRecord(
            id=uuid.uuid4(), source_id=ev.object_id, target_id=ev.target_id,
            rel_type=rel_type, weight=p.get('weight'), properties=p.get('properties', {}) or {},
            valid_from=ev.valid_from, valid_to=ev.valid_to, event_id=ev.id,
        )
        session.add(link)

    elif ev.event_type == EventType.LINK_REMOVED.value:
        if not ev.object_id or not ev.target_id:
            raise OntologyError('LinkRemoved requiere object_id (source) y target_id')
        rid = (p.get('properties') or {}).get('retracts_event_id')
        if rid:
            # G2: retracción DIRIGIDA — cierra SOLO la fila creada por ese evento
            try:
                rid_u = uuid.UUID(str(rid))
            except ValueError:
                raise OntologyError(f'retracts_event_id inválido: {rid}')
            rows = session.scalars(select(LinkRecord).where(LinkRecord.event_id == rid_u,
                                                            LinkRecord.valid_to.is_(None))).all()
            if not rows:
                cev = session.get(Event, rid_u)
                if cev is not None and cev.event_type == EventType.LINK_CREATED.value:
                    cp = cev.payload or {}
                    crel = cp.get('rel_type') or cp.get('type') or 'supply'
                    cand = session.scalars(select(LinkRecord).where(
                        LinkRecord.source_id == cev.object_id, LinkRecord.target_id == cev.target_id,
                        LinkRecord.rel_type == crel, LinkRecord.valid_from == cev.valid_from,
                        LinkRecord.valid_to.is_(None), LinkRecord.event_id.is_(None))
                        .order_by(LinkRecord.valid_from)).all()
                    rows = [r for r in cand if _same_weight(r.weight, cp.get('weight'))][:1]
                    for r in rows:
                        r.event_id = cev.id
            for r in rows:
                r.valid_to = ev.valid_from
            if (p.get('properties') or {}).get('promote_dedups'):     # solo un DESHACER asciende
                for r in rows:
                    _promote_dedup(session, r.source_id, r.target_id, r.rel_type, r.weight)
            return
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
    directed = {}            # G2: retracciones dirigidas → {event_id de la creación: fecha}
    for ev in removed:
        rid = ((ev.payload or {}).get('properties') or {}).get('retracts_event_id')
        if rid:
            directed[_uuid_str(rid)] = ev.valid_from     # G5: UUID normalizado como en _materialize
            continue
        rel = (ev.payload or {}).get('rel_type') or (ev.payload or {}).get('type')
        removals.setdefault((ev.object_id, ev.target_id), []).append((ev.valid_from, rel, ev.recorded_at))
    # G5: deduplicadas que "ascienden" (misma regla que las tablas: _promotion_choice)
    promoted = _replay_promotions(session)

    active = []
    for ev in created:
        p = ev.payload or {}
        rel = p.get('rel_type') or p.get('type') or 'supply'
        if (p.get('properties') or {}).get('dedup_of') and ev.id not in promoted:
            continue                                   # G2: creación duplicada = no-op
        if str(ev.id) in directed and directed[str(ev.id)] <= as_of_dt:
            continue                                   # G2: retractada exactamente esta creación
        # ¿este evento propio ya expiró (valid_to) antes de as_of?
        if ev.valid_to is not None and ev.valid_to <= as_of_dt:
            continue
        # una remoción solo mata creaciones ANTERIORES a ella: si el vínculo se
        # re-creó después de la remoción, sigue vigente en as_of. G5: "anterior"
        # también en tiempo de REGISTRO — una re-creación registrada DESPUÉS de
        # la remoción (fusión, reconciliación, deshacer) no muere aunque su
        # valid_from sea viejo; igual que en las tablas.
        if _killed(ev, rel, removals.get((ev.object_id, ev.target_id), []), as_of_dt):
            continue
        row = {
            'source': ev.object_id, 'target': ev.target_id, 'rel_type': rel,
            'weight': p.get('weight'), 'properties': p.get('properties', {}),
            'valid_from': ev.valid_from.isoformat() if ev.valid_from else None,
            'event_id': str(ev.id),
        }
        if is_genesis(ev.valid_from):
            row['valid_from_known'] = False
        active.append(row)
    # G6b: ConfirmarVinculo cambia el estado de la fila materializada; el replay
    # lo aplica desde su ActionExecuted (creation_event_id) para que as_of y el
    # presente coincidan (p. ej. el descuento por "no verificado" en las matrices).
    if active:
        conf = {}
        for a in session.scalars(select(Event).where(
                Event.event_type == 'ActionExecuted',
                Event.payload['action'].astext == 'ConfirmarVinculo')).all():
            cid = (a.payload or {}).get('creation_event_id')
            if cid:
                conf[_uuid_str(cid)] = a.actor
        if conf:
            for row in active:
                who = conf.get(row['event_id'])
                if who is not None:
                    row['properties'] = dict(row['properties'] or {}, status='confirmed', confirmed_by=who)
    return active


def as_of_graph(session, as_of_dt=None):
    """Grafo (nodos + aristas) vigente en `as_of_dt` (default: ahora).

    Acepta datetime o texto ('2026-04-01'). Antes asumía datetime y reventaba
    con un string —la ruta HTTP lo esquivaba porque parsea antes de llamar—,
    así que el fallo solo aparecía al usar la función directamente."""
    as_of_dt = _parse_dt(as_of_dt) or _utcnow()
    links = _links_active_at(session, as_of_dt)
    node_ids = set()
    for l in links:
        node_ids.add(l['source']); node_ids.add(l['target'])
    objs = session.scalars(select(ObjectRecord).where(ObjectRecord.id.in_(node_ids))).all() if node_ids else []
    nodes = [{'id': o.id, 'type': o.type, 'label': o.label} for o in objs]
    return {'as_of': as_of_dt.isoformat(), 'nodes': nodes, 'links': links,
            'counts': {'nodes': len(nodes), 'links': len(links)}}


def diff_graph(session, from_dt, to_dt):
    """Qué vínculos aparecieron/desaparecieron entre dos fechas de validez.

    Acepta datetime o texto, igual que as_of_graph: ambas tenían el mismo fallo
    latente (asumían datetime y la ruta HTTP lo tapaba parseando antes)."""
    from_dt = _parse_dt(from_dt) or _utcnow()
    to_dt = _parse_dt(to_dt) or _utcnow()
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
