"""tests/test_live_universe.py — lote L (2026-10-15): UN universo de cotizaciones para lo en vivo y la historia.

  · `core.instruments.universe()` = el grafo vigente (catálogo + empresas importadas a Postgres): primario = `mkt`, o el
    listado `is_primary` de props.listings[], o ids.yahoo_symbol si la ficha no declara listados; un símbolo una sola
    vez (gana el primer dueño, el conflicto se lista); símbolos imposibles fuera; listados dados de baja marcados;
  · con el catálogo del repo el universo es EXACTAMENTE el de hoy (568 símbolos = `mkt`; nada cambia solo);
  · core/live_caps (capitalización y precio), core/live_fundamentals y core/prices_store (historia diaria) leen ese
    universo; los símbolos NUEVOS entran por tandas (`phase_in`: 120 por ciclo en vivo, 500 por corrida diaria);
  · el lote de Yahoo nunca hace más de 15 pedidos por minuto (el presupuesto de hoy), por grande que sea el universo;
  · la capitalización viene SOLO de la fuente en vivo: nada del universo trae cifras de mercado de la ficha.
Sin red, sin base (lo de Postgres va en tests/test_live_universe_db.py)."""
import json
import math
import os
import sys
from datetime import date

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('KHIPU_SCHEDULER', 'off')


@pytest.fixture(scope='module')
def catalog():
    with open(os.path.join(ROOT, 'data', 'grafo_v0.json'), encoding='utf-8') as fh:
        return json.load(fh)['nodes']


def _imp(nid, **kw):
    n = {'id': nid, 'label': nid, 'imported': True}
    n.update(kw)
    return n


# ── el universo ─────────────────────────────────────────────────────────────────────────────────────────────────
def test_con_el_catalogo_el_universo_es_el_de_hoy(catalog):
    from core import instruments as I
    u = I.universe(catalog)
    today = {n['id']: n['mkt'].strip().upper() for n in catalog if n.get('mkt')}
    assert len(today) == len(set(today.values())) == 568
    assert I.live_symbols(catalog) == today                        # mismo mapa id → símbolo que live_caps usaba
    assert u['conflicts'] == [] and u['invalid'] == []
    assert all(e['origin'] == 'catalog' for e in u['primary'] + u['secondary'])
    # secundarios declarados: 2330.TW (TSMC) y 186A.T (Astroscale) se bajan; TOELY/AJINY/SMNEY están dados de baja
    sec = {e['symbol']: e['delisted'] for e in u['secondary']}
    assert sec == {'2330.TW': False, 'TOELY': True, 'AJINY': True, 'SMNEY': True, '186A.T': False}
    eod = I.eod_symbols(catalog)
    assert len(eod['equities']) == 568 + 2 and 'TOELY' not in eod['equities']
    assert eod['currencies'] >= {'JPY', 'TWD', 'GBP', 'EUR'} and 'USD' not in eod['currencies']
    # la siembra de la tabla usa el MISMO recorrido: un primario por símbolo, los 5 secundarios
    assert [i['id'] for i in I.from_catalog(catalog)] == [e['symbol'] for e in u['primary']]
    assert {i['id'] for i in I.secondary_from_catalog(catalog)} == set(sec)


