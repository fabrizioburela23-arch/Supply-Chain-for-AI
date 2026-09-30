"""mcp_server/protocol.py — JSON-RPC 2.0 + Model Context Protocol (servidor).

Independiente de Flask: `handle(msg, ctx)` recibe UN mensaje ya decodificado y
devuelve (respuesta | None, info_de_auditoría). api.py se ocupa del transporte
(Streamable HTTP: POST /mcp → application/json).

Versiones soportadas: 2025-06-18 (la más nueva) y 2025-03-26. Negociación
(spec «Lifecycle»): si el cliente pide una versión soportada se devuelve esa;
si no, la más nueva que soporta el servidor (el cliente decide si sigue).

Errores: los de PROTOCOLO (JSON inválido, método inexistente, parámetros que
no cumplen el esquema, herramienta desconocida) son errores JSON-RPC; los de
EJECUCIÓN de una herramienta van como resultado con isError: true, para que el
modelo los lea y se corrija.
"""
import json
import logging
import math

from mcp_server import SERVER_NAME, SERVER_TITLE, SERVER_VERSION
from mcp_server import tools as _tools

log = logging.getLogger('khipu')

SUPPORTED_VERSIONS = ('2025-06-18', '2025-03-26')
LATEST_VERSION = SUPPORTED_VERSIONS[0]

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
UNSUPPORTED_VERSION = -32022        # «unsupported protocol version» (revisiones posteriores del spec)

MAX_RESULT_CHARS = 240_000


def negotiate(requested):
    return requested if requested in SUPPORTED_VERSIONS else LATEST_VERSION


def error(id_, code, message, data=None):
    err = {'code': code, 'message': message}
    if data is not None:
        err['data'] = data
    return {'jsonrpc': '2.0', 'id': id_, 'error': err}


def result(id_, res):
    return {'jsonrpc': '2.0', 'id': id_, 'result': res}


def instructions(principal):
    sc = ', '.join(sorted(principal.scopes))
    lines = [
        'Khipus Finance AI — financial terminal and ontology of the AI supply chain (949 curated companies, '
        '2,500+ supplier→customer links, macro layers), live market data, a research-agent swarm with '
        'evidence-backed claims, an investment committee and multi-client brokerage (Alpaca).',
        f'This connection has scopes: {sc}.',
        'Rules: (1) Never invent figures — every tool result carries source and as_of; if something is '
        'unavailable, say so. (2) Research and committee memos are information, not advice. '
        '(3) Start with search_companies to get ids, then get_company / get_supply_chain / get_research.',
    ]
    if principal.has('trade') and principal.client_id and _tools.trading_enabled():
        lines.append(
            f'Trading: this token may act ONLY for brokerage client {principal.client_id}. preview_order runs '
            'risk checks and puts AI-proposed orders in the HUMAN APPROVAL queue in Khipus '
            '(👥 Clientes → Aprobaciones); submit_order cannot bypass it (except auto-approval for PAPER '
            'accounts if the server enables it). Only propose orders when the user explicitly asks, always with '
            'a rationale, and tell the user the order is waiting for approval. cancel_order only works on orders '
            'this connection proposed; orders placed by a person are cancelled by a person in Khipus.')
    elif principal.has('trade') and principal.client_id:
        lines.append('Trading through MCP is switched off on this server (MCP_TRADING_ENABLED=off): no trading tools '
                     'are available; do not offer to place orders.')
    else:
        lines.append('Trading tools are not enabled for this connection.')
    return ' '.join(lines)


def _is_valid_id(v):
    return (isinstance(v, str) and len(v) <= 200) or (isinstance(v, int) and not isinstance(v, bool))


def _finite(v, depth=0):
    """NaN/Infinity (p. ej. de una fuente de datos) → None: no son JSON válido."""
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if depth > 40:
        return v
    if isinstance(v, dict):
        return {k: _finite(x, depth + 1) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_finite(x, depth + 1) for x in v]
    return v


def _tool_result(payload, is_error=False):
    try:
        try:
            text = json.dumps(payload, ensure_ascii=False, default=str, allow_nan=False)
        except ValueError:
            text = json.dumps(_finite(payload), ensure_ascii=False, default=str, allow_nan=False)
    except Exception:  # noqa: BLE001
        text = json.dumps({'error': 'result could not be serialized'})
        is_error = True
    if len(text) > MAX_RESULT_CHARS:
        payload = {'error': 'result too large — narrow the request (smaller limit/depth)',
                   'code': 'too_large', 'size_chars': len(text)}
        text = json.dumps(payload)
        is_error = True
    return {'content': [{'type': 'text', 'text': text}], 'structuredContent': json.loads(text),
            'isError': bool(is_error)}


