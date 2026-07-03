"""ontology/api.py — API REST de la ontología: /api/ontology/*

Prefijo elegido para NO colisionar con /v1/* (que ya es el producto de API
pública monetizado por tiers de Khipu Finance — ver server.py:khipu_auth).

Sigue el patrón de "feature opcional" ya usado con Neo4j: si DATABASE_URL no
está configurada, todas las rutas devuelven 503 con un mensaje claro en vez
de romper el arranque del servidor.
"""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from ontology.db import ontology_available, session_scope
from ontology.service import (
    OntologyError, apply_event, get_object, list_objects, object_links,
    object_history, as_of_graph, diff_graph, _parse_dt, _utcnow,
)

ontology_bp = Blueprint('ontology', __name__, url_prefix='/api/ontology')


def _unavailable():
    return jsonify({
        'error': 'ontología no configurada',
        'detail': 'Falta DATABASE_URL (añade el plugin de Postgres en Railway).',
    }), 503


def _require_db(fn):
    def wrapper(*a, **kw):
        if not ontology_available():
            return _unavailable()
        return fn(*a, **kw)
    wrapper.__name__ = fn.__name__
    return wrapper


def _obj_to_dict(o):
    return {'id': o.id, 'type': o.type, 'label': o.label, 'properties': o.properties,
            'created_at': o.created_at.isoformat() if o.created_at else None,
            'updated_at': o.updated_at.isoformat() if o.updated_at else None}


def _link_to_dict(l):
    return {'id': str(l.id), 'source': l.source_id, 'target': l.target_id,
            'rel_type': l.rel_type, 'weight': l.weight, 'properties': l.properties,
            'valid_from': l.valid_from.isoformat() if l.valid_from else None,
            'valid_to': l.valid_to.isoformat() if l.valid_to else None}


def _event_to_dict(e):
    return {'id': str(e.id), 'event_type': e.event_type, 'object_id': e.object_id,
            'target_id': e.target_id, 'payload': e.payload,
            'valid_from': e.valid_from.isoformat() if e.valid_from else None,
            'valid_to': e.valid_to.isoformat() if e.valid_to else None,
            'recorded_at': e.recorded_at.isoformat() if e.recorded_at else None,
            'source': e.source, 'actor': e.actor}


@ontology_bp.route('/status')
def status():
    if not ontology_available():
        return jsonify({'configured': False, 'ok': False,
                         'detail': 'DATABASE_URL no configurada — añade Postgres en Railway.'})
    try:
        with session_scope() as s:
            from ontology.models import ObjectRecord, LinkRecord, Event
            n_obj = s.query(ObjectRecord).count()
            n_link = s.query(LinkRecord).count()
            n_ev = s.query(Event).count()
        return jsonify({'configured': True, 'ok': True, 'objects': n_obj, 'links': n_link, 'events': n_ev})
    except Exception as e:  # noqa: BLE001
        return jsonify({'configured': True, 'ok': False, 'detail': str(e)[:200]}), 500


@ontology_bp.route('/objects')
@_require_db
def objects_list():
    type_ = request.args.get('type')
    q = request.args.get('q')
    limit = int(request.args.get('limit', 200))
    with session_scope() as s:
        objs = list_objects(s, type_=type_, q=q, limit=limit)
        return jsonify({'count': len(objs), 'objects': [_obj_to_dict(o) for o in objs]})


@ontology_bp.route('/objects/<object_id>')
@_require_db
def objects_get(object_id):
    with session_scope() as s:
        o = get_object(s, object_id)
        if not o:
            return jsonify({'error': 'not found'}), 404
        return jsonify(_obj_to_dict(o))


@ontology_bp.route('/objects/<object_id>/links')
@_require_db
def objects_links(object_id):
    direction = request.args.get('direction', 'out')
    with session_scope() as s:
        links = object_links(s, object_id, direction=direction)
        return jsonify({'count': len(links), 'links': [_link_to_dict(l) for l in links]})


