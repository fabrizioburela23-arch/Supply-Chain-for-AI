"""tests/test_a2ui.py — A2UI v1.0 (Google, estándar abierto): Khipus habla y entiende el idioma de interfaces de agentes.

Servidor (core/genui/a2ui.py): cada sobre kblocks/1 de las doradas se traduce a mensajes A2UI válidos en los dos
catálogos (Khipus con KhipusBlock + modelo de datos; básico solo con componentes estándar), sin perder cifras, sin
ids colgando y sin un solo botón de órdenes. Navegador (engine/a2ui.js): pinta superficies, enlaza el modelo, manda
el mensaje `action` del estándar y aplica updateDataModel en vivo.
"""
import glob
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from core.genui import a2ui  # noqa: E402

BASIC_COMPONENTS = {'Text', 'Row', 'Column', 'Card', 'Button', 'Divider', 'List', 'Image'}


def _goldens():
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'tests', 'golden', 'genui_*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        if isinstance(d, dict) and isinstance(d.get('es'), list):
            out.append((os.path.basename(f), d['es']))
    assert len(out) >= 10
    return out


def _env(blocks, extra=()):
    blocks = [dict(b, id=b.get('id') if b.get('id') != 'x' else f'b{i + 1}') for i, b in enumerate(blocks)]
    blocks = [{'id': 't1', 'type': 'text', 'state': 'ready', 'data': {'md': '**Nvidia sube.** Resumen.\n- punto _info aquí_.', 'lang': 'es'}}] \
        + blocks + list(extra)
    return {'v': 'kblocks/1', 'lang': 'es', 'state': 'final', 'layout': 'auto', 'as_of': '2026-11-25T10:00:00Z',
            'blocks': blocks}


ACTIONS = {'id': 'act', 'type': 'actions', 'state': 'ready', 'data': {'items': [
    {'kind': 'open_dossier', 'entity': {'id': 'Nvidia', 'label': 'Nvidia'}, 'label': {'es': 'Dossier: Nvidia', 'en': 'Dossier: Nvidia'}}]}}
SOURCES = {'id': 'src', 'type': 'sources', 'state': 'ready', 'data': {'items': [
    {'id': 'F1', 'label': 'yahoo', 'as_of': '2026-11-25T09:00:00Z'},
    {'label': 'Reuters', 'as_of': '2026-11-25T08:00:00Z', 'url': 'https://www.reuters.com/x'}]}}


def _check(msgs, catalog):
    assert isinstance(msgs, list) and len(msgs) == 1
    m = msgs[0]
    assert m['version'] == '1.0' and set(m) == {'version', 'createSurface'}
    cs = m['createSurface']
    comps = {c['id']: c for c in cs['components']}
    assert len(comps) == len(cs['components']), 'ids repetidos'
    assert 'root' in comps
    for c in cs['components']:
        refs = list(c.get('children') or []) if isinstance(c.get('children'), list) else []
        if c.get('child'):
            refs.append(c['child'])
        for r in refs:
            assert r in comps, f'hijo colgando {r}'
        if c['component'] == 'Button':
            a = c['action']
            assert set(a) <= {'event', 'functionCall'} and len(a) == 1
            if 'event' in a:
                assert a['event']['name'].startswith('khipus.') and 'order' not in a['event']['name']
            else:
                assert a['functionCall']['@call'] == 'openUrl'
                assert a['functionCall']['args']['url'].startswith('https://')
    if catalog == 'basic':
        assert cs['catalogId'] == a2ui.BASIC_CATALOG_ID and 'dataModel' not in cs
        assert {c['component'] for c in cs['components']} <= BASIC_COMPONENTS
    else:
        assert cs['catalogId'] == a2ui.KHIPUS_CATALOG_ID
        for c in cs['components']:
            if c['component'] == 'KhipusBlock':
                key = c['block']['@path'].split('/')[-1]
                assert key in cs['dataModel']['blocks']
    return cs


@pytest.mark.parametrize('catalog', ['khipus', 'basic'])
def test_every_golden_translates_to_valid_a2ui(catalog):
    for name, blocks in _goldens():
        cs = _check(a2ui.to_a2ui(_env(blocks, (ACTIONS, SOURCES)), 'es', catalog), catalog)
        assert cs['components'][0]['id'] == 'root', name


