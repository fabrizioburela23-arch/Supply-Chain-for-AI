"""core/hotviews/api.py — /api/hot/* (INFRA_OPERATIVA §4.6; NUNCA /v1/*).

Toda respuesta lleva el sobre común `{"data": …, "view": {name, generation, graph_version, release,
built_at, age_ms, source, stale, lag_versions}}`, el ETag `"<vista>:<generación>"` (304 si no cambió) y la
cabecera `X-Khipu-Graph-Version`. Leer NUNCA reconstruye: si la vista va atrasada se dice (`stale`,
`lag_versions`); si todavía no existe ninguna (arranque), se espera hasta 2 s y si no, 503 `view_warming`.

    GET  /api/hot/status
    GET  /api/hot/impact/<id>?severity=0-100&kind=collapse|shock&top=50
    GET  /api/hot/chokepoints?by=sum|count&limit=25
    GET  /api/hot/factors
    POST /api/hot/scenario   {shocks:[{id, magnitude}]|[ids], factors:'active'|'none'|[ids], direction:'down',
                              damping?, max_hops?, top?}
"""
import math
import time

from flask import Blueprint, jsonify, request

from core.http import rate_limit

hot_bp = Blueprint('hot', __name__, url_prefix='/api/hot')

WARM_WAIT_S = 2.0
SHOCKS_CAP = 200
TOP_CAP = 500


def _gen():
    from core.hotviews import builder
    return builder.current(timeout=WARM_WAIT_S)


def _warming():
    r = jsonify({'error': 'Las vistas rápidas se están preparando (arranque); reintenta en unos segundos',
                 'error_en': 'Fast views are warming up (startup); retry in a few seconds',
                 'code': 'view_warming', 'retry_after': 3})
    r.headers['Retry-After'] = '3'
    return r, 503


def envelope(name, data, g, status=200, etag=True, extra=None):
    """Respuesta con el sobre `view` + ETag/304 + X-Khipu-Graph-Version."""
    from core.hotviews import registry
    meta = registry.meta(name, g)
    tag = f'"{name}:{g.id}"' if (etag and g is not None) else None
    if tag and request.method == 'GET' and request.headers.get('If-None-Match') == tag and not meta['stale']:
        resp = jsonify({})
        resp.status_code = 304
    else:
        body = {'data': data, 'view': meta}
        if extra:
            body.update(extra)
        resp = jsonify(body)
        resp.status_code = status
    if tag:
        resp.headers['ETag'] = tag
    if g is not None:
        resp.headers['X-Khipu-Graph-Version'] = str(g.graph_version)
    return resp


def _bad(key, es, en):
    return jsonify({'error': es, 'error_en': en, 'param': key}), 400


def _num(raw, default, lo, hi, key):
    if raw in (None, ''):
        return default, None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None, _bad(key, f'parámetro inválido: {key} (debe ser numérico)', f'invalid parameter: {key} (must be numeric)')
    if not math.isfinite(v):
        return None, _bad(key, f'parámetro inválido: {key}', f'invalid parameter: {key}')
    return max(lo, min(hi, v)), None


@hot_bp.get('/status')
@rate_limit(240, 60)
def hot_status():
    from core.hotviews import builder, registry, signals
    from core.hotviews.views import graph_core, impact
    g = registry.generation()
    if g is None:
        builder.request_build()
    data = {'warming': g is None, 'builder': builder.state(), 'signals': signals.stats(),
            'known': {k: v for k, v in signals.known().items() if k != 'ids'},
            'history': registry.history()[:10]}
    if g is not None:
        data.update({
            'generation': g.id, 'graph_version': g.graph_version, 'lineage': g.lineage, 'source': g.source,
            'release': g.release, 'release_label': g.release_label, 'built_at': g.built_at,
            'build_ms': g.build_ms, 'read_ms': g.read_ms,
            'views': {'graph_core': graph_core.status(g.views['graph_core']),
                      'impact': impact.status(g.views['impact'])},
            'snapshot': {k: g.extra.get(k) for k in ('snapshot_sha', 'exported_at')} if g.source == 'snapshot' else None,
        })
    return envelope('status', data, g, etag=False)


@hot_bp.get('/impact/<path:node_id>')
@rate_limit(240, 60)
def hot_impact(node_id):
    from core.hotviews.views import impact
    g = _gen()
    if g is None:
        return _warming()
    core, imp = g.views['graph_core'], g.views['impact']
    oid = core.resolve(node_id[:120])
    if oid is None:
        return jsonify({'error': f'id desconocido: {node_id[:120]}', 'error_en': f'unknown id: {node_id[:120]}',
                        'code': 'unknown_id'}), 404
    sev, bad = _num(request.args.get('severity'), 100.0, 0.0, 100.0, 'severity')
    if bad:
        return bad
    top, bad = _num(request.args.get('top'), 50, 1, TOP_CAP, 'top')
    if bad:
        return bad
    kind = (request.args.get('kind') or 'collapse').strip().lower()
    if kind not in ('collapse', 'shock'):
        return _bad('kind', "kind inválido: usa 'collapse' o 'shock'", "invalid kind: use 'collapse' or 'shock'")
    if kind == 'collapse' and sev >= 100.0:
        data = impact.impact_payload(core, imp, oid, top=int(top))
        return envelope('impact', data, g)
    # choque parcial: el MISMO kernel sobre las matrices de la vista (~1-2 ms), no precalculado
    import numpy as np
    x0 = np.zeros(len(core.ids))
    x0[core.idx[oid]] = sev / 100.0
    t0 = time.perf_counter()
    sc = impact.scenario(core, x0, top=int(top))
    data = {'id': oid, 'label': core.label(oid), 'severity': sev, 'kind': kind, 'affected': sc['affected'],
            'reach_1': sc['reach_1'], 'reach_10': sc['reach_10'], 'sum_impact': sc['sum_impact'],
            'by_hop': sc['by_hop'], 'victims': sc['victims'], 'precomputed': False,
            'compute_ms': round((time.perf_counter() - t0) * 1000, 3)}
    return envelope('impact', data, g)


