"""core/khipu_chat.py — EL cerebro conversacional de Khipu (texto).

Problema que resuelve (feedback de Fabrizio, 2026-09-30: "el Khipu está
bastante tonto; le pregunto algo y me responde otra cosa… siento que está
limitado"): antes el texto pasaba por regex sueltas que secuestraban las
preguntas (pantallas de oportunidades, gráficos del texto de la pregunta…) y
la IA de /api/ai/command solo veía la lista de nombres de empresas, con 3
frases de máximo y sin acceso a datos.

Ahora: POST /api/khipu/chat → un bucle de agente con HERRAMIENTAS REALES.

  · Protocolo JSON (no el tool-calling nativo de un proveedor) para que
    funcione igual con Claude, Gemini o NVIDIA: en cada paso el modelo
    devuelve {"tool": nombre, "args": {...}} (o {"calls": [...]}, hasta 3 en
    paralelo) o {"final": {"answer": "...", "actions": [...]}}.
  · Herramientas = las MISMAS funciones de solo lectura del servidor MCP
    (mcp_server/tools.py: nada se duplica, todo trae source/as_of) + algunas
    ligeras propias (noticias, movimientos del día, ranking del grafo, espacio,
    búsqueda web si hay TAVILY_KEY). NUNCA herramientas de órdenes: este
    cerebro es de solo lectura; "compra X" → explica y ofrece la acción
    'broker' (la orden se confirma en la Cabina con el flujo de siempre).
  · Toda llamada de IA pasa por core.ai._ai_complete → guardián de cifras +
    bloque DATOS EN VIVO. Límites: 5 rondas de herramientas, ~45 s en total.
  · Sin IA (sin keys, ocupada o caída) → mensaje bilingüe claro + respuesta
    determinista con los datos reales de las herramientas cuando se puede
    (p. ej. ficha de la empresa mencionada).
  · Acciones de pantalla validadas contra una lista blanca; los ids de
    empresa se validan con core.entities (nunca un id inventado).
"""
import json
import logging
import re
import sys
import threading
import time
import uuid
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as _FutTimeout
from concurrent.futures import wait
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request

from core import ai as _ai
from core.http import rate_limit

log = logging.getLogger('khipu')

khipu_chat_bp = Blueprint('khipu_chat', __name__, url_prefix='/api/khipu')

MAX_STEPS = 5                  # rondas de herramientas (la respuesta final es aparte)
TIME_BUDGET_S = 45.0           # presupuesto total de la petición
MIN_STEP_S = 4.0               # por debajo de esto no se lanza otra llamada de IA
FINAL_RESERVE_S = 14.0         # con menos tiempo que esto se exige la respuesta final
MAX_MESSAGE = 2000
MAX_HISTORY = 12
MAX_HISTORY_ITEM = 1500
MAX_TOOL_RESULT_CHARS = 7000
MAX_SCRATCH_CHARS = 26000
MAX_CALLS_PER_STEP = 3
MAX_ACTIONS = 3
MAX_ANSWER = 6000
SYNTH_TIMEOUT_S = 20.0         # redacción final en prosa (cuando el protocolo falla)
SYNTH_GRACE_S = 4.0            # margen extra sobre el presupuesto para esa redacción (45+4+20 < 70 s del cliente)
STEP_MAX_TOKENS = 1600
TOOL_TIMEOUT_S = 14.0

_POOL = ThreadPoolExecutor(max_workers=8, thread_name_prefix='khipu-chat')


def _ai_interactive(fn, *a, **kw):
    """R7: las llamadas de IA del chat corren en un hilo del pool (sin contexto de
    petición) y core/ai las tomaba por trabajo de FONDO: nunca usaban el cupo
    reservado al usuario y recibían 'IA ocupada' mientras ese cupo estaba libre."""
    with _ai.ai_background(False):
        return fn(*a, **kw)


def _submit_ai(fn, *a, **kw):
    """Llamada de IA del chat en el pool, ATRIBUIDA a quien la pidió: ai_usage.bind captura
    la función/quién en ESTE hilo (la petición → 'khipu_chat'; el informe de cartera →
    'riesgo_cartera') y la reaplica en el hilo del pool. Sin esto el gasto quedaba como
    'fondo' y la tarjeta de Khipu (core/agents_api) mostraba 'sin actividad'."""
    from core import ai_usage
    return _POOL.submit(ai_usage.bind(_ai_interactive), fn, *a, **kw)


TABS = ('map', 'market', 'analysis', 'geo', 'simulation', 'space', 'terminal', 'canvas', 'portfolios', 'guia')
PRESETS = ('taiwan_conflict', 'china_chip_ban_total', 'hbm_shortage_2027', 'openai_ipo_impact', 'starshield_reveal')

# ════════════════════════════════════════════════════════════════════════════
# KHIPUS OS (2026-10-06, docs/KHIPUS_OS.md §3.2): qué AGENTE (mascota) hace cada
# herramienta. EL MISMO mapa vive en el cliente (engine/khipu_chat.js) y el de
# puesto → mascota es el de engine/mascot.js: cambiar los tres juntos.
# ════════════════════════════════════════════════════════════════════════════
AGENT_IDS = ('khipu', 'analista', 'radar', 'cadena', 'tecnico', 'comite')
TOOL_AGENT = {
    'get_company': 'analista', 'search_companies': 'analista', 'get_research': 'analista',
    'get_claim_evidence': 'analista',
    'get_supply_chain': 'cadena', 'rank_companies': 'cadena',
    'get_news': 'radar', 'get_world_events': 'radar', 'web_search': 'radar', 'scenario_exposure': 'radar',
    'market_movers': 'tecnico', 'get_option_greeks': 'tecnico', 'get_risk_report': 'tecnico',
    'get_committee_memo': 'comite', 'get_conclusions_board': 'comite', 'get_track_record': 'comite',
}
SEAT_AGENT = {}
for _ag, _seats in (('khipu', ('khipu', 'brain')),
                    ('analista', ('fundamental', 'fundamentals', 'macro', 'valuation')),
                    ('radar', ('news', 'sentiment', 'geopolitical', 'geo', 'events', 'crypto')),
                    ('cadena', ('supply_chain', 'chain', 'supply')),
                    ('tecnico', ('technical', 'momentum', 'risk', 'risk_observation', 'risk_officer', 'market')),
                    ('comite', ('committee', 'chair', 'portfolio', 'president', 'quant', 'mandate', 'all'))):
    for _s in _seats:
        SEAT_AGENT[_s] = _ag
AGENT_LABEL = {'khipu': ('Khipu', 'Khipu'), 'analista': ('Analista', 'Analyst'), 'radar': ('Radar', 'Radar'),
               'cadena': ('Cadena', 'Chain'), 'tecnico': ('Técnico', 'Technical'), 'comite': ('Comité', 'Committee')}


def tool_agent(name, args=None):
    """Herramienta (+ sus argumentos) → id de la mascota que la "hace"."""
    if name == 'ask_agent':
        seat = str((args or {}).get('seat') or '').strip().lower() if isinstance(args, dict) else ''
        if seat not in SEAT_AGENT:
            try:                     # 'técnico', 'noticias', 'todos'… → puesto canónico (misma regla que @menciones)
                from research.ask_agent import seat_from_words
                seat = seat_from_words(seat) or seat
            except Exception:  # noqa: BLE001
                pass
        return SEAT_AGENT.get(seat, 'analista')
    return TOOL_AGENT.get(name, 'khipu')


# ── progreso EN VIVO de una pregunta (GET /api/khipu/chat/progress/<req_id>) ──
# En memoria (el servidor corre 1 worker: el estado es único), TTL 5 min y tope de
# entradas: el cliente lo consulta cada ~0,7 s para mostrar qué agentes trabajan.
PROGRESS_TTL_S = 300.0
PROGRESS_MAX = 500
_REQ_ID_RX = re.compile(r'[A-Za-z0-9_-]{1,64}')
_PROG = OrderedDict()
_PROG_LOCK = threading.Lock()


def valid_req_id(x):
    return x if isinstance(x, str) and _REQ_ID_RX.fullmatch(x) else None


def _prog_purge_locked(now):
    while _PROG:
        k, v = next(iter(_PROG.items()))
        if len(_PROG) > PROGRESS_MAX or now - v['ts'] > PROGRESS_TTL_S:
            _PROG.popitem(last=False)
        else:
            break


def progress_begin(req_id):
    if not req_id:
        return
    now = time.time()
    with _PROG_LOCK:
        _PROG.pop(req_id, None)
        _PROG[req_id] = {'ts': now, 't0': time.monotonic(), 'done': False, 'phase': 'start', 'agents': [],
                         'elapsed_ms': None}
        _prog_purge_locked(now)


def progress_phase(req_id, phase):
    if not req_id:
        return
    with _PROG_LOCK:
        rec = _PROG.get(req_id)
        if rec is not None and not rec['done']:
            rec['phase'] = phase


def progress_add(req_id, tool, args=None, state='working'):
    """Registra una consulta → índice (para actualizar su estado) o None."""
    if not req_id:
        return None
    with _PROG_LOCK:
        rec = _PROG.get(req_id)
        if rec is None or rec['done']:
            return None
        rec['agents'].append({'agent': tool_agent(tool, args), 'tool': tool, 'state': state})
        return len(rec['agents']) - 1


def progress_set(req_id, idx, state):
    if not req_id or idx is None:
        return
    with _PROG_LOCK:
        rec = _PROG.get(req_id)
        if rec is not None and 0 <= idx < len(rec['agents']) and rec['agents'][idx]['state'] == 'working':
            rec['agents'][idx]['state'] = state


def _progress_from_future(req_id, idx, fut):
    try:
        ok, _res = fut.result()
    except Exception:  # noqa: BLE001
        ok = False
    progress_set(req_id, idx, 'done' if ok else 'error')


def progress_end(req_id):
    if not req_id:
        return
    with _PROG_LOCK:
        rec = _PROG.get(req_id)
        if rec is None or rec['done']:
            return
        for a in rec['agents']:
            if a['state'] == 'working':       # no llegó a tiempo para esta respuesta
                a['state'] = 'error'
        rec['done'] = True
        rec['phase'] = 'done'
        rec['elapsed_ms'] = int((time.monotonic() - rec['t0']) * 1000)


def progress_get(req_id):
    with _PROG_LOCK:
        _prog_purge_locked(time.time())
        rec = _PROG.get(req_id)
        if rec is None:
            return {'req_id': req_id, 'done': False, 'elapsed_ms': 0, 'phase': None, 'agents': []}
        el = rec['elapsed_ms'] if rec['done'] else int((time.monotonic() - rec['t0']) * 1000)
        return {'req_id': req_id, 'done': rec['done'], 'elapsed_ms': el, 'phase': rec['phase'],
                'agents': [dict(a) for a in rec['agents']]}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


class ChatValidationError(ValueError):
    def __init__(self, es, en):
        super().__init__(en)
        self.es, self.en = es, en


class ToolFailure(Exception):
    """Error de una herramienta propia (se le devuelve al modelo como texto)."""


# ════════════════════════════════════════════════════════════════════════════
# herramientas
# ════════════════════════════════════════════════════════════════════════════
# Herramientas de SOLO LECTURA del servidor MCP que el cerebro reutiliza.
# (2026-10-04) fuera del catálogo del chat: get_ontology_object y get_option_greeks (ruido para el modelo;
# siguen en el MCP). Menos herramientas = decisiones mejores y más rápidas.
MCP_READ_TOOLS = ('search_companies', 'get_company', 'get_supply_chain', 'get_research', 'get_research_health', 'get_claim_evidence',
                  'get_committee_memo', 'get_conclusions_board', 'get_track_record', 'get_risk_report',
                  'get_world_events')

_EXTRA = {}     # nombre → {'sig', 'desc', 'fn', 'available'}


def _extra(name, sig, desc, available=None):
    def deco(fn):
        _EXTRA[name] = {'sig': sig, 'desc': desc, 'fn': fn, 'available': available or (lambda: True)}
        return fn
    return deco


def _mcp():
    from mcp_server import tools as mt
    return mt


_PRINCIPAL = {'p': None}


def _principal():
    if _PRINCIPAL['p'] is None:
        from mcp_server.auth import Principal
        _PRINCIPAL['p'] = Principal(token_id='khipu-chat', name='khipu-chat', scopes=frozenset({'read'}))
    return _PRINCIPAL['p']


def _schema_sig(schema):
    parts = []
    req = set(schema.get('required') or [])
    for k, v in (schema.get('properties') or {}).items():
        t = v.get('type') or 'any'
        if v.get('enum'):
            t = '|'.join(str(e) for e in v['enum'])
        elif t == 'array' and isinstance(v.get('items'), dict):
            it = v['items']
            if it.get('type') == 'object':
                t = '[{' + ', '.join(f'{ik}' for ik in (it.get('properties') or {})) + '}]'
            elif it.get('enum'):
                t = '[' + '|'.join(it['enum']) + ']'
        parts.append(f'{k}{"" if k in req else "?"}:{t}')
    return ', '.join(parts)


def _clip(s, n):
    s = re.sub(r'\s+', ' ', str(s or '')).strip()
    return s if len(s) <= n else s[:n - 1] + '…'


def tool_catalog():
    """[(nombre, firma, descripción)] de las herramientas DISPONIBLES ahora."""
    out = []
    try:
        reg = _mcp().REGISTRY
        for name in MCP_READ_TOOLS:
            t = reg.get(name)
            if t is not None and t.scope == 'read':
                out.append((name, _schema_sig(t.input_schema), _clip(t.description, 170)))
    except Exception as e:  # noqa: BLE001
        log.warning('khipu_chat: catálogo MCP no disponible (%s)', type(e).__name__)
    for name, spec in _EXTRA.items():
        try:
            ok = spec['available']()
        except Exception:  # noqa: BLE001
            ok = False
        if ok:
            out.append((name, spec['sig'], spec['desc']))
    return out


def _snapshot():
    return _mcp()._snapshot()


def _node_label(nid):
    n = (_snapshot()['nodes'].get(nid) or {})
    return n.get('label') or nid


@_extra('get_news', 'company:string, limit?:integer 1-15',
        'Latest news headlines about ONE company (Finnhub company news for listed tickers, GDELT global news '
        'otherwise): title, outlet, date and URL. Use it for "what happened with X", "why did X move".')
def x_get_news(company, limit=8):
    mt = _mcp()
    r = mt._resolve_or_fail(company)
    n = _snapshot()['nodes'].get(r['id']) or {}
    try:
        limit = max(1, min(15, int(limit)))
    except (TypeError, ValueError):
        limit = 8
    from core.config import FINNHUB
    from core.http import _safe_get, _safe_ticker
    sym = _safe_ticker(n.get('mkt') or '') if mt._listed(n) else None
    items, src = [], None
    if sym and FINNHUB:
        from datetime import date, timedelta
        today = date.today()
        data, err = _safe_get(f'https://finnhub.io/api/v1/company-news?symbol={sym}&from='
                              f'{(today - timedelta(days=14)).isoformat()}&to={today.isoformat()}&token={FINNHUB}',
                              timeout=8)
        if not err and isinstance(data, list):
            for a in data[:limit]:
                ts = a.get('datetime')
                items.append({'title': a.get('headline'), 'outlet': a.get('source'), 'url': a.get('url'),
                              'date': (datetime.fromtimestamp(ts, timezone.utc).isoformat() if isinstance(ts, (int, float))
                                       else None),
                              'summary': _clip(a.get('summary'), 280)})
            src = 'Finnhub company news'
    if not items:
        from urllib.parse import quote
        q = re.sub(r'[^A-Za-z0-9 ._-]', '', n.get('label') or r['id'])[:60]
        data, err = _safe_get(f'https://api.gdeltproject.org/api/v2/doc/doc?query={quote(chr(34) + q + chr(34))}'
                              '&mode=artlist&maxrecords=20&format=json&sort=datedesc', timeout=10)
        if not err and isinstance(data, dict):
            for a in (data.get('articles') or [])[:limit]:
                items.append({'title': a.get('title'), 'outlet': a.get('domain'), 'url': a.get('url'),
                              'date': a.get('seendate'), 'language': a.get('language')})
            src = 'GDELT (global news index)'
    if not items:
        raise ToolFailure(f'no news could be fetched for {n.get("label") or r["id"]} right now '
                          '(news sources unavailable or nothing recent)')
    return {'company': {'id': r['id'], 'label': n.get('label'), 'symbol': n.get('mkt')}, 'count': len(items),
            'items': items, 'source': src, 'as_of': _now_iso()}


