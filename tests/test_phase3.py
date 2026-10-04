"""tests/test_phase3.py — PHASE 3 · aprendizaje (resultados + calibración) y
comité de inversión con aprobación humana.

Sin red: precios, perfil en vivo, riesgo, IA y corretaje son simulados.
Los tests con base requieren Postgres (DATABASE_URL).
"""
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')

UTC = timezone.utc


# ── utilidades ───────────────────────────────────────────────────────────────
def _series(start, end, f):
    """Cierres en días hábiles: {iso: f(fecha)}."""
    out, d = {}, start
    while d <= end:
        if d.weekday() < 5:
            out[d.isoformat()] = f(d)
        d += timedelta(days=1)
    return out


ANCHOR = date(2026, 6, 1)           # lunes
CREATED = datetime(2026, 6, 1, 15, 0, tzinfo=UTC)   # 11:00 en Nueva York


def _up(d):          # +0.4 % por día calendario tras la fecha base
    return 100.0 * (1 + 0.004 * max(0, (d - ANCHOR).days))


SERIES = {
    'NVDA': _series(date(2026, 5, 1), date(2027, 7, 1), _up),
    'AMD': _series(date(2026, 5, 1), date(2027, 7, 1), lambda d: 50.0),       # plano
    'SPY': _series(date(2026, 5, 1), date(2027, 7, 1), lambda d: 500.0),      # plano
}


def PRICE_FN(sym, since):
    return SERIES.get(sym)


RISK = {'ok': True, 'vol_ann_pct': 40.0, 'max_drawdown_pct': -30.0, 'max_drawdown_date': '2026-04-01',
        'beta_spy': 1.5, 'var95_1d_pct': 3.2, 'days': 250, 'as_of': '2026-09-29', 'source': 'test'}
LIVE = {'ok': True, 'price': 181.2, 'currency': 'USD', 'market_cap_usd_b': 4420, 'change_pct': 1.0,
        'pe_trailing': 48, 'week52_low': 90, 'week52_high': 190, 'as_of': '2026-09-30T12:00:00Z', 'source': 'test'}
DEPS = {'risk_fn': lambda sym: dict(RISK), 'live_fn': lambda eid, sym: dict(LIVE), 'brokerage': None}


def _chair_json(prompt, extra_risk='', decision=None, agent='fundamental'):
    dec = decision or re.search(r'Decisión del núcleo: (\w+)', prompt).group(1)
    rd = (date.today() + timedelta(days=60)).isoformat()
    return json.dumps({
        'decision': dec,
        'summary_es': 'El comité ve fundamentos sólidos a largo plazo con riesgos de corto plazo (C1, Q1).',
        'summary_en': 'The committee sees solid long-term fundamentals with short-term risks (C1, Q1).',
        'thesis': [{'horizon': 'LONG_TERM', 'thesis_es': 'Crecimiento de ingresos sostenido por centros de datos.',
                    'thesis_en': 'Revenue growth sustained by data centers.', 'refs': ['C1']}],
        'key_risks': [{'risk_es': 'Volatilidad alta del precio.' + extra_risk, 'risk_en': 'High price volatility.',
                       'refs': ['R1']}],
        'dissent': [{'agent_type': agent, 'view_es': 'Un agente ve presión de corto plazo.',
                     'view_en': 'One agent sees short-term pressure.', 'refs': ['C1']}],
        'falsifiers_es': ['Dos trimestres de caída de ingresos.'], 'falsifiers_en': ['Two quarters of falling revenue.'],
        'review_date': rd, 'confidence': 0.55})


# ════════════════════════════════════════════════════════════════════════════
# SIN BASE: lógica pura
# ════════════════════════════════════════════════════════════════════════════
def test_checkpoints_por_horizonte():
    from research.outcomes import build_checkpoints
    assert [c['days'] for c in build_checkpoints('INTRADAY', ANCHOR)] == [1]
    assert [(c['days'], c['final']) for c in build_checkpoints('SHORT_TERM', ANCHOR)] == [(7, False), (30, True)]
    assert [c['days'] for c in build_checkpoints('MEDIUM_TERM', ANCHOR)] == [30, 90, 180]
    lt = build_checkpoints('LONG_TERM', ANCHOR)
    assert [c['days'] for c in lt] == [90, 180, 365] and lt[-1]['label'] == 'final_365d'
    assert lt[-1]['due_date'] == '2027-06-01'
    assert build_checkpoints('STRUCTURAL', ANCHOR) == []


def test_fecha_de_mercado_es_nueva_york():
    from research.outcomes import market_date
    # 01:00 UTC del 30-sep = 21:00 del 29-sep en Nueva York (sesión del 29)
    assert market_date(datetime(2026, 9, 30, 1, 0, tzinfo=UTC)) == date(2026, 9, 29)
    assert market_date(datetime(2026, 9, 30, 15, 0, tzinfo=UTC)) == date(2026, 9, 30)


def test_juicio_por_postura_y_banda():
    from research.outcomes import judge, na_reason_for
    assert judge('positive', 0.05, 0.02) == 'hit' and judge('positive', 0.019, 0.02) == 'miss'
    assert judge('negative', -0.03, 0.02) == 'hit' and judge('negative', 0.01, 0.02) == 'miss'
    assert judge('neutral', 0.015, 0.02) == 'hit' and judge('neutral', -0.021, 0.02) == 'miss'
    assert judge('mixed', 0.5, 0.02) == 'n/a'
    assert 'mixta' in na_reason_for('SHORT_TERM', 'mixed', 'NVDA')
    assert 'no cotiza' in na_reason_for('SHORT_TERM', 'positive', None)
    assert 'ESTRUCTURAL' in na_reason_for('STRUCTURAL', 'positive', 'NVDA')
    assert na_reason_for('LONG_TERM', 'negative', 'NVDA') is None


def _bl(**over):
    b = dict(scoreable=True, na_reason=None, baseline_date=ANCHOR.isoformat(), symbol='NVDA',
             benchmark_symbol='SPY', stance='positive', band=0.02)
    b.update(over)
    return SimpleNamespace(**b)


def test_score_checkpoint_exceso_vs_spy_y_pendientes():
    from research.outcomes import score_checkpoint
    cp = {'label': 'final_30d', 'days': 30, 'due_date': (ANCHOR + timedelta(days=30)).isoformat(), 'final': True}
    today = ANCHOR + timedelta(days=45)
    r = score_checkpoint(_bl(), cp, PRICE_FN, today)
    assert r['result'] == 'hit' and abs(r['asset_return'] - 0.12) < 1e-9 and r['bench_return'] == 0.0
    assert r['base_date'] == '2026-06-01' and r['eval_date'] == '2026-07-01'
    assert 'exceso +12.00 %' in r['reason']
    assert score_checkpoint(_bl(stance='negative'), cp, PRICE_FN, today)['result'] == 'miss'
    assert score_checkpoint(_bl(symbol='AMD', stance='neutral'), cp, PRICE_FN, today)['result'] == 'hit'
    # serie que aún no llega al vencimiento → pendiente (None); si pasó mucho → n/a
    short = {k: v for k, v in SERIES['NVDA'].items() if k < '2026-06-20'}
    fn = lambda s, since: short if s == 'NVDA' else SERIES['SPY']  # noqa: E731
    assert score_checkpoint(_bl(), cp, fn, today) is None
    late = score_checkpoint(_bl(), cp, fn, ANCHOR + timedelta(days=60))
    assert late['result'] == 'n/a' and 'deslistada' in late['reason']
    # proveedor caído → pendiente
    assert score_checkpoint(_bl(), cp, lambda s, since: None, today) is None
    # no calificable → n/a con su motivo, sin pedir precios
    na = score_checkpoint(_bl(scoreable=False, na_reason='postura mixta: x'), cp, None, today)
    assert na['result'] == 'n/a' and 'mixta' in na['reason']


def test_split_no_produce_falso_desplome():
    """Ambos precios salen de la MISMA serie ajustada: un split 10:1 no es −90 %."""
    from research.outcomes import score_checkpoint
    adj = _series(date(2026, 5, 1), date(2026, 8, 1), lambda d: 10.0 * (1 + 0.001 * max(0, (d - ANCHOR).days)))
    cp = {'label': 'final_30d', 'days': 30, 'due_date': '2026-07-01', 'final': True}
    r = score_checkpoint(_bl(stance='negative'), cp, lambda s, since: adj if s == 'NVDA' else SERIES['SPY'],
                         date(2026, 7, 10))
    assert abs(r['asset_return'] - 0.03) < 1e-9 and r['result'] == 'miss'


def test_brier_y_tramos_de_fiabilidad():
    from research.outcomes import stats
    st = stats([(0.8, 1), (0.6, 0), (0.7, 1), (0.1, 0)])
    assert st['n_scored'] == 4 and st['hits'] == 2 and st['hit_rate'] == 0.5
    assert abs(st['brier'] - (0.04 + 0.36 + 0.09 + 0.01) / 4) < 1e-4
    b = {x['bucket']: x for x in st['calibration']}
    assert b['0.6-0.8']['n'] == 2 and b['0.6-0.8']['hit_rate'] == 0.5 and b['0.8-1.0']['n'] == 1
    assert b['0.0-0.2']['mean_conf'] == 0.1 and b['0.4-0.6']['n'] == 0 and b['0.4-0.6']['hit_rate'] is None


