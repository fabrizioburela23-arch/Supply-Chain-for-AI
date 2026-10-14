"""tests/test_ops_single_source.py — INFRA_OPERATIVA paso 8: UN solo grafo en el servidor.

  · Estático: ningún módulo abre data/grafo_v0.json por su cuenta salvo la fuente de las vistas
    (core/hotviews/source.py) y ontology/reconcile.py (compara catálogo ↔ base a propósito); los 13 lectores
    pasan por core/hotviews/hot.graph(); el screener ya no lee el privado matrix.api._TTL_CACHE.
  · Todos los lectores reportan la MISMA generación (graph_version) y la renuevan cuando la generación cambia
    (una empresa nueva aparece en todos), en vez de "cargar una vez y para siempre".
  · Sin base, las salidas son IDÉNTICAS a las del cálculo viejo sobre el archivo (misma forma, mismos números),
    salvo dos cambios DELIBERADOS: Ψ del tensor (kernel + factores, solo flujo) y el bonus de PageRank del
    screener, que ahora se aplica siempre que la vista exista (antes casi nunca: leía una caché de rutas).
  · Ψ del tensor = EL kernel del servidor (propagate + factores de la generación) SOLO sobre relaciones de
    flujo (BRECHAS #4 por defecto: socios/inversores no transmiten) hasta que el paso 12 lo lleve al kernel.
  · La vista es inmutable (FrozenDict / MappingProxy).
  · Con Postgres: los lectores leen la base (source 'pg', misma graph_version que /api/hot/*), una empresa
    creada en la base aparece en entidades, MCP, tensor, World Monitor y screener; una fusión (retired +
    merged_into) pasa a alias; una base que no trae el catálogo NO deja a la app sin empresas (respaldo del
    snapshot marcado stale).
"""
import json
import os
import re
import subprocess
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATABASE_URL = os.getenv('DATABASE_URL', '')
needs_db = pytest.mark.skipif(not DATABASE_URL, reason='requiere DATABASE_URL (Postgres)')

READERS = ('core/world.py', 'core/entities.py', 'core/screener.py', 'core/sim_agents.py', 'core/semantic.py',
           'core/portfolio_ai.py', 'research/router.py', 'research/context.py', 'matrix/tensor.py',
           'mcp_server/tools.py')
ALLOWED_LOADERS = {'core/hotviews/source.py', 'ontology/reconcile.py'}


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as fh:
        return fh.read()


def _catalog():
    with open(os.path.join(ROOT, 'data', 'grafo_v0.json'), encoding='utf-8') as fh:
        return json.load(fh)


def _all_versions():
    from core import entities, portfolio_ai, screener, semantic, world
    from matrix import tensor
    from mcp_server import tools
    from research import context, router
    return {'entities': entities.graph_version(), 'world': world.graph_version(),
            'screener': screener.graph_version(), 'semantic': semantic.graph_version(),
            'portfolio_ai': portfolio_ai.graph_version(), 'router': router.graph_version(),
            'context': context.graph_version(), 'tensor': tensor.graph_version(),
            'mcp': tools.graph_version()}


@pytest.fixture
def nodb(monkeypatch):
    """Sin base aunque DATABASE_URL exista: la generación es la del snapshot."""
    import ontology.db as odb
    from core.hotviews import builder, hot, registry
    monkeypatch.setattr(odb, 'ontology_available', lambda: False)
    registry.reset()
    # una construcción fallida de una prueba anterior (Postgres sin tablas) deja al constructor en espera: ensure()
    # devolvería None y hot.graph() caería a la privada (fallback) en vez de la generación del snapshot
    builder._ST.update(consecutive_failures=0, retry_at=0.0)
    hot.reset()
    yield
    registry.reset()
    hot.reset()


