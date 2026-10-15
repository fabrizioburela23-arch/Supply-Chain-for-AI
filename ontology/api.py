"""ontology/api.py — API REST de la ontología: /api/ontology/*

Prefijo elegido para NO colisionar con /v1/* (que ya es el producto de API
pública monetizado por tiers de Khipu Finance — ver server.py:khipu_auth).

Sigue el patrón de "feature opcional": si DATABASE_URL no
está configurada, todas las rutas devuelven 503 con un mensaje claro en vez
de romper el arranque del servidor.

Seguridad (auditoría estructural 2026-09-30, #20/#22):
  · las ESCRITURAS que alimentan el análisis de inversión (Acciones, eventos,
    carga masiva, correr agentes, aprobar/rechazar propuestas) exigen el PIN de
    operador (X-Trade-Pin) vía core.pin.require_operator: sin TRADE_PIN
    configurado se permiten (modo desarrollo, con aviso en el log); con
    TRADE_PIN, sin PIN correcto → 401 (y bloqueo por IP/global compartido).
    La UI debe llamarlas con window._tradeFetch(url, opts, true);
  · /ingest/news, /alerts y /agents/brief siguen abiertas pero con límite de
    tasa por IP (core.http.rate_limit);
  · aprobar/rechazar una propuesta es un RECLAMO ATÓMICO
    (UPDATE … WHERE status='pending'): dos clics o dos pestañas a la vez ya no
    ejecutan la Acción dos veces.

Paso 5 de INFRA_OPERATIVA (2026-10-13): QUIÉN escribe sale de core/identity (PIN → op:fabrizio; en
producción require_operator es estricto: sin TRADE_PIN → 403). El campo 'actor' de los cuerpos se sigue
aceptando (compatibilidad) pero queda solo como etiqueta (declared_name en la decisión y en ActionExecuted).
Cada Acción ejecutada deja además su ficha en el libro de decisiones (core/decisions, `decision_id`).

Revisión 2026-09-30:
  · POST /agents/cycle: el "latido" del Radar (engine/live.js, cada 10 min) SIN
    PIN y SIN force sigue funcionando — no recibe datos del cliente, así que no
    sirve para envenenar el grafo, y el servidor ya lo limita a UNA corrida
    cada 5 min en total. Forzar una corrida (force:true) o mandar un PIN exige
    el PIN correcto (y un PIN errado cuenta para el bloqueo). Antes, con
    TRADE_PIN puesto, el Radar recibía 401 en silencio y dejaba de
    auto-aplicar propuestas seguras y de evaluar alertas;
  · el estado de los ciclos de fondo (_cycle_state/_invest_state) se toma con
    un lock: dos peticiones simultáneas ya no arrancan dos corridas;
  · un cuerpo JSON que no es objeto (p. ej. una lista) se trata como {} y los
    parámetros numéricos de la URL inválidos dan 400 bilingüe (antes 500).
"""
import threading
import time
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from core.http import rate_limit
from core.pin import operator_strict, pin_error, require_operator
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


def _body():
    """Cuerpo JSON como dict SIEMPRE (una lista/número/texto → {}): antes un
    `[...]` en approve/reject/agents/run reventaba con AttributeError (500)."""
    b = request.get_json(force=True, silent=True)
    return b if isinstance(b, dict) else {}


class _BadArg(ValueError):
    pass


def _int_arg(name, default, lo, hi):
    """Entero de la query acotado a [lo, hi]; no numérico → _BadArg (400)."""
    raw = request.args.get(name)
    if raw in (None, ''):
        return default
    try:
        return max(lo, min(hi, int(raw)))
    except (TypeError, ValueError):
        raise _BadArg(name) from None


def _bad_arg(name):
    return jsonify({'error': f'parámetro inválido: {name} (debe ser un entero)',
                    'error_en': f'invalid parameter: {name} (must be an integer)'}), 400


from core.decisions import LedgerUnavailable as _LedgerUnavailable  # noqa: E402
from core.gates import GateViolation as _GateViolation  # noqa: E402


def _gate_violation(e, decision_id=None):
    """Paso 11 (puertas en BLOQUEO, policy.gates@2.0.0 activado con PIN): 422 con el GateReport/1 y el motivo ES/EN
    (§3.6); la decisión quedó 'blocked' en el libro (record_rejection, sesión propia)."""
    return jsonify(e.payload(decision_id)), 422


def _ledger_unavailable():
    """§7: sin ficha no hay efecto — la Acción se revirtió porque el libro de decisiones no se pudo escribir."""
    return jsonify({'error': 'No se pudo registrar la decisión: la acción NO se aplicó. Reintenta en un momento.',
                    'error_en': 'The decision could not be recorded: the action was NOT applied. Retry shortly.',
                    'code': 'ledger_unavailable'}), 503


def _principal(declared=None):
    """Paso 5 (INFRA_OPERATIVA §8.1): QUIÉN escribe sale de la autenticación (PIN → op:fabrizio; sin PIN en
    desarrollo → ui:anon), no del campo libre 'actor', que queda solo como etiqueta (declared_name)."""
    from core import identity
    return identity.principal_from_request(declared=declared)


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


def _mark_genesis(d, valid_from):
    """G4b: la fecha centinela 2000-01-01 de la migración NO es una fecha real
    ("desde que se rastrea"). Se marca para que la UI y las IAs no la lean
    como inicio real. Solo se añade la clave cuando aplica."""
    from ontology.service import is_genesis
    if is_genesis(valid_from):
        d['valid_from_known'] = False
    return d


def _link_to_dict(l):
    return _mark_genesis({'id': str(l.id), 'source': l.source_id, 'target': l.target_id,
                          'rel_type': l.rel_type, 'weight': l.weight, 'properties': l.properties,
                          'valid_from': l.valid_from.isoformat() if l.valid_from else None,
                          'valid_to': l.valid_to.isoformat() if l.valid_to else None}, l.valid_from)


def _event_to_dict(e):
    return _mark_genesis({'id': str(e.id), 'event_type': e.event_type, 'object_id': e.object_id,
                          'target_id': e.target_id, 'payload': e.payload,
                          'valid_from': e.valid_from.isoformat() if e.valid_from else None,
                          'valid_to': e.valid_to.isoformat() if e.valid_to else None,
                          'recorded_at': e.recorded_at.isoformat() if e.recorded_at else None,
                          'source': e.source, 'actor': e.actor}, e.valid_from)


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
            from ontology import bitemporal          # paso 23: ¿ya conviene object_versions? (umbral ~20.000)
            bt = bitemporal.scale_note(s)
        return jsonify({'configured': True, 'ok': True, 'objects': n_obj, 'links': n_link, 'events': n_ev,
                        'bitemporal': bt})
    except Exception as e:  # noqa: BLE001
        return jsonify({'configured': True, 'ok': False, 'detail': str(e)[:200]}), 500


@ontology_bp.route('/gates')
@rate_limit(60, 60)
def gates_status():
    """Puertas de validación (INFRA_OPERATIVA paso 10): modo (sombra), versión e ir_hash de las formas, reglas,
    cuántas veces avisó cada regla desde el arranque y la latencia p50/p95 de la puerta compilada. No necesita base."""
    try:
        import core.gates as gates
        st = gates.status()
        st['explain'] = {
            'es': ('Modo SOMBRA: las reglas solo AVISAN y quedan en el libro de decisiones; nada se rechaza todavía.'
                   if st['mode'] == 'shadow' else 'Puertas APAGADAS por el interruptor de emergencia KHIPU_GATES=off.'),
            'en': ('SHADOW mode: rules only WARN and are recorded in the decision ledger; nothing is rejected yet.'
                   if st['mode'] == 'shadow' else 'Gates OFF via the KHIPU_GATES=off emergency switch.')}
        return jsonify(st)
    except Exception as e:  # noqa: BLE001
        return jsonify({'available': False, 'error': 'puertas no disponibles', 'error_en': 'gates unavailable',
                        'detail': type(e).__name__}), 503


@ontology_bp.route('/objects')
@_require_db
def objects_list():
    type_ = request.args.get('type')
    q = request.args.get('q')
    try:
        limit = _int_arg('limit', 200, 1, 2000)
    except _BadArg as e:
        return _bad_arg(str(e))
    with session_scope() as s:
        objs = list_objects(s, type_=type_, q=q, limit=limit)
        return jsonify({'count': len(objs), 'objects': [_obj_to_dict(o) for o in objs]})


def _known_bad(e):
    """known_at inválido (paso 23): 400 bilingüe."""
    return jsonify({'error': e.es, 'error_en': e.en, 'param': 'known_at'}), 400


@ontology_bp.route('/objects/<object_id>')
@_require_db
def objects_get(object_id):
    """Objeto materializado de hoy. Con ?as_of= y/o ?known_at= (paso 23, props_at): sus propiedades en la fecha
    as_of TAL COMO SE CONOCÍAN en κ, plegadas desde `events` (no la fila de hoy)."""
    as_of_raw, known_raw = request.args.get('as_of'), request.args.get('known_at')
    if as_of_raw or known_raw:
        from ontology import bitemporal
        try:
            as_of_dt = _parse_dt(as_of_raw) if as_of_raw else None
        except OntologyError as e:
            return jsonify({'error': str(e), 'error_en': 'invalid as_of (use YYYY-MM-DD or ISO 8601)'}), 400
        with session_scope() as s:
            try:
                known = bitemporal.resolve(s, known_raw) if known_raw else None
            except bitemporal.KnownAtError as e:
                return _known_bad(e)
            o = bitemporal.props_at(s, ids=[object_id], t=as_of_dt, known=known).get(object_id)
            if o is None:
                return jsonify({'error': 'no existía en esa fecha / not found at that time',
                                'as_of': as_of_dt.isoformat() if as_of_dt else None,
                                **(known.to_dict() if known else {})}), 404
            return jsonify({**bitemporal.object_props_dict(o), 'as_of': as_of_dt.isoformat() if as_of_dt else None,
                            **(known.to_dict() if known else {}), 'method': 'props_at@1'})
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
    """?known_at= (paso 23): solo los eventos que Khipus ya conocía en κ (ISO o versión del grafo)."""
    known_raw = request.args.get('known_at')
    with session_scope() as s:
        known = None
        if known_raw:
            from ontology import bitemporal
            try:
                known = bitemporal.resolve(s, known_raw)
            except bitemporal.KnownAtError as e:
                return _known_bad(e)
        events = object_history(s, object_id, known=known)
        out = {'count': len(events), 'events': [_event_to_dict(e) for e in events]}
        if known is not None:
            out.update(known.to_dict())
        return jsonify(out)


@ontology_bp.route('/graph')
@_require_db
def graph():
    as_of_raw = request.args.get('as_of')
    known_raw = request.args.get('known_at') or None      # paso 23: G(t, κ) — ISO o versión del grafo
    try:
        as_of_dt = _parse_dt(as_of_raw) if as_of_raw else _utcnow()
    except OntologyError as e:
        return jsonify({'error': str(e)}), 400
    from ontology.bitemporal import KnownAtError
    with session_scope() as s:
        if known_raw is None:      # paso 26: punto de control EXACTO (solo por encima del umbral; si no, sin consultas)
            from ontology import checkpoints as _cp
            hit = _cp.lookup(s, as_of_dt)
            if hit is not None:
                return jsonify(hit)
        try:
            return jsonify(as_of_graph(s, as_of_dt, known_at=known_raw))
        except KnownAtError as e:
            return _known_bad(e)


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
    from ontology.bitemporal import KnownAtError
    with session_scope() as s:
        try:
            return jsonify(diff_graph(s, from_dt, to_dt, known_at=request.args.get('known_at') or None))
        except KnownAtError as e:
            return _known_bad(e)


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
    try:
        limit = _int_arg('limit', 100, 1, 500)
    except _BadArg as e:
        return _bad_arg(str(e))
    with session_scope() as s:
        events = list_actions(s, actor=actor, action_type=action_type, object_id=object_id, limit=limit)
        return jsonify({'count': len(events), 'actions': [_action_event_to_dict(e) for e in events]})