@_extra('ask_agent', 'seat:fundamental|technical|news|supply_chain|geopolitical|macro|crypto|all, question:string, company:string',
        'Ask ONE of the Khipus research analysts (the committee seats) — or all of them — a question about a company, '
        'IN THEIR OWN VOICE and FROM THEIR ROLE: each seat brings its own live skills (supply_chain → supplier '
        'concentration, supplier countries, upstream/downstream risk; technical → price indicators; fundamental → '
        'statements, ratios, peers; news/geopolitical/macro → live events and indices) plus its research conclusions '
        'if any. Use it when the user wants a specific analyst\'s view ("what does the technical analyst think", '
        '"pregúntale al de noticias", "@fundamental"). No prior research is needed.')
def x_ask_agent(seat, question, company, lang='es'):
    # `lang` NO lo elige el modelo: execute_tool lo inyecta con el idioma de la PETICIÓN (antes se leía de
    # _PRINCIPAL, que nunca lo tuvo → el analista respondía siempre en español aunque la app estuviera en inglés)
    from research import ask_agent as aa
    lang = 'en' if str(lang or '').lower().startswith('en') else 'es'
    seat = aa.seat_from_words(str(seat or '')) or str(seat or '').strip().lower()
    with _research_session() as s:      # sin base: responde igual con sus habilidades en vivo
        if seat == 'all':
            r = aa.ask_all(s, str(question or ''), str(company or ''), lang)
        else:
            r = aa.ask(s, seat, str(question or ''), str(company or ''), lang)
    out = {k: v for k, v in (r or {}).items() if k in ('ok', 'seat', 'emoji', 'name', 'entity', 'label', 'answer', 'n_claims', 'needs_research')}
    if r and r.get('answers'):
        out['answers'] = [{k: a.get(k) for k in ('seat', 'emoji', 'name', 'answer', 'n_claims', 'needs_research')} for a in r['answers']]
    sk = (r or {}).get('skill') or {}
    if sk.get('facts'):
        out['role_data'] = sk['facts']
    out['source'] = 'Khipus analyst skills (live data of its role) + research claims; answer written by the analyst persona (AI)'
    return out


def _research_session():
    """Sesión de la base de investigación, o un contexto vacío (None) si no hay base."""
    import contextlib
    try:
        from ontology.db import ontology_available as db_ok, session_scope
        if db_ok():
            return session_scope()
    except Exception:  # noqa: BLE001
        pass
    return contextlib.nullcontext(None)


@_extra('scenario_exposure', 'scenario:string (the what-if in plain words)',
        'STRUCTURAL ANALYSIS of a hypothetical scenario on the Khipus supply-chain graph: what is at stake (e.g. HBM, '
        'rare earths, Taiwan), who acts, which companies take the DIRECT hit, which could BENEFIT (substitutes), and '
        'who is hit through the chain (customers / suppliers) with the PATH of each impact and what to watch. Use it '
        'for "what if…", "most exposed to…", "who loses if…", war/ban/tariff/shortage questions.')
def x_scenario_exposure(scenario):
    from core import scenario_engine, semantic
    snap = semantic._load_snapshot()
    a = scenario_engine.analyze(str(scenario or '')[:300], snap)
    if not a:
        raise ToolFailure('could not identify companies, product or country in that scenario; name at least one')
    return {'theme': a['theme_en'] or a['theme_es'], 'actor': a['actor_en'], 'event': a['event'],
            'mechanism': a['mechanism_en'],
            'direct_hit': [snap['by_id'][i].get('label') for i in a['hit']],
            'could_benefit': [snap['by_id'][i].get('label') for i in a['benefit']],
            'impacts': [{'company': x['label'], 'id': x['id'], 'channel': x['channel'], 'severity': x['sev'],
                         'path': x['path'], 'country': x['country']} for x in a['impacts'][:15]],
            'watch': a['watch_en'], 'source': 'Khipus supply-chain graph (structural estimate, not prices)',
            'as_of': _now_iso()}


@_extra('market_movers', 'direction?:up|down, limit?:integer 1-20, sector?:string',
        "Today's biggest LIVE price moves (%) among the listed companies of the Khipus graph (Yahoo Finance, "
        'refreshed every ~15 min), optionally filtered by sector. Use it for "what is moving today", '
        '"which chip stocks fell most".')
def x_market_movers(direction='up', limit=10, sector=None):
    from core.live_caps import get_caps
    st = get_caps()
    caps = st.get('caps') or {}
    if not caps:
        raise ToolFailure('live market data is still warming up or unavailable — try again in a minute'
                          + (f' ({st.get("error")})' if st.get('error') else ''))
    try:
        limit = max(1, min(20, int(limit)))
    except (TypeError, ValueError):
        limit = 10
    snap = _snapshot()
    sec_q = str(sector or '').strip().lower()
    rows = []
    for nid, c in caps.items():
        if c.get('change_pct') is None:
            continue
        n = snap['nodes'].get(nid) or {}
        if sec_q:
            s = snap['sectors'].get(n.get('sector')) or {}
            if sec_q not in ' '.join(str(x).lower() for x in (n.get('sector'), s.get('label'), s.get('en'),
                                                               n.get('cat'))):
                continue
        rows.append({'id': nid, 'label': n.get('label') or nid, 'symbol': c.get('symbol'),
                     'change_pct': c.get('change_pct'), 'price': c.get('price'), 'currency': c.get('currency'),
                     'market_cap_usd_b': c.get('mcap_b'), 'sector': n.get('sector'),
                     # R9: estado del mercado y hora REAL del precio (no la del lote)
                     'market_state': c.get('market_state'), 'market_time': _iso_time(c.get('price_ts'))})
    rows.sort(key=lambda r: r['change_pct'], reverse=(str(direction).lower() != 'down'))
    return {'direction': 'down' if str(direction).lower() == 'down' else 'up', 'sector_filter': sector or None,
            'universe': len(caps), 'items': rows[:limit], 'source': 'Yahoo Finance (live quotes, Khipus cache)',
            'as_of': st.get('as_of')}


@_extra('rank_companies', 'by?:connections|risk, sector?:string, country?:string, listed_only?:boolean, '
        'limit?:integer 1-25',
        'Rank companies of the Khipus graph by number of supply-chain connections (how central/critical they '
        'are) or by Network Risk Score (fragility), optionally filtered by sector (e.g. "memory", "energy", '
        '"fabricacion") or country. Use it for "most critical companies", "riskiest suppliers in Taiwan".')
def x_rank_companies(by='connections', sector=None, country=None, listed_only=False, limit=10):
    snap = _snapshot()
    mt = _mcp()
    try:
        limit = max(1, min(25, int(limit)))
    except (TypeError, ValueError):
        limit = 10
    sec_q = str(sector or '').strip().lower()
    cty_q = str(country or '').strip().lower()
    by = 'risk' if str(by).lower() in ('risk', 'nrs', 'riesgo') else 'connections'
    rows = []
    try:
        from core.world import client_nrs
    except Exception:  # noqa: BLE001
        client_nrs = None
    for nid, n in snap['nodes'].items():
        if listed_only and not mt._listed(n):
            continue
        if sec_q:
            s = snap['sectors'].get(n.get('sector')) or {}
            hay = ' '.join(str(x).lower() for x in (n.get('sector'), s.get('label'), s.get('en'), n.get('cat')))
            if sec_q not in hay:
                continue
        if cty_q and cty_q not in str(n.get('country') or '').lower() and cty_q not in str(n.get('loc') or '').lower():
            continue
        deg = snap['deg'].get(nid, 0)
        row = mt._brief(n, deg)
        if by == 'risk':
            if client_nrs is None:
                raise ToolFailure('risk score is not available on this server')
            try:
                # G4d: el NRS usa el grado ESTRUCTURAL (pares de flujo), igual que get_company y la app
                row['nrs'] = client_nrs(n, snap['flow_deg'].get(nid, 0))
            except Exception:  # noqa: BLE001
                continue
        rows.append(row)
    key = (lambda r: (-(r.get('nrs') or 0), -r['degree'])) if by == 'risk' else (lambda r: -r['degree'])
    rows.sort(key=key)
    return {'by': by, 'filters': {'sector': sector, 'country': country, 'listed_only': bool(listed_only)},
            'matched': len(rows), 'items': rows[:limit],
            'explain': ('degree = number of supplier/customer links in the curated graph; nrs = Network Risk '
                        'Score 0-100 (higher = more fragile), a heuristic, not a forecast'),
            'source': mt.SNAPSHOT_SOURCE, 'as_of': snap['as_of']}


@_extra('get_space_summary', '',
        'Space economy snapshot: next orbital launch, launches this week/month by provider, active platforms and '
        'Khipus-graph companies involved (Launch Library 2), plus tracked satellites per constellation '
        '(CelesTrak) when available. Use it for questions about launches, SpaceX/Starlink, satellites.')
def x_get_space_summary():
    out = {}
    try:
        from core import space
        up, s_up = space.get_launches('upcoming')
        prev, s_prev = space.get_launches('previous')
        summ = space.summarize(up, prev)
        out['launches'] = json.loads(json.dumps(summ, default=str))
        out['launches_sources'] = {'upcoming': s_up, 'previous': s_prev}
    except Exception as e:  # noqa: BLE001
        out['launches'] = {'available': False, 'reason': type(e).__name__}
    srv = sys.modules.get('server') or sys.modules.get('__main__')
    fn = getattr(srv, '_space_facts_str', None)
    if callable(fn):
        try:
            out['satellites'] = fn()
        except Exception as e:  # noqa: BLE001
            out['satellites'] = f'unavailable ({type(e).__name__})'
    out['source'] = 'Launch Library 2 (The Space Devs) + CelesTrak'
    out['as_of'] = _now_iso()
    return out


def _web_available():
    try:
        from core.websearch import _web_search_available
        return _web_search_available()
    except Exception:  # noqa: BLE001
        return False


@_extra('web_search', 'query:string',
        'Search the open web (recent articles with URL and snippet). Use it for current events or facts that '
        'are not in the Khipus graph (macro, regulation, a company outside the graph). Cite the URLs.',
        available=_web_available)
def x_web_search(query):
    from core.websearch import web_search
    q = _clip(query, 200)
    if not q:
        raise ToolFailure('query is required')
    res = web_search(q, max_results=5, search_depth='basic')
    if not res:
        raise ToolFailure('web search returned nothing (or is unavailable)')
    return {'query': q, 'results': [{'title': r.get('title'), 'url': r.get('url'),
                                     'snippet': _clip(r.get('content'), 600),
                                     'published': r.get('published_date')} for r in res],
            'source': 'Tavily web search', 'as_of': _now_iso()}


def tool_names():
    return [t[0] for t in tool_catalog()]


def _board_memo_flags(res):
    """get_conclusions_board (MCP) da decisión/estado/fecha del memo pero no `decision_code` ni
    `expired`: sin ellos un HOLD SIN QUÓRUM (INSUFFICIENT_DATA) se leía «comité: mantener» y un memo
    vencido como vigente. Se completan desde research.committee.board — la MISMA pizarra (y su
    caché de 60 s) que la herramienta acaba de leer — solo si el memo es el mismo (misma fecha).
    Nunca rompe la herramienta: si no se puede, el resultado sigue igual."""
    if not isinstance(res, dict):
        return res
    need = [x for x in res.get('items') or [] if isinstance(x, dict) and isinstance(x.get('committee'), dict)
            and ('decision_code' not in x['committee'] or 'expired' not in x['committee'])]
    if not need:
        return res
    try:
        from ontology.db import session_scope
        from research import committee as rc
        with session_scope() as s:
            b = rc.board(s, limit=60)
    except Exception as e:  # noqa: BLE001
        log.info('khipu_chat board flags: %s', type(e).__name__)
        return res
    memos = {x.get('entity_id'): x.get('memo') for x in (b or {}).get('items') or []
             if isinstance(x, dict) and isinstance(x.get('memo'), dict)}
    for x in need:
        m, cm = memos.get(x.get('entity_id')), x['committee']
        if m and str(m.get('created_at')) == str(cm.get('date')):
            cm.setdefault('decision_code', m.get('decision_code'))
            if m.get('expired') is not None:
                cm.setdefault('expired', bool(m.get('expired')))
            if m.get('expires_at'):
                cm.setdefault('expires_at', m.get('expires_at'))
    return res


def execute_tool(name, args, app=None, lang=None):
    """→ (ok, result_dict). Nunca lanza. `lang` = idioma de la petición: se pasa a las
    herramientas que redactan en un idioma (ask_agent), por encima de lo que diga el modelo."""
    args = args if isinstance(args, dict) else {}

    def _run():
        if name in _EXTRA:
            spec = _EXTRA[name]
            if not spec['available']():
                raise ToolFailure(f'{name} is not available on this server')
            import inspect
            params = inspect.signature(spec['fn']).parameters
            clean = {k: v for k, v in args.items() if k in params}
            unknown = [k for k in args if k not in params]
            if lang in ('es', 'en') and 'lang' in params:
                clean['lang'] = lang
            res = spec['fn'](**clean)
            if unknown:
                res = dict(res, ignored_arguments=unknown)
            return res
        if name in MCP_READ_TOOLS:
            mt = _mcp()
            res = mt.call(name, args, mt.Ctx(principal=_principal()))
            if name == 'get_conclusions_board':
                res = _board_memo_flags(res)
            return res
        raise KeyError(name)

    def _in_ctx():
        if app is not None:
            with app.app_context():
                return _run()
        return _run()

    try:
        res = _in_ctx()
        return True, (res if isinstance(res, dict) else {'result': res})
    except KeyError:
        return False, {'error': f'unknown tool "{name}". Available tools: {", ".join(tool_names())}'}
    except ToolFailure as e:
        return False, {'error': str(e)}
    except Exception as e:  # noqa: BLE001
        mt = sys.modules.get('mcp_server.tools')
        if mt is not None and isinstance(e, getattr(mt, 'ToolError', ())):
            return False, e.payload()
        if mt is not None and isinstance(e, getattr(mt, 'InvalidParams', ())):
            return False, {'error': f'invalid arguments: {e}'}
        log.warning('khipu_chat tool %s: %s', name, e)
        return False, {'error': f'{type(e).__name__}: {_clip(e, 200)}'}


# ════════════════════════════════════════════════════════════════════════════
# acciones de pantalla (lista blanca)
# ════════════════════════════════════════════════════════════════════════════
ACTION_SPECS = {
    'open_xray': 'node', 'navigate': 'node', 'stress': 'node', 'dossier': 'node', 'open_research': 'node',
    'open_committee': 'node', 'simulate': 'preset', 'agent_sim': 'text', 'chart': 'text', 'compare': 'pair',
    'open_risk_report': 'none', 'switch_tab': 'tab', 'open_world': 'latlon', 'broker': 'none',
    'open_window': 'window',
}
# ventanas nativas de Khipus OS que una respuesta puede abrir (engine/oswindows.js) — todas sobre UNA empresa
WINDOW_KINDS = ('glance', 'supplychain')
_ACTION_ALIASES = {'xray': 'open_xray', 'second_brain': 'open_xray', 'research': 'open_research',
                   'committee': 'open_committee', 'risk_report': 'open_risk_report', 'world': 'open_world',
                   'tab': 'switch_tab', 'agentsim': 'agent_sim', 'sim': 'stress', 'trade': 'broker'}


