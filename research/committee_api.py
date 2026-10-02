"""research/committee_api.py — blueprint /api/committee/* (PHASE 3).

POST /run                         {entity, client_id?, actor, sync?} → corre el comité (segundo plano;
                                  sync solo con PIN; dedupe por entidad+cliente; tope simultáneo → 429)
GET  /memo/<id>                   memo completo (si tiene cliente: montos solo con X-Trade-Pin)
GET  /entity/<id>                 último memo + historial de memos de la entidad
POST /memo/<id>/approve           (X-Trade-Pin) aprobación humana → previsualización en corretaje
POST /memo/<id>/reject            (X-Trade-Pin) rechazo con motivo
GET  /track-record[?agent=]       historial por agente (aciertos, Brier, fiabilidad)
GET  /calibration                 tabla de calibración + fotos periódicas
POST /outcomes/evaluate           (X-Trade-Pin) califica predicciones vencidas (también 1×/día solo)
GET  /outcomes/recent             últimas calificaciones (auditoría)
GET  /clients                     (X-Trade-Pin) clientes del módulo de corretaje (para elegir)
Sin DATABASE_URL → 503. Sin IA → memo determinista rotulado "sin IA".
PIN: header X-Trade-Pin == env TRADE_PIN vía core.pin (auditoría #7): MISMO contador
por IP y GLOBAL que /api/trade, /api/brokerage, /api/mcp y la ontología (antes se
comparaba aquí sin freno → adivinanza ilimitada del PIN). Sin TRADE_PIN → 403.
"""
import logging
import threading

from flask import Blueprint, current_app, jsonify, request

from core import pin as _core_pin
from core.http import rate_limit
from ontology.db import ontology_available, session_scope

log = logging.getLogger('khipu')

committee_bp = Blueprint('committee', __name__, url_prefix='/api/committee')


def _unavailable():
    return jsonify({'error': 'comité no disponible', 'error_en': 'committee not available', 'available': False,
                    'detail': 'Falta DATABASE_URL (el comité guarda sus memos en la ontología).'}), 503


def _pin_status():
    """None si el PIN es válido; si no, (respuesta, código). core.pin: cuenta los
    fallos en el contador COMPARTIDO y respeta el bloqueo por IP y global."""
    return _core_pin.pin_error(where='committee', strict=True)


def _pin_ok():
    """¿PIN válido? (para mostrar montos del cliente). Un PIN vacío no cuenta
    como fallo, así la vista redactada no suma al contador."""
    return _core_pin.check(where='committee', strict=True) is None


def _actor(body):
    return str((body or {}).get('actor') or '').strip()[:120]


def _with_schema(fn):
    """Si las tablas de Phase 3 aún no existen (base que arrancó después), las crea y reintenta."""
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        if 'does not exist' not in str(e) and 'UndefinedTable' not in type(e).__name__ + str(e):
            raise
        from ontology.db import init_schema
        init_schema(retries=1)
        return fn()


def _run_async(memo_id, eid, actor, client_id):
    """Corre el comité en un hilo. El cupo (acquire_run_slot) ya se tomó: se
    libera al terminar, pase lo que pase."""
    def _work():
        from research.committee import fail_memo, progress_clear, progress_set, release_run_slot, run_committee
        progress_set(memo_id, 'claims')
        try:
            with session_scope() as s:
                run_committee(s, eid, actor, client_id=client_id, memo_id=memo_id)
        except Exception as e:  # noqa: BLE001
            log.warning('committee %s: %s', memo_id, e)
            try:
                with session_scope() as s:
                    fail_memo(s, memo_id, f'{type(e).__name__}: {str(e)[:300]}')
            except Exception:  # noqa: BLE001
                pass
        finally:
            release_run_slot()
            progress_clear(memo_id)
    t = threading.Thread(target=_work, name=f'committee-{memo_id[:8]}', daemon=True)
    t.start()
    return t


def _busy():
    return jsonify({'error': 'el comité ya está deliberando otros pedidos; intenta en un minuto',
                    'error_en': 'the committee is already deliberating other requests; try again in a minute',
                    'code': 'busy'}), 429


