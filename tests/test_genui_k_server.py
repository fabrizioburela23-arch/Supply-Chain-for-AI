"""tests/test_genui_k_server.py — RESPUESTAS VISUALES, lote K (2026-10-14): lo que Fabrizio vio con GENUI=on en producción
(«muéstrame las ganancias de nvidia en un gráfico»), lado servidor. Sin red: la IA es un guion y los estados financieros
son la muestra grabada tests/fixtures/genui/tools/get_fundamentals__nvda.json.

  1. get_fundamentals (mcp_server/ops.py): estados por período con márgenes y crecimiento, fuente y as_of; sin fuente →
     'unavailable' honesto (nunca inventa); trimestral desde Yahoo (parser puro sobre un payload sintético);
     constructor → chart.bar (ingresos por período) + metric.tiles (márgenes del último período) + barra de utilidad;
     la pregunta «ganancias de nvidia en un gráfico» produce ese bloque principal (y la IA ya no puede decir que no
     tiene la serie: la receta está en el system).
  5. la prosa NO lleva nombres internos: «(get_company, Yahoo, hoy 2026-10-14)» → «(Grafo Khipus, Yahoo, hoy …)».
  E2.9. la ficha (core/hotviews/views/card.py) expone market_position[] y facilities[] de las propiedades del objeto
     (Postgres de prueba) y rank_by_market responde «¿cuál es la empresa de baterías más grande?» desde ahí; sin
     datos dice «no tengo ese ranking».
"""
import copy
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

from core import ai as core_ai  # noqa: E402
from core import genui  # noqa: E402
from core import khipu_chat as kc  # noqa: E402
from core.genui import builders as B  # noqa: E402
from core.genui import layout as L  # noqa: E402
from core.genui import validate as V  # noqa: E402
from mcp_server import ops  # noqa: E402

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')
FIX_FUND = os.path.join(ROOT, 'tests', 'fixtures', 'genui', 'tools', 'get_fundamentals__nvda.json')
FIX_MKT = os.path.join(ROOT, 'tests', 'fixtures', 'genui', 'tools', 'rank_by_market__lithium.json')


def _load(p):
    with open(p, encoding='utf-8') as fh:
        return json.load(fh)


class FakeAI:
    def __init__(self, script):
        self.script = list(script)
        self.prompts = []

    def __call__(self, system, prompt, max_tokens=1000, tier='fast', model=None, verify_numbers=True, **kw):
        self.prompts.append((system, prompt))
        item = self.script.pop(0) if self.script else {'final': {'answer': 'Listo.', 'actions': []}}
        return (item if isinstance(item, str) else json.dumps(item)), 'fake:model'


def _fin_from_fixture():
    """La estructura normalizada de core/company_data que produce EXACTAMENTE la muestra grabada."""
    doc = _load(FIX_FUND)
    rows = doc['result']['periods']
    fin = {'available': True, 'source': doc['result']['source'], 'currency': 'USD', 'reason': None, 'reason_en': None,
           'years': [r['period'][2:] for r in rows], 'tried': ['yahoo'], 'fx_rate': None}
    for k in ('revenue', 'gross_profit', 'operating_income', 'net_income', 'fcf'):
        fin[k] = [r[k] for r in rows]
    for k in ('total_debt', 'cash', 'equity', 'shares', 'ebitda', 'eps', 'ev_to_sales', 'capex', 'invested_capital',
              'roe', 'roic', 'pe'):
        fin[k] = [None] * len(rows)
    return fin


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    from mcp_server import tools as mt
    monkeypatch.setattr(mt, '_live_profile', lambda sym: {'available': False, 'reason': 'test (offline)'})
    monkeypatch.setattr(mt._auth, 'db_available', lambda: False)
    monkeypatch.setattr(core_ai, '_ai_configured', lambda: True)
    monkeypatch.setattr(ops, '_annual_financials', lambda sym: copy.deepcopy(_fin_from_fixture()))
    genui.reset_stats()


# ── 1. get_fundamentals ──────────────────────────────────────────────────────────────────────────────────────────
def test_get_fundamentals_herramienta_en_el_chat_y_en_el_system():
    names = kc.tool_names()
    assert 'get_fundamentals' in names and 'rank_by_market' in names
    sysmsg = kc.build_system('es')
    assert 'get_fundamentals(id_or_ticker' in sysmsg and 'rank_by_market(market' in sysmsg
    assert 'PROHIBIDO escribir nombres internos' in sysmsg
    assert kc.tool_agent('get_fundamentals') == 'analista'


