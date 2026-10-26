"""tests/test_prices_eod.py — la memoria de los números (BRECHAS bloque 2: L3-01, L2-12, L3-14).

  · la descarga descarta la vela de la sesión que NO cerró y fecha cada cierre con el día de la bolsa;
  · la ingesta es idempotente y append-only: un split/dividendo detectado al re-bajar NO reescribe precios —
    agrega un factor en price_adjustments y la serie leída queda continua;
  · UPDATE/DELETE/TRUNCATE fallan en las tablas de historia;
  · el relleno de 5 años SOLO arranca a pedido del operador (PIN), deja la decisión 'data.backfill' (inicio y
    cierre), muestra progreso y es reanudable (la segunda vez salta lo cubierto);
  · la corrida diaria guarda cierres + FX y las fotos del día (metrics_eod, positions_eod desde user_state);
  · el reloj NO rellena historia solo.
Sin red (Yahoo simulado). Lo de base se salta sin DATABASE_URL."""
import os
import random
import re
import sys
from datetime import date, datetime, timedelta, timezone

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')


def _bdays(n, end=None):
    end = end or date.today() - timedelta(days=1)
    out, d = [], end
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d -= timedelta(days=1)
    return sorted(out)


def _chart(dates, closes, currency='USD', adj=None, gmtoffset=0, period=None):
    ts = [int(datetime(d.year, d.month, d.day, 15, tzinfo=timezone.utc).timestamp()) - gmtoffset for d in dates]
    meta = {'currency': currency, 'gmtoffset': gmtoffset, 'exchangeTimezoneName': 'X',
            'currentTradingPeriod': {'regular': period or {'start': 0, 'end': 1}}}
    return {'chart': {'result': [{'timestamp': ts, 'meta': meta,
                                  'indicators': {'quote': [{'close': list(closes), 'open': list(closes),
                                                            'high': list(closes), 'low': list(closes),
                                                            'volume': [1234] * len(closes)}],
                                                 'adjclose': [{'adjclose': list(adj or closes)}]}}]}}


# ── sin base ─────────────────────────────────────────────────────────────────
def test_descarga_descarta_la_vela_de_la_sesion_abierta_y_usa_el_dia_de_la_bolsa():
    from core import prices_store
    now = datetime(2026, 10, 13, 18, 0, tzinfo=timezone.utc)
    d = [date(2026, 10, 9), date(2026, 10, 12), date(2026, 10, 13)]
    start = int(datetime(2026, 10, 13, 13, 30, tzinfo=timezone.utc).timestamp())
    chart = _chart(d, [10, 11, 12], period={'start': start, 'end': start + 6.5 * 3600})
    got = prices_store.fetch_chart('ABC', getter=lambda u, params=None, timeout=None: (chart, None), now=now)
    assert [r['date'] for r in got['rows']] == d[:2]            # la del 13 (sesión abierta) no entra
    # Tokio: una vela a las 00:00 UTC es el día SIGUIENTE en la bolsa (gmtoffset +9 h)
    tk = _chart([date(2026, 10, 8)], [100], gmtoffset=32400)
    tk['chart']['result'][0]['timestamp'] = [int(datetime(2026, 10, 8, 0, 30, tzinfo=timezone.utc).timestamp())]
    g2 = prices_store.fetch_chart('8035.T', getter=lambda u, params=None, timeout=None: (tk, None), now=now)
    assert g2['rows'][0]['date'] == date(2026, 10, 8) and g2['rows'][0]['volume'] == 1234


def test_descarga_sin_red_no_inventa():
    from core import prices_store
    got = prices_store.fetch_chart('ABC', getter=lambda u, params=None, timeout=None: (None, 'upstream 429'))
    assert got['rows'] == [] and '429' in got['error']


def test_detector_de_ajustes_split_4_a_1():
    from core import prices_store
    d = _bdays(6)
    stored = {x: 400.0 for x in d[:4]}
    fetched = [{'date': x, 'adj_close': 100.0} for x in d[:4]] + [{'date': x, 'adj_close': 101.0} for x in d[4:]]
    adj = prices_store.detect_adjustments(stored, fetched)
    assert len(adj) == 1 and adj[0][0] == d[4] and adj[0][1] == pytest.approx(0.25)