def test_khipus_catalog_keeps_full_blocks_in_data_model():
    blocks = dict(_goldens())['genui_get_history__nvda.json']
    cs = a2ui.to_a2ui(_env(blocks), 'es', 'khipus')[0]['createSurface']
    blk = list(cs['dataModel']['blocks'].values())[0]
    assert blk['type'] == 'chart.line' and blk['data']['series'][0]['points'][-1][1] == 147.481
    kb = [c for c in cs['components'] if c['component'] == 'KhipusBlock'][0]
    assert '147,48' in kb['alt']                      # el texto alternativo trae la cifra verificada


def test_basic_catalog_shows_figures_not_charts():
    blocks = dict(_goldens())['genui_get_company__amd.json']
    cs = a2ui.to_a2ui(_env(blocks), 'en', 'basic')[0]['createSurface']
    texts = ' '.join(c.get('text', '') for c in cs['components'] if c['component'] == 'Text')
    tiles = [b for b in blocks if b['type'] == 'metric.tiles'][0]
    assert 'Price' in texts and '161' in texts       # cifra clave del bloque de cifras, con su etiqueta
    assert tiles['data']['items'][0]['value']['v'] == 161.2


def test_wants_and_capabilities():
    assert a2ui.wants({'ui_format': 'a2ui'}) == 'khipus'
    assert a2ui.wants({'ui_format': 'A2UI:basic'}) == 'basic'
    assert a2ui.wants({'a2uiRendererCapabilities': {'supportedCatalogIds': [a2ui.BASIC_CATALOG_ID]}}) == 'basic'
    assert a2ui.wants({'a2uiRendererCapabilities': {'supportedCatalogIds': [a2ui.KHIPUS_CATALOG_ID]}}) == 'khipus'
    assert a2ui.wants({}) is None and a2ui.wants('x') is None
    assert a2ui.to_a2ui(None) is None
    u = a2ui.data_update('s 1', '/blocks/b1/data/items/0/value/v', 162.0)
    assert u == {'version': '1.0', 'updateDataModel': {'surfaceId': 's_1', 'path': '/blocks/b1/data/items/0/value/v',
                                                       'value': 162.0}}


def test_chat_request_and_response_wiring(monkeypatch):
    from core import khipu_chat as kc
    req = kc.validate_request({'message': 'precio de nvidia', 'context': {'ui_format': 'a2ui:basic', 'genui': 1}})
    assert req['context']['a2ui'] == 'basic'
    assert 'a2ui' not in kc.validate_request({'message': 'hola'})['context']
    from core import genui
    env = _env(dict(_goldens())['genui_get_history__nvda.json'])
    monkeypatch.setattr(genui, 'mode', lambda: 'on')
    monkeypatch.setattr(genui, 'build_ui', lambda *a, **k: (env, ''))
    out = {'answer': 'x', 'as_of': '2026-11-25T10:00:00Z'}
    ctx = dict(req['context'])
    out['_genui'] = {'calls': []}
    kc._genui_attach(out, 'precio de nvidia', 'es', ctx)
    assert out.get('a2ui') and out['a2ui'][0]['createSurface']['catalogId'] == a2ui.BASIC_CATALOG_ID


def test_catalog_endpoint_and_wiring():
    from flask import Flask

    from core.khipu_chat import khipu_chat_bp
    app = Flask('a2ui')
    app.register_blueprint(khipu_chat_bp)
    r = app.test_client().get('/api/khipu/a2ui/catalog.json')
    assert r.status_code == 200 and r.get_json()['protocolVersion'] == '1.0'
    assert 'KhipusBlock' in r.get_json()['components']
    html = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()
    assert html.index('engine/genui.js') < html.index('engine/a2ui.js')
    assert "'/engine/a2ui.js'" in open(os.path.join(ROOT, 'sw.js'), encoding='utf-8').read()
    js = open(os.path.join(ROOT, 'engine/khipu_chat.js'), encoding='utf-8').read()
    assert "ctx.ui_format = 'a2ui'" in js and 'a2ui: d.a2ui' in js


PAGE = """<!doctype html><html><head><meta charset="utf-8"></head><body><div id="h"></div>
<script>window.KhipuGenUI={renderAnswer:function(){return 'orig'},renderBlock:function(el,b){el.textContent='BLOCK:'+b.type;return el;}};</script>
<script>%s</script></body></html>"""


