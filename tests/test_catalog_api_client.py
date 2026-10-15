"""tests/test_catalog_api_client.py — EXPANSION_5K E3.1 (lote L): engine/catalog_sync.js, el adaptador del navegador.

Con un navegador simulado (node + vm, sin d3: el mapa se prueba con Playwright) se fija el contrato:
  · SOLO AÑADE: un nodo que el navegador ya tiene no se repite ni se toca (mismo objeto); un vínculo con la misma
    clave origen→destino·tipo no se repite; extremos por _canonId (un id alias cae en su canónico); sin extremo o
    a sí mismo → fuera (contado);
  · alias de la base y nombres para la búsqueda: solo claves que no existían (LEGAL_NAMES / NODE_ID_ALIAS);
  · tamaño: la valuación VERIFICADA entra a NODE_META solo para empresas nuevas y nunca pisa una capitalización
    que ya está (la en vivo manda); sin dato → capStatus 'none' (el mapa la marca «Sin capitalización»);
  · el NRS se invalida UNA vez; la señal 🔴/🟡 llega sin el texto; los textos y el texto de cada vínculo se piden al
    abrir la ficha (una vez) y la ficha se vuelve a pintar si sigue abierta;
  · diferencia vacía, error o 503 → no se toca nada; páginas de UNA generación (409 → empieza de nuevo).
Y en estático: el orden en app.html, las reglas del mapa (nada de sim.alpha().restart() ni azar) y d3 v7.
"""
import json
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')

