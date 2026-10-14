#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/build_vault.py — BÓVEDA DE OBSIDIAN + GRAFO DE CONOCIMIENTO del repo (2026-10-11).

Pedido de Fabrizio: "conectar este proyecto a un Obsidian o Graphify para que sea
más fácil analizar y trabajar en el proyecto". Este script convierte el repo en
una bóveda de Obsidian (carpeta vault/) y en un grafo (vault/_grafo/graph.json +
vault/_grafo/mapa.html): una nota por módulo, por grupo de API, por variable de
entorno y por sesión de docs/ESTADO.md, con [[enlaces]] que dibujan la
arquitectura real en la vista de grafo de Obsidian.

Reglas: determinista, gratis y sin red (solo biblioteca estándar, nunca IA, nunca
la hora del reloj: las únicas fechas salen de las fuentes). Correrlo dos veces da
bytes idénticos. Solo NOMBRES de variables de entorno, jamás sus valores.

Uso:
  python scripts/build_vault.py           (re)escribe vault/
  python scripts/build_vault.py --check   regenera en memoria; sale 1 y lista las
                                          diferencias si vault/ está desactualizada

El generador es dueño de las notas 00/01/02 y de las carpetas Capas/ Módulos/ API/
Entorno/ Sesiones/ Pruebas/ Documentos/ _grafo/. .obsidian/app.json y
.obsidian/graph.json los crea si faltan; si ya existen son de la persona (Obsidian
los reescribe al mover controles): solo refresca los colores de capa del grafo.
Cualquier otra carpeta (p. ej. "Mis notas/") es del usuario y no se toca nunca.
"""
import argparse
import ast
import fnmatch
import glob
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT = 'vault'

# ════════════════════════════════════════════════════════════════════════════
# 1. QUÉ SE LEE
# ════════════════════════════════════════════════════════════════════════════
FUENTES = [
    'server.py', 'security_audit.py', 'app.html', 'sw.js',
    'core/*.py', 'core/providers/*.py',
    'research/*.py', 'research/agents/*.py',
    'ontology/*.py', 'ontology/vocabulary.json',
    'matrix/*.py', 'mcp_server/*.py', 'brokerage/*.py',
    'scripts/*.py', 'scripts/*.js',
    'engine/*.js', 'sim/*.js', 'nodes/*.js',
    'data/*.json',
    'tests/*.py', 'tests/js/*.js',
    'docs/*.md', 'CLAUDE.md', 'README.md', 'SETUP.md', 'REPAIR_LOG.md', 'KNOWLEDGE_BASE.md',
]
# Archivos de despliegue que también leen variables de entorno (no tienen nota propia).
ENV_INFRA_FILES = ['Dockerfile', 'docker-compose.yml', 'railway.toml', '.github/workflows/*.yml']

# ════════════════════════════════════════════════════════════════════════════
# 2. LA TABLA DE CAPAS (única fuente: cambiar aquí y regenerar)
# ════════════════════════════════════════════════════════════════════════════
# clave → (nombre visible, etiqueta, color en Obsidian, estilo en el mapa, descripción)
# El color de Obsidian es PLANO (no hay anillos): cada capa lleva un tono distinto (verde agua / verde lima,
# azul / celeste, naranja / marrón…). mapa.html usa en cambio 8 ranuras + relleno o anillo.
# estilo en el mapa: (ranura de color s1..s8 | n1/n2 = gris, relleno 'fill' | 'ring')
CAPAS = [
    ('interfaz', 'Interfaz (Khipus OS)', 'capa/interfaz', '#2a78d6', ('s1', 'fill'),
     'Lo que ves en pantalla: la Cabina / Khipus OS, ventanas, pestañas, mapa, avisos y estilos.'),
    ('chat', 'Chat y agentes', 'capa/chat-agentes', '#eb6834', ('s2', 'fill'),
     'El cerebro conversacional de Khipu, los agentes con su rol, el portero Jev y el lenguaje de comandos.'),
    ('investigacion', 'Investigación', 'capa/investigacion', '#1baf7a', ('s3', 'fill'),
     'El enjambre de agentes que investiga: conclusiones (claims) con evidencia citada, cola de trabajos, salud.'),
    ('comite', 'Comité', 'capa/comite', '#eda100', ('s4', 'fill'),
     'El comité de inversión: puestos, debate, convicción, tamaño, track record y comité de cartera.'),
    ('ontologia', 'Ontología y grafo temporal', 'capa/ontologia', '#e87ba4', ('s5', 'fill'),
     'La fuente de verdad del grafo: eventos bitemporales en Postgres, acciones auditadas, reconciliación y el tiempo en el mapa.'),
    ('cuant', 'Cuantitativo (matrices, tensores, riesgo)', 'capa/cuantitativo', '#9bb51c', ('s6', 'fill'),
     'Matemática del sistema: matrices y propagación de shocks, tensores, VaR, griegas, escenarios y simulaciones.'),
    ('vivo', 'Datos en vivo (cotizaciones, mundo, espacio, fundamentales)', 'capa/datos-vivo', '#6250d6',
     ('s7', 'fill'),
     'Todo lo que llega de afuera en vivo: precios, fundamentales, World Monitor, Space Monitor, noticias y el Dossier.'),
    ('dinero', 'Dinero (carteras, trading, corretaje)', 'capa/dinero', '#e34948', ('s8', 'fill'),
     'Carteras, órdenes y corretaje multi-cliente con Alpaca. Regla de oro: toda orden pasa por preview → confirmación humana.'),
    ('mcp', 'MCP y API', 'capa/mcp-api', '#13a3c6', ('s1', 'ring'),
     'El servidor MCP para IAs externas (herramientas, tokens kmcp_, OAuth) y la pantalla para conectarlas.'),
    ('voz', 'Voz', 'capa/voz', '#b345c4', ('s2', 'ring'),
     'Khipu por voz: ElevenLabs (servidor y navegador) y el orbe.'),
    ('infra', 'Infraestructura', 'capa/infraestructura', '#52514e', ('n1', 'fill'),
     'La base: server.py, IA en cascada y su gasto, PIN, HTTP saneado, reloj del servidor, service worker, sincronización.'),
    ('catalogo', 'Datos del catálogo', 'capa/datos-catalogo', '#8b5e34', ('s3', 'ring'),
     'El catálogo curado de empresas y vínculos (nodes/*.js), el snapshot data/grafo_v0.json y sus generadores.'),
    ('pruebas', 'Pruebas', 'capa/pruebas', '#9a9993', ('n2', 'fill'),
     'Las pruebas automáticas (pytest) que vigilan cada parte.'),
    ('docs', 'Documentación', 'capa/documentacion', '#b9b8b1', ('n2', 'ring'),
     'Documentos del proyecto (CLAUDE.md, docs/*.md) y las sesiones de trabajo de docs/ESTADO.md.'),
    ('otros', 'Otros', 'capa/otros', '#7d7c76', ('n1', 'ring'),
     'Archivos que la tabla de capas todavía no clasifica (se reportan para asignarles capa).'),
]
CAPA = {c[0]: c for c in CAPAS}

# Primera regla que coincide gana (fnmatch sobre la ruta relativa).
REGLAS_CAPA = [
    ('tests/*', 'pruebas'), ('docs/*', 'docs'), ('*.md', 'docs'),
    # Voz
    ('core/voice_agent.py', 'voz'), ('core/voice_api.py', 'voz'), ('engine/voice.js', 'voz'), ('engine/orb.js', 'voz'),
    # Chat y agentes
    ('core/khipu_chat.py', 'chat'), ('core/agents_api.py', 'chat'), ('core/decide.py', 'chat'),
    ('core/decide_api.py', 'chat'), ('core/semantic.py', 'chat'), ('core/canvas_spec.py', 'chat'),
    ('research/agent_skills.py', 'chat'), ('research/ask_agent.py', 'chat'),
    ('engine/khipu_chat.js', 'chat'), ('engine/command_center.js', 'chat'), ('engine/khipu_lang.js', 'chat'),
    ('engine/resolve.js', 'chat'), ('engine/localcharts.js', 'chat'), ('engine/canvas-data.js', 'chat'),
    ('engine/pickers.js', 'chat'), ('engine/app_canvas.js', 'chat'),
    # Comité
    ('research/committee*.py', 'comite'), ('research/debate.py', 'comite'), ('research/deliberation.py', 'comite'),
    ('research/outcomes.py', 'comite'), ('core/portfolio_advisor.py', 'comite'),
    ('engine/committee.js', 'comite'), ('engine/pfcommittee.js', 'comite'),
    # Investigación
    ('research/*', 'investigacion'), ('core/sec.py', 'investigacion'), ('core/websearch.py', 'investigacion'),
    ('engine/research.js', 'investigacion'),
    # Ontología y grafo temporal
    ('ontology/*', 'ontologia'), ('core/entities.py', 'ontologia'),
    ('scripts/migrate_v0_to_ontology.py', 'ontologia'), ('scripts/reconcile_v0_to_ontology.py', 'ontologia'),
    ('scripts/audit_graph.py', 'ontologia'), ('scripts/build_graph_review.py', 'ontologia'),
    ('scripts/link_origins.js', 'ontologia'),
    ('engine/temporal-graph.js', 'ontologia'), ('engine/timeline3d.js', 'ontologia'),
    ('engine/maptime.js', 'ontologia'), ('engine/reconcile.js', 'ontologia'),
    ('engine/secondbrain.js', 'ontologia'), ('engine/hypergraph.js', 'ontologia'),
    # Cuantitativo
    ('matrix/*', 'cuant'), ('core/risk_report.py', 'cuant'), ('core/risk_models.py', 'cuant'),
    ('core/options.py', 'cuant'),
    ('core/scenario_engine.py', 'cuant'), ('core/sim_agents.py', 'cuant'), ('core/screener.py', 'cuant'),
    ('core/scenario_pnl.py', 'cuant'), ('scripts/calibrate_kernel.py', 'cuant'),
    ('scripts/bench_scale.py', 'cuant'), ('scripts/gen_synth_graph.py', 'cuant'),
    ('engine/statematrix.js', 'cuant'), ('engine/hotclient.js', 'cuant'), ('engine/livesim.js', 'cuant'), ('engine/matrixview.js', 'cuant'),
    ('engine/insights.js', 'cuant'), ('engine/riskreport.js', 'cuant'), ('engine/compare.js', 'cuant'),
    ('sim/*', 'cuant'), ('engine/app_preflight.js', 'cuant'),
    # Dinero
    ('brokerage/*', 'dinero'), ('core/trading_agent.py', 'dinero'), ('engine/trade.js', 'dinero'),
    ('core/portfolio_ai.py', 'dinero'), ('core/portfolio_report.py', 'dinero'),
    ('core/portfolio_reports_api.py', 'dinero'), ('engine/clients.js', 'dinero'),
    ('engine/portfolios.js', 'dinero'), ('engine/pfreports.js', 'dinero'), ('engine/app_trade_panel.js', 'dinero'),
    # MCP y API
    ('mcp_server/*', 'mcp'), ('engine/mcpconnect.js', 'mcp'), ('scripts/smoke_mcp.py', 'mcp'),
    # Datos en vivo
    ('core/quotes.py', 'vivo'), ('core/live_*.py', 'vivo'), ('core/company_data.py', 'vivo'),
    ('core/world*.py', 'vivo'), ('core/gdelt_events.py', 'vivo'), ('core/gpr.py', 'vivo'),
    ('core/geosit.py', 'vivo'), ('core/country_geo.py', 'vivo'), ('core/space.py', 'vivo'),
    ('core/news_feed.py', 'vivo'), ('core/providers/*', 'vivo'),
    ('engine/worldmonitor.js', 'vivo'), ('engine/spacemonitor.js', 'vivo'),
    ('engine/globe.js', 'vivo'), ('engine/geo_coords.js', 'vivo'), ('engine/live.js', 'vivo'),
    ('engine/termdata.js', 'vivo'), ('engine/fincard.js', 'vivo'), ('engine/crypto.js', 'vivo'),
    ('engine/brief.js', 'vivo'),
    # Datos del catálogo
    ('nodes/*', 'catalogo'), ('data/*', 'catalogo'), ('scripts/build_listing_status.py', 'catalogo'),
    ('scripts/build_private_valuations.py', 'catalogo'), ('scripts/ingest_*.py', 'catalogo'),
    ('scripts/export_graph_v0.js', 'catalogo'),
    # Infraestructura
    ('server.py', 'infra'), ('security_audit.py', 'infra'), ('sw.js', 'infra'), ('core/*', 'infra'),
    ('scripts/__init__.py', 'infra'), ('scripts/build_vault.py', 'infra'),
    ('scripts/build_governance.py', 'infra'), ('scripts/build_shapes.py', 'infra'),
    ('scripts/build_impl_goldens.py', 'infra'),
    ('scripts/build_instrument_review.py', 'catalogo'),
    ('scripts/fetch_ledger_anchor.py', 'infra'),
    ('engine/aispend.js', 'infra'), ('engine/sync.js', 'infra'),
    # Interfaz
    # G5-06: el JS que era inline en app.html (engine/app_*.js); canvas/preflight/trade_panel van arriba en su capa
    ('app.html', 'interfaz'), ('engine/app_main.js', 'interfaz'), ('engine/app_coordinator.js', 'interfaz'),
    ('engine/app_scatter.js', 'interfaz'), ('engine/*', 'interfaz'),
]

# Este mismo generador (y su prueba) nombra rutas y archivos en sus textos como DATOS: no cuenta como "uso"
# (ni llamadas a rutas, ni referencias, ni cobertura de pruebas).
ANALYSIS_EXCLUDE = {'scripts/build_vault.py', 'tests/test_vault.py'}
# Pruebas excluidas del análisis: lo único que cubren de verdad.
TEST_SCOPE = {'tests/test_vault.py': {'scripts/build_vault.py'}}

# nodes/*.js que son CÓDIGO (el resto son datos)
NODES_CODE = {'nodes/merge_graph.js'}

# Puertas de entrada: nadie las importa/usa y está bien.
PY_ENTRY = {'server.py', 'security_audit.py', 'tests/conftest.py'}
ROUTE_EXTERNAL_PREFIXES = ('/v1/', '/mcp', '/oauth/', '/.well-known/', '/docs')
ROUTE_EXTERNAL_EXACT = {'/', '/sw.js', '/manifest.webmanifest', '/icon.svg', '/api/health'}
ROUTE_STATIC_PREFIXES = ('/nodes/', '/engine/', '/sim/', '/vendor/')
ENDPOINT_ROOTS = ('/api', '/v1', '/mcp', '/oauth', '/.well-known')

# Nombres de propiedades del navegador: asignarlas (window.onerror = …) no crea una "global de Khipus".
BROWSER_GLOBALS = {
    'location', 'name', 'status', 'open', 'close', 'history', 'document', 'navigator', 'console', 'fetch',
    'alert', 'confirm', 'prompt', 'localStorage', 'sessionStorage', 'performance', 'requestAnimationFrame',
    'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval', 'innerWidth', 'innerHeight', 'scrollTo',
    'addEventListener', 'removeEventListener', 'dispatchEvent', 'speechSynthesis', 'devicePixelRatio',
    'matchMedia', 'getComputedStyle', 'crypto', 'caches', 'origin', 'parent', 'top', 'self', 'window',
}
# Globales con nombre genérico: solo cuentan como "uso" si se escriben window.X.
GENERIC_NAMES = {
    'data', 'node', 'nodes', 'links', 'link', 'state', 'init', 'render', 'load', 'show', 'hide', 'open', 'close',
    'update', 'api', 'log', 'err', 'res', 'key', 'map', 'set', 'get', 'list', 'text', 'html', 'name', 'type',
    'item', 'items', 'value', 'url', 'opts', 'msg', 'fmt', 'tab', 'run', 'start', 'stop', 'step', 'tick', 'draw',
    'clear', 'reset', 'toggle', 'select', 'search', 'sort', 'filter', 'add', 'remove', 'send', 'post', 'parse',
    'format', 'color', 'size', 'width', 'height', 'label', 'title', 'body', 'view', 'mode', 'lang', 'resize',
    'refresh', 'apply', 'save', 'fetchJSON', 'escape', 'toast', 'debounce', 'throttle', 'clamp', 'sleep', 'now',
    'cache', 'config', 'sum', 'max', 'min', 'avg', 'pct', 'num', 'money', 'fmtNum', 'fmtPct', 'tr', 'L', 'T',
    'selected', 'sim', 'svg', 'zoom', 'root', 'legend', 'tooltip', 'canvas', 'ctx', 'scale', 'tip', 'g', 'el',
    'path', 'nodeG', 'linkG', 'width', 'height', 'margin', 'color', 'colors', 'labels', 'chart', 'charts', 'timer',
}

DECL_WORDS = {'function', 'class', 'var', 'let', 'const'}
RX_PREV_PUNCT = set('(,=:[!&|?{};+-*%<>~^}')
RX_PREV_WORDS = {'return', 'typeof', 'case', 'do', 'else', 'in', 'of', 'new', 'delete', 'void', 'throw',
                 'yield', 'await', 'instanceof'}

EDGE_DOC = {
    'imports': 'módulo Python → módulo Python que importa (también importaciones perezosas y por texto: importlib)',
    'uses_global': 'archivo JS/HTML → archivo que define una global window.* (o de nivel superior) que usa',
    'calls_endpoint': 'archivo (JS, Python o prueba) → ruta HTTP que llama (literal que empieza por /api, /v1, /mcp…)',
    'defines_endpoint': 'módulo → ruta HTTP (o herramienta MCP) que define',
    'tested_by': 'módulo → prueba que lo importa o menciona su ruta',
    'reads_env': 'módulo → variable de entorno que lee (solo el NOMBRE)',
    'mentions_in_session': 'sesión de docs/ESTADO.md → archivo o variable que menciona',
    'loads_script': 'app.html → script que carga con <script src> (en orden)',
    'references_file': 'archivo → otro archivo que nombra por su ruta (carga perezosa, lectura de datos, listas)',
}


# ════════════════════════════════════════════════════════════════════════════
# 3. UTILIDADES
# ════════════════════════════════════════════════════════════════════════════
def _read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8', errors='replace') as f:
        return f.read()


def _lines(text):
    return len(text.splitlines())


def capa_de(path):
    for pat, key in REGLAS_CAPA:
        if fnmatch.fnmatchcase(path, pat):
            return key
    return 'otros'


_FORBIDDEN = re.compile(r'[\\/:*?"<>|#^\[\]]')


def safe_name(s, limit=96):
    """Nombre de archivo válido en Windows/macOS/Linux y como [[enlace]] de Obsidian."""
    s = s.replace('→', '-').replace('/', '-').replace(':', ' -')
    s = _FORBIDDEN.sub(' ', s)
    s = ''.join(ch for ch in s if ch.isalnum() or ch in ' -—–(),.+&\'_')
    s = re.sub(r'\s+', ' ', s).strip(' .-')
    s = re.sub(r'\s+([,)])', r'\1', re.sub(r'\(\s+', '(', s))
    if len(s) > limit:
        s = s[:limit].rsplit(' ', 1)[0].rstrip(' .-—,')
        if s.count('(') > s.count(')'):
            s = s[:s.rfind('(')].rstrip(' .-—,')
    return s or 'sin nombre'


def prose(s):
    """Texto tomado de las fuentes → Markdown seguro (sin enlaces, etiquetas ni HTML accidentales)."""
    s = re.sub(r'\s+', ' ', s or '').strip()
    s = s.replace('[[', '[ [').replace(']]', '] ]').replace('%%', '% %')
    s = re.sub(r'(?<![\w&/])#(?=[A-Za-z_])', r'\\#', s)
    s = re.sub(r'<(?=[A-Za-z/!?])', '&lt;', s)
    s = s.replace('*', r'\*').replace('$', r'\$').replace('==', '= =')
    if s.count('`') % 2:
        s = s.replace('`', "'")
    if s and (s[0] in '-+>|' or re.match(r'\d+\.\s', s)):
        s = '\\' + s
    return s


def cell(s):
    return prose(s).replace('|', r'\|')


def code(s):
    s = str(s).replace('`', "'")
    return '`' + s + '`'


def tcode(s):
    """código dentro de una tabla"""
    return code(s).replace('|', r'\|')


def link(name):
    return '[[' + name + ']]'


def first_paragraph(text, limit=700):
    paras = re.split(r'\n\s*\n', (text or '').strip())
    p = paras[0] if paras else ''
    p = re.sub(r'\s+', ' ', p).strip()
    if len(p) > limit:
        p = p[:limit].rsplit(' ', 1)[0] + ' …'
    return p


def strip_self_path(p, path):
    """Quita el prefijo «ruta — » con el que empiezan casi todos los docstrings/cabeceras."""
    base = os.path.basename(path)
    for pref in (path, base, path.rsplit('.', 1)[0], os.path.dirname(path) + '/', os.path.dirname(path)):
        if pref and p.startswith(pref):
            rest = p[len(pref):].lstrip()
            if rest[:1] in ('—', '-', '–', ':', '·'):
                return rest[1:].strip()
    return p


def fm(d):
    """Front matter YAML (cadenas en JSON, que es YAML válido)."""
    out = ['---']
    for k, v in d.items():
        if isinstance(v, list):
            out.append(k + ': [' + ', '.join(json.dumps(x, ensure_ascii=False) for x in v) + ']')
        elif isinstance(v, bool):
            out.append(k + ': ' + ('true' if v else 'false'))
        elif isinstance(v, int):
            out.append(k + ': ' + str(v))
        else:
            out.append(k + ': ' + json.dumps(v, ensure_ascii=False))
    out.append('---')
    return '\n'.join(out) + '\n'


def miles(n):
    return f'{n:,}'.replace(',', '.')


# ════════════════════════════════════════════════════════════════════════════
# 4. ESCÁNER DE JAVASCRIPT (sin dependencias)
#    Quita comentarios, conserva cadenas, extrae literales y declaraciones de
#    nivel superior. Heurística clásica para distinguir /regex/ de división.
# ════════════════════════════════════════════════════════════════════════════
_TOK = re.compile(r'''
 (?P<ws>\s+)
|(?P<lc>//[^\n]*)
|(?P<bc>/\*[\s\S]*?(?:\*/|\Z))
|(?P<sq>'(?:[^'\\\n]|\\[\s\S])*'?)
|(?P<dq>"(?:[^"\\\n]|\\[\s\S])*"?)
|(?P<bt>`)
|(?P<id>[A-Za-z_$À-￿][\w$À-￿]*)
|(?P<num>\d[\w.]*)
|(?P<slash>/)
|(?P<p>[\s\S])
''', re.X)
_RX = re.compile(r'/(?:[^/\\\[\n]|\\.|\[(?:[^\]\\\n]|\\.)*\])+/[a-z]*')
_TPL_STOP = re.compile(r'[`\\]|\$\{')


class JSScan:
    """code = fuente sin comentarios (con cadenas); code_ns = además sin el TEXTO de las cadenas
    (quedan comillas vacías; el código dentro de ${…} se conserva); code_cs = como code_ns pero con las
    cadenas '…'/"…" intactas (para seguir concatenaciones sin que una /regex/ confunda)."""

    def __init__(self, src):
        self.src = src
        self.out = []
        self.ns = []
        self.cs = []
        self.strings = []
        self.templates = []
        self.top = []
        self._code(0, nested=False)
        self.code = ''.join(self.out)
        self.code_ns = ''.join(self.ns)
        self.code_cs = ''.join(self.cs)

    def _emit(self, tok, ns=None, cs=None):
        self.out.append(tok)
        n_ = tok if ns is None else ns
        self.ns.append(n_)
        self.cs.append(n_ if cs is None else cs)

    def _code(self, i, nested):
        src, n = self.src, len(self.src)
        depth = 0
        prev = None
        while i < n:
            m = _TOK.match(src, i)
            kind, tok = m.lastgroup, m.group()
            if kind == 'ws':
                self._emit(tok)
            elif kind == 'lc':
                pass
            elif kind == 'bc':
                self._emit(' ')
            elif kind in ('sq', 'dq'):
                self._emit(tok, '""', tok)
                body = tok[1:-1] if len(tok) >= 2 and tok[-1] == tok[0] else tok[1:]
                self.strings.append(body)
                prev = ('s', '')
            elif kind == 'bt':
                i = self._template(i)
                prev = ('s', '')
                continue
            elif kind == 'slash':
                if prev is None or (prev[0] == 'p' and prev[1] in RX_PREV_PUNCT) or \
                        (prev[0] == 'w' and prev[1] in RX_PREV_WORDS):
                    r = _RX.match(src, i)
                    if r:
                        self._emit(r.group(), '/x/')
                        prev = ('r', '')
                        i = r.end()
                        continue
                self._emit('/')
                prev = ('p', '/')
            elif kind == 'id':
                if not nested and depth == 0 and prev and prev[0] == 'w' and prev[1] in DECL_WORDS:
                    self.top.append(tok)
                self._emit(tok)
                prev = ('w', tok)
            elif kind == 'num':
                self._emit(tok)
                prev = ('n', tok)
            else:
                if tok == '{':
                    depth += 1
                elif tok == '}':
                    if depth == 0 and nested:
                        self._emit('}')
                        return i + 1
                    depth = max(0, depth - 1)
                self._emit(tok)
                prev = ('p', tok)
            i = m.end()
        return n

    def _template(self, i):
        src, n = self.src, len(self.src)
        self._emit('`')
        j = i + 1
        parts = []
        while j < n:
            m = _TPL_STOP.search(src, j)
            if not m:
                parts.append(src[j:])
                self._emit(src[j:], '')
                j = n
                break
            seg = src[j:m.start()]
            parts.append(seg)
            self._emit(seg, '')
            t = m.group()
            if t == '\\':
                esc = src[m.start():m.start() + 2]
                parts.append(esc)
                self._emit(esc, '')
                j = m.start() + 2
            elif t == '`':
                self._emit('`')
                j = m.end()
                break
            else:
                self._emit('${')
                parts.append('◊')
                j = self._code(m.end(), nested=True)
        self.strings.append(''.join(parts))
        self.templates.append(''.join(parts))
        return j


_ID_RX = re.compile(r'[A-Za-z_$][\w$]*')
_WIN_DEF = re.compile(r'(?<![\w$.])(?:window|globalThis)\.([A-Za-z_$][\w$]*)\s*(?:=(?![=>])|\|\|=|\?\?=|&&=)')
_WIN_DEF2 = re.compile(r'''(?<![\w$.])window\[\s*['"]([A-Za-z_$][\w$]*)['"]\s*\]\s*=(?!=)''')
_WIN_READ = re.compile(r'(?<![\w$.])(?:window|globalThis|self)\.([A-Za-z_$][\w$]*)(?![\w$])'
                       r'(?!\s*(?:=(?![=>])|\|\|=|\?\?=|&&=))')
_WIN_DEF3 = re.compile(r'''defineProperty\(\s*window\s*,\s*['"]([A-Za-z_$][\w$]*)['"]''')
_LOCAL_DECL = re.compile(r'(?:\bfunction\s*\*?\s*|\bclass\s+|\b(?:var|let|const)\s+)([A-Za-z_$][\w$]*)')
_PARAMS = re.compile(r'\bfunction\s*\*?\s*[\w$]*\s*\(([^)]*)\)')
_ARROW_P = re.compile(r'\(([^()]*)\)\s*=>')
_ARROW_1 = re.compile(r'(?<![\w$.])([A-Za-z_$][\w$]*)\s*=>')
_CATCH = re.compile(r'\bcatch\s*\(\s*([A-Za-z_$][\w$]*)')
_DESTR = re.compile(r'\b(?:var|let|const)\s*[\{\[]([^}\]]*)[\}\]]')


def _is_object_key(code_text, s, e):
    """¿El identificador en [s, e) es la CLAVE de un objeto ({ LINKS: … } / , clave: …)? Entonces no es un uso."""
    j = e
    n = len(code_text)
    while j < n and code_text[j] in ' \t\r\n':
        j += 1
    if j >= n or code_text[j] != ':' or code_text[j + 1:j + 2] == ':':
        return False
    k = s - 1
    while k >= 0 and code_text[k] in ' \t\r\n':
        k -= 1
    return k >= 0 and code_text[k] in '{,'


def js_identifiers(code_text, skip_keys=False):
    """(identificadores sueltos, identificadores leídos como window.X). skip_keys: sin las claves de objetos."""
    bare, win = set(), set()
    for m in _ID_RX.finditer(code_text):
        s = m.start()
        name = m.group()
        if s > 0 and code_text[s - 1] in '$_':
            continue
        if s > 0 and (code_text[s - 1].isalnum()):
            continue
        if s > 0 and code_text[s - 1] == '.':
            k = s - 1
            pre = code_text[max(0, k - 10):k]
            if pre.endswith('window') or pre.endswith('globalThis') or pre.endswith('self'):
                win.add(name)
            continue
        if skip_keys and _is_object_key(code_text, s, m.end()):
            continue
        bare.add(name)
    return bare, win


def js_local_decls(code_text):
    loc = set(_LOCAL_DECL.findall(code_text))
    for rx in (_PARAMS, _ARROW_P, _DESTR):
        for grp in rx.findall(code_text):
            for p in re.split(r'[,\s=:{}\[\]().]+', grp):
                if _ID_RX.fullmatch(p or ''):
                    loc.add(p)
    loc.update(_ARROW_1.findall(code_text))
    loc.update(_CATCH.findall(code_text))
    return loc


def js_header(text):
    """Primer comentario del archivo (cabecera) → texto plano."""
    t = text.lstrip('﻿')
    if t.startswith('#!'):
        t = t.split('\n', 1)[1] if '\n' in t else ''
    t = t.lstrip()
    # cabecera dentro de un IIFE: (function(){ 'use strict'; /* … */
    m = re.match(r'(?:\(\s*function\s*\([^)]*\)\s*\{\s*)?(?:[\'"]use strict[\'"];?\s*)?', t)
    if m and m.end() and t[m.end():].lstrip().startswith(('/*', '//')):
        t = t[m.end():].lstrip()
    if t.startswith('/*'):
        end = t.find('*/')
        body = t[2:end if end >= 0 else len(t)]
    elif t.startswith('//'):
        ls = []
        for ln in t.split('\n'):
            s = ln.strip()
            if not s.startswith('//'):
                break
            ls.append(s[2:])
        body = '\n'.join(ls)
    else:
        return ''
    out = []
    for ln in body.split('\n'):
        s = ln.strip()
        s = re.sub(r'^\*+\s?', '', s)
        if re.fullmatch(r'[=\-─━*_#~]{3,}', s):
            s = ''
        s = re.sub(r'\s*[=─━]{2,}\s*$', '', s)
        s = re.sub(r'^[=─━\-]{2,}\s*', '', s)
        out.append(s)
    return '\n'.join(out).strip()


# ════════════════════════════════════════════════════════════════════════════
# 5. ANÁLISIS DE PYTHON (ast)
# ════════════════════════════════════════════════════════════════════════════
def _const_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _render_str(node):
    """Constante, f-string o suma de cadenas → texto con ◊ donde va una variable."""
    s = _const_str(node)
    if s is not None:
        return s
    if isinstance(node, ast.JoinedStr):
        parts = []
        for v in node.values:
            c = _const_str(v)
            parts.append(c if c is not None else '◊')
        return ''.join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        a, b = _render_str(node.left), _render_str(node.right)
        if a is None and b is None:
            return None
        return (a if a is not None else '◊') + (b if b is not None else '◊')
    return None


def _call_name(func):
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        base = _call_name(func.value)
        return (base + '.' + func.attr) if base else func.attr
    return None


def _sig(fn):
    a = fn.args
    names = [x.arg for x in a.posonlyargs + a.args]
    if names and names[0] in ('self', 'cls'):
        names = names[1:]
    nd = len(a.defaults)
    parts = []
    for i, nm in enumerate(names):
        parts.append(nm + ('=…' if i >= len(names) - nd else ''))
    if a.vararg:
        parts.append('*' + a.vararg.arg)
    for k, d in zip(a.kwonlyargs, a.kw_defaults):
        parts.append(k.arg + ('=…' if d is not None else ''))
    if a.kwarg:
        parts.append('**' + a.kwarg.arg)
    return '(' + ', '.join(parts) + ')'


_ENV_DIRECT = {'os.getenv', 'getenv', 'os.environ.get', 'environ.get', 'os.environ.setdefault',
               'environ.setdefault', 'os.environ.pop'}


def analyze_py(path, text):
    info = {'defs': [], 'imports': [], 'strings': [], 'routes': [], 'env': [], 'has_main': False,
            'docstring': '', 'tools': [], 'helpers': {}, 'parse_error': None, 'dyn': []}
    try:
        tree = ast.parse(text)
    except SyntaxError as e:  # pragma: no cover
        info['parse_error'] = str(e)
        return info
    info['docstring'] = ast.get_docstring(tree) or ''

    # definiciones de nivel superior
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            info['defs'].append({'name': node.name, 'kind': 'función', 'sig': _sig(node),
                                 'doc': first_paragraph(ast.get_docstring(node) or '', 140), 'line': node.lineno})
        elif isinstance(node, ast.ClassDef):
            info['defs'].append({'name': node.name, 'kind': 'clase', 'sig': '',
                                 'doc': first_paragraph(ast.get_docstring(node) or '', 140), 'line': node.lineno})
        elif isinstance(node, ast.If):
            t = node.test
            if isinstance(t, ast.Compare) and isinstance(t.left, ast.Name) and t.left.id == '__name__':
                info['has_main'] = True

    # UNA sola pasada por el árbol + mapa de padres (antes: varias pasadas = lento)
    nodes = list(ast.walk(tree))
    parent = {}
    for n in nodes:
        for c in ast.iter_child_nodes(n):
            parent[id(c)] = n

    def _up(n):
        while id(n) in parent:
            n = parent[id(n)]
            yield n

    # constantes de módulo que son tuplas/listas de nombres (para os.getenv(n) en bucle)
    const_lists = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            v = node.value
            if isinstance(v, (ast.Tuple, ast.List, ast.Set)) and v.elts and all(_const_str(e) for e in v.elts):
                const_lists[node.targets[0].id] = [_const_str(e) for e in v.elts]

    # blueprints → prefijo
    prefixes = {'app': ''}
    skip_ids = set()
    for node in nodes:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and \
                _call_name(node.value.func) in ('Blueprint', 'flask.Blueprint'):
            pref = ''
            for kw in node.value.keywords:
                if kw.arg == 'url_prefix' and _const_str(kw.value) is not None:
                    pref = _const_str(kw.value)
                    skip_ids.add(id(kw.value))
            for t in node.targets:
                if isinstance(t, ast.Name):
                    prefixes[t.id] = pref

    def _methods(call, default):
        for kw in call.keywords:
            if kw.arg == 'methods' and isinstance(kw.value, (ast.List, ast.Tuple, ast.Set)):
                return sorted({(_const_str(e) or '').upper() for e in kw.value.elts if _const_str(e)})
        return default

    # rutas (decoradores y add_url_rule), en cualquier nivel
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for d in node.decorator_list:
                if not isinstance(d, ast.Call) or not isinstance(d.func, ast.Attribute):
                    continue
                verb = d.func.attr
                obj = d.func.value.id if isinstance(d.func.value, ast.Name) else None
                if verb not in ('route', 'get', 'post', 'put', 'delete', 'patch') or not d.args:
                    continue
                p = _const_str(d.args[0])
                if p is None or not p.startswith('/'):
                    continue
                skip_ids.add(id(d.args[0]))
                meths = _methods(d, ['GET']) if verb == 'route' else [verb.upper()]
                full = prefixes.get(obj, '') + p if obj else p
                info['routes'].append({'path': full, 'methods': meths, 'func': node.name, 'line': node.lineno,
                                       'bp': obj or ''})
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'add_url_rule':
            if not node.args:
                continue
            p = _const_str(node.args[0])
            if p is None:
                continue
            skip_ids.add(id(node.args[0]))
            for a in node.args[1:2]:
                if _const_str(a) is not None:
                    skip_ids.add(id(a))
            obj = node.func.value.id if isinstance(node.func.value, ast.Name) else ''
            view = node.args[2] if len(node.args) > 2 else None
            fname = ''
            while view is not None:
                if isinstance(view, ast.Name):
                    fname = view.id
                    break
                if isinstance(view, ast.Call):
                    view = view.args[0] if view.args else None
                    continue
                break
            if not fname:
                fname = _const_str(node.args[1]) if len(node.args) > 1 and _const_str(node.args[1]) else '?'
            info['routes'].append({'path': prefixes.get(obj, '') + p, 'methods': _methods(node, ['GET']),
                                   'func': fname, 'line': node.lineno, 'bp': obj})

    # importaciones (también las perezosas dentro de funciones)
    for node in nodes:
        if isinstance(node, ast.Import):
            for a in node.names:
                info['imports'].append((a.name, None, node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for a in node.names:
                info['imports'].append((node.module, a.name, node.lineno))

    # cadenas (sin las que DEFINEN rutas ni los docstrings) + lecturas de entorno
    docstring_ids = set()
    for node in nodes:
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            b0 = node.body[0]
            if isinstance(b0, ast.Expr) and _const_str(b0.value) is not None:
                docstring_ids.add(id(b0.value))
    seen_parts = set()
    for node in nodes:
        if isinstance(node, (ast.JoinedStr, ast.BinOp)) and id(node) not in seen_parts:
            r = _render_str(node)
            if r is not None and id(node) not in skip_ids and '◊' in r:
                info['strings'].append(r)
                for sub in ast.walk(node):
                    seen_parts.add(id(sub))
    helper_calls = []
    for node in nodes:
        s = _const_str(node)
        if s is not None and id(node) not in skip_ids and id(node) not in docstring_ids and id(node) not in seen_parts:
            info['strings'].append(s)
        if isinstance(node, ast.Call):
            cn = _call_name(node.func) or ''
            if cn in _ENV_DIRECT and node.args:
                a0 = node.args[0]
                nm = _const_str(a0)
                if nm is not None:
                    info['env'].append((nm, 'código', node.lineno))
                elif isinstance(a0, (ast.BinOp, ast.JoinedStr)):
                    r = _render_str(a0)
                    if r and r[0].isupper():
                        info['env'].append((r.replace('◊', '{X}'), 'código', node.lineno))
                elif isinstance(a0, ast.Name):
                    # ¿ayudante? def f(name, …): … os.getenv(name)
                    for anc in _up(node):
                        if isinstance(anc, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            params = [x.arg for x in anc.args.posonlyargs + anc.args.args]
                            if a0.id in params:
                                info['helpers'][anc.name] = params.index(a0.id)
                            break
                    # ¿bucle? for n in ('A','B') / for n in CONSTANTE
                    for nm2 in _loop_names(_up(node), a0.id, const_lists):
                        info['env'].append((nm2, 'lista', node.lineno))
            short = cn.rsplit('.', 1)[-1]
            if node.args and short:
                helper_calls.append((short, [_const_str(a) for a in node.args], node.lineno))
        if isinstance(node, ast.Subscript) and _call_name(node.value) in ('os.environ', 'environ'):
            nm = _const_str(node.slice)
            if nm is not None:
                info['env'].append((nm, 'código', node.lineno))
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], (ast.In, ast.NotIn)) \
                and _call_name(node.comparators[0]) in ('os.environ', 'environ'):
            nm = _const_str(node.left)
            if nm is not None:
                info['env'].append((nm, 'código', node.lineno))
    for short, args, line in helper_calls:
        if short in info['helpers']:
            k = info['helpers'][short]
            if k < len(args) and args[k] and re.fullmatch(r'[A-Z][A-Z0-9_]+', args[k]):
                info['env'].append((args[k], 'código', line))
    info['env'] = [(n, k, ln) for (n, k, ln) in info['env'] if re.fullmatch(r'[A-Z][A-Z0-9_{}X]*', n)]

    # herramientas MCP (@tool('nombre', 'título', 'alcance', …, read_only=…))
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for d in node.decorator_list:
                if isinstance(d, ast.Call) and _call_name(d.func) == 'tool' and len(d.args) >= 3:
                    ro = True
                    for kw in d.keywords:
                        if kw.arg == 'read_only' and isinstance(kw.value, ast.Constant):
                            ro = bool(kw.value.value)
                    info['tools'].append({'name': _const_str(d.args[0]) or '?', 'title': _const_str(d.args[1]) or '',
                                          'scope': _const_str(d.args[2]) or '?', 'read_only': ro,
                                          'func': node.name, 'line': node.lineno})
    info['dyn'] = sorted(set(dyn_module_refs(tree, info['strings'])))
    info['_tree'] = tree
    return info


_DOTTED_MOD = re.compile(r'[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)+')
_DYN_IMPORT_CALLS = {'import_module', '__import__', '_module', 'find_spec'}


def dyn_module_refs(root, strings=None):
    """Textos que nombran un módulo para importarlo en tiempo de ejecución (importación «dinámica»).

    Una palabra suelta ('server', 'research', 'matrix') es casi siempre otra cosa (una categoría, una clave
    de dict, un alcance): solo cuenta si va DENTRO de una llamada que importa — importlib.import_module(x),
    __import__(x), sys.modules.get(x) / sys.modules[x], _module(x), monkeypatch.setitem(sys.modules, x, …) — o
    es el primer elemento de una tupla (módulo, '…_bp') de blueprints. Un texto con puntos ('core.world')
    cuenta en cualquier lugar (`strings`; si no se dan, todos los textos bajo `root`)."""
    out = []
    if strings is None:
        strings = [s for s in (_const_str(n) for n in ast.walk(root)) if s is not None]
    out.extend(s for s in strings if _DOTTED_MOD.fullmatch(s))
    for n in ast.walk(root):
        if isinstance(n, ast.Call):
            cn = _call_name(n.func) or ''
            short = cn.rsplit('.', 1)[-1]
            if (short in _DYN_IMPORT_CALLS or cn.endswith('modules.get')) and n.args:
                s = _const_str(n.args[0])
                if s:
                    out.append(s)
            elif short == 'setitem' and len(n.args) >= 2 and (_call_name(n.args[0]) or '').endswith('modules'):
                s = _const_str(n.args[1])
                if s:
                    out.append(s)
        elif isinstance(n, ast.Subscript) and (_call_name(n.value) or '') in ('sys.modules', 'modules'):
            s = _const_str(n.slice)
            if s:
                out.append(s)
        elif isinstance(n, ast.Tuple) and len(n.elts) == 2:
            a, b = _const_str(n.elts[0]), _const_str(n.elts[1])
            if a and b and b.endswith('_bp'):
                out.append(a)
    return out


def _loop_names(ancestors, var, const_lists):
    """Nombres constantes sobre los que itera la variable `var` (bucle o comprensión que rodea la llamada)."""
    for node in ancestors:
        gens = []
        if isinstance(node, (ast.For, ast.AsyncFor)):
            gens = [(node.target, node.iter)]
        elif isinstance(node, (ast.GeneratorExp, ast.ListComp, ast.SetComp, ast.DictComp)):
            gens = [(g.target, g.iter) for g in node.generators]
        for tgt, it in gens:
            if isinstance(tgt, ast.Name) and tgt.id == var:
                if isinstance(it, (ast.Tuple, ast.List, ast.Set)):
                    return [s for s in (_const_str(e) for e in it.elts) if s]
                if isinstance(it, ast.Name) and it.id in const_lists:
                    return list(const_lists[it.id])
                return []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
            return []
    return []


# ════════════════════════════════════════════════════════════════════════════
# 6. INVENTARIO
# ════════════════════════════════════════════════════════════════════════════
def inventory():
    paths = set()
    for pat in FUENTES:
        for p in glob.glob(os.path.join(ROOT, pat)):
            if os.path.isfile(p) and '__pycache__' not in p:
                paths.add(os.path.relpath(p, ROOT).replace(os.sep, '/'))
    files = {}
    for path in sorted(paths):
        text = _read(path)
        ext = path.rsplit('.', 1)[-1]
        if path.startswith('tests/'):
            role = 'test'
        elif ext == 'md':
            role = 'doc'
        elif ext == 'json' or (path.startswith('nodes/') and path not in NODES_CODE):
            role = 'data'
        elif ext == 'html':
            role = 'page'
        else:
            role = 'code'
        f = {'path': path, 'ext': ext, 'role': role, 'text': text, 'lines': _lines(text),
             'layer': capa_de(path)}
        files[path] = f
    _assign_names(files)
    return files


def _assign_names(files):
    used = {}
    for path in sorted(files):
        f = files[path]
        if f['role'] == 'doc':
            base = 'Doc ' + os.path.basename(path)[:-3]
            folder = 'Documentos'
        elif f['role'] == 'test':
            base = path.replace('/', '.')
            folder = 'Pruebas'
        else:
            base = path.replace('/', '.')
            d = os.path.dirname(path)
            folder = 'Módulos/' + (d if d else 'raíz')
        name = base
        k = 2
        while name.lower() in used:
            name = f'{base} ({k})'
            k += 1
        used[name.lower()] = path
        f['note'] = name
        f['folder'] = folder


# ════════════════════════════════════════════════════════════════════════════
# 7. EL ANÁLISIS COMPLETO
# ════════════════════════════════════════════════════════════════════════════
class Model:
    pass


def _module_names(files):
    """dotted → ruta para todo .py"""
    mods = {}
    for path, f in files.items():
        if f['ext'] != 'py':
            continue
        dotted = path[:-3].replace('/', '.')
        if dotted.endswith('.__init__'):
            dotted = dotted[:-9]
        mods[dotted] = path
    return mods


def _resolve_import(mods, module, name):
    if name:
        cand = module + '.' + name
        if cand in mods:
            return mods[cand]
    parts = module.split('.')
    while parts:
        cand = '.'.join(parts)
        if cand in mods:
            return mods[cand]
        parts.pop()
    return None


def endpoint_ref(s):
    """Literal que parece una ruta HTTP de Khipus → forma normalizada, o None."""
    if not isinstance(s, str):
        return None
    s = s.strip()
    if s.startswith('◊/'):          # `${base}/api/…` o f'{BASE}/api/…': la base es el servidor
        s = s[1:]
    if not s.startswith(ENDPOINT_ROOTS):
        return None
    if not re.match(r'^/(?:api|v1|mcp|oauth|\.well-known)(?:[/?◊]|$)', s):
        return None
    s = re.split(r'[?#\s]', s, maxsplit=1)[0]
    if re.search(r'[\'"<>{}\\]', s.replace('◊', '')):
        return None
    return s


def _segs(p):
    p = p.strip('/')
    return p.split('/') if p else []


def _seg_ok(ref_seg, route_seg):
    if route_seg.startswith('<'):
        return True
    if '◊' in ref_seg:
        rx = '.*'.join(re.escape(x) for x in ref_seg.split('◊'))
        return re.fullmatch(rx, route_seg) is not None
    return ref_seg == route_seg


def match_routes(ref, routes_by_path, prefix=True):
    """Rutas que un literal puede estar llamando. Exacto; o (prefix=True) prefijo si el
    literal termina en '/' (se concatena algo) o es una base como '/api/brokerage'."""
    rs = _segs(ref)
    exact = []
    for path in routes_by_path:
        ps = _segs(path)
        if len(ps) == len(rs) and all(_seg_ok(a, b) for a, b in zip(rs, ps)):
            exact.append(path)
    if (exact and not ref.endswith('/')) or not prefix:
        return sorted(exact)
    if len(rs) < 2:
        return sorted(exact)
    pref = []
    for path in routes_by_path:
        ps = _segs(path)
        if len(ps) > len(rs) and all(_seg_ok(a, b) for a, b in zip(rs, ps)):
            pref.append(path)
    return sorted(set(exact) | set(pref))


_PATH_TOKEN = re.compile(r'(?<![\w.-])((?:[\w-]+/)+[\w.-]+\.(?:py|js|html|json))(?![\w-])')
_QUOTED_BASE = re.compile(r'''(?<=['"/])([\w.-]+\.(?:py|js|html|json))(?=['"])''')


def build_model():
    M = Model()
    files = inventory()
    M.files = files
    mods = _module_names(files)
    M.mods = mods
    by_basename = defaultdict(list)
    for p in files:
        by_basename[os.path.basename(p)].append(p)
    M.unique_base = {b: ps[0] for b, ps in by_basename.items() if len(ps) == 1}

    # ── análisis por archivo ─────────────────────────────────────────────────
    for path, f in files.items():
        if f['ext'] == 'json':
            try:
                d = json.loads(f['text'])
            except ValueError:
                d = None
            doc = ''
            if isinstance(d, dict):
                doc = next((d[k] for k in ('_doc', 'description') if isinstance(d.get(k), str)), '')
                if not doc and isinstance(d.get('source'), str):
                    doc = 'Generado desde ' + d['source']
            f['purpose'] = first_paragraph(doc) or 'Archivo de datos JSON.'
        elif f['ext'] == 'py':
            f['py'] = analyze_py(path, f['text'])
            f['purpose'] = strip_self_path(first_paragraph(f['py']['docstring']), path)
        elif f['ext'] == 'js':
            f['js'] = _analyze_js(f['text'])
            f['purpose'] = strip_self_path(first_paragraph(js_header(f['text'])), path)
        elif f['ext'] == 'html':
            f['js'] = _analyze_html(f['text'])
            f['purpose'] = ''
        elif f['ext'] == 'md':
            f['purpose'] = _md_purpose(f['text'])

    edges = []  # (src_id, dst_id, type, detail)
    M.edges = edges

    # ── Python: importaciones ────────────────────────────────────────────────
    imp = defaultdict(lambda: defaultdict(set))  # src → dst → nombres
    dyn = defaultdict(set)
    for path, f in files.items():
        if f['ext'] != 'py':
            continue
        for module, name, _ln in f['py']['imports']:
            dst = _resolve_import(mods, module, name)
            if dst and dst != path:
                imp[path][dst].add(name or module)
        for s in f['py']['dyn']:
            if s in mods and mods[s] != path:
                dyn[path].add(mods[s])
                imp[path][mods[s]].add('(dinámico: ' + s + ')')
    M.imports = imp
    M.dyn_imports = dyn

    # ── rutas HTTP ───────────────────────────────────────────────────────────
    routes = []
    for path, f in files.items():
        if f['ext'] == 'py' and f['role'] != 'test':
            for r in f['py']['routes']:
                r = dict(r)
                r['file'] = path
                r['id'] = 'endpoint:' + ','.join(r['methods']) + ' ' + r['path']
                routes.append(r)
    routes.sort(key=lambda r: (r['path'], ','.join(r['methods']), r['file'], r['func']))
    # ids únicos
    seen = defaultdict(int)
    for r in routes:
        seen[r['id']] += 1
        if seen[r['id']] > 1:
            r['id'] += f' #{seen[r["id"]]}'
    M.routes = routes
    routes_by_path = defaultdict(list)
    for r in routes:
        routes_by_path[r['path']].append(r)
    M.routes_by_path = routes_by_path

    # ── quién llama a cada ruta ──────────────────────────────────────────────
    calls = defaultdict(lambda: defaultdict(set))  # file → route path → refs
    unmatched = defaultdict(set)
    for path, f in files.items():
        if path == 'sw.js' or path in ANALYSIS_EXCLUDE or f['role'] in ('doc', 'data'):
            continue
        strs = f['py']['strings'] if f['ext'] == 'py' else (f['js']['strings'] if 'js' in f else [])
        refs_here = sorted({r for r in (endpoint_ref(x) for x in strs) if r})
        # el Python del servidor no se llama a sí mismo por HTTP: ahí solo cuentan coincidencias
        # EXACTAS (una tabla de prefijos como ('/api/research', 'research') no es una llamada)
        loose = f['ext'] != 'py' or f['role'] == 'test' or path.startswith('scripts/')
        # rutas RELATIVAS del mismo archivo ('/clients/' + id + '/audit' → '/clients/◊/audit') para unirlas a
        # una base como var API = '/api/brokerage'
        rel = f['js']['rel'] if 'js' in f else relative_refs([x for x in strs if x.startswith('◊/')])
        for ref in refs_here:
            exact = match_routes(ref, routes_by_path, prefix=False)
            if loose and not exact and not ref.endswith('/') and '◊' not in ref and len(_segs(ref)) >= 2 \
                    and match_routes(ref, routes_by_path, prefix=True):
                # una BASE: solo cuenta lo que el archivo arma sobre ella; si no arma nada (la pasa a otro
                # módulo) vale como prefijo de todas sus rutas, salvo en pruebas (ahí son textos de aserción)
                hits = defaultdict(set)
                for r in rel:
                    for h in match_routes(ref + r, routes_by_path, prefix=r.endswith('/')):
                        hits[h].add(ref + r)
                if not hits and not rel and f['role'] != 'test':
                    for h in match_routes(ref, routes_by_path, prefix=True):
                        hits[h].add(ref)
                for h, rs in hits.items():
                    calls[path][h] |= rs
                continue
            hits = match_routes(ref, routes_by_path, prefix=loose)
            if hits:
                for h in hits:
                    calls[path][h].add(ref)
            elif not loose and match_routes(ref, routes_by_path, prefix=True):
                pass        # el servidor nombra un PREFIJO (tabla de rutas → función): ni llamada ni error
            elif f['role'] != 'test' and ref.startswith('/api/') and len(_segs(ref)) >= 2:
                unmatched[path].add(ref)
    M.calls = calls
    M.unmatched_calls = unmatched

    # ── JS: globales definidas y usadas ──────────────────────────────────────
    definers = defaultdict(set)  # nombre → archivos
    explicit = defaultdict(set)  # nombre → archivos (window.X explícito)
    for path, f in files.items():
        # solo lo que corre en la PÁGINA define globales (scripts/*.js corren en Node; sw.js en su propio worker)
        if 'js' not in f or f['role'] == 'test' or path.startswith('scripts/') or path == 'sw.js':
            continue
        for nm in f['js']['win_defs']:
            definers[nm].add(path)
            explicit[nm].add(path)
        for nm in f['js']['top']:
            if nm not in BROWSER_GLOBALS:
                definers[nm].add(path)
    for nm in list(definers):
        if nm in BROWSER_GLOBALS:
            del definers[nm]
            explicit.pop(nm, None)
    # definidor PRINCIPAL: quien la declara de nivel superior (const NODES / function switchTab);
    # los que solo hacen window.X = X (re-exportar) o la envuelven son secundarios.
    primary = {}
    for nm, defs in definers.items():
        tops = {d for d in defs if nm in files[d]['js']['top']}
        primary[nm] = tops or set(defs)
    M.definers = definers
    M.primary = primary
    M.explicit = explicit
    uses = defaultdict(lambda: defaultdict(set))  # usuario → definidor → nombres
    for path, f in files.items():
        if 'js' not in f or f['role'] == 'test' or path.startswith('scripts/') or path == 'sw.js':
            continue
        js = f['js']
        for nm, defs in primary.items():
            if path in defs:
                continue
            if nm not in js['win']:
                if nm in GENERIC_NAMES or len(nm) < 3:
                    continue
                if nm in explicit:
                    # window.X exportada: vale nombrarla en CÓDIGO (no como clave de objeto) o usarla dentro de
                    # un texto/HTML como X( · X.algo · window.X (onclick="X(…)"); la palabra suelta en un texto
                    # o en el HTML ("KHIPU&gt;", 'KHIPU TRADING') no es un uso
                    if nm not in js['bare_code'] and nm not in js['str_uses']:
                        continue
                else:
                    # global de nivel superior (const/function del script): solo código real o X( en un texto
                    if len(nm) < 4 or (nm not in js['bare_code'] and nm not in js['str_calls']):
                        continue
                if nm in js['local'] and path not in definers[nm]:
                    continue
            for d in defs:
                uses[path][d].add(nm)
    M.uses = uses

    # menciones de globales fuera de JS (Python del servidor y pruebas)
    py_text_ids = {}
    for path, f in files.items():
        if f['ext'] == 'py' and path not in ANALYSIS_EXCLUDE:
            py_text_ids[path] = set(_ID_RX.findall(' '.join(f['py']['strings'])))
    M.py_text_ids = py_text_ids

    # ── scripts de app.html (orden de carga) ─────────────────────────────────
    M.app_scripts = files['app.html']['js']['scripts'] if 'app.html' in files else []

    # ── referencias a archivos por su ruta ───────────────────────────────────
    refs = defaultdict(set)
    for path, f in files.items():
        if path == 'sw.js' or path in ANALYSIS_EXCLUDE or f['role'] in ('doc', 'test', 'data'):
            continue
        strs = f['py']['strings'] if f['ext'] == 'py' else (f['js']['strings'] if 'js' in f else [])
        for s in strs:
            t = s.strip().split('?')[0].lstrip('./').lstrip('/')
            if not t or len(t) > 120:
                continue
            dst = None
            if t in files:
                dst = t
            elif '/' not in t and t in M.unique_base and files[M.unique_base[t]]['role'] in ('data', 'page') \
                    and f['ext'] == 'py':
                dst = M.unique_base[t]
            if dst and dst != path and files[dst]['role'] != 'doc':
                refs[path].add(dst)
    if 'app.html' in files:
        for s in M.app_scripts:
            if s['src'] in files:
                refs['app.html'].discard(s['src'])
    M.file_refs = refs

    # ── pruebas → módulos ────────────────────────────────────────────────────
    tested = defaultdict(set)  # módulo → pruebas
    for tpath, tf in files.items():
        if tf['role'] != 'test':
            continue
        if tpath in ANALYSIS_EXCLUDE:
            for p in sorted(TEST_SCOPE.get(tpath, ())):
                if p in files:
                    tested[p].add(tpath)
            continue
        covered = set()
        if tf['ext'] == 'py':
            for module, name, _ln in tf['py']['imports']:
                dst = _resolve_import(mods, module, name)
                if dst:
                    covered.add(dst)
            for s in tf['py']['dyn']:
                if s in mods:
                    covered.add(mods[s])
            for s in tf['py']['strings']:
                mm = re.match(r'^([a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)+)', s)
                if mm:
                    parts = mm.group(1).split('.')
                    while len(parts) > 1:
                        cand = '.'.join(parts)
                        if cand in mods:
                            covered.add(mods[cand])
                            break
                        parts.pop()
        text = tf['text']
        # rutas escritas (engine/x.js, también dentro de ROOT + '/engine/x.js') …
        for tok in _PATH_TOKEN.findall(text):
            parts = tok.split('/')
            for k in range(len(parts)):
                cand = '/'.join(parts[k:])
                if cand in files:
                    covered.add(cand)
                    break
        # … o el nombre de archivo entre comillas ('cockpit.js', os.path.join(ROOT, 'engine', 'x.js'))
        for b in _QUOTED_BASE.findall(text):
            if b in M.unique_base:
                covered.add(M.unique_base[b])
        # … o llama por HTTP a una ruta que el módulo define
        for rpath in M.calls.get(tpath, {}):
            for r in routes_by_path[rpath]:
                covered.add(r['file'])
        for p in covered:
            if p != tpath and files[p]['role'] not in ('test', 'doc'):
                tested[p].add(tpath)
    M.tested = tested

    # ── variables de entorno ─────────────────────────────────────────────────
    env_readers = defaultdict(lambda: defaultdict(set))  # nombre → archivo → tipos
    for path, f in files.items():
        if f['ext'] == 'py' and f['role'] != 'test':
            for nm, kind, _ln in f['py']['env']:
                env_readers[nm][path].add(kind)
    infra_env = defaultdict(set)
    for pat in ENV_INFRA_FILES:
        for p in sorted(glob.glob(os.path.join(ROOT, pat))):
            rel = os.path.relpath(p, ROOT).replace(os.sep, '/')
            t = _read(rel)
            for nm in re.findall(r'\$\{\{\s*(?:secrets|vars)\.([A-Z][A-Z0-9_]+)', t):
                infra_env[nm].add(rel)
            for nm in re.findall(r'\$\{?([A-Z][A-Z0-9_]+)', t):
                infra_env[nm].add(rel)
    M.env_readers = env_readers
    M.infra_env = infra_env
    test_env = defaultdict(set)
    env_names = set(env_readers) | set(infra_env)
    for tpath, tf in files.items():
        if tf['role'] == 'test' and tf['ext'] == 'py' and tpath not in ANALYSIS_EXCLUDE:
            ss = set(tf['py']['strings'])
            for nm in env_names:
                if nm in ss:
                    test_env[nm].add(tpath)
    M.test_env = test_env
    claude = files['CLAUDE.md']['text'] if 'CLAUDE.md' in files else ''
    M.claude_block = parse_claude_env_block(claude)
    M.claude_text = claude

    # ── herramientas MCP ─────────────────────────────────────────────────────
    M.tools = []
    for _tp in ('mcp_server/tools.py', 'mcp_server/ops.py'):     # ops.py: operaciones v2 (mismo REGISTRY)
        if _tp in files:
            M.tools += [dict(t, file=_tp) for t in _mcp_tools(files[_tp], mods)]
    M.tools.sort(key=lambda t: t['name'])

    # ── sesiones de ESTADO ───────────────────────────────────────────────────
    M.sessions = parse_sessions(files.get('docs/ESTADO.md', {}).get('text', ''))
    env_all = sorted(env_names)
    for s in M.sessions:
        s['files'] = sorted(_mentions(s['body'] + '\n' + s['heading'], files, M.unique_base, mods))
        s['envs'] = sorted(nm for nm in env_all if '{X}' not in nm and re.search(r'(?<![A-Z0-9_])' + re.escape(nm) +
                                                                               r'(?![A-Z0-9_])', s['body']))
    for path, f in files.items():
        if f['role'] == 'doc' and path != 'docs/ESTADO.md':
            f['mentions'] = sorted(p for p in _mentions(f['text'], files, M.unique_base, mods) if p != path)

    _build_edges(M)
    return M


def _window_aliases(code_text):
    """Nombres que el archivo usa como sinónimo de window (var W = window; (function (root){…})(window))."""
    al = set(re.findall(r'\b(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:window|globalThis)\s*[;,\n)]', code_text))
    if re.search(r'\}\)\(\s*(?:window|globalThis|this|typeof window[^)]*)\)\s*;?\s*$', code_text.rstrip()):
        m = re.match(r'\s*(?:[\'"]use strict[\'"];?\s*)?\(\s*function\s*\(\s*([A-Za-z_$][\w$]*)', code_text)
        if m:
            al.add(m.group(1))
    changed = True
    while changed:
        changed = False
        for a in sorted(al):
            for b in re.findall(r'\b(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=\s*' + re.escape(a) + r'\s*[;,\n]',
                                code_text):
                if b not in al:
                    al.add(b)
                    changed = True
    return sorted(al - {'window', 'globalThis'})


def _analyze_js(text):
    sc = JSScan(text)
    aliases = _window_aliases(sc.code)
    if aliases:
        rx = re.compile(r'(?<![\w$.])(?:' + '|'.join(re.escape(a) for a in aliases) + r')\.')
        sc.code = rx.sub('window.', sc.code)
        sc.code_ns = rx.sub('window.', sc.code_ns)
    bare, win = js_identifiers(sc.code)
    bare_code, _w = js_identifiers(sc.code_ns, skip_keys=True)
    defs = set(_WIN_DEF.findall(sc.code)) | set(_WIN_DEF2.findall(sc.code)) | set(_WIN_DEF3.findall(sc.code))
    joined = '\n'.join(sc.strings)
    return {'code': sc.code, 'strings': sc.strings, 'top': sorted(set(sc.top)), 'win_defs': sorted(defs),
            'bare': bare, 'bare_code': bare_code, 'str_calls': set(_STR_CALL.findall(joined)),
            'str_uses': _str_uses(joined), 'rel': relative_refs(js_concat_chains(sc.code_cs) + sc.templates),
            'win': win, 'local': js_local_decls(sc.code_ns), 'scripts': [], 'blocks': [],
            'str_ids': set(_ID_RX.findall(joined)), 'win_reads': set(_WIN_READ.findall(sc.code))}


_STR_CALL = re.compile(r'(?<![\w$.])([A-Za-z_$][\w$]*)\s*\(')
# usos dentro de un TEXTO (onclick="X(…)", "X.open()", "window.X"): no basta con nombrar la palabra
_STR_USE = re.compile(r'(?<![\w$.])([A-Za-z_$][\w$]*)\s*(?:\(|\.[A-Za-z_$])|(?<![\w$.])window\.([A-Za-z_$][\w$]*)')
_JS_STR = re.compile(r"""'(?:[^'\\\n]|\\.)*'|"(?:[^"\\\n]|\\.)*\"""")
_JS_OPERAND_ID = re.compile(r'[A-Za-z_$][\w$]*(?:\s*\.\s*[A-Za-z_$][\w$]*)*')


