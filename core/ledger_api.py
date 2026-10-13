"""core/ledger_api.py — lectura del libro de decisiones: /api/ledger/* (docs/INFRA_OPERATIVA.md §2.9; paso 6).

  GET /api/ledger/status              público: conteo, cabeza de la cadena, estado del sellador (sin cuerpos)
  GET /api/ledger/decisions           ?kind=&principal=&status=&entity=&since=&limit=
  GET /api/ledger/decision/<id>       ?blobs=1 (solo operador) · ?lang=es|en
  GET /api/ledger/verify              ?from_seal=&limit=&blobs=1 — SOLO operador (PIN); una ruptura queda en el libro
  GET /api/ledger/anchor              PÚBLICO: solo {day, head_seal, head_hash} de la última ancla diaria (paso 7;
                                      el GitHub Action smoke-mcp.yml la guarda fuera de la base — D7)
  GET /api/ledger/chain               público: ¿cadena rota? ¿dinero real bloqueado? (sin cuerpos)
  POST /api/ledger/chain_ack          SOLO operador (PIN): reconoce la ruptura → decisión ledger.chain_ack y el
                                      dinero real vuelve a operar

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
        try:      # paso 20/21: colas en segundo plano (decisiones async, registro ai_calls)
            from core import ai_calls, decisions
            st['writer']['async_pending'] = decisions.async_pending()
            st['ai_calls'] = {k: v for k, v in ai_calls.stats().items() if k != 'last_error'}
        except Exception:  # noqa: BLE001
            pass
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
        out = ledger.verify(from_seal=from_seal, limit=limit, record_break=True)
        out.pop('broken_keys', None)        # la lista completa es interna (dedupe de rupturas); va el total
        if request.args.get('blobs') == '1':  # paso 26: blobs por su sha (presentes) o purgados por retention.purge
            out['blobs'] = ledger.verify_blobs()
        return jsonify(out)
    except Exception as e:  # noqa: BLE001
        return _err(e)


@ledger_bp.route('/anchor')
@rate_limit(60, 60)
def ledger_anchor():
    """Ancla diaria PÚBLICA: SOLO la cabeza de la cadena (ningún contenido). Sin ancla todavía → anchor:null."""
    if not _db():
        return _unavailable()
    try:
        from core import ledger
        a = ledger.latest_anchor()
    except Exception as e:  # noqa: BLE001
        return _err(e)
    if a is None:
        return jsonify({'available': True, 'day': None, 'head_seal': None, 'head_hash': None, 'pending': True})
    resp = jsonify({'available': True, 'day': a['day'], 'head_seal': a['head_seal'], 'head_hash': a['head_hash']})
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@ledger_bp.route('/chain')
@rate_limit(60, 60)
def ledger_chain():
    if not _db():
        return _unavailable()
    try:
        from core import ledger
        st = ledger.chain_state()
        ok, es, en = ledger.money_gate()
        return jsonify({'broken': st['broken'], 'since': st['since'], 'pending_ack': len(st['open_breaks']),
                        'real_money_allowed': ok, 'message': es, 'message_en': en})
    except Exception as e:  # noqa: BLE001
        return _err(e)


@ledger_bp.route('/chain_ack', methods=['POST'])
@rate_limit(6, 60)
def ledger_chain_ack():
    """Reconocer la cadena rota (PIN estricto, persona). Cuerpo: {note?, break_id?}."""
    if not _db():
        return _unavailable()
    from core import pin
    err = pin.pin_error(where='ledger_ack', strict=True)
    if err:
        return err
    body = request.get_json(silent=True) or {}
    try:
        from core import identity, ledger
        from ontology.db import session_scope
        principal = identity.principal_from_request(declared=body.get('actor'))
        with session_scope() as s:
            out = ledger.chain_ack(s, principal, note=body.get('note'), break_id=body.get('break_id'))
        ledger._invalidate_chain()
        return jsonify({'ok': True, **out})
    except PermissionError as e:
        return jsonify({'error': str(e), 'error_en': 'acknowledging requires a person authenticated with the PIN',
                        'code': 'forbidden'}), 403
    except LookupError as e:
        return jsonify({'error': str(e), 'error_en': 'there is no pending chain break to acknowledge',
                        'code': 'nothing_to_ack'}), 404
    except ValueError as e:
        return jsonify({'error': str(e), 'error_en': 'that break was already acknowledged',
                        'code': 'already_acked'}), 409
    except Exception as e:  # noqa: BLE001
        return _err(e)
