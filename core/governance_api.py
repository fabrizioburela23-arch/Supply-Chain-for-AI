"""core/governance_api.py — /api/governance/* (docs/INFRA_OPERATIVA.md §5.1; paso 9). Nunca bajo /v1/*.

  GET  /api/governance/active             público: release vigente {release_hash, semver, label, ratified, source,
                                          artifacts{id: {semver, hash, params}}} — ETag = release_hash. El cliente
                                          debe leer aquí los números (en vez de copiarlos)
  GET  /api/governance/status             público: resumen sin parámetros (+ avisos de entorno con PIN)
  POST /api/governance/ratify             SOLO operador (PIN, persona): {release_hash?, note?} → decisión
                                          governance.ratify (el bootstrap 1.0.0 queda ratificado; no bloquea nada)
  GET  /api/governance/preview?artifact=kernel.params&semver=2.0.0
                                          público: "¿qué cambia para mí?" — contrafactual SIN tocar el kernel vivo
                                          (core/governance_preview.py; ~0,3-1 s la primera vez, luego caché)
  POST /api/governance/activate           SOLO operador (PIN, persona): {artifact, semver, note?} → fila nueva en
                                          gov_releases + decisión governance.activate; deshacer = activar la anterior
                                          Paso 25: {release_hash} (= «Deshacer»: volver a un release entero),
                                          effective_from ('now' | 'ny_close' | ISO; por defecto ya, salvo
                                          policy.broker_risk → cierre de NY, D5) → programada; cita la última
                                          regresión (governance.validate) de esa versión
  ── paso 25 (flujo completo, core/governance_flow.py) ──
  POST /api/governance/propose            SOLO operador: {artifact, changes{ruta: número}, change_kind?, semver?,
                                          changelog_es?, changelog_en?, note?} → gov_artifacts (origin app) +
                                          decisión governance.propose; lanza la regresión en segundo plano.
                                          Lint = el de scripts/build_governance.py → 422 {problems:[{code,es,en}]}
  POST /api/governance/validate           SOLO operador: {artifact, semver, ids?} → regresión en segundo plano (202)
  GET  /api/governance/validation?artifact=&semver=   público: estado/resultado de la última regresión
  POST /api/governance/cancel             SOLO operador: {decision_id} → cancela una activación PROGRAMADA
  GET  /api/governance/history            público: releases, decisiones governance.*, programadas, propuestas de la
                                          app, «Deshacer» disponible y el formulario de afinables
  GET  /api/governance/attribution?decision_id=   público: qué release y qué versiones decidieron esa decisión
"""
import logging

from flask import Blueprint, jsonify, make_response, request

from core.http import rate_limit

log = logging.getLogger('khipu')

governance_bp = Blueprint('governance', __name__, url_prefix='/api/governance')


@governance_bp.route('/active')
@rate_limit(120, 60)
def gov_active():
    from core import governance
    try:
        b = governance.active()
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': 'registro de gobernanza no disponible', 'error_en': 'governance registry unavailable',
                        'detail': type(e).__name__}), 503
    etag = f'"rel-{b.release_hash[:24]}"'
    if etag in [t.strip() for t in str(request.headers.get('If-None-Match') or '').split(',')]:
        resp = make_response('', 304)
        resp.headers['ETag'] = etag
        return resp
    out = b.summary()
    out['artifacts'] = {a: {'semver': v['semver'], 'hash': v['hash'], 'params': v['params']}
                        for a, v in sorted(b.artifacts.items())}
    out['explain'] = {'es': governance.explain('es'), 'en': governance.explain('en')}
    resp = jsonify(out)
    resp.headers['ETag'] = etag
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


@governance_bp.route('/status')
@rate_limit(60, 60)
def gov_status():
    from core import governance, pin
    try:
        st = governance.status()
    except Exception as e:  # noqa: BLE001
        return jsonify({'error': 'registro de gobernanza no disponible', 'error_en': 'governance registry unavailable',
                        'detail': type(e).__name__}), 503
    full = False
    if request.headers.get('X-Trade-Pin'):
        err = pin.pin_error(where='governance', strict=True)
        if err:
            return err
        full = True
    if not full:
        st['env_warnings'] = len(st['env_warnings'])
        st.pop('db_error', None)
    st['explain'] = {'es': governance.explain('es'), 'en': governance.explain('en')}
    return jsonify(st)


