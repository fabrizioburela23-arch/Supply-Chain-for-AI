"""tests/test_genui_browser.py — RESPUESTAS VISUALES (kblocks/1), fase F2, en Chromium REAL (docs/CHAT_UI_GENERATIVA.md §10.1).

La página lleva la CSP REAL del servidor (server.CONTENT_SECURITY_POLICY) y los scripts reales del repo servidos como
archivos (mismo origen). Se abre Khipus OS (la Cabina) y cada respuesta entra por el camino de siempre:
KhipuChat.appendUser → appendPending → fillReply(d) con d.ui (las 4 preguntas del prototipo, ES y EN, cifras de MUESTRA).
  · 4 preguntas × {1440, 390} × {claro, oscuro} × {ES, EN}: 0 errores de página, 0 violaciones de CSP, sin
    desplazamiento horizontal a 390, cada gráfico role=img con aria-label, anuncio role=status, textos del idioma;
  · reducir movimiento: todo visible en t = 0 y ninguna animación dentro de los bloques; sin reducir: termina igual
    (cifras finales, línea dibujada) y no queda nada animándose en bucle;
  · 📌 abre una ventana `genui` con el mismo gráfico; el mini-grafo se fija en su ventana nativa (supplychain);
  · sin la bandera kh_genui el chat se ve como hoy; el interruptor del menú del avatar la cambia;
  · cambiar ES/EN repinta los bloques visibles; los 3 sobres de examples.kblocks.json (con esqueleto y error) se pintan;
  · context() manda usd por posición con la valoración de KhipuHot (paso 12) y context.genui/genui_types.
Se salta sin Playwright/Chromium. Capturas en $KH_SHOTS (opcional) para compararlas a ojo con las del prototipo.
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
SCRIPTS = ['toast.js', 'explain.js', 'agents_registry.js', 'mascot.js', 'hotclient.js', 'genui.js', 'genui_charts.js',
           'genui_shapes.js', 'oswindows.js', 'khipu_chat.js', 'desktop.js', 'cockpit.js']


def _r(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8') as f:
        return f.read()


def _chromium(p):
    for kw in ({}, {'executable_path': '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', 'args': ['--no-sandbox']}):
        try:
            return p.chromium.launch(**kw)
        except Exception:  # noqa: BLE001
            continue
    return None


QS = json.loads(_r('tests', 'fixtures', 'genui', 'prototype_questions.kblocks.json'))['questions']
EX = json.loads(_r('tests', 'fixtures', 'genui', 'examples.kblocks.json'))['valid']

ASK = r"""(q) => {
  const C = window.BixbyCockpit; if (!C.isOpen || !C.isOpen()) C.open();
  const th = document.getElementById('bcp-thread'); if (q.clear) th.textContent = '';
  const K = window.KhipuChat;
  K.appendUser(th, q.text);
  const pend = K.appendPending(th, {text: q.text});
  const d = { answer: q.answer || 'respuesta', ui: q.env, tools_used: (q.tools || []).map(n => ({name: n, ok: true})), ai: true, model: 'demo',
              elapsed_ms: 1900, steps: (q.tools || []).length, sources: [{label: 'demo', as_of: '2026-10-13T15:00:00Z'}],
              agents_used: (q.agents || []).map(a => ({agent: a, ok: true, tools: (q.tools || []).slice(0, 2)})) };
  K.fillReply(pend, d, {autoRun: false});
  return pend.querySelectorAll('.kg-root [data-kg-id]').length;
}"""

CHECK = r"""() => {
  const root = document.querySelector('.kg-root');
  const imgs = [...root.querySelectorAll('[role=img]')];
  const blocks = [...root.querySelectorAll(':scope > [data-kg-id]')];
  return { sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth,
    rootOverflow: root.scrollWidth > root.clientWidth + 1, csp: window.__csp.slice(),
    imgs: imgs.length, unlabeled: imgs.filter(e => !(e.getAttribute('aria-label') || '').trim()).length,
    blocks: blocks.length, wide: blocks.filter(b => b.getBoundingClientRect().width > root.getBoundingClientRect().width + 1).length,
    status: (document.getElementById('kg-status') || {}).textContent || '',
    srcs: (root.querySelector('.kg-srcs') || {}).textContent || '', text: root.innerText,
    anims: document.getAnimations().filter(a => a.effect && a.effect.target && a.effect.target.closest && a.effect.target.closest('.kg-root')).length,
    hidden: [...root.querySelectorAll('.kg-b,.kg-bare')].filter(e => getComputedStyle(e).opacity !== '1').length };
}"""


@pytest.fixture(scope='module')
def pw():
    sync = pytest.importorskip('playwright.sync_api')
    with sync.sync_playwright() as p:
        b = _chromium(p)
        if not b:
            pytest.skip('Chromium no disponible')
        yield b
        b.close()


def _open(browser, lang='es', theme='dark', width=1440, height=1300, reduced=True, flag=True, extra='', scripts=None):
    import server
    snap = json.loads(_r('data', 'grafo_v0.json'))
    nodes = [{'id': n['id'], 'label': n.get('label') or n['id'], 'cat': n.get('cat'), 'mkt': n.get('mkt')} for n in snap['nodes']]
    boot = ("window.LANG=%s;try{localStorage.setItem('eco_lang',%s);%slocalStorage.setItem('khipu_actor','Fabrizio B');}catch(e){}"
            "window.NODES=%s;window.NODE_BY_ID={};window.NODES.forEach(function(n){window.NODE_BY_ID[n.id]=n;});window.LINKS=[];"
            "window.NODE_META={};window.SECTORS9={};window.CAT_TO_SECTOR={};window.MKT={pos:{},quotes:{}};window.computeNRS=function(){return 40;};%s"
            % (json.dumps(lang), json.dumps(lang), "localStorage.setItem('kh_genui','1');" if flag else "localStorage.removeItem('kh_genui');",
               json.dumps(nodes), extra))
    html = ('<!doctype html><html lang="%s"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>genui</title><script src="/boot.js"></script></head><body class="%s" style="margin:0">%s</body></html>'
            % (lang, 'dark' if theme == 'dark' else '', ''.join('<script src="/engine/%s"></script>' % f for f in (scripts or SCRIPTS))))
    ctx = browser.new_context(viewport={'width': width, 'height': height}, reduced_motion='reduce' if reduced else 'no-preference')

    def handler(route):
        path = route.request.url[len('http://khipu.test'):].split('?')[0]
        if path in ('', '/'):
            return route.fulfill(status=200, content_type='text/html', body=html,
                                 headers={'Content-Security-Policy': server.CONTENT_SECURITY_POLICY})
        if path == '/boot.js':
            return route.fulfill(status=200, content_type='application/javascript', body=boot)
        if path.startswith('/engine/') and path.endswith('.js'):
            return route.fulfill(status=200, content_type='application/javascript', body=_r(path.lstrip('/')))
        return route.fulfill(status=503, content_type='application/json', body=json.dumps({'error': 'offline', 'offline': True}))
    ctx.route('http://khipu.test/**', handler)
    ctx.add_init_script("window.__csp=[];document.addEventListener('securitypolicyviolation',function(e){window.__csp.push(e.violatedDirective+' '+e.blockedURI);});")
    pg = ctx.new_page()
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto('http://khipu.test/')
    pg.wait_for_function('() => window.BixbyCockpit && window.KhipuGenUI && window.KhipuChat')
    pg.evaluate("() => { window.__surf = []; window._surface = function (k, a) { window.__surf.push([k, a]); return true; }; }")
    return ctx, pg, errs


def _ask(pg, q, lang, clear=True):
    return pg.evaluate(ASK, {'text': q['question'][lang], 'env': q['envelope'][lang], 'tools': q['tools'], 'agents': q['agents'], 'clear': clear})


@pytest.mark.parametrize('lang,theme,width', [(l, t, w) for l in ('es', 'en') for t in ('dark', 'light') for w in (1440, 390)])
def test_las_4_preguntas_del_prototipo(pw, lang, theme, width):
    shots = os.environ.get('KH_SHOTS')
    ctx, pg, errs = _open(pw, lang, theme, width, height=2300 if shots else 1300)
    try:
        for q in QS:
            n = _ask(pg, q, lang)
            visual = [b for b in q['envelope'][lang]['blocks'] if b['type'] not in ('text', 'actions', 'sources')]
            assert n >= len(visual), (q['key'], n)
            pg.wait_for_timeout(150)
            c = pg.evaluate(CHECK)
            assert not c['csp'], c['csp']
            assert c['unlabeled'] == 0 and c['imgs'] >= 1, (q['key'], c)
            assert c['wide'] == 0 and not c['rootOverflow'], (q['key'], c)
            if width == 390:
                assert c['sw'] <= c['cw'], (q['key'], c['sw'], c['cw'])
            assert c['status'].startswith('Respuesta lista' if lang == 'es' else 'Answer ready'), c['status']
            assert c['srcs'].startswith('Fuentes:' if lang == 'es' else 'Sources:'), c['srcs']
            assert c['anims'] == 0 and c['hidden'] == 0, (q['key'], c['anims'], c['hidden'])     # reducir movimiento: todo ya visible
            other = ('Fuentes', 'Fijar como ventana', 'empresas golpeadas') if lang == 'en' else ('Sources:', 'Pin as a window', 'companies hit')
            for w in other:
                assert w not in c['text'], (q['key'], w)
            if shots:
                pg.evaluate("() => { const u = document.querySelector('.kc-user'); if (u) u.scrollIntoView({block: 'start'}); }")
                pg.screenshot(path=os.path.join(shots, 'genui_%s_%s_%s_%d.png' % (q['key'], lang, theme, width)))
        assert not errs, errs
    finally:
        ctx.close()


def test_movimiento_termina_y_no_queda_en_bucle(pw):
    ctx, pg, errs = _open(pw, 'es', 'dark', 1440, reduced=False)
    try:
        c_q = [q for q in QS if q['key'] == 'c'][0]
        _ask(pg, c_q, 'es')
        early = pg.evaluate("() => document.querySelector('.kg-cast b').textContent")
        assert early in ('…', '0') or early == '60'
        assert early != '0'                                                   # nunca «0 empresas» provisional
        loops = pg.evaluate("() => document.getAnimations().filter(a => a.effect && a.effect.getComputedTiming().iterations === Infinity && a.effect.target && a.effect.target.closest && a.effect.target.closest('.kg-root')).length")
        assert loops == 0                                                     # el pulso del origen se repite 3 veces y para
        pg.wait_for_timeout(5200)
        out = pg.evaluate("""() => ({ total: document.querySelector('.kg-cast b').textContent,
          hops: [...document.querySelectorAll('.kg-hpv span')].map(e => e.textContent),
          pnl: document.querySelector('.kg-pfv').firstChild.textContent,
          anims: document.getAnimations().filter(a => a.effect && a.effect.target && a.effect.target.closest && a.effect.target.closest('.kg-root') && a.playState === 'running').length })""")
        assert out['total'] == '60' and out['hops'] == ['10', '20', '30'], out
        assert out['pnl'] == '−$1530' and out['anims'] == 0, out          # P&L sin conteo; nada sigue animándose
        b_q = [q for q in QS if q['key'] == 'b'][0]
        _ask(pg, b_q, 'es')
        pg.wait_for_timeout(1800)
        off = pg.evaluate("() => document.querySelector('.kg-t-chart-line path.ln').getAttribute('stroke-dashoffset')")
        assert off == '0'
        assert not errs, errs
    finally:
        ctx.close()


def test_fijar_abre_ventanas_con_el_mismo_contenido(pw):
    ctx, pg, errs = _open(pw, 'es', 'light', 1440)
    try:
        _ask(pg, [q for q in QS if q['key'] == 'b'][0], 'es')
        pg.click('.kg-root .kg-t-chart-line .kg-hd .kg-ic')                     # 📌 del gráfico
        pg.wait_for_selector('.kd-win[data-kind="genui"] .kg-t-chart-line svg[role=img]', timeout=5000)
        same = pg.evaluate("""() => { const a = document.querySelector('.kc-thread .kg-t-chart-line path.ln').getAttribute('d');
            const b = document.querySelector('.kd-win[data-kind="genui"] .kg-t-chart-line path.ln');
            return { same: !!b && b.getAttribute('d').length > 100, pressed: document.querySelector('.kc-thread .kg-t-chart-line .kg-hd .kg-ic').getAttribute('aria-pressed') }; }""")
        assert same['same'] and same['pressed'] == 'true', same
        pg.click('.kg-root .kg-t-graph-mini .kg-hd .kg-ic')                     # el mini-grafo → su ventana nativa
        pg.wait_for_selector('.kd-win[data-kind="supplychain"]', timeout=5000)
        assert not errs, errs
    finally:
        ctx.close()


def test_sin_bandera_el_chat_queda_como_hoy_y_el_menu_la_cambia(pw):
    ctx, pg, errs = _open(pw, 'es', 'dark', 1440, flag=False)
    try:
        _ask(pg, QS[1], 'es')
        out = pg.evaluate("() => ({ kg: !!document.querySelector('.kg-root'), body: document.querySelector('.kc-bot .kc-body').textContent })")
        assert not out['kg'] and 'respuesta' in out['body'], out
        assert pg.evaluate("() => window.KhipuChat.context().genui") is None
        pg.click('#kos-me')
        item = pg.wait_for_selector('.kos-pop [data-k="genui"]')
        assert 'Respuestas visuales (beta)' in item.text_content() and item.get_attribute('aria-checked') == 'false'
        item.click()
        assert pg.evaluate("() => localStorage.getItem('kh_genui')") == '1'
        ctxj = pg.evaluate("() => window.KhipuChat.context()")
        assert ctxj['genui'] == 1 and len(ctxj['genui_types']) == 17
        assert not errs, errs
    finally:
        ctx.close()


def test_idioma_repinta_y_ejemplos_del_esquema(pw):
    ctx, pg, errs = _open(pw, 'es', 'dark', 1440)
    try:
        _ask(pg, QS[3], 'es')
        assert pg.evaluate("() => document.querySelector('.kg-srcs').textContent.startsWith('Fuentes:')")
        pg.evaluate("() => { window.LANG = 'en'; localStorage.setItem('eco_lang', 'en'); document.documentElement.lang = 'en'; }")
        pg.wait_for_function("() => document.querySelector('.kg-srcs').textContent.startsWith('Sources:')", timeout=3000)
        for ex in EX:
            _ask(pg, {'question': {'en': ex['name']}, 'envelope': {'en': ex['envelope']}, 'tools': [], 'agents': []}, 'en', clear=False)
        evil = {'v': 'kblocks/1', 'lang': 'en', 'state': 'final', 'layout': 'auto', 'as_of': '2026-10-13T15:00:00Z', 'blocks': [
            {'id': 't9', 'type': 'text', 'state': 'ready', 'data': {'md': 'hi <img src=x onerror="window.__pwn=1"> **ok**', 'lang': 'en'}},
            {'id': 'w9', 'type': 'widget.future', 'state': 'ready', 'alt': {'es': 'texto alternativo', 'en': 'alt text here'}, 'data': {}},
            {'id': 'g9', 'type': 'geo.mini', 'state': 'ready', 'title': {'es': 'Dónde', 'en': 'Where'}, 'alt': {'es': 'Mapa', 'en': 'Map of Taiwan and Korea'},
             'prov': {'kind': 'tool', 'name': 'get_world_events', 'call': 0},
             'data': {'region': 'east_asia', 'src': 'demo', 'as_of': '2026-10-13T15:00:00Z', 'points': [
                 {'lat': 24.8, 'lon': 121.0, 'label': 'TSMC', 'kind': 'fab', 'risk': True, 'precision': 'city'},
                 {'lat': 37.3, 'lon': 127.0, 'label': 'Samsung', 'kind': 'company', 'precision': 'city'}],
                 'arcs': [{'from': [24.8, 121.0], 'to': [37.3, 127.0], 'weight': 0.5}]}},
            {'id': 'a9', 'type': 'actions', 'state': 'ready', 'data': {'items': [{'kind': 'place_order', 'label': {'es': 'Comprar', 'en': 'Buy'}}]}}]}
        _ask(pg, {'question': {'en': 'x'}, 'envelope': {'en': evil}, 'tools': [], 'agents': []}, 'en', clear=False)
        safe = pg.evaluate("""() => { const r = [...document.querySelectorAll('.kg-root')].pop();
            return { img: r.querySelectorAll('img').length, pwn: !!window.__pwn, bold: !!r.querySelector('.kg-text b'),
                     unk: (r.querySelector('.kg-unk') || {}).textContent || '', geo: r.querySelectorAll('.kg-geo circle.pt').length,
                     geoLabel: (r.querySelector('.kg-geo') || {getAttribute: () => ''}).getAttribute('aria-label'), buy: [...r.querySelectorAll('button')].some(b => /Buy/.test(b.textContent)) }; }""")
        assert safe['geo'] == 2 and safe['geoLabel'] == 'Map of Taiwan and Korea', safe
        assert safe['img'] == 0 and not safe['pwn'] and safe['bold'] and 'alt text here' in safe['unk'] and not safe['buy'], safe
        st = pg.evaluate("""() => ({ planned: document.querySelectorAll('.kg-root [aria-busy=true][data-kg-type]').length,
            alert: document.querySelectorAll('.kg-root .kg-err[role=alert]').length,
            shapes: document.querySelectorAll('.kg-root .kg-steps .kg-sh').length,
            candles: document.querySelectorAll('.kg-root .kg-t-chart-candles rect').length,
            stale: document.querySelectorAll('.kg-root .kg-stale').length, csp: window.__csp })""")
        assert st['planned'] >= 1 and st['alert'] >= 1 and st['shapes'] >= 4 and st['candles'] >= 2 and st['stale'] >= 1, st
        assert not st['csp'], st
        assert not errs, errs
    finally:
        ctx.close()


def test_contexto_usd_por_posicion_igual_que_khipuhot(pw):
    extra = ("window.MKT={pos:{Nvidia:{sh:10,bp:100},Apple:{sh:4,bp:200},AMD:{sh:3}},quotes:{NVDA:{close:180,src:'yahoo'},AAPL:{close:250,live:251,src:'finnhub'}}};"
             "window.quotePx=function(q){if(!q)return 0;var v=typeof q.live==='number'?q.live:q.close;return Number(v)||0;};")
    ctx, pg, errs = _open(pw, 'es', 'dark', 1440, extra=extra)
    try:
        out = pg.evaluate("() => ({ c: window.KhipuChat.context().portfolio.positions, h: window.KhipuHot.myPositions().positions })")
        by = {p['symbol']: p for p in out['c']}
        hot = {p['symbol']: p['usd'] for p in out['h']}
        assert by['NVDA']['usd'] == hot['NVDA'] == 1800 and by['AAPL']['usd'] == hot['AAPL'] == 1004
        amd = [p for p in out['c'] if p['shares'] == 3]
        assert amd and 'usd' not in amd[0]                                 # sin precio: sin usd (nunca un monto inventado)
        assert all('shares' in p for p in out['c'])
        assert not errs, errs
    finally:
        ctx.close()


# ═══ revisión F2 (hallazgos del 2026-10-14): cada prueba fallaba antes del arreglo ═══════════════════════════════════
def _menu(pg, sel, word):
    """Abre el ⋯ del bloque `sel` y elige el ítem cuyo texto contiene `word`."""
    pg.click(sel + ' .kg-hd .kg-ic[aria-haspopup=menu]')
    items = pg.query_selector_all('.kg-pop [role=menuitem]')
    hit = [i for i in items if word in i.text_content()]
    assert hit, [i.text_content() for i in items]
    hit[0].click()


def test_tabla_y_vuelta_al_grafico_conserva_las_cifras(pw):
    ctx, pg, errs = _open(pw, 'es', 'dark', 1440)
    try:
        _ask(pg, [q for q in QS if q['key'] == 'c'][0], 'es')
        cas = '.kg-root .kg-t-impact-cascade'
        HID = "() => [...document.querySelector('.kg-t-impact-cascade').querySelectorAll('*')].filter(e => getComputedStyle(e).opacity === '0').map(e => e.className.baseVal || e.className)"
        hid0 = pg.evaluate(HID)                         # lo que ya va oculto a propósito (p. ej. el pulso que terminó)
        _menu(pg, cas, 'tabla')
        assert pg.evaluate("() => !!document.querySelector('.kg-t-impact-cascade .kg-tb')")
        _menu(pg, cas, 'gráfico')
        out = pg.evaluate("""() => { const r = document.querySelector('.kg-t-impact-cascade');
            return { total: r.querySelector('.kg-cast b').textContent, hops: [...r.querySelectorAll('.kg-hpv span')].map(e => e.textContent),
              hidden: [...r.querySelectorAll('*')].filter(e => getComputedStyle(e).opacity === '0').length,
              flat: [...r.querySelectorAll('*')].filter(e => /matrix\\(0, 0, 0, 1|scaleX\\(0\\)/.test(getComputedStyle(e).transform)).length }; }""")
        assert out['total'] == '60' and out['hops'] == ['10', '20', '30'], out
        assert pg.evaluate(HID) == hid0 and out['flat'] == 0, (out, hid0, pg.evaluate(HID))
        _ask(pg, [q for q in QS if q['key'] == 'b'][0], 'es')
        ln = '.kg-root .kg-t-chart-line'
        _menu(pg, ln, 'tabla')
        _menu(pg, ln, 'gráfico')
        assert pg.evaluate("() => document.querySelector('.kg-t-chart-line path.ln').getAttribute('stroke-dashoffset')") == '0'
        assert not errs, errs
    finally:
        ctx.close()


def test_menu_por_teclado_devuelve_el_foco(pw):
    ctx, pg, errs = _open(pw, 'es', 'dark', 1440)
    try:
        _ask(pg, [q for q in QS if q['key'] == 'b'][0], 'es')
        pg.focus('.kg-root .kg-t-chart-line .kg-hd .kg-ic[aria-haspopup=menu]')
        pg.keyboard.press('Enter')
        a = pg.evaluate("() => ({ role: document.activeElement.getAttribute('role'), menu: document.querySelector('.kg-pop').getAttribute('role'), n: document.querySelectorAll('.kg-pop [role=menuitem]').length, txt: document.activeElement.textContent })")
        assert a['role'] == 'menuitem' and a['menu'] == 'menu' and a['n'] >= 2, a
        pg.keyboard.press('ArrowDown')
        b = pg.evaluate("() => document.activeElement.textContent")
        assert b != a['txt']
        pg.keyboard.press('Escape')
        back = "() => document.activeElement.matches('.kg-t-chart-line .kg-ic[aria-haspopup=menu]')"
        assert pg.evaluate(back) and not pg.query_selector('.kg-pop')
        pg.keyboard.press('Enter')                       # elegir «Ver como tabla» con el teclado: el foco vuelve al ⋯
        pg.keyboard.press('Enter')
        assert pg.evaluate("() => !!document.querySelector('.kg-t-chart-line .kg-tb')") and pg.evaluate(back)
        # «¿De dónde sale?» no es un menú: es un diálogo
        _menu(pg, '.kg-root .kg-t-chart-line', 'dónde')
        assert pg.evaluate("() => document.querySelector('.kg-pop').getAttribute('role')") == 'dialog'
        assert not errs, errs
    finally:
        ctx.close()


def _env(blocks, lang='es'):
    return {'v': 'kblocks/1', 'lang': lang, 'state': 'final', 'layout': 'auto', 'as_of': '2026-10-13T15:00:00Z', 'blocks': blocks}


def test_marcas_utf16_con_emojis_y_teclado_en_enlaces(pw):
    from core.genui.layout import marks_of
    md = '📈 TSMC subió y 🚀 Nvidia también [F1]. Luego Intel (⚠ cifra no verificada)'
    ents = [{'id': 'TSMC', 'label': 'TSMC'}, {'id': 'Nvidia', 'label': 'Nvidia'}, {'id': 'Intel', 'label': 'Intel'}]
    blocks = [{'id': 't1', 'type': 'text', 'state': 'ready', 'data': {'md': md, 'lang': 'es', 'marks': marks_of(md, ents)}},
              {'id': 'tb', 'type': 'table', 'state': 'ready', 'title': {'es': 'Tabla', 'en': 'Table'},
               'prov': {'kind': 'tool', 'name': 'get_company', 'call': 0},
               'data': {'columns': [{'key': 'e', 'label': {'es': 'Empresa', 'en': 'Company'}, 'kind': 'entity'}],
                        'rows': [{'e': {'id': 'Nvidia', 'label': 'Nvidia'}}]}},
              {'id': 'tl', 'type': 'timeline', 'state': 'ready', 'title': {'es': 'Hechos', 'en': 'Events'},
               'prov': {'kind': 'tool', 'name': 'get_world_events', 'call': 0},
               'data': {'items': [{'date': '2026-10-12', 'title': {'es': 'Sismo', 'en': 'Quake'}, 'kind': 'event', 'src': 'usgs',
                                   'entity': {'id': 'TSMC', 'label': 'TSMC'}, 'lat': 24.8, 'lon': 121.0}]}},
              {'id': 'src', 'type': 'sources', 'state': 'ready', 'data': {'items': [{'id': 'F1', 'label': 'Finnhub', 'as_of': '2026-10-13T15:00:00Z'}]}}]
    ctx, pg, errs = _open(pw, 'es', 'dark', 1440)
    try:
        _ask(pg, {'question': {'es': 'x'}, 'envelope': {'es': _env(blocks)}, 'tools': [], 'agents': []}, 'es')
        mk = pg.evaluate("() => [...document.querySelectorAll('.kg-text .kg-mk')].map(e => [e.className.split('kg-mk-')[1], e.textContent])")
        assert mk == [['entity', 'TSMC'], ['entity', 'Nvidia'], ['fact', '[F1]'], ['entity', 'Intel'],
                      ['unverified', '(⚠ cifra no verificada)']], mk
        # Enter / Espacio abren lo mismo que el clic
        for sel, key in (('.kg-tb .kg-ent', 'Enter'), ('.kg-tl .kg-ent', ' '), ('.kg-text .kg-mk-entity', 'Enter')):
            pg.evaluate('() => { window.__surf = []; }')
            pg.focus(sel)
            pg.keyboard.press(key)
            assert pg.evaluate('() => window.__surf.length') == 1, sel
        pg.focus('.kg-text .kg-mk-fact')
        pg.keyboard.press('Enter')
        assert pg.evaluate("() => !!document.querySelector('[data-kg-fact=\"F1\"].hi')")
        assert not errs, errs
    finally:
        ctx.close()


def test_conteo_nunca_muestra_un_cero_provisional(pw):
    ctx, pg, errs = _open(pw, 'es', 'dark', 1440, reduced=False)
    try:
        pg.evaluate("""() => { window.__seen = {tot: [], hop: []};
            const tick = () => { const t = document.querySelector('.kg-cast b'); if (t) window.__seen.tot.push(t.textContent);
              const h = document.querySelector('.kg-hpv span'); if (h) window.__seen.hop.push(h.textContent);
              if (window.__seen.tot.length < 400) requestAnimationFrame(tick); };
            requestAnimationFrame(tick);
            new MutationObserver(() => { const t = document.querySelector('.kg-cast b'); if (t) window.__seen.tot.push(t.textContent);
              const h = document.querySelector('.kg-hpv span'); if (h) window.__seen.hop.push(h.textContent); })
              .observe(document.body, {subtree: true, childList: true, characterData: true}); }""")
        _ask(pg, [q for q in QS if q['key'] == 'c'][0], 'es')
        pg.wait_for_timeout(4000)
        seen = pg.evaluate('() => window.__seen')
        assert '0' not in seen['tot'] and '0' not in seen['hop'], (seen['tot'][:12], seen['hop'][:12])
        assert seen['tot'][-1] == '60'
        assert not errs, errs
    finally:
        ctx.close()


def test_ventana_fijada_conserva_la_fuente_al_cambiar_idioma(pw):
    ctx, pg, errs = _open(pw, 'es', 'light', 1440)
    try:
        _ask(pg, [q for q in QS if q['key'] == 'b'][0], 'es')
        pg.click('.kg-root .kg-t-chart-line .kg-hd .kg-ic')
        win = '.kd-win[data-kind="genui"] .kg-t-chart-line .kg-src'
        pg.wait_for_selector(win, timeout=5000)
        before = pg.text_content(win)
        pg.evaluate("() => { window.LANG = 'en'; localStorage.setItem('eco_lang', 'en'); document.documentElement.lang = 'en'; }")
        pg.wait_for_function("() => document.querySelector('.kg-srcs').textContent.startsWith('Sources:')", timeout=3000)
        after = pg.text_content(win)
        label = before.split('·')[0].strip()
        assert len(label) > 3 and label in after, (before, after)
        assert not errs, errs
    finally:
        ctx.close()


CONTRAST = r"""(sel) => {
  const lum = (c) => { const m = c.match(/[\d.]+/g).map(Number); const f = v => { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); };
    return .2126 * f(m[0]) + .7152 * f(m[1]) + .0722 * f(m[2]); };
  const bg = (e) => { for (; e; e = e.parentElement) { const c = getComputedStyle(e).backgroundColor; const a = (c.match(/[\d.]+/g) || []).map(Number);
    if (a.length === 3 || (a.length === 4 && a[3] === 1)) return c; } return 'rgb(255,255,255)'; };
  return [...document.querySelectorAll(sel)].slice(0, 12).map(e => { const a = lum(getComputedStyle(e).color), b = lum(bg(e));
    return (Math.max(a, b) + .05) / (Math.min(a, b) + .05); });
}"""


@pytest.mark.parametrize('theme', ['light', 'dark'])
def test_procedencia_legible_contraste_aa(pw, theme):
    ctx, pg, errs = _open(pw, 'es', theme, 1440)
    try:
        worst = 99
        for q in QS:
            _ask(pg, q, 'es')
            for sel in ('.kg-root .kg-src', '.kg-root .kg-sub', '.kg-root .kg-srcs', '.kg-root .kg-d', '.kg-root .kg-tb th', '.kg-root .kg-tld'):
                vals = pg.evaluate(CONTRAST, sel)
                if vals:
                    worst = min(worst, min(vals))
        assert worst >= 4.5, worst
    finally:
        ctx.close()


def test_graficos_perezosos(pw):
    lean = [f for f in SCRIPTS if f not in ('genui_charts.js', 'genui_shapes.js')]
    ctx, pg, errs = _open(pw, 'es', 'dark', 1440, flag=False, scripts=lean)
    try:
        pg.wait_for_timeout(300)
        assert pg.evaluate("() => !window.KhipuGenUI.extrasReady() && !document.querySelector('script[src*=genui_charts]')")
        # llega un sobre con gráficos sin la bandera (p. ej. otra pestaña la encendió): se cargan y se repinta
        pg.evaluate("() => localStorage.setItem('kh_genui', '1')")
        _ask(pg, [q for q in QS if q['key'] == 'b'][0], 'es')
        pg.wait_for_selector('.kg-root .kg-t-chart-line svg[role=img]', timeout=5000)
        assert pg.evaluate("() => window.KhipuGenUI.extrasReady() && document.querySelectorAll('script[src*=genui_charts]').length === 1")
        assert not errs, errs
    finally:
        ctx.close()
    ctx, pg, errs = _open(pw, 'es', 'dark', 1440, flag=True, scripts=lean)
    try:
        pg.wait_for_function('() => window.KhipuGenUI.extrasReady()', timeout=5000)     # con la bandera: al arrancar
        assert not errs, errs
    finally:
        ctx.close()
