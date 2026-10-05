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
