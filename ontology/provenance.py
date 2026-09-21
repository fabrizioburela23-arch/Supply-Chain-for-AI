"""ontology/provenance.py — Phase 1 · M1: procedencia de primera clase.

El problema que resuelve (ver docs/ARCHITECTURE.md §2): hasta ahora
`Event.source` era una etiqueta de CANAL (`'manual'`, `'radar'`, `'gdelt'`),
nunca un documento. No había forma de ir de un hecho del grafo a la evidencia
original. Las únicas URLs reales del sistema (las que cita el Investigador en
`CrearTesis.fuentes`) quedaban enterradas en `Thesis.properties` y ni siquiera
llegaban al evento auditable.

Diseño — tres decisiones:

1. **`Source` es una ENTIDAD del grafo**, no una tabla lateral. El tipo ya
   estaba declarado en `ontology/vocabulary.json` (sin código detrás); aquí se
   le pone el motor. Así hereda gratis la bitemporalidad, la API de objetos y
   el recorrido que los agentes de Fase 2 van a necesitar.

2. **El id se deriva de la URL** (`src_<sha1[:12]>`): dos hechos que citan el
   mismo artículo apuntan al MISMO objeto, sin necesidad de deduplicar después.
   Es estable entre procesos y reinicios.

3. **El puntero vive en el evento** (`Event.source_id`), no en el objeto
   materializado. Como objetos y links se derivan de eventos, la procedencia de
   cualquier hecho vigente es la de los eventos que lo produjeron — y eso se
   puede preguntar *as_of* una fecha, igual que todo lo demás.

La confiabilidad (`trust`) NO se inventa aquí: sale de `source_kinds` del
vocabulario, que ya definía `primary: 3`, `press/trade: 2`,
`rumor/aggregator/corporate/state: 1` y se describía como "base del filtro de
OBJETIVIDAD" sin que nadie lo leyera.
"""
import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import select

from ontology.models import Event, ObjectRecord

# Parámetros de rastreo que no cambian el documento: quitarlos evita crear dos
# Source distintos para el mismo artículo llegado por dos caminos.
_TRACKING_PARAMS = re.compile(
    r'(^|&)(utm_[a-z]+|fbclid|gclid|mc_cid|mc_eid|ref|ref_src)=[^&]*', re.I)

SOURCE_TYPE = 'Source'
EVIDENCE_REL = 'evidenced_by'
DEFAULT_KIND = 'aggregator'   # el más conservador del vocabulario (trust 1)


def _utcnow():
    return datetime.now(timezone.utc)


def normalize_url(url):
    """Normaliza para deduplicar: esquema/host en minúsculas, sin parámetros de
    rastreo, sin fragmento, sin barra final. Devuelve None si no es usable."""
    if not url or not str(url).strip():
        return None
    raw = str(url).strip()
    if not re.match(r'^https?://', raw, re.I):
        raw = 'https://' + raw
    try:
        parts = urlsplit(raw)
    except ValueError:
        return None
    host = (parts.netloc or '').split('@')[-1].split(':')[0]
    # Un host debe parecer un host: con punto (dominio) o localhost. Sin esto,
    # una errata como 'no-es-una-url' se convertiría en https://no-es-una-url y
    # acabaría creando una entidad Source a partir de basura.
    if not host or ('.' not in host and host.lower() != 'localhost'):
        return None
    query = _TRACKING_PARAMS.sub('', parts.query or '').lstrip('&')
    path = (parts.path or '').rstrip('/')
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, query, ''))


def source_id_for(url):
    """Id estable y derivado de la URL — mismo documento ⇒ mismo id, siempre."""
    norm = normalize_url(url)
    if not norm:
        return None
    return 'src_' + hashlib.sha1(norm.encode('utf-8')).hexdigest()[:12]


def publisher_from_url(url):
    """Dominio como publicador de respaldo cuando la fuente no lo declara."""
    norm = normalize_url(url)
    if not norm:
        return ''
    host = urlsplit(norm).netloc
    return host[4:] if host.startswith('www.') else host


