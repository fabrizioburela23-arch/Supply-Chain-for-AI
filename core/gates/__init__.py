"""core/gates — PUERTAS de validación de la ontología (docs/INFRA_OPERATIVA.md §3; paso 10: MODO SOMBRA).

SHACL es la FUENTE de las reglas (governance/shapes/*.ttl), no el motor en vivo: scripts/build_shapes.py las
compila a governance/shapes/compiled.ir.json (artefacto `ontology.shapes` del registro de gobernanza) y aquí
corren validadores Python de 0,01-0,3 ms. pySHACL + rdflib solo existen en requirements-dev.txt (oráculo de CI).

    focus.py   un mapeo a grafo foco por puerta (el MISMO alimenta al evaluador y a pySHACL)
    rules.py   la impl Python de cada restricción SPARQL (registradas por IRI)
    engine.py  IR → validadores; índice del foco; semántica SHACL Core
    report.py  GateReport/1 + registro en el libro (decision_violations)

Dónde corren (todas síncronas, en el mismo proceso; §3.4):
    G1      ontology/service.apply_event, tras _materialize (vínculo, objeto, factor: ESTADO RESULTANTE)
    G2      ontology/actions.execute_action, antes del handler (acción + principal)
    G-PROP  ontology/agents.run_agents, al crear la propuesta (reporte adjunto a proposed_actions.gate_report)
    G-BULK  ontology/bulk_import.import_links_bulk, por lote
    G8      core/decisions.record (meta-puerta del libro)

Modo (artefacto `policy.gates.mode`): 'shadow' = TODO solo avisa y queda registrado (no se rechaza nada).
Paso 11: 'block' (policy.gates@2.0.0, `"activation": "pin"`: SOLO Fabrizio lo activa con su PIN) bloquea en las
puertas de `policy.gates.block_gates` (G1 vínculo/objeto/factor, G2 acción, G-PROP, G-BULK): un resultado efectivo
'block' lanza `GateViolation` (ValueError, code='gate_violation', mensaje ES/EN de la primera regla, GateReport/1
completo) DESPUÉS de dejar el reporte en la decisión en curso — el libro la registra 'blocked' y la API responde 422.
Las demás puertas (órdenes G3, comité G5, libro G8) siguen en SOMBRA aunque el modo sea 'block' (esperan BRECHAS #1).
`KHIPU_GATES=off` es solo un interruptor de emergencia (no cambia ninguna regla; el 🩺 lo muestra). Nunca IA.
En sombra nunca lanzan.
"""
import logging
import os
import time

log = logging.getLogger('khipu')
_INSTALLED = [False]
BLOCKABLE = ('ontology.g1.link', 'ontology.g1.object', 'ontology.g1.factor', 'ontology.g2.action', 'ontology.g_prop',
             'ontology.g_bulk')


class GateViolation(ValueError):
    """Una escritura no conforme en una puerta que BLOQUEA (paso 11). `report` = GateReport/1 completo."""
    code = 'gate_violation'

    def __init__(self, report):
        self.report = report
        first = next((r for r in (report.get('results') or []) if r.get('effective') == 'block'), None) or {}
        msg = first.get('message') or {}
        n = sum(1 for r in (report.get('results') or []) if r.get('effective') == 'block')
        more_es = f' (+{n - 1} regla(s) más)' if n > 1 else ''
        more_en = f' (+{n - 1} more rule(s))' if n > 1 else ''
        self.error_es = (msg.get('es') or first.get('rule') or 'regla de la ontología') + more_es
        self.error_en = (msg.get('en') or first.get('rule') or 'ontology rule') + more_en
        super().__init__(f'Bloqueado por la puerta {report.get("gate")}: {self.error_es}')

    def payload(self, decision_id=None):
        return {'code': self.code, 'error': f'Bloqueado: {self.error_es}', 'error_en': f'Blocked: {self.error_en}',
                'report': self.report, 'decision_id': decision_id}


def mode():
    if (os.getenv('KHIPU_GATES') or '').strip().lower() in ('off', '0', 'false', 'no'):
        return 'off'
    try:
        from core import governance
        m = governance.param('policy.gates', 'mode')
    except Exception:  # noqa: BLE001
        m = 'shadow'
    # paso 11: 'block' solo si el release VIGENTE lo pide (policy.gates@2.0.0, activado con PIN); lo demás = sombra
    return 'off' if m == 'off' else ('block' if m == 'block' else 'shadow')


def mode_for(gate):
    """El modo que rige en UNA puerta: 'block' solo en las de policy.gates.block_gates (nunca órdenes/comité/libro)."""
    m = mode()
    if m != 'block':
        return m
    try:
        from core import governance
        allowed = set(governance.param('policy.gates', 'block_gates', ()) or ()) & set(BLOCKABLE)
    except Exception:  # noqa: BLE001
        allowed = set()
    return 'block' if gate in allowed else 'shadow'


def blocks(rep):
    return bool(rep) and rep.get('mode') == 'block' and rep.get('outcome') == 'block'


