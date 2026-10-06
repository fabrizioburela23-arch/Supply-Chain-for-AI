"""Khipus OS v1 — arreglos de la cáscara (engine/cockpit.js + engine/desktop.js) tras la revisión.

Cada prueba falla con el código anterior al arreglo y pasa con el nuevo:
  #0  la fila del saldo del menú (teléfono/tablet) llevaba un 🧪 FIJO aunque el saldo fuera de DINERO REAL;
  #1  "solo chat" (< 1100 px): lo que se preguntaba con una ventana abierta quedaba DEBAJO de la ventana;
  #2  pasar a la Cabina clásica en OTRA pestaña destruía la barra de entrada de ésta (#bcp-barwrap);
  #14 la ventana del Grafo en un flanco quedaba en blanco: la ficha de 380 px de app.html no encoge.
Dos niveles: estáticas (siempre) y navegador (Playwright + Chromium, si hay) con los módulos REALES y
una página mínima con el CSS real del mapa de app.html.
"""
import json
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COCKPIT_PATH = os.path.join(ROOT, 'engine', 'cockpit.js')
DESKTOP_PATH = os.path.join(ROOT, 'engine', 'desktop.js')
APP_PATH = os.path.join(ROOT, 'app.html')


def _r(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


def _fn(src, name):
    """Cuerpo de `function name(` hasta la siguiente función de primer nivel (2 espacios de sangría)."""
    i = src.index('  function ' + name + '(')
    j = src.find('\n  function ', i + 10)
    return src[i:j if j > 0 else len(src)]


# ─────────────────────────────── estáticas ───────────────────────────────
def test_0_insignia_del_saldo_aparte_del_texto():
    s = _r(COCKPIT_PATH)
    me = _fn(s, '_openMe')
    # la columna del ícono ya no es un 🧪 fijo: sale del estado del saldo y se repinta con él
    assert 'id="kos-me-bal-ic"' in me and "(_bal.ic || '🧪')" in me
    assert '<span class="ic">🧪</span><span class="tx" id="kos-me-bal">' not in me
    ref = _fn(s, '_balRefresh')
    assert "ic: '🔴'" in ref and "ic: '🧪'" in ref
    # el texto ya no repite la insignia (antes: "🧪  🧪 Bróker (papel)" y "🧪  🔴 Bróker (dinero real)")
    assert "plain: '🧪 '" not in ref and "plain: '🔴 '" not in ref
    paint = _fn(s, '_balPaintMenu')
    assert "getElementById('kos-me-bal-ic')" in paint and "getElementById('kos-me-bal')" in paint


def test_1_solo_chat_destapa_la_conversacion_en_cada_camino():
    s = _r(COCKPIT_PATH)
    rv = _fn(s, '_revealChat')
    assert 'isCentered()' in rv and 'D.minimize(w.id)' in rv   # solo en "solo chat"; a la barra, no cerradas
    assert "if (chatCentered()) { _revealChat();" in _fn(s, '_ensureThread')
    assert "if (kind === 'chat' && chatCentered()) { _revealChat(); _focusChat(); return; }" in _fn(s, 'stage')
    assert '_revealChat();' in _fn(s, 'invokeAgent')   # invocar a un agente (antes _askAgentPrefill) destapa el chat
    # escribir en la barra o que otro módulo la llene (oswindows.js "Pregúntale a Radar") la destapa
    assert "input.addEventListener('input', function () { _revealChat(); });" in s
    assert 'revealChat: _revealChat' in s


def test_2_modo_clasico_en_otra_pestana_no_destruye_la_barra():
    s = _r(COCKPIT_PATH)
    st = _fn(s, 'stage')
    i_guard = st.index('if (!D) _deskTeardownStale();')
    assert i_guard < st.index('restoreAdopted();   // devolver cualquier panel adoptado')   # antes del camino clásico
    td = _fn(s, '_deskTeardownStale')
    assert 'K.unmount()' in td
    assert "if (e.key === 'kh_desk_mode') _deskModeFromStorage();" in s
    assert 'onModeChange: _onDeskMode,' in s


def test_14_grafo_en_ventana_angosta_sin_la_ficha_fija():
    s = _r(COCKPIT_PATH)
    assert '#bcp-stage.kd-desk:not(.kd-mobile) .kd-body>#bcp-embed-graph{container:kosmap/inline-size}' in s
    m = re.search(r'@container kosmap \(max-width:760px\)\{(.*?)\n\}', s, re.S)
    assert m, 'falta la consulta de contenedor del grafo'
    css = m.group(1)
    assert '#bcp-embed-graph>main>.panel{position:absolute' in css
    assert '#bcp-embed-graph>main>.panel:has(>#detail[style*="none"]){display:none}' in css
    g = _fn(s, 'stageGraph')
    assert '_mapSettleSoon();' in g
    assert "window._ensureMapSettled(false)" in _fn(s, '_mapSettleSoon')
    assert '_mapSettleSoon()' in _fn(s, 'readopt')   # al reabrir la Cabina el mapa vuelve a su ventana


# ─────────────────────────────── navegador ───────────────────────────────
def _app_map_css():
    """El CSS REAL del mapa y de la ficha (app.html), para medir lo mismo que en la app."""
    a = _r(APP_PATH)
    out = []
    for pat in (r'\nmain\{[^}]*\}', r'\n\.graph-wrap\{[^}]*\}', r'\n\.panel\{[^}]*\}', r'\n\.mobile-only\{display:none\}',
                r'\n\.icon-btn\{[^}]*\}'):
        m = re.search(pat, a)
        assert m, pat
        out.append(m.group(0))
    return '\n'.join(out)


PAGE = r"""<!doctype html><html lang="es"><head><meta charset="utf-8"><style>
html,body{margin:0;height:100%;font-family:system-ui}
.app{display:flex;flex-direction:column;height:100%}
#graph{display:block;width:100%;height:100%}
%%APPCSS%%
</style></head><body class="dark">
<div class="app"><main><div class="graph-wrap"><svg id="graph"></svg><div class="legend" id="legend">leyenda</div>
<div class="graph-hint">ayuda</div></div>
<aside class="panel" id="panel"><button class="sheet-close icon-btn mobile-only" id="sheet-close">✕</button>
<div class="panel-empty" id="panel-empty">Explora la cadena de valor</div><div class="detail" id="detail" style="display:none">Nvidia</div></aside></main></div>
<script>
window.LANG = 'es';
window.NODES = []; window.NODE_BY_ID = {}; window.LINKS = [];
window.__settle = [];
window._ensureMapSettled = function () { window.__settle.push(Math.round(document.getElementById('graph').getBoundingClientRect().width)); return true; };
window.KhipuChat = { appendUser: function () {}, appendPending: function () { return document.createElement('div'); },
  send: function () { return new Promise(function () {}); }, fillReply: function () {}, fillError: function () {},
  classify: function () { return { kind: 'brain' }; }, ensureStyles: function () {}, clear: function () {},
  noteEntity: function () {}, remember: function () {} };
window.addEventListener('error', function (e) { (window.errs = window.errs || []).push(String(e.message)); });
</script></body></html>"""


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


def _ctx(browser, w, h):
    mobile = w <= 760
    c = browser.new_context(viewport={'width': w, 'height': h}, is_mobile=mobile, has_touch=mobile)
    page_html = PAGE.replace('%%APPCSS%%', _app_map_css())

    def handler(route):
        url = route.request.url
        if url.rstrip('/') == 'http://khipu.test':
            return route.fulfill(status=200, content_type='text/html', body=page_html)
        return route.fulfill(status=503, content_type='application/json', body=json.dumps({'error': 'sin servidor'}))
    c.route('http://khipu.test/**', handler)
    return c


def _page(c, cockpit_src=None):
    pg = c.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://khipu.test/')
    pg.add_script_tag(content=_r(DESKTOP_PATH))
    pg.add_script_tag(content=cockpit_src or _r(COCKPIT_PATH))
    pg.evaluate("BixbyCockpit.registerKind('tst', { icon: '▫', es: 'Prueba', en: 'Test', render: function (b) { b.innerHTML = '<p>hola</p>'; } })")
    pg.evaluate('BixbyCockpit.open()')
    pg.wait_for_timeout(250)
    return pg, errs


def _wins(pg):
    return pg.evaluate('() => KhipuDesk.list().map(w => [w.kind, w.min])')


def _input_on_top(pg):
    return pg.evaluate("""() => { const i = document.getElementById('bcp-input'); if (!i) return false;
      const r = i.getBoundingClientRect(); const el = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
      return !!(el && (el === i || (el.closest && el.closest('#bcp-barwrap')))); }""")


@pytest.mark.parametrize('paper', [False, True])
def test_navegador_0_fila_del_saldo_con_la_insignia_correcta(browser, paper):
    c = _ctx(browser, 390, 844)
    pg, errs = _page(c)
    pg.evaluate("""(paper) => { window._tradePinStored = function () { return '1234'; };
      window._tradeAccountInfo = function (i, p) { return Promise.resolve({ equity: 12345.67, paper: paper }); };
      BixbyCockpit.refreshBalance(); }""", paper)
    pg.wait_for_timeout(150)
    pg.click('#kos-me')
    pg.wait_for_timeout(150)
    ic, tx = pg.evaluate("() => { const b = document.querySelector('.kos-mi[data-k=bal]'); return [b.querySelector('.ic').textContent, b.querySelector('.tx').textContent]; }")
    assert ic == ('🧪' if paper else '🔴'), (ic, tx)          # antes: 🧪 junto a un saldo de DINERO REAL
    assert '12.345,67' in tx and '🧪' not in tx and '🔴' not in tx   # la insignia una sola vez (antes "🧪 🧪")
    # un refresco con el menú abierto repinta texto E insignia juntos
    pg.evaluate("""(paper) => { window._tradeAccountInfo = function () { return Promise.resolve({ equity: 1, paper: !paper }); };
      BixbyCockpit.refreshBalance(); }""", paper)
    pg.wait_for_timeout(150)
    assert pg.evaluate("() => document.getElementById('kos-me-bal-ic').textContent") == ('🔴' if paper else '🧪')
    assert not errs, errs
    c.close()


@pytest.mark.parametrize('w,h', [(900, 1000), (390, 844)])
def test_navegador_1_solo_chat_la_respuesta_no_queda_bajo_una_ventana(browser, w, h):
    c = _ctx(browser, w, h)
    pg, errs = _page(c)
    assert pg.evaluate('KhipuDesk.isSolo()') is True
    # 1) "Pregúntale a Radar" (oswindows.js): llena la barra, dispara 'input' y la enfoca
    pg.evaluate("BixbyCockpit.stage('tst')")
    pg.wait_for_timeout(150)
    assert _wins(pg) == [['tst', False]] and not _input_on_top(pg)
    pg.evaluate("""() => { const i = document.getElementById('bcp-input'); i.value = '@noticias ';
      i.dispatchEvent(new Event('input', { bubbles: true })); i.focus(); }""")
    pg.wait_for_timeout(150)
    assert _wins(pg) == [['tst', True]], 'la ventana sigue tapando la barra'
    assert _input_on_top(pg)
    # 2) stage('chat') (💬 / command_center)
    pg.evaluate("BixbyCockpit.stage('tst')")
    pg.wait_for_timeout(150)
    assert _wins(pg) == [['tst', False]]
    pg.evaluate("BixbyCockpit.stage('chat')")
    pg.wait_for_timeout(150)
    assert _wins(pg) == [['tst', True]] and _input_on_top(pg)
    # 3) una pregunta (chatAsk → _ensureThread): la respuesta se ve
    pg.evaluate("BixbyCockpit.stage('tst')")
    pg.wait_for_timeout(150)
    pg.evaluate("BixbyCockpit.chat('¿Cómo está Nvidia?')")
    pg.wait_for_timeout(150)
    assert _wins(pg) == [['tst', True]] and _input_on_top(pg)
    # la ventana NO se pierde: su chip de la barra de tareas la devuelve
    pg.click('.kd-task')
    pg.wait_for_timeout(150)
    assert _wins(pg) == [['tst', False]]
    assert not errs, errs
    c.close()


def test_navegador_1_con_el_chat_al_centro_escribir_no_toca_las_ventanas(browser):
    c = _ctx(browser, 1440, 900)
    pg, errs = _page(c)
    assert pg.evaluate('BixbyCockpit.isCentered()') is True
    pg.evaluate("BixbyCockpit.stage('tst')")
    pg.wait_for_timeout(150)
    pg.evaluate("""() => { const i = document.getElementById('bcp-input'); i.value = 'hola';
      i.dispatchEvent(new Event('input', { bubbles: true })); }""")
    pg.evaluate("BixbyCockpit.chat('hola')")
    pg.wait_for_timeout(150)
    assert _wins(pg) == [['tst', False]]          # en flancos la ventana nunca tapa el chat: se queda
    assert not errs, errs
    c.close()


def test_navegador_2_modo_clasico_en_otra_pestana_conserva_la_barra(browser):
    c = _ctx(browser, 1440, 900)
    pg, errs = _page(c)
    assert pg.evaluate("!!document.querySelector('#kd-center #bcp-barwrap')")
    # la otra pestaña escribió kh_desk_mode='off' (en ESTA no llega ningún evento): la próxima escena
    pg.evaluate("localStorage.setItem('kh_desk_mode', 'off')")
    pg.evaluate("BixbyCockpit.stage('chat')")
    pg.wait_for_timeout(150)
    st = pg.evaluate("""() => ({ bw: !!document.querySelector('#bcp-ov #bcp-barwrap'), inp: !!document.getElementById('bcp-input'),
      active: KhipuDesk.active(), classic: document.getElementById('bcp-ov').classList.contains('kos-classic') })""")
    assert st == {'bw': True, 'inp': True, 'active': False, 'classic': True}, st
    # y la vuelta al modo ventanas encuentra la barra (antes: getElementById('bcp-barwrap') === null para siempre)
    pg.evaluate("localStorage.setItem('kh_desk_mode', 'on')")
    pg.evaluate("BixbyCockpit.stage('empty')")
    pg.wait_for_timeout(150)
    assert pg.evaluate("!!document.querySelector('#kd-center #bcp-barwrap')")
    assert not errs, errs
    c.close()


def test_navegador_2_el_evento_storage_sigue_el_modo_de_la_otra_pestana(browser):
    c = _ctx(browser, 1440, 900)
    pg, errs = _page(c)
    pg.evaluate("BixbyCockpit.stage('tst')")
    pg.evaluate("""() => { localStorage.setItem('kh_desk_mode', 'off');
      window.dispatchEvent(new StorageEvent('storage', { key: 'kh_desk_mode', oldValue: 'on', newValue: 'off' })); }""")
    pg.wait_for_timeout(150)
    st = pg.evaluate("""() => ({ active: KhipuDesk.active(), bw: !!document.querySelector('#bcp-ov #bcp-barwrap'),
      classic: document.getElementById('bcp-ov').classList.contains('kos-classic') })""")
    assert st == {'active': False, 'bw': True, 'classic': True}, st
    pg.evaluate("""() => { localStorage.setItem('kh_desk_mode', 'on');
      window.dispatchEvent(new StorageEvent('storage', { key: 'kh_desk_mode', oldValue: 'off', newValue: 'on' })); }""")
    pg.wait_for_timeout(150)
    assert pg.evaluate('KhipuDesk.active()') is True
    assert pg.evaluate("!!document.querySelector('#kd-center #bcp-barwrap')")
    assert not errs, errs
    c.close()


@pytest.mark.parametrize('w,h', [(1280, 800), (1440, 900)])
def test_navegador_14_grafo_en_un_flanco_tiene_mapa(browser, w, h):
    c = _ctx(browser, w, h)
    pg, errs = _page(c)
    assert pg.evaluate('BixbyCockpit.isCentered()') is True
    pg.evaluate("BixbyCockpit.stage('graph')")
    pg.wait_for_timeout(400)
    m = pg.evaluate("""() => { const win = document.querySelector('.kd-win[data-kind=graph]').getBoundingClientRect();
      const s = document.getElementById('graph').getBoundingClientRect(); const p = document.getElementById('panel');
      return { win: Math.round(win.width), svg: Math.round(s.width), panel: getComputedStyle(p).display,
               legend: getComputedStyle(document.getElementById('legend')).display }; }""")
    assert m['win'] <= 760
    assert m['svg'] >= m['win'] - 4, m          # antes: svg = ventana − 380 px (0 px a 1280, 36 px a 1440)
    assert m['panel'] == 'none' and m['legend'] == 'none', m   # sin empresa elegida la ficha no ocupa nada
    # la Cabina pide asentar el mapa tras mudarlo, ya con ancho real
    settle = pg.evaluate('window.__settle')
    assert settle and max(settle) >= m['win'] - 4, settle
    # con una empresa elegida, la ficha es una hoja ENCIMA del mapa (no le quita ancho) y ✕ se ve
    pg.evaluate("document.getElementById('detail').style.display = 'block'")
    d = pg.evaluate("""() => { const p = document.getElementById('panel'), r = p.getBoundingClientRect(), cs = getComputedStyle(p);
      return { pos: cs.position, disp: cs.display, h: Math.round(r.height), svg: Math.round(document.getElementById('graph').getBoundingClientRect().width),
               x: getComputedStyle(document.getElementById('sheet-close')).display,
               wh: Math.round(document.querySelector('.kd-win[data-kind=graph] .kd-body').getBoundingClientRect().height) }; }""")
    assert d['pos'] == 'absolute' and d['disp'] == 'block' and d['x'] == 'flex', d
    assert d['svg'] == m['svg'] and d['h'] < d['wh'] * 0.6, d
    assert not errs, errs
    c.close()


def test_navegador_14_ventana_ancha_y_cabina_clasica_sin_cambios(browser):
    # ventana ancha (flanco de 912 px a 2560): la ficha sigue en la fila, como antes
    c = _ctx(browser, 2560, 1100)
    pg, errs = _page(c)
    pg.evaluate("BixbyCockpit.stage('graph')")
    pg.wait_for_timeout(300)
    m = pg.evaluate("""() => { const p = document.getElementById('panel'); return { pos: getComputedStyle(p).position,
      pw: Math.round(p.getBoundingClientRect().width), svg: Math.round(document.getElementById('graph').getBoundingClientRect().width) }; }""")
    assert m['pos'] == 'static' and m['pw'] >= 380 and m['svg'] > 400, m   # 380 px + borde
    c.close()
    # Cabina clásica (kh_desk_mode=off desde el arranque): igual que siempre
    c = _ctx(browser, 1280, 800)
    c.add_init_script("try { localStorage.setItem('kh_desk_mode', 'off'); } catch (e) {}")
    pg, errs2 = _page(c)
    pg.evaluate("BixbyCockpit.stage('graph')")
    pg.wait_for_timeout(300)
    m2 = pg.evaluate("""() => ({ desk: KhipuDesk.active(), pos: getComputedStyle(document.getElementById('panel')).position,
      pw: Math.round(document.getElementById('panel').getBoundingClientRect().width) })""")
    assert m2['desk'] is False and m2['pos'] == 'static' and m2['pw'] >= 380, m2
    assert not errs and not errs2, (errs, errs2)
    c.close()
