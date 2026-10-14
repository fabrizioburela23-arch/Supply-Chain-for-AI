"""tests/test_resolve_ids.py — EXPANSION_5K E1.6 (lote K): resolver por IDENTIFICADORES en core/entities.

`resolve_ids(ids, name)` sigue el orden lei > isin/cik/qid > figi > yahoo_symbol / ticker@MIC > dominio (solo candidato)
> nombre ≥ 85 (60-84 = possible_duplicate). Reglas fijadas aquí:
  · un ticker SIN bolsa nunca resuelve ("3750" → None); "3750.HK" o '3750' + 'XHKG' sí;
  · los nombres en escritura local de `other_names` ("宁德时代") resuelven con resolve();
  · los alias de VOZ no cambian ("en vidia" → Nvidia con 80, nunca con el umbral de escritura);
  · identificadores leídos de las props de Postgres cuando existen y del catálogo (ticker/mkt) si no;
  · un identificador que dos empresas reclaman se devuelve como conflicto, nunca se elige en silencio;
  · p50 ≤ 5 ms a 937 y a 5k;
  · MCP search_companies acepta identificadores en `query` o como argumentos opcionales (solo lectura).
"""
import os
import statistics
import subprocess
import sys
import time
import types

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
DATABASE_URL = os.getenv('DATABASE_URL')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')

# ── fichas sintéticas con la forma que escribe el importador (contrato 3 del lote K) ──────────────────────────────
CATL = {'id': 'CATL', 'label': 'CATL', 'sector': 'energia', 'cat': 'battery_cells', 'country': 'China',
        'country_iso2': 'CN', 'mkt': '300750.SZ', 'ticker': '300750 · SZSE',
        'ids': {'lei': '300300C1091K2DKGZ518', 'isin': ['CNE100003662'], 'qid': 'Q21012583', 'domain': 'catl.com',
                'yahoo_symbol': '300750.SZ', 'ticker': '300750', 'mic': 'XSHE'},
        'listings': [{'symbol': '300750', 'mic': 'XSHE', 'yahoo_symbol': '300750.SZ', 'is_primary': True,
                      'kind': 'a_share', 'currency': 'CNY'},
                     {'symbol': '3750', 'mic': 'XHKG', 'yahoo_symbol': '3750.HK', 'is_primary': False,
                      'kind': 'h_share', 'currency': 'HKD', 'isin': 'CNE1000078B4'}],
        'other_names': [{'name': '宁德时代', 'kind': 'local_script', 'lang': 'zh'},
                        {'name': 'Contemporary Amperex Technology', 'kind': 'common', 'lang': 'en'}],
        'aliases': ['宁德时代', 'Contemporary Amperex Technology']}
BYD = {'id': 'BYD', 'label': 'BYD', 'sector': 'energia', 'cat': 'battery_cells', 'country': 'China', 'mkt': '1211.HK',
       'ticker': '1211 · HKEX', 'ids': {'isin': ['CNE100000296'], 'cik': '1234567', 'domain': 'byd.com'},
       'listings': [{'symbol': '1211', 'mic': 'XHKG', 'yahoo_symbol': '1211.HK', 'is_primary': True},
                    {'symbol': '002594', 'mic': 'XSHE', 'yahoo_symbol': '002594.SZ', 'is_primary': False}]}
# dos fichas que reclaman el MISMO ISIN y el mismo LEI (datos de investigación con un error): conflicto
DUP_A = {'id': 'DupA', 'label': 'Dup Alfa Materials', 'sector': 'materiales', 'cat': 'chem',
         'ids': {'isin': 'XX0000000001', 'lei': 'DUPDUPDUPDUPDUPDUP01', 'figi': ['BBG000000AA1']}}
DUP_B = {'id': 'DupB', 'label': 'Dup Beta Materials', 'sector': 'materiales', 'cat': 'chem',
         'ids': {'isin': 'XX0000000001', 'lei': 'DUPDUPDUPDUPDUPDUP01', 'figi': ['BBG000000BB2']}}


