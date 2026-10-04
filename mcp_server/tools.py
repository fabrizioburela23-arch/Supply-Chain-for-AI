"""mcp_server/tools.py — catálogo de herramientas MCP de Khipus.

Tres alcances (ver auth.py):
  read      consultas: grafo, ficha de empresa, ontología, investigación,
            riesgo de cartera, griegas, eventos mundiales, comité, historial.
  research  lanzar investigación / comité (gasta presupuesto de IA).
  trade     SOLO sobre el cliente de corretaje ligado al token: cuenta,
            posiciones, PROPONER órdenes (preview → cola de aprobación
            humana), estado y cancelación.

Reglas (también en las descripciones que lee el modelo):
  · Nada se inventa: cada resultado trae `source` y `as_of`; lo que no está
    disponible se dice (isError) en vez de rellenarse.
  · Una orden de un agente NUNCA se ejecuta sola: queda «pendiente de
    aprobación humana» en Khipus (👥 Clientes → Aprobaciones), salvo
    BROKERAGE_AUTO_APPROVE_PAPER=on con un cliente de PAPEL.
  · Dependencias opcionales (brokerage, comité, world, base de datos) se
    importan de forma perezosa: si faltan → error claro, nunca un crash.
"""
import importlib
import json
import logging
import math
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as _FutTimeout
from dataclasses import dataclass, field
from datetime import datetime, timezone

from mcp_server import auth as _auth

log = logging.getLogger('khipu')

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SNAPSHOT = os.path.join(_ROOT, 'data', 'grafo_v0.json')
_PRIVATE_VAL = os.path.join(_ROOT, 'nodes', 'private_valuations.js')
_POOL = ThreadPoolExecutor(max_workers=6, thread_name_prefix='mcp-tool')

APPROVAL_PLACE_ES = '👥 Clientes → Aprobaciones'
DISCLAIMER_EN = ('Informational research, not investment advice. Orders proposed by an AI agent are only '
                 'executed after explicit human approval in Khipus.')


# ════════════════════════════════════════════════════════════════════════════
# errores
# ════════════════════════════════════════════════════════════════════════════
class ToolError(Exception):
    """Error de EJECUCIÓN de la herramienta → resultado con isError: true."""

    def __init__(self, message, code='error', data=None):
        super().__init__(message)
        self.message = str(message)
        self.code = code
        self.data = data or {}

    def payload(self):
        d = {'error': self.message, 'code': self.code}
        d.update(self.data)
        return d


class InvalidParams(Exception):
    """Argumentos que no cumplen el inputSchema → JSON-RPC -32602."""


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


# ════════════════════════════════════════════════════════════════════════════
# registro + validación mínima de JSON Schema
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class Tool:
    name: str
    title: str
    scope: str
    description: str
    input_schema: dict
    handler: object
    annotations: dict = field(default_factory=dict)

    def describe(self):
        return {'name': self.name, 'title': self.title, 'description': self.description,
                'inputSchema': self.input_schema, 'annotations': dict(self.annotations, title=self.title)}


REGISTRY = {}


def tool(name, title, scope, description, properties=None, required=None, read_only=True,
         destructive=False, idempotent=True, open_world=False):
    schema = {'type': 'object', 'properties': properties or {}, 'additionalProperties': False}
    if required:
        schema['required'] = list(required)

    def deco(fn):
        REGISTRY[name] = Tool(name=name, title=title, scope=scope, description=description,
                              input_schema=schema, handler=fn,
                              annotations={'readOnlyHint': read_only, 'destructiveHint': destructive,
                                           'idempotentHint': idempotent, 'openWorldHint': open_world})
        return fn
    return deco


_TYPES = {'string': str, 'boolean': bool, 'object': dict, 'array': list}


def _coerce(schema, v, path):
    t = schema.get('type')
    if t == 'integer':
        if isinstance(v, bool):
            raise InvalidParams(f'{path}: expected integer')
        if isinstance(v, str) and re.fullmatch(r'-?\d+', v.strip()):
            v = int(v.strip())
        if isinstance(v, float) and math.isfinite(v) and v.is_integer():
            v = int(v)
        if not isinstance(v, int):
            raise InvalidParams(f'{path}: expected integer')
    elif t == 'number':
        if isinstance(v, bool):
            raise InvalidParams(f'{path}: expected number')
        if isinstance(v, str):
            try:
                v = float(v.strip())
            except ValueError:
                raise InvalidParams(f'{path}: expected number') from None
        if not isinstance(v, (int, float)) or not math.isfinite(v):
            raise InvalidParams(f'{path}: expected a finite number')
    elif t in _TYPES:
        if not isinstance(v, _TYPES[t]):
            raise InvalidParams(f'{path}: expected {t}')
    if 'enum' in schema:
        vv = v.upper() if isinstance(v, str) and all(isinstance(e, str) and e.isupper() for e in schema['enum']) else v
        vv = vv.lower() if isinstance(vv, str) and all(isinstance(e, str) and e.islower() for e in schema['enum']) else vv
        if vv not in schema['enum']:
            raise InvalidParams(f'{path}: must be one of {schema["enum"]}')
        v = vv
    if t in ('integer', 'number'):
        if 'minimum' in schema and v < schema['minimum']:
            raise InvalidParams(f'{path}: must be ≥ {schema["minimum"]}')
        if 'maximum' in schema and v > schema['maximum']:
            raise InvalidParams(f'{path}: must be ≤ {schema["maximum"]}')
        if 'exclusiveMinimum' in schema and v <= schema['exclusiveMinimum']:
            raise InvalidParams(f'{path}: must be > {schema["exclusiveMinimum"]}')
    if t == 'string':
        if 'maxLength' in schema and len(v) > schema['maxLength']:
            raise InvalidParams(f'{path}: longer than {schema["maxLength"]} characters')
        if len(v.strip()) < schema.get('minLength', 0):
            raise InvalidParams(f'{path}: shorter than {schema["minLength"]} characters')
    if t == 'array':
        if 'maxItems' in schema and len(v) > schema['maxItems']:
            raise InvalidParams(f'{path}: more than {schema["maxItems"]} items')
        if 'minItems' in schema and len(v) < schema['minItems']:
            raise InvalidParams(f'{path}: fewer than {schema["minItems"]} items')
        if 'items' in schema:
            v = [_coerce(schema['items'], x, f'{path}[{i}]') for i, x in enumerate(v)]
    if t == 'object' and 'properties' in schema:
        v = validate(schema, v, path)
    return v


def validate(schema, args, path='arguments'):
    if args is None:
        args = {}
    if not isinstance(args, dict):
        raise InvalidParams(f'{path}: expected object')
    props = schema.get('properties') or {}
    out = {}
    for k in schema.get('required') or []:
        if k not in args or args[k] is None or (isinstance(args[k], str) and not args[k].strip()):
            raise InvalidParams(f'{path}.{k} is required')
    for k, v in args.items():
        if k not in props:
            if schema.get('additionalProperties') is False:
                raise InvalidParams(f'{path}: unknown argument "{k}" (allowed: {", ".join(props) or "none"})')
            continue
        if v is None:
            continue
        out[k] = _coerce(props[k], v, f'{path}.{k}')
    return out


# ════════════════════════════════════════════════════════════════════════════
# contexto de llamada
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class Ctx:
    principal: object
    session_id: str = None
    ip: str = None
    protocol_version: str = None


def visible_tools(principal):
    out = []
    for t in REGISTRY.values():
        if not principal.has(t.scope):
            continue
        if t.scope == 'trade' and (not principal.client_id or not trading_enabled()):
            continue
        out.append(t)
    return out


def trading_enabled():
    return os.getenv('MCP_TRADING_ENABLED', 'on').strip().lower() not in ('off', '0', 'false', 'no')


def call(name, args, ctx):
    """→ dict (éxito). Lanza ToolError (isError) o InvalidParams (-32602)."""
    t = REGISTRY.get(name)
    if t is None:
        raise KeyError(name)
    p = ctx.principal
    if not p.has(t.scope):
        raise ToolError(f"insufficient scope: this token lacks the '{t.scope}' scope required by {name}. "
                        'Create a token with that scope in Khipus (🩺 Sistema → 🤖 Conectar IAs).',
                        code='insufficient_scope')
    lim = _auth.limits()
    if t.scope == 'research' and not _auth.allow(p, 'research', lim['research_per_hour'], 3600):
        raise ToolError('rate limit: too many research runs this hour for this token', code='rate_limited')
    if t.scope == 'trade' and name in ('preview_order', 'submit_order', 'cancel_order') \
            and not _auth.allow(p, 'trade', lim['trade_per_hour'], 3600):
        raise ToolError('rate limit: too many trading actions this hour for this token', code='rate_limited')
    clean = validate(t.input_schema, args or {})
    res = t.handler(ctx, **clean)
    if not isinstance(res, dict):
        res = {'result': res}
    return res


