"""Las cifras que CLAUDE.md afirma, comparadas con el código (limpieza 2026-10-11, §12).

CLAUDE.md es la memoria entre sesiones: si dice "949 nodos" o "13 Acciones" cuando ya son 937 y 17, la
próxima sesión trabaja con datos falsos. Al cambiar el catálogo, las Acciones, los agentes de la ontología,
los bloques inline de app.html o las pestañas, esta prueba pide actualizar el texto."""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel):
    return open(os.path.join(ROOT, rel), encoding='utf-8').read()


DOC = _read('CLAUDE.md')


def _es(n):
    return f'{n:,}'.replace(',', '.')


def test_conteos_del_catalogo():
    counts = json.load(open(os.path.join(ROOT, 'data', 'grafo_v0.json'), encoding='utf-8'))['counts']
    head = DOC[:600]
    assert f"{counts['nodes']} nodos en el catálogo" in head and f"{_es(counts['links'])} relaciones" in head
    assert f"snapshot canónico ({counts['nodes']} nodos / {_es(counts['links'])} links" in DOC


def test_acciones_y_agentes_de_la_ontologia():
    from ontology.actions import ACTION_CATALOG
    from ontology.agents import AGENTS
    assert f'catálogo de {len(ACTION_CATALOG)} Acciones' in DOC
    assert f'({len(AGENTS)} agentes + brief matinal' in DOC


def test_bloques_inline_y_pestanas_de_app_html():
    html = _read('app.html')
    n = len(re.findall(r'<script(?![^>]*\bsrc=)[^>]*>', html))
    assert f'{n} bloques `<script>`' in DOC
    from core.khipu_chat import TABS
    arch = DOC[DOC.index('- `app.html` ('):DOC.index('- `server.py` (')]
    for t in TABS:
        assert t in arch, t


def test_nombre_de_la_app():
    assert 'App: **Khipus Finance Intelligence**' in DOC
    assert _read('README.md').startswith('# Khipus Finance Intelligence')
