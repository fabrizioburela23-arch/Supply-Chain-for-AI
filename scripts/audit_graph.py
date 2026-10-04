#!/usr/bin/env python3
"""scripts/audit_graph.py — Auditoría automática del grafo (misión de reparación, G1).

Lee el snapshot canónico `data/grafo_v0.json` (nodes, links, node_id_alias,
categories, sectors9) y produce un dict de hallazgos por categoría + un
resumen bilingüe. PURO por defecto: sin red y sin base de datos; `--db`
(opcional, solo si hay DATABASE_URL) compara con Postgres en SOLO LECTURA.

Categorías RATCHET (cuentan para `data/graph_audit_baseline.json`: no pueden
empeorar; ver tests/test_graph_audit.py):
  duplicate_links        triplas (source, target, type) repetidas
  duplicate_entities     pares de ids distintos NO cubiertos por node_id_alias
                         con la misma etiqueta normalizada o el mismo `mkt`
  suspicious_directions  (1) supply/fab/cloud cuyo `rel` empieza por un verbo
                         de consumo ("usa", "depende", "compra", "recibe",
                         "fabrica … en") Y nombra al TARGET como proveedor sin
                         nombrar al source — el texto del catálogo suele estar
                         escrito desde el punto de vista del cliente
                         ("TSMC→Achronix fab: Fabrica sus FPGA en TSMC" es
                         CORRECTO), así que el verbo solo no basta;
                         (2) supply/fab/cloud cuyo source es un servicio no
                         industrial (agencia de rating, broker inmobiliario,
                         índice, banco, fondo, trader de energía…);
                         (3) pares A→B y B→A con el MISMO tipo no simétrico
                         (partner es simétrica según ontology/vocabulary.json)
  no_source_text         links con `rel` vacío
  unverified_weighted    `rel` con "no verificad" / "posible" / "no revisad" /
                         "no confirmad" / "sin confirmar" y w > 1
  orphans                nodos con grado 0
  bad_vocab              `type` fuera de ontology/vocabulary.json, `cat` fuera de
                         las categorías del snapshot o `sector` fuera de sectors9

Categorías INFORMATIVAS (se reportan, no se ratchetean):
  undated_figures        nodos con margin/capex_2026 sin fecha propia
  missing_coverage       semis analógicos/mixed-signal ausentes (ADI, TXN…)
  pairs_multi_type       pares (source,target) con más de un tipo de enlace

Uso:
    python scripts/audit_graph.py [--format json|md] [--snapshot RUTA]
                                  [--baseline RUTA | --no-baseline] [--strict]
                                  [--write-baseline] [--limit N] [--db]
Salida: 0 si ninguna categoría ratchet supera el baseline (o, con --strict,
si todas están en 0); 1 en caso contrario. --write-baseline escribe
data/graph_audit_baseline.json con los números actuales y sale con 0.
"""
import argparse
import collections
import datetime as _dt
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT_PATH = os.path.join(ROOT, 'data', 'grafo_v0.json')
BASELINE_PATH = os.path.join(ROOT, 'data', 'graph_audit_baseline.json')
VOCAB_PATH = os.path.join(ROOT, 'ontology', 'vocabulary.json')

RATCHET = ('duplicate_links', 'duplicate_entities', 'suspicious_directions',
           'no_source_text', 'unverified_weighted', 'orphans', 'bad_vocab')
INFO = ('undated_figures', 'missing_coverage', 'pairs_multi_type')

