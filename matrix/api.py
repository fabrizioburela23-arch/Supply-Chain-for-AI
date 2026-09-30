"""matrix/api.py — blueprint Flask del motor de matrices: /api/matrix/*.

Igual que la ontología: opcional y defensivo — sin DATABASE_URL responde 503
y el resto de la app sigue intacta. NO tocar /v1/* (API monetizada).

Límites (auditoría estructural 2026-09-30, #17): los parámetros del kernel se
ACOTAN antes de propagar (max_hops ≤ 12, damping ∈ [0, 0.95] — con damping ≥ 1
las cascadas no decaen —, n_samples ≤ 100, magnitude ∈ [0, 5]) y las rutas
pesadas (/impact, /insights, /simulations, /factor/fire, /metrics, /<rel_type>,
/parity) tienen límite de tasa por IP. Un valor no numérico → 400 bilingüe.

Revisión 2026-09-30 (medido con el grafo completo): /metrics sin caché cuesta
~50 s de CPU (una propagación POR NODO) y las bandas Monte Carlo ~5 s cada 100
muestras. Con 1 worker de gunicorn eso bastaba para dejar la app lenta. Ahora:
  · as_of se NORMALIZA (UTC; sin zona horaria → UTC; medianoche → 'AAAA-MM-DD')
    antes de usarlo y de armar la clave de caché: '2024-01-03' y
    '2024-01-03T00:00:00Z' comparten caché, y un ISO sin zona ya no da 500;
  · los cálculos pesados (métricas, bandas, paridad) pasan por un SEMÁFORO
    (MATRIX_HEAVY_CONCURRENCY, 1) con espera corta (MATRIX_BUSY_WAIT_S, 3 s):
    sin cupo → 503 bilingüe 'matrix_busy' (o la última lectura, marcada stale);
  · cada FALLO de caché gasta un PRESUPUESTO de cálculo por IP (y global en
    /metrics): las lecturas cacheadas siguen siendo gratis;
  · /insights: tier 'deep' (Sonnet, de pago) solo con el PIN de operador; sin
    él se usa 'fast'. Pasado el presupuesto de IA por IP narra la plantilla.
"""
import json
import logging
import math
import os
import threading
import time
from contextlib import contextmanager

from flask import Blueprint, jsonify, request

from core.http import rate_limit

log = logging.getLogger('khipu')

MAX_HOPS_CAP = 12
DAMPING_MAX = 0.95
N_SAMPLES_CAP = 100          # ~5 s de CPU con el grafo completo (500 eran ~26-46 s)
MAGNITUDE_MAX = 5.0
SHOCK_IDS_CAP = 200


def _env_num(name, default, lo, hi, cast=float):
    try:
        v = cast(os.getenv(name, default))
    except (TypeError, ValueError):
        v = cast(default)
    return max(lo, min(hi, v))


# ── Cálculos pesados: semáforo + presupuestos (revisión 2026-09-30) ─────────
MATRIX_HEAVY_CONCURRENCY = _env_num('MATRIX_HEAVY_CONCURRENCY', 1, 1, 4, int)
MATRIX_BUSY_WAIT_S = _env_num('MATRIX_BUSY_WAIT_S', 3, 0, 60)
METRICS_TTL_S = 900                      # la clave ya lleva la época del grafo
# (límite, ventana en s) de FALLOS de caché — lo cacheado no gasta presupuesto
METRICS_COMPUTE_PER_IP = (4, 600)        # ~50 s de CPU cada uno
METRICS_COMPUTE_GLOBAL = (8, 600)        # tope de todo el servidor: ≤ ~2/3 de un núcleo
BANDS_COMPUTE_PER_IP = (10, 600)         # Monte Carlo (n_samples > 1)
INSIGHTS_AI_PER_IP = (12, 600)           # narraciones IA nuevas; después, plantilla
_HEAVY_SEM = threading.BoundedSemaphore(MATRIX_HEAVY_CONCURRENCY)


class _BadParam(ValueError):
    pass


class _Busy(RuntimeError):
    pass


@contextmanager
def _heavy_slot():
    """Un cálculo pesado a la vez (por defecto): el resto espera poco y se
    rechaza con _Busy en vez de apilar hilos quemando CPU."""
    if not _HEAVY_SEM.acquire(timeout=MATRIX_BUSY_WAIT_S):
        raise _Busy()
    try:
        yield
    finally:
        _HEAVY_SEM.release()


def _busy_response():
    resp = jsonify({'error': 'El motor de matrices está ocupado con otro cálculo pesado; reintenta en un minuto',
                    'error_en': 'The matrix engine is busy with another heavy computation; retry in a minute',
                    'code': 'matrix_busy', 'retry_after': 30})
    resp.headers['Retry-After'] = '30'
    return resp, 503


def _budget_response():
    resp = jsonify({'error': 'Demasiados cálculos pesados seguidos: espera unos minutos',
                    'error_en': 'Too many heavy computations in a row: wait a few minutes',
                    'code': 'compute_budget', 'retry_after': 120})
    resp.headers['Retry-After'] = '120'
    return resp, 429


