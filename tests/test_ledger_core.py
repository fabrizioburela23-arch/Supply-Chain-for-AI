"""tests/test_ledger_core.py — INFRA_OPERATIVA paso 6: el libro de decisiones (core/decisions).

Garantiza (docs/INFRA_OPERATIVA.md §2 y §9):
  · forma canónica estable (10.000 casos aleatorios: el orden de las claves no cambia los bytes; ida y vuelta
    idéntica; NaN rechazado);
  · vocabulario CERRADO de kinds y durabilidad por prefijo;
  · TODA Acción ejecutada deja exactamente UNA decisión sync con principal tipado, release, graph_version,
    manifiesto con su hash, la entrada exacta en un blob y los eventos escritos como efectos;
    ActionExecuted.payload.decision_id apunta a ella; RegistrarDecision es solo el ANCLA (properties.decision_id);
  · ATOMICIDAD: si la ficha no se puede escribir, la Acción se revierte (no hay efecto sin ficha);
  · record_rejection sobrevive al rollback del caller (sesión autónoma) y nunca se cuelga esperando a la
    transacción del mismo hilo;
  · append-only en la base (decisiones, referencias, resultados, sellos, linaje) y blobs con purga válida solamente;
  · approve / outcome / link / supersede: solo INSERT; aprobar exige persona con PIN distinta del solicitante;
  · /api/ledger/*: resumen redactado sin PIN, cuerpos con PIN, verify solo con PIN.
"""
import json
import os
import random
import sys
import time
import uuid
import zlib

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
PIN = 'pin-libro-7781'


# ── sin base ─────────────────────────────────────────────────────────────────
def _rand_value(rng, depth=0):
    r = rng.random()
    if depth > 3 or r < 0.35:
        return rng.choice([rng.randint(-10 ** 12, 10 ** 12), rng.random() * 1e6 - 5e5, True, False, None,
                           ''.join(rng.choice('abcñé€😀 "\\/\n\t') for _ in range(rng.randint(0, 12)))])
    if r < 0.65:
        return [_rand_value(rng, depth + 1) for _ in range(rng.randint(0, 5))]
    return {''.join(rng.choice('abcxyzÑ_é') for _ in range(rng.randint(1, 6))): _rand_value(rng, depth + 1)
            for _ in range(rng.randint(0, 5))}


def _shuffled(obj, rng):
    if isinstance(obj, dict):
        items = list(obj.items())
        rng.shuffle(items)
        return {k: _shuffled(v, rng) for k, v in items}
    if isinstance(obj, list):
        return [_shuffled(v, rng) for v in obj]
    return obj


def test_forma_canonica_estable_10000_casos():
    from core.decisions import canonical
    rng = random.Random(20261013)
    for _ in range(10000):
        obj = _rand_value(rng)
        b = canonical(obj)
        assert canonical(_shuffled(obj, rng)) == b
        assert canonical(json.loads(b.decode('utf-8'))) == b
    with pytest.raises(ValueError):
        canonical({'x': float('nan')})
    assert canonical({'b': 1, 'a': [1.5, 'ñ']}) == '{"a":[1.5,"ñ"],"b":1}'.encode('utf-8')


def test_vocabulario_cerrado_y_durabilidad():
    from core import decisions, identity
    with pytest.raises(ValueError):
        decisions.DecisionCtx('ontology.inventado', identity.system('t'))
    assert decisions.default_durability('ontology.action') == 'sync'
    assert decisions.default_durability('order.preview') == 'sync'
    assert decisions.default_durability('approval.grant') == 'sync'
    assert decisions.default_durability('chat.answer') == 'async'
    assert decisions.default_durability('whatif.shock') == 'async'


def test_ninguna_escritura_de_libro_hace_update_o_delete():
    """Prueba estática: core/decisions y core/ledger solo hacen INSERT/SELECT sobre el libro."""
    import re
    for rel in ('core/decisions.py', 'core/ledger.py'):
        src = open(os.path.join(ROOT, rel), encoding='utf-8').read()
        assert not re.search(r'\b(UPDATE|DELETE FROM|TRUNCATE)\b\s+(decisions|decision_|ledger_|events)', src), rel
        assert not re.search(r'\.(update|delete)\(\)\s*\.where', src), rel        # Core update()/delete()


# ── con base ─────────────────────────────────────────────────────────────────
@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    with session_scope() as s:
        for oid in ('LC_A', 'LC_B'):
            apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company'}, valid_from='2000-01-01',
                        source='test', actor='pytest', object_id=oid)
        apply_event(s, 'ObjectCreated', {'label': 'Factor LC', 'type': 'Factor',
                                         'properties': {'severity': 1.0, 'severity_crisis': 4.0}},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id='LC_FX')
    yield engine
    Base.metadata.drop_all(engine)