def test_empresas_importadas_entran_con_su_listado_principal(catalog):
    from core import instruments as I
    extra = [
        # base (no importada), sin mkt: Incorporada a mano → antes que las importadas
        {'id': 'ZDbOnly', 'label': 'Db only', 'mkt': 'ZDBO'},
        _imp('Moutai', listings=[
            {'symbol': '600519', 'mic': 'XSHG', 'yahoo_symbol': '600519.SS', 'is_primary': True, 'kind': 'a_share',
             'currency': 'CNY'},
            {'symbol': 'KWEIY', 'mic': 'OTCM', 'yahoo_symbol': 'KWEIY', 'is_primary': False, 'kind': 'adr',
             'currency': 'USD'},
            {'symbol': 'OLD', 'mic': 'OTCM', 'yahoo_symbol': 'OLDQY', 'is_primary': False, 'kind': 'adr',
             'currency': 'USD', 'delisted_at': '2024-03'},
            {'symbol': 'FUT', 'mic': 'OTCM', 'yahoo_symbol': 'FUTQY', 'is_primary': False, 'kind': 'adr',
             'currency': 'USD', 'delisted_at': '2099-01-01'}]),
        _imp('BWX', mkt='BWXT', listings=[{'symbol': 'BWXT', 'mic': 'XNYS', 'yahoo_symbol': 'BWXT', 'is_primary': True,
                                           'kind': 'equity', 'currency': 'USD'}]),
        _imp('NvidiaClone', mkt='NVDA'),                             # mismo símbolo que Nvidia → conflicto, gana Nvidia
        _imp('Ericsson2', mkt='ERIC B'),                             # símbolo imposible para Yahoo → fuera
        _imp('OnlyIds', ids={'yahoo_symbol': 'onid.l'}),             # sin listados: el identificador de la ficha
        _imp('DepOnly', ids={'yahoo_symbol': 'DEPO'}, listings=[    # solo certificados, ninguno principal → sin precio
            {'symbol': 'DEPO', 'mic': 'OTCM', 'yahoo_symbol': 'DEPO', 'is_primary': False, 'kind': 'adr'}]),
        _imp('PTTx', listings=[{'symbol': 'PTT', 'mic': 'XBKK', 'yahoo_symbol': 'PTT.BK', 'is_primary': True,
                                'kind': 'equity', 'currency': 'THB'}]),
    ]
    nodes = list(catalog) + extra
    u = I.universe(nodes, today=date(2026, 10, 15))
    prim = {e['symbol']: e for e in u['primary']}
    assert prim['600519.SS']['company_id'] == 'Moutai' and prim['600519.SS']['origin'] == 'new'
    assert prim['BWXT']['imported'] is True and prim['ONID.L']['company_id'] == 'OnlyIds'
    assert prim['PTT.BK']['currency'] == 'THB'                       # sufijo que SUFFIX no conoce: moneda de la ficha
    assert 'DEPO' not in prim                                         # honra «sin precio en vivo hasta revisarla»
    assert prim['NVDA']['company_id'] == 'Nvidia'
    assert u['conflicts'] == [{'symbol': 'NVDA', 'owner': 'Nvidia', 'other': 'NvidiaClone'}]
    assert u['invalid'] == [{'company_id': 'Ericsson2', 'symbol': 'ERIC B', 'role': 'primary'}]
    sec = {e['symbol']: e['delisted'] for e in u['secondary'] if e['company_id'] == 'Moutai'}
    assert sec == {'KWEIY': False, 'OLDQY': True, 'FUTQY': False}
    # prioridad: catálogo del repo → otros nodos de la base → importados
    order = [e['symbol'] for e in u['primary']]
    assert order[:568] == [e['symbol'] for e in I.universe(catalog)['primary']]
    assert order.index('ZDBO') == 568 and order.index('600519.SS') > order.index('ZDBO')
    live = I.live_symbols(nodes, today=date(2026, 10, 15))
    assert live['Moutai'] == '600519.SS' and 'NvidiaClone' not in live and 'Ericsson2' not in live
    assert len(live) == len(set(live.values())) == 568 + 5      # ZDBO, 600519.SS, BWXT, ONID.L, PTT.BK
    eod = I.eod_symbols(nodes, today=date(2026, 10, 15))
    assert {'KWEIY', 'FUTQY', 'PTT.BK'} <= set(eod['equities']) and 'OLDQY' not in eod['equities']
    assert {'CNY', 'THB'} <= eod['currencies']
    rows = {r['id']: r for r in I.all_instruments(nodes)}
    assert rows['600519.SS']['source'] == 'import' and rows['ZDBO']['source'] == 'catalog'
    assert rows['PTT.BK']['currency'] == 'THB' and 'THBUSD=X' in rows
    assert rows['OLDQY']['note']['delisted_at'] == '2024-03'        # sembrado (pedido explícito posible), no a diario
    # cifras de mercado: el universo no lleva NINGUNA (capitalización y acciones salen del perfil en vivo)
    for e in u['primary'] + u['secondary']:
        assert not ({'mcap_b', 'mktcap_b', 'market_cap', 'shares_outstanding', 'price'} & set(e))
    # la lista de revisión de Fabrizio es para dudas del CATÁLOGO, no para la principal que eligió una ficha
    assert 'Moutai' not in {r['id'] for r in I.review_list(nodes)}


