"""tests/test_merge_graph_alias.py — G1c (misión de reparación 2026-10-04).

`nodes/merge_graph.js` (EL merge, compartido por el navegador y el snapshot)
debe dejar `NODE_BY_ID[alias] === NODE_BY_ID[canónico]` para TODO alias de
NODE_ID_ALIAS cuyo canónico exista. Antes, si el nodo con id alias se cargaba
ANTES que el canónico, se renombraba pero el id viejo quedaba sin mapear (32
de 90 alias): `jumpTo('SouthernCompany')` o un hecho temporal con el id viejo
no encontraban la empresa.
"""
import json
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')

JS = r"""
const fs = require('fs'), path = require('path'), vm = require('vm');
const ROOT = process.argv[1];
const src = fs.readFileSync(path.join(ROOT, 'scripts/export_graph_v0.js'), 'utf-8');
const files = vm.runInNewContext(src.match(/const DATA_FILES = (\[[\s\S]*?\]);/)[1]);
const ctx = vm.createContext({ window: {}, console: { log(){}, warn(){}, error(){} } });
for (const f of files) vm.runInContext(fs.readFileSync(path.join(ROOT, f), 'utf-8'), ctx, { filename: f });
const g = n => vm.runInContext(`typeof ${n} !== 'undefined' ? ${n} : (window.${n} !== undefined ? window.${n} : null)`, ctx);
const NODES = g('NODES'); const NODE_BY_ID = {}; NODES.forEach(n => { NODE_BY_ID[n.id] = n; });
const exp = src.match(/expansions: (\[[^\]]*\])/)[1]; const lnk = src.match(/linkArrays: (\[[^\]]*\])/)[1];
g('buildKhipusGraph')({ NODES, NODE_BY_ID, NODE_ID_ALIAS: g('NODE_ID_ALIAS'), RAW_LINKS: g('RAW_LINKS'),
  LISTING_STATUS: g('LISTING_STATUS'), PRIVATE_VALUATIONS: g('PRIVATE_VALUATIONS'),
  expansions: vm.runInNewContext(exp).map(g), linkArrays: vm.runInNewContext(lnk).map(g), warn: () => {} });
const A = g('NODE_ID_ALIAS') || {};
const resolve = id => { let k = 0; while (A[id] && k++ < 5) id = A[id]; return id; };
const bad = [], ok = [];
for (const a of Object.keys(A)) {
  const c = resolve(a);
  if (!NODE_BY_ID[c]) continue;                       // canónico inexistente: otro problema
  if (NODE_BY_ID[a] !== NODE_BY_ID[c]) bad.push(a + '→' + c); else ok.push(a);
}
const ids = NODES.map(n => n.id);
const aliasLeft = ids.filter(id => A[id]);            // ningún nodo debe quedar con id alias
process.stdout.write(JSON.stringify({ bad, ok: ok.length, nodes: NODES.length, unique: new Set(ids).size, aliasLeft }));
"""


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_todo_alias_apunta_al_nodo_canonico():
    out = subprocess.run([NODE, '-e', JS, ROOT], capture_output=True, text=True, timeout=60, check=True).stdout
    r = json.loads(out)
    assert r['bad'] == [], f"{len(r['bad'])} alias sin mapear: {r['bad'][:10]}"
    assert r['ok'] >= 50
    assert r['nodes'] == r['unique'], 'ids de nodo repetidos tras el merge'
    assert r['aliasLeft'] == [], f"nodos que conservan un id alias: {r['aliasLeft']}"