def _str_uses(text):
    out = set()
    for a, b in _STR_USE.findall(text):
        out.add(a or b)
    return out


def js_concat_chains(code):
    """Concatenaciones que arman una ruta RELATIVA: '/clients/' + id + '/audit' → '/clients/◊/audit' y
    API + '/status' → '◊/status'. Un texto en medio de una cadena ('/audit' tras + id +) no se cuenta solo."""
    out = []
    n = len(code)

    def ws(i):
        while i < n and code[i] in ' \t\r\n':
            i += 1
        return i

    def back_ws(i):
        while i >= 0 and code[i] in ' \t\r\n':
            i -= 1
        return i

    for m in _JS_STR.finditer(code):
        body = m.group()[1:-1]
        if not body.startswith('/') or body.startswith(ENDPOINT_ROOTS):
            continue
        prefix = ''
        k = back_ws(m.start() - 1)
        if k >= 0 and code[k] == '+' and (k == 0 or code[k - 1] != '+'):
            # ¿qué hay antes del +? solo vale un nombre simple (API, this.base) que ABRE la cadena
            j = back_ws(k - 1)
            e = j + 1
            while j >= 0 and (code[j].isalnum() or code[j] in '_$.'):
                j -= 1
            name = code[j + 1:e]
            if not name or not _JS_OPERAND_ID.fullmatch(name):
                continue
            jj = back_ws(j)
            if jj >= 0 and code[jj] == '+':
                continue
            prefix = '◊'
        parts = [prefix, body]
        i = m.end()
        while True:
            j = ws(i)
            if j >= n or code[j] != '+' or code[j + 1:j + 2] in ('+', '='):
                break
            j = ws(j + 1)
            sm = _JS_STR.match(code, j)
            if sm:
                parts.append(sm.group()[1:-1])
                i = sm.end()
                continue
            k, depth = j, 0
            while k < n:
                c = code[k]
                if c in '\'"':
                    q = _JS_STR.match(code, k)
                    k = q.end() if q else k + 1
                    continue
                if c in '([{':
                    depth += 1
                elif c in ')]}':
                    if depth == 0:
                        break
                    depth -= 1
                elif depth == 0 and c in '+,;?:`':
                    break
                k += 1
            if k == j:
                break
            parts.append('◊')
            i = k
        out.append(''.join(parts))
    return out


