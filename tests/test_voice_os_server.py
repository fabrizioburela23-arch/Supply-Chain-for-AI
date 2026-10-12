"""Voz para Khipus OS (2026-10-11), lado servidor — contrato v2 de las herramientas de Khipu (voz).

Antes la voz tenía 31 herramientas pensadas para las pestañas viejas: abría "pestañas" que ya no existen,
decía SIEMPRE "dinero de papel" aunque la cuenta del bróker podía ser real y sus respuestas no aparecían en
el chat central. Ahora son 17 (respuestas al chat central, pantallas como ventanas, dinero con la verdad
del resultado) y la sincronización SUELTA del agente de ElevenLabs las retiradas. Estas pruebas fijan:
  · las 17 herramientas, sin nombres retirados, con enums cerrados y descripciones en cada parámetro;
  · las pantallas de open_screen = las del menú Herramientas de engine/cockpit.js, con el MISMO nombre visible;
  · los agentes de ask_khipu_brain = los del registro único (sin Khipu);
  · las instrucciones: cada herramienta explicada, ninguna retirada, tres productos de investigación con su
    nombre, el dinero según "mode" (papel/real), PIN en pantalla, sin `{{ }}` (variables de ElevenLabs).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('SECRET_KEY', 'test-secret-key')

import server  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECTED = ['ask_khipu_brain', 'open_company', 'get_company_info', 'open_screen', 'compare_companies',
            'run_live_simulation', 'run_agent_simulation', 'show_opportunities', 'create_visualization',
            'quick_thesis', 'deep_search', 'place_order', 'open_order_ticket', 'get_account_status',
            'get_space_summary', 'run_guided_demo', 'control_interface']


def _specs():
    return {t['name']: t for t in server._bixby_client_tools()}


def _enum(tool, prop):
    return _specs()[tool]['parameters']['properties'][prop]['enum']


def test_diecisiete_herramientas_sin_retiradas():
    specs = server._bixby_client_tools()
    names = [t['name'] for t in specs]
    assert names == EXPECTED
    assert not set(names) & set(server.RETIRED_VOICE_TOOLS)
    assert len(set(server.RETIRED_VOICE_TOOLS)) == len(server.RETIRED_VOICE_TOOLS) == 25
    for t in specs:
        assert t['type'] == 'client' and t['expects_response'] is True and len(t['description']) > 40, t['name']
        params = t['parameters']
        assert set(params['required']) <= set(params['properties']), t['name']
        for k, prop in params['properties'].items():
            assert prop.get('description'), (t['name'], k)
            if 'enum' in prop:
                assert prop['type'] == 'string' and len(set(prop['enum'])) == len(prop['enum']) >= 2
    assert set(server._VOICE_TOOL_TIMEOUTS) <= set(names)
    assert all(1 <= v <= 120 for v in server._VOICE_TOOL_TIMEOUTS.values())


def test_contrato_de_parametros():
    s = _specs()
    assert s['ask_khipu_brain']['parameters']['required'] == ['question']
    assert _enum('open_company', 'view') == ['glance', 'xray', 'supply_chain', 'map', 'chart', 'dossier',
                                             'research', 'committee']
    assert _enum('run_live_simulation', 'kind') == ['collapse', 'demand', 'price', 'sanction']
    assert _enum('place_order', 'side') == ['buy', 'sell']
    assert set(s['place_order']['parameters']['required']) >= {'symbol_or_name', 'side', 'confirmed'}
    assert s['place_order']['parameters']['properties']['confirmed']['type'] == 'boolean'
    assert _enum('run_agent_simulation', 'preset') == list(server.VOICE_SIM_PRESETS)
    assert s['run_agent_simulation']['parameters']['required'] == []          # escenario O preset
    assert _enum('control_interface', 'action') == list(server.VOICE_UI_ACTIONS)
    assert 'classic' not in ' '.join(server.VOICE_UI_ACTIONS)                 # nunca saca al usuario de Khipus OS


def test_presets_de_simulacion_son_los_de_scenario_builder():
    js = open(os.path.join(ROOT, 'sim', 'scenario_builder.js'), encoding='utf-8').read()
    for p in server.VOICE_SIM_PRESETS:
        assert re.search(rf'\b{p}\s*:', js), p


def test_agentes_de_la_voz_son_los_del_registro_unico():
    from core.agents_registry import AGENTS
    assert _enum('ask_khipu_brain', 'agent') == [a['id'] for a in AGENTS if a['id'] != 'khipu']


def _cockpit_screens():
    js = open(os.path.join(ROOT, 'engine', 'cockpit.js'), encoding='utf-8').read()
    body = js[js.index('function screens() {'):js.index('function _runScreen(id)')]
    return {m[0]: (m[1], m[2]) for m in re.findall(r"id: '(\w+)', ic: '[^']*', es: '([^']*)', en: '([^']*)'", body)}


def test_pantallas_de_la_voz_son_las_del_menu_herramientas():
    cockpit = _cockpit_screens()
    assert len(cockpit) >= 25
    assert _enum('open_screen', 'screen') == list(server.VOICE_SCREENS)
    for k, names in server.VOICE_SCREENS.items():
        assert cockpit.get(k) == names, (k, cockpit.get(k), names)          # mismo nombre VISIBLE que el menú
    # las de una empresa se alcanzan con open_company / compare / quick_thesis / run_live_simulation
    assert set(cockpit) - set(server.VOICE_SCREENS) == {'xray', 'compare', 'swarm', 'research', 'sim'}
    for alias, target in server.VOICE_SCREEN_ALIASES.items():
        assert target in server.VOICE_SCREENS and alias not in server.VOICE_SCREENS


def _words(text):
    return set(re.findall(r'\b[a-z][a-z0-9_]+\b', text))


def test_instrucciones_explican_cada_herramienta_y_ninguna_retirada():
    p = server.BIXBY_SYSTEM_PROMPT
    w = _words(p)
    for name in EXPECTED:
        assert name in w, name
    for name in server.RETIRED_VOICE_TOOLS:
        assert name not in w, name
    assert '{{' not in p and '}}' not in p and '{agents}' not in p and '{screens}' not in p
    for prod in ('Investigación con evidencia', 'Tesis rápida', 'Búsqueda profunda'):
        assert prod in p, prod


def test_instrucciones_dicen_la_verdad_sobre_el_dinero():
    p = server.BIXBY_SYSTEM_PROMPT
    money = p[p.index('## MONEY'):p.index('## DOMAIN KNOWLEDGE')]
    assert '"mode"' in money and 'paper' in money and 'live' in money and 'REAL MONEY' in money
    assert 'Carteras de práctica' in money and 'Mi cuenta (bróker)' in money
    assert 'PIN' in money and 'never ask them to say it aloud' in money
    assert 'confirmed=false' in money and 'confirmed=true' in money and 'NOT a yes' in money
    # la versión vieja afirmaba que SIEMPRE era papel: falso si la cuenta del bróker es real
    assert 'SIMULATED paper-money broker' not in p and 'ALWAYS say clearly that the operation is simulated' not in p
    po = _specs()['place_order']['description']
    assert 'REAL money' in po and '"mode"' in po and 'confirmed=false' in po
    assert 'ALWAYS waits for human approval' in p


def test_instrucciones_hablan_de_ventanas_y_chat_central():
    p = server.BIXBY_SYSTEM_PROMPT
    assert 'CENTER of the screen' in p and 'WINDOW beside the chat' in p
    assert 'SHORT SUMMARY' in p                                          # la respuesta completa queda escrita
    assert 'switch_tab(' not in p and 'tab:' not in p


def test_place_order_acepta_cantidad_y_no_obliga_a_inventar_dolares():
    po = _specs()['place_order']['parameters']
    assert po['properties']['qty']['type'] == 'number'
    assert 'notional_usd' not in po['required'] and 'qty' not in po['required']    # monto en dólares O cantidad
    assert set(po['required']) == {'symbol_or_name', 'side', 'confirmed'}


def test_instrucciones_mencion_de_agente_solo_con_empresa_y_modo_del_dinero():
    p = server.BIXBY_SYSTEM_PROMPT
    tools = p[p.index('## YOUR TOOLS'):p.index('## THE ONE-MINUTE TOUR')]
    assert 'Add agent ONLY when the question is about ONE specific company' in tools
    assert 'go WITHOUT agent' in tools and "ALWAYS write the company's name in the question" in tools
    assert 'news and events → radar' not in p                              # antes: toda pregunta de noticias → @noticias
    # 'practice' = solo las carteras de práctica: el modo del bróker NO se sabe → preguntar, nunca adivinar
    assert 'money_mode tells you whether the account is practice or real' not in p
    assert "broker account's mode is NOT known" in tools and 'call get_account_status before telling' in tools
    money = p[p.index('## MONEY'):p.index('## DOMAIN KNOWLEDGE')]
    assert 'The money badge on screen shows which one' not in money and 'never guess "practice"' in money
