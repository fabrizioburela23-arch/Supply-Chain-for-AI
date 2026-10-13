"""tests/test_ledger_callsites_committee.py — INFRA_OPERATIVA §2.5 (sitios de llamada del libro), pasos 18 y 19:
COMITÉ, INVESTIGACIÓN, PROPUESTAS y ALERTAS (la parte de dinero está en tests/test_ledger_callsites.py).

  committee.run (memo 'proposed', claims citados con huella, policy.committee, cotización con fuente y fecha, paquete y
  transcripción como blobs, puerta G5 en sombra) → approval.grant | approval.deny (hijas; la previsualización queda
  dentro) · committee.portfolio_advice (después de responder, dueño como hash) · policy.change con valor anterior
  (cliente de corretaje, límites de IA) · research.job (creación + cierre) → research.run (claims y evidencia E#) →
  claim.status (superseded / falsified) y decision_outcomes 'claim_eval' · proposal.create → proposal.auto_apply →
  ontology.action · approval.* humanos de propuestas · alert.rule (dueño como hash) · alert.fire (async, sin inundar).
Sin red. Las pruebas con base se saltan sin DATABASE_URL.
"""
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
UTC = timezone.utc
PIN = '4321'


@pytest.fixture(scope='module')
def db():
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    import brokerage.models  # noqa: F401
    import research.models  # noqa: F401
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def clean(monkeypatch):
    from core import http as h
    from core import pin
    for v in ('RAILWAY_ENVIRONMENT', 'RAILWAY_ENVIRONMENT_NAME', 'RAILWAY_PROJECT_ID'):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv('TRADE_PIN', PIN)
    pin._reset_for_tests()
    with h._rate_lock:
        h._rate_buckets.clear()
    yield
    pin._reset_for_tests()


def _q(sql, **kw):
    from sqlalchemy import text
    from ontology.db import session_scope
    with session_scope() as s:
        return [dict(r._mapping) for r in s.execute(text(sql), kw)]


def _decs(kind, **subject):
    return _q("SELECT id, kind, status, parent_id, principal_id, principal_kind, on_behalf_of, subject, output, "
              "manifest, verdict, model, inputs_sha FROM decisions WHERE kind = :k AND subject @> CAST(:s AS jsonb) "
              "ORDER BY seq", k=kind, s=json.dumps(subject))


def _refs(did, role=None):
    rows = _q("SELECT role, ref_kind, ref_id, ref_hash, note FROM decision_refs WHERE decision_id = CAST(:i AS uuid)",
              i=str(did))
    return [r for r in rows if role is None or r['role'] == role]


def _viols(did):
    return _q("SELECT rule_iri, severity, value FROM decision_violations WHERE decision_id = CAST(:i AS uuid)",
              i=str(did))


def _blob(sha):
    import zlib
    r = _q("SELECT body, retention_class FROM decision_blobs WHERE sha256 = :s", s=sha)
    return (json.loads(zlib.decompress(bytes(r[0]['body']))), r[0]['retention_class']) if r else (None, None)


# ════════════════════════════════════════════════════════════════════════════
# puerta G5 (sin base): el foco y la sombra
# ════════════════════════════════════════════════════════════════════════════
def _memo(**kw):
    base = dict(id='m-1', decision='BUY', quant_decision='BUY', ai_used=True,
                created_at=datetime.now(UTC) - timedelta(hours=1),
                sizing={'raw_weight_pct': 5.304, 'max_position_pct': 10.0, 'target_weight_pct': 2.652,
                        'unvalidated': True},
                memo={'track_validation': {'validated': False, 'status': 'unvalidated'}, 'quorum': {'ok': True},
                      'decision_code': None},
                inputs={'n_claims': 6})
    base.update(kw)
    return SimpleNamespace(**base)


def _g5(memo):
    import core.gates as gates
    from core.decision_sites import memo_facts
    from core.gates import focus as F
    t, foc = F.memo_triples(memo_facts(memo))
    return gates.evaluate('committee.g5', t, foc)