def resolve_node(x):
    """id/ticker/nombre → id canónico del grafo, o None."""
    if isinstance(x, dict):
        x = x.get('id') or x.get('node_id') or x.get('ticker') or x.get('name')
    if not isinstance(x, str) or not x.strip() or len(x) > 120:
        return None
    nodes = _snapshot()['nodes']
    if x in nodes:
        return x
    try:
        from core.entities import resolve
        r = resolve(x.strip(), umbral=60)
    except Exception:  # noqa: BLE001
        r = None
    return r['id'] if r and r.get('id') in nodes else None


def validate_actions(raw):
    out = []
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return out
    for a in raw[:8]:
        if not isinstance(a, dict):
            continue
        typ = str(a.get('type') or '').strip().lower()
        typ = _ACTION_ALIASES.get(typ, typ)
        kind = ACTION_SPECS.get(typ)
        if not kind:
            continue
        arg = a.get('arg', a.get('args'))
        if kind == 'node':
            nid = resolve_node(arg)
            if not nid:
                continue
            item = {'type': typ, 'arg': nid, 'label': _node_label(nid)}
        elif kind == 'pair':
            if isinstance(arg, (list, tuple)) and len(arg) == 2:
                arg = {'a': arg[0], 'b': arg[1]}
            if not isinstance(arg, dict):
                continue
            ia, ib = resolve_node(arg.get('a')), resolve_node(arg.get('b'))
            if not ia or not ib or ia == ib:
                continue
            item = {'type': typ, 'arg': {'a': ia, 'b': ib}, 'label': f'{_node_label(ia)} vs {_node_label(ib)}'}
        elif kind == 'preset':
            if arg not in PRESETS:
                continue
            item = {'type': typ, 'arg': arg}
        elif kind == 'text':
            if isinstance(arg, dict):
                arg = arg.get('text') or arg.get('scenario') or arg.get('spec') or arg.get('query')
            if not isinstance(arg, str) or len(arg.strip()) < 3:
                continue
            item = {'type': typ, 'arg': _clip(arg, 300)}
        elif kind == 'tab':
            t = str(arg or '').strip().lower()
            if t == 'sim':
                t = 'simulation'
            if t not in TABS:
                continue
            item = {'type': typ, 'arg': t}
        elif kind == 'window':
            if not isinstance(arg, dict) or arg.get('kind') not in WINDOW_KINDS:
                continue
            nid = resolve_node(arg.get('id'))
            if not nid:
                continue
            item = {'type': typ, 'arg': {'kind': arg['kind'], 'id': nid}, 'label': _node_label(nid)}
        elif kind == 'latlon':
            item = {'type': typ, 'arg': None}
            if isinstance(arg, dict):
                try:
                    lat, lon = float(arg.get('lat')), float(arg.get('lon'))
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        item['arg'] = {'lat': round(lat, 4), 'lon': round(lon, 4)}
                except (TypeError, ValueError):
                    pass
        else:   # none
            item = {'type': typ, 'arg': None}
        if any(o['type'] == item['type'] and o['arg'] == item['arg'] for o in out):
            continue
        out.append(item)
        if len(out) >= MAX_ACTIONS:
            break
    return out


# ════════════════════════════════════════════════════════════════════════════
# validación de la petición
# ════════════════════════════════════════════════════════════════════════════
def _guess_lang(text):
    t = f' {str(text or "").lower()} '
    en = len(re.findall(r"\b(the|what|how|why|which|who|is|are|does|do|of|and|should|tell|me|about|risks?)\b", t))
    es = len(re.findall(r'\b(el|la|los|las|qué|que|cómo|como|por|cuál|cuáles|es|son|de|y|dime|sobre|riesgos?)\b', t))
    if re.search(r'[¿¡ñáéíóú]', t):
        es += 2
    return 'en' if en > es else 'es'


def validate_request(body):
    if not isinstance(body, dict):
        raise ChatValidationError('cuerpo JSON inválido', 'invalid JSON body')
    msg = body.get('message')
    if not isinstance(msg, str) or not msg.strip():
        raise ChatValidationError('escribe un mensaje', 'message is required')
    msg = msg.strip()
    if len(msg) > MAX_MESSAGE:
        raise ChatValidationError(f'mensaje demasiado largo (máx. {MAX_MESSAGE} caracteres)',
                                  f'message too long (max {MAX_MESSAGE} characters)')
    hist_raw = body.get('history') or []
    if not isinstance(hist_raw, list):
        raise ChatValidationError('historial inválido', 'invalid history')
    history = []
    for h in hist_raw[-(MAX_HISTORY * 4):]:
        if not isinstance(h, dict):
            continue
        content = h.get('content', h.get('text'))
        if not isinstance(content, str) or not content.strip():
            continue
        role = 'user' if str(h.get('role') or '').lower() == 'user' else 'assistant'
        history.append({'role': role, 'content': _clip(content, MAX_HISTORY_ITEM)})
    history = history[-MAX_HISTORY:]
    lang = str(body.get('lang') or '').lower()[:2]
    if lang not in ('es', 'en'):
        lang = _guess_lang(msg)
    ctx_raw = body.get('context') if isinstance(body.get('context'), dict) else {}
    ctx = {}
    sel = ctx_raw.get('selected_node')
    if sel:
        nid = resolve_node(str(sel)[:120])
        if nid:
            ctx['selected_node'] = {'id': nid, 'label': _node_label(nid),
                                    'symbol': (_snapshot()['nodes'].get(nid) or {}).get('mkt')}
    tab = str(ctx_raw.get('tab') or '').strip().lower()[:20]
    if tab:
        ctx['tab'] = tab if re.fullmatch(r'[a-z_]{2,20}', tab) else None
    ow = ctx_raw.get('open_windows')
    if isinstance(ow, list):
        ctx['open_windows'] = [re.sub(r'[^\w .:·()\-/+&]', '', str(w))[:60] for w in ow[:8] if str(w).strip()]
    re_ = ctx_raw.get('recent_entities')
    if isinstance(re_, list):
        ids = []
        for x in re_[:5]:
            nid = resolve_node(x)
            if nid and nid not in ids:
                ids.append(nid)
        if ids:
            ctx['recent_entities'] = ids
    pf = ctx_raw.get('portfolio')
    if isinstance(pf, dict) and isinstance(pf.get('positions'), list):
        pos = []
        for p in pf['positions'][:30]:
            if not isinstance(p, dict):
                continue
            sym = re.sub(r'[^A-Za-z0-9.\-^=/]', '', str(p.get('symbol') or ''))[:15].upper()
            try:
                sh = float(p.get('shares'))
            except (TypeError, ValueError):
                continue
            if sym and sh > 0:
                pos.append({'symbol': sym, 'shares': sh})
        if pos:
            ctx['portfolio'] = pos
    # Khipus OS: preferencias de PRESENTACIÓN del usuario (kh_agent_prefs). Solo cambian el prompt
    # (tono y qué herramientas priorizar); nunca decisiones del comité ni órdenes.
    mode = str(ctx_raw.get('mode') or body.get('mode') or '').strip().lower()
    ctx['mode'] = 'pro' if mode == 'pro' else 'simple'
    ae = ctx_raw.get('agents_enabled', body.get('agents_enabled'))
    if isinstance(ae, list):
        want = {str(x).strip().lower() for x in ae[:12] if isinstance(x, str)}
        ctx['agents_enabled'] = [a for a in AGENT_IDS if a == 'khipu' or a in want]
    else:
        ctx['agents_enabled'] = list(AGENT_IDS)
    return {'message': msg, 'history': history, 'lang': lang, 'context': ctx,
            'req_id': valid_req_id(body.get('req_id'))}


# ════════════════════════════════════════════════════════════════════════════
# prompt
# ════════════════════════════════════════════════════════════════════════════
_MODE_RULES = {
    'simple': ('MODO SIMPLE (lo eligió el usuario: no es experto): lenguaje llano y frases cortas, sin jerga ni siglas '
               'sueltas. La primera vez que uses un término financiero (capitalización, margen, VaR, NRS, convicción, '
               'volatilidad…) defínelo en pocas palabras entre paréntesis. Si es un análisis (no un saludo ni un dato '
               'suelto), termina con UNA conclusión clara, en una sola línea que empiece con «En resumen:» («In '
               'short:» si respondes en inglés).'),
    'pro': ('MODO PRO (lo eligió el usuario: inversionista experto): denso y cuantitativo, sin definir términos básicos. '
            'Da las cifras clave con fuente y fecha, rangos cuando los datos los traigan (mín.–máx. de 52 semanas, '
            'escenarios, por horizonte), el horizonte de cada idea (corto / mediano / largo plazo) y los riesgos '
            'cuantificados (exposición %, concentración, volatilidad, VaR) SOLO con datos de las herramientas: nunca '
            'inventes un rango, una probabilidad ni un precio objetivo.'),
}


def _agents_rule(agents_enabled):
    """Línea del prompt con las herramientas de los agentes activos / desactivados (None = todos activos)."""
    if not isinstance(agents_enabled, (list, tuple)):
        return ''
    on = {a for a in agents_enabled if a in AGENT_IDS} | {'khipu'}
    off = [a for a in AGENT_IDS if a not in on]
    if not off:
        return ''
    avail = set(tool_names()) | {'ask_agent'}

    def tools_of(a):
        ts = [t for t, ag in TOOL_AGENT.items() if ag == a and t in avail]
        if a != 'khipu' and 'ask_agent' in avail:
            ts.append('ask_agent(seat de ' + ('/'.join(s for s, x in SEAT_AGENT.items()
                                                       if x == a and s in ('fundamental', 'macro', 'news',
                                                                           'geopolitical', 'crypto', 'supply_chain',
                                                                           'technical', 'all'))) + ')')
        return ', '.join(ts)
    act = '; '.join(f'{AGENT_LABEL[a][0]} → {tools_of(a)}' for a in AGENT_IDS if a in on and a != 'khipu' and tools_of(a))
    des = '; '.join(f'{AGENT_LABEL[a][0]} → {tools_of(a)}' for a in off if tools_of(a))
    return ('AGENTES DEL USUARIO: ' + (f'activos: {act}. Prioriza las herramientas de los agentes activos. ' if act else '')
            + (f'DESACTIVADOS por el usuario: {des}. Evita sus herramientas salvo que sean estrictamente necesarias '
               'para responder lo que pregunta.' if des else ''))


def build_system(lang, mode=None, agents_enabled=None):
    """mode: 'simple' | 'pro' | None (llamadas internas: sin regla de modo). agents_enabled: ids de
    mascotas activas (None = todas). Ambos vienen de las preferencias del usuario (kh_agent_prefs)."""
    tools = '\n'.join(f'- {n}({sig}): {desc}' for n, sig, desc in tool_catalog())
    idioma = 'inglés' if lang == 'en' else 'español'
    publico = ('Hablas con un inversionista EXPERTO: preciso, denso y concreto' if mode == 'pro'
               else 'Hablas con inversionistas NO expertos: claro, corto y concreto')
    extra = '\n\n'.join(x for x in (_MODE_RULES.get(mode, ''), _agents_rule(agents_enabled)) if x)
    extra = ('\n\n' + extra) if extra else ''
    return f"""Eres Khipu, el asistente de inversión de Khipus Finance Intelligence (terminal sobre la cadena de suministro de la \
IA: ~950 empresas y sus relaciones proveedor → cliente, precios en vivo, investigación de analistas, comité). \
{publico}, en {idioma} (o el idioma del usuario).

PROTOCOLO: responde SIEMPRE con UN SOLO objeto JSON válido, sin texto fuera:
  a) consultar: {{"tool":"<nombre>","args":{{...}},"why":"<1 frase>"}}  o varias a la vez (máx. {MAX_CALLS_PER_STEP}): \
{{"calls":[{{"tool":"...","args":{{...}}}}],"why":"..."}}
  b) responder: {{"final":{{"answer":"<respuesta>","actions":[{{"type":"...","arg":...}}]}}}}
Hasta {MAX_STEPS} rondas de consulta; lo normal es UNA.

RECETAS (una ronda): "¿cómo va X?" / "¿qué pasa con X?" → get_company(include_live=true) + get_news juntas. \
"precio / capitalización de X" → get_company. "proveedores / clientes de X" → get_supply_chain. \
"qué piensan los analistas / qué dice el comité" → get_conclusions_board o get_research (sobre UNA empresa, \
también get_committee_memo). "@analista / pregúntale \
al analista" → ask_agent. "¿puedo investigar ahora? / ¿por qué falló o quedó a medias la investigación?" → \
get_research_health (proveedores en pausa, cola, presupuesto); en get_research, last_job.status 'partial' = síntesis \
incompleta (lee coverage.note_es) y 'deferred' = sin presupuesto, se reanuda mañana. "qué pasa si… / quién pierde si…" → scenario_exposure. "más expuestas / mejores / \
peores" → rank_companies o market_movers. Preguntas conceptuales (qué es el VaR, cómo funciona HBM) → sin \
herramientas. get_company ya entiende nombres y tickers: NO gastes una ronda en search_companies salvo \
ambigüedad real.

RESPUESTA: primero la respuesta directa a lo preguntado (1-2 frases), luego el porqué (3-6 líneas, máx. una \
lista). Cada cifra con su fuente y fecha en la misma frase, p. ej. «233,95 USD (Yahoo, hoy)». Nunca inventes \
cifras ni datos: si no están, dilo. Usa el historial y lo que hay EN PANTALLA para resolver "ella / su / este". \
Markdown ligero. Sin recomendaciones personalizadas de comprar/vender (sí riesgos, pros, contras, escenarios); \
si piden operar, explica que la orden se prepara y confirma en el bróker de la app y ofrece la acción "broker". \
Acciones de pantalla solo si ayudan (máx. 2) y sin anunciarlas. No menciones el protocolo ni nombres internos.{extra}

HERRAMIENTAS:
{tools}
Usa ids de empresa de los resultados (o el nombre exacto)."""


_CHAT_DROP_KEYS = {'edge_semantics', 'explain', 'figures_note', 'figures_note_es', 'as_of_note', 'provenance_note',
                   'provenance_note_es', 'valid_from_note_es', 'valid_from_note_en', 'convention'}
# niveles de compactación: (largo máx. de texto, tope de listas, tope de `related`)
_CHAT_LEVELS = ((220, None, None), (140, 25, 8), (100, 12, 6))


def _balance_edges(edges, root):
    """Proveedores y clientes INTERCALADOS: al recortar, el chat ve de los dos lados."""
    up = [e for e in edges if isinstance(e, dict) and e.get('target') == root]
    down = [e for e in edges if isinstance(e, dict) and e.get('source') == root]
    rest = [e for e in edges if not (isinstance(e, dict) and root in (e.get('source'), e.get('target')))]
    out = []
    for k in range(max(len(up), len(down))):
        if k < len(up):
            out.append(up[k])
        if k < len(down):
            out.append(down[k])
    return out + rest