@ontology_bp.route('/actions/<action_type>', methods=['POST'])
@_require_db
@require_operator
@rate_limit(120, 600)
def actions_execute(action_type):
    """Catálogo de Acciones (Fase 2): CrearTesis, AnotarObjeto, MarcarRiesgo,
    ProponerVinculo, Confirmar/RechazarVinculo, RegistrarDecision,
    AjustarPosicion, CorregirDato. Body: {actor, ...campos del esquema}."""
    from ontology.actions import execute_action, ActionError
    body = _body()
    declared = body.pop('actor', None)       # paso 5: SOLO etiqueta para mostrar (declared_name)
    body.pop('action', None)  # por si el cliente reenvía el nombre dentro del body
    principal = _principal(declared)
    meta = {}
    try:
        with session_scope() as s:
            result = execute_action(s, action_type, body, principal.id, principal=principal, meta=meta)
            return jsonify({'status': 'ok', 'action': action_type, 'result': result,
                            'decision_id': meta.get('decision_id'), 'principal': principal.id})
    except _GateViolation as e:
        return _gate_violation(e, meta.get('decision_id'))
    except ActionError as e:
        return jsonify({'error': str(e), 'decision_id': meta.get('decision_id')}), 400
    except OntologyError as e:
        return jsonify({'error': str(e), 'decision_id': meta.get('decision_id')}), 400
    except _LedgerUnavailable:
        return _ledger_unavailable()


def _proposal_to_dict(p):
    return {'id': str(p.id), 'agent': p.agent, 'action_type': p.action_type, 'payload': p.payload,
            'object_id': p.object_id, 'confidence': p.confidence, 'explanation': p.explanation,
            'status': p.status, 'created_at': p.created_at.isoformat() if p.created_at else None,
            'resolved_at': p.resolved_at.isoformat() if p.resolved_at else None, 'resolved_by': p.resolved_by,
            # paso 10 (G-PROP): qué reglas NO cumpliría esta propuesta (en sombra: solo aviso) — para quien aprueba
            'gate_report': getattr(p, 'gate_report', None)}


@ontology_bp.route('/agents/run', methods=['POST'])
@_require_db
@require_operator
@rate_limit(10, 600)
def agents_run():
    """Dispara una corrida de todos los agentes (o los que pida `only`).
    Pensado para un botón manual o un cron externo — ver ontology/agents.py
    para por qué NO corre en un scheduler interno de gunicorn."""
    from ontology.agents import run_agents
    body = _body()
    only = body.get('only')  # lista opcional de nombres de agente
    with session_scope() as s:
        summary = run_agents(s, only=only)
        return jsonify({'status': 'ok', 'summary': summary})


# Ciclo en vivo: corre en un HILO de background (GDELT + IA tardan 30-60s —
# jamás atar un worker síncrono de gunicorn a eso). El endpoint responde al
# instante con el último resultado y lanza una corrida nueva si toca; el
# cliente (engine/live.js) recoge el resultado en su siguiente poll.
_cycle_state = {'running': False, 'last': None, 'last_at': 0.0}
_cycle_lock = threading.Lock()      # check-and-set de 'running' (dos POST a la vez = una corrida)
CYCLE_MIN_INTERVAL_S = 300          # corrida nueva como mucho cada 5 min (salvo force con PIN)


def _cycle_bg():
    from ontology.agents import auto_cycle, check_alerts
    last = None
    try:
        with session_scope() as s:
            result = auto_cycle(s)
            try:
                fired = check_alerts(s)
            except Exception:  # noqa: BLE001
                fired = []
        last = {'status': 'ok', 'auto_applied': result['auto_applied'],
                'left_for_human': result['left_for_human'],
                'agents': result['agents'], 'alerts_fired': fired}
    except Exception as e:  # noqa: BLE001
        last = {'status': 'error', 'error': str(e)[:300]}
    finally:
        with _cycle_lock:
            _cycle_state['last'] = last
            _cycle_state['last_at'] = time.time()
            _cycle_state['running'] = False


def _try_start_cycle(force):
    """Arranca una corrida en segundo plano si toca. Atómico (lock): True si
    ESTA llamada la arrancó."""
    with _cycle_lock:
        if _cycle_state['running']:
            return False
        if not force and time.time() - _cycle_state['last_at'] <= CYCLE_MIN_INTERVAL_S:
            return False
        _cycle_state['running'] = True
    try:
        threading.Thread(target=_cycle_bg, name='ontology-cycle', daemon=True).start()
    except Exception:  # noqa: BLE001 — sin hilo: no dejar 'running' pegado para siempre
        with _cycle_lock:
            _cycle_state['running'] = False
        raise
    return True


@ontology_bp.route('/agents/cycle', methods=['POST'])
@_require_db
@rate_limit(30, 600)
def agents_cycle():
    """Ciclo EN VIVO (elección de Fabrizio 2026-07-10: automático + reversible):
    corre los 5 agentes, auto-aprueba las propuestas SEGURAS (anotar, marcar
    riesgo, proponer vínculo, incorporar empresa — actor 'agent:auto'), deja lo
    que toca dinero para el humano, y evalúa las alertas. El grafo se mantiene
    relevante solo; todo queda auditado en la ontología.

    PIN: el latido normal (sin force, sin PIN) NO lo exige — no lleva datos del
    cliente y el servidor lo limita a una corrida cada 5 min en total. force:true
    (saltarse esa espera) o cualquier X-Trade-Pin enviado → PIN de operador
    (core.pin, mismo bloqueo compartido). Un cron externo que quiera forzar
    corridas debe mandar X-Trade-Pin."""
    force = bool(_body().get('force'))
    if force or request.headers.get('X-Trade-Pin'):
        # paso 5 (G-6): en producción sin TRADE_PIN, forzar corridas (costo de IA + auto-aplicación) → 403
        err = pin_error(where='agents_cycle', strict=operator_strict())
        if err:
            return err
    started = _try_start_cycle(force)
    with _cycle_lock:
        snap = dict(_cycle_state)
    return jsonify({'status': 'ok', 'started_new_run': started,
                    'running': snap['running'],
                    'last_at': snap['last_at'],
                    'last': snap['last']})


# ── Ingesta masiva (expansión multicapa y futuras) ───────────────────────────
@ontology_bp.route('/bulk/import', methods=['POST'])
@_require_db
@require_operator
@rate_limit(30, 600)
def bulk_import_route():
    """Carga masiva AUDITADA: objects (solo tipos NO económicos del registro,
    p.ej. Seat) + links (vía ontology.bulk_import: validación de integridad,
    cuarentena, idempotencia por external_id/triple, por lotes). Body:
    {actor, provenance, objects?: [{id,type,label,properties}], links?: [...]}.
    Mismo modelo de seguridad que las Acciones (actor obligatorio, todo queda
    como eventos inmutables reversibles) + límite de tamaño por request."""
    b = _body()
    declared = (b.get('actor') or '').strip()[:80]
    provenance = (b.get('provenance') or 'bulk').strip()[:60]
    if not declared:
        return jsonify({'error': 'actor requerido'}), 400
    actor = _principal(declared).id          # paso 5: se registra el principal, no el texto libre
    objects = b.get('objects') or []
    links = b.get('links') or []
    if len(objects) > 200 or len(links) > 1000:
        return jsonify({'error': 'máx 200 objects / 1000 links por request'}), 400
    out = {'objects_created': 0, 'objects_skipped': [], 'links': None}
    from core import decisions as _decisions
    principal = _principal(declared)
    did = {}
    try:
        with session_scope() as s, _decisions.decision_scope(
                'ontology.bulk_import', principal, session=s,
                subject={'provenance': provenance, 'n_objects': len(objects), 'n_links': len(links)}) as dctx:
            did['id'] = str(dctx.id)
            _bulk_import_apply(s, objects, links, provenance, actor, out)
            dctx.output = {'objects_created': out['objects_created'],
                           'links_created': (out['links'] or {}).get('created')}
    except _GateViolation as e:
        return _gate_violation(e, did.get('id'))
    except _LedgerUnavailable:
        return _ledger_unavailable()
    out['decision_id'] = did.get('id')
    return jsonify(out)


def _bulk_import_apply(s, objects, links, provenance, actor, out):
    """Lo que escribe la carga masiva, dentro de la decisión ontology.bulk_import del llamador."""
    if objects:
        from ontology.models import ObjectRecord
        from ontology.service import apply_event
        from ontology.vocabulary import is_economic, object_types
        known_types = object_types()
        for o in objects:
            oid = str(o.get('id') or '').strip()[:120]
            otype = str(o.get('type') or '').strip()[:40]
            if not oid or otype not in known_types or is_economic(otype):
                out['objects_skipped'].append({'id': oid, 'reason':
                    'tipo económico o fuera del registro — usa IncorporarEmpresa/acciones'})
                continue
            if s.get(ObjectRecord, oid):
                out['objects_skipped'].append({'id': oid, 'reason': 'ya existe'})
                continue
            apply_event(s, 'ObjectCreated',
                        {'label': str(o.get('label') or oid)[:300], 'type': otype,
                         'properties': dict(o.get('properties') or {})},
                        valid_from=None,   # _parse_dt → ahora (default)
                        source=provenance, actor=actor, object_id=oid)
            out['objects_created'] += 1
    if links:
        from ontology.bulk_import import import_links_bulk
        res = import_links_bulk(s, links, provenance, actor=actor)
        res['quarantined'] = res.get('quarantined', [])[:15]   # muestra, no todo
        out['links'] = res
    return out


# ── Investigador Autónomo (Track C): investigación puntual bajo demanda ─────
# Corre en hilo de fondo (2-4 búsquedas web + 1 síntesis tier deep = 20-60 s;
# no se bloquea un worker síncrono ese tiempo). Throttle de 3 min por si se
# aprieta el botón dos veces. Este endpoint NO depende de INVESTIGADOR_AUTO —
# es el camino "cuando yo pida" y queda activo desde el primer deploy.
_invest_state = {'running': False, 'last': None, 'last_at': 0.0, 'last_query': ''}
_invest_lock = threading.Lock()


def _invest_bg(query, actor, empresa_id):
    try:
        from ontology.agents import AGENTS
        inv = next((a for a in AGENTS if a.name == 'investigador_autonomo'), None)
        if inv is None:
            _invest_state['last'] = {'status': 'error', 'error': 'agente no registrado'}
            return
        with session_scope() as s:
            proposal = inv.investigar_manual(s, query, actor, empresa_id=empresa_id)
            if not proposal:
                _invest_state['last'] = {'status': 'sin_resultado',
                                         'hint': 'Sin TAVILY_KEY o sin fuentes — nada que proponer.'}
                return
            from ontology.models import ProposedAction
            pa = ProposedAction(agent=inv.name, action_type=proposal['action_type'],
                                payload=proposal['payload'], object_id=proposal.get('object_id'),
                                confidence=proposal.get('confidence'),
                                explanation=proposal.get('explanation'), status='pending')
            s.add(pa)
            s.flush()
            _invest_state['last'] = {'status': 'ok', 'action_type': proposal['action_type'],
                                     'proposal_id': str(pa.id), 'confidence': proposal.get('confidence')}
    except Exception as e:  # noqa: BLE001
        _invest_state['last'] = {'status': 'error', 'error': str(e)[:300]}
    finally:
        with _invest_lock:
            _invest_state['last_at'] = time.time()
            _invest_state['running'] = False