def test_confianza_calibrada_encogimiento_bayesiano():
    from research.outcomes import calibrated_confidence, calibration_detail, reliability
    t = {'fundamental': {'n': 10, 'hits': 3, 'buckets': [[0, 0], [0, 0], [0, 0], [10, 3], [0, 0]]}}
    assert calibrated_confidence('fundamental', 0.7, table=t, k=10) == 0.5          # (3+7)/(10+10)
    assert calibrated_confidence('news', 0.7, table=t, k=10) == 0.7                 # sin historia → cruda
    big = {'fundamental': {'n': 1000, 'hits': 300, 'buckets': [[0, 0]] * 3 + [[1000, 300], [0, 0]]}}
    assert abs(calibrated_confidence('fundamental', 0.7, table=big, k=10) - 0.3040) < 1e-3
    d = calibration_detail('fundamental', 0.7, table=t, k=10)
    assert d['sufficient'] and d['n_bucket'] == 10 and d['bucket'] == '0.6-0.8'
    assert not calibration_detail('fundamental', 0.3, table=t, k=10)['sufficient']
    assert reliability(0, 0, k=10) == 0.5 and reliability(10, 10, k=10) == 0.75


def _c(i, agent, stance, hz, conf):
    return {'id': f'c{i}', 'agent_type': agent, 'stance': stance, 'horizon': hz, 'confidence': conf}


def test_conviccion_por_horizonte_y_contradicciones():
    from research.committee import agent_views, conviction_by_horizon
    claims = [_c(1, 'fundamental', 'positive', 'LONG_TERM', 0.7), _c(2, 'supply_chain', 'positive', 'LONG_TERM', 0.7),
              _c(3, 'news', 'positive', 'LONG_TERM', 0.7), _c(4, 'technical', 'negative', 'SHORT_TERM', 0.6)]
    conv, overall = conviction_by_horizon(claims)
    assert conv['LONG_TERM']['score'] == pytest.approx(100 * 2.1 / 3.1, abs=0.1)     # W0 = 1
    assert conv['SHORT_TERM']['score'] == pytest.approx(-37.5, abs=0.1)
    assert overall == pytest.approx((0.2 * -37.5 + 0.35 * 67.74) / 0.55, abs=0.2)
    conv2, overall2 = conviction_by_horizon(claims, contradicted_ids={'c1'})
    assert conv2['LONG_TERM']['score'] < conv['LONG_TERM']['score'] and overall2 < overall
    assert conv2['LONG_TERM']['contra_share'] == pytest.approx(1 / 3, abs=1e-3)
    one, _ = conviction_by_horizon([_c(1, 'fundamental', 'positive', 'LONG_TERM', 0.6)])
    assert 0 < one['LONG_TERM']['score'] < 50            # una sola claim: la duda (W0) frena
    # un agente poco fiable pesa menos
    rel = {'technical': 0.9, 'fundamental': 0.1}
    c3, o3 = conviction_by_horizon([_c(1, 'fundamental', 'positive', 'MEDIUM_TERM', 0.8),
                                    _c(2, 'technical', 'negative', 'MEDIUM_TERM', 0.8)], reliab=lambda a: rel[a])
    assert o3 < 0
    v = agent_views(conv)
    assert v['technical'] < 0 < v['fundamental']


def test_decision_por_umbrales():
    from research.committee import decide
    assert decide(40, target_w=0.05)[0] == 'BUY'
    assert decide(40, target_w=None)[0] == 'HOLD'                    # sin volatilidad no se dimensiona
    assert decide(20, target_w=0.05)[0] == 'HOLD'
    assert decide(-25, target_w=0.05)[0] == 'AVOID'
    assert decide(40, investable=False)[0] == 'AVOID'
    assert decide(90, insufficient=True, target_w=0.05)[0] == 'HOLD'
    assert decide(40, blocked=True, target_w=0.05)[0] == 'AVOID'
    assert decide(40, has_position=True, current_w=0.02, target_w=0.05)[0] == 'ADD'
    assert decide(10, has_position=True, current_w=0.08, target_w=0.05)[0] == 'TRIM'   # sobre-ponderada
    assert decide(-30, has_position=True, current_w=0.03, target_w=0.05)[0] == 'TRIM'
    assert decide(-60, has_position=True, current_w=0.03, target_w=0.05)[0] == 'SELL'
    assert decide(10, has_position=True, current_w=0.05, target_w=0.05)[0] == 'HOLD'


def test_tamano_por_volatilidad_y_topes():
    from research.committee import compute_sizing, mandate_from
    m = mandate_from(None)                                  # 2 % riesgo · tope 10 % · vol mínima 10 %
    s = compute_sizing('BUY', 40.0, m, equity=100000.0, price=200.0)
    assert s['target_weight_pct'] == pytest.approx(5.0) and s['notional'] == 5000 and s['qty_est'] == 25.0
    assert any('2.0 % ÷ volatilidad 40.0 %' in x for x in s['steps_es'])
    s = compute_sizing('BUY', 12.0, m, equity=100000.0)
    assert s['raw_weight_pct'] == pytest.approx(16.667, abs=1e-2) and s['notional'] == 10000 and s['capped_by'] == 'max_position'
    s = compute_sizing('BUY', 5.0, m, equity=100000.0)          # vol mínima 10 % → 20 % → tope 10 %
    assert s['vol_used_pct'] == 10.0 and s['notional'] == 10000
    s = compute_sizing('BUY', 40.0, m, equity=100000.0, buying_power=2000.0)
    assert s['notional'] == 2000 and s['capped_by'] == 'buying_power'
    s = compute_sizing('ADD', 40.0, m, equity=100000.0, current_value=2000.0)
    assert s['notional'] == 3000
    s = compute_sizing('ADD', 12.0, m, equity=100000.0, current_value=9500.0)   # exposición existente
    assert s['notional'] == 500
    s = compute_sizing('TRIM', 40.0, m, equity=100000.0, current_value=8000.0, trim_reason='overweight')
    assert s['notional'] == 3000
    s = compute_sizing('SELL', 40.0, m, equity=100000.0, current_value=8000.0, current_qty=40.0)
    assert s['notional'] == 8000 and s['qty'] == 40.0
    s = compute_sizing('BUY', 40.0, m)                                            # sin cliente
    assert s['reference_only'] and s['per_10k'] == 500 and s['notional'] == 0
    s = compute_sizing('BUY', None, m, equity=100000.0)
    assert s['target_weight_pct'] is None and s['notional'] == 0
    cm = mandate_from({'mandate': {'risk_budget_pct': 1, 'max_position_pct': 4, 'blocked_symbols': ['tsla']}})
    assert cm['risk_budget'] == 0.01 and cm['max_position'] == 0.04 and cm['blocked_symbols'] == ['TSLA']


def test_guardian_del_presidente_rechaza_cifras_decision_y_refs():
    from research.committee import ChairMemo, chair_checks
    prompt = 'Decisión del núcleo: BUY'
    ev = [{'title': 'D1', 'excerpt': 'precio 181.2 USD · capitalización 4420 mil millones USD'},
          {'title': 'Q1', 'excerpt': 'Orden propuesta: BUY $5,000'}]
    today = date.today()
    ok = ChairMemo.model_validate(json.loads(_chair_json(prompt)))
    args = (['C1', 'R1', 'Q1', 'D1'], 'BUY', today + timedelta(days=7), today + timedelta(days=400), ev, ['fundamental'])
    assert chair_checks(ok, *args) == []
    bad = ChairMemo.model_validate(json.loads(_chair_json(prompt, extra_risk=' Vale $999B.')))
    assert any('NO están en la evidencia' in e for e in chair_checks(bad, *args))
    good_money = ChairMemo.model_validate(json.loads(_chair_json(prompt, extra_risk=' Orden de $5,000.')))
    assert chair_checks(good_money, *args) == []
    wrong = ChairMemo.model_validate(json.loads(_chair_json(prompt, decision='SELL')))
    assert any('núcleo cuantitativo' in e for e in chair_checks(wrong, *args))
    hold = ChairMemo.model_validate(json.loads(_chair_json(prompt, decision='HOLD')))
    assert any('chair_note' in e for e in chair_checks(hold, *args))
    refs = ChairMemo.model_validate(json.loads(_chair_json(prompt).replace('"R1"', '"E9"')))
    assert any('refs inexistentes' in e for e in chair_checks(refs, *args))
    ag = ChairMemo.model_validate(json.loads(_chair_json(prompt, agent='oraculo')))
    assert any('agent_type desconocido' in e for e in chair_checks(ag, *args))


# ════════════════════════════════════════════════════════════════════════════
# CON BASE
# ════════════════════════════════════════════════════════════════════════════
@pytest.fixture(scope='module')
def db():
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    import research.models  # noqa: F401
    from research.outcomes import invalidate_cache
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    init_schema()
    invalidate_cache()
    yield
    invalidate_cache()
    Base.metadata.drop_all(engine)


def _mk_claim(s, entity, agent, stance, horizon, conf, created=CREATED, status='active', topic='revenue_growth'):
    from research.models import ResearchClaim
    c = ResearchClaim(agent_id=f'{agent}_agent', agent_type=agent, agent_version='1.0', subject_entity_id=entity,
                      predicate='TEST_' + stance.upper(), claim_type='forecast', topic=topic, stance=stance,
                      statement_es=f'Conclusión {stance} de {agent} sobre {entity} ({horizon}).',
                      statement_en=f'{stance} conclusion by {agent} on {entity} ({horizon}).',
                      reasoning_summary='Prueba.', horizon=horizon, depth='STANDARD', valid_from=created,
                      confidence=conf, confidence_components={'method': 'conf-v1'}, affected_entity_ids=[],
                      falsifiers=[f'Falsador de {agent}'], status=status, created_at=created)
    s.add(c)
    s.flush()
    return c


