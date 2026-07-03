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
