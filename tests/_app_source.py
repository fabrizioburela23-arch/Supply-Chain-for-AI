"""tests/_app_source.py — el TEXTO de app.html tal como era antes de partirlo (G5-06).

app.html carga su JS propio desde engine/app_*.js con `<script src="engine/app_X.js"></script>` en el MISMO lugar
donde estaba cada bloque inline. app_source() vuelve a poner cada archivo dentro de su `<script>…</script>`:
el resultado es byte a byte el app.html de antes, así que las pruebas que buscan texto, extraen un bloque o lo
corren en node siguen comprobando EXACTAMENTE lo mismo. Las pruebas del orden de carga real (sw.js SHELL, posición
de los <script src>) y la cuenta de bloques inline leen app.html crudo a propósito.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_JS_TAG = re.compile(r'<script src="(engine/app_[a-z0-9_]+\.js)"></script>')


def _read(p):
    with open(p, encoding='utf-8', newline='') as f:
        return f.read()


def app_js_files(root=ROOT):
    """Los engine/app_*.js que app.html carga, en orden."""
    return APP_JS_TAG.findall(_read(os.path.join(root, 'app.html')))


def app_source(root=ROOT):
    html = _read(os.path.join(root, 'app.html'))
    return APP_JS_TAG.sub(lambda m: '<script>' + _read(os.path.join(root, m.group(1))) + '</script>', html)
