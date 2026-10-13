"""core/ai_calls.py — registro append-only de CADA pedido a la IA (docs/INFRA_OPERATIVA.md §2.6, paso 21; GV-11).

El ÚNICO que llama a `begin/finish/submit` es core/ai.py (`_ai_complete_raw` y el guardián de `_ai_complete`):
así "qué le preguntamos a la IA, qué modelo REAL contestó, cuánto costó y qué dijo el guardián de cifras" tiene
una sola puerta (tests/test_ai_calls.py lo vigila con un grep).

Una fila de `ai_calls` (ontology/ledger_models.AICall) por pedido de texto (la cascada entera: el proveedor
que contestó, o el fallo). Guarda:
  · prompt_sha / system_sha (sha256 del texto UTF-8) y los TEXTOS como blobs direccionados por hash en
    `decision_blobs` (system, entrada y salida por separado: el system se repite y se guarda UNA vez);
  · retención: 'legal' si la llamada ocurrió dentro de una decisión sync (comité, investigación…); si no
    (chat, qué-pasaría-si, insights) 'standard_90d' (D3). La purga es el paso 26 (aún no corre);
  · tokens (incluida la caché leída/escrita por separado, L4-06), costo con los precios de core/ai_usage, latencia,
    modelo real, nivel, función y QUIÉN como hash (nunca en claro), veredicto del guardián y `decision_id`
    cuando la llamada corre dentro de una decisión (contextvar; sin FK: las decisiones async se escriben después).

NUNCA agrega latencia al usuario: la fila se arma en memoria y un hilo la escribe en lote (cada ~1 s; tope 5.000
en cola: lo que no cabe se cuenta en STATS['dropped'] y el 🩺 lo muestra). Sin DATABASE_URL no hace nada.
Append-only (kh_append_only) y sellada por core/ledger (cadena de hashes). Nunca IA aquí.
"""
import contextvars
import hashlib
import logging
import threading
import time
import uuid
import zlib
from collections import deque
from contextlib import contextmanager
from datetime import datetime, timezone

log = logging.getLogger('khipu')

QUEUE_MAX = 5000
FLUSH_EVERY_S = 1.0
BATCH = 200

# decisión a la que se atribuyen las llamadas de IA de este contexto: {'decision_id': str, 'ids': list|None}
_ATTR = contextvars.ContextVar('kh_ai_attr', default=None)
_TLS = threading.local()             # retención de filas mientras el guardián decide su veredicto
_LOCK = threading.Lock()
_FLUSH_LOCK = threading.Lock()       # un lote a la vez (el hilo escritor y flush() de las pruebas)
_Q = deque()
_STATE = {'writer': None, 'wake': threading.Event()}
STATS = {'queued': 0, 'written': 0, 'dropped': 0, 'errors': 0, 'last_error': None, 'last_flush_ms': None,
         'last_flush_at': None}


def _db_on():
    try:
        from ontology.db import ontology_available
        return bool(ontology_available())
    except Exception:  # noqa: BLE001
        return False


def sha_text(s):
    return hashlib.sha256(('' if s is None else str(s)).encode('utf-8')).hexdigest()


# ── atribución a una decisión ────────────────────────────────────────────────
@contextmanager
def attribute(decision_id, collect=None, durability='async'):
    """Las llamadas de IA de este bloque (y de los hilos que lo hereden vía core/ai_usage.bind) llevan este
    `decision_id`; si `collect` es una lista, se le agregan los ids de ai_calls (la decisión los cita)."""
    tok = _ATTR.set({'decision_id': str(decision_id) if decision_id else None, 'durability': durability,
                     'ids': collect})
    try:
        yield collect
    finally:
        _ATTR.reset(tok)


def snapshot():
    """Lo que un hilo del pool debe heredar (core/ai_usage.bind). Nunca lanza."""
    sd = _scope_decision()          # un decision_scope abierto en ESTE hilo es lo más específico
    if sd:
        return {'decision_id': sd[0], 'durability': sd[1], 'ids': None}
    return _ATTR.get()


@contextmanager
def restore(snap):
    if snap is None:
        yield
        return
    tok = _ATTR.set(snap)
    try:
        yield
    finally:
        _ATTR.reset(tok)


def _scope_decision():
    try:
        from core import decisions
        ctx = decisions.current()
        return (str(ctx.id), ctx.durability) if ctx is not None else None
    except Exception:  # noqa: BLE001
        return None


