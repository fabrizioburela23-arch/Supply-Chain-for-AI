"""core/governance_api.py — /api/governance/* (docs/INFRA_OPERATIVA.md §5.1; paso 9). Nunca bajo /v1/*.

  GET  /api/governance/active             público: release vigente {release_hash, semver, label, ratified, source,
                                          artifacts{id: {semver, hash, params}}} — ETag = release_hash. El cliente
                                          debe leer aquí los números (en vez de copiarlos)
  GET  /api/governance/status             público: resumen sin parámetros (+ avisos de entorno con PIN)
  POST /api/governance/ratify             SOLO operador (PIN, persona): {release_hash?, note?} → decisión
                                          governance.ratify (el bootstrap 1.0.0 queda ratificado; no bloquea nada)
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
