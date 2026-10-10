"""Overnight 2 (2026-10-10) — arreglos de la revisión de las escenas de la Cabina y del 🩺 Sistema.

1. Saldos grandes del bróker: la cifra NUNCA se recorta con «…» (antes nowrap + ellipsis escondía dígitos de
   «$12,345,678.91»); si no cabe baja de línea tras una coma de miles (<wbr>) y lleva title con el valor entero.
2. 🩺: la pista « → …» del servidor se separa en la primera flecha FUERA de paréntesis — «(Deployments → Restart)»
   ya no se parte a la mitad — y un detalle con viñetas «•» no se parte.
3. Explosivas en una ventana angosta: el detalle 5d·20d·60d y ↗MA20 bajan a una 2.ª línea en vez de esconderse.
4. 🩺 abierto al cambiar ES/EN: se re-pinta en el idioma nuevo.
5. color-mix(): "background:X;background:color-mix(…var()…)" no es respaldo → @supports en el CSS y detección
   (CSS.supports) para los style="" de la Cabina.
"""
import json
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')
COCKPIT_PATH = os.path.join(ROOT, 'engine', 'cockpit.js')
DESKTOP_PATH = os.path.join(ROOT, 'engine', 'desktop.js')
MASCOT_PATH = os.path.join(ROOT, 'engine', 'mascot.js')