HARNESS = r"""
const fs = require('fs'), vm = require('vm');
const ROOT = process.argv[1], SCEN = process.argv[2];
const src = fs.readFileSync(ROOT + '/engine/catalog_sync.js', 'utf-8');
const NF = ['id','label','cat','sector','country','country_iso2','ticker','mkt','status','preipo','margin','gflag'];
const LF = ['source','target','w','type','conf','verified','since'];
function page(o) {
  return Object.assign({generation: 'g7', graph_version: 7, source: 'pg', fallback: false, node_fields: NF, link_fields: LF,
    nodes: [], links: [], valuations: {}, names: {}, aliases: {}, flow_types: ['supply'], total_nodes: 0, total_links: 0,
    offset: 0, limit: 5000, next_offset: null}, o);
}
const DELTA = page({
  nodes: [['DbOne', 'Db One', 'memory', 'semis', 'Corea', 'KR', 'X1 · Corea (KRX)', 'X1.KS', 'public', 0, 0.2, 'r'],
          ['DbTwo', 'Db Two', 'memory', null, 'EEUU', 'US', '', null, 'private', 1, null, null],
          ['TSMC', 'NO PISAR', 'x', null, null, null, '', null, null, 0, null, null]],
  links: [['TSM_alias', 'DbOne', 4, 'supply', 0.3, false, null], ['DbOne', 'DbTwo', 1, 'partner', 0.9, true, '2024-05'],
          ['TSMC', 'Nvidia', 9, 'supply', 1, true, null], ['DbOne', 'Ghost', 2, 'supply', 1, true, null],
          ['DbOne', 'DbOne', 2, 'supply', 1, true, null]],
  valuations: {DbTwo: {usd_b: 2.5, as_of: '2026-01', round: 'Serie B', source_url: 'https://x.com/a', confidence: 0.8},
               Nvidia: {usd_b: 1, as_of: '2020', source_url: 'https://x.com/b'}},
  names: {'Existing Name': 'DbOne', 'Db One Legal': 'DbOne'},
  aliases: {OldDb: 'DbOne', TSM_alias: 'DbTwo'}, total_nodes: 3, total_links: 5});
const DETAIL = {data: {nodes: {DbOne: {role: 'Rol de Db One', role_en: 'Db One role', growth: '🔴 caen las ventas 10 %',
  hq_city: 'Seúl', founded: '1999', employees: 1200, listing: {symbol: 'X1', yahoo_symbol: 'X1.KS'}}},
  rels: [['TSMC', 'DbOne', 'supply', 'Obleas de prueba']], unknown_ids: [], catalog_ids: [], generation: 'g7'}};
const calls = [];
function resp(status, body) {
  return Promise.resolve({status, headers: {get: () => 'application/json'}, json: () => Promise.resolve(body)});
}
let pageCalls = 0;
function route(url) {
  calls.push(url);
  if (url.indexOf('/api/hot/catalog/detail') === 0) return resp(200, DETAIL);
  if (SCEN === 'empty') return resp(200, {data: page({})});
  if (SCEN === 'error') return resp(500, {error: 'x'});
  if (SCEN === 'paged') {
    pageCalls++;
    if (pageCalls === 1) return resp(200, {data: page({nodes: DELTA.nodes.slice(0, 1), next_offset: 1, total_nodes: 2})});
    if (pageCalls === 2) return resp(409, {code: 'generation_changed', generation: 'g8'});
    if (pageCalls === 3) return resp(200, {data: page({generation: 'g8', nodes: DELTA.nodes.slice(0, 1), next_offset: 1, total_nodes: 2})});
    return resp(200, {data: page({generation: 'g8', offset: 1, nodes: DELTA.nodes.slice(1, 2), total_nodes: 2})});
  }
  return resp(200, {data: DELTA});
}
const TSMC = {id: 'TSMC', label: 'TSMC', ticker: 'TSM', cat: 'foundry', country: 'Taiwan'};
const NV = {id: 'Nvidia', label: 'Nvidia', ticker: 'NVDA', cat: 'gpu', country: 'EEUU'};
const NODES = [TSMC, NV], LINKS = [{source: 'TSMC', target: 'Nvidia', w: 5, rel: 'x', type: 'supply'}];
const NB = {TSMC, Nvidia: NV, TSM_alias: TSMC};
const rendered = [];
const W = {NODES, LINKS, NODE_BY_ID: NB, NODE_META: {Nvidia: {mktcap_b: 4000, mktcap_live: {}}},
  LEGAL_NAMES: {'Existing Name': 'TSMC'}, NODE_ID_ALIAS: {TSM_alias: 'TSMC'}, LANG: 'es', selected: 'DbOne',
  _canonId: id => (NB[id] && NB[id].id) || id, _invalidateNRS() { W.__inv = (W.__inv || 0) + 1; },
  renderDetail(id) { rendered.push(id); }, dispatchEvent(e) { W.__ev = (W.__ev || []).concat([e.type]); },
  KhipuCountries: {label: (c, l) => c === 'KR' ? (l === 'en' ? 'South Korea' : 'Corea del Sur') : c},
  document: {readyState: 'complete', addEventListener() {}, getElementById() { return null; }},
  localStorage: {getItem() { return null; }}, performance: {now: () => Date.now()},
  CustomEvent: function (t, o) { this.type = t; this.detail = o && o.detail; },
  fetch: route, setTimeout, Promise, JSON, Math, Date, Set, Object, Array, String, Number, isFinite, encodeURIComponent, console};
W.window = W;
vm.createContext(W);
vm.runInContext(src, W, {filename: 'catalog_sync.js'});
(async () => {
  const st = await W.KhipuCatalogSync.ready;
  const out = {st, calls: calls.slice(), nodes: NODES.map(n => n.id), tsmcSame: NB.TSMC === TSMC && TSMC.label === 'TSMC' && !TSMC.from_db,
    links: LINKS.map(l => [l.source, l.target, l.type, l.w, l.conf, l.verified, l.since || null, !!l.from_db]),
    inv: W.__inv || 0, ev: W.__ev || [], meta: W.NODE_META, ln: W.LEGAL_NAMES, ida: W.NODE_ID_ALIAS,
    oldDb: NB.OldDb ? NB.OldDb.id : null, tsmAlias: NB.TSM_alias.id};
  if (NB.DbOne) {
    const d = NB.DbOne;
    out.dbOne = {growth: d.growth, loc: d.loc, listing: d.listing, ticker: d.ticker, mkt: d.mkt, margin: d.margin, from_db: d.from_db, role: d.role};
    out.dbTwo = NB.DbTwo ? {preipo: NB.DbTwo.preipo, mkt: NB.DbTwo.mkt, ticker: NB.DbTwo.ticker, growth: NB.DbTwo.growth} : null;
    out.cap = {DbOne: W.KhipuCatalogSync.capStatus('DbOne'), DbTwo: W.KhipuCatalogSync.capStatus('DbTwo'), Nvidia: W.KhipuCatalogSync.capStatus('Nvidia')};
    out.isDb = [W.KhipuCatalogSync.isDbNode('OldDb'), W.KhipuCatalogSync.isDbNode('TSMC')];
    W.renderDetail('DbOne');                       // la ficha abierta pide los textos (una vez)
    await new Promise(r => setTimeout(r, 30));
    await W.KhipuCatalogSync.ensureDetail('DbOne');
    await W.KhipuCatalogSync.ensureDetail('OldDb');
    out.after = {role: d.role, role_en: d.role_en, growth: d.growth, loc: d.loc, listing: d.listing,
                 founded: (W.NODE_META.DbOne || {}).founded, rel: (LINKS.find(l => l.source === 'TSMC' && l.target === 'DbOne') || {}).rel};
    out.detailCalls = calls.filter(u => u.indexOf('/detail') > 0);
    out.rendered = rendered.slice();
    out.inv2 = W.__inv || 0;
  }
  process.stdout.write(JSON.stringify(out));
})().catch(e => { process.stdout.write(JSON.stringify({fatal: String(e && e.stack || e)})); });
"""