def _compact_for_chat(v, level=0, depth=0, root=None):
    """Revisión G4/G6b: get_company/get_supply_chain crecieron (clase, confianza,
    `related`, notas). Cortar el JSON a ciegas a MAX_TOOL_RESULT_CHARS dejaba al
    cerebro sin clientes. Se compacta por NIVELES (solo lo necesario): primero se
    quitan notas largas y valores por defecto; si no alcanza, se acortan textos y
    listas — las aristas, intercalando proveedores y clientes."""
    maxs, maxl, maxrel = _CHAT_LEVELS[level]
    if isinstance(v, dict):
        root = v.get('root', root) if depth == 0 else root
        out = {}
        for k, x in v.items():
            if k in _CHAT_DROP_KEYS:
                continue
            if k == 'verified' and x is True:
                continue
            if k == 'confidence' and isinstance(x, (int, float)) and x >= 1:
                continue
            if k == 'edges' and isinstance(x, list) and root:
                x = _balance_edges(x, root)
            out[k] = _compact_for_chat(x, level, depth + 1, root)
        if depth == 0 and isinstance(v.get('related'), list) and maxrel:
            rel = v['related']                          # lo menos importante: al final, acotado sobre la lista ORIGINAL
            out.pop('related', None)
            out['related'] = [_compact_for_chat(x, level, depth + 1, root) for x in rel[:maxrel]] + (
                [f'…+{len(rel) - maxrel}'] if len(rel) > maxrel else [])
        return out
    if isinstance(v, list):
        if maxl and len(v) > maxl:
            return [_compact_for_chat(x, level, depth + 1, root) for x in v[:maxl]] + [f'…+{len(v) - maxl}']
        return [_compact_for_chat(x, level, depth + 1, root) for x in v]
    if isinstance(v, str) and len(v) > maxs:
        return v[:maxs] + '…'
    return v


def _fmt_result(res):
    txt = json.dumps(res, ensure_ascii=False, default=str, separators=(',', ':'))
    level = 0
    while len(txt) > MAX_TOOL_RESULT_CHARS and level < len(_CHAT_LEVELS):
        txt = json.dumps(_compact_for_chat(res, level), ensure_ascii=False, default=str, separators=(',', ':'))
        level += 1
    if len(txt) > MAX_TOOL_RESULT_CHARS:
        txt = txt[:MAX_TOOL_RESULT_CHARS] + '…[truncated]'
    return txt


def _args_summary(args):
    if not isinstance(args, dict) or not args:
        return ''
    vals = []
    for v in args.values():
        if isinstance(v, bool) or v is None:
            continue
        if isinstance(v, (list, dict)):
            v = f'{len(v)} items' if isinstance(v, list) else '{…}'
        vals.append(str(v))
    return _clip(', '.join(vals), 80)


def build_prompt(message, history, lang, context, scratch, rounds_left, force_final, feedback=None, live=''):
    """Orden (2026-10-04): contexto → historial → resultados → PREGUNTA ACTUAL al FINAL → formato.
    Los modelos pesan el final del prompt: antes la pregunta quedaba a 20-30k caracteres de
    distancia y Khipu "respondía otra cosa"."""
    parts = []
    ctx = [f'fecha actual (UTC): {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")}',
           f'idioma de la interfaz: {lang}']
    if context.get('tab'):
        ctx.append(f'pestaña abierta: {context["tab"]}')
    sel = context.get('selected_node')
    if sel:
        ctx.append(f'empresa seleccionada en pantalla: {sel["label"]} (id {sel["id"]}'
                   + (f', ticker {sel["symbol"]}' if sel.get('symbol') else '') + ')')
    if context.get('open_windows'):
        ctx.append('EN PANTALLA AHORA (ventanas abiertas): ' + ' · '.join(context['open_windows']))
    if context.get('recent_entities'):
        ctx.append('empresas vistas hace poco (de más reciente a más antigua): ' +
                   ', '.join(f'{_node_label(i)} (id {i})' for i in context['recent_entities']))
    if context.get('portfolio'):
        ctx.append('cartera del usuario (posiciones locales, acciones): ' +
                   ', '.join(f'{p["symbol"]} {p["shares"]:g}' for p in context['portfolio']))
    if context.get('portfolio_notes'):
        # "Pregúntale a tu cartera" (core/portfolio_reports_api): reporte y consejos YA calculados
        ctx.append('INFORME DE LA CARTERA DEL USUARIO (datos verificados; úsalos para responder sobre SU cartera):\n'
                   + str(context['portfolio_notes'])[:3500])
    parts.append('CONTEXTO DE LA APP:\n- ' + '\n- '.join(ctx))
    if history:
        parts.append('CONVERSACIÓN PREVIA (antigua → reciente):\n' + '\n'.join(
            f'{"Usuario" if h["role"] == "user" else "Khipu"}: {h["content"]}' for h in history))
    if live:
        parts.append(live.strip())
    if scratch:
        body, used = [], 0
        for i, s_ in enumerate(scratch, 1):
            line = f'[{i}] {s_}'
            used += len(line)
            body.append(line)
        txt = '\n'.join(body)
        if used > MAX_SCRATCH_CHARS:
            txt = '…[resultados antiguos recortados]\n' + txt[-MAX_SCRATCH_CHARS:]
        parts.append('RESULTADOS DE HERRAMIENTAS (de esta respuesta):\n' + txt)
    ents = _entities_in(message)
    q = f'PREGUNTA ACTUAL DEL USUARIO (responde EXACTAMENTE esto): {message}'
    if ents:
        q += '\nEMPRESAS DETECTADAS EN LA PREGUNTA: ' + ', '.join(f'{_node_label(i)} (id {i})' for i in ents[:3])
    parts.append(q)
    if feedback:
        parts.append('AVISO: ' + feedback)
    if force_final:
        parts.append('No quedan rondas de herramientas: responde AHORA con {"final":{"answer":"...","actions":[]}} '
                     'usando lo que ya tienes (si falta un dato, dilo).')
    else:
        parts.append(f'Te quedan {rounds_left} rondas de herramientas. Responde SOLO con el objeto JSON.')
    return '\n\n'.join(parts)


# ════════════════════════════════════════════════════════════════════════════
# parseo de cada paso
# ════════════════════════════════════════════════════════════════════════════
class StepParseError(ValueError):
    pass


def _json_objects(text):
    """Todos los objetos JSON BALANCEADOS del texto (respetando strings), en orden.
    Los modelos a veces "piensan en voz alta" antes/después del JSON o escriben
    varios borradores: nos quedamos con el último que cumpla el protocolo."""
    t = str(text or '')
    out, i, n = [], 0, len(t)
    while i < n:
        if t[i] != '{':
            i += 1
            continue
        depth, j, in_str, esc_ = 0, i, False, False
        while j < n:
            ch = t[j]
            if in_str:
                if esc_:
                    esc_ = False
                elif ch == '\\':
                    esc_ = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    try:
                        out.append(json.loads(t[i:j + 1]))
                    except ValueError:
                        pass
                    break
            j += 1
        i = j + 1 if j > i else i + 1
    return out


def parse_step(text):
    """→ ('final', {'answer','actions'}) | ('tools', [{'tool','args'}]). Lanza StepParseError."""
    try:
        data = _ai._extract_json(text)
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        data = None
        err = e
    if not (isinstance(data, dict) and ('final' in data or 'tool' in data or 'calls' in data or data.get('answer'))):
        cands = [o for o in _json_objects(text) if isinstance(o, dict)
                 and ('final' in o or 'tool' in o or 'calls' in o or o.get('answer'))]
        if cands:
            data = cands[-1]
        elif data is None:
            raise StepParseError(f'not valid JSON ({type(err).__name__})') from None
    if isinstance(data, list) and data and all(isinstance(x, dict) and x.get('tool') for x in data):
        data = {'calls': data}
    if not isinstance(data, dict):
        raise StepParseError('the JSON must be an object')
    if 'final' in data:
        f = data['final']
        if isinstance(f, str):
            f = {'answer': f}
        if not isinstance(f, dict) or not str(f.get('answer') or '').strip():
            raise StepParseError('"final" must contain a non-empty "answer"')
        if 'actions' not in f and 'actions' in data:
            f['actions'] = data['actions']
        return 'final', f
    if 'calls' in data or 'tool' in data:
        calls = data.get('calls') if isinstance(data.get('calls'), list) else [data]
        out = []
        for c in calls[:MAX_CALLS_PER_STEP]:
            if isinstance(c, dict) and isinstance(c.get('tool'), str) and c['tool'].strip():
                a = c.get('args', c.get('arguments'))
                out.append({'tool': c['tool'].strip(), 'args': a if isinstance(a, dict) else {}})
        if not out:
            raise StepParseError('"tool" must be a tool name')
        return 'tools', out
    if str(data.get('answer') or '').strip():
        return 'final', data
    raise StepParseError('expected {"tool":...} or {"final":{"answer":...}}')


# restos del protocolo JSON o "pensamiento en voz alta" al INICIO de una línea
_LEAK_RX = re.compile(r'"(actions|final|tool|calls|args)"\s*:|```|^\s*[{}\[\]]\s*,?\s*$|'
                      r'^\s*(Wait|Hmm+|Let me|Okay,? so|Actually,|I need to|I should|Espera,|Mmm)\b', re.I | re.M)


def truncated(text):
    """¿La respuesta quedó cortada? (negritas sin cerrar, paréntesis abiertos o
    termina a mitad de palabra sin puntuación)."""
    t = str(text or '').rstrip()
    if len(t) < 15:
        return False
    if t.count('**') % 2 or t.count('(') > t.count(')'):
        return True
    last = t.splitlines()[-1].strip()
    if re.match(r'^(_?\*?)(fuentes?|sources?|fuente de datos)\b', last, re.I) or re.match(r'^[-•*]\s', last):
        return False                      # línea de fuentes o ítem de lista: puede terminar sin punto
    # una ORACIÓN larga que termina a mitad (sin puntuación final) = cortada
    return len(last) > 60 and bool(re.search(r'[A-Za-zÁÉÍÓÚáéíóúñÑ0-9,]$', last))


def leaked(text):
    """¿El texto trae restos del protocolo o del "pensamiento en voz alta" del modelo?"""
    return bool(_LEAK_RX.search(str(text or '')))


def _prose_answer(text):
    """Si el modelo respondió en prosa LIMPIA (no JSON ni borradores), úsala como respuesta."""
    t = re.sub(r'^```\w*\s*|\s*```$', '', str(text or '').strip()).strip()
    if len(t) < 2 or t.startswith('{') or t.startswith('[') or leaked(t):
        return None
    return t


SYNTH_SYSTEM = (
    'Eres Khipu, analista senior de Khipus Finance Intelligence. Te doy la PREGUNTA del usuario y los DATOS que ya '
    'consultaste con las herramientas de la app. Escribe AHORA la respuesta final, analizando la pregunta '
    'CONCRETA (no otra cosa): primero la respuesta directa en 1-2 frases, luego el porqué con los datos '
    '(nombra empresas, cifras y relaciones que aparecen en los datos), y una línea de fuentes al final. '
    'Si un dato no está, dilo. Prosa clara en markdown ligero, 80-250 palabras. PROHIBIDO: JSON, código, '
    'llaves, pensar en voz alta, mencionar herramientas o el protocolo. No des órdenes de compra/venta.')


def synthesize(message, history, lang, context, scratch, timeout):
    """El AGENTE redacta la respuesta final en prosa a partir de lo consultado
    (cuando el paso con protocolo JSON falló o se acabó el tiempo de rondas)."""
    parts = [f'PREGUNTA: {message}']
    if history:
        parts.append('CONVERSACIÓN PREVIA:\n' + '\n'.join(
            f'{"Usuario" if h["role"] == "user" else "Khipu"}: {h["content"]}' for h in history[-6:]))
    if context.get('portfolio_notes'):
        parts.append('INFORME DE LA CARTERA:\n' + str(context['portfolio_notes'])[:3000])
    if scratch:
        parts.append('DATOS CONSULTADOS:\n' + '\n'.join(scratch)[-MAX_SCRATCH_CHARS:])
    parts.append(f'Responde en {"inglés" if lang == "en" else "español"}.')
    t0 = time.monotonic()
    fut = _submit_ai(_ai._ai_complete, SYNTH_SYSTEM, '\n\n'.join(parts), 2200, 'fast',
                     timeout_s=max(5.0, min(float(timeout), 30.0)))
    text, model = fut.result(timeout=max(1.0, timeout))
    t = re.sub(r'^```\w*\s*|\s*```$', '', str(text or '').strip()).strip()
    left = timeout - (time.monotonic() - t0)
    if (leaked(t) or truncated(t)) and left > 8:          # un reintento con el aviso concreto
        fb = ('\n\nTU RESPUESTA ANTERIOR ' + ('QUEDÓ CORTADA' if truncated(t) else 'TENÍA JSON O BORRADORES') +
              '. Escríbela COMPLETA, más corta (máx. 180 palabras), en prosa limpia.')
        fut = _submit_ai(_ai._ai_complete, SYNTH_SYSTEM, '\n\n'.join(parts) + fb, 2200, 'fast',
                         timeout_s=max(5.0, min(float(left), 30.0)))
        text2, model2 = fut.result(timeout=max(1.0, left))
        t2 = re.sub(r'^```\w*\s*|\s*```$', '', str(text2 or '').strip()).strip()
        if t2 and not leaked(t2) and not truncated(t2):
            return t2, model2
    # última defensa: quitar líneas con restos de protocolo/borrador
    if leaked(t):
        t = '\n'.join(ln for ln in t.splitlines() if not _LEAK_RX.search(ln)).strip()
    return (t or None), model


# ════════════════════════════════════════════════════════════════════════════
# respuesta determinista (sin IA)
# ════════════════════════════════════════════════════════════════════════════
_REASON = {
    'no_ai': ('No hay ninguna IA configurada en el servidor ahora mismo, así que te respondo solo con datos.',
              'No AI provider is configured on the server right now, so I am answering with data only.'),
    'busy': ('La IA está ocupada con otras consultas; te respondo con los datos que tengo. Reintenta en unos '
             'segundos para una respuesta completa.',
             'The AI is busy with other requests; here is what the data says. Retry in a few seconds for a full '
             'answer.'),
    'ai_error': ('Los proveedores de IA no respondieron; te respondo solo con datos.',
                 'The AI providers did not answer; I am answering with data only.'),
    'budget': ('Se me acabó el tiempo para razonar la respuesta completa; esto es lo que reuní.',
               'I ran out of time to reason a full answer; this is what I gathered.'),
    'bad_output': ('No pude interpretar la respuesta de la IA; esto es lo que reuní.',
                   'I could not interpret the AI output; this is what I gathered.'),
}


def _num(v, nd=2):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f'{f:,.{nd}f}'


def company_summary(c, lang):
    en = lang == 'en'
    cat = dict(c.get('catalog') or {})
    if not en:   # el catálogo MCP prioriza el inglés; en español, los textos originales
        try:
            n = _snapshot()['nodes'].get(c.get('id')) or {}
            cat['role'] = n.get('role') or cat.get('role')
            cat['moat_and_risks'] = n.get('moat') or cat.get('moat_and_risks')
        except Exception:  # noqa: BLE001
            pass
    head = f'**{c.get("label")}**' + (f' ({c["symbol"]})' if c.get('symbol') else '')
    lines = [head + (f' — {_clip(cat.get("role"), 220)}' if cat.get('role') else '')]
    lm = c.get('live_market') or {}
    if lm.get('available'):
        bits = []
        if lm.get('price') is not None:
            chg = lm.get('change_pct')
            bits.append((('Price' if en else 'Precio') + f': {_num(lm["price"])} {lm.get("currency") or ""}').strip()
                        + (_chg_label(f'{"+" if (chg or 0) >= 0 else ""}{_num(chg)} %', lm, not en)
                           if chg is not None else ''))
        if lm.get('market_cap_usd_b') is not None:
            bits.append(('Market cap' if en else 'Capitalización') + f': {_num(lm["market_cap_usd_b"], 1)} ' +
                        ('billion USD' if en else 'mil millones USD'))
        if bits:
            lines.append('- ' + ' · '.join(bits) + f' ({lm.get("source") or "live"})')
    elif c.get('private_valuation'):
        pv = c['private_valuation']
        if pv.get('valuation_usd_b') is not None:
            lines.append('- ' + ('Last verified valuation' if en else 'Última valuación verificada') +
                         f': {_num(pv["valuation_usd_b"], 1)} ' + ('billion USD' if en else 'mil millones USD') +
                         (f' ({pv.get("as_of")})' if pv.get('as_of') else '') +
                         (' — not a live price' if en else ' — no es un precio en vivo'))
    nrs = (c.get('network_risk_score') or {}).get('value')
    if nrs is not None:
        lines.append('- ' + ('Network Risk Score' if en else 'Índice de riesgo NRS') + f': {nrs}/100 ' +
                     ('(higher = more fragile)' if en else '(más alto = más frágil)'))
    sup = [s.get('label') for s in (c.get('top_suppliers') or [])[:5] if s.get('label')]
    cus = [s.get('label') for s in (c.get('top_customers') or [])[:5] if s.get('label')]
    if sup:
        lines.append('- ' + ('Key suppliers' if en else 'Proveedores clave') + ': ' + ', '.join(sup))
    if cus:
        lines.append('- ' + ('Key customers' if en else 'Clientes clave') + ': ' + ', '.join(cus))
    if cat.get('moat_and_risks'):
        lines.append('- ' + ('Moat & risks' if en else 'Foso y riesgos') + ': ' + _clip(cat['moat_and_risks'], 240))
    return '\n'.join(lines)