def _compute_allowed(name, per_ip, glob=None):
    """Gasta 1 del presupuesto de CÁLCULO de esta IP (y el global si se pide).
    Mismo contador en memoria que core.http.rate_limit (IP = último salto XFF)."""
    from core.http import _client_ip, _rate_limit
    if not _rate_limit(f'{_client_ip()}:{name}', per_ip[0], per_ip[1]):
        return False
    if glob and not _rate_limit(f'global:{name}', glob[0], glob[1]):
        return False
    return True


def _num(body, key, default, lo, hi, cast=float):
    """Lee body[key] como número acotado a [lo, hi]. No numérico/NaN → _BadParam."""
    raw = body.get(key, default)
    if raw is None:
        raw = default
    try:
        v = cast(float(raw)) if cast is int else float(raw)
    except (TypeError, ValueError, OverflowError):
        raise _BadParam(key) from None
    if isinstance(v, float) and not math.isfinite(v):
        raise _BadParam(key)
    return max(lo, min(hi, v))


def _bad_param(key):
    return jsonify({'error': f'parámetro inválido: {key} (debe ser numérico)',
                    'error_en': f'invalid parameter: {key} (must be numeric)'}), 400


def _as_of_norm(as_of):
    """(as_of_normalizado | None, respuesta_400 | None).

    Normaliza a UTC: un ISO sin zona horaria se toma como UTC (antes pasaba la
    validación y reventaba en build_matrices con "can't compare offset-naive and
    offset-aware datetimes" → 500); medianoche UTC → 'AAAA-MM-DD'; si no, ISO
    con +00:00. Así las distintas grafías de la MISMA fecha comparten caché."""
    if as_of in (None, ''):
        return None, None
    try:
        from datetime import timezone

        from ontology.service import _parse_dt
        if not isinstance(as_of, str):
            raise ValueError('as_of no es texto')
        dt = _parse_dt(as_of.strip()[:40])
        dt = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
        if (dt.hour, dt.minute, dt.second, dt.microsecond) == (0, 0, 0, 0):
            return dt.date().isoformat(), None
        return dt.isoformat(), None
    except Exception:  # noqa: BLE001 — OntologyError / ValueError / OverflowError
        return None, (jsonify({'error': 'as_of inválido (usa AAAA-MM-DD o ISO 8601)',
                               'error_en': 'invalid as_of (use YYYY-MM-DD or ISO 8601)'}), 400)


def _as_of_error(as_of):
    """Compat: None si as_of es válido (o no vino); si no, la respuesta 400."""
    return _as_of_norm(as_of)[1]


def _rel_weights(raw):
    """rel_weights opcional: {rel_type: peso} solo con tipos conocidos y pesos
    numéricos acotados a [0, 2]. Cualquier otra cosa se descarta."""
    if not isinstance(raw, dict):
        return None
    from matrix.engine import REL_TYPES
    out = {}
    for k, v in list(raw.items())[:32]:
        if k not in REL_TYPES:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if math.isfinite(f):
            out[k] = max(0.0, min(2.0, f))
    return out or None

matrix_bp = Blueprint('matrix', __name__, url_prefix='/api/matrix')

# ── caché TTL por worker (metrics corre UNA propagación POR NODO — pesado) ──
_TTL_CACHE = {}
_TTL_MAX = 200
_TTL_LOCK = threading.Lock()
_LAST_METRICS = {}          # última lectura de /metrics "ahora" (cualquier época) → respaldo stale


def _ttl_get(key, ttl):
    e = _TTL_CACHE.get(key)
    if e and time.time() - e[0] < ttl:
        return e[1]
    return None


def _ttl_set(key, value):
    """Nunca crece sin límite; al llenarse descarta las entradas MÁS VIEJAS (antes
    vaciaba todo: un chorro de as_of distintos borraba también la lectura cara
    del estado actual)."""
    with _TTL_LOCK:
        if len(_TTL_CACHE) >= _TTL_MAX and key not in _TTL_CACHE:
            for k in sorted(_TTL_CACHE, key=lambda k: _TTL_CACHE[k][0])[:len(_TTL_CACHE) - _TTL_MAX + 1]:
                _TTL_CACHE.pop(k, None)
        _TTL_CACHE[key] = (time.time(), value)


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
    from matrix.engine import (REL_TYPES, _graph_epoch, active_factors,
                               build_matrices, node_index, spectral_radius)
    with scope() as s:
        idx, ids = node_index(s)
        factors = active_factors(s)
        # ρ(T): riesgo sistémico macro. Cacheado por ÉPOCA del grafo (no solo
        # TTL): así un cambio de peso o de severidad de un Factor invalida el
        # ρ/estabilidad cacheados (la clave por nº de nodos + ids de factor NO
        # capturaba esos cambios → estabilidad rancia hasta el TTL).
        ck = 'spectral:' + _graph_epoch(s)
        sr = _ttl_get(ck, ttl=60)
        if sr is None:
            try:
                mats, midx, mids = build_matrices(s)
                sr = spectral_radius(mats, factors=factors, idx=midx)
                _ttl_set(ck, sr)
            except Exception:  # noqa: BLE001
                sr = None
    out = {'available': True, 'objects': len(ids),
           'rel_types': REL_TYPES,
           'active_factors': [{'id': f['id'], 'label': f['label'],
                               'severity': f['severity'],
                               'members': len(f['members'])}
                              for f in factors]}
    if sr:
        # Estabilidad sistémica: damping·ρ(T) < 1 ⇒ las cascadas decaen.
        out['spectral_radius'] = sr['rho']
        out['damping_rho'] = sr['damping_rho']
        out['systemically_stable'] = sr['stable']
    return jsonify(out)


