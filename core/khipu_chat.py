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
import time
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

TABS = ('map', 'market', 'analysis', 'geo', 'simulation', 'space', 'terminal', 'canvas', 'portfolios', 'guia')
PRESETS = ('taiwan_conflict', 'china_chip_ban_total', 'hbm_shortage_2027', 'openai_ipo_impact', 'starshield_reveal')


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
        'IN THEIR OWN VOICE, grounded ONLY in their active research conclusions and evidence. Use it when the user '
        'wants a specific analyst\'s view ("what does the technical analyst think", "pregúntale al de noticias", '
        '"@fundamental"). If the analyst has no research on that company, the answer says so and offers to research.')
def x_ask_agent(seat, question, company):
    from ontology.db import ontology_available as db_ok, session_scope
    from research import ask_agent as aa
    if not db_ok():
        return {'available': False, 'error': 'the research database is not available right now'}
    seat = aa.seat_from_words(str(seat or '')) or str(seat or '').strip().lower()
    with session_scope() as s:
        if seat == 'all':
            r = aa.ask_all(s, str(question or ''), str(company or ''), _PRINCIPAL.get('lang') or 'es')
        else:
            r = aa.ask(s, seat, str(question or ''), str(company or ''), _PRINCIPAL.get('lang') or 'es')
    out = {k: v for k, v in (r or {}).items() if k in ('ok', 'seat', 'emoji', 'name', 'entity', 'label', 'answer', 'n_claims', 'needs_research')}
    if r and r.get('answers'):
        out['answers'] = [{k: a.get(k) for k in ('seat', 'emoji', 'name', 'answer', 'n_claims', 'needs_research')} for a in r['answers']]
    out['source'] = 'Khipus research claims + evidence (Postgres); answer written by the analyst persona (AI)'
    return out


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
                     'market_cap_usd_b': c.get('mcap_b'), 'sector': n.get('sector')})
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
                row['nrs'] = client_nrs(n, deg)
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


def execute_tool(name, args, app=None):
    """→ (ok, result_dict). Nunca lanza."""
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
            res = spec['fn'](**clean)
            if unknown:
                res = dict(res, ignored_arguments=unknown)
            return res
        if name in MCP_READ_TOOLS:
            mt = _mcp()
            return mt.call(name, args, mt.Ctx(principal=_principal()))
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
}
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
    return {'message': msg, 'history': history, 'lang': lang, 'context': ctx}


# ════════════════════════════════════════════════════════════════════════════
# prompt
# ════════════════════════════════════════════════════════════════════════════
def build_system(lang):
    tools = '\n'.join(f'- {n}({sig}): {desc}' for n, sig, desc in tool_catalog())
    idioma = 'inglés' if lang == 'en' else 'español'
    return f"""Eres Khipu, el asistente de inversión de Khipus Finance AI (terminal sobre la cadena de suministro de la \
IA: ~950 empresas y sus relaciones proveedor → cliente, precios en vivo, investigación de analistas, comité). \
Hablas con inversionistas NO expertos: claro, corto y concreto, en {idioma} (o el idioma del usuario).

PROTOCOLO: responde SIEMPRE con UN SOLO objeto JSON válido, sin texto fuera:
  a) consultar: {{"tool":"<nombre>","args":{{...}},"why":"<1 frase>"}}  o varias a la vez (máx. {MAX_CALLS_PER_STEP}): \
{{"calls":[{{"tool":"...","args":{{...}}}}],"why":"..."}}
  b) responder: {{"final":{{"answer":"<respuesta>","actions":[{{"type":"...","arg":...}}]}}}}
Hasta {MAX_STEPS} rondas de consulta; lo normal es UNA.

RECETAS (una ronda): "¿cómo va X?" / "¿qué pasa con X?" → get_company(include_live=true) + get_news juntas. \
"precio / capitalización de X" → get_company. "proveedores / clientes de X" → get_supply_chain. \
"qué piensan los analistas / qué dice el comité" → get_conclusions_board o get_research. "@analista / pregúntale \
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
Acciones de pantalla solo si ayudan (máx. 2) y sin anunciarlas. No menciones el protocolo ni nombres internos.

HERRAMIENTAS:
{tools}
Usa ids de empresa de los resultados (o el nombre exacto)."""


