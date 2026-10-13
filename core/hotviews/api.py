"""core/hotviews/api.py — /api/hot/* (INFRA_OPERATIVA §4.6; NUNCA /v1/*).

Toda respuesta lleva el sobre común `{"data": …, "view": {name, generation, graph_version, release,
built_at, age_ms, source, stale, lag_versions}}`, el ETag `"<vista>:<generación>"` (304 si no cambió) y la
cabecera `X-Khipu-Graph-Version`. Leer NUNCA reconstruye: si la vista va atrasada se dice (`stale`,
`lag_versions`); si todavía no existe ninguna (arranque), se espera hasta 2 s y si no, 503 `view_warming`.

    GET  /api/hot/status
    GET  /api/hot/impact/<id>?severity=0-100&kind=collapse|shock&top=50[&as_of=…&known_at=…]   (paso 23: G(t, κ))
    GET  /api/hot/chokepoints?by=sum|count&limit=25
    GET  /api/hot/factors
    GET  /api/hot/card/<id>?lang=es|en&structure=1   tarjeta V3 (NRS + 5 términos, flujo en pares distintos, estructura)
    GET  /api/hot/nrs?ids=a,b[&terms=1]              vector NRS (todas sin ids) — LA fórmula, una vez por generación
    GET  /api/hot/geo?ids=a,b                        V6 GeoRisk: ≤3 hechos vivos por empresa (versión del mundo)
    GET  /api/hot/quote?symbols=NVDA,TSM             V4 cotización con sello {src, as_of, age_s, live, stale}
    POST /api/hot/scenario   {shocks:[{id, magnitude}]|[ids], factors:'active'|'none'|[ids], direction:'down',
                              damping?, max_hops?, top?}
"""
import math
import time

from flask import Blueprint, jsonify, request

from core.http import rate_limit


def _kdef(name):
    """Valor por defecto del kernel (kernel.params del release vigente, paso 9) — import perezoso del motor."""
    from matrix import engine as _E
    return getattr(_E, name)

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


def envelope(name, data, g, status=200, etag=True, extra=None, etag_extra=None):
    """Respuesta con el sobre `view` + ETag/304 + X-Khipu-Graph-Version. `etag_extra`: lo que ADEMÁS de la
    generación define el contenido (p. ej. la versión de los fundamentales en vivo del NRS)."""
    from core.hotviews import registry
    meta = registry.meta(name, g)
    tag = f'"{name}:{g.id}{(":" + str(etag_extra)) if etag_extra is not None else ""}"' if (etag and g is not None) else None
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
    from core.hotviews import builder, hot, registry, signals
    from core.hotviews.views import graph as graph_view
    from core.hotviews.views import graph_core, impact
    g = registry.generation()
    if g is None:
        builder.request_build()
    from core.hotviews import derived
    from core.hotviews.views import alerts as _alerts
    from core.hotviews.views import geo as _geo
    from core.hotviews.views import quote as _quote
    data = {'warming': g is None, 'builder': builder.state(), 'signals': signals.stats(),
            'derived': derived.stats(), 'geo': _geo.status(), 'quote': _quote.stats(), 'alerts': _alerts.stats(),
            'known': {k: v for k, v in signals.known().items() if k != 'ids'},
            'history': registry.history()[:10], 'readers': hot.status(), 'asof': _asof_stats()}
    if g is not None:
        data.update({
            'generation': g.id, 'graph_version': g.graph_version, 'lineage': g.lineage, 'source': g.source,
            'release': g.release, 'release_label': g.release_label, 'built_at': g.built_at,
            'build_ms': g.build_ms, 'read_ms': g.read_ms,
            'views': {'graph_core': graph_core.status(g.views['graph_core']),
                      'impact': impact.status(g.views['impact']),
                      'graph': graph_view.status(g.views.get('graph')),
                      'card': _card_status(g)},
            'snapshot': {k: g.extra.get(k) for k in ('snapshot_sha', 'exported_at')} if g.source == 'snapshot' else None,
        })
    return envelope('status', data, g, etag=False)


def _asof_stats():
    from core.hotviews.views import asof
    return asof.stats()


def _card_status(g):
    from core.hotviews import derived
    from core.hotviews.views import card
    return card.status(derived.peek(g, 'card'))


