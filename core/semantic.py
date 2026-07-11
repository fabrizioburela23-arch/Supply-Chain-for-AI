"""core/semantic.py — CAPA 2 (PRECONSCIENTE): el grafo semántico activo.

La idea de Fabrizio (2026-07-10): antes de que la "capa consciente" (el LLM)
responda, el sistema ya preparó el contexto MÍNIMO Y RELEVANTE — el subgrafo
alrededor de lo que se pregunta, hiper-filtrado, sin saturar la ventana de
contexto ni pagar tokens de más.

build_context(company_ids, question) → dict compacto con:
  - las empresas foco (rol, sector, país, meta),
  - sus vecinos a 1 salto (top por peso, con tipo de relación y dirección),
  - chokepoints globales del grafo (para que el LLM sitúe el riesgo).

Fuentes (en orden): ontología viva (Postgres, incluye lo que el Radar
incorporó) → snapshot data/grafo_v0.json (555 curadas, siempre disponible).
El snapshot se carga UNA vez por proceso (caché de módulo).
"""
import json
import os
import threading

_SNAP = {'data': None}
_LOCK = threading.Lock()


def _load_snapshot():
    if _SNAP['data'] is not None:
        return _SNAP['data']
    with _LOCK:
        if _SNAP['data'] is not None:
            return _SNAP['data']
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'data', 'grafo_v0.json')
        with open(path, 'r', encoding='utf-8') as f:
            g = json.load(f)
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
        _SNAP['data'] = {'by_id': by_id, 'by_label': by_label, 'by_ticker': by_ticker,
                         'out': out_links, 'in': in_links, 'deg': deg}
    return _SNAP['data']


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
        ins = sorted(snap['in'].get(nid, []), key=lambda l: -(l.get('w') or 0))[:neighbors_per_side]
        outs = sorted(snap['out'].get(nid, []), key=lambda l: -(l.get('w') or 0))[:neighbors_per_side]
        focus.append({
            'empresa': _node_brief(snap, nid),
            'depende_de': [{'de': l['source'], 'tipo': l.get('type'), 'w': l.get('w'),
                            'rel': (l.get('rel') or '')[:90]} for l in ins],
            'provee_a': [{'a': l['target'], 'tipo': l.get('type'), 'w': l.get('w'),
                          'rel': (l.get('rel') or '')[:90]} for l in outs],
            'grado': snap['deg'].get(nid, 0),
        })

    top_deg = sorted(snap['deg'].items(), key=lambda kv: -kv[1])[:10]
    return {
        'foco': focus,
        'chokepoints_por_grado': [{'id': k, 'links': v} for k, v in top_deg],
        'universo': {'empresas': len(snap['by_id'])},
    }