def handle(msg, ctx):
    """→ (respuesta dict | None, audit dict | None).

    None como respuesta = notificación o respuesta del cliente (HTTP 202)."""
    if not isinstance(msg, dict) or msg.get('jsonrpc') != '2.0':
        return error(None, INVALID_REQUEST, 'Invalid Request: expected a JSON-RPC 2.0 object'), \
            {'method': None, 'status': 'invalid', 'error': 'invalid request'}
    has_id = 'id' in msg
    method = msg.get('method')
    if method is None and has_id and ('result' in msg or 'error' in msg):
        return None, None                      # respuesta del cliente a algo nuestro (no enviamos requests)
    if not isinstance(method, str) or not method:
        return error(msg.get('id') if has_id and _is_valid_id(msg.get('id')) else None, INVALID_REQUEST,
                     'Invalid Request: missing method'), {'method': None, 'status': 'invalid', 'error': 'no method'}
    if not has_id:
        return None, None                      # notificación (notifications/initialized, cancelled…)
    id_ = msg.get('id')
    if not _is_valid_id(id_):
        return error(None, INVALID_REQUEST, 'Invalid Request: id must be a string or integer'), \
            {'method': method, 'status': 'invalid', 'error': 'bad id'}
    params = msg.get('params')
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return error(id_, INVALID_PARAMS, 'Invalid params: expected an object'), \
            {'method': method, 'status': 'invalid', 'error': 'params not object'}
    audit = {'method': method, 'status': 'ok'}
    try:
        if method == 'initialize':
            ver = negotiate(params.get('protocolVersion'))
            ctx.protocol_version = ver
            ci = params.get('clientInfo') if isinstance(params.get('clientInfo'), dict) else {}
            audit['args'] = {'requested_version': str(params.get('protocolVersion'))[:20], 'version': ver,
                             'client': str(ci.get('name') or '')[:80], 'client_version': str(ci.get('version') or '')[:40]}
            return result(id_, {
                'protocolVersion': ver,
                'capabilities': {'tools': {'listChanged': False}},
                'serverInfo': {'name': SERVER_NAME, 'title': SERVER_TITLE, 'version': SERVER_VERSION},
                'instructions': instructions(ctx.principal),
            }), audit
        if method == 'ping':
            return result(id_, {}), None
        if method == 'tools/list':
            ts = _tools.visible_tools(ctx.principal)
            audit['args'] = {'count': len(ts)}
            return result(id_, {'tools': [t.describe() for t in ts]}), audit
        if method == 'tools/call':
            name = params.get('name')
            args = params.get('arguments')
            audit.update({'tool': name if isinstance(name, str) else None, 'args': args if isinstance(args, dict) else {}})
            if not isinstance(name, str) or not name:
                audit.update(status='invalid', error='missing tool name')
                return error(id_, INVALID_PARAMS, 'Invalid params: "name" is required'), audit
            if args is not None and not isinstance(args, dict):
                audit.update(status='invalid', error='arguments not object')
                return error(id_, INVALID_PARAMS, 'Invalid params: "arguments" must be an object'), audit
            if name not in _tools.REGISTRY:
                audit.update(status='invalid', error='unknown tool')
                return error(id_, INVALID_PARAMS, f'Unknown tool: {name[:60]}'), audit
            try:
                res = _tools.call(name, args or {}, ctx)
                return result(id_, _tool_result(res)), audit
            except _tools.InvalidParams as e:
                audit.update(status='invalid', error=str(e))
                return error(id_, INVALID_PARAMS, f'Invalid params: {e}'), audit
            except _tools.ToolError as e:
                audit.update(status='denied' if e.code in ('insufficient_scope', 'forbidden') else
                             'rate_limited' if e.code == 'rate_limited' else 'error', error=e.message)
                return result(id_, _tool_result(e.payload(), is_error=True)), audit
            except Exception as e:  # noqa: BLE001 — fallo inesperado de la herramienta: isError, no 500
                log.warning('mcp tool %s: %s: %s', name, type(e).__name__, str(e)[:200])
                audit.update(status='error', error=f'{type(e).__name__}: {str(e)[:200]}')
                return result(id_, _tool_result({'error': f'internal error in {name} ({type(e).__name__}); '
                                                          'the server logged it', 'code': 'internal'},
                                                is_error=True)), audit
        if method == 'resources/list':
            return result(id_, {'resources': []}), audit
        if method == 'resources/templates/list':
            return result(id_, {'resourceTemplates': []}), audit
        if method == 'prompts/list':
            return result(id_, {'prompts': []}), audit
        if method == 'logging/setLevel':
            return result(id_, {}), None
        audit.update(status='invalid', error='method not found')
        return error(id_, METHOD_NOT_FOUND, f'Method not found: {method[:60]}'), audit
    except Exception as e:  # noqa: BLE001
        log.warning('mcp %s: %s', method, e)
        audit.update(status='error', error=f'{type(e).__name__}')
        return error(id_, INTERNAL_ERROR, 'Internal error'), audit