@needs_db
def test_foto_de_partida_al_persistir_la_claim(db):
    """El runner guarda la foto (precio en vivo + SPY + checkpoints) y la calibración."""
    from ontology.db import session_scope
    from research.llm import FakeProvider
    from research.models import ClaimBaseline, ResearchClaim
    from research.runner import create_job, execute_job
    from tests.test_research import FETCH, _claim, _result
    with session_scope() as s:
        job, _ = create_job(s, 'Nvidia', agents=['fundamental'], requested_by='pytest', force=True)
        execute_job(s, job, provider_factory=lambda a: FakeProvider([_result([_claim()])]), fetchers=FETCH)
        c = s.query(ResearchClaim).filter_by(job_id=job.id).one()
        b = s.query(ClaimBaseline).filter_by(claim_id=c.id).one()
        assert b.symbol == 'NVDA' and b.scoreable and b.baseline_price == 181.2 and b.benchmark_price == 181.2
        assert b.baseline_source.startswith('live:') and b.horizon == 'LONG_TERM'
        assert [x['days'] for x in b.checkpoints] == [90, 180, 365] and b.confidence == c.confidence
        cal = c.confidence_components['calibration']
        assert cal['raw'] == pytest.approx(c.confidence, abs=1e-3) and cal['sufficient'] is False
        assert c.confidence_components['method'] == 'conf-v2'     # C9


@needs_db
def test_evaluacion_con_precios_reales_idempotente_y_na(db):
    from ontology.db import session_scope
    from research.models import ClaimBaseline, ClaimOutcome
    from research.outcomes import evaluate_due, outcomes_for_claim, track_record
    with session_scope() as s:
        pos = _mk_claim(s, 'Nvidia', 'fundamental', 'positive', 'SHORT_TERM', 0.8)
        neg = _mk_claim(s, 'Nvidia', 'technical', 'negative', 'SHORT_TERM', 0.7, status='superseded')
        neu = _mk_claim(s, 'AMD', 'news', 'neutral', 'SHORT_TERM', 0.5)
        mix = _mk_claim(s, 'Nvidia', 'news', 'mixed', 'SHORT_TERM', 0.6)
        unl = _mk_claim(s, 'IBMQuantum', 'supply_chain', 'positive', 'SHORT_TERM', 0.6)
        stc = _mk_claim(s, 'Nvidia', 'supply_chain', 'positive', 'STRUCTURAL', 0.6)
        ids = dict(pos=pos.id, neg=neg.id, neu=neu.id, mix=mix.id, unl=unl.id, stc=stc.id)
    with session_scope() as s:
        # antes de vencer: todo pendiente (y crea las fotos de partida por backfill)
        r0 = evaluate_due(s, now=datetime(2026, 6, 5, 12, tzinfo=UTC), price_fn=PRICE_FN)
        assert r0['evaluated'] == 0 and r0['pending'] >= 10 and r0['baselines_created'] >= 6
        assert s.query(ClaimBaseline).filter_by(claim_id=ids['stc']).one().checkpoints == []
    with session_scope() as s:
        r1 = evaluate_due(s, now=datetime(2026, 7, 15, 12, tzinfo=UTC), price_fn=PRICE_FN)
        assert r1['evaluated'] == 10                  # 5 claims × (7d + 30d)
        res = {(o.claim_id, o.checkpoint): o for o in s.query(ClaimOutcome).all()}
        assert res[(ids['pos'], 'interim_7d')].result == 'hit'          # +2.8 % > banda
        assert res[(ids['pos'], 'final_30d')].result == 'hit' and res[(ids['pos'], 'final_30d')].final
        assert res[(ids['neg'], 'final_30d')].result == 'miss'          # superada: igual se califica
        assert res[(ids['neg'], 'final_30d')].claim_status == 'superseded'
        assert res[(ids['neu'], 'final_30d')].result == 'hit'           # AMD plano vs SPY plano
        assert res[(ids['mix'], 'final_30d')].result == 'n/a' and 'mixta' in res[(ids['mix'], 'final_30d')].reason
        assert res[(ids['unl'], 'final_30d')].result == 'n/a' and 'no cotiza' in res[(ids['unl'], 'final_30d')].reason
        o = res[(ids['pos'], 'final_30d')]
        assert o.base_price == 100.0 and o.eval_price == pytest.approx(112.0) and o.excess_return == pytest.approx(0.12)
        assert outcomes_for_claim(s, ids['pos'])[-1]['result'] == 'hit'
    with session_scope() as s:
        r2 = evaluate_due(s, now=datetime(2026, 7, 16, 12, tzinfo=UTC), price_fn=PRICE_FN)
        assert r2['evaluated'] == 0                   # idempotente
        assert s.query(ClaimOutcome).count() == 10
        tr = track_record(s)
        ag = {a['agent_type']: a for a in tr['agents']}
        assert ag['fundamental']['n_scored'] == 1 and ag['fundamental']['hits'] == 1
        assert ag['fundamental']['brier'] == pytest.approx(0.04, abs=1e-4)
        assert ag['technical']['hit_rate'] == 0.0 and ag['technical']['brier'] == pytest.approx(0.49, abs=1e-4)
        assert ag['news']['n_na'] == 2 and ag['news']['n_scored'] == 1
        assert ag['fundamental']['interim']['n_scored'] == 1
        assert tr['overall']['n_scored'] == 3 and not tr['overall']['sufficient']
        assert ag['fundamental']['reliability'] == pytest.approx((1 + 10 * 0.5) / 11, abs=1e-3)
        from research.models import CalibrationSnapshot
        assert s.query(CalibrationSnapshot).filter(CalibrationSnapshot.agent_type.is_(None)).count() >= 1


def _fresh_entity_claims(s, entity):
    """Claims ACTIVAS de hoy para el comité (sin tocar las de otras pruebas)."""
    from research.models import ClaimRelation
    now = datetime.now(UTC)
    a = _mk_claim(s, entity, 'fundamental', 'positive', 'LONG_TERM', 0.8, created=now)
    b = _mk_claim(s, entity, 'supply_chain', 'positive', 'LONG_TERM', 0.75, created=now, topic='supply_chain')
    e = _mk_claim(s, entity, 'macro', 'positive', 'LONG_TERM', 0.7, created=now, topic='macro')
    c = _mk_claim(s, entity, 'news', 'positive', 'MEDIUM_TERM', 0.7, created=now, topic='demand')
    d = _mk_claim(s, entity, 'technical', 'negative', 'SHORT_TERM', 0.6, created=now, topic='momentum')
    h = _mk_claim(s, entity, 'news', 'positive', 'SHORT_TERM', 0.5, created=now, topic='sentiment')
    s.add(ClaimRelation(claim_a=d.id, claim_b=h.id, reason='prueba de contradicción'))
    s.flush()
    return [a, b, e, c, d, h]


class _FakeBroker:
    def __init__(self, position=None, equity=100000.0):
        self.calls = []
        self.position = position
        self.equity = equity

    def available(self):
        return True

    def get_client(self, session, client_id):
        return {'id': client_id, 'name': 'Cliente Demo', 'mode': 'paper',
                'mandate': {'risk_budget_pct': 2, 'max_position_pct': 10}} if client_id == 'cli-1' else None

    def account_snapshot(self, session, client_id):
        pos = [self.position] if self.position else []
        return {'ok': True, 'client': {'id': client_id},
                'account': {'equity': self.equity, 'cash': 50000.0, 'buying_power': 50000.0, 'currency': 'USD',
                            'paper': True}, 'positions': pos}

    def preview_order(self, session, client_id, symbol, side, notional=None, qty=None, order_type='market',
                      limit_price=None, source='ui', requested_by='', proposal_id=None, rationale=None):
        self.calls.append(dict(client_id=client_id, symbol=symbol, side=side, notional=notional, qty=qty,
                               source=source, requested_by=requested_by, proposal_id=proposal_id))
        return {'ok': True, 'preview_id': 'pv-1', 'client_id': client_id, 'symbol': symbol, 'side': side,
                'notional': notional, 'qty': qty, 'blocked': False, 'requires_human_approval': True,
                'status': 'pending_approval', 'checks': [], 'summary_es': 'x', 'summary_en': 'x'}

    def list_clients(self, session):
        return [{'id': 'cli-1', 'name': 'Cliente Demo', 'mode': 'paper', 'api_secret': 'NO'}]

    def reject_preview(self, session, preview_id, actor, reason=''):
        self.calls.append(dict(kind='reject_preview', preview_id=preview_id, actor=actor, reason=reason))
        return {'ok': True, 'status': 'rejected', 'order': {'id': preview_id, 'status': 'rejected'}}


@needs_db
def test_comite_con_presidente_ia_y_tamano_determinista(db):
    from ontology.db import session_scope
    from research.committee import run_committee
    from research.llm import FakeProvider
    from research.models import AgentRun, CommitteeMemo
    broker = _FakeBroker()
    with session_scope() as s:
        _fresh_entity_claims(s, 'Broadcom')
        prov = FakeProvider([lambda p: _chair_json(p)])
        m = run_committee(s, 'Broadcom', 'pytest', client_id='cli-1', provider=prov, deps=dict(DEPS, brokerage=broker))
        assert m['status'] == 'proposed' and m['ai_used'] and m['memo']['generated_by'] == 'ai'
        assert m['decision'] == m['quant_decision'] == 'BUY' and m['overall_conviction'] >= 35
        # C6 (misión de reparación): sin historial validado el objetivo es la MITAD (2 % → 1 % ÷ 40 % = 2.5 %)
        assert m['sizing']['target_weight_pct'] == pytest.approx(2.5) and m['sizing']['notional'] == 2500
        assert m['sizing']['capped_by'] == 'unvalidated' and m['memo']['track_validation']['status'] == 'unvalidated'
        assert m['inputs']['client']['equity'] == 100000.0 and m['inputs']['mandate']['risk_budget'] == 0.02
        assert 'aprobación humana' in m['disclaimer_es'] and 'human approval' in m['disclaimer_en']
        assert m['conviction']['SHORT_TERM']['contra_share'] == 1.0      # contradicción: penalización
        assert m['conviction']['SHORT_TERM']['penalty'] == 0.5 and m['conviction']['LONG_TERM']['contra_share'] == 0
        assert 'Q1' in m['inputs']['valid_refs'] and 'M1' in m['inputs']['valid_refs']
        assert 'BUY $2,500' in m['inputs']['package']
        run = s.query(AgentRun).filter_by(agent_type='committee').order_by(AgentRun.started_at.desc()).first()
        assert run.status == 'done' and run.entity_id == 'Broadcom'
        assert s.get(CommitteeMemo, m['memo_id']).audit[-1]['action'] == 'proposed'