def test_get_fundamentals_da_la_serie_con_margenes_y_fuente():
    ok, res = kc.execute_tool('get_fundamentals', {'id_or_ticker': 'Nvidia', 'period': 'annual', 'years': 5})
    assert ok, res
    assert res['symbol'] == 'NVDA' and res['id'] == 'Nvidia' and res['n'] == 5 and res['source'] == 'yahoo'
    assert res['source_label'] == 'Yahoo Finance' and res['as_of'] and res['unit'] == 'USD'
    last = res['latest']
    fx = _load(FIX_FUND)['result']['latest']
    for k in ('revenue', 'net_income', 'gross_margin_pct', 'operating_margin_pct', 'net_margin_pct', 'revenue_growth_pct'):
        assert last[k] == fx[k], k
    # márgenes = cifra / ingresos (solo con ingresos > 0); crecimiento = contra el año fiscal ANTERIOR consecutivo
    assert last['net_margin_pct'] == round(100 * last['net_income'] / last['revenue'], 1)
    assert res['periods'][0]['revenue_growth_pct'] is None                  # el primero no tiene con qué compararse
    assert ops._growth(10.0, 0) is None and ops._pct(5.0, -1.0) is None     # base ≤ 0: sin cifra
    # years=2 recorta por la cola (los más recientes)
    ok, r2 = kc.execute_tool('get_fundamentals', {'id_or_ticker': 'NVDA', 'years': 2})
    assert ok and [r['period'] for r in r2['periods']] == ['FY2024', 'FY2025']


def test_get_fundamentals_sin_fuente_es_unavailable_y_privada_no_data(monkeypatch):
    monkeypatch.setattr(ops, '_annual_financials', lambda sym: {'available': False, 'reason_en': 'no key', 'tried': []})
    ok, res = kc.execute_tool('get_fundamentals', {'id_or_ticker': 'Nvidia'})
    assert not ok and res.get('code') == 'unavailable' and 'unavailable' in res['error']
    ok, res = kc.execute_tool('get_fundamentals', {'id_or_ticker': 'OpenAI'})     # privada: sin ticker
    assert not ok and res.get('code') == 'no_data'


def _q_payload(rows):
    """Payload sintético de Yahoo fundamentals-timeseries (trimestral)."""
    res = []
    for typ, field in ops._Q_TYPES.items():
        res.append({'meta': {'type': [typ]}, typ: [{'asOfDate': d, 'reportedValue': {'raw': v[field]}, 'currencyCode': 'USD'}
                                                   for d, v in rows if v.get(field) is not None]})
    return {'timeseries': {'result': res}}


def test_get_fundamentals_trimestral_desde_yahoo(monkeypatch):
    from core import company_data as cd
    rows = [('2025-04-30', {'revenue': 44.1e9, 'gross_profit': 26.7e9, 'operating_income': 21.6e9, 'net_income': 18.8e9, 'ocf': 27.4e9, 'capex': -1.2e9}),
            ('2025-07-31', {'revenue': 46.7e9, 'gross_profit': 33.8e9, 'operating_income': 28.4e9, 'net_income': 26.4e9, 'fcf': 13.5e9})]
    monkeypatch.setattr(cd, '_yahoo_get', lambda url, params=None, timeout=None: (_q_payload(rows), None))
    ops._Q_CACHE.clear()
    ok, res = kc.execute_tool('get_fundamentals', {'id_or_ticker': 'Nvidia', 'period': 'quarterly'})
    assert ok, res
    assert res['period'] == 'quarterly' and res['n'] == 2 and res['source'] == 'yahoo'
    q1, q2 = res['periods']
    assert q1['period'] == 'Q 2025-04-30' and q1['fcf'] == 27.4e9 - 1.2e9          # FCF = OCF − |CapEx|
    assert q2['revenue_growth_pct'] == round((46.7 / 44.1 - 1) * 100, 1) and q2['revenue_growth_yoy_pct'] is None
    # Yahoo caído → unavailable (y la caché de fallos no lo repite 10 min)
    ops._Q_CACHE.clear()
    monkeypatch.setattr(cd, '_yahoo_get', lambda url, params=None, timeout=None: (None, 'timeout'))
    ok, res = kc.execute_tool('get_fundamentals', {'id_or_ticker': 'Nvidia', 'period': 'quarterly'})
    assert not ok and res.get('code') == 'unavailable' and 'timeout' in res['error']
    ops._Q_CACHE.clear()