def _entities_in(message):
    ids = []
    try:
        from core.live_facts import detect_entities
        ids = detect_entities(message, limit=3)
    except Exception:  # noqa: BLE001
        ids = []
    if not ids:
        short = re.sub(r'[¿?¡!.,]', ' ', message).strip()
        if 0 < len(short) <= 40:
            nid = resolve_node(short)
            if nid:
                ids = [nid]
    return ids


def fallback_answer(message, lang, reason, results, deadline, app=None, req_id=None):
    """Respuesta SIN IA con datos reales. → (answer, actions, extra_results)."""
    en = lang == 'en'
    head = _REASON.get(reason, _REASON['ai_error'])[1 if en else 0]
    companies = [r for (name, ok, r) in results if ok and name == 'get_company']
    extra = []
    if not companies:
        for nid in _entities_in(message)[:2]:
            if time.monotonic() > deadline - 2:
                break
            h = progress_add(req_id, 'get_company')
            fut = _POOL.submit(execute_tool, 'get_company', {'id_or_ticker': nid}, app, lang)
            try:
                ok, res = fut.result(timeout=max(1.0, min(14.0, deadline - time.monotonic())))
            except _FutTimeout:
                ok, res = False, {'error': 'timeout'}
            progress_set(req_id, h, 'done' if ok else 'error')
            extra.append(('get_company', {'id_or_ticker': nid}, ok, res))
            if ok:
                companies.append(res)
    actions = []
    if companies:
        body = '\n\n'.join(company_summary(c, lang) for c in companies[:2])
        actions = validate_actions([{'type': 'open_xray', 'arg': companies[0].get('id')}])
        tail = ('Source: Khipus graph · live market profile.' if en
                else 'Fuente: grafo Khipus · perfil de mercado en vivo.')
        return f'{head}\n\n{body}\n\n{tail}', actions, extra
    other = [(name, r) for (name, ok, r) in results if ok]
    if other:
        name, r = other[-1]
        items = r.get('items') or r.get('results') or []
        if isinstance(items, list) and items:
            lst = []
            for it in items[:8]:
                if isinstance(it, dict):
                    lbl = it.get('label') or it.get('title') or it.get('id')
                    extra_bits = [f'{k}: {it[k]}' for k in ('change_pct', 'nrs', 'degree', 'severity') if
                                  it.get(k) is not None]
                    lst.append(f'- {lbl}' + (f' ({", ".join(extra_bits)})' if extra_bits else ''))
            if lst:
                return head + '\n\n' + '\n'.join(lst) + f'\n\n{"Source" if en else "Fuente"}: {r.get("source") or name}', [], extra
    tip = ('You can still use exact commands without AI, e.g. **NVDA XRAY**, **COMPARE NVDA AMD**, '
           '**SHOCK TSMC**, or write just a company name to open its X-Ray.' if en else
           'Igual puedes usar comandos exactos sin IA, por ejemplo **NVDA XRAY**, **COMPARE NVDA AMD**, '
           '**SHOCK TSMC**, o escribir solo el nombre de una empresa para abrir su radiografía.')
    return f'{head}\n\n{tip}', [], extra


# ════════════════════════════════════════════════════════════════════════════
# el bucle del agente
# ════════════════════════════════════════════════════════════════════════════
def _friendly_source(label, lang):
    low = str(label or '').lower()
    if 'grafo_v0' in low or 'curated catalog' in low or 'graph snapshot' in low:
        return 'Grafo Khipus (catálogo curado)' if lang == 'es' else 'Khipus graph (curated catalog)'
    return label


def _collect_sources(tool_name, res, into, lang='es'):
    """sources[] = {label, url, tool, as_of[, published]}. as_of = cuándo el SERVIDOR obtuvo el dato
    (Khipus OS: el cliente muestra la hora junto a cada fuente); published = fecha de la nota/ronda."""
    def add(label, url=None, as_of=None, published=None):
        label = _clip(_friendly_source(label, lang), 120)
        if not label or any(s['label'] == label and s.get('url') == url for s in into):
            return
        if len(into) < 10:
            item = {'label': label, 'url': url, 'tool': tool_name, 'as_of': as_of}
            if published:
                item['published'] = str(published)[:40]
            into.append(item)
    if not isinstance(res, dict):
        return
    res_as_of = res.get('as_of') if isinstance(res.get('as_of'), str) else None
    if isinstance(res.get('source'), str):
        add(res['source'], as_of=res_as_of)
    elif tool_name == 'get_company':
        # el catálogo curado: su fecha es la de EXPORTACIÓN del grafo (no la de sus cifras)
        add('curated catalog', as_of=(res.get('catalog') or {}).get('as_of') or res_as_of)
    for it in (res.get('items') or res.get('results') or [])[:4] if tool_name in ('get_news', 'web_search') else []:
        if isinstance(it, dict) and it.get('url'):
            add(it.get('outlet') or it.get('title') or it['url'], it['url'], as_of=res_as_of,
                published=it.get('date') or it.get('published'))
    lm = res.get('live_market')
    if isinstance(lm, dict) and lm.get('available') and lm.get('source'):
        add(f'{lm["source"]} (live)', as_of=_price_time(lm, res_as_of))
    pv = res.get('private_valuation')
    if isinstance(pv, dict) and pv.get('source_url'):
        add('verified funding round', pv['source_url'], as_of=res_as_of, published=pv.get('as_of'))


_SRC_NAMES = {'yahoo': 'Yahoo Finance', 'finnhub': 'Finnhub', 'marketstack': 'Marketstack', 'fmp': 'FMP',
              'alphavantage': 'Alpha Vantage', 'av': 'Alpha Vantage'}


def _src_name(src):
    s = str(src or '').strip()
    return _SRC_NAMES.get(s.lower(), s)


# ════════════════════════════════════════════════════════════════════════════
# KHIPUS OS: qué aportó cada agente (agents_used), tarjetas (cards) y empresas
# (entities). TODO DETERMINISTA: solo valores que ESTÁN en los resultados de las
# herramientas de esta respuesta (nunca texto del modelo, nunca cifras nuevas).
# ════════════════════════════════════════════════════════════════════════════
_RISK_Q_RX = re.compile(r'riesg|risk|proveed|supplier|cadena|chain|depend|expos|vulnerab|fr[aá]gil|fragil|cuello|'
                        r'bottleneck|chokepoint|suministr|supply|reemplaz|sustitu|substitut', re.I)
_AGENT_ORDER = ('analista', 'radar', 'cadena', 'tecnico', 'comite', 'khipu')
_NOTE_MAX = 220


def _fmt_num(v, nd=1, lang='es', sign=False):
    """1234.5 → '1.234,5' (es) / '1,234.5' (en). None si no es un número finito."""
    if isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float('inf'), float('-inf')):
        return None
    s = f'{f:+,.{nd}f}' if sign else f'{f:,.{nd}f}'
    if lang == 'es':
        s = s.replace(',', '\x00').replace('.', ',').replace('\x00', '.')
    return s


def _pct(v, lang, nd=1, sign=False):
    s = _fmt_num(v, nd, lang, sign)
    return None if s is None else (f'{s} %' if lang == 'es' else f'{s}%')


def _usd_b(v, lang):
    """Miles de millones de USD → '4.470 mil millones USD' / '$4,470B' (menos de 1: en millones)."""
    if isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:
        return None
    if abs(f) < 1:
        s = _fmt_num(f * 1000, 0, lang)
        return f'{s} millones USD' if lang == 'es' else f'${s}M'
    s = _fmt_num(f, 0 if abs(f) >= 100 else 1, lang)
    return f'{s} mil millones USD' if lang == 'es' else f'${s}B'


def _price(v, lang):
    """Precio con los decimales que hacen falta (centavos; 4 decimales por debajo de 1)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return _fmt_num(f, 2 if abs(f) >= 1 else 4, lang)


def _quote(t, lang):
    t = _clip(t, 110)
    return f'«{t}»' if lang == 'es' else f'"{t}"'


def _decision_labels(decision):
    try:
        from research.committee import DECISION_LABEL
        return DECISION_LABEL.get(decision, (decision, decision))
    except Exception:  # noqa: BLE001
        return (decision, decision)


_RISK_SRC_RX = re.compile(r'^(.*?)\s+(-?\d+(?:\.\d+)?)%(\s*\(indirect\))?\s*$')


def _risk_sources(structure):
    """structure.risk_sources ('TSMC 61.1%', 'PDF Solutions 6.2% (indirect)') → [(label, pct, indirecta)]."""
    out = []
    for s in (structure or {}).get('risk_sources') or []:
        m = _RISK_SRC_RX.match(str(s or ''))
        if m:
            out.append((m.group(1).strip(), float(m.group(2)), bool(m.group(3))))
    return out


SESSION_FRESH_S = 1800          # sin estado del mercado: precio de hace ≤ 30 min = sesión en curso


def _iso_time(v):
    """market_time (ISO, unix o {raw}) → ISO UTC 'YYYY-MM-DDTHH:MM:SSZ', o None."""
    if isinstance(v, dict):
        v = v.get('raw')
    if isinstance(v, bool) or v is None or v == '':
        return None
    if isinstance(v, (int, float)):
        try:
            return datetime.fromtimestamp(float(v), timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        except (OverflowError, OSError, ValueError):
            return None
    return str(v)[:40]


def _session_live(state, market_time, now=None):
    """¿La variación es de la sesión EN CURSO? True / False, o None si la fuente no lo dice.
    market_state de Yahoo: solo REGULAR es la sesión abierta (PRE/POST/CLOSED → la variación es
    la de la ÚLTIMA sesión vs. su cierre anterior). Sin estado se mira la hora real del precio."""
    st = str(state or '').strip().upper()
    if st:
        return st == 'REGULAR'
    mt = _iso_time(market_time)
    if not mt:
        return None
    try:
        t = datetime.fromisoformat(mt.replace('Z', '+00:00'))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return ((now or datetime.now(timezone.utc)) - t).total_seconds() <= SESSION_FRESH_S


def _chg_label(chg, lm, es):
    """' (+1,23 % hoy)' solo con la sesión abierta; si no, ' (+1,23 % vs. cierre anterior, sesión del
    2026-10-02)' — antes el cierre del viernes se mostraba el domingo como «hoy»."""
    live = _session_live(lm.get('market_state'), lm.get('market_time'))
    if live:
        return f' ({chg} {"hoy" if es else "today"})'
    d = (_iso_time(lm.get('market_time')) or '')[:10]
    if es:
        return f' ({chg} vs. cierre anterior' + (f', sesión del {d}' if d else '') + ')'
    return f' ({chg} vs. prior close' + (f', session of {d}' if d else '') + ')'


def _price_time(lm, fallback=None):
    """Hora REAL del precio (market_time); as_of del perfil = cuándo el servidor lo consultó."""
    return _iso_time(lm.get('market_time')) or lm.get('as_of') or fallback


def _note_company(res, _args, ctx):
    lbl = res.get('label') or res.get('id')
    lm = res.get('live_market') if isinstance(res.get('live_market'), dict) else {}
    nrs = (res.get('network_risk_score') or {}).get('value') if isinstance(res.get('network_risk_score'), dict) else None
    live = bool(lm.get('available')) and lm.get('price') is not None

    def build(lang):
        es = lang == 'es'
        bits = []
        if live:
            s = f'{lbl}: {_price(lm["price"], lang)} {lm.get("currency") or ""}'.rstrip()
            chg = _pct(lm.get('change_pct'), lang, 2, True)
            if chg:
                s += _chg_label(chg, lm, es)
            bits.append(s)
            cap = _usd_b(lm.get('market_cap_usd_b'), lang)
            if cap:
                bits.append(('capitalización ' if es else 'market cap ') + cap)
        else:
            pv = res.get('private_valuation') if isinstance(res.get('private_valuation'), dict) else {}
            if pv.get('valuation_usd_b') is not None:
                d = f' ({pv["as_of"]})' if pv.get('as_of') else ''
                bits.append(f'{lbl}: ' + ('última valuación verificada ' if es else 'last verified valuation ')
                            + _usd_b(pv['valuation_usd_b'], lang) + d
                            + (' — no es un precio en vivo' if es else ' — not a live price'))
            elif res.get('listed') is False:
                bits.append(f'{lbl}: ' + ('no cotiza en bolsa' if es else 'not listed on an exchange'))
            else:
                bits.append(f'{lbl}: ' + ('sin precio en vivo ahora' if es else 'no live price right now'))
        if nrs is not None:
            bits.append(('riesgo de red NRS ' if es else 'network risk NRS ') + f'{nrs}/100')
        return ' · '.join(bits)
    if live:
        return build('es'), build('en'), _src_name(lm.get('source')) or 'live', _price_time(lm, res.get('as_of'))
    return build('es'), build('en'), 'Khipus graph', res.get('as_of')


def _note_structure(res, _args, ctx):
    """Cadena desde la ficha (get_company.structure: modelo de flujo del grafo)."""
    st = res.get('structure') if isinstance(res.get('structure'), dict) else None
    srcs = _risk_sources(st)
    if not srcs:
        return None
    top = srcs[:2]

    def build(lang):
        es = lang == 'es'
        parts = []
        for i, (lab, p, ind) in enumerate(top):
            pct = _pct(p, lang, 1)
            tag = ((' de exposición' if es else ' exposure') if i == 0 else '')
            parts.append(f'{lab} ({pct}{tag}' + ((', indirecta' if es else ', indirect') if ind else '') + ')')
        joined = (' y ' if es else ' and ').join(parts)
        return (f'Su mayor riesgo aguas arriba: {joined}' if es else f'Biggest upstream risk: {joined}')
    return build('es'), build('en'), 'Khipus flow model (graph)', res.get('as_of')


def _note_supply_chain(res, args, ctx):
    root = res.get('root')
    edges = [e for e in res.get('edges') or [] if isinstance(e, dict) and e.get('hop', 1) == 1]
    nodes = {n.get('id'): n.get('label') for n in res.get('nodes') or [] if isinstance(n, dict)}
    sups = [nodes.get(e['source']) or e['source'] for e in edges if e.get('target') == root][:3]
    cus = [nodes.get(e['target']) or e['target'] for e in edges if e.get('source') == root][:3]
    if not sups and not cus:
        return (f'{res.get("label") or root}: sin proveedores ni clientes de flujo en el grafo',
                f'{res.get("label") or root}: no flow suppliers or customers in the graph', 'Khipus graph',
                res.get('as_of'))

    def build(lang):
        es = lang == 'es'
        bits = []
        if sups:
            bits.append(('Proveedores clave: ' if es else 'Key suppliers: ') + ', '.join(sups))
        if cus:
            bits.append(('clientes clave: ' if es else 'key customers: ') + ', '.join(cus))
        return ' · '.join(bits)
    return build('es'), build('en'), 'Khipus graph', res.get('as_of')