def relative_refs(chains):
    """Rutas relativas limpias ('/clients/◊/audit') a partir de las cadenas armadas."""
    out = set()
    for s in chains:
        s = s[1:] if s.startswith('◊/') else s
        s = re.split(r'[?#\s]', s, maxsplit=1)[0]
        if not re.match(r'^/[A-Za-z_◊]', s) or s.startswith(ENDPOINT_ROOTS) or len(s) > 120:
            continue
        if re.search(r'[\'"<>{}\\=]', s.replace('◊', '')):
            continue
        out.add(s)
    return sorted(out)
_SCRIPT_RX = re.compile(r'<script\b([^>]*)>([\s\S]*?)</script\s*>', re.I)


def _analyze_html(text):
    codes, codes_ns, strings, top, defs = [], [], [], [], set()
    scripts, blocks, chains = [], [], []
    markup = []
    last = 0
    for m in _SCRIPT_RX.finditer(text):
        markup.append(text[last:m.start()])
        last = m.end()
        attrs, body = m.group(1), m.group(2)
        line = text.count('\n', 0, m.start()) + 1
        src = re.search(r'''\bsrc\s*=\s*["']([^"']+)["']''', attrs)
        if src:
            s = src.group(1).split('?')[0].lstrip('/')
            scripts.append({'src': s, 'line': line, 'kind': 'src'})
            continue
        sc = JSScan(body)
        codes.append(sc.code)
        codes_ns.append(sc.code_ns)
        strings.extend(sc.strings)
        chains.extend(js_concat_chains(sc.code_cs) + sc.templates)
        top.extend(sc.top)
        defs |= set(_WIN_DEF.findall(sc.code)) | set(_WIN_DEF2.findall(sc.code)) | set(_WIN_DEF3.findall(sc.code))
        n_lines = body.count('\n') + 1
        hdr = js_header(body)
        nfun = len(re.findall(r'(?m)^\s{0,2}(?:async\s+)?function\s+[A-Za-z_$]', body))
        blocks.append({'line': line, 'lines': n_lines, 'header': first_paragraph(hdr, 160), 'functions': nfun})
        scripts.append({'src': '', 'line': line, 'kind': 'inline', 'block': len(blocks)})
    markup.append(text[last:])
    mk = re.sub(r'<!--[\s\S]*?-->', ' ', ''.join(markup))
    code_all = '\n'.join(codes) + '\n' + mk
    for q in re.findall(r'''["'`](/(?:api|v1|mcp|oauth|\.well-known)[^"'`\s]*)["'`]''', mk):
        strings.append(q)
    bare, win = js_identifiers(code_all)
    # bare_code = solo CÓDIGO (sin el texto de cadenas ni el HTML); en textos y HTML vale X( / X.algo / window.X
    bare_code, _w = js_identifiers('\n'.join(codes_ns), skip_keys=True)
    str_calls = set(_STR_CALL.findall('\n'.join(strings) + '\n' + mk))
    str_uses = _str_uses('\n'.join(strings) + '\n' + mk)
    tabs = []
    for m in re.finditer(r'<button[^>]*\bclass="tab[^"]*"[^>]*>([\s\S]*?)</button>', text):
        tag = m.group(0)
        dt = re.search(r'data-tab="([^"]+)"', tag)
        grp = re.search(r'data-group="([^"]+)"', tag)
        tid = re.search(r'\bid="([^"]+)"', tag)
        label = re.sub(r'<[^>]+>', ' ', m.group(1))
        label = re.sub(r'\s+', ' ', label).strip()
        tabs.append({'tab': dt.group(1) if dt else '', 'group': grp.group(1) if grp else '',
                     'id': tid.group(1) if tid else '', 'label': label})
    title = re.search(r'<title>([^<]*)</title>', text)
    return {'code': code_all, 'strings': strings, 'top': sorted(set(top)), 'win_defs': sorted(defs),
            'bare': bare, 'bare_code': bare_code, 'str_calls': str_calls, 'str_uses': str_uses,
            'rel': relative_refs(chains), 'win': win,
            'local': js_local_decls('\n'.join(codes_ns)), 'scripts': scripts,
            'str_ids': set(_ID_RX.findall('\n'.join(strings) + '\n' + mk)), 'win_reads': set(_WIN_READ.findall(code_all)),
            'blocks': blocks, 'tabs': tabs, 'title': title.group(1).strip() if title else ''}