@matrix_bp.get('/<rel_type>')
@rate_limit(30, 600)
def matrix_get(rel_type):
    scope = _db()
    if scope is None:
        return jsonify({'error': 'DATABASE_URL no configurada'}), 503
    from matrix.engine import REL_TYPES, active_factors, build_matrices, modulate
    if rel_type not in REL_TYPES:
        return jsonify({'error': f'rel_type desconocido. Válidos: {REL_TYPES}',
                        'error_en': f'unknown rel_type. Valid: {REL_TYPES}'}), 400
    as_of, bad = _as_of_norm(request.args.get('as_of') or None)
    if bad:
        return bad
    with scope() as s:
        mats, idx, ids = build_matrices(s, as_of=as_of)
        if request.args.get('modulated', '1') != '0':
            mats = modulate(mats, idx, active_factors(s, as_of=as_of))
    import scipy.sparse as sp
    m = mats[rel_type]
    if sp.issparse(m):
        coo = m.tocoo()
        cells = [[ids[i], ids[j], round(float(v), 3)]
                 for i, j, v in zip(coo.row.tolist(), coo.col.tolist(), coo.data.tolist()) if v != 0]
    else:
        cells = [[ids[i], ids[j], round(float(m[i, j]), 3)]
                 for i, j in zip(*m.nonzero())]
    return jsonify({'rel_type': rel_type, 'as_of': as_of, 'n': len(ids),
                    'nnz': len(cells), 'cells': cells})


@matrix_bp.post('/impact')
@rate_limit(60, 300)
def matrix_impact():
    """Body: {shock: [ids], magnitude?, damping?, max_hops?, rel_weights?, as_of?}
    → {impacts: {id: pct}, cascade: [{id, hop, impact}], factors_active}."""
    scope = _db()
    if scope is None:
        return jsonify({'error': 'DATABASE_URL no configurada'}), 503
    from matrix.engine import active_factors, build_matrices, fragility, propagate
    body = request.get_json(silent=True) or {}
    if not isinstance(body, dict):
        body = {}
    shock = body.get('shock') or []
    if not shock or not isinstance(shock, list):
        return jsonify({'error': 'shock: lista de ids requerida'}), 400
    shock = [x for x in shock if isinstance(x, str)][:SHOCK_IDS_CAP]
    if not shock:
        return jsonify({'error': 'shock: lista de ids requerida', 'error_en': 'shock: list of ids required'}), 400
    try:
        kw = dict(
            magnitude=_num(body, 'magnitude', 1.0, 0.0, MAGNITUDE_MAX),
            damping=_num(body, 'damping', 0.6, 0.0, DAMPING_MAX),
            max_hops=_num(body, 'max_hops', 6, 1, MAX_HOPS_CAP, int),
            rel_weights=_rel_weights(body.get('rel_weights')),
            nonlinear=bool(body.get('nonlinear', False)),   # flag: kernel no-lineal (estrés severo)
        )
        n_samples = _num(body, 'n_samples', 1, 1, N_SAMPLES_CAP, int)
        seed = _num(body, 'seed', 0, 0, 2 ** 31 - 1, int)
    except _BadParam as e:
        return _bad_param(str(e))
    as_of, bad = _as_of_norm(body.get('as_of') or None)
    if bad:
        return bad
    with scope() as s:
        mats, idx, ids = build_matrices(s, as_of=as_of)
        factors = active_factors(s, as_of=as_of)
        frag = fragility(idx, factors)
    unknown = [x for x in shock if x not in idx]
    if len(unknown) == len(shock):
        return jsonify({'error': f'ningún id del shock existe: {unknown[:5]}'}), 400
    shock_ids = [x for x in shock if x in idx]
    impacts, cascade = propagate(mats, idx, ids, shock_ids, frag=frag, **kw)
    out = {'shock': shock, 'as_of': as_of,
           'impacts': impacts, 'cascade': cascade,
           'affected': len(impacts) - len(shock),
           'factors_active': [f['label'] for f in factors],
           'unknown_ids': unknown}
    # Bandas de incertidumbre Monte Carlo (opt-in: n_samples>1). Lenguaje VaR/CVaR.
    # Caras (~5 s / 100 muestras): presupuesto por IP + semáforo. Si no hay
    # cupo, el impacto determinista SÍ se devuelve y se explica por qué faltan
    # las bandas (bands_skipped) en vez de fallar la petición entera.
    if n_samples > 1:
        from matrix.engine import propagate_bands
        if not _compute_allowed('matrix_bands_compute', BANDS_COMPUTE_PER_IP):
            out['bands_skipped'] = {
                'reason': 'budget',
                'error': 'Demasiadas simulaciones Monte Carlo seguidas: bandas omitidas, reintenta en unos minutos',
                'error_en': 'Too many Monte Carlo runs in a row: bands skipped, retry in a few minutes'}
        else:
            try:
                with _heavy_slot():
                    mc = propagate_bands(mats, idx, ids, shock_ids, n_samples=n_samples,
                                         seed=seed, frag=frag, **kw)
                out['bands'] = mc['bands']
                out['n_samples'] = mc['n_samples']
            except _Busy:
                out['bands_skipped'] = {
                    'reason': 'busy',
                    'error': 'Motor ocupado con otro cálculo pesado: bandas omitidas, reintenta en un minuto',
                    'error_en': 'Engine busy with another heavy computation: bands skipped, retry in a minute'}
    return jsonify(out)