def evaluate(gate, triples, focus=None):
    """GateReport/1 de un grafo foco (o None si las puertas están apagadas o no disponibles)."""
    from core.gates import engine, report
    m = mode_for(gate)
    if m == 'off':
        return None
    comp = engine.load()
    if comp is None:
        return None
    t0 = time.perf_counter()
    raw = engine.run(comp, triples)
    try:   # paso 25: formas PROPUESTAS en sombra junto a las vigentes (cola acotada, se evalúa en otro hilo)
        from core import governance_shadow
        governance_shadow.tap(gate, triples, raw)
    except Exception:  # noqa: BLE001
        pass
    from core import governance
    try:
        overrides = governance.param('policy.gates', 'severity_overrides') or {}
    except Exception:  # noqa: BLE001
        overrides = {}
    rep = report.build(gate, raw, comp, m, overrides, focus=focus)
    us = int((time.perf_counter() - t0) * 1e6)
    rep['latency_us'] = us
    report.note_stats(rep, us)
    report.capture_focus(rep, triples)     # paso 24: el grafo foco queda con la decisión en curso (replay)
    return rep


def check(gate, builder, *args, session=None, **kw):
    """Arma el foco con `builder(*args, **kw)` → (tripletas, foco), evalúa y REGISTRA. En sombra nunca lanza; en una
    puerta que BLOQUEA (paso 11) lanza GateViolation después de registrar el reporte."""
    try:
        triples, focus = builder(*args, **kw)
        rep = evaluate(gate, triples, focus)
        if rep is not None:
            from core.gates import report
            report.record(rep, session=session)
            if blocks(rep):
                raise GateViolation(rep)
        return rep
    except GateViolation:
        raise
    except Exception as e:  # noqa: BLE001 — vigilar nunca tumba una escritura
        from core.gates import report
        with report._LOCK:
            report.STATS['eval_errors'] += 1
            report.STATS['last_error'] = f'{gate}: {type(e).__name__}: {str(e)[:160]}'
        log.warning('gates: %s no evaluó (%s)', gate, type(e).__name__)
        return None


UNCHANGED = object()           # "este evento no cambió el objeto" (p. ej. un vínculo 'affects' de un factor)


def defer_object(session, object_id, prev_type, prev_props, touches):
    """G1 de objetos/factores sobre el estado FINAL: anota el objeto con su estado previo al PRIMER evento."""
    if session is None or not object_id or mode() == 'off':
        return
    bag = session.info.setdefault('kh_gate_defer', {})
    cur = bag.get(object_id)
    if cur is None:
        bag[object_id] = {'prev_type': prev_type, 'prev_props': prev_props, 'touches': bool(touches)}
    else:
        if cur['prev_type'] is UNCHANGED and prev_type is not UNCHANGED:
            cur['prev_type'], cur['prev_props'] = prev_type, prev_props
        cur['touches'] = cur['touches'] or bool(touches)


def flush_deferred(session):
    """Evalúa los objetos/factores anotados (estado final). Lo llaman core/decisions al cerrar una decisión y el
    gancho before_commit para lo que quede. Nunca lanza."""
    if session is None:
        return
    bag = session.info.pop('kh_gate_defer', None)
    if not bag:
        return
    try:
        from ontology.models import ObjectRecord

        from core.gates import focus as _gf
        for oid, st in bag.items():
            obj = session.get(ObjectRecord, oid)
            if obj is None:
                continue
            pt = None if st['prev_type'] is UNCHANGED else st['prev_type']
            pp = None if st['prev_props'] is UNCHANGED else st['prev_props']
            if st['prev_type'] is not UNCHANGED:
                check('ontology.g1.object', _gf.gather_object, obj, pt, session=session)
            if obj.type == 'Factor':
                check('ontology.g1.factor', _gf.gather_factor, session, obj, pp, st['touches'], session=session)
    except GateViolation:
        raise
    except Exception as e:  # noqa: BLE001
        log.warning('gates: diferidos no evaluados (%s)', type(e).__name__)


def _before_commit(session):
    flush_deferred(session)


def _after_commit(session):
    pend = session.info.pop('kh_gate_pending', None)
    if pend:
        try:
            from core.gates import report
            report.write_audit(pend)
        except Exception as e:  # noqa: BLE001
            log.warning('gates: audit.gates no escrito (%s)', type(e).__name__)


def _after_rollback(session):
    # la transacción se deshizo: lo que se intentó escribir NO quedó; el aviso tampoco (sombra = estado real)
    session.info.pop('kh_gate_pending', None)
    session.info.pop('kh_gate_defer', None)


def install():
    """Ganchos de Session (una vez por proceso): al confirmar se escriben los reportes sin decisión en curso."""
    if _INSTALLED[0]:
        return
    from sqlalchemy import event
    from sqlalchemy.orm import Session
    event.listen(Session, 'before_commit', _before_commit)
    event.listen(Session, 'after_commit', _after_commit)
    event.listen(Session, 'after_rollback', _after_rollback)
    _INSTALLED[0] = True


def status():
    from core.gates import engine, report
    if mode() != 'off':
        engine.load()           # compila el IR del release vigente si aún no (o si cambió)
    st = engine.state()
    st['mode'] = mode()
    st['stats'] = report.stats()
    return st