@ontology_bp.route('/agents/investigar', methods=['POST'])
@_require_db
@require_operator
@rate_limit(20, 600)
def agents_investigar():
    """Body: {query, actor, empresa_id?}. Responde al instante; el resultado
    aparece como ProposedAction en 🔔 Propuestas (y en GET de este estado)."""
    import threading as _th
    import time as _t
    from core.websearch import _web_search_available
    if not _web_search_available():
        return jsonify({'ok': False, 'error': 'TAVILY_KEY no configurada — añádela en Railway '
                        '(tavily.com, tier gratis) para habilitar la investigación web.'}), 400
    b = _body()
    query = (b.get('query') or '').strip()[:300]
    actor = _principal((b.get('actor') or '').strip()[:80]).id    # paso 5: el principal, no el texto libre
    empresa_id = (b.get('empresa_id') or None)
    if not query:
        return jsonify({'ok': False, 'error': 'query requerida'}), 400
    started = False
    with _invest_lock:                 # check-and-set atómico: dos clics = una investigación
        if not _invest_state['running'] and _t.time() - _invest_state['last_at'] > 180:
            _invest_state.update(running=True, last_query=query)
            started = True
    if started:
        try:
            _th.Thread(target=_invest_bg, args=(query, actor, empresa_id), daemon=True).start()
        except Exception:  # noqa: BLE001
            with _invest_lock:
                _invest_state['running'] = False
            raise
    return jsonify({'ok': True, 'started': started, 'running': _invest_state['running'],
                    'last': _invest_state['last'], 'last_query': _invest_state['last_query']})


@ontology_bp.route('/agents/proposals', methods=['GET'])
@_require_db
def agents_proposals_list():
    from ontology.models import ProposedAction
    status = request.args.get('status', 'pending')
    try:
        limit = _int_arg('limit', 100, 1, 500)
    except _BadArg as e:
        return _bad_arg(str(e))
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


def _claim_proposal(s, pid, new_status, actor):
    """RECLAMO ATÓMICO de una propuesta pendiente (auditoría #22).

    UPDATE … WHERE id=… AND status='pending': Postgres bloquea la fila, así que
    una segunda petición simultánea espera y, cuando la primera confirma, ya no
    encuentra 'pending' → rowcount 0 → 409. Antes era leer-y-luego-escribir y
    dos clics a la vez ejecutaban la Acción DOS veces. Todo va en la MISMA
    transacción que la Acción: si la Acción falla, el rollback devuelve la
    propuesta a 'pending'. Devuelve (propuesta, None) o (None, (json, status)).

    Mientras el ciclo del Radar corre (_cycle_state['running']), una propuesta
    que el ciclo PODRÍA auto-aplicar (tipo seguro con confianza suficiente) no
    se resuelve a mano → 409 'cycle_running': auto_cycle (ontology/agents.py)
    aún lee-y-luego-escribe sin reclamo atómico, así que aprobarla a la vez la
    ejecutaría dos veces. El ciclo dura 30-60 s; basta reintentar."""
    from sqlalchemy import update
    from ontology.models import ProposedAction
    busy = _cycle_may_auto_apply(s, pid)
    if busy:
        return None, busy
    res = s.execute(update(ProposedAction)
                    .where(ProposedAction.id == pid, ProposedAction.status == 'pending')
                    .values(status=new_status, resolved_at=datetime.now(timezone.utc), resolved_by=actor)
                    .execution_options(synchronize_session=False))
    p = s.get(ProposedAction, pid, populate_existing=True)
    if res.rowcount != 1:
        if not p:
            return None, (jsonify({'error': 'propuesta no encontrada', 'error_en': 'proposal not found'}), 404)
        return None, (jsonify({'error': f'la propuesta ya está resuelta ({p.status})',
                               'error_en': f'proposal already resolved ({p.status})',
                               'code': 'already_resolved'}), 409)
    return p, None


def _cycle_may_auto_apply(s, pid):
    """(json, 409) si el ciclo en curso podría auto-aplicar esta propuesta; si no, None."""
    with _cycle_lock:
        running = _cycle_state['running']
    if not running:
        return None
    try:
        from ontology.agents import AUTO_MIN_CONFIDENCE, SAFE_AUTO
        from ontology.models import ProposedAction
        p = s.get(ProposedAction, pid)
    except Exception:  # noqa: BLE001 — ante la duda, dejar que el reclamo decida
        return None
    if (p is None or p.status != 'pending' or p.action_type not in SAFE_AUTO
            or (p.confidence or 0) < AUTO_MIN_CONFIDENCE):
        return None
    return (jsonify({'error': 'El Radar está procesando propuestas ahora mismo; reintenta en un minuto',
                     'error_en': 'The Radar is processing proposals right now; retry in a minute',
                     'code': 'cycle_running', 'retry_after': 60}), 409)


def _proposal_actor_and_id(body, proposal_id):
    """(principal, pid, None) o (None, None, error). El cuerpo sigue exigiendo 'actor' (compatibilidad), pero
    lo que se registra como quien resolvió es el PRINCIPAL autenticado (paso 5); el texto queda de etiqueta."""
    import uuid as _uuid
    declared = str(body.get('actor') or '').strip()[:120]
    if not declared:
        return None, None, (jsonify({'error': 'actor es requerido', 'error_en': 'actor is required'}), 400)
    try:
        pid = _uuid.UUID(proposal_id)
    except ValueError:
        return None, None, (jsonify({'error': 'proposal_id inválido', 'error_en': 'invalid proposal_id'}), 400)
    return _principal(declared), pid, None


@ontology_bp.route('/agents/proposals/<proposal_id>/approve', methods=['POST'])
@_require_db
@require_operator
def agents_proposal_approve(proposal_id):
    """Aprueba (con ediciones opcionales) → ejecuta la Acción real, auditada
    con actor='<agente>, aprobado por <humano>'. Reclamo atómico: ver
    _claim_proposal."""
    from ontology.actions import execute_action, ActionError
    body = _body()
    principal, pid, err = _proposal_actor_and_id(body, proposal_id)
    if err:
        return err
    edits = body.get('edits') or {}
    if not isinstance(edits, dict):
        return jsonify({'error': 'edits debe ser un objeto', 'error_en': 'edits must be an object'}), 400
    meta = {}
    try:
        with session_scope() as s:
            p, err = _claim_proposal(s, pid, 'approved', principal.id)
            if err:
                return err
            payload = {**(p.payload or {}), **edits}
            combined_actor = f'{p.agent} → aprobado por {principal.id}'[:120]
            # paso 19: approval.grant (persona con PIN) sobre el proposal.create; la Acción queda como hija
            from core import decision_sites as _ds
            from core import identity
            with identity.use(principal), _ds.approval(
                    s, 'grant', target_kind='proposal.create', target_ref=('proposal', pid),
                    parent_id=_ds.proposal_parent(s, pid), note=({'edits': edits} if edits else None),
                    subject={'action_type': p.action_type}):
                result = execute_action(s, p.action_type, payload, combined_actor, principal=principal, meta=meta,
                                        correlation_id=f'proposal:{pid}')
            return jsonify({'status': 'ok', 'result': result, 'decision_id': meta.get('decision_id'),
                            'principal': principal.id})
    except _GateViolation as e:
        return _gate_violation(e, meta.get('decision_id'))
    except ActionError as e:
        return jsonify({'error': str(e), 'decision_id': meta.get('decision_id')}), 400
    except OntologyError as e:
        return jsonify({'error': str(e), 'decision_id': meta.get('decision_id')}), 400
    except _LedgerUnavailable:
        return _ledger_unavailable()


@ontology_bp.route('/agents/proposals/<proposal_id>/reject', methods=['POST'])
@_require_db
@require_operator
def agents_proposal_reject(proposal_id):
    body = _body()
    principal, pid, err = _proposal_actor_and_id(body, proposal_id)
    if err:
        return err
    try:
        with session_scope() as s:
            _p, err = _claim_proposal(s, pid, 'rejected', principal.id)
            if err:
                return err
            from core import decision_sites as _ds        # paso 19: approval.deny sobre el proposal.create
            from core import identity
            with identity.use(principal), _ds.approval(s, 'deny', target_kind='proposal.create',
                                                        target_ref=('proposal', pid),
                                                        parent_id=_ds.proposal_parent(s, pid),
                                                        subject={'action_type': _p.action_type}):
                pass
            return jsonify({'status': 'ok'})
    except _LedgerUnavailable:
        return _ledger_unavailable()


@ontology_bp.route('/agents/brief')
@_require_db
@rate_limit(20, 600)          # abierta pero llama a la IA (tier deep) → con tope por IP
def agents_brief():
    """Cronista: Brief Matinal — no requiere aprobación, es informativo."""
    from ontology.agents import brief_matinal
    try:
        hours = _int_arg('hours', 24, 1, 168)
    except _BadArg as e:
        return _bad_arg(str(e))
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
@rate_limit(30, 600)
def alerts_create():
    """Body: {owner, rule:{entity,metric,op,value} o {region,event_type}, channel?}."""
    from ontology.models import Alert
    body = _body()
    owner = body.get('owner')
    rule = body.get('rule')
    if not owner or not rule:
        return jsonify({'error': "'owner' y 'rule' son requeridos"}), 400
    if not isinstance(rule, dict) or not isinstance(owner, str):
        return jsonify({'error': "'rule' debe ser un objeto y 'owner' un texto",
                        'error_en': "'rule' must be an object and 'owner' a string"}), 400
    if not (rule.get('metric') in ('price', 'nrs', 'news_region') or rule.get('event_type')):
        return jsonify({'error': "rule.metric debe ser 'price'|'nrs'|'news_region'"}), 400
    from core import decision_sites as _ds
    try:
        with session_scope() as s:
            a = Alert(owner=owner, rule=rule, channel=body.get('channel', 'browser'), is_active=True)
            s.add(a)
            s.flush()
            _ds.alert_rule(s, a, 'create')        # paso 19: alert.rule (sync; el dueño solo como hash)
            return jsonify({'status': 'ok', 'alert': _alert_to_dict(a)})
    except _LedgerUnavailable:
        return _ledger_unavailable()


@ontology_bp.route('/alerts/<alert_id>', methods=['DELETE'])
@_require_db
@rate_limit(60, 600)
def alerts_delete(alert_id):
    import uuid as _uuid
    from ontology.models import Alert
    try:
        aid = _uuid.UUID(alert_id)
    except ValueError:
        return jsonify({'error': 'alert_id inválido'}), 400
    from core import decision_sites as _ds
    try:
        with session_scope() as s:
            a = s.get(Alert, aid)
            if not a:
                return jsonify({'error': 'no encontrada'}), 404
            _ds.alert_rule(s, a, 'delete')        # paso 19: la baja también queda (con la regla que se borra)
            s.delete(a)
            return jsonify({'status': 'ok'})
    except _LedgerUnavailable:
        return _ledger_unavailable()


@ontology_bp.route('/alerts/check', methods=['GET'])
@_require_db
@rate_limit(120, 600)
def alerts_check():
    """Evalúa las alertas activas (de `owner` si se pasa) y devuelve las que
    dispararon ahora — el cliente las convierte en notificaciones del navegador."""
    from ontology.agents import check_alerts
    owner = request.args.get('owner')
    with session_scope() as s:
        fired = check_alerts(s, owner=owner)
        return jsonify({'fired': fired, 'count': len(fired)})