def _view(extra=(), n_synth=0):
    """GraphView del snapshot + fichas extra (y, si n_synth, copias sintéticas hasta ese tamaño)."""
    from core.hotviews import hot
    from core.hotviews.views import graph as graph_view
    g = hot.graph().snapshot
    nodes = list(g['nodes']) + [dict(x) for x in extra]
    if n_synth:
        try:
            import gen_synth_graph as G
            data = G.synth_graphdata(n_synth)
            nodes = list(data.nodes) + [dict(x) for x in extra]
            links = data.links
            cat = data.catalog
        except ImportError:
            k = 0
            while len(nodes) < n_synth:
                n = dict(g['nodes'][k % len(g['nodes'])])
                n['id'] = f"S{k:05d}_{n['id'][:12]}"
                n['label'] = f"{n.get('label') or n['id']} Synth {k}"
                if n.get('mkt'):
                    n['mkt'] = f'SY{k:04d}'
                nodes.append(n)
                k += 1
            links, cat = g['links'], {k2: g.get(k2) for k2 in ('node_id_alias', 'legal_names', 'voice_aliases',
                                                                  'resolve_stopwords')}
    else:
        links, cat = g['links'], {k2: g.get(k2) for k2 in ('node_id_alias', 'legal_names', 'voice_aliases',
                                                              'resolve_stopwords')}
    data = types.SimpleNamespace(nodes=tuple(nodes), links=links, catalog=cat)
    gv = graph_view.build(data)
    gv.attach(types.SimpleNamespace(id=f'synth-resolve-ids-{len(nodes)}-{len(extra)}', graph_version=None,
                                    source='snapshot', lineage=None, built_at=None, views={}))
    return gv


@pytest.fixture
def catalogo(monkeypatch):
    """La generación del snapshot (sin base)."""
    import ontology.db as odb
    from core.hotviews import hot, registry
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    registry.reset()
    hot.reset()
    yield hot.graph()
    registry.reset()
    hot.reset()


@pytest.fixture
def con_fichas(monkeypatch, catalogo):
    gv = _view([CATL, BYD, DUP_A, DUP_B])
    from core.hotviews import hot
    monkeypatch.setattr(hot, 'graph', lambda wait=True, timeout=None: gv)
    return gv


# ── catálogo de hoy: ticker/mkt ───────────────────────────────────────────────────────────────────────────────────

def test_catalogo_ticker_solo_nunca_resuelve_con_bolsa_si(catalogo):
    from core import entities as E
    assert E.resolve_ids({'ticker': '2330'}) is None
    assert E.resolve_ids({'ticker': 'TSM'}) is None
    assert E.resolve_ids({'ticker': 'NVDA'}) is None          # el símbolo de Nvidia, pero sin bolsa no identifica
    assert E.resolve_ids({'yahoo_symbol': '2330.TW'})['id'] == 'TSMC'            # listado declarado (home)
    assert E.resolve_ids({'ticker': '2330', 'mic': 'XTAI'})['id'] == 'TSMC'
    assert E.resolve_ids({'ticker': 'TSM', 'mic': 'XNYS'})['id'] == 'TSMC'
    assert E.resolve_ids({'ticker': 'NVDA', 'exchange_mic': 'XNAS'}) == {'id': 'Nvidia', 'method': 'ticker_mic',
                                                                         'score': 96, 'conflicts': []}
    assert E.resolve_ids({'yahoo_symbol': 'nvda'})['id'] == 'Nvidia'             # el símbolo de Yahoo = mkt
    # el TEXTO del catálogo ("005930 · KRX") da el símbolo de casa como clave blanda
    assert E.resolve_ids({'ticker': '005930', 'mic': 'XKRX'})['id'] == 'Samsung'
    assert E.resolve_ids({'yahoo_symbol': '005930.KS'})['id'] == 'Samsung'
    assert E.resolve_ids({'ticker': '981', 'mic': 'XHKG'})['id'] == 'SMIC'       # HKEX: 981 = 0981
    assert E.resolve_ids({'ticker': '2330', 'mic': 'XHKG'}) is None              # misma cifra, otra bolsa: nada
    assert E.resolve_ids({}) is None and E.resolve_ids(None) is None


