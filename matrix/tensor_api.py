"""matrix/tensor_api.py — /api/tensor/*: la ontología nivel 2 (matrix/tensor.py) por HTTP.

Sin base de datos (lee el snapshot canónico): siempre disponible. Solo LECTURA y propuestas:
`/suggest` nunca escribe vínculos — devuelve candidatos para que una persona los revise.
"""
import logging
import os
import threading

from flask import Blueprint, jsonify, request

from core.http import rate_limit

log = logging.getLogger('khipu')
tensor_bp = Blueprint('tensor', __name__)
_EVAL = {'key': None, 'data': None}
_EVAL_LOCK = threading.Lock()


def _T():
    from matrix import tensor
    return tensor


def _err(es, en, code):
    return jsonify({'error': es, 'error_en': en}), code


@tensor_bp.route('/api/tensor/status')
def tensor_status():
    try:
        return jsonify(_T().status())
    except Exception as e:  # noqa: BLE001
        log.warning('tensor status: %s', e)
        return _err('El motor de tensores no está disponible.', 'The tensor engine is unavailable.', 503)


@tensor_bp.route('/api/tensor/node/<path:nid>')
@rate_limit(600, 3600)
def tensor_node(nid):
    try:
        out = _T().structure(nid)
    except Exception as e:  # noqa: BLE001
        log.warning('tensor node: %s', e)
        return _err('El motor de tensores no está disponible.', 'The tensor engine is unavailable.', 503)
    if not out:
        return _err('Empresa no encontrada en el grafo.', 'Company not found in the graph.', 404)
    return jsonify(out)


@tensor_bp.route('/api/tensor/rank')
@rate_limit(300, 3600)
def tensor_rank():
    by = request.args.get('by', 'cap_at_risk')
    if by not in ('cap_at_risk', 'concentration', 'exposure'):
        return _err("'by' debe ser cap_at_risk, concentration o exposure.",
                    "'by' must be cap_at_risk, concentration or exposure.", 400)
    try:
        limit = int(request.args.get('limit', 20))
    except ValueError:
        limit = 20
    return jsonify({'by': by, 'items': _T().ranking(by=by, limit=limit)})


@tensor_bp.route('/api/tensor/suggest', methods=['POST'])
@rate_limit(120, 3600)
def tensor_suggest():
    """{id} de una empresa existente, o {node:{label, cat, sector, country, role}} de una NUEVA."""
    body = request.get_json(silent=True) or {}
    nid, new = body.get('id'), body.get('node')
    if new is not None and not isinstance(new, dict):
        return _err("'node' debe ser un objeto.", "'node' must be an object.", 400)
    if not nid and not (new and (new.get('cat') or new.get('label'))):
        return _err('Indica una empresa (id) o los datos de una nueva (node.cat / node.label).',
                    'Give a company (id) or a new one (node.cat / node.label).', 400)
    try:
        n = max(1, min(25, int(body.get('n', 10))))
    except (TypeError, ValueError):
        n = 10
    out = _T().suggest_links(nid=nid, new=new, n=n)
    if not out:
        return _err('Empresa no encontrada en el grafo.', 'Company not found in the graph.', 404)
    return jsonify(out)


@tensor_bp.route('/api/tensor/eval')
@rate_limit(30, 3600)
def tensor_eval():
    """Calidad medida de la auto-conexión (vínculos reales ocultos). Se calcula 1 vez por snapshot."""
    T = _T()
    try:
        key = os.path.getmtime(T.SNAPSHOT)
    except OSError:
        key = None
    with _EVAL_LOCK:
        if _EVAL['key'] != key or _EVAL['data'] is None:
            runs = [T.evaluate(seed=s) for s in (7, 11, 23)]
            ok = [r for r in runs if r.get('hit_rate') is not None]
            _EVAL.update(key=key, data={
                'runs': runs, 'k': 10,
                'hit_rate': round(sum(r['hit_rate'] for r in ok) / len(ok), 3) if ok else None,
                'baseline_popularity': round(sum(r['baseline_popularity'] for r in ok) / len(ok), 3) if ok else None,
                'note_es': 'Se ocultan vínculos reales y se mide si vuelven entre las 10 primeras propuestas.',
                'note_en': 'Real links are hidden and we measure whether they come back in the top 10 proposals.'})
        return jsonify(_EVAL['data'])
