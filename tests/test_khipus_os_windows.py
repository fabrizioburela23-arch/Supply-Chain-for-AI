"""Khipus OS — ventanas nativas (engine/oswindows.js, 2026-10-06).

«<Empresa> en una mirada», «Convicción de tus agentes», «Cadena de suministro de X» y
«Tus agentes». Tres niveles de prueba:
  1. estáticas: contrato (registerKind, 4 tipos, multi), solo tokens --os-*, sin ids
     globales, sin caminos de órdenes, bilingüe, explicadores "?";
  2. node vm: funciones puras (formato es/en, regla de color de las barras, filas
     visibles, cadena solo de FLUJO, pros/contras estructurales);
  3. navegador (Playwright, si hay Chromium): página mínima con la API simulada —
     cuenta animada, vacíos honestos, multi-instancia, idioma, preferencias, @mención.
"""
import json
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, 'engine', 'oswindows.js')
SRC = open(PATH, encoding='utf-8').read()
NODE = shutil.which('node')
CSS = re.search(r"var CSS = ''(.*?);\n  function ensureCss", SRC, re.S).group(1)


# ─────────────────────────────── estáticas ───────────────────────────────
def test_contrato_registro_y_tipos():
    assert "c.registerKind(k, spec(k))" in SRC                      # docs/KHIPUS_OS.md §3.1
    for k in ('glance:', 'conviction:', 'supplychain:', 'agents:'):
        assert k in SRC
    assert re.search(r"glance: \{[^}]*multi: true", SRC) and re.search(r"supplychain: \{[^}]*multi: true", SRC)
    assert re.search(r"conviction: \{[^}]*multi: false", SRC) and re.search(r"agents: \{[^}]*multi: false", SRC)
    # se abre por la única puerta de la Cabina
    assert "c.stage(kind, arg)" in SRC and "c.open({ kind: kind, arg: arg })" in SRC
    # reintento: cockpit.js puede cargar después
    assert "setInterval(function () { if (ensureRegistered() || ++tries > 40) clearInterval(iv); }, 250)" in SRC


def test_es5_sin_sintaxis_moderna():
    code = re.sub(r"'(?:[^'\\\n]|\\.)*'", "''", SRC)                 # sin cadenas
    assert '=>' not in code and '`' not in code
    assert not re.search(r'\b(let|const|class)\s', code)


def test_solo_tokens_os_en_los_estilos():
    vars_ = set(re.findall(r'var\((--[\w-]+)', CSS))
    assert vars_ and all(v.startswith('--os-') or v in ('--w',) for v in vars_), vars_
    assert not re.search(r'#[0-9a-fA-F]{3,8}\b', CSS), 'color fijo en el CSS'
    assert 'rgba(' not in CSS and 'rgb(' not in CSS
    assert 'font-variant-numeric:tabular-nums' in CSS
    assert 'prefers-reduced-motion' in CSS


def test_multi_instancia_sin_ids_globales():
    assert not re.search(r'(?<![\w-])id="', SRC)                   # todo se pinta con clases + querySelector
    ids = re.findall(r"getElementById\('([^']+)'\)", SRC)
    assert set(ids) <= {'osw-css', 'bcp-input'}, ids
    assert 'document.querySelector(' not in SRC


def test_dinero_sin_caminos_nuevos():
    for bad in ('/api/trade', '_tradeFetch', '_executeTradeOrder', '/approve', "method: 'POST'", 'X-Trade-Pin', 'confirmOrder'):
        assert bad not in SRC, bad
    # «Revisar propuesta» solo abre el comité (que exige aprobación humana con PIN)
    assert "if (act === 'committee') { if (id) openCommittee(id); return; }" in SRC
    assert "window.KhipuCommittee.open(id)" in SRC


def test_bilingue_sin_llamadas_de_un_solo_idioma():
    assert not re.search(r"\bL\('(?:[^'\\]|\\.)*'\)", SRC), 'L() con un solo idioma'
    for es, en in (('en una mirada', 'at a glance'), ('Convicción de tus agentes', "Your agents\\' conviction"),
                   ('Cadena de suministro de ', ' supply chain'), ('Tus agentes', 'Your agents'),
                   ('Revisar propuesta', 'Review proposal'), ('Pedir opinión al comité', 'Ask the committee'),
                   ('Ver evidencia', 'See evidence'), ('Sin veredicto aún', 'No verdict yet'),
                   ('sin comité aún', 'no committee yet'), ('Datos insuficientes', 'Insufficient data')):
        assert es in SRC and en in SRC, (es, en)