def _r(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


SRC = _r(COCKPIT_PATH)
HTML = _r(os.path.join(ROOT, 'app.html'))


def _rule(css, selector):
    m = re.search(re.escape(selector) + r'\{([^}]*)\}', css)
    assert m, 'falta la regla ' + selector
    return m.group(1)


def _supports_blocks(css):
    """Cuerpos de los @supports (…){…} (llaves balanceadas)."""
    out = []
    for m in re.finditer(r'@supports[^{]*\{', css):
        depth, j = 1, m.end()
        while depth:
            depth += {'{': 1, '}': -1}.get(css[j], 0)
            j += 1
        out.append(css[m.end():j - 1])
    return out


# ── 1. dinero completo ──────────────────────────────────────────────────────────────────────────────────
def test_stat_money_is_never_ellipsized():
    b = _rule(SRC, '.bcp-stat b')
    assert 'text-overflow' not in b and 'overflow:hidden' not in b and 'nowrap' not in b
    assert 'overflow-wrap:anywhere' in b
    # las tres cifras del bróker pasan por _moneyHTML (title + <wbr> tras cada coma)
    for f in ('_moneyHTML(acct.equity, LINK_CSS)', '_moneyHTML(acct.cash)', '_moneyHTML(acct.buying_power)'):
        assert f in SRC, f
    assert "'<b title=\"' + t + '\"'" in SRC and "t.replace(/,/g, ',<wbr>')" in SRC


# ── 2. pista del diagnóstico ────────────────────────────────────────────────────────────────────────────
_DIAG_JS = HTML[HTML.index('/* ── Estado del Sistema — diagnóstico en vivo'):HTML.index('window.openDiagnostics = async function')]
_HARNESS = r"""
const vm = require('vm');
const ctx = { window: { LANG: 'es' }, out: null };
ctx.esc = s => String(s == null ? '' : s);
vm.createContext(ctx);
vm.runInContext(%s + '\n;out = (s, l) => _diagTexts(s, l);', ctx);
const cases = %s, r = {};
for (const [k, s] of Object.entries(cases)) r[k] = ctx.out(s, 'bad');
console.log(JSON.stringify(r));
"""
SCHEMA = ('Esquema desactualizado: faltan events.source_id. Se intentó reparar automáticamente y no se pudo — '
          'reinicia el servicio en Railway (Deployments → Restart).')
DB = ('Ontología configurada pero no conecta: could not translate host name "postgres.railway.internal" → El servicio '
      'de base de datos no existe con ese nombre en el proyecto. En Railway: crea el Postgres (+ New → Database) y pon '
      'la variable como REFERENCIA.')
NEO = ('NEO4J configurado pero no conecta: timed out → Tiempo de espera agotado: red o firewall entre la app y la base. '
       '[usuario=neo4j · host=x.databases.neo4j.io · pw=12 car.]')
CASES = {
    'schema': {'configured': True, 'ok': False, 'detail': SCHEMA},
    'db': {'configured': True, 'ok': False, 'detail': DB},
    'neo': {'configured': True, 'ok': False, 'detail': NEO},
    'ai': {'configured': True, 'ok': False, 'detail': 'FAST: m ✗ (400) → Saldo agotado: recarga en la consola del proveedor.'},
    'bullets': {'configured': True, 'ok': False, 'detail': 'Khipu (voz) tiene problemas: • En Railway → Variables falta la clave.'},
}


@pytest.fixture(scope='module')
def diag():
    if not NODE:
        pytest.skip('node no disponible')
    js = _HARNESS % (json.dumps(_DIAG_JS), json.dumps(CASES))
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_diag_hint_split_skips_arrows_inside_parentheses(diag):
    # la flecha de «(Deployments → Restart)» es una ruta de menú, no la pista: el texto queda ENTERO
    assert diag['schema'] == {'detail': SCHEMA, 'fixes': []}
    # la pista del servidor se separa en su flecha; la flecha entre paréntesis de la pista se conserva
    assert diag['db']['detail'] == 'Ontología configurada pero no conecta: could not translate host name "postgres.railway.internal"'
    assert diag['db']['fixes'] == ['El servicio de base de datos no existe con ese nombre en el proyecto. En Railway: crea el '
                                   'Postgres (+ New → Database) y pon la variable como REFERENCIA.']
    assert diag['neo']['detail'] == 'NEO4J configurado pero no conecta: timed out'
    assert diag['neo']['fixes'][0].startswith('Tiempo de espera agotado') and diag['neo']['fixes'][0].endswith('pw=12 car.]')
    assert diag['ai'] == {'detail': 'FAST: m ✗ (400)', 'fixes': ['Saldo agotado: recarga en la consola del proveedor.']}
    # un detalle con viñetas «•» (la voz) no se parte
    assert diag['bullets'] == {'detail': CASES['bullets']['detail'], 'fixes': []}


# ── 3. explosivas: el detalle baja de línea en vez de esconderse ─────────────────────────────────────────
def test_screener_wraps_detail_instead_of_hiding():
    a = SRC.index('.bcp-scr{container-type:inline-size}')
    css = SRC[a:SRC.index('/* progreso por pasos de engine/loading.js', a)]
    assert not re.search(r'\.bcp-scr \.(mono|ma)\{display:none', css)
    assert re.search(r'\.bcp-scr \.mono,\s*\.bcp-scr \.ma\{display:none', css) is None
    assert '.bcp-scr .bcp-row{flex-wrap:wrap' in css
    assert '.bcp-scr .bcp-row::after{content:"";order:2;flex:0 0 100%;height:0}' in css      # salto de línea forzado
    assert re.search(r'\.bcp-scr \.mono\{order:3;flex:1 1 0%!important;', css)
    assert '.bcp-scr .ma{order:4}' in css
    assert '@container (max-width:380px){.bcp-scr .bar{display:none}}' in css


# ── 4. 🩺 abierto al cambiar de idioma ────────────────────────────────────────────────────────────────────
def test_sistema_relabels_on_language_toggle():
    assert ('applyLang = function(){ _applyLang(); try{ applyLangV8(); }catch(e){} try{ _sistemaRelabel(); }catch(e){} };'
            in HTML)
    fn = re.search(r'function _sistemaRelabel\(\)\{.*?\n\}', HTML, re.S).group(0)
    if not NODE:
        pytest.skip('node no disponible')
    js = r"""
const vm = require('vm');
const res = [];
for (const show of [true, false]) {
  const calls = [];
  const ctx = { calls, _sistemaTab: 'gasto', _switchSistemaTab: t => calls.push(t),
                $: id => (id === 'sistema-panel' ? { classList: { contains: c => c === 'show' && show } } : null) };
  vm.createContext(ctx);
  vm.runInContext(%s + '\n_sistemaRelabel();', ctx);
  res.push(calls);
}
console.log(JSON.stringify(res));
""" % json.dumps(fn)
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == [['gasto'], []]        # abierto → re-pinta su pestaña; cerrado → nada


# ── 5. color-mix con respaldo REAL ───────────────────────────────────────────────────────────────────────
def _sistema_css():
    a = HTML.index('/* ----- 🩺 Sistema — Khipus OS')
    return HTML[a:HTML.index('@media(prefers-reduced-motion:reduce){\n  #sistema-panel', a)]


def _scene_css():
    a = SRC.index('/* ══ ESCENAS de la Cabina (2026-10-10)')
    return SRC[a:SRC.index('/* CHAT de Khipu (2026-09-30)', a)]


def test_color_mix_only_behind_supports_or_detection():
    for css in (_scene_css(), _sistema_css()):
        css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)          # los comentarios citan el patrón viejo
        assert ';background:color-mix(' not in css and ';color:color-mix(' not in css
        inside = ''.join(_supports_blocks(css))
        assert css.count('color-mix(') == inside.count('color-mix(') + css.count('@supports (color:color-mix(')
        assert inside.count('color-mix(') >= 3
    # sin color-mix, las bases quedan en superficies del tema
    assert 'background:var(--os-surface-2,#1F2029)' in _rule(_scene_css(), '.bcp-trade.buy')
    assert 'background:var(--os-surface-2,#1F2029)' in _rule(_scene_css(), '.bcp-fact')
    # style="" de la Cabina: la mezcla solo si CSS.supports lo confirma; nunca la doble declaración
    assert "CSS.supports('color', 'color-mix(in srgb, red 50%, blue)')" in SRC
    assert "var LINK_INK = CMIX ? 'color-mix(" in SRC and "var LINK_CSS = 'color:' + LINK_INK;" in SRC
    assert "(CMIX ? 'color-mix(in srgb,' + c + ' ' + (pct || 14) + '%,transparent)' : OS.s2)" in SRC
    js_only = re.sub(r'var css = `.*?`;', '', SRC, flags=re.S)
    js_only = re.sub(r'(?m)^\s*//.*$', '', js_only)                  # sin comentarios
    assert ";background:color-mix(" not in js_only and ";color:color-mix(" not in js_only


