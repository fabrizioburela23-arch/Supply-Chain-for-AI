"""tests/test_genui_render_node.py — RESPUESTAS VISUALES (kblocks/1), fase F2: las funciones PURAS del cliente en node
(docs/CHAT_UI_GENERATIVA.md §10.1).

Carga engine/agents_registry.js + genui.js + genui_charts.js + genui_shapes.js en vm (sin DOM) y comprueba:
  · formato de cifras por unidad y por idioma (es/en), signo, «—» sin dato y su motivo; nunca un 0 falso;
  · toTable() de CADA bloque listo de los ejemplos y de las 4 preguntas del prototipo (vista accesible / CSV),
    y que cada cifra de la tabla sale de los datos del bloque (no se calcula nada);
  · height() estable (mismo bloque, mismo ancho → misma altura) para reservar el espacio;
  · catalog() = los 17 tipos; el resumen accesible («Respuesta lista: 1 gráfico, …») en es/en.
"""
import json
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = shutil.which('node')
pytestmark = pytest.mark.skipif(not NODE, reason='requiere node')

HARNESS = r"""
const fs = require('fs'), vm = require('vm');
const ROOT = process.argv[1];
const store = {};
const ctx = { console, Date, Math, JSON, Intl, Promise, Array, Object, String, Number, isFinite,
  setTimeout, clearTimeout, localStorage: { getItem: k => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } } };
ctx.window = ctx; ctx.globalThis = ctx;
vm.createContext(ctx);
for (const f of ['agents_registry.js', 'genui.js', 'genui_charts.js', 'genui_shapes.js']) vm.runInContext(fs.readFileSync(ROOT + '/engine/' + f, 'utf8'), ctx);
const G = ctx.KhipuGenUI, out = {};
const ex = JSON.parse(fs.readFileSync(ROOT + '/tests/fixtures/genui/examples.kblocks.json', 'utf8'));
const pq = JSON.parse(fs.readFileSync(ROOT + '/tests/fixtures/genui/prototype_questions.kblocks.json', 'utf8'));
const envs = ex.valid.map(v => v.envelope);
pq.questions.forEach(q => { envs.push(q.envelope.es); envs.push(q.envelope.en); });
out.catalog = G.catalog();
out.queue = (ctx.__kosKindQueue || []).map(x => x[0]);
function fmtCase(lang) {
  ctx.LANG = lang;
  const f = G._vm.fmt, P = G._vm.parts;
  return { usd: f(109.5, 'USD'), usdBig: f(-1530, 'USD'), usdB: f(1234.5, 'USD_B'), pct: f(1.234, 'pct'), pctInt: f(50, 'pct'),
    sign: P(1.2, 'pct', { sign: true }).text, neg: f(-0.4, 'pct'), x: f(40, 'x'), nrs: f(70, 'nrs'), count: f(1234, 'count'),
    ccy: f(950, 'CCY', { currency: 'TWD' }), na: f(null, 'USD'), nan: f(NaN, 'pct'), prec: f(3.14159, 'none', { precision: 3 }),
    fig: G._vm.figure({ v: null, unit: 'USD_B', src: 'finnhub', as_of: null, missing_reason: { es: 'sin dato en vivo', en: 'no live data' } }),
    sum: G._vm.summary([{ type: 'text' }, { type: 'chart.line' }, { type: 'ranking' }, { type: 'table' }, { type: 'metric.tiles' }, { type: 'sources' }]) };
}
out.es = fmtCase('es'); out.en = fmtCase('en');
ctx.LANG = 'es';
out.tables = []; out.heights = [];
envs.forEach(env => env.blocks.forEach(b => {
  const t = G.toTable(b);
  out.tables.push({ type: b.type, state: b.state, block: b, t: t });
  out.heights.push([b.type, G._u.height(b, 600), G._u.height(b, 600), G._u.height(b, 380)]);
}));
process.stdout.write(JSON.stringify(out));
"""