@matrix_bp.post('/simulations')
@rate_limit(30, 600)
def matrix_save_sim():
    """Guarda una simulación en la ontología (objeto type='Simulation') → hereda
    fecha (recorded_at) e historial. Body: {actor, name, targets, kind,
    direction, severity, affected, top:[{id,v}]}."""
    scope = _db()
    if scope is None:
        return jsonify({'error': 'DATABASE_URL no configurada'}), 503
    import uuid
    from datetime import datetime, timezone
    from ontology.service import apply_event
    b = request.get_json(silent=True) or {}
    if not isinstance(b, dict):
        b = {}
    actor = str(b.get('actor') or 'anónimo').strip()[:80] or 'anónimo'
    sid = 'sim_' + uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    targets = [str(t)[:120] for t in (b.get('targets') if isinstance(b.get('targets'), list) else [])][:20]
    try:
        affected = int(_num(b, 'affected', 0, 0, 10 ** 7, int))
    except _BadParam as e:
        return _bad_param(str(e))
    top = b.get('top') if isinstance(b.get('top'), list) else []
    props = {'kind': str(b.get('kind', 'collapse'))[:40], 'direction': str(b.get('direction', 'down'))[:10],
             'severity': b.get('severity', 100) if isinstance(b.get('severity', 100), (int, float)) else 100,
             'targets': targets, 'affected': affected, 'top': top[:10],
             'saved_at': now, 'saved_by': actor}
    label = str(b.get('name') or ('Sim ' + ', '.join((targets or ['?'])[:2])))[:200]
    with scope() as s:
        apply_event(s, 'ObjectCreated', {'label': label, 'type': 'Simulation', 'properties': props},
                    valid_from=now, source='livesim', actor=actor, object_id=sid)
    return jsonify({'id': sid, 'label': label, 'saved_at': now})


@matrix_bp.get('/simulations')
def matrix_list_sims():
    """Historial de simulaciones guardadas, más recientes primero."""
    scope = _db()
    if scope is None:
        return jsonify({'error': 'DATABASE_URL no configurada'}), 503
    from sqlalchemy import select
    from ontology.models import ObjectRecord
    try:
        limit = min(max(int(request.args.get('limit', 30)), 1), 100)
    except (TypeError, ValueError):
        return jsonify({'error': 'limit inválido (entero 1-100)', 'error_en': 'invalid limit (integer 1-100)'}), 400
    with scope() as s:
        rows = s.scalars(select(ObjectRecord).where(ObjectRecord.type == 'Simulation')).all()
        sims = [{'id': o.id, 'label': o.label, **(o.properties or {})} for o in rows]
    sims.sort(key=lambda x: x.get('saved_at', ''), reverse=True)
    return jsonify({'simulations': sims[:limit]})


def _fallback_insights(situation, lang):
    """Narración de plantilla (sin IA) — el panel NUNCA sale vacío."""
    es = lang != 'en'
    out = []
    for f in (situation.get('factors') or [])[:2]:
        mem = ', '.join(f.get('members', [])[:4])
        out.append({'kind': 'riesgo',
            'title': (f"Factor activo: {f['label']}" if es else f"Active factor: {f['label']}"),
            'detail': (f"Severidad {f.get('severity', 5):.0f}/10. Toca a {mem}. "
                       f"Amplifica el daño que se propaga a sus dependientes." if es else
                       f"Severity {f.get('severity', 5):.0f}/10. Hits {mem}. "
                       f"Amplifies the damage cascading to their dependents.")})
    ct = situation.get('cascade_top') or []
    if situation.get('trigger') and ct:
        top = ct[0]
        out.append({'kind': 'estructura',
            'title': (f"Cascada desde {situation['trigger']}" if es else f"Cascade from {situation['trigger']}"),
            'detail': (f"Alcanza a {situation.get('affected_count', 0)} nodos; el más golpeado es "
                       f"{top['name']} ({top['impact']:.0f}%)." if es else
                       f"Reaches {situation.get('affected_count', 0)} nodes; hardest hit is "
                       f"{top['name']} ({top['impact']:.0f}%).")})
    cps = situation.get('chokepoints') or []
    if cps:
        out.append({'kind': 'estructura',
            'title': ('Puntos de estrangulamiento' if es else 'Chokepoints'),
            'detail': (f"El sistema depende desproporcionadamente de {', '.join(cps[:3])}." if es else
                       f"The system depends disproportionately on {', '.join(cps[:3])}.")})
    if not out:
        out.append({'kind': 'estructura',
            'title': ('Sistema estable' if es else 'Stable system'),
            'detail': ('Sin factores sistémicos activos ahora mismo.' if es else
                       'No active systemic factors right now.')})
    return out[:4]