def test_baja_de_un_listado():
    from core.instruments import listing_delisted as D
    t = date(2026, 10, 15)
    assert D({'note': 'ADR OTC: el agregador lo marca dado de baja; verificar'}, t)
    assert D({'delisted_at': '2026-10-15'}, t) and D({'delisted_at': '2025'}, t) and D({'delisted_at': '2026-10'}, t)
    assert not D({'delisted_at': '2026-10-16'}, t) and not D({'delisted_at': '2027'}, t)
    assert D({'delisted_at': 'sí, en algún momento'}, t)             # dice que se dio de baja: no se baja a diario
    assert not D({}, t) and not D(None, t) and not D({'note': 'cotización local (home)'}, t)


def test_tandas_de_simbolos_nuevos():
    from core.instruments import phase_in
    base = {'A', 'B'}
    syms = ['A', 'B'] + [f'N{i}' for i in range(10)]
    inc, now, pend = phase_in(syms, set(), 3, baseline=base)
    assert inc == ['A', 'B', 'N0', 'N1', 'N2'] and now == ['N0', 'N1', 'N2'] and len(pend) == 7
    inc, now, pend = phase_in(syms, {'N0', 'N1', 'N2'}, 3, baseline=base)
    assert now == ['N3', 'N4', 'N5'] and inc[:2] == ['A', 'B'] and len(inc) == 2 + 6
    # la ventana rota: en len(nuevos)/límite ciclos TODOS tuvieron turno aunque ninguno se admita para siempre
    seen = set()
    for k in range(4):
        seen |= set(phase_in(syms, set(), 3, baseline=base, offset=k * 3)[1])
    assert seen == {f'N{i}' for i in range(10)}
    # sin catálogo legible no se frena nada (nunca dejar el mapa sin precios)
    assert phase_in(syms, set(), 3, baseline=frozenset())[0] == syms


# ── en vivo: capitalización y precio (core/live_caps) ───────────────────────────────────────────────────────────
class _Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


def _yahoo(monkeypatch, clock, log):
    from core import quotes as Q

    class R:
        status_code = 200

        def __init__(self, syms):
            self.syms = syms

        def json(self):
            return {'quoteResponse': {'result': [{'symbol': s, 'marketCap': 2.0e10, 'currency': 'USD',
                                                  'regularMarketPrice': 12.5} for s in self.syms]}}

    class S:
        def get(self, url, params=None, timeout=None):
            syms = params['symbols'].split(',')
            log.append((clock.t, len(syms)))
            clock.t += 0.4
            return R(syms)
    monkeypatch.setattr(Q, '_yahoo_session', lambda: (S(), 'crumb'))
    monkeypatch.setattr(Q, '_fx_to_usd', lambda cur: 1.0)


def _max_per_window(stamps, window=60.0):
    return max((sum(1 for u in stamps if t <= u < t + window) for t in stamps), default=0)


def test_el_lote_de_yahoo_nunca_pasa_15_pedidos_por_minuto(monkeypatch):
    from core import quotes as Q
    clk, log = _Clock(), []
    _yahoo(monkeypatch, clk, log)
    lim = Q.WindowLimiter(Q.YAHOO_BATCH_PER_MIN, 60.0, clock=clk, sleep=clk.sleep)
    syms = [f'S{i:04d}' for i in range(4700)]                       # el universo con el lote 1 entero
    out = Q.fetch_quotes_batch_yahoo(syms, limiter=lim)
    assert len(out) == 4700 and all(r['mcap_b'] == 20.0 for r in out.values())
    assert len(log) == lim.count == math.ceil(4700 / Q.YAHOO_BATCH_CHUNK) == 118
    assert _max_per_window([t for t, _n in log]) == 15            # nunca más que hoy (15 pedidos seguidos)
    assert log[15][0] >= 60.0 and lim.waited_s > 0                # el 16.º espera su minuto: se alarga, no se acelera
    assert Q.YAHOO_BATCH_LIMITER.per_window == 15 and Q.YAHOO_BATCH_LIMITER.window_s == 60.0


