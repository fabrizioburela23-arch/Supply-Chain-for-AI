"""core/hotviews/source.py — la fuente CANÓNICA de las vistas (INFRA_OPERATIVA §4.1 punto 1).

Postgres cuando hay DATABASE_URL (la verdad); si no, el snapshot data/grafo_v0.json con el MISMO código de
construcción. Ambas devuelven un `GraphData` con los mismos campos; la diferencia queda en `source`.

PG: UNA transacción `REPEATABLE READ READ ONLY` lee `kh_versions.v` (y el linaje) Y los datos en la misma
foto → la versión que anota la vista es exactamente la de su contenido (Anexo B: 0 inconsistencias en 2.175
fotos con 8 escritores). Las fórmulas son las de matrix/engine (node_index, build_matrices, active_factors):
mismos tipos económicos, mismo orden de ids (ORDER BY id de la base), mismo peso efectivo (_eff_weight ×
link_confidence).

Snapshot: replica lo que scripts/migrate_v0_to_ontology.py escribiría en la base (empresas + objetos de
ontología, vínculos del catálogo, hechos temporales SIN fin, factores latentes de
data/multicapa_factors_seats.json), versión 0.
"""
import hashlib
import json
import os
import time
from dataclasses import dataclass, field

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SNAPSHOT_PATH = os.path.join(ROOT, 'data', 'grafo_v0.json')
FACTORS_PATH = os.path.join(ROOT, 'data', 'multicapa_factors_seats.json')
FACTOR_LATENT_SEVERITY = 1.0          # = scripts/migrate_v0_to_ontology.FACTOR_LATENT_SEVERITY


@dataclass
class GraphData:
    source: str                       # 'pg' | 'snapshot'
    graph_version: int
    lineage: str
    ids: list                         # nodos económicos, en el orden del índice
    meta: dict                        # id → {label, type, sector, ticker, country}
    triples: list                     # (source, target, rel_type, peso efectivo)
    flow_links: list                  # [{source, target, type}] vigentes (grado de flujo en pares distintos)
    factors: list                     # = matrix.engine.active_factors()
    read_ms: float = 0.0
    extra: dict = field(default_factory=dict)


def _meta_of(label, otype, props):
    props = props or {}
    return {'label': label, 'type': otype, 'sector': props.get('sector'), 'ticker': props.get('ticker'),
            'country': props.get('country') or props.get('pais')}


# ── Postgres ────────────────────────────────────────────────────────────────
def load_pg():
    """Lee la verdad en una foto coherente. Lanza si la base no responde (el constructor conserva la vista
    anterior marcada stale)."""
    from sqlalchemy import select, text

    from matrix import engine as E
    from ontology import vocabulary as vocab
    from ontology.db import get_session_factory
    from ontology.models import LinkRecord, ObjectRecord
    t0 = time.perf_counter()
    wall0 = time.time()
    s = get_session_factory()()
    try:
        s.connection(execution_options={'isolation_level': 'REPEATABLE READ', 'postgresql_readonly': True})
        row = s.execute(text(
            "SELECT v, to_regclass('events')::oid, to_regclass('kh_versions')::oid "
            "FROM kh_versions WHERE name = 'graph'")).first()
        v, lineage = (int(row[0]), f'{row[1]}.{row[2]}') if row else (0, None)
        econ = vocab.economic_types()
        objs = s.execute(select(ObjectRecord.id, ObjectRecord.type, ObjectRecord.label, ObjectRecord.properties)
                         .where(ObjectRecord.type.in_(econ)).order_by(ObjectRecord.id)).all()
        ids = [o[0] for o in objs]
        meta = {o[0]: _meta_of(o[2], o[1], o[3]) for o in objs}
        rows = s.scalars(select(LinkRecord).where(LinkRecord.valid_to.is_(None))).all()
        triples, flow_links = [], []
        for l in rows:
            props = l.properties or {}
            triples.append((l.source_id, l.target_id, l.rel_type,
                            E._eff_weight(l.weight, props.get('source'), E.link_confidence(props))))
            flow_links.append({'source': l.source_id, 'target': l.target_id, 'type': l.rel_type})
        factors = E.active_factors(s)
        extra = {}
        try:      # la foto de esta lectura: el sondeo busca después escrituras SIN versión (contenedor viejo)
            from core.hotviews import signals
            extra['snapshot'] = signals.current_snapshot(s)
            extra['snapshot_at'] = wall0
        except Exception:  # noqa: BLE001 — base sin txid: sin vigilancia de huérfanos, la vista igual sale
            pass
    finally:
        try:
            s.rollback()
        finally:
            s.close()
    return GraphData('pg', v, lineage, ids, meta, triples, flow_links, factors,
                     read_ms=round((time.perf_counter() - t0) * 1000, 1), extra=extra)


