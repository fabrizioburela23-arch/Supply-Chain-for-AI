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


# ════════════════════════════════════════════════════════════════════════════
# C8 · Falsadores estructurados {metric, op, threshold, by}: dirección válida + chequeo diario → 'falsified'
# ════════════════════════════════════════════════════════════════════════════

def test_c8_un_falsador_a_favor_de_la_tesis_se_rechaza():
    from research.falsifiers import FalsifierRule, direction_errors
    up = [{'metric': 'price', 'op': '>', 'threshold': 236.54, 'by': '2027-04-15'}]
    down = [{'metric': 'price', 'op': '<', 'threshold': 170, 'by': '2027-04-15'}]
    assert direction_errors('BUY', up) and 'a favor' in direction_errors('BUY', up)[0]
    assert direction_errors('positive', up) and direction_errors('positive', down) == []
    assert direction_errors('SELL', down) and direction_errors('negative', up) == []
    assert direction_errors('HOLD', up) == [] and direction_errors('neutral', up) == []
    r = FalsifierRule(metric='Price', op='below', threshold='170', by='2027-01-05')
    assert r.metric == 'price' and r.op == '<' and r.threshold == 170.0
    with pytest.raises(Exception):
        FalsifierRule(metric='margin', op='<', threshold=1, by='2027-01-01')


def test_c8_el_presidente_no_puede_copiar_un_falsador_que_confirma_la_compra():
    import json

    from research.committee import ChairMemo, chair_checks
    from tests.test_phase3 import _chair_json
    base = json.loads(_chair_json('Decisión del núcleo: BUY', decision='BUY'))
    base['falsifier_rules'] = [{'metric': 'price', 'op': '>', 'threshold': 236.54, 'by': '2027-04-15'}]
    obj = ChairMemo.model_validate(base)
    today = __import__('datetime').date.today()
    errs = chair_checks(obj, ['C1', 'R1', 'Q1'], 'BUY', today, today.replace(year=today.year + 1),
                        [{'title': 'R1', 'excerpt': 'vol 40 %'}], ['fundamental'])
    assert any('a favor de la tesis' in e for e in errs)
    base['falsifier_rules'][0]['op'] = '<'
    ok = chair_checks(ChairMemo.model_validate(base), ['C1', 'R1', 'Q1'], 'BUY', today,
                      today.replace(year=today.year + 1), [{'title': 'R1', 'excerpt': 'vol 40 %'}], ['fundamental'])
    assert not any('a favor' in e for e in ok)


def test_c8_las_claims_de_los_agentes_aceptan_reglas_y_rechazan_la_direccion_mala():
    import json

    from research.schemas import AgentResearchResult, check_refs
    from tests.test_research import _claim, _result
    good = _claim(falsifier_rules=[{'metric': 'excess_vs_spy', 'op': '<', 'threshold': -10, 'by': '2027-03-01'}])
    r = AgentResearchResult.model_validate(json.loads(_result([good])))
    assert r.claims[0].falsifier_rules[0].metric == 'excess_vs_spy' and check_refs(r, ['E2', 'E3', 'E4']) == []
    bad = _claim(falsifier_rules=[{'metric': 'price', 'op': '>', 'threshold': 999, 'by': '2027-03-01'}])
    r2 = AgentResearchResult.model_validate(json.loads(_result([bad])))
    assert any('a favor de la tesis' in e for e in check_refs(r2, ['E2', 'E3', 'E4']))
    assert AgentResearchResult.model_validate(json.loads(_result([_claim()]))).claims[0].falsifier_rules == []


def test_c8_regla_de_precio_se_dispara_con_la_serie():
    from research.falsifiers import check_rules
    from tests.test_phase3 import _series, date
    series = _series(date(2026, 6, 1), date(2026, 7, 1), lambda d: 100.0 if d < date(2026, 6, 20) else 60.0)
    rules = [{'metric': 'price', 'op': '<', 'threshold': 70, 'by': '2026-07-01'}]
    hit = check_rules(rules, '2026-06-01', series, today=date(2026, 6, 25))
    assert hit and hit['date'] == '2026-06-22' and hit['value'] == 60.0          # primer día hábil con 60
    assert check_rules(rules, '2026-06-01', series, today=date(2026, 6, 10)) is None   # todavía no
    expired = [{'metric': 'price', 'op': '<', 'threshold': 70, 'by': '2026-06-15'}]
    assert check_rules(expired, '2026-06-01', series, today=date(2026, 6, 25)) is None  # venció sin dispararse
    bench = _series(date(2026, 6, 1), date(2026, 7, 1), lambda d: 500.0)
    ex = [{'metric': 'excess_vs_spy', 'op': '<', 'threshold': -20, 'by': '2026-07-01'}]
    hit2 = check_rules(ex, '2026-06-01', series, bench, today=date(2026, 6, 25))
    assert hit2 and hit2['value'] == pytest.approx(-40.0)


