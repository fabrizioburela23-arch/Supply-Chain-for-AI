"""tests/test_governance_flow.py — INFRA_OPERATIVA paso 25: flujo de gobernanza COMPLETO.

    proponer (PIN, lint del repo) → regresión contrafactual (libro real + choques + NRS + formas en sombra)
    → programar con effective_from (el reloj la pone en vigor; se puede cancelar antes) → activar → deshacer
    → atribución (qué versiones decidieron una decisión).

Sin base: el lint (semver honesto, esquema de afinables, espejos) con mensajes ES/EN, «¿qué cambia para mí?», la
fórmula NRS con otros parámetros sin tocar la vigente, la sombra de formas y el D5 del cierre de NY.
Con base: el recorrido entero por la API con el PIN de Fabrizio (D1: un solo aprobador; four_eyes 'unavailable').
"""
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
PIN = 'pin-flujo-25-xyz'


# ── lint de la propuesta (sin base) ──────────────────────────────────────────
def test_propuesta_honesta_se_arma_como_major_con_la_version_siguiente():
    from core import governance_flow as F
    doc, diffs, probs = F.build_proposal('kernel.params', {'damping': '0,55'})
    assert probs == []
    assert diffs == [{'path': 'damping', 'from': 0.6, 'to': 0.55}]
    # 2.0.0 ya existe en el repositorio (disponible con PIN): la siguiente mayor libre es 3.0.0
    assert doc['semver'] == '3.0.0' and doc['change_kind'] == 'major' and doc['parent'] == 'kernel.params@1.0.0'
    assert doc['activation'] == 'pin' and doc['origin'] == 'app'
    assert 'damping' in doc['changelog_es'] and 'damping' in doc['changelog_en']


def test_propuesta_que_rompe_semver_se_rechaza_con_mensaje_bilingue():
    from core import governance_flow as F
    _d, _x, probs = F.build_proposal('kernel.params', {'damping': 0.55}, change_kind='minor')
    assert [p['code'] for p in probs] == ['minor_changes']
    assert 'MINOR solo agrega' in probs[0]['es'] and 'MINOR only adds' in probs[0]['en']
    _d, _x, probs = F.build_proposal('kernel.params', {'damping': 0.55}, change_kind='patch')
    assert 'patch_changes' in [p['code'] for p in probs]
    _d, _x, probs = F.build_proposal('kernel.params', {'damping': 0.55}, change_kind='major', semver='1.0.1')
    assert [p['code'] for p in probs] == ['bump_mismatch'] and probs[0]['en']
    _d, _x, probs = F.build_proposal('kernel.params', {'damping': 0.55}, semver='2.0.0')
    assert [p['code'] for p in probs] == ['semver_taken']           # el registro solo crece


def test_esquema_y_espejos():
    from core import governance_flow as F
    codes = lambda *a, **k: [p['code'] for p in F.build_proposal(*a, **k)[2]]  # noqa: E731
    assert codes('kernel.params', {'damping': 0.99}) == ['out_of_range']
    assert codes('kernel.params', {'max_hops': 3.5}) == ['not_int']
    assert 'mirror' in codes('kernel.params', {'rel_weights.license': 0.8})     # espejo del vocabulario
    assert codes('nrs.formula', {'chain_cap': 20}) == ['mirror']                  # espejo en app.html
    assert codes('policy.gates', {'limits.max_weight': 5}) == ['mirror']          # bloqueo: solo por versión del repo
    assert codes('kernel.params', {'no_existe': 1}) == ['unknown_key']
    assert codes('policy.committee', {'buy_threshold': -30}) == ['out_of_range', 'relation']
    # BRECHAS #1 sin respuesta: el tope por orden nunca supera los US$100.000 de hoy
    assert codes('policy.broker_risk', {'hard_max_order_usd': 200000}) == ['out_of_range']
    assert set(codes('policy.broker_risk', {'hard_max_order_usd': 1000})) == {'relation'}    # perfiles > tope
    assert codes('kernel.params', {'damping': 0.6}) == ['no_change']


def test_el_script_usa_el_mismo_lint_y_revisa_los_afinables():
    from core import governance_lint as GL
    from scripts import build_governance as B
    assert B._diff_kind is GL.diff_kind
    assert B.check(verbose=False) == []
    from core import governance as G
    assert GL.tunables_problems(G.latest_per_id(G.scan_repo())) == []
    for aid, tab in GL.tunables().items():
        if aid.startswith('_'):
            continue
        for path, spec in tab.items():
            assert spec['label_es'] and spec['label_en'] and spec['help_es'] and spec['help_en'], (aid, path)


