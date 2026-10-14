"""tests/test_catalog_fix_categories.py — categorías del catálogo con FUENTE ÚNICA (lote 2026-10-14).

  · data/categories.json = las 108 de hoy + las 55 propuestas (aprobadas por defecto; battery_components se consolida
    en battery_cells) con es/en/sector/cssVar/x; nodes/categories_extra.js se GENERA de ahí (scripts/build_categories.py)
    y la prueba exige que esté al día;
  · toda categoría usada por un nodo del catálogo existe en el JSON; ids únicos; alias (agrupa) → UN id consolidado y
    nunca chocan con un id; sectores = los 13 del catálogo (mismo color);
  · las categorías con color propio tienen su variable --c-<id> en app.html en los DOS temas (claro en :root, oscuro
    en .dark) con el mismo hex que el JSON; app.html carga categories_extra.js justo después de nodes_seed.js;
  · en el navegador (sandbox de Node con los mismos archivos que el exportador) las nuevas entran en CATS y en
    CAT_TO_SECTOR sin pisar nada, y las etiquetas crudas (air_cargo…) pasan a leerse en ES/EN;
  · /api/vocabulary las sirve con `companies` (0 para las nuevas) y `category_aliases`, y el ETag cambia con el JSON.
"""
import json
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts import build_categories as B  # noqa: E402

JSON_PATH = os.path.join(ROOT, 'data', 'categories.json')
JS_PATH = os.path.join(ROOT, 'nodes', 'categories_extra.js')
APP = os.path.join(ROOT, 'app.html')
SNAPSHOT = os.path.join(ROOT, 'data', 'grafo_v0.json')
CSS_RX = re.compile(r'--c-([a-z_0-9]+)\s*:\s*(#[0-9A-Fa-f]{6})')


@pytest.fixture(scope='module')
def doc():
    return B.load(JSON_PATH)


@pytest.fixture(scope='module')
def snap():
    with open(SNAPSHOT, encoding='utf-8') as fh:
        return json.load(fh)


def _read(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8') as fh:
        return fh.read()


def test_json_valido_y_js_generado_al_dia(doc):
    assert B.validate(doc) == []
    assert doc['schema'] == 'khipus.categories/1'
    assert B.render(doc) == _read('nodes', 'categories_extra.js'), 'corre python scripts/build_categories.py'
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'build_categories.py'), '--check'],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr


def _catalog_categories(snap):
    """Las categorías que definen los nodes_*.js de hoy SIN categories_extra.js (sandbox de Node, como el
    exportador); sin node, las del snapshot que no vengan del lote."""
    import shutil
    node = shutil.which('node')
    if node:
        js = ("const vm=require('vm'),fs=require('fs'),path=require('path');const ROOT=process.argv[1];"
              "const ctx=vm.createContext({window:{},console});"
              "for (const f of ['nodes/nodes_seed.js','nodes/nodes_expand5.js','nodes/nodes_multicapa.js'])"
              " vm.runInContext(fs.readFileSync(path.join(ROOT,f),'utf-8'),ctx,{filename:f});"
              "process.stdout.write(JSON.stringify(Object.keys(vm.runInContext('Object.assign({},CATS,CATS_NEW)',ctx))));")
        return set(json.loads(subprocess.run([node, '-e', js, ROOT], capture_output=True, text=True, timeout=60,
                                             check=True).stdout))
    return {k for k in snap['categories'] if k not in (B.load(JSON_PATH)['categories'] or {})
            or B.load(JSON_PATH)['categories'][k]['origin'] == 'catalog'}


def test_108_de_hoy_mas_55_nuevas_y_battery_components_consolidada(doc, snap):
    cats = doc['categories']
    old = {k for k, v in cats.items() if v['origin'] == 'catalog'}
    new = {k for k, v in cats.items() if v['origin'] != 'catalog'}
    assert old == _catalog_categories(snap) and len(old) == 108
    assert set(snap['categories']) in (old, old | new)      # el snapshot: sin o con categories_extra.js en el exportador
    assert len(new) == 55 and not (old & new)
    assert 'battery_components' not in cats
    assert 'battery_components' in cats['battery_cells']['aliases']
    assert doc['merged'] == {'battery_components': 'battery_cells'}
    assert all(v['status'] == 'approved' for k, v in cats.items() if k in new)   # aprobadas por defecto
    # las 55 vienen del CSV del lote, con su sector y sus etiquetas
    import csv
    rows = {r['id']: r for r in csv.DictReader(open(os.path.join(
        ROOT, 'data', 'import', 'lotes', '2026-10-14', 'categorias_propuestas.csv'), encoding='utf-8'))}
    assert set(rows) - {'battery_components'} == new
    for k in new:
        assert cats[k]['sector'] == rows[k]['sector'] and cats[k]['es'] == rows[k]['label_es']
        assert cats[k]['en'] == rows[k]['label_en']
        for a in [x.strip() for x in rows[k]['agrupa'].split(',') if x.strip() and x.strip() != k]:
            assert a in cats[k]['aliases'], (k, a)