@ontology_bp.route('/search')
@_require_db
def search_objects():
    """Búsqueda de entidades desde el SERVIDOR (Phase 1 · M5).

    Hasta ahora buscar era cosa solo del cliente, así que nada fuera del
    navegador (un agente, un script, otra app) podía encontrar una entidad.

    Combina dos caminos: el resolvedor único de M2 —que conoce tickers y la
    tabla de alias del merge, y por eso acierta con "NVDA" o "NVIDIA
    Corporation"— y una búsqueda por texto en la etiqueta para lo demás.
    El resultado dice CÓMO se encontró cada cosa (`match`), para que quien
    consuma pueda exigir más o menos rigor."""
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({'error': "el parámetro 'q' es requerido"}), 400
    tipo = (request.args.get('type') or '').strip() or None
    try:
        limit = min(max(int(request.args.get('limit', 20)), 1), 100)
    except (TypeError, ValueError):
        limit = 20

    resultados, vistos = [], set()

    # 1) coincidencia fuerte: id, ticker o alias (umbral de BÚSQUEDA)
    try:
        from core.entities import UMBRAL_BUSQUEDA, resolve
        r = resolve(q, umbral=UMBRAL_BUSQUEDA)
    except Exception:  # noqa: BLE001 — sin snapshot seguimos con la búsqueda por texto
        r = None

    with session_scope() as s:
        if r:
            obj = get_object(s, r['id'])
            if obj and (not tipo or obj.type == tipo):
                vistos.add(obj.id)
                resultados.append({'id': obj.id, 'label': obj.label, 'type': obj.type,
                                   'score': r['score'], 'match': r['method']})

        # 2) por texto en la etiqueta, para todo lo demás
        for o in list_objects(s, type_=tipo, q=q, limit=limit * 2):
            if o.id in vistos:
                continue
            vistos.add(o.id)
            resultados.append({'id': o.id, 'label': o.label, 'type': o.type,
                               'score': 50, 'match': 'texto'})

    resultados.sort(key=lambda x: -x['score'])
    return jsonify({'query': q, 'count': len(resultados[:limit]),
                    'results': resultados[:limit]})


@ontology_bp.route('/events/<event_id>')
@_require_db
def event_detail(event_id):
    """Un evento concreto, con su procedencia resuelta (Phase 1 · M5)."""
    import uuid as _uuid

    from ontology.models import Event, ObjectRecord
    from ontology.provenance import source_to_dict
    try:
        eid = _uuid.UUID(event_id)
    except ValueError:
        return jsonify({'error': 'event_id inválido'}), 400

    with session_scope() as s:
        ev = s.get(Event, eid)
        if not ev:
            return jsonify({'error': f'evento no encontrado: {event_id}'}), 404
        fuente = None
        if ev.source_id:
            o = s.get(ObjectRecord, ev.source_id)
            if o is not None:
                fuente = source_to_dict(o)
        return jsonify(_mark_genesis({
            'id': str(ev.id), 'event_type': ev.event_type,
            'object_id': ev.object_id, 'target_id': ev.target_id,
            'payload': ev.payload,
            'valid_from': ev.valid_from.isoformat() if ev.valid_from else None,
            'valid_to': ev.valid_to.isoformat() if ev.valid_to else None,
            'recorded_at': ev.recorded_at.isoformat() if ev.recorded_at else None,
            'channel': ev.source, 'actor': ev.actor,
            'confidence': ev.confidence, 'source': fuente,
        }, ev.valid_from))


@ontology_bp.route('/objects/<object_id>/timeline')
@_require_db
def object_timeline(object_id):
    """Qué le ha pasado a esta entidad, en un solo hilo (Phase 1 · M5).
    Fusiona eventos del grafo y noticias, ordenado por cuándo fue cierto en el
    mundo. Query: ?limit=60&lang=es|en&news=0 para excluir noticias."""
    from ontology.timeline import entity_timeline
    lang = (request.args.get('lang') or 'es').strip().lower()[:2]
    incluir_noticias = (request.args.get('news') or '1') not in ('0', 'false', 'no')
    try:
        limit = min(max(int(request.args.get('limit', 60)), 1), 300)
    except (TypeError, ValueError):
        limit = 60

    known_raw = request.args.get('known_at')        # paso 23: ?known_at= (ISO o versión del grafo)
    with session_scope() as s:
        obj = get_object(s, object_id)
        if not obj:
            return jsonify({'error': f'objeto no encontrado: {object_id}'}), 404
        known = None
        if known_raw:
            from ontology import bitemporal
            try:
                known = bitemporal.resolve(s, known_raw)
            except bitemporal.KnownAtError as e:
                return _known_bad(e)
        entradas = entity_timeline(s, object_id, limit=limit, lang=lang,
                                   include_news=incluir_noticias, known=known)
        out = {'object_id': object_id, 'label': obj.label,
               'type': obj.type, 'count': len(entradas),
               'timeline': entradas}
        if known is not None:
            out.update(known.to_dict())
        return jsonify(out)


@ontology_bp.route('/feed')
@_require_db
def global_feed_route():
    """Lo último que entró al grafo ENTERO (M6): noticias, relaciones nuevas
    o terminadas, tesis y acciones — sin la migración ni los precios.
    Query: ?limit=30&lang=es|en&since=<ISO> (solo lo registrado después)."""
    from ontology.timeline import global_feed
    from ontology.service import _parse_dt
    lang = (request.args.get('lang') or 'es').strip().lower()[:2]
    try:
        limit = min(max(int(request.args.get('limit', 30)), 1), 200)
    except (TypeError, ValueError):
        limit = 30
    since = None
    if request.args.get('since'):
        try:
            since = _parse_dt(request.args.get('since'))
        except Exception:
            since = None
        if since is None:
            return jsonify({'error': 'since inválido (usa ISO 8601)'}), 400
    # FRESCURA (2026-10-04, "veo noticias viejas como si fueran lo último"): por
    # defecto solo lo registrado en los últimos `days` (14). Si no hay nada, se
    # devuelve la fecha de lo último que entró para decirlo claramente.
    from datetime import datetime, timedelta, timezone
    try:
        days = max(1, min(int(request.args.get('days', 14)), 365))
    except (TypeError, ValueError):
        days = 14
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    if since is None or since < cutoff:
        since = cutoff
    with session_scope() as s:
        entradas = global_feed(s, limit=limit, lang=lang, since=since)
        last_at = None
        if not entradas:
            from sqlalchemy import select
            from ontology.models import Event
            last = s.scalars(select(Event.recorded_at).where(~Event.source.like('migration%'), Event.event_type != 'PriceObserved')
                             .order_by(Event.recorded_at.desc()).limit(1)).first()
            last_at = last.isoformat() if last else None
        return jsonify({'count': len(entradas), 'feed': entradas, 'days': days, 'last_at': last_at})


@ontology_bp.route('/objects/<object_id>/news')
@_require_db
def object_news(object_id):
    """Noticias que informan sobre una entidad, ya en el grafo (Phase 1 · M4).
    Solo LEE: no dispara ingesta, para que abrir una ficha no provoque
    llamadas a proveedores externos sin que nadie lo pida."""
    from ontology.ingest_news import news_for_object
    try:
        limit = min(max(int(request.args.get('limit', 20)), 1), 200)
    except (TypeError, ValueError):
        limit = 20
    with session_scope() as s:
        obj = get_object(s, object_id)
        if not obj:
            return jsonify({'error': f'objeto no encontrado: {object_id}'}), 404
        items = news_for_object(s, object_id, limit=limit)
        return jsonify({'object_id': object_id, 'label': obj.label,
                        'count': len(items), 'news': items})


@ontology_bp.route('/ingest/news', methods=['POST'])
@_require_db
@rate_limit(60, 600)          # abierta (observación con fuente) pero llama a proveedores → tope por IP
def ingest_news():
    """Ingiere noticias de una entidad AL GRAFO (Phase 1 · M4).
    Body: {entity_id, query?, limit?, actor?}.

    Escribe: crea `NewsItem` + `Source` y los enlaza con `reports_on` /
    `published_by`. Es idempotente (el id sale de la URL), así que repetirlo no
    duplica. La noticia entra directo por ser una observación con fuente
    comprobable; su interpretación sigue pasando por la cola de aprobación."""
    from ontology.ingest_news import ingest_news_for
    body = _body()
    entity_id = (body.get('entity_id') or '').strip()
    if not entity_id:
        return jsonify({'error': 'entity_id es requerido'}), 400
    declared = (body.get('actor') or '').strip()
    if not declared:
        return jsonify({'error': 'actor es requerido — toda escritura queda atribuida'}), 400
    # paso 5: ruta abierta → events.actor = principal AUTENTICADO (ui:anon sin PIN); el texto libre no puede
    # hacerse pasar por 'op:fabrizio' (queda solo como etiqueta en el principal).
    actor = _principal(declared).id
    try:
        limit = min(max(int(body.get('limit', 10)), 1), 50)
    except (TypeError, ValueError):
        limit = 10

    from core import decisions as _decisions
    try:
        # cierre del lote H (E3): las noticias que entran al grafo dejan su decisión `ontology.news_ingest` (misma
        # transacción; efectos = los eventos escritos). Sin ningún evento nuevo → 'noop'.
        with session_scope() as s, _decisions.decision_scope(
                'ontology.news_ingest', _principal(declared), session=s,
                subject={'entity_id': entity_id[:120], 'limit': limit}) as dctx:
            res = ingest_news_for(s, entity_id, query=body.get('query'),
                                  limit=limit, actor=actor)
            dctx.output = {k: res.get(k) for k in ('ok', 'fetched', 'ingested', 'new', 'skipped_no_url')}
            dctx.output['errors'] = len(res.get('errors') or [])
            if not res.get('ok'):
                dctx.status = 'rejected'
            elif not any(k[0] == 'effect' for k in dctx.refs):
                dctx.status = 'noop'            # todo ya estaba (idempotente): ningún evento escrito
            res['decision_id'] = str(dctx.id)
    except _LedgerUnavailable:
        return _ledger_unavailable()
    # PHASE 2 · event-driven: noticias NUEVAS de una entidad = evento NEWS →
    # router → agentes suscritos (QUICK, dedupe 24 h, tope diario). Apagado
    # por defecto por costo: RESEARCH_AUTO_EVENTS=on en Railway lo activa.
    try:
        import os
        if res.get('ok') and res.get('new') and os.getenv('RESEARCH_AUTO_EVENTS', 'off').lower() == 'on':
            from research.router import dispatch_event
            with session_scope() as s2:
                res['research'] = dispatch_event(s2, {
                    'type': 'NEWS', 'entities': [entity_id], 'depth': 'QUICK',
                    'headline': f"{res.get('new')} noticias nuevas de {entity_id}"}, actor='event:news-ingest')
            res['research'] = {k: res['research'].get(k) for k in ('event_type', 'agents', 'jobs', 'reason')}
    except Exception as e:  # noqa: BLE001 — la investigación nunca tumba la ingesta
        res['research_error'] = type(e).__name__
    return (jsonify(res), 200) if res.get('ok') else (jsonify(res), 404)


@ontology_bp.route('/sources')
@_require_db
def sources_list():
    """Documentos que respaldan hechos del grafo (Phase 1 · M1).
    Query: ?kind=primary&min_trust=2&limit=50. Ordenadas por confiabilidad."""
    from sqlalchemy import select
    from ontology.models import ObjectRecord
    from ontology.provenance import SOURCE_TYPE, source_to_dict

    kind = (request.args.get('kind') or '').strip().lower()
    try:
        min_trust = int(request.args.get('min_trust', 0))
    except (TypeError, ValueError):
        min_trust = 0
    try:
        limit = min(max(int(request.args.get('limit', 50)), 1), 500)
    except (TypeError, ValueError):
        limit = 50

    with session_scope() as s:
        objs = s.scalars(select(ObjectRecord).where(ObjectRecord.type == SOURCE_TYPE)).all()
        out = [source_to_dict(o) for o in objs]
    if kind:
        out = [x for x in out if (x.get('kind') or '') == kind]
    if min_trust:
        out = [x for x in out if (x.get('trust') or 0) >= min_trust]
    out.sort(key=lambda x: (-(x.get('trust') or 0), x.get('publisher') or ''))
    return jsonify({'count': len(out), 'sources': out[:limit]})


