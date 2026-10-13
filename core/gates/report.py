"""core/gates/report.py — EL objeto de explicación `GateReport/1` (docs/INFRA_OPERATIVA.md §3.6) y su registro.

Una sola forma de reporte en lugar de las cuatro de hoy (G-3):

  {"schema": "gate-report/1", "gate": "ontology.g1", "mode": "shadow", "outcome": "warn", "conforms": false,
   "shapes": {"artifact": "ontology.shapes", "semver": "1.0.0", "ir_hash": "…"}, "focus": "khd:link/…",
   "results": [{"rule": "khr:link.no_self_loop", "shape": "khs:LinkNoSelfLoop", "severity": "block",
                "effective": "warn", "path": "kh:source", "focus": "khd:link/…", "value": "TSMC", "limit": null,
                "message": {"es": "…", "en": "…"}}],
   "latency_us": 41}

  · `severity` = la DECLARADA en el TTL (con `policy.gates.severity_overrides`); `effective` = la que rige. En
    modo SOMBRA (paso 10) todo rige como aviso: block/requires_approval → warn (info sigue info). Nada se rechaza.
  · Los mensajes son plantillas del TTL con {value} y {limit} que llena el evaluador (ninguna cifra viene de IA).
  · Dónde queda: en la decisión en curso (decision_violations fila por fila + blob `gate_report` + veredicto
    combinado); sin decisión en curso, se acumula por transacción y al confirmar se escribe UNA decisión
    `audit.gates` (system:gates, async) con todas. Nunca lanza: vigilar no tumba una escritura.
"""
import logging
import threading
from datetime import datetime
from decimal import Decimal

from core.gates import focus as F

log = logging.getLogger('khipu')
SCHEMA = 'gate-report/1'
MAX_RESULTS = 200
_LOCK = threading.Lock()
STATS = {'evaluated': 0, 'with_results': 0, 'recorded': 0, 'record_errors': 0, 'eval_errors': 0,
         'by_rule': {}, 'last_error': None, 'lat_us': []}


def _shadow(sev):
    return 'info' if sev == 'info' else 'warn'


def _json_val(v):
    if v is None:
        return None
    if isinstance(v, F.IRI):
        return F.compact(v)
    if isinstance(v, bool):
        return v
    if isinstance(v, Decimal):
        return float(v) if v.is_finite() else str(v)
    if isinstance(v, datetime):
        return v.isoformat()
    return str(v)[:200]


def _fmt(v, lang):
    if v is None:
        return '—'
    if isinstance(v, F.IRI):
        return F.ident_of(v)
    if isinstance(v, bool):
        return ('sí' if v else 'no') if lang == 'es' else ('yes' if v else 'no')
    if isinstance(v, Decimal):
        s = format(v.normalize(), 'f') if v == v else str(v)
        return s.replace('.', ',') if lang == 'es' else s
    if isinstance(v, datetime):
        return v.strftime('%Y-%m-%d %H:%M')
    return str(v)[:120]


def build(gate, raw, compiled, mode, overrides=None, latency_us=None, focus=None):
    overrides = overrides or {}
    results = []
    outcome = 'pass'
    from core.gates.engine import SEVERITY, worst
    by_rule = {}
    for n, (this, kind, spec, v, lim) in enumerate(raw):
        declared = overrides.get(spec['rule']) or SEVERITY.get(F.expand(spec['severity']), 'block')
        eff = _shadow(declared) if mode == 'shadow' else declared
        outcome = worst(outcome, eff)          # sobre TODOS los resultados (no solo los primeros MAX_RESULTS)
        by_rule[spec['rule']] = by_rule.get(spec['rule'], 0) + 1
        if n >= MAX_RESULTS:
            continue                           # el detalle se recorta; el conteo y el desenlace no
        msg = {}
        for lang in ('es', 'en'):
            t = spec.get(f'msg_{lang}') or spec['rule']
            msg[lang] = t.replace('{value}', _fmt(v, lang)).replace('{limit}', _fmt(lim, lang))
        results.append({'rule': spec['rule'], 'shape': spec['iri'], 'severity': declared, 'effective': eff,
                        'path': spec.get('path'), 'focus': F.compact(this), 'value': _json_val(v),
                        'limit': _json_val(lim), 'message': msg})
    rep = {'schema': SCHEMA, 'gate': gate, 'mode': mode, 'outcome': outcome, 'conforms': not raw,
           'shapes': {'artifact': 'ontology.shapes', 'semver': compiled.semver, 'ir_hash': compiled.ir_hash},
           'focus': F.compact(focus) if focus is not None else None, 'results': results,
           'n_results': len(raw), 'by_rule': dict(sorted(by_rule.items()))}
    if len(raw) > MAX_RESULTS:
        rep['truncated'] = len(raw) - MAX_RESULTS
    if latency_us is not None:
        rep['latency_us'] = latency_us
    return rep


