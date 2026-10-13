"""core/ledger_api.py — lectura del libro de decisiones: /api/ledger/* (docs/INFRA_OPERATIVA.md §2.9; paso 6).

  GET /api/ledger/status              público: conteo, cabeza de la cadena, estado del sellador (sin cuerpos)
  GET /api/ledger/decisions           ?kind=&principal=&status=&entity=&since=&limit=
  GET /api/ledger/decision/<id>       ?blobs=1 (solo operador) · ?lang=es|en
  GET /api/ledger/verify              ?from_seal=&limit=   — SOLO operador (PIN)

Acceso: con el PIN de operador (X-Trade-Pin, core/pin — estricto en producción) se ven los CUERPOS (manifiesto,
sujeto, salida, referencias, resultados, blobs). Sin PIN, un resumen REDACTADO (ids, kind, estado, tipo de
principal, canal, versiones y hashes): nada del sujeto, ni la etiqueta libre, ni el manifiesto. Un PIN errado
cuenta para el bloqueo compartido. Nunca bajo /v1/*. Sin DATABASE_URL → 503.
"""
import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from core.http import rate_limit

log = logging.getLogger('khipu')

ledger_bp = Blueprint('ledger', __name__, url_prefix='/api/ledger')


def _db():
    try:
        from ontology.db import ontology_available
        return ontology_available()
    except Exception:  # noqa: BLE001
        return False


def _unavailable():
    return jsonify({'available': False, 'error': 'Libro de decisiones no disponible — falta DATABASE_URL (Postgres)',
                    'error_en': 'Decision ledger unavailable — DATABASE_URL (Postgres) is missing',
                    'code': 'ledger_unavailable'}), 503


def _operator():
    """(es_operador, error_o_None). Sin cabecera de PIN → no operador (resumen redactado), salvo desarrollo sin
    TRADE_PIN (todo abierto, como las demás escrituras de operador). Con PIN → se verifica (cuenta fallos)."""
    from core import pin
    got = request.headers.get('X-Trade-Pin', '')
    if not pin.configured():
        if pin.operator_strict():
            return False, None
        return True, None
    if not got:
        return False, None
    err = pin.pin_error(where='ledger', strict=True)
    return (err is None), err


def _require_operator():
    from core import pin
    if not pin.configured() and not pin.operator_strict():
        return None
    return pin.pin_error(where='ledger', strict=True)


def _err(e, status=500):
    log.warning('ledger api: %s', type(e).__name__)
    return jsonify({'error': 'error del libro de decisiones', 'error_en': 'decision ledger error',
                    'detail': type(e).__name__}), status


@ledger_bp.route('/status')
@rate_limit(60, 60)
def ledger_status():
    if not _db():
        return _unavailable()
    try:
        from core import ledger
        st = ledger.status()
        from core.decisions import stats
        st['writer'] = {k: v for k, v in stats().items() if k != 'last_error'}
        return jsonify({'available': True, **st})
    except Exception as e:  # noqa: BLE001
        return _err(e)


@ledger_bp.route('/decisions')
@rate_limit(60, 60)
def ledger_decisions():
    if not _db():
        return _unavailable()
    full, err = _operator()
    if err:
        return err
    since = request.args.get('since')
    if since:
        try:
            since = datetime.fromisoformat(since.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'since inválido (ISO 8601)', 'error_en': 'invalid since (ISO 8601)'}), 400
    try:
        limit = max(1, min(500, int(request.args.get('limit', 50))))
    except ValueError:
        return jsonify({'error': 'limit inválido', 'error_en': 'invalid limit'}), 400
    try:
        from core import decisions
        from ontology.db import session_scope
        with session_scope() as s:
            items = decisions.list_decisions(
                s, kind=request.args.get('kind') or None, principal=request.args.get('principal') or None,
                status=request.args.get('status') or None,
                entity=(request.args.get('entity') if full else None) or None, since=since, limit=limit,
                redact=not full)
        return jsonify({'count': len(items), 'redacted': not full, 'decisions': items})
    except Exception as e:  # noqa: BLE001
        return _err(e)


@ledger_bp.route('/decision/<decision_id>')
@rate_limit(120, 60)
def ledger_decision(decision_id):
    if not _db():
        return _unavailable()
    import uuid
    try:
        uuid.UUID(decision_id)
    except ValueError:
        return jsonify({'error': 'id inválido', 'error_en': 'invalid id'}), 400
    full, err = _operator()
    if err:
        return err
    try:
        from core import decisions
        from ontology.db import session_scope
        with session_scope() as s:
            d = decisions.get(s, decision_id, redact=not full,
                              with_blobs=bool(full and request.args.get('blobs') in ('1', 'true')))
        if d is None:
            return jsonify({'error': 'decisión no encontrada', 'error_en': 'decision not found'}), 404
        if full:
            d['explain'] = {'es': decisions.explain(d, 'es'), 'en': decisions.explain(d, 'en')}
        return jsonify(d)
    except Exception as e:  # noqa: BLE001
        return _err(e)


@ledger_bp.route('/verify')
@rate_limit(6, 60)
def ledger_verify():
    if not _db():
        return _unavailable()
    err = _require_operator()
    if err:
        return err
    try:
        from_seal = max(1, int(request.args.get('from_seal', 1)))
        limit = request.args.get('limit')
        limit = max(1, min(1_000_000, int(limit))) if limit else None
    except ValueError:
        return jsonify({'error': 'parámetro inválido', 'error_en': 'invalid parameter'}), 400
    try:
        from core import ledger
        return jsonify(ledger.verify(from_seal=from_seal, limit=limit))
    except Exception as e:  # noqa: BLE001
        return _err(e)