LABELS = {
    'duplicate_links': {'es': 'Enlaces duplicados (source, target, type)', 'en': 'Duplicate links (source, target, type)'},
    'duplicate_entities': {'es': 'Entidades duplicadas sin alias (misma etiqueta o mismo ticker)', 'en': 'Duplicate entities without alias (same label or ticker)'},
    'suspicious_directions': {'es': 'Direcciones sospechosas (verbo de consumo hacia el target, fuente de servicio, par bidireccional)', 'en': 'Suspicious directions (consumption verb towards target, service source, bidirectional pair)'},
    'no_source_text': {'es': 'Enlaces sin texto de relación', 'en': 'Links without relation text'},
    'unverified_weighted': {'es': 'Enlaces "no verificados" con peso > 1', 'en': '"Unverified" links with weight > 1'},
    'orphans': {'es': 'Nodos huérfanos (grado 0)', 'en': 'Orphan nodes (degree 0)'},
    'bad_vocab': {'es': 'Fuera de vocabulario (type / cat / sector)', 'en': 'Out of vocabulary (type / cat / sector)'},
    'undated_figures': {'es': 'Nodos con margin/capex sin fecha (informativo)', 'en': 'Nodes with undated margin/capex (informational)'},
    'missing_coverage': {'es': 'Cobertura faltante: semis analógicos (informativo)', 'en': 'Missing coverage: analog semis (informational)'},
    'pairs_multi_type': {'es': 'Pares con más de un tipo de enlace (informativo)', 'en': 'Pairs with more than one link type (informational)'},
}

# Tipos cuya dirección significa "source PROVEE a target" de forma estricta.
DIRECTIONAL_TYPES = frozenset({'supply', 'fab', 'cloud'})

# Categorías de SERVICIO no industrial: no "suministran", "fabrican" ni "dan
# nube" a nadie. Un supply/fab/cloud que sale de ellas es cobertura, asesoría,
# tenencia o (traders) una COMPRA escrita al revés — se revisa a mano.
SERVICE_CATS = frozenset({
    'rating_agency', 'real_estate_services', 'index_provider', 'cds_index_provider',
    'exchange_index_provider', 'derivatives_standards', 'exchange_derivatives',
    'investment_bank', 'universal_bank', 'asset_manager', 'alternative_asset_manager',
    'pension_fund', 'sovereign_fund', 'private_equity', 'private_credit',
    'venture_capital', 'growth_equity', 'infrastructure_investor', 'central_bank',
    'treasury', 'bis', 'energy_trading',
})

# Verbos de CONSUMO al inicio del texto (adaptado de CONSUME_RE en
# scripts/ingest_enrichment_md.py, anclado al inicio porque aquí se audita
# texto ya canonizado, no se infiere dirección).
CONSUME_START_RE = re.compile(
    r'^\s*(?:usa[n]?|utiliza[n]?|depende[n]?|compra[n]?|comprador(?:a|es)?|adquiere[n]?|'
    r'recibe[n]?|consume[n]?|contrata[n]?|clientes? de|se abastece[n]?|alojad[oa]s? en|'
    r'corre[n]? sobre|basad[oa]s? en|licencia de|opera[n]? sobre)\b', re.I)
# "Fabrica sus chips en <target>": el que fabrica es el target. El nombre del
# target debe ir justo tras "en" (si no, "Fabrica A18 en N3E — Apple es el 1º
# cliente" se marcaría al revés).
FAB_START_RE = re.compile(r'^\s*fabrica(?:n|do|dos|da|das)?\b', re.I)
FAB_EN_PREFIX = r'\ben\s+(?:(?:la|el|los|las|su|sus|de|del|planta|plantas|f[áa]brica|f[áa]bricas|fabs?|proceso|procesos|nodos?)\s+){0,3}(?:'

UNVERIFIED_RE = re.compile(r'no verificad|\bposible|no revisad|no confirmad|sin confirmar', re.I)

SUFFIX_RE = re.compile(
    r'\s+(?:inc|corp|corporation|ltd|limited|co|company|group|trust|holdings?|plc)\.?\s*$', re.I)

# Semis analógicos / mixed-signal que el universo debería cubrir (aviso).
COVERAGE_WANTED = (
    ('ADI', 'Analog Devices'), ('TXN', 'Texas Instruments'), ('MCHP', 'Microchip'),
    ('NXPI', 'NXP Semiconductors'), ('ON', 'onsemi'), ('STM', 'STMicroelectronics'),
)

DATE_KEYS = ('as_of', 'figures_as_of', 'data_as_of', 'margin_as_of', 'capex_as_of')