# ── snapshot ────────────────────────────────────────────────────────────────
_SNAP_CACHE = {}


def _snapshot_bytes():
    st = os.stat(SNAPSHOT_PATH)
    key = (st.st_mtime_ns, st.st_size)
    hit = _SNAP_CACHE.get('raw')
    if hit and hit[0] == key:
        return hit[1], hit[2]
    with open(SNAPSHOT_PATH, 'rb') as fh:
        raw = fh.read()
    sha = hashlib.sha256(raw).hexdigest()
    _SNAP_CACHE['raw'] = (key, raw, sha)
    return raw, sha


def load_snapshot():
    """Lo que la migración escribiría en Postgres, sin Postgres (versión 0, linaje = sha del snapshot)."""
    from matrix import engine as E
    from ontology import vocabulary as vocab
    t0 = time.perf_counter()
    raw, sha = _snapshot_bytes()
    g = json.loads(raw)
    nodes = g.get('nodes') or []
    onto = (g.get('ontology') or {}).get('objects') or []
    econ = set(vocab.economic_types())
    objects = {}
    for n in nodes:
        props = {k: v for k, v in n.items() if k not in ('id', 'label')}
        objects[n['id']] = (n.get('label') or n['id'], 'Company', props)
    for o in onto:
        objects.setdefault(o['id'], (o.get('label') or o['id'], o.get('type', 'Org'), {}))
    known = set(objects)
    ids = sorted(i for i, (_, t, _) in objects.items() if t in econ)
    meta = {i: _meta_of(objects[i][0], objects[i][1], objects[i][2]) for i in ids}

    triples, flow_links = [], []

    def add(src, tgt, rel, w, props):
        triples.append((src, tgt, rel, E._eff_weight(w, props.get('source'), E.link_confidence(props))))
        flow_links.append({'source': src, 'target': tgt, 'type': rel})

    for l in g.get('links') or []:
        src, tgt = l.get('source'), l.get('target')
        if src not in known or tgt not in known or src == tgt:
            continue
        props = {'rel_label': l.get('rel') or ''}
        if l.get('conf') is not None:
            props['confidence'] = l.get('conf')
        if l.get('verified') is not None:
            props['verified'] = bool(l.get('verified'))
        add(src, tgt, l.get('type') or 'supply', l.get('w'), props)
    for f in g.get('temporal_facts') or []:
        if f.get('object_type') != 'node' or f.get('valid_until'):
            continue            # con fin: en la base queda con valid_to → fuera de "ahora" (build_matrices)
        subj, obj = f.get('subject'), f.get('object')
        if subj not in known or obj not in known or subj == obj:
            continue
        add(subj, obj, f.get('rel') or 'supply', None,
            {'headline': (f.get('meta') or {}).get('headline', ''), 'confidence': f.get('confidence'),
             'predicate': f.get('predicate')})

    factors = []
    try:
        with open(FACTORS_PATH, 'r', encoding='utf-8') as fh:
            fdata = json.load(fh)
    except (OSError, ValueError):
        fdata = {}
    for f in fdata.get('factors') or []:
        fid = (f.get('id') or '').strip()
        members = {m: float(c or 1) for m, c in (f.get('members') or {}).items() if m in known}
        if not fid or not members:
            continue
        crisis = f.get('severity')
        factors.append({'id': fid, 'label': f.get('label') or fid, 'severity': FACTOR_LATENT_SEVERITY,
                        'severity_crisis': float(crisis) if crisis is not None else None,
                        'rationale': f.get('rationale') or '', 'since': None, 'updated': None,
                        'members': members})
    return GraphData('snapshot', 0, 'snap:' + sha[:12], ids, meta, triples, flow_links, factors,
                     read_ms=round((time.perf_counter() - t0) * 1000, 1),
                     extra={'snapshot_sha': sha, 'exported_at': g.get('exported_at'),
                            'alias': g.get('node_id_alias') or {}})


def load():
    """Postgres si está configurada; si no, el snapshot."""
    from ontology.db import ontology_available
    return load_pg() if ontology_available() else load_snapshot()