@pytest.fixture(scope='module')
def run():
    p = subprocess.run([NODE, '-e', HARNESS, ROOT], capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr[-2000:]
    return json.loads(p.stdout)


def test_catalogo_y_ventana_genui(run):
    sch = json.loads(open(os.path.join(ROOT, 'governance', 'schemas', 'kblocks-1.schema.json'), encoding='utf-8').read())['$defs']
    want = sorted(sch[b['$ref'].split('/')[-1]]['properties']['type']['const'] for b in sch['Block']['oneOf'])
    assert sorted(run['catalog']) == want
    assert 'genui' in run['queue']                      # 📌 se registra por la cola de arranque de Khipus OS


def test_formato_por_unidad_e_idioma(run):
    es, en = run['es'], run['en']
    assert es['usd'] == '$109,50' and en['usd'] == '$109.50'
    assert es['usdBig'] == '−$1530' and en['usdBig'] == '−$1,530'          # P&L ≥ 1000: sin centavos; signo menos tipográfico
    assert es['usdB'] == '$1234,5 B' and en['usdB'] == '$1,234.5 B'
    assert es['pct'] == '1,2 %' and en['pct'] == '1.2%' and es['pctInt'] == '50 %'
    assert es['sign'] == '+1,2 %' and es['neg'] == '−0,4 %'
    assert es['x'] == '40×' and es['nrs'] == '70/100' and en['count'] == '1,234'
    assert es['ccy'] == '950 TWD' and es['prec'] == '3,142'
    for k in ('na', 'nan'):
        assert es[k] == '—' and en[k] == '—'                                # sin dato: guion, nunca 0
    assert es['fig']['na'] and es['fig']['reason'] == 'sin dato en vivo' and en['fig']['reason'] == 'no live data'
    assert es['sum'] == 'Respuesta lista: 2 gráficos, 1 tabla, 1 grupo de cifras'
    assert en['sum'] == 'Answer ready: 2 charts, 1 table, 1 figure group'


def _nums(b):
    """todos los números de los datos del bloque (sin ids ni rangos)."""
    out = []

    def walk(x):
        if isinstance(x, bool):
            return
        if isinstance(x, (int, float)):
            out.append(float(x))
        elif isinstance(x, dict):
            for k, v in x.items():
                if k not in ('call', 'generation', 'graph_version', 'seq', 'precision', 'rank', 'hop', 's', 'e', 'w', 'h', 'lat', 'lon', 'weight', 'conf'):
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(b.get('data'))
    return out


def test_to_table_de_cada_bloque_sin_cifras_inventadas(run):
    import re
    seen = set()
    for row in run['tables']:
        b, t = row['block'], row['t']
        if row['state'] not in ('ready', 'stale') or b['type'] in ('actions',):
            assert t is None or b['type'] == 'actions'
            continue
        assert t and t['columns'] and isinstance(t['rows'], list), b['type']
        assert all(len(r) == len(t['columns']) for r in t['rows']), b['type']
        seen.add(b['type'])
        nums = _nums(b)
        for r in t['rows']:
            for cell in r[1:]:
                for m in re.findall(r'[−-]?\d[\d.]*(?:,\d+)?', str(cell).replace('/100', '')):
                    if re.match(r'^\d{4}-', str(cell)) or re.match(r'^\d{4}$', m):
                        continue
                    v = float(m.replace('−', '-').replace('.', '').replace(',', '.')) if ',' in m else float(m.replace('−', '-'))
                    if b['type'] in ('timeline', 'sources', 'image', 'callout', 'graph.mini'):
                        continue
                    assert any(abs(abs(v) - abs(n)) <= max(0.051, abs(n) * 0.006) or abs(v - n * 1000) < 1 for n in nums) or v in (0,), (b['type'], cell, nums[:8])
    want = {'text', 'metric.tiles', 'chart.line', 'chart.bar', 'chart.candles', 'ranking', 'table', 'company.card', 'graph.mini',
            'impact.cascade', 'timeline', 'callout', 'image', 'comparison', 'sources'}
    assert want <= seen, want - seen


def test_altura_reservada_estable(run):
    for t, a, b, c in run['heights']:
        assert a == b and a > 40 and c > 40, (t, a, b, c)
