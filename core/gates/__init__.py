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

Modo (artefacto `policy.gates.mode`): 'shadow' = TODO solo avisa y queda registrado (no se rechaza nada); el
paso 11 pasará a bloquear con una versión MAJOR aprobada con PIN. `KHIPU_GATES=off` es solo un interruptor de
emergencia (no cambia ninguna regla; el 🩺 lo muestra). Nunca IA. Nunca lanzan en sombra.
"""
import logging
import os
import time

log = logging.getLogger('khipu')
_INSTALLED = [False]


def mode():
    if (os.getenv('KHIPU_GATES') or '').strip().lower() in ('off', '0', 'false', 'no'):
        return 'off'
    try:
        from core import governance
        m = governance.param('policy.gates', 'mode')
    except Exception:  # noqa: BLE001
        m = 'shadow'
    # paso 10: este código SOLO sabe avisar. Aunque un release pidiera 'enforce', rige la sombra hasta el paso 11.
    return 'off' if m == 'off' else 'shadow'


def evaluate(gate, triples, focus=None):
    """GateReport/1 de un grafo foco (o None si las puertas están apagadas o no disponibles)."""
    from core.gates import engine, report
    m = mode()
    if m == 'off':
        return None
    comp = engine.load()
    if comp is None:
        return None
    t0 = time.perf_counter()
    raw = engine.run(comp, triples)
    from core import governance
    try:
        overrides = governance.param('policy.gates', 'severity_overrides') or {}
    except Exception:  # noqa: BLE001
        overrides = {}
    rep = report.build(gate, raw, comp, m, overrides, focus=focus)
    us = int((time.perf_counter() - t0) * 1e6)
    rep['latency_us'] = us
    report.note_stats(rep, us)
    return rep


def check(gate, builder, *args, session=None, **kw):
    """Arma el foco con `builder(*args, **kw)` → (tripletas, foco), evalúa y REGISTRA. Nunca lanza (sombra)."""
    try:
        triples, focus = builder(*args, **kw)
        rep = evaluate(gate, triples, focus)
        if rep is not None:
            from core.gates import report
            report.record(rep, session=session)
        return rep
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
