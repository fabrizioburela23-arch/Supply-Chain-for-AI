"""core/hotviews/api.py — /api/hot/* (INFRA_OPERATIVA §4.6; NUNCA /v1/*).

Toda respuesta lleva el sobre común `{"data": …, "view": {name, generation, graph_version, release,
built_at, age_ms, source, stale, lag_versions}}`, el ETag `"<vista>:<generación>"` (304 si no cambió) y la
cabecera `X-Khipu-Graph-Version`. Leer NUNCA reconstruye: si la vista va atrasada se dice (`stale`,
`lag_versions`); si todavía no existe ninguna (arranque), se espera hasta 2 s y si no, 503 `view_warming`.

    GET  /api/hot/status
    GET  /api/hot/impact/<id>?severity=0-100&kind=collapse|shock&top=50[&as_of=…&known_at=…]   (paso 23: G(t, κ))
    GET  /api/hot/chokepoints?by=sum|count&limit=25
    GET  /api/hot/factors[?limit=&offset=&fields=id,label,…]   sin parámetros = TODOS (como siempre); con ellos,
                              una página + total/limit/offset (E1.7: 414 KB a 5k empresas)
    GET  /api/hot/card/<id>?lang=es|en&structure=1   tarjeta V3 (NRS + 5 términos, flujo en pares distintos, estructura)
    GET  /api/hot/nrs?ids=a,b[&terms=1]              vector NRS (todas sin ids) — LA fórmula, una vez por generación;
                                                      lote: ids separados por coma (o repetidos), hasta 250
                                                      (línea de pedido de gunicorn; hotclient parte en 200)
    GET  /api/hot/geo?ids=a,b                        V6 GeoRisk: ≤3 hechos vivos por empresa (versión del mundo)
    GET  /api/hot/quote?symbols=NVDA,TSM             V4 cotización con sello {src, as_of, age_s, live, stale}
    POST /api/hot/scenario   {shocks:[{id, magnitude}]|[ids], factors:'active'|'none'|[ids], direction:'down',
                              damping?, max_hops?, top?}
    POST /api/hot/scenario_pnl {shocks, positions:[{id|symbol, usd}], factors?, record?}  escenario → dinero con el κ
                              calibrado (kernel.calibration); calibración débil/ausente → sin cifra (batch I3)
    GET  /api/hot/catalog[?offset=&limit=&gen=]      E3.1 (lote L): lo que el grafo de los LECTORES tiene y el catálogo
                              estático del navegador (data/grafo_v0.json = nodes/*.js) NO: empresas solo en Postgres
                              (importadas) y vínculos nuevos, en columnas compactas; ETag = generación; paginado
                              (primero nodos, luego vínculos). engine/catalog_sync.js lo AÑADE al mapa (nunca pisa).
    GET  /api/hot/catalog/detail?ids=a,b             textos (rol, suministra, foso, crecimiento…) de esas empresas
                              nuevas y el texto de los vínculos nuevos que las tocan — a pedido (al abrir la ficha)
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


FACTOR_FIELDS = ('id', 'label', 'severity', 'severity_crisis', 'rationale', 'since', 'updated', 'members',
                 'members_fragility')
FACTORS_PAGE_CAP = 1000


def _int_arg(key, lo, hi):
    """(valor, None) · (None, None) si no vino · (None, respuesta 400 bilingüe) si no es un entero en [lo, hi]."""
    raw = request.args.get(key)
    if raw in (None, ''):
        return None, None
    try:
        v = int(str(raw).strip())
    except (TypeError, ValueError):
        return None, _bad(key, f'parámetro inválido: {key} (entero de {lo} a {hi})',
                          f'invalid parameter: {key} (integer from {lo} to {hi})')
    if v < lo or v > hi:
        return None, _bad(key, f'parámetro fuera de rango: {key} (de {lo} a {hi})',
                          f'parameter out of range: {key} (from {lo} to {hi})')
    return v, None


@hot_bp.get('/factors')
@rate_limit(240, 60)
def hot_factors():
    """Sin parámetros: la lista COMPLETA (forma de siempre). `limit`/`offset` (E1.7): una página, en el orden de la
    vista, con `total`/`limit`/`offset`; `fields`: solo esos campos de cada factor (`id` siempre va)."""
    from core.hotviews.views import graph_core
    g = _gen()
    if g is None:
        return _warming()
    core = g.views['graph_core']
    limit, bad = _int_arg('limit', 1, FACTORS_PAGE_CAP)
    if bad:
        return bad
    offset, bad = _int_arg('offset', 0, 10 ** 7)
    if bad:
        return bad
    fields = None
    if request.args.get('fields'):
        fields = _ids_arg(request.args.get('fields'), cap=50)
        unknown = [f for f in fields if f not in FACTOR_FIELDS]
        if unknown or not fields:
            return _bad('fields', f"fields inválido: {', '.join(unknown) or '—'} (usa {', '.join(FACTOR_FIELDS)})",
                        f"invalid fields: {', '.join(unknown) or '—'} (use {', '.join(FACTOR_FIELDS)})")
    paged = limit is not None or offset is not None
    items = graph_core.factors_payload(core)          # la MISMA lista (y orden) de siempre; la página es un corte
    if paged:
        off = offset or 0
        items = items[off:off + limit] if limit is not None else items[off:]
    if fields is not None:
        keep = ['id'] + [f for f in fields if f != 'id']
        items = [{k: it.get(k) for k in keep} for it in items]
    data = {'factors': items, 'count': len(core.factors),
            'rho': (core.rho or {}).get('rho'), 'damping_rho': (core.rho or {}).get('damping_rho'),
            'stable': (core.rho or {}).get('stable')}
    extra = None
    if paged:
        data.update(total=len(core.factors), limit=limit, offset=offset or 0)
        extra = f'p{offset or 0}.{limit if limit is not None else "all"}'
    if fields is not None:
        extra = f"{extra or 'pall'}.f{'+'.join(fields)}"
    return envelope('graph_core', data, g, etag_extra=extra)


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


POSITIONS_CAP = 100


@hot_bp.post('/scenario_pnl')
@rate_limit(60, 300)
def hot_scenario_pnl():
    """Escenario → DINERO de una cartera (batch I3, L2-13): el MISMO kernel que /scenario siembra el golpe y
    core/scenario_pnl traduce el impacto con el κ CALIBRADO de kernel.calibration (nunca se ajusta aquí). Si la
    calibración es débil, falta o es de otro motor, `pnl.status` lo dice y NO hay cifra.
    {shocks:[{id, magnitude}]|[ids], positions:[{id|symbol, usd}], factors:'active'|'none', record?:bool}"""
    import numpy as np

    from core import scenario_pnl as SP
    from core.hotviews.views import impact
    g = _gen()
    if g is None:
        return _warming()
    core = g.views['graph_core']
    body = request.get_json(silent=True) or {}
    if not isinstance(body, dict):
        body = {}
    raw = body.get('shocks')
    if not isinstance(raw, list) or not raw:
        return _bad('shocks', 'shocks: lista de ids o de {id, magnitude} requerida',
                    'shocks: list of ids or {id, magnitude} required')
    pos_raw = body.get('positions')
    if not isinstance(pos_raw, list):
        return _bad('positions', 'positions: lista de {id|symbol, usd} requerida',
                    'positions: list of {id|symbol, usd} required')
    x0 = np.zeros(len(core.ids))
    used, unknown = [], []
    for it in raw[:SHOCKS_CAP]:
        sid, mag = (it, 1.0) if isinstance(it, str) else ((it.get('id'), it.get('magnitude')) if isinstance(it, dict)
                                                          else (None, None))
        mag, bad = _num(mag, 1.0, 0.0, 1.0, 'magnitude')
        if bad:
            return bad
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
    if factors not in ('active', 'none'):
        return _bad('factors', "factors: 'active' o 'none'", "factors: 'active' or 'none'")
    tickers = _ticker_map_now()
    positions = []
    for p in pos_raw[:POSITIONS_CAP]:
        if not isinstance(p, dict):
            continue
        usd, bad = _num(p.get('usd'), 0.0, 0.0, 1e12, 'usd')
        if bad:
            return bad
        sym = str(p.get('symbol') or '').strip().upper()[:40] or None
        oid = core.resolve(str(p.get('id') or '')[:120]) if p.get('id') else None
        if oid is None and sym:
            oid = tickers.get(sym.replace('/', '')) or core.resolve(sym)
        positions.append({'id': oid, 'symbol': sym or p.get('id'), 'usd': usd})
    t0 = time.perf_counter()
    sc = impact.scenario(core, x0, factors=factors, top=1)
    pnl = SP.translate(sc.get('impacts') or {}, positions)
    ms = round((time.perf_counter() - t0) * 1000, 3)
    if body.get('record', True) is not False:
        try:   # ficha whatif.shock (async): lo pedido, la generación y la versión de κ (sin montos por posición)
            from matrix.api import ledger_whatif
            ledger_whatif('whatif.shock', {'shock': [u['id'] for u in used], 'shocks': used, 'factors': factors,
                                           'direction': 'down', 'endpoint': '/api/hot/scenario_pnl',
                                           'positions_n': len(positions)},
                          sc.get('impacts') or {}, g, {'affected': sc.get('affected'),
                                                      'pnl': {k: pnl.get(k) for k in ('status', 'pnl_usd', 'band_usd')},
                                                      'calibration': (pnl.get('calibration') or {}).get('artifact')})
        except Exception:  # noqa: BLE001
            pass
    data = {'shocks': used, 'unknown_ids': unknown, 'factors': factors, 'affected': sc.get('affected'),
            'pnl': pnl, 'compute_ms': ms}
    return envelope('impact', data, g, etag=False)


def _ticker_map_now():
    """{TICKER: id} de la generación de lectores YA publicada (nunca espera ni construye)."""
    try:
        from core.hotviews import hot
        from core.hotviews.views.account import _ticker_map
        v = hot.graph(wait=False)
        return hot.cached('account.ticker_map', _ticker_map, view=v) if v is not None else {}
    except Exception:  # noqa: BLE001
        return {}


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
    # la etiqueta lleva la versión de fundamentales que USÓ el cuerpo (la ficha puede calcular solo su NRS sin
    # rehacer el vector: cv.nrs_version() quedaría vieja → 304 con un NRS viejo)
    fv = (data.get('nrs') or {}).get('fund_version')
    if fv is None:
        from core import live_fundamentals as lf
        fv = lf.version()
    return envelope('card', data, g, etag_extra=f'{lang}.{int(want_struct)}.f{fv}.{caps}')


NRS_IDS_CAP = 250          # ~3.100 caracteres de ids reales: cabe en la línea de pedido de gunicorn (4.094)


@hot_bp.get('/nrs')
@rate_limit(240, 60)
def hot_nrs():
    from core.hotviews.views import card
    g = _reader_gen()
    if g is None:
        return _warming()
    cv = card.view(g)
    allv = cv.nrs_all()
    # lote: ids=a,b,c o ids=a&ids=b (los dos juntos también); tope NRS_IDS_CAP: con más, la línea del pedido pasa
    # el límite de gunicorn (4.094 caracteres → 400 en HTML). engine/hotclient.js parte el lote en trozos de 200
    ids = _ids_arg(','.join(request.args.getlist('ids')), cap=NRS_IDS_CAP)
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
    if ids:   # el lote también revalida (304): la etiqueta lleva la huella de los ids pedidos
        import hashlib
        tag = hashlib.sha1('\x1f'.join(ids).encode('utf-8')).hexdigest()[:12]
        return envelope('card', data, g, etag_extra=f'nrs.f{cv.nrs_version()}.i{tag}.{int(terms)}')
    return envelope('card', data, g, etag_extra=f'nrs.f{cv.nrs_version()}.0.{int(terms)}')


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


# ── E3.1 (lote L, 2026-10-15): el catálogo del navegador se COMPLETA con lo que solo está en Postgres ────────────
# El navegador arma NODES/LINKS con el catálogo estático (nodes/*.js; su exportación es data/grafo_v0.json): una
# empresa que solo existe en la base (importada con el importador, IncorporarEmpresa) no salía en el mapa, la
# búsqueda ni las listas. Esta ruta da la DIFERENCIA entre el grafo de los lectores (hot.graph(), la misma
# generación que el MCP, el chat y el NRS del servidor) y ese catálogo: solo AÑADE — un nodo o vínculo que el
# catálogo ya tiene nunca se repite ni se pisa (un vínculo es la clave (origen, destino, tipo), como en el merge).
CATALOG_NODE_FIELDS = ('id', 'label', 'cat', 'sector', 'country', 'country_iso2', 'ticker', 'mkt', 'status', 'preipo',
                       'margin', 'gflag')
CATALOG_NAMES_PER_NODE = 3         # nombres alternativos por empresa para la búsqueda del navegador (KhipuResolve)
CATALOG_LINK_FIELDS = ('source', 'target', 'w', 'type', 'conf', 'verified', 'since')
CATALOG_PAGE_DEFAULT = 5000        # elementos (nodos + vínculos) por página: el lote de 386 cabe en una
CATALOG_PAGE_CAP = 20000
CATALOG_DETAIL_IDS_CAP = 100
DETAIL_TEXT_FIELDS = ('role', 'role_en', 'supplies', 'supplies_en', 'moat', 'moat_en', 'growth', 'growth_en', 'desc',
                      'desc_en', 'geo_risk', 'geo_risk_en', 'capex_2026', 'capex_2026_en', 'backlog_status',
                      'backlog_status_en', 'legal_name', 'website', 'hq_city', 'founded', 'employees', 'verified')
_STATIC_CAT = [None]               # (sha, ids, alias_keys, link_keys) del catálogo estático, una vez por archivo


def _static_catalog():
    """El catálogo estático que el navegador ya trae (ids canónicos, ids alias y claves de vínculo) — leído por
    core/hotviews/source (la única que abre el archivo), una vez por versión."""
    from core.hotviews import source
    snap, sha = source._snapshot_parsed()
    hit = _STATIC_CAT[0]
    if hit is not None and hit[0] == sha:
        return hit
    ids = frozenset(n['id'] for n in snap.get('nodes') or [] if n.get('id'))
    alias = frozenset((snap.get('node_id_alias') or {}).keys())
    lkeys = frozenset((l.get('source'), l.get('target'), l.get('type') or 'supply') for l in snap.get('links') or [])
    hit = (sha, ids, alias, lkeys)
    _STATIC_CAT[0] = hit
    return hit


def _searchable(name):
    """¿La búsqueda del navegador (engine/resolve.js `norm`: sin tildes, solo a-z0-9) puede usar este nombre? Uno en
    otra escritura («(주)엘지화학», «LG화학») queda vacío o reducido a «lg» allí — una clave corta que robaría la
    búsqueda de otras empresas —: no se manda (el MCP y el chat lo resuelven en el servidor). Hace falta que la
    mayoría de sus letras sean latinas y que la forma normalizada tenga ≥ 4 caracteres."""
    import re
    import unicodedata
    folded = ''.join(ch for ch in unicodedata.normalize('NFD', str(name or '').lower())
                     if unicodedata.category(ch) != 'Mn')
    letters = [ch for ch in folded if ch.isalnum()]
    latin = [ch for ch in letters if ('a' <= ch <= 'z') or ('0' <= ch <= '9')]
    normed = re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9\s]', ' ', folded)).strip()
    return bool(letters) and len(latin) * 2 >= len(letters) and len(normed) >= 4


def _gflag(growth):
    """La señal del crecimiento que usa el NRS (core/world.nrs_terms: 🔴 manda sobre 🟡) — sin mandar el texto."""
    g = str(growth or '').lower()
    return 'r' if '🔴' in g else ('y' if '🟡' in g else None)


def _num_or_none(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _link_trust(l):
    """conf/verified EFECTIVOS como los usa el kernel (matrix.engine.link_confidence): lo guardado manda; sin dato,
    el texto curado decide (vocabulary.text_says_unverified, la gemela de nodes/merge_graph.js linkTrust)."""
    from ontology import vocabulary as vocab
    conf, ver = _num_or_none(l.get('conf')), l.get('verified')
    if conf is None:
        unv = vocab.text_says_unverified(l.get('rel') or '')
        conf = vocab.UNVERIFIED_CONF if unv else 1.0
        if ver is None:
            ver = not unv
    conf = max(0.0, min(1.0, conf))
    if ver is None:
        ver = conf >= 1
    return conf, bool(ver)


def _valuation_usd(n, min_conf):
    """Valuación VERIFICADA de una privada (última ronda cerrada que trae la ficha, con fuente) en miles de millones de
    USD — la que dimensiona el nodo como en nodes/private_valuations.js. Otra moneda o confianza baja → None (el
    navegador no convierte: sin dato, el nodo sale con el tamaño mínimo fijo marcado «sin capitalización»)."""
    val = n.get('valuation')
    if not isinstance(val, dict) or str(val.get('currency') or 'USD').upper() != 'USD':
        return None
    v, c = _num_or_none(val.get('value')), _num_or_none(val.get('confidence'))
    if v is None or v <= 0 or not str(val.get('source_url') or '').startswith('http'):
        return None
    if c is not None and c < min_conf:
        return None
    return {'usd_b': round(v / 1e9, 3), 'as_of': str(val.get('as_of') or ''), 'round': val.get('round'),
            'source_url': val.get('source_url'), 'confidence': c}


def _catalog_delta(v, st):
    """La diferencia (UNA vez por generación y versión del catálogo; hot.cached)."""
    from core import governance as gov
    from ontology import vocabulary as vocab
    t0 = time.perf_counter()
    sha, ids, alias_keys, lkeys = st
    try:
        min_conf = float(gov.param('policy.import', 'live_min_confidence'))
    except Exception:  # noqa: BLE001 — sin política: la regla de siempre del importador
        min_conf = 0.5
    nodes, delta_ids, skipped_alias, vals, names, name_owner = [], set(), [], {}, {}, {}
    for n in v.nodes:
        nid = n.get('id')
        if not nid or nid in ids:
            continue
        if nid in alias_keys:          # el navegador ya lleva ese id a un nodo del catálogo: nunca un 2.º nodo
            skipped_alias.append(nid)
            continue
        delta_ids.add(nid)
        tk = n.get('ticker')
        row = {'id': nid, 'label': str(n.get('label') or nid), 'cat': n.get('cat') or None,
               'sector': n.get('sector') or None, 'country': n.get('country') or None,
               'country_iso2': n.get('country_iso2') or None, 'ticker': tk if isinstance(tk, str) else '',
               'mkt': (str(n.get('mkt')).strip() or None) if n.get('mkt') and not n.get('preipo') else None,
               'status': n.get('status') or None, 'preipo': 1 if n.get('preipo') else 0,
               'margin': _num_or_none(n.get('margin')), 'gflag': _gflag(n.get('growth'))}
        nodes.append([row[k] for k in CATALOG_NODE_FIELDS])
        val = _valuation_usd(n, min_conf)
        if val is not None:
            vals[nid] = val
        label_l, kept = row['label'].strip().lower(), 0
        for nm in [n.get('legal_name')] + list(n.get('aliases') or []):
            nm = str(nm or '').strip()[:120]
            key = nm.lower()
            # «ABB Ltd» para «ABB»: la búsqueda ya la encuentra por la etiqueta (ahorra bytes, no cambia resultados)
            if (not nm or key == label_l or key.startswith(label_l + ' ') or kept >= CATALOG_NAMES_PER_NODE
                    or not _searchable(nm)):
                continue
            kept += 1
            if key in name_owner and name_owner[key] != nid:
                name_owner[key] = None          # dos empresas reclaman el nombre: no se resuelve por él
            elif key not in name_owner:
                name_owner[key] = nid
                names[nm] = nid
    names = {nm: i for nm, i in names.items() if name_owner.get(nm.lower()) == i}
    links, reader_keys = [], set()
    for l in v.links:
        k = (l.get('source'), l.get('target'), l.get('type') or 'supply')
        reader_keys.add(k)
        if k in lkeys:
            continue
        conf, ver = _link_trust(l)
        links.append([k[0], k[1], _num_or_none(l.get('w')), k[2], conf, ver, l.get('since') or None])
    aliases = {}
    for a in sorted(v.alias):
        if a in alias_keys or a in ids or a in v.by_id:
            continue
        c = v.canonical(a)
        if c in v.by_id and c != a:
            aliases[a] = c
    flow = set(vocab.flow_relation_types())
    stats = {'skipped_alias_ids': skipped_alias[:25], 'skipped_alias_n': len(skipped_alias),
             'catalog_nodes_missing_in_db': int((v.stats or {}).get('missing_from_db_n') or 0),
             'catalog_links_missing_in_db': len(lkeys - reader_keys) if v.source == 'pg' else 0,
             'flow_links': sum(1 for l in links if l[3] in flow), 'nonflow_links': sum(1 for l in links if l[3] not in flow),
             'with_valuation': len(vals), 'build_ms': round((time.perf_counter() - t0) * 1000, 2)}
    return {'nodes': nodes, 'links': links, 'delta_ids': frozenset(delta_ids), 'valuations': vals, 'names': names,
            'aliases': aliases, 'flow_types': sorted(flow), 'stats': stats, 'sha': sha, 'lkeys': lkeys,
            'base': {'snapshot_sha': sha[:16], 'catalog_nodes': len(ids), 'catalog_links': len(lkeys)}}


def _catalog_view():
    """(GraphView de los lectores, delta) o (None, respuesta de error)."""
    from core.hotviews import hot
    v = hot.graph(timeout=WARM_WAIT_S)
    if v is None:
        return None, _warming()
    try:
        st = _static_catalog()
    except (OSError, ValueError):
        return None, (jsonify({'error': 'no se pudo leer el catálogo estático', 'error_en': 'static catalog unreadable',
                               'code': 'catalog_unavailable'}), 503)
    return v, hot.cached(f'hot.catalog_delta:{st[0][:16]}', lambda vv: _catalog_delta(vv, st), view=v)


@hot_bp.get('/catalog')
@rate_limit(120, 60)
def hot_catalog():
    """Empresas y vínculos de la generación vigente que el catálogo estático del navegador NO trae. Columnas
    (`node_fields`/`link_fields`); primero los nodos y después los vínculos (`offset`/`limit` cuentan los dos;
    `next_offset` null = última página). `gen` = la generación de la primera página: si cambió entre páginas → 409
    `generation_changed` (el cliente empieza de nuevo). Sin base (o base sin el catálogo) la diferencia es vacía."""
    v, d = _catalog_view()
    if v is None:
        return d
    off, bad = _int_arg('offset', 0, 10 ** 7)
    if bad:
        return bad
    lim, bad = _int_arg('limit', 1, CATALOG_PAGE_CAP)
    if bad:
        return bad
    off, lim = off or 0, lim or CATALOG_PAGE_DEFAULT
    want_gen = (request.args.get('gen') or '').strip()[:80]
    if want_gen and want_gen != str(v.generation):
        return jsonify({'error': 'el grafo cambió entre páginas: vuelve a empezar', 'error_en': 'the graph changed '
                        'between pages: start again', 'code': 'generation_changed', 'generation': v.generation}), 409
    t0 = time.perf_counter()
    nn, nl = len(d['nodes']), len(d['links'])
    end = off + lim
    page_nodes = d['nodes'][off:end] if off < nn else []
    page_links = d['links'][max(0, off - nn):max(0, end - nn)]
    pids = {r[0] for r in page_nodes}
    data = {'generation': v.generation, 'graph_version': v.graph_version, 'source': v.source, 'fallback': v.fallback,
            'base': d['base'], 'node_fields': list(CATALOG_NODE_FIELDS), 'nodes': page_nodes,
            'link_fields': list(CATALOG_LINK_FIELDS), 'links': page_links,
            'valuations': {i: x for i, x in d['valuations'].items() if i in pids},
            'names': {nm: i for nm, i in d['names'].items() if i in pids},
            'aliases': d['aliases'] if off == 0 else {}, 'flow_types': d['flow_types'],
            'total_nodes': nn, 'total_links': nl, 'offset': off, 'limit': lim,
            'next_offset': end if end < nn + nl else None, 'stats': d['stats'],
            'compute_ms': round((time.perf_counter() - t0) * 1000, 3)}
    resp = envelope('catalog', data, v.generation_obj, etag_extra=f"{d['sha'][:12]}.o{off}.l{lim}")
    resp.headers['Cache-Control'] = 'no-cache'      # revalidar siempre con el ETag (304 si la generación es la misma)
    return resp


@hot_bp.get('/catalog/detail')
@rate_limit(240, 60)
def hot_catalog_detail():
    """Los textos de las empresas NUEVAS pedidas (los del catálogo ya están en el navegador) y el texto (`rel`) de los
    vínculos nuevos que tocan a CUALQUIERA de los ids pedidos — se piden al abrir la ficha, no al arrancar."""
    v, d = _catalog_view()
    if v is None:
        return d
    ids = _ids_arg(','.join(request.args.getlist('ids')), cap=CATALOG_DETAIL_IDS_CAP)
    if not ids:
        return _bad('ids', 'ids: lista de empresas separadas por coma', 'ids: comma-separated list of companies')
    want = {}
    for i in ids:
        c = v.canonical(i)
        want[i] = c if c in v.by_id else None
    nodes = {}
    for i, c in want.items():
        if c is None or c not in d['delta_ids']:
            continue
        n = v.by_id[c]
        out = {}
        for k in DETAIL_TEXT_FIELDS:
            x = n.get(k)
            if x is None or x == '':
                continue
            out[k] = x if isinstance(x, (str, int, float, bool)) else str(x)
        ls = n.get('listing')
        if isinstance(ls, dict):
            out['listing'] = {k: ls.get(k) for k in ('symbol', 'mic', 'yahoo_symbol', 'currency', 'kind') if ls.get(k)}
        rm = n.get('research_meta')
        if isinstance(rm, dict):
            out['research'] = {k: rm.get(k) for k in ('batch', 'researched_at', 'tier') if rm.get(k)}
        nodes[c] = out
    targets = {c for c in want.values() if c}
    rels = []
    if targets:
        for l in v.links:
            s, t = l.get('source'), l.get('target')
            if s not in targets and t not in targets:
                continue
            k = (s, t, l.get('type') or 'supply')
            if k in d['lkeys']:
                continue
            rels.append([s, t, k[2], str(l.get('rel') or '')])
    data = {'nodes': nodes, 'rels': rels, 'unknown_ids': [i for i, c in want.items() if c is None],
            'catalog_ids': [i for i, c in want.items() if c is not None and c not in d['delta_ids']],
            'generation': v.generation}
    import hashlib
    tag = hashlib.sha1('\x1f'.join(ids).encode('utf-8')).hexdigest()[:12]
    resp = envelope('catalog', data, v.generation_obj, etag_extra=f"{d['sha'][:12]}.d{tag}")
    resp.headers['Cache-Control'] = 'no-cache'
    return resp