def _bounded(fn, timeout, *a, **kw):
    fut = _POOL.submit(fn, *a, **kw)
    try:
        return fut.result(timeout=timeout)
    except _FutTimeout:
        raise ToolError(f'upstream data source did not answer within {timeout:.0f}s — try again later',
                        code='timeout') from None


# ════════════════════════════════════════════════════════════════════════════
# datos del grafo (snapshot canónico data/grafo_v0.json)
# ════════════════════════════════════════════════════════════════════════════
_SNAP = {'data': None}
_SNAP_LOCK = threading.Lock()


def _snapshot():
    if _SNAP['data'] is not None:
        return _SNAP['data']
    with _SNAP_LOCK:
        if _SNAP['data'] is not None:
            return _SNAP['data']
        with open(_SNAPSHOT, encoding='utf-8') as fh:
            snap = json.load(fh)
        nodes = {n['id']: n for n in snap.get('nodes') or [] if n.get('id')}
        out_e, in_e, deg = {}, {}, {}
        for lk in snap.get('links') or []:
            s, t = lk.get('source'), lk.get('target')
            if s not in nodes or t not in nodes:
                continue
            e = {'source': s, 'target': t, 'w': lk.get('w'), 'rel': lk.get('rel'), 'type': lk.get('type')}
            out_e.setdefault(s, []).append(e)
            in_e.setdefault(t, []).append(e)
            deg[s] = deg.get(s, 0) + 1
            if t != s:
                deg[t] = deg.get(t, 0) + 1
        _SNAP['data'] = {'nodes': nodes, 'out': out_e, 'in': in_e, 'deg': deg,
                         'sectors': snap.get('sectors9') or {}, 'cats': snap.get('categories') or {},
                         'preipo': snap.get('preipo_intel') or {}, 'as_of': snap.get('exported_at'),
                         'counts': snap.get('counts') or {}}
        return _SNAP['data']


_PV = {'data': None}


def _private_valuations():
    """nodes/private_valuations.js (GENERADO, verificado con fuente) → dict."""
    if _PV['data'] is not None:
        return _PV['data']
    data = {'as_of': None, 'entries': {}}
    try:
        with open(_PRIVATE_VAL, encoding='utf-8') as fh:
            txt = fh.read()
        i = txt.index('window.PRIVATE_VALUATIONS')
        j = txt.index('{', i)
        obj, _end = json.JSONDecoder().raw_decode(txt[j:])
        if isinstance(obj, dict):
            data = {'as_of': obj.get('as_of'), 'entries': obj.get('entries') or {}}
    except Exception as e:  # noqa: BLE001
        log.warning('mcp: private_valuations no disponible: %s', type(e).__name__)
    _PV['data'] = data
    return data


SNAPSHOT_SOURCE = 'Khipus supply-chain graph snapshot (data/grafo_v0.json, curated catalog)'


def _resolve(text, umbral=60):
    from core.entities import resolve
    return resolve(str(text or '')[:120], umbral=umbral)


def _resolve_or_fail(text):
    r = _resolve(text)
    if not r:
        sug = [x['id'] for x in _search(text, 3)]
        raise ToolError(f'entity not found in the Khipus graph: "{str(text)[:80]}"', code='not_found',
                        data={'suggestions': sug, 'hint': 'use search_companies first'})
    return r


def _listed(n):
    st = (n.get('listing') or {}).get('status')
    return bool(n.get('mkt')) and st not in ('acquired', 'merged', 'subsidiary', 'private', 'bankrupt', 'delisted')


def _brief(n, deg=None):
    snap = _snapshot()
    sec = snap['sectors'].get(n.get('sector')) or {}
    return {'id': n['id'], 'label': n.get('label') or n['id'], 'symbol': n.get('mkt') or None,
            'listed': _listed(n), 'preipo': bool(n.get('preipo')), 'sector': n.get('sector'),
            'sector_label': sec.get('en') or sec.get('label'), 'category': n.get('cat'),
            'country': n.get('country'), 'degree': snap['deg'].get(n['id'], 0) if deg is None else deg}


def _search(query, limit=10):
    from core.entities import get_index, norm
    q = str(query or '').strip()
    n = norm(q)
    if not n:
        return []
    snap = _snapshot()
    idx = get_index()
    cands = {}

    def add(nid, score, method):
        if nid in snap['nodes'] and score > cands.get(nid, (0, ''))[0]:
            cands[nid] = (score, method)
    top = _resolve(q, umbral=60)
    if top:
        add(top['id'], top['score'], top['method'])
    up = q.upper()
    for alias, nid in idx['por_alias'].items():
        if alias == n:
            add(nid, 92, 'alias')
        elif len(n) >= 3 and alias.startswith(n):
            add(nid, 78, 'alias_prefix')
    for nid, node in snap['nodes'].items():
        lab = norm(node.get('label') or '')
        sym = (node.get('mkt') or '').upper()
        if sym and sym == up:
            add(nid, 98, 'ticker')
        elif lab == n:
            add(nid, 95, 'label')
        elif lab.startswith(n):
            add(nid, 75, 'prefix')
        elif norm(nid).startswith(n):
            add(nid, 72, 'id_prefix')
        elif len(n) >= 3 and re.search(r'(^|\s)' + re.escape(n), lab):
            add(nid, 66, 'word')
        elif len(n) >= 3 and n in lab:
            add(nid, 60, 'substring')
        elif len(n) >= 4:
            desc = norm(' '.join(str(node.get(k) or '') for k in ('role_en', 'supplies_en', 'role', 'supplies')))
            if n in desc:
                add(nid, 40, 'description')
    ranked = sorted(cands.items(), key=lambda kv: (-kv[1][0], -snap['deg'].get(kv[0], 0), kv[0]))
    out = []
    for nid, (score, method) in ranked[:limit]:
        b = _brief(snap['nodes'][nid])
        b['match'] = {'score': score, 'method': method}
        out.append(b)
    return out


def _edges(nid, direction, min_w=0.0):
    snap = _snapshot()
    lst = snap['in'].get(nid, []) if direction == 'up' else snap['out'].get(nid, [])
    out = [e for e in lst if (e.get('w') or 0) >= min_w]
    out.sort(key=lambda e: (-(e.get('w') or 0), e['source'], e['target']))
    return out


def _nrs(nid, node):
    """NRS del servidor (ontología) si existe el objeto; si no, la MISMA fórmula
    que la app (computeNRS) sobre el catálogo."""
    expl = ('Network Risk Score 0-100 (higher = more fragile position in the AI supply chain): country/geo '
            'risk + graph centrality + margin + fundamentals + concentration. A heuristic, not a forecast.')
    if _auth.db_available():
        try:
            from ontology.agents import _compute_server_nrs
            from ontology.db import session_scope
            from ontology.models import ObjectRecord
            with session_scope() as s:
                obj = s.get(ObjectRecord, nid)
                if obj is not None:
                    return {'value': _compute_server_nrs(s, obj), 'method': 'server (ontology links, margin clamped)',
                            'explain': expl}
        except Exception as e:  # noqa: BLE001
            log.info('mcp nrs server: %s', type(e).__name__)
    try:
        from core.world import client_nrs
        return {'value': client_nrs(node, _snapshot()['deg'].get(nid, 0)),
                'method': 'catalog formula (same as the app computeNRS)', 'explain': expl}
    except Exception as e:  # noqa: BLE001
        return {'value': None, 'method': 'unavailable', 'error': type(e).__name__, 'explain': expl}


def _live_profile(symbol):
    from core.company_data import get_live_profile
    return get_live_profile(symbol)


# ════════════════════════════════════════════════════════════════════════════
# READ — grafo y empresas
# ════════════════════════════════════════════════════════════════════════════
@tool('search_companies', 'Search companies in the Khipus graph', 'read',
      'Find companies/entities in the Khipus AI supply-chain graph (949 curated nodes: chips, foundries, '
      'memory, cloud, AI labs, energy, materials, logistics…) by name, ticker, alias or keyword. Returns ids to '
      'use with the other tools. Data comes from the curated Khipus catalog; it never guesses.',
      {'query': {'type': 'string', 'description': 'Name, ticker, alias or keyword (e.g. "TSMC", "NVDA", "HBM").',
                 'maxLength': 120, 'minLength': 1},
       'limit': {'type': 'integer', 'minimum': 1, 'maximum': 25, 'default': 10}},
      required=['query'])
def t_search_companies(ctx, query, limit=10):
    res = _search(query, limit)
    return {'query': query, 'count': len(res), 'results': res, 'source': SNAPSHOT_SOURCE,
            'as_of': _snapshot()['as_of']}


@tool('get_company', 'Company profile (catalog + live market data + risk)', 'read',
      'Full profile of one company: curated role/moat/supply description, verified listing status, verified '
      'private valuation (for private companies: last CLOSED round with source URL — not a live price), LIVE '
      'market profile for listed companies (price, market cap… from Yahoo/Finnhub, with as_of), Network Risk '
      'Score, and its top suppliers and customers in the graph. Fields are labeled with their source.',
      {'id_or_ticker': {'type': 'string', 'description': 'Graph id, ticker or name (e.g. "Nvidia", "TSM").',
                        'maxLength': 120, 'minLength': 1},
       'include_live': {'type': 'boolean', 'default': True,
                        'description': 'Fetch the live market profile (slower, network).'}},
      required=['id_or_ticker'], open_world=True)