def note_stats(rep, us):
    with _LOCK:
        STATS['evaluated'] += 1
        lat = STATS['lat_us']
        lat.append(us)
        if len(lat) > 2000:
            del lat[:1000]
        if rep['results']:
            STATS['with_results'] += 1
            for rule, k in by_rule_of(rep).items():
                STATS['by_rule'][rule] = STATS['by_rule'].get(rule, 0) + k


def by_rule_of(rep):
    """Conteo COMPLETO por regla (también lo recortado); reportes viejos sin `by_rule` → desde `results`."""
    if rep.get('by_rule') is not None:
        return dict(rep['by_rule'])
    out = {}
    for r in rep.get('results') or ():
        out[r['rule']] = out.get(r['rule'], 0) + 1
    return out


def stats():
    with _LOCK:
        lat = sorted(STATS['lat_us'])
        out = {k: v for k, v in STATS.items() if k != 'lat_us'}
        out['by_rule'] = dict(sorted(STATS['by_rule'].items()))
    if lat:
        out['latency_us'] = {'p50': lat[len(lat) // 2], 'p95': lat[min(len(lat) - 1, int(len(lat) * 0.95))],
                             'n': len(lat)}
    return out


# ── registro en el libro ─────────────────────────────────────────────────────
def to_ctx_report(rep):
    """GateReport/1 → la forma que consume DecisionCtx.gate (decision_violations)."""
    viols = []
    for r in rep['results']:
        viols.append({'rule_iri': r['rule'], 'severity': r['effective'], 'focus': r['focus'] or rep.get('focus') or '',
                      'value': {'value': r['value'], 'limit': r['limit'], 'declared': r['severity'],
                                'path': r['path'], 'shape': r['shape'], 'message': r['message'], 'gate': rep['gate'],
                                'mode': rep['mode'], 'shapes_semver': rep['shapes'].get('semver')}})
    return {'outcome': rep['outcome'], 'shapes_hash': rep['shapes'].get('ir_hash'), 'violations': viols}


def attach(ctx, rep):
    """A la decisión en curso: violaciones + blob con el reporte completo + índice en el manifiesto."""
    ctx.gate(to_ctx_report(rep))
    sha = ctx.blob('gate_report', rep, retention='legal' if ctx.durability == 'sync' else 'standard_90d')
    ctx.extra.setdefault('gate_reports', []).append(
        {'gate': rep['gate'], 'outcome': rep['outcome'], 'mode': rep['mode'], 'ir_hash': rep['shapes'].get('ir_hash'),
         'n': len(rep['results']), 'blob': sha})


def record(rep, session=None):
    """Sin resultados no se registra nada. Con decisión en curso (y sin escribir aún) → a esa decisión; si no,
    a la cola de la transacción (`session.info['kh_gate_pending']`) que se escribe al confirmar; sin sesión →
    una decisión audit.gates ya mismo (async: nunca lanza)."""
    if not rep or not rep['results']:
        return
    try:
        from core import decisions
        ctx = decisions.current()
        if ctx is not None and not ctx.recorded:
            attach(ctx, rep)
            with _LOCK:
                STATS['recorded'] += 1
            return
        if session is not None:
            session.info.setdefault('kh_gate_pending', []).append(rep)
            return
        write_audit([rep])
    except Exception as e:  # noqa: BLE001
        with _LOCK:
            STATS['record_errors'] += 1
            STATS['last_error'] = f'{type(e).__name__}: {str(e)[:160]}'
        log.warning('gates: no se registró el reporte %s (%s)', rep.get('gate'), type(e).__name__)


def write_audit(reports):
    """UNA decisión `audit.gates` (system:gates, async) con todos los reportes de una transacción sin decisión."""
    reports = [r for r in reports if r and r['results']]
    if not reports:
        return None
    from core import decisions, identity
    ctx = decisions.DecisionCtx('audit.gates', identity.system('gates'), durability='async',
                                subject={'gates': sorted({r['gate'] for r in reports}),
                                         'focus': [r['focus'] for r in reports[:50]]})
    for r in reports:
        attach(ctx, r)
    by_rule = {}
    for r in reports:
        for rule, k in by_rule_of(r).items():
            by_rule[rule] = by_rule.get(rule, 0) + k
    # el libro guarda hasta 200 filas de violaciones por decisión; el CONTEO completo por regla va en la salida
    ctx.output = {'reports': len(reports),
                  'results': sum(r.get('n_results', len(r['results'])) for r in reports),
                  'by_rule': dict(sorted(by_rule.items())), 'mode': reports[0]['mode']}
    did = decisions.record(None, ctx, status='recorded')
    with _LOCK:
        STATS['recorded'] += len(reports)
    return did


# ── 🩺 «Puertas»: 7 días de avisos en sombra (paso 11: para decidir si activar el bloqueo) ──────────────────────
_SUMMARY_CACHE = {'at': 0.0, 'key': None, 'data': None}


def shadow_summary(days=7, engine=None, fresh=False):
    """Por regla, en los últimos `days` días: cuántos avisos, en qué puerta, con qué severidad DECLARADA, y cuántas
    escrituras se habrían BLOQUEADO con policy.gates@2.0.0 (declarada 'block' en una puerta de block_gates).
    {'days', 'total', 'would_block', 'decisions_would_block', 'rules': [{rule, gate, declared, n, decisions, last}]}.
    Caché 60 s (lo lee el 🩺). Nunca lanza."""
    import time as _t
    key = int(days)
    if not fresh and _SUMMARY_CACHE['data'] is not None and _SUMMARY_CACHE['key'] == key \
            and _t.time() - _SUMMARY_CACHE['at'] < 60:
        return _SUMMARY_CACHE['data']
    out = {'days': key, 'total': 0, 'would_block': 0, 'decisions_would_block': 0, 'rules': []}
    try:
        from sqlalchemy import text
        if engine is None:
            from ontology.db import _get_engine, ontology_available
            if not ontology_available():
                return {**out, 'available': False}
            engine = _get_engine()
        blockable = _blockable_in_v2()
        with engine.connect() as c:
            rows = c.execute(text(
                "SELECT v.rule_iri AS rule, coalesce(v.value->>'gate', '') AS gate, "
                "coalesce(v.value->>'declared', v.severity) AS declared, count(*) AS n, "
                "count(DISTINCT v.decision_id) AS d, max(d.recorded_at) AS last "
                "FROM decision_violations v JOIN decisions d ON d.id = v.decision_id "
                "WHERE d.recorded_at > clock_timestamp() - make_interval(days => :days) "
                "GROUP BY 1, 2, 3 ORDER BY 4 DESC LIMIT 60"), {'days': key}).all()
            wb = c.execute(text(
                "SELECT count(DISTINCT v.decision_id) FROM decision_violations v JOIN decisions d "
                "ON d.id = v.decision_id WHERE d.recorded_at > clock_timestamp() - make_interval(days => :days) "
                "AND coalesce(v.value->>'declared', v.severity) = 'block' AND v.value->>'gate' = ANY(:g)"),
                {'days': key, 'g': sorted(blockable)}).scalar()
        for r in rows:
            item = {'rule': r.rule, 'gate': r.gate or None, 'declared': r.declared, 'n': int(r.n),
                    'decisions': int(r.d), 'last': r.last.isoformat() if r.last else None}
            out['rules'].append(item)
            out['total'] += item['n']
            if item['declared'] == 'block' and item['gate'] in blockable:
                out['would_block'] += item['n']
        out['decisions_would_block'] = int(wb or 0)
        out['available'] = True
    except Exception as e:  # noqa: BLE001
        out['available'] = False
        out['error'] = type(e).__name__
    _SUMMARY_CACHE.update(at=_t.time(), key=key, data=out)
    return out


def _blockable_in_v2():
    """Las puertas que BLOQUEARÍA la versión 2.x de policy.gates disponible (o, si ya rige, la vigente)."""
    import core.gates as G
    try:
        from core import governance
        cur = governance.param('policy.gates', 'block_gates', None)
        if cur:
            return set(cur) & set(G.BLOCKABLE)
        doc = governance.available_artifact('policy.gates', '2.0.0')
        return set(doc['params'].get('block_gates') or ()) & set(G.BLOCKABLE)
    except Exception:  # noqa: BLE001
        return set(G.BLOCKABLE)