# ── navegador: saldos enormes en una ventana angosta y explosivas en un flanco ────────────────────────────
PAGE = r"""<!doctype html><html lang="es"><head><meta charset="utf-8"><style>html,body{margin:0;height:100%;font-family:system-ui}</style>
</head><body><main id="mainmap" style="display:flex"><div>mapa</div></main>
<script>
window.LANG = 'es';
window.NODES = [{ id: 'Nvidia', label: 'Nvidia', mkt: 'NVDA', cat: 'gpu' }];
window.NODE_BY_ID = { Nvidia: window.NODES[0] }; window.LINKS = []; window.SECTORS9 = {}; window.CAT_TO_SECTOR = {};
window.computeNRS = function () { return 40; };
window._tradePinStored = function () { return '1234'; };
window._tradeFetch = function (u, o) { return fetch(u, o); };
window._tradeAccountInfo = function () { return Promise.resolve({ equity: 12345678.91, cash: 4021034.17, buying_power: 8042068.34, paper: true }); };
window._tradeStatusInfo = function () { return Promise.resolve({ pin_set: true, paper: true }); };
window.KhipuChat = { appendUser: function () {}, appendPending: function () { return document.createElement('div'); },
  send: function () { return new Promise(function () {}); }, fillReply: function () {}, fillError: function () {},
  classify: function () { return { kind: 'brain' }; }, ensureStyles: function () {}, clear: function () {},
  noteEntity: function () {}, remember: function () {} };
</script></body></html>"""
API = {
    '/api/trade/positions/detail': [], '/api/trade/history': [],
    '/api/screener/growth': {'ranked': [
        {'id': 'Nvidia', 'label': 'Nvidia', 'score': 12.4, 'r5': 3.1, 'r20': 9.8, 'r60': 21.4, 'pagerank_rank': 3, 'above_ma20': True},
        # sin PageRank (con y sin ↗MA20): antes de forzar el salto, el detalle se metía en la 1.ª línea y aplastaba el nombre
        {'id': 'Micron', 'label': 'Micron Technology', 'score': 7.7, 'r5': -0.4, 'r20': 8.0, 'r60': 18.9, 'pagerank_rank': None, 'above_ma20': True},
        {'id': 'Intel', 'label': 'Intel', 'score': -4.6, 'r5': -2.2, 'r20': -5.1, 'r60': -9.4, 'pagerank_rank': None, 'above_ma20': False}],
        'coverage': {'complete': True, 'warm': 5, 'total': 5}},
}


