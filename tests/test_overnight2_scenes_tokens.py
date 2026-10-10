"""Overnight 2 (2026-10-10) — las escenas que pinta la propia Cabina entran a Khipus OS (engine/cockpit.js).

Antes, bróker, scalping, explosivas, investigación profunda, simulación por agentes, comparar, caída simulada,
selector de empresa y "no encontré" usaban colores neón FIJOS (#00E0FF, #E8EDFB, rgba(11,18,34,…)) y su ventana
llevaba .kd-legacy-dark (una "isla oscura" dentro del tema claro). Ahora:
  · LEGACY_DARK queda vacía (el mecanismo se conserva como red de seguridad);
  · el CSS de las escenas y sus style="" usan SOLO tokens --os-* con respaldo oscuro dentro de var();
  · las insignias 🧪 SIMULADO / 🔴 DINERO REAL conservan sus palabras y contraste (rojo sólido + blanco = 5.6:1);
  · los flujos de dinero (confirmación pop-up/en línea, PIN con _tradeFetch, scalping 1-clic solo en papel) intactos;
  · donde habla un agente de Khipu va su MASCOTA (investigación por secciones, "Khipu:" del informe y consejos, demo).
Dos niveles: estáticas (siempre) y navegador (Playwright + Chromium, si hay): TODA escena BUILTIN se pinta sin
errores, sin .kd-legacy-dark y con tinta oscura en el tema claro.
"""
import json
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COCKPIT_PATH = os.path.join(ROOT, 'engine', 'cockpit.js')
DESKTOP_PATH = os.path.join(ROOT, 'engine', 'desktop.js')
MASCOT_PATH = os.path.join(ROOT, 'engine', 'mascot.js')


