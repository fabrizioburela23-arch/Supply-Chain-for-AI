"""Khipus OS v1 — correcciones de la revisión en engine/oswindows.js (clave «windows»).

Cada prueba falla con la versión anterior del archivo y pasa con el arreglo:
  #6/#7  «En una mirada» pintaba un precio YA convertido a USD con el símbolo de la moneda
         local («₩14», «CN¥14,00» para ~$14). Contrato de MKT.quotes (igual que xray.js):
         converted:true → el monto está en USD; se rotula «convertido de KRW».
  #9     el veredicto de «en una mirada» tomaba el último memo del comité aunque fuera de un
         CLIENTE del corretaje (HOLD/TRIM/AVOID propios de ese cliente). Ahora solo memos
         generales (client_id nulo), la misma regla que la Pizarra.
  #10    «Tus agentes» mostraba el historial COMBINADO de los analistas como acierto propio del
         Comité (y en Pro, su «fiabilidad»). Ahora se rotula combinado y sin Brier/fiabilidad.
"""
import json
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, 'engine', 'oswindows.js')
SRC = open(PATH, encoding='utf-8').read()
NODE = shutil.which('node')


# ─────────────────────────────── node vm (funciones puras) ───────────────────────────────
VM_PRELUDE = r"""
const fs = require('fs'), vm = require('vm');
const win = { LANG: 'es', addEventListener(){}, explainRegister(){} };
const ctx = { window: win, console, setTimeout, clearTimeout, setInterval: () => 0, clearInterval(){},
  localStorage: { getItem(){ return null; }, setItem(){} },
  document: { readyState: 'complete', hidden: false, getElementById(){ return null; }, addEventListener(){},
              documentElement: {}, head: { appendChild(){} }, createElement(){ return {}; } } };
ctx.window.window = ctx.window;
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), ctx);
const W = ctx.window, H = W.KhipuOSWin._h;
"""