def _chromium(p):
    for kw in ({}, {'executable_path': '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', 'args': ['--no-sandbox']}):
        try:
            return p.chromium.launch(**kw)
        except Exception:  # noqa: BLE001
            continue
    return None


@pytest.fixture(scope='module')
def browser():
    pw = pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        b = _chromium(p)
        if not b:
            pytest.skip('Chromium no disponible')
        yield b
        b.close()


def _page(browser, w, h, before=''):
    c = browser.new_context(viewport={'width': w, 'height': h})

    def handler(route):
        path = route.request.url[len('http://khipu.test'):].split('?')[0]
        if path in ('', '/'):
            return route.fulfill(status=200, content_type='text/html', body=PAGE)
        if path in API:
            return route.fulfill(status=200, content_type='application/json', body=json.dumps(API[path]))
        return route.fulfill(status=503, content_type='application/json', body='{"error":"sin servidor"}')
    c.route('http://khipu.test/**', handler)
    pg = c.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://khipu.test/')
    if before:
        pg.add_script_tag(content=before)
    for p in (MASCOT_PATH, DESKTOP_PATH, COCKPIT_PATH):
        pg.add_script_tag(content=_r(p))
    pg.evaluate('BixbyCockpit.open()')
    pg.wait_for_timeout(200)
    return c, pg, errs


_MEASURE = """(gw) => { const g = document.querySelector('.kd-win[data-kind="broker"] .bcp-grid3'); if (!g) return null;
  if (gw) g.style.width = gw + 'px';
  return [...g.querySelectorAll('.bcp-stat b')].map(b => ({ t: b.textContent, title: b.title, sw: b.scrollWidth, cw: b.clientWidth,
    h: b.getBoundingClientRect().height, fs: parseFloat(getComputedStyle(b).fontSize), to: getComputedStyle(b).textOverflow,
    col: getComputedStyle(b).color })); }"""


@pytest.mark.parametrize('vw,vh,gw', [(1440, 900, None), (1180, 820, None), (390, 844, None), (1440, 900, 150)])
def test_navegador_saldos_enormes_completos(browser, vw, vh, gw):
    c, pg, errs = _page(browser, vw, vh)
    pg.evaluate("() => BixbyCockpit.stage('broker')")
    pg.wait_for_timeout(500)
    stats = pg.evaluate(_MEASURE, gw)
    assert stats and len(stats) == 3
    want = ['$12,345,678.91', '$4,021,034.17', '$8,042,068.34']
    assert [s['t'] for s in stats] == want and [s['title'] for s in stats] == want
    for s in stats:
        assert s['sw'] <= s['cw'] + 1, s           # nada escondido ni desbordado
        assert s['to'] != 'ellipsis', s
        assert s['fs'] >= 15.5, s                  # sigue legible (mínimo del clamp: 16 px)
    if gw:                                         # columna de 150 px: la cifra baja de línea en vez de cortarse
        assert stats[0]['h'] > stats[0]['fs'] * 1.9, stats[0]
    assert not errs, errs
    c.close()


def test_navegador_link_ink_sin_color_mix(browser):
    # navegador sin color-mix (simulado): el «Valor total» se pinta con el acento, nunca queda sin color ni transparente
    c, pg, errs = _page(browser, 1440, 900, before="CSS.supports = function () { return false; };")
    pg.evaluate("() => BixbyCockpit.stage('broker')")
    pg.wait_for_timeout(500)
    st = pg.evaluate("""() => { const b = document.querySelector('.kd-win[data-kind="broker"] .bcp-stat b');
      return { style: b.getAttribute('style'), col: getComputedStyle(b).color,
               acc: getComputedStyle(b).getPropertyValue('--os-accent').trim() }; }""")
    assert 'color-mix' not in st['style'] and st['style'].startswith('color:var(--os-accent')
    assert not errs, errs
    c.close()


