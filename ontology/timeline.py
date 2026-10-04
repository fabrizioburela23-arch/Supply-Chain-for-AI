"""ontology/timeline.py — Phase 1 · M5: la línea de tiempo de una entidad.

Es el modelo de LECTURA que cierra el criterio de éxito del spec: abrir una
empresa y ver, en un solo hilo, qué le ha pasado y de dónde sale cada cosa.

Fusiona dos cosas que hasta ahora vivían separadas:
  · los eventos del grafo (entró, cambió, apareció o se cortó una relación,
    alguien registró una tesis…) — el event store de Fase 1;
  · las noticias que informan sobre ella — la ingesta de M4.

Dos decisiones:

1. **Se ordena por cuándo fue cierto EN EL MUNDO** (`valid_from`), no por
   cuándo nos enteramos. Una noticia de marzo ingerida hoy va en marzo. Pero
   `recorded_at` viaja en cada entrada, porque "cuándo lo supimos" es la otra
   mitad del modelo bitemporal y a veces es justo lo interesante (nos
   enteramos tarde).

2. **Cada entrada arrastra su procedencia** cuando la tiene. Si no la tiene,
   se dice con un hueco, no se rellena con algo plausible.

Los títulos se generan en español o inglés (`lang`): el texto que ve el
usuario nunca debe existir en un solo idioma.
"""
from sqlalchemy import or_, select

from ontology.models import Event, LinkRecord, ObjectRecord
from ontology.provenance import source_to_dict
from ontology.service import is_genesis

_T = {
    'es': {
        'created': 'Entró al grafo',
        'updated': 'Datos actualizados',
        'link_out': 'Nueva relación: {rel} {other}',
        'link_in': 'Nueva relación: {other} {rel} esta empresa',
        'unlink_out': 'Relación terminada: {rel} {other}',
        'unlink_in': 'Relación terminada: {other} {rel} esta empresa',
        'action': 'Acción: {name}',
        'price': 'Precio observado',
        'news': 'Noticia',
        'fields': 'campos',
    },
    'en': {
        'created': 'Entered the graph',
        'updated': 'Data updated',
        'link_out': 'New relation: {rel} {other}',
        'link_in': 'New relation: {other} {rel} this company',
        'unlink_out': 'Relation ended: {rel} {other}',
        'unlink_in': 'Relation ended: {other} {rel} this company',
        'action': 'Action: {name}',
        'price': 'Price observed',
        'news': 'News',
        'fields': 'fields',
    },
}


# Verbos legibles para los tipos de relación (el código crudo "supply" no le
# dice nada a un inversionista). Lo desconocido se muestra tal cual.
_REL = {
    'es': {'supply': 'suministra a', 'fab': 'fabrica para', 'license': 'licencia a',
           'cloud': 'da nube a', 'invest': 'invierte en', 'deploy': 'despliega en',
           'partner': 'socio de', 'affects': 'afecta a', 'reports_on': 'informa sobre',
           'fabrica': 'fabrica', 'sanciona': 'sanciona a', 'restringe': 'restringe',
           'depende': 'depende de', 'compite': 'compite con', 'invierte': 'invierte en'},
    'en': {'supply': 'supplies', 'fab': 'fabs for', 'license': 'licenses to',
           'cloud': 'provides cloud to', 'invest': 'invests in', 'deploy': 'deploys at',
           'partner': 'partners with', 'affects': 'affects', 'reports_on': 'reports on',
           'fabrica': 'makes', 'sanciona': 'sanctions', 'restringe': 'restricts',
           'depende': 'depends on', 'compite': 'competes with', 'invierte': 'invests in'},
}


def _iso(dt):
    return dt.isoformat() if dt else None


def _titulo(ev, object_id, etiquetas, t):
    """Título legible. No inventa: si no sabe describir un evento, usa su tipo."""
    tipo = ev.event_type
    p = ev.payload or {}

    if tipo == 'ObjectCreated':
        return t['created'], ''
    if tipo == 'ObjectUpdated':
        campos = list((p.get('properties') or {}).keys())
        return t['updated'], ', '.join(campos[:6])
    if tipo in ('LinkCreated', 'LinkRemoved'):
        rel = p.get('rel_type') or p.get('type') or '?'
        rel = _REL['en' if t is _T['en'] else 'es'].get(rel, rel)
        saliente = ev.object_id == object_id
        otro_id = ev.target_id if saliente else ev.object_id
        otro = etiquetas.get(otro_id, otro_id or '?')
        clave = ('link_out' if saliente else 'link_in') if tipo == 'LinkCreated' \
            else ('unlink_out' if saliente else 'unlink_in')
        return t[clave].format(rel=rel, other=otro), (p.get('properties') or {}).get('headline', '')
    if tipo == 'ActionExecuted':
        nombre = p.get('action') or 'Acción'
        detalle = (p.get('rationale') or p.get('razon') or p.get('decision')
                   or p.get('texto') or '')
        return t['action'].format(name=nombre), str(detalle)[:240]
    if tipo == 'PriceObserved':
        return t['price'], str(p.get('price') or p.get('close') or '')
    return tipo, ''