def _fmt_result(res):
    txt = json.dumps(res, ensure_ascii=False, default=str, separators=(',', ':'))
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
    'Eres Khipu, analista senior de Khipus Finance AI. Te doy la PREGUNTA del usuario y los DATOS que ya '
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
    fut = _POOL.submit(_ai_interactive, _ai._ai_complete, SYNTH_SYSTEM, '\n\n'.join(parts), 2200, 'fast',
                       timeout_s=max(5.0, min(float(timeout), 30.0)))
    text, model = fut.result(timeout=max(1.0, timeout))
    t = re.sub(r'^```\w*\s*|\s*```$', '', str(text or '').strip()).strip()
    left = timeout - (time.monotonic() - t0)
    if (leaked(t) or truncated(t)) and left > 8:          # un reintento con el aviso concreto
        fb = ('\n\nTU RESPUESTA ANTERIOR ' + ('QUEDÓ CORTADA' if truncated(t) else 'TENÍA JSON O BORRADORES') +
              '. Escríbela COMPLETA, más corta (máx. 180 palabras), en prosa limpia.')
        fut = _POOL.submit(_ai_interactive, _ai._ai_complete, SYNTH_SYSTEM, '\n\n'.join(parts) + fb, 2200, 'fast',
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
                        + (f' ({"+" if (chg or 0) >= 0 else ""}{_num(chg)} % {"today" if en else "hoy"})'
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


def fallback_answer(message, lang, reason, results, deadline, app=None):
    """Respuesta SIN IA con datos reales. → (answer, actions, extra_results)."""
    en = lang == 'en'
    head = _REASON.get(reason, _REASON['ai_error'])[1 if en else 0]
    companies = [r for (name, ok, r) in results if ok and name == 'get_company']
    extra = []
    if not companies:
        for nid in _entities_in(message)[:2]:
            if time.monotonic() > deadline - 2:
                break
            fut = _POOL.submit(execute_tool, 'get_company', {'id_or_ticker': nid}, app)
            try:
                ok, res = fut.result(timeout=max(1.0, min(14.0, deadline - time.monotonic())))
            except _FutTimeout:
                ok, res = False, {'error': 'timeout'}
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
    def add(label, url=None):
        label = _clip(_friendly_source(label, lang), 120)
        if not label or any(s['label'] == label and s.get('url') == url for s in into):
            return
        if len(into) < 10:
            into.append({'label': label, 'url': url, 'tool': tool_name})
    if not isinstance(res, dict):
        return
    if isinstance(res.get('source'), str):
        add(res['source'])
    elif tool_name == 'get_company':
        add('curated catalog')
    for it in (res.get('items') or res.get('results') or [])[:4] if tool_name in ('get_news', 'web_search') else []:
        if isinstance(it, dict) and it.get('url'):
            add(it.get('outlet') or it.get('title') or it['url'], it['url'])
    lm = res.get('live_market')
    if isinstance(lm, dict) and lm.get('available') and lm.get('source'):
        add(f'{lm["source"]} (live)')
    pv = res.get('private_valuation')
    if isinstance(pv, dict) and pv.get('source_url'):
        add('verified funding round', pv['source_url'])


def _call_ai(system, prompt, timeout):
    # want_json: cada paso es un objeto JSON (parse_step) → con Gemini, JSON estricto y sin pensamiento.
    # timeout_s: el proveedor corta a la vez que el chat (antes el hilo seguía 90 s ocupando cupo).
    # live_facts=False: el bloque "DATOS EN VIVO" se calcula UNA vez por pregunta en _run_chat.
    fut = _POOL.submit(_ai_interactive, _ai._ai_complete, system, prompt, STEP_MAX_TOKENS, 'fast', want_json=True,
                       timeout_s=max(5.0, min(float(timeout), 30.0)), live_facts=False)
    return fut.result(timeout=max(1.0, timeout))


def run_chat(message, history=None, lang='es', context=None, app=None, budget_s=None, max_steps=None):
    """PORTERO (Jev, core/decide.py) en MODO SOMBRA: decide en paralelo qué
    necesita la pregunta y al final se compara con lo que el chat hizo. No
    cambia la respuesta mientras DECIDE_CONTROL no incluya 'chat_gate'."""
    gate = None
    try:
        from core import decide as _decide
        gate = _decide.chat_gate_start(message, lang)
    except Exception:  # noqa: BLE001
        gate = None
    direct = _mention_route(message, history, lang, context)
    out = direct if direct is not None else _run_chat(message, history, lang, context, app, budget_s, max_steps)
    if gate is not None:
        try:
            _decide.chat_gate_finish(gate, out, message)
        except Exception:  # noqa: BLE001
            pass
    return out


def _mention_route(message, history, lang, context):
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
    ents = _entities_in(question) or _entities_in(message)
    if not ents and isinstance(context, dict):
        for k in ('entity', 'company', 'selected'):
            if context.get(k):
                ents = [str(context[k])]
                break
    if not ents:
        # la empresa de la que se venía hablando
        for h in reversed(list(history or [])):
            txt = h.get('content') if isinstance(h, dict) else str(h)
            ents = _entities_in(str(txt or ''))
            if ents:
                break
    meta = aa.seat_meta(seat) if seat != 'all' else {'seat': 'all', 'emoji': '🏛', 'name_es': 'Todos los analistas', 'name_en': 'All analysts'}
    agent = {'seat': seat, 'emoji': meta['emoji'], 'name': meta['name_en'] if lang == 'en' else meta['name_es']}
    base = {'actions': [], 'tools_used': [{'name': 'ask_agent', 'args_summary': seat, 'ok': True}], 'sources': [],
            'model': None, 'answer_source': 'agent', 'ai': True, 'lang': lang, 'steps': 1, 'agent': agent,
            'elapsed_ms': 0, 'as_of': _now_iso()}
    if not ents:
        base['answer'] = ('Which company should I ask about?' if lang == 'en' else '¿Sobre qué empresa quieres que responda?')
        base['ai'] = False
        return base
    from ontology.db import ontology_available as db_ok, session_scope
    if not db_ok():
        base['answer'] = ('The research database is not available right now.' if lang == 'en'
                          else 'La base de investigación no está disponible ahora mismo.')
        base['ai'] = False
        return base
    try:
        with session_scope() as s:
            r = aa.ask_all(s, question, ents[0], lang) if seat == 'all' else aa.ask(s, seat, question, ents[0], lang)
    except Exception as e:  # noqa: BLE001
        log.warning('ask_agent: %s', _clip(e, 160))
        base['answer'] = ('The analyst could not answer right now.' if lang == 'en' else 'El analista no pudo responder ahora mismo.')
        base['ai'] = False
        base['degraded'] = 'ai_error'
        base['ai_detail'] = _ai._redact(e, 200)
        return base
    base['answer'] = str((r or {}).get('answer') or '')[:MAX_ANSWER]
    base['model'] = (r or {}).get('model')
    if (r or {}).get('entity'):
        base['agent']['entity'] = r['entity']
        base['agent']['label'] = r.get('label')
    if (r or {}).get('answers'):
        base['agent']['answers'] = [{k: a.get(k) for k in ('seat', 'emoji', 'name', 'answer')} for a in r['answers']]
    if (r or {}).get('needs_research') and (r or {}).get('entity'):
        base['actions'] = validate_actions([{'type': 'open_research', 'arg': r['entity']}])
    base['elapsed_ms'] = int((time.monotonic() - t0) * 1000)
    return base


def _run_chat(message, history=None, lang='es', context=None, app=None, budget_s=None, max_steps=None):
    t0 = time.monotonic()
    budget = TIME_BUDGET_S if budget_s is None else float(budget_s)
    steps_max = MAX_STEPS if max_steps is None else int(max_steps)
    deadline = t0 + budget
    history = list(history or [])[-MAX_HISTORY:]
    context = context or {}
    scratch, results, tools_used, sources = [], [], [], []
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
        return {'answer': str(answer or '').strip()[:MAX_ANSWER], 'actions': validate_actions(actions),
                'tools_used': tools_used, 'sources': sources, 'model': model if answer_source == 'ai' else None,
                'answer_source': answer_source, 'ai': answer_source == 'ai', 'lang': lang,
                'steps': ai_calls, 'elapsed_ms': int((time.monotonic() - t0) * 1000), 'as_of': _now_iso()}

    def fallback(why):
        ans, acts, extra = fallback_answer(message, lang, why, results, deadline, app)
        for name, args, ok, res in extra:
            tools_used.append({'name': name, 'args_summary': _args_summary(args), 'ok': ok})
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

    system = build_system(lang)
    # DATOS EN VIVO una sola vez por pregunta (antes se recalculaban en cada paso sobre 26k chars)
    live = ''
    try:
        from core.live_facts import live_facts_block
        live = _POOL.submit(live_facts_block, message).result(timeout=3.5) or ''
    except Exception:  # noqa: BLE001
        live = ''
    # PRE-CONSULTA especulativa: la ficha de la(s) empresa(s) mencionada(s) se pide YA, en paralelo
    # con la primera llamada a la IA → la mayoría de preguntas simples se resuelven en UNA ronda
    pre = {}
    for nid in _entities_in(message)[:2]:
        pre[nid] = _POOL.submit(execute_tool, 'get_company', {'id_or_ticker': nid, 'include_live': True}, app)
    if pre:
        wait(list(pre.values()), timeout=min(2.5, max(0.5, deadline - time.monotonic() - 10)))
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
            tools_used.append({'name': 'get_company', 'args_summary': _args_summary({'id_or_ticker': nid}), 'ok': bool(ok),
                               **({} if ok else {'error': _clip(res.get('error'), 160)})})
            if ok:
                _collect_sources('get_company', res, sources, lang)
            scratch.append(f'get_company({json.dumps({"id_or_ticker": nid}, ensure_ascii=False)}) → '
                           + ('' if ok else 'ERROR: ') + _fmt_result(res))
    while True:
        remaining = deadline - time.monotonic()
        if remaining < MIN_STEP_S:
            reason = 'budget'
            break
        force_final = rounds >= steps_max or remaining < FINAL_RESERVE_S
        prompt = build_prompt(message, history, lang, context, scratch, steps_max - rounds, force_final, feedback, live=live)
        feedback = None
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
        # ── ejecutar herramientas (en paralelo, con caché por petición) ──
        pending = []
        for c in payload:
            key = c['tool'] + json.dumps(c['args'], sort_keys=True, default=str)
            if key in cache:
                ok, res = cache[key]
                pending.append((c, None, ok, res, 0))
            else:
                pending.append((c, _POOL.submit(execute_tool, c['tool'], c['args'], app), None, None,
                                time.monotonic()))
        futs = [p[1] for p in pending if p[1] is not None]
        if futs:
            wait(futs, timeout=max(1.0, min(TOOL_TIMEOUT_S, deadline - time.monotonic() - 2)))
        for c, fut, ok, res, started in pending:
            ms = 0
            if fut is not None:
                if fut.done():
                    ok, res = fut.result()
                else:
                    ok, res = False, {'error': 'the data source did not answer in time'}
                ms = int((time.monotonic() - started) * 1000)
                cache[c['tool'] + json.dumps(c['args'], sort_keys=True, default=str)] = (ok, res)
            results.append((c['tool'], ok, res))
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
        out = run_chat(req['message'], req['history'], req['lang'], req['context'], app=app)
    except Exception as e:  # noqa: BLE001 — nunca un 500 mudo en el chat
        log.exception('khipu_chat: fallo inesperado')
        return jsonify({'error': 'Khipu tuvo un problema procesando eso; reintenta.',
                        'error_en': 'Khipu had a problem processing that; please retry.',
                        'code': 'internal', 'detail': type(e).__name__}), 500
    return jsonify(out)


@khipu_chat_bp.route('/tools', methods=['GET'])
@rate_limit(60, 60)
def tools_endpoint():
    return jsonify({'tools': [{'name': n, 'args': s, 'description': d} for n, s, d in tool_catalog()],
                    'actions': sorted(ACTION_SPECS), 'max_steps': MAX_STEPS, 'time_budget_s': TIME_BUDGET_S,
                    'ai_configured': bool(_ai._ai_configured())})

