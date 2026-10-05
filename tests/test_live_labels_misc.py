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
        assert syn == 9          # fuera de la tabla: sin cambio (no se agranda el mapa entero)
    # el tooltip del mapa muestra ingresos de 12 meses EN VIVO antes que la cifra 2025 del catálogo
    assert 'const rv=meta.revenue_ttm_usd_b, liv=rv!=null&&isFinite(+rv);' in s
