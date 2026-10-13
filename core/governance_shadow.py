"""core/governance_shadow.py — FORMAS PROPUESTAS EN SOMBRA junto a las vigentes (docs/INFRA_OPERATIVA.md §5.3; paso 25).

Cuando existe una versión de `ontology.shapes` MÁS NUEVA que la vigente (archivo del repositorio o propuesta
registrada), cada evaluación de una puerta (core/gates.evaluate) deja su grafo foco y su resultado crudo en una COLA
ACOTADA (`tap`: un append, 0 ms en el camino del usuario). Un hilo aparte corre ese mismo foco con las formas
propuestas y cuenta la DIFERENCIA de violaciones (nuevas / que desaparecen, por regla). La regresión de gobernanza
(core/governance_flow.regress) y el 🩺 ⚖ Gobernanza leen `stats(semver)` antes de activar.

Nunca bloquea ni cambia un veredicto: solo cuenta. Nunca IA. Sin candidata, `tap` vuelve al instante.
"""
import collections
import logging
import threading
import time

log = logging.getLogger('khipu')

QUEUE_MAX = 500
SAMPLES = 5
_LOCK = threading.Lock()
_Q = collections.deque(maxlen=QUEUE_MAX)
_EV = threading.Event()
_STATE = {'semver': None, 'comp': None, 'ir_hash': None, 'armed_at': None, 'error': None, 'thread': None,
          'checked_for': None}
_STATS = {}                     # semver → {evaluations, with_diff, new_by_rule, gone_by_rule, samples, dropped}


def _candidate():
    """(semver, ir) de la versión de ontology.shapes más nueva que la vigente, o (None, None)."""
    from core import governance
    best = None
    for p in governance.proposals():
        if p['id'] == 'ontology.shapes' and p.get('newer'):
            if best is None or governance.semver_key(p['semver']) > governance.semver_key(best):
                best = p['semver']
    if best is None:
        return None, None
    doc = governance.available_artifact('ontology.shapes', best)
    return best, doc['params']


def arm(force=False):
    """(Re)carga la candidata si cambió el release o las propuestas. Barato; lo llama el reloj de gobernanza."""
    from core import governance
    try:
        key = (governance.active().release_hash, tuple(sorted(governance.registered())))
    except Exception:  # noqa: BLE001
        key = None
    if not force and key is not None and key == _STATE['checked_for']:
        return state()
    try:
        sv, params = _candidate()
        if sv is None:
            with _LOCK:
                _STATE.update(semver=None, comp=None, ir_hash=None, error=None, checked_for=key)
            return state()
        if sv == _STATE['semver'] and _STATE['comp'] is not None:
            _STATE['checked_for'] = key
            return state()
        from core.gates import engine
        ir = params['ir']
        if engine.ir_canonical_hash(ir) != params.get('ir_hash') or ir.get('ir_hash') != params.get('ir_hash'):
            raise RuntimeError('el IR propuesto no coincide con su hash')
        comp = engine.compile_ir(ir)
        comp.semver = sv
        with _LOCK:
            _STATE.update(semver=sv, comp=comp, ir_hash=params.get('ir_hash'), armed_at=time.time(), error=None,
                          checked_for=key)
            _STATS.setdefault(sv, _empty())
        _ensure_worker()
    except Exception as e:  # noqa: BLE001
        with _LOCK:
            _STATE.update(comp=None, error=f'{type(e).__name__}: {str(e)[:160]}', checked_for=key)
        log.warning('governance_shadow: candidata no cargada (%s)', _STATE['error'])
    return state()


def _empty():
    return {'evaluations': 0, 'with_diff': 0, 'new_by_rule': {}, 'gone_by_rule': {}, 'samples': [], 'dropped': 0,
            'errors': 0}


def tap(gate, triples, raw):
    """Gancho de core/gates.evaluate: encola (gate, foco, resultado vigente) si hay candidata. O(1)."""
    if _STATE['comp'] is None:
        return
    if len(_Q) >= QUEUE_MAX:
        st = _STATS.get(_STATE['semver'])
        if st is not None:
            st['dropped'] += 1
    _Q.append((gate, triples, raw, _STATE['semver']))
    _EV.set()


def _vkey(r):
    focus, _kind, spec, value, _lim = r
    return (spec.get('rule') if isinstance(spec, dict) else str(spec), str(focus), str(value)[:80])


def _process(item):
    from core.gates import engine
    gate, triples, raw, sv = item
    comp = _STATE['comp']
    if comp is None or comp.semver != sv:
        return
    st = _STATS.setdefault(sv, _empty())
    try:
        cand = engine.run(comp, triples)
    except Exception:  # noqa: BLE001
        st['errors'] += 1
        return
    a, b = {_vkey(r) for r in raw}, {_vkey(r) for r in cand}
    new, gone = b - a, a - b
    with _LOCK:
        st['evaluations'] += 1
        if new or gone:
            st['with_diff'] += 1
            for k in new:
                st['new_by_rule'][k[0]] = st['new_by_rule'].get(k[0], 0) + 1
            for k in gone:
                st['gone_by_rule'][k[0]] = st['gone_by_rule'].get(k[0], 0) + 1
            if len(st['samples']) < SAMPLES:
                st['samples'].append({'gate': gate, 'new': sorted(k[0] for k in new)[:5],
                                      'gone': sorted(k[0] for k in gone)[:5], 'at': time.time()})


def drain(max_items=None):
    """Procesa la cola en ESTE hilo (lo usa el hilo de fondo y las pruebas). Devuelve cuántos procesó."""
    n = 0
    while _Q and (max_items is None or n < max_items):
        try:
            item = _Q.popleft()
        except IndexError:
            break
        _process(item)
        n += 1
    return n


def _ensure_worker():
    t = _STATE.get('thread')
    if t is not None and t.is_alive():
        return

    def loop():
        while True:
            _EV.wait(30)
            _EV.clear()
            try:
                drain()
            except Exception:  # noqa: BLE001
                pass
    t = threading.Thread(target=loop, name='gov-shapes-shadow', daemon=True)
    _STATE['thread'] = t
    t.start()


def stats(semver=None):
    sv = semver or _STATE['semver']
    with _LOCK:
        st = dict(_STATS.get(sv) or _empty())
        st['new_by_rule'] = dict(st['new_by_rule'])
        st['gone_by_rule'] = dict(st['gone_by_rule'])
        st['samples'] = list(st['samples'])
    st.update(semver=sv, armed=_STATE['semver'] == sv and _STATE['comp'] is not None, queued=len(_Q),
              armed_at=_STATE['armed_at'] if _STATE['semver'] == sv else None)
    return st


def state():
    return {'semver': _STATE['semver'], 'armed': _STATE['comp'] is not None, 'ir_hash': _STATE['ir_hash'],
            'error': _STATE['error'], 'queued': len(_Q)}


def reset_for_tests():
    with _LOCK:
        _Q.clear()
        _STATS.clear()
        _STATE.update(semver=None, comp=None, ir_hash=None, armed_at=None, error=None, checked_for=None)