def _asof_gen():
    """Paso 23 (V7 AsOf): ?as_of= y/o ?known_at= → (Generation G(t, κ), meta, None) o (None, None, respuesta de
    error). Sin ninguno de los dos → (None, None, None): el camino vivo de siempre."""
    as_of, known_at = request.args.get('as_of') or None, request.args.get('known_at') or None
    if as_of is None and known_at is None:
        return None, None, None
    from core.hotviews.views import asof
    from ontology.bitemporal import KnownAtError
    from ontology.service import OntologyError
    try:
        g, meta = asof.get(as_of, known_at)
    except KnownAtError as e:
        return None, None, (jsonify({'error': e.es, 'error_en': e.en, 'param': 'known_at'}), 400)
    except OntologyError as e:
        return None, None, _bad('as_of', f'as_of inválido: {e}', 'invalid as_of (use YYYY-MM-DD or ISO 8601)')
    except asof.AsOfUnavailable:
        return None, None, (jsonify({'error': 'la historia (as_of/known_at) necesita la base de datos',
                                     'error_en': 'history (as_of/known_at) needs the database',
                                     'code': 'asof_unavailable'}), 503)
    except asof.AsOfBusy:
        r = jsonify({'error': 'la vista histórica está ocupada; reintenta en unos segundos',
                     'error_en': 'the historical view is busy; retry in a few seconds', 'code': 'asof_busy',
                     'retry_after': 5})
        r.headers['Retry-After'] = '5'
        return None, None, (r, 503)
    return g, meta, None


def _asof_envelope(name, data, g, meta):
    from core.hotviews.views import asof
    r = jsonify({'data': data, 'view': asof.view_meta(g, meta, name=name)})
    r.headers['X-Khipu-Graph-Version'] = str(g.graph_version)
    return r


@hot_bp.get('/impact/<path:node_id>')
@rate_limit(240, 60)
def hot_impact(node_id):
    """?as_of=&known_at= (paso 23, opcionales): el mismo impacto sobre G(t, κ) (vista AsOf, LRU de 16)."""
    from core.hotviews.views import impact
    g, ameta, err = _asof_gen()
    if err is not None:
        return err
    if g is None:
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
        return _asof_envelope('impact', data, g, ameta) if ameta is not None else envelope('impact', data, g)
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
    return _asof_envelope('impact', data, g, ameta) if ameta is not None else envelope('impact', data, g)


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
    from matrix import engine as _E
    if direction not in ('down', 'up') or (direction == 'up' and not _E.direction_up_enabled()):
        # 'up' (auge de demanda, PROP-17) lo calcula el kernel desde kernel.params 2.0.0 (activación con PIN)
        return _bad('direction', "direction 'up' todavía no está disponible (paso 12: llega con kernel.params 2.0.0 "
                                 'cuando Fabrizio lo active con su PIN, 🩺 → Gobernanza)',
                    "direction 'up' is not available yet (step 12: it comes with kernel.params 2.0.0 once Fabrizio "
                    'activates it with his PIN, 🩺 → Governance)')
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
    damping, bad = _num(body.get('damping'), _kdef('DAMPING'), 0.0, 0.95, 'damping')
    if bad:
        return bad
    hops, bad = _num(body.get('max_hops'), _kdef('MAX_HOPS'), 1, 12, 'max_hops')
    if bad:
        return bad
    top, bad = _num(body.get('top'), 50, 1, TOP_CAP, 'top')
    if bad:
        return bad
    t0 = time.perf_counter()
    sc = impact.scenario(core, x0, factors=factors, damping=damping, max_hops=int(hops), top=int(top),
                         direction=direction)
    try:   # paso 20: ficha whatif.shock (async, 0 ms al usuario) con lo pedido y la generación usada
        from matrix.api import ledger_whatif
        ledger_whatif('whatif.shock', {'shock': [u['id'] for u in used], 'shocks': used, 'factors': factors,
                                       'direction': direction, 'damping': damping, 'max_hops': int(hops),
                                       'endpoint': '/api/hot/scenario'},
                      sc.get('impacts') or {}, g, {'affected': sc.get('affected')})
    except Exception:  # noqa: BLE001
        pass
    if not body.get('full'):
        sc.pop('impacts', None)            # el vector completo solo si se pide (full: true)
    data = {'shocks': used, 'unknown_ids': unknown, 'factors': factors, 'direction': direction,
            'params': {'damping': damping, 'max_hops': int(hops), 'threshold': _kdef('THRESHOLD')},
            'compute_ms': round((time.perf_counter() - t0) * 1000, 3), **sc}
    return envelope('impact', data, g, etag=False)