def t_get_company(ctx, id_or_ticker, include_live=True):
    r = _resolve_or_fail(id_or_ticker)
    snap = _snapshot()
    nid = r['id']
    n = snap['nodes'].get(nid) or {}
    out = {'id': nid, 'label': n.get('label') or nid, 'resolved_from': {'text': id_or_ticker, 'method': r['method'],
                                                                        'score': r['score']}}
    out.update({k: v for k, v in _brief(n).items() if k not in ('id', 'label')})
    out['catalog'] = {
        'source': SNAPSHOT_SOURCE + ' — descriptive text curated by Khipus; figures inside may be approximate',
        'as_of': snap['as_of'], 'ticker_text': n.get('ticker'), 'location': n.get('loc'),
        'role': n.get('role_en') or n.get('role'), 'supplies': n.get('supplies_en') or n.get('supplies'),
        'moat_and_risks': n.get('moat_en') or n.get('moat'), 'growth_note': n.get('growth_en') or n.get('growth'),
        'operating_margin': n.get('margin'), 'capex_2026_note': n.get('capex_2026_en') or n.get('capex_2026'),
        'backlog_note': n.get('backlog_status_en') or n.get('backlog_status')}
    if n.get('listing'):
        out['listing_status'] = dict(n['listing'], source='verified listing status (nodes/listing_status.js)')
    pv = _private_valuations()
    e = (pv.get('entries') or {}).get(nid)
    if e:
        out['private_valuation'] = {
            'valuation_usd_b': e.get('valuation_usd_b'), 'as_of': e.get('as_of'), 'round': e.get('round'),
            'lead': e.get('lead'), 'raised': e.get('raised'), 'note': e.get('note_en') or e.get('note_es'),
            'source_url': e.get('source_url'), 'confidence': e.get('confidence'),
            'in_talks_usd_b': e.get('talks_usd_b'), 'talks_note': e.get('talks_note_en') or e.get('talks_note_es'),
            'talks_source_url': e.get('talks_source_url'),
            'kind': 'last CLOSED funding round, verified with source — NOT a live price',
            'layer_as_of': pv.get('as_of')}
    pre = snap['preipo'].get(nid)
    if pre:
        out['preipo_catalog'] = {k: v for k, v in pre.items() if k != 'valuation'}
        out['preipo_catalog']['source'] = 'Khipus catalog (nodes/preipo_intel.js) — curated, not live'
    sym = n.get('mkt')
    if include_live and sym and _listed(n):
        try:
            prof = _bounded(_live_profile, 12, sym)
            out['live_market'] = prof if prof.get('available') else {
                'available': False, 'symbol': sym, 'reason': prof.get('reason_en') or prof.get('reason')}
        except ToolError as te:
            out['live_market'] = {'available': False, 'symbol': sym, 'reason': te.message}
    elif sym and not include_live:
        out['live_market'] = {'available': False, 'symbol': sym, 'reason': 'not requested (include_live=false)'}
    else:
        out['live_market'] = {'available': False, 'reason': 'not a listed company (no exchange price exists)'}
    out['network_risk_score'] = _nrs(nid, n)
    ups, downs = _edges(nid, 'up'), _edges(nid, 'down')
    nodes = snap['nodes']
    out['top_suppliers'] = [{'id': x['source'], 'label': (nodes.get(x['source']) or {}).get('label'), 'weight': x['w'],
                             'relation': x['rel'], 'type': x['type']} for x in ups[:10]]
    out['top_customers'] = [{'id': x['target'], 'label': (nodes.get(x['target']) or {}).get('label'), 'weight': x['w'],
                             'relation': x['rel'], 'type': x['type']} for x in downs[:10]]
    out['counts'] = {'suppliers': len(ups), 'customers': len(downs)}
    out['as_of'] = _now_iso()
    out['sources'] = ['Khipus graph snapshot', 'nodes/private_valuations.js (verified)',
                      'live profile: ' + str((out.get('live_market') or {}).get('source') or 'n/a')]
    return out


@tool('get_supply_chain', 'Supply-chain neighborhood', 'read',
      'Suppliers (direction "up"), customers ("down") or both of a company in the Khipus graph, up to 2 hops. '
      'Edge convention: source SUPPLIES target; weight w (1-3+) is the dependency strength curated by Khipus.',
      {'id': {'type': 'string', 'maxLength': 120, 'minLength': 1, 'description': 'Graph id, ticker or name.'},
       'direction': {'type': 'string', 'enum': ['up', 'down', 'both'], 'default': 'both'},
       'depth': {'type': 'integer', 'minimum': 1, 'maximum': 2, 'default': 1},
       'min_weight': {'type': 'number', 'minimum': 0, 'maximum': 10, 'default': 0},
       'limit': {'type': 'integer', 'minimum': 1, 'maximum': 60, 'default': 25,
                 'description': 'Max neighbors per node and direction.'}},
      required=['id'])
def t_get_supply_chain(ctx, id, direction='both', depth=1, min_weight=0, limit=25):  # noqa: A002
    r = _resolve_or_fail(id)
    snap = _snapshot()
    root = r['id']
    dirs = ['up', 'down'] if direction == 'both' else [direction]
    seen = {root: 0}
    edges, ekeys = [], set()
    frontier = [(root, d) for d in dirs]
    truncated = False
    for hop in range(1, depth + 1):
        nxt = []
        for nid, d in frontier:
            lst = _edges(nid, d, float(min_weight or 0))
            if len(lst) > limit:
                truncated = True
            for e in lst[:limit]:
                other = e['source'] if d == 'up' else e['target']
                k = (e['source'], e['target'], e['type'])
                if k not in ekeys:
                    ekeys.add(k)
                    edges.append(dict(e, hop=hop, direction=d))
                if other not in seen:
                    seen[other] = hop
                    nxt.append((other, d))
            if len(edges) >= 400:
                truncated = True
                break
        frontier = nxt
    nodes = []
    for nid, hop in seen.items():
        b = _brief(snap['nodes'][nid])
        b['hop'] = hop
        nodes.append(b)
    nodes.sort(key=lambda b: (b['hop'], -b['degree']))
    return {'root': root, 'label': (snap['nodes'].get(root) or {}).get('label'), 'direction': direction,
            'depth': depth, 'min_weight': min_weight, 'nodes': nodes, 'edges': edges, 'truncated': truncated,
            'convention': 'edge source SUPPLIES target', 'source': SNAPSHOT_SOURCE, 'as_of': snap['as_of']}


# ════════════════════════════════════════════════════════════════════════════
# READ — ontología (Postgres) e investigación
# ════════════════════════════════════════════════════════════════════════════
def _need_db(what='this tool'):
    if not _auth.db_available():
        raise ToolError(f'{what} needs the Khipus ontology database (DATABASE_URL), which is not configured '
                        'on this server', code='unavailable')


def _iso(d):
    return d.isoformat() if d else None


@tool('get_ontology_object', 'Ontology object (bitemporal)', 'read',
      'An object of the Khipus ontology (Postgres, event-sourced): current properties, its most recent events '
      '(what changed, when it was valid, when it was recorded, by whom), active links and the provenance '
      'sources (documents with trust score) that back it.',
      {'id': {'type': 'string', 'maxLength': 120, 'minLength': 1, 'description': 'Object id, ticker or name.'},
       'events_limit': {'type': 'integer', 'minimum': 1, 'maximum': 50, 'default': 15}},
      required=['id'])
def t_get_ontology_object(ctx, id, events_limit=15):  # noqa: A002
    _need_db('get_ontology_object')
    from sqlalchemy import or_, select

    from ontology.db import session_scope
    from ontology.models import Event, LinkRecord, ObjectRecord
    with session_scope() as s:
        o = s.get(ObjectRecord, str(id)[:120])
        if o is None:
            r = _resolve(id)
            o = s.get(ObjectRecord, r['id']) if r else None
        if o is None:
            raise ToolError(f'object not found in the ontology: "{str(id)[:80]}"', code='not_found')
        evs = s.scalars(select(Event).where(or_(Event.object_id == o.id, Event.target_id == o.id))
                        .order_by(Event.recorded_at.desc()).limit(events_limit)).all()
        links = s.scalars(select(LinkRecord).where(or_(LinkRecord.source_id == o.id, LinkRecord.target_id == o.id),
                                                   LinkRecord.valid_to.is_(None)).limit(200)).all()
        try:
            from ontology.provenance import provenance_for_object
            prov = provenance_for_object(s, o.id, limit=20)
        except Exception as e:  # noqa: BLE001
            prov = {'error': type(e).__name__}
        props = dict(o.properties or {})
        return {
            'object': {'id': o.id, 'type': o.type, 'label': o.label, 'properties': props,
                       'created_at': _iso(o.created_at), 'updated_at': _iso(o.updated_at)},
            'recent_events': [{'id': str(e.id), 'event_type': e.event_type, 'object_id': e.object_id,
                               'target_id': e.target_id, 'payload': e.payload, 'valid_from': _iso(e.valid_from),
                               'valid_to': _iso(e.valid_to), 'recorded_at': _iso(e.recorded_at),
                               'channel': e.source, 'actor': e.actor, 'source_id': e.source_id,
                               'confidence': e.confidence} for e in evs],
            'active_links': {
                'outgoing': [{'target': lk.target_id, 'rel_type': lk.rel_type, 'weight': lk.weight,
                              'valid_from': _iso(lk.valid_from)} for lk in links if lk.source_id == o.id][:40],
                'incoming': [{'source': lk.source_id, 'rel_type': lk.rel_type, 'weight': lk.weight,
                              'valid_from': _iso(lk.valid_from)} for lk in links if lk.target_id == o.id][:40],
                'total': len(links)},
            'provenance': prov,
            'source': 'Khipus ontology (Postgres, append-only events)', 'as_of': _now_iso()}


