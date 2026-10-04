#!/usr/bin/env python3
"""scripts/smoke_mcp.py — O1 (misión de reparación 2026-10-04): humo del MCP
VIVO (el desplegado en Railway), solo con herramientas de LECTURA.

    KHIPU_MCP_TOKEN=kmcp_…  python scripts/smoke_mcp.py            # producción
    KHIPU_MCP_TOKEN=kmcp_…  python scripts/smoke_mcp.py --url http://localhost:5000 --json

El token debe ser de scope **read** (🩺 Sistema → 🤖 Conectar IAs → crear token
"solo lectura"). Si el token puede ver herramientas de trading, el script se
NIEGA a seguir (código 2): un humo nunca debe tener poder de dar órdenes.
Nunca llama preview_order / submit_order / cancel_order / run_research /
run_committee, ni nada que no esté marcado readOnlyHint.

Salida: tabla (o --json) y código 0 = todo bien · 1 = algo falló · 2 = config.
"""
import argparse
import json
import os
import sys
import time

DEFAULT_URL = 'https://supply-chain-for-ai-production.up.railway.app'
PROTOCOL = '2025-06-18'
DENY = {'preview_order', 'submit_order', 'cancel_order', 'run_research', 'run_committee'}
# (herramienta, argumentos, campos que DEBEN venir) — misma lista que core/ops_check.SMOKE_TOOLS
SMOKE = (
    ('search_companies', {'query': 'TSMC', 'limit': 3}, ('results', 'as_of', 'source')),
    ('get_company', {'id_or_ticker': 'TSMC', 'include_live': False}, ('id', 'catalog', 'counts', 'network_risk_score')),
    ('get_supply_chain', {'id': 'TSMC', 'limit': 5}, ('edges', 'nodes', 'convention')),
    ('get_research_health', {}, ('ok', 'providers', 'queue')),
    ('get_world_events', {'layers': ['quakes', 'chokepoints'], 'limit': 5}, ('items', 'sources')),
    ('get_track_record', {}, ()),
    ('get_conclusions_board', {}, ()),
)
NEEDS_DB = 'needs the Khipus ontology database'


class SmokeConfigError(RuntimeError):
    pass


def _rpc(http, url, token, method, params=None, rid=1, sid=None, timeout=60):
    msg = {'jsonrpc': '2.0', 'method': method}
    if rid is not None:
        msg['id'] = rid
    if params is not None:
        msg['params'] = params
    h = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
         'Authorization': f'Bearer {token}', 'MCP-Protocol-Version': PROTOCOL}
    if sid:
        h['Mcp-Session-Id'] = sid
    r = http.post(url, data=json.dumps(msg), headers=h, timeout=timeout)
    body = None
    if r.status_code != 202:
        try:
            body = r.json()
        except ValueError:
            body = None
    return r, body