def test_catalogo_sin_identificadores_declarados_no_inventa(catalogo):
    from core import entities as E
    assert E.resolve_ids({'lei': '549300ABCDEFGHIJKL12'}) is None
    assert E.resolve_ids({'isin': 'US67066G1040'}) is None
    assert E.resolve_ids({'domain': 'nvidia.com'}) is None
    assert E.identifier_conflicts() == []


def test_nombre_solo_con_umbral_de_escritura(catalogo):
    from core import entities as E
    r = E.resolve_ids({}, name='NVIDIA Corporation')
    assert r['id'] == 'Nvidia' and r['method'].startswith('name:') and r['score'] >= 85
    r = E.resolve_ids({}, name='Taiwan Semiconductor Manufacturing Company')
    assert r['id'] == 'TSMC' and r['score'] >= 85
    r = E.resolve_ids({}, name='Nvid')                       # 70 (prefijo): posible duplicado, NO coincidencia
    assert r == {'id': None, 'method': None, 'score': 0,
                 'conflicts': [{'kind': 'possible_duplicate', 'id': 'Nvidia', 'score': 70, 'method': 'prefijo'}]}
    assert E.resolve_ids({}, name='zzzz empresa inexistente qqq') is None
    # un alias de VOZ (80) no alcanza el umbral de escritura: posible duplicado, nunca coincidencia
    r = E.resolve_ids({}, name='en vidia')
    assert r['id'] is None and r['conflicts'][0]['kind'] == 'possible_duplicate' and r['conflicts'][0]['score'] == 80


def test_alias_de_voz_sin_cambios(catalogo):
    from core import entities as E
    r = E.resolve('en vidia')
    assert r and r['id'] == 'Nvidia' and r['score'] == 80 and r['method'] == 'voice_alias'
    assert E.resolve('en vidia', umbral=E.UMBRAL_ESCRITURA) is None
    assert E.resolve('taiwan semi')['id'] == 'TSMC'
    assert E.resolve('NVDA')['score'] == 98 and E.resolve('Nvidia')['score'] == 100


# ── fichas importadas: ids / listings / other_names ────────────────────────────────────────────────────────────────

def test_ids_de_la_ficha_en_el_orden_del_contrato(con_fichas):
    from core import entities as E
    assert E.resolve_ids({'lei': '300300C1091K2DKGZ518'}) == {'id': 'CATL', 'method': 'lei', 'score': 100,
                                                            'conflicts': []}
    assert E.resolve_ids({'isin': 'CNE100003662'})['method'] == 'isin'
    assert E.resolve_ids({'isin': ['CNE1000078B4']})['id'] == 'CATL'            # ISIN del listado H
    assert E.resolve_ids({'qid': 'q21012583'})['score'] == 99
    assert E.resolve_ids({'wikidata_qid': 'Q21012583'})['id'] == 'CATL'
    assert E.resolve_ids({'cik': 1234567})['id'] == 'BYD' and E.resolve_ids({'cik': '0001234567'})['id'] == 'BYD'
    assert E.resolve_ids({'figi': 'BBG000000AA1'})['id'] == 'DupA'
    assert E.resolve_ids({'yahoo_symbol': '3750.HK'}) == {'id': 'CATL', 'method': 'yahoo_symbol', 'score': 97,
                                                        'conflicts': []}
    assert E.resolve_ids({'yahoo_symbol': '300750.SZ'})['id'] == 'CATL'
    assert E.resolve_ids({'ticker': '3750', 'mic': 'XHKG'})['method'] == 'ticker_mic'
    assert E.resolve_ids({'ticker': '002594', 'mic': 'XSHE'})['id'] == 'BYD'
    assert E.resolve_ids({'ticker': '3750'}) is None                              # E1.6: sin MIC, nada
    assert E.resolve_ids({'ticker': '3750', 'mic': 'XTAI'}) is None               # otra bolsa, nada
    # el LEI manda sobre un ISIN que apunta a otra: se elige el LEI y el ISIN queda como conflicto
    r = E.resolve_ids({'lei': '300300C1091K2DKGZ518', 'isin': 'CNE100000296'})
    assert r['id'] == 'CATL' and r['conflicts'] == [{'kind': 'id_conflict', 'method': 'isin', 'id': 'BYD',
                                                     'vs': 'CATL'}]
    # el dominio NUNCA resuelve solo: candidato
    assert E.resolve_ids({'domain': 'https://www.catl.com/en/'}) == {
        'id': None, 'method': None, 'score': 0, 'conflicts': [{'kind': 'domain_candidate', 'id': 'CATL'}]}
    r = E.resolve_ids({'yahoo_symbol': '1211.HK', 'domain': 'catl.com'})
    assert r['id'] == 'BYD' and r['conflicts'] == [{'kind': 'domain_conflict', 'id': 'CATL', 'vs': 'BYD'}]
    # nombre que contradice al identificador: conflicto, el identificador manda
    r = E.resolve_ids({'isin': 'CNE100000296'}, name='CATL')
    assert r['id'] == 'BYD' and r['conflicts'][0]['kind'] == 'name_conflict' and r['conflicts'][0]['id'] == 'CATL'