def test_g5_memo_sin_validar_a_la_mitad_pasa_y_sin_mitad_avisa():
    ok = _g5(_memo())
    assert ok is not None and ok['results'] == [] and ok['outcome'] == 'pass'
    bad = _g5(_memo(sizing={'raw_weight_pct': 5.304, 'max_position_pct': 10.0, 'target_weight_pct': 5.304,
                            'unvalidated': False}))
    rules = {r['rule']: r for r in bad['results']}
    assert set(rules) == {'khr:memo.unvalidated_half', 'khr:memo.unvalidated_label'}
    # SOMBRA: lo que el TTL declara 'block' rige como aviso (nada se rechaza en el paso 18)
    assert rules['khr:memo.unvalidated_half']['severity'] == 'block'
    assert rules['khr:memo.unvalidated_half']['effective'] == 'warn' and bad['outcome'] == 'warn'
    assert bad['mode'] == 'shadow' and bad['shapes']['semver'] == '4.0.0'
    assert 'mitad' in rules['khr:memo.unvalidated_half']['message']['es']
    assert 'halved' in rules['khr:memo.unvalidated_half']['message']['en']


def test_g5_quorum_caducidad_y_tope_del_mandato():
    noq = _g5(_memo(memo={'track_validation': {'validated': True}, 'quorum': {'ok': False},
                          'decision_code': None}, sizing={'raw_weight_pct': 5.0, 'max_position_pct': 10.0,
                                                          'target_weight_pct': 5.0, 'unvalidated': False}))
    assert {r['rule'] for r in noq['results']} == {'khr:memo.quorum', 'khr:memo.quorum_no_ai'}
    old = _g5(_memo(created_at=datetime.now(UTC) - timedelta(hours=80)))
    assert [r['rule'] for r in old['results']] == ['khr:memo.not_expired']
    big = _g5(_memo(memo={'track_validation': {'validated': True}, 'quorum': {'ok': True}},
                    sizing={'raw_weight_pct': 15.0, 'max_position_pct': 10.0, 'target_weight_pct': 12.0,
                            'unvalidated': False}))
    assert [r['rule'] for r in big['results']] == ['khr:memo.size_le_mandate']
    # sin conclusiones no hay "sin quórum" (el comité no delibera: no es un memo de datos insuficientes)
    empty = _g5(_memo(decision='HOLD', inputs={'n_claims': 0}, memo={'quorum': {'ok': False},
                                                                     'track_validation': {'validated': True}},
                      sizing={'target_weight_pct': None}))
    assert empty['results'] == []


# ════════════════════════════════════════════════════════════════════════════
# comité (paso 18)
# ════════════════════════════════════════════════════════════════════════════
@needs_db
def test_committee_run_queda_en_el_libro_con_claims_politica_cotizacion_y_g5(db):
    from ontology.db import session_scope
    from research.llm import FakeProvider
    from research.committee import run_committee
    from tests.test_phase3 import DEPS, _FakeBroker, _chair_json, _fresh_entity_claims
    with session_scope() as s:
        claims = _fresh_entity_claims(s, 'Broadcom')
        cids = {c.id for c in claims}
        m = run_committee(s, 'Broadcom', 'pytest', client_id='cli-1', provider=FakeProvider([lambda p: _chair_json(p)]),
                          deps=dict(DEPS, brokerage=_FakeBroker()))
    d = _decs('committee.run', memo_id=m['memo_id'])
    assert len(d) == 1
    d = d[0]
    assert d['status'] == 'proposed' and d['subject']['entity_ids'] == ['Broadcom']
    assert set(d['subject']['claim_ids']) == cids
    out = d['output']
    assert out['decision'] == m['decision'] and out['validated'] is False and out['sizing']['unvalidated'] is True
    assert out['sizing']['target_weight_pct'] == m['sizing']['target_weight_pct'] and len(out['memo_sha']) == 64
    refs = _refs(d['id'])
    ev = [r for r in refs if r['role'] == 'evidence' and r['ref_kind'] == 'claim']
    assert {r['ref_id'] for r in ev} == cids and all(len(r['ref_hash']) == 64 for r in ev)
    assert any(r['role'] == 'policy' and r['ref_id'].startswith('policy.committee@') and r['ref_hash'] for r in refs)
    assert any(r['role'] == 'effect' and r['ref_kind'] == 'memo' and r['ref_id'] == m['memo_id'] for r in refs)
    q = d['manifest']['quotes'][0]
    assert q['ticker'] == m['symbol'] and q['as_of'] and q['src']               # G8: con fecha y fuente
    body, ret = _blob(d['inputs_sha'])
    assert ret == 'legal' and body['package'] == m['inputs']['package'] and body['mandate']
    assert d['manifest']['transcript_blob'] and _blob(d['manifest']['transcript_blob'])[1] == 'legal'
    # G5 corrió en sombra: el memo no validado lleva la mitad → sin violaciones del comité
    assert not [v for v in _viols(d['id']) if v['rule_iri'].startswith('khr:memo.')]
    if m['ai_used']:
        assert d['model']['prompt_version'] and 'model' in d['model']
    else:
        assert d['model'] is None and out['ai_used'] is False