def entity_timeline(session, object_id, limit=60, lang='es', include_news=True):
    """Todo lo que le ha pasado a una entidad, en un solo hilo ordenado.

    Devuelve las entradas de la más reciente a la más antigua por `at`
    (validez). Cada una lleva su procedencia si existe."""
    t = _T.get(lang if lang in _T else 'es')
    limit = max(1, min(int(limit or 60), 300))

    eventos = session.scalars(
        select(Event).where(or_(Event.object_id == object_id,
                                Event.target_id == object_id))
        .order_by(Event.valid_from.desc()).limit(limit)
    ).all()

    # etiquetas de la otra punta, en UNA consulta (no una por evento)
    otros = {e.target_id if e.object_id == object_id else e.object_id
             for e in eventos}
    otros.discard(None)
    otros.discard(object_id)
    etiquetas = {}
    if otros:
        etiquetas = {o.id: o.label for o in session.scalars(
            select(ObjectRecord).where(ObjectRecord.id.in_(list(otros)))).all()}

    # las fuentes citadas, también en una sola consulta
    src_ids = {e.source_id for e in eventos if e.source_id}
    fuentes = {}
    if src_ids:
        fuentes = {o.id: source_to_dict(o) for o in session.scalars(
            select(ObjectRecord).where(ObjectRecord.id.in_(list(src_ids)))).all()}

    entradas = []
    for ev in eventos:
        titulo, detalle = _titulo(ev, object_id, etiquetas, t)
        fuente = fuentes.get(ev.source_id) if ev.source_id else None
        fila = {
            'kind': 'event',
            'at': _iso(ev.valid_from),
            'recorded_at': _iso(ev.recorded_at),   # cuándo lo SUPIMOS
            'event_type': ev.event_type,
            'title': titulo,
            'detail': detalle,
            'actor': ev.actor,
            'channel': ev.source,                  # por qué tubería entró
            'confidence': ev.confidence,
            'source': fuente,
            'url': (fuente or {}).get('url'),
        }
        # G4b: 2000-01-01 es el centinela de la migración ("desde que se
        # rastrea"), no una fecha real — que la línea de tiempo no lo pinte
        # como si la relación hubiera empezado ese día.
        if is_genesis(ev.valid_from):
            fila['valid_from_known'] = False
        entradas.append(fila)

    if include_news:
        from ontology.ingest_news import news_for_object
        for n in news_for_object(session, object_id, limit=limit):
            entradas.append({
                'kind': 'news',
                'at': n.get('published_at') or n.get('valid_from'),
                'recorded_at': None,
                'event_type': 'NewsItem',
                'title': n.get('title') or t['news'],
                'detail': n.get('publisher') or '',
                'actor': None,
                'channel': 'news',
                'confidence': None,
                'source': {'url': n.get('url'), 'kind': n.get('source_kind'),
                           'publisher': n.get('publisher')},
                'url': n.get('url'),
            })

    # orden por validez, descendente. Las entradas sin fecha van al final en vez
    # de romper la comparación o colarse arriba como si fueran de hoy.
    entradas.sort(key=lambda x: (x['at'] is not None, x['at'] or ''), reverse=True)
    return entradas[:limit]


# ── Feed GLOBAL: lo último que entró al grafo (M6, pendiente cerrado) ───────
#
# La línea de tiempo de arriba es POR ENTIDAD. Este es el hilo de TODO el
# grafo: "¿qué hay de nuevo?". Se ordena por `recorded_at` (cuándo lo SUPIMOS)
# y no por validez, porque la pregunta es qué es nuevo para nosotros — una
# noticia de marzo ingerida hoy ES novedad hoy. `at` (validez) viaja igual.
#
# Se filtra el ruido estructural, que ahogaría lo interesante:
#   · la migración (miles de ObjectCreated con fecha GÉNESIS),
#   · los precios observados,
#   · las Fuentes y los vínculos de procedencia (published_by/evidenced_by/
#     justified_by): son el "de dónde sale", ya viajan DENTRO de cada entrada.
# Una noticia aparece UNA vez, con las empresas sobre las que informa.

_RELS_PROCEDENCIA = {'published_by', 'evidenced_by', 'justified_by'}

_TF = {
    'es': {'news_about': 'Noticia', 'no_entity': 'sin empresa asociada'},
    'en': {'news_about': 'News', 'no_entity': 'no linked company'},
}