def test_escritura_local_y_nombres_alternativos_resuelven(con_fichas):
    from core import entities as E
    r = E.resolve('宁德时代')
    assert r and r['id'] == 'CATL' and r['method'] == 'alias' and r['score'] == 92
    assert E.resolve('宁德时代', umbral=E.UMBRAL_ESCRITURA)['id'] == 'CATL'
    assert E.resolve('Contemporary Amperex Technology')['id'] == 'CATL'
    assert E.resolve_ids({}, name='宁德时代')['id'] == 'CATL'
    assert E.resolve_ids({'ticker': '3750'}, name='宁德时代')['method'] == 'name:alias'
    assert E.search_scores('宁德时代')['CATL'] == (92, 'alias')
    # un alias alternativo nunca pisa lo curado (alias del merge / nombres legales / etiquetas)
    assert E.resolve('TSMC')['id'] == 'TSMC' and E.resolve('Google')['id'] == 'Alphabet'


def test_identificador_reclamado_por_dos_empresas_es_conflicto_no_eleccion(con_fichas):
    from core import entities as E
    r = E.resolve_ids({'isin': 'XX0000000001'})
    assert r['id'] is None and r['conflicts'] == [{'kind': 'ambiguous_id', 'method': 'isin', 'ids': ['DupA', 'DupB'],
                                                   'key': 'XX0000000001'}]
    r = E.resolve_ids({'lei': 'DUPDUPDUPDUPDUPDUP01', 'figi': 'BBG000000BB2'})
    assert r['id'] == 'DupB' and r['method'] == 'figi' and r['conflicts'][0]['kind'] == 'ambiguous_id'
    cs = E.identifier_conflicts()
    assert {(c['kind'], c['key']) for c in cs} == {('isin', 'XX0000000001'), ('lei', 'DUPDUPDUPDUPDUPDUP01')}
    assert all(c['ids'] == ['DupA', 'DupB'] for c in cs)


def test_indice_por_generacion(monkeypatch, catalogo):
    """El índice de identificadores se arma por generación: otra vista → otro índice (como el de búsqueda)."""
    from core import entities as E
    from core.hotviews import hot
    assert E.resolve_ids({'lei': '300300C1091K2DKGZ518'}) is None
    gv = _view([CATL])
    monkeypatch.setattr(hot, 'graph', lambda wait=True, timeout=None: gv)
    assert E.graph_version() == gv.generation
    assert E.resolve_ids({'lei': '300300C1091K2DKGZ518'})['id'] == 'CATL'
    idx = E.get_index()
    assert set(idx['identificadores']) >= {'lei', 'isin', 'cik', 'qid', 'figi', 'yahoo', 'ticker_mic', 'domain',
                                           'conflictos'}


# ── velocidad ──────────────────────────────────────────────────────────────────────────────────────────────────────
_QS = [{'yahoo_symbol': '2330.TW'}, {'ticker': 'NVDA', 'mic': 'XNAS'}, {'lei': '549300ABCDEFGHIJKL12'},
       {'isin': 'US67066G1040'}, {'ticker': '3750'}, {'ticker': '005930', 'mic': 'XKRX'}, {'qid': 'Q1337386'},
       {'cik': '0000320193', 'domain': 'apple.com'}]