# ════════════════════════════════════════════════════════════════════════════
# estático
# ════════════════════════════════════════════════════════════════════════════
def test_nadie_abre_el_snapshot_por_su_cuenta():
    lit = re.compile(r"""['"]grafo_v0\.json['"]""")
    bad = []
    for base in ('core', 'research', 'matrix', 'mcp_server', 'ontology', 'brokerage', 'sim'):
        for dp, _dn, fns in os.walk(os.path.join(ROOT, base)):
            for fn in fns:
                if not fn.endswith('.py'):
                    continue
                rel = os.path.relpath(os.path.join(dp, fn), ROOT).replace(os.sep, '/')
                if rel in ALLOWED_LOADERS:
                    continue
                if lit.search(_read(rel)):
                    bad.append(rel)
    for rel in ('server.py',):
        if lit.search(_read(rel)):
            bad.append(rel)
    assert bad == [], f'cargan data/grafo_v0.json por su cuenta: {bad}'


def test_los_lectores_pasan_por_el_accesor_unico():
    for rel in READERS:
        src = _read(rel)
        assert 'hotviews' in src, rel
        assert '_SNAPSHOT' not in src, rel                # ni constante propia ni la de core.entities
    # reconcile conserva su carga a propósito (compara catálogo vs Postgres)
    assert "SNAPSHOT_PATH = os.path.join(_ROOT, 'data', 'grafo_v0.json')" in _read('ontology/reconcile.py')


def test_el_screener_ya_no_lee_la_cache_privada_de_matrix():
    src = _read('core/screener.py')
    assert '_TTL_CACHE' not in src and 'matrix.api' not in src


# ════════════════════════════════════════════════════════════════════════════
# sin base: una versión, mismas salidas que el cálculo viejo
# ════════════════════════════════════════════════════════════════════════════
def test_todos_los_lectores_reportan_la_misma_generacion(nodb):
    from core.hotviews import hot
    g = hot.graph()
    assert g.source == 'snapshot' and not g.fallback and g.graph_version == 0
    vers = _all_versions()
    assert set(vers.values()) == {g.generation}, vers


def test_salidas_identicas_al_archivo_sin_base(nodb):
    """Sin base, cada lector arma EXACTAMENTE lo que armaba desde el archivo (misma forma y números)."""
    from collections import defaultdict

    from core import entities, portfolio_ai, screener, semantic, sim_agents, world
    from mcp_server import tools
    from ontology.vocabulary import flow_degree
    cat = _catalog()
    nodes, links = cat['nodes'], cat['links']
    # entidades
    idx = entities.get_index()
    assert list(idx['nodos']) == [n['id'] for n in nodes]
    assert all(dict(idx['nodos'][n['id']]) == n for n in nodes)
    assert entities.resolve('Taiwan Semiconductor Manufacturing Company')['id'] == 'TSMC'
    alias = cat['node_id_alias']
    a = next(k for k, v in alias.items() if v in idx['nodos'])
    assert a in entities.entity_ids_for(alias[a])
    # semántica (grado de flujo y adyacencia)
    sem = semantic._load_snapshot()
    assert sem['flow_deg'] == flow_degree(links)
    assert sum(len(v) for v in sem['out'].values()) == len(links)
    # World Monitor
    w = world._graph()
    assert [r['id'] for r in w['nodes']] == [n['id'] for n in nodes if n.get('id')]
    fd = flow_degree(links)
    assert all(r['flow_degree'] == fd.get(r['id'], 0) for r in w['nodes'])
    # screener: universo deduplicado por símbolo, en el orden del catálogo
    seen, uni = set(), []
    for n in nodes:
        mkt = (n.get('mkt') or '').strip()
        if mkt and mkt not in seen:
            seen.add(mkt)
            uni.append({'id': n['id'], 'label': n.get('label') or n['id'], 'mkt': mkt,
                        'cat': n.get('cat', ''), 'sector': n.get('sector', '')})
    assert screener._load_universe() == uni
    # carteras: grado, proveedores, clientes
    deg, sup = defaultdict(int), defaultdict(list)
    for l in links:
        deg[l['source']] += 1
        deg[l['target']] += 1
        sup[l['target']].append((l.get('w') or 1, l['source']))
    pg = portfolio_ai._graph()
    assert pg['deg'] == dict(deg) and pg['sup'] == dict(sup) and pg['flow_deg'] == fd
    # MCP
    snap = tools._snapshot()
    assert snap['source_label'] == tools.SNAPSHOT_SOURCE and snap['as_of'] == cat['exported_at']
    assert len(snap['nodes']) == len(nodes) and snap['flow_deg'] == flow_degree(
        e for lst in snap['out'].values() for e in lst)
    # simulación por agentes: etiquetas de sector del catálogo
    assert sim_agents._sectors9() == cat['sectors9']


