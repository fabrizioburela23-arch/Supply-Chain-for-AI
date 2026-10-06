"""Cifras que el texto daba como actuales (2026-10-05): cripto (supply/dominancia de jul-2026), Insights (margen sin
origen), Guía ("949 empresas" fijo). Ahora: dato vivo arriba, origen rotulado y conteos del catálogo cargado."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _r(p):
    return open(os.path.join(ROOT, p), encoding='utf-8').read()


def test_cripto_expediente_lleva_el_dato_en_vivo():
    s = _r('engine/crypto.js')
    assert 'function liveIntelLine(a)' in s and 'intelHTML(it, a)' in s and 'En vivo (CoinGecko): ' in s


def test_insights_usa_crecimiento_real_y_dice_el_origen_del_margen():
    s = _r('engine/insights.js')
    assert 'n.growth_live' in s and "'en vivo' : 'del catálogo'" in s


def test_guia_cuenta_las_empresas_del_catalogo_cargado():
    s = _r('engine/guide.js')
    assert '.replace(/\\b949\\b/g, String(_nCos()))' in s and 'function _nCos()' in s


def test_mapa_tamano_de_privadas_usa_valuacion_verificada_y_tooltip_ingresos_en_vivo():
    import json
    import re
    import shutil
    import subprocess
    node = shutil.which('node')
    s = _r('app.html')
    fn = re.search(r'function computeNodeRadius\(nodeId\) \{.*?\n\}\n', s, re.S).group(0)
    js = ("const window={NODE_META:{OpenAI:{mktcap_b:852},Synopsys:{mktcap_b:80}},MKT:null};"
          "const NODE_BY_ID={OpenAI:{id:'OpenAI'},Synopsys:{id:'Synopsys'}};const SHARES_OUTSTANDING_B={};"
          + fn + "console.log(JSON.stringify([computeNodeRadius('OpenAI'),computeNodeRadius('Synopsys')]))")
    if node:
        r = subprocess.run([node, '-e', js], capture_output=True, text=True, timeout=20)
        oa, syn = json.loads(r.stdout)
        assert oa == 20          # 852 B verificado (antes 300 B fijo → 19)
        assert syn == 16         # 2026-10-06: TODAS por su capitalización en vivo (antes 9 = "vale 0,5 B")
    # el tooltip del mapa muestra ingresos de 12 meses EN VIVO antes que la cifra 2025 del catálogo
    assert 'const rv=meta.revenue_ttm_usd_b, liv=rv!=null&&isFinite(+rv);' in s


def test_mapa_etiquetas_solo_las_mas_grandes_y_se_redimensiona_con_caps_en_vivo():
    s = _r('app.html')
    assert 'const LBL_MAX = 90;' in s and "function _lblOn(d){ return !!d.big || computeNodeRadius(d.id) >= _lblMinR; }" in s
    assert "window.addEventListener('khipu:livecaps'" in s and 'function _resizeNodesByCap(){' in s
    assert 'computeNodeRadius(d.id) < 13' not in s     # la regla vieja llenaría el mapa de nombres


def test_home_muestra_cada_cartera_con_su_nombre():
    # "¿de qué cartera habla? tengo 2": antes solo la cuenta del bróker, rotulada "Tu cartera"
    s = _r('engine/cockpit.js')
    assert 'function _homePfLines(en)' in s and "P._stats(pf)" in s and 'class="bcp-home-pf"' in s
    assert "(en ? 'Broker account' : 'Cuenta del bróker')" in s
    assert "(en ? 'Your portfolio' : 'Tu cartera') + ': '" not in s