def _claim_brief(c, n_sup=0, n_cnt=0):
    return {'claim_id': c.id, 'agent_type': c.agent_type, 'topic': c.topic, 'stance': c.stance,
            'claim_type': c.claim_type, 'statement': c.statement_en or c.statement_es,
            'statement_es': c.statement_es, 'horizon': c.horizon, 'confidence': c.confidence,
            'status': c.status, 'falsifiers': c.falsifiers, 'n_supporting': n_sup, 'n_counter': n_cnt,
            'created_at': _iso(c.created_at), 'valid_to': _iso(c.valid_to), 'model': c.model}


def _unsupported_money(session, c, ev=None):
    """¿La claim cita cifras de dinero que NO están en su evidencia? (mismo
    criterio que research.runner.retract_unsupported, sin modificar nada)."""
    try:
        from core.numbers import evidence_numbers, unsupported_money

        from research.models import ResearchEvidence
        txt = ' '.join(filter(None, [c.statement_es, c.statement_en, c.reasoning_summary, c.object]))
        if not txt or not re.search(r'\d', txt):
            return False
        if ev is None:
            ev = session.query(ResearchEvidence).filter(ResearchEvidence.claim_id == c.id).all()
        vals = evidence_numbers([{'title': e.title, 'excerpt': e.excerpt} for e in ev])
        return bool(unsupported_money(txt, vals))
    except Exception:  # noqa: BLE001
        return False


@tool('get_research', 'Research claims on an entity', 'read',
      'Active research claims produced by the Khipus agent swarm on an entity (fundamental, news, technical, '
      'supply_chain… agents): each with stance, horizon, CALCULATED confidence, falsifiers and evidence counts; '
      'plus contradictions between agents and the last synthesis. Claims whose money figures are not backed by '
      'their own evidence are withheld. Use get_claim_evidence for the "why".',
      {'entity': {'type': 'string', 'maxLength': 120, 'minLength': 1, 'description': 'Graph id, ticker or name.'},
       'limit': {'type': 'integer', 'minimum': 1, 'maximum': 60, 'default': 30}},
      required=['entity'])
def t_get_research(ctx, entity, limit=30):
    _need_db('get_research')
    r = _resolve(entity)
    eid = r['id'] if r else str(entity)[:120]
    from sqlalchemy import func

    from ontology.db import session_scope
    from research.models import ClaimRelation, ResearchClaim, ResearchEvidence, ResearchJob
    with session_scope() as s:
        claims = (s.query(ResearchClaim).filter(ResearchClaim.subject_entity_id == eid,
                                                ResearchClaim.status == 'active')
                  .order_by(ResearchClaim.created_at.desc()).limit(limit).all())
        withheld = [c.id for c in claims if _unsupported_money(s, c)]
        claims = [c for c in claims if c.id not in withheld]
        ids = [c.id for c in claims]
        counts = {}
        if ids:
            for cid, st, n in (s.query(ResearchEvidence.claim_id, ResearchEvidence.stance, func.count())
                               .filter(ResearchEvidence.claim_id.in_(ids))
                               .group_by(ResearchEvidence.claim_id, ResearchEvidence.stance).all()):
                counts.setdefault(cid, {})[st] = n
        rels = (s.query(ClaimRelation).filter(ClaimRelation.claim_a.in_(ids) | ClaimRelation.claim_b.in_(ids)).all()
                if ids else [])
        last = (s.query(ResearchJob).filter(ResearchJob.entity_id == eid)
                .order_by(ResearchJob.created_at.desc()).first())
        by_agent = {}
        for c in claims:
            by_agent.setdefault(c.agent_type, []).append(
                _claim_brief(c, counts.get(c.id, {}).get('supporting', 0), counts.get(c.id, {}).get('counter', 0)))
        last_job = None
        if last:
            cov = _job_coverage(s, last)
            last_job = {'job_id': last.id, 'status': last.status, 'created_at': _iso(last.created_at),
                        'completed_at': _iso(last.completed_at), 'synthesis': last.synthesis,
                        'coverage': cov, 'error': last.error}
            if cov and not cov.get('complete'):
                last_job['hint'] = (f"coverage incomplete: {cov['n_done']} of {cov['n_effective']} agents answered, "
                                    f"missing {', '.join(cov['missing'])}. Treat the synthesis as partial; "
                                    "run_research(entity, only_missing=true) completes the missing agents.")
        return {'entity_id': eid, 'label': (r or {}).get('label', eid), 'n_claims': len(claims),
                'claims_by_agent': by_agent,
                'contradictions': [{'claim_a': x.claim_a, 'claim_b': x.claim_b, 'type': x.rel_type,
                                    'reason': x.reason} for x in rels],
                'withheld_unsupported_figures': len(withheld),
                'last_job': last_job,
                'hint': (None if claims else 'no active research yet — run_research (research scope) can start one'),
                'source': 'Khipus research swarm (research_claims, Postgres)', 'as_of': _now_iso(),
                'disclaimer': DISCLAIMER_EN}


@tool('get_claim_evidence', 'Why? — evidence behind a claim', 'read',
      'The full "why" of one research claim: reasoning summary, supporting and counter evidence (with source '
      'URL/reference, publication date and reliability), affected entities, contradicting claims and the agent '
      'run that produced it (model, provider, time).',
      {'claim_id': {'type': 'string', 'maxLength': 40, 'minLength': 1}},
      required=['claim_id'])
def t_get_claim_evidence(ctx, claim_id):
    _need_db('get_claim_evidence')
    from ontology.db import session_scope
    from research.models import AgentRun, ClaimRelation, ResearchClaim, ResearchEvidence
    with session_scope() as s:
        c = s.get(ResearchClaim, str(claim_id)[:40])
        if not c:
            raise ToolError('claim not found', code='not_found')
        ev = s.query(ResearchEvidence).filter(ResearchEvidence.claim_id == c.id).all()
        srcs = {}
        sids = [e.source_id for e in ev if e.source_id]
        if sids:
            try:
                from ontology.models import ObjectRecord
                from ontology.provenance import source_to_dict
                srcs = {o.id: source_to_dict(o) for o in s.query(ObjectRecord).filter(ObjectRecord.id.in_(sids)).all()}
            except Exception:  # noqa: BLE001
                srcs = {}

        def ed(e):
            return {'ref': e.context_ref, 'source_type': e.source_type, 'source_reference': e.source_reference,
                    'title': e.title, 'excerpt': e.excerpt, 'published_at': _iso(e.published_at),
                    'retrieved_at': _iso(e.retrieved_at), 'reliability': e.reliability,
                    'source': srcs.get(e.source_id)}
        run = s.get(AgentRun, c.run_id) if c.run_id else None
        rels = s.query(ClaimRelation).filter((ClaimRelation.claim_a == c.id) | (ClaimRelation.claim_b == c.id)).all()
        out = _claim_brief(c, sum(1 for e in ev if e.stance == 'supporting'), sum(1 for e in ev if e.stance == 'counter'))
        out.update({
            'subject_entity_id': c.subject_entity_id, 'predicate': c.predicate, 'object': c.object,
            'confidence_components': c.confidence_components, 'reasoning_summary': c.reasoning_summary,
            'affected_entity_ids': c.affected_entity_ids,
            'unsupported_money_figures': _unsupported_money(s, c, ev),
            'supporting': [ed(e) for e in ev if e.stance == 'supporting'],
            'counter': [ed(e) for e in ev if e.stance == 'counter'],
            'contradicts': [{'claim_id': (x.claim_b if x.claim_a == c.id else x.claim_a), 'reason': x.reason,
                             'type': x.rel_type} for x in rels],
            'run': ({'run_id': run.id, 'agent_type': run.agent_type, 'model': run.model, 'provider': run.provider,
                     'status': run.status, 'started_at': _iso(run.started_at),
                     'completed_at': _iso(run.completed_at)} if run else None),
            'source': 'Khipus research swarm (research_claims + research_evidence)', 'as_of': _now_iso()})
        return out