@needs_db
def test_aprobar_y_rechazar_memos_dejan_approval_hijas_con_g5(db):
    from ontology.db import session_scope
    from research.committee import approve_memo, reject_memo, run_committee
    from research.llm import FakeProvider
    from research.models import CommitteeMemo
    from tests.test_phase3 import DEPS, _FakeBroker, _chair_json, _fresh_entity_claims
    broker = _FakeBroker()
    with session_scope() as s:
        _fresh_entity_claims(s, 'Marvell')
        m = run_committee(s, 'Marvell', 'pytest', client_id='cli-1', provider=FakeProvider([lambda p: _chair_json(p)]),
                          deps=dict(DEPS, brokerage=broker))
    run_id = _decs('committee.run', memo_id=m['memo_id'])[0]['id']
    with session_scope() as s:
        out = approve_memo(s, m['memo_id'], 'op:fabrizio', note='adelante', brokerage=broker)
    assert out['ok']
    g = _decs('approval.grant', memo_id=m['memo_id'])
    assert len(g) == 1 and g[0]['status'] == 'approved' and g[0]['parent_id'] == run_id
    assert g[0]['output']['preview_id'] == 'pv-1' and g[0]['output']['preview_status'] == 'pending_approval'
    note = g[0]['manifest']['note_blob']
    assert _blob(note)[0] == {'note': 'adelante'}                         # texto del operador: auditable (§2.7)
    # segunda aprobación de un memo ya aprobado → ficha 'rejected' (bad_status), nada se ejecuta
    with session_scope() as s:
        again = approve_memo(s, m['memo_id'], 'op:fabrizio', brokerage=broker)
    assert again['code'] == 'bad_status'
    assert [x['status'] for x in _decs('approval.grant', memo_id=m['memo_id'])] == ['approved', 'rejected']
    with session_scope() as s:
        rej = reject_memo(s, m['memo_id'], 'op:fabrizio', reason='cambié de idea', brokerage=broker)
    assert rej['ok']
    dn = _decs('approval.deny', memo_id=m['memo_id'])
    assert len(dn) == 1 and dn[0]['status'] == 'rejected' and dn[0]['parent_id'] == run_id
    assert dn[0]['output']['withdrawn'] is True
    # un memo VENCIDO: la aprobación se rechaza y la puerta G5 (sombra) deja memo.not_expired en la ficha
    with session_scope() as s:
        _fresh_entity_claims(s, 'Arista')
        m2 = run_committee(s, 'Arista', 'pytest', provider=FakeProvider([lambda p: _chair_json(p)]), deps=DEPS)
    from sqlalchemy import text
    with session_scope() as s:      # (el memo es una proyección: la prueba lo envejece directo)
        s.execute(text("UPDATE committee_memos SET created_at = now() - interval '100 hours' WHERE id = :i"),
                  {'i': m2['memo_id']})
    with session_scope() as s:
        exp = approve_memo(s, m2['memo_id'], 'op:fabrizio', brokerage=broker)
        assert exp['code'] == 'expired' and s.get(CommitteeMemo, m2['memo_id']).status == 'proposed'
    ge = _decs('approval.grant', memo_id=m2['memo_id'])[0]
    assert ge['status'] == 'rejected' and ge['output']['code'] == 'expired'
    v = [x for x in _viols(ge['id']) if x['rule_iri'] == 'khr:memo.not_expired']
    assert v and v[0]['severity'] == 'warn' and v[0]['value']['declared'] == 'block'