# ── paso 14: V3 Card + NRS, V6 GeoRisk, V4 Quote con sello ─────────────────────────────────────────────────────
def _reader_gen():
    """La generación del grafo de los LECTORES (la publicada; si todavía no sirve, la privada del snapshot) —
    la misma que leen el MCP, el chat y el World Monitor."""
    from core.hotviews import hot
    gv = hot.graph(timeout=WARM_WAIT_S)
    return gv.generation_obj if gv is not None else None


def _ids_arg(raw, cap=1000):
    out = []
    for x in str(raw or '').split(','):
        x = x.strip()[:120]
        if x and x not in out:
            out.append(x)
    return out[:cap]


@hot_bp.get('/card/<path:node_id>')
@rate_limit(240, 60)
def hot_card(node_id):
    from core.hotviews.views import card
    g = _reader_gen()
    if g is None:
        return _warming()
    cv = card.view(g)
    oid = cv.resolve(node_id[:120])
    if oid is None:
        return jsonify({'error': f'empresa desconocida: {node_id[:120]}', 'error_en': f'unknown company: {node_id[:120]}',
                        'code': 'unknown_id'}), 404
    lang = 'en' if (request.args.get('lang') or '').lower().startswith('en') else 'es'
    want_struct = (request.args.get('structure') or '1') not in ('0', 'false', 'no')
    t0 = time.perf_counter()
    data = cv.card(oid, lang=lang, structure=want_struct)
    data['compute_ms'] = round((time.perf_counter() - t0) * 1000, 3)
    caps = ((data.get('structure') or {}).get('caps_as_of')) if want_struct else None
    return envelope('card', data, g, etag_extra=f'{lang}.{int(want_struct)}.f{cv.nrs_version()}.{caps}')


@hot_bp.get('/nrs')
@rate_limit(240, 60)
def hot_nrs():
    from core.hotviews.views import card
    g = _reader_gen()
    if g is None:
        return _warming()
    cv = card.view(g)
    allv = cv.nrs_all()
    ids = _ids_arg(request.args.get('ids'))
    terms = (request.args.get('terms') or '') in ('1', 'true', 'yes')
    if ids:
        resolved = {i: cv.resolve(i) for i in ids}
        unknown = [i for i, r in resolved.items() if r is None]
        pick = {i: r for i, r in resolved.items() if r is not None}
    else:
        unknown, pick = [], {k: k for k in allv}
    vals = {i: allv[r]['total'] for i, r in pick.items() if r in allv}
    data = {'values': vals, 'n': len(vals), 'unknown_ids': unknown, 'fund_version': cv.nrs_version(),
            'method': 'core.world.nrs_terms (= app computeNRS) · structural flow degree, distinct pairs'}
    if terms:
        data['terms'] = {i: {k: allv[r][k] for k in ('geo', 'chain', 'market', 'fundamental', 'concentration', 'degree')}
                         for i, r in pick.items() if r in allv}
    return envelope('card', data, g, etag_extra=f'nrs.f{cv.nrs_version()}.{len(ids)}.{int(terms)}' if not ids else None,
                    etag=not ids)


@hot_bp.get('/geo')
@rate_limit(120, 60)
def hot_geo():
    from core.hotviews.views import geo
    g = _reader_gen()
    ids = _ids_arg(request.args.get('ids'), cap=50)
    if not ids:
        return _bad('ids', 'ids: lista de empresas separadas por coma', 'ids: comma-separated list of companies')
    facts, wv = geo.facts(ids, wait=0)
    data = {'facts': facts, 'world_version': wv, 'max_per_entity': 3,
            'source': 'Khipus World Monitor (official + live layers, cached; never forces downloads)'}
    resp = envelope('geo', data, g, etag=False)
    return resp


@hot_bp.get('/quote')
@rate_limit(120, 60)
def hot_quote():
    from core.hotviews.views import quote
    syms = _ids_arg(request.args.get('symbols'), cap=150)
    if not syms:
        return _bad('symbols', 'symbols: lista de tickers separados por coma', 'symbols: comma-separated tickers')
    t0 = time.perf_counter()
    q = quote.stamped(syms)
    r = jsonify({'data': {'quotes': q, 'n': len(q), 'missing': [s for s in syms if s.upper() not in q and s not in q],
                          'stale_after_s': quote.STALE_AFTER_S,
                          'compute_ms': round((time.perf_counter() - t0) * 1000, 2)},
                 'view': {'name': 'quote', 'live': True, 'generation': None,
                          'note': 'live view: each quote carries its own stamp (src, as_of, age_s)'}})
    r.headers['Cache-Control'] = 'no-store'
    return r