@needs_db
def test_comite_guardian_de_cifras_repara_y_sin_ia_cae_a_determinista(db):
    from ontology.db import session_scope
    from research.committee import run_committee
    from research.llm import FakeProvider, LLMProvider
    with session_scope() as s:
        _fresh_entity_claims(s, 'Micron')
        prov = FakeProvider([lambda p: _chair_json(p, extra_risk=' Micron vale $7.3T.'), lambda p: _chair_json(p)])
        m = run_committee(s, 'Micron', 'pytest', provider=prov, deps=DEPS)
        assert m['ai_used'] and m['validation']['repaired'] and 'NO están en la evidencia' in prov.calls[1]
        assert '$7.3T' not in json.dumps(m['memo'])
        assert m['sizing']['reference_only'] and m['sizing']['per_10k'] == 250     # C6: mitad sin historial validado
        # el modelo insiste con la cifra inventada → memo determinista "sin IA"
        bad = FakeProvider([lambda p: _chair_json(p, extra_risk=' vale $7.3T'), lambda p: _chair_json(p, extra_risk=' vale $7.3T')])
        m2 = run_committee(s, 'Micron', 'pytest', provider=bad, deps=DEPS)
        assert not m2['ai_used'] and m2['memo']['generated_by'] == 'deterministic'
        assert 'determinista' in m2['memo']['ai_error'] and m2['decision'] == m2['quant_decision']
        assert m2['memo']['thesis'] and m2['memo']['key_risks'] and m2['memo']['falsifiers_es']
        assert any(d['agent_type'] == 'technical' for d in m2['memo']['dissent'])     # disiente del alza

        class Off(LLMProvider):
            def available(self):
                return False
        m3 = run_committee(s, 'Micron', 'pytest', provider=Off(), deps=DEPS)
        assert not m3['ai_used'] and 'proveedor' in m3['memo']['ai_error']
        # sin conclusiones: no se consulta a la IA; HOLD por evidencia insuficiente
        m4 = run_committee(s, 'Qualcomm', 'pytest', provider=FakeProvider([]), deps=DEPS)
        assert m4['decision'] == 'HOLD' and 'Investigación IA' in m4['memo']['ai_error']
        # no cotiza → AVOID
        _mk_claim(s, 'IBMQuantum', 'fundamental', 'positive', 'LONG_TERM', 0.8, created=datetime.now(UTC))
        _mk_claim(s, 'IBMQuantum', 'news', 'positive', 'LONG_TERM', 0.8, created=datetime.now(UTC))
        m5 = run_committee(s, 'IBMQuantum', 'pytest', provider=Off(), deps=DEPS)
        assert m5['decision'] == 'AVOID' and m5['symbol'] is None


@needs_db
def test_aprobar_crea_preview_en_corretaje_y_rechazar(db):
    from ontology.db import session_scope
    from research.committee import approve_memo, reject_memo, run_committee
    from research.llm import LLMProvider
    from research.models import CommitteeMemo

    class Off(LLMProvider):
        def available(self):
            return False
    broker = _FakeBroker(position={'symbol': 'AVGO', 'qty': 10, 'avg_entry_price': 150, 'market_value': 2000.0,
                                   'unrealized_pl': 0, 'unrealized_plpc': 0})
    with session_scope() as s:
        _fresh_entity_claims(s, 'Broadcom')
        m = run_committee(s, 'Broadcom', 'pytest', client_id='cli-1', provider=Off(), deps=dict(DEPS, brokerage=broker))
        assert m['decision'] == 'ADD' and m['sizing']['notional'] == 500         # C6: objetivo 2.5k − 2k actuales
        out = approve_memo(s, m['memo_id'], 'fabrizio', brokerage=broker)
        assert out['ok'] and out['memo']['status'] == 'approved' and out['memo']['preview_id'] == 'pv-1'
        call = broker.calls[-1]
        assert call['source'] == 'committee' and call['proposal_id'] == m['memo_id'] and call['side'] == 'buy'
        assert call['notional'] == 500 and call['symbol'] == 'AVGO' and call['requested_by'] == 'fabrizio'
        again = approve_memo(s, m['memo_id'], 'fabrizio', brokerage=broker)
        assert not again['ok'] and again['code'] == 'bad_status'
        # sin cliente: aprobación registrada, ninguna orden
        m2 = run_committee(s, 'Broadcom', 'pytest', provider=Off(), deps=DEPS)
        out2 = approve_memo(s, m2['memo_id'], 'fabrizio', brokerage=broker)
        assert out2['ok'] and out2['preview'] is None and len(broker.calls) == 1
        # rechazo
        m3 = run_committee(s, 'Broadcom', 'pytest', provider=Off(), deps=DEPS)
        rj = reject_memo(s, m3['memo_id'], 'fabrizio', reason='no me convence')
        assert rj['ok'] and rj['memo']['status'] == 'rejected' and rj['memo']['decision_note'] == 'no me convence'
        # vencido → no se aprueba
        m4 = run_committee(s, 'Broadcom', 'pytest', provider=Off(), deps=DEPS)
        s.get(CommitteeMemo, m4['memo_id']).created_at = datetime.now(UTC) - timedelta(hours=100)
        s.flush()
        ex = approve_memo(s, m4['memo_id'], 'fabrizio', brokerage=broker)
        assert not ex['ok'] and ex['code'] == 'expired'
        # sin módulo de corretaje: NO se aprueba (sigue propuesto) y se dice en es/en
        m5 = run_committee(s, 'Broadcom', 'pytest', client_id='cli-1', provider=Off(), deps=dict(DEPS, brokerage=broker))
        import research.committee as rc
        orig = rc.brokerage_service
        rc.brokerage_service = lambda: None
        try:
            out5 = approve_memo(s, m5['memo_id'], 'fabrizio')
        finally:
            rc.brokerage_service = orig
        assert not out5['ok'] and out5['code'] == 'brokerage_unavailable' and 'corretaje' in out5['error']
        assert 'brokerage' in out5['error_en'] and out5['memo']['status'] == 'proposed'


@needs_db
def test_api_del_comite(db, monkeypatch):
    import research.committee as rc
    import research.llm as rl
    import research.outcomes as ro
    import server
    from ontology.db import session_scope
    server.app.config['TESTING'] = True
    c = server.app.test_client()
    monkeypatch.setattr(rc, '_default_risk', DEPS['risk_fn'])
    monkeypatch.setattr(rc, '_default_live', DEPS['live_fn'])
    monkeypatch.setattr(rl, 'route_for', lambda a: [rl.FakeProvider([lambda p: _chair_json(p)])])
    broker = _FakeBroker()
    monkeypatch.setattr(rc, 'brokerage_service', lambda: broker)
    monkeypatch.setenv('TRADE_PIN', '4321')
    PIN = {'X-Trade-Pin': '4321'}
    with session_scope() as s:
        _fresh_entity_claims(s, 'ASML')
    assert c.post('/api/committee/run', json={'entity': 'ASML'}).status_code == 400          # actor obligatorio
    assert c.post('/api/committee/run', json={'entity': 'zzqqxx', 'actor': 't'}).status_code == 404
    # con cliente sin PIN → 401
    assert c.post('/api/committee/run', json={'entity': 'ASML', 'actor': 't', 'client_id': 'cli-1'}).status_code == 401
    r = c.post('/api/committee/run', json={'entity': 'ASML', 'actor': 'pytest', 'client_id': 'cli-1', 'sync': True},
               headers=PIN)
    assert r.status_code == 200, r.get_json()
    m = r.get_json()
    assert m['ai_used'] and m['decision'] == 'BUY' and m['sizing']['notional'] == 2500      # C6: mitad
    mid = m['memo_id']
    red = c.get(f'/api/committee/memo/{mid}').get_json()                 # sin PIN: montos ocultos
    assert red['redacted'] and red['sizing']['notional'] is None and 'client' not in red['inputs']
    assert 'package' not in red['inputs'] and not any('$' in x for x in red['sizing']['steps_es'])
    assert 'mandate' not in red['inputs'] and red['client_mode'] == {'mode': 'paper', 'paper': True}
    full = c.get(f'/api/committee/memo/{mid}', headers=PIN).get_json()
    assert not full['redacted'] and full['sizing']['notional'] == 2500
    ent = c.get('/api/committee/entity/ASML').get_json()
    assert ent['entity_id'] == 'ASML' and ent['latest']['memo_id'] == mid and ent['history']
    assert c.post(f'/api/committee/memo/{mid}/approve', json={'actor': 'f'}).status_code == 401
    monkeypatch.delenv('TRADE_PIN')
    assert c.post(f'/api/committee/memo/{mid}/approve', json={'actor': 'f'}, headers=PIN).status_code == 403
    monkeypatch.setenv('TRADE_PIN', '4321')
    ap = c.post(f'/api/committee/memo/{mid}/approve', json={'actor': 'fabrizio'}, headers=PIN)
    assert ap.status_code == 200 and ap.get_json()['preview']['preview_id'] == 'pv-1'
    assert broker.calls[-1]['source'] == 'committee'
    assert c.post(f'/api/committee/memo/{mid}/reject', json={'actor': 'f'}, headers=PIN).status_code == 200
    assert broker.calls[-1]['kind'] == 'reject_preview' and broker.calls[-1]['preview_id'] == 'pv-1'   # orden retirada
    assert c.post(f'/api/committee/memo/{mid}/reject', json={'actor': 'f'}, headers=PIN).status_code == 409
    # asíncrono: 202 + la fila queda consultable
    r2 = c.post('/api/committee/run', json={'entity': 'ASML', 'actor': 'pytest'})
    assert r2.status_code == 202 and r2.get_json()['status'] == 'running'
    import time
    st = None
    for _ in range(100):                     # el hilo termina (proveedor falso: instantáneo)
        st = c.get('/api/committee/memo/' + r2.get_json()['memo_id']).get_json()['status']
        if st != 'running':
            break
        time.sleep(0.05)
    assert st == 'proposed'
    tr = c.get('/api/committee/track-record').get_json()
    assert 'agents' in tr and tr['k'] == 10 and tr['min_n'] == 5
    cal = c.get('/api/committee/calibration').get_json()
    assert 'table' in cal and cal['buckets'][0] == [0.0, 0.2]
    monkeypatch.setattr(ro, 'default_price_fn', PRICE_FN)
    assert c.post('/api/committee/outcomes/evaluate').status_code == 401
    ev = c.post('/api/committee/outcomes/evaluate', headers=PIN)
    assert ev.status_code == 200 and 'evaluated' in ev.get_json()
    assert c.get('/api/committee/outcomes/recent?limit=5').status_code == 200
    cl = c.get('/api/committee/clients', headers=PIN).get_json()
    assert cl['available'] and cl['clients'][0]['name'] == 'Cliente Demo' and 'api_secret' not in cl['clients'][0]
    import research.committee_api as api
    monkeypatch.setattr(api, 'ontology_available', lambda: False)
    assert c.get('/api/committee/track-record').status_code == 503
    assert c.post('/api/committee/run', json={'entity': 'ASML', 'actor': 't'}).status_code == 503