def _narrate_insights(situation, lang, tier):
    """IA barata narra el estado del hipergrafo. Fallback a plantilla si falla."""
    tongue = 'inglés' if lang == 'en' else 'español'
    sys = ('Eres el motor de INSIGHTS de Khipus Finance AI: un hipergrafo vivo de la cadena de '
           'suministro de IA, semiconductores, espacio y nuclear. Te doy el ESTADO del sistema '
           '(factores sistémicos activos = hiperaristas, puntos de estrangulamiento, y una '
           'cascada ya simulada por el motor). Devuelve 2-4 INSIGHTS accionables, cortos y '
           'ESPECÍFICOS: nombra empresas reales del estado, no generalidades. Cauto: es '
           'análisis, no asesoría financiera; nada de "compra/vende" tajante. '
           'Responde SOLO un objeto JSON válido, sin markdown: '
           '{"insights":[{"title":str,"detail":str,"kind":str}]}. '
           'kind ∈ "riesgo"|"oportunidad"|"estructura". title ≤ 9 palabras. detail = 1-2 frases. '
           f'Escribe TODO en {tongue}.')
    prompt = 'ESTADO DEL HIPERGRAFO (JSON):\n' + json.dumps(situation, ensure_ascii=False)[:4000]
    try:
        from core.ai import _ai_complete, _extract_json
        text, model = _ai_complete(sys, prompt, max_tokens=700, tier=tier)
        parsed = _extract_json(text)
        arr = parsed.get('insights') if isinstance(parsed, dict) else None
        if isinstance(arr, list) and arr:
            out = []
            for it in arr[:4]:
                if not isinstance(it, dict):
                    continue
                kind = it.get('kind')
                out.append({'title': str(it.get('title', ''))[:120],
                            'detail': str(it.get('detail', ''))[:400],
                            'kind': kind if kind in ('riesgo', 'oportunidad', 'estructura') else 'estructura'})
            out = [o for o in out if o['title'] or o['detail']]
            if out:
                return out, model
    except Exception:  # noqa: BLE001
        pass
    return _fallback_insights(situation, lang), 'plantilla'


@matrix_bp.post('/insights')
@rate_limit(40, 600)
def matrix_insights():
    """El hipergrafo corre una simulación EN VIVO con los factores activos y la
    NARRA. Body: {as_of?, tier?='fast', lang?='es', shock?=[ids]}. Sin factores
    dispara desde el chokepoint principal. → {situation, insights, factors,
    chokepoints, cascade, trigger, affected, model}."""
    scope = _db()
    if scope is None:
        return jsonify({'available': False, 'reason': 'DATABASE_URL no configurada'}), 503
    import numpy as np
    from sqlalchemy import select

    from matrix.engine import (_graph_epoch, active_factors, build_matrices,
                               fragility, propagate)
    from ontology.models import ObjectRecord
    body = request.get_json(silent=True) or {}
    if not isinstance(body, dict):
        body = {}
    lang = 'en' if str(body.get('lang') or 'es').strip().lower()[:2] == 'en' else 'es'
    tier, tier_note = _insights_tier(body.get('tier'))
    manual_shock = body.get('shock') or None
    as_of, bad = _as_of_norm(body.get('as_of') or None)
    if bad:
        return bad
    if manual_shock is not None:
        manual_shock = [x for x in manual_shock if isinstance(x, str)][:SHOCK_IDS_CAP] \
            if isinstance(manual_shock, list) else None

    with scope() as s:
        # Clave cacheada por ÉPOCA del grafo → un alta/baja/cambio de peso o de
        # Factor invalida los insights (antes solo TTL 180s → datos rancios).
        epoch = _graph_epoch(s)
        ck = f'insights:{epoch}:{as_of or "now"}:{lang}:{tier}'
        if not manual_shock:
            hit = _ttl_get(ck, ttl=180)
            if hit is not None:
                return jsonify({**hit, 'cached': True, **tier_note})
        mats, idx, ids = build_matrices(s, as_of=as_of)
        factors = active_factors(s, as_of=as_of)
        lbl = {r[0]: r[1] for r in s.execute(
            select(ObjectRecord.id, ObjectRecord.label)).all()}

    def nm(i):
        return lbl.get(i, i)

    if not ids:
        empty = {'available': True, 'as_of': as_of, 'situation': {}, 'insights':
                 _fallback_insights({}, lang), 'factors': [], 'chokepoints': [],
                 'cascade': [], 'trigger': None, 'affected': 0, 'model': 'plantilla'}
        return jsonify(empty)

    # Chokepoints rápidos: in-degree ponderado combinado (sin correr metrics pesado).
    agg = None
    for m in mats.values():
        agg = m.copy() if agg is None else agg + m
    # in-degree ponderado; np.asarray(...).ravel() → 1D tanto denso como sparse
    # (sparse.sum devuelve np.matrix, que rompería argsort/indexado).
    indeg = np.asarray(agg.sum(axis=0)).ravel() if agg is not None else np.zeros(len(ids))
    top_choke = [ids[i] for i in np.argsort(-indeg)[:6] if indeg[i] > 0]

    # Foco de la simulación: shock manual > miembros del factor más severo > chokepoint.
    if manual_shock:
        shock = [x for x in manual_shock if x in idx]
        trigger = 'shock manual'
    elif factors:
        fx = max(factors, key=lambda f: f['severity'] * max(1, len(f['members'])))
        shock = [m for m in fx['members'] if m in idx]
        trigger = fx['label']
    else:
        shock = top_choke[:1]
        trigger = (f'colapso hipotético de {nm(shock[0])}' if shock else None)

    cascade_top, affected = [], 0
    if shock:
        frag = fragility(idx, factors)
        impacts, order = propagate(mats, idx, ids, shock, magnitude=1.0, frag=frag)
        affected = max(0, len(impacts) - len(shock))
        cascade_top = [{'id': o['id'], 'name': nm(o['id']),
                        'impact': o['impact'], 'hop': o['hop']} for o in order[:8]]

    situation = {
        'factors': [{'label': f['label'], 'severity': f['severity'],
                     'members': [nm(m) for m in list(f['members'])[:8]]} for f in factors[:5]],
        'chokepoints': [nm(i) for i in top_choke],
        'trigger': trigger,
        'cascade_top': [{'name': c['name'], 'impact': c['impact']} for c in cascade_top],
        'affected_count': affected,
    }
    # Presupuesto de narraciones IA NUEVAS por IP (lo cacheado no gasta): pasado
    # el tope, la plantilla (sin IA) — y esa respuesta degradada no se cachea
    # ni entra al historial, para no "pegarle" la plantilla al resto.
    ai_ok = _compute_allowed('matrix_insights_ai', INSIGHTS_AI_PER_IP)
    if ai_ok:
        insights, model = _narrate_insights(situation, lang, tier)
    else:
        insights, model = _fallback_insights(situation, lang), 'plantilla'
    payload = {'available': True, 'as_of': as_of, 'situation': situation,
               'insights': insights, 'factors': situation['factors'],
               'chokepoints': situation['chokepoints'], 'cascade': cascade_top,
               'trigger': trigger, 'affected': affected, 'model': model}
    if not manual_shock and ai_ok:
        _ttl_set(ck, payload)
        # historial = lecturas del estado REAL: ni shocks manuales ni viajes en
        # el tiempo (as_of) — cada as_of distinto dejaba una fila nueva.
        if as_of is None:
            _persist_insight(scope, epoch, as_of, lang, payload)
    return jsonify({**payload, **tier_note})


