"""ontology/bitemporal.py — G(t, κ): el grafo vigente en la fecha t TAL COMO SE CONOCÍA en κ (INFRA_OPERATIVA §5.5).

Dos ejes de tiempo:
  · t (validez, `as_of`): cuándo fue cierto en el mundo → `events.valid_from/valid_to` (lo de siempre).
  · κ (conocimiento, `known_at`): qué había REGISTRADO Khipus en ese momento. κ se expresa como
    `graph_version` (el contador que se toma AL CONFIRMAR, core/hotviews/signals.py: su orden ES el orden de
    confirmación) o como un instante ISO, que se traduce a la última versión confirmada hasta ese instante.

Regla de visibilidad de un evento en κ (una sola, la usan ontology/service, matrix/engine y la vista AsOf):
  · su transacción tiene versión (kh_tx_versions)   → visible si version ≤ κ.gv (EXACTO para el grafo económico);
  · su transacción no tiene versión (txid NULL = anterior a la migración del paso 1, o una transacción NO
    económica: noticias, notas…)                    → visible si recorded_at ≤ κ.ts.
  · base sin kh_tx_versions / sin events.txid       → solo recorded_at ≤ κ.ts (modo 'recorded_at', el 🩺 lo dice).

Historia de propiedades (`props_at`): pliega ObjectCreated/ObjectUpdated con valid_from ≤ t y visibles en κ, en
orden de REGISTRO (recorded_at, events.seq) con la MISMA semántica y el MISMO orden que `_materialize` (las propiedades se
fusionan; label/type nuevos pisan). Un objeto "existe" en (t, κ) si tiene al menos un evento así; `retired`
sale de sus propiedades (FusionarEntidad / DarDeBaja).

Escala (medida en el registro de prueba migrado del catálogo, ~4.100 eventos): props_at de todo ≈ decenas de ms.
La tabla `object_versions` (materializar la historia) y los puntos de control solo valen la pena cuando el
registro pase ~20.000 eventos de objetos (MAP V: as_of > 1 s por encima de ~25.000 eventos); producción
tiene ~5.000 → NO se construye todavía (umbral en OBJECT_VERSIONS_THRESHOLD, lo informa `scale_note`).

Sin `known_at` NADA cambia: las funciones de siempre siguen su camino de siempre (paridad 0 diferencias).
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

OBJECT_VERSIONS_THRESHOLD = 20_000      # eventos de objetos a partir de los cuales conviene object_versions
OBJECT_EVENT_TYPES = ('ObjectCreated', 'ObjectUpdated')


class KnownAtError(ValueError):
    """known_at inválido (texto bilingüe en .es / .en)."""

    def __init__(self, es, en):
        super().__init__(es)
        self.es, self.en = es, en


@dataclass(frozen=True)
class Known:
    gv: object            # int | None — versión del grafo κ (None: la base no tiene contador)
    ts: object            # datetime | None — instante para eventos sin versión (None = todos visibles)
    mode: str             # 'graph_version' | 'time' | 'now' | 'recorded_at'
    raw: str = ''
    mark: object = None   # datetime | None — último evento ECONÓMICO SIN versión (huérfano) visible en κ.ts

    def key(self):
        """Clave canónica del CONTENIDO económico: con versión ≥ 1 la versión lo define, MÁS la marca de huérfanos
        cuando κ tiene instante: un evento económico confirmado sin versión (contenedor viejo durante un
        despliegue, guion sin el hook; signals.check_orphans sube la versión DESPUÉS, sin atarle esos eventos)
        hace que dos instantes con la misma versión sean grafos distintos (revisión del paso 23). Sin versión,
        el instante."""
        if self.gv is not None and self.gv >= 1:
            if self.ts is None:
                return ('gv', int(self.gv))
            return ('gv', int(self.gv), self.mark.isoformat() if self.mark is not None else None)
        return ('ts', self.ts.isoformat() if self.ts else None, self.gv)

    def to_dict(self):
        return {'known_at': self.ts.isoformat() if self.ts else None, 'known_graph_version': self.gv,
                'known_mode': self.mode}


def _utcnow():
    return datetime.now(timezone.utc)


def _as_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_known(raw):
    """Texto/número → ('gv', int) | ('ts', datetime) | None (sin κ: 'now', vacío). Lanza KnownAtError."""
    if raw is None or isinstance(raw, Known):
        return raw
    if isinstance(raw, bool):
        raise KnownAtError('known_at inválido', 'invalid known_at')
    if isinstance(raw, int):
        if raw < 0:
            raise KnownAtError('known_at: la versión del grafo no puede ser negativa',
                               'known_at: graph version cannot be negative')
        return ('gv', raw)
    if isinstance(raw, datetime):
        return ('ts', _as_utc(raw))
    s = str(raw).strip()[:64]
    if not s or s.lower() in ('now', 'ahora', 'latest'):
        return None
    body = s[1:] if s[:1] in ('g', 'G') and s[1:].isdigit() else s
    if body.isdigit():
        return ('gv', int(body))
    try:
        if len(s) == 10:
            dt = datetime.fromisoformat(s + 'T00:00:00+00:00')
        else:
            dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
    except ValueError:
        raise KnownAtError(f'known_at inválido: {s!r} (usa AAAA-MM-DD, ISO 8601 o una versión del grafo: 123 / g123)',
                           f'invalid known_at: {s!r} (use YYYY-MM-DD, ISO 8601 or a graph version: 123 / g123)')
    return ('ts', _as_utc(dt))


def capabilities(session):
    """¿La base tiene kh_tx_versions y events.txid? (to_regclass/information_schema: nunca falla)."""
    from sqlalchemy import text
    try:
        row = session.execute(text(
            "SELECT to_regclass('kh_tx_versions') IS NOT NULL, "
            "EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() "
            "AND table_name = 'events' AND column_name = 'txid')")).first()
        return bool(row[0] and row[1])
    except Exception:  # noqa: BLE001
        return False


def _has_seq(session):
    """¿events.seq existe? (columna tardía del paso 1; information_schema: nunca falla)."""
    from sqlalchemy import text
    try:
        return bool(session.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() "
            "AND table_name = 'events' AND column_name = 'seq')")).scalar())
    except Exception:  # noqa: BLE001
        return False


def current_version(session):
    from sqlalchemy import text
    v = session.execute(text("SELECT v FROM kh_versions WHERE name = 'graph'")).scalar()
    return int(v or 0)


def resolve(session, raw):
    """known_at (texto, número, datetime o Known) → Known | None (None = sin κ: el camino de siempre)."""
    p = parse_known(raw)
    if p is None or isinstance(p, Known):
        return p
    kind, val = p
    sraw = str(raw)[:64]
    if not capabilities(session):
        if kind == 'gv':
            raise KnownAtError('known_at por versión del grafo no disponible: esta base no tiene kh_tx_versions '
                               '(usa una fecha ISO)',
                               'known_at by graph version unavailable: this database has no kh_tx_versions '
                               '(use an ISO date)')
        return Known(None, val, 'recorded_at', sraw)
    from sqlalchemy import text
    cur = current_version(session)
    if kind == 'ts':
        gv = session.execute(text(
            "SELECT coalesce(max(version), 0) FROM kh_tx_versions WHERE name = 'graph' AND committed_at <= :ts"),
            {'ts': val}).scalar()
        gv = int(gv or 0)
        return Known(gv, val, 'time', sraw, orphan_mark(session, val) if gv >= 1 else None)
    gv = int(val)
    if gv > cur:
        raise KnownAtError(f'known_at: la versión del grafo {gv} todavía no existe (la actual es {cur})',
                           f'known_at: graph version {gv} does not exist yet (current is {cur})')
    if gv == cur:
        return Known(gv, None, 'graph_version', sraw)    # κ = hoy: todo lo sin versión es visible
    nxt = session.execute(text(
        "SELECT min(committed_at) FROM kh_tx_versions WHERE name = 'graph' AND version > :v"), {'v': gv}).scalar()
    # κ = versión gv representa el intervalo [confirmación de gv, confirmación de gv+1): lo SIN versión registrado
    # en ese intervalo ya se conocía (mismo resultado que un known_at ISO dentro del intervalo).
    ts = (_as_utc(nxt) - timedelta(microseconds=1)) if nxt is not None else None
    return Known(gv, ts, 'graph_version', sraw, orphan_mark(session, ts) if (ts is not None and gv >= 1) else None)


ORPHAN_SCAN = 200


def orphan_mark(session, ts):
    """recorded_at del último evento ESTRUCTURAL y ECONÓMICO con txid pero SIN versión (huérfano) registrado hasta
    `ts` (None si no hay). Los eventos sin txid (anteriores a la migración del paso 1) son todos anteriores a la
    versión 1: no cambian nada entre dos instantes con versión ≥ 1. Mira a lo sumo ORPHAN_SCAN huérfanos (índice
    parcial ix_events_structural); si todos fueran no económicos, devuelve `ts` (clave por instante: nunca un
    grafo equivocado, solo menos aciertos de caché)."""
    from types import SimpleNamespace

    from sqlalchemy import text
    try:
        from core import ledger_ddl
        from core.hotviews import signals
        types = ', '.join(f"'{t}'" for t in ledger_ddl.STRUCTURAL_EVENT_TYPES)
        with session.begin_nested():           # un fallo aquí no envenena la transacción del que llama
            rows = session.execute(text(
                f"SELECT e.recorded_at, e.event_type, e.object_id, e.target_id, e.payload FROM events e "
                f"WHERE e.event_type IN ({types}) AND e.recorded_at <= :ts AND e.txid IS NOT NULL "
                f"AND NOT EXISTS (SELECT 1 FROM kh_tx_versions t WHERE t.txid = e.txid AND t.name = 'graph') "
                f"ORDER BY e.recorded_at DESC LIMIT {ORPHAN_SCAN}"), {'ts': ts}).all()
    except Exception:  # noqa: BLE001 — ante la duda, clave por instante (correcta, menos aciertos)
        return ts
    for rec, et, oid, tid, payload in rows:
        ev = SimpleNamespace(event_type=et, object_id=oid, target_id=tid, payload=payload or {})
        if signals.is_economic(session, ev):
            return _as_utc(rec)
    return ts if len(rows) >= ORPHAN_SCAN else None


def now_known(session):
    """κ = ahora (la versión actual): G(t, ahora) debe ser EXACTAMENTE el as_of de siempre (paridad)."""
    if not capabilities(session):
        return Known(None, None, 'recorded_at', 'now')
    return Known(current_version(session), None, 'now', 'now')


def visible(known):
    """Cláusula SQLAlchemy sobre `events` (FROM events, sin alias): ¿el evento era conocido en κ?"""
    from sqlalchemy import and_, column, literal_column, or_, select, table, true

    from ontology.models import Event
    if known is None:
        return true()
    if known.mode == 'recorded_at' or known.gv is None:
        return Event.recorded_at <= known.ts if known.ts is not None else true()
    tv = table('kh_tx_versions', column('txid'), column('name'), column('version'))
    gvq = (select(tv.c.version).where(tv.c.txid == literal_column('events.txid'), tv.c.name == 'graph')
           .scalar_subquery())
    unversioned = gvq.is_(None) if known.ts is None else and_(gvq.is_(None), Event.recorded_at <= known.ts)
    return or_(gvq <= int(known.gv), unversioned)


# ── historia de propiedades ──────────────────────────────────────────────────────────────────────────────────
def props_at(session, ids=None, t=None, known=None, types=None):
    """{id: {id, type, label, properties, valid_from, updated_from, retired, merged_into}} en (t, κ).

    Pliega ObjectCreated/ObjectUpdated con valid_from ≤ t (t=None: sin límite de validez) visibles en κ, en orden
    de REGISTRO, con la semántica de `_materialize` (t=None, κ=ahora → la fila materializada). `ids` limita a
    esos objetos; `types` filtra por el tipo RESULTANTE. Un objeto sin eventos así no existe en (t, κ)."""
    from sqlalchemy import select

    from ontology.models import Event
    q = select(Event.object_id, Event.event_type, Event.payload, Event.valid_from).where(
        Event.event_type.in_(OBJECT_EVENT_TYPES), Event.object_id.isnot(None))
    if t is not None:
        q = q.where(Event.valid_from <= t)
    if known is not None:
        q = q.where(visible(known))
    if ids is not None:
        ids = [str(i) for i in ids if i]
        if not ids:
            return {}
        q = q.where(Event.object_id.in_(ids))
    # Orden de REGISTRO (recorded_at, luego events.seq = orden de inserción; id solo desempata lo anterior a la
    # migración): EXACTAMENTE el orden en que `_materialize` aplicó los eventos. Así G(ahora, κ=ahora) = la fila
    # materializada, y una corrección registrada después pisa a una afirmación anterior aunque su valid_from sea
    # más viejo (revisión del paso 23: plegar por validez devolvía el valor viejo).
    if _has_seq(session):
        from sqlalchemy import literal_column
        q = q.order_by(Event.recorded_at, literal_column('events.seq').asc().nulls_first(), Event.id)
    else:
        q = q.order_by(Event.recorded_at, Event.id)
    out = {}
    for oid, et, payload, vf in session.execute(q).all():
        p = payload or {}
        new_props = p.get('properties', {}) or {}
        cur = out.get(oid)
        if cur is None:
            cur = out[oid] = {'id': oid, 'type': p.get('type') or 'Company', 'label': p.get('label') or oid,
                              'properties': dict(new_props), 'valid_from': vf, 'updated_from': vf}
            continue
        cur['properties'].update(new_props)
        cur['label'] = p.get('label') or cur['label']
        cur['type'] = p.get('type') or cur['type']
        cur['valid_from'] = min(cur['valid_from'], vf)
        cur['updated_from'] = max(cur['updated_from'], vf)
    for o in out.values():
        pr = o['properties']
        o['retired'] = pr.get('retired') is True
        o['merged_into'] = pr.get('merged_into') if o['retired'] else None
    if types is not None:
        types = set(types)
        out = {k: v for k, v in out.items() if v['type'] in types}
    return out


def object_props_dict(o):
    """props_at → dict serializable (fechas ISO, centinela marcado como en el resto de la API)."""
    from ontology.service import is_genesis
    d = {'id': o['id'], 'type': o['type'], 'label': o['label'], 'properties': o['properties'],
         'valid_from': o['valid_from'].isoformat() if o.get('valid_from') else None,
         'updated_from': o['updated_from'].isoformat() if o.get('updated_from') else None,
         'retired': o['retired']}
    if o.get('merged_into'):
        d['merged_into'] = o['merged_into']
    if is_genesis(o.get('valid_from')):
        d['valid_from_known'] = False
    return d


def economic_ids_at(session, t=None, known=None):
    """Nodos económicos que EXISTEN en (t, κ), en orden de id (DT-M2: existencia de nodos en el tiempo)."""
    from ontology import vocabulary as vocab
    return sorted(props_at(session, t=t, known=known, types=vocab.economic_types()))


def delta_theta(session, from_dt, to_dt, known=None, limit=300):
    """Δθ (L3-07): qué PROPIEDADES de nodos económicos/factores cambiaron entre dos fechas de validez, y qué nodos
    aparecieron. Solo mira los objetos con algún evento de objeto en (from, to] — barato aunque el registro crezca."""
    from sqlalchemy import select

    from ontology import vocabulary as vocab
    from ontology.models import Event
    if from_dt is None or to_dt is None or to_dt <= from_dt:
        return {'changed': [], 'nodes_added': [], 'truncated': False}
    q = select(Event.object_id).where(Event.event_type.in_(OBJECT_EVENT_TYPES), Event.object_id.isnot(None),
                                      Event.valid_from > from_dt, Event.valid_from <= to_dt).distinct()
    if known is not None:
        q = q.where(visible(known))
    touched = [r for (r,) in session.execute(q).all()]
    if not touched:
        return {'changed': [], 'nodes_added': [], 'truncated': False}
    keep = set(vocab.economic_types()) | {'Factor'}
    a = props_at(session, ids=touched, t=from_dt, known=known)
    b = props_at(session, ids=touched, t=to_dt, known=known)
    changed, added = [], []
    for oid in sorted(b):
        nb = b[oid]
        if nb['type'] not in keep:
            continue
        na = a.get(oid)
        if na is None:
            added.append({'id': oid, 'type': nb['type'], 'label': nb['label']})
            continue
        diff = {}
        for k in sorted(set(na['properties']) | set(nb['properties'])):
            va, vb = na['properties'].get(k), nb['properties'].get(k)
            if va != vb:
                diff[k] = {'from': va, 'to': vb}
        for k in ('label', 'type'):
            if na[k] != nb[k]:
                diff[k] = {'from': na[k], 'to': nb[k]}
        if diff:
            changed.append({'id': oid, 'type': nb['type'], 'label': nb['label'], 'changes': diff})
    trunc = len(changed) > limit or len(added) > limit
    return {'changed': changed[:limit], 'nodes_added': added[:limit], 'truncated': trunc}


def scale_note(session):
    """¿Ya conviene object_versions? (umbral documentado; nunca se construye sola)."""
    from sqlalchemy import func, select

    from ontology.models import Event
    try:
        n = int(session.execute(select(func.count()).select_from(Event)
                                .where(Event.event_type.in_(OBJECT_EVENT_TYPES))).scalar() or 0)
    except Exception:  # noqa: BLE001
        return None
    return {'object_events': n, 'object_versions_threshold': OBJECT_VERSIONS_THRESHOLD,
            'object_versions_recommended': n >= OBJECT_VERSIONS_THRESHOLD}