# ════════════════════════════════════════════════════════════════════════════
# CORRECCIONES DE LA REVISIÓN (Phase 3 · fixer)
# ════════════════════════════════════════════════════════════════════════════
def _ranged(series_by_sym):
    """Como Yahoo: devuelve SOLO la ventana pedida (desde `since`)."""
    def fn(sym, since):
        ser = series_by_sym.get(sym)
        if ser is None:
            return None
        return {k: v for k, v in ser.items() if k >= since.isoformat()}
    return fn


def test_serie_que_no_llega_al_inicio_queda_pendiente_no_na():
    """Una ventana corta del proveedor no es un n/a definitivo: se reintenta."""
    from research.outcomes import score_checkpoint
    cp = {'label': 'final_30d', 'days': 30, 'due_date': '2026-07-01', 'final': True}
    short = {k: v for k, v in SERIES['NVDA'].items() if k >= '2026-06-15'}
    fn = lambda s, since: short if s == 'NVDA' else SERIES['SPY']  # noqa: E731
    assert score_checkpoint(_bl(), cp, fn, date(2026, 7, 10)) is None
    late = score_checkpoint(_bl(), cp, fn, date(2026, 8, 1))
    assert late['result'] == 'n/a' and 'partida' in late['reason'] and late['reason_en']


def test_calificacion_bilingue_y_moneda_local():
    from research.outcomes import is_us_listing, na_reasons, score_checkpoint
    cp = {'label': 'final_30d', 'days': 30, 'due_date': '2026-07-01', 'final': True}
    r = score_checkpoint(_bl(), cp, PRICE_FN, date(2026, 7, 10))
    assert 'excess +12.00%' in r['reason_en'] and '→ hit' in r['reason_en']
    loc = score_checkpoint(_bl(symbol='9984.T'), cp, lambda s, since: SERIES['NVDA'] if s == '9984.T' else SERIES['SPY'],
                           date(2026, 7, 10))
    assert 'moneda local' in loc['reason'] and 'local-currency' in loc['reason_en']
    assert is_us_listing('NVDA') and is_us_listing('BRK.B') and is_us_listing('MOG-A')
    assert not any(is_us_listing(x) for x in ('9984.T', '2330.TW', 'BA.L', '005930.KS', 'UCU.V', None))
    es, en = na_reasons('SHORT_TERM', 'mixed', 'NVDA')
    assert 'mixta' in es and 'mixed' in en


def test_tamano_respeta_limites_del_corretaje_y_ventas_sin_volatilidad():
    from research.committee import _downgrade_reason, compute_sizing, mandate_from
    client = {'mandate': {'max_position_pct': 20, 'max_order_usd': 5000, 'max_daily_usd': 15000}}
    m = mandate_from(client)
    assert m['max_order_usd'] == 5000 and m['max_daily_usd'] == 15000 and m['max_position'] == 0.2
    s = compute_sizing('BUY', 30.0, m, equity=100000.0, buying_power=100000.0)    # 6.67 % → $6,666
    assert s['notional'] == 5000 and s['capped_by'] == 'max_order'
    assert any('máximo por orden' in x for x in s['steps_es']) and any('per-order' in x for x in s['steps_en'])
    m['daily_remaining_usd'] = 1800.0
    s = compute_sizing('BUY', 30.0, m, equity=100000.0, buying_power=100000.0)
    assert s['notional'] == 1800 and s['capped_by'] == 'daily_limit'
    m['daily_remaining_usd'] = 0.0
    s = compute_sizing('BUY', 30.0, m, equity=100000.0)
    assert s['notional'] == 0 and 'límite diario' in _downgrade_reason(s, 30.0)[0]
    # venta mayor que el máximo por orden → venta PARCIAL por monto (sin qty)
    m = mandate_from(client)
    s = compute_sizing('SELL', 30.0, m, equity=100000.0, current_value=8000.0, current_qty=40.0)
    assert s['notional'] == 5000 and s['qty'] is None and s['partial']
    # SIN volatilidad: vender / reducir por convicción igual se dimensiona con la posición
    m0 = mandate_from(None)
    s = compute_sizing('SELL', None, m0, equity=100000.0, current_value=8000.0, current_qty=40.0)
    assert s['notional'] == 8000 and s['qty'] == 40.0 and s['target_weight_pct'] is None
    s = compute_sizing('TRIM', None, m0, equity=100000.0, current_value=8000.0, trim_reason='conviction')
    assert s['notional'] == 4000
    s = compute_sizing('BUY', None, m0, equity=100000.0)
    assert s['notional'] == 0 and 'volatilidad' in _downgrade_reason(s, None)[0]
    # ≈ acciones solo con precio en dólares
    assert compute_sizing('BUY', 40.0, m0, equity=100000.0, price=6000.0, price_is_usd=False)['qty_est'] is None
    assert compute_sizing('BUY', 40.0, m0, equity=100000.0, price=200.0)['qty_est'] == 25.0


def test_decision_no_operable_en_alpaca_y_simbolo_alpaca():
    from research.committee import alpaca_symbol, decide
    d, es, en = decide(60, target_w=0.05, tradable=False)
    assert d == 'HOLD' and 'Alpaca' in es and 'Alpaca' in en
    assert decide(-40, target_w=0.05, tradable=False)[0] == 'AVOID'          # la vista negativa se conserva
    assert alpaca_symbol('MOG-A') == 'MOG.A' and alpaca_symbol('NVDA') == 'NVDA'


def test_redaccion_cubre_formatos_de_dinero():
    from research.committee import _scrub
    txt = _scrub('patrimonio USD 100,000 · 1.234 USD · 100.000 dólares · US$5,000.00 · $7.3T · 5 mil millones USD')
    assert not re.search(r'\d', txt.replace('$•••', '')), txt


@needs_db
def test_cache_de_precios_usa_la_ventana_mas_antigua_del_lote(db):
    """Regresión: un checkpoint corto procesado ANTES no debe dejar a SPY con una
    ventana de 1 año y el final de 365 días como n/a para siempre."""
    from ontology.db import session_scope
    from research.models import ClaimOutcome
    from research.outcomes import evaluate_due
    a0 = date(2026, 7, 8)
    ser = {'NVDA': _series(date(2026, 6, 1), date(2027, 7, 20), lambda d: 100.0 * (1 + 0.001 * max(0, (d - a0).days))),
           'AMD': _series(date(2026, 6, 1), date(2027, 7, 20), lambda d: 50.0),
           'SPY': _series(date(2026, 6, 1), date(2027, 7, 20), lambda d: 500.0)}
    fn = _ranged(ser)
    with session_scope() as s:
        lt = _mk_claim(s, 'Nvidia', 'macro', 'positive', 'LONG_TERM', 0.7,
                       created=datetime(2026, 7, 8, 15, 0, tzinfo=UTC), topic='lt_cache')
        lt_id = lt.id
    with session_scope() as s:            # los intermedios (90/180 d) se califican en una corrida anterior
        evaluate_due(s, now=datetime(2027, 1, 10, 12, tzinfo=UTC), price_fn=fn)
        assert s.query(ClaimOutcome).filter_by(claim_id=lt_id, checkpoint='interim_180d').one().result == 'hit'
        intraday = _mk_claim(s, 'AMD', 'technical', 'neutral', 'INTRADAY', 0.6,
                             created=datetime(2027, 7, 6, 15, 0, tzinfo=UTC), topic='intraday_cache')
        in_id = intraday.id
    with session_scope() as s:            # mismo lote: INTRADAY (vence antes) + final de 365 días
        evaluate_due(s, now=datetime(2027, 7, 10, 12, tzinfo=UTC), price_fn=fn)
        fin = s.query(ClaimOutcome).filter_by(claim_id=lt_id, checkpoint='final_365d').one()
        assert fin.result == 'hit', fin.reason
        assert fin.base_date == '2026-07-08' and fin.reason_en and 'excess' in fin.reason_en
        assert s.query(ClaimOutcome).filter_by(claim_id=in_id).one().result == 'hit'


