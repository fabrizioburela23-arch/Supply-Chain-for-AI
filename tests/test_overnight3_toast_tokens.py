"""Overnight 3 (2026-10-10) — avisos/confirmaciones (engine/toast.js), cargadores (engine/loading.js) y el rótulo
«cat.» del X-Ray (engine/xray.js) entran a Khipus OS.

Antes:
  · toast.js era SIEMPRE oscuro (#11151D / #E8EAF0…), también en el tema claro.
  · loading.js fijaba tintas oscuras (#7C87A3 / #E8EDFB / neón); solo la Cabina las corregía dentro de #bcp-ov.
  · el X-Ray pintaba el rótulo «cat.» (capitalización del catálogo) con var(--ink-3) de la piel vieja
    (rgba(27,23,20,.4) ≈ 2.5:1).
Ahora:
  · #kht-stack y #khm-ov llevan .kos-themed → tokens --os-* de engine/cockpit.js (claro = body sin .dark,
    oscuro = body.dark), siempre var(--token, respaldo-oscuro).
  · Insignias de dinero intactas: 🔴 DINERO REAL = píldora roja SÓLIDA con texto blanco (≥ 4.5:1 en ambos temas);
    🧪 SIMULADO = tinta ámbar sobre tinte ámbar (≥ 4.5:1).
  · confirmOrder resuelve true/false EXACTAMENTE como antes (Confirmar / Cancelar / ✕ / Esc / fondo / casilla de
    DINERO REAL / «sí» por voz que la reemplaza), con el foco en el diálogo (un Enter suelto nunca envía dinero).
"""
import json
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _r(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8') as f:
        return f.read()


TOAST = _r('engine', 'toast.js')
LOADING = _r('engine', 'loading.js')
XRAY = _r('engine', 'xray.js')
COCKPIT = _r('engine', 'cockpit.js')
HTML = _r('app.html')


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


def _css_array(src):
    a = src.index('var CSS = [')
    return src[a:src.index("].join('\\n');", a)]


def _supports_blocks(css):
    out = []
    for m in re.finditer(r'@supports[^{]*\{', css):
        depth, j = 1, m.end()
        while depth:
            depth += {'{': 1, '}': -1}.get(css[j], 0)
            j += 1
        out.append(css[m.end():j - 1])
    return out


COLOR_RE = r'#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|rgba?\([^)]*\)'

# piel oscura vieja de toast.js (fondos, tintas, bordes, violeta/verde/rojo neón, letra mono)
TOAST_LEGACY = ['#11151D', '#E8EAF0', '#F3F4F8', '#A9AFBE', '#7D8496', '#9097A8', '#F5F6FA', '#B7BDCB', '#D5D9E3',
                '#FFB3BD', '#FF6B7D', '#6E6FE0', '#A5A6FF', '#7C8CFF', '#8B8CF6', '#2EBD85', '#F6465D', '#FFB300',
                '#1F9D6C', '#D63A50', '#F0A92E', 'rgba(3,6,12', 'rgba(255,255,255', 'rgba(0,0,0', 'rgba(246,70,93',
                'rgba(46,189,133', 'rgba(255,179,0', 'rgba(139,140,246', 'JetBrains']


# ── estático: toast.js ──────────────────────────────────────────────────────────────────────────────────
def test_toast_sin_piel_oscura_fuera_de_var():
    rest = _strip_var_fallbacks(TOAST)
    low = rest.lower()
    for c in TOAST_LEGACY:
        assert c.lower() not in low, 'color/letra fijo de la piel vieja fuera de var(): ' + c
    # fuera de var() solo quedan los colores de DINERO (iguales en ambos temas): rojo sólido, verde del botón y blanco
    found = set(re.findall(COLOR_RE, rest))
    assert found <= {'#c42b2b', '#15803D', '#fff'}, sorted(found - {'#c42b2b', '#15803D', '#fff'})


def test_toast_contenedores_llevan_kos_themed():
    assert "s.id = 'kht-stack';\n      s.className = 'kos-themed';" in TOAST
    assert "ov.id = 'khm-ov';\n    ov.className = 'kos-themed';" in TOAST
    # el tema lo resuelve cockpit.js (claro = body sin .dark, oscuro = body.dark)
    assert 'body:not(.dark) .kos-themed' in COCKPIT and 'body.dark .kos-themed' in COCKPIT


def test_toast_cada_token_existe_en_cockpit():
    used = set(re.findall(r'var\((--(?:os|kos)-[a-z0-9-]+)', TOAST))
    assert {'--os-surface', '--os-ink', '--os-ink-2', '--os-good-ink', '--os-bad-ink', '--os-warn-ink', '--os-warn'} <= used
    for tok in used:
        assert tok + ':' in COCKPIT, 'toast.js usa %s y cockpit.js no lo define' % tok


def test_toast_insignias_de_dinero_intactas():
    css = _css_array(TOAST)
    live = re.search(r"\.kht-mode\.live\{([^}]*)\}", css).group(1)
    assert 'color:#fff' in live and 'background:#c42b2b' in live            # píldora roja SÓLIDA, texto blanco
    paper = re.search(r"\.kht-mode\.paper\{([^}]*)\}", css).group(1)
    assert 'color:var(--os-warn-ink' in paper and 'var(--os-warn,' in paper  # ámbar sobre ámbar
    assert ".kht-mode.paper{background:color-mix(in srgb,var(--os-warn,#F2C46D) 20%,transparent)}'" in css
    # el marcado y los textos de la insignia no cambian
    assert "'<span class=\"kht-mode ' + (m === 'live' ? 'live' : 'paper') + '\">'" in TOAST
    for s in ("L('🔴 DINERO REAL', '🔴 REAL MONEY')", "L('🧪 SIMULADO', '🧪 SIMULATED')",
              "L('Entiendo que esta orden usa DINERO REAL.', 'I understand this order uses REAL MONEY.')",
              "L('Confirmar compra', 'Confirm buy')", "L('Confirmar venta', 'Confirm sell')", "L('Cancelar', 'Cancel')"):
        assert s in TOAST, s
    # botón Confirmar: verde/rojo SÓLIDO con texto blanco (≥ 4.5:1 en ambos temas)
    assert "'.khm-ok.buy{color:#fff;background:#15803D}.khm-ok.sell{color:#fff;background:#c42b2b}'" in css


def test_toast_color_mix_solo_dentro_de_supports():
    css = re.sub(r'/\*.*?\*/', '', _css_array(TOAST), flags=re.S)      # sin comentarios
    blocks = _supports_blocks(css)
    assert blocks and all('color-mix' in b for b in blocks)
    outside = css
    for b in blocks:
        outside = outside.replace(b, '')
    outside = re.sub(r'@supports[^{]*\{', '', outside)                    # y la condición del @supports
    assert 'color-mix' not in outside
    # los style="" que arma el JS no usan color-mix (con var() no hay respaldo posible)
    js = TOAST.replace(_css_array(TOAST), '')
    js = re.sub(r'/\*.*?\*/', '', js, flags=re.S)
    assert 'color-mix' not in re.sub(r'(?m)//.*$', '', js)


def test_toast_api_publica_igual():
    m = re.search(r'window\.KhipuToast = \{(.*?)\n  \};', TOAST, re.S)
    assert m
    body = re.sub(r'\s+', ' ', m.group(1)).strip()
    assert body == ('__v: 1, show: show, update: update, dismiss: dismiss, clear: clear, confirm: confirmDlg, '
                    'confirmOrder: confirmOrder, modeLabel: modeLabel, modeBadge: modeBadge, order: { confirm: confirmOrder, '
                    'sending: sending, result: result, watch: watch, filled: filled, key: orderKey, resolveMode: resolveMode },')
    # foco y temporizadores tal cual
    for s in ("try { ov.querySelector('.khm').focus(); } catch (e) {}", "if (prevFocus && prevFocus.focus && document.contains(prevFocus)) prevFocus.focus();",
              "el.addEventListener('mouseenter', function () { pause(it); });", "el.addEventListener('focusin', function () { pause(it); });",
              "var DEF_TIMEOUT = { info: 5000, success: 6500, buy: 7000, sell: 7000, warn: 9000, error: 12000 };",
              "var POLL_AT = [2500, 5000, 9000, 14000, 20000, 28000, 38000, 48000, 60000];",
              "if (_dlg && _dlg.key && _dlg.key === orderKey(o)) _dlg.close(false, 'superseded');",
              "if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close(false); return; }"):
        assert s in TOAST, s


# ── estático: loading.js ────────────────────────────────────────────────────────────────────────────────
def test_loading_sin_tintas_oscuras_fijas():
    rest = _strip_var_fallbacks(LOADING)
    for c in ('#7C87A3', '#AEB8D6', '#E8EDFB', '#00E0FF', '#8e5aff', '#3DE0C8', 'rgba(122,158,255', 'NEON', 'TEAL', 'VIO'):
        assert c.lower() not in rest.lower(), c
    assert not re.findall(COLOR_RE, rest), re.findall(COLOR_RE, rest)
    # ningún style="" con color: las tintas viven en clases tematizadas
    assert 'color:#' not in LOADING
    # Khipus OS primero, luego el tema de app.html, luego el respaldo oscuro
    assert "'var(--os-ink-2,var(--ink-2,#A6A8B5))'" in LOADING and "'var(--os-ink,var(--ink,#F2F2F5))'" in LOADING
    assert 'prefers-reduced-motion' in LOADING
    for tok in set(re.findall(r'var\((--(?:os|kos)-[a-z0-9-]+)', LOADING)):
        assert tok + ':' in COCKPIT, tok


def test_loading_api_igual():
    assert 'window.KhipuLoading = { spinner: spinner, dots: dots, skeleton: skeleton, staged: staged, _ensureCSS: ensureCSS };' in LOADING
    for frag in ("'khl-css'", 'class="khl-spin"', 'class="khl-sk"', 'class="khl-staged"', 'class="khl-orb"', 'id="khl-sub"',
                 'id="khl-steps"', 'class="khl-step"', 'return { stop: function () { clearInterval(iv); } };'):
        assert frag in LOADING, frag


# ── estático: xray.js ───────────────────────────────────────────────────────────────────────────────────
def test_xray_puente_rotulo_cat():
    assert '.xray-scope span[style*="var(--ink-3)"]{color:var(--os-ink-2,#A6A8B5)!important' in XRAY
    # liveCapDot (app.html) sigue pintando «cat.» con var(--ink-3): el puente lo alcanza
    assert "<span style=\"color:var(--ink-3);font-size:9px" in HTML and "'cat.'" in HTML


# ── navegador ───────────────────────────────────────────────────────────────────────────────────────────
APP_TOKENS = re.search(r':root\{\s*/\*[^*]*\*/\s*(--bg:[^}]*?--accent:#6D28D9;)', HTML).group(1)
APP_DARK = re.search(r'\.dark\{\s*/\*[^*]*\*/\s*(--bg:#15120C;[^}]*?--accent:#A78BFA;)', HTML).group(1)
_a = HTML.index('window.liveCapDot = function(meta){')
LIVECAPDOT = HTML[_a:HTML.index('\n};', _a) + 3]

PAGE = r"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<style>html,body{margin:0;height:100%;font-family:system-ui}body{background:#EDEDF5}body.dark{background:#0E0F14}
:root{@@ROOT@@}.dark{@@DARK@@}</style></head><body><button id="opener">abrir</button>
<script>
window.LANG = 'es';
window.esc = function (s) { return String(s == null ? '' : s); };
window.NODES = [{ id: 'Nvidia', label: 'Nvidia', mkt: 'NVDA', cat: 'gpu', country: 'USA', margin: 0.6, growth: '+50%' }];
window.NODE_BY_ID = { Nvidia: window.NODES[0] }; window.LINKS = []; window.SECTORS9 = {}; window.CAT_TO_SECTOR = {};
window.NODE_META = { Nvidia: { founded: 1993, employees: 36000, mktcap_b: 4400 } };
window.computeNRS = function () { return 40; };
window.computeNRSBreakdown = function () { return { total: 40, terms: [{ key: 'Cadena', detail: 'grado 2', val: 20, max: 25 }] }; };
</script></body></html>""".replace('@@ROOT@@', APP_TOKENS).replace('@@DARK@@', APP_DARK)

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
  var acc = [255, 255, 255, 1];
  for (var i = layers.length - 1; i >= 0; i--) acc = __over(layers[i], acc);
  return acc;
};
window.__lum = function (c) {
  var f = function (v) { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]);
};
window.__contrast = function (el) {
  if (typeof el === 'string') el = document.querySelector(el);
  if (!el) return null;
  var bg = __bg(el), fg = __parse(getComputedStyle(el).color);
  if (fg[3] < 1) fg = __over(fg, bg);
  var a = __lum(fg), b = __lum(bg);
  return Math.round((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05) * 100) / 100;
};
"""


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


def _page(browser, w=1440, h=900, dark=False, with_os=True, extra=()):
    c = browser.new_context(viewport={'width': w, 'height': h}, service_workers='block')

    def handler(route):
        path = route.request.url[len('http://khipu.test'):].split('?')[0]
        if path in ('', '/'):
            return route.fulfill(status=200, content_type='text/html', body=PAGE)
        return route.fulfill(status=503, content_type='application/json', body='{"error":"sin servidor"}')
    c.route('http://khipu.test/**', handler)
    pg = c.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://khipu.test/')
    pg.evaluate("(d) => document.body.classList.toggle('dark', d)", dark)
    files = (['engine/mascot.js', 'engine/desktop.js', 'engine/cockpit.js'] if with_os else []) + \
        ['engine/loading.js', 'engine/toast.js'] + list(extra)
    for f in files:
        pg.add_script_tag(content=_r(*f.split('/')))
    pg.add_script_tag(content=CONTRAST_JS)
    return c, pg, errs


# confirmOrder: cada camino resuelve EXACTAMENTE como antes
_FLOW = r"""async (kind) => {
  const T = window.KhipuToast, opener = document.getElementById('opener');
  opener.focus();
  const order = kind === 'live'
    ? { symbol: 'NVDA', side: 'sell', qty: 3, price: 181.2, mode: 'live', tif: 'gtc' }
    : { symbol: 'NVDA', label: 'Nvidia', side: 'buy', notional: 500, mode: 'paper', tif: 'day' };
  const out = {};
  const run = async (act) => {
    let h = null;   // el diálogo (con .reason / .close) llega por onHandle, como lo usan la Cabina y el panel
    const p = T.confirmOrder(Object.assign({}, order), Object.assign(kind === 'paper' ? { amounts: [100, 500, 1000] } : {},
      { onHandle: x => { h = x; } }));
    await new Promise(r => setTimeout(r, 30));
    const ov = document.getElementById('khm-ov'), box = ov && ov.querySelector('.khm');
    const st = { themed: ov.classList.contains('kos-themed'), focusDlg: document.activeElement === box,
      badge: ov.querySelector('.kht-mode') ? ov.querySelector('.kht-mode').className : null,
      okDisabled: ov.querySelector('.khm-ok').disabled };
    await act(ov);
    const hp = await Promise.race([p.then(x => ({ v: x })), new Promise(r => setTimeout(() => r({ pending: true }), 120))]);
    st.result = hp.pending ? 'pending' : hp.v;
    st.reason = h.reason || null;
    st.closed = !document.getElementById('khm-ov');
    st.focusBack = document.activeElement === opener;
    if (hp.pending) { h.close('dismissed'); st.after = await p; st.reason2 = h.reason; }
    return st;
  };
  out.confirm = await run(async ov => {
    if (kind === 'live') ov.querySelector('#khm-ck').click();
    ov.querySelector('.khm-ok').click();
  });
  out.cancel = await run(async ov => ov.querySelector('.khm-cancel').click());
  out.x = await run(async ov => ov.querySelector('.khm-x').click());
  out.esc = await run(async ov => document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })));
  out.backdrop = await run(async ov => ov.dispatchEvent(new MouseEvent('mousedown', { bubbles: true })));
  out.enter = await run(async ov => document.activeElement.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })));
  out.okWithoutCheck = await run(async ov => ov.querySelector('.khm-ok').click());
  // el «sí» por voz de la MISMA orden cierra el diálogo como 'superseded' (false) y el aviso de envío toma el relevo
  out.voice = await run(async ov => { T.order.sending(Object.assign({}, order)); });
  T.clear();
  return out;
}"""


@pytest.mark.parametrize('dark', [False, True])
@pytest.mark.parametrize('kind', ['paper', 'live'])
def test_navegador_confirm_order_resuelve_igual(browser, kind, dark):
    c, pg, errs = _page(browser, dark=dark)
    r = pg.evaluate(_FLOW, kind)
    for k, st in r.items():
        assert st['themed'] and st['focusDlg'], (k, st)                   # foco en el diálogo, no en Confirmar
        assert st['badge'] == 'kht-mode ' + ('live' if kind == 'live' else 'paper'), (k, st)
        assert st['okDisabled'] is (kind == 'live'), (k, st)               # DINERO REAL: casilla obligatoria
    assert r['confirm']['result'] is True and r['confirm']['reason'] == 'confirm' and r['confirm']['closed']
    for k in ('cancel', 'x', 'esc', 'backdrop'):
        assert r[k]['result'] is False and r[k]['reason'] == 'cancel' and r[k]['closed'], (k, r[k])
        assert r[k]['focusBack'], (k, r[k])                                # el foco vuelve a quien lo abrió
    # Enter suelto: NO confirma (sigue abierto hasta que se cierra a mano)
    assert r['enter']['result'] == 'pending' and r['enter']['after'] is False and r['enter']['reason2'] == 'dismissed'
    if kind == 'live':                                                     # sin la casilla, Confirmar no hace nada
        assert r['okWithoutCheck']['result'] == 'pending' and r['okWithoutCheck']['after'] is False
    else:
        assert r['okWithoutCheck']['result'] is True
    assert r['voice']['result'] is False and r['voice']['reason'] == 'superseded'
    assert not errs, errs
    c.close()


_CONTRAST = r"""() => {
  const T = window.KhipuToast;
  T.show({ kind: 'info', title: 'Vista clásica', body: 'Puedes volver desde el menú.', timeout: 0 });
  T.show({ kind: 'success', title: 'Compra ejecutada ✓', mode: 'paper', html: '<span class="kht-num">3</span> <b>NVDA</b>', timeout: 0 });
  T.show({ kind: 'error', title: 'La compra no se envió', mode: 'live', body: 'PIN incorrecto.', timeout: 0 });
  T.show({ kind: 'warn', title: 'No se envió dos veces', body: 'Esa misma orden ya se envió.', timeout: 0 });
  const q = s => [...document.querySelectorAll(s)];
  const out = {
    stackThemed: document.getElementById('kht-stack').classList.contains('kos-themed'),
    toastBgLum: __lum(__bg(document.querySelector('.kht'))),
    title: Math.min(...q('.kht-title').map(__contrast)), body: Math.min(...q('.kht-body').map(__contrast)),
    ico: Math.min(...q('.kht-ico').map(__contrast)), x: Math.min(...q('.kht-x').map(__contrast)),
    live: __contrast('#kht-stack .kht-mode.live'), paper: __contrast('#kht-stack .kht-mode.paper'),
    liveBg: getComputedStyle(document.querySelector('#kht-stack .kht-mode.live')).backgroundColor,
    liveFg: getComputedStyle(document.querySelector('#kht-stack .kht-mode.live')).color,
  };
  T.clear();
  return out;
}"""
_CONTRAST_DLG = r"""async (kind) => {
  const T = window.KhipuToast;
  let h = null;
  const p = T.confirmOrder(kind === 'live' ? { symbol: 'NVDA', side: 'sell', qty: 3, price: 181.2, mode: 'live', tif: 'gtc' }
                                           : { symbol: 'NVDA', side: 'buy', notional: 500, mode: 'paper' },
                           { amounts: [100, 500], onHandle: x => { h = x; } });
  await new Promise(r => setTimeout(r, 30));
  const q = s => [...document.querySelectorAll('#khm-ov ' + s)];
  const ck = document.getElementById('khm-ck'); if (ck) ck.click();
  const out = {
    boxBgLum: __lum(__bg(document.querySelector('.khm'))),
    title: __contrast('.khm-title'), sub: __contrast('.khm-sub'),
    dt: Math.min(...q('.khm-rows dt').map(__contrast)), dd: Math.min(...q('.khm-rows dd').map(__contrast)),
    side: __contrast('.khm-side'), badge: __contrast('#khm-ov .kht-mode'), ok: __contrast('.khm-ok'), cancel: __contrast('.khm-cancel'),
    note: __contrast('.khm-note'), total: __contrast('.khm-total b'),
    warn: q('.khm-warn').length ? __contrast('.khm-warn') : null, warnB: q('.khm-warn b').length ? __contrast('.khm-warn b') : null,
    chip: q('.khm-chips button[aria-pressed="true"]').length ? __contrast('.khm-chips button[aria-pressed="true"]') : null,
    chipOff: q('.khm-chips button[aria-pressed="false"]').length ? __contrast('.khm-chips button[aria-pressed="false"]') : null,
  };
  h.close('dismissed'); await p;
  return out;
}"""


@pytest.mark.parametrize('w,h', [(1440, 900), (390, 844)])
@pytest.mark.parametrize('dark', [False, True])
def test_navegador_contraste_avisos_y_dialogo(browser, dark, w, h):
    c, pg, errs = _page(browser, w, h, dark=dark)
    t = pg.evaluate(_CONTRAST)
    assert t['stackThemed']
    # el tema manda: claro = tarjeta clara (antes SIEMPRE oscura), oscuro = tarjeta oscura
    assert (t['toastBgLum'] < 0.05) if dark else (t['toastBgLum'] > 0.85), t
    for k in ('title', 'body', 'ico', 'x', 'live', 'paper'):
        assert t[k] >= 4.5, (k, t)
    # 🔴 DINERO REAL: píldora ROJA SÓLIDA, texto blanco, en ambos temas
    assert t['liveBg'] == 'rgb(196, 43, 43)' and t['liveFg'] == 'rgb(255, 255, 255)', t
    for kind in ('paper', 'live'):
        d = pg.evaluate(_CONTRAST_DLG, kind)
        assert (d['boxBgLum'] < 0.05) if dark else (d['boxBgLum'] > 0.85), d
        for k, v in d.items():
            if k != 'boxBgLum' and v is not None:
                assert v >= 4.5, (kind, k, d)
    assert not errs, errs
    c.close()


def test_navegador_sin_cockpit_queda_oscuro_como_antes(browser):
    # sin cockpit.js (sin tokens) los respaldos dan el aspecto oscuro de siempre, también con body claro
    c, pg, errs = _page(browser, with_os=False)
    t = pg.evaluate(_CONTRAST)
    assert t['toastBgLum'] < 0.05, t
    for k in ('title', 'body', 'live', 'paper'):
        assert t[k] >= 4.5, (k, t)
    assert not errs, errs
    c.close()


_LOADERS = r"""(where) => {
  const host = document.createElement('div');
  if (where === 'os') { host.className = 'kos-themed'; host.style.background = 'var(--os-surface)'; }
  else host.style.background = 'var(--surface)';            // vista clásica: tokens de app.html, sin .kos-themed
  host.style.padding = '12px';
  document.body.appendChild(host);
  host.innerHTML = '<div id="st"></div>' + KhipuLoading.spinner({ label: 'Cargando precios…' }) + KhipuLoading.dots('Pensando') +
    KhipuLoading.skeleton({ lines: 2 });
  const h = KhipuLoading.staged(host.querySelector('#st'), { title: 'Investigación profunda', accent: '#9f60e5', cycle: 40,
    steps: ['Mapeando el sector', 'Competidores', 'Exposición geopolítica'] });
  return new Promise(res => setTimeout(() => {   // 300 ms de pasos + 450 ms para que termine la transición de color
    h.stop();
    const st = getComputedStyle(host.querySelector('.khl-step'));
    res({ title: __contrast(host.querySelector('.khl-title')), sub: __contrast(host.querySelector('.khl-sub')),
      steps: Math.min(...[...host.querySelectorAll('.khl-step')].map(__contrast)),
      spinLabel: __contrast(host.querySelector('.khl-inl')), dots: __contrast(host.querySelector('.khl-dots')),
      stepColor: st.color, orbShadow: getComputedStyle(host.querySelector('.khl-orb')).boxShadow,
      doneIc: getComputedStyle(host.querySelector('.khl-step.done .ic')).color });
  }, 750));
}"""


@pytest.mark.parametrize('dark', [False, True])
def test_navegador_cargadores_legibles_en_cualquier_lado(browser, dark):
    c, pg, errs = _page(browser, dark=dark)
    os_ = pg.evaluate(_LOADERS, 'os')
    for k in ('title', 'sub', 'steps', 'spinLabel', 'dots'):
        assert os_[k] >= 4.5, ('os', k, os_)
    assert 'rgba(159, 96, 229, 0.4)' in os_['orbShadow']                  # el brillo del orbe de quien llama se respeta
    classic = pg.evaluate(_LOADERS, 'classic')
    # vista clásica: la tinta sale del tema de app.html (antes: #7C87A3 fijo, ilegible en claro)
    assert classic['stepColor'] == ('rgb(182, 172, 151)' if dark else 'rgba(27, 23, 20, 0.6)'), classic
    for k in ('title', 'steps', 'spinLabel'):
        assert classic[k] >= 4.2, ('classic', k, classic)
    assert not errs, errs
    c.close()


@pytest.mark.parametrize('dark', [False, True])
def test_navegador_xray_rotulo_cat_legible(browser, dark):
    c, pg, errs = _page(browser, dark=dark, extra=('engine/xray.js',))
    pg.add_script_tag(content=LIVECAPDOT)
    pg.evaluate("() => window.openXRay('Nvidia')")
    pg.wait_for_timeout(200)
    r = pg.evaluate("""() => { const s = document.querySelector('#xray .xr-mcap span[style*="--ink-3"]');
      return s ? { txt: s.textContent, c: __contrast(s), col: getComputedStyle(s).color } : null; }""")
    assert r and r['txt'] == 'cat.', r
    assert r['c'] >= 4.5, r                                                 # antes ≈ 2.5:1 en claro
    # también en el modo escenario (ventana de Khipus OS: fondo --os-surface)
    r2 = pg.evaluate("""() => { const w = document.createElement('div'); w.className = 'kos-themed';
      w.style.background = 'var(--os-surface)'; document.body.appendChild(w);
      w.innerHTML = '<div class="xray-scope xr-full">' + window.buildXRayHTML('Nvidia', { full: true }) + '</div>';
      const s = w.querySelector('.xr-mcap span[style*="--ink-3"]'); return s ? __contrast(s) : null; }""")
    assert r2 and r2 >= 4.5, r2
    c.close()
