"""core/decide_api.py — /api/decide/*: estado del modo sombra de Jev (lectura, PIN de operador)."""
from flask import Blueprint, jsonify, request

from core.decide import available, shadow_mode, shadow_report
from core.http import rate_limit
from core.pin import require_operator

decide_bp = Blueprint('decide', __name__, url_prefix='/api/decide')


@decide_bp.route('/status', methods=['GET'])
@rate_limit(60, 60)
def status():
    return jsonify({'available': available(), 'shadow': shadow_mode()})


@decide_bp.route('/shadow', methods=['GET'])
@rate_limit(30, 60)
@require_operator
def shadow():
    try:
        days = max(1, min(90, int(request.args.get('days') or 30)))
    except (TypeError, ValueError):
        days = 30
    return jsonify(shadow_report(days=days))