def test_toda_categoria_usada_por_un_nodo_existe_y_sin_duplicados(doc, snap):
    cats = doc['categories']
    used = {n.get('cat') for n in snap['nodes']}
    assert used <= set(cats), sorted(used - set(cats))
    ids = list(cats)
    assert len(ids) == len(set(ids)) and all(B.ID_RX.match(i) for i in ids)
    assert len({i.lower() for i in ids}) == len(ids)


def test_cada_categoria_tiene_es_en_sector_cssvar_y_x(doc, snap):
    cats = doc['categories']
    for cid, c in cats.items():
        assert c['es'].strip() and c['en'].strip(), cid
        assert c['es'] != cid and c['en'] != cid, f'{cid}: etiqueta cruda (el id)'
        assert c['sector'] in doc['sectors'] and c['sector'] in snap['sectors9'], cid
        assert c['cssVar'] == '--c-' + cid
        assert 0 <= c['x'] <= 1
    # las de hoy conservan el sector del catálogo (CAT_TO_SECTOR) y su x
    for cid, sec in snap['cat_to_sector'].items():
        assert cats[cid]['sector'] == sec, cid
        assert cats[cid]['x'] == snap['categories'][cid].get('x', 0.5), cid
    # los 13 sectores con el MISMO color que el catálogo
    assert set(doc['sectors']) == set(snap['sectors9'])
    for k, v in snap['sectors9'].items():
        assert doc['sectors'][k]['color'] == v['color'] and doc['sectors'][k]['es'] == v['label']


def test_alias_mapean_a_un_solo_id_consolidado(doc):
    al = B.aliases(doc)
    cats = doc['categories']
    inv = {}
    for a, cid in al.items():
        assert cid in cats
        inv.setdefault(a, set()).add(cid)
    assert all(len(v) == 1 for v in inv.values())
    assert B.resolve('battery_components', doc) == 'battery_cells'
    assert B.resolve('lidar', doc) == 'ev_components' and B.resolve('fabless', doc) == 'fabless'
    assert B.resolve('no_existe', doc) is None
    # un alias nunca es a la vez un id
    assert not ({a for a, c in al.items() if a != c} & set(cats))


def test_variables_css_en_app_html_en_los_dos_temas(doc):
    app = _read('app.html')
    ri = app.index(':root{')
    light = dict(CSS_RX.findall(app[ri:app.index('}', ri)]))
    di = app.index('.dark{')
    dark = dict(CSS_RX.findall(app[di:app.index('}', di)]))
    for cid, c in doc['categories'].items():
        if c['color_source'] == 'css':
            assert light.get(cid) == c['color']['light'], (cid, light.get(cid))
            assert dark.get(cid) == c['color']['dark'], (cid, dark.get(cid))
        else:
            assert cid not in light and cid not in dark, cid
    # las nuevas con color propio son distintas entre sí (claro y oscuro) y distintas de las de hoy
    new = [c['color'] for c in doc['categories'].values() if c['origin'] != 'catalog']
    assert all(c for c in new)
    for t in ('light', 'dark'):
        vals = [c[t] for c in new]
        assert len(vals) == len(set(vals))
        assert not (set(vals) & set((light if t == 'light' else dark)[k] for k in doc['categories']
                                   if doc['categories'][k]['origin'] == 'catalog' and k in light))
    # lo que imprime --css es exactamente lo que está pegado
    assert '\n'.join(B.css_lines(doc, 'light')) in app and '\n'.join(B.css_lines(doc, 'dark')) in app
    # revisión lote K: distintas DE VERDAD (ΔE CIE76 ≥ 10 entre cada nueva y TODAS las demás --c-* del tema; antes
    # mining_equipment/power quedaban a 1,5 y rare_earth_magnets/rare_earth a 1,9: iguales en una leyenda)
    for t in ('light', 'dark'):
        d, a, b2 = B.min_delta_e(doc, t)
        assert d >= 10, (t, a, b2, d)


def test_app_html_carga_categories_extra_tras_nodes_seed():
    app = _read('app.html')
    a = app.index('<script src="nodes/nodes_seed.js"></script>')
    b = app.index('<script src="nodes/categories_extra.js"></script>')
    assert a < b and app[a:b].count('<script') == 1          # inmediatamente después
    assert app.count('<script src="nodes/categories_extra.js"></script>') == 1