def test_explicadores_y_vacios_honestos():
    for k in ('os_conviction', 'os_track'):
        assert re.search(k + r": \{\s*es: \{ t: '[^']+',", SRC) and re.search(k + r": \{.*?en: \{ t: '", SRC, re.S), k
        assert "qChip('" + k + "')" in SRC, k
    assert "window.explainRegister(k, EXPL[k])" in SRC
    assert "20 días hábiles" in SRC and "20 business days" in SRC     # historial: honesto, no inventado
    assert "Sin historial suficiente todavía" in SRC
    assert "no es una opinión de tus agentes" in SRC                  # pros/contras estructurales rotulados
    assert "No es una recomendación personal." in SRC


# ─────────────────────────────── node vm ───────────────────────────────
VM_PRELUDE = r"""
const fs = require('fs'), vm = require('vm');
const reg = {}, ex = {};
const win = { LANG: 'es', addEventListener(){}, explainRegister(k, e){ ex[k] = e; } };
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
def test_formato_es_en_y_signos():
    o = _node(r"""process.stdout.write(JSON.stringify({
      a: H.fmtConv(50.6, 'es'), b: H.fmtConv(-1.06, 'es'), c: H.fmtConv(-0.04, 'es'), d: H.fmtConv(0, 'en'),
      e: H.fmtConv(42, 'en'), f: H.fmtNum(50218.49, 2, 'es'), g: H.fmtNum(50218.49, 2, 'en'), h: H.fmtNum(1234567, 0, 'es'),
      i: H.fmtPct(61.1, 'es', 0, false), j: H.fmtPct(1.234, 'en', 2), k: H.fmtMoney(182.4, 'USD', 'es'),
      l: H.fmtMoney(185000, 'KRW', 'en'), m: H.fmtMoney(0, 'USD', 'es'), n: H.fmtNum(null, 1, 'es'), o: H.fmtNum('x', 1, 'es'),
      p: H.fmtNum(-21.5, 1, 'es', {sign: true}) })); process.exit(0);""")
    M = '−'
    assert o['a'] == '+50,6' and o['b'] == M + '1,1' and o['c'] == '0,0' and o['d'] == '0.0'
    assert o['e'] == '+42.0' and o['f'] == '50.218,49' and o['g'] == '50,218.49' and o['h'] == '1.234.567'
    assert o['i'] == '61 %' and o['j'] == '+1.23%' and o['k'] == '$182,40' and o['l'] == '₩185,000'
    assert o['m'] == '—' and o['n'] == '—' and o['o'] == '—' and o['p'] == M + '21,5'


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_regla_de_color_y_geometria_de_barras():
    o = _node(r"""const vs = [50.6, 5, 4.96, 4.9, 0, -1.1, -4.99, -5, -9.7, -14.9, -15, -21.5, NaN];
      process.stdout.write(JSON.stringify({ t: vs.map(H.barTone), g: [H.barGeom(50.6), H.barGeom(-21.5), H.barGeom(180), H.barGeom(NaN)] })); process.exit(0);""")
    # |v|<5 gris · a favor azul · ≤−15 naranja · otro en contra gris (con el valor redondeado a 1 decimal, como se muestra)
    assert o['t'] == ['pos', 'pos', 'pos', 'mute', 'mute', 'mute', 'mute', 'mute', 'mute', 'mute', 'neg', 'neg', 'mute']
    assert o['g'][0] == {'side': 'pos', 'pct': 25.3} and o['g'][1] == {'side': 'neg', 'pct': 10.75}
    assert o['g'][2] == {'side': 'pos', 'pct': 50} and o['g'][3] == {'side': 'pos', 'pct': 0}


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_filas_visibles_de_la_pizarra():
    o = _node(r"""process.stdout.write(JSON.stringify({
      small: H.visibleRows(12, 1, false), all: H.visibleRows(30, 20, true).length,
      mid: H.visibleRows(30, 15, false), top: H.visibleRows(30, 2, false), none: H.visibleRows(20, -1, false) })); process.exit(0);""")
    assert o['small'] == list(range(12)) and o['all'] == 30
    assert o['mid'] == [0, 1, 2, 3, 4, 5, {'gap': 7}, 13, 14, 15, 16, 17, {'gap': 9}, 27, 28, 29]
    assert o['top'] == [0, 1, 2, 3, 4, 5, {'gap': 21}, 27, 28, 29]
    assert o['none'] == [0, 1, 2, 3, 4, 5, {'gap': 11}, 17, 18, 19]


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_cadena_solo_flujo_sin_duplicados_y_canonica():
    o = _node(r"""
      const links = [
        {source: 'TSMC', target: 'Nvidia', w: 6, type: 'fab', conf: 1, verified: true},
        {source: {id: 'SKHynix'}, target: {id: 'Nvidia'}, w: 6, type: 'supply'},
        {source: 'SKHynix', target: 'Nvidia', w: 2, type: 'supply'},              // par repetido: cuenta una vez (máx)
        {source: 'Hynix_old', target: 'Nvidia', w: 3, type: 'supply'},            // alias → canónico SKHynix
        {source: 'Anthropic', target: 'Nvidia', w: 9, type: 'partner'},           // NO es flujo
        {source: 'Fund', target: 'Nvidia', w: 9, type: 'invest'},                 // NO es flujo
        {source: 'Shady', target: 'Nvidia', w: 5, type: 'supply', conf: 0.3, verified: false},
        {source: 'Nvidia', target: 'Dell', w: 6, type: 'supply'},
        {source: 'Nvidia', target: 'CoreWeave', w: 6, type: 'cloud'},
        {source: 'Nvidia', target: 'Nvidia', w: 6, type: 'owns'} ];
      const canon = (x) => x === 'Hynix_old' ? 'SKHynix' : x;
      const c = H.chainOf('Nvidia', links, canon);
      process.stdout.write(JSON.stringify(c)); process.exit(0);""")
    sup = {x['id']: x for x in o['suppliers']}
    assert set(sup) == {'TSMC', 'SKHynix', 'Shady'}
    assert sup['SKHynix']['w'] == 6 and sup['SKHynix']['n'] == 3
    assert sup['Shady']['w'] == pytest.approx(1.5) and sup['Shady']['verified'] is False   # peso × conf, marcado sin verificar
    assert [x['id'] for x in o['suppliers']][:2] == ['SKHynix', 'TSMC']                     # por peso, luego id
    assert [x['id'] for x in o['customers']] == ['CoreWeave', 'Dell']


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_pros_contras_estructurales_y_pizarra():
    o = _node(r"""
      const t = { supplier_concentration: { level: 'baja', n_suppliers: 44, top: [{id: 'TSMC', label: 'TSMC', share_pct: 6.4}] },
                  upstream_risk_sources: [{id: 'TSMC', label: 'TSMC', exposure_pct: 61.1, direct: true},
                                          {id: 'ARM', label: 'ARM', exposure_pct: 12.0, direct: true},
                                          {id: 'PDF', label: 'PDF Solutions', exposure_pct: 6.2, direct: false}] };
      const t2 = { supplier_concentration: { level: 'alta', n_suppliers: 1, top: [{id: 'TSMC', label: 'TSMC', share_pct: 100}] },
                   upstream_risk_sources: [{id: 'TSMC', label: 'TSMC', exposure_pct: 80, direct: true}] };
      const items = [{entity_id: 'TSMC'}, {entity_id: 'nvidia'}];
      process.stdout.write(JSON.stringify({ es: H.structPC(t, 'es'), en: H.structPC(t, 'en'), hi: H.structPC(t2, 'es'),
        b1: H.boardItem(items, 'Nvidia'), b2: H.boardItem(items, 'AMD'), cl: H.clean('Demanda alta. [C1] Riesgo [E2, R1] bajo.'),
        a1: H.argId('Nvidia'), a2: H.argId({id: 'TSMC'}), a3: H.argId({a: 'AMD'}), a4: H.argId(null), a5: H.argId({id: {x: 1}}) }));
      process.exit(0);""")
    assert [c['t'] for c in o['es']['cons']] == ['Si TSMC falla, le llega el 61 % del golpe.', 'Si ARM falla, le llega el 12 % del golpe.']
    assert o['es']['pros'][0]['t'] == '44 proveedores y ninguno pesa más del 7 % de su red de proveedores.'
    assert o['en']['cons'][0]['t'] == 'If TSMC fails, 61% of the shock reaches it.'
    assert o['hi']['cons'][0]['t'] == 'Depende en 100 % de TSMC entre sus proveedores.' and len(o['hi']['cons']) == 1
    assert o['hi']['pros'] == []
    assert o['b1'] == {'entity_id': 'nvidia'} and o['b2'] is None
    assert o['cl'] == 'Demanda alta. Riesgo bajo.'
    assert (o['a1'], o['a2'], o['a3'], o['a4'], o['a5']) == ('Nvidia', 'TSMC', 'AMD', None, None)


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_registro_temprano_y_explicadores():
    o = _node(r"""
      // la Cabina ya existe: se registra al cargar
      const reg2 = {}; const ctx2 = Object.assign({}, ctx);
      const w2 = { LANG: 'en', addEventListener(){}, BixbyCockpit: { registerKind(k, s){ reg2[k] = s; } } };
      w2.window = w2; ctx2.window = w2; vm.createContext(ctx2);
      vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), ctx2);
      const out = {};
      Object.keys(reg2).forEach(k => { const s = reg2[k]; out[k] = { icon: !!s.icon, es: s.es, en: s.en, multi: s.multi,
        render: typeof s.render, title: s.title({id: 'Nvidia'}) }; });
      process.stdout.write(JSON.stringify({ reg: out, ex: Object.keys(ex).sort(), exl: Object.keys(ex.os_conviction) })); process.exit(0);""")
    r = o['reg']
    assert set(r) == {'glance', 'conviction', 'supplychain', 'agents'}
    assert r['glance']['multi'] is True and r['supplychain']['multi'] is True and r['agents']['multi'] is False
    assert all(v['render'] == 'function' and v['icon'] and v['es'] and v['en'] for v in r.values())
    assert r['glance']['title'] == 'Nvidia at a glance' and r['supplychain']['title'] == 'Nvidia supply chain'
    assert o['ex'] == ['os_conviction', 'os_track'] and o['exl'] == ['es', 'en']


# ─────────────────────────── navegador (Playwright) ───────────────────────────
def _chromium(p):
    for kw in ({}, {'executable_path': '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'}):
        try:
            return p.chromium.launch(**kw)
        except Exception:  # noqa: BLE001
            continue
    return None


PAGE = r"""<!doctype html><html lang="es"><head><meta charset="utf-8"><style>
body.dark #h{--os-bg:#0E0F14;--os-surface:#17181F;--os-surface-2:#1F2029;--os-surface-3:#2A2B36;--os-ink:#F2F2F5;--os-ink-2:#A6A8B5;--os-ink-3:#6E7080;
 --os-line:rgba(255,255,255,.07);--os-shadow:0 1px 2px rgba(0,0,0,.4);--os-accent:#4C8DF6;--os-pos:#4C8DF6;--os-neg:#F07A52;--os-mute:#3A3C4A;
 --os-good:#2fbf5b;--os-bad:#f06565;--os-btn:#F2F2F5;--os-btn-ink:#111216;--os-r:18px;--os-r-sm:12px;--os-font:system-ui}
