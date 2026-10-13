"""core/gates/focus.py — EL mapeo a grafo foco de cada puerta (docs/INFRA_OPERATIVA.md §3.2; paso 10).

Una función PURA por foco (`link_triples`, `object_triples`, `factor_triples`, `action_triples`,
`decision_triples`) que recibe diccionarios y devuelve una lista de tripletas Python `(s, p, o)`. En vivo las
consume el evaluador compilado (core/gates/engine, sin rdflib); en pruebas y en la auditoría, `to_rdflib()` arma
el grafo para pySHACL. Como el MISMO mapeo alimenta a los dos, la prueba de conformidad cubre también el mapeo.
Las funciones `gather_*` leen de la sesión lo que el foco necesita (estado RESULTANTE dentro de la transacción).

Reglas de literales (las trampas medidas en MAP G):
  · enumerados (rel, tipo, canal, modo) como literales SIMPLES (str), nunca ^^xsd:string;
  · números como xsd:decimal a partir de Decimal(str(x)); un valor no numérico queda como texto (la regla lo ve);
  · fechas como xsd:dateTime en UTC; booleanos como xsd:boolean;
  · IRIs de entidad codificadas con porcentaje (khd:obj/<id>).
Los límites de política (`policy.gates.limits`, `policy.auto_apply`) entran como LITERALES del foco: ningún
número de política se escribe en el TTL.
"""
import math
from datetime import date, datetime, timezone
from decimal import Decimal
from urllib.parse import quote, unquote

