"""tests/test_repair_committee.py — Misión de reparación (2026-10-04), P0 · Comité.

Cada test fija un arreglo de REPAIR_LOG.md (C6-C10): fallaba antes del commit y
pasa después. Sin red; los tests con base se saltan sin DATABASE_URL.
"""
import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
UTC = timezone.utc


@pytest.fixture
def db():
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    import research.models  # noqa: F401
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    init_schema()
    yield
    Base.metadata.drop_all(engine)


# ════════════════════════════════════════════════════════════════════════════
# C6 · "No validado" (sin ≥ MIN_N calificaciones por analista) → etiqueta + tamaño a la mitad
# ════════════════════════════════════════════════════════════════════════════

def test_c6_sin_historial_validado_el_tamano_se_reduce_a_la_mitad():
    from research.committee import UNVALIDATED_FACTOR, compute_sizing, mandate_from
    m = mandate_from(None)
    full = compute_sizing('BUY', 37.71, m)                       # default: validado (tests viejos intactos)
    half = compute_sizing('BUY', 37.71, m, validated=False)
    assert UNVALIDATED_FACTOR == 0.5
    assert full['target_weight_pct'] == pytest.approx(5.304, abs=0.01)
    assert half['target_weight_pct'] == pytest.approx(2.652, abs=0.01) and half['capped_by'] == 'unvalidated'
    assert half['unvalidated'] is True and any('mitad' in x for x in half['steps_es']) and any('half' in x for x in half['steps_en'])
    with_eq = compute_sizing('BUY', 40.0, m, equity=100000.0, validated=False)
    assert with_eq['notional'] == 2500 and with_eq['target_weight_pct'] == pytest.approx(2.5)


def test_c6_estado_de_validacion_por_analista():
    from research.committee import validation_status
    from research.outcomes import MIN_N
    none = validation_status(['fundamental', 'news'], {})
    assert none['status'] == 'unvalidated' and none['validated'] is False and none['min_n'] == MIN_N
    assert none['agents']['fundamental'] == {'n': 0, 'hits': 0, 'sufficient': False}
    assert 'no validado' in none['label_es'].lower() and 'not validated' in none['label_en'].lower()
    part = validation_status(['fundamental', 'news'], {'fundamental': {'n': 6, 'hits': 4}})
    assert part['status'] == 'partial' and part['validated'] is False and part['agents']['fundamental']['sufficient']
    ok = validation_status(['fundamental', 'news'], {'fundamental': {'n': 6, 'hits': 4}, 'news': {'n': 5, 'hits': 2}})
    assert ok['status'] == 'validated' and ok['validated'] is True
    assert validation_status([], {})['status'] == 'unvalidated'


# ════════════════════════════════════════════════════════════════════════════
# C7 · Quórum: fundamental obligatorio + 3 de 4 analistas; si no → DATOS INSUFICIENTES (sin deliberar)
# ════════════════════════════════════════════════════════════════════════════

def test_c7_quorum_fundamental_obligatorio_y_tres_de_cuatro():
    from research.committee import decide, quorum_check
    q = quorum_check({'news', 'technical'})
    assert q['ok'] is False and q['missing_required'] == ['fundamental'] and q['n_present'] == 2
    assert q['to_run'] == ['fundamental', 'supply_chain'] and 'fundamental' in q['reason_es'] and q['reason_en']
    assert quorum_check({'fundamental', 'news', 'technical'})['ok'] is True
    assert quorum_check({'fundamental', 'news'})['ok'] is False       # solo 2 de 4
    assert quorum_check({'fundamental', 'news', 'macro', 'crypto'})['ok'] is False   # macro/cripto no cuentan para el 3 de 4
    d, es, en = decide(60, target_w=0.05, quorum=quorum_check({'news', 'technical'}))
    assert d == 'HOLD' and 'quórum' in es and 'quorum' in en
    assert decide(60, target_w=0.05, quorum=quorum_check({'fundamental', 'news', 'technical'}))[0] == 'BUY'
    assert decide(60, investable=False, quorum=quorum_check(set()))[0] == 'AVOID'   # no cotiza manda


@needs_db
def test_c6_memo_lleva_estado_de_validacion_y_tamano_reducido(db):
    from ontology.db import session_scope
    from research.committee import run_committee
    from research.llm import FakeProvider
    from tests.test_phase3 import DEPS, _FakeBroker, _chair_json, _fresh_entity_claims
    broker = _FakeBroker()
    with session_scope() as s:
        _fresh_entity_claims(s, 'Broadcom')
        m = run_committee(s, 'Broadcom', 'pytest', client_id='cli-1', provider=FakeProvider([lambda p: _chair_json(p)]),
                          deps=dict(DEPS, brokerage=broker))
        tv = m['memo']['track_validation']
        assert tv['status'] == 'unvalidated' and tv['validated'] is False and tv['min_n'] == 5
        assert tv['agents']['fundamental']['sufficient'] is False
        assert m['decision'] == 'BUY' and m['memo']['decision_code'] is None
        assert m['sizing']['target_weight_pct'] == pytest.approx(2.5) and m['sizing']['notional'] == 2500
        assert m['sizing']['capped_by'] == 'unvalidated' and m['sizing']['unvalidated'] is True
        assert m['inputs']['track_record']['fundamental']['sufficient'] is False
        assert m['memo']['quorum']['ok'] is True


@needs_db
def test_c7_sin_quorum_el_comite_encarga_a_los_que_faltan_y_si_no_llegan_queda_en_datos_insuficientes(db):
    from ontology.db import session_scope
    from research.committee import run_committee
    from research.llm import FakeProvider
    from research.models import ResearchJob
    from tests.test_phase3 import DEPS, _chair_json, _mk_claim
    now = datetime.now(UTC)
    with session_scope() as s:
        _mk_claim(s, 'Intel', 'news', 'positive', 'MEDIUM_TERM', 0.8, created=now, topic='demand')
        _mk_claim(s, 'Intel', 'news', 'positive', 'LONG_TERM', 0.7, created=now, topic='competition')
        s.flush()
        failing = lambda a: FakeProvider(['no json', 'tampoco', 'ni esto'])     # los analistas encargados no producen nada
        m = run_committee(s, 'Intel', 'pytest', provider=FakeProvider([lambda p: _chair_json(p, agent='news')]),
                          deps=dict(DEPS, research_provider_factory=failing))
        job = s.query(ResearchJob).filter_by(entity_id='Intel').order_by(ResearchJob.created_at.desc()).first()
        assert job is not None and job.agents == ['fundamental', 'technical', 'supply_chain']   # solo los que faltan
        assert m['decision'] == 'HOLD' and m['memo']['decision_code'] == 'INSUFFICIENT_DATA'
        q = m['memo']['quorum']
        assert q['ok'] is False and q['missing_required'] == ['fundamental'] and q['n_present'] == 1
        assert 'quórum' in m['memo']['quant_reason_es'] and 'quorum' in m['memo']['quant_reason_en']
        assert 'INSUFICIENTES' in m['memo']['decision_label_es'] and 'INSUFFICIENT' in m['memo']['decision_label_en']
        assert m['memo']['debate']['ai'] is False and 'quórum' in (m['memo']['debate']['reason_es'] or '')
        absent = [x for x in m['memo']['seats'] if x.get('absent')]
        assert {x['seat'] for x in absent} == {'fundamental', 'technical', 'supply_chain'}
        assert m['sizing']['notional'] == 0 and m['memo']['generated_by'] == 'deterministic'