.kd-body{width:560px;height:560px;overflow:auto;padding:16px}
</style></head><body class="dark"><div id="h"><div class="kd-body" id="b1"></div><div class="kd-body" id="b2"></div><div class="kd-body" id="b3"></div></div>
<input id="bcp-input">
<script>
window.LANG='es';
window.calls={committee:[],research:[],stage:[],open:[],prefs:[],reg:{}};
var N=[{id:'Nvidia',label:'Nvidia',mkt:'NVDA'},{id:'TSMC',label:'TSMC',mkt:'TSM'},{id:'SKHynix',label:'SK Hynix',mkt:'000660.KS'},
 {id:'Dell',label:'Dell Technologies',mkt:'DELL'},{id:'CoreWeave',label:'CoreWeave',mkt:'CRWV'},{id:'Anthropic',label:'Anthropic',mkt:null}];
window.NODES=N; window.NODE_BY_ID={}; N.forEach(function(n){window.NODE_BY_ID[n.id]=n;});
window._canonId=function(i){var n=window.NODE_BY_ID[i];return (n&&n.id)||i;};
window.LINKS=[{source:N[1],target:N[0],w:6,type:'fab',conf:1,verified:true},{source:N[2],target:N[0],w:6,type:'supply',conf:1,verified:true},
 {source:N[5],target:N[0],w:9,type:'partner'},{source:N[0],target:N[3],w:6,type:'supply'},{source:N[0],target:N[4],w:5,type:'cloud'}];
