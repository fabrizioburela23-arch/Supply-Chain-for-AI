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