def test_d5_politica_del_corretaje_entra_despues_del_cierre_de_ny():
    from core import governance_flow as F
    assert F.parse_effective_from('now', {'policy.broker_risk': '2.0.0'}) is None
    assert F.parse_effective_from(None, {'kernel.params': '3.0.0'}) is None           # D5: inmediato por defecto
    t = F.parse_effective_from(None, {'policy.broker_risk': '2.0.0'})
    assert t > datetime.now(timezone.utc) and t.weekday() < 5
    sat = datetime(2026, 10, 17, 15, 0, tzinfo=timezone.utc)                           # sábado
    assert F.next_ny_close(sat).weekday() == 0                                          # → lunes
    with pytest.raises(ValueError):
        F.parse_effective_from('2026-10-14T10:00:00', {})                               # sin zona horaria
    with pytest.raises(ValueError):
        F.parse_effective_from((datetime.now(timezone.utc) + timedelta(days=200)).isoformat(), {})


def test_nrs_con_otros_parametros_no_toca_la_formula_vigente():
    from core import governance, world
    from core.hotviews import hot
    g = hot.graph()
    cur = governance.section('nrs.formula')
    alt = dict(cur, chain_cap=10)
    diff = 0
    for n in g.nodes:
        d = g.flow_degree.get(n['id'], 0)
        assert world.nrs_terms(n, d, params=cur) == world.nrs_terms(n, d)        # paridad exacta
        diff += world.nrs_terms(n, d, params=alt)['total'] != world.nrs_terms(n, d)['total']
    assert diff > 0
    assert world._NRS_CHAIN_CAP == cur['chain_cap']                                 # la vigente no se movió


def test_que_cambia_para_mi_con_mis_posiciones(monkeypatch):
    import ontology.db as odb
    import server
    from core import governance_preview
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    governance_preview.reset()
    c = server.app.test_client()
    d = c.get('/api/governance/preview?artifact=kernel.params&semver=2.0.0&ids=Nvidia,Apple').get_json()
    fm = d['for_me']
    assert fm['basis'] == 'positions' and [x['id'] for x in fm['items']][:2] and \
        {x['id'] for x in fm['items']} == {'Nvidia', 'Apple'}
    assert fm['lines_es'] and fm['lines_en'] and len(fm['lines_es']) == len(fm['lines_en'])
    d = c.get('/api/governance/preview?artifact=kernel.params&semver=2.0.0').get_json()
    assert d['for_me']['basis'] == 'top10' and len(d['for_me']['items']) == 10
    d = c.get('/api/governance/preview?artifact=policy.gates&semver=1.0.0').get_json()
    assert d['for_me']['basis'] == 'params'


def test_sin_base_proponer_responde_503_y_la_historia_trae_el_formulario(monkeypatch):
    import ontology.db as odb
    import server
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    c = server.app.test_client()
    r = c.post('/api/governance/propose', json={'artifact': 'kernel.params', 'changes': {'damping': 0.55}})
    assert r.status_code == 503 and r.get_json()['code'] == 'ledger_unavailable'
    h = c.get('/api/governance/history').get_json()
    assert h['db'] is False
    f = {x['path']: x for x in h['proposable']['kernel.params']['fields']}
    assert f['damping']['value'] == 0.6 and f['damping']['min'] == 0.3 and f['damping']['label_en']
    assert 'nrs.formula' not in h['proposable'] and 'policy.gates' not in h['proposable']


# ── formas propuestas en sombra ──────────────────────────────────────────────
def test_formas_en_sombra_cuentan_la_diferencia_sin_tocar_el_veredicto(monkeypatch):
    from core import gates, governance_shadow as S
    from core.gates import engine
    S.reset_for_tests()
    assert S.arm(force=True)['armed'] is False          # hoy no hay formas más nuevas que la vigente (4.0.0)
    calls = []
    monkeypatch.setattr(S, 'tap', lambda *a: calls.append(a))
    gates.evaluate('G1', [])
    assert calls and calls[0][0] == 'G1'                # el gancho existe y es O(1)
    monkeypatch.undo()

    class Fake:
        semver = '9.0.0'
    S._STATE.update(semver='9.0.0', comp=Fake())
    raw = [('urn:x', 'prop', {'rule': 'khr:link.weight_max'}, 9, 6)]
    monkeypatch.setattr(engine, 'run', lambda comp, triples: [] if isinstance(comp, Fake) else raw)
    S.tap('G1', [('urn:x', 'rdf:type', 'kh:Link')], raw)
    assert S.drain() == 1
    st = S.stats('9.0.0')
    assert st['evaluations'] == 1 and st['with_diff'] == 1 and st['gone_by_rule'] == {'khr:link.weight_max': 1}
    S.reset_for_tests()


