"""Canvas nivel Power BI (2026-10-06): paleta validada, tooltip/cruz al pasar el mouse, vista de tabla y CSV."""
import json
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')
HTML = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()


def test_paleta_validada_y_sin_ciclos():
    # validate_palette.js (dataviz): oscuro sobre #2B241A y claro sobre #E9E2D4 → todas las pruebas en verde
    assert "const CV_PAL_D = ['#3987e5','#d95926','#199e70','#c98500','#d55181','#008300','#9085e9','#e66767'];" in HTML
    assert "const CV_PAL_L = ['#2a78d6','#eb6834','#1baf7a','#eda100','#e87ba4','#008300','#4a3aa7','#e34948'];" in HTML
    assert 'return i<p.length?p[i]:CV_OTHER;' in HTML and 'CV_PAL[i % CV_PAL.length]' not in HTML
    lc = open(os.path.join(ROOT, 'engine', 'localcharts.js'), encoding='utf-8').read()
    assert 'PAL[i % PAL.length]' not in lc and 'window.cvCol(i)' in lc


def test_barras_de_una_serie_en_un_color_y_mapa_de_calor_de_un_tono():
    assert "const col=d.color||cvCol(0), v=d.value" in HTML            # antes cvCol(i): arcoíris sin significado
    assert "function lerp(t){ return cvSeq(t,hue); }" in HTML           # antes azul→verde→ámbar→rojo


def test_interaccion_tooltip_cruz_tabla_csv():
    assert 'class="cv-hit"' in HTML and "hit.addEventListener('mousemove',at)" in HTML     # cruz en líneas
    assert "closest('.cv-body [data-tip]')" in HTML                                        # tooltip compartido
    assert 'data-cvact="table"' in HTML and 'data-cvact="csv"' in HTML and 'function cvDownloadCSV(spec)' in HTML
    for k in ("asTable:'Ver como tabla'", "asTable:'View as table'", "csv:'Descargar CSV'", "csv:'Download CSV'"):
        assert k in HTML, k


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_cvrows_convierte_cada_tipo_en_filas():
    grab = lambda rx: re.search(rx, HTML, re.S).group(0)  # noqa: E731
    src = '\n'.join([grab(r'const CV_T = \{.*?\n\};'), grab(r'function cvT\(k\)\{.*?\}\n'), grab(r'function cvRows\(spec\)\{.*?\n\}\n')])
    js = 'global.window={LANG:"es"};' + src + r'''
const out = {
  line: cvRows({type:'line', data:[{label:'A',values:[1,2]},{label:'B',values:[3,null]}], config:{labels:['ene','feb'], series_labels:['A','B']}}),
  bar: cvRows({type:'bar', data:[{label:'Nvidia',value:62},{label:'AMD',value:'12'}], config:{unit:'%'}}),
  grouped: cvRows({type:'grouped', data:[{label:'Margen',values:[62,12]}], config:{series_labels:['Nvidia','AMD']}}),
  heat: cvRows({type:'heatmap', data:[{row:'EEUU',col:'Nube',value:28}], config:{rows:['EEUU'],cols:['Nube','Diseño']}}),
  scatter: cvRows({type:'scatter', data:[{label:'TSMC',x:49,y:60}], config:{x_label:'Margen',y_label:'NRS'}}),
};
process.stdout.write(JSON.stringify(out));'''
    r = subprocess.run([NODE, '-e', js], capture_output=True, text=True, timeout=20)
    assert r.returncode == 0, r.stderr
    o = json.loads(r.stdout)
    assert o['line']['cols'] == ['Periodo', 'A', 'B'] and o['line']['raw'] == [['ene', 1, 3], ['feb', 2, None]]
    assert o['bar']['cols'] == ['', 'Valor (%)'] and o['bar']['raw'] == [['Nvidia', 62], ['AMD', 12]]
    assert o['grouped']['raw'] == [['Margen', 62, 12]]
    assert o['heat']['cols'] == ['', 'Nube', 'Diseño'] and o['heat']['raw'] == [['EEUU', 28, None]]
    assert o['scatter']['cols'] == ['', 'Margen', 'NRS'] and o['scatter']['raw'] == [['TSMC', 49, 60]]
