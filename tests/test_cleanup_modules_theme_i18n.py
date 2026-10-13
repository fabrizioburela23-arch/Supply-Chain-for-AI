"""Limpieza 2026-10-11 — nueve módulos que seguían con la piel NEXUS (paleta oscura FIJA) entran a Khipus OS y
cumplen la regla bilingüe.

Antes (medido): spacemonitor 54, worldmonitor 50, crypto 49, livesim 36, compare 17, layers 14, matrixview 10 y
termdata 8 colores hex viejos → en el tema CLARO eran islas oscuras o texto ilegible; layers.js («Capas»,
«Conexiones»…), matrixview.js y live.js no tenían idioma.

Ahora:
  · la piel usa var(--os-*, respaldo) (tokens de engine/cockpit.js; claro = body sin .dark, oscuro = body.dark) y
    la raíz de cada panel/overlay que vive fuera de #bcp-ov lleva .kos-themed. termdata.js sigue con los tokens
    --kt-* de la Terminal (su propio sistema claro/oscuro, app.html) y ya no tiene colores fijos fuera de var().
  · los colores de DATOS (capas, severidad, NRS, sectores, tipos de golpe, 24h%, KPIs, globo) viven en constantes
    de paleta con nombre; como texto pasan por .wm-c/.sm-c/.ls-c/.cr-c, que en el tema claro los mezcla con la
    tinta (dentro de @supports) para que se lean.
  · el ESCENARIO de los globos (World/Space Monitor) sigue oscuro a propósito (STAGE): el look 'monitor' de
    engine/globe.js dibuja halo aditivo y estrellas; lo que flota encima (barra, paneles, botones) sigue el tema.
  · canvas (matrices, burbujas cripto, gráfico 90d) leen los tokens al dibujar y se re-pintan al cambiar el tema.
  · todo texto visible tiene ES y EN y se re-etiqueta al cambiar de idioma (<html lang> que fija applyLang()).

Dos niveles: estático (siempre) y navegador (Playwright + Chromium, si hay).
"""
import json
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _r(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8') as f:
        return f.read()


FILES = ['spacemonitor', 'worldmonitor', 'crypto', 'livesim', 'compare', 'layers', 'matrixview', 'termdata', 'live']
SRC = {f: _r('engine', f + '.js') for f in FILES}
COCKPIT = _r('engine', 'cockpit.js')
HTML = _r('app.html')

HEX_RE = re.compile(r'#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b')

# Paletas de DATOS con nombre (no son piel): se excluyen del conteo. Cada entrada = el comienzo de la definición;
# se quita hasta el cierre balanceado del primer [ o { que sigue.
DATA_PALETTES = {
    'spacemonitor': ['var LAYERS = [', 'var ST_C = {', 'var PALETTE = [', 'var STAGE = {', 'var SPC = {', 'var GLOBE = {',
                     'function nrsColor('],
    'worldmonitor': ['var LAYERS = [', 'var STAGE = {', 'var PAL = {', 'var GLOBE = {', 'function sevColor(',
                     'function nrsColor('],
    'crypto': ['var CR_PAL = {', 'function pctCol('],
    'livesim': ['var TYPES = ['],
    'compare': ['function secColor('],
    'layers': [],
    'matrixview': ['function secColor('],
    'termdata': [],
    'live': [],
}

# RATCHET: colores hex fijos que quedan FUERA de var(--…, respaldo), fuera de las paletas de datos de arriba y fuera
# de los lectores de tokens para canvas (g('--os-x', 'respaldo')). Tras la limpieza son 0 en los nueve módulos;
# si un cambio necesita uno nuevo, va a una paleta con nombre (y se añade aquí) o se sube este número a conciencia.
CEILING = {f: 0 for f in FILES}

# superficies/tintas oscuras de la piel NEXUS: no deben volver como color fijo (fuera de var() o de un lector de tokens)
NEXUS_DARK = ['rgba(15,21,34', 'rgba(21,28,45', 'rgba(5,10,20', 'rgba(5,8,20', 'rgba(13,19,33', 'rgba(8,12,24',
              'rgba(3,6,12', 'rgba(10,18,34', 'rgba(10,16,36', 'rgba(12,18,40', 'rgba(4,8,16', 'rgba(4,6,16',
              'rgba(3,7,15', 'rgba(3,5,14', 'rgba(20,30,52', 'rgba(8,14,26', 'rgba(20,16,34', 'rgba(24,18,40',
              'rgba(2,4,12']


def _strip_var_fallbacks(src):
    """Quita cada var(--x, respaldo) completo (anidados incluidos): lo que queda son colores FIJOS."""
    out, i = [], 0
    while True:
        j = src.find('var(--', i)
        if j < 0:
            out.append(src[i:])
            break
        out.append(src[i:j])
        depth, k = 0, j
        while k < len(src):
            if src[k] == '(':
                depth += 1
            elif src[k] == ')':
                depth -= 1
                if depth == 0:
                    break
            k += 1
        out.append('VAR')
        i = k + 1
    return ''.join(out)


def _strip_token_readers(src):
    """Quita los respaldos de los lectores de tokens para canvas: g('--os-ink', '#E8EDFB') → g(TOKEN)."""
    return re.sub(r"'--(?:os|kos|kt)-[a-z0-9-]+'\s*,\s*'[^']*'", 'TOKEN', src)


def _strip_comments(src):
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    return '\n'.join(l for l in src.split('\n') if not l.lstrip().startswith('//'))


def _balanced_end(src, start):
    """Índice justo después del cierre balanceado del primer [ o { desde `start` (salta cadenas '…' y "…")."""
    k = start
    while src[k] not in '[{':
        k += 1
    depth, q = 0, None
    while k < len(src):
        c = src[k]
        if q:
            if c == '\\':
                k += 2
                continue
            if c == q:
                q = None
        elif c in '\'"':
            q = c
        elif c in '[{':
            depth += 1
        elif c in ']}':
            depth -= 1
            if depth == 0:
                return k + 1
        k += 1
    raise AssertionError('sin cierre balanceado')


def _strip_palettes(src, markers):
    for m in markers:
        assert src.count(m) == 1, 'la paleta de datos %r debe definirse exactamente una vez' % m
        a = src.index(m)
        src = src[:a] + 'PALETTE' + src[_balanced_end(src, a):]
    return src


def _rest(name):
    s = _strip_comments(SRC[name])
    s = _strip_palettes(s, DATA_PALETTES[name])
    return _strip_token_readers(_strip_var_fallbacks(s))


# ── estático ────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize('name', FILES)
def test_sin_colores_fijos_fuera_de_tokens_ni_paletas(name):
    found = HEX_RE.findall(_rest(name))
    assert len(found) <= CEILING[name], '%s: colores fijos fuera de var()/paletas de datos: %s' % (name, found)


@pytest.mark.parametrize('name', FILES)
def test_sin_superficies_oscuras_nexus(name):
    rest = _rest(name).replace(' ', '')
    for c in NEXUS_DARK:
        assert c not in rest, '%s: superficie oscura NEXUS fija: %s' % (name, c)


@pytest.mark.parametrize('name', FILES)
def test_idioma_es_en(name):
    s = SRC[name]
    assert 'window.LANG' in s and 'eco_lang' in s, name


@pytest.mark.parametrize('name', ['spacemonitor', 'worldmonitor', 'crypto', 'livesim', 'compare', 'layers',
                                  'matrixview', 'live'])
def test_re_etiqueta_al_cambiar_idioma(name):
    # applyLang() (app.html) fija <html lang>: cada módulo con texto pintado lo observa
    assert "attributeFilter: ['lang']" in SRC[name], name
    assert 'document.documentElement.lang=LANG' in HTML


def test_termdata_re_etiqueta_por_la_terminal_y_usa_tokens_kt():
    td = SRC['termdata']
    assert "window.TermData = { load: load, mount: mount, relabel: relabel" in td
    assert 'window.TermData.relabel()' in HTML              # _termRelabel, enganchado a applyLang
    # tokens --kt-* de la Terminal (claro/oscuro en app.html); sin respaldos de la paleta NEXUS
    assert 'var(--kt-ink-3,#6E7586)' in td and 'var(--kt-up,#2EBD85)' in td and 'var(--kt-down,#F6465D)' in td
    for old in ('#7C87A3', '#FF4D6A', '#FFB300', '#2BE38B'):
        assert old not in td, old
    assert '--kt-ink-3:' in HTML and '--kt-up:' in HTML


@pytest.mark.parametrize('name,frag', [
    ('layers', "btn.id = 'lay-btn'; btn.className = 'kos-themed';"),
    ('layers', "panel.id = 'lay-panel'; panel.className = 'kos-themed';"),
    ('livesim', "btn.id = 'ls-btn'; btn.className = 'kos-themed';"),
    ('livesim', "panel.id = 'ls-panel'; panel.className = 'kos-themed';"),
    ('compare', "ov.className = 'kos-themed';"),
    ('matrixview', "host.classList.add('kos-themed');"),
    ('matrixview', "tip.id = 'mxv-tip'; tip.className = 'kos-themed';"),
    ('crypto', 'class="kos-themed cr-root"'),
    ('worldmonitor', '<div class="wm kos-themed" id="wm">'),
    ('spacemonitor', '<div class="sm kos-themed" id="sm">'),
    ('live', "wrap.className = 'kos-themed';"),
])
def test_raices_llevan_kos_themed(name, frag):
    assert frag in SRC[name], (name, frag)
    assert 'body:not(.dark) .kos-themed' in COCKPIT and 'body.dark .kos-themed' in COCKPIT


@pytest.mark.parametrize('name', [f for f in FILES if f != 'termdata'])
def test_cada_token_existe_en_cockpit(name):
    used = set(re.findall(r'var\((--(?:os|kos)-[a-z0-9-]+)', SRC[name]))
    used |= set(re.findall(r"'(--(?:os|kos)-[a-z0-9-]+)'", SRC[name]))
    assert used, name
    for tok in used:
        assert tok + ':' in COCKPIT, '%s usa %s y cockpit.js no lo define' % (name, tok)


@pytest.mark.parametrize('name', ['spacemonitor', 'worldmonitor', 'crypto', 'livesim'])
def test_color_mix_solo_dentro_de_supports(name):
    # el oscurecimiento de los colores de datos en el tema claro va SIEMPRE dentro de @supports (sin soporte →
    # se ve el color del dato tal cual, como antes) y nunca en un style="" (ahí no hay respaldo posible)
    for line in SRC[name].split('\n'):
        if 'color-mix(' in line:
            assert '@supports (color:color-mix(' in line, (name, line.strip()[:120])


@pytest.mark.parametrize('name,cls', [('spacemonitor', 'sm-c'), ('worldmonitor', 'wm-c'), ('crypto', 'cr-c'),
                                      ('livesim', 'ls-c')])
def test_texto_en_color_de_dato_se_lee_en_claro(name, cls):
    s = SRC[name]
    # !important = la precedencia del style="color:…" que reemplaza (si no, p.ej. .sm-kv .v.mono le ganaba al NRS)
    assert ('.' + cls + '{color:var(--' + cls + ')!important}') in s
    assert ('body:not(.dark) ' in s) and ('color-mix(in srgb,var(--' + cls + ') 50%,var(--os-ink,#111216))!important') in s


@pytest.mark.parametrize('name,frag', [
    ('spacemonitor', ".sm-up{color:var(--os-good-ink,#2BE38B)!important}.sm-down{color:var(--os-bad-ink,#FF4D6A)!important}"),
    ('spacemonitor', ".sm-warn{color:var(--os-warn-ink,#FFD27A)!important}"),
    ('worldmonitor', ".wm-warn{color:var(--os-warn-ink,#FFB300)!important}"),
    ('livesim', ".ls-up{color:var(--os-good-ink,#2BE38B)!important}.ls-down{color:var(--os-bad-ink,#FF4D6A)!important}"),
])
def test_clases_que_reemplazan_style_color_ganan_como_el(name, frag):
    assert frag in SRC[name], (name, frag)


def test_globos_conservan_el_escenario_oscuro_a_proposito():
    for name, cls in (('worldmonitor', '.wm{'), ('spacemonitor', '.sm{')):
        s = SRC[name]
        assert "var STAGE = { bg: 'radial-gradient(" in s, name
        assert (cls + "position:relative;") in s and "background:' + STAGE.bg + ';'" in s, name
        # lo que flota encima sigue el tema
        assert '--os-surface' in s and 'kos-themed' in s


def test_canvas_leen_tokens_y_se_repintan_con_el_tema():
    mv, cr = SRC['matrixview'], SRC['crypto']
    for s in (mv, cr):
        assert "attributeFilter: ['class']" in s and 'getComputedStyle' in s and "getPropertyValue(name)" in s
    assert 'function redraw()' in mv and "g('--os-line'," in mv
    assert 'function bubPal(el)' in cr and 'BUB.pal = null' in cr and 'function chartPal(up)' in cr
    assert "CHART.update('none')" in cr


def test_cripto_dinero_intacto():
    s = SRC['crypto']
    for frag in ("T2('cr_trade_paper', '🧪 SIMULADO (papel)', '🧪 SIMULATED (paper)')",
                 "T2('cr_trade_real', '🔴 DINERO REAL', '🔴 REAL MONEY')",
                 "T2('cr_trade_confirm', 'Confirmar', 'Confirm')", "T2('cr_trade_cancel', 'Cancelar', 'Cancel')",
                 'trade: tradeAsk,', 'tradeConfirm: tradeSend,', "window._tradeFetch('/api/trade/order', {"):
        assert frag in s, frag
    # al cambiar de idioma NO se re-pinta con una orden esperando confirmación
    assert 'if (!onScreen() || TRD) return;' in s
    # textos que estaban solo en un idioma
    assert "T2('cr_refresh', 'Actualizar', 'Refresh')" in s
    assert "T2('cr_trade_off', 'Trading deshabilitado — configura TRADE_PIN en Railway', 'Trading disabled — set TRADE_PIN in Railway')" in s


@pytest.mark.parametrize('name,frag', [
    ('layers', "{ id: 'links',   label: 'Conexiones',         en: 'Links',"),
    ('layers', "L('Capas', 'Layers')"),
    ('layers', "L('Capas del mapa', 'Map layers')"),
    ('matrixview', "L('Las 9 matrices de relación', 'The 9 relationship matrices')"),
    ('matrixview', "L('peso', 'weight')"),
    ('live', "L('EN VIVO', 'LIVE')"),
    ('live', "L('Modo en vivo: insights y radar automáticos', 'Live mode: automatic insights and radar')"),
    ('live', "L('🔔 Alerta: ', '🔔 Alert: ')"),
])
def test_textos_nuevos_bilingues(name, frag):
    assert frag in SRC[name], (name, frag)


def test_layers_todas_las_capas_tienen_en():
    s = SRC['layers']
    block = s[s.index('var LAYERS = ['):s.index('];', s.index('var LAYERS = ['))]
    assert block.count("id: '") == block.count(" en: '") == 5


@pytest.mark.parametrize('name', FILES)
def test_sintaxis_node(name):
    node = shutil.which('node')
    if not node:
        pytest.skip('node no disponible')
    r = subprocess.run([node, '--check', os.path.join(ROOT, 'engine', name + '.js')], capture_output=True, text=True,
                       timeout=30)
    assert r.returncode == 0, r.stderr


# ── navegador ───────────────────────────────────────────────────────────────────────────────────────────
PAGE = r"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<style>html,body{margin:0;font-family:system-ui}body{background:#EDEDF5}body.dark{background:#0E0F14}</style></head><body>
<div class="graph-wrap" style="position:relative;width:1000px;height:640px"><svg id="graph"></svg></div>
<div id="an-matrix"></div>
<section id="crypto-panel" style="display:block;min-height:400px"></section>
<div id="wm-root" style="position:relative;width:1300px;height:760px"></div>
<div id="sp-root" style="position:relative;width:1300px;height:760px"></div>
<footer><span id="footer-nodecount">3</span></footer>
<script>
window.LANG = 'es';
window.esc = function (s) { return String(s == null ? '' : s); };
window.SECTORS9 = { fabricacion: { label: 'Fabricación', en: 'Manufacturing', color: '#FF7A45' },
  diseno: { label: 'Diseño & IP', en: 'Design & IP', color: '#9D6BFF' }, cloud_ia: { label: 'Cloud & IA', en: 'Cloud & AI', color: '#00E0FF' } };
window.CAT_TO_SECTOR = { foundry: 'fabricacion', fabless: 'diseno', cloud: 'cloud_ia' };
window.sectorName = function (k, byCat) { var s = window.SECTORS9[byCat ? (window.CAT_TO_SECTOR[k] || 'cloud_ia') : k]; return s ? (window.LANG === 'en' ? s.en : s.label) : k; };
window.NODES = [{ id: 'TSMC', label: 'TSMC', mkt: 'TSM', cat: 'foundry', country: 'Taiwan', margin: 0.55 },
  { id: 'Nvidia', label: 'Nvidia', mkt: 'NVDA', cat: 'fabless', country: 'EEUU', margin: 0.6, margin_live: true },
  { id: 'Amazon', label: 'Amazon', mkt: 'AMZN', cat: 'cloud', country: 'EEUU', margin: 0.1 }];
window.NODE_BY_ID = {}; window.NODES.forEach(function (n) { window.NODE_BY_ID[n.id] = n; });
window.LINKS = [{ source: 'TSMC', target: 'Nvidia', w: 5, rel: 'fab', type: 'fab' }, { source: 'Nvidia', target: 'Amazon', w: 4, rel: 'supply', type: 'supply' }];
window.NODE_META = { TSMC: { mktcap_b: 900 }, Nvidia: { mktcap_b: 4400, mktcap_live: { as_of: 'hoy' } }, Amazon: { mktcap_b: 2000 } };
window.computeNRS = function (id) { return id === 'TSMC' ? 72 : 30; };
window.computeNRSBreakdown = function () { return { terms: [{ key: 'Geopolítica', val: 22, max: 30, hot: true }, { key: 'Cadena', val: 10, max: 25, hot: false }] }; };
window.MKT = { quotes: {}, pos: {} };
window.KhipuState = { idsInSector: function () { return ['TSMC']; }, idsInCountry: function () { return ['TSMC']; },
  frames: function (r) { return [r.impact]; } };
// paso 13 INFRA_OPERATIVA: las cifras las da el motor del servidor por window.KhipuHot (aquí, un doble)
window.KhipuHot = { simulate: function () { var m = new Map([['TSMC', 100], ['Nvidia', 70], ['Amazon', 30]]);
    return Promise.resolve({ ok: true, kind: 'collapse', direction: 'down', severity: 100, targets: ['TSMC'], impact: m,
      victims: [{ id: 'Nvidia', pct: 70, hop: 1 }, { id: 'Amazon', pct: 30, hop: 2 }], reach_1: 2, reach_10: 2, sum_impact: 1,
      view: { generation: 'g0.r0.c0.snapshot', graph_version: 0, source: 'snapshot', age_ms: 1000 } }); },
  rivals: function () { return []; }, stamp: function () { return 'g0'; }, stampHTML: function () { return '<span class="kh-hot-stamp">g0</span>'; } };
try { localStorage.setItem('kh_cryptoview', 'list'); } catch (e) {}
</script></body></html>"""

ASSETS = {'assets': [
    {'id': 'bitcoin', 'symbol': 'btc', 'name': 'Bitcoin', 'rank': 1, 'price': 100000, 'change_24h_pct': 1.2,
     'change_7d_pct': -2.1, 'market_cap': 2.0e12, 'volume_24h': 4.0e10},
    {'id': 'ethereum', 'symbol': 'eth', 'name': 'Ethereum', 'rank': 2, 'price': 4000, 'change_24h_pct': -3.4,
     'change_7d_pct': 5.0, 'market_cap': 4.8e11, 'volume_24h': 2.0e10}]}

# contraste WCAG con mezcla alfa sobre el fondo EFECTIVO (se suben los ancestros hasta un fondo opaco)
CONTRAST_JS = r"""
window.__parse = function (c) {
  var m = /^rgba?\(([^)]+)\)/.exec(c);
  if (m) { var p = m[1].split(/[\s,\/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; }
  m = /^color\(srgb ([^)]+)\)/.exec(c);
  if (m) { var q = m[1].split(/[\s\/]+/).filter(Boolean).map(Number); return [q[0] * 255, q[1] * 255, q[2] * 255, q.length > 3 ? q[3] : 1]; }
  return null;
};
window.__over = function (top, bot) { var a = top[3]; return [top[0] * a + bot[0] * (1 - a), top[1] * a + bot[1] * (1 - a), top[2] * a + bot[2] * (1 - a), 1]; };
window.__bg = function (el) {
  var layers = [];
  for (var e = el; e; e = e.parentElement) {
    var c = __parse(getComputedStyle(e).backgroundColor);
    if (c && c[3] > 0) { layers.push(c); if (c[3] >= 1) break; }
  }
  var acc = document.body.classList.contains('dark') ? [14, 15, 20, 1] : [237, 237, 245, 1];
  for (var i = layers.length - 1; i >= 0; i--) acc = __over(layers[i], acc);
  return acc;
};
window.__lum = function (c) {
  var f = function (v) { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]);
};
window.__contrast = function (sel) {
  var el = document.querySelector(sel);
  if (!el) return null;
  var bg = __bg(el), fg = __parse(getComputedStyle(el).color);
  if (fg[3] < 1) fg = __over(fg, bg);
  var a = __lum(fg), b = __lum(bg);
  return Math.round((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05) * 100) / 100;
};
window.__bgLum = function (sel) { var el = document.querySelector(sel); return el ? Math.round(__lum(__bg(el)) * 100) / 100 : null; };
"""

MODULES = ['layers', 'livesim', 'compare', 'matrixview', 'crypto', 'worldmonitor', 'spacemonitor', 'live']


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


def _page(browser, dark):
    c = browser.new_context(viewport={'width': 1440, 'height': 900}, service_workers='block')

    def handler(route):
        path = route.request.url[len('http://khipu.test'):].split('?')[0]
        if path in ('', '/'):
            return route.fulfill(status=200, content_type='text/html', body=PAGE)
        if path == '/api/crypto/markets':
            return route.fulfill(status=200, content_type='application/json', body=json.dumps(ASSETS))
        return route.fulfill(status=503, content_type='application/json', body='{"error":"sin servidor"}')
    c.route('http://khipu.test/**', handler)
    pg = c.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://khipu.test/')
    pg.evaluate("(d) => document.body.classList.toggle('dark', d)", dark)
    for f in ['engine/mascot.js', 'engine/desktop.js', 'engine/cockpit.js'] + ['engine/%s.js' % m for m in MODULES]:
        pg.add_script_tag(content=_r(*f.split('/')))
    pg.add_script_tag(content=CONTRAST_JS)
    pg.evaluate("""() => {
      document.getElementById('lay-btn').click();
      document.getElementById('ls-btn').click();
      window.openCompare('TSMC', 'Nvidia');
      window.renderMatrixView();
      window.KhipuCrypto.init();
      window.KhipuWorld.mount(document.getElementById('wm-root'));
      window.KhipuSpace.mount(document.getElementById('sp-root'));
    }""")
    pg.wait_for_timeout(400)
    return c, pg, errs


# texto que tiene que leerse (≥ 4.5:1) en los dos temas
READABLE = ['#lay-panel .lay-row .lay-lb', '#lay-btn', '#lay-note', '#ls-panel .ls-lbl', '#ls-stats .ls-cell b',
            '#ls-stats .ls-cell span', '#cmp .cmp-row .lab', '#cmp .cmp-row .win', '#cmp .eb', '#an-matrix .mxv-s',
            '#an-matrix .mxv-mm .t', '#crypto-panel .cr-root td', '#crypto-panel .cr-root h2', '#wm-left .wm-ph',
            '#wm-left .wm-lay .nm', '#wm-left .wm-note', '#wm-right .wm-gauge .d', '#sm-left .sm-ph', '#sm-left .sm-lay .nm',
            '#sm-right .sm-ph', '#sm-tl .sm-tlh .ttl', '#live-lbl']
# superficies del HUD: claras en el tema claro, oscuras en el oscuro (antes, SIEMPRE oscuras)
SURFACES = ['#lay-panel', '#ls-panel', '#cmp', '#an-matrix .mxv-big', '#wm-left', '#wm-right', '#sm-left', '#sm-tl']


@pytest.mark.parametrize('dark', [False, True])
def test_navegador_hud_legible_y_del_tema(browser, dark):
    c, pg, errs = _page(browser, dark)
    try:
        assert not errs, errs
        themed = pg.evaluate("""() => ['#lay-btn', '#lay-panel', '#ls-panel', '#cmp-ov', '#an-matrix', '#crypto-panel .cr-root',
          '#wm', '#sm'].map(s => [s, !!document.querySelector(s) && document.querySelector(s).classList.contains('kos-themed')])""")
        assert all(t for _, t in themed), themed
        for sel in READABLE:
            ratio = pg.evaluate('(s) => window.__contrast(s)', sel)
            assert ratio is not None, 'no se pintó: ' + sel
            assert ratio >= 4.5, '%s: contraste %s en tema %s' % (sel, ratio, 'oscuro' if dark else 'claro')
        for sel in SURFACES:
            lum = pg.evaluate('(s) => window.__bgLum(s)', sel)
            assert lum is not None, sel
            assert (lum < 0.1) if dark else (lum > 0.7), '%s: luminancia de fondo %s' % (sel, lum)
        # el escenario del globo sigue oscuro a propósito (también en claro)
        stage = pg.evaluate("() => getComputedStyle(document.getElementById('wm')).backgroundImage")
        assert 'radial-gradient' in stage
    finally:
        c.close()


def test_navegador_cambio_de_idioma_re_etiqueta(browser):
    c, pg, errs = _page(browser, False)
    try:
        before = pg.evaluate("() => document.querySelector('#lay-panel .lay-row .lay-lb').textContent")
        assert before == 'Conexiones'
        pg.evaluate("() => { window.LANG = 'en'; document.documentElement.lang = 'en'; }")
        pg.wait_for_timeout(250)
        got = pg.evaluate("""() => ({
          layBtn: document.getElementById('lay-btn').textContent,
          layRow: document.querySelector('#lay-panel .lay-row .lay-lb').textContent,
          layHead: document.querySelector('#lay-panel .lay-h').textContent,
          lsBtn: document.getElementById('ls-btn').textContent,
          lsTitle: document.querySelector('#ls-panel [data-l="title"]').textContent,
          live: document.getElementById('live-lbl').textContent,
          cmp: document.querySelector('#cmp .eb').textContent,
          mxv: document.querySelector('#an-matrix .mxv-h').textContent,
          cr: (document.querySelector('#crypto-panel .cr-root button[title]') || {}).title,
          wm: document.getElementById('wm-reopen-l').textContent,
          wmLeft: document.querySelector('#wm-left .wm-ph').textContent,
          sm: document.getElementById('sm-reopen-l').textContent,
        })""")
        assert 'Layers' in got['layBtn'] and got['layRow'] == 'Links' and got['layHead'] == 'Map layers', got
        assert 'Live' in got['lsBtn'] and got['lsTitle'] == 'Live simulation', got
        assert got['live'] == 'LIVE', got
        assert got['cmp'] == 'Compare companies', got
        assert 'relationship matrices' in got['mxv'], got
        assert got['cr'] == 'Refresh', got
        assert got['wm'] == '☰ Layers' and 'Layers' in got['wmLeft'], got
        assert got['sm'] == '☰ Layers', got
        assert not errs, errs
    finally:
        c.close()