def _md_purpose(text):
    lines = text.split('\n')
    title = ''
    body = []
    for ln in lines:
        if not title and ln.startswith('# '):
            title = ln[2:].strip()
            continue
        if title or ln.strip():
            body.append(ln)
    paras = [p for p in re.split(r'\n\s*\n', '\n'.join(body)) if p.strip() and not p.strip().startswith(('#', '---', '```'))]
    first = first_paragraph(paras[0], 500) if paras else ''
    return (title + ' — ' + first) if title and first else (title or first)


def parse_claude_env_block(text):
    m = re.search(r'## Variables de entorno\s*\n```[^\n]*\n([\s\S]*?)\n```', text)
    names = set()
    if not m:
        return names
    for ln in m.group(1).split('\n'):
        ln = ln.split('←')[0]
        ln = re.sub(r'\([^)]*\)', ' ', ln)
        ln = re.sub(r'=\S*', ' ', ln)
        prev_full = None
        for tok in re.findall(r'/?\s*_?[A-Z][A-Z0-9_]*(?:/[A-Z][A-Z0-9_]*)*', ln):
            t = tok.replace(' ', '')
            if t.startswith('/_') or t.startswith('_'):
                if prev_full:
                    t = prev_full.rsplit('_', 1)[0] + '_' + t.lstrip('/_')
                    names.add(t)
                continue
            t = t.lstrip('/')
            parts = t.split('/')
            base = parts[0]
            if '_' not in base:
                continue
            names.add(base)
            prev_full = base
            for p in parts[1:]:
                names.add(p if '_' in p else base.rsplit('_', 1)[0] + '_' + p)
    return names


def env_documented(M, name):
    if name in M.claude_block:
        return True
    if '{X}' in name:
        pre = name.split('{X}')[0]
        return any(b.startswith(pre) for b in M.claude_block) or \
            re.search(re.escape(pre) + r'[<{*]', M.claude_text) is not None
    return re.search(r'(?<![A-Z0-9_])' + re.escape(name) + r'(?![A-Z0-9_])', M.claude_text) is not None


def env_is_read(M, name):
    """¿Alguien la lee? (directo, por patrón f'PREFIJO_{x}' o en despliegue)"""
    if name in M.env_readers or name in M.infra_env:
        return True
    return any(n.endswith('{X}') and name.startswith(n[:-3]) for n in M.env_readers)


def _mcp_tools(f, mods):
    py = f['py']
    tree = py['_tree']
    top_fns = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}

    def direct(fn):
        found = set()
        called = set()
        for sub in ast.walk(fn):
            if isinstance(sub, ast.Import):
                for a in sub.names:
                    d = _resolve_import(mods, a.name, None)
                    if d:
                        found.add(d)
            elif isinstance(sub, ast.ImportFrom) and sub.module and not sub.level:
                for a in sub.names:
                    d = _resolve_import(mods, sub.module, a.name)
                    if d:
                        found.add(d)
            elif isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id in top_fns:
                called.add(sub.func.id)
        for s in dyn_module_refs(fn):
            if s in mods:
                found.add(mods[s])
        return found, called

    cache = {}

    def closure(name, stack=()):
        if name in cache:
            return cache[name]
        if name in stack:
            return set()
        found, called = direct(top_fns[name])
        out = set(found)
        for c in sorted(called):
            out |= closure(c, stack + (name,))
        cache[name] = out
        return out

    tools = []
    for t in py['tools']:
        t = dict(t)
        t['modules'] = sorted(m for m in closure(t['func']) if m != f['path'])
        t['id'] = 'mcp:' + t['name']
        tools.append(t)
    tools.sort(key=lambda t: t['name'])
    return tools


_MENTION_PATH = re.compile(r'(?<![\w/.-])((?:[\w-]+/)*[\w.-]+\.(?:py|js|html|json|md))(?![\w])')
_MENTION_DOT = re.compile(r'(?<![\w.])((?:core|research|ontology|matrix|mcp_server|brokerage|scripts)'
                          r'(?:\.[a-z_][a-z0-9_]*)+)')
# ruta SIN extensión: core/decide.chat_plan · matrix/engine · research/ask_agent · engine/statematrix
_MENTION_NOEXT = re.compile(r'(?<![\w/.-])((?:core|research|ontology|matrix|mcp_server|brokerage|engine|scripts|nodes|sim)'
                            r'(?:/[A-Za-z_][\w-]*)+)(?![\w/-])')


def _mentions(text, files, unique_base, mods):
    out = set()
    for m in _MENTION_PATH.finditer(text):
        p = m.group(1)
        if p in files:
            out.add(p)
        elif '/' not in p and p in unique_base:
            out.add(unique_base[p])
        elif '/' in p:
            tail = p.split('/', 1)[1] if p.startswith(('./', '../')) else None
            if tail and tail in files:
                out.add(tail)
    for m in _MENTION_NOEXT.finditer(text):
        p = m.group(1)
        for ext in ('.py', '.js'):
            if p + ext in files:
                out.add(p + ext)
                break
    for m in _MENTION_DOT.finditer(text):
        parts = m.group(1).split('.')
        while len(parts) > 1:
            cand = '.'.join(parts)
            if cand in mods:
                out.add(mods[cand])
                break
            parts.pop()
    return {p for p in out if files[p]['role'] != 'doc' or p != 'docs/ESTADO.md'}


def parse_sessions(text):
    lines = text.split('\n')
    heads = []
    for i, ln in enumerate(lines):
        m = re.match(r'^(#{1,3})\s+(.*\S)\s*$', ln)
        if not m:
            continue
        level, title = len(m.group(1)), m.group(2)
        dated = bool(re.search(r'20\d\d-\d\d', title)) or title.upper().startswith('SESIÓN')
        heads.append((i, level, title, dated))
    sessions = []
    for k, (i, level, title, dated) in enumerate(heads):
        if not dated:
            continue
        end = len(lines)
        for (j, lv2, _t2, d2) in heads[k + 1:]:
            if lv2 <= level or d2:
                end = j
                break
        body = '\n'.join(lines[i + 1:end]).strip('\n')
        dm = re.search(r'(20\d\d-\d\d(?:-\d\d)?)(\s*(?:/|→|->)\s*(\d\d(?:-\d\d)?))?', title)
        date = dm.group(1) if dm else ''
        date_shown = (date + ' al ' + dm.group(3)) if dm and dm.group(3) else date
        if dm and dm.group(2):
            title = title.replace(dm.group(0), date, 1)
        rest = re.sub(r'^SESI[ÓO]N\s*', '', title, flags=re.I)
        if date:
            d = re.escape(date)
            rest = re.sub(r'\(\s*' + d + r'\s*[,;]\s*', '(', rest, count=1)
            rest = re.sub(r'\(\s*' + d + r'\s*\)', '', rest, count=1)
            rest = rest.replace(date, '', 1)
        rest = re.sub(r'\(\s*\)', '', rest).strip()
        tag = re.match(r'^(\([^)]{1,12}\))\s*[—\-–:·]*\s*', rest)   # "(ii) — TÍTULO" → etiqueta junto a la fecha
        if tag:
            date_tag = tag.group(1)
            rest = rest[tag.end():]
        else:
            date_tag = ''
        rest = re.sub(r'^[\s—\-–:·]+', '', rest).strip()
        rest = re.sub(r'\s+([,;)])', r'\1', rest)
        summary_lines = [ln.strip() for ln in body.split('\n') if ln.strip() and ln.strip() != '---'
                         and not ln.strip().startswith('#')]
        summary = ' '.join(summary_lines[:4])
        sessions.append({'heading': title, 'date': date, 'date_shown': date_shown, 'tag': date_tag, 'title': rest or title, 'line': i + 1,
                         'lines': end - i, 'body': body, 'summary': first_paragraph(summary, 520),
                         'order': len(sessions)})
    used = set()
    for s in sessions:
        head = ' '.join(x for x in ('Sesión', s['date_shown'], s['tag']) if x)
        base = safe_name(head + ' — ' + s['title'], 90)
        name, n = base, 2
        while name.lower() in used:
            name = f'{base} ({n})'
            n += 1
        used.add(name.lower())
        s['note'] = name
        s['id'] = 'session:' + s['note']
    return sessions


# ════════════════════════════════════════════════════════════════════════════
# 8. ARISTAS DEL GRAFO
# ════════════════════════════════════════════════════════════════════════════
def _build_edges(M):
    E = []
    for src in sorted(M.imports):
        for dst in sorted(M.imports[src]):
            E.append((src, dst, 'imports', ', '.join(sorted(M.imports[src][dst]))))
    for src in sorted(M.uses):
        for dst in sorted(M.uses[src]):
            E.append((src, dst, 'uses_global', ', '.join(sorted(M.uses[src][dst]))))
    for src in sorted(M.calls):
        for path in sorted(M.calls[src]):
            for r in M.routes_by_path[path]:
                E.append((src, r['id'], 'calls_endpoint', ', '.join(sorted(M.calls[src][path]))))
    for r in M.routes:
        E.append((r['file'], r['id'], 'defines_endpoint', r['func']))
    for t in M.tools:
        E.append((t.get('file', 'mcp_server/tools.py'), t['id'], 'defines_endpoint', t['func']))
        for m in t['modules']:
            E.append((t['id'], m, 'imports', 'herramienta MCP'))
    for mod in sorted(M.tested):
        for t in sorted(M.tested[mod]):
            E.append((mod, t, 'tested_by', ''))
    for nm in sorted(M.env_readers):
        for p in sorted(M.env_readers[nm]):
            E.append((p, 'env:' + nm, 'reads_env', ', '.join(sorted(M.env_readers[nm][p]))))
    for s in M.sessions:
        for p in s['files']:
            E.append((s['id'], p, 'mentions_in_session', ''))
        for nm in s['envs']:
            E.append((s['id'], 'env:' + nm, 'mentions_in_session', ''))
    for i, s in enumerate(M.app_scripts):
        if s['kind'] == 'src' and s['src'] in M.files:
            E.append(('app.html', s['src'], 'loads_script', f'#{i + 1}'))
    for src in sorted(M.file_refs):
        for dst in sorted(M.file_refs[src]):
            E.append((src, dst, 'references_file', ''))
    # sin duplicados, orden estable
    seen = set()
    out = []
    for e in E:
        k = (e[0], e[1], e[2])
        if k in seen:
            continue
        seen.add(k)
        out.append(e)
    out.sort(key=lambda e: (e[2], e[0], e[1]))
    M.edges = out
    M.env_names = sorted(set(M.env_readers) | set(M.infra_env) | (M.claude_block & set(M.env_readers)))


# ════════════════════════════════════════════════════════════════════════════
# 9. DERIVADOS: agrupaciones, grados, cosas sueltas
# ════════════════════════════════════════════════════════════════════════════
# Capa de cada grupo de API por su prefijo (/api/<segmento>/…): el dinero, la voz y los datos en vivo que
# server.py define no son "Infraestructura". Si el segmento no está, manda la capa del módulo que la define.
API_CAPA = {
    'trade': 'dinero', 'portfolio': 'dinero', 'portfolio-ai': 'dinero', 'portfolio-report': 'dinero',
    'brokerage': 'dinero',
    'voice': 'voz',
    'quote': 'vivo', 'quotes': 'vivo', 'candles': 'vivo', 'scalp': 'vivo', 'crypto': 'vivo', 'news': 'vivo',
    'market': 'vivo', 'marketstack': 'vivo', 'fundamentals': 'vivo', 'findossier': 'vivo', 'dossier': 'vivo',
    'company': 'vivo', 'earnings': 'vivo', 'insiders': 'vivo', 'investors': 'vivo', 'ipo_calendar': 'vivo',
    'macro': 'vivo', 'world': 'vivo', 'geo': 'vivo', 'space': 'vivo', 'space2': 'vivo', 'supply-chain': 'vivo',
    'ws-key': 'vivo', 'ws-token': 'vivo',
    'portfolio-risk': 'cuant', 'options': 'cuant', 'matrix': 'cuant', 'tensor': 'cuant', 'sim': 'cuant',
    'screener': 'cuant',
    'research': 'investigacion', 'deep': 'investigacion',
    'committee': 'comite',
    'ontology': 'ontologia', 'grafo': 'ontologia', 'vocabulary': 'ontologia',
    'khipu': 'chat', 'agents': 'chat', 'decide': 'chat', 'canvas': 'chat',
    'mcp': 'mcp',
    'ai': 'infra', 'health': 'infra', 'diag': 'infra', 'diagnostics': 'infra', 'ops': 'infra', 'user-state': 'infra',
}


def api_group_layer(M, g, rs):
    seg = _segs(rs[0]['path'])[1] if rs[0]['path'].startswith('/api/') and len(_segs(rs[0]['path'])) > 1 else ''
    if seg in API_CAPA:
        return API_CAPA[seg]
    if 'MCP' in g or g == 'API v1 (pública)':
        return 'mcp'
    files_ = sorted({r['file'] for r in rs})
    return M.files[files_[0]]['layer']


def api_group(path):
    if path.startswith('/api/'):
        seg = _segs(path)[1] if len(_segs(path)) > 1 else 'raíz'
        return 'API ' + safe_name(seg)
    if path.startswith('/v1/') or path == '/docs':
        return 'API v1 (pública)'
    if path.startswith(('/mcp', '/oauth', '/.well-known')):
        return 'API MCP transporte y OAuth'
    return 'API páginas y archivos estáticos'


def route_is_external(path):
    # …/oauth/callback: la llama el proveedor (Alpaca) al volver del login, no la app
    return path in ROUTE_EXTERNAL_EXACT or path.startswith(ROUTE_EXTERNAL_PREFIXES) or \
        path.startswith(ROUTE_STATIC_PREFIXES) or path == '/mcp' or path.endswith('/oauth/callback')


def derive(M):
    files = M.files
    # quién llama a cada ruta (por id)
    callers = defaultdict(set)
    for src in M.calls:
        for path in M.calls[src]:
            for r in M.routes_by_path[path]:
                callers[r['id']].add(src)
    M.route_callers = callers
    # grupos de API
    groups = defaultdict(list)
    for r in M.routes:
        r['group'] = api_group(r['path'])
        groups[r['group']].append(r)
    M.groups = dict(sorted(groups.items()))
    for g, rs in M.groups.items():
        lay = api_group_layer(M, g, rs)
        for r in rs:
            r['layer'] = lay
    # usuarios inversos
    M.imported_by = defaultdict(set)
    for src, dsts in M.imports.items():
        for d in dsts:
            M.imported_by[d].add(src)
    M.used_by = defaultdict(set)
    for src, dsts in M.uses.items():
        for d in dsts:
            M.used_by[d].add(src)
    M.referenced_by = defaultdict(set)
    for src, dsts in M.file_refs.items():
        for d in dsts:
            M.referenced_by[d].add(src)
    M.loaded_at = {}
    for i, s in enumerate(M.app_scripts):
        if s['kind'] == 'src':
            M.loaded_at[s['src']] = i
    M.session_mentions = defaultdict(list)
    for s in M.sessions:
        for p in s['files']:
            M.session_mentions[p].append(s)
        for nm in s['envs']:
            M.session_mentions['env:' + nm].append(s)
    M.tool_users = defaultdict(list)
    for t in M.tools:
        for m in t['modules']:
            M.tool_users[m].append(t)
    # grado de acoplamiento (solo aristas de código entre archivos)
    deg_in, deg_out = defaultdict(int), defaultdict(int)
    route_file = {r['id']: r['file'] for r in M.routes}
    pairs = set()
    for (a, b, t, _d) in M.edges:
        if a not in files or files[a]['role'] in ('test', 'doc'):
            continue        # las pruebas cubren, no acoplan (y los nodos que no son archivos no cuentan)
        if t in ('imports', 'uses_global', 'loads_script', 'references_file') and b in files:
            pairs.add((a, b))
        elif t == 'calls_endpoint' and b in route_file and route_file[b] != a:
            pairs.add((a, route_file[b]))
    for a, b in pairs:
        deg_out[a] += 1
        deg_in[b] += 1
    M.code_pairs = pairs
    M.deg_in, M.deg_out = deg_in, deg_out


# ════════════════════════════════════════════════════════════════════════════
# 10. NOTAS
# ════════════════════════════════════════════════════════════════════════════
def capa_link(key):
    return link('Capa ' + safe_name(CAPA[key][1]))


def capa_note_name(key):
    return 'Capa ' + safe_name(CAPA[key][1])


def env_note(nm):
    return 'ENV ' + nm


def tags_for(layer, tipo):
    return [CAPA[layer][2], 'tipo/' + tipo]


def _flink(M, p):
    return link(M.files[p]['note'])


def _route_line(M, r):
    return f"{tcode(','.join(r['methods']))} | {tcode(r['path'])} | {tcode(r['func'])}"


def _callers_cell(M, rid, exclude=None):
    cs = sorted(M.route_callers.get(rid, ()))
    app = [c for c in cs if M.files[c]['role'] != 'test' and c != exclude]
    tests = [c for c in cs if M.files[c]['role'] == 'test']
    parts = [_flink(M, c) for c in app]
    if tests:
        parts.append(f'{len(tests)} prueba' + ('s' if len(tests) != 1 else ''))
    return ', '.join(parts) if parts else '—'


def note_module(M, p):
    f = M.files[p]
    role = f['role']
    tipo = {'code': 'modulo', 'data': 'datos', 'page': 'pagina', 'test': 'prueba', 'doc': 'documento'}[role]
    lang = {'py': 'python', 'js': 'javascript', 'html': 'html', 'json': 'json', 'md': 'markdown'}[f['ext']]
    out = [fm({'tipo': tipo, 'capa': CAPA[f['layer']][1], 'ruta': p, 'lenguaje': lang, 'lineas': f['lines'],
               'aliases': [p], 'tags': tags_for(f['layer'], tipo)})]
    out.append(f'# {p}\n')
    kind_es = {'code': 'Módulo', 'data': 'Datos', 'page': 'Página', 'test': 'Prueba', 'doc': 'Documento'}[role]
    out.append(f"> {kind_es} · capa {capa_link(f['layer'])} · {miles(f['lines'])} líneas · {code(p)}\n")
    if role == 'page':
        out.extend(_page_sections(M, p))
    elif role == 'doc':
        out.extend(_doc_sections(M, p))
    elif role == 'test':
        out.extend(_test_sections(M, p))
    else:
        out.append('## Para qué sirve\n')
        out.append((prose(f['purpose']) or '_(sin cabecera ni docstring)_') + '\n')
        if role == 'data':
            out.extend(_data_sections(M, p))
        out.extend(_api_sections(M, p))
        out.extend(_dep_sections(M, p))
    out.extend(_endpoint_sections(M, p))
    out.extend(_env_sections(M, p))
    if role not in ('test', 'doc'):
        ts = sorted(M.tested.get(p, ()))
        out.append('## Pruebas que lo cubren\n')
        out.append('\n'.join('- ' + _flink(M, t) for t in ts) + '\n' if ts else
                   '_Ninguna prueba lo importa ni menciona su ruta._\n')
    ss = M.session_mentions.get(p, [])
    if ss:
        out.append('## Mencionado en sesiones de trabajo\n')
        recent = ss[:12]
        out.append('\n'.join(f"- {link(s['note'])}" for s in recent) + '\n')
        if len(ss) > len(recent):
            out.append(f'_…y {len(ss) - len(recent)} sesiones más antiguas._\n')
    return '\n'.join(out)