window.MKT={quotes:{NVDA:{close:182.4,live:182.4,prev:180.18,pct:1.23,src:'finnhub',as_of:new Date(Date.now()-60000).toISOString(),currency:'USD'}}};
window.quotePx=function(q){return q?(typeof q.live==='number'?q.live:q.close):0;};
window.KhipuCommittee={open:function(id){calls.committee.push(id);}};
window.KhipuResearch={open:function(id){calls.research.push(id);}};
var PREF={mode:'simple',agents:{khipu:{on:true,auto:true},analista:{on:true,auto:true},radar:{on:true,auto:false},cadena:{on:true,auto:true},tecnico:{on:true,auto:false},comite:{on:true,auto:true}}};
window.KhipuAgentPrefs={get:function(){return JSON.parse(JSON.stringify(PREF));},set:function(p){calls.prefs.push(p);
  if(p.mode)PREF.mode=p.mode; if(p.agents)Object.keys(p.agents).forEach(function(k){Object.assign(PREF.agents[k],p.agents[k]);});
  window.dispatchEvent(new CustomEvent('khipu:agentprefs'));return PREF;}};
window.addEventListener('error',function(e){(window.errs=window.errs||[]).push(String(e.message));});
</script></body></html>"""

MEMO = {'entity_id': 'Nvidia', 'latest': {
    'memo_id': 'm1', 'entity_id': 'Nvidia', 'status': 'proposed', 'decision': 'BUY', 'overall_conviction': 42.0,
    'created_at': '2026-10-06T10:00:00+00:00', 'expires_at': '2026-10-09T10:00:00+00:00', 'expired': False,
    'memo': {'decision_code': None, 'thesis': [{'horizon': 'LONG_TERM', 'thesis_es': 'Demanda asegurada por pedidos. [C1]', 'thesis_en': 'Demand secured by orders. [C1]'}],
             'key_risks': [{'risk_es': 'Depende de TSMC.', 'risk_en': 'Relies on TSMC.'}]}}}
BOARD = {'generated_at': '2026-10-06T10:00:00+00:00', 'items': [
    {'entity_id': 'Tesla', 'label': 'Tesla', 'overall_conviction': -21.5, 'by_horizon': {'SHORT_TERM': -30.2}, 'agents': ['technical'], 'n_claims': 3},
    {'entity_id': 'TSMC', 'label': 'TSMC', 'overall_conviction': 50.6, 'by_horizon': {'LONG_TERM': 60}, 'agents': ['fundamental'], 'n_claims': 5},
    {'entity_id': 'Alphabet', 'label': 'Alphabet', 'overall_conviction': -9.7, 'by_horizon': {}, 'agents': ['news'], 'n_claims': 2},
    {'entity_id': 'Nvidia', 'label': 'Nvidia', 'overall_conviction': 42.0, 'by_horizon': {'MEDIUM_TERM': 48.3}, 'agents': ['fundamental', 'supply_chain'], 'n_claims': 9}]}
TENSOR = {'id': 'Nvidia', 'label': 'Nvidia', 'supplier_concentration': {'level': 'media', 'n_suppliers': 2, 'top': [{'id': 'TSMC', 'label': 'TSMC', 'share_pct': 50}]},
          'upstream_risk_sources': [{'id': 'TSMC', 'label': 'TSMC', 'exposure_pct': 61.1, 'direct': True}], 'caps_as_of': None}


def _page(b, state):
    """state: dict path→(status, json). Las rutas sin entrada devuelven 503 (sin base de datos)."""
    pg = b.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))

    def handler(route):
        url = route.request.url
        path = url.split('khipu.test', 1)[1]
        if path in ('/', '/index.html'):
            return route.fulfill(status=200, content_type='text/html', body=PAGE)
        for k, (st, body) in state.items():
            if path.startswith(k):
                return route.fulfill(status=st, content_type='application/json', body=json.dumps(body))
        return route.fulfill(status=503, content_type='application/json', body=json.dumps({'error': 'comité no disponible', 'error_en': 'committee not available'}))
    pg.route('http://khipu.test/**', handler)
    pg.goto('http://khipu.test/')
    pg.add_script_tag(content=SRC)
    return pg, errs


@pytest.fixture(scope='module')
def browser():
    pw = pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        b = _chromium(p)
        if not b:
            pytest.skip('Chromium no disponible')
        yield b
        b.close()


def test_navegador_glance_con_memo_cuenta_y_propuesta(browser):
    pg, errs = _page(browser, {'/api/committee/entity/': (200, MEMO), '/api/committee/board': (200, BOARD), '/api/tensor/node/': (200, TENSOR)})
    pg.evaluate("KhipuOSWin.render('glance', document.getElementById('b1'), {id:'Nvidia'})")
    pg.wait_for_function("() => { const n = document.querySelector('#b1 [data-r=num]'); return n && n.textContent === '+42'; }", timeout=5000)
    t = pg.inner_text('#b1')
    assert 'Nvidia en una mirada' in t and 'Comité: comprar' in t and 'propuesta · espera tu revisión' in t
    assert 'Demanda asegurada por pedidos.' in t and '[C1]' not in t and 'Depende de TSMC.' in t
    assert 'NVDA' in t and '$182,40' in t                               # precio en vivo con fuente arriba
    pg.click('#b1 [data-act=committee]')
    assert pg.inner_text('#b1 [data-act=committee]') == 'Revisar propuesta'
    pg.click('#b1 [data-act=research]')
    assert pg.evaluate('calls.committee') == ['Nvidia'] and pg.evaluate('calls.research') == ['Nvidia']
    assert not errs


def test_navegador_glance_sin_base_precio_y_estructura(browser):
    pg, errs = _page(browser, {'/api/tensor/node/': (200, TENSOR)})
    pg.evaluate("KhipuOSWin.render('glance', document.getElementById('b1'), {id:'Nvidia'})")
    pg.wait_for_function("() => document.querySelector('#b1 .osw-pc')", timeout=5000)
    t = pg.inner_text('#b1')
    assert '$182,40' in t and 'Sin veredicto aún' in t and 'Pedir opinión al comité' in t
    assert 'no es una opinión de tus agentes' in t and 'Depende en 50' in t and 'de TSMC entre sus proveedores' in t
    assert 'no disponibles en este servidor' in t
    # empresa privada: sin precio inventado
    pg.evaluate("KhipuOSWin.render('glance', document.getElementById('b2'), {id:'Anthropic'})")
    pg.wait_for_function("() => /No cotiza en bolsa/.test(document.getElementById('b2').innerText)", timeout=5000)
    assert '$' not in pg.inner_text('#b2 [data-r=main]')
    # multi-instancia: dos ventanas independientes, sin ids nuevos en el documento
    assert 'Nvidia en una mirada' in pg.inner_text('#b1') and 'Anthropic en una mirada' in pg.inner_text('#b2')
    assert pg.evaluate("document.querySelectorAll('#h [id]').length") == 3
    assert not errs


def test_navegador_conviccion_orden_colores_idioma_y_vacio(browser):
    pg, errs = _page(browser, {'/api/committee/board': (200, BOARD)})
    pg.evaluate("KhipuOSWin.render('conviction', document.getElementById('b1'), {id:'Nvidia'})")
    pg.wait_for_selector('#b1 .osw-cv-row')
    rows = pg.eval_on_selector_all('#b1 .osw-cv-row', "els => els.map(e => [e.querySelector('.osw-cv-name').textContent, e.querySelector('.osw-cv-val').textContent, e.querySelector('.osw-cv-bar').className, e.classList.contains('hi')])")
    assert [r[0] for r in rows] == ['TSMC', 'Nvidia', 'Alphabet', 'Tesla']
    assert [r[1] for r in rows] == ['+50,6', '+42,0', '−19,7'.replace('19,7', '9,7'), '−21,5']
    assert 't-pos' in rows[0][2] and 't-mute' in rows[2][2] and 't-neg' in rows[3][2] and 'neg' in rows[3][2].split()
    assert [r[3] for r in rows] == [False, True, False, False]
    # cambio de idioma: <html lang> (lo pone applyLang) → se repinta en inglés
    pg.evaluate("window.LANG='en'; document.documentElement.lang='en'")
    pg.wait_for_function("() => /Your agents' conviction/.test(document.getElementById('b1').innerText)", timeout=3000)
    assert '+50.6' in pg.inner_text('#b1') and 'for +100' in pg.inner_text('#b1')
    pg.evaluate("window.LANG='es'; document.documentElement.lang='es'")
    # clic en una fila → «en una mirada» de esa empresa por la puerta de la Cabina
    pg.evaluate("window.BixbyCockpit={registerKind:function(k,s){calls.reg[k]=s.multi;},isOpen:function(){return true;},stage:function(k,a){calls.stage.push([k,a]);},open:function(o){calls.open.push(o);}}")
    pg.click('#b1 .osw-cv-row >> nth=0')
    assert pg.evaluate('calls.stage') == [['glance', {'id': 'TSMC'}]]
    assert pg.evaluate('calls.reg') == {'glance': True, 'conviction': False, 'supplychain': True, 'agents': False}
    # sin base de datos: vacío honesto + «Investigar»
    pg2, errs2 = _page(browser, {})
    pg2.evaluate("KhipuOSWin.render('conviction', document.getElementById('b1'), {id:'Nvidia'})")
    pg2.wait_for_selector('#b1 .osw-empty')
    t = pg2.inner_text('#b1')
    assert 'no tiene conectada la base de investigación' in t and 'Investigar Nvidia' in t
    pg2.click('#b1 [data-act=research]')
    assert pg2.evaluate('calls.research') == ['Nvidia']
    assert not errs and not errs2


def test_navegador_cadena_flujo_y_riesgo(browser):
    pg, errs = _page(browser, {'/api/tensor/node/': (200, TENSOR)})
    pg.evaluate("KhipuOSWin.render('supplychain', document.getElementById('b1'), {id:'Nvidia'})")
    t = pg.inner_text('#b1')                                            # instantáneo desde LINKS
    assert 'Cadena de suministro de Nvidia' in t and 'TSMC' in t and 'SK Hynix' in t and 'Dell Technologies' in t and 'CoreWeave' in t
    assert 'Anthropic' not in t                                          # 'partner' no es flujo
    pg.wait_for_selector('#b1 .osw-sc-pill.risk')
    assert pg.inner_text('#b1 .osw-sc-pill.risk') == 'TSMC'
    assert 'riesgo: 61' in pg.get_attribute('#b1 .osw-sc-pill.risk', 'title')
    assert 'concentración de proveedores: media' in pg.inner_text('#b1')
    pg.evaluate("window.BixbyCockpit={registerKind:function(){},isOpen:function(){return false;},stage:function(k,a){calls.stage.push([k,a]);},open:function(o){calls.open.push(o);}}")
    pg.click("#b1 .osw-sc-pill:has-text('Dell Technologies')")
    assert pg.evaluate('calls.open') == [{'kind': 'glance', 'arg': {'id': 'Dell'}}]   # Cabina cerrada → la abre en esa ventana
    assert not errs


def test_navegador_agentes_respaldo_preferencias_y_mencion(browser):
    pg, errs = _page(browser, {})                                        # /api/agents/profiles → 503: respaldo estático
    pg.evaluate("KhipuOSWin.render('agents', document.getElementById('b1'))")
    pg.wait_for_function("() => /el servidor no respondió/.test(document.getElementById('b1').innerText)", timeout=5000)
    assert pg.eval_on_selector_all('#b1 .osw-ag', 'e => e.length') == 6
    t = pg.inner_text('#b1')
    for k in ('Khipu', 'Analista', 'Radar', 'Cadena', 'Técnico', 'Comité', 'Datos que usa'.upper(), 'Presentaciones a la SEC'):
        assert k in t, k
    sw = "#b1 [data-agent=radar][data-pref=on]"
    assert pg.get_attribute(sw, 'aria-checked') == 'true'
    pg.click(sw)
    assert pg.evaluate('calls.prefs') == [{'agents': {'radar': {'on': False}}}]
    pg.wait_for_function("() => document.querySelector('#b1 [data-agent=radar][data-pref=on]').getAttribute('aria-checked') === 'false'")
    pg.click("#b1 [data-act=mode][data-mode=pro]")
    assert pg.evaluate('calls.prefs[1]') == {'mode': 'pro'}
    pg.click("#b1 [data-act=ask][data-agent=analista]")
    assert pg.input_value('#bcp-input') == '@fundamental '
    assert pg.evaluate('document.activeElement.id') == 'bcp-input'
    # con historial real del servidor
    prof = {'db': True, 'as_of': '2026-10-06T10:00:00+00:00', 'agents': [
        {'id': 'analista', 'track': {'n_scored': 12, 'hits': 8, 'hit_rate': 0.6667, 'sufficient': True}, 'stats_30d': {'runs': 18, 'claims': 61, 'cost_usd': 0.84}},
        {'id': 'radar', 'track': {'n_scored': 3, 'hits': 2, 'hit_rate': 0.67, 'sufficient': False}}]}
    pg2, errs2 = _page(browser, {'/api/agents/profiles': (200, prof)})
    pg2.evaluate("KhipuOSWin.render('agents', document.getElementById('b1'))")
    pg2.wait_for_function("() => /67\\s% de aciertos/.test(document.getElementById('b1').innerText)", timeout=5000)
    t2 = pg2.inner_text('#b1 [data-agent=radar]')
    assert 'Sin historial suficiente todavía' in t2 and '(3 de 5 calificaciones)' in t2   # 67 % con 3 casos NO se muestra
    assert 'US$0,84' in pg2.inner_text('#b1 [data-agent=analista]')
    assert not errs and not errs2


def test_navegador_glance_sin_quorum_y_memo_vencido(browser):
    # sin quórum (C7): el comité NO decidió → «Datos insuficientes», número atenuado, nunca «Comité: comprar»
    insuf = json.loads(json.dumps(MEMO))
    insuf['latest'].update(decision='HOLD', status='proposed')
    insuf['latest']['memo']['decision_code'] = 'INSUFFICIENT_DATA'
    pg, errs = _page(browser, {'/api/committee/entity/': (200, insuf), '/api/committee/board': (200, BOARD), '/api/tensor/node/': (200, TENSOR)})
    pg.evaluate("KhipuOSWin.render('glance', document.getElementById('b1'), {id:'Nvidia'})")
    pg.wait_for_selector('#b1 .osw-big.mut')
    t = pg.inner_text('#b1')
    assert 'Datos insuficientes' in t and 'faltan analistas para decidir' in t and 'Comité: ' not in t
    # memo VENCIDO (TTL): el número grande vuelve a ser el precio; la convicción de la pizarra se rotula
    old = json.loads(json.dumps(MEMO))
    old['latest']['expired'] = True
    pg2, errs2 = _page(browser, {'/api/committee/entity/': (200, old), '/api/committee/board': (200, BOARD), '/api/tensor/node/': (200, TENSOR)})
    pg2.evaluate("KhipuOSWin.render('glance', document.getElementById('b1'), {id:'Nvidia'})")
    pg2.wait_for_function("() => /sin comité vigente/.test(document.getElementById('b1').innerText)", timeout=5000)
    t2 = pg2.inner_text('#b1')
    assert '$182,40' in t2 and 'Sin veredicto vigente' in t2 and '+42,0' in t2 and '(vencido)' in t2
    assert 'Revisar propuesta' not in t2 and 'Pedir opinión al comité' in t2       # un memo vencido no se aprueba
    assert not errs and not errs2