@governance_bp.route('/ratify', methods=['POST'])
@rate_limit(6, 60)
def gov_ratify():
    from core import governance, identity, pin
    from ontology.db import ontology_available
    if not ontology_available():
        return jsonify({'error': 'Sin base de datos no hay release que ratificar (rige el del repositorio)',
                        'error_en': 'Without a database there is no release to ratify (the repository one rules)',
                        'code': 'ledger_unavailable'}), 503
    err = pin.pin_error(where='governance_ratify', strict=True)
    if err:
        return err
    body = request.get_json(silent=True) or {}
    try:
        from ontology.db import session_scope
        principal = identity.principal_from_request(declared=body.get('actor'))
        with session_scope() as s:
            out = governance.ratify(s, principal, release_hash=body.get('release_hash'), note=body.get('note'))
        governance.refresh()
        return jsonify({'ok': True, **out, 'status': governance.status()['label']})
    except PermissionError as e:
        return jsonify({'error': str(e), 'error_en': 'ratifying requires a person authenticated with the PIN',
                        'code': 'forbidden'}), 403
    except LookupError as e:
        return jsonify({'error': str(e), 'error_en': 'release not found', 'code': 'not_found'}), 404
    except ValueError as e:
        return jsonify({'error': str(e), 'error_en': 'that release is already ratified',
                        'code': 'already_ratified'}), 409
    except Exception as e:  # noqa: BLE001
        log.warning('governance ratify: %s', type(e).__name__)
        return jsonify({'error': 'error del registro de gobernanza', 'error_en': 'governance registry error',
                        'detail': type(e).__name__}), 500


@governance_bp.route('/preview')
@rate_limit(12, 60)
def gov_preview():
    from core import governance_preview
    aid = (request.args.get('artifact') or '').strip()[:48]
    sv = (request.args.get('semver') or '').strip()[:16]
    if not aid or not sv:
        return jsonify({'error': 'faltan artifact y semver', 'error_en': 'artifact and semver are required',
                        'code': 'bad_request'}), 400
    ids = [x for x in (request.args.get('ids') or '').split(',') if x.strip()][:25]
    try:
        out = governance_preview.preview({aid: sv}, focus=ids)
    except LookupError:
        return jsonify({'error': f'{aid}@{sv} no existe', 'error_en': f'{aid}@{sv} does not exist',
                        'code': 'not_found'}), 404
    except Exception as e:  # noqa: BLE001
        log.warning('governance preview: %s', type(e).__name__)
        return jsonify({'error': 'no se pudo calcular la vista previa', 'error_en': 'could not compute the preview',
                        'detail': type(e).__name__}), 500
    resp = jsonify(out)
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