@ontology_bp.route('/objects/<object_id>/provenance')
@_require_db
def object_provenance(object_id):
    """De dónde salió lo que sabemos de este objeto: las fuentes que lo
    evidencian y los eventos que las citan (con fecha y confianza).

    Es el camino `Graph Claim → Source → evidencia original` que pide la
    especificación. Una lista vacía significa exactamente eso — que el hecho
    aún no tiene documento detrás — y no se disfraza."""
    from ontology.provenance import provenance_for_object
    with session_scope() as s:
        obj = get_object(s, object_id)
        if not obj:
            return jsonify({'error': f'objeto no encontrado: {object_id}'}), 404
        fuentes = provenance_for_object(s, object_id)
        return jsonify({'object_id': object_id, 'label': obj.label,
                        'count': len(fuentes), 'sources': fuentes})


@ontology_bp.route('/events', methods=['POST'])
@_require_db
@require_operator
@rate_limit(120, 600)
def events_create():
    """Escritura de bajo nivel. En Fase 2 esto se envuelve con el catálogo de
    Acciones (validación por tipo, auditoría de actor humano). Por ahora
    requiere explícitamente source+actor para que nada quede sin trazar."""
    body = _body()
    required = ('event_type', 'valid_from', 'source', 'actor')
    missing = [k for k in required if not body.get(k)]
    if missing:
        return jsonify({'error': f'faltan campos: {", ".join(missing)}'}), 400
    from core import decisions as _decisions
    principal = _principal(body['actor'])
    did = {}
    try:
        # cierre del lote H (E1): el evento crudo deja su decisión `ontology.raw_event` en la MISMA transacción
        with session_scope() as s, _decisions.decision_scope(
                'ontology.raw_event', principal, session=s,
                subject={'event_type': str(body['event_type'])[:40], 'object_id': body.get('object_id'),
                         'target_id': body.get('target_id')}) as dctx:
            did['id'] = str(dctx.id)
            ev = apply_event(
                s, event_type=body['event_type'], payload=body.get('payload', {}),
                valid_from=body['valid_from'], valid_to=body.get('valid_to'),
                source=body['source'], actor=principal.id,   # paso 5: el principal
                object_id=body.get('object_id'), target_id=body.get('target_id'),
            )
            s.flush()
            dctx.output = {'event_id': str(ev.id), 'event_type': ev.event_type}
            res = {'status': 'ok', 'event': _event_to_dict(ev), 'decision_id': did['id']}
        return jsonify(res)
    except _GateViolation as e:
        return _gate_violation(e, did.get('id'))
    except OntologyError as e:
        return jsonify({'error': str(e), 'decision_id': did.get('id')}), 400
    except _LedgerUnavailable:
        return _ledger_unavailable()


# ── G3 (misión de reparación 2026-10-04): reconciliación catálogo ↔ base ──────
# Solo lectura por defecto. Aplicar/deshacer = PIN de operador + nombre EXACTO
# de la base (lo devuelve el plan) + actor; todo por eventos (ontology/reconcile.py).
_RECON_CACHE = {'ts': 0.0, 'key': None, 'data': None}
import threading as _threading  # noqa: E402
_RECON_BUILD = _threading.Lock()     # G5: un solo cálculo del plan a la vez (no se puede saturar el servidor)


def _recon_plan(fresh=False):
    import time as _t
    from ontology import reconcile as R
    snap = R.load_snapshot()
    key = snap.get('exported_at')

    def cached():
        if _RECON_CACHE['data'] is not None and _RECON_CACHE['key'] == key:
            return _RECON_CACHE['data']
        return None
    if not fresh and cached() is not None and _t.time() - _RECON_CACHE['ts'] < 120:
        return snap, cached()
    if not _RECON_BUILD.acquire(timeout=25):
        if cached() is not None:
            return snap, cached()            # otro pedido ya lo está calculando: se sirve el último
        raise TimeoutError('plan en cálculo')
    try:
        if not fresh and cached() is not None and _t.time() - _RECON_CACHE['ts'] < 120:
            return snap, cached()
        with session_scope() as s:
            plan = R.build_plan(s, snap)
            plan['db'] = R._db_name(s)
            plan['runs'] = R.list_runs(s, limit=10)
        _RECON_CACHE.update(ts=_t.time(), key=key, data=plan)
        return snap, plan
    finally:
        _RECON_BUILD.release()


@ontology_bp.route('/reconcile/plan')
@_require_db
@rate_limit(20, 600)
def reconcile_plan():
    """Dry-run: ?format=json (default) | md | html · ?lang=es|en · ?fresh=1.
    No escribe nada."""
    from flask import Response
    from ontology import reconcile as R
    fmt = (request.args.get('format') or 'json').lower()
    lang = 'en' if (request.args.get('lang') or '').lower() == 'en' else 'es'
    fresh = False
    if request.args.get('fresh') == '1':      # G5: recalcular a demanda solo con PIN de operador
        err = pin_error(where='reconcile_plan', strict=True)
        if err:
            return err                        # G6b: un PIN malo NO recibe un plan viejo como si fuera fresco
        fresh = True
    try:
        _snap, plan = _recon_plan(fresh=fresh)
    except FileNotFoundError:
        return jsonify({'error': 'falta data/grafo_v0.json en el servidor', 'error_en': 'data/grafo_v0.json is missing on '
                        'the server', 'code': 'no_snapshot'}), 503
    except TimeoutError:
        return jsonify({'error': 'el plan se está calculando; reintenta en unos segundos',
                        'error_en': 'the plan is being computed; retry in a few seconds', 'code': 'busy'}), 503
    if fmt == 'md':
        return Response(R.render_markdown(plan, dbname=plan.get('db'), lang=lang, limit_rows=500),
                        mimetype='text/markdown; charset=utf-8')
    if fmt == 'html':
        md = R.render_markdown(plan, dbname=plan.get('db'), lang=lang, limit_rows=500)
        return Response(R.markdown_to_html(md, title='Khipus · ' + ('Graph review' if lang == 'en' else 'Revisión del grafo')),
                        mimetype='text/html; charset=utf-8')
    if request.args.get('summary') == '1':
        return jsonify({k: plan.get(k) for k in ('summary', 'out_of_scope', 'db', 'as_of', 'snapshot', 'default_apply', 'runs',
                                                 'plan_sha')})
    return jsonify(plan)


def _strict_operator():
    """G5: reconcile exige un PIN de operador CONFIGURADO (sin TRADE_PIN → 403, no 'modo desarrollo')."""
    return pin_error(where='reconcile', strict=True)


def _strict_operator_required(fn):
    """G6b: el PIN se comprueba ANTES del límite de frecuencia: un PIN viejo no
    agota el cupo de aplicar/deshacer de la IP del operador."""
    from functools import wraps

    @wraps(fn)
    def wrapper(*a, **k):
        err = _strict_operator()
        if err:
            return err
        return fn(*a, **k)
    return wrapper


def _str_arg(b, k, n):
    v = b.get(k)
    return v.strip()[:n] if isinstance(v, str) else ''


@ontology_bp.route('/reconcile/apply', methods=['POST'])
@_require_db
@_strict_operator_required
@rate_limit(5, 600)
def reconcile_apply():
    """Body: {actor, confirm_db, include: ['alias','duplicates',…], expect: {cat: n}}. Devuelve run_id."""
    from ontology import reconcile as R
    b = _body()
    actor = _str_arg(b, 'actor', 80)
    if not actor:
        return jsonify({'error': 'actor requerido', 'error_en': 'actor is required'}), 400
    principal = _principal(actor)
    actor = principal.id                       # paso 5: se registra el principal (op:fabrizio), no el texto
    include = b.get('include') or list(R.DEFAULT_APPLY)
    if not isinstance(include, list) or any(c not in R.CATEGORIES for c in include):
        return jsonify({'error': f'include inválido; válidas: {list(R.CATEGORIES)}',
                        'error_en': f'invalid include; valid: {list(R.CATEGORIES)}'}), 400
    expect = b.get('expect') if isinstance(b.get('expect'), dict) else None
    # paso 11: `expect` OBLIGATORIO y atado a la huella del plan revisado (GET /reconcile/plan → plan_sha)
    if expect is None or not isinstance(expect.get('plan_sha'), str) or len(expect['plan_sha']) != 64:
        return jsonify({'error': 'falta expect con la huella del plan que revisaste (plan_sha): vuelve a abrir la lista',
                        'error_en': 'expect with the fingerprint of the plan you reviewed (plan_sha) is required: '
                                    'reopen the list', 'code': 'expect_required'}), 400
    if not all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for k, v in expect.items() if k != 'plan_sha'):
        return jsonify({'error': 'expect debe ser {categoría: número, plan_sha}',
                        'error_en': 'expect must be {category: number, plan_sha}'}), 400
    try:
        res = R.apply_plan(session_scope, R.load_snapshot(), include=include, confirm_db=_str_arg(b, 'confirm_db', 120),
                           actor=actor, expect=expect, principal=principal)
    except _LedgerUnavailable:
        return _ledger_unavailable()
    except R.ReconcileError as e:
        return jsonify({'error': str(e), 'error_en': e.en}), 409 if 'en curso' in str(e) or 'cambió' in str(e) else 400
    except (OntologyError, ValueError) as e:
        return jsonify({'error': str(e)[:300], 'error_en': str(e)[:300]}), 400
    _RECON_CACHE.update(data=None)
    if res.get('error'):
        return jsonify({'status': 'partial', **res, 'error_es': f"falló en «{res['error']['category']}»: lo anterior quedó "
                        f"aplicado; se puede deshacer con {res['run_id']}", 'error_en': f"failed at '{res['error']['category']}': "
                        f"earlier categories were applied; undo with {res['run_id']}"}), 409
    return jsonify({'status': 'ok', **res})


@ontology_bp.route('/reconcile/rollback', methods=['POST'])
@_require_db
@_strict_operator_required
@rate_limit(5, 600)
def reconcile_rollback():
    """Body: {actor, confirm_db, run_id}. Deshace con eventos nuevos."""
    from ontology import reconcile as R
    b = _body()
    actor = _str_arg(b, 'actor', 80)
    run_id = _str_arg(b, 'run_id', 60)
    if not actor or not run_id:
        return jsonify({'error': 'actor y run_id requeridos', 'error_en': 'actor and run_id are required'}), 400
    principal = _principal(actor)
    actor = principal.id
    try:
        with session_scope() as s:
            res = R.rollback_run(s, run_id, confirm_db=_str_arg(b, 'confirm_db', 120), actor=actor, principal=principal)
    except _LedgerUnavailable:
        return _ledger_unavailable()
    except R.ReconcileError as e:
        return jsonify({'error': str(e), 'error_en': e.en}), 409 if 'en curso' in str(e) else 400
    except (OntologyError, ValueError) as e:
        return jsonify({'error': str(e)[:300], 'error_en': str(e)[:300]}), 400
    _RECON_CACHE.update(data=None)
    return jsonify({'status': 'ok', **res})


# ── EXPANSION_5K E2.4: importación de fichas khipus.company/1 (ontology/company_import.py) ────────────────────
# Subida en TROZOS (MAX_CONTENT_LENGTH es 1 MB: cada trozo ≤ policy.import.upload_chunk_max_bytes comprimido),
# plan PURO (sin escritura; cacheado por archivo + categorías aprobadas + generación del grafo), aplicar con PIN +
# `expect.plan_sha` (si el plan o el grafo cambiaron → 409) + mismo candado consultivo que reconcile, deshacer y
# corridas. Toda escritura deja UNA decisión (ontology.bulk_import / ontology.import_rollback) o responde 503.
import base64 as _b64  # noqa: E402
import hashlib as _hashlib  # noqa: E402
import zlib as _zlib  # noqa: E402

