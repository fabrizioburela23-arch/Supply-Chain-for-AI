"""tests/test_live_universe_db.py — lote L con Postgres: las 386 fichas completas aplicadas → el universo en vivo y la
historia diaria las incluyen (por tandas, sin pasar el presupuesto de pedidos de hoy) y deshacer las saca.

Base desechable (se migra el catálogo entero y se aplica data/import/lotes/2026-10-15/bundle_lote2_completas.json.gz,
~60 s). Sin red: Yahoo simulado con un reloj falso (cuenta pedidos y la espera del tope de 15 por minuto); la historia
diaria con una descarga falsa que no trae filas (cuenta pedidos, no escribe). Lo medido queda en `ronda['medido']`
(también lo imprime con -s)."""
import math
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('KHIPU_SCHEDULER', 'off')

DATABASE_URL = os.getenv('DATABASE_URL', '')
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
LOTE = os.path.join(ROOT, 'data', 'import', 'lotes', '2026-10-15')


def _rebuild():
    from core.hotviews import builder, hot, registry
    registry.reset()
    hot.invalidate()
    g = builder.build_once()
    assert g.source == 'pg'
    return hot.graph()


def _dbname():
    from sqlalchemy import text

    from ontology.db import session_scope
    with session_scope() as s:
        return s.execute(text('SELECT current_database()')).scalar()


class _Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


def _live_cycles(n_cycles=3):
    """Ciclos de core/live_caps con Yahoo simulado: [(símbolos, pedidos, nuevos admitidos, pendientes, segundos
    simulados, máx. pedidos en 60 s)]."""
    from core import live_caps as LC
    from core import quotes as Q
    clk, log = _Clock(), []

    class R:
        status_code = 200

        def __init__(self, syms):
            self.syms = syms

        def json(self):
            return {'quoteResponse': {'result': [{'symbol': s, 'marketCap': 1.0e10, 'currency': 'USD',
                                                  'regularMarketPrice': 10.0} for s in self.syms]}}

    class S:
        def get(self, url, params=None, timeout=None):
            syms = params['symbols'].split(',')
            log.append(clk.t)
            clk.t += 0.4                       # ~0,4 s por pedido de 40 símbolos
            return R(syms)
    real_sess, real_fx, real_out = Q._yahoo_session, Q._fx_to_usd, LC._daily_outcomes
    Q._yahoo_session, Q._fx_to_usd, LC._daily_outcomes = (lambda: (S(), 'c')), (lambda cur: 1.0), (lambda: None)
    lim = Q.WindowLimiter(Q.YAHOO_BATCH_PER_MIN, 60.0, clock=clk, sleep=clk.sleep)
    LC._PHASE['admitted'].clear()
    LC._STATE.update(caps={}, as_of=None, ts=0.0, running=False, error=None, cycle=None)
    out = []
    try:
        for _c in range(n_cycles):
            log.clear()
            t0 = clk.t
            LC.refresh(fetch=lambda syms: Q.fetch_quotes_batch_yahoo(syms, limiter=lim))
            st = LC.get_caps(start=False)
            per_min = max((sum(1 for u in log if t <= u < t + 60) for t in log), default=0)
            out.append({'symbols': st['cycle']['symbols'], 'requests': len(log), 'new': st['cycle']['new_admitted'],
                        'pending': st['cycle']['pending'], 'caps': st['n'], 'sim_s': round(clk.t - t0, 1),
                        'max_per_60s': per_min, 'caps_ids': set(st['caps'])})
            clk.t += 15 * 60
    finally:
        Q._yahoo_session, Q._fx_to_usd, LC._daily_outcomes = real_sess, real_fx, real_out
        LC._PHASE['admitted'].clear()
        LC._STATE.update(caps={}, as_of=None, ts=0.0, running=False, error=None, cycle=None)
    return out


def _eod_run(now, per_run=None):
    """Una corrida diaria con descarga falsa (sin filas). → {total, requests, phase, paced_s}."""
    from core import prices_store as PS
    calls, slept = [], []

    def getter(url, params=None, timeout=None):
        calls.append(url.rsplit('/', 1)[1])
        return {'chart': {'result': []}}, None
    real = PS.NEW_PER_DAILY_RUN
    if per_run is not None:
        PS.NEW_PER_DAILY_RUN = per_run
    try:
        st = {'stop': False}
        t0 = time.perf_counter()
        PS._run(st, rng='1mo', getter=getter, sleep=lambda s: slept.append(s), now=now, interval=PS.req_interval_s())
    finally:
        PS.NEW_PER_DAILY_RUN = real
    return {'total': st['total'], 'requests': len(calls), 'calls': list(calls), 'phase': st['phase'],
            'failed': st['failed'], 'paced_s': round(len(calls) * PS.req_interval_s(), 1),
            'wall_s': round(time.perf_counter() - t0, 1)}