def _decisions(s, **kw):
    from core import decisions
    return decisions.list_decisions(s, redact=False, limit=500, **kw)


@needs_db
def test_accion_deja_exactamente_una_decision_sync_completa(db):
    from sqlalchemy import select, text

    from core import decisions, identity
    from core.decisions import canonical, sha256_hex
    from ontology.actions import execute_action
    from ontology.db import session_scope
    from ontology.models import Event
    p = identity.operator('ui', 'Fabrizio')
    meta = {}
    with session_scope() as s:
        before = s.execute(text('SELECT count(*) FROM decisions')).scalar()
        res = execute_action(s, 'AnotarObjeto', {'object_id': 'LC_A', 'texto': 'nota auditada'}, p.id,
                             principal=p, meta=meta)
    with session_scope() as s:
        assert s.execute(text('SELECT count(*) FROM decisions')).scalar() == before + 1
        d = decisions.get(s, meta['decision_id'], redact=False, with_blobs=True)
        evs = s.scalars(select(Event).where(Event.payload['decision_id'].astext == meta['decision_id'])).all()
        written = {str(e.id) for e in s.scalars(select(Event).where(
            (Event.object_id == res['annotation_id']) | (Event.target_id == res['annotation_id'])))}
    assert d['kind'] == 'ontology.action' and d['durability'] == 'sync' and d['status'] == 'executed'
    assert d['principal_id'] == 'op:fabrizio' and d['principal_kind'] == 'human' and d['auth'] == 'pin'
    assert len(d['release_hash']) == 64 and d['code_sha'] and d['lineage_id']
    assert d['graph_version'] is not None and d['manifest']['schema'] == 'manifest/1'
    assert d['manifest_sha'] == sha256_hex(d['manifest'])
    assert d['subject'] == {'action': 'AnotarObjeto', 'entity_ids': ['LC_A']}
    assert d['output'] == res and d['output_sha'] == sha256_hex(canonical(res))
    body = d['blobs'][d['inputs_sha']]['body']
    assert body == {'action': 'AnotarObjeto', 'payload': {'object_id': 'LC_A', 'texto': 'nota auditada'}}
    assert len(evs) == 1 and evs[0].event_type == 'ActionExecuted'
    effects = {r['ref_id'] for r in d['refs'] if r['role'] == 'effect' and r['ref_kind'] == 'event'}
    assert written <= effects and str(evs[0].id) in effects
    assert d['seal'] is None                   # el sellado es asíncrono (core/ledger)


@needs_db
def test_atomicidad_sin_ficha_no_hay_efecto(db, monkeypatch):
    from sqlalchemy import text

    from core import decisions, identity
    from ontology.actions import execute_action
    from ontology.db import session_scope

    def boom(*a, **k):
        raise RuntimeError('libro caído (simulado)')
    monkeypatch.setattr(decisions, '_insert', boom)
    with session_scope() as s:
        n_ann = s.execute(text("SELECT count(*) FROM objects WHERE type = 'Annotation'")).scalar()
        n_ev = s.execute(text('SELECT count(*) FROM events')).scalar()
    with pytest.raises(decisions.LedgerUnavailable):
        with session_scope() as s:
            execute_action(s, 'AnotarObjeto', {'object_id': 'LC_A', 'texto': 'no debe quedar'}, 'x',
                           principal=identity.operator())
    monkeypatch.undo()
    with session_scope() as s:
        assert s.execute(text("SELECT count(*) FROM objects WHERE type = 'Annotation'")).scalar() == n_ann
        assert s.execute(text('SELECT count(*) FROM events')).scalar() == n_ev


@needs_db
def test_rechazo_sobrevive_al_rollback_del_caller(db):
    from core import identity
    from ontology.actions import ActionError, execute_action
    from ontology.db import session_scope
    meta = {}
    with pytest.raises(ActionError):
        with session_scope() as s:
            execute_action(s, 'AnotarObjeto', {'object_id': 'NO_EXISTE_LC', 'texto': 'x'}, 'op:fabrizio',
                           principal=identity.operator(), meta=meta)
    with session_scope() as s:
        rows = [d for d in _decisions(s) if d['id'] == meta['decision_id']]
    assert len(rows) == 1 and rows[0]['status'] == 'rejected'
    assert rows[0]['output']['error']['type'] == 'ActionError'
    assert 'NO_EXISTE_LC' in rows[0]['output']['error']['message']
    # Acción desconocida y entrada inválida también quedan, sin copiar los valores de entrada al error
    meta2 = {}
    with pytest.raises(ActionError):
        with session_scope() as s:
            execute_action(s, 'MarcarRiesgo', {'company_id': 'LC_A', 'nivel': 'altísimo-SECRETO', 'razon': 'r'},
                           'x', principal=identity.operator(), meta=meta2)
    with session_scope() as s:
        r2 = [d for d in _decisions(s) if d['id'] == meta2['decision_id']][0]
    assert r2['status'] == 'rejected' and r2['output']['error']['code'] == 'invalid_input'
    assert 'SECRETO' not in json.dumps(r2['output'])