def _note_rank(res, args, ctx):
    items = [x for x in res.get('items') or [] if isinstance(x, dict)][:3]
    if not items:
        return None
    risk = res.get('by') == 'risk'

    def build(lang):
        es = lang == 'es'
        names = ', '.join(f'{x.get("label")} ({x.get("nrs")})' if risk and x.get('nrs') is not None
                          else str(x.get('label')) for x in items)
        if risk:
            return ('Más frágiles por NRS: ' if es else 'Most fragile by NRS: ') + names
        return ('Más conectadas en la cadena: ' if es else 'Most connected in the chain: ') + names
    return build('es'), build('en'), 'Khipus graph', res.get('as_of')


def _note_news(res, args, ctx):
    items = [x for x in res.get('items') or [] if isinstance(x, dict) and x.get('title')]
    if not items:
        return None
    it = items[0]
    out = it.get('outlet')

    def build(lang):
        es = lang == 'es'
        return (('Última noticia: ' if es else 'Latest news: ') + _quote(it['title'], lang)
                + (f' ({out})' if out else ''))
    return build('es'), build('en'), res.get('source'), res.get('as_of')


def _note_world(res, args, ctx):
    items = [x for x in res.get('items') or [] if isinstance(x, dict) and x.get('title')]
    n = res.get('count_total')
    win = res.get('window') or '24h'
    if not items:
        return (f'Sin eventos relevantes en el mundo ({win})', f'No relevant world events ({win})',
                res.get('source'), res.get('as_of'))
    it = items[0]

    def build(lang):
        es = lang == 'es'
        head = (f'{n} eventos ({win}); el más grave: ' if es else f'{n} events ({win}); most severe: ') if n else \
            ('El evento más grave: ' if es else 'Most severe event: ')
        return head + _quote(it['title'], lang)
    return build('es'), build('en'), res.get('source'), res.get('as_of')


def _note_web(res, args, ctx):
    items = [x for x in res.get('results') or [] if isinstance(x, dict) and x.get('title')]
    if not items:
        return None
    return ('En la web: ' + _quote(items[0]['title'], 'es'), 'On the web: ' + _quote(items[0]['title'], 'en'),
            res.get('source'), res.get('as_of'))


def _note_scenario(res, args, ctx):
    hit = [x for x in res.get('direct_hit') or [] if x][:3]
    ben = [x for x in res.get('could_benefit') or [] if x][:2]
    if not hit and not ben:
        return None

    def build(lang):
        es = lang == 'es'
        bits = []
        if hit:
            bits.append(('Golpe directo: ' if es else 'Direct hit: ') + ', '.join(hit))
        if ben:
            bits.append(('podrían ganar: ' if es else 'could benefit: ') + ', '.join(ben))
        return ' · '.join(bits)
    return build('es'), build('en'), res.get('source'), res.get('as_of')


def _note_movers(res, args, ctx):
    items = [x for x in res.get('items') or [] if isinstance(x, dict) and x.get('change_pct') is not None][:3]
    if not items:
        return None
    down = res.get('direction') == 'down'
    # «hoy» solo si ninguna fila dice que su mercado está fuera de sesión (fin de semana, antes de
    # la apertura, después del cierre): entonces la variación es la de la ÚLTIMA sesión
    last = any(_session_live(x.get('market_state'), x.get('market_time')) is False for x in items)

    def build(lang):
        es = lang == 'es'
        if last:
            head = ('Más caen (última sesión): ' if down else 'Más suben (última sesión): ') if es else \
                ('Top losers (last session): ' if down else 'Top gainers (last session): ')
        else:
            head = ('Más caen hoy: ' if down else 'Más suben hoy: ') if es else ('Top losers today: ' if down else
                                                                                  'Top gainers today: ')
        return head + ', '.join(f'{x.get("label")} ({_pct(x["change_pct"], lang, 1, True)})' for x in items)
    return build('es'), build('en'), res.get('source'), res.get('as_of')


def _note_risk_report(res, args, ctx):
    vol = res.get('vol_ann_pct')
    var = res['var95'].get('hist_1d_pct') if isinstance(res.get('var95'), dict) else None
    mdd = res.get('max_drawdown_pct')
    if vol is None and var is None:
        return None

    def build(lang):
        es = lang == 'es'
        bits = []
        if vol is not None:
            bits.append(('volatilidad anual ' if es else 'annual volatility ') + _pct(vol, lang, 1))
        if var is not None:
            bits.append(('VaR 95 % a 1 día ' if es else '1-day 95% VaR ') + _pct(var, lang, 2))
        if mdd is not None:
            bits.append(('peor caída ' if es else 'max drawdown ') + _pct(mdd, lang, 1))
        s = ' · '.join(bits)
        return s[:1].upper() + s[1:]
    return build('es'), build('en'), 'Yahoo Finance (daily prices) + Khipus', res.get('as_of')


def _note_greeks(res, args, ctx):
    t = res.get('totals') if isinstance(res.get('totals'), dict) else {}
    if t.get('vega_usd') is None:
        return None

    def build(lang):
        es = lang == 'es'
        s = (f'Vega {_fmt_num(t["vega_usd"], 2, lang)} USD ' + ('por punto de volatilidad' if es else 'per vol point'))
        if t.get('theta_usd_day') is not None:
            s += f' · theta {_fmt_num(t["theta_usd_day"], 2, lang)} USD/' + ('día' if es else 'day')
        return s
    return build('es'), build('en'), res.get('source'), res.get('as_of')


def _note_memo(res, args, ctx):
    body = res.get('memo') if isinstance(res.get('memo'), dict) else {}
    dec = res.get('decision')
    les, len_ = body.get('decision_label_es'), body.get('decision_label_en')
    if not les and dec:
        les, len_ = _decision_labels(dec)
    conv = res.get('overall_conviction')
    st = res.get('status')
    # el nombre solo si el memo NO es de la empresa principal de la pregunta (si no, sobra)
    lbl = None if res.get('entity_id') == ctx.get('primary') else (res.get('label') or res.get('entity_id'))

    def build(lang):
        es = lang == 'es'
        if body.get('decision_code') == 'INSUFFICIENT_DATA':
            s = ('Sin veredicto: faltan analistas (datos insuficientes)' if es
                 else 'No verdict: not enough analysts (insufficient data)')
        else:
            word = str((les if es else len_) or dec or '').lower()
            c = _fmt_num(conv, 0, lang, True)
            cv = (f' (convicción {c})' if es else f' (conviction {c})') if c is not None else ''
            if st == 'proposed':
                s = (f'Propone {word}{cv} · espera tu revisión' if es else f'Proposes {word}{cv} · awaiting your review')
            elif st == 'approved':
                s = (f'Aprobado: {word}{cv}' if es else f'Approved: {word}{cv}')
            elif st == 'rejected':
                s = (f'Propuesta de {word} rechazada' if es else f'Proposal to {word} rejected')
            elif st == 'executed':
                s = (f'Ejecutado: {word}' if es else f'Executed: {word}')
            else:
                s = (f'Decisión: {word}{cv}' if es else f'Decision: {word}{cv}')
        if lbl:
            s = f'{lbl} — {s}'
        if res.get('expired'):
            d = str(res.get('created_at') or '')[:10]
            s += (f' · memo vencido ({d})' if es else f' · expired memo ({d})')
        return s
    return build('es'), build('en'), res.get('source'), res.get('created_at') or res.get('as_of')


def _memo_expired(cm):
    """¿El memo de la pizarra ya venció? Usa `expired` si viene; si no, fecha + TTL del comité."""
    if 'expired' in cm and cm.get('expired') is not None:
        return bool(cm.get('expired'))
    d = cm.get('date') or cm.get('created_at')
    if not d:
        return False
    try:
        from research.committee import _ttl_hours
        ttl = float(_ttl_hours())
    except Exception:  # noqa: BLE001
        ttl = 72.0
    try:
        t = datetime.fromisoformat(str(d).replace('Z', '+00:00'))
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    return (datetime.now(timezone.utc) - t).total_seconds() > ttl * 3600


def _board_committee(cm, es):
    """' · comité: …' de una fila de la pizarra. Sin quórum NO hay veredicto (HOLD +
    INSUFFICIENT_DATA), una propuesta rechazada no es la postura vigente y un memo vencido se
    marca con su fecha — la misma regla que _note_memo y la ventana «En una mirada»."""
    if cm.get('decision_code') == 'INSUFFICIENT_DATA':
        s = ' · comité: sin veredicto (datos insuficientes)' if es else ' · committee: no verdict (insufficient data)'
    else:
        les, len_ = _decision_labels(cm['decision'])
        w = str(les if es else len_).lower()
        if cm.get('status') == 'rejected':
            s = f' · comité: propuesta de {w} rechazada' if es else f' · committee: proposal to {w} rejected'
        else:
            s = f' · comité: {w}' if es else f' · committee: {w}'
    if _memo_expired(cm):
        d = str(cm.get('date') or cm.get('created_at') or '')[:10]
        s += (' · memo vencido' if es else ' · expired memo') + (f' ({d})' if d else '')
    return s


def _board_num(x):
    v = x.get('conviction')
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) and v == v else None


def _note_board(res, args, ctx):
    items = [x for x in res.get('items') or [] if isinstance(x, dict)]
    side = str((args or {}).get('side') or 'all').strip().lower()
    if side not in ('favorable', 'unfavorable'):
        side = 'all'
    if not items:
        if side == 'unfavorable':       # filtrada: vacía NO quiere decir que no haya investigación
            return ('Ninguna empresa de la pizarra tiene convicción en contra',
                    'No company on the board has negative conviction', res.get('source'), res.get('as_of'))
        if side == 'favorable':
            return ('Ninguna empresa de la pizarra tiene convicción a favor',
                    'No company on the board has positive conviction', res.get('source'), res.get('as_of'))
        return ('La pizarra está vacía: todavía no hay investigación', 'The board is empty: no research yet',
                res.get('source'), res.get('as_of'))
    prim = ctx.get('primary')
    it = next((x for x in items if x.get('entity_id') == prim), None)
    scored = [x for x in items if _board_num(x) is not None]
    # `items` es lo que DEVOLVIÓ la herramienta (cortado por `limit` y filtrado por `side`): son las
    # empresas MOSTRADAS, no el tamaño de la pizarra. Con side=unfavorable la elegida es la MÁS en
    # contra (antes max() llamaba «la más favorable» a la menos negativa).
    if side == 'unfavorable':
        pick = min(scored, key=_board_num) if scored else None
    else:
        pick = max(scored, key=_board_num) if scored else None

    def build(lang):
        es = lang == 'es'
        if it is not None:
            c = _fmt_num(it.get('conviction'), 1, lang, True)
            s = (f'Convicción de los agentes en {it.get("label")}: {c}' if es
                 else f'Agents\' conviction on {it.get("label")}: {c}')
            cm = it.get('committee') if isinstance(it.get('committee'), dict) else None
            if cm and cm.get('decision'):
                s += _board_committee(cm, es)
            return s
        n = len(items)
        if side == 'unfavorable':
            head = (f'{n} empresas en contra mostradas' if es else f'{n} unfavorable companies shown')
        elif side == 'favorable':
            head = (f'{n} empresas a favor mostradas' if es else f'{n} favorable companies shown')
        else:
            head = (f'{n} empresas de la pizarra mostradas' if es else f'{n} board companies shown')
        if pick is None:
            return head
        v = _board_num(pick)
        c = _fmt_num(v, 1, lang, True)
        if side == 'unfavorable':
            tag = ('la más en contra' if es else 'most unfavorable') if v < 0 else \
                ('la de menor convicción' if es else 'lowest conviction')
        else:
            tag = ('la más favorable' if es else 'most favorable') if v > 0 else \
                ('la de mayor convicción' if es else 'highest conviction')
        return f'{head}; {tag}: {pick.get("label")} ({c})'
    return build('es'), build('en'), res.get('source'), res.get('as_of')


def _note_track(res, args, ctx):
    ov = res.get('overall') if isinstance(res.get('overall'), dict) else {}
    n, h = ov.get('n_scored') or 0, ov.get('hits') or 0
    mn = res.get('min_n') or 5

    def build(lang):
        es = lang == 'es'
        if n >= mn:
            r = _pct(h / n * 100 if n else None, lang, 0)
            return (f'Historial: {h} aciertos de {n} conclusiones calificadas ({r})' if es
                    else f'Track record: {h} hits out of {n} scored conclusions ({r})')
        return (f'Sin historial suficiente todavía ({n} calificadas; hacen falta {mn})' if es
                else f'Not enough track record yet ({n} scored; {mn} needed)')
    return build('es'), build('en'), res.get('source'), res.get('as_of')


def _note_research(res, args, ctx):
    n = res.get('n_claims')
    lbl = res.get('label') or res.get('entity_id')
    k = len(res.get('claims_by_agent') or {})
    if not n:
        return (f'Sin investigación vigente sobre {lbl} todavía', f'No current research on {lbl} yet',
                res.get('source'), res.get('as_of'))
    return (f'{n} conclusiones vigentes de {k} analista{"s" if k != 1 else ""} sobre {lbl}',
            f'{n} current conclusion{"s" if n != 1 else ""} from {k} analyst{"s" if k != 1 else ""} on {lbl}',
            res.get('source'), res.get('as_of'))


def _note_ask(res, args, ctx):
    if res.get('available') is False:
        return None
    lbl = res.get('label') or res.get('entity') or ''
    answers = res.get('answers') if isinstance(res.get('answers'), list) else None
    if answers:
        return (f'{len(answers)} analistas respondieron sobre {lbl}', f'{len(answers)} analysts answered on {lbl}',
                'Khipus research claims', None)
    sk = res.get('skill') if isinstance(res.get('skill'), dict) else {}
    if sk.get('note_es'):
        return (sk['note_es'], sk.get('note_en') or sk['note_es'], 'Khipus — datos en vivo del rol', None)
    if res.get('needs_research') and sk.get('n_evidence'):
        return (f'Respondió con los datos en vivo de su rol sobre {lbl}', f'Answered from the live data of its role on {lbl}',
                'Khipus — datos en vivo del rol', None)
    if res.get('needs_research'):
        return (f'Todavía no investigó {lbl}: puede investigarlo', f'Has not researched {lbl} yet: it can research it',
                'Khipus research claims', None)
    n = res.get('n_claims')
    if n:
        return (f'Respondió con sus {n} conclusiones vigentes sobre {lbl}', f'Answered from its {n} current conclusions on {lbl}',
                'Khipus research claims', None)
    return None


def _note_search(res, args, ctx):
    n = res.get('count')
    if n is None:
        return None
    return (f'Encontró {n} empresas para {_quote(res.get("query"), "es")}',
            f'Found {n} companies for {_quote(res.get("query"), "en")}', res.get('source'), res.get('as_of'))


def _note_health(res, args, ctx):
    if not (res.get('hint_es') or res.get('hint_en')):
        return None
    return (_clip(res.get('hint_es') or res.get('hint_en'), _NOTE_MAX), _clip(res.get('hint_en') or res.get('hint_es'), _NOTE_MAX),
            res.get('source'), res.get('as_of'))


_NOTE_FN = {'get_company': _note_company, 'get_supply_chain': _note_supply_chain, 'rank_companies': _note_rank,
            'get_news': _note_news, 'get_world_events': _note_world, 'web_search': _note_web,
            'scenario_exposure': _note_scenario, 'market_movers': _note_movers, 'get_risk_report': _note_risk_report,
            'get_option_greeks': _note_greeks, 'get_committee_memo': _note_memo, 'get_conclusions_board': _note_board,
            'get_track_record': _note_track, 'get_research': _note_research, 'ask_agent': _note_ask,
            'search_companies': _note_search, 'get_research_health': _note_health}
_GENERIC_NOTE = {
    'get_claim_evidence': ('Revisó la evidencia de una conclusión', 'Checked the evidence behind a conclusion'),
    'get_space_summary': ('Revisó lanzamientos y satélites (Launch Library 2, CelesTrak)',
                          'Checked launches and satellites (Launch Library 2, CelesTrak)'),
}