def _decision_now():
    """(decision_id, retención) de la llamada que empieza: la de `attribute`/`restore` o la del decision_scope
    abierto. Dentro de una decisión sync (comité, investigación…) los blobs son 'legal'; si no, 90 días (D3)."""
    sd = _scope_decision()          # el decision_scope más interno manda sobre la atribución exterior (chat)
    a = {'decision_id': sd[0], 'durability': sd[1]} if sd else _ATTR.get()
    if a is None or not a.get('decision_id'):
        return None, 'standard_90d'
    return a['decision_id'], ('legal' if a.get('durability') == 'sync' else 'standard_90d')


# ── una llamada ──────────────────────────────────────────────────────────────
def begin(system, prompt, *, tier='fast', max_tokens=None, want_json=False, model=None):
    """Arma la fila (en memoria) ANTES de llamar al proveedor. Barato: los sha y los blobs se calculan en el
    hilo escritor."""
    did, retention = _decision_now()
    try:
        from core import ai_usage
        cur = ai_usage.current()
    except Exception:  # noqa: BLE001
        cur = {'feature': None, 'who': None}
    who = cur.get('who')
    try:
        from core.identity import hash_id
        who_h = hash_id(who, 'ai_who') if who else None
    except Exception:  # noqa: BLE001
        who_h = None
    return {'id': uuid.uuid4(), 'started_at': datetime.now(timezone.utc), 't0': time.perf_counter(),
            'system': system or '', 'prompt': prompt or '', 'tier': 'deep' if tier == 'deep' else 'fast',
            'feature': (cur.get('feature') or None) and str(cur['feature'])[:40], 'who_hash': who_h,
            'decision_id': did, 'retention_class': retention,
            'route': {'max_tokens': max_tokens, 'json': bool(want_json), **({'model_req': str(model)[:80]} if model else {})}}


def finish(rec, *, text=None, used=None, acc=None, ok=True, error=None, tried=None):
    """Completa la fila con lo que pasó (texto, modelo real, tokens/costo medidos por core/ai_usage.meter)."""
    acc = acc or {}
    rec['latency_ms'] = int((time.perf_counter() - rec.pop('t0', time.perf_counter())) * 1000)
    rec['ok'] = bool(ok)
    rec['output'] = None if text is None else str(text)
    used = str(used or '')
    rec['provider'] = (used.split(':', 1)[0] if ':' in used else ('claude' if used.startswith('claude') else None)) \
        if used else None
    rec['model'] = used[:80] or None
    rec['tokens_in'] = int(acc.get('raw_in') or acc.get('tokens_in') or 0)
    rec['tokens_out'] = int(acc.get('tokens_out') or 0)
    rec['cache_read_tokens'] = int(acc.get('cache_read') or 0)
    rec['cache_write_tokens'] = int(acc.get('cache_write') or 0)
    rec['cost_usd'] = round(float(acc.get('cost_usd') or 0.0), 6)
    if error is not None:
        rec['error'] = str(error)[:240]
    if tried:
        rec['route']['tried'] = list(tried)[:6]
    return rec


@contextmanager
def held():
    """El guardián de cifras (core/ai._ai_complete) retiene las filas de su bloque para anotarles su veredicto
    antes de encolarlas. Devuelve la lista retenida; al salir (aunque falle) se encolan."""
    prev = getattr(_TLS, 'hold', None)
    _TLS.hold = []
    try:
        yield _TLS.hold
    finally:
        rows, _TLS.hold = _TLS.hold, prev
        for r in rows:
            submit(r)


def submit(rec):
    """Encola la fila (o la retiene si el guardián está mirando). Nunca lanza; nunca bloquea."""
    try:
        hold = getattr(_TLS, 'hold', None)
        if hold is not None:
            hold.append(rec)
            return rec['id']
        a = _ATTR.get()
        if a is not None and isinstance(a.get('ids'), list) and rec.get('decision_id') == a.get('decision_id'):
            a['ids'].append(str(rec['id']))
        if not _db_on():
            return rec['id']
        with _LOCK:
            if len(_Q) >= QUEUE_MAX:
                STATS['dropped'] += 1
                return None
            _Q.append(rec)
            STATS['queued'] += 1
            n = len(_Q)
        _ensure_writer()
        if n >= BATCH:
            _STATE['wake'].set()
        return rec['id']
    except Exception as e:  # noqa: BLE001 — el registro nunca rompe una llamada
        with _LOCK:
            STATS['errors'] += 1
            STATS['last_error'] = type(e).__name__
        return None


# ── escritura en lote ────────────────────────────────────────────────────────
def _blob(blobs, kind, obj, retention):
    from core.decisions import canonical
    b = canonical(obj)
    sha = hashlib.sha256(b).hexdigest()
    cur = blobs.get(sha)
    if cur is None or (retention == 'legal' and cur['retention_class'] != 'legal'):
        blobs[sha] = {'sha256': sha, 'kind': kind, 'body': zlib.compress(b, 6), 'size_bytes': len(b),
                      'retention_class': retention}
    return sha


