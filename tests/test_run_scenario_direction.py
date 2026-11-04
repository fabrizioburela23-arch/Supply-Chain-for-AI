"""tests/test_run_scenario_direction.py — run_scenario con choque de DEMANDA (2026-11-04).

Hallazgo de una corrida real: «los hiperescaladores recortan → ¿cuánto pierde Nvidia?» daba 1 % porque la herramienta
solo propagaba 'down' (el que cae deja de suministrar → sufren sus clientes). El kernel YA tiene 'up' (cliente → proveedor,
fila normalizada con el piso, kernel.params ≥ 2.0.0): ahora run_scenario lo expone con `direction`, y sin él nada cambia."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('SECRET_KEY', 'test')

CUT = [{'id': 'CoreWeave', 'magnitude': 0.5}, {'id': 'Oracle', 'magnitude': 0.4}, {'id': 'OpenAI', 'magnitude': 0.3},
       {'id': 'Meta', 'magnitude': 0.3}, {'id': 'Microsoft', 'magnitude': 0.25}]


def _cf():
    from core import governance
    return governance.counterfactual({'kernel.params': '2.0.0'})


def _hit(out, cid):
    return next((v['impact_pct'] for v in out['victims'] if v['id'] == cid), 0.0)


def test_default_es_down_y_no_cambia():
    from mcp_server.ops import t_run_scenario
    with _cf():
        a = t_run_scenario(None, shocks=CUT, top=100)
        b = t_run_scenario(None, shocks=CUT, top=100, direction='down')
    assert a['direction'] == 'down' and 'SUPPLY' in a['direction_meaning']
    assert [(v['id'], v['impact_pct']) for v in a['victims']] == [(v['id'], v['impact_pct']) for v in b['victims']]


def test_up_llega_al_proveedor_y_down_casi_no():
    from mcp_server.ops import t_run_scenario
    with _cf():
        up = t_run_scenario(None, shocks=CUT, top=100, direction='up')
        down = t_run_scenario(None, shocks=CUT, top=100)
    assert up['direction'] == 'up' and 'DEMAND' in up['direction_meaning']
    assert _hit(up, 'Nvidia') > 10 > _hit(down, 'Nvidia')       # el caso real: ~21 % contra ~1 %


def test_up_sin_release_que_lo_habilite_es_un_error_claro():
    from mcp_server.ops import ToolError, t_run_scenario
    with pytest.raises(ToolError):
        t_run_scenario(None, shocks=CUT, direction='up')            # kernel.params 1.0.0 (el vigente en la prueba)
