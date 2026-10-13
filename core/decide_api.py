"""core/decide_api.py — /api/decide/*: estado del modo sombra de Jev (lectura, PIN de operador)."""
from flask import Blueprint, jsonify, request

from core.decide import available, control_features, shadow_mode, shadow_report
from core.http import rate_limit
from core.pin import require_operator

decide_bp = Blueprint('decide', __name__, url_prefix='/api/decide')


@decide_bp.route('/status', methods=['GET'])
@rate_limit(60, 60)
def status():
    # control_features (solo nombres de funciones, nada privado): el 💰 dice «ACTIVO · manda en el chat» en vez de
    # «MODO SOMBRA» cuando Jev ya decide algo (Fabrizio, 2026-10-13: «modo sombra dice, ¿qué significa?»).
    on = available()
    return jsonify({'available': on, 'shadow': shadow_mode(), 'control_features': list(control_features()) if on else []})


@decide_bp.route('/shadow', methods=['GET'])
@rate_limit(30, 60)
@require_operator
def shadow():
    try:
        days = max(1, min(90, int(request.args.get('days') or 30)))
    except (TypeError, ValueError):
        days = 30
    return jsonify(shadow_report(days=days))