@hot_bp.get('/chokepoints')
@rate_limit(240, 60)
def hot_chokepoints():
    from core.hotviews.views import impact
    g = _gen()
    if g is None:
        return _warming()
    by = (request.args.get('by') or 'sum').strip().lower()
    if by not in ('sum', 'count'):
        return _bad('by', "by inválido: usa 'sum' o 'count'", "invalid by: use 'sum' or 'count'")
    limit, bad = _num(request.args.get('limit'), 25, 1, 200, 'limit')
    if bad:
        return bad
    return envelope('impact', impact.chokepoints_payload(g.views['graph_core'], g.views['impact'], by, int(limit)), g)


@hot_bp.get('/factors')
@rate_limit(240, 60)
def hot_factors():
    from core.hotviews.views import graph_core
    g = _gen()
    if g is None:
        return _warming()
    core = g.views['graph_core']
    data = {'factors': graph_core.factors_payload(core), 'count': len(core.factors),
            'rho': (core.rho or {}).get('rho'), 'damping_rho': (core.rho or {}).get('damping_rho'),
            'stable': (core.rho or {}).get('stable')}
    return envelope('graph_core', data, g)


@hot_bp.post('/scenario')
@rate_limit(60, 300)
def hot_scenario():
    """Varias fuentes con su magnitud, con el MISMO kernel (propagate_block). Nunca escribe nada."""
    import numpy as np

    from core.hotviews.views import impact
    g = _gen()
    if g is None:
        return _warming()
    core = g.views['graph_core']
    body = request.get_json(silent=True) or {}
    if not isinstance(body, dict):
        body = {}
    direction = str(body.get('direction') or 'down').lower()
    if direction != 'down':
        return _bad('direction', "direction 'up' todavía no está disponible (bloque 1, paso 12 del plan)",
                    "direction 'up' is not available yet (block 1, step 12 of the plan)")
    raw = body.get('shocks')
    if not isinstance(raw, list) or not raw:
        return _bad('shocks', 'shocks: lista de ids o de {id, magnitude} requerida',
                    'shocks: list of ids or {id, magnitude} required')
    x0 = np.zeros(len(core.ids))
    unknown, used = [], []
    for it in raw[:SHOCKS_CAP]:
        if isinstance(it, str):
            sid, mag = it, 1.0
        elif isinstance(it, dict):
            sid = it.get('id')
            mag, bad = _num(it.get('magnitude'), 1.0, 0.0, 1.0, 'magnitude')
            if bad:
                return bad
        else:
            continue
        oid = core.resolve(str(sid or '')[:120])
        if oid is None:
            unknown.append(str(sid)[:120])
            continue
        x0[core.idx[oid]] = max(x0[core.idx[oid]], mag)
        used.append({'id': oid, 'magnitude': mag})
    if not used:
        return jsonify({'error': 'ningún id del escenario existe', 'error_en': 'no scenario id exists',
                        'unknown_ids': unknown[:20]}), 400
    factors = body.get('factors', 'active')
    if not (factors in ('active', 'none') or (isinstance(factors, list) and all(isinstance(x, str) for x in factors))):
        return _bad('factors', "factors: 'active', 'none' o lista de ids", "factors: 'active', 'none' or a list of ids")
    damping, bad = _num(body.get('damping'), 0.6, 0.0, 0.95, 'damping')
    if bad:
        return bad
    hops, bad = _num(body.get('max_hops'), 6, 1, 12, 'max_hops')
    if bad:
        return bad
    top, bad = _num(body.get('top'), 50, 1, TOP_CAP, 'top')
    if bad:
        return bad
    t0 = time.perf_counter()
    sc = impact.scenario(core, x0, factors=factors, damping=damping, max_hops=int(hops), top=int(top))
    if not body.get('full'):
        sc.pop('impacts', None)            # el vector completo solo si se pide (full: true)
    data = {'shocks': used, 'unknown_ids': unknown, 'factors': factors, 'direction': direction,
            'params': {'damping': damping, 'max_hops': int(hops), 'threshold': 0.01},
            'compute_ms': round((time.perf_counter() - t0) * 1000, 3), **sc}
    return envelope('impact', data, g, etag=False)