@needs_db
def test_rechazo_dentro_de_una_transaccion_con_el_mismo_blob_no_se_cuelga(db):
    """El blob de entrada ya lo insertó (sin confirmar) la misma transacción: la sesión autónoma no debe esperar
    a esa transacción (que no avanza mientras esperamos) → lock_timeout corto y la ficha queda sin el blob."""
    from core import identity
    from ontology.actions import ActionError, execute_action
    from ontology.db import session_scope
    payload = {'factor_id': 'LC_FX', 'razon': 'crisis'}
    meta = {}
    t0 = time.time()
    with session_scope() as s:
        execute_action(s, 'ActivarFactor', dict(payload), 'op:fabrizio', principal=identity.operator())
        with pytest.raises(ActionError):       # mismo payload → mismo blob; ya activo → rechazo
            execute_action(s, 'ActivarFactor', dict(payload), 'op:fabrizio', principal=identity.operator(),
                           meta=meta)
    assert time.time() - t0 < 10
    with session_scope() as s:
        r = [d for d in _decisions(s) if d['id'] == meta['decision_id']][0]
    assert r['status'] == 'rejected' and r['manifest'].get('inputs_blob_unavailable') is True
    assert r['inputs_sha'] is None


@needs_db
def test_registrar_decision_es_ancla_del_libro(db):
    from core import decisions, identity
    from ontology.actions import execute_action
    from ontology.db import session_scope
    from ontology.models import ObjectRecord
    with session_scope() as s:
        res = execute_action(s, 'RegistrarDecision', {'decision': 'comprar menos', 'company_id': 'LC_A'},
                             'op:fabrizio', principal=identity.operator())
    with session_scope() as s:
        anchor = s.get(ObjectRecord, res['decision_id'])
        d = decisions.get(s, res['ledger_decision_id'], redact=False)
    assert anchor.type == 'Decision' and anchor.properties['decision_id'] == res['ledger_decision_id']
    assert d['subject']['action'] == 'RegistrarDecision'


@needs_db
@pytest.mark.parametrize('sql', [
    "UPDATE decisions SET status = 'approved'",
    'DELETE FROM decisions',
    'TRUNCATE decisions CASCADE',
    "UPDATE decision_refs SET note = '{}'::jsonb",
    'DELETE FROM decision_refs',
    'DELETE FROM ledger_meta',
    'DELETE FROM decision_blobs',
    "UPDATE decision_blobs SET body = NULL",
    'TRUNCATE decision_blobs CASCADE',
])
def test_libro_append_only_en_la_base(db, sql):
    from sqlalchemy import text
    from core import identity
    from ontology.actions import execute_action
    from ontology.db import session_scope
    with session_scope() as s:
        execute_action(s, 'AnotarObjeto', {'object_id': 'LC_B', 'texto': 'para el disparador'}, 'x',
                       principal=identity.operator())
    with pytest.raises(Exception) as ei:
        with db.begin() as c:
            c.execute(text(sql))
    assert 'append-only' in str(ei.value)