def test_live_caps_suma_lo_nuevo_por_tandas_y_cuenta_pedidos(monkeypatch, catalog):
    from core import live_caps as LC
    from core import quotes as Q
    base = {n['id']: n['mkt'].strip().upper() for n in catalog if n.get('mkt')}
    new = {f'Imp{i:03d}': f'ZQ{i:03d}.SS' for i in range(300)}
    monkeypatch.setattr(LC, '_symbols_by_id', lambda: {**base, **new})
    monkeypatch.setattr(LC, '_daily_outcomes', lambda: None)
    clk, log = _Clock(), []
    _yahoo(monkeypatch, clk, log)
    lim = Q.WindowLimiter(Q.YAHOO_BATCH_PER_MIN, 60.0, clock=clk, sleep=clk.sleep)
    LC._PHASE['admitted'].clear()
    LC._STATE.update(caps={}, as_of=None, ts=0.0, running=False, error=None, cycle=None)
    seen = []
    try:
        for _cycle in range(4):
            log.clear()
            LC.refresh(fetch=lambda syms: Q.fetch_quotes_batch_yahoo(syms, limiter=lim))
            st = LC.get_caps(start=False)
            seen.append((st['cycle']['symbols'], st['cycle']['requests'], len(log), st['cycle']['new_admitted'],
                         st['universe']['pending'], st['n']))
            assert _max_per_window([t for t, _n in log]) <= 15
            clk.t += 15 * 60
    finally:
        LC._PHASE['admitted'].clear()
        LC._STATE.update(caps={}, as_of=None, ts=0.0, running=False, error=None, cycle=None)
    n0 = len(base)
    assert seen == [(n0 + 120, math.ceil((n0 + 120) / 40), math.ceil((n0 + 120) / 40), 120, 180, n0 + 120),
                    (n0 + 240, math.ceil((n0 + 240) / 40), math.ceil((n0 + 240) / 40), 120, 60, n0 + 240),
                    (n0 + 300, math.ceil((n0 + 300) / 40), math.ceil((n0 + 300) / 40), 60, 0, n0 + 300),
                    (n0 + 300, math.ceil((n0 + 300) / 40), math.ceil((n0 + 300) / 40), 0, 0, n0 + 300)]
    assert seen[0][1] - math.ceil(n0 / 40) == 3                    # primer ciclo tras importar: +3 pedidos, no ráfaga


def test_live_caps_y_fundamentales_leen_el_mismo_universo(monkeypatch):
    from core import instruments as I
    from core import live_caps as LC
    from core import live_fundamentals as LF
    monkeypatch.setattr(I, 'live_symbols', lambda nodes=None, today=None: {'Moutai': '600519.SS'})
    assert LC._symbols_by_id() == {'Moutai': '600519.SS'} == LF._universe()


def test_capitalizacion_solo_de_la_fuente_en_vivo(monkeypatch):
    """Una empresa importada sin dato de Yahoo NO tiene capitalización (nunca se toma de la ficha ni se inventa)."""
    from core import live_caps as LC
    monkeypatch.setattr(LC, '_symbols_by_id', lambda: {'Nvidia': 'NVDA', 'Moutai': '600519.SS'})
    monkeypatch.setattr(LC, '_daily_outcomes', lambda: None)
    LC._PHASE['admitted'].clear()
    LC._STATE.update(caps={}, as_of=None, ts=0.0, running=False, error=None, cycle=None)
    try:
        LC.refresh(fetch=lambda syms: {'NVDA': {'mcap_b': 4500.0, 'price': 180.0, 'currency': 'USD'}})
        st = LC.get_caps(start=False)
        assert st['caps']['Nvidia']['mcap_b'] == 4500.0 and 'Moutai' not in st['caps']
        assert st['cycle']['symbols'] == 2 and st['cycle']['with_data'] == 1
    finally:
        LC._PHASE['admitted'].clear()
        LC._STATE.update(caps={}, as_of=None, ts=0.0, running=False, error=None, cycle=None)


# ── historia diaria (core/prices_store) ─────────────────────────────────────────────────────────────────────────
class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Sess:
    """Sesión falsa: la tabla `instruments` y qué símbolos ya tienen historia."""

    def __init__(self, rows, have=()):
        self.rows, self.have = rows, set(have)

    def execute(self, stmt, params=None):
        if 'prices_eod' in str(stmt):
            return _Rows([(s,) for s in (params or {}).get('ids') or [] if s in self.have])
        return _Rows(self.rows)