@needs_db
def test_no_se_califica_con_la_barra_de_hoy_en_curso(db):
    from ontology.db import session_scope
    from research.models import ClaimOutcome
    from research.outcomes import evaluate_due
    # vence el sábado 2027-08-07; el primer cierre posterior es el del lunes 09 (hoy)
    ser = {'ORCL': _series(date(2027, 7, 1), date(2027, 8, 9), lambda d: 100.0 if d < date(2027, 8, 9) else 110.0),
           'SPY': _series(date(2027, 7, 1), date(2027, 8, 9), lambda d: 500.0)}
    with session_scope() as s:
        c = _mk_claim(s, 'Oracle', 'news', 'positive', 'INTRADAY', 0.6,
                      created=datetime(2027, 8, 6, 15, 0, tzinfo=UTC), topic='live_bar')
        cid = c.id
    with session_scope() as s:            # lunes 15:00 en Nueva York: sesión abierta → pendiente
        evaluate_due(s, now=datetime(2027, 8, 9, 19, 0, tzinfo=UTC), price_fn=_ranged(ser))
        assert s.query(ClaimOutcome).filter_by(claim_id=cid).count() == 0
    with session_scope() as s:            # lunes 17:30 en Nueva York: ya es un cierre
        evaluate_due(s, now=datetime(2027, 8, 9, 21, 30, tzinfo=UTC), price_fn=_ranged(ser))
        o = s.query(ClaimOutcome).filter_by(claim_id=cid).one()
        assert o.eval_date == '2027-08-09' and o.result == 'hit'


@needs_db
def test_runner_sobrevive_a_un_fallo_de_la_tabla_de_calibracion(db, monkeypatch):
    """La consulta de calibración va en SAVEPOINT: un error de Postgres no
    aborta la transacción del job (antes: 'current transaction is aborted')."""
    from sqlalchemy import text
    import research.outcomes as ro
    from ontology.db import session_scope
    from research.llm import FakeProvider
    from research.models import ResearchClaim
    from research.runner import create_job, execute_job
    from tests.test_research import FETCH, _claim, _result

    def broken(session=None, force=False):
        session.execute(text('SELECT * FROM tabla_que_no_existe_p3'))
    monkeypatch.setattr(ro, 'calibration_table', broken)
    ro.invalidate_cache()
    with session_scope() as s:
        job, _ = create_job(s, 'Nvidia', agents=['fundamental'], requested_by='pytest', force=True)
        execute_job(s, job, provider_factory=lambda a: FakeProvider([_result([_claim()])]), fetchers=FETCH)
        c = s.query(ResearchClaim).filter_by(job_id=job.id).one()
        assert c.status == 'active' and 'calibration' not in c.confidence_components


def _neg_claims(s, entity, n=2):
    now = datetime.now(UTC)
    out = []
    for hz in ('LONG_TERM', 'MEDIUM_TERM', 'SHORT_TERM'):
        for i, ag in enumerate(('fundamental', 'news', 'supply_chain')[:n + (1 if hz == 'LONG_TERM' else 0)]):
            out.append(_mk_claim(s, entity, ag, 'negative', hz, 0.85, created=now, topic=f'neg_{hz}_{i}'))
    return out


@needs_db
def test_vender_sin_volatilidad_no_se_convierte_en_mantener(db):
    from ontology.db import session_scope
    from research.committee import run_committee
    from research.llm import LLMProvider

    class Off(LLMProvider):
        def available(self):
            return False
    broker = _FakeBroker(position={'symbol': 'INTC', 'qty': 40, 'avg_entry_price': 30, 'market_value': 1200.0,
                                   'unrealized_pl': 0, 'unrealized_plpc': 0})
    no_vol = dict(DEPS, risk_fn=lambda sym: {'ok': False, 'error': 'Yahoo no respondió'}, brokerage=broker)
    with session_scope() as s:
        _neg_claims(s, 'Intel')
        m = run_committee(s, 'Intel', 'pytest', client_id='cli-1', provider=Off(), deps=no_vol)
        assert m['overall_conviction'] <= -50
        assert m['decision'] == 'SELL', (m['decision'], m['memo']['quant_reason_es'])
        assert m['sizing']['qty'] == 40 and m['sizing']['notional'] == 1200
        assert m['inputs']['risk']['error'] and not m['inputs']['risk']['ok']


@needs_db
def test_cotizacion_extranjera_no_se_opera_en_alpaca(db):
    from ontology.db import session_scope
    from research.committee import approve_memo, run_committee
    from research.llm import LLMProvider
    from research.models import CommitteeMemo

    class Off(LLMProvider):
        def available(self):
            return False
    jpy = dict(DEPS, live_fn=lambda eid, sym: dict(LIVE, price=9000.0, currency='JPY'))
    broker = _FakeBroker()
    with session_scope() as s:
        _fresh_entity_claims(s, 'SoftBank')
        m = run_committee(s, 'SoftBank', 'pytest', client_id='cli-1', provider=Off(), deps=dict(jpy, brokerage=broker))
        assert m['symbol'] == '9984.T' and m['decision'] == 'HOLD' and 'Alpaca' in m['memo']['quant_reason_es']
        assert m['inputs']['us_listing'] is False and m['sizing']['qty_est'] is None
        ref = run_committee(s, 'SoftBank', 'pytest', provider=Off(), deps=jpy)          # sin cliente: vista + referencia
        assert ref['decision'] == 'BUY' and ref['sizing']['reference_only'] and ref['sizing']['qty_est'] is None
        # aunque un memo viejo diga BUY con cliente, aprobar NO manda el ticker extranjero al corretaje
        row = s.get(CommitteeMemo, m['memo_id'])
        row.decision, row.sizing = 'BUY', dict(row.sizing, notional=1000.0, side='buy')
        s.flush()
        out = approve_memo(s, m['memo_id'], 'fabrizio', brokerage=broker)
        assert not out['ok'] and out['code'] == 'not_tradable' and not broker.calls
        assert s.get(CommitteeMemo, m['memo_id']).status == 'proposed'


@needs_db
def test_redaccion_sin_pin_no_filtra_montos(db):
    from ontology.db import session_scope
    from research.committee import approve_memo, mark_executed, memo_dict, run_committee
    from research.llm import LLMProvider
    from research.models import CommitteeMemo

    class Off(LLMProvider):
        def available(self):
            return False

    class Blocked(_FakeBroker):
        def preview_order(self, session, client_id, symbol, side, **kw):
            return {'ok': True, 'blocked': True, 'status': 'rejected', 'preview_id': 'pv-b', 'mode': 'paper',
                    'checks': [{'name': 'order_size', 'ok': False, 'severity': 'block',
                                'detail': 'Monto US$6,667.00 supera el máximo por orden del cliente (US$5,000.00)',
                                'detail_en': 'Amount US$6,667.00 exceeds the client per-order max (US$5,000.00)'}],
                    'error': 'bloqueada por controles de riesgo: Monto US$6,667.00 supera…'}
    broker = Blocked()
    with session_scope() as s:
        _fresh_entity_claims(s, 'Cisco')
        m = run_committee(s, 'Cisco', 'pytest', client_id='cli-1', provider=Off(), deps=dict(DEPS, brokerage=broker))
        out = approve_memo(s, m['memo_id'], 'fabrizio', note='ok con USD 100,000 del cliente', brokerage=broker)
        assert not out['ok'] and out['code'] == 'preview_failed' and 'máximo por orden' in out['error']
        assert out['memo']['status'] == 'proposed'                       # se puede reintentar
        mark_executed(s, m['memo_id'], order={'id': 'o1', 'status': 'filled', 'notional': 5000.0, 'qty': 27.6,
                                              'symbol': 'CSCO', 'side': 'buy', 'alpaca_order_id': 'alp-9'})
        row = s.get(CommitteeMemo, m['memo_id'])
        row.decision_note, row.error = 'aprobado con 100.000 dólares', 'saldo USD 90,000'
        red = memo_dict(row, redact_client=True)
    blob = json.dumps(red, ensure_ascii=False)
    assert not re.search(r'\$\s?\d|USD\s?\d|\d[\d.,]*\s?(?:USD|d[óo]lares|dollars)\b', blob), blob
    assert 'mandate' not in red['inputs'] and 'client' not in red['inputs'] and 'package' not in red['inputs']
    assert all(set((a.get('detail') or {})) <= {'decision', 'quant_decision', 'ai', 'overall', 'status', 'preview_id',
                                                'ok', 'code', 'via', 'symbol', 'side', 'blocked', 'withdrawn'}
               for a in red['audit'])
    assert red['client_mode'] == {'mode': 'paper', 'paper': True} and red['preview']['redacted']
    assert red['sizing']['current_weight_pct'] is None


@needs_db
def test_aprobaciones_simultaneas_crean_una_sola_orden(db):
    import threading
    import time as _t
    from ontology.db import session_scope
    from research.committee import approve_memo, run_committee
    from research.llm import LLMProvider

    class Off(LLMProvider):
        def available(self):
            return False

    class Slow(_FakeBroker):
        def preview_order(self, *a, **kw):
            _t.sleep(1.0)
            return super().preview_order(*a, **kw)
    broker = Slow()
    with session_scope() as s:
        _fresh_entity_claims(s, 'Marvell')
        mid = run_committee(s, 'Marvell', 'pytest', client_id='cli-1', provider=Off(),
                            deps=dict(DEPS, brokerage=broker))['memo_id']
    results = []

    def go():
        with session_scope() as s:
            results.append(approve_memo(s, mid, 'fabrizio', brokerage=broker))
    th = [threading.Thread(target=go) for _ in range(2)]
    for t in th:
        t.start()
    for t in th:
        t.join(30)
    assert len(broker.calls) == 1, broker.calls
    assert sorted(bool(r['ok']) for r in results) == [False, True]
    assert any(r.get('code') == 'bad_status' for r in results)


