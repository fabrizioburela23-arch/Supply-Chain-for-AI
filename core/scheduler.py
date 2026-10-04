"""core/scheduler.py — tareas periódicas del SERVIDOR (misión de reparación 2026-10-04, R5).

Antes no existía ningún reloj: lo "diario" (calificar predicciones, reanudar
investigaciones diferidas por presupuesto) colgaba del refresco de
capitalizaciones, que solo corre cuando alguien abre el mapa. Aquí hay UN hilo
demonio (gunicorn corre 1 worker) que cada `TICK_S` revisa las tareas
registradas y corre las vencidas, una a una, con try/except y estado visible
(`state()` → /api/research/health y 🩺). Nada aquí llama a la IA.

Uso:
    from core import scheduler
    scheduler.register('nombre', fn, every_s=600)
    scheduler.start()          # idempotente; KHIPU_SCHEDULER=off lo apaga
"""
import logging
import os
import threading
import time
from datetime import datetime, timezone

log = logging.getLogger('khipu')

TICK_S = 30.0
_TASKS = {}
_LOCK = threading.Lock()
_THREAD = [None]


def _iso(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec='seconds') if ts else None


def register(name, fn, every_s, run_at_start=True):
    """Registra (o reemplaza) una tarea. run_at_start: la primera pasada la corre."""
    with _LOCK:
        _TASKS[name] = {'fn': fn, 'every_s': max(5.0, float(every_s)), 'last': 0.0 if run_at_start else time.time(),
                        'runs': 0, 'errors': 0, 'last_ok': None, 'last_error': None, 'last_result': None,
                        'last_ms': None}


def tick(now=None):
    """Una pasada: corre las tareas vencidas (testable, sin hilo)."""
    now = time.time() if now is None else now
    with _LOCK:
        due = [(n, t) for n, t in _TASKS.items() if now - t['last'] >= t['every_s']]
    ran = []
    for name, t in due:
        t0 = time.time()
        try:
            res = t['fn']()
            with _LOCK:
                t.update(last=now, runs=t['runs'] + 1, last_ok=now, last_error=None, last_result=res,
                         last_ms=int((time.time() - t0) * 1000))
        except Exception as e:  # noqa: BLE001 — una tarea rota no detiene a las demás
            with _LOCK:
                t.update(last=now, errors=t['errors'] + 1, last_error=f'{type(e).__name__}: {str(e)[:160]}',
                         last_ms=int((time.time() - t0) * 1000))
            log.warning('scheduler %s: %s', name, type(e).__name__)
        ran.append(name)
    return ran


def state():
    with _LOCK:
        return {n: {'every_s': t['every_s'], 'runs': t['runs'], 'errors': t['errors'],
                    'last_ok': _iso(t['last_ok']), 'last_error': t['last_error'], 'last_result': t['last_result'],
                    'last_ms': t['last_ms']} for n, t in _TASKS.items()}


def enabled():
    return (os.getenv('KHIPU_SCHEDULER') or 'on').lower() not in ('off', '0', 'false', 'no')


def _loop():
    while True:
        try:
            tick()
        except Exception as e:  # noqa: BLE001
            log.warning('scheduler loop: %s', type(e).__name__)
        time.sleep(TICK_S)


def start():
    """Arranca el hilo (una vez). Devuelve True si quedó corriendo."""
    if not enabled():
        return False
    with _LOCK:
        t = _THREAD[0]
        if t is not None and t.is_alive():
            return True
        t = threading.Thread(target=_loop, name='khipu-scheduler', daemon=True)
        _THREAD[0] = t
        t.start()
        return True


def running():
    t = _THREAD[0]
    return bool(t is not None and t.is_alive())


def _reset():
    """Solo para tests."""
    with _LOCK:
        _TASKS.clear()