KH = 'https://khipus.ai/ont#'
KHD = 'https://khipus.ai/id/'
KHS = 'https://khipus.ai/shapes#'
KHR = 'https://khipus.ai/rule#'
SH = 'http://www.w3.org/ns/shacl#'
XSD = 'http://www.w3.org/2001/XMLSchema#'
RDF_TYPE = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'
PREFIXES = {'kh': KH, 'khd': KHD, 'khs': KHS, 'khr': KHR, 'sh': SH, 'xsd': XSD,
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'}
NUMERIC_OBJECT_PROPS = {'margin': 'margin', 'severity': 'severity', 'severity_crisis': 'severityCrisis'}


class IRI(str):
    """Un término IRI (el resto de los objetos son literales: str, bool, Decimal, datetime)."""
    __slots__ = ()


def kh(local):
    return IRI(KH + local)


def node(kind, ident):
    return IRI(f'{KHD}{kind}/{quote(str(ident), safe="")}')


def compact(iri):
    s = str(iri)
    for p, ns in PREFIXES.items():
        if s.startswith(ns):
            return f'{p}:{s[len(ns):]}'
    return s


def expand(c):
    if isinstance(c, str) and ':' in c and not c.startswith('http'):
        p, local = c.split(':', 1)
        if p in PREFIXES:
            return PREFIXES[p] + local
    return c


def ident_of(iri):
    """khd:obj/TSMC → 'TSMC' (para mostrar)."""
    s = str(iri)
    if s.startswith(KHD):
        return unquote(s.rsplit('/', 1)[-1])
    return compact(s)


TYPE = IRI(RDF_TYPE)


def num(x):
    """Número → Decimal (xsd:decimal); bool, NaN/inf, texto u otra cosa → texto (la forma lo marca)."""
    if x is None:
        return None
    if isinstance(x, bool):
        return 'true' if x else 'false'
    if isinstance(x, Decimal):
        return x if x.is_finite() else str(x)
    if isinstance(x, (int, float)):
        if isinstance(x, float) and not math.isfinite(x):
            return str(x)
        return Decimal(str(x))
    if isinstance(x, str):
        return x
    return str(x)


def dt(x):
    if x is None:
        return None
    if isinstance(x, datetime):
        return (x if x.tzinfo else x.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    if isinstance(x, date):
        return datetime(x.year, x.month, x.day, tzinfo=timezone.utc)
    try:
        s = str(x)
        v = datetime.fromisoformat(s.replace('Z', '+00:00') if len(s) > 10 else s + 'T00:00:00+00:00')
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


class _T(list):
    def add(self, s, p, o):
        if o is not None:
            self.append((s, p, o))


# ── focos puros ──────────────────────────────────────────────────────────────
def link_triples(link, endpoints=None, inverses=(), sources=None, limits=None, flow_rels=()):
    """link: {id, source, target, rel, weight, confidence, valid_from, valid_to, rel_label, evidenced_by[], dated}
    endpoints: {id: {type, live}} · inverses: [{id, source, target, rel, live}] · sources: {id: trust}
    limits: policy.gates.limits · flow_rels: relaciones de FLUJO del vocabulario. → (tripletas, foco)."""
    t = _T()
    L = node('link', link.get('id') or f"{link.get('source')}>{link.get('target')}:{link.get('rel')}")
    t.add(L, TYPE, kh('Link'))
    for side in ('source', 'target'):
        if link.get(side) is not None:
            t.add(L, kh(side), node('obj', link[side]))
    rel = link.get('rel')
    if rel is not None:
        t.add(L, kh('relType'), str(rel))
        if str(rel) in set(flow_rels or ()):
            t.add(L, kh('flow'), True)
    t.add(L, kh('weight'), num(link.get('weight')))
    t.add(L, kh('confidence'), num(link.get('confidence')))
    t.add(L, kh('validFrom'), dt(link.get('valid_from')))
    t.add(L, kh('validTo'), dt(link.get('valid_to')))
    if link.get('rel_label'):
        t.add(L, kh('relLabel'), str(link['rel_label'])[:300])
    if link.get('dated'):
        t.add(L, kh('datedFact'), True)
    for sid in link.get('evidenced_by') or ():
        S = node('obj', sid)
        t.add(L, kh('evidencedBy'), S)
        tr = (sources or {}).get(sid)
        if tr is not None:
            t.add(S, kh('trust'), num(tr))
    lim = limits or {}
    t.add(L, kh('maxWeight'), num(lim.get('max_weight')))
    t.add(L, kh('highConfMin'), num(lim.get('high_conf_min')))
    t.add(L, kh('minTrust'), num(lim.get('min_trust')))
    for oid, e in (endpoints or {}).items():
        E = node('obj', oid)
        if e.get('type'):
            t.add(E, kh('objType'), str(e['type']))
        if e.get('live'):
            t.add(E, TYPE, kh('LiveObject'))
    for inv in inverses or ():
        R = node('linkref', inv.get('id'))
        t.add(R, TYPE, kh('LinkRef'))
        t.add(R, kh('source'), node('obj', inv.get('source')))
        t.add(R, kh('target'), node('obj', inv.get('target')))
        t.add(R, kh('relType'), str(inv.get('rel')) if inv.get('rel') is not None else None)
        if inv.get('live'):
            t.add(R, kh('live'), True)
    return list(t), L


def object_triples(obj):
    """obj: {id, type, prev_type, props} → (tripletas, foco)."""
    t = _T()
    O = node('obj', obj['id'])
    t.add(O, TYPE, kh('Object'))
    if obj.get('type') is not None:
        t.add(O, kh('type'), str(obj['type']))
    if obj.get('prev_type') is not None:
        t.add(O, kh('prevType'), str(obj['prev_type']))
    props = obj.get('props') or {}
    for key, local in NUMERIC_OBJECT_PROPS.items():
        if key in props and props[key] is not None:
            t.add(O, kh(local), num(props[key]))
    return list(t), O


def factor_triples(f, limits=None):
    """f: {id, props, prev_props (None si es nuevo), touches, members:[{id, target, coef, live}]} → (tripletas, foco)."""
    t = _T()
    F = node('obj', f['id'])
    t.add(F, TYPE, kh('Factor'))
    p = f.get('props') or {}
    t.add(F, kh('severity'), num(p.get('severity')))
    t.add(F, kh('severityCrisis'), num(p.get('severity_crisis')))
    t.add(F, kh('active'), bool(p.get('activo')))
    t.add(F, kh('retired'), bool(p.get('expired') or p.get('retired')))
    prev = f.get('prev_props')
    if prev is not None:
        t.add(F, kh('prevSeverity'), num(prev.get('severity')))
        t.add(F, kh('prevActive'), bool(prev.get('activo')))
    if f.get('touches'):
        t.add(F, kh('touchesSeverity'), True)
    lim = limits or {}
    t.add(F, kh('severityScale'), num(lim.get('severity_scale')))
    t.add(F, kh('maxCoef'), num(lim.get('max_member_coef')))
    for m in f.get('members') or ():
        M = node('aff', m.get('id'))
        t.add(F, kh('membership'), M)
        t.add(M, TYPE, kh('Membership'))
        t.add(M, kh('member'), node('obj', m.get('target')))
        t.add(M, kh('coef'), num(m.get('coef')))
        if m.get('live'):
            t.add(M, kh('live'), True)
    return list(t), F


def action_triples(a):
    """a: {id, action_type, principal:{id, kind, auth}, auto_apply, confidence, nivel, reason, unknown_fields[],
    safe_auto[], auto_min_conf} → (tripletas, foco)."""
    t = _T()
    A = node('action', a.get('id') or 'req')
    t.add(A, TYPE, kh('ActionRequest'))
    if a.get('action_type') is not None:
        t.add(A, kh('actionType'), str(a['action_type']))
    pr = a.get('principal') or {}
    for k, local in (('kind', 'principalKind'), ('auth', 'principalAuth'), ('id', 'principalId')):
        if pr.get(k) is not None:
            t.add(A, kh(local), str(pr[k]))
    if a.get('auto_apply'):
        t.add(A, kh('autoApply'), True)
    t.add(A, kh('confidence'), num(a.get('confidence')))
    t.add(A, kh('nivel'), num(a.get('nivel')))
    if a.get('reason') is not None:
        t.add(A, kh('reason'), str(a['reason']))
    for fld in a.get('unknown_fields') or ():
        t.add(A, kh('unknownField'), str(fld))
    for st in a.get('safe_auto') or ():
        t.add(A, kh('safeAutoType'), str(st))
    t.add(A, kh('autoMinConfidence'), num(a.get('auto_min_conf')))
    return list(t), A


def decision_triples(d):
    """d: {id, kind, status, principal_kind, release_hash, verdict, quotes:[{ticker, as_of, src}]} → (tripletas, foco)."""
    t = _T()
    D = node('decision', d.get('id') or 'd')
    t.add(D, TYPE, kh('Decision'))
    for k, local in (('kind', 'kind'), ('status', 'status'), ('principal_kind', 'principalKind'),
                     ('release_hash', 'releaseHash'), ('verdict', 'verdict')):
        if d.get(k) is not None:
            t.add(D, kh(local), str(d[k]))
    for n, q in enumerate(d.get('quotes') or ()):
        Q = node('quote', f"{d.get('id') or 'd'}-{n}")
        t.add(D, kh('quote'), Q)
        t.add(Q, kh('ticker'), str(q.get('ticker') or '?'))
        if q.get('as_of'):
            t.add(Q, kh('asOf'), str(q['as_of']))
        if q.get('src'):
            t.add(Q, kh('src'), str(q['src']))
    return list(t), D


# ── para pySHACL (pruebas, auditoría): importado de forma perezosa ───────────
def to_rdflib(triples):
    from rdflib import Graph, Literal, URIRef
    from rdflib.namespace import XSD as _XSD
    g = Graph()
    for s, p, o in triples:
        if isinstance(o, IRI):
            obj = URIRef(o)
        elif isinstance(o, bool):
            obj = Literal(o)
        elif isinstance(o, Decimal):
            obj = Literal(o, datatype=_XSD.decimal)
        elif isinstance(o, datetime):
            obj = Literal(o)
        else:
            obj = Literal(str(o))                  # literal SIMPLE (nunca ^^xsd:string: MAP G)
        g.add((URIRef(s), URIRef(p), obj))
    return g


# ── recolección desde la sesión (estado RESULTANTE dentro de la transacción) ─
def _limits():
    from core import governance
    return governance.param('policy.gates', 'limits')


def _flow_rels():
    from ontology import vocabulary as vocab
    return tuple(vocab.flow_relation_types())


def _live(o):
    return o is not None and not (o.properties or {}).get('retired')


def gather_link(session, link, source_id=None):
    """LinkRecord recién materializado → (tripletas, foco). 2 lecturas: extremos (mapa de identidad) e inversos."""
    from sqlalchemy import select

    from ontology.models import LinkRecord, ObjectRecord
    props = link.properties or {}
    weight = link.weight if link.weight is not None else props.get('weight')
    src_ids = [link.source_id, link.target_id]
    endpoints = {}
    for oid in src_ids:
        o = session.get(ObjectRecord, oid)
        endpoints[oid] = {'type': o.type if o is not None else None, 'live': _live(o)}
    inv = []
    for r in session.scalars(select(LinkRecord).where(
            LinkRecord.source_id == link.target_id, LinkRecord.target_id == link.source_id,
            LinkRecord.rel_type == link.rel_type, LinkRecord.valid_to.is_(None)).limit(20)).all():
        if r.id != link.id:
            inv.append({'id': str(r.id), 'source': r.source_id, 'target': r.target_id, 'rel': r.rel_type,
                        'live': (r.properties or {}).get('status') != 'rejected'})
    sources, ev_by = {}, []
    sid = source_id
    if sid:
        so = session.get(ObjectRecord, sid)
        ev_by.append(sid)
        if so is not None and (so.properties or {}).get('trust') is not None:
            sources[sid] = (so.properties or {}).get('trust')
    rec = {'id': str(link.id), 'source': link.source_id, 'target': link.target_id, 'rel': link.rel_type,
           'weight': weight, 'confidence': props.get('confidence'), 'valid_from': link.valid_from,
           'valid_to': link.valid_to, 'rel_label': props.get('rel_label') or props.get('label'),
           'evidenced_by': ev_by, 'dated': bool(props.get('predicate') or props.get('since'))}
    return link_triples(rec, endpoints, inv, sources, _limits(), _flow_rels())


def gather_object(obj, prev_type):
    return object_triples({'id': obj.id, 'type': obj.type, 'prev_type': prev_type, 'props': obj.properties or {}})


def gather_factor(session, obj, prev_props, touches):
    from sqlalchemy import select

    from ontology.models import LinkRecord, ObjectRecord
    members = []
    for r in session.scalars(select(LinkRecord).where(
            LinkRecord.rel_type == 'affects', LinkRecord.source_id == obj.id,
            LinkRecord.valid_to.is_(None)).limit(200)).all():
        tgt = session.get(ObjectRecord, r.target_id)
        members.append({'id': str(r.id), 'target': r.target_id, 'coef': r.weight if r.weight is not None else 1.0,
                        'live': _live(tgt)})
    return factor_triples({'id': obj.id, 'props': obj.properties or {}, 'prev_props': prev_props,
                           'touches': touches, 'members': members}, _limits())


def gather_action(action_type, payload, principal, schema=None, validated=None, auto_apply=False, ident=None,
                  confidence=None):
    """`confidence`: la de la PROPUESTA (auto-aplicación); manda sobre la del payload/modelo si viene."""
    from core import governance
    payload = payload if isinstance(payload, dict) else {}
    unknown = []
    if schema is not None:
        try:
            fields = set(schema.model_fields)
            unknown = sorted(k for k in payload if k not in fields)
        except Exception:  # noqa: BLE001
            unknown = []
    get = (lambda k: getattr(validated, k, None)) if validated is not None else payload.get
    reason = get('razon') if action_type == 'RetractarVinculo' else None
    conf = confidence if confidence is not None else (
        payload.get('confidence') if 'confidence' in payload else (
            getattr(validated, 'confidence', None) if validated is not None else None))
    pr = {'id': getattr(principal, 'id', None), 'kind': getattr(principal, 'kind', None),
          'auth': getattr(principal, 'auth', None)} if principal is not None else {}
    if isinstance(principal, dict):
        pr = principal
    return action_triples({'id': ident, 'action_type': action_type, 'principal': pr, 'auto_apply': auto_apply,
                           'confidence': conf, 'nivel': get('nivel') if action_type == 'MarcarRiesgo' else None,
                           'reason': reason, 'unknown_fields': unknown,
                           'safe_auto': governance.param('policy.auto_apply', 'safe_auto'),
                           'auto_min_conf': governance.param('policy.auto_apply', 'auto_min_confidence')})


def gather_decision(ctx, status):
    quotes = [{'ticker': q.get('ticker'), 'as_of': q.get('as_of'), 'src': q.get('src')}
              for q in (ctx.extra.get('quotes') or [])]
    return decision_triples({'id': str(ctx.id), 'kind': ctx.kind, 'status': status,
                             'principal_kind': getattr(ctx.principal, 'kind', None),
                             'release_hash': ctx.stamp.get('release_hash'),
                             'verdict': (ctx.verdict or {}).get('outcome'), 'quotes': quotes})