@needs_db
def test_consejo_de_cartera_despues_de_responder_dueno_como_hash(db):
    from flask import Flask

    from core import decision_sites as ds
    app = Flask('pf')
    owner = 'propietario-secreto-1234567890'
    a = {'ok': True, 'health': {'score': 64, 'tone': 'warn', 'verdict': 'Algo arriesgada.'},
         'kpis': {'n_positions': 2, 'value_usd': 1000.0}, 'actions': [{'type': 'reduce', 'symbol': 'NVDA',
                                                                       'delta_usd': -200.0, 'priority': 1}],
         'positions': [{'entity_id': 'Nvidia', 'symbol': 'NVDA'}], 'sectors': [], 'as_of': '2026-10-13'}
    with app.test_request_context('/api/committee/portfolio', headers={'X-Khipu-Owner': owner}):
        assert ds.portfolio_advice(a, positions=[{'symbol': 'NVDA', 'shares': 3}], profile={'risk': 'moderado'})
    ds.flush()
    d = _decs('committee.portfolio_advice', entity_ids=['Nvidia'])
    assert len(d) == 1 and d[0]['status'] == 'recorded' and d[0]['on_behalf_of'].startswith('owner:')
    assert d[0]['output']['actions'][0]['symbol'] == 'NVDA' and d[0]['output']['health']['score'] == 64
    body, ret = _blob(d[0]['inputs_sha'])
    assert ret == 'legal' and body['positions'] == [{'symbol': 'NVDA', 'shares': 3}]     # D3: comité = para siempre
    assert owner not in json.dumps(d[0], default=str)


@needs_db
def test_policy_change_de_cliente_y_de_limites_de_ia_con_valor_anterior(db, monkeypatch):
    from brokerage import service
    from core import ai_usage
    from ontology.db import session_scope
    with session_scope() as s:
        c = service.create_client(s, 'Cliente Política', limits={'max_order_usd': 900}, actor='pytest')
    cid = c['client']['id']
    with session_scope() as s:
        service.update_client(s, cid, {'limits': {'max_order_usd': 1500}, 'notes': 'nota privada'}, actor='pytest')
    with session_scope() as s:
        service.update_client(s, cid, {'notes': 'otra nota'}, actor='pytest')       # sin cambio de política
    d = _decs('policy.change', policy='broker.client_limits', client_id=cid)
    assert [x['status'] for x in d] == ['executed', 'executed']
    assert d[0]['output']['before'] is None and d[0]['output']['after']['risk_limits']['max_order_usd'] == 900
    assert d[1]['output']['before']['risk_limits']['max_order_usd'] == 900
    assert d[1]['output']['after']['risk_limits']['max_order_usd'] == 1500 and d[1]['output']['changed'] == ['risk_limits']
    assert 'nota privada' not in json.dumps(d, default=str)          # notas/correo/nombre no son política
    ai_usage._STATE['settings'] = None
    ai_usage.save_settings({'daily_usd': 7.5}, 'pytest')
    ai_usage.save_settings({'daily_usd': 9}, 'pytest')
    a = _decs('policy.change', policy='ai.spend_limits')
    assert len(a) == 2 and a[1]['output']['before']['daily_usd'] == 7.5 and a[1]['output']['after']['daily_usd'] == 9
    assert a[1]['output']['changed'] == ['daily_usd'] and a[1]['principal_id'].startswith('system:')


