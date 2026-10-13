"""G5-06 (2026-10-13) — app.html partido SIN cambiar comportamiento.

El JS propio de app.html vive en engine/app_*.js: cada archivo es, byte a byte, un bloque `<script>` inline de antes,
cargado con `<script src="engine/app_X.js"></script>` EXACTAMENTE donde estaba el bloque (script clásico: sin
defer/async/module → corre en el mismo orden y comparte el ámbito global igual que antes). Quedan inline solo los
bloques que deben correr aunque falle la carga de archivos externos (arranque de emergencia + seguridad + franja de
"servidor no disponible", el vigía de /api/health) y dos diminutos (orbe, insignia de 👥 Clientes).

Esta prueba fija ese contrato: orden documentado, cada archivo existe, está en el SHELL de sw.js, compila con
`node --check`, los bloques inline que quedan compilan con vm.Script y tests/_app_source.app_source() vuelve a armar
el texto de antes (las demás pruebas leen app.html con él).
"""
import json
import os
import re
import shutil
import subprocess

import pytest

from tests._app_source import APP_JS_TAG, ROOT, app_js_files, app_source

NODE = shutil.which('node')

# El orden de carga documentado (CLAUDE.md). Nuevo código de app.html va al archivo que corresponda, nunca a un
# bloque inline nuevo.
APP_JS_ORDER = [
    'engine/app_main.js',          # antes bloque 2: núcleo (i18n, tema, NRS, mapa d3, pestañas, precios, 🩺, arranque)
    'engine/app_coordinator.js',   # antes bloque 6: Khipu Core Coordinator + Análisis/Terminal/Simulación
    'engine/app_trade_panel.js',   # antes bloque 7: panel de trading profesional
    'engine/app_preflight.js',     # antes bloque 8: preflight de la simulación
    'engine/app_canvas.js',        # antes bloque 9: Khipu Canvas IA
    'engine/app_scatter.js',       # antes bloque 10: dispersión semántica 3D
]
INLINE_LEFT = 4                    # bloques que siguen inline (ver docstring)
INLINE_BEFORE = 10                 # bloques inline que tenía app.html antes de partirlo


def _r(*p):
    with open(os.path.join(ROOT, *p), encoding='utf-8', newline='') as f:
        return f.read()


def _inline_blocks(html):
    return re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S)


def test_orden_documentado_y_sin_huerfanos():
    assert app_js_files() == APP_JS_ORDER
    on_disk = sorted('engine/' + f for f in os.listdir(os.path.join(ROOT, 'engine')) if re.fullmatch(r'app_[a-z0-9_]+\.js', f))
    assert on_disk == sorted(APP_JS_ORDER)          # ningún engine/app_*.js suelto sin cargar


def test_scripts_clasicos_en_el_mismo_lugar():
    html = _r('app.html')
    # cada etiqueta, exactamente una vez y SIN atributos extra (defer/async/type=module cambiarían el orden/ámbito)
    for f in APP_JS_ORDER:
        assert len(re.findall(r'<script[^>]*\bsrc="' + re.escape(f) + r'[^"]*"[^>]*>', html)) == 1, f
        assert html.count('<script src="%s"></script>' % f) == 1, f
    pos = {f: html.index('<script src="%s"></script>' % f) for f in APP_JS_ORDER}
    order = [pos[f] for f in APP_JS_ORDER]
    assert order == sorted(order)
    # vecinos: el núcleo corre tras el catálogo (merge_graph) y antes de los módulos engine/*; el resto, al final
    assert html.index('<script src="nodes/merge_graph.js"></script>') < pos['engine/app_main.js']
    assert pos['engine/app_main.js'] < html.index('<script src="engine/loading.js"></script>')
    assert html.index('<script src="sim/scenario_builder.js"></script>') < pos['engine/app_coordinator.js']
    # la seguridad compartida sigue siendo el PRIMER bloque inline, antes de todo el JS propio
    first = re.search(r'<script(?![^>]*\bsrc=)[^>]*>', html)
    assert first.start() < pos['engine/app_main.js']
    assert 'Seguridad compartida del cliente' in _inline_blocks(html)[0]