@committee_bp.route('/run', methods=['POST'])
@rate_limit(limit=10, window=3600)
def run():
    """Corre el comité (asíncrono: 202 + memo_id). Con client_id exige PIN.
    `sync: true` (espera la respuesta en el hilo del pedido) SOLO con PIN válido
    o en tests: sin eso, unos pocos pedidos en paralelo ocuparían los 8 hilos
    del servidor. Mismo (entidad, cliente) deliberando o recién propuesto → se
    reutiliza ese memo (no se gasta IA dos veces). Tope de comités simultáneos:
    COMMITTEE_MAX_CONCURRENT (2) → 429."""
    if not ontology_available():
        return _unavailable()
    body = request.get_json(silent=True) or {}
    actor = _actor(body)
    if not actor:
        return jsonify({'error': 'actor obligatorio', 'error_en': 'actor is required'}), 400
    from core.entities import UMBRAL_BUSQUEDA, resolve
    r = resolve(str(body.get('entity') or '')[:120], umbral=UMBRAL_BUSQUEDA)
    if not r:
        return jsonify({'error': 'entidad no encontrada', 'error_en': 'entity not found'}), 404
    eid = r['id']
    client_id = str(body.get('client_id') or '').strip()[:60] or None
    if client_id:
        bad = _pin_status()          # datos de la cuenta de un cliente → PIN
        if bad:
            return bad
    sync = bool(body.get('sync')) and (current_app.config.get('TESTING') or _pin_ok())
    from research.committee import (acquire_run_slot, create_placeholder, recent_memo, release_run_slot,
                                    run_committee)
    try:
        def _reuse():
            with session_scope() as s:
                m = recent_memo(s, eid, client_id)
                return (m.id, m.status) if m else None
        prev = _with_schema(_reuse)
    except Exception as e:  # noqa: BLE001
        log.warning('committee run (dedupe): %s', e)
        prev = None
    if prev and not sync:
        return jsonify({'memo_id': prev[0], 'entity_id': eid, 'status': prev[1], 'reused': True}), 202
    if not acquire_run_slot():
        return _busy()
    started = False
    try:
        if sync:
            def _sync():
                with session_scope() as s:
                    out = run_committee(s, eid, actor, client_id=client_id)
                if out and out.get('memo_id'):
                    from research.committee import progress_clear
                    progress_clear(out['memo_id'])
                return out
            return jsonify(_with_schema(_sync))

        def _ph():
            with session_scope() as s:
                return create_placeholder(s, eid, actor, client_id).id
        mid = _with_schema(_ph)
        _run_async(mid, eid, actor, client_id)
        started = True
    except Exception as e:  # noqa: BLE001
        log.warning('committee run: %s', e)
        return jsonify({'error': 'no se pudo correr el comité', 'error_en': 'the committee could not run',
                        'detail': f'{type(e).__name__}: {str(e)[:240]}'}), 500
    finally:
        if not started:
            release_run_slot()           # el hilo libera el cupo solo si arrancó
    return jsonify({'memo_id': mid, 'entity_id': eid, 'status': 'running'}), 202


@committee_bp.route('/memo/<memo_id>')
@rate_limit(limit=120, window=60)
def memo(memo_id):
    if not ontology_available():
        return _unavailable()
    from research.committee import fail_memo, get_memo, progress_get
    with session_scope() as s:
        d = get_memo(s, memo_id, redact_client=not _pin_ok())
        if d and d.get('status') == 'running':
            prog = progress_get(memo_id)
            if prog:
                d['progress'] = prog
            elif _age_s(d.get('created_at')) > 90:
                # nadie lo está calculando (reinicio del servidor a mitad): no
                # dejar la pantalla "cargando" para siempre
                fail_memo(s, memo_id, 'se interrumpió (el servidor se reinició); vuelve a correr el comité',
                          'interrupted (the server restarted); run the committee again')
                d = get_memo(s, memo_id, redact_client=not _pin_ok())
    if not d:
        return jsonify({'error': 'memo no encontrado', 'error_en': 'memo not found'}), 404
    return jsonify(d)


def _age_s(iso):
    from datetime import datetime, timezone
    try:
        t = datetime.fromisoformat(str(iso).replace('Z', '+00:00'))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - t).total_seconds()
    except Exception:  # noqa: BLE001
        return 0