def test_constructor_fundamentals_barras_y_cifras():
    doc = _load(FIX_FUND)
    b = B.Ctx('es', 0, 'F1', 'Nvidia')
    blocks = B.BUILDERS['get_fundamentals'](copy.deepcopy(doc['result']), b)
    types = [(x['type'], x['_meta']['kind']) for x in blocks]
    assert types == [('chart.bar', 'fund_bar'), ('metric.tiles', 'fund_tiles'), ('chart.bar', 'fund_bar2')]
    bar, tiles, bar2 = blocks
    assert [it['label'] for it in bar['data']['items']] == ['FY2021', 'FY2022', 'FY2023', 'FY2024', 'FY2025']
    assert bar['data']['items'][-1]['v'] == doc['result']['latest']['revenue'] and bar['data']['values']['unit'] == 'USD'
    assert bar['data']['values']['src'] == 'yahoo' and bar['data']['values']['fact'] == 'F1'
    assert 'table' in bar['menu']                                                 # «Ver como tabla» (⋯)
    labels = [it['label']['es'] for it in tiles['data']['items']]
    assert labels == ['Ingresos', 'Utilidad neta', 'Margen bruto', 'Margen operativo', 'Margen neto', 'Crecimiento de ingresos']
    assert [it['value']['unit'] for it in tiles['data']['items']] == ['USD', 'USD', 'pct', 'pct', 'pct', 'pct']
    assert all(it['value']['explain'].startswith('genui_') for it in tiles['data']['items'])
    assert bar2['_meta']['role'] == 'secondary' and bar2['data']['diverging'] is True
    calls = [('get_fundamentals', None, True, doc['result'])]
    for blk in blocks:
        ok, why, _n = genui._check(blk, calls)
        assert ok, why
        assert V.errors(genui._strip(blk), 'Block') == []
    # una cifra que no está en el resultado → el bloque se descarta (procedencia)
    bad = copy.deepcopy(blocks[0])
    bad['data']['items'][0]['v'] = 123456789.0
    assert genui._check(bad, calls)[1] == 'no_provenance'


def test_pregunta_ganancias_en_grafico_produce_el_bloque(monkeypatch):
    monkeypatch.setenv('GENUI', 'on')
    script = [{'tool': 'get_fundamentals', 'args': {'id_or_ticker': 'Nvidia', 'period': 'annual'}, 'why': 'ganancias'},
              {'final': {'answer': 'Los ingresos de **Nvidia** crecieron año a año [F2].', 'actions': []}}]
    fake = FakeAI(script)
    monkeypatch.setattr(core_ai, '_ai_complete', fake)
    for mode in ('simple', 'pro'):
        out = kc.run_chat('muéstrame las ganancias de nvidia en un gráfico', [], 'es', {'genui': 1, 'mode': mode},
                          req_id='k-fund-' + mode)
        assert any(t['name'] == 'get_fundamentals' and t['ok'] for t in out['tools_used']), out['tools_used']
        ui = out.get('ui')
        assert ui and ui['v'] == 'kblocks/1' and V.errors(ui, 'Envelope') == []
        vis = [b for b in ui['blocks'] if b['type'] not in ('text', 'actions', 'sources')]
        assert vis[0]['type'] == 'chart.bar' and vis[0]['prov']['name'] == 'get_fundamentals', [b['type'] for b in vis]
        assert vis[1]['type'] == 'metric.tiles' and vis[1]['prov']['name'] == 'get_fundamentals'
        if mode == 'pro':
            assert any(b['type'] == 'chart.bar' and b['id'] != vis[0]['id'] for b in vis)      # utilidad neta, secundaria
        else:
            assert len(vis) == 2
        assert L.intent_of('muéstrame las ganancias de nvidia en un gráfico') == 'fundamentals'
        fake.script = list(script)