# ════════════════════════════════════════════════════════════════════════════
# investigación (paso 19)
# ════════════════════════════════════════════════════════════════════════════
@needs_db
def test_research_job_run_claims_y_superados(db):
    from ontology.db import session_scope
    from research.models import ResearchClaim
    from tests.test_research import _claim, _result, _run
    jid = _run('Nvidia', ['fundamental'], {'fundamental': [_result([_claim()])]})
    jobs = _decs('research.job', job_id=jid)
    assert [x['status'] for x in jobs] == ['recorded', 'executed']            # creación y cierre (done)
    create, close = jobs
    assert close['parent_id'] == create['id'] and close['output']['job_status'] == 'done'
    assert create['output']['agents'] == ['fundamental']
    runs = _decs('research.run', job_id=jid)
    assert len(runs) == 1 and runs[0]['status'] == 'executed' and runs[0]['parent_id'] == create['id']
    assert runs[0]['principal_id'] == 'agent:fundamental@1.0' and runs[0]['principal_kind'] == 'agent'
    with session_scope() as s:
        c1 = s.query(ResearchClaim).filter_by(job_id=jid).one().id
    eff = _refs(runs[0]['id'], 'effect')
    assert [r['ref_id'] for r in eff if r['ref_kind'] == 'claim'] == [c1]
    ev = _refs(runs[0]['id'], 'evidence')
    assert ev and all(r['ref_kind'] == 'evidence' and len(r['ref_hash']) == 64 for r in ev)
    assert runs[0]['model']['prompt_version'] and runs[0]['output']['claims'] == 1
    # el MISMO analista/tema/horizonte otra vez → el claim viejo queda superado CON su decisión claim.status
    jid2 = _run('Nvidia', ['fundamental'], {'fundamental': [_result([_claim()])]})
    run2 = _decs('research.run', job_id=jid2)[0]
    st = _decs('claim.status', to='superseded')
    st = [x for x in st if x['parent_id'] == run2['id']]
    assert len(st) == 1 and st[0]['subject']['claim_ids'] == [c1] and st[0]['status'] == 'executed'
    note = _refs(st[0]['id'], 'effect')[0]['note']
    assert note['to'] == 'superseded' and note['by']
    with session_scope() as s:
        assert s.get(ResearchClaim, c1).status == 'superseded'


@needs_db
def test_falsador_deja_claim_status_y_claim_eval(db):
    from core import decisions, identity
    from ontology.db import session_scope
    from research.models import ResearchClaim
    from research.outcomes import evaluate_due
    from tests.test_phase3 import _mk_claim, _series
    crash = {'AVGO': _series(date(2026, 5, 1), date(2027, 7, 1), lambda d: 100.0 if d < date(2026, 6, 20) else 60.0),
             'SPY': _series(date(2026, 5, 1), date(2027, 7, 1), lambda d: 500.0)}
    with session_scope() as s:
        c = _mk_claim(s, 'Broadcom', 'fundamental', 'positive', 'SHORT_TERM', 0.8)
        c.falsifier_rules = [{'metric': 'price', 'op': '<', 'threshold': 70, 'by': '2026-09-01'}]
        cid = c.id
        # el claim lo "creó" un research.run (en producción lo escribe el runner)
        with decisions.decision_scope('research.run', identity.agent('fundamental', '1.0'), session=s,
                                      subject={'job_id': 'j-test'}) as ctx:
            ctx.effect('claim', cid)
            ctx.status = 'executed'
        run_id = str(ctx.id)
    with session_scope() as s:
        r = evaluate_due(s, now=datetime(2026, 6, 25, 12, tzinfo=UTC), price_fn=lambda sym, since: crash.get(sym))
        assert r['falsified'] == 1 and s.get(ResearchClaim, cid).status == 'falsified'
    st = [x for x in _decs('claim.status', to='falsified') if cid in x['subject']['claim_ids']]
    assert len(st) == 1 and str(st[0]['parent_id']) == run_id and st[0]['output']['reason'] == 'falsifier'
    note = _refs(st[0]['id'], 'effect')[0]['note']
    assert note['rule']['metric'] == 'price' and note['value'] < 70 and note['date'] == '2026-06-22'
    outs = _q("SELECT outcome_kind, source, result FROM decision_outcomes WHERE decision_id = CAST(:i AS uuid)",
              i=run_id)
    fal = [o for o in outs if o['result'].get('checkpoint') == 'falsifier']
    assert len(fal) == 1 and fal[0]['outcome_kind'] == 'claim_eval' and fal[0]['result']['result'] == 'miss'
    # idempotente: correr otra vez no duplica ni la transición ni el resultado
    with session_scope() as s:
        evaluate_due(s, now=datetime(2026, 7, 15, 12, tzinfo=UTC), price_fn=lambda sym, since: crash.get(sym))
    assert len([x for x in _decs('claim.status', to='falsified') if cid in x['subject']['claim_ids']]) == 1
    outs2 = _q("SELECT result FROM decision_outcomes WHERE decision_id = CAST(:i AS uuid)", i=run_id)
    assert sum(1 for o in outs2 if o['result'].get('checkpoint') == 'falsifier') == 1
    assert any(o['result'].get('checkpoint') != 'falsifier' for o in outs2)      # los checkpoints vencidos también