def source_kinds():
    """Los tipos de fuente del vocabulario (con su `trust`). Si el vocabulario
    no se puede leer, se degrada a un mínimo razonable en vez de reventar."""
    try:
        from ontology.vocabulary import source_kinds as _vocab_kinds
        kinds = _vocab_kinds()
        if isinstance(kinds, dict) and kinds:
            return kinds
    except Exception:  # noqa: BLE001
        pass
    return {'primary': {'trust': 3}, 'press': {'trust': 2}, 'aggregator': {'trust': 1}}


def source_trust(kind):
    """0-3. Un `kind` desconocido vale 0: preferimos subestimar una fuente
    antes que darle confianza que nadie declaró."""
    entry = source_kinds().get(str(kind or '').strip().lower())
    if not isinstance(entry, dict):
        return 0
    try:
        return int(entry.get('trust') or 0)
    except (TypeError, ValueError):
        return 0


# Pistas de fuente PRIMARIA (filing, comunicado oficial, dominio .gov). Mismo
# criterio que ya usaba el Investigador para puntuar confianza.
_PRIMARY_HINTS = ('sec.gov', '.gov', 'investor.', 'ir.', 'prnewswire', 'businesswire')

# Heurística de ÚLTIMO RECURSO, solo cuando quien registra no declara el tipo.
# Sin esto todo lo que no es .gov caía en 'aggregator' y la señal de confianza
# degeneraba a "primaria o nada": una agencia de cable y un blog anónimo
# acababan con el mismo trust. Listas cortas y revisables a propósito — quien
# llama SIEMPRE puede declarar el `kind` y su decisión manda sobre esto.
_PRESS_DOMAINS = (
    'reuters.com', 'bloomberg.com', 'ft.com', 'wsj.com', 'nytimes.com',
    'apnews.com', 'cnbc.com', 'economist.com', 'elpais.com', 'lemonde.fr',
)
_TRADE_DOMAINS = (
    'digitimes.com', 'trendforce.com', 'semianalysis.com', 'tomshardware.com',
    'anandtech.com', 'eetimes.com', 'spacenews.com',
)
_STATE_DOMAINS = ('xinhuanet.com', 'globaltimes.cn', 'rt.com', 'tass.com', 'cgtn.com')


def guess_kind(url, declared=None):
    """Si quien registra la fuente declara un `kind` válido, manda. Si no, se
    infiere de la URL de forma conservadora: ante la duda, 'aggregator' (el
    trust más bajo del vocabulario). Nunca se sobreestima una fuente."""
    if declared and str(declared).strip().lower() in source_kinds():
        return str(declared).strip().lower()
    norm = (normalize_url(url) or '').lower()
    if not norm:
        return DEFAULT_KIND
    host = urlsplit(norm).netloc
    if any(h in norm for h in _PRIMARY_HINTS):
        return 'primary'
    if any(host == d or host.endswith('.' + d) for d in _STATE_DOMAINS):
        return 'state'
    if any(host == d or host.endswith('.' + d) for d in _TRADE_DOMAINS):
        return 'trade'
    if any(host == d or host.endswith('.' + d) for d in _PRESS_DOMAINS):
        return 'press'
    return DEFAULT_KIND