# ── 5. nombres internos fuera de la prosa ────────────────────────────────────────────────────────────────────────
def test_la_prosa_no_lleva_nombres_de_herramientas(monkeypatch):
    script = [{'final': {'answer': 'Nvidia cotiza a 182,40 USD (get_company, Yahoo, hoy 2026-10-14). Según `get_history` '
                                   'subió. Datos de la herramienta run_scenario.', 'actions': []}}]
    monkeypatch.setattr(core_ai, '_ai_complete', FakeAI(script))
    out = kc.run_chat('¿cómo está Nvidia?', [], 'es', {}, req_id='k-prose')
    ans = out['answer']
    for name in ('get_company', 'get_history', 'run_scenario'):
        assert name not in ans, ans
    assert '(Grafo Khipus' in ans and 'hoy 2026-10-14' in ans and 'motor de choques' in ans, ans
    assert '`' not in ans and 'la herramienta' not in ans
    # unitario: la fuente del hecho manda; sin hecho, el nombre humano; nada que no sea una herramienta se toca
    facts = [{'id': 'F1', 'kind': 'get_history', 'source': 'prices_eod', 'as_of': 'x'},
             {'id': 'F2', 'kind': 'get_company', 'source': 'Khipus supply-chain graph snapshot (curated catalog)', 'as_of': 'y'}]
    assert kc.strip_tool_names('(get_history, Yahoo Finance)', [{'id': 'F1', 'kind': 'get_history', 'source': 'yahoo_live'}], 'es') == '(Yahoo Finance)'
    assert kc.strip_tool_names('(get_company)', facts, 'en') == '(Khipus graph)'
    assert kc.strip_tool_names('get_companyx /api/get_company sin_herramienta', facts, 'es') == 'get_companyx /api/get_company sin_herramienta'
    assert kc.strip_tool_names('', facts, 'es') == ''


# ── E2.9. posición de mercado: ficha + rank_by_market + chat ─────────────────────────────────────────────────────
def test_limpieza_de_market_position_y_facilities():
    from core.hotviews.views import card as C
    raw = [{'market': ' EV batteries ', 'rank': '1', 'share_pct': '37,9', 'region': 'GLOBAL', 'period': '2025',
            'measured_by': 'SNE Research', 'source_url': 'https://example.org/x', 'as_of': '2026-02-01', 'confidence': 0.8,
            'extra': 'fuera'}, {'rank': 2}, 'basura', None]
    out = C.market_position_of(raw)
    assert out == [{'market': 'EV batteries', 'rank': 1, 'share_pct': 37.9, 'metric': None, 'region': 'GLOBAL',
                    'period': '2025', 'measured_by': 'SNE Research', 'source_url': 'https://example.org/x',
                    'as_of': '2026-02-01', 'confidence': 0.8}]
    assert C.market_position_of('x') == [] and C.market_position_of(None) == []
    fac = C.facilities_of([{'facility_id': 'fac-001', 'name': 'Ningde', 'kind': 'plant', 'country': 'CN', 'city': 'Ningde',
                            'capacity': {'value': '120', 'unit': 'GWh/yr'}, 'status': 'operating', 'start': '2011',
                            'source_url': 'https://example.org/f', 'as_of': '2026-01-01'}, {'kind': 'plant'}])
    assert len(fac) == 1 and fac[0]['capacity'] == {'value': 120.0, 'unit': 'GWh/yr'} and fac[0]['facility_id'] == 'fac-001'
    assert C.facilities_of([{'name': 'x', 'capacity': {'unit': 'GWh'}}])[0]['capacity'] is None


