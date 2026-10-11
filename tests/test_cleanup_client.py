"""Limpieza 2026-10-11 ("que no queden cosas sueltas"), lado cliente. Cada prueba fija un arreglo del
inventario: §5 estilos de carga repetidos · §6 Cabina clásica forzada a oscuro · §10 "Pensando" que no
cambiaba de idioma · §11 el 🩺 decía "Claude = IA principal" · §16 código viejo cargado en cada arranque ·
§17 tres pantallas llamadas "Investigación" · §7 PIN en claro y diálogos nativos en app.html · el gráfico
intradía del panel de operaciones llamaba a una ruta inexistente."""
import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel):
    return open(os.path.join(ROOT, rel), encoding='utf-8').read()


HTML = _read('app.html')
CK = _read('engine/cockpit.js')


def test_cabina_clasica_sigue_el_tema():
    assert 'kos-classic,' not in CK and '#bcp-ov.kos-classic' not in CK
    assert ':not(.kos-classic)' not in _read('engine/khipu_chat.js')


def test_cargadores_sin_copia_de_colores():
    assert '#bcp-ov .khl-spin{' not in CK and '#bcp-ov .khl-step.now{' not in CK
    assert '#bcp-ov .khl-title{font-weight:800}' in CK


def test_pildora_de_estado_se_re_traduce():
    assert "setState('think', L('" not in CK                      # textos fijos del chat → setStateL (la voz se repinta aparte)
    for es, en in (('Investigando', 'Researching'), ('Pensando', 'Thinking')):
        assert f"setStateL('think', '{es}', '{en}')" in CK
    rel = CK[CK.index('function relabelShell('):CK.index('function _paintThemeBtn(')]
    assert 'st._lbl' in rel


def test_diagnostico_muestra_la_ruta_real_de_la_ia():
    assert "why:'IA principal" not in HTML and 'Canal de respaldo de IA' not in HTML
    assert 'd.ai_model' not in HTML and "_diagCard(k, d.services[k], d.routing)" in HTML
    src = HTML[HTML.index('function _diagAiRole('):HTML.index('function _diagCard(')]
    script = src + r'''
function _sysEN(){ return false; }
const R = { fast: ['gemini', 'claude', 'nvidia'], deep: ['claude', 'gemini', 'nvidia'],
            models: { fast: 'claude-haiku-4-5', deep: 'claude-sonnet-5-5', gemini: 'gemini-3.8-flash' } };
process.stdout.write(JSON.stringify({ g: _diagAiRole('gemini', R), c: _diagAiRole('claude', R), none: _diagAiRole('gemini', null) }));
'''
    r = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out['g'].startswith('Rápido (chat): 1.º') and 'Profundo (investigación): respaldo 1' in out['g'] and 'gemini-3.8-flash' in out['g']
    assert 'Profundo (investigación): 1.º' in out['c'] and 'claude-sonnet-5-5' in out['c']
    assert out['none'] == ''
    import server
    assert 'routing' in server.diagnostics.__code__.co_names or "'routing': _ai_route_now()" in _read('server.py')


def test_codigo_viejo_no_se_carga_al_arrancar():
    assert not os.path.exists(os.path.join(ROOT, 'engine', 'geosituation.js'))
    assert 'geosituation' not in HTML and 'geosituation' not in _read('sw.js')
    for f in ('graph3d.js', 'hypergraph.js'):
        assert f'<script src="engine/{f}"></script>' not in HTML, f          # se descargan al pedir ?webgl3d=1
    assert "one('engine/graph3d.js')" in HTML and "one('engine/hypergraph.js')" in HTML
    assert 'data-i18n="hg_add"' in HTML and "hg_add:'+ Event'" in HTML


def test_tres_productos_de_investigacion_tres_nombres():
    meta = CK[CK.index('var KIND_META = {'):CK.index('};', CK.index('var KIND_META = {'))]
    assert "deep: ['🌐', 'Búsqueda profunda', 'Deep search']" in meta
    assert "research: ['💡', 'Tesis rápida', 'Quick thesis']" in meta
    assert "id: 'swarm'" in CK and 'W.KhipuResearch.open(' in CK                  # el equipo de analistas, en el menú
    assert "'/api/thesis/quick'" in CK and '/api/research/deep' not in CK
    assert "@app.route('/api/thesis/quick'" in _read('server.py') and "'/api/research/deep'" not in _read('server.py')


def test_pin_oculto_y_sin_dialogos_nativos_en_app_html():
    ask = HTML[HTML.index('async function askPin()'):HTML.index('function jsonResp(')]
    assert 'password: true' in ask and 'window.prompt' not in ask
    assert 'pin = await askPin()' in HTML and 'var p2 = await askPin()' in HTML
    for rx in (r'window\.(confirm|prompt|alert)\(', r'(?<![\w.$])(confirm|prompt|alert)\('):
        hits = [m.group(0) for m in re.finditer(rx, HTML)]
        assert not hits, hits
    assert "'anónimo'" not in HTML                                               # actor: EL helper khipuActor


def test_grafico_intradia_usa_la_ruta_que_existe():
    assert 'fetch(`/api/chart/' not in HTML
    chart = HTML[HTML.index('async function _tpLoadChart('):HTML.index('window._tpRefreshPositions')]
    assert '/api/candles/${encodeURIComponent(ticker)}?range=1d&interval=5m' in chart and 'data.c' in chart
    assert "@app.route('/api/candles/<ticker>')" in _read('server.py')


def test_segundo_cerebro_bilingue_precio_oficial_y_solo_flujo():
    sb = _read('engine/secondbrain.js')
    assert '_sbL(' in sb and "Keys.has('finnhub')" not in sb and 'Configura Finnhub' not in sb
    assert 'window.quotePx' in sb and 'q.close != null' not in sb               # contrato de MKT.quotes
    assert '_sbFlow(l)' in sb and 'window.NRS_FLOW_TYPES = NRS_FLOW_TYPES;' in HTML  # proveedores = solo FLUJO
    for es in ('>Proveedores<', '>Clientes<', 'Desglose NRS Risk Score', 'Sin noticias disponibles</div>\''):
        assert es not in sb, es
