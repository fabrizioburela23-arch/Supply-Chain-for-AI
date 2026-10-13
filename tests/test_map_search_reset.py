"""Mapa (2026-10-05): buscar una empresa, elegirla y deseleccionarla dejaba encendida SOLO esa empresa hasta
recargar. Causa: pickSugg limpiaba searchTerm pero no el filtro guardado (buildFilterCache seguía con "nvid")."""
import os
from tests._app_source import app_source  # noqa: E402
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_elegir_una_sugerencia_invalida_el_filtro_guardado():
    h = app_source()
    m = re.search(r'function pickSugg\(id\)\{([\s\S]*?)\n\}', h)
    assert m and 'invalidateFilterCache()' in m.group(1)
    assert m.group(1).index("searchTerm=''") < m.group(1).index('invalidateFilterCache()')


def test_nrs_cliente_acota_margen_y_reconoce_paises():
    h = app_source()
    # limpieza 2026-10-11: la fórmula vive UNA vez en _nrsTerms; computeNRS y el desglose la usan
    body = h[h.index('function _nrsTerms('):h.index('function _nrsTerms(') + 2500]
    assert 'Math.max(0, Math.min(20, Math.round((1 - Math.min(1, margin / 0.4)) * 20)))' in body
    assert '_nrsCountry(n.country)' in body
    for fn in ('function computeNRS(', 'function computeNRSBreakdown('):
        assert '_nrsTerms(nodeId, n)' in h[h.index(fn):h.index(fn) + 900], fn