# ════════════════════════════════════════════════════════════════════════════
# propuestas y alertas (paso 19)
# ════════════════════════════════════════════════════════════════════════════
def _client():
    from flask import Flask

    from ontology.api import ontology_bp
    app = Flask('ledger_f1')
    app.config['TESTING'] = True
    app.register_blueprint(ontology_bp)
    return app.test_client()


class _StubAgent:
    name = 'centinela_nrs'

    def __init__(self, oid, conf):
        self.oid, self.conf = oid, conf

    def observe(self, session):
        return [{'x': 1}]

    def propose(self, session, sig):
        return {'action_type': 'AnotarObjeto', 'payload': {'object_id': self.oid, 'texto': 'nota del agente'},
                'object_id': self.oid, 'confidence': self.conf, 'explanation': 'prueba'}


def _seed_obj(oid):
    from ontology.db import session_scope
    from ontology.service import apply_event
    with session_scope() as s:
        apply_event(s, 'ObjectCreated', {'label': oid, 'type': 'Company', 'properties': {}},
                    valid_from='2000-01-01', source='test', actor='pytest', object_id=oid)


@needs_db
def test_propuesta_creada_auto_aplicada_y_aprobada_por_persona(db, clean, monkeypatch):
    import ontology.agents as A
    from ontology.db import session_scope
    from ontology.models import ProposedAction
    for oid in ('PR_A', 'PR_B', 'PR_C'):
        _seed_obj(oid)
    monkeypatch.setattr(A, 'AGENTS', [_StubAgent('PR_A', 0.9)])
    with session_scope() as s:
        out = A.auto_cycle(s)
    assert out['auto_applied'] and out['auto_applied'][0]['object'] == 'PR_A'
    with session_scope() as s:
        pa = s.query(ProposedAction).filter_by(object_id='PR_A').one()
        pid = str(pa.id)
    cr = _decs('proposal.create', proposal_id=pid)
    assert len(cr) == 1 and cr[0]['status'] == 'proposed' and cr[0]['principal_id'] == 'agent:radar@1'
    assert cr[0]['output']['action_type'] == 'AnotarObjeto' and cr[0]['output']['gate_outcome'] in ('pass', 'warn')
    au = _decs('proposal.auto_apply', proposal_id=pid)
    assert len(au) == 1 and au[0]['parent_id'] == cr[0]['id'] and au[0]['principal_id'] == 'system:auto_apply'
    assert any(r['role'] == 'policy' and r['ref_id'] == 'policy.auto_apply@1.0.0' for r in _refs(au[0]['id']))
    act = _q("SELECT kind, status FROM decisions WHERE parent_id = CAST(:i AS uuid)", i=str(au[0]['id']))
    assert act == [{'kind': 'ontology.action', 'status': 'executed'}]
    # baja confianza → queda para la persona: aprobar con PIN deja approval.grant (hija del proposal.create) y la
    # Acción como hija de la aprobación; rechazar otra deja approval.deny
    monkeypatch.setattr(A, 'AGENTS', [_StubAgent('PR_B', 0.2), _StubAgent('PR_C', 0.2)])
    with session_scope() as s:
        A.run_agents(s)
    with session_scope() as s:
        pb = str(s.query(ProposedAction).filter_by(object_id='PR_B').one().id)
        pc = str(s.query(ProposedAction).filter_by(object_id='PR_C').one().id)
    c = _client()
    r = c.post(f'/api/ontology/agents/proposals/{pb}/approve', headers={'X-Trade-Pin': PIN},
               json={'actor': 'Fabri', 'edits': {'texto': 'nota editada'}})
    assert r.status_code == 200, r.get_json()
    g = _decs('approval.grant', proposal_id=pb)
    assert len(g) == 1 and g[0]['status'] == 'approved' and g[0]['principal_id'] == 'op:fabrizio'
    assert g[0]['parent_id'] == _decs('proposal.create', proposal_id=pb)[0]['id']
    assert _blob(g[0]['manifest']['note_blob'])[0] == {'note': {'edits': {'texto': 'nota editada'}}}
    kid = _q("SELECT id FROM decisions WHERE parent_id = CAST(:i AS uuid) AND kind = 'ontology.action'",
             i=str(g[0]['id']))
    assert len(kid) == 1 and r.get_json()['decision_id'] == str(kid[0]['id'])
    r = c.post(f'/api/ontology/agents/proposals/{pc}/reject', headers={'X-Trade-Pin': PIN}, json={'actor': 'Fabri'})
    assert r.status_code == 200
    dn = _decs('approval.deny', proposal_id=pc)
    assert len(dn) == 1 and dn[0]['status'] == 'rejected' and dn[0]['principal_id'] == 'op:fabrizio'


