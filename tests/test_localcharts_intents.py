"""Gráficos instantáneos (engine/localcharts.js, 2026-10-05): preguntas típicas que caían a la IA (o fallaban)
por palabras no reconocidas — "promedio", "semiconductores", "desglosado", "oro"."""
import json
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_sector_promedio_y_materias_primas_se_resuelven_sin_ia():
    r = subprocess.run([NODE, os.path.join(ROOT, 'tests/js/localcharts_intents.js'), ROOT], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    o = json.loads(r.stdout)
    assert o['precio del oro último año'] == {'intent': 'trend', 'local': True, 'sectors': None, 'commodity': 'GC=F'}
    assert o['top 5 semiconductores por margen']['sectors'] == ['fabricacion', 'diseno', 'equipos'] and o['top 5 semiconductores por margen']['local']
    assert o['margen promedio por sector']['local'] is True
    assert o['gold'] == {'type': 'line', 'title': 'Oro (GC=F) — precio, 1 año', 'n': 6}


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_rendimiento_de_mi_cartera_es_grafico_local_con_cierres_reales():
    r = subprocess.run([NODE, os.path.join(ROOT, 'tests/js/localcharts_pfperf.js'), ROOT], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    o = json.loads(r.stdout)
    for q in ('rendimiento de mi cartera', 'cuánto ganó mi cartera este año', 'how is my portfolio doing'):
        assert o[q] == {'intent': 'trend', 'local': True, 'pfPerf': True}, q
    assert o['mi cartera']['intent'] == 'composition'          # sin "rendimiento" sigue siendo el reparto
    assert o['por qué perdió mi cartera']['local'] is False    # el "por qué" sigue yendo a la IA
    c = o['chart']
    assert c['type'] == 'line' and c['vals'] == [600, 620, 650]   # 2×NVDA + 1×LMT (LMT arrastra su cierre)
    assert '+8.3%' in c['sub'] and '+$70' in c['sub'] and '+11.7%' in c['sub']   # hoy (en vivo) vs costo
    assert 'OpenAI' in c['note']                                 # no cotiza → se dice, no se inventa
