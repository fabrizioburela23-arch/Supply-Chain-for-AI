"""ontology/ingest_news.py — Phase 1 · M4: las noticias entran al grafo.

Hasta ahora GDELT era un PASAMANOS: `server.py` lo consultaba, devolvía el JSON
al navegador y ahí moría. La noticia no entraba al event store, la URL se
descartaba, y lo único que sobrevivía era un resumen en texto plano dentro de
una anotación. Es decir: no se podía preguntar "¿qué se publicó sobre TSMC en
marzo?" ni rastrear un hecho hasta el artículo que lo respalda.

Aquí convergen los tres milestones anteriores:
  · M3 (`core/providers/news`) trae el artículo normalizado,
  · M1 (`ontology/provenance`) lo registra como `Source` citable,
  · M2 (`core/entities`) decide a qué entidad se pega —con umbral de ESCRITURA.

Tres decisiones de diseño:

1. **`valid_from` = fecha de PUBLICACIÓN, no de ingesta.** Es la razón de ser
   del modelo bitemporal: la noticia fue cierta en el mundo cuando se publicó,
   aunque la hayamos leído hoy. Así `GET /graph?as_of=<fecha>` devuelve lo que
   se sabía entonces, no lo que ingerimos después.

2. **El vínculo con la empresa es por CONSTRUCCIÓN, no por adivinanza.** Se
   pide noticias PARA una entidad concreta, así que `reports_on` es un hecho,
   no una inferencia. Escanear el texto buscando menciones y pegar hechos a
   quien se parezca es justo como se contamina un grafo; eso queda para cuando
   haya extracción con evidencia verificable.

3. **La noticia se ingiere directo; su INTERPRETACIÓN no.** "Este artículo
   existe, lo publicó X y habla de Y" es una observación con fuente
   comprobable. "Esto significa que la empresa va a caer" es una afirmación, y
   ésas siguen pasando por la cola de aprobación humana (`ProposedAction`).

Idempotente: el id del `NewsItem` se deriva de la URL, así que re-ingerir no
duplica — solo añade el vínculo si es nuevo.
"""
import hashlib

from sqlalchemy import select

from ontology.models import LinkRecord, ObjectRecord
from ontology.provenance import (EVIDENCE_REL, normalize_url, register_source,
                                 source_trust)
from ontology.service import _parse_dt, _utcnow, apply_event

NEWS_TYPE = 'NewsItem'
REPORTS_REL = 'reports_on'
PUBLISHED_REL = 'published_by'


def news_id_for(url):
    """Id estable derivado de la URL: el mismo artículo es el mismo objeto,
    aunque llegue por dos búsquedas distintas."""
    norm = normalize_url(url)
    if not norm:
        return None
    return 'news_' + hashlib.sha1(norm.encode('utf-8')).hexdigest()[:12]


def _link_exists(session, src, tgt, rel):
    return session.scalars(
        select(LinkRecord).where(
            LinkRecord.source_id == src, LinkRecord.target_id == tgt,
            LinkRecord.rel_type == rel, LinkRecord.valid_to.is_(None),
        ).limit(1)).first() is not None