@governance_bp.route('/activate', methods=['POST'])
@rate_limit(6, 60)
def gov_activate():
    from core import governance, identity, pin
    from ontology.db import ontology_available
    if not ontology_available():
        return jsonify({'error': 'Sin base de datos no hay release que activar (rige el del repositorio)',
                        'error_en': 'Without a database there is no release to activate (the repository one rules)',
                        'code': 'ledger_unavailable'}), 503
    err = pin.pin_error(where='governance_activate', strict=True)
    if err:
        return err
    body = request.get_json(silent=True) or {}
    if not isinstance(body, dict):
        body = {}
    sel = body.get('selection')
    rel_target = str(body.get('release_hash') or '').strip().lower()[:64]
    if not isinstance(sel, dict) or not sel:
        aid, sv = str(body.get('artifact') or '').strip()[:48], str(body.get('semver') or '').strip()[:16]
        sel = {aid: sv} if aid and sv else None
    if not sel and not rel_target:
        return jsonify({'error': 'falta {artifact, semver}', 'error_en': '{artifact, semver} is required',
                        'code': 'bad_request'}), 400
    try:
        from core import governance_flow
        from ontology.db import session_scope
        principal = identity.principal_from_request(declared=body.get('actor'))
        with session_scope() as s:
            if rel_target:      # paso 25 «Deshacer»: volver a un release ENTERO (sus versiones)
                from sqlalchemy import text
                row = s.execute(text('SELECT artifacts FROM gov_releases WHERE release_hash = :r'),
                                {'r': rel_target}).first()
                if row is None:
                    raise LookupError('release no encontrado')
                sel = {a: v['semver'] for a, v in (row.artifacts or {}).items()}
            # D5 mira solo lo que CAMBIA (un «Deshacer» trae el release entero, con policy.broker_risk igual)
            cur_arts = governance.active().artifacts
            changing = {a: v for a, v in sel.items() if (cur_arts.get(a) or {}).get('semver') != v}
            try:
                eff = governance_flow.parse_effective_from(body.get('effective_from'), changing)
            except ValueError as e:
                return jsonify({'error': f'effective_from inválido: {e}', 'error_en': 'invalid effective_from (ISO 8601 '
                                'with a time zone, at most 90 days ahead)', 'code': 'bad_request'}), 400
            vid = body.get('validation_id') or governance_flow.latest_validation_id(s, sel)
            out = governance.activate(s, principal, sel, note=body.get('note'), effective_from=eff,
                                      validation_id=vid)
        b = governance.refresh()          # pone en vigor el release nuevo: re-asigna constantes y reconstruye vistas
        st = governance.status()
        return jsonify({'ok': True, **out, 'in_force': (b.release_hash if b else None) == out['release_hash'],
                        'status': {'semver': st['semver'], 'label': st['label'], 'release_hash': st['release_hash'],
                                   'artifacts': st['artifacts']}})
    except PermissionError as e:
        return jsonify({'error': str(e), 'error_en': 'activating requires a person authenticated with the PIN',
                        'code': 'forbidden'}), 403
    except LookupError as e:
        return jsonify({'error': str(e), 'error_en': 'artifact version or release not found', 'code': 'not_found'}), 404
    except ValueError as e:
        if getattr(e, 'code', None):
            return jsonify({'error': e.es, 'error_en': e.en, 'code': e.code}), 409
        return jsonify({'error': str(e), 'error_en': 'those versions are already in force', 'code': 'no_change'}), 409
    except Exception as e:  # noqa: BLE001
        log.warning('governance activate: %s', type(e).__name__)
        return jsonify({'error': 'error del registro de gobernanza', 'error_en': 'governance registry error',
                        'detail': type(e).__name__}), 500


# ── paso 25: flujo completo (core/governance_flow.py) ─────────────────────────────────────────────────────────
def _need_db():
    from ontology.db import ontology_available
    if ontology_available():
        return None
    return jsonify({'error': 'Sin base de datos no hay registro de gobernanza (rige el del repositorio)',
                    'error_en': 'Without a database there is no governance registry (the repository one rules)',
                    'code': 'ledger_unavailable'}), 503


def _body():
    b = request.get_json(silent=True) or {}
    return b if isinstance(b, dict) else {}


def _gov_error(e, where):
    log.warning('governance %s: %s', where, type(e).__name__)
    return jsonify({'error': 'error del registro de gobernanza', 'error_en': 'governance registry error',
                    'detail': type(e).__name__}), 500


@governance_bp.route('/propose', methods=['POST'])
@rate_limit(6, 60)
def gov_propose():
    from core import governance, governance_flow, identity, pin
    err = _need_db()
    if err:
        return err
    err = pin.pin_error(where='governance_propose', strict=True)
    if err:
        return err
    body = _body()
    try:
        from ontology.db import session_scope
        principal = identity.principal_from_request(declared=body.get('actor'))
        with session_scope() as s:
            out = governance_flow.propose(
                s, principal, str(body.get('artifact') or '').strip()[:48], body.get('changes'),
                change_kind=body.get('change_kind'), semver=body.get('semver'), base_semver=body.get('base_semver'),
                changelog_es=str(body.get('changelog_es') or '')[:2000],
                changelog_en=str(body.get('changelog_en') or '')[:2000], note=body.get('note'))
        governance.refresh()                    # la propuesta aparece en «propuestas» (no entra en vigor)
        ids = [str(x)[:120] for x in (body.get('ids') or [])][:25] if isinstance(body.get('ids'), list) else None
        out['validation'] = governance_flow.validate_async(principal, out['artifact'], out['semver'], focus=ids)
        out['validation'].pop('report', None)
        return jsonify({'ok': True, **out})
    except governance_flow.ProposalRefused as e:
        return jsonify({'error': '; '.join(p['es'] for p in e.problems), 'error_en': '; '.join(p['en'] for p in e.problems),
                        'code': 'proposal_refused', 'problems': e.problems}), 422
    except PermissionError as e:
        return jsonify({'error': str(e), 'error_en': 'proposing requires a person authenticated with the PIN',
                        'code': 'forbidden'}), 403
    except Exception as e:  # noqa: BLE001
        return _gov_error(e, 'propose')