def test_mkt_match_es_en_y_sin_ranking_honesto():
    assert ops.mkt_match('baterías', 'EV batteries (cells)') >= 0.5
    assert ops.mkt_match('EV battery', 'baterías para vehículos eléctricos') >= 0.5
    assert ops.mkt_match('memoria HBM', 'HBM memory') >= 0.5
    assert ops.mkt_match('baterías', 'data-center GPUs') == 0.0
    assert ops._region_key('global') == 'GLOBAL' and ops._region_key(None) == 'GLOBAL' and ops._region_key('cn') == 'CN'
    doc = _load(FIX_MKT)
    b = B.Ctx('es', 0, 'F1', '')
    blocks = B.BUILDERS['rank_by_market'](copy.deepcopy(doc['result']), b)
    assert len(blocks) == 1 and blocks[0]['type'] == 'ranking'
    d = blocks[0]['data']
    assert d['direction'] == 'higher_better' and d['metric']['unit'] == 'pct' and d['metric']['src'] == 'khipus_graph'
    assert [it['entity']['id'] for it in d['items']] == ['Albemarle', 'SQM', 'GanfengLithium', 'TianqiLithium']
    assert d['items'][0]['v'] == 20.5 and d['items'][-1]['v'] is None and d['items'][0]['as_of'] == '2026-03-01'
    assert L.intent_of('¿cuál es la empresa de baterías más grande?') == 'market'
    assert L.intent_of('which is the largest EV battery maker?') == 'market'


@pytest.fixture(scope='module')
def pg():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from core.hotviews import builder, registry
    from ontology.db import _get_engine, init_schema, session_scope
    from ontology.models import Base
    from ontology.service import apply_event
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    assert init_schema(retries=1)
    src = 'https://example.org/sne-2025'
    mp = {
        'K_CATL': {'label': 'CATL (prueba)', 'ticker': '300750', 'market_position': [
            {'market': 'EV batteries', 'rank': 1, 'share_pct': 37.9, 'metric': 'GWh installed', 'region': 'GLOBAL',
             'period': '2025', 'measured_by': 'SNE Research', 'source_url': src, 'as_of': '2026-02-01', 'confidence': 0.8}],
            'facilities': [{'facility_id': 'fac-001', 'name': 'Ningde', 'kind': 'plant', 'country': 'CN', 'city': 'Ningde',
                            'capacity': {'value': 120, 'unit': 'GWh/yr'}, 'status': 'operating', 'start': '2011',
                            'source_url': src, 'as_of': '2026-01-01'}]},
        'K_BYD': {'label': 'BYD (prueba)', 'market_position': [
            {'market': 'baterías para vehículos eléctricos', 'rank': 2, 'share_pct': 17.2, 'metric': 'GWh installed',
             'region': 'global', 'period': '2025', 'measured_by': 'SNE Research', 'source_url': src, 'as_of': '2026-02-01',
             'confidence': 0.8}]},
        'K_LGES': {'label': 'LG Energy (prueba)', 'market_position': [
            {'market': 'EV batteries', 'rank': 3, 'share_pct': 10.8, 'metric': 'GWh installed', 'region': 'GLOBAL',
             'period': '2025', 'measured_by': 'SNE Research', 'source_url': src, 'as_of': '2026-02-01', 'confidence': 0.7},
            {'market': 'EV batteries', 'rank': 1, 'share_pct': 25.1, 'metric': 'GWh installed', 'region': 'US',
             'period': '2025', 'measured_by': 'SNE Research', 'source_url': src, 'as_of': '2026-02-01', 'confidence': 0.6}]},
        'K_GPU': {'label': 'GPU Co (prueba)', 'market_position': [
            {'market': 'data-center GPUs', 'rank': 1, 'share_pct': 86.4, 'metric': 'revenue share', 'region': 'GLOBAL',
             'period': '2025', 'measured_by': 'x', 'source_url': src, 'as_of': '2026-01-01', 'confidence': 0.5}]},
        'K_NONE': {'label': 'Sin posición (prueba)'},
    }
    with session_scope() as s:
        for oid, props in mp.items():
            p = dict(props, sector='x')
            lab = p.pop('label')
            apply_event(s, 'ObjectCreated', {'label': lab, 'type': 'Company', 'properties': p},
                        valid_from='2000-01-01', source='test', actor='pytest', object_id=oid)
        apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 5.0}, valid_from='2000-01-01', source='test',
                    actor='pytest', object_id='K_CATL', target_id='K_BYD')
    # una base de prueba con 5 empresas no cubre el catálogo (MIN_COVERAGE): para que los LECTORES (ficha, chat) lean
    # Postgres y no el snapshot, se baja el umbral solo aquí
    from core.hotviews import hot
    cov = hot.MIN_COVERAGE
    hot.MIN_COVERAGE = 0.0
    registry.reset()
    hot.reset()
    builder.build_once()
    yield engine
    hot.MIN_COVERAGE = cov
    registry.reset()
    hot.reset()
    Base.metadata.drop_all(engine)


