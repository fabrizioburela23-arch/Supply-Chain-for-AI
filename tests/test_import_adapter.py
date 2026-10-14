"""tests/test_import_adapter.py — EXPANSION_5K E2.3 sobre el lote REAL 2026-10-14 (data/import/lotes/2026-10-14):
las 4.174 fichas nivel A validan; los nombres que ya están en el catálogo se FUSIONAN (nunca se duplican); el CEDEAR
de Boeing NO es la cotización principal (queda marcado); las 56 categorías propuestas se listan para aprobar; el
"¿qué cambia?" dice la verdad (nodos sin vínculos: ρ y TSMC no cambian); un lote vacío = antes == después; el plan es
PURO (dos llamadas → la misma huella) y rápido."""
import os
import sys
import time
from collections import Counter

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault('KHIPU_SCHEDULER', 'off')

from ontology import company_import as CI  # noqa: E402

YA_EN_CATALOGO = ('Boeing', 'BMW', 'Cemex', 'Umicore', 'National Grid', 'Terna', 'Prysmian', 'DHL Group', 'Tencent',
                  'GE Aerospace', 'Vulcan Energy', 'RWE', 'Ericsson', 'Shell')


@pytest.fixture(scope='module')
def view():
    """El grafo de los lectores desde el SNAPSHOT (sin base), como lo ve el plan en un servidor sin DATABASE_URL."""
    import ontology.db as odb
    from core.hotviews import hot, registry
    real = odb.ontology_available
    odb.ontology_available = lambda: False
    try:
        registry.reset()
        hot.reset()
        v = hot.graph()
    finally:
        odb.ontology_available = real
    assert v is not None and len(v.nodes) >= 900
    return v


@pytest.fixture(scope='module')
def bundle():
    return CI.adapt_lote_2026_10_14()


@pytest.fixture(scope='module')
def lote_plan(bundle, view):
    t0 = time.perf_counter()
    p = CI.plan(bundle['records'], bundle['updates'], view=view, batch=bundle['batch'], approve_categories=[])
    p['_secs'] = time.perf_counter() - t0
    return p


def test_el_lote_valida_entero(bundle):
    assert len(bundle['records']) == 4174 and len(bundle['updates']) == 934 and len(bundle['approve_categories']) == 56
    valid, invalid = CI.validate_batch(bundle['records'])
    assert len(valid) == 4174 and not invalid, invalid[:3]
    ids = {r['record_id'] for r in bundle['records']}
    assert len(ids) == 4174
    codes = Counter(w['code'] for w in bundle['warnings'])
    assert codes['symbol_invalid'] == 4            # GVT&D, ARE&M, PE&OLES, M&M: fuera del patrón del esquema
    assert codes['primary_is_depositary'] >= 5     # CEDEAR / OTC / regionales alemanas como "principal" (revisión 1)


def test_las_que_ya_estan_se_fusionan_no_se_duplican(lote_plan, view):
    by_name = {it['name']: it for it in lote_plan['items']}
    for name in YA_EN_CATALOGO:
        it = by_name[name]
        assert it['action'] == 'merge', (name, it['action'], it['method'])
        assert it['score'] >= CI.policy('name_write_threshold')
    assert lote_plan['counts']['merge'] >= 30
    assert lote_plan['counts']['create'] + lote_plan['counts']['merge'] + lote_plan['counts']['skip'] == 4174
    assert lote_plan['counts']['update'] == 934 and lote_plan['counts']['invalid'] == 0
    assert lote_plan['counts']['links'] == {'live': 0, 'proposed': 0, 'pending': 0, 'quarantine': 0}
    # fusión: lo curado que YA existe nunca se pisa (se lista como conflicto); solo se añade lo que falta
    for it in lote_plan['items']:
        if it['action'] == 'merge':
            cur = view.by_id.get(it['id']) or {}
            pisa = {k for k in ('cat', 'country', 'mkt', 'ticker', 'role', 'sector') if k in it['props'] and cur.get(k)}
            assert not pisa, (it['name'], pisa)


def test_boeing_cedear_no_es_principal(lote_plan):
    boe = next(it for it in lote_plan['items'] if it['name'] == 'Boeing')
    assert boe['action'] == 'merge' and boe['id'] == 'Boeing'
    ls = boe['props'].get('listings') or []
    assert ls and ls[0]['mic'] == 'XBUE' and ls[0]['is_primary'] is False and ls[0]['isin'].startswith('AR')
    assert 'mkt' not in boe['props'] and 'ticker' not in boe['props']   # BA · NYSE sigue siendo la principal


