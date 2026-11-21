"""ontology/curation_loop.py — el LATIDO del servidor para que la ontología se mantenga sola (2026-11-21).

Antes el ciclo de agentes (ontology.agents.auto_cycle: leer → proponer → curar → aplicar lo seguro) solo corría cuando
alguien tenía la app abierta (engine/live.js, cada 10 min). Si nadie entraba, el grafo se quedaba quieto.

Ahora un hilo del servidor dispara el MISMO ciclo cada ONTOLOGY_AUTO_MIN minutos (20), por el mismo camino que el
navegador (ontology.api._try_start_cycle: un solo ciclo a la vez, como mucho uno cada 5 min entre los dos). No es el
reloj de core/scheduler.py a propósito: ese reloj nunca llama a la IA, y el ciclo sí (Lector de hechos, resúmenes).
Con 1 worker de gunicorn hay un solo hilo. ONTOLOGY_AUTO=off lo apaga; KHIPU_SCHEDULER=off (pruebas) tampoco arranca.
"""
import logging
import os
import threading
import time

log = logging.getLogger('khipu')
_STARTED = {'on': False, 'beats': 0, 'last': None}
_LOCK = threading.Lock()
FIRST_DELAY_S = 120


def interval_s():
    try:
        return max(5, int(os.getenv('ONTOLOGY_AUTO_MIN') or 20)) * 60
    except ValueError:
        return 20 * 60


def enabled():
    off = ('off', '0', 'false', 'no')
    return ((os.getenv('ONTOLOGY_AUTO') or 'on').strip().lower() not in off
            and (os.getenv('KHIPU_SCHEDULER') or 'on').strip().lower() not in off)


def beat():
    """Una vuelta: pide al ciclo de la ontología que corra (si ya corre o corrió hace poco, no hace nada)."""
    try:
        from ontology.db import ontology_available
        if not ontology_available():
            return False
        from ontology.api import _try_start_cycle
        started = _try_start_cycle(False)
        _STARTED['beats'] += 1
        _STARTED['last'] = time.time()
        return started
    except Exception as e:  # noqa: BLE001 — el latido nunca tumba el servidor
        log.warning('ontología: latido (%s)', type(e).__name__)
        return False


def _loop():
    time.sleep(FIRST_DELAY_S)
    while True:
        beat()
        time.sleep(interval_s())


def start():
    """Idempotente. Devuelve True si arrancó el hilo ahora."""
    if not enabled():
        return False
    with _LOCK:
        if _STARTED['on']:
            return False
        _STARTED['on'] = True
    threading.Thread(target=_loop, name='ontology-autoloop', daemon=True).start()
    return True


def status():
    return {'enabled': enabled(), 'running': _STARTED['on'], 'beats': _STARTED['beats'], 'last_beat': _STARTED['last'],
            'interval_min': interval_s() // 60}