def _api_sections(M, p):
    f = M.files[p]
    out = []
    if f['ext'] == 'py':
        defs = f['py']['defs']
        pub = [d for d in defs if not d['name'].startswith('_')]
        priv = [d for d in defs if d['name'].startswith('_')]
        out.append('## API pública\n')
        if pub:
            for d in pub:
                lbl = ('clase ' if d['kind'] == 'clase' else '') + code(d['name'] + d['sig'])
                out.append(f"- {lbl}" + (f" — {prose(d['doc'])}" if d['doc'] else '') + f" _(línea {d['line']})_")
            out.append('')
        else:
            out.append('_Sin funciones ni clases públicas de nivel superior._\n')
        if priv:
            names = [d['name'] for d in priv]
            shown = names[:60]
            out.append('**Internas** (empiezan con `_`): ' + ', '.join(code(n) for n in shown) +
                       (f' y {len(names) - len(shown)} más' if len(names) > len(shown) else '') + '\n')
        if f['py']['tools']:
            out.append(f"Define **{len(f['py']['tools'])} herramientas MCP** → {link('API herramientas MCP')}\n")
    elif f['ext'] == 'js':
        js = f['js']
        wins = js['win_defs']
        tops = [t for t in js['top'] if t not in wins]
        out.append('## API pública (globales que define)\n')
        if wins:
            out.append(', '.join(code('window.' + n) for n in wins) + '\n')
        if tops:
            out.append('De nivel superior (globales del script): ' +
                       ', '.join(code(n) for n in tops[:80]) +
                       (f' y {len(tops) - 80} más' if len(tops) > 80 else '') + '\n')
        if not wins and not tops:
            out.append('_No define globales (código encapsulado)._\n')
    return out


def _dep_sections(M, p):
    f = M.files[p]
    out = ['## Depende de\n']
    items = []
    for d in sorted(M.imports.get(p, {})):
        names = sorted(M.imports[p][d])
        items.append(f"- {_flink(M, d)} — importa {', '.join(code(n) for n in names[:8])}"
                     + (' …' if len(names) > 8 else ''))
    for d in sorted(M.uses.get(p, {})):
        names = sorted(M.uses[p][d])
        items.append(f"- {_flink(M, d)} — usa {', '.join(code(n) for n in names[:10])}"
                     + (f' y {len(names) - 10} más' if len(names) > 10 else ''))
    for d in sorted(M.file_refs.get(p, ())):
        items.append(f"- {_flink(M, d)} — lo nombra por su ruta")
    out.append('\n'.join(items) + '\n' if items else '_Nada interno._\n')
    if p in M.loaded_at:
        i = M.loaded_at[p]
        scr = M.app_scripts
        prev = next((s for s in reversed(scr[:i]) if s['kind'] == 'src' and s['src'] in M.files), None)
        nxt = next((s for s in scr[i + 1:] if s['kind'] == 'src' and s['src'] in M.files), None)
        txt = f"Se carga en {link('app.html')} en la posición **{i + 1} de {len(scr)}** (línea {scr[i]['line']})"
        if prev:
            txt += f", después de {_flink(M, prev['src'])}"
        if nxt:
            txt += f" y antes de {_flink(M, nxt['src'])}"
        out.append(txt + '.\n')
    out.append('## Lo usan\n')
    users = []
    if p in M.loaded_at:
        users.append(f"- {link('app.html')} — lo carga con `<script>` (posición {M.loaded_at[p] + 1})")
    test_importers = 0
    for u in sorted(M.imported_by.get(p, ())):
        if M.files[u]['role'] == 'test':
            test_importers += 1
            continue
        users.append(f'- {_flink(M, u)} — lo importa')
    for u in sorted(M.used_by.get(p, ())):
        names = sorted(M.uses[u][p])
        users.append(f"- {_flink(M, u)} — usa {', '.join(code(n) for n in names[:8])}"
                     + (f' y {len(names) - 8} más' if len(names) > 8 else ''))
    for u in sorted(M.referenced_by.get(p, ())):
        users.append(f'- {_flink(M, u)} — lo nombra por su ruta')
    for t in M.tool_users.get(p, []):
        users.append(f"- herramienta MCP {code(t['name'])} → {link('API herramientas MCP')}")
    out.append('\n'.join(users) + '\n' if users else '_Nadie dentro de la app (ver_ ' + link('01 Reporte del grafo') +
               '_)._\n')
    if test_importers:
        out.append(f'_Además lo importan {test_importers} pruebas (lista abajo)._\n')
    return out


def _endpoint_sections(M, p):
    out = []
    rs = [r for r in M.routes if r['file'] == p]
    if rs:
        out.append('## Endpoints que define\n')
        out.append('| Método | Ruta | Función | Lo llaman |')
        out.append('|---|---|---|---|')
        for r in rs:
            out.append(f"| {_route_line(M, r)} | {_callers_cell(M, r['id'], exclude=p)} |")
        grps = sorted({r['group'] for r in rs})
        out.append('\nGrupos: ' + ', '.join(link(g) for g in grps) + '\n')
    calls = M.calls.get(p, {})
    if calls and M.files[p]['role'] != 'test':
        out.append('## Endpoints que llama\n')
        rows = []
        for path in sorted(calls):
            for r in M.routes_by_path[path]:
                rows.append(f"- {code(','.join(r['methods']) + ' ' + r['path'])} → {_flink(M, r['file'])}"
                            f" ({link(r['group'])})")
        out.append('\n'.join(sorted(set(rows))) + '\n')
    um = M.unmatched_calls.get(p)
    if um:
        out.append('**Rutas que nombra y no existen en el servidor** (¿restos viejos?): ' +
                   ', '.join(code(u) for u in sorted(um)) + '\n')
    return out


def _env_sections(M, p):
    names = sorted(nm for nm in M.env_readers if p in M.env_readers[nm])
    if not names:
        return []
    out = ['## Variables de entorno que lee (solo nombres)\n']
    items = []
    for nm in names:
        kinds = M.env_readers[nm][p]
        extra = ' _(en una lista, p. ej. para tapar secretos en logs)_' if kinds == {'lista'} else ''
        items.append(f'- {link(env_note(nm))}{extra}')
    out.append('\n'.join(items) + '\n')
    return out


def _data_sections(M, p):
    f = M.files[p]
    out = ['## Qué datos contiene\n']
    if f['ext'] == 'json':
        try:
            d = json.loads(f['text'])
        except ValueError:
            d = None
        rows = []
        if isinstance(d, dict):
            for k in d:
                v = d[k]
                if isinstance(v, (list, dict)):
                    rows.append(f'| {tcode(k)} | {"lista" if isinstance(v, list) else "objeto"} | {miles(len(v))} |')
                elif isinstance(v, str) and re.match(r'20\d\d-\d\d-\d\d', v):
                    rows.append(f'| {tcode(k)} | fecha | {tcode(v[:25])} |')
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    rows.append(f'| {tcode(k)} | número | {v} |')
        if rows:
            out.append('| Clave | Tipo | Tamaño / valor |\n|---|---|---|\n' + '\n'.join(rows) + '\n')
    else:
        t = f['js']['code']
        stats = []
        n_ids = len(re.findall(r'''\bid\s*:\s*['"]''', t))
        n_links = len(re.findall(r'''(?m)^\s*\[\s*['"][^'"\n]+['"]\s*,\s*['"]''', t)) + \
            len(re.findall(r'''\{\s*s\s*:\s*['"][^'"]+['"]\s*,\s*t\s*:''', t))
        n_keys = len(re.findall(r'''(?m)^ {2,4}['"]?[^\s'":\[\]{}]+['"]?\s*:\s*[\{\[]''', t))
        if n_ids:
            stats.append(f'- ~{miles(n_ids)} objetos con `id` (empresas, hechos u objetos)')
        if n_links:
            stats.append(f'- ~{miles(n_links)} filas de vínculos (`[origen, destino, …]` o `{{s, t}}`)')
        if n_keys and not n_ids:
            stats.append(f'- ~{miles(n_keys)} entradas con clave')
        stats.append(f'- {miles(len(f["text"].encode("utf-8")) // 1024)} KB')
        out.append('\n'.join(stats) + '\n')
        out.append('_Conteos aproximados por patrón de texto (no se ejecuta el JavaScript)._\n')
    return out


def _page_sections(M, p):
    f = M.files[p]
    js = f['js']
    out = ['## Para qué sirve\n',
           prose(f"{js.get('title') or 'Khipus'}: TODA la interfaz en un solo archivo HTML. Arranca Khipus OS "
                 "(la Cabina con el chat y las ventanas); la vista clásica conserva las pestañas.") + '\n']
    tabs = js.get('tabs') or []
    if tabs:
        out.append('## Pestañas\n')
        out.append('| Botón | data-tab | Grupo | id |\n|---|---|---|---|')
        for t in tabs:
            out.append(f"| {cell(t['label'])} | {tcode(t['tab'] or '—')} | {tcode(t['group'] or '—')} | {tcode(t['id'])} |")
        out.append('')
    out.append('## Orden de carga de scripts\n')
    for i, s in enumerate(js['scripts']):
        if s['kind'] == 'inline':
            b = js['blocks'][s['block'] - 1]
            out.append(f"{i + 1}. bloque `<script>` inline #{s['block']} (línea {s['line']}, {miles(b['lines'])} líneas)")
        elif s['src'] in M.files:
            out.append(f"{i + 1}. {_flink(M, s['src'])} (línea {s['line']})")
        else:
            out.append(f"{i + 1}. {code(s['src'])} — externo/vendor (línea {s['line']})")
    out.append('')
    out.append('## Bloques `<script>` inline\n')
    out.append('| # | Línea | Líneas | Funciones | Cabecera |\n|---|---|---|---|---|')
    for k, b in enumerate(js['blocks']):
        out.append(f"| {k + 1} | {b['line']} | {miles(b['lines'])} | {b['functions']} | {cell(b['header']) or '—'} |")
    out.append('')
    wins = js['win_defs']
    out.append('## API pública (globales window.* que define)\n')
    out.append(', '.join(code('window.' + n) for n in wins) + '\n' if wins else '_ninguna_\n')
    tops = [t for t in js['top'] if t not in wins]
    if tops:
        out.append(f'Además declara **{len(tops)}** funciones/constantes de nivel superior en sus bloques inline '
                   '(globales del navegador): ' + ', '.join(code(n) for n in tops[:120]) +
                   (f' y {len(tops) - 120} más' if len(tops) > 120 else '') + '\n')
    out.extend(_dep_sections(M, p))
    return out


def _doc_sections(M, p):
    f = M.files[p]
    out = ['## De qué trata\n', (prose(f['purpose']) or '_(sin título)_') + '\n']
    if p == 'docs/ESTADO.md':
        out.append(f"Es la memoria entre sesiones: cada encabezado con fecha es una nota en "
                   f"{link('Índice de sesiones')} ({len(M.sessions)} sesiones).\n")
    ms = f.get('mentions') or []
    if ms:
        out.append('## Menciona\n')
        out.append('\n'.join('- ' + _flink(M, m) for m in ms) + '\n')
    return out


def _test_sections(M, p):
    f = M.files[p]
    out = ['## Qué prueba\n', (prose(f['purpose']) or '_(sin docstring)_') + '\n']
    if f['ext'] == 'py':
        n = len(re.findall(r'(?m)^\s*(?:async\s+)?def test_', f['text']))
        out.append(f'**{n}** funciones `test_…`.\n')
    cov = sorted(m for m, ts in M.tested.items() if p in ts)
    out.append('## Cubre\n')
    out.append('\n'.join('- ' + _flink(M, m) for m in cov) + '\n' if cov else
               '_No importa ni nombra un módulo concreto (prueba transversal)._\n')
    cs = M.calls.get(p, {})
    if cs:
        groups = sorted({r['group'] for path in cs for r in M.routes_by_path[path]})
        out.append('## Rutas HTTP que llama\n')
        out.append(f"{miles(len(cs))} rutas, de los grupos: " + ', '.join(link(g) for g in groups) + '\n')
    envs = sorted(nm for nm, ts in M.test_env.items() if p in ts)
    if envs:
        out.append('## Variables de entorno que fija o nombra\n')
        out.append(', '.join(link(env_note(nm)) for nm in envs) + '\n')
    return out


def note_api_group(M, g):
    rs = M.groups[g]
    files_ = sorted({r['file'] for r in rs})
    layer = rs[0]['layer']
    out = [fm({'tipo': 'api', 'capa': CAPA[layer][1], 'rutas': len(rs), 'tags': tags_for(layer, 'api')})]
    out.append(f'# {g}\n')
    pref = sorted({'/'.join(r['path'].split('/')[:3]) for r in rs})
    out.append(f"> {len(rs)} rutas · definidas en " + ', '.join(_flink(M, x) for x in files_) +
               ' · prefijo ' + ', '.join(code(x) for x in pref[:4]) + '\n')
    if g == 'API v1 (pública)':
        out.append('**API pública MONETIZADA por tiers (JWT). No se usa para funciones internas.**\n')
    out.append('Cómo seguir el camino: **pantalla (JS) → ruta → módulo que responde**.\n')
    out.append('| Método | Ruta | Función | Módulo | Lo llaman |\n|---|---|---|---|---|')
    for r in rs:
        out.append(f"| {_route_line(M, r)} | {_flink(M, r['file'])} | {_callers_cell(M, r['id'])} |")
    out.append('')
    return '\n'.join(out)


def note_mcp_tools(M):
    out = [fm({'tipo': 'api', 'capa': CAPA['mcp'][1], 'herramientas': len(M.tools),
               'tags': tags_for('mcp', 'api')})]
    out.append('# API herramientas MCP\n')
    out.append(f"> {len(M.tools)} herramientas definidas en {link('mcp_server.tools.py')} (y las v2 en "
               f"{link('mcp_server.ops.py')}) y servidas por "
               f"{link('mcp_server.api.py')} en `POST /mcp` (JSON-RPC). Alcances: **read** (consultas), "
               "**research** (gasta presupuesto de IA), **trade** (solo PROPONE órdenes; siempre aprobación humana).\n")
    out.append('| Herramienta | Alcance | Solo lectura | Función | Módulos que usa |\n|---|---|---|---|---|')
    for t in M.tools:
        mods = ', '.join(_flink(M, m) for m in t['modules']) or '—'
        out.append(f"| {tcode(t['name'])} | {t['scope']} | {'sí' if t['read_only'] else '**no**'} | "
                   f"{tcode(t['func'])} | {mods} |")
    out.append('')
    out.append(f"El chat de Khipu ({link('core.khipu_chat.py')}) reutiliza estas mismas herramientas, solo las de lectura.\n")
    return '\n'.join(out)


def note_api_index(M):
    out = [fm({'tipo': 'indice', 'capa': CAPA['mcp'][1], 'tags': tags_for('mcp', 'indice')})]
    out.append('# Índice de la API\n')
    out.append(f"{len(M.routes)} rutas HTTP en {len(M.groups)} grupos + {len(M.tools)} herramientas MCP.\n")
    out.append('| Grupo | Rutas | Definidas en |\n|---|---|---|')
    for g, rs in M.groups.items():
        fs = sorted({r['file'] for r in rs})
        out.append(f"| {link(g)} | {len(rs)} | {', '.join(_flink(M, x) for x in fs)} |")
    out.append(f"| {link('API herramientas MCP')} | {len(M.tools)} | {link('mcp_server.tools.py')} |")
    out.append('')
    return '\n'.join(out)


def note_env(M, nm):
    readers = M.env_readers.get(nm, {})
    infra = sorted(M.infra_env.get(nm, ()))
    doc_block = nm in M.claude_block
    doc_any = env_documented(M, nm)
    layer = 'infra'
    out = [fm({'tipo': 'variable', 'capa': CAPA[layer][1], 'nombre': nm, 'documentada': doc_any,
               'tags': tags_for(layer, 'variable')})]
    out.append(f'# {nm}\n')
    out.append('> Variable de entorno · se configura en Railway (Variables). Aquí solo el **nombre**, nunca el valor.\n')
    out.append('## La leen\n')
    items = []
    for p in sorted(readers):
        kinds = readers[p]
        extra = ' _(en una lista de nombres, p. ej. para tapar secretos en logs)_' if kinds == {'lista'} else ''
        items.append(f'- {_flink(M, p)}{extra}')
    for p in infra:
        items.append(f'- {code(p)} (despliegue)')
    out.append('\n'.join(items) + '\n' if items else '_Nadie la lee en el código (ver_ ' +
               link('01 Reporte del grafo') + '_)._\n')
    ts = sorted(M.test_env.get(nm, ()))
    if ts:
        out.append('## Pruebas que la fijan o nombran\n')
        out.append('\n'.join('- ' + _flink(M, t) for t in ts) + '\n')
    out.append('## ¿Está documentada en CLAUDE.md?\n')
    if doc_block:
        out.append(f"Sí — en la lista **Variables de entorno** de {link('Doc CLAUDE')}.\n")
    elif doc_any:
        out.append(f"Sí — mencionada en el texto de {link('Doc CLAUDE')} (no en la lista de variables).\n")
    else:
        out.append(f"**No** — falta en {link('Doc CLAUDE')}.\n")
    ss = M.session_mentions.get('env:' + nm, [])
    if ss:
        out.append('## Mencionada en sesiones\n')
        out.append('\n'.join(f"- {link(s['note'])}" for s in ss[:10]) + '\n')
    return '\n'.join(out)


def note_env_index(M):
    out = [fm({'tipo': 'indice', 'capa': CAPA['infra'][1], 'tags': tags_for('infra', 'indice')})]
    out.append('# Índice de variables de entorno\n')
    out.append(f"{len(M.env_names)} variables. Solo nombres: los valores viven en Railway y nunca entran a la bóveda.\n")
    out.append('| Variable | La leen | En CLAUDE.md |\n|---|---|---|')
    for nm in M.env_names:
        n = len(M.env_readers.get(nm, {})) + len(M.infra_env.get(nm, ()))
        out.append(f"| {link(env_note(nm))} | {n} | {'sí' if env_documented(M, nm) else '**no**'} |")
    out.append('')
    return '\n'.join(out)


def note_session(M, s, prev, nxt):
    out = [fm({'tipo': 'sesion', 'capa': CAPA['docs'][1], 'fecha': s['date'],
               'ruta': f"docs/ESTADO.md#L{s['line']}", 'tags': tags_for('docs', 'sesion')})]
    out.append(f"# {prose(s['heading'])}\n")
    out.append(f"> Sesión de trabajo · {code('docs/ESTADO.md')} línea {s['line']} ({s['lines']} líneas) · "
               f"{link('Índice de sesiones')}\n")
    out.append('## Resumen\n')
    out.append((prose(s['summary']) or '_(sin texto)_') + '\n')
    if s['files']:
        out.append('## Archivos que menciona\n')
        out.append('\n'.join('- ' + _flink(M, p) for p in s['files']) + '\n')
    if s['envs']:
        out.append('## Variables que menciona\n')
        out.append(', '.join(link(env_note(nm)) for nm in s['envs']) + '\n')
    nav = []
    if nxt:   # más abajo en ESTADO.md = más antigua
        nav.append('← más antigua: ' + link(nxt['note']))
    if prev:  # más arriba = más nueva
        nav.append('más nueva: ' + link(prev['note']) + ' →')
    if nav:
        out.append(' · '.join(nav) + '\n')
    return '\n'.join(out)


def note_session_index(M):
    out = [fm({'tipo': 'indice', 'capa': CAPA['docs'][1], 'tags': tags_for('docs', 'indice')})]
    out.append('# Índice de sesiones\n')
    out.append(f"{len(M.sessions)} sesiones de trabajo leídas de {link('Doc ESTADO')}, en el orden del archivo "
               "(lo más nuevo arriba).\n")
    for s in M.sessions:
        out.append(f"- {link(s['note'])} — {len(s['files'])} archivos")
    out.append('')
    return '\n'.join(out)


def note_test_index(M):
    out = [fm({'tipo': 'indice', 'capa': CAPA['pruebas'][1], 'tags': tags_for('pruebas', 'indice')})]
    out.append('# Índice de pruebas\n')
    ts = [p for p, f in M.files.items() if f['role'] == 'test']
    out.append(f"{len(ts)} archivos de prueba. Correr todo: `python -m pytest tests/ -q`.\n")
    out.append('| Prueba | Funciones test_ | Módulos que cubre |\n|---|---|---|')
    for p in ts:
        f = M.files[p]
        n = len(re.findall(r'(?m)^\s*(?:async\s+)?def test_', f['text'])) if f['ext'] == 'py' else 0
        cov = sum(1 for m, s in M.tested.items() if p in s)
        out.append(f"| {_flink(M, p)} | {n} | {cov} |")
    out.append('')
    return '\n'.join(out)


def note_layer(M, key):
    c = CAPA[key]
    members = sorted(p for p, f in M.files.items() if f['layer'] == key)
    out = [fm({'tipo': 'capa', 'capa': c[1], 'archivos': len(members), 'tags': [c[2], 'tipo/capa']})]
    out.append(f'# Capa {c[1]}\n')
    out.append(f"> {prose(c[5])}\n")
    total = sum(M.files[p]['lines'] for p in members)
    out.append(f"**{len(members)} archivos · {miles(total)} líneas.** Volver al {link('00 Mapa de Khipus')}.\n")
    if key == 'docs':
        out.append(f"Sesiones de trabajo: {link('Índice de sesiones')}.\n")
    if key == 'pruebas':
        out.append(f"Lista completa: {link('Índice de pruebas')}.\n")
    if key == 'mcp':
        out.append(f"Rutas y herramientas: {link('Índice de la API')} · {link('API herramientas MCP')}.\n")
    if key == 'infra':
        out.append(f"Variables de entorno: {link('Índice de variables de entorno')}.\n")
    if key == 'pruebas':
        return '\n'.join(out)
    out.append('## Archivos\n')
    for p in sorted(members, key=lambda x: (-M.files[x]['lines'], x)):
        f = M.files[p]
        pur = prose(f.get('purpose') or '')
        if len(pur) > 150:
            pur = pur[:150].rsplit(' ', 1)[0] + ' …'
        out.append(f"- {_flink(M, p)} — {miles(f['lines'])} líneas" + (f" · {pur}" if pur else ''))
    out.append('')
    # conexiones con otras capas
    cnt = defaultdict(int)
    for a, b in M.code_pairs:
        la, lb = M.files[a]['layer'], M.files[b]['layer']
        if la == key and lb != key:
            cnt[('→', lb)] += 1
        elif lb == key and la != key:
            cnt[('←', la)] += 1
    if cnt:
        out.append('## Conexiones con otras capas\n')
        out.append('| Dirección | Capa | Conexiones |\n|---|---|---|')
        for (d, l2), n in sorted(cnt.items(), key=lambda x: (-x[1], x[0])):
            out.append(f"| {'usa a' if d == '→' else 'la usa'} | {capa_link(l2)} | {n} |")
        out.append('')
    return '\n'.join(out)