def _insights_tier(requested):
    """('deep'|'fast', nota). 'deep' (Sonnet, de pago) solo con el PIN de
    operador válido — o sin TRADE_PIN configurado (desarrollo). Sin PIN se
    degrada a 'fast' (nunca 401: es una lectura); un PIN errado cuenta para el
    bloqueo compartido de core.pin."""
    if requested != 'deep':
        return 'fast', {}
    try:
        from core.pin import check
        if check(where='matrix_insights_deep', strict=False) is None:
            return 'deep', {}
    except Exception:  # noqa: BLE001 — sin core.pin/Flask: lo seguro es 'fast'
        pass
    return 'fast', {'tier': 'fast', 'tier_note': 'deep requiere el PIN de operador — se usó fast',
                    'tier_note_en': 'deep requires the operator PIN — fast was used'}


def _persist_insight(scope, epoch, as_of, lang, payload):
    """Guarda el insight en el historial, UNA fila por época del grafo.

    Solo para lecturas del estado real (los shocks manuales son exploración,
    no historia). Nunca debe tumbar la respuesta: si el guardado falla, el
    usuario igual recibe su insight."""
    from ontology.models import InsightSnapshot
    from sqlalchemy import select
    try:
        with scope() as s:
            dup = s.scalars(select(InsightSnapshot).where(
                InsightSnapshot.graph_epoch == str(epoch),
                InsightSnapshot.as_of.is_(None) if as_of is None else InsightSnapshot.as_of == as_of,
                InsightSnapshot.lang == lang,
            ).limit(1)).first()
            if dup:
                return
            s.add(InsightSnapshot(
                graph_epoch=str(epoch), as_of=as_of, lang=lang,
                trigger=(payload.get('trigger') or '')[:300],
                affected=int(payload.get('affected') or 0),
                situation=payload.get('situation') or {},
                insights=payload.get('insights'),
                model=(payload.get('model') or '')[:60],
            ))
    except Exception:  # noqa: BLE001
        log.warning('no se pudo guardar el insight en el historial', exc_info=True)


@matrix_bp.get('/insights/history')
def matrix_insights_history():
    """Historial de insights: cómo fue cambiando la lectura de la red.

    Una fila por cambio real del grafo (no por visita) — ver InsightSnapshot.
    Query: ?limit=20&lang=es. → {available, count, history:[…]}."""
    scope = _db()
    if scope is None:
        return jsonify({'available': False, 'reason': 'DATABASE_URL no configurada'}), 503
    from ontology.models import InsightSnapshot
    from sqlalchemy import select
    try:
        limit = min(max(int(request.args.get('limit', 20)), 1), 200)
    except (TypeError, ValueError):
        limit = 20
    lang = (request.args.get('lang') or '').strip().lower()[:2]

    with scope() as s:
        q = select(InsightSnapshot)
        if lang:
            q = q.where(InsightSnapshot.lang == lang)
        rows = s.scalars(q.order_by(InsightSnapshot.created_at.desc()).limit(limit)).all()
        history = [{
            'id': str(r.id), 'as_of': r.as_of, 'lang': r.lang, 'trigger': r.trigger,
            'affected': r.affected, 'situation': r.situation, 'insights': r.insights,
            'model': r.model,
            'created_at': r.created_at.isoformat() if r.created_at else None,
        } for r in rows]
    return jsonify({'available': True, 'count': len(history), 'history': history})