def _job_coverage(session, job):
    """R4: cobertura guardada (terminado) o en vivo (en curso); None si el runner no está."""
    try:
        syn = job.synthesis if isinstance(job.synthesis, dict) else None
        if syn and syn.get('coverage'):
            return syn['coverage']
        from research.runner import job_coverage
        return job_coverage(session, job)
    except Exception:  # noqa: BLE001
        return None


@tool('get_research_job', 'Research job status', 'read',
      'Status of a research job started with run_research: queued/running/done/partial/failed, per-agent runs, '
      'coverage (which agents answered), number of claims produced and the synthesis when done. '
      '`partial` = some agents did not answer: the synthesis is incomplete.',
      {'job_id': {'type': 'string', 'maxLength': 40, 'minLength': 1}},
      required=['job_id'])
def t_get_research_job(ctx, job_id):
    _need_db('get_research_job')
    from ontology.db import session_scope
    from research.models import AgentRun, ResearchClaim, ResearchJob
    with session_scope() as s:
        j = s.get(ResearchJob, str(job_id)[:40])
        if not j:
            raise ToolError('research job not found', code='not_found')
        runs = s.query(AgentRun).filter(AgentRun.job_id == j.id).order_by(AgentRun.started_at).all()
        n_claims = s.query(ResearchClaim).filter(ResearchClaim.job_id == j.id).count()
        try:   # R3: posición en la cola (campos nuevos; el contrato no cambia)
            from research.runner import queue_position, research_queue_state
            qpos, qs = (queue_position(j.id) if j.status == 'queued' else None), research_queue_state()
        except Exception:  # noqa: BLE001
            qpos, qs = None, {'jobs_queued': None, 'jobs_running': None}
        cov = _job_coverage(s, j)
        return {'job_id': j.id, 'entity_id': j.entity_id, 'status': j.status, 'depth': j.depth, 'agents': j.agents,
                'created_at': _iso(j.created_at), 'completed_at': _iso(j.completed_at), 'error': j.error,
                'queue_position': qpos, 'queue_length': qs['jobs_queued'], 'jobs_running': qs['jobs_running'],
                'coverage': cov,
                'synthesis': j.synthesis, 'claims_produced': n_claims,
                'runs': [{'agent_type': x.agent_type, 'status': x.status, 'model': x.model,
                          'claims_generated': x.claims_generated, 'errors': x.errors,
                          'latency_ms': x.latency_ms} for x in runs],
                'next': ('call get_research(entity) to read the claims' if j.status == 'done' else
                         ('coverage incomplete (missing ' + ', '.join((cov or {}).get('missing') or []) +
                          '): read get_research(entity) as PARTIAL, or call run_research(entity, only_missing=true) '
                          'to complete the missing agents') if j.status == 'partial' else
                         'still working — poll again in ~20-40 s' if j.status in ('queued', 'running') else None),
                'source': 'Khipus research swarm', 'as_of': _now_iso()}


# ════════════════════════════════════════════════════════════════════════════
# READ — riesgo, opciones, mundo
# ════════════════════════════════════════════════════════════════════════════
@tool('get_risk_report', 'Portfolio risk report (VaR)', 'read',
      'Risk report for a list of stock positions using REAL daily prices for the last year (Yahoo Finance): '
      'value, volatility, historical & parametric VaR 95/99%, expected shortfall, beta vs benchmark, '
      'correlations and per-position risk contribution. Statistical estimate from the past, not a forecast.',
      {'positions': {'type': 'array', 'minItems': 1, 'maxItems': 30,
                     'items': {'type': 'object', 'properties': {
                         'symbol': {'type': 'string', 'maxLength': 15, 'minLength': 1},
                         'shares': {'type': 'number', 'exclusiveMinimum': 0}},
                         'required': ['symbol', 'shares'], 'additionalProperties': False}},
       'horizon_days': {'type': 'integer', 'minimum': 1, 'maximum': 30, 'default': 10}},
      required=['positions'], open_world=True)
def t_get_risk_report(ctx, positions, horizon_days=10):
    from core.risk_report import build_report
    rep = _bounded(build_report, 40, positions, horizon=horizon_days)
    if not rep.get('ok'):
        raise ToolError(rep.get('error') or 'risk report failed', code='no_data',
                        data={'excluded': rep.get('excluded') or []})
    rep = {k: v for k, v in rep.items() if k != 'histogram'}
    rep['as_of'] = rep.get('as_of') or rep.get('generated_at')
    return rep


@tool('get_option_greeks', 'Option greeks (Black-Scholes, live IV)', 'read',
      'Values option positions with Black-Scholes-Merton using the LIVE underlying price and the contract\'s '
      'implied volatility (falls back to 1-year historical volatility, labeled): delta, gamma, vega, theta and '
      'P&L under volatility shocks. Nothing is executed.',
      {'options': {'type': 'array', 'minItems': 1, 'maxItems': 40,
                   'items': {'type': 'object', 'properties': {
                       'symbol': {'type': 'string', 'maxLength': 15, 'minLength': 1},
                       'kind': {'type': 'string', 'enum': ['call', 'put']},
                       'strike': {'type': 'number', 'exclusiveMinimum': 0},
                       'expiry': {'type': 'string', 'maxLength': 10, 'description': 'YYYY-MM-DD'},
                       'contracts': {'type': 'number', 'description': '+ long / − short'}},
                       'required': ['symbol', 'kind', 'strike', 'expiry', 'contracts'],
                       'additionalProperties': False}}},
      required=['options'], open_world=True)
def t_get_option_greeks(ctx, options):
    from core.options import vega_report
    rep = _bounded(vega_report, 40, options)
    if not rep.get('ok'):
        raise ToolError(rep.get('error') or 'could not value any option', code='no_data',
                        data={'excluded': rep.get('excluded') or []})
    rep['as_of'] = rep.get('generated_at')
    rep['source'] = 'Yahoo Finance options chain (live) + Black-Scholes-Merton'
    return rep


_WORLD_LAYERS = ['conflict', 'unrest', 'trade', 'quakes', 'natural', 'chokepoints', 'instability']


@tool('get_world_events', 'World monitor events', 'read',
      'Live geopolitical and physical-risk events from the Khipus World Monitor (GDELT conflict/unrest/trade, '
      'USGS earthquakes, NASA EONET natural events, maritime chokepoints, instability), each with coordinates, '
      'severity, time, source and URL. Per-layer status says what could not be fetched.',
      {'layers': {'type': 'array', 'maxItems': 7, 'items': {'type': 'string', 'enum': _WORLD_LAYERS}},
       'window': {'type': 'string', 'enum': ['24h', '7d'], 'default': '24h'},
       'limit': {'type': 'integer', 'minimum': 1, 'maximum': 150, 'default': 40}},
      open_world=True)
def t_get_world_events(ctx, layers=None, window='24h', limit=40):
    try:
        world = importlib.import_module('core.world')
        fn = world.world_events
    except Exception as e:  # noqa: BLE001
        raise ToolError(f'world monitor is not available on this server ({type(e).__name__})',
                        code='unavailable') from None
    res = _bounded(fn, 25, layers or None, window) or {}
    items = list(res.get('items') or [])
    items.sort(key=lambda x: str(x.get('time') or ''), reverse=True)        # más reciente primero…
    items.sort(key=lambda x: -(x.get('severity') or 0))                      # …dentro de cada severidad
    keep = ('id', 'layer', 'lat', 'lon', 'title', 'severity', 'time', 'source', 'url', 'country', 'place')
    return {'window': res.get('window') or window, 'count_total': len(items),
            'items': [{k: x.get(k) for k in keep if k in x} for x in items[:limit]],
            'sources': res.get('sources') or {}, 'as_of': res.get('as_of') or _now_iso(),
            'source': 'Khipus World Monitor (core.world)'}


# ════════════════════════════════════════════════════════════════════════════
# READ — comité y track record (Phase 3, opcionales)
# ════════════════════════════════════════════════════════════════════════════
def _module(name, what):
    try:
        return importlib.import_module(name)
    except Exception as e:  # noqa: BLE001
        raise ToolError(f'{what} is not available on this server ({type(e).__name__})', code='unavailable') from None


def _trim_memo(m):
    if not isinstance(m, dict):
        return m
    m = dict(m)
    if isinstance(m.get('audit'), list):
        m['audit'] = m['audit'][-10:]
    if isinstance(m.get('inputs'), dict):
        m['inputs'] = {k: v for k, v in m['inputs'].items() if k != 'package'}
    if isinstance(m.get('memo'), dict) and isinstance(m['memo'].get('transcript'), list):
        # el debate completo pesa mucho: se resume (quién, postura, titular o inicio del texto)
        body = dict(m['memo'])
        body['transcript'] = [
            {'seat': x.get('seat'), 'kind': x.get('kind'), 'stance': x.get('stance'), 'ai': x.get('ai'),
             'said': (x.get('headline_en') or x.get('headline_es') or str(x.get('text_en') or x.get('text_es') or ''))[:260]}
            for x in body['transcript'] if x.get('kind') in ('position', 'rebuttal', 'verdict')][:16]
        body.pop('seats', None)
        m['memo'] = body
    return m