_IMPORT_UPLOADS = {}                     # sha → {'name', 'chunks': {i: bytes}, 'n', 'at'}  (1 worker: memoria)
_IMPORT_PLAN_CACHE = {'key': None, 'plan': None, 'ts': 0.0}
_IMPORT_LOCK = _threading.Lock()
_IMPORT_UPLOAD_TTL_S = 1800
_IMPORT_UPLOADS_MAX = 8                  # subidas a medias a la vez (un cliente mal hecho no agota la RAM)
_IMPORT_UPLOAD_MAX_BYTES = 64 * 1024 * 1024   # tope del archivo entero (sin comprimir) retenido en memoria


def _import_mod():
    from ontology import company_import as CI
    return CI


def _import_file(sha):
    """Paquete (records/updates/approve_categories) guardado en import_files, o None."""
    from ontology import import_models
    CI = _import_mod()
    if not import_models.ensure_tables():
        return None
    with session_scope() as s:
        row = s.get(import_models.ImportFile, sha)
        if row is None:
            return None
        text = _zlib.decompress(row.content).decode('utf-8')
        name = row.name
    return CI.parse_bundle(text, name=name)


def _import_bundle_from_body(b):
    """(paquete, file_sha) desde el cuerpo: `file_sha` (archivo subido), `package` (un paquete del REPOSITORIO por su
    NOMBRE de GET /import/packages; E2.7) o fichas en línea (records/updates)."""
    CI = _import_mod()
    sha = _str_arg(b, 'file_sha', 64)
    pkg = _str_arg(b, 'package', 160)
    if pkg and (sha or b.get('records') is not None):
        raise CI.ImportProblem('manda UNA sola fuente: package, file_sha o records',
                               'send ONE source only: package, file_sha or records', 'ambiguous_source')
    if pkg:
        cached, sha, _meta = _import_package(pkg)
        bundle = dict(cached)               # copia: approve_categories/batch del cuerpo no tocan la caché
        bundle['records'], bundle['updates'] = list(cached['records']), list(cached['updates'])
        bundle['approve_categories'] = list(cached.get('approve_categories') or [])
        _pkg_release()                      # la copia vive lo que dura el pedido; la caché no retiene las fichas
    elif sha:
        bundle = _import_file(sha)
        if bundle is None:
            raise CI.ImportProblem('archivo no encontrado: súbelo primero (POST /api/ontology/import/files)',
                                   'file not found: upload it first (POST /api/ontology/import/files)', 'file_not_found')
    else:
        recs = b.get('records')
        if not isinstance(recs, list):
            raise CI.ImportProblem('falta file_sha o records', 'file_sha or records is required', 'records_required')
        bundle = {'records': recs, 'updates': list(b.get('updates') or []), 'approve_categories': [], 'batch': None}
        sha = None
    if isinstance(b.get('approve_categories'), list):
        bundle['approve_categories'] = [c for c in b['approve_categories'] if isinstance(c, dict)]
    if _str_arg(b, 'batch', 60):
        bundle['batch'] = _str_arg(b, 'batch', 60)
    return bundle, sha


def _import_view_current():
    """La vista rápida en la versión de la BASE (para aplicar): si va atrás, pide la reconstrucción y espera hasta
    HOT_WAIT_S; si no llega → ImportProblem graph_stale (409: inténtalo en unos segundos)."""
    from core.hotviews import builder, hot, signals
    CI = _import_mod()
    view = hot.graph()
    if view is None or view.source != 'pg':
        return view
    try:
        with session_scope() as s:
            dbv = signals.read_db_version(s)
    except Exception:  # noqa: BLE001
        dbv = None
    if not dbv or dbv[0] == view.graph_version:
        return view
    g = builder.ensure(dbv[0], dbv[1], timeout=hot.HOT_WAIT_S)
    view = hot.graph()
    if g is None or view is None or view.graph_version != dbv[0]:
        raise CI.ImportProblem(f'la vista rápida (versión {view.graph_version if view else "?"}) va atrás de la base '
                               f'(versión {dbv[0]}): inténtalo en unos segundos',
                               f'the hot view (version {view.graph_version if view else "?"}) lags the database '
                               f'(version {dbv[0]}): try again in a few seconds', 'graph_stale')
    return view


def _import_plan_for(bundle, sha, fresh=False, current=False, sanitize=False):
    """El plan del paquete sobre la generación VIGENTE (cacheado: mismo archivo + categorías + generación).
    `current=True` (aplicar): la vista debe estar en la versión de la base (_import_view_current). `sanitize=True`
    (cuerpo `sanitize: 1`, lo manda el panel para archivos SUBIDOS): pasa antes el saneador de FORMATO
    (company_import.sanitize_batch, idempotente; plan y aplicar deben pedirlo igual o la huella no coincide → 409)."""
    from core.hotviews import hot
    CI = _import_mod()
    view = _import_view_current() if current else hot.graph()
    if view is None:
        raise CI.ImportProblem('grafo no disponible', 'graph unavailable', 'graph_unavailable')
    key = (sha or CI._sha(bundle['records'] + bundle['updates']), CI._sha(bundle.get('approve_categories') or []),
           bundle.get('batch'), view.generation, bool(sanitize))
    with _IMPORT_LOCK:
        if not fresh and _IMPORT_PLAN_CACHE['key'] == key and _IMPORT_PLAN_CACHE['plan'] is not None:
            return _IMPORT_PLAN_CACHE['plan'], view
        pending = []
        if ontology_available():
            try:
                with session_scope() as s:
                    pending = CI.pending_links(s, limit=None)       # TODOS (antes: los 500 más nuevos)
            except Exception:  # noqa: BLE001 — sin pendientes el plan sale igual
                pending = []
        p = CI.plan(bundle['records'], bundle['updates'], view=view, batch=bundle.get('batch'),
                    approve_categories=bundle.get('approve_categories'), pending=pending, sanitize=bool(sanitize))
        _IMPORT_PLAN_CACHE.update(key=key, plan=p, ts=time.time())
        return p, view


def _import_plan_summary(p, full=False):
    if full:
        return p
    out = {k: v for k, v in p.items() if k not in ('items', 'updates', 'sources', 'pending_resolved')}
    out['items'] = [{'record_id': it['record_id'], 'name': it.get('name'), 'action': it['action'], 'id': it.get('id'),
                     'method': it.get('method'), 'score': it.get('score'), 'priority': it.get('priority'),
                     'conflicts': it.get('conflicts') or [], 'warnings': [w.get('code') for w in it.get('warnings') or []],
                     'links': [{'relation_id': l.get('relation_id'), 'rel_type': l.get('rel_type'), 'route': l.get('route'),
                                'reason': l.get('reason'), 'counterparty': (l.get('counterparty') or {}).get('name'),
                                'target': l.get('target'), 'source': l.get('source')} for l in it.get('links') or []]}
                    for it in p['items']]
    out['updates'] = [{'khipus_id': u.get('khipus_id'), 'action': u['action'], 'reason': u.get('reason'),
                       'keys': sorted(k for k in (u.get('props') or {}) if k != 'country_facts'),
                       'conflicts': u.get('conflicts') or []} for u in p['updates']]
    out['pending_resolved'] = len(p.get('pending_resolved') or [])
    out['sources_new'] = len(p.get('sources') or [])
    return out


def _import_error(e):
    CI = _import_mod()
    if isinstance(e, CI.ImportProblem):
        code = 409 if e.code in ('plan_changed', 'graph_changed', 'graph_stale', 'later_runs', 'already_rolled_back', 'busy') \
            else (404 if e.code in ('file_not_found', 'run_not_found', 'package_not_found')
                  else (503 if e.code in ('graph_unavailable', 'import_tables_unavailable') else 400))
        return jsonify({'error': str(e), 'error_en': e.en, 'code': e.code}), code
    from ontology.reconcile import ReconcileError
    if isinstance(e, ReconcileError):
        return jsonify({'error': str(e), 'error_en': e.en, 'code': 'busy' if 'en curso' in str(e) else 'rejected'}), \
            409 if 'en curso' in str(e) else 400
    return jsonify({'error': str(e)[:300], 'error_en': str(e)[:300]}), 400


@ontology_bp.route('/import/files', methods=['POST'])
@_require_db
@_strict_operator_required
@rate_limit(240, 600)
def import_files():
    """Subida por trozos. Body: {name, sha256 (del contenido entero sin comprimir), chunk, chunks, data (base64 del
    trozo comprimido con zlib), encoding: 'zlib'|'none'}. Con el último trozo: se verifica el sha, se cuenta el
    paquete y se guarda en import_files (decisión ontology.bulk_import, etapa 'upload'). Respuesta: {status: partial|
    stored, received, sha256, n_records, n_updates, batch}."""
    from core import decisions as _decisions
    from ontology import import_models
    CI = _import_mod()
    b = _body()
    sha = _str_arg(b, 'sha256', 64).lower()
    name = _str_arg(b, 'name', 200) or 'import.json'
    try:
        idx, n = int(b.get('chunk', 0)), int(b.get('chunks', 1))
    except (TypeError, ValueError):
        return jsonify({'error': 'chunk/chunks deben ser enteros', 'error_en': 'chunk/chunks must be integers'}), 400
    if len(sha) != 64 or idx < 0 or n < 1 or idx >= n or n > 400:
        return jsonify({'error': 'sha256 (64 hex), chunk y chunks válidos requeridos',
                        'error_en': 'valid sha256 (64 hex), chunk and chunks are required'}), 400
    try:
        raw = _b64.b64decode(str(b.get('data') or ''), validate=True)
    except (ValueError, TypeError):
        return jsonify({'error': 'data no es base64', 'error_en': 'data is not base64'}), 400
    limit = int(CI.policy('upload_chunk_max_bytes'))
    if len(raw) > limit:
        return jsonify({'error': f'trozo mayor que {limit} bytes', 'error_en': f'chunk larger than {limit} bytes',
                        'code': 'chunk_too_big'}), 413
    if (b.get('encoding') or 'zlib') == 'zlib':
        # el tope se mide DESCOMPRIMIDO (un trozo zlib de 1 KB puede expandirse a 1 GB y tumbar el único worker)
        try:
            d = _zlib.decompressobj()
            raw = d.decompress(raw, limit + 1)
            if len(raw) > limit or d.unconsumed_tail:
                return jsonify({'error': f'trozo mayor que {limit} bytes al descomprimir',
                                'error_en': f'chunk larger than {limit} bytes once decompressed', 'code': 'chunk_too_big'}), 413
        except _zlib.error:
            return jsonify({'error': 'el trozo no es zlib', 'error_en': 'chunk is not zlib'}), 400
    now = time.time()
    with _IMPORT_LOCK:
        for k in [k for k, v in _IMPORT_UPLOADS.items() if now - v['at'] > _IMPORT_UPLOAD_TTL_S]:
            _IMPORT_UPLOADS.pop(k, None)
        if sha not in _IMPORT_UPLOADS and len(_IMPORT_UPLOADS) >= _IMPORT_UPLOADS_MAX:
            return jsonify({'error': 'demasiadas subidas a medias; espera a que terminen', 'error_en': 'too many uploads in '
                            'progress; wait for them to finish', 'code': 'too_many_uploads'}), 429
        up = _IMPORT_UPLOADS.setdefault(sha, {'name': name, 'chunks': {}, 'n': n, 'at': now})
        if sum(len(c) for i, c in up['chunks'].items() if i != idx) + len(raw) > _IMPORT_UPLOAD_MAX_BYTES:
            _IMPORT_UPLOADS.pop(sha, None)
            return jsonify({'error': f'archivo mayor que {_IMPORT_UPLOAD_MAX_BYTES // (1024 * 1024)} MB',
                            'error_en': f'file larger than {_IMPORT_UPLOAD_MAX_BYTES // (1024 * 1024)} MB',
                            'code': 'file_too_big'}), 413
        up['chunks'][idx] = raw
        up['at'] = now
        if len(up['chunks']) < n:
            return jsonify({'status': 'partial', 'received': len(up['chunks']), 'chunks': n, 'sha256': sha})
        content = b''.join(up['chunks'][i] for i in range(n))
        _IMPORT_UPLOADS.pop(sha, None)
    if _hashlib.sha256(content).hexdigest() != sha:
        return jsonify({'error': 'el sha256 no coincide con el contenido recibido', 'error_en': 'sha256 does not match the '
                        'received content', 'code': 'sha_mismatch'}), 400
    try:
        bundle = CI.parse_bundle(content.decode('utf-8'), name=name)
    except (CI.ImportProblem, ValueError, UnicodeDecodeError) as e:
        return jsonify({'error': f'archivo ilegible: {str(e)[:200]}', 'error_en': f'unreadable file: {str(e)[:200]}',
                        'code': 'bad_file'}), 400
    if not import_models.ensure_tables():
        return jsonify({'error': 'tablas del importador no disponibles', 'error_en': 'import tables unavailable',
                        'code': 'import_tables_unavailable'}), 503
    principal = _principal(_str_arg(b, 'actor', 80) or None)
    try:
        with session_scope() as s, _decisions.decision_scope(
                'ontology.bulk_import', principal, session=s,
                subject={'import': True, 'stage': 'upload', 'file_sha': sha, 'name': name[:120],
                         'n_records': len(bundle['records']), 'n_updates': len(bundle['updates'])}) as dctx:
            if s.get(import_models.ImportFile, sha) is None:
                s.add(import_models.ImportFile(sha256=sha, name=name, size_bytes=len(content), n_records=len(bundle['records']),
                                               content_type='jsonl' if name.endswith('.jsonl') else 'json',
                                               content=_zlib.compress(content, 6), uploaded_by=principal.id[:96]))
                dctx.output = {'stored': True, 'file_sha': sha, 'n_records': len(bundle['records'])}
            else:
                dctx.output = {'stored': False, 'already': True, 'file_sha': sha}
                dctx.status = 'noop'
            dctx.status = dctx.status or 'recorded'
    except _LedgerUnavailable:
        return _ledger_unavailable()
    _IMPORT_PLAN_CACHE.update(key=None, plan=None)
    return jsonify({'status': 'stored', 'sha256': sha, 'name': name, 'n_records': len(bundle['records']),
                    'n_updates': len(bundle['updates']), 'batch': bundle.get('batch'),
                    'approve_categories': len(bundle.get('approve_categories') or [])})