# ── con base: el recorrido entero ────────────────────────────────────────────
@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from core import governance, governance_flow, governance_shadow
    from core.hotviews import hot, registry
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    governance._reset_for_tests()
    governance_flow.reset_for_tests()
    governance_shadow.reset_for_tests()
    assert init_schema(retries=1)
    yield engine
    from core.hotviews import builder
    t0 = time.time()
    while builder.state().get('building') and time.time() - t0 < 10:
        time.sleep(0.02)
    t0 = time.time()
    while any(j.get('state') == 'running' for j in governance_flow._JOBS.values()) and time.time() - t0 < 60:
        time.sleep(0.05)
    governance._reset_for_tests()
    governance_flow.reset_for_tests()
    registry.reset()
    hot.reset()
    Base.metadata.drop_all(engine)


def _client(monkeypatch):
    import server
    from core import http as core_http
    from core import pin
    monkeypatch.setenv('TRADE_PIN', PIN)
    pin._reset_for_tests()
    c = server.app.test_client()
    real_post, real_get = c.post, c.get

    def post(*a, **k):                     # los límites reales (6/min) no son lo que se prueba aquí
        core_http._rate_buckets.clear()
        k.setdefault('headers', {'X-Trade-Pin': PIN})
        return real_post(*a, **k)

    def get(*a, **k):
        core_http._rate_buckets.clear()
        return real_get(*a, **k)
    c.post, c.get = post, get
    return c


def _whatif(entity='TSMC'):
    """Un qué-pasaría-si REAL en el libro (como lo deja /api/hot/scenario)."""
    from core import decisions, identity
    ctx = decisions.DecisionCtx('whatif.shock', identity.system('test'), subject={'entity_ids': [entity]})
    ctx.params(shock=[entity], shocks=[{'id': entity, 'magnitude': 1.0}], damping=0.6, max_hops=6,
               endpoint='/api/hot/scenario')
    ctx.output = {'top': [], 'n': 0}
    return decisions.record(None, ctx, status='executed')


def _wait_validation(c, aid, sv, timeout=90):
    t0 = time.time()
    while time.time() - t0 < timeout:
        v = c.get(f'/api/governance/validation?artifact={aid}&semver={sv}').get_json()['validation']
        if v and v['state'] != 'running':
            return v
        time.sleep(0.1)
    raise AssertionError('la validación no terminó')