def note_home(M):
    out = [fm({'tipo': 'inicio', 'tags': ['tipo/inicio']})]
    out.append('# 00 Mapa de Khipus\n')
    n_code = sum(1 for f in M.files.values() if f['role'] in ('code', 'page'))
    lines = sum(f['lines'] for f in M.files.values() if f['role'] in ('code', 'page'))
    out.append('Bienvenido. Esta bóveda es un **mapa vivo del código de Khipus Finance AI**: cada archivo, ruta '
               'de la API, variable de entorno y sesión de trabajo es una nota, y los enlaces entre notas son las '
               'conexiones reales del código. La genera `scripts/build_vault.py` sin IA, leyendo el repositorio.\n')
    out.append(f"**{miles(n_code)} archivos de código ({miles(lines)} líneas) · {len(M.routes)} rutas HTTP · "
               f"{len(M.tools)} herramientas MCP · {len(M.env_names)} variables de entorno · "
               f"{len(M.sessions)} sesiones de trabajo.**\n")
    out.append(f"Empieza por {link('02 Cómo usar esta bóveda')} y mira las cosas sueltas en "
               f"{link('01 Reporte del grafo')}.\n")
    out.append('## Cómo fluye todo\n')
    out.append(f"1. **Lo que ves**: {link('app.html')} arranca Khipus OS ({link('engine.cockpit.js')}, "
               f"{link('engine.desktop.js')}, {link('engine.oswindows.js')}).\n"
               f"2. **El chat**: {link('engine.khipu_chat.js')} → `POST /api/khipu/chat` → {link('core.khipu_chat.py')}, "
               f"que usa las herramientas de {link('mcp_server.tools.py')} y la IA de {link('core.ai.py')}.\n"
               f"3. **El servidor**: {link('server.py')} registra todos los blueprints (ver {link('Índice de la API')}).\n"
               f"4. **La verdad del grafo**: el catálogo {link('nodes.merge_graph.js')} → snapshot "
               f"{link('data.grafo_v0.json')} → ontología en Postgres ({link('ontology.service.py')}).\n"
               f"5. **El dinero**: toda orden pasa por {link('brokerage.service.py')} (preview → confirmación humana).\n")
    out.append('## Capas\n')
    out.append('| Capa | Archivos | Líneas | De qué trata |\n|---|---|---|---|')
    for c in CAPAS:
        members = [p for p, f in M.files.items() if f['layer'] == c[0]]
        if not members and c[0] == 'otros':
            continue
        out.append(f"| {capa_link(c[0])} | {len(members)} | {miles(sum(M.files[p]['lines'] for p in members))} | "
                   f"{cell(c[5])} |")
    out.append('')
    out.append('## Índices\n')
    out.append(f"- {link('Índice de la API')} — rutas por grupo y quién las llama\n"
               f"- {link('API herramientas MCP')} — lo que pueden usar las IAs externas\n"
               f"- {link('Índice de variables de entorno')} — solo nombres\n"
               f"- {link('Índice de sesiones')} — la historia del proyecto (docs/ESTADO.md)\n"
               f"- {link('Índice de pruebas')}\n"
               f"- {link('Doc CLAUDE')} — las reglas del proyecto\n")
    out.append('## Mapa interactivo\n')
    out.append('Abre `_grafo/mapa.html` en el navegador (doble clic en el archivo dentro de la carpeta `vault`). '
               'Los datos en bruto están en `_grafo/graph.json`.\n')
    return '\n'.join(out)


def note_howto(M):
    out = [fm({'tipo': 'guia', 'tags': ['tipo/guia']})]
    out.append('# 02 Cómo usar esta bóveda\n')
    out.append('Una **bóveda** es simplemente una carpeta de notas que el programa gratuito **Obsidian** sabe '
               'mostrar como un mapa. Esta carpeta (`vault`) la genera Claude a partir del código de Khipus, '
               'así puedes ver de un vistazo cómo se conecta todo.\n')
    out.append('## 1. Instalar Obsidian (una sola vez)\n')
    out.append('1. Entra a **https://obsidian.md** y haz clic en **Download** (Descargar) → elige Windows.\n'
               '2. Abre el instalador descargado y sigue los pasos (siguiente, siguiente, finalizar). Es gratis.\n')
    out.append('## 2. Abrir la bóveda\n')
    out.append('1. Asegúrate de tener el proyecto actualizado en tu PC (GitHub Desktop → **Fetch origin** → '
               '**Pull origin**).\n'
               '2. Abre Obsidian → **Open folder as vault** (Abrir carpeta como bóveda).\n'
               '3. Busca la carpeta del proyecto (`Supply-Chain-for-AI`), entra y elige la carpeta **`vault`** → '
               '**Abrir**.\n'
               f"4. Abre la nota {link('00 Mapa de Khipus')}: es la portada.\n")
    out.append('## 3. Ver el grafo (el mapa de conexiones)\n')
    out.append('- Haz clic en el ícono de **puntos conectados** en la barra de la izquierda, o pulsa **Ctrl + G**.\n'
               '- Cada punto es una nota; las líneas son conexiones reales del código. Ya viene **coloreado por capa**:\n')
    out.append('| Color | Capa |\n|---|---|')
    names = {'#2a78d6': 'azul', '#eb6834': 'naranja', '#1baf7a': 'verde agua', '#eda100': 'amarillo',
             '#e87ba4': 'rosa', '#9bb51c': 'verde lima', '#6250d6': 'violeta', '#e34948': 'rojo',
             '#13a3c6': 'celeste', '#b345c4': 'morado', '#52514e': 'gris oscuro', '#8b5e34': 'marrón',
             '#9a9993': 'gris', '#b9b8b1': 'gris claro', '#7d7c76': 'gris medio'}
    for c in CAPAS:
        out.append(f"| {names.get(c[3], c[3])} | {capa_link(c[0])} |")
    out.append('| lila | sesiones de trabajo |\n| arena | variables de entorno |\n')
    out.append('- Si quieres **tus propios colores** (por ejemplo resaltar una nota), agrégalos en el panel '
               '**Groups** del grafo con otra búsqueda: se respetan y ganan a los de capa. Los colores de las capas '
               'los repone el generador.\n')
    out.append('- **Filtrar**: en el grafo abre el panel **Filters** (arriba a la derecha) y escribe en la caja de '
               'búsqueda:\n'
               '  - `path:Módulos` → solo el código\n'
               '  - `-path:Sesiones -path:Pruebas` → esconde sesiones y pruebas\n'
               '  - `tag:#capa/dinero` → solo una capa (las etiquetas están en cada nota)\n'
               '- Pasa el mouse sobre un punto para ver su nombre; haz clic para abrir la nota.\n'
               '- **Grafo local**: con una nota abierta, menú ⋯ → **Open local graph** muestra solo sus vecinos.\n')
    out.append('## 4. Buscar\n')
    out.append('- **Ctrl + O**: abrir una nota por nombre (escribe por ejemplo `cockpit` o `khipu_chat`).\n'
               '- **Ctrl + Shift + F**: buscar una palabra en todas las notas (por ejemplo `PIN` o `/api/trade`).\n'
               '- Cada nota de código dice: para qué sirve, qué funciones ofrece, de quién depende, quién la usa, '
               'qué rutas define o llama, qué variables lee, qué pruebas la cubren y en qué sesiones se mencionó.\n')
    out.append('## 5. El mapa interactivo (sin Obsidian)\n')
    out.append('Dentro de `vault/_grafo/` está **`mapa.html`**: ábrelo con doble clic y se abre en el navegador '
               '(necesita internet cada vez que lo abres, para cargar la librería de dibujo; sin conexión muestra '
               'un aviso). Tiene buscador, filtros por '
               'capa y al tocar un punto muestra sus conexiones. Funciona también en el teléfono.\n')
    out.append('## 6. Cómo se actualiza\n')
    out.append('**Lo actualiza Claude en cada cambio**: antes de guardar cambios en el código corre '
               '`python scripts/build_vault.py`, y una prueba automática avisa si la bóveda quedó vieja. '
               'Tú no tienes que hacer nada más que **Pull** en GitHub Desktop para ver la versión nueva.\n')
    out.append('- No edites las notas generadas: se reescriben solas.\n'
               '- **Tus notas personales** van en la carpeta **`Mis notas`** (el generador nunca la toca).\n')
    out.append('## Glosario rápido\n')
    out.append('- **Módulo**: un archivo de código (por ejemplo `core/ai.py`).\n'
               '- **Ruta / endpoint**: una dirección del servidor que la pantalla llama (por ejemplo '
               '`/api/khipu/chat`).\n'
               '- **Variable de entorno**: un ajuste secreto o de configuración que vive en Railway (aquí solo '
               'aparece el nombre).\n'
               '- **Prueba**: un chequeo automático que confirma que algo sigue funcionando.\n'
               '- **Capa**: un grupo de archivos que hacen un mismo tipo de trabajo (interfaz, dinero, voz…).\n')
    out.append('## Qué hacer ahora\n')
    out.append('1. Instala Obsidian y abre la carpeta `vault` como bóveda.\n'
               f"2. Abre {link('00 Mapa de Khipus')} y luego el grafo con **Ctrl + G**.\n"
               f"3. Mira {link('01 Reporte del grafo')}: ahí están las cosas sueltas que conviene revisar.\n")
    return '\n'.join(out)


def note_report(M, R):
    out = [fm({'tipo': 'reporte', 'tags': ['tipo/reporte']})]
    out.append('# 01 Reporte del grafo\n')
    out.append('Lo calcula `scripts/build_vault.py` leyendo el código (sin IA). Sirve para encontrar **cosas sueltas**: '
               'código sin pruebas, módulos o rutas que nadie usa, variables sin documentar.\n')
    out.append('> [!info] Cómo se decide "nadie lo usa" (heurística, revisar antes de borrar nada)\n'
               '> - **Python**: cuenta como uso cualquier `import`/`from … import` (también dentro de funciones) y el '
               'nombre del módulo con puntos escrito como texto (`importlib.import_module("core.world")`, la lista '
               'de blueprints de server.py). Una palabra suelta (`"server"`, `"research"`) solo cuenta dentro de '
               '`import_module(…)`, `__import__(…)` o `sys.modules.get(…)`: si no, es una categoría o una clave, no '
               'una importación. Son puertas de entrada (no se reportan): `server.py`, los scripts de '
               '`scripts/`, todo módulo con `if __name__ == "__main__"`, los `__init__.py` y `tests/conftest.py`.\n'
               '> - **JavaScript**: una global es `window.X = …` (o `Object.defineProperty(window, "X")`). Para las '
               'conexiones del grafo cuenta como uso que otro archivo escriba `X` en su código (no como clave de un '
               'objeto `{ X: … }`) o `window.X`, o la use dentro de un texto/HTML como `X(…)`, `X.algo` o `window.X` '
               '(los `onclick="…"`); la palabra suelta en un texto no cuenta. Para la lista de "nadie la usa" se es más '
               'generoso (cualquier mención, también del Python del servidor), así que lo que aparece ahí casi seguro '
               'sobra. No detecta accesos dinámicos (`window[nombre]`).\n'
               '> - **Rutas**: cuenta como llamada cualquier texto que empiece por `/api`, `/v1`, `/mcp`… en JS, '
               'Python del servidor, scripts o pruebas; un texto que termina en `/` se trata como prefijo de las rutas '
               'que siguen. Una base como `var API = "/api/brokerage"` se une a las rutas relativas que el mismo '
               'archivo arma (`"/clients/" + id + "/audit"` → `/api/brokerage/clients/<id>/audit`); solo si el '
               'archivo no arma ninguna vale como prefijo de todas. Las rutas externas (`/v1/*` monetizada, `/mcp`, '
               'OAuth y su `…/oauth/callback`, `/api/health` de Railway, archivos estáticos) no se reportan.\n'
               '> - **Pruebas**: un módulo está cubierto si una prueba lo importa o escribe su ruta (`engine/x.js`) '
               'o su nombre de archivo entre comillas.\n')
    out.append('## Conteos\n')
    out.append('| Qué | Cuántos |\n|---|---|')
    for k, v in R['counts']:
        out.append(f'| {k} | {v} |')
    out.append('')
    out.append('## Nodos "dios" (más conectados)\n')
    out.append('Conexiones de código entre archivos (importa, usa globales, carga, nombra, llama a su ruta). '
               'Mucho acoplamiento = cambiar ahí afecta a muchos.\n')
    out.append('| Archivo | Total | Entran | Salen | Capa |\n|---|---|---|---|---|')
    for p, tot, i, o in R['god']:
        out.append(f"| {_flink(M, p)} | {tot} | {i} | {o} | {capa_link(M.files[p]['layer'])} |")
    out.append('')
    out.append(f"## Módulos sin pruebas ({len(R['untested'])})\n")
    out.append('Código (no datos) que ninguna prueba importa ni nombra. Ordenado por tamaño.\n')
    if R['untested']:
        out.append('| Módulo | Líneas | Capa |\n|---|---|---|')
        for p in R['untested']:
            out.append(f"| {_flink(M, p)} | {miles(M.files[p]['lines'])} | {capa_link(M.files[p]['layer'])} |")
        out.append('')
    out.append(f"## Módulos Python que nadie importa ({len(R['py_orphans'])})\n")
    out.append('\n'.join(f'- {_flink(M, p)}' for p in R['py_orphans']) + '\n' if R['py_orphans'] else '_Ninguno._\n')
    if R['py_test_only']:
        out.append(f"**Solo los importan las pruebas** ({len(R['py_test_only'])}): " +
                   ', '.join(_flink(M, p) for p in R['py_test_only']) + '\n')
    out.append(f"## Globales window.* que ningún otro archivo usa ({len(R['js_orphans'])})\n")
    out.append('Se exportan a `window` pero nadie más las lee. Si "se usa dentro de su archivo" dice sí, la función '
               'sí trabaja (solo sobra la exportación); si dice no, es candidata a código muerto.\n')
    if R['js_orphans']:
        out.append('| Global | Definida en | ¿Se usa dentro de su archivo? | ¿La nombra alguna prueba? |\n'
                   '|---|---|---|---|')
        for nm, defs, in_tests, internal in R['js_orphans']:
            out.append(f"| {tcode('window.' + nm)} | {', '.join(_flink(M, d) for d in defs)} | "
                       f"{'sí' if internal else '**no**'} | {'sí (solo pruebas)' if in_tests else 'no'} |")
        out.append('')
    else:
        out.append('_Ninguna._\n')
    out.append(f"## Rutas definidas que nadie llama ({len(R['dead_routes'])})\n")
    out.append('Posible código muerto: ni la pantalla, ni el servidor, ni las pruebas, ni los scripts nombran la ruta.\n')
    if R['dead_routes']:
        out.append('| Método | Ruta | Función | Módulo |\n|---|---|---|---|')
        for r in R['dead_routes']:
            out.append(f"| {_route_line(M, r)} | {_flink(M, r['file'])} |")
        out.append('')
    if R['test_only_routes']:
        out.append(f"**Solo las llaman las pruebas** ({len(R['test_only_routes'])}): " +
                   ', '.join(code(','.join(r['methods']) + ' ' + r['path']) for r in R['test_only_routes']) + '\n')
    out.append(f"## Llamadas a rutas que no existen ({len(R['broken_calls'])})\n")
    out.append('Textos con forma de ruta (`/api/…`) en el código que no coinciden con ninguna ruta del servidor. '
               'Pueden ser restos de funciones retiradas o rutas armadas por partes.\n')
    if R['broken_calls']:
        out.append('| Archivo | Ruta nombrada |\n|---|---|')
        for p, ref in R['broken_calls']:
            out.append(f'| {_flink(M, p)} | {tcode(ref)} |')
        out.append('')
    out.append(f"## Variables leídas en el código que faltan en CLAUDE.md ({len(R['env_undoc'])})\n")
    out.append('Se pueden configurar en Railway pero nadie las anotó en la lista de CLAUDE.md.\n')
    out.append(', '.join(link(env_note(n)) for n in R['env_undoc']) + '\n' if R['env_undoc'] else '_Ninguna._\n')
    if R['env_deploy_only']:
        out.append(f"Solo aparecen en archivos de despliegue (Dockerfile, docker-compose.yml, workflows) y no en "
                   f"CLAUDE.md ({len(R['env_deploy_only'])}): " +
                   ', '.join(link(env_note(n)) for n in R['env_deploy_only']) + '\n')
    if R['env_list_only']:
        out.append(f"Solo aparecen en listas de nombres (p. ej. la lista de secretos que se tapan en los logs) "
                   f"({len(R['env_list_only'])}): " + ', '.join(link(env_note(n)) for n in R['env_list_only']) + '\n')
    out.append(f"## Variables de la lista de CLAUDE.md que nadie lee ({len(R['env_unread'])})\n")
    out.append(', '.join(code(n) for n in R['env_unread']) + '\n' if R['env_unread'] else '_Ninguna._\n')
    out.append(f"## Scripts que app.html carga pero sw.js no guarda en caché ({len(R['not_in_shell'])})\n")
    out.append('Regla de CLAUDE.md: todo archivo JS nuevo va también al array SHELL de `sw.js`.\n')
    out.append(', '.join(_flink(M, p) for p in R['not_in_shell']) + '\n' if R['not_in_shell'] else '_Ninguno._\n')
    out.append(f"## Archivos en la capa \"Otros\" ({len(R['otros'])})\n")
    out.append('Faltan en la tabla de capas (`REGLAS_CAPA` en `scripts/build_vault.py`).\n')
    out.append(', '.join(_flink(M, p) for p in R['otros']) + '\n' if R['otros'] else '_Ninguno: todo tiene capa._\n')
    return '\n'.join(out)


def report_data(M):
    files = M.files
    R = {}
    code_files = [p for p, f in files.items() if f['role'] in ('code', 'page')]
    counts = [
        ('Archivos de código (Python, JS, HTML)', miles(len(code_files))),
        ('Líneas de código', miles(sum(files[p]['lines'] for p in code_files))),
        ('Archivos de datos del catálogo', miles(sum(1 for f in files.values() if f['role'] == 'data'))),
        ('Archivos de prueba', miles(sum(1 for f in files.values() if f['role'] == 'test'))),
        ('Documentos', miles(sum(1 for f in files.values() if f['role'] == 'doc'))),
        ('Rutas HTTP', miles(len(M.routes))),
        ('Grupos de API', miles(len(M.groups))),
        ('Herramientas MCP', miles(len(M.tools))),
        ('Variables de entorno', miles(len(M.env_names))),
        ('Sesiones de trabajo', miles(len(M.sessions))),
    ]
    by_type = defaultdict(int)
    for e in M.edges:
        by_type[e[2]] += 1
    for t in sorted(by_type):
        counts.append((f'Aristas `{t}`', miles(by_type[t])))
    R['counts'] = counts
    tot = {p: M.deg_in.get(p, 0) + M.deg_out.get(p, 0) for p in files}
    god = sorted((p for p in tot if tot[p] > 0), key=lambda p: (-tot[p], p))[:20]
    R['god'] = [(p, tot[p], M.deg_in.get(p, 0), M.deg_out.get(p, 0)) for p in god]
    R['untested'] = sorted((p for p in code_files if not M.tested.get(p) and
                            not (p.endswith('__init__.py') and files[p]['lines'] < 40)),
                           key=lambda p: (-files[p]['lines'], p))
    orph, test_only = [], []
    for p, f in sorted(files.items()):
        if f['ext'] != 'py' or f['role'] != 'code':
            continue
        if p in PY_ENTRY or p.startswith('scripts/') or p.endswith('__init__.py') or f['py']['has_main']:
            continue
        users = M.imported_by.get(p, set())
        app_users = {u for u in users if files[u]['role'] != 'test'}
        if not users:
            orph.append(p)
        elif not app_users:
            test_only.append(p)
    R['py_orphans'], R['py_test_only'] = orph, test_only
    js_orph = []
    for nm in sorted(M.explicit):
        defs = sorted(M.explicit[nm])
        all_defs = M.definers.get(nm, set())
        used = False
        for path, f in files.items():
            if 'js' not in f:
                continue
            js = f['js']
            if path in all_defs:
                if nm in js['win_reads']:   # lectura window.X que no es la asignación
                    used = True
                    break
                if nm in js['str_ids']:
                    used = True
                    break
                continue
            if nm in js['win'] or (nm in js['bare'] and nm not in js['local']):
                used = True
                break
        if used:
            continue
        in_server = any(nm in ids for p2, ids in M.py_text_ids.items() if files[p2]['role'] != 'test')
        if in_server:
            continue
        in_tests = any(nm in ids for p2, ids in M.py_text_ids.items() if files[p2]['role'] == 'test') or \
            any(nm in files[p2]['text'] for p2 in files if files[p2]['role'] == 'test' and files[p2]['ext'] == 'js')
        internal = False
        for d in defs:
            c = files[d]['js']['code']
            e = re.escape(nm)
            bare_n = len(re.findall(r'(?<![\w$.])' + e + r'(?![\w$])', c))
            decl = len(re.findall(r'\b(?:function|var|let|const|class)\s+' + e + r'(?![\w$])', c))
            export = len(re.findall(r'\bwindow\.' + e + r'\s*=\s*' + e + r'(?![\w$])', c))
            if bare_n - decl - export > 0:
                internal = True
        js_orph.append((nm, defs, in_tests, internal))
    R['js_orphans'] = js_orph
    dead, test_only_r = [], []
    for r in M.routes:
        if route_is_external(r['path']):
            continue
        cs = M.route_callers.get(r['id'], set())
        if not cs:
            dead.append(r)
        elif all(files[c]['role'] == 'test' for c in cs):
            test_only_r.append(r)
    R['dead_routes'], R['test_only_routes'] = dead, test_only_r
    R['broken_calls'] = sorted((p, ref) for p, refs in M.unmatched_calls.items() for ref in refs)
    undoc, list_only, deploy_only = [], [], []
    for nm in sorted(M.env_readers):
        kinds = set().union(*M.env_readers[nm].values())
        if env_documented(M, nm):
            continue
        if kinds == {'lista'}:
            list_only.append(nm)
        else:
            undoc.append(nm)
    for nm in sorted(M.infra_env):
        if nm not in M.env_readers and not env_documented(M, nm) and nm != 'PORT':
            deploy_only.append(nm)
    R['env_undoc'] = sorted(undoc)
    R['env_list_only'] = list_only
    R['env_deploy_only'] = deploy_only
    R['env_unread'] = sorted(nm for nm in M.claude_block if not env_is_read(M, nm))
    shell = set()
    if 'sw.js' in files:
        for s in JSScan(files['sw.js']['text']).strings:
            shell.add(s.split('?')[0].lstrip('./').lstrip('/'))
    R['shell'] = shell
    R['not_in_shell'] = sorted(s['src'] for s in M.app_scripts
                               if s['kind'] == 'src' and s['src'] in files and s['src'] not in shell)
    R['otros'] = sorted(p for p, f in files.items() if f['layer'] == 'otros')
    return R