@ontology_bp.route('/import/plan', methods=['POST'])
@_require_db
@_strict_operator_required
@rate_limit(30, 600)
def import_plan():
    """Plan PURO (no escribe): {file_sha | package | records[, updates], approve_categories?, batch?, full?: 0|1,
    format?: json|md, lang?: es|en, fresh?: 0|1, sanitize?: 0|1, view?: 'panel'}. Devuelve el resumen con `plan_sha` (`full=1`: con
    propiedades y vínculos; `view='panel'`: el resumen corto del panel 🩺 → 📥, _import_panel_summary)."""
    from flask import Response
    CI = _import_mod()
    b = _body()
    try:
        bundle, sha = _import_bundle_from_body(b)
        p, _view = _import_plan_for(bundle, sha, fresh=bool(b.get('fresh')), sanitize=bool(b.get('sanitize')))
    except Exception as e:  # noqa: BLE001
        return _import_error(e)
    if (b.get('format') or 'json') == 'md':
        lang = 'en' if (b.get('lang') or '').lower() == 'en' else 'es'
        return Response(CI.render_summary(p, lang=lang), mimetype='text/markdown; charset=utf-8')
    if b.get('view') == 'panel':
        return jsonify({'status': 'ok', 'file_sha': sha, 'plan': _import_panel_summary(p)})
    return jsonify({'status': 'ok', 'file_sha': sha, 'plan': _import_plan_summary(p, full=bool(b.get('full')))})


@ontology_bp.route('/import/apply', methods=['POST'])
@_require_db
@_strict_operator_required
@rate_limit(5, 600)
def import_apply():
    """Aplica el plan que la persona revisó: {file_sha | package | records, approve_categories?, batch?, confirm_db, expect:
    {plan_sha}, sanitize?: 0|1}. Se recalcula el plan sobre la generación vigente; otra huella → 409 plan_changed. UNA
    decisión ontology.bulk_import; sin libro → 503."""
    CI = _import_mod()
    b = _body()
    expect = b.get('expect') if isinstance(b.get('expect'), dict) else None
    if expect is None or not isinstance(expect.get('plan_sha'), str) or len(expect['plan_sha']) != 64:
        return jsonify({'error': 'falta expect con la huella del plan que revisaste (plan_sha)',
                        'error_en': 'expect with the fingerprint of the plan you reviewed (plan_sha) is required',
                        'code': 'expect_required'}), 400
    confirm_db = _str_arg(b, 'confirm_db', 120) or None
    if not confirm_db:
        return jsonify({'error': 'falta confirm_db (el nombre EXACTO de la base, como en reconcile)',
                        'error_en': 'confirm_db (the EXACT database name, as in reconcile) is required',
                        'code': 'confirm_required'}), 400
    principal = _principal(_str_arg(b, 'actor', 80) or None)
    try:
        bundle, sha = _import_bundle_from_body(b)
        p, view = _import_plan_for(bundle, sha, fresh=True, current=True, sanitize=bool(b.get('sanitize')))
        res = CI.apply_run(session_scope, p, principal, confirm_db=confirm_db, expect=expect, file_sha=sha, view=view)
    except _LedgerUnavailable:
        return _ledger_unavailable()
    except _GateViolation as e:
        return _gate_violation(e)
    except Exception as e:  # noqa: BLE001
        return _import_error(e)
    _IMPORT_PLAN_CACHE.update(key=None, plan=None)
    # objects_created cuenta también las FUENTES nuevas (Source); el panel muestra EMPRESAS: los conteos del plan que
    # se aplicó (la huella coincidió, así que son exactamente estos)
    return jsonify({'status': 'ok', **res, 'plan_counts': p['counts']})


@ontology_bp.route('/import/rollback', methods=['POST'])
@_require_db
@_strict_operator_required
@rate_limit(5, 600)
def import_rollback():
    """Deshace una corrida: {run_id, confirm_db}. Decisión ontology.import_rollback; de la más nueva a la más vieja."""
    CI = _import_mod()
    b = _body()
    run_id = _str_arg(b, 'run_id', 60)
    if not run_id:
        return jsonify({'error': 'run_id requerido', 'error_en': 'run_id is required'}), 400
    confirm_db = _str_arg(b, 'confirm_db', 120) or None
    if not confirm_db:
        return jsonify({'error': 'falta confirm_db (el nombre EXACTO de la base, como en reconcile)',
                        'error_en': 'confirm_db (the EXACT database name, as in reconcile) is required',
                        'code': 'confirm_required'}), 400
    principal = _principal(_str_arg(b, 'actor', 80) or None)
    try:
        with session_scope() as s:
            res = CI.rollback_run(s, run_id, principal, confirm_db=confirm_db)
    except _LedgerUnavailable:
        return _ledger_unavailable()
    except Exception as e:  # noqa: BLE001
        return _import_error(e)
    _IMPORT_PLAN_CACHE.update(key=None, plan=None)
    return jsonify({'status': 'ok', **res})


@ontology_bp.route('/import/runs')
@_require_db
@rate_limit(60, 600)
def import_runs():
    """Corridas aplicadas/deshechas (las más nuevas primero) y cuántos vínculos esperan su contraparte."""
    CI = _import_mod()
    try:
        with session_scope() as s:
            runs = CI.list_runs(s, limit=_int_arg('limit', 20, 1, 200))
            pending = len(CI.pending_links(s, limit=5000))
    except _BadArg as e:
        return _bad_arg(str(e))
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': str(e)[:200], 'error_en': str(e)[:200]}), 503
    return jsonify({'runs': runs, 'pending_links': pending, 'policy': CI.policy()})


# ── EXPANSION_5K E2.7: paquetes del REPOSITORIO para el panel 🩺 → 📥 Importar (engine/importer.js) ───────────────
# `data/import/lotes/<AAAA-MM-DD>/bundle_*.json.gz` (los arma scripts/import_companies.py, p. ej. --lote2). El cliente
# NUNCA manda una ruta: elige un NOMBRE ('<fecha>/<archivo>') de la LISTA BLANCA que arma el servidor con un patrón fijo
# (sin enlaces simbólicos); cualquier otro texto → 404 package_not_found. Ver la lista y el plan de un paquete NO pide
# PIN (lectura pura, como GET /reconcile/plan; el plan se cachea por generación del grafo); aplicar sigue en POST
# /import/apply con {package} + PIN + confirm_db + expect.plan_sha (la misma decisión ontology.bulk_import) y deshacer
# en POST /import/rollback por run_id. La huella del archivo (`sha256`) = la del contenido DESCOMPRIMIDO: la misma que
# deja `import_companies.py --apply --server` al subir el .gz, así una corrida se reconoce venga de donde venga.
import gzip as _gzip  # noqa: E402
import os as _os  # noqa: E402
import re as _re  # noqa: E402

_REPO_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_PKG_ROOT = _os.path.join(_REPO_ROOT, 'data', 'import', 'lotes')
_PKG_DIR_RX = _re.compile(r'^\d{4}-\d{2}-\d{2}$')
_PKG_FILE_RX = _re.compile(r'^bundle_[A-Za-z0-9][A-Za-z0-9_\-]{0,80}\.json\.gz$')
_PKG_CACHE = {}                          # nombre → {'stat', 'sha', 'meta'}  (SOLO lo que muestra la lista: sin fichas)
_PKG_BUNDLE = {}                         # LRU de 1: {'name', 'stat', 'bundle'}; se suelta tras armar el plan (_pkg_release)
_PKG_LOCK = _threading.Lock()
_PKG_MAX_BYTES = _IMPORT_UPLOAD_MAX_BYTES     # mismo tope que una subida (sin comprimir)
_PKG_ORIGIN_KEYS = ('received', 'package', 'package_records', 'kept_records', 'excel', 'excel_rows', 'note_es', 'note_en')


def _import_packages():
    """{nombre: ruta} — la LISTA BLANCA: carpetas con fecha y archivos bundle_*.json.gz, sin enlaces simbólicos."""
    out = {}
    try:
        dirs = sorted(_os.listdir(_PKG_ROOT))
    except OSError:
        return out
    for d in dirs:
        full = _os.path.join(_PKG_ROOT, d)
        if not _PKG_DIR_RX.match(d) or _os.path.islink(full) or not _os.path.isdir(full):
            continue
        for f in sorted(_os.listdir(full)):
            path = _os.path.join(full, f)
            if _PKG_FILE_RX.match(f) and not _os.path.islink(path) and _os.path.isfile(path):
                out[f'{d}/{f}'] = path
    return out


def _pkg_side_json(folder, fname):
    """ORIGEN.json / sanitize_log.json de la MISMA carpeta (nombres fijos, nunca del cliente); None si falta o no es JSON."""
    import json as _json
    path = _os.path.join(folder, fname)
    if _os.path.islink(path) or not _os.path.isfile(path):
        return None
    try:
        with open(path, encoding='utf-8') as fh:
            data = _json.load(fh)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _num_es(n):
    return f'{int(n):,}'.replace(',', '.')


