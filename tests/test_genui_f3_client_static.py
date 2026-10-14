"""tests/test_genui_f3_client_static.py — RESPUESTAS VISUALES PROGRESIVAS (F3, pasos 23-24), cliente sin navegador
(docs/CHAT_UI_GENERATIVA.md §6, §7.4, §8).

  · la IDENTIDAD de un bloque (keyOf de engine/khipu_chat.js) es la MISMA que la del servidor (_ui_key): sobre los
    ejemplos del esquema, las 4 preguntas del prototipo y un esqueleto/error;
  · movimiento: la duración sale de los tokens --os-dur-* y con «reducir movimiento» es 0; el CSS nuevo apaga la
    entrada y muestra el texto entero con prefers-reduced-motion; solo se anima transform/opacity, nada en bucle;
  · esqueleto con altura RESERVADA = height() del renderizador con un contenido típico (estable por ancho);
  · el sondeo pide `?since=` solo con la burbuja de respuestas visuales (servidor viejo / sin bandera: igual que hoy);
  · el desplazamiento inteligente decide con el 30 % de una pantalla;
  · presupuestos: genui.js sigue dentro de sus 90 KB; sw.js sube de versión; textos nuevos ES/EN.
"""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
NODE = shutil.which('node')


def _r(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8') as f:
        return f.read()


HARNESS = r"""
const fs = require('fs'), vm = require('vm');
const ROOT = process.argv[1];
const store = {}, media = { reduce: false };
const ctx = { console, Date, Math, JSON, Intl, Promise, Array, Object, String, Number, isFinite, parseFloat,
  setTimeout, clearTimeout, setInterval: () => 0, clearInterval: () => {},
  localStorage: { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } },
  matchMedia: q => ({ matches: /reduce/.test(q) && media.reduce }),
  getComputedStyle: el => ({ overflowY: el && el._ovf || 'visible', getPropertyValue: k => (el && el._vars && el._vars[k]) || '' }) };
ctx.window = ctx; ctx.globalThis = ctx;
ctx.document = { createElement: () => ({ style: {}, setAttribute() {}, appendChild() {} }), getElementById: () => null, head: null, querySelectorAll: () => [] };
vm.createContext(ctx);
for (const f of ['agents_registry.js', 'genui.js', 'genui_charts.js', 'genui_shapes.js', 'genui_progress.js', 'khipu_chat.js'])
  vm.runInContext(fs.readFileSync(ROOT + '/engine/' + f, 'utf8'), ctx);
const K = ctx.KhipuChat, G = ctx.KhipuGenUI, out = {};
const blocks = JSON.parse(process.argv[2]);
out.keys = blocks.map(b => K.keyOf(b));
const el = { _vars: { '--os-dur-2': ' 220ms', '--os-dur-3': '380ms' } };
out.dur = [K._f3.dur(el, 2), K._f3.dur(el, 3), K._f3.dur({}, 2), K._f3.dur({}, 1)];
media.reduce = true;
out.durReduced = [K._f3.dur(el, 2), K._f3.dur(el, 3), K._f3.dur({}, 2)];
media.reduce = false;
// altura reservada del esqueleto: height() del renderizador con el contenido TÍPICO (y estable)
out.reserve = {};
['metric.tiles', 'chart.line', 'impact.cascade', 'graph.mini', 'ranking', 'timeline'].forEach(t => {
  const pseudo = { type: t, state: 'ready', data: K._f3.typical[t] || {} };
  out.reserve[t] = [G._u.height(pseudo, 473), G._u.height(pseudo, 473), G._u.height(pseudo, 316), G._u.height({ type: t, state: 'planned' }, 473)];
});
// desplazamiento inteligente: a menos del 30 % de una pantalla del final = siguiendo
const mk = (top) => { const sc = { scrollHeight: 3000, clientHeight: 800, scrollTop: top, _ovf: 'auto' }; sc.parentElement = null;
  return { parentElement: sc }; };
out.stick = [K._f3.stick(mk(2200)), K._f3.stick(mk(1960)), K._f3.stick(mk(1959)), K._f3.stick(mk(0)), K._f3.stick({ parentElement: null })];
process.stdout.write(JSON.stringify(out));
"""


def _blocks():
    ex = json.loads(_r('tests', 'fixtures', 'genui', 'examples.kblocks.json'))
    pq = json.loads(_r('tests', 'fixtures', 'genui', 'prototype_questions.kblocks.json'))
    out = [b for v in ex['valid'] for b in v['envelope']['blocks']]
    for q in pq['questions']:
        for lang in ('es', 'en'):
            out += q['envelope'][lang]['blocks']
    out += [{'id': 'p3', 'type': 'impact.cascade', 'state': 'planned', 'prov': {'kind': 'tool', 'name': 'run_scenario', 'call': 3}},
            {'id': 'q9', 'type': 'chart.line', 'state': 'ready', 'prov': {'kind': 'tool', 'name': 'get_history', 'call': 0},
             'data': {'rebased': True, 'series': []}},
            {'id': 'g1', 'type': 'geo.mini', 'state': 'error', 'prov': {'kind': 'view', 'name': 'hot.geo'}}]
    return out


@pytest.fixture(scope='module')
def run():
    if not NODE:
        pytest.skip('requiere node')
    bl = _blocks()
    p = subprocess.run([NODE, '-e', HARNESS, ROOT, json.dumps(bl)], capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr[-2000:]
    return bl, json.loads(p.stdout)


def test_identidad_igual_a_la_del_servidor(run):
    from core import khipu_chat as kc
    bl, o = run
    assert o['keys'] == [kc._ui_key(b) for b in bl]
    assert len(set(o['keys'][-3:])) == 3 and o['keys'][-2].endswith('|r')        # la línea en índice 100 es otra


def test_movimiento_con_tokens_y_reducido_es_cero(run):
    _bl, o = run
    assert o['dur'] == [220, 380, 220, 120]            # token --os-dur-N (con respaldo 120/220/380 si falta)
    assert o['durReduced'] == [0, 0, 0]                # reducir movimiento: nada se anima


def test_esqueleto_reserva_la_altura_del_renderizador(run):
    _bl, o = run
    for t, (a, b, narrow, planned) in o['reserve'].items():
        assert a == b and a >= planned and a >= 100, t          # estable, nunca menor que la del bloque vacío
    assert o['reserve']['metric.tiles'][2] >= o['reserve']['metric.tiles'][0]   # angosto: 2 filas de cifras


def test_desplazamiento_inteligente_30_por_ciento(run):
    _bl, o = run
    # al final, a 240 px (=30 % de 800) del final, a 241 px, arriba del todo, y sin contenedor desplazable
    assert o['stick'] == [True, True, False, False, True]


def _f3_js():
    # el motor F3 vive en engine/genui_progress.js (perezoso, lote J); khipu_chat.js conserva el sondeo, el CSS y los
    # ayudantes de movimiento
    return _r('engine', 'khipu_chat.js') + '\n' + _r('engine', 'genui_progress.js')


def test_css_reducido_solo_transform_opacidad_y_nada_en_bucle():
    js = _f3_js()
    css = ''.join(re.findall(r"'(\.kc-prov[^']*|\.kc-in[^']*|@keyframes kcBk[^']*|\.kc-xf[^']*|\.kc-main>\.kc-think[^']*|"
                             r"\.kc-more[^']*|@media\(prefers-reduced-motion:reduce\)[^']*)'", js))
    assert '.kc-in{animation:kcBk var(--os-dur-2' in css and 'var(--os-ease-out' in css
    kf = re.search(r'@keyframes kcBk\{([^}]*\}[^}]*)\}', css).group(1)
    assert set(re.findall(r'([a-z-]+):', kf)) <= {'from', 'to', 'opacity', 'transform'}, kf
    red = re.search(r"@media\(prefers-reduced-motion:reduce\)\{([^']*)\}'", js).group(1)
    assert '.kc-in' in red and 'animation:none' in red and '.kc-w{opacity:1}' in red
    assert 'infinite' not in js
    # las animaciones por script (FLIP, fundido del esqueleto) solo tocan transform u opacidad
    for m in re.finditer(r'\.animate\(\[([^\]]*)\]', js):
        props = set(re.findall(r'\{ ?([a-zA-Z]+):', m.group(1)))
        assert props <= {'transform', 'opacity'}, m.group(0)


def test_sondeo_con_since_solo_con_la_burbuja_nueva_y_textos_bilingues():
    js = _f3_js()
    assert "(el._kgShell ? '?since=' + since : '')" in js
    assert 'progressBlocks(el, p.ui)' in js and 'G.renderBlock(pb, b,' in js
    # el sobre final manda: renderAnswer con `reuse` (mismo bloque = mismo elemento) y el texto de siempre de respaldo
    assert "reuse: opts.reuse || null" in js and "body.innerHTML = md(d.answer" in js
    for es, en in (("'Más datos de esta respuesta'", "'More data from this answer'"), ("'paso'", "'step'"),
                   ("'pasos'", "'steps'"), ("'Respuesta'", "'Answer'")):
        assert "L(%s, %s)" % (es, en) in js, es
    g = _r('engine', 'genui.js')
    assert 'opts.reuse && b && !b.cards ? opts.reuse(b) : null' in g and 'if (x.kept) return;' in g
    assert len(g.encode('utf-8')) <= 90 * 1024                  # §8: lo que se carga al abrir sigue dentro de 90 KB


def test_motor_f3_perezoso_y_fuera_de_lo_que_baja_todo_el_mundo():
    """Revisión F3 (lote J): el motor de respuestas progresivas ya no viaja en khipu_chat.js (lo bajan todos aunque la
    bandera esté apagada): engine/genui_progress.js lo carga KhipuGenUI.loadExtras con los gráficos, está en el SHELL y
    NO en app.html. khipu_chat.js vuelve cerca de su tamaño de antes de F3 (88 KB)."""
    g, kc, app, sw = _r('engine', 'genui.js'), _r('engine', 'khipu_chat.js'), _r('app.html'), _r('sw.js')
    assert "EXTRAS = ['genui_charts.js', 'genui_shapes.js', 'genui_progress.js']" in g
    assert 'engine/genui_progress.js' not in app and "'/engine/genui_progress.js'" in sw
    gp = _r('engine', 'genui_progress.js')
    for fn in ('land(', '_moreFold(', '_reveal(', 'keepOnError(', '_foldSteps(', '_xfade('):
        assert 'function ' + fn in gp, fn
    for fn in ('_land(', '_moreFold(', '_reveal(', 'keepOnError(', '_foldSteps(', '_xfade('):
        assert 'function ' + fn not in kc, fn
    assert len(kc.encode('utf-8')) <= 98 * 1024, len(kc.encode('utf-8'))
    assert len(_r('engine', 'genui_progress.js').encode('utf-8')) <= 16 * 1024
    # sin el motor cargado todo funciona como sin la bandera (fillReply no aterriza; progressBlocks lo pide)
    assert 'F3 = _f3m(), land = !!(F3 &&' in kc and 'G.loadExtras().then(function () { if (_f3m()' in kc


def test_sw_sube_de_version():
    sw = _r('sw.js')
    m = re.search(r"const CACHE = 'khipu-finance-v(\d+)'", sw[:2048])
    assert m and int(m.group(1)) >= 270