@needs_db
def test_rechazar_memo_ya_enviado_no_miente(db):
    from ontology.db import session_scope
    from research.committee import approve_memo, reject_memo, run_committee
    from research.llm import LLMProvider

    class Off(LLMProvider):
        def available(self):
            return False

    class Sent(_FakeBroker):
        def reject_preview(self, session, preview_id, actor, reason=''):
            return {'ok': False, 'code': 'bad_status', 'status': 'submitted', 'error': 'la propuesta ya está «submitted»'}
    broker = Sent()
    with session_scope() as s:
        _fresh_entity_claims(s, 'Dell')
        m = run_committee(s, 'Dell', 'pytest', client_id='cli-1', provider=Off(), deps=dict(DEPS, brokerage=broker))
        assert approve_memo(s, m['memo_id'], 'fabrizio', brokerage=broker)['ok']
        rj = reject_memo(s, m['memo_id'], 'fabrizio', reason='tarde', brokerage=broker)
        assert not rj['ok'] and rj['code'] == 'order_sent' and rj['error_en']
        assert rj['memo']['status'] == 'executed'


# ── integración con el corretaje REAL (brokerage.service + sus controles) ────
class _Alp:
    """Bróker Alpaca falso (misma forma que la API: números como strings)."""
    def __init__(self, equity=100000.0, price=180.0):
        self.paper, self.price, self.submits = True, price, []
        self.account = {'equity': str(equity), 'cash': str(equity), 'buying_power': str(equity),
                        'portfolio_value': str(equity), 'currency': 'USD', 'status': 'ACTIVE'}
        self.by_coid = {}

    def get_account(self):
        return dict(self.account)

    def get_positions(self):
        return []

    def get_clock(self):
        return {'is_open': True}

    def latest_price(self, symbol):
        return self.price

    def submit_order(self, symbol, side, notional=None, qty=None, order_type='market', limit_price=None,
                     time_in_force=None, client_order_id=None):
        od = {'id': f'alp-{len(self.submits) + 1}', 'client_order_id': client_order_id, 'status': 'accepted',
              'symbol': symbol, 'side': side, 'filled_qty': '0'}
        self.submits.append(dict(od, notional=notional, qty=qty))
        self.by_coid[client_order_id] = od
        return dict(od)

    def get_order_by_client_id(self, coid):
        return dict(self.by_coid[coid])


@pytest.fixture
def real_broker(monkeypatch):
    pytest.importorskip('brokerage.service')
    from brokerage import service
    for k in ('BROKERAGE_TRADING_ENABLED', 'BROKERAGE_LIVE_ENABLED', 'BROKERAGE_AUTO_APPROVE_PAPER', 'ALPACA_KEY',
              'ALPACA_SECRET', 'ALPACA_BASE'):
        monkeypatch.delenv(k, raising=False)
    alp = _Alp()
    monkeypatch.setattr(service, 'make_alpaca', lambda rec: alp)
    return service, alp, monkeypatch


def _real_client(s, service, name):
    from brokerage.models import BrokerClient
    r = service.create_client(s, name, actor='pytest')          # perfil moderado: orden máx. US$5,000
    assert r['ok'], r
    cid = r['client']['id']
    s.get(BrokerClient, cid).enc_credentials = 'conectado-en-test'   # make_alpaca está sustituido
    s.flush()
    return cid


@needs_db
def test_integracion_corretaje_real_topes_aprobacion_y_retiro(db, real_broker):
    from ontology.db import session_scope
    from research.committee import approve_memo, reject_memo, run_committee
    from research.llm import LLMProvider
    from research.models import CommitteeMemo
    service, alp, mp = real_broker

    class Off(LLMProvider):
        def available(self):
            return False
    vol30 = dict(DEPS, risk_fn=lambda sym: dict(RISK, vol_ann_pct=30.0), brokerage=service)
    with session_scope() as s:
        cid = _real_client(s, service, 'Cliente Integración')
        _fresh_entity_claims(s, 'Qualcomm')
        m = run_committee(s, 'Qualcomm', 'pytest', client_id=cid, provider=Off(), deps=vol30)
        # C6: sin historial validado 2 % → 1 %; 1 % ÷ 30 % = 3.33 % de $100k = $3,333 (bajo el tope por orden de $5,000)
        assert m['decision'] == 'BUY' and m['sizing']['notional'] == 3333 and m['sizing']['capped_by'] == 'unvalidated'
        assert m['inputs']['mandate']['max_order_usd'] == 5000 and m['inputs']['mandate']['daily_remaining_usd'] == 15000
        out = approve_memo(s, m['memo_id'], 'fabrizio', brokerage=service)
        assert out['ok'], out
        pv = out['preview']
        assert not pv['blocked'] and pv['status'] == 'pending_approval' and pv['requires_human_approval']
        assert out['memo']['status'] == 'approved'
        assert any(p['id'] == pv['preview_id'] for p in service.pending_approvals(s))
        # rechazar el memo RETIRA la orden de la cola de Clientes
        rj = reject_memo(s, m['memo_id'], 'fabrizio', reason='cambié de idea', brokerage=service)
        assert rj['ok'] and rj['withdrawn']['ok'] and rj['memo']['status'] == 'rejected'
        assert not any(p['id'] == pv['preview_id'] for p in service.pending_approvals(s))
        assert service.approve_preview(s, pv['preview_id'], 'otro')['ok'] is False
        assert not alp.submits

        # límite del cliente más bajo → la previsualización sale BLOQUEADA: el memo sigue propuesto
        m2 = run_committee(s, 'Qualcomm', 'pytest', client_id=cid, provider=Off(), deps=vol30)
        service.update_client(s, cid, {'limits': {'max_order_usd': 1000}}, actor='pytest')
        bad = approve_memo(s, m2['memo_id'], 'fabrizio', brokerage=service)
        assert not bad['ok'] and bad['code'] == 'preview_failed' and bad['preview']['blocked']
        assert 'máximo por orden' in bad['error'] and 'per-order' in bad['error_en']
        assert s.get(CommitteeMemo, m2['memo_id']).status == 'proposed'
        # un memo nuevo ya respeta el límite nuevo
        m3 = run_committee(s, 'Qualcomm', 'pytest', client_id=cid, provider=Off(), deps=vol30)
        assert m3['sizing']['notional'] == 1000
        assert approve_memo(s, m3['memo_id'], 'fabrizio', brokerage=service)['ok']

        # BROKERAGE_AUTO_APPROVE_PAPER=on + papel: la aprobación con PIN del memo ES la humana → se envía
        mp.setenv('BROKERAGE_AUTO_APPROVE_PAPER', 'on')
        cid2 = _real_client(s, service, 'Cliente Auto')
        _fresh_entity_claims(s, 'Micron')
        m4 = run_committee(s, 'Micron', 'pytest', client_id=cid2, provider=Off(), deps=vol30)
        ok = approve_memo(s, m4['memo_id'], 'fabrizio', brokerage=service)
        assert ok['ok'] and ok.get('executed') and ok['memo']['status'] == 'executed', ok
        assert alp.submits and alp.submits[-1]['symbol'] == 'MU' and alp.submits[-1]['notional'] == 3333
        assert any(a['action'] == 'executed' for a in s.get(CommitteeMemo, m4['memo_id']).audit)


@needs_db
def test_api_sync_solo_con_pin_dedupe_y_tope(db, monkeypatch):
    import research.committee as rc
    import server
    from ontology.db import session_scope
    c = server.app.test_client()
    monkeypatch.setattr(rc, '_default_risk', DEPS['risk_fn'])
    monkeypatch.setattr(rc, '_default_live', DEPS['live_fn'])
    monkeypatch.delenv('TRADE_PIN', raising=False)
    with session_scope() as s:
        _fresh_entity_claims(s, 'Arista')
    monkeypatch.setitem(server.app.config, 'TESTING', False)
    r = c.post('/api/committee/run', json={'entity': 'Arista', 'actor': 'pytest', 'sync': True})
    assert r.status_code == 202 and r.get_json()['status'] == 'running'        # sin PIN: nunca síncrono
    mid = r.get_json()['memo_id']
    r2 = c.post('/api/committee/run', json={'entity': 'Arista', 'actor': 'pytest'})
    assert r2.status_code == 202 and r2.get_json()['memo_id'] == mid and r2.get_json()['reused']
    import time
    for _ in range(200):
        if c.get(f'/api/committee/memo/{mid}').get_json()['status'] != 'running':
            break
        time.sleep(0.05)
    monkeypatch.setattr(rc, 'acquire_run_slot', lambda: False)
    r3 = c.post('/api/committee/run', json={'entity': 'Broadcom', 'actor': 'pytest'})
    assert r3.status_code == 429 and r3.get_json()['error_en']


def test_progreso_del_comite_y_memo_huerfano():
    """La pantalla de carga recibe el paso real; un memo 'running' sin nadie
    calculándolo (reinicio) se marca 'failed' en vez de cargar para siempre."""
    from research.committee import progress_clear, progress_get, progress_set
    progress_set('m1', 'claims')
    progress_set('m1', 'live', n_claims=3)
    progress_set('m1', 'chair')
    p = progress_get('m1')
    assert p['stage'] == 'chair' and p['done'] == ['claims', 'live'] and p['n_claims'] == 3
    assert 'chair' in p['stages'] and p['elapsed_s'] >= 0
    progress_clear('m1')
    assert progress_get('m1') is None


@needs_db
def test_memo_huerfano_se_marca_fallido(db):
    from datetime import datetime, timedelta, timezone
    import server
    from ontology.db import session_scope
    from research.committee import create_placeholder
    with session_scope() as s:
        m = create_placeholder(s, 'Nvidia', 'pytest')
        m.created_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        mid = m.id
    r = server.app.test_client().get(f'/api/committee/memo/{mid}')
    d = r.get_json()
    assert d['status'] == 'failed' and 'reinici' in (d.get('error') or '')


