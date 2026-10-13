"""tests/test_alias_voz_paridad.py — G5-19 (lote I1): el servidor entiende los alias de VOZ que entiende el navegador.

Una sola tabla (nodes/legal_names.js: window.VOICE_ALIASES + window.RESOLVE_STOPWORDS) → la lee engine/resolve.js en
el navegador y el exportador la saca al snapshot (data/grafo_v0.json: voice_aliases / resolve_stopwords) para
core/entities.py. Comprueba:

  1. engine/resolve.js ya NO tiene su propia copia de la tabla (nunca dos listas a mano).
  2. Paridad: TODOS los alias de voz + todas las etiquetas + todos los tickers del catálogo → el mismo id en el
     navegador (KhipuResolve.find, en Node) y en el servidor (core.entities.resolve, umbral de búsqueda). Las
     diferencias que quedan son SOLO las conocidas (el navegador hace fuzzy/prefijos donde el servidor no adivina).
  3. Un alias de voz NUNCA alcanza el umbral de ESCRITURA (85): 'video' o 'applied' no pegan hechos a una empresa.
  4. El detector de entidades del contexto no marca empresas por alias de voz amplios dentro de una frase.
  5. El snapshot está al día con nodes/legal_names.js.
"""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
NODE = shutil.which('node')

HARNESS = r'''
const vm = require('vm'), fs = require('fs'), path = require('path');
const R = process.argv[1];
const snap = JSON.parse(fs.readFileSync(path.join(R, 'data/grafo_v0.json'), 'utf8'));
const w = { NODES: snap.nodes, NODE_BY_ID: {}, localStorage: { getItem: () => null }, addEventListener() {} };
snap.nodes.forEach(n => { w.NODE_BY_ID[n.id] = n; });
Object.keys(snap.node_id_alias || {}).forEach(k => { const t = w.NODE_BY_ID[snap.node_id_alias[k]]; if (t) w.NODE_BY_ID[k] = t; });
w.window = w; w.document = { addEventListener() {}, getElementById: () => null, querySelectorAll: () => [] };
vm.createContext(w);
vm.runInContext(fs.readFileSync(path.join(R, 'engine/resolve.js'), 'utf8'), w);
vm.runInContext(fs.readFileSync(path.join(R, 'nodes/legal_names.js'), 'utf8'), w);
const qs = JSON.parse(fs.readFileSync(0, 'utf8'));
const out = {};
qs.forEach(q => { const r = w.KhipuResolve.find(q); out[q] = r && r.node ? r.node.id : null; });
process.stdout.write(JSON.stringify({ out, va: w.VOICE_ALIASES, st: Object.keys(w.RESOLVE_STOPWORDS).sort() }));
'''


def _snap():
    with open(os.path.join(ROOT, 'data', 'grafo_v0.json'), encoding='utf-8') as fh:
        return json.load(fh)


def _browser(queries):
    p = subprocess.run([NODE, '-e', HARNESS, ROOT], input=json.dumps(queries), capture_output=True, text=True,
                       timeout=120)
    assert p.returncode == 0, p.stderr[-2000:]
    return json.loads(p.stdout)


def test_resolve_js_no_tiene_copia_propia():
    src = open(os.path.join(ROOT, 'engine', 'resolve.js'), encoding='utf-8').read()
    assert 'window.VOICE_ALIASES' in src and 'window.RESOLVE_STOPWORDS' in src
    assert "'en vidia'" not in src and 'var STOP = {' not in src
    ln = open(os.path.join(ROOT, 'nodes', 'legal_names.js'), encoding='utf-8').read()
    assert "'en vidia': 'Nvidia'" in ln


@pytest.mark.skipif(not NODE, reason='node no instalado')
def test_snapshot_al_dia_con_la_tabla():
    snap = _snap()
    got = _browser([])
    assert snap.get('voice_aliases') == got['va'], 'regenera el snapshot: node scripts/export_graph_v0.js'
    assert snap.get('resolve_stopwords') == got['st']


@pytest.mark.skipif(not NODE, reason='node no instalado')
def test_paridad_navegador_servidor():
    from core import entities as E
    snap = _snap()
    va = snap['voice_aliases']
    labels = [n['label'] for n in snap['nodes'] if n.get('label')]
    tickers = [n['mkt'] for n in snap['nodes'] if n.get('mkt')]
    extra = ['en vidia', 'envidia', 'taiwan semi', 'open ai', 'la empresa en vidia', 'el open ai']
    queries = sorted(set(list(va) + labels + tickers + extra))
    br = _browser(queries)['out']
    diff = {}
    for q in queries:
        r = E.resolve(q)
        s = r['id'] if r else None
        if s != br[q]:
            diff[q] = (br[q], s)
    # 1) los alias de voz: idénticos SIEMPRE (los dos leen la misma tabla)
    ids = {n['id'] for n in snap['nodes']} | set(snap.get('node_id_alias') or {})
    vivos = {E.norm(k) for k, v in va.items() if v in ids}       # un alias a un id que no existe se ignora en ambos
    voz_diff = {q: v for q, v in diff.items() if E.norm(q) in vivos or q in extra}
    assert not voz_diff, f'alias de voz que el servidor entiende distinto: {voz_diff}'
    # 2) etiquetas/tickers: como mucho las diferencias de antes del lote (el servidor no hace fuzzy y resuelve
    #    sufijos societarios que el navegador no). Hoy medidas: ≤ 5 sobre ~1.500 consultas.
    assert len(diff) <= 5, diff
    for q in ('en vidia', 'envidia', 'taiwan semi', 'open ai'):
        assert br[q] is not None and E.resolve(q)['id'] == br[q], q


def test_alias_de_voz_nunca_alcanza_el_umbral_de_escritura():
    from core import entities as E
    for q in ('video', 'applied', 'en vidia', 'texas', 'lam', 'open ai', 'taiwan semi'):
        r = E.resolve(q)
        if r and r['method'] in ('voice_alias', 'voice_prefijo'):
            assert r['score'] < E.UMBRAL_ESCRITURA
            assert E.resolve(q, umbral=E.UMBRAL_ESCRITURA) is None, q
    assert E.resolve('en vidia')['method'] == 'voice_alias'


def test_detector_de_contexto_no_usa_alias_de_voz_amplios():
    from core import context_engine
    assert 'Nvidia' not in context_engine.detect('Mira este video sobre el clima en Texas')
    assert 'AMAT' not in context_engine.detect('He applied the rule to the lam data')
