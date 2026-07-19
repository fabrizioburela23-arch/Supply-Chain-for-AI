"""matrix/api.py — blueprint Flask del motor de matrices: /api/matrix/*.

Igual que la ontología: opcional y defensivo — sin DATABASE_URL responde 503
y el resto de la app sigue intacta. NO tocar /v1/* (API monetizada).
"""
import json
import time

from flask import Blueprint, jsonify, request

matrix_bp = Blueprint('matrix', __name__, url_prefix='/api/matrix')

# ── caché TTL por worker (metrics corre UNA propagación POR NODO — pesado) ──
_TTL_CACHE = {}


def _ttl_get(key, ttl):
    e = _TTL_CACHE.get(key)
    if e and time.time() - e[0] < ttl:
        return e[1]
    return None


def _ttl_set(key, value):
    if len(_TTL_CACHE) > 200:   # sanidad: nunca crecer sin límite
        _TTL_CACHE.clear()
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


@matrix_bp.post('/simulations')
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
    actor = (b.get('actor') or 'anónimo').strip() or 'anónimo'
    sid = 'sim_' + uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    props = {'kind': b.get('kind', 'collapse'), 'direction': b.get('direction', 'down'),
             'severity': b.get('severity', 100), 'targets': (b.get('targets') or [])[:20],
             'affected': int(b.get('affected', 0)), 'top': (b.get('top') or [])[:10],
             'saved_at': now, 'saved_by': actor}
    label = b.get('name') or ('Sim ' + ', '.join((b.get('targets') or ['?'])[:2]))
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
    limit = min(int(request.args.get('limit', 30)), 100)
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
    sys = ('Eres el motor de INSIGHTS de Bixby Finance: un hipergrafo vivo de la cadena de '
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

    from matrix.engine import (active_factors, build_matrices, fragility,
                               propagate)
    from ontology.models import ObjectRecord
    body = request.get_json(silent=True) or {}
    as_of = body.get('as_of')
    lang = (body.get('lang') or 'es').strip().lower()[:2]
    tier = body.get('tier') or 'fast'
    manual_shock = body.get('shock') or None
    ck = f'insights:{as_of or "now"}:{lang}:{tier}'
    if not manual_shock:
        hit = _ttl_get(ck, ttl=180)
        if hit is not None:
            return jsonify({**hit, 'cached': True})

    with scope() as s:
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
    indeg = agg.sum(axis=0) if agg is not None else np.zeros(len(ids))
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
    insights, model = _narrate_insights(situation, lang, tier)
    payload = {'available': True, 'as_of': as_of, 'situation': situation,
               'insights': insights, 'factors': situation['factors'],
               'chokepoints': situation['chokepoints'], 'cascade': cascade_top,
               'trigger': trigger, 'affected': affected, 'model': model}
    if not manual_shock:
        _ttl_set(ck, payload)
    return jsonify(payload)


@matrix_bp.get('/metrics')
def matrix_metrics():
    scope = _db()
    if scope is None:
        return jsonify({'error': 'DATABASE_URL no configurada'}), 503
    as_of = request.args.get('as_of')
    ck = 'metrics:' + (as_of or 'now')
    hit = _ttl_get(ck, ttl=300)
    if hit is not None:
        return jsonify(hit)
    from matrix.engine import compute_metrics
    with scope() as s:
        metrics, factors = compute_metrics(s, as_of=as_of)
    top = sorted(metrics.items(), key=lambda kv: kv[1]['chokepoint_rank'])[:25]
    payload = {'nodes': len(metrics),
               'factors_active': [f['label'] for f in factors],
               'chokepoints_top25': [{'id': k, **v} for k, v in top],
               'metrics': metrics}
    _ttl_set(ck, payload)
    return jsonify(payload)