def test_sin_base_todo_queda_en_vivo(monkeypatch):
    from core import prices_store
    from ontology import db
    monkeypatch.setattr(db, 'DATABASE_URL', '')
    assert prices_store.history('NVDA', '1y') is None
    assert prices_store.fx_history('JPY', '1y') is None
    assert prices_store.daily_tick() == {'skipped': 'no_database'}


def test_el_reloj_no_rellena_historia_solo():
    """BRECHAS #3 sin responder: el relleno de 5 años solo se llama desde el endpoint con PIN."""
    srv = open(os.path.join(ROOT, 'server.py'), encoding='utf-8').read()
    assert "_sched.register('prices_eod_daily', _prices_store.daily_tick" in srv
    assert 'start_backfill' not in srv
    callers = []
    for base, _dirs, files in os.walk(ROOT):
        if any(x in base for x in ('/tests', '/vault', '/.git', '__pycache__', '/node_modules')):
            continue
        for f in files:
            if f.endswith('.py'):
                src = open(os.path.join(base, f), encoding='utf-8').read()
                if re.search(r'\bstart_backfill\(', src):
                    callers.append(os.path.relpath(os.path.join(base, f), ROOT))
    assert sorted(callers) == ['core/prices_api.py', 'core/prices_store.py']
    api = open(os.path.join(ROOT, 'core', 'prices_api.py'), encoding='utf-8').read()
    assert "pin.pin_error(where='prices_backfill', strict=True)" in api


def test_diario_espera_el_cierre_de_todas_las_bolsas(monkeypatch):
    from core import prices_store
    from ontology import db
    monkeypatch.setattr(db, 'DATABASE_URL', 'postgresql://x/y')
    prices_store._reset_for_tests()
    assert prices_store._daily_due(datetime(2026, 10, 13, 20, 0, tzinfo=timezone.utc)) == (False, 'not_yet')
    assert prices_store._daily_due(datetime(2026, 10, 17, 23, 0, tzinfo=timezone.utc)) == (False, 'not_yet')  # sábado


# ── con base ─────────────────────────────────────────────────────────────────
@pytest.fixture(scope='module')
def db():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from ontology.db import _get_engine, init_schema
    assert init_schema(retries=1)
    yield _get_engine()


@pytest.fixture
def small_catalog(monkeypatch):
    from core import instruments
    tag = str(random.randint(10 ** 6, 10 ** 7))
    nodes = [{'id': f'Co{tag}', 'label': f'Co {tag}', 'mkt': f'T{tag}', 'ticker': f'T{tag} · NYSE'},
             {'id': f'Jp{tag}', 'label': f'Jp {tag}', 'mkt': f'{tag[:4]}.T', 'ticker': f'{tag[:4]} · TSE'}]
    monkeypatch.setattr(instruments, 'catalog_nodes', lambda: nodes)
    return tag, nodes


def _rows(dates, closes, adj=None):
    return [{'date': d, 'open': c, 'high': c, 'low': c, 'close': c, 'adj_close': (adj or closes)[i], 'volume': 5}
            for i, (d, c) in enumerate(zip(dates, closes))]


def test_ingesta_idempotente_y_split_sin_reescribir(db):
    from sqlalchemy import text

    from core import prices_store
    from ontology.db import session_scope
    sym = f'SPL{random.randint(10 ** 6, 10 ** 7)}'
    d = _bdays(30)
    with session_scope() as s:
        r1 = prices_store.ingest_series(s, sym, _rows(d[:25], [400.0] * 25), currency='USD')
    with session_scope() as s:
        r2 = prices_store.ingest_series(s, sym, _rows(d[:25], [400.0] * 25), currency='USD')
    assert r1['inserted'] == 25 and r2 == {'inserted': 0, 'adjustments': 0}
    # split 4:1 el día d[25]: Yahoo re-escribe la historia (÷4); Khipus NO toca sus filas, agrega un factor
    win = d[5:]
    closes = [100.0] * 20 + [101.0] * 5
    with session_scope() as s:
        r3 = prices_store.ingest_series(s, sym, _rows(win, closes), currency='USD')
    assert r3 == {'inserted': 5, 'adjustments': 1}
    with session_scope() as s:
        ser = prices_store.load_series(s, sym)
        raw = s.execute(text('SELECT adj_close FROM prices_eod WHERE instrument_id = :i ORDER BY date LIMIT 1'),
                        {'i': sym}).scalar()
    assert raw == 400.0                                         # lo guardado no cambió
    assert [round(x['adj'], 6) for x in ser] == [100.0] * 25 + [101.0] * 5       # serie continua (sin −75 %)
    # re-bajar la misma ventana otra vez no agrega más factores
    with session_scope() as s:
        assert prices_store.ingest_series(s, sym, _rows(win, closes), currency='USD') == {'inserted': 0, 'adjustments': 0}