@needs_db
def test_recorrido_completo_proponer_regresion_programar_activar_deshacer(db, monkeypatch):
    from sqlalchemy import text

    from core import governance, governance_flow
    from matrix import engine as E
    from core.hotviews import source
    c = _client(monkeypatch)
    # la base de prueba está vacía: la regresión corre sobre el grafo del snapshot (937 empresas), como sin base
    monkeypatch.setattr(source, 'load', source.load_snapshot)
    governance.refresh()
    boot = governance.active()
    assert boot.source == 'db' and governance.artifact_semver('kernel.params') == '1.0.0'
    w1 = _whatif('TSMC')
    _whatif('Nvidia')

    # 1) proponer: sin PIN no; con PIN → gov_artifacts (origin app) + decisión governance.propose 'proposed'
    body = {'artifact': 'kernel.params', 'changes': {'damping': 0.5}, 'ids': ['Nvidia']}
    assert c.post('/api/governance/propose', json=body, headers={}).status_code == 401
    r = c.post('/api/governance/propose', json=dict(body, change_kind='minor'))
    assert r.status_code == 422
    d = r.get_json()
    assert d['code'] == 'proposal_refused' and 'MINOR' in d['error'] and 'MINOR' in d['error_en']
    r = c.post('/api/governance/propose', json=body)
    assert r.status_code == 200, r.get_json()
    p = r.get_json()
    sv = p['semver']
    assert sv == '3.0.0' and p['four_eyes'] == 'unavailable' and p['changes'][0]['to'] == 0.5
    with db.connect() as cn:
        row = cn.execute(text("SELECT body, proposed_by FROM gov_artifacts WHERE artifact_id = 'kernel.params' "
                              'AND semver = :v'), {'v': sv}).first()
        dec = cn.execute(text("SELECT status, principal_id, auth, subject FROM decisions WHERE kind = "
                              "'governance.propose' AND subject->>'semver' = :v"), {'v': sv}).first()
    assert row.body['origin'] == 'app' and row.body['params']['damping'] == 0.5 and row.proposed_by == 'op:fabrizio'
    assert dec.status == 'proposed' and dec.principal_id == 'op:fabrizio' and dec.auth == 'pin'
    assert dec.subject['four_eyes'] == 'unavailable'
    # no entra en vigor sola; aparece en propuestas y se puede leer como versión disponible
    assert governance.artifact_semver('kernel.params') == '1.0.0' and float(E._P('damping')) == 0.6
    prop = next(x for x in governance.proposals() if x['id'] == 'kernel.params' and x['semver'] == sv)
    assert prop['origin'] == 'app' and prop['newer'] and prop['activation'] == 'pin'
    assert governance.available_artifact('kernel.params', sv)['params']['damping'] == 0.5

    # 2) regresión contrafactual en segundo plano → decisión governance.validate con su blob
    v = _wait_validation(c, 'kernel.params', sv)
    assert v['state'] == 'done', v
    rep = v['report']
    assert rep['shocks']['shocks'] > 900 and rep['shocks']['shocks_changed'] > 0
    w = rep['ledger']['whatif']
    assert w['decisions'] >= 2 and w['replayed'] >= 2 and w['changed'] >= 1
    assert rep['for_me']['basis'] == 'positions' and rep['for_me']['items'][0]['id'] == 'Nvidia'
    assert rep['summary_es'] and rep['summary_en'] and 'NRS' in rep['summary_es']
    assert float(E._P('damping')) == 0.6                                      # el motor vivo no se tocó
    with db.connect() as cn:
        vd = cn.execute(text("SELECT id, inputs_sha, output FROM decisions WHERE kind = 'governance.validate'")).all()
    assert len(vd) == 1 and vd[0].inputs_sha == vd[0].output['validation_blob']
    vid = str(vd[0].id)

    # 3) programar (effective_from en el futuro): queda 'approved', nada cambia todavía; otra activación → 409
    eff = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
    r = c.post('/api/governance/activate', json={'artifact': 'kernel.params', 'semver': sv, 'effective_from': eff})
    assert r.status_code == 200, r.get_json()
    a = r.get_json()
    assert a['scheduled'] is True and a['in_force'] is False and a['regression'] == vid
    assert governance.artifact_semver('kernel.params') == '1.0.0'
    h = c.get('/api/governance/history').get_json()
    assert len(h['scheduled']) == 1 and h['scheduled'][0]['decision_id'] == a['decision_id']
    r = c.post('/api/governance/activate', json={'artifact': 'kernel.params', 'semver': '2.0.0'})
    assert r.status_code == 409 and r.get_json()['code'] == 'scheduled_pending' and r.get_json()['error_en']
    with db.connect() as cn:
        vb = cn.execute(text('SELECT validation_blob FROM gov_releases WHERE release_hash = :r'),
                        {'r': a['release_hash']}).scalar()
    assert vb == vd[0].inputs_sha                                             # el release cita su regresión

    # 4) cancelar antes de que empiece: otra decisión (ninguna fila se toca) → nunca entra en vigor
    r = c.post('/api/governance/cancel', json={'decision_id': a['decision_id']})
    assert r.status_code == 200, r.get_json()
    assert c.post('/api/governance/cancel', json={'decision_id': a['decision_id']}).status_code == 409
    assert c.get('/api/governance/history').get_json()['scheduled'] == []

    # 5) programar de nuevo para dentro de 1,5 s → el reloj la pone en vigor y deja la decisión del sistema
    eff = (datetime.now(timezone.utc) + timedelta(seconds=1.5)).isoformat()
    r = c.post('/api/governance/activate', json={'artifact': 'kernel.params', 'semver': sv, 'effective_from': eff})
    assert r.status_code == 200 and r.get_json()['scheduled'] is True
    a2 = r.get_json()
    governance.refresh_job()
    assert governance.artifact_semver('kernel.params') == '1.0.0'                      # aún no
    time.sleep(1.8)
    out = governance.refresh_job()
    assert out['scheduled_applied'] == 1
    assert governance.artifact_semver('kernel.params') == sv and float(E._P('damping')) == 0.5
    assert governance.refresh_job()['scheduled_applied'] == 0                          # idempotente
    with db.connect() as cn:
        ap = cn.execute(text("SELECT principal_id, status, subject FROM decisions WHERE kind = 'governance.activate' "
                             "AND subject->>'applies' = :i"), {'i': a2['decision_id']}).all()
        rejected = cn.execute(text("SELECT count(*) FROM decisions WHERE kind = 'governance.activate' "
                                   "AND status = 'rejected'")).scalar()
    assert len(ap) == 1 and ap[0].principal_id == 'system:governance_scheduler' and ap[0].status == 'executed'
    assert rejected == 1

    # 6) atribución: una decisión tomada AHORA la decidió kernel.params@<sv>; la de antes, 1.0.0
    w2 = _whatif('ASML')
    at = c.get(f'/api/governance/attribution?decision_id={w2}').get_json()
    assert at['artifacts']['kernel.params']['semver'] == sv and at['release']['source'] == 'gov_releases'
    assert at['explain_es'] and at['explain_en']
    at1 = c.get(f'/api/governance/attribution?decision_id={w1}').get_json()
    assert at1['artifacts']['kernel.params']['semver'] == '1.0.0'
    assert c.get('/api/governance/attribution?decision_id=00000000-0000-0000-0000-000000000000').status_code == 404

    # 7) D2: el entorno NO fija números ni elige una versión que ningún release aprobó
    monkeypatch.setenv('FRAGILITY_CAP', '9')
    monkeypatch.setenv('KERNEL_PARAMS', '2.0.0')            # nunca estuvo en un release aprobado
    governance.refresh()
    assert governance.artifact_semver('kernel.params') == sv and float(E._P('fragility_cap')) == 2.5
    monkeypatch.delenv('FRAGILITY_CAP')
    monkeypatch.delenv('KERNEL_PARAMS')
    governance.refresh()

    # 8) deshacer = volver al release anterior (otra decisión; reactiva el del arranque)
    h = c.get('/api/governance/history').get_json()
    assert h['undo'] and h['undo']['to_release'] == boot.release_hash
    r = c.post('/api/governance/activate', json={'release_hash': h['undo']['to_release']})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()['reactivation'] is True and r.get_json()['in_force'] is True, (r.get_json(), governance._STATE['db_error'], governance.active().release_hash)
    assert governance.artifact_semver('kernel.params') == '1.0.0' and float(E._P('damping')) == 0.6
    kinds = {x['kind'] for x in c.get('/api/governance/history').get_json()['decisions']}
    assert {'governance.propose', 'governance.validate', 'governance.activate'} <= kinds
    with db.connect() as cn:   # todo es append-only: ninguna fila de gov_* se cambió
        assert cn.execute(text('SELECT count(*) FROM gov_releases')).scalar() == 2
    governance_flow.reset_for_tests()


