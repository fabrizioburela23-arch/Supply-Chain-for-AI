"""tests/test_pickers.py — opciones FIJAS (pedido 2026-10-05): engine/pickers.js sugiere empresas o
símbolos mientras se escribe y solo acepta opciones de la lista (exact)."""
import json
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')
JS = r"""
global.window = { LANG: 'es', addEventListener: () => {} };
global.document = { addEventListener: () => {}, getElementById: () => null };
global.localStorage = { getItem: () => null };
window.NODES = [{id:'Nvidia',label:'Nvidia',mkt:'NVDA'},{id:'TSMC',label:'TSMC',mkt:'TSM · NYSE'},{id:'Tesla',label:'Tesla',mkt:'TSLA'},
                {id:'OpenAI',label:'OpenAI',mkt:null},{id:'Envicool',label:'Envicool',mkt:'002837.SZ'}];
window.NODE_BY_ID = {}; window.NODES.forEach(n => window.NODE_BY_ID[n.id] = n); window.NODE_BY_ID['NVIDIA'] = window.NODE_BY_ID.Nvidia;
window.CRYPTO_INTEL = { bitcoin: { ticker: 'BTC', name: 'Bitcoin' } };
require(process.argv[1] + '/engine/pickers.js');
const P = window.KhipuPick;
const out = {
  nvi: P.search('nvi', 'entity').map(x => x.value),
  ts: P.search('ts', 'entity').map(x => x.value),
  sym_ts: P.search('ts', 'symbol').map(x => x.value),
  btc: P.search('btc', 'symbol').map(x => x.value),
  exact_nvda: (P.exact('nvda', 'entity') || {}).value || null,
  exact_tsm_sym: (P.exact('TSM', 'symbol') || {}).value || null,
  exact_free: P.exact('Empresa Inventada', 'entity'),
  exact_openai_sym: P.exact('OpenAI', 'symbol'),
};
process.stdout.write(JSON.stringify(out));
"""


@pytest.mark.skipif(not NODE, reason='requiere node')
def test_sugiere_y_solo_acepta_opciones_de_la_lista():
    r = subprocess.run([NODE, '-e', JS, ROOT], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    o = json.loads(r.stdout)
    assert o['nvi'][0] == 'Nvidia'
    assert o['ts'][:2] == ['TSMC', 'Tesla']
    assert o['sym_ts'][:2] == ['TSM', 'TSLA'] and o['btc'] == ['BTC/USD']
    assert o['exact_nvda'] == 'Nvidia' and o['exact_tsm_sym'] == 'TSM'
    assert o['exact_free'] is None
    assert o['exact_openai_sym'] is None
