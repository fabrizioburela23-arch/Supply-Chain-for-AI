"""core/agents_registry.py — el registro de agentes del lado Python (limpieza 2026-10-11).

La fuente es engine/agents_registry.js (la MISMA que carga el navegador como window.KHIPU_AGENTS):
aquí se extrae su objeto JSON una vez y se exponen las vistas que antes cada módulo escribía a mano
(core/khipu_chat SEAT_AGENT/TOOL_AGENT/AGENT_LABEL, research/agent_skills SEAT_MASCOT/MASCOT_NAME/
SEAT_ROLE, research/deliberation AGENT_NAMES/DESK, research/ask_agent SEAT_WORDS, research/runner
AGENT_LABELS). Sin dependencias: lo importan módulos que arrancan antes que Flask."""
import json
import os
import re

_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'engine', 'agents_registry.js')
_RX = re.compile(r'\.KHIPU_AGENTS\s*=\s*(\{.*\})\s*;\s*$', re.S)


def _load(path=_PATH):
    with open(path, encoding='utf-8') as fh:
        m = _RX.search(fh.read())
    if not m:
        raise ValueError('engine/agents_registry.js: no encuentro "….KHIPU_AGENTS = {…};"')
    return json.loads(m.group(1))


REGISTRY = _load()

AGENTS = tuple(REGISTRY['agents'])
AGENT_IDS = tuple(a['id'] for a in AGENTS)
AGENT_BY_ID = {a['id']: a for a in AGENTS}
# nombre de la mascota (es, en)
AGENT_LABEL = {a['id']: (a['es'], a['en']) for a in AGENTS}
# puesto (o alias de puesto) → mascota
SEAT_AGENT = {s: a['id'] for a in AGENTS for s in a['seats']}
# herramienta del chat → mascota
TOOL_AGENT = dict(REGISTRY['tool_agent'])
# palabra de una mención (sin acentos, minúsculas) → puesto ('all' = todos)
SEAT_WORDS = dict(REGISTRY['mention_words'])
# palabras que nombran a la MASCOTA, no a un puesto: "@analista de cadena" es Cadena, no Fundamental
GENERIC_WORDS = frozenset(w for w in ('analista', 'analyst') if w in SEAT_WORDS)

SEATS = dict(REGISTRY['seats'])
# puestos de investigación (analistas) y puestos fijos de la sala del comité: (ícono, nombre es, nombre en)
AGENT_NAMES = {k: (v['icon'], v['es'], v['en']) for k, v in SEATS.items() if not v.get('desk')}
DESK = {k: (v['icon'], v['es'], v['en']) for k, v in SEATS.items() if v.get('desk')}
# etiqueta corta del analista (cobertura de un job: "faltan Noticias, Cadena de suministro")
SHORT_LABEL = {k: (v['short_es'], v['short_en']) for k, v in SEATS.items() if v.get('short_es')}
# rol entre paréntesis cuando el nombre de la mascota no lo dice solo ("Radar (noticias)")
CALL_ROLE = {k: (v['call_es'], v['call_en']) for k, v in SEATS.items() if v.get('call_es')}


def seat_agent(seat, default=None):
    return SEAT_AGENT.get(str(seat or '').strip().lower(), default)


def research_types_of(agent_id):
    """Tipos de analista de investigación (research/agents/registry) que pertenecen a una mascota."""
    return [s for s in (AGENT_BY_ID.get(agent_id) or {}).get('seats', ()) if s in AGENT_NAMES]
