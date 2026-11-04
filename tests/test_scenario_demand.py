"""tests/test_scenario_demand.py — texto libre de DEMANDA (2026-11-04). Hallazgo de una corrida real: «Nvidia reporta débil»
sembraba a Nvidia misma al 100 % como si dejara de suministrar. Ahora es un evento 'demand': la empresa nombrada (o los
hiperescaladores) COMPRA menos y el golpe va aguas arriba, a sus proveedores, con UN caso de recorte rotulado como supuesto."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('SECRET_KEY', 'test')


def _cf():
    from core import governance
    return governance.counterfactual({'kernel.params': '2.0.0'})


@pytest.mark.parametrize('q', ['Nvidia reporta resultados débiles el 17 de noviembre', 'los hiperescaladores recortan capex',
                               'Meta cancela pedidos de GPUs', 'Nvidia earnings miss', 'hyperscalers cut capex',
                               'caída de la demanda de GPUs'])
def test_detecta_demanda(q):
    from core import scenario_engine as SE
    assert SE.detect(q)['event'] == 'demand', q


@pytest.mark.parametrize('q,ev', [('China blockades Taiwan', 'disruption'), ('OpenAI sale a bolsa', 'capital'),
                                  ('China prohíbe exportar HBM', 'export_ban'), ('boom de demanda de GPUs', 'boost'),
                                  ('terremoto en Taiwán', 'disruption')])
def test_no_toca_los_otros_eventos(q, ev):
    from core import scenario_engine as SE
    assert SE.detect(q)['event'] == ev, q


def test_reporta_debil_no_siembra_a_la_empresa_y_golpea_a_sus_proveedores():
    from core import scenario_engine as SE, semantic
    with _cf():
        a = SE.analyze('Nvidia reporta resultados débiles el 17 de noviembre', semantic._load_snapshot(), lang='es')
    assert a['event'] == 'demand' and not a.get('hit')                      # nadie «deja de suministrar»
    bear = a['cases']['bear']['impacts']
    assert bear and all(x['id'] != 'Nvidia' for x in bear) and all(x['impact_pct'] < 0 for x in bear)
    assert 'bull' not in a['cases'] and 'No es un pronóstico de precio' in a['cases']['assumptions']['note_es']


def test_hiperescaladores_recortan_llega_a_nvidia_con_el_motor():
    from core import scenario_engine as SE, semantic
    with _cf():
        a = SE.analyze('los hiperescaladores recortan capex', semantic._load_snapshot(), lang='es')
    got = {x['id']: x['impact_pct'] for x in a['cases']['bear']['impacts']}
    assert got.get('Nvidia', 0) < -10                                      # antes de este arreglo: ~ -1 %


def test_mcp_en_palabras_devuelve_el_caso_de_recorte():
    from mcp_server.ops import t_run_scenario
    with _cf():
        out = t_run_scenario(None, scenario='hyperscalers cut capex', top=5)
    assert out['scenario']['event'] == 'demand' and out['shocks'] == []
    assert list(k for k in out['cases'] if k != 'assumptions') == ['bear']
