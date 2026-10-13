"""tests/test_replay_determinism.py — INFRA_OPERATIVA paso 24 (§5.6): repetir decisiones pasadas.

Pruebas DORADAS del replay (modo audit, core/replay.py) sobre una base propia:
  · whatif.shock (/api/hot/scenario y /api/matrix/impact) y whatif.factor_fire se repiten IDÉNTICOS — la huella del
    vector completo, el top-50 y la GraphCore reconstruida = la que publicó la generación (hot_view_builds);
  · un cambio posterior del grafo NO cambia el replay (κ = la versión que se leyó);
  · una decisión tomada con kernel.params 1.0.0 se repite idéntica DESPUÉS de activar 2.0.0 (y la de 2.0.0 también);
  · un cambio de CÓDIGO que altera el resultado se detecta: 'differs' con la ruta del campo;
  · committee.run (umbrales → tamaño) con y sin cliente; order.preview / order.confirm (run_checks); las PUERTAS
    (grafo foco guardado, IR por hash) de una acción de la ontología y de una orden;
  · IA: nunca se re-ejecuta — not_replayable 'ai_text' con prompt_sha/output_sha y el guardián de cifras verificados;
    un blob PURGADO se dice (nunca se inventa);
  · API /api/ledger/replay|why|audit (sin PIN: resumen sin valores), MCP replay_decision y la muestra nocturna.
Sin red. Se salta sin DATABASE_URL.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

DATABASE_URL = os.getenv('DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
PIN = 'pin-replay-2424'
G = '2000-01-01'
_W = {}                                  # decisiones creadas en la primera prueba (el orden del módulo importa)


def _ev(s, et, payload, oid, tgt=None):
    from ontology.service import apply_event
    return apply_event(s, et, payload, valid_from=G, source='test', actor='pytest', object_id=oid, target_id=tgt)


@pytest.fixture(scope='module')
def db():
    from core import governance, replay
    from core.hotviews import hot, registry
    from core.hotviews.views import asof
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    import brokerage.models  # noqa: F401
    import research.models  # noqa: F401
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    governance._reset_for_tests()
    assert init_schema(retries=1)
    governance.refresh()
    registry.reset()
    hot.reset()
    asof.reset()
    replay._reset_for_tests()
    with session_scope() as s:                      # RA → RB (supply) → RC (fab) ⇢ RD (partner: daña solo en 1.0.0)
        for oid in ('RA', 'RB', 'RC', 'RD', 'RE'):
            _ev(s, 'ObjectCreated', {'label': oid, 'type': 'Company', 'properties': {'country': 'US'}}, oid)
        _ev(s, 'ObjectCreated', {'label': 'Crisis F', 'type': 'Factor',
                                 'properties': {'severity': 3.0, 'severity_crisis': 8.0}}, 'RF')
        _ev(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 5}, 'RA', 'RB')
        _ev(s, 'LinkCreated', {'rel_type': 'fab', 'weight': 4}, 'RB', 'RC')
        _ev(s, 'LinkCreated', {'rel_type': 'partner', 'weight': 5}, 'RC', 'RD')
        _ev(s, 'LinkCreated', {'rel_type': 'affects', 'weight': 0.7}, 'RF', 'RB')
    yield engine
    import time

    from core.hotviews import builder
    t0 = time.time()
    while builder.state().get('building') and time.time() - t0 < 10:
        time.sleep(0.02)
    governance._reset_for_tests()
    registry.reset()
    hot.reset()
    asof.reset()
    replay._reset_for_tests()
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(monkeypatch):
    import server
    from core import http as h
    from core import pin
    for v in ('RAILWAY_ENVIRONMENT', 'RAILWAY_ENVIRONMENT_NAME', 'RAILWAY_PROJECT_ID'):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv('TRADE_PIN', PIN)
    pin._reset_for_tests()
    with h._rate_lock:
        h._rate_buckets.clear()
    c = server.app.test_client()
    yield c
    pin._reset_for_tests()


def _flush():
    from core import ai_calls, decisions
    decisions.flush_async()
    ai_calls.flush()


def _last(kind):
    from sqlalchemy import text
    from ontology.db import session_scope
    with session_scope() as s:
        return str(s.execute(text('SELECT id FROM decisions WHERE kind = :k ORDER BY seq DESC LIMIT 1'),
                             {'k': kind}).scalar())


def _replay(did, **kw):
    from core import replay
    return replay.replay(did, record=False, use_cache=False, **kw)


def _ok(out):
    steps = {s['name']: s for s in out['steps']}
    assert out['verdict'] == 'identical', (out['verdict'], out['reasons'], [(s['name'], s.get('ok'), s.get('diffs'))
                                                                             for s in out['steps']])
    return steps


# ── qué-pasaría-si ───────────────────────────────────────────────────────────────────────────────────────────────
def test_whatif_shock_y_factor_se_repiten_identicos(db, client):
    r1 = client.post('/api/hot/scenario', json={'shocks': [{'id': 'RA', 'magnitude': 0.9}]})
    assert r1.status_code == 200, r1.get_json()
    _flush()
    d_scn = _last('whatif.shock')
    r2 = client.post('/api/matrix/impact', json={'shock': ['RA', 'NO_EXISTE'], 'damping': 0.55})
    assert r2.status_code == 200, r2.get_json()
    _flush()
    d_imp = _last('whatif.shock')
    r3 = client.post('/api/matrix/factor/fire', json={'factor_id': 'RF'})
    assert r3.status_code == 200, r3.get_json()
    _flush()
    d_fire = _last('whatif.factor_fire')
    for did in (d_scn, d_imp, d_fire):
        out = _replay(did)
        st = _ok(out)
        assert out['fidelity'] == 'exact' and out['reproduced'] is True
        assert st['integrity']['ok'] and st['artifacts']['ok'] and st['impl']['ok'] and st['lineage']['ok']
        assert st['views_rebuilt']['ok'] is True                 # la GraphCore reconstruida = la publicada
        assert st['deterministic_core']['impl'] == 'propagate@1' and 'content_sha' in st['deterministic_core']['compared']
        assert out['world']['release_semver']['kernel.params'] == '1.0.0'
        assert 'EXACTAMENTE' in out['explanation']['es'] and 'EXACTLY' in out['explanation']['en']
    assert 'rho_crisis' in {s['name']: s for s in _replay(d_fire)['steps']}['deterministic_core']['compared']
    _W.update({'scn': d_scn, 'imp': d_imp, 'fire': d_fire,
               'top': [k for k, _v in json.loads(json.dumps(_dec(d_scn)['output']['top']))]})


def _dec(did):
    from core import decisions
    from ontology.db import session_scope
    with session_scope() as s:
        return decisions.get(s, did, redact=False)


def test_un_cambio_posterior_del_grafo_no_cambia_el_replay(db, client):
    w = _W
    gv0 = _replay(w['scn'])['world']['graph_version']
    with __import__('ontology.db', fromlist=['x']).session_scope() as s:
        _ev(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 6}, 'RE', 'RA')     # RE ahora alimenta a RA
        _ev(s, 'ObjectUpdated', {'properties': {'severity': 9.0}}, 'RF')
    for did in (w['scn'], w['imp'], w['fire']):
        out = _replay(did)
        _ok(out)
        assert out['world']['graph_version'] == gv0               # κ = lo que se leyó, no lo de hoy


def test_detecta_un_cambio_de_codigo_que_altera_el_resultado(db, monkeypatch):
    from core.hotviews.views import impact
    w = _W
    real = impact.scenario

    def bent(core, x0, **kw):                  # «nuevo código» que mueve un impacto 0,01 puntos
        out = real(core, x0, **kw)
        k = next(iter(out['impacts']))
        out['impacts'] = dict(out['impacts'], **{k: round(out['impacts'][k] - 0.01, 2)})
        return out
    monkeypatch.setattr(impact, 'scenario', bent)
    out = _replay(w['scn'])
    assert out['verdict'] == 'differs' and out['reproduced'] is False
    core = next(s for s in out['steps'] if s['name'] == 'deterministic_core')
    paths = {d['path'] for d in core['diffs']}
    assert 'content_sha' in paths and core['ok'] is False
    assert 'DISTINTO' in out['explanation']['es'] and 'DIFFERENT' in out['explanation']['en']


def test_kernel_1_se_repite_identico_despues_de_activar_2(db, client):
    from core import governance, governance_flow, identity
    from ontology.db import session_scope
    w = _W
    assert 'RD' in w['top']                                        # 1.0.0: el socio RD recibe daño
    vid = governance_flow.validate(identity.operator(), 'kernel.params', '2.0.0')['decision_id']
    with session_scope() as s:
        governance.activate(s, identity.operator(), {'kernel.params': '2.0.0'}, validation_id=vid)
    governance.refresh()
    try:
        assert governance.artifact_semver('kernel.params') == '2.0.0'
        for did in (w['scn'], w['imp'], w['fire']):
            out = _replay(did)
            _ok(out)
            assert out['world']['release_semver']['kernel.params'] == '1.0.0'   # el release de ENTONCES
        r = client.post('/api/hot/scenario', json={'shocks': [{'id': 'RA', 'magnitude': 0.9}]})
        assert r.status_code == 200
        _flush()
        d2 = _last('whatif.shock')
        assert _dec(d2)['output']['content_sha'] != _dec(w['scn'])['output']['content_sha']
        assert 'RD' not in [k for k, _v in _dec(d2)['output']['top']]   # 2.0.0: los socios no transmiten daño
        out2 = _replay(d2)
        _ok(out2)
        assert out2['world']['release_semver']['kernel.params'] == '2.0.0'
        out_v = _replay(vid)                                       # la regresión misma se repite (parte de choques)
        st = _ok(out_v)
        assert st['deterministic_core']['impl'] == 'gov-regression@1'
        assert 'regression_ledger_window' in out_v['reasons']
    finally:
        with session_scope() as s:                                 # deshacer: vuelve 1.0.0 (otra decisión)
            governance.activate(s, identity.operator(), {'kernel.params': '1.0.0'})
        governance.refresh()
    assert governance.artifact_semver('kernel.params') == '1.0.0'


# ── comité ───────────────────────────────────────────────────────────────────────────────────────────────────────
def test_committee_run_tamano_se_repite_con_y_sin_cliente(db):
    from ontology.db import session_scope
    from research.committee import run_committee
    from research.llm import FakeProvider
    from tests.test_phase3 import DEPS, _FakeBroker, _chair_json, _fresh_entity_claims
    with session_scope() as s:
        _fresh_entity_claims(s, 'Broadcom')
        m1 = run_committee(s, 'Broadcom', 'pytest', client_id='cli-1',
                           provider=FakeProvider([lambda p: _chair_json(p)]), deps=dict(DEPS, brokerage=_FakeBroker()))
    with session_scope() as s:
        _fresh_entity_claims(s, 'Marvell')
        m2 = run_committee(s, 'Marvell', 'pytest', provider=FakeProvider([lambda p: _chair_json(p)]), deps=DEPS)
    from sqlalchemy import text
    with session_scope() as s:
        ids = [str(r[0]) for r in s.execute(text("SELECT id FROM decisions WHERE kind = 'committee.run' AND "
                                                  "subject->>'memo_id' = ANY(:m) ORDER BY seq"),
                                             {'m': [m1['memo_id'], m2['memo_id']]})]
    assert len(ids) == 2
    for did, m in zip(ids, (m1, m2)):
        out = _replay(did)
        st = _ok(out)
        core = st['deterministic_core']
        assert core['impl'] == 'compute_sizing@1' and not core['diffs']
        assert set(core['compared']) == {'quant_decision', 'decision_code', 'quorum_ok', 'sizing'}
        d = _dec(did)
        assert d['manifest']['replay']['impl'] == 'compute_sizing@1'
    # el tamaño repetido es el del memo (con cliente: patrimonio y posición de la foto guardada)
    assert m1['sizing']['equity'] == 100000.0


def test_committee_detecta_umbral_cambiado_en_el_codigo(db, monkeypatch):
    """Si el código pasara a leer otro umbral (sin que cambie el release), el replay lo marca."""
    from core import impls
    from sqlalchemy import text
    from ontology.db import session_scope
    with session_scope() as s:
        did = str(s.execute(text("SELECT id FROM decisions WHERE kind = 'committee.run' ORDER BY seq DESC LIMIT 1"))
                  .scalar())
    real = impls.module_view

    def tweaked(mod, arts, notes=None):
        v = real(mod, arts, notes)
        if mod == 'research.committee':
            impls.view_with(v, UNVALIDATED_FACTOR=0.25)
        return v
    monkeypatch.setattr(impls, 'module_view', tweaked)
    out = _replay(did)
    assert out['verdict'] == 'differs'
    core = next(s for s in out['steps'] if s['name'] == 'deterministic_core')
    assert any(p['path'].startswith('sizing.') for p in core['diffs'])


# ── órdenes ──────────────────────────────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def alpaca(monkeypatch, db):
    import requests

    from tests.test_order_single_path import HTTPAlpaca
    fake = HTTPAlpaca()
    for name in ('request', 'get', 'post', 'delete'):
        monkeypatch.setattr(requests, name, getattr(fake, name))
    for k, v in (('ALPACA_KEY', 'PKFAKEKEY0001'), ('ALPACA_SECRET', 'FAKE-SECRET-123'),
                 ('ALPACA_BASE', 'https://paper-api.alpaca.markets')):
        monkeypatch.setenv(k, v)
    for k in ('BROKERAGE_TRADING_ENABLED', 'BROKERAGE_LIVE_ENABLED', 'BROKERAGE_AUTO_APPROVE_PAPER'):
        monkeypatch.delenv(k, raising=False)
    return fake


def test_order_preview_y_confirm_controles_identicos(db, alpaca, monkeypatch):
    from brokerage import service
    from ontology.db import session_scope
    with session_scope() as s:
        p = service.preview_order(s, 'house', 'AMD', 'buy', notional=6000, source='ui', requested_by='pytest')
    assert p['blocked']
    out = _replay(p['decision_id'])
    st = _ok(out)
    assert st['deterministic_core']['impl'] == 'run_checks@1' and st['deterministic_core']['compared'] == ['checks']
    assert st['gates']['ok'] is True and any(r['gate'] == 'order.pre_trade' for r in st['gates']['reports'])
    with session_scope() as s:
        res = service.house_order(s, 'NVDA', 'buy', notional=15, requested_by='pytest')
    assert res['ok'], res
    d_conf = _last('order.confirm')
    _ok(_replay(d_conf))
    # el interruptor de entorno que regía se respeta (hoy APAGADO no cambia la repetición de ayer)
    monkeypatch.setenv('BROKERAGE_TRADING_ENABLED', 'off')
    _ok(_replay(p['decision_id']))
    monkeypatch.delenv('BROKERAGE_TRADING_ENABLED', raising=False)
    # una orden anterior al paso 24 (sin entradas de replay) se declara no repetible, sin inventar
    from core import replay as R
    real = R._mf

    def no_replay(run, session, key):
        return None if key == 'replay' else real(run, session, key)
    monkeypatch.setattr(R, '_mf', no_replay)
    old = _replay(p['decision_id'])
    assert 'inputs_not_stored' in old['reasons']
    assert old['verdict'] == 'identical'                          # las puertas guardadas sí se repiten


# ── puertas de una acción de la ontología ───────────────────────────────────────────────────────────────────────
def test_puertas_de_una_accion_se_repiten_con_el_ir_de_entonces(db):
    from core import identity
    from ontology.actions import execute_action
    from ontology.db import session_scope
    meta = {}
    with session_scope() as s:
        out = execute_action(s, 'ProponerVinculo', {'from_id': 'RA', 'to_id': 'RA', 'tipo': 'suministra_a',
                                                    'metadata': {'weight': 7.5}, 'fuente': 'prueba', 'peso': 9},
                             'op:fabrizio', principal=identity.operator(), meta=meta)
    assert out['status'] == 'proposed'
    did = meta['decision_id']
    d = _dec(did)
    gf = d['manifest']['gate_focus']
    assert {g['gate'] for g in gf} >= {'ontology.g1.link', 'ontology.g2.action'}
    assert all(len(g['rsha']) == 64 and g['blob'] for g in gf)
    rep = _replay(did)
    st = _ok(rep)
    assert st['gates']['ok'] is True and all(r['ok'] for r in st['gates']['reports'])
    assert 'no_deterministic_core' in rep['reasons']              # la acción es una escritura: no hay «cálculo»


# ── IA: solo verificación; blob purgado ──────────────────────────────────────────────────────────────────────────
def test_ia_no_se_reejecuta_y_el_guardian_se_verifica(db, monkeypatch):
    from core import ai_calls, decisions, identity
    from ontology.db import session_scope
    ctx = decisions.DecisionCtx('chat.answer', identity.system('pytest_chat'), durability='async')
    with ai_calls.attribute(ctx.id, durability='async'):
        rec = ai_calls.begin('reglas', 'DATOS: Nvidia cotiza a 182,40 USD.', tier='fast')
        rec = ai_calls.finish(rec, text='Nvidia vale 300 USD hoy.', used='claude:claude-haiku-4-5', acc={})
        rec['guardian'] = {'kinds': ['money'], 'unsupported': 1, 'retried': False, 'marked': 1, 'outcome': 'marked',
                           'attempt': 'first'}
        ai_calls.submit(rec)
    ctx.output = {'answer_sha': 'x'}
    with session_scope() as s:
        decisions.record(s, ctx, status='answered')
    _flush()
    out = _replay(str(ctx.id))
    assert out['verdict'] == 'not_replayable' and 'ai_text' in out['reasons']
    ai = next(s for s in out['steps'] if s['name'] == 'ai_steps')
    call = ai['calls'][0]
    assert call['prompt_sha_ok'] and call['output_sha_ok'] and call['guardian_ok']
    assert call['guardian'] == {'recorded': 1, 'replayed': 1}
    assert 'IA' in out['explanation']['es'] and 'AI' in out['explanation']['en']
    # el blob de entrada se PURGA (retención de 90 días: la base solo deja vaciarlo a los 90 días, así que la prueba
    # simula la lectura de un blob purgado): se dice, nunca se inventa
    from sqlalchemy import text

    from core import replay as R
    with session_scope() as s:
        purged = s.execute(text('SELECT input_blob FROM ai_calls WHERE decision_id = CAST(:d AS uuid)'),
                           {'d': str(ctx.id)}).scalar()
    real = R._blob
    monkeypatch.setattr(R, '_blob', lambda session, sha: (None, 'purged') if sha == purged else real(session, sha))
    out2 = _replay(str(ctx.id))
    assert 'blob_purged' in out2['reasons'] and out2['verdict'] == 'not_replayable'
    assert any(c.get('purged') for c in next(s for s in out2['steps'] if s['name'] == 'ai_steps')['calls'])
    assert '90 días' in out2['explanation']['es'] and '90 days' in out2['explanation']['en']


# ── API, MCP, muestra nocturna ───────────────────────────────────────────────────────────────────────────────────
def test_api_replay_why_audit_con_y_sin_pin(db, client):
    w = _W
    r = client.get(f"/api/ledger/replay/{w['scn']}")
    assert r.status_code == 200
    d = r.get_json()
    assert d['redacted'] is True and d['verdict'] == 'identical'
    assert all('diffs' not in s and 'blobs' not in s for s in d['steps'])   # sin PIN: sin valores
    r = client.post(f"/api/ledger/replay/{w['scn']}", headers={'X-Trade-Pin': PIN})
    assert r.status_code == 200 and r.get_json()['redacted'] is False
    assert client.get('/api/ledger/replay/no-es-uuid').status_code == 400
    assert client.get('/api/ledger/replay/00000000-0000-0000-0000-000000000000').status_code == 404
    assert client.get(f"/api/ledger/replay/{w['scn']}?mode=counterfactual").status_code == 400
    wy = client.get(f"/api/ledger/why/{w['fire']}").get_json()
    assert wy['kind_label']['es'].startswith('Qué pasaría') and wy['replayable'] is True and wy['redacted'] is True
    assert 'subject' not in wy and 'principal_id' not in wy and len(wy['lines_es']) == len(wy['lines_en']) >= 6
    assert 'kernel.params' in wy['lines_es'][3]
    wy2 = client.get(f"/api/ledger/why/{w['fire']}", headers={'X-Trade-Pin': PIN}).get_json()
    assert wy2['redacted'] is False and 'subject' in wy2
    a = client.get('/api/ledger/audit?kind=whatif.shock&limit=5').get_json()
    assert a['count'] >= 2 and all(x['kind'] == 'whatif.shock' and x['replayable'] for x in a['decisions'])
    assert 'principal_id' not in a['decisions'][0] and any(k['kind'] == 'audit.replay' for k in a['kinds'])
    assert client.get('/api/ledger/audit?principal_kind=robot').status_code == 400
    a2 = client.get('/api/ledger/audit?principal_kind=system&limit=50').get_json()
    assert all(x['principal_kind'] == 'system' for x in a2['decisions'])
    assert client.get('/api/ledger/audit?until=2000-01-01T00:00:00Z').get_json()['count'] == 0
    # el replay por la API queda en el libro: decision_outcome 'replay' + audit.replay del auditor
    _flush()
    from sqlalchemy import text
    from ontology.db import session_scope
    with session_scope() as s:
        n = s.execute(text("SELECT count(*) FROM decision_outcomes WHERE outcome_kind = 'replay' AND "
                           "decision_id = CAST(:d AS uuid)"), {'d': w['scn']}).scalar()
        a = s.execute(text("SELECT count(*) FROM decisions WHERE kind = 'audit.replay' AND "
                           "subject->>'target_id' = :d"), {'d': w['scn']}).scalar()
    assert n >= 1 and a >= 1


def test_mcp_replay_decision(db):
    from mcp_server import tools
    t = tools.REGISTRY['replay_decision']
    assert t.scope == 'read'
    w = _W
    out = t.handler({'principal': None}, w['fire'])
    assert out['verdict'] == 'identical' and out['redacted'] is True and out['source']
    with pytest.raises(Exception):
        t.handler({'principal': None}, 'no-es-uuid')


def test_muestra_nocturna_registra_conteos(db):
    from core import replay
    out = replay.sample(force=True)
    assert out['sampled'] >= 4 and out['counts']['identical'] >= 4 and out['counts']['differs'] == 0
    assert 'order.preview' in out['by_kind'] or 'order.confirm' in out['by_kind']   # TODAS las de dinero
    assert replay.sample()['skipped'] == 'already_today'
    st = replay.status()
    assert st['last']['sampled'] == out['sampled'] and st['differs'] == 0
    au = _replay(_last('audit.replay'))       # repetir la propia auditoría: un registro, nunca «código perdido»
    assert au['verdict'] == 'not_replayable' and au['reasons'] == ['no_deterministic_core'], au['reasons']


def test_diagnostico_en_rojo_si_la_muestra_tiene_distintas(db, monkeypatch):
    import server
    from core import replay
    ok_card = server._diag_gobernanza()
    assert 'Repetición (muestra' in ok_card['detail'] and 'Replay (sample' in ok_card['detail_en']
    real = replay.status

    def bad(engine=None):
        st = real(engine)
        st['differs'] = 1
        st['last'] = dict(st['last'] or {}, counts={'identical': 3, 'differs': 1, 'not_replayable': 0})
        return st
    monkeypatch.setattr(replay, 'status', bad)
    card = server._diag_gobernanza()
    assert card['ok'] is False and card['replay']['differs'] == 1
    assert '⚖ Auditoría' in card['fix_es'] and '⚖ Audit' in card['fix_en']


def test_vista_viva_y_grafo_de_entonces_tienen_la_misma_huella(db):
    """Factores que comparten un miembro: la fragilidad suma en orden canónico en la vista viva (tabla) y en G(t, κ)
    (eventos). Antes el orden de lectura difería y la huella de GraphCore también (1 ulp)."""
    from core.hotviews import source
    from core.hotviews.views import asof, graph_core
    from ontology import bitemporal
    from ontology.db import session_scope
    with session_scope() as s:
        for fid, w in (('RF4', 0.7), ('RF2', 0.3), ('RF3', 0.4), ('RF1', 0.6)):
            _ev(s, 'ObjectCreated', {'label': fid, 'type': 'Factor', 'properties': {'severity': 1.0}}, fid)
            _ev(s, 'LinkCreated', {'rel_type': 'affects', 'weight': w}, fid, 'RC')
    live = source.load_pg()
    with session_scope() as s:
        then = asof.load(s, None, bitemporal.resolve(s, live.graph_version))
    assert [f['id'] for f in live.factors] == [f['id'] for f in then.factors] == sorted(f['id'] for f in live.factors)
    assert graph_core.build(live).content_sha == graph_core.build(then).content_sha


def test_fragilidad_no_depende_del_orden_de_lectura():
    import numpy as np

    from matrix import engine as E
    idx = {'X': 0}
    fs = [{'id': f'F{i}', 'severity': 1.0, 'members': {'X': c}} for i, c in enumerate((0.7, 0.3, 0.4, 0.6))]
    a = E.fragility(idx, E._canonical_factors([dict(f) for f in fs]))
    b = E.fragility(idx, E._canonical_factors([dict(f) for f in reversed(fs)]))
    assert np.array_equal(a, b)
