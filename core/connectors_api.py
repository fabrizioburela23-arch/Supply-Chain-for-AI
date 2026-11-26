"""core/connectors_api.py — /api/connectors/* : la ventana 🧩 Conectores (engine/connectors.js) habla con esto.

  GET  /api/connectors/pending        → solo mis pendientes (ligero, para el aviso de confirmación)
  GET  /api/connectors/status         → ¿está Composio?, mis apps conectadas, sugeridas y mis acciones pendientes
  POST /api/connectors/link {app}     → enlace OFICIAL de inicio de sesión de esa app (Khipus nunca ve contraseñas)
  POST /api/connectors/confirm {id}   → ejecuta UNA acción pendiente que ESCRIBE (enviar correo, crear fila…) — PIN +
                                        decisión en el libro (policy.change 'connectors.execute'; sin libro → 503)
  POST /api/connectors/discard {id}   → la descarta
La persona = huella de X-Khipu-Owner (cada quien sus apps). Lógica en core/connectors.py.
"""
import logging

from flask import Blueprint, jsonify, request

from core import connectors as C
from core.http import rate_limit

log = logging.getLogger('khipu')
connectors_bp = Blueprint('connectors', __name__, url_prefix='/api/connectors')


def _uid():
    return C.user_id(request.headers.get('X-Khipu-Owner'))


def _body():
    b = request.get_json(silent=True)
    return b if isinstance(b, dict) else {}


def _err(e):
    return jsonify({'error': str(e), 'code': getattr(e, 'code', 'connector_error')}), getattr(e, 'status', 502)


@connectors_bp.route('/status', methods=['GET'])
@rate_limit(120, 300)
def status():
    uid = _uid()
    out = dict(C.status(), connected={}, pending=[])
    if not uid:
        out['need_owner'] = True
        return jsonify(out)
    out['pending'] = C.pending(uid)
    if C.enabled():
        try:
            out['connected'] = C.connections(uid)
        except C.ConnectorError as e:
            out['error'] = str(e)
    return jsonify(out)


@connectors_bp.route('/pending', methods=['GET'])
@rate_limit(400, 300)
def pending_list():
    """Ligero (no llama a Composio): lo consulta engine/connectors.js para pedir confirmación al instante."""
    uid = _uid()
    return jsonify({'enabled': C.enabled(), 'pending': C.pending(uid) if uid else []})


@connectors_bp.route('/link', methods=['POST'])
@rate_limit(20, 600)
def link():
    uid = _uid()
    if not uid:
        return jsonify({'error': 'falta la llave del navegador', 'code': 'need_owner'}), 400
    b = _body()
    try:
        return jsonify(C.connect_link(uid, b.get('app'), b.get('callback_url')))
    except C.ConnectorError as e:
        return _err(e)


@connectors_bp.route('/confirm', methods=['POST'])
@rate_limit(30, 600)
def confirm():
    from core.pin import pin_error
    err = pin_error(where='connectors_confirm', strict=True)
    if err:
        return err
    uid = _uid()
    p = C.take(uid, _body().get('id')) if uid else None
    if not p:
        return jsonify({'error': 'esa acción ya no está pendiente (vence a los 15 min)', 'code': 'not_found'}), 404
    # libro: QUÉ acción y en qué app (los nombres de los campos, nunca su contenido: un correo no va al libro)
    try:
        from core import decision_sites as _ds
        from ontology.db import ontology_available, session_scope
        if not ontology_available():
            return jsonify({'error': 'sin libro de decisiones no se ejecutan acciones', 'code': 'ledger_unavailable'}), 503
        with session_scope() as s:
            _ds.policy_change(s, 'connectors.execute', None,
                              {'tool': p['tool'], 'app': p['app'], 'fields': sorted((p['arguments'] or {}).keys())[:20]},
                              subject={'app': p['app'], 'tool': p['tool']}, task='connectors')
    except Exception as e:  # noqa: BLE001
        log.warning('conectores: sin decisión (%s)', type(e).__name__)
        return jsonify({'error': 'no se pudo registrar la decisión; no se ejecutó', 'code': 'ledger_unavailable'}), 503
    try:
        res = C.execute(uid, p['tool'], p['arguments'])
    except C.ConnectorError as e:
        return _err(e)
    return jsonify(dict(res, tool=p['tool'], app=p['app']))


@connectors_bp.route('/discard', methods=['POST'])
@rate_limit(60, 600)
def discard():
    uid = _uid()
    return jsonify({'ok': bool(uid and C.drop(uid, _body().get('id')))})