def _node(js):
    r = subprocess.run([NODE, '-e', VM_PRELUDE + js, PATH], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_6_7_moneda_del_monto_segun_el_contrato_de_cotizaciones():
    o = _node(r"""process.stdout.write(JSON.stringify({
      c1: H.quoteCur({currency: 'CNY', converted: true}), c2: H.quoteCur({currency: 'USD', converted: false}),
      c3: H.quoteCur({}), c4: H.quoteCur(null), c5: H.quoteCur({currency: 'KRW'}),
      o1: H.quoteOrigCur({currency: 'TWD', converted: true}), o2: H.quoteOrigCur({currency: 'GBp', converted: true}),
      o3: H.quoteOrigCur({currency: 'USD', converted: false}), o4: H.quoteOrigCur({currency: 'KRW'}),
      o5: H.quoteOrigCur({currency: 'ZAc', converted: true}), o6: H.quoteOrigCur(null),
      m1: H.fmtMoney(9.85, H.quoteCur({currency: 'TWD', converted: true}), 'es') }));
      process.exit(0);""")
    assert o['c1'] == 'USD' and o['c2'] == 'USD' and o['c3'] == 'USD' and o['c4'] == 'USD'
    assert o['c5'] == 'KRW'                       # sin conversión, el monto está en su moneda (contrato)
    assert o['o1'] == 'TWD' and o['o2'] == 'GBP' and o['o5'] == 'ZAR'   # peniques/centavos → moneda entera
    assert o['o3'] == '' and o['o4'] == '' and o['o6'] == ''
    assert o['m1'] == '$9,85'                     # nunca «NT$9,85» para 9,85 USD


def test_6_7_estatico_sin_moneda_original_en_los_montos():
    assert 'fmtMoney(qq.px, qq.q && qq.q.currency)' not in SRC
    assert SRC.count('esc(quoteMoney(qq))') == 2
    assert "L('convertido de ' + oc, 'converted from ' + oc)" in SRC


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_9_memo_general_nunca_el_de_un_cliente():
    o = _node(r"""
      const gen = {memo_id: 'g1', client_id: null, decision: 'BUY', overall_conviction: 30};
      const cli = {memo_id: 'c1', client_id: 'house', decision: 'HOLD', overall_conviction: 42};
      const hist = [{memo_id: 'c1', has_client: true, status: 'proposed'}, {memo_id: 'r1', has_client: false, status: 'running'},
                    {memo_id: 'f1', has_client: false, status: 'failed'}, {memo_id: 'g1', has_client: false, status: 'approved'}];
      process.stdout.write(JSON.stringify({
        a: H.generalMemoOf({latest: gen, history: []}),
        b: H.generalMemoOf({latest: cli, history: hist}),
        c: H.generalMemoOf({latest: cli, history: [hist[0]]}),
        d: H.generalMemoOf({latest: cli, latest_general: gen, history: hist}),
        e: H.generalMemoOf({latest: cli, latest_general: null, history: hist}),
        f: H.generalMemoOf(null), g: H.generalMemoOf({latest: null, history: []}) }));
      process.exit(0);""")
    assert o['a']['memo']['memo_id'] == 'g1' and 'fetchId' not in o['a']
    assert o['b'] == {'memo': None, 'fetchId': 'g1'}         # el último GENERAL terminado del historial
    assert o['c'] == {'memo': None}                          # solo memos de clientes → sin veredicto general
    assert o['d']['memo']['memo_id'] == 'g1'                 # servidor que ya manda latest_general
    assert o['e'] == {'memo': None}
    assert o['f'] == {'memo': None} and o['g'] == {'memo': None}


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_10_historial_del_comite_es_combinado():
    o = _node(r"""process.stdout.write(JSON.stringify({
      a: H.isPooledTrack({id: 'comite', track: {}}), b: H.isPooledTrack({id: 'analista', track: {scope: 'overall'}}),
      c: H.isPooledTrack({id: 'analista', track: {scope: 'agents'}}), d: H.isPooledTrack(null) })); process.exit(0);""")
    assert o == {'a': True, 'b': True, 'c': False, 'd': False}


# ─────────────────────────── navegador (Playwright) ───────────────────────────
def _chromium(p):
    for kw in ({}, {'executable_path': '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'}):
        try:
            return p.chromium.launch(**kw)
        except Exception:  # noqa: BLE001
            continue
    return None


PAGE = r"""<!doctype html><html lang="es"><head><meta charset="utf-8"><style>
.kd-body{width:560px;height:560px;overflow:auto;padding:16px}
</style></head><body><div id="h"><div class="kd-body" id="b1"></div><div class="kd-body" id="b2"></div></div>
<input id="bcp-input">
<script>
window.LANG='es';
window.calls={committee:[],research:[],prefs:[]};
var N=[{id:'Nvidia',label:'Nvidia',mkt:'NVDA'},{id:'SKHynix',label:'SK Hynix',mkt:'000660.KS'},{id:'CXMT',label:'CXMT',mkt:'688825.SS'}];
window.NODES=N; window.NODE_BY_ID={}; N.forEach(function(n){window.NODE_BY_ID[n.id]=n;});
window._canonId=function(i){var n=window.NODE_BY_ID[i];return (n&&n.id)||i;};
window.LINKS=[];
var T=new Date(Date.now()-60000).toISOString();
// core/quotes.fetch_quote_intl: monto en USD, `currency` = moneda ORIGINAL de la bolsa, converted:true
window.MKT={quotes:{NVDA:{close:182.4,live:182.4,prev:180.18,pct:1.23,src:'finnhub',as_of:T,currency:'USD'},
  '000660.KS':{close:14,live:14,prev:13.8,pct:1.45,src:'yahoo',as_of:T,currency:'KRW',converted:true},
  '688825.SS':{close:14,live:14,prev:14,pct:0,src:'yahoo',via:'live_caps',as_of:T,currency:'CNY',converted:true}}};
window.quotePx=function(q){return q?(typeof q.live==='number'?q.live:q.close):0;};
window.KhipuCommittee={open:function(id){calls.committee.push(id);}};
window.KhipuResearch={open:function(id){calls.research.push(id);}};
var PREF={mode:'simple',agents:{khipu:{on:true,auto:true},analista:{on:true,auto:true},radar:{on:true,auto:false},cadena:{on:true,auto:true},tecnico:{on:true,auto:false},comite:{on:true,auto:true}}};
window.KhipuAgentPrefs={get:function(){return JSON.parse(JSON.stringify(PREF));},set:function(p){calls.prefs.push(p);return PREF;}};
</script></body></html>"""


def _memo(mid, decision, conv, client_id=None, status='proposed'):
    return {'memo_id': mid, 'entity_id': 'SKHynix', 'status': status, 'decision': decision, 'overall_conviction': conv,
            'client_id': client_id, 'client_mode': 'client' if client_id else None,
            'created_at': '2026-10-06T10:00:00+00:00', 'expires_at': '2026-10-09T10:00:00+00:00', 'expired': False,
            'memo': {'decision_code': None, 'thesis': [], 'key_risks': []}}


def _page(b, state):
    """state: prefijo de ruta → (status, json). Sin entrada → 503 (sin base de datos)."""
    pg = b.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    seen = []

    def handler(route):
        url = route.request.url
        path = url.split('khipu.test', 1)[1]
        if path in ('/', '/index.html'):
            return route.fulfill(status=200, content_type='text/html', body=PAGE)
        seen.append(path)
        for k, (st, body) in state.items():
            if path.startswith(k):
                return route.fulfill(status=st, content_type='application/json', body=json.dumps(body))
        return route.fulfill(status=503, content_type='application/json', body=json.dumps({'error': 'no disponible', 'error_en': 'not available'}))
    pg.route('http://khipu.test/**', handler)
    pg.goto('http://khipu.test/')
    pg.add_script_tag(content=SRC)
    return pg, errs, seen


@pytest.fixture(scope='module')
def browser():
    pw = pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        b = _chromium(p)
        if not b:
            pytest.skip('Chromium no disponible')
        yield b
        b.close()


def test_6_7_numero_grande_en_usd_con_rotulo_de_conversion(browser):
    pg, errs, _ = _page(browser, {})                                     # sin comité → el número grande es el PRECIO
    pg.evaluate("KhipuOSWin.render('glance', document.getElementById('b1'), {id:'SKHynix'})")
    pg.wait_for_function("() => /Sin veredicto/.test(document.getElementById('b1').innerText)", timeout=5000)
    big = pg.inner_text('#b1 [data-r=main] .osw-big')
    assert big == '$14,00', big                                          # antes: «₩14» (14 USD con símbolo de won)
    assert '₩' not in pg.inner_text('#b1')
    assert 'convertido de KRW' in pg.inner_text('#b1 [data-r=main]')
    # CNY por el relleno de live_caps: igual
    pg.evaluate("KhipuOSWin.render('glance', document.getElementById('b2'), {id:'CXMT'})")
    pg.wait_for_function("() => /Sin veredicto/.test(document.getElementById('b2').innerText)", timeout=5000)
    assert pg.inner_text('#b2 [data-r=main] .osw-big') == '$14,00' and 'CN¥' not in pg.inner_text('#b2')
    # idioma inglés
    pg.evaluate("window.LANG='en'; document.documentElement.lang='en'")
    pg.wait_for_function("() => /converted from KRW/.test(document.getElementById('b1').innerText)", timeout=3000)
    assert pg.inner_text('#b1 [data-r=main] .osw-big') == '$14.00'
    assert not errs


def test_6_7_linea_de_precio_sobre_el_veredicto_en_usd(browser):
    ent = {'entity_id': 'SKHynix', 'latest': _memo('g1', 'BUY', 30), 'history': [{'memo_id': 'g1', 'has_client': False, 'status': 'proposed'}]}
    pg, errs, _ = _page(browser, {'/api/committee/entity/': (200, ent)})
    pg.evaluate("KhipuOSWin.render('glance', document.getElementById('b1'), {id:'SKHynix'})")
    pg.wait_for_function("() => { const e = document.querySelector('#b1 [data-r=quote]'); return e && !e.hidden && /000660/.test(e.innerText); }", timeout=5000)
    line = pg.inner_text('#b1 [data-r=quote]')
    assert '$14,00' in line and '₩' not in line and 'convertido de KRW' in line, line
    # una cotización en USD de verdad no cambia ni lleva rótulo de conversión
    pg.evaluate("KhipuOSWin.render('glance', document.getElementById('b2'), {id:'Nvidia'})")
    pg.wait_for_function("() => { const e = document.querySelector('#b2 [data-r=quote]'); return e && !e.hidden && /NVDA/.test(e.innerText); }", timeout=5000)
    l2 = pg.inner_text('#b2 [data-r=quote]')
    assert '$182,40' in l2 and 'convertido' not in l2
    assert not errs


def test_9_glance_ignora_el_memo_de_un_cliente_y_usa_el_general(browser):
    cli = _memo('c1', 'HOLD', 42, client_id='house')                     # HOLD: «no se puede operar en Alpaca»
    gen = _memo('g1', 'BUY', 30, status='approved')
    ent = {'entity_id': 'SKHynix', 'latest': cli, 'history': [
        {'memo_id': 'c1', 'has_client': True, 'status': 'proposed'},
        {'memo_id': 'g1', 'has_client': False, 'status': 'approved'}]}
    pg, errs, seen = _page(browser, {'/api/committee/entity/': (200, ent), '/api/committee/memo/g1': (200, gen)})
    pg.evaluate("KhipuOSWin.render('glance', document.getElementById('b1'), {id:'SKHynix'})")
    pg.wait_for_function("() => { const n = document.querySelector('#b1 [data-r=num]'); return n && n.textContent === '+30'; }", timeout=5000)
    t = pg.inner_text('#b1')
    assert 'Comité: comprar' in t and 'aprobada por una persona' in t
    assert 'mantener' not in t and '+42' not in t
    assert '/api/committee/memo/g1' in seen
    assert not errs


def test_9_solo_memos_de_clientes_no_hay_veredicto_general(browser):
    ent = {'entity_id': 'SKHynix', 'latest': _memo('c1', 'TRIM', 42, client_id='house'),
           'history': [{'memo_id': 'c1', 'has_client': True, 'status': 'proposed'}]}
    pg, errs, seen = _page(browser, {'/api/committee/entity/': (200, ent)})
    pg.evaluate("KhipuOSWin.render('glance', document.getElementById('b1'), {id:'SKHynix'})")
    pg.wait_for_function("() => /Sin veredicto aún/.test(document.getElementById('b1').innerText)", timeout=5000)
    t = pg.inner_text('#b1')
    assert 'Comité:' not in t and 'reducir' not in t and 'Revisar propuesta' not in t
    assert pg.inner_text('#b1 [data-r=main] .osw-big') == '$14,00'       # el número grande vuelve a ser el precio
    assert not [p for p in seen if p.startswith('/api/committee/memo/')]
    # servidor con latest_general explícito: manda ese y no se pide nada más
    ent2 = dict(ent, latest_general=_memo('g2', 'AVOID', -25))
    pg2, errs2, seen2 = _page(browser, {'/api/committee/entity/': (200, ent2)})
    pg2.evaluate("KhipuOSWin.render('glance', document.getElementById('b1'), {id:'SKHynix'})")
    pg2.wait_for_function("() => /Comité: evitar/.test(document.getElementById('b1').innerText)", timeout=5000)
    assert not [p for p in seen2 if p.startswith('/api/committee/memo/')]
    assert not errs and not errs2


def test_10_comite_rotulado_como_historial_combinado_sin_fiabilidad(browser):
    tr = {'n_scored': 40, 'hits': 25, 'hit_rate': 0.625, 'brier': 0.21, 'reliability': 0.58, 'sufficient': True}
    prof = {'db': True, 'as_of': '2026-10-06T10:00:00+00:00', 'agents': [
        {'id': 'analista', 'track': dict(tr, n_scored=12, hits=8, hit_rate=0.6667, reliability=0.61)},
        {'id': 'comite', 'track': dict(tr, scope='overall')}]}
    pg, errs, _ = _page(browser, {'/api/agents/profiles': (200, prof)})
    pg.evaluate("PREF.mode='pro'; KhipuOSWin.render('agents', document.getElementById('b1'))")
    pg.wait_for_function("() => /63\\s% de aciertos/.test(document.querySelector('#b1 article[data-agent=comite]').innerText)", timeout=5000)
    com = pg.inner_text('#b1 article[data-agent=comite] .osw-ag-track')
    assert com.startswith('Historial combinado de los analistas (el comité no se califica solo)'), com
    assert 'fiabilidad' not in com and 'Brier' not in com
    ana = pg.inner_text('#b1 article[data-agent=analista] .osw-ag-track')
    assert 'fiabilidad 61' in ana and 'Brier' in ana and 'combinado' not in ana   # un analista sí tiene su historial
    # servidor anterior (sin scope): el Comité igual se rotula combinado
    prof2 = json.loads(json.dumps(prof))
    del prof2['agents'][1]['track']['scope']
    pg2, errs2, _ = _page(browser, {'/api/agents/profiles': (200, prof2)})
    pg2.evaluate("window.LANG='en'; document.documentElement.lang='en'; PREF.mode='pro'; KhipuOSWin.render('agents', document.getElementById('b1'))")
    pg2.wait_for_function("() => /63% hit rate/.test(document.querySelector('#b1 article[data-agent=comite]').innerText)", timeout=5000)
    com2 = pg2.inner_text('#b1 article[data-agent=comite] .osw-ag-track')
    assert com2.startswith('Combined record of the analysts (the committee is not scored on its own)') and 'reliability' not in com2
    assert not errs and not errs2


def test_fix8_tooltip_de_conviccion_no_presenta_memo_vencido_como_vigente():
    import shutil
    import subprocess
    node = shutil.which('node')
    if not node:
        return
    src = open(os.path.join(ROOT, 'engine', 'oswindows.js'), encoding='utf-8').read()
    import re
    fn = re.search(r'function memoLine\(memo, DEC\) \{.*?\n  \}\n', src, re.S).group(0)
    js = ("var L=function(a,b){return a};var fmtWhen=function(){return '6 oct'};" + fn +
          "var D={BUY:['comprar','buy']};console.log(JSON.stringify([memoLine({decision:'BUY'},D),memoLine({decision:'BUY',expired:true},D),"
          "memoLine({decision:'HOLD',decision_code:'INSUFFICIENT_DATA'},D),memoLine({decision:'BUY',status:'rejected'},D)]))")
    out = json.loads(subprocess.run([node, '-e', js], capture_output=True, text=True, timeout=20).stdout)
    assert out[0] == 'Comité: comprar · 6 oct'
    assert 'vencido' in out[1] and 'insuficientes' in out[2] and 'rechazado' in out[3]
    tools = open(os.path.join(ROOT, 'mcp_server', 'tools.py'), encoding='utf-8').read()
    assert "'decision_code': x['memo'].get('decision_code')" in tools and "'expired': x['memo'].get('expired')" in tools
