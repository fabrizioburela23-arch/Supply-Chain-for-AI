"""tests/test_countries.py — core/countries (ISO-2 ↔ clave ↔ nombre ES/EN) y su gemela JS window.KhipuCountries.

Trinquete: TODA grafía de país del catálogo (data/grafo_v0.json) debe resolver a un ISO-2 o ser una región conocida;
paridad Python ↔ JS sobre las 136 grafías + las 937 filas investigadas + códigos + nombres; el NRS NO cambia
(sus doradas viven en tests/golden; aquí se comprueba que `nrs_country` no mira la tabla nueva).
"""
import csv
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core import countries as C  # noqa: E402
from core import world as W  # noqa: E402

SNAPSHOT = os.path.join(ROOT, 'data', 'grafo_v0.json')
CSV_PATH = os.path.join(ROOT, 'data', 'import', 'lotes', '2026-10-14', 'existentes_paises.csv')
REGIONS = {'Europa', 'RestoEuropa', 'RestoMundo'}


def _nodes():
    with open(SNAPSHOT, encoding='utf-8') as fh:
        return json.load(fh)['nodes']


def _spellings():
    return sorted({str(n.get('country') or '') for n in _nodes() if n.get('country')})


def _csv_rows():
    if not os.path.exists(CSV_PATH):
        return []
    with open(CSV_PATH, encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


# ═══ 1. la tabla ═══════════════════════════════════════════════════════════════════════════════════════════════
def test_table_shape_and_catalog_keys():
    assert len(C.TABLE) >= 249 and all(len(k) == 2 and k.isupper() for k in C.TABLE)
    for iso, row in C.TABLE.items():
        assert set(row) == {'key', 'es', 'en', 'eu'} and row['es'] and row['en'] and row['key'], iso
    # toda clave de país de core/world._COUNTRY tiene ISO-2 (las regiones y el alias 'Japan' no son países)
    world_keys = set(W._COUNTRY) - REGIONS - {'Japan'}
    assert world_keys == set(C.KEY_TO_ISO), (world_keys ^ set(C.KEY_TO_ISO))
    for key, iso in C.KEY_TO_ISO.items():
        assert C.TABLE[iso]['key'] == key and W.country_key(key) == key
    # los alias extra apuntan a códigos de la tabla y están ya normalizados (como _js_norm)
    for k, v in C.EXTRA_ALIAS.items():
        assert v in C.TABLE, (k, v)
        assert k == W._js_norm(k), k
    assert 'DE' in C.EUROPE and 'GB' in C.EUROPE and 'US' not in C.EUROPE and 'RU' not in C.EUROPE


def test_contract_examples():
    assert C.iso2_of('Estados Unidos (HQ Denver, CO)') == 'US'
    assert C.iso2_of('EEUU') == 'US' and C.iso2_of('United States') == 'US' and C.iso2_of('US') == 'US'
    assert C.iso2_of('Japón') == 'JP' and C.iso2_of('Japon') == 'JP' and C.iso2_of('Japan') == 'JP'
    assert C.iso2_of('Taiwán') == 'TW' and C.iso2_of('Hong Kong (China)') == 'HK'
    assert C.iso2_of('Corea') == 'KR' and C.iso2_of('Korea, Republic of') == 'KR'
    assert C.iso2_of('Reino Unido / Noruega') == 'GB'                  # el PRIMER país del texto
    assert C.iso2_of('Bangladesh') == 'BD'                             # sin clave de catálogo: por el nombre
    assert C.iso2_of('Europa') is None and C.iso2_of('RestoMundo') is None and C.iso2_of('RestoEuropa') is None
    assert C.iso2_of('Eurozone (HQ Frankfurt, Germany)') is None and C.region_of('Eurozone (HQ Frankfurt, Germany)') == 'Europa'
    assert C.iso2_of('ca') is None and C.iso2_of('Planeta Marte') is None and C.iso2_of('') is None and C.iso2_of(None) is None
    assert C.region_of('Europa') == 'Europa' and C.region_of('RestoEuropa') == 'RestoEuropa' and C.region_of('Japón') is None
    for iso, key in (('US', 'EEUU'), ('JP', 'Japon'), ('GB', 'ReinoUnido'), ('NL', 'PaisesBajos'), ('AE', 'EAU'),
                     ('HK', 'HongKong'), ('KR', 'Corea'), ('TW', 'Taiwan'), ('CN', 'China')):
        assert C.catalog_key_of(iso) == key, iso
    assert C.catalog_key_of('BD') == 'Bangladesh' and C.catalog_key_of('XX') == 'XX' and C.catalog_key_of('gb') == 'ReinoUnido'
    assert C.label('US', 'es') == 'Estados Unidos' and C.label('US', 'en') == 'United States'
    assert C.label('Europa', 'en') == 'Europe' and C.label('RestoMundo', 'es') == 'Resto del mundo'
    assert C.label('ReinoUnido', 'en') == 'United Kingdom' and C.label('Planeta', 'es') == 'Planeta'
    assert C.is_europe('Suiza') and C.is_europe('DE') and C.is_europe('Europa') and not C.is_europe('Chile')
    assert C.resolve('Japón') == {'iso2': 'JP', 'key': 'Japon', 'region': None, 'es': 'Japón', 'en': 'Japan'}
    assert C.resolve('Europa')['region'] == 'Europa' and C.resolve('Bangladesh')['key'] is None


def test_iso2_of_props_prefers_importer_iso_then_country_then_loc():
    assert C.iso2_of_props({'country': 'Estados Unidos (HQ Denver, CO)'}) == 'US'
    assert C.iso2_of_props({'hq_country': 'DE', 'country': 'EEUU'}) == 'DE'          # lo investigado manda
    assert C.iso2_of_props({'country_iso2': 'FR', 'country': 'EEUU'}) == 'FR'
    assert C.iso2_of_props({'country': 'RestoMundo', 'loc': 'Canadá'}) == 'CA'        # región: el loc dice el país
    assert C.iso2_of_props({'country': 'RestoEuropa', 'loc': 'Finlandia'}) == 'FI'
    assert C.iso2_of_props({'country': 'Europa'}) is None and C.iso2_of_props({}) is None and C.iso2_of_props(None) is None
    assert C.iso2_of_props({'hq_country': 'xx', 'country': 'Japón'}) == 'JP'          # ISO inválido se ignora


# ═══ 2. trinquete sobre el catálogo y la investigación ═════════════════════════════════════════════════════════
def test_every_catalog_spelling_resolves_or_is_region():
    bad = [sp for sp in _spellings() if not (C.iso2_of(sp) or C.region_of(sp) in REGIONS)]
    assert not bad, ('Grafía de país NUEVA sin ISO-2: añade el alias a core/world._ALIAS (y a engine/geo_coords.js) o a '
                     'core/countries.EXTRA_ALIAS, y regenera docs/REVISION_PAISES.md: %r' % bad)
    sp = _spellings()
    assert len(sp) >= 130                                    # las 136 grafías de hoy (crece con el catálogo)
    regions = [n['id'] for n in _nodes() if C.region_of(n.get('country'))]
    assert len(regions) <= 71, regions                       # solo puede ACHICARSE (Fabrizio marca la sede en la revisión)


def test_research_rows_disagreements_are_documented_and_bounded():
    rows = _csv_rows()
    if not rows:
        pytest.skip('sin lote 2026-10-14')
    assert len(rows) == 937
    doc = open(os.path.join(ROOT, 'docs', 'REVISION_PAISES.md'), encoding='utf-8').read()
    dis, agree = [], 0
    for r in rows:
        ours, hq = C.iso2_of(r['pais_original']), r['hq_country']
        if ours and hq:
            if ours == hq:
                agree += 1
            else:
                dis.append(r['khipus_id'])
    assert agree >= 840 and len(dis) <= 20, (agree, dis)      # medido 2026-10-14: 846 de acuerdo, 20 desacuerdos
    for i in dis:
        assert f'(`{i}`)' in doc, f'desacuerdo {i} sin fila en docs/REVISION_PAISES.md (regenera el documento)'
    # toda sede investigada es un ISO-2 de la tabla (o vacío)
    assert all((not r['hq_country']) or C.is_iso2(r['hq_country']) for r in rows)


def test_review_document_and_js_table_up_to_date():
    from scripts import build_country_review as B
    assert B.update_js(write=False) is False, 'engine/geo_coords.js: corre python scripts/build_country_review.py --js'
    assert B.render(B.analyze()) == open(B.OUT_MD, encoding='utf-8').read(), \
        'docs/REVISION_PAISES.md desactualizado: corre python scripts/build_country_review.py'
    a = B.analyze()
    assert not a['unresolved'] and len(a['regions']) == 71 and len(a['nrs_diff']) == 2 and len(a['nrs_map']) == 5
    assert {r['id'] for r in a['nrs_diff']} | {r['id'] for r in a['nrs_map']} == {
        'AlignedDataCenters', 'ECB', 'Brookfield', 'ChinaMerchantsPort', 'chindata', 'QuantumMachines'}


# ═══ 3. core/world: ISO-2 de entrada, NRS intacto ══════════════════════════════════════════════════════════════
def test_world_country_key_accepts_iso2_without_touching_the_rest():
    assert W.country_key('US') == 'EEUU' and W.country_key('JP') == 'Japon' and W.country_key('GB') == 'ReinoUnido'
    assert W.country_key('CA') == 'Canada' and W.country_key('HK') == 'HongKong' and W.country_key(' KR ') == 'Corea'
    assert W.country_key('ca') is None and W.country_key('Ca') is None     # solo MAYÚSCULAS (California en un evento)
    assert W.country_key('BD') is None                                      # sin clave en _COUNTRY: como antes
    assert W.country_key('EU') == 'Europa' and W.country_key('UK') == 'ReinoUnido' and W.country_key('us') == 'EEUU'
    g = W.geo_coord({'id': 'zz_iso', 'country': 'JP'})
    assert g['country'] == 'Japon' and g['precision'] == 'country'
    assert W.geo_coord({'id': 'zz_iso2', 'country': 'US'})['precision'] == 'hub'
    assert W.place_country('Ridgecrest, CA') == 'EEUU' and W.place_country('12 km S of Tecate, B.C., MX') == 'Mexico'
    assert W.place_country('Kyiv, Kyyiv, Misto, Ukraine') == 'Ucrania'


def test_nrs_country_ignores_the_new_table():
    # el NRS sigue con su tabla gobernada: 'US' ya era alias suyo ('us'), 'JP'/'GB'/'DE' no lo son (no mira la tabla nueva)
    assert W.nrs_country('US') == 'EEUU' and W.nrs_country('JP') is None and W.nrs_country('GB') is None
    assert W.nrs_country('DE') is None and W.nrs_country('Japón') == 'Japan'
    assert W.nrs_country('Estados Unidos (HQ Denver, CO)') == 'EEUU' and W.nrs_country('Suiza') is None
    exp = {'EEUU': 462, 'China': 71, 'Japan': 60, 'Taiwan': 25, 'Korea': 11, 'Israel': 10, 'Europa': 51}   # medido 2026-10-14
    got = {}
    for n in _nodes():
        k = W.nrs_country(n.get('country'))
        if k:
            got[k] = got.get(k, 0) + 1
    assert got == exp, got                                   # misma lectura que la dorada impl_nrs.formula@1


# ═══ 4. consumidores Python ═══════════════════════════════════════════════════════════════════════════════════
def test_hotviews_meta_carries_derived_iso2():
    from core.hotviews import source
    m = source._meta_of('X', 'Company', {'country': 'Estados Unidos (HQ Denver, CO)', 'sector': 's'})
    assert m['country'] == 'Estados Unidos (HQ Denver, CO)' and m['country_iso2'] == 'US' and 'hq_country' not in m
    m = source._meta_of('X', 'Company', {'country': 'EEUU', 'hq_country': 'DE'})
    assert m['country_iso2'] == 'DE' and m['hq_country'] == 'DE'
    m = source._meta_of('X', 'Company', {'country': 'RestoMundo', 'loc': 'Chile'})
    assert m['country_iso2'] == 'CL'
    assert source._meta_of('X', 'Org', None)['country_iso2'] is None
    data = source.load_snapshot()
    assert data.meta['TSMC']['country_iso2'] == 'TW' and data.meta['TSMC']['country'] == 'Taiwan'
    assert data.meta['QuantumMachines']['country_iso2'] == 'IL'          # RestoMundo + loc Israel


def test_portfolio_ai_groups_by_catalog_key():
    from core import portfolio_ai as P
    assert P._country('Estados Unidos (HQ Denver, CO)') == 'EEUU' and P._country('EEUU') == 'EEUU'
    assert P._country('Taiwán') == 'Taiwan' and P._country('Taiwan') == 'Taiwan' and P._country('Hong Kong (China)') == 'HongKong'
    assert P._country('Rusia') == 'Rusia' and P._country('Russia') == 'Rusia'
    assert P._country('') == '?' and P._country(None) == '?' and P._country('Planeta Marte') == 'Planeta Marte'
    assert not hasattr(P, '_COUNTRY_NORM')


def test_context_tail_summary_groups_countries_by_iso2():
    from core import context_engine as ce
    meta = {'a': {'country': 'EEUU'}, 'b': {'country': 'Estados Unidos (HQ Denver, CO)'}, 'c': {'country': 'Taiwán'},
            'd': {'country': 'Europa'}, 'e': {'country': 'Planeta Marte'}}
    omitted = [{'target': 'a', 'w': 1.0}, {'target': 'b', 'w': 2.0}, {'target': 'c', 'w': 2.5}, {'target': 'd', 'w': 0.5},
               {'target': 'e', 'w': 0.25}]
    t = ce.tail_summary(omitted, meta.get, lang='es')
    assert t['top_countries_by_weight'][:2] == [{'country': 'Estados Unidos', 'weight': 3.0}, {'country': 'Taiwán', 'weight': 2.5}]
    names = [x['country'] for x in t['top_countries_by_weight']]
    assert 'Europa' in names and 'EEUU' not in names
    t_en = ce.tail_summary(omitted, meta.get, lang='en')
    assert t_en['top_countries_by_weight'][0]['country'] == 'United States'
    assert ce.tail_summary([], meta.get) is None


# ═══ 5. paridad con la gemela JS (engine/geo_coords.js) y la cubeta de la vista geo (nodes/nodes_seed.js) ═══════
_JS = r"""
const fs=require('fs'),vm=require('vm');
const ctx={window:{}};vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[1]+'/engine/geo_coords.js','utf8'),ctx,{filename:'geo_coords.js'});
const KC=ctx.window.KhipuCountries, G=ctx.window.GeoCoords;
const inp=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const out={table:KC.TABLE, iso2:{}, region:{}, key:{}, label_es:{}, label_en:{}, eu:{}, ck:{}, group:{}, node_iso:{}};
inp.texts.forEach(t=>{ out.iso2[t]=KC.iso2Of(t); out.region[t]=KC.regionOf(t); out.eu[t]=KC.isEurope(t); out.ck[t]=G.countryKey(t); out.group[t]=G.countryGroup(t); });
inp.codes.forEach(c=>{ out.key[c]=KC.catalogKeyOf(c); out.label_es[c]=KC.label(c,'es'); out.label_en[c]=KC.label(c,'en'); });
inp.nodes.forEach(n=>{ out.node_iso[n.id]=G.countryIso2(n); });
process.stdout.write(JSON.stringify(out));
"""


@pytest.mark.skipif(shutil.which('node') is None, reason='node no instalado')
def test_js_twin_parity(tmp_path):
    nodes = _nodes()
    texts = sorted(set(_spellings()) | {r['pais_original'] for r in _csv_rows()} | set(C.TABLE) |
                   {r['en'] for r in C.TABLE.values()} | {r['es'] for r in C.TABLE.values()} | set(C.EXTRA_ALIAS) |
                   {'Europa', 'RestoEuropa', 'RestoMundo', 'Planeta Marte', 'ca', 'Ca', 'us', 'EU', 'UK', ' JP ', 'Korea, Republic of',
                    'Eurozone (HQ Frankfurt, Germany)', 'Reino Unido / Noruega', 'Hong Kong (China)', 'ñandú 🦙', '', 'Japan'})
    codes = sorted(set(C.TABLE) | set(C.KEY_TO_ISO) | {'Europa', 'RestoEuropa', 'RestoMundo', 'XX', 'gb', 'Planeta', ''})
    inp = tmp_path / 'inp.json'
    inp.write_text(json.dumps({'texts': texts, 'codes': codes, 'nodes': nodes + [
        {'id': 'zz_hq', 'hq_country': 'DE', 'country': 'EEUU'}, {'id': 'zz_reg', 'country': 'RestoMundo', 'loc': 'Chile'},
        {'id': 'zz_none', 'country': 'Europa'}]}, ensure_ascii=False), encoding='utf-8')
    res = subprocess.run(['node', '-e', _JS, ROOT, str(inp)], capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, res.stderr
    js = json.loads(res.stdout)
    assert js['table'] == C.TABLE, 'tabla JS ≠ Python: corre python scripts/build_country_review.py --js'
    for t in texts:
        assert js['iso2'][t] == C.iso2_of(t), t
        assert js['region'][t] == C.region_of(t), t
        assert js['eu'][t] == C.is_europe(t), t
        assert js['ck'][t] == W.country_key(t), t
        assert js['group'][t] == (W.country_key(t) or (t or None)), t
    for c in codes:
        assert js['key'][c] == C.catalog_key_of(c), c
        assert js['label_es'][c] == C.label(c, 'es') and js['label_en'][c] == C.label(c, 'en'), c
    for n in json.loads(inp.read_text(encoding='utf-8'))['nodes']:
        assert js['node_iso'][n['id']] == C.iso2_of_props(n), n['id']
    assert js['node_iso']['zz_hq'] == 'DE' and js['node_iso']['zz_reg'] == 'CL' and js['node_iso']['zz_none'] is None


_JS_BUCKET = r"""
const fs=require('fs'),vm=require('vm');
const ctx={window:{}};vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[1]+'/nodes/nodes_seed.js','utf8'),ctx,{filename:'nodes_seed.js'});
const before={}; const T=JSON.parse(process.argv[2]); T.forEach(t=>{before[t]=ctx.countryBucket(t);});
vm.runInContext(fs.readFileSync(process.argv[1]+'/engine/geo_coords.js','utf8'),ctx,{filename:'geo_coords.js'});
const after={}; T.forEach(t=>{after[t]=ctx.countryBucket(t);});
const NODES=JSON.parse(fs.readFileSync(process.argv[1]+'/data/grafo_v0.json','utf8')).nodes, COUNTRIES=vm.runInContext('COUNTRIES',ctx);
const counts={}; NODES.forEach(n=>{const k=ctx.countryBucket(n.country); counts[k]=(counts[k]||0)+1;});
process.stdout.write(JSON.stringify({before, after, counts, keys:Object.keys(COUNTRIES)}));
"""


@pytest.mark.skipif(shutil.which('node') is None, reason='node no instalado')
def test_geo_view_bucket_for_every_spelling():
    texts = ['Estados Unidos (HQ Denver, CO)', 'Estados Unidos', 'EEUU', 'Japón', 'Taiwán', 'Canadá', 'Reino Unido',
             'Suiza', 'Finlandia', 'Chile', 'Europa', 'RestoEuropa', 'RestoMundo', 'Hong Kong (China)', 'Planeta Marte', '']
    res = subprocess.run(['node', '-e', _JS_BUCKET, ROOT, json.dumps(texts)], capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, res.stderr
    d = json.loads(res.stdout)
    # sin geo_coords.js cargado: solo la clave exacta (como antes); nada se cachea
    assert d['before']['EEUU'] == 'EEUU' and d['before']['Estados Unidos'] == 'RestoMundo'
    exp = {'Estados Unidos (HQ Denver, CO)': 'EEUU', 'Estados Unidos': 'EEUU', 'EEUU': 'EEUU', 'Japón': 'Japon', 'Taiwán': 'Taiwan',
           'Canadá': 'Canada', 'Reino Unido': 'ReinoUnido', 'Suiza': 'RestoEuropa', 'Finlandia': 'RestoEuropa', 'Chile': 'RestoMundo',
           'Europa': 'Europa', 'RestoEuropa': 'RestoEuropa', 'RestoMundo': 'RestoMundo', 'Hong Kong (China)': 'RestoMundo',
           'Planeta Marte': 'RestoMundo', '': 'RestoMundo'}
    assert d['after'] == exp
    assert set(d['counts']) <= set(d['keys']) and sum(d['counts'].values()) == len(_nodes())
    assert d['counts']['EEUU'] >= 440 and d['counts']['Japon'] >= 59 and d['counts']['Taiwan'] >= 25   # antes 361/44/21
    assert d['counts']['RestoMundo'] <= 70                                                            # antes 272 (todo lo no exacto)


def test_js_consumers_route_through_country_key():
    """Los consumidores del navegador agrupan por clave (no por texto exacto)."""
    def src(p):
        return open(os.path.join(ROOT, p), encoding='utf-8').read()
    am = src('engine/app_main.js')
    assert am.count('countryBucket(') >= 4 and "COUNTRIES[d.country]||COUNTRIES.RestoMundo" not in am
    assert 'd.country===activeCountry' not in am and 'countryBucket(d.country)===activeCountry' in am
    assert 'regionZ(n.country)' in src('engine/graph3d.js') and '_regionZ(n.country)' in src('engine/universe2d.js')
    for p in ('engine/insights.js', 'engine/livesim.js', 'engine/statematrix.js', 'engine/temporal-graph.js'):
        assert 'countryGroup' in src(p), p
    assert 'KhipuCountries.label' in src('engine/livesim.js') or 'KC.label' in src('engine/livesim.js')
    assert 'window.KhipuCountries' in src('engine/geo_coords.js') and 'countryIso2' in src('engine/geo_coords.js')