@tool('get_committee_memo', 'Investment committee memo', 'read',
      'The latest investment-committee memo for an entity (or a specific memo_id): decision (BUY/ADD/HOLD/TRIM/'
      'SELL/AVOID…), conviction by horizon, thesis, risks, dissent, sizing and status. Client-specific amounts '
      'are redacted unless this token trades for that client. Research, not advice.',
      {'entity': {'type': 'string', 'maxLength': 120, 'description': 'Graph id, ticker or name.'},
       'memo_id': {'type': 'string', 'maxLength': 40}})
def t_get_committee_memo(ctx, entity=None, memo_id=None):
    if not entity and not memo_id:
        raise InvalidParams('arguments: provide "entity" or "memo_id"')
    _need_db('get_committee_memo')
    cm = _module('research.committee', 'the investment committee')
    from ontology.db import session_scope
    p = ctx.principal

    def _q():
        with session_scope() as s:
            if memo_id:
                m = cm.get_memo(s, memo_id, redact_client=False)
            else:
                r = _resolve(entity)
                eid = r['id'] if r else str(entity)[:120]
                m = cm.latest_memo(s, eid, redact_client=False)
            if m and m.get('client_id') and not (p.has('trade') and p.client_id == m.get('client_id')):
                m = (cm.get_memo(s, m['memo_id'], redact_client=True) if hasattr(cm, 'get_memo') else
                     {k: v for k, v in m.items() if k not in ('sizing', 'inputs', 'preview')})
            return m
    m = _auth.with_schema(_q)
    if not m:
        raise ToolError('no committee memo found' + (f' for "{entity}"' if entity else ''), code='not_found',
                        data={'hint': 'run_committee (research scope) can produce one'})
    out = _trim_memo(m)
    out['source'] = 'Khipus investment committee (research.committee)'
    out['as_of'] = _now_iso()
    return out


@tool('get_conclusions_board', 'Committee conclusions board', 'read',
      'Every researched company ranked by the agents\' overall conviction (−100..+100), with the strongest '
      'argument for and against, contradiction count and the latest committee decision/conclusion. Use it for '
      '"which companies look best/worst?" or "what have the analysts concluded?". Research, not advice.',
      {'limit': {'type': 'integer', 'minimum': 1, 'maximum': 60, 'default': 20},
       'side': {'type': 'string', 'enum': ['all', 'favorable', 'unfavorable'], 'default': 'all'}})
def t_get_conclusions_board(ctx, limit=20, side='all'):
    _need_db('get_conclusions_board')
    cm = _module('research.committee', 'the investment committee')
    from ontology.db import session_scope

    def _q():
        with session_scope() as s:
            return cm.board(s, limit=60)
    res = _auth.with_schema(_q) or {}
    items = list(res.get('items') or [])
    if side == 'favorable':
        items = [x for x in items if x['overall_conviction'] > 0]
    elif side == 'unfavorable':
        items = sorted([x for x in items if x['overall_conviction'] < 0], key=lambda x: x['overall_conviction'])
    out = []
    for x in items[:max(1, min(int(limit or 20), 60))]:
        out.append({'entity_id': x['entity_id'], 'label': x['label'], 'conviction': x['overall_conviction'],
                    'n_claims': x['n_claims'], 'agents': x['agents'], 'contradictions': x['n_contradictions'],
                    'last_research': x['last_research'],
                    'best_for': (x['best_for'] or {}).get('text_en') if x.get('best_for') else None,
                    'best_against': (x['best_against'] or {}).get('text_en') if x.get('best_against') else None,
                    'committee': ({'decision': x['memo']['decision'], 'status': x['memo']['status'],
                                   'date': x['memo']['created_at'], 'ai_debate': x['memo']['ai'],
                                   'conclusion': x['memo'].get('conclusion_en')} if x.get('memo') else None)})
    return {'items': out, 'n': len(out), 'source': 'Khipus research claims + committee memos',
            'note': res.get('note_en'), 'as_of': _now_iso()}


@tool('get_track_record', 'Agent track record & calibration', 'read',
      'How accurate the Khipus research agents have been: scored predictions, hit rate, Brier score and '
      'calibration buckets per agent (predictions are scored against real prices after their horizon).',
      {'agent_type': {'type': 'string', 'maxLength': 40}})
def t_get_track_record(ctx, agent_type=None):
    _need_db('get_track_record')
    oc = _module('research.outcomes', 'the track record module')
    from ontology.db import session_scope

    def _q():
        with session_scope() as s:
            return oc.track_record(s, agent_type=agent_type)
    res = _auth.with_schema(_q) or {}
    res = dict(res)
    res['source'] = 'Khipus research outcomes (claims scored vs real prices)'
    res.setdefault('as_of', _now_iso())
    return res


# ════════════════════════════════════════════════════════════════════════════
# RESEARCH — lanzar investigación / comité (gasta presupuesto de IA)
# ════════════════════════════════════════════════════════════════════════════
@tool('run_research', 'Start research on an entity', 'research',
      'Starts (or reuses a recent identical) research job by the Khipus agent swarm on an entity. Asynchronous: '
      'returns a job_id; poll get_research_job, then read get_research. Respects the server daily AI budget. '
      'Agents cite evidence and never give buy/sell orders.',
      {'entity': {'type': 'string', 'maxLength': 120, 'minLength': 1},
       'depth': {'type': 'string', 'enum': ['QUICK', 'STANDARD'], 'default': 'STANDARD'},
       'only_missing': {'type': 'boolean', 'default': False,
                        'description': 'Only re-run the agents that did not answer in the last (partial) job.'}},
      required=['entity'], read_only=False, idempotent=False, open_world=True)
def t_run_research(ctx, entity, depth='STANDARD', only_missing=False):
    _need_db('run_research')
    r = _resolve_or_fail(entity)
    try:
        from core.ai import _ai_configured
        if not _ai_configured():
            raise ToolError('no AI provider is configured on the server', code='unavailable')
    except ImportError:
        raise ToolError('AI layer not available', code='unavailable') from None
    runner = _module('research.runner', 'the research runner')
    from ontology.db import session_scope
    p = ctx.principal
    # MISMA lectura que el runner (antes '0' se leía como $2.00 y se informaba mal al agente)
    cfg = getattr(runner, '_cfg', None)
    try:
        budget = float(cfg('RESEARCH_DAILY_BUDGET_USD', 2.0)) if cfg else float(os.getenv('RESEARCH_DAILY_BUDGET_USD',
                                                                                          '2.0'))
    except (TypeError, ValueError):
        budget = 2.0
    if budget <= 0:
        raise ToolError('research is switched off on this server (daily AI budget RESEARCH_DAILY_BUDGET_USD = 0)',
                        code='budget_exhausted', data={'daily_budget_usd': budget})

    def _crear():
        with session_scope() as s:
            spent = runner.spent_today(s)
            if spent >= budget:
                raise ToolError(f'daily research budget exhausted (~${spent:.2f} of ${budget:.2f} estimated); '
                                'try again tomorrow', code='budget_exhausted')
            job, reused = runner.create_job(s, r['id'], depth=depth, trigger={'kind': 'mcp', 'by': p.actor},
                                            requested_by=p.actor, only_missing=bool(only_missing))
            return {'job_id': job.id, 'entity_id': r['id'], 'label': r['label'], 'status': job.status,
                    'reused': reused, 'agents': job.agents, 'depth': job.depth,
                    'spent_today_usd_est': round(spent, 4), 'daily_budget_usd': budget}
    out = _auth.with_schema(_crear)
    if not out['reused']:
        runner.execute_job_async(out['job_id'])
    out['next'] = 'poll get_research_job(job_id) every ~30 s; when done read get_research(entity)'
    out['as_of'] = _now_iso()
    return out


def _run_committee_async(memo_id, eid, actor, client_id, release=None):
    """Corre el comité en un hilo. El cupo (acquire_run_slot) ya se tomó: `release`
    lo libera al terminar, pase lo que pase (mismo contrato que committee_api._run_async)."""
    def _work():
        from ontology.db import session_scope
        try:
            from research.committee import fail_memo, run_committee
            try:
                with session_scope() as s:
                    run_committee(s, eid, actor, client_id=client_id, memo_id=memo_id)
            except Exception as e:  # noqa: BLE001
                log.warning('mcp committee %s: %s', memo_id, e)
                try:
                    with session_scope() as s:
                        fail_memo(s, memo_id, f'{type(e).__name__}: {str(e)[:300]}')
                except Exception:  # noqa: BLE001
                    pass
        finally:
            try:
                from research.committee import progress_clear
                progress_clear(memo_id)
            except Exception:  # noqa: BLE001
                pass
            if release is not None:
                release()
    t = threading.Thread(target=_work, name=f'mcp-committee-{str(memo_id)[:8]}', daemon=True)
    t.start()
    return t


