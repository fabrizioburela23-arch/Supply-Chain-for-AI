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

_T = {
    'es': {
        'created': 'Entró al grafo',
        'updated': 'Datos actualizados',
        'link_out': 'Nueva relación: {rel} → {other}',
        'link_in': 'Nueva relación: {other} → {rel}',
        'unlink_out': 'Relación terminada: {rel} → {other}',
        'unlink_in': 'Relación terminada: {other} → {rel}',
        'action': 'Acción: {name}',
        'price': 'Precio observado',
        'news': 'Noticia',
        'fields': 'campos',
    },
    'en': {
        'created': 'Entered the graph',
        'updated': 'Data updated',
        'link_out': 'New relation: {rel} → {other}',
        'link_in': 'New relation: {other} → {rel}',
        'unlink_out': 'Relation ended: {rel} → {other}',
        'unlink_in': 'Relation ended: {other} → {rel}',
        'action': 'Action: {name}',
        'price': 'Price observed',
        'news': 'News',
        'fields': 'fields',
    },
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
        entradas.append({
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
        })

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