@ontology_bp.route('/objects/<object_id>/history')
@_require_db
def objects_history(object_id):
    with session_scope() as s:
        events = object_history(s, object_id)
        return jsonify({'count': len(events), 'events': [_event_to_dict(e) for e in events]})


@ontology_bp.route('/graph')
@_require_db
def graph():
    as_of_raw = request.args.get('as_of')
    try:
        as_of_dt = _parse_dt(as_of_raw) if as_of_raw else _utcnow()
    except OntologyError as e:
        return jsonify({'error': str(e)}), 400
    with session_scope() as s:
        return jsonify(as_of_graph(s, as_of_dt))


@ontology_bp.route('/graph/diff')
@_require_db
def graph_diff():
    from_raw, to_raw = request.args.get('from'), request.args.get('to')
    if not from_raw or not to_raw:
        return jsonify({'error': "'from' y 'to' son requeridos (YYYY-MM-DD)"}), 400
    try:
        from_dt, to_dt = _parse_dt(from_raw), _parse_dt(to_raw)
    except OntologyError as e:
        return jsonify({'error': str(e)}), 400
    with session_scope() as s:
        return jsonify(diff_graph(s, from_dt, to_dt))


def _action_event_to_dict(e):
    p = e.payload or {}
    return {'id': str(e.id), 'action': p.get('action'), 'object_id': e.object_id,
            'target_id': e.target_id, 'payload': p, 'actor': e.actor, 'source': e.source,
            'recorded_at': e.recorded_at.isoformat() if e.recorded_at else None}


@ontology_bp.route('/actions', methods=['GET'])
@_require_db
def actions_list():
    """Panel '📋 Registro': timeline de Acciones ejecutadas, filtrable."""
    from ontology.actions import list_actions
    actor = request.args.get('actor')
    action_type = request.args.get('type')
    object_id = request.args.get('object_id')
    limit = int(request.args.get('limit', 100))
    with session_scope() as s:
        events = list_actions(s, actor=actor, action_type=action_type, object_id=object_id, limit=limit)
        return jsonify({'count': len(events), 'actions': [_action_event_to_dict(e) for e in events]})


@ontology_bp.route('/actions/<action_type>', methods=['POST'])
@_require_db
def actions_execute(action_type):
    """Catálogo de Acciones (Fase 2): CrearTesis, AnotarObjeto, MarcarRiesgo,
    ProponerVinculo, Confirmar/RechazarVinculo, RegistrarDecision,
    AjustarPosicion, CorregirDato. Body: {actor, ...campos del esquema}."""
    from ontology.actions import execute_action, ActionError
    body = request.get_json(force=True, silent=True) or {}
    actor = body.pop('actor', None)
    body.pop('action', None)  # por si el cliente reenvía el nombre dentro del body
    try:
        with session_scope() as s:
            result = execute_action(s, action_type, body, actor)
            return jsonify({'status': 'ok', 'action': action_type, 'result': result})
    except ActionError as e:
        return jsonify({'error': str(e)}), 400
    except OntologyError as e:
        return jsonify({'error': str(e)}), 400


def _proposal_to_dict(p):
    return {'id': str(p.id), 'agent': p.agent, 'action_type': p.action_type, 'payload': p.payload,
            'object_id': p.object_id, 'confidence': p.confidence, 'explanation': p.explanation,
            'status': p.status, 'created_at': p.created_at.isoformat() if p.created_at else None,
            'resolved_at': p.resolved_at.isoformat() if p.resolved_at else None, 'resolved_by': p.resolved_by}


@ontology_bp.route('/agents/run', methods=['POST'])
@_require_db
def agents_run():
    """Dispara una corrida de todos los agentes (o los que pida `only`).
    Pensado para un botón manual o un cron externo — ver ontology/agents.py
    para por qué NO corre en un scheduler interno de gunicorn."""
    from ontology.agents import run_agents
    body = request.get_json(force=True, silent=True) or {}
    only = body.get('only')  # lista opcional de nombres de agente
    with session_scope() as s:
        summary = run_agents(s, only=only)
        return jsonify({'status': 'ok', 'summary': summary})


