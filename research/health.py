"""research/health.py — "¿puedo investigar ahora?" en UNA foto (R6, misión de reparación).

Sin red, sin PIN, sin IA: proveedores (clave + pausa del corta-circuito),
cupos del semáforo, cola de investigación, presupuesto, reloj del servidor,
última evaluación de predicciones y últimos errores de proveedor (redactados).
La usan GET /api/research/health, el bloque `research` de /api/health, la
herramienta MCP get_research_health y el 🩺.
"""
import os
import time
from datetime import datetime, timezone

_CACHE = {'ts': 0.0, 'data': None}
CACHE_S = 5.0


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _providers():
    from core import ai
    out = {}
    circ = ai.ai_circuit_state()
    for name, (has_key, _fn) in ai._AI_PROVIDERS.items():
        st = circ.get(name) or {'open': False}
        out[name] = {'configured': bool(has_key()), 'available': ai.provider_available(name),
                     'circuit': st}
    return out


def _slots():
    from core import ai
    mx, reserve = int(ai.AI_MAX_CONCURRENCY), int(ai.AI_INTERACTIVE_RESERVE)
    bg_max = max(1, mx - reserve)
    try:
        in_use = mx - int(ai._AI_SEM._value)          # BoundedSemaphore: cupos libres
        bg_in_use = bg_max - int(ai._AI_BG_SEM._value)
    except Exception:  # noqa: BLE001
        in_use = bg_in_use = None
    return {'max': mx, 'interactive_reserve': reserve, 'bg_max': bg_max, 'in_use': in_use, 'bg_in_use': bg_in_use,
            'busy_wait_s': float(ai.AI_BUSY_WAIT_S)}


def _queue_and_budget():
    from research import runner
    q = runner.research_queue_state()
    budget = {'daily_usd': runner.daily_budget(), 'spent_today_usd': None, 'remaining_usd': None,
              'exhausted': None, 'note': None}
    db_counts = None
    try:
        from ontology.db import ontology_available, session_scope
        if ontology_available():
            from sqlalchemy import func

            from research.models import ResearchJob
            with session_scope() as s:
                spent = round(runner.spent_today(s), 4)
                budget.update(spent_today_usd=spent, remaining_usd=round(max(0.0, budget['daily_usd'] - spent), 4),
                              exhausted=spent >= budget['daily_usd'])
                rows = (s.query(ResearchJob.status, func.count()).group_by(ResearchJob.status).all())
                db_counts = {st: int(n) for st, n in rows}
        else:
            budget['note'] = 'sin base de datos: el gasto de investigación no se puede leer / no database'
    except Exception as e:  # noqa: BLE001
        budget['note'] = f'no se pudo leer el gasto: {type(e).__name__}'
    q['db_counts'] = db_counts
    return q, budget


def _ai_usage_limits():
    try:
        from core import ai_usage
        st = ai_usage.settings()
        return {'daily_usd': st.get('daily_usd'), 'monthly_usd': st.get('monthly_usd'),
                'blocked_providers': list(st.get('blocked_providers') or [])}
    except Exception:  # noqa: BLE001
        return None


def _scheduler():
    try:
        from core import scheduler
        return {'running': scheduler.running(), 'enabled': scheduler.enabled(), 'tasks': scheduler.state()}
    except Exception:  # noqa: BLE001
        return None


def _outcomes():
    try:
        from core import live_caps
        st = dict(getattr(live_caps, '_OUT_STATE', {}) or {})
        return {'last_day': st.get('day'), 'last_result': st.get('last'), 'error': st.get('error')}
    except Exception:  # noqa: BLE001
        return None


def _last_errors():
    try:
        from core import ai
        return list(ai.last_errors())
    except Exception:  # noqa: BLE001
        return []