def test_la_vista_es_inmutable(nodb):
    from core.hotviews import hot
    g = hot.graph()
    n = g.by_id['Nvidia']
    with pytest.raises(TypeError):
        n['label'] = 'x'
    with pytest.raises(TypeError):
        n['listing'] = {}
    with pytest.raises(TypeError):
        g.by_id['X'] = n
    with pytest.raises(TypeError):
        g.nodes = ()
    with pytest.raises((TypeError, AttributeError)):
        g.links.append({})
    copia = dict(n)
    copia['label'] = 'x'                                        # una copia sí se puede cambiar
    assert g.by_id['Nvidia']['label'] != 'x'
    assert json.loads(json.dumps(n))['id'] == 'Nvidia'
    import copy
    assert type(copy.deepcopy(n)) is dict
    assert hot.graph() is g                                     # misma generación → mismo objeto


def test_una_generacion_nueva_renueva_a_todos_los_lectores(nodb):
    """Lo que antes era imposible sin reiniciar: una empresa nueva aparece en TODOS los lectores."""
    from core import entities, screener, semantic, world
    from core.hotviews import builder, hot, source
    from matrix import tensor
    from mcp_server import tools
    g0 = hot.graph()
    assert entities.resolve('Zeta Nueva Fab', umbral=85) is None
    data = source.load_snapshot()
    nuevo = {'id': 'ZetaNuevaFab', 'label': 'Zeta Nueva Fab', 'mkt': 'ZZNF', 'sector': 'fabricacion',
             'cat': 'foundry', 'country': 'EEUU', 'ticker': 'ZZNF · Nasdaq'}
    data.nodes = list(data.nodes) + [nuevo]
    data.links = list(data.links) + [{'source': 'ZetaNuevaFab', 'target': 'Nvidia', 'w': 5, 'rel': 'obleas',
                                      'type': 'fab', 'conf': 1, 'verified': True}]
    data.ids = sorted(set(data.ids) | {'ZetaNuevaFab'})
    data.meta = dict(data.meta, ZetaNuevaFab={'label': 'Zeta Nueva Fab', 'type': 'Company', 'sector': 'fabricacion',
                                             'ticker': 'ZZNF', 'country': 'EEUU'})
    data.triples = list(data.triples) + [('ZetaNuevaFab', 'Nvidia', 'fab', 5.0)]
    data.lineage = 'snap:prueba-paso8'
    g1 = builder.build_once(data)
    view = hot.graph()
    assert view.generation == g1.id != g0.generation
    assert entities.resolve('Zeta Nueva Fab', umbral=85)['id'] == 'ZetaNuevaFab'
    assert entities.resolve('ZZNF')['id'] == 'ZetaNuevaFab'
    assert 'ZetaNuevaFab' in world._graph()['by_id']
    assert any(u['mkt'] == 'ZZNF' for u in screener._load_universe())
    assert 'ZetaNuevaFab' in semantic._load_snapshot()['by_id']
    assert tools.t_search_companies(None, 'Zeta Nueva')['results'][0]['id'] == 'ZetaNuevaFab'
    st = tensor.structure('Nvidia')
    assert st is not None and tensor.model().generation == g1.id
    m = tensor.model()
    assert m.psi[m.idx['Nvidia'], m.idx['ZetaNuevaFab']] > 0      # la fab nueva ya transmite a Nvidia
    vers = _all_versions()
    assert set(vers.values()) == {g1.id}, vers


def test_el_screener_toma_el_pagerank_de_la_misma_generacion(nodb):
    from core import screener
    from core.hotviews import hot, registry
    assert screener._pagerank_ranks() == {}          # sin generación: no dispara construcciones
    g = hot.graph()
    ranks = screener._pagerank_ranks()
    assert ranks and ranks == {k: m['pagerank_rank'] for k, m in g.impact.metrics.items() if m.get('pagerank_rank')}
    assert registry.generation() is g.generation_obj