@tool('run_committee', 'Run the investment committee', 'research',
      'Runs the Khipus investment committee on an entity (asynchronous): it weighs the agents\' claims, '
      'track record, live risk and (optionally) the mandate/positions of the client bound to this token, and '
      'writes a memo with a decision and sizing. Returns memo_id; poll get_committee_memo(memo_id). If the same '
      'entity/client is already deliberating (or was decided < 2 min ago) that memo is returned (reused=true). '
      'Only a few committees run at once server-wide: code "busy" means retry in a minute. A memo is NOT an '
      'order: any resulting order still needs human approval in Khipus.',
      {'entity': {'type': 'string', 'maxLength': 120, 'minLength': 1},
       'client_id': {'type': 'string', 'maxLength': 60,
                     'description': 'Only the brokerage client bound to this token (needs the trade scope).'}},
      required=['entity'], read_only=False, idempotent=False, open_world=True)
def t_run_committee(ctx, entity, client_id=None):
    _need_db('run_committee')
    cm = _module('research.committee', 'the investment committee')
    r = _resolve_or_fail(entity)
    p = ctx.principal
    cid = None
    if client_id:
        if not p.has('trade') or not p.client_id:
            raise ToolError("client_id requires a token with the 'trade' scope bound to that client",
                            code='insufficient_scope')
        if str(client_id).strip() != p.client_id:
            svc = _brokerage(required=False)
            canon = None
            if svc is not None:
                from ontology.db import session_scope
                with session_scope() as s:
                    c = svc.get_client(s, client_id)
                    canon = (c or {}).get('id')
            if canon != p.client_id:
                raise ToolError('this token can only act for its own bound client', code='forbidden')
        cid = p.client_id
    from ontology.db import session_scope
    base = {'entity_id': r['id'], 'label': r['label'], 'client_id': cid,
            'next': 'poll get_committee_memo(memo_id=…) every ~30 s', 'disclaimer': DISCLAIMER_EN}
    # 1) mismo (entidad, cliente) deliberando o recién decidido → se reutiliza (no se gasta IA dos veces)
    recent = getattr(cm, 'recent_memo', None)
    if recent is not None:
        def _reuse():
            with session_scope() as s:
                m = recent(s, r['id'], cid)
                return (m.id, m.status) if m else None
        try:
            prev = _auth.with_schema(_reuse)
        except Exception as e:  # noqa: BLE001
            log.warning('mcp committee (dedupe): %s', type(e).__name__)
            prev = None
        if prev:
            return dict(base, memo_id=prev[0], status=prev[1], reused=True, as_of=_now_iso())
    # 2) tope de comités simultáneos en TODO el servidor (COMMITTEE_MAX_CONCURRENT)
    acquire, release = getattr(cm, 'acquire_run_slot', None), getattr(cm, 'release_run_slot', None)
    if acquire is not None and not acquire():
        raise ToolError('the investment committee is busy with other requests — retry in a minute', code='busy',
                        data={'retry_after_s': 60})
    started = False
    try:
        def _ph():
            with session_scope() as s:
                return cm.create_placeholder(s, r['id'], p.actor, cid).id
        mid = _auth.with_schema(_ph)
        _run_committee_async(mid, r['id'], p.actor, cid, release=release)
        started = True
    finally:
        if not started and release is not None:
            release()                     # el hilo libera el cupo solo si arrancó
    return dict(base, memo_id=mid, status='running', reused=False, as_of=_now_iso())


# ════════════════════════════════════════════════════════════════════════════
# TRADE — solo el cliente ligado al token; aprobación humana
# ════════════════════════════════════════════════════════════════════════════
def _brokerage(required=True):
    try:
        svc = importlib.import_module('brokerage.service')
    except Exception as e:  # noqa: BLE001
        if not required:
            return None
        raise ToolError(f'the brokerage module is not available on this server ({type(e).__name__})',
                        code='unavailable') from None
    return svc


def _trade_ctx(ctx):
    p = ctx.principal
    if not p.has('trade'):
        raise ToolError("insufficient scope: this token lacks the 'trade' scope", code='insufficient_scope')
    if not p.client_id:
        raise ToolError('this token is not bound to a brokerage client', code='no_client')
    if not trading_enabled():
        raise ToolError('trading through MCP is switched off on this server (MCP_TRADING_ENABLED=off)',
                        code='trading_disabled')
    svc = _brokerage()
    try:
        ok = svc.available()
    except Exception:  # noqa: BLE001
        ok = False
    if not ok:
        raise ToolError('brokerage is not available (it needs the Khipus database)', code='unavailable')
    return p, svc


def _session():
    from ontology.db import session_scope
    return session_scope()


def _mode_badge(paper):
    return 'PAPER (simulated money)' if paper else 'LIVE (REAL MONEY)'


_CLIENT_KEYS = ('id', 'name', 'mode', 'paper', 'live_enabled', 'risk_profile', 'limits', 'status',
                'drawdown_pct', 'connected')


def _client_public(c):
    return {k: (c or {}).get(k) for k in _CLIENT_KEYS if k in (c or {})}


def _order_public(o):
    if not isinstance(o, dict):
        return o
    drop = ('client_order_id',)
    return {k: v for k, v in o.items() if k not in drop}


def _own_order(svc, s, cid, order_id):
    oid = str(order_id or '').strip()[:40]
    get = getattr(svc, 'get_order', None)
    o = None
    if get is not None:
        o = get(s, oid)
    else:
        o = next((x for x in svc.list_orders(s, client_id=cid, limit=500)
                  if x.get('id') == oid or x.get('preview_id') == oid), None)
    if not o or o.get('client_id') != cid:
        raise ToolError('order not found for the client bound to this token', code='not_found')
    return o


@tool('get_account', 'Brokerage account (bound client)', 'trade',
      'Live account of the brokerage client bound to this token (Alpaca via Khipus): equity, cash, buying '
      'power, mode (PAPER = simulated / LIVE = real money), risk profile & limits, and positions.',
      {}, open_world=True)
def t_get_account(ctx):
    p, svc = _trade_ctx(ctx)
    with _session() as s:
        snap = svc.account_snapshot(s, p.client_id)
    if not snap or not snap.get('ok'):
        raise ToolError((snap or {}).get('error') or 'could not read the account', code='broker_error')
    acct = snap.get('account') or {}
    paper = acct.get('paper', (snap.get('client') or {}).get('paper', True))
    return {'client': _client_public(snap.get('client')), 'account': acct, 'positions': snap.get('positions') or [],
            'mode_badge': _mode_badge(paper), 'source': 'Alpaca (read live through Khipus brokerage)',
            'as_of': snap.get('as_of') or _now_iso()}


@tool('get_positions', 'Positions (bound client)', 'trade',
      'Open positions of the brokerage client bound to this token: symbol, qty, average entry, market value '
      'and unrealized P&L (live from the broker).', {}, open_world=True)
def t_get_positions(ctx):
    p, svc = _trade_ctx(ctx)
    with _session() as s:
        snap = svc.account_snapshot(s, p.client_id)
    if not snap or not snap.get('ok'):
        raise ToolError((snap or {}).get('error') or 'could not read the positions', code='broker_error')
    paper = (snap.get('account') or {}).get('paper', True)
    return {'client_id': p.client_id, 'positions': snap.get('positions') or [], 'mode_badge': _mode_badge(paper),
            'source': 'Alpaca (read live through Khipus brokerage)', 'as_of': snap.get('as_of') or _now_iso()}


_APPROVAL_MSG_EN = ('Order queued for human approval in Khipus (👥 Clientes → Aprobaciones). A human must approve it '
                    'with the trading PIN; nothing has been sent to the broker yet.')
_APPROVAL_MSG_ES = ('En cola de aprobación humana en Khipus (👥 Clientes → Aprobaciones). Una persona debe '
                    'aprobarla con el PIN de trading; todavía no se envió nada al bróker.')


@tool('preview_order', 'Propose an order (preview + risk checks)', 'trade',
      'PROPOSES an order for the client bound to this token. Khipus runs pre-trade risk checks (mandate, '
      'position and daily limits, buying power, market hours, duplicates, kill switch) and returns a preview '
      'with a human-readable summary. Orders from AI agents are placed in the HUMAN APPROVAL queue in Khipus '
      '(👥 Clientes → Aprobaciones) — you cannot approve them yourself. Give either notional (USD) or qty. '
      'Always explain your reasoning in "rationale": the human reads it before approving. Never trade without '
      'the user explicitly asking you to.',
      {'symbol': {'type': 'string', 'maxLength': 15, 'minLength': 1,
                  'description': 'Ticker (e.g. "NVDA") or crypto pair "BTC/USD".'},
       'side': {'type': 'string', 'enum': ['buy', 'sell']},
       'notional': {'type': 'number', 'exclusiveMinimum': 0, 'description': 'USD amount (fractional).'},
       'qty': {'type': 'number', 'exclusiveMinimum': 0, 'description': 'Number of shares/units.'},
       'order_type': {'type': 'string', 'enum': ['market', 'limit'], 'default': 'market'},
       'limit_price': {'type': 'number', 'exclusiveMinimum': 0},
       'rationale': {'type': 'string', 'minLength': 10, 'maxLength': 2000,
                     'description': 'Why this order (thesis, evidence, risk). Shown to the human approver.'}},
      required=['symbol', 'side', 'rationale'], read_only=False, idempotent=False, open_world=True)