def _rows(batch):
    blobs, rows = {}, []
    for r in batch:
        ret = r.get('retention_class') or 'standard_90d'
        sys_sha = sha_text(r.get('system'))
        system_blob = _blob(blobs, 'ai_system', {'system': r.get('system') or ''}, ret)
        input_blob = _blob(blobs, 'ai_input', {'prompt': r.get('prompt') or '', 'system_sha': sys_sha,
                                               'system_blob': system_blob}, ret)
        out = r.get('output')
        rows.append({
            'id': r['id'], 'started_at': r['started_at'], 'provider': r.get('provider'), 'model': r.get('model'),
            'tier': r['tier'], 'feature': r.get('feature'), 'who_hash': r.get('who_hash'),
            'prompt_sha': sha_text(r.get('prompt')), 'system_sha': sys_sha, 'system_blob': system_blob,
            'input_blob': input_blob, 'output_sha': sha_text(out) if out is not None else None,
            'output_blob': _blob(blobs, 'ai_output', {'output': out}, ret) if out is not None else None,
            'tokens_in': r.get('tokens_in') or 0, 'tokens_out': r.get('tokens_out') or 0,
            'cache_read_tokens': r.get('cache_read_tokens') or 0, 'cache_write_tokens': r.get('cache_write_tokens') or 0,
            'cost_usd': r.get('cost_usd') or 0.0, 'latency_ms': r.get('latency_ms'), 'ok': bool(r.get('ok')),
            'error': r.get('error'), 'guardian': r.get('guardian'), 'route': r.get('route'),
            'decision_id': uuid.UUID(r['decision_id']) if r.get('decision_id') else None, 'retention_class': ret})
    return list(blobs.values()), rows


def flush(max_rows=None):
    """Escribe lo encolado (una transacción por lote). → filas escritas. Lo usan el hilo escritor y las pruebas."""
    with _FLUSH_LOCK:
        return _flush(max_rows)


def _flush(max_rows=None):
    total = 0
    while True:
        with _LOCK:
            n = min(len(_Q), BATCH if max_rows is None else max(0, max_rows - total))
            batch = [_Q.popleft() for _ in range(n)]
        if not batch:
            return total
        t0 = time.perf_counter()
        try:
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            from ontology.db import session_scope
            from ontology.ledger_models import AICall, DecisionBlob
            blobs, rows = _rows(batch)
            with session_scope() as s:
                if blobs:
                    s.execute(pg_insert(DecisionBlob.__table__).values(blobs).on_conflict_do_nothing())
                s.execute(pg_insert(AICall.__table__).values(rows).on_conflict_do_nothing())
            total += len(rows)
            with _LOCK:
                STATS['written'] += len(rows)
                STATS['last_flush_ms'] = round((time.perf_counter() - t0) * 1000, 2)
                STATS['last_flush_at'] = time.time()
        except Exception as e:  # noqa: BLE001 — base caída: se reintenta una vez más tarde (si cabe)
            with _LOCK:
                STATS['errors'] += 1
                STATS['last_error'] = f'{type(e).__name__}: {str(e)[:160]}'
                retry = [r for r in batch if not r.get('_retried')]
                for r in retry:
                    r['_retried'] = True
                if len(_Q) + len(retry) <= QUEUE_MAX:
                    _Q.extendleft(reversed(retry))
                else:
                    STATS['dropped'] += len(retry)
                STATS['dropped'] += len(batch) - len(retry)
            log.warning('ai_calls: lote no escrito (%s)', type(e).__name__)
            return total
        if max_rows is not None and total >= max_rows:
            return total


def _ensure_writer():
    t = _STATE['writer']
    if t is not None and t.is_alive():
        return
    with _LOCK:
        t = _STATE['writer']
        if t is not None and t.is_alive():
            return

        def loop():
            while True:
                _STATE['wake'].wait(FLUSH_EVERY_S)
                _STATE['wake'].clear()
                try:
                    flush()
                except Exception:  # noqa: BLE001
                    pass
        t = threading.Thread(target=loop, name='ai-calls-writer', daemon=True)
        _STATE['writer'] = t
        t.start()


def stats():
    with _LOCK:
        return dict(STATS, pending=len(_Q))


def _reset_for_tests():
    with _LOCK:
        _Q.clear()
        for k in ('queued', 'written', 'dropped', 'errors'):
            STATS[k] = 0
        STATS['last_error'] = None