def test_en_el_navegador_entran_en_cats_sin_pisar_nada(doc):
    """Sandbox de Node con nodes_seed.js → categories_extra.js → nodes_expand5.js → nodes_multicapa.js (el orden de
    app.html) y el Object.assign(CATS, CATS_NEW) de engine/app_main.js."""
    import shutil
    node = shutil.which('node')
    if not node:
        pytest.skip('sin node')
    js = r"""
const vm=require('vm'),fs=require('fs'),path=require('path');const ROOT=process.argv[1];
const ctx=vm.createContext({window:{},console,document:undefined});
for (const f of ['nodes/nodes_seed.js','nodes/categories_extra.js','nodes/nodes_expand5.js','nodes/nodes_multicapa.js'])
  vm.runInContext(fs.readFileSync(path.join(ROOT,f),'utf-8'),ctx,{filename:f});
const out=vm.runInContext(`(function(){var C=Object.assign({},CATS,CATS_NEW);return {cats:C,c2s:CAT_TO_SECTOR,
  extra:Object.keys(window.CATS_EXTRA).length, fix:window.CATS_LABELS_FIX, al:window.CAT_ALIASES,
  seed:Object.keys(CATS).length};})()`,ctx);
process.stdout.write(JSON.stringify(out));
"""
    out = json.loads(subprocess.run([node, '-e', js, ROOT], capture_output=True, text=True, timeout=60,
                                    check=True).stdout)
    cats, c2s = out['cats'], out['c2s']
    for cid, c in doc['categories'].items():
        assert cid in cats, cid
        assert cats[cid]['label'] == c['es'] and cats[cid]['en'] == c['en'], cid
        assert cats[cid]['cssVar'] == c['cssVar'] and c2s[cid] == c['sector'], cid
        assert abs(cats[cid]['x'] - c['x']) < 1e-9, cid
    assert out['extra'] == 55 and out['al']['battery_components'] == 'battery_cells'
    # las de nodes_seed.js (CATS) no cambiaron de etiqueta: categories_extra solo añade lo que falta
    with open(SNAPSHOT, encoding='utf-8') as fh:
        old = json.load(fh)['categories']
    for cid, v in old.items():
        if cid not in out['fix']:
            assert cats[cid]['label'] == v['label'] and cats[cid]['en'] == v['en'], cid
    assert 'air_cargo' in out['fix'] and cats['air_cargo']['label'] == 'Carga aérea'


def test_vocabulario_sirve_categorias_con_conteo_y_alias(doc, snap):
    from ontology import vocabulary as V
    cats = V.categories()
    assert set(cats) == set(doc['categories'])
    assert V.resolve_category('battery_components') == 'battery_cells'
    assert V.resolve_category('tin') == 'mining_tin' and V.resolve_category('nada') is None
    assert V.category_aliases()['foundry'] == 'foundry'
    # el vocabulario de relaciones no cambia por esto (los números del motor siguen iguales)
    assert 'categories' not in V.snapshot()
    os.environ.setdefault('KHIPU_SCHEDULER', 'off')
    import server
    c = server.app.test_client()
    r = c.get('/api/vocabulary')
    assert r.status_code == 200
    body = r.get_json()
    got = body['categories']
    assert set(got) == set(doc['categories'])
    assert body['category_aliases']['battery_components'] == 'battery_cells'
    assert set(body['sectors']) == set(snap['sectors9'])
    for cid, c in doc['categories'].items():
        g = got[cid]
        assert g['es'] == c['es'] and g['en'] == c['en'] and g['sector'] == c['sector']
        if c['origin'] != 'catalog':
            assert g['companies'] == 0, cid
    assert got['foundry']['companies'] >= 10 and got['fabless']['companies'] >= 30
    # los conteos salen del grafo de lectura VIGENTE (con DATABASE_URL otras pruebas pueden haber creado empresas):
    # cubren todas sus empresas y nunca menos que el catálogo
    from core.hotviews import hot
    live = hot.graph().nodes
    n_live = sum(1 for n in live if n.get('cat') in got)    # una empresa de prueba con categoría ajena no cuenta
    assert sum(g['companies'] for g in got.values()) == n_live >= len(snap['nodes'])
    assert r.headers['ETag'].startswith('"vocab-') and r.headers['ETag'].rstrip('"').split('-')[-1] != ''
    etag = r.headers['ETag']
    # el ETag lleva la huella de las categorías servidas (definiciones + conteos): otra lista → otro ETag
    import hashlib
    cats_sha = hashlib.sha256(json.dumps(got, sort_keys=True).encode('utf-8')).hexdigest()[:8]
    assert etag.endswith('-' + cats_sha + '"'), etag


def test_conteos_del_snapshot_cubren_todos_los_nodos(doc):
    counts = B.counts(doc, SNAPSHOT)
    with open(SNAPSHOT, encoding='utf-8') as fh:
        n = len(json.load(fh)['nodes'])
    assert sum(counts.values()) == n
    assert all(counts[k] == 0 for k, v in doc['categories'].items() if v['origin'] != 'catalog')
