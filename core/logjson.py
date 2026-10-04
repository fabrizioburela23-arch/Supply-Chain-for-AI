"""core/logjson.py — O2 (misión de reparación 2026-10-04): logs estructurados.

`LOG_JSON=on` (Railway) → cada línea de log es un JSON con ts/level/logger/msg
+ campos de contexto (job_id, entity, agent) y, en los eventos, proveedor,
modelo, tokens, costo y latencia. Sin la variable NADA cambia: los mensajes de
texto actuales siguen iguales y los eventos estructurados no se emiten.

    from core.logjson import log_context, event
    with log_context(job_id=job.id, entity=job.entity_id):
        ...                                   # toda línea de este hilo lleva esos campos
    event('ai_call', provider='gemini', ms=812, cost_usd=0.0004)

`core.ai_usage.bind` copia el contexto a los hilos del pool de agentes.
"""
import json
import logging
import os
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

_TLS = threading.local()
EVENT_LOGGER = 'khipu.events'
_FIELDS = ('event', 'job_id', 'entity', 'agent', 'provider', 'model', 'feature', 'who', 'tokens_in', 'tokens_out',
           'cost_usd', 'ms', 'ok', 'status', 'seconds', 'error', 'kind')


def enabled():
    return (os.getenv('LOG_JSON') or '').strip().lower() in ('on', '1', 'true', 'yes', 'json')


def current_fields():
    return dict(getattr(_TLS, 'fields', None) or {})


@contextmanager
def log_context(**fields):
    prev = getattr(_TLS, 'fields', None)
    _TLS.fields = dict(prev or {}, **{k: v for k, v in fields.items() if v is not None})
    try:
        yield
    finally:
        _TLS.fields = prev


class JsonFormatter(logging.Formatter):
    def format(self, record):
        d = {'ts': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec='milliseconds'),
             'level': record.levelname, 'logger': record.name, 'msg': record.getMessage()}
        d.update(current_fields())
        for k in _FIELDS:
            v = getattr(record, k, None)
            if v is not None:
                d[k] = v
        if record.exc_info:
            d['exc'] = self.formatException(record.exc_info)[-2000:]
        return json.dumps(d, ensure_ascii=False, default=str)


def configure(root=None):
    """Llamar una vez tras logging.basicConfig. Devuelve True si activó JSON."""
    if not enabled():
        return False
    root = root or logging.getLogger()
    fmt = JsonFormatter()
    if not root.handlers:
        root.addHandler(logging.StreamHandler())
    for h in root.handlers:
        h.setFormatter(fmt)
    return True


def event(name, level=logging.INFO, **fields):
    """Evento estructurado (solo con LOG_JSON=on: en modo texto no ensucia los logs)."""
    if not enabled():
        return
    try:
        logging.getLogger(EVENT_LOGGER).log(level, name, extra=dict(event=name, **{
            k: v for k, v in fields.items() if k in _FIELDS and v is not None}))
    except Exception:  # noqa: BLE001 — un log jamás rompe la llamada
        pass