@needs_db
def test_c8_el_job_diario_falsa_la_claim_y_el_memo_lo_avisa(db):
    from datetime import datetime

    from ontology.db import session_scope
    from research.models import ClaimBaseline, ClaimOutcome, ResearchClaim
    from research.outcomes import evaluate_due, track_record
    from tests.test_phase3 import _mk_claim, _series, date
    crash = {'NVDA': _series(date(2026, 5, 1), date(2027, 7, 1), lambda d: 100.0 if d < date(2026, 6, 20) else 60.0),
             'SPY': _series(date(2026, 5, 1), date(2027, 7, 1), lambda d: 500.0)}
    with session_scope() as s:
        c = _mk_claim(s, 'Nvidia', 'fundamental', 'positive', 'SHORT_TERM', 0.8)
        c.falsifier_rules = [{'metric': 'price', 'op': '<', 'threshold': 70, 'by': '2026-09-01'}]
        cid = c.id
    with session_scope() as s:
        r = evaluate_due(s, now=datetime(2026, 6, 10, 12, tzinfo=UTC), price_fn=lambda sym, since: crash.get(sym))
        assert r['falsified'] == 0 and s.get(ResearchClaim, cid).status == 'active'
    with session_scope() as s:
        r = evaluate_due(s, now=datetime(2026, 6, 25, 12, tzinfo=UTC), price_fn=lambda sym, since: crash.get(sym))
        assert r['falsified'] == 1
        c = s.get(ResearchClaim, cid)
        assert c.status == 'falsified' and c.valid_to is not None
        o = s.query(ClaimOutcome).filter_by(claim_id=cid, checkpoint='falsifier').one()
        assert o.result == 'miss' and o.final and '2026-06-22' in o.reason and 'falsifier triggered' in o.reason_en
        assert s.query(ClaimBaseline).filter_by(claim_id=cid).one().scoreable is False
        tr = track_record(s)
        assert tr['overall']['n_scored'] == 1 and tr['overall']['hits'] == 0      # cuenta como fallo del analista
    with session_scope() as s:        # idempotente y, falsada, ya no se califican sus checkpoints futuros
        r = evaluate_due(s, now=datetime(2026, 7, 15, 12, tzinfo=UTC), price_fn=lambda sym, since: crash.get(sym))
        assert r['falsified'] == 0
        rows = s.query(ClaimOutcome).filter_by(claim_id=cid).all()
        assert sum(1 for o in rows if o.checkpoint == 'falsifier') == 1
        fin = [o for o in rows if o.checkpoint == 'final_20b']
        assert all(o.result == 'n/a' and 'falsada' in (o.reason or '') for o in fin)   # ya no cuenta como acierto/fallo
        tr = track_record(s)
        assert tr['overall']['n_scored'] == 1          # solo el fallo por falsación


# ════════════════════════════════════════════════════════════════════════════
# C9 · Evidencia calculada por Khipus = 'computed' (no fuente independiente); cifras de dinero sin fuente externa → tope 0.5
# ════════════════════════════════════════════════════════════════════════════

def test_c9_evidencia_calculada_no_cuenta_como_fuente_independiente():
    from research.confidence import METHOD, compute_confidence
    assert METHOD == 'conf-v2'
    support = [{'source_type': 'financials', 'reference': 'https://finance.yahoo.com/quote/NVDA/financials', 'reliability': 0.9},
               {'source_type': 'computed', 'reference': 'khipus:ratios:NVDA', 'reliability': 0.85}]
    score, parts = compute_confidence(support, [], 0.8, 1.0)
    assert parts['distinct_sources'] == 1 and score <= 0.6 and parts['method'] == 'conf-v2'
    assert any('una sola referencia' in c for c in parts['caps'])


def test_c9_catalogo_y_grafo_propios_son_una_sola_referencia_interna():
    from research.confidence import compute_confidence
    support = [{'source_type': 'catalog', 'reference': 'khipus:catalog:Nvidia', 'reliability': 0.5},
               {'source_type': 'graph', 'reference': 'khipus:graph:Nvidia', 'reliability': 0.6}]
    score, parts = compute_confidence(support, [], 0.8, 1.0)
    assert parts['distinct_sources'] == 1 and score <= 0.6


def test_c9_cifras_de_dinero_sin_fuente_externa_topan_a_0_5():
    from research.confidence import compute_confidence
    internal = [{'source_type': 'catalog', 'reference': 'khipus:catalog:Nvidia', 'reliability': 0.5},
                {'source_type': 'graph', 'reference': 'khipus:graph:Nvidia', 'reliability': 0.6}]
    score, parts = compute_confidence(internal, [], 0.9, 1.0, statement='backlog de aproximadamente $500B hasta 2027')
    assert score <= 0.5 and any('sin fuente primaria externa' in c for c in parts['caps'])
    external = internal + [{'source_type': 'news', 'reference': 'https://www.reuters.com/x', 'reliability': 0.8,
                            'published_at': '2026-09-20T12:00:00Z'}]
    score2, parts2 = compute_confidence(external, [], 0.9, 1.0, statement='backlog de aproximadamente $500B hasta 2027')
    assert not any('sin fuente primaria externa' in c for c in parts2['caps']) and score2 > 0.5
    # sin cifras de dinero no aplica el tope
    score3, parts3 = compute_confidence(internal, [], 0.9, 1.0, statement='la demanda sigue fuerte')
    assert not any('sin fuente primaria externa' in c for c in parts3['caps'])