@committee_bp.route('/entity/<entity_id>')
@rate_limit(limit=120, window=60)
def entity(entity_id):
    if not ontology_available():
        return _unavailable()
    from core.entities import UMBRAL_BUSQUEDA, resolve
    from research.committee import latest_memo, list_memos
    r = resolve(entity_id[:120], umbral=UMBRAL_BUSQUEDA)
    eid = r['id'] if r else entity_id[:120]
    try:
        def _q():
            with session_scope() as s:
                return {'entity_id': eid, 'latest': latest_memo(s, eid, redact_client=not _pin_ok()),
                        'history': list_memos(s, eid, limit=20)}
        return jsonify(_with_schema(_q))
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': 'no se pudo leer el comité', 'error_en': 'could not read the committee', 'detail': f'{type(e).__name__}: {str(e)[:200]}'}), 500


def _decide(memo_id, fn):
    if not ontology_available():
        return _unavailable()
    bad = _pin_status()
    if bad:
        return bad
    body = request.get_json(silent=True) or {}
    actor = _actor(body)
    if not actor:
        return jsonify({'error': 'actor obligatorio', 'error_en': 'actor is required'}), 400
    with session_scope() as s:
        out = fn(s, memo_id, actor, body)
    code = 200 if out.get('ok') else {'not_found': 404, 'expired': 409, 'bad_status': 409, 'order_sent': 409,
                                      'preview_failed': 409, 'confirm_failed': 409, 'not_tradable': 409,
                                      'brokerage_unavailable': 409, 'withdraw_failed': 409}.get(out.get('code'), 400)
    return jsonify(out), code


@committee_bp.route('/memo/<memo_id>/approve', methods=['POST'])
@rate_limit(limit=30, window=3600)
def approve(memo_id):
    from research.committee import approve_memo
    return _decide(memo_id, lambda s, mid, actor, b: approve_memo(s, mid, actor, note=str(b.get('note') or '')))


@committee_bp.route('/memo/<memo_id>/reject', methods=['POST'])
@rate_limit(limit=30, window=3600)
def reject(memo_id):
    from research.committee import reject_memo
    return _decide(memo_id, lambda s, mid, actor, b: reject_memo(s, mid, actor, reason=str(b.get('reason') or '')))


@committee_bp.route('/board')
def board_route():
    if not ontology_available():
        return _unavailable()
    from research.committee import board
    try:
        lim = max(1, min(int(request.args.get('limit', 40)), 80))
    except (TypeError, ValueError):
        lim = 40
    try:
        def _q():
            with session_scope() as s:
                return board(s, limit=lim)
        return jsonify(_with_schema(_q))
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': 'no se pudo armar la pizarra', 'error_en': 'could not build the board',
                        'detail': f'{type(e).__name__}: {str(e)[:200]}'}), 500


@committee_bp.route('/board/refresh', methods=['POST'])
@rate_limit(limit=4, window=3600)
def board_refresh():
    """Encarga investigación para hasta 3 empresas (viejas, pedidas o clave) y la
    corre EN SERIE en un hilo (una a la vez: respeta el presupuesto y la IA)."""
    if not ontology_available():
        return _unavailable()
    from core.ai import _ai_configured
    body = request.get_json(silent=True) or {}
    actor = str(body.get('actor') or '').strip()[:120]
    if not actor:
        return jsonify({'error': 'actor obligatorio', 'error_en': 'actor required'}), 400
    if not _ai_configured():
        return jsonify({'error': 'ningún proveedor de IA configurado', 'error_en': 'no AI provider configured'}), 503
    from research.committee import refresh_targets
    from research.runner import create_job, execute_job
    ents = body.get('entities') if isinstance(body.get('entities'), list) else None
    try:
        def _plan():
            with session_scope() as s:
                targets = refresh_targets(s, max_n=3, entities=ents)
                jobs = []
                for eid in targets:
                    job, reused = create_job(s, eid, depth='STANDARD', trigger={'kind': 'board', 'by': actor},
                                             requested_by=actor)
                    jobs.append({'entity_id': eid, 'job_id': job.id, 'reused': reused, 'status': job.status})
                return jobs
        jobs = _with_schema(_plan)
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': 'no se pudo encargar la investigación', 'error_en': 'could not queue research',
                        'detail': f'{type(e).__name__}: {str(e)[:200]}'}), 500
    todo = [j['job_id'] for j in jobs if not j['reused']]
    if todo:
        import threading

        def _work():
            from research.models import ResearchJob
            for jid in todo:
                try:
                    with session_scope() as s:
                        job = s.get(ResearchJob, jid)
                        if job and job.status == 'queued':
                            execute_job(s, job)
                except Exception as e:  # noqa: BLE001
                    log.warning('board refresh %s: %s', jid, e)
        threading.Thread(target=_work, name='board-refresh', daemon=True).start()
    return jsonify({'jobs': jobs, 'n': len(jobs)}), 202