def smoke(base_url, token, http=None, timeout=60):
    if not token or len(token) < 16:
        raise SmokeConfigError('falta KHIPU_MCP_TOKEN (un token kmcp_ de scope read)')
    if http is None:
        import requests
        http = requests.Session()
    url = base_url.rstrip('/') + '/mcp'
    t0 = time.time()
    results = []
    r, b = _rpc(http, url, token, 'initialize', {'protocolVersion': PROTOCOL, 'capabilities': {},
                                                  'clientInfo': {'name': 'khipus-smoke', 'version': '1'}},
                timeout=timeout)
    if r.status_code != 200 or not b or 'result' not in b:
        raise SmokeConfigError(f'initialize falló: HTTP {r.status_code} {str(b)[:200]}')
    sid = r.headers.get('Mcp-Session-Id')
    results.append({'name': 'initialize', 'status': 'ok', 'detail': b['result'].get('serverInfo', {}).get('name', '')})
    _rpc(http, url, token, 'notifications/initialized', rid=None, sid=sid, timeout=timeout)
    r, b = _rpc(http, url, token, 'tools/list', {}, rid=2, sid=sid, timeout=timeout)
    tools = {t['name']: t for t in ((b or {}).get('result') or {}).get('tools') or []}
    if not tools:
        raise SmokeConfigError(f'tools/list vacío: HTTP {r.status_code} {str(b)[:200]}')
    if DENY & set(tools):
        raise SmokeConfigError('este token ve herramientas de trading/investigación '
                               f'({", ".join(sorted(DENY & set(tools)))}): usa un token SOLO lectura')
    results.append({'name': 'tools/list', 'status': 'ok', 'detail': f'{len(tools)} herramientas'})
    for i, (name, args, must) in enumerate(SMOKE, start=10):
        t = tools.get(name)
        if t is None:
            results.append({'name': name, 'status': 'fail', 'detail': 'no aparece en tools/list'})
            continue
        if name in DENY or not (t.get('annotations') or {}).get('readOnlyHint'):
            results.append({'name': name, 'status': 'fail', 'detail': 'negado: no es de solo lectura'})
            continue
        t1 = time.time()
        r, b = _rpc(http, url, token, 'tools/call', {'name': name, 'arguments': args}, rid=i, sid=sid, timeout=timeout)
        ms = int((time.time() - t1) * 1000)
        res = (b or {}).get('result') or {}
        if r.status_code != 200 or 'error' in (b or {}):
            results.append({'name': name, 'status': 'fail', 'ms': ms, 'detail': f'HTTP {r.status_code} {str(b)[:160]}'})
            continue
        sc = res.get('structuredContent')
        if sc is None:
            try:
                sc = json.loads(((res.get('content') or [{}])[0]).get('text') or '{}')
            except ValueError:
                sc = {}
        if res.get('isError'):
            txt = json.dumps(sc)[:200] if sc else str(res.get('content'))[:200]
            st = 'warn' if NEEDS_DB in txt else 'fail'
            results.append({'name': name, 'status': st, 'ms': ms, 'detail': txt})
            continue
        missing = [k for k in must if k not in sc]
        results.append({'name': name, 'status': 'fail' if missing else 'ok', 'ms': ms,
                        'detail': f'faltan {missing}' if missing else f'{len(sc)} campos'})
    try:
        http.delete(url, headers={'Authorization': f'Bearer {token}', 'Mcp-Session-Id': sid or ''}, timeout=timeout)
    except Exception:  # noqa: BLE001
        pass
    n_fail = sum(1 for x in results if x['status'] == 'fail')
    return {'url': base_url, 'ok': n_fail == 0, 'n_fail': n_fail,
            'n_warn': sum(1 for x in results if x['status'] == 'warn'),
            'duration_ms': int((time.time() - t0) * 1000), 'results': results}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--url', default=os.getenv('KHIPU_URL') or DEFAULT_URL)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--retries', type=int, default=int(os.getenv('SMOKE_RETRIES') or 1),
                    help='reintentos si el servidor aún está arrancando (tras un deploy)')
    args = ap.parse_args(argv)
    token = os.getenv('KHIPU_MCP_TOKEN', '').strip()
    out, err = None, None
    for intento in range(max(1, args.retries)):
        try:
            out = smoke(args.url, token)
            if out['ok']:
                break
        except SmokeConfigError as e:
            err = str(e)
            if 'falta KHIPU_MCP_TOKEN' in err or 'SOLO lectura' in err:
                break
        except Exception as e:  # noqa: BLE001 — red caída, deploy a medias…
            err = f'{type(e).__name__}: {e}'
        if intento + 1 < args.retries:
            time.sleep(30)
    if out is None:
        print(f'❌ {err}', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(out, indent=1, ensure_ascii=False))
    else:
        icon = {'ok': '✅', 'warn': '⚠️', 'fail': '❌'}
        for x in out['results']:
            print(f"{icon[x['status']]} {x['name']:<24} {str(x.get('ms', '')):>6}  {x['detail']}")
        print(f"\n{'✅ TODO BIEN' if out['ok'] else '❌ HAY FALLOS'} · {out['url']} · {out['duration_ms']} ms")
    return 0 if out['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
