"""core/prices_api.py — /api/prices/* y /api/instruments/* (BRECHAS bloque 2: la memoria de los números). Nunca /v1/*.

  GET  /api/prices/status                 público: cuánta historia hay (filas, instrumentos, última fecha, FX, fotos)
  GET  /api/prices/eod/<símbolo>?range=1y público: serie diaria AJUSTADA con `source` y `as_of` (la base primero;
                                          si no la cubre, la descarga en vivo de siempre — y lo dice)
  GET  /api/prices/backfill               público: progreso del relleno (hecho/total/ETA/errores)
  POST /api/prices/backfill               SOLO operador (PIN): {years?: 1-5, symbols?: [...]} → arranca el relleno de
                                          historia (BRECHAS #3: nunca automático) + decisión 'data.backfill'
  POST /api/prices/backfill/stop          SOLO operador (PIN): lo detiene (reanudable: lo ya bajado se salta)
  GET  /api/instruments/review            público: los 44 casos (varios listados / OTC-ADR) que Fabrizio debe elegir
"""
import logging

from flask import Blueprint, jsonify, request

from core.http import rate_limit

log = logging.getLogger('khipu')

prices_bp = Blueprint('prices', __name__)

_NO_DB = {'error': 'Sin base de datos no se guarda historia: los cálculos siguen usando la descarga en vivo',
          'error_en': 'Without a database no history is stored: calculations keep using the live download',
          'code': 'ledger_unavailable'}


@prices_bp.route('/api/prices/status')
@rate_limit(60, 60)
def prices_status():
    from core import prices_store
    return jsonify(prices_store.status())


@prices_bp.route('/api/prices/eod/<path:symbol>')
@rate_limit(60, 60)
def prices_eod(symbol):
    from core import prices_store
    from core.http import _safe_ticker
    from core.risk_report import fetch_history, history_meta
    sym = _safe_ticker(symbol)
    rng = (request.args.get('range') or '1y').strip()
    if not sym:
        return jsonify({'error': 'símbolo inválido', 'error_en': 'invalid symbol', 'code': 'bad_request'}), 400
    if rng not in prices_store.RANGE_DAYS:
        return jsonify({'error': 'rango inválido', 'error_en': 'invalid range', 'code': 'bad_request',
                        'allowed': sorted(prices_store.RANGE_DAYS)}), 400
    h, cur = fetch_history(sym, rng)
    meta = history_meta(sym, rng) or {}
    if not h:
        return jsonify({'symbol': sym, 'range': rng, 'points': [], 'source': None, 'as_of': None,
                        'error': 'sin historia para ese símbolo', 'error_en': 'no history for that symbol',
                        'code': 'data_unavailable'}), 404
    pts = [[d, round(v, 6)] for d, v in sorted(h.items())]
    return jsonify({'symbol': sym, 'range': rng, 'currency': cur, 'adjusted': bool(meta.get('adjusted', True)),
                    'source': meta.get('source') or 'yahoo_live', 'as_of': meta.get('as_of') or pts[-1][0],
                    'n': len(pts), 'points': pts})


@prices_bp.route('/api/prices/backfill', methods=['GET'])
@rate_limit(120, 60)
def prices_backfill_state():
    from core import prices_store
    return jsonify(prices_store.backfill_state())


@prices_bp.route('/api/prices/backfill', methods=['POST'])
@rate_limit(6, 60)
def prices_backfill_start():
    from core import identity, pin, prices_store
    if not prices_store.db_on():
        return jsonify(_NO_DB), 503
    err = pin.pin_error(where='prices_backfill', strict=True)
    if err:
        return err
    body = request.get_json(silent=True) or {}
    try:
        years = int(body.get('years') or prices_store.MAX_YEARS)
    except (TypeError, ValueError):
        years = prices_store.MAX_YEARS
    syms = body.get('symbols') if isinstance(body.get('symbols'), list) else None
    try:
        principal = identity.principal_from_request(declared=body.get('actor'))
        st = prices_store.start_backfill(principal, years=years, symbols=syms)
    except RuntimeError:
        return jsonify({'error': 'ya hay una descarga de historia en curso', 'error_en': 'a history download is '
                        'already running', 'code': 'already_running', 'state': prices_store.backfill_state()}), 409
    except Exception as e:  # noqa: BLE001
        from core.decisions import LedgerUnavailable
        if isinstance(e, LedgerUnavailable):
            return jsonify(dict(_NO_DB, error='el libro de decisiones no está disponible',
                                error_en='the decision ledger is unavailable')), 503
        log.warning('prices backfill start: %s', type(e).__name__)
        return jsonify({'error': 'no se pudo arrancar el relleno', 'error_en': 'could not start the backfill',
                        'detail': type(e).__name__}), 500
    return jsonify({'ok': True, 'state': st})


@prices_bp.route('/api/prices/backfill/stop', methods=['POST'])
@rate_limit(6, 60)
def prices_backfill_stop():
    from core import identity, pin, prices_store
    if not prices_store.db_on():
        return jsonify(_NO_DB), 503
    err = pin.pin_error(where='prices_backfill_stop', strict=True)
    if err:
        return err
    body = request.get_json(silent=True) or {}
    try:
        stopped = prices_store.stop_backfill(identity.principal_from_request(declared=body.get('actor')))
    except Exception as e:  # noqa: BLE001
        log.warning('prices backfill stop: %s', type(e).__name__)
        return jsonify({'error': 'no se pudo detener', 'error_en': 'could not stop', 'detail': type(e).__name__}), 500
    return jsonify({'ok': True, 'stopping': stopped, 'state': prices_store.backfill_state()})


@prices_bp.route('/api/instruments/review')
@rate_limit(30, 60)
def instruments_review():
    from core import instruments
    rows = instruments.review_list()
    return jsonify({'n': len(rows), 'multi_listed': sum(r['review'] == 'multi_listed' for r in rows),
                    'otc_adr': sum(r['review'] == 'otc_adr' for r in rows), 'rows': rows,
                    'doc': 'docs/REVISION_INSTRUMENTOS.md',
                    'note_es': 'Nada cambia solo: el precio de hoy sigue siendo el primario hasta que Fabrizio elija.',
                    'note_en': 'Nothing changes by itself: today\'s price stays primary until Fabrizio chooses.'})