def _import_package_meta(name, path, bundle, sha, size):
    """Lo que el panel muestra del paquete (sin fichas): título ES/EN, conteos, origen y resumen del saneador."""
    folder, fname = _os.path.dirname(path), _os.path.basename(path)
    day = name.split('/', 1)[0]
    stem = fname[len('bundle_'):-len('.json.gz')]
    m = _re.search(r'lote[_\-]?(\d+)', stem, _re.I)
    n = len(bundle['records'])
    complete = 'complet' in stem.lower()
    label_es = f'Lote {m.group(1)}' if m else f'Lote del {day}'
    label_en = f'Batch {m.group(1)}' if m else f'Batch of {day}'
    origin = _pkg_side_json(folder, 'ORIGEN.json') or {}
    slog = _pkg_side_json(folder, 'sanitize_log.json') or {}
    summ = slog.get('summary') if isinstance(slog.get('summary'), dict) else None
    plan_doc = f'docs/expansion/LOTE_{day}_PLAN.md'
    return {
        'name': name, 'date': day, 'file': fname, 'batch': bundle.get('batch'),
        'title_es': f'{label_es} — {_num_es(n)} empresas' + (' completas' if complete else ''),
        'title_en': f'{label_en} — {n:,} ' + ('complete companies' if complete else 'companies'),
        'n_records': n, 'n_updates': len(bundle['updates']),
        'n_approve_categories': len(bundle.get('approve_categories') or []),
        'n_relations': sum(len(r.get('relations') or []) for r in bundle['records'] if isinstance(r, dict)),
        'size_bytes': size, 'gz_bytes': _os.path.getsize(path), 'sha256': sha,
        'origin': {k: origin[k] for k in _PKG_ORIGIN_KEYS if k in origin} | (
            {'excluded': len(origin['excluded'])} if isinstance(origin.get('excluded'), list) else {}),
        'sanitize': ({'records_in': slog.get('records_in'), 'records_changed': summ.get('records_changed'),
                      'fields_repaired': summ.get('fields_repaired'), 'fields_dropped': summ.get('fields_dropped'),
                      'rejected': len(summ.get('rejected') or []), 'by_rule': dict(summ.get('by_rule') or {})}
                     if summ else None),
        'plan_doc': plan_doc if _os.path.isfile(_os.path.join(_REPO_ROOT, plan_doc)) else None,
    }


def _pkg_release():
    """Suelta el paquete parseado (8 MB de fichas ≈ 21 MB en memoria): la lista solo guarda su meta; volver a leerlo
    cuesta ~0,2 s. Revisión del lote L: la caché retenía TODO paquete abierto mientras viviera el proceso."""
    with _PKG_LOCK:
        _PKG_BUNDLE.clear()


def _import_package(name, with_bundle=True):
    """(paquete, sha256, meta) del paquete `name` de la lista blanca o ImportProblem 404. La meta se cachea por
    mtime+tamaño; el paquete parseado solo en un LRU de 1 (`with_bundle=False` → (None, sha, meta) sin retenerlo)."""
    CI = _import_mod()
    path = _import_packages().get(name) if isinstance(name, str) else None
    if path is None:
        raise CI.ImportProblem('no existe ese paquete (mira la lista de GET /api/ontology/import/packages)',
                               'no such package (see the list from GET /api/ontology/import/packages)', 'package_not_found')
    st = _os.stat(path)
    key = (st.st_mtime_ns, st.st_size)
    with _PKG_LOCK:
        hit = _PKG_CACHE.get(name)
        if hit is not None and hit['stat'] == key:
            if not with_bundle:
                return None, hit['sha'], hit['meta']
            if _PKG_BUNDLE.get('name') == name and _PKG_BUNDLE.get('stat') == key:
                return _PKG_BUNDLE['bundle'], hit['sha'], hit['meta']
    try:
        with _gzip.open(path, 'rb') as fh:
            raw = fh.read(_PKG_MAX_BYTES + 1)
    except (OSError, EOFError) as e:
        raise CI.ImportProblem(f'paquete ilegible: {e}', f'unreadable package: {e}', 'bad_file') from e
    if len(raw) > _PKG_MAX_BYTES:
        raise CI.ImportProblem('paquete demasiado grande', 'package too large', 'package_too_big')
    sha = _hashlib.sha256(raw).hexdigest()
    try:
        bundle = CI.parse_bundle(raw.decode('utf-8'), name=_os.path.basename(path)[:-3])
    except (ValueError, UnicodeDecodeError) as e:
        raise CI.ImportProblem(f'paquete ilegible: {str(e)[:160]}', f'unreadable package: {str(e)[:160]}', 'bad_file') from e
    size = len(raw)
    del raw
    meta = _import_package_meta(name, path, bundle, sha, size)
    with _PKG_LOCK:
        _PKG_CACHE[name] = {'stat': key, 'sha': sha, 'meta': meta}
        if with_bundle:
            _PKG_BUNDLE.clear()
            _PKG_BUNDLE.update(name=name, stat=key, bundle=bundle)
    return (bundle if with_bundle else None), sha, meta


_PANEL_REVIEW_KINDS = ('possible_duplicate', 'hint_mismatch', 'hint_contradicted', 'name_target_is_counterparty',
                       'name_differs_from_hint')


def _import_panel_summary(p):
    """El plan en CORTO para el panel (sin fichas ni vínculos uno a uno): conteos, ¿qué cambia? (ρ, TSMC, top-20 que
    entra/sale), fusiones, lo que conviene revisar, avisos, inválidas y categorías por aprobar. Los textos son
    CÓDIGOS: el panel los traduce (ES/EN) y pinta los nombres de empresa como texto, nunca como HTML."""
    from collections import Counter
    wc = p.get('what_changes') or {}
    if wc.get('available'):
        b, a = wc.get('before') or {}, wc.get('after') or {}
        tb = [x['id'] for x in b.get('chokepoints') or []]
        ta = [x['id'] for x in a.get('chokepoints') or []]
        keys = ('nodes', 'links', 'rho', 'damping_rho', 'tsmc_hit')
        what = {'available': True, 'identical': bool(wc.get('identical')), 'before': {k: b.get(k) for k in keys},
                'after': {k: a.get(k) for k in keys}, 'top_in': [x for x in ta if x not in tb],
                'top_out': [x for x in tb if x not in ta], 'top_after': ta, 'added_nodes': wc.get('added_nodes'),
                'added_links': wc.get('added_links'), 'calibration_stale': bool(wc.get('calibration_stale')),
                'note_es': wc.get('note_es'), 'note_en': wc.get('note_en')}
    else:
        what = {'available': False, 'reason': str(wc.get('reason') or wc.get('error') or 'unavailable')[:200]}
    items = p.get('items') or []
    links_by_type, reasons = {}, Counter()
    for it in items:
        for lk in it.get('links') or []:
            t = links_by_type.setdefault(lk.get('rel_type') or '?', {})
            t[lk.get('route')] = t.get(lk.get('route'), 0) + 1
            if lk.get('route') != 'live':
                reasons[lk.get('reason') or '?'] += 1
    review = []
    for it in items:
        for cf in it.get('conflicts') or []:
            if cf.get('kind') in _PANEL_REVIEW_KINDS and len(review) < 40:
                review.append({'record_id': it.get('record_id'), 'name': it.get('name'), 'action': it.get('action'),
                               'id': it.get('id'), 'kind': cf.get('kind'), 'other': cf.get('id') or cf.get('hint'),
                               'score': cf.get('score')})
    return {
        'plan_sha': p['plan_sha'], 'batch': p.get('batch'), 'generation': p.get('generation'),
        'graph_version': p.get('graph_version'), 'graph_source': p.get('graph_source'), 'built_at': p.get('built_at'),
        'build_ms': p.get('build_ms'), 'counts': p['counts'], 'what_changes': what,
        'merges': [{'record_id': it.get('record_id'), 'name': it.get('name'), 'id': it.get('id'),
                    'method': it.get('method'), 'score': it.get('score')} for it in items if it.get('action') == 'merge'][:60],
        'conflicts': dict(Counter(cf.get('kind') for it in items for cf in it.get('conflicts') or [])),
        'review': review,
        'warnings': dict(Counter(w.get('code') for it in items for w in it.get('warnings') or [])),
        'links_by_type': links_by_type, 'not_live_reasons': dict(reasons),
        'invalid': [{'record_id': inv.get('record_id'), 'msg_es': ((inv.get('errors') or [{}])[0]).get('msg_es'),
                     'msg_en': ((inv.get('errors') or [{}])[0]).get('msg_en')} for inv in (p.get('invalid') or [])[:20]],
        'categories_to_approve': [{k: c.get(k) for k in ('id', 'label_es', 'label_en', 'sector', 'n')}
                                  for c in (p.get('categories') or {}).get('to_approve') or []][:40],
        'sanitize': p.get('sanitize'),
    }


def _import_runs_by_file():
    """{file_sha: [corridas]} de import_runs (para marcar «ya aplicado»); {} si la tabla no está."""
    CI = _import_mod()
    try:
        with session_scope() as s:
            runs = CI.list_runs(s, limit=200)
    except Exception:  # noqa: BLE001 — sin tablas del importador la lista sale igual
        return {}
    undone = {r['rolled_back_run'] for r in runs if r['kind'] == 'rollback' and r.get('rolled_back_run')}
    out = {}
    for r in runs:
        if r['kind'] == 'apply' and r.get('file_sha'):
            out.setdefault(r['file_sha'], []).append({
                'run_id': r['run_id'], 'created_at': r.get('created_at'), 'decision_id': r.get('decision_id'),
                'undone': r['id'] in undone, 'created': (r.get('summary') or {}).get('objects_created')})
    return out


@ontology_bp.route('/import/packages')
@_require_db
@rate_limit(60, 600)
def import_packages():
    """Paquetes del repositorio listos para importar (lectura, sin PIN): nombre, fecha, título ES/EN, conteos, origen,
    resumen del saneador y si ya se aplicó (corridas con el mismo sha256)."""
    out, errors = [], []
    runs = _import_runs_by_file()
    for name in _import_packages():
        try:
            _b, sha, meta = _import_package(name, with_bundle=False)     # solo la meta: no retiene las fichas
        except Exception as e:  # noqa: BLE001 — un paquete roto no esconde a los demás
            errors.append({'name': name, 'error': str(e)[:200], 'error_en': getattr(e, 'en', str(e))[:200]})
            continue
        mine = runs.get(sha) or []
        out.append({**meta, 'runs': mine, 'applied': any(not r['undone'] for r in mine)})
    out.sort(key=lambda m: (m['date'], m['name']), reverse=True)
    return jsonify({'packages': out, 'errors': errors})


@ontology_bp.route('/import/packages/plan')
@_require_db
@rate_limit(20, 600)
def import_package_plan():
    """Plan PURO de un paquete del repositorio, SIN PIN (no escribe nada): ?package=<nombre de la lista>. El mismo
    cálculo y la misma huella (`plan_sha`) que POST /import/plan; el resumen corto del panel (_import_panel_summary).
    Sin `fresh` (se cachea por generación del grafo: nadie sin PIN puede forzar recálculos)."""
    name = (request.args.get('package') or '').strip()[:160]
    try:
        bundle, sha, meta = _import_package(name)
        p, _view = _import_plan_for(dict(bundle), sha)
    except Exception as e:  # noqa: BLE001
        return _import_error(e)
    finally:
        _pkg_release()
    return jsonify({'status': 'ok', 'package': meta, 'file_sha': sha, 'plan': _import_panel_summary(p)})