def note_sw(M, R):
    p = 'sw.js'
    base = note_module(M, p)
    f = M.files[p]
    m = re.search(r'''const\s+CACHE\s*=\s*['"]([^'"]+)['"]''', f['text'])
    extra = ['\n## Caché del service worker\n']
    if m:
        extra.append(f"Versión de caché actual: {code(m.group(1))} — se sube en CADA cambio de JS/HTML "
                     "(regla de despliegue n.º 1 de CLAUDE.md).\n")
    shell = sorted(x for x in R['shell'] if x.endswith(('.js', '.html', '.css', '.json', '.svg')))
    extra.append(f"El array SHELL guarda **{len(shell)}** archivos para usarlos sin conexión "
                 f"(lista en texto para no saturar el grafo):\n")
    extra.append('`' + '`, `'.join(shell) + '`\n' if shell else '')
    return base + '\n'.join(extra)


# ════════════════════════════════════════════════════════════════════════════
# 11. GRAFO (graph.json + mapa.html) y configuración de Obsidian
# ════════════════════════════════════════════════════════════════════════════
def note_path(M, p):
    f = M.files[p]
    return f['folder'] + '/' + f['note']


def graph_data(M):
    nodes = []
    for p in sorted(M.files):
        f = M.files[p]
        t = {'code': 'module', 'page': 'page', 'data': 'data', 'test': 'test', 'doc': 'doc'}[f['role']]
        nodes.append({'id': p, 'label': p, 'layer': f['layer'], 'type': t, 'lines': f['lines'], 'path': p,
                      'note': note_path(M, p)})
    for r in M.routes:
        nodes.append({'id': r['id'], 'label': ','.join(r['methods']) + ' ' + r['path'],
                      'layer': r['layer'], 'type': 'endpoint', 'lines': None, 'path': r['file'],
                      'note': 'API/' + r['group']})
    for t in M.tools:
        nodes.append({'id': t['id'], 'label': 'MCP ' + t['name'], 'layer': 'mcp', 'type': 'endpoint',
                      'lines': None, 'path': 'mcp_server/tools.py', 'note': 'API/API herramientas MCP'})
    for nm in M.env_names:
        nodes.append({'id': 'env:' + nm, 'label': nm, 'layer': 'infra', 'type': 'env', 'lines': None, 'path': None,
                      'note': 'Entorno/' + env_note(nm)})
    for s in M.sessions:
        nodes.append({'id': s['id'], 'label': s['note'], 'layer': 'docs', 'type': 'session', 'lines': s['lines'],
                      'path': f"docs/ESTADO.md#L{s['line']}", 'note': 'Sesiones/' + s['note']})
    ids = {n['id'] for n in nodes}
    edges = [{'source': a, 'target': b, 'type': t, 'detail': d} for (a, b, t, d) in M.edges if a in ids and b in ids]
    layers = [{'key': c[0], 'name': c[1], 'tag': c[2], 'obsidian_color': c[3], 'slot': c[4][0], 'style': c[4][1],
               'note': 'Capas/' + capa_note_name(c[0])} for c in CAPAS]
    return {'_doc': 'Grafo de conocimiento del repo Khipus. Generado por scripts/build_vault.py (determinista, sin '
                    'IA, sin red). Nodos: archivos, rutas HTTP/herramientas MCP (type endpoint), variables de '
                    'entorno (solo nombres) y sesiones de docs/ESTADO.md.',
            'edge_types': EDGE_DOC, 'layers': layers, 'nodes': nodes, 'edges': edges}


def graph_json_text(G):
    out = ['{']
    out.append(' "_doc": ' + json.dumps(G['_doc'], ensure_ascii=False) + ',')
    out.append(' "edge_types": ' + json.dumps(G['edge_types'], ensure_ascii=False, sort_keys=True) + ',')
    for key in ('layers', 'nodes', 'edges'):
        out.append(f' "{key}": [')
        items = G[key]
        for i, it in enumerate(items):
            out.append('  ' + json.dumps(it, ensure_ascii=False, sort_keys=True) + (',' if i < len(items) - 1 else ''))
        out.append(' ]' + (',' if key != 'edges' else ''))
    out.append('}')
    return '\n'.join(out) + '\n'


def map_html(M, G):
    # datos compactos: nodos como listas, aristas por índice
    idx = {n['id']: i for i, n in enumerate(G['nodes'])}
    types = ['module', 'page', 'data', 'test', 'doc', 'endpoint', 'env', 'session']
    etypes = sorted(EDGE_DOC) + ['via_endpoint']
    lkeys = [c[0] for c in CAPAS]
    nodes = [[n['label'], lkeys.index(n['layer']), types.index(n['type']), n['lines'] or 0, n['path'] or '',
              n['note']] for n in G['nodes']]
    edges = [[idx[e['source']], idx[e['target']], etypes.index(e['type'])] for e in G['edges']]
    # aristas virtuales: quien llama a una ruta → el módulo que la define (cuando se esconden las rutas)
    route_file = {r['id']: r['file'] for r in M.routes}
    virt = set()
    for e in G['edges']:
        if e['type'] == 'calls_endpoint' and e['target'] in route_file and route_file[e['target']] != e['source']:
            virt.add((idx[e['source']], idx[route_file[e['target']]]))
    for a, b in sorted(virt):
        edges.append([a, b, etypes.index('via_endpoint')])
    data = {'layers': [{'key': c[0], 'name': c[1], 'slot': c[4][0], 'style': c[4][1]} for c in CAPAS],
            'types': types, 'etypes': etypes, 'nodes': nodes, 'edges': edges}
    blob = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    return MAP_TEMPLATE.replace('__DATA__', blob).replace('__COUNTS__',
                                                         f"{miles(len(nodes))} nodos · {miles(len(G['edges']))} conexiones")


def obsidian_files():
    app = {
        'alwaysUpdateLinks': True,
        'attachmentFolderPath': 'Mis notas/adjuntos',
        'newFileFolderPath': 'Mis notas',
        'newFileLocation': 'folder',
        'newLinkFormat': 'shortest',
        'promptDelete': True,
        'readableLineLength': True,
        'showLineNumber': False,
        'useMarkdownLinks': False,
        'userIgnoreFilters': ['_grafo/'],
    }
    groups = [{'query': 'tag:#tipo/sesion', 'color': {'a': 1, 'rgb': int('b7a6e8', 16)}},
              {'query': 'tag:#tipo/variable', 'color': {'a': 1, 'rgb': int('d9b35c', 16)}}]
    for c in CAPAS:
        groups.append({'query': 'tag:#' + c[2], 'color': {'a': 1, 'rgb': int(c[3][1:], 16)}})
    graph = {
        'collapse-filter': False, 'search': '', 'showTags': False, 'showAttachments': False,
        'hideUnresolved': True, 'showOrphans': True, 'collapse-color-groups': False, 'colorGroups': groups,
        'collapse-display': True, 'showArrow': True, 'textFadeMultiplier': 0, 'nodeSizeMultiplier': 1.1,
        'lineSizeMultiplier': 1, 'collapse-forces': True, 'centerStrength': 0.45, 'repelStrength': 12,
        'linkStrength': 1, 'linkDistance': 180, 'scale': 0.6, 'close': False,
    }
    return {'.obsidian/app.json': _dump_cfg(app), '.obsidian/graph.json': _dump_cfg(graph)}


def _dump_cfg(d):
    return json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True) + '\n'


def _managed_group(g):
    q = str(g.get('query', '')) if isinstance(g, dict) else ''
    return q.startswith('tag:#capa/') or q in ('tag:#tipo/sesion', 'tag:#tipo/variable')


def merge_obsidian_config(rel, old_text, new_text):
    """Configuración de Obsidian que YA existe → lo que hay que escribir (None = no tocar).

    La persona mueve controles del grafo y Obsidian reescribe estos archivos: eso se respeta. app.json no se
    toca nunca; en graph.json solo se refrescan los grupos de color de las capas (los suyos propios — otra
    búsqueda — se conservan ANTES de los de capa, así ganan) y se agregan las claves que falten."""
    if rel != '.obsidian/graph.json':
        return None
    try:
        old = json.loads(old_text)
    except ValueError:
        return new_text
    if not isinstance(old, dict):
        return new_text
    new = json.loads(new_text)
    merged = dict(old)
    for k, v in new.items():
        merged.setdefault(k, v)
    mine = [g for g in old.get('colorGroups') or [] if isinstance(g, dict) and not _managed_group(g)]
    merged['colorGroups'] = mine + new['colorGroups']
    return None if merged == old else _dump_cfg(merged)


# ════════════════════════════════════════════════════════════════════════════
# 12. ARMADO DE LA BÓVEDA
# ════════════════════════════════════════════════════════════════════════════
OWNED_DIRS = ('Capas', 'Módulos', 'API', 'Entorno', 'Sesiones', 'Pruebas', 'Documentos', '_grafo')
TOP_NOTES = ('00 Mapa de Khipus.md', '01 Reporte del grafo.md', '02 Cómo usar esta bóveda.md')
SEED_FILES = {  # se crean solo si faltan; nunca se comparan ni se pisan
    'Mis notas/Léeme.md': '# Mis notas\n\nEsta carpeta es tuya: el generador de la bóveda nunca la toca. '
                          'Escribe aquí ideas, pendientes o preguntas para Claude.\n',
}


def build_vault():
    """→ dict {ruta relativa dentro de vault/: texto}"""
    M = build_model()
    derive(M)
    R = report_data(M)
    out = {}

    def put(rel, text):
        if rel in out:
            raise RuntimeError('nota duplicada: ' + rel)
        out[rel] = text if text.endswith('\n') else text + '\n'

    for p in sorted(M.files):
        f = M.files[p]
        body = note_sw(M, R) if p == 'sw.js' else note_module(M, p)
        put(f"{f['folder']}/{f['note']}.md", body)
    for g in M.groups:
        put(f'API/{g}.md', note_api_group(M, g))
    put('API/API herramientas MCP.md', note_mcp_tools(M))
    put('API/Índice de la API.md', note_api_index(M))
    for nm in M.env_names:
        put(f'Entorno/{env_note(nm)}.md', note_env(M, nm))
    put('Entorno/Índice de variables de entorno.md', note_env_index(M))
    for i, s in enumerate(M.sessions):
        prev = M.sessions[i - 1] if i > 0 else None
        nxt = M.sessions[i + 1] if i + 1 < len(M.sessions) else None
        put(f"Sesiones/{s['note']}.md", note_session(M, s, prev, nxt))
    put('Sesiones/Índice de sesiones.md', note_session_index(M))
    put('Pruebas/Índice de pruebas.md', note_test_index(M))
    for c in CAPAS:
        put(f'Capas/{capa_note_name(c[0])}.md', note_layer(M, c[0]))
    put('00 Mapa de Khipus.md', note_home(M))
    put('01 Reporte del grafo.md', note_report(M, R))
    put('02 Cómo usar esta bóveda.md', note_howto(M))
    G = graph_data(M)
    put('_grafo/graph.json', graph_json_text(G))
    put('_grafo/mapa.html', map_html(M, G))
    for rel, text in obsidian_files().items():
        put(rel, text)
    # nombres de nota únicos (los [[enlaces]] se resuelven por nombre)
    seen = {}
    for rel in out:
        if rel.endswith('.md'):
            nm = os.path.basename(rel)[:-3].lower()
            if nm in seen:
                raise RuntimeError(f'nombre de nota repetido: {rel} y {seen[nm]}')
            seen[nm] = rel
    return out, M, R


def _owned(rel):
    return rel in TOP_NOTES or rel.split('/', 1)[0] in OWNED_DIRS or rel in ('.obsidian/app.json',
                                                                             '.obsidian/graph.json')


def existing_owned(vault_dir):
    found = set()
    for d in OWNED_DIRS:
        base = os.path.join(vault_dir, d)
        for dp, _dn, fns in os.walk(base):
            for fn in fns:
                found.add(os.path.relpath(os.path.join(dp, fn), vault_dir).replace(os.sep, '/'))
    for t in TOP_NOTES + ('.obsidian/app.json', '.obsidian/graph.json'):
        if os.path.isfile(os.path.join(vault_dir, t)):
            found.add(t)
    return found


OBSIDIAN_CONFIG = ('.obsidian/app.json', '.obsidian/graph.json')


def diff_vault(out, vault_dir):
    """Diferencias entre lo generado y vault/. La configuración de Obsidian solo tiene que EXISTIR:
    Obsidian la reescribe cuando la persona mueve un control del grafo, y eso no es "bóveda vieja"."""
    problems = []
    have = existing_owned(vault_dir)
    for rel in sorted(out):
        fp = os.path.join(vault_dir, rel)
        if not os.path.isfile(fp):
            problems.append('falta: ' + rel)
            continue
        if rel in OBSIDIAN_CONFIG:
            continue
        with open(fp, encoding='utf-8') as fh:   # saltos universales: un checkout CRLF (Windows) no cuenta
            if fh.read() != out[rel]:
                problems.append('distinto: ' + rel)
    for rel in sorted(have - set(out)):
        problems.append('sobra: ' + rel)
    return problems