def global_feed(session, limit=30, lang='es', since=None):
    """Lo más reciente del grafo entero, más nuevo primero.

    `since` (datetime) devuelve solo lo registrado después — para refrescar
    sin volver a traer todo. Cada entrada: kind, at, recorded_at, event_type,
    subject {id,label,type}, entities [ids], title, detail, actor, channel,
    confidence, source, url."""
    from ontology.ingest_news import NEWS_TYPE, REPORTS_REL

    t = _T.get(lang if lang in _T else 'es')
    tf = _TF.get(lang if lang in _TF else 'es')
    limit = max(1, min(int(limit or 30), 200))

    q = (select(Event)
         .where(~Event.source.like('migration%'),
                Event.event_type != 'PriceObserved')
         # desempate estable: en una misma transacción todo comparte recorded_at
         .order_by(Event.recorded_at.desc(), Event.valid_from.desc())
         # se filtra en Python lo que no se puede en SQL sin joins (tipo del
         # objeto); se pide de más para que el filtro no deje la página corta
         .limit(limit * 4))
    if since is not None:
        q = q.where(Event.recorded_at > since)
    eventos = session.scalars(q).all()

    ids = set()
    for e in eventos:
        ids.add(e.object_id)
        ids.add(e.target_id)
    ids.discard(None)
    objs = {}
    if ids:
        objs = {o.id: o for o in session.scalars(
            select(ObjectRecord).where(ObjectRecord.id.in_(list(ids)))).all()}

    # sobre qué empresas informa cada noticia del lote
    noticias = [e.object_id for e in eventos
                if e.object_id in objs and objs[e.object_id].type == NEWS_TYPE]
    informa = {}
    if noticias:
        for l in session.scalars(select(LinkRecord).where(
                LinkRecord.source_id.in_(noticias),
                LinkRecord.rel_type == REPORTS_REL)).all():
            informa.setdefault(l.source_id, []).append(l.target_id)
        faltan = {x for v in informa.values() for x in v} - set(objs)
        if faltan:
            objs.update({o.id: o for o in session.scalars(
                select(ObjectRecord).where(ObjectRecord.id.in_(list(faltan)))).all()})

    src_ids = {e.source_id for e in eventos if e.source_id}
    fuentes = {}
    if src_ids:
        fuentes = {o.id: source_to_dict(o) for o in session.scalars(
            select(ObjectRecord).where(ObjectRecord.id.in_(list(src_ids)))).all()}

    etiquetas = {k: o.label for k, o in objs.items()}

    def ent(oid):
        o = objs.get(oid)
        return {'id': oid, 'label': o.label if o else oid, 'type': o.type if o else None}

    entradas = []
    for ev in eventos:
        obj = objs.get(ev.object_id)
        tipo_obj = obj.type if obj else None
        rel = (ev.payload or {}).get('rel_type') or (ev.payload or {}).get('type')
        if tipo_obj == 'Source':
            continue
        if ev.event_type in ('LinkCreated', 'LinkRemoved') and rel in _RELS_PROCEDENCIA:
            continue
        fuente = fuentes.get(ev.source_id) if ev.source_id else None

        if tipo_obj == NEWS_TYPE:
            # la noticia se cuenta una sola vez: en su creación
            if ev.event_type != 'ObjectCreated':
                continue
            props = obj.properties or {}
            sobre = informa.get(ev.object_id, [])
            entradas.append({
                'kind': 'news',
                'at': _iso(ev.valid_from), 'recorded_at': _iso(ev.recorded_at),
                'event_type': 'NewsItem',
                'subject': ent(sobre[0]) if sobre else None,
                'entities': sobre,
                'title': props.get('title') or obj.label or tf['news_about'],
                'detail': ', '.join(etiquetas.get(x, x) for x in sobre[:4]) or tf['no_entity'],
                'actor': ev.actor, 'channel': ev.source, 'confidence': ev.confidence,
                'source': fuente or {'url': props.get('url'), 'kind': props.get('source_kind'),
                                     'publisher': props.get('publisher')},
                'url': props.get('url') or (fuente or {}).get('url'),
            })
        else:
            titulo, detalle = _titulo(ev, ev.object_id, etiquetas, t)
            entidades = [x for x in (ev.object_id, ev.target_id) if x]
            fila = {
                'kind': 'event',
                'at': _iso(ev.valid_from), 'recorded_at': _iso(ev.recorded_at),
                'event_type': ev.event_type,
                'subject': ent(ev.object_id) if ev.object_id else None,
                'entities': entidades,
                'title': titulo, 'detail': detalle,
                'actor': ev.actor, 'channel': ev.source, 'confidence': ev.confidence,
                'source': fuente, 'url': (fuente or {}).get('url'),
            }
            if is_genesis(ev.valid_from):
                fila['valid_from_known'] = False
            entradas.append(fila)
        if len(entradas) >= limit:
            break
    return entradas
