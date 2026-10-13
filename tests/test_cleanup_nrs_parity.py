"""Limpieza 2026-10-11 (§2 del inventario de "cosas sueltas"): el NRS tenía 5 copias con
divergencia REAL — el servidor omitía el término fundamental (hasta 15 pts en 370/937 empresas) y
Python redondeaba al par (457/937 empresas con término de mercado terminado en .5 → 1 punto menos).
Ahora hay UNA fórmula por lenguaje: app.html `_nrsTerms` y core/world.py `client_nrs` (servidor,
MCP y carteras delegan ahí). Esta prueba ejecuta la del navegador sobre TODO el catálogo y exige
el MISMO número que la de Python, empresa por empresa."""
import inspect
import json
import os
from tests._app_source import app_source  # noqa: E402
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _node(script, payload):
    r = subprocess.run(['node', '-e', script], input=json.dumps(payload), capture_output=True, text=True,
                       cwd=ROOT, timeout=120)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _client_src():
    html = app_source()
    i = html.index('let _nrsDegree = null;')
    j = html.index('window.computeNRSBreakdown = computeNRSBreakdown;', i)
    return html[i:j] + 'window.computeNRS = computeNRS; window.computeNRSBreakdown = computeNRSBreakdown;'


def test_nrs_del_navegador_y_de_python_coinciden_en_todo_el_catalogo(monkeypatch):
    import core.live_fundamentals as lf
    from core.world import client_nrs
    from ontology.vocabulary import flow_degree
    monkeypatch.setattr(lf, 'live_margin', lambda _id: None)      # misma entrada en los dos lados
    snap = json.load(open(os.path.join(ROOT, 'data', 'grafo_v0.json'), encoding='utf-8'))
    nodes = [n for n in snap['nodes'] if n.get('id')]
    links = [{'source': l['source'], 'target': l['target'], 'type': l.get('type') or 'supply'}
             for l in snap['links']]
    harness = r'''
const vm = require('vm');
const P = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const ctx = { console };
ctx.window = ctx;
ctx.lid = x => (x && typeof x === 'object') ? x.id : x;
ctx.LINKS = P.links;
ctx.NODE_BY_ID = {};
for (const n of P.nodes) ctx.NODE_BY_ID[n.id] = n;
vm.createContext(ctx);
vm.runInContext(P.src, ctx);
const out = {};
for (const n of P.nodes) out[n.id] = [ctx.computeNRS(n.id), ctx.computeNRSBreakdown(n.id).total];
process.stdout.write(JSON.stringify(out));
'''
    js = _node(harness, {'src': _client_src(), 'nodes': nodes, 'links': links})
    deg = flow_degree(links)
    diffs = []
    for n in nodes:
        py = client_nrs(n, deg.get(n['id'], 0))
        a, b = js[n['id']]
        assert a == b, n['id']                                   # total del desglose = computeNRS
        if a != py:
            diffs.append((n['id'], a, py))
    assert len(nodes) > 900
    assert not diffs, f'{len(diffs)} empresas con NRS distinto JS↔Python, p. ej. {diffs[:5]}'


def test_servidor_y_carteras_delegan_en_la_formula_unica():
    from core import portfolio_ai
    from ontology import agents
    assert 'client_nrs' in inspect.getsource(agents._compute_server_nrs)
    assert 'client_nrs' in inspect.getsource(portfolio_ai.nrs)
    assert not hasattr(agents, 'GEO_RISK')                       # tabla muerta (la de verdad vive en core/world)


def test_carteras_suman_el_termino_fundamental_y_redondean_como_la_app(monkeypatch):
    import core.live_fundamentals as lf
    from core import portfolio_ai
    from core.world import client_nrs
    monkeypatch.setattr(lf, 'live_margin', lambda _id: None)
    preipo = {'id': 'x', 'country': 'EEUU', 'margin': 0.2, 'preipo': True, 'growth': '🔴 cae'}
    assert portfolio_ai.nrs(preipo, 1) == client_nrs(preipo, 1) == 8 + 3 + 10 + 15 + 4   # 2.5 + 10 → 12.5 → JS round