# ════════════════════════════════════════════════════════════════════════════
# Ψ del tensor = la vista Impact (EL kernel)
# ════════════════════════════════════════════════════════════════════════════
def test_psi_del_tensor_es_el_kernel_solo_flujo_en_todo_el_catalogo(nodb):
    """Ψ = EL kernel del servidor (propagate, fragilidad de los factores de la generación) con las relaciones de
    FLUJO solamente (BRECHAS #4, por defecto vigente): socios e inversores no transmiten daño."""
    from core.hotviews import hot
    from matrix import engine as E
    from matrix import tensor
    from ontology import vocabulary as vocab
    g = hot.graph()
    m = tensor.model(force=True)
    core = g.core
    flow = set(vocab.flow_relation_types())
    mats = {r: x for r, x in core.mats.items() if r in flow}
    assert set(core.mats) - flow, 'el catálogo trae socios/inversores (la máscara debe hacer algo)'
    for s in ('TSMC', 'Nvidia', 'ASML', 'Microsoft', 'Codelco', 'SoftBank'):
        if s not in core.idx:
            continue
        impacts, _ = E.propagate(mats, core.idx, core.ids, [s], frag=core.frag)
        exp = np.zeros(m.n)
        for k, p in impacts.items():
            if k != s and k in m.idx:
                exp[m.idx[k]] = p / 100.0
        assert np.array_equal(m.psi[:, m.idx[s]], exp), s
    assert m.psi_method == 'impact_kernel_flow_only:propagate@1'


def test_socios_e_inversores_no_transmiten_en_el_tensor(nodb):
    """BRECHAS #4 (por defecto vigente hasta que Fabrizio responda): el kernel del servidor HOY transmite por socio
    (0,3) e inversión (0,25) en la vista Impact; el Ψ del tensor (cifras de inversionista: capitalización aguas
    abajo en riesgo, MCP get_company.structure) NO. El paso 12 lleva la regla al kernel."""
    from core.hotviews.views import impact as IV
    from matrix import tensor as T
    n = lambda i: {'id': i, 'label': i, 'cat': 'x', 'sector': 'x', 'country': 'EEUU'}  # noqa: E731
    snap = {'nodes': [n('Z'), n('C'), n('D'), n('I')],
            'links': [{'source': 'Z', 'target': 'C', 'w': 3, 'type': 'partner', 'conf': 1},
                      {'source': 'I', 'target': 'C', 'w': 3, 'type': 'invest', 'conf': 1},
                      {'source': 'C', 'target': 'D', 'w': 6, 'type': 'supply', 'conf': 1}]}
    m = T.Model(snap)
    assert m.psi[m.idx['C'], m.idx['Z']] == 0.0                   # socio: no transmite
    assert m.psi[m.idx['C'], m.idx['I']] == 0.0                   # inversor: no transmite
    assert m.psi[m.idx['D'], m.idx['C']] == 0.6                   # proveedor único con peso 6
    # la vista Impact (el kernel de hoy) sí lo hace: la diferencia es deliberada y medible
    imp = IV.build(T._core_for(snap))
    vz = dict(zip(*imp.victims['Z'][:2]))
    assert vz.get('C', 0) > 0


# ════════════════════════════════════════════════════════════════════════════
# con Postgres
# ════════════════════════════════════════════════════════════════════════════
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


@pytest.fixture
def pg(migrated):
    from core.hotviews import builder, hot, registry
    registry.reset()
    hot.reset()
    g = builder.build_once()
    yield g
    registry.reset()
    hot.reset()


@needs_db
def test_con_base_los_lectores_leen_postgres_con_la_misma_version(pg):
    from core.hotviews import hot
    view = hot.graph()
    assert view.generation == pg.id and view.source == 'pg' and not view.fallback
    assert view.coverage == 1.0 and view.graph_version == pg.graph_version
    vers = _all_versions()
    assert set(vers.values()) == {pg.id}, vers
    from mcp_server import tools
    snap = tools._snapshot()
    assert snap['source_label'].startswith('Khipus ontology (Postgres, graph_version ')


