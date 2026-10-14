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

Paso 8 (un solo grafo en el servidor): la MISMA foto trae además el grafo "de lectura" en la forma del
catálogo (`nodes` con todas sus propiedades, `links` {source, target, w, rel, type, conf, verified} y los
diccionarios del catálogo) que sirven la vista `graph` (core/hotviews/views/graph.py) a los 13 lectores del
servidor. En PG: empresas = objetos `Company` vigentes (sin `retired`; `merged_into` pasa a alias), vínculos =
filas vigentes entre esas empresas, propiedades de la base y SOLO los campos que la base no tiene se completan
con el catálogo (nunca lo pisan). Este módulo es, con ontology/reconcile.py y los scripts, el único que lee
data/grafo_v0.json (tests/test_ops_single_source.py).
"""
import hashlib
import json
import os
import time
from dataclasses import dataclass, field

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SNAPSHOT_PATH = os.path.join(ROOT, 'data', 'grafo_v0.json')
FACTORS_PATH = os.path.join(ROOT, 'data', 'multicapa_factors_seats.json')
# severidad LATENTE de los factores sistémicos (= scripts/migrate_v0_to_ontology.FACTOR_LATENT_SEVERITY):
# número del kernel → artefacto `kernel.params.factor_latent_severity` (paso 9)
from core import governance as _gov  # noqa: E402
(
    FACTOR_LATENT_SEVERITY,
) = _gov.bind(globals(), 'kernel.params', {'FACTOR_LATENT_SEVERITY': 'factor_latent_severity'})


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
    # paso 8: el grafo de lectura en la forma del catálogo (None = esta foto no lo trae → sin vista `graph`)
    nodes: list = None                # [{id, label, …propiedades}] empresas vigentes
    links: list = None                # [{source, target, w, rel, type, conf, verified[, since][, status]}]
    catalog: dict = None              # sectors9, categories, legal_names, node_id_alias… + catalog_ids


def _meta_of(label, otype, props):
    """`country` = el texto guardado (no se reescribe); `country_iso2` = ISO-2 DERIVADO (core/countries: hq_country del
    importador > country > loc si country es una región); `hq_country` solo si la ficha lo trae."""
    props = props or {}
    from core import countries as _C
    m = {'label': label, 'type': otype, 'sector': props.get('sector'), 'ticker': props.get('ticker'),
         'country': props.get('country') or props.get('pais'), 'country_iso2': _C.iso2_of_props(props)}
    if props.get('hq_country'):
        m['hq_country'] = props.get('hq_country')
    return m


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
        comp = [(o[0], o[2], o[3]) for o in objs if o[1] == 'Company']     # la misma lectura, sin otra consulta
        r_nodes, r_links, r_catalog = _reader_graph_pg(comp, rows)
        extra = {'alias': r_catalog['node_id_alias']}      # GraphCore.resolve: alias del catálogo + fusiones
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
                     read_ms=round((time.perf_counter() - t0) * 1000, 1), extra=extra,
                     nodes=r_nodes, links=r_links, catalog=r_catalog)


# ── grafo de lectura (paso 8) ───────────────────────────────────────────────
CATALOG_KEYS = ('sectors9', 'categories', 'cat_to_sector', 'legal_names', 'preipo_intel', 'counts',
                'exported_at', 'source', 'voice_aliases', 'resolve_stopwords')


def _catalog_meta(g, sha):
    """Los diccionarios del CATÁLOGO (no son verdad del grafo: etiquetas de sector, nombres legales…) y el
    conjunto de ids del catálogo (para medir cuánto del catálogo trae la base)."""
    meta = {k: g.get(k) for k in CATALOG_KEYS}
    meta['node_id_alias'] = dict(g.get('node_id_alias') or {})
    meta['snapshot_sha'] = sha
    meta['catalog_ids'] = frozenset(n['id'] for n in g.get('nodes') or [] if n.get('id'))
    return meta


def _reader_link_pg(l):
    """Fila vigente de `links` → vínculo en la forma del catálogo. `conf`/`verified` como los exporta
    nodes/merge_graph.js; una confirmación de una persona (LinkStatusChanged) manda: conf 1, verificado."""
    props = l.properties or {}
    conf, ver = props.get('confidence'), props.get('verified')
    if props.get('status') == 'confirmed':
        conf, ver = 1, True
    out = {'source': l.source_id, 'target': l.target_id, 'w': l.weight,
           'rel': props.get('rel_label') or props.get('headline') or '', 'type': l.rel_type or 'supply',
           'conf': conf, 'verified': ver}
    if props.get('since'):
        out['since'] = props.get('since')
    if props.get('status'):
        out['status'] = props.get('status')
    return out


def _reader_graph_pg(comp, rows):
    """(nodes, links, catalog) desde la base. Orden estable = el del catálogo (los nuevos al final, por id),
    para que los desempates de los lectores no cambien solo por la fuente."""
    try:
        snap, sha = _snapshot_parsed()
    except OSError:
        snap, sha = {'nodes': [], 'links': []}, None
    cat = _catalog_meta(snap, sha)
    cat_nodes = {n['id']: n for n in snap.get('nodes') or [] if n.get('id')}
    order = {nid: i for i, nid in enumerate(cat_nodes)}
    alias = cat['node_id_alias']
    nodes, filled, retired = [], 0, 0
    for oid, label, props in comp:
        props = props or {}
        if props.get('retired') is True:
            retired += 1
            if props.get('merged_into') and oid not in alias:
                alias[oid] = props['merged_into']
            continue
        n = {'id': oid, 'label': label or oid}
        n.update({k: v for k, v in props.items() if k not in ('id', 'label')})
        base = cat_nodes.get(oid)
        if base:                       # SOLO lo que la base no tiene; nunca pisa un valor de Postgres
            for k, v in base.items():
                if k not in n:
                    n[k] = v
                    filled += 1
        nodes.append(n)
    nodes.sort(key=lambda n: (order.get(n['id'], len(order)), n['id']))
    known = {n['id'] for n in nodes}
    lorder = {}
    for i, l in enumerate(snap.get('links') or []):
        lorder.setdefault((l.get('source'), l.get('target'), l.get('type') or 'supply'), i)
    links, proposed, facts = [], 0, 0
    for l in rows:
        if l.source_id not in known or l.target_id not in known or l.source_id == l.target_id:
            continue
        props = l.properties or {}
        # Una PROPUESTA (ProponerVinculo: radar, IncorporarEmpresa/tensor con confianza 0) o un vínculo
        # RECHAZADO no es un proveedor/cliente: queda "proposed hasta que una persona lo confirme". Fuera del
        # grafo de lectura (MCP, chat, contexto de investigación, grado de flujo, NRS); sigue en la ontología.
        if props.get('status') in ('proposed', 'rejected'):
            proposed += 1
            continue
        # Hecho temporal migrado (predicate/headline, sin rel_label): su rel_type salió por defecto ('supply'
        # para "Amazon invierte $8B en Anthropic"). El snapshot nunca los trajo como vínculos de lectura →
        # misma regla aquí (siguen en la ImpactView y en el Grafo Temporal, como antes).
        if props.get('predicate') is not None and not props.get('rel_label'):
            facts += 1
            continue
        links.append(_reader_link_pg(l))
    links.sort(key=lambda l: (lorder.get((l['source'], l['target'], l['type']), len(lorder)),
                              l['source'], l['target'], l['type'], str(l.get('rel'))))
    # un par (origen, destino, tipo) = UN vínculo de lectura (como el catálogo): gana el primero con peso
    uniq = {}
    for l in links:
        k = (l['source'], l['target'], l['type'])
        cur = uniq.get(k)
        if cur is None or (cur.get('w') is None and l.get('w') is not None):
            uniq[k] = l
    dups = len(links) - len(uniq)
    links = list(uniq.values())
    links.sort(key=lambda l: (lorder.get((l['source'], l['target'], l['type']), len(lorder)),
                              l['source'], l['target'], l['type'], str(l.get('rel'))))
    cat['stats'] = {'catalog_fields_filled': filled, 'retired': retired,
                    'missing_from_db': sorted(cat['catalog_ids'] - known),
                    'proposed_excluded': proposed, 'facts_excluded': facts, 'duplicates_collapsed': dups}
    return nodes, links, cat


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


def _snapshot_parsed():
    """(dict, sha) del snapshot, parseado UNA vez por versión del archivo. Solo lectura: quien lo use arma
    sus propias estructuras (la vista `graph` congela las suyas)."""
    raw, sha = _snapshot_bytes()
    hit = _SNAP_CACHE.get('parsed')
    if hit and hit[0] == sha:
        return hit[1], sha
    g = json.loads(raw)
    _SNAP_CACHE['parsed'] = (sha, g)
    return g, sha


def load_snapshot():
    """Lo que la migración escribiría en Postgres, sin Postgres (versión 0, linaje = sha del snapshot)."""
    t0 = time.perf_counter()
    g, sha = _snapshot_parsed()
    return from_snapshot(g, sha, t0=t0)


def from_snapshot(g, sha=None, t0=None, factors_data=None):
    """GraphData desde un dict con la forma del snapshot (el archivo, o uno armado a mano: matrix/tensor.evaluate
    y las pruebas). Mismo código que la base usaría: mismas triples, mismos factores latentes.
    `factors_data`: dict con la forma de data/multicapa_factors_seats.json que reemplaza al archivo (grafos
    sintéticos de escala, scripts/gen_synth_graph.py); None = leer FACTORS_PATH, como siempre."""
    from matrix import engine as E
    from ontology import vocabulary as vocab
    t0 = time.perf_counter() if t0 is None else t0
    if sha is None:
        sha = hashlib.sha256(json.dumps(g, sort_keys=True, default=str).encode()).hexdigest()
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
    if factors_data is not None:
        fdata = factors_data
    else:
        try:
            with open(FACTORS_PATH, 'r', encoding='utf-8') as fh:
                fdata = json.load(fh)
        except (OSError, ValueError):
            fdata = {}
    for f in fdata.get('factors') or []:
        fid = (f.get('id') or '').strip()
        members = {m: E.factor_coef(c) for m, c in (f.get('members') or {}).items() if m in known}
        if not fid or not members:
            continue
        crisis = f.get('severity')
        factors.append({'id': fid, 'label': f.get('label') or fid,
                        'severity': float(_gov.param('kernel.params', 'factor_latent_severity')),
                        'severity_crisis': float(crisis) if crisis is not None else None,
                        'rationale': f.get('rationale') or '', 'since': None, 'updated': None,
                        'members': members})
    cat = _catalog_meta(g, sha)
    cat['stats'] = {'catalog_fields_filled': 0, 'retired': 0, 'missing_from_db': []}
    return GraphData('snapshot', 0, 'snap:' + sha[:12], ids, meta, triples, flow_links, factors,
                     read_ms=round((time.perf_counter() - t0) * 1000, 1),
                     extra={'snapshot_sha': sha, 'exported_at': g.get('exported_at'),
                            'alias': g.get('node_id_alias') or {}},
                     nodes=[n for n in g.get('nodes') or [] if n.get('id')],
                     links=list(g.get('links') or []), catalog=cat)


def load():
    """Postgres si está configurada; si no, el snapshot."""
    from ontology.db import ontology_available
    return load_pg() if ontology_available() else load_snapshot()