def test_c9_ratios_y_pares_se_etiquetan_computed_y_catalogo_grafo_internal():
    from research.context import ContextBuilder
    from tests.test_research import FETCH
    ctx = ContextBuilder(fetchers=FETCH).build('Nvidia', 'fundamental')
    by_ref = {e['reference']: e for e in ctx['evidence'] if e.get('reference')}
    r = next((e for k, e in by_ref.items() if str(k).startswith('khipus:ratios:')), None)
    assert r and r['source_type'] == 'computed' and r['source_kind'] == 'computed'
    cat = next((e for k, e in by_ref.items() if str(k).startswith('khipus:catalog:')), None)
    assert cat and cat['source_type'] == 'catalog' and cat['source_kind'] == 'internal'
    g = next((e for k, e in by_ref.items() if str(k).startswith('khipus:graph:')), None)
    assert g is None or g['source_kind'] == 'internal'


# ════════════════════════════════════════════════════════════════════════════
# C10 · Checkpoints en días hábiles de NYSE + evaluación diaria robusta desde el reloj del servidor
# ════════════════════════════════════════════════════════════════════════════

def test_c10_checkpoints_en_dias_habiles_y_feriados_nyse():
    from datetime import date

    from research.outcomes import build_checkpoints, business_days_after, is_business_day, nyse_holidays
    h = nyse_holidays(2026)
    assert {date(2026, 1, 1), date(2026, 1, 19), date(2026, 2, 16), date(2026, 4, 3), date(2026, 5, 25), date(2026, 6, 19),
            date(2026, 7, 3), date(2026, 9, 7), date(2026, 11, 26), date(2026, 12, 25)} <= h
    assert not is_business_day(date(2026, 6, 19)) and not is_business_day(date(2026, 6, 20)) and is_business_day(date(2026, 6, 22))
    anchor = date(2026, 6, 1)
    assert business_days_after(anchor, 5) == date(2026, 6, 8)
    assert business_days_after(anchor, 20) == date(2026, 6, 30)        # Juneteenth no cuenta
    cps = build_checkpoints('SHORT_TERM', anchor)
    assert [c['label'] for c in cps] == ['interim_5b', 'final_20b'] and cps[1]['due_date'] == '2026-06-30'
    assert cps[0]['unit'] == 'business' and cps[1]['final'] is True
    med = build_checkpoints('MEDIUM_TERM', anchor)
    assert [c['label'] for c in med] == ['interim_20b', 'interim_60b', 'final_180d'] and med[2]['due_date'] == '2026-11-28'
    lng = build_checkpoints('LONG_TERM', anchor)
    assert [c['label'] for c in lng] == ['interim_60b', 'interim_180d', 'final_365d']


def test_c10_la_evaluacion_diaria_no_marca_el_dia_si_falla_y_se_reintenta(monkeypatch):
    from datetime import datetime

    from core import live_caps
    import ontology.db as odb
    import research.outcomes as oc
    monkeypatch.setattr(live_caps, '_OUT_STATE', {'day': None, 'last': None, 'last_at': None, 'error': None,
                                                  'error_at': None, 'runs': 0})
    monkeypatch.setattr(odb, 'ontology_available', lambda: True)

    class _S:
        def __enter__(self):
            return object()

        def __exit__(self, *a):
            return False
    monkeypatch.setattr(odb, 'session_scope', lambda: _S())
    calls = []

    def flaky(session, now=None, **kw):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError('Yahoo caído')
        return {'evaluated': 2}
    monkeypatch.setattr(oc, 'evaluate_due', flaky)
    now = datetime(2026, 10, 5, 8, tzinfo=UTC)
    assert live_caps._daily_outcomes(now=now) is None and live_caps._OUT_STATE['day'] is None
    assert 'RuntimeError' in live_caps._OUT_STATE['error']
    assert live_caps._daily_outcomes(now=now) == {'evaluated': 2}          # segunda pasada SÍ corre
    assert live_caps._OUT_STATE['day'] == '2026-10-05' and live_caps._OUT_STATE['error'] is None
    assert live_caps._daily_outcomes(now=now) is None and len(calls) == 2  # ya corrió hoy


def test_c10_la_evaluacion_corre_aunque_yahoo_no_de_capitalizaciones(monkeypatch):
    from core import live_caps
    seen = []
    monkeypatch.setattr(live_caps, '_daily_outcomes', lambda now=None: seen.append(1))
    monkeypatch.setattr(live_caps, '_symbols_by_id', lambda: {'Nvidia': 'NVDA'})
    live_caps.refresh(fetch=lambda syms: {})
    assert seen == [1]


def test_c10_el_reloj_del_servidor_tiene_las_dos_tareas_registradas():
    import server  # noqa: F401
    from core import scheduler
    st = scheduler.state()
    assert 'research_outcomes_daily' in st and 'research_resume_deferred' in st
    assert st['research_outcomes_daily']['every_s'] == 3600