@pytest.mark.parametrize('dark', [False, True])
def test_navegador_explosivas_angosta_muestra_momentum(browser, dark):
    c, pg, errs = _page(browser, 1440, 900)
    pg.evaluate("(d) => document.body.classList.toggle('dark', d)", dark)
    pg.evaluate("() => BixbyCockpit.stage('screener')")
    pg.wait_for_timeout(500)
    res = {}
    for w in (900, 380, 320):
        res[w] = pg.evaluate("""(w) => { const host = document.getElementById('bcp-scr'); host.style.width = w + 'px';
          const row = host.querySelector('.bcp-row'); const r = el => el ? el.getBoundingClientRect() : null;
          const nm = r(row.querySelector('.nm')), mono = r(row.querySelector('.mono')), ma = r(row.querySelector('.ma')),
                bar = r(row.querySelector('.bar')), pv = r(row.querySelector('.pv'));
          // la fila sobresale 8 px a cada lado a propósito (margin:0 -8px: fondo del hover) → tolerancia 9 px
          return { nm, mono, ma, bar, pv, monoTxt: row.querySelector('.mono').textContent,
                   over: Math.max(pv.right, mono.right, ma.right) > host.getBoundingClientRect().right + 9 }; }""", w)
    for w, x in res.items():
        assert x['mono']['height'] > 0 and x['ma']['height'] > 0, (w, x)      # nunca escondidos
        assert x['monoTxt'] == '5d +3.1% · 20d +9.8% · 60d +21.4%'
        assert x['pv']['height'] > 0 and not x['over'], (w, x)
    # ancho: todo en una línea; angosto: momentum y ↗MA20 en una 2.ª línea, alineados bajo el nombre
    assert abs(res[900]['mono']['top'] - res[900]['nm']['top']) < 4 and res[900]['mono']['height'] < 20   # 1 línea
    for w in (380, 320):
        x = res[w]
        assert x['mono']['top'] >= x['nm']['bottom'] - 1, (w, x)
        assert x['ma']['top'] >= x['nm']['bottom'] - 1, (w, x)
        assert abs(x['mono']['left'] + 30 - x['nm']['left']) < 2, (w, x)        # padding-left:30px = bajo el nombre
    assert res[380]['bar']['height'] == 0 or res[380]['bar']['width'] == 0   # la barra (repite la cifra) cede en ≤380
    # TODAS las filas (con o sin PageRank / ↗MA20): el nombre se ve entero y el detalle va DEBAJO de él
    for w in (900, 600, 380, 320):
        rows = pg.evaluate("""(w) => { const host = document.getElementById('bcp-scr'); host.style.width = w + 'px';
          return [...host.querySelectorAll('.bcp-row')].map(row => { const r = s => { const e = row.querySelector(s); return e ? e.getBoundingClientRect() : null; };
            const nm = row.querySelector('.nm');
            return { nm: r('.nm'), mono: r('.mono'), full: nm.scrollWidth <= nm.clientWidth + 1, txt: nm.textContent }; }); }""", w)
        assert len(rows) == 3
        for x in rows:
            assert x['nm']['width'] >= 40 and x['full'], (w, x)
            if w <= 600:
                assert x['mono']['top'] >= x['nm']['bottom'] - 1, (w, x)
            else:
                assert abs(x['mono']['top'] - x['nm']['top']) < 4, (w, x)
    assert not errs, errs
    c.close()


def test_saldos_con_dos_decimales():
    """"$40,210.1" → "$40,210.10": las tarjetas de saldo siempre muestran centavos."""
    src = _r(COCKPIT_PATH)
    i = src.index('function _moneyHTML(v, style) {')
    assert "minimumFractionDigits: 2, maximumFractionDigits: 2" in src[i:i + 400]
