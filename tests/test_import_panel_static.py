"""tests/test_import_panel_static.py — EXPANSION_5K E2.7: reglas fijas de engine/importer.js (panel 🩺 → 📥 Importar).

  · compila (node --check) y el diccionario T tiene las MISMAS claves en ES y EN, sin textos vacíos; toda clave que el
    código pide con t('…') existe; los códigos del servidor (conflictos, avisos, motivos, tipos de vínculo de
    ontology/company_import.py) tienen su traducción en los dos idiomas;
  · DOM seguro: nada de innerHTML/outerHTML/insertAdjacentHTML/document.write/eval (los datos van como texto);
  · nada de window.confirm/prompt/alert (diálogos SOLO por KhipuToast); el PIN SOLO por window._tradeFetch (ni la
    cabecera ni el PIN guardado se tocan aquí) y toda ruta de escritura del importador sale por pinPost;
  · cada «?» del panel tiene su explicación registrada en engine/explain.js (explainRegister);
  · carga PEREZOSA: app.html no lo trae; engine/app_main.js lo descarga al abrir 🩺 con base de datos (misma ?v=).
"""
import json
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = os.path.join(ROOT, 'engine', 'importer.js')
NODE = shutil.which('node')


def _src():
    with open(JS, encoding='utf-8') as f:
        return f.read()


def _code_only(src):
    """Sin comentarios /* */ ni // (para no contar la documentación como código)."""
    src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    return re.sub(r'(^|[^:\'"\\])//[^\n]*', r'\1', src)


