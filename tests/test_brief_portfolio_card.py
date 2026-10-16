"""Brief matinal: tarjeta «Qué cambió en tu cartera desde ayer y por qué» (2026-10-16, «IA concreta» b). Cifras SOLO de
las cotizaciones de la app × valor de la posición (KhipuHot.myPositions); el porqué del grafo o de las noticias."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

HARNESS = r"""
const fs = require('fs'), vm = require('vm');
const feed = %FEED%, news = %NEWS%;
const W = {
  LANG: 'es', setTimeout, console,
  NODE_BY_ID: {Nvidia: {id: 'Nvidia', label: 'Nvidia', mkt: 'NVDA'}, AMD: {id: 'AMD', label: 'AMD', mkt: 'AMD'}},
  MKT: {quotes: {NVDA: {close: 110, prev: 100, src: 'finnhub', as_of: '2026-10-16T14:30:00Z'},
                 AMD: {close: 95, prev: 100, src: 'yahoo', as_of: '2026-10-16T14:30:00Z'}}},
  quotePx: q => q.close,
  KhipuHot: {myPositions: () => ({positions: [{id: 'Nvidia', symbol: 'NVDA', usd: 1100}, {id: 'AMD', symbol: 'AMD', usd: 950}],
                                   no_price: %NOPRICE%})},
  KhipuPfStore: {name: () => 'Mi cartera'}, addEventListener: () => {},
  localStorage: {getItem: () => null, setItem: () => {}},
  document: {getElementById: () => null, addEventListener: () => {}, readyState: 'loading', hidden: true,
             createElement: () => ({}), head: {appendChild: () => {}}, body: {appendChild: () => {}}},
  fetch: (url) => Promise.resolve({ok: true, json: () => Promise.resolve(url.indexOf('/feed') >= 0 ? feed : news)}),
};
W.window = W;
vm.createContext(W);
vm.runInContext(fs.readFileSync('engine/brief.js', 'utf8'), W);
W._briefPfCard().then(c => { process.stdout.write(JSON.stringify(c)); });
"""


def _run(feed, news, no_price=0):
    if not shutil.which('node'):
        pytest.skip('sin node')
    js = HARNESS.replace('%FEED%', json.dumps(feed)).replace('%NEWS%', json.dumps(news)).replace('%NOPRICE%', str(no_price))
    out = subprocess.run(['node', '-e', js], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_cambio_desde_ayer_con_motivo_del_grafo_y_de_noticias():
    feed = {'feed': [{'title': 'TSMC amplía la capacidad CoWoS para Nvidia', 'entities': ['TSMC', 'Nvidia'],
                      'recorded_at': '2026-10-16T08:00:00Z'}]}
    news = {'items': [{'title': 'AMD baja tras su guía', 'holdings': ['AMD'], 'outlet': 'Reuters'}]}
    c = _run(feed, news)
    t = c['text']
    assert c['kind'] == 'pf' and c['node'] == 'Nvidia'           # el que más movió en USD va primero
    assert 'Mi cartera' in t and '+50 USD' in t                    # 100 − 50 = +50 desde el cierre anterior
    assert '+10 %' in t and '+100 USD' in t and '−5 %' in t and '−50 USD' in t
    assert 'CoWoS' in t and 'grafo Khipus' in t and 'AMD baja' in t and 'Reuters' in t
    assert 'finnhub' in t                                          # fuente del precio a la vista


def test_sin_motivo_y_sin_precio_de_ayer_se_dice():
    c = _run({'feed': []}, {'items': []}, no_price=1)
    assert 'sin hechos nuevos' in c['text'] and '1 posición(es) sin precio de ayer' in c['text']