def test_browser_renderer_paints_binds_and_acts(tmp_path):
    import shutil
    import subprocess
    if not shutil.which('node') or subprocess.run(['node', '-e', "require('playwright')"], capture_output=True).returncode:
        pytest.skip('requiere node + playwright (navegador real)')
    js = open(os.path.join(ROOT, 'engine', 'a2ui.js'), encoding='utf-8').read()
    msgs = a2ui.to_a2ui(_env(dict(_goldens())['genui_get_history__nvda.json'], (ACTIONS,)), 'es', 'khipus', 'srf')
    form = [{'version': '1.0', 'createSurface': {'surfaceId': 'f', 'catalogId': a2ui.BASIC_CATALOG_ID,
             'dataModel': {'name': 'Ana', 'items': [{'t': 'uno'}, {'t': 'dos'}]}, 'components': [
                 {'id': 'root', 'component': 'Column', 'children': ['hi', 'tf', 'lst', 'go']},
                 {'id': 'hi', 'component': 'Text', 'text': {'@call': 'formatString', 'args': {'value': 'Hola ${/name}'}}},
                 {'id': 'tf', 'component': 'TextField', 'label': 'Nombre', 'value': {'@path': '/name'}},
                 {'id': 'lst', 'component': 'List', 'children': {'path': '/items', 'componentId': 'it'}},
                 {'id': 'it', 'component': 'Text', 'text': {'@path': 't'}},
                 {'id': 'go', 'component': 'Button', 'child': 'gol',
                  'action': {'event': {'name': 'save', 'context': {'who': {'@path': '/name'}}}}},
                 {'id': 'gol', 'component': 'Text', 'text': 'Guardar'}]}}]
    (tmp_path / 'page.html').write_text(PAGE % js, encoding='utf-8')
    (tmp_path / 'args.json').write_text(json.dumps({'msgs': msgs, 'form': form}), encoding='utf-8')
    script = """
const { chromium } = require('playwright'); const fs = require('fs');
(async () => {
  const dir = process.argv[1], args = JSON.parse(fs.readFileSync(dir + '/args.json', 'utf8'));
  const b = await chromium.launch(); const pg = await b.newPage();
  await pg.setContent(fs.readFileSync(dir + '/page.html', 'utf8'));
  const res = await pg.evaluate((a) => {
    const h = document.getElementById('h'), got = [];
    KhipuA2UI.process(h, a.msgs, {onAction: m => got.push(m)});
    const khipus = h.textContent;
    h.querySelector('button').click();
    const f = document.createElement('div'); document.body.appendChild(f);
    KhipuA2UI.process(f, a.form, {onAction: m => got.push(m)});
    const before = f.textContent;
    const inp = f.querySelector('input'); inp.value = 'Luz'; inp.dispatchEvent(new Event('input'));
    f.querySelectorAll('button')[0].click();
    KhipuA2UI.update('f', '/name', 'Sol');
    return {khipus, before, after: f.textContent, got, model: KhipuA2UI.get('f').model.name};
  }, args);
  await b.close(); console.log(JSON.stringify(res));
})().catch(e => { console.error(e); process.exit(1); });
"""
    r = subprocess.run(['node', '-e', script, str(tmp_path)], capture_output=True, text=True, timeout=90)
    assert r.returncode == 0, r.stderr[-800:]
    res = json.loads(r.stdout.strip().splitlines()[-1])
    assert 'BLOCK:chart.line' in res['khipus'] and 'Nvidia sube.' in res['khipus']
    assert '• punto info aquí.' in res['khipus'] and '_' not in res['khipus'].split('BLOCK')[0]   # viñeta y cursiva sin símbolos
    assert res['got'][0]['action']['name'] == 'khipus.open_dossier'
    assert res['got'][0]['action']['context'] == {'kind': 'open_dossier', 'entity': 'Nvidia'}
    assert 'Hola Ana' in res['before'] and 'uno' in res['before'] and 'dos' in res['before']
    save = res['got'][1]
    assert save['version'] == '1.0' and save['action']['name'] == 'save' and save['action']['context'] == {'who': 'Luz'}
    assert save['action']['surfaceId'] == 'f' and save['action']['sourceComponentId'] == 'go'
    assert 'Hola Sol' in res['after'] and res['model'] == 'Sol'