@needs_db
def test_sala_del_comite_puestos_y_conversacion(db):
    """Pedido 2026-10-02: puestos + comunicación visible, sin texto inventado."""
    from ontology.db import session_scope
    from research.committee import progress_get, run_committee
    from research.llm import FakeProvider
    with session_scope() as s:
        cl = _fresh_entity_claims(s, 'Broadcom')
        prov = FakeProvider([lambda p: _chair_json(p)])
        m = run_committee(s, 'Broadcom', 'pytest', provider=prov, deps=DEPS)
        b = m['memo']
        seats = {x['seat']: x for x in b['seats']}
        assert set(seats) == {'fundamental', 'supply_chain', 'macro', 'news', 'technical'}
        assert seats['technical']['stance'] == 'against' and seats['fundamental']['stance'] == 'for'
        assert b['tally']['for'] >= 3 and b['tally']['against'] == 1
        tr = b['transcript']
        kinds = [x['kind'] for x in tr]
        assert tr[0]['seat'] == 'chair' and kinds[0] == 'open'
        assert kinds.count('position') == 5 and 'rebuttal' in kinds
        assert any(x['seat'] == 'quant' and 'Q1' in x.get('refs', []) for x in tr)
        assert any(x['seat'] == 'risk_officer' for x in tr) and tr[-1]['seat'] == 'chair'
        assert tr[-1]['kind'] == 'verdict' and 'PROPUESTA' in tr[-1]['text_es'] and tr[-1]['text_en']
        # lo que "dice" cada analista es SU conclusión real (texto del claim), con su C#
        pos = next(x for x in tr if x['kind'] == 'position' and x['seat'] == 'fundamental')
        assert cl[0].statement_es[:40] in pos['text_es'] and pos['refs'][0] in m['inputs']['valid_refs']
        # la contradicción X1 se debate entre los dos puestos
        assert any(x['kind'] == 'rebuttal' and 'X1' in x.get('refs', []) for x in tr)
        assert progress_get(m['memo_id'])['messages']              # en vivo durante la corrida


def test_deliberacion_sin_conclusiones_y_sin_cotizar():
    from research import deliberation as d
    assert 'Investigación' in d.opening('X', None, [], 0, 0)[0]['text_es']
    assert d.risk_msg({'ok': True}, None) is None
    assert 'no cotiza' in d.market_msg({}, None)['text_es']
    assert d.stance_of(0.5) == 'for' and d.stance_of(-0.5) == 'against' and d.stance_of(0.05) == 'neutral'


def _seat_ai(prompt):
    """IA falsa de un puesto: postura según SU propia conclusión (sección TUS CONCLUSIONES)."""
    if 'TAREA: tu réplica' in prompt:
        own = re.search(r'\b(C\d+) \[', prompt.split('TUS CONCLUSIONES')[1]).group(1)
        return json.dumps({'reply_es': f'Mi evidencia de corto plazo pesa más que tu lectura de largo plazo [{own}].',
                           'reply_en': f'My short-term evidence outweighs your long-term reading [{own}].',
                           'concedes_es': 'El largo plazo se ve bien.', 'concedes_en': 'Long term looks fine.',
                           'stance_after': 'against' if 'postura negative' in prompt.split('LO QUE SOSTIENEN')[0] else 'for',
                           'refs': [own]})
    mine = prompt.split('TUS CONCLUSIONES')[1].split('LO QUE SOSTIENEN')[0]
    ref = re.search(r'\b(C\d+) \[', mine).group(1)
    st = 'against' if 'postura negative' in mine else 'for'
    return json.dumps({'stance': st, 'headline_es': 'Mi conclusión principal es clara',
                       'headline_en': 'My main conclusion is clear',
                       'argument_es': f'La evidencia [{ref}] muestra una tendencia que importa para el valor de la empresa en este plazo.',
                       'argument_en': f'The evidence [{ref}] shows a trend that matters for the company value in this horizon.',
                       'watch_es': 'el próximo trimestre', 'watch_en': 'next quarter',
                       'change_mind_es': 'si cambia la demanda', 'change_mind_en': 'if demand changes',
                       'conviction': 0.7, 'refs': [ref, 'D1']})


@needs_db
def test_debate_con_ia_por_puesto_y_replicas(db):
    from ontology.db import session_scope
    from research.committee import run_committee
    from research.llm import FakeProvider
    from research.models import AgentRun
    with session_scope() as s:
        _fresh_entity_claims(s, 'Micron')
        prov = FakeProvider([lambda p: _chair_json(p)])
        deps = dict(DEPS, seat_provider_factory=lambda: FakeProvider([_seat_ai, _seat_ai]))
        m = run_committee(s, 'Micron', 'pytest', provider=prov, deps=deps)
        b = m['memo']
        assert b['debate']['ai'] and b['debate']['n_ai'] == 5 and b['debate']['n_rebuttals'] >= 2
        tr = b['transcript']
        ai_pos = [x for x in tr if x['kind'] == 'position' and x.get('ai')]
        assert len(ai_pos) == 5 and all(x['stage'] == 'debate' for x in ai_pos)
        assert any(x['kind'] == 'rebuttal' and x.get('ai') and 'Concedo' in x['text_es'] for x in tr)
        tech = next(x for x in ai_pos if x['seat'] == 'technical')
        assert tech['stance'] == 'against' and 'Vigilo' in tech['text_es']
        # el presidente recibió el debate (S#) en su paquete
        assert 'DEBATE DEL COMITÉ' in prov.calls[0] and 'S1 [debate' in prov.calls[0]
        assert 'S1' in m['inputs']['valid_refs']
        # cada intervención con IA cuenta para el presupuesto
        n = s.query(AgentRun).filter(AgentRun.agent_id.in_(('committee_seat', 'committee_rebuttal')),
                                     AgentRun.entity_id == 'Micron').count()
        assert n >= 7


@needs_db
def test_debate_ia_cifra_inventada_cae_a_plantilla(db):
    from ontology.db import session_scope
    from research.committee import run_committee
    from research.llm import FakeProvider

    def liar(prompt):
        d = json.loads(_seat_ai(prompt))
        if 'argument_es' in d:
            d['argument_es'] += ' Su capitalización es de $9,999 mil millones.'
        return json.dumps(d)
    with session_scope() as s:
        _fresh_entity_claims(s, 'AMD')
        deps = dict(DEPS, seat_provider_factory=lambda: FakeProvider([liar, liar]))
        m = run_committee(s, 'AMD', 'pytest', provider=FakeProvider([lambda p: _chair_json(p)]), deps=deps)
        tr = m['memo']['transcript']
        assert not any('9,999' in x['text_es'] for x in tr)              # el guardián la rechazó
        assert m['memo']['debate']['n_ai'] == 0 and not m['memo']['debate']['ai']
        assert sum(1 for x in tr if x['kind'] == 'position') == 5          # plantillas con su conclusión real


def test_rescate_de_resultado_casi_valido():
    from research.agents.base import salvage
    from research.schemas import AgentResearchResult
    obj = AgentResearchResult.model_validate({
        'summary_es': 'Resumen de prueba suficiente', 'summary_en': 'Test summary enough',
        'claims': [
            {'predicate': 'AAA', 'claim_type': 'forecast', 'topic': 'revenue_growth', 'stance': 'positive',
             'horizon': 'LONG_TERM', 'statement_es': 'Crece por centros de datos.', 'statement_en': 'Grows via data centers.',
             'reasoning_summary': 'razonamiento de prueba', 'evidence_refs': ['E1', 'E9'], 'counter_evidence_refs': [],
             'agent_certainty': 0.6, 'falsifiers': ['f'], 'affected_entities': []},
            {'predicate': 'BBB', 'claim_type': 'forecast', 'topic': 'revenue_growth', 'stance': 'positive',
             'horizon': 'LONG_TERM', 'statement_es': 'Vale $5,000 mil millones.', 'statement_en': 'Worth $5,000 billion.',
             'reasoning_summary': 'razonamiento de prueba', 'evidence_refs': ['E1'], 'counter_evidence_refs': [],
             'agent_certainty': 0.6, 'falsifiers': ['f'], 'affected_entities': []}]})
    assert salvage(obj, ['E1'], [{'title': 'E1', 'excerpt': 'ventas suben'}]) == []
    assert len(obj.claims) == 1 and obj.claims[0].evidence_refs == ['E1']
    assert any('Descartada' in q for q in obj.unresolved_questions)


@needs_db
def test_pizarra_de_conclusiones(db):
    import server
    from ontology.db import session_scope
    from research.committee import board
    with session_scope() as s:
        _fresh_entity_claims(s, 'IonQ')
        b = board(s, limit=80)
        it = next(x for x in b['items'] if x['entity_id'] == 'IonQ')
        assert it['n_claims'] == 6 and it['n_contradictions'] == 1 and it['overall_conviction'] > 0
        assert it['best_for']['agent_type'] in ('fundamental', 'supply_chain', 'macro', 'news')
        assert it['best_against']['agent_type'] == 'technical' and it['label']
        convs = [x['overall_conviction'] for x in b['items']]
        assert convs == sorted(convs, reverse=True)
    server.app.config['TESTING'] = True
    r = server.app.test_client().get('/api/committee/board?limit=5')
    assert r.status_code == 200 and len(r.get_json()['items']) <= 5


@needs_db
def test_pizarra_actualizar_investigacion(db, monkeypatch):
    import core.ai
    import research.runner as rr
    import server
    from ontology.db import session_scope
    from research.committee import refresh_targets
    with session_scope() as s:
        assert refresh_targets(s, entities=['nvda', 'zzqqxx', 'TSMC']) == ['Nvidia', 'TSMC']
    monkeypatch.setattr(core.ai, '_ai_configured', lambda: True)
    ran = []
    monkeypatch.setattr(rr, 'execute_job', lambda s, job, **k: ran.append(job.entity_id))
    server.app.config['TESTING'] = True
    c = server.app.test_client()
    assert c.post('/api/committee/board/refresh', json={}).status_code == 400
    r = c.post('/api/committee/board/refresh', json={'actor': 'pytest', 'entities': ['Rigetti']})
    assert r.status_code == 202 and r.get_json()['jobs'][0]['entity_id'] == 'Rigetti'
    import time
    for _ in range(50):
        if ran:
            break
        time.sleep(0.05)
    assert ran == ['Rigetti']