def test_la_historia_diaria_baja_solo_el_universo_vigente(monkeypatch):
    from core import instruments as I
    from core import prices_store as PS
    monkeypatch.setattr(I, 'seed', lambda session, nodes=None: None)
    monkeypatch.setattr(I, 'eod_symbols', lambda nodes=None, today=None: {
        'equities': ['NVDA', '8035.T', '600519.SS', '2330.TW', 'KWEIY'], 'currencies': {'JPY', 'CNY', 'TWD'}})
    rows = [('600519.SS', 'equity', 'CNY', {}, True), ('8035.T', 'equity', 'JPY', {}, True),
            ('HXSCL', 'otc', 'USD', {}, True),                       # símbolo viejo corregido: ya no está en el grafo
            ('ZZROLL.SS', 'equity', 'CNY', {}, True),                # importación deshecha: queda en la tabla
            ('2330.TW', 'equity', 'TWD', {'primary': 'TSM'}, False), ('KWEIY', 'adr', 'USD', {'primary': '600519.SS'}, False),
            ('NVDA', 'equity', 'USD', {}, True), ('SPY', 'etf', 'USD', None, True), ('^IRX', 'rate', 'USD', None, True),
            ('JPYUSD=X', 'fx', 'USD', {'ccy': 'JPY'}, True), ('CNYUSD=X', 'fx', 'USD', {'ccy': 'CNY'}, True),
            ('KRWUSD=X', 'fx', 'USD', {'ccy': 'KRW'}, True)]
    eq, fx = PS._targets(_Sess(rows))
    assert eq == ['SPY', '^IRX', 'NVDA', '8035.T', '600519.SS', '2330.TW', 'KWEIY']   # orden del universo
    assert fx == ['JPY', 'CNY']                                       # KRW ya no hace falta
    eq2, fx2 = PS._targets(_Sess(rows), symbols=['zzroll.ss', 'KRWUSD=X'])           # a pedido: lo pedido
    assert eq2 == ['ZZROLL.SS'] and fx2 == ['KRW']
    # sin universo legible: la tabla entera, como antes
    monkeypatch.setattr(I, 'eod_symbols', lambda nodes=None, today=None: {'equities': [], 'currencies': set()})
    eq3, fx3 = PS._targets(_Sess(rows))
    assert 'HXSCL' in eq3 and 'ZZROLL.SS' in eq3 and len(fx3) == 3


def test_corrida_diaria_por_tandas(monkeypatch):
    from datetime import datetime, timezone

    from core import instruments as I
    from core import prices_store as PS
    base = frozenset({'SPY', '^IRX', 'NVDA'})
    monkeypatch.setattr(I, 'baseline_symbols', lambda: base)
    monkeypatch.setattr(PS, 'NEW_PER_DAILY_RUN', 4)
    new = [f'N{i}' for i in range(10)]
    eq = ['SPY', '^IRX', 'NVDA'] + new
    now = datetime(2026, 10, 15, 23, tzinfo=timezone.utc)
    out, ph = PS._phase_daily(_Sess([], have={'N7'}), eq, now)
    assert out[:3] == ['SPY', '^IRX', 'NVDA'] and 'N7' in out          # con historia: entra siempre
    assert ph == {'new': 10, 'with_history': 1, 'admitted': 4, 'pending': 5} and len(out) == 3 + 1 + 4
    # días seguidos: la ventana rota, todos los nuevos tienen turno aunque ninguno traiga datos
    seen = set()
    for k in range(3):
        o, _p = PS._phase_daily(_Sess([]), eq, datetime(2026, 10, 15 + k, 23, tzinfo=timezone.utc))
        seen |= set(o) - set(base)
    assert seen == set(new)
    # sin nuevos no se consulta nada y no cambia nada
    assert PS._phase_daily(_Sess([]), ['SPY', 'NVDA'], now) == (['SPY', 'NVDA'], {'new': 0, 'admitted': 0,
                                                                               'pending': 0, 'with_history': 0})