@needs_db
def test_la_ficha_expone_market_position_y_facilities(pg):
    from core.hotviews.views import card as C
    cv = C.reader_view()
    assert cv is not None and cv.source == 'pg', (cv and cv.source)
    c = cv.card('K_CATL', 'es', structure=False, nrs=False)
    assert c['market_position'] == [{'market': 'EV batteries', 'rank': 1, 'share_pct': 37.9, 'metric': 'GWh installed',
                                     'region': 'GLOBAL', 'period': '2025', 'measured_by': 'SNE Research',
                                     'source_url': 'https://example.org/sne-2025', 'as_of': '2026-02-01', 'confidence': 0.8}]
    assert c['facilities'][0]['name'] == 'Ningde' and c['facilities'][0]['capacity'] == {'value': 120, 'unit': 'GWh/yr'}
    assert cv.card('K_NONE', 'es', structure=False, nrs=False)['market_position'] == []
    assert cv.card('K_NONE', 'es', structure=False, nrs=False)['facilities'] == []
    import server
    r = server.app.test_client().get('/api/hot/card/K_CATL?structure=0')
    assert r.status_code == 200
    data = r.get_json()['data']
    assert data['market_position'][0]['rank'] == 1 and data['facilities'][0]['facility_id'] == 'fac-001'


@needs_db
def test_rank_by_market_sobre_postgres_y_sin_ranking(pg):
    ok, res = kc.execute_tool('rank_by_market', {'market': 'baterías', 'metric': 'share_pct'})
    assert ok, res
    assert [x['id'] for x in res['items']] == ['K_CATL', 'K_BYD', 'K_LGES']          # es/en, región GLOBAL (no la fila US)
    assert res['items'][0]['rank'] == 1 and res['items'][0]['share_pct'] == 37.9 and res['items'][0]['source_url']
    assert res['graph_source'] == 'pg' and res['sorted_by'] == 'share_pct'
    ok, r2 = kc.execute_tool('rank_by_market', {'market': 'EV batteries', 'region': 'US'})
    assert ok and [x['id'] for x in r2['items']] == ['K_LGES'] and r2['items'][0]['share_pct'] == 25.1
    ok, r3 = kc.execute_tool('rank_by_market', {'market': 'baterías', 'metric': 'rank'})
    assert ok and r3['sorted_by'] == 'rank' and [x['rank'] for x in r3['items']] == [1, 2, 3]
    ok, r4 = kc.execute_tool('rank_by_market', {'market': 'satélites'})
    assert not ok and r4.get('code') == 'no_data' and 'I do not have that ranking' in r4['error']


@needs_db
def test_chat_cual_es_la_empresa_de_baterias_mas_grande(pg, monkeypatch):
    monkeypatch.setenv('GENUI', 'on')
    script = [{'tool': 'rank_by_market', 'args': {'market': 'baterías', 'metric': 'share_pct'}, 'why': 'ranking'},
              {'final': {'answer': 'La más grande es **CATL (prueba)** [F1].', 'actions': []}}]
    monkeypatch.setattr(core_ai, '_ai_complete', FakeAI(script))
    out = kc.run_chat('¿cuál es la empresa de baterías más grande?', [], 'es', {'genui': 1, 'mode': 'simple'}, req_id='k-mkt')
    assert any(t['name'] == 'rank_by_market' and t['ok'] for t in out['tools_used']), out['tools_used']
    ui = out['ui']
    assert V.errors(ui, 'Envelope') == []
    rk = [b for b in ui['blocks'] if b['type'] == 'ranking']
    assert rk and rk[0]['prov']['name'] == 'rank_by_market'
    assert [it['entity']['id'] for it in rk[0]['data']['items']] == ['K_CATL', 'K_BYD', 'K_LGES']
    assert rk[0]['data']['items'][0]['v'] == 37.9 and rk[0]['data']['items'][0]['entity']['label'] == 'CATL (prueba)'
    assert 'CATL (prueba)' in out['answer'] and 'rank_by_market' not in out['answer']
    assert any(a['agent'] == 'khipu' and '1.º CATL (prueba)' in a['note_es'] for a in out['agents_used']), out['agents_used']