# Vocabulario histórico exacto (fallback si vocabulary.json no se puede leer).
_FALLBACK_RELS = ('supply', 'cloud', 'fab', 'license', 'partner', 'invest', 'deploy', 'owns', 'ppa')
_FALLBACK_SYMMETRIC = frozenset({'partner'})


# ── carga ───────────────────────────────────────────────────────────────────

def load_snapshot(path=SNAPSHOT_PATH):
    with open(path, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def load_vocab(path=VOCAB_PATH):
    """{'rel_types': set, 'structural': list(ordenada), 'symmetric': set}."""
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        rt = data.get('relation_types') or {}
        if not rt:
            raise ValueError('relation_types vacío')
        return {
            'rel_types': set(rt.keys()),
            'structural': [k for k, v in rt.items() if (v or {}).get('structural')],
            'symmetric': {k for k, v in rt.items() if (v or {}).get('symmetric')},
        }
    except Exception:  # noqa: BLE001 — sin vocabulario no se para la auditoría
        return {'rel_types': set(_FALLBACK_RELS), 'structural': list(_FALLBACK_RELS),
                'symmetric': set(_FALLBACK_SYMMETRIC)}


def load_baseline(path=BASELINE_PATH):
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


# ── normalización de nombres ────────────────────────────────────────────────

def norm_label(label):
    """minúsculas, sin paréntesis finales, sin sufijos corporativos (Inc/Corp/
    Ltd/Co/Company/Group/Trust/Holdings/PLC), sin espacios/guiones/puntos."""
    s = (label or '').strip().lower()
    s = re.sub(r'\s*\([^)]*\)\s*$', '', s)
    prev = None
    while prev != s:
        prev = s
        s = SUFFIX_RE.sub('', s)
    return re.sub(r'[\s\-_.·+&,/]', '', s)


def _resolver(alias):
    alias = alias or {}

    def resolve(i):
        cur, hops = i, 0
        while cur in alias and hops < 5:
            cur = alias[cur]
            hops += 1
        return cur
    return resolve


def _name_variants(node, alias_names):
    out = set()
    for raw in (node.get('label') or '', node.get('id') or ''):
        s = re.sub(r'\s*\([^)]*\)\s*$', '', (raw or '').strip())
        if s:
            out.add(s)
            prev = None
            while prev != s:
                prev = s
                s = SUFFIX_RE.sub('', s)
            out.add(s)
    nid = node.get('id') or ''
    out.add(re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', nid.replace('_', ' ').replace('-', ' ')))
    out.update(alias_names)
    return [v for v in out if len(re.sub(r'[^A-Za-z0-9]', '', v)) >= 3]


def _name_pattern(variants):
    """Alternación regex (texto) que reconoce cualquiera de las variantes del
    nombre, tolerando separadores ('Kinder Morgan' ≈ 'KinderMorgan')."""
    pats = []
    for v in sorted(set(variants)):
        toks = [t for t in re.split(r'[^A-Za-z0-9]+', v) if t]
        if toks:
            pats.append(r'(?<![A-Za-z0-9])' + r'[\s\-_.+&/]*'.join(re.escape(t) for t in toks) + r'(?![A-Za-z0-9])')
    return '|'.join(pats) if pats else ''


# ── auditoría del snapshot ──────────────────────────────────────────────────

def audit_snapshot(snap, vocab=None):
    vocab = vocab or load_vocab()
    nodes = snap.get('nodes') or []
    links = snap.get('links') or []
    alias = snap.get('node_id_alias') or {}
    categories = snap.get('categories') or {}
    sectors = snap.get('sectors9') or {}
    resolve = _resolver(alias)
    by_id = {n.get('id'): n for n in nodes if n.get('id')}
    f = {k: [] for k in RATCHET + INFO}

    # (a) enlaces duplicados ────────────────────────────────────────────────
    triples = collections.Counter((l.get('source'), l.get('target'), l.get('type') or 'supply') for l in links)
    for (s, t, ty), n in sorted(triples.items()):
        if n > 1:
            f['duplicate_links'].append({'source': s, 'target': t, 'type': ty, 'n': n})

    # (b) entidades duplicadas sin alias ────────────────────────────────────
    by_label = collections.defaultdict(list)
    by_mkt = collections.defaultdict(list)
    for n in nodes:
        nid = n.get('id')
        if not nid:
            continue
        key = norm_label(n.get('label'))
        if key:
            by_label[key].append(nid)
        mkt = (n.get('mkt') or '').strip().upper()
        if mkt:
            by_mkt[mkt].append(nid)
    pairs = {}
    for kind, groups in (('label', by_label), ('ticker', by_mkt)):
        for key, ids in groups.items():
            ids = sorted(set(ids))
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    a, b = ids[i], ids[j]
                    if resolve(a) == resolve(b):
                        continue  # cubierto por node_id_alias
                    e = pairs.setdefault((a, b), {'ids': [a, b], 'labels': [by_id[a].get('label'), by_id[b].get('label')], 'reasons': [], 'keys': []})
                    e['reasons'].append(kind)
                    e['keys'].append(key)
    f['duplicate_entities'] = [pairs[k] for k in sorted(pairs)]

    # (c) direcciones sospechosas ────────────────────────────────────────────
    alias_by_canon = collections.defaultdict(list)
    for k, v in alias.items():
        alias_by_canon[resolve(v)].append(k)
    _pat_cache, _rx_cache, _fab_cache = {}, {}, {}

    def name_pattern(nid):
        if nid not in _pat_cache:
            node = by_id.get(nid) or {'id': nid}
            _pat_cache[nid] = _name_pattern(_name_variants(node, alias_by_canon.get(nid, [])))
        return _pat_cache[nid]

    def mentions(text, nid):
        if nid not in _rx_cache:
            pat = name_pattern(nid)
            _rx_cache[nid] = re.compile(pat, re.I) if pat else None
        rx = _rx_cache[nid]
        return bool(rx and rx.search(text))

    def fab_en_target(text, nid):
        """'Fabrica … en <target>' (el target es quien fabrica)."""
        if not FAB_START_RE.search(text):
            return False
        if nid not in _fab_cache:
            pat = name_pattern(nid)
            _fab_cache[nid] = re.compile(FAB_EN_PREFIX + pat + ')', re.I) if pat else None
        rx = _fab_cache[nid]
        return bool(rx and rx.search(text))

    for l in links:
        ty = l.get('type') or 'supply'
        if ty not in DIRECTIONAL_TYPES:
            continue
        s, t, rel = l.get('source'), l.get('target'), (l.get('rel') or '')
        if rel and ((CONSUME_START_RE.search(rel) and mentions(rel, t)) or fab_en_target(rel, t)) and not mentions(rel, s):
            f['suspicious_directions'].append({'source': s, 'target': t, 'type': ty, 'w': l.get('w'), 'rel': rel,
                                               'reason': 'consume_verb_target'})
        scat = (by_id.get(s) or {}).get('cat')
        if scat in SERVICE_CATS:
            f['suspicious_directions'].append({'source': s, 'target': t, 'type': ty, 'w': l.get('w'), 'rel': rel,
                                               'reason': 'service_source', 'source_cat': scat})
    fwd = collections.defaultdict(set)
    for l in links:
        fwd[(l.get('source'), l.get('target'))].add(l.get('type') or 'supply')
    seen = set()
    for (a, b), types in sorted(fwd.items()):
        if (b, a) not in fwd or (b, a) in seen:
            continue
        seen.add((a, b))
        for ty in sorted((types & fwd[(b, a)]) - vocab['symmetric']):
            f['suspicious_directions'].append({'source': a, 'target': b, 'type': ty, 'reason': 'bidirectional_same_type'})

    # (d) sin texto ─────────────────────────────────────────────────────────
    for l in links:
        if not (l.get('rel') or '').strip():
            f['no_source_text'].append({'source': l.get('source'), 'target': l.get('target'), 'type': l.get('type') or 'supply'})

    # (e) no verificados con peso ───────────────────────────────────────────
    for l in links:
        rel = l.get('rel') or ''
        try:
            w = float(l.get('w') or 0)
        except (TypeError, ValueError):
            w = 0.0
        if w > 1 and UNVERIFIED_RE.search(rel):
            f['unverified_weighted'].append({'source': l.get('source'), 'target': l.get('target'),
                                             'type': l.get('type') or 'supply', 'w': l.get('w'), 'rel': rel})

    # (f) huérfanos ─────────────────────────────────────────────────────────
    degree = collections.Counter()
    for l in links:
        degree[l.get('source')] += 1
        degree[l.get('target')] += 1
    f['orphans'] = sorted(nid for nid in by_id if degree[nid] == 0)

    # (g) vocabulario ───────────────────────────────────────────────────────
    for l in links:
        ty = l.get('type') or 'supply'
        if ty not in vocab['rel_types']:
            f['bad_vocab'].append({'kind': 'rel_type', 'value': ty, 'source': l.get('source'), 'target': l.get('target')})
    for n in nodes:
        if categories and n.get('cat') not in categories:
            f['bad_vocab'].append({'kind': 'cat', 'value': n.get('cat'), 'id': n.get('id')})
        if sectors and n.get('sector') and n.get('sector') not in sectors:
            f['bad_vocab'].append({'kind': 'sector', 'value': n.get('sector'), 'id': n.get('id')})

    # (h) cifras sin fecha (informativo) ───────────────────────────────────
    for n in nodes:
        has_fig = n.get('margin') is not None or bool(n.get('capex_2026'))
        if has_fig and not any(n.get(k) for k in DATE_KEYS):
            f['undated_figures'].append(n.get('id'))

    # (i) cobertura faltante (informativo) ─────────────────────────────────
    have = {(n.get('mkt') or '').split('.')[0].strip().upper() for n in nodes}
    for tk, name in COVERAGE_WANTED:
        if tk not in have:
            f['missing_coverage'].append({'ticker': tk, 'name': name})

    # pares multi-tipo (informativo) ─────────────────────────────────────────
    for (a, b), types in sorted(fwd.items()):
        if len(types) > 1:
            f['pairs_multi_type'].append({'source': a, 'target': b, 'types': sorted(types)})

    metrics = {k: len(f[k]) for k in RATCHET}
    info = {k: len(f[k]) for k in INFO}
    res = {
        'snapshot': {'exported_at': snap.get('exported_at'), 'nodes': len(nodes), 'links': len(links)},
        'metrics': metrics,
        'info': info,
        'findings': f,
        'labels': LABELS,
    }
    res['summary'] = {'es': summary(res, 'es'), 'en': summary(res, 'en')}
    return res


def summary(res, lang='es'):
    m, i, s = res['metrics'], res['info'], res['snapshot']
    date = (s.get('exported_at') or '')[:10]
    if lang == 'en':
        return (f"Graph audit (snapshot {date}): {s['nodes']} nodes, {s['links']} links · duplicate links {m['duplicate_links']} · "
                f"duplicate entities {m['duplicate_entities']} · suspicious directions {m['suspicious_directions']} · "
                f"no text {m['no_source_text']} · unverified with weight {m['unverified_weighted']} · orphans {m['orphans']} · "
                f"out of vocabulary {m['bad_vocab']} · (info) undated figures {i['undated_figures']}, "
                f"missing coverage {i['missing_coverage']}, multi-type pairs {i['pairs_multi_type']}")
    return (f"Auditoría del grafo (snapshot {date}): {s['nodes']} nodos, {s['links']} enlaces · enlaces duplicados {m['duplicate_links']} · "
            f"entidades duplicadas {m['duplicate_entities']} · direcciones sospechosas {m['suspicious_directions']} · "
            f"sin texto {m['no_source_text']} · no verificados con peso {m['unverified_weighted']} · huérfanos {m['orphans']} · "
            f"fuera de vocabulario {m['bad_vocab']} · (info) cifras sin fecha {i['undated_figures']}, "
            f"cobertura faltante {i['missing_coverage']}, pares multi-tipo {i['pairs_multi_type']}")


# ── baseline (ratchet) ──────────────────────────────────────────────────────

def compare_baseline(res, baseline):
    """{'worse': {cat: (antes, ahora)}, 'better': {...}, 'ok': bool}. Solo RATCHET."""
    out = {'worse': {}, 'better': {}, 'ok': True}
    base = (baseline or {}).get('metrics') or {}
    for k in RATCHET:
        if k not in base:
            continue
        before, now = int(base[k]), int(res['metrics'].get(k, 0))
        if now > before:
            out['worse'][k] = (before, now)
            out['ok'] = False
        elif now < before:
            out['better'][k] = (before, now)
    return out


def build_baseline(res):
    return {
        '_doc': 'Línea base de scripts/audit_graph.py (G1). Las categorías de `metrics` NO pueden empeorar '
                '(tests/test_graph_audit.py); `info` es solo informativo. Regenerar con '
                '`python scripts/audit_graph.py --write-baseline` tras una mejora consciente.',
        'generated_at': _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
        'snapshot_exported_at': res['snapshot'].get('exported_at'),
        'nodes': res['snapshot']['nodes'],
        'links': res['snapshot']['links'],
        'metrics': dict(res['metrics']),
        'info': dict(res['info']),
    }


# ── comparación con Postgres (opcional, SOLO lectura) ───────────────────────

def audit_db(snap, vocab=None, sample=15):
    """Compara los links vigentes de la base (links.valid_to IS NULL) con el
    snapshot. Nunca escribe: la transacción se abre READ ONLY."""
    if not os.getenv('DATABASE_URL'):
        return {'available': False, 'reason': 'DATABASE_URL no configurada / not set'}
    try:
        sys.path.insert(0, ROOT)
        from sqlalchemy import text
        from ontology.db import session_scope
    except Exception as e:  # noqa: BLE001
        return {'available': False, 'reason': f'ontología no importable: {e}'}
    vocab = vocab or load_vocab()
    structural = set(vocab['structural'])
    resolve = _resolver(snap.get('node_id_alias') or {})
    snap_triples = {(resolve(l.get('source')), resolve(l.get('target')), l.get('type') or 'supply')
                    for l in (snap.get('links') or [])}
    out = {'available': True}
    try:
        with session_scope() as s:
            s.execute(text('SET TRANSACTION READ ONLY'))
            rows = s.execute(text(
                'SELECT source_id, target_id, rel_type, weight, valid_from FROM links WHERE valid_to IS NULL')).fetchall()
            exact = collections.Counter((r[0], r[1], r[2]) for r in rows)
            db_struct = {(resolve(r[0]), resolve(r[1]), r[2]) for r in rows if r[2] in structural}
            in_db_not_snap = sorted(db_struct - snap_triples)
            in_snap_not_db = sorted(snap_triples - db_struct)
            genesis = sum(1 for r in rows if r[4] and r[4].strftime('%Y-%m-%d') == '2000-01-01')
            out.update({
                'links_current': len(rows),
                'links_structural': len(db_struct),
                'links_genesis_pct': round(100.0 * genesis / len(rows), 1) if rows else 0.0,
                'exact_duplicates': {'n': sum(1 for v in exact.values() if v > 1),
                                     'sample': [{'source': k[0], 'target': k[1], 'type': k[2], 'n': v}
                                                for k, v in sorted(exact.items()) if v > 1][:sample]},
                'in_db_not_snapshot': {'n': len(in_db_not_snap),
                                       'sample': [{'source': a, 'target': b, 'type': t} for a, b, t in in_db_not_snap[:sample]]},
                'in_snapshot_not_db': {'n': len(in_snap_not_db),
                                       'sample': [{'source': a, 'target': b, 'type': t} for a, b, t in in_snap_not_db[:sample]]},
            })
            ev = s.execute(text(
                "SELECT source AS canal, event_type, count(*) AS n, "
                "sum(CASE WHEN valid_from::date = DATE '2000-01-01' THEN 1 ELSE 0 END) AS genesis, "
                "sum(CASE WHEN source_id IS NULL THEN 1 ELSE 0 END) AS sin_fuente "
                "FROM events GROUP BY 1, 2 ORDER BY 1, 2")).fetchall()
            by_channel = {}
            for canal, etype, n, gen, sinf in ev:
                c = by_channel.setdefault(canal, {'events': 0, 'without_source_id': 0, 'link_created': 0, 'link_created_genesis': 0})
                c['events'] += int(n)
                c['without_source_id'] += int(sinf or 0)
                if etype == 'LinkCreated':
                    c['link_created'] += int(n)
                    c['link_created_genesis'] += int(gen or 0)
            for c in by_channel.values():
                c['without_source_pct'] = round(100.0 * c['without_source_id'] / c['events'], 1) if c['events'] else 0.0
                c['genesis_pct'] = round(100.0 * c['link_created_genesis'] / c['link_created'], 1) if c['link_created'] else None
            out['by_channel'] = by_channel
    except Exception as e:  # noqa: BLE001
        out['error'] = str(e)[:300]
    return out


# ── salida ──────────────────────────────────────────────────────────────────

def _fmt_finding(cat, x):
    if isinstance(x, str):
        return x
    if cat == 'duplicate_entities':
        return f"{x['ids'][0]} ≈ {x['ids'][1]} ({', '.join(x['reasons'])}: {' / '.join(map(str, x['labels']))})"
    if cat == 'suspicious_directions':
        extra = f" [{x.get('source_cat')}]" if x.get('source_cat') else ''
        rel = (x.get('rel') or '')[:90]
        return f"{x['source']} → {x['target']} ({x['type']}) · {x['reason']}{extra}" + (f" · «{rel}»" if rel else '')
    if cat == 'bad_vocab':
        return f"{x['kind']}={x['value']!r} en {x.get('id') or (str(x.get('source')) + ' → ' + str(x.get('target')))}"
    if cat == 'missing_coverage':
        return f"{x['ticker']} ({x['name']})"
    if cat == 'pairs_multi_type':
        return f"{x['source']} → {x['target']} ({', '.join(x['types'])})"
    if cat in ('duplicate_links', 'no_source_text', 'unverified_weighted'):
        tail = f" · n={x['n']}" if 'n' in x else ''
        tail += f" · w={x['w']} · «{(x.get('rel') or '')[:90]}»" if 'w' in x else ''
        return f"{x['source']} → {x['target']} ({x['type']}){tail}"
    return json.dumps(x, ensure_ascii=False)


def to_markdown(res, baseline=None, cmp=None, limit=12, db=None):
    s = res['snapshot']
    base = (baseline or {}).get('metrics') or {}
    base_info = (baseline or {}).get('info') or {}
    out = ['# Auditoría del grafo · Graph audit', '',
           f"Snapshot: {s.get('exported_at')} · {s['nodes']} nodos/nodes · {s['links']} enlaces/links", '',
           f"**ES** {res['summary']['es']}", '', f"**EN** {res['summary']['en']}", '',
           '| Categoría / Category | Ahora / Now | Base | Δ |', '|---|---:|---:|---:|']
    for k in RATCHET:
        now = res['metrics'][k]
        b = base.get(k)
        delta = '' if b is None else ('=' if now == b else f"{now - b:+d}")
        out.append(f"| {LABELS[k]['es']} / {LABELS[k]['en']} | {now} | {'' if b is None else b} | {delta} |")
    for k in INFO:
        now = res['info'][k]
        b = base_info.get(k)
        delta = '' if b is None else ('=' if now == b else f"{now - b:+d}")
        out.append(f"| _{LABELS[k]['es']} / {LABELS[k]['en']}_ | {now} | {'' if b is None else b} | {delta} |")
    if cmp is not None:
        out.append('')
        if cmp['worse']:
            out.append('**EMPEORA / WORSE:** ' + ', '.join(f"{k} {a}→{b}" for k, (a, b) in cmp['worse'].items()))
        elif cmp['better']:
            out.append('**Mejora / Better:** ' + ', '.join(f"{k} {a}→{b}" for k, (a, b) in cmp['better'].items()))
        else:
            out.append('Sin cambios frente a la base / No change vs baseline.')
    for k in RATCHET + INFO:
        items = res['findings'][k]
        if not items:
            continue
        out += ['', f"## {LABELS[k]['es']} / {LABELS[k]['en']} — {len(items)}", '']
        for x in items[:limit]:
            out.append(f"- {_fmt_finding(k, x)}")
        if len(items) > limit:
            out.append(f"- … (+{len(items) - limit})")
    if db is not None:
        out += ['', '## Base de datos / Database (solo lectura · read-only)', '']
        if not db.get('available'):
            out.append(f"- no disponible / unavailable: {db.get('reason')}")
        elif db.get('error'):
            out.append(f"- error: {db['error']}")
        else:
            out.append(f"- links vigentes / current: {db['links_current']} (estructurales {db['links_structural']}; "
                       f"valid_from 2000-01-01: {db['links_genesis_pct']} %)")
            out.append(f"- duplicados exactos en la base / exact duplicates: {db['exact_duplicates']['n']}")
            out.append(f"- en la base y no en el snapshot / in DB not in snapshot: {db['in_db_not_snapshot']['n']}")
            out.append(f"- en el snapshot y no en la base / in snapshot not in DB: {db['in_snapshot_not_db']['n']}")
            for canal, c in sorted((db.get('by_channel') or {}).items()):
                gp = '—' if c['genesis_pct'] is None else f"{c['genesis_pct']} %"
                out.append(f"- canal `{canal}`: {c['events']} eventos, sin source_id {c['without_source_pct']} %, "
                           f"LinkCreated con 2000-01-01: {gp}")
            for key in ('exact_duplicates', 'in_db_not_snapshot', 'in_snapshot_not_db'):
                for x in db[key]['sample'][:limit]:
                    out.append(f"  - {key}: {x['source']} → {x['target']} ({x['type']})" + (f" ×{x['n']}" if 'n' in x else ''))
    return '\n'.join(out) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description='Auditoría automática del grafo (snapshot, sin red).')
    ap.add_argument('--format', choices=('json', 'md'), default='md')
    ap.add_argument('--snapshot', default=SNAPSHOT_PATH)
    ap.add_argument('--baseline', default=BASELINE_PATH)
    ap.add_argument('--no-baseline', action='store_true', help='no comparar con la línea base')
    ap.add_argument('--strict', action='store_true', help='salida 1 si alguna categoría ratchet es > 0')
    ap.add_argument('--write-baseline', action='store_true', help='escribe la línea base con los números actuales')
    ap.add_argument('--limit', type=int, default=12, help='muestras por categoría en Markdown')
    ap.add_argument('--db', action='store_true', help='comparar con Postgres (DATABASE_URL), solo lectura')
    args = ap.parse_args(argv)

    try:  # Windows: consola sin UTF-8
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:  # noqa: BLE001
        pass

    snap = load_snapshot(args.snapshot)
    vocab = load_vocab()
    res = audit_snapshot(snap, vocab)
    db = audit_db(snap, vocab) if args.db else None

    if args.write_baseline:
        with open(args.baseline, 'w', encoding='utf-8') as fh:
            json.dump(build_baseline(res), fh, ensure_ascii=False, indent=2)
            fh.write('\n')
        print(f"línea base escrita / baseline written: {args.baseline}")
        return 0

    baseline = None if args.no_baseline else load_baseline(args.baseline)
    cmp = compare_baseline(res, baseline) if baseline else None
    if args.format == 'json':
        payload = dict(res)
        payload['baseline'] = cmp
        if db is not None:
            payload['db'] = db
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(to_markdown(res, baseline, cmp, limit=args.limit, db=db))

    if cmp is not None and not cmp['ok']:
        return 1
    if args.strict and any(res['metrics'][k] > 0 for k in RATCHET):
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