@needs_db
def test_alertas_regla_con_dueno_como_hash_y_disparos_sin_inundar(db, clean, monkeypatch):
    from core import decision_sites as ds
    import ontology.agents as A
    owner = 'mi-nombre-de-dueno-privado'
    c = _client()
    r = c.post('/api/ontology/alerts', json={'owner': owner, 'rule': {'entity': 'Nvidia', 'metric': 'price',
                                                                       'op': '>', 'value': 1}})
    assert r.status_code == 200, r.get_json()
    aid = r.get_json()['alert']['id']
    rule = _decs('alert.rule', alert_id=aid)
    assert len(rule) == 1 and rule[0]['status'] == 'executed' and rule[0]['output']['op'] == 'create'
    assert rule[0]['subject']['owner_hash'] and owner not in json.dumps(rule[0], default=str)
    monkeypatch.setattr(A, 'evaluate_alert', lambda session, rule, values=None: (True, 181.2, 'NVDA = 181.2'))
    for _ in range(3):                                  # tres sondeos seguidos: UNA ficha (FIRE_GAP_S)
        r = c.get('/api/ontology/alerts/check?owner=' + owner)
        assert r.get_json()['count'] == 1
    ds.flush()
    fires = _decs('alert.fire', alert_id=aid)
    assert len(fires) == 1 and fires[0]['status'] == 'fired' and fires[0]['principal_id'] == 'system:alerts'
    assert fires[0]['output']['value'] == 181.2 and fires[0]['output']['threshold'] == 1
    assert owner not in json.dumps(fires[0], default=str)
    r = c.delete(f'/api/ontology/alerts/{aid}')
    assert r.status_code == 200
    rule = _decs('alert.rule', alert_id=aid)
    assert [x['output']['op'] for x in rule] == ['create', 'delete']
    blobs = _q("SELECT body FROM decision_blobs")
    import zlib
    assert all(owner not in zlib.decompress(bytes(b['body'])).decode() for b in blobs if b['body'] is not None)
