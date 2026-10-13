"""tests/test_review_batch_e.py — revisión del batch E (2026-10-13): lo que se ve en el navegador.

  · FACTOR <id> FIRE: la animación convierte la severidad de crisis con la ESCALA que devuelve el servidor
    (kernel 1.0.0 → 0-5, 2.0.0 → 0-10), nunca con un /5 fijo, y nunca pasa de 100 %;
  · la tarjeta de Gobernanza solo avisa «Cambio mayor» al activar una versión NUEVA y mayor (no al volver atrás);
  · el reporte de riesgo muestra la fuente de los datos en el idioma elegido (source_es / source_en).
"""
import os
from tests._app_source import app_source  # noqa: E402
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


def test_factor_fire_usa_la_escala_del_servidor():
    src = _read('engine/khipu_lang.js')
    assert 'severity_crisis / 5)' not in src
    assert 'r.factor.severity_scale' in src and 'Math.min(100' in src
    app = app_source()
    assert 'severity_crisis)}/5)' not in app and 'r.factor.severity_scale || 5' in app


@pytest.mark.skipif(not shutil.which('node'), reason='requiere node')
@pytest.mark.parametrize('crisis,scale,want', [(4, 5, 80), (4, 10, 40), (10, 10, 100), (10, 5, 100), (4, None, 80)])
def test_factor_fire_porcentaje_de_la_animacion(crisis, scale, want):
    """El mismo cálculo que khipu_lang.js (extraído del archivo) con la respuesta del servidor."""
    src = _read('engine/khipu_lang.js')
    m = re.search(r"const scale = (.+?);\n\s*const sev = (.+?);\n", src)
    assert m, 'no se encontró el cálculo de la escala en khipu_lang.js'
    js = (f"const r = {{factor: {{severity_crisis: {crisis}, severity_scale: {'null' if scale is None else scale}}}}};"
          f"const scale = {m.group(1)}; const sev = {m.group(2)}; process.stdout.write(String(sev));")
    out = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=20)
    assert out.returncode == 0, out.stderr
    assert int(out.stdout) == want


def test_aviso_de_cambio_mayor_solo_para_una_version_nueva():
    src = _read('engine/governance.js')
    assert 'warnHtml: major ?' in src
    assert re.search(r"var major = !!prop\.newer && \(prop\.four_eyes === 'unavailable' \|\| prop\.change_kind === "
                     r"'major'\);", src)


def test_reporte_de_riesgo_fuente_bilingue():
    js = _read('engine/riskreport.js')
    assert 'r.source_en' in js and 'r.source_es' in js
    py = _read('core/risk_report.py')
    assert "rep['source_en']" in py and "rep['source_es']" in py