@needs_db
def test_con_base_las_propiedades_son_las_del_catalogo_migrado(pg):
    """La migración copia cada empresa con TODAS sus propiedades: el grafo de lectura de la base coincide con el
    catálogo nodo a nodo Y vínculo a vínculo. Los hechos temporales migrados (predicate/headline sin rel_label,
    rel_type 'supply' por defecto: "Amazon invierte $8B en Anthropic") NO son vínculos de lectura —el snapshot
    nunca los trajo—: siguen en la ImpactView y en el Grafo Temporal. Un par (origen, destino, tipo) = un vínculo."""
    from collections import Counter

    from core.hotviews import hot
    from ontology.vocabulary import flow_degree
    cat = _catalog()
    view = hot.graph()
    assert [n['id'] for n in view.nodes] == [n['id'] for n in cat['nodes']]
    diff = [n['id'] for n in cat['nodes'] if dict(view.by_id[n['id']]) != n]
    assert diff == [], diff[:5]
    key = lambda l: (l['source'], l['target'], l.get('type') or 'supply')  # noqa: E731
    assert {key(l) for l in view.links} == {key(l) for l in cat['links']}
    assert [k for k, c in Counter(key(l) for l in view.links).items() if c > 1] == []
    assert dict(view.flow_degree) == dict(flow_degree(cat['links']))
    assert view.stats['facts_excluded'] > 0


@needs_db
def test_con_base_mcp_no_lista_inversores_como_proveedores_repetidos(pg):
    """Revisión del paso 8: get_company('Anthropic').top_suppliers listaba a Amazon y Alphabet DOS veces (el
    vínculo cloud del catálogo y el hecho temporal "invierte en" como 'supply' sin peso)."""
    from mcp_server import tools
    sup = tools.t_get_company(None, 'Anthropic', include_live=False)['top_suppliers']
    ids = [x['id'] for x in sup]
    assert len(ids) == len(set(ids)), ids
    assert all(x.get('weight') is not None for x in sup), sup


@needs_db
def test_con_base_una_propuesta_no_es_un_proveedor_verificado(pg):
    """Revisión del paso 8: un ProponerVinculo (radar, auto-aplicado como SAFE_AUTO) quedaba en el grafo de
    lectura y el MCP lo daba como proveedor verified:true, confianza 1.0 (y subía el grado de flujo / NRS)."""
    from core import world
    from core.hotviews import builder, hot
    from mcp_server import tools
    from ontology.actions import execute_action
    from ontology.db import session_scope
    before = dict(hot.graph().flow_degree).get('Anthropic', 0)
    nrs0 = world.client_nrs(hot.graph().by_id['Anthropic'], before)
    with session_scope() as s:
        execute_action(s, 'ProponerVinculo', {'from_id': 'Bluefors', 'to_id': 'Anthropic', 'tipo': 'supply',
                                              'metadata': {'rel_label': 'Suministra criostatos (nota de prensa)'},
                                              'fuente': 'radar'}, actor='agent:radar')
    g = builder.ensure(pg.graph_version + 1, pg.lineage, timeout=15)
    assert g is not None
    view = hot.graph()
    assert view.generation == g.id
    assert not any(l['source'] == 'Bluefors' and l['target'] == 'Anthropic' for l in view.links)
    assert view.stats['proposed_excluded'] >= 1
    sup = tools.t_get_company(None, 'Anthropic', include_live=False)['top_suppliers']
    assert 'Bluefors' not in [x['id'] for x in sup]
    edges = tools.t_get_supply_chain(None, 'Anthropic')['edges']
    assert not any(e.get('source') == 'Bluefors' or e.get('from') == 'Bluefors' for e in edges)
    assert dict(view.flow_degree).get('Anthropic', 0) == before
    assert world.client_nrs(view.by_id['Anthropic'], before) == nrs0


