"""tests/test_genui_rivals.py — «ganadores» de un choque en el SERVIDOR (core/genui/rivals.py) = el MISMO resultado que
KhipuHot.rivals del navegador (engine/hotclient.js), sobre las mismas entradas (docs/CHAT_UI_GENERATIVA.md §5.2, F1
paso 11). Se corre el JS real en node con el catálogo real; impactos y capitalizaciones al azar (semilla fija).
Y run_scenario (mcp_server/ops.py) los devuelve calculados sobre TODOS los impactos del kernel.
"""
import json
import os
import random
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.genui import rivals as R  # noqa: E402

NODE = shutil.which('node')

HARNESS = r"""
const fs = require('fs'), vm = require('vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const win = { NODES: input.nodes, NODE_BY_ID: {}, NODE_META: input.meta, LANG: 'es' };
input.nodes.forEach(n => { win.NODE_BY_ID[n.id] = n; });
win.window = win;
const ctx = vm.createContext(Object.assign(win, { console, Map, Promise, setTimeout, clearTimeout }));
vm.runInContext(fs.readFileSync(input.file, 'utf8'), ctx, { filename: 'hotclient.js' });
const out = input.cases.map(c => win.KhipuHot.rivals(c.seeds, c.impacts, c.max));
process.stdout.write(JSON.stringify(out));
"""


def _catalog():
    with open(os.path.join(ROOT, 'data', 'grafo_v0.json'), encoding='utf-8') as fh:
        return [{'id': n['id'], 'cat': n.get('cat')} for n in json.load(fh)['nodes']]


def _cases(nodes, n=60):
    rng = random.Random(20261013)
    ids = [x['id'] for x in nodes]
    caps_pool = [None, 0, 1.5, 12, 250.0, '3.2', ' 44 ', 'div. IBM', '', '1e3', 0.25, 4447.3, '12abc']
    out, meta = [], {}
    for i in ids:
        c = rng.choice(caps_pool)
        if c is not None:
            meta[i] = {'mktcap_b': c}
    for k in range(n):
        seeds = rng.sample(ids, rng.choice((1, 1, 2, 3)))
        imp = {}
        for i in rng.sample(ids, rng.randint(5, 300)):
            imp[i] = rng.choice((rng.uniform(0, 100), rng.uniform(35, 45), rng.uniform(10, 20), 14.95, 15.0, 40.0,
                                 39.99, 0.04, 100.0))
        for s in seeds:
            imp[s] = 100.0
        out.append({'seeds': seeds, 'impacts': imp, 'max': rng.choice((0, 4, 6, 12))})
    return out, meta


@pytest.mark.skipif(not NODE, reason='node no instalado')
def test_paridad_con_khipuhot_rivals():
    nodes = _catalog()
    cases, meta = _cases(nodes)
    payload = {'nodes': nodes, 'meta': meta, 'cases': cases, 'file': os.path.join(ROOT, 'engine', 'hotclient.js')}
    p = subprocess.run([NODE, '-e', HARNESS], input=json.dumps(payload), capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr[-2000:]
    js = json.loads(p.stdout)
    caps = {k: v['mktcap_b'] for k, v in meta.items()}
    nonempty = 0
    for c, want in zip(cases, js):
        got = R.rivals(c['seeds'], c['impacts'], nodes, caps, c['max'])
        assert got == want, (c['seeds'], got[:3], want[:3])
        nonempty += bool(got)
    assert nonempty >= 20                         # la muestra ejercita la regla de verdad


def test_js_number_como_javascript():
    for v, want in ((None, 0), ('', 0), (' 44 ', 44), ('1e3', 1000), ('div. IBM', 0), ('12abc', 0), (float('nan'), 0),
                    (True, 1), ('0x1A', 26), (2.5, 2.5)):
        assert R.js_number(v) == want, v
    assert R.js_round1(1.25) == 1.3 and R.js_round1(14.95) == 15.0 and R.js_round1(-0.05) == 0.0


def test_run_scenario_los_trae_del_kernel():
    from mcp_server import tools as mt
    from mcp_server.auth import Principal
    p = Principal(token_id='t', name='t', scopes=frozenset({'read'}))
    r = mt.call('run_scenario', {'shocks': [{'id': 'TSMC'}]}, mt.Ctx(principal=p))
    riv = r['least_hit_rivals']
    assert 1 <= len(riv) <= 4 and 'DAMAGE' in r['least_hit_rivals_rule']
    assert all(x['impact_pct'] < R.RIVAL_MAX and x['id'] != 'TSMC' and x['cat_damaged'] >= 1 for x in riv)
