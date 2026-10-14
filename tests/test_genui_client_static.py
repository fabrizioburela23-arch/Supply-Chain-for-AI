"""tests/test_genui_client_static.py — RESPUESTAS VISUALES del chat (kblocks/1), fase F2: reglas estáticas del cliente
(docs/CHAT_UI_GENERATIVA.md §7.3, §9, §10.1).

· DOM seguro: en engine/genui*.js el ÚNICO innerHTML es la salida de KhipuChat.md() (markdown que escapa primero);
  sin onclick= en línea, sin eval/new Function, sin window.confirm/alert/prompt, sin setAttribute('style', …).
· Catálogo cerrado: los tipos registrados son EXACTAMENTE los 17 del esquema; las acciones y ventanas, las del esquema
  (ningún botón de dinero).
· Bilingüe: todo diccionario propio tiene las mismas claves en es y en.
· Tokens: colores solo con var(--os-*) / var(--kg-*) (más la serie B validada y la paleta del Canvas).
· Carga: genui.js antes de khipu_chat.js (gráficos y formas, perezosos); los tres en el SHELL de sw.js; CACHE ≥ v269.
· Gancho: khipu_chat.js pinta d.ui solo con la bandera; manda usd por posición (paso 12); el menú del avatar tiene el
  interruptor «Respuestas visuales (beta)»; cockpit.js define los tokens de movimiento.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ('genui.js', 'genui_charts.js', 'genui_shapes.js')


def _r(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8') as f:
        return f.read()


def _code(src):
    return re.sub(r'/\*[\s\S]*?\*/', '', re.sub(r'(?m)^\s*//[^\n]*', '', src))


def _schema():
    return json.loads(_r('governance', 'schemas', 'kblocks-1.schema.json'))['$defs']


def test_dom_seguro():
    for f in FILES:
        code = _code(_r('engine', f))
        sets = re.findall(r'\.innerHTML\s*=\s*([^;\n]+)', code)
        for rhs in sets:
            assert rhs.strip().startswith('K.md('), (f, rhs)        # solo markdown que escapa primero
        assert len(sets) <= 1 if f == 'genui.js' else not sets, (f, sets)
        assert 'insertAdjacentHTML' not in code and 'outerHTML' not in code and 'document.write' not in code, f
        assert not re.search(r'\bonclick\s*=|on[a-z]+=\\?["\']', code), f
        assert not re.search(r'\beval\s*\(|new\s+Function\b', code), f
        assert not re.search(r'\b(window\.)?(confirm|alert|prompt)\s*\(', code), f
        assert "setAttribute('style'" not in code and 'setAttribute("style"' not in code, f
        assert '/v1/' not in code, f


def test_catalogo_cerrado_igual_al_esquema():
    d = _schema()
    enum = [b['$ref'].split('/')[-1] for b in d['Block']['oneOf']]
    want = sorted(d[x]['properties']['type']['const'] for x in enum)
    src = ''.join(_r('engine', f) for f in FILES)
    got = sorted(set(re.findall(r"(?:register|G\.register)\('([a-z.]+)'", src)))
    assert got == want and len(got) == 17, (got, want)
    m = re.search(r'var TYPES = \[([^\]]+)\]', _r('engine', 'genui.js'))
    assert sorted(re.findall(r"'([a-z.]+)'", m.group(1))) == want


def test_acciones_y_ventanas_del_esquema_sin_dinero():
    d = _schema()
    src = _r('engine', 'genui.js')
    acts = re.findall(r"(\w+): 1", re.search(r'var ACTION_KINDS = \{([^}]+)\}', src).group(1))
    wins = re.findall(r"(\w+): 1", re.search(r'var WINDOWS = \{([^}]+)\}', src).group(1))
    assert sorted(acts) == sorted(d['Action']['properties']['kind']['enum'])
    assert sorted(wins) == sorted(d['WindowKind']['enum'])
    for bad in ('broker', 'trade', 'order', 'place_order', 'approve', 'submit_order', 'preview_order'):
        assert bad not in acts and bad not in wins
    for f in FILES:
        code = _code(_r('engine', f))
        for tok in ('/api/trade', '/api/brokerage', 'confirmOrder', '_tradeFetch', '_executeTradeOrder'):
            assert tok not in code, (f, tok)
    # la ruta de imagen es la del esquema (mismo origen); nunca img-src https: elegido por la IA
    sch = d['ImageBlock']['properties']['data']['properties']['asset']['properties']['path']['pattern']
    assert sch.replace('\\/', '/') in src.replace('\\/', '/')


def _dict_keys(src, name):
    m = re.search(r'var ' + name + r' = \{\s*es: \{([\s\S]*?)\},\s*en: \{([\s\S]*?)\}\s*\};', src)
    assert m, name
    k = lambda body: sorted(set(re.findall(r'(?:^|[,{\s])([A-Za-z]\w*):\s', body)))
    return k(m.group(1)), k(m.group(2))


def test_textos_bilingues():
    es, en = _dict_keys(_r('engine', 'genui.js'), 'S')
    assert es == en and len(es) > 60
    es, en = _dict_keys(_r('engine', 'genui_charts.js'), 'CS')
    assert es == en and len(es) > 30
    for f in FILES:
        src = _r('engine', f)
        # rótulos sueltos L('es','en') / I18n literales: siempre de a pares
        for m in re.finditer(r"label: \{ es: '([^']*)', en: '([^']*)' \}", src):
            assert m.group(1) and m.group(2)
    ck = _r('engine', 'cockpit.js')
    assert "L('Respuestas visuales (beta)', 'Visual answers (beta)')" in ck
    assert "L('activas', 'on')" in ck and "L('apagadas', 'off')" in ck


def test_colores_solo_tokens():
    ok = {'#E06640', '#E8623A', '#fff', '#8a8577', '#4C8DF6'}   # serie B validada (claro/oscuro), blanco sobre acento, «otros» de cvCol
    for f in FILES:
        src = _r('engine', f)
        css = ''.join(re.findall(r"var CSS = ''([\s\S]*?);\n", src))
        assert css, f
        bare = re.sub(r'var\(--[a-z0-9-]+,[^()]*(\([^()]*\))?[^()]*\)', '', css)     # los respaldos dentro de var() no cuentan
        for hx in re.findall(r'#[0-9A-Fa-f]{3,6}\b', bare):
            assert hx in ok, (f, hx)
        assert 'var(--os-' in css


def test_movimiento_tokens_y_reducido():
    ck = _r('engine', 'cockpit.js')
    for tok in ('--os-dur-1:120ms', '--os-dur-2:220ms', '--os-dur-3:380ms', '--os-ease-out:cubic-bezier(.2,0,0,1)',
                '--os-ease-inout:cubic-bezier(.4,0,.2,1)', '--os-stagger:70ms'):
        assert tok in ck, tok
    assert re.search(r'prefers-reduced-motion:reduce\)\{#bcp-ov,\.kos-themed\{--os-dur-1:0ms', ck)
    g = _r('engine', 'genui.js')
    assert 'prefers-reduced-motion' in g and '.kg-rm' in g
    # nada en bucle: solo animaciones con un número FIJO de repeticiones
    for f in FILES:
        assert 'infinite' not in _r('engine', f), f
    # sin conteo animado de precios / P&L: solo conteos y puntajes
    assert re.search(r'var COUNTABLE = \{ count: 1, score: 1 \};', g)


def test_carga_shell_y_version():
    app = _r('app.html')
    pos = {f: app.index('<script src="engine/%s"></script>' % f) for f in
           ('explain.js', 'genui.js', 'oswindows.js', 'khipu_chat.js', 'cockpit.js')}
    assert pos['genui.js'] < pos['oswindows.js'] < pos['khipu_chat.js'] < pos['cockpit.js']
    # gráficos y formas: PEREZOSOS (genui.js los pide con la bandera o con el primer sobre), nunca en app.html (§8)
    assert 'engine/genui_charts.js' not in app and 'engine/genui_shapes.js' not in app
    g = _r('engine', 'genui.js')
    assert "EXTRAS = ['genui_charts.js', 'genui_shapes.js', 'genui_progress.js']" in g and 'sc.async = false' in g
    sw = _r('sw.js')
    shell = sw[sw.index('const SHELL'):sw.index('];', sw.index('const SHELL'))]
    for f in FILES:
        assert "'/engine/%s'" % f in shell, f
    m = re.search(r"const CACHE = 'khipu-finance-v(\d+)'", sw[:2048])
    assert m and int(m.group(1)) >= 269


def test_gancho_del_chat_y_usd_por_posicion():
    kc = _r('engine', 'khipu_chat.js')
    assert 'G.enabled()' in kc and 'G.renderAnswer(body, d.ui' in kc and 'd.ui.v !== G.V' in kc
    assert 'ctx.genui = 1' in kc and 'ctx.genui_types = G.catalog()' in kc
    assert 'W.KhipuHot.myPositions()' in kc and 'o.usd = usdBy[n.id]' in kc
    # el texto de siempre queda de respaldo si el sobre no se puede pintar
    assert "body.innerHTML = md(d.answer" in kc


def test_presupuesto_de_tamano_trinquete():
    """§8 pide ≤ 90 KB sin minificar para los tres archivos. HOY no se cumple (ver el informe de F2): este trinquete
    impide que crezca y obliga a bajar el tope cuando se recorte."""
    raw = sum(len(_r('engine', f).encode('utf-8')) for f in FILES)
    assert raw <= 168 * 1024, raw
    # lo que se descarga e interpreta al ABRIR la app (sin la bandera) es solo genui.js: dentro de los 90 KB
    assert len(_r('engine', 'genui.js').encode('utf-8')) <= 90 * 1024