@needs_db
def test_purga_de_blob_solo_si_es_valida(db):
    from sqlalchemy import text
    old = 'f' * 64
    cited = 'e' * 64
    with db.begin() as c:
        c.execute(text("INSERT INTO decision_blobs (sha256, kind, body, size_bytes, retention_class, created_at) "
                       "VALUES (:a, 'payload', :b, 3, 'standard_90d', now() - interval '120 days'), "
                       "(:c, 'payload', :b, 3, 'legal', now() - interval '120 days')"),
                  {'a': old, 'b': zlib.compress(b'{}'), 'c': cited})
    def purge(sha, job=True, with_decision=True, real_decision=True):
        # paso 26: la forma EXACTA de la purga lleva purged_at Y purge_decision_id (la decisión retention.purge);
        # revisión batch G: esa decisión debe existir y escribirse en la MISMA transacción (disparador diferido)
        from core import decisions, identity
        from ontology.db import session_scope
        with session_scope() as s:
            with decisions.decision_scope('retention.purge', identity.system('pytest_purge'), session=s) as ctx:
                if job:
                    s.execute(text("SELECT set_config('khipus.retention_job', 'on', true)"))
                s.execute(text('UPDATE decision_blobs SET body = NULL, purged_at = now(), purge_decision_id = '
                               + ("CAST(:d AS uuid)" if with_decision else 'NULL') + ' WHERE sha256 = :s'),
                          {'s': sha, 'd': str(ctx.id) if real_decision else str(uuid.uuid4())})
                ctx.output = {'purged': 1}
    with pytest.raises(Exception):
        purge(old, job=False)                  # sin el job de retención: no
    with pytest.raises(Exception):
        purge(old, with_decision=False)        # sin la decisión de la purga: no
    with pytest.raises(Exception):
        purge(cited)                           # 'legal': nunca
    with pytest.raises(Exception):
        purge(old, real_decision=False)        # un UUID cualquiera, sin su decisión retention.purge: no
    purge(old)                                 # standard_90d, viejo, sin decisión sync que lo cite: sí
    with db.connect() as c:
        assert c.execute(text('SELECT body IS NULL FROM decision_blobs WHERE sha256 = :s'), {'s': old}).scalar()


@needs_db
def test_aprobar_resultados_enlaces_y_correccion_solo_insertan(db):
    from datetime import datetime, timezone

    from sqlalchemy import text

    from core import decisions, identity
    from ontology.db import session_scope
    agent = identity.system('auto_apply')
    with session_scope() as s:
        with decisions.decision_scope('proposal.create', agent, session=s, subject={'entity_ids': ['LC_A']}) as ctx:
            ctx.output = {'proposal': 'x'}
            ctx.status = 'pending_approval'
        target = ctx.id
    with session_scope() as s:
        with pytest.raises(PermissionError):           # un agente no aprueba
            decisions.approve(s, target, identity.system('otro'))
    with session_scope() as s:
        gid = decisions.approve(s, target, identity.operator('ui', 'Fabrizio'), note='ok, se aplica')
    with session_scope() as s:
        g = decisions.get(s, gid, redact=False)
        assert g['kind'] == 'approval.grant' and g['parent_id'] == str(target) and g['status'] == 'approved'
        t = decisions.get(s, target, redact=False)
        assert str(gid) in t['children']
        # resultado con dedup_key: no se repite
        now = datetime.now(timezone.utc)
        a = decisions.outcome(s, target, 'user_feedback', {'dedup_key': 'k1', 'v': 1}, observed_at=now, source='user')
        b = decisions.outcome(s, target, 'user_feedback', {'dedup_key': 'k1', 'v': 2}, observed_at=now, source='user')
        assert a is not None and b is None
        decisions.link(s, target, 'evidence', 'source', 'src_1')
        decisions.link(s, target, 'evidence', 'source', 'src_1')        # repetir = no-op
        sid = decisions.supersede(s, target, identity.operator(), 'corrección de prueba')
    with session_scope() as s:
        t = decisions.get(s, target, redact=False)
        assert [r for r in t['refs'] if r['ref_id'] == 'src_1'] and len(t['outcomes']) == 1
        assert str(sid) in t['children']
        assert decisions.get(s, sid, redact=False)['supersedes_id'] == str(target)
        # el original NO cambió
        assert t['status'] == 'pending_approval'
        n = s.execute(text('SELECT count(*) FROM decisions WHERE id = :i'), {'i': target}).scalar()
        assert n == 1


@needs_db
def test_auto_aplicar_queda_a_nombre_de_system(db):
    from sqlalchemy import select

    from core import decisions
    from ontology.agents import auto_cycle
    from ontology.db import session_scope
    from ontology.models import ProposedAction
    with session_scope() as s:
        s.add(ProposedAction(agent='centinela_nrs', action_type='AnotarObjeto',
                             payload={'object_id': 'LC_A', 'texto': 'auto'}, object_id='LC_A', confidence=0.9,
                             explanation='prueba', status='pending'))
    import ontology.agents as A
    orig = A.run_agents
    A.run_agents = lambda session, **k: {}
    try:
        with session_scope() as s:
            out = auto_cycle(s)
    finally:
        A.run_agents = orig
    assert out['auto_applied'], out
    with session_scope() as s:
        p = s.scalars(select(ProposedAction).where(ProposedAction.agent == 'centinela_nrs')).first()
        rows = [d for d in decisions.list_decisions(s, redact=False, principal='system:auto_apply')
                if d['correlation_id'] == f'proposal:{p.id}']
    # paso 19: la Acción (ontology.action) es HIJA de proposal.auto_apply; las dos a nombre de system:auto_apply
    acts = [d for d in rows if d['kind'] == 'ontology.action']
    auto = [d for d in rows if d['kind'] == 'proposal.auto_apply']
    assert len(acts) == 1 and acts[0]['declared_name'] == 'centinela_nrs' and acts[0]['status'] == 'executed'
    assert len(auto) == 1 and auto[0]['status'] == 'executed' and acts[0]['parent_id'] == auto[0]['id']


