"""Mapa (2026-10-05): buscar una empresa, elegirla y deseleccionarla dejaba encendida SOLO esa empresa hasta
recargar. Causa: pickSugg limpiaba searchTerm pero no el filtro guardado (buildFilterCache seguía con "nvid")."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_elegir_una_sugerencia_invalida_el_filtro_guardado():
    h = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()
    m = re.search(r'function pickSugg\(id\)\{([\s\S]*?)\n\}', h)
    assert m and 'invalidateFilterCache()' in m.group(1)
    assert m.group(1).index("searchTerm=''") < m.group(1).index('invalidateFilterCache()')


def test_nrs_cliente_acota_margen_y_reconoce_paises():
    h = open(os.path.join(ROOT, 'app.html'), encoding='utf-8').read()
    for fn in ('function computeNRS(', 'function computeNRSBreakdown('):
        body = h[h.index(fn):h.index(fn) + 2500]
        assert 'Math.max(0, Math.min(20, Math.round((1 - Math.min(1, margin / 0.4)) * 20)))' in body, fn
        assert '_nrsCountry(n.country)' in body, fn