@pytest.mark.parametrize('sql', ["UPDATE prices_eod SET close = 1", 'DELETE FROM prices_eod', 'TRUNCATE fx_daily',
                                 'DELETE FROM price_adjustments', "UPDATE metrics_eod SET nrs = 1",
                                 'DELETE FROM positions_eod'])
def test_tablas_de_historia_son_append_only(db, sql):
    from sqlalchemy import text
    k = f'AO{random.randint(10 ** 6, 10 ** 7)}'
    with db.begin() as c:      # una fila en cada tabla (el disparador es por fila: sin filas no hay nada que frenar)
        c.execute(text("INSERT INTO prices_eod (instrument_id, source, date, close, adj_close) VALUES (:k, 't', '2020-01-02', 1, 1)"), {'k': k})
        c.execute(text("INSERT INTO price_adjustments (instrument_id, source, before_date, factor) VALUES (:k, 't', '2020-01-02', 1)"), {'k': k})
        c.execute(text("INSERT INTO metrics_eod (entity_id, date, nrs) VALUES (:k, '2020-01-02', 1)"), {'k': k})
        c.execute(text("INSERT INTO positions_eod (owner_hash, portfolio, instrument_id, date, qty, source) "
                       "VALUES (:k, 'market', 'X', '2020-01-02', 1, 't')"), {'k': k})
    with pytest.raises(Exception) as ei:
        with db.begin() as c:
            c.execute(text(sql))
    assert 'append-only' in str(ei.value)


def _net(dates, calls, fail=()):
    def g(url, params=None, timeout=None):
        sym = url.rsplit('/', 1)[-1]
        calls.append((sym, dict(params or {})))
        if sym in fail:
            return None, 'upstream 404'
        if sym.endswith('USD=X'):
            return _chart(dates, [0.0067 + i * 1e-6 for i in range(len(dates))]), None
        cur = 'JPY' if sym.endswith('.T') else 'USD'
        return _chart(dates, [100.0 + i for i in range(len(dates))], currency=cur), None
    return g


def test_relleno_a_pedido_del_operador_con_decision_progreso_y_reanudable(db, small_catalog):
    from sqlalchemy import text

    from core import identity, prices_store
    from ontology.db import session_scope
    tag, nodes = small_catalog
    prices_store._reset_for_tests()
    d = _bdays(1300, end=date.today() - timedelta(days=1))
    calls = []
    syms = [nodes[0]['mkt'], nodes[1]['mkt'], 'JPYUSD=X']
    st = prices_store.start_backfill(identity.operator('ui', 'Fabrizio'), years=5, symbols=syms,
                                     getter=_net(d, calls), sleep=lambda s: None, threaded=False, interval=0)
    assert st['running'] is False
    b = prices_store.backfill_state()
    # (el JPY puede estar ya cubierto por otra prueba en esta base: entonces cuenta como 'skipped')
    assert b['total'] == 3 and b['done'] == 3 and b['ok'] + b['skipped'] == 3 and b['failed'] == 0
    assert b['rows'] >= 2 * 1290
    assert b['pct'] == 100.0 and b['stopped_reason'] is None
    assert all('period1' in p for _s, p in calls)                    # 5 años por fechas, no "range"
    with session_scope() as s:
        decs = s.execute(text("SELECT principal_id, subject->>'action', parent_id FROM decisions "
                              "WHERE kind = 'data.backfill' AND id = :i OR parent_id = :i ORDER BY recorded_at"),
                         {'i': b['decision_id']}).all()
        n_fx = s.execute(text("SELECT count(*) FROM fx_daily WHERE ccy = 'JPY'")).scalar()
    assert [r[1] for r in decs] == ['start', 'finish']
    assert decs[0][0] == 'op:fabrizio' and decs[1][0] == 'system:prices_backfill'
    assert n_fx >= 1290
    # reanudable: la segunda vez todo está cubierto → no se pide nada a la red
    calls.clear()
    prices_store.start_backfill(identity.operator('ui'), years=5, symbols=syms, getter=_net(d, calls),
                                sleep=lambda s: None, threaded=False, interval=0)
    assert calls == [] and prices_store.backfill_state()['skipped'] == 3


