"""matrix/api.py — blueprint Flask del motor de matrices: /api/matrix/*.

Igual que la ontología: opcional y defensivo — sin DATABASE_URL responde 503
y el resto de la app sigue intacta. NO tocar /v1/* (API monetizada).
"""
from flask import Blueprint, jsonify, request

matrix_bp = Blueprint('matrix', __name__, url_prefix='/api/matrix')


def _db():
    from ontology.db import ontology_available, session_scope
    if not ontology_available():
        return None
    return session_scope


@matrix_bp.get('/status')
def matrix_status():
    scope = _db()
    if scope is None:
        return jsonify({'available': False, 'reason': 'DATABASE_URL no configurada'}), 503
    from matrix.engine import REL_TYPES, active_factors, node_index
    with scope() as s:
        idx, ids = node_index(s)
        factors = active_factors(s)
    return jsonify({'available': True, 'objects': len(ids),
                    'rel_types': REL_TYPES,
                    'active_factors': [{'id': f['id'], 'label': f['label'],
                                        'severity': f['severity'],
                                        'members': len(f['members'])}
                                       for f in factors]})


@matrix_bp.get('/<rel_type>')
def matrix_get(rel_type):
    scope = _db()
    if scope is None:
        return jsonify({'error': 'DATABASE_URL no configurada'}), 503
    from matrix.engine import REL_TYPES, active_factors, build_matrices, modulate
    if rel_type not in REL_TYPES:
        return jsonify({'error': f'rel_type desconocido. Válidos: {REL_TYPES}'}), 400
    as_of = request.args.get('as_of')
    with scope() as s:
        mats, idx, ids = build_matrices(s, as_of=as_of)
        if request.args.get('modulated', '1') != '0':
            mats = modulate(mats, idx, active_factors(s, as_of=as_of))
    m = mats[rel_type]
    cells = [[ids[i], ids[j], round(float(m[i, j]), 3)]
             for i, j in zip(*m.nonzero())]
    return jsonify({'rel_type': rel_type, 'as_of': as_of, 'n': len(ids),
                    'nnz': len(cells), 'cells': cells})


@matrix_bp.post('/impact')
def matrix_impact():
    """Body: {shock: [ids], magnitude?, damping?, max_hops?, rel_weights?, as_of?}
    → {impacts: {id: pct}, cascade: [{id, hop, impact}], factors_active}."""
    scope = _db()
    if scope is None:
        return jsonify({'error': 'DATABASE_URL no configurada'}), 503
    from matrix.engine import active_factors, build_matrices, fragility, propagate
    body = request.get_json(silent=True) or {}
    shock = body.get('shock') or []
    if not shock or not isinstance(shock, list):
        return jsonify({'error': 'shock: lista de ids requerida'}), 400
    as_of = body.get('as_of')
    with scope() as s:
        mats, idx, ids = build_matrices(s, as_of=as_of)
        factors = active_factors(s, as_of=as_of)
        frag = fragility(idx, factors)
    unknown = [x for x in shock if x not in idx]
    if len(unknown) == len(shock):
        return jsonify({'error': f'ningún id del shock existe: {unknown[:5]}'}), 400
    impacts, cascade = propagate(
        mats, idx, ids, [x for x in shock if x in idx],
        magnitude=float(body.get('magnitude', 1.0)),
        damping=float(body.get('damping', 0.6)),
        max_hops=int(body.get('max_hops', 6)),
        rel_weights=body.get('rel_weights'), frag=frag,
    )
    return jsonify({'shock': shock, 'as_of': as_of,
                    'impacts': impacts, 'cascade': cascade,
                    'affected': len(impacts) - len(shock),
                    'factors_active': [f['label'] for f in factors],
                    'unknown_ids': unknown})


@matrix_bp.get('/metrics')
def matrix_metrics():
    scope = _db()
    if scope is None:
        return jsonify({'error': 'DATABASE_URL no configurada'}), 503
    from matrix.engine import compute_metrics
    with scope() as s:
        metrics, factors = compute_metrics(s, as_of=request.args.get('as_of'))
    top = sorted(metrics.items(), key=lambda kv: kv[1]['chokepoint_rank'])[:25]
    return jsonify({'nodes': len(metrics),
                    'factors_active': [f['label'] for f in factors],
                    'chokepoints_top25': [{'id': k, **v} for k, v in top],
                    'metrics': metrics})