def t_preview_order(ctx, symbol, side, rationale, notional=None, qty=None, order_type='market', limit_price=None):
    p, svc = _trade_ctx(ctx)
    if (notional is None) == (qty is None):
        raise InvalidParams('arguments: give exactly one of "notional" (USD) or "qty"')
    if order_type == 'limit' and limit_price is None:
        raise InvalidParams('arguments: "limit_price" is required for limit orders')
    with _session() as s:
        res = svc.preview_order(s, p.client_id, symbol, side, notional=notional, qty=qty, order_type=order_type,
                                limit_price=limit_price, source='mcp', requested_by=p.actor,
                                rationale=f'[{p.actor}] {rationale}')
    if not res or not res.get('ok'):
        raise ToolError((res or {}).get('error') or 'preview failed', code=(res or {}).get('code') or 'preview_failed')
    out = _order_public(dict(res))
    paper = out.get('paper', True)
    out['mode_badge'] = _mode_badge(paper)
    if res.get('blocked'):
        out['next'] = 'BLOCKED by risk checks — see checks; do not retry the same order. Explain to the user.'
    elif res.get('requires_human_approval') or res.get('status') == 'pending_approval':
        out['next'] = _APPROVAL_MSG_EN + ' You may call submit_order(preview_id) to confirm the request; ' \
                                         'it will report the approval status.'
        out['message_es'] = _APPROVAL_MSG_ES
    else:
        out['next'] = 'Auto-approval for PAPER accounts is on: call submit_order(preview_id) within the preview ' \
                      'validity to send it.'
    out['as_of'] = _now_iso()
    return out


@tool('submit_order', 'Submit a previewed order', 'trade',
      'Confirms a preview created with preview_order. For AI-agent orders this does NOT bypass the human: '
      'unless the server enables auto-approval for PAPER accounts, the result is "pending_human_approval" — '
      'queued in Khipus (👥 Clientes → Aprobaciones) until a person approves it with the trading PIN. Check '
      'later with get_order_status.',
      {'preview_id': {'type': 'string', 'maxLength': 40, 'minLength': 1}},
      required=['preview_id'], read_only=False, destructive=True, idempotent=True, open_world=True)
def t_submit_order(ctx, preview_id):
    p, svc = _trade_ctx(ctx)
    with _session() as s:
        o = _own_order(svc, s, p.client_id, preview_id)
        # defensa en profundidad: si la cuenta del cliente cambió de modo desde la
        # previsualización (p. ej. papel → dinero real), NO se confirma nada.
        c = svc.get_client(s, p.client_id) or {}
        cur_mode = c.get('mode') or ('paper' if c.get('paper', True) else 'live')
        if o.get('mode') and cur_mode and o.get('mode') != cur_mode:
            raise ToolError(f"the client's account mode changed since the preview ({o.get('mode')} → {cur_mode}); "
                            'nothing was sent — create a new preview_order', code='account_changed',
                            data={'preview_mode': o.get('mode'), 'client_mode': cur_mode})
        res = svc.confirm_order(s, preview_id, approved_by=p.actor, source='mcp') or {}
    order = _order_public(res.get('order'))
    if res.get('ok'):
        # el distintivo sale del modo de la ORDEN y del modo ACTUAL de la cuenta: PAPER solo si ambos lo son
        paper = bool((order or {}).get('paper', True)) and cur_mode != 'live' and (order or {}).get('mode') != 'live'
        return {'status': res.get('status') or (order or {}).get('status'), 'order': order,
                'mode_badge': _mode_badge(paper),
                'message': 'Sent to the broker (' + _mode_badge(paper) + '). Track it with get_order_status.',
                'as_of': _now_iso()}
    if res.get('status') == 'pending_approval' or res.get('code') == 'requires_human_approval' \
            or 'requires human approval' in str(res.get('error') or ''):
        return {'status': 'pending_human_approval', 'preview_id': preview_id, 'order': order,
                'message': _APPROVAL_MSG_EN, 'message_es': _APPROVAL_MSG_ES,
                'approval_location': APPROVAL_PLACE_ES, 'as_of': _now_iso()}
    raise ToolError(res.get('error') or 'could not submit the order', code=res.get('code') or 'submit_failed',
                    data={'status': res.get('status'), 'order': order})


@tool('list_orders', 'Orders of the bound client', 'trade',
      'Recent previews/orders of the client bound to this token, newest first, with status (previewed, '
      'pending_approval, approved, submitted, filled, canceled, rejected, expired, failed).',
      {'status': {'type': 'string', 'maxLength': 120,
                  'description': 'Optional comma-separated filter, e.g. "pending_approval,submitted".'},
       'limit': {'type': 'integer', 'minimum': 1, 'maximum': 200, 'default': 30}})
def t_list_orders(ctx, status=None, limit=30):
    p, svc = _trade_ctx(ctx)
    with _session() as s:
        rows = svc.list_orders(s, client_id=p.client_id, status=status, limit=limit) or []
    rows = [_order_public(o) for o in rows if o.get('client_id') in (None, p.client_id)]
    return {'client_id': p.client_id, 'count': len(rows), 'orders': rows, 'source': 'Khipus brokerage',
            'as_of': _now_iso()}


@tool('cancel_order', 'Cancel an order this connection proposed', 'trade',
      'Cancels a preview, a proposal waiting for approval or an open order that THIS connection proposed '
      '(preview_order). Orders placed by a person in Khipus, committee proposals or other agents\' orders cannot be '
      'cancelled from here: tell the user to cancel them in Khipus (👥 Clientes).',
      {'order_id': {'type': 'string', 'maxLength': 40, 'minLength': 1}},
      required=['order_id'], read_only=False, destructive=True, idempotent=True, open_world=True)
def t_cancel_order(ctx, order_id):
    p, svc = _trade_ctx(ctx)
    with _session() as s:
        o = _own_order(svc, s, p.client_id, order_id)
        # un agente solo cancela lo que ÉL propuso: nunca la orden de una persona (quizás una
        # protección límite en una cuenta real) ni una propuesta del comité → sin aprobación humana
        if o.get('source') != 'mcp' or (o.get('requested_by') or '') != p.actor:
            raise ToolError('this order was not proposed by this connection (it came from '
                            f"{o.get('source') or 'unknown'}): only a person can cancel it, in Khipus → 👥 Clientes",
                            code='forbidden', data={'order_source': o.get('source'),
                                                    'where': '👥 Clientes (Khipus)'})
        res = svc.cancel_order(s, order_id, p.actor) or {}
    if not res.get('ok'):
        raise ToolError(res.get('error') or 'could not cancel', code=res.get('code') or 'cancel_failed',
                        data={'status': res.get('status')})
    return {'status': res.get('status'), 'order': _order_public(res.get('order')), 'as_of': _now_iso()}


@tool('get_order_status', 'Order status', 'trade',
      'Status of one preview/order of the client bound to this token (refreshed from the broker when possible): '
      'pending_approval means a human has not approved it yet in Khipus.',
      {'order_id': {'type': 'string', 'maxLength': 40, 'minLength': 1}},
      required=['order_id'], open_world=True)
def t_get_order_status(ctx, order_id):
    p, svc = _trade_ctx(ctx)
    synced = False
    with _session() as s:
        o = _own_order(svc, s, p.client_id, order_id)
        sync = getattr(svc, 'sync_orders', None)
        if sync is not None and o.get('alpaca_order_id') and o.get('status') in (
                'approved', 'submitted', 'partially_filled'):
            try:
                sync(s, client_id=p.client_id, actor=p.actor)
                synced = True
                o = _own_order(svc, s, p.client_id, order_id)
            except Exception as e:  # noqa: BLE001
                log.info('mcp sync: %s', type(e).__name__)
    out = {'order': _order_public(o), 'synced_with_broker': synced, 'as_of': _now_iso()}
    if o.get('status') == 'pending_approval':
        out['message'] = _APPROVAL_MSG_EN
    return out


def catalog():
    """Para la UI / docs: todas las herramientas con su alcance."""
    return [dict(t.describe(), scope=t.scope) for t in REGISTRY.values()]


def reset_caches():
    _SNAP['data'] = None
    _PV['data'] = None


__all__ = ['REGISTRY', 'Tool', 'ToolError', 'InvalidParams', 'Ctx', 'call', 'visible_tools', 'catalog',
           'validate']