@matrix_bp.get('/metrics')
@rate_limit(60, 600)
def matrix_metrics():
    """Métricas por nodo (chokepoints, PageRank, ρ). PESADO sin caché (~50 s de
    CPU con el grafo completo): caché por época+as_of, presupuesto de cálculo
    por IP y global, y un solo cálculo a la vez. Para "ahora" (sin as_of), si no
    hay cupo se sirve la última lectura con stale:true en vez de fallar."""
    scope = _db()
    if scope is None:
        return jsonify({'error': 'DATABASE_URL no configurada'}), 503
    as_of, bad = _as_of_norm(request.args.get('as_of') or None)
    if bad:
        return bad
    from matrix.engine import (_graph_epoch, build_matrices, compute_metrics,
                               spectral_radius)
    slot = as_of or 'now'
    with scope() as s:
        # Cacheado por ÉPOCA del grafo → un cambio estructural invalida las
        # métricas (antes solo TTL 300s → chokepoints/cascada/ρ rancios).
        ck = f'metrics:{_graph_epoch(s)}:{slot}'
    hit = _ttl_get(ck, ttl=METRICS_TTL_S)
    if hit is not None:
        return jsonify(hit)
    stale = _LAST_METRICS.get(slot)

    def _fallback(resp):
        if stale is not None:
            return jsonify({**stale, 'stale': True})
        return resp

    if not _compute_allowed('matrix_metrics_compute', METRICS_COMPUTE_PER_IP, METRICS_COMPUTE_GLOBAL):
        return _fallback(_budget_response())
    try:
        with _heavy_slot():
            hit = _ttl_get(ck, ttl=METRICS_TTL_S)     # otro hilo pudo calcularlo mientras esperábamos
            if hit is not None:
                return jsonify(hit)
            with scope() as s:
                metrics, factors = compute_metrics(s, as_of=as_of)
                try:
                    mats, midx, _ = build_matrices(s, as_of=as_of)
                    sr = spectral_radius(mats, factors=factors, idx=midx)
                except Exception:  # noqa: BLE001
                    sr = None
    except _Busy:
        return _fallback(_busy_response())
    top = sorted(metrics.items(), key=lambda kv: kv[1]['chokepoint_rank'])[:25]
    # PageRank: centralidad complementaria (robusta a componentes desconectados)
    pr_top = sorted(metrics.items(), key=lambda kv: kv[1].get('pagerank_rank', 1e9))[:25]
    payload = {'nodes': len(metrics),
               'factors_active': [f['label'] for f in factors],
               'chokepoints_top25': [{'id': k, **v} for k, v in top],
               'central_pagerank_top25': [{'id': k, 'pagerank': v.get('pagerank'),
                                           'pagerank_rank': v.get('pagerank_rank')}
                                          for k, v in pr_top],
               'spectral': sr,
               'metrics': metrics}
    _ttl_set(ck, payload)
    if slot == 'now':
        _LAST_METRICS['now'] = payload
    return jsonify(payload)


@matrix_bp.get('/factors')
def matrix_factors():
    """Track B: detalle COMPLETO de los Factor activos — /status solo expone un
    conteo de members; el motor cliente (livesim) necesita el dict {obj_id:coef}
    y el rationale para aplicar la MISMA fragilidad que el server."""
    scope = _db()
    if scope is None:
        return jsonify({'available': False, 'factors': []})
    from matrix.engine import active_factors
    as_of, bad = _as_of_norm(request.args.get('as_of') or None)
    if bad:
        return bad
    with scope() as s:
        factors = active_factors(s, as_of=as_of)
    return jsonify({'available': True, 'as_of': as_of, 'factors': factors})