@ontology_bp.route('/agents/proposals', methods=['GET'])
@_require_db
def agents_proposals_list():
    from ontology.models import ProposedAction
    status = request.args.get('status', 'pending')
    limit = int(request.args.get('limit', 100))
    with session_scope() as s:
        q = select_proposed(status, limit)
        props = s.scalars(q).all()
        return jsonify({'count': len(props), 'proposals': [_proposal_to_dict(p) for p in props]})


def select_proposed(status, limit):
    from sqlalchemy import select
    from ontology.models import ProposedAction
    q = select(ProposedAction)
    if status and status != 'all':
        q = q.where(ProposedAction.status == status)
    return q.order_by(ProposedAction.created_at.desc()).limit(min(limit, 500))


@ontology_bp.route('/agents/proposals/<proposal_id>/approve', methods=['POST'])
@_require_db
def agents_proposal_approve(proposal_id):
    """Aprueba (con ediciones opcionales) → ejecuta la Acción real, auditada
    con actor='<agente>, aprobado por <humano>'."""
    import uuid as _uuid
    from ontology.models import ProposedAction
    from ontology.actions import execute_action, ActionError
    body = request.get_json(force=True, silent=True) or {}
    actor = body.get('actor')
    edits = body.get('edits') or {}
    if not actor:
        return jsonify({'error': 'actor es requerido'}), 400
    try:
        pid = _uuid.UUID(proposal_id)
    except ValueError:
        return jsonify({'error': 'proposal_id inválido'}), 400
    try:
        with session_scope() as s:
            p = s.get(ProposedAction, pid)
            if not p:
                return jsonify({'error': 'propuesta no encontrada'}), 404
            if p.status != 'pending':
                return jsonify({'error': f'la propuesta ya está resuelta ({p.status})'}), 409
            payload = {**p.payload, **edits}
            combined_actor = f'{p.agent} → aprobado por {actor}'
            result = execute_action(s, p.action_type, payload, combined_actor)
            p.status = 'approved'
            p.resolved_at = datetime.now(timezone.utc)
            p.resolved_by = actor
            return jsonify({'status': 'ok', 'result': result})
    except ActionError as e:
        return jsonify({'error': str(e)}), 400
    except OntologyError as e:
        return jsonify({'error': str(e)}), 400


@ontology_bp.route('/agents/proposals/<proposal_id>/reject', methods=['POST'])
@_require_db
def agents_proposal_reject(proposal_id):
    import uuid as _uuid
    from ontology.models import ProposedAction
    body = request.get_json(force=True, silent=True) or {}
    actor = body.get('actor')
    if not actor:
        return jsonify({'error': 'actor es requerido'}), 400
    try:
        pid = _uuid.UUID(proposal_id)
    except ValueError:
        return jsonify({'error': 'proposal_id inválido'}), 400
    with session_scope() as s:
        p = s.get(ProposedAction, pid)
        if not p:
            return jsonify({'error': 'propuesta no encontrada'}), 404
        if p.status != 'pending':
            return jsonify({'error': f'la propuesta ya está resuelta ({p.status})'}), 409
        p.status = 'rejected'
        p.resolved_at = datetime.now(timezone.utc)
        p.resolved_by = actor
        return jsonify({'status': 'ok'})


@ontology_bp.route('/agents/brief')
@_require_db
def agents_brief():
    """Cronista: Brief Matinal — no requiere aprobación, es informativo."""
    from ontology.agents import brief_matinal
    hours = int(request.args.get('hours', 24))
    with session_scope() as s:
        return jsonify(brief_matinal(s, hours=hours))