def _result_entity(name, args, res):
    """Id canónico de la empresa de la que habla un resultado (o None)."""
    if not isinstance(res, dict):
        return None
    if name == 'get_company':
        return res.get('id')
    if name == 'get_supply_chain':
        return res.get('root')
    if name in ('get_research', 'get_committee_memo'):
        return res.get('entity_id')
    if name == 'get_news':
        return (res.get('company') or {}).get('id') if isinstance(res.get('company'), dict) else None
    if name == 'ask_agent':
        return res.get('entity')
    return None


def chat_entities(message, calls, context=None, limit=5):
    """[{id, label}] — empresas DETECTADAS en la pregunta (primero, en orden) y las que consultaron las
    herramientas. Ids canónicos del grafo (nunca un id que no exista)."""
    ids = []
    try:
        ids = list(_entities_in(message))
    except Exception:  # noqa: BLE001
        ids = []
    for name, args, ok, res in calls or []:
        if ok:
            e = _result_entity(name, args, res)
            if e and e not in ids:
                ids.append(e)
    try:
        nodes = _snapshot()['nodes']
    except Exception:  # noqa: BLE001
        nodes = {}
    out = []
    for i in ids:
        if i in nodes and all(o['id'] != i for o in out):
            out.append({'id': i, 'label': nodes[i].get('label') or i})
        if len(out) >= limit:
            break
    return out


def _company_card(c):
    lm = c.get('live_market') if isinstance(c.get('live_market'), dict) else {}
    live = bool(lm.get('available')) and lm.get('price') is not None

    def nb(lst):
        return [{'id': x['id'], 'label': x.get('label') or x['id'], 'weight': x.get('weight'), 'type': x.get('type'),
                 'verified': x.get('verified', True), 'confidence': x.get('confidence')}
                for x in (lst or [])[:5] if isinstance(x, dict) and x.get('id')]
    st = c.get('structure') if isinstance(c.get('structure'), dict) else None
    card = {'id': c.get('id'), 'label': c.get('label'), 'symbol': c.get('symbol'), 'live': live,
            'price': lm.get('price') if live else None, 'change_pct': lm.get('change_pct') if live else None,
            'currency': lm.get('currency') if live else None,
            'market_cap_usd_b': lm.get('market_cap_usd_b') if live else None,
            'source': lm.get('source') if live else None,
            'source_label': _src_name(lm.get('source')) if live else None,
            'as_of': _price_time(lm) if live else None,
            'market_state': lm.get('market_state') if live else None,
            'session_live': _session_live(lm.get('market_state'), lm.get('market_time')) if live else None,
            'nrs': (c.get('network_risk_score') or {}).get('value') if isinstance(c.get('network_risk_score'), dict) else None,
            'top_suppliers': nb(c.get('top_suppliers')), 'top_customers': nb(c.get('top_customers')),
            'counts': c.get('counts') if isinstance(c.get('counts'), dict) else None,
            'structure': dict(st) if st else None, 'listed': c.get('listed'),
            'graph_as_of': (c.get('catalog') or {}).get('as_of') if isinstance(c.get('catalog'), dict) else None,
            'checked_at': c.get('as_of')}
    if not live and lm.get('reason'):
        card['live_reason'] = _clip(lm['reason'], 160)
    pv = c.get('private_valuation')
    if isinstance(pv, dict) and pv.get('valuation_usd_b') is not None:
        card['private_valuation'] = {k: pv.get(k) for k in ('valuation_usd_b', 'as_of', 'round', 'source_url')}
    return card


def _committee_card(m):
    body = m.get('memo') if isinstance(m.get('memo'), dict) else {}
    dec = m.get('decision')
    les, len_ = body.get('decision_label_es'), body.get('decision_label_en')
    if not les and dec:
        les, len_ = _decision_labels(dec)
    th = [x for x in body.get('thesis') or [] if isinstance(x, dict)]
    rk = [x for x in body.get('key_risks') or [] if isinstance(x, dict)]
    tv = body.get('track_validation') if isinstance(body.get('track_validation'), dict) else {}
    conv = m.get('conviction') if isinstance(m.get('conviction'), dict) else {}
    return {'entity_id': m.get('entity_id'), 'label': m.get('label'), 'memo_id': m.get('memo_id'),
            'status': m.get('status'), 'decision': dec, 'decision_label_es': les, 'decision_label_en': len_,
            'decision_code': body.get('decision_code'), 'overall_conviction': m.get('overall_conviction'),
            'by_horizon': {h: r.get('score') for h, r in conv.items() if isinstance(r, dict)},
            'thesis_es': [_clip(x.get('thesis_es'), 320) for x in th if x.get('thesis_es')][:3],
            'thesis_en': [_clip(x.get('thesis_en') or x.get('thesis_es'), 320) for x in th
                          if x.get('thesis_en') or x.get('thesis_es')][:3],
            'risks_es': [_clip(x.get('risk_es'), 320) for x in rk if x.get('risk_es')][:3],
            'risks_en': [_clip(x.get('risk_en') or x.get('risk_es'), 320) for x in rk
                         if x.get('risk_en') or x.get('risk_es')][:3],
            'validation_es': tv.get('label_es'), 'validation_en': tv.get('label_en'),
            'created_at': m.get('created_at'), 'expires_at': m.get('expires_at'), 'expired': bool(m.get('expired'))}


def chat_cards(calls, entities):
    """{company?, committee?} de la empresa PRINCIPAL (la 1.ª detectada) con los resultados ya obtenidos."""
    prim = entities[0]['id'] if entities else None
    cards = {}
    comp = [r for (n, a, ok, r) in calls if ok and n == 'get_company' and isinstance(r, dict) and r.get('id')]
    if comp:
        c = next((r for r in comp if r.get('id') == prim), comp[0])
        cards['company'] = _company_card(c)
    memos = [r for (n, a, ok, r) in calls if ok and n == 'get_committee_memo' and isinstance(r, dict)
             and r.get('memo_id')]
    if memos:
        m = next((r for r in memos if r.get('entity_id') == prim), memos[0])
        cards['committee'] = _committee_card(m)
    return cards


def agents_used(calls, message, context=None, entities=None):
    """[{agent, tools, ok, note_es, note_en, source, as_of}] en el orden de las mascotas. La nota se
    arma SOLO con valores de los resultados (sin IA). Cadena también aporta cuando la ficha de la
    empresa trae su estructura de proveedores y la pregunta habla de riesgo/proveedores."""
    context = context or {}
    prim = entities[0]['id'] if entities else None
    ctx = {'primary': prim}
    by = {}
    for name, args, ok, res in calls or []:
        ag = tool_agent(name, args)
        g = by.setdefault(ag, {'tools': [], 'ok': False, 'notes': [], 'errs': 0})
        if name not in g['tools']:
            g['tools'].append(name)
        if ok:
            g['ok'] = True
            # la ficha de la empresa PRINCIPAL primero (si hay varias)
            fn = _NOTE_FN.get(name)
            try:
                note = fn(res, args, ctx) if fn and isinstance(res, dict) else None
            except Exception as e:  # noqa: BLE001 — una nota nunca rompe la respuesta
                log.info('khipu_chat nota %s: %s', name, type(e).__name__)
                note = None
            if note is None and name in _GENERIC_NOTE:
                note = _GENERIC_NOTE[name] + ((res or {}).get('source'), (res or {}).get('as_of'))
            if note:
                rank = 0 if _result_entity(name, args, res) in (prim, None) else 1
                g['notes'].append((rank, len(g['notes']), name, note))
        else:
            g['errs'] += 1
    enabled = context.get('agents_enabled')
    cad_ok = not isinstance(enabled, list) or 'cadena' in enabled
    if cad_ok and _RISK_Q_RX.search(message or ''):
        comp = [(a, r) for (n, a, ok, r) in calls or [] if ok and n == 'get_company' and isinstance(r, dict)]
        comp.sort(key=lambda x: 0 if x[1].get('id') == prim else 1)
        for a, r in comp[:1]:
            note = _note_structure(r, a, ctx)
            if note:
                g = by.setdefault('cadena', {'tools': [], 'ok': True, 'notes': [], 'errs': 0})
                if 'get_company' not in g['tools']:
                    g['tools'].append('get_company')
                g['ok'] = True
                g['notes'].insert(0, (-1, -1, 'get_company', note))
    out = []
    for ag in _AGENT_ORDER:
        g = by.get(ag)
        if not g:
            continue
        notes = sorted(g['notes'], key=lambda x: (x[0], x[1]))
        seen, es_bits, en_bits, src, as_of = set(), [], [], None, None
        for _r, _i, name, (n_es, n_en, s_, a_) in notes:
            if not n_es or n_es in seen:
                continue
            n_en = n_en or n_es
            # una 2.ª nota solo si cabe ENTERA: nunca se corta una cifra a la mitad ("4.47…" ≠ 4.470)
            if es_bits and (len(' · '.join(es_bits + [n_es])) > _NOTE_MAX
                            or len(' · '.join(en_bits + [n_en])) > _NOTE_MAX):
                continue
            seen.add(n_es)
            es_bits.append(n_es)
            en_bits.append(n_en)
            if src is None:
                src, as_of = s_, a_
            if len(es_bits) >= 2:
                break
        if not es_bits:
            if g['ok']:
                es_bits = ['Consultó ' + ', '.join(g['tools'])]
                en_bits = ['Checked ' + ', '.join(g['tools'])]
            else:
                es_bits = ['No pudo obtener los datos ahora']
                en_bits = ['Could not get the data right now']
        out.append({'agent': ag, 'tools': list(g['tools']), 'ok': bool(g['ok']),
                    'note_es': _clip(' · '.join(es_bits), _NOTE_MAX), 'note_en': _clip(' · '.join(en_bits), _NOTE_MAX),
                    'source': src, 'as_of': as_of})
    return out


def enrich_answer(message, calls, context=None, req_id=None):
    """Campos que Khipus OS SUMA a la respuesta (nunca reemplaza ninguno)."""
    out = {'req_id': req_id, 'entities': [], 'agents_used': [], 'cards': {}}
    try:
        ents = chat_entities(message, calls, context)
        out['entities'] = ents
        out['agents_used'] = agents_used(calls, message, context, ents)
        out['cards'] = chat_cards(calls, ents)
    except Exception as e:  # noqa: BLE001 — la respuesta del chat nunca se rompe por un extra
        log.warning('khipu_chat enrich: %s', type(e).__name__)
    return out


def _call_ai(system, prompt, timeout):
    # want_json: cada paso es un objeto JSON (parse_step) → con Gemini, JSON estricto y sin pensamiento.
    # timeout_s: el proveedor corta a la vez que el chat (antes el hilo seguía 90 s ocupando cupo).
    # live_facts=False: el bloque "DATOS EN VIVO" se calcula UNA vez por pregunta en _run_chat.
    fut = _submit_ai(_ai._ai_complete, system, prompt, STEP_MAX_TOKENS, 'fast', want_json=True,
                     timeout_s=max(5.0, min(float(timeout), 30.0)), live_facts=False)
    return fut.result(timeout=max(1.0, timeout))


def run_chat(message, history=None, lang='es', context=None, app=None, budget_s=None, max_steps=None, req_id=None):
    """PORTERO (Jev, core/decide.py): decide en paralelo qué necesita la pregunta. En SOMBRA solo se
    compara con lo que el chat hizo; con DECIDE_CONTROL=chat_gate MANDA (router_plan): responder con
    datos locales SIN IA, pocas consultas, el análisis completo, o el nivel de modelo de un @agente.
    `out.router` dice quién decidió ({by: 'jev'|'default', route, confidence}).

    Khipus OS: con `req_id` (lo manda el cliente) el progreso queda consultable en
    GET /api/khipu/chat/progress/<req_id> mientras la respuesta se arma."""
    rid = valid_req_id(req_id)
    progress_begin(rid)
    try:
        gate = None
        try:
            from core import decide as _decide
            gate = _decide.chat_gate_start(message, lang)
        except Exception:  # noqa: BLE001
            gate = None
        direct = _mention_route(message, history, lang, context, req_id=rid, gate=gate)
        out = direct if direct is not None else _run_chat(message, history, lang, context, app, budget_s, max_steps,
                                                          req_id=rid, gate=gate)
        out.setdefault('router', {'by': 'default'})
        if gate is not None:
            try:
                _decide.chat_gate_finish(gate, out, message)
            except Exception:  # noqa: BLE001
                pass
    finally:
        progress_end(rid)
    # contrato Khipus OS (solo se AGREGAN campos): siempre presentes
    out['req_id'] = rid or out.get('req_id') or uuid.uuid4().hex[:16]
    out.setdefault('entities', [])
    out.setdefault('agents_used', [])
    out.setdefault('cards', {})
    return out


def _mention_route(message, history, lang, context, req_id=None, gate=None):
    """'@fundamental ¿qué opinas de TSMC?' / 'pregúntale al analista técnico: …' → el puesto responde
    en persona (research/ask_agent). Devuelve None si no es una mención."""
    try:
        from research import ask_agent as aa
        seat, question = aa.parse_mention(message)
    except Exception:  # noqa: BLE001
        return None
    if not seat:
        return None
    t0 = time.monotonic()
    context = context if isinstance(context, dict) else {}
    ents = _entities_in(question) or _entities_in(message)
    if not ents:
        for k in ('entity', 'company', 'selected'):
            if context.get(k):
                ents = [str(context[k])]
                break
    if not ents and isinstance(context.get('selected_node'), dict) and context['selected_node'].get('id'):
        ents = [context['selected_node']['id']]          # la empresa EN PANTALLA (validate_request la deja aquí)
    if not ents:
        # la empresa de la que se venía hablando
        for h in reversed(list(history or [])):
            txt = h.get('content') if isinstance(h, dict) else str(h)
            ents = _entities_in(str(txt or ''))
            if ents:
                break
    if not ents and context.get('recent_entities'):
        ents = [context['recent_entities'][0]]
    meta = aa.seat_meta(seat) if seat != 'all' else {'seat': 'all', 'emoji': '🏛', 'name_es': 'Todos los analistas', 'name_en': 'All analysts'}
    agent = {'seat': seat, 'emoji': meta['emoji'], 'name': meta['name_en'] if lang == 'en' else meta['name_es']}
    base = {'actions': [], 'tools_used': [{'name': 'ask_agent', 'args_summary': seat, 'ok': True}], 'sources': [],
            'model': None, 'answer_source': 'agent', 'ai': True, 'lang': lang, 'steps': 1, 'agent': agent,
            'elapsed_ms': 0, 'as_of': _now_iso()}
    mascot = SEAT_AGENT.get(seat, 'analista')

    def finish(ok, res=None, note=None):
        """Campos de Khipus OS para la ruta @ (mismo contrato que el bucle de herramientas)."""
        calls = [('ask_agent', {'seat': seat}, ok, res if isinstance(res, dict) else {})]
        ex = enrich_answer(message, calls if ok else [], context, req_id)
        if not ok:
            es, en = note or ('El analista no pudo responder ahora', 'The analyst could not answer right now')
            ex['agents_used'] = [{'agent': mascot, 'tools': ['ask_agent'], 'ok': False, 'note_es': es, 'note_en': en,
                                  'source': None, 'as_of': None}]
        base.update(ex)
        return base

    if not ents:
        base['answer'] = ('Which company should I ask about?' if lang == 'en' else '¿Sobre qué empresa quieres que responda?')
        base['ai'] = False
        return finish(False, note=('Falta saber de qué empresa', 'Needs to know which company'))
    h = progress_add(req_id, 'ask_agent', {'seat': seat})
    progress_phase(req_id, 'agent')
    # JEV AL MANDO: el nivel del analista. Pregunta puntual → solo sus datos (sin IA); de consulta → modelo
    # rápido; análisis → modelo profundo (el de siempre).
    mode, plan = 'deep', None
    try:
        from core import decide as _decide
        plan = _decide.chat_plan(gate)
    except Exception:  # noqa: BLE001
        plan = None
    if plan:
        mode = {'local_fact': 'local', 'needs_tools': 'fast', 'offtopic': 'fast'}.get(plan['route'], 'deep')
        base['router'] = _router(plan, mode=mode)
    kw = {} if mode == 'deep' else {'mode': mode}
    try:
        with _research_session() as s:      # sin base de investigación: responde con sus habilidades en vivo
            r = aa.ask_all(s, question, ents[0], lang, **kw) if seat == 'all' else aa.ask(s, seat, question, ents[0], lang, **kw)
    except Exception as e:  # noqa: BLE001
        progress_set(req_id, h, 'error')
        log.warning('ask_agent: %s', _clip(e, 160))
        base['answer'] = ('The analyst could not answer right now.' if lang == 'en' else 'El analista no pudo responder ahora mismo.')
        base['ai'] = False
        base['degraded'] = 'ai_error'
        base['ai_detail'] = _ai._redact(e, 200)
        return finish(False)
    progress_set(req_id, h, 'done' if (r or {}).get('ok', True) else 'error')
    base['answer'] = str((r or {}).get('answer') or '')[:MAX_ANSWER]
    base['model'] = (r or {}).get('model')
    if (r or {}).get('entity'):
        base['agent']['entity'] = r['entity']
        base['agent']['label'] = r.get('label')
    if (r or {}).get('answers'):
        base['agent']['answers'] = [{k: a.get(k) for k in ('seat', 'emoji', 'name', 'answer')} for a in r['answers']]
    # la ventana / el gráfico DE SU ROL (Cadena → cadena de suministro; Técnico → gráfico de precio…) y,
    # si nunca la investigó a fondo, la investigación profunda como opción (no como respuesta)
    sk = (r or {}).get('skill') or {}
    acts = list(sk.get('actions') or [])
    if (r or {}).get('needs_research') and (r or {}).get('entity'):
        acts.append({'type': 'open_research', 'arg': r['entity']})
    base['actions'] = validate_actions(acts)
    base['sources'] = [{'label': str(x.get('label') or '')[:160], 'as_of': x.get('as_of')}
                       for x in (sk.get('sources') or []) if isinstance(x, dict) and x.get('label')][:8]
    if not (r or {}).get('model'):
        base['ai'] = False
    base['elapsed_ms'] = int((time.monotonic() - t0) * 1000)
    return finish(bool((r or {}).get('ok', True)), r)