def test_relleno_se_detiene_si_la_fuente_cae(db, small_catalog, monkeypatch):
    from core import identity, prices_store
    tag, nodes = small_catalog
    prices_store._reset_for_tests()
    monkeypatch.setattr(prices_store, 'SOURCE_DOWN_AFTER', 2)
    calls = []
    d = _bdays(30)
    syms = [nodes[0]['mkt'], nodes[1]['mkt'], 'JPYUSD=X']
    prices_store.start_backfill(identity.operator('ui'), years=1, symbols=syms,
                                getter=_net(d, calls, fail={nodes[0]['mkt'], nodes[1]['mkt'], 'JPYUSD=X'}),
                                sleep=lambda s: None, threaded=False, interval=0)
    b = prices_store.backfill_state()
    assert b['stopped_reason'] == 'source_down' and b['failed'] == 2 and b['ok'] == 0


def test_corrida_diaria_guarda_cierres_fx_y_fotos(db, small_catalog, monkeypatch):
    from sqlalchemy import text

    from core import prices_store, world
    from ontology.db import session_scope
    tag, nodes = small_catalog
    prices_store._reset_for_tests()
    owner = f'own{tag}'
    with session_scope() as s:
        s.execute(text("INSERT INTO user_state (owner_hash, key, value, updated_at) VALUES "
                       "(:o, 'eco_pos', CAST(:v AS jsonb), now())"),
                  {'o': owner, 'v': '{"%s": {"sh": 3, "bp": 90}}' % nodes[1]['id']})
    monkeypatch.setattr(world, '_graph', lambda: {'generation': 'g-test', 'nodes': [
        {'id': nodes[0]['id'], 'ticker': nodes[0]['mkt'], 'nrs': 41, 'flow_degree': 2},
        {'id': nodes[1]['id'], 'ticker': nodes[1]['mkt'], 'nrs': 55, 'flow_degree': 1}]})
    calls = []
    d = _bdays(22)
    nxt = d[-1] + timedelta(days=1)
    while nxt.weekday() >= 5:                 # el reloj diario no corre en fin de semana: la prueba fallaba domingos y lunes
        nxt += timedelta(days=1)
    run_day = datetime.combine(nxt, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=23)
    monkeypatch.setattr(prices_store, '_targets', lambda s, symbols=None: ([nodes[0]['mkt'], nodes[1]['mkt']], ['JPY']))
    res = prices_store.run_daily(now=run_day, getter=_net(d, calls), sleep=lambda s: None, broker=False)
    assert res['failed'] == 0 and res['ok'] == 3 and res['snapshot']['metrics'] >= 2
    assert all(p.get('range') == '1mo' for _s, p in calls)
    with session_scope() as s:
        m = s.execute(text('SELECT nrs, close, currency, price_usd FROM metrics_eod WHERE entity_id = :e AND date = :d'),
                      {'e': nodes[1]['id'], 'd': run_day.date()}).first()
        p = s.execute(text('SELECT qty, price, currency, price_usd, value_usd, source FROM positions_eod '
                           'WHERE owner_hash = :o'), {'o': owner}).first()
        fx_day = s.execute(text("SELECT rate_to_usd FROM fx_daily WHERE ccy = 'JPY' AND date <= :d "
                                "ORDER BY date DESC LIMIT 1"), {'d': run_day.date()}).scalar()
    assert m[0] == 55 and m[1] == 121.0 and m[2] == 'JPY'
    assert m[3] == pytest.approx(121.0 * fx_day, rel=1e-9)                       # convertido con el FX de ESE día
    assert p[0] == 3 and p[5] == 'user_state:eco_pos' and p[4] == pytest.approx(3 * m[3], rel=1e-9)
    # la foto del día ya existe → el reloj no vuelve a bajar todo tras un reinicio
    prices_store._reset_for_tests()
    assert prices_store._daily_due(run_day) == (False, 'done_today')