@governance_bp.route('/validate', methods=['POST'])
@rate_limit(6, 60)
def gov_validate():
    from core import governance, governance_flow, identity, pin
    err = _need_db()
    if err:
        return err
    err = pin.pin_error(where='governance_validate', strict=True)
    if err:
        return err
    body = _body()
    aid, sv = str(body.get('artifact') or '').strip()[:48], str(body.get('semver') or '').strip()[:16]
    try:
        governance.available_artifact(aid, sv)
    except LookupError:
        return jsonify({'error': f'{aid}@{sv} no existe', 'error_en': f'{aid}@{sv} does not exist',
                        'code': 'not_found'}), 404
    except Exception as e:  # noqa: BLE001
        return _gov_error(e, 'validate')
    ids = [str(x)[:120] for x in (body.get('ids') or [])][:25] if isinstance(body.get('ids'), list) else None
    principal = identity.principal_from_request(declared=body.get('actor'))
    job = governance_flow.validate_async(principal, aid, sv, focus=ids)
    job.pop('report', None)
    return jsonify({'ok': True, 'job': job}), 202


@governance_bp.route('/validation')
@rate_limit(60, 60)
def gov_validation():
    from core import governance_flow
    aid = (request.args.get('artifact') or '').strip()[:48]
    sv = (request.args.get('semver') or '').strip()[:16]
    if not aid or not sv:
        return jsonify({'error': 'faltan artifact y semver', 'error_en': 'artifact and semver are required',
                        'code': 'bad_request'}), 400
    try:
        v = governance_flow.validation(aid, sv)
    except Exception as e:  # noqa: BLE001
        return _gov_error(e, 'validation')
    resp = jsonify({'validation': v})
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


@governance_bp.route('/cancel', methods=['POST'])
@rate_limit(6, 60)
def gov_cancel():
    from core import governance, governance_flow, identity, pin
    err = _need_db()
    if err:
        return err
    err = pin.pin_error(where='governance_cancel', strict=True)
    if err:
        return err
    body = _body()
    try:
        from ontology.db import session_scope
        principal = identity.principal_from_request(declared=body.get('actor'))
        with session_scope() as s:
            out = governance_flow.cancel_scheduled(s, principal, str(body.get('decision_id') or '')[:40])
        governance.refresh()
        return jsonify({'ok': True, **out})
    except PermissionError as e:
        return jsonify({'error': str(e), 'error_en': 'cancelling requires a person authenticated with the PIN',
                        'code': 'forbidden'}), 403
    except ValueError as e:
        return jsonify({'error': getattr(e, 'es', str(e)), 'error_en': getattr(e, 'en', str(e)),
                        'code': getattr(e, 'code', 'bad_request')}), 409
    except Exception as e:  # noqa: BLE001
        return _gov_error(e, 'cancel')


@governance_bp.route('/history')
@rate_limit(30, 60)
def gov_history():
    from core import governance_flow
    err = _need_db()
    if err:
        try:          # sin base: solo el formulario (para mostrar qué se podría proponer), sin historia
            return jsonify({'releases': [], 'decisions': [], 'scheduled': [], 'app_proposals': [], 'undo': None,
                            'proposable': {a: governance_flow._proposable_fields(a)
                                           for a in governance_flow.param_artifacts()},
                            'db': False})
        except Exception as e:  # noqa: BLE001
            return _gov_error(e, 'history')
    try:
        from ontology.db import session_scope
        with session_scope() as s:
            out = governance_flow.history(s, limit=request.args.get('limit') or 30)
        out['db'] = True
        resp = jsonify(out)
        resp.headers['Cache-Control'] = 'no-cache'
        return resp
    except Exception as e:  # noqa: BLE001
        return _gov_error(e, 'history')


@governance_bp.route('/attribution')
@rate_limit(60, 60)
def gov_attribution():
    from core import governance_flow
    err = _need_db()
    if err:
        return err
    did = (request.args.get('decision_id') or '').strip()[:40]
    if not did:
        return jsonify({'error': 'falta decision_id', 'error_en': 'decision_id is required', 'code': 'bad_request'}), 400
    try:
        from ontology.db import session_scope
        with session_scope() as s:
            return jsonify(governance_flow.attribution(s, did))
    except LookupError:
        return jsonify({'error': 'decisión no encontrada', 'error_en': 'decision not found', 'code': 'not_found'}), 404
    except Exception as e:  # noqa: BLE001
        return _gov_error(e, 'attribution')
