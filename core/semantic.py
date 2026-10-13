"""core/semantic.py — CAPA 2 (PRECONSCIENTE): el grafo semántico activo.

La idea de Fabrizio (2026-07-10): antes de que la "capa consciente" (el LLM)
responda, el sistema ya preparó el contexto MÍNIMO Y RELEVANTE — el subgrafo
alrededor de lo que se pregunta, hiper-filtrado, sin saturar la ventana de
contexto ni pagar tokens de más.

build_context(company_ids, question) → dict compacto con:
  - las empresas foco (rol, sector, país, meta),
  - sus vecinos a 1 salto (top por peso, con tipo de relación y dirección),
  - chokepoints globales del grafo (para que el LLM sitúe el riesgo).

Fuente: la vista `graph` de la generación vigente (core/hotviews/hot.graph(): Postgres —incluye lo que el
Radar incorporó— si existe; el catálogo data/grafo_v0.json si no). Lo derivado se arma UNA vez por generación
(paso 8: antes una vez por proceso, y una empresa nueva nunca entraba al contexto).
"""
import threading

_SNAP = {'data': None}
_LOCK = threading.Lock()


def _build(view):
    g = view.snapshot
    by_id = {n['id']: n for n in g['nodes']}
    by_label = {n.get('label', '').lower(): n['id'] for n in g['nodes']}
    by_ticker = {n['mkt'].upper(): n['id'] for n in g['nodes'] if n.get('mkt')}
    out_links, in_links = {}, {}
    for l in g['links']:
        s, t = l.get('source'), l.get('target')
        out_links.setdefault(s, []).append(l)
        in_links.setdefault(t, []).append(l)
    deg = {}
    for l in g['links']:
        deg[l.get('source')] = deg.get(l.get('source'), 0) + 1
        deg[l.get('target')] = deg.get(l.get('target'), 0) + 1
    # grado ESTRUCTURAL (G4d: pares distintos de FLUJO) — el que usan el NRS y los chokepoints
    from ontology.vocabulary import flow_relation_types
    return {'by_id': by_id, 'by_label': by_label, 'by_ticker': by_ticker,
            'out': out_links, 'in': in_links, 'deg': deg,
            'flow_deg': dict(view.flow_degree), 'flow_types': frozenset(flow_relation_types()),
            'generation': view.generation}


def _load_snapshot():
    """El grafo vigente, indexado (by_id, by_label, by_ticker, out, in, deg, flow_deg, flow_types)."""
    from core.hotviews import hot
    view = hot.graph()
    cur = _SNAP['data']
    if cur is not None and cur.get('generation') == view.generation:
        return cur
    with _LOCK:
        cur = _SNAP['data']
        if cur is None or cur.get('generation') != view.generation:
            _SNAP['data'] = _build(view)
        return _SNAP['data']


def graph_version():
    """La generación del grafo que usa la capa semántica (tests/test_ops_single_source.py)."""
    return _load_snapshot().get('generation')


def resolve_ids(names):
    """Nombres/tickers/ids sueltos → ids canónicos del snapshot (los que existan)."""
    snap = _load_snapshot()
    found = []
    for raw in names or []:
        q = str(raw).strip()
        if not q:
            continue
        if q in snap['by_id']:
            found.append(q)
            continue
        tid = snap['by_ticker'].get(q.upper())
        if tid:
            found.append(tid)
            continue
        lid = snap['by_label'].get(q.lower())
        if lid:
            found.append(lid)
            continue
        # subcadena única en labels
        hits = [i for lbl, i in snap['by_label'].items() if q.lower() in lbl]
        if len(set(hits)) == 1:
            found.append(hits[0])
    return list(dict.fromkeys(found))


def extract_companies(question, limit=4):
    """Detección barata (sin IA) de empresas mencionadas en la pregunta."""
    snap = _load_snapshot()
    ql = ' ' + str(question).lower() + ' '
    hits = []
    for lbl, nid in snap['by_label'].items():
        if len(lbl) >= 3 and lbl in ql:
            hits.append((len(lbl), nid))
    hits.sort(reverse=True)
    out = []
    for _, nid in hits:
        if nid not in out:
            out.append(nid)
        if len(out) >= limit:
            break
    return out


def _node_brief(snap, nid):
    n = snap['by_id'].get(nid) or {}
    return {k: n.get(k) for k in ('id', 'label', 'sector', 'cat', 'country',
                                  'role', 'moat', 'growth', 'margin', 'mkt') if n.get(k) is not None}


def build_context(company_ids=None, question=None, neighbors_per_side=8):
    """El contexto preconsciente: foco + vecindario + chokepoints. Compacto
    a propósito — está pensado para entrar en un prompt sin inflarlo."""
    snap = _load_snapshot()
    ids = list(company_ids or [])
    if question and not ids:
        ids = extract_companies(question)
    ids = [i for i in ids if i in snap['by_id']][:4]

    focus = []
    for nid in ids:
        # proveedores / clientes = SOLO flujo (G4a); socios e inversores van aparte en 'relacionados'
        flow = snap['flow_types']
        ins = sorted([l for l in snap['in'].get(nid, []) if (l.get('type') or 'supply') in flow],
                     key=lambda l: -(l.get('w') or 0))[:neighbors_per_side]
        outs = sorted([l for l in snap['out'].get(nid, []) if (l.get('type') or 'supply') in flow],
                      key=lambda l: -(l.get('w') or 0))[:neighbors_per_side]
        rel = sorted([l for l in snap['in'].get(nid, []) + snap['out'].get(nid, [])
                      if (l.get('type') or 'supply') not in flow], key=lambda l: -(l.get('w') or 0))[:4]
        focus.append({
            'empresa': _node_brief(snap, nid),
            'depende_de': [{'de': l['source'], 'tipo': l.get('type'), 'w': l.get('w'),
                            'rel': (l.get('rel') or '')[:90]} for l in ins],
            'provee_a': [{'a': l['target'], 'tipo': l.get('type'), 'w': l.get('w'),
                          'rel': (l.get('rel') or '')[:90]} for l in outs],
            'relacionados': [{'id': l['target'] if l['source'] == nid else l['source'], 'tipo': l.get('type')}
                             for l in rel],
            'grado': snap['flow_deg'].get(nid, 0),
        })

    top_deg = sorted(snap['flow_deg'].items(), key=lambda kv: -kv[1])[:10]
    return {
        'foco': focus,
        'chokepoints_por_grado': [{'id': k, 'links': v} for k, v in top_deg],
        'universo': {'empresas': len(snap['by_id'])},
    }