def _p50_ms(fn, args, reps=40):
    ts = []
    for _ in range(reps):
        for a in args:
            t0 = time.perf_counter()
            fn(a)
            ts.append((time.perf_counter() - t0) * 1000)
    return statistics.median(ts)


def test_p50_937(catalogo):
    from core import entities as E
    E.resolve_ids(_QS[0])
    assert _p50_ms(E.resolve_ids, _QS) <= 5
    p = _p50_ms(lambda a: E.resolve_ids(a, name='Taiwan Semiconductor Manufacturing Company'), _QS, reps=10)
    assert p <= 5, p


def test_p50_5k(monkeypatch, catalogo):
    from core import entities as E
    from core.hotviews import hot
    gv = _view([CATL, BYD], n_synth=5000)
    monkeypatch.setattr(hot, 'graph', lambda wait=True, timeout=None: gv)
    t0 = time.perf_counter()
    assert E.resolve_ids({'yahoo_symbol': '3750.HK'})['id'] == 'CATL'
    primera = (time.perf_counter() - t0) * 1000           # incluye armar el índice de la generación
    assert len(E.get_index()['nodos']) >= 5000
    assert _p50_ms(E.resolve_ids, _QS) <= 5
    assert primera < 5000, primera


# ── MCP search_companies ───────────────────────────────────────────────────────────────────────────────────────────

def test_mcp_search_companies_con_identificadores(con_fichas):
    from mcp_server import tools as T
    T._SNAP['data'] = None
    plano = T.t_search_companies(None, 'NVDA', 5)
    assert set(plano) == {'query', 'count', 'results', 'source', 'as_of'}       # sin identificador: igual que antes
    assert plano['results'][0]['id'] == 'Nvidia' and plano['results'][0]['match'] == {'score': 98, 'method': 'ticker'}
    r = T.t_search_companies(None, '3750.HK', 5)
    assert r['identifiers'] == {'yahoo_symbol': '3750.HK'}
    # el identificador manda el id; si el TEXTO ya encontraba ese símbolo con más puntaje, conserva su puntaje (regla
    # de abajo: 98 ticker > 97 yahoo_symbol) — desde que los listados secundarios entran al índice de texto, pasa aquí
    assert r['results'][0]['id'] == 'CATL'
    assert r['results'][0]['match'] in ({'score': 97, 'method': 'yahoo_symbol'}, {'score': 98, 'method': 'ticker'})
    r = T.t_search_companies(None, '3750@XHKG', 5)
    assert r['identifiers'] == {'ticker': '3750', 'mic': 'XHKG'} and r['results'][0]['match']['method'] == 'ticker_mic'
    r = T.t_search_companies(None, 'baterias', 5, lei='300300C1091K2DKGZ518')
    assert r['results'][0]['id'] == 'CATL' and r['results'][0]['match'] == {'score': 100, 'method': 'lei'}
    r = T.t_search_companies(None, 'CNE100000296', 3)
    assert r['identifiers'] == {'isin': 'CNE100000296'} and r['results'][0]['id'] == 'BYD'
    r = T.t_search_companies(None, 'Q21012583', 3)
    assert r['results'][0]['id'] == 'CATL' and r['count'] == len(r['results']) <= 3
    # ticker suelto: texto, nunca identificador (y se dice)
    r = T.t_search_companies(None, 'catl', 5, ticker='3750')
    assert r['identifiers'] == {'ticker': '3750'} and r['results'][0]['id'] == 'CATL'
    assert 'never identifies' in r['identifiers_note'] and 'conflicts' not in r
    # un identificador ambiguo se devuelve como conflicto
    r = T.t_search_companies(None, 'XX0000000001', 5)
    assert r['conflicts'][0]['kind'] == 'ambiguous_id' and r['conflicts'][0]['ids'] == ['DupA', 'DupB']
    # el símbolo que el TEXTO ya encuentra con más puntaje conserva su puntaje (98 ticker > 97 yahoo_symbol)
    r = T.t_search_companies(None, '0981.HK', 3)
    assert r['results'][0]['id'] == 'SMIC' and r['results'][0]['match']['score'] == 98
    # el esquema sigue exigiendo `query`; los nuevos argumentos son opcionales y cortos
    sch = T.REGISTRY['search_companies'].input_schema
    assert sch['required'] == ['query'] and {'lei', 'isin', 'cik', 'qid', 'yahoo_symbol', 'ticker', 'mic'} <= set(sch['properties'])
    assert T.REGISTRY['search_companies'].annotations['readOnlyHint'] is True
    T.validate(sch, {'query': 'x', 'mic': 'XHKG', 'ticker': '3750'})
    with pytest.raises(T.InvalidParams):
        T.validate(sch, {'query': 'x', 'mic': 'XHKGX'})