def test_cuenta_de_bloques_y_reconstruccion():
    html = _r('app.html')
    assert len(_inline_blocks(html)) == INLINE_LEFT
    src = app_source()
    assert len(_inline_blocks(src)) == INLINE_BEFORE
    assert not APP_JS_TAG.search(src)
    for f in APP_JS_ORDER:
        body = _r(f)
        assert '</script' not in body.lower() and '<!--' not in body, f   # re-inline seguro (y así era inline)
        assert '<script>' + body + '</script>' in src, f


def test_en_el_shell_del_service_worker():
    sw = _r('sw.js')
    shell = sw[sw.index('const SHELL'):sw.index('];', sw.index('const SHELL'))]
    for f in APP_JS_ORDER:
        assert "'/%s'" % f in shell, f



def _fingerprints():
    import hashlib
    # \r\n → \n: en Windows git puede bajar los archivos con CRLF (mismo código, misma huella)
    return {f: hashlib.sha256(_r(f).encode('utf-8').replace(b'\r\n', b'\n')).hexdigest() for f in APP_JS_ORDER}


def _cache_num(c):
    return int(re.fullmatch(r'khipu-finance-v(\d+)', c).group(1))


def test_cambiar_app_js_exige_subir_sw():
    """Hallazgo de revisión (G5-06): antes este código iba DENTRO de app.html, que se sirve siempre fresco; ahora va en
    engine/app_*.js?v=<N de sw.js>, inmutable 1 año y servido por el SW desde su copia exacta. Editarlo sin subir CACHE
    = HTML nuevo con JS viejo. tests/app_js_fingerprint.json guarda la huella de los 6 archivos junto al CACHE con que
    se publicaron: si cambian, hace falta una entrada NUEVA con un CACHE mayor (y ese CACHE debe ser el de sw.js)."""
    doc = json.loads(_r('tests', 'app_js_fingerprint.json'))
    hist = doc['history']
    nums = [_cache_num(h['cache']) for h in hist]
    assert nums == sorted(set(nums)), 'history: cada entrada con un CACHE mayor que la anterior (añadir, nunca editar)'
    cur = re.search(r"const CACHE = '(khipu-finance-v\d+)'", _r('sw.js')[:2048]).group(1)
    assert _cache_num(cur) >= nums[-1], (cur, hist[-1]['cache'])
    now = _fingerprints()
    if now == hist[-1]['sha256']:
        return
    entry = json.dumps({'cache': cur, 'sha256': now}, ensure_ascii=False, indent=1)
    if cur == hist[-1]['cache']:
        pytest.fail('engine/app_*.js cambió pero CACHE de sw.js sigue en %s: súbelo (vN → vN+1) y añade al final de '
                    'tests/app_js_fingerprint.json "history" la entrada con el CACHE nuevo y estas huellas:\n%s'
                    % (cur, entry))
    pytest.fail('engine/app_*.js cambió con CACHE %s: añade al final de tests/app_js_fingerprint.json "history":\n%s'
                % (cur, entry))


@pytest.mark.skipif(not NODE, reason='node no instalado')
def test_compilan():
    for f in APP_JS_ORDER:
        r = subprocess.run([NODE, '--check', os.path.join(ROOT, f)], capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, (f, r.stderr)
    code = ("const vm=require('vm');const bs=JSON.parse(require('fs').readFileSync(0,'utf8'));"
            "bs.forEach((b,i)=>{try{new vm.Script(b,{filename:'inline'+(i+1)})}catch(e){console.error(i+1,e.message);process.exitCode=1}});")
    r = subprocess.run([NODE, '-e', code], input=json.dumps(_inline_blocks(_r('app.html'))),
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