@pytest.fixture(scope='module')
def ronda():
    from sqlalchemy import text

    import brokerage.models  # noqa: F401
    import mcp_server.models  # noqa: F401
    import research.models  # noqa: F401
    from core import identity
    from core import instruments as I
    from core import prices_store as PS
    from ontology import company_import as CI
    from ontology import import_models
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    import_models._reset_for_tests()
    assert init_schema(retries=1)
    from scripts.migrate_v0_to_ontology import run_migration
    assert run_migration(reset=False, log=lambda *_a: None)
    assert import_models.ensure_tables(engine)
    PS._reset_for_tests()
    v0 = _rebuild()
    live0, eod0 = I.live_symbols(), I.eod_symbols()
    b = CI.load_bundle(os.path.join(LOTE, CI.LOTE2_BUNDLE))
    p = CI.plan(b['records'], b['updates'], view=v0, batch=b['batch'], what_changes=False)
    principal = identity.operator('ui', 'pytest')
    res = CI.apply_run(session_scope, p, principal, confirm_db=_dbname(), expect={'plan_sha': p['plan_sha']}, view=v0)
    v1 = _rebuild()
    t = time.perf_counter()
    u1 = I.universe()
    universe_ms = round((time.perf_counter() - t) * 1000, 1)
    live1, eod1 = I.live_symbols(), I.eod_symbols()
    cycles = _live_cycles(3)
    t = time.perf_counter()
    with session_scope() as s:
        eq1, fx1 = PS._targets(s)
        n_table = s.execute(text("SELECT count(*) FROM instruments WHERE source = 'import'")).scalar()
    targets_ms = round((time.perf_counter() - t) * 1000, 1)
    day = datetime(2026, 10, 15, 23, tzinfo=timezone.utc)
    run_a = _eod_run(day)                                   # la tanda real (500): entra todo el lote 2
    run_b = _eod_run(day, per_run=100)                      # tanda chica para ver las tandas
    run_c = _eod_run(day + timedelta(days=1), per_run=100)  # al día siguiente la ventana rota
    nodes1 = {n['id']: n for n in v1.nodes}
    with session_scope() as s:
        rb = CI.rollback_run(s, res['run_id'], principal, confirm_db=_dbname())
    v2 = _rebuild()
    live2 = I.live_symbols()
    with session_scope() as s:
        eq2, fx2 = PS._targets(s)
        n_table2 = s.execute(text("SELECT count(*) FROM instruments WHERE source = 'import'")).scalar()
    medido = {'nodes': (len(v0.nodes), len(v1.nodes), len(v2.nodes)),
              'live_symbols': (len(live0), len(live1), len(live2)),
              'eod_equities': (len(eod0['equities']), len(eod1['equities'])),
              'fx_pairs': (len(eod0['currencies']), len(eod1['currencies'])),
              'universe_ms': universe_ms, 'targets_ms': targets_ms,
              'live_cycles': [{k: v for k, v in c.items() if k != 'caps_ids'} for c in cycles],
              'eod_targets_after_import': (len(eq1), len(fx1)), 'instruments_import_rows': n_table,
              'eod_run_500': {k: v for k, v in run_a.items() if k != 'calls'},
              'eod_run_100': {k: v for k, v in run_b.items() if k != 'calls'},
              'eod_run_100_next_day': {k: v for k, v in run_c.items() if k != 'calls'},
              'after_rollback': {'eod_targets': (len(eq2), len(fx2)), 'instruments_import_rows': n_table2}}
    print('\nMEDIDO', medido)
    yield {'plan': p, 'res': res, 'rb': rb, 'live0': live0, 'live1': live1, 'live2': live2, 'eod0': eod0, 'eod1': eod1,
           'u1': u1, 'nodes1': nodes1, 'cycles': cycles, 'eq1': eq1, 'fx1': fx1, 'eq2': eq2, 'fx2': fx2,
           'run_a': run_a, 'run_b': run_b, 'run_c': run_c, 'medido': medido, 'n_table2': n_table2}
    Base.metadata.drop_all(engine)