def ingest_item(session, item, entity_id=None, actor='ingesta_noticias'):
    """Ingiere UN artículo normalizado (esquema de core/providers/news).

    Devuelve {'news_id', 'source_id', 'created', 'linked'} o None si el
    artículo no es utilizable. Nunca lanza por un artículo malo: en un lote,
    uno roto no debe tumbar a los demás."""
    url = (item or {}).get('url')
    nid = news_id_for(url)
    if not nid:
        return None   # sin URL no hay procedencia posible → no entra al grafo

    titulo = (item.get('title') or '').strip()
    publicador = (item.get('publisher') or '').strip()
    publicado = (item.get('published_at') or '').strip()
    kind = item.get('source_kind') or None

    # 1) la fuente (M1): deduplicada por URL, con su confiabilidad
    source_id = register_source(
        session, url, kind=kind, title=titulo, publisher=publicador,
        published_at=publicado, extractor=item.get('provider') or 'news',
        actor=actor)

    # 2) cuándo fue cierto EN EL MUNDO — publicación, no ingesta
    valid_from = _parse_dt(publicado) if publicado else None
    if not valid_from:
        valid_from = _utcnow()

    creado = False
    if session.get(ObjectRecord, nid) is None:
        apply_event(session, 'ObjectCreated', {
            'label': (titulo or publicador or url)[:200],
            'type': NEWS_TYPE,
            'properties': {
                'url': normalize_url(url), 'title': titulo,
                'publisher': publicador, 'published_at': publicado,
                'language': item.get('language') or '',
                'provider': item.get('provider') or '',
                'source_kind': kind or '',
            },
        }, valid_from=valid_from, source='news', actor=actor, object_id=nid,
           source_id=source_id,
           # la confianza de la NOTICIA hereda la del tipo de fuente: un filing
           # y un agregador anónimo no valen lo mismo (escala 0-3 → 0-1)
           confidence=(source_trust(kind) / 3.0) if kind else None)
        creado = True

    if source_id and not _link_exists(session, nid, source_id, PUBLISHED_REL):
        apply_event(session, 'LinkCreated', {'rel_type': PUBLISHED_REL, 'properties': {}},
                    valid_from=valid_from, source='news', actor=actor,
                    object_id=nid, target_id=source_id, source_id=source_id)

    enlazado = False
    if entity_id and not _link_exists(session, nid, entity_id, REPORTS_REL):
        apply_event(session, 'LinkCreated', {'rel_type': REPORTS_REL, 'properties': {}},
                    valid_from=valid_from, source='news', actor=actor,
                    object_id=nid, target_id=entity_id, source_id=source_id)
        enlazado = True

    return {'news_id': nid, 'source_id': source_id, 'created': creado, 'linked': enlazado}


def ingest_news_for(session, entity_id, query=None, limit=10,
                    actor='ingesta_noticias', provider_registry=None):
    """Busca noticias de una entidad y las ingiere al grafo.

    `entity_id` debe existir ya en la ontología: no se crean empresas desde una
    noticia (para eso está la Acción IncorporarEmpresa, que pasa por revisión).

    Devuelve un resumen con lo ingerido y lo saltado, sin excepciones: si el
    proveedor falla, se reporta y la app sigue."""
    obj = session.get(ObjectRecord, entity_id)
    if obj is None:
        return {'ok': False, 'error': f'entidad no encontrada: {entity_id}',
                'ingested': 0, 'items': []}

    if provider_registry is None:
        from core.providers.news import news_registry
        provider_registry = news_registry()

    termino = (query or obj.label or entity_id).strip()
    articulos, errores = [], []
    for p in provider_registry.configured():
        try:
            articulos.extend(p.get_latest(termino, limit=limit) or [])
        except Exception as e:  # noqa: BLE001 — un proveedor caído no rompe la ingesta
            errores.append({'provider': getattr(p, 'name', '?'), 'error': str(e)[:140]})

    resultados, saltados = [], 0
    for art in articulos[:limit]:
        try:
            r = ingest_item(session, art, entity_id=entity_id, actor=actor)
        except Exception as e:  # noqa: BLE001
            errores.append({'url': (art or {}).get('url', '')[:120], 'error': str(e)[:140]})
            r = None
        if r:
            resultados.append(r)
        else:
            saltados += 1

    return {
        'ok': True, 'entity_id': entity_id, 'query': termino,
        'fetched': len(articulos),
        'ingested': len(resultados),
        'new': sum(1 for r in resultados if r['created']),
        'skipped_no_url': saltados,
        'errors': errores,
        'items': resultados,
    }


def news_for_object(session, entity_id, limit=20):
    """Noticias que informan sobre una entidad, de la más reciente a la más
    antigua (por fecha de PUBLICACIÓN, que es lo que le importa al usuario)."""
    filas = session.scalars(
        select(LinkRecord).where(
            LinkRecord.target_id == entity_id,
            LinkRecord.rel_type == REPORTS_REL,
            LinkRecord.valid_to.is_(None),
        ).order_by(LinkRecord.valid_from.desc()).limit(min(limit, 200))
    ).all()
    if not filas:
        return []

    ids = [f.source_id for f in filas]
    objs = {o.id: o for o in session.scalars(
        select(ObjectRecord).where(ObjectRecord.id.in_(ids))).all()}

    salida = []
    for f in filas:
        o = objs.get(f.source_id)
        if o is None:
            continue
        p = o.properties or {}
        salida.append({
            'id': o.id, 'title': p.get('title') or o.label, 'url': p.get('url'),
            'publisher': p.get('publisher'), 'published_at': p.get('published_at'),
            'source_kind': p.get('source_kind'), 'language': p.get('language'),
            'valid_from': f.valid_from.isoformat() if f.valid_from else None,
        })
    return salida