@committee_bp.route('/track-record')
def track_record():
    if not ontology_available():
        return _unavailable()
    from research.outcomes import track_record as tr
    agent = (request.args.get('agent') or '').strip()[:40] or None
    try:
        def _q():
            with session_scope() as s:
                return tr(s, agent_type=agent)
        return jsonify(_with_schema(_q))
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': 'no se pudo calcular el historial', 'error_en': 'could not compute the track record', 'detail': f'{type(e).__name__}: {str(e)[:200]}'}), 500


@committee_bp.route('/calibration')
def calibration():
    if not ontology_available():
        return _unavailable()
    from research.outcomes import BUCKETS, CAL_METHOD, MIN_N, calibration_table, k_default, snapshots
    try:
        def _q():
            with session_scope() as s:
                return {'table': calibration_table(s), 'k': k_default(), 'min_n': MIN_N, 'method': CAL_METHOD,
                        'buckets': [list(b) for b in BUCKETS],
                        'formula': '(aciertos_tramo + k·cruda) / (n_tramo + k)',
                        'snapshots': snapshots(s, limit=60)}
        return jsonify(_with_schema(_q))
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': 'no se pudo leer la calibración', 'error_en': 'could not read the calibration', 'detail': f'{type(e).__name__}: {str(e)[:200]}'}), 500


@committee_bp.route('/outcomes/evaluate', methods=['POST'])
@rate_limit(limit=12, window=3600)
def evaluate():
    if not ontology_available():
        return _unavailable()
    bad = _pin_status()
    if bad:
        return bad
    from research.outcomes import evaluate_due
    try:
        def _q():
            with session_scope() as s:
                return evaluate_due(s)
        return jsonify(_with_schema(_q))
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': 'no se pudo evaluar', 'error_en': 'could not score', 'detail': f'{type(e).__name__}: {str(e)[:200]}'}), 500


@committee_bp.route('/outcomes/recent')
def outcomes_recent():
    if not ontology_available():
        return _unavailable()
    from research.outcomes import recent_outcomes
    try:
        limit = min(max(int(request.args.get('limit', 30)), 1), 100)
    except (TypeError, ValueError):
        limit = 30
    agent = (request.args.get('agent') or '').strip()[:40] or None
    try:
        def _q():
            with session_scope() as s:
                return {'outcomes': recent_outcomes(s, limit=limit, agent_type=agent)}
        return jsonify(_with_schema(_q))
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': 'no se pudo leer', 'error_en': 'could not read', 'detail': f'{type(e).__name__}: {str(e)[:200]}'}), 500


@committee_bp.route('/clients')
@rate_limit(limit=60, window=60)
def clients():
    if not ontology_available():
        return _unavailable()
    bad = _pin_status()
    if bad:
        return bad
    from research.committee import brokerage_service
    svc = brokerage_service()
    if svc is None:
        return jsonify({'available': False, 'clients': [],
                        'detail': 'módulo de corretaje no instalado o no disponible'})
    try:
        with session_scope() as s:
            rows = svc.list_clients(s) or []
    except Exception as e:  # noqa: BLE001
        return jsonify({'available': False, 'clients': [], 'detail': f'{type(e).__name__}: {str(e)[:200]}'})
    keep = ('id', 'client_id', 'name', 'display_name', 'mode', 'status', 'live_enabled')
    return jsonify({'available': True, 'clients': [{k: c.get(k) for k in keep if k in c} for c in rows]})