def register_source(session, url, kind=None, title='', publisher='',
                    published_at='', retrieved_at='', extractor='', raw_ref='',
                    actor='system'):
    """Registra (o reutiliza) la entidad `Source` de una URL. Idempotente: si el
    documento ya existe, NO lo duplica ni lo sobreescribe — solo completa los
    campos que estaban vacíos, para que una segunda cita más rica enriquezca la
    ficha sin borrar lo anterior.

    Devuelve el `source_id`, o None si la URL no es usable (nunca lanza: una
    fuente mal formada no debe tumbar la escritura del hecho que la cita)."""
    from ontology.service import apply_event

    sid = source_id_for(url)
    if not sid:
        return None
    norm = normalize_url(url)
    k = guess_kind(url, kind)

    existing = session.get(ObjectRecord, sid)
    if existing is not None:
        props = existing.properties or {}
        faltantes = {}
        for campo, valor in (('title', title), ('publisher', publisher),
                             ('published_at', published_at), ('extractor', extractor),
                             ('raw_ref', raw_ref)):
            if valor and not props.get(campo):
                faltantes[campo] = valor
        if faltantes:
            apply_event(session, 'ObjectUpdated', {'properties': faltantes},
                        valid_from=_utcnow(), source='provenance', actor=actor,
                        object_id=sid)
        return sid

    apply_event(session, 'ObjectCreated', {
        'label': (title or publisher or publisher_from_url(url) or norm)[:200],
        'type': SOURCE_TYPE,
        'properties': {
            'url': norm,
            'kind': k,
            'trust': source_trust(k),
            'title': title or '',
            'publisher': publisher or publisher_from_url(url),
            'published_at': published_at or '',
            'retrieved_at': retrieved_at or _utcnow().isoformat(),
            'extractor': extractor or '',
            'raw_ref': raw_ref or '',
        },
    }, valid_from=_utcnow(), source='provenance', actor=actor, object_id=sid)
    return sid


def link_evidence(session, object_id, source_id, actor='system', quote=''):
    """Enlaza un objeto con la fuente que lo evidencia (`evidenced_by`)."""
    from ontology.service import apply_event
    if not object_id or not source_id:
        return False
    apply_event(session, 'LinkCreated',
                {'rel_type': EVIDENCE_REL, 'properties': {'quote': (quote or '')[:500]}},
                valid_from=_utcnow(), source='provenance', actor=actor,
                object_id=object_id, target_id=source_id)
    return True


def source_to_dict(obj):
    props = (obj.properties or {}) if obj is not None else {}
    return {
        'id': obj.id if obj is not None else None,
        'url': props.get('url'), 'kind': props.get('kind'),
        'trust': props.get('trust'), 'title': props.get('title'),
        'publisher': props.get('publisher'),
        'published_at': props.get('published_at'),
        'retrieved_at': props.get('retrieved_at'),
        'extractor': props.get('extractor'),
    }


def provenance_for_object(session, object_id, limit=50):
    """De dónde salió lo que sabemos de este objeto.

    Dos caminos, porque la evidencia puede llegar de dos formas:
      1. eventos sobre el objeto que declaran `source_id` (el camino nuevo);
      2. links `evidenced_by` salientes (útil para objetos como una Tesis, que
         cita varias fuentes a la vez).

    Devuelve las fuentes ordenadas por confiabilidad descendente, cada una con
    los eventos que la citan — para poder contestar "¿cuándo supimos esto?"."""
    from ontology.models import LinkRecord

    eventos = session.scalars(
        select(Event).where(Event.object_id == object_id, Event.source_id.isnot(None))
        .order_by(Event.recorded_at.desc()).limit(limit)
    ).all()

    por_fuente = {}
    for ev in eventos:
        por_fuente.setdefault(ev.source_id, []).append({
            'event_id': str(ev.id), 'event_type': ev.event_type,
            'recorded_at': ev.recorded_at.isoformat() if ev.recorded_at else None,
            'valid_from': ev.valid_from.isoformat() if ev.valid_from else None,
            'confidence': ev.confidence, 'actor': ev.actor,
        })

    enlaces = session.scalars(
        select(LinkRecord).where(
            LinkRecord.source_id == object_id,
            LinkRecord.rel_type == EVIDENCE_REL,
            LinkRecord.valid_to.is_(None),
        ).limit(limit)
    ).all()
    for l in enlaces:
        por_fuente.setdefault(l.target_id, [])

    if not por_fuente:
        return []

    objs = {o.id: o for o in session.scalars(
        select(ObjectRecord).where(ObjectRecord.id.in_(list(por_fuente.keys())))).all()}

    salida = []
    for sid, citas in por_fuente.items():
        obj = objs.get(sid)
        if obj is None:
            continue  # la fuente se retiró: no inventamos una ficha vacía
        salida.append({**source_to_dict(obj), 'cited_by': citas})
    salida.sort(key=lambda s: (-(s.get('trust') or 0), s.get('publisher') or ''))
    return salida