def test_mcp_identificadores_en_la_consulta():
    from mcp_server.tools import _identifiers_in
    assert _identifiers_in('nvidia') == {}
    assert _identifiers_in('NVDA') == {} and _identifiers_in('tsm') == {}
    assert _identifiers_in('549300ABCDEFGHIJKL12') == {'lei': '549300ABCDEFGHIJKL12'}
    assert _identifiers_in('us67066g1040') == {'isin': 'US67066G1040'}
    assert _identifiers_in('Q1337386') == {'qid': 'Q1337386'}
    assert _identifiers_in('0000320193') == {'cik': '0000320193'}
    assert _identifiers_in('300750.sz') == {'yahoo_symbol': '300750.SZ'}
    assert _identifiers_in('3750@xhkg') == {'ticker': '3750', 'mic': 'XHKG'}
    assert _identifiers_in('x', ticker='3750', mic='XHKG') == {'ticker': '3750', 'mic': 'XHKG'}
    assert _identifiers_in('3750.HK', yahoo_symbol='1211.HK') == {'yahoo_symbol': '1211.HK'}   # el argumento manda


# ── Postgres: identificadores leídos de las propiedades del objeto ─────────────────────────────────────────────────
@pytest.fixture(scope='module')
def migrated():
    if not DATABASE_URL:
        pytest.skip('requiere DATABASE_URL')
    from ontology.db import _get_engine, init_schema
    from ontology.models import Base
    engine = _get_engine()
    Base.metadata.drop_all(engine)
    init_schema()
    script = os.path.join(ROOT, 'scripts', 'migrate_v0_to_ontology.py')
    r = subprocess.run([sys.executable, script, '--reset'], capture_output=True, text=True,
                       env={**os.environ, 'DATABASE_URL': DATABASE_URL, 'PYTHONIOENCODING': 'utf-8'})
    assert r.returncode == 0, r.stderr
    yield engine
    from core.hotviews import hot, registry
    registry.reset()
    hot.reset()
    Base.metadata.drop_all(engine)


@needs_db
def test_postgres_props_ids_listings_other_names(migrated):
    from core import entities as E
    from core.hotviews import builder, hot, registry
    from mcp_server import tools as T
    from ontology.db import session_scope
    from ontology.service import apply_event
    registry.reset()
    hot.reset()
    g0 = builder.build_once()
    assert hot.graph().generation == g0.id and E.resolve_ids({'yahoo_symbol': '3750.HK'}) is None
    assert E.resolve_ids({'yahoo_symbol': '2330.TW'})['id'] == 'TSMC'           # el catálogo sigue ahí (mkt/listings)
    props = {k: v for k, v in CATL.items() if k not in ('id', 'label')}
    with session_scope() as s:
        apply_event(s, 'ObjectCreated', {'label': 'CATL', 'type': 'Company', 'properties': props},
                    valid_from='2026-10-14', source='test', actor='pytest', object_id='CATL')
    g1 = builder.ensure(g0.graph_version + 1, g0.lineage, timeout=15)
    assert g1 is not None and hot.graph().generation == g1.id
    assert E.graph_version() == g1.id
    assert E.resolve_ids({'lei': '300300C1091K2DKGZ518'})['id'] == 'CATL'
    assert E.resolve_ids({'ticker': '3750', 'mic': 'XHKG'})['id'] == 'CATL'
    assert E.resolve_ids({'ticker': '3750'}) is None
    assert E.resolve('宁德时代')['id'] == 'CATL'
    T._SNAP['data'] = None
    assert T.t_search_companies(None, 'CNE100003662', 3)['results'][0]['id'] == 'CATL'
    registry.reset()
    hot.reset()