def test_api_relleno_exige_pin_y_muestra_progreso(db, monkeypatch):
    from flask import Flask

    from core import pin, prices_store
    from core.prices_api import prices_bp
    app = Flask(__name__)
    app.register_blueprint(prices_bp)
    c = app.test_client()
    pin._reset_for_tests()
    monkeypatch.setenv('TRADE_PIN', '4321')
    started = {}
    monkeypatch.setattr(prices_store, 'start_backfill', lambda principal, years=5, symbols=None: started.update(
        who=principal.id, years=years) or prices_store.backfill_state())
    assert c.post('/api/prices/backfill', json={'years': 5}).status_code in (401, 403)
    assert not started
    r = c.post('/api/prices/backfill', json={'years': 9}, headers={'X-Trade-Pin': '4321'})
    assert r.status_code == 200 and started == {'who': 'op:fabrizio', 'years': 9}   # el tope (5) lo pone el servicio
    g = c.get('/api/prices/backfill').get_json()
    assert {'done', 'total', 'pct', 'running', 'errors'} <= set(g)
    st = c.get('/api/prices/status').get_json()
    assert st['db'] is True and 'rows' in st
    rv = c.get('/api/instruments/review').get_json()
    # la ruta cuenta sobre el grafo VIGENTE (con el lote L aplicado en esta base: 33/23); el catálogo del repo, 21/25
    from core import instruments
    now = instruments.review_list()
    assert (rv['multi_listed'], rv['otc_adr']) == (sum(r['review'] == 'multi_listed' for r in now),
                                                   sum(r['review'] == 'otc_adr' for r in now))
    import json as _json
    snap = _json.load(open(os.path.join(ROOT, 'data', 'grafo_v0.json'), encoding='utf-8'))['nodes']
    rs = instruments.review_list(snap)
    assert sum(r['review'] == 'multi_listed' for r in rs) == 21 and sum(r['review'] == 'otc_adr' for r in rs) == 25  # lote K
    pin._reset_for_tests()


def test_base_caida_no_frena_cada_lectura(monkeypatch):
    """Con DATABASE_URL pero la base caída, tras UN fallo las lecturas se saltan 60 s (respaldo en vivo inmediato)."""
    from core import prices_store
    from ontology import db as odb
    prices_store._reset_for_tests()
    monkeypatch.setattr(odb, 'DATABASE_URL', 'postgresql://x/y')
    calls = []

    def boom(*a, **k):
        calls.append(1)
        raise RuntimeError('db down')
    monkeypatch.setattr(odb, 'session_scope', boom)
    assert prices_store.history('NVDA', '1y') is None and prices_store._reads_paused()
    assert prices_store.history('NVDA', '1y') is None and prices_store.fx_history('JPY', '1y') is None
    assert len(calls) == 1
    prices_store._reset_for_tests()


# ── revisión batch E: huecos, cierres viejos, zona horaria real, series sin ajustar ─────────────────────────────
def test_fecha_con_la_zona_horaria_real_de_la_bolsa_no_el_desfase_de_hoy():
    """FX de Londres a las 00:00 BST = 23:00 UTC del día anterior: con el gmtoffset de invierno (0) las filas de
    verano quedaban un día antes (lunes fechado domingo)."""
    from core import prices_store
    ts = [int(datetime(2026, 6, 28, 23, 0, tzinfo=timezone.utc).timestamp()),
          int(datetime(2026, 6, 29, 23, 0, tzinfo=timezone.utc).timestamp()),
          int(datetime(2026, 12, 1, 0, 0, tzinfo=timezone.utc).timestamp())]
    chart = {'chart': {'result': [{'timestamp': ts, 'meta': {
        'currency': 'USD', 'gmtoffset': 0, 'exchangeTimezoneName': 'Europe/London',
        'currentTradingPeriod': {'regular': {'start': 0, 'end': 1}}},
        'indicators': {'quote': [{'close': [0.031, 0.0311, 0.0312]}]}}]}}
    got = prices_store.fetch_chart('TWDUSD=X', getter=lambda u, params=None, timeout=None: (chart, None),
                                   now=datetime(2026, 12, 15, 22, 30, tzinfo=timezone.utc), years=5)
    assert [r['date'] for r in got['rows']] == [date(2026, 6, 29), date(2026, 6, 30), date(2026, 12, 1)]
    # sin adjclose de Yahoo: el ajustado queda VACÍO (al leer vale el cierre y la serie sale "sin ajustar")
    assert all(r['adj_close'] is None for r in got['rows'])