@matrix_bp.post('/factor/fire')
@rate_limit(30, 300)
def matrix_factor_fire():
    """WHAT-IF de crisis: dispara UN factor a su severity_crisis SIN mutar la
    ontología (los factores viven LATENTES — severity 1.0 — para no simular
    todas las crisis a la vez; ver curación 2026-08-02). El shock inicial son
    sus miembros escalados por su coeficiente; la fragilidad se recalcula con
    ese factor en nivel de crisis sobre el fondo latente.
    Body: {factor_id, magnitude?, damping?, max_hops?, n_samples?}
    → {factor, rho: {latente, crisis, crisis_damped}, impacts, cascade,
       affected, top}."""
    scope = _db()
    if scope is None:
        return jsonify({'error': 'DATABASE_URL no configurada'}), 503
    from matrix.engine import (active_factors, build_matrices, fragility,
                               propagate, spectral_radius)
    body = request.get_json(silent=True) or {}
    if not isinstance(body, dict):
        body = {}
    fid = str(body.get('factor_id') or '').strip()[:120]
    if not fid:
        return jsonify({'error': 'factor_id requerido'}), 400
    try:
        damping = _num(body, 'damping', 0.6, 0.0, DAMPING_MAX)
        max_hops = _num(body, 'max_hops', 6, 1, MAX_HOPS_CAP, int)
        mag_raw = body.get('magnitude')
        magnitude = None if mag_raw is None else _num(body, 'magnitude', 1.0, 0.0, MAGNITUDE_MAX)
    except _BadParam as e:
        return _bad_param(str(e))
    with scope() as s:
        mats, idx, ids = build_matrices(s)
        factors = active_factors(s)
    target = next((f for f in factors if f['id'] == fid), None)
    if target is None:
        return jsonify({'error': f'factor no activo o inexistente: {fid}',
                        'activos': [f['id'] for f in factors][:60]}), 404
    crisis = target.get('severity_crisis') or min(5.0, target['severity'] * 2)
    factors_crisis = [dict(f, severity=crisis) if f['id'] == fid else f
                      for f in factors]
    frag = fragility(idx, factors_crisis)
    shock_ids = [m for m in target['members'] if m in idx]
    if not shock_ids:
        return jsonify({'error': f'ningún miembro del factor existe en la matriz: {fid}'}), 400
    # magnitud del golpe inicial = coeficiente del miembro × (crisis/5): un
    # miembro coef 0.9 en una crisis sev 4 arranca al 72%, no al 100%
    base_mag = magnitude if magnitude is not None else max(0.0, min(MAGNITUDE_MAX, float(crisis) / 5.0))
    impacts, cascade = propagate(
        mats, idx, ids, shock_ids, frag=frag,
        magnitude=base_mag, damping=damping,
        max_hops=max_hops)
    # el golpe inicial por miembro respeta su coeficiente relativo
    for m in shock_ids:
        coef = min(1.0, float(target['members'][m]))
        if m in impacts:
            impacts[m] = round(impacts[m] * coef, 2)
    rho_lat = spectral_radius(mats, factors, idx, damping=damping)
    rho_cri = spectral_radius(mats, factors_crisis, idx, damping=damping)
    top = sorted(((k, v) for k, v in impacts.items() if k not in target['members']),
                 key=lambda x: -x[1])[:15]
    return jsonify({
        'factor': {'id': fid, 'label': target['label'],
                   'severity_latente': target['severity'],
                   'severity_crisis': crisis,
                   'rationale': target.get('rationale', ''),
                   'members': target['members']},
        'rho': {'latente': rho_lat.get('rho'), 'crisis': rho_cri.get('rho'),
                'crisis_damped': rho_cri.get('damping_rho'),
                'estable_en_crisis': rho_cri.get('stable')},
        'impacts': impacts, 'cascade': cascade,
        'affected': len(impacts) - len(shock_ids),
        'top_contagio': [{'id': k, 'impact': round(v, 1)} for k, v in top],
    })


@matrix_bp.get('/parity')
@rate_limit(10, 600)
def matrix_parity():
    """CORTE SEGURO denso↔disperso (spec §"Plan de despliegue seguro"): corre
    AMBOS motores sobre los MISMOS datos y reporta la discrepancia máxima. Se
    usa para correr los dos en paralelo antes de retirar el denso — solo se
    promueve MATRIX_ENGINE=sparse tras un periodo sin discrepancias. `alert`
    True si la diferencia supera la tolerancia. Params: ?shock=ID&shock=ID&tol=."""
    scope = _db()
    if scope is None:
        return jsonify({'available': False, 'reason': 'DATABASE_URL no configurada'}), 503
    from matrix import engine as E
    if E.sp is None:
        return jsonify({'available': False,
                        'reason': 'scipy no instalado — modo disperso no disponible'}), 200
    shock = [str(x)[:120] for x in request.args.getlist('shock')][:SHOCK_IDS_CAP]
    try:
        tol = float(request.args.get('tol', '1e-6'))
        if not math.isfinite(tol) or tol < 0:
            raise ValueError
    except (TypeError, ValueError):
        return _bad_param('tol')
    try:
        with _heavy_slot(), scope() as s:     # construye las matrices DENSAS: pesado
            md, idx, ids = E.build_matrices(s, sparse=False)
            ms, _, _ = E.build_matrices(s, sparse=True)
            shock = [x for x in shock if x in idx] or ids[:1]
            imp_d, _ = E.propagate(md, idx, ids, shock)
            imp_s, _ = E.propagate(ms, idx, ids, shock)
            rho_d = E.spectral_radius(md).get('rho')
            rho_s = E.spectral_radius(ms).get('rho')
    except _Busy:
        return _busy_response()
    keys = set(imp_d) | set(imp_s)
    max_diff = max((abs(imp_d.get(k, 0.0) - imp_s.get(k, 0.0)) for k in keys), default=0.0)
    mismatch = sorted(set(imp_d) ^ set(imp_s))
    within = (max_diff <= tol) and not mismatch and abs((rho_d or 0) - (rho_s or 0)) <= 1e-3
    return jsonify({
        'available': True, 'shock': shock, 'tol': tol,
        'nodes_compared': len(keys), 'max_abs_diff': round(max_diff, 9),
        'key_set_mismatch': mismatch[:20],
        'rho_dense': rho_d, 'rho_sparse': rho_s,
        'within_tolerance': within, 'alert': (not within),
        'recommendation': (
            'El motor disperso coincide con el denso dentro de tolerancia — seguro promover MATRIX_ENGINE=sparse.'
            if within else
            'DISCREPANCIA sobre la tolerancia — NO promover el motor disperso; investigar antes del corte.')})