# ── API ──────────────────────────────────────────────────────────────────────
def _client():
    from flask import Flask

    from core.ledger_api import ledger_bp
    from ontology.api import ontology_bp
    app = Flask('ledger_core')
    app.config['TESTING'] = True
    app.register_blueprint(ontology_bp)
    app.register_blueprint(ledger_bp)
    return app.test_client()


@pytest.fixture
def clean(monkeypatch):
    from core import http as h
    from core import pin
    for v in ('RAILWAY_ENVIRONMENT', 'RAILWAY_ENVIRONMENT_NAME', 'RAILWAY_PROJECT_ID'):
        monkeypatch.delenv(v, raising=False)
    pin._reset_for_tests()
    with h._rate_lock:
        h._rate_buckets.clear()
    yield
    pin._reset_for_tests()


@needs_db
def test_api_del_libro_redacta_sin_pin(db, monkeypatch, clean):
    monkeypatch.setenv('TRADE_PIN', PIN)
    c = _client()
    r = c.post('/api/ontology/actions/AnotarObjeto', headers={'X-Trade-Pin': PIN},
               json={'actor': 'Etiqueta Libre', 'object_id': 'LC_A', 'texto': 'texto de la nota'})
    did = r.get_json()['decision_id']
    red = c.get(f'/api/ledger/decision/{did}').get_json()
    assert red['redacted'] is True and red['kind'] == 'ontology.action'
    blob = json.dumps(red)
    assert 'Etiqueta Libre' not in blob and 'texto de la nota' not in blob and 'manifest' not in red
    lst = c.get('/api/ledger/decisions?kind=ontology.action').get_json()
    assert lst['redacted'] and all('subject' not in d for d in lst['decisions'])
    full = c.get(f'/api/ledger/decision/{did}?blobs=1', headers={'X-Trade-Pin': PIN}).get_json()
    assert full['declared_name'] == 'Etiqueta Libre' and full['explain']['es'] and full['explain']['en']
    assert full['blobs'][full['inputs_sha']]['body']['payload']['texto'] == 'texto de la nota'
    assert c.get(f'/api/ledger/decision/{did}', headers={'X-Trade-Pin': 'malo'}).status_code == 401
    assert c.get('/api/ledger/verify').status_code == 401
    v = c.get('/api/ledger/verify', headers={'X-Trade-Pin': PIN}).get_json()
    assert v['ok'] is True
    assert c.get('/api/ledger/decision/no-es-uuid').status_code == 400
    assert c.get(f'/api/ledger/decision/{uuid.uuid4()}', headers={'X-Trade-Pin': PIN}).status_code == 404
    st = c.get('/api/ledger/status').get_json()
    assert st['available'] and st['decisions'] >= 1 and 'head' in st


def test_api_del_libro_sin_base_responde_503(monkeypatch):
    from flask import Flask

    from core import ledger_api
    monkeypatch.setattr(ledger_api, '_db', lambda: False)
    app = Flask('ledger_nodb')
    app.register_blueprint(ledger_api.ledger_bp)
    c = app.test_client()
    for path in ('/api/ledger/status', '/api/ledger/decisions', f'/api/ledger/decision/{uuid.uuid4()}',
                 '/api/ledger/verify'):
        r = c.get(path)
        assert r.status_code == 503 and r.get_json()['code'] == 'ledger_unavailable', path


@needs_db
def test_api_sin_libro_responde_503_y_no_aplica_la_accion(db, monkeypatch, clean):
    from sqlalchemy import text

    from core import decisions
    monkeypatch.delenv('TRADE_PIN', raising=False)

    def boom(*a, **k):
        raise RuntimeError('libro caído (simulado)')
    with db.connect() as c:
        n_ev = c.execute(text('SELECT count(*) FROM events')).scalar()
    monkeypatch.setattr(decisions, '_insert', boom)
    r = _client().post('/api/ontology/actions/AnotarObjeto', json={'actor': 'x', 'object_id': 'LC_A', 'texto': 'no'})
    assert r.status_code == 503 and r.get_json()['code'] == 'ledger_unavailable' and r.get_json()['error_en']
    with db.connect() as c:
        assert c.execute(text('SELECT count(*) FROM events')).scalar() == n_ev