def _router(plan, **extra):
    return dict({'by': 'jev', 'route': plan['route'], 'confidence': plan.get('confidence')}, **extra)


def _local_answer(message, lang, results):
    """Ruta LOCAL (Jev: 'local_fact'): la ficha de la empresa con datos en vivo, SIN IA. None si no hay ficha."""
    companies = [r for (name, ok, r) in results if ok and name == 'get_company']
    if not companies:
        return None
    en = lang == 'en'
    body = '\n\n'.join(company_summary(c, lang) for c in companies[:2])
    tail = ('Source: Khipus graph · live market profile.' if en else 'Fuente: grafo Khipus · perfil de mercado en vivo.')
    return f'{body}\n\n{tail}', [{'type': 'open_xray', 'arg': companies[0].get('id')}]


def _run_chat(message, history=None, lang='es', context=None, app=None, budget_s=None, max_steps=None, req_id=None,
              gate=None):
    t0 = time.monotonic()
    budget = TIME_BUDGET_S if budget_s is None else float(budget_s)
    steps_max = MAX_STEPS if max_steps is None else int(max_steps)
    deadline = t0 + budget
    history = list(history or [])[-MAX_HISTORY:]
    context = context or {}
    scratch, results, tools_used, sources = [], [], [], []
    calls = []          # (herramienta, args, ok, resultado) en orden → agents_used / cards / entities
    cache = {}
    model = None
    ai_calls = 0
    reason = None
    ai_detail = None
    feedback = None
    repaired = False
    rounds = 0
    ai_slow = False

    def done(answer, actions, answer_source='ai'):
        out = {'answer': str(answer or '').strip()[:MAX_ANSWER], 'actions': validate_actions(actions),
               'tools_used': tools_used, 'sources': sources, 'model': model if answer_source == 'ai' else None,
               'answer_source': answer_source, 'ai': answer_source == 'ai', 'lang': lang,
               'steps': ai_calls, 'elapsed_ms': int((time.monotonic() - t0) * 1000), 'as_of': _now_iso()}
        out.update(enrich_answer(message, calls, context, req_id))
        out['router'] = router
        return out

    router = {'by': 'default'}

    def fallback(why):
        progress_phase(req_id, 'fallback')
        ans, acts, extra = fallback_answer(message, lang, why, results, deadline, app, req_id=req_id)
        for name, args, ok, res in extra:
            tools_used.append({'name': name, 'args_summary': _args_summary(args), 'ok': ok})
            calls.append((name, args, ok, res))
            if ok:
                _collect_sources(name, res, sources, lang)
        out = done(ans, acts, answer_source='fallback')
        out['degraded'] = why
        if ai_detail:
            out['ai_detail'] = ai_detail   # p. ej. "claude: credit balance…; gemini: HTTP 404 NOT_FOUND"
            try:
                from research.errors import friendly
                es, en = friendly(ai_detail)
                if es:
                    out['ai_detail_es'], out['ai_detail_en'] = es, en
            except Exception:  # noqa: BLE001
                pass
        return out

    if not _ai._ai_configured():
        return fallback('no_ai')

    system = build_system(lang, context.get('mode'), context.get('agents_enabled'))
    # DATOS EN VIVO (una sola vez por pregunta) y PRE-CONSULTA especulativa de la ficha de la(s) empresa(s)
    # mencionada(s), AL MISMO TIEMPO (Khipus OS, 2026-10-06: antes en serie → hasta 3,5 s + 2,5 s antes de la
    # primera llamada a la IA; ahora como mucho 3,5 s). Mismos topes por pieza que antes: el bloque en vivo
    # hasta 3,5 s y la ficha hasta 2,5 s (o mientras se espera el bloque), así que el resultado no cambia.
    progress_phase(req_id, 'prefetch')
    t_pre = time.monotonic()
    live_fut = None
    try:
        from core.live_facts import live_facts_block
        live_fut = _POOL.submit(live_facts_block, message)
    except Exception:  # noqa: BLE001
        live_fut = None
    pre = {}
    for nid in _entities_in(message)[:2]:
        h = progress_add(req_id, 'get_company')
        fut = _POOL.submit(execute_tool, 'get_company', {'id_or_ticker': nid, 'include_live': True}, app, lang)
        if h is not None:
            fut.add_done_callback(lambda f, h=h: _progress_from_future(req_id, h, f))
        pre[nid] = fut
    live = ''
    if live_fut is not None:
        try:
            live = live_fut.result(timeout=3.5) or ''
        except Exception:  # noqa: BLE001
            live = ''
    if pre:
        cap = min(2.5, max(0.5, deadline - t_pre - 10))
        wait(list(pre.values()), timeout=max(0.0, cap - (time.monotonic() - t_pre)))
        for nid, fut in pre.items():
            if not fut.done():
                continue
            try:
                ok, res = fut.result()
            except Exception:  # noqa: BLE001
                continue
            key = 'get_company' + json.dumps({'id_or_ticker': nid, 'include_live': True}, sort_keys=True, default=str)
            cache[key] = (ok, res)
            results.append(('get_company', ok, res))
            calls.append(('get_company', {'id_or_ticker': nid, 'include_live': True}, ok, res))
            tools_used.append({'name': 'get_company', 'args_summary': _args_summary({'id_or_ticker': nid}), 'ok': bool(ok),
                               **({} if ok else {'error': _clip(res.get('error'), 160)})})
            if ok:
                _collect_sources('get_company', res, sources, lang)
            scratch.append(f'get_company({json.dumps({"id_or_ticker": nid}, ensure_ascii=False)}) → '
                           + ('' if ok else 'ERROR: ') + _fmt_result(res))
    # JEV AL MANDO (DECIDE_CONTROL=chat_gate): ya pensó en paralelo con la pre-consulta → elige el camino más
    # barato que alcanza. Sin Jev / sin confianza → camino de siempre.
    plan = None
    try:
        from core import decide as _decide
        plan = _decide.chat_plan(gate)
    except Exception:  # noqa: BLE001
        plan = None
    router = {'by': 'default'}
    if plan:
        route = plan['route']
        if route == 'local_fact' and (plan.get('about_portfolio') or 0) < 0.5:
            loc = _local_answer(message, lang, results)
            if loc:
                out = done(loc[0], loc[1], answer_source='local')
                out['router'] = _router(plan, ai_calls=0)
                return out
        if route == 'needs_tools':
            steps_max = min(steps_max, 2)
        elif route in ('offtopic', 'local_fact'):
            steps_max = min(steps_max, 1)
        router = _router(plan, max_steps=steps_max)
    while True:
        remaining = deadline - time.monotonic()
        if remaining < MIN_STEP_S:
            reason = 'budget'
            break
        force_final = rounds >= steps_max or remaining < FINAL_RESERVE_S
        prompt = build_prompt(message, history, lang, context, scratch, steps_max - rounds, force_final, feedback, live=live)
        feedback = None
        progress_phase(req_id, 'thinking')
        try:
            ai_calls += 1
            text, model = _call_ai(system, prompt, remaining)
        except _FutTimeout:
            reason = 'budget'
            ai_slow = True          # la IA no alcanzó a responder: no tiene sentido pedirle otra redacción
            break
        except _ai.AIBusyError:
            reason = 'busy'
            break
        except Exception as e:  # noqa: BLE001
            log.warning('khipu_chat: IA falló (%s)', _clip(e, 160))
            reason = 'ai_error'
            ai_detail = _ai._redact(e, 220)   # qué proveedor falló y por qué (sin secretos) → se muestra en el chat
            break
        try:
            kind, payload = parse_step(text)
        except StepParseError as e:
            if not repaired:
                repaired = True
                feedback = (f'tu respuesta anterior no cumplió el protocolo ({e}). Devuelve SOLO un objeto JSON: '
                            '{"tool":...,"args":{...}} o {"final":{"answer":"...","actions":[]}}.')
                continue
            prose = _prose_answer(text)
            if prose and not truncated(prose):
                return done(prose, [])
            reason = 'bad_output'
            break
        if kind == 'final':
            ans = payload.get('answer')
            if leaked(ans) or truncated(ans):   # restos o cortada → el agente la reescribe completa
                reason = 'bad_output'
                break
            return done(ans, payload.get('actions'))
        if force_final:
            reason = 'budget'
            break
        rounds += 1
        progress_phase(req_id, 'tools')
        # ── ejecutar herramientas (en paralelo, con caché por petición) ──
        pending = []
        for c in payload:
            key = c['tool'] + json.dumps(c['args'], sort_keys=True, default=str)
            if key in cache:
                ok, res = cache[key]
                progress_add(req_id, c['tool'], c['args'], state='done' if ok else 'error')
                pending.append((c, None, ok, res, 0, None))
            else:
                h = progress_add(req_id, c['tool'], c['args'])
                pending.append((c, _POOL.submit(execute_tool, c['tool'], c['args'], app, lang), None, None,
                                time.monotonic(), h))
        futs = [p[1] for p in pending if p[1] is not None]
        if futs:
            wait(futs, timeout=max(1.0, min(TOOL_TIMEOUT_S, deadline - time.monotonic() - 2)))
        for c, fut, ok, res, started, h in pending:
            ms = 0
            if fut is not None:
                if fut.done():
                    ok, res = fut.result()
                else:
                    ok, res = False, {'error': 'the data source did not answer in time'}
                ms = int((time.monotonic() - started) * 1000)
                cache[c['tool'] + json.dumps(c['args'], sort_keys=True, default=str)] = (ok, res)
                progress_set(req_id, h, 'done' if ok else 'error')
            results.append((c['tool'], ok, res))
            calls.append((c['tool'], c['args'], ok, res))
            tools_used.append({'name': c['tool'], 'args_summary': _args_summary(c['args']), 'ok': bool(ok),
                               'ms': ms, **({} if ok else {'error': _clip(res.get('error'), 160)})})
            if ok:
                _collect_sources(c['tool'], res, sources, lang)
            scratch.append(f'{c["tool"]}({json.dumps(c["args"], ensure_ascii=False, default=str)}) → '
                           + ('' if ok else 'ERROR: ') + _fmt_result(res))
    # El AGENTE intercede SIEMPRE que haya IA: si el protocolo falló o se acabó el
    # tiempo de rondas, redacta la respuesta en prosa con lo ya consultado. La
    # plantilla sin IA queda solo para cuando la IA no responde de verdad.
    left = min(SYNTH_TIMEOUT_S, deadline + SYNTH_GRACE_S - time.monotonic())
    if reason in ('budget', 'bad_output') and not ai_slow and left >= 6.0:
        progress_phase(req_id, 'writing')
        try:
            ai_calls += 1
            ans, m = synthesize(message, history, lang, context, scratch, left)
            if ans and len(ans) > 20:
                model = m or model
                return done(ans, [])
        except Exception as e:  # noqa: BLE001
            log.warning('khipu_chat: síntesis falló (%s)', _clip(e, 160))
    return fallback(reason or 'budget')


# ════════════════════════════════════════════════════════════════════════════
# endpoints
# ════════════════════════════════════════════════════════════════════════════
@khipu_chat_bp.route('/chat', methods=['POST'])
@rate_limit(40, 300)
def chat_endpoint():
    body = request.get_json(silent=True)
    try:
        req = validate_request(body)
    except ChatValidationError as e:
        return jsonify({'error': e.es, 'error_en': e.en, 'code': 'bad_request'}), 400
    try:
        app = current_app._get_current_object()
    except Exception:  # noqa: BLE001
        app = None
    try:
        out = run_chat(req['message'], req['history'], req['lang'], req['context'], app=app, req_id=req.get('req_id'))
    except Exception as e:  # noqa: BLE001 — nunca un 500 mudo en el chat
        log.exception('khipu_chat: fallo inesperado')
        return jsonify({'error': 'Khipu tuvo un problema procesando eso; reintenta.',
                        'error_en': 'Khipu had a problem processing that; please retry.',
                        'code': 'internal', 'detail': type(e).__name__, 'req_id': req.get('req_id')}), 500
    return jsonify(out)


@khipu_chat_bp.route('/chat/progress/<req_id>', methods=['GET'])
@rate_limit(600, 300)                # su PROPIO límite (no gasta el de /chat): el cliente consulta cada ~0,7 s
def chat_progress_endpoint(req_id):
    """Qué agentes están trabajando en la pregunta `req_id` → {req_id, done, elapsed_ms, phase,
    agents:[{agent, tool, state: working|done|error}]}. Id desconocido o vencido → done:false, agents:[]."""
    rid = valid_req_id(req_id)
    if rid is None:
        return jsonify({'error': 'identificador inválido', 'error_en': 'invalid request id', 'code': 'bad_request'}), 400
    try:
        out = progress_get(rid)
    except Exception:  # noqa: BLE001 — nunca un 500 en una consulta de progreso
        out = {'req_id': rid, 'done': False, 'elapsed_ms': 0, 'phase': None, 'agents': []}
    resp = jsonify(out)
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@khipu_chat_bp.route('/tools', methods=['GET'])
@rate_limit(60, 60)
def tools_endpoint():
    return jsonify({'tools': [{'name': n, 'args': s, 'description': d, 'agent': tool_agent(n)} for n, s, d in tool_catalog()],
                    'actions': sorted(ACTION_SPECS), 'max_steps': MAX_STEPS, 'time_budget_s': TIME_BUDGET_S,
                    'ai_configured': bool(_ai._ai_configured()),
                    'tool_agent': dict(TOOL_AGENT), 'seat_agent': dict(SEAT_AGENT)})