def test_categorias_del_lote_ya_viven_en_el_catalogo(bundle, view, lote_plan):
    """Lote K: las 55 categorías propuestas están en data/categories.json → nodes/categories_extra.js (aprobadas por
    defecto; Fabrizio puede rechazar) y `battery_components` quedó fusionada en `battery_cells`: el plan no tiene nada
    que aprobar y las 1.487 empresas entran directo con su categoría (la propuesta queda guardada en cat_proposed)."""
    assert lote_plan['categories']['to_approve'] == []
    assert len(bundle['approve_categories']) == 56 and all(c['label_es'] and c['label_en'] and c['sector'] for c in bundle['approve_categories'])
    from ontology.vocabulary import resolve_category
    target = {resolve_category(c['id']) or c['id'] for c in bundle['approve_categories']}
    assert 'battery_components' not in target and 'battery_cells' in target
    props = [it['props'] for it in lote_plan['items'] if it['action'] != 'skip']
    assert sum(1 for p in props if p.get('cat_proposed')) == 1485            # 1.487 − las 2 de battery_components
    assert sum(1 for p in props if p.get('cat_declared') == 'battery_components') == 2
    assert sum(1 for p in props if p.get('cat') == 'battery_cells') == 90    # 88 + 2 fusionadas
    # 1.487 fichas traen una categoría nueva; las 7 que se FUSIONAN con una empresa curada conservan la categoría de
    # hoy (lo curado no se pisa: solo queda `cat_proposed`), así que entran con la nueva las 1.480 que se crean
    assert sum(1 for p in props if p.get('cat') in target) == 1480
    assert sum(1 for it in lote_plan['items'] if it['action'] == 'merge' and it['props'].get('cat_proposed')) == 7
    assert not any(p.get('cat_unknown') for p in props)
    p2 = CI.plan(bundle['records'][:300], [], view=view, batch='x', approve_categories=bundle['approve_categories'],
                 what_changes=False)
    assert p2['categories']['to_approve'] == [] and len(p2['categories']['approved_now']) == 56
    assert not any(it['props'].get('cat_approved_in_run') for it in p2['items'] if it['action'] == 'create')


def test_que_cambia_dice_la_verdad(lote_plan):
    wc = lote_plan['what_changes']
    assert wc['available'] and not wc['identical'] and wc['added_links'] == 0 and wc['added_nodes'] >= 4000
    assert wc['calibration_stale'] is False
    assert wc['before']['tsmc_hit'] == wc['after']['tsmc_hit'] == 318
    assert wc['before']['rho'] == wc['after']['rho']
    assert [c['id'] for c in wc['before']['chokepoints']] == [c['id'] for c in wc['after']['chokepoints']]
    assert len(wc['before']['chokepoints']) == 20 and wc['after']['nodes'] == wc['before']['nodes'] + wc['added_nodes']


def test_lote_vacio_antes_igual_despues(view):
    p = CI.plan([], [], view=view, batch='vacio')
    assert p['counts']['create'] == 0 and p['what_changes']['identical'] and p['what_changes']['before'] == p['what_changes']['after']


def test_el_plan_es_puro_y_rapido(bundle, view, lote_plan):
    assert lote_plan['_secs'] < 30, lote_plan['_secs']       # meta: 250 fichas ≤ 10 s; aquí 4.174
    p2 = CI.plan(bundle['records'], bundle['updates'], view=view, batch=bundle['batch'], approve_categories=[],
                 what_changes=False)
    assert p2['plan_sha'] == lote_plan['plan_sha']
    sub = CI.plan(bundle['records'][:250], [], view=view, batch='sub', what_changes=False)
    assert sub['build_ms'] < 10000


def test_contrato_de_propiedades(lote_plan):
    it = next(it for it in lote_plan['items'] if it['action'] == 'create' and it['props'].get('listings'))
    pr = it['props']
    for k in ('ids', 'listings', 'hq_country', 'country', 'country_iso2', 'texts', 'verified', 'research_meta', 'cat', 'sector'):
        assert k in pr, k
    assert set(pr['texts']) == {'role_es', 'role_en', 'supplies_es', 'supplies_en', 'moat_es', 'moat_en', 'risk_es', 'risk_en',
                                'growth_es', 'growth_en'}
    assert pr['texts']['role_es'] and pr['texts']['role_en'] is None       # solo español: el inglés queda pendiente
    l0 = pr['listings'][0]
    assert {'symbol', 'mic', 'yahoo_symbol', 'is_primary', 'kind', 'currency'} <= set(l0)
    assert pr['research_meta']['batch'] == 'lote-2026-10-14' and pr['research_meta']['priority'] in ('P1', 'P2', 'P3')
    assert 'price' not in pr and 'market_cap' not in pr


def test_paises_de_las_existentes_entran_como_hechos_con_fuente(lote_plan):
    ups = [u for u in lote_plan['updates'] if u['action'] == 'update']
    assert len(ups) == 934
    air = next(u for u in ups if u['khipus_id'] == 'Airbus')
    assert air['props']['hq_country'] == 'FR' and air['props']['incorporation_country'] == 'NL'
    assert air['props']['country_facts']['hq_country']['source_id'] and air['source_id']
    assert all('country' not in u['props'] for u in ups)      # el texto `country` del catálogo no se toca


def test_resumen_en_los_dos_idiomas(lote_plan):
    es = CI.render_summary(lote_plan, 'es')
    en = CI.render_summary(lote_plan, 'en')
    assert 'Plan de importación' in es and 'Import plan' in en and lote_plan['plan_sha'] in es