def write_vault(out, vault_dir):
    have = existing_owned(vault_dir)
    for rel in sorted(have - set(out)):
        os.remove(os.path.join(vault_dir, rel))
    for rel, text in sorted(out.items()):
        fp = os.path.join(vault_dir, rel)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        old = None
        if os.path.isfile(fp):
            with open(fp, encoding='utf-8') as fh:
                old = fh.read()
        if rel in OBSIDIAN_CONFIG and old is not None:
            # ya existe: es de la persona (Obsidian la reescribe al mover controles); solo se fusiona
            text = merge_obsidian_config(rel, old, text)
            if text is None:
                continue
        if old != text:
            with open(fp, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(text)
    for rel, text in SEED_FILES.items():
        fp = os.path.join(vault_dir, rel)
        if not os.path.exists(fp):
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            with open(fp, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(text)
    # carpetas vacías que quedaron
    for d in OWNED_DIRS:
        base = os.path.join(vault_dir, d)
        for dp, dn, fns in sorted(os.walk(base, topdown=False), reverse=False):
            if dp != base and not os.listdir(dp):
                os.rmdir(dp)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Genera la bóveda de Obsidian + grafo del repo (vault/).')
    ap.add_argument('--check', action='store_true', help='no escribe; sale 1 si vault/ está desactualizada')
    ap.add_argument('--vault', default=os.path.join(ROOT, VAULT), help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    out, M, R = build_vault()
    if a.check:
        problems = diff_vault(out, a.vault)
        if problems:
            print(f'La bóveda está DESACTUALIZADA ({len(problems)} diferencias). '
                  'Corre: python scripts/build_vault.py')
            for p in problems[:60]:
                print('  ' + p)
            if len(problems) > 60:
                print(f'  … y {len(problems) - 60} más')
            return 1
        print(f'Bóveda al día: {len(out)} archivos.')
        return 0
    write_vault(out, a.vault)
    print(f"Bóveda escrita en {os.path.relpath(a.vault, ROOT)}/: {len(out)} archivos "
          f"({sum(1 for r in out if r.endswith('.md'))} notas). Rutas: {len(M.routes)} · MCP: {len(M.tools)} · "
          f"variables: {len(M.env_names)} · sesiones: {len(M.sessions)}.")
    if R['otros']:
        print('Archivos sin capa (van a "Otros"): ' + ', '.join(R['otros']))
    return 0


# ════════════════════════════════════════════════════════════════════════════
# 13. PLANTILLA DEL MAPA INTERACTIVO (autocontenido; d3 solo desde cdnjs)
# ════════════════════════════════════════════════════════════════════════════
MAP_TEMPLATE = r'''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mapa de Khipus</title>
<meta name="description" content="Mapa interactivo del código de Khipus: archivos, rutas, variables y sesiones, coloreado por capa.">
<style>
:root{
  color-scheme: light;
  --bg:#f6f5f2; --surface:#fcfcfb; --surface-2:#ffffff; --ink:#0b0b0b; --ink-2:#52514e; --muted:#7a7974;
  --line:#e2e1dc; --edge:rgba(40,40,36,.13); --edge-hi:rgba(40,40,36,.55); --ring:#0b0b0b; --focus:#2a78d6;
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100; --s5:#e87ba4; --s6:#008300; --s7:#6250d6; --s8:#e34948;
  --n1:#52514e; --n2:#a8a7a1; --chip:#efeeea; --chip-on:#ffffff; --shadow:0 6px 24px rgba(0,0,0,.10);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme: dark;
    --bg:#121211; --surface:#1a1a19; --surface-2:#222220; --ink:#f0efec; --ink-2:#c3c2b7; --muted:#8f8e86;
    --line:#2f2f2c; --edge:rgba(240,239,236,.10); --edge-hi:rgba(240,239,236,.55); --ring:#f0efec; --focus:#3987e5;
    --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181; --s6:#008300; --s7:#9085e9; --s8:#e66767;
    --n1:#c3c2b7; --n2:#6f6e69; --chip:#262624; --chip-on:#33332f; --shadow:0 6px 24px rgba(0,0,0,.45);
  }
}
:root[data-theme="dark"]{
  color-scheme: dark;
  --bg:#121211; --surface:#1a1a19; --surface-2:#222220; --ink:#f0efec; --ink-2:#c3c2b7; --muted:#8f8e86;
  --line:#2f2f2c; --edge:rgba(240,239,236,.10); --edge-hi:rgba(240,239,236,.55); --ring:#f0efec; --focus:#3987e5;
  --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181; --s6:#008300; --s7:#9085e9; --s8:#e66767;
  --n1:#c3c2b7; --n2:#6f6e69; --chip:#262624; --chip-on:#33332f; --shadow:0 6px 24px rgba(0,0,0,.45);
}
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);
  font:14px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;overflow:hidden}
body{display:flex;flex-direction:column;min-width:0}
header{display:flex;flex-wrap:wrap;align-items:center;gap:8px 14px;padding:10px 16px;background:var(--surface);
  border-bottom:1px solid var(--line)}
h1{font-size:16px;margin:0;font-weight:650;letter-spacing:.01em}
.sub{color:var(--muted);font-size:12px}
.search{position:relative;flex:1 1 220px;min-width:0;max-width:440px;margin-left:auto}
#q{width:100%;height:34px;border-radius:9px;border:1px solid var(--line);background:var(--surface-2);color:var(--ink);
  padding:0 12px;font:inherit}
#q:focus-visible,button:focus-visible,summary:focus-visible,a:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
#results{position:absolute;left:0;right:0;top:38px;background:var(--surface-2);border:1px solid var(--line);
  border-radius:10px;box-shadow:var(--shadow);z-index:20;max-height:320px;overflow:auto;display:none}
#results button{display:flex;gap:8px;align-items:center;width:100%;text-align:left;border:0;background:none;
  color:var(--ink);padding:8px 10px;font:inherit;cursor:pointer;min-width:0}
#results button:hover,#results button.on{background:var(--chip)}
#results .lbl{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
#results .t{margin-left:auto;color:var(--muted);font-size:11px;flex:none}
.filters{background:var(--surface);border-bottom:1px solid var(--line);padding:6px 16px 8px}
.filters details>summary{cursor:pointer;color:var(--ink-2);font-size:12px;padding:4px 0;list-style:none}
.filters details>summary::-webkit-details-marker{display:none}
.filters details>summary::before{content:"▸ ";color:var(--muted)}
.filters details[open]>summary::before{content:"▾ "}
.row{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:4px 0}
.row .lab{color:var(--muted);font-size:12px;margin-right:2px}
.chip{display:inline-flex;align-items:center;gap:6px;height:28px;padding:0 10px;border-radius:999px;
  border:1px solid var(--line);background:var(--chip);color:var(--ink-2);font:inherit;font-size:12px;cursor:pointer;
  max-width:100%}
.chip[aria-pressed="true"]{background:var(--chip-on);color:var(--ink);border-color:var(--ink-2)}
.chip[aria-pressed="false"]{opacity:.55}
.chip .n{color:var(--muted);font-variant-numeric:tabular-nums}
.chip span.nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sw{width:12px;height:12px;border-radius:50%;flex:none}
.sw.ring{background:transparent!important;border:3px solid}
.link{background:none;border:0;color:var(--focus);font:inherit;font-size:12px;cursor:pointer;padding:4px}
main{position:relative;flex:1;min-height:0}
canvas{display:block;width:100%;height:100%;touch-action:none;cursor:grab}
#tip{position:absolute;pointer-events:none;background:var(--surface-2);color:var(--ink);border:1px solid var(--line);
  border-radius:8px;padding:4px 8px;font-size:12px;box-shadow:var(--shadow);display:none;max-width:60vw;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#panel{position:absolute;top:12px;right:12px;bottom:12px;width:360px;max-width:calc(100% - 24px);background:var(--surface);
  border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);display:none;flex-direction:column;overflow:hidden}
#panel.open{display:flex}
#panel .hd{display:flex;gap:8px;align-items:flex-start;padding:12px 12px 8px 14px;border-bottom:1px solid var(--line)}
#panel h2{font-size:14px;margin:0;word-break:break-all;flex:1;min-width:0}
#panel .x{border:0;background:var(--chip);color:var(--ink);width:28px;height:28px;border-radius:8px;cursor:pointer;flex:none;font:inherit}
#panel .bd{overflow:auto;padding:10px 14px 14px}
.meta{display:grid;grid-template-columns:auto 1fr;gap:4px 10px;font-size:12px;margin-bottom:10px}
.meta dt{color:var(--muted)} .meta dd{margin:0;word-break:break-all;min-width:0}
code{font:12px/1.4 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;background:var(--chip);padding:1px 5px;border-radius:5px}
.grp{margin:10px 0 4px;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.lst{list-style:none;margin:0;padding:0}
.lst li button{display:flex;gap:8px;align-items:center;width:100%;border:0;background:none;color:var(--ink);text-align:left;
  padding:5px 4px;border-radius:6px;font:inherit;font-size:12.5px;cursor:pointer;min-width:0}
.lst li button:hover{background:var(--chip)}
.lst li .lbl{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.hint{position:absolute;left:12px;bottom:12px;color:var(--muted);font-size:12px;background:var(--surface);
  border:1px solid var(--line);border-radius:8px;padding:4px 8px;max-width:calc(100% - 24px)}
.legend-note{color:var(--muted);font-size:11px;margin-top:2px}
.vh{position:absolute!important;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
@media (max-width:720px){
  header{padding:8px 16px}
  .search{flex-basis:100%;max-width:none;margin-left:0}
  #panel{top:auto;left:8px;right:8px;bottom:8px;width:auto;max-width:none;max-height:58%}
  .hint{display:none}
  .filters{padding:4px 16px 6px}
}
</style>
</head>
<body>
<header>
  <h1>Mapa de Khipus</h1>
  <span class="sub" id="counts">__COUNTS__</span>
  <div class="search">
    <label class="vh" for="q">Buscar en el mapa</label>
    <input id="q" type="search" placeholder="Buscar archivo, ruta o variable…" autocomplete="off" role="combobox"
      aria-expanded="false" aria-controls="results">
    <div id="results" role="listbox"></div>
  </div>
</header>
<section class="filters" aria-label="Filtros">
  <div class="row" id="types"><span class="lab">Mostrar:</span></div>
  <details id="layersBox">
    <summary>Capas <span id="layerCount"></span></summary>
    <div class="row" id="layers"></div>
    <div class="row"><button class="link" id="allL" type="button">Todas</button><button class="link" id="noneL" type="button">Ninguna</button>
    <span class="legend-note">Relleno = capa principal · aro = capa con el mismo tono · gris = base, pruebas y documentos</span></div>
  </details>
</section>
<main>
  <canvas id="cv" aria-label="Grafo del código de Khipus" role="img"></canvas>
  <div id="tip"></div>
  <div class="hint">Toca un punto para ver sus conexiones · rueda o pellizco para acercar · arrastra para moverte · doble clic para encuadrar</div>
  <aside id="panel" aria-live="polite">
    <div class="hd"><h2 id="pTitle"></h2><button class="x" id="pClose" type="button" aria-label="Cerrar">✕</button></div>
    <div class="bd" id="pBody"></div>
  </aside>
</main>
<script id="data" type="application/json">__DATA__</script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script>
(function(){
'use strict';
var D = JSON.parse(document.getElementById('data').textContent);
var TYPE_ES = {module:'Código', page:'Página', data:'Datos', test:'Pruebas', doc:'Documentos', endpoint:'Rutas y MCP',
  env:'Variables', session:'Sesiones'};
var TYPE_ONE = {module:'módulo', page:'página', data:'datos', test:'prueba', doc:'documento', endpoint:'ruta / herramienta MCP',
  env:'variable de entorno', session:'sesión de trabajo'};
var DEFAULT_ON = {module:1, page:1, data:1, test:0, doc:0, endpoint:0, env:0, session:0};
var E_OUT = {imports:'Importa', uses_global:'Usa globales de', calls_endpoint:'Llama a', defines_endpoint:'Define',
  tested_by:'Probado por', reads_env:'Lee la variable', mentions_in_session:'Menciona', loads_script:'Carga',
  references_file:'Nombra el archivo', via_endpoint:'Llama (vía ruta) a'};
var E_IN = {imports:'Lo importan', uses_global:'Usan sus globales', calls_endpoint:'La llaman', defines_endpoint:'Definida en',
  tested_by:'Prueba a', reads_env:'La leen', mentions_in_session:'Mencionado en', loads_script:'Lo carga',
  references_file:'Lo nombran', via_endpoint:'Lo llaman (vía ruta)'};
if (!window.d3){
  document.getElementById('cv').replaceWith(Object.assign(document.createElement('p'), {
    textContent:'No se pudo cargar la librería de dibujo (d3) desde cdnjs.cloudflare.com. Revisa tu conexión a internet y recarga.',
    style:'padding:24px;color:var(--ink-2)'}));
  return;
}
var nodes = D.nodes.map(function(a, i){
  return {i:i, label:a[0], layer:a[1], type:D.types[a[2]], lines:a[3], path:a[4], note:a[5], deg:0};
});
var links = D.edges.map(function(e){ return {s:e[0], t:e[1], type:D.etypes[e[2]]}; });
links.forEach(function(l){ nodes[l.s].deg++; nodes[l.t].deg++; });
var adjOut = nodes.map(function(){return [];}), adjIn = nodes.map(function(){return [];});
links.forEach(function(l){ adjOut[l.s].push(l); adjIn[l.t].push(l); });
var typeOn = {}; D.types.forEach(function(t){ typeOn[t] = !!DEFAULT_ON[t]; });
var layerOn = D.layers.map(function(){ return true; });
var selected = null, hover = null;
var css = {};
function readCss(){
  var cs = getComputedStyle(document.documentElement);
  ['bg','surface','ink','ink-2','muted','edge','edge-hi','ring','focus','s1','s2','s3','s4','s5','s6','s7','s8','n1','n2']
    .forEach(function(k){ css[k] = cs.getPropertyValue('--' + k).trim(); });
}
readCss();
function color(n){ return css[D.layers[n.layer].slot]; }
function isRing(n){ return D.layers[n.layer].style === 'ring'; }
function radius(n){
  if (n.type === 'module' || n.type === 'page' || n.type === 'data') return Math.max(3.2, Math.min(15, 2.4 + Math.sqrt(n.lines) / 5.2));
  if (n.type === 'test') return 3; if (n.type === 'doc') return 4.2;
  return 2.6;
}
function visible(n){ return typeOn[n.type] && layerOn[n.layer]; }

// ── controles ──
var typesEl = document.getElementById('types');
var counts = {}; nodes.forEach(function(n){ counts[n.type] = (counts[n.type] || 0) + 1; });
D.types.forEach(function(t){
  if (!counts[t]) return;
  var b = document.createElement('button'); b.type = 'button'; b.className = 'chip';
  b.setAttribute('aria-pressed', String(typeOn[t]));
  b.innerHTML = '<span class="nm"></span> <span class="n"></span>';
  b.querySelector('.nm').textContent = TYPE_ES[t]; b.querySelector('.n').textContent = counts[t];
  b.onclick = function(){ typeOn[t] = !typeOn[t]; b.setAttribute('aria-pressed', String(typeOn[t])); refresh(); };
  typesEl.appendChild(b);
});
var layersEl = document.getElementById('layers'), layerBtns = [];
var lcount = D.layers.map(function(){ return 0; }); nodes.forEach(function(n){ lcount[n.layer]++; });
D.layers.forEach(function(L, k){
  if (!lcount[k]) { layerBtns.push(null); return; }
  var b = document.createElement('button'); b.type = 'button'; b.className = 'chip'; b.setAttribute('aria-pressed', 'true');
  var sw = document.createElement('span'); sw.className = 'sw' + (L.style === 'ring' ? ' ring' : '');
  b.appendChild(sw);
  var nm = document.createElement('span'); nm.className = 'nm'; nm.textContent = L.name; b.appendChild(nm);
  var c = document.createElement('span'); c.className = 'n'; b.appendChild(c);
  b.onclick = function(){ layerOn[k] = !layerOn[k]; b.setAttribute('aria-pressed', String(layerOn[k])); refresh(); };
  layersEl.appendChild(b); layerBtns.push(b);
});
function layerCounts(){
  var cnt = D.layers.map(function(){ return 0; });
  nodes.forEach(function(n){ if (typeOn[n.type]) cnt[n.layer]++; });
  layerBtns.forEach(function(b, k){ if (b) b.querySelector('.n').textContent = cnt[k]; });
}
function paintSwatches(){
  layerBtns.forEach(function(b, k){ if (!b) return; var sw = b.querySelector('.sw'); var c = css[D.layers[k].slot];
    if (D.layers[k].style === 'ring') { sw.style.borderColor = c; } else { sw.style.background = c; } });
}
paintSwatches();
document.getElementById('layerCount').textContent = '(' + D.layers.filter(function(L,k){return lcount[k];}).length + ')';
document.getElementById('allL').onclick = function(){ layerOn = layerOn.map(function(){return true;}); syncLayerBtns(); refresh(); };
document.getElementById('noneL').onclick = function(){ layerOn = layerOn.map(function(){return false;}); syncLayerBtns(); refresh(); };
function syncLayerBtns(){ layerBtns.forEach(function(b, k){ if (b) b.setAttribute('aria-pressed', String(layerOn[k])); }); }
if (window.innerWidth > 720) document.getElementById('layersBox').open = true;

// ── simulación ──
var canvas = document.getElementById('cv'), ctx = canvas.getContext('2d');
var W = 0, H = 0, dpr = 1, transform = d3.zoomIdentity;
var nl = D.layers.length;
var stageR = document.querySelector('main').getBoundingClientRect();
var portrait = stageR.height > stageR.width * 1.15;          /* teléfono vertical: capas en un óvalo alto */
var RX = portrait ? 250 : 420, RY = portrait ? 470 : 300;
var anchor = D.layers.map(function(L, k){ var a = (k / nl) * Math.PI * 2 - Math.PI / 2; return {x: Math.cos(a) * RX, y: Math.sin(a) * RY}; });
nodes.forEach(function(n){ var a = anchor[n.layer]; n.x = a.x + (Math.random() - .5) * 140; n.y = a.y + (Math.random() - .5) * 140; });
var sim = d3.forceSimulation().alphaDecay(0.035).velocityDecay(0.45)
  .force('charge', d3.forceManyBody().strength(function(n){ return -16 - radius(n) * 3; }).distanceMax(360))
  .force('link', d3.forceLink().id(function(n){ return n.i; }).distance(function(l){ return l.type === 'tested_by' ? 46 : 36; }).strength(0.035))
  .force('x', d3.forceX(function(n){ return anchor[n.layer].x; }).strength(0.085))
  .force('y', d3.forceY(function(n){ return anchor[n.layer].y; }).strength(0.085))
  .force('collide', d3.forceCollide(function(n){ return radius(n) + 1.5; }))
  .on('tick', function(){ schedule(); if (!touched && sim.alpha() < 0.09) fit(false); });
var touched = false;
function fit(animate){
  if (!vis.length || !W) return;
  var x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  vis.forEach(function(n){ var r = radius(n); x0 = Math.min(x0, n.x - r); y0 = Math.min(y0, n.y - r); x1 = Math.max(x1, n.x + r); y1 = Math.max(y1, n.y + r); });
  var pad = W < 720 ? 18 : 40, k = Math.min((W - pad * 2) / Math.max(1, x1 - x0), (H - pad * 2) / Math.max(1, y1 - y0), 2.2);
  var t = d3.zoomIdentity.translate(W / 2 - (x0 + x1) / 2 * k, H / 2 - (y0 + y1) / 2 * k).scale(k);
  touched = true;
  if (animate) d3.select(canvas).transition().duration(500).call(zoom.transform, t);
  else d3.select(canvas).call(zoom.transform, t);
}
var vis = [], vlinks = [];
function refresh(){
  vis = nodes.filter(visible);
  layerCounts();
  var on = {}; vis.forEach(function(n){ on[n.i] = 1; });
  vlinks = links.filter(function(l){
    if (!on[l.s] || !on[l.t]) return false;
    if (l.type === 'via_endpoint') return !typeOn.endpoint;
    return true;
  });
  sim.nodes(vis);
  sim.force('link').links(vlinks.map(function(l){ return {source:l.s, target:l.t, type:l.type}; }));
  sim.alpha(0.6).restart();
  if (selected && !visible(selected)) closePanel();
  schedule();
}
function resize(){
  var r = canvas.getBoundingClientRect(); dpr = window.devicePixelRatio || 1;
  W = r.width; H = r.height; canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
  schedule();
}
var raf = 0;
function schedule(){ if (!raf) raf = requestAnimationFrame(draw); }
function neighborSet(n){
  var s = {}; if (!n) return s; s[n.i] = 1;
  adjOut[n.i].concat(adjIn[n.i]).forEach(function(l){ s[l.s] = 1; s[l.t] = 1; });
  return s;
}
function draw(){
  raf = 0;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, W, H);
  ctx.translate(transform.x, transform.y); ctx.scale(transform.k, transform.k);
  var focus = selected || hover, nb = neighborSet(focus);
  ctx.lineWidth = 1 / transform.k;
  ctx.strokeStyle = css.edge; ctx.beginPath();
  vlinks.forEach(function(l){ var a = nodes[l.s], b = nodes[l.t];
    if (focus && (nb[l.s] && nb[l.t]) && (l.s === focus.i || l.t === focus.i)) return;
    ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); });
  ctx.globalAlpha = focus ? 0.35 : 1; ctx.stroke(); ctx.globalAlpha = 1;
  if (focus){
    ctx.lineWidth = 1.6 / transform.k; ctx.strokeStyle = css['edge-hi']; ctx.beginPath();
    vlinks.forEach(function(l){ if (l.s === focus.i || l.t === focus.i){ var a = nodes[l.s], b = nodes[l.t];
      ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); } });
    ctx.stroke();
  }
  vis.forEach(function(n){
    var r = radius(n), c = color(n), dim = focus && !nb[n.i];
    ctx.globalAlpha = dim ? 0.18 : 1;
    ctx.beginPath();
    if (n.type === 'env') { ctx.rect(n.x - r, n.y - r, r * 2, r * 2); }
    else if (n.type === 'session') { ctx.moveTo(n.x, n.y - r - 1); ctx.lineTo(n.x + r + 1, n.y); ctx.lineTo(n.x, n.y + r + 1); ctx.lineTo(n.x - r - 1, n.y); ctx.closePath(); }
    else ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
    if (isRing(n)) { ctx.fillStyle = css.surface; ctx.fill(); ctx.lineWidth = Math.max(1.6, r * 0.45); ctx.strokeStyle = c; ctx.stroke(); }
    else { ctx.fillStyle = c; ctx.fill(); ctx.lineWidth = 1 / transform.k; ctx.strokeStyle = css.surface; ctx.stroke(); }
    if (selected && n.i === selected.i){ ctx.lineWidth = 2.5 / transform.k; ctx.strokeStyle = css.ring;
      ctx.beginPath(); ctx.arc(n.x, n.y, r + 3.5 / transform.k + 1, 0, Math.PI * 2); ctx.stroke(); }
  });
  ctx.globalAlpha = 1;
  // etiquetas: grandes al acercar, y siempre el foco y sus vecinos
  ctx.font = (11 / transform.k) + 'px system-ui,-apple-system,Segoe UI,Roboto,sans-serif';
  ctx.textBaseline = 'middle'; ctx.fillStyle = css.ink;
  var minR = transform.k > 2.2 ? 0 : (transform.k > 1.2 ? 6 : 10.5);
  vis.forEach(function(n){
    var r = radius(n), show = focus ? nb[n.i] : (r >= minR && (n.type === 'module' || n.type === 'page' || n.type === 'data'));
    if (!show) return;
    var t = shortLabel(n);
    ctx.lineWidth = 3 / transform.k; ctx.strokeStyle = css.bg; ctx.strokeText(t, n.x + r + 3 / transform.k, n.y);
    ctx.fillText(t, n.x + r + 3 / transform.k, n.y);
  });
}
function shortLabel(n){
  if (n.type === 'module' || n.type === 'data' || n.type === 'test' || n.type === 'page'){ var p = n.label.split('/'); return p[p.length - 1]; }
  return n.label.length > 42 ? n.label.slice(0, 40) + '…' : n.label;
}
var zoom = d3.zoom().scaleExtent([0.15, 8]).on('zoom', function(ev){ transform = ev.transform; if (ev.sourceEvent) touched = true; schedule(); });
d3.select(canvas).call(zoom).on('dblclick.zoom', null);
function toGraph(ev){ var r = canvas.getBoundingClientRect(); return transform.invert([ev.clientX - r.left, ev.clientY - r.top]); }
function pick(ev){ var p = toGraph(ev); var n = sim.find(p[0], p[1], 14 / transform.k + 4); return n || null; }
canvas.addEventListener('mousemove', function(ev){
  var n = pick(ev); var tip = document.getElementById('tip');
  if (n !== hover){ hover = n; schedule(); }
  canvas.style.cursor = n ? 'pointer' : 'grab';
  if (n){ var r = canvas.getBoundingClientRect(); tip.textContent = n.label + ' · ' + D.layers[n.layer].name;
    tip.style.display = 'block'; tip.style.left = Math.min(ev.clientX - r.left + 12, W - 200) + 'px'; tip.style.top = (ev.clientY - r.top + 12) + 'px'; }
  else tip.style.display = 'none';
});
canvas.addEventListener('mouseleave', function(){ hover = null; document.getElementById('tip').style.display = 'none'; schedule(); });
canvas.addEventListener('click', function(ev){ var n = pick(ev); if (n) select(n, false); else closePanel(); });
canvas.addEventListener('dblclick', function(){ fit(true); });

// ── panel ──
var panel = document.getElementById('panel');
function closePanel(){ selected = null; panel.classList.remove('open'); schedule(); }
document.getElementById('pClose').onclick = closePanel;
document.addEventListener('keydown', function(ev){ if (ev.key === 'Escape') closePanel(); });
function el(tag, cls, txt){ var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
function nodeButton(n){
  var b = el('button'); b.type = 'button';
  var sw = el('span', 'sw' + (isRing(n) ? ' ring' : '')); if (isRing(n)) sw.style.borderColor = color(n); else sw.style.background = color(n);
  b.appendChild(sw); b.appendChild(el('span', 'lbl', n.label));
  b.title = n.label; b.onclick = function(){ select(n, true); };
  return b;
}
function select(n, center){
  if (!visible(n)){ typeOn[n.type] = true; layerOn[n.layer] = true; syncLayerBtns();
    Array.prototype.forEach.call(typesEl.querySelectorAll('.chip'), function(b){
      var t = Object.keys(TYPE_ES).find(function(k){ return TYPE_ES[k] === b.querySelector('.nm').textContent; });
      if (t) b.setAttribute('aria-pressed', String(typeOn[t])); });
    refresh(); }
  selected = n; panel.classList.add('open');
  document.getElementById('pTitle').textContent = n.label;
  var body = document.getElementById('pBody'); body.innerHTML = '';
  var dl = el('dl', 'meta');
  function row(k, v, isCode){ dl.appendChild(el('dt', null, k)); var dd = el('dd'); if (isCode){ dd.appendChild(el('code', null, v)); } else dd.textContent = v; dl.appendChild(dd); }
  row('Tipo', TYPE_ONE[n.type]); row('Capa', D.layers[n.layer].name);
  if (n.path) row('Ruta', n.path, true);
  if (n.lines) row('Líneas', n.lines.toLocaleString('es'));
  row('Nota', n.note + '.md', true);
  body.appendChild(dl);
  var a = el('a', null, 'Abrir la nota en Obsidian'); a.href = 'obsidian://open?vault=vault&file=' + encodeURIComponent(n.note);
  a.style.fontSize = '12px'; a.style.color = 'var(--focus)'; body.appendChild(a);
  var groups = {};
  adjOut[n.i].forEach(function(l){ if (l.type === 'via_endpoint') return; (groups['o:' + l.type] = groups['o:' + l.type] || []).push(nodes[l.t]); });
  adjIn[n.i].forEach(function(l){ if (l.type === 'via_endpoint') return;
    if (l.type === 'imports' && nodes[l.s].type === 'test') return;   /* ya salen en "Probado por" */
    (groups['i:' + l.type] = groups['i:' + l.type] || []).push(nodes[l.s]); });
  var keys = Object.keys(groups).sort();
  if (!keys.length) body.appendChild(el('p', 'grp', 'Sin conexiones'));
  keys.forEach(function(k){
    var dir = k[0], t = k.slice(2), list = groups[k].sort(function(x, y){ return x.label < y.label ? -1 : 1; });
    body.appendChild(el('div', 'grp', (dir === 'o' ? E_OUT[t] : E_IN[t]) + ' (' + list.length + ')'));
    var ul = el('ul', 'lst');
    list.slice(0, 80).forEach(function(m){ var li = el('li'); li.appendChild(nodeButton(m)); ul.appendChild(li); });
    if (list.length > 80) ul.appendChild(el('li', 'grp', '… y ' + (list.length - 80) + ' más'));
    body.appendChild(ul);
  });
  if (center){ var k = Math.max(transform.k, 1.4);
    d3.select(canvas).transition().duration(450).call(zoom.transform, d3.zoomIdentity.translate(W / 2 - n.x * k, H / 2 - n.y * k).scale(k)); }
  schedule();
}

// ── búsqueda ──
var q = document.getElementById('q'), res = document.getElementById('results'), hits = [], cur = -1;
function norm(s){ return (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); }
nodes.forEach(function(n){ n._k = norm(n.label + ' ' + n.path); });
q.addEventListener('input', function(){
  var s = norm(q.value.trim()); res.innerHTML = ''; cur = -1;
  if (!s){ res.style.display = 'none'; q.setAttribute('aria-expanded', 'false'); return; }
  hits = nodes.filter(function(n){ return n._k.indexOf(s) >= 0; })
    .sort(function(a, b){ return (a._k.indexOf(s) - b._k.indexOf(s)) || (b.deg - a.deg); }).slice(0, 12);
  hits.forEach(function(n, i){
    var b = el('button'); b.type = 'button'; b.setAttribute('role', 'option');
    var sw = el('span', 'sw' + (isRing(n) ? ' ring' : '')); if (isRing(n)) sw.style.borderColor = color(n); else sw.style.background = color(n);
    b.appendChild(sw); b.appendChild(el('span', 'lbl', n.label)); b.appendChild(el('span', 't', TYPE_ONE[n.type]));
    b.onclick = function(){ choose(i); }; res.appendChild(b);
  });
  if (!hits.length) res.appendChild(el('div', 'grp', 'Sin resultados'));
  res.style.display = 'block'; q.setAttribute('aria-expanded', 'true');
});
function choose(i){ var n = hits[i]; if (!n) return; res.style.display = 'none'; q.setAttribute('aria-expanded', 'false'); select(n, true); }
q.addEventListener('keydown', function(ev){
  if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp'){ ev.preventDefault(); if (!hits.length) return;
    cur = (cur + (ev.key === 'ArrowDown' ? 1 : -1) + hits.length) % hits.length;
    Array.prototype.forEach.call(res.children, function(c, j){ c.classList.toggle('on', j === cur); }); }
  else if (ev.key === 'Enter'){ choose(cur >= 0 ? cur : 0); }
  else if (ev.key === 'Escape'){ res.style.display = 'none'; }
});
document.addEventListener('click', function(ev){ if (!ev.target.closest('.search')) res.style.display = 'none'; });

// ── tema y tamaño ──
var mq = window.matchMedia('(prefers-color-scheme: dark)');
(mq.addEventListener ? mq.addEventListener.bind(mq, 'change') : mq.addListener.bind(mq))(function(){ readCss(); paintSwatches(); schedule(); });
window.addEventListener('resize', resize);
resize();
transform = d3.zoomIdentity.translate(W / 2, H / 2).scale(Math.min(W / 1150, H / 820, 1.1));
d3.select(canvas).call(zoom.transform, transform);
refresh();
})();
</script>
</body>
</html>
'''


if __name__ == '__main__':
    sys.exit(main())