def _hint(providers, budget, queue):
    avail = [p for p, v in providers.items() if v['available']]
    paused = [f"{p} ({v['circuit'].get('reason_es')})" for p, v in providers.items()
              if v['configured'] and v['circuit'].get('open')]
    paused_en = [f"{p} ({v['circuit'].get('reason_en')})" for p, v in providers.items()
                 if v['configured'] and v['circuit'].get('open')]
    if not any(v['configured'] for v in providers.values()):
        return False, ('No hay ningún proveedor de IA con clave en Railway: no se puede investigar.',
                       'No AI provider has a key on Railway: research is not possible.')
    if not avail:
        return False, ('Todos los proveedores de IA están en pausa: ' + ', '.join(paused) + '. Revisa 🩺 Sistema → IA.',
                       'All AI providers are paused: ' + ', '.join(paused_en) + '. Check 🩺 System → AI.')
    if budget.get('exhausted'):
        return False, (f"Presupuesto diario de investigación agotado (≈${budget['spent_today_usd']:.2f} de "
                       f"${budget['daily_usd']:.2f}): los pedidos nuevos quedan diferidos hasta mañana 00:05 UTC.",
                       f"Daily research budget used up (≈${budget['spent_today_usd']:.2f} of ${budget['daily_usd']:.2f}): "
                       'new requests are deferred until tomorrow 00:05 UTC.')
    es = f"Listo para investigar con {', '.join(avail)}"
    en = f"Ready to research with {', '.join(avail)}"
    if paused:
        es += ' (en pausa: ' + ', '.join(paused) + ')'
        en += ' (paused: ' + ', '.join(paused_en) + ')'
    if queue.get('jobs_queued') or queue.get('jobs_running'):
        es += f" · cola: {queue.get('jobs_queued', 0)} en espera, {queue.get('jobs_running', 0)} en curso"
        en += f" · queue: {queue.get('jobs_queued', 0)} waiting, {queue.get('jobs_running', 0)} running"
    return True, (es + '.', en + '.')


def research_health(fresh=False):
    """Dict serializable. Caché CACHE_S segundos (la llaman UI, MCP y /api/health)."""
    now = time.time()
    if not fresh and _CACHE['data'] is not None and now - _CACHE['ts'] < CACHE_S:
        return dict(_CACHE['data'], cached=True)
    providers = _providers()
    queue, budget = _queue_and_budget()
    ok, (hint_es, hint_en) = _hint(providers, budget, queue)
    data = {'ok': ok, 'hint_es': hint_es, 'hint_en': hint_en, 'providers': providers, 'slots': _slots(),
            'queue': queue, 'budget': {'research': budget, 'ai_usage_limits': _ai_usage_limits()},
            'scheduler': _scheduler(), 'outcomes': _outcomes(), 'last_errors': _last_errors(),
            'env': {'RESEARCH_PARALLEL': os.getenv('RESEARCH_PARALLEL'),
                    'RESEARCH_JOB_CONCURRENCY': os.getenv('RESEARCH_JOB_CONCURRENCY'),
                    'RESEARCH_MODEL_DEFAULT': os.getenv('RESEARCH_MODEL_DEFAULT'),
                    'AI_ORDER': os.getenv('AI_ORDER')},
            'as_of': _now_iso(), 'cached': False}
    _CACHE.update(ts=now, data=data)
    return data


def health_brief():
    """Resumen chico para /api/health (sin base, nunca lanza)."""
    try:
        h = research_health()
        return {'ok': h['ok'], 'hint_es': h['hint_es'], 'hint_en': h['hint_en'],
                'providers_available': [p for p, v in h['providers'].items() if v['available']],
                'providers_paused': [p for p, v in h['providers'].items() if v['circuit'].get('open')],
                'jobs_queued': h['queue'].get('jobs_queued'), 'jobs_running': h['queue'].get('jobs_running'),
                'budget_exhausted': h['budget']['research'].get('exhausted'),
                'scheduler_running': (h.get('scheduler') or {}).get('running')}
    except Exception as e:  # noqa: BLE001
        return {'ok': None, 'error': type(e).__name__}