def test_una_serie_con_un_hueco_de_meses_no_se_da_por_completa():
    from core import prices_store
    today = date(2026, 10, 13)
    d = _bdays(261, end=today - timedelta(days=1))
    rows = [{'date': x} for x in d]
    start = today - timedelta(days=366)
    assert prices_store._covers(rows, start, today, 366)
    holed = [r for r in rows if not (date(2026, 3, 26) <= r['date'] <= date(2026, 6, 26))]
    assert len(holed) >= int(366 * 252 / 365 * 0.55)        # pasaba el conteo de filas…
    assert not prices_store._covers(holed, start, today, 366)                    # …pero tiene un hueco de 3 meses
    assert prices_store.max_gap_days(r['date'] for r in rows) <= 4


def test_historia_con_hueco_no_se_lee_y_el_relleno_lo_completa(db, small_catalog):
    from core import identity, prices_store
    from ontology.db import session_scope
    tag, nodes = small_catalog
    prices_store._reset_for_tests()
    sym = nodes[0]['mkt']
    d = _bdays(262, end=date.today() - timedelta(days=1))
    hole = set(d[60:125])
    with session_scope() as s:
        prices_store.ingest_series(s, sym, _rows([x for x in d if x not in hole],
                                                 [100.0 + i for i, x in enumerate(d) if x not in hole]), 'USD')
    assert prices_store.history(sym, '1y') is None                   # con el hueco → en vivo, no la base
    calls = []
    prices_store.start_backfill(identity.operator('ui'), years=1, symbols=[sym], getter=_net(d, calls),
                                sleep=lambda s: None, threaded=False, interval=0)
    assert [c for c, _p in calls] == [sym]                           # no lo saltó por "ya cubierto"
    got = prices_store.history(sym, '1y')
    assert got is not None and got[2]['n'] >= 250 and got[2]['adjusted'] is True


def test_foto_diaria_no_usa_un_cierre_viejo_y_lo_sin_ajustar_se_marca(db):
    from core import prices_store
    from ontology.db import session_scope
    sym = f'OLD{random.randint(10 ** 6, 10 ** 7)}'
    with session_scope() as s:
        prices_store.ingest_series(s, sym, _rows([date(2023, 3, 1)], [50.0]), 'USD')
        assert prices_store._last_close(s, sym, date.today()) == (None, None, None)
        assert prices_store._last_close(s, sym, date(2023, 3, 3))[0] == 50.0
    raw = f'RAW{random.randint(10 ** 6, 10 ** 7)}'
    d = _bdays(262, end=date.today() - timedelta(days=1))
    rows = _rows(d, [10.0 + i * 0.01 for i in range(len(d))])
    for r in rows[-5:]:
        r['adj_close'] = None                                        # Yahoo sin adjclose
    with session_scope() as s:
        prices_store.ingest_series(s, raw, rows, 'USD')
    h = prices_store.history(raw, '1y')
    assert h is not None and h[2]['adjusted'] is False
    assert h[0][d[-1].isoformat()] == rows[-1]['close']               # vale el cierre crudo


def test_diario_repara_un_atraso_mayor_a_un_mes(db, small_catalog):
    from core import prices_store
    from ontology.db import session_scope
    tag, nodes = small_catalog
    sym = nodes[0]['mkt']
    old = _bdays(40, end=date.today() - timedelta(days=60))
    with session_scope() as s:
        prices_store.ingest_series(s, sym, _rows(old, [5.0] * len(old)), 'USD')
    calls = []
    st = {'stop': False}
    prices_store._run(st, rng='1mo', symbols=[sym], getter=_net(_bdays(90), calls), sleep=lambda s: None,
                      interval=0)
    assert calls and calls[0][1].get('range') == '3mo' and st['repaired'] == 1
