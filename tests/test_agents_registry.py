"""Registro ÚNICO de agentes (limpieza 2026-10-11, §1 del inventario de "cosas sueltas").

engine/agents_registry.js es la única fuente de mascotas, puestos, palabras de mención y herramienta →
mascota. Lo cargan el navegador (window.KHIPU_AGENTS) y Python (core/agents_registry.py). Antes había ~12
copias a mano (mascot.js, khipu_chat.js ×2, committee.js, core/khipu_chat.py, research/agent_skills.py,
deliberation.py, ask_agent.py, runner.py, agents_api.py) y "@radar"/"@analista" solo funcionaban en el
navegador."""
import json
import os
from tests._app_source import app_source  # noqa: E402
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel):
    return open(os.path.join(ROOT, rel), encoding='utf-8').read()


def test_el_registro_es_json_estricto_y_coherente():
    from core.agents_registry import AGENT_IDS, REGISTRY, SEATS
    assert AGENT_IDS == ('khipu', 'analista', 'radar', 'cadena', 'tecnico', 'comite')
    seen = {}
    for a in REGISTRY['agents']:
        assert len(a['colors']) == 4 and a['ink'].startswith('#') and a['es'] and a['en'] and a['role_en']
        for s in a['seats']:
            assert s not in seen, f'puesto {s} en dos mascotas'
            seen[s] = a['id']
    for w, seat in REGISTRY['mention_words'].items():
        assert w == w.lower() and (seat == 'all' or seat in SEATS), w
    assert set(REGISTRY['tool_agent'].values()) <= set(AGENT_IDS)
    for k, v in SEATS.items():
        assert v['icon'] and v['es'] and v['en'] and k in seen, k              # todo puesto tiene mascota


def test_cada_analista_de_investigacion_tiene_puesto_y_mascota():
    from core.agents_registry import AGENT_NAMES, SEAT_AGENT, SHORT_LABEL
    from research.agents.registry import AGENTS
    for a in AGENTS:
        assert a.agent_type in AGENT_NAMES and a.agent_type in SHORT_LABEL and a.agent_type in SEAT_AGENT, a.agent_type


def test_herramientas_del_registro_existen_en_el_chat():
    from core.agents_registry import TOOL_AGENT
    from core.khipu_chat import tool_names
    # web_search solo aparece con Tavily configurado; get_option_greeks es del MCP (fuera del catálogo del chat)
    assert set(TOOL_AGENT) <= set(tool_names()) | {'web_search', 'get_option_greeks'}


def test_menciones_de_mascota_tambien_en_el_servidor():
    from research.ask_agent import parse_mention
    assert parse_mention('@radar ¿qué pasó con TSMC?')[0] == 'news'
    assert parse_mention('@analista NVDA')[0] == 'fundamental'
    assert parse_mention('@analista de cadena: ¿de quién depende?')[0] == 'supply_chain'   # "analista" es genérico
    assert parse_mention('@chain NVDA')[0] == 'supply_chain'
    assert parse_mention('@todos NVDA')[0] == 'all'


def test_el_cliente_deriva_los_mismos_mapas():
    from core.agents_registry import AGENT_IDS, SEAT_AGENT, TOOL_AGENT
    script = r'''
const vm = require('vm'), fs = require('fs'), ROOT = process.argv[1];
const ctx = { console, Date, Math, JSON, Promise };
ctx.window = ctx; ctx.globalThis = ctx;
ctx.localStorage = { getItem: () => null, setItem: () => {} };
ctx.document = { getElementById: () => null, createElement: () => ({}), head: { appendChild() {} } };
vm.createContext(ctx);
for (const f of ['agents_registry.js', 'mascot.js', 'khipu_chat.js']) vm.runInContext(fs.readFileSync(ROOT + '/engine/' + f, 'utf8'), ctx);
const K = ctx.KhipuChat;
process.stdout.write(JSON.stringify({ order: K.AGENT_ORDER, seat: K.SEAT_AGENT, tool: K.TOOL_AGENT,
  mascots: ctx.KhipuMascot.agents().map(a => a.id), radar: K.toolAgent('ask_agent', { seat: 'radar' }) }));
'''
    r = subprocess.run(['node', '-e', script, ROOT], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert tuple(out['order']) == tuple(out['mascots']) == AGENT_IDS
    assert out['seat'] == SEAT_AGENT and out['tool'] == TOOL_AGENT
    assert out['radar'] == 'radar'


def test_no_quedan_copias_a_mano():
    copies = {
        'engine/mascot.js': "seats: ['fundamental'",
        'engine/khipu_chat.js': "analista: ['Analista', 'Analyst']",
        'core/khipu_chat.py': "'get_company': 'analista'",
        'research/agent_skills.py': 'SEAT_MASCOT = {',
        'research/deliberation.py': 'AGENT_NAMES = {',
        'research/ask_agent.py': 'SEAT_WORDS = {',
        'research/runner.py': 'AGENT_LABELS = {',
        'core/agents_api.py': "'role_es': 'Fundamentales'",
        'engine/committee.js': "var SEAT_MASCOT = { fundamental:",
    }
    for rel, needle in copies.items():
        assert needle not in _read(rel), rel


def test_se_carga_antes_que_las_mascotas_y_queda_en_cache():
    html = app_source()
    assert html.index('src="engine/agents_registry.js"') < html.index('src="engine/mascot.js"')
    assert "'/engine/agents_registry.js'" in _read('sw.js')
    src = _read('engine/agents_registry.js')
    assert re.search(r'\.KHIPU_AGENTS\s*=\s*\{', src)