def test_las_importadas_con_listado_principal_entran_al_universo(ronda):
    live0, live1 = ronda['live0'], ronda['live1']
    assert len(live0) == 568                                        # el catálogo de hoy
    base = set(live0.values())
    created = [i for i in ronda['plan']['items'] if i['action'] == 'create']
    want = {}
    for it in created:
        prim = [l for l in (ronda['nodes1'].get(it['id']) or {}).get('listings') or [] if l.get('is_primary')]
        if prim and prim[0]['yahoo_symbol'].upper() not in base:
            want[it['id']] = prim[0]['yahoo_symbol'].upper()
    assert len(want) >= 180
    for cid, sym in want.items():
        assert live1.get(cid) == sym, (cid, sym)
    assert len(live1) == len(live0) + len(want) and len(set(live1.values())) == len(live1)   # un símbolo, una vez
    # las FUSIONADAS conservan su cotización del catálogo (nada cambia solo) y la de la ficha queda secundaria
    assert live1['Samsung'] == live0['Samsung'] == 'SSNLF'
    assert '005930.KS' in ronda['eod1']['equities'] and '005930.KS' not in live1.values()
    u = ronda['u1']
    assert u['conflicts'] == [] and u['invalid'] == []
    assert sum(1 for e in u['primary'] if e['origin'] == 'new') == len(want)
    # monedas nuevas declaradas por las fichas (sufijos que SUFFIX no conoce: .BK, .SN…) piden su par FX
    assert {'THB', 'CLP'} <= ronda['eod1']['currencies'] - ronda['eod0']['currencies']
    # la capitalización nunca viene de la ficha: ninguna importada trae cifras de mercado en sus propiedades
    for cid in want:
        assert not ({'mktcap_b', 'mcap_b', 'market_cap', 'shares_outstanding'} & set(ronda['nodes1'][cid]))


def test_en_vivo_por_tandas_sin_pasar_15_pedidos_por_minuto(ronda):
    c = ronda['cycles']
    n0, n1 = len(ronda['live0']), len(ronda['live1'])
    new = n1 - n0
    assert [x['symbols'] for x in c] == [n0 + min(120, new), n1, n1]
    assert [x['requests'] for x in c] == [math.ceil((n0 + min(120, new)) / 40), math.ceil(n1 / 40), math.ceil(n1 / 40)]
    assert c[0]['new'] == 120 and c[0]['pending'] == new - 120 and c[1]['pending'] == 0 and c[2]['new'] == 0
    assert all(x['max_per_60s'] <= 15 for x in c)                   # nunca más que el ciclo de HOY
    assert c[0]['requests'] - math.ceil(n0 / 40) == 3               # el primer ciclo tras importar: +3 pedidos
    assert set(ronda['live1']) == c[1]['caps_ids']                   # todas (también las importadas) con capitalización


def test_historia_diaria_las_suma_en_una_tanda_y_rota(ronda):
    eq1, eod1 = ronda['eq1'], ronda['eod1']
    assert set(eod1['equities']) <= set(eq1) and eq1[:2] == ['SPY', '^IRX']
    a = ronda['run_a']
    assert a['failed'] == 0 and a['requests'] == a['total'] == len(eq1) + len(ronda['fx1'])
    assert a['phase']['new'] == a['phase']['admitted'] > 300 and a['phase']['pending'] == 0   # lote 2 cabe en un día
    b, c = ronda['run_b'], ronda['run_c']
    assert b['phase']['admitted'] == c['phase']['admitted'] == 100
    assert b['requests'] == a['requests'] - b['phase']['pending']
    new_b = set(b['calls']) - set(c['calls'])
    assert new_b and set(c['calls']) - set(b['calls'])             # otro día, otra ventana de nuevos


def test_deshacer_saca_las_importadas_de_lo_en_vivo_y_de_la_historia(ronda):
    assert ronda['rb']['decision_id']
    assert ronda['live2'] == ronda['live0']
    # las filas de `instruments` quedan (la siembra nunca borra) pero la corrida diaria ya no las baja
    assert ronda['n_table2'] > 0
    imported = {e['symbol'] for e in ronda['u1']['primary'] + ronda['u1']['secondary'] if e['origin'] == 'new'}
    assert not (imported & set(ronda['eq2']))
    assert len(ronda['eq2']) == len(ronda['eod0']['equities']) + 2   # + SPY y ^IRX