@needs_db
def test_una_empresa_creada_en_la_base_aparece_en_todos(pg):
    from core import entities, screener, world
    from core.hotviews import builder, hot
    from matrix import tensor
    from mcp_server import tools
    from ontology.db import session_scope
    from ontology.service import apply_event
    with session_scope() as s:
        apply_event(s, 'ObjectCreated', {'label': 'Omega Litografía Nueva', 'type': 'Company',
                                         'properties': {'mkt': 'OMGL', 'sector': 'equipos', 'cat': 'litho',
                                                        'country': 'Japón'}},
                    valid_from='2026-10-13', source='test', actor='pytest', object_id='OmegaLitoNueva')
        apply_event(s, 'LinkCreated', {'rel_type': 'supply', 'weight': 6,
                                       'properties': {'rel_label': 'escáneres EUV'}},
                    valid_from='2026-10-13', source='test', actor='pytest', object_id='OmegaLitoNueva',
                    target_id='TSMC')
    g = builder.ensure(pg.graph_version + 1, pg.lineage, timeout=15)
    assert g is not None and g.graph_version > pg.graph_version
    view = hot.graph()
    assert view.generation == g.id
    assert entities.resolve('Omega Litografía Nueva', umbral=85)['id'] == 'OmegaLitoNueva'
    assert 'OmegaLitoNueva' in world._graph()['by_id']
    assert any(u['mkt'] == 'OMGL' for u in screener._load_universe())
    assert tools.t_search_companies(None, 'Omega Litografia')['results'][0]['id'] == 'OmegaLitoNueva'
    m = tensor.model()
    assert m.generation == g.id and m.psi[m.idx['TSMC'], m.idx['OmegaLitoNueva']] > 0
    assert set(_all_versions().values()) == {g.id}


@needs_db
def test_fusion_en_la_base_pasa_a_alias(pg):
    from core import entities
    from core.hotviews import builder, hot
    from ontology.db import session_scope
    from ontology.service import apply_event
    with session_scope() as s:
        apply_event(s, 'ObjectCreated', {'label': 'Duplicado de Prueba Paso8', 'type': 'Company', 'properties': {}},
                    valid_from='2026-10-13', source='test', actor='pytest', object_id='DupPaso8')
    g1 = builder.ensure(pg.graph_version + 1, pg.lineage, timeout=15)
    assert 'DupPaso8' in hot.graph().by_id
    with session_scope() as s:
        apply_event(s, 'ObjectUpdated', {'properties': {'retired': True, 'merged_into': 'TSMC'}},
                    valid_from='2026-10-13', source='test', actor='pytest', object_id='DupPaso8')
    g2 = builder.ensure(g1.graph_version + 1, g1.lineage, timeout=15)
    view = hot.graph()
    assert view.generation == g2.id and 'DupPaso8' not in view.by_id
    assert view.canonical('DupPaso8') == 'TSMC' and view.stats['retired'] >= 1
    assert 'DupPaso8' in entities.entity_ids_for('TSMC')


@needs_db
def test_base_sin_el_catalogo_no_deja_a_la_app_sin_empresas(migrated):
    """Una base nueva (o con datos de prueba) no trae el catálogo: los lectores usan el snapshot por su cuenta,
    marcado fallback/stale, y /api/hot/* sigue con la generación de la base."""
    from core import entities
    from core.hotviews import builder, hot, registry, source
    registry.reset()
    hot.reset()
    data = source.load_pg()
    data.nodes = [n for n in data.nodes if n['id'] in ('TSMC', 'Nvidia')]
    data.links = [l for l in data.links if l['source'] in ('TSMC', 'Nvidia') and l['target'] in ('TSMC', 'Nvidia')]
    data.lineage = (data.lineage or '') + '.parcial'
    try:
        g = builder.build_once(data)
        assert g.views['graph'].coverage < hot.MIN_COVERAGE
        view = hot.graph()
        assert view.fallback and view.source == 'snapshot' and view.stale and view.n_nodes == 937
        assert entities.resolve('ASML')['id'] == 'ASML'
        assert registry.generation() is g                     # lo publicado no cambia
        assert hot.status()['stats']['last_fallback_reason'].startswith('low_coverage')
    finally:
        registry.reset()
        hot.reset()