def _run(scen):
    out = subprocess.run([NODE, '-e', HARNESS, ROOT, scen], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr[-800:]
    r = json.loads(out.stdout)
    assert 'fatal' not in r, r.get('fatal')
    return r


needs_node = pytest.mark.skipif(not NODE, reason='requiere node')


@needs_node
def test_solo_anade_y_nunca_pisa():
    r = _run('full')
    st = r['st']
    assert st['phase'] == 'done' and st['map'] == 'no_map' and st['generation'] == 'g7'
    assert (st['added_nodes'], st['added_links']) == (2, 2)
    assert st['skipped'] == {'existing_node': 1, 'existing_link': 1, 'missing_endpoint': 1, 'self_loop': 1}
    assert r['nodes'] == ['TSMC', 'Nvidia', 'DbOne', 'DbTwo'] and r['tsmcSame']
    assert r['links'][0] == ['TSMC', 'Nvidia', 'supply', 5, None, None, None, False]       # el del catálogo, intacto
    assert ['TSMC', 'DbOne', 'supply', 4, 0.3, False, None, True] in r['links']            # alias → canónico
    assert ['DbOne', 'DbTwo', 'partner', 1, 0.9, True, '2024-05', True] in r['links']
    assert len(r['links']) == 3
    assert r['inv'] == 1 and r['ev'] == ['khipu:catalogsync']
    d1, d2 = r['dbOne'], r['dbTwo']
    assert (d1['growth'], d1['loc'], d1['ticker'], d1['mkt'], d1['margin'], d1['from_db'], d1['role']) == \
        ('🔴', 'Corea del Sur', 'X1 · Corea (KRX)', 'X1.KS', 0.2, True, '')
    assert d1['listing'] == {'status': 'public', 'source': 'ontology'}
    assert d2 == {'preipo': True, 'mkt': None, 'ticker': '', 'growth': ''}


@needs_node
def test_alias_nombres_y_tamano():
    r = _run('full')
    assert r['oldDb'] == 'DbOne' and r['ida']['OldDb'] == 'DbOne'
    assert r['tsmAlias'] == 'TSMC' and r['ida']['TSM_alias'] == 'TSMC'       # un alias existente no se pisa
    assert r['ln'] == {'Existing Name': 'TSMC', 'Db One Legal': 'DbOne'}
    m = r['meta']
    assert m['DbTwo']['mktcap_b'] == 2.5 and m['DbTwo']['mktcap_verified']['label'] == '$2.5B (2026-01)'
    assert m['DbTwo']['mktcap_verified']['source_url'] == 'https://x.com/a'
    assert m['Nvidia'] == {'mktcap_b': 4000, 'mktcap_live': {}}             # solo empresas nuevas; nunca pisa
    assert r['cap'] == {'DbOne': 'none', 'DbTwo': 'verified', 'Nvidia': 'live'}
    assert r['isDb'] == [True, False]
    assert r['st']['valuations'] == 1 and r['st']['names'] == 1 and r['st']['aliases'] == 1


@needs_node
def test_textos_a_pedido_una_vez():
    r = _run('full')
    a = r['after']
    assert (a['role'], a['role_en'], a['growth']) == ('Rol de Db One', 'Db One role', '🔴 caen las ventas 10 %')
    assert a['loc'] == 'Seúl, Corea del Sur' and a['founded'] == '1999' and a['rel'] == 'Obleas de prueba'
    assert a['listing']['status'] == 'public' and a['listing']['yahoo_symbol'] == 'X1.KS'
    assert r['detailCalls'] == ['/api/hot/catalog/detail?ids=DbOne']          # una vez (alias incluido)
    assert r['rendered'].count('DbOne') >= 2                                 # la ficha abierta se vuelve a pintar
    assert r['inv2'] == 1                                                    # los textos no cambian el NRS (misma señal 🔴)


@needs_node
@pytest.mark.parametrize('scen,phase', [('empty', 'empty'), ('error', 'error')])
def test_sin_diferencia_o_con_error_no_toca_nada(scen, phase):
    r = _run(scen)
    assert r['st']['phase'] == phase and r['nodes'] == ['TSMC', 'Nvidia'] and len(r['links']) == 1
    assert r['inv'] == 0 and r['ev'] == [] and 'dbOne' not in r
    assert r['ln'] == {'Existing Name': 'TSMC'}


@needs_node
def test_paginas_de_una_generacion():
    r = _run('paged')
    assert r['calls'][:4] == ['/api/hot/catalog?offset=0', '/api/hot/catalog?offset=1&gen=g7',
                              '/api/hot/catalog?offset=0', '/api/hot/catalog?offset=1&gen=g8']
    assert r['st']['generation'] == 'g8' and r['st']['pages'] == 2 and r['nodes'] == ['TSMC', 'Nvidia', 'DbOne', 'DbTwo']


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as fh:
        return fh.read()


def test_orden_en_app_html():
    html = _read('app.html')
    i_merge = html.index('<script src="nodes/merge_graph.js"></script>')
    i_sync = html.index('<script src="engine/catalog_sync.js"></script>')
    i_main = html.index('<script src="engine/app_main.js"></script>')
    assert i_merge < i_sync < i_main                     # pide temprano; aplica en DOMContentLoaded (tras app_main)
    assert html.count('engine/catalog_sync.js') == 1


def test_reglas_del_mapa_y_del_tamano():
    js = _read('engine/catalog_sync.js')
    code = re.sub(r'/\*[\s\S]*?\*/|//[^\n]*', '', js)
    assert '.restart(' not in code and 'alphaTarget' not in code      # la física solo se adelanta sin dibujar
    assert 'Math.random' not in code                                   # posiciones deterministas; tamaño nunca al azar
    assert '_resizeNodesByCap' in code and 'computeNodeRadius(' in code
    assert 'computeNodeRadius =' not in code and 'function computeNodeRadius' not in code
    assert 'Sin capitalización' in code and 'No market cap' in code    # bilingüe
    assert 'innerHTML' not in code                                     # el aviso se arma con textContent
    assert "fetch(" in code and '/api/hot/catalog' in code and '/v1/' not in code


def test_d3_v7_contrato_interno():
    """El adaptador entra a las selecciones vivas del mapa (`_groups`) y copia los manejadores (`__on`): forma
    interna de d3 v4-v7. Si alguien cambia de versión mayor, esta prueba avisa (y el adaptador tiene respaldo de clic)."""
    assert re.search(r'cdnjs\.cloudflare\.com/ajax/libs/d3/7\.\d+\.\d+/d3\.min\.js', _read('app.html'))
    assert re.search(r"'d3\.min\.js':\s*'https://cdnjs\.cloudflare\.com/ajax/libs/d3/7\.\d+\.\d+/d3\.min\.js'", _read('server.py'))
    js = _read('engine/catalog_sync.js')
    assert 'nodeSel._groups' in js and '__on' in js and "selectNode(d.id)" in js