def _r(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


SRC = _r(COCKPIT_PATH)

# la paleta neón vieja de las escenas (como texto, fondo, borde o respaldo): no debe volver
LEGACY = ['#00E0FF', '#E8EDFB', 'rgba(11,18,34', '#7C87A3', '#9BA6C4', '#5b6580', '#5E6884', '#C3CBE0', '#D5DCF0',
          '#C6CEE6', '#8E9AB8', '#AEB8D4', '#C7D0EA', '#FF8FA3', '#FFD27A', '#FFE7B0', '#C9D2EA', '#8b95b0', '#8791AC',
          '#8E5AFF', '#FF2D46', '#FFB300', '#34d399', '#f87171', '#fbbf24', '#f59e0b', '#7AA2FF', '#7ef0ff', '#0b6fa8',
          'rgba(122,158,255', 'rgba(0,224,255', 'rgba(12,18,32', 'rgba(8,14,26', 'rgba(4,6,11', 'rgba(6,11,22',
          'rgba(255,77,106', 'rgba(43,227,139', 'rgba(255,179,0', 'rgba(255,45,70', 'rgba(248,113,113', 'rgba(52,211,153',
          'JetBrains Mono']

# funciones que pintan las escenas antes marcadas LEGACY_DARK (+ sus ayudantes)
SCENE_FUNCS = ['backBar', 'stagePick', 'stageNotFound', 'buildFundTable', 'stageCompareFund', 'stageCompare', 'stageSim',
               'stageScreener', 'badgeHTML', '_khipuSays', 'renderPortfolioReport', '_fetchPortfolioComment', '_scalpDrawSpark',
               '_scalpPoll', '_scalpOrder', '_scalpLoadPos', '_scalpClose', 'stageScalp', '_fetchAdvice', '_renderAdvice',
               'stageBroker', 'renderTradeConfirm', 'confirmPendingOrder', 'loadBroker', 'stageDeep', 'agentTypeColor',
               'simBox', 'essentialsHTML', 'sidesHTML', 'quotesHTML', 'timelineHTML', 'watchHTML', 'renderAgentSim',
               'stageAgentSim', 'renderResearch', 'stageResearch', '_demoRenderBar']


def _func(src, name):
    """Fuente de `function name(…) {…}` con llaves balanceadas (salta cadenas y comentarios)."""
    m = re.search(r'(?:async\s+)?function ' + re.escape(name) + r'\s*\(', src)
    assert m, name
    i = src.index('{', m.end())
    depth, j, n = 0, i, len(src)
    q = None
    while j < n:
        c = src[j]
        if q:
            if c == '\\':
                j += 2
                continue
            if c == q:
                q = None
        elif c in '\'"`':
            q = c
        elif src.startswith('//', j):
            j = src.index('\n', j)
            continue
        elif src.startswith('/*', j):
            j = src.index('*/', j) + 2
            continue
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return src[m.start():j + 1]
        j += 1
    raise AssertionError('sin cierre: ' + name)


def _strip_vars(css):
    """Reemplaza cada var(--x, respaldo) (con paréntesis anidados) por VAR: queda solo lo que NO es un token."""
    out, i = [], 0
    while True:
        k = css.find('var(', i)
        if k < 0:
            out.append(css[i:])
            return ''.join(out)
        out.append(css[i:k])
        depth, j = 0, k + 3
        while j < len(css):
            if css[j] == '(':
                depth += 1
            elif css[j] == ')':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append('VAR')
        i = j + 1


def _scene_css():
    a = SRC.index('/* ══ ESCENAS de la Cabina (2026-10-10)')
    b = SRC.index('/* CHAT de Khipu (2026-09-30)', a)
    return SRC[a:b]


def _lum(h):
    h = h.lstrip('#')
    ch = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    ch = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def _ratio(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


# ─────────────────────────────── estáticas ───────────────────────────────
def test_legacy_dark_vacia_y_mecanismo_conservado():
    m = re.search(r"var LEGACY_DARK = \[([^\]]*)\]", SRC)
    assert m and m.group(1).strip() == ''
    assert "body.classList.toggle('kd-legacy-dark', LEGACY_DARK.indexOf(kind) >= 0)" in SRC
    # el bloque de tokens oscuros para .kd-legacy-dark sigue existiendo (desktop.js lo usa como isla de respaldo)
    assert 'body.dark #bcp-ov,body.dark .kos-themed,body #bcp-ov.kos-classic,#bcp-ov .kd-legacy-dark{' in SRC


def test_css_de_escenas_sin_oscuros_fijos():
    css = _scene_css()
    low = css.lower()
    assert [c for c in LEGACY if c.lower() in low] == []           # ni siquiera como respaldo
    bare = _strip_vars(css)
    # fuera de var(--token, respaldo) no queda NINGÚN color literal (ni hex ni rgb/rgba)
    assert re.findall(r'#[0-9a-fA-F]{3,8}\b', bare) == []
    assert re.findall(r'rgba?\(', bare) == []
    # todo token usado como valor lleva respaldo oscuro (por si el CSS de la Cabina aún no se inyectó)
    assert re.findall(r'var\(--(?:os|kos)-[a-z0-9-]+\)', css) == []
    # las clases que engine/insights.js re-tematiza siguen existiendo
    for c in ('.bcp-icard', '.bcp-lh', '.bcp-row', '.bcp-casc', '.bcp-fact', '.bcp-hyper-hd'):
        assert c + '{' in css or c + ' ' in css, c


def test_funciones_de_escena_solo_con_tokens():
    for name in SCENE_FUNCS:
        body = re.sub(r'(?m)(^|\s)//[^\n]*', r'\1', _func(SRC, name))     # sin comentarios (pueden citar lo viejo)
        low = body.lower()
        assert [c for c in LEGACY if c.lower() in low] == [], name
        # ni los neón de siempre ni los atajos "color + '22'" (alfa hex pegado a un color: no funciona con var())
        assert '#2be38b' not in low and '#ff4d6a' not in low, name
        assert not re.search(r'\b(UP|DOWN|NEON|VIOLET)\b', body), name
        assert not re.search(r"(?:col|tint|fill|c)\s*\+\s*'[0-9a-fA-F]{2}'", body), name


def test_tabla_de_tokens_os_con_respaldo():
    m = re.search(r'var OS = \{(.*?)\};', SRC, re.S)
    assert m
    toks = dict(re.findall(r"(\w+): '(var\([^']+\))'", m.group(1)))
    for k in ('ink', 'ink2', 's1', 's2', 's3', 'line', 'acc', 'ai', 'good', 'bad', 'warn', 'goodInk', 'badInk', 'warnInk'):
        assert k in toks, k
        assert re.match(r'var\(--os-[a-z0-9-]+,[^)]', toks[k]), toks[k]       # siempre con respaldo
    # cada token usado existe en el bloque de tokens de la Cabina (claro y oscuro)
    for t in set(re.findall(r'var\((--os-[a-z0-9-]+)', m.group(1))):
        assert t + ':' in SRC, t


def test_insignias_simulado_y_dinero_real_intactas():
    b = _func(SRC, 'badgeHTML')
    assert "tb('paperBadge')" in b and "tb('realBadge')" in b
    assert "if (paper === true)" in b and "if (paper === false)" in b and "return '';" in b
    # 🔴 DINERO REAL: rojo SÓLIDO con texto blanco en ambos temas (≥ 4.5:1); 🧪: tinta ámbar AA sobre tinte ámbar
    assert 'color:#fff;background:#c42b2b' in b
    assert _ratio('#ffffff', '#c42b2b') >= 4.5
    assert "'color:' + OS.warnInk" in b
    # las palabras de las insignias no cambian
    assert "paperBadge:  { es: '🧪 SIMULADO (papel)', en: '🧪 SIMULATED (paper)' }" in SRC
    assert "realBadge:   { es: '🔴 DINERO REAL', en: '🔴 REAL MONEY' }" in SRC
    # la confirmación en línea pinta su insignia; el scalping también (con el modo real de /api/trade/status)
    assert '<span id="bcp-bk-cbadge"></span>' in _func(SRC, 'renderTradeConfirm')
    assert 'badgeHTML(x && typeof x.paper === \'boolean\' ? x.paper : false)' in _func(SRC, 'stageScalp')


def test_flujos_de_dinero_sin_cambios():
    rc = _func(SRC, 'renderTradeConfirm')
    # pop-up de toast.js si existe; si no, tarjeta en línea con Confirmar/Cancelar y montos rápidos
    assert 'KT.confirmOrder(ord, {' in rc and "if (yes) { confirmPendingOrder(); return; }" in rc
    for i in ('id="bcp-bk-ok"', 'id="bcp-bk-no"', 'id="bcp-bk-cstatus"', 'class="bcp-pill bcp-amt'):
        assert i in rc, i
    assert "box.querySelector('#bcp-bk-ok').addEventListener('click', confirmPendingOrder);" in rc
    cp = _func(SRC, 'confirmPendingOrder')
    assert 'window._executeTradeOrder(o)' in cp and '_pendingOrder = null;' in cp
    so = _func(SRC, '_scalpOrder')
    # 1 clic SOLO en papel: con dinero real (o modo desconocido) SIEMPRE la confirmación pop-up
    assert "var mode = KT ? await KT.order.resolveMode({}) : null;" in so
    assert "if (KT && mode !== 'paper') {" in so and 'await KT.confirmOrder(' in so
    lb = re.sub(r'(?m)(^|\s)//[^\n]*', r'\1', _func(SRC, 'loadBroker'))   # sin comentarios ("nunca prompt()")
    # el PIN: solo formulario en línea + _tradePinSave/_tradeFetch (nunca prompt() ni otro camino)
    assert 'window._tradePinSave(v)' in lb and "window._tradeFetch('/api/trade/positions/detail'" in lb
    assert 'prompt(' not in lb and 'window.confirm' not in SRC
    for i in ('id="bcp-bk-pin"', 'id="bcp-bk-pin-ok"', 'id="bcp-bk-refresh"'):
        assert i in lb, i
    sc = _func(SRC, 'stageScalp')
    for i in ('id="bcp-scalp-buy"', 'id="bcp-scalp-sell"', 'id="bcp-scalp-price"', 'id="bcp-scalp-mode"', 'class="bcp-pill bcp-scalp-sym',
              'class="bcp-pill bcp-scalp-amt', 'setInterval(_scalpPoll, 2500)', 'setInterval(_scalpLoadPos, 5000)'):
        assert i in sc, i
    # los atributos de presentación SVG no resuelven var(): el trazo del mini-gráfico va en style=""
    assert '\'" fill="none" style="stroke:\' + (up ? OS.good : OS.bad)' in _func(SRC, '_scalpDrawSpark')


def test_ids_y_clases_que_usan_otros_modulos():
    for i in ('id="bcp-bk-confirm"', 'id="bcp-bk-acct"', 'id="bcp-bk-report"', 'id="bcp-bk-advbtn"', 'id="bcp-bk-advice"',
              'id="bcp-bk-pos"', 'id="bcp-bk-ord"', 'id="bcp-bk-aicomment"', 'id="bcp-scr"', 'id="bcp-deep-steps"',
              'id="bcp-deep-result"', 'id="bcp-ag-body"', 'id="bcp-rs-body"', 'id="bcp-cmp-profile"', 'id="bcp-cmp-fund"',
              'id="bcp-cmpA"', 'id="bcp-cmpB"', "class=\"bcp-adv-apply", 'class="bcp-home-pf"', "'.cmp-tab'",
              'data-cmp="', 'id="bcp-pick-ok"', 'class="bcp-pick-it"', 'id="bcp-demotxt"',
              'id="bcp-demodots"'):
        assert i in SRC, i
    # Comparar: pestañas = control segmentado accesible (aria-selected) en vez de bordes neón en style=""
    cmp = _func(SRC, 'stageCompare')
    assert 'class="bcp-seg" role="tablist"' in cmp and "x.setAttribute('aria-selected', x === btn ? 'true' : 'false')" in cmp


def test_mascotas_donde_habla_un_agente():
    rr = _func(SRC, 'renderResearch')
    assert '_mascot(ag, 22)' in rr and "esc(_agentName(ag))" in rr
    m = re.search(r'var RS_AGENT = \{([^}]*)\}', SRC)
    agents = dict(re.findall(r"(\w+): '(\w+)'", m.group(1)))
    assert agents == {'thesis': 'comite', 'sector': 'analista', 'competitors': 'analista', 'geopolitics': 'radar',
                      'chokepoints': 'cadena', 'risks': 'tecnico', 'watch': 'radar'}
    assert "_stackHTML(['analista', 'radar', 'cadena', 'comite'], 26)" in _func(SRC, 'stageResearch')
    assert "_mascot('khipu', 22" in _func(SRC, '_khipuSays')
    assert '_khipuSays(' in _func(SRC, '_fetchPortfolioComment') and '_khipuSays(' in _func(SRC, '_renderAdvice')
    assert "_mascot('khipu', 22)" in _func(SRC, 'stageBroker')            # botón «Consejos de Khipu»
    assert "_mascot('khipu', 30" in _func(SRC, 'stageDeep')
    assert "_mascot('khipu', 34, { state: 'talk' })" in _func(SRC, '_demoRenderBar')
    # sin los emojis que hacían de agente
    assert '🧠 Khipu:' not in SRC and '💬 Khipu:' not in SRC


def test_textos_nuevos_bilingues():
    assert "esc(en ? 'Compare by' : 'Comparar por')" in SRC
    assert "(en2 ? 'Trading PIN' : 'PIN de trading')" in SRC
    # las etiquetas de la investigación por agente salen de KhipuMascot.name (bilingüe) con respaldo es/en
    assert "AGENT_FALLBACK = { khipu: ['#f07fa0', '#7a4ce8', 'Khipu', 'Khipu'], analista: ['#7d8be6', '#4054cf', 'Analista', 'Analyst']" in SRC


def test_cada_escena_builtin_tiene_su_rama_de_render():
    m = re.search(r"var BUILTIN_KINDS = \[([^\]]*)\]", SRC)
    kinds = re.findall(r"'(\w+)'", m.group(1))
    assert len(kinds) >= 15
    rnd = _func(SRC, 'render')
    for k in kinds:
        assert "kind === '" + k + "'" in rnd, k


# ─────────────────────────────── navegador ───────────────────────────────
PAGE = r"""<!doctype html><html lang="es"><head><meta charset="utf-8"><style>
html,body{margin:0;height:100%;font-family:system-ui}
</style></head><body>
<main id="mainmap" style="display:flex"><div>mapa</div></main>
<section id="terminal-panel" style="display:none">terminal</section>
<section id="crypto-panel" style="display:none">cripto</section>
<script>
window.LANG = 'es';
window.NODES = [{ id: 'Nvidia', label: 'Nvidia', mkt: 'NVDA', cat: 'gpu' }, { id: 'AMD', label: 'AMD', mkt: 'AMD', cat: 'gpu' },
  { id: 'TSMC', label: 'TSMC', mkt: 'TSM', cat: 'foundry' }];
window.NODE_BY_ID = {}; window.NODES.forEach(function (n) { window.NODE_BY_ID[n.id] = n; });
window.LINKS = []; window.SECTORS9 = { cloud_ia: { label: 'IA', color: '#4C8DF6' } }; window.CAT_TO_SECTOR = {};
window.computeNRS = function () { return 40; };
window.buildXRayHTML = function (id) { return '<div class="xr-name">' + id + '</div>'; };
window.wireXRay = function () {};
window.KhipuState = { simulate: function () { return { impact: new Map([['AMD', 40], ['TSMC', 25]]) }; } };
window.xrayComputeWinners = function () { return [{ id: 'AMD', up: 12 }]; };
window._tradePinStored = function () { return '1234'; };
window._tradeFetch = function (u, o) { return fetch(u, o); };
window._tradeAccountInfo = function () { return Promise.resolve({ equity: 101234.56, cash: 40210.1, buying_power: 80420.2, paper: true }); };
window._tradeStatusInfo = function () { return Promise.resolve({ pin_set: true, paper: true }); };
window._resolveTradeSymbol = function (s) { return Promise.resolve({ ok: true, symbol: s, label: s, kind: 'crypto' }); };
window._executeTradeOrder = function () { return Promise.resolve({ ok: true, data: { status: 'accepted' } }); };
window.KhipuChat = { appendUser: function () {}, appendPending: function () { return document.createElement('div'); },
  send: function () { return new Promise(function () {}); }, fillReply: function () {}, fillError: function () {},
  classify: function () { return { kind: 'brain' }; }, ensureStyles: function () {}, clear: function () {},
  noteEntity: function () {}, remember: function () {} };
</script></body></html>"""

API = {
    '/api/trade/positions/detail': [{'symbol': 'NVDA', 'qty': 12, 'market_val': 2240.5, 'unrealized': 210.4, 'unrealized_pct': 10.36, 'cost_basis': 2030.1}],
    '/api/trade/history': [{'side': 'buy', 'symbol': 'NVDA', 'notional': 500, 'status': 'filled', 'created_at': '2026-10-09T14:00:00Z'}],
    '/api/portfolio/comment': {'comment': 'Cartera concentrada en semiconductores.'},
    '/api/screener/growth': {'ranked': [{'id': 'Nvidia', 'label': 'Nvidia', 'score': 12.4, 'r5': 3.1, 'r20': 9.8, 'r60': 21.4,
                                         'pagerank_rank': 3, 'above_ma20': True}], 'coverage': {'complete': True, 'warm': 5, 'total': 5}},
    '/api/deep/analyze': {'ok': True},
    '/api/deep/status': {'running': False, 'steps': [{'paso': 'Planear', 'detalle': 'qué mirar'}],
                         'result': {'answer': 'Respuesta.', 'sim': {'afectadas': 3, 'shock': 'TSMC'}, 'focos': ['TSMC'], 'model': 'x'}},
    '/api/research/deep': {'thesis': 'Tesis.', 'sector': 'Sector.', 'competitors': ['AMD'], 'geopolitics': 'Geo.',
                           'chokepoints': ['CoWoS'], 'risks': ['China'], 'watch': ['HBM'], 'disclaimer': 'No es asesoría.'},
    '/api/sim/agents': {'ok': True, 'narrative': 'Narrativa.', 'theme': 'HBM', 'summary': {'n_hit': 2, 'n_benefit': 1, 'sectors': ['a']},
                        'impacts': [{'id': 'AMD', 'label': 'AMD', 'pct': -9, 'channel': 'direct'}, {'id': 'TSMC', 'label': 'TSMC', 'pct': 4}],
                        'agents': [{'name': 'MOFCOM', 'type': 'gobierno', 'stance': 'Presiona.'}], 'quotes': [{'agent': 'AMD', 'quote': 'Ok.'}],
                        'rounds': [{'round': 1, 'events': ['Evento.']}], 'watch': ['Precio HBM']},
    '/api/findossier/NVDA': {'available': True, 'source': 'fmp', 'revenue': [130e9], 'gross_margin': [75.0]},
    '/api/findossier/AMD': {'available': True, 'source': 'fmp', 'revenue': [25.8e9], 'gross_margin': [49.0]},
}

# escena → argumento (las que no se listan van sin argumento)
ARGS = {
    'broker': {'confirm': {'symbol': 'BTC/USD', 'side': 'buy', 'notional': 500, 'label': 'Bitcoin', 'kind': 'crypto'}},
    'scalp': {'sym': 'BTC/USD'}, 'pick': {'for': 'compare', 'a': 'Nvidia'}, 'xray': 'Nvidia', 'compare': {'a': 'Nvidia', 'b': 'AMD'},
    'agentsim': {'scenario': 'China prohíbe exportar HBM', 'seeds': []}, 'research': {'id': 'Nvidia'},
    'sim': {'id': 'TSMC', 'kind': 'collapse'}, 'deep': '¿Qué pasa si TSMC se detiene?', 'graph': None, 'terminal': None,
}


def _chromium(p):
    for kw in ({}, {'executable_path': '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'}):
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


def _page(browser, w=1440, h=900):
    c = browser.new_context(viewport={'width': w, 'height': h})

    def handler(route):
        url = route.request.url
        path = url[len('http://khipu.test'):].split('?')[0]
        if path in ('', '/'):
            return route.fulfill(status=200, content_type='text/html', body=PAGE)
        if path.startswith('/api/scalp/price/'):
            return route.fulfill(status=200, content_type='application/json', body=json.dumps({'price': 62150.12, 'prev': 61800}))
        if path in API:
            return route.fulfill(status=200, content_type='application/json', body=json.dumps(API[path]))
        return route.fulfill(status=503, content_type='application/json', body=json.dumps({'error': 'sin servidor'}))
    c.route('http://khipu.test/**', handler)
    pg = c.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://khipu.test/')
    for p in (MASCOT_PATH, DESKTOP_PATH, COCKPIT_PATH):
        pg.add_script_tag(content=_r(p))
    pg.evaluate('BixbyCockpit.open()')
    pg.wait_for_timeout(250)
    return c, pg, errs


@pytest.mark.parametrize('dark', [False, True])
def test_navegador_cada_escena_builtin_se_pinta_con_el_tema(browser, dark):
    kinds = re.findall(r"'(\w+)'", re.search(r"var BUILTIN_KINDS = \[([^\]]*)\]", SRC).group(1))
    c, pg, errs = _page(browser)
    pg.evaluate("(d) => document.body.classList.toggle('dark', d)", dark)
    assert pg.evaluate('() => KhipuDesk.active()')
    bad = []
    for k in kinds:
        pg.evaluate('() => KhipuDesk.closeAll()')
        pg.evaluate("([k, a]) => BixbyCockpit.stage(k, a === null ? undefined : a)", [k, ARGS.get(k)])
        pg.wait_for_timeout(450 if k in ('deep', 'agentsim', 'research', 'broker', 'screener', 'compare') else 200)
        st = pg.evaluate("""(k) => {
          const w = document.querySelector('.kd-win[data-kind="' + k + '"]'); if (!w) return null;
          const b = w.querySelector('.kd-body');
          // rgb(…) en 0-255; color(srgb …) (lo que devuelve color-mix) en 0-1
          const lum = (c) => { const m = c.match(/[\\d.]+/g); if (!m) return null; const k = /^color\\(/.test(c) ? 1 : 255;
            const v = m.slice(0, 3).map(x => { x = x / k; return x <= .03928 ? x / 12.92 : Math.pow((x + .055) / 1.055, 2.4); }); return .2126 * v[0] + .7152 * v[1] + .0722 * v[2]; };
          // la tinta de un texto propio de la escena: el título de la sección o la primera fila de texto
          const t = b.querySelector('.bcp-lh, .bcp-pick-h, .bcp-simhd .big, .bcp-stat b, .bcp-loading, .bcp-row .nm, .nm');
          return { legacy: b.classList.contains('kd-legacy-dark'), html: b.innerHTML.length,
                   bg: getComputedStyle(b).backgroundColor, ink: t ? lum(getComputedStyle(t).color) : null };
        }""", k)
        if not st:
            bad.append((k, 'sin ventana'))
            continue
        if st['legacy']:
            bad.append((k, 'kd-legacy-dark'))
        if st['html'] < 40:
            bad.append((k, 'vacía'))
        if 'rgb(11, 15, 25)' in st['bg']:
            bad.append((k, 'fondo oscuro fijo'))
        if st['ink'] is not None and ((not dark and st['ink'] > 0.35) or (dark and st['ink'] < 0.2)):
            bad.append((k, 'tinta del tema equivocada', st['ink']))
    assert not bad, bad
    assert not errs, errs
    c.close()


def test_navegador_insignia_dinero_real_y_confirmacion_en_linea(browser):
    c, pg, errs = _page(browser)
    pg.evaluate("""() => { window._tradeAccountInfo = function () { return Promise.resolve({ equity: 5, cash: 5, buying_power: 5, paper: false }); };
      window._tradeStatusInfo = function () { return Promise.resolve({ pin_set: true, paper: false }); };
      const KT = window.KhipuToast; window.KhipuToast = null;
      BixbyCockpit.stage('broker', { confirm: { symbol: 'NVDA', side: 'sell', notional: 100, label: 'Nvidia', kind: 'equity' } });
      window.KhipuToast = KT; }""")
    pg.wait_for_timeout(500)
    r = pg.evaluate("""() => { const b = document.querySelector('#bcp-bk-cbadge .bcp-badge');
      const ok = document.getElementById('bcp-bk-ok'), no = document.getElementById('bcp-bk-no');
      const on = document.querySelector('.bcp-amt.on');
      return { cls: b && b.className, txt: b && b.textContent, col: b && getComputedStyle(b).color, bg: b && getComputedStyle(b).backgroundColor,
               ok: !!ok, no: !!no, on: on && on.getAttribute('data-amt') }; }""")
    assert r['cls'] == 'bcp-badge real' and r['txt'] == '🔴 DINERO REAL'
    assert r['col'] == 'rgb(255, 255, 255)' and r['bg'] == 'rgb(196, 43, 43)'
    assert r['ok'] and r['no'] and r['on'] == '100'
    # un toque en otro monto re-pinta la tarjeta con ese monto (mismo flujo de siempre); nada se envía sin Confirmar
    pg.evaluate("() => { window.__sent = 0; window._executeTradeOrder = function () { window.__sent++; return Promise.resolve({ ok: true }); }; document.querySelector('.bcp-amt[data-amt=\"500\"]').click(); }")
    pg.wait_for_timeout(100)
    assert pg.evaluate("() => document.querySelector('.bcp-amt.on').getAttribute('data-amt')") == '500'
    assert pg.evaluate('() => window.__sent') == 0
    pg.evaluate("() => document.getElementById('bcp-bk-ok').click()")
    pg.wait_for_timeout(100)
    assert pg.evaluate('() => window.__sent') == 1
    assert not errs, errs
    c.close()