@needs_db
def test_regresion_de_politicas_sobre_el_libro_real(db, monkeypatch):
    """policy.committee reclasifica memos reales; policy.broker_risk revisa los montos de órdenes recientes."""
    from core import decisions, governance, governance_flow, identity
    governance.refresh()
    who = identity.system('test')
    for conv in (40.0, 30.0, -25.0):
        ctx = decisions.DecisionCtx('committee.run', who, subject={'entity_ids': ['Nvidia']})
        ctx.output = {'overall_conviction': conv, 'n_claims': 3, 'memo_id': f'm{conv}'}
        from ontology.db import session_scope
        with session_scope() as s:
            decisions.record(s, ctx, status='proposed')
    cur = governance.section('policy.committee')
    new = dict(cur, buy_threshold=25.0)
    out = governance_flow._ledger_committee(cur, new)
    assert out['replayed'] == 3 and out['changed'] == 1                      # 30 pasa de mantener a comprar
    assert out['examples'][0]['zone_before'] == 'hold' and out['examples'][0]['zone_after'] == 'buy'
    pol = governance.section('policy.broker_risk')
    client = {'risk_profile': 'moderado', 'risk_limits': {}}
    assert governance_flow._order_amount_verdict(4000, client, pol) == set()
    tighter = dict(pol, profiles=dict(pol['profiles'], moderado=dict(pol['profiles']['moderado'], max_order_usd=3000)))
    assert governance_flow._order_amount_verdict(4000, client, tighter) == {'max_order'}
    assert governance_flow._order_amount_verdict(4000, {'risk_profile': 'moderado',
                                                        'risk_limits': {'max_order_usd': 5000}}, tighter) == set()