@pytest.fixture(scope='module')
def T():
    if not NODE:
        pytest.skip('node no disponible')
    prog = ("const vm=require('vm');const fs=require('fs');const store={};"
            "const W={localStorage:{getItem:k=>store[k]||null,setItem:(k,v)=>{store[k]=String(v)}}};W.window=W;"
            "const reg={};W.explainRegister=(k,e)=>{reg[k]=e};"
            "vm.createContext(W);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),W);"
            "process.stdout.write(JSON.stringify({T:W.KhipuImporter._T,reg:reg,api:Object.keys(W.KhipuImporter)}));")
    out = subprocess.run([NODE, '-e', prog, JS], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_compila():
    if not NODE:
        pytest.skip('node no disponible')
    r = subprocess.run([NODE, '--check', JS], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr


def test_bilingue_mismas_claves(T):
    es, en = T['T']['es'], T['T']['en']
    assert set(es) == set(en), sorted(set(es) ^ set(en))
    assert all(isinstance(v, str) and v.strip() for v in list(es.values()) + list(en.values()))
    assert {'mount', 'reload', '_T'} <= set(T['api'])
    # mismas variables {x} en las dos versiones de cada texto
    for k in es:
        assert set(re.findall(r'\{(\w+)\}', es[k])) == set(re.findall(r'\{(\w+)\}', en[k])), k


def test_toda_clave_pedida_existe(T):
    used = set(re.findall(r"\bt\('([a-z0-9_]+)'\s*[,)]", _src()))
    missing = used - set(T['T']['es'])
    assert not missing, sorted(missing)


def test_codigos_del_servidor_traducidos(T):
    from ontology import company_import as CI
    es = T['T']['es']
    for prefix, table in (('cf_', CI._CONFLICT_ES), ('r_', CI._REASON_ES), ('w_', CI._WARN_ES), ('rel_', CI._REL_ES)):
        falta = [k for k in table if prefix + k not in es]
        assert not falta, (prefix, falta)
    for route in CI.ROUTES[:3]:
        assert 'route_' + route in es


def test_dom_seguro():
    code = _code_only(_src())
    for bad in ('innerHTML', 'outerHTML', 'insertAdjacentHTML', 'document.write', 'eval(', 'new Function'):
        assert bad not in code, bad


def test_sin_dialogos_nativos_y_pin_solo_por_tradefetch():
    code = _code_only(_src())
    assert not re.search(r'(?<![.\w])(confirm|prompt|alert)\s*\(', code)
    assert not re.search(r'window\.(confirm|prompt|alert)\b|W\.(confirm|prompt|alert)\b', code)
    for bad in ('X-Trade-Pin', 'x-trade-pin', '_tradePinStored', 'khipu_trade_pin', '_tradePinSave'):
        assert bad not in code, bad
    assert 'W._tradeFetch' in code
    for route in ('apply', 'rollback', 'files', 'plan'):
        hits = [m.start() for m in re.finditer(r"'/api/ontology/import/%s'" % route, code)]
        assert hits, route
        for pos in hits:
            assert code[max(0, pos - 40):pos].rstrip().endswith('pinPost('), (route, code[pos - 60:pos + 40])
    # las lecturas (lista, plan del paquete, corridas) van SIN PIN (fetch normal)
    assert "getJSON('/api/ontology/import/packages')" in code
    assert "getJSON('/api/ontology/import/packages/plan?package=' + encodeURIComponent(" in code
    assert "getJSON('/api/ontology/import/runs" in code


def test_cada_signo_de_pregunta_tiene_explicacion(T):
    keys = set(re.findall(r"\bq\('([a-z_]+)'\)", _src())) | set(re.findall(r"\bsec\([^)]*?,\s*'([a-z_]+)'\)", _src()))
    assert keys and keys <= set(T['reg']), sorted(keys - set(T['reg']))
    for k in T['reg']:
        assert T['reg'][k]['es']['t'] and T['reg'][k]['en']['t'] and T['reg'][k]['es']['b'] and T['reg'][k]['en']['b']


def test_carga_perezosa_desde_el_diagnostico():
    with open(os.path.join(ROOT, 'app.html'), encoding='utf-8') as f:
        html = f.read()
    assert 'engine/importer.js' not in html                       # no se descarga al abrir la app
    with open(os.path.join(ROOT, 'engine', 'app_main.js'), encoding='utf-8') as f:
        main = f.read()
    assert "el.src = 'engine/importer.js' + (v ? '?' + v[1] : '');" in main
    diag = main[main.index('window.openDiagnostics = async function'):]
    diag = diag[:diag.index('\n};')]
    assert 'd.services.ontologia.configured) _sysImporter()' in diag


def test_tokens_de_khipus_os():
    src = _src()
    assert "classList.add('kos-themed')" in src
    css = src[src.index("st.textContent ="):src.index("document.head.appendChild(st)")]
    # colores SOLO como respaldo de un token --os-* (nada de colores sueltos)
    for m in re.finditer(r'#[0-9A-Fa-f]{3,8}\b', css):
        before = css[max(0, m.start() - 40):m.start()]
        assert 'var(--os-' in before, css[m.start() - 60:m.end() + 5]
    assert 'prefers-reduced-motion' in css and 'max-width:480px' in css


def test_huella_sha256_en_js_puro_igual_a_hashlib():
    """Sin crypto.subtle (página en http) la huella del archivo subido sale del SHA-256 en JS puro: debe ser IDÉNTICA
    a la que calcula el servidor (hashlib), en todos los bordes de relleno (55/56/63/64 bytes…)."""
    import hashlib
    if not NODE:
        pytest.skip('node no disponible')
    sizes = [0, 1, 55, 56, 63, 64, 65, 119, 120, 1000, 70001]
    prog = ("const vm=require('vm'),fs=require('fs');const W={localStorage:{getItem:()=>null,setItem:()=>{}}};W.window=W;"
            "vm.createContext(W);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),W);"
            "const out={};for(const n of JSON.parse(process.argv[2])){const b=new Uint8Array(n);"
            "for(let i=0;i<n;i++)b[i]=(i*31+7)&255;out[n]=W.KhipuImporter._sha256(b);}"
            "process.stdout.write(JSON.stringify(out));")
    r = subprocess.run([NODE, '-e', prog, JS, json.dumps(sizes)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    got = json.loads(r.stdout)
    for n in sizes:
        assert got[str(n)] == hashlib.sha256(bytes((i * 31 + 7) & 255 for i in range(n))).hexdigest(), n