def _alert_to_dict(a):
    return {'id': str(a.id), 'owner': a.owner, 'rule': a.rule, 'channel': a.channel,
            'is_active': a.is_active, 'created_at': a.created_at.isoformat() if a.created_at else None,
            'last_fired_at': a.last_fired_at.isoformat() if a.last_fired_at else None}


@ontology_bp.route('/alerts', methods=['GET'])
@_require_db
def alerts_list():
    from ontology.models import Alert
    owner = request.args.get('owner')
    with session_scope() as s:
        q = select_alerts(owner)
        alerts = s.scalars(q).all()
        return jsonify({'count': len(alerts), 'alerts': [_alert_to_dict(a) for a in alerts]})


def select_alerts(owner):
    from sqlalchemy import select
    from ontology.models import Alert
    q = select(Alert)
    if owner:
        q = q.where(Alert.owner == owner)
    return q.order_by(Alert.created_at.desc())


@ontology_bp.route('/alerts', methods=['POST'])
@_require_db
def alerts_create():
    """Body: {owner, rule:{entity,metric,op,value} o {region,event_type}, channel?}."""
    from ontology.models import Alert
    body = request.get_json(force=True, silent=True) or {}
    owner = body.get('owner')
    rule = body.get('rule')
    if not owner or not rule:
        return jsonify({'error': "'owner' y 'rule' son requeridos"}), 400
    if not (rule.get('metric') in ('price', 'nrs', 'news_region') or rule.get('event_type')):
        return jsonify({'error': "rule.metric debe ser 'price'|'nrs'|'news_region'"}), 400
    with session_scope() as s:
        a = Alert(owner=owner, rule=rule, channel=body.get('channel', 'browser'), is_active=True)
        s.add(a)
        s.flush()
        return jsonify({'status': 'ok', 'alert': _alert_to_dict(a)})


@ontology_bp.route('/alerts/<alert_id>', methods=['DELETE'])
@_require_db
def alerts_delete(alert_id):
    import uuid as _uuid
    from ontology.models import Alert
    try:
        aid = _uuid.UUID(alert_id)
    except ValueError:
        return jsonify({'error': 'alert_id inválido'}), 400
    with session_scope() as s:
        a = s.get(Alert, aid)
        if not a:
            return jsonify({'error': 'no encontrada'}), 404
        s.delete(a)
        return jsonify({'status': 'ok'})


@ontology_bp.route('/alerts/check', methods=['GET'])
@_require_db
def alerts_check():
    """Evalúa las alertas activas (de `owner` si se pasa) y devuelve las que
    dispararon ahora — el cliente las convierte en notificaciones del navegador."""
    from ontology.agents import check_alerts
    owner = request.args.get('owner')
    with session_scope() as s:
        fired = check_alerts(s, owner=owner)
        return jsonify({'fired': fired, 'count': len(fired)})


@ontology_bp.route('/events', methods=['POST'])
@_require_db
def events_create():
    """Escritura de bajo nivel. En Fase 2 esto se envuelve con el catálogo de
    Acciones (validación por tipo, auditoría de actor humano). Por ahora
    requiere explícitamente source+actor para que nada quede sin trazar."""
    body = request.get_json(force=True, silent=True) or {}
    required = ('event_type', 'valid_from', 'source', 'actor')
    missing = [k for k in required if not body.get(k)]
    if missing:
        return jsonify({'error': f'faltan campos: {", ".join(missing)}'}), 400
    try:
        with session_scope() as s:
            ev = apply_event(
                s, event_type=body['event_type'], payload=body.get('payload', {}),
                valid_from=body['valid_from'], valid_to=body.get('valid_to'),
                source=body['source'], actor=body['actor'],
                object_id=body.get('object_id'), target_id=body.get('target_id'),
            )
            s.flush()
            return jsonify({'status': 'ok', 'event': _event_to_dict(ev)})
    except OntologyError as e:
        return jsonify({'error': str(e)}), 400
