"""Escenarios de FINANCIACIÓN (IPO / ronda, 2026-10-22, pedido de Fabrizio tras un informe «cualitativo» del chat sobre
la salida a bolsa de OpenAI): el motor entiende «sale a bolsa» como evento de financiación con DOS casos (más pedidos /
recorte de pedidos a los proveedores, % del kernel único aguas arriba), scenario_exposure entrega impact_pct y el
impacto en la cartera (posiciones que pone el SERVIDOR) y el prompt prohíbe decir «no tengo modelo cuantitativo»."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('SECRET_KEY', 'test')


def _cf():
    from core import governance
    return governance.counterfactual({'kernel.params': '2.0.0'})


def test_detecta_evento_de_financiacion_sin_tocar_las_disrupciones():
    from core import scenario_engine as SE
    for q in ('OpenAI sale a bolsa cerca de $852B', '¿Qué pasa si Anthropic hace su IPO?', 'SpaceX goes public',
              'xAI levanta capital en una ronda de financiación'):
        assert SE.detect(q)['event'] == 'capital', q
    for q, ev in (('Taiwan blockade', 'disruption'), ('China prohíbe exportar HBM', 'export_ban'),
                  ('boom de demanda de GPUs', 'boost')):
        assert SE.detect(q)['event'] == ev, q


def test_ipo_de_openai_dos_casos_con_el_kernel_y_solo_openai_como_semilla():
    from core import scenario_engine as SE
    from core import semantic
    snap = semantic._load_snapshot()
    with _cf():
        a = SE.analyze('OpenAI sale a bolsa cerca de $852B', snap)
    assert a['event'] == 'capital' and a['hit'] == [] and a['benefit'] == []
    c = a['cases']
    bull, bear = c['bull']['impacts'], c['bear']['impacts']
    assert bull and bear and c['bear']['method'].startswith('propagate@1 direction=up')
    assert all(x['impact_pct'] > 0 for x in bull) and all(x['impact_pct'] < 0 for x in bear)
    ids = [x['id'] for x in bear]
    assert ids[0] == 'Oracle' and 'Microsoft' in ids             # Microsoft es PROVEEDOR, no semilla
    assert all(x['path'].endswith('OpenAI') for x in bear)
    # el caso desfavorable recorta más (supuesto 50 % vs 30 %) → mismo orden, mayor magnitud
    b = {x['id']: x['impact_pct'] for x in bull}
    assert abs(bear[0]['impact_pct']) > b['Oracle']
    assert 'Supuesto' in c['assumptions']['note_es']
    # la lista principal = lo que está en riesgo (caso desfavorable)
    assert a['impacts'] and all(x['sev'] < 0 for x in a['impacts'])


def test_scenario_exposure_da_porcentajes_y_cartera_del_servidor():
    from core import khipu_chat as K
    ctx = {'portfolio': [{'symbol': 'ORCL', 'shares': 10, 'usd': 1291.3}, {'symbol': 'KO', 'shares': 3, 'usd': 200.0}]}
    # una cartera que escribiera el MODELO se descarta: la pone el servidor desde el contexto
    args = K._server_args('scenario_exposure', {'scenario': 'OpenAI sale a bolsa',
                                                'positions': [{'symbol': 'ORCL', 'usd': 9e9}]}, ctx)
    assert args['positions'] == [{'symbol': 'ORCL', 'usd': 1291.3}, {'symbol': 'KO', 'usd': 200.0}]
    with _cf():
        ok, res = K.execute_tool('scenario_exposure', args)
    assert ok, res
    assert 'impact_pct' in res['impacts'][0] and 'severity' not in res['impacts'][0]
    assert res['engine']['kernel_semver'] == '2.0.0' and 'Quote these numbers' in res['units']
    assert set(res['cases']) == {'bull', 'bear', 'assumptions'}
    pf = res['portfolio']
    assert pf['total_usd'] == 1491.3 and pf['n_untouched'] == 1
    bear = pf['cases']['bear']
    row = bear['positions_touched'][0]
    assert row['symbol'] == 'ORCL' and row['est_usd'] == round(1291.3 * row['impact_pct'] / 100, 2) < 0
    assert pf['cases']['bull']['est_usd'] > 0
    es, en, src, _ = K._note_scenario(res, {}, {})
    assert es.startswith('Caso desfavorable (motor de Khipus): Oracle') and en.startswith('Bear case')


def test_1_0_0_no_inventa_porcentajes():
    from core import khipu_chat as K
    ok, res = K.execute_tool('scenario_exposure', {'scenario': 'OpenAI sale a bolsa',
                                                   'positions': [{'symbol': 'ORCL', 'usd': 100.0}]})
    assert ok and 'severity' in res['impacts'][0] and 'impact_pct' not in res['impacts'][0]
    assert 'cases' not in res and 'portfolio' not in res and 'NOT a percentage' in res['units']


def test_prompt_exige_el_motor_y_los_dos_casos():
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'core', 'khipu_chat.py'),
               encoding='utf-8').read()
    for frag in ('NUNCA digas que no tienes un modelo cuantitativo', 'caso favorable y caso desfavorable',
                 '«En tu cartera»', 'sin dato verificado'):
        assert frag in src, frag


def test_mcp_run_scenario_en_palabras_devuelve_los_dos_casos():
    from mcp_server.ops import t_run_scenario
    with _cf():
        out = t_run_scenario(None, scenario='OpenAI goes public', top=5)
    assert out['scenario']['event'] == 'capital' and out['shocks'] == []
    assert out['cases']['bear']['impacts'][0]['id'] == 'Oracle' and out['cases']['bull']['impacts'][0]['impact_pct'] > 0
    assert 'Assumption' in out['assumptions']
